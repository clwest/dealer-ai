---
title: "Milestone 25 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-03
sessions: SESSION_185 → SESSION_187
milestone: 25
milestone_name: "Lead-to-Test-Drive Operational Completion"
related:
  - docs/roadmap/MILESTONE_25_PLANNING.md
  - docs/roadmap/MILESTONE_24_RETROSPECTIVE.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7z
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 25
---

# Milestone 25 — Retrospective

Written at Milestone 25 close (SESSION_187, close-out folded into
M25.2 per §5.h evidence-sized Option B). Records what was planned,
what shipped, what deviated and why, and lessons carried forward
for Milestone 26. Mirrors `MILESTONE_24_RETROSPECTIVE.md` shape.

## 1. Planned scope

`MILESTONE_25_PLANNING.md` at SESSION_184 close (skeleton) and
SESSION_185 (full active memo) defined the milestone as
**Lead-to-Test-Drive Operational Completion** — bundle of
Candidate A3 (lead-source attribution display, NEW at M24.1 open)
+ Candidate A4 (test-drive UI, NEW at M24.1 open) identified via
the primary operational-coverage lens at M24 close.

**Anchor business question:** *Can a salesperson receive a lead,
understand exactly where it came from, assign it, and schedule
the customer's test drive entirely through the normal product
workflow?*

**Three increments planned** (§5.f evidence-sized shape):

- **M25.0** — planning refinement + all §5 locks (SESSION_185).
- **M25.1** — attribution display + JSONField backend addition
  (SESSION_186).
- **M25.2** — test-drive UI (modal-only per §5.d) with **M25.3
  close-out folding** per §5.h if evidence permits (SESSION_187).

**All eight §5 locks** established at M25.0 open:

- §5.a — A3 + A4 bundle framed as "Lead-to-Test-Drive
  Operational Completion."
- §5.b — Attribution persistence: Option A · JSONField variant
  (`CustomerLead.source_metadata`).
- §5.c — Attribution display: display-only, no navigation.
- §5.d — Test-drive form attachment: modal-only. Secondary
  launch on `DealerAiSalesTestDrives` deferred.
- §5.e — Vehicle picker: `interested_vehicles` as suggested +
  full tenant inventory as fallback.
- §5.f — 3 increments; M25.3 close-out folds per evidence.
- §5.g — DoD compliance: extend M24.3 + M24.4 journeys in M25.1;
  add `sales/lead_to_test_drive.spec.ts` in M25.2.
- §5.h — Evidence-sized close-out fold; coordinated push at
  close.

## 2. What actually shipped

**Ships matched the planned scope exactly plus one additive
backend endpoint surfaced by M25.2-open empirical discovery
(user-confirmed Option A).**

### M25.0 — planning refinement (SESSION_185)

- Full active memo expansion at `MILESTONE_25_PLANNING.md` with
  all eight §5 locks.
- Handoff at `docs/handoffs/SESSION_185_m25_inc0_planning.md`.
- Audit artifact regenerated (post-M24 baseline: 113 covered /
  40 backend-only).
- Two mid-planning refinements recorded honestly: §5.b JSONField
  selection over CharField (durability rationale) and §5.d
  modal-only over dual entry points (new durable "one workflow
  beats two overlapping" principle captured as user-feedback
  memory).
- **Commit: `4e0a958`** (+ hash backfill `d46d7df`).

### M25.1 — attribution display + JSONField backend (SESSION_186)

- **Backend:** `CustomerLead.source_metadata =
  JSONField(blank=True, default=dict)` + typed accessor
  `get_source_platform() -> str`. Migration
  `0049_customerlead_source_metadata` (single `AddField`, no
  backfill). `CustomerLeadSerializer` extended additively with
  `channel` + `referrer` + `referrer_name` +
  `source_metadata`. `record_webhook_lead` writes
  `source_metadata={"platform": platform}` at persistence
  time (before M25.1 the platform string was used only to
  dispatch the adapter, then discarded).
- **Frontend:** `LeadDetailResponse.lead` TS interface extended
  with the four new attribution fields. `LeadDetailModal`
  renders a new "Source" section per §5.c channel-specific
  rules (referral → "Referred by: {name}"; listing_form →
  "Source: {platform_label}"; chat/walk_in/phone/other →
  omitted). Pure helpers `displayPlatform` +
  `computeSourceLine` exported for direct Vitest coverage.
