from django.contrib import admin
from .models import Department
from django.utils.html import format_html


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """
    Custom Admin Panel for Managing Departments.
    """
    list_display = ('name', 'code', 'head_of_department', 'dean', 'user_count', 'created_by', 'created_at')
    search_fields = ('name', 'code', 'head_of_department__username', 'head_of_department__first_name',
                     'head_of_department__last_name', 'dean__username', 'dean__first_name', 'dean__last_name')
    list_filter = ('created_at', 'updated_at', 'head_of_department', 'dean')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'user_count')
    ordering = ['name', '-created_at']

    fieldsets = (
        ("Basic Information", {
            'fields': ('name', 'description', 'code', 'head_of_department', 'dean')
        }),
        ("Metadata", {
            'fields': ('created_by', 'user_count', 'created_at', 'updated_at'),
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Auto-assign created_by when a new department is created.
        """
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """
        Prevent deletion if the department has assigned users.
        """
        if obj.users.exists():
            self.message_user(request, "This department has assigned users and cannot be deleted.", level='error')
        else:
            super().delete_model(request, obj)

    def user_count(self, obj):
        """
        Display the number of users in the department.
        """
        return obj.users.count()

    user_count.short_description = "Users"

    def get_readonly_fields(self, request, obj=None):
        """
        Make `code` read-only after the department is created.
        """
        if obj:
            return self.readonly_fields + ('code',)
        return self.readonly_fields
