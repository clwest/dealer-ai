---
state: active
date: 2026-08-02
last_session_shipped: SESSION_128
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: shipped
milestone_11_status: shipped
milestone_12_status: shipped
milestone_13_status: planning
next_session: SESSION_129
next_milestone: 13
next_milestone_name: "Accounting reconciliation core"
next_increment: 0
next_increment_name: "M13.0 — Planning refinement + first-decision review"
---

# Next session — SESSION_129 · Milestone 13 · Increment 0 (M13.0 — Planning refinement)

> **SESSION_128 shipped M12.8 —** six
> close-out docs (retrospective +
> capability matrix §7m + roadmap
> flip + planning frontmatter flip +
> session-start refresh + M13
> planning skeleton) + one
> coordinated commit. **Milestone
> 12 — BHPH portfolio operations
> (v1) — SHIPPED.**
>
> **M12 close totals:** five new
> entities across seven
> implementation sessions (BhphNote
> + BhphPayment + BhphPromiseToPay +
> CollectionContact + Repossession)
> + one additive BhphNote extension
> (M12.3 aging columns) + seven new
> `services/` packages + one new
> `/dealer-ai-bhph/` route family
> + two new Celery-beat task
> families (M12.3 08:00 aging
> detector + M12.4 09:00 broken-
> PTP detector) + one new post-LLM
> scrub stage (`collection_language`).
> **Six planning-time §5 decisions
> confirmed as-recommended at M12.1
> open** — streak stands at **41
> planning-time as-recommended
> M5.1 → M12.1** across three
> consecutive milestones now.
>
> **Backend baseline: 4,150 pass,
> 1 skipped, 0 fail** (was 3,895
> at M11 close — +255 tests, 0
> regressions). **Frontend Vitest
> baseline: 78 pass** (was 67 —
> +11 at M12.7). Migrations
> `0037`–`0042`. Tenancy carriers
> 44. DRF admin surface 98.
> Frontend operator routes 17.
> Celery-beat task families 8.
> Permission classes 8
> (unchanged — zero drift).
>
> **Push authorization:** eight
> local commits (M12.1 through
> M12.8) queued for user
> authorization at SESSION_128
> close.
>
> **SESSION_129 opens M13.0 —
> planning refinement + first-
> decision review.** Per
> `MILESTONE_13_PLANNING.md`
> (draft planning skeleton
> written at M12.8 close per
> standing user directive).
> **Six §5 decisions to confirm
> at session open.**

## First thing SESSION_129 must do

### 1. Confirm the six §5 decisions in `MILESTONE_13_PLANNING.md`

The M13 planning skeleton drafted at
M12.8 close carries six load-bearing
decisions. All six recommendations
follow the M12 pattern (41 consecutive
as-recommended planning-time
resolutions).

Recommendations (drawn from
`MILESTONE_13_PLANNING.md` §4):

1. **§5.a — Milestone slice
   selection.** Option A —
   substrate (GL account +
   journal entry models) + Q1
   (M2 cost reconciliation) as
   first slice. **THIS IS THE
   LOAD-BEARING DECISION.**
   Per IMPLEMENTATION_ROADMAP
   §Milestone 13, a monolithic
   accounting milestone violates
   Project Rule 4 (Scope
   Discipline) — multiple
   slices layer onto M14+ or
   into ongoing operational
   milestones.
2. **§5.b — GL chart-of-accounts
   source.** Option B —
   platform-shipped default
   chart (industry-standard
   auto-dealer COA); per-dealer
   overrides at M14+.
3. **§5.c — Journal entry
   immutability.** Option A —
   immutable + reversing
   entries.
4. **§5.d — GL-posting trigger
   shape.** Option C — hybrid
   (sync for M9 sale-booking;
   detector for M2 cost accrual
   + M12 payment posting).
5. **§5.e — Substrate location.**
   Option A — new `services/
   accounting/` package inside
   `dealer_ai/`.
