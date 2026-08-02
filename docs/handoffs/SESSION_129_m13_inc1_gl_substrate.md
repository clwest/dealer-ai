---
title: "SESSION_129 handoff — Milestone 13 · Increment 1 (M13.1 — GL substrate: chart of accounts + immutable journal entries)"
status: historical
type: handoff
date: 2026-08-02
session: 129
milestone: 13
milestone_status: in_progress
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_129 — Milestone 13 · Increment 1 (M13.1 — GL substrate)

## What shipped

Milestone 13 opens. Accounting substrate
per `MILESTONE_13_PLANNING.md` §7 M13.1
and §5.a Option A / §5.b Option A / §5.c
Option A / §5.e Option A. Three new
entities (`GLAccount` + `JournalEntry` +
`JournalEntryLine`) + platform default
COA fixture + three service verbs + three
admin endpoints.

**Six planning-time §5 decisions confirmed
as-recommended at M13.0 open** — streak
extends to **47 planning-time as-
recommended M5.1 → M13.0**. First §5
resolution against an accounting-
reconciliation surface (M12
retrospective §7 flagged this milestone
as the pattern test).

- §5.a: Option A (substrate + Q1 M2 cost
  reconciliation as first slice; M13.2 =
  M2 reconciliation, M13.3 = trial
  balance, M13.4 = closeout).
- §5.b: Option A (platform-shipped
  default COA per ACCOUNTING §1.1 NADA /
  dealer-standard chart; per-dealer
  overrides defer to M14+).
- §5.c: Option A (immutable journal
  entries + reversing entries — every
  correction is a new posting).
- §5.d: Option C (hybrid GL-posting
  trigger — sync for M9 sale-booking,
  detector for M2 cost accrual + M12
  BHPH payment posting).
- §5.e: Option A (new `services/
  accounting/` package inside
  `dealer_ai/`).
- §5.f: Option C (no operator UI at
  M13; UI defers to M14).

## By the numbers

- **Backend baseline: 4,194 pass, 1
  skipped, 0 fail** (was 4,150 at M12
  close — **+44 tests, 0 regressions**).
- **Frontend Vitest baseline: 78 pass**
  (unchanged — no frontend at M13.1
  per §5.f Option C).
- **Migrations `0043`**
  (`0043_m131_accounting_substrate`).
  Schema + RunPython seed step in a
  single migration (self-contained).
- **Tenancy carriers: 44 → 47**
  (`GLAccount` + `JournalEntry` +
  `JournalEntryLine` registered in
  `services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`).
- **DRF admin surface: 98 → 101**
  (`admin-journal-entry-create` +
  `admin-journal-entry-reverse` +
  `admin-journal-entry-retrieve`).
- **Frontend operator routes:** 17
  (unchanged — no UI per §5.f).
- **Permission classes: 8** (unchanged
  — reused M4
  `IsSalesManagerOrOwnerAtActiveDealership`;
  zero drift, matching M11 + M12
  posture across three consecutive
  milestones).
- **Post-LLM scrub layers:** 17
  (unchanged).
- **Celery-beat task families:** 8
  (unchanged — GL-posting detectors
  land at M13.2 per §5.d Option C).
- **Default COA:** 24 accounts per
  Dealership seeded by migration
  RunPython step.

## Files touched

### New
- `backend/dealer_ai/services/accounting/__init__.py`
- `backend/dealer_ai/services/accounting/default_coa.py`
  (`DEFAULT_COA` fixture + idempotent
  `seed_default_coa(dealership)` verb).
- `backend/dealer_ai/services/accounting/journal.py`
  (three verbs + six domain-error
  classes + `JournalLineInput`
  dataclass).
- `backend/dealer_ai/views_accounting.py`
  (three endpoints + serializers +
  projection helpers).
- `backend/dealer_ai/migrations/0043_m131_accounting_substrate.py`
  (three CreateModel + unique
  constraint + RunPython seed step).
- `backend/dealer_ai/tests/test_m131_gl_account_model.py`
  (5 tests).
- `backend/dealer_ai/tests/test_m131_journal_entry_model.py`
  (8 tests).
- `backend/dealer_ai/tests/test_m131_accounting_service.py`
  (19 tests — 8 post, 5 reverse, 3
  get, 3 seed COA).
- `backend/dealer_ai/tests/test_m131_accounting_endpoint.py`
  (12 tests — 6 create, 4 reverse,
  2 retrieve).
- `docs/handoffs/SESSION_129_m13_inc1_gl_substrate.md`
  (this file).

