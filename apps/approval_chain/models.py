# apps/approval_chain/models.py
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.apps import apps  # ✅ Prevents circular imports
from django.db.models import F
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
    def mark_to(self, target_user, target_order=None):
        """
        Inserts a new approver at the specified order in the chain.
        - If an approver already exists at that order, shifts all subsequent approvers down.
        - Ensures the approval chain remains valid.
        - Only one approver remains active (`is_current=True`).
        """
        if not self.is_current:
            raise ValidationError("You are not the current approver for this minute.")

        if self.approval_chain.approvers.filter(user=target_user).exists():
            raise ValidationError(f"{target_user.get_full_name()} is already in the approval chain.")

        max_order = self.approval_chain.approvers.aggregate(models.Max("order"))["order__max"] or 0
        target_order = target_order or max_order + 1  # Default to the next available order

        # ✅ If inserting at the last position, just append without shifting others
        if target_order <= max_order:
            # Shift all affected approvers down by 1 position
            self.approval_chain.approvers.filter(order__gte=target_order).update(order=F("order") + 1)

        # ✅ Add new approver at the target order
        new_approver = Approver.objects.create(
            approval_chain=self.approval_chain,
            user=target_user,
            order=target_order,
            status="Pending",
            is_current=False  # Initially inactive
        )

        # ✅ Update current approver status to "Marked" and deactivate
        self.status = "Marked"
        self.is_current = False
        self.save()

        # ✅ Ensure only one approver remains active
        next_approver = self.approval_chain.approvers.filter(order__gt=self.order, status="Pending").order_by(
            "order").first()

        if next_approver:
            next_approver.is_current = True
            next_approver.save()
        else:
            new_approver.is_current = True  # If no next approver, activate the new one
            new_approver.save()

    @transaction.atomic
    def return_to(self, target_user):
        """
        Sends the minute back to a previous approver.
        """
        if not self.is_current:
            raise ValidationError("You are not the current approver for this minute.")

        previous_approver = self.approval_chain.approvers.filter(user=target_user, order__lt=self.order).first()

        if not previous_approver:
            raise ValidationError("The selected user is not a previous approver.")

        # ✅ Deactivate current approver
        self.is_current = False
        self.status = "Returned"
        self.save()

        # ✅ Reactivate previous approver
        previous_approver.is_current = True
        if previous_approver.status != "Pending":
            previous_approver.status = "Pending"
        previous_approver.save()
