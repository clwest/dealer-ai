---
title: "SESSION_183 handoff — Milestone 24 · Increment 3 (M24.3 — referral UI + referring-customer picker + journey)"
status: historical
type: handoff
date: 2026-08-03
session: 183
milestone: 24
milestone_status: in-progress
milestone_name: "Sales Operational Entry"
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_183 — Milestone 24 · Increment 3 (M24.3 — referral UI + referring-customer picker + journey)

## What shipped

Third anchor UI increment per M24
§5.a scope. Referral adds the
`<ReferralLeadFormExtras>`
component (a tenant-scoped
"Referring customer (existing
lead)" picker) as a small delta
over the shared M24.1
`<LeadIntakeForm>` substrate,
composed via the extras slot.
Journey validates the backend
referrer FK attribution via API-
side assertion (`LeadDetailModal`
does not currently display
`referrer_id`; deferred per M24
§3 deferral 13 to M25). Webhook
integration journey ships at
M24.4.

**Verification:**
- Isolated sales_manager project
  run on clean DB: **10 passed
  @ 16.9s** (6 setup + 4
  journeys: daily_startup +
  walk-in + phone + referral).
- Full acceptance suite on
  clean DB: **18 passed @
  25.9s** (6 setup + 12
  journeys; up from 17 passed
  / 11 journeys at M24.2
  close).
- Full Vitest run on affected
  components (DealerAiSalesLeads
  + LeadIntakeForm +
  ReferralLeadFormExtras +
  RecordBeBackForm +
  CadenceConfigPanel): **29
  passed** (up from 12 at
  M24.2 close — 8 new
  `<ReferralLeadFormExtras>`
  tests + adjacent suites
  covered).
- Frontend + acceptance tsc
  clean.

**Backend baseline unchanged:**
4,780 pass, 1 skipped, 0 fail
(no backend code changes).

**Frontend Vitest baseline
delta:** 201 → **209 (+8)** — 8
new `<ReferralLeadFormExtras>`
tests.

**Acceptance suite baseline
delta:** 11 → **12 journeys**
(sales_manager project 3 → 4;
clean-DB suite 17 → 18).

**Zero-drift permission-class
streak:** still twenty-three
consecutive milestones (M10 →
M23). M24.3 introduces zero
permission-class changes.
Streak target at M24.5 close:
twenty-four.

**M24 planning-time streak:**
still at 0 (unchanged since
M24.0 reset).

### Shipped surface

**Frontend components (new):**
- `frontend/src/components/sales/ReferralLeadFormExtras.tsx`
  — controlled component;
  props: `value: number | null`
  (currently-selected referring
  customer id) + `onSelect:
  (leadId: number | null) =>
  void`. Fetches tenant-scoped
  leads on mount via
  `fetchAdminLeads({ limit:
  200 })`; filters client-side
  by name/phone/email
  substring as the operator
  types (server-side name
  filter does not exist today
  — would require an
  `admin-leads-search`
  endpoint, out of scope for
  M24). Top 10 matches render
  as clickable rows keyed by
  lead id. Optional field per
  backend nullability
  (models.py:904 SET_NULL);
  the "Unselect" button clears
  the selection to null.
  Testids:
  `referral-lead-form-extras`,
  `referral-lead-form-extras-search`,
  `referral-lead-form-extras-selected`,
  `referral-lead-form-extras-clear`,
  `referral-lead-form-extras-matches`,
  `referral-lead-form-extras-match-<id>`,
  `referral-lead-form-extras-empty`,
  `referral-lead-form-extras-error`.
- `frontend/src/components/sales/ReferralLeadFormExtras.test.tsx`
  — 8 unit tests: mount fetches
  with `limit=200`, no matches
  until search entered, name-
  substring filter (case-
  insensitive), phone/email
  substring filter, empty-
  state when no matches,
  onSelect callback with picked
  id, selected chip renders
  with lead details + Unselect
  clears, load-error surface.

