---
state: active
date: 2026-08-02
last_session_shipped: SESSION_129
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
milestone_13_status: in_progress
next_session: SESSION_130
next_milestone: 13
next_milestone_name: "Accounting reconciliation core"
next_increment: 2
next_increment_name: "M13.2 — M2 cost reconciliation detector"
---

# Next session — SESSION_130 · Milestone 13 · Increment 2 (M13.2 — M2 cost reconciliation)

> **SESSION_129 shipped M13.1 —** GL
> substrate (chart of accounts +
> immutable journal entries + three
> service verbs + three admin
> endpoints + 24-account platform
> default COA). **Six §5 decisions
> confirmed as-recommended at M13.0
> open** — streak extends to **47
> planning-time as-recommended M5.1
> → M13.0** (four consecutive
> milestones now: M10 + M11 + M12
> + M13).
>
> **Backend baseline: 4,194 pass, 1
> skipped, 0 fail** (was 4,150 at
> M12 close — **+44 tests, 0
> regressions**). **Frontend Vitest
> baseline: 78 pass** (unchanged —
> no frontend at M13.1 per §5.f
> Option C). Migration `0043`.
> Tenancy carriers 47. DRF admin
> surface 101. Frontend operator
> routes 17. Celery-beat task
> families 8. Permission classes 8
> (unchanged — every M13.1
> endpoint reused
> `IsSalesManagerOrOwnerAtActiveDealership`;
> zero drift across four
> consecutive milestones now).
>
> **Push authorization:** one local
> M13.1 commit queued for user
> authorization at SESSION_129
> close.

## First thing SESSION_130 must do

### 1. Surface any implementation-time micro-decisions

Per M10/M11/M12 §0.a precedent —
M13.2 planning is expected to surface
3–5 implementation-time micro-decisions
at session open. Draft recommendations,
present with user, record confirmations
in `MILESTONE_13_PLANNING.md` §0.a
narrowly before touching code.

Anticipated micro-decisions for M13.2:

1. **`VehicleCost.posted_at`
   population posture.** Denormalize
   at write (detector sets
   `posted_at` on successful GL
   post) vs recompute on read
   (detector queries `posted_at IS
   NULL` per M12 §6 lesson 4
   denormalize-at-write pattern).
   **Recommendation:** denormalize
   at write — matches M12.3 aging-
   detector posture.
2. **Which GLAccounts M13.2 posts
   against.** Recommendation: 122000
   Recon WIP (debit) + 200000 A/P
   Trade (credit) for standard M2
   VehicleCost rows. Category-
   specific overrides defer to
   later increments.
3. **Detector scheduling slot.**
   10:00 project-time daily per
   §7 M13.2 draft + M11-M12
   non-overlapping-window pattern
   (M12.3 08:00, M12.4 09:00,
   next slot 10:00). Confirm at
   open.
4. **Idempotency posture.** Same
   as M12.3 / M12.4 — bulk-update
   or write-if-changed so re-runs
   on the same day produce
   identical output.

### 2. Verify starting state

- `git status` — clean (M13.1
  commit landed at SESSION_129
  close; batch push authorized +
  executed).
- `git log --oneline -3` — top
  should reference SESSION_129 /
  M13.1.
- `git log origin/main..HEAD
  --oneline` — **empty** (all M13.1
  commits pushed).
- `python3 manage.py test dealer_ai`
  → **4,194 pass, 1 skipped, 0
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

## What M13.2 delivers

Per `MILESTONE_13_PLANNING.md` §5
M13.2:

- **New Celery-beat task** at 10:00
  project-time daily (ninth task
  family — extends the 02:00-09:00
  slot pattern).
- **`VehicleCost.posted_at`
  denormalized column** (additive
  extension — new nullable
  DateTimeField).
- **Migration `0044`** for the
  column addition.
- **Detector scans** unposted
  `VehicleCost` rows (`posted_at IS
  NULL`) + posts corresponding
  journal entries via the M13.1
  `post_journal_entry` verb +
  denormalizes `posted_at` on
  successful post.
- **New verbs in `services/
  accounting/`:**
  - `detect_unposted_costs(dealership,
    now=None)` — pure query for
    unposted rows.
  - `post_vehicle_cost_journal(vehicle_cost,
    dealership)` — atomic sibling-
    service call (per M12 §6
    lesson 11 atomic-sibling-
    crossing pattern).
  - Celery-beat task orchestrator
    per M7.2 / M11.4 / M11.5 /
    M12.3 / M12.4 pattern (passes
    `dealership_id` kwarg so
    JobRunLog rows carry tenant
    context).
- **~25 focused tests** across
  service / detector / migration
  files.
- **Baseline target 4,194 →
  ~4,220.**
- **Celery-beat task families:**
  8 → 9.
- **Tenancy carriers:** unchanged
  (no new entity — additive M2
  extension only).

### Non-goals for M13.2

