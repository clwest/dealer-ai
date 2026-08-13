---
title: "SESSION_142 handoff — Milestone 16 · Increment 0 (M16.0 — planning refinement)"
status: historical
type: handoff
date: 2026-08-02
session: 142
milestone: 16
milestone_status: in-progress
milestone_name: "M12 BHPH payment GL post"
increment: 0
increment_status: shipped
commit: TBD
---

# SESSION_142 — Milestone 16 · Increment 0 (M16.0 — planning refinement)

## What shipped

Planning-only session per the
M10.0 / M11.0 / M12.0 / M13.0 /
M14.0 / M15.0 precedent. Full memo
expansion + all six §5 load-bearing
decisions resolved at open. **§5.a
→ Option B confirmed** (M12 BHPH
payment GL post named as the M16
target). **§5.b–§5.f all confirmed
as-recommended.** Streak extends
to **64 planning-time as-
recommended M5.1 → M16.0** across
seven consecutive milestones now
(M10 + M11 + M12 + M13 + M14 + M15
+ M16).

**Backend baseline unchanged:**
4,296 pass, 1 skipped, 0 fail
(verified at session open).
**Frontend Vitest baseline
unchanged:** 122 pass. Migrations
`0043`–`0044` (unchanged).
Tenancy carriers 47 (unchanged).
DRF admin surface 104 (unchanged).
Frontend operator routes 20
(unchanged). Permission classes 8
(unchanged). Celery-beat task
families 9 (unchanged — the 11:00
BHPH-payment entry lands at
M16.1).

## Load-bearing decisions confirmed at M16.0 open

Six decisions per M10.0 / M11.0 /
M12.0 / M13.0 / M14.0 / M15.0
precedent. All confirmed as-
recommended.

