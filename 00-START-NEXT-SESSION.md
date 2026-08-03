---
state: active
date: 2026-08-03
last_session_shipped: SESSION_182
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
next_session: SESSION_183
next_milestone: 24
next_milestone_name: "Sales Operational Entry"
next_increment: 3
next_increment_name: "M24.3 — Referral UI + referring-customer picker + journey"
---

# Next session — SESSION_183 · Milestone 24 · Increment 3 (M24.3 — referral UI + referring-customer picker + journey)

> **Milestone 24 · Increment
> 2 (M24.2) — SHIPPED at
> SESSION_182.** Phone Dialog
> CTA on `DealerAiSalesLeads`
> reusing the M24.1
> `<LeadIntakeForm>` substrate
> unchanged +
> `phone_intake.spec.ts`
> journey with downstream
> cadence step via existing
> `CadenceConfigPanel`.
>
> **Backend baseline unchanged
> at 4,780 pass** (no code
> changes; existing suite
> reverified at M24.1).
> **Vitest baseline 201 pass**
> (no additions; existing
> M24.1 tests already cover
> phone). **Acceptance suite
> 10 → 11 journeys** — clean-
> DB dry-run: **17 passed @
> 24.6s** (6 setup + 11
> journeys).
>
> **Zero-drift permission-
> class streak** still at 23
> consecutive milestones
> (M10 → M23); M24 target
> 24 at close.
>
> **M24 planning-time
> streak** still at 0
> (unchanged since M24.0
> reset).
>
> **M24.3 is the third
> anchor UI increment.**
> Referral adds
> `<ReferralLeadFormExtras>`
> component (referring-
> customer picker) as a
> small delta over the
> shared form + a journey
> that validates backend
> referrer FK attribution
> via API-side assertion
> (modal-side referrer
> display deferred per §3
> deferral 13).

