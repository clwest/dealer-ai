---
state: active
date: 2026-08-02
last_session_shipped: SESSION_120
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
milestone_12_status: planning
next_session: SESSION_121
next_milestone: 12
next_milestone_name: "BHPH portfolio operations (v1)"
next_increment: 1
next_increment_name: "M12.1 — BhphNote origination + payment schedule"
---

# Next session — SESSION_121 · Milestone 12 · Increment 1 (M12.1 — BhphNote origination + payment schedule)

> **SESSION_120 shipped M11.7 —**
> six close-out docs (retrospective +
> capability matrix §7l + roadmap flip +
> planning frontmatter flip + session-
> start refresh + M12 planning skeleton)
> + one coordinated commit. **Milestone
> 11 — Sales-side non-chat channels +
> customer-journey completeness — SHIPPED.**
>
> **M11 close totals:** five new entities
> across five implementation sessions
> (TestDrive + DealWriteup +
> FollowUpCadence + FollowUpTask +
> BeBack) + one additive `CustomerLead`
> extension + five new `services/`
> packages + one new frontend route
> family + two new Celery-beat task
> families (M11.4 06:00 surfacer + M11.5
> 07:00 detector). **Six planning-time
> §5 decisions confirmed as-recommended
> at M11.1 open** — streak stands at
> **35 planning-time as-recommended
> M5.1 → M11.1**.
>
> **Backend baseline: 3,895 pass, 1
> skipped, 0 fail** (was 3,730 at M10
> close — +165 tests, 0 regressions).
> **Frontend Vitest baseline: 67 pass**
> (was 51 — +16 at M11.6). Migrations
> `0032`–`0036`. Tenancy carriers 39.
> DRF admin surface 82. Frontend
> operator routes 15. Celery-beat task
> families 6. Permission classes 8
> (unchanged — zero drift).
>
> **Push authorization:** eight local
> commits (M113 hash fixup + M11.1
> through M11.7) queued for user
> authorization at SESSION_120 close.
>
> **SESSION_121 opens M12.1 — BhphNote
> origination + payment schedule.** Per
> `MILESTONE_12_PLANNING.md` (draft
> planning skeleton written at M11.7
> close per standing user directive).
> **Six §5 decisions to confirm at
> session open.**

## First thing SESSION_121 must do

### 1. Confirm the six §5 decisions in `MILESTONE_12_PLANNING.md`

The M12 planning skeleton drafted at
M11.7 close carries six load-bearing
decisions. All six recommendations
follow the M11 pattern (35 consecutive
as-recommended planning-time
resolutions).

Recommendations (drawn from
`MILESTONE_12_PLANNING.md` §9):

1. **§5.a — Contract type vocab
   extension.** Option A (no M10.5
   vocab change; use M9
   `Sale.finance_type == "bhph"` as
   the BHPH signal).
2. **§5.b — Payment application
   order.** Option A (platform-wide
   constant: fees → interest →
   principal).
3. **§5.c — Aging bucket
   vocabulary.** Option A (fixed 7-
   value vocab).
4. **§5.d — PTP reconciliation
   shape.** Option A (operator-
   triggered link).
5. **§5.e — Collection contact
   scrub scope.** Option A (extend
   existing `services/llm_safety.py`
   scrub stack).
6. **§5.f — Operator UI scope.**
   Option C (MVP — portfolio
   dashboard + per-note detail;
   collection contact + repo-order
   UI defer to follow-on).

**Do not write M12.1 code until
every `[NEEDS-DECISION-BEFORE-M12.N]`
item is resolved.** Any user override
→ amend `MILESTONE_12_PLANNING.md`
§0.a narrowly at session top (per
M5-M11 §0.a precedent) before
implementation.

### 2. Verify starting state

- `git status` — clean (M11.7 commit
  landed at SESSION_120 close;
  batch push authorized + executed).
