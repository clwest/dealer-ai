---
title: "Milestone 4 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-01
sessions: SESSION_065 → SESSION_073
milestone: 4
milestone_name: "Recon automation"
related:
  - docs/roadmap/MILESTONE_4_PLANNING.md
  - docs/roadmap/MILESTONE_3_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 4
---

# Milestone 4 — Retrospective

Written at Milestone 4 close (SESSION_073). Records what was
planned, what shipped, what deviated and why, and the lessons
that should shape Milestone 5 and beyond. Mirrors the
`MILESTONE_3_RETROSPECTIVE.md` structure.

## 1. Planned scope

`MILESTONE_4_PLANNING.md` at SESSION_065 defined the milestone
as answering fifteen operational questions from RECON §3.1 /
§3.5 / §3.7 / §4.2 / §4.6 / §5.1 / §5.4 / §5.6 / §6.1 – §6.6
/ §7.1 – §7.4 / §13.1 / §14.1 / §14.3 / §14.7 / §14.8 / §16.5.
The questions cover the whole recon pipeline: *which findings
will we fix (three-tier decision), who / where owns each job,
what parts, at what estimated / authorized / actual cost,
what did we communicate to the vendor, and which claims came
from human data vs AI wording?*

§1 followed with seven design-memo entries — one per subsystem:

- §1.1 `ReconDecision` (one-per-Finding; three-tier framework).
- §1.2 `Vendor` (many-per-Dealership; PROTECT deletion contract
  refined SESSION_066).
- §1.3 `WorkOrder` (many-per-Vehicle; five-state lifecycle).
- §1.4 `WorkOrderFinding` (through table; M:N).
- §1.5 `WorkOrderPart` (operational tracking only; no
  marketplace).
- §1.6 `VendorCommunication` (AI-drafted + operator-logged
  workflows; sent/logged semantics separated at SESSION_066).
- §1.7 Vehicle read-model extension (two `@property` accessors).

§2 enumerated 22 existing surfaces the milestone touched with
required work. §3 defined the compatibility checklist. §5.a
through §5.j resolved the ten load-bearing decisions (a → j).
§7 sequenced nine increments, of which eight were planned to
land and one (M4.8 outbound send) was reserved as a deferrable
subset gated on real pilot-store engagement.

**Original §7 sequencing (M4.1 → M4.9) shipped verbatim** with
one deferral (M4.8) and multiple in-flight planning
refinements (see §3 below).

## 2. What actually shipped

