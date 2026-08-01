---
title: "SESSION_065 handoff — Milestone 4 · Increment 0 (planning pass)"
status: historical
type: handoff
date: 2026-08-01
session: 065
milestone: 4
milestone_status: planning
increment: 0
increment_status: shipped
commit: 98d9e79
---

# SESSION_065 — Milestone 4 · Increment 0 (M4.0 — planning pass)

## What shipped

Documentation-only session. No code changes. Milestone 4
(Recon Automation) is now scoped, sequenced, and ready for
implementation. All ten load-bearing pre-implementation
decisions are resolved inside the planning artifact §5.

The deliverable is `docs/roadmap/MILESTONE_4_PLANNING.md`
(1,712 lines) mirroring the eight-section shape (§0–§8) that
`MILESTONE_2_PLANNING.md` (SESSION_045) and
`MILESTONE_3_PLANNING.md` (SESSION_055) proved out across the
M2 and M3 execution paths.

## Read-first pass performed

Per the SESSION_064 handoff § "Read-first list for SESSION_065":

1. `docs/PROJECT_RULES.md` — six governance rules.
2. `docs/DOC_GOVERNANCE.md` — six documentation principles.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4 —
   business objective, operational pain, gap statement,
   scope boundary.
4. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` — full
   document. §8 M4 bootstrap and §6 (ten lessons) are
   load-bearing inputs.
5. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 — six
   lessons carried forward alongside the M3 ten.
6. `docs/research/RECON_MAPPING.md` — full document, with
   focus on §3 (three-tier recon planning framework must-do
   / should-do / won't-do), §4 (in-house shop R.O. flow at
   §4.2), §5 (outsourced vendor management, especially §5.4
   estimated / authorized / actual costs and §5.6 vendor
   comms), §6 (parts sourcing OEM vs aftermarket + §6.6
   parts tracking states), §7 (QC pass), §11 (vendor
   communications), §13.1 (warranty exposure for skipped
   items), §14 (blockers), §16 (automation opportunities —
   §16.2 recon plan drafting, §16.3 vendor recommendation,
   §16.4 parts pre-order, §16.5 vendor comm drafting).
7. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 3 —
   target M4 shape (`Vendor`, `WorkOrder`, auto-mint
   `VehicleCost` on complete, AI drafting for narratives /
   emails / SMS / POs, new `invented_recon_fact` scrub).
8. `docs/roadmap/AUTHENTICATION_MODEL.md` — every M4
   endpoint inherits the four-layer separation unchanged;
   `recon_manager` role already exists in `ROLE_CHOICES`
   (M1 · 4A shipped it; M4 first surfaces it in a
   permission class).
9. `docs/roadmap/MILESTONE_3_PLANNING.md` §7 — the
   nine-increment shape M4 mirrors, plus the M3.6 A/B split
   discipline precedent.
10. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b — the
    alternate eight-increment shape and the ledger-service
    template (`services/vehicle_ledger.py`) M4.3 extends.
11. `backend/dealer_ai/models.py` — verified
    `ROLE_RECON_MANAGER` exists (line 25-33); confirmed
    `VehicleCost.vendor` is a free-text CharField in M2
    (not yet FK — see §5.b decision below).
12. `backend/dealer_ai/services/vehicle_ledger.py` —
    verified `add_cost(..., reference="...", vendor="...")`
    signature that M4.3 idempotency guard depends on.
13. `backend/dealer_ai/services/tenancy.py` —
    `_TENANT_CARRIER_MODEL_NAMES` tuple (9 entries at M3
    close; M4.1 extends to 15).

## The ten load-bearing decisions — all resolved

The planning artifact §5 records each with rationale,
options considered, and chosen path.

### §5.a Recon Plan vs. Work Order

**Chosen: Option B — one entity (`WorkOrder`).** Per-finding
decision recorded via `ReconDecision` (OneToOne on
`ConditionFinding`); no separate `ReconPlan` container.
Rationale: RECON §3.1 three-tier decision is per-finding,
not per-container; findings and work orders are already
enough model surface for the M4 operational questions.

### §5.b Vendor entity migration strategy

**Chosen: Option C — do NOT modify `VehicleCost.vendor`.**
The M2 free-text field stays intact. `WorkOrder.vendor` is
a proper FK to the new `Vendor` model. When a work-order
completion auto-mints a `VehicleCost` via `add_cost`, it
passes `vendor=work_order.vendor.name` as a snapshot
string. Historical M2 rows are unchanged; no destructive
migration; the M2 `total_investment` contract is preserved.

### §5.c Work-order state machine

**Chosen: five states — `draft`, `approved`,
`in_progress`, `completed`, `cancelled`.** Service-owned
transitions (`approve_work_order`, `start_work_order`,
`complete_work_order`, `cancel_work_order`); no FSM
library. Rejected: separate `waiting_parts` /
`scheduled` states (recorded as blocker text on the WO,
not lifecycle stages). Reversing-entry pattern for
cancellation of an approved WO (mirrors M2.6 pattern).

### §5.d Findings-to-work mapping

**Chosen: many-to-many via `WorkOrderFinding` through
model.** One finding can be addressed across multiple
work orders (e.g. tire mount + alignment); one work
order can address multiple findings (RECON §3.7
combined-work-efficiency example). Attach/detach only
when parent WO is in `draft`.

### §5.e Estimate-to-ledger contract + idempotency

**Chosen: reference-tagged idempotency.**

- On `approve_work_order`: post
  `add_cost(is_estimate=True, reference="WORKORDER:<id>:estimate:<seq>")`.
- On `complete_work_order`: post
  `add_cost(is_estimate=False, reference="WORKORDER:<id>:actual")`.
- On `cancel_work_order` of an approved WO: post negative
  reversing entry
  `WORKORDER:<id>:estimate:<seq>:reversal`.
- On WO PATCH that changes `estimated_cost` while
  status=approved: reversal + new estimate.

Idempotency: check for a matching reference-tagged
non-reversed row before calling `add_cost`. `ConditionFinding.estimated_cost`
NEVER triggers a ledger post — regression coverage in
M4.3 test surface.

### §5.f Role permission matrix

**Chosen: new permission class
`IsReconManagerSalesManagerOrOwnerAtActiveDealership`.**
Composed like the M1 · 4D
`IsSalesManagerOrOwnerAtActiveDealership` class. The
`recon_manager` role gets write access to
recon-decision + work-order + parts + vendor-comm-draft
endpoints; `sales_manager` and `dealer_owner` retain
their existing write access to everything (superset).
Advisors read-only; porters no access; F&I no access;
collections no access. Full matrix in §5.f table.

### §5.g Vendor communication AI boundary + safety scrub

**Chosen: new post-LLM scrub
`_scrub_invented_recon_fact` firing on `kind="vendor_comm"`
and `kind="parts_order"`.** Regex families cover
invented finding IDs, invented part numbers, invented $
amounts, invented dates. Mirrors the
`_scrub_acquisition_price` pattern (M2.5) —
opt-in-by-kind, defense-in-depth alongside prompt-level
grounding. `source_provenance` JSONField maps sentence
indices to source-bundle keys. Human `approved_by` +
`sent_by` required before `status="sent"`. AI never
authors findings themselves (that's the M3
human-authorship invariant, unchanged).

### §5.h Parts procurement scope

**Chosen: operational tracking only.** Six
`WorkOrderPart.status` values (`needed`, `ordered`,
`backordered`, `received`, `installed`, `returned`).
Explicit non-goals: no marketplace, no parts-store API
integration, no automated ordering, no payment. Parts
document what's been done; they don't transact.

### §5.i Outsourced scheduling

**Chosen: v1 records operator input only.** No calendar
API, no SMS provider, no vendor booking system. Operator
records `estimated_completion_date` from vendor
communication; `actual_completion_date` gets set on
`status="completed"` transition. If a pilot store
surfaces a real need, M8 or a dedicated pre-M5 pass can
add integration.

### §5.j First-live-prod deployment

**Chosen: defer send to a separate pre-pilot pass.** M4
ships with operator-copy-paste-from-draft-UI as the send
workflow. SMTP wiring, per-tenant reply-to config,
Twilio SMS adapter — all reserved for M4.8 IF a pilot
store engagement surfaces during M4 that requires
outbound. Otherwise it lands in a "prod-readiness pass"
between M4 and M5. Rationale: prod deployment introduces
its own set of load-bearing decisions (DNS, TLS, bounce
handling, tenant SMTP identity, DKIM/SPF, unsubscribe,
GDPR export) that deserve their own planning pass.

## The nine-increment sequence

Mirrors the M2 §7.b + M3 §7 shape. Each increment ships
one session with focused tests and a healthy full-suite
baseline at the boundary. No preemptive bundling; the
M3.6 A/B split precedent stands.

| Increment | Session | What it delivers | Test target |
|-----------|---------|------------------|-------------|
| M4.1 | 066 | Six models (`Vendor`, `ReconDecision`, `WorkOrder`, `WorkOrderFinding`, `WorkOrderPart`, `VendorCommunication`) + migration `0016` + admin registrations + enum constants + cross-tenant `clean()` guards + `_TENANT_CARRIER_MODEL_NAMES` extension (9 → 15) | 2,124 → ~2,189 |
| M4.2 | 067 | `services/recon.py` with `record_decision`, `create_work_order`, `attach_findings`, `detach_finding`, `approve_work_order`, `start_work_order`, `complete_work_order`, `cancel_work_order` + state machine + `CrossTenantReconError` + `ReconImmutableError` + two `Vehicle` `@property` accessors | ~2,189 → ~2,244 |
| M4.3 | 068 | Estimate-to-ledger contract with idempotency (`_post_estimate`, `_post_estimate_reversal`, `_post_actual`) wired into approve / complete / cancel hooks; vendor snapshot pass-through | ~2,244 → ~2,279 |
| M4.4 | 069 | Parts tracking (`add_part`, `update_part`, `transition_part_status`, `delete_part`) + six-status enum + gated by WO status | ~2,279 → ~2,309 |
| M4.5 | 070 | `services/vendor_comm.py` + new `_scrub_invented_recon_fact` post-LLM scrub + `source_provenance` recording + human-approval-before-send invariant | ~2,309 → ~2,364 |
| M4.6 | 071 | Admin API — ~17 endpoints under `/api/dealer-ai/admin/vehicles/<stock>/recon/`, `/work-orders/…`, `/comms/…`, `/vendors/` + new `IsReconManagerSalesManagerOrOwnerAtActiveDealership` permission class + full permission matrix | ~2,364 → ~2,454 |
| M4.7 | 072 | Operator UI — `/dealer-ai-inventory/:stock/recon` route + `VehicleReconPage.tsx` + extracted components under `frontend/src/components/recon/` + typed API helpers + `source_provenance` display + draft-vs-approved-vs-sent visual states | Frontend only; backend baseline ~2,454 unchanged |
| M4.8 | 073 (deferrable) | Communication send / scheduling — SMTP wiring + optional Twilio adapter — DEFERRED unless pilot-store engagement surfaces during M4 | +~30 if landed; 0 if deferred |
| M4.9 | 074 (or 073 if M4.8 deferred) | Verification + closeout — §3 compatibility sweep with evidence citations; `MILESTONE_4_RETROSPECTIVE.md`; `CAPABILITY_MATRIX.md` §7e; roadmap M4 → SHIPPED; frontmatter flip | No code |

## What Milestone 4 delivers (recap)

For any stock number with a completed M3 condition report,
answer the operational questions: **"Which findings will we
repair? Who's doing each job? What parts? What did we
estimate? What did we actually spend? What was communicated
to the vendor?"** — with the AI drafting the artifacts that
today require manual composition (recon narratives, vendor
emails, purchase orders), while humans retain approval and
sending authority.

**In scope** (per `IMPLEMENTATION_ROADMAP.md` §Milestone 4 +
`MILESTONE_4_PLANNING.md` §1):

- `ReconDecision` (one-per-Finding, three-tier).
- `Vendor` model (many-per-Dealership; is_active soft-delete).
- `WorkOrder` (many-per-Vehicle; five-state lifecycle;
  in-house or outsourced venue).
- `WorkOrderFinding` (many-to-many through table).
- `WorkOrderPart` (six-status operational tracking).
- `VendorCommunication` (AI-drafted; human-approved;
  `source_provenance`-tracked).
- Estimate-to-ledger auto-post with idempotency + reversing
  entries.
- New `_scrub_invented_recon_fact` post-LLM scrub.
- New `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  permission class (first `recon_manager` write surface).
- Operator UI for the full recon dashboard per vehicle.

