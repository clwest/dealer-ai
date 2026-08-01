---
title: "Milestone 5 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-01
sessions: SESSION_074 → SESSION_081
milestone: 5
milestone_name: "Vehicle lifecycle stages + retail gating"
related:
  - docs/roadmap/MILESTONE_5_PLANNING.md
  - docs/roadmap/MILESTONE_4_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 5
---

# Milestone 5 — Retrospective

Written at Milestone 5 close (SESSION_081). Records what
was planned, what shipped, what deviated and why, and
lessons carried forward for Milestone 6. Mirrors the
`MILESTONE_4_RETROSPECTIVE.md` structure.

## 1. Planned scope

`MILESTONE_5_PLANNING.md` at SESSION_074 defined the
milestone as answering twelve operational questions from
VCP Phase 4 + `INVENTORY_ACQUISITION_MAPPING.md` §6 +
`RECON_MAPPING.md` §14. The questions cover: *what stage
is this vehicle in right now, is it retail-eligible, when
did it enter the current stage (aging seam for M8), what
was the full stage history and who authorized each
transition, which transitions can the system suggest
based on M4 recon completion, how does the retail chat's
inventory retrieval change to gate on stage rather than
`is_available`, and how does the operator SEE all of
this in the UI?*

§1 followed with seven design-memo entries covering both
models (`VehicleStage`, `VehicleStageEvent`), the
service module (`services/vehicle_lifecycle.py`), the
retail-gating refactor, the operator UI, and the Vehicle
read-model extension (two `@property` accessors).

§2 enumerated 22 existing surfaces M5 touched with
required work. §3 defined the compatibility checklist.
§5.a–§5.k drafted eleven load-bearing decisions —
**four flagged `[NEEDS-DECISION-BEFORE-M5.1]`** requiring
user review before code landed. §7 sequenced seven
increments (M5.1–M5.7).

**Original §7 sequencing (M5.1 → M5.7) shipped verbatim**
with substantial planning-doc amendments at SESSION_075
(§0.a change-log entry) plus multiple in-flight
refinements.

## 2. What actually shipped

