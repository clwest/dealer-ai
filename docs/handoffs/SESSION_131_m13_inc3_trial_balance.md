---
title: "SESSION_131 handoff — Milestone 13 · Increment 3 (M13.3 — Trial-balance snapshot)"
status: historical
type: handoff
date: 2026-08-02
session: 131
milestone: 13
milestone_status: in_progress
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_131 — Milestone 13 · Increment 3 (M13.3 — Trial-balance snapshot)

## What shipped

Third M13 slice per
`MILESTONE_13_PLANNING.md` §5 M13.3.
Pure recompute trial-balance verb +
`TrialBalanceRow` / `TrialBalanceSnapshot`
frozen dataclasses + GET endpoint. No
snapshot entity, no writes — the
substrate is a read-side aggregator
over the M13.1 `JournalEntryLine`
substrate.

**Five implementation-time §0.a M13.3
micro-decisions confirmed as-
recommended at SESSION_131 open.** Per
M10-M13.2 precedent these do not
count against the planning-time streak
(which stands at 47 M5.1 → M13.0).

- M13.3 · 1: frozen dataclass
  output (M12 §6 lesson 15 pattern).
- M13.3 · 2: pure recompute; no
  snapshot entity (defers to M14+
  close workflow).
- M13.3 · 3: reuse
  `IsSalesManagerOrOwnerAtActiveDealership`.
- M13.3 · 4: optional `as_of`
  (default `timezone.now()`);
  includes lines where
  `entry.posted_at <= as_of`.
- M13.3 · 5: empty balanced snapshot
  for zero-portfolio (not 404).

## By the numbers

- **Backend baseline: 4,240 pass, 1
  skipped, 0 fail** (was 4,220 at
  M13.2 close — **+20 tests, 0
  regressions**). Target was ~20;
  hit exactly.
- **Frontend Vitest baseline: 78 pass**
  (unchanged — no frontend at M13.3
  per §5.f Option C).
- **No new migration** — read-only
  aggregate, no schema change.
- **Tenancy carriers: 47** (unchanged
  — pure aggregate reads).
- **DRF admin surface: 101 → 102**
  (`admin-trial-balance`).
- **Frontend operator routes:** 17
  (unchanged — no UI at M13).
- **Permission classes: 8** (unchanged
  — reused
  `IsSalesManagerOrOwnerAtActiveDealership`;
  zero drift across five consecutive
  milestones now — M10 + M11 + M12
  + M13.1 + M13.2 + M13.3).
- **Celery-beat task families:** 9
  (unchanged — M13.3 is on-demand
  reads only).
- **Post-LLM scrub layers:** 17
  (unchanged).

## Files touched

### New
- `backend/dealer_ai/services/accounting/snapshot.py`
  (`TrialBalanceRow` +
  `TrialBalanceSnapshot` frozen
  dataclasses + `compute_trial_balance`
  pure verb — single SELECT GROUP BY
  aggregation with `as_of` filter).
- `backend/dealer_ai/tests/test_m133_trial_balance_service.py`
  (12 tests: empty portfolio, no-seed
  fallback, single posting, natural-
  balance signs by type, credit-normal
  types, multi-line aggregation,
  as_of filter, tenant scoping,
  ascending order, reversal-nets-to-
  zero, is_balanced invariant, as_of
  default).
- `backend/dealer_ai/tests/test_m133_trial_balance_endpoint.py`
  (8 tests: empty 200, with postings,
  as_of query, invalid as_of 400,
  auth guard, advisor 403, cross-
  tenant scoping, row shape
  projection).
- `docs/handoffs/SESSION_131_m13_inc3_trial_balance.md`
  (this file).

### Modified
- `backend/dealer_ai/services/accounting/__init__.py`
  — extended public surface with
  `TrialBalanceRow`,
  `TrialBalanceSnapshot`,
  `compute_trial_balance`.
- `backend/dealer_ai/views_accounting.py`
  — added `TrialBalanceQuerySerializer`,
  `_project_trial_balance`, and
  `admin_trial_balance` view function.
- `backend/dealer_ai/urls.py` — one
  new admin path
  (`admin/accounting/trial-balance/`).
- `docs/roadmap/MILESTONE_13_PLANNING.md`
  — §0.a table appended with five
  as-recommended M13.3 confirmations.
- `00-START-NEXT-SESSION.md` — flipped
  to SESSION_132 · M13.4 (closeout).

## What the endpoint does

### `GET /admin/accounting/trial-balance/[?as_of=<ISO8601>]`

Returns the tenant's trial-balance
snapshot at ``as_of`` (default:
current time). Response shape:

```json
{
  "trial_balance": {
    "dealership_id": 1,
    "dealership_slug": "default",
    "as_of": "2026-08-02T10:00:00Z",
    "total_debits": "500.00",
    "total_credits": "500.00",
    "is_balanced": true,
    "rows": [
      {
        "account_code": "122000",
        "account_name": "Recon Work in Process",
        "account_type": "asset",
        "debit_total": "500.00",
        "credit_total": "0.00",
        "natural_balance": "500.00"
      }
    ]
  }
}
```

