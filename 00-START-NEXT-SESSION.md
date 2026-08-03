---
state: active
date: 2026-08-03
last_session_shipped: SESSION_183
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
next_session: SESSION_184
next_milestone: 24
next_milestone_name: "Sales Operational Entry"
next_increment: 4
next_increment_name: "M24.4 — Webhook integration-to-operator journey"
---

# Next session — SESSION_184 · Milestone 24 · Increment 4 (M24.4 — webhook integration-to-operator journey)

> **Milestone 24 · Increment
> 3 (M24.3) — SHIPPED at
> SESSION_183.**
> `<ReferralLeadFormExtras>`
> component with tenant-
> scoped referring-customer
> picker + `+ Referral`
> Dialog CTA on
> `DealerAiSalesLeads` +
> `referral_intake.spec.ts`
> journey with API-side
> referrer FK attribution
> assertion (modal-side
> display deferred to M25).
>
> **Backend baseline
> unchanged at 4,780 pass.**
> **Vitest baseline 201 →
> 209 (+8
> `<ReferralLeadFormExtras>`
> tests).** **Acceptance
> suite 11 → 12 journeys** —
> clean-DB dry-run: **18
> passed @ 25.9s**.
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
> **M24.4 is the fourth and
> final journey increment.**
> Webhook integration-to-
> operator journey — NO new
> UI component (webhook is
> system-to-system per M24.0
> → M24.1-open redirect).
> Playwright setup POSTs to
> the real
> `/admin/leads/webhook/`
> endpoint with
> `platform="generic"` +
> realistic dealer-owned
> envelope; browser then
> handles the ingested lead
> through the shipped sales-
> side UI (list channel
> filter → modal → assign).
> **Small-scope increment;
> may fold into M24.5
> close-out if journey-only
> work exceeds no in-scope
> §5.d fixes** (per §5.h
> Option B evidence-sized
> collapse posture).

## First thing SESSION_184 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` —
  top should be the M24.3
  commit; `origin/main`
  still at `6dfdb5c` (M23
  close-out; 5 commits
  behind — no push until
  M24.5).
