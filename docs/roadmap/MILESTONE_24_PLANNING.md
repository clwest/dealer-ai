---
title: "Milestone 24 — Sales Operational Entry"
status: active
type: planning-memo
generated: 2026-08-03
generated_at_session: SESSION_179 (skeleton), SESSION_180 (expansion)
milestone: 24
milestone_name: "Sales Operational Entry"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_23_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_23_PLANNING.md
  - docs/roadmap/MILESTONE_22_PLANNING.md
  - docs/roadmap/MILESTONE_21_PLANNING.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7x
---

# Milestone 24 — Sales Operational Entry

> **Active planning memo.** Expanded at
> SESSION_180 M24.0 open from the
> skeleton drafted at M23.4 close.
> §5.a Candidate O2 (lead-source-
> specific intake) confirmed at open
> per the primary operational-
> coverage lens, then refined by the
> user into an operational-workflow
> framing rather than a four-forms
> framing. Milestone name: **"Sales
> Operational Entry."**
>
> Before M24, dealership salesperson
> lead intake is limited to the M6
> public chat funnel plus the M11.6
> lead list read UI. Non-chat lead
> sources (walk-in, phone, referral,
> listing-platform webhook) have
> shipped backend endpoints since
> M11.1 and typed wrappers in
> `salesApi.ts` since M11.6, but no
> operator UI consumes them. Every
> non-chat lead intake today
> requires curl or Django shell.
> **M24 closes this gap for the
> three operator-created channels
> via UI-native intake and validates
> the integration-to-operator flow
> for the fourth (externally-
> created) channel via a Playwright
> journey that exercises the real
> webhook endpoint.**
>
> **The anchor business question**
> — *Can a salesperson begin their
> entire workflow inside the
> platform from the very first
> customer interaction across all
> four intake channels?* — governs
> every M24 scope decision. Each
> intake path must (a) begin from
> real UI (or real integration
> boundary for webhook), (b) create
> a usable lead, and (c)
> immediately hand the salesperson
> into the already-shipped
> downstream sales workflow via at
> least one real operational verb
> per channel (per §5.d).
>
> **M24 returns to the M21
> Candidate O UI-creation shape**
> shared with M23. Every M24
> shipped operator surface (a)
> maps to shipped backend +
> missing frontend, (b) closes a
> missing operator-facing UI, (c)
> adds a Playwright operational
> journey, (d) is not generic UX
> polish. The webhook journey
> uses a modified shape (§5.d):
> setup at the real integration
> boundary; operator handling via
> real UI.
>
> **§5.b + §5.d were redirected
> before lock at SESSION_180
> M24.0 open.** Initial
> recommendation included a
> `+ Webhook` operator CTA plus a
> `<WebhookIntakeForm>` with
> curated demo payloads. User
> corrected the framing: webhook
> is a system-to-system
> integration boundary, not a
> salesperson-created intake
> source. Repository evidence
> confirms — the shipped
> `generic` adapter's docstring
> describes it as the envelope
> that "platform integrations map
> into," and there is no
> repository or research-corpus
> evidence for manual operator
> webhook entry. Revised plan
> ships three operator forms +
> one integration-to-operator
> journey. **The planning-time
> as-recommended streak resets
> to 0.** Recording this honestly
> is preferable to reclassifying
> the redirect merely to
> preserve the counter.
>
> **M24 introduces zero new
> backend service verbs, zero new
> DRF endpoints, zero new
> frontend routes, zero new
> tenancy carriers, zero new
> migrations, zero new permission
> classes.** The zero-drift
> permission-class streak extends
> **twenty-three → twenty-four**
> consecutive milestones (M10 →
> M24). All four intake endpoints
> reuse
> `IsSalesManagerOrOwnerAtActiveDealership`
> (existing M4 permission class).
> Backend baseline growth expected
> only from new seed-fixture
> tests and possibly one or two
> new assertion-helper unit
> tests; frontend Vitest growth
> expected from two new
> components.
>
> **Eight load-bearing decisions**
> — §5.a target selection + §5.b
> component attachment plan +
> §5.c journey folder + shape +
> §5.d downstream-handoff
> assertion scope (M24-specific
> load-bearing decision replacing
> M23's audit-tool-fix slot) +
> §5.e seed command pattern +
> §5.f baseline verification
> approach + §5.g testid
> hardening posture + §5.h
> increment sequencing and
> completion contract. **§5.a +
> §5.c + §5.e + §5.f + §5.g +
> §5.h confirmed as-recommended
> at open. §5.b + §5.d redirected
> before lock** (webhook
> operator-UI posture).

## Guiding question (durable, per M22 close)

**Which candidate most increases
operational coverage for a
dealership employee?**

This lens governed §5.a target
selection at M24.0. Applied
independently against the freshly
regenerated M21_OPERATIONAL_SURFACE_AUDIT
artifact (153 endpoints, 110
covered, 43 backend-only after
M23.1 fix), the audit-fresh
recommendation was Candidate O2
sub-scope "lead-source-specific
intake" (4 endpoints, wrappers
already existing in `salesApi.ts`,
front-of-funnel, highest
frequency × population served
delta of the O2 pool).

The user refined the framing at
M24.0 from "sales intake bundle"
(4 forms) to "Sales Operational
Entry" (one operational workflow
with four channel-specific entry
points, each handing the
salesperson into already-shipped
downstream workflow). Framing
refinement did not change the
target endpoints or scope
boundary; it clarified that each
journey must validate real
operational continuity, not
CRUD.

The lens continues to govern any
mid-milestone scope addition or
subtraction. Endpoint count,
implementation effort, roadmap
momentum, and continuity with
prior scope are secondary
signals used to break ties
within candidates that score
comparably on operational
coverage.

## Preserve the M20–M23 operational contract (durable)

Compound guidance carried forward
through every M24 decision and
increment:

- **Evidence over assumptions.**
  Verify through the real
  application before locking
  scope. Applied at M24.0 open:
  reviewed `views_leads.py` +
  `services/leads/channel_intake.py`
  + `salesApi.ts` +
  `webhook_adapters/generic.py`
  + `models.py` referrer FK
  before locking §5.b and §5.d.
  The webhook posture redirect
  emerged directly from that
  evidence review — repository
  evidence contradicted the
  initial recommendation.
- **Operational workflow over
  endpoint count.** M24 anchor
  business question is
  operational, not enumerative.
  Four endpoints do not equal
  four independent forms; they
  equal one workflow with four
  entry points. Every §5
  decision reflects the
  workflow framing.
- **Every customer-facing
  capability extends Playwright.**
  M21.0 §5.f Option B DoD
  amendment. M24 ships four new
  operational journeys under
  `acceptance/journeys/sales_manager/`
  (see §3 DoD compliance
  section).
