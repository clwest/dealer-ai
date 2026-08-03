---
title: "SESSION_180 handoff — Milestone 24 · Increment 0 (M24.0 — planning refinement + target selection)"
status: historical
type: handoff
date: 2026-08-03
session: 180
milestone: 24
milestone_status: in-progress
milestone_name: "Sales Operational Entry"
increment: 0
increment_status: shipped
commit: TBD
---

# SESSION_180 — Milestone 24 · Increment 0 (M24.0 — planning refinement + target selection)

## What shipped

Planning-only session per the M10.0
/ M11.0 / M12.0 / M13.0 / M14.0 /
M15.0 / M16.0 / M17.0 / M18.0 /
M19.0 / M20.0 / M21.0 / M22.0 /
M23.0 precedent. Full memo
expansion from the M23.4 skeleton +
all **eight** §5 load-bearing
decisions resolved at open.

**§5.a → O2 (lead-source-specific
intake sub-scope) confirmed at
open** per the primary operational-
coverage lens ("which candidate
most increases operational coverage
for a dealership employee?").
Applied independently against the
freshly regenerated audit artifact
(153 endpoints, 110 covered, 43
backend-only). Recommendation
diverged from the SESSION_179
skeleton's elevated ranking
(Candidate A2 JE creation UI); the
operational-coverage lens ranked
lead-source intake above JE
creation on frequency × population
served (~10–20 sales users daily
× multi-hourly at peak vs. 1–2
accounting users weekly).

**Framing refined at M24.0 open**
from "Sales Intake Bundle" (four
independent forms) to **"Sales
Operational Entry"** (one
operational workflow with four
channel-specific entry points).
User directed reframing: the
anchor business question is *Can
a salesperson begin their entire
workflow inside the platform from
the very first customer
interaction across all four
intake channels?* Each intake
path must (a) begin from real
UI (or real integration boundary
for webhook), (b) create a
usable lead, and (c) immediately
hand the salesperson into the
already-shipped downstream sales
workflow via at least one real
operational verb per channel.

**§5.b + §5.d REDIRECTED before
lock on the webhook operator-UI
posture.** Initial
recommendation included a
`+ Webhook` operator CTA and a
`<WebhookIntakeForm>` with
curated demo payloads. User
corrected: webhook is a system-
to-system integration mechanism,
not a salesperson-created lead
source. Repository evidence
confirmed the correction —
`webhook_adapters/generic.py`
docstring describes the envelope
as one that "platform
integrations map into," and
zero repository or research-
corpus evidence supports manual
operator webhook payload entry.

**Revised webhook posture (locked
at §5.d Option B):**

- Playwright setup step (outside
  browser) POSTs to real
  `/admin/leads/webhook/` with
  `platform="generic"` +
  realistic dealer-owned envelope.
- Journey then opens the
  browser as salesperson.
- Asserts ingested lead appears
  in the salesperson's leads
  list with correct
  platform/channel attribution
  (`channel="listing_form"`
  filter).
- Salesperson opens lead detail
  and assigns via real UI.
- **No test-only backend
  endpoint. No fabricated
  operator workflow.** All
  dealership-operator
  interaction after ingestion
  occurs through the real UI.

**Referrer contract verification
completed at M24.0 open.**
`CustomerLead.referrer` is a self-
FK (`ForeignKey("self")`,
`SET_NULL`, `related_name="referred_leads"`)
at `backend/dealer_ai/models.py:904`.
The referring party IS modeled
as a prior `CustomerLead` — same-
tenant guard enforced by
`record_referral_lead()`;
nullable (referrals where
referrer identity lives only in
notes ship with NULL referrer
FK). **Preservation posture:**
backend contract kept as-is; UI
picker labeled **"Referring
customer (existing lead)"** —
truthful, matches operational
reality that the referrer IS an
existing customer with a lead
record. Optional in the UI to
match backend nullability. No
backend redesign inside M24.

**Webhook adapter registry
verification.** `_ADAPTERS =
{"generic": generic}` at
`backend/dealer_ai/services/leads/webhook_adapters/__init__.py:40`.
The `generic` adapter accepts a
documented dealer-owned envelope
(`full_name`, `phone`, `email`,
`message`, budget hints per
`generic.py:14`). Named
platforms (Autotrader / Cars.com
/ CarGurus / Facebook
Marketplace) are documented-as-
future, not shipped. **M24.4
webhook journey uses the
shipped `generic` adapter — no
test-only registrations
required.**

