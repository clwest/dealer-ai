---
state: active
date: 2026-08-03
last_session_shipped: SESSION_180
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
milestone_23_status: shipped
milestone_24_status: in-progress
next_session: SESSION_181
next_milestone: 24
next_milestone_name: "Sales Operational Entry"
next_increment: 1
next_increment_name: "M24.1 — Shared intake substrate + walk-in UI + walk-in journey"
---

# Next session — SESSION_181 · Milestone 24 · Increment 1 (M24.1 — shared intake substrate + walk-in UI + walk-in journey)

> **Milestone 24 — Sales
> Operational Entry — PLANNING
> LOCKED at SESSION_180.** Full
> memo expansion + eight §5 load-
> bearing decisions resolved.
> §5.a + §5.c + §5.e + §5.f +
> §5.g + §5.h confirmed as-
> recommended; **§5.b + §5.d
> redirected before lock** on
> the webhook operator-UI
> posture (webhook is a system-
> to-system integration
> mechanism, not an operator-
> created lead source).
>
> **Planning-time as-recommended
> streak: RESET TO 0** at
> SESSION_180. Historical run
> preserved for the record: 89
> across fourteen consecutive
> milestones (M10 → M23).
>
> **M24 shape:** 5-to-6
> evidence-sized increments.
> M24.0 planning (shipped) →
> M24.1 shared substrate + walk-
> in (this session) → M24.2
> phone → M24.3 referral →
> M24.4 webhook integration
> journey → M24.5 close-out
> (with M24.4 collapse into
> M24.5 possible).
>
> **M24.1 ships the shared
> `<LeadIntakeForm>` component
> that M24.2 + M24.3 inherit
> via sibling-pattern
> discipline.** First anchor UI
> — get the shared substrate
> right so subsequent increments
> are small.
>
> **Zero-drift permission-class
> streak extends 22 → 23 at M23
> close; M24 target extends to
> 24** — all four intake
> endpoints reuse
> `IsSalesManagerOrOwnerAtActiveDealership`.

## First thing SESSION_181 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  should be the SESSION_180
  M24.0 planning commit;
  `origin/main` still at
  `6dfdb5c` (M23 close-out,
  no push at M24.0 per M24
  non-goals).
- `python3 manage.py test dealer_ai`
  → **4,780 pass, 1 skipped,
  0 fail**.
- `cd frontend && npm test` →
  **193 pass**.
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

### 2. Verify wrapper + endpoint shape one more time

Before authoring UI, re-verify
that `createWalkInLead` in
`salesApi.ts` matches
`admin-lead-walk-in-create`
serializer exactly (should be
unchanged since M11.6). Grep-
verify no `<LeadIntakeForm>`
component exists yet in
`frontend/src/components/sales/`.

### 3. Ship `<LeadIntakeForm>` shared component

Per MILESTONE_24_PLANNING.md
§5.b + §7 M24.1:

- Create
  `frontend/src/components/sales/LeadIntakeForm.tsx`.
- Nine base fields per
  `_BaseIntakeSerializer`
  (`name`, `phone`, `email`,
  `notes`, `target_monthly_payment`,
  `down_payment`, `trade_in`,
  `credit_range`, `urgency`).
- Parameterized by `channel:
  LeadChannel` prop; on
  submit, dispatches to the
  correct wrapper
  (`createWalkInLead` /
  `createPhoneLead` /
  `createReferralLead`) based
  on `channel`.
- Submit + error handling +
  loading state.
- Uses shadcn primitives (Form,
  Input, Button, Textarea,
  Select) matching M23.2 /
  M23.3 form patterns.
- Vitest coverage: ~5–7 tests.

### 4. Attach `+ Walk-in` Dialog CTA to DealerAiSalesLeads

- Import `<LeadIntakeForm>` +
  shadcn `Dialog`.
- Add `+ Walk-in` button as
  page-header CTA or table-
  header action (attachment
  point finalized during
  authoring per M17 §6 lesson
  6 in-place-page-extension
  posture).
- On submit success: close
  Dialog + `navigate(\`/dealer-ai/sales/leads/${lead.id}\`)`.

### 5. Ship the seed command