- **Every milestone increases
  operational coverage for
  dealership employees.** M24
  target selection applied this
  lens directly; the user's
  framing refinement
  strengthened it (workflow
  entry, not form additions).
- **Tightly bounded milestones.**
  Evidence-sized §5.h Option B
  posture allows shape to
  shrink as well as grow. M24
  target is 5 increments with
  collapse to 5 possible if
  M24.4's journey-only work
  folds into M24.5.
- **Sibling-pattern discipline
  (M23 durable lesson).** First-
  of-a-kind changes surface
  latent bugs; inherited
  patterns don't. When
  implementing, look for the
  closest existing pattern and
  follow it exactly; deviations
  require conscious
  justification. Applied in §5.b
  (in-place-page-extension per
  M17 §6 lesson 6 + M21.2 +
  M23.2/M23.3 precedent), §5.c
  (per-workflow spec files per
  M23.2), §5.e (single-seed-
  per-milestone per M23.2),
  §5.f (journey-as-verifier per
  M22.2/M23), §5.g (opportunistic
  testids per M21/M22/M23).
- **Session-invalidation seed
  pattern (M23.2 durable
  lesson).** Guard `set_password`
  calls in seed commands so
  re-invocation between
  journeys does not invalidate
  active sessions. Applied in
  §5.e from the start.

## Guiding principle (Candidate O UI-creation contract, M21 shape)

M24 inherits the M21 Candidate O
governing contract (M22 refined
it for validation-shape
milestones; M23 returned to and
proved the UI-creation shape;
M24 continues the UI-creation
shape with one channel using an
integration-to-operator variant
per §5.d). Every M24 shipped
surface must satisfy four
conditions:

1. **Maps to an already-shipped
   backend capability.** All
   four target endpoints
   (`admin-lead-walk-in-create`,
   `admin-lead-phone-create`,
   `admin-lead-referral-create`,
   `admin-lead-webhook-create`)
   ship since M11.1; wrappers
   ship in `salesApi.ts` since
   M11.6. The M24 scope closes
   the missing operator-facing
   UI (three channels) and
   validates the missing
   integration-to-operator flow
   (webhook).
2. **Closes a missing operator-
   facing UI OR validates a
   missing integration-to-
   operator flow.** Verified
   empirically at M24.0 open.
   Zero of the four intake
   endpoints have UI consumers
   in `frontend/src/pages/` or
   `frontend/src/components/sales/`.
   Wrappers exist but are
   dormant.
3. **Adds a Playwright
   operational journey.** Four
   new sibling spec files
   under
   `acceptance/journeys/sales_manager/`
   per §5.c.
4. **Is not generic UX polish.**
   Scope items map 1:1 to a
   backend verb + a missing
   form (three channels) OR to
   a backend integration
   boundary + a missing
   operator handling assertion
   (webhook). Cosmetic friction
   discovered mid-milestone
   feeds Candidate P
   (deferred), not this
   milestone.

This governing contract binds
every §5 decision, every
increment scope call, every
gap-review decision. When
these conditions conflict with
feasibility mid-milestone, the
resolution posture is to defer
the scope item to a future
milestone rather than relax
any of the four conditions.

## 0. Engineering practices to preserve from M2–M23

Full posture per M23.0 §0
(carried forward). M24-specific
notes:

- **Backend-first architecture.**
  M24 ships zero new backend
  business logic. Every UI
  action goes through an
  existing service verb via an
  existing endpoint. The
  frontend + acceptance
  workspaces are the only
  workspaces whose surface
  expands.
- **Service ownership.** Every
  UI target invokes an
  existing service verb —
  `record_walk_in_lead`,
  `record_phone_lead`,
  `record_referral_lead` (via
  the existing wrappers in
  `salesApi.ts`). No parallel
  or duplicate call paths.
- **Wrapper-only verification
  before UI writes.** Before
  M24.1 authors any UI code,
  verify each wrapper's exact
  request/response shape from
  `salesApi.ts` matches the
  backend serializer.
- **Tenant discipline.** All
  four intake endpoints
  resolve `dealership` via
  `services.tenancy.get_current_dealership`
  and pass it explicitly to
  the service verb. UI writes
  need no explicit tenant
  handling — the endpoint
  layer enforces.
- **Fail-closed responses.**
  Referral endpoint returns
  404 on cross-tenant
  `referrer_lead_id` per M2.6
  / M3.6 / M4.6 / M9.1 /
  M10.1 convention.
- **Zero-drift permission
  classes.** All four
  endpoints reuse
  `IsSalesManagerOrOwnerAtActiveDealership`.
  Streak extends 23 → 24
  consecutive milestones.
- **Decimal-as-string on the
  wire.** Money fields
  (`target_monthly_payment`,
  `down_payment`) ship as
  strings in the request
  body per M9.5 / M10.1
  convention. The wrapper
  types already reflect
  this.
- **Idempotency + cleanup on
  seed re-invocation** per
  M22.2 reversal-cleanup /
  M23.2 payment-cleanup
  pattern.
- **Sibling-pattern
  discipline (M23 durable).**

## 1. Business questions this milestone answers

The anchor question:

> **Can a salesperson begin
> their entire workflow inside
> the platform from the very
> first customer interaction
> across all four intake
> channels (walk-in, phone,
> referral, listing-platform
> webhook)?**

Broken down by channel:

1. **Walk-in.** *When a customer
   walks onto the lot, can the
   salesperson create their
   lead in the system in under
   a minute and immediately
   schedule a test drive?* M24
   answer: yes, via `+ Walk-in`
   Dialog CTA on
   `DealerAiSalesLeads` →
   shared `<LeadIntakeForm>`
   with `channel="walk_in"` →
   post-create redirect to
   `/dealer-ai/sales/leads/<id>`
   → assign + schedule test
   drive via existing UI.
   Playwright validates.

2. **Phone.** *When a customer
   calls the dealership, can
   the salesperson create their
   lead while on the phone and
   trigger the 24-hour follow-
   up cadence automatically?*
   M24 answer: yes, via
   `+ Phone` Dialog CTA →
   shared `<LeadIntakeForm>`
   with `channel="phone"` →
   post-create redirect →
   assign + start 24hr cadence
   via existing UI. Playwright
   validates.

3. **Referral.** *When an
   existing customer refers a
   friend, can the salesperson
   record the referral with
   accurate attribution to the
   referring customer's
   existing lead?* M24 answer:
   yes, via `+ Referral`
   Dialog CTA → shared
   `<LeadIntakeForm>` +
   `<ReferralLeadFormExtras>`
   with "Referring customer
   (existing lead)" picker
   (queries `fetchAdminLeads`
   tenant-scoped; optional) →
   post-create redirect →
   attribution link visible on
   lead detail. Playwright
   validates. Backend contract
   preserved: referrer is a
   self-FK to a prior
   `CustomerLead` per M11.1
   design (`models.py:904`).

