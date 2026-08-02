"""Milestone 10 · Increment 3 (SESSION_108) — Lender catalog + submission verbs.

Six verbs. Two for the catalog surface + four for the submission
workflow. All transactional or explicitly pure.

Catalog surface:

- :func:`record_lender_program` — create a per-dealership lender
  program row. Refuses duplicate name per tenant (surfaces the
  unique constraint as a typed error). Refuses cross-tenant
  writes at entry.
- :func:`list_active_lender_programs` — pure read verb. Returns
  the tenant-scoped ordered queryset of active programs
  (``is_active=True``).

Submission workflow:

- :func:`record_lender_submission` — transactional. Creates a
  submission for a deal-structure + program pair. Refuses
  cross-tenant deal_structure / lender_program at entry
  (:class:`CrossTenantLenderSubmissionError`).
- :func:`update_lender_submission_status` — validated status
  transition. M10.3 accepts any-to-any transition
  (operator behavior captured as-recorded); transition rules
  can be locked at M10.4+ if evidence surfaces need. Refuses
  unknown status values.
- :func:`get_lender_submission` — pure read verb, tenant-scoped
  by pk. Returns ``None`` for unknown / cross-tenant pk (never
  raises, never leaks).
- :func:`list_submissions_for_deal_structure` — pure read verb.
  Returns the ordered queryset of submissions for a given deal
  structure (tenant-scoped implicitly via the FK — the
  deal_structure's own tenancy is authoritative).

Layer discipline mirrors ``services/f_and_i/credit_application.py``
and ``services/f_and_i/deal_structure.py``: identity +
authorization live in the view layer; data-scoping + business
semantics live here. Every write function accepts an explicit
``dealership`` kwarg.

See ``docs/roadmap/MILESTONE_10_PLANNING.md`` §1.3 + §7 M10.3 for
the contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from ...models import (
    LENDER_SUBMISSION_STATUS_CHOICES,
    LENDER_SUBMISSION_STATUS_PENDING,
    DealStructure,
    Dealership,
    LenderProgram,
    LenderSubmission,
)


_VALID_STATUSES = frozenset(key for key, _ in LENDER_SUBMISSION_STATUS_CHOICES)


class CrossTenantLenderSubmissionError(ValueError):
    """Raised when a LenderSubmission verb is called with a
    ``dealership`` that does not match the parent deal_structure's
    or lender_program's tenant.

    Subclasses :class:`ValueError` so callers catching ``ValueError``
    keep working. Named specifically so log lines + API responses can
    identify the failure mode without string-matching.

    Service-layer defense against cross-tenant writes — the model
    layer's :meth:`LenderSubmission.clean` is the second line. Belt
    + suspenders; do not remove either.
    """


class DuplicateLenderProgramError(ValueError):
    """Raised when :func:`record_lender_program` would violate the
    unique constraint on ``(dealership, name)``.

    Typed so the endpoint layer can map to HTTP 409 Conflict
    without string-matching a DB error message. Matches the
    :class:`SaleAlreadyExistsError` pattern from M9.1.
    """


# ---- Catalog surface --------------------------------------------------------


def _assert_same_tenant_deal_structure(
    deal: DealStructure, dealership: Dealership
) -> None:
    if deal.dealership_id != dealership.pk:
        raise CrossTenantLenderSubmissionError(
            f"DealStructure #{deal.pk} belongs to "
            f"dealership_id={deal.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


def _assert_same_tenant_lender_program(
    program: LenderProgram, dealership: Dealership
) -> None:
    if program.dealership_id != dealership.pk:
        raise CrossTenantLenderSubmissionError(
            f"LenderProgram #{program.pk} belongs to "
            f"dealership_id={program.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


@transaction.atomic
def record_lender_program(
    *,
    dealership: Dealership,
    name: str,
    contact: str = "",
    terms_summary: str = "",
    is_active: bool = True,
) -> LenderProgram:
    """Create a :class:`LenderProgram` for ``dealership``.

    Refuses duplicate ``(dealership, name)`` at entry
    (:class:`DuplicateLenderProgramError`). Transactional so the
    uniqueness check + insert run atomically — otherwise two
    concurrent requests with the same name could both pass the
    pre-check and race to the same IntegrityError, one of which
    would surface as a raw exception without the typed wrapper.

    ``is_active`` defaults to True — new programs are added when
    an operator establishes a lender relationship, and the
    default assumption is that the relationship is live at
    creation time. Deactivation via
    :func:`services.f_and_i.deal_structure.recompute_ratios`-style
    edit-then-save patterns (or a future explicit
    ``deactivate_lender_program`` verb) is deferred.
    """
    try:
        return LenderProgram.objects.create(
            dealership=dealership,
            name=name,
            contact=contact,
            terms_summary=terms_summary,
            is_active=is_active,
        )
    except IntegrityError as exc:
        # Map the DB-layer unique-constraint violation to a typed
        # domain error so the endpoint layer can respond 409 without
        # string-matching the DB error text.
        raise DuplicateLenderProgramError(
            f"LenderProgram with name={name!r} already exists for "
            f"dealership_id={dealership.pk}."
        ) from exc


def list_active_lender_programs(
    dealership: Dealership,
) -> "QuerySet[LenderProgram]":
    """Return the ordered queryset of active
    :class:`LenderProgram` rows for ``dealership``.

    Pure verb. Never mutates. Filter is ``is_active=True`` —
    inactive programs are historical records for the audit
    trail. Ordering inherits from the model's ``Meta.ordering``
    (``name`` ascending).
    """
    return LenderProgram.objects.filter(
        dealership=dealership, is_active=True
    )


# ---- Submission workflow ----------------------------------------------------


@transaction.atomic
def record_lender_submission(
    *,
    dealership: Dealership,
    deal_structure: DealStructure,
    lender_program: LenderProgram,
    submitted_at: Optional[datetime] = None,
    status: str = LENDER_SUBMISSION_STATUS_PENDING,
    counter_terms: Optional[dict] = None,
    approval_terms: Optional[dict] = None,
    notes: str = "",
) -> LenderSubmission:
    """Create a :class:`LenderSubmission` for
    ``deal_structure`` + ``lender_program``.

    Refuses cross-tenant parents at entry
    (:class:`CrossTenantLenderSubmissionError`). Refuses
    unknown ``status`` values (:class:`ValueError`).

    Transactional — tenant checks + insert happen inside a single
    ``transaction.atomic`` block so concurrent writes observe a
    serialized view of tenant state.

    ``submitted_at`` defaults to :func:`django.utils.timezone.now`
    when omitted. Both ``counter_terms`` and ``approval_terms``
    default to empty dict — the row shape is stable regardless
    of status value (a ``pending`` submission has empty terms;
    an ``approved`` submission may populate ``approval_terms``;
    a ``counter`` submission may populate ``counter_terms``).
    """
    _assert_same_tenant_deal_structure(deal_structure, dealership)
    _assert_same_tenant_lender_program(lender_program, dealership)

    if status not in _VALID_STATUSES:
        raise ValueError(
            f"Unknown status={status!r}. "
            f"Valid values: {sorted(_VALID_STATUSES)!r}."
        )

    return LenderSubmission.objects.create(
        dealership=dealership,
        deal_structure=deal_structure,
        lender_program=lender_program,
        submitted_at=submitted_at if submitted_at is not None else timezone.now(),
        status=status,
        counter_terms=counter_terms if counter_terms is not None else {},
        approval_terms=approval_terms if approval_terms is not None else {},
        notes=notes,
    )


def update_lender_submission_status(
    submission: LenderSubmission,
    *,
    new_status: str,
    counter_terms: Optional[dict] = None,
    approval_terms: Optional[dict] = None,
    notes: Optional[str] = None,
) -> LenderSubmission:
    """Update the status (and optionally terms / notes) of a
    :class:`LenderSubmission`.

    Refuses unknown ``new_status`` values (:class:`ValueError`).
    No transition constraints at M10.3 — accepts any-to-any
    (operator behavior captured as-recorded); transition rules
    can be locked at M10.4+ if evidence surfaces need.

    ``counter_terms`` / ``approval_terms`` / ``notes`` — when
    omitted, the existing values are preserved (the caller
    passes only the fields they want to change).

    Returns the same :class:`LenderSubmission` instance with the
    updated fields persisted via a targeted
    ``.save(update_fields=...)`` so no other columns are touched.
    """
    if new_status not in _VALID_STATUSES:
        raise ValueError(
            f"Unknown status={new_status!r}. "
            f"Valid values: {sorted(_VALID_STATUSES)!r}."
        )

    update_fields = ["status", "updated_at"]
    submission.status = new_status
    if counter_terms is not None:
        submission.counter_terms = counter_terms
        update_fields.append("counter_terms")
    if approval_terms is not None:
        submission.approval_terms = approval_terms
        update_fields.append("approval_terms")
    if notes is not None:
        submission.notes = notes
        update_fields.append("notes")

    submission.save(update_fields=update_fields)
    return submission


def get_lender_submission(
    pk: int, *, dealership: Dealership
) -> Optional[LenderSubmission]:
    """Return the tenant-scoped :class:`LenderSubmission` for
    ``pk``, or ``None`` if unknown / cross-tenant.

    Never raises. Never leaks whether the row exists in another
    tenant. Callers translate ``None`` to HTTP 404 per the
    fail-closed pattern from M2.6 / M3.6 / M4.6 / M9.1 / M10.1
    / M10.2.
    """
    return (
        LenderSubmission.objects.filter(dealership=dealership, pk=pk)
        .select_related("deal_structure", "lender_program")
        .first()
    )


def list_submissions_for_deal_structure(
    deal_structure: DealStructure,
) -> "QuerySet[LenderSubmission]":
    """Return the ordered queryset of submissions for a given
    :class:`DealStructure`.

    Pure verb. Never mutates. Tenant scoping is implicit via the
    FK — the deal_structure's own tenancy is authoritative, and
    a caller with a cross-tenant deal_structure instance in hand
    is misusing the API (verify tenancy at the endpoint layer via
    the deal_structure lookup, not here). Ordering inherits from
    the model's ``Meta.ordering`` (``(-submitted_at,
    -created_at)``).
    """
    return LenderSubmission.objects.filter(deal_structure=deal_structure)
