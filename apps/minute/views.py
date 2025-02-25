# apps/minute/views.py
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import reverse
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Minute
from .forms import MinuteForm
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.views.generic import DetailView
from apps.minute.models import Minute
from apps.approval_chain.models import ApprovalChain
from apps.approval_chain.models import Approver
from apps.minute.forms import MarkToForm, ReturnToForm
from django.core.exceptions import ValidationError
from django.db import transaction
import logging
logger = logging.getLogger(__name__)



class CreateMinuteView(LoginRequiredMixin, CreateView):
    """
    View to create a new Minute. Automatically assigns the user's department.
    """
    model = Minute
    form_class = MinuteForm
    template_name = "minute/create.html"

    def get_form_kwargs(self):
        """
        Injects the request into the form to validate the user.
        """
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user  # ✅ Pass the logged-in user
        return kwargs

    def form_valid(self, form):
        """
        Automatically assigns the department from the logged-in user before saving.
        Then redirects to create an approval chain for this minute.
        """
        user = self.request.user

        # ✅ Ensure user has a department before proceeding
        if not hasattr(user, "department") or not user.department:
            messages.error(self.request, "You must belong to a department to create a Minute.")
            return render(self.request, self.template_name, {"form": form})  # ✅ Re-render with message

        # ✅ Auto-assign department from the user
        form.instance.department = user.department
        form.instance.created_by = user
        self.object = form.save()

        messages.success(self.request, "Minute created successfully. Now create the Approval Chain.")

        # ✅ Redirect to Approval Chain Creation, passing the Minute ID
        return redirect(reverse("approval_chain:create") + f"?minute_id={self.object.id}")

    def form_invalid(self, form):
        """
        Handles form errors gracefully.
        """
        messages.error(self.request, "There was an error with your submission.")
        return self.render_to_response(self.get_context_data(form=form))


@login_required
def view_minute_detail(request, minute_id):
    """
    Displays the official minute sheet in its university format.
    - Ensures only the minute creator or an assigned approver can view it.
    - Supports real-time approval progress updates.
    - Implements pagination for long descriptions.
    """

    # ✅ Fetch Minute
    minute = get_object_or_404(Minute, pk=minute_id)
    approval_chain = getattr(minute, 'approval_chain', None)

    # ✅ Ensure only the Minute Creator or an Approver can view it
    is_creator = minute.created_by == request.user
    is_approver = approval_chain and approval_chain.approvers.filter(user=request.user).exists()

    if not (is_creator or is_approver):
        return HttpResponseForbidden("You are not authorized to view this minute.")

    # ✅ Read Current Page from GET request
    try:
        page = int(request.GET.get("page", 1))  # Default to page 1
    except ValueError:
        page = 1  # Fallback to prevent errors

    # ✅ Define Words Per Page
    MAX_WORDS_PER_PAGE = 200

    # ✅ Paginate Description
    description_pages = split_description_into_pages(minute.description, MAX_WORDS_PER_PAGE)
    total_pages = len(description_pages)

    # ✅ Ensure Page is Within Range
    page = max(1, min(page, total_pages))

    # ✅ Get Content for Current Page
    current_description = description_pages[page - 1] if description_pages else "No content available."

    # ✅ Fetch Approval Chain & Approvers
    approvers_status = []
    if approval_chain:
        for approver in approval_chain.approvers.order_by('order'):
            approvers_status.append({
                'approver': approver.user.get_full_name(),
                'status': approver.status,
                'is_current': approver.is_current,
            })

    # ✅ Render Page with `minutesheet.html`
    return render(request, "minute/view_minute.html", {
        'minute': minute,
        'approval_chain': approval_chain,
        'approvers_status': approvers_status,
        'current_description': current_description,
        'total_pages': total_pages,
        'current_page': page,
    })


def split_description_into_pages(description, words_per_page=200):
    """
    Automatically splits long descriptions into multiple pages, keeping sentences intact.
    """
    if not description or not isinstance(description, str):
        return ["No description available."]

    words = description.split()
    pages = [" ".join(words[i:i + words_per_page]) for i in range(0, len(words), words_per_page)]

    return pages
