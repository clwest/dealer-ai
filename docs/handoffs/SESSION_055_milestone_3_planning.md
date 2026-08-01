---
title: "SESSION_055 handoff — Milestone 3 · Increment 0 (planning pass)"
status: historical
type: handoff
date: 2026-07-31
session: 055
milestone: 3
milestone_status: planning
increment: 0
increment_status: shipped
commit: TBD
---

# SESSION_055 — Milestone 3 · Increment 0 (M3.0 — planning pass)

## What shipped

Documentation-only session. No code changes. Milestone 3
(Structured Condition Report) is now scoped, sequenced, and
ready for implementation. The load-bearing multi-photo storage
decision has been resolved: **Option A — fold storage into M3**
as its own increment (M3.4) before `ConditionFindingPhoto`
(M3.5).

The deliverable is `docs/roadmap/MILESTONE_3_PLANNING.md`
mirroring the eight-section shape (`§0–§8`) that
`MILESTONE_2_PLANNING.md` proved out across SESSION_046 →
SESSION_054.

## Read-first pass performed

Per the SESSION_054 handoff § "Read-first list for SESSION_055,"
these were read in order before any drafting began:

1. `docs/PROJECT_RULES.md` (all six governance rules).
2. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 (eleven
   lessons) + §7 (remaining deferrals) + §8 (roadmap guidance
   for M3).
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3
   (business objective + scope boundary + non-goals).
4. `docs/research/RECON_MAPPING.md` — full 2,084-line document.
   Load-bearing anchors noted: *"the condition report is where
   recon quality begins"* (preamble), *"Human-authored
   inspection discipline is non-negotiable"* (§2.3), the
   inspection category list (§2.1), the four severity levels
   (§2.2), photos-in-condition-reporting (§2.5), what AI is
   never allowed to do (§2.6), what AI IS allowed to do
   (§2.7), the front-line-ready decision + sign-off authority
   (§12.1–§12.2), warranty exposure (§13.1), and pains #4
   (inspection quality variance), #5 (jacket confusion), #6
   (multiple techs), #14 (post-sale warranty callback).
5. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 2 (~lines
   449–470) — target `ConditionReport` + `ConditionFinding`
   shape and the "AI role: NONE yet. Deliberately un-automated
   so the data shape gets proven before automation lands on
   top" invariant.
6. `docs/BUSINESS_DOMAIN_MAP.md` §4.2 Recon — department
   identity, rhythm, boundary.
7. `docs/roadmap/AUTHENTICATION_MODEL.md` — all four layers
   (identity, authorization, business permissions, data
   scoping). Every ConditionReport row inherits this substrate
   unchanged.
8. `backend/dealer_ai/models.py` — `Vehicle`, `Dealership`,
   `VehicleAcquisition`, `VehicleCost`, `UserDealershipRole`.
9. `backend/dealer_ai/services/vehicle_ledger.py` — the M2
   service pattern M3's `services/condition_report.py` will
   mirror (fail-closed cross-tenant guard, explicit
   `dealership=` kwarg, `full_clean()` before save, one
   authoritative write path).
10. `backend/dealer_ai/services/tenancy.py` — the tenancy
    primitives every ConditionReport read/write flows through,
    plus the `_TENANT_CARRIER_MODEL_NAMES` tuple M3.1 extends
    to register the three new carriers.
11. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b (as-shipped
    eight-increment sequence) + §3 (annotated compatibility
    checklist) + §5 (deferrals table shape) — the templates
    the M3 planning artifact mirrors.

## The load-bearing storage decision — Option A

The multi-photo storage tension named at
`MILESTONE_2_RETROSPECTIVE.md` §7 has been resolved in
`MILESTONE_3_PLANNING.md` §5.a. Three options were considered:

- **Option A — Fold storage into Milestone 3.** Storage
  abstraction (`django-storages` config, presigned upload URL
  helper) ships as M3.4; `ConditionFindingPhoto` model + upload
  flow ships as M3.5.
- **Option B — Pre-M3 half-milestone.** Storage ships
  standalone as "M2.9" or "M3.0" before M3 targets its use.
- **Option C — Text-only M3.** Findings without photos in v1;
  photo attachments deferred.

**Chosen: Option A.** Reasoning captured in the planning
artifact:

1. Half-milestones defer coordination without avoiding work.
2. The storage story is small when kept minimal (one
   dependency, one settings block, one presigned-URL helper,
   ~30 lines of service code + focused tests).