## First thing SESSION_183 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` —
  top should be the M24.2
  commit; `origin/main`
  still at `6dfdb5c` (M23
  close-out; 4 commits
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
- `cd acceptance && npx tsc
  --noEmit` clean.
- `redis-cli ping` →
  `PONG`.

### 2. Sanity-check M24.2 shipped surface

- Grep-verify
  `sales-leads-add-phone`
  testid on
  `DealerAiSalesLeads.tsx`.
- Grep-verify
  `phone_intake.spec.ts`
  in
  `acceptance/journeys/sales_manager/`.

### 3. Ship `<ReferralLeadFormExtras>` component

Per MILESTONE_24_PLANNING.md
§5.b + §7 M24.3:

- Create
  `frontend/src/components/sales/ReferralLeadFormExtras.tsx`.
- "Referring customer
  (existing lead)"
  picker: search box +
  dropdown showing tenant-
  scoped lead matches
  from `fetchAdminLeads`.
- Optional field —
  operator may skip
  (matches backend
  nullability).
- On select, calls a
  callback with the
  selected lead's id.
- Exposes state via a
  controlled component
  pattern OR a simple
  callback that the
  parent Dialog handler
  captures.
- Vitest coverage: ~5–7
  tests (picker search,
  tenant scope, optional
  handling, submission
  behavior).

### 4. Wire the picker into the referral Dialog

- Add `+ Referral` Button
  next to `+ Walk-in` /
  `+ Phone`. Testid:
  `sales-leads-add-referral`.
- Add
  `useState<boolean>` for
  `referralDialogOpen`.
- Add
  `useState<number |
  null>` for
  `selectedReferrerId`
  (or similar
  state depending on
  component pattern).
- Dialog wraps
  `<LeadIntakeForm
  channel="referral"
  onSubmit={
    (payload) =>
      createReferralLead({
        ...payload,
        referrer_lead_id: selectedReferrerId,
      })
  }
  extras={<ReferralLeadFormExtras
    onSelect={setSelectedReferrerId}
  />} />`.
- Reset picker state on
  Dialog close.

### 5. Ship the referral Playwright journey

Per §5.c + §5.d Option C
referral row:

- `acceptance/journeys/sales_manager/referral_intake.spec.ts`:
  1. Navigate to
     `/dealer-ai-sales/leads`.
  2. Click `+ Referral`
     CTA.
  3. Fill form with
     unique per-run
     customer name.
  4. In the picker,
     search for and
     select the seeded
     referring-customer
     lead (`Priya Prior-
     Customer`).
  5. Submit.
  6. Assert
     `LeadDetailModal`
     opens.
  7. Extract new lead id.
  8. Assign Acceptance
     Advisor.
  9. **Business-outcome
     assertion via admin
     API:** fetch new
     lead; assert
     `referrer` (or the
     API's field name)
     matches the picker's
     selected lead id;
     `channel="referral"`;
     `assigned_to` is
     Acceptance Advisor.
  10. Reload → assert
      list row shows
      `channel="referral"`.
- **No modal-side
  referrer-display
  assertion** —
  `LeadDetailModal` does
  not display
  `referrer_id`
  (deferred per §3
  deferral 13 to M25).

### 6. Optional assertion helper

If patterns are
repeating enough,
extract to
`acceptance/support/assertions/sales.ts`.

### 7. Small operator-surface gap fixes (in-scope per §5.d)

Per §5.d durable posture.

### 8. Ship the M24.3 handoff

- `docs/handoffs/SESSION_183_m24_inc3_referral.md`
  following M24.2 shape.
- **Do NOT push** —
  coordinated push at
  M24.5.

### 9. Refresh 00-START-NEXT-SESSION.md for M24.4

Point at SESSION_184
M24.4 webhook integration
journey.

## Non-goals for SESSION_183

- ❌ Do NOT ship a
  `<WebhookIntakeForm>` or
  `+ Webhook` CTA per §5.b
  + §5.d.
- ❌ Do NOT ship
  `<RecordTestDriveForm>`
  (M25 §3 deferral 12).
- ❌ Do NOT add
  `referrer_id` or
  `platform` display to
  `LeadDetailModal` (M25
  §3 deferrals 13 + 14).
- ❌ Do NOT redesign the
  `CustomerLead.referrer`
  backend self-FK.
  Preserve as-is; UI
  picker label uses
  truthful operator
  language ("Referring
  customer (existing
  lead)").
- ❌ Do NOT re-write
  `<LeadIntakeForm>` —
  reuse M24.1 substrate
  via the extras slot.
- ❌ Do NOT push
  individual M24 commits
  — coordinated close-out
  push at M24.5.
- ❌ Do NOT force-scope
  test-hygiene
  (Candidate H) into
  M24 — elevated as M25
  candidate.

## Baseline expected at M24.3 close

- Backend: 4,780 → 4,780
  (unchanged).
- Frontend Vitest: 201 →
  **~207–212** (~5–7 new
  `<ReferralLeadFormExtras>`
  tests).
- Acceptance suite
  (clean-DB): 17 →
  **18**.
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

Start SESSION_183 with (a)
starting-state
verification, (b)
M24.2-shipped-surface
sanity check, (c) new
`<ReferralLeadFormExtras>`
component with tenant-
scoped picker + Vitest
coverage, (d) `+
Referral` Dialog CTA on
`DealerAiSalesLeads.tsx`
wrapping
`<LeadIntakeForm
channel="referral">`
composed with the picker
via extras slot, (e)
new
`referral_intake.spec.ts`
Playwright journey with
API-side referrer
attribution assertion
(no modal-side display
per M25 deferral), (f)
optional assertion
helper extraction if
patterns repeat, (g)
small in-scope §5.d
fixes if surfaced, (h)
ship
`SESSION_183_m24_inc3_referral.md`
handoff, (i) refresh
`00-START-NEXT-SESSION.md`
for M24.4.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_24_PLANNING.md`
6. `docs/roadmap/MILESTONE_23_PLANNING.md`
7. `docs/roadmap/MILESTONE_23_RETROSPECTIVE.md`
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
9. `docs/CAPABILITY_MATRIX.md`
10. `docs/handoffs/SESSION_182_m24_inc2_phone.md`
    (M24.2 shipped)
11. `docs/handoffs/SESSION_181_m24_inc1_walk_in.md`
    (M24.1 shipped +
    test-hygiene Candidate H
    reinforcement note)
12. `docs/handoffs/SESSION_180_m24_inc0_planning.md`
    (M24.0 record +
    SESSION_181-open
    correction section)

Narrative docs are
claims. Rules +
research + code are
facts.

---

## Operational state (post-SESSION_182 M24.2)

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
  Vite on `:5173`.
  **Vitest baseline:
  201 pass**.
- **Frontend (prod):**
  NONE.
- **Acceptance workspace
  (local):** Playwright
  1.49 + TS 5.6. **11
  journeys** end-to-end.
  **Clean-DB dry-run
  baseline: 17 passed
  (~24.6s)** (6 setup +
  11 journeys).
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
  6.4.0. **10 scheduled
  task families**.
- **Milestones shipped:**
  M1 → **M23**. M24 IN
  PROGRESS — M24.0
  planning + M24.1
  walk-in + M24.2
  phone shipped;
  M24.3/M24.4 pending.
- **DRF admin surface:**
  **113** endpoints (M24
  adds zero).
- **Frontend operator
  routes:** **20** (M24
  adds zero).
- **Service surface:**
  all M1–M23 packages
  unchanged.
- **Frontend surfaces
  shipped at M24.1:**
  `<LeadIntakeForm>`
  component + `+
  Walk-in` Dialog CTA
  + `LeadDetailModal` +
  `AssignmentDropdown`
  wire-in.
- **Frontend surfaces
  shipped at M24.2:**
  `+ Phone` Dialog CTA
  reusing
  `<LeadIntakeForm>`
  (no new component
  work).
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
  streak **23
  consecutive
  milestones** (M10 →
  M23). M24 target: 24.
- **AI safety stack:**
  17 scrub stages.
- **Milestone 24
  status:** IN PROGRESS.
  M24.0 planning +
  M24.1 walk-in +
  M24.2 phone shipped;
  M24.3 referral
  next.
- **Sales intake gaps
  closed so far:**
  walk-in (M24.1) +
  phone (M24.2)
  operator UI-native
  intake + reachable
  end-to-end through
  the sales-side leads
  page + post-create
  modal + assignment
  (+ cadence downstream
  for phone).
- **Deferred to M25**
  per M24.1-open
  corrections + M24.1
  test-hygiene finding:
  (a)
  `<RecordTestDriveForm>`;
  (b) `referrer_id`
  display in modal;
  (c) `platform`
  display in modal;
  (d) test-hygiene
  Candidate H (stable
  full-suite baseline
  on state-dirty DB).
- **Audit tooling:**
  authoritative for
  BHPH + accounting
  post-M23.1 fix.
  Not regenerated at
  M24.2 close (no new
  endpoints; no new
  wrappers).
- **Planning-time
  streak:** **0**
  (unchanged since
  M24.0 reset).
  Historical run: 89.
- **DoD amendment
  (M21.0 §5.f Option
  B):** M24 ships
  four new Playwright
  operational
  journeys — 2 of 4
  shipped
  (`walk_in_intake`,
  `phone_intake`);
  2 to go
  (`referral_intake`,
  `webhook_integration_intake`).
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
  locking §5.b + §5.d.