### Modified
- `backend/dealer_ai/models.py` — added
  `GLAccount` + `JournalEntry` +
  `JournalEntryLine` models + five
  `GL_ACCOUNT_TYPE_*` vocab constants +
  `GL_ACCOUNT_TYPE_CHOICES` +
  `GL_NORMAL_BALANCE_DEBIT_TYPES` /
  `_CREDIT_TYPES` frozensets at end
  (matches M12.6 layout).
- `backend/dealer_ai/services/tenancy.py`
  — extended `_TENANT_CARRIER_MODEL_NAMES`
  44 → 47.
- `backend/dealer_ai/urls.py` — three
  new admin paths under `/admin/
  accounting/journal-entries/` +
  `views_accounting` import.
- `docs/roadmap/MILESTONE_13_PLANNING.md`
  — §0.a table populated with the six
  as-recommended M13.0 confirmations.
- `00-START-NEXT-SESSION.md` — flipped
  to SESSION_130 · M13.2 priority.

## What the endpoints do

### `POST /admin/accounting/journal-entries/`

Body: `description` (str, max 500),
`lines` (list of
`{account_id, debit?, credit?, memo?}`),
optional `posted_at` (datetime — defaults
to `timezone.now()`).

Behavior:
- Empty `lines` → 400
  (`EmptyJournalEntryError`).
- Line with both debit + credit set,
  both zero, or negative amount → 400
  (`InvalidJournalLineError`).
- `account_id` missing in tenant or
  belonging to another tenant → 404
  (`CrossTenantGLAccountError`;
  fail-closed).
- Unbalanced entry (`sum(debits) !=
  sum(credits)`) → 400
  (`UnbalancedJournalEntryError`).

Response: `{ "journal_entry": {...} }`
with `id`, `description`, `posted_at`,
`posted_by_user_id`, `reverses_id`,
`reason`, `lines: [...]`.

### `POST /admin/accounting/journal-entries/<pk>/reverse/`

Body: `reason` (str, required, non-blank),
optional `posted_at`.

Behavior:
- Missing / cross-tenant `pk` → 404
  (fail-closed).
- Blank / whitespace-only `reason` → 400
  (DRF serializer belt) or 409
  (service `ImmutableJournalEntryError`
  suspenders — currently unreachable
  via endpoint, exercised in service
  tests).

Response: `{ "journal_entry": {...} }`
with the newly-created reversal
(debits/credits swapped from original;
`reverses_id` populated).

### `GET /admin/accounting/journal-entries/<pk>/`

Behavior:
- Missing / cross-tenant `pk` → 404
  (fail-closed).

Response: `{ "journal_entry": {...} }`
identical shape to POST create response.

## Default COA composition

Twenty-four accounts organized per
ACCOUNTING §1.1 NADA-style chart:

- **1-series (assets, 8 accounts):**
  100000 Cash on Hand, 110000 Bank —
  Operating, 120000 Contracts in
  Transit, 121000 Used Vehicle
  Inventory, 122000 Recon WIP,
  123000 BHPH Notes Receivable,
  130000 A/R — Reserve Receivable,
  131000 A/R — Warranty Commission.
- **2-series (liabilities, 4):**
  200000 A/P — Trade, 210000 Floor
  Plan Payable, 220000 Sales Tax
  Payable, 230000 Customer Deposits.
- **3-series (equity, 2):** 300000
  Owner Equity, 310000 Retained
  Earnings.
- **4-series (revenue, 4):** 400000
  Vehicle Sales — Retail, 410000
  Vehicle Sales — Wholesale, 420000
  F&I Reserve Income, 430000 BHPH
  Interest Income.
- **5-series (cost of sales, 2):**
  500000 Cost of Vehicle Sales,
  510000 Recon Expense.
- **6/7/8/9-series (expense, 4):**
  600000 Advertising, 700000
  Salaries — Sales, 800000 Rent,
  900000 Interest Expense — Floor
  Plan.

The set covers every posting target
M13.2+ needs (M2 cost accrual → 122000
+ 121000; M9 sale booking → 400000 +
121000 + 500000; M10 F&I reserve →
420000 + 130000; M12 BHPH payment →
430000 + 123000 + 110000) without
over-modeling. Additional accounts land
as follow-on milestones surface
operator evidence per M11 §6 lesson 18
fixed-vocab posture.

## Non-goals honored (per §5.a Option A)

- ❌ No M2 cost reconciliation
  detector (M13.2).
