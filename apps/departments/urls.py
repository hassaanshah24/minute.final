from django.urls import path
from .views import department_dashboard, department_list_api  # ✅ Correct import

app_name = 'departments'

urlpatterns = [
    # ✅ Department Dashboard (Superusers Only)
    path('dashboard/', department_dashboard, name='dashboard'),

    # ✅ API Endpoint: Fetch list of departments
    path('api/list/', department_list_api, name='department_list_api'),
]
