---
title: "SESSION_066 handoff — Milestone 4 · Increment 1 (core recon persistence)"
status: historical
type: handoff
date: 2026-08-01
session: 066
milestone: 4
milestone_status: in-progress
increment: 1
increment_status: shipped
commit: 7c1eb7e
---

# SESSION_066 — Milestone 4 · Increment 1 (M4.1 — core recon persistence)

## What shipped

The persistence layer for the recon-automation domain. Six
new models (`Vendor`, `ReconDecision`, `WorkOrder`,
`WorkOrderFinding`, `WorkOrderPart`, `VendorCommunication`),
migration `0016`, nine module-level enum sets, cross-tenant
`clean()` guards on every model, tenancy-carrier registration
extended from 9 → 15, six new admin registrations, and 95
focused tests. **No service module, no state transitions, no
ledger integration, no scrubs, no endpoints, no frontend, no
AI.**

Also: three narrow **planning-doc refinements** to
`MILESTONE_4_PLANNING.md` — reviewed and approved at the top
of the session — locking the vendor deletion contract at the
schema layer, the estimate-retirement-on-completion contract
for the M4.3 ledger integration, and the split
`sent` vs `logged` requirement matrix on
`VendorCommunication`.

## Session preamble — the planning refinements

The user opened the session with three narrow refinements to
`MILESTONE_4_PLANNING.md` that had to land before code was
written, because each one is a persistence-contract issue
that would otherwise get discovered during M4.2 or M4.3
implementation:

1. **Vendor deletion contract.** The planning artifact said
   "vendors are soft-deleted; never hard-delete a referenced
   vendor," but the planned FK shapes on `WorkOrder.vendor`
   and `VendorCommunication.vendor` were `SET_NULL`. Those
   two are contradictory. Resolution: `Vendor.is_active=False`
   remains the normal removal path; `on_delete=PROTECT` on
   every FK pointing at Vendor **prevents hard-deletion at
   the schema layer** so the invariant is enforceable.
   Renames are still allowed and never rewrite the
   `VehicleCost.vendor` free-text snapshot on historical
   rows. Amended §1.2 + §1.3 + §1.6 + §3 + §5.b.

2. **Estimate retirement on completion.** The planning
   estimate-to-ledger section said estimate rows remain
   outstanding after actual cost posts, which would make
   `projected_total_investment` double-count completed work.
   Resolution: completion **reverses the outstanding
   estimate** atomically with the actual post, using a
   dedicated one-shot reference key
   (`WORKORDER:<id>:completion_estimate_reversal`) distinct
   from the mid-life revision keys and the cancel key. After
   any WorkOrder reaches a terminal state, the net estimate
   contribution for that WO in the ledger must be zero.
   Amended §3 + §5.e (full rewrite of bullets 3, 4;
   reference-key vocabulary locked as a five-family list)
   + §7 M4.3 sequencing (added `_post_completion_reversal`
   hook, transaction-atomic completion, new tests). No M4.1
   code impact — the field surface captures the shape M4.3
   consumes.

3. **VendorCommunication `logged` semantics separated from
   `sent`.** The planning artifact treated both `sent` and
   `logged` as requiring `approved_by` and `sent_by`. That
   is too broad for inbound calls or communications logged
   after the fact. Resolution:

   - AI-drafted outbound (kind=vendor_comm/parts_order):
     `draft → approved → sent`, requiring `approved_by`,
     `approved_at`, `sent_by`, `sent_at`, and nonblank
     `sent_content` at the sent transition.
   - Operator-recorded (channel=phone/in_person, inbound
     logging, narrative notes): may be created directly at
     `status='logged'`. `logged` requires a human actor
     (`sent_by`), a timestamp (`sent_at`), and a durable
     recorded body (`draft_content` nonblank). **No prior
     approval step required.**
   - "AI-generated content may never jump directly to
     logged" is enforceable only at the M4.5 service layer
     (a persistence-only guard cannot distinguish AI-drafted
     from operator-recorded rows); the invariant is
     documented but explicitly deferred to M4.5. Amended
     §1.6 field notes and §3 invariant matrix.