- `git log --oneline -3` — top
  should be `Milestone 11 shipped —
  Sales-side channels + customer
  journey (SESSION_114-120)` or
  similar.
- `git log origin/main..HEAD
  --oneline` — **empty** (all M11
  commits pushed).
- `python3 manage.py test dealer_ai`
  → **3,895 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **67 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `npx tsc --noEmit` + `npx vite
  build` both clean.
- `redis-cli ping` → `PONG`.

## What M12.1 delivers

Per `MILESTONE_12_PLANNING.md` §7
M12.1 (assuming §5.a Option A
confirmed):

- **New `BhphNote` model.**
  - `dealership` FK CASCADE
    (tenancy carrier; extend 39
    → 40).
  - `sale` OneToOne FK to
    `Sale` CASCADE (mandatory —
    BhphNote exists per-sale-that-
    financed-BHPH).
  - `principal_financed`
    Decimal(10, 2).
  - `apr` Decimal(5, 2)
    (percent units matching
    M2 payment_engine
    convention).
  - `term_weeks`
    PositiveIntegerField.
  - `payment_frequency`
    CharField vocab (`weekly`
    / `biweekly` / `semi_monthly`).
  - `payment_amount`
    Decimal(8, 2)
    (denormalized at write from
    payment_engine BHPH math).
  - `first_payment_due` DateField.
  - `default_grace_days`
    PositiveIntegerField default 5.
  - Model `clean()`: sale must
    have `finance_type=="bhph"`
    per §5.a; cross-tenant
    guard on `sale`.
- **New `services/bhph_notes/`
  package** (mirrors M11
  package layout).
- **Verbs (three):**
  - `record_bhph_note(sale,
    principal_financed, apr,
    term_weeks,
    payment_frequency,
    first_payment_due,
    default_grace_days=5)`
    — computes
    `payment_amount` via
    `payment_engine.bhph_payment`;
    refuses non-BHPH sale
    (`NonBhphSaleError`);
    refuses cross-tenant sale
    (`CrossTenantBhphNoteError`);
    refuses duplicate note
    per sale
    (`DuplicateBhphNoteError`
    409).
  - `get_bhph_note(pk,
    dealership)` — tenant-
    scoped read.
  - `get_payment_schedule(note)`
    — pure verb returning
    computed schedule (list of
    `(due_date, amount)`
    tuples) without persisting
    per-payment rows (M12.2
    lands the payment intake
    entity).
- **Endpoints (two):**
  - `POST /admin/bhph-notes/`.
  - `GET /admin/bhph-notes/<pk>/`.
- **Migration `0037`**.
- **Tenancy carrier extension**
  (39 → 40).
- **~30 focused tests** across
  model / service / endpoint
  files (BHPH payment math
  surface warrants larger
  coverage than M11 increments).
- **Baseline target 3,895 →
  ~3,925.**

### Non-goals for M12.1

- ❌ No `BhphPayment` entity
  (M12.2).
- ❌ No delinquency detection
  (M12.3).
- ❌ No PTP tracking (M12.4).
- ❌ No collections (M12.5).
- ❌ No repossession (M12.6).
- ❌ No portfolio analytics or
  UI (M12.7).
- ❌ No M10.5 Contract
  modification.
- ❌ No new `contract_type`
  vocab member.
- ❌ No M11 follow-ups
  (DealWriteup UI, delivery
  adapters, etc. — separate
  M11.x track).

## What SESSION_121 should do

### Recommended step sequence

