"""SESSION_240 (walk finding 28) — one clock per store.

Every business-day decision — the ledger's "today", aging buckets,
BHPH delinquency day-counts, floor-plan accrual, the 07:00 be-back
detector, follow-up cadences — used to read
``django.utils.timezone.now().date()``, which resolves to the project
``TIME_ZONE`` (``America/Chicago``). A Yuma store that sells a car at
22:00 local Phoenix time would book it to tomorrow because Chicago
had already rolled past midnight.

This module holds the three helpers that consume the per-store
``Dealership.timezone``:

- :func:`store_now` — ``datetime`` right now, aware, in the store's
  zone.
- :func:`store_today` — the store's local ``date`` right now.
- :func:`store_localize` — convert an aware ``datetime`` into the
  store's local zone.

Plus two thin conveniences that Celery Beat wants:

- :func:`store_local_hour` — the store's clock hour right now (0-23).
- :func:`suggest_timezone_for_state` — default a store's zone from
  its two-letter state; a one-zone state resolves outright, a
  multi-zone state returns ``None`` so the operator picks and the
  onboarding page says so.

The module deliberately accepts a ``Dealership`` (not a raw name)
because forgetting to pass one is a bug we want the type checker to
catch, and because passing the model instance means the helper can
never look at the wrong tenant's clock. A ``None`` argument falls
back to the project ``TIME_ZONE`` so tests and management commands
that legitimately don't have a dealership in scope (e.g. an
orchestrator counting all tenants) keep working.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.utils import timezone


def _project_zone() -> ZoneInfo:
    """Return the project-default zone, tolerating a missing TIME_ZONE."""
    name = getattr(settings, "TIME_ZONE", "UTC") or "UTC"
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _zone_for(dealership) -> ZoneInfo:
    """Resolve a store's zone; fall back to project TIME_ZONE.

    ``dealership`` may be ``None`` (project default) or an object with
    a ``timezone`` attribute (the ``Dealership`` model, or a stub in
    tests). An unknown IANA name silently downgrades to project TIME_ZONE
    — the Dealership.save() guard should make this branch cold, but the
    fallback keeps a legacy row from crashing a request handler.
    """
    if dealership is None:
        return _project_zone()
    name = getattr(dealership, "timezone", "") or ""
    if not name:
        return _project_zone()
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return _project_zone()


def store_now(dealership) -> datetime:
    """Return the current instant as an aware :class:`datetime` in the
    store's zone.

    Prefer this over ``timezone.now()`` at every site whose result
    ends up in a user-visible "today" or drives a business-day
    decision. The returned value is still the same instant — only the
    displayed tz-offset differs — so a comparison against a
    UTC-aware column continues to work.
    """
    return timezone.now().astimezone(_zone_for(dealership))


def store_today(dealership) -> date:
    """Return the store's local :class:`date` right now.

    This is the replacement for ``timezone.now().date()`` /
    ``date.today()`` at every business-day boundary. A car sold at
    22:00 Phoenix on 2026-09-03 must book to 2026-09-03, not to
    2026-09-04 (which is what Chicago's clock would say).
    """
    return store_now(dealership).date()


def store_localize(dt: datetime, dealership) -> datetime:
    """Convert an aware ``datetime`` into the store's local zone.

    A naive ``datetime`` is assumed to already be in the store's zone
    and gets attached to it (this preserves the "the stored wall-time
    was store-local" reading — safer than assuming UTC). Aware
    datetimes are simply reprojected.
    """
    zone = _zone_for(dealership)
    if timezone.is_naive(dt):
        return dt.replace(tzinfo=zone)
    return dt.astimezone(zone)


def store_local_hour(dealership) -> int:
    """The store's clock hour right now (0-23)."""
    return store_now(dealership).hour


# SESSION_240 — state → default IANA zone. Split from the mapping in
# models.py so the runtime consumer (Celery task deciding "does this
# store's clock read 07:00?") does not have to import from models. Kept
# in sync by importing the same dict at reference time.
def suggest_timezone_for_state(state_code: str) -> str | None:
    """Return the default IANA zone for a two-letter US state, or
    ``None`` if the state spans multiple zones.

    A ``None`` return is the signal that the onboarding page must say
    "your state has more than one zone — pick one" rather than silently
    guessing. Multi-zone states: FL, IN, KY, MI, ND, SD, TN, TX
    (the "unset in defaults" set).
    """
    from ..models import _STATE_TIMEZONE_DEFAULTS

    if not state_code:
        return None
    return _STATE_TIMEZONE_DEFAULTS.get(state_code.strip().upper())