## Read-first pass performed

Per the start-here doc's recommended sequence, read in order:

1. `docs/roadmap/MILESTONE_4_PLANNING.md` — §0 practices, §1.1
   through §1.7 (all subsystem shapes), §2 migration impact,
   §3 compatibility checklist, §5.b + §5.c + §5.d + §5.e +
   §5.h load-bearing decisions, §7 M4.1 detail.
2. `docs/handoffs/SESSION_065_m4_planning.md` — the ten
   decision resolutions + Exact M4.1 scope section.
3. `backend/dealer_ai/models.py` — reread `VehicleAcquisition`,
   `VehicleCost`, `ConditionReport`, `ConditionFinding`,
   `ConditionFindingPhoto` (persistence-layer template + M2/M3
   enum + `clean()` cross-tenant guard shapes).
4. `backend/dealer_ai/services/tenancy.py` — reread
   `_TENANT_CARRIER_MODEL_NAMES` tuple and
   `register_default_dealership_autofill` handler.
5. `backend/dealer_ai/admin.py` — reread M2/M3 admin shapes.
6. `backend/dealer_ai/tests/test_condition_finding.py` +
   `test_condition_report.py` + `test_dealership.py`
   (WritePathFallback) — the test-file shape M4.1 mirrors.

## The planning-doc refinements — inline diff of the sections
touched

1. **§1.2 (Vendor).** `is_active` note rewritten to make
   PROTECT the enforcement of the "never hard-delete a
   referenced vendor" rule. Adds explicit citation of
   SESSION_066 as the point of introduction.
2. **§1.3 (WorkOrder.vendor).** FK annotation changed from
   `SET_NULL` to `PROTECT`.
3. **§1.6 (VendorCommunication.vendor).** FK annotation
   changed from `SET_NULL` to `PROTECT`. Rationale for
   `NULL` case documented (inbound rows authored before
   vendor identification).
4. **§3 model-layer invariants list.** Six new checklist
   rows added: WorkOrder.vendor PROTECT, VendorCommunication.vendor
   PROTECT, sent-state structural requirements, approved-
   state structural requirements, logged-state structural
   requirements, AI-drafted-cannot-jump-to-logged (deferred
   to M4.5 service layer).
5. **§3 ledger-integration invariants list.** Reference-tag
   invariant expanded to five families; two new invariants
   added: completion posts actual + estimate reversal
   atomically; net estimate contribution on terminal WO = 0;
   `projected_total_investment` no longer double-counts
   completed WOs.
6. **§5.b (Vendor entity migration).** "Soft-delete only"
   bullet rewritten to reflect that PROTECT enforces the
   invariant at the schema layer (Postgres/SQLite raise
   `ProtectedError`); admin surfaces mirror by not offering
   delete affordances on referenced vendors.
7. **§5.e (Estimate-to-ledger contract).** Full rewrite of
   the numbered bullet list. Load-bearing invariant surfaced
   at the top (net estimate contribution = 0 post-terminal).
   Bullets 1–5 restated with the new reference-key vocabulary.
   New reference-key module-constant list block added (five
   entries: `WORKORDER_LEDGER_REF_ESTIMATE`,
   `_REVERSAL`, `_COMPLETION_ESTIMATE_REVERSAL`,
   `_ESTIMATE_REVERSAL_CANCEL`, `_ACTUAL`). Semantic
   corollary on `projected_total_investment` added.
8. **§7 M4.3 sequencing.** `_post_completion_reversal` hook
   added; `_post_cancel_reversal` renamed for symmetry;
   `_post_estimate` signature updated to take explicit
   `seq`; `complete_work_order` wraps completion in
   `transaction.atomic()` block. Test list expanded with
   completion-time-reversal test, net-zero-on-terminal test,
   projected-does-not-double-count test, mid-completion-
   crash atomicity test.

Unrelated planning sections were not touched.

## Concrete deliverables

### Models (`backend/dealer_ai/models.py`)

