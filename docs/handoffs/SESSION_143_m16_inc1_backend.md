---
title: "SESSION_143 handoff — Milestone 16 · Increment 1 (M16.1 — Backend: BHPH payment GL detector)"
status: historical
type: handoff
date: 2026-08-02
session: 143
milestone: 16
milestone_status: in-progress
milestone_name: "M12 BHPH payment GL post"
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_143 — Milestone 16 · Increment 1 (M16.1 — Backend: BHPH payment GL detector)

## What shipped

Every unposted BhphPayment is now
picked up by an 11:00 project-time
daily Celery-beat detector and posts
a matching balanced JournalEntry via
`services/accounting/post_journal_entry`.
The M14.3 journal-entry browser
surfaces these entries automatically
with descriptive `description`
("BHPH payment intake — BhphPayment
#X against note #Y (…)") + line
memos.

Per `MILESTONE_16_PLANNING.md` §5.b
+ §5.c + §5.d + §5.e + §5.f Option A
(all confirmed as-recommended at
SESSION_142 M16.0 open):

- **§5.b** Detector at 11:00
  project-time daily, next open
  slot after M13.2's 10:00.
  Continues the 02:00-10:00 non-
  overlapping window pattern.
- **§5.c** Uniform DR 100000 Cash
  on Hand regardless of payment
  method. Method-aware fund-flow
  routing deferred pending deposit-
  workflow milestone.
- **§5.d** Idempotency via
  `BhphPayment.posted_at__isnull=True`
  filter (migration `0045` adds the
  column).
- **§5.e** Zero-amount line skip —
  early-payoff / interest-only
  payments post 2-line entries;
  standard split posts 3-line
  entries; both-zero
  architecturally impossible
  upstream.
- **§5.f** No frontend — M14.3
  browser + M14.2 trial balance
  surface new entries automatically.

**Nine §0.a M16.1 micro-decisions
recorded** — all as-recommended per
M10 §9 (do not count against
planning-time streak). The
planning-time streak stands at **64
planning-time as-recommended M5.1
→ M16.0** across seven consecutive
milestones (M10 + M11 + M12 + M13 +
M14 + M15 + M16).

**Backend baseline: 4,296 → 4,326
pass, 1 skipped, 0 fail** (+30
tests, zero regressions —
exactly the top of the 25-30
planning target). **Frontend
Vitest baseline: 122 pass**
(unchanged — no frontend at M16
per §5.f Option A). Migrations
`0043`–`0044` → **`0043`–`0045`**
(+1). Tenancy carriers 47
(unchanged — BhphPayment gained a
column, not a new model). DRF
admin surface 104 (unchanged — no
new endpoints; detector is Celery-
scheduled). Frontend operator
routes 20 (unchanged). Permission
classes 8 (unchanged — **zero-
drift streak extends to eight
consecutive milestones now**:
M10 + M11 + M12 + M13 + M14 + M15
+ M16). Celery-beat task families
9 → **10** (new bhph-payment
daily entry at 11:00).

## Files touched at M16.1

Created:

1. `backend/dealer_ai/migrations/
   0045_m161_bhph_payment_posted_at.py`
   — one `AddField` for
   `BhphPayment.posted_at
   DateTimeField(null=True,
   blank=True)`. Matches
   `0044_m132_vehicle_cost_posted_at`
   shape verbatim per §0.a M16.1
   decision 1.
2. `backend/dealer_ai/services/
   accounting/bhph_payment.py` —
   new module (~290 lines).
   Exports:
   `detect_unposted_bhph_payments`
   pure query;
   `post_bhph_payment_journal`
   atomic sibling verb (DR 100000
   Cash + optional CR 123000
   Notes Rcv + optional CR
   430000 Interest Income);
   `post_all_unposted_bhph_payments_for_dealership`
   orchestrator (matches M13.2
   return shape exactly).
   Declares
   `UnexpectedBhphPaymentFeesError`
   (broken-invariant guard),
   duplicates
   `_lookup_required_account`
   from M13.2, and declares
   three account-code constants
   (`CASH_ACCOUNT_CODE`,
   `BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE`,
   `BHPH_INTEREST_INCOME_ACCOUNT_CODE`).
3. `backend/dealer_ai/tests/
   test_m161_bhph_payment_gl.py`
   — **30 focused tests** across
   9 TestCase classes:
   - `DetectUnpostedBhphPaymentsTests`
     (5 tests) — unposted rows
     returned, already-posted
     excluded, dealership-scoped,
     ordering by paid_at+id,
     zero-portfolio semantics.
   - `PostBhphPaymentJournalHappyPathTests`
     (7 tests) — 3-line entry
     (principal+interest), 2-line
     (zero-interest early payoff),
     2-line (zero-principal
     interest-only), posted_at
     denorm, balanced double-
     entry, description shape,
     posted_at uses supplied
     timestamp.
   - `PostBhphPaymentJournalGuardsTests`
     (6 tests) — cross-tenant,
     missing Cash / Notes Rcv /
     Interest Income accounts,
     non-zero fees, atomic
     rollback on failure.
   - `PostAllUnpostedBhphPaymentsOrchestratorTests`
     (5 tests) — posts all,
     summary shape matches M13.2,
     per-row failure isolation,
     cross-run idempotency,
     zero-payments summary.
   - `PostBhphPaymentTaskTests`
     (3 tests) — per-tenant task
     name constant, orchestrator
     name constant, direct call
     posts + returns summary.
   - `BhphPaymentOrchestratorDispatchTests`
     (1 test) — orchestrator
     dispatches per tenant via
     `.delay`.
   - `BhphPaymentBeatScheduleTests`
     (2 tests) — 11:00 slot
     registered, beat families
     >= 10.
   - `TrialBalanceReflectsBhphPaymentsTests`
     (1 test) — M14.2 trial
     balance shows 100000 /
     123000 / 430000 activity
     after posting.
4. `docs/handoffs/SESSION_143_
   m16_inc1_backend.md` — this
   handoff.

Modified:

5. `backend/dealer_ai/models.py`
   — added `BhphPayment.posted_at
   DateTimeField(null=True,
   blank=True)` with docstring
   referencing §5.d Option A.
6. `backend/dealer_ai/services/
   accounting/tasks.py` —
   extended module docstring;
   added two new task-name
   constants
   (`POST_BHPH_PAYMENT_FOR_TENANT_TASK_NAME`
   +
   `POST_BHPH_PAYMENT_FOR_ALL_TENANTS_TASK_NAME`);
   added two new `@instrumented_task`
   functions
   (`post_bhph_payment_journals_for_dealership`
   +
   `post_bhph_payment_journals_for_all_tenants`).
7. `backend/dealer_ai/services/
   accounting/__init__.py` —
   re-exports the new bhph_payment
   verbs +
   `BHPH_INTEREST_INCOME_ACCOUNT_CODE`
   +
   `UnexpectedBhphPaymentFeesError`.
   `__all__` extended
   accordingly.
8. `backend/dealer_kit/settings.py`
   — added
   `accounting-bhph-payment-post-
   daily-11-00` entry to
   `CELERY_BEAT_SCHEDULE` at
   `crontab(hour=11, minute=0)`
   per §5.b Option A. Continues
   the 02:00-10:00 non-overlapping
   window pattern by one hour.
9. `docs/roadmap/MILESTONE_16_
   PLANNING.md` — §0.a change log
   extended with SESSION_143
   M16.1 close block (5 micro-
   decisions + delta totals);
   §7 M16.1 deliverable text
   adjusted to reflect no
   `db_index` per §0.a M16.1
   decision 1.
10. `00-START-NEXT-SESSION.md`
    — overwritten with M16.2
    close-out priority per doc-
    governance session-lifecycle
    rule.

## §0.a M16.1 micro-decisions

Recorded in
`MILESTONE_16_PLANNING.md` §0.a
per M10 §9 posture (implementation-
time defaults; do not count
against planning-time streak).
Summary:

1. **`db_index` dropped** on
   `BhphPayment.posted_at` —
   matches M13.2's
   `VehicleCost.posted_at`
   verbatim. Existing
   `dealership_id` FK index
   scopes the detector query at
   expected daily volumes; the
   write-side index cost is not
   justified by evidence.
2. **`_lookup_required_account`
   duplicated** verbatim in the
   BHPH-payment module — mirrors
   M15.1 §0.a decision 3
   (evidence gate for a shared-
   helper refactor not tripped).
3. **`CrossTenantGLAccountError`
   reused** for cross-tenant
   BhphPayment check — matches
   M13.2 + M15.1 posture (same
   fail-closed 404 shape).
4. **`UnexpectedBhphPaymentFeesError`
   as `RuntimeError` subclass**
   — broken-invariant signal
   (matches
   `MissingDefaultAccountError`
   + `UnmappedFinanceTypeError`
   posture). Fires when a future
   BhphFee milestone populates
   `applied_to_fees` without
   extending this verb first.
5. **Local account-code
   constants** — duplicates
   `CASH_ACCOUNT_CODE` +
   `BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE`
   from `sale_booking.py`
   (accepted per M15.1 posture);
   declares new
   `BHPH_INTEREST_INCOME_ACCOUNT_CODE`
   locally. `__init__.py`
   re-exports the new constant
   only.

## Verifications passed at SESSION_143 close

- `git status` — pending this
  commit; working tree contains
  M16.1 code + docs.
- `git log --oneline -5` — top
  is `e909582 Milestone 16 ·
  Increment 0 — Planning
  refinement + target selection
  (SESSION_142)`.
- `python3 manage.py test dealer_ai`
  → **4,326 pass, 1 skipped, 0
  fail** (+30 tests, zero
  regressions).
- `python3 manage.py check`
  clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected." (migration `0045`
  already applied to the schema.)
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → PONG.

