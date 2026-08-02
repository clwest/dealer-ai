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

from .default_coa import DEFAULT_COA, seed_default_coa
from .journal import (
    CrossTenantGLAccountError,
    CrossTenantJournalEntryError,
    EmptyJournalEntryError,
    ImmutableJournalEntryError,
    InvalidJournalLineError,
    JournalLineInput,
    UnbalancedJournalEntryError,
    get_journal_entry,
    post_journal_entry,
    reverse_journal_entry,
)

__all__ = [
    "DEFAULT_COA",
    "CrossTenantGLAccountError",
    "CrossTenantJournalEntryError",
    "EmptyJournalEntryError",
    "ImmutableJournalEntryError",
    "InvalidJournalLineError",
    "JournalLineInput",
    "UnbalancedJournalEntryError",
    "get_journal_entry",
    "post_journal_entry",
    "reverse_journal_entry",
    "seed_default_coa",
]