Appended after `ConditionFindingPhoto` following the M2/M3
append convention.

- **`Vendor`** — 9 fields.
  - `dealership` (FK CASCADE, related_name `vendors`).
  - `name` (CharField 255, required).
  - `slug` (SlugField 64, unique-per-dealership via
    `Meta.constraints`).
  - `categories` (JSONField, default `list`) — free-form list
    of canonical category slugs; persistence layer does not
    validate contents.
  - `phone`, `email` (CharField 64 / EmailField, blank).
  - `notes` (TextField, blank).
  - `is_active` (Boolean, default True).
  - Timestamps.
  - `Meta.ordering = ("name",)`.
  - `Meta.constraints = [UniqueConstraint(("dealership", "slug"))]`.

- **`ReconDecision`** — 6 fields.
  - `finding` (OneToOneField CASCADE, related_name
    `recon_decision`).
  - `dealership` (FK CASCADE, related_name `recon_decisions`).
  - `tier` (CharField 16, choices from
    `RECON_DECISION_TIER_CHOICES`).
  - `decided_by` (FK to `AUTH_USER_MODEL`, nullable
    SET_NULL, `related_name="+"`).
  - `decided_at` (DateTimeField, required).
  - `notes` (TextField, blank).
  - Timestamps.
  - `Meta.ordering = ("-decided_at", "-created_at")`.
  - `clean()` enforces cross-tenant guard via
    `finding.report.vehicle.dealership`.

- **`WorkOrder`** — 17 domain fields + 8 provenance fields.
  - `vehicle` (FK CASCADE, related_name `work_orders`).
  - `dealership` (FK CASCADE, related_name `work_orders`).
  - `category` (CharField 32, choices from
    `CONDITION_CATEGORY_CHOICES` — **reused, not
    duplicated**).
  - `venue` (CharField 16, choices from
    `WORK_ORDER_VENUE_CHOICES`).
  - `vendor` (FK **PROTECT** nullable, related_name
    `work_orders`).
  - `assignee` (FK to `AUTH_USER_MODEL`, nullable SET_NULL).
  - `status` (CharField 16, choices from
    `WORK_ORDER_STATUS_CHOICES`, default `draft`).
  - `estimated_cost`, `authorized_cost`, `actual_cost`
    (DecimalField 10.2, nullable).
  - `estimated_completion_date`, `actual_completion_date`
    (DateField, nullable).
  - `notes` (TextField, blank).
  - Provenance × 4 pairs: `approved_at` + `approved_by`;
    `started_at` + `started_by`; `completed_at` +
    `completed_by`; `cancelled_at` + `cancelled_by`. All
    nullable at persistence.
  - `cancellation_reason` (TextField, blank).
  - Timestamps.
  - `Meta.ordering = ("-created_at",)`.
  - `clean()` enforces three invariants: cross-tenant
    vehicle guard, outsourced-requires-vendor guard,
    cross-tenant vendor guard.

- **`WorkOrderFinding`** — 3 core fields + created_at.
  - `work_order` (FK CASCADE, related_name `finding_links`).
  - `finding` (FK CASCADE, related_name `work_order_links`).
  - `dealership` (FK CASCADE, related_name
    `work_order_findings`).
  - `created_at`.
  - `Meta.ordering = ("-created_at",)`.
  - `Meta.constraints = [UniqueConstraint(("work_order", "finding"))]`.
  - `clean()` enforces three invariants: dealership matches
    WO tenant, dealership matches finding tenant chain,
    WO.vehicle == finding.report.vehicle (cross-vehicle
    links prohibited).

