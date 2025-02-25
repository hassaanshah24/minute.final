# Generated by Django 5.1.4 on 2025-02-23 16:24

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("approval_chain", "0001_initial"),
        ("minute", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="approvalchain",
            name="minute",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="approval_chains_temp",
                to="minute.minute",
            ),
        ),
        migrations.AddField(
            model_name="approver",
            name="approval_chain",
            field=models.ForeignKey(
                help_text="The approval chain this approver belongs to.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="approvers",
                to="approval_chain.approvalchain",
            ),
        ),
        migrations.AddField(
            model_name="approver",
            name="user",
            field=models.ForeignKey(
                help_text="The user responsible for approving the minute.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="approvals",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="approver",
            unique_together={("approval_chain", "user")},
        ),
    ]