**Explicitly out of scope** (verified against roadmap +
retro + planning-artifact §5):

- Parts marketplace / ordering / payment (§5.h).
- Vendor recommendation ranking (deferred to Milestone 8).
- Calendar API / SMS booking (§5.i).
- Prod SMTP send (§5.j — reserved for pre-pilot pass).
- Vehicle lifecycle stages (Milestone 5).
- Inbound email processing.
- Warranty callback tracking (Milestone 4+ or later).
- Cross-department aging dashboards (Milestone 8).
- Any destructive migration of `VehicleCost.vendor` (§5.b).

## Non-goals verified (this session)

- ❌ Zero Milestone 4 code was written (no models, no
  migrations, no service functions, no views, no tests, no
  frontend, no prompts, no AI workflows).
- ❌ Zero changes to `services/vehicle_ledger.py` or any M2
  ledger endpoint / UI.
- ❌ Zero changes to `services/condition_report.py` or any
  M3 endpoint / UI.
- ❌ Zero changes to `dealer_ai/permissions.py` (new class
  planned for M4.6, not touched this session).
- ❌ Zero changes to `services/tenancy.py` (the
  `_TENANT_CARRIER_MODEL_NAMES` extension is planned for
  M4.1, not touched this session).
- ❌ Zero changes to `services/llm_safety.py`
  (`_scrub_invented_recon_fact` is planned for M4.5, not
  touched this session).
