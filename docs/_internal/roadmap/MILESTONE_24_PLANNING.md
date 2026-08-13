---
title: "Milestone 24 — Sales Operational Entry"
status: active
type: planning-memo
generated: 2026-08-03
generated_at_session: SESSION_179 (skeleton), SESSION_180 (expansion), SESSION_181 (M24.1-open downstream-surface reality correction)
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
> **Corrected at SESSION_181 M24.1
> open** — see the correction note
> below for the specific §5.b + §5.d
> + §5.h revisions caused by
> incomplete M24.0 downstream-surface
> verification.
>
> §5.a Candidate O2 (lead-source-
> specific intake) confirmed at
> M24.0 open per the primary
> operational-coverage lens, then
> refined by the user into an
> operational-workflow framing
> rather than a four-forms framing.
> Milestone name: **"Sales
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
> every M24 scope decision.
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
> M24.0 open** on the webhook
> operator-UI posture (system-
> to-system boundary, not
> salesperson-created source).
> **§5.b + §5.d + §5.h were
> revised again at SESSION_181
> M24.1 open** — see the M24.1-
> open correction note below for
> the specific evidence-based
> rescoping.
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
> expected from one new component
> (`<LeadIntakeForm>`) and
> possibly one small extension
> component
> (`<ReferralLeadFormExtras>`).
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
> §5.c + §5.e + §5.f + §5.g
> confirmed as-recommended at
> M24.0 open. §5.b + §5.d + §5.h
> revised at M24.1 open** to
> match product reality (see
> correction note).

## M24.1-open correction (SESSION_181)

**What triggered the correction.**
Empirical UI substrate verification
performed at M24.1 open (before
authoring any implementation code)
surfaced that M24.0's §5.b + §5.d
+ §5.h assumed downstream operator
UI existed that in fact does not
ship today:

1. **Route path mismatch.** M24.0
   memo, handoff, and next-session
   file all referenced
   `/dealer-ai/sales/leads/<id>`
   as the post-create redirect
   target. The real sales leads
   route is
   `/dealer-ai-sales/leads`
   (hyphen; no `:id` sub-route);
   there is no dedicated sales-
   side lead detail page. This
   was a documentation error
   introduced at M24.0 by
   unverified route assumption.

2. **Downstream verb UI
   substrate gap.** M24.0 §5.d
   promised per-channel handoffs
   assuming shipped UI existed:
   - Walk-in → assign + schedule
     test drive. Assign is
     reachable via
     `LeadDetailModal` +
     `AssignmentDropdown` (but
     the modal is not currently
     wired into
     `DealerAiSalesLeads` —
     small in-scope wire-up
     needed). **Test-drive
     creation UI does not
     ship.** `DealerAiSalesTestDrives.tsx:4-5`
     explicitly notes: "Read-
     only view at M11.6 —
     creation happens via the
     dedicated form on the
     M11.2 backend surface
     (deferred to a follow-on
     UX pass)."
   - Phone → assign + start
     24hr cadence. Both
     reachable — assign via
     modal wire-up; cadence
     via existing
     `CadenceConfigPanel` on
     `DealerAiSalesFollowUps`
     (M21.3 shipped).
   - Referral → attribution
     link visible on lead
     detail. **`LeadDetailModal`
     does not display
     `referrer_id` or referrer
     information.** Attribution
     is observable only in the
     raw API projection today.
     Truthful M24 assertion:
     `channel="referral"`
     visible in the leads-list
     table column.
   - Webhook → correct
     platform/channel
     attribution visible in
     UI. `channel="listing_form"`
     IS visible in the leads-
     list table column, so
     this assertion is
     truthful. `platform`
     value (e.g. `"generic"`)
     is NOT shown anywhere in
     the operator UI today.

**How the correction was
performed.** Under the M23 §5.d
durable "small in-scope fix vs.
large deferred" posture, and per
user direction at SESSION_181
open:

- **Small in-scope fixes
  accepted into M24 scope:**
  - Route path corrections
    (documentation-only).
  - Wire `LeadDetailModal` +
    `AssignmentDropdown` into
    `DealerAiSalesLeads` (~30-
    line extension: useState
    modal-open state; row-click
    handler; open on post-
    create).
- **Genuinely-missing UI
  surfaces deferred to M25 or
  the next Operational Surface
  Completion milestone:**
  - `<RecordTestDriveForm>` +
    attachment on
    `DealerAiSalesTestDrives`
    (Candidate O2, wrapper
    exists).
  - `referrer_id` /
    "Referred by" display in
    `LeadDetailModal` (small
    UI addition; requires no
    new backend).
  - `platform` display in
    `LeadDetailModal` for
    webhook-origin leads
    (small UI addition;
    requires no new backend).

**Streak accounting.**
Planning-time as-recommended
streak was already reset to 0
at SESSION_180 M24.0 open for
the webhook operator-UI
posture redirect. The
SESSION_181 M24.1-open
correction is a second planning
revision on the same milestone;
streak remains at 0 (not
extended, not further reset).
The M24 retrospective §5 will
record both corrections
truthfully.

**Doc governance.** Per
DOC_GOVERNANCE.md rule 5,
historical documents are
preserved unless factual
correction is required. The
SESSION_180 handoff is
appended with a "Correction at
SESSION_181 open" section
documenting this discovery
without rewriting the original
record. This memo (an active
planning artifact) is updated
in place per rule 2.

## Guiding question (durable, per M22 close)

**Which candidate most increases
operational coverage for a
dealership employee?**

