"""Milestone 10 · Increment 4 (SESSION_109) — Stipulation lifecycle verbs.

Four verbs. One transactional write path + one state-transition
updater + two pure reads.

- :func:`record_stipulation` — transactional. Creates a
  :class:`Stipulation` for a lender submission with initial
  state ``open``. Refuses cross-tenant
  lender_submission at entry
  (:class:`CrossTenantStipulationError`). Refuses unknown
  ``stip_type`` values.
- :func:`update_stipulation_state` — state transition.
  Auto-populates ``cleared_at`` when moving to ``cleared`` /
  ``waived``; auto-clears ``cleared_at`` when moving back to
  ``open`` (rare — usually an operator error correction).
  M10.4 accepts any-to-any transition (operator behavior
  captured as-recorded); transition rules can be locked at
  M10.7 compliance layer if evidence surfaces.
- :func:`get_stipulation` — pure read verb, tenant-scoped by pk.
  Returns ``None`` for unknown / cross-tenant pk (never raises,
  never leaks).
- :func:`list_stipulations_for_submission` — pure read verb. FK
  filter, ordering inherits from Meta.

Layer discipline mirrors the M10.1-M10.3 sibling modules.

See ``docs/roadmap/MILESTONE_10_PLANNING.md`` §1.4 + §7 M10.4
for the contract.
"""

from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ...models import (
    STIPULATION_STATE_CHOICES,
    STIPULATION_STATE_CLEARED,
    STIPULATION_STATE_OPEN,
    STIPULATION_STATE_WAIVED,
    STIPULATION_TYPE_CHOICES,
    Dealership,
    LenderSubmission,
    Stipulation,
)


User = get_user_model()

_VALID_TYPES = frozenset(key for key, _ in STIPULATION_TYPE_CHOICES)
_VALID_STATES = frozenset(key for key, _ in STIPULATION_STATE_CHOICES)
_CLEARED_STATES = frozenset(
    (STIPULATION_STATE_CLEARED, STIPULATION_STATE_WAIVED)
)


class CrossTenantStipulationError(ValueError):
    """Raised when a Stipulation verb is called with a
    ``dealership`` that does not match the parent lender
    submission's tenant.

    Subclasses :class:`ValueError` so callers catching
    ``ValueError`` keep working. Named specifically so log lines
    + API responses can identify the failure mode without
    string-matching.

    Service-layer defense against cross-tenant writes — the
    model layer's :meth:`Stipulation.clean` is the second line.
    Belt + suspenders; do not remove either.
    """


def _assert_same_tenant_lender_submission(
    submission: LenderSubmission, dealership: Dealership
) -> None:
    if submission.dealership_id != dealership.pk:
        raise CrossTenantStipulationError(
            f"LenderSubmission #{submission.pk} belongs to "
            f"dealership_id={submission.dealership_id}, but the "
            f"caller passed dealership_id={dealership.pk}."
        )


@transaction.atomic
def record_stipulation(
    *,
    dealership: Dealership,
    lender_submission: LenderSubmission,
    stip_type: str,
    notes: str = "",
) -> Stipulation:
    """Create a :class:`Stipulation` for ``lender_submission``.

    Refuses cross-tenant parent at entry
    (:class:`CrossTenantStipulationError`). Refuses unknown
    ``stip_type`` values (:class:`ValueError`).

    Initial state is always ``open`` — clearing / waiving is a
    separate transition captured by
    :func:`update_stipulation_state`. This preserves audit-trail
    rigor (the moment a stip was cleared is a distinct event
    from the moment it was recorded).

    ``documented_by`` is not accepted at record time — a fresh
    stip hasn't been documented yet; the FK is populated when
    the state transitions to ``cleared`` / ``waived``.

    Transactional — the tenant check + insert run inside a
    single ``transaction.atomic`` block.
    """
    _assert_same_tenant_lender_submission(lender_submission, dealership)

    if stip_type not in _VALID_TYPES:
        raise ValueError(
            f"Unknown stip_type={stip_type!r}. "
            f"Valid values: {sorted(_VALID_TYPES)!r}."
        )

    return Stipulation.objects.create(
        dealership=dealership,
        lender_submission=lender_submission,
        stip_type=stip_type,
        state=STIPULATION_STATE_OPEN,
        notes=notes,
    )


def update_stipulation_state(
    stipulation: Stipulation,
    *,
    new_state: str,
    documented_by=None,
    notes: Optional[str] = None,
) -> Stipulation:
    """Transition a :class:`Stipulation` to ``new_state``.

    Refuses unknown ``new_state`` values (:class:`ValueError`).
    No transition constraints at M10.4 — any-to-any allowed
    (operator behavior captured as-recorded). Transition rules
    may be locked at M10.7 compliance layer if evidence
    surfaces need.

    Side effects on ``cleared_at``:

    - Transitioning to ``cleared`` or ``waived`` populates
      ``cleared_at`` with :func:`django.utils.timezone.now`
      (if not already set — re-transitions don't overwrite).
    - Transitioning back to ``open`` resets ``cleared_at`` to
      NULL (operator error correction path).

    ``documented_by`` — when provided, populates the FK. Only
    meaningful on transitions to ``cleared`` / ``waived``; on
    a back-transition to ``open`` the caller can pass ``None``
    to clear the FK (or omit to preserve the existing value).
    ``notes`` — when provided, replaces the existing notes;
    when omitted, preserved.

    Returns the same :class:`Stipulation` instance with the
    updated fields persisted via a targeted
    ``.save(update_fields=...)``.
    """
    if new_state not in _VALID_STATES:
        raise ValueError(
            f"Unknown state={new_state!r}. "
            f"Valid values: {sorted(_VALID_STATES)!r}."
        )

    update_fields = ["state", "updated_at"]
    stipulation.state = new_state

    if new_state in _CLEARED_STATES:
        # Only populate ``cleared_at`` on first transition —
        # re-transitions preserve the original clear/waive moment.
        if stipulation.cleared_at is None:
            stipulation.cleared_at = timezone.now()
            update_fields.append("cleared_at")
    else:
        # Transitioning back to ``open`` (or any non-cleared
        # state) clears the timestamp — the stip is once again
        # outstanding, so the previous clear event is no longer
        # the current state.
        if stipulation.cleared_at is not None:
            stipulation.cleared_at = None
            update_fields.append("cleared_at")

    if documented_by is not None:
        stipulation.documented_by = documented_by
        update_fields.append("documented_by")
    if notes is not None:
        stipulation.notes = notes
        update_fields.append("notes")

    stipulation.save(update_fields=update_fields)
    return stipulation


def get_stipulation(
    pk: int, *, dealership: Dealership
) -> Optional[Stipulation]:
    """Return the tenant-scoped :class:`Stipulation` for ``pk``,
    or ``None`` if unknown / cross-tenant.

    Never raises. Never leaks whether the row exists in another
    tenant.
    """
    return (
        Stipulation.objects.filter(dealership=dealership, pk=pk)
        .select_related("lender_submission", "documented_by")
        .first()
    )


def list_stipulations_for_submission(
    lender_submission: LenderSubmission,
) -> "QuerySet[Stipulation]":
    """Return the ordered queryset of stipulations for a given
    :class:`LenderSubmission`.

    Pure verb. Never mutates. Tenant scoping is implicit via the
    FK — the submission's own tenancy is authoritative. Ordering
    inherits from the model's ``Meta.ordering``
    (``(-created_at,)``).
    """
    return Stipulation.objects.filter(lender_submission=lender_submission)