- ❌ Zero introduction of a new AI role (M4.5 first surfaces
  vendor-comm drafting).
- ❌ Zero re-opening of M2 semantic contracts
  (`total_investment` still excludes estimates; money-as-
  strings at API boundaries; `VehicleCost.vendor` remains
  free-text).
- ❌ Zero re-opening of M3 semantic contracts
  (human-authorship of `ConditionFinding` remains intact;
  complete reports remain immutable; `ConditionFinding.estimated_cost`
  never posts to the ledger).

## Baselines unchanged

- **Backend test baseline unchanged: 2,124 pass, 1 skipped,
  0 fail** (measured at SESSION_064 close; this session
  made no code changes).
- **Migrations unchanged through `0015`.**
- **Frontend build unchanged.** No `.tsx` or `.ts` touched.
- **No new dependencies added this session.** Zero pip /
  npm installs.

## Documentation updated

- **`docs/roadmap/MILESTONE_4_PLANNING.md`** — NEW (1,712
  lines). Full eight-section planning artifact mirroring
  `MILESTONE_3_PLANNING.md`. `status: draft`, `milestone: 4`,
  `milestone_name: "Recon automation"`.
- **`docs/handoffs/SESSION_065_m4_planning.md`** — this
  file.
- **`00-START-NEXT-SESSION.md`** — overwritten with
  SESSION_066 = Milestone 4 · Increment 1 (M4.1 core
  persistence) priority.

