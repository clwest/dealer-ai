"""Milestone 10 · Increment 1 (SESSION_106) — CreditApplication verbs.

Four verbs (three shipped at M10.1; one added at M32.1). All
deterministic. Cross-tenant writes refuse at entry.

- :func:`record_credit_application` — write path. Creates a
  :class:`CreditApplication` for a lead and/or sale, computes
  ``retention_expires_at`` from ``captured_at`` +
  :data:`dealer_ai.models.CREDIT_APP_RETENTION_YEARS`, and
  denormalizes it on the row. Refuses cross-tenant parents.
  **M32.1 extension:** optional ``deal_writeup`` kwarg — sets
  the provenance backpointer per D9-revised²; raises
  :class:`DealWriteupAlreadyLinkedError` if the writeup already
  has a paired CA (service-layer belt for the DB unique constraint).
- :func:`get_credit_application` — pure read verb by pk. Tenant-
  scoped; returns ``None`` on unknown or cross-tenant pk (never
  raises, never leaks existence).
- :func:`compute_retention_expires_at` — pure verb. Returns
  ``captured_at + relativedelta(years=CREDIT_APP_RETENTION_YEARS)``.
  Callable outside the write path so the retention-clock
  invariant is testable in isolation and the value can be
  re-derived on any row that predates the field ever being
  written.
- :func:`list_credit_applications` (**M32.1** + **M33.1
  annotations**) — tenant-scoped list read for the F&I intake
  queue. Optional filters: ``intake=True`` filters to CAs
  without a Contract (pre-contract incoming queue); ``lead=``
  filters by CustomerLead; ``since=`` filters by
  ``captured_at >= since``. Fail-explicit filter validation per
  M32.1 D3 — callers pass typed args, endpoint layer handles
  query-string parsing + 400 mapping. **M33.1 adds two
  tenant-scoped subquery annotations on every returned row**:
  ``has_deal_structure`` (Boolean; drives the M33 intake-row
  chip) + ``latest_deal_structure_id`` (nullable int;
  deterministic ordering ``("-created_at", "-pk")`` for the
  "Open structure" action). Both per
  ``MILESTONE_33_PLANNING.md`` §5.b D1 + D3.

Retention discipline (locked at the model layer per
``MILESTONE_10_PLANNING.md`` §5.e). The service *computes*
``retention_expires_at`` at write time and denormalizes it on the
row; the model's :meth:`CreditApplication.delete` override
*enforces* the invariant by refusing unexpired deletes. Two
layers so a service-only guard can't be bypassed.

Attach-shape discipline (§5.a Option C — user-confirmed at
SESSION_106 open). At least one of ``lead`` / ``sale`` must be
set. The service raises :class:`ValueError` when both are ``None``
before the model layer's ``clean()`` would surface the same
invariant, so callers get a clean domain-typed error instead of a
Django ``ValidationError``.

See ``docs/roadmap/MILESTONE_10_PLANNING.md`` §5.a + §5.e + §7
M10.1 for the contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.db.models import Exists, OuterRef, Subquery
from django.utils import timezone

from ...models import (
    CREDIT_APP_FORMAT_CHOICES,
    CREDIT_APP_RETENTION_YEARS,
    CREDIT_APP_STATUS_CHOICES,
    CREDIT_APP_STATUS_RECEIVED,
    CreditApplication,
    CustomerLead,
    Dealership,
    DealStructure,
    DealWriteup,
    LenderSubmission,
    Sale,
)


_VALID_FORMATS = frozenset(key for key, _ in CREDIT_APP_FORMAT_CHOICES)
_VALID_STATUSES = frozenset(key for key, _ in CREDIT_APP_STATUS_CHOICES)


class CrossTenantCreditApplicationError(ValueError):
    """Raised when a CreditApplication verb is called with a
    ``dealership`` that does not match the parent lead's or sale's
    tenant.

    Subclasses :class:`ValueError` so callers catching ``ValueError``
    keep working. Named specifically so log lines + API responses can
    identify the failure mode without string-matching.

    Service-layer defense against cross-tenant writes — the model
    layer's :meth:`CreditApplication.clean` is the second line. Belt
    + suspenders; do not remove either.
    """


class DealWriteupAlreadyLinkedError(Exception):
    """Milestone 32 · Increment 1 — raised when
    :func:`record_credit_application` is called with a
    ``deal_writeup`` that already has a paired CreditApplication.

    Per ``MILESTONE_32_PLANNING.md`` §5.b D9-revised²: service-layer
    belt for the database-layer OneToOneField unique constraint on
    :attr:`CreditApplication.deal_writeup`. Kicks in before the DB
    write so callers see a clean domain-typed error rather than a
    Django ``IntegrityError``.

    Composed with the M11.3 shipped
    :class:`services.deal_writeups.WriteupAlreadyHandedOffError`
    which catches the writeup-side second-hand-off path — this class
    catches any alternate caller path
    (:func:`record_credit_application` invoked directly with a
    ``deal_writeup=`` kwarg referencing an already-paired writeup).

    Endpoint layer maps to 409 CONFLICT — matches the M11.3
    ``WriteupAlreadyHandedOffError`` HTTP shape.
    """


def compute_retention_expires_at(captured_at: datetime) -> datetime:
    """Return ``captured_at + relativedelta(years=CREDIT_APP_RETENTION_YEARS)``.

    Pure verb. Never mutates. Same ``captured_at`` → same
    :class:`datetime`.

    Uses :func:`dateutil.relativedelta.relativedelta` rather than
    :class:`datetime.timedelta` so the arithmetic respects leap
    years (a 7-year window from a Feb 29 capture date should land
    on the corresponding Feb 28 / 29 of the target year, not
    ``captured_at + 365*7 days``). Same trade-off Django's own
    date-arithmetic helpers make.
    """
    return captured_at + relativedelta(years=CREDIT_APP_RETENTION_YEARS)


def get_credit_application(
    pk: int, *, dealership: Dealership
) -> Optional[CreditApplication]:
    """Return the tenant-scoped :class:`CreditApplication` for ``pk``,
    or ``None`` if unknown / cross-tenant.

    Never raises. Never leaks whether the row exists in another
    tenant. Callers translate ``None`` to HTTP 404 per the
    fail-closed pattern from M2.6 / M3.6 / M4.6.
    """
    return (
        CreditApplication.objects.filter(dealership=dealership, pk=pk)
        .select_related("lead", "sale")
        .first()
    )


def _assert_same_tenant_lead(lead: CustomerLead, dealership: Dealership) -> None:
    if lead.dealership_id != dealership.pk:
        raise CrossTenantCreditApplicationError(
            f"CustomerLead #{lead.pk} belongs to "
            f"dealership_id={lead.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


def _assert_same_tenant_sale(sale: Sale, dealership: Dealership) -> None:
    if sale.dealership_id != dealership.pk:
        raise CrossTenantCreditApplicationError(
            f"Sale #{sale.pk} belongs to "
            f"dealership_id={sale.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


@transaction.atomic
def record_credit_application(
    *,
    dealership: Dealership,
    applicant_full_name: str,
    source_format: str,
    lead: Optional[CustomerLead] = None,
    sale: Optional[Sale] = None,
    applicant_ssn_last4: str = "",
    status: str = CREDIT_APP_STATUS_RECEIVED,
    captured_at: Optional[datetime] = None,
    notes: str = "",
    deal_writeup: Optional[DealWriteup] = None,
) -> CreditApplication:
    """Create a :class:`CreditApplication` and populate
    ``retention_expires_at`` at write time.

    Refuses cross-tenant parents at entry
    (:class:`CrossTenantCreditApplicationError`). Requires at least
    one of ``lead`` / ``sale`` to be set (:class:`ValueError`);
    §5.a Option C means the app can attach to a lead early and
    gain a sale reference at close, but never to nothing. Refuses
    unknown ``source_format`` or ``status`` values
    (:class:`ValueError`).

    Transactional — the tenant checks + insert happen inside a
    single ``transaction.atomic`` block so concurrent writes
    observe a serialized view of tenant state.

    ``captured_at`` defaults to :func:`django.utils.timezone.now`
    when omitted. The retention clock starts from ``captured_at``,
    not from row insert time, so a paper app captured hours or
    days before data-entry retains the true intake timestamp.

    **M32.1 extension — ``deal_writeup`` provenance backpointer**
    per ``MILESTONE_32_PLANNING.md`` §5.b D9-revised². When
    provided, sets the OneToOneField backpointer on the created
    CA. Raises :class:`DealWriteupAlreadyLinkedError` if the
    writeup already has a paired CA (service-layer belt for the
    DB unique constraint). Direct-create callers (M10.1 path)
    omit the kwarg — field stays NULL. When ``deal_writeup`` is
    provided, its ``dealership`` must match ``dealership`` — an
    additional cross-tenant guard mirrors the ``lead`` / ``sale``
    guards.

    Returns the persisted :class:`CreditApplication` with
    ``retention_expires_at`` populated from
    :func:`compute_retention_expires_at`.
    """
    if lead is None and sale is None:
        raise ValueError(
            "CreditApplication must attach to at least one of lead or "
            "sale (see MILESTONE_10_PLANNING.md §5.a Option C)."
        )
    if lead is not None:
        _assert_same_tenant_lead(lead, dealership)
    if sale is not None:
        _assert_same_tenant_sale(sale, dealership)
    if deal_writeup is not None:
        _assert_same_tenant_deal_writeup(deal_writeup, dealership)
        _assert_writeup_not_already_linked(deal_writeup)

    if source_format not in _VALID_FORMATS:
        raise ValueError(
            f"Unknown source_format={source_format!r}. "
            f"Valid values: {sorted(_VALID_FORMATS)!r}."
        )
    if status not in _VALID_STATUSES:
        raise ValueError(
            f"Unknown status={status!r}. "
            f"Valid values: {sorted(_VALID_STATUSES)!r}."
        )

    captured = captured_at if captured_at is not None else timezone.now()
    retention_expires = compute_retention_expires_at(captured)

    return CreditApplication.objects.create(
        dealership=dealership,
        lead=lead,
        sale=sale,
        applicant_full_name=applicant_full_name,
        applicant_ssn_last4=applicant_ssn_last4,
        source_format=source_format,
        status=status,
        captured_at=captured,
        retention_expires_at=retention_expires,
        notes=notes,
        deal_writeup=deal_writeup,
    )


def _assert_same_tenant_deal_writeup(
    deal_writeup: DealWriteup, dealership: Dealership
) -> None:
    if deal_writeup.dealership_id != dealership.pk:
        raise CrossTenantCreditApplicationError(
            f"DealWriteup #{deal_writeup.pk} belongs to "
            f"dealership_id={deal_writeup.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


def _assert_writeup_not_already_linked(deal_writeup: DealWriteup) -> None:
    """Belt for the DB OneToOneField unique constraint.

    Raises :class:`DealWriteupAlreadyLinkedError` (clean domain
    error) before the DB write when the writeup already has a
    paired CA. Prevents the caller from seeing a Django
    ``IntegrityError`` for a semantically-meaningful lifecycle
    violation.

    Uses ``CreditApplication.objects.filter(...).exists()`` rather
    than accessing ``deal_writeup.credit_application`` (which
    raises ``CreditApplication.DoesNotExist`` on the unpaired
    case, making the None-path noisy).
    """
    if CreditApplication.objects.filter(deal_writeup=deal_writeup).exists():
        raise DealWriteupAlreadyLinkedError(
            f"DealWriteup #{deal_writeup.pk} already has a paired "
            "CreditApplication. Refusing to create a duplicate "
            "(see MILESTONE_32_PLANNING.md §5.b D9-revised²)."
        )


def list_credit_applications(
    *,
    dealership: Dealership,
    intake: bool = False,
    lead: Optional[CustomerLead] = None,
    since: Optional[datetime] = None,
) -> list[CreditApplication]:
    """Milestone 32 · Increment 1 — tenant-scoped CA list for the
    F&I intake queue.

    Returns credit applications for ``dealership``, ordered newest-
    first by ``captured_at`` then ``-created_at`` (matches
    :attr:`CreditApplication.Meta.ordering`).

    Optional filters (composable):

    - ``intake=True`` — filter to CAs where no downstream Contract
      exists (pre-contract incoming queue). Uses the model chain
      :class:`CreditApplication` → :class:`DealStructure`
      (``credit_application`` FK) → :class:`Contract`
      (``deal_structure`` FK). A CA is "intake" when none of its
      deal_structures has any contracts (including CAs with no
      deal_structures at all — F&I has not yet begun structuring).
      Default ``False`` returns unfiltered.
    - ``lead=<CustomerLead>`` — filter by lead FK. Must be same-
      tenant; cross-tenant lead raises
      :class:`CrossTenantCreditApplicationError`.
    - ``since=<datetime>`` — filter to ``captured_at >= since``.

    Query strategy: single ``.filter(dealership=dealership)`` base
    + composable filter application. Uses ``.exclude(...)`` for the
    intake filter so CAs with no deal_structures survive (they are
    the most-intake case — the M11.3 hand-off path creates the CA
    before any deal_structure exists). ``.distinct()`` guards
    against join multiplicity when a CA has multiple deal_structures.
    No pagination (M10.7 / M11 precedent — 100-row soft cap
    deferred per §5.h). Callers cap via slicing if needed.

    **M33.1 extension.** Every returned row carries two subquery
    annotations that let the endpoint projection derive the
    F&I structuring status without an N+1 fetch:

    - ``has_deal_structure`` — ``True`` when any
      :class:`DealStructure` exists for this CA in the caller's
      tenant; ``False`` otherwise. Drives the M33 intake-row chip
      ("Incoming" when False; "In progress" when True) per
      ``MILESTONE_33_PLANNING.md`` §5.b D1.
    - ``latest_deal_structure_id`` — pk of the most-recent
      :class:`DealStructure` for this CA, or ``None`` when
      Incoming. Deterministic ordering
      ``("-created_at", "-pk")`` disambiguates the rare case
      where two structures share ``created_at`` at microsecond
      granularity (seed / migration / bulk-import scenarios).
      Per ``MILESTONE_33_PLANNING.md`` §5.b D3.

    Both subqueries are explicitly tenant-scoped
    (``dealership=dealership`` in the filter) — belt over the
    :meth:`DealStructure.clean` and service-layer
    :class:`CrossTenantDealStructureError` suspenders that already
    prevent legitimate cross-tenant rows.

    **M35.1 extension.** A third subquery annotation extends the
    projection to the lender-submission workflow state:

    - ``latest_lender_submission_status`` — status string of the
      most-recent :class:`LenderSubmission` on the
      ``latest_deal_structure_id`` structure, or ``None`` when
      either the latest DealStructure has no submissions OR the
      CA has no DealStructure at all. One of ``"pending"`` /
      ``"approved"`` / ``"counter"`` / ``"declined"``. Correlates
      on the ``latest_deal_structure_id`` annotation itself (D1
      output feeds D2 input); Django emits ANSI-standard
      correlated subqueries that compile + execute on both
      SQLite and Postgres (verified live at M35.0 §4.8 + M35.1
      §0.a). Deterministic ordering
      ``("-submitted_at", "-created_at", "-pk")`` — business
      time first, DB write time second, pk as ultimate tiebreak.
      Per ``MILESTONE_35_PLANNING.md`` §5.b D2.
    - ``latest_lender_submission_id`` — pk of the same latest-
      submission subquery, or ``None`` under the same conditions
      as ``latest_lender_submission_status``. Added at M35.2
      §0.a as a scope amendment: the response form UI requires
      the submission pk for the PATCH URL, and page refreshes
      erase any locally cached
      :class:`LenderSubmissionProjection`. Preserves the M35.0
      §5.h non-goal of NOT adding a GET single-record endpoint —
      derived id via annotation lets the frontend PATCH without
      a preceding GET. Per M35.2 §0.a amendment.

    Combined with D1's ``latest_deal_structure_id``, the M35
    projection lets the frontend derive six workflow states
    ("Incoming" / "In progress" / "Submitted — awaiting response"
    / "Approved" / "Counter-offer received" / "Declined") purely
    from FK events on the latest DealStructure's latest
    LenderSubmission. **No stored ``workflow_state`` column; no
    state machine; no schema change.**

    The M35.1 subquery is tenant-scoped identically to the M33.1
    subquery — belt (filter) over model :meth:`LenderSubmission.clean`
    and service-layer :class:`CrossTenantLenderSubmissionError`
    suspenders.

    Pure read — never raises except on cross-tenant lead.
    """
    if lead is not None:
        _assert_same_tenant_lead(lead, dealership)

    tenant_deal_structures = DealStructure.objects.filter(
        dealership=dealership,
        credit_application=OuterRef("pk"),
    )
    tenant_latest_submissions = LenderSubmission.objects.filter(
        dealership=dealership,
        deal_structure_id=OuterRef("latest_deal_structure_id"),
    ).order_by("-submitted_at", "-created_at", "-pk")
    qs = (
        CreditApplication.objects.filter(dealership=dealership)
        .select_related("lead", "sale", "deal_writeup")
        .annotate(
            has_deal_structure=Exists(tenant_deal_structures),
            latest_deal_structure_id=Subquery(
                tenant_deal_structures
                .order_by("-created_at", "-pk")
                .values("pk")[:1]
            ),
            latest_lender_submission_status=Subquery(
                tenant_latest_submissions.values("status")[:1]
            ),
            latest_lender_submission_id=Subquery(
                tenant_latest_submissions.values("pk")[:1]
            ),
        )
    )
    if intake:
        # Exclude any CA whose deal_structures include at least one
        # Contract row. CAs with no deal_structures survive (they are
        # the pure intake case — hand-off just landed, F&I has not
        # begun structuring). ``distinct()`` guards against duplicate
        # rows when a CA has multiple deal_structures.
        qs = qs.exclude(deal_structures__contracts__isnull=False).distinct()
    if lead is not None:
        qs = qs.filter(lead=lead)
    if since is not None:
        qs = qs.filter(captured_at__gte=since)
    return list(qs)
