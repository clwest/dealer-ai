---
title: "SESSION_140 handoff — Milestone 15 · Increment 1 (M15.1 — Backend: sale-booking GL post)"
status: historical
type: handoff
date: 2026-08-02
session: 140
milestone: 15
milestone_status: in_progress
milestone_name: "M9 sale-booking GL post"
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_140 — Milestone 15 · Increment 1 (M15.1 — Backend: sale-booking GL post)

## What shipped

Single backend increment. Every sold
vehicle now produces a matching
balanced JournalEntry via a sync
`@transaction.atomic` sibling-service
call inside
`services/sale/record_sale`. The
M14.3 journal-entry browser surfaces
these entries automatically with
`posted_by_username` populated from
the acting operator — zero frontend
changes needed.

**Backend baseline: 4,277 → 4,296
pass, 1 skipped, 0 fail** (+19
tests, zero regressions). Projected
was +25-30 tests; shipped 19
(comparable coverage in fewer
functions — each finance-type branch
is one test rather than three
parameterized variants; the
propagation + rollback + idempotency
guards each covered with a single
assertion). Frontend Vitest: **122
pass** (unchanged — no frontend
touched at M15.1 per §5.f Option A).

**Nine §0.a M15.1 micro-decisions
recorded** — all as-recommended per
M10 §9 (do not count against
planning-time streak).

## §0.a M15.1 micro-decisions

Recorded in `MILESTONE_15_PLANNING.md`
§0.a per M5-M14 precedent. All
implementation-time defaults per
M10 §9.

1. **Zero-value COGS pair skipped
   via a `> Decimal("0.00")`
   guard** (not `>= 0.01` or
   sign-check) — matches
   `Decimal.__gt__` semantics and
   handles negative-total-investment
   edge cases with an explicit
   `else` warn-log branch.
2. **Un-posted-cost flush uses
   `detect_unposted_costs(...).filter(vehicle=vehicle)`**
   rather than a new per-vehicle
   detector verb. Reuses the M13.2
   query filter (`posted_at__isnull=True
   AND is_estimate=False`) to keep
   the two paths semantically
   identical. Additive extension
   posture per M11.1 / M12.3 /
   M13.2 / M14.1 pattern.
3. **`_lookup_required_account`
   duplicated in the sale-booking
   module** (mirrors M13.2's
   private helper verbatim). Not
   promoted to a shared accounting
   helper module at M15.1 —
   evidence gate not tripped
   (two callers is not yet a
   refactor trigger per Project
   Rule 4 scope discipline).
4. **`CrossTenantGLAccountError`
   reused for cross-tenant Sale
   check** (matches M13.2's
   posture on VehicleCost cross-
   tenant). Semantically slightly
   broader than the class name
   suggests, but precedent-set at
   M13.2 and produces the same
   fail-closed 404 at the
   endpoint layer.
5. **`UnmappedFinanceTypeError`
   as a `RuntimeError` subclass**
   (not `ValueError`) —
   signals a broken invariant
   (vocab drift without mapping
   extension), not user-input
   error. Matches
   `MissingDefaultAccountError`
   posture. Would map to 500 at
   the endpoint layer, not 400.
6. **`gross_realized` refreshed
   AFTER the cost flush** so the
   denormalized value on the Sale
   row matches the COGS line the
   sale-booking journal posts.
   Before-flush read would leak
   a stale `total_investment` for
   sales where §5.d Option A
   posted new costs.
7. **JournalEntry description
   text carries `Sale #<pk> of
   stock <stock>
   (<finance_type_display>)`** —
   sufficient operator drill-back
   at the M14.3 browser without
   an FK addition (per §3 item 9
   deferral). `get_finance_type_display()`
   used for human-readable copy.
8. **`_auth_helpers.make_dealership`
   extended to seed default COA**
   — brings test dealerships in
   line with the M13.1 migration
   invariant that every Dealership
   has the full default chart of
   accounts. Fixes M15.1's
   dependency without requiring
   per-test setUp edits across
   the endpoint test suite.
