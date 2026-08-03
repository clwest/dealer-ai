---
title: "SESSION_187 handoff — Milestone 25 · Increment 2 (M25.2 — test-drive UI + admin vehicle list endpoint)"
status: historical
type: handoff
date: 2026-08-03
session: 187
milestone: 25
milestone_status: in-progress
milestone_name: "Lead-to-Test-Drive Operational Completion"
increment: 2
increment_status: shipped
commit: TBD
---

# SESSION_187 — Milestone 25 · Increment 2 (M25.2 — test-drive UI + admin vehicle list endpoint)

## What shipped

M25.2 closes M24.1-open §3 deferral **12** (test-drive UI) — the
`<RecordTestDriveForm>` component is now attached inside
`LeadDetailModal` as a collapsible "Schedule test drive" section
per MILESTONE_25_PLANNING.md §5.d modal-only lock. Operators can
receive a lead, see its source, assign it, and schedule the
customer's test drive without leaving the modal. The M25 anchor
business question is answered end-to-end for walk-in / phone /
referral / webhook leads.

**Backend additions:**

- **`GET /admin/vehicles/` endpoint** added at M25.2 open per
  empirical discovery (see below). Thin QuerySet wrapper matching
  the M11.6 `admin/test-drives/list/` precedent — tenant-scoped
  filter, optional `search` / `condition` / `is_available`
  querystrings, cap at 100 rows, compact projection (id +
  stock/year/make/model/trim + condition + price + image_url +
  is_available + display_name). Reuses M4
  `IsSalesManagerOrOwnerAtActiveDealership` — zero-drift
  permission-class streak preserved. Corresponding
  `admin-vehicle-list` URL registered before the stock-scoped
  ledger routes.
- **`seed_journey_sales_operational_entry` extended** with one
  deterministic Vehicle fixture (`stock=M25-TEST-DRIVE-01`, 2025
  Ford Bronco Wildtrak). Idempotent via `get_or_create` on the
  stable stock number. The M25.2 Playwright journey targets this
  row via search + testid lookup.

**Frontend additions:**

- **`salesApi.ts::listAdminVehicles`** — typed wrapper for
  `GET /admin/vehicles/` with `AdminVehicleRow` /
  `AdminVehicleListResponse` / `AdminVehicleListFilters` interfaces.
- **`<RecordTestDriveForm>`** component in
  `frontend/src/components/sales/` matching the M24.1
  `<LeadIntakeForm>` substrate pattern. Two-zone vehicle picker
  per §5.e: "Suggested for this lead" (reads
  `detail.interested_vehicles` from the modal) + "All inventory"
  (lazy-loads via `listAdminVehicles` with debounced search).
  Optional fields: `duration_minutes`, `route_notes`,
  `customer_reaction`, `objections_captured` (comma-separated),
  `next_action`. `driven_at` defaults server-side to
  `timezone.now()` per M11.2. Submit → `onCreated` fires;
  optional Cancel → `onCancel`. Injectable `loadInventory` +
  `submit` for tests.
- **`LeadDetailModal` collapsible integration** — new
  "Schedule test drive" section between "Interested vehicles"
  and "AI conversation summary". Collapsed by default; expands
  on operator click. On successful submit → collapses with a
  "Recorded" success badge in the header. Modal-only per §5.d
  — no secondary launch on `DealerAiSalesTestDrives`.
  `data-testid` set for Playwright targeting:
  `schedule-test-drive-section`, `schedule-test-drive-toggle`,
  `schedule-test-drive-success`.

**Test additions:**

- **Backend +11 tests** in new file
  `tests/test_m252_vehicle_list_endpoint.py`:
  4 auth-matrix (401/403/200 for anonymous/advisor/sales_manager/
  dealer_owner), 7 shape+filter cases (tenant scoping,
  projection shape, search across stock/year/make/model/trim,
  condition + is_available filters, garbage-filter tolerance,
  100-row cap, ordering).
- **Frontend +7 tests** in new file
  `RecordTestDriveForm.test.tsx`: inventory load-on-mount,
  suggested-zone render, submit-disabled-until-vehicle,
  submit-with-optional-fields + reset, 404-error humanization,
  inventory-load error, search-refetches-and-filters-suggested.