## Commit hashes

- `98d9e79` — `docs(m4-inc0): Milestone 4 planning pass — MILESTONE_4_PLANNING.md + SESSION_065 handoff + SESSION_066 priority`

## Exact SESSION_066 Milestone 4 · Increment 1 (M4.1) scope

**SESSION_066 = Milestone 4 · Increment 1 (M4.1 — core
persistence).** First implementation session for Milestone 4.

### Deliverable

The persistence layer for recon automation:

- `Vendor` model per `MILESTONE_4_PLANNING.md` §1.2 (fields:
  `dealership` FK NOT NULL, `name`, `slug` (unique-per-
  dealership), `categories` JSONField, `phone`, `email`,
  `notes`, `is_active` default True, timestamps).
- `ReconDecision` model per §1.1 (fields: `finding`
  OneToOne CASCADE, `dealership` FK NOT NULL, `tier`
  choices, `decided_by` FK SET_NULL, `decided_at`, `notes`,
  timestamps).
- `WorkOrder` model per §1.3 (fields: `vehicle` FK
  CASCADE, `dealership` FK NOT NULL, `category` choices,
  `venue` choices, `vendor` FK SET_NULL nullable, `assignee`
  FK SET_NULL nullable, `status` choices, `estimated_cost`,
  `authorized_cost`, `actual_cost`,
  `estimated_completion_date`, `actual_completion_date`,
  `notes`, plus provenance fields: `approved_at`,
  `approved_by`, `started_at`, `started_by`, `completed_at`,
  `completed_by`, `cancelled_at`, `cancelled_by`,
  `cancellation_reason`, timestamps).
