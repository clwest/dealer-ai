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

Resolution order for the rest of the profile (SESSION_032 threaded
``DealerOnboardingProfile`` values through here — persistence lives on
the singleton row managed by ``/dealer-ai-onboarding``):

- ``dealer_type``: ``DealerOnboardingProfile.dealer_type`` when
  non-empty → ``settings.DEALER_AI_DEALER_TYPE`` env override →
  Copper Canyon default ``"independent"``.
- ``primary_make``: ``settings.DEALER_AI_PRIMARY_MAKE`` env override →
  Copper Canyon default (``None`` for indie mixed-lot).
- ``bhph_enabled``: ``DealerOnboardingProfile.bhph_enabled`` **only
  when** ``bhph_configured`` is ``True`` (that flag flips the first
  time the profile is saved via the Setup UI, distinguishing "user
  explicitly toggled" from "migration default"). Otherwise Copper
  Canyon default (``True``).
- ``subprime_lenders``, ``makes_carried``: newline-separated
  ``DealerOnboardingProfile`` text field → parsed into a tuple.
  Empty → Copper Canyon default tuple. ``makes_carried`` falls back
  to the legacy CSV ``main_brands`` field when both new and
  ``main_brands`` are populated but ``makes_carried`` is blank.
- ``floor_plan_lender``, ``warranty_offering``,
  ``credit_range_served``: ``DealerOnboardingProfile`` string when
  non-empty → Copper Canyon default.

Env overrides remain the escape hatch for franchise / alternate-config
testing without touching the DB row.

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


def _parse_lines(raw: str) -> tuple[str, ...]:
    """Split a newline-separated TextField value into a tuple of
    trimmed non-empty strings. Matches the convention used by the
    ``approved_phrases`` / ``banned_phrases`` scrub loaders."""
    return tuple(
        line.strip()
        for line in (raw or "").splitlines()
        if line.strip()
    )


def _parse_csv(raw: str) -> tuple[str, ...]:
    """Split the legacy ``main_brands`` CSV field. Kept separate from
    :func:`_parse_lines` so a future migration that copies
    ``main_brands`` → ``makes_carried`` can pick either parser
    explicitly."""
    return tuple(
        item.strip()
        for item in (raw or "").split(",")
        if item.strip()
    )


def get_dealer_profile() -> DealerProfile:
    """Return the full shape of the currently-configured dealer.

    Every field has a documented resolution order — see this module's
    docstring. DB access is lazy + exception-swallowed so importing
    this module never requires a ready app registry, and a fresh
    install pre-migrate still returns the Copper Canyon defaults.
    """
    profile = None
    try:
        # Lazy import so this module stays safe at settings-load time.
        from ..models import DealerOnboardingProfile

        profile = DealerOnboardingProfile.objects.first()
    except Exception:
        # Table missing (pre-migrate), DB offline, or import failure.
        # Fall through — every field below has a hardcoded fallback.
        profile = None

    # dealer_type: DB → env → default.
    if profile and (profile.dealer_type or "").strip():
        dealer_type: DealerType = profile.dealer_type  # type: ignore[assignment]
    else:
        dealer_type_env = (
            getattr(settings, "DEALER_AI_DEALER_TYPE", "") or ""
        ).strip().lower()
        if dealer_type_env in ("independent", "franchise"):
            dealer_type = dealer_type_env  # type: ignore[assignment]
        else:
            dealer_type = _COPPER_CANYON_DEFAULTS.dealer_type

    # primary_make: env → default (no DB field; franchise config is
    # environment-driven for the primary-make ranking key).
    primary_make_env = (
        getattr(settings, "DEALER_AI_PRIMARY_MAKE", "") or ""
    ).strip()
    primary_make = primary_make_env or _COPPER_CANYON_DEFAULTS.primary_make

    # bhph_enabled: DB when explicitly configured → default. The
    # `bhph_configured` sentinel flips True on the first save via the
    # Setup UI so we can distinguish "user toggled off" from
    # "migration default of True".
    if profile and profile.bhph_configured:
        bhph_enabled = profile.bhph_enabled
    else:
        bhph_enabled = _COPPER_CANYON_DEFAULTS.bhph_enabled

    # subprime_lenders: DB newline-separated → default tuple. Empty DB
    # value means "not yet configured, use demo defaults"; a dealer
    # who truly has no subprime panel should be represented by the
    # onboarding form storing a single sentinel entry (future
    # enhancement) or via env override.
    if profile:
        subprime_lenders = _parse_lines(profile.subprime_lenders) \
            or _COPPER_CANYON_DEFAULTS.subprime_lenders
    else:
        subprime_lenders = _COPPER_CANYON_DEFAULTS.subprime_lenders

    # floor_plan_lender, warranty_offering, credit_range_served:
    # DB non-empty → default.
    def _prefer_profile(attr: str, fallback: str) -> str:
        if profile and (getattr(profile, attr, "") or "").strip():
            return getattr(profile, attr).strip()
        return fallback

    floor_plan_lender = _prefer_profile(
        "floor_plan_lender", _COPPER_CANYON_DEFAULTS.floor_plan_lender
    )
    warranty_offering = _prefer_profile(
        "warranty_offering", _COPPER_CANYON_DEFAULTS.warranty_offering
    )
    credit_range_served = _prefer_profile(
        "credit_range_served", _COPPER_CANYON_DEFAULTS.credit_range_served
    )

    # makes_carried: DB newline-separated → legacy main_brands CSV
    # fallback → Copper Canyon default tuple. The two-level fallback
    # lets legacy profiles that only populated `main_brands` (the
    # pre-SESSION_032 franchise-oriented CSV field) continue to
    # surface their brand mix through the new API contract without a
    # data-migration commit.
    if profile:
        makes_carried = (
            _parse_lines(profile.makes_carried)
            or _parse_csv(profile.main_brands)
            or _COPPER_CANYON_DEFAULTS.makes_carried
        )
    else:
        makes_carried = _COPPER_CANYON_DEFAULTS.makes_carried

    return replace(
        _COPPER_CANYON_DEFAULTS,
        name=get_dealer_name(),
        dealer_type=dealer_type,
        primary_make=primary_make,
        bhph_enabled=bhph_enabled,
        subprime_lenders=subprime_lenders,
        floor_plan_lender=floor_plan_lender,
        warranty_offering=warranty_offering,
        credit_range_served=credit_range_served,
        makes_carried=makes_carried,
    )