**Frontend pages (extended):**
- `frontend/src/pages/DealerAiSalesLeads.tsx`
  — added:
  - `createReferralLead`
    import alongside
    `createPhoneLead` +
    `createWalkInLead`.
  - `ReferralLeadFormExtras`
    import.
  - `useState<boolean>` for
    `referralDialogOpen`.
  - `useState<number | null>`
    for `referrerLeadId`
    (picker selection state
    lifted into parent so the
    submit handler can fold it
    into the createReferralLead
    payload).
  - `+ Referral` Button in
    page header
    (`data-testid="sales-leads-add-referral"`)
    sibling to `+ Walk-in` /
    `+ Phone`.
  - `Dialog` wrapping
    `<LeadIntakeForm
    channel="referral"
    onSubmit={(payload) =>
      createReferralLead({
        ...payload,
        referrer_lead_id: referrerLeadId,
      })
    }
    extras={<ReferralLeadFormExtras
      value={referrerLeadId}
      onSelect={setReferrerLeadId} />} />`
    (`data-testid="sales-leads-referral-dialog"`).
  - Dialog `onOpenChange`
    resets `referrerLeadId` to
    null when the Dialog
    closes so a subsequent
    Referral CTA opens with a
    clean picker.
  - Post-create closes intake
    Dialog + clears picker +
    opens `LeadDetailModal` +
    reloads list.

**Backend: no changes.** The
existing `createReferralLead`
wrapper (M11.6) posts to the
existing `admin-lead-referral-
create` endpoint (M11.1). The
existing `record_referral_lead`
service verb enforces tenant-
scoped `referrer_lead_id`
validation (raises
`CrossTenantReferrerError` →
404 on cross-tenant, unchanged).

**Seed: no changes.** M24.1's
`seed_journey_sales_operational_entry`
already provisions the
salesperson persona + advisor +
Priya Prior-Customer referring
lead. The referral journey
picks Priya via the picker.

**Acceptance journey (new):**
- `acceptance/journeys/sales_manager/referral_intake.spec.ts`
  — referral intake operational
  contract:
  1. Look up Priya's id via
     `findSeededLead` (id
     shifts across suite runs
     because seed --reset
     re-creates her).
  2. Navigate to
     `/dealer-ai-sales/leads`.
  3. Click `+ Referral` CTA.
  4. Search "Priya" in the
     picker → click her
     match row (dynamic
     testid
     `referral-lead-form-extras-match-<id>`).
  5. Assert the "selected"
     chip appears with
     Priya's name.
  6. Fill LeadIntakeForm base
     fields with unique per-
     run customer name.
  7. Submit → LeadDetailModal
     opens.
  8. Extract new lead id
     from modal header.
  9. Assign Acceptance
     Advisor via
     AssignmentDropdown.
  10. Business-outcome
      assertion via admin
      API: new lead assigned
      + `channel="referral"`
      + `referrer` FK matches
      Priya's id (backend
      contract preserved
      even though modal does
      not display it —
      deferred to M25 per §3
      deferral 13).
  11. Reload → assert list
      row shows
      `channel="referral"`.