Applied at M24.0 to lock §5.a
(lead-source-specific intake).
Applied again at M24.1 open to
scope downstream verbs to the
deepest shipped-and-reachable
UI (rather than the deepest
imagined-to-exist UI). The lens
continues to govern any mid-
milestone scope addition or
subtraction.

## Preserve the M20–M23 operational contract (durable)

Compound guidance carried forward
through every M24 decision and
increment:

- **Evidence over assumptions.**
  Verify through the real
  application before locking
  scope. Applied at M24.0 open
  (webhook adapter registry
  review). Applied again at
  M24.1 open (downstream verb
  UI substrate review — surfaced
  the correction above). Both
  applications preserved
  operational-coverage
  discipline at the cost of one
  correction each.
- **Operational workflow over
  endpoint count.** M24 anchor
  business question is
  operational, not enumerative.
- **Every customer-facing
  capability extends Playwright.**
  M21.0 §5.f Option B DoD
  amendment. M24 ships four new
  operational journeys under
  `acceptance/journeys/sales_manager/`.
- **Every milestone increases
  operational coverage for
  dealership employees.**
- **Tightly bounded milestones.**
  Evidence-sized §5.h Option B
  posture allows shape to
  shrink as well as grow.
- **Sibling-pattern discipline
  (M23 durable lesson).** First-
  of-a-kind changes surface
  latent bugs; inherited
  patterns don't. Applied in
  §5.b (in-place-page-extension
  per M17 §6 lesson 6 + M21.2 +
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
- **Verify prior recommendations
  at planning open (M22 durable
  lesson).** M24.0 open verified
  the four intake endpoints /
  wrappers / referrer contract
  / webhook adapter registry.
  M24.0 did NOT verify the
  downstream verb UI substrate,
  which surfaced the correction
  documented above. **Durable
  lesson strengthened for M25+:
  verification MUST cover both
  intake and downstream UI
  surfaces before locking §5.b
  + §5.d.**

## Guiding principle (Candidate O UI-creation contract, M21 shape)

M24 inherits the M21 Candidate O
governing contract. Every M24
shipped surface must satisfy
four conditions:

1. **Maps to an already-shipped
   backend capability.** All
   four target endpoints
   (`admin-lead-walk-in-create`,
   `admin-lead-phone-create`,
   `admin-lead-referral-create`,
   `admin-lead-webhook-create`)
   ship since M11.1; wrappers
   ship in `salesApi.ts` since
   M11.6.
2. **Closes a missing operator-
   facing UI OR validates a
   missing integration-to-
   operator flow.** Verified
   empirically at M24.0 open
   (intake surface) and M24.1
   open (downstream surface).
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
   (webhook).

## 0. Engineering practices to preserve from M2–M23

Full posture per M23.0 §0
(carried forward). M24-specific
notes:

- **Backend-first architecture.**
  M24 ships zero new backend
  business logic.
- **Service ownership.** Every
  UI target invokes an existing
  service verb.
- **Wrapper-only verification
  before UI writes.** Before
  M24.1 authors any UI code,
  verify each wrapper's exact
  request/response shape from
  `salesApi.ts` matches the
  backend serializer.
- **Downstream-surface
  verification before locking
  §5.b + §5.d.** New M24
  durable lesson.
- **Tenant discipline.** All
  four intake endpoints
  resolve `dealership` via
  `services.tenancy.get_current_dealership`.
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
  strings.
- **Idempotency + cleanup on
  seed re-invocation** per
  M22.2 / M23.2 pattern.
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

Broken down by channel (revised
at M24.1 open to match shipped
UI reality):

1. **Walk-in.** *When a customer
   walks onto the lot, can the
   salesperson create their
   lead in the system and
   immediately open its detail
   record and assign a
   salesperson?* M24 answer:
   yes, via `+ Walk-in` Dialog
   CTA on `DealerAiSalesLeads`
   → shared `<LeadIntakeForm>`
   with `channel="walk_in"` →
   post-create opens
   `LeadDetailModal` for the
   new lead (same page; no
   redirect) → assign via
   `AssignmentDropdown` in the
   modal header. Playwright
   validates.

   *Test-drive scheduling is
   the natural next-next step
   but the UI has not shipped
   (M11.6 deferred it). Test-
   drive UI is now an M25
   Candidate O2 sub-scope
   candidate per §3.*

2. **Phone.** *When a customer
   calls the dealership, can
   the salesperson create their
   lead while on the phone,
   assign it, and start a 24-
   hour follow-up cadence?* M24
   answer: yes, via `+ Phone`
   Dialog CTA → shared
   `<LeadIntakeForm>` with
   `channel="phone"` → post-
   create opens `LeadDetailModal`
   → assign via
   `AssignmentDropdown` →
   navigate to
   `/dealer-ai-sales/follow-ups`
   → use existing
   `CadenceConfigPanel`
   (`CreateCadenceForm`) to
   start 24hr cadence with the
   new lead's ID. Playwright
   validates.

3. **Referral.** *When an
   existing customer refers a
   friend, can the salesperson
   record the referral with
   the referring customer
   linked to the new lead in
   the backend, and hand off
   the new lead through the
   normal operational
   workflow?* M24 answer: yes,
   via `+ Referral` Dialog CTA
   → shared `<LeadIntakeForm>`
   + `<ReferralLeadFormExtras>`
   with "Referring customer
   (existing lead)" picker →
   post-create opens
   `LeadDetailModal` for the
   new lead → assign via
   `AssignmentDropdown` →
   `channel="referral"` visible
   in the leads-list table
   column post-hoc. Playwright
   validates.

   *Explicit truthful boundary:
   `LeadDetailModal` does NOT
   currently display
   `referrer_id` or a
   "Referred by" link. The
   backend contract IS
   preserved (referrer FK
   set correctly) but the
   operator cannot see the
   attribution in the detail
   modal. Referrer display in
   the modal is now an M25
   candidate per §3.*

4. **Webhook (listing platform
   integration).** *When an
   external listing platform
   posts a customer lead to
   the dealership's webhook
   endpoint, does that lead
   appear correctly in the
   salesperson's UI with
   channel attribution, and
   can the salesperson pick
   it up and assign it?* M24
   answer: yes, validated via
   `webhook_integration_intake.spec.ts`
   — Playwright setup step
   POSTs to real
   `/admin/leads/webhook/`
   with `platform="generic"` +
   realistic dealer-owned
   envelope; journey then
   opens the browser as
   salesperson → asserts lead
   appears with
   `channel="listing_form"`
   in the leads-list table →
   opens `LeadDetailModal` →
   assigns via
   `AssignmentDropdown`. No
   manual webhook form.

   *Explicit truthful boundary:
   the operator UI shows
   `channel="listing_form"`
   but does NOT show the
   `platform` value (e.g.
   `"generic"`) anywhere. The
   platform is captured in
   the backend but not
   surfaced in the modal or
   the list. Platform display
   is now an M25 candidate per
   §3.*

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
  adapter? M24 answer: yes.
- Does `DealerAiSalesLeads`
  currently wire the
  `LeadDetailModal`? M24
  answer: no; M24.1 wires it
  as a small in-scope
  extension per §5.b.

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
  reused unchanged.
- `CustomerLead.referrer`
  self-FK (M11.1
  `models.py:904`) — backend
  contract preserved.

**Frontend wrappers (already
exist in `salesApi.ts`).**

- `createWalkInLead` /
  `createPhoneLead` /
  `createReferralLead` — M11.6
  wrappers consumed by new
  UI.
- `createWebhookLead` — M11.6
  wrapper. **Not consumed by
  operator UI in M24;** stays
  in `salesApi.ts` for a
  future integration-console
  or health-check surface.
- `fetchAdminLeads(filters)`
  — used by the referral
  picker to search existing
  leads tenant-scoped.
- `fetchLeadDetail`
  `buildLeadHandoff` —
  consumed by
  `LeadDetailModal` (already
  wired into modal;
  unchanged).
- `assignLead` —
  consumed by
  `AssignmentDropdown`
  (already wired; unchanged).
- `createCadence` — consumed
  by `CadenceConfigPanel`
  (already wired on
  `DealerAiSalesFollowUps`
  since M21.3; unchanged).

**Frontend components already
shipped and reused unchanged.**

- **`LeadDetailModal`**
  (`frontend/src/components/LeadDetailModal.tsx`)
  — currently attached to the
  older `LeadsPage` at
  `/dealer-ai-leads`. **M24.1
  wires it into
  `DealerAiSalesLeads`** as a
  small in-scope extension
  per §5.b. Component itself
  unchanged.
- **`AssignmentDropdown`**
  (`frontend/src/components/AssignmentDropdown.tsx`)
  — used inside
  `LeadDetailModal` header;
  unchanged.
- **`CadenceConfigPanel`**
  (`frontend/src/components/sales/CadenceConfigPanel.tsx`)
  — shipped M21.3 on
  `DealerAiSalesFollowUps`;
  used by phone journey to
  create the 24hr cadence
  post-intake.

**Frontend pages (attachment
targets).**

- `DealerAiSalesLeads.tsx`
  (M11.6) — receives three
  Dialog CTAs (`+ Walk-in`,
  `+ Phone`, `+ Referral`) +
  `LeadDetailModal` wire-in
  + row-click handler.
- `DealerAiSalesFollowUps.tsx`
  (M11.6 + M21.3) —
  unchanged; consumed by the
  phone journey's cadence
  step.

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
discovery rule. Revised at
M24.1 open to add three
deferrals surfaced by
downstream-surface
verification.

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
   payloads.

2. **New backend service
   verbs, DRF endpoints,
   tenancy carriers,
   migrations, permission
   classes, or frontend
   routes.** M24 is UI-
   creation + integration-
   validation only.

3. **Named-platform webhook
   adapters** (Autotrader /
   Cars.com / CarGurus /
   Facebook Marketplace).
   Documented as future work
   in `webhook_adapters/__init__.py:12-15`.

4. **Referral incentive
   payout logic.** Deferred
   from M11 per M11 §2.

5. **Salesperson-authored
   lead search / filter
   enhancements** beyond
   what already ships in
   `DealerAiSalesLeads`.

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
   §5.g.

8. **Manual pre-verification
   of each intake workflow
   before authoring the
   journey.** Journey-as-
   verifier per §5.f Option
   B.

9. **Splitting the M24
   Playwright seed into per-
   channel seeds.** One
   shared seed per §5.e
   Option A.

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

### Deferrals surfaced by M24.1-open downstream-surface verification

12. **`<RecordTestDriveForm>`
    component + attachment on
    `DealerAiSalesTestDrives`.**
    The `createTestDrive`
    wrapper exists in
    `salesApi.ts` since M11.6
    but no UI consumes it;
    `DealerAiSalesTestDrives.tsx`
    is read-only. Genuinely
    missing operator surface.
    **Re-entry path:** M25
    Candidate O2 sub-scope
    (bundle with the walk-in
    journey's downstream
    verb assertion to
    strengthen the walk-in
    operational-entry
    story). Sibling-pattern
    fit with M24.1 form
    substrate.

13. **`referrer_id` /
    "Referred by" display in
    `LeadDetailModal`.**
    Backend contract IS
    correctly persisted; the
    referrer self-FK is set
    on the created lead per
    `record_referral_lead()`.
    The operator simply
    cannot see the
    attribution in the
    detail modal today.
    Genuinely missing UI.
    **Re-entry path:** M25
    small UI extension
    (~20-line addition to
    `LeadDetailModal` to
    fetch and render the
    referring lead's name +
    ID). Would also
    strengthen the M24.3
    referral journey's
    downstream assertion.

14. **`platform` display in
    `LeadDetailModal` for
    webhook-origin leads.**
    `channel="listing_form"`
    IS visible in the leads-
    list column, but the
    specific `platform`
    value (e.g. `"generic"`
    or a future
    `"autotrader"`) is not
    surfaced anywhere in
    the operator UI.
    Genuinely missing UI.
    **Re-entry path:** M25
    small UI extension
    (~10-line addition to
    `LeadDetailModal`).
    Bundle with #13 as a
    single "Lead source
    attribution display"
    M25 candidate.

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
M24.0 open (verified again at
M24.1 open: 4,780 pass, 1
skipped, 0 fail in 163s).
New test additions expected
at M24.1–M24.4:

- Possibly one or two seed-
  fixture correctness tests
  for
  `seed_journey_sales_operational_entry`.
- No new endpoint tests.
- No new service tests.
- No new permission tests.

**Frontend Vitest tests
unchanged.** All 193 tests
pass at M24.0 open (verified
at M24.1 open: 193 pass).
New component tests expected
at M24.1–M24.3:

- `<LeadIntakeForm>` unit
  tests — M24.1.
- `<ReferralLeadFormExtras>`
  unit tests — M24.3.
- Possibly a small addition
  to `DealerAiSalesLeads`
  tests covering
  `LeadDetailModal` wire-in
  behavior — M24.1.
- Estimated total growth:
  ~10–15 new tests.

**Acceptance suite
unchanged.** All 9 journeys
+ 6 setup steps pass at
M24.0 open (~20.5s
baseline). Journey count
grows to 13 at M24 close.

**Type checks unchanged.**
`frontend/` and `acceptance/`
`tsc --noEmit` both clean at
M24.0 open (verified at
M24.1 open).

**Migrations unchanged.**
`0001`–`0048`; no new
migrations expected.

**Django check unchanged.**
0 issues at M24.0 open
(verified at M24.1 open).

## 5. Load-bearing decisions

### 5.a `[RESOLVED at SESSION_180 open]` — Milestone target selection

**Question.** Which candidate
defines M24 scope?

**Decision. Candidate O2 —
lead-source-specific intake
sub-scope (4 endpoints:
walk-in, phone, referral,
webhook), framed as "Sales
Operational Entry."**

**Rationale.** (1) Highest
per-unit operational-
coverage delta on the
primary lens. (2) Front-of-
funnel position — every
downstream sales verb
requires a lead first. (3)
Wrapper economy — all 4
wrappers already exist. (4)
Bookend-completion pattern.
(5) User's framing
refinement to "Sales
Operational Entry"
strengthened the workflow
lens. (6) Streak-neutral on
permission classes.

### 5.b `[RESOLVED at SESSION_180 open — REDIRECTED before M24.0 lock — REVISED at SESSION_181 M24.1 open]` — Component attachment plan + shared substrate + downstream modal wire-in

**Question.** Where do the
intake entry points attach,
how much of the form
component tree is shared,
and what happens after a
successful intake?

**M24.0 posture (rejected in
part).** Three operator
Dialog CTAs on
`DealerAiSalesLeads` + shared
`<LeadIntakeForm>` + post-
create redirect to
`/dealer-ai/sales/leads/<id>`.

**M24.1-open correction.**
Route path was wrong (real
route is `/dealer-ai-sales/leads`
with hyphen; no `:id` sub-
route exists). Post-create
redirect target does not
exist. Revised to open
`LeadDetailModal` on the same
page.

**Options at M24.1 open:**

- **Option A (locked)** —
  Three operator-facing
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
  `referrer_lead_id`). **No
  `+ Webhook` operator CTA.
  No `<WebhookIntakeForm>`.**
  On successful intake:
  close intake Dialog →
  open `LeadDetailModal`
  for the newly created
  lead on the same page.
  **`LeadDetailModal` +
  `AssignmentDropdown`
  wired into
  `DealerAiSalesLeads`**
  as a small in-scope
  extension (~30-line
  addition: useState
  modal-open state; row-
  click handler; open on
  post-create). Route
  target is
  `/dealer-ai-sales/leads`
  (unchanged; no
  navigation).