Every §3 compatibility item verified true; details in
the annotated checklist at `MILESTONE_5_PLANNING.md` §3.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M5.0 planning | 074 | `MILESTONE_5_PLANNING.md` (1,472 lines) resolving seven load-bearing decisions and leaving four for user review | `ec2b611` |
| M5.1 core persistence | 075 | Two models (`VehicleStage`, `VehicleStageEvent`) + migration `0017` (with bootstrap data migration seeding both stage AND event per Vehicle) + admin registrations (event admin add/delete-locked for append-only history) + 12 stage constants + 4 trigger constants + cross-tenant `clean()` guards + tenancy-carrier extension 15→17 + 58 focused tests. **8 planning amendments landed at session top** (§0.a change-log): 12-stage enum (no `sold`, `company_use` added, `hold_reserved` consistent, `detail` distinct); refined transition table with post-frontline operational escapes; §5.c bootstrap creates both rows; §5.e Option D without premature removal date; §5.f role matrix with `UnauthorizedStageTransitionError` distinct from `InvalidStageTransitionError`; §1.6 no-hidden-writes from Vehicle properties; §5.h rule evaluator refinements; §5.i truthful customer language | TBD |
| M5.2 service + state machine | 076 | `services/vehicle_lifecycle.py` (~610 lines) with 5 public functions (`get_current_stage`, `ensure_current_stage`, `advance_stage`, `retail_eligible`, `suggest_transitions`) + 4 distinct domain errors (`CrossTenantLifecycleError` → 404, `InvalidStageTransitionError` → 409, `UnauthorizedStageTransitionError` → 403, `StageAlreadyCurrentError` → 409) + module-level transition table + role-authority map + 2 Vehicle `@property` accessors (`current_stage`, `is_retail_eligible` as pure reads) + 1 read helper (`resolve_hold_reserved_return_target`) + `SuggestedTransition` dataclass. 77 focused service tests. One design decision surfaced during test-run: `_RETAIL_PREPARATION_STAGES` includes `frontline` (all 8 stages of the retail pipeline) so `hold_reserved → frontline` return resolution works | TBD |
| M5.3 deterministic rules | 077 | 3 rule evaluators in `services/vehicle_lifecycle.py`: `_rule_inspection_to_recon` (fires on ≥1 actionable-severity finding), `_rule_recon_to_qc` (fires when zero open WOs AND every must_do decision covered by completed WO), `_rule_photography_to_listing` (always returns structured unmet prerequisite per §5.h). `suggest_transitions` rewritten from stub to per-stage composition. **NO `_rule_listing_to_frontline`** — manual-only in M5. 41 focused rule tests. Rule functions now `_assert_vehicle_tenant()` at entry for consistent `CrossTenantLifecycleError` (rather than delegating error type to substrate helpers) | TBD |
| M5.4 admin API | 078 | `views_lifecycle.py` (~330 lines) with 3 DRF endpoints (GET dashboard, POST manual transition, POST rule accept) + URL registrations. All three share `IsReconManagerSalesManagerOrOwnerAtActiveDealership` (M4.6 reuse); per-transition role authority happens at M5.2 service via `UnauthorizedStageTransitionError` → 403. Rule accept re-evaluates suggestions at apply time and refuses 409 when predicate flipped OR when matched suggestion has `unmet_prerequisites`. 48 focused endpoint tests | TBD |
| M5.5 retail-gating refactor | 079 | `customer_visible_vehicles()` (single choke point) flipped from `is_available=True` to `_lifecycle_retail_eligible=True` via new `annotate_retail_eligible` queryset helper (annotation name `_lifecycle_`-prefixed to avoid @property setter collision). `_similar_vehicles` routed through the choke point. `inventory_import.py` (only production Vehicle creation site) seeds `frontline` with `trigger='import'` explicitly. Test-only `post_save` auto-bootstrap signal registered in `apps.py::ready()` gated on `_is_running_tests()` (avoids mechanical sweep of ~150 pre-existing test fixtures). M5.1–M5.4 tests call `wipe_lifecycle_state(vehicle)` after creation to observe pre-seed state. 12 net-new tests | TBD |
| M5.6 operator UI | 080 | Frontend surface: 1 route (`/dealer-ai-inventory/:stock/lifecycle` inside `<RequireAuth>`) + 1 page (`VehicleLifecyclePage.tsx`, ~280 lines) + 4 extracted components (`StageBadge`, `StageTimeline`, `SuggestedTransitionsPanel`, `ManualTransitionForm`) + 1 shared `lib/lifecycle.ts` module mirroring backend `_ALLOWED_TRANSITIONS` + `_STAGE_ROLE_AUTHORITY` + 3 typed API helpers. Distinct 400/401/403/404/409 UX. `tsc --noEmit` + `vite build` both clean. Zero backend changes | TBD |
| M5.7 closeout | 081 | This retrospective + `CAPABILITY_MATRIX.md` §7f + `IMPLEMENTATION_ROADMAP.md` M5-shipped-M6-promoted + `MILESTONE_5_PLANNING.md` frontmatter flip + `DEALER_KIT_SESSION_START.md` refresh + `MILESTONE_6_PLANNING.md` created per standing user directive | TBD |

## 3. Planning-doc amendments landed inside increments

**Every reviewed amendment landed in the planning
artifact narrowly + inline at the top of the increment
that consumed it** (M4 §6 lesson 8 carried forward). The
M5 amendments were unusually load-bearing because four
of them resolved user-review-required decisions:

1. **§5.a stage enum — Modified Option C (SESSION_075).**
   12 stages (`incoming → inspection → recon → qc →
   detail → photography → listing → frontline` +
   `wholesale_out`, `hold_reserved`, `company_use`,
   `off_market`). `sold` deferred entirely to M9 (no
   enum constant, no stub). `company_use` added as
   distinct disposition per INVENTORY §6.5.
   `hold_reserved` used consistently (not alternated
   with `hold`). `detail` kept distinct in v1.

