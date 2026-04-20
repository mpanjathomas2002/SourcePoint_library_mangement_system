# permissions.py
"""
SourcePoint - Custom DRF Permissions
======================================
Role-based permission classes for API views.
"""

from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allow access to admin and superadmin roles only."""
    message = "You must be an admin to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ('admin', 'superadmin')
        )


class IsSuperAdmin(BasePermission):
    """Allow access to superadmin role only."""
    message = "Only the super admin can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'superadmin'
        )


class IsAdminOrReadOnly(BasePermission):
    """Allow read access to anyone, write access to admins only."""

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in ('admin', 'superadmin')
        )