- ❌ No trial-balance snapshot verb
  (M13.3).
- ❌ No M9 sale-booking GL post
  (M13+ deferred slice per §5.d
  Option C hybrid — sync GL post
  wires into M9.1 `record_sale`
  when that slice ships).
- ❌ No M10 F&I chargeback GL
  reversal (deferred).
- ❌ No M12 BHPH payment GL post
  (deferred).
- ❌ No operator UI (§5.f Option C
  — defers to M14).
- ❌ No CSV export / spreadsheet
  integration.
- ❌ No per-dealer COA overrides
  (§5.b Option A — defers to M14+).
- ❌ No `pre_save` signal wiring
  for auto-seeding new dealerships
  (explicit `seed_default_coa`
  call defers to M14+ operator
  UI).

## Design notes worth remembering

### Immutability = no update verb, only reversal

The `services.accounting` package
deliberately has no `update_journal_entry`
verb. This is load-bearing: per §5.c
Option A a journal entry is immutable
once posted. Every correction goes
through `reverse_journal_entry`, which
creates a new row with `reverses` FK
populated. The original row is never
mutated. The absence of an update
verb is the enforcement mechanism —
future maintainers should not add one.

### Reversal of reversal is legal

Double-reversing restores the original
economic effect. Both reversals stay
in the audit trail. Locked by
`test_reversal_of_reversal_allowed`.
This preserves the "operator changed
their mind" workflow without allowing
edits.

### JournalLineInput is a dataclass, not a dict

Passing lines as `list[JournalLineInput]`
(frozen dataclass with typed fields)
rather than `list[dict]` catches
schema mismatches at import time and
gives the endpoint layer a clean
serializer → dataclass mapping. The
verb signature stays stable across
future line-field additions (memo
now, GL-department suffix in M14+
per ACCOUNTING §1.2).

### Belt (model `clean()`) + suspenders (service)

Same posture as every M4-M12 entity:

- `JournalEntry.clean()` enforces
  `reverses.dealership == dealership`.
- `JournalEntryLine.clean()` enforces
  `entry.dealership == dealership`
  AND `account.dealership ==
  dealership`.
- `services.accounting.post_journal_entry`
  raises `CrossTenantGLAccountError`
  (→ 404) and the balance /
  malformed-line errors (→ 400)
  before any DB write.
- `services.accounting.reverse_journal_entry`
  raises `CrossTenantJournalEntryError`
  (→ 404) and `ImmutableJournalEntryError`
  (→ 409) before any DB write.

The service is the primary
enforcement layer; the model
`clean()` is the safety net for
callers that bypass the verb (per
M11-M12 pattern).

### Balance invariant enforced at service, not DB

`sum(debits) == sum(credits)` is
checked in `_validate_lines` before
any INSERT. The DB does not enforce
it — a raw
`JournalEntry.objects.create` +
naked `JournalEntryLine.objects.create`
sequence can produce an unbalanced
entry. Production paths must go
through `post_journal_entry`. This
matches M12.2's split of pure
`allocate_payment` (validated
compute) from write `record_payment`
(persisted result).

### Migration RunPython is self-contained

The `_seed_default_coa` step imports
`DEFAULT_COA` from
`services.accounting.default_coa` for
the source-of-truth tuple, but writes
rows via
`apps.get_model("dealer_ai", "GLAccount")`
— the historical model. This means
the migration stays valid across
future model changes (renames,
column additions, etc.) without
needing an amendment.

### `seed_default_coa` is idempotent

`get_or_create` on `(dealership, code)`
means re-running the seeder against
a partially-seeded tenant fills in
missing rows without disturbing
existing ones. Locked by
`test_seed_default_coa_idempotent`.
Safe to call from a future
management command / M14 operator
UI without worrying about the
existing-vs-new-tenant branching.

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_13_PLANNING.md`
   §1 + §2 + §5 + §7 M13.1
4. `docs/handoffs/SESSION_128_m12_close.md`
5. `docs/roadmap/MILESTONE_12_RETROSPECTIVE.md`
   §6 (nineteen lessons —
   informed M13.1 posture)
6. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
   §1.1 (COA composition) + §1.3
   (schedule concept) + §1.6
   (immutability + close discipline)
7. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 13
8. `backend/dealer_ai/models.py::GLAccount`
   / `JournalEntry` / `JournalEntryLine`
9. `backend/dealer_ai/services/accounting/`
10. `backend/dealer_ai/views_accounting.py`
11. `backend/dealer_ai/urls.py::admin-journal-entry-*`
