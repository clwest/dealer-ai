---
title: "Milestone 24 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-03
sessions: SESSION_180 → SESSION_184
milestone: 24
milestone_name: "Sales Operational Entry"
related:
  - docs/roadmap/MILESTONE_24_PLANNING.md
  - docs/roadmap/MILESTONE_23_RETROSPECTIVE.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7y
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 24
---

# Milestone 24 — Retrospective

Written at Milestone 24 close
(SESSION_184). Records what was
planned, what shipped, what deviated
and why, and lessons carried forward
for Milestone 25 and beyond. Mirrors
the `MILESTONE_23_RETROSPECTIVE.md`
structure so milestone history remains
directly comparable.

## 1. Planned scope

`MILESTONE_24_PLANNING.md` at
SESSION_179 close (skeleton) and
SESSION_180 (full active memo) —
subsequently corrected at SESSION_181
open per user direction — defined the
milestone as **Sales Operational
Entry** — Candidate O2 sub-scope
(lead-source-specific intake)
identified via the primary
operational-coverage lens established
at M22 close.

Framing refined at M24.0 open per
user direction, from "Sales Intake
Bundle" (four independent forms) to
"Sales Operational Entry" (one
operational workflow with four
channel-specific entry points). Three
operator-created intake paths (walk-
in, phone, referral) + one
integration-to-operator path (webhook
via shipped `generic` adapter). Anchor
business question: *Can a salesperson
begin their entire workflow inside
the platform from the very first
customer interaction across all four
intake channels?*

Governing contract inherited from M21
Candidate O UI-creation shape: every
M24 surface (a) maps to shipped
backend + missing frontend, (b) closes
a missing operator-facing UI OR
validates a missing integration-to-
operator flow, (c) adds a Playwright
operational journey, (d) not generic
UX polish.

Eight §5 load-bearing decisions
resolved at M24.0 open. §5.a + §5.c +
§5.e + §5.f + §5.g + §5.h confirmed
as-recommended. §5.b + §5.d
**redirected before M24.0 lock** on
the webhook operator-UI posture
(webhook is a system-to-system
integration boundary, not a
salesperson-created lead source). §5.b
+ §5.d + §5.h **revised again at
M24.1 open** per user direction after
empirical UI substrate verification
surfaced (a) route path mismatch and
(b) downstream verb UI substrate gap.

## 2. What actually shipped

**Five increments across five
sessions** (SESSION_180 → SESSION_184)
— M24.4 folded into M24.5 close-out
per §5.h Option B evidence-sized
collapse posture (webhook journey was
journey-only with zero in-scope §5.d
operator-surface fixes; the CSRF
header adjustment was a test-authoring
choice, not an operator-surface bug).
Five sessions covered six logical
increments: M24.0 planning + M24.0
correction (both SESSION_180 and
SESSION_181-open respectively) + M24.1
walk-in + M24.2 phone + M24.3
referral + M24.4/M24.5 combined
close-out.

### M24.0 — Planning refinement + target selection (SESSION_180)

Full memo expansion + all 8 §5
decisions resolved. Candidate O2
(lead-source-specific intake)
confirmed at open per operational-
coverage lens. Framing refined from
"Sales Intake Bundle" to "Sales
Operational Entry" per user
direction. **§5.b + §5.d redirected
before lock** on the webhook
operator-UI posture. Repository
evidence
(`webhook_adapters/generic.py:14`
docstring) confirmed redirect —
envelope is described as one that
"platform integrations map into,"
not one operators author. **Streak
RESET TO 0** at open — historical
run of 89 across fourteen
consecutive milestones (M10 → M23)
preserved for the record; not
extended.

### M24.0 correction (SESSION_181 open, before M24.1 implementation)

Empirical UI substrate verification
before any implementation code was
authored surfaced two evidence-
based mismatches:

1. **Route path mismatch.** M24.0
   memo/handoff/next-session file
   referenced
   `/dealer-ai/sales/leads/<id>`
   as the post-create redirect
   target. Real route is
   `/dealer-ai-sales/leads`
   (hyphen; no `:id` sub-route);
   no dedicated sales-side lead
   detail page exists.

2. **Downstream verb UI substrate
   gap.** M24.0 §5.d assumed
   downstream operator UI existed
   for assign + schedule test
   drive + start cadence +
   attribution display + platform
   display. Verification showed
   only assign (via in-scope
   `LeadDetailModal` wire-in) and
   cadence (already shipped) are
   actually reachable today.

**Revised decisions locked at M24.1
open** per user direction and the
M23 §5.d durable "small in-scope
fix vs. large deferred" posture:

- **§5.b revised.** Post-create
  opens `LeadDetailModal` on the
  same page (no redirect; no new
  route). `LeadDetailModal` +
  `AssignmentDropdown` wired into
  `DealerAiSalesLeads` as an
  M24.1 in-scope extension.
- **§5.d revised.** Common core
  across all four channels: intake
  → list channel visibility →
  modal → assign. Phone additionally
  navigates to follow-ups and
  creates a 24hr cadence via
  existing `CadenceConfigPanel`.
  Walk-in / referral / webhook
  stop at assign.
- **§5.h revised.** M24.1
  completion contract expanded to
  include `LeadDetailModal` +
  `AssignmentDropdown` wire-in.
- **§3 deferrals added:** (12)
  `<RecordTestDriveForm>` +
  attachment; (13) `referrer_id`
  display in modal; (14) platform
  display in modal. All three
  elevated to M25 candidates with
  explicit re-entry paths.

**Streak accounting.** Streak
stayed at 0 (not further reset;
not extended). Both corrections
recorded honestly. **Durable
lesson strengthened for M25+:**
planning-open verification must
cover both intake AND downstream
UI surfaces before locking §5.b +
§5.d for any UI-creation
milestone.

Committed separately as `75752f1`
before any M24.1 implementation
code.

### M24.1 — Shared intake substrate + walk-in UI + LeadDetailModal wire-in + walk-in journey (SESSION_181)

Shipped:
- `<LeadIntakeForm>` shared
  component parameterized by
  `channel`; 9 base fields
  matching backend
  `_BaseIntakeSerializer` verbatim;
  optional `extras` slot for
  referral picker; onSubmit
  callback pattern; 8 Vitest
  tests.
- `+ Walk-in` Dialog CTA on
  `DealerAiSalesLeads.tsx`;
  post-create closes intake
  Dialog + opens `LeadDetailModal`
  + reloads list.
- `LeadDetailModal` +
  `AssignmentDropdown` wired
  into `DealerAiSalesLeads` as
  an M24.1 in-scope extension
  (~30-line addition) — the
  modal wasn't previously wired
  into the sales-side leads
  page (only the older
  `/dealer-ai-leads` admin
  surface).
- New
  `seed_journey_sales_operational_entry`
  management command with
  session-safe `set_password`
  guarding per M23.2 durable
  memory; `--reset` deletes
  fixture + clears role +
  deactivates advisor.
- New Playwright journey
  `walk_in_intake.spec.ts`:
  navigate → click + Walk-in →
  fill form → submit → modal
  opens → extract new lead id
  → assign Acceptance Advisor
  → business-outcome API
  assertion → reload → list
  row shows channel.

