"""Milestone 19 · Increment 1 (SESSION_154) — pilot dealership registry verbs.

Three verbs per MILESTONE_19_PLANNING.md §7 M19.1 + §5.c Option A +
§5.d Option A + §5.h Option A (user-confirmed at SESSION_153 open,
recorded in §0.a):

- :func:`create_pilot_dealership` — atomic create + COA seed +
  owner membership + profile populate + auto-fired checklist.
- :func:`list_pilot_dealerships` — pure read (``is_pilot=True,
  terminated_at IS NULL``).
- :func:`terminate_pilot` — atomic termination with archive or
  cleanup mode per §5.h Option A.

**Belt-and-suspenders guard** per §5.h Option A: the
``terminate_pilot`` write path raises
:class:`NonPilotTerminationError` when called with a Dealership
where ``is_pilot=False`` AND ``assert dealership.is_pilot`` fires
at the top of the write verb. The layered check prevents a future
refactor that accidentally weakens one guard from compromising
the invariant.

**Cleanup mode** cascades reverse-order per M18.2's proven pattern
(child-before-parent for PROTECT FKs; demo-owned Users cleared for
username-collision safety on re-create).

**Archive mode** preserves child rows so a post-mortem review can
examine the pilot's operational data — but the pilot no longer
appears in the operator surface (``is_pilot=False`` after
termination; the ``terminated_at`` timestamp is populated).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from django.db import IntegrityError, transaction
from django.utils import timezone

from ...models import (
    PILOT_ONBOARDING_STEP_DEALERSHIP_CREATED,
    PILOT_TERMINATION_MODE_ARCHIVE,
    PILOT_TERMINATION_MODE_CHOICES,
    PILOT_TERMINATION_MODE_CLEANUP,
    ROLE_DEALER_OWNER,
    Dealership,
    DealerOnboardingProfile,
    PilotOnboardingChecklist,
    PilotOnboardingStep,
    UserDealershipRole,
)
from ..accounting import seed_default_coa
from .errors import NonPilotTerminationError, PilotAlreadyExistsError


_LOGGER = logging.getLogger("dealer_ai.pilot_onboarding.registry")

_VALID_TERMINATION_MODES = {key for key, _ in PILOT_TERMINATION_MODE_CHOICES}


@transaction.atomic
def create_pilot_dealership(
    *,
    slug: str,
    name: str,
    owner_user,
    profile_kwargs: Optional[dict[str, Any]] = None,
    actor=None,
) -> tuple[Dealership, PilotOnboardingChecklist]:
    """Create a fresh pilot dealership + seed COA + attach owner + fire checklist.

    Atomic — Dealership + GLAccount rows + UserDealershipRole +
    DealerOnboardingProfile + PilotOnboardingChecklist +
    ``dealership_created`` step all commit or nothing does. Partial
    pilot creation is architecturally impossible.

    Per §5.c Option A: the new Dealership has ``is_pilot=True``,
    ``is_demo=False``, ``outbound_enabled=False`` (per §0.a M19.1
    decision 2 — outbound suppressed by default for pilots).

    Refuses:

    - Slug collision with any existing Dealership (demo, pilot, or
      live) — :class:`PilotAlreadyExistsError` (409). Catches
      ``IntegrityError`` on the unique constraint + re-raises as
      the domain error per M17 §6 lesson 4 pattern.

    Returns a tuple of ``(Dealership, PilotOnboardingChecklist)``
    — the new pilot dealership and its auto-created checklist
    with the ``dealership_created`` step already completed.
    """
    try:
        dealership = Dealership.objects.create(
            slug=slug,
            name=name,
            is_demo=False,
            is_pilot=True,
            outbound_enabled=False,
        )
    except IntegrityError as exc:
        raise PilotAlreadyExistsError(
            f"A Dealership with slug {slug!r} already exists. Pilot "
            "slugs must be unique across all Dealership rows (demo, "
            "pilot, or live)."
        ) from exc

    # Seed the M13.1 default COA — every Dealership must have the
    # default chart of accounts for M15+ sale-booking GL post to
    # succeed. Matches the ``services/demo_store/registry`` posture.
    seed_default_coa(dealership)

    # Attach the owner user with dealer_owner role.
    UserDealershipRole.objects.create(
        user=owner_user,
        dealership=dealership,
        role=ROLE_DEALER_OWNER,
    )

    # Populate DealerOnboardingProfile from caller-supplied kwargs.
    # The model manages defaults for absent fields — Chris fills in
    # the profile progressively during onboarding via the
    # ``profile_configured`` checklist step.
    profile_data = profile_kwargs or {}
    DealerOnboardingProfile.objects.create(
        dealership=dealership,
        **profile_data,
    )

    # Auto-fire the checklist per §5.d Option A. The
    # ``dealership_created`` step is already complete at this point.
    checklist = PilotOnboardingChecklist.objects.create(
        dealership=dealership,
        is_ready=False,
    )
    PilotOnboardingStep.objects.create(
        dealership=dealership,
        checklist=checklist,
        step_slug=PILOT_ONBOARDING_STEP_DEALERSHIP_CREATED,
        completed_at=timezone.now(),
        completed_by=(
            actor if actor is not None and getattr(
                actor, "is_authenticated", False
            ) else None
        ),
        notes="Auto-completed by create_pilot_dealership.",
    )

    _LOGGER.info(
        "pilot dealership created",
        extra={
            "dealership_slug": slug,
            "owner_username": owner_user.username,
            "actor": str(actor) if actor is not None else None,
        },
    )
    return dealership, checklist


def list_pilot_dealerships() -> list[Dealership]:
    """Return every active pilot :class:`Dealership`.

    Pure. Read-only. Filters to ``is_pilot=True`` AND
    ``terminated_at IS NULL`` — terminated pilots are excluded from
    the operator surface (they survive in the DB with
    ``is_pilot=False, terminated_at=<timestamp>`` for audit trail
    per §5.h Option A).

    Ordered by ``slug`` for deterministic output.
    """
    return list(
        Dealership.objects.filter(
            is_pilot=True, terminated_at__isnull=True
        ).order_by("slug")
    )


@transaction.atomic
def terminate_pilot(
    *,
    dealership: Dealership,
    reason: str,
    actor=None,
    mode: str = PILOT_TERMINATION_MODE_ARCHIVE,
) -> Dealership:
    """Terminate a pilot dealership per §5.h Option A.

    Belt-and-suspenders guard per §5.h Option A + §0 posture:

    1. :class:`NonPilotTerminationError` raised if
       ``dealership.is_pilot=False``.
    2. ``assert dealership.is_pilot`` fires at the top of the write
       path — defensive second layer per M17/M18 pattern.

    Sets ``is_pilot=False``, populates ``terminated_at`` +
    ``termination_reason``, and (based on ``mode``):

    - ``mode='archive'`` preserves child rows for post-mortem review.
      The pilot leaves the operator surface but its history stays
      queryable in the DB.
    - ``mode='cleanup'`` cascades reverse-order per M18.2 pattern
      (child-before-parent for PROTECT FKs). Customer PII is removed
      from the tenant. Demo-owned Users cleared for username-
      collision safety on future re-create.

    Refuses unknown modes with :class:`ValueError`.

    Returns the mutated :class:`Dealership`.
    """
    if not dealership.is_pilot:
        raise NonPilotTerminationError(
            f"terminate_pilot refuses to touch dealership "
            f"{dealership.slug!r} (is_pilot=False). Only pilot "
            "dealerships can be terminated via this path."
        )
    assert dealership.is_pilot, (
        "terminate_pilot belt-and-suspenders assert failed — "
        f"dealership {dealership.slug!r} reached the write path "
        "with is_pilot=False. Broken invariant."
    )
    if mode not in _VALID_TERMINATION_MODES:
        raise ValueError(
            f"Unknown termination mode={mode!r}. Valid: "
            f"{sorted(_VALID_TERMINATION_MODES)!r}."
        )

    if mode == PILOT_TERMINATION_MODE_CLEANUP:
        _cleanup_pilot_children(dealership)

    dealership.is_pilot = False
    dealership.terminated_at = timezone.now()
    dealership.termination_reason = reason or ""
    dealership.save(
        update_fields=[
            "is_pilot",
            "terminated_at",
            "termination_reason",
            "updated_at",
        ]
    )
    _LOGGER.info(
        "pilot dealership terminated",
        extra={
            "dealership_slug": dealership.slug,
            "mode": mode,
            "reason_len": len(reason or ""),
            "actor": str(actor) if actor is not None else None,
        },
    )
    return dealership


def _cleanup_pilot_children(dealership: Dealership) -> None:
    """Delete every tenanted row keyed to ``dealership`` except the
    Dealership row itself.

    Mirrors :func:`services.demo_store.registry._delete_demo_store_children`
    posture per M18.2 decision 3. Iterates
    :data:`_TENANT_CARRIER_MODEL_NAMES` in **reverse** order so
    child-first deletion satisfies PROTECT FKs. Also deletes demo-
    owned Users (those whose only memberships are at this
    dealership) so a future recreate doesn't collide on the
    ``username`` unique constraint.

    Called inside the caller's atomic block. A ProtectedError from
    a genuine circular-PROTECT cycle fires loud and the termination
    rolls back.
    """
    from django.apps import apps as django_apps
    from django.contrib.auth import get_user_model

    from ...models import UserDealershipRole
    from ..tenancy import _TENANT_CARRIER_MODEL_NAMES

    User = get_user_model()

    # Identify pilot-owned users before the delete removes the
    # memberships that identify them.
    membership_user_ids = set(
        UserDealershipRole.objects.filter(
            dealership=dealership
        ).values_list("user_id", flat=True)
    )
    pilot_owned_user_ids: list[int] = []
    for user_id in membership_user_ids:
        other_memberships = UserDealershipRole.objects.filter(
            user_id=user_id
        ).exclude(dealership=dealership).exists()
        if not other_memberships:
            pilot_owned_user_ids.append(user_id)

    for model_name in reversed(_TENANT_CARRIER_MODEL_NAMES):
        Model = django_apps.get_model("dealer_ai", model_name)
        Model.objects.filter(dealership=dealership).delete()

    if pilot_owned_user_ids:
        User.objects.filter(pk__in=pilot_owned_user_ids).delete()
