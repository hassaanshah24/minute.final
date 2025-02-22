from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.validators import RegexValidator
from .models import CustomUser
from apps.departments.models import Department

# ✅ Custom Validator for Phone Number (Ensures only digits & correct length)
phone_validator = RegexValidator(
    regex=r'^\d{10,15}$',
    message="Phone number must be between 10-15 digits."
)

class CustomLoginForm(AuthenticationForm):
    """
    Custom Login Form with better UI styling.
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control shadow-sm bg-white rounded-3',
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control shadow-sm bg-white rounded-3',
            'placeholder': 'Password'
        })
    )

class CustomUserAdminForm(forms.ModelForm):
    """
    Admin form for managing users with department and role selection.
    """
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(),  # Lazy loading for efficiency
        required=False,
        help_text="Select a department for the user.",
        widget=forms.Select(attrs={
            'class': 'form-control shadow-sm bg-white rounded-3'
        })
    )

    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,  # Assuming roles are defined in CustomUser model
        widget=forms.Select(attrs={
            'class': 'form-control shadow-sm bg-white rounded-3'
        })
    )

    class Meta:
        model = CustomUser
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        """
        Override init to dynamically populate department choices.
        """
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.all()

    def clean_employee_id(self):
        """
        Ensure employee ID is unique.
        """
        employee_id = self.cleaned_data.get('employee_id')
        if CustomUser.objects.filter(employee_id=employee_id).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(f"A user with employee ID '{employee_id}' already exists.")
        return employee_id


class ProfileUpdateForm(forms.ModelForm):
    """
    User profile update form for editing personal details.
    """
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(),  # Lazy loaded
        required=False,
        help_text="Select a department.",
        widget=forms.Select(attrs={
            'class': 'form-control shadow-sm bg-white rounded-3'
        })
    )

    profile_picture = forms.ImageField(
        required=False,
        help_text="Upload a profile picture.",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control shadow-sm bg-white rounded-3'
        })
    )

    phone_number = forms.CharField(
        validators=[phone_validator],  # Ensures only valid phone numbers
        widget=forms.TextInput(attrs={
            'class': 'form-control shadow-sm bg-white rounded-3',
            'placeholder': 'Phone Number'
        })
    )

    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,  # Dropdown for role selection
        widget=forms.Select(attrs={
            'class': 'form-control shadow-sm bg-white rounded-3'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['email', 'designation', 'phone_number', 'department', 'profile_picture', 'role']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control shadow-sm bg-white rounded-3',
                'placeholder': 'Email'
            }),
            'designation': forms.TextInput(attrs={
                'class': 'form-control shadow-sm bg-white rounded-3',
                'placeholder': 'Designation'
            }),
        }

    def __init__(self, *args, **kwargs):
        """
        Override init to dynamically populate department choices.
        """
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.all()

    def clean_email(self):
        """
        Ensure email is unique among users.
        """
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