**Journey-authoring adjustment:**
first walk-in journey attempt
hit Playwright strict-mode Close-
button collision inside the modal
region (`AssignmentDropdown` has
its own Close in addition to
`LeadDetailModal`'s outer Close).
Fixed by reordering steps —
business-outcome API assertion
first, then `page.reload()` to
dismiss modal + confirm assignment
persists. Journey-authoring
choice, not an operator UI bug.

**Test-hygiene finding (Candidate
H reinforcement).** First pass of
the full acceptance suite on a
state-dirty DB (already mutated
by isolated walk-in journey runs
earlier in the session) surfaced
3 pre-existing failing journeys
(`sales_manager/daily_startup`,
`recon/workflow`,
`office/accounting_workflow`) due
to non-idempotent assertions on
shared DB state (e.g.
`expect(seededLead.assigned_to).toBeNull()`
when prior runs already assigned
the lead). Clean-DB re-run
passed all 16. Confirms pre-
existing test-hygiene issue
documented as M22 §9
`feedback_avoid_exact_count_locks_in_tests`
+ M23 §9 Candidate H. Elevated
as M25 candidate. M24.1
introduced no regressions.

Backend baseline unchanged (4,780;
seed has no Django test). Vitest
193 → 201 (+8). Acceptance 9 →
10.

### M24.2 — Phone UI + cadence journey (SESSION_182)

Shipped:
- `+ Phone` Dialog CTA on
  `DealerAiSalesLeads.tsx`
  sibling to walk-in. Reuses
  `<LeadIntakeForm>` with
  `channel="phone"` +
  `createPhoneLead` — no new
  component work.
- New Playwright journey
  `phone_intake.spec.ts`:
  intake → modal → assign →
  business-outcome API →
  reload → list row shows
  channel → navigate to
  follow-ups → fill
  `CadenceConfigPanel`
  `CreateCadenceForm` with new
  lead id + `24hr` template →
  submit → extract new cadence
  id → business-outcome API:
  at least one follow-up task
  spawned for the new cadence
  (proves cadence engine ran,
  not just row rendered).

**Sibling-pattern discipline paid
off — first-run pass, zero
§5.d fixes needed, zero new
component work.** Phone Dialog
CTA is a pure reuse of the
walk-in shape.

Backend baseline unchanged.
Vitest unchanged (M24.1 tests
already cover phone).
Acceptance 10 → 11.

### M24.3 — Referral UI + referring-customer picker + journey (SESSION_183)

Shipped:
- `<ReferralLeadFormExtras>`
  controlled component;
  fetches tenant-scoped leads
  on mount via
  `fetchAdminLeads({ limit: 200 })`;
  filters client-side by
  name/phone/email substring;
  top 10 matches render as
  clickable rows; optional
  per backend nullability;
  "Unselect" clears to null;
  8 Vitest tests.
- `+ Referral` Dialog CTA on
  `DealerAiSalesLeads.tsx`
  composing
  `<LeadIntakeForm
  channel="referral">` with
  `<ReferralLeadFormExtras>`
  in the extras slot. Dialog
  `onOpenChange` resets
  `referrerLeadId` to null on
  close.
- New Playwright journey
  `referral_intake.spec.ts`:
  look up Priya's id via
  `findSeededLead` → click
  + Referral → search "Priya"
  → click her match → assert
  selected chip → fill form →
  submit → modal → assign →
  **business-outcome API
  assertion: `referrer` FK
  matches Priya's id** +
  `channel="referral"` +
  assigned to Acceptance
  Advisor. **No modal-side
  referrer-display assertion**
  per M24.1-open direction —
  deferred per §3 deferral 13
  as genuinely-missing UI.

**Journey-authoring
adjustment:** one Vitest
test-data bug (default email
leaked through un-overridden
test leads causing subset-
mismatch assertion) fixed
with explicit email overrides.
Not an operator-surface bug.

Backend baseline unchanged.
Vitest 201 → 209 (+8).
Acceptance 11 → 12.

### M24.4 (folded with M24.5) — Webhook integration-to-operator journey + close-out (SESSION_184)

Shipped:
- New Playwright journey
  `webhook_integration_intake.spec.ts`:
  `test.beforeEach` POSTs to
  real
  `/api/dealer-ai/admin/leads/webhook/`
  with `platform="generic"` +
  realistic dealer-owned
  envelope; captures new lead
  id from 201 response. Then
  navigates as salesperson,
  filters list by
  `channel="listing_form"`,
  asserts ingested lead row
  appears with correct channel,
  clicks row → modal opens →
  assigns Acceptance Advisor →
  business-outcome API
  assertion. **No new UI
  component.** No `+ Webhook`
  operator CTA. No
  `<WebhookIntakeForm>`. Uses
  shipped `generic` adapter +
  shipped webhook endpoint +
  shipped operator UI + M24.1
  modal wire-in.
- Close-out artifacts:
  CAPABILITY_MATRIX §7y +
  MILESTONE_24_RETROSPECTIVE
  (this file) +
  MILESTONE_25_PLANNING skeleton
  + IMPLEMENTATION_ROADMAP M24
  section + coordinated close-
  out commit + first M24 push.

**Journey-authoring
adjustment:** initial webhook
POST returned 403 (DRF
SessionAuthentication enforces
CSRF on unsafe methods). Fixed
by reusing the shipped
frontend pattern
(`frontend/src/lib/authFetch.ts:84-86`)
— read `csrftoken` cookie out
of the persona's storage state
+ pass as `X-CSRFToken`
header. Test-authoring choice,
not an operator-surface bug.

M24.4 folded into M24.5
close-out per §5.h Option B
evidence-sized collapse posture
— journey-only work with no
in-scope §5.d operator-surface
fixes.

Backend baseline unchanged.
Vitest unchanged. Acceptance
12 → 13.

## 3. Deviations vs. planning memo

**Two mid-milestone planning
corrections** — both recorded
honestly rather than reclassified
to preserve the planning-time as-
recommended streak.

### Deviation 1 — M24.0 webhook operator-UI posture (§5.b + §5.d)

**Planned:** original
recommendation included a `+
Webhook` operator CTA and a
`<WebhookIntakeForm>` with
curated demo payloads.

**Actual:** redirected before
M24.0 lock per user direction.
Webhook is a system-to-system
integration boundary, not a
salesperson-created lead source.
Repository evidence
(`webhook_adapters/generic.py:14`
docstring; `_ADAPTERS` registry;
zero repository/research-corpus
evidence for manual operator
webhook payload entry)
contradicted the initial
recommendation.

**Reason:** initial framing
treated webhook as symmetrically-
shaped with walk-in/phone/referral;
empirical review of the shipped
adapter's documented envelope
made the asymmetry clear. User
correctly flagged before lock.

**Impact:** streak reset to 0 at
open. Revised §5.b + §5.d locked
"three operator Dialog CTAs +
one integration-to-operator
journey" shape.

### Deviation 2 — M24.1-open downstream-verb UI substrate gap (§5.b + §5.d + §5.h)

**Planned:** M24.0 §5.d promised
per-channel handoffs assuming
shipped downstream UI existed
for: assign, schedule test drive,
start cadence, referrer
attribution display, platform
display.

**Actual:** empirical UI substrate
verification at M24.1 open showed
only assign (via M24.1 in-scope
`LeadDetailModal` wire-in) and
cadence (already shipped) are
actually reachable. Test-drive
creation UI absent per M11.6
explicit deferral. Referrer_id
display absent in
`LeadDetailModal`. Platform
display absent. Additionally,
route path
`/dealer-ai/sales/leads/<id>`
does not exist (real route is
`/dealer-ai-sales/leads` with no
`:id` sub-route).

**Reason:** M24.0 planning
verified the intake side (four
endpoints, wrappers, referrer
contract, webhook adapter
registry) but did NOT verify the
downstream verb UI substrate.
Route path was assumed rather
than grep-verified.

**Impact:** streak stayed at 0
(not further reset). §5.b + §5.d
+ §5.h revised. Three §3
deferrals added (test-drive UI,
referrer display, platform
display) as M25 candidates.
**Durable lesson strengthened for
M25+:** planning-open
verification must cover both
intake AND downstream UI
surfaces before locking §5.b +
§5.d for any UI-creation
milestone.

### Deviation 3 — M24.4 folded into M24.5 close-out

**Planned:** §5.h Option B
sequencing allowed 5-to-6
increments with collapse if
warranted.

**Actual:** M24.4 (webhook
journey-only work) landed
cleanly with no in-scope §5.d
operator-surface fixes. Folded
into M24.5 close-out in the
same session per §5.h Option B
evidence-sized collapse posture.

**Reason:** by design.

**Impact:** total sessions 5
(SESSION_180 → SESSION_184)
covering 6 logical increments.
No regression; no rework
required.

## 4. Deferrals reviewed

Fourteen §3 deferrals catalogued
in the planning memo. Three
added at M24.1 open per the
downstream-verb correction. All
remain valid at M24 close.

**Reviewed at M24 close:**

1. **Manual webhook payload
   entry UI** — deferred
   without scheduled re-entry.
   Rationale unchanged.
2. **New backend service
   verbs / endpoints / carriers
   / migrations / permission
   classes / frontend routes**
   — zero of each shipped in
   M24. Governing-contract
   fit clean.
3. **Named-platform webhook
   adapters** — future work.
4. **Referral incentive
   payout logic** — deferred
   from M11 §2. Unchanged.
5. **Salesperson-authored
   lead search / filter
   enhancements** —
   `<ReferralLeadFormExtras>`'s
   client-side substring filter
   is sufficient for typical
   dealership scale; server-
   side name-search endpoint
   remains a future M25+
   candidate if evidence
   surfaces.
6. **Deal writeup lifecycle /
   test-drive creation UI
   beyond walk-in journey /
   F&I substrate / JE creation
   UI / other O2 sub-scopes**
   — all remain in the O2
   pool for M25+ selection.
7. **Full-coverage testid
   pass** — opportunistic-
   only stayed sufficient.
8. **Manual pre-verification
   before authoring journey**
   — journey-as-verifier
   posture held. Two
   authoring adjustments
   (Close-button strict-mode,
   CSRF POST) resolved
   inline.
9. **Splitting the M24 seed
   into per-channel seeds** —
   single seed sufficed for
   all four journeys.
10. **Force-scoping larger
    discovered gaps into M24**
    — three genuine gaps
    surfaced (test-drive UI,
    referrer display, platform
    display); all deferred to
    M25 with re-entry paths
    per §3.
11. **Individual per-increment
    pushes** — coordinated
    push held at M24.5.
12. **`<RecordTestDriveForm>`
    component + attachment**
    (NEW at M24.1 open) —
    genuinely-missing UI
    surface; M25 Candidate O2
    sub-scope.
13. **`referrer_id` / "Referred
    by" display in
    `LeadDetailModal`** (NEW
    at M24.1 open) — small
    UI extension; M25
    candidate. Would
    strengthen the M24.3
    referral journey's
    downstream assertion
    from API-side to modal-
    side.
14. **`platform` display in
    `LeadDetailModal` for
    webhook-origin leads**
    (NEW at M24.1 open) —
    small UI extension; bundle
    with #13.

**Test-hygiene Candidate H
reinforcement (surfaced at
M24.1 close):** three pre-
existing shared-DB non-
idempotent journeys
(`sales_manager/daily_startup`,
`recon/workflow`,
`office/accounting_workflow`)
fail on state-dirty full-suite
runs; clean-DB runs pass all
13. Elevated as M25 candidate
for operational-coverage-
compounding value of a stable
full-suite baseline.

## 5. Lessons learned

### Lesson 1 — Sibling-pattern discipline compounds forward

M24.1 shipped `<LeadIntakeForm>`
as a shared substrate. M24.2
phone was a pure reuse — same
Dialog shape, same shared form,
different channel prop, different
wrapper. Zero new component
work. **First-run pass, zero
§5.d fixes needed.**

M24.3 referral extended the
substrate via the extras slot
pattern rather than re-writing
the base form. `<ReferralLeadFormExtras>`
is a small delta, composed
cleanly. **First-attempt pass on
the operator-facing journey.**

**Carry-forward:** first-of-a-
kind work (M24.1) invests in
substrate that subsequent
increments inherit. Compound
value across M24.2/M24.3 was
significant (M24.2 shipped
zero-new-component; M24.3
shipped small extension).
Continues M23 durable-lesson
memory `feedback_playwright_as_operational_contract`
+ `sibling-pattern-discipline`.

### Lesson 2 — Downstream-verb UI substrate verification is mandatory at planning-open

M24.0 planning verified the
intake side (four endpoints,
wrappers, referrer contract,
webhook adapter registry) but
did not verify the downstream
verb UI substrate. Result: §5.b
+ §5.d assumed shipped UI that
did not exist (test-drive
creation UI, referrer display,
platform display).

M24.1-open correction resolved
it before any implementation
code shipped, but the correction
cost a planning revision on §5.b
+ §5.d + §5.h and reset the
planning-time streak to 0.

**Carry-forward:** M25+
planning-open checklists MUST
cover BOTH intake AND downstream
UI surfaces before locking §5.b
+ §5.d for any UI-creation
milestone. This is now
`feedback_verify_downstream_ui_at_planning_open`
durable memory alongside the
existing M22
`feedback_verify_prior_recommendations_at_planning_open`.

### Lesson 3 — Record planning corrections honestly

The user directed at both M24.0
and M24.1 open: record planning
corrections honestly rather than
reclassify them to preserve the
planning-time as-recommended
streak. Streak reset to 0 at
M24.0; stayed at 0 through
M24.1-open correction.

**Result:** governance record is
truthful. Future planning-open
checklists can use the M24
corrections as evidence for the
verification-must-cover-both-
sides lesson. Reclassification
would have hidden the compound
learning value.

**Carry-forward:**
`feedback_record_planning_redirects_honestly`
durable memory added — streak
integrity beats streak count.

### Lesson 4 — Test-authoring adjustments vs. operator-surface fixes are distinct §5.d classes

Three test-authoring adjustments
landed in M24 (Close-button
strict-mode in M24.1, Vitest
test-data bug in M24.3, CSRF
POST in M24.4). None of these
was an operator-surface bug —
each was a Playwright/Vitest
authoring choice inherited from
the shipped frontend's own
patterns.

**Carry-forward:** classify §5.d
adjustments by kind in future
retrospectives. Test-authoring
adjustments are cost-of-doing-
Playwright, not operator-facing
gaps. Only surface-level fixes
should be attributed to §5.d
operator-surface work.

### Lesson 5 — Attribution assertions gate on truthful UI display

The user directed at M24.1 open:
"retain attribution assertions
only if the existing lead-detail
UI truthfully displays those
fields. Otherwise validate
creation, source/channel
persistence, detail visibility,
and assignment, and document
the missing attribution
presentation separately."

M24.3 referral journey applied
this cleanly: `referrer` FK
attribution asserted via admin
API (backend contract preserved),
NOT via `LeadDetailModal`
display (deferred per §3
deferral 13). M24.4 webhook
journey similarly asserted
`channel="listing_form"` in the
list column but did NOT assert
platform="generic" anywhere in
the UI (platform display
deferred per §3 deferral 14).

**Carry-forward:** journeys
should never assert on UI
display that doesn't ship —
attribution goes to API-side
assertion + explicit §3
deferral for the display gap.

### Lesson 6 — Session-safe seed pattern applied from the start

M24.1's
`seed_journey_sales_operational_entry`
inherited the M23.2 durable
session-safe `set_password`
guarding from the start —
newly-created users get
`set_password` on first
provisioning; existing users
retain their session hashes
across re-invocations. Zero
session-invalidation bugs in
M24.

**Carry-forward:** M23.2's
durable lesson is now
consistently applied. Every
new seed command in M24+
uses the guard from day one.

## 6. Streak status

**Planning-time as-recommended
streak: RESET TO 0 at M24.0
open** on the webhook operator-
UI redirect. **Stayed at 0
through M24.1-open correction**
on the downstream-verb UI
substrate gap.

Historical run at M24.0 open
(immediately before the reset):
89 planning-time as-recommended
M5.1 → M23.0 across fourteen
consecutive milestones (M10 →
M23). **Preserved for the
record; not extended.**

**Zero-drift permission-class
streak: extends twenty-three →
twenty-four consecutive
milestones** (M10 → M24). All
four M24 intake endpoints reuse
`IsSalesManagerOrOwnerAtActiveDealership`
(existing M4 class). Zero new
permission classes.

Historical §5 counts through
M24.0:
- M10 through M17: 6 decisions
  each = 48.
- M18: 7 decisions.
- M19: 8 decisions.
- M20: 8 decisions.
- M21: 8 decisions.
- M22: 8 decisions.
- M23: 8 decisions.
- M24: 8 decisions (§5.a
  target + §5.b–§5.h).
- Total across fifteen
  milestones (M10–M24):
  48 + 7 + 8 + 8 + 8 + 8 + 8
  + 8 = **103 §5 decisions**.

Post-M24.0 (at open) counter: 6
as-recommended (§5.a + §5.c +
§5.e + §5.f + §5.g + §5.h), 2
redirected (§5.b + §5.d). At
M24.1 open, 3 further revised
(§5.b + §5.d + §5.h). New
streak counter begins fresh at
M25.0.

## 7. Governing-contract validation

M21 Candidate O UI-creation
contract inherited by M24 held
across all three operator-
created channels + the webhook
integration variant:

| Condition | Walk-in (M24.1) | Phone (M24.2) | Referral (M24.3) | Webhook (M24.4) |
| --- | --- | --- | --- | --- |
| (a) Maps to shipped backend | ✓ (M11.1) | ✓ (M11.1) | ✓ (M11.1) | ✓ (M11.1) |
| (b) Closes missing operator-facing UI OR validates missing integration-to-operator flow | ✓ closes UI | ✓ closes UI | ✓ closes UI | ✓ validates integration |
| (c) Adds Playwright operational journey | ✓ | ✓ | ✓ | ✓ |
| (d) Not generic UX polish | ✓ | ✓ | ✓ | ✓ |

**Contract fit is clean for all
four channels.** The webhook
channel's variant (setup outside
browser + operator handling via
real UI) preserves conditions
(a) + (c) + (d); condition (b)
uses the "integration-to-
operator flow" variant rather
than "operator-facing UI" —
which the M24 memo formalized
in the revised M24 governing-
principle language.

