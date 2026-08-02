"""Milestone 10 · Increment 2 (SESSION_107) — DealStructure verbs.

Six verbs. Three pure ratio computations + one transactional write
path + one tenant-scoped read + one recomputation helper.

Ratio semantics (per FINANCE_DEPARTMENT_MAPPING.md §3.6):

- :func:`loan_to_value` — ``(amount_financed / sale_price) * 100``.
  Returns Decimal in percent units (e.g. ``110.50`` for 110.5%
  LTV — real-world over-financed deals hit this territory when
  the customer rolls in negative trade equity). Returns ``None``
  when ``sale_price <= 0`` (division-by-zero guard) or the
  deal-structure is missing the field.
- :func:`payment_to_income` — ``(monthly_payment /
  gross_monthly_income) * 100``. Uses the parent
  :class:`CreditApplication.gross_monthly_income`. Returns
  ``None`` when income is NULL (M10.1-era CreditApplication
  rows without income) or ≤ 0.
- :func:`debt_to_income` — ``((existing_monthly_debt +
  monthly_payment) / gross_monthly_income) * 100``. Includes the
  new monthly payment in the numerator per the FINANCE §3.6
  definition ("total monthly debt obligations INCLUDING the
  proposed new loan payment"). Returns ``None`` when either
  income OR existing_monthly_debt is NULL, or income ≤ 0.

Write-path discipline:

- :func:`record_deal_structure` computes all three ratios at
  write time and denormalizes them on the row. Callers that
  update inputs later call :func:`recompute_ratios` to refresh
  the denormalized columns.
- :func:`get_deal_structure` — pure read verb, tenant-scoped by
  ``pk``. Returns ``None`` for unknown or cross-tenant pk
  (never raises, never leaks).

All ratio verbs are Decimal-based (not float). Quantization to 2
decimal places matches the ``*_pct`` column precision.

See ``docs/roadmap/MILESTONE_10_PLANNING.md`` §1.2 + §1.2.a
Option A + §7 M10.2 for the contract.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from django.db import transaction

from ...models import (
    CreditApplication,
    DealStructure,
    Dealership,
    Vehicle,
)


_HUNDRED = Decimal("100")
_PCT_QUANT = Decimal("0.01")  # Two decimal places — matches column precision.


class CrossTenantDealStructureError(ValueError):
    """Raised when a DealStructure verb is called with a ``dealership``
    that does not match the parent credit-application's or
    vehicle's tenant.

    Subclasses :class:`ValueError` so callers catching ``ValueError``
    keep working. Named specifically so log lines + API responses can
    identify the failure mode without string-matching.

    Service-layer defense against cross-tenant writes — the model
    layer's :meth:`DealStructure.clean` is the second line. Belt +
    suspenders; do not remove either.
    """


def _quantize_pct(value: Decimal) -> Decimal:
    """Round a percent-unit Decimal to two decimal places.

    Half-up rounding matches operator expectations for the
    displayed ratio (``9.995`` → ``10.00`` not ``9.99``). Consistent
    across all three ratios so downstream compliance filters can
    equality-compare stored values without normalization.
    """
    return value.quantize(_PCT_QUANT, rounding=ROUND_HALF_UP)


def loan_to_value(deal: DealStructure) -> Optional[Decimal]:
    """Return LTV as a Decimal percent (e.g. ``110.50`` for 110.5%).

    Pure verb. Never mutates. ``(amount_financed / sale_price) *
    100``, quantized to 2 decimal places.

    Returns ``None`` when ``sale_price`` is ≤ 0 — division-by-zero
    guard. In production the model layer would reject a
    non-positive sale_price via ``DecimalField(min_value=...)`` or
    a ``clean()`` invariant, but the ratio verb is defensive
    because it can be called on any row (including test fixtures
    or migrated historical data).
    """
    if deal.sale_price <= 0:
        return None
    ratio = (deal.amount_financed / deal.sale_price) * _HUNDRED
    return _quantize_pct(ratio)


def payment_to_income(deal: DealStructure) -> Optional[Decimal]:
    """Return PTI as a Decimal percent, or ``None`` when income is
    not captured on the parent credit application.

    Pure verb. Never mutates. ``(monthly_payment /
    gross_monthly_income) * 100``, quantized to 2 decimal places.

    Returns ``None`` in two cases:

    1. The parent credit application predates M10.2 (or its
       operator didn't capture income), so
       ``gross_monthly_income`` is NULL.
    2. Income is present but ≤ 0 — division-by-zero guard.

    ``None`` propagates through the denormalized ``pti_pct``
    column so downstream compliance filters treat NULL as "not
    computable" rather than "zero income."
    """
    income = deal.credit_application.gross_monthly_income
    if income is None or income <= 0:
        return None
    ratio = (deal.monthly_payment / income) * _HUNDRED
    return _quantize_pct(ratio)


def debt_to_income(deal: DealStructure) -> Optional[Decimal]:
    """Return DTI as a Decimal percent, or ``None`` when either
    income or existing_monthly_debt is not captured on the parent
    credit application.

    Pure verb. Never mutates. ``((existing_monthly_debt +
    monthly_payment) / gross_monthly_income) * 100``, quantized
    to 2 decimal places.

    Per FINANCE §3.6 the numerator includes the proposed new
    loan payment (``monthly_payment`` from this deal structure)
    on top of the applicant's existing debt obligations from
    the bureau pull. This matches how lenders compute DTI at
    approval time: "with this new loan, does the customer's
    total monthly debt fit within our DTI ceiling?"

    Returns ``None`` in three cases:

    1. ``gross_monthly_income`` is NULL (M10.1-era CA row).
    2. ``existing_monthly_debt`` is NULL (bureau pull hasn't
       happened or the operator didn't capture the totals).
    3. Income is present but ≤ 0 — division-by-zero guard.

    Note the asymmetry with PTI: PTI needs only income to
    compute (the payment is deal-structure data). DTI needs
    both applicant-side fields. This is why DTI is more often
    NULL than PTI in production data.
    """
    income = deal.credit_application.gross_monthly_income
    existing_debt = deal.credit_application.existing_monthly_debt
    if income is None or income <= 0 or existing_debt is None:
        return None
    ratio = ((existing_debt + deal.monthly_payment) / income) * _HUNDRED
    return _quantize_pct(ratio)


def get_deal_structure(
    pk: int, *, dealership: Dealership
) -> Optional[DealStructure]:
    """Return the tenant-scoped :class:`DealStructure` for ``pk``,
    or ``None`` if unknown / cross-tenant.

    Never raises. Never leaks whether the row exists in another
    tenant. Callers translate ``None`` to HTTP 404 per the
    fail-closed pattern from M2.6 / M3.6 / M4.6 / M9.1 / M10.1.
    """
    return (
        DealStructure.objects.filter(dealership=dealership, pk=pk)
        .select_related("credit_application", "vehicle")
        .first()
    )


def _assert_same_tenant_credit_application(
    app: CreditApplication, dealership: Dealership
) -> None:
    if app.dealership_id != dealership.pk:
        raise CrossTenantDealStructureError(
            f"CreditApplication #{app.pk} belongs to "
            f"dealership_id={app.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


def _assert_same_tenant_vehicle(
    vehicle: Vehicle, dealership: Dealership
) -> None:
    if vehicle.dealership_id != dealership.pk:
        raise CrossTenantDealStructureError(
            f"Vehicle #{vehicle.stock_number} belongs to "
            f"dealership_id={vehicle.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


@transaction.atomic
def record_deal_structure(
    *,
    dealership: Dealership,
    credit_application: CreditApplication,
    vehicle: Vehicle,
    sale_price: Decimal,
    amount_financed: Decimal,
    apr: Decimal,
    term_months: int,
    monthly_payment: Decimal,
    down_payment: Decimal = Decimal("0.00"),
    trade_allowance: Decimal = Decimal("0.00"),
    trade_payoff: Decimal = Decimal("0.00"),
    taxes: Decimal = Decimal("0.00"),
    fees: Decimal = Decimal("0.00"),
    back_end_products: Optional[list] = None,
) -> DealStructure:
    """Create a :class:`DealStructure` for ``credit_application`` +
    ``vehicle`` and populate the three ratio columns at write time.

    Refuses cross-tenant parents at entry
    (:class:`CrossTenantDealStructureError`). Refuses non-positive
    ``sale_price`` / ``amount_financed`` / ``monthly_payment`` /
    ``term_months`` (:class:`ValueError`) — these are dealbreakers
    at the write path rather than at ratio time.

    Transactional — the tenant checks + insert + ratio computation
    happen inside a single ``transaction.atomic`` block so
    concurrent writes observe a serialized view of tenant state
    and every row lands with its ratios populated (or NULL when
    inputs are missing).

    Returns the persisted :class:`DealStructure` with ``ltv_pct`` /
    ``pti_pct`` / ``dti_pct`` populated from the three ratio verbs.
    """
    _assert_same_tenant_credit_application(credit_application, dealership)
    _assert_same_tenant_vehicle(vehicle, dealership)

    if sale_price <= 0:
        raise ValueError(
            f"sale_price must be > 0 (got {sale_price})."
        )
    if amount_financed < 0:
        raise ValueError(
            f"amount_financed must be >= 0 (got {amount_financed})."
        )
    if monthly_payment < 0:
        raise ValueError(
            f"monthly_payment must be >= 0 (got {monthly_payment})."
        )
    if term_months <= 0:
        raise ValueError(
            f"term_months must be > 0 (got {term_months})."
        )
    if apr < 0:
        raise ValueError(
            f"apr must be >= 0 (got {apr}); negative APR is not a "
            f"real business scenario for auto lending."
        )

    deal = DealStructure(
        dealership=dealership,
        credit_application=credit_application,
        vehicle=vehicle,
        sale_price=sale_price,
        down_payment=down_payment,
        trade_allowance=trade_allowance,
        trade_payoff=trade_payoff,
        taxes=taxes,
        fees=fees,
        amount_financed=amount_financed,
        apr=apr,
        term_months=term_months,
        monthly_payment=monthly_payment,
        back_end_products=back_end_products if back_end_products is not None else [],
    )
    # Compute ratios pre-save so the denormalized columns land in
    # the same INSERT — one row, one round-trip.
    deal.ltv_pct = loan_to_value(deal)
    deal.pti_pct = payment_to_income(deal)
    deal.dti_pct = debt_to_income(deal)
    deal.save()
    return deal


def recompute_ratios(deal: DealStructure) -> DealStructure:
    """Recompute the three ratio columns from the current row +
    parent CreditApplication state and persist.

    Callable after operator edits to ``monthly_payment`` /
    ``amount_financed`` / ``sale_price`` on the DealStructure or
    to ``gross_monthly_income`` / ``existing_monthly_debt`` on the
    parent CreditApplication. Ratios that transition from NULL to
    non-NULL (or vice-versa) survive round-trip.

    Returns the same :class:`DealStructure` instance with the
    three ratio columns updated. Persists via a targeted
    ``.save(update_fields=...)`` so no other columns are touched.
    """
    deal.ltv_pct = loan_to_value(deal)
    deal.pti_pct = payment_to_income(deal)
    deal.dti_pct = debt_to_income(deal)
    deal.save(update_fields=["ltv_pct", "pti_pct", "dti_pct", "updated_at"])
    return deal