Every §3 compatibility item verified true; details in the
annotated checklist at `MILESTONE_4_PLANNING.md` §3.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M4.0 planning | 065 | Full `MILESTONE_4_PLANNING.md` (8 sections; ten load-bearing decisions resolved; nine increments sequenced) | `98d9e79` |
| M4.1 core models | 066 | Six models (Vendor, ReconDecision, WorkOrder, WorkOrderFinding, WorkOrderPart, VendorCommunication) + migration `0016` + admin registrations + 9 module-level enum sets + tenancy-carrier registration 9→15 + 95 focused tests. Three narrow planning refinements (§1.2 + §1.3 + §1.6 + §3 + §5.b + §5.e + §7 M4.3 amendments): Vendor PROTECT contract; estimate retirement on completion; VendorCommunication logged semantics distinct from sent | `7c1eb7e` |
| M4.2 service + state machine | 067 | `services/recon.py` (~800 lines) with 10 public functions + 4 domain errors (`CrossTenantReconError`, `ReconImmutableError`, `InvalidReconTransitionError`, `IncompleteConditionReportError`) + two `Vehicle` @property accessors (`open_work_orders`, `has_recon_decisions`). Zero ledger calls (per SESSION_067 pushback — no hook stubs; M4.3 refactor lands the real ledger integration). 66 focused service tests. Two planning amendments landed: §1.0.QC-GAP (Q13 renegotiated) + §1.6.SHIPPED (enum reconciliation) | `9d4404a` |
| M4.3 ledger integration | 068 | 5 reference-key module constants + 5 private `_post_*` helpers + 3 private support helpers + `revise_estimate` new public function. Refactored `approve_work_order` / `complete_work_order` / `cancel_work_order` to invoke ledger helpers. Completion posts reversal + actual atomically inside `transaction.atomic()` block. WorkOrder→VehicleCost category mapping table (12 entries) with rationale documented at §5.e. 33 focused ledger tests | `568d81e` |
| M4.4 parts service | 069 | 4 public parts-service functions (`add_part`, `update_part`, `transition_part_status`, `delete_part`) in `services/recon.py`. Whitelisted 8-field update. 7-transition FSM with auto-timestamp population. `select_for_update` + `refresh_from_db` concurrency pattern. Zero VehicleCost side effects (planning §5.h boundary preserved). 49 focused tests | `33438ff` |
| M4.5 vendor comm + scrub | 070 | New `services/vendor_comm.py` (~520 lines) with 4 public functions + 4 domain errors. New `_scrub_invented_recon_fact` in `services/llm_safety.py` firing on `kind in {"vendor_comm", "parts_order"}` with 4 regex families (finding IDs, part numbers, dollar amounts, ISO dates). 62 focused tests (29 scrub + 33 service). Zero real LLM API access (MockLLMProvider throughout) | `ad3e7ad` |
| M4.6 admin API | 071 | 18 admin endpoints under `/api/dealer-ai/admin/` (vendor CRUD, recon dashboard, recon decision, WorkOrder lifecycle, WorkOrder findings attach/detach, WorkOrder patch, WorkOrderPart create/patch/delete, VendorCommunication draft/approve/mark-sent/log). New permission class `IsReconManagerSalesManagerOrOwnerAtActiveDealership`. New view module `views_recon.py` (~750 lines). Domain-error → HTTP status mapping (404 / 409 / 422 / 502 / 400). 89 focused endpoint tests | `b031f09` |
| M4.7 operator UI | 072 | Frontend recon page: route `/dealer-ai-inventory/:stock/recon` + `VehicleReconPage.tsx` (~640 lines) + 6 extracted components in `components/recon/` (`WorkOrderStatusBadge`, `DecisionRow`, `PartRow`, `VendorCommDraftPanel`, `VendorPickerModal`, `WorkOrderCard`) + 18 typed API helpers appended to `lib/api.ts` + "Recon" button on operator inventory card. Distinct 401/403/404/409/422/502 UX. Draft/approved/sent/logged visually distinct per state. Provenance rendering in comm panel | `90cbf7c` |
| M4.9 closeout | 073 | §3 sweep with inline evidence + this retrospective + `CAPABILITY_MATRIX.md` §7e + `IMPLEMENTATION_ROADMAP.md` flip. Zero code changes | (this session) |

**Test baseline evolution.** M3 close 2,124 → 2,219 (M4.1)
→ 2,285 (M4.2) → 2,318 (M4.3) → 2,367 (M4.4) → 2,429 (M4.5)
→ 2,518 (M4.6) → 2,518 (M4.7 — frontend only)
→ **2,518 (M4.9 unchanged)**. Delta: **+394 tests, zero
regressions.** No test suppressed with `@skip` to make the
baseline pass. Frontend `npx tsc --noEmit` clean; `npx vite
build` clean (same pre-existing 552-KB chunk warning from
M2.7).

**M4.8 (outbound send) deferred** per planning §5.i + §5.j.
No pilot-store engagement surfaced during M4; the deferrable-
subset gate did not open. M4 closed at M4.9 with the send
workflow intentionally absent.

## 3. Sequencing refinements

Ten material refinements from the SESSION_065 plan. Each was
course-corrected in-flight based on user brief guidance or
planning-artifact review.

Clearly distinguishing planned vs executed:

