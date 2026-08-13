---
title: "Milestone 2 — Retrospective"
status: shipped
type: retrospective
date: 2026-07-31
sessions: SESSION_045 → SESSION_054
milestone: 2
milestone_name: "Vehicle investment ledger"
related:
  - docs/roadmap/MILESTONE_2_PLANNING.md
  - docs/roadmap/MILESTONE_1_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md §7c
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 2
---

# Milestone 2 — Retrospective

Written at Milestone 2 close (SESSION_054). Records what was
planned, what shipped, what deviated and why, and the lessons that
should shape Milestone 3 and beyond. Mirrors the M1 retrospective
structure at `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md`.

## 1. What was planned

`MILESTONE_2_PLANNING.md` at SESSION_045 defined the milestone as
answering two operational questions for any stock number: *"what
do we have invested?"* and *"what's the projected front-end gross
at current asking price?"*. §1.0 enumerated six specific business
questions from the research corpus (INVENTORY_ACQUISITION §4/§5/§14/§15,
ACCOUNTING §2.12/§2.14/§2.15, VCP Phase 1) that the ledger must
answer. §1 followed with seven design-memo entries — one per
subsystem the milestone would ship: acquisition record
(`VehicleAcquisition`), cost ledger (`VehicleCost`), computed
gross properties on `Vehicle`, floor-plan interest accrual
mechanism, acquisition-price scrub, operator ledger UI, and a §1.7
"what M2 enables for future milestones" statement to keep the
scope focused. §3 was the compatibility checklist Milestone 2 had
to uphold; §5 named the deferrals (`expected_gross` computed from
estimated remaining, `Vendor` FK, automated curtailment, tenant-
scoped `stock_number` uniqueness, recon-manager access,
aging-alert recommended actions, multi-photo storage, async
scheduling, cost update/delete workflows, prod deployment).

Original §7 increment sequencing (§7.a in the shipped doc) called
for three increments — M2.1 schema, M2.2 API+service+safety+
accrual, M2.3 operator UI + closeout. That plan was course-
corrected in-flight (see §3 below).

## 2. What shipped

Every §3 compatibility item verified true; details in the
annotated checklist at `MILESTONE_2_PLANNING.md` §3. Summary of
the shipped substrate:

| Layer | Shipped surface | Session | Commit |
|---|---|---|---|
| Models — VehicleAcquisition + VehicleCost | `dealer_ai/models.py` + migrations `0012`, `0013` + admin + `SOURCE_*` × 8 + `CATEGORY_*` × 26 + `DATABASES["migration_check"]` alias per M1 lesson 2 | 046 (M2.1) | `795fee4` + `882b8e5` |
| Deterministic ledger service | `services/vehicle_ledger.py` (`record_acquisition` upsert / `add_cost` immutable / `compute_totals` deterministic / `category_group_of` classifier / `CrossTenantLedgerError` guard / `LedgerTotals` frozen dataclass / `ZERO`) + category groupings (`FLOORING/RECON/ADMIN/PHOTOGRAPHY_CATEGORIES`) | 047 (M2.2) | `0d40b6b` + `de9b565` |
| Vehicle-as-read-model | `@cached_property ledger_totals` + 9 delegator `@property` accessors + `days_in_inventory` (temporal, returns `None` when no acquisition) | 048 (M2.3) | `e25ab4d` + `c2e0ba3` |
| Financial math + APR configuration | `services/payment_engine.py::daily_floor_plan_interest` (pure, 365-day, ROUND_HALF_UP) + `DealerOnboardingProfile.floor_plan_apr` + migration `0014` + `services/dealer_config.py::get_floor_plan_apr` + `settings.py::DEALER_AI_FLOOR_PLAN_APR` env | 049 (M2.4a) | `f8cd0b2` + `ba5aec9` |
| Accrual command | `manage.py accrue_floor_plan_interest --dealership=<slug> [--as-of=DATE] [--dry-run]` (plan/execute split via `AccrualPlan`; workflow-owned idempotency via `ACCRUAL:<date>` reference tag; whole-run atomic; posts via `add_cost` only) | 050 (M2.4b) | `30ff9ee` + `eafef8c` |
| Acquisition-price safety scrub | `services/llm_safety.py::_scrub_acquisition_price` + 12 verbal-framing patterns + branch in `apply_post_llm_scrubs` firing on every `kind` | 051 (M2.5) | `ea0ee04` + `8de3540` |
| Admin API (three endpoints + serializers) | `views.py::admin_vehicle_ledger` (GET) + `admin_vehicle_acquisition_upsert` (POST) + `admin_vehicle_cost_create` (POST) + serializers (four output + two input) + URL registrations. Reuses M1 · 4D `IsSalesManagerOrOwnerAtActiveDealership` unchanged | 052 (M2.6) | `9e5f6d7` + `1448e31` |
| Operator ledger UI | `frontend/src/pages/VehicleLedgerPage.tsx` at `/dealer-ai-inventory/:stock/ledger` inside `<RequireAuth>` + three typed `lib/api.ts` helpers via `authFetch` + "Ledger" button on operator inventory cards + role-gated write forms | 053 (M2.7) | `ce3817c` + `f20564f` |
| Milestone closeout | §3 walk with inline evidence + `CAPABILITY_MATRIX.md` §7c + `IMPLEMENTATION_ROADMAP.md` flip + this retrospective + `MILESTONE_2_PLANNING.md` frontmatter → shipped | 054 (M2.8) | (this session) |

