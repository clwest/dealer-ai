---
state: active
date: 2026-08-02
last_session_shipped: SESSION_139
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
milestone_15_status: in_progress
next_session: SESSION_140
next_milestone: 15
next_milestone_name: "M9 sale-booking GL post"
next_increment: 1
next_increment_name: "M15.1 — Backend: sale-booking GL post"
---

# Next session — SESSION_140 · Milestone 15 · Increment 1 (M15.1 — Backend: sale-booking GL post)

> **SESSION_139 shipped M15.0 —**
> planning-only session. Expanded
> `MILESTONE_15_PLANNING.md` skeleton
> (~305 lines) into active memo
> (~635 lines). All six §5 load-
> bearing decisions confirmed as-
> recommended at session open per
> the M5-M14 pattern. **Streak
> extends to 58 planning-time as-
> recommended M5.1 → M15.0** across
> six consecutive milestones (M10 +
> M11 + M12 + M13 + M14 + M15).
>
> **M15 target: Option A — M9 sale-
> booking GL post.** Sync
> `@transaction.atomic` sibling-
> service call inside
> `services/sale/record_sale` per M13
> §5.d Option C hybrid posture. Every
> sold vehicle produces a matching
> balanced JournalEntry via
> `services/accounting/post_journal_entry`.
> M14.3 journal-entry browser
> surfaces the resulting entries
> automatically — zero frontend
> increment at M15.
>
> **M15 sequencing:** three
> increments total (M15.0 planning +
> M15.1 backend + M15.2 close-out).
> Smaller surface than M14's five
> per backend-only scope.

## First thing SESSION_140 must do

### 1. Verify starting state

- `git status` — clean (M15.0 docs
  commit landed at SESSION_139
  close per user authorization).
- `git log --oneline -3` — top
  should be the M15.0 docs commit.
- `python3 manage.py test dealer_ai`
  → **4,277 pass, 1 skipped, 0
  fail** (unchanged from
  SESSION_138 close).
- `cd frontend && npm test` → **122
  pass** (unchanged).
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `redis-cli ping` → `PONG`.

### 2. Read first (in order)

- `docs/roadmap/MILESTONE_15_PLANNING.md`
  §5.a–§5.f (six confirmed
  decisions) + §7 M15.1 (increment
  scope).
- `docs/handoffs/SESSION_139_m15_inc0_planning.md`
  (previous session — this
  handoff details what SESSION_140
  picks up).
- `backend/dealer_ai/services/sale/computation.py`
  (M9 write path — `record_sale`
  will be extended).
- `backend/dealer_ai/services/accounting/journal.py`
  (M13.1 — `post_journal_entry`
  is the atomic sibling target;
  `JournalLineInput` dataclass is
  the input contract).
- `backend/dealer_ai/services/accounting/vehicle_cost.py`
  (M13.2 — `post_vehicle_cost_journal`
  is invoked for the un-posted-
  cost flush per §5.d Option A;
  `_lookup_required_account` is
  the template for the sale-
  booking module's account
  helpers).
- `backend/dealer_ai/services/accounting/default_coa.py`
  (M13.1 — enumerates the account
  codes M15 uses: 100000, 120000,
  122000, 123000, 400000, 500000).
- `backend/dealer_ai/views_sale.py`
  (M9 endpoint — extend to pass
  `request.user` through as
  `posted_by_user`).
- `backend/dealer_ai/tests/test_m9_sale_computation.py`
  (M9 existing test file — new
  M15.1 tests likely add a
  companion file
  `test_m151_sale_booking.py`
  per M13/M14 pattern).

## What M15.1 delivers

Per `MILESTONE_15_PLANNING.md` §7
M15.1:

- **New module**
  `backend/dealer_ai/services/
  accounting/sale_booking.py` with
  `post_sale_booking_journal(*,
  dealership, sale,
  posted_by_user=None) ->
  JournalEntry` — atomic sibling-
  service verb composing
  receivable + revenue + COGS +
  Recon-WIP-clear lines and
  delegating to
  `post_journal_entry`.
- **Finance-type → receivable
  account mapping** per §5.b
  Option A:
  - `cash` → **100000 Cash on
    Hand**.
  - `retail` → **120000 Contracts
    in Transit**.
  - `bhph` → **123000 BHPH Notes
    Receivable**.
- **Zero-cost path** per §5.c
  Option A — skip COGS + Recon
  WIP pair when `total_investment
  == 0`; post revenue-pair only;
  log warning.
- **Un-posted-cost flush** per
  §5.d Option A — inside
  `record_sale`, before the sale-
  booking journal posts, iterate
  every un-posted / non-estimate
  VehicleCost for the target
  vehicle and call
  `post_vehicle_cost_journal`.
- **`record_sale` extension** —
  accept `posted_by_user=None`
  kwarg (default preserves
  existing call sites) + invoke
  the flush + sale-booking calls
  inside the existing
  `@transaction.atomic` block.
- **`views_sale.py` extension**
  — pass `request.user` through
  as `posted_by_user=request.user`
  so the JournalEntry's
  `posted_by_user` FK is populated.
- **Focused tests (~25-30)** —
  finance-type mapping (cash /
  retail / BHPH), balanced double-
  entry, cross-tenant guard,
  zero-cost skip path, un-posted-
  cost flush, missing-account
  error, `posted_by_user`
  propagation, atomic-rollback,
  idempotency short-circuit,
  M14.3 list-endpoint sees the
  new entries.