- **`WorkOrderPart`** — 12 fields.
  - `work_order` (FK CASCADE, related_name `parts`).
  - `dealership` (FK CASCADE, related_name
    `work_order_parts`).
  - `name` (CharField 255, required).
  - `description` (TextField, blank).
  - `part_number` (CharField 128, blank).
  - `quantity` (PositiveIntegerField default 1, validated
    `>= 1` via `MinValueValidator(1)`).
  - `unit_cost` (DecimalField 10.2, nullable).
  - `status` (CharField 16, choices from
    `WORK_ORDER_PART_STATUS_CHOICES`, default `needed`).
  - `source_type` (CharField 32, choices from
    `WORK_ORDER_PART_SOURCE_TYPE_CHOICES`, default
    `in_stock`).
  - `source_name` (CharField 255, blank).
  - Per-state date fields: `ordered_at`, `received_at`,
    `installed_at`, `returned_at` (all nullable, not
    auto-populated at model layer).
  - `notes` (TextField, blank).
  - Timestamps.
  - `Meta.ordering = ("-created_at",)`.
  - `clean()` enforces cross-tenant guard against WorkOrder
    tenant.

- **`VendorCommunication`** — 17 fields.
  - `dealership` (FK CASCADE, related_name
    `vendor_communications`).
  - `vendor` (FK **PROTECT** nullable, related_name
    `communications`).
  - `work_order` (FK SET_NULL nullable, related_name
    `communications`).
  - `kind`, `channel`, `direction`, `status` (CharField 16
    from `VENDOR_COMMUNICATION_*_CHOICES`).
  - `draft_content` (TextField, blank).
  - `sent_content` (TextField, blank).
  - `source_provenance` (JSONField, default `dict`).
  - `notes` (TextField, blank).
  - Actor + timestamp × 3 pairs: `drafted_by` +
    `drafted_at`; `approved_by` + `approved_at`; `sent_by`
    + `sent_at`. All nullable at persistence.
  - Timestamps.
  - `Meta.ordering = ("-created_at",)`.
  - `clean()` enforces the full SESSION_066 refinement
    invariant matrix (see class docstring for the table).

### Enums (`backend/dealer_ai/models.py`)

Nine module-level constant sets. Each individual value has a
module-level constant per the M2/M3 house pattern — not just
the choice tuple. Total: 42 individual constants + 9 tuples.

- `RECON_DECISION_TIER_CHOICES` — 3 values.
- `WORK_ORDER_STATUS_CHOICES` — 5 values.
- `WORK_ORDER_VENUE_CHOICES` — 2 values.
- `WORK_ORDER_PART_STATUS_CHOICES` — 6 values.
- `WORK_ORDER_PART_SOURCE_TYPE_CHOICES` — 7 values (includes
  `customer_supplied` finalized at SESSION_066).
- `VENDOR_COMMUNICATION_KIND_CHOICES` — 3 values (`vendor_comm`,
  `parts_order`, `narrative`).
- `VENDOR_COMMUNICATION_CHANNEL_CHOICES` — 5 values.
- `VENDOR_COMMUNICATION_DIRECTION_CHOICES` — 2 values.
- `VENDOR_COMMUNICATION_STATUS_CHOICES` — 4 values (no
  `failed` in M4.1; retry / bounce handling deferred).

`WorkOrder.category` reuses `CONDITION_CATEGORY_CHOICES` (12
values from M3.1). **Not duplicated** — locked by
`WorkOrderCategoryReusesConditionVocabulary` test.

### Migration

- `backend/dealer_ai/migrations/0016_recon_persistence.py`
  — Django-generated, renamed from the auto-slug to a
  cleaner name; no hand-edits to the migration body.
  Creates all six models, both unique constraints, and every
  FK. No schema drift beyond `0016`.
- Round-tripped clean-slate against
  `DATABASES["migration_check"]` per M1 lesson 2: applied
  forward, rolled back to 0015, reapplied — all clean, no
  data loss.

### Tenancy carrier extension

- `backend/dealer_ai/services/tenancy.py`
  `_TENANT_CARRIER_MODEL_NAMES` extended from 9 → 15. Six
  new entries added at the end of the tuple with a comment
  tying the extension to `MILESTONE_4_PLANNING.md` §2 row 4.
  Resolver contract unchanged; only the tuple grew.

### Admin registrations

Six new diagnostic admins, each following the M2/M3
read-mostly pattern (`list_display` / `list_filter` /
`search_fields` / `autocomplete_fields` / `readonly_fields`).

