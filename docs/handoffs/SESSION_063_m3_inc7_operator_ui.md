---
title: "SESSION_063 handoff — Milestone 3 · Increment 7 (operator condition-report UI)"
status: historical
type: handoff
date: 2026-08-01
session: 063
milestone: 3
milestone_status: in-progress
increment: 7
increment_status: shipped
commit: TBD
---

# SESSION_063 — Milestone 3 · Increment 7 (M3.7 — operator condition-report UI)

## What shipped

First frontend work in Milestone 3. Operator condition-report
UI wired to all 10 M3.6 endpoints. Route + page + 7
extracted components + 10 typed API helpers + inventory-card
button + PATCH/DELETE `authFetch` helpers.

**Zero backend changes.** Backend baseline **2,124 pass**
unchanged.

Frontend verification: `npx tsc --noEmit` clean; `npx vite
build` clean (same pre-existing chunk-size warning as M2.7).

**Manual browser walkthrough was NOT performed** — this
session had no interactive browser access. See "Manual
browser verification" below for the honest scope of what
remains operator verification.

## Components added

Per M3.7 spec pushback "if the page begins approaching M2's
~800-line ledger page, stop and extract components." Extracted
7 small components into
`frontend/src/components/condition-report/`:

- `SeverityBadge.tsx` (102 lines) — badge + icon + text label
  per severity. **A11y: not color-only.** Exports
  `SEVERITY_DISPLAY_ORDER` (safety → advisory).
- `CompletionBanner.tsx` (61) — visible locked-state banner
  for completed reports. Distinct visual state, not merely
  disabled.
- `PhotoUploadButton.tsx` (185) — three-step upload
  orchestrator (request → upload → attach) with step-labeled
  progress + per-step humanized error UI.
- `PhotoGallery.tsx` (181) — per-finding gallery; delete
  affordance draft-only; detects `LOCAL_READ_URL_MARKER`
  prefix to render a dev placeholder instead of a broken
  `<img>`.
- `FindingCard.tsx` (277) — one finding + inline edit form +
  per-finding photo gallery. Category + severity re-parenting
  intentionally out of scope for edit (service whitelist
  would refuse).
- `AddFindingForm.tsx` (196) — expandable inline form.
- `CreateReportForm.tsx` (152) — shown when the vehicle has
  no report yet.

