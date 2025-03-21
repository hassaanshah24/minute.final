# Generated by Django 5.1.4 on 2025-02-23 16:24

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Approver",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "order",
                    models.PositiveIntegerField(
                        help_text="The order of this approver in the chain."
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Pending", "Pending"),
                            ("Approved", "Approved"),
                            ("Rejected", "Rejected"),
                            ("Marked", "Marked"),
                            ("Returned", "Returned"),
                        ],
                        default="Pending",
                        help_text="Approval status of this approver.",
                        max_length=20,
                    ),
                ),
                (
                    "is_current",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if this approver is the current active approver.",
                    ),
                ),
            ],
            options={
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="ApprovalChain",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Descriptive name for the approval chain.",
                        max_length=255,
                        unique=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("In Progress", "In Progress"),
                            ("Completed", "Completed"),
                        ],
                        default="In Progress",
                        help_text="Tracks the status of the approval chain.",
                        max_length=20,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the approval chain was created.",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        help_text="User who created this approval chain.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_approval_chains",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