4. **Webhook (listing platform
   integration).** *When an
   external listing platform
   posts a customer lead to
   the dealership's webhook
   endpoint, does that lead
   appear correctly in the
   salesperson's UI with
   proper platform/channel
   attribution, and can the
   salesperson pick it up and
   act on it?* M24 answer:
   yes, validated via
   `webhook_integration_intake.spec.ts`
   — Playwright setup step
   POSTs to real
   `/admin/leads/webhook/`
   with `platform="generic"`
   + realistic dealer-owned
   envelope; journey then
   opens the browser as
   salesperson → asserts lead
   appears under
   `channel="listing_form"`
   filter → assigns via UI.
   No manual webhook form.

Secondary questions answered
as by-products:

- Does the platform's shared
  intake substrate support a
  single reusable form
  component for the three
  channels that share the
  base 9-field envelope, with
  a specialization slot for
  referral's referrer picker?
  M24 answer: yes,
  `<LeadIntakeForm>` +
  `<ReferralLeadFormExtras>`
  per §5.b.
- Does the shipped webhook
  adapter registry
  (`_ADAPTERS = {"generic":
  generic}`) support a
  realistic integration test
  without adding a test-only
  adapter? M24 answer: yes;
  the `generic` adapter is
  the shipped surface, and
  its documented envelope is
  designed for exactly this
  use.

## 2. What existing primitives extend

**Backend (unchanged in M24).**

- `views_leads.admin_lead_walk_in_create`
  (M11.1) — endpoint reused
  as-is.
- `views_leads.admin_lead_phone_create`
  (M11.1) — endpoint reused
  as-is.
- `views_leads.admin_lead_referral_create`
  (M11.1) — endpoint reused
  as-is.
- `views_leads.admin_lead_webhook_create`
  (M11.1) — endpoint exercised
  directly by webhook journey
  setup (integration boundary).
- `services.leads.channel_intake.record_walk_in_lead`
  / `record_phone_lead` /
  `record_referral_lead` /
  `record_webhook_lead` —
  service verbs unchanged.
- `services.leads.webhook_adapters.generic.normalize`
  — shipped adapter reused
  as-is (dealer-owned
  envelope: `full_name`,
  `phone`, `email`, `message`,
  budget hints).
- `IsSalesManagerOrOwnerAtActiveDealership`
  — M4 permission class,
  reused unchanged for all
  four endpoints.
- `CustomerLead.referrer`
  self-FK (M11.1
  `models.py:904`) — backend
  contract preserved; UI
  picker posts
  `referrer_lead_id`.

**Frontend wrappers (already
exist in `salesApi.ts`).**

- `createWalkInLead(payload:
  CreateBaseLeadRequest)` —
  M11.6.
- `createPhoneLead(payload:
  CreateBaseLeadRequest)` —
  M11.6.
- `createReferralLead(payload:
  CreateReferralLeadRequest)`
  — M11.6.
- `createWebhookLead(payload:
  CreateWebhookLeadRequest)`
  — M11.6. **Not consumed by
  any operator UI in M24;
  stays in `salesApi.ts` for
  a future integration-
  console or health-check
  surface if evidence
  surfaces.**
- `fetchAdminLeads(filters)`
  — used by the referral
  picker to search existing
  leads tenant-scoped.

**Frontend pages (attachment
targets).**

- `DealerAiSalesLeads.tsx`
  (M11.6) — receives three
  Dialog CTAs (`+ Walk-in`,
  `+ Phone`, `+ Referral`).
- `/dealer-ai/sales/leads/<id>`
  (existing route) — post-
  create redirect target for
  all three operator intakes;
  also the browser landing
  point for the webhook
  integration journey after
  ingestion.

**Playwright substrate.**

- `acceptance/journeys/sales_manager/`
  folder (existing;
  currently holds
  `daily_startup.spec.ts`) —
  receives four new sibling
  spec files.
- `acceptance/support/`
  (existing) — likely gains
  a small `assertions/sales.ts`
  helper if journey code
  patterns repeat (evidence-
  sized during M24.1
  authoring).
- Existing test-fixture
  patterns from
  `seed_journey_bhph_collections_workflow`
  (M23.2 durable) provide
  the template for
  `seed_journey_sales_operational_entry`.

## 3. What's NOT in this milestone (deferrals)

Explicit non-goals with re-
entry paths preserved per
discovery rule.

1. **Manual webhook payload
   entry UI.** No `+ Webhook`
   operator CTA. No
   `<WebhookIntakeForm>`. No
   curated demo-payload
   picker. **Deferred without
   scheduled re-entry** —
   requires repository or
   research-corpus evidence
   that a real dealership
   employee needs to
   manually submit webhook
   payloads. If such evidence
   surfaces (e.g., an
   operator debugging an
   integration issue in
   production), reopen as a
   future integration-
   diagnostics candidate.

2. **New backend service
   verbs, DRF endpoints,
   tenancy carriers,
   migrations, permission
   classes, or frontend
   routes.** M24 is UI-
   creation + integration-
   validation only. Any
   discovered backend gap
   feeds Candidate C
   (deferred) or a dedicated
   future milestone.

3. **Named-platform webhook
   adapters** (Autotrader /
   Cars.com / CarGurus /
   Facebook Marketplace).
   Documented as future work
   in `webhook_adapters/__init__.py:12-15`.
   Ship only when operator
   evidence surfaces the
   platform-specific envelope
   shapes.

4. **Referral incentive
   payout logic.** Deferred
   from M11 per M11 §2.
   `CustomerLead.referrer`
   self-FK is `SET_NULL` on
   delete precisely because
   payout logic is not yet
   in scope.

5. **Salesperson-authored
   lead search / filter
   enhancements** beyond
   what already ships in
   `DealerAiSalesLeads`.
   Referral picker uses
   existing `fetchAdminLeads`
   with basic search; any
   discovered friction feeds
   Candidate G (dashboard
   testid hardening) or a
   future search-refinement
   candidate.

6. **Deal writeup lifecycle,
   test-drive creation UI
   beyond the walk-in
   journey, F&I substrate,
   JE creation UI, other
   remaining `defer-
   candidate-O2` sub-scopes.**
   All remain in the O2 pool
   for M25+ selection.

7. **Full-coverage testid
   pass on `DealerAiSalesLeads`
   or intake components.**
   Opportunistic-only per
   §5.g. Full pass remains
   Candidate G's future
   milestone shape.

8. **Manual pre-verification
   of each intake workflow
   before authoring the
   journey.** Journey-as-
   verifier per §5.f Option
   B carries forward from
   M22.2 / M23.

9. **Splitting the M24
   Playwright seed into per-
   channel seeds.** One
   shared seed per §5.e
   Option A. Splitting
   reversible if the seed
   becomes hard to reason
   about mid-milestone.

