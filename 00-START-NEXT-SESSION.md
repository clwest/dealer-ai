---
state: active
date: 2026-08-03
last_session_shipped: SESSION_177
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
next_session: SESSION_178
next_milestone: 23
next_milestone_name: "BHPH Origination + Payment Intake"
next_increment: 3
next_increment_name: "M23.3 — Payment intake UI + journey"
---

# Next session — SESSION_178 · Milestone 23 · Increment 3 (M23.3 — payment intake UI + journey)

> **Milestone 23 · Increment 2 —
> Note origination UI + journey —
> SHIPPED at SESSION_177.** New
> `createBhphNote` wrapper +
> `RecordBhphNoteForm` +
> DealerAiBhphPortfolio CTA/Dialog
> + seed extension +
> `expectBhphNoteOriginated`
> helper + `bhph/note_origination.spec.ts`
> journey. Backend baseline
> **4,766 → 4,773 (+7)** seed
> tests. Frontend Vitest **180 →
> 187 (+7)** form tests.
> Acceptance suite **7 → 8**
> journeys. Full clean-DB dry-
> run: **14 passed @ 18.8s**.
>
> **§5.d gap fix landed in-
> scope:** session-invalidation
> bug in `_provision_collector`
> (unconditional `set_password`
> broke Django session hashes
> when journey re-invoked seed
> mid-suite) fixed by wrapping
> in `if created:`. One-file
> trivial change per §5.d
> Option B in-scope threshold.
> Pre-existing latent bug that
> only surfaced under M23.2's
> new journey pattern.
>
> **SESSION_178 opens M23.3 —
> second anchor UI.** BHPH
> payment intake form +
> wrapper + journey. Same
> shape as M23.2 with the
> `RecordBhphNoteForm` +
> `note_origination.spec.ts`
> patterns as reference.
>
> **DoD compliance satisfied
> by construction** for M23.3
> — the new
> `bhph/payment_intake.spec.ts`
> journey directly satisfies
> the M21.0 §5.f Option B
> amendment.

## First thing SESSION_178 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  should be the M23.2 close
  commit; `origin/main` still
  at the M22 durable-lessons
  head (M23 has not pushed).
- `python3 manage.py test dealer_ai`
  → **4,773 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **187 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc
  --noEmit` clean.
- `cd acceptance && npx tsc
  --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. Inspect the backend payment-intake surface

Read
`backend/dealer_ai/views_bhph_payments.py`
`admin_bhph_payment_create` view +
serializer to confirm the payload
shape. Expect fields something
like: `amount` (decimal),
`method` (enum from
BHPH_PAYMENT_METHOD choices),
`paid_at` (datetime), optional
`memo`. Verify against actual
code before authoring — the
M22 lesson about "verify prior
recommendations" applies here.

### 3. Extend the BHPH seed with a fresh-note-with-balance fixture

Extend
`backend/dealer_ai/management/commands/seed_journey_bhph_collections_workflow.py`
with a **fresh-note-with-balance
fixture**:

- Provision a distinct
  Sale + BhphNote pair (stable
  stock number — suggested
  `M23-BHPH-PAY`; distinct from
  M20.4's `M20-BHPH-ACCEPT` and
  M23.2's `M23-BHPH-ORIG`)
  where the note has non-zero
  outstanding balance and NO
  payments yet.
- Payment cleanup on re-
  invocation: any BhphPayment
  linked to this fixture note
  in a previous journey run
  gets deleted. Matches M22.2's
  reversal-cleanup + M23.2's
  note-cleanup patterns.
- SUCCESS message extended with
  `m23_pay_note_pk=<N>` so the
  journey can parse it via
  `invokeSeed()` stdout.
- Add backend test cases (~5)
  covering fixture provisioning,
  no-payment invariant,
  idempotency, payment cleanup,
  reset.

### 4. Add the `createBhphPayment` wrapper

Extend `frontend/src/lib/bhphApi.ts`:

```typescript
export interface CreateBhphPaymentPayload {
  amount: string;
  method: BhphPaymentMethod;
  paid_at: string;  // ISO 8601 datetime
  memo?: string;
}

export interface BhphPaymentCreateResponse {
  bhph_payment: BhphPaymentProjection;
}

export function createBhphPayment(
  notePk: number,
  payload: CreateBhphPaymentPayload,
): Promise<BhphPaymentCreateResponse> {
  return authPostJSON<BhphPaymentCreateResponse>(
    `/admin/bhph-notes/${notePk}/payments/`,
    payload,
  );
}
```

Verify shape against the backend
serializer before authoring.

### 5. Author the `RecordBhphPaymentForm` component

New file:
`frontend/src/components/bhph/RecordBhphPaymentForm.tsx`.

Attributes matching backend
serializer:
- Amount input
  (currency-formatted).
- Payment method picker
  (`<select>` with the M12
  vocab: cash / check / money
  order / ach / card per
  `BHPH_PAYMENT_METHOD_*` in
  models.py).
- Paid-at datetime picker
  (`<Input type="datetime-local">`).
- Memo textarea (optional).
- Submit button (disabled
  until required fields
  filled).
- Error handling via
  `humanizeError` for 400 /
  404 / 409.
- Optimistic list refresh
  via `onRecorded` callback.

Add Vitest coverage matching
the M23.2
`RecordBhphNoteForm.test.tsx`
pattern (~7 tests).

**Remember** the M23.2 pattern:
NO `required` on inputs, NO
browser-level HTML5 validation
(`min` / `max`) that would
short-circuit onSubmit. Rely on
JS validation.

### 6. Attach to DealerAiBhphNoteDetail

Modify
`frontend/src/pages/DealerAiBhphNoteDetail.tsx`
to add a new Payments card
matching the existing
Promises/Contacts/Repossessions
sibling pattern:
- Card header with title +
  "Record payment" CTA.
- Card content with existing
  payment list (already
  consumed via
  `listBhphPayments`).
- CTA opens a shadcn Dialog
  containing
  `RecordBhphPaymentForm`.
- On successful submit,
  refresh the payment list +
  close the dialog.

### 7. Extend the BHPH assertion helper

Extend
`acceptance/support/assertions/bhph.ts`
with
`expectBhphPaymentRecorded(request, noteId, expected)`
— asserts:
- Payment exists on the note
  with matching amount +
  method.
- Outstanding balance
  decreased by the payment
  amount (verify against
  `principal_financed` or
  the note's balance field
  depending on what M12
  exposes).

### 8. Author the payment intake journey

New file:
`acceptance/journeys/bhph/payment_intake.spec.ts`.

Walk:
1. Parse the M23.3 fixture
   note pk from seed stdout
   via `invokeSeed()`.
2. `bhph_collector` persona
   navigates to
   `/dealer-ai-bhph/notes/<pk>`
   for the fixture note.
3. Verify Payments card
   renders (empty).
4. Click "Record payment" —
   dialog opens.
5. Fill amount, method,
   paid_at, memo.
6. Submit — dialog closes +
   payment appears in
   Payments card.
7. Business-outcome assertion
   via
   `expectBhphPaymentRecorded`.

Uses the SAME
`invokeSeed()` + stdout-
parsing pattern established
in M23.2's journey.

### 9. Verify journey passes locally on clean DB

```bash
rm -f backend/db.acceptance.sqlite3
cd acceptance
npx playwright test bhph/payment_intake.spec.ts --project=bhph_collector
```

Then full-suite:

```bash
rm -f backend/db.acceptance.sqlite3
npx playwright test
```

Expected: **15 passed (~19s)**
(6 setup + 9 journeys).

### 10. Ship the M23.3 handoff

- `docs/handoffs/SESSION_178_m23_inc3_payment_intake.md`.
- Overwrite `00-START-NEXT-SESSION.md`
  with M23.4 priority.
- **Do NOT push** — M23 uses
  coordinated close-out push
  per M18.6 / M19.6 / M20.5 /
  M21.5 / M22.4 cadence at
  M23.4.

## Non-goals for SESSION_178

- ❌ Do NOT add new backend
  service verbs, DRF endpoints,
  tenancy carriers, migrations,
  permission classes, or
  frontend routes.
- ❌ Do NOT extend the audit
  script further.
- ❌ Do NOT manually verify
  the payment workflow before
  authoring the journey —
  journey-as-verifier per §5.f
  Option B.
- ❌ Do NOT ship JE creation UI
  even though M23.1 surfaced
  the gap — out of M23 scope.
- ❌ Do NOT ship the sale
  picker UI / deep-link — M23
  non-goal per §3 deferral 1.
- ❌ Do NOT split the BHPH
  seed into per-workflow
  seeds.
- ❌ Do NOT push M23.3
  commits.

## Baseline expected at close

- Backend baseline: 4,773 →
  **~4,777** (seed fixture
  + payment cleanup tests).
- Frontend Vitest: 187 →
  **~194-198** (new component
  tests).
- Acceptance suite: **8 →
  9** (payment intake
  journey added).
- Migrations `0001`–`0048`
  unchanged.
- Tenancy carriers 52
  unchanged.
- Permission classes 7
  unchanged (zero-drift
  streak intact).

## NEXT TASK

Start SESSION_178 with (a)
starting-state verification,
(b) inspect the backend
payment-intake serializer +
service verb, (c) extend the
BHPH seed with a fresh-note-
with-balance fixture + payment
cleanup + backend tests, (d)
add `createBhphPayment` wrapper
to `bhphApi.ts`, (e) author
the `RecordBhphPaymentForm`
component + Vitest coverage
(remember: no HTML5 validation
attrs that short-circuit
onSubmit), (f) attach to
`DealerAiBhphNoteDetail.tsx`
as a new Payments card
matching sibling pattern, (g)
extend the BHPH assertion
helper with
`expectBhphPaymentRecorded`,
(h) author the
`bhph/payment_intake.spec.ts`
journey using the M23.2
invokeSeed + stdout-parsing
pattern, (i) verify journey
passes locally on clean DB,
(j) ship the M23.3 handoff +
refresh
`00-START-NEXT-SESSION.md`
for M23.4. Do NOT push.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M22 shipped section landed
   at M22.4)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (active memo — §0.a M23.2
   amendment records shipped
   UI + seed session-fix)
