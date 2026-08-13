---
title: "SESSION_176 handoff — Milestone 23 · Increment 1 (M23.1 — audit-tool false-positive fix + artifact refresh)"
status: historical
type: handoff
date: 2026-08-03
session: 176
milestone: 23
milestone_status: in-progress
milestone_name: "BHPH Origination + Payment Intake"
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_176 — Milestone 23 · Increment 1 (M23.1 — audit-tool false-positive fix + artifact refresh)

## What shipped

Supporting-work increment per §5.d
Option A — targeted regex + parser
enhancements to
`backend/dealer_ai/scripts/audit_operational_surface.py`
that close the HTTP-verb-agnostic
URL-prefix matching false-positive
class identified at M23.0 open. Not
the milestone centerpiece; the two
anchor UIs land at M23.2 (note
origination) and M23.3 (payment
intake).

**Coverage delta.** Audit artifact
regenerated. Coverage **110 → 108
(-2)**. Backend-only **43 → 45 (+2)**.

**Two rows fully reclassified `covered`
→ `defer-candidate-O2`** (genuine
backend-only revealed):

- **Row 123
  `admin-bhph-note-create`
  (POST `admin/bhph-notes/`)** —
  was falsely claimed as consumed
  by `getBhphNote` (a GET wrapper
  for the pk-suffixed path). Now
  correctly `defer-candidate-O2`.
  Confirms the M23.2 target scope.
- **Row 139
  `admin-journal-entry-create`
  (POST `admin/accounting/journal-entries/`)** —
  was falsely claimed as consumed
  by `fetchJournalEntry` (a GET
  wrapper for the pk-suffixed
  path). **NEW genuine gap
  surfaced by audit correction** —
  JE creation UI is genuinely
  missing from the frontend. This
  is exactly the type of finding
  the M22 retrospective §9 A2
  candidate speculated about but
  couldn't confirm. Recorded here
  as evidence for the M23.4
  retrospective §9 M24 candidate
  discussion.

**Five rows with wrapper-list
pruned but staying `covered`**
(different-verb wrappers dropped;
correct-verb wrapper remains):

- Row 41 `admin-vendor-list` (GET)
  — pruned `updateVendor` (PUT);
  kept `fetchVendors` + others.
- Row 51 `admin-work-order-attach-
  findings` (POST) — pruned
  `detachFinding` (DELETE); kept
  `attachFindings`.
- Row 62 `admin-photo-list` (GET)
  — pruned `deletePhoto` (DELETE);
  kept `fetchVehiclePhotos`.
- Row 101 `admin-compliance-
  create` (POST) — pruned
  `updateCompliance` (PUT/PATCH);
  kept `createCompliance`.
- Row 145 `admin-trial-balance-
  snapshot-create` (POST) —
  pruned `fetchTrialBalanceSnapshot`
  (GET); kept `freezeTrialBalance`.

**Budget guard status.** ~30-40
minutes of active work — well under
the ~2-hour §5.d guard. Same
envelope as M22.1. No deferral to a
future audit-tooling milestone
required.

**Backend baseline unchanged:**
4,766 pass, 1 skipped, 0 fail.
Verified post-fix with full
`python3 manage.py test dealer_ai`
— zero regressions. Frontend Vitest
unchanged: 180 pass. Acceptance
suite unchanged: 7 journeys.
Migrations, tenancy carriers,
permission classes, DRF endpoints,
frontend routes, celery-beat
families all unchanged.

## Root-cause reframe (relative to M23.0 open)

At M23.0 open, empirical verification
surfaced audit row 123's false-
positive claim on `admin-bhph-note-
create`. The initial framing was
"HTTP-verb-agnostic URL-prefix
matching." M23.1 investigation
confirmed the framing and revealed
the full symptomatic surface:

- The audit script's
  `cross_reference()` function
  builds four candidate patterns
  per endpoint (base, base with
  `/api/dealer-ai` prefix, base
  with `{PARAM}/` suffix for
  querystring variants, both with
  `{PARAM}/`). The querystring
  variant was added at M21.1 to
  catch wrappers using the
  `${qs ? \`?${qs}\` : ""}` idiom
  (later fixed at M22.1 to also
  handle nested templates).
- The querystring variant matches
  wrappers that use pk-suffixed
  URLs (e.g. `getBhphNote` hits
  `admin/bhph-notes/<pk>/`) —
  because the pk substitutes to
  `{PARAM}` and the wrapper's
  normalized pattern
  `admin/bhph-notes/{PARAM}/`
  matches the base endpoint's
  querystring-variant candidate
  `admin/bhph-notes/{PARAM}/`.
- Without HTTP-verb
  discrimination, a GET wrapper
  hitting `.../<pk>/` gets
  wrongly claimed as consuming
  the sibling POST endpoint at
  the base URL.