2. **§5.b transition table — SESSION_075 refinements.**
   `hold_reserved → previous stage` resolves via the
   most recent `VehicleStageEvent` whose
   `to_stage=='hold_reserved'` and its `from_stage`,
   NOT via `notes` free-text parsing. Post-frontline
   operational transitions explicitly allowed
   (`frontline → hold_reserved / off_market /
   wholesale_out / company_use`). No `frontline → sold`
   in M5.

3. **§5.c bootstrap — SESSION_075 refinement.**
   Migration `0017` creates BOTH a `VehicleStage` AND a
   matching bootstrap `VehicleStageEvent` for every
   existing Vehicle. Skipping the event would leave a
   vehicle whose current stage has no corresponding
   event and silently break the "every stage the
   vehicle occupies has an event" invariant M8 aging
   analytics relies on.

4. **§5.e `Vehicle.is_available` — Option D without
   removal date (SESSION_075).** Keep intact as
   backwards-compat; add `is_retail_eligible` as
   authoritative; refactor known retail consumers in
   M5.5; **NO scheduled M9 removal** — instead
   documented as "retain until every known consumer
   has migrated and a repository-wide audit proves
   removal safe." Anti-pattern locked out:
   `is_available` MUST NOT remain a manual override
   for retail gating.

5. **§5.f role matrix — SESSION_075 refined.** Reuse
   existing permission classes. Recon-adjacent
   transitions: dealer_owner + sales_manager +
   recon_manager. Commercial/disposition transitions
   (`hold_reserved`, `wholesale_out`, `company_use`,
   `off_market`): dealer_owner + sales_manager only.
   `recon_manager` may NOT transition into any
   commercial target. Introduce
   `UnauthorizedStageTransitionError` distinct from
   `InvalidStageTransitionError`; overloading refused.

6. **§1.6 no-hidden-writes refinement (SESSION_075).**
   The original planning sketch had `Vehicle.current_stage`
   @property lazily bootstrapping a missing row. That
   violates M2–M4 side-effect-free Vehicle-read-model
   discipline. The M5.2 contract splits:
   `get_current_stage` (pure read; may return `None`)
   from `ensure_current_stage` (explicit mutating op).
   Vehicle `@property` accessors deferred out of M5.1
   into M5.2 alongside the service.

7. **§5.h rule evaluator refinements (SESSION_075).**
   Rules stay suggestions only. `inspection → recon`
   fires only when completed report has actionable
   findings (empty report NOT forced into recon).
   `recon → qc` requires every must_do decision
   addressed by completed WO coverage.
   `photography → listing` returns structured unmet
   prerequisite (not fake suggestion) pending M6.
   `listing → frontline` manual-only in M5.

8. **§5.i truthful customer language (SESSION_075).**
   Approved phrasing for stock-specific non-frontline
   lookup: *"That vehicle is not currently available
   for retail."* Do NOT expose stage / recon / ETA /
   vendor / expected-ready-date.

9. **Test-only auto-bootstrap signal design
   (SESSION_079).** Rather than update ~150
   pre-existing test fixtures individually (mechanical
   sweep, no design value), a `post_save` signal
   registered in `apps.py::ready()` gated on
   `_is_running_tests()` auto-seeds `frontline` for
   every newly saved Vehicle in tests. Production
   write paths remain explicit per §0.a item 6. M5.1–
   M5.4 tests call `wipe_lifecycle_state(vehicle)` to
   observe pre-seed state.

10. **Annotation name collision refinement
    (SESSION_079).** The `annotate_retail_eligible`
    helper's annotation is named
    `_lifecycle_retail_eligible` (leading underscore +
    prefix) rather than `is_retail_eligible` because
    Django populates annotations via `setattr` and the
    `Vehicle.is_retail_eligible` @property has no
    setter. First draft caught this via test failure
    `AttributeError: property has no setter`.

## 4. Deviations

**Accepted improvements** (all landed inside
increments, all reviewed by user first):

