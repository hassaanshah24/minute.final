# apps/approval_chain/models.py
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.apps import apps  # ✅ Prevents circular imports

User = get_user_model()


class ApprovalChain(models.Model):
    """
    Represents an ordered sequence of approvers for a minute.
    Each minute is linked to a unique approval chain.
    """

    STATUS_CHOICES = [
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    ]

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Descriptive name for the approval chain."
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="In Progress",
        help_text="Tracks the status of the approval chain."
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_approval_chains",
        help_text="User who created this approval chain."
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the approval chain was created."
    )

    minute = models.OneToOneField(  # ✅ FIX: Changed from ForeignKey to OneToOneField
        "minute.Minute",
        on_delete=models.CASCADE,
        related_name="approval_chain_link_temp",  # ✅ FIX: Set correct related_name for lookups
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.name} - {self.status}"

    @transaction.atomic
    def add_approver(self, user, order=None):
        """
        Adds an approver to the chain in a specific order.
        If no order is given, it auto-assigns the next available order.
        Ensures the first approver is always set as `is_current=True`.
        """
        if self.approvers.filter(user=user).exists():
            raise ValidationError(f"{user.get_full_name()} is already an approver.")

        max_order = self.approvers.aggregate(models.Max("order"))["order__max"] or 0
        order = order or max_order + 1

        # ✅ Ensure First Approver is Always is_current=True
        is_first = order == 1 and not self.approvers.exists()

        approver = Approver.objects.create(
            approval_chain=self,
            user=user,
            order=order,
            is_current=is_first  # ✅ First approver should always be active
        )

        return approver

    def get_next_approver(self, current_order):
        """
        Retrieves the next approver in the chain.
        """
        return self.approvers.filter(order__gt=current_order, status="Pending").order_by("order").first()

    @transaction.atomic
    def check_and_update_status(self):
        """
        Updates the approval chain status when all approvals are completed.
        """
        if not self.approvers.filter(status="Pending").exists():
            self.status = "Completed"
            self.save()

            # ✅ FIX: Lazy-load `Minute` model to avoid circular imports
            Minute = apps.get_model("minute", "Minute")
            minute = self.minute
            minute.finalize_minute("Approved")


class Approver(models.Model):
    """
    Represents a single user responsible for approving a minute.
    """

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Marked", "Marked"),
        ("Returned", "Returned"),
    ]

    approval_chain = models.ForeignKey(
        ApprovalChain,
        on_delete=models.CASCADE,
        related_name="approvers",
        help_text="The approval chain this approver belongs to."
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="approvals",
        help_text="The user responsible for approving the minute."
    )

    order = models.PositiveIntegerField(help_text="The order of this approver in the chain.")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending",
        help_text="Approval status of this approver."
    )

    is_current = models.BooleanField(
        default=False,
        help_text="Indicates if this approver is the current active approver."
    )

    class Meta:
        unique_together = ("approval_chain", "user")
        ordering = ["order"]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.status} (Order {self.order})"

    @transaction.atomic
    def approve(self):
        """
        Approves the minute and moves it to the next approver.
        If this is the last approver, it finalizes the minute.
        """
        if not self.is_current:
            raise ValidationError("You are not the current approver for this minute.")

        self.status = "Approved"
        self.is_current = False
        self.save()

        next_approver = self.approval_chain.get_next_approver(self.order)

        if next_approver:
            next_approver.is_current = True
            next_approver.save()
        else:
            # ✅ If this is the last approver, finalize the minute
            self.approval_chain.minute.finalize_minute("Approved")

    @transaction.atomic
    def reject(self):
        """
        Rejects the minute and stops the approval chain.
        """
        if not self.is_current:
            raise ValidationError("You are not the current approver for this minute.")

        self.status = "Rejected"
        self.is_current = False
        self.save()

        # ✅ Mark the Approval Chain & Minute as Rejected and archive it
        self.approval_chain.status = "Completed"
        self.approval_chain.save()
        self.approval_chain.minute.finalize_minute("Rejected")

    @transaction.atomic
    def mark_to(self, target_user, target_order):
        """
        Inserts a new approver at the specified order in the chain.
        If an approver already exists at that order, shift all subsequent approvers down.
        """
        if not self.is_current:
            raise ValidationError("You are not the current approver for this minute.")

        if self.approval_chain.approvers.filter(user=target_user).exists():
            raise ValidationError("This user is already in the approval chain.")

        # ✅ Shift all existing approvers if needed
        existing_orders = self.approval_chain.approvers.filter(order__gte=target_order)
        for approver in existing_orders:
            approver.order += 1
            approver.save()

        # ✅ Add the new approver at the specified order
        new_approver = Approver.objects.create(
            approval_chain=self.approval_chain,
            user=target_user,
            order=target_order,
            status="Pending",
            is_current=False
        )

        # ✅ Update current approver status to "Marked"
        self.status = "Marked"
        self.is_current = False
        self.save()

        # ✅ Make the newly added approver the active approver
        new_approver.is_current = True
        new_approver.save()

    @transaction.atomic
    def return_to(self, target_user):
        """
        Sends the minute back to a previous approver.
        """
        previous_approver = self.approval_chain.approvers.filter(user=target_user, order__lt=self.order).first()

        if not previous_approver:
            raise ValidationError("The selected user is not a previous approver.")

        self.is_current = False
        self.save()

        previous_approver.is_current = True
        previous_approver.status = "Pending"  # ✅ Reset status so they need to approve again
        previous_approver.save()
