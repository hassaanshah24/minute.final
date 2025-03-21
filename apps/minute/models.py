# apps/minute/models.py
from django.db import models, transaction
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models import F

from apps.approval_chain.models import Approver

User = get_user_model()


def generate_unique_id(department):
    """
    Generates a unique ID for the minute sheet using the format:
    DHA/DSU/{DepartmentCode}/{MM-YYYY}/{4-digit Unique Number}
    """
    current_date = now()
    month_year = current_date.strftime("%m-%Y")

    Minute = apps.get_model("minute", "Minute")  # ✅ Prevents circular import issues

    count = Minute.objects.filter(
        department=department, created_at__year=current_date.year, created_at__month=current_date.month
    ).count()

    unique_number = f"{count + 1:04d}"  # 4-digit unique number

    return f"DHA/DSU/{department.code}/{month_year}/{unique_number}"


class Minute(models.Model):
    """
    Model representing a Minute Sheet.
    """

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Archived", "Archived"),
    ]

    subject = models.CharField(max_length=255, help_text="The subject of the minute sheet.")
    description = models.TextField(help_text="Detailed description of the minute.")
    unique_id = models.CharField(max_length=50, unique=True, editable=False, help_text="Auto-generated unique ID.")
    sheet_no = models.PositiveIntegerField(help_text="Auto-incremented Sheet No per department.")

    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        related_name="minutes",
        help_text="The department this minute belongs to."
    )

    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_minutes", help_text="User who created this minute."
    )

    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the minute was created.")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Pending", help_text="Current status of the minute."
    )

    approval_chain = models.OneToOneField(
        "approval_chain.ApprovalChain",
        on_delete=models.CASCADE,
        related_name="linked_minute",
        null=True,
        blank=True,
        help_text="The approval chain linked to this minute."
    )
    attachment = models.FileField(
        upload_to="minute_attachments/",
        blank=True,
        null=True,
        help_text="Optional attachment (PDF, image, Word, Excel, etc.)."
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["unique_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.subject} ({self.unique_id})"

    # apps/minute/models.py

    def save(self, *args, **kwargs):
        """
        Custom save method to ensure:
        - Unique ID and Sheet Number are set.
        - Approval Chain is created (if missing).
        - First Approver is activated automatically.
        """
        if not self.department:
            self.department = self.created_by.department  # Auto-assign department from user

        if not self.unique_id:
            self.unique_id = generate_unique_id(self.department)

        if not self.sheet_no:
            last_sheet = Minute.objects.filter(department=self.department).order_by("-sheet_no").first()
            self.sheet_no = (last_sheet.sheet_no + 1) if last_sheet else 1

        super().save(*args, **kwargs)  # ✅ First save the Minute object

        # ✅ Ensure ApprovalChain is created **only if it does not exist**
        ApprovalChain = apps.get_model("approval_chain", "ApprovalChain")

        if not self.approval_chain:
            approval_chain = ApprovalChain.objects.create(
                name=f"Approval Chain for {self.unique_id}",
                created_by=self.created_by,
                minute=self
            )
            self.approval_chain = approval_chain
            self.save(update_fields=["approval_chain"])  # ✅ Save only the new field

        # ✅ Auto-Activate First Approver
        first_approver = self.approval_chain.approvers.order_by("order").first()
        if first_approver and not first_approver.is_current:
            first_approver.is_current = True
            first_approver.save()  # ✅ Ensure the first approver is activated immediately

    @transaction.atomic
    def finalize_minute(self, status):
        """
        Finalizes the minute by marking it as Approved or Rejected, then moving to the archive.
        """
        self.status = status
        self.approval_chain.status = "Completed"
        self.approval_chain.save()

        if status == "Rejected":
            self.archive()

        self.save()

    @transaction.atomic
    def approve(self, approver):
        """
        Approves the minute and moves it to the next approver.
        If it's the last approver, the minute is marked as 'Approved'.
        """
        current_approver = self.approval_chain.approvers.filter(user=approver, is_current=True).first()

        if not current_approver:
            raise ValidationError("You are not authorized to approve this minute.")

        current_approver.approve()

        next_approver = self.approval_chain.get_next_approver(current_approver.order)

        if next_approver:
            next_approver.is_current = True
            next_approver.save()
        else:
            self.finalize_minute("Approved")

    @transaction.atomic
    def reject(self, approver):
        """
        Rejects the minute and archives it.
        """
        current_approver = self.approval_chain.approvers.filter(user=approver, is_current=True).first()

        if not current_approver:
            raise ValidationError("You are not authorized to reject this minute.")

        current_approver.reject()
        self.finalize_minute("Rejected")

    @transaction.atomic
    def mark_to(self, approver, target_user, target_order=None):
        """
        Marks the minute to another user, inserting them into the approval chain.
        - If an approver already exists at the target order, shift all subsequent approvers down.
        - Ensures only one approver remains active.
        """
        # ✅ Ensure the user making this action is the current approver
        current_approver = self.approval_chain.approvers.filter(user=approver, is_current=True).first()

        if not current_approver:
            raise ValidationError("You are not authorized to mark this minute to another user.")

        if self.approval_chain.approvers.filter(user=target_user).exists():
            raise ValidationError(f"{target_user.get_full_name()} is already in the approval chain.")

        max_order = self.approval_chain.approvers.aggregate(models.Max("order"))["order__max"] or 0
        target_order = target_order or max_order + 1  # Default to next available order

        # ✅ If inserting in the middle, shift subsequent orders down
        if target_order <= max_order:
            self.approval_chain.approvers.filter(order__gte=target_order).update(order=F("order") + 1)

        # ✅ Create new approver
        new_approver = Approver.objects.create(
            approval_chain=self.approval_chain,
            user=target_user,
            order=target_order,
            status="Pending",
            is_current=False  # Default to inactive
        )

        # ✅ Update the current approver's status
        current_approver.status = "Marked"
        current_approver.is_current = False
        current_approver.save()

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
    def return_to(self, approver, target_user):
        """
        Returns the minute to a previous approver.
        """
        current_approver = self.approval_chain.approvers.filter(user=approver, is_current=True).first()

        if not current_approver:
            raise ValidationError("You are not authorized to return this minute.")

        previous_approver = self.approval_chain.approvers.filter(user=target_user,
                                                                 order__lt=current_approver.order).first()

        if not previous_approver:
            raise ValidationError("The selected user is not a previous approver.")

        # ✅ Deactivate the current approver
        current_approver.is_current = False
        current_approver.status = "Returned"
        current_approver.save()

        # ✅ Reactivate the previous approver only if necessary
        if previous_approver.status != "Pending":
            previous_approver.status = "Pending"

        previous_approver.is_current = True
        previous_approver.save()

    @transaction.atomic
    def archive(self):
        """
        Moves the minute to the archive after approval or rejection.
        """
        self.status = "Archived"
        self.save()

    def is_pending(self):
        return self.status == "Pending"

    def is_archived(self):
        return self.status == "Archived"
