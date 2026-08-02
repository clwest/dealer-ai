import os
import sys
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
    # Milestone 7 · Increment 1 (SESSION_088) — DB-backed Celery Beat
    # scheduler. Installs the ``django_celery_beat_*`` tables
    # (PeriodicTask, CrontabSchedule, IntervalSchedule, etc.) so
    # future M7.2-M7.5 job schedules can be edited via Django admin
    # without a code deploy. Runtime scheduling is decoupled from this
    # setting — a schedule dict lives in ``CELERY_BEAT_SCHEDULE`` for
    # the code-first path, and the DatabaseScheduler picks up the DB
    # rows on top. Empty schedule at M7.1 — job bodies land in
    # M7.2-M7.5.
    "django_celery_beat",
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

# Milestone 2 · Increment 1 — dedicated migration-verification alias.
# Per `MILESTONE_1_RETROSPECTIVE.md` §6 lesson 2: SESSION_038 verified
# `migrate dealer_ai zero` → `migrate` against the live dev DB and
# wiped ~200 rows of seed data. The right pattern is a separate DB
# alias reserved for destructive migration probes. SQLite file at
# `backend/db.migration_check.sqlite3` — cheap, gitignored, and
# always safe to drop and recreate. Invoked with
# `python3 manage.py migrate --database=migration_check ...`.
DATABASES["migration_check"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.migration_check.sqlite3",
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

# Milestone 3 · Increment 4 — provider-neutral photo storage.
#
# Configuration uses Django 5.0's ``STORAGES`` dict (the modern
# successor to ``DEFAULT_FILE_STORAGE``). A dedicated
# ``condition_photos`` alias keeps the storage decision decoupled
# from the ``default`` alias so unrelated file fields (e.g. any
# future onboarding-logo migration) never inherit condition-report
# storage semantics silently. See
# ``docs/roadmap/MILESTONE_3_PLANNING.md`` §1.4 + §5.a for the
# design memo.
#
# The env-driven switch is intentional: unset ``AWS_STORAGE_BUCKET_NAME``
# → dev / test uses local ``FileSystemStorage`` under
# ``MEDIA_ROOT/condition-photos``. Tests therefore make **zero** S3
# network calls unless an operator has explicitly configured a
# bucket via env.
#
# Env vars (all optional; if unset, dev / test uses FileSystemStorage):
#   - ``AWS_STORAGE_BUCKET_NAME`` — presence triggers S3 mode.
#   - ``AWS_S3_REGION_NAME`` — e.g. ``us-east-1``.
#   - ``AWS_S3_ENDPOINT_URL`` — for S3-compatible providers
#     (DigitalOcean Spaces, Backblaze B2, Cloudflare R2, MinIO).
#   - ``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY`` — or IAM
#     role in prod. django-storages / boto3 read these from env
#     automatically per the standard AWS SDK credential chain.
#   - ``AWS_S3_CUSTOM_DOMAIN`` — CDN in front of the bucket
#     (CloudFront / Cloudflare). Optional.
#
# Security invariants (locked by ``tests/test_photo_storage.py``):
#   - ``default_acl=None`` — no public ACL is ever set on uploads.
#   - ``querystring_auth=True`` — every read URL is signed +
#     short-lived. No permanent public URLs.
#   - Presigned URL TTL capped at 900 seconds
#     (``services/photo_storage._MAX_TTL_SECONDS``).
_condition_photos_bucket = os.getenv("AWS_STORAGE_BUCKET_NAME", "").strip()
if _condition_photos_bucket:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
        "condition_photos": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": _condition_photos_bucket,
                "region_name": os.getenv("AWS_S3_REGION_NAME", "us-east-1"),
                "endpoint_url": os.getenv("AWS_S3_ENDPOINT_URL") or None,
                "custom_domain": os.getenv("AWS_S3_CUSTOM_DOMAIN") or None,
                # Private uploads only — never public-read.
                "default_acl": None,
                # Every read URL is signed + short-lived.
                "querystring_auth": True,
                # Never overwrite an existing object at the same key
                # (defense against key collisions; every canonical key
                # embeds a UUID so collisions are already vanishingly
                # rare).
                "file_overwrite": False,
            },
        },
    }