**Test baseline:** 1,466 → **1,753 pass** (+287), 1 skipped, 0
fail across the milestone. Zero regressions. No test suppressed
with `@skip` to make the baseline pass. Frontend `npx tsc
--noEmit` clean; `npx vite build` clean (same pre-existing 524KB
chunk warning as SESSION_044).

## 3. Sequencing refinements

Three material sequencing changes from the SESSION_045
plan. Each was course-corrected in flight based on user brief
guidance:

1. **M2.1 narrowed from "persistence + service skeleton" to
   "persistence only" (SESSION_046 brief).** The original §7
   M2.1 scope bundled `services/vehicle_ledger.py` skeleton +
   `Vehicle` `@property` accessors alongside the model layer. The
   SESSION_046 brief explicitly narrowed: *"Do not implement
   business logic. This is only the persistence layer."* The
   service skeleton absorbed into M2.2. Rationale: cleaner
   separation between schema and service; the ledger tables can
   be reviewed independently of any business-rule commitments.

2. **The proposed 12-deliverable M2.2 was rejected (SESSION_047
   brief), replaced with an 8-increment sequence (M2.1–M2.8).**
   The M2.1 handoff proposed a M2.2 that would ship: ledger
   business logic + Vehicle computed properties + API surfaces +
   authorization + tenant scoping + acquisition-price safety +
   floor-plan math + floor-plan configuration + accrual command
   behavior. The SESSION_047 brief correctly identified this as
   "too many independent concerns" combined into one increment.
   The refined sequence lives in `MILESTONE_2_PLANNING.md` §7.b
   and is what actually shipped. Every subsequent increment was
   named and scoped independently.

3. **M2.4 split into M2.4a (financial math) + M2.4b (accrual
   workflow) (SESSION_049 brief).** The original M2.4 bundled
   `daily_floor_plan_interest` math + APR configuration + the
   accrual management command. The SESSION_049 brief said:
   *"combines three different concerns: financial mathematics,
   dealership configuration, operational batch processing."* The
   split kept the engine pure and testable in isolation
   (SESSION_049) before wiring the workflow around it
   (SESSION_050). This was the same three-concerns-in-one pattern
   the SESSION_047 brief had rejected — the SESSION_049 brief
   caught it recurring and made the same call again.

Each course-correction cost one session but paid for itself in
the review clarity of the shipped surface and in test isolation.

## 4. Intentional deviations

Four documented deviations from the shipped-as-planned expectation:

1. **`total_investment` semantic contract locked at M2.2 to exclude
   estimates.** Planning §1.3 originally left the treatment of
   `is_estimate=True` rows in `total_investment` ambiguous. The
   SESSION_047 brief made a strong recommendation: *"actual_investment
   includes only is_estimate=False. estimated_remaining includes
   only is_estimate=True. projected_total_investment =
   actual_investment + estimated_remaining. Do not label
   estimated spending as money already invested."* Adopted
   verbatim. This is now the recorded contract every downstream
   milestone inherits. Locked by
   `ComputeTotalsActualVsEstimated` (5 tests) at M2.2 and
   preserved at the API + UI layers.

2. **`days_in_inventory` returns `None` when no acquisition
   exists (SESSION_048).** Original planning §1.3 left the
   fallback shape open. SESSION_048 chose `None` over any
   fallback (like `imported_at`) because a fallback would produce
   wrong aging buckets in the ledger UI + accrual command for
   dealers onboarded with existing inventory (where `imported_at`
   is when the row hit our DB, not when the vehicle physically
   arrived). `None` forces the operator to record acquisition
   first — a documented invariant.