1. **Vendor PROTECT contract (SESSION_066).** *Planned:* §1.2
   said "vendors are soft-deleted; never hard-delete a
   referenced vendor," while §1.3 + §1.6 planned SET_NULL FKs
   on `WorkOrder.vendor` and `VendorCommunication.vendor`.
   Those two are contradictory. *Executed:*
   `on_delete=PROTECT` on both FKs enforces the invariant at
   the schema layer (Postgres/SQLite raise `ProtectedError`
   when a referenced Vendor is deleted); normal removal path
   remains `Vendor.is_active=False`. §1.2 / §1.3 / §1.6 / §3
   / §5.b amended narrowly at session open.

2. **Estimate retirement on completion (SESSION_066).**
   *Planned:* §5.e originally said estimate rows remain
   outstanding after actual cost posts, which would
   double-count completed work in
   `projected_total_investment`. *Executed:* completion
   atomically posts a reversal (under the dedicated one-shot
   `completion_estimate_reversal` reference) plus the actual
   inside a single `transaction.atomic()` block. Net
   estimate contribution on any terminal WO is
   `Decimal("0.00")`. §3 + §5.e + §7 M4.3 amended at session
   open. Implementation landed at SESSION_068 per the
   revised contract.

3. **VendorCommunication `logged` semantics separated from
   `sent` (SESSION_066).** *Planned:* the sent-state checklist
   treated both `sent` and `logged` as requiring
   `approved_by` and `sent_by`. Too broad for operator-
   recorded phone / in-person / inbound rows. *Executed:*
   `logged` requires `sent_by` + `sent_at` + nonblank
   `draft_content` (recorded body) but does NOT require a
   prior approval step. Sent still requires the full draft →
   approved → sent ladder. "AI-generated content may never
   jump directly to logged" is enforced at the M4.5 service
   layer (a persistence-only guard cannot distinguish
   AI-drafted from operator-recorded rows). §1.6 + §3
   amended.

4. **Q13 renegotiated — completion timestamps do not claim
   QC (SESSION_067).** *Planned:* §1.0 questions table listed
   Q13 "was the work verified after completion?" as answered
   by the work-order subsystem. *Executed:* new §1.0.QC-GAP
   annotation flags that `WorkOrder.completed_at` proves
   *when work was marked complete*, not *whether it was
   verified*. Two paths documented for a future QC
   increment (Path A: new `QcVerification` model; Path B:
   fields on WorkOrder). Locked at
   `test_recon_service.py::CompletionDoesNotClaimQc` — the
   schema does not gain `qc_verified*` fields and the
   service function's signature does not accept a
   `qc_verified` kwarg. If a future increment adds QC
   fields, this test forces a planning revision first.

5. **Enum reconciliation for the shipped M4.1 vocabularies
   (SESSION_067).** *Planned:* §1.6 draft listed
   `kind = (assignment, status_check, invoice_question,
   general_note)`, `channel = (email, sms, phone, in_person)`,
   `status = (draft, approved, sent, logged, failed)`.
   *Executed:* M4.1 shipped `kind = (vendor_comm,
   parts_order, narrative)`, `channel = (email, sms, phone,
   in_person, internal_note)`, `status = (draft, approved,
   sent, logged)`. New §1.6.SHIPPED annotation justifies
   each divergence and documents where the retired
   `assignment / status_check / invoice_question` intents
   live in the shipped schema (in prose within
   `draft_content` / `sent_content`; in `direction`;
   in `channel`). `failed` deferred pending live send in a
   future prod-readiness pass.

6. **No ledger-hook stubs in M4.2 (SESSION_067).** *Planned:*
   the M4.1 handoff's recommended M4.2 scope proposed a
   `_post_*_hook` stub pattern in M4.2 that M4.3 would fill
   in. *Executed:* SESSION_067 brief pushed back — a silent
   stub risks tests proving a false contract. M4.2 shipped
   with **zero** ledger calls; M4.3 refactored the transition
   functions to add real ledger invocations. Compensating
   discipline: `test_recon_service.py::NoLedgerSideEffectsWithoutEstimate`
   (post-M4.3) locks the "no ledger side effects without an
   estimate" boundary.

