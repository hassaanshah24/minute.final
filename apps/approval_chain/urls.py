from django.urls import path
from apps.approval_chain.views import (
    ApprovalChainListView,
    ApprovalChainCreateView,
    ApprovalChainDetailView,
    ApprovalChainUpdateView,
    ApprovalChainDeleteView,
    add_approver,
    add_bulk_approvers,
    remove_approver,
    confirm_approval_chain,  # ✅ Add the missing view
)

app_name = "approval_chain"

urlpatterns = [
    path("", ApprovalChainListView.as_view(), name="list"),
    path("create/", ApprovalChainCreateView.as_view(), name="create"),
    path("<int:pk>/", ApprovalChainDetailView.as_view(), name="detail"),
    path("<int:pk>/update/", ApprovalChainUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", ApprovalChainDeleteView.as_view(), name="delete"),
    path("<int:chain_id>/add_approver/", add_approver, name="add_approver"),
    path("<int:chain_id>/add_bulk_approvers/", add_bulk_approvers, name="add_bulk_approvers"),
    path("<int:chain_id>/remove_approver/<int:approver_id>/", remove_approver, name="remove_approver"),
    path("<int:pk>/confirm/", confirm_approval_chain, name="confirm"),  # ✅ Fix: Add missing route
]