- **Tests:** +2 admin_lead_detail attribution tests (backend);
  +10 source-line unit tests (frontend); M24.3 referral +
  M24.4 webhook Playwright journeys extended with modal
  Source-line assertions.
- **Baselines at close:** 4,782 backend (+2), 219 frontend
  (+10), 13 acceptance journeys.
- **Commit: `368fe37`** (+ hash backfill `64c8341`).
- **Closes M24.1-open §3 deferrals 13 + 14.**

### M25.2 — test-drive UI + admin vehicle list endpoint (SESSION_187)

- **Backend:** New `GET /admin/vehicles/` endpoint following
  the M11.6 `admin/test-drives/list/` precedent — thin
  QuerySet wrapper, tenant-scoped filter, optional
  `search`/`condition`/`is_available` querystrings, cap at 100
  rows. Reuses M4 `IsSalesManagerOrOwnerAtActiveDealership`.
  `seed_journey_sales_operational_entry` extended with one
  deterministic Vehicle fixture (`M25-TEST-DRIVE-01`, 2025
  Ford Bronco Wildtrak) for the M25.2 journey picker.
  Idempotent via `get_or_create`.
- **Frontend:** `salesApi.ts::listAdminVehicles` typed
  wrapper. `<RecordTestDriveForm>` component in
  `components/sales/` matching the M24.1 `<LeadIntakeForm>`
  substrate pattern. Two-zone vehicle picker per §5.e
  (suggested from `detail.interested_vehicles` + full
  inventory with debounced search). Optional
  duration/route/reaction/objections/next-action fields.
  `LeadDetailModal` collapsible "Schedule test drive" section
  between "Interested vehicles" and "AI summary." Modal-only
  per §5.d. Recorded success badge in the header after
  submit.
- **Tests:** +11 admin_vehicle_list tests (backend, new file);
  +7 RecordTestDriveForm tests (frontend, new file); +1 new
  Playwright journey `sales/lead_to_test_drive.spec.ts`.
- **Baselines at close:** 4,793 backend (+11), 226 frontend
  (+7), **14 acceptance journeys** (13 → 14), 20 total
  including setup on clean-DB run (~30s).
- **Commit: `27cbe87`** (+ hash backfill `c8302f5`).
- **Closes M24.1-open §3 deferral 12.**
- **Close-out folded into M25.2 session per §5.h** (this
  retrospective + roadmap update + audit rerun + M26
  handoff all land at SESSION_187 close).

### Aggregate M25 impact

- **Baseline growth:** backend 4,780 → **4,793** (+13);
  frontend 209 → **226** (+17); acceptance 13 → **14**
  journeys (+1 new + 2 extended assertions on M24.3 + M24.4).
- **Migrations:** 1 (`0049_customerlead_source_metadata`).
- **New endpoints:** 1 (`admin/vehicles/`). No new permission
  classes.
- **New components:** 1 (`<RecordTestDriveForm>`).
- **New API wrappers:** 1 (`listAdminVehicles`).
- **New seed fixtures:** 1 (`M25-TEST-DRIVE-01` vehicle).
- **New Playwright journeys:** 1
  (`sales/lead_to_test_drive.spec.ts`).
- **M24.1-open §3 deferrals closed:** 12 + 13 + 14 (all three).

## 3. Deviations vs. planning memo

### 3.1 §5.b JSONField selection at M25.0 open

**Planned at M24.5 skeleton close:** "small UI extension
(~10-line addition)" for platform display, on the assumption
that platform was persisted.

**Empirical discovery at M25.0 open:** `platform` was not
persisted on `CustomerLead` — the webhook adapter dispatched
on it then discarded it. §3 deferral 14 required a backend
model addition, not display-only work.

**Refinement locked at M25.0 open:** Option A · JSONField
variant (`source_metadata`) over CharField. Rationale:
extension-without-migration durability, matches codebase
JSON precedent (`ChatSession.extracted_profile`,
`TestDrive.objections_captured`), preserves query support.
User confirmed after considering both variants + Option B
(descope) + Option C (notes field).

