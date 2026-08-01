"""
Production settings overlay for VehicleMatch on Render free tier.

Imports the dev settings and layers prod-grade overrides on top:
- DEBUG off, ALLOWED_HOSTS env-driven (defaults to *.onrender.com)
- WhiteNoise for static file serving (Render has no nginx layer)
- STATIC_ROOT for collectstatic
- Trust Render's reverse proxy for HTTPS detection + CSRF
- SQLite remains on the baked image's disk — fine for ephemeral demo data
"""
from __future__ import annotations

import os

from .settings import *  # noqa: F401,F403
from .settings import BASE_DIR, MIDDLEWARE, STORAGES  # explicit re-imports for editors

# --- core security ---------------------------------------------------------
DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]  # required in prod

_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _hosts.split(",") if h.strip()] + [
    ".onrender.com",
]

# --- static files (WhiteNoise) --------------------------------------------
STATIC_ROOT = BASE_DIR / "staticfiles"

# Insert WhiteNoise right after SecurityMiddleware
_security_idx = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
MIDDLEWARE = (
    MIDDLEWARE[: _security_idx + 1]
    + ["whitenoise.middleware.WhiteNoiseMiddleware"]
    + MIDDLEWARE[_security_idx + 1 :]
)
# Milestone 3 · Increment 4 — prod overlay only swaps ``staticfiles``
# to WhiteNoise's compressed manifest backend and re-uses the
# ``condition_photos`` alias from the dev settings (env-driven S3 vs
# FileSystemStorage). Do NOT rewrite the whole ``STORAGES`` dict here
# or the ``condition_photos`` env-switch logic gets bypassed.
STORAGES = {
    **STORAGES,
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# --- proxy / SSL ----------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# --- CSRF -----------------------------------------------------------------
_csrf_extra = [o for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
CSRF_TRUSTED_ORIGINS = [
    f"https://{h.lstrip('.')}" for h in ALLOWED_HOSTS if h
] + _csrf_extra
