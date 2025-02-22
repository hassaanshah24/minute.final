from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    landing_page,
    LoginView,
    LogoutView,
    FacultyDashboardView,
    AdminDashboardView,
    SuperuserDashboardView,
    role_based_redirect_view,
    profile_view,
    profile_edit_view,
)

app_name = 'users'

urlpatterns = [
    # ✅ Authentication Routes
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # ✅ Dashboard Redirect Based on Role
    path('redirect/', role_based_redirect_view, name='redirect_view'),

    # ✅ Role-Specific Dashboards
    path('dashboard/faculty/', FacultyDashboardView.as_view(), name='faculty_dashboard'),
    path('dashboard/admin/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('dashboard/superuser/', SuperuserDashboardView.as_view(), name='superuser_dashboard'),

    # ✅ Profile Management
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', profile_edit_view, name='profile_edit'),

    # ✅ Landing Page (Root URL)
    path('', landing_page, name='landing'),
]

# ✅ Serve Media Files During Development ONLY
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
