from django.db.models import Q
"""
SourcePoint Users - Views
===========================
Authentication and user management API endpoints.

Endpoints:
    POST /api/v1/auth/register/     - New user registration
    POST /api/v1/auth/login/        - Login, returns JWT tokens
    POST /api/v1/auth/logout/       - Logout (blacklist refresh token)
    POST /api/v1/auth/token/refresh/ - Refresh access token
    GET  /api/v1/auth/profile/      - Get current user profile
    PUT  /api/v1/auth/profile/      - Update profile
    DELETE /api/v1/auth/account/    - Delete own account (soft delete)
    GET  /api/v1/auth/users/        - Admin: list all users
    POST /api/v1/auth/users/<id>/suspend/ - Admin: suspend user
    POST /api/v1/auth/users/<id>/unsuspend/ - Admin: unsuspend user
    DELETE /api/v1/auth/users/<id>/ - Superadmin: delete user
    POST /api/v1/auth/admins/       - Superadmin: create admin
    DELETE /api/v1/auth/admins/<id>/ - Superadmin: delete admin
"""

import logging
from django.utils import timezone
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User, UserPreference
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer,
    UserProfileSerializer, AdminUserListSerializer,
    AdminCreateSerializer, UserPreferenceSerializer
)
from .permissions import IsAdmin, IsSuperAdmin

logger = logging.getLogger('sourcepoint')


def get_tokens_for_user(user):
    """Generate JWT access and refresh tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class RegisterView(APIView):
    """
    POST /api/v1/auth/register/
    Public endpoint - anyone can register.
    Creates a new user account with role='user'.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Create default preferences for new user
            UserPreference.objects.create(user=user)

            # Generate tokens so user is immediately logged in
            tokens = get_tokens_for_user(user)

            logger.info(f"New user registered: {user.email}")

            return Response({
                'message': 'Account created successfully! Welcome to SourcePoint.',
                'user': UserProfileSerializer(user, context={'request': request}).data,
                'tokens': tokens,
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Public endpoint - authenticate with email and password.
    Returns JWT tokens and user profile.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # Update last login timestamp
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            tokens = get_tokens_for_user(user)

            logger.info(f"User logged in: {user.email} [{user.role}]")

            return Response({
                'message': f'Welcome back, {user.get_short_name()}!',
                'user': UserProfileSerializer(user, context={'request': request}).data,
                'tokens': tokens,
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Blacklists the refresh token to invalidate the session.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Logged out successfully.'})
        except TokenError:
            # Token already invalid - that's fine
            return Response({'message': 'Logged out.'})


class ProfileView(APIView):
    """
    GET  /api/v1/auth/profile/ - Retrieve current user's profile
    PUT  /api/v1/auth/profile/ - Update profile (name, bio, avatar)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def put(self, request):
        # Only allow updating safe fields (not role or email)
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully.',
                'user': serializer.data,
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteAccountView(APIView):
    """
    DELETE /api/v1/auth/account/
    Allows users to delete their own account (soft delete).
    Active borrowings are automatically returned.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user

        # Prevent superadmin from self-deleting
        if user.is_superadmin:
            return Response(
                {'error': 'Super admin account cannot be self-deleted.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Return any active borrowings
        active_borrowings = user.borrowings.filter(status='active')
        for borrowing in active_borrowings:
            borrowing.status = 'returned'
            borrowing.returned_at = timezone.now()
            borrowing.save()

        # Soft delete the account
        user.soft_delete()

        logger.info(f"User self-deleted account: {user.email}")

        return Response({'message': 'Your account has been deleted. We hope to see you again!'})


class UserListView(generics.ListAPIView):
    """
    GET /api/v1/auth/users/
    Admin only: List all users with filtering and search.
    """
    serializer_class = AdminUserListSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        queryset = User.objects.exclude(role='superadmin').order_by('-date_joined')

        # Filter by role
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)

        # Filter by status
        user_status = self.request.query_params.get('status')
        if user_status:
            queryset = queryset.filter(status=user_status)

        # Search by name or email
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        return queryset


class SuspendUserView(APIView):
    """
    POST /api/v1/auth/users/<user_id>/suspend/
    Admin: Suspend a user account.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, user_id):
        try:
            # Admins cannot suspend other admins (only superadmin can)
            user = User.objects.get(id=user_id)

            if user.role in ('admin', 'superadmin') and not request.user.is_superadmin:
                return Response(
                    {'error': 'Only the super admin can suspend admin accounts.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            reason = request.data.get('reason', 'Suspended by admin.')
            user.suspend(reason, request.user)

            logger.info(f"User {user.email} suspended by {request.user.email}. Reason: {reason}")

            return Response({'message': f'User {user.get_full_name()} has been suspended.'})

        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)


class UnsuspendUserView(APIView):
    """
    POST /api/v1/auth/users/<user_id>/unsuspend/
    Admin: Restore a suspended user account.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.unsuspend()

            logger.info(f"User {user.email} unsuspended by {request.user.email}")

            return Response({'message': f'User {user.get_full_name()} account has been restored.'})

        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)


class DeleteUserView(APIView):
    """
    DELETE /api/v1/auth/users/<user_id>/
    SuperAdmin only: Permanently soft-delete a user.
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)

            # Prevent deleting self
            if user == request.user:
                return Response(
                    {'error': 'You cannot delete your own super admin account.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.soft_delete()
            logger.info(f"User {user.email} deleted by superadmin {request.user.email}")

            return Response({'message': f'User {user.get_full_name()} has been deleted.'})

        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)


class AdminManageView(APIView):
    """
    POST   /api/v1/auth/admins/       - Create a new admin (superadmin only)
    DELETE /api/v1/auth/admins/<id>/  - Delete an admin (superadmin only)
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        """Create a new admin account."""
        serializer = AdminCreateSerializer(data=request.data)
        if serializer.is_valid():
            admin = serializer.save()

            # Create preferences for admin too
            UserPreference.objects.get_or_create(user=admin)

            logger.info(f"New admin created: {admin.email} by superadmin {request.user.email}")

            return Response({
                'message': f'Admin account created for {admin.email}',
                'admin': AdminUserListSerializer(admin).data,
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        """Delete (soft) an admin account."""
        try:
            admin = User.objects.get(id=user_id, role='admin')
            admin.soft_delete()

            logger.info(f"Admin {admin.email} deleted by superadmin {request.user.email}")

            return Response({'message': f'Admin {admin.get_full_name()} has been removed.'})

        except User.DoesNotExist:
            return Response({'error': 'Admin not found.'}, status=status.HTTP_404_NOT_FOUND)


class ClearMockUsersView(APIView):
    """
    DELETE /api/v1/auth/mock-data/
    Admin: Clear all mock/seed user data.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def delete(self, request):
        deleted_count = User.objects.filter(is_mock_data=True).delete()[0]
        logger.info(f"Mock users cleared by {request.user.email}. Count: {deleted_count}")
        return Response({
            'message': f'Removed {deleted_count} mock user records.',
        })