else:
    # Dev / test — FileSystemStorage under a dedicated subdir of
    # MEDIA_ROOT. Callers of ``services/photo_storage`` receive
    # local-mode URLs that are explicitly non-production markers;
    # see the service module docstring for the local contract.
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
        "condition_photos": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {
                "location": str(MEDIA_ROOT / "condition-photos"),
            },
        },
    }

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

# Franchise config env-override path. The resolver
# `services/dealer_config.get_dealer_profile()` reads these via
# ``getattr(settings, ...)`` and layers them BETWEEN the persisted
# `DealerOnboardingProfile` and the Copper Canyon defaults. Empty
# strings (the default) → resolver falls through to defaults.
# Documented in `MILESTONE_1_PLANNING.md` §3 "Existing dealer
# configuration resolution".
DEALER_AI_DEALER_TYPE = os.getenv("DEALER_AI_DEALER_TYPE", "")
DEALER_AI_PRIMARY_MAKE = os.getenv("DEALER_AI_PRIMARY_MAKE", "")

# Milestone 7 · Increment 1 (SESSION_088) — Celery + Redis async
# infrastructure. VCP Phase 6 mandate: "no Celery earlier" — M7 is the
# first milestone with recurring background work to run. Per
# ``MILESTONE_7_PLANNING.md`` §5.a-§5.e (user-confirmed at SESSION_088
# open): broker = Redis (§5.a), framework = Celery (§5.b),
# observability = ``JobRunLog`` Django model (§5.e).
#
# ``CELERY_*`` keys are read by ``dealer_kit/celery.py`` via
# :meth:`celery.Celery.config_from_object` with the ``CELERY``
# namespace. E.g. ``CELERY_BROKER_URL`` here binds to
# ``app.conf.broker_url``.
#
# **Broker + result backend.** Redis, one URL for both. Env-driven so
# prod can point at a managed Redis (Upstash / AWS ElastiCache / DO
# Managed Redis) without a code change.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL


def _is_running_tests() -> bool:
    """Return True when Django's test runner is executing.

    Mirrors ``dealer_ai.apps._is_running_tests`` — kept as a settings-
    level twin so ``CELERY_TASK_ALWAYS_EAGER`` can be computed at
    settings-import time (before ``AppConfig.ready`` runs). Detects
    via ``sys.argv`` — ``manage.py test`` or ``manage.py test <app>``.
    Also true when the runner is invoked programmatically (e.g.
    ``django-admin test`` or a CI wrapper passing ``test`` as the first
    positional arg).
    """
    if len(sys.argv) < 2:
        return False
    return sys.argv[1] == "test" or "test" in sys.argv


# Test posture per M7 §5.f. ``ALWAYS_EAGER=True`` in tests → every
# ``@shared_task`` invocation runs synchronously in the calling thread,
# so the test suite never depends on a running broker or worker. In
# dev / prod the setting is False — jobs land on the Redis broker and
# a real Celery worker picks them up. ``EAGER_PROPAGATES=True`` in
# tests so exceptions raised by task bodies propagate to the caller
# (otherwise Celery swallows them into ``EagerResult.failed=True``,
# which is worse for test signal).
CELERY_TASK_ALWAYS_EAGER = _is_running_tests()
CELERY_TASK_EAGER_PROPAGATES = _is_running_tests()