- `WorkOrderFinding` through model per §1.4 (fields:
  `work_order` FK CASCADE, `finding` FK CASCADE,
  `dealership` FK NOT NULL, `created_at`, unique_together
  on `(work_order, finding)`).
- `WorkOrderPart` model per §1.5 (see planning §1.5 for
  fields including `status` six-value choices,
  `source_type`, `source_name`, timestamps for each state
  transition).
- `VendorCommunication` model per §1.6 (fields: `work_order`
  FK, `vendor` FK SET_NULL nullable, `dealership` FK NOT
  NULL, `kind` choices, `channel` choices, `direction`
  choices, `status` choices, `draft_content`, `sent_content`,
  `source_provenance` JSONField, `drafted_by`, `drafted_at`,
  `approved_by`, `approved_at`, `sent_by`, `sent_at`,
  timestamps).
- Migration `0016` (verify sequential via `showmigrations`).
- Admin registrations for all six models with list displays,
  filters, search — following the M2/M3 admin pattern.
- Module-level constants for all nine enum groups:
  - `WORK_ORDER_STATUS_CHOICES` (5 values).
  - `WORK_ORDER_VENUE_CHOICES` (2 values).
  - `RECON_DECISION_TIER_CHOICES` (3 values).
  - `WORK_ORDER_PART_STATUS_CHOICES` (6 values).
  - `WORK_ORDER_PART_SOURCE_TYPE_CHOICES` (3-5 values —
    finalize in M4.1 per RECON §6.1–§6.4).
  - `VENDOR_COMMUNICATION_KIND_CHOICES` (values including
    `vendor_comm`, `parts_order`, `narrative`).
  - `VENDOR_COMMUNICATION_CHANNEL_CHOICES` (values
    including `email`, `sms`, `phone`, `in_person`,
    `internal_note`).
  - `VENDOR_COMMUNICATION_DIRECTION_CHOICES` (`outbound`,
    `inbound`).
  - `VENDOR_COMMUNICATION_STATUS_CHOICES` (values including
    `draft`, `approved`, `sent`, `logged`).
- Cross-tenant `clean()` guards on all six models (same
  shape as `VehicleAcquisition.clean` / `VehicleCost.clean`
  / `ConditionReport.clean`).
- `services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES` tuple
  extended from 9 → 15 (one line per new carrier).
- `DATABASES["migration_check"]` alias verified against the
  new migration.

### What M4.1 does NOT ship

- ❌ No service module (`services/recon.py` +
  `services/vendor_comm.py` are M4.2 + M4.5).
- ❌ No `Vehicle` `@property` methods (`open_work_orders`,
  `has_recon_decisions` are M4.2).
- ❌ No estimate-to-ledger integration (M4.3).
- ❌ No parts-status transitions logic (M4.4 — model
  supports the enum but service-level transition logic
  is M4.4).
