# apps/remarks/forms.py

from django import forms
from apps.remarks.models import Remark

class RemarkForm(forms.ModelForm):
    """
    A simple form to allow approvers to add optional remarks when taking action.
    """

    text = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Enter your remarks..."}),
        required=False,  # ✅ Remarks are optional
        help_text="You can provide a reason or comment for your action."
    )

    class Meta:
        model = Remark
        fields = ["text"]