# Beat schedule. M7.2 (SESSION_089) added the first entry: the daily
# floor-plan interest accrual orchestrator. Each scheduled increment
# appends its entry here. Kept as a dict (not ``None``) so downstream
# code can call ``.get()`` / iterate without a guard.
#
# Timezone note: ``CELERY_TIMEZONE`` below binds these ``crontab``
# entries to the project's ``TIME_ZONE`` (America/Chicago). A
# ``crontab(hour=2, minute=0)`` entry therefore means "02:00 project-
# time" — not 02:00 UTC. Per-tenant local time is deliberately not
# supported at v1; see the tasks module docstring for the rationale.
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE: dict = {
    "floor-plan-accrual-daily-02-00": {
        "task": (
            "dealer_ai.services.floor_plan.tasks"
            ".accrue_daily_interest_for_all_tenants"
        ),
        # 02:00 project-time daily. Chosen because the M2 accrual is
        # a whole-day arithmetic operation and 02:00 is late enough
        # to be past midnight in every US timezone the operator base
        # might sit in.
        "schedule": crontab(hour=2, minute=0),
        # No positional args; ``as_of_iso=None`` in the task kwargs
        # means "default to today" at task-run time.
        "kwargs": {},
    },
    "stage-aging-snapshot-daily-03-00": {
        "task": (
            "dealer_ai.services.lifecycle_aging.tasks"
            ".snapshot_stage_ages_for_all_tenants"
        ),
        # 03:00 project-time daily — one hour after the M7.2
        # floor-plan accrual job so both tasks do not contend for
        # Celery workers in the same maintenance window. The snapshot
        # job is read-heavy (scans every VehicleStage row per tenant)
        # so keeping it isolated from the accrual job's ledger writes
        # also simplifies operator triage if one starts failing.
        "schedule": crontab(hour=3, minute=0),
        # ``snapshot_at_iso=None`` in the task kwargs means each
        # per-tenant task defaults to ``timezone.now()`` at the moment
        # IT runs. See the M7.3 tasks docstring for the coordinated-
        # snapshot alternative.
        "kwargs": {},
    },
    "vendor-sla-scan-daily-04-00": {
        "task": (
            "dealer_ai.services.vendor_sla.tasks"
            ".detect_sla_breaches_for_all_tenants"
        ),
        # 04:00 project-time daily — one hour after the M7.3 aging
        # snapshot job. Continues the non-overlapping window pattern
        # (M7.2 at 02:00, M7.3 at 03:00, M7.4 at 04:00) so operator
        # triage is straightforward when one of the three job families
        # starts failing.
        "schedule": crontab(hour=4, minute=0),
        # ``as_of_iso=None`` in the task kwargs means each per-tenant
        # task defaults to today.
        "kwargs": {},
    },
    "photo-tombstone-reaper-daily-05-00": {
        "task": (
            "dealer_ai.services.photo_gallery.tasks"
            ".reap_tombstoned_photos_for_all_tenants"
        ),
        # 05:00 project-time daily — one hour after the M7.4 vendor
        # SLA scan. Continues the non-overlapping window pattern
        # (M7.2 at 02:00, M7.3 at 03:00, M7.4 at 04:00, M7.5 at
        # 05:00) so the four job families stay in separate maintenance
        # windows. Positioned last because it's the only job that
        # physically deletes data — running it after every read-heavy
        # aggregation job (M7.3 aging) and every DB-write accrual job
        # (M7.2 floor-plan) means the day's snapshots + accruals ran
        # against pre-reap data.
        "schedule": crontab(hour=5, minute=0),
        # ``as_of_iso=None`` in the task kwargs means each per-tenant
        # task defaults to ``timezone.now()``.
        "kwargs": {},
    },
    "follow-up-task-surface-daily-06-00": {
        "task": (
            "dealer_ai.services.follow_ups.tasks"
            ".surface_due_follow_up_tasks_for_all_tenants"
        ),
        # 06:00 project-time daily — one hour after the M7.5
        # tombstone reaper. Continues the non-overlapping window
        # pattern (M7.2 at 02:00, M7.3 at 03:00, M7.4 at 04:00,
        # M7.5 at 05:00, M11.4 at 06:00). The M11.4 orchestrator is
        # read-only — it counts + logs due pending tasks per tenant
        # but never transitions state (operator intent is required
        # for every state transition per SESSION_117 §0.a M11.4
        # decision 3). Positioned after M7.5 so the daily task
        # surfacing sees today's snapshots + accruals reflected in
        # any lead-status filters that get added downstream.
        "schedule": crontab(hour=6, minute=0),
        # No positional args; the orchestrator takes no kwargs.
        "kwargs": {},
    },
    "be-back-no-show-detector-daily-07-00": {
        "task": (
            "dealer_ai.services.be_backs.tasks"
            ".detect_no_show_be_backs_for_all_tenants"
        ),
        # 07:00 project-time daily — one hour after the M11.4
        # follow-up surfacer. Continues the non-overlapping window
        # pattern (M7.2 at 02:00, M7.3 at 03:00, M7.4 at 04:00,
        # M7.5 at 05:00, M11.4 at 06:00, M11.5 at 07:00). Distinct
        # from the M11.4 surfacer in one key way — this task
        # *does* transition state (per SESSION_118 §0.a M11.5
        # decision §5.g.3 Option B). The M11.4 surfacer is read-
        # only because task completion is operator-intent; the M11.5
        # detector auto-transitions promised → no_show because the
        # promise is the customer's, not the operator's, and the
        # detector only reflects an already-elapsed grace period.
        "schedule": crontab(hour=7, minute=0),
        # No positional args; the orchestrator takes no kwargs.
        "kwargs": {},
    },
    "bhph-delinquency-detector-daily-08-00": {
        "task": (
            "dealer_ai.services.bhph_delinquency.tasks"
            ".detect_delinquencies_for_all_tenants"
        ),
        # 08:00 project-time daily — one hour after the M11.5
        # no-show detector. Continues the non-overlapping window
        # pattern (M7.2 at 02:00, M7.3 at 03:00, M7.4 at 04:00,
        # M7.5 at 05:00, M11.4 at 06:00, M11.5 at 07:00, M12.3 at
        # 08:00). State-transitioning per M11 §6 lesson 17 — aging
        # is objectively elapsed (calendar math), same posture as
        # the M11.5 detector. Recomputes ``current_bucket`` +
        # ``days_past_due`` on every active BhphNote per tenant;
        # only writes when the derived value differs from the
        # stored value (idempotent within a run).
        "schedule": crontab(hour=8, minute=0),
        # No positional args; the orchestrator takes no kwargs.
        "kwargs": {},
    },
}