The fix orthogonally filters
candidate consumers by HTTP verb
match before de-duplication.
Preserves the querystring-variant
matching for its intended purpose
(handling wrappers using `?${qs}`
idiom with variable-first
assembly) while eliminating the
sibling-endpoint cross-
contamination.

## Three targeted changes

1. **New `methods: frozenset[str]`
   field on `BackendEndpoint`
   dataclass** with default empty
   frozenset. Preserves backwards-
   compatibility (existing code
   paths continue to work when
   methods are unknown).
2. **New `extract_view_methods()`
   helper** walks every `views*.py`
   under `backend/dealer_ai/` and
   extracts `{view_function_name:
   frozenset(methods)}` from
   `@api_view([...])` decorator +
   `def` header pairs via regex.
   Handles multiple methods per
   view (`@api_view(["GET",
   "PUT"])`). Handles intervening
   decorators
   (`@permission_classes`) between
   `@api_view` and `def`. Called
   from `main()` and passed into
   `extract_backend_endpoints`.
3. **New `_HELPER_TO_VERB` module-
   level dict** maps helper wrapper
   name to HTTP verb:
   - `authGetJSON` → GET
   - `authPostJSON` /
     `authPostForm` → POST
   - `authPatchJSON` → PATCH
   - `authPutJSON` → PUT
   - `authDelete` → DELETE
   - `fetch` → GET (public fetch
     calls in this codebase are
     all GETs)
   `cross_reference()` filters
   candidate consumers by
   `_HELPER_TO_VERB[c.helper] ∈
   ep.methods` before de-
   duplication. Filter skipped
   when `ep.methods` is empty
   (backwards-compat).

## Verification

- Ran
  `python3 -m dealer_ai.scripts.audit_operational_surface`
  from `backend/`. Output:
  - Backend endpoints: 153
    (unchanged)
  - Covered: 110 → **108 (-2)**
  - Backend-only: 43 → **45 (+2)**
  - Service verbs: 312 (unchanged)
- Diff of
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  isolated to:
  - Two rows (123, 139)
    reclassify to `defer-
    candidate-O2`.
  - Five rows (41, 51, 62, 101,
    145) have wrapper-list
    pruned but stay `covered`
    with correct-verb wrapper(s)
    remaining.
  - Summary counts updated
    accordingly.
  - No legitimate coverage
    broken.
- Ran full backend test suite
  post-fix — **4,766 pass, 1
  skipped, 0 fail** — zero
  regressions. Audit script is
  operator-invoked; changing it
  doesn't touch any tested code
  path.

## Deferrals surfaced during M23.1

- **JE creation UI** — row 139
  now reveals `admin-journal-
  entry-create` is genuinely
  missing operator-facing UI.
  Not in M23 scope (M23 anchors
  are BHPH origination + payment
  intake). Recorded as evidence-
  based candidate for the M23.4
  retrospective §9 M24
  discussion. Fits the M22
  refined validation-shape
  contract OR the M21 Candidate
  O UI-creation contract
  depending on how a future
  milestone shapes it.
- **Additional audit false-
  positive/negative classes.**
  M22.1 fixed the variable-
  first URL assembly false-
  negative class; M23.1 fixed
  the HTTP-verb-agnostic URL-
  prefix matching false-
  positive class. Two distinct
  regex/parser limitation
  classes fixed at low cost.
  Suggests 2-3 more latent
  classes remain (unquantified);
  each is separately correctable
  when operational evidence
  surfaces them. Reinforces the
  "audit correctness as
  supporting infrastructure"
  posture memory established at
  M22 close.
- **Full AST-based audit
  rewrite** — still explicit
  non-goal per §5.d Option A.
  Targeted regex + parser
  approach continues to suffice
  for the current wrapper
  corpus. If future patterns
  break the approach entirely,
  a dedicated audit-tooling
  milestone becomes the vehicle
  for AST rewrite.
