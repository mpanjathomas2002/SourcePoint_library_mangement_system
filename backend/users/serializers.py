"""
SourcePoint Users - Serializers
=================================
Handles serialization/deserialization of User data for the REST API.
Includes validation for email format, password strength, and role limits.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserPreference
import re


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for new user registration.
    Validates email format and password strength.
    No email verification token needed - just valid email format.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name']

    def validate_email(self, value):
        """Validate email format and uniqueness."""
        # Basic email format check
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise serializers.ValidationError("Please enter a valid email address.")

        # Check uniqueness
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("An account with this email already exists.")

        return value.lower()

    def validate(self, attrs):
        """Cross-field validation - ensure passwords match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        """Create new user, removing the confirm field first."""
        validated_data.pop('password_confirm')
        return User.objects.create_user(**validated_data)


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login via email and password."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Authenticate user credentials."""
        email = attrs.get('email', '').lower()
        password = attrs.get('password')

        # Find user by email first to give better error messages
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email address.")

        # Check account status before authenticating
        if user.status == 'suspended':
            raise serializers.ValidationError(
                f"Your account has been suspended. Reason: {user.suspension_reason or 'Contact admin.'}"
            )
        if user.status == 'deleted':
            raise serializers.ValidationError("This account has been deleted.")

        # Authenticate password
        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Incorrect password. Please try again.")

        attrs['user'] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for reading and updating user profile.
    Excludes sensitive fields like password.
    """
    full_name = serializers.SerializerMethodField()
    borrowed_count = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'status', 'bio', 'avatar', 'avatar_url',
            'date_joined', 'last_login', 'borrowed_count',
        ]
        read_only_fields = ['id', 'email', 'role', 'status', 'date_joined', 'last_login']

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_borrowed_count(self, obj):
        """Return number of currently borrowed books."""
        return obj.borrowings.filter(status='active').count()

    def get_avatar_url(self, obj):
        """Return full URL for avatar image."""
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
        return None


class AdminUserListSerializer(serializers.ModelSerializer):
    """
    Serializer for admin views of user list.
    Includes more fields than the public profile.
    """
    full_name = serializers.SerializerMethodField()
    borrow_stats = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'first_name', 'last_name',
            'role', 'status', 'date_joined', 'last_login',
            'is_mock_data', 'admin_note', 'suspension_reason',
            'suspended_at', 'borrow_stats',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_borrow_stats(self, obj):
        """Return borrowing statistics for admin view."""
        borrowings = obj.borrowings.all()
        return {
            'total': borrowings.count(),
            'active': borrowings.filter(status='active').count(),
            'overdue': borrowings.filter(status='overdue').count(),
            'returned': borrowings.filter(status='returned').count(),
        }


class AdminCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for superadmin creating new admin accounts.
    Enforces the 5-admin limit.
    """
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'role']

    def validate_role(self, value):
        """Ensure role is admin (not superadmin - only one superadmin allowed)."""
        if value not in ('admin', 'user'):
            raise serializers.ValidationError("Role must be 'admin' or 'user'.")
        return value

    def validate(self, attrs):
        """Check the 5-admin limit before creating."""
        if attrs.get('role') == 'admin':
            admin_count = User.objects.filter(role='admin', status='active').count()
            if admin_count >= 5:
                raise serializers.ValidationError(
                    "Maximum of 5 admin accounts allowed. Remove an existing admin first."
                )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        if validated_data.get('role') == 'admin':
            user.is_staff = True
        user.save()
        return user


class UserPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for user preferences."""

    class Meta:
        model = UserPreference
        fields = ['favorite_categories', 'preferred_language',
                  'email_notifications', 'due_date_reminders']
