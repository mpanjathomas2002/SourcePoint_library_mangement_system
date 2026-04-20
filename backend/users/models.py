"""
SourcePoint Users App - Models
================================
Custom User model with role-based access control.

Roles:
    - user: Regular library member (default)
    - admin: Library administrator (5 slots)
    - superadmin: Full system access (1 slot)

Status:
    - active: Normal account
    - suspended: Blocked by admin (cannot login)
    - deleted: Soft-deleted (data retained for audit)
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import uuid


class UserManager(BaseUserManager):
    """Custom manager for the SourcePoint User model."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with email and password."""
        if not email:
            raise ValueError('Email address is required')

        # Normalize email (lowercase domain part)
        email = self.normalize_email(email)

        # Set default role to 'user' if not specified
        extra_fields.setdefault('role', 'user')
        extra_fields.setdefault('is_active', True)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a super admin user. Only one should exist."""
        extra_fields.setdefault('role', 'superadmin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('role') != 'superadmin':
            raise ValueError('Superuser must have role=superadmin.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    SourcePoint custom user model.
    Uses email as the unique identifier instead of username.
    """

    # Role choices - determines dashboard and permissions
    ROLE_CHOICES = [
        ('user', 'User'),               # Regular library member
        ('admin', 'Admin'),             # Library administrator
        ('superadmin', 'Super Admin'),  # Full system access
    ]

    # Account status choices
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),    # Admin blocked the account
        ('deleted', 'Deleted'),        # Soft-deleted
    ]

    # Primary identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Authentication fields
    email = models.EmailField(unique=True, db_index=True)

    # Profile information
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True, max_length=500)

    # Role-based access control
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user', db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Django required fields for AbstractBaseUser
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Access to Django admin

    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Mock data flag - makes it easy to identify and remove seed data
    is_mock_data = models.BooleanField(default=False, help_text="True for seeded test data")

    # Admin note - admins can add notes about users
    admin_note = models.TextField(blank=True, help_text="Internal notes by admin")

    # Suspension reason
    suspension_reason = models.TextField(blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_by = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='suspended_users'
    )

    # Required by AbstractBaseUser
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = 'sp_users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}> [{self.role}]"

    def get_full_name(self):
        """Return first + last name, or email if names not set."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email.split('@')[0]

    def get_short_name(self):
        """Return first name or email prefix."""
        return self.first_name or self.email.split('@')[0]

    @property
    def is_admin(self):
        """True for both admin and superadmin roles."""
        return self.role in ('admin', 'superadmin')

    @property
    def is_superadmin(self):
        """True only for superadmin role."""
        return self.role == 'superadmin'

    @property
    def is_suspended(self):
        """True if account is suspended."""
        return self.status == 'suspended'

    def suspend(self, reason, suspended_by_user):
        """Suspend a user account."""
        self.status = 'suspended'
        self.suspension_reason = reason
        self.suspended_at = timezone.now()
        self.suspended_by = suspended_by_user
        self.is_active = False
        self.save(update_fields=['status', 'suspension_reason', 'suspended_at', 'suspended_by', 'is_active'])

    def unsuspend(self):
        """Restore a suspended account."""
        self.status = 'active'
        self.suspension_reason = ''
        self.suspended_at = None
        self.suspended_by = None
        self.is_active = True
        self.save(update_fields=['status', 'suspension_reason', 'suspended_at', 'suspended_by', 'is_active'])

    def soft_delete(self):
        """Soft delete - mark as deleted but retain data for audit."""
        self.status = 'deleted'
        self.is_active = False
        self.save(update_fields=['status', 'is_active'])


class UserPreference(models.Model):
    """
    Stores user preferences for the library system.
    One-to-one relationship with User.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')

    # Reading preferences
    favorite_categories = models.JSONField(default=list, blank=True)
    preferred_language = models.CharField(max_length=50, default='English')

    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    due_date_reminders = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sp_user_preferences'

    def __str__(self):
        return f"Preferences for {self.user.email}"
