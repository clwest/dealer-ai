"""Milestone 19 · Increment 1 (SESSION_154) — pilot onboarding checklist verbs.

Per MILESTONE_19_PLANNING.md §5.f Option A (user-confirmed at
SESSION_153 open).

Two verbs (checklist creation is handled internally by
:func:`services.pilot_onboarding.create_pilot_dealership`; not
exposed as a standalone verb because a pilot without a checklist
is not a valid state):

- :func:`advance_step` — atomic transition adding a step row.
- :func:`is_pilot_ready` — pure predicate.

**Readiness precondition** per §5.f Option A:
``readiness_confirmed`` cannot be advanced until every prior step
in :data:`PILOT_ONBOARDING_STEP_ORDER` has a corresponding
:class:`PilotOnboardingStep` row with ``completed_at`` populated.
The verb raises :class:`PilotReadinessNotConfirmedError` on
violation.
"""

from __future__ import annotations

from typing import Optional

from django.db import IntegrityError, transaction
from django.utils import timezone

from ...models import (
    PILOT_ONBOARDING_STEP_CHOICES,
    PILOT_ONBOARDING_STEP_ORDER,
    PILOT_ONBOARDING_STEP_READINESS_CONFIRMED,
    Dealership,
    PilotOnboardingChecklist,
    PilotOnboardingStep,
)
from .errors import PilotReadinessNotConfirmedError


class UnknownChecklistStepError(ValueError):
    """Raised when ``step_slug`` is not in the fixed vocab.

    Mapped to HTTP 400 at the endpoint layer.
    """


class ChecklistStepAlreadyCompletedError(ValueError):
    """Raised when advancing a step that already has a row.

    Per M18 §6 lesson 4 immutability posture — a completed step is
    immutable; re-completion is refused. Corrections happen via a
    new PilotProspect / new pilot / notes edit outside this verb.
    Mapped to HTTP 409 at the endpoint layer.
    """


_VALID_STEP_SLUGS = {key for key, _ in PILOT_ONBOARDING_STEP_CHOICES}


@transaction.atomic
def advance_step(
    *,
    checklist: PilotOnboardingChecklist,
    step_slug: str,
    completed_by=None,
    notes: str = "",
) -> PilotOnboardingStep:
    """Add a :class:`PilotOnboardingStep` row advancing ``step_slug``.

    Atomic — step-row create + optional
    :class:`PilotOnboardingChecklist.is_ready` flip commit together.

    Refuses:

    - Unknown ``step_slug`` —
      :class:`UnknownChecklistStepError` (400).
    - Step already completed on this checklist —
      :class:`ChecklistStepAlreadyCompletedError` (409). Catches
      the DB-level unique constraint IntegrityError + re-raises as
      the domain error per M17 §6 lesson 4 pattern.
    - Advancing ``readiness_confirmed`` before every prior step is
      completed —
      :class:`PilotReadinessNotConfirmedError` (409).

    When ``step_slug='readiness_confirmed'`` succeeds, the parent
    checklist's ``is_ready`` flag is flipped to True in the same
    transaction. The M19.4 admin surface reads this flag to gate the
    pilot dealer's operator surface access.
    """
    if step_slug not in _VALID_STEP_SLUGS:
        raise UnknownChecklistStepError(
            f"Unknown step_slug={step_slug!r}. Valid: "
            f"{sorted(_VALID_STEP_SLUGS)!r}."
        )

    # Readiness precondition — ``readiness_confirmed`` requires every
    # prior step to already exist with completed_at populated.
    if step_slug == PILOT_ONBOARDING_STEP_READINESS_CONFIRMED:
        prior_slugs = tuple(
            s for s in PILOT_ONBOARDING_STEP_ORDER if s != step_slug
        )
        completed_prior = set(
            PilotOnboardingStep.objects.filter(
                checklist=checklist,
                step_slug__in=prior_slugs,
                completed_at__isnull=False,
            ).values_list("step_slug", flat=True)
        )
        missing = set(prior_slugs) - completed_prior
        if missing:
            raise PilotReadinessNotConfirmedError(
                "Cannot advance 'readiness_confirmed' — the following "
                f"prior steps are not yet complete: {sorted(missing)!r}."
            )

    try:
        step = PilotOnboardingStep.objects.create(
            dealership=checklist.dealership,
            checklist=checklist,
            step_slug=step_slug,
            completed_at=timezone.now(),
            completed_by=(
                completed_by if completed_by is not None
                and getattr(completed_by, "is_authenticated", False)
                else None
            ),
            notes=notes or "",
        )
    except IntegrityError as exc:
        raise ChecklistStepAlreadyCompletedError(
            f"Step {step_slug!r} is already completed on "
            f"checklist #{checklist.pk}. Steps are immutable per M18 §6 "
            "lesson 4 posture; a correction requires a new record."
        ) from exc

    if step_slug == PILOT_ONBOARDING_STEP_READINESS_CONFIRMED:
        checklist.is_ready = True
        checklist.save(update_fields=["is_ready", "updated_at"])

    return step


def is_pilot_ready(dealership: Dealership) -> bool:
    """Return True iff the pilot's checklist has ``is_ready=True``.

    Pure. Read-only. Returns False for non-pilot dealerships +
    dealerships that don't have a checklist row yet. The M19.4
    admin surface uses this to gate the pilot dealer's operator
    surface access.
    """
    if not dealership.is_pilot:
        return False
    checklist: Optional[PilotOnboardingChecklist] = (
        PilotOnboardingChecklist.objects.filter(
            dealership=dealership
        ).first()
    )
    if checklist is None:
        return False
    return bool(checklist.is_ready)
