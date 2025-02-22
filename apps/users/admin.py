# apps/users/admin.py

import logging
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from .models import CustomUser
from apps.departments.models import Department

# ✅ Enable logging for user actions
logger = logging.getLogger(__name__)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Enhanced Admin configuration for the CustomUser model with Department integration.
    """

    fieldsets = UserAdmin.fieldsets + (
        ('Additional Information', {
            'fields': ('role', 'department', 'designation', 'employee_id', 'phone_number'),
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Information', {
            'fields': ('role', 'department', 'designation', 'employee_id', 'phone_number'),
        }),
    )

    # ✅ Enhanced list display with more details
    list_display = ['username', 'email', 'role', 'department', 'designation', 'employee_id', 'phone_number', 'is_staff']
    list_filter = ['role', 'department', 'is_active']

    # ✅ Added phone number to search fields
    search_fields = ['username', 'email', 'department__name', 'employee_id', 'phone_number']

    # ✅ Optimized related data fetching for performance
    autocomplete_fields = ['department']  # Enables autocomplete for departments

    def save_model(self, request, obj, form, change):
        """
        Override save_model to ensure the uniqueness of employee_id and handle custom logic.
        """
        if not change and obj.employee_id and CustomUser.objects.filter(employee_id=obj.employee_id).exists():
            raise ValidationError("A user with this Employee ID already exists.")

        obj.clean()  # Ensure model validation.

        super().save_model(request, obj, form, change)
        logger.info(f"Admin {request.user.username} updated user: {obj.username}")

    def get_queryset(self, request):
        """
        Optimize queryset to prefetch related departments and enhance performance.
        """
        queryset = super().get_queryset(request)
        return queryset.select_related('department')

    def delete_model(self, request, obj):
        """
        Custom delete logic to log admin actions.
        """
        logger.warning(f"Admin {request.user.username} deleted user: {obj.username}")
        super().delete_model(request, obj)
