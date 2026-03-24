"""Django settings for YAMLconfig project."""

from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret.
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-change-me")

# SECURITY WARNING: don't run with debug turned on in production.
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() in {"1", "true", "yes"}

ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]


INSTALLED_APPS = [
	"django.contrib.admin",
	"django.contrib.auth",
	"django.contrib.contenttypes",
	"django.contrib.sessions",
	"django.contrib.messages",
	"django.contrib.staticfiles",
	# "django.contrib.sites",  # allauth dependency (disabled for now)
	# "allauth",  # disabled until email/app-password setup is ready
	# "allauth.account",  # disabled until email/app-password setup is ready
	"generator",
]

MIDDLEWARE = [
	"django.middleware.security.SecurityMiddleware",
	"django.contrib.sessions.middleware.SessionMiddleware",
	"django.middleware.common.CommonMiddleware",
	"django.middleware.csrf.CsrfViewMiddleware",
	"django.contrib.auth.middleware.AuthenticationMiddleware",
	# "allauth.account.middleware.AccountMiddleware",  # allauth disabled for now
	"django.contrib.messages.middleware.MessageMiddleware",
	"django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
	{
		"BACKEND": "django.template.backends.django.DjangoTemplates",
		"DIRS": [BASE_DIR / "templates"],
		"APP_DIRS": True,
		"OPTIONS": {
			"context_processors": [
				"django.template.context_processors.request",
				"django.contrib.auth.context_processors.auth",
				"django.contrib.messages.context_processors.messages",
			],
		},
	},
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


DATABASES = {
	"default": {
		"ENGINE": "django.db.backends.sqlite3",
		"NAME": BASE_DIR / "db.sqlite3",
	}
}


AUTH_PASSWORD_VALIDATORS = [
	{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
	{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
	{"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
	{"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

_static_dirs = [
	BASE_DIR / "theme" / "static",
	BASE_DIR / "theme" / "static_src",
]
STATICFILES_DIRS = [path for path in _static_dirs if path.exists()]


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# SITE_ID = 1  # allauth disabled for now

AUTHENTICATION_BACKENDS = [
	"django.contrib.auth.backends.ModelBackend",
	# "allauth.account.auth_backends.AuthenticationBackend",  # allauth disabled for now
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Allauth account settings kept for later re-enable.
# ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# ACCOUNT_UNIQUE_EMAIL = True
# ACCOUNT_SIGNUP_FIELDS = ["username*", "email*", "password1*", "password2*"]

if DEBUG:
	EMAIL_BACKEND = os.getenv(
		"DJANGO_EMAIL_BACKEND",
		"django.core.mail.backends.console.EmailBackend",
	)
else:
	EMAIL_BACKEND = os.getenv("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")

EMAIL_HOST = os.getenv("DJANGO_EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("DJANGO_EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("DJANGO_EMAIL_USE_TLS", "false").lower() in {"1", "true", "yes"}
EMAIL_USE_SSL = os.getenv("DJANGO_EMAIL_USE_SSL", "false").lower() in {"1", "true", "yes"}
DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL", "no-reply@yamlconfig.local")