## What SESSION_144 (M16.2) picks up

Per `MILESTONE_16_PLANNING.md` §7
M16.2 — close-out session
(documentation only). Six close-
out docs matching the M10.8 /
M11.7 / M12.8 / M13.4 / M14.5 /
M15.2 precedent:

1. Write
   `docs/roadmap/MILESTONE_16_
   RETROSPECTIVE.md` (mirror
   M15 shape: planned scope,
   what shipped, deferrals,
   deviations, compatibility,
   lessons, streak update, M17
   unblocks).
2. Append §7q to
   `docs/CAPABILITY_MATRIX.md`
   describing the M16 BHPH-
   payment GL-post surface.
3. Add §Milestone 16 SHIPPED
   entry to
   `docs/roadmap/IMPLEMENTATION_
   ROADMAP.md`.
4. Frontmatter flip on
   `MILESTONE_16_PLANNING.md`:
   `status: active` → `status:
   shipped`.
5. Draft
   `docs/roadmap/MILESTONE_17_
   PLANNING.md` skeleton with
   the M16 §8 unblocked-work
   list.
6. Overwrite
   `00-START-NEXT-SESSION.md`
   with M17.0 priority.

**M16.2 target totals.** Backend
baseline stays **4,326 pass** (no
code at close-out). Frontend
Vitest **122 pass** (unchanged).
Migrations `0043`–`0045`
(unchanged).

## Explicit non-goals for SESSION_144 (M16.2)

- ❌ Do NOT ship M17.1+ code at
  M16.2 (close-out is docs
  only).
- ❌ Do NOT modify M1-M16
  business logic.
- ❌ Do NOT force-push or amend
  earlier commits.

## Push authorization

M16.1 will land as one commit
containing: migration `0045`, new
`bhph_payment.py` module + test
file, extended `tasks.py` +
`__init__.py`, `settings.py` beat
entry, model change, planning-
doc §0.a amendments, this
handoff, and session-start
refresh. Mirrors the M15.1 single-
commit pattern.

User authorization required
before push per standing user
directive.