- **Option B (rejected)** —
  Ship a new
  `DealerAiSalesLeadDetail.tsx`
  page + `/dealer-ai-sales/leads/:id`
  route. Would violate
  M24 §3 non-goal on new
  frontend routes.
- **Option C (rejected)** —
  Post-create table
  refresh only; salesperson
  finds the new lead
  themselves. Fails the
  operational-entry
  framing (no immediate
  handoff).

**Decision. Option A —
three operator Dialog CTAs
+ shared component + one
specialization + on-page
`LeadDetailModal` open + in-
scope `LeadDetailModal`
wire-in.**

**Rationale.** (1) Matches
M17 §6 lesson 6 + M21.2 +
M23.2/M23.3 in-place-page-
extension posture — no new
routes; sibling-pattern
discipline preserved. (2)
`DealerAiSalesLeads` is
already the salesperson's
primary destination. (3)
Shared `<LeadIntakeForm>`
mirrors backend
`_BaseIntakeSerializer`
substrate exactly (9
shared fields). (4)
`LeadDetailModal` wire-in
satisfies the operational-
entry framing without
adding routes — salesperson
lands in the detail modal
immediately post-intake,
can assign in one click.
(5) Referring-customer UI
language ("Referring
customer (existing lead)")
preserves the backend
self-FK contract
truthfully. (6) The M24.0
redirect target
(`/dealer-ai/sales/leads/<id>`)
was a documentation error
introduced by unverified
route assumption; the
correction avoids
introducing a new route
just to hold the operator
handoff.

### 5.c `[RESOLVED at SESSION_180 open]` — Journey folder + shape

**Question.** Which folder,
and one journey per
channel or consolidated?

**Decision. Option A —
four sibling journeys in
`acceptance/journeys/sales_manager/`.**

- `walk_in_intake.spec.ts`
- `phone_intake.spec.ts`
- `referral_intake.spec.ts`
- `webhook_integration_intake.spec.ts`

**Rationale.** Per M23.2
§5.c Option B precedent
(per-workflow spec files
for distinct workflows).
Each intake channel
represents a distinct
operator situation. Clean
failure attribution.
`sales_manager/` folder
already exists.

### 5.d `[RESOLVED at SESSION_180 open — REDIRECTED before M24.0 lock — REVISED at SESSION_181 M24.1 open]` — Downstream-handoff assertion scope + webhook ingestion posture

**Question.** How far into
the downstream sales
workflow must each intake
journey reach to validate
the operational-entry
framing, and how does the
webhook integration
journey originate its
ingestion step?

**M24.0 posture (rejected
in part).** Per-channel
downstream verbs assumed
downstream operator UI
existed for assign +
schedule test drive +
start cadence + attribution
display + platform display.
Only assign (via wire-in)
and cadence (already
shipped) are actually
reachable today.

**Options at M24.1 open:**

- **Option A (minimum)** —
  Journey asserts lead
  created + visible in
  the lead list. Downstream
  verbs untested.
- **Option B (M24.0 posture,
  rejected)** — Full per-
  channel handoffs
  including test-drive UI
  and referrer-display,
  which do not ship.
- **Option C (revised
  recommendation,
  LOCKED)** — **Common
  core across all four
  channels (deepest
  shipped-and-reachable
  downstream verb):**
  intake → list visibility
  with correct `channel`
  attribution → open
  `LeadDetailModal` for
  the new lead → assign
  via `AssignmentDropdown`.
  **Per-channel narrow
  extras where reachable
  and truthful:**
  - **Walk-in:** UI Dialog
    create → list
    visibility
    (`channel="walk_in"`)
    → open `LeadDetailModal`
    → assign. **No test-
    drive step** (UI
    deferred per §3
    deferral 12).
  - **Phone:** UI Dialog
    create → list
    visibility
    (`channel="phone"`) →
    open `LeadDetailModal`
    → assign → navigate to
    `/dealer-ai-sales/follow-ups`
    → use existing
    `CadenceConfigPanel`
    (`CreateCadenceForm`)
    to start 24hr cadence
    with the new lead's ID
    → assert cadence
    created.
  - **Referral:** UI Dialog
    create with referring-
    customer picker → list
    visibility
    (`channel="referral"`)
    → open
    `LeadDetailModal` →
    assign. Referrer
    backend attribution
    verified via API
    setup-side assertion
    (list projection
    includes `referrer_id`)
    since the modal does
    not display it. **No
    modal-side referrer
    assertion** (display
    deferred per §3
    deferral 13).
  - **Webhook (integration-
    to-operator):**
    Playwright setup step
    (outside browser)
    POSTs to real
    `/admin/leads/webhook/`
    with `platform="generic"`
    + realistic dealer-
    owned envelope.
    Journey then opens the
    browser as salesperson
    → navigates to
    `/dealer-ai-sales/leads`
    filtered on
    `channel="listing_form"`
    → asserts ingested
    lead appears with
    correct channel → opens
    `LeadDetailModal` →
    assigns via
    `AssignmentDropdown`.
    **No modal-side
    platform assertion**
    (display deferred per
    §3 deferral 14).

**Decision. Option C —
common core (list
visibility + modal +
assign) across all four
channels; phone
additionally validates
cadence creation; walk-in
/ referral / webhook stop
at assign; deferred UI
gaps documented per §3.**

**Rationale.** (1) Directly
matches user M24.1-open
direction — "define each
journey around the deepest
already-shipped and
normally reachable
operator action, rather
than assuming every
channel must reach a
different downstream
verb." (2) Every asserted
downstream verb is shipped
and reachable today after
the M24.1 in-scope wire-in
of `LeadDetailModal` into
`DealerAiSalesLeads`. (3)
Genuinely-missing UI
gaps (test-drive, referrer
display, platform display)
documented as M25
candidates per §3 rather
than silently ignored or
forced into M24 scope. (4)
Webhook setup outside
browser is honest about
the producer being an
external system. (5)
Attribution assertions are
retained where the UI
truthfully shows the field
(channel column) and
dropped where it does not
(referrer, platform),
consistent with user
direction "retain
attribution assertions
only if the existing lead-
detail UI truthfully
displays those fields."

### 5.e `[RESOLVED at SESSION_180 open]` — Seed command pattern

**Question.** One extended
seed or new per-channel
seeds?

**Decision. Option A — one
new `seed_journey_sales_operational_entry`
seed.**

Provisions shared
salesperson user + role +
tenant + referring-
customer lead (for
referral attribution). No
target-vehicle fixture
required (walk-in no
longer schedules a test
drive per revised §5.d).
Session-safe re-invocation
+ lead cleanup applied
from the start per M23.2
durable pattern. Webhook
payload lives in the
journey's `test.beforeEach`
hook, not the seed.

### 5.f `[RESOLVED at SESSION_180 open]` — Baseline verification approach

**Decision. Option B —
journey-as-verifier.**
Carries forward from M22.2
/ M23.

### 5.g `[RESOLVED at SESSION_180 open]` — Testid hardening posture

**Decision. Option B —
opportunistic.** Carries
forward from M21 / M22 /
M23.

### 5.h `[RESOLVED at SESSION_180 open — REVISED at SESSION_181 M24.1 open]` — Increment sequencing + completion contract

**Question.** How are M24
increments sequenced, and
what does "M24 shipped"
mean?

**Decision. Option B —
evidence-sized five-to-
six increments.**
Sequencing preserved from
M24.0; M24.1 scope
expanded to include
`LeadDetailModal` wire-in;
per-channel downstream
verbs adjusted per revised
§5.d.

Sequencing:

- **M24.0** — planning
  refinement + target
  selection (SHIPPED at
  SESSION_180 with M24.1-
  open corrections
  documented in
  MILESTONE_24_PLANNING.md
  preamble).
- **M24.1** — shared
  `<LeadIntakeForm>`
  substrate + walk-in
  specialization +
  **`LeadDetailModal` +
  `AssignmentDropdown`
  wire-in into
  `DealerAiSalesLeads`** +
  `walk_in_intake.spec.ts`.
- **M24.2** — phone
  specialization (reuses
  `<LeadIntakeForm>`
  unchanged) +
  `phone_intake.spec.ts`
  (adds navigation to
  follow-ups + cadence
  creation step).
- **M24.3** —
  `<ReferralLeadFormExtras>`
  referring-customer
  picker +
  `referral_intake.spec.ts`.
- **M24.4** —
  `webhook_integration_intake.spec.ts`
  (integration-to-
  operator journey; no
  new UI component).
- **M24.5** — close-out.
  Evidence-sized collapse
  possible.

**Milestone completion
contract (revised at
M24.1 open):**

- `createWalkInLead` /
  `createPhoneLead` /
  `createReferralLead`
  wrappers **unchanged**;
  consumed by new UI.
- `createWebhookLead`
  wrapper stays but is
  not consumed by
  operator UI in M24.
- **`<LeadIntakeForm>`**
  ships in
  `frontend/src/components/sales/`,
  parameterized by
  `channel`, covering
  walk-in + phone +
  referral base 9 fields.
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
- Three operator Dialog
  CTAs (`+ Walk-in`,
  `+ Phone`, `+ Referral`)
  attach to
  `DealerAiSalesLeads.tsx`.
- **`LeadDetailModal`** +
  **`AssignmentDropdown`**
  wired into
  `DealerAiSalesLeads.tsx`
  as an M24.1 in-scope
  extension. Opens on
  post-create for the
  newly created lead;
  also opens on table
  row click for existing
  leads.
- **No post-create
  redirect.** Salesperson
  stays on
  `/dealer-ai-sales/leads`;
  the modal opens on
  same page.
- Four new Playwright
  journeys in
  `acceptance/journeys/sales_manager/`
  per §5.d Option C:
  - `walk_in_intake.spec.ts`
    — Dialog CTA → create
    → list channel
    visibility → modal
    → assign.
  - `phone_intake.spec.ts`
    — Dialog CTA → create
    → list channel
    visibility → modal
    → assign → navigate
    to follow-ups →
    cadence create.
  - `referral_intake.spec.ts`
    — Dialog CTA →
    referring-customer
    picker → create →
    list channel
    visibility → modal
    → assign. Backend
    referrer FK verified
    via API-side
    assertion since modal
    does not display it.
  - `webhook_integration_intake.spec.ts`
    — test setup POSTs
    to real
    `/admin/leads/webhook/`
    with
    `platform="generic"`
    → browser opens as
    salesperson → list
    channel visibility →
    modal → assign.
- One new seed
  `seed_journey_sales_operational_entry`
  with referring-customer
  lead fixture (for M24.3)
  + salesperson +
  session-safe re-
  invocation + lead
  cleanup.
- Vitest coverage grows
  ~10–15 tests across
  two new components
  (`<LeadIntakeForm>`,
  `<ReferralLeadFormExtras>`).
  Plus possibly small
  additions to
  `DealerAiSalesLeads.test.tsx`
  for the modal wire-in.
- All four M24 journeys
  pass on `main` CI in
  coordinated push at
  M24.5.
- **Zero-drift
  permission-class
  streak extends 23 →
  24**.
- Acceptance journey
  count grows **9 → 13**.
- Retrospective §9
  records: sales front-
  of-funnel operationally
  complete at the assign
  level (three operator-
  created + one
  integration-to-operator)
  + M25 candidates
  identified for test-
  drive UI + lead source
  attribution display.

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
   §8 + §9
7. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (M23 governing contract
   inherited by M24)
8. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (M21 Candidate O
   governing contract)
9. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact —
   authoritative for
   BHPH + accounting
   post-M23.1)
