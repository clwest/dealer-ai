---
state: active
date: 2026-08-03
last_session_shipped: SESSION_181
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
next_session: SESSION_182
next_milestone: 24
next_milestone_name: "Sales Operational Entry"
next_increment: 2
next_increment_name: "M24.2 — Phone UI + cadence journey"
---

# Next session — SESSION_182 · Milestone 24 · Increment 2 (M24.2 — phone UI + cadence journey)

> **Milestone 24 · Increment
> 1 (M24.1) — SHIPPED at
> SESSION_181.** Walk-in
> intake UI + shared
> `<LeadIntakeForm>`
> substrate +
> `LeadDetailModal` +
> `AssignmentDropdown` wire-
> in on
> `DealerAiSalesLeads` + new
> `seed_journey_sales_operational_entry`
> + `walk_in_intake.spec.ts`
> journey. First anchor UI —
> subsequent M24.2/M24.3
> inherit the substrate via
> sibling-pattern discipline.
>
> **Backend baseline unchanged
> at 4,780 pass, 1 skipped, 0
> fail** (167.7s). **Vitest
> baseline 193 → 201 (+8
> LeadIntakeForm tests).**
> **Acceptance suite 9 → 10
> journeys** — clean-DB dry-
> run: **16 passed @ 25.2s**
> (6 setup + 10 journeys).
>
> **Zero-drift permission-
> class streak** still at 23
> consecutive milestones
> (M10 → M23); M24 target 24
> at close.
>
> **M24 planning-time
> streak** still at 0
> (unchanged since M24.0
> reset; the M24.1-open
> planning correction did
> not further reset it).
>
> **Test-hygiene finding
> at M24.1 close.** State-
> dirty full-suite runs
> surface 3 pre-existing
> failing journeys
> (sales_manager/daily_startup,
> recon/workflow,
> office/accounting_workflow)
> due to non-idempotent
> assertions on shared DB
> state. Clean-DB runs pass
> all 16. Documented M22 §9
> `feedback_avoid_exact_count_locks_in_tests`
> + M23 §9 Candidate H.
> **Not an M24 regression** —
> pre-existing. **Elevated
> as an M25 candidate** for
> the operational-coverage-
> compounding value of a
> stable full-suite baseline.

## First thing SESSION_182 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` —
  top should be the M24.1
  commit; `origin/main`
  still at `6dfdb5c` (M23
  close-out; 2 commits
  behind — no push until
  M24.5).