7. **Decision reconsideration policy — upsert-while-not-yet-
   authorized (SESSION_067).** *Planned:* the M4.1 planning
   contract was silent on what a second `record_decision`
   call on the same finding should do. *Executed:* upsert
   while no linked WorkOrder has left draft state; refuse
   with `ReconImmutableError` once any linked WO is
   approved / in_progress / completed / cancelled.
   Rationale: recon managers legitimately reconsider tier
   before quotes come back or before work is authorized;
   once acted on, the decision is history and locking it
   preserves the audit trail.

8. **Approval requires ≥1 linked finding (SESSION_067).**
   *Planned:* §1.3 was silent on whether a no-finding
   approval was permitted. *Executed:* `approve_work_order`
   refuses when `work_order.finding_links.count() == 0`.
   Rationale: planning §1.4 frames WOs as the execution
   side of the finding → decision → work chain; a
   no-finding approval breaks Q1 back-traceability. If
   operational evidence surfaces a legitimate no-finding
   recon job (routine detail on a front-line-ready unit),
   the rule is a service-layer concern that can be relaxed
   with a planning annotation — no schema change required.

9. **Category-mapping table for WorkOrder→VehicleCost
   (SESSION_068).** *Planned:* §5.e said `add_cost` receives
   `category=` mapped from `WorkOrder.category` — same
   12-value enum. In fact `WorkOrder.category` uses
   `CONDITION_CATEGORY_CHOICES` (12 values) while
   `VehicleCost.category` uses `VEHICLE_COST_CATEGORY_CHOICES`
   (26 values). *Executed:* new 12-entry mapping table at
   `services/recon.py::_WORK_ORDER_CATEGORY_TO_LEDGER_CATEGORY`
   with per-row rationale in the code + documented at §5.e.
   Ambiguous rows (cosmetic → paint vs body_work; safety →
   brakes vs tires) default to the most common real-world
   outcome. Locked by
   `test_recon_ledger.py::CategoryMappingCompleteness`.

10. **`revise_estimate` as a distinct public function
    (SESSION_068).** *Planned:* §5.e said estimate updates
    happen via "the WO patch endpoint" without a distinct
    service verb. *Executed:* new `revise_estimate` public
    function on `services/recon.py` — separate operator
    gesture from `approve_work_order` (which handles the
    idempotent re-approve for `authorized_cost` updates but
    NOT `estimated_cost` revision). Rationale: approval is
    about authorizing work; estimate revision is about
    re-pricing it after new information. Distinct semantics
    warrant distinct verbs.

## 4. Deviations

**Accepted improvements** (tightenings landed inside
increments, all reviewed by user first):

1. **Vendor PROTECT + estimate retirement + logged
   semantics** (M4.1, SESSION_066 preamble) — see §3 above.
2. **QC-GAP + enum reconciliation + no-ledger-stubs +
   reconsideration policy + approve-requires-findings**
   (M4.2, SESSION_067 preamble + brief) — see §3 above.
3. **Category mapping + `revise_estimate`** (M4.3,
   SESSION_068) — see §3 above.
4. **`customer_supplied` source-type finalized at M4.1**
   (SESSION_066) — planning §1.5 listed 6 source types +
   "finalize count in M4.1 per RECON §6.1–§6.4". Shipped
   with 7 including `customer_supplied` because customer-
   supplied parts have warranty + liability implications
   that operationally distinct from `in_stock`. Locked at
   `test_work_order.py::WorkOrderPartSourceTypeVocabulary::test_customer_supplied_present`.