- ❌ No `_scrub_invented_recon_fact` (M4.5).
- ❌ No API endpoints (M4.6).
- ❌ No permission class (M4.6 introduces
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`).
- ❌ No frontend (M4.7).
- ❌ No AI role of any kind (M4.5 first).

### Test surface

~65 focused model tests:

- **Schema tests.** `dealership` FK NOT NULL on all six
  models (six mirrored tests).
- **Choices validation.** `full_clean()` rejects invalid
  values on each of the nine enum groups.
- **Enum vocabulary.** Each choices tuple contains exactly
  the documented number of values.
- **Cascade behavior.** Deleting a `Vehicle` cascades to
  `WorkOrder`; deleting a `WorkOrder` cascades to
  `WorkOrderPart` + `WorkOrderFinding` + `VendorCommunication`;
  deleting a `ConditionFinding` cascades to `ReconDecision`
  + `WorkOrderFinding`; deleting a `Vendor` does NOT cascade
  (SET_NULL on WO + VC — historical rows preserved).
- **Soft delete.** `Vendor.is_active=False` preserves the
  row; work orders + comms still readable in historical
  view.
- **Cross-tenant guards.** `clean()` on all six models
  rejects `dealership` mismatch against parent vehicle /
  finding / work_order / vendor.
- **`_TENANT_CARRIER_MODEL_NAMES` extension.** The six new
  carriers are registered by
  `register_default_dealership_autofill()` without breaking
  the nine existing ones.
- **Unique constraints.**
  `WorkOrderFinding.unique_together = ("work_order", "finding")`;
  `Vendor.slug` unique per dealership.
- **Vendor foreign-key nullability.** `WorkOrder.vendor`
  NULL for in-house venues; required (application-level,
  not DB) for outsourced venues (application enforcement
  lands in M4.2 service; M4.1 model-level test is
  presence of nullability + `venue` enum).
- **Provenance field defaults.** `WorkOrder.approved_by /
  started_by / completed_by / cancelled_by` all
  `null=True, blank=True` at model layer (state machine
  enforces set-on-transition in M4.2).

### Read-first list for SESSION_066

1. `docs/roadmap/MILESTONE_4_PLANNING.md` — §0 practices,
   §1.1 through §1.7 (all seven subsystem shapes), §2
   migration impact rows M4.1 satisfies, §3 M4-invariants
   checklist rows M4.1 must satisfy at close, §5.b + §5.c
   + §5.d + §5.f + §5.h (load-bearing decisions M4.1 must
   honor at the model layer), §7 M4.1 detail.
2. `backend/dealer_ai/models.py` — reread
   `VehicleAcquisition`, `VehicleCost`, `ConditionReport`,
   `ConditionFinding`, `ConditionFindingPhoto` as the
   persistence-layer template M4.1 mirrors, especially
   the `clean()` cross-tenant guards.
3. `backend/dealer_ai/services/tenancy.py` — the
   `_TENANT_CARRIER_MODEL_NAMES` tuple + the
   `register_default_dealership_autofill` function M4.1
   extends.
4. `backend/dealer_ai/tests/test_condition_report.py` +
   `test_condition_finding.py` (SESSION_056) — test shape
   M4.1 mirrors.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.1 entry —
   the "core models" increment shape M4.1 mirrors.

### Explicit non-goals for SESSION_066

- ❌ Do NOT write the service modules — those are M4.2 +
  M4.5.
- ❌ Do NOT add any `@property` on `Vehicle` — those are
  M4.2.
- ❌ Do NOT introduce `_scrub_invented_recon_fact` — that
  is M4.5.
- ❌ Do NOT add any endpoint — those are M4.6.
- ❌ Do NOT add the new permission class — that is M4.6.
- ❌ Do NOT change tenancy resolver signatures.
- ❌ Do NOT change safety pipeline.
- ❌ Do NOT reopen the M2 ledger surface.
- ❌ Do NOT reopen the M3 condition-report surface.
- ❌ Do NOT modify `VehicleCost.vendor` (per §5.b).
- ❌ Do NOT introduce any AI role.

### Boundary condition

Test baseline at SESSION_066 close: 2,124 → ~2,189 pass.
All new; zero regressions. Migration `0016` applied
cleanly. `makemigrations --check --dry-run` reports "No
changes detected." App remains deployable.

## Anchors that win on conflict (for SESSION_066)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_4_PLANNING.md` (this session's
   deliverable) — §1 design memo, §3 compatibility
   checklist, §5 load-bearing decisions, §7 increment
   sequencing.
6. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6 lessons
   + §8 M4 bootstrap.
7. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons.
8. `docs/roadmap/MILESTONE_3_PLANNING.md` §7 (increment
   shape template) + `MILESTONE_2_PLANNING.md` §7.b.
9. `docs/research/RECON_MAPPING.md` §§3–7 + §11 + §13.1 +
   §14 + §16 (business-truth for anything the planning
   artifact does not resolve).
10. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 3.
11. This handoff (`SESSION_065_m4_planning.md`) — the
    ten-decision resolutions + increment sequence + M4.1
    scope authoritative for the next session.
12. Current source code — the shipped M1 + M2 + M3
    surface (M4 inherits it unchanged).

Planning docs are claims. Rules + research + code are facts.