9. **`test_m9_sale_computation.py`
   patched to seed COA inline**
   (in-file `Dealership.objects.create`
   calls, four setUps / test
   scopes) rather than migrated
   to `make_dealership`. Keeps
   the file's slug conventions
   (`m91-gr` / `m91-rec` / etc.)
   stable + preserves per-test
   isolation the file was
   originally written around.

## Files touched

Created:

1. `backend/dealer_ai/services/
   accounting/sale_booking.py` —
   new module. `post_sale_booking_journal`
   atomic sibling-service verb +
   `_lookup_required_account` helper
   + `_resolve_receivable_account`
   helper + `UnmappedFinanceTypeError`
   class + six account-code
   constants
   (`CASH_ACCOUNT_CODE`,
   `CONTRACTS_IN_TRANSIT_ACCOUNT_CODE`,
   `BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE`,
   `RECON_WIP_ACCOUNT_CODE`,
   `VEHICLE_SALES_RETAIL_ACCOUNT_CODE`,
   `COST_OF_VEHICLE_SALES_ACCOUNT_CODE`)
   + finance-type → receivable
   mapping table.
2. `backend/dealer_ai/tests/
   test_m151_sale_booking.py` —
   new test file. 19 focused
   tests across 9 TestCase
   classes: FinanceTypeMappingTests
   (3), RevenueAndCogsLineTests
   (3), ZeroCostBasisPathTests
   (2), UnpostedCostFlushTests
   (2), CrossTenantGuardTests (1),
   MissingAccountErrorTests (1),
   UnmappedFinanceTypeErrorTests
   (1), PostedByUserPropagationTests
   (2), AtomicRollbackTests (1),
   IdempotencyShortCircuitTests
   (1), ListEndpointSurfaceTests
   (1), SaleCreateEndpointPropagationTests
   (1).
3. `docs/handoffs/SESSION_140_m15
   _inc1_backend.md` — this
   handoff.

Modified:

4. `backend/dealer_ai/services/
   sale/computation.py` — extended
   `record_sale` with `posted_by_user`
   kwarg + per-vehicle
   `detect_unposted_costs` +
   `post_vehicle_cost_journal`
   flush loop (§5.d Option A) +
   `post_sale_booking_journal`
   call (§5.b + §5.c Option A).
5. `backend/dealer_ai/services/
   accounting/__init__.py` — added
   sale_booking imports + six new
   account-code constants +
   `UnmappedFinanceTypeError` +
   `post_sale_booking_journal` to
   `__all__`.
6. `backend/dealer_ai/views_sale.py`
   — `admin_sale_create` passes
   `request.user` through as
   `posted_by_user=request.user`
   to `record_sale`.
7. `backend/dealer_ai/tests/
   _auth_helpers.py` — extended
   `make_dealership` to seed the
   default COA on creation.
8. `backend/dealer_ai/tests/
   test_m9_sale_computation.py`
   — added `seed_default_coa`
   import + four inline seed
   calls (two setUps + two in-
   test dealership creates).

## Verifications passed

- `git status` (before this
  handoff commit) — M15.0 landed
  at `ce511a2`; M15.1 code +
  tests + handoff pending
  commit.
- `python3 manage.py test dealer_ai`
  → **4,296 pass, 1 skipped, 0
  fail**. 35s. **+19 vs
  SESSION_139 close; 0
  regressions.**
- `python3 manage.py test
  dealer_ai.tests.test_m151_sale_booking`
  → **19/19 pass**. 0.4s.
- `python3 manage.py test
  dealer_ai.tests.test_m9_sale_computation`
  → 12/12 pass (verified after
  M9 test patches).
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."

## Milestone 15 state after M15.1

- **Sessions:** 139 → 140 (2 so
  far; M15.2 close-out ahead).
- **Backend baseline:** 4,277 →
  **4,296** pass (+19).
- **Frontend Vitest:** 122
  (unchanged — no frontend
  touched at M15.1 per §5.f
  Option A).