- `python3 manage.py test
  dealer_ai` → **4,780
  pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test`
  → **201 pass**.
- `python3 manage.py check`
  clean.
- `python3 manage.py
  makemigrations --check
  --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc
  --noEmit` clean.
- `cd acceptance && npx
  tsc --noEmit` clean.
- `redis-cli ping` →
  `PONG`.

### 2. Sanity-check M24.1 shipped surface

- Grep-verify
  `<LeadIntakeForm>` at
  `frontend/src/components/sales/LeadIntakeForm.tsx`.
- Grep-verify
  `sales-leads-add-walk-in`
  testid on
  `DealerAiSalesLeads.tsx`.
- Grep-verify
  `seed_journey_sales_operational_entry`
  in
  `backend/dealer_ai/management/commands/`.
- Grep-verify
  `walk_in_intake.spec.ts`
  in
  `acceptance/journeys/sales_manager/`.

### 3. Ship + Phone Dialog CTA

Per MILESTONE_24_PLANNING.md
§5.b + §7 M24.2:

- Add `+ Phone` Button on
  `DealerAiSalesLeads.tsx`
  next to `+ Walk-in`.
  Testid:
  `sales-leads-add-phone`.
- Add `useState<boolean>`
  for `phoneDialogOpen`.
- Wrap
  `<LeadIntakeForm
  channel="phone"
  onSubmit={createPhoneLead}
  onCreated={/* same
  handler as walk-in:
  close dialog + open
  modal + reload */} />`
  in a Dialog with
  testid
  `sales-leads-phone-dialog`.

### 4. No new component work

`<LeadIntakeForm>` shipped
at M24.1 handles all three
operator channels via the
`channel` prop. Phone
specialization is a pure
reuse — same shape as
walk-in.

### 5. Optional Vitest additions

If the phone code path
warrants specific
coverage (e.g. wrapper
dispatch, channel-
parameterized error copy
verification for phone),
add 2–3 tests to
`LeadIntakeForm.test.tsx`
or a new
`DealerAiSalesLeads.test.tsx`
addition. Otherwise
defer.

### 6. Ship the phone Playwright journey

Per §5.c + §5.d Option C
phone row:

- `acceptance/journeys/sales_manager/phone_intake.spec.ts`:
  1. Navigate to
     `/dealer-ai-sales/leads`.
  2. Click `+ Phone`
     CTA.
  3. Fill form with
     unique per-run
     customer name.
  4. Submit.
  5. Assert
     `LeadDetailModal`
     opens.
  6. Extract new lead id
     from modal header.
  7. Assign
     `Acceptance Advisor`
     via
     `AssignmentDropdown`.
  8. Business-outcome
     assertion via admin
     API: assigned +
     `channel="phone"`.
  9. Close modal (via
     `page.reload()`
     per M24.1 pattern).
  10. Navigate to
      `/dealer-ai-sales/follow-ups`.
  11. Locate
      `CadenceConfigPanel`.
  12. Enter new lead's
      id + select
      `24hr` template.
  13. Submit.
  14. Business-outcome
      assertion via admin
      API: cadence
      created for the
      correct lead with
      the correct
      template.

### 7. Optional assertion helper

If the M24.2 journey
patterns repeat what
M24.1 established,
extract a helper to
`acceptance/support/assertions/sales.ts`.
Else defer to M24.3.

### 8. Small operator-surface gap fixes (in-scope per §5.d)

If authoring surfaces
small gaps: fix in-scope
per M23 §5.d durable
posture. Large gaps:
document as
retrospective §9
evidence for M25
planning.

### 9. Ship the M24.2 handoff

- `docs/handoffs/SESSION_182_m24_inc2_phone.md`
  following M24.1's
  SESSION_181 shape.
- **Do NOT push** —
  coordinated push at
  M24.5.

### 10. Refresh 00-START-NEXT-SESSION.md for M24.3

Point at SESSION_183 M24.3
referral specialization +
referring-customer picker
+ journey.

## Non-goals for SESSION_182

- ❌ Do NOT ship a
  `<WebhookIntakeForm>` or
  `+ Webhook` CTA per §5.b
  + §5.d.
- ❌ Do NOT ship
  `<RecordTestDriveForm>`.
  Deferred to M25 per §3
  deferral 12.
- ❌ Do NOT add
  `referrer_id` or
  `platform` display to
  `LeadDetailModal`.
  Deferred to M25 per §3
  deferrals 13 + 14.
- ❌ Do NOT re-write
  `<LeadIntakeForm>`.
  Reuse the M24.1
  substrate unchanged.
- ❌ Do NOT ship the
  `<ReferralLeadFormExtras>`
  component. That lands at
  M24.3.
- ❌ Do NOT wire up any
  channels beyond phone —
  each channel lands in
  its own increment per
  sibling-pattern
  discipline.
- ❌ Do NOT push
  individual M24 commits
  — coordinated close-out
  push at M24.5.
- ❌ Do NOT force-scope
  the test-hygiene fixes
  (Candidate H) into M24.
  Elevated as M25
  candidate per §9
  finding.

## Baseline expected at M24.2 close

- Backend: 4,780 → 4,780
  (unchanged; new journey-
  only work).
- Frontend Vitest: 201 →
  **~201–204** (optional
  additions if needed).
- Acceptance suite
  (clean-DB): 16 → **17**.
- Migrations `0001`–
  `0048` (unchanged).
- Tenancy carriers 52
  (unchanged).
- DRF admin surface 113
  (unchanged).
- Frontend operator
  routes 20 (unchanged).
- Permission classes 7
  (unchanged).
- Celery-beat task
  families 10
  (unchanged).

## NEXT TASK

Start SESSION_182 with (a)
starting-state
verification, (b)
M24.1-shipped-surface
sanity check, (c) `+
Phone` Dialog CTA on
`DealerAiSalesLeads.tsx`
reusing the
`<LeadIntakeForm>`
substrate, (d) optional
Vitest additions for
phone code path, (e)
new
`phone_intake.spec.ts`
Playwright journey
covering intake →
modal → assign → follow-
ups page → cadence
creation per revised
§5.d shape, (f) optional
assertion helper
extraction if patterns
repeat, (g) small in-
scope §5.d fixes if
surfaced, (h) ship
`SESSION_182_m24_inc2_phone.md`
handoff, (i) refresh
`00-START-NEXT-SESSION.md`
for M24.3.

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
7. `docs/roadmap/MILESTONE_23_RETROSPECTIVE.md`
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
9. `docs/CAPABILITY_MATRIX.md`
10. `docs/handoffs/SESSION_181_m24_inc1_walk_in.md`
    (M24.1 shipped + test-
    hygiene Candidate H
    reinforcement note)
11. `docs/handoffs/SESSION_180_m24_inc0_planning.md`
    (M24.0 record +
    SESSION_181-open
    correction section)

Narrative docs are
claims. Rules +
research + code are
facts.

---

## Operational state (post-SESSION_181 M24.1)

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
  --noEmit` clean.
  **Vitest baseline:
  201 pass**.
