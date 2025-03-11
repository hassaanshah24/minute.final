# apps/remarks/models.py
from django.db import models
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from apps.minute.models import Minute
from apps.approval_chain.models import Approver

User = get_user_model()


class Remark(models.Model):
    """
    Stores remarks added by approvers when they take action on a minute.
    """

    minute = models.ForeignKey(
        Minute,
        on_delete=models.CASCADE,
        related_name="remarks",
        help_text="The minute this remark belongs to."
    )

    approver = models.ForeignKey(
        Approver,
        on_delete=models.CASCADE,
        related_name="remarks",
        help_text="The approver who made this remark."
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_remarks",
        help_text="The user who added this remark."
    )

    action = models.CharField(
        max_length=20,
        choices=[
            ("Approve", "Approve"),
            ("Reject", "Reject"),
            ("Mark-To", "Mark-To"),
            ("Return-To", "Return-To"),
        ],
        help_text="The action taken by the approver."
    )

    text = models.TextField(
        blank=True,
        null=True,
        help_text="Optional remarks added by the approver."
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp of when the remark was added."
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.approver.user.get_full_name()} - {self.action} on {self.minute.unique_id}"