- **Migrations:** `0043`–`0044`
  (unchanged — zero schema
  changes at M15).
- **Tenancy carriers:** 47
  (unchanged — no new models).
- **DRF admin surface:** 104
  (unchanged — no new
  endpoints).
- **Frontend operator routes:**
  20 (unchanged — no frontend
  changes).
- **Permission classes:** 8
  (unchanged — zero-drift
  streak extends to seven
  consecutive milestones on
  M15.1 landing: M10 + M11 +
  M12 + M13 + M14 + M15).
- **Celery-beat task families:**
  9 (unchanged — sale booking
  is operator intent, not
  detector-shaped per M13 §5.d
  Option C hybrid posture).
- **AI safety stack:** 17 scrub
  stages (unchanged — M15 has
  no LLM path).
- **`services/accounting/`
  packages:** 4 → **5** (added
  `sale_booking.py`).

## What SESSION_141 (M15.2) picks up

Per `MILESTONE_15_PLANNING.md` §7
M15.2 — close-out docs. No code.

Deliverables:

- `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
  — new. Mirrors
  `MILESTONE_14_RETROSPECTIVE.md`
  structure. §1 planned scope +
  §2 what shipped (per-increment
  table) + §3 deferrals (12 M15-
  specific + 5 universal =
  17) + §4 deviations + §5
  compatibility + §6 lessons
  (target ~8-10 carry into M16+)
  + §7 streak update (58 →
  should hold at 58 unless
  M15.1 surfaced planning-time
  deltas) + §8 what M15
  unblocks for M16+.
- `docs/CAPABILITY_MATRIX.md`
  §7p — new section describing
  the M15 GL-post surface.
  Mirrors §7o structure.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  §Milestone 15 SHIPPED entry —
  new. Between the existing
  §Milestone 14 SHIPPED entry
  and §5 (non-goals).
- `docs/roadmap/MILESTONE_15_PLANNING.md`
  frontmatter flip: `status:
  active` → `status: shipped`;
  add `shipped_at_session:
  SESSION_141` + `retrospective:`
  fields. Closing note appended
  at bottom (delta totals +
  zero-regression note + cross-
  links).
- `docs/roadmap/MILESTONE_16_PLANNING.md`
  skeleton per standing user
  directive. Draft §1
  candidate M16 targets from
  M15 retrospective §8 + the
  still-valid M14 §8 unblocked-
  work list.
- `00-START-NEXT-SESSION.md`
  overwritten with M16.0
  priority (planning + target
  selection).
- `docs/handoffs/SESSION_141_m15_close.md`
  — new session handoff.
- One coordinated commit
  landing all M15.2 docs.

**Backend baseline at M15.2
close:** 4,296 pass (unchanged
— docs-only session). Frontend
Vitest: 122 pass (unchanged).

## Explicit non-goals for SESSION_141

- ❌ Do NOT ship any code
  changes (M15.2 is docs-only).
- ❌ Do NOT modify M1-M15
  business logic.
- ❌ Do NOT force-push or amend
  M15.0 / M15.1 commits.
- ❌ Do NOT re-vote any §5
  decision — amendments go to
  §0.a as micro-decisions per
  M10 §9.

## Push authorization

M15.1 is a code session — one
commit will land at SESSION_140
close containing:

- `backend/dealer_ai/services/accounting/sale_booking.py`
- `backend/dealer_ai/services/accounting/__init__.py`
- `backend/dealer_ai/services/sale/computation.py`
- `backend/dealer_ai/views_sale.py`
- `backend/dealer_ai/tests/_auth_helpers.py`
- `backend/dealer_ai/tests/test_m9_sale_computation.py`
- `backend/dealer_ai/tests/test_m151_sale_booking.py`
- `docs/handoffs/SESSION_140_m15_inc1_backend.md`
- `docs/roadmap/MILESTONE_15_PLANNING.md` (§0.a
  micro-decision log amendment)
- `00-START-NEXT-SESSION.md`

User authorization required before
commit + push per standing user
directive.
