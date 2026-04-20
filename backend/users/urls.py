"""
SourcePoint Users URL Configuration
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Public authentication endpoints
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User profile management
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('account/delete/', views.DeleteAccountView.as_view(), name='delete_account'),

    # Admin user management
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<uuid:user_id>/suspend/', views.SuspendUserView.as_view(), name='suspend_user'),
    path('users/<uuid:user_id>/unsuspend/', views.UnsuspendUserView.as_view(), name='unsuspend_user'),
    path('users/<uuid:user_id>/delete/', views.DeleteUserView.as_view(), name='delete_user'),

    # Superadmin admin management
    path('admins/', views.AdminManageView.as_view(), name='create_admin'),
    path('admins/<uuid:user_id>/', views.AdminManageView.as_view(), name='delete_admin'),

    # Mock data management
    path('mock-data/', views.ClearMockUsersView.as_view(), name='clear_mock_users'),
]
