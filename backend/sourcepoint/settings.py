"""
SourcePoint Library Management System - Django Settings
=======================================================
Configure your environment variables in .env file before running.
See .env.example for required variables.

Quick Start:
    1. Copy .env.example to .env and fill in your values
    2. Run: python manage.py migrate
    3. Run: python manage.py createsuperuser
    4. Run: python manage.py seed_data  (loads mock data)
    5. Run: python manage.py runserver
"""

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ===========================================================
# SECURITY SETTINGS
# ===========================================================
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-change-this-in-production-sourcepoint-2024')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ===========================================================
# INSTALLED APPLICATIONS
# ===========================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',               # Django REST Framework
    'rest_framework_simplejwt',           # JWT Authentication
    'rest_framework_simplejwt.token_blacklist', # Required for logout token invalidation
    'corsheaders',                  # Cross-Origin Resource Sharing
    'django_filters',               # Advanced filtering

    # SourcePoint apps
    'users',                        # Custom user model & auth
    'library',                      # Books, categories, borrowing
    'ai_assistant',
    'sourcepoint',                                  # AI features powered by Gemini
]

# ===========================================================
# MIDDLEWARE
# ===========================================================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',    # CORS must be first
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sourcepoint.urls'

# ===========================================================
# TEMPLATES
# ===========================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sourcepoint.wsgi.application'

# ===========================================================
# DATABASE - Supabase PostgreSQL
# ===========================================================
# ── DATABASE CONFIGURATION ──────────────────────────────────────────
# Uses Supabase PostgreSQL in production.
# Falls back to SQLite for local development if SUPABASE_DB_HOST is not set.
# This prevents the "unable to translate hostname" crash during development.

_SUPABASE_HOST = os.getenv('SUPABASE_DB_HOST', '')
_SUPABASE_PW = os.getenv('SUPABASE_DB_PASSWORD', '')

if _SUPABASE_HOST and _SUPABASE_PW:
    # Production/staging: use Supabase PostgreSQL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('SUPABASE_DB_NAME', 'postgres'),
            'USER': os.getenv('SUPABASE_DB_USER', 'postgres'),
            'PASSWORD': _SUPABASE_PW,
            'HOST': _SUPABASE_HOST,
            'PORT': os.getenv('SUPABASE_DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',  # Supabase requires SSL
                'connect_timeout': 10,
            },
            'CONN_MAX_AGE': 60,  # connection pooling
        }
    }
else:
    # Development fallback: SQLite (no setup needed)
    # Set SUPABASE_DB_HOST and SUPABASE_DB_PASSWORD in .env to switch to PostgreSQL
    import warnings
    warnings.warn(
        "SUPABASE_DB_HOST not set. Using SQLite for development. "
        "Set SUPABASE_DB_HOST and SUPABASE_DB_PASSWORD in .env for PostgreSQL.",
        stacklevel=2
    )
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Supabase client configuration (for storage and realtime features)
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY', '')  # Use anon key for client-side ops
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '')  # Service key for admin ops
SUPABASE_STORAGE_BUCKET = os.getenv('SUPABASE_STORAGE_BUCKET', 'sourcepoint-books')

# ===========================================================
# CUSTOM USER MODEL
# ===========================================================
AUTH_USER_MODEL = 'users.User'

# ===========================================================
# AUTHENTICATION
# ===========================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ===========================================================
# REST FRAMEWORK CONFIGURATION
# ===========================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# ===========================================================
# JWT SETTINGS
# ===========================================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ===========================================================
# CORS SETTINGS
# ===========================================================
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:8000'
).split(',')

CORS_ALLOW_CREDENTIALS = True

# ===========================================================
# STATIC & MEDIA FILES
# ===========================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise compression and caching
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (uploaded book covers) - served via Supabase Storage in production
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ===========================================================
# INTERNATIONALIZATION
# ===========================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ===========================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ===========================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===========================================================
# AI ASSISTANT - Groq (COMPLETELY FREE — no credit card)
# Sign up at: https://console.groq.com
# Click "Create API Key" — takes 30 seconds
# Free limits: 14,400 requests/day, 6,000 tokens/min
# ===========================================================
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
# Legacy Gemini key (kept for backwards compat — not used if GROQ_API_KEY is set)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# ===========================================================
# LIBRARY SYSTEM SETTINGS
# ===========================================================
# Default maximum borrow period in days (admins can change per-book)
DEFAULT_MAX_BORROW_DAYS = 30

# Maximum books a user can borrow at once
MAX_CONCURRENT_BORROWS = 5

# ===========================================================
# LOGGING
# ===========================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': str(BASE_DIR / 'logs' / 'sourcepoint.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO'},
        'sourcepoint': {'handlers': ['console', 'file'], 'level': 'DEBUG', 'propagate': False},
    },
}

# Create logs directory
os.makedirs(str(BASE_DIR / 'logs'), exist_ok=True)
