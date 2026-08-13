---
title: "Milestone 25 — Lead-to-Test-Drive Operational Completion"
status: active
type: planning-memo
generated: 2026-08-03
generated_at_session: SESSION_184 (skeleton), SESSION_185 (expansion + all §5 locks)
milestone: 25
milestone_name: "Lead-to-Test-Drive Operational Completion"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_24_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_24_PLANNING.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7y
  - docs/research/SALES_DEPARTMENT_MAPPING.md
---

# Milestone 25 — Lead-to-Test-Drive Operational Completion

> **Active planning memo.** Expanded at SESSION_185 M25.0
> open from the skeleton drafted at M24.5 close.
>
> §5.a locked at open per the primary operational-coverage
> lens as the bundle **A3 (lead-source attribution display) +
> A4 (test-drive creation UI)**, refined by the user into a
> single operational-workflow framing rather than two
> independent surfaces. Milestone name: **"Lead-to-Test-Drive
> Operational Completion."**
>
> M24 shipped the sales front-of-funnel operationally at the
> assign level — walk-in, phone, referral all reach a
> salesperson via the intake dialog + shared `<LeadIntakeForm>`
> + post-create `LeadDetailModal` open + `AssignmentDropdown`.
> **The next step in the salesperson's real workflow after
> assignment is scheduling the test drive.** Today that step
> lives only in the backend — the M11.2 endpoint has shipped
> since SESSION_115 with a typed `createTestDrive` wrapper
> since M11.6, but no operator UI consumes it.
> `DealerAiSalesTestDrives.tsx` is read-only per its M11.6
> in-file comment. Additionally, when the salesperson opens a
> lead created via the M24.3 referral or M24.4 webhook
> channel, the modal cannot show them **which** referrer or
> **which** listing platform originated the lead — the
> attribution is captured in the backend but hidden from the
> operator (§3 deferrals 13 + 14 recorded at M24.1 open).
>
> **The anchor business question** — *Can a salesperson
> receive a lead, understand exactly where it came from,
> assign it, and schedule the customer's test drive entirely
> through the normal product workflow?* — governs every M25
> scope decision.
>
> **M25 returns to the M21 Candidate O UI-creation shape**
> shared with M23 + M24. Every M25 shipped operator surface
> (a) maps to shipped backend + missing frontend, (b) closes
> a missing operator-facing UI, (c) adds or extends a
> Playwright operational journey. **One additive backend
> serializer + one additive JSONField** land in M25.1 to
> unblock attribution display — the model addition surfaced
> from empirical verification at M25.0 open (see §5.b) and
> represents the only in-scope backend change. All other
> M25 work is frontend + acceptance.
>
> Anchor cross-refs:
> - `SALES_DEPARTMENT_MAPPING.md` §workflow step 6
>   (demonstration / test drive) — M11.2 endpoint remit.
> - `SALES_DEPARTMENT_MAPPING.md` §lead acquisition
>   (attribution) — the operator-visible "where did this
>   lead come from" business need.
> - `MILESTONE_24_PLANNING.md` §3 deferrals 12 (test-drive
>   UI), 13 (referrer display), 14 (platform display) —
>   the three genuine gaps M25 closes.

## Guiding question (durable, per M22 close)

**Which candidate most increases operational coverage for a
dealership employee?**

