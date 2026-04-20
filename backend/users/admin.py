from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserPreference

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'status', 'date_joined']
    list_filter = ['role', 'status']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('first_name', 'last_name', 'bio', 'avatar')}),
        ('Access', {'fields': ('role', 'status', 'is_active', 'is_staff', 'is_superuser')}),
        ('Admin Notes', {'fields': ('admin_note', 'suspension_reason', 'is_mock_data')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'password1', 'password2', 'role')}),
    )

admin.site.register(UserPreference)