**Character:** empirical-discovery refinement of the M25
planning contract, presented at open. Not a mid-implementation
correction — the discovery came before scope commit. Streak
integrity preserved.

### 3.2 §5.d modal-only lock at M25.0 open

**Initial recommendation at M25.0 open:** modal-attached
primary + secondary "+ Record test drive" button on
`DealerAiSalesTestDrives` page.

**User redirect:** rejected the secondary launch point.
Principle: "one operational workflow is stronger than two
partially overlapping ones." Secondary launch deferred to
M26+ pending operator evidence.

**Captured:** new durable design principle recorded as user
feedback memory (`feedback_one_workflow_over_two_
overlapping.md`) so future M25+ planning defaults to
single-canonical-workflow posture at attachment-point
decisions.

### 3.3 admin/vehicles/ endpoint addition at M25.2 open

**Planned at M25.0 §5.e:** "Fetched via the existing
vehicle-list endpoint (verify precise endpoint at M25.2
open; likely /admin/vehicles/ or equivalent)."

**Empirical discovery at M25.2 open:** no admin tenant-wide
vehicle-list endpoint existed. Every `admin/vehicles/*`
route was stock-scoped. The picker's "All inventory"
fallback would shut out walk-in / phone / referral leads
(empty `interested_vehicles`), defeating the workflow-
completion narrative.

**Refinement locked at M25.2 open:** Option A · additive
`GET /admin/vehicles/` following the M11.6
`admin/test-drives/list/` precedent. Small (~30 lines), reuses
existing M4 permission class, no domain logic. User
confirmed after considering both Options B (interested-only,
rejected — shuts out three channels) and C (manual stock
entry, rejected — operator-hostile).

**Character:** second empirical-discovery refinement of the
milestone (same shape as §5.b — planning-open verification
surfaced an assumption that turned out wrong). Recorded
honestly.

### 3.4 §5.h close-out fold applied

**Planned:** "If M25.1 and M25.2 both ship cleanly with no
operator-surface fixes required at close, fold the close-out
into the M25.2 session."

**Applied:** M25.1 and M25.2 both shipped cleanly. Fold
applied — this retrospective + roadmap update + audit rerun
+ M26 handoff all land at SESSION_187 close. Coordinated push
of all M25 commits presented for user confirmation per
§5.h.

**Character:** as-planned execution of the evidence-sized
fold posture.

## 4. Deferrals reviewed

**M24.1-open §3 deferrals — all three closed by M25:**

- §3 deferral 12 (test-drive UI) — closed by M25.2.
- §3 deferral 13 (referrer display in modal) — closed by
  M25.1.
- §3 deferral 14 (platform display in modal for webhook
  leads) — closed by M25.1 (required JSONField backend
  addition per §3.1 above).

**M25 §3 deferrals recorded for M26+:**

- Secondary "+ Record test drive" launch point on
  `DealerAiSalesTestDrives` — deferred per §5.d
  "one-workflow" principle. Re-entry requires operator
  evidence.
- Clickable/navigable "Referred by" attribution link —
  deferred per §5.c display-only lock. Re-entry requires
  operator evidence.
- Test-drive edit/delete UI — deferred; records are
  immutable per M11.2 subsidiary-log design.
- Named-platform adapters (Autotrader/Cars.com/etc.) —
  deferred; JSONField substrate ready when needed.
