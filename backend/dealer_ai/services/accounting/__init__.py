"""Milestone 13 · Increment 1 (SESSION_129) — accounting substrate.

Three verbs per ``MILESTONE_13_PLANNING.md`` §7 M13.1 + §5.a Option A
+ §5.c Option A + §5.e Option A (user-confirmed at SESSION_129 open,
recorded in §0.a):

- :func:`post_journal_entry` — atomic write of a JournalEntry + its
  lines. Refuses unbalanced entries, cross-tenant account references,
  and empty / malformed lines.
- :func:`reverse_journal_entry` — atomic write of the reversal
  JournalEntry with inverted debits/credits. Original row is not
  modified per §5.c Option A immutability.
- :func:`get_journal_entry` — tenant-scoped read.

Plus a supporting seeder for the platform-shipped default chart of
accounts (§5.b Option A):

- :func:`seed_default_coa` — idempotent per-Dealership seeder for the
  default COA. Called from ``migrations/0043_m131_accounting_substrate.py``
  at apply time (via the historical model) and available for ad-hoc /
  future-M14 dealer-creation flows.
- :data:`DEFAULT_COA` — the 24-account fixture (per ACCOUNTING §1.1
  NADA-style chart).

Domain-error → HTTP mapping (consumed by ``views_accounting.py``):

- :class:`EmptyJournalEntryError` — 400.
- :class:`InvalidJournalLineError` — 400.
- :class:`UnbalancedJournalEntryError` — 400.
- :class:`CrossTenantGLAccountError` — 404 (fail-closed).
- :class:`CrossTenantJournalEntryError` — 404 (fail-closed).
- :class:`ImmutableJournalEntryError` — 409 (empty reason on
  reversal is the only mutation attempt currently guarded).
"""

from __future__ import annotations

from .bhph_payment import (
    BHPH_INTEREST_INCOME_ACCOUNT_CODE,
    UnexpectedBhphPaymentFeesError,
    detect_unposted_bhph_payments,
    post_all_unposted_bhph_payments_for_dealership,
    post_bhph_payment_journal,
)
from .default_coa import DEFAULT_COA, seed_default_coa
from .journal import (
    CrossTenantGLAccountError,
    CrossTenantJournalEntryError,
    EmptyJournalEntryError,
    ImmutableJournalEntryError,
    InvalidJournalLineError,
    JournalEntryListPage,
    JournalLineInput,
    UnbalancedJournalEntryError,
    get_journal_entry,
    list_journal_entries,
    post_journal_entry,
    reverse_journal_entry,
)
from .snapshot import (
    TrialBalanceComputation,
    TrialBalanceComputationRow,
    compute_trial_balance,
)
from .template import (
    DuplicateJournalEntryTemplateNameError,
    EmptyJournalEntryTemplateError,
    InvalidJournalEntryTemplateLineError,
    TemplateLineInput,
    UnbalancedJournalEntryTemplateError,
    create_journal_entry_template,
    delete_journal_entry_template,
    get_journal_entry_template,
    list_journal_entry_templates,
    update_journal_entry_template,
)
from .trial_balance_close import (
    DuplicateTrialBalanceSnapshotError,
    TrialBalanceSnapshotListPage,
    freeze_trial_balance,
    get_trial_balance_snapshot,
    list_trial_balance_snapshots,
)
from .sale_booking import (
    BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE,
    CASH_ACCOUNT_CODE,
    CONTRACTS_IN_TRANSIT_ACCOUNT_CODE,
    COST_OF_VEHICLE_SALES_ACCOUNT_CODE,
    VEHICLE_SALES_RETAIL_ACCOUNT_CODE,
    UnmappedFinanceTypeError,
    post_sale_booking_journal,
)
from .vehicle_cost import (
    AP_TRADE_ACCOUNT_CODE,
    RECON_WIP_ACCOUNT_CODE,
    MissingDefaultAccountError,
    detect_cost_posting_failures,
    detect_unposted_costs,
    post_all_unposted_costs_for_dealership,
    post_vehicle_cost_journal,
)

__all__ = [
    "AP_TRADE_ACCOUNT_CODE",
    "BHPH_INTEREST_INCOME_ACCOUNT_CODE",
    "BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE",
    "CASH_ACCOUNT_CODE",
    "CONTRACTS_IN_TRANSIT_ACCOUNT_CODE",
    "COST_OF_VEHICLE_SALES_ACCOUNT_CODE",
    "DEFAULT_COA",
    "CrossTenantGLAccountError",
    "CrossTenantJournalEntryError",
    "DuplicateJournalEntryTemplateNameError",
    "DuplicateTrialBalanceSnapshotError",
    "EmptyJournalEntryError",
    "EmptyJournalEntryTemplateError",
    "ImmutableJournalEntryError",
    "InvalidJournalLineError",
    "InvalidJournalEntryTemplateLineError",
    "JournalEntryListPage",
    "JournalLineInput",
    "TemplateLineInput",
    "MissingDefaultAccountError",
    "RECON_WIP_ACCOUNT_CODE",
    "TrialBalanceComputation",
    "TrialBalanceComputationRow",
    "TrialBalanceSnapshotListPage",
    "UnbalancedJournalEntryError",
    "UnbalancedJournalEntryTemplateError",
    "UnexpectedBhphPaymentFeesError",
    "UnmappedFinanceTypeError",
    "VEHICLE_SALES_RETAIL_ACCOUNT_CODE",
    "compute_trial_balance",
    "create_journal_entry_template",
    "delete_journal_entry_template",
    "detect_cost_posting_failures",
    "detect_unposted_bhph_payments",
    "detect_unposted_costs",
    "freeze_trial_balance",
    "get_journal_entry",
    "get_journal_entry_template",
    "get_trial_balance_snapshot",
    "list_journal_entries",
    "list_journal_entry_templates",
    "list_trial_balance_snapshots",
    "post_all_unposted_bhph_payments_for_dealership",
    "post_all_unposted_costs_for_dealership",
    "post_bhph_payment_journal",
    "post_journal_entry",
    "post_sale_booking_journal",
    "post_vehicle_cost_journal",
    "reverse_journal_entry",
    "seed_default_coa",
    "update_journal_entry_template",
]