- `VendorAdmin` — plus `prepopulated_fields = {"slug": ("name",)}`
  and **`has_delete_permission` overridden to return False**
  so the admin does not offer a delete button that would
  fail confusingly at DB layer against a PROTECT-referenced
  vendor.
- `ReconDecisionAdmin` — filters on `tier`.
- `WorkOrderAdmin` — filters on `status` / `venue` /
  `category`.
- `WorkOrderFindingAdmin` — minimal through-table
  diagnostic surface.
- `WorkOrderPartAdmin` — filters on `status` / `source_type`.
- `VendorCommunicationAdmin` — filters on `status` / `kind`
  / `channel` / `direction`.

No workflow buttons, no transition actions, no AI
generation, no ledger posting affordances on any admin
surface.

### Tests

Domain-organized per the SESSION_066 brief's pushback on
"one file per model" fragmentation — four focused files
covering the six models by tightly-related domain surface,
plus one shared file for admin registrations and one
extension to `test_dealership.py` for tenancy-carrier
autofill.

- `backend/dealer_ai/tests/test_vendor.py` — 12 tests:
  create round-trip, categories default, is_active default,
  inactive persists, slug unique-per-dealership + not
  globally, duplicate slug rejected within dealership,
  dealership NOT NULL, unreferenced delete succeeds,
  WorkOrder-referenced delete raises ProtectedError,
  VendorCommunication-referenced delete raises
  ProtectedError, deactivation always succeeds, `__str__`,
  ordering.
- `backend/dealer_ai/tests/test_recon_decision.py` — 12
  tests: tier vocabulary (3 canonical), all-fields round-
  trip, invalid tier rejected, notes optional, second
  decision on same finding raises IntegrityError,
  dealership NOT NULL, cross-tenant clean guard
  (match/mismatch), cascade on finding delete,
  creating-decision-creates-no-WorkOrder,
  creating-decision-creates-no-VehicleCost.
- `backend/dealer_ai/tests/test_work_order.py` — 30 tests
  across WorkOrder + WorkOrderFinding + WorkOrderPart:
  status vocabulary (5), venue vocabulary (2), category
  reuses CONDITION_CATEGORY_CHOICES, in-house + outsourced
  round-trips, invalid status rejected, outsourced-requires-
  vendor guard, cross-tenant vehicle rejected, cross-tenant
  vendor rejected, all-match passes, dealership NOT NULL,
  cascade on vehicle delete, creating-WO-creates-no-
  VehicleCost, WOF many-to-many both directions, WOF unique
  pair, cross-vehicle link rejected, cross-tenant link
  chains rejected, WOF cascade on WO / finding delete,
  WOP status vocabulary (6), WOP source-type vocabulary
  (7 including customer_supplied), WOP round-trip + defaults,
  WOP quantity >= 1 (zero rejected, one passes), WOP
  cross-tenant guard, WOP cascade on WO delete, WOP
  status-installed-with-null-timestamp persists (locks
  "not auto-transitioned" invariant).
- `backend/dealer_ai/tests/test_vendor_communication.py` —
  29 tests: four vocabulary tests (kind, channel with 5
  values, direction with 2, status with 4), draft round-
  trip, source_provenance default empty dict,
  approved-state without approved_by / without approved_at
  rejected, approved-state with both passes, sent-state all
  fields pass, sent-state without sent_content / whitespace-
  only / without approved_by / without sent_by / without
  sent_at rejected (5 negative cases), logged-state without
  approval fields passes (SESSION_066 load-bearing
  assertion), logged-state without draft_content / without
  sent_by / without sent_at rejected, logged-state with only
  approved fields still rejected (locks the sent_by
  requirement even if approved fields are supplied), cross-
  tenant vendor / WO / paired-mismatch guards, all-match
  passes, null-vendor-permitted-on-inbound-logged, work_order
  SET_NULL on delete (leaves comm intact), dealership NOT
  NULL.
- `backend/dealer_ai/tests/test_admin_recon.py` — 7 tests:
  all six models registered with the admin site;
  Vendor admin `has_delete_permission` returns False at both
  list-level and object-level.
