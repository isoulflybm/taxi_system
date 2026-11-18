import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-local-key-change-before-deploy")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [u.strip() for u in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if u.strip()]
MAP_STYLE_URL = os.environ.get("MAP_STYLE_URL", "").strip() or "https://tiles.openfreemap.org/styles/liberty"
NOMINATIM_BASE_URL = os.environ.get("NOMINATIM_BASE_URL", "").rstrip("/")
NOMINATIM_USER_AGENT = os.environ.get("NOMINATIM_USER_AGENT", "TaxiKG/0.1 (configure-contact-email)")
OSRM_BASE_URL = os.environ.get("OSRM_BASE_URL", "").rstrip("/")
DRIVER_LOCATION_MAX_AGE_SECONDS = int(os.environ.get("DRIVER_LOCATION_MAX_AGE_SECONDS", "120"))
DRIVER_SEARCH_RADIUS_METERS = int(os.environ.get("DRIVER_SEARCH_RADIUS_METERS", "10000"))
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "rest_framework",
    "rest_framework.authtoken",
    "channels",
    "apps.accounts",
    "apps.fleet",
    "apps.orders",
    "apps.trips",
    "apps.dispatch",
    "apps.tariffs",
    "apps.tracking",
    "apps.geo",
    "apps.payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": {
    "ENGINE": "django.contrib.gis.db.backends.postgis",
    "NAME": os.environ.get("POSTGRES_DB", "taxi_kg"),
    "USER": os.environ.get("POSTGRES_USER", "taxi_kg"),
    "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "local-only-change-me"),
    "HOST": os.environ.get("POSTGRES_HOST", "db"),
    "PORT": os.environ.get("POSTGRES_PORT", "5432"),
}}

REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
CHANNEL_LAYERS = {"default": {
    "BACKEND": "channels_redis.core.RedisChannelLayer",
    # Redis-py 8 defaults socket_timeout to 5s, which breaks the blocking
    # receive used by idle Channels WebSockets. Keep this connection unbounded.
    "CONFIG": {"hosts": [{"address": REDIS_URL, "socket_timeout": None}]},
}}
CACHES = {"default": {
    "BACKEND": "django.core.cache.backends.redis.RedisCache",
    "LOCATION": REDIS_URL,
}}

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Bishkek"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "driver_location": "30/min",
        "geo_search": "10/min",
        "public_route": "30/min",
        "signup": "5/hour",
    },
}
