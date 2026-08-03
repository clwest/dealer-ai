---
state: active
date: 2026-08-03
last_session_shipped: SESSION_176
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: shipped
milestone_11_status: shipped
milestone_12_status: shipped
milestone_13_status: shipped
milestone_14_status: shipped
milestone_15_status: shipped
milestone_16_status: shipped
milestone_17_status: shipped
milestone_18_status: shipped
milestone_19_status: shipped
milestone_20_status: shipped
milestone_21_status: shipped
milestone_22_status: shipped
milestone_23_status: in-progress
next_session: SESSION_177
next_milestone: 23
next_milestone_name: "BHPH Origination + Payment Intake"
next_increment: 2
next_increment_name: "M23.2 — Note origination UI + journey"
---

# Next session — SESSION_177 · Milestone 23 · Increment 2 (M23.2 — note origination UI + journey)

> **Milestone 23 · Increment 1 —
> Audit tooling fix — SHIPPED at
> SESSION_176.** Targeted three-
> change fix to `audit_operational_surface.py`
> reclassified two rows from
> `covered` to `defer-candidate-O2`:
> row 123 `admin-bhph-note-create`
> (as expected — confirms M23.2
> target) and row 139
> `admin-journal-entry-create`
> (**NEW genuine gap surfaced —
> JE creation UI is missing;
> M24 candidate evidence**).
> Coverage 110 → 108 (-2);
> backend-only 43 → 45 (+2).
> Root-cause reframe: HTTP-verb-
> agnostic URL-prefix matching
> — GET wrappers on pk-suffixed
> paths were being falsely
> claimed as consuming sibling
> POST endpoints via the
> querystring-variant candidate
> pattern. Fix orthogonally
> filters by verb match.
> Budget guard held — ~30-40
> min of active work, well
> under the ~2-hour §5.d
> guard.
>
> **Backend baseline unchanged
> at 4,766 pass.** Zero
> regressions verified via full
> test suite post-fix.
>
> **SESSION_177 opens M23.2 —
> first anchor UI.** BHPH note
> origination form + wrapper +
> journey. Journey-as-verifier
> per §5.f — no manual pre-
> verification.
>
> **DoD compliance satisfied by
> construction** for M23.2 —
> the new
> `bhph/note_origination.spec.ts`
> journey directly satisfies
> the M21.0 §5.f Option B
> amendment.

## First thing SESSION_177 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  should be the M23.1 close
  commit; `origin/main` still
  at the M22 durable-lessons
  head (M23 has not pushed).
- `python3 manage.py test
  dealer_ai` → **4,766 pass,
  1 skipped, 0 fail**.
- `cd frontend && npm test` →
  **180 pass**.
- `python3 manage.py check`
  clean.
- `python3 manage.py
  makemigrations --check
  --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc
  --noEmit` clean.
- `cd acceptance && npx tsc
  --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. Extend the BHPH seed with a vehicle fixture

Extend
`backend/dealer_ai/management/commands/seed_journey_bhph_collections_workflow.py`
with a **vehicle-for-origination
fixture**:

- Provision an available
  inventory vehicle (stable
  stock number tag —
  suggested
  `M23.2-BHPH-ORIG-VEH-1`;
  idempotent per M22.2's
  reversal-cleanup pattern
  precedent) that the M23.2
  origination journey targets.
- Distinct from any vehicle
  the existing collections
  journey depends on so the
  two workflows don't
  interfere.
- Any note created against
  this vehicle during a
  journey run gets deleted on
  the next seed invocation
  (analogous to M22.2's
  reversal cleanup) so the
  fixture stays reversible.

Add a backend test covering
idempotency + tenant scoping +
note cleanup behavior per M22.2
precedent.

### 3. Add the `createBhphNote` wrapper

Extend `frontend/src/lib/bhphApi.ts`:

```typescript
export interface CreateBhphNotePayload {
  vehicle_id: number;
  principal: string;         // Decimal-as-string per M12 convention
  apr: string;               // Decimal-as-string
  cadence: "weekly" | "biweekly" | "semimonthly" | "monthly";
  first_payment_date: string; // ISO 8601 date
  // Additional fields per the backend serializer (M12.1).
  // Verify shape against
  // backend/dealer_ai/views_bhph_notes.py before authoring.
}