10. **Force-scoping larger
    discovered gaps into
    M24.** Any gap surfaced
    during journey authoring
    that exceeds "small in-
    scope fix" gets
    documented as
    retrospective §9
    evidence.

11. **Individual per-
    increment pushes.**
    Coordinated close-out
    push at M24.5 per M18.6
    / M19.6 / M20.5 / M21.5
    / M22.4 / M23.4
    cadence.

### DoD compliance (M21.0 §5.f Option B)

**Compliance path chosen:
Option B (add or update at
least one Playwright
operational journey).** M24
ships **four new operational
journeys** in
`acceptance/journeys/sales_manager/`:

1. `walk_in_intake.spec.ts`
2. `phone_intake.spec.ts`
3. `referral_intake.spec.ts`
4. `webhook_integration_intake.spec.ts`

Compliance is intrinsic to
the milestone shape (see
§5.h completion contract);
no exception path invoked.

## 4. What existing tests bind

**Backend tests unchanged.**
All 4,780 tests pass at
M24.0 open. No M24 code
changes affect any existing
test. New test additions
expected at M24.1–M24.4:

- Possibly one or two seed-
  fixture correctness tests
  for
  `seed_journey_sales_operational_entry`
  (mirroring M23.2's
  seed test).
- No new endpoint tests
  (endpoints unchanged).
- No new service tests
  (service verbs unchanged).
- No new permission tests
  (permission class
  unchanged).

**Frontend Vitest tests
unchanged.** All 193 tests
pass at M24.0 open. New
component tests expected at
M24.1–M24.3:

- `<LeadIntakeForm>` unit
  tests (shared component
  behavior across
  channels) — M24.1.
- `<ReferralLeadFormExtras>`
  unit tests (referrer
  picker + optional
  attribution) — M24.3.
- Estimated total growth:
  ~10–15 new tests across
  the two new components.

**Acceptance suite
unchanged.** All 9 journeys
+ 6 setup steps pass at
M24.0 open (~20.5s
baseline). Journey count
grows to 13 at M24
close.

**Type checks
unchanged.** `frontend/`
and `acceptance/` `tsc
--noEmit` both clean at
M24.0 open. No type
regressions expected —
new components use
shipped types
(`CreateBaseLeadRequest`,
`CreateReferralLeadRequest`,
`LeadProjection`) from
`salesApi.ts`.

**Migrations
unchanged.** `0001`–`0048`;
no new migrations
expected.

**Django check
unchanged.** 0 issues at
M24.0 open. The 7 pre-
existing DecimalField
warnings on
`min_value` are unrelated
to M24 scope.

## 5. Load-bearing decisions

### 5.a `[RESOLVED at SESSION_180 open]` — Milestone target selection

**Question.** Which candidate
from the M24 skeleton
(A2 / H / O2 sub-scopes /
T / U / L / M / D / C / G)
defines M24 scope?

**Decision. Candidate O2 —
lead-source-specific intake
sub-scope (4 endpoints:
walk-in, phone, referral,
webhook), framed as "Sales
Operational Entry"** per
user's refined framing.
Milestone name: **"Sales
Operational Entry."**

**Rationale.** (1) Highest
per-unit operational-
coverage delta on the
primary lens. Sales team
(~10–20 people) uses lead
intake daily, often multi-
hourly at peak — highest
frequency × population
served product in the O2
pool. Candidate A2 (JE
creation UI, 1 endpoint)
serves 1–2 accounting users
weekly and lost on the
frequency × population
comparison. (2) Front-of-
funnel position — every
downstream sales verb
(test drive, writeup, F&I,
delivery) requires a lead
first. Without UI-native
intake, sales operates
outside the product on the
first touch. (3) Wrapper
economy — all 4 wrappers
already exist in
`salesApi.ts` (M11.6);
engineering effort is UI +
journeys only. (4)
Bookend-completion pattern
— read/lifecycle side
already covered
(`admin-lead-detail`,
`admin-lead-list`,
`admin-lead-assign`,
`admin-lead-handoff`);
source-specific intake is
the missing write-side.
(5) User's framing
refinement to "Sales
Operational Entry"
strengthened the workflow
lens without changing
scope boundaries: four
endpoints → three
operator-created intake
paths + one integration-
to-operator path. (6)
Streak-neutral on
permission classes — zero
new classes; zero-drift
streak extends 23 → 24.
(7) M23-shape milestone
(evidence-sized 5-to-6
increments matching
M23.2/M23.3 shipping
shape).

### 5.b `[RESOLVED at SESSION_180 open — REDIRECTED before lock]` — Component attachment plan + shared substrate

**Question.** Where do the
intake entry points attach
in the UI, and how much of
the form component tree is
shared?

**Original recommendation
(rejected).** Four
operator Dialog CTAs on
`DealerAiSalesLeads`
including `+ Webhook` +
`<WebhookIntakeForm>` with
curated demo payloads.

**Redirect rationale
(user).** Webhook is a
system-to-system
integration mechanism, not
a salesperson-created
lead source. No repository
or research-corpus
evidence supports manual
operator webhook payload
entry.

**Repository evidence
confirming redirect.**
`webhook_adapters/generic.py`
docstring explicitly
describes the envelope as
one that "platform
integrations map into,"
not one operators author.
`_ADAPTERS` registry has
only `"generic"`; named
platforms are documented
as future work when
operator evidence
surfaces platform-specific
envelope shapes.

**Options:**

- **Option A (revised
  recommendation, LOCKED)**
  — Three operator-facing
  Dialog CTAs on
  `DealerAiSalesLeads`:
  `+ Walk-in`, `+ Phone`,
  `+ Referral`. Shared
  `<LeadIntakeForm>`
  parameterized by
  `channel` covers walk-in
  + phone + the 9 base
  fields of referral.
  `<ReferralLeadFormExtras>`
  adds the "Referring
  customer (existing
  lead)" picker slot
  (queries
  `fetchAdminLeads`
  tenant-scoped; optional;
  posts as
  `referrer_lead_id`).
  **No `+ Webhook`
  operator CTA. No
  `<WebhookIntakeForm>`.
  No manual webhook
  payload UI.** On
  successful create →
  close Dialog → redirect
  to
  `/dealer-ai/sales/leads/<id>`.
- **Option B (rejected)**
  — Four operator CTAs
  including manual
  `+ Webhook` (fails user
  framing).
- **Option C (rejected)**
  — Dedicated intake
  routes for each source
  (multiplies routes
  without justification;
  fails in-place-page-
  extension posture).

**Decision. Option A —
three operator Dialog CTAs
+ shared component + one
specialization + post-
create redirect. No
webhook operator UI.**

