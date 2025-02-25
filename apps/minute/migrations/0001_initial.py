# Generated by Django 5.1.4 on 2025-02-23 16:24

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("approval_chain", "0001_initial"),
        ("departments", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Minute",
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
                    "subject",
                    models.CharField(
                        help_text="The subject of the minute sheet.", max_length=255
                    ),
                ),
                (
                    "description",
                    models.TextField(help_text="Detailed description of the minute."),
                ),
                (
                    "unique_id",
                    models.CharField(
                        editable=False,
                        help_text="Auto-generated unique ID.",
                        max_length=50,
                        unique=True,
                    ),
                ),
                (
                    "sheet_no",
                    models.PositiveIntegerField(
                        help_text="Auto-incremented Sheet No per department."
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the minute was created.",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Pending", "Pending"),
                            ("Approved", "Approved"),
                            ("Rejected", "Rejected"),
                            ("Archived", "Archived"),
                        ],
                        default="Pending",
                        help_text="Current status of the minute.",
                        max_length=20,
                    ),
                ),
                (
                    "approval_chain",
                    models.OneToOneField(
                        blank=True,
                        help_text="The approval chain linked to this minute.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="minute_link",
                        to="approval_chain.approvalchain",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        help_text="User who created this minute.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_minutes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "department",
                    models.ForeignKey(
                        help_text="The department this minute belongs to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="minutes",
                        to="departments.department",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["unique_id"], name="minute_minu_unique__930e49_idx"
                    ),
                    models.Index(
                        fields=["status"], name="minute_minu_status_3ae72d_idx"
                    ),
                ],
            },
        ),
    ]
