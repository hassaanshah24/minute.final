# apps/minute/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.minute.models import Minute
from apps.approval_chain.models import Approver, ApprovalChain
from django.db import models


User = get_user_model()


# ✅ Minute Creation Form
class MinuteForm(forms.ModelForm):
    """
    Form for creating a new Minute.
    The department is automatically assigned from the logged-in user.
    """

    class Meta:
        model = Minute
        fields = ["subject", "description", "attachment"]  # ✅ Now includes attachment
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter subject"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "Enter description"}),
        }

    def __init__(self, *args, **kwargs):
        """
        Override init to accept `user` argument and auto-assign department.
        """
        self.user = kwargs.pop("user", None)  # ✅ Extract user from kwargs
        super().__init__(*args, **kwargs)

    def clean(self):
        """
        Ensure that the user belongs to a department before saving.
        """
        cleaned_data = super().clean()

        if not self.user or not hasattr(self.user, "department") or not self.user.department:
            raise ValidationError("You must belong to a department to create a Minute.")

        return cleaned_data

    def save(self, commit=True):
        """
        Automatically assigns department and creator before saving.
        """
        instance = super().save(commit=False)
        instance.created_by = self.user
        instance.department = self.user.department  # ✅ Auto-assign department

        if commit:
            instance.save()
        return instance


# ✅ Approve/Reject Form (With Optional Remarks)
class ApprovalActionForm(forms.Form):
    """
    Form for approving or rejecting a minute.
    Allows optional remarks for better tracking.
    """
    remarks = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        required=False,
        help_text="Optional remarks on your decision."
    )

    action = forms.ChoiceField(
        choices=[("approve", "Approve"), ("reject", "Reject")],
        widget=forms.RadioSelect,
        help_text="Select action: Approve or Reject."
    )

    def __init__(self, *args, **kwargs):
        self.minute = kwargs.pop("minute", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        """
        Validates that the user is the current approver.
        """
        if not self.minute or not self.user:
            raise ValidationError("Invalid request.")

        current_approver = self.minute.approval_chain.approvers.filter(user=self.user, is_current=True).first()

        if not current_approver:
            raise ValidationError("You are not authorized to take action on this minute.")

        return self.cleaned_data

    def save(self):
        """
        Saves the approve/reject action.
        """
        action = self.cleaned_data["action"]

        if action == "approve":
            self.minute.approve(self.user)
        else:
            self.minute.reject(self.user)

from django.db.models import F


class MarkToForm(forms.Form):
    """
    Allows the current approver to assign the minute to a new approver.
    Excludes the minute creator, existing approvers, and already approved users.
    """

    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Select New Approver",
        help_text="Choose a user to forward this minute to.",
        widget=forms.Select(attrs={"class": "form-control", "required": "required"}),  # ✅ Ensures proper form submission
    )

    order = forms.IntegerField(
        min_value=1,
        label="Approval Order",
        help_text="Select the order in which the new approver should be placed.",
        widget=forms.NumberInput(attrs={"class": "form-control", "required": "required"}),  # ✅ Ensures required field
    )

    def __init__(self, *args, **kwargs):
        self.approval_chain = kwargs.pop("approval_chain", None)
        super().__init__(*args, **kwargs)

        if self.approval_chain:
            # ✅ Exclude: Minute Creator, Existing Approvers, & Already Approved Users
            existing_approvers = self.approval_chain.approvers.values_list("user_id", flat=True)
            already_approved_users = self.approval_chain.approvers.filter(status="Approved").values_list("user_id", flat=True)

            self.fields["user"].queryset = User.objects.exclude(
                id__in=list(existing_approvers) + list(already_approved_users)
            ).exclude(id=self.approval_chain.created_by.id)

    def clean_user(self):
        """
        Ensures that a valid user is selected and that they are not already in the approval chain.
        Fixes cases where an empty string is appended in POST data.
        """
        user = self.cleaned_data.get("user")

        # ✅ Fix: If user is coming as a list, extract only valid IDs
        if isinstance(user, list):
            user = next((u for u in user if u), None)  # Get first valid user, ignore empty values

        if not user:
            raise ValidationError("Please select a valid user.")

        if self.approval_chain.approvers.filter(user=user).exists():
            raise ValidationError(f"{user.get_full_name()} is already an approver.")

        return user

    def clean_order(self):
        """
        Ensures the order number is within the valid range.
        """
        order = self.cleaned_data.get("order")

        # ✅ Get max existing order, default to 0 if none exist
        max_existing_order = self.approval_chain.approvers.aggregate(models.Max("order"))["order__max"] or 0

        if order > max_existing_order + 1:
            raise ValidationError(f"Invalid order. Maximum order allowed is {max_existing_order + 1}.")

        return order

    def save(self, current_approver):
        """
        Saves the mark-to action and inserts a new approver in the chain.
        """
        target_user = self.cleaned_data["user"]
        target_order = self.cleaned_data["order"]

        # ✅ Ensure existing orders are shifted correctly
        if self.approval_chain.approvers.filter(order=target_order).exists():
            self.approval_chain.approvers.filter(order__gte=target_order).update(order=F("order") + 1)

        # ✅ Insert New Approver (New approver should be active)
        new_approver = Approver.objects.create(
            approval_chain=self.approval_chain,
            user=target_user,
            order=target_order,
            status="Pending",
            is_current=True  # ✅ New approver takes control
        )

        # ✅ Update Current Approver (Mark them as "Marked" & Deactivate)
        current_approver.status = "Marked"
        current_approver.is_current = False
        current_approver.save()

        return new_approver



# ✅ Return-To Form (Reverts the minute to a previous approver)
class ReturnToForm(forms.Form):
    """
    Allows the current approver to return the minute to a previous approver in the chain.
    """
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Select Previous Approver",
        help_text="Choose a previous approver to return the minute to.",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        approval_chain = kwargs.pop("approval_chain", None)
        super().__init__(*args, **kwargs)

        if approval_chain:
            previous_approvers = approval_chain.approvers.filter(order__lt=approval_chain.approvers.filter(is_current=True).first().order)
            self.fields["user"].queryset = User.objects.filter(id__in=previous_approvers.values_list("user_id", flat=True))

    def clean(self):
        """
        Validates the selected previous approver.
        """
        cleaned_data = super().clean()
        target_user = cleaned_data.get("user")

        if not target_user:
            raise ValidationError("Please select a valid previous approver.")

        return cleaned_data

    def save(self, approval_chain, current_approver):
        """
        Saves the return-to action by reverting to a previous approver.
        """
        target_user = self.cleaned_data["user"]
        previous_approver = approval_chain.approvers.filter(user=target_user, order__lt=current_approver.order).first()

        if previous_approver:
            current_approver.is_current = False
            current_approver.save()

            previous_approver.is_current = True
            previous_approver.status = "Pending"  # ✅ Reset status so they need to approve again
            previous_approver.save()

            return previous_approver
        else:
            raise ValidationError("Invalid previous approver selected.")