**Rationale.** (1) Matches
M17 §6 lesson 6 + M21.2 +
M23.2/M23.3 in-place-page-
extension posture — no
new routes; sibling-
pattern discipline
preserved. (2) `DealerAiSalesLeads`
is already the
salesperson's primary
destination — the natural
spot to *start* a lead.
(3) Shared `<LeadIntakeForm>`
mirrors backend
`_BaseIntakeSerializer`
substrate exactly (9
shared fields per
`views_leads.py:52–95`).
Referral extension is a
single optional referring-
customer picker slot.
Webhook is genuinely
different (platform +
payload dict shape) and
handled via §5.d
integration-to-operator
posture. (4) Post-create
redirect to lead detail
completes the operational-
entry framing —
salesperson lands in
downstream workflow
(assignment, test drive,
cadence, be-back all
reachable) immediately.
(5) Referring-customer UI
language ("Referring
customer (existing
lead)") preserves the
backend self-FK contract
truthfully — the referrer
IS an existing customer
lead per M11.1 design;
field remains optional in
the UI to match backend
nullability.

### 5.c `[RESOLVED at SESSION_180 open]` — Journey folder + shape

**Question.** Which folder,
and one journey per
channel or consolidated?

**Options:**

- **Option A** — Four
  sibling journeys in
  `acceptance/journeys/sales_manager/`:
  `walk_in_intake.spec.ts`,
  `phone_intake.spec.ts`,
  `referral_intake.spec.ts`,
  `webhook_integration_intake.spec.ts`.
- **Option B** — One
  consolidated
  `sales_operational_entry.spec.ts`
  exercising all four
  channels.
- **Option C** — Split by
  shape — three operator-
  form journeys +
  webhook integration
  journey in separate
  folder.

**Decision. Option A —
four sibling journeys in
`sales_manager/`, one per
intake channel** confirmed
as-recommended.

**Rationale.** (1) Matches
M23.2 §5.c Option B
precedent (per-workflow
spec files for distinct
workflows). Each intake
channel represents a
distinct operator
situation (customer
physically present vs.
inbound call vs.
referral chain vs.
external-system
ingestion). (2) Clean
failure attribution — a
phone-intake regression
does not fail the
walk-in journey. (3)
Each journey asserts a
different downstream
handoff pattern per §5.d,
so separating them lets
each journey pick the
highest-value handoff
for that channel. (4)
Consolidated (Option B)
creates a mega-journey —
slower to diagnose,
mixes concerns, longer
CI runtime. (5) Two-
folder split (Option C)
is superficial — the
webhook journey's
operator-side behavior
IS a `sales_manager`
concern; folder
placement follows
persona, not setup
mechanism. Only the
ingestion setup step
originates outside the
browser. (6)
`sales_manager/` folder
already exists
(contains
`daily_startup.spec.ts`
from M20) — natural
sibling placement.

### 5.d `[RESOLVED at SESSION_180 open — REDIRECTED before lock]` — Downstream-handoff assertion scope + webhook ingestion posture

**Question.** How far
into the downstream sales
workflow must each intake
journey reach to validate
the operational-entry
framing? And how does the
webhook integration
journey originate its
ingestion step without
inventing an operator
workflow?

**Original recommendation
(partially rejected on the
webhook row).** All four
channels asserted intake-
plus-one-downstream-verb;
webhook via
`<WebhookIntakeForm>` in
browser with curated demo
payload.

**Redirect rationale
(user).** Webhook
ingestion must originate
at the real integration
boundary because the
producer is an external
system. The journey's
setup step is allowed
outside the browser
because it represents a
system-to-system flow;
all dealership-operator
interaction after
ingestion must occur
through the real UI. No
test-only backend
endpoint. No fake
operator workflow to
force browser-driven
setup.

**Options for downstream
handoff per channel
(walk-in / phone /
referral unchanged; only
webhook redirected):**

- **Option A (minimum,
  rejected)** — Journey
  asserts lead created +
  lead visible in the
  lead list. No
  downstream verb tested.
- **Option B (revised
  recommendation,
  LOCKED)** — Per-
  channel assertion set:
  - **Walk-in:** UI
    Dialog create →
    assign → schedule
    test drive (customer
    physically present).
  - **Phone:** UI
    Dialog create →
    assign → start 24hr
    follow-up cadence.
  - **Referral:** UI
    Dialog create with
    referring-customer
    picker → attribution
    link visible on lead
    detail page.
  - **Webhook
    (integration-to-
    operator):**
    Playwright setup
    step (outside
    browser) POSTs to
    real
    `/admin/leads/webhook/`
    with
    `platform="generic"`
    + realistic dealer-
    owned envelope
    (`full_name`,
    `phone`, `email`,
    `message`, budget
    hints per shipped
    generic adapter's
    documented envelope).
    Journey then opens
    the browser as
    salesperson →
    navigates to
    `/dealer-ai/sales/leads`
    filtered on
    `channel="listing_form"`
    → asserts ingested
    lead appears with
    correct
    platform/channel
    attribution → opens
    lead detail →
    performs `assign`
    via real UI. Zero
    test-only backend
    endpoints. Zero
    fabricated operator
    workflows.
- **Option C (maximum,
  rejected)** — Full
  downstream chain per
  journey (turns each
  intake journey into a
  full-lifecycle test;
  scope creep).

**Decision. Option B —
per-channel downstream
handoff realism; webhook
uses real integration
boundary + real UI
operator handling.**

**Rationale.** (1)
Directly satisfies the
user's framing — "each
intake path must begin
from the real UI, create
a usable lead, and
immediately hand the
salesperson into the
existing operational
workflow." Option A
fails (no handoff
proven); Option C
exceeds (turns each
intake journey into a
full lifecycle test
better housed in a
dedicated lifecycle
journey). (2) Per-
channel handoff choice
reflects operator
reality — a walk-in
becomes a test drive
*now*; a phone lead
becomes a cadence; a
referral is defined by
its referrer link; a
webhook lead is defined
by platform routing.
(3) Every downstream
verb chosen is already
shipped and covered —
no new backend surface
required. (4) Ties
intake regression
coverage to
operational relevance —
a broken handoff either
way fails the journey,
matching M20–M23
operational-contract
principle. (5) `generic`
is the shipped
adapter — using it is
using shipped surface,
not test-only surface.
(6) Webhook setup
outside browser is
honest about the
producer being an
external system;
forcing it into a
browser UI would be
inventing a workflow
that does not exist.

### 5.e `[RESOLVED at SESSION_180 open]` — Seed command pattern

**Question.** One
extended seed or new
per-channel seeds?

**Options:**

- **Option A** — One
  new
  `seed_journey_sales_operational_entry`
  provisioning shared
  salesperson + role +
  tenant + target
  vehicle (for walk-in
  test drive) +
  referring-customer
  lead (for referral
  attribution). Webhook
  payload is ephemeral
  per-run → lives in
  the journey's
  `test.beforeEach`
  hook, not in the
  seed. Session-safe
  re-invocation +
  lead cleanup on
  re-invocation
  applied from the
  start per M23.2
  durable pattern.
- **Option B** — Four
  separate per-channel
  seeds.
- **Option C** —
  Extend
  `seed_journey_sales_daily_startup`
  (M20) with M24
  fixtures.

**Decision. Option A —
one new sales-
operational-entry seed**
confirmed as-
recommended.

**Rationale.** (1)
Matches M23.2 §5.e
Option A precedent
(single seed for the
whole milestone's
Playwright substrate).
All four journeys share
salesperson + tenant +
role setup; per-source
fixtures (vehicle,
referrer) are additive
within one seed. (2)
Session-invalidation
seed pattern (M23.2
§5.d durable memory)
applied from the start
— `set_password`
guarded to run only
when needed. (3) Lead
cleanup on re-
invocation mirrors
M22.2 reversal-cleanup
/ M23.2 payment-
cleanup pattern —
keeps `newest lead`
selectors
deterministic. (4)
Webhook payload lives
in the journey's
`beforeEach` hook, not
the seed — payload is
ephemeral per run and
belongs at the point
of use. Seed only
guarantees baseline
state; the webhook
journey provides its
own ingestion payload
each run. (5) Option
B creates seed sprawl.
(6) Option C tangles
M24 fixtures with M20
daily-startup —
coupling neither seed
benefits from.

### 5.f `[RESOLVED at SESSION_180 open]` — Baseline verification approach

**Question.** Manual
pre-verification of
each intake→handoff
workflow before
authoring the journey,
or journey-as-verifier?

**Options:**

- **Option A** — Manual
  pass-through per
  channel before
  authoring.
- **Option B** —
  Journey-as-verifier
  (carries forward
  from M22.2 / M23).

**Decision. Option B —
journey-as-verifier**
confirmed as-
recommended.

**Rationale.** (1)
M22.2, M23.2, M23.3
shipped clean with
journey-as-verifier
(M23.3 first-pass
zero fixes). (2) M24
UI is NEW (like
M23.2) — expect small
operator-surface gaps
to surface as
specific Playwright
assertion failures;
handle each with
"small in-scope fix
vs. large deferred"
posture inherited
from M23 §5.d. (3)
Vitest handles
component-level
correctness;
Playwright covers
full stack including
tenant discipline and
wrapper wiring. (4)
Sibling-pattern
discipline (M23
durable) — walk-in
journey ships first;
phone / referral /
webhook inherit
exactly. (5)
Playwright's fail-
loud contract
catches any
incompleteness in
the shipped
workflow as a
specific business-
outcome assertion
failure — cheaper
than manual
verification and
produces test
artifacts for
regression
detection.

### 5.g `[RESOLVED at SESSION_180 open]` — Testid hardening posture

**Question.**
Opportunistic testids
or full-coverage pass
on `DealerAiSalesLeads`?

**Options:**

- **Option A** — Full
  testid pass on
  `DealerAiSalesLeads`
  + intake components.
- **Option B** —
  Opportunistic — add
  `data-testid` only
  where new M24
  journeys need stable
  selectors.

**Decision. Option B —
opportunistic**
carries forward from
M21 §5.g + M22 + M23
practice confirmed
as-recommended.

**Rationale.** (1)
M22.2 and M23.3
shipped zero testid
additions. Shadcn /
Radix primitives +
role-based Playwright
selectors have handled
the M23 surfaces
cleanly; intake
components use the
same primitives. (2)
Full-coverage testid
pass remains
Candidate G's future
milestone shape. (3)
Preserves Rule 4
(scope discipline).
(4) Testids land at
natural insertion
points during journey
authoring — Dialog
trigger buttons, form
field inputs, submit
buttons, `+ Walk-in`
/ `+ Phone` / `+
Referral` CTAs.

### 5.h `[RESOLVED at SESSION_180 open]` — Increment sequencing + completion contract

**Question.** How are
M24 increments
sequenced, and what
does "M24 shipped"
mean?

**Options:**

- **Option A** — 4
  fixed increments.
- **Option B** —
  Evidence-sized 5-
  to-6 increments per
  user's suggested
  shape.
- **Option C** — 5
  fixed increments
  matching M23 shape.

**Decision. Option B —
evidence-sized five-
to-six increments**
confirmed as-
recommended.

Sequencing:

- **M24.0** — planning
  refinement + target
  selection (this
  session).
- **M24.1** — shared
  `<LeadIntakeForm>`
  substrate + walk-
  in specialization +
  `walk_in_intake.spec.ts`.
  First anchor —
  ships the shared
  form component
  that M24.2 + M24.3
  inherit.
- **M24.2** — phone
  specialization
  (reuses
  `<LeadIntakeForm>`
  unchanged; only
  channel + downstream
  verb differ) +
  `phone_intake.spec.ts`.
- **M24.3** —
  `<ReferralLeadFormExtras>`
  referring-customer
  picker +
  `referral_intake.spec.ts`.
- **M24.4** —
  `webhook_integration_intake.spec.ts`
  (integration-to-
  operator journey;
  no new UI
  component; setup
  POSTs to real
  endpoint per §5.d).
- **M24.5** — close-
  out. Evidence-sized
  collapse possible:
  M24.4 may fold
  into M24.5 if the
  journey-only work
  is small enough.

**Rationale.** (1)
Matches M21.h /
M22.h / M23.h Option
B posture. Fixed
increment counts
distort scope. (2)
M24.1 does double
duty — ships shared
`<LeadIntakeForm>` +
walk-in specialization
+ walk-in operational
journey. Subsequent
increments inherit
substrate (sibling-
pattern discipline;
M23 durable lesson).
(3) Phone (M24.2) is
nearly identical to
walk-in — only
channel constant +
downstream verb
differ. Small
increment. (4)
Referral (M24.3)
adds referrer picker
(small delta over
base form) +
attribution journey.
(5) Webhook (M24.4)
uses the shipped
`generic` adapter
via real integration
boundary + real UI
handling — no new
UI component. Small
increment. (6) Close
(M24.5) matches
M20.5 / M21.5 /
M22.4 / M23.4
pattern. (7)
Collapse to 5
possible if M24.4
folds into M24.5.

**Milestone completion
contract:**

- `createWalkInLead` /
  `createPhoneLead` /
  `createReferralLead`
  wrappers
  **unchanged**
  (already in
  `salesApi.ts`);
  consumed by new UI.
- `createWebhookLead`
  wrapper stays but
  is not consumed by
  operator UI in
  M24 — reserved for
  a future
  integration-console
  or health-check
  surface if evidence
  surfaces.
- **`<LeadIntakeForm>`**
  ships in
  `frontend/src/components/sales/`,
  parameterized by
  `channel`,
  covering walk-in +
  phone + referral
  base 9 fields.
- **`<ReferralLeadFormExtras>`**
  adds the "Referring
  customer (existing
  lead)" picker
  (optional, tenant-
  scoped).
- **No
  `<WebhookIntakeForm>`
  ships. No `+ Webhook`
  operator CTA.**
- Three operator
  Dialog CTAs
  (`+ Walk-in`,
  `+ Phone`,
  `+ Referral`)
  attach to
  `DealerAiSalesLeads.tsx`.
- Post-create
  redirect to
  `/dealer-ai/sales/leads/<id>`
  from every
  operator intake.
- Four new Playwright
  journeys in
  `acceptance/journeys/sales_manager/`
  per §5.d:
  - `walk_in_intake.spec.ts`
    — Dialog CTA →
    create → assign
    → schedule test
    drive
  - `phone_intake.spec.ts`
    — Dialog CTA →
    create → assign
    → start 24hr
    cadence
  - `referral_intake.spec.ts`
    — Dialog CTA →
    create with
    referring-
    customer picker
    → attribution
    verified
  - `webhook_integration_intake.spec.ts`
    — test setup
    POSTs to real
    `/admin/leads/webhook/`
    with
    `platform="generic"`
    → browser opens
    as salesperson
    → asserts lead
    appears under
    `channel="listing_form"`
    filter → assign
    via UI
- One new seed
  `seed_journey_sales_operational_entry`
  with vehicle +
  referring-customer
  lead fixtures +
  session-safe re-
  invocation + lead
  cleanup.
- Vitest coverage
  grows ~10–15 tests
  across two new
  components
  (`<LeadIntakeForm>`,
  `<ReferralLeadFormExtras>`).
- All four M24
  journeys pass on
  `main` CI in
  coordinated push
  at M24.5.
- **Zero-drift
  permission-class
  streak extends 23
  → 24** (all
  endpoints reuse
  `IsSalesManagerOrOwnerAtActiveDealership`).
- Acceptance
  journey count
  grows **9 → 13**.
- Retrospective §9
  records: sales
  front-of-funnel
  operationally
  complete (three
  operator-created
  + one integration-
  to-operator) +
  M25 next-candidate
  identified by
  intake-journey
  evidence.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M23 shipped section
   landed at M23.4)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_24_PLANNING.md`
   (this memo)
6. `docs/roadmap/MILESTONE_23_RETROSPECTIVE.md`
   §8 + §9 (M23 corrections +
   standing M24 question)
7. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (M23 governing contract
   inherited by M24)
8. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (M21 Candidate O
   governing contract that
   M23 + M24 inherit
   directly)
9. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact —
   authoritative for BHPH
   + accounting post-M23.1;
   authoritative for sales
   intake at M24.0)
10. `docs/CAPABILITY_MATRIX.md`
    §7x (M23 shipped
    surface)

## 7. Sequencing

### Increment 0 (M24.0) — Planning refinement + target selection

**Status:** SHIPPED at
SESSION_180.

Planning-only session per
M10.0–M23.0 precedent. All
eight §5 decisions resolved
at open. §5.a + §5.c +
§5.e + §5.f + §5.g + §5.h
confirmed as-recommended;
§5.b + §5.d redirected
before lock on the webhook
operator-UI posture per
user framing. Planning-
time as-recommended streak
reset to 0.

Backend baseline unchanged:
4,780 pass, 1 skipped, 0
fail. Frontend Vitest
baseline unchanged: 193
pass. Migrations
`0001`–`0048` (unchanged).
Tenancy carriers 52
(unchanged). DRF admin
surface 113 (unchanged).
Frontend operator routes
20 (unchanged). Permission
classes 7 (unchanged —
zero-drift streak intact
at twenty-three
consecutive milestones;
M24 extends to twenty-
four at close). Celery-
beat task families 10
(unchanged). Acceptance
suite 9 journeys
(unchanged — M24 grows to
13 at close).

### Increment 1 (M24.1) — Shared intake substrate + walk-in UI + walk-in journey

**Target session:** SESSION_181.

Ships the shared
`<LeadIntakeForm>`
substrate + walk-in
specialization + walk-in
operational journey.
First anchor UI —
subsequent M24.2 + M24.3
inherit the substrate via
sibling-pattern
discipline.

Scope:

- **`<LeadIntakeForm>`
  component** in
  `frontend/src/components/sales/`
  with the 9 shared fields
  (`name`, `phone`,
  `email`, `notes`,
  `target_monthly_payment`,
  `down_payment`,
  `trade_in`,
  `credit_range`,
  `urgency`), submit +
  error handling,
  parameterized by
  `channel`.
- **`+ Walk-in` Dialog
  CTA** attached to
  `DealerAiSalesLeads.tsx`
  Notes-card-header
  pattern (or equivalent
  attachment point;
  finalize during
  authoring per M17 §6
  lesson 6).
- **Post-create redirect**
  to
  `/dealer-ai/sales/leads/<id>`.
- **Vitest coverage** for
  `<LeadIntakeForm>` (~5–7
  tests).
- **New seed**
  `seed_journey_sales_operational_entry`
  with salesperson + role
  + tenant + target
  vehicle fixture +
  session-safe pattern +
  lead cleanup.
- **New assertion helper**
  at
  `acceptance/support/assertions/sales.ts`
  (if patterns repeat
  during authoring — else
  ship in M24.2).
- **New journey**
  `acceptance/journeys/sales_manager/walk_in_intake.spec.ts`:
  seed → login as
  salesperson → open
  `DealerAiSalesLeads` →
  click `+ Walk-in` →
  fill form → submit →
  land on
  `/dealer-ai/sales/leads/<id>`
  → assign salesperson →
  schedule test drive
  via existing UI →
  assert test drive
  appears on lead
  detail.
- **Small operator-
  surface gap fixes**
  per §5.d inherited
  posture (in-scope
  small fixes; large
  deferred).

Backend baseline target:
4,780 → ~4,781 (possibly
one seed-fixture test).
Frontend Vitest target:
193 → ~198–200. Acceptance
suite: 9 → **10**.

### Increment 2 (M24.2) — Phone UI + journey

**Target session:** SESSION_182.

Phone specialization
reuses `<LeadIntakeForm>`
unchanged; only channel
constant + downstream verb
differ. Small increment.

Scope:

- **`+ Phone` Dialog CTA**
  attached to
  `DealerAiSalesLeads.tsx`.
- **`<LeadIntakeForm
  channel="phone">`**
  reuse; no new component
  work if M24.1 shipped
  the substrate cleanly.
- **Post-create redirect**
  to
  `/dealer-ai/sales/leads/<id>`.
- **Vitest coverage** for
  channel-parameterization
  behavior (~2–3 tests
  if not already covered
  in M24.1).
- **Seed extension:** no
  new fixtures required.
- **New journey**
  `acceptance/journeys/sales_manager/phone_intake.spec.ts`:
  seed → login → open
  `DealerAiSalesLeads` →
  click `+ Phone` → fill
  form → submit → land
  on lead detail →
  assign → start 24hr
  cadence via existing
  UI → assert cadence
  appears on lead
  detail.
- **Small operator-
  surface gap fixes**
  per §5.d.

Backend baseline target:
~4,781 → ~4,782.
Frontend Vitest target:
~198–200 → ~200–203.
Acceptance suite: 10 →
**11**.

### Increment 3 (M24.3) — Referral UI + journey

**Target session:** SESSION_183.

Referral adds the
`<ReferralLeadFormExtras>`
component (referring-
customer picker) as a
small delta over
`<LeadIntakeForm>` + a
Playwright journey that
validates attribution.

Scope:

- **`+ Referral` Dialog
  CTA** attached to
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
  channel="referral">`**
  as the specialization
  slot.
