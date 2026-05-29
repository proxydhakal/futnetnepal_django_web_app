"""
Django settings for futnetnepal.

Environment variables are loaded from `.env` via python-dotenv (see futnetnepal.env).
Copy `.env.example` to `.env` and adjust per environment.
"""

from datetime import timedelta
from pathlib import Path

from corsheaders.defaults import default_headers, default_methods

from futnetnepal.env import env, env_bool, env_csv, env_int

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_path(name, default_relative):
    raw = env(name, default='')
    if not raw:
        return BASE_DIR / default_relative
    path = Path(raw)
    return path if path.is_absolute() else BASE_DIR / path


def _env_url(name, default):
    value = env(name, default=default)
    return value if value.endswith('/') else f'{value}/'


def _csv(name, default=''):
    return env_csv(name, default=default)


# ——— Core ———
SECRET_KEY = env('SECRET_KEY', required=True)
DEBUG = env_bool('DEBUG', default=False)

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
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'channels',
    'apps.dashboard.apps.DashboardConfig',
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
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'futnetnepal.middleware.request_logging.RequestLoggingMiddleware',
    'futnetnepal.middleware.AuditContextMiddleware',
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
                'apps.core.context_processors.site_content',
                'apps.dashboard.context_processors.admin_nav',
            ],
        },
    },
]

WSGI_APPLICATION = 'futnetnepal.wsgi.application'
ASGI_APPLICATION = 'futnetnepal.asgi.application'

# ——— Redis / Channels ———
_redis_url = env('REDIS_URL', default='')
if not _redis_url:
    _redis_password = env('REDIS_PASSWORD', default='')
    if _redis_password:
        _redis_host = env('REDIS_HOST', default='127.0.0.1')
        _redis_port = env_int('REDIS_PORT', default=6379)
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

_database_url = env('DATABASE_URL', default='')
_use_sqlite = env_bool('USE_SQLITE', default=DEBUG) or (
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
    _db_engine = env('DB_ENGINE', default='django.db.backends.mysql')
    if _db_engine == 'mysql':
        _db_engine = 'django.db.backends.mysql'

    _db_options = {
        'charset': 'utf8mb4',
        'use_unicode': True,
    }
    if 'mysql' in _db_engine:
        _db_options['init_command'] = "SET sql_mode='STRICT_TRANS_TABLES'"

    DATABASES = {
        'default': {
            'ENGINE': _db_engine,
            'NAME': env('DB_NAME', required=True),
            'USER': env('DB_USER', required=True),
            'PASSWORD': env('DB_PASSWORD', default=''),
            'HOST': env('DB_HOST', default='127.0.0.1'),
            'PORT': env_int('DB_PORT', default=3306),
            'CONN_MAX_AGE': env_int('DB_CONN_MAX_AGE', default=60 if not DEBUG else 0),
            'OPTIONS': _db_options,
        },
    }

# ——— Auth ———
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ——— i18n ———
LANGUAGE_CODE = 'en-us'
TIME_ZONE = env('TIME_ZONE', default='Asia/Kathmandu')
USE_I18N = True
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
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env_int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', default=True)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', default=False)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
# From address must match the authenticated mailbox (or an allowed alias) on most SMTP hosts.
DEFAULT_FROM_EMAIL = env(
    'DEFAULT_FROM_EMAIL',
    default=EMAIL_HOST_USER or 'noreply@futnetnepal.com',
)
SERVER_EMAIL = env('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)
EMAIL_TIMEOUT = env_int('EMAIL_TIMEOUT', default=30)
# Optional: send all outbound mail to this address (testing only; leave empty in production).
EMAIL_OVERRIDE_RECIPIENT = env('EMAIL_OVERRIDE_RECIPIENT', default='').strip()
FUTNET_INFO_EMAIL = env('FUTNET_INFO_EMAIL', default='info@futnetnepal.com').strip()

SITE_URL = env('SITE_URL', default='http://127.0.0.1:8000').rstrip('/')

# ——— SMS / OTP ———
AAKASH_SMS_AUTH_TOKEN = env('AAKASH_SMS_AUTH_TOKEN', default='')
PHONE_OTP_EXPIRY_MINUTES = env_int('PHONE_OTP_EXPIRY_MINUTES', default=10)
PHONE_OTP_RESEND_COOLDOWN_SECONDS = env_int('PHONE_OTP_RESEND_COOLDOWN_SECONDS', default=60)
PHONE_OTP_MAX_ATTEMPTS = env_int('PHONE_OTP_MAX_ATTEMPTS', default=5)
EMAIL_OTP_EXPIRY_MINUTES = env_int('EMAIL_OTP_EXPIRY_MINUTES', default=15)
EMAIL_OTP_RESEND_COOLDOWN_SECONDS = env_int('EMAIL_OTP_RESEND_COOLDOWN_SECONDS', default=60)
EMAIL_OTP_MAX_ATTEMPTS = env_int('EMAIL_OTP_MAX_ATTEMPTS', default=5)

# ——— CORS (django-cors-headers) ———
# Applies to REST API routes (Flutter web, SPA). Native mobile apps are not affected by CORS.
CORS_URLS_REGEX = r'^/api/.*$'

_cors_origins = _csv('CORS_ALLOWED_ORIGINS')
_cors_origin_regexes = _csv('CORS_ALLOWED_ORIGIN_REGEXES')

if _cors_origins:
    CORS_ALLOWED_ORIGINS = _cors_origins
    CORS_ALLOW_ALL_ORIGINS = False
elif DEBUG:
    CORS_ALLOW_ALL_ORIGINS = env_bool('CORS_ALLOW_ALL_ORIGINS', default=True)
    if not CORS_ALLOW_ALL_ORIGINS:
        CORS_ALLOWED_ORIGINS = [
            'http://localhost:3000',
            'http://localhost:5173',
            'http://localhost:8080',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:5173',
            'http://127.0.0.1:8000',
            'http://127.0.0.1:8001',
        ]
else:
    CORS_ALLOWED_ORIGINS = [
        'https://futnetnepal.com',
        'https://www.futnetnepal.com',
    ]
    CORS_ALLOW_ALL_ORIGINS = False

if _cors_origin_regexes:
    CORS_ALLOWED_ORIGIN_REGEXES = _cors_origin_regexes

CORS_ALLOW_CREDENTIALS = env_bool('CORS_ALLOW_CREDENTIALS', default=False)
if CORS_ALLOW_CREDENTIALS and CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOW_HEADERS = list(default_headers) + [
    'x-csrftoken',
    'cache-control',
]
CORS_ALLOW_METHODS = list(default_methods)
CORS_EXPOSE_HEADERS = ['content-type', 'content-length']
CORS_PREFLIGHT_MAX_AGE = env_int('CORS_PREFLIGHT_MAX_AGE', default=86400)

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
    'EXCEPTION_HANDLER': 'futnetnepal.api_exceptions.logged_api_exception_handler',
}

if DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    )

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env_int('JWT_ACCESS_MINUTES', default=60 * 24)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env_int('JWT_REFRESH_DAYS', default=30)),
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
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', default=True)
    CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', default=True)
    SECURE_HSTS_SECONDS = env_int('SECURE_HSTS_SECONDS', default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
    SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', default=True)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'

# ——— Logging ———
from futnetnepal.logging_config import build_logging_settings  # noqa: E402

LOGGING = build_logging_settings(debug=DEBUG)

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
