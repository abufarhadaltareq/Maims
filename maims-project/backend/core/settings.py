import dj_database_url
import os
# ... rest of your imports and code
from django.urls import reverse_lazy
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load local .env (STRIPE keys, SECRET_KEY, etc.) — silently skipped if absent.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:  # python-dotenv not installed: rely on real environment vars
    pass


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/
# PRODUCTION: set DEBUG=False, SECRET_KEY to a long random value, and
# ALLOWED_HOSTS=maims.eu,www.maims.eu (plus CSRF_TRUSTED_ORIGINS below).
# The admin header then flips from the amber "Development" badge to the
# green "Live · maims.eu" badge via core.admin.environment_callback.

# SECURITY WARNING: keep the secret key used in production secret!
# The fallback below is a dev convenience ONLY — it is validated against DEBUG
# so it can never silently ship to production.
_INSECURE_DEV_KEY = 'django-insecure-l88&4z9wxa^19^suqzf3q+^_*7n7o0*rm+qr9@l8wqo6zdtzgc'
SECRET_KEY = os.environ.get('SECRET_KEY', _INSECURE_DEV_KEY)

# SECURITY WARNING: don't run with debug turned on in production!
# Default to False so a missing env var fails closed instead of leaking tracebacks.
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

# Fail fast if production is misconfigured with the public fallback key.
if not DEBUG and SECRET_KEY == _INSECURE_DEV_KEY:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        'SECRET_KEY environment variable must be set to a strong, unique value when DEBUG=False.'
    )

# ALLOWED_HOSTS: read from env var, default to localhosts in DEBUG, else empty (must be set in production).
_allowed_hosts = os.environ.get('ALLOWED_HOSTS')
if _allowed_hosts:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(',') if h.strip()]
else:
    if DEBUG:
        ALLOWED_HOSTS = ['localhost', '127.0.0.1']
    else:
        ALLOWED_HOSTS = []

# maims.eu production hosts: CSRF_TRUSTED_ORIGINS must list the exact https
# origins or admin POSTs (login, save, actions) return 403 once DEBUG=False.
# Example: CSRF_TRUSTED_ORIGINS=https://maims.eu,https://www.maims.eu
_csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS')
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = []

# FRONTEND_BASE_URL and BACKEND_BASE_URL: read from env vars. In production they are required.
FRONTEND_BASE_URL = os.environ.get('FRONTEND_BASE_URL')
if not FRONTEND_BASE_URL:
    if not DEBUG:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured('FRONTEND_BASE_URL environment variable is required in production.')
    FRONTEND_BASE_URL = ''
else:
    FRONTEND_BASE_URL = FRONTEND_BASE_URL.rstrip('/')

BACKEND_BASE_URL = os.environ.get('BACKEND_BASE_URL')
if not BACKEND_BASE_URL:
    if not DEBUG:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured('BACKEND_BASE_URL environment variable is required in production.')
    BACKEND_BASE_URL = ''
else:
    BACKEND_BASE_URL = BACKEND_BASE_URL.rstrip('/')

# Where the built Vue storefront lives. Served at / when the file exists
# (production), otherwise / falls through to the /health/ JSON probe.
FRONTEND_DIST_DIR = Path(os.environ.get('FRONTEND_DIST_DIR', BASE_DIR / 'static' / 'storefront'))


# Application definition