1. **Bulk `[NEEDS-DECISION-BEFORE-M5.1]` resolution
   + no-hidden-writes refinement** (M5.1, SESSION_075
   preamble) — see §3 above (items 1–8).
2. **Rule functions raise `CrossTenantLifecycleError`
   directly** (M5.3, SESSION_077 in-flight) — first
   draft delegated the tenant check to substrate
   helpers, which raise their own error types. Test
   failure surfaced the inconsistency. Fix: explicit
   `_assert_vehicle_tenant()` at entry.
3. **`_RETAIL_PREPARATION_STAGES` includes `frontline`**
   (M5.2, SESSION_076 in-flight) — first draft
   excluded frontline, breaking `hold_reserved →
   frontline` return resolution. Fix: include
   frontline as the 8th pipeline stage.
4. **Annotation name collision** (M5.5, SESSION_079
   in-flight) — see §3 above (item 10).
5. **Test-only auto-bootstrap signal** (M5.5,
   SESSION_079) — see §3 above (item 9).

**Deferrals cataloged** (not dropped; scheduled for
follow-up increments or future milestones):

- **§5.i customer-language refactor for
  `vehicle_detail` / `vehicle_ask`** — requires locating
  the exact stock-specific lookup path inside
  `chat_engine.py` (4,000+ lines). `customer_visible_vehicles()`
  already removes non-frontline units from
  `matched_vehicles`; M4.5 scrub prevents recon-detail
  leaks. Full truthful-phrasing refactor deferred to
  a follow-up.
- **`InventoryPreviewPage` stage-badge + Lifecycle
  button integration** — dedicated `/lifecycle` route
  works standalone. Deferred out of M5.6 to keep the
  shipping boundary clean.
- **`ad_copy.py` / `pipeline.py` `is_available`
  consumer audit** — deliberate per §5.e Option D
  (non-retail consumers migrate on their own
  schedule).
- **`is_available` field removal audit** — post-M9 per
  §5.e SESSION_075 refined (no premature removal
  date).

**No planned scope dropped** in the sense of a
shipped-but-broken feature or silently-missing
invariant.

## 5. Compatibility

Every §3 compatibility row verified true with inline
evidence at `MILESTONE_5_PLANNING.md` §3. Test baseline:
**2,754 pass, 1 skipped, 0 fail** at SESSION_081.
Delta: +236 tests over M4 close baseline (2,518 →
2,754); 0 regressions.

Highlights:

- **Zero regressions** across M1–M4 test suites. All
  pre-M5 chat / vehicle-ask / ad-copy / follow-up /
  ledger / condition-report / recon tests continue to
  pass at 2,518-test baseline.
- **`Vehicle.is_available` schema + values unchanged.**
  §5.e Option D SESSION_075 refined. Field remains
  intact for backwards-compat.
- **M2 ledger substrate byte-for-byte preserved.**
  `services/vehicle_ledger.py` API unchanged.
- **M3 substrate preserved.**
  `services/condition_report.py` API unchanged.
- **M4 substrate preserved.** `services/recon.py` +
  `services/vendor_comm.py` APIs unchanged. M4.6
  admin endpoints unchanged. M4.7 frontend
  unchanged.
- **Customer-facing filtering funnels through
  `customer_visible_vehicles()` — one choke-point
  flip → every downstream retail consumer inherits.**

## 6. Lessons

Ten lessons carried forward for Milestone 6 and beyond.
The first seven inherit unchanged from M2 §6 + M3 §6 +
M4 §6 with M5 evidence; the last three are new to M5.