3. **"Stage 17" numbered-stage terminology removed from code
   (SESSION_051).** The SESSION_051 brief flagged that
   *"the safety stack count is documentation, not necessarily a
   code contract. Do not introduce ordering dependencies based
   on a number that future scrubs could invalidate."* The M2.5
   scrub is named `acquisition_price` in `scrubs_fired` — that
   is the durable identifier. The planning doc §1.5 heading was
   renamed from "17th safety pipeline stage" to
   "defense-in-depth" to preserve the same discipline in the
   documentation layer.

4. **M2.6 defensive scrub patterns for "we paid" and "our cost"
   never fire under current conditions.** The pre-existing
   `_RESPONSE_FORBIDDEN_PATTERNS` in `chat_engine.py` (from M1)
   catches these phrases via `detect_unsafe_response` — which
   fires FIRST in `apply_post_llm_scrubs` and short-circuits
   before the M2.5 acquisition-price scrub runs. The M2.5 scrub
   still carries patterns for these phrases as defensive
   redundancy: if a future session loosens the pre-existing
   detector, M2.5 provides defense-in-depth. Documented in the
   scrub module's comment block + the SESSION_051 handoff.

## 5. Regressions avoided

The compatibility contract held in full. Explicit rechecks
recorded in `MILESTONE_2_PLANNING.md` §3 (see the "verified
inline" annotations). Load-bearing items:

- **All 16 pre-existing safety-pipeline stages unchanged.** M2.5
  added a 17th (acquisition-price) without touching any
  existing scrub. Every pre-existing scrub test passes at the
  1,753 baseline.
- **Customer chat, vehicle Q&A, ad-copy, follow-up drafts,
  budget-fit classification, manager coaching Shape A/B, indie
  prohibited copy** — all unchanged, all tests passing.
- **Franchise env-override + Copper Canyon defaults** — verified
  via fresh-process smoke at SESSION_054 close (mirroring the
  SESSION_044 M1 · 4F pattern).
- **Public routes remain unauthenticated.** Verified live at
  SESSION_054: `/`, `/assistant`, `/showroom`,
  `/embed/assistant`, `/login`, `/onboarding/profile/` (GET),
  `/salespeople/`, `/vehicles/<id>/` all return 200 without a
  session.
- **`DEFAULT_PERMISSION_CLASSES` remains unset.** Verified by
  two tests + runtime probe.
- **Ledger data isolation from customer surfaces.** M2.6
  `PublicSurfacesNeverExposeLedgerData` (5 tests, 7-keyword
  scan) + runtime-verified at SESSION_054 against the live
  backend.
- **Milestone 1 substrate byte-for-byte preserved.** No file in
  `services/tenancy.py`, `dealer_ai/permissions.py`,
  `dealer_ai/models.py::Dealership / UserDealershipRole`, or
  M1 migrations `0001`–`0011` was modified by any M2 session.

## 6. Lessons learned

The lessons the next milestone should carry forward:

1. **Persistence, service, read model, math, workflow, safety,
   API, and UI are safer as separate increments.** The
   M2.1→M2.7 sequence made every layer independently reviewable
   and testable. Two attempted "combine multiple concerns into
   one large session" scopes (proposed M2.2 at SESSION_046
   handoff; original M2.4 at SESSION_049 brief) were correctly
   rejected — the reasoning generalizes: no session should ship
   two independent responsibilities at once unless one truly
   cannot be tested without the other.

2. **Deferred work must be redistributed into small increments,
   not accumulated into an oversized next increment.** The
   SESSION_047 course-correction is the model: when narrowing
   scope defers work, RE-plan the deferred work into small
   sessions of its own — do NOT let it accumulate into the
   next increment's scope.

3. **Actual investment and estimated remaining cost must remain
   semantically separate.** M2.2's `total_investment` excludes
   estimates by contract, `estimated_cost_total` isolates them,
   `projected_total_investment` sums both. Every downstream
   layer (M2.3 property, M2.6 API, M2.7 UI) preserves the
   distinction with explicit labels. Labeling projected spend as
   invested money would mislead operators making disposition
   decisions — the `is_estimate` field on `VehicleCost` exists
   precisely because this distinction matters at decision time.

