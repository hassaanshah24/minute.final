# apps/minute/views.py
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import reverse
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from weasyprint.css.validation.properties import string_set
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
from django.db.models import F, Max
import logging
logger = logging.getLogger(__name__)
import weasyprint
from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import get_object_or_404
from apps.remarks.forms import RemarkForm

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

    # ✅ Fetch Remarks for this minute
    remarks = Remark.objects.filter(minute=minute).order_by("-timestamp")  # Latest remarks first
    print(f"✅ DEBUG: Loaded {remarks.count()} remarks for Minute ID {minute_id}")  # 🔥 Debugging

    # ✅ Render Page with `minutesheet.html`
    return render(request, "minute/view_minute.html", {
        'minute': minute,
        'approval_chain': approval_chain,
        'approvers_status': approvers_status,
        'current_description': current_description,
        'total_pages': total_pages,
        'current_page': page,
        'remarks': remarks,
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

@login_required
def minute_action_view(request, minute_id):
    """
    Unified View for Approvers to Perform Actions on a Minute:
    - Approve
    - Reject
    - Mark-To (Assign to a new approver)
    - Return-To (Send back to a previous approver)
    """
    logger.info(f"🔍 DEBUG: Accessing minute_action_view for Minute ID: {minute_id}")

    minute = get_object_or_404(Minute, pk=minute_id)
    approval_chain = minute.approval_chain

    if not approval_chain:
        messages.error(request, "This minute has no approval chain linked.")
        logger.warning(f"⚠️ WARNING: Minute {minute_id} has no approval chain.")
        return redirect("minute:tracking", minute_id=minute.id)

    # ✅ Ensure at least one active approver exists
    current_approver = approval_chain.approvers.filter(user=request.user, is_current=True).first()
    if not current_approver:
        messages.warning(request, "You are not the current approver for this minute.")
        logger.warning(f"⚠️ WARNING: User {request.user} is not the current approver for Minute {minute_id}.")
        return redirect("minute:tracking", minute_id=minute.id)

    logger.info(f"✅ DEBUG: Current Approver Found - {current_approver.user.get_full_name()}")

    # ✅ Initialize Forms
    mark_form = MarkToForm(request.POST or None, approval_chain=approval_chain)
    return_form = ReturnToForm(request.POST or None, approval_chain=approval_chain)
    remark_form = RemarkForm(request.POST or None)  # ✅ New Remark Form

    if request.method == "POST":
        action = request.POST.get("action")
        logger.info(f"✅ DEBUG: Action Received - {action}")
        logger.info(f"✅ DEBUG: Request POST Data - {request.POST}")

        # ✅ Extract remark_text directly from request.POST
        remark_text = request.POST.get("remark_text", "").strip()
        logger.info(f"✅ DEBUG: Extracted Remark Text - '{remark_text}'")

        try:
            with transaction.atomic():
                if action == "approve":
                    logger.info("✅ DEBUG: Processing 'approve' action...")
                    response_message = approve_minute(current_approver, approval_chain, minute, remark_text)

                elif action == "reject":
                    logger.info("✅ DEBUG: Processing 'reject' action...")
                    response_message = reject_minute(current_approver, minute, remark_text)

                elif action == "mark_to":
                    logger.info("✅ DEBUG: Processing 'mark_to' action...")
                    mark_form = MarkToForm(request.POST, approval_chain=approval_chain)

                    if mark_form.is_valid():
                        response_message = mark_to_new_approver(
                            request, mark_form, current_approver, approval_chain, remark_text
                        )
                    else:
                        messages.error(request, "Invalid selection for Mark-To action.")
                        logger.warning(f"⚠️ WARNING: Invalid Mark-To form! Errors: {mark_form.errors}")
                        return redirect("minute:tracking", minute_id=minute.id)

                elif action == "return_to":
                    logger.info("✅ DEBUG: Processing 'return_to' action...")
                    response_message = return_to_previous_approver(
                        request, return_form, current_approver, approval_chain, remark_text
                    )

                else:
                    logger.error(f"❌ ERROR: Invalid action selected: {action}")
                    raise ValidationError("Invalid action selected.")

        except ValidationError as e:
            messages.error(request, str(e))
            logger.error(f"❌ ERROR: ValidationError occurred - {str(e)}")
            return redirect("minute:tracking", minute_id=minute.id)

        # ✅ Save Remark

        logger.info(f"✅ DEBUG: Remark Saved Successfully - User: {request.user.get_full_name()}, Action: {action}, Text: {remark_text}")

        # ✅ Always Redirect to Prevent Errors
        messages.success(request, response_message)
        logger.info(f"✅ SUCCESS: {response_message}")
        return redirect(reverse("minute:tracking", kwargs={"minute_id": minute.id}))

    return render(request, "minute/action.html", {
        "minute": minute,
        "approval_chain": approval_chain,
        "current_approver": current_approver,
        "mark_form": mark_form,
        "return_form": return_form,
        "remark_form": remark_form,  # ✅ Include Remark Form in the template
    })


### **✅ Updated Helper Functions to Save Remarks**
from apps.remarks.models import Remark


def save_remark(user, minute, action, text):
    """
    Saves a remark for the given action taken on a minute.
    Ensures that the action is valid and prevents duplicate remarks.
    """

    # ✅ Ensure action is correctly formatted
    valid_actions = {
        "approve": "Approve",
        "reject": "Reject",
        "mark_to": "Mark-To",
        "return_to": "Return-To",
    }

    formatted_action = valid_actions.get(action.lower())

    if not formatted_action:
        print(f"❌ ERROR: Invalid action '{action}' passed to save_remark()")
        return

    # ✅ Retrieve the correct approver instance
    approver = Approver.objects.filter(user=user, approval_chain=minute.approval_chain).first()

    if not approver:
        print(f"❌ ERROR: Approver not found for User: {user.get_full_name()} on Minute: {minute.unique_id}")
        return

    # ✅ Prevent duplicate remarks for the same action
    existing_remark = Remark.objects.filter(
        user=user, minute=minute, action=formatted_action, text=text
    ).exists()

    if existing_remark:
        print(
            f"⚠️ WARNING: Duplicate Remark Detected! Skipping save for User: {user.get_full_name()} on Minute: {minute.unique_id}")
        return

    # ✅ Save the remark properly
    remark = Remark.objects.create(
        user=user,
        minute=minute,
        approver=approver,
        action=formatted_action,
        text=text.strip() if text else None
    )

    print(f"✅ DEBUG: Remark saved successfully! ID: {remark.id}, Action: {formatted_action}, Text: {remark.text}")


def approve_minute(current_approver, approval_chain, minute, remark_text):
    """
    Handles minute approval by moving to the next approver or finalizing it.
    """
    current_approver.status = "Approved"
    current_approver.is_current = False
    current_approver.save()

    save_remark(current_approver.user, minute, "approve", remark_text)  # ✅ Save remark

    # ✅ Move to the next approver
    next_approver = approval_chain.approvers.filter(order=current_approver.order + 1, status="Pending").first()

    if next_approver:
        next_approver.is_current = True
        next_approver.save()
        return f"You approved the minute. Next Approver: {next_approver.user.get_full_name()}."

    # ✅ Finalize minute if no more approvers
    minute.finalize_minute("Approved")
    return "Minute has been fully approved and archived."


def reject_minute(current_approver, minute, remark_text):
    """
    Handles minute rejection and finalizes it.
    """
    current_approver.status = "Rejected"
    current_approver.is_current = False
    current_approver.save()

    save_remark(current_approver.user, minute, "reject", remark_text)  # ✅ Save remark

    minute.finalize_minute("Rejected")
    return "Minute has been rejected and archived."



def mark_to_new_approver(request, mark_form, current_approver, approval_chain, remark_text):
    """
    Handles forwarding the minute to a new approver.
    """
    if not mark_form.is_valid():
        raise ValidationError("Invalid selection for Mark-To action.")

    target_user = mark_form.cleaned_data["user"]
    target_order = mark_form.cleaned_data["order"] or \
                   (approval_chain.approvers.aggregate(Max("order"))["order__max"] or 0) + 1

    if approval_chain.approvers.filter(user=target_user).exists():
        raise ValidationError(f"{target_user.get_full_name()} is already an approver.")

    # ✅ Get the minute linked to the approval chain
    minute = approval_chain.minute  # 🔥 FIX: Ensure minute is properly retrieved

    # ✅ Shift existing approvers down by 1
    approval_chain.approvers.filter(order__gte=target_order).update(order=F("order") + 1)

    # ✅ Create new approver at the specified order
    new_approver = Approver.objects.create(
        approval_chain=approval_chain,
        user=target_user,
        order=target_order,
        status="Pending",
        is_current=True
    )

    # ✅ Mark the current approver as "Marked" and deactivate
    current_approver.status = "Marked"
    current_approver.is_current = False
    current_approver.save()

    save_remark(current_approver.user, minute, "mark_to", remark_text)  # ✅ FIXED: minute is now properly passed

    return f"Minute assigned to {target_user.get_full_name()} at position {target_order}."


def return_to_previous_approver(request, return_form, current_approver, approval_chain, remark_text):
    """
    Handles returning the minute to a previous approver.
    """
    if not return_form.is_valid():
        raise ValidationError("Invalid selection for Return-To action.")

    target_user = return_form.cleaned_data["user"]
    previous_approver = approval_chain.approvers.filter(user=target_user, order__lt=current_approver.order).first()

    if not previous_approver:
        raise ValidationError("Invalid selection for Return-To action.")

    # ✅ Get the minute linked to the approval chain
    minute = approval_chain.minute  # 🔥 FIX: Ensure minute is properly retrieved

    # ✅ Deactivate current approver
    current_approver.is_current = False
    current_approver.status = "Returned"
    current_approver.save()

    previous_approver.is_current = True
    previous_approver.status = "Pending"
    previous_approver.save()

    save_remark(current_approver.user, minute, "return_to", remark_text)  # ✅ FIXED: minute is now properly passed

    return f"Minute returned to {target_user.get_full_name()}."

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

    # ✅ Fetch all remarks related to this minute
    remarks = Remark.objects.filter(minute=minute).select_related("user").order_by("-timestamp")

    # ✅ Check if Minute is Completed (Approved or Rejected)
    is_finalized = minute.status in ["Approved", "Rejected"]

    return render(request, "minute/tracking.html", {
        "minute": minute,
        "approval_chain": approval_chain,
        "approvers_status": formatted_approvers,  # ✅ Fixed
        "remarks": remarks,  # ✅ Added this
        "is_finalized": is_finalized
    })

from PyPDF2 import PdfReader, PdfWriter
import os
from PIL import Image
import pandas as pd
import io

@login_required
def generate_minute_pdf(request, minute_id):
    """
    Generates a PDF of the official Minute Sheet and appends attachments (PDF, images, Excel).
    """
    # ✅ Fetch the specific minute entry
    minute = get_object_or_404(Minute, id=minute_id)

    # ✅ Fetch Approval Chain and Approvers
    approval_chain = getattr(minute, 'approval_chain', None)
    approvers_status = []

    if approval_chain:
        approvers = approval_chain.approvers.order_by('order').select_related("user")
        for approver in approvers:
            approvers_status.append({
                'approver': approver.user.get_full_name(),
                'status': approver.status,
                'is_current': approver.is_current,
            })

    # ✅ Fetch all remarks related to this minute
    remarks = Remark.objects.filter(minute=minute).select_related("user").order_by("-timestamp")

    # ✅ Load the PDF template
    template = get_template('minute/minutesheet_pdf.html')

    # ✅ Context to pass into the template
    context = {
        'minute': minute,
        'approvers_status': approvers_status,
        'remarks': remarks,  # ✅ Pass remarks to template
        'sheet_no': "DYNAMIC_SHEET_NO",  # This will be replaced dynamically
    }
    html_content = template.render(context)

    # ✅ Generate PDF from HTML with proper pagination
    main_pdf_bytes = weasyprint.HTML(string=html_content).write_pdf(
        stylesheets=[weasyprint.CSS(string='''  
            @page {
                size: A4 portrait;
                margin: 1in;

                /* ✅ Dynamic Page Numbering */
                @bottom-center {
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 10pt;
                    font-family: "Times New Roman", serif;
                }

                /* ✅ Dynamic Sheet Number */
                @top-right {
                    content: "Sheet: " counter(page);
                    font-weight: bold;
                    font-size: 12pt;
                    font-family: "Times New Roman", serif;
                }
            }

            body {
                font-family: 'Times New Roman', serif;
                font-size: 12pt;
                line-height: 1.5;
            }
        ''')]
    )

    # ✅ Convert `bytes` to `BytesIO` file-like object
    main_pdf_io = io.BytesIO(main_pdf_bytes)
    pdf_writer = PdfWriter()
    pdf_writer.append(PdfReader(main_pdf_io))  # ✅ Add the main minute PDF first

    # ✅ Handle attachments
    if minute.attachment:
        attachment_path = minute.attachment.path
        attachment_ext = os.path.splitext(attachment_path)[1].lower()

        if attachment_ext == ".pdf":
            # ✅ Append PDF directly
            with open(attachment_path, "rb") as f:
                attachment_reader = PdfReader(f)
                for page in attachment_reader.pages:
                    pdf_writer.add_page(page)

        elif attachment_ext in [".png", ".jpg", ".jpeg"]:
            # ✅ Convert image to PDF and append
            image = Image.open(attachment_path)
            img_pdf_io = io.BytesIO()
            image.convert("RGB").save(img_pdf_io, format="PDF")
            img_pdf_io.seek(0)
            img_reader = PdfReader(img_pdf_io)
            pdf_writer.append(img_reader)

        elif attachment_ext in [".xls", ".xlsx"]:
            # ✅ Convert Excel to PDF Table & Append
            try:
                if attachment_ext == ".xls":
                    df = pd.read_excel(attachment_path, engine="xlrd")  # ✅ Ensure xlrd for .xls
                else:
                    df = pd.read_excel(attachment_path, engine="openpyxl")  # ✅ Ensure openpyxl for .xlsx

                table_html = df.to_html(index=False, border=1)
                excel_pdf_bytes = weasyprint.HTML(string=f"<h3>Excel Attachment</h3>{table_html}").write_pdf()
                excel_pdf_io = io.BytesIO(excel_pdf_bytes)
                excel_reader = PdfReader(excel_pdf_io)
                pdf_writer.append(excel_reader)

            except Exception as e:
                print(f"Error processing Excel file: {e}")  # ✅ Log errors for debugging

    # ✅ Write final PDF file
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Minute_{minute.unique_id}.pdf"'
    pdf_writer.write(response)
    return response

