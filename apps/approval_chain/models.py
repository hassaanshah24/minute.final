from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.db.models import Max

User = get_user_model()


class ApprovalChain(models.Model):
    """
    Represents an ordered sequence of approvers for a minute.
    Each minute is linked to a unique approval chain.
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Descriptive name for the approval chain"
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

    def __str__(self):
        return self.name

    @transaction.atomic
    def add_approver(self, user, order=None):
        """
        Adds an approver to the chain in a specific order.
        If no order is given, it auto-assigns the next available order.
        """
        if self.approvers.filter(user=user).exists():
            raise ValidationError(f"{user.get_full_name()} is already an approver.")

        max_order = self.approvers.aggregate(models.Max("order"))["order__max"] or 0
        order = order or max_order + 1

        is_first = order == 1
        approver = Approver.objects.create(
            approval_chain=self,
            user=user,
            order=order,
            is_current=is_first  # First approver is set as current approver
        )
        return approver

    def get_next_approver(self, current_order):
        """
        Retrieves the next approver in the chain.
        """
        return self.approvers.filter(
            order__gt=current_order
        ).order_by("order").first()

    @transaction.atomic
    def check_and_update_status(self):
        """
        Marks the approval chain as complete if all approvers have approved.
        """
        if not self.approvers.filter(status="Pending").exists():
            self.completed = True
            self.save()


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
        Approves the minute and moves to the next approver.
        """
        self.status = "Approved"
        self.is_current = False
        self.save()

        next_approver = self.approval_chain.get_next_approver(self.order)
        if next_approver:
            next_approver.is_current = True
            next_approver.save()
        else:
            self.approval_chain.check_and_update_status()

    @transaction.atomic
    def reject(self):
        """
        Rejects the minute and finalizes it.
        """
        self.status = "Rejected"
        self.is_current = False
        self.save()
        # Final rejection - Notify relevant users

    @transaction.atomic
    def mark_to(self, target_user):
        """
        Marks the minute to another user, adding them into the approval chain.
        """
        if self.approval_chain.approvers.filter(user=target_user).exists():
            raise ValidationError(f"{target_user.get_full_name()} is already in the approval chain.")

        new_order = self.order + 1
        Approver.objects.filter(
            approval_chain=self.approval_chain,
            order__gte=new_order
        ).update(order=models.F("order") + 1)

        new_approver = Approver.objects.create(
            approval_chain=self.approval_chain,
            user=target_user,
            order=new_order,
            status="Pending",
            is_current=True
        )

        self.is_current = False
        self.save()

    @transaction.atomic
    def return_to(self, target_user):
        """
        Returns the minute to a previous approver.
        """
        previous_approver = Approver.objects.filter(
            approval_chain=self.approval_chain,
            user=target_user
        ).first()

        if not previous_approver:
            raise ValidationError(f"{target_user.get_full_name()} is not a previous approver.")

        self.is_current = False
        self.save()

        previous_approver.is_current = True
        previous_approver.status = "Pending"
        previous_approver.save()