# ---- Milestone 11 · Increment 5 (SESSION_118) — BeBack no-show grace.
# Configurable via env or settings override. Zero → transition on the
# moment ``promised_at`` passes; higher values give operators more
# room. Four hours is the default per §0.a M11.5 amendment (§5.g.3
# Option B recommendation — matches operator reality that a customer
# a few hours late isn't yet a no-show).
BE_BACK_NO_SHOW_GRACE_HOURS = int(os.getenv("BE_BACK_NO_SHOW_GRACE_HOURS", "4"))

# DB-backed scheduler (django-celery-beat). PeriodicTask + CrontabSchedule
# rows shipped by the ``django_celery_beat`` app hold the source of truth
# in the DB so operators can edit schedules via Django admin without a
# code deploy. The ``CELERY_BEAT_SCHEDULE`` dict above stays as the
# code-first bootstrap; the DB rows layer on top at Beat start.
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Timezone alignment. Beat schedules are interpreted in ``TIME_ZONE`` so
# a ``crontab(hour=2, minute=0)`` entry means "02:00 America/Chicago"
# rather than 02:00 UTC. Matches Django's ``USE_TZ=True`` posture — no
# implicit UTC bounces at task-invocation time.
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Task-serialization pins. JSON only — no pickle. Guards against a
# future ``services/**/tasks.py`` module accidentally passing a
# non-serializable object (Django model instance, Decimal that isn't
# str-cast, etc.) and having Celery silently pickle it. JSON forces the
# error to surface at ``apply_async`` time.
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

# Milestone 2 · Increment 4a — floor-plan APR env override. Consumed
# by ``dealer_ai.services.dealer_config.get_floor_plan_apr`` which
# layers DB (``DealerOnboardingProfile.floor_plan_apr``) → this env →
# Copper Canyon default (8.5%). Empty string = "unset, resolver falls
# through to next layer." Expressed in **percent units** to match
# ``DEFAULT_APR`` in ``services/payment_engine.py`` and every existing
# APR-in-payment-engine call site. Example:
# ``DEALER_AI_FLOOR_PLAN_APR=6.25`` sets the tenant's floor-plan APR
# to 6.25% for every accrual until a real profile value is saved.
DEALER_AI_FLOOR_PLAN_APR = os.getenv("DEALER_AI_FLOOR_PLAN_APR", "")