## 8. Corrections landed by M24 work

**M24.0 correction:** webhook
operator-UI posture redirect
before lock. §5.b + §5.d
locked "three operator Dialog
CTAs + one integration-to-
operator journey" shape.

**M24.1-open correction:**
route path fix + downstream-
verb UI substrate revision.
§5.b + §5.d + §5.h revised.
Three §3 deferrals added
(test-drive UI, referrer
display, platform display) as
M25 candidates.

**M24.1 sales-side modal wire-
in:** `LeadDetailModal` +
`AssignmentDropdown` now
reachable from
`/dealer-ai-sales/leads` (were
previously only reachable
from the older `/dealer-ai-
leads` admin surface). Small
in-scope extension (~30 lines)
per M24.1-open correction.

**Test-hygiene Candidate H
reinforcement:** M24.1 close
surfaced 3 pre-existing shared-
DB non-idempotent journeys.
Elevated as M25 candidate.
Not an M24 regression.

## 9. Standing M25 question

**Which candidate most increases
operational coverage for a
dealership employee?**

Applied at M25.0 to lock §5.a.
Candidate list at M24 close
(pool composition + priority):

### Elevated at M24 close

- **Candidate A2 (JE creation
  UI, unchanged from M24
  candidate list — NOT
  selected at M24)** — still
  the smallest-scope M25
  candidate. Single endpoint
  (`admin-journal-entry-
  create`); ships new
  wrapper + form + journey.
  Matches M23.2/M23.3
  shipping shape.
