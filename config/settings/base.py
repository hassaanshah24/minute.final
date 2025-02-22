from pathlib import Path
import environ
import os

# Base directory path
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize environment variables
env = environ.Env(DEBUG=(bool, False))

# Explicitly read the .env file from the root directory
environ.Env.read_env(BASE_DIR / ".env")

# Database configuration
DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')
}

SECRET_KEY = env("SECRET_KEY", default="dummy-secret-key")
DEBUG = env("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

# Installed apps
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.users",
    "apps.departments",
    "widget_tweaks",
    "rest_framework",
    'rest_framework_simplejwt',# Django REST Framework
    "channels",
    "corsheaders",

]

# Middleware
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'apps.users.middleware.RoleBasedRedirectMiddleware',

]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"  # For Django Channels

# Channels Configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],  # Redis server for WebSocket communication
        },
    },
}

# Templates and Static files
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

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

AUTH_USER_MODEL = 'users.CustomUser'


LOGIN_URL = '/users/login/'  # Ensure this exists
LOGIN_REDIRECT_URL = '/users/redirect/'  # Redirects to the correct URL
LOGOUT_REDIRECT_URL = '/'  # Redirect to landing page after logout


# Disable CSRF for API requests using JWT authentication
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}
CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8000']
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Add the BASE_URL setting
BASE_URL = 'http://127.0.0.1:8000'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',  # Change DEBUG to WARNING to suppress logs
            'class': 'logging.FileHandler',
            'filename': 'django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'WARNING',  # Change from DEBUG to WARNING
            'propagate': False,
        },
    },
}


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

PDFKIT_CONFIG = {
    'wkhtmltopdf': r"C:\Users\ESHOP\wkhtmltopdf\bin\wkhtmltopdf.exe"  # Make sure this path is correct
}

WKHTMLTOPDF_PATH = r"C:\Users\ESHOP\wkhtmltopdf\bin\wkhtmltopdf.exe"
