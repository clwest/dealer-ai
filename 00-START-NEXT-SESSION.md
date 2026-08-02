---
state: active
date: 2026-08-02
last_session_shipped: SESSION_142
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
milestone_13_status: shipped
milestone_14_status: shipped
milestone_15_status: shipped
milestone_16_status: in-progress
next_session: SESSION_143
next_milestone: 16
next_milestone_name: "M12 BHPH payment GL post"
next_increment: 1
next_increment_name: "M16.1 — Backend: BHPH payment GL detector"
---

# Next session — SESSION_143 · Milestone 16 · Increment 1 (M16.1 — Backend: BHPH payment GL detector)

> **SESSION_142 shipped M16.0 —**
> planning-only session per the
> M10.0 / M11.0 / M12.0 / M13.0 /
> M14.0 / M15.0 precedent. Full
> memo expansion at
> `MILESTONE_16_PLANNING.md` (~1,010
> lines) + one coordinated commit.
> **§5.a → Option B confirmed**
> (M12 BHPH payment GL post named as
> the M16 target). **All six §5
> decisions confirmed as-recommended
> at M16.0 open** — streak extends
> to **64 planning-time as-
> recommended M5.1 → M16.0** across
> **seven consecutive milestones now**
> (M10 + M11 + M12 + M13 + M14 +
> M15 + M16).
>
> **Backend baseline at M16.0 close:**
> 4,296 pass, 1 skipped, 0 fail
> (unchanged — planning-only).
> **Frontend Vitest baseline:** 122
> pass (unchanged — no frontend at
> M16 per §5.f Option A). Migrations
> `0043`–`0044` (unchanged).
> Tenancy carriers 47 (unchanged).
> DRF admin surface 104 (unchanged).
> Frontend operator routes 20
> (unchanged). Celery-beat task
> families 9 (unchanged — 11:00
> BHPH-payment entry lands at M16.1).
>
> **SESSION_143 opens M16.1 —
> single backend increment.** All
> M16 write-path work lands here
> per §7 M16.1 sequencing. Follows
> M13.2's `vehicle_cost.py` +
> `tasks.py` + `CELERY_BEAT_SCHEDULE`
> template near-verbatim (different
> source entity, different accounts,
> same posture).

## First thing SESSION_143 must do

### 1. Verify starting state

- `git status` — clean (M16.0
  docs commit landed at
  SESSION_142 close pending user
  authorization on push).
- `git log --oneline -5` — top
  should be the coordinated M16.0
  docs commit.
- `python3 manage.py test dealer_ai`
  → **4,296 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **122 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Read first (in order)

