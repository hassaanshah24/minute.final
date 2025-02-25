# apps/approval_chain/admin.py
from django.contrib import admin
from .models import ApprovalChain, Approver


class ApproverInline(admin.TabularInline):
    """
    Shows approvers inside the Approval Chain admin panel.
    """
    model = Approver
    extra = 0  # No extra empty fields
    readonly_fields = ("user", "order", "status", "is_current")  # Prevent editing
    can_delete = False  # Prevent deletion from admin

    def get_queryset(self, request):
        """
        Filters approvers to show only those linked to a Minute.
        """
        queryset = super().get_queryset(request)
        return queryset.select_related("approval_chain").filter(approval_chain__minute__isnull=False)


@admin.register(ApprovalChain)
class ApprovalChainAdmin(admin.ModelAdmin):
    """
    Admin panel for Approval Chain.
    Shows status of the chain and allows searching/filtering.
    """
    list_display = ("name", "get_linked_minute", "status", "created_by", "created_at")  # ✅ Added Linked Minute
    search_fields = ("name", "created_by__username", "minute__unique_id")
    list_filter = ("status", "created_by", "created_at")
    ordering = ("-created_at",)

    readonly_fields = ("name", "get_linked_minute", "status")  # ✅ Added Linked Minute as readonly

    inlines = [ApproverInline]  # ✅ Show Approvers inside Approval Chain admin

    def get_linked_minute(self, obj):
        """
        Displays the linked Minute in the admin panel.
        """
        if obj.minute:
            return obj.minute.unique_id  # ✅ Shows the Minute's unique ID
        return "No Linked Minute"

    get_linked_minute.short_description = "Linked Minute"  # ✅ Display name in admin


@admin.register(Approver)
class ApproverAdmin(admin.ModelAdmin):
    """
    Admin panel for Approvers.
    Shows details of each approver in an approval chain.
    """
    list_display = ("user", "approval_chain", "order", "status", "is_current")
    search_fields = ("user__username", "approval_chain__name")
    list_filter = ("status", "approval_chain")
    ordering = ("approval_chain", "order")

    readonly_fields = ("user", "approval_chain", "order", "status", "is_current")