**§5.a — Milestone target selection.**
Option B — M12 BHPH payment GL
post. Closes the M13 §5.d Option
C hybrid architecturally (M15
shipped the sync half; M16 ships
the detector half). Substrate
100% ready — every required
primitive shipped in prior
milestones. Pattern reuse near-
total against M13.2's `vehicle_
cost.py` template.

**§5.b — Detector shape + schedule
slot.** Option A — Celery-beat
detector at 11:00 project-time
daily, next open slot after
M13.2's 10:00. Matches
BHPH_OPERATIONS §3.10 end-of-day
cash-reconciliation rhythm and
extends the 02:00-10:00 non-
overlapping window pattern by one
hour. Failure isolation preserved
per M13.2's per-row `try/except`
pattern.

**§5.c — Cash-side account
mapping.** Option A — uniform DR
100000 Cash on Hand regardless of
`method`. Method-aware fund-flow
routing (cash → 100000, ACH →
110000 Bank Operating, etc.)
defers to a future deposit-
workflow milestone. Preserves
M13.2's uniform-mapping posture.

**§5.d — Detector idempotency
signal.** Option A — add
`BhphPayment.posted_at
DateTimeField(null=True,
db_index=True)` via one migration.
Detector filters
`posted_at__isnull=True` for
cross-run idempotency per M13.2
template. FK to JournalEntry
defers per M15 §3 item 9
(unified GL-to-source-entity
milestone).

**§5.e — Zero-amount line
handling.** Option A — skip zero
lines. Zero-interest payment
posts 2-line entry (DR Cash / CR
123000 BHPH Notes Receivable);
zero-principal (interest-only)
payment posts 2-line entry (DR
Cash / CR 430000 BHPH Interest
Income). Fees column always
skipped at M16 per §3 item 2
(no BhphFee entity exists yet;
`applied_to_fees` is always
Decimal("0.00")). Both-zero
architecturally impossible
upstream via `allocate_payment`.
Matches M15 §5.c Option A zero-
cost posture.

**§5.f — Operator UI at M16.**
Option A — no frontend increment.
M14.3 journal-entry browser
surfaces the new BHPH-payment
entries automatically with
descriptive `description` + line
memos. M14.2 trial balance
renders new 100000 / 123000 /
430000 activity. UI polish
(filter, drill-back, list column)
belongs to a separate M14 UX
polish milestone.

## Files touched at M16.0

Modified:

1. `docs/roadmap/MILESTONE_16_
   PLANNING.md` — expanded from
   ~330-line skeleton to full
   memo (~1,010 lines). Frontmatter
   `status: draft` → `status:
   active`; `milestone_name` set
   to "M12 BHPH payment GL post";
   `sources` list extended with
   `BHPH_OPERATIONS_MAPPING.md` +
   `ACCOUNTING_DEPARTMENT_MAPPING.md`
   + M13 planning/retrospective +
   M14 retrospective. §0.a change
   log populated with all six §5
   confirmations + streak-update
   line. §1 business questions
   expanded to four operator-
   workflow questions (Q1 GL
   reflects the payment / Q2 BHPH
   interest income at the GL /
   Q3 BHPH Notes Receivable
   amortizes / Q4 cash flow into
   GL). §2 existing primitives
   enumerated (M13.1 substrate +
   M13.2 template + M14 UI). §3
   deferrals locked at 16 (11
   M16-specific + 5 universal).
   §5.a-§5.f all `[RESOLVED at
   SESSION_142 open]`. §7
   sequenced one code increment +
   one close-out (three total
   including this planning
   session).
2. `00-START-NEXT-SESSION.md` —
   overwritten with M16.1
   priority per doc-governance
   session-lifecycle rule.

Created:

3. `docs/handoffs/SESSION_142_
   m16_inc0_planning.md` — this
   handoff.

## Verifications passed at SESSION_142 close

- `git status` (before this
  handoff commit) — M15.2 commit
  landed at SESSION_141 close
  (`adda63d`); M16.0 planning
  docs pending commit.
- `git log --oneline -5` — top
  is `adda63d Milestone 15
  shipped — M9 sale-booking GL
  post (SESSION_139-141)`.
- `python3 manage.py test dealer_ai`
  → **4,296 pass, 1 skipped, 0
  fail** (unchanged — planning-
  only session).
- `cd frontend && npm test` →
  **122 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → PONG.

## What SESSION_143 (M16.1) picks up

Per `MILESTONE_16_PLANNING.md` §7
M16.1:

1. **Migration `0045_m161_bhph_
   payment_posted_at.py`** —
   adds `BhphPayment.posted_at
   DateTimeField(null=True,
   blank=True, db_index=True)`
   per §5.d Option A.
2. **New module `services/
   accounting/bhph_payment.py`**
   mirroring `vehicle_cost.py`
   shape:
   - `detect_unposted_bhph_
     payments(*, dealership)` —
     pure query.
   - `post_bhph_payment_journal(
     *, dealership, bhph_payment,
     posted_at=None)` — atomic
     sibling verb composing 2-
     or 3-line JournalEntry per
     §5.c + §5.e Option A.
   - `post_all_unposted_bhph_
     payments_for_dealership(*,
     dealership, now=None)` —
     orchestrator matching
     M13.2's return-shape.
3. **Extend `services/accounting/
   tasks.py`** with:
   - `post_bhph_payment_journals_
     for_dealership(*,
     dealership_id)`.
   - `post_bhph_payment_journals_
     for_all_tenants()`.
4. **Add `bhph-payment-post-
   daily-11-00` entry to
   `CELERY_BEAT_SCHEDULE`** in
   `dealer_kit/settings.py` at
   `crontab(hour=11, minute=0)`.
5. **Extend `services/accounting/
   __init__.py`** `__all__` for
   the new verbs.
6. **~25-30 focused tests** in
   new `tests/test_m161_bhph_
   payment_gl.py` — happy path
   (principal+interest), zero-
   interest (2-line), zero-
   principal (2-line), cross-
   tenant guard, missing account,
   orchestrator + per-row
   failure isolation, idempotency,
   Celery-task wiring, beat
   schedule registration, trial
   balance reflection.

**M16.1 target totals.**

- Backend baseline: 4,296 →
  ~4,321-4,326 (+25-30 tests,
  zero regressions).
- Frontend Vitest: 122
  (unchanged — no frontend at
  M16 per §5.f Option A).
- Migrations: `0043`–`0044` →
  `0043`–`0045` (+1).
- Tenancy carriers: 47
  (unchanged — BhphPayment
  gains a column, not a new
  model).
- DRF admin surface: 104
  (unchanged — no endpoint
  changes).
- Frontend operator routes:
  20 (unchanged).
- Permission classes: 8
  (unchanged — zero-drift
  streak extends to eight
  consecutive milestones).
- Celery-beat task families:
  9 → 10 (new bhph-payment
  daily entry at 11:00).

## Explicit non-goals for SESSION_143 (M16.1)

- ❌ Do NOT ship M16.2+ docs at
  M16.1 (close-out is a
  separate session).
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
  additive `posted_at` column.
- ❌ Do NOT force-push or amend
  any earlier commits.

## Push authorization

M16.0 is a docs-only session —
one commit will land at
SESSION_142 close containing:

- `docs/roadmap/MILESTONE_16_PLANNING.md`
  (expanded from skeleton;
  frontmatter flip + all §5
  decisions locked)
- `docs/handoffs/SESSION_142_m16_inc0_planning.md`
- `00-START-NEXT-SESSION.md`
  (overwritten with M16.1
  priority)

User authorization required before
commit + push per standing user
directive on all doc-only commits.