5. **`log_communication` accepts any kind, not only
   narrative** (M4.5, SESSION_070) — an operator may log a
   vendor_comm that already happened off-system (they sent
   an email from Gmail directly). The AI-cannot-jump-to-
   logged invariant is preserved structurally: the
   `draft_communication` function never returns a row in
   logged status; `log_communication` creates a brand-new
   row directly at logged. Locked by
   `test_vendor_comm_service.py::AIDraftedCannotReachLogged`.
6. **Vendor CRUD admin: no DELETE endpoint** (M4.6,
   SESSION_071) — PROTECT contract from §5.b would surface
   a confusing `ProtectedError` at DB layer on the delete
   button. The M4.6 endpoint layer omits the delete route
   entirely; the vendor detail endpoint accepts PATCH only.
   Locked at `test_admin_recon_endpoints.py::VendorCrudFlow::test_no_delete_endpoint_exists`
   (asserts 405 on DELETE).
7. **Cross-tenant → 404 (never 403)** (M4.6, SESSION_071)
   — same shape as M2.6 + M3.6. Never leak whether a
   resource exists in another dealership. Locked across
   every resource type in
   `test_admin_recon_endpoints.py::*CrossTenant404`.

**No planned scope dropped** in the sense of a shipped-but-
broken feature or a silently-missing invariant. **M4.8
(outbound send) is deferred, not dropped** per planning
§5.i + §5.j.

## 5. Compatibility

Every §3 compatibility row verified true with inline
evidence citations at `MILESTONE_4_PLANNING.md` §3. Test
baseline: **2,518 pass, 1 skipped, 0 fail** at SESSION_073.

Highlights:

- **Zero regressions** across the M1 · 4A / 4B / 4C / 4D /
  4E, M2.1 – M2.8, M3.1 – M3.8 test suites. All pre-M4
  chat / vehicle-ask / ad-copy / follow-up / ledger /
  condition-report tests continue to pass at 2,518-test
  baseline.
- **M2 ledger substrate byte-for-byte preserved.**
  `services/vehicle_ledger.py::add_cost` signature
  unchanged. `VehicleCost` immutability preserved (M4.3
  posts new rows; never edits / deletes).
  `total_investment` semantic contract unchanged; anti-
  double-count invariant on completed WOs is a positive
  addition, not a regression.
- **M3 substrate preserved.** `services/condition_report.py`
  API unchanged. `ConditionFinding.estimated_cost`
  documentation-only invariant intact (locked by three
  pre-existing tests + one new M4.3 regression test).
- **M4.7 frontend has zero backend impact.** M2.7 ledger
  page + M3.7 condition-report page continue to work
  unchanged; the M4.7 recon page adds a fourth surface to
  the operator inventory card without disturbing the
  other three.

## 6. Lessons

Ten lessons carried forward for Milestone 5 and beyond. The
first seven inherit unchanged from M2 §6 + M3 §6 with M4
evidence; the last three are new to M4.

1. **Increment discipline.** Each M4 sub-increment shipped
   independently verifiable in one session. When user brief
   guidance called for scope refinement (SESSION_067
   pushback on ledger hook stubs; SESSION_066 planning
   refinements), the correction landed at session open —
   never mid-session as a rescue. Carry-forward from M3 §6
   lesson 1.

2. **Backend-first architecture; frontend never owns
   business rules.** M4.7 is a thin orchestrator around
   the M4.6 admin API. Every write affordance in the
   frontend is gated server-side by
   `IsReconManagerSalesManagerOrOwnerAtActiveDealership`;
   the frontend `useAuth().hasRole()` gate is a UX
   convenience, not the authoritative rule. Carry-forward
   from M3 §6 lesson 2.

3. **Provider-neutral boundaries.** `services/vendor_comm.py`
   consumes the existing LLM provider factory
   (`services/llm/factory.py`) without embedding any
   provider-specific code path. The M4.5 tests inject
   `MockLLMProvider` for zero real API access. The M4.8
   outbound-send deferral means no SMTP / SMS provider
   coupling exists yet; when it does, the same discipline
   applies. Carry-forward from M3 §6 lesson 3.

