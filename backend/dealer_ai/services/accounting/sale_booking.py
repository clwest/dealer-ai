"""Sale-booking GL post — receivable + revenue + inventory relief.

SESSION_241 books-1 refit (see
``docs/_internal/TASK_books-1-acquisition-and-relief.md``): COGS
relieves :code:`121000 Used Vehicle Inventory`, never
:code:`122000 Recon Work in Process`. RWIP now only ever holds
open recon-in-progress balances. Any recon that hit RWIP for the
sold car transfers into inventory first (DR 121000 / CR 122000),
then the full basis is relieved out of inventory into COGS. RWIP
stays at zero or small-positive on the trial balance — no more
$-379K asset-side surprise.

SESSION_243 books-2 refit (see
``docs/_internal/TASK_books-2-three-floor-companies.md``): a car
that was floored at acquisition retires its own floor when it
sells. The sale-booking journal now includes a DR 210000 Floor
Plan Payable / CR 100000 Cash on Hand pair for that car's
floored principal — the acquisition basis at the moment of the
draw. Without this the payable only ever grows; with it, Floor
Plan Payable at the end of a full seed equals the acquisition
basis of the floored cars still on the lot and nothing else.

Finance-type → receivable account mapping (unchanged from M15.1):

- ``cash`` → ``100000`` Cash on Hand.
- ``retail`` → ``120000`` Contracts in Transit.
- ``bhph`` → ``123000`` BHPH Notes Receivable.

Revenue always credits ``400000`` Vehicle Sales — Retail (wholesale
variant defers — no ``SALE_FINANCE_TYPE_WHOLESALE`` vocab yet).

Lines composed per sale:

1. **DR receivable** ``sold_price`` (per ``finance_type``).
2. **CR 400000 Vehicle Sales — Retail** ``sold_price``.
3. **DR 121000 / CR 122000** for the vehicle's recon amount — only
   when recon > 0 (skipped for cars that never carried any
   posted VehicleCost). This is the RWIP → Inventory transfer.
4. **DR 500000 Cost of Vehicle Sales / CR 121000 Used Vehicle
   Inventory** for the vehicle's ``total_investment`` (acquisition
   + recon).

Zero-cost path (unchanged): when ``total_investment == 0`` the COGS
pair and the transfer are both skipped, revenue-only entry is
posted, and a warning is logged.

Un-posted VehicleCost flush still happens in
:func:`services.sale.record_sale` before this verb runs — this
module assumes every posted cost is visible.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction

from ...models import (
    SALE_FINANCE_TYPE_BHPH,
    SALE_FINANCE_TYPE_CASH,
    SALE_FINANCE_TYPE_RETAIL,
    Dealership,
    GLAccount,
    JournalEntry,
    Sale,
)
from ..vehicle_ledger import compute_totals
from .journal import (
    CrossTenantGLAccountError,
    JournalLineInput,
    post_journal_entry,
)
from .vehicle_cost import MissingDefaultAccountError

_LOGGER = logging.getLogger("dealer_ai.accounting.sale_booking")


CASH_ACCOUNT_CODE = "100000"
CONTRACTS_IN_TRANSIT_ACCOUNT_CODE = "120000"
USED_VEHICLE_INVENTORY_ACCOUNT_CODE = "121000"
BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE = "123000"
RECON_WIP_ACCOUNT_CODE = "122000"
FLOOR_PLAN_PAYABLE_ACCOUNT_CODE = "210000"
VEHICLE_SALES_RETAIL_ACCOUNT_CODE = "400000"
COST_OF_VEHICLE_SALES_ACCOUNT_CODE = "500000"


# §5.b Option A — finance-type → receivable account code.
_FINANCE_TYPE_TO_RECEIVABLE_CODE: dict[str, str] = {
    SALE_FINANCE_TYPE_CASH: CASH_ACCOUNT_CODE,
    SALE_FINANCE_TYPE_RETAIL: CONTRACTS_IN_TRANSIT_ACCOUNT_CODE,
    SALE_FINANCE_TYPE_BHPH: BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE,
}


class UnmappedFinanceTypeError(RuntimeError):
    """Raised when ``Sale.finance_type`` is not in the receivable-mapping table.

    Signals a broken invariant — every value in
    :data:`models.SALE_FINANCE_TYPE_CHOICES` must have an entry in
    :data:`_FINANCE_TYPE_TO_RECEIVABLE_CODE`. Fires only if a new
    finance-type vocab value ships without a corresponding mapping
    extension.
    """


def _lookup_required_account(
    dealership: Dealership, code: str
) -> GLAccount:
    """Return the active :class:`GLAccount` with ``code`` for ``dealership``.

    Mirrors :func:`services.accounting.vehicle_cost._lookup_required_account`
    verbatim so both M13.2 and M15.1 have identical account-lookup
    semantics. Raises :class:`MissingDefaultAccountError` when the
    account is absent or inactive — signals a broken seed-invariant,
    not a user error.
    """
    try:
        return GLAccount.objects.get(
            dealership=dealership, code=code, is_active=True
        )
    except GLAccount.DoesNotExist as exc:
        raise MissingDefaultAccountError(
            f"Required default COA account {code!r} missing (or "
            f"inactive) for dealership {dealership.slug!r}. Run "
            "services.accounting.seed_default_coa or re-activate "
            "the account before M15.1 sale-booking will succeed."
        ) from exc


def _resolve_receivable_account(
    dealership: Dealership, finance_type: str
) -> GLAccount:
    try:
        code = _FINANCE_TYPE_TO_RECEIVABLE_CODE[finance_type]
    except KeyError as exc:
        raise UnmappedFinanceTypeError(
            f"Sale.finance_type={finance_type!r} has no receivable-account "
            "mapping. Extend _FINANCE_TYPE_TO_RECEIVABLE_CODE when new "
            "finance-type vocab lands."
        ) from exc
    return _lookup_required_account(dealership, code)


@transaction.atomic
def post_sale_booking_journal(
    *,
    dealership: Dealership,
    sale: Sale,
    posted_by_user=None,
) -> JournalEntry:
    """Post the GL journal entry for one Sale.

    Atomic — either the JournalEntry + every line commits, or nothing
    does. Called from :func:`services.sale.record_sale` inside its
    existing ``@transaction.atomic`` block; the nested atomic is a
    no-op but keeps this verb self-contained for direct-call test
    paths.

    Composes up to four lines:

    1. **DR receivable** for ``sale.sold_price`` — account picked
       per §5.b Option A by ``sale.finance_type`` (cash → 100000,
       retail → 120000 CIT, bhph → 123000 BHPH Notes Receivable).
    2. **CR 400000 Vehicle Sales — Retail** for ``sale.sold_price``.
    3. **DR 500000 Cost of Vehicle Sales — Retail** for
       ``vehicle.total_investment`` — skipped if
       ``total_investment == 0`` per §5.c Option A.
    4. **CR 122000 Recon Work in Process** for the same amount —
       skipped alongside line 3.

    Refuses:

    - Cross-tenant Sale
      (:class:`journal.CrossTenantGLAccountError` — 404).
    - Missing / inactive default COA account
      (:class:`MissingDefaultAccountError` — signals broken
      invariant, not user error).
    - Unmapped finance-type
      (:class:`UnmappedFinanceTypeError` — signals broken
      invariant, not user error).

    Zero-total-investment behavior per §5.c Option A: revenue pair
    still posts; COGS/Recon-WIP pair is skipped; warning logged so
    the missing cost basis is discoverable.

    Returns the persisted :class:`JournalEntry`.
    """
    if sale.dealership_id != dealership.id:
        raise CrossTenantGLAccountError(
            f"Sale {sale.pk} belongs to another tenant."
        )

    receivable = _resolve_receivable_account(
        dealership, sale.finance_type
    )
    revenue = _lookup_required_account(
        dealership, VEHICLE_SALES_RETAIL_ACCOUNT_CODE
    )

    stock_number = getattr(sale.vehicle, "stock_number", "?")
    description = (
        f"Sold #{stock_number} — Sale #{sale.pk} "
        f"({sale.get_finance_type_display()})"
    )
    receivable_memo = (
        "Amount owed by buyer"
        + (f" via {sale.lender_name}" if sale.lender_name else "")
    )
    revenue_memo = "Vehicle sale revenue"

    lines: list[JournalLineInput] = [
        JournalLineInput(
            account=receivable,
            debit=sale.sold_price,
            memo=receivable_memo,
        ),
        JournalLineInput(
            account=revenue,
            credit=sale.sold_price,
            memo=revenue_memo,
        ),
    ]

    totals = compute_totals(sale.vehicle, dealership=dealership)
    cogs_amount = totals.total_investment
    if cogs_amount > Decimal("0.00"):
        # SESSION_241 books-1 — first move any RWIP for THIS car into
        # inventory (DR 121000 / CR 122000), then relieve the full
        # basis (acquisition + recon) out of inventory into COGS. The
        # transfer keeps RWIP at zero for sold cars while unsold cars
        # still in recon retain their small-positive RWIP balances.
        inventory = _lookup_required_account(
            dealership, USED_VEHICLE_INVENTORY_ACCOUNT_CODE
        )
        recon_wip = _lookup_required_account(
            dealership, RECON_WIP_ACCOUNT_CODE
        )
        cogs = _lookup_required_account(
            dealership, COST_OF_VEHICLE_SALES_ACCOUNT_CODE
        )

        # Recon basis for this vehicle only: flooring + recon
        # categories + administrative + photography. The
        # ``compute_totals`` verb already partitions these; we sum the
        # four category buckets which equal ``actual_cost_total`` (no
        # estimates by construction).
        recon_amount = totals.actual_cost_total
        if recon_amount > Decimal("0.00"):
            lines.append(
                JournalLineInput(
                    account=inventory,
                    debit=recon_amount,
                    memo="Move recon spend into the car's basis",
                )
            )
            lines.append(
                JournalLineInput(
                    account=recon_wip,
                    credit=recon_amount,
                    memo="Clear this car's Recon WIP",
                )
            )

        lines.append(
            JournalLineInput(
                account=cogs,
                debit=cogs_amount,
                memo="Cost of vehicle sold",
            )
        )
        lines.append(
            JournalLineInput(
                account=inventory,
                credit=cogs_amount,
                memo="Vehicle out of inventory",
            )
        )
    else:
        # Zero-cost basis: skip COGS + transfer; log so miss is
        # discoverable and the operator can post an adjusting entry.
        _LOGGER.warning(
            "accounting.sale_booking zero-cost basis dealership=%s "
            "sale_pk=%s vehicle_stock=%s — COGS pair skipped, revenue "
            "posted only. Cost basis may be recorded later; consider "
            "an adjusting entry once known.",
            dealership.slug,
            sale.pk,
            stock_number,
        )

    # SESSION_243 books-2 — a floored car retires its own floor on
    # sale. DR 210000 Floor Plan Payable / CR 100000 Cash on Hand for
    # the acquisition principal that was drawn on the floor line at
    # acquisition (purchase price + acquisition fees — the same basis
    # that was credited to 210000 by ``post_acquisition_journal``).
    # Without this the payable only ever grows and Floor Plan Payable
    # becomes the next account that lies. The invariant asserted by
    # the books-2 tests: after a full seed, Floor Plan Payable equals
    # the acquisition basis of floored cars still on the lot and
    # nothing else.
    acquisition = getattr(sale.vehicle, "acquisition", None)
    if (
        acquisition is not None
        and acquisition.floor_plan_company_id is not None
    ):
        floored_principal = (
            acquisition.purchase_price
            + acquisition.buyer_fees
            + acquisition.arbitration_fees
            + acquisition.transportation_cost
            + acquisition.title_acquisition_cost
        )
        if floored_principal > Decimal("0.00"):
            floor_plan_payable = _lookup_required_account(
                dealership, FLOOR_PLAN_PAYABLE_ACCOUNT_CODE
            )
            cash = _lookup_required_account(
                dealership, CASH_ACCOUNT_CODE
            )
            company = acquisition.floor_plan_company
            lines.append(
                JournalLineInput(
                    account=floor_plan_payable,
                    debit=floored_principal,
                    memo=(
                        f"Retire floor plan — {company.name} "
                        f"({company.code})"
                    ),
                )
            )
            lines.append(
                JournalLineInput(
                    account=cash,
                    credit=floored_principal,
                    memo="Floor plan payoff on sale",
                )
            )

    return post_journal_entry(
        dealership=dealership,
        description=description,
        posted_at=None,
        posted_by_user=posted_by_user,
        lines=lines,
    )
