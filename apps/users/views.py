# views.py
import logging

from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters

from django.contrib.auth.views import LoginView as BaseLoginView, LogoutView as BaseLogoutView
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.users.forms import ProfileUpdateForm
from apps.departments.models import Department

logger = logging.getLogger(__name__)


class LoginView(BaseLoginView):
    template_name = "users/login.html"
    redirect_authenticated_user = True

    @method_decorator(sensitive_post_parameters('password'))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        """ Handles failed login attempts and shows proper error messages """
        error_messages = {
            'invalid_login': "Invalid username or password.",
            'inactive': "This account is inactive. Contact admin.",
            'locked': "Your account has been temporarily locked due to too many failed login attempts. Try again later.",
        }

        # Default error message
        message = error_messages['invalid_login']

        for error in form.errors.get('__all__', []):
            if 'locked' in error.lower():
                message = error_messages['locked']
            elif 'inactive' in error.lower():
                message = error_messages['inactive']

        # Show error inside the login form
        return self.render_to_response(self.get_context_data(form=form, error_message=message))


class LogoutView(BaseLogoutView):
    """
    Logout View with Logging & Redirect
    """
    next_page = '/'

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"User {request.user.username} logged out.")
        messages.success(request, "You have been logged out successfully.")
        return super().dispatch(request, *args, **kwargs)


# DASHBOARDS BASED ON ROLE
class FacultyDashboardView(LoginRequiredMixin, TemplateView):
    """ Faculty Dashboard """
    template_name = "users/dashboard_faculty.html"


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """ Admin Dashboard """
    template_name = "users/dashboard_admin.html"


class SuperuserDashboardView(LoginRequiredMixin, TemplateView):
    """ Superuser Dashboard """
    template_name = "users/dashboard_superuser.html"


@login_required
def role_based_redirect_view(request):
    """
    Redirect users to their dashboard based on role.
    """
    if request.user.is_superuser:
        return redirect(reverse('users:superuser_dashboard'))
    elif request.user.is_admin():
        return redirect(reverse('users:admin_dashboard'))
    elif request.user.is_faculty():
        return redirect(reverse('users:faculty_dashboard'))

    messages.warning(request, "No valid role assigned. Redirecting to home.")
    return redirect('/')


@login_required
def profile_view(request):
    """ Displays the user's profile. """
    return render(request, 'users/profile_view.html', {'user': request.user})


@login_required
def profile_edit_view(request):
    """
    Allows users to edit their profile with AJAX support.
    """
    user = request.user

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            logger.info(f"User {user.username} updated their profile.")
            return redirect(reverse('users:profile'))
        else:
            messages.error(request, "Error updating profile. Please correct the errors below.")
    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, 'users/profile_edit.html', {'form': form, 'user': user})


def landing_page(request):
    """
    Landing Page:
    - Redirects authenticated users to their dashboard.
    - Shows the landing page to anonymous users.
    """
    if request.user.is_authenticated:
        return redirect(reverse('users:redirect_view'))
    return render(request, 'users/landing.html')