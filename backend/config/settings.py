import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_ROOT = Path(os.getenv("DATA_ROOT", BASE_DIR.parent / "data")).resolve()
SYNCED_DATA_ROOT = Path(os.getenv("SYNCED_DATA_ROOT", DATA_ROOT / "synced_data")).resolve()
TEMPLATE_ROOT = Path(os.getenv("TEMPLATE_ROOT", DATA_ROOT / "templates")).resolve()
OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", DATA_ROOT / "output")).resolve()
UNFOLDX_USER_DATA_WORKBOOK = Path(
    os.getenv(
        "UNFOLDX_USER_DATA_WORKBOOK",
        SYNCED_DATA_ROOT / "onedrive" / "unfoldx_user_data.xlsx",
    )
)
BUSINESS_RULE_CONFIG_PATH = Path(
    os.getenv(
        "BUSINESS_RULE_CONFIG_PATH",
        BASE_DIR / "project_config" / "business_rules.json",
    )
)
UNFOLDX_USER_DATA_SHEET = os.getenv("UNFOLDX_USER_DATA_SHEET", "Nominator")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "config",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
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
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_ROOT / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
    }
}

AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = []

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR.parent / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "15552000"))
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

DATA_ROOT.mkdir(parents=True, exist_ok=True)
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
