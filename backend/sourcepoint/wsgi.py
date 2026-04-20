"""
WSGI config for SourcePoint project.
Used by Gunicorn for production deployment.
Deploy command: gunicorn sourcepoint.wsgi:application --bind 0.0.0.0:8000
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sourcepoint.settings')
application = get_wsgi_application()
