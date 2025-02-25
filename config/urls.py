# project/urls.py (Main URL Configuration)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # ✅ Set users app for root and keep namespace unique
    path('', include('apps.users.urls')),  # No namespace here
    path('users/', include('apps.users.urls')),  # No namespace here

    # ✅ Other app routes with unique namespaces
    path('minute/', include('apps.minute.urls', namespace='minute')),
    path('departments/', include('apps.departments.urls', namespace='departments')),
    path("approval-chain/", include("apps.approval_chain.urls", namespace="approval_chain")),
]

# ✅ Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