10. `docs/CAPABILITY_MATRIX.md`
    §7x (M23 shipped
    surface)

## 7. Sequencing

### Increment 0 (M24.0) — Planning refinement + target selection

**Status:** SHIPPED at
SESSION_180 with M24.1-open
corrections documented in
the preamble above.

Planning-only session per
M10.0–M23.0 precedent. All
eight §5 decisions resolved.
§5.b + §5.d redirected
before lock on the webhook
operator-UI posture at
M24.0 open; §5.b + §5.d +
§5.h revised again at
M24.1 open per user
direction on the
downstream-verb UI
substrate gap.

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
classes 7 (unchanged).
Celery-beat task families
10 (unchanged). Acceptance
suite 9 journeys
(unchanged — M24 grows to
13 at close).

### Increment 1 (M24.1) — Shared intake substrate + walk-in UI + LeadDetailModal wire-in + walk-in journey

**Target session:** SESSION_181.

Ships the shared
`<LeadIntakeForm>`
substrate + walk-in
specialization +
**`LeadDetailModal` +
`AssignmentDropdown`
wire-in into
`DealerAiSalesLeads`** +
walk-in operational
journey. First anchor UI
— subsequent M24.2 +
M24.3 inherit the
substrate.

Scope:

- **`<LeadIntakeForm>`
  component** in
  `frontend/src/components/sales/LeadIntakeForm.tsx`
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
  (attachment point
  finalized during
  authoring per M17 §6
  lesson 6 in-place-page-
  extension posture).