INSTALLED_APPS = [
    # Unfold must come before django.contrib.admin: it ships replacements for
    # admin/base.html & friends, and app template dirs are searched in INSTALLED_APPS
    # order, so Unfold's win only if it is listed first. The unfold.contrib add-ons
    # give the admin Unfold-styled filters, form widgets and inlines.
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'unfold.contrib.inlines',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    # Explicit AppConfig path: ProductsConfig.ready() imports the order signal
    # handlers, and Django only calls ready() for the config it is given.
    'products.apps.ProductsConfig',
    'core',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise serves /static directly from the app process, so admin CSS/JS
    # keeps working on platforms with no separate CDN or static container. It
    # must sit directly below SecurityMiddleware to see the security headers.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

def _postgres_from_url(url):
    """Parse postgresql://user:pass@host:port/db into a Django DATABASES dict."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ('postgres', 'postgresql'):
        raise ValueError(f'DATABASE_URL must use the postgresql:// scheme, got {parsed.scheme!r}')
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': parsed.path.lstrip('/') or 'maims_db',
        'USER': parsed.username or 'maims_user',
        'PASSWORD': parsed.password or '',
        'HOST': parsed.hostname or '127.0.0.1',
        'PORT': str(parsed.port or 5432),
    }


def _postgres_from_env():
    """Build a PostgreSQL config from discrete environment variables."""
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB') or os.environ.get('PGDATABASE') or 'maims_db',
        'USER': os.environ.get('POSTGRES_USER') or os.environ.get('PGUSER') or 'maims_user',
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD') or os.environ.get('PGPASSWORD') or 'maims_password',
        'HOST': os.environ.get('POSTGRES_HOST') or os.environ.get('PGHOST') or '127.0.0.1',
        'PORT': str(os.environ.get('POSTGRES_PORT') or os.environ.get('PGPORT') or 5432),
    }


if os.environ.get('DB_ENGINE', 'postgresql').lower() == 'sqlite':
    # Explicit opt-in only (local dev / data migration). Not a default.
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Use dj-database-url to parse DATABASE_URL (e.g., from Neon).
    # If not set, fall back to discrete POSTGRES_* env vars.
    DATABASES = {
        'default': dj_database_url.parse(
            os.environ.get('DATABASE_URL') or
            f"postgres://{os.environ.get('POSTGRES_USER', 'maims_user')}:"
            f"{os.environ.get('POSTGRES_PASSWORD', 'maims_password')}@"
            f"{os.environ.get('POSTGRES_HOST', '127.0.0.1')}:"
            f"{os.environ.get('POSTGRES_PORT', '5432')}/"
            f"{os.environ.get('POSTGRES_DB', 'maims_db')}"
        )
    }
    # Enforce SSL in production (when not DEBUG).
    if not DEBUG:
        DATABASES['default']['OPTIONS'] = {'sslmode': 'require'}
    # Reuse connections between requests when talking to PostgreSQL.
    DATABASES['default']['CONN_MAX_AGE'] = int(os.environ.get('DB_CONN_MAX_AGE', '0'))


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Password-reset links expire after 24 hours (the emailed link says so).
PASSWORD_RESET_TIMEOUT = 24 * 3600


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        # Use Cloudinary for media in production; local file storage only when DEBUG.
        'BACKEND': (
            'django.core.files.storage.FileSystemStorage'
            if DEBUG
            else 'cloudinary_storage.storage.MediaCloudinaryStorage'
        ),
    },
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}

# WhiteNoise answer-indexes /static without touching the filesystem.
WHITENOISE_AUTOREFRESH = DEBUG
# Never delete the originals; some deployments share staticfiles between builds.
WHITENOISE_KEEP_ONLY_HASHED_FILES = False

# --- django-unfold -------------------------------------------------------------
UNFOLD = {
    'SITE_TITLE': 'Maims Admin',
    'SITE_HEADER': 'Maims Store Admin',
    'SITE_SUBHEADER': 'Orders, stock and customers',
    'SITE_SYMBOL': 'storefront',
    'SHOW_HISTORY': True,
    'SHOW_VIEW_ON_SITE': False,
    'SHOW_BACK_BUTTON': True,

    'DASHBOARD_CALLBACK': 'core.admin.dashboard_callback',
    'ENVIRONMENT': 'core.admin.environment_callback',

    'STYLES': [
        lambda request: static('admin/maims.css'),
    ],

    'BORDER_RADIUS': '10px',

    'COLORS': {
        'primary': {
            '50': '#faf5ff', '100': '#f3e8ff', '200': '#e9d5ff', '300': '#d8b4fe',
            '400': '#c084fc', '500': '#a855f7', '600': '#9333ea', '700': '#7e22ce',
            '800': '#6b21a8', '900': '#581c87', '950': '#3b0764',
        },
        'secondary': {
            '50': '#fdf4ff', '100': '#fae8ff', '200': '#f5d0fe', '300': '#f0abfc',
            '400': '#e879f9', '500': '#d946ef', '600': '#c026d3', '700': '#a21caf',
            '800': '#86198f', '900': '#701a75', '950': '#4a044e',
        },
    },

    'SIDEBAR': {
        'show_search': True,
        'show_all_applications': False,
        'navigation': [
            {
                'title': _('Daily work'),
                'separator': True,
                'items': [
                    {'title': _('Dashboard'), 'icon': 'dashboard',
                     'link': reverse_lazy('admin:index')},
                    {'title': _('Awaiting our decision'), 'icon': 'inventory_2',
                     'link': '/admin/products/order/?status__exact=new',
                     'badge': 'core.admin.new_orders_badge'},
                    {'title': _('Accepted, to pack'), 'icon': 'package_2',
                     'link': '/admin/products/order/?status__exact=accepted'},
                    {'title': _('Packed, waiting for courier'), 'icon': 'local_shipping',
                     'link': '/admin/products/order/?status__exact=packed'},
                    {'title': _('Out for delivery'), 'icon': 'local_shipping',
                     'link': '/admin/products/order/?status__exact=shipped'},
                    {'title': _('Delivered'), 'icon': 'check_circle',
                     'link': '/admin/products/order/?status__exact=delivered'},
                    {'title': _('Declined'), 'icon': 'cancel',
                     'link': '/admin/products/order/?status__exact=rejected'},
                    {'title': _('Cancelled'), 'icon': 'cancel',
                     'link': '/admin/products/order/?status__exact=cancelled'},
                    {'title': _('Notifications'), 'icon': 'notifications',
                     'link': reverse_lazy('admin:products_ordernotification_changelist'),
                     'badge': 'core.admin.failed_notifications_badge'},
                ],
            },
            {
                'title': _('Shop'),
                'separator': True,
                'items': [
                    {'title': _('Orders'), 'icon': 'shopping_cart',
                     'link': reverse_lazy('admin:products_order_changelist')},
                    {'title': _('Products'), 'icon': 'inventory_2',
                     'link': reverse_lazy('admin:products_product_changelist')},
                    {'title': _('Categories'), 'icon': 'category',
                     'link': reverse_lazy('admin:products_category_changelist')},
                    {'title': _('Collections'), 'icon': 'collections',
                     'link': reverse_lazy('admin:products_collection_changelist')},
                    {'title': _('Hero slides'), 'icon': 'photo_library',
                     'link': reverse_lazy('admin:products_heroslide_changelist')},
                    {'title': _('Reviews'), 'icon': 'star',
                     'link': reverse_lazy('admin:products_review_changelist')},
                    {'title': _('Customers'), 'icon': 'group',
                     'link': reverse_lazy('admin:auth_user_changelist')},
                    {'title': _('Groups'), 'icon': 'group',
                     'link': reverse_lazy('admin:auth_group_changelist')},
                    {'title': _('Store settings'), 'icon': 'settings',
                     'link': reverse_lazy('admin:products_sitesettings_changelist')},
                    {'title': _('Update prices & stock (CSV)'), 'icon': 'upload_file',
                     'link': reverse_lazy('admin:products_product_import_csv'),
                     'permission': lambda request: request.user.has_perm('products.change_product')},
                ],
            },
        ],
    },

    'TABS': [
        {
            'models': ['products.order'],
            'items': [
                {'title': _('To decide'), 'link': '/admin/products/order/?status__exact=new'},
                {'title': _('To pack'), 'link': '/admin/products/order/?status__exact=accepted'},
                {'title': _('Packed'), 'link': '/admin/products/order/?status__exact=packed'},
                {'title': _('In transit'), 'link': '/admin/products/order/?status__exact=shipped'},
                {'title': _('Unpaid'), 'link': '/admin/products/order/?is_paid__exact=0'},
            ],
        },
    ],
}

STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

SERVE_MEDIA = os.environ.get('SERVE_MEDIA', 'True').lower() in ('true', '1', 'yes')

# --- Logging ------------------------------------------------------------------
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
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
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'rest_framework': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# --- CORS Configuration --------------------------------------------------------
# --- CORS Configuration --------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = os.environ.get('CORS_ALLOW_ALL_ORIGINS', 'False').lower() in ('true', '1', 'yes')

_cors_allowed = os.environ.get('CORS_ALLOWED_ORIGINS')
if _cors_allowed:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_allowed.split(',') if o.strip()]
else:
    CORS_ALLOWED_ORIGINS = [
        'https://shop.maims.eu',
        'https://maims.eu',
        'https://www.maims.eu',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
    ]

# Automatically allow any subdomain on maims.eu to avoid mismatch issues
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://([a-zA-Z0-9-]+\.)*maims\.eu$",
]

CORS_ALLOW_CREDENTIALS = False

from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = list(default_headers) + [
    'idempotency-key',
]

# STRIPE CONFIGURATION
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

if STRIPE_SECRET_KEY and not STRIPE_WEBHOOK_SECRET:
    import logging as _logging
    _logging.getLogger('core').warning(
        'STRIPE_WEBHOOK_SECRET is not set. Card payments will only be confirmed '
        'when the customer returns to the success page; set it to '
        'https://dashboard.stripe.com/webhooks for reliable order confirmation.'
    )

# --- Facebook Page product sync -------------------------------------------
FACEBOOK_PAGE_ID = os.environ.get('FACEBOOK_PAGE_ID', '')
FACEBOOK_PAGE_ACCESS_TOKEN = os.environ.get('FACEBOOK_PAGE_ACCESS_TOKEN', '')
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET', '')
FACEBOOK_WEBHOOK_VERIFY_TOKEN = os.environ.get('FACEBOOK_WEBHOOK_VERIFY_TOKEN', '')
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL', '')
FACEBOOK_SYNC_CATEGORY_SLUG = os.environ.get('FACEBOOK_SYNC_CATEGORY_SLUG', 'facebook-sync')
FACEBOOK_SYNC_DEFAULT_STOCK = int(os.environ.get('FACEBOOK_SYNC_DEFAULT_STOCK', '10'))
FACEBOOK_SYNC_DEFAULT_CURRENCY = os.environ.get('FACEBOOK_SYNC_DEFAULT_CURRENCY', 'EUR')

# EMAIL
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Maims <noreply@maims.eu>')
ADMIN_RECEIVER_EMAIL = os.environ.get('ADMIN_RECEIVER_EMAIL', '')
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', '')
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')

if DEBUG:
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    else:
        EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    if not BREVO_API_KEY:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured('BREVO_API_KEY environment variable is required in production.')
    EMAIL_BACKEND = 'anymail.backends.brevo.EmailBackend'
    ANYMAIL = {'BREVO_API_KEY': BREVO_API_KEY}

# --- Transport & cookie hardening ---
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'products.authentication.ExpiringTokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'auth': os.environ.get('THROTTLE_AUTH', '10/min'),
        'checkout': os.environ.get('THROTTLE_CHECKOUT', '30/hour'),
        'newsletter': os.environ.get('THROTTLE_NEWSLETTER', '5/hour'),
        'chatbot': os.environ.get('THROTTLE_CHATBOT', '60/min'),
    },
}

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-4o-mini')

AUTH_TOKEN_MAX_AGE_DAYS = int(os.environ.get('AUTH_TOKEN_MAX_AGE_DAYS', '90'))