**Planning-time as-recommended
streak: RESET TO 0.** §5.b +
§5.d were meaningful redirects
based on repository evidence.
Recording this honestly is
preferable to reclassifying the
redirect merely to preserve
the counter. Historical run at
M24.0 open (immediately before
the reset): **89 planning-time
as-recommended M5.1 → M23.0**
across fourteen consecutive
milestones (M10 → M23).
Preserved for the record; not
extended.

**Governing contract inherited
from M21 (UI-creation shape).**
M24 continues the M21 Candidate
O UI-creation shape (also used
by M23). Every M24 shipped
surface (a) maps to shipped
backend + missing frontend,
(b) closes a missing operator-
facing UI OR validates a
missing integration-to-
operator flow, (c) adds a
Playwright operational journey,
(d) is not generic UX polish.

**DoD compliance verified by
construction.** M24 ships four
new Playwright operational
journeys (`walk_in_intake.spec.ts`,
`phone_intake.spec.ts`,
`referral_intake.spec.ts`,
`webhook_integration_intake.spec.ts`).
§3 of the memo names all four
journey additions explicitly.
The M21.0 §5.f Option B DoD
amendment is satisfied
intrinsically; no exception
path invoked.

**Backend baseline unchanged:**
4,780 pass, 1 skipped, 0 fail.
**Frontend Vitest baseline
unchanged:** 193 pass.
Migrations `0001`–`0048`
(unchanged). Tenancy carriers
52 (unchanged — M24 adds no
tenancy carriers). DRF admin
surface 113 (unchanged — M24
adds no endpoints). Frontend
operator routes 20 (unchanged —
M24 adds no routes; new
components attach to existing
page). Permission classes 7
(unchanged — zero-drift
streak intact at twenty-three
consecutive milestones; M24
extends to twenty-four at
close). Celery-beat task
families 10 (unchanged).
Acceptance suite 9 journeys
(unchanged — M24 grows count
to 13 at close).

## Starting-state verification (this session)

Ran the full M24.0-open
checklist per the M23.4
handoff:

- `git status` — clean.
- `git log --oneline -6` — top
  commit is `6dfdb5c` (M23
  close-out); `origin/main`
  at the same head.
- `python3 manage.py test
  dealer_ai` → **4,780 pass,
  1 skipped, 0 fail (161.8s)**.
- `python3 manage.py check`
  clean (7 pre-existing
  DecimalField `min_value`
  warnings — unrelated to M24
  scope, no new issues).
- `python3 manage.py
  makemigrations --check
  --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc
  --noEmit` clean.
- `cd frontend && npm test`
  → **193 pass** (4.65s).
- `cd acceptance && npx tsc
  --noEmit` clean.
- `redis-cli ping` → `PONG`.
- **M23 acceptance CI run
  verified green:** run
  `30840071050` (M23 shipped
  push at SESSION_179;
  workflow: `acceptance`,
  branch: `main`, event:
  `push`) completed
  **success** in 2m20s at
  2026-08-03T18:10:31Z.
  First real M23 CI run
  passed cleanly.