- **`LeadDetailModal` +
  `AssignmentDropdown`
  wire-in on
  `DealerAiSalesLeads.tsx`**
  — new `useState`
  `selectedLeadId`; open
  modal on table row
  click; open modal on
  post-create with the
  newly created lead's
  id.
- **No post-create
  redirect.** Salesperson
  stays on
  `/dealer-ai-sales/leads`.
- **Vitest coverage** for
  `<LeadIntakeForm>` (~5–
  7 tests). Optional
  small additions to
  `DealerAiSalesLeads.test.tsx`
  for the modal wire-in
  behavior.
- **New seed**
  `seed_journey_sales_operational_entry`
  with salesperson +
  role + tenant +
  referring-customer lead
  (for M24.3) + session-
  safe pattern + lead
  cleanup.
- **New assertion helper**
  at
  `acceptance/support/assertions/sales.ts`
  (if patterns repeat
  during authoring; else
  defer to M24.2).
- **New journey**
  `acceptance/journeys/sales_manager/walk_in_intake.spec.ts`:
  1. Invoke seed via
     `invokeSeed('sales_operational_entry')`.
  2. Login as salesperson.
  3. Navigate to
     `/dealer-ai-sales/leads`.
  4. Click `+ Walk-in`
     CTA.
  5. Fill form with test
     customer details.
  6. Submit.
  7. Assert `LeadDetailModal`
     opens for the newly
     created lead.
  8. Assert list row for
     new lead shows
     `channel="walk_in"`
     when modal closed.
  9. Assign salesperson
     via `AssignmentDropdown`
     in modal.
  10. Assert assignment
      persists (reopen
      modal or reload;
      assignment shows
      salesperson).
