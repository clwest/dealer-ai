"""Milestone 13 · Increment 1 (SESSION_129) — default chart of accounts.

Per MILESTONE_13_PLANNING.md §5.b Option A (user-confirmed at
SESSION_129 open, recorded in §0.a): platform ships a fixed default
COA per Dealership. Per-dealer overrides defer to M14+.

Shape follows ACCOUNTING §1.1 NADA / dealer-standard chart —
six-digit account numbers organized as 1-series assets, 2-series
liabilities, 3-series equity, 4-series sales revenue, 5-series
cost of sales, 6-series variable expense, 7-series semi-fixed,
8-series fixed expense, 9-series other income/expense.

The set is deliberately compact — it covers every posting target
the M13.2+ operational-reconciliation slices need (M2 cost accrual,
M9 sale-booking, M10 F&I chargeback, M12 BHPH payment posting)
without over-modeling. Additional accounts land as follow-on
milestones surface operator evidence (per M11 §6 lesson 18 vocab-
set posture).

The migration ``0043_m131_accounting_substrate.py`` loads this
fixture into every existing Dealership at apply time via a
RunPython step. :func:`seed_default_coa` provides the same seeding
verb for future Dealership creation (currently not signal-wired
— explicit call via management command or M14+ operator UI).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...models import (
    GL_ACCOUNT_TYPE_ASSET,
    GL_ACCOUNT_TYPE_EQUITY,
    GL_ACCOUNT_TYPE_EXPENSE,
    GL_ACCOUNT_TYPE_LIABILITY,
    GL_ACCOUNT_TYPE_REVENUE,
    GLAccount,
)

if TYPE_CHECKING:
    from ...models import Dealership


# (code, name, account_type) tuples. Six-digit codes per ACCOUNTING
# §1.1 convention. Order preserved on insert so downstream iteration
# by ``code`` yields the same order as this list.
DEFAULT_COA: tuple[tuple[str, str, str], ...] = (
    # 1-series — assets
    ("100000", "Cash on Hand", GL_ACCOUNT_TYPE_ASSET),
    ("110000", "Bank — Operating", GL_ACCOUNT_TYPE_ASSET),
    ("120000", "Contracts in Transit", GL_ACCOUNT_TYPE_ASSET),
    ("121000", "Used Vehicle Inventory", GL_ACCOUNT_TYPE_ASSET),
    ("122000", "Recon Work in Process", GL_ACCOUNT_TYPE_ASSET),
    ("123000", "BHPH Notes Receivable", GL_ACCOUNT_TYPE_ASSET),
    ("130000", "A/R — Reserve Receivable", GL_ACCOUNT_TYPE_ASSET),
    ("131000", "A/R — Warranty Commission", GL_ACCOUNT_TYPE_ASSET),
    # 2-series — liabilities
    ("200000", "Accounts Payable — Trade", GL_ACCOUNT_TYPE_LIABILITY),
    ("210000", "Floor Plan Payable", GL_ACCOUNT_TYPE_LIABILITY),
    ("220000", "Sales Tax Payable", GL_ACCOUNT_TYPE_LIABILITY),
    ("230000", "Customer Deposits", GL_ACCOUNT_TYPE_LIABILITY),
    # 3-series — equity
    ("300000", "Owner Equity", GL_ACCOUNT_TYPE_EQUITY),
    ("310000", "Retained Earnings", GL_ACCOUNT_TYPE_EQUITY),
    # 4-series — revenue
    ("400000", "Vehicle Sales — Retail", GL_ACCOUNT_TYPE_REVENUE),
    ("410000", "Vehicle Sales — Wholesale", GL_ACCOUNT_TYPE_REVENUE),
    ("420000", "F&I Reserve Income", GL_ACCOUNT_TYPE_REVENUE),
    ("430000", "BHPH Interest Income", GL_ACCOUNT_TYPE_REVENUE),
    # 5-series — cost of sales
    ("500000", "Cost of Vehicle Sales — Retail", GL_ACCOUNT_TYPE_EXPENSE),
    ("510000", "Recon Expense", GL_ACCOUNT_TYPE_EXPENSE),
    # 6-series — variable expense
    ("600000", "Advertising Expense", GL_ACCOUNT_TYPE_EXPENSE),
    # 7-series — semi-fixed expense
    ("700000", "Salaries — Sales", GL_ACCOUNT_TYPE_EXPENSE),
    # 8-series — fixed expense
    ("800000", "Rent Expense", GL_ACCOUNT_TYPE_EXPENSE),
    # 9-series — other income/expense
    ("900000", "Interest Expense — Floor Plan", GL_ACCOUNT_TYPE_EXPENSE),
)


def seed_default_coa(dealership: "Dealership") -> int:
    """Ensure every :data:`DEFAULT_COA` account exists on ``dealership``.

    Idempotent — uses ``get_or_create`` on ``(dealership, code)`` so
    re-running the seeder against a partially-seeded tenant fills in
    only the missing rows without disturbing existing ones. Returns
    the count of newly-created rows.

    Callers today:

    - ``migrations/0043_m131_accounting_substrate.py`` at apply time
      (backfills existing dealerships — using the historical model
      via ``apps.get_model``, not this verb, so migrations stay
      self-contained).
    - Ad-hoc management command / M14+ operator UI (future).

    Does NOT wire into ``pre_save`` on Dealership creation — that
    coupling defers until operator evidence names a need (per M11
    §6 lesson 18 fixed-vocab posture).
    """
    created = 0
    for code, name, account_type in DEFAULT_COA:
        _, was_created = GLAccount.objects.get_or_create(
            dealership=dealership,
            code=code,
            defaults={"name": name, "account_type": account_type},
        )
        if was_created:
            created += 1
    return created
