import logging
from django.shortcuts import redirect
from django.urls import reverse_lazy

# ✅ Enable logging for debugging
logger = logging.getLogger(__name__)

class RoleBasedRedirectMiddleware:
    """
    Redirect authenticated users to their respective dashboards based on role.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        Handle role-based redirection for authenticated users.
        """
        # ✅ Skip API paths & static files for performance
        if request.path.startswith('/api/') or request.path.startswith('/static/'):
            return self.get_response(request)

        # ✅ Redirect users from default Django `/accounts/profile/`
        if request.user.is_authenticated and request.path == '/accounts/profile/':
            role = getattr(request.user, 'role', None)  # ✅ Avoids attribute errors

            # ✅ Role-Based Redirections
            role_redirects = {
                "Superuser": reverse_lazy('users:superuser_dashboard'),
                "Faculty": reverse_lazy('users:faculty_dashboard'),
                "Admin": reverse_lazy('users:admin_dashboard'),
            }

            # ✅ Determine redirect path
            redirect_path = role_redirects.get(role, reverse_lazy('users:default_dashboard'))

            logger.info(f"User {request.user.username} redirected to {redirect_path}")  # ✅ Logging

            return redirect(redirect_path)

        return self.get_response(request)