4. **Service ownership — one authoritative write path per
   operation.** Every M4.6 endpoint delegates to a service
   function; no endpoint calls `WorkOrder.objects.create`
   or `VendorCommunication.objects.create` directly.
   Cross-tenant guards live in the service. Carry-forward
   from M2 + M3 lesson 4.

5. **Local vs production parity.** Every M4 code path
   walks the same shape in tests as in production. The LLM
   is mocked via provider injection; the ledger writes are
   real (against the test DB); the transitions use the same
   `select_for_update` + `refresh_from_db` pattern the
   production DB would enforce. Carry-forward from M2 + M3
   lesson 5.

6. **Honest verification reporting.** M4.7 does NOT claim a
   completed manual browser walkthrough — the handoff
   explicitly defers to operator first-live-use per M3.7
   precedent. §1.0.QC-GAP is the most load-bearing example:
   the planning artifact originally claimed M4 answered
   Q13 ("was the work verified?"); SESSION_067 renegotiated
   that claim rather than silently rendering
   `completed_at` as if it meant "verified." Carry-forward
   from M2 + M3 lesson 6.

7. **Storage-first / safer-direction deletion.** Applies at
   M4 via the Vendor PROTECT contract: hard-delete of a
   referenced vendor is refused at the schema layer, not
   silently cascaded to NULL. If operator error attempts
   the wrong deletion, the DB refuses; the operator learns
   the constraint immediately rather than discovering it
   after historical rows are corrupted. Carry-forward from
   M3 §6 lesson 7 (adapted from "storage delete first" to
   "reference protection first").

8. **Document implementation refinements immediately.**
   New at M4 — SESSION_066 landed three narrow planning
   amendments before code; SESSION_067 landed two more
   (§1.0.QC-GAP, §1.6.SHIPPED); SESSION_068 added the
   §5.e category-mapping table. Every amendment is a
   reviewed refinement that the M4.9 §3 sweep can point
   at as evidence. The alternative — silent drift between
   planning and code — would have made this retrospective
   an archaeology exercise rather than a summary.

9. **Compat patches must be honest.** New at M4 — the
   `SESSION_066_m4_inc1_core_models.md` handoff records
   the `MinValueValidator` import addition to
   `models.py` explicitly (needed for the M4.1
   `WorkOrderPart.quantity >= 1` constraint) rather than
   burying it. Every subsequent M4 handoff enumerates its
   file-level changes at the "Files changed" section.
   Carry-forward from M3 §6 lesson 9.

10. **Avoid architectural drift — don't generalize
    prematurely.** New at M4 — the recon service was
    tempting to abstract into a generic "workflow engine"
    with configurable state machines and hookable ledger
    integrations. Deliberately kept concrete:
    `services/recon.py` is one file with recon-specific
    verbs and recon-specific state semantics. If a second
    consumer (M5 lifecycle, M11+ deal desk) proves the
    need for shared state-machine infrastructure, the
    refactor lands at that time with two real use cases.
    Carry-forward from M3 §6 lesson 10.

## 7. Remaining deferrals

Every deferred item has a home in an existing planning /
retrospective / handoff doc; `docs/roadmap/DEFERRED_IDEAS.md`
does not exist and is not needed for M4 close (per M3.8
precedent).

1. **M4.8 — outbound SMTP / SMS send** (planning §5.i +
   §5.j). Deferred pending a real pilot-store engagement.
   When it lands, the acceptance criteria in §5.j
   enumerate the necessary work (SMTP wiring, per-tenant
   reply-to, bounce handling, retry queue, legal review,
   real pilot-store vendor list).

2. **`QcVerification` model or fields** (planning §1.0.QC-GAP,
   SESSION_067). Deferred to a future increment
   (SESSION_073 handoff or M5 planning to pick up).
   Two paths documented (Path A: separate model; Path B:
   fields on `WorkOrder`). Locked at
   `test_recon_service.py::CompletionDoesNotClaimQc` — if
   this test starts failing, revisit §1.0.QC-GAP.