- **Acceptance +1 journey** — new
  `journeys/sales_manager/lead_to_test_drive.spec.ts`
  exercises: preflight fixture-vehicle-id resolution via the
  M25.2 endpoint → walk-in intake → modal opens → assign
  advisor → expand collapsible → search "Bronco" → click
  fixture row → submit → assert Recorded badge + form
  unmounts → close modal → assert business outcome via
  `admin/test-drives/list/?lead_id=` (correct lead / vehicle /
  dealership / driven_by_user / driven_at / duration /
  reaction associations) → navigate to
  `DealerAiSalesTestDrives` → assert row visible with
  expected reaction text.

## Starting-state verification (this session)

- `git status` — clean; 4 commits ahead of `origin/main` from
  M25.0 + M25.1.
- Backend baseline from M25.1 close: 4,782 pass, 1 skipped, 0
  fail. Frontend: 219 pass. Acceptance: 13 journeys.
- `python3 manage.py check` clean; migrations clean at open.
- Frontend + acceptance `tsc --noEmit` clean at open.

## Empirical discovery at M25.2 open (informs §5.e)

**Surprise: no admin tenant-wide vehicle-list endpoint existed.**
Every `admin/vehicles/*` route was stock-scoped
(`admin/vehicles/<stock>/ledger/`,
`admin/vehicles/<stock>/acquisition/`, per-vehicle listing +
photos + condition endpoints, per-vehicle sale/delivery/lifecycle
verbs). No `admin/vehicles/` list. The M25 planning §5.e note
"likely `/admin/vehicles/` or equivalent" turned out to be
optimistic — verification at open confirmed the endpoint did not
exist.

Impact: the M25.2 test-drive picker needed a full-inventory
fallback for walk-in / phone / referral leads (which land with
empty `interested_vehicles`). Without an endpoint, three of the
four M24 intake channels would be shut out of the test-drive
workflow, defeating the M25 workflow-completion narrative.

Three options considered at open:

- **Option A** — Add the additive `GET /admin/vehicles/` list
  endpoint. Small (~30 lines), follows M11.6 precedent, reuses
  existing M4 permission class. Genuinely load-bearing for the
  workflow.
- **Option B** — Source only from `detail.interested_vehicles`.
  Shuts out walk-in / phone / referral leads — rejected.
- **Option C** — Manual stock-number entry. Fragile,
  operator-hostile — rejected.

**User locked Option A** at open. Ships one additive endpoint +
one typed wrapper + one seed fixture on top of what M25 planning
originally anticipated. Recorded honestly per the "record
planning corrections honestly" durable lesson from M24.

## Baselines at M25.2 close

- **Backend: 4,793 pass** (+11 from M25.2 vehicle-list endpoint
  tests; +13 total across M25 from the 4,780 pre-M25 baseline).
- **Frontend: 226 pass** across 32 test files (+7 from M25.2
  RecordTestDriveForm tests; +17 total across M25 from the 209
  pre-M25 baseline).
- **Acceptance: 14 journeys** (13 → 14 with the new
  `lead_to_test_drive.spec.ts`). Full clean-DB run: **20 passed
  (~30s)** including 6 setup steps.