- `python3 manage.py test
  dealer_ai` → **4,780
  pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test`
  → **209 pass**.
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

### 2. Sanity-check M24.3 shipped surface

- Grep-verify
  `sales-leads-add-referral`
  testid on
  `DealerAiSalesLeads.tsx`.
- Grep-verify
  `<ReferralLeadFormExtras>`
  at
  `frontend/src/components/sales/ReferralLeadFormExtras.tsx`.
- Grep-verify
  `referral_intake.spec.ts`
  in
  `acceptance/journeys/sales_manager/`.

### 3. Re-verify shipped webhook adapter

- `grep _ADAPTERS
  backend/dealer_ai/services/leads/webhook_adapters/__init__.py`
  → should show
  `"generic": generic`
  (unchanged; no new
  named-platform adapters
  shipped in M24).
- Confirm the `generic`
  adapter's documented
  envelope
  (`webhook_adapters/generic.py:14`)
  still accepts:
  `full_name` (required),
  `phone`, `email`,
  `message`,
  `target_monthly_payment`,
  `down_payment`,
  `trade_in`,
  `credit_range`.

### 4. Ship the webhook integration-to-operator journey

Per MILESTONE_24_PLANNING.md
§5.d Option C webhook row +
§7 M24.4:

- `acceptance/journeys/sales_manager/webhook_integration_intake.spec.ts`:
  1. `test.beforeEach`:
     use APIRequestContext
     to POST to
     `/api/dealer-ai/admin/leads/webhook/`
     with
     `platform="generic"`
     + realistic dealer-
     owned envelope
     (unique per-run
     `full_name` +
     phone/email so runs
     don't collide). Body
     shape:
     ```
     {
       platform: "generic",
       payload: {
         full_name: "M24.4
                     Webhook
                     Winnie
                     ${Date.now()}",
         phone: "+15551244004",
         email: "m244-webhook-winnie@example.com",
         message: "Interested
                   in the
                   F-150",
         target_monthly_payment: "450",
         down_payment: "3000"
       }
     }
     ```
  2. Assert the POST
     returned 201 + capture
     the new lead id from
     the response body's
     `lead.id` (per
     `views_leads.py:216`
     projection).
  3. Login as
     salesperson (via
     storage state).
  4. Navigate to
     `/dealer-ai-sales/leads`.
  5. Change the channel
     filter to
     `listing_form` via
     the existing
     `Channel filter`
     select (channel enum
     for webhook-ingested
     leads is
     `LEAD_CHANNEL_LISTING_FORM`
     per
     `channel_intake.py`).
  6. Assert the ingested
     lead's row appears in
     the filtered table
     with the expected
     name.
  7. Click the row →
     `LeadDetailModal`
     opens.
  8. Assign Acceptance
     Advisor via
     AssignmentDropdown.
  9. Business-outcome
     assertion via admin
     API: assigned +
     `channel="listing_form"`.

### 5. Small operator-surface gap fixes (in-scope per §5.d)

Rare — the browser-side
flow uses shipped UI +
M24.1 wire-in unchanged.
Only the API-side setup
step is new. Any surfaced
gaps: fix in-scope per
M23 §5.d durable posture.

### 6. Collapse decision

Per §5.h Option B
evidence-sized posture: if
the journey lands cleanly
with zero in-scope §5.d
fixes, M24.4 may fold
into M24.5 close-out
(single session).
Otherwise, ship M24.4
as its own increment
handoff and open M24.5
separately at SESSION_185.

### 7. Ship the M24.4 handoff (or fold into M24.5)

Non-folded path:
- `docs/handoffs/SESSION_184_m24_inc4_webhook.md`
  following M24.3 shape.
- **Do NOT push** —
  coordinated push at
  M24.5.
- Refresh
  `00-START-NEXT-SESSION.md`
  for M24.5.

Folded path (M24.4 →
M24.5 in one session):
- Skip a M24.4-specific
  handoff.
- Proceed directly to the
  M24.5 close-out
  activities in the same
  session:
  * Coordinated close-out
    commit.
  * CI validation of all
    four new M24
    journeys.
  * `docs/CAPABILITY_MATRIX.md`
    §7y — M24 shipped
    surface.
  * `docs/roadmap/MILESTONE_24_RETROSPECTIVE.md`
    with §8 corrections
    (both M24.0 and
    M24.1-open) + §9
    next-candidate.
  * `docs/roadmap/MILESTONE_25_PLANNING.md`
    skeleton (draft),
    elevating the three
    §3 deferrals + test-
    hygiene Candidate H.
  * `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
    updated with M24
    shipped.
  * `00-START-NEXT-SESSION.md`
    refreshed for M25.0.
  * **Coordinated push**
    of all M24 commits
    to `main`.

## Non-goals for SESSION_184

- ❌ Do NOT ship a
  `<WebhookIntakeForm>` or
  `+ Webhook` operator CTA.
  Per §5.b + §5.d M24.0
  redirect (webhook is
  system-to-system, not
  operator-authored).
- ❌ Do NOT create a
  test-only backend
  endpoint or fake
  operator workflow to
  make the webhook
  journey fully browser-
  driven. Per §5.d Option
  B: use the real webhook
  endpoint as the setup
  boundary.
- ❌ Do NOT ship named-
  platform webhook
  adapters (Autotrader /
  Cars.com / CarGurus /
  Facebook Marketplace).
  Documented as future
  work in
  `webhook_adapters/__init__.py`.
- ❌ Do NOT ship
  `<RecordTestDriveForm>`
  or referrer/platform
  display in modal —
  deferred to M25 per §3
  deferrals 12/13/14.
- ❌ Do NOT add new
  backend service verbs,
  DRF endpoints,
  tenancy carriers,
  migrations, permission
  classes, or frontend
  routes.