- **Small operator-
  surface gap fixes**
  per §5.d inherited
  posture (in-scope
  small fixes; large
  deferred as §3
  deferrals).

Backend baseline target:
4,780 → ~4,781 (possibly
one seed-fixture test).
Frontend Vitest target:
193 → ~198–202.
Acceptance suite: 9 →
**10**.

### Increment 2 (M24.2) — Phone UI + journey with cadence downstream

**Target session:** SESSION_182.

Phone specialization
reuses `<LeadIntakeForm>`
unchanged. Journey adds
navigation to the
follow-ups page and
cadence creation via the
existing
`CadenceConfigPanel`.

Scope:

- **`+ Phone` Dialog CTA**
  attached to
  `DealerAiSalesLeads.tsx`.
- **`<LeadIntakeForm
  channel="phone">`**
  reuse; no new component
  work.
- **Post-create opens
  `LeadDetailModal`** for
  the new phone lead
  (wire-in from M24.1
  reused).
- **Vitest coverage** for
  channel-parameterization
  behavior (~2–3 tests
  if not already covered
  in M24.1).
- **Seed extension:** no
  new fixtures required.
- **New journey**
  `acceptance/journeys/sales_manager/phone_intake.spec.ts`:
  1. Invoke seed.
  2. Login as salesperson.
  3. Navigate to
     `/dealer-ai-sales/leads`.
  4. Click `+ Phone` CTA.
  5. Fill form.
  6. Submit.
  7. Assert
     `LeadDetailModal`
     opens.
  8. Assign via
     `AssignmentDropdown`.
  9. Close modal.
  10. Navigate to
      `/dealer-ai-sales/follow-ups`.
  11. Locate
      `CadenceConfigPanel`
      (`CreateCadenceForm`).
  12. Enter the new
      lead's id + select
      "24hr" template.
  13. Submit.
  14. Assert cadence
      created for the
      correct lead.