- **Audit-script correctness
  tests.** Discretionary per
  M22.1 precedent. Not added at
  M23.1 — the artifact
  regeneration is the functional
  verification (the two target
  rows either reclassify or they
  don't). If the audit script
  becomes more complex or if
  regressions surface, adding
  pytest coverage of
  `extract_view_methods` +
  `cross_reference` verb
  filtering is a reasonable
  future investment.

## Streak

**Planning-time as-recommended:
still 89 across fourteen
consecutive milestones (M10 →
M23).** M23.1 is implementation
work; no new §5 decisions
surfaced.

**Zero-drift permission-class:
still 22 consecutive milestones
(M10 → M22).** M23.1 introduces
zero permission-class changes.
Streak target at M23.4 close:
23.

## What's next: SESSION_177 M23.2 note origination UI + journey

Per `MILESTONE_23_PLANNING.md` §7
M23.2:

- **`createBhphNote` wrapper** in
  `frontend/src/lib/bhphApi.ts`
  hitting POST `admin/bhph-notes/`.
  Payload type matches backend
  serializer verbatim.
- **`RecordBhphNoteForm`
  component** in
  `frontend/src/components/bhph/`
  with vehicle picker (select
  from available inventory),
  principal input, APR input,
  cadence picker (weekly /
  biweekly / semimonthly /
  monthly), first-payment-date
  picker, submit + error
  handling.
- **Attached to
  `DealerAiBhphPortfolio.tsx`**
  Notes card as persistent "Add
  note" CTA + modal per §5.b
  Option A. Replaces the current
  empty-state message that
  literally documents the gap
  (`DealerAiBhphPortfolio.tsx:193-194`).
- **Vitest coverage** for the
  new component (submit +
  validation + error paths +
  vehicle picker interaction).
- **Extended seed** at
  `backend/dealer_ai/management/commands/seed_journey_bhph_collections_workflow.py`
  with vehicle fixture
  (origination target — an
  available inventory vehicle
  distinct from any existing
  note's collateral) + backend
  test covering fixture
  idempotency + tenant scoping.
- **Extended assertion helper**
  at
  `acceptance/support/assertions/bhph.ts`
  with
  `expectBhphNoteOriginated(request, vehicleId)`
  — asserts a BHPH note exists
  for the given vehicle with
  the expected shape (principal,
  APR, cadence).
- **New journey** at
  `acceptance/journeys/bhph/note_origination.spec.ts`
  walking: land on
  `/dealer-ai-bhph-portfolio` →
  click "Add note" → fill
  origination form → submit →
  verify status message →
  verify new note appears in
  Notes card → business-outcome
  assertion via API using the
  new helper.
- **Small operator-surface gap
  fixes per §5.d** (in-scope
  for one-file trivial changes)
  if any surfaced during
  authoring.
- **Session handoff** at
  `docs/handoffs/SESSION_177_m23_inc2_note_origination.md`.
- **`00-START-NEXT-SESSION.md`**
  refreshed for M23.3.

**Backend baseline target at M23.2
close:** 4,766 → **~4,770** (seed
fixture idempotency tests).
Frontend Vitest: 180 → **~187-192**.
Acceptance suite: **7 → 8**.

## What lands at M23.3 (SESSION_178) — second anchor UI

Payment intake UI + seed extension
+ journey. See MILESTONE_23_PLANNING.md
§7 M23.3 for details.

## What lands at M23.4 (SESSION_179) — close-out

CI validation on all new / extended
journeys + capability matrix §7x +
retrospective (with §9 evidence for
M24 candidate discussion including
the JE creation UI finding from
M23.1) + M24 planning skeleton +
coordinated close-out push per
M18.6 / M19.6 / M20.5 / M21.5 /
M22.4 cadence.

## Non-goals for the remaining M23 increments

Per MILESTONE_23_PLANNING.md §3:

- ❌ Do NOT ship sale-time
  origination trigger (§3
  deferral 1). Portfolio-based
  CTA ships first; sale-time
  trigger revisited when
  operator usage demonstrates
  the sale-time flow is more
  natural.
- ❌ Do NOT add new backend
  service verbs, DRF endpoints,
  tenancy carriers, migrations,
  permission classes, or
  frontend routes.
- ❌ Do NOT rewrite the audit
  script as AST-based —
  targeted regex + parser fix
  already landed at M23.1 per
  §5.d Option A.
- ❌ Do NOT manually verify
  workflows before authoring
  journeys — journey-as-
  verifier per §5.f Option B.
- ❌ Do NOT ship JE creation
  UI in M23 — surfaced at
  M23.1 but out of M23 scope.
  Recorded as M24 evidence-
  based candidate.
- ❌ Do NOT split the BHPH
  seed into per-workflow seeds
  — extend additively per
  §5.e Option A.
- ❌ Do NOT push M23 commits
  individually — coordinated
  close-out push at M23.4.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M22 shipped section landed
   at M22.4)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (active memo — §0.a M23.1
   amendment records shipped
   fix + JE-creation-UI
   finding)
6. `docs/handoffs/SESSION_175_m23_inc0_planning.md`
   (M23.0 close — empirical
   discovery record)
7. `docs/handoffs/SESSION_172_m22_inc1_audit_correction.md`
   (M22.1 close — audit
   correction precedent for
   M23.1 shape)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact — now
   authoritative for both
   variable-first URL
   assembly (M22.1) and HTTP-
   verb-agnostic URL-prefix
   matching (M23.1) classes)
9. `docs/CAPABILITY_MATRIX.md` §7w
   (M22 shipped surface)
