from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from .models import Department


def is_superuser(user):
    """
    Helper function to check if the user is a superuser.
    """
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(is_superuser)
def department_dashboard(request):
    """
    Dashboard to view all departments and their details.
    Accessible only to superusers.
    """
    # Fetch departments with optimized queries
    departments = Department.objects.select_related("head_of_department", "dean").all()

    context = {
        "departments": departments,
        "total_departments": departments.count(),
        "department_heads": departments.filter(head_of_department__isnull=False).count(),
        "departments_without_heads": departments.filter(head_of_department__isnull=True).count(),
        "departments_without_deans": departments.filter(dean__isnull=True).count(),
    }

    return render(request, "departments/dashboard.html", context)


@login_required
@user_passes_test(is_superuser)
def department_list_api(request):
    """
    API Endpoint: Returns a list of departments.
    Accessible only to superusers.
    """
    departments = Department.objects.all().values(
        "id", "name", "code", "description", "head_of_department__username", "dean__username"
    )

    response_data = {
        "departments": list(departments),
        "total_departments": departments.count(),
        "department_heads": Department.objects.filter(head_of_department__isnull=False).count(),
        "departments_without_heads": Department.objects.filter(head_of_department__isnull=True).count(),
        "departments_without_deans": Department.objects.filter(dean__isnull=True).count(),
    }

    return JsonResponse(response_data, safe=False)