- Analytics/rollup surfaces (e.g. "all Autotrader leads
  this month") — deferred; JSONField query support enables.
- Vehicle picker advanced filters (year/make/model
  dropdowns) — deferred; search substring suffices in M25.2.
- `interested_vehicles` editing from modal — deferred;
  vehicle attach at test-drive time writes to
  `TestDrive.vehicle`, not back to
  `CustomerLead.interested_vehicles`.
- Test-drive scheduling in advance (as opposed to recording
  post-drive) — deferred; M11.2 `driven_at` defaults to
  `timezone.now()`, form allows override but primary use
  case is post-drive.
- Salesperson/advisor role distinction on test-drive
  create — deferred per M11.2 posture.

**Pre-existing audit-script gap surfaced during M25.3:**
`admin/test-drives/list/` (M11.6) and the new
`admin/vehicles/` endpoint are both consumed by the shipped
UI but reported as `defer-candidate-O2` in the audit
artifact. Root cause: the audit's TypeScript template-literal
parser does not resolve `${qs ? \`?${qs}\` : ""}` trailing
templates to a URL that matches the Django URL pattern. Both
endpoints are `covered` in reality (M11.6 test-drives/list/
by `DealerAiSalesTestDrives.tsx`; M25.2 vehicles/ by
`RecordTestDriveForm.tsx`). Actual audit-accurate coverage
is **116 / 154** vs. the artifact's reported 114 / 154.
**Recorded as M26 candidate:** small bounded audit-script
refinement to handle the trailing-optional-querystring
template pattern. Matches the "audit correctness as
supporting infrastructure" durable principle.

## 5. Lessons learned

### 5.1 (durable — carried) One operational workflow beats two overlapping ones

Origin: M25.0 §5.d user redirect. Captured as
`feedback_one_workflow_over_two_overlapping.md`. For customer-
facing operational features, default to one canonical entry
point; defer secondary launch points until operator evidence
proves they're needed. Fragmenting the workflow dilutes the
Playwright journey and grows surface area without evidence.

### 5.2 (durable — carried) Planning-open verification must cover the persistence path, not just the UI path

Origin: M25.0 §5.b (platform-not-persisted discovery) and
M25.2-open (admin/vehicles/ endpoint-not-shipped discovery).
When planning a UI-consuming milestone, verify the full
data path: does the backend endpoint exist? Does the
serializer expose the field? Is the field persisted? An
optimistic planning assumption at either layer will surface
at implementation open with force. **Both M25 empirical
discoveries were caught before scope commit** — verification
at open worked as intended.

### 5.3 (durable — carried) Additive-forever JSONField beats CharField for capturing adapter extras

Origin: M25.0 §5.b decision. When persisting
integration-boundary metadata that has one known key today
but plausibly more tomorrow (adapters normalizing
platform-specific extras), JSONField with a typed accessor
gives you: extension without migration, cleaner adapter
contract, query support preserved, and codebase-precedent
alignment. Junk-drawer risk is mitigated by the typed
accessor — read sites don't sprinkle raw `.get()` calls.

### 5.4 (durable — carried) Record empirical-discovery refinements honestly; they preserve streak integrity

Origin: M25.0 (§5.b JSONField), M25.2 (admin/vehicles/
endpoint). Both were surprises against the planning memo's
optimistic-assumption prose. Both were presented at open
with options + recommendation + user confirmation. The
"planning-time as-recommended" streak counts increments
where the final lock matches what was recommended after
presenting alternatives — refinements from empirical
discovery still count as as-recommended so long as the
recommendation process is transparent. Streak reached 3 at
M25.2 close.

### 5.5 (durable — carried) Modal-attached collapsible + success badge > toast for post-action confirmation

Origin: M25.2 §5.d locked, applied at implementation. When
the operator submits an action from within a modal, showing
a persistent "Recorded" success badge in the collapsible
header (visible until the operator re-opens the
collapsible or the modal) is stronger UX than a transient
toast. The operator returns to context and sees the
confirmation, not a vanishing message.

### 5.6 (durable — carried) Dependency-injectable helpers over network mocks in unit tests

Origin: M25.2 `<RecordTestDriveForm>` test suite. The form
accepts injectable `loadInventory` + `submit` props
defaulting to the shipped wrappers. Vitest tests pass mocks
directly — no MSW, no fetch stubs, no environment setup.
The full network path is covered by the Playwright journey.
Layered coverage: unit tests exercise the pure component
contract; journeys exercise the end-to-end wiring.

### 5.7 (carried from M24) Playwright as operational contract

Applied unchanged. All three M24.1-open §3 deferrals now
have Playwright coverage: 12 via new `lead_to_test_drive`
journey; 13 + 14 via extended M24.3 + M24.4 assertions.
Every M25 attribution + test-drive claim is proven by a
journey, not just a unit test.

### 5.8 (carried from M24) Sibling-pattern discipline

M25.1 CustomerLeadSerializer extension inherited M11.6
`AdminLeadListSerializer` additive pattern cleanly — zero
first-of-a-kind risk on the additive-field posture. M25.2
`admin_vehicle_list` inherited M11.6 `admin_test_drive_list`
list-endpoint shape cleanly — zero first-of-a-kind risk on
the thin-QuerySet + optional-filter pattern. The two backend
additions M25 shipped both used inherited patterns; no bugs
surfaced at implementation.

## 6. Streak status

- **Planning-time as-recommended streak: 3** at M25.2 close.
  M25.0 (all §5 locks including refined §5.b + §5.d) + M25.1
  (matched planning exactly) + M25.2 (matched planning locks
  including refined §5.e endpoint addition). Fresh counter
  reset at M24.0 open; historical run of 89 across M10 → M23
  preserved for the record.
- **Zero-drift permission-class streak: 25** consecutive
  milestones (M10 → M25). M25.1 used M4
  `IsSalesManagerOrOwnerAtActiveDealership` on unchanged
  M6.5 endpoints; M25.2 used the same class on the new
  `admin_vehicle_list` endpoint. Zero new classes.

## 7. Governing-contract validation

The M25 governing contract (`MILESTONE_25_PLANNING.md` §5)
held through all three increments:

- §5.a A3 + A4 bundle framed as "Lead-to-Test-Drive
  Operational Completion" — **satisfied.** Anchor business
  question answered end-to-end for all four M24 intake
  channels.
- §5.b JSONField persistence + typed accessor + additive
  serializer + adapter wiring — **satisfied** at M25.1.
- §5.c display-only attribution — **satisfied** at M25.1
  (no navigation, no links, channel-specific rendering).
- §5.d modal-only test-drive form — **satisfied** at M25.2
  (secondary launch explicitly deferred, not shipped).
- §5.e suggested + inventory picker zones — **satisfied**
  at M25.2 (with the additive endpoint per §3.3 above).
- §5.f 3-increment shape — **satisfied**, plus §5.h fold
  applied.
- §5.g DoD Playwright journey plan — **satisfied** (two
  M25.1 assertion extensions + one M25.2 new journey).
- §5.h evidence-sized close-out fold — **applied** at
  SESSION_187 (this retrospective is that fold).

## 8. Corrections landed by M25 work

- **§3 deferrals 12 + 13 + 14 (M24.1 origin)** — all closed
  by M25. Every M24.1-open genuine gap in operator
  visibility / operator action for the Sales Operational
  Entry funnel is now resolved.
- **`platform` persistence gap (M25.0 discovery)** — fixed
  by JSONField addition + adapter wiring.
- **`admin/vehicles/` endpoint gap (M25.2 discovery)** —
  fixed by additive endpoint following M11.6 precedent.
- **`CustomerLeadSerializer` field asymmetry (M25.0
  discovery)** — fixed by additive serializer extension
  matching M11.6 `AdminLeadListSerializer` precedent.

## 9. Standing M26 question

At M26.0, evaluate the elevated candidate list under the
primary operational-coverage lens ("which candidate most
increases operational coverage for a dealership
employee?"):

**Elevated at M26.0:**

- **Candidate H — test-hygiene remediation** (reinforced
  M24.1 close + carried forward from M25 without change).
  Three shared-DB non-idempotent journeys break full-suite
  runs on state-dirty DB; clean-DB runs pass all 14. High
  compound value for CI baseline stability as the suite
  grows.
- **Candidate A2 — JE creation UI** (unchanged since M23
  close). Small scope, audit-verified genuine gap.
- **NEW Candidate audit-script refinement** (M25.3
  discovery). Small bounded fix to detect
  trailing-optional-querystring template patterns so
  `admin/test-drives/list/` + `admin/vehicles/` audit as
  `covered` (reality) instead of `defer-candidate-O2`
  (current false positive). Compounds every future audit
  read.

**Gated candidates:** T (tester feedback), U (hosted demo
substrate), L (first-live-pilot staging), M (multi-operator
support — breaks zero-drift streak with intent).

**Deferred pending evidence:** D (LLM router / cost caps), C
(F&I chargeback substrate), G (dashboard testid hardening),
plus all M25 §3 deferrals recorded above.

M26.0 opens fresh with the standard candidate presentation
+ recommendation + user confirmation flow.