- **Candidate A3 (Lead source
  attribution display, NEW at
  M24.1-open correction)** —
  bundle §3 deferrals 13 +
  14. Small UI extensions to
  `LeadDetailModal`:
  referrer_id / "Referred by"
  display + platform display
  for webhook-origin leads.
  Would strengthen the M24.3
  referral journey's
  downstream assertion from
  API-side to modal-side.
  Small scope, high compound
  value across M24 journeys.
- **Candidate A4 (RecordTestDriveForm
  UI, NEW at M24.1-open
  correction)** — §3 deferral
  12. Wrapper exists since
  M11.6 but no UI consumes
  it; `DealerAiSalesTestDrives.tsx`
  is read-only. Would
  strengthen the M24.1 walk-
  in journey's downstream
  assertion (from stop-at-
  assign to schedule-test-
  drive as originally
  envisioned before M24.1-
  open correction). Small
  scope, matches M24.1
  substrate pattern.
- **Candidate H reinforcement
  (test-hygiene remediation)**
  — surfaced at M24.1 close.
  Three shared-DB non-
  idempotent journeys break
  full-suite runs. Small
  scope, high engineering-
  velocity value. Enables
  stable full-suite baseline
  for M25+ CI reliability.

### Standing candidates (unchanged from M23/M24)