export function createBhphNote(
  payload: CreateBhphNotePayload,
): Promise<BhphNoteDetailResponse> {
  return authPostJSON<BhphNoteDetailResponse>(
    "/admin/bhph-notes/",
    payload,
  );
}
```

Verify the payload shape against
`backend/dealer_ai/views_bhph_notes.py`
`admin_bhph_note_create` view + the
underlying `create_bhph_note`
service verb before authoring.

### 4. Author the `RecordBhphNoteForm` component

New file:
`frontend/src/components/bhph/RecordBhphNoteForm.tsx`.

Attributes:
- Vehicle picker (query
  available inventory via the
  existing inventory API or a
  simple `<select>` populated
  from the seed's known stock
  numbers if inventory API is
  not available).
- Principal input
  (currency-formatted).
- APR input (percentage-
  formatted).
- Cadence picker
  (`<Select>` with the four
  cadence values).
- First-payment-date picker
  (`<Input type="date">` or
  the shadcn date picker if
  used elsewhere in BHPH
  forms).
- Submit button (disabled
  until required fields
  filled).
- Error handling via
  `ApiError` + inline
  message per M21.2
  precedent.
- Optimistic list refresh via
  `onCreated` callback that
  the parent uses to
  invalidate the notes list.

Add Vitest coverage matching
the M21.2 `RecordPromiseToPayForm.test.tsx`
pattern.

### 5. Attach to DealerAiBhphPortfolio

Modify `DealerAiBhphPortfolio.tsx`
Notes card:
- Replace the empty-state
  message (currently
  documenting the POST curl
  workaround at line 193-194)
  with a persistent "Add note"
  CTA in the card header.
- CTA opens a shadcn `<Dialog>`
  containing `RecordBhphNoteForm`.
- On successful submit,
  refresh the notes list +
  close the dialog.

Add Vitest coverage for the
CTA + dialog integration.

### 6. Extend the accounting-style assertion helper

Extend
`acceptance/support/assertions/bhph.ts`
(existing helpers from M20.4 /
M21.2) with:

```typescript
export async function expectBhphNoteOriginated(
  request: APIRequestContext,
  vehicleId: number,
): Promise<BhphNoteDetail> {
  // Fetch notes list; find one attached to vehicle_id.
  // Assert:
  //   - note exists
  //   - note.principal / apr / cadence match seed defaults or form input
  //   - note carries the expected shape
}
```

Use the existing `listBhphNotes`
wrapper as reference for the
list fetch shape.

### 7. Author the note origination journey

New file:
`acceptance/journeys/bhph/note_origination.spec.ts`.

Walk:
1. BHPH collector (or owner
   — verify which persona
   fits the origination
   permission gate; likely
   sales_manager per M21.2
   precedent) navigates to
   `/dealer-ai-bhph-portfolio`.
2. Verify Notes card renders
   with existing seed notes.
3. Click "Add note" — dialog
   opens.
4. Fill vehicle picker with
   the seeded vehicle fixture.
5. Fill principal, APR,
   cadence, first-payment-
   date with test values.
6. Click submit — dialog
   closes + success message.
7. Verify new note appears in
   Notes card.
8. Business-outcome assertion
   via
   `expectBhphNoteOriginated(request, vehicleId)`.

Follow the fail-loud contract
per M20 §0 — journey test name
identifies the operational
workflow; failure messages
target the business outcome
that failed.

### 8. Concurrent §5.d small operator-surface gap fixes

If journey authoring reveals a
one-file trivial change is
needed to make the workflow
completable (missing testid,
broken link, label typo,
form validation bug), fix it
in-scope with a §0.a M23.2
amendment recording the fix.

If a larger gap surfaces
(missing service verb, new
UI structure, new form
component), DO NOT fix in-
scope. Document as future
candidate evidence in the
M23.2 handoff.

### 9. Verify journey passes locally

```bash
cd acceptance
rm -f ../backend/db.acceptance.sqlite3  # clean DB
npx playwright test bhph/note_origination.spec.ts --project=bhph_collector
```

If persona is different, adjust
`--project`. Then run full
suite:

```bash
npx playwright test
```

Expected: **14 passed (~19s)**
(6 setup + 8 journeys).

### 10. Ship the M23.2 handoff

- `docs/handoffs/SESSION_177_m23_inc2_note_origination.md`.
- Overwrite `00-START-NEXT-SESSION.md`
  with M23.3 priority.
- **Do NOT push** — M23 uses
  coordinated close-out push
  per M18.6 / M19.6 / M20.5 /
  M21.5 / M22.4 cadence at
  M23.4.

## Non-goals for SESSION_177

- ❌ Do NOT ship the payment
  intake UI (that's M23.3
  scope).
- ❌ Do NOT add new backend
  service verbs, DRF endpoints,
  tenancy carriers, migrations,
  permission classes, or
  frontend routes.
- ❌ Do NOT extend the audit
  script further — M23.1
  shipped the targeted fix.
- ❌ Do NOT manually verify
  the origination workflow
  before authoring the
  journey — journey-as-
  verifier per §5.f Option B.
- ❌ Do NOT ship sale-time
  origination trigger on
  `VehicleSalePage.tsx` —
  deferred per §3 deferral
  1.
- ❌ Do NOT ship JE creation
  UI even though M23.1
  surfaced the gap — out of
  M23 scope; recorded as
  M24 evidence.
- ❌ Do NOT split the BHPH
  seed into per-workflow
  seeds pre-emptively.
- ❌ Do NOT push M23.2
  commits.

## Baseline expected at close

- Backend baseline: 4,766 →
  **~4,770** (seed fixture
  idempotency tests).
- Frontend Vitest: 180 →
  **~187-192** (new component
  tests).
- Acceptance suite: **7 →
  8** (note origination
  journey added).
- Migrations `0001`–`0048`
  unchanged.
- Tenancy carriers 52
  unchanged.
- Permission classes 7
  unchanged (zero-drift streak
  intact).

## NEXT TASK

Start SESSION_177 with (a)
starting-state verification,
(b) extend the BHPH seed with
a vehicle-for-origination
fixture + backend idempotency
test, (c) add the
`createBhphNote` wrapper to
`bhphApi.ts` matching backend
serializer verbatim, (d) author
the `RecordBhphNoteForm`
component + Vitest coverage,
(e) attach to
`DealerAiBhphPortfolio.tsx`
Notes card as persistent CTA
replacing the empty-state
message, (f) extend the BHPH
assertion helper with
`expectBhphNoteOriginated`,
(g) author the
`bhph/note_origination.spec.ts`
journey, (h) apply small
operator-surface gap fixes
per §5.d if any surfaced, (i)
verify journey passes locally
on clean DB, (j) ship the
M23.2 handoff + refresh
`00-START-NEXT-SESSION.md`
for M23.3. Do NOT push.

---

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
   audit fix + JE-creation-UI
   finding)
6. `docs/handoffs/SESSION_176_m23_inc1_audit_fix.md`
   (M23.1 close — audit
   correction root-cause
   reframe + shipped changes
   + JE-creation-UI evidence
   for M24)
7. `docs/handoffs/SESSION_175_m23_inc0_planning.md`
   (M23.0 close — empirical
   discovery record + §5
   decisions)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact — now
   authoritative for BHPH
   post-M23.1 fix)
9. `frontend/src/pages/DealerAiBhphPortfolio.tsx`
   (M23.2 attach target;
   line 193-194 empty-state
   message replaced by CTA)
10. `frontend/src/components/bhph/RecordPromiseToPayForm.tsx`
    (M21.2 form pattern
    reference for M23.2
    authoring)
11. `docs/CAPABILITY_MATRIX.md` §7w
    (M22 shipped surface)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_176 — Milestone 23.1 audit fix shipped)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,766 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 180 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace
  (local):** Playwright 1.49 +
  TS 5.6 operational; **seven
  journeys** passing end-to-end
  on clean DB.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`.
  Last verified green: run
  `30831196864` (M22 durable-
  lessons carry-forward push,
  2m3s). M23 has not pushed
  yet — coordinated push at
  M23.4.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  **M22**. M23 in-progress
  (M23.0 planning + M23.1
  audit fix shipped; M23.2
  next at SESSION_177).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all
  M1–M22 packages unchanged.
  M23 adds zero service verbs.
