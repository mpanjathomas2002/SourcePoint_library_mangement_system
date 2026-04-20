"""
SourcePoint URL Configuration
==============================
All API routes are prefixed with /api/v1/
Frontend routes serve the main SPA template.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Django admin (for super admin low-level access)
    path('django-admin/', admin.site.urls),

    # API Routes - versioned for future compatibility
    path('api/v1/auth/', include('users.urls')),
    path('api/v1/library/', include('library.urls')),
    path('api/v1/ai/', include('ai_assistant.urls')),

    # Catch-all: serve the single-page app for all non-API routes
    # The frontend handles routing via JavaScript
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('<path:path>', TemplateView.as_view(template_name='index.html'), name='spa'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
