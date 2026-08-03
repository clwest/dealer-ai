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
next_increment_name: "M24.1 — Shared intake substrate + walk-in UI + LeadDetailModal wire-in + walk-in journey"
---

# Next session — SESSION_181 · Milestone 24 · Increment 1 (M24.1 — shared intake substrate + walk-in UI + LeadDetailModal wire-in + walk-in journey)

> **Milestone 24 — Sales
> Operational Entry — PLANNING
> LOCKED at SESSION_180 with
> M24.1-open corrections
> documented in the memo
> preamble.** Two planning
> corrections landed on the
> same milestone:
>
> 1. **SESSION_180 M24.0
>    open:** §5.b + §5.d
>    redirected before lock on
>    the webhook operator-UI
>    posture. Streak reset
>    89 → 0.
> 2. **SESSION_181 M24.1
>    open:** §5.b + §5.d +
>    §5.h revised for the
>    downstream-verb UI
>    substrate gap (route path
>    correction + wire
>    `LeadDetailModal` into
>    `DealerAiSalesLeads` as
>    small in-scope fix +
>    defer test-drive UI +
>    referrer display +
>    platform display to
>    M25). Streak stays at 0
>    (not further reset;
>    not extended).
>
> **M24 shape:** 5-to-6
> evidence-sized increments.
> M24.0 planning (shipped) →
> M24.1 shared substrate +
> walk-in + modal wire-in
> (this session) → M24.2
> phone + cadence → M24.3
> referral → M24.4 webhook
> integration journey →
> M24.5 close-out (with
> M24.4 collapse into M24.5
> possible).
>
> **M24.1 ships the shared
> `<LeadIntakeForm>` +
> walk-in Dialog CTA +
> `LeadDetailModal` +
> `AssignmentDropdown` wire-
> in.** First anchor UI —
> get the shared substrate
> right so subsequent
> increments are small.
>
> **Zero-drift permission-
> class streak M24 target
> extends to 24** — all four
> intake endpoints reuse
> `IsSalesManagerOrOwnerAtActiveDealership`.

## First thing SESSION_181 must do

### 1. Verify starting state

Verified at SESSION_181
M24.1 open (2026-08-03):

- `git status` — clean.
- `git log --oneline -6` —
  top is `a52a56e` (M24.0
  close); `origin/main` at
  `6dfdb5c` (M23 close-out,
  1 commit behind).
- `python3 manage.py test
  dealer_ai` → **4,780
  pass, 1 skipped, 0 fail
  (163s)**.
- `cd frontend && npm test`
  → **193 pass**.
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
- `redis-cli ping` →
  `PONG`.

**M24.1 re-runs these
before starting** to
confirm no drift since
the M24.0 planning
correction commit.

### 2. Verify wrapper + endpoint shape one more time

Before authoring UI, re-
verify that
`createWalkInLead` in
`salesApi.ts` matches
`admin-lead-walk-in-create`
serializer exactly.
Verified at SESSION_181
M24.1 open (unchanged
since M11.6). Grep-verify
no `<LeadIntakeForm>`
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
- Parameterized by
  `channel: "walk_in" |
  "phone" | "referral"`
  prop; on submit,
  dispatches to the
  correct wrapper based
  on `channel`.
- Submit + error handling
  + loading state.
- Uses shadcn primitives
  matching M23.2 / M23.3
  form patterns (see
  `frontend/src/components/bhph/RecordBhphNoteForm.tsx`
  as sibling).
- Vitest coverage: ~5–7
  tests.

### 4. Wire LeadDetailModal + AssignmentDropdown into DealerAiSalesLeads

Small in-scope extension
per §5.b (M24.1-open
correction). ~30 lines:

- Import `LeadDetailModal`
  from
  `@/components/LeadDetailModal`.
- Add `useState<number |
  null>(null)` for
  `selectedLeadId`.
- Add row-click handler
  on each `<tr>`:
  `setSelectedLeadId(lead.id)`.
- Render
  `<LeadDetailModal
  leadId={selectedLeadId}
  onClose={() =>
  setSelectedLeadId(null)}
  onHandoffComplete={()
  => void load()} />`.
- Assignment reaches via
  `AssignmentDropdown`
  inside modal (already
  wired).

### 5. Attach `+ Walk-in` Dialog CTA to DealerAiSalesLeads

- Import `<LeadIntakeForm>`
  + shadcn `Dialog`.
- Add `+ Walk-in` button
  as page-header CTA or
  table-header action.
- On submit success:
  close intake Dialog +
  `setSelectedLeadId(lead.id)`
  (opens the newly
  created lead's detail
  modal).
- **No `navigate()` call
  needed.** Salesperson
  stays on
  `/dealer-ai-sales/leads`;
  modal opens on same
  page.

### 6. Ship the seed command

Per §5.e Option A:

- `backend/dealer_ai/management/commands/seed_journey_sales_operational_entry.py`.
- Provisions salesperson
  user + role + tenant +
  referring-customer lead
  (for M24.3 referral
  attribution).
- Session-safe pattern
  (guard `set_password`
  call per M23.2 durable
  memory).