Per §5.e Option A:

- `backend/dealer_ai/management/commands/seed_journey_sales_operational_entry.py`.
- Provisions salesperson user +
  role + tenant + target
  vehicle (for walk-in test
  drive downstream handoff).
- Session-safe pattern (guard
  `set_password` call per
  M23.2 durable memory).
- Lead cleanup on re-
  invocation per M22.2 /
  M23.2 pattern.
- Backend test: optional
  seed-fixture correctness
  test (~1 test).

### 6. Ship the walk-in Playwright journey

Per §5.c + §5.d Option B
walk-in row:

- `acceptance/journeys/sales_manager/walk_in_intake.spec.ts`:
  1. Invoke seed via `invokeSeed('sales_operational_entry')`.
  2. Login as salesperson via
     `loginAs('salesperson')`.
  3. Navigate to
     `/dealer-ai/sales/leads`.
  4. Click `+ Walk-in` CTA.
  5. Fill form with test
     customer details.
  6. Submit.
  7. Assert redirect to
     `/dealer-ai/sales/leads/<id>`.
  8. Assign salesperson via
     existing UI.
  9. Schedule test drive via
     existing UI (walk-in
     scenario — customer
     physically present).
  10. Assert test drive
      appears on lead detail.
- New assertion helper at
  `acceptance/support/assertions/sales.ts`
  IF patterns repeat (else
  defer to M24.2).

### 7. Small operator-surface gap fixes (in-scope per §5.d)

If authoring the journey
surfaces small operator-
surface gaps (missing testid,
wrong redirect target, form
validation friction): fix in-
scope per M23 §5.d durable
posture. Large gaps: document
as retrospective §9 evidence
for M25 planning.

### 8. Ship the M24.1 handoff

- `docs/handoffs/SESSION_181_m24_inc1_walk_in.md`
  following M23.2's SESSION_177
  shape.
- **Do NOT push** — coordinated
  push at M24.5 per M24 non-
  goals.

### 9. Refresh 00-START-NEXT-SESSION.md for M24.2

Point at SESSION_182 M24.2
phone specialization + journey.

## Non-goals for SESSION_181

- ❌ Do NOT ship a
  `<WebhookIntakeForm>` or a
  `+ Webhook` operator CTA
  per §5.b + §5.d.
- ❌ Do NOT create a test-only
  backend endpoint or fake
  operator workflow per §5.d.
- ❌ Do NOT add new backend
  service verbs, DRF
  endpoints, tenancy
  carriers, migrations,
  permission classes, or
  frontend routes.
- ❌ Do NOT push individual
  M24 commits — coordinated
  close-out push at M24.5.
- ❌ Do NOT force-scope
  phone / referral / webhook
  work into M24.1 — sibling-
  pattern discipline; each
  channel lands in its own
  increment.
- ❌ Do NOT skip the seed
  session-invalidation
  guarding — M23.2 durable
  memory applies from the
  start.
- ❌ Do NOT ship
  `<LeadIntakeForm>` without
  Vitest coverage — component
  binding contract per M11
  practice.

## Baseline expected at M24.1 close

- Backend: 4,780 → **~4,781**
  (possibly one seed-fixture
  test).
- Frontend Vitest: 193 →
  **~198–200**.
- Acceptance suite: 9 →
  **10**.
- Migrations `0001`–`0048`
  (unchanged).
- Tenancy carriers 52
  (unchanged).
- DRF admin surface 113
  (unchanged).
- Frontend operator routes
  20 (unchanged).
- Permission classes 7
  (unchanged).
- Celery-beat task families
  10 (unchanged).

## NEXT TASK

