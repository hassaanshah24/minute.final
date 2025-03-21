# Generated by Django 5.1.4 on 2025-03-10 11:26

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("approval_chain", "0004_alter_approvalchain_minute"),
        ("minute", "0003_minute_attachment"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Remark",
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
                    "action",
                    models.CharField(
                        choices=[
                            ("Approve", "Approve"),
                            ("Reject", "Reject"),
                            ("Mark-To", "Mark-To"),
                            ("Return-To", "Return-To"),
                        ],
                        help_text="The action taken by the approver.",
                        max_length=20,
                    ),
                ),
                (
                    "text",
                    models.TextField(
                        blank=True,
                        help_text="Optional remarks added by the approver.",
                        null=True,
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp of when the remark was added.",
                    ),
                ),
                (
                    "approver",
                    models.ForeignKey(
                        help_text="The approver who made this remark.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="remarks",
                        to="approval_chain.approver",
                    ),
                ),
                (
                    "minute",
                    models.ForeignKey(
                        help_text="The minute this remark belongs to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="remarks",
                        to="minute.minute",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="The user who added this remark.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_remarks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
            },
        ),
    ]