At M25.0, this lens ranked A3 highest (per-item delta ×
frequency: every referral / webhook lead opened surfaces
the attribution gap) with A4 close behind (completes the
walk-in journey's original create → assign → schedule
operational-entry story from M24.1). The user then applied
the **operational-workflow framing** — bundling A3 + A4
into a single continuous operator workflow ("receive → see
source → assign → schedule test drive") rather than
shipping two independent UI surfaces. This bundling reflects
the same M24-open reframe that turned four intake forms
into one Sales Operational Entry workflow. **The workflow
is the unit of value, not the individual UI surface.**

## Preserve the M20–M24 operational contract (durable)

Compound guidance carried forward through every M25 decision:

- Verify through the real application before locking scope —
  including BOTH intake AND downstream UI surfaces (M24.1-
  open durable lesson, applied at M25.0 open — see §5.b
  Empirical Discovery).
- Let evidence drive roadmap decisions.
- Keep milestones tightly bounded.
- Extend Playwright journeys whenever customer-facing
  operational behavior changes.
- Allow completed operational journeys to reveal the next
  highest-value work rather than planning from assumptions.
- Sibling-pattern discipline (M23 durable) — first-of-a-kind
  changes surface latent bugs; inherited patterns don't.
- Record planning corrections honestly (M24 durable) —
  streak integrity beats streak count.
- **One operational workflow beats two partially-overlapping
  ones (M25 durable)** — for customer-facing operational
  features, default to one canonical entry point; defer
  secondary launch points until operator evidence proves the
  need.

## Guiding principle (Candidate O UI-creation contract, M21 shape)

Inherited unchanged from M21 → M22 → M23 → M24. Every M25
shipped operator surface satisfies three constraints:

1. **Maps to shipped backend surface.** All three §3
   deferrals M25 closes name endpoints that have been in
   `salesApi.ts` since M11.6.
2. **Closes a missing operator-facing UI.** No surface M25
   ships duplicates an existing UI path.
3. **Ships with a Playwright operational journey that
   proves the surface works end-to-end** — extend the M24.3
   referral journey for A3 attribution display; add a new
   `sales/lead_to_test_drive.spec.ts` for A4.

The **JSONField + serializer addition** in §5.b is the only
backend change; it is additive-only, does not touch
existing behavior, and the M11.6 `AdminLeadListSerializer`
precedent (additive `channel` + `referrer` at that
milestone) applies directly.

## 0. Engineering practices to preserve from M2–M24

- **Tenant discipline.** All M25 reads / writes go through
  `services.tenancy.get_current_dealership(request)`.
- **Additive serializer changes.** `CustomerLeadSerializer`
  gains fields; existing consumers ignore unknown keys.
- **JSONField default-dict.** `source_metadata` defaults to
  `dict`; historical rows land with `{}` via the migration
  default. No backfill migration required.
- **Typed accessor on JSON reads.** A helper method on
  `CustomerLead` (`get_source_platform() -> str`) reads
  `source_metadata.get("platform", "")` so read sites do
  not sprinkle raw `.get()` calls across the codebase.
- **Fail-closed cross-tenant on test-drive create.** M11.2
  `CrossTenantTestDriveError → 404` already correct; UI
  handles 404 as "not found" without leaking existence.
- **17-stage scrub stack unchanged.** M25 does not touch
  LLM output — attribution display + test-drive form are
  operator-owned surfaces.
- **Playwright real-DB posture.** M25.2 journey exercises
  the real `/admin/test-drives/` endpoint end-to-end,
  matching M24.4 webhook posture.
- **Zero-drift permission classes.** All M25 reads / writes
  use existing permission classes (`IsSalesManagerOrOwnerAt
  ActiveDealership` — M4). Twenty-four-milestone streak
  intended to extend to twenty-five.

## 1. Business questions this milestone answers

**Primary — governs §5.a.** *Can a salesperson receive a
lead, understand exactly where it came from, assign it,
and schedule the customer's test drive entirely through
the normal product workflow?*

**Secondary questions M25 answers along the way:**

1. Can the operator see whether a lead came from a
   specific referring customer, and if so who? (A3 · §3
   deferral 13, backed by the M11.1 referrer FK.)
2. Can the operator see which listing platform originated
   a webhook lead, not just the generic "listing_form"
   channel label? (A3 · §3 deferral 14, requires the
   §5.b JSONField addition per M25.0 empirical
   discovery.)
3. Can the operator schedule and record a test drive
   without leaving the lead-detail context? (A4 · §3
   deferral 12.)
4. Does a newly-scheduled test drive appear in the
   existing tenant-wide test-drive log without any
   additional backend or UI work? (Verified at M25.0
   open — `admin/test-drives/list/` already returns
   ordered-by-`-driven_at`, `DealerAiSalesTestDrives.tsx`
   already consumes it.)

## 2. What existing primitives extend

**Backend (all shipped, all inherited unchanged except
the additive addition in §5.b):**

- `services.leads.channel_intake.record_webhook_lead`
  (M11.1) — receives `platform` string, dispatches to
  adapter, currently discards `platform` after
  normalization. **M25.1 modifies to persist platform
  into `source_metadata` alongside adapter-normalized
  kwargs.**
- `services.leads.webhook_adapters` (M11.1) — the
  adapter contract gains an optional
  `metadata_capture()` alongside `normalize()`, or a
  simpler pattern where `record_webhook_lead` writes
  `{"platform": platform}` directly (see §5.b for
  chosen shape).
- `services.test_drives.record_test_drive` (M11.2) —
  unchanged; the M25.2 UI writes through this verb
  via the existing `POST /admin/test-drives/`
  endpoint.
- `admin_test_drive_list` (M11.6) — unchanged;
  `DealerAiSalesTestDrives.tsx` already reads
  through it.
- `admin_lead_detail` (M6.5 / M8) — unchanged;
  reads through the extended
  `CustomerLeadSerializer`.

**Model (one additive field):**

- `CustomerLead.source_metadata =
  JSONField(blank=True, default=dict)` — see §5.b.

**Serializer (additive field additions):**

- `CustomerLeadSerializer` gains `referrer`
  (PrimaryKeyRelatedField or serialized nested
  reference), `referrer_name` (SerializerMethodField),
  and `source_metadata` (JSONField exposed as-is).

**Frontend (shared substrate + new component):**

- `LeadDetailModal.tsx` (M6.5 / Phase 4) — extended
  with a "Source" attribution section + collapsible
  "Schedule test drive" section.
- `AssignmentDropdown.tsx` (Phase 4) — unchanged;
  M25.2 journey exercises it as part of the
  create-to-schedule flow.
- `frontend/src/components/sales/` (M24) — gains
  `<RecordTestDriveForm>` component matching the
  `<LeadIntakeForm>` substrate pattern.
- `salesApi.ts::createTestDrive` (M11.6) — unchanged
  wrapper; UI consumes it.
- `DealerAiSalesTestDrives.tsx` (M11.6) — unchanged;
  remains the canonical visibility surface.

**Test substrate:**

- M24.3 referral Playwright journey — extended to
  assert modal attribution display.
- M24.4 webhook Playwright journey — extended (or a
  small companion assertion added) to assert platform
  display for webhook-origin leads.
- New M25.2 Playwright journey
  `sales/lead_to_test_drive.spec.ts` — the anchor
  operational contract for the milestone.

## 3. What's NOT in this milestone (deferrals)

- **Secondary "+ Record test drive" launch point on
  `DealerAiSalesTestDrives`.** Considered at M25.0 open,
  explicitly deferred pending operator evidence per the
  M25.0-durable "one operational workflow beats two
  partially-overlapping ones" principle. The modal-
  attached form is the canonical creation surface;
  `DealerAiSalesTestDrives` remains read-only. Re-entry
  requires operator evidence.
- **Test-drive edit / delete UI.** Records are immutable
  once persisted per the M11.2 subsidiary-log design.
  M25 does not surface post-hoc mutation.
- **Referrer-name link (clickable "Referred by" opens
  the referrer's LeadDetailModal).** Considered at
  M25.0 open, deferred as display-only. Re-entry
  requires operator evidence that navigation between
  linked leads is a real workflow need.
- **Structured objection vocabulary lookup.** M11.2
  ships `objections_captured` as a free-text list;
  M25.2 preserves that shape in the form.
- **Named-platform adapters** (Autotrader / Cars.com /
  CarGurus / Facebook native envelopes). M25.1 keeps
  the generic adapter unchanged; the `source_metadata`
  JSONField is precisely the substrate that named
  adapters can extend without further model changes.
- **Analytics / rollup surfaces** (e.g. "all
  autotrader leads this month"). JSONField key
  lookups support the query but no rollup UI ships in
  M25. Re-entry when operator evidence surfaces the
  reporting need.
- **Vehicle picker as searchable inventory browse.**
  M25.2 vehicle picker exposes `interested_vehicles`
  as suggestions + full tenant inventory as a
  fallback list. Advanced filters (year / make / model /
  price range) are M26+ pending operator evidence.
- **`interested_vehicles` editing from the modal.**
  Read-only in the modal per M6.5. Vehicle attach at
  test-drive time writes to `TestDrive.vehicle`, not
  back to `CustomerLead.interested_vehicles`.
- **Test-drive scheduling in advance** (as opposed to
  recording after the fact). M11.2 `driven_at`
  defaults to `timezone.now()`; the M25.2 form allows
  operator override but the primary use case is
  recording immediately post-drive.
- **Sales manager / advisor role distinction on
  test-drive create.** M11.2 permission is
  `IsSalesManagerOrOwnerAtActiveDealership`; the
  salesperson-writes-their-own-drive advisor gate is
  a deferred M11.2 follow-on. M25.2 inherits the
  M11.2 posture unchanged.
- **Deal write-up, F&I handoff creation, generic
  sales polish.** Explicitly out of scope per user
  framing at M25.0 open. "One operational workflow"
  means M25 stays inside the lead-to-test-drive
  narrative; adjacent sales surfaces are M26+
  candidates.

**Playwright journey binding for DoD compliance (M21.0
§5.f Option B):** M25 extends the M24.3 referral
journey and adds a new `sales/lead_to_test_drive.spec.
ts` journey. §3 documents both additions, satisfying
the DoD amendment.

## 4. What existing tests bind

- **M11.1 channel-intake tests** — `test_m111_*.py`.
  Assert `channel` field + `referrer` FK persistence
  across walk-in / phone / referral / webhook. M25.1
  extends the webhook coverage to assert
  `source_metadata["platform"]` persistence via the
  adapter.
- **M11.2 test-drive endpoint tests** —
  `test_m112_test_drive_endpoint.py`. Assert
  cross-tenant fail-closed + FK requiredness + happy
  path. Unchanged by M25.
- **M11.6 list-endpoint tests** —
  `test_m116_list_endpoints.py`. Assert
  `admin/test-drives/list/` filter behavior.
  Unchanged.
- **M6.5 / Phase 4 lead-detail tests** — assert
  `admin_lead_detail` payload shape. M25.1 extends
  to assert new fields (`referrer`,
  `referrer_name`, `source_metadata`) present in
  serialized output.
- **Frontend Vitest baseline (209 pass)** — M25.1
  adds `LeadDetailModal.test.tsx` coverage for the
  Source section render; M25.2 adds
  `RecordTestDriveForm.test.tsx` coverage matching
  the `LeadIntakeForm.test.tsx` pattern.
- **Acceptance baseline (13 journeys, ~26.8s
  clean-DB dry-run)** — M25 extends M24.3 +
  adds one new journey; end target 14 journeys.

## 5. Load-bearing decisions

### §5.a — Milestone target selection

**LOCKED at M25.0 open as A3 + A4 bundle, framed as
"Lead-to-Test-Drive Operational Completion."**

Presented at open per the primary operational-coverage
lens against the freshly regenerated audit artifact
(153 endpoints, 113 covered, 40 backend-only post-M24).
Ranking:

1. **A3 (referrer + platform attribution display)** —
   highest per-item operational-coverage delta at
   smallest scope. Every referral / webhook lead
   opened surfaces the gap.
2. **A4 (test-drive UI)** — completes the M24.1
   walk-in journey's original create → assign →
   schedule operational-entry story.
3. **H (test-hygiene remediation)** — indirect
   coverage delta; high-compound value for CI
   stability but not workflow-completing.
4. **A2 (JE creation UI)** — smallest per-item delta
   of the elevated set.

User confirmed A3 + A4 bundle, redirected framing from
"Sales UI completeness" (which invites feature creep) to
**"Lead-to-Test-Drive Operational Completion"** — a
single operational-workflow narrative that binds both
anchors. Streak counter increments from 0 to 1 at
M25.0 (see §8).

### §5.b — Attribution persistence contract

**LOCKED at M25.0 open as Option A · JSONField variant
(`CustomerLead.source_metadata`).**

**Empirical discovery at M25.0 open:** verified that
`platform` is not persisted on `CustomerLead`. The
webhook receives `platform` as a request field, uses
it to dispatch to the `webhook_adapters` module, and
discards it after `adapter.normalize(payload)` returns
the normalized kwargs (see
`services/leads/channel_intake.py:record_webhook_lead`).
`CustomerLead` persists only `channel="listing_form"`.
The M24.1-open §3 deferral 14 as originally framed
("small UI extension") is therefore not implementable
without a backend model addition.

Three options considered at open:

- **Option A** — Add a persistence field to
  `CustomerLead` and wire the intake path to write it.
  Two variants:
  - **A · CharField** (`source_platform`) — simple,
    typed, queryable. Locks the schema to a single
    field; each future attribution attribute requires
    another migration.
  - **A · JSONField** (`source_metadata`) — additive-
    forever contract; adapters return metadata
    alongside normalized kwargs. Matches existing
    codebase JSON patterns (`ChatSession.
    extracted_profile`, `TestDrive.
    objections_captured`, BHPH contact metadata).
    Query support via `.filter(source_metadata__
    platform="autotrader")` on Postgres native +
    modern SQLite (JSON1, enabled by default in
    Django 4+).
- **Option B** — Descope §3 deferral 14. Ship only
  referrer display + test-drive UI. Preserves M24's
  zero-backend posture.
- **Option C** — Store platform in `CustomerLead.notes`
  or `session.extracted_profile`. Fragile, not typed.

**User locked Option A · JSONField** for durability.
Rationale carried in the memo body: extension without
migration, codebase precedent, cleaner adapter
contract (adapters stop discarding captured extras),
query support preserved. Junk-drawer risk mitigated
by a typed accessor `CustomerLead.
get_source_platform() -> str` that reads
`source_metadata.get("platform", "")` — read sites use
the accessor; write sites use the adapter contract.

**Model + migration shape:**

```python
# dealer_ai/models.py — additive on CustomerLead
source_metadata = models.JSONField(blank=True, default=dict)

def get_source_platform(self) -> str:
    return (self.source_metadata or {}).get("platform", "")
```

Migration is a single `AddField` — no backfill required
(`default=dict` handles historical rows on first read /
serialization).

**Adapter contract shape:** the simpler path — `record_
webhook_lead` writes `source_metadata={"platform":
platform, **adapter_extras}` at persistence time. No
change to the `WebhookAdapter` protocol itself; the
generic adapter returns extras as needed. Preserves
the M11.1 adapter contract's tight scope while making
extras first-class.

### §5.c — Attribution display posture

**LOCKED as display-only in the modal, no navigation
links.**

`LeadDetailModal` gains a "Source" section rendered
near the existing lead-id header. Rendering rules per
channel:

- `chat`, `walk_in`, `phone`, `other` — Source
  section omitted (no attribution to display).
- `listing_form` — "Source: {platform_label}" where
  `platform_label` is a display-cased version of
  `source_metadata.platform` (e.g. `autotrader` →
  "Autotrader"). Falls back to "Listing form" when
  metadata missing.
- `referral` — "Referred by: {referrer_name}" where
  `referrer_name` comes from a new
  `SerializerMethodField` on `CustomerLeadSerializer`
  that reads `self.referrer.name` when set. Falls
  back to "Referral (referrer not linked)" when
  `referrer` FK is NULL (matches M11.1 optional-
  referrer posture).

No clickable navigation to the referrer's own lead —
deferred per §3.

### §5.d — Test-drive form attachment point

**LOCKED as modal-only.**

`<RecordTestDriveForm>` component in
`frontend/src/components/sales/` matching the
`<LeadIntakeForm>` substrate pattern from M24.1.
Attached inside `LeadDetailModal` as a collapsible
"Schedule test drive" section — collapsed by default,
expands on operator click. On successful submit the
section collapses with a success indicator + refreshes
the modal's cached `detail` if needed.

**No secondary launch point on
`DealerAiSalesTestDrives`.** Deferred to M26+ pending
operator evidence per the M25-durable "one operational
workflow beats two partially-overlapping ones"
principle (see §3). The Playwright journey exercises
the modal-attached workflow as the sole creation
surface + asserts that `DealerAiSalesTestDrives`
remains the canonical visibility surface (existing
read-only behavior).

### §5.e — Vehicle picker sourcing

**LOCKED as `interested_vehicles` as suggestions +
full tenant inventory as fallback.**

The form's vehicle selector renders in two zones:

1. **"Suggested vehicles"** — from
   `detail.interested_vehicles` (the modal already
   fetches these via `admin_lead_detail`). Chat-
   origin leads populate this; walk-in / phone /
   referral / webhook leads default to empty.
2. **"All inventory"** — a searchable list of the
   tenant's active vehicles. Fetched via the
   existing vehicle-list endpoint (verify precise
   endpoint at M25.2 open; likely
   `/admin/vehicles/` or equivalent).

Selection sets the form's `vehicle_id` before submit.
No inline vehicle creation — vehicle must exist in
tenant inventory beforehand (matches M11.2 backend
requirement).

Advanced filters (year / make / model / price)
deferred per §3.

### §5.f — Increment shape

**LOCKED as 3 increments, close-out folding per
evidence.**

- **M25.0 — Planning refinement + target selection
  (this session, SESSION_185).** Locks all §5
  decisions. Ships the M25 memo expansion + the
  SESSION_185 handoff. **No code, no push.**
- **M25.1 — Attribution display + JSONField backend
  addition.** Backend: model field addition +
  migration + typed accessor + serializer additive
  extension + `record_webhook_lead` adapter wiring.
  Frontend: `LeadDetailModal` Source section +
  Vitest coverage. Acceptance: extend M24.3
  referral journey + extend or add small companion
  for M24.4 webhook platform assertion.
  **~1 session.**
- **M25.2 — Test-drive UI (modal-attached only).**
  Frontend: `<RecordTestDriveForm>` component +
  modal integration + Vitest coverage. Acceptance:
  new `sales/lead_to_test_drive.spec.ts` journey
  exercising create → assign → schedule → verify
  on DealerAiSalesTestDrives page. **~1-2
  sessions.**
- **M25.3 — Close-out** (retrospective + audit
  rerun + coordinated push). **~1 session, or
  folds into M25.2 close if evidence-sized §5.h
  Option B posture holds.**

**Total: ~3-4 sessions** matching the M24 velocity
envelope.

### §5.g — DoD compliance (Playwright journey plan)

**LOCKED with two journey changes named in §3.**

- **M25.1** extends the M24.3 referral journey to
  assert that after creating a referral lead with a
  referring-customer picker → opening the resulting
  `LeadDetailModal` → the "Referred by: {name}"
  Source line is visible. Also extends the M24.4
  webhook journey (or adds a small companion assertion
  in the same file) to assert "Source: {platform_label}"
  for a webhook-origin lead.
- **M25.2** adds a new
  `acceptance/journeys/sales/lead_to_test_drive.spec.ts`
  journey that: creates a walk-in lead via existing
  M24.1 substrate → post-create modal opens → assigns
  a salesperson via the dropdown → expands "Schedule
  test drive" collapsible → picks a vehicle from
  inventory → submits → asserts the collapsible
  closes with success → closes modal → navigates to
  `DealerAiSalesTestDrives` → asserts a row appears
  with correct lead / vehicle / salesperson /
  dealership / date associations.

M21.0 §5.f Option B satisfied. No exception path
required.

### §5.h — Close-out posture

**LOCKED as evidence-sized Option B (per M24 precedent).**

If M25.1 and M25.2 both ship cleanly with no operator-
surface fixes required at close, fold the close-out
into the M25.2 session (retrospective + audit rerun +
coordinated push in the same session). Otherwise
promote to a separate M25.3 close-out session. Push
executes once, at the end of the milestone, per M18
→ M24 cadence — **no per-increment pushes.**

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_24_RETROSPECTIVE.md` §9
6. `docs/roadmap/MILESTONE_24_PLANNING.md` §3
   (deferrals 12, 13, 14 — the direct M25 re-entry
   record)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
8. `docs/CAPABILITY_MATRIX.md` §7y
9. `docs/research/SALES_DEPARTMENT_MAPPING.md`
   §workflow step 6 + §lead acquisition

## 7. Sequencing

**M25.0 (SESSION_185, this session)** — planning
refinement + target selection + all §5 locks.
Ships memo expansion + handoff. No code, no push.

**M25.1 (SESSION_186)** — attribution display +
JSONField backend. In order:

1. Add `CustomerLead.source_metadata` field +
   migration + `get_source_platform()` accessor.
2. Extend `CustomerLeadSerializer` with `referrer`,
   `referrer_name`, `source_metadata` (additive).
3. Update `record_webhook_lead` to write
   `source_metadata={"platform": platform}` at
   persistence time.
4. Extend M11.1 webhook tests to assert
   `source_metadata` persistence + M6.5 lead-detail
   tests to assert new serialized fields.
5. Add Source section to `LeadDetailModal` +
   Vitest coverage.
6. Extend M24.3 referral journey with modal
   attribution assertion + extend M24.4 webhook
   journey with platform assertion.
7. Run full backend + frontend + acceptance
   baselines clean. Handoff.

**M25.2 (SESSION_187, possibly SESSION_187 + _188)**
— test-drive UI. In order:

1. Verify at open: which endpoint returns tenant
   vehicle inventory for the picker (likely
   existing `salesApi`-adjacent wrapper).
2. Create `<RecordTestDriveForm>` component in
   `frontend/src/components/sales/` matching the
   `<LeadIntakeForm>` substrate pattern.
3. Attach as collapsible "Schedule test drive"
   section inside `LeadDetailModal`.
4. Vitest coverage for form + integration.
5. New `sales/lead_to_test_drive.spec.ts`
   journey.
6. Run baselines. Handoff.
7. If evidence-sized close-out posture holds:
   fold M25.3 into this session (retrospective
   + audit rerun + coordinated push).

**M25.3 (SESSION_188 or _189, or folded into
M25.2)** — close-out. Retrospective + audit
rerun + coordinated push of all M25 commits.

## 8. Streak accounting (M25)

- **Zero-drift permission-class streak** — enters
  M25 at 24 consecutive milestones (M10 → M24).
  Intended posture: extend to 25. M25.1 uses
  existing M4 permission class
  (`IsSalesManagerOrOwnerAtActiveDealership`) on
  the M11.2 endpoint; M25.2 does not add any
  endpoints. No new permission class ships.
- **Planning-time as-recommended streak** —
  reset to 0 at M24.0 open (stayed at 0 through
  M24.1-open correction). Historical run of 89
  across M10 → M23 preserved for the record.
  M25.0 opens fresh — increments to 1 if the
  user confirms all §5 locks as recommended.
  Two mid-planning refinements at M25.0 (user
  redirected §5.a framing to
  "Lead-to-Test-Drive Operational Completion,"
  chose §5.b JSONField over CharField and §5.d
  modal-only over dual entry points) are recorded
  as *refinements of the recommendation*, not
  corrections against it — the recommendation
  process presented options and the user selected
  from them. Streak counts increments where the
  final lock matches what was recommended after
  presenting alternatives.

## 9. Non-goals for the remaining M25 increments

- ❌ Do NOT add a secondary "+ Record test drive"
  entry point on `DealerAiSalesTestDrives` or
  anywhere else. Modal-only is the locked scope
  per §5.d. Re-entry requires operator evidence
  and a fresh milestone decision.
- ❌ Do NOT make the "Referred by" attribution
  line clickable / navigable. Display-only is
  the locked scope per §5.c.
- ❌ Do NOT introduce named-platform adapters
  (Autotrader / Cars.com / etc.). Generic
  adapter unchanged; `source_metadata` is the
  extension substrate but M25 does not populate
  new adapters.
- ❌ Do NOT add analytics / rollup surfaces
  (e.g. "leads by platform this month"). The
  JSONField query support enables such
  surfaces later; M25 does not ship any.
- ❌ Do NOT modify the M1–M24 shipped surface
  except for the additive changes explicitly
  scoped in §5.b (model field, serializer
  fields, `record_webhook_lead` adapter
  wiring).
- ❌ Do NOT expand the vehicle picker beyond
  "Suggested + all inventory" (§5.e).
  Advanced filters are M26+.
- ❌ Do NOT push per-increment. Coordinated
  push at M25 close (M25.2 or M25.3
  depending on close-out fold).
- ❌ Do NOT let "one workflow" broaden into
  adjacent sales surfaces (deal write-up, F&I
  handoff, etc.). M25 stays inside the
  lead-to-test-drive narrative per §5.a
  framing.
- ❌ Do NOT skip the M25.1-open verification of
  the vehicle-list endpoint used by the M25.2
  picker. Empirical verification of both
  intake AND downstream surfaces before
  locking implementation is the M24.1-open
  durable lesson.