Start SESSION_181 with (a)
starting-state verification,
(b) wrapper + endpoint shape
re-verification, (c)
`<LeadIntakeForm>` shared
component + Vitest coverage,
(d) `+ Walk-in` Dialog CTA
attachment on
`DealerAiSalesLeads` with
post-create redirect, (e)
new
`seed_journey_sales_operational_entry`
seed command with session-
safe + cleanup patterns, (f)
new `walk_in_intake.spec.ts`
Playwright journey exercising
intake + assign + schedule
test drive, (g) small in-
scope §5.d fixes if
surfaced, (h) ship
`SESSION_181_m24_inc1_walk_in.md`
handoff, (i) refresh
`00-START-NEXT-SESSION.md`
for M24.2.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_24_PLANNING.md`
   (planning locked at
   SESSION_180)
6. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (M23 governing contract
   inherited by M24)
7. `docs/roadmap/MILESTONE_23_RETROSPECTIVE.md`
   §8 + §9
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (authoritative for sales
   intake at M24.0)
9. `docs/CAPABILITY_MATRIX.md`
   §7x (M23 shipped surface)
10. `docs/handoffs/SESSION_180_m24_inc0_planning.md`
    (M24 planning-open
    findings + redirect
    record)

Narrative docs are claims.
Rules + research + code are
facts.

---

## Operational state (post-SESSION_180 — Milestone 24 planning LOCKED, implementation PENDING)

- **Backend (local):** Django
  on `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,780 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT
  active.
- **Frontend (local):** Vite
  on `:5173`. `tsc --noEmit` +
  `vite build` clean.
  **Vitest baseline: 193
  pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace
  (local):** Playwright 1.49
  + TS 5.6 operational; **nine
  journeys** passing end-to-
  end on clean DB. Full dry-
  run baseline: **15 passed
  (~20.5s)** (6 setup + 9
  journeys).
- **Acceptance (CI):** live
  on
  `.github/workflows/acceptance.yml`.
  M23 close-out CI run
  `30840071050` verified
  **success** in 2m20s.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1
  → **M23**. **M24
  planning locked**; M24
  implementation begins at
  M24.1 (SESSION_181).
- **DRF admin surface:**
  **113** endpoints (M24 adds
  zero).
- **Frontend operator
  routes:** **20** (M24 adds
  zero).
- **Public endpoints:** +1
  M6.5 showroom.
- **Service surface:** all
  M1–M23 packages unchanged.
  M24 will add zero service
  verbs.
- **Frontend surfaces (M24
  target):** two new
  components
  (`<LeadIntakeForm>` +
  `<ReferralLeadFormExtras>`)
  in
  `frontend/src/components/sales/`.
  Three Dialog CTAs on
  `DealerAiSalesLeads.tsx`
  (`+ Walk-in`, `+ Phone`,
  `+ Referral`). No new
  routes.
- **Tenancy carriers:** **52**
  (M24 adds zero).
- **Permission classes:** **7
  actual** — zero-drift
  streak **twenty-three
  consecutive milestones**
  (M10 → M23). M24 target:
  extend to twenty-four —
  all four intake endpoints
  reuse
  `IsSalesManagerOrOwnerAtActiveDealership`.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 24 status:**
  planning LOCKED at
  SESSION_180 M24.0;
  implementation begins at
  SESSION_181 M24.1.
- **Sales intake gap
  addressed at M24 target:**
  Three operator-created
  intake paths (walk-in,
  phone, referral) get UI-
  native intake via shared
  `<LeadIntakeForm>` +
  `<ReferralLeadFormExtras>`.
  One externally-created
  intake path (webhook)
  gets an integration-to-
  operator Playwright
  journey via the shipped
  `generic` adapter.
- **Audit tooling:**
  authoritative for BHPH +
  accounting endpoints
  post-M23.1 fix.
  Regenerated at M24.0 open
  (153 endpoints, 110
  covered, 43 backend-only).
- **§9 evidence for M25:**
  will emerge from M24
  journey-authoring
  evidence per §5.f
  journey-as-verifier
  posture.
- **Planning-time streak:**
  **RESET TO 0** at
  SESSION_180 M24.0.
  Historical run: 89 across
  fourteen consecutive
  milestones (M10 → M23).
  Preserved for the record;
  not extended. §5.b + §5.d
  webhook redirect
  recorded honestly.
- **DoD amendment (M21.0
  §5.f Option B):** M24
  ships four new Playwright
  operational journeys —
  intrinsically compliant.
- **Governing contract:** M21
  Candidate O UI-creation
  shape (also used by M23)
  inherited by M24 for
  three operator channels;
  webhook channel uses a
  modified integration-to-
  operator variant per
  §5.d.