- `backend/dealer_ai/tests/test_dealership.py` —
  `WritePathFallback` extended with 6 new autofill tests,
  one per new carrier.

**Total new tests: 95** (89 focused across the four M4.1
test files + 1 admin + 6 tenancy-carrier autofill).

Domain grouping avoided six-file fragmentation. `test_work_order.py`
covers three tightly-coupled models (WorkOrder is the
parent; findings + parts hang off it) — the alternative would
have been two very short files plus one normal file. Per
brief, "the test count is a forecast, not a requirement."

## Verification evidence

- `python3 manage.py test dealer_ai` → **2,219 pass, 1
  skipped, 0 fail** (up from 2,124; +95 new tests).
- `python3 manage.py check` → "System check identified no
  issues (0 silenced)."
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected."
- `python3 manage.py showmigrations dealer_ai` → `0001` –
  `0016` all applied.
- Migration round-trip on `migration_check` DB: forward,
  rollback to `0015`, reapply — all three legs clean, no
  errors.
- `git status --short frontend/` → empty (no frontend files
  changed).
- Django admin renders all six new registrations without
  errors (verified via `check` — Django's admin registry
  validation runs at check time).

## Compatibility (Milestone 1 + Milestone 2 + Milestone 3
substrate)

Preserved unchanged:

- **Tenancy substrate.** `Dealership` model unchanged.
  `get_default_dealership` / `get_current_dealership` /
  `get_active_membership` signatures unchanged. Every
  existing tenant carrier still has `dealership` FK NOT
  NULL. Tuple grew 9 → 15 additively.
- **Identity + authentication.** No
  `DEFAULT_PERMISSION_CLASSES` change. Auth endpoints
  unchanged. CSRF still enforced.
- **Endpoint-level permissions.** Zero changes to
  `dealer_ai/permissions.py`. (M4 permission class lands
  in M4.6, not this session.)
- **Safety stack.** Zero changes to
  `services/llm_safety.py`. M2.5 `_scrub_acquisition_price`
  unchanged. No new scrub in M4.1.
- **Customer-facing surfaces.** No changes. No recon /
  vendor / work-order data appears in any customer-facing
  response body.
- **M2 ledger substrate.** `services/vehicle_ledger.py` API
  unchanged. `Vehicle.ledger_totals` + delegators unchanged.
  `VehicleCost` immutability unchanged. `total_investment`
  semantic contract unchanged. `VehicleCost.vendor` free-
  text field unchanged. **M4.1 posts zero VehicleCost rows**
  — the ledger integration lands in M4.3 (locked by
  `WorkOrderNoLedgerSideEffects` test).
- **M3 substrate.** `services/condition_report.py` API
  unchanged. `Vehicle.latest_condition_report` /
  `latest_completed_condition_report` unchanged.
  `services/photo_storage.py` API unchanged. Completed
  condition reports remain immutable. `ConditionFinding.estimated_cost`
  still documentation-only (M3.5 invariant locked by three
  pre-existing tests, all still passing). M3.6A/B admin
  API + M3.7 operator UI unchanged.
- **Dealer identity resolution.** `get_dealer_name()` /
  `get_dealer_profile()` / `get_floor_plan_apr()`
  unchanged.
- **Frontend contracts.** `useBrand()` / `useDealerProfile()`
  / `brand.*` Tailwind tokens / `authFetch` / `AuthContext`
  / `RequireAuth` / `LoginPage` unchanged (no frontend
  files touched).

## Explicitly out of scope for M4.1 (deferred to specific
increments, unchanged)

- ❌ Service module (`services/recon.py`) — M4.2.
- ❌ Vendor communication service (`services/vendor_comm.py`)
  — M4.5.
- ❌ Vehicle `@property` accessors (`open_work_orders`,
  `has_recon_decisions`) — M4.2.
- ❌ Ledger integration + reference-key vocabulary + estimate-
  retirement-on-completion implementation — M4.3 (planning
  amendment landed here; code lands in M4.3).
