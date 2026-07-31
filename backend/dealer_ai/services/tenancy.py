"""Milestone 1 · Increment 3 — default-tenancy resolver + write-path safety net.

The kit is still single-tenant at every request boundary today; every
tenant-carrying row therefore belongs to the deterministically-seeded
default :class:`Dealership` (``slug="default"``) created by data-migration
``0009_backfill_dealership_fks``.

This module is the *single source of truth* for that resolution. Future
increments will layer request-context resolution on top (e.g. reading a
tenant from the authenticated user or an incoming ``X-Dealership-Slug``
header) but they will delegate to :func:`get_default_dealership` as the
fallback path. The primitive is deliberately small so the extension
happens *inside* it, not by paralleling it.

Two consumers:

1. :func:`services.dealer_config.get_dealer_name` /
   :func:`services.dealer_config.get_dealer_profile` — read-path
   resolvers for prompt templating and payment-engine math.
2. The :func:`_auto_attach_default_dealership` ``pre_save`` signal
   handler registered against the six tenant carriers — the write-path
   safety net. Any ``save()`` on ``Vehicle`` / ``Salesperson`` /
   ``ChatSession`` / ``ChatMessage`` / ``CustomerLead`` /
   ``DealerOnboardingProfile`` where ``dealership_id is None`` gets the
   default attached automatically. Callers that already set
   ``dealership=`` (production views, seeders, request-context code
   in later increments) short-circuit the fallback — the handler never
   overwrites an explicit value.

Import-safety: the module never touches the DB at import time. The
first :func:`get_default_dealership` call performs the lookup and
caches the primary key at module scope. :func:`reset_default_dealership_cache`
exists for tests that re-create the test database mid-run.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models.signals import pre_save

if TYPE_CHECKING:  # pragma: no cover — typing-only import
    from ..models import Dealership


_DEFAULT_SLUG = "default"

# Module-level PK cache. The migration-seeded default row has a stable
# PK across the life of a single process (Django test runners recreate
# the DB once per run and reuse it across tests). We cache the PK, not
# the model instance, so a fresh ``.get(pk=...)`` lookup runs per call
# — cheap (single indexed hit) and always returns a live-connection
# instance instead of a stale cached one.
_default_dealership_pk: int | None = None


class DealershipNotConfigured(RuntimeError):
    """Raised when :func:`get_default_dealership` is called before the
    ``0009_backfill_dealership_fks`` migration has seeded the default
    row.

    This should only surface pre-migrate — after migration, the row is
    guaranteed to exist. If a test sees this, either the migration was
    skipped or the row was deleted mid-test; both are bugs.
    """


def get_default_dealership() -> "Dealership":
    """Return the deterministic default :class:`Dealership` row.

    The row is created by data-migration ``0009_backfill_dealership_fks``
    with ``slug="default"``. Every ``save()`` on a tenant-carrying model
    without an explicit ``dealership=`` gets attached here by the
    ``pre_save`` handler below.

    Raises :class:`DealershipNotConfigured` if the row is missing.
    """
    global _default_dealership_pk

    from ..models import Dealership  # lazy: keep this module import-safe

    if _default_dealership_pk is not None:
        try:
            return Dealership.objects.get(pk=_default_dealership_pk)
        except Dealership.DoesNotExist:
            # Test DB was recreated / row was deleted; fall through to
            # the slug lookup below and re-cache.
            _default_dealership_pk = None

    try:
        default = Dealership.objects.get(slug=_DEFAULT_SLUG)
    except Dealership.DoesNotExist as exc:
        raise DealershipNotConfigured(
            "Default Dealership row missing. Ensure migration "
            "0009_backfill_dealership_fks has run."
        ) from exc

    _default_dealership_pk = default.pk
    return default


def reset_default_dealership_cache() -> None:
    """Clear the module-level PK cache.

    Useful for tests that flush and re-seed the tenant carrier rows,
    or that re-create the test database mid-run. Safe to call at any
    time — the next :func:`get_default_dealership` call rehydrates from
    the DB.
    """
    global _default_dealership_pk
    _default_dealership_pk = None


# ---- pre_save signal — write-path safety net --------------------------------

# Model names covered by the fallback. Kept as strings so the handler
# registration in :func:`register_default_dealership_autofill` doesn't
# trigger app-registry access at import time — the actual model class
# lookup happens inside ``AppConfig.ready()``.
_TENANT_CARRIER_MODEL_NAMES = (
    "Vehicle",
    "Salesperson",
    "ChatSession",
    "ChatMessage",
    "CustomerLead",
    "DealerOnboardingProfile",
)


def _auto_attach_default_dealership(sender, instance, **kwargs) -> None:  # noqa: ARG001
    """``pre_save`` handler: fill ``instance.dealership_id`` when the
    caller left it unset.

    Resolution order:

    1. Explicit ``dealership=`` on ``.create()`` / ``.save()`` — the
       fallback is a no-op when ``dealership_id`` is already populated.
       This preserves the explicit-tenant path that future
       request-context resolution will use.
    2. Parent-record inheritance — if ``instance`` has a ``session_id``
       (``ChatMessage`` and ``CustomerLead`` both do) and the parent
       ``ChatSession`` has a ``dealership_id``, inherit. This keeps
       child rows tenant-consistent with their parent session without
       requiring every caller to plumb the tenant argument through.
    3. Default tenancy — :func:`get_default_dealership`.
    """
    if getattr(instance, "dealership_id", None) is not None:
        return

    session_id = getattr(instance, "session_id", None)
    if session_id is not None:
        parent_dealership_id = _parent_session_dealership_id(sender, session_id)
        if parent_dealership_id is not None:
            instance.dealership_id = parent_dealership_id
            return

    instance.dealership = get_default_dealership()


def _parent_session_dealership_id(sender, session_id) -> int | None:
    """Return the ``dealership_id`` of the parent ``ChatSession``, or
    ``None`` if the session is missing or has no tenancy set yet.

    Uses ``.values_list()`` so exactly one column round-trips per
    inherited save (avoids materializing the full ``ChatSession``
    instance in the hot path)."""
    from django.apps import apps as django_apps

    # Only lookup for models whose `session` FK actually points at
    # ChatSession — guard against false positives if a future model
    # names a field `session` for something else.
    session_field = sender._meta.get_field("session") if _has_field(sender, "session") else None
    if session_field is None:
        return None
    if session_field.related_model is not django_apps.get_model("dealer_ai", "ChatSession"):
        return None

    ChatSession = django_apps.get_model("dealer_ai", "ChatSession")
    return (
        ChatSession.objects.filter(pk=session_id)
        .values_list("dealership_id", flat=True)
        .first()
    )


def _has_field(model, name: str) -> bool:
    try:
        model._meta.get_field(name)
    except Exception:
        return False
    return True


def register_default_dealership_autofill() -> None:
    """Wire :func:`_auto_attach_default_dealership` into ``pre_save`` for
    each tenant carrier.

    Called from :meth:`dealer_ai.apps.DealerAiConfig.ready`. Idempotent
    — Django dispatch deduplicates handler+sender pairs when ``dispatch_uid``
    is set.
    """
    from django.apps import apps as django_apps

    for model_name in _TENANT_CARRIER_MODEL_NAMES:
        Model = django_apps.get_model("dealer_ai", model_name)
        pre_save.connect(
            _auto_attach_default_dealership,
            sender=Model,
            dispatch_uid=f"dealer_ai.tenancy.autofill.{model_name}",
        )
