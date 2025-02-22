from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError


class CustomUserManager(BaseUserManager):
    """
    Custom manager for CustomUser to handle user creation properly.
    """

    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        if not username:
            raise ValueError("Users must have a username")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        """
        Properly handles superuser creation.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Custom user model that extends Django's AbstractUser.
    """

    ROLE_CHOICES = [
        ("Faculty", "Faculty"),
        ("Admin", "Admin"),
        ("Superuser", "Superuser"),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        help_text="Role of the user in the system."
    )

    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text="Department to which the user belongs."
    )

    employee_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Unique Employee ID (can be set or updated later)."
    )

    designation = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profile_pictures/", blank=True, null=True)

    is_active = models.BooleanField(default=True)  # Keep the default active status

    objects = CustomUserManager()  # Attach Custom Manager

    class Meta:
        verbose_name = "Custom User"
        verbose_name_plural = "Custom Users"

    def __str__(self):
        return f"{self.username} ({self.role})"

    def clean(self):
        """
        Ensure the employee_id is unique if provided.
        """
        if self.employee_id:
            existing_user = CustomUser.objects.filter(employee_id=self.employee_id).exclude(pk=self.pk).first()
            if existing_user:
                raise ValidationError({"employee_id": "This Employee ID is already in use."})

    # ✅ Role-Based Helper Methods
    def is_admin(self):
        return self.role == "Admin"

    def is_faculty(self):
        return self.role == "Faculty"

    def is_custom_superuser(self):
        return self.role == "Superuser"  # Avoid overriding Django's `is_superuser`
