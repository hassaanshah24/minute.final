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
class ApproverForm(forms.ModelForm):
    """
    Form to add a single approver to an Approval Chain.
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

        # Auto-assign the next available order if not manually assigned
        if self.approval_chain:
            existing_orders = self.approval_chain.approvers.values_list("order", flat=True)
            suggested_order = max(existing_orders, default=0) + 1
            self.fields["order"].initial = suggested_order

        # ✅ Ensure the dropdown does not show users already in the approval chain
        if self.approval_chain:
            existing_users = self.approval_chain.approvers.values_list("user", flat=True)
            self.fields["user"].queryset = User.objects.exclude(id__in=existing_users)

    def clean_user(self):
        """
        Ensure the selected user is not already an approver.
        """
        user = self.cleaned_data.get("user")

        if self.approval_chain and Approver.objects.filter(approval_chain=self.approval_chain, user=user).exists():
            raise ValidationError(f"{user.get_full_name()} is already an approver in this chain.")

        return user

    def clean_order(self):
        """
        Ensure the order number is unique within the approval chain.
        """
        order = self.cleaned_data.get("order")

        if self.approval_chain and Approver.objects.filter(approval_chain=self.approval_chain, order=order).exists():
            raise ValidationError(f"An approver with order {order} already exists.")

        return order

    def save(self, commit=True):
        """
        Assign the approval chain before saving.
        """
        instance = super().save(commit=False)

        if self.approval_chain:
            instance.approval_chain = self.approval_chain

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
