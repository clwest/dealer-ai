import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Both .env files loaded with override=True so edits are picked up on
# every Django autoreload — otherwise stale os.environ values from a
# previous process keep winning. Repo root loaded last so secrets kept
# there (like OPENAI_API_KEY) trump anything in backend/.env.
load_dotenv(BASE_DIR / ".env", override=True)
load_dotenv(BASE_DIR.parent / ".env", override=True)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    # Milestone 1 · Increment 4B — provides the ``Token`` model consumed
    # by :class:`rest_framework.authentication.TokenAuthentication` in
    # ``REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]`` below. The
    # token table is created but no tokens exist until an operator
    # provisions one (per-user or via ``manage.py drf_create_token``).
    "rest_framework.authtoken",
    "corsheaders",
    "dealer_ai",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "dealer_kit.middleware.EmbedFramePolicyMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "dealer_kit.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "dealer_kit.wsgi.application"

USE_POSTGRES = os.getenv("POSTGRES_DB") and os.getenv("POSTGRES_USER")

if USE_POSTGRES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB"),
            "USER": os.getenv("POSTGRES_USER"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
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
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    # Milestone 1 · Increment 4B — establish that requests *carry*
    # identity when credentials are present. `SessionAuthentication`
    # keeps the customer-facing chat + embed frame cookie-friendly.
    # `TokenAuthentication` enables scripted / API-client access
    # (Increment 4E frontend will use session cookies; token is here
    # for headless clients and future integrations).
    #
    # ``DEFAULT_PERMISSION_CLASSES`` is intentionally NOT SET — the
    # DRF default (``AllowAny``) stands so no currently-public
    # endpoint silently gains a 401. Endpoint-level tightening
    # arrives in 4C (advisor workspace) and 4D (admin endpoints).
    # See ``docs/roadmap/AUTHENTICATION_MODEL.md`` for the identity /
    # authorization / permission layer separation.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
}

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]

# Milestone 1 · Increment 4E — Django's CsrfViewMiddleware (and DRF's
# SessionAuthentication.enforce_csrf) require the request's Origin
# header to match one of these entries when validating unsafe methods
# on cookie-backed sessions. In dev, the browser talks to the Vite
# dev server (:5173) which proxies to Django (:8001); the Origin the
# browser sends is the vite URL, not the Django one. Configurable via
# env so prod (single-origin behind one domain) can override.
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]

DEALER_AI_EMBED_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("DEALER_AI_EMBED_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]

# LLM provider config (read by services/llm/factory.py)
DEALER_AI_LLM_PROVIDER = os.getenv("DEALER_AI_LLM_PROVIDER", "ollama")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Dealer identity. Prompts + reply templates format themselves with
# `{dealer_name}` and resolve the value at call time via
# `dealer_ai.services.dealer_config.get_dealer_name()`, which prefers
# this env var over the persisted DealerOnboardingProfile.
DEALER_AI_DEALER_NAME = os.getenv("DEALER_AI_DEALER_NAME", "")
