from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Ensure the root URL serves the landing page from the users app
    path('', include('apps.users.urls', namespace='users')),

    # Other app routes
    path('users/', include('apps.users.urls', namespace='users')),  # Users app
    path('departments/', include('apps.departments.urls', namespace='departments')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