**Journey design notes:**
- API-side referrer assertion
  is the operational contract
  (per user M24.1-open
  direction: "retain
  attribution assertions only
  if the existing lead-detail
  UI truthfully displays those
  fields. Otherwise validate
  creation, source/channel
  persistence, detail
  visibility, and assignment,
  and document the missing
  attribution presentation
  separately"). Modal-side
  referrer display is
  deferred to M25 §3 deferral
  13 as a genuinely-missing
  UI surface.
- Reused M24.1/M24.2 reload-
  instead-of-close-button
  pattern (strict-mode
  Close collision
  avoidance).
- Unique per-run customer
  name (timestamped).

## Starting-state verification (this session)

Fast checklist (skipped full
Django + Vitest since no code
changed between the M24.2
commit `0e83342` and M24.3
open):

- `git status` — clean; 4
  commits ahead of `origin/main`.
- `git log --oneline -6` —
  top is `0e83342` (M24.2
  close); `origin/main`
  still at `6dfdb5c`.
- `python3 manage.py check`
  clean.
- `redis-cli ping` → `PONG`.

Post-change verification:
- Vitest on affected files
  (5 suites): **29 passed**.
- Frontend tsc post-changes:
  clean.
- Acceptance tsc post-
  journey-add: clean.
- sales_manager project
  clean-DB run: 10 passed
  @ 16.9s.
- Full acceptance suite
  clean-DB: **18 passed @
  25.9s**.

## §5.d authoring notes (M24.3 in-scope small fixes)

None. Referral journey
passed on first attempt.
One Vitest test-data bug
surfaced during authoring
of `<ReferralLeadFormExtras>`
tests (default `email`
field in `makeLead()`
leaked into un-overridden
test rows, causing a
subset-mismatch assertion
to fail) — fixed by
explicit email overrides
in each test lead. That
was a test-authoring bug,
not an operator-surface
gap.

## Load-bearing decisions honored

**§5.a** — target unchanged
(Sales Operational Entry).

**§5.b** (revised at M24.1
open, locked) — referral
Dialog CTA sibling to
walk-in + phone.
`<ReferralLeadFormExtras>`
in the extras slot with
"Referring customer
(existing lead)" language
per plan; optional field
per backend nullability.

**§5.c** — journey in
`acceptance/journeys/sales_manager/`
folder as planned.

**§5.d** (revised at M24.1
open, Option C) — referral
row shipped: intake with
picker → list channel
visibility → modal →
assign. API-side referrer
FK assertion (not modal-
side display — deferred
per §3 deferral 13).

**§5.e** — no seed changes
(M24.1's seed covers
Priya).

**§5.f** — journey-as-
verifier. First-pass zero
operator-surface fixes.

**§5.g** — opportunistic
testids. Added:
`sales-leads-add-referral`,
`sales-leads-referral-dialog`,
`referral-lead-form-extras*`
(8 sub-testids on the
picker component).

**§5.h** (revised at M24.1
open, Option B) — M24.3
scope per plan
(`<ReferralLeadFormExtras>`
+ referral Dialog CTA +
journey).

## Streak

**Planning-time as-
recommended streak: 0**
(unchanged since M24.0
reset).

**Zero-drift permission-
class streak: still 23
consecutive milestones**
(M10 → M23) at M24.3
close. Streak target at
M24.5 close: 24.

## What's next: SESSION_184 M24.4 webhook integration-to-operator journey

Per MILESTONE_24_PLANNING.md
§7 M24.4:

- **No new UI component.**
  No `<WebhookIntakeForm>`.
  No `+ Webhook` CTA per
  M24.0 → M24.1-open
  webhook posture redirect
  (webhook is a system-to-
  system integration
  mechanism, not an
  operator-created lead
  source).
- **No new backend
  surface.** Uses shipped
  `/admin/leads/webhook/`
  endpoint + shipped
  `generic` adapter.
- **Seed extension:** no
  new fixtures required
  (M24.1's seed already
  covers persona +
  advisor).
- **New journey**
  `acceptance/journeys/sales_manager/webhook_integration_intake.spec.ts`:
  1. `test.beforeEach`:
     APIRequestContext
     POSTs to real
     `/api/dealer-ai/admin/leads/webhook/`
     with
     `platform="generic"`
     + realistic dealer-
     owned envelope
     (`full_name`,
     `phone`, `email`,
     `message`, budget
     hints per the shipped
     generic adapter's
     documented envelope
     at
     `webhook_adapters/generic.py:14`).
  2. Login as
     salesperson (via
     storage state).
  3. Navigate to
     `/dealer-ai-sales/leads`
     with `channel` filter
     set to
     `listing_form`.
  4. Assert the ingested
     lead appears in the
     filtered list with
     correct
     `channel="listing_form"`
     attribution.
  5. Open the row via
     click →
     `LeadDetailModal`.
  6. Assign Acceptance
     Advisor via
     AssignmentDropdown.
  7. Business-outcome
     assertion via admin
     API: assigned +
     `channel="listing_form"`.
- **Small operator-
  surface gap fixes**
  per §5.d (rare — the
  browser-side flow
  uses shipped UI
  unchanged; only setup
  hits the API).
- **Session handoff** at
  `docs/handoffs/SESSION_184_m24_inc4_webhook.md`.
- **`00-START-NEXT-SESSION.md`**
  refreshed for M24.5.

**Backend baseline target
at M24.4 close:** 4,780 →
4,780 (unchanged; no code
change). Frontend Vitest:
209 → 209 (unchanged;
journey-only). Acceptance
suite (clean-DB): 18 →
**19**.

**Collapse condition:**
if M24.4's journey-only
work is small enough that
no in-scope §5.d fixes
surface, M24.4 may fold
into M24.5 close-out per
§5.h Option B evidence-
sized posture.

## What lands at M24.5 (SESSION_185, or SESSION_184 if M24.4 folds) — close-out

CI validation + capability
matrix + retrospective + M25
skeleton + coordinated push.

## Non-goals for the remaining M24 increments

Unchanged from §9:
- ❌ No manual webhook UI.
- ❌ No test-drive UI
  (M25).
- ❌ No referrer / platform
  display in modal (M25).
- ❌ No new routes /
  endpoints / carriers /
  migrations / permission
  classes.
- ❌ No individual per-
  increment pushes.

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
11. `docs/handoffs/SESSION_181_m24_inc1_walk_in.md`
12. `docs/handoffs/SESSION_180_m24_inc0_planning.md`
