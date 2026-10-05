from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager
import secrets
import hashlib






class UserManager(BaseUserManager):
    """Manager for email-based User."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


# Create your models here.
class User(AbstractUser):
    """
    Email-based user. Removes username field, uses email as unique identifier.
    Compatible with allauth (ACCOUNT_USER_MODEL_USERNAME_FIELD=None) and
    Google OAuth (socialaccount creates user via email).
    """

    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female")
    ]

    username = None
    email = models.EmailField("email address", unique=True)
    gender = models.CharField(choices=GENDER_CHOICES, max_length=10, default="Male")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email



class UserInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_info')
    full_name = models.CharField(max_length=255, blank=True, null=True)
    user_information = models.TextField( blank=True, null=True)
    education = models.JSONField(default=list, blank=True, null=True)
    projects = models.JSONField(default=list, blank=True, null=True)
    skills = models.JSONField(default=list, blank=True, null=True)
    hobbies = models.JSONField(default=list, blank=True, null=True)
    contact_information = models.JSONField(default=list, blank=True, null=True)

    def __str__(self):
        return f"Info - {self.user.email}"