- Lead cleanup on re-
  invocation per M22.2 /
  M23.2 pattern.
- Backend test: optional
  seed-fixture correctness
  test (~1 test).

### 7. Ship the walk-in Playwright journey

Per §5.c + §5.d Option C
walk-in row:

- `acceptance/journeys/sales_manager/walk_in_intake.spec.ts`:
  1. Invoke seed via
     `invokeSeed('sales_operational_entry')`.
  2. Login as salesperson
     via
     `loginAs('salesperson')`.
  3. Navigate to
     `/dealer-ai-sales/leads`.
  4. Click `+ Walk-in`
     CTA.
  5. Fill form with test
     customer details.
  6. Submit.
  7. Assert
     `LeadDetailModal`
     opens for the newly
     created lead (check
     modal header shows
     "Lead #N" with the
     new id).
  8. Assign salesperson
     via
     `AssignmentDropdown`
     in modal header.
  9. Close modal.
  10. Assert list row for
      new lead shows
      `channel="walk_in"`.
  11. Reopen modal via
      row click.
  12. Assert assignment
      persists.
- New assertion helper
  at
  `acceptance/support/assertions/sales.ts`
  IF patterns repeat
  (else defer to M24.2).

### 8. Small operator-surface gap fixes (in-scope per §5.d)

If authoring the journey
surfaces small gaps: fix
in-scope per M23 §5.d
durable posture. Large
gaps: document as
retrospective §9
evidence for M25
planning.

### 9. Ship the M24.1 handoff

- `docs/handoffs/SESSION_181_m24_inc1_walk_in.md`
  following M23.2's
  SESSION_177 shape.
- **Do NOT push** —
  coordinated push at
  M24.5 per M24 non-
  goals.

### 10. Refresh 00-START-NEXT-SESSION.md for M24.2

Point at SESSION_182
M24.2 phone specialization
+ cadence journey.

## Non-goals for SESSION_181

- ❌ Do NOT ship a
  `<WebhookIntakeForm>`
  or a `+ Webhook`
  operator CTA per §5.b
  + §5.d.
- ❌ Do NOT ship a
  `<RecordTestDriveForm>`
  component. Deferred to
  M25 per §3 deferral 12.
- ❌ Do NOT add
  `referrer_id` or
  `platform` display to
  `LeadDetailModal`.
  Deferred to M25 per §3
  deferrals 13 + 14.
- ❌ Do NOT create a
  test-only backend
  endpoint or fake
  operator workflow per
  §5.d.
- ❌ Do NOT redirect
  post-create to a new
  route. Modal-on-same-
  page per M24.1-open
  correction.
- ❌ Do NOT add new
  backend service verbs,
  DRF endpoints,
  tenancy carriers,
  migrations, permission
  classes, or frontend
  routes.
- ❌ Do NOT push
  individual M24
  commits — coordinated
  close-out push at
  M24.5.
- ❌ Do NOT force-scope
  phone / referral /
  webhook work into
  M24.1 — sibling-
  pattern discipline;
  each channel lands in
  its own increment.
- ❌ Do NOT skip the
  seed session-
  invalidation guarding
  — M23.2 durable
  memory applies from
  the start.
- ❌ Do NOT ship
  `<LeadIntakeForm>`
  without Vitest
  coverage — component
  binding contract per
  M11 practice.

## Baseline expected at M24.1 close

- Backend: 4,780 →
  **~4,781** (possibly
  one seed-fixture
  test).
- Frontend Vitest: 193 →
  **~198–202** (Lead
  IntakeForm tests + any
  modal wire-in tests).
- Acceptance suite: 9 →
  **10**.
- Migrations `0001`–
  `0048` (unchanged).
- Tenancy carriers 52
  (unchanged).
- DRF admin surface 113
  (unchanged).
- Frontend operator
  routes 20 (unchanged
  — no new routes; only
  the modal wire-in).
- Permission classes 7
  (unchanged).
- Celery-beat task
  families 10
  (unchanged).

## NEXT TASK

Start SESSION_181 with (a)
starting-state
verification, (b)
wrapper + endpoint
shape re-verification,
(c) `<LeadIntakeForm>`
shared component +
Vitest coverage, (d)
`LeadDetailModal` +
`AssignmentDropdown`
wire-in on
`DealerAiSalesLeads`
per M24.1-open
correction, (e)
`+ Walk-in` Dialog CTA
attachment with post-
create-opens-modal (no
redirect), (f) new
`seed_journey_sales_operational_entry`
seed command with
session-safe + cleanup
patterns, (g) new
`walk_in_intake.spec.ts`
Playwright journey per
revised §5.d shape
(intake → list channel
visibility → modal →
assign; no test-drive
scheduling step), (h)
small in-scope §5.d
fixes if surfaced, (i)
ship
`SESSION_181_m24_inc1_walk_in.md`
handoff, (j) refresh
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
   SESSION_180 with M24.1-
   open corrections
   integrated)
6. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (M23 governing
   contract inherited by
   M24)
7. `docs/roadmap/MILESTONE_23_RETROSPECTIVE.md`
   §8 + §9
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
9. `docs/CAPABILITY_MATRIX.md`
   §7x (M23 shipped
   surface)