**Baselines projected at M15.1
close:**
- Backend: 4,277 → ~4,302-4,307
  (+25-30 tests, 0 regressions).
- Frontend Vitest: 122 (unchanged
  — no frontend touched).
- Migrations: 0043-0044
  (unchanged — no schema changes).
- DRF admin surface: 104
  (unchanged).
- Frontend operator routes: 20
  (unchanged).
- Tenancy carriers: 47
  (unchanged).
- Permission classes: 8
  (unchanged — zero-drift extends
  to seven consecutive milestones).
- Celery-beat task families: 9
  (unchanged).

## What SESSION_140 should do

### Recommended step sequence

1. **Verify starting state** (§1
   above).

2. **Read first (§2 above).**

3. **Create the new module +
   verb.** Write
   `services/accounting/sale_booking.py`
   with `post_sale_booking_journal`
   + account-lookup helpers. Wire
   into
   `services/accounting/__init__.py`
   `__all__`.

4. **Extend `record_sale`** to
   invoke the flush + sale-
   booking calls. Preserve
   existing call sites via
   `posted_by_user=None` default.

5. **Extend `views_sale.py`** to
   propagate `request.user`.

6. **Write focused tests
   (~25-30).** New test file
   `test_m151_sale_booking.py`.

7. **Full test suite** → assert
   4,277 → ~4,302-4,307 with 0
   regressions.

8. **Manual verification** via
   `manage.py shell` — record a
   sale for each finance_type;
   verify a balanced JournalEntry
   is created; verify M14.3 list
   endpoint returns them with
   `posted_by_username` populated.

9. **Ship handoff at
   `docs/handoffs/SESSION_140_m15_inc1_backend.md`.**

10. **Overwrite
    `00-START-NEXT-SESSION.md`**
    with M15.2 (close-out)
    priority.

## Explicit non-goals for SESSION_140

- ❌ Do NOT ship sales-tax posting.
- ❌ Do NOT ship trade-in
  accounting.
- ❌ Do NOT ship F&I product
  revenue at sale.
- ❌ Do NOT ship doc-fee revenue.
- ❌ Do NOT ship reserve-
  receivable at sale.
- ❌ Do NOT ship BHPH interest-
  accrual detector.
- ❌ Do NOT add
  `SALE_FINANCE_TYPE_WHOLESALE`
  vocab.
- ❌ Do NOT wire sale-reversal to
  M14.4 JournalEntry reversal.
- ❌ Do NOT add JournalEntry FK
  to Sale.
- ❌ Do NOT ship CIT-to-Cash
  funding workflow.
- ❌ Do NOT modify M13.2 detector
  for post-sale VehicleCost.
- ❌ Do NOT ship GL-derived
  reporting analytics.
- ❌ Do NOT ship any frontend
  changes (§5.f Option A — M15 is
  backend-only).
- ❌ Do NOT force-push or amend
  any earlier commits.

## NEXT TASK

Start SESSION_140 with (a)
starting-state verification, (b)
the read-first list, then (c)
implementing M15.1 per the six
confirmed §5 decisions. Ship the
M15.1 handoff.

Backend baseline at SESSION_140
close: **~4,302-4,307 pass** (+25-
30 vs SESSION_139). Frontend
baseline: **122 pass** (unchanged
— M15 is backend-only).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_15_PLANNING.md`
6. `docs/roadmap/MILESTONE_14_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_139_m15_inc0_planning.md`
   (this session's close)
8. `docs/handoffs/SESSION_138_m14_close.md`
9. `docs/CAPABILITY_MATRIX.md` §7o
10. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
    §3.5 (CIT / funding) + §3.13
    (sales-tax deferred).

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_139 — M15.0 shipped, M15 in progress)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0044`. Test baseline:
  **4,277 pass**, 1 skipped, 0
  fail (unchanged — planning-
  only session).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 122 pass** (unchanged
  — planning-only session).
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **9
  scheduled task families
  registered.** M15 adds no new
  beat schedules — sale booking
  is operator intent, not
  elapsed condition.
- **Milestones shipped:** M1 →
  **M14** (SESSION_138 close).
  **M15 in progress** — M15.0
  planning complete; M15.1
  backend + M15.2 close-out
  ahead.
- **DRF admin surface:** **104**
  endpoints (unchanged at M15).
- **Frontend operator routes:**
  **20** (unchanged at M15 —
  backend-only milestone).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages + seven M12
  packages + `services/
  accounting/` (M13 four modules
  + M14.1 two additive query
  verbs). **M15.1 adds
  `services/accounting/sale_booking.py`
  as a fifth module.**
- **Frontend accounting
  surface:** unchanged at M15.
- **Tenancy carriers:** **47**
  (unchanged at M15 — no new
  models).
- **Permission classes:** **8**
  (unchanged — zero-drift
  streak extends to seven
  consecutive milestones on
  M15.1 landing: M10 + M11 +
  M12 + M13 + M14 + M15).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M15 has
  no LLM path).
- **Deterministic rules:**
  unchanged.
- **Milestone 15 next:** M15.1
  backend — sale-booking GL
  post inside `record_sale` via
  new sibling module.
