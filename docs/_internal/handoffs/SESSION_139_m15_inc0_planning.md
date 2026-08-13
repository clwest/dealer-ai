---
title: "SESSION_139 handoff — Milestone 15 · Increment 0 (M15.0 — Planning refinement + target selection)"
status: historical
type: handoff
date: 2026-08-02
session: 139
milestone: 15
milestone_status: planning
milestone_name: "M9 sale-booking GL post"
increment: 0
increment_status: shipped
commit: TBD
---

# SESSION_139 — Milestone 15 · Increment 0 (M15.0 — Planning refinement + target selection)

## What shipped

Planning-only session per M15 §7
sequencing draft. Two documentation
artifacts updated:

1. **`docs/roadmap/MILESTONE_15_
   PLANNING.md`** — expanded from
   skeleton (drafted at M14.5 close)
   to active memo. Frontmatter
   `status: draft` → `status:
   active`; `milestone_name` set to
   "M9 sale-booking GL post". All six
   §5 load-bearing decisions resolved
   with full recommendations +
   rationale. §1 business questions
   expanded to four operator-workflow
   questions (Q1 does the GL reflect
   the sale / Q2 which receivable /
   Q3 gross-profit at the GL / Q4
   Recon WIP clear). §3 deferrals
   locked at 17 (12 M15-specific + 5
   universal). §7 sequencing locks
   two code increments + one close-
   out (three total including this
   planning increment — smaller
   surface than M14's five per
   backend-only scope).
2. **`00-START-NEXT-SESSION.md`**
   overwritten with M15.1 priority
   (backend sale-booking GL post via
   sibling-service call inside
   `record_sale`).

**Milestone 15 target confirmed:
Option A — M9 sale-booking GL post.**
Locks the sync `@transaction.atomic`
sibling-service call inside
`services/sale/record_sale` per M13
§5.d Option C hybrid posture. Every
sold vehicle produces a matching
balanced JournalEntry via
`services/accounting/post_journal_entry`.
The M14.3 journal-entry browser
surfaces the resulting entries
automatically with `posted_by_username`
populated from the sale-booking user
— zero frontend increment at M15.

## §5 decisions confirmed at SESSION_139 open

All six confirmed **as-recommended**
per the M5-M14 pattern. Recorded in
`MILESTONE_15_PLANNING.md` §0.a
change log.

| Decision | Recommendation | Confirmed |
|---|---|---|
| §5.a Milestone scope | Option A — M9 sale-booking GL post | ✅ |
| §5.b Finance-type → receivable | Option A — three-way branch (cash → 100000; retail → 120000 CIT; bhph → 123000 BHPH Notes Rec) | ✅ |
| §5.c Zero-total-investment sales | Option A — skip COGS pair, post revenue-only, log warning | ✅ |
| §5.d Un-posted VehicleCost at sale | Option A — flush synchronously via `post_vehicle_cost_journal` inside `record_sale` | ✅ |
| §5.e Post-sale VehicleCost | Option A — accept phantom Recon WIP balance; defer variance handling | ✅ |
| §5.f Operator UI at M15 | Option A — no UI; M14.3 surfaces new entries automatically | ✅ |

**Streak update at M15.0 close: 58
planning-time as-recommended M5.1 →
M15.0.** Six consecutive milestones
now (M10 + M11 + M12 + M13 + M14 +
M15) with every §5 decision confirmed
as-recommended at planning-time open.

## Sequencing locked at §7

Three increments total. Backend +
frontend baselines projected:

| Increment | Session | Scope | Backend Δ | Frontend Δ |
|---|---|---|---|---|
| M15.0 | 139 | Planning + decision review | none | none |
| M15.1 | 140 | Backend: sale-booking GL post (new sibling module + `record_sale` extension + view `posted_by_user` propagation) | +25-30 tests | none |
| M15.2 | 141 | Close-out docs (retrospective + capability matrix §7p + roadmap flip + M16 planning skeleton) | none | none |

**Projected M15 close totals:**
- Backend: 4,277 → ~4,302-4,307
  (+25-30).
- Frontend Vitest: 122 (unchanged —
  no frontend touched at M15).
- DRF admin surface: 104 (unchanged
  — no new endpoints).
- Frontend operator routes: 20
  (unchanged — no new routes).
- Tenancy carriers: 47 (unchanged —
  no new models).
- Permission classes: 8 (unchanged —
  zero-drift streak extends to seven
  consecutive milestones).