1. **Confirm the six §5 decisions
   with the user** (§1 above).

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_12_PLANNING.md`
     §1.1 + §1.2 + §5.a + §5.b +
     §7 M12.1.
   - `docs/handoffs/SESSION_120_m11_close.md`
     (previous session).
   - `docs/roadmap/MILESTONE_11_RETROSPECTIVE.md`
     §6 (nineteen lessons carry
     into M12).
   - `docs/research/BHPH_OPERATIONS_MAPPING.md`
     §origination + §payment
     cadence.
   - `backend/dealer_ai/services/payment_engine.py`
     BHPH math functions (already
     shipped; M12.1 consumes
     them).
   - `backend/dealer_ai/models.py::Sale`
     + `Contract` (attach
     targets).
   - `backend/dealer_ai/services/f_and_i/`
     (M10 service package pattern
     to mirror).

3. **Verify starting state** (§2
   above).

4. **Draft (in order):**
   - `BhphNote` model + tenancy
     carrier extension (39 → 40).
   - Migration `0037`.
   - `services/bhph_notes/` package
     + three verbs.
   - `views_bhph_notes.py` +
     endpoints.
   - URL routes.
   - ~30 focused tests.

5. **Full-suite verification.**
   Target 3,895 → ~3,925.

6. **Ship handoff at
   `docs/handoffs/SESSION_121_m12_inc1_bhph_note.md`.**

7. **Overwrite
   `00-START-NEXT-SESSION.md`** with
   M12.2 priority (BhphPayment
   intake + application).

## Explicit non-goals for SESSION_121

- ❌ Do NOT ship M12.2-M12.8 scope.
- ❌ Do NOT modify M1-M11 business
  logic.
- ❌ Do NOT force-push or amend
  any M10/M11 commits.

## NEXT TASK

Start SESSION_121 with (a)
confirming the six §5 decisions
with the user (all recommendations
per M11 pattern), (b) the read-
first list, (c) starting-state
verification, then (d) `BhphNote`
model + tenancy carrier extension
(39 → 40) + migration + service
package with three verbs + endpoints
+ ~30 tests. Target baseline
3,895 → ~3,925. Ship the M12.1
handoff.

Backend baseline at SESSION_121
close: **~3,925 pass**. Frontend
baseline: unchanged (no frontend
at M12.1).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 12
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_12_PLANNING.md`
6. `docs/roadmap/MILESTONE_11_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_120_m11_close.md`
   (this session's close)
8. `docs/handoffs/SESSION_119_m11_inc6_operator_ui.md`
9. `docs/handoffs/SESSION_118_m11_inc5_be_back.md`
10. `docs/handoffs/SESSION_117_m11_inc4_follow_up_cadence.md`
11. `docs/handoffs/SESSION_116_m11_inc3_deal_writeup.md`
12. `docs/handoffs/SESSION_115_m11_inc2_test_drive.md`
13. `docs/handoffs/SESSION_114_m11_inc1_channel_intake.md`
14. `docs/CAPABILITY_MATRIX.md` §7l
15. `docs/research/BHPH_OPERATIONS_MAPPING.md`
16. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_120 — M11 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0036`. Test baseline:
  **3,895 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 67 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **6
  scheduled task families
  registered** (M7.2-M7.5 +
  M11.4 06:00 read-only surfacer
  + M11.5 07:00 state-
  transitioning detector).
- **Milestones shipped:** M1 →
  **M11** (SESSION_120 close).
  M12 planning drafted.
- **DRF admin surface:** **82**
  endpoints.
- **Frontend operator routes:**
  **15** (11 pre-M11 + 4 M11.6
  sales route family).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages (`leads` /
  `test_drives` / `deal_writeups`
  / `follow_ups` / `be_backs`).
- **Tenancy carriers:** **39**
  (34 at M10 close → 39 at M11
  close via M11.2 + M11.3 +
  M11.4×2 + M11.5).
- **Permission classes:** **8**
  (unchanged — every M11
  endpoint reused M4
  `IsSalesManagerOrOwnerAtActiveDealership`;
  zero drift).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** unchanged.
- **Deterministic rules:**
  unchanged.
- **Milestone 12 next:** M12.1
  BhphNote origination + payment
  schedule. Verify six §5
  decisions at session open.
  ~30 tests. Baseline 3,895 →
  ~3,925.