- ❌ Parts service (state transitions, timestamp population)
  — M4.4.
- ❌ `_scrub_invented_recon_fact` post-LLM scrub — M4.5.
- ❌ New permission class
  (`IsReconManagerSalesManagerOrOwnerAtActiveDealership`)
  — M4.6.
- ❌ Admin API endpoints — M4.6.
- ❌ Frontend (`VehicleReconPage.tsx`, extracted components,
  API helpers) — M4.7.
- ❌ Prod deployment / send workflow — post-M4 pre-pilot pass
  (planning §5.j).
- ❌ AI role — nowhere in M4.1.

## Files changed

- `backend/dealer_ai/models.py` — added `MinValueValidator`
  import; appended nine enum sets (42 individual constants +
  9 choice tuples) and six model classes at end (after
  `ConditionFindingPhoto`).
- `backend/dealer_ai/services/tenancy.py` — extended
  `_TENANT_CARRIER_MODEL_NAMES` tuple 9 → 15 with a comment
  block tying the extension to `MILESTONE_4_PLANNING.md` §2
  row 4.
- `backend/dealer_ai/admin.py` — added six admin
  registrations + updated the `from .models import` list.
  `VendorAdmin.has_delete_permission` overridden to False.
- `backend/dealer_ai/migrations/0016_recon_persistence.py`
  — new file (renamed from auto-slug).
- `backend/dealer_ai/tests/test_vendor.py` — new file (12
  tests).
- `backend/dealer_ai/tests/test_recon_decision.py` — new file
  (12 tests).
- `backend/dealer_ai/tests/test_work_order.py` — new file (30
  tests across WorkOrder + WorkOrderFinding + WorkOrderPart).
- `backend/dealer_ai/tests/test_vendor_communication.py` —
  new file (29 tests).
- `backend/dealer_ai/tests/test_admin_recon.py` — new file
  (7 tests).
- `backend/dealer_ai/tests/test_dealership.py` — extended
  `WritePathFallback` with 6 M4.1 carrier autofill tests
  (one per new carrier).
- `docs/roadmap/MILESTONE_4_PLANNING.md` — three narrow
  refinements per session preamble above; unrelated
  sections untouched.
- `docs/handoffs/SESSION_066_m4_inc1_core_models.md` — this
  handoff.
- `00-START-NEXT-SESSION.md` — overwritten with SESSION_067
  = M4.2 priority.

## Recommended exact scope for SESSION_067 (M4.2 — recon service
+ WorkOrder state machine)

Per `MILESTONE_4_PLANNING.md` §7 M4.2 (locked at SESSION_065;
unchanged by this session):

**Scope.** `backend/dealer_ai/services/recon.py` with these
exported functions, each threading `dealership=` explicitly
per `AUTHENTICATION_MODEL.md` §8b:

- `record_decision(finding, *, dealership, tier, decided_by,
  notes="") -> ReconDecision` — refuses when
  `finding.report.status != "complete"` (analog to M3.2's
  `_refresh_and_assert_draft` but reversed); refuses
  cross-tenant; one-per-finding enforced by OneToOne (raises
  IntegrityError if second decision attempted).
- `create_work_order(vehicle, *, dealership, category, venue,
  vendor=None, assignee=None, estimated_cost=None,
  estimated_completion_date=None, notes="") -> WorkOrder`
  — always creates in `status="draft"`.
- `attach_findings(work_order, *, dealership, finding_ids:
  list[int]) -> list[WorkOrderFinding]` — creates the
  through-table rows; refuses if any finding is cross-tenant
  or from a non-completed report; refuses if WO status is
  not `draft`.
- `detach_finding(work_order, finding, *, dealership) -> None`
  — refuses when WO status is not `draft`.
- `approve_work_order(work_order, *, dealership, approved_by,
  authorized_cost=None) -> WorkOrder` — draft→approved
  transition; sets `approved_at` + `approved_by` atomically.
  **Ledger-posting hook is a stub or no-op in M4.2** — the
  actual `_post_estimate` call lands in M4.3 wired to the
  reference-key vocabulary refined at SESSION_066.