- Celery-beat task families: 9
  (unchanged — sale booking is
  operator intent, not a detector).
- Migrations: none (no schema
  changes).

## Files touched

1. `docs/roadmap/MILESTONE_15_
   PLANNING.md` — draft skeleton
   (~305 lines) → active memo
   (~635 lines). Frontmatter
   updated (`status: draft` →
   `status: active`; `milestone_name`
   set); §0.a change log populated
   with six §5 confirmations + streak
   extension to 58; §1 + §2 + §3 +
   §4 + §5 (5.a-5.f) + §6 + §7 all
   expanded.
2. `00-START-NEXT-SESSION.md` —
   full overwrite with M15.1
   priority per doc-governance
   session-lifecycle rule.
3. `docs/handoffs/SESSION_139_m15
   _inc0_planning.md` — this
   handoff (new).

## Verifications passed at session open

- `git status` clean (main +
  origin/main aligned).
- `git log --oneline -7` — top =
  `8b0802b Milestone 14 shipped —
  Operator UI for accounting
  substrate (SESSION_133-138)`.
- `git log origin/main..HEAD
  --oneline` — empty (all M14
  commits pushed).
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `redis-cli ping` → `PONG`.
- Full test-suite runs deferred to
  M15.1 open per planning-only
  session posture (no code changes
  at M15.0). Baseline stands at
  4,277 pass / 122 Vitest from
  SESSION_138 close.

Frontend baseline unchanged (no
frontend touched at M15.0).

## What SESSION_140 (M15.1) picks up

Per `MILESTONE_15_PLANNING.md` §7
Increment 1:

- **New module
  `backend/dealer_ai/services/
  accounting/sale_booking.py`** with
  one atomic sibling-service verb:
  `post_sale_booking_journal(*,
  dealership, sale,
  posted_by_user=None) ->
  JournalEntry`. Composes the
  finance-type-aware receivable line
  + revenue line + COGS line + Recon-
  WIP-clear line, then delegates to
  `post_journal_entry` for the
  balanced double-entry write.
  Account resolution via helper
  mirroring M13.2's
  `_lookup_required_account`
  (raises `MissingDefaultAccountError`
  when a required account is
  absent or inactive).

- **Finance-type → receivable
  account mapping** per §5.b Option
  A:
  - `SALE_FINANCE_TYPE_CASH` →
    `100000` Cash on Hand.
  - `SALE_FINANCE_TYPE_RETAIL` →
    `120000` Contracts in Transit.
  - `SALE_FINANCE_TYPE_BHPH` →
    `123000` BHPH Notes Receivable.

- **Zero-total-investment path**
  per §5.c Option A: when
  `total_investment == 0`, skip
  the COGS + Recon WIP pair; post
  only the receivable + revenue
  pair. Log a warning via
  `logging.getLogger("dealer_ai.
  accounting.sale_booking")` so the
  miss is discoverable.

- **Un-posted VehicleCost flush**
  per §5.d Option A: before the
  sale-booking journal posts,
  iterate any VehicleCost rows for
  the target vehicle with
  `posted_at__isnull=True AND
  is_estimate=False` and call
  `post_vehicle_cost_journal` on
  each. Same atomic transaction —
  either every prerequisite cost
  + the sale-booking entry all
  commit, or nothing does.

- **Extend
  `services/sale/computation.record_sale`**
  to accept `posted_by_user=None`
  (default preserves existing call
  sites) and invoke the flush +
  sale-booking calls after the
  Sale row is created but inside
  the existing
  `@transaction.atomic` block.

- **Extend `views_sale.py` create
  endpoint** to pass
  `request.user` through as
  `posted_by_user=request.user` so
  the JournalEntry's
  `posted_by_user` FK is populated
  (surfaces in the M14.3 browser).

- **Extend
  `services/accounting/__init__.py`**
  `__all__` for the new
  `post_sale_booking_journal` verb.

