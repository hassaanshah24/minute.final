from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from django.db.models import Max
from apps.approval_chain import models
from apps.approval_chain.models import ApprovalChain, Approver
from apps.approval_chain.forms import ApprovalChainForm, ApproverForm, BulkApproverForm

User = get_user_model()

# ✅ Approval Chain List View
class ApprovalChainListView(LoginRequiredMixin, ListView):
    """
    Displays a list of all approval chains created by the logged-in user.
    """
    model = ApprovalChain
    template_name = "approval_chain/list.html"
    context_object_name = "approval_chains"
    ordering = ["-created_at"]

    def get_queryset(self):
        """
        Fetches only chains created by the logged-in user with preloaded approvers.
        """
        return ApprovalChain.objects.filter(created_by=self.request.user).prefetch_related("approvers")

# ✅ Create Approval Chain View
class ApprovalChainCreateView(LoginRequiredMixin, CreateView):
    """
    View to create a new Approval Chain.
    """
    model = ApprovalChain
    form_class = ApprovalChainForm
    template_name = "approval_chain/create.html"
    success_url = reverse_lazy("approval_chain:list")

    def form_valid(self, form):
        """
        Assigns the current user as the creator before saving.
        """
        form.instance.created_by = self.request.user
        messages.success(self.request, "Approval chain created successfully.")
        return super().form_valid(form)

# ✅ Approval Chain Detail View
class ApprovalChainDetailView(LoginRequiredMixin, DetailView):
    model = ApprovalChain
    template_name = "approval_chain/detail.html"
    context_object_name = "approval_chain"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        approval_chain = self.get_object()

        # ✅ Ensure Approvers are always in FIFO order
        context["approvers"] = approval_chain.approvers.order_by("order").select_related("user")

        # ✅ Exclude Already Added Users from the Bulk Selection
        existing_users = approval_chain.approvers.values_list("user_id", flat=True)
        bulk_form = BulkApproverForm(approval_chain=approval_chain)
        bulk_form.fields["users"].queryset = User.objects.exclude(id__in=existing_users).order_by("id")

        context["bulk_approver_form"] = bulk_form
        return context

# ✅ Add Single Approver View

@login_required
def add_approver(request, chain_id):
    """
    Handles adding a single approver to an existing approval chain.
    Ensures correct FIFO order synchronization with bulk approvers.
    """
    approval_chain = get_object_or_404(ApprovalChain, pk=chain_id)

    if request.method == "POST":
        form = ApproverForm(request.POST, approval_chain=approval_chain)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    messages.success(request, "Approver added successfully.")
                    return redirect("approval_chain:detail", pk=chain_id)
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Failed to add approver. Check your inputs.")
    else:
        # ✅ Ensure `form` is initialized even for `GET` requests to avoid UnboundLocalError
        form = ApproverForm(approval_chain=approval_chain)

    # ✅ Synchronize Single & Bulk Approver Forms
    bulk_form = BulkApproverForm(approval_chain=approval_chain)
    bulk_form.fields["users"].queryset = User.objects.exclude(
        id__in=approval_chain.approvers.values_list("user_id", flat=True)
    ).order_by("first_name")

    return render(request, "approval_chain/add_approver.html", {
        "form": form,  # ✅ Now `form` is always defined
        "bulk_approver_form": bulk_form,
        "approval_chain": approval_chain
    })
# ✅ Add Bulk Approvers View
@login_required
def add_bulk_approvers(request, chain_id):
    """
    Handles adding multiple approvers at once with correct FIFO ordering.
    """
    approval_chain = get_object_or_404(ApprovalChain, pk=chain_id)

    if request.method == "POST":
        user_order_data = request.POST.get("order")  # Get userID:orderNumber CSV string

        if not user_order_data:
            messages.error(request, "No users selected.")
            return redirect("approval_chain:detail", pk=chain_id)

        user_order_pairs = [pair.split(":") for pair in user_order_data.split(",")]
        ordered_users = [(int(user_id), int(order)) for user_id, order in user_order_pairs]

        try:
            with transaction.atomic():
                # ✅ Get the last order number (FIFO synchronization)
                last_order = approval_chain.approvers.aggregate(Max("order"))["order__max"] or 0

                for user_id, order in ordered_users:
                    user = get_object_or_404(User, pk=user_id)
                    Approver.objects.create(
                        approval_chain=approval_chain,
                        user=user,
                        order=last_order + order,  # ✅ Ensuring the FIFO sequence is correct
                        status="Pending"
                    )

                messages.success(request, "Approvers added successfully.")
                return redirect("approval_chain:detail", pk=chain_id)

        except ValidationError as e:
            messages.error(request, str(e))

    return redirect("approval_chain:detail", pk=chain_id)

# ✅ Confirm Approval Chain View
@login_required
def confirm_approval_chain(request, chain_id):
    """
    Marks an approval chain as confirmed/finalized.
    """
    approval_chain = get_object_or_404(ApprovalChain, pk=chain_id)

    try:
        with transaction.atomic():
            approval_chain.is_confirmed = True
            approval_chain.save()
            messages.success(request, "Approval chain confirmed successfully.")
    except Exception as e:
        messages.error(request, f"Error confirming approval chain: {str(e)}")

    return redirect("approval_chain:detail", pk=chain_id)

# ✅ Update Approval Chain View
class ApprovalChainUpdateView(LoginRequiredMixin, UpdateView):
    """
    Allows updating an existing approval chain.
    """
    model = ApprovalChain
    form_class = ApprovalChainForm
    template_name = "approval_chain/update.html"
    success_url = reverse_lazy("approval_chain:list")

    def form_valid(self, form):
        """
        Assigns success message before saving the updated chain.
        """
        messages.success(self.request, "Approval chain updated successfully.")
        return super().form_valid(form)

# ✅ Delete Approval Chain View
@method_decorator(login_required, name="dispatch")
class ApprovalChainDeleteView(DeleteView):
    """
    Deletes an approval chain.
    """
    model = ApprovalChain
    template_name = "approval_chain/delete.html"
    success_url = reverse_lazy("approval_chain:list")

    def delete(self, request, *args, **kwargs):
        """
        Assigns success message before deletion.
        """
        messages.success(request, "Approval chain deleted successfully.")
        return super().delete(request, *args, **kwargs)

# ✅ Remove Approver View
@login_required
def remove_approver(request, chain_id, approver_id):
    approval_chain = get_object_or_404(ApprovalChain, pk=chain_id)
    approver = get_object_or_404(Approver, pk=approver_id, approval_chain=approval_chain)

    try:
        with transaction.atomic():
            approver.delete()
            messages.success(request, f"Approver {approver.user.get_full_name()} removed successfully.")

            # ✅ Reorder remaining approvers in FIFO order
            remaining_approvers = approval_chain.approvers.order_by("order")
            for index, approver in enumerate(remaining_approvers, start=1):
                approver.order = index
                approver.save()

    except Exception as e:
        messages.error(request, f"Error removing approver: {str(e)}")

    return redirect("approval_chain:detail", pk=chain_id)
