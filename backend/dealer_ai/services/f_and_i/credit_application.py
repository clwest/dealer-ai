"""Milestone 10 · Increment 1 (SESSION_106) — CreditApplication verbs.

Three verbs. All deterministic. Cross-tenant writes refuse at entry.

- :func:`record_credit_application` — write path. Creates a
  :class:`CreditApplication` for a lead and/or sale, computes
  ``retention_expires_at`` from ``captured_at`` +
  :data:`dealer_ai.models.CREDIT_APP_RETENTION_YEARS`, and
  denormalizes it on the row. Refuses cross-tenant parents.
- :func:`get_credit_application` — pure read verb by pk. Tenant-
  scoped; returns ``None`` on unknown or cross-tenant pk (never
  raises, never leaks existence).
- :func:`compute_retention_expires_at` — pure verb. Returns
  ``captured_at + relativedelta(years=CREDIT_APP_RETENTION_YEARS)``.
  Callable outside the write path so the retention-clock
  invariant is testable in isolation and the value can be
  re-derived on any row that predates the field ever being
  written.

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
from django.utils import timezone

from ...models import (
    CREDIT_APP_FORMAT_CHOICES,
    CREDIT_APP_RETENTION_YEARS,
    CREDIT_APP_STATUS_CHOICES,
    CREDIT_APP_STATUS_RECEIVED,
    CreditApplication,
    CustomerLead,
    Dealership,
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
    )