- **Frontend surfaces:** all
  M1–M22 components unchanged.
  M23.2 will add
  `RecordBhphNoteForm`; M23.3
  will add
  `RecordBhphPaymentForm`.
- **Tenancy carriers:** **52**.
- **Permission classes:** **7
  actual** — zero-drift streak
  **twenty-two consecutive
  milestones** (M10 → M22).
  Target at M23.4 close: 23.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 23 status:** IN-
  PROGRESS. M23.0 planning +
  M23.1 audit fix shipped.
  M23.2 first anchor UI next.
- **Audit tooling:**
  authoritative for BHPH +
  accounting endpoints post-
  M23.1 fix. Coverage
  **108/153**. Backend-only
  **45**. Two false-positive
  classes now closed: variable-
  first URL assembly (M22.1)
  + HTTP-verb-agnostic URL-
  prefix matching (M23.1).
- **Audit artifact:** current at
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`.
  Trusted source material for
  M23.2+ journey authoring +
  future OSC candidate
  selection.
- **New M24 evidence-based
  candidate surfaced at
  M23.1:** JE creation UI
  (row 139
  `admin-journal-entry-create`
  reclassified as backend-
  only). Recorded in memo
  §0.a M23.1 amendment + this
  handoff for the M23.4
  retrospective §9 M24
  discussion.
- **Planning-time streak:** **89
  as-recommended M5.1 → M23.0**
  across fourteen consecutive
  milestones (M10 → M23).
- **DoD amendment (M21.0 §5.f
  Option B):** M23 satisfies
  by construction — M23.2 +
  M23.3 each add a Playwright
  operational journey. M23.2
  will add
  `bhph/note_origination.spec.ts`;
  M23.3 will add
  `bhph/payment_intake.spec.ts`.
- **M23 governing contract
  (inherited from M21
  Candidate O UI-creation
  shape):** (1) maps to
  shipped backend + missing
  frontend; (2) closes a
  missing operator-facing UI;
  (3) adds or extends a
  Playwright operational
  journey; (4) not generic UX
  polish.
- **M23 remaining increments:**
  M23.2 note origination UI +
  journey (first anchor,
  SESSION_177); M23.3 payment
  intake UI + journey (second
  anchor, SESSION_178); M23.4
  close-out (SESSION_179).