4. **Vehicle is the read model; the ledger service is the
   business/write layer.** M2.3 made this explicit — `Vehicle`
   exposes ledger data via `@cached_property` + `@property`
   delegators to `services/vehicle_ledger.compute_totals`. No
   business logic (aggregation, category grouping, cross-tenant
   guards, money math) lives on `Vehicle`. Same shape carried to
   the frontend — the operator UI page consumes the API contract
   without recomputing totals.

5. **Immutable cost rows plus reversing entries preserve
   operational history.** No M2 endpoint permits updating or
   deleting a `VehicleCost`. Corrections happen by posting a new
   row with the negative amount + a `reference` pointing at the
   original. Matches accounting practice
   (`ACCOUNTING_DEPARTMENT_MAPPING.md` §2.11) and removes an
   entire class of "when did that number change?" bugs.

6. **Financial math belongs in deterministic services and never
   in React or the LLM.** M2.4a's `daily_floor_plan_interest`
   is pure; the accrual command consumes it; the API projects
   the result; the UI displays what the backend returned. The
   frontend `formatMoney` helper is pure string manipulation
   with zero float arithmetic. The LLM never touches ledger
   data — the M2.5 scrub is defense in depth.

7. **Explicit workflow idempotency is stronger than relying only
   on mathematical zero-day behavior.** M2.4b's accrual command
   queries for an existing row with
   `reference=f"ACCRUAL:{as_of.isoformat()}"` BEFORE computing
   interest — belt on top of the engine's `days_elapsed <= 0 →
   Decimal("0.00")` suspenders. Same-day re-runs post ZERO new
   rows and increment `skipped_duplicate` in the summary.

8. **The accrual command's plan/execute split creates a future
   extension seam.** `AccrualPlan` is today a transient Python
   dataclass. Tomorrow it could become a persisted
   `AccrualEvent` model without changing the command's
   user-facing surface. The pattern applies to any workflow
   where the "what will happen" concept is distinct from the
   "make it happen" side effect.

9. **Currency strings at the API boundary prevent accidental
   JavaScript precision loss.** Every money field in the M2.6
   JSON contract is a fixed two-decimal-place string. The M2.7
   frontend stores currency as strings, submits currency as
   strings, and renders currency by string manipulation. Cent-
   level exactness is preserved end-to-end.

10. **A strong negative corpus is the load-bearing part of a
    financial-data safety scrub.** M2.5's 71 tests split ~2:1
    between positive (25 phrase families + 8 variants + 4 kinds
    + 3 misc) and negative (21 legitimate-customer-language
    cases). The negative corpus is what proves the scrub does
    not damage valid pricing, payment, trade, warranty, or
    budget language. The rule the SESSION_051 brief locked —
    *"favor false negatives over broad false positives"* — was
    the right call.

11. **Frontend manual/browser verification must not be marked
    complete when tooling cannot perform it.** M2.7 shipped
    with an honest "manual browser smoke deferred to operator
    verification" note in the handoff because the environment
    couldn't drive an interactive browser. SESSION_054 preserves
    that honesty in the annotated §3 (two frontend items retain
    "pending manual operator smoke" notes even though the
    server-side pathway is fully locked by tests). Falsely
    marking a manual step complete would corrupt the
    trustworthiness of every future §3 sweep.

## 7. Remaining deferred work

Recorded here so nothing gets rediscovered from source. Every
item stays in its authoritative deferral list (planning §5 +
this section).

**Explicit M2 §5 deferrals still deferred:**

- `expected_gross` computed property (requires
  `estimated_remaining_investment` — Milestone 3 ConditionReport
  scope).
- `Vendor` FK model on `VehicleCost` (Milestone 4).
- Automated curtailment scheduling (Milestone 7+ — needs lender
  integration or async).
- `recon_manager` read/write access on the ledger (Milestone 4
  when recon-manager workflows create cost entries).
- Aging-alert recommended actions (Milestone 8 operational
  intelligence).
- Tenant-scoped uniqueness on `Vehicle.stock_number` (milestone
  that first onboards a second live dealership).
- `Vehicle.is_available` → computed lifecycle (Milestone 5).
- `Vehicle.make="Ford"` default rename (opportunistic — M5 most
  likely).
- Multi-photo storage (S3-compatible + CDN) — Milestone 3
  ConditionReport concern or a pre-M3 half-milestone.
- Async / Celery for the accrual command (Milestone 7).
- Cost update / delete on `VehicleCost` (v1 corrections are
  reversing rows; revisit only if operator evidence surfaces
  friction).
- Full DMS-style deal recap (Milestones 9 + 13).
- Prod deployment as part of M2 (alongside first field-based
  milestone — M3 or M4 more likely).
- Bulk inventory-list optimization (per M2.3 handoff N+1
  preview — M2.6 API endpoints are detail-only; a future
  inventory-list page needs bulk aggregates).
- `floor_plan_apr` field in the operator Setup UI (deferred but
  M2.7-adjacent; land whenever the Setup UI takes its next
  extension).

**New deferrals surfaced during M2 implementation** (recorded so
they aren't rediscovered):

- **Complete interactive-browser smoke of M2.7 UI.** SESSION_053
  and SESSION_054 both could not drive an interactive browser.
  Server-side and static-analysis paths are locked; the 12-step
  click-through flow from the SESSION_053 brief remains queued
  for operator verification at first live use.
- **Grouping `views.py::_money_str` into a shared helper module.**
  M2.6 introduced this at the view layer. If future ledger-
  adjacent endpoints (M2.8+ hardening, M8 intelligence surfaces,
  M13 accounting reconciliation) need the same
  Decimal-quantize-and-string pattern, lift into a shared
  helper.
- **Fresh-DB seed script that includes ledger data.** The Copper
  Canyon demo seed (SESSION_030 Phase 3) does not create
  `VehicleAcquisition` or `VehicleCost` rows. Result: a fresh
  install's M2.7 ledger page shows every vehicle in the empty
  state. Not a bug — the models are greenfield — but a
  developer-experience improvement worth doing before the next
  demo cycle. Belongs in either M3 or a small
  developer-productivity increment.

**Post-Milestone-2 hardening candidates** (recorded now so the
first Milestone 3 session can decide whether to fold any of
them in):

- Playwright end-to-end tests for the M2.7 UI. Playwright is
  already in `frontend/package.json` devDependencies but has no
  config or test directory. Not blocking; complements manual
  operator smoke.
- Ledger-write audit logging. Currently `add_cost` and
  `record_acquisition` post rows silently. A structured audit
  event (M1 · 4D `services/audit.py` pattern) would surface
  who-posted-what for GLBA-style compliance questions later.
  Milestone 8 concern.

## 8. Does the roadmap need adjustment?

**No structural changes.** The Milestone 1 → Milestone 13
sequence in `IMPLEMENTATION_ROADMAP.md` §4 remains sound.
Milestone 3 (Structured condition report) is next and its scope
is unaffected by M2's actual shipped shape — the ledger's
`VehicleCost.is_estimate` field is already the right seam for
Milestone 3's ConditionReport findings to attach cost estimates
to. M4 (Recon automation) will introduce the `Vendor` FK that
data-migrates the M2 `VehicleCost.vendor` CharField.

Two small edits landed at M2.8 close:

- `docs/CAPABILITY_MATRIX.md` §2.1 rows for "Acquisition record"
  and "Per-vehicle cost basis" flipped from N to F. §2.5 row
  "Per-vehicle cost accumulation" flipped from N to F. New §7c
  block enumerates the shipped ledger surface with concrete
  file pointers.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
  paragraph updated to record shipped date + retrospective link.

Milestone 3 (Structured condition report) opens in SESSION_055
as a planning pass. Its planning artifact will land there per
the next-session pointer. The retrospective's most relevant
guidance for Milestone 3:

- **The multi-photo storage tension named at planning §5 is
  now the load-bearing pre-implementation decision** —
  `ConditionFinding` will need photo attachments, which needs
  S3-compatible storage + CDN. The Milestone 3 planning pass
  should either scope in the storage story or split it out as
  a pre-M3 half-milestone.
- **Continue the increment-discipline pattern** — M3 planning
  should mirror the M2 §7.b breakdown, not the original M2 §7.a
  three-increment sketch. The eight-increment shape scaled
  cleanly and every session left the baseline healthy.
- **The `is_estimate` semantic contract carries forward.** M3's
  `ConditionFinding.estimated_cost` will flow into
  `VehicleCost` rows (via M4's recon automation, not M3
  directly) with `is_estimate=True`. The M2.2 contract already
  handles this.
- **Focused test matrices over integration tests.** M2 shipped
  287 focused tests across seven increments; the discipline
  paid off in every migration + refactor. Continue.

---

*End of Milestone 2 retrospective.*
