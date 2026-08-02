"""Milestone 13 · Increment 3 (SESSION_131) — trial-balance recompute.

Pure. Tenant-scoped. Read-only. No writes.

Per MILESTONE_13_PLANNING.md §5 M13.3 + §0.a M13.3 decisions 1-5
(all as-recommended at SESSION_131 open):

- :func:`compute_trial_balance` — aggregate JournalEntryLine rows
  for one tenant into per-account totals + grand totals + a
  balanced-flag. Optional ``as_of`` (default ``timezone.now()``)
  limits inclusion to JournalEntry rows whose ``posted_at <= as_of``.
- :class:`TrialBalanceComputationRow` — one account's row.
- :class:`TrialBalanceComputation` — the aggregate return shape.

**Zero-portfolio semantics** (§0.a M13.3 decision 5): a dealership
with no journal entries yet returns an empty balanced computation
(``rows=[]``, ``total_debits=0``, ``total_credits=0``,
``is_balanced=True``) — not a 404. A fresh dealership post-M13.1
seed is a valid trial-balance state.

**Immutable output** (§0.a M13.3 decision 1): frozen dataclass;
callers project into serialized shape. Matches the M12.7
``BhphAnalyticsSummary`` posture.

**Pure recompute, live-only** (§0.a M13.3 decision 2 + §0.a M17.1
naming resolution): every call re-aggregates from JournalEntryLine.
Durable materialization for period-close semantics lives in
``services/accounting/trial_balance_close.py`` (M17.1) via the
``TrialBalanceSnapshot`` Django model — the durable persisted
entity earns the "snapshot" name; this transient computation is
labeled ``TrialBalanceComputation`` to distinguish the two.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from ...models import (
    GL_NORMAL_BALANCE_DEBIT_TYPES,
    Dealership,
    JournalEntryLine,
)


_ZERO = Decimal("0.00")


@dataclass(frozen=True)
class TrialBalanceComputationRow:
    """One account's row in a live trial-balance computation.

    Fields:

    - ``account_code`` — six-digit COA code.
    - ``account_name`` — human-readable account name.
    - ``account_type`` — one of the five ``GL_ACCOUNT_TYPE_*``
      vocab members.
    - ``debit_total`` — sum of ``JournalEntryLine.debit`` across
      every included line (posted_at <= as_of).
    - ``credit_total`` — sum of ``JournalEntryLine.credit`` across
      every included line.
    - ``natural_balance`` — signed by account type. Debit-normal
      accounts (assets, expenses) return ``debit_total -
      credit_total``. Credit-normal accounts (liabilities, equity,
      revenue) return ``credit_total - debit_total``. Positive =
      normal-side balance, negative = contra-side (rare but valid
      — e.g. a fully-reversed asset).
    """

    account_code: str
    account_name: str
    account_type: str
    debit_total: Decimal
    credit_total: Decimal
    natural_balance: Decimal


@dataclass(frozen=True)
class TrialBalanceComputation:
    """Aggregate trial-balance state for one tenant at one moment.

    Transient — the return type of :func:`compute_trial_balance`.
    Distinct from :class:`dealer_ai.models.TrialBalanceSnapshot`,
    which is the durable materialized entity used for period-close
    workflows (M17.1). Naming discipline per §0.a M17.1 decision 1:
    the persisted entity earns "snapshot"; the transient view is a
    "computation".

    ``rows`` includes only accounts with at least one line posted at
    ``posted_at <= as_of``. Empty ``rows`` is a valid state (fresh
    dealership post-M13.1 seed with no postings — per §0.a M13.3
    decision 5 zero-portfolio semantics).

    ``is_balanced`` is ``True`` iff ``total_debits == total_credits``.
    A trial balance is required to be balanced by the M13.1
    ``UnbalancedJournalEntryError`` guard — the only way this can be
    ``False`` in production is a data-integrity break (raw
    ``JournalEntryLine.objects.create`` bypassing the service verb,
    which is a documented anti-pattern).
    """

    dealership_id: int
    dealership_slug: str
    as_of: dt.datetime
    rows: tuple[TrialBalanceComputationRow, ...]
    total_debits: Decimal
    total_credits: Decimal
    is_balanced: bool


def compute_trial_balance(
    *,
    dealership: Dealership,
    as_of: Optional[dt.datetime] = None,
) -> TrialBalanceComputation:
    """Aggregate the tenant's JournalEntryLine rows into a trial balance.

    Pure. No writes. Iterates every line whose parent JournalEntry
    has ``posted_at <= as_of`` (default: ``timezone.now()``) for the
    given tenant, groups by account, computes per-account totals
    and grand totals.

    Returns a :class:`TrialBalanceComputation`. Rows are ordered by
    account ``code`` ascending. Empty rows on a dealership with no
    postings yet — not an error state per §0.a M13.3 decision 5.

    Performance posture: single SELECT with GROUP BY over
    JournalEntryLine joined to JournalEntry (for the posted_at
    filter) and GLAccount (for code/name/type). No N+1.
    """
    effective = as_of or timezone.now()

    zero_decimal = Value(_ZERO, output_field=DecimalField(max_digits=14, decimal_places=2))

    aggregates = (
        JournalEntryLine.objects.filter(
            dealership=dealership,
            entry__posted_at__lte=effective,
        )
        .values(
            "account__code",
            "account__name",
            "account__account_type",
        )
        .annotate(
            debit_total=Coalesce(Sum("debit"), zero_decimal),
            credit_total=Coalesce(Sum("credit"), zero_decimal),
        )
        .order_by("account__code")
    )

    rows: list[TrialBalanceComputationRow] = []
    total_debits = _ZERO
    total_credits = _ZERO
    for agg in aggregates:
        debit_total = agg["debit_total"] or _ZERO
        credit_total = agg["credit_total"] or _ZERO
        account_type = agg["account__account_type"]
        if account_type in GL_NORMAL_BALANCE_DEBIT_TYPES:
            natural_balance = debit_total - credit_total
        else:
            natural_balance = credit_total - debit_total
        rows.append(
            TrialBalanceComputationRow(
                account_code=agg["account__code"],
                account_name=agg["account__name"],
                account_type=account_type,
                debit_total=debit_total,
                credit_total=credit_total,
                natural_balance=natural_balance,
            )
        )
        total_debits += debit_total
        total_credits += credit_total

    return TrialBalanceComputation(
        dealership_id=dealership.pk,
        dealership_slug=dealership.slug,
        as_of=effective,
        rows=tuple(rows),
        total_debits=total_debits,
        total_credits=total_credits,
        is_balanced=total_debits == total_credits,
    )