- ❌ No trial-balance snapshot
  (M13.3).
- ❌ No M9 sale-booking GL post
  (M13+ deferred slice).
- ❌ No M10 F&I chargeback GL
  reversal (deferred).
- ❌ No M12 BHPH payment GL post
  (deferred).
- ❌ No operator UI (§5.f Option
  C — defers to M14).
- ❌ No new GLAccounts (default
  COA covers M13.2 needs).
- ❌ No per-vehicle P&L
  reporting.

## What SESSION_130 should do

### Recommended step sequence

1. **Surface M13.2 micro-decisions
   with the user** (§1 above) and
   amend `MILESTONE_13_PLANNING.md`
   §0.a per M5-M12 precedent.

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_13_PLANNING.md`
     §5 M13.2.
   - `docs/handoffs/SESSION_129_m13_inc1_gl_substrate.md`
     (previous session).
   - `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
     §2.6 (vendor invoices) +
     §2.7 (recon expenses) +
     pain #1 (three-way
     reconciliation).
   - `backend/dealer_ai/models.py::VehicleCost`
     (M2 target entity).
   - `backend/dealer_ai/services/accounting/`
     (M13.1 verbs to consume).
   - `backend/dealer_ai/services/bhph_delinquency/tasks.py`
     (M12.3 detector pattern to
     mirror).
   - `backend/dealer_ai/services/bhph_promises/tasks.py`
     (M12.4 detector pattern to
     mirror).

3. **Verify starting state** (§2
   above).

4. **Draft (in order):**
   - `VehicleCost.posted_at`
     column + migration `0044`
     (additive nullable
     DateTimeField).
   - `services/accounting/
     vehicle_cost.py` module with
     `detect_unposted_costs` +
     `post_vehicle_cost_journal`
     verbs.
   - `services/accounting/tasks.py`
     Celery-beat orchestrator +
     10:00 slot registration in
     `dealer_kit/settings.py`.
   - ~25 focused tests
     distributed across service /
     detector / task files.

5. **Full-suite verification.**
   Target 4,194 → ~4,220.

6. **Ship handoff at
   `docs/handoffs/SESSION_130_m13_inc2_m2_cost_reconciliation.md`.**

7. **Overwrite
   `00-START-NEXT-SESSION.md`** with
   M13.3 priority (trial-balance
   snapshot).

## Explicit non-goals for SESSION_130

- ❌ Do NOT ship M13.3-M13.4 scope.
- ❌ Do NOT modify M1-M12 business
  logic beyond additive
  `VehicleCost.posted_at`.
- ❌ Do NOT force-push or amend
  any M11/M12/M13.1 commits.

## NEXT TASK

Start SESSION_130 with (a) surfacing
M13.2 implementation-time micro-
decisions with the user, (b) the
read-first list, (c) starting-state
verification, then (d)
`VehicleCost.posted_at` additive
extension + migration `0044` +
`services/accounting/vehicle_cost.py`
+ Celery-beat detector at 10:00 +
~25 tests. Target baseline 4,194
→ ~4,220. Ship the M13.2 handoff.

Backend baseline at SESSION_130
close: **~4,220 pass**. Frontend
baseline: unchanged (no frontend
at M13.2).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 13
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_13_PLANNING.md`
6. `docs/roadmap/MILESTONE_12_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_129_m13_inc1_gl_substrate.md`
   (this session's close)
8. `docs/handoffs/SESSION_128_m12_close.md`
9. `docs/CAPABILITY_MATRIX.md` §7m
10. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
11. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_129 — M13.1 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0043`. Test baseline:
  **4,194 pass**, 1 skipped, 0
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
  registered** (unchanged — M13.2
  10:00 slot lands next
  session).
- **Milestones shipped:** M1 →
  **M12** + M13.1 (of M13). M13.2
  next.
- **DRF admin surface:** **101**
  endpoints (was 98 at M12 close;
  +3 M13.1 accounting).
- **Frontend operator routes:**
  **17** (unchanged — no UI at
  M13.1 per §5.f Option C).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages + seven M12
  packages + new
  `services/accounting/` (M13.1
  — 24-account default COA +
  three verbs).
- **Tenancy carriers:** **47**
  (44 at M12 close → 47 at M13.1
  close via GLAccount +
  JournalEntry + JournalEntryLine).
- **Permission classes:** **8**
  (unchanged — every M13.1
  endpoint reused M4
  `IsSalesManagerOrOwnerAtActiveDealership`;
  zero drift across four
  consecutive milestones now).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — no LLM
  path at M13.1).
- **Deterministic rules:**
  unchanged.
- **Milestone 13 next:** M13.2
  M2 cost reconciliation
  detector. Ninth Celery-beat
  task family at 10:00.
  `VehicleCost.posted_at`
  additive extension. Migration
  `0044`. Target ~25 tests,
  baseline 4,194 → ~4,220.