- `docs/roadmap/MILESTONE_16_PLANNING.md`
  §5.a-§5.f (all six locked) +
  §7 M16.1 sequencing (this
  session's scope).
- `docs/handoffs/SESSION_142_m16_inc0_planning.md`
  (previous session).
- `backend/dealer_ai/services/accounting/vehicle_cost.py`
  (M13.2 template that M16.1
  mirrors — same shape, different
  source entity + accounts).
- `backend/dealer_ai/services/accounting/tasks.py`
  (M13.2 Celery-task pair that
  M16.1 extends).
- `backend/dealer_ai/services/bhph_payments/bhph_payment.py`
  (M12.2 write path that produces
  the rows M16.1 will post).
- `backend/dealer_ai/models.py`
  §BhphPayment (~line 6614 — the
  entity gaining `posted_at`).
- `backend/dealer_kit/settings.py`
  §CELERY_BEAT_SCHEDULE
  (~line 484 — the M13.2 entry
  M16.1 pattern-matches).

## What M16.1 delivers

Per `MILESTONE_16_PLANNING.md` §7
M16.1:

1. **Migration `0045_m161_bhph_
   payment_posted_at.py`** —
   adds `BhphPayment.posted_at
   DateTimeField(null=True,
   blank=True, db_index=True)`
   per §5.d Option A. All
   existing rows default null →
   become detector-eligible on
   next run.
2. **New module `services/
   accounting/bhph_payment.py`**
   mirroring `vehicle_cost.py`
   shape:
   - `detect_unposted_bhph_
     payments(*, dealership) ->
     QuerySet[BhphPayment]` —
     pure query, no writes.
     Filter: `posted_at__isnull=
     True`, tenant-scoped,
     ordered by `paid_at, id`.
   - `post_bhph_payment_journal(
     *, dealership, bhph_payment,
     posted_at=None) ->
     BhphPayment` — atomic
     sibling verb. Composes 2-
     or 3-line JournalEntry per
     §5.c Option A (DR 100000
     Cash) + §5.e Option A (CR
     430000 Interest Income if
     non-zero interest; CR
     123000 BHPH Notes
     Receivable if non-zero
     principal; fees always
     skipped per §3 item 2).
   - `post_all_unposted_bhph_
     payments_for_dealership(*,
     dealership, now=None) ->
     dict[str, Any]` —
     orchestrator matching
     M13.2's return shape
     exactly (dealership_id,
     dealership_slug, as_of,
     posted_count, failed_count,
     posted_ids, failed_ids).
3. **Extend `services/accounting/
   tasks.py`** with two new
   Celery tasks:
   - `post_bhph_payment_journals_
     for_dealership(*,
     dealership_id) -> dict`.
   - `post_bhph_payment_journals_
     for_all_tenants() -> dict`.
   Both use `@instrumented_task`
   per M13.2 pattern.
4. **Add `bhph-payment-post-
   daily-11-00` entry** to
   `CELERY_BEAT_SCHEDULE` in
   `dealer_kit/settings.py` at
   `crontab(hour=11, minute=0)`
   per §5.b Option A.
5. **Extend `services/accounting/
   __init__.py`** `__all__` for
   the new verbs.
6. **Focused tests (~25-30
   target)** in new
   `tests/test_m161_bhph_
   payment_gl.py`:
   - `detect_unposted_bhph_
     payments` — correct rows,
     tenant-scoped, ordered.
   - `post_bhph_payment_journal`
     happy path — balanced 3-
     line entry for principal+
     interest payment.
   - Zero-interest payment — 2-
     line entry (DR Cash / CR
     Notes Rcv), Interest
     Income line skipped.
   - Zero-principal (interest-
     only) payment — 2-line
     entry (DR Cash / CR
     Interest Income).
   - `posted_at` denormalized
     on success.
   - Cross-tenant BhphPayment
     raises
     `CrossTenantGLAccountError`
     → 404 shape (fail-closed).
   - Missing account raises
     `MissingDefaultAccountError`.
   - Fees column non-zero
     raises a broken-invariant
     error (asserts M12 zero-
     fees assumption).
   - Orchestrator posts all
     unposted rows for one
     tenant.
   - Orchestrator per-row
     failure isolation (one bad
     row does not block the
     rest).
   - Idempotency — second run
     posts nothing.
   - Celery task `post_bhph_
     payment_journals_for_
     dealership` calls the
     orchestrator.
   - Celery task `post_bhph_
     payment_journals_for_all_
     tenants` enqueues per-
     tenant tasks.
   - Beat schedule registration
     test (mirrors M13.2 test).
   - Trial balance reflects new
     entries.
- No new endpoints.
- No new permission classes.
- No new post-LLM scrub stages.

**Backend baseline target:**
4,296 → ~4,321-4,326 pass (+25-
30 tests, 0 regressions).
Frontend Vitest: unchanged.
Migrations: `0043`–`0044` →
`0043`–`0045` (+1). Tenancy
carriers: 47 (unchanged).
DRF admin surface: 104
(unchanged). Frontend operator
routes: 20 (unchanged).
Permission classes: 8
(unchanged — zero-drift extends
to eight consecutive milestones).
Celery-beat task families: 9 →
**10** (new bhph-payment daily
entry at 11:00).

## What SESSION_143 should do

### Recommended step sequence

1. **Verify starting state** (§1
   above).

2. **Read first (in order)** (§2
   above).

3. **Ship the migration first**
   — one `AddField` per §5.d
   Option A. Verify with
   `makemigrations --check
   --dry-run` clean before /
   after.

4. **Write `services/accounting/
   bhph_payment.py` module** —
   mirror `vehicle_cost.py`
   verbatim; substitute
   `BhphPayment` for
   `VehicleCost` + the three
   BHPH accounts (100000 /
   123000 / 430000) for the two
   M13.2 accounts (122000 /
   200000). Handle the 2-vs-3-
   line composition per §5.e
   Option A.

5. **Extend `services/
   accounting/tasks.py`** — add
   the two Celery tasks +
   register the beat entry.

6. **Write focused tests** in
   `tests/test_m161_bhph_
   payment_gl.py` per §7 M16.1
   test list.

7. **Verify baseline delta** —
   `python3 manage.py test
   dealer_ai` → 4,321-4,326
   pass, zero regressions.

8. **Ship handoff at
   `docs/handoffs/SESSION_143_
   m16_inc1_backend.md`.**

9. **Overwrite
   `00-START-NEXT-SESSION.md`**
   with M16.2 close-out
   priority.

## Explicit non-goals for SESSION_143

- ❌ Do NOT ship M16.2 close-out
  docs (separate session per
  M15 pattern).
- ❌ Do NOT wire NSF / reversal
  handling (deferred per §3
  item 3).
- ❌ Do NOT add method-aware
  fund-flow routing (deferred
  per §3 item 1).
- ❌ Do NOT add BhphFee entity
  or late-fee income line
  (deferred per §3 item 2).
- ❌ Do NOT add JournalEntry FK
  to BhphPayment (deferred per
  §3 item 7 / M15 §3 item 9).
- ❌ Do NOT modify M1-M15
  business logic beyond the
  additive `posted_at` column
  on BhphPayment.
- ❌ Do NOT ship frontend work
  (§5.f Option A locked).
- ❌ Do NOT force-push or amend
  any earlier commits.

## NEXT TASK

Start SESSION_143 with (a)
starting-state verification, (b)
the read-first list, then (c)
shipping migration `0045` +
module `services/accounting/
bhph_payment.py` + tasks.py
extension + beat-schedule entry
+ focused tests. Ship the M16.1
handoff.

Backend baseline at SESSION_143
close: **~4,321-4,326 pass**
(+25-30 tests, zero regressions).
Frontend baseline: **122 pass**
(unchanged).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_16_PLANNING.md`
   (all six §5 decisions locked
   at SESSION_142 M16.0 open)
6. `docs/handoffs/SESSION_142_m16_inc0_planning.md`
   (previous session)
7. `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
   §6 (eight lessons carry into
   M16) + §8 (M15 unblocked
   work — BHPH payment detector
   explicitly named)
8. `docs/roadmap/MILESTONE_13_PLANNING.md`
   §5.d Option C hybrid GL-
   posting trigger shape
9. `docs/CAPABILITY_MATRIX.md` §7p
10. `docs/research/BHPH_OPERATIONS_MAPPING.md`
    §3 payment operations +
    §3.10 daily rhythm

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_142 — M16.0 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0044`. Test baseline:
  **4,296 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 122 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **9
  scheduled task families
  registered** at M16.0
  (unchanged; 11:00 BHPH-payment
  entry lands at M16.1 to make
  it **10**).
- **Milestones shipped:** M1 →
  **M15** (SESSION_141 close).
  M16 in-progress at M16.0.
- **DRF admin surface:** **104**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages + seven M12
  packages + **`services/
  accounting/` (five modules:
  `default_coa.py` + `journal.py`
  + `snapshot.py` + `vehicle_
  cost.py` + `sale_booking.py`)**.
  M16.1 adds **`bhph_payment.py`**
  as the sixth module.
- **Frontend accounting
  surface:** `frontend/src/lib/
  accountingApi.ts` with 4
  fetchers + 1 mutator + three
  page components (unchanged at
  M16 — backend-only per §5.f
  Option A).
- **Tenancy carriers:** **47**
  (unchanged at M16).
- **Permission classes:** **8**
  (unchanged — zero-drift
  streak extends to seven
  consecutive milestones; M16.1
  extends to **eight** since
  no endpoints added).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M16 has
  no LLM path).
- **Deterministic rules:**
  unchanged.
- **Milestone 16 next:** M16.1
  backend implementation.
  Migration `0045` +
  `services/accounting/bhph_
  payment.py` + tasks.py
  extension + beat-schedule
  entry + focused tests.