- **Post-create
  redirect** to
  `/dealer-ai/sales/leads/<id>`.
- **Vitest coverage**
  for
  `<ReferralLeadFormExtras>`
  (~5–7 tests: picker
  search, tenant scope,
  optional handling,
  `referrer_lead_id`
  submission).
- **Seed extension:**
  add referring-
  customer lead
  fixture to
  `seed_journey_sales_operational_entry`.
- **New journey**
  `acceptance/journeys/sales_manager/referral_intake.spec.ts`:
  seed → login → open
  `DealerAiSalesLeads`
  → click `+ Referral`
  → fill form + select
  referring customer
  from picker → submit
  → land on lead
  detail → assert
  referrer link visible
  and correct.
- **Small operator-
  surface gap fixes**
  per §5.d.

Backend baseline
target: ~4,782 →
~4,783. Frontend Vitest
target: ~200–203 →
~207–210. Acceptance
suite: 11 → **12**.

### Increment 4 (M24.4) — Webhook integration-to-operator journey

**Target session:**
SESSION_184.

**No new UI component.**
Ships a Playwright
journey that validates
the real integration
boundary + real
operator UI handling
per §5.d.

Scope:

- **No new frontend
  component.** No
  `<WebhookIntakeForm>`.
  No `+ Webhook`
  operator CTA.