1. **Increment discipline.** Each M5 sub-increment
   shipped independently verifiable in one session.
   When user brief guidance called for scope refinement
   (SESSION_075's eight planning amendments), the
   correction landed at session open — never
   mid-session as a rescue. Carry-forward from M4 §6
   lesson 1.

2. **Backend-first architecture; frontend never owns
   business rules.** M5.6 is a thin orchestrator
   around the M5.4 admin API. Every write affordance
   in the frontend is gated server-side by
   `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
   (DRF admission) + M5.2 service-layer per-transition
   role authority (`UnauthorizedStageTransitionError`
   → 403). The frontend `allowedTargetsForRole` filter
   is a UX convenience, not the authoritative rule.
   Carry-forward from M4 §6 lesson 2.

3. **Provider-neutral boundaries.** M5 introduced no
   AI role; the module `services/vehicle_lifecycle.py`
   has no LLM integration. If a future increment adds
   AI-drafted stage-transition suggestions, they route
   through the shared safety stack via a new
   `kind="stage_suggestion"` dispatch. Carry-forward
   from M4 §6 lesson 3.

4. **Service ownership — one authoritative write path
   per operation.** Every M5.4 endpoint delegates to
   `services/vehicle_lifecycle.py`. `advance_stage` is
   the single transition verb; both endpoint call
   sites (manual + rule-accept) go through it.
   Cross-tenant guards live in the service; DRF
   permission classes are the coarse admission layer.
   Carry-forward from M4 §6 lesson 4.

5. **Local vs production parity.** Every M5 code path
   walks the same shape in tests as in production.
   The test-only auto-bootstrap signal is the sole
   deliberate divergence — it exists ONLY to avoid
   mechanical fixture sweep, is gated on
   `_is_running_tests()`, and the production write
   path in `inventory_import.py` remains explicit per
   §0.a item 6. Carry-forward from M4 §6 lesson 5.

6. **Honest verification reporting.** When the M5.3
   `photography → listing` rule couldn't be evaluated
   (M6 photo predicate not yet shipped), the M5.3
   implementation returns a **structured unmet
   prerequisite** instead of a fake suggestion or
   silence. §5.i customer-language refactor deferral
   was cataloged as a followup, not silently absorbed.
   Carry-forward from M4 §6 lesson 6.

7. **Storage-first / safer-direction deletion.** M5
   did not touch storage. If any M5 delete flow had
   surfaced, it would follow the M3.5 safer-direction
   pattern. Carry-forward from M3 §6 lesson 7.

8. **[NEW] Load-bearing decisions get user review
   BEFORE code.** SESSION_075 mandate (from
   SESSION_073 handoff): "Do not silently pick a
   load-bearing decision option without user review."
   M5.1 opened with four `[NEEDS-DECISION-BEFORE-M5.1]`
   items resolved at session top via bulk amendment
   before any code landed. Amendments recorded in
   `MILESTONE_5_PLANNING.md` §0.a change-log entry so
   the provenance survives across sessions. **Every
   milestone-opening session that has unresolved
   load-bearing decisions must resolve them at
   session top with the same discipline.**

9. **[NEW] Distinct domain errors → distinct HTTP
   status codes.** M5's four errors
   (`CrossTenantLifecycleError`,
   `InvalidStageTransitionError`,
   `UnauthorizedStageTransitionError`,
   `StageAlreadyCurrentError`) map to four different
   status codes (404/409/403/409). Overloading
   `InvalidStageTransitionError` for both structural
   illegality AND role refusal was explicitly
   rejected at SESSION_075 §0.a item 5 — role refusal
   is 403 (retry-with-authorized-actor); structural
   illegality is 409 (retry-with-different-target). The
   two remediation paths differ; the two error types
   should too. **Every future milestone's endpoint
   layer should map distinct domain error classes to
   distinct HTTP codes, not overload.**

10. **[NEW] Read-model properties are pure reads.**
    §0.a item 6: `Vehicle.current_stage` and
    `Vehicle.is_retail_eligible` @property accessors
    delegate to pure read helpers that may return
    `None` / `False` when no stage row exists. The
    mutating side (`ensure_current_stage`) is a
    distinct explicit verb, not a property-read side
    effect. Migration `0017` bootstraps every existing
    Vehicle; the M5.5 write-path integration in
    `inventory_import.py` seeds new Vehicles
    explicitly. **Every future milestone that adds a
    Vehicle @property accessor must preserve the
    side-effect-free contract — mutating verbs are
    distinct from read helpers.**
