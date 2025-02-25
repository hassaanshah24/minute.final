from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps
from .models import Minute
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db import connection
from apps.minute.models import Minute

@receiver(post_save, sender=Minute)
def create_approval_chain(sender, instance, created, **kwargs):
    """
    Auto-create an Approval Chain when a new Minute is created.
    """
    if created and not instance.approval_chain:
        ApprovalChain = apps.get_model("approval_chain", "ApprovalChain")
        approval_chain = ApprovalChain.objects.create(
            name=f"Approval Chain for {instance.unique_id}",
            created_by=instance.created_by,
            minute=instance
        )
        instance.approval_chain = approval_chain
        instance.save(update_fields=["approval_chain"])


@receiver(post_delete, sender=Minute)
def reset_minute_id_sequence(sender, **kwargs):
    """
    Resets the ID sequence if all Minutes are deleted.
    Ensures the next created Minute starts from ID=1 automatically.
    """
    if not Minute.objects.exists():  # ✅ If no Minutes exist, reset ID
        with connection.cursor() as cursor:
            cursor.execute("SELECT setval(pg_get_serial_sequence('minute_minute', 'id'), 1, false);")