- **No new backend
  surface.** Uses
  shipped
  `/admin/leads/webhook/`
  endpoint + shipped
  `generic` adapter.
- **Seed extension:**
  no new fixtures
  required
  (`seed_journey_sales_operational_entry`
  already provisions
  salesperson +
  tenant).
- **New journey**
  `acceptance/journeys/sales_manager/webhook_integration_intake.spec.ts`:
  - `test.beforeEach`:
    APIRequestContext
    POSTs to real
    `/admin/leads/webhook/`
    with
    `platform="generic"`
    + realistic dealer-
    owned envelope
    (`full_name`,
    `phone`, `email`,
    `message`, budget
    hints).
  - Login as
    salesperson.
  - Navigate to
    `/dealer-ai/sales/leads`
    with `channel`
    filter set to
    `listing_form`.
  - Assert the
    ingested lead
    appears in the
    filtered list with
    correct
    platform/channel
    attribution.
  - Open lead detail.
  - Assign via existing
    UI (real button;
    real assignment
    endpoint).
  - Assert assignment
    persisted on lead
    detail.
- **Small operator-
  surface gap fixes**
  per §5.d (rare —
  the browser-side
  flow uses shipped
  UI unchanged).

Backend baseline
target: ~4,783 → ~4,783
(no code change).
Frontend Vitest target:
~207–210 (unchanged).
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

