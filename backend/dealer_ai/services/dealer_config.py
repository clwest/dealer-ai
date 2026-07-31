"""Runtime dealer-identity resolver used by every LLM prompt + template.

The kit ships with **no dealer** baked in. Every module that used to
hardcode dealer-specific strings now formats its prompt/response with
``{dealer_name}`` (or reads the full ``DealerProfile`` for richer
shape-of-business questions) and resolves the value at call time via
:func:`get_dealer_name` / :func:`get_dealer_profile`.

Resolution order for ``name`` (first non-empty wins):

1. ``settings.DEALER_AI_DEALER_NAME`` (env-driven —
   ``DEALER_AI_DEALER_NAME=...`` in ``backend/.env`` or repo-root
   ``.env``).
2. ``DealerOnboardingProfile.dealership_name`` (the singleton persisted
   via the Setup UI — matches the source-of-truth ``useBrand()`` uses on
   the frontend).
3. ``"the dealership"`` — a bland but sentence-safe fallback so
   generated copy stays coherent when nothing is configured yet.

Resolution order for the rest of the profile:

- ``settings.DEALER_AI_DEALER_TYPE`` env override for
  :attr:`DealerProfile.dealer_type` (``"independent"`` /
  ``"franchise"``).
- Otherwise the Copper Canyon Auto independent-dealer defaults below.

The Phase 3 pivot work extends ``DealerOnboardingProfile`` with the
rest of the fields (``bhph_enabled``, ``subprime_lenders``,
``floor_plan_lender``, ``warranty_offering``, ``credit_range_served``,
``makes_carried``) and threads them through this resolver. Until that
migration lands, the defaults represent the shipped Copper Canyon Auto
demo persona; env overrides are the escape hatch for franchise or
alternate-config testing.

Keep this module *dependency-light*: importing it must not require the
Django app registry to be ready, so DB access is lazy and swallowed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from django.conf import settings

_FALLBACK_DEALER_NAME = "the dealership"

DealerType = Literal["independent", "franchise"]


@dataclass(frozen=True)
class DealerProfile:
    """Shape of the currently-configured dealer.

    Immutable so prompt templates and payment-engine callers can cache
    the result within a request without worrying about mid-turn edits.

    ``primary_make`` is ``None`` for independent (mixed-lot) dealers and
    the OEM brand for a franchise config. It drives the inventory
    ranking key in :mod:`chat_engine` — franchise deployments still get
    "primary brand first" ordering; indies rank purely on financial fit.
    """

    name: str
    dealer_type: DealerType
    primary_make: str | None
    bhph_enabled: bool
    subprime_lenders: tuple[str, ...]
    floor_plan_lender: str
    warranty_offering: str
    credit_range_served: str
    makes_carried: tuple[str, ...]


# Copper Canyon Auto — Yuma, AZ — invented independent-dealer persona
# that ships as the kit's shape-of-business default per
# docs/INDEPENDENT_DEALER_PIVOT.md. `.name` is intentionally left as the
# sentence-safe fallback so unconfigured copy still reads as generic
# ("the dealership") rather than surprising a fresh install with an
# invented brand name. Callers wanting the persona name should either
# set DEALER_AI_DEALER_NAME env, populate DealerOnboardingProfile via
# the Setup UI, or override in tests.
#
# The invented subprime-lender names ("Sonoran Credit", "Desert Auto
# Finance", "Vista Lending") are provisional — flagged as open
# question 3 in INDEPENDENT_DEALER_PIVOT.md, to be locked when Phase 2
# seed data ships.
_COPPER_CANYON_DEFAULTS = DealerProfile(
    name=_FALLBACK_DEALER_NAME,
    dealer_type="independent",
    # Indie mixed-lot has no primary brand — every make competes on
    # financial fit. Franchise deployments set DEALER_AI_PRIMARY_MAKE
    # (or Phase 3's DealerOnboardingProfile field) to restore
    # primary-brand-first ranking.
    primary_make=None,
    bhph_enabled=True,
    subprime_lenders=(
        "Sonoran Credit",
        "Desert Auto Finance",
        "Vista Lending",
    ),
    floor_plan_lender="NextGear",
    warranty_offering="30-day / 1000-mile powertrain",
    credit_range_served="580+ with strong down; BHPH below",
    makes_carried=(
        "Toyota",
        "Honda",
        "Ford",
        "Chevy",
        "Nissan",
        "Kia",
    ),
)


def get_dealer_name() -> str:
    """Return the display name for the currently-configured dealer."""
    env_name = (getattr(settings, "DEALER_AI_DEALER_NAME", "") or "").strip()
    if env_name:
        return env_name

    try:
        # Lazy import so this module is safe to import at settings-load time.
        from ..models import DealerOnboardingProfile

        profile = DealerOnboardingProfile.objects.first()
        if profile:
            name = (profile.dealership_name or "").strip()
            if name:
                return name
    except Exception:
        # Table doesn't exist yet (fresh install pre-migrate), DB is
        # offline, or the model import fails. Fall through to the
        # bland default rather than crash any caller.
        pass

    return _FALLBACK_DEALER_NAME


def get_dealer_profile() -> DealerProfile:
    """Return the full shape of the currently-configured dealer.

    For the SESSION_030 pivot, ``name``, ``dealer_type``, and
    ``primary_make`` have real dynamic resolution paths. The rest come
    from the Copper Canyon Auto independent-dealer defaults until
    Phase 3 extends ``DealerOnboardingProfile`` with the remaining
    fields.
    """
    dealer_type_env = (
        getattr(settings, "DEALER_AI_DEALER_TYPE", "") or ""
    ).strip().lower()
    if dealer_type_env in ("independent", "franchise"):
        dealer_type: DealerType = dealer_type_env  # type: ignore[assignment]
    else:
        dealer_type = _COPPER_CANYON_DEFAULTS.dealer_type

    primary_make_env = (
        getattr(settings, "DEALER_AI_PRIMARY_MAKE", "") or ""
    ).strip()
    primary_make = primary_make_env or _COPPER_CANYON_DEFAULTS.primary_make

    return replace(
        _COPPER_CANYON_DEFAULTS,
        name=get_dealer_name(),
        dealer_type=dealer_type,
        primary_make=primary_make,
    )