6. **§5.f — Operator UI scope.**
   Option C — no UI at M13
   (backend-only); UI defers
   to M14.

**Do not write M13.1 code until
every `[NEEDS-DECISION-BEFORE-M13.N]`
item is resolved.** Any user override
→ amend `MILESTONE_13_PLANNING.md`
§0.a narrowly at session top (per
M5-M12 §0.a precedent) before
implementation.

### 2. Verify starting state

- `git status` — clean (M12.8
  commit landed at SESSION_128
  close; batch push authorized +
  executed).
- `git log --oneline -3` — top
  should be `Milestone 12 shipped
  — BHPH portfolio operations
  (SESSION_121-128)` or similar.
- `git log origin/main..HEAD
  --oneline` — **empty** (all M12
  commits pushed).
- `python3 manage.py test dealer_ai`
  → **4,150 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **78 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `npx tsc --noEmit` + `npx vite
  build` both clean.
- `redis-cli ping` → `PONG`.

## What M13.1 delivers (assuming §5.a Option A confirmed)

Per `MILESTONE_13_PLANNING.md` §5
M13.1:

- **New `services/accounting/`
  package.**
- **New `GLAccount` model** —
  chart-of-accounts entity +
  fixed default COA fixture per
  §5.b Option A (auto-dealer
  industry-standard chart).
- **New `JournalEntry` +
  `JournalEntryLine` models** —
  immutable per §5.c Option A.
  Journal entries are the atomic
  unit of GL posting; lines are
  the debit/credit rows.
- **Three verbs:**
  - `post_journal_entry(dealership,
    lines, description)` —
    atomic write. Refuses
    unbalanced entries (debits
    != credits).
  - `reverse_journal_entry(pk,
    reason)` — atomic write of
    the reversal entry with
    inverted debits/credits.
  - `get_journal_entry(pk,
    dealership)` — tenant-
    scoped read.
- **Domain errors:**
  - `UnbalancedJournalEntryError`
    (400).
  - `CrossTenantJournalEntryError`
    (404).
  - `CrossTenantGLAccountError`
    (404).
  - `ImmutableJournalEntryError`
    (409) — attempted edit
    after post.
- **Endpoints (three):**
  - `POST /admin/accounting/journal-entries/`
    — post.
  - `POST /admin/accounting/journal-entries/<pk>/reverse/`
    — reverse.
  - `GET /admin/accounting/journal-entries/<pk>/`
    — retrieve.
- **Migration `0043`.**
- **Tenancy carriers 44 → 47**
  (GLAccount + JournalEntry +
  JournalEntryLine).
- **~40 focused tests** across
  model / service / endpoint
  files (larger — GL substrate
  is the load-bearing shared
  layer for M13.2+).
- **Baseline target 4,150 →
  ~4,190.**

### Non-goals for M13.1

- ❌ No M2 cost reconciliation
  (M13.2).
- ❌ No trial-balance snapshot
  (M13.3).
- ❌ No M9 sale-booking flow
  (M13+ deferred slice).
- ❌ No M10 F&I chargeback
  reversal (deferred slice).
- ❌ No M12 BHPH payment
  reconciliation (deferred
  slice).
- ❌ No operator UI (M14).
- ❌ No CSV export /
  spreadsheet integration.

## What SESSION_129 should do

### Recommended step sequence

