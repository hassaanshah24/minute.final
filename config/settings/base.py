from pathlib import Path
import environ
import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

os.add_dll_directory("C:/GTK/bin")

# ✅ *Base directory path*
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ✅ *Initialize environment variables*
env = environ.Env(DEBUG=(bool, False))

# ✅ *Read the .env file*
environ.Env.read_env(BASE_DIR / ".env")

# ✅ *Security & Secret Key*
SECRET_KEY = env("SECRET_KEY", default="dummy-secret-key")
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

# ✅ *Database Configuration*
DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3")
}

# ✅ *Sentry Integration for Error Tracking*
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True,
    )

# ✅ *Redis Cache Configuration (With Fallback)*
REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/1")
USE_REDIS = True

try:
    # Test Redis Connection
    import redis
    r = redis.StrictRedis.from_url(REDIS_URL)
    r.ping()
except (redis.ConnectionError, ImportError):
    print("⚠ Redis is not running. Using local memory cache instead.")
    USE_REDIS = False

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache" if USE_REDIS else "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": REDIS_URL if USE_REDIS else "unique-snowflake",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        } if USE_REDIS else {},
    }
}

# ✅ *Installed Apps*
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.users",
    "apps.minute",
    "apps.departments",
    "apps.remarks",
    "widget_tweaks",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",  # API Documentation
    "channels",
    "corsheaders",
    "axes",
    'apps.approval_chain',
    "django_extensions",
    "django_ckeditor_5",
]

# ✅ *Middleware*
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",  # Brute-force prevention
    "apps.users.middleware.RoleBasedRedirectMiddleware",
]

# ✅ *ASGI & WebSockets Configuration*
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ✅ *Django Channels & Redis for WebSockets (Handles Redis Failure)*
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer" if USE_REDIS else "channels.layers.InMemoryChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL] if USE_REDIS else [],
        } if USE_REDIS else {},
    },
}

# ✅ *Templates & Static Files*
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ✅ *Authentication & Authorization*
AUTH_USER_MODEL = "users.CustomUser"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "axes.backends.AxesBackend",  # Prevent brute-force login attempts
]

LOGIN_URL = "/users/login/"
LOGIN_REDIRECT_URL = "/users/redirect/"
LOGOUT_REDIRECT_URL = "/"

# ✅ *Django Rest Framework & JWT Authentication*
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",  # API Docs
}

# ✅ *JWT Token Configuration*
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# ✅ *CSRF & CORS Settings*
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:8000"]
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

# ✅ *Session Engine (Handles Redis Failure)*
SESSION_ENGINE = "django.contrib.sessions.backends.cache" if USE_REDIS else "django.contrib.sessions.backends.db"
SESSION_CACHE_ALIAS = "default"

# ✅ *Logging for better debugging*
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": "django.log",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": True,
        },
        "django.db.backends": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# ✅ *CKEditor Configuration (Fixed)*
CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": "full",
        "height": 300,
        "width": "100%",
    }
}

# ✅ *PDF Generation*
PDFKIT_CONFIG = {
    "wkhtmltopdf": r"C:\Users\ESHOP\wkhtmltopdf\bin\wkhtmltopdf.exe"
}
WKHTMLTOPDF_PATH = r"C:\Users\ESHOP\wkhtmltopdf\bin\wkhtmltopdf.exe"

# ✅ *DRF Spectacular Settings (API Documentation)*
SPECTACULAR_SETTINGS = {
    "TITLE": "Minute 2.0 API",
    "DESCRIPTION": "API documentation for Minute 2.0 using DRF Spectacular",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA":False,
}
AXES_FAILURE_LIMIT = 10  # Increase the failure limit before lockout
AXES_COOLOFF_TIME = None  # Remove automatic cooldown
AXES_RESET_ON_SUCCESS = True  # Reset failed attempts on successful login


# settings.py
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ✅ Define the CKEditor upload path
CKEDITOR_UPLOAD_PATH = "uploads/ckeditor/"