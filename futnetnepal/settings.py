"""
Django settings for futnetnepal.

All sensitive and environment-specific values come from `.env` (python-decouple).
Copy `.env.example` to `.env` and adjust per environment.
"""

from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_path(name, default_relative):
    raw = config(name, default='')
    if not raw:
        return BASE_DIR / default_relative
    path = Path(raw)
    return path if path.is_absolute() else BASE_DIR / path


def _env_url(name, default):
    value = config(name, default=default)
    return value if value.endswith('/') else f'{value}/'


def _csv(name, default=''):
    raw = config(name, default=default, cast=Csv())
    return [item.strip() for item in raw if item and item.strip()]


# ——— Core ———
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

_allowed_hosts = _csv('ALLOWED_HOSTS')
if _allowed_hosts:
    ALLOWED_HOSTS = _allowed_hosts
elif DEBUG:
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '[::1]']
else:
    ALLOWED_HOSTS = []

if not DEBUG and not ALLOWED_HOSTS:
    raise ValueError('Set ALLOWED_HOSTS in .env for production (comma-separated).')

if not DEBUG and SECRET_KEY in ('', 'change-me', 'change-me-in-production'):
    raise ValueError('Set a strong SECRET_KEY in .env before running in production.')

# ——— Apps ———
INSTALLED_APPS = [
    'daphne',
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'channels',
    'apps.api',
    'apps.accounts',
    'apps.core',
    'apps.blogs',
    'apps.posts',
    'ckeditor',
    'ckeditor_uploader',
]

AUTHENTICATION_BACKENDS = [
    'apps.accounts.backends.EmailOrUsernameBackend',
    'django.contrib.auth.backends.ModelBackend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.accounts.middleware.EmailVerificationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'futnetnepal.urls'

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
                'apps.accounts.context_processors.user_profile',
            ],
        },
    },
]

WSGI_APPLICATION = 'futnetnepal.wsgi.application'
ASGI_APPLICATION = 'futnetnepal.asgi.application'

# ——— Redis / Channels ———
_redis_url = config('REDIS_URL', default='')
if not _redis_url:
    _redis_password = config('REDIS_PASSWORD', default='')
    if _redis_password:
        _redis_host = config('REDIS_HOST', default='127.0.0.1')
        _redis_port = config('REDIS_PORT', default=6379, cast=int)
        _redis_url = f'redis://:{_redis_password}@{_redis_host}:{_redis_port}/0'

if _redis_url:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [_redis_url]},
        },
    }
else:
    if not DEBUG:
        import warnings
        warnings.warn(
            'REDIS_URL is not set; WebSockets use in-memory channel layer (single process only).',
            stacklevel=1,
        )
    CHANNEL_LAYERS = {
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'},
    }

# ——— Database ———
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

_database_url = config('DATABASE_URL', default='')
_use_sqlite = config('USE_SQLITE', default=DEBUG, cast=bool) or (
    _database_url and 'sqlite' in _database_url.lower()
)

if _use_sqlite:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        },
    }
else:
    _db_engine = config('DB_ENGINE', default='django.db.backends.mysql')
    if _db_engine == 'mysql':
        _db_engine = 'django.db.backends.mysql'

    _db_options = {'charset': 'utf8mb4'}
    if 'mysql' in _db_engine:
        _db_options['init_command'] = "SET sql_mode='STRICT_TRANS_TABLES'"

    DATABASES = {
        'default': {
            'ENGINE': _db_engine,
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='127.0.0.1'),
            'PORT': config('DB_PORT', default='3306', cast=int),
            'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=60 if not DEBUG else 0, cast=int),
            'OPTIONS': _db_options,
        },
    }

# ——— Auth ———
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ——— i18n ———
LANGUAGE_CODE = 'en-us'
TIME_ZONE = config('TIME_ZONE', default='Asia/Kathmandu')
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ——— Static & media ———
STATIC_URL = _env_url('STATIC_URL', '/static/')
STATIC_ROOT = _env_path('STATIC_ROOT', 'staticfiles')
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = _env_url('MEDIA_URL', '/media/')
MEDIA_ROOT = _env_path('MEDIA_ROOT', 'media')

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

CKEDITOR_UPLOAD_PATH = 'uploads/'
LOGIN_REDIRECT_URL = '/home/'
LOGIN_URL = '/accounts/login/'
LOGOUT_REDIRECT_URL = '/'

# ——— Email ———
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
# From address must match the authenticated mailbox (or an allowed alias) on most SMTP hosts.
DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL',
    default=EMAIL_HOST_USER or 'noreply@futnetnepal.com',
)
SERVER_EMAIL = config('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=30, cast=int)
# Optional: send all outbound mail to this address (testing only; leave empty in production).
EMAIL_OVERRIDE_RECIPIENT = config('EMAIL_OVERRIDE_RECIPIENT', default='').strip()

SITE_URL = config('SITE_URL', default='http://127.0.0.1:8000').rstrip('/')

# ——— SMS / OTP ———
AAKASH_SMS_AUTH_TOKEN = config('AAKASH_SMS_AUTH_TOKEN', default='')
PHONE_OTP_EXPIRY_MINUTES = config('PHONE_OTP_EXPIRY_MINUTES', default=10, cast=int)
PHONE_OTP_RESEND_COOLDOWN_SECONDS = config('PHONE_OTP_RESEND_COOLDOWN_SECONDS', default=60, cast=int)
PHONE_OTP_MAX_ATTEMPTS = config('PHONE_OTP_MAX_ATTEMPTS', default=5, cast=int)
EMAIL_OTP_EXPIRY_MINUTES = config('EMAIL_OTP_EXPIRY_MINUTES', default=15, cast=int)
EMAIL_OTP_RESEND_COOLDOWN_SECONDS = config('EMAIL_OTP_RESEND_COOLDOWN_SECONDS', default=60, cast=int)
EMAIL_OTP_MAX_ATTEMPTS = config('EMAIL_OTP_MAX_ATTEMPTS', default=5, cast=int)

# ——— CORS ———
_cors_origins = _csv('CORS_ALLOWED_ORIGINS')
if _cors_origins:
    CORS_ALLOWED_ORIGINS = _cors_origins
    CORS_ALLOW_ALL_ORIGINS = False
elif DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = [
        'https://futnetnepal.com',
        'https://www.futnetnepal.com',
    ]
    CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOW_CREDENTIALS = config('CORS_ALLOW_CREDENTIALS', default=False, cast=bool)
CORS_ALLOW_HEADERS = (
    'accept',
    'authorization',
    'content-type',
    'origin',
    'user-agent',
    'x-requested-with',
)

# ——— DRF / JWT ———
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',),
}

if DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    )

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('JWT_ACCESS_MINUTES', default=60 * 24, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=config('JWT_REFRESH_DAYS', default=30, cast=int)),
    'ROTATE_REFRESH_TOKENS': True,
    'UPDATE_LAST_LOGIN': True,
}

# ——— Production security (HTTPS behind reverse proxy) ———
_csrf_trusted = _csv('CSRF_TRUSTED_ORIGINS')
if _csrf_trusted:
    CSRF_TRUSTED_ORIGINS = _csrf_trusted
elif not DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        'https://futnetnepal.com',
        'https://www.futnetnepal.com',
    ]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
    CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
    SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'

# ——— Logging ———
_log_level = config('LOG_LEVEL', default='DEBUG' if DEBUG else 'INFO')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': _log_level,
    },
    'loggers': {
        'django': {'level': _log_level, 'propagate': True},
        'django.request': {'level': 'ERROR', 'propagate': True},
    },
}

# ——— Jazzmin ———
JAZZMIN_SETTINGS = {
    'site_title': 'FutnetNepal Admin',
    'site_header': 'FutnetNepal',
    'site_logo': 'images/logo.png',
    'site_brand': 'Futnet Nepal',
    'site_logo_classes': 'img-responisve',
    'site_icon': 'images/logo.png',
    'welcome_sign': 'Welcome to the Futnet Nepal',
    'copyright': 'Futnet Nepal Pvt. Ltd.',
    'search_model': 'auth.User',
    'user_avatar': None,
    'topmenu_links': [
        {'name': 'Home', 'url': 'index', 'new_window': True},
        {'name': 'Contact', 'url': 'contact', 'new_window': True},
        {'name': 'Blog', 'url': 'blog', 'new_window': True},
        {'name': 'About', 'url': 'about', 'new_window': True},
        {'name': 'Partner WithUS', 'url': 'partnerwithus', 'new_window': True},
        {'model': 'auth.User'},
    ],
}

CKEDITOR_CONFIGS = {
    'default': {
        'skin': 'moono',
        'toolbar_Basic': [['Source', '-', 'Bold', 'Italic']],
        'toolbar_YourCustomToolbarConfig': [
            {'name': 'document', 'items': ['Source', '-', 'Save', 'NewPage', 'Preview', 'Print', '-', 'Templates']},
            {'name': 'clipboard', 'items': ['Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
            {'name': 'editing', 'items': ['Find', 'Replace', '-', 'SelectAll']},
            {'name': 'forms', 'items': ['Form', 'Checkbox', 'Radio', 'TextField', 'Textarea', 'Select', 'Button', 'ImageButton', 'HiddenField']},
            '/',
            {'name': 'basicstyles', 'items': ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-', 'RemoveFormat']},
            {'name': 'paragraph', 'items': ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote', 'CreateDiv', '-', 'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock', '-', 'BidiLtr', 'BidiRtl', 'Language']},
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
            {'name': 'insert', 'items': ['Image', 'Flash', 'Table', 'HorizontalRule', 'Smiley', 'SpecialChar', 'PageBreak', 'Iframe']},
            '/',
            {'name': 'styles', 'items': ['Styles', 'Format', 'Font', 'FontSize']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
            {'name': 'tools', 'items': ['Maximize', 'ShowBlocks']},
            {'name': 'about', 'items': ['About']},
            '/',
            {'name': 'yourcustomtools', 'items': ['Preview', 'Maximize']},
        ],
        'toolbar': 'YourCustomToolbarConfig',
        'tabSpaces': 4,
        'extraPlugins': ','.join([
            'uploadimage', 'div', 'autolink', 'autoembed', 'embedsemantic', 'autogrow',
            'widget', 'lineutils', 'clipboard', 'dialog', 'dialogui', 'elementspath',
        ]),
    },
}

from django.contrib.messages import constants as messages  # noqa: E402

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}