1. **Confirm the six §5 decisions
   with the user** (§1 above).

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_13_PLANNING.md`
     §1 + §2 + §5 (all).
   - `docs/handoffs/SESSION_128_m12_close.md`
     (previous session).
   - `docs/roadmap/MILESTONE_12_RETROSPECTIVE.md`
     §6 (nineteen lessons carry
     into M13).
   - `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
     §"Accounting is the
     reconciliation layer that
     validates every operational
     event" + §"When the DMS is
     right, accounting is right"
     + pain #1.
   - `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
     §Milestone 13 (incremental-
     structure note is load-
     bearing).
   - `backend/dealer_ai/services/f_and_i/`
     (M10 service-package
     pattern to mirror).
   - `backend/dealer_ai/services/bhph_notes/`
     (M12.1 service-package
     pattern to mirror).

3. **Verify starting state** (§2
   above).

4. **Draft (in order — assuming
   §5.a Option A confirmed):**
   - `GLAccount` + `JournalEntry`
     + `JournalEntryLine` models
     + tenancy carrier extension
     (44 → 47).
   - Default COA fixture.
   - Migration `0043`.
   - `services/accounting/`
     package with three verbs.
   - `views_accounting.py` +
     endpoints.
   - URL routes.
   - ~40 focused tests.

5. **Full-suite verification.**
   Target 4,150 → ~4,190.

6. **Ship handoff at
   `docs/handoffs/SESSION_129_m13_inc1_gl_substrate.md`.**

7. **Overwrite
   `00-START-NEXT-SESSION.md`** with
   M13.2 priority (M2 cost
   reconciliation).

## Explicit non-goals for SESSION_129

- ❌ Do NOT ship M13.2-M13.4 scope.
- ❌ Do NOT modify M1-M12 business
  logic.
- ❌ Do NOT force-push or amend
  any M11/M12 commits.

## NEXT TASK

Start SESSION_129 with (a)
confirming the six §5 decisions
with the user (all recommendations
per M12 pattern), (b) the read-
first list, (c) starting-state
verification, then (d) `GLAccount`
+ `JournalEntry` + `JournalEntryLine`
models + tenancy carrier extension
(44 → 47) + default COA fixture +
migration + `services/accounting/`
package with three verbs +
endpoints + ~40 tests. Target
baseline 4,150 → ~4,190. Ship the
M13.1 handoff.

Backend baseline at SESSION_129
close: **~4,190 pass**. Frontend
baseline: unchanged (no frontend
at M13.1).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 13
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_13_PLANNING.md`
6. `docs/roadmap/MILESTONE_12_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_128_m12_close.md`
   (this session's close)
8. `docs/handoffs/SESSION_127_m12_inc7_analytics_ui.md`
9. `docs/CAPABILITY_MATRIX.md` §7m
10. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
11. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_128 — M12 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0042`. Test baseline:
  **4,150 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 78 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **8
  scheduled task families
  registered** (M7.2-M7.5 +
  M11.4 06:00 + M11.5 07:00 +
  M12.3 08:00 + M12.4 09:00).
- **Milestones shipped:** M1 →
  **M12** (SESSION_128 close).
  M13 planning drafted.
- **DRF admin surface:** **98**
  endpoints.
- **Frontend operator routes:**
  **17** (15 pre-M12.7 + 2 M12.7
  `/dealer-ai-bhph/` routes).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages + seven M12
  packages
  (`bhph_notes` /
  `bhph_payments` /
  `bhph_delinquency` /
  `bhph_promises` /
  `collection_contacts` /
  `repossessions` /
  `bhph_analytics`).
- **Tenancy carriers:** **44**
  (39 at M11 close → 44 at M12
  close via M12.1 + M12.2 +
  M12.4 + M12.5 + M12.6).
- **Permission classes:** **8**
  (unchanged — every M12
  endpoint reused M4
  `IsSalesManagerOrOwnerAtActiveDealership`;
  zero drift).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (16 → 17 via M12.5
  `collection_language`).
- **Deterministic rules:**
  unchanged.
- **BHPH portfolio math:** three
  M12 pure-verb families in
  `services/payment_engine.py`
  (M12.1) + `services/
  bhph_payments/apply.py`
  (M12.2) + `services/
  bhph_delinquency/compute.py`
  (M12.3) + `services/
  bhph_analytics/compute.py`
  (M12.7).
- **Milestone 13 next:** M13.0
  planning refinement +
  first-decision review. Verify
  six §5 decisions at session
  open — §5.a is the load-
  bearing scope-slice decision.
  M13.1 substrate + Q1 slice
  target: ~40 tests, baseline
  4,150 → ~4,190.