- **Candidate O2 (next OSC
  iteration)** — remaining
  ~40 `defer-candidate-O2`
  endpoints. Sub-scope
  options: F&I substrate
  (large — 16 endpoints;
  warrants dedicated
  milestone-family), deal-
  writeup lifecycle (3),
  remaining accounting
  writes.
- **Candidate T (real tester
  feedback)** — gated on
  tester sessions.
- **Candidate U (hosted-demo
  substrate)** — gated on
  demo-scaling willingness.
- **Candidate L (first-live-
  pilot staging)** — gated
  on real pilot + staging
  env.
- **Candidate M (multi-
  operator support)** —
  breaks zero-drift streak
  with intent.
- **Candidate D (LLM router
  / cost caps)** — deferred
  pending evidence.
- **Candidate C (F&I
  chargeback substrate)** —
  deferred pending evidence.
- **Candidate G (dashboard
  testid hardening)** —
  deferred but stable.

### Recommendation at M25.0

Apply the primary operational-
coverage lens at open. Under
that lens:

- **A3 (Lead source attribution
  display bundle)** has the
  highest per-item operational-
  coverage delta at small
  scope — post-M24, referral
  and webhook leads exist in
  the system with correct
  backend attribution but the
  operator can't see the
  attribution in the modal.
  Every referral / webhook
  lead the salesperson opens
  is a moment where this gap
  surfaces. High frequency ×
  low scope.
- **A4 (RecordTestDriveForm
  UI)** completes the walk-in
  journey's original operational-
  entry story (create → assign
  → schedule test drive, per
  the M24.0 §5.d intent
  before the substrate
  verification). High
  frequency, small scope.
  Also enables the M24 walk-
  in journey to add a test-
  drive step retroactively.
- **A2 (JE creation UI)** —
  unchanged since M23 close.
  Small scope, single
  accounting user weekly.
  Lower frequency × person-
  count than A3/A4.
- **Candidate H (test-
  hygiene)** — engineering-
  velocity value, no direct
  operational-coverage delta.

Suggested M25.0 target under
the primary lens: **A3 (Lead
source attribution display
bundle)** as first choice,
with A4 (test-drive UI) as
close second. Both are natural
extensions of M24's substrate
+ close M24-surfaced §3
deferrals. Alternatively,
bundle A3 + A4 as a "sales
UI completeness" milestone if
scope fits. Final selection
happens at M25.0 open per
standard operational-coverage-
lens discipline.