6. `docs/handoffs/SESSION_177_m23_inc2_note_origination.md`
   (M23.2 close — origination
   pattern reference for
   M23.3)
7. `docs/handoffs/SESSION_176_m23_inc1_audit_fix.md`
   (M23.1 close)
8. `docs/handoffs/SESSION_175_m23_inc0_planning.md`
   (M23.0 close)
9. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact — trustworthy
   for BHPH post-M23.1)
10. `frontend/src/components/bhph/RecordBhphNoteForm.tsx`
    (M23.2 form pattern
    reference for M23.3
    `RecordBhphPaymentForm`)
11. `acceptance/journeys/bhph/note_origination.spec.ts`
    (M23.2 journey pattern
    reference for M23.3
    `payment_intake.spec.ts`
    — especially the
    invokeSeed + stdout-parsing
    pattern)
12. `docs/CAPABILITY_MATRIX.md` §7w
    (M22 shipped surface)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_177 — Milestone 23.2 origination UI shipped)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,773 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 187 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace
  (local):** Playwright 1.49 +
  TS 5.6 operational; **eight
  journeys** passing end-to-end
  on clean DB. Full dry-run
  baseline: **14 passed
  (~18.8s)**. M23.2 added
  `bhph/note_origination.spec.ts`.
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
  audit fix + M23.2
  origination UI shipped;
  M23.3 payment intake UI
  next at SESSION_178).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all
  M1–M22 packages unchanged.
  M23 adds zero service verbs.
- **Frontend surfaces:** M23.2
  added `RecordBhphNoteForm`
  attached to
  `DealerAiBhphPortfolio`
  Notes card as CTA + Dialog.
  M23.3 will add
  `RecordBhphPaymentForm`
  attached to
  `DealerAiBhphNoteDetail`.
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
  M23.1 audit fix + M23.2
  origination UI shipped.
  M23.3 payment intake UI
  next.
- **Audit tooling:**
  authoritative for BHPH +
  accounting endpoints
  post-M23.1 fix. Coverage
  **108/153**. Backend-only
  **45**.
- **M23.2 seed fix:**
  `_provision_collector` no
  longer resets password on
  every invocation.
  Preserves Django session
  hashes when journeys re-
  invoke seeds mid-suite.
  Pattern generalizes to
  other seeds that do the
  same — flagged for future
  work.
- **M23.2 sale picker UX
  deferral:** manual sale_id
  input — no admin sale-list
  endpoint ships. Documented
  in M23 §3 deferral 1 for
  M24+ consideration.
- **Planning-time streak:**
  **89 as-recommended M5.1 →
  M23.0** across fourteen
  consecutive milestones (M10
  → M23).
- **DoD amendment (M21.0 §5.f
  Option B):** M23 satisfies
  by construction — M23.2
  added
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
  journey; (4) not generic
  UX polish.
- **M23 remaining increments:**
  M23.3 payment intake UI +
  journey (second anchor,
  SESSION_178); M23.4 close-
  out (SESSION_179).
- **M23 §9 evidence
  accumulating:** JE creation
  UI (M23.1 finding), sale
  picker UX (M23.2 finding),
  session-invalidation seed
  pattern generalization
  (M23.2 finding), route URL
  discovery friction (M23.2
  finding). All feed the
  M23.4 retrospective §9 M24
  candidate discussion.
