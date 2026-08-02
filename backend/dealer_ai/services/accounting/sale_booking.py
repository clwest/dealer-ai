"""Milestone 15 · Increment 1 (SESSION_140) — sale-booking GL post.

One atomic sibling-service verb per MILESTONE_15_PLANNING.md §7 M15.1
+ §5.a-§5.f (all as-recommended at SESSION_139 open):

- :func:`post_sale_booking_journal` — atomic sibling-service call.
  Composes finance-type-aware receivable line + revenue line + COGS
  line + Recon-WIP-clear line and delegates to
  :func:`post_journal_entry` for the balanced double-entry write.

Called from :func:`services.sale.record_sale` inside its existing
``@transaction.atomic`` block per §5.d Option C hybrid posture (sale
booking is operator intent — synchronous, not detector-driven).

Finance-type → receivable account mapping per §5.b Option A:

- ``cash`` → ``100000`` Cash on Hand.
- ``retail`` → ``120000`` Contracts in Transit.
- ``bhph`` → ``123000`` BHPH Notes Receivable.

Revenue always credits ``400000`` Vehicle Sales — Retail (wholesale
variant defers per §3 item 7 — no ``SALE_FINANCE_TYPE_WHOLESALE``
vocab yet).

COGS pair debits ``500000`` Cost of Vehicle Sales — Retail and
credits ``122000`` Recon Work in Process for the vehicle's
``total_investment`` (matches the M13.2 uniform-mapping posture —
every VehicleCost sits in Recon WIP until sale clears it).

Zero-cost path per §5.c Option A: when ``total_investment == 0`` the
COGS pair is skipped (revenue pair still posts) and a warning is
logged. M13.1 rejects zero-value lines outright so a $0.00 COGS pair
is architecturally impossible.

Un-posted VehicleCost flush happens in :func:`services.sale.record_sale`
per §5.d Option A — this module assumes all costs for the vehicle
have posted by the time it's called.
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
BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE = "123000"
RECON_WIP_ACCOUNT_CODE = "122000"
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
        f"M9 sale booking — Sale #{sale.pk} of stock {stock_number} "
        f"({sale.get_finance_type_display()})"
    )
    receivable_memo = (
        f"Sale #{sale.pk} — receivable"
        + (f" ({sale.lender_name})" if sale.lender_name else "")
    )
    revenue_memo = f"Sale #{sale.pk} — revenue"

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
        cogs = _lookup_required_account(
            dealership, COST_OF_VEHICLE_SALES_ACCOUNT_CODE
        )
        recon_wip = _lookup_required_account(
            dealership, RECON_WIP_ACCOUNT_CODE
        )
        lines.append(
            JournalLineInput(
                account=cogs,
                debit=cogs_amount,
                memo=f"Sale #{sale.pk} — COGS",
            )
        )
        lines.append(
            JournalLineInput(
                account=recon_wip,
                credit=cogs_amount,
                memo=f"Sale #{sale.pk} — clear Recon WIP",
            )
        )
    else:
        # §5.c Option A: skip COGS pair; log so miss is discoverable.
        _LOGGER.warning(
            "accounting.sale_booking zero-cost basis dealership=%s "
            "sale_pk=%s vehicle_stock=%s — COGS pair skipped, revenue "
            "posted only. Cost basis may be recorded later; consider "
            "an adjusting entry once known.",
            dealership.slug,
            sale.pk,
            stock_number,
        )

    return post_journal_entry(
        dealership=dealership,
        description=description,
        posted_at=None,
        posted_by_user=posted_by_user,
        lines=lines,
    )