- **Focused tests (~25-30
  target):**
  - Cash finance-type → 100000
    debit + 400000 credit.
  - Retail finance-type → 120000
    debit + 400000 credit.
  - BHPH finance-type → 123000
    debit + 400000 credit.
  - COGS line uses 500000 debit +
    122000 credit for
    `total_investment`.
  - Balanced double-entry
    (`sum(debits) == sum(credits)`).
  - Cross-tenant guard (Vehicle in
    other tenant → error).
  - Zero-cost path per §5.c: only
    revenue-pair posted; warning
    logged.
  - Un-posted VehicleCost flush per
    §5.d: pending costs post before
    sale-booking entry.
  - `MissingDefaultAccountError`
    raised when any required
    account is inactive.
  - `posted_by_user` propagation
    from view through service into
    JournalEntry FK.
  - Atomic sibling posture: sale-
    booking failure rolls back the
    Sale row.
  - Idempotency: second
    `record_sale` on same Vehicle
    raises `SaleAlreadyExistsError`
    BEFORE any GL work.
  - M14.3 list endpoint returns the
    new sale-booking entries with
    `posted_by_username` populated.

- **Zero new migrations.** All
  five required accounts already
  seeded per Dealership by M13.1
  migration `0043`.

- **Zero new endpoints.** M9 sale
  create endpoint carries the GL
  post as a side effect.

- **Zero new post-LLM scrub
  stages.** M15 has no LLM path.

- **Tenancy carriers 47
  (unchanged).**

- **Permission classes 8
  (unchanged — zero-drift streak
  extends to seven consecutive
  milestones).**

- **DRF admin surface 104
  (unchanged).**

**Backend baseline target at M15.1
close:** ~4,302-4,307 pass (+25-30
tests, 0 regressions). Frontend
Vitest: 122 (unchanged).

## Explicit non-goals for SESSION_140

- ❌ Do NOT ship sales-tax posting
  (§3 item 1 deferral).
- ❌ Do NOT ship trade-in
  accounting (§3 item 2 deferral).
- ❌ Do NOT ship F&I product
  revenue at sale (§3 item 3 —
  separate milestone via M10
  substrate).
- ❌ Do NOT ship doc-fee revenue
  (§3 item 4 deferral).
- ❌ Do NOT ship reserve-receivable
  at sale (§3 item 5 deferral).
- ❌ Do NOT ship BHPH interest-
  accrual detector (§3 item 6 —
  separate M12+ milestone).
- ❌ Do NOT add
  `SALE_FINANCE_TYPE_WHOLESALE`
  vocab (§3 item 7 deferral).
- ❌ Do NOT wire sale-reversal to
  the M14.4 JournalEntry reversal
  verb (§3 item 8 — needs
  operational contract first).
- ❌ Do NOT add JournalEntry FK to
  Sale (§3 item 9 deferral —
  operator drill via
  `description` text is sufficient
  at MVP).
- ❌ Do NOT ship the CIT-to-Cash
  funding workflow (§3 item 10 —
  separate payments-inbound
  milestone).
- ❌ Do NOT modify M13.2 detector
  behavior for post-sale
  VehicleCost rows (§3 item 11 —
  variance handling defers).
- ❌ Do NOT ship GL-derived
  reporting analytics (§3 item 12
  deferral).
- ❌ Do NOT modify M1-M14
  business logic beyond the
  additive changes to `record_sale`
  and `views_sale.py`.
- ❌ Do NOT ship any frontend
  changes (§5.f Option A — M15 is
  backend-only).

## Anchors that win on conflict at SESSION_140 open

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_15_PLANNING.md`
   (this session's target)
6. `docs/roadmap/MILESTONE_14_RETROSPECTIVE.md`
   §6 (ten lessons carry into M15+)
7. `docs/roadmap/MILESTONE_13_PLANNING.md`
   §5.d (Option C hybrid GL trigger
   posture — M15.1 is the sync half)
8. `docs/roadmap/MILESTONE_13_RETROSPECTIVE.md`
   §8 (M13 unblocked work anchor)
9. `docs/CAPABILITY_MATRIX.md` §7o
10. `docs/handoffs/SESSION_139_m15_inc0_planning.md`
    (this handoff)
11. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
    §3.5 CIT + §3.13 sales tax
    (§3 item 1 deferral rationale)
12. Existing implementations —
    `services/sale/computation.py`
    (M9), `services/accounting/journal.py`
    (M13.1), `services/accounting/
    vehicle_cost.py` (M13.2),
    `services/accounting/default_coa.py`
    (M13.1).

## Push authorization

M15.0 is a planning-only session —
one docs commit will land at
SESSION_139 close containing:

- `docs/roadmap/MILESTONE_15_PLANNING.md`
- `docs/handoffs/SESSION_139_m15_inc0_planning.md`
- `00-START-NEXT-SESSION.md`

User authorization required before
commit + push per standing user
directive on all doc-only commits.
