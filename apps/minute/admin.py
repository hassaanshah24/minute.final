# apps/minute/admin.py
from django.contrib import admin
from apps.minute.models import Minute
from apps.approval_chain.models import ApprovalChain


class ApprovalChainInline(admin.StackedInline):
    """
    Displays Approval Chain inside the Minute panel.
    """
    model = ApprovalChain
    extra = 0
    can_delete = False
    readonly_fields = ["name", "created_by", "created_at", "status"]

@admin.register(Minute)
class MinuteAdmin(admin.ModelAdmin):
    """
    Admin panel for the Minute model.
    """
    list_display = ("id", "subject", "unique_id", "status", "created_by", "created_at", "department", "get_approval_chain")
    list_filter = ("status", "created_by", "department", "created_at")
    search_fields = ("subject", "unique_id", "created_by__username")
    readonly_fields = ("id", "unique_id", "sheet_no", "created_by", "created_at", "approval_chain")  # ✅ Added id
    ordering = ["-created_at"]  # Show newest first

    inlines = [ApprovalChainInline]  # ✅ Shows Approval Chain inside Minute panel

    def get_approval_chain(self, obj):
        """
        Returns the approval chain name instead of auto-generated ID.
        """
        if obj.approval_chain:
            return obj.approval_chain.name  # ✅ Returns the correct Approval Chain Name
        return "No Approval Chain"

    get_approval_chain.short_description = "Approval Chain Name"

    def save_model(self, request, obj, form, change):
        """
        Auto-assigns the created_by field on creation.
        """
        if not obj.pk:  # Only set for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