- ❌ Do NOT push M24
  commits individually —
  coordinated close-out
  push at M24.5.
- ❌ Do NOT force-scope
  larger discovered gaps
  into M24 — document as
  retrospective §9
  evidence.
- ❌ Do NOT force-scope
  test-hygiene fixes
  (Candidate H) into
  M24 — elevated as M25
  candidate.

## Baseline expected at M24.4 close

- Backend: 4,780 → 4,780
  (unchanged; journey-
  only work).
- Frontend Vitest: 209
  → 209 (unchanged; no
  new component work).
- Acceptance suite
  (clean-DB): 18 →
  **19**.
- Migrations `0001`–
  `0048` (unchanged).
- Tenancy carriers 52
  (unchanged).
- DRF admin surface 113
  (unchanged).
- Frontend operator
  routes 20 (unchanged).
- Permission classes 7
  (unchanged; streak
  target at M24.5 close:
  24).
- Celery-beat task
  families 10
  (unchanged).

## NEXT TASK

Start SESSION_184 with (a)
starting-state
verification, (b)
M24.3-shipped-surface
sanity check, (c)
webhook adapter re-
verification (grep
`_ADAPTERS`; confirm
`generic` envelope
shape), (d) new
`webhook_integration_intake.spec.ts`
Playwright journey with
`test.beforeEach` real
webhook POST + browser-
side channel-filter-and-
assign flow per revised
§5.d shape, (e) small
in-scope §5.d fixes if
surfaced, (f) collapse
decision — if journey
lands cleanly, fold
M24.4 into M24.5 close-
out (single session);
else ship M24.4
handoff separately and
open M24.5 at
SESSION_185.

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
10. `docs/handoffs/SESSION_183_m24_inc3_referral.md`
11. `docs/handoffs/SESSION_182_m24_inc2_phone.md`
12. `docs/handoffs/SESSION_181_m24_inc1_walk_in.md`
13. `docs/handoffs/SESSION_180_m24_inc0_planning.md`

Narrative docs are
claims. Rules +
research + code are
facts.

---

## Operational state (post-SESSION_183 M24.3)

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
  209 pass**.
- **Frontend (prod):**
  NONE.
- **Acceptance workspace
  (local):** Playwright
  1.49 + TS 5.6. **12
  journeys** end-to-end.
  **Clean-DB dry-run
  baseline: 18 passed
  (~25.9s)** (6 setup +
  12 journeys).
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
  phone + M24.3
  referral shipped;
  M24.4 webhook +
  M24.5 close-out
  pending (may fold).
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
  `<LeadIntakeForm>`.
- **Frontend surfaces
  shipped at M24.3:**
  `<ReferralLeadFormExtras>`
  component +
  `+ Referral` Dialog
  CTA composing
  `<LeadIntakeForm
  channel="referral">`
  with extras slot.
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
  M24.2 phone +
  M24.3 referral
  shipped; M24.4
  webhook journey
  next (may fold into
  M24.5 close-out).
- **Sales intake gaps
  closed so far:**
  walk-in (M24.1),
  phone (M24.2),
  referral (M24.3)
  operator UI-native
  intake + reachable
  end-to-end through
  sales-side leads
  page + post-create
  modal + assignment
  (+ cadence
  downstream for
  phone; + referrer
  FK backend
  attribution for
  referral).
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
  post-M23.1 fix. Not
  regenerated at
  M24.3 close (no new
  endpoints; no new
  wrappers).
- **Planning-time
  streak:** **0**
  (unchanged since
  M24.0 reset).
  Historical run: 89.
- **DoD amendment
  (M21.0 §5.f Option
  B):** M24 ships four
  new Playwright
  operational
  journeys — 3 of 4
  shipped
  (`walk_in_intake`,
  `phone_intake`,
  `referral_intake`);
  1 to go
  (`webhook_integration_intake`).
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