Behavior:

- Zero-portfolio dealership → 200
  with empty `rows`, all totals
  `0.00`, `is_balanced: true`.
- Cross-tenant scoping is implicit —
  the request's tenant (via
  `get_current_dealership`) is the
  only tenant whose lines get
  aggregated.
- Invalid `as_of` (bad ISO8601) →
  400 (serializer rejection).
- Unauthenticated / non-authorized
  → 401 or 403 (permission-class
  gate).

## Non-goals honored (per §0.a M13.3 decisions)

- ❌ No `TrialBalanceSnapshot`
  entity — pure recompute per §0.a
  M13.3 decision 2. Materialization
  defers to M14+ close workflow.
- ❌ No M9 sale-booking GL post
  (deferred).
- ❌ No M10 F&I chargeback GL
  reversal (deferred).
- ❌ No M12 BHPH payment GL post
  (deferred).
- ❌ No operator UI (§5.f Option C
  — defers to M14).
- ❌ No PDF / spreadsheet export.
- ❌ No period-comparison verbs
  (delta between two `as_of`
  snapshots).
- ❌ No balance-sheet / P&L
  derivatives. Trial balance is
  the raw substrate; higher-level
  reports layer at M14+.
- ❌ No new tenancy carriers.

## Design notes worth remembering

### Frozen dataclass output — immutable + explicit shape

Per §0.a M13.3 decision 1, the
snapshot uses frozen dataclasses.
Callers project into serialized shape
without ever mutating the aggregator's
output. Matches M12.7
`BhphAnalyticsSummary` /
`BucketHistogramRow` posture. The
tuple field on
`TrialBalanceSnapshot.rows` reinforces
immutability — a `list` would let
downstream code accidentally mutate.

### Zero-portfolio semantics is a first-class state

Per §0.a M13.3 decision 5, a fresh
dealership with no postings returns
an empty balanced snapshot, not 404.
Rationale: the M13.1 seed migration
creates 24 GLAccount rows on every
Dealership, so "no journal entries
yet" is a valid intermediate state
between "seeded" and "first posting."
A 404 would surprise operators and
force a defensive check in the UI.

`is_balanced=True` on an empty
snapshot is mathematically correct
(`0 == 0`) and semantically meaningful
(the books are trivially in balance
when there's nothing on them).

### Natural balance signs use fixed-set membership

Per M13.1, `GL_NORMAL_BALANCE_DEBIT_TYPES`
is a frozenset of `{asset, expense}`.
The snapshot computes
`natural_balance = debit - credit`
when the account type is in that set,
and `credit - debit` otherwise.
Positive natural balance means the
account is on its normal side;
negative means it's on the contra
side (rare, e.g. a fully-reversed
asset).

The distinct constant makes the
invariant self-documenting in code
and gives M13.3 tests a fixed hook
to assert against.

### as_of filter uses posted_at, not created_at

Per the M13.1 `JournalEntry.posted_at`
design — that field is the *business-
effective* moment, distinct from
`created_at` (row insertion). An
operator posting a Jul 31 accrual on
Aug 3 sets `posted_at` to Jul 31, so
a Jul 31 trial balance sees the
entry.

Documented in
`test_as_of_filter_excludes_future_postings`.

### Single SELECT with GROUP BY — no N+1

The aggregator uses
`.values(...).annotate(Sum(...))`
so the entire trial balance is one
SQL query. Even at large journal-
line volumes this stays fast; each
row is one COALESCE'd Decimal sum.
No N+1, no per-account fetch loop.

### is_balanced=True is an invariant, not a runtime discovery

Every posting through
`post_journal_entry` is balanced
by the M13.1
`UnbalancedJournalEntryError`
guard. The only way `is_balanced`
can be `False` in production is a
data-integrity break (raw
`JournalEntryLine.objects.create`
bypassing the service verb — a
documented anti-pattern). Locking
the invariant with
`test_is_balanced_true_for_all_valid_postings`
means a future refactor that
introduces such a bypass will
surface here.

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_13_PLANNING.md`
   §5 M13.3 + §0.a M13.3
4. `docs/handoffs/SESSION_130_m13_inc2_m2_cost_reconciliation.md`
5. `docs/roadmap/MILESTONE_12_RETROSPECTIVE.md`
   §6 (lesson 15 informed frozen-
   dataclass posture)
6. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
   §1.3 (schedule concept) + §1.6
   (trial balance + close)
7. `backend/dealer_ai/services/accounting/snapshot.py`
8. `backend/dealer_ai/views_accounting.py::admin_trial_balance`
9. `backend/dealer_ai/urls.py::admin-trial-balance`
