"""Milestone 9 · Increment 1 (SESSION_100) — Sale write + gross-realized verbs.

Two verbs. Both deterministic. Both refuse cross-tenant access at
entry.

- :func:`record_sale` — write path. Creates a :class:`Sale` for a
  Vehicle, computes ``gross_realized`` against the M2 ledger, and
  denormalizes it on the row. Refuses if the Vehicle already has a
  Sale (OneToOne invariant enforced at both service + DB layers).
- :func:`gross_realized` — pure read verb. Returns
  ``sale.sold_price - vehicle.total_investment`` per the
  ``services.vehicle_ledger`` semantic contract (sunk cost only —
  estimates excluded). Never mutates the Sale, the Vehicle, or the
  ledger. Callable at any point after write to verify or re-derive
  the stored ``gross_realized`` if ledger state has evolved.

The distinction between the stored ``Sale.gross_realized`` field
and the :func:`gross_realized` verb is the M2 "denormalize for
aggregate speed, verb for correctness" pattern. M9.3 analytics
queries aggregate the denormalized field directly (no per-row
ledger recomputation); the verb exists so callers can re-verify or
recompute when ledger state changes.

Semantic decision — *`gross_realized` uses `total_investment`, not
`projected_total_investment`*:

- ``Vehicle.total_investment`` = acquisition + actual costs.
  Sunk cash the store has committed. This is the true cost basis
  at sale time.
- Estimated costs (`is_estimate=True` on VehicleCost) are open
  work orders / projected repairs. They should NOT reduce the
  realized gross — the money hasn't been spent yet.

This choice locks the same "estimated spend is NOT invested money"
invariant that ``services.vehicle_ledger.LedgerTotals`` enforces
for the M2 ledger.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import transaction

from ..accounting.sale_booking import post_sale_booking_journal
from ..accounting.vehicle_cost import (
    detect_unposted_costs,
    post_vehicle_cost_journal,
)
from ..vehicle_ledger import compute_totals
from ...models import (
    SALE_FINANCE_TYPE_CHOICES,
    CustomerLead,
    Dealership,
    Sale,
    Vehicle,
)


_VALID_FINANCE_TYPES = frozenset(key for key, _ in SALE_FINANCE_TYPE_CHOICES)


class CrossTenantSaleError(ValueError):
    """Raised when a Sale verb is called with a ``dealership`` that
    does not match the target ``Vehicle``'s or ``buyer``'s tenant.

    Subclasses :class:`ValueError` so callers catching ``ValueError``
    keep working. Named specifically so log lines + API responses can
    identify the failure mode without string-matching.

    Service-layer defense against cross-tenant writes — the model
    layer's :meth:`Sale.clean` is the second line. Belt + suspenders;
    do not remove either.
    """


class SaleAlreadyExistsError(ValueError):
    """Raised when :func:`record_sale` is called against a Vehicle
    that already has a Sale row.

    The OneToOne constraint on ``Sale.vehicle`` would raise
    :class:`django.db.utils.IntegrityError` at the DB layer; this
    service-level check surfaces the same invariant with a
    domain-specific error type so the endpoint layer can map it to
    HTTP 409 Conflict without string-matching a DB error message.
    """


def _assert_same_tenant_vehicle(vehicle: Vehicle, dealership: Dealership) -> None:
    if vehicle.dealership_id != dealership.pk:
        raise CrossTenantSaleError(
            f"Vehicle #{vehicle.stock_number} belongs to "
            f"dealership_id={vehicle.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


def _assert_same_tenant_buyer(
    buyer: CustomerLead, dealership: Dealership
) -> None:
    if buyer.dealership_id != dealership.pk:
        raise CrossTenantSaleError(
            f"CustomerLead #{buyer.pk} belongs to "
            f"dealership_id={buyer.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


def gross_realized(sale: Sale) -> Decimal:
    """Return ``sale.sold_price - sale.vehicle.total_investment``.

    Pure verb. Never mutates. Same ``sale`` + same DB state →
    same :class:`Decimal`.

    Uses ``total_investment`` (sunk cost only — see module
    docstring) via :func:`services.vehicle_ledger.compute_totals`.
    Refuses to touch a Vehicle in a different tenant than the
    Sale's ``dealership`` — although the model-layer
    :meth:`Sale.clean` guard prevents constructing such a Sale in
    the first place, this verb re-checks so an in-memory mutation
    can't leak per-tenant totals.

    Signed Decimal — negative when the sale closed below cost
    basis.
    """
    _assert_same_tenant_vehicle(sale.vehicle, sale.dealership)
    totals = compute_totals(sale.vehicle, dealership=sale.dealership)
    return sale.sold_price - totals.total_investment


@transaction.atomic
def record_sale(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    sale_date: date,
    sold_price: Decimal,
    finance_type: str,
    buyer: Optional[CustomerLead] = None,
    lender_name: str = "",
    posted_by_user=None,
) -> Sale:
    """Create a :class:`Sale` for ``vehicle`` and populate
    ``gross_realized`` at write time.

    Refuses cross-tenant writes at entry
    (:class:`CrossTenantSaleError`). Refuses to overwrite an
    existing Sale (:class:`SaleAlreadyExistsError`). Refuses
    unknown ``finance_type`` values (:class:`ValueError`).

    Transactional — the ledger read + Sale insert + M15.1 sibling
    GL posts happen inside a single ``transaction.atomic`` block so
    a concurrent second ``record_sale`` on the same Vehicle observes
    a serialized view of the OneToOne uniqueness invariant AND so
    that a GL post failure rolls back the Sale row.

    M15.1 GL-posting side effects (per ``MILESTONE_15_PLANNING.md``
    §5.d + §5.b Option A, confirmed at SESSION_139):

    1. **Flush unposted VehicleCost rows for the target vehicle**
       via :func:`services.accounting.post_vehicle_cost_journal` —
       ensures Recon WIP has posted the full ``total_investment``
       before the sale-booking journal clears it. Keeps trial
       balance always internally consistent (no transient negative
       Recon WIP for this vehicle).
    2. **Post the sale-booking JournalEntry** via
       :func:`services.accounting.post_sale_booking_journal` —
       finance-type-aware receivable line + revenue line + COGS +
       Recon-WIP-clear lines. The ``posted_by_user`` kwarg
       propagates from the view so the M14.3 journal-entry browser
       shows who booked the sale.

    Returns the persisted :class:`Sale` with ``gross_realized``
    populated from :func:`gross_realized`.
    """
    _assert_same_tenant_vehicle(vehicle, dealership)
    if buyer is not None:
        _assert_same_tenant_buyer(buyer, dealership)

    if finance_type not in _VALID_FINANCE_TYPES:
        raise ValueError(
            f"Unknown finance_type={finance_type!r}. "
            f"Valid values: {sorted(_VALID_FINANCE_TYPES)!r}."
        )

    if Sale.objects.filter(vehicle=vehicle).exists():
        raise SaleAlreadyExistsError(
            f"Vehicle #{vehicle.stock_number} already has a Sale."
        )

    # §5.d Option A — flush unposted VehicleCost rows for the target
    # vehicle before the sale-booking journal posts. Same transaction:
    # either every prerequisite cost + the sale-booking entry commit,
    # or nothing does. Reuses M13.2's tenant-scoped detector filter
    # (``posted_at__isnull=True AND is_estimate=False``).
    unposted_for_vehicle = list(
        detect_unposted_costs(dealership=dealership).filter(
            vehicle=vehicle
        )
    )
    for cost in unposted_for_vehicle:
        post_vehicle_cost_journal(
            dealership=dealership, vehicle_cost=cost
        )

    # Refresh ``total_investment`` AFTER the flush so the
    # ``gross_realized`` denormalization reflects the same ledger
    # snapshot the sale-booking journal will use for its COGS line.
    totals = compute_totals(vehicle, dealership=dealership)
    computed_gross = sold_price - totals.total_investment

    sale = Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        buyer=buyer,
        sale_date=sale_date,
        sold_price=sold_price,
        finance_type=finance_type,
        lender_name=lender_name,
        gross_realized=computed_gross,
    )

    # §5.b Option A + §5.c Option A — sibling-service post of the
    # sale-booking JournalEntry. Zero-cost path handled inside the
    # verb (revenue-only + warning log).
    post_sale_booking_journal(
        dealership=dealership,
        sale=sale,
        posted_by_user=posted_by_user,
    )

    return sale
