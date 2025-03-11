from django import forms
from django.core.exceptions import ValidationError
from apps.approval_chain.models import ApprovalChain, Approver
from django.contrib.auth import get_user_model
from django.db.models import Max
User = get_user_model()


# ✅ Form to Create or Update an Approval Chain
class ApprovalChainForm(forms.ModelForm):
    """
    Form to create or update an Approval Chain.
    """

    class Meta:
        model = ApprovalChain
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        """
        Extract the request object for setting the created_by field.
        """
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        """
        Ensure the approval chain name is unique (case-insensitive check).
        """
        name = self.cleaned_data.get("name").strip()

        if ApprovalChain.objects.filter(name__iexact=name).exists():
            raise ValidationError("An approval chain with this name already exists.")

        return name

    def save(self, commit=True):
        """
        Assign the created_by field before saving.
        """
        instance = super().save(commit=False)

        if self.request and hasattr(self.request, "user"):
            instance.created_by = self.request.user

        if commit:
            instance.save()
        return instance


# ✅ Form to Add a Single Approver
from django.db.models import F

class ApproverForm(forms.ModelForm):
    """
    Form to add a single approver to an Approval Chain (Supports Mark-To Functionality).
    """

    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Select a user as an approver"
    )

    order = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Order of the approver in the chain"
    )

    class Meta:
        model = Approver
        fields = ["user", "order"]

    def __init__(self, *args, **kwargs):
        """
        Extracts the approval chain and sets up initial validation.
        """
        self.approval_chain = kwargs.pop("approval_chain", None)
        super().__init__(*args, **kwargs)

        if self.approval_chain:
            existing_orders = self.approval_chain.approvers.values_list("order", flat=True)
            suggested_order = max(existing_orders, default=0) + 1
            self.fields["order"].initial = suggested_order

        # ✅ Exclude: Minute Creator, Existing Approvers, & Already Approved Users
        if self.approval_chain:
            existing_users = self.approval_chain.approvers.values_list("user", flat=True)
            already_approved_users = self.approval_chain.approvers.filter(status="Approved").values_list("user", flat=True)

            self.fields["user"].queryset = User.objects.exclude(
                id__in=list(existing_users) + list(already_approved_users)
            ).exclude(id=self.approval_chain.created_by.id)

    def clean(self):
        """
        Validates the selected user and order.
        """
        cleaned_data = super().clean()
        target_user = cleaned_data.get("user")
        target_order = cleaned_data.get("order")

        if not target_user:
            raise ValidationError("Please select a valid user.")

        # ✅ Ensure target_order is valid
        max_existing_order = self.approval_chain.approvers.aggregate(Max("order"))["order__max"] or 0
        if target_order > max_existing_order + 1:
            raise ValidationError(f"Invalid order. Maximum order allowed is {max_existing_order + 1}.")

        return cleaned_data

    def save(self, commit=True):
        """
        Saves the Mark-To action by inserting a new approver.
        """
        instance = super().save(commit=False)

        if self.approval_chain:
            instance.approval_chain = self.approval_chain

            # ✅ Shift existing approvers down when inserting a new approver
            if self.approval_chain.approvers.filter(order=instance.order).exists():
                self.approval_chain.approvers.filter(order__gte=instance.order).update(order=F("order") + 1)

        if commit:
            instance.save()
        return instance


# ✅ Form to Add Multiple Approvers at Once
class BulkApproverForm(forms.Form):
    """
    Form to add multiple approvers at once in FIFO order.
    """
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.SelectMultiple(attrs={"class": "form-control select2"}),
        help_text="Select multiple users to be added as approvers"
    )

    order = forms.CharField(widget=forms.HiddenInput(), required=False)  # ✅ Store selection order

    def __init__(self, *args, **kwargs):
        self.approval_chain = kwargs.pop("approval_chain", None)
        super().__init__(*args, **kwargs)

        if self.approval_chain:
            existing_users = self.approval_chain.approvers.values_list("user_id", flat=True)
            available_users = User.objects.exclude(id__in=existing_users).order_by("id")

            self.fields["users"].queryset = available_users
            if not available_users.exists():
                self.fields["users"].help_text = "No available users to add."

    def save(self):
        """
        Bulk save selected approvers in FIFO order.
        """
        if not self.approval_chain:
            raise ValidationError("Approval chain not found.")

        selected_users = self.cleaned_data["users"]
        selection_order = self.cleaned_data["order"]

        # ✅ Convert order string to a list of IDs
        selection_order_list = list(map(int, selection_order.split(","))) if selection_order else []

        # ✅ Assign order based on selection sequence
        new_approvers = []
        for idx, user in enumerate(selected_users):
            order_number = selection_order_list[idx] if idx < len(selection_order_list) else idx + 1
            new_approvers.append(
                Approver(
                    approval_chain=self.approval_chain,
                    user=user,
                    order=order_number,
                    status="Pending",
                    is_current=(order_number == 1)
                )
            )

        Approver.objects.bulk_create(new_approvers)
