---
title: "SESSION_130 handoff — Milestone 13 · Increment 2 (M13.2 — M2 cost reconciliation detector)"
status: historical
type: handoff
date: 2026-08-02
session: 130
milestone: 13
milestone_status: in_progress
increment: 2
increment_status: shipped
commit: TBD
---

# SESSION_130 — Milestone 13 · Increment 2 (M13.2 — M2 cost reconciliation)

## What shipped

Second M13 slice per
`MILESTONE_13_PLANNING.md` §5 M13.2
and §5.a Option A / §5.d Option C
(hybrid detector for M2 cost accrual).
Ninth Celery-beat task family at 10:00
project-time daily. `VehicleCost.posted_at`
additive extension. New
`services/accounting/vehicle_cost.py`
verbs. GL entries for every unposted,
non-estimate VehicleCost row auto-post
via the M13.1 substrate.

**Six implementation-time §0.a M13.2
micro-decisions confirmed as-recommended
at SESSION_130 open.** Per M10/M11/M12
precedent these do not count against
the planning-time streak (which stands
at 47 M5.1 → M13.0).

- M13.2 · 1: `VehicleCost.posted_at`
  denormalize-at-write (M12 §6 lesson
  4 posture).
- M13.2 · 2: uniform mapping DR
  `122000` Recon WIP / CR `200000`
  A/P Trade. Category-group-aware
  mapping defers.
- M13.2 · 3: 10:00 project-time
  detector slot (ninth family).
- M13.2 · 4: estimates skipped.
- M13.2 · 5: negative-amount rows
  post with swapped sides.
- M13.2 · 6: `posted_at__isnull=True
  AND is_estimate=False` filter gives
  cross-run idempotency; per-row
  `@transaction.atomic` around GL
  post + `posted_at` update (M12 §6
  lesson 11 sibling-crossing).

## By the numbers

- **Backend baseline: 4,220 pass, 1
  skipped, 0 fail** (was 4,194 at
  M13.1 close — **+26 tests, 0
  regressions**).
- **Frontend Vitest baseline: 78 pass**
  (unchanged — no frontend at M13.2
  per M13 §5.f Option C).
- **Migration `0044`**
  (`0044_m132_vehicle_cost_posted_at`
  — additive nullable DateTimeField).
- **Tenancy carriers: 47** (unchanged
  — additive M2 extension only).
- **DRF admin surface: 101**
  (unchanged — detector runs via
  Celery, no new endpoint).
- **Frontend operator routes:** 17
  (unchanged).
- **Permission classes: 8** (unchanged
  — no new endpoint to gate).
- **Celery-beat task families: 8 →
  9** (`accounting-vehicle-cost-post-
  daily-10-00` registered in
  `dealer_kit/settings.py`
  `CELERY_BEAT_SCHEDULE`).
- **Post-LLM scrub layers:** 17
  (unchanged).
- **`Vehicle.is_available`:**
  unchanged.

## Files touched

### New
- `backend/dealer_ai/services/accounting/vehicle_cost.py`
  (three verbs: `detect_unposted_costs` +
  `post_vehicle_cost_journal` +
  `post_all_unposted_costs_for_dealership`
  + `MissingDefaultAccountError` +
  uniform-mapping constants).
- `backend/dealer_ai/services/accounting/tasks.py`
  (`post_vehicle_cost_journals_for_dealership`
  + `post_vehicle_cost_journals_for_all_tenants`).
- `backend/dealer_ai/migrations/0044_m132_vehicle_cost_posted_at.py`
  (single AddField operation —
  additive nullable column).
- `backend/dealer_ai/tests/test_m132_vehicle_cost_service.py`
  (19 tests: detector query,
  post_vehicle_cost_journal happy /
  negative / atomic / cross-tenant /
  explicit posted_at / memo,
  orchestrator idempotent / mixed /
  scoped / estimate-flip,
  MissingDefaultAccount, posted_at
  field defaults).
- `backend/dealer_ai/tests/test_m132_vehicle_cost_tasks.py`
  (7 tests: task-name constants,
  direct call, orchestrator dispatch,
  beat-schedule registration).
- `docs/handoffs/SESSION_130_m13_inc2_m2_cost_reconciliation.md`
  (this file).

### Modified
- `backend/dealer_ai/models.py` —
  added `VehicleCost.posted_at`
  nullable DateTimeField at end of
  the model definition. All existing
  behavior unchanged.
- `backend/dealer_ai/services/accounting/__init__.py`
  — extended public surface with
  vehicle_cost exports.
- `backend/dealer_kit/settings.py`
  — added
  `accounting-vehicle-cost-post-daily-
  10-00` entry to
  `CELERY_BEAT_SCHEDULE` (ninth
  family).
- `docs/roadmap/MILESTONE_13_PLANNING.md`
  — §0.a table appended with six
  as-recommended M13.2 confirmations.
- `00-START-NEXT-SESSION.md` — flipped
  to SESSION_131 · M13.3 priority
  (trial-balance snapshot).

## What the detector does

At 10:00 project-time daily,
`post_vehicle_cost_journals_for_all_tenants`
enqueues one per-tenant task via
`.delay()` for every :class:`Dealership`
row. Each per-tenant task iterates the
unposted, non-estimate VehicleCost rows
for that dealership and posts them
through the M13.1 GL substrate.

**Per-row atomic posting:**

1. `@transaction.atomic` around GL
   post + `posted_at` denormalization
   (M12 §6 lesson 11 sibling-service
   crossing pattern).
2. Positive `amount` → DR `122000`
   Recon WIP + CR `200000` A/P Trade.
3. Negative `amount` (correction row)
   → DR A/P Trade + CR Recon WIP with
   `abs(amount)` on both lines.
4. On success: `posted_at` populated
   with the detector's `now`.
5. On failure: transaction rolls back;
   row stays unposted; next run picks
   it up.

**Cross-run idempotency:** the
`posted_at__isnull=True AND
is_estimate=False` filter naturally
skips already-posted rows. Re-runs on
the same day produce zero writes.

**Estimate handling:** rows with
`is_estimate=True` are excluded. When
an estimate flips to committed
(`is_estimate=False`), its still-NULL
`posted_at` triggers a fresh post on
the next detector run. Locked by
`test_estimate_flip_to_committed_picks_up_on_next_run`.

## Non-goals honored (per §5.a Option A + M13.1 non-goals)

- ❌ No trial-balance snapshot verbs
  (M13.3).
- ❌ No M9 sale-booking GL post
  (deferred).
- ❌ No M10 F&I chargeback GL
  reversal (deferred).
- ❌ No M12 BHPH payment GL post
  (deferred).
- ❌ No operator UI (§5.f Option C
  — defers to M14).
- ❌ No category-group-aware GL
  mapping (uniform mapping per §0.a
  M13.2 decision 2; defers until
  operator evidence surfaces need).
- ❌ No per-vehicle P&L reporting.
- ❌ No admin endpoint for manual
  "post now" trigger (detector is
  the sole entry point at M13.2;
  addendum could land later
  narrowly like M12.7).
- ❌ No `VehicleCost` update /
  delete paths (M2 correction
  pattern is to post a new
  reversing row per §1.6
  VehicleCost design note).

## Design notes worth remembering

### Zero-amount rows are rejected

An `amount == Decimal("0.00")`
VehicleCost row fails
`InvalidJournalLineError` (400) inside
the atomic block — the M13.1
`_validate_lines` guard rejects lines
with both debit and credit at zero.
The transaction rolls back, `posted_at`
stays NULL, and the row is skipped on
the next run too (it's the same
condition). Documented in
`test_zero_amount_still_posts_balanced`.

This is a **feature, not a bug** —
zero-amount rows are noise. If a
future operational path legitimately
needs to represent "posted, zero
effect," it should use `is_estimate=True`
(explicit skip) rather than an
attempted zero-line entry.

### Uniform mapping is the M13.2 posture

Every VehicleCost posts to the same
two GLAccounts regardless of category.
This is deliberate: category-group-
aware mapping (flooring → floor plan
accounts, admin → rent / ad, etc.) is
easy to add later once operator
evidence names the need. Adding it
prematurely burns modeling capacity
against uncertain requirements.

Future increment would branch on
`VehicleCost.category` (or
`FLOORING_CATEGORIES` /
`ADMIN_CATEGORIES` group membership)
via a lookup table exposed as
`GLAccountMappingRule` or similar.
The `services/accounting/vehicle_cost.py`
verb signature stays stable — only
the internal debit/credit selection
changes.

### MissingDefaultAccountError is a broken-invariant signal

If the required default COA account
(`122000` or `200000`) is missing for
a tenant, that means either the M13.1
seeder failed to run OR an operator
has hidden the account via
`is_active=False`. The detector
raises `MissingDefaultAccountError`
per-row; the orchestrator catches +
logs + counts as `failed_count` but
does not halt (later rows in the
same batch can still succeed if
their accounts are fine).

This surfaces the operational
problem to operators without
silently degrading. When the operator
reactivates the account, the next
detector run picks up the previously-
failed rows because their
`posted_at` is still NULL.

### Belt (M13.1 service) + suspenders (M13.2 verb)

Cross-tenant VehicleCost is caught
both at the M13.2 entry guard (raises
`CrossTenantGLAccountError` before
any GL post) AND downstream at the
M13.1 `_validate_lines` guard (which
would catch the same cross-tenant
account reference if the M13.2 guard
were bypassed). Both layers preserve
the fail-closed 404 posture.

### Beat schedule vs code registration

The M13.2 slot is registered in the
code-first
`CELERY_BEAT_SCHEDULE` dict. In
production the DB-backed scheduler
(`django_celery_beat.schedulers:
DatabaseScheduler`) allows operator
overrides via Django admin without a
code deploy. The code-first entry is
the bootstrap baseline. Locked by
`test_10_00_slot_registered`.

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_13_PLANNING.md`
   §5 M13.2 + §0.a M13.2
4. `docs/handoffs/SESSION_129_m13_inc1_gl_substrate.md`
5. `docs/roadmap/MILESTONE_12_RETROSPECTIVE.md`
   §6 (lessons 4 + 11 informed
   M13.2 posture)
6. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
   §2.6 (vendor invoices) + §2.7
   (recon expenses) + pain #1
7. `backend/dealer_ai/models.py::VehicleCost.posted_at`
8. `backend/dealer_ai/services/accounting/vehicle_cost.py`
9. `backend/dealer_ai/services/accounting/tasks.py`
10. `backend/dealer_kit/settings.py::CELERY_BEAT_SCHEDULE`
    (`accounting-vehicle-cost-post-
    daily-10-00`)