3. Photos are load-bearing for warranty defense per RECON
   §13.1; Option C would leave one of the four core M3
   operational questions (Q4) unanswered.
4. M2 retrospective §6 lesson 1 (*"no session should ship two
   independent responsibilities at once unless one truly
   cannot be tested without the other"*) is honored — M3.4
   (storage abstraction) and M3.5 (`ConditionFindingPhoto`
   model + upload flow) remain two separate increments with
   independent test surfaces even though they land in the
   same milestone.

Storage details codified in `MILESTONE_3_PLANNING.md` §1.4:
`django-storages[s3]` dependency, env-driven
`DEFAULT_FILE_STORAGE` selection with local `FileSystemStorage`
fall-through for dev/test, presigned browser-to-S3 uploads
(never proxied through Django), signed read URLs with TTL ≤ 15
minutes (no public bucket policy), four-value content-type
whitelist (`image/jpeg`, `image/png`, `image/heic`,
`image/webp`) enforced at URL issuance.

## The eight-increment sequence

Mirrors the M2 §7.b shape. Each increment ships one session
with focused tests and a healthy full-suite baseline at the
boundary.

| Increment | Session | What it delivers |
|-----------|---------|------------------|
| M3.1 | 056 | Core models (`ConditionReport` + `ConditionFinding` + `ConditionFindingPhoto`) + migration `0015` + admin + category/severity/status/content-type enum constants + cross-tenant `clean()` guards + `_TENANT_CARRIER_MODEL_NAMES` extension |
| M3.2 | 057 | `services/condition_report.py` — `create_report` / `complete_report` (one-way draft → complete) / `add_finding` / `update_finding` / `delete_finding` / `latest_condition_report` / `latest_completed_condition_report` + `CrossTenantConditionReportError` |
| M3.3 | 058 | Two `@property` accessors on `Vehicle` (`latest_condition_report`, `latest_completed_condition_report`). No `@cached_property` in v1 (unproven access pattern) |
| M3.4 | 059 | Storage abstraction — `django-storages[s3]` + env-driven `DEFAULT_FILE_STORAGE` + `services/photo_storage.py` (`generate_upload_url` / `object_exists` / `generate_read_url` with content-type whitelist + TTL cap) |
| M3.5 | 060 | `ConditionFindingPhoto` model + migration `0016` + `services/condition_report.py` extensions (`request_photo_upload` / `attach_photo` / `delete_photo`) |
| M3.6 | 061 | Admin API — ten endpoints under `/api/dealer-ai/admin/vehicles/<stock_number>/…` with `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]` composition (M1 · 4D class reused unchanged), full permission matrix per endpoint, cross-tenant + nonexistent both return 404 identical body |
| M3.7 | 062 | Operator UI — `VehicleConditionReportPage.tsx` at `/dealer-ai-inventory/:stock/condition-report` inside `<RequireAuth>`; draft-vs-complete UI states; direct browser-to-S3 upload flow |
| M3.8 | 063 | Verification + closeout — full §3 compatibility sweep with inline evidence; `CAPABILITY_MATRIX.md` §7d; `IMPLEMENTATION_ROADMAP.md` §Milestone 3 flipped shipped; `MILESTONE_3_RETROSPECTIVE.md`; planning frontmatter marked `status: shipped` |

## What Milestone 3 delivers (recap)

For any stock number, answer: **"What needs to happen before
this vehicle is front-line ready?"** Human-authored,
structured, photo-documented.

**In scope** (per `IMPLEMENTATION_ROADMAP.md` §Milestone 3 +
`MILESTONE_3_PLANNING.md` §1):

- `ConditionReport` model (many-per-Vehicle; timestamped;
  authored by a named human; `status draft/complete`
  one-way transition; complete reports immutable).
- `ConditionFinding` model (twelve categories; four severities;
  required `description`; optional `estimated_cost` as
  documentation only — does NOT post `VehicleCost` in M3).
- `ConditionFindingPhoto` model (multi-photo per finding;
  presigned S3 uploads; signed short-TTL reads; four-value
  content-type whitelist).
- Storage abstraction sufficient for photo attachments
  (S3-compatible + CDN; local dev fall-through).
- Operator UI to author + view a condition report.
- **Deliberate absence of AI** — the milestone ships with NO
  LLM role at all so the data shape gets proven before
  automation lands on top (per VCP §Phase 2).

**Explicitly out of scope** (verified against roadmap +
retrospective + planning-artifact §5):

- AI-drafted recon work plans (Milestone 4).
- `Vendor` FK model (Milestone 4).
- `WorkOrder` model (Milestone 4).
- Vehicle lifecycle stage advancement based on findings
  (Milestone 5).
- Auto-minting `VehicleCost` rows from findings or completed
  work (Milestone 4).
- `recon_manager` permission class (Milestone 4).
- Warranty callback tracking (Milestone 4 or later).
- Historical-cost-informed cost estimates (Milestone 8).
- Reopening a completed report (data-first — revisit with
  operator evidence).
- Bulk photo upload / image processing / thumbnails / EXIF
  stripping (data-first — revisit with operator evidence).
- Inspection templates / scheduling / cross-department views
  (deferred; see planning §5.b for the full list).

## Non-goals verified (this session)

- ❌ Zero Milestone 3 code was written (no models, no
  migrations, no service functions, no views, no tests).
- ❌ Zero changes to `services/vehicle_ledger.py` or any M2
  ledger endpoint / UI.
- ❌ Zero changes to `dealer_ai/permissions.py`.
- ❌ Zero changes to `services/tenancy.py` (the
  `_TENANT_CARRIER_MODEL_NAMES` extension is planned for
  M3.1, not touched this session).
- ❌ Zero changes to `services/llm_safety.py` or any pre/post-
  LLM guard.
- ❌ Zero introduction of a `recon_manager` permission class
  in the planning artifact (M4 first surfaces this role's
  need).
- ❌ Zero re-opening of M2 semantic contracts
  (`total_investment` still excludes estimates;
  `days_in_inventory` still returns `None` on missing
  acquisition; money-as-strings at API boundaries).

## Baselines unchanged

- **Backend test baseline unchanged: 1,753 pass** (last
  measured at SESSION_054 close; this session made no code
  changes).
- **Migrations unchanged through `0014`.**
- **Frontend build unchanged.** No `.tsx` or `.ts` touched.
- **No new dependencies added this session.** `django-storages`
  addition is queued for M3.4 (SESSION_059).

## Documentation updated

- **`docs/roadmap/MILESTONE_3_PLANNING.md`** — new file (1,490
  lines). Full eight-section planning artifact mirroring
  `MILESTONE_2_PLANNING.md`'s shape. `status: draft`,
  `milestone: 3`, `milestone_name: "Structured condition report"`.
- **`docs/handoffs/SESSION_055_milestone_3_planning.md`** —
  this file.
- **`00-START-NEXT-SESSION.md`** — overwritten with SESSION_056
  = Milestone 3 · Increment 1 (M3.1 core condition-report
  models) priority.

## Commit hashes

(Filled in immediately after commit.)

- (this session's commit) — `docs(m3-inc0): Milestone 3 planning pass — MILESTONE_3_PLANNING.md + SESSION_055 handoff + SESSION_056 priority`

## Exact SESSION_056 Milestone 3 · Increment 1 (M3.1) scope

**SESSION_056 = Milestone 3 · Increment 1 (M3.1 — core
condition-report models).** First implementation session for
Milestone 3.

### Deliverable

The persistence layer for structured condition reports:

- `ConditionReport` model (many-per-Vehicle, `status draft/complete`).
- `ConditionFinding` model (twelve categories, four severities,
  required description, optional Decimal `estimated_cost`).
- `ConditionFindingPhoto` model (fields per
  `MILESTONE_3_PLANNING.md` §1.5; the actual upload flow lands
  M3.5, but the model + admin ship in M3.1).
- Migration `0015` (or whatever the next sequential number is
  at SESSION_056 time — verify via `showmigrations`).
- Admin registrations for all three models
  (`ConditionReportAdmin`, `ConditionFindingAdmin`,
  `ConditionFindingPhotoAdmin`) with list displays, filters,
  and search that follow the M2 admin pattern
  (`VehicleAcquisitionAdmin` / `VehicleCostAdmin`).
- Module-level constants for the four enums:
  - `CONDITION_CATEGORY_CHOICES` (twelve values).
  - `CONDITION_SEVERITY_CHOICES` (four values).
  - `CONDITION_REPORT_STATUS_CHOICES` (two values).
  - `CONDITION_PHOTO_CONTENT_TYPE_CHOICES` (four values).
- Cross-tenant model `clean()` guards on all three models
  (same shape as `VehicleAcquisition.clean` /
  `VehicleCost.clean`).
- `services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES` tuple
  extended to register the three new carriers (one line each).
- `DATABASES["migration_check"]` alias verified against the
  new migration.

### What M3.1 does NOT ship

- ❌ No service module (`services/condition_report.py` is
  M3.2).
- ❌ No `Vehicle` `@property` methods (M3.3).
- ❌ No storage abstraction (M3.4).
- ❌ No upload flow (M3.5).
- ❌ No API endpoints (M3.6).
- ❌ No frontend (M3.7).
- ❌ No AI role of any kind (M3 has no AI role — this is a
  load-bearing invariant per VCP §Phase 2).

### Test surface

~40 focused model tests:

- **Schema tests.** `dealership` FK NOT NULL on all three models
  (`test_condition_report.DealershipRequired`,
  `test_condition_finding.DealershipRequired`,
  `test_condition_finding_photo.DealershipRequired`).
- **Choices validation.** `full_clean()` rejects invalid
  category / severity / status / content-type.
- **Enum vocabulary.** Each choices tuple contains exactly the
  documented number of values (12 / 4 / 2 / 4).
- **Cascade behavior.** Deleting a `Vehicle` cascades to
  `ConditionReport`; deleting a report cascades to findings +
  photos.
- **Cross-tenant guards.** `clean()` on all three models
  rejects a `dealership` mismatch against the parent Vehicle
  (mirrors `test_vehicle_acquisition.CrossTenantClean` +
  `test_vehicle_cost.CrossTenantClean`).
- **`_TENANT_CARRIER_MODEL_NAMES` extension.** The three new
  carriers are registered by `register_default_dealership_autofill()`
  without breaking the six existing ones (mirror
  `test_dealership.WritePathFallback.*` shape).
- **Photo whitelist.** `ConditionFindingPhoto.content_type`
  restricted to the four whitelist values at the model layer
  (defense in depth — the API layer will also whitelist at
  URL issuance in M3.4).
- **`ConditionReport.completed_at` invariant.** NULL exactly
  when `status="draft"`; set exactly when `status="complete"`
  (model `clean()` guard).

### Read-first list for SESSION_056

1. `docs/roadmap/MILESTONE_3_PLANNING.md` — the planning
   artifact drafted this session; §0 practices, §1.1
   `ConditionReport` field shape, §1.2 `ConditionFinding`
   field shape + category/severity enums, §1.5
   `ConditionFindingPhoto` field shape, §2 migration impact,
   §3 M3-invariants checklist rows M3.1 must satisfy at
   close, §7 M3.1 detail.
2. `backend/dealer_ai/models.py` — reread
   `VehicleAcquisition` + `VehicleCost` (SESSION_046 shape)
   as the persistence-layer template M3.1 mirrors, especially
   the `clean()` cross-tenant guards.
3. `backend/dealer_ai/services/tenancy.py` — the
   `_TENANT_CARRIER_MODEL_NAMES` tuple + the
   `register_default_dealership_autofill` function M3.1
   extends.
4. `backend/dealer_ai/tests/test_vehicle_acquisition.py` +
   `test_vehicle_cost.py` (SESSION_046) — test shape M3.1
   mirrors.
5. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b M2.1 entry —
   the "core ledger models" increment shape M3.1 mirrors.

### Explicit non-goals for SESSION_056

- ❌ Do NOT write the service module — that is M3.2.
- ❌ Do NOT add any `@property` on `Vehicle` — that is M3.3.
- ❌ Do NOT introduce `django-storages` — that is M3.4.
- ❌ Do NOT add any endpoint — that is M3.6.
- ❌ Do NOT change permission classes.
- ❌ Do NOT change tenancy resolver signatures.
- ❌ Do NOT change safety pipeline.
- ❌ Do NOT reopen the M2 ledger surface.
- ❌ Do NOT introduce any AI role.

### Boundary condition

Test baseline at SESSION_056 close: 1,753 → ~1,793 pass. All
new; zero regressions. Migration `0015` applied cleanly.
`makemigrations --check --dry-run` reports "No changes
detected." App remains deployable.

## Anchors that win on conflict (for SESSION_056)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_3_PLANNING.md` (this session's
   deliverable) — §1 design memo, §3 compatibility checklist,
   §7 increment sequencing.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons
   (the eleven inherit unchanged).
7. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b (increment
   shape template).
8. `docs/research/RECON_MAPPING.md` +
   `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 2
   (business-truth for anything the planning artifact does
   not resolve).
9. This handoff (`SESSION_055_milestone_3_planning.md`) — the
   storage decision + increment sequence + M3.1 scope
   authoritative for the next session.
10. Current source code — the shipped M1 + M2 surface (M3
    inherits it unchanged).

Planning docs are claims. Rules + research + code are facts.