3. **Vendor CRUD admin page in the frontend UI** (M4.7
   explicit non-goal). The M4.6 API endpoints exist; the
   dedicated `/admin/vendors/` UI page is deferred to a
   future increment when operator evidence surfaces the
   need. Current UX: vendor selection via the WorkOrder
   creation form's picker; vendor lifecycle (create /
   patch / deactivate) via API only.

4. **Per-sentence `source_provenance` UI attribution.**
   M4.5 v1 captures the source bundle as provenance; M4.7
   renders it as JSON in a collapsible panel. Per-sentence
   mapping (which sentence in the AI draft came from which
   source field) requires either structured LLM output or
   NLP heuristics — deferred pending operator evidence.

5. **Cost-variance analytics** (planning §1.0 Q10, M8).
   M4 records estimate + actual per WO; M8 will aggregate
   for vendor-performance dashboards + category-level
   variance. Data shape locked; aggregation deferred.

6. **Aging / bottleneck detection dashboards** (Q11 at
   fleet level, M8). Same shape — M4 records the raw
   `WorkOrder.status` + `WorkOrderPart.status` + timestamps;
   M8 aggregates.

7. **Live parts-marketplace integration + auto-order +
   vendor-portal booking** (planning §5.h + §5.i explicit
   out-of-scope). RECON §16.4 documented the automation
   opportunity; deferred to a future async-infrastructure
   milestone (M7 or later).

8. **AI-drafted return / re-order draft flow.** M4.5 drafts
   outbound vendor comms and parts orders; the "cancel my
   previous order" or "reorder because backordered" flow
   is a future extension of `draft_communication` with a
   new source-bundle field (e.g. `previous_comm_reference`).
   Deferred.

## 8. Milestone 5 bootstrap

Milestone 5 is **Vehicle lifecycle stages + retail
gating** per `IMPLEMENTATION_ROADMAP.md` §Milestone 5.
M5 reads M4 shipped surface as an input.

**M5 read-model prerequisites already shipped:**

- `Vehicle.open_work_orders` — queryset of nonterminal
  WOs. M5 uses this to gate "front-line ready" transitions
  (a vehicle with open must-do work is not front-line).
- `Vehicle.has_recon_decisions` — bool. M5 uses this to
  detect vehicles that have not yet been recon-planned.
- `services/recon.py::has_recon_decisions_for_vehicle` +
  `open_work_orders_for_vehicle` — read helpers M5 can
  call directly instead of going through the properties
  when passing an explicit dealership.

**M5 planning shape (mirrors SESSION_055 → M3, SESSION_065
→ M4 planning-pass shape).** SESSION_074 (or whenever the
user schedules M5.0) should:

- Frame the four operational questions M5 must answer
  (candidates: "is this vehicle front-line ready?"; "what
  stage is this vehicle in?"; "who authorized the stage
  transition?"; "when did stage transitions happen?").
- Design memo per subsystem (lifecycle stages enum,
  Vehicle stage field + provenance, retail-gating service).
- Migration impact review (M4 substrate is read-only from
  M5's perspective — no changes needed).
- Load-bearing decisions (state-machine granularity;
  auto-transitions from M4 recon completion vs manual
  transitions; retail gating hard-block vs advisory).
- Nine or fewer increments sequenced.

**M4 → M5 handoff surface:**

- `WorkOrder.status="completed"` + finding.severity=safety
  or must_do → contributes to front-line-ready gate.
- `ReconDecision.tier="must_do"` on an outstanding finding
  → blocks front-line-ready.
- `Vehicle.is_available` (from M1) is the current binary
  gate; M5 refactors to a computed lifecycle stage that
  subsumes it.

**Recommend M5 planning pass at SESSION_074 or when the
user is ready to promote from the M4 closeout.**