- **Migrations:** 0049 (M25.1) unchanged; no new migrations in
  M25.2.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` — "No
  changes detected."
- Frontend + acceptance `tsc --noEmit` clean.

## Design decisions applied at M25.2

- **Additive endpoint following M11.6 precedent.** Same shape
  (thin QuerySet wrapper, tenant filter, optional querystrings,
  100-row cap, `{count, results}` response). No new domain
  logic.
- **Compact projection.** id + stock/year/make/model/trim +
  condition + price + image_url + is_available + display_name —
  enough to render a picker row with a thumbnail; heavier
  fields (VIN, features, description) load via per-stock
  endpoints when the operator drills in.
- **Search across stock/year/make/model/trim.** Case-
  insensitive substring on strings; exact match on year when
  the search string is numeric. Handles the operator's
  natural picker query (e.g. "F-150", "2024", "Wildtrak")
  without over-engineering full-text search.
- **`is_available` filter defaults to unset.** Operator flows
  that record a completed test drive after a sale still work.
  Adding `?is_available=true` narrows to available inventory
  for pre-sale test drives.
- **Vehicle picker: suggested + inventory zones.** Suggested
  vehicles from `detail.interested_vehicles` render at the
  top; inventory fetches on mount + on search change. Search
  narrows both zones consistently (suggested filtered
  client-side; inventory refetched with `search` querystring).
- **Debounced search fetch (200ms).** Avoids fetch-per-keystroke
  while keeping the picker responsive.
- **Injectable `loadInventory` + `submit`.** Vitest suite
  exercises the picker + submit contract without mocking
  network — dependency-injection pattern matches shipped
  substrate for testability.
- **Recorded success badge in collapsible header, not toast.**
  Discovers post-close-out — operator returns to the modal
  and sees the badge as confirmation, not a transient toast
  that vanishes.
- **Deterministic seed fixture (`M25-TEST-DRIVE-01`).** The
  M25.2 journey targets a known-good vehicle by stable stock
  number. Idempotent via `get_or_create`. No cross-suite
  collision risk.

## Streak

- **Planning-time as-recommended streak → 3** at M25.2 close.
  M25.2 implementation matched the M25 planning §5.d modal-only
  + §5.e suggested + inventory locks exactly. The §5.b Option A
  admin-vehicles endpoint addition was an empirical-discovery
  refinement presented at open and confirmed by the user — same
  pattern as M25.0 (JSONField selection) and M25.1 (no
  refinements needed).
- **Zero-drift permission-class streak → 25.** M25.2 uses the
  existing M4 `IsSalesManagerOrOwnerAtActiveDealership` on the
  new `admin_vehicle_list` endpoint (same class as every M25
  operator surface). Twenty-five consecutive milestones
  (M10 → M25) with no new permission classes.

## What's next: M25.3 close-out (folded into this session per §5.h)

Per MILESTONE_25_PLANNING.md §5.h evidence-sized Option B posture:
M25.2 shipped cleanly with no operator-surface fixes required —
the fold-into-M25.2 close-out condition is met. Following the
M25.2 handoff, this session continues with:

1. **Regenerate the audit artifact.** Expect
   `admin/test-drives/` create endpoint to flip
   `wrapper-only → covered` (M25.2 UI consumes it). The
   webhook endpoint remains wrapper-only per M24.4 no-operator-
   UI design. Total covered post-M25:
   113 → 114 or 115 depending on how the new
   `admin/vehicles/` endpoint's audit categorization lands.
2. **Draft `MILESTONE_25_RETROSPECTIVE.md`** with §8
   (corrections captured honestly: JSONField selection at
   §5.b, `admin/vehicles/` endpoint at M25.2 open) + §9
   evidence for M26 candidate ranking (Candidate H test-
   hygiene, Candidate A2 JE creation UI, gated Candidates T /
   U / L / M).
3. **Update `IMPLEMENTATION_ROADMAP.md`** M25 shipped
   section.
4. **Update `CAPABILITY_MATRIX.md`** §7z (new section for
   M25 shipped surface).
5. **Update `00-START-NEXT-SESSION.md`** with M26.0
   priority (target selection pending).
6. **Ship the M25.3 close-out handoff.**
7. **Coordinated push** of all M25 commits (M25.0 planning
   + hash backfill + M25.1 attribution + hash backfill +
   M25.2 test-drive UI + hash backfill + M25.3 close-out)
   to `origin/main`. **Awaits explicit user confirmation
   per CLAUDE.md safety before push.**

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_25_PLANNING.md` §5 (M25
   governing contract — §5.a + §5.b + §5.c + §5.d + §5.e
   + §5.g locks now all satisfied; §5.h fold pending
   close-out this session)
6. `docs/roadmap/MILESTONE_24_PLANNING.md` §3 (deferrals 12
   + 13 + 14 all closed as of M25.2)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (regenerated at M25.3 close)
8. `docs/CAPABILITY_MATRIX.md` §7y (M24) + §7z (M25 at
   close)
9. `docs/research/SALES_DEPARTMENT_MAPPING.md` §workflow
   step 6 (demonstration)
10. `docs/handoffs/SESSION_186_m25_inc1_attribution.md`
    (M25.1 shipped)
