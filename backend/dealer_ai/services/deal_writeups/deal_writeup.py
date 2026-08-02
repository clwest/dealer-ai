"""Milestone 11 · Increment 3 (SESSION_116) — DealWriteup write verbs.

Three verbs backing the M11.3 DealWriteup entity:

- :func:`record_deal_writeup` — create.
- :func:`approve_deal_writeup` — sales-manager approval (sets
  ``sales_manager_approved_at`` + ``sales_manager_approved_by_user``).
- :func:`hand_off_to_fandi` — sets ``handed_off_to_fandi_at`` and
  server-side creates a matching :class:`CreditApplication` per
  §5.e Option A. The auto-created CA carries the writeup's terms in
  its ``notes`` field per SESSION_116 §0.a M11.3 amendment.

State-machine invariants:

- Handoff requires prior approval
  (:class:`WriteupNotApprovedError`).
- Handoff is idempotent per writeup
  (:class:`WriteupAlreadyHandedOffError`) — a second call refuses
  rather than creating a duplicate CA.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from ...models import (
    CREDIT_APP_FORMAT_TABLET,
    CreditApplication,
    CustomerLead,
    Dealership,
    DealWriteup,
    Vehicle,
)
from ..f_and_i import record_credit_application


User = get_user_model()


class CrossTenantDealWriteupError(Exception):
    """Raised when a write names a lead or vehicle in another tenant.

    Surfaces at the endpoint layer as 404 (fail-closed), matching the
    M2.6 / M3.6 / M4.6 / M9.1 / M10.1 / M11.1 / M11.2 convention.
    """


class WriteupNotApprovedError(Exception):
    """Raised when handoff is attempted before sales-manager approval."""


class WriteupAlreadyHandedOffError(Exception):
    """Raised when a second handoff is attempted for the same writeup.

    Idempotency guard — a duplicate handoff would create a duplicate
    :class:`CreditApplication`, which has legal-retention
    consequences (M10.1 §5.e). Refusing at the service layer is the
    safer default.
    """


def record_deal_writeup(
    *,
    dealership: Dealership,
    lead: CustomerLead,
    vehicle: Vehicle,
    write_up_at: Optional[dt.datetime] = None,
    written_up_by_user: Optional[Any] = None,
    vehicle_price: Optional[Decimal] = None,
    trade_allowance: Optional[Decimal] = None,
    down_payment: Optional[Decimal] = None,
    monthly_payment_target: Optional[Decimal] = None,
    term_months_target: Optional[int] = None,
    apr_target: Optional[Decimal] = None,
    notes: str = "",
) -> DealWriteup:
    """Persist a :class:`DealWriteup`.

    Both ``lead`` and ``vehicle`` are mandatory. Cross-tenant
    references raise :class:`CrossTenantDealWriteupError`.
    ``write_up_at`` defaults to ``timezone.now()``.
    """
    if lead.dealership_id != dealership.id:
        raise CrossTenantDealWriteupError(
            f"CustomerLead {lead.pk} belongs to another tenant."
        )
    if vehicle.dealership_id != dealership.id:
        raise CrossTenantDealWriteupError(
            f"Vehicle {vehicle.pk} belongs to another tenant."
        )
    return DealWriteup.objects.create(
        dealership=dealership,
        lead=lead,
        vehicle=vehicle,
        write_up_at=write_up_at if write_up_at is not None else timezone.now(),
        written_up_by_user=written_up_by_user,
        vehicle_price=vehicle_price,
        trade_allowance=trade_allowance,
        down_payment=down_payment,
        monthly_payment_target=monthly_payment_target,
        term_months_target=term_months_target,
        apr_target=apr_target,
        notes=notes or "",
    )


def approve_deal_writeup(
    *,
    writeup: DealWriteup,
    approved_by_user: Any,
    approved_at: Optional[dt.datetime] = None,
) -> DealWriteup:
    """Mark the writeup approved by the sales manager.

    Idempotent — re-approving a writeup overwrites the approval
    timestamp + user, matching operator reality (the manager can
    re-approve after edits). The handoff verb will refuse if the
    writeup is *already handed off* (see
    :class:`WriteupAlreadyHandedOffError`).
    """
    writeup.sales_manager_approved_at = (
        approved_at if approved_at is not None else timezone.now()
    )
    writeup.sales_manager_approved_by_user = approved_by_user
    writeup.save(
        update_fields=[
            "sales_manager_approved_at",
            "sales_manager_approved_by_user",
            "updated_at",
        ]
    )
    return writeup


def _format_handoff_notes(writeup: DealWriteup) -> str:
    """Structured summary of the writeup's four-square terms.

    Per SESSION_116 §0.a M11.3 amendment: the auto-created
    CreditApplication carries this summary in its ``notes`` field so
    the F&I manager sees the deal parameters without opening the
    writeup separately.
    """
    lines = [f"Deal write-up #{writeup.pk} handoff:"]
    if writeup.vehicle_price is not None:
        lines.append(f"- Vehicle price: ${writeup.vehicle_price}")
    if writeup.trade_allowance is not None:
        lines.append(f"- Trade allowance: ${writeup.trade_allowance}")
    if writeup.down_payment is not None:
        lines.append(f"- Down payment: ${writeup.down_payment}")
    if writeup.monthly_payment_target is not None:
        lines.append(
            f"- Monthly payment target: ${writeup.monthly_payment_target}/mo"
        )
    if writeup.term_months_target is not None:
        lines.append(f"- Term target: {writeup.term_months_target} months")
    if writeup.apr_target is not None:
        lines.append(f"- APR target: {writeup.apr_target}%")
    if writeup.notes:
        lines.append("")
        lines.append(f"Writeup notes: {writeup.notes}")
    return "\n".join(lines)


@transaction.atomic
def hand_off_to_fandi(
    *,
    writeup: DealWriteup,
    handed_off_at: Optional[dt.datetime] = None,
    source_format: str = CREDIT_APP_FORMAT_TABLET,
) -> tuple[DealWriteup, CreditApplication]:
    """Hand the writeup off to F&I. Server-side auto-creates the CA.

    Per §5.e Option A + SESSION_116 §0.a M11.3 amendment:

    - Sets ``handed_off_to_fandi_at`` on the writeup.
    - Calls
      :func:`services.f_and_i.record_credit_application` with:
      - ``applicant_full_name`` = ``writeup.lead.name``
      - ``source_format`` = param (defaults to
        ``CREDIT_APP_FORMAT_TABLET`` — in-store manager tablet is
        the operator reality).
      - ``notes`` = structured summary of the four-square terms
        (see :func:`_format_handoff_notes`).
      - ``lead`` = ``writeup.lead``.
    - Returns ``(writeup, credit_application)``.

    Raises :class:`WriteupNotApprovedError` if the writeup has not
    been sales-manager approved. Raises
    :class:`WriteupAlreadyHandedOffError` if the writeup already
    has a handoff timestamp — idempotency guard prevents duplicate
    CreditApplication rows (which would trigger M10.1 §5.e
    retention-clock duplication).

    The atomic block covers the timestamp update + CA creation so
    a mid-handoff failure never leaves the writeup marked handed-off
    without a matching CA row.
    """
    if writeup.sales_manager_approved_at is None:
        raise WriteupNotApprovedError(
            f"DealWriteup {writeup.pk} has not been approved by the "
            "sales manager. Approve before hand-off."
        )
    if writeup.handed_off_to_fandi_at is not None:
        raise WriteupAlreadyHandedOffError(
            f"DealWriteup {writeup.pk} was already handed off to F&I at "
            f"{writeup.handed_off_to_fandi_at.isoformat()}. Refusing "
            "to create a duplicate CreditApplication."
        )

    writeup.handed_off_to_fandi_at = (
        handed_off_at if handed_off_at is not None else timezone.now()
    )
    writeup.save(update_fields=["handed_off_to_fandi_at", "updated_at"])

    credit_app = record_credit_application(
        dealership=writeup.dealership,
        applicant_full_name=writeup.lead.name,
        source_format=source_format,
        lead=writeup.lead,
        notes=_format_handoff_notes(writeup),
    )
    return writeup, credit_app