**Page**: `frontend/src/pages/VehicleConditionReportPage.tsx`
(~506 lines — well under M2 ledger's 1,059-line ceiling).
State + workflow orchestration lives here; presentation
lives in the components.

## API helpers

Extended `frontend/src/lib/api.ts` with 10 typed helpers
(one per M3.6 endpoint, all via existing `authFetch`):

- `fetchLatestConditionReport(stock)`.
- `createConditionReport(stock, body)`.
- `completeConditionReport(stock, reportId)`.
- `createConditionFinding(stock, reportId, body)`.
- `updateConditionFinding(stock, findingId, body)`.
- `deleteConditionFinding(stock, findingId)`.
- `requestPhotoUpload(stock, findingId, contentType)`.
- `uploadPhotoBytes({stock, findingId, uploadTarget, contentType, file})`
  — branches on `LOCAL_UPLOAD_URL_MARKER` prefix.
- `attachPhoto(stock, findingId, body)`.
- `deletePhoto(stock, publicId)` — public UUID in URL.

Plus:

- Choice constants: `CONDITION_CATEGORY_CHOICES`,
  `CONDITION_SEVERITY_CHOICES`,
  `CONDITION_PHOTO_CONTENT_TYPES`.
- `LOCAL_UPLOAD_URL_MARKER` constant re-exported so UI
  branching doesn't reach into the storage module.
- Typed interfaces for every request + response body.

**Three-step upload workflow kept literal** per M3.7 spec —
no one-shot `uploadAndAttachPhoto` helper. Callers see the
contract in their code.

## Routing changes

- New route in `frontend/src/main.tsx` inside
  `<RequireAuth>`:
  `dealer-ai-inventory/:stock/condition-report`
  → `<VehicleConditionReportPage />`. Sits alongside the
  existing M2.7 `.../ledger` route.

- New button in `frontend/src/pages/InventoryPreviewPage.tsx`
  card footer beside the existing "Ledger" link:
  "Condition Report". Same operator-only surface — NOT on
  `/showroom`.

## Upload workflow

Follows the M3.5 backend contract literally:

1. `requestPhotoUpload(stock, findingId, contentType)` —
   returns `PhotoUploadTarget`.
2. `uploadPhotoBytes({...uploadTarget, file})` — branches:
   - **Local dev**: `upload_url` starts with
     `LOCAL_UPLOAD_URL_MARKER` → POST multipart to the
     M3.6B local receiver via `authPostForm`.
   - **Production**: real presigned S3 URL → direct
     browser-to-S3 PUT via plain `fetch` (bypasses Django).
3. `attachPhoto(stock, findingId, {storage_key,
   content_type, size_bytes, caption?})` — HEAD-verified by
   the backend before the row lands.

`PhotoUploadButton` shows step-labeled progress
("Requesting…", "Uploading…", "Attaching…") so operators
see exactly which stage failed on error.

## Role behavior

Convention preserved from M2.7:
`WRITE_ROLES = ["dealer_owner", "sales_manager"]`.
`useAuth().hasRole(...WRITE_ROLES)` gates all edit
affordances. Read affordances render for any authenticated
caller. Server authorization is authoritative — the M3.6A/B
endpoints enforce `IsSalesManagerOrOwnerAtActiveDealership`.

Advisor / porter roles get:

- The vehicle header + report metadata + findings + photos
  (read-only).
- No "Create draft report" form.
- No "Add finding" button.
- No per-finding "Edit" / "Delete" buttons.
- No `PhotoUploadButton`.
- No `PhotoGallery` delete affordance.
- No "Complete report" button.

Anonymous callers redirect to `/login?next=...` via
`<RequireAuth>` (M1 · 4E pattern, unchanged).

## Draft/complete behavior

Follows M3.7 spec "Completed reports should look different,
not merely become disabled":

- **Draft state**: full edit affordances render for write
  roles. Findings show inline "Edit" + "Delete" buttons.
  "Add finding" button visible. "Complete report" section
  at the bottom.
- **Complete state**: `CompletionBanner` renders at the top
  (visible locked state — green banner with lock icon +
  completion date/authored_by). ALL edit affordances hidden
  (add/edit/delete finding, upload photo, delete photo,
  complete button — none render). Data itself is fully
  visible — findings, notes, estimated costs, photos all
  remain readable. Read affordance untouched.
- Status Badge in the header switches from outline (draft)
  to solid emerald (complete).

## Browser verification

**None performed via automation this session.** No
interactive browser access.

**Twelve steps from M3.7 spec that remain operator
verification** (first-live-use):

1. Open inventory.
2. Navigate to Condition Report from a vehicle card.
3. Create report (fill inspector / date / mileage form).
4. Add multiple findings across different categories +
   severities.
5. Upload photo(s) to a finding.
6. Attach (button flow — verify server metadata
   verification succeeds).
7. Refresh page.
8. Verify persistence (report + findings + photos still
   rendered).
9. Complete report ("Complete report" button).
10. Verify editing disappears (no add/edit/delete/upload
    affordances; `CompletionBanner` visible).
11. Verify advisor role sees read-only surface (log in as
    `smoke_advisor`; walk to the report; confirm no edit
    affordances render).
12. Verify anonymous redirects to login (log out; navigate
    to a report URL; confirm redirect to `/login?next=...`).

If UI friction surfaces during steps 1-12, record in
`docs/roadmap/DEFERRED_IDEAS.md` (create the file at that
moment; the M3 planning + retrospective docs are the current
home for deferred items, but a stand-alone
`DEFERRED_IDEAS.md` becomes appropriate when the first
piece of "not planned anywhere else" friction shows up).

## Frontend verification (SESSION_063 — performed)

- `npx tsc --noEmit` — **exit 0**.
- `npx vite build` — **success**. Bundle:
  `dist/assets/index-F0sQTOf7.js` 552.78 kB (gzip 150.79 kB).
  Same pre-existing chunk-size warning as M2.7 — unchanged.
- Backend baseline: `python3 manage.py test dealer_ai` →
  **2,124 pass, 1 skipped, 0 fail** (identical to
  post-M3.6B baseline).
- **Zero backend files touched** — verified via `git status`.
- **Zero condition-report keywords in public showroom** —
  new inventory card button lives only on the operator
  `InventoryPreviewPage`; `PublicShowroomPage` is not
  modified.
- Ledger navigation still works (M2.7 route unchanged; the
  new button was ADDED beside "Ledger" in the operator card
  footer, not replacing it).

## Compatibility

Preserved unchanged:

- All backend surfaces (M1 tenancy, M1 auth, M1 · 4D
  permissions, M2 ledger, M3.1 models, M3.2 service, M3.3
  read-model, M3.4 storage, M3.5 photo workflow, M3.6A/B
  endpoints).
- All existing frontend routes.
- Public showroom (no changes).
- Onboarding, salespeople, embed assistant, chat surfaces
  — all unchanged.
- Auth flow (M1 · 4E) — unchanged.
- Copper Canyon branding + `brand.*` tokens — reused; no
  new design language.
- Six v4-only Tailwind variant patterns — **not used** (per
  CLAUDE.md caveats about the shadcn/ui v3 bridge).

Modified (this session — frontend only):

- `frontend/src/lib/api.ts` — 10 new helpers + types +
  constants (~230 additive lines).
- `frontend/src/lib/authFetch.ts` — `authPatchJSON` +
  `authDelete` helpers.
- `frontend/src/main.tsx` — new route registration (2 lines
  + import).
- `frontend/src/pages/InventoryPreviewPage.tsx` —
  "Condition Report" button beside "Ledger" (operator-only
  card).

New (this session — frontend only):

- `frontend/src/pages/VehicleConditionReportPage.tsx`
  (506 lines).
- `frontend/src/components/condition-report/` — 7 files
  (~1,154 lines total).

## Security invariants (verified by code inspection)

- **`storage_key` never rendered.** The only place the UI
  references it is `PhotoUploadButton.uploadPhotoBytes`'s
  call chain, where it is passed to the local receiver's
  form-data OR bound into the presigned PUT URL — never
  displayed. Every photo projection surface uses
  `public_id`.
- **`LOCAL_UPLOAD_URL_MARKER` never rendered.** Referenced
  only in the API-layer branching helper.
- **`LOCAL_READ_URL_MARKER`** detected in `PhotoGallery` and
  swapped for a "Local dev — no signed URL" placeholder
  rather than passed to `<img src>`.
- **No bucket / provider / adapter internals** rendered.
- **No AWS credentials** rendered (they're never in a
  response body per M3.4 invariants).

## Explicitly out of scope for M3.7 (deferred / never in M3)

- ❌ Report scoring / completion percentage.
- ❌ AI recommendations.
- ❌ Work Orders / Vendor integration.
- ❌ Image editing.
- ❌ Photo reordering.
- ❌ Caption editing after attach.
- ❌ Recon manager role.
- ❌ Lifecycle transitions.
- ❌ Mobile optimization.
- ❌ Milestone 3 closeout (M3.8).
- ❌ Component-test framework (no Vitest / Jest / RTL — same
  discipline as M2.7).
- ❌ Playwright automation of the 12 browser-verification
  steps.

## Files changed

- New: `frontend/src/pages/VehicleConditionReportPage.tsx`
  (506 lines).
- New: `frontend/src/components/condition-report/SeverityBadge.tsx`
  (102 lines).
- New: `frontend/src/components/condition-report/CompletionBanner.tsx`
  (61 lines).
- New: `frontend/src/components/condition-report/PhotoUploadButton.tsx`
  (185 lines).
- New: `frontend/src/components/condition-report/PhotoGallery.tsx`
  (181 lines).
- New: `frontend/src/components/condition-report/FindingCard.tsx`
  (277 lines).
- New: `frontend/src/components/condition-report/AddFindingForm.tsx`
  (196 lines).
- New: `frontend/src/components/condition-report/CreateReportForm.tsx`
  (152 lines).
- Modified: `frontend/src/lib/api.ts` — 10 helpers + types.
- Modified: `frontend/src/lib/authFetch.ts` — `authPatchJSON`
  + `authDelete`.
- Modified: `frontend/src/main.tsx` — route registration.
- Modified: `frontend/src/pages/InventoryPreviewPage.tsx`
  — inventory card button.
- Modified: `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.7
  annotated SHIPPED.
- New: `docs/handoffs/SESSION_063_m3_inc7_operator_ui.md`
  — this handoff.
- Modified: `00-START-NEXT-SESSION.md` — SESSION_064 = M3.8
  closeout priority.

No modifications to any backend file. Zero changes to
`requirements.txt`, migrations, models, admin, services,
permissions, views (backend), urls (backend), or the six
production settings files.

## Recommended exact scope for SESSION_064 (M3.8 — Milestone 3 closeout)

Per `MILESTONE_3_PLANNING.md` §7 M3.8 (unchanged since
SESSION_055 planning) + the M2.8 closeout template
(SESSION_054):

**Scope.** Documentation-only session. Closes out Milestone
3 and prepares Milestone 4.

1. **Verify all M3 invariants** end-to-end via the §3
   compatibility checklist annotated in-place with
   evidence citations (test class names, endpoint paths,
   commit hashes). Same shape as M2's SESSION_054
   §3 sweep.
2. **Write `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md`**
   mirroring `MILESTONE_2_RETROSPECTIVE.md` (SESSION_054):
   - §1 What shipped (per-increment summary).
   - §2 Test baseline evolution
     (M2 close 1,753 → M3.1 1,813 → M3.2 1,874 → M3.3
     1,894 → M3.4 1,940 → M3.5 1,998 → M3.6A 2,067 → M3.6B
     2,124 → M3.7 unchanged 2,124).
   - §3 Timeline (SESSION_055 → SESSION_063).
   - §4 Reviewed refinements (there were 6-8 across
     M3.1–M3.7 — every one documented in the respective
     handoff's SHIPPED annotation).
   - §5 Compatibility with M1 + M2.
   - §6 Lessons (increment discipline paid off — M3.6 split
     into A/B; latent-bug compat patches surfaced by pip
     install; storage-first delete strategy;
     provider-neutral service boundaries).
   - §7 Deferrals (create `DEFERRED_IDEAS.md` if the M3.7
     browser verification surfaces friction that doesn't
     fit anywhere else).
   - §8 M4 handoff guidance (recon-manager role, work
     orders, findings → work order automation).
3. **Update `docs/CAPABILITY_MATRIX.md`** with the M3
   shipped surface (10 endpoints, 3 models, 4 services,
   1 frontend page + component library).
4. **Roadmap flips** in
   `docs/roadmap/IMPLEMENTATION_ROADMAP.md`:
   `milestone_3_status: shipped` (from `in-progress`);
   `next_milestone: 4` (recon automation).
5. **Overwrite `00-START-NEXT-SESSION.md`** with the M4
   planning-pass priority (SESSION_065 = M4.0).

**Boundary.** No code changes. Backend baseline unchanged
(2,124). Frontend baseline unchanged.

**Explicit non-goals for M3.8.**

- ❌ Any code change (backend or frontend).
- ❌ Any migration.
- ❌ Any new feature.
- ❌ M4 planning drafting (that's SESSION_065 = M4.0).

## Anchors that win on conflict for SESSION_064

1. `docs/PROJECT_RULES.md`.
2. `docs/DOC_GOVERNANCE.md`.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3 +
   §Milestone 4.
4. `docs/roadmap/AUTHENTICATION_MODEL.md`.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.1–M3.7
   SHIPPED; §7 M3.8 is the sub-scope for the next session;
   §3 compatibility checklist is the load-bearing artifact
   for the retro sweep.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` — shape
   template for the M3 retro.
7. `docs/roadmap/MILESTONE_2_PLANNING.md` §8 M2.8 closeout
   annotation — shape template for §7 M3.8 annotation.
8. `docs/CAPABILITY_MATRIX.md`.
9. All handoffs SESSION_055 – SESSION_063.

## Operational state (post-SESSION_063 — M3.7 operator UI shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015` applied. Test baseline: **2,124 pass**, 1
  skipped, 0 fail (unchanged this session).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. New route
  `/dealer-ai-inventory/:stock/condition-report`
  registered. `npx tsc --noEmit` clean. `npx vite build`
  clean.
- **Frontend (prod):** NONE.
- **DRF defaults + CSRF + permissions:** unchanged.
- **Env-override surface:** unchanged.
- **New runtime primitives (M3.7 — frontend only):**
  1 page + 7 components + 10 API helpers + 2 authFetch
  helpers + 1 inventory-card button.
- **Milestone 3 shipped surface:** M3.0 planning + M3.1
  models + M3.2 service + M3.3 read-model + M3.4 storage +
  M3.5 photo workflow + M3.6A core admin API + M3.6B photo
  API + M3.7 operator UI (SESSION_063 — this session).
  Remaining: M3.8 closeout queued for SESSION_064.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Create at SESSION_064 if the retrospective sweep
  or M3.7 browser verification surfaces anything that
  doesn't fit existing planning / retro docs.