- **Small operator-
  surface gap fixes** per
  §5.d.

Backend baseline target:
~4,781 → ~4,782.
Frontend Vitest: ~198–202
→ ~200–205. Acceptance
suite: 10 → **11**.

### Increment 3 (M24.3) — Referral UI + journey

**Target session:** SESSION_183.

Referral adds the
`<ReferralLeadFormExtras>`
component. Journey
validates channel
attribution + backend
referrer FK (via API-side
assertion; modal does not
display referrer).

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
  channel="referral">`**.
- **Post-create opens
  `LeadDetailModal`** for
  the new referral lead.
- **Vitest coverage** for
  `<ReferralLeadFormExtras>`
  (~5–7 tests: picker
  search, tenant scope,
  optional handling,
  `referrer_lead_id`
  submission).
- **Seed:** referring-
  customer lead fixture
  already provisioned by
  M24.1's seed
  extension.
- **New journey**
  `acceptance/journeys/sales_manager/referral_intake.spec.ts`:
  1. Invoke seed.
  2. Login as salesperson.
  3. Navigate to
     `/dealer-ai-sales/leads`.
  4. Click `+ Referral`
     CTA.
  5. Fill base form +
     select referring
     customer from
     picker.
  6. Submit.
  7. Assert
     `LeadDetailModal`
     opens for the new
     lead.
  8. Assign via
     `AssignmentDropdown`.
  9. **Backend
     attribution
     assertion (API-
     side):** fetch new
     lead via
     `fetchAdminLeads`
     with id filter;
     assert
     `referrer_id`
     matches the
     referring
     customer's id.
  10. Assert list row
      shows
      `channel="referral"`.
- **Small operator-
  surface gap fixes**
  per §5.d.

Backend baseline target:
~4,782 → ~4,783. Frontend
Vitest: ~200–205 →
~207–212. Acceptance
suite: 11 → **12**.

### Increment 4 (M24.4) — Webhook integration-to-operator journey

**Target session:** SESSION_184.

**No new UI component.**
Ships a Playwright
journey that validates
the real integration
boundary + real operator
UI handling per §5.d.

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
- **Seed extension:** no
  new fixtures required.
- **New journey**
  `acceptance/journeys/sales_manager/webhook_integration_intake.spec.ts`:
  1. Invoke seed.
  2. `test.beforeEach`:
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
  3. Login as
     salesperson.
  4. Navigate to
     `/dealer-ai-sales/leads`
     with `channel`
     filter set to
     `listing_form`.
  5. Assert the
     ingested lead
     appears in the
     filtered list.
  6. Open
     `LeadDetailModal`
     via table row
     click.
  7. Assign via
     `AssignmentDropdown`.
  8. Assert assignment
     persists.
- **Small operator-
  surface gap fixes**
  per §5.d (rare — the
  browser-side flow
  uses shipped UI +
  M24.1 wire-in
  unchanged).

Backend baseline target:
~4,783 → ~4,783 (no code
change). Frontend Vitest:
~207–212 (unchanged).
Acceptance suite: 12 →
**13**.

**Collapse condition:**
if M24.4's journey-only
work is small enough
that no in-scope §5.d
fixes surface, M24.4
may fold into M24.5
close-out per §5.h
Option B evidence-sized
posture.

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
  operator journey +
  `LeadDetailModal`
  sales-side wire-in).
- `docs/roadmap/MILESTONE_24_RETROSPECTIVE.md`
  with §8 corrections
  (both M24.0 and
  M24.1-open) + §9
  next-candidate.
- `docs/roadmap/MILESTONE_25_PLANNING.md`
  skeleton (status:
  draft), elevating
  the three §3
  deferrals surfaced at
  M24.1 open (test-
  drive UI + referrer
  display + platform
  display).
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

## 8. Streak accounting (M24)

**Planning-time as-
recommended streak:
RESET TO 0.** Two
corrections landed on
the same milestone:

1. **SESSION_180 M24.0
   open:** §5.b + §5.d
   redirected before
   lock on the webhook
   operator-UI posture.
   Streak reset from 89
   → 0.
2. **SESSION_181 M24.1
   open:** §5.b + §5.d +
   §5.h revised for the
   downstream-verb UI
   substrate gap
   (implementation-time
   planning correction).
   Streak stays at 0
   (not further reset;
   not extended).

Both corrections were
meaningful and evidence-
based. Recording them
honestly preserves the
integrity of the
governance record.

Historical run
(preserved for the
record; not extended):
**89 planning-time as-
recommended M5.1 →
M23.0** across fourteen
consecutive milestones
(M10 → M23).

Post-M24.0 counter: 5
as-recommended at open
(§5.a + §5.c + §5.e +
§5.f + §5.g), 2
redirected at open
(§5.b + §5.d). At M24.1
open: 3 further revised
(§5.b + §5.d + §5.h)
after downstream-surface
verification. Post-lock
at M24.1 open, the
revised plan is stable
and ready for M24.1
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
  §5.b + §5.d M24.0
  redirect.
- ❌ Do NOT create a
  test-only backend
  endpoint or fake
  operator workflow to
  make the webhook
  journey fully
  browser-driven. Per
  §5.d.
- ❌ Do NOT ship a
  `<RecordTestDriveForm>`
  component or wire
  test-drive creation
  into `DealerAiSalesTestDrives`
  inside M24. Deferred
  per §3 deferral 12 to
  M25 candidate O2 sub-
  scope.
- ❌ Do NOT add
  `referrer_id` /
  "Referred by" display
  to `LeadDetailModal`
  inside M24. Deferred
  per §3 deferral 13 to
  M25 candidate.
- ❌ Do NOT add
  `platform` display to
  `LeadDetailModal`
  inside M24. Deferred
  per §3 deferral 14 to
  M25 candidate.
- ❌ Do NOT add new
  backend service
  verbs, DRF endpoints,
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
  the
  `CustomerLead.referrer`
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
  evidence.