- `start_work_order(work_order, *, dealership, started_by)
  -> WorkOrder` — approved→in_progress.
- `complete_work_order(work_order, *, dealership,
  completed_by, actual_cost, actual_completion_date=None)
  -> WorkOrder` — approved/in_progress→completed; sets
  actual_cost + actual_completion_date + completed_by +
  completed_at atomically. **Ledger-posting hook is a stub
  or no-op in M4.2** — completion-time atomic reversal + actual
  post lands in M4.3 per the SESSION_066 refinement.
- `cancel_work_order(work_order, *, dealership, cancelled_by,
  cancellation_reason="") -> WorkOrder` — any non-terminal
  state → cancelled. **Ledger reversing-entry hook is a stub
  in M4.2** — lands in M4.3.
- Two new `@property` accessors on `Vehicle`:
  `open_work_orders` (queryset of non-terminal WOs) and
  `has_recon_decisions` (bool: latest completed condition
  report has at least one attached decision). Function-local
  imports per M3.3 pattern.
- `CrossTenantReconError(ValueError)` — fail-closed guard at
  every service entry.
- `ReconImmutableError(ValueError)` — refused state
  transition. Distinct class so M4.6 API can map to 409.

Every function must call `full_clean()` before save (per
retro §6 lesson 4). Every function must raise the
cross-tenant error at entry — mismatched `dealership=`
against `vehicle.dealership` / `finding.report.vehicle.dealership`
/ `work_order.vehicle.dealership` short-circuits before
touching the ORM.

**Tests target.** ~55 focused service tests covering:
decision semantics (one-per-finding, completed-report
required, cross-tenant refusal); state-machine transitions
(each allowed transition succeeds; each disallowed raises);
attach/detach findings (cross-tenant refusal, through-table
integrity, draft-only gating); `_refresh_and_assert_status`
pattern; `full_clean` before save on every write path.

**Boundary.** Backend baseline: 2,219 → ~2,274. No
migrations. No frontend.

**Explicit non-goals for M4.2.**

- ❌ Do NOT implement the ledger integration hooks
  (`_post_estimate`, `_post_actual`,
  `_post_completion_reversal`, `_post_cancel_reversal`)
  — those land in M4.3 per the SESSION_066 planning
  refinement. Leave the state-transition service with
  stub or no-op ledger calls that M4.3 will replace with
  the real implementation.
- ❌ Do NOT create a `VehicleCost` row from any M4.2
  service function.
- ❌ Do NOT modify the M4.1 model shape unless a test
  reveals a real defect (raise as a scope question first,
  do not silently patch).
- ❌ Do NOT touch M4.4+ scope (parts service,
  VendorCommunication drafting, endpoints, frontend).

## Anchors that win on conflict for SESSION_067

1. `docs/PROJECT_RULES.md` — six governance rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every service
   entry point inherits the tenancy substrate. §8b threads
   `dealership=` explicitly.
5. `docs/roadmap/MILESTONE_4_PLANNING.md` — §1.1 – §1.6
   locked field shapes (annotated for M4.1 SHIPPED here);
   §5.b / §5.c / §5.e (SESSION_066 refinements) load-
   bearing decisions; §7 M4.2 locks service signatures.
6. `docs/handoffs/SESSION_066_m4_inc1_core_models.md` — this
   handoff.
7. `docs/handoffs/SESSION_065_m4_planning.md` —
   the ten-decision resolutions authoritative for the
   overall M4.
8. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6 lessons.
9. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons.
10. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b M2.2 entry
    (the shape M4.2 mirrors — extracted service module with
    fail-closed cross-tenant guard).
11. `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.2 entry
    (the shape M4.2 mirrors most closely — service module
    with state machine + entry-guarded cross-tenant
    resolution).
12. `docs/research/RECON_MAPPING.md` §3.1 (recon-decision
    framework), §4.2 (R.O. as work order), §5 (vendor
    categories), §14 (bottlenecks driving state semantics).