- **Audit regeneration:**
  ran `python3 -m
  dealer_ai.scripts.audit_operational_surface`.
  Output: **153 endpoints,
  110 covered, 43 backend-
  only** (up from 108
  covered / 45 backend-only
  reported in the M23.4
  handoff — 2 endpoints
  reclassified as covered
  post-M23.1). Fresh
  artifact written to
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`.

All green. No §0.a M24.0
amendments needed for
regressions.

## Empirical discovery during M24.0 open (informs §5.b + §5.d)

The scope-verification
performed during M24.0 open
surfaced two findings that
directly drove §5.b + §5.d
redirects:

**Finding 1: Webhook is a
system-to-system boundary,
not an operator UI target.**
Read
`backend/dealer_ai/views_leads.py`
+
`backend/dealer_ai/services/leads/channel_intake.py`
+
`backend/dealer_ai/services/leads/webhook_adapters/generic.py`.
The webhook endpoint's
serializer accepts
`{platform, payload}` where
payload is a raw platform-
native envelope. The
`generic` adapter's
docstring explicitly frames
the envelope as one that
"platform integrations map
into" — i.e., listing
platforms and dealer DR
systems POST into this
endpoint; operators do not
author payloads. Named
adapters (Autotrader,
Cars.com, CarGurus,
Facebook Marketplace) are
documented as future work
in the adapter registry
docstring but not shipped.
**No repository or
research-corpus evidence
supports manual operator
webhook payload entry.**

**Impact on §5.b + §5.d:**
initial recommendation
included a `+ Webhook`
operator CTA and a
`<WebhookIntakeForm>` with
curated demo payloads.
User correctly redirected
before lock. Revised
posture: three operator
Dialog CTAs (walk-in +
phone + referral) via
shared `<LeadIntakeForm>` +
`<ReferralLeadFormExtras>`;
one integration-to-
operator Playwright
journey exercising the
real webhook endpoint via
setup hook + validating
operator handling via
real UI.

**Finding 2: Referrer
contract is a truthful
self-FK to a prior
CustomerLead.**
`backend/dealer_ai/models.py:904`
declares
`referrer = ForeignKey("self",
on_delete=SET_NULL, null=True,
blank=True, related_name="referred_leads")`.
`record_referral_lead()` in
`services/leads/channel_intake.py:153`
enforces same-tenant guard
and raises
`CrossTenantReferrerError`
on mismatch (surfaces as
404 per fail-closed
convention). The
referring party is
genuinely modeled as an
existing `CustomerLead`
— referral incentive
payout logic deferred to
future (M11 §2 non-goal;
SET_NULL preserves
referred rows).

**Impact on §5.b:** UI
picker labeled **"Referring
customer (existing lead)"**
— truthful. Optional in
the UI to match backend
nullability. Backend
contract preserved
verbatim.

## Load-bearing decisions confirmed at M24.0 open

Eight decisions per M22 /
M23 precedent.

**§5.a — Milestone target
selection.** Candidate O2
lead-source-specific
intake sub-scope, framed
as "Sales Operational
Entry." Confirmed as-
recommended after
independent audit review.
Diverged from SESSION_179
skeleton's elevated
Candidate A2 (JE
creation UI) on
frequency × population
served under the primary
operational-coverage
lens.

**§5.b — Component
attachment plan +
shared substrate.**
**REDIRECTED before
lock.** Locked as Option
A (revised): three
operator Dialog CTAs
(`+ Walk-in`, `+ Phone`,
`+ Referral`) on
`DealerAiSalesLeads`;
shared `<LeadIntakeForm>`
parameterized by
`channel`; `<ReferralLeadFormExtras>`
adds "Referring customer
(existing lead)" picker
slot. **No `+ Webhook`
operator CTA. No
`<WebhookIntakeForm>`.**
Post-create redirect to
`/dealer-ai/sales/leads/<id>`.

**§5.c — Journey folder
+ shape.** Option A —
four sibling journeys in
`acceptance/journeys/sales_manager/`.
Confirmed as-
recommended.

**§5.d — Downstream-
handoff assertion scope
+ webhook ingestion
posture.** **REDIRECTED
before lock.** Locked as
Option B (revised):
per-channel downstream
verb realism (walk-in →
test drive; phone →
24hr cadence; referral
→ attribution
verification; webhook →
integration-to-operator
via real endpoint POST
+ real UI assignment).

**§5.e — Seed command
pattern.** Option A —
one new
`seed_journey_sales_operational_entry`
seed. Session-safe
re-invocation + lead
cleanup applied from
the start. Webhook
payload lives in the
journey's `beforeEach`
hook, not the seed
(ephemeral per run).
Confirmed as-
recommended.

**§5.f — Baseline
verification approach.**
Option B — journey-as-
verifier. Carries
forward from M22.2 /
M23. Confirmed as-
recommended.

**§5.g — Testid
hardening posture.**
Option B — opportunistic.
Carries forward from
M21 / M22 / M23.
Confirmed as-
recommended.

**§5.h — Increment
sequencing + completion
contract.** Option B —
evidence-sized 5-to-6
increments matching
user's suggested shape.
M24.0 planning
(shipped) + M24.1
shared substrate +
walk-in + M24.2 phone
+ M24.3 referral +
M24.4 webhook
integration journey +
M24.5 close-out.
Collapse possible if
M24.4 folds into
M24.5. Confirmed as-
recommended.

## Streak

**Planning-time as-
recommended streak:
RESET TO 0** at
SESSION_180 M24.0 open.
§5.b + §5.d were
redirected before lock
on the webhook
operator-UI posture per
user framing.

Historical run at M24.0
open (immediately
before the reset): **89
planning-time as-
recommended M5.1 →
M23.0** across fourteen
consecutive milestones
(M10 → M23). Preserved
for the record.

Historical §5 counts
through M24.0:

- M10 through M17: 6
  decisions each = 48.
- M18: 7 decisions.
- M19: 8 decisions.
- M20: 8 decisions.
- M21: 8 decisions.
- M22: 8 decisions.
- M23: 8 decisions.
- M24: 8 decisions
  (§5.a target + §5.b–
  §5.h).
- Total across fifteen
  milestones (M10–M24):
  48 + 7 + 8 + 8 + 8 +
  8 + 8 + 8 = **103 §5
  decisions**.

Post-M24.0 counter: 6
as-recommended
(§5.a + §5.c + §5.e +
§5.f + §5.g + §5.h),
2 redirected (§5.b +
§5.d). New streak
counter begins at 0.

**Zero-drift permission-
class streak target for
M24 close:** twenty-
three → **twenty-four**
consecutive milestones.
M24 introduces zero new
permission classes.

## What's next: SESSION_181 M24.1 shared intake substrate + walk-in UI + walk-in journey

Per `MILESTONE_24_PLANNING.md`
§7 M24.1:

- **`<LeadIntakeForm>`
  component** in
  `frontend/src/components/sales/`
  with the 9 shared
  fields, parameterized
  by `channel`, submit
  + error handling.
- **`+ Walk-in` Dialog
  CTA** attached to
  `DealerAiSalesLeads.tsx`.
- **Post-create redirect**
  to `/dealer-ai/sales/leads/<id>`.
- **Vitest coverage** for
  `<LeadIntakeForm>`
  (~5–7 tests).
- **New seed**
  `seed_journey_sales_operational_entry`
  with salesperson +
  role + tenant + target
  vehicle fixture +
  session-safe pattern +
  lead cleanup.
- **New assertion helper**
  at
  `acceptance/support/assertions/sales.ts`
  (if patterns repeat
  during authoring; else
  defer to M24.2).
- **New journey**
  `acceptance/journeys/sales_manager/walk_in_intake.spec.ts`.
- **Small operator-
  surface gap fixes**
  per §5.d inherited
  posture.
- **Session handoff** at
  `docs/handoffs/SESSION_181_m24_inc1_walk_in.md`.
- **`00-START-NEXT-SESSION.md`**
  refreshed for M24.2.

**Backend baseline target
at M24.1 close:** 4,780
→ **~4,781** (possibly
one seed-fixture test).
Frontend Vitest: 193 →
**~198–200**. Acceptance
suite: 9 → **10**.

## What lands at M24.2 (SESSION_182) — phone UI + journey

Phone specialization
reuses `<LeadIntakeForm>`
unchanged:

- **`+ Phone` Dialog
  CTA** attached to
  `DealerAiSalesLeads.tsx`.
- **`<LeadIntakeForm
  channel="phone">`**
  reuse; no new component
  work.
- **Post-create
  redirect** to
  `/dealer-ai/sales/leads/<id>`.
- **Vitest coverage** for
  channel-parameterization
  behavior (~2–3 tests
  if not already covered
  in M24.1).
- **New journey**
  `acceptance/journeys/sales_manager/phone_intake.spec.ts`
  — assign + start 24hr
  cadence downstream
  handoff.
- **Small operator-
  surface gap fixes** per
  §5.d.

Backend baseline target:
~4,781 → ~4,782.
Frontend Vitest: ~198–
200 → ~200–203.
Acceptance suite: 10 →
**11**.

## What lands at M24.3 (SESSION_183) — referral UI + journey

Referral adds the
`<ReferralLeadFormExtras>`
component:

- **`+ Referral` Dialog
  CTA** on
  `DealerAiSalesLeads.tsx`.
- **`<ReferralLeadFormExtras>`
  component** with
  "Referring customer
  (existing lead)"
  picker (queries
  `fetchAdminLeads`
  tenant-scoped;
  optional; posts as
  `referrer_lead_id`).
- **Composed with
  `<LeadIntakeForm
  channel="referral">`**.
- **Post-create
  redirect** to
  `/dealer-ai/sales/leads/<id>`.
- **Vitest coverage**
  for
  `<ReferralLeadFormExtras>`
  (~5–7 tests).
- **Seed extension:**
  add referring-customer
  lead fixture to
  `seed_journey_sales_operational_entry`.
- **New journey**
  `acceptance/journeys/sales_manager/referral_intake.spec.ts`
  — attribution link
  verified on detail.
- **Small operator-
  surface gap fixes**
  per §5.d.

Backend baseline
target: ~4,782 →
~4,783. Frontend
Vitest: ~200–203 →
~207–210. Acceptance
suite: 11 → **12**.

## What lands at M24.4 (SESSION_184) — webhook integration-to-operator journey

**No new UI
component.** Journey-
only work per §5.d:

- **No `<WebhookIntakeForm>`.
  No `+ Webhook` CTA.**
- **No new backend
  surface.** Uses
  shipped
  `/admin/leads/webhook/`
  + `generic` adapter.
- **New journey**
  `acceptance/journeys/sales_manager/webhook_integration_intake.spec.ts`:
  - `test.beforeEach`
    POSTs to real
    webhook endpoint
    with
    `platform="generic"`
    + realistic dealer-
    owned envelope.
  - Login as
    salesperson.
  - Navigate to
    `/dealer-ai/sales/leads`
    with `channel`
    filter set to
    `listing_form`.
  - Assert ingested
    lead appears with
    correct
    platform/channel
    attribution.
  - Open lead detail.
  - Assign via
    existing UI.
  - Assert assignment
    persisted.

Backend baseline
target: ~4,783 → ~4,783
(no code change).
Frontend Vitest: ~207–
210 (unchanged).
Acceptance suite: 12 →
**13**.

**Collapse condition:**
if M24.4's journey-only
work is small enough
that no in-scope §5.d
fixes surface, M24.4
may fold into M24.5
close-out per §5.h
Option B evidence-
sized posture.

## What lands at M24.5 (SESSION_185, or SESSION_184 if M24.4 folds) — close-out

- CI job validation on
  all four new journeys.
- `docs/CAPABILITY_MATRIX.md`
  §7y — M24 shipped
  surface.
- `docs/roadmap/MILESTONE_24_RETROSPECTIVE.md`
  with §8 corrections +
  §9 next-candidate.
- `docs/roadmap/MILESTONE_25_PLANNING.md`
  skeleton (status:
  draft).
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  updated with M24
  shipped status.
- `00-START-NEXT-SESSION.md`
  refreshed for M25.0.
- Coordinated close-out
  commit + push per
  M18.6 / M19.6 / M20.5
  / M21.5 / M22.4 /
  M23.4 pattern.

## Non-goals for the remaining M24 increments

Per MILESTONE_24_PLANNING.md
§3 + §9:

- ❌ Do NOT ship a
  `<WebhookIntakeForm>`
  or a `+ Webhook`
  operator CTA. Per
  §5.b + §5.d redirect.
- ❌ Do NOT create a
  test-only backend
  endpoint or fake
  operator workflow to
  make the webhook
  journey fully
  browser-driven. Per
  §5.d.
- ❌ Do NOT add new
  backend service verbs,
  DRF endpoints,
  tenancy carriers,
  migrations, permission
  classes, or frontend
  routes.
- ❌ Do NOT ship named-
  platform webhook
  adapters. Documented
  as future work in
  `webhook_adapters/__init__.py`.
- ❌ Do NOT redesign
  the `CustomerLead.referrer`
  self-FK backend
  contract inside M24.
  Preserve as-is; UI
  label uses truthful
  operator language.
- ❌ Do NOT manually
  verify workflows
  before authoring
  journeys — journey-as-
  verifier per §5.f
  Option B.
- ❌ Do NOT split the
  M24 seed into per-
  channel seeds pre-
  emptively — extend
  additively per §5.e
  Option A.
- ❌ Do NOT push M24
  commits individually
  — coordinated close-
  out push at M24.5
  per M18.6 / M19.6 /
  M20.5 / M21.5 /
  M22.4 / M23.4
  cadence.
- ❌ Do NOT force-scope
  larger discovered
  gaps into M24 —
  document as
  retrospective §9
  evidence.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M23 shipped section
   landed at M23.4)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_24_PLANNING.md`
   (this session's
   expansion target)
6. `docs/roadmap/MILESTONE_23_RETROSPECTIVE.md`
   §8 + §9 (M23
   corrections + standing
   M24 question)
7. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (M23 governing
   contract inherited by
   M24)
8. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (M21 Candidate O
   governing contract
   that M23 + M24
   inherit directly)
9. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact —
   authoritative for
   BHPH + accounting
   post-M23.1;
   authoritative for
   sales intake at
   M24.0)
10. `docs/CAPABILITY_MATRIX.md`
    §7x (M23 shipped
    surface)
