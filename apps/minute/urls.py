# apps/minute/urls.py
from django.urls import path
from .views import CreateMinuteView, view_minute_detail, minute_action_view, pending_approvals, tracking_minute_view

app_name = "minute"

urlpatterns = [
    path("create/", CreateMinuteView.as_view(), name="create"),  # ✅ Create a new minute
    path("<int:minute_id>/", view_minute_detail, name="detail"),  # ✅ View an existing minute
    path("<int:minute_id>/action/", minute_action_view, name="action"),  # ✅ Approvers take actions
    path("pending/", pending_approvals, name="pending_approvals"),
    path("<int:minute_id>/tracking/", tracking_minute_view, name="tracking"),
]
