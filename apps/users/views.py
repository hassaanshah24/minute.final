import logging
from django.contrib.auth.views import LoginView as BaseLoginView, LogoutView as BaseLogoutView
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.users.forms import ProfileUpdateForm
from apps.departments.models import Department

# ✅ Enable logging
logger = logging.getLogger(__name__)


class LoginView(BaseLoginView):
    """
    Custom Login View with improved error handling & redirects.
    """
    template_name = "users/login.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, "You are already logged in.")
            return redirect(reverse('users:redirect_view'))  # Redirect logged-in users to dashboard
        return super().get(request, *args, **kwargs)

    def form_invalid(self, form):
        """
        Handle invalid login attempts with error messages.
        """
        messages.error(self.request, "Invalid username or password. Please try again.")
        return super().form_invalid(form)


class LogoutView(BaseLogoutView):
    """
    Logout View with Logging & Redirect
    """
    next_page = '/'

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"User {request.user.username} logged out.")
        messages.success(request, "You have been logged out successfully.")
        return super().dispatch(request, *args, **kwargs)


# ✅ DASHBOARDS BASED ON ROLE
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
    return render(request, 'users/templates/landing.html')
