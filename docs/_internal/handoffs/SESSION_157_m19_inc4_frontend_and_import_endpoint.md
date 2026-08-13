---
title: "SESSION_157 handoff — Milestone 19 · Increment 4 (M19.4 — Frontend admin + inventory-import endpoint)"
status: historical
type: handoff
date: 2026-08-02
session: 157
milestone: 19
milestone_status: in-progress
milestone_name: "Founding Dealer Pilot Onboarding"
increment: 4
increment_status: shipped
---

# SESSION_157 — Milestone 19 · Increment 4 (M19.4 — Frontend admin surface + inventory-import endpoint)

## What shipped

Mixed-stack increment per
`MILESTONE_19_PLANNING.md` §7 M19.4.
Ships the fifth pilot admin endpoint
(inventory import, deferred from M19.3)
+ its frontend consumer + full pilot
admin surface embedded in
`DealerAdmin`.

**Two §0.a M19.4 implementation-time
decisions recorded** (do not count
against planning-time streak per M10
§9). Both surfaced at open with
grounding in existing patterns.

### §0.a M19.4 decision 1 — DRF `FileField` for multipart upload

**Decision.** The inventory-import
endpoint uses a `FileField` on a DRF
serializer +
`@parser_classes([MultiPartParser])`
on the view. Raw `request.FILES`
inspection ruled out because it
bypasses the serializer validation
pattern the other pilot endpoints
follow and would duplicate error
handling.

Discovered gap during implementation:
`@api_view` alone does not accept
multipart bodies (returns 415 with
`"Unsupported media type"`). Fixed by
adding
`@parser_classes([MultiPartParser])`
to the decorator stack.

Second discovered gap: Django's
`UploadedFile.read()` returns bytes,
but `csv.DictReader` requires text.
The M19.2 wrapper's `_read_csv_rows`
helper was extended additively to
detect bytes-mode file-likes and wrap
them in an `io.TextIOWrapper` with
`utf-8-sig` encoding (preserves BOM
tolerance for Excel-saved CSVs).

### §0.a M19.4 decision 2 — extend existing `/dealer-ai-admin` route in place

**Decision.** Pilot admin surfaces
as a `<PilotOnboardingSection>` sub-
section inside `DealerAdmin.tsx`.
Operator route count stays at 20 —
no new route is added. Matches the
M19.0 planning posture "M19.4
extends existing admin route in
place" verbatim.

The alternative — a new sibling route
`/dealer-ai-admin/pilots` mirroring
the existing `/dealer-ai-admin/team`
pattern — was ruled out at open. Pilot
admin is a low-frequency surface
(create, advance, upload — not daily
churn). Embedding as a section keeps
Chris's cognitive surface flat.

## Delivered

**Backend:**

- New endpoint
  `POST /admin/pilots/<slug>/inventory/import/`
  in
  `dealer_ai/views_pilot_onboarding.py::admin_pilot_inventory_import`.
  200 with serialized
  `PilotInventoryImportResult`; 400 on
  missing file; 404 on nonexistent /
  non-pilot slug; 500 on
  `NonPilotImportError`
  (belt-and-suspenders).
- New serializer
  `InventoryImportRequestSerializer`
  with a `FileField` for canonical
  multipart validation.
- URL wiring adds the fifth pilot
  path; admin surface grows **112 →
  113**.
- Additive fix in
  `services/pilot_onboarding/inventory_import.py::_read_csv_rows`
  — detects bytes-mode file-likes
  (Django `UploadedFile`) and wraps
  them in `io.TextIOWrapper` with
  `utf-8-sig` encoding. Text-mode
  `StringIO` path unchanged. M19.2
  tests continue to pass without
  modification.

**Frontend:**

- New API client functions in
  `frontend/src/lib/api.ts`:
  - `fetchPilotDealerships` (GET)
  - `createPilotDealership` (POST)
  - `advancePilotChecklistStep` (POST)
  - `importPilotInventory` (POST
    multipart via
    `authPostForm(FormData)`)
  - `terminatePilotDealership` (POST)
  - Five DTO types matching the
    backend projections.
- New component
  `frontend/src/components/pilots/PilotOnboardingSection.tsx`
  (534 lines) with four sub-panels:
  - `PilotCreateForm` — slug + name +
    owner_username with disabled-until-
    filled submit + friendly 409 / 400
    error surfaces.
  - `PilotList` — clickable rows with
    ready / in-progress badges +
    empty / loading states.
  - `PilotDetailPanel` (per-pilot
    detail — shows on row click):
    - `ChecklistStepper` — ordered
      steps per
      `PILOT_ONBOARDING_STEP_ORDER`;
      complete button per uncompleted
      step; readiness precondition 409
      error surface.
    - `InventoryUploadPanel` — file
      input + submit + accepted /
      rejected counters + expandable
      rejected-rows details block.
    - `TerminateForm` — mode picker
      (archive / cleanup) + reason
      textarea + two-step confirm gate.