# apps/minute/views.py
@login_required
def minute_action_view(request, minute_id):
    """
    Unified View for Approvers to Perform Actions on a Minute:
    - Approve
    - Reject
    - Mark-To (Assign to a new approver)
    - Return-To (Send back to a previous approver)
    """
    minute = get_object_or_404(Minute, pk=minute_id)
    approval_chain = minute.approval_chain

    # ✅ Ensure the minute has an approval chain
    if not approval_chain:
        messages.error(request, "This minute has no approval chain linked.")
        return redirect("minute:tracking", minute_id=minute.id)

    # ✅ Ensure at least one active approver exists
    if not approval_chain.approvers.filter(is_current=True).exists():
        first_approver = approval_chain.approvers.order_by("order").first()
        if first_approver:
            first_approver.is_current = True
            first_approver.save()

    # ✅ Ensure the user is the current approver
    current_approver = approval_chain.approvers.filter(user=request.user, is_current=True).first()
    if not current_approver:
        messages.warning(request, "You are not the current approver for this minute.")
        return redirect("minute:tracking", minute_id=minute.id)

    # ✅ Initialize Forms
    mark_form = MarkToForm(request.POST or None, approval_chain=approval_chain)
    return_form = ReturnToForm(request.POST or None, approval_chain=approval_chain)

    if request.method == "POST":
        action = request.POST.get("action")

        try:
            with transaction.atomic():
                if action == "approve":
                    current_approver.status = "Approved"
                    current_approver.is_current = False
                    current_approver.save()

                    next_approver = approval_chain.approvers.filter(order=current_approver.order + 1, status="Pending").first()

                    if next_approver:
                        next_approver.is_current = True
                        next_approver.save()
                        response_message = f"You approved the minute. Next Approver: {next_approver.user.get_full_name()}."
                    else:
                        # ✅ If last approver, finalize the minute
                        minute.finalize_minute("Approved")
                        response_message = "Minute has been fully approved and archived."

                elif action == "reject":
                    current_approver.status = "Rejected"
                    current_approver.is_current = False
                    current_approver.save()

                    # ✅ Finalize and archive the minute
                    minute.finalize_minute("Rejected")
                    response_message = "Minute has been rejected and archived."

                elif action == "mark_to":
                    if mark_form.is_valid():
                        target_user = mark_form.cleaned_data["user"]
                        target_order = mark_form.cleaned_data["order"]

                        # ✅ Ensure new approver does not break order
                        max_order = approval_chain.approvers.aggregate(models.Max("order"))["order__max"] or 0
                        if target_order > max_order + 1:
                            raise ValidationError(f"Invalid order. Maximum allowed order is {max_order + 1}.")

                        # ✅ Shift existing approvers down if necessary
                        approval_chain.approvers.filter(order__gte=target_order).update(order=models.F("order") + 1)

                        # ✅ Insert new approver
                        new_approver = Approver.objects.create(
                            approval_chain=approval_chain,
                            user=target_user,
                            order=target_order,
                            status="Pending",
                            is_current=True  # ✅ New approver becomes the active approver
                        )

                        # ✅ Update current approver status to "Marked"
                        current_approver.status = "Marked"
                        current_approver.is_current = False
                        current_approver.save()

                        response_message = f"Minute has been assigned to {target_user.get_full_name()} at position {target_order}."
                    else:
                        raise ValidationError("Invalid selection for Mark-To action.")

                elif action == "return_to":
                    if return_form.is_valid():
                        target_user = return_form.cleaned_data["user"]

                        previous_approver = approval_chain.approvers.filter(user=target_user, order__lt=current_approver.order).first()

                        if previous_approver:
                            current_approver.is_current = False
                            current_approver.save()

                            previous_approver.is_current = True
                            previous_approver.status = "Pending"  # ✅ Reset status so they need to approve again
                            previous_approver.save()

                            response_message = f"Minute has been returned to {target_user.get_full_name()}."
                        else:
                            raise ValidationError("Invalid selection for Return-To action.")
                    else:
                        raise ValidationError("Invalid selection for Return-To action.")

                else:
                    raise ValidationError("Invalid action selected.")

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect("minute:tracking", minute_id=minute.id)

        # ✅ FIXED: Always redirect to prevent AJAX error popup
        messages.success(request, response_message)
        return redirect(reverse("minute:tracking", kwargs={"minute_id": minute.id}))

    return render(request, "minute/action.html", {
        "minute": minute,
        "approval_chain": approval_chain,
        "current_approver": current_approver,
        "mark_form": mark_form,
        "return_form": return_form,
    })

from django.db.models import Prefetch, Q

@login_required
def pending_approvals(request):
    """
    View for approvers to see all minutes awaiting their approval.
    """
    # ✅ Fetch all minutes where the user is a current approver
    pending_approvals = Minute.objects.filter(
        approval_chain__approvers__user=request.user,
        approval_chain__approvers__is_current=True,
        approval_chain__approvers__status="Pending"
    ).distinct().prefetch_related(
        Prefetch("approval_chain__approvers", queryset=Approver.objects.order_by("order"))
    )

    return render(request, "minute/pending_approvals.html", {
        "pending_approvals": pending_approvals,
    })

# apps/minute/views.py
@login_required
def tracking_minute_view(request, minute_id):
    """
    View to track a minute's approval process.
    Shows real-time status of approvers and actions taken.
    """
    minute = get_object_or_404(Minute, pk=minute_id)
    approval_chain = minute.approval_chain

    # ✅ Fetch Approvers & Ensure Names Are Available
    approvers_status = approval_chain.approvers.order_by("order").select_related("user").values(
        "user__first_name", "user__last_name", "status", "is_current"
    )

    # ✅ Properly Format Approver Names
    formatted_approvers = [
        {
            "approver": f"{approver['user__first_name']} {approver['user__last_name']}".strip(),
            "status": approver["status"],
            "is_current": approver["is_current"],
        }
        for approver in approvers_status
    ]

    # ✅ Check if Minute is Completed (Approved or Rejected)
    is_finalized = minute.status in ["Approved", "Rejected"]

    return render(request, "minute/tracking.html", {
        "minute": minute,
        "approval_chain": approval_chain,
        "approvers_status": formatted_approvers,  # ✅ Fixed
        "is_finalized": is_finalized
    })