10. `docs/handoffs/SESSION_180_m24_inc0_planning.md`
    (M24.0 planning
    record + SESSION_181-
    open correction
    section)

Narrative docs are
claims. Rules +
research + code are
facts.

---

## Operational state (post-SESSION_180 M24.0 with M24.1-open corrections integrated)

- **Backend (local):**
  Django on `:8001`.
  Migrations
  `0001`–`0048`. Test
  baseline: **4,780
  pass**, 1 skipped, 0
  fail.
- **Backend (prod):**
  NOT active.
- **Frontend (local):**
  Vite on `:5173`. `tsc
  --noEmit` + `vite
  build` clean. **Vitest
  baseline: 193 pass**.
- **Frontend (prod):**
  NONE.
- **Acceptance workspace
  (local):** Playwright
  1.49 + TS 5.6
  operational; **nine
  journeys** passing
  end-to-end on clean
  DB.
- **Acceptance (CI):**
  live on
  `.github/workflows/acceptance.yml`.
  M23 close-out CI run
  `30840071050` verified
  **success** in 2m20s.
- **Async runtime:**
  Celery 5.5.3 + Redis
  6.4.0 +
  `django-celery-beat`
  2.8.1
  DatabaseScheduler. **10
  scheduled task
  families**.
- **Milestones shipped:**
  M1 → **M23**. **M24
  planning locked** with
  M24.1-open corrections
  integrated;
  implementation begins
  at M24.1 (SESSION_181).
- **DRF admin surface:**
  **113** endpoints (M24
  adds zero).
- **Frontend operator
  routes:** **20** (M24
  adds zero; modal wire-
  in does not add a
  route).
- **Service surface:**
  all M1–M23 packages
  unchanged. M24 will
  add zero service
  verbs.
- **Frontend surfaces
  (M24 target):** two
  new components
  (`<LeadIntakeForm>` +
  `<ReferralLeadFormExtras>`)
  in
  `frontend/src/components/sales/`.
  Three operator Dialog
  CTAs on
  `DealerAiSalesLeads.tsx`
  (`+ Walk-in`, `+ Phone`,
  `+ Referral`).
  `LeadDetailModal` +
  `AssignmentDropdown`
  wired into
  `DealerAiSalesLeads.tsx`
  as an M24.1 in-scope
  extension. No new
  routes.
- **Tenancy carriers:**
  **52** (M24 adds zero).
- **Permission classes:**
  **7 actual** — zero-
  drift streak
  **twenty-three
  consecutive
  milestones** (M10 →
  M23). M24 target:
  extend to twenty-four.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:**
  17 scrub stages
  (unchanged).
- **Deterministic
  rules:** unchanged.
- **Milestone 24
  status:** planning
  LOCKED at SESSION_180
  M24.0 with M24.1-open
  corrections
  integrated;
  implementation begins
  at SESSION_181 M24.1.
- **Sales intake gap
  addressed at M24
  target:** Three
  operator-created
  intake paths (walk-
  in, phone, referral)
  get UI-native intake
  via shared
  `<LeadIntakeForm>` +
  `<ReferralLeadFormExtras>`.
  One externally-created
  intake path (webhook)
  gets an integration-
  to-operator
  Playwright journey via
  the shipped `generic`
  adapter. `LeadDetailModal`
  wired into the sales
  leads page for the
  post-create handoff.
- **Deferred to M25 per
  M24.1-open
  corrections:** (a)
  `<RecordTestDriveForm>`
  component + attachment
  (Candidate O2 sub-
  scope; wrapper exists
  since M11.6);
  (b) `referrer_id` /
  "Referred by" display
  in `LeadDetailModal`
  (small UI extension);
  (c) `platform` display
  in `LeadDetailModal`
  for webhook-origin
  leads (small UI
  extension). Bundle
  (b) + (c) as a single
  "Lead source
  attribution display"
  M25 candidate.
- **Audit tooling:**
  authoritative for
  BHPH + accounting
  endpoints post-M23.1
  fix. Regenerated at
  M24.0 open (153
  endpoints, 110
  covered, 43 backend-
  only).
- **Planning-time
  streak:** **RESET TO
  0** at SESSION_180
  M24.0 for the
  webhook operator-UI
  redirect. **Stays at
  0** through SESSION_181
  M24.1-open correction
  (not further reset;
  not extended).
  Historical run: 89
  across fourteen
  consecutive milestones
  (M10 → M23).
  Preserved for the
  record.
- **DoD amendment
  (M21.0 §5.f Option
  B):** M24 ships four
  new Playwright
  operational journeys
  — intrinsically
  compliant.
- **Governing
  contract:** M21
  Candidate O UI-
  creation shape (also
  used by M23)
  inherited by M24 for
  three operator
  channels; webhook
  channel uses a
  modified integration-
  to-operator variant
  per §5.d.
- **Durable lesson
  strengthened at
  M24.1-open:**
  planning-open
  verification MUST
  cover both intake and
  downstream UI
  surfaces before
  locking §5.b + §5.d
  for any UI-creation
  milestone. M25+
  planning-open
  checklists should
  reflect this.