- Integration into
  `DealerAdmin.tsx` — one new
  `<PilotOnboardingSection />` render
  above the existing modals.

**Tests:**

- Backend: 10 focused tests in
  `tests/test_m194_inventory_import_endpoint.py`:
  - Happy path 200 with accepted
    stock numbers (2 rows in → 2
    accepted).
  - Partial-success projection
    (accepted + rejected coexist).
  - Empty CSV returns empty
    projection.
  - Missing file returns 400.
  - Nonexistent slug returns 404.
  - Non-pilot (demo) slug returns
    404.
  - Unauth returns 401 / 403.
  - Persisted Vehicles carry
    `source="pilot-inventory-import"`.
  - Endpoint count `>=` 113 growth
    assertion (112 → 113).
  - Permission-class exact-set
    equality — zero-drift streak
    now **eighteen consecutive
    milestones** (M10 → M19.4).
- Frontend: 13 Vitest cases in
  `frontend/src/components/pilots/PilotOnboardingSection.test.tsx`:
  - Empty state renders.
  - Each pilot renders with ready
    badge.
  - Create submit disabled until all
    fields populated.
  - Create form calls
    `createPilotDealership` +
    reloads list.
  - 409 slug collision surfaces
    friendly error.
  - Checklist steps render in fixed
    vocab order.
  - Step advance calls the API +
    triggers reload.
  - 409 readiness precondition
    surfaces friendly error.
  - CSV upload sends multipart body
    + reflects accepted / rejected.
  - Rejected rows expand in details
    block.
  - Terminate requires confirm click
    (two-step gate).
  - Terminate mode switch persists
    to payload.
  - Global fetch error surfaces.

## Baseline delta

- **Backend:** 4,659 → **4,669 pass**,
  1 skipped, 0 fail. **+10 tests, 0
  regressions.** In-range with the
  8-12 planning target.
- **Frontend Vitest:** 140 → **153
  pass**. **+13 tests, 0
  regressions.** In-range with the
  10-15 planning target.
- Migrations `0043-0048` (unchanged
  — M19.4 is service+view+frontend).
- Tenancy carriers **52** (unchanged
  — no new tenant-scoped models).
- DRF admin surface **112 → 113**
  (+1 inventory-import endpoint).
- Frontend operator routes **20**
  (unchanged per §0.a M19.4 decision
  2).
- Permission classes **7 actual** —
  **zero-drift streak now eighteen
  consecutive milestones** (M10 →
  M19.4).
- Celery-beat task families **10**
  (unchanged).

## Streak update

**85 planning-time as-recommended
M5.1 → M19.0** (unchanged — M19.4 is
implementation-time work per M10 §9).
**Two §0.a M19.4 implementation-time
decisions recorded** (DRF `FileField`
overlay + extend-existing-admin-route-
in-place). Both grounded in the
pre-existing shipping patterns.

## What's next: SESSION_158 M19.5 playbook + first end-to-end dry-run

Per `MILESTONE_19_PLANNING.md` §7
M19.5:

- New doc
  `docs/PILOT_ONBOARDING_PLAYBOOK.md`
  — narrative step-by-step for
  Chris walking through a fresh
  pilot from prospect intake to
  readiness confirmed. Includes
  screenshots of the M19.4 admin
  surface, the CSV template
  reference, and expected outcomes
  at each checklist step.
- First end-to-end dry-run inside
  the test suite (or as a Django
  management command) that
  exercises every M19.1-M19.4 verb
  and endpoint against a synthetic
  pilot from create through
  readiness_confirmed. Ships a
  fixture proving the full
  substrate holds together.
- Focused tests (~5-10 target) in
  `tests/test_m195_pilot_dry_run.py`.

**Backend baseline target at M19.5
close:** 4,669 → ~4,674-4,679 pass
(+5-10 tests, 0 regressions).
Frontend Vitest: 153 (unchanged —
no frontend at M19.5).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_156_m19_inc3_endpoints.md`
7. `docs/PILOT_INVENTORY_TEMPLATE.md`
8. `docs/CAPABILITY_MATRIX.md` §7s
9. `backend/dealer_ai/views_pilot_onboarding.py`
   (five endpoint handlers)
10. `frontend/src/components/pilots/PilotOnboardingSection.tsx`
    (the admin surface)
11. `backend/dealer_ai/tests/test_m194_inventory_import_endpoint.py`
    +
    `frontend/src/components/pilots/PilotOnboardingSection.test.tsx`
    (behavior contract)