- **Frontend (prod):**
  NONE.
- **Acceptance workspace
  (local):** Playwright
  1.49 + TS 5.6
  operational. **10
  journeys** end-to-end.
  **Clean-DB dry-run
  baseline: 16 passed
  (~25.2s)** (6 setup +
  10 journeys).
- **Acceptance (CI):**
  live on
  `.github/workflows/acceptance.yml`.
  Last verified green
  run: M23 close-out
  `30840071050` (2m20s).
  First M24 CI run
  fires at M24.5
  coordinated push.
- **Async runtime:**
  Celery 5.5.3 + Redis
  6.4.0 +
  `django-celery-beat`
  2.8.1
  DatabaseScheduler.
  **10 scheduled task
  families**.
- **Milestones shipped:**
  M1 → **M23**. M24
  IN PROGRESS —
  M24.0 planning +
  M24.1 walk-in
  shipped;
  M24.2/M24.3/M24.4
  pending.
- **DRF admin surface:**
  **113** endpoints (M24
  adds zero).
- **Frontend operator
  routes:** **20** (M24
  adds zero;
  `LeadDetailModal`
  wire-in reused the
  existing route).
- **Service surface:**
  all M1–M23 packages
  unchanged. M24 adds
  zero service verbs.
- **Frontend surfaces
  shipped at M24.1:**
  - New:
    `<LeadIntakeForm>`
    (`frontend/src/components/sales/LeadIntakeForm.tsx`).
  - Extended:
    `DealerAiSalesLeads.tsx`
    with `+ Walk-in`
    Dialog CTA +
    `LeadDetailModal`
    wire-in +
    `AssignmentDropdown`
    reach + row-click
    handler + `data-
    testid` additions.
- **Frontend surfaces
  planned at M24.2:**
  `+ Phone` Dialog CTA
  reusing
  `<LeadIntakeForm>`.
- **Frontend surfaces
  planned at M24.3:**
  `<ReferralLeadFormExtras>`
  + `+ Referral`
  Dialog CTA.
- **Frontend surfaces
  planned at M24.4:**
  NONE — webhook is
  journey-only.
- **Tenancy carriers:**
  **52** (M24 adds
  zero).
- **Permission
  classes:** **7
  actual** — zero-drift
  streak **twenty-
  three consecutive
  milestones** (M10 →
  M23). M24 target:
  extend to twenty-
  four.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:**
  17 scrub stages
  (unchanged).
- **Deterministic
  rules:** unchanged.
- **Milestone 24
  status:** IN PROGRESS.
  M24.0 planning +
  M24.1 walk-in
  shipped;
  implementation
  continues at
  SESSION_182 M24.2.
- **Sales intake gap
  addressed so far:**
  walk-in operator
  intake UI-native +
  reachable end-to-end
  through the sales-
  side leads page +
  post-create modal +
  assignment. Phone /
  referral / webhook
  pending.
- **Deferred to M25
  per M24.1-open
  corrections:**
  (a)
  `<RecordTestDriveForm>`
  component +
  attachment;
  (b) `referrer_id` /
  "Referred by"
  display in
  `LeadDetailModal`;
  (c) `platform`
  display in
  `LeadDetailModal`
  for webhook-origin
  leads. Bundle (b) +
  (c) as a single
  "Lead source
  attribution
  display" M25
  candidate.
- **Test-hygiene
  Candidate H
  reinforcement**
  from M24.1 close:
  full-suite runs on
  state-dirty DB
  surface 3 pre-
  existing failing
  journeys
  (sales_manager/daily_startup,
  recon/workflow,
  office/accounting_workflow).
  Clean-DB runs pass
  all 16. Not an M24
  regression; elevated
  as M25 candidate
  for operational-
  coverage-
  compounding value
  of a stable full-
  suite baseline.
- **Audit tooling:**
  authoritative for
  BHPH + accounting
  endpoints post-
  M23.1 fix. Not
  regenerated at
  M24.1 close (no
  new endpoints; no
  new wrappers).
- **Planning-time
  streak:** **0**
  (unchanged since
  M24.0 reset; M24.1-
  open correction did
  not further reset).
  Historical run: 89
  across fourteen
  consecutive
  milestones (M10 →
  M23). Preserved
  for the record.
- **DoD amendment
  (M21.0 §5.f Option
  B):** M24 ships
  four new Playwright
  operational
  journeys — 1 of 4
  shipped at M24.1
  (`walk_in_intake`);
  3 to go
  (M24.2/M24.3/M24.4).
- **Governing
  contract:** M21
  Candidate O UI-
  creation shape.
- **Durable lesson
  from M24.1-open:**
  planning-open
  verification must
  cover both intake
  and downstream UI
  surfaces before
  locking §5.b + §5.d
  for any UI-creation
  milestone.