### Increment 5 (M24.5) — Close-out

**Target session:**
SESSION_185 (or
SESSION_184 if M24.4
folds).

Scope:

- CI job validation on
  all four new
  journeys.
- `docs/CAPABILITY_MATRIX.md`
  §7y — M24 shipped
  surface (three
  operator-created
  intake paths + one
  integration-to-
  operator journey).
- `docs/roadmap/MILESTONE_24_RETROSPECTIVE.md`
  with §8 corrections
  + §9 next-candidate.
- `docs/roadmap/MILESTONE_25_PLANNING.md`
  skeleton (status:
  draft).
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  updated with M24
  shipped status.
- `00-START-NEXT-SESSION.md`
  refreshed for M25.0.
- Coordinated close-
  out commit + push
  per M18.6 / M19.6 /
  M20.5 / M21.5 /
  M22.4 / M23.4
  pattern.

Backend baseline
target: unchanged from
M24.4. Frontend Vitest:
unchanged. Acceptance
suite: 13 (unchanged).

## 8. Streak accounting (M24 open)

**Planning-time as-
recommended streak:
RESET TO 0.** §5.b and
§5.d were redirected
before lock at
SESSION_180 M24.0 open
on the webhook
operator-UI posture.
The correction was
meaningful — repository
evidence contradicted
the initial
recommendation. The M24
retrospective §5 will
formally acknowledge
the redirect;
resetting the streak
is preferable to
reclassifying the
redirect merely to
preserve the counter.

Historical run at M24.0
open (immediately
before the reset): 89
planning-time as-
recommended M5.1 →
M23.0 across fourteen
consecutive milestones
(M10 → M23). Preserved
for the record.

Post-reset counter
starts at M24.0. §5.a +
§5.c + §5.e + §5.f +
§5.g + §5.h confirmed
as-recommended (6
decisions). §5.b +
§5.d redirected (2
decisions). Post-lock,
the revised M24 plan
is stable and ready
for M24.1
implementation.

**Zero-drift permission-
class streak target for
M24 close: twenty-three
→ twenty-four
consecutive
milestones.** M24
introduces zero new
permission classes.

## 9. Non-goals for the remaining M24 increments

Per §3 above:

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
  backend service
  verbs, DRF
  endpoints, tenancy
  carriers, migrations,
  permission classes,
  or frontend routes.
- ❌ Do NOT ship named-
  platform webhook
  adapters (Autotrader,
  Cars.com, CarGurus,
  Facebook Marketplace).
  Documented as future
  work in
  `webhook_adapters/__init__.py`.
- ❌ Do NOT redesign
  the `CustomerLead.referrer`
  self-FK backend
  contract inside M24.
  Preserve as-is; UI
  label uses truthful
  operator language
  ("Referring customer
  (existing lead)").
- ❌ Do NOT manually
  verify workflows
  before authoring
  journeys — journey-
  as-verifier per §5.f
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
  out push at M24.5.
- ❌ Do NOT force-scope
  larger discovered
  gaps into M24 —
  document as
  retrospective §9
  evidence per §5.f-
  inherited posture.
