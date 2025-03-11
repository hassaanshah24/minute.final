# apps/remarks/admin.py
from django.contrib import admin
from apps.remarks.models import Remark


@admin.register(Remark)
class RemarkAdmin(admin.ModelAdmin):
    """
    Efficient admin panel configuration for the Remark model.
    """

    list_display = ("user", "minute", "action", "text", "timestamp")  # ✅ Corrected 'timestamp' field
    list_filter = ("action", "user", "minute")  # ✅ Filters for quick search
    search_fields = ("user__username", "user__first_name", "user__last_name", "minute__unique_id", "text")  # ✅ Search bar
    ordering = ("-timestamp",)  # ✅ Show latest remarks first
    readonly_fields = ("user", "minute", "approver", "action", "text", "timestamp")  # ✅ Now correctly references model fields
    list_per_page = 25  # ✅ Pagination for better performance

    def has_add_permission(self, request):
        """ Disable manual remark creation from admin panel. """
        return False  # ✅ Prevent adding remarks manually

    def has_change_permission(self, request, obj=None):
        """ Disable editing remarks in the admin panel. """
        return False  # ✅ Prevent accidental edits

    def has_delete_permission(self, request, obj=None):
        """ Allow deleting remarks if needed. """
        return True  # ✅ Admins can delete remarks if required
