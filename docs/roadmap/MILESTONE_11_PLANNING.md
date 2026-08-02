---
title: "Milestone 11 — Implementation-Planning Pass"
status: draft
type: planning-artifact
generated: 2026-08-02
generated_at_session: SESSION_113 (post-M10-closeout)
milestone: 11
milestone_name: "Sales-side non-chat channels + customer-journey completeness"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_10_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_10_PLANNING.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/SALES_DEPARTMENT_MAPPING.md
---

# Milestone 11 — Implementation-Planning Pass

**Purpose.** Acceptance contract for Milestone 11
(Sales-side non-chat channels + customer-journey
completeness). Every implementation increment
cites back here for scope, invariants, and
refinement provenance. Mirrors the shape M3 /
M4 / M5 / M6 / M7 / M8 / M9 / M10 planning docs
proved out.

**Business objective (from `IMPLEMENTATION_ROADMAP.md`
§Milestone 11).** Extend the leads pipeline
beyond chat-originated leads to cover the walk-
in, phone, listing-platform-form, and referral
channels the sales research names. Add the
customer-journey artifacts the chat channel
does not produce today: test-drive record, deal
write-up (four-square-style), follow-up cadence
orchestration (24hr / 1wk / 30day / 90day / 6mo
/ 1yr), be-back tracking, referral capture +
attribution.

**Research anchors.** `SALES_DEPARTMENT_MAPPING.md`
§lead acquisition (channel mix percentages) +
§workflow (16-step sales workflow from lead
acquisition through be-back management) +
pains #1 (following up consistently) + #2
(forgetting callbacks) + #3 (poor CRM notes) +
#13 (managing multiple communication channels)
+ #15 (be-back promises) + #16 (working leads
across shifts).

**Zero implementation this session.** Planning
artifact only. SESSION_114 opens M11.1.

**Note.** This is a **planning skeleton**
created at M10.8 close per standing user
directive. The §5 load-bearing decisions and
§7 sequencing are **initial drafts** — expect
the user to refine at M11.0 open (or split
into per-increment §5-equivalent decisions
surfaced at each session open per the M10
pattern that proved out).

---

## 0. Engineering practices to preserve from M2-M10

Synthesized from the nine prior retrospectives.
Every practice below is a load-bearing
constraint on M11.

*(Mirrors the M10 §0 structure; the nineteen M10
lessons in `MILESTONE_10_RETROSPECTIVE.md` §6
carry forward with M11 evidence expected. Three
lessons are particularly relevant for M11.)*

Three lessons will get exercised hard at M11:

- **Lesson 8 — load-bearing decisions get user
  review BEFORE code.** M11 has a large design
  surface (multi-channel lead intake webhook
  contracts, test-drive record shape, deal
  write-up structure, cadence orchestration
  semantics, be-back scheduling model, referral
  attribution). Every §5 decision must surface
  at increment open, not silently at
  implementation time. **Twenty-nine
  consecutive as-recommended resolutions in M10
  set the trust posture; M11 should continue
  the pattern.**
- **Lesson 15 — plan-open pushback pattern.**
  When planning-time assumptions don't survive
  direct code inspection, surface with
  recommendations + trade-offs before code
  lands. M11's multi-channel intake shapes may
  need per-channel adapter modules that don't
  exist today.
- **Lesson 12 — prior-increment count
  assertions use `>=` not `==`.** Now project
  posture. Every M11 test asserting
  tenant-carrier / permission-class / etc.
  counts should use `>=N` + membership check
  from day one.

## 0.a Change log (implementation-time amendments)

Per M5/M6/M7/M8/M9/M10 §9 mandates, load-
bearing planning decisions may need narrow
amendment at implementation time as substrate
reality asserts itself. Every amendment
records the session, option, and the affected
sections.

### SESSION_114 · M11.1 open — all six §5 decisions resolved as-recommended

At SESSION_114 open the user approved all six
§5 planning decisions as-recommended per §9,
with no overrides. The M10-established
recommend-and-approve streak advances to 35
consecutive as-recommended resolutions
(M5.1 → M11.1 open).

Confirmed selections:

- **§5.a — `CustomerLead.channel` field +
  vocabulary.** Option A — additive
  CharField, fixed 5+1 vocab
  (`chat`/`walk_in`/`phone`/`listing_form`/`referral`/`other`),
  data migration backfills historical rows
  to `chat`.
- **§5.b — Listing-platform webhook shape.**
  Option A — one generic
  `POST /admin/leads/webhook/` + per-platform
  adapter modules under
  `services/leads/webhook_adapters/`.
- **§5.c — TestDrive attach shape.** Option A
  — mandatory FK to both `CustomerLead` +
  `Vehicle` (M11.2 scope; recorded here for
  model-shape stability).
- **§5.d — FollowUpCadence + Task shape.**
  Option A — two entities; task rows
  queryable (M11.4 scope).
- **§5.e — DealWriteup → CreditApplication
  flow.** Option A — server-side auto-CA-
  creation on handoff action (M11.3 scope).
- **§5.f — Operator UI scope.** Option C —
  MVP substrate at M11.1; extended UI in a
  follow-on increment (M10.7 §1.8.d
  precedent).

No amendments to §1–§8. Implementation may
proceed against the planning skeleton as
written.

### SESSION_116 · M11.3 open — handoff micro-decisions recorded

At M11.3 implementation time two field-
copy specifics surfaced beyond the §5.e
Option A shape decision. Both are narrow
implementation-time choices (not new load-
bearing planning decisions), resolved by
proceeding with defensible defaults and
recording here per the M5-M10 §0.a
convention:

1. **Auto-created CreditApplication
   `source_format` on handoff.**
   Default: `CREDIT_APP_FORMAT_TABLET`.
   Reason: the writeup + handoff both
   happen on the sales-manager's tablet
   in-store, so tablet is the accurate
   provenance. Overridable via kwarg on
   :func:`services.deal_writeups.hand_off_to_fandi`
   for edge cases (paper hand-off from
   the manager's desk).
2. **Field-copy shape from DealWriteup
   → CreditApplication.**
   - `applicant_full_name` ← `lead.name`
     (required by the M10.1 CA verb).
   - `notes` ← structured summary of
     the writeup terms
     (`vehicle_price`,
     `monthly_payment_target`,
     `term_months_target`,
     `apr_target`) so the F&I manager
     sees the deal parameters without
     opening the writeup separately.
   - No `applicant_ssn_last4` (not
     captured on the writeup; F&I fills
     in from the customer's credit-app
     paperwork).

Neither micro-decision closes any future
option — a subsequent planning pass can
change either the default source_format
or the field-copy shape without a
migration.

The M10 recommend-and-approve streak
remains 35 as-recommended (§5.a-§5.f);
these implementation-time defaults are
not counted against the streak per M10
§9 (planning-time decisions only).

### SESSION_117 · M11.4 open — cadence + beat micro-decisions recorded

At M11.4 implementation time three
substrate-shape defaults surfaced. All
three are implementation-time
selections that don't close future
options — resolved by proceeding with
the defaults and recording here per
the M11.3 precedent.

1. **Cadence templates: fixed constants.**
   The six named templates (`24hr`,
   `1wk`, `30day`, `90day`, `6mo`,
   `1yr`) live as module-level
   constants (`FOLLOW_UP_TEMPLATE_*`
   + `FOLLOW_UP_TEMPLATE_CHOICES`)
   matching the M11.1 lead-channel
   vocab-set pattern. Operator-
   configurable rows would be a
   larger planning decision (would
   require a `CadenceTemplate` entity
   + admin CRUD); deferred until
   operator evidence surfaces need.
2. **Beat schedule ownership: code-
   first bootstrap + DatabaseScheduler
   overlay.** The M11.4 orchestrator
   is added to
   `CELERY_BEAT_SCHEDULE` in
   `dealer_kit/settings.py` at the
   next M7 slot (06:00 project-time
   daily; M7.2-M7.5 occupy 02:00-
   05:00). Django-celery-beat's
   `DatabaseScheduler` (already
   configured per M7) surfaces the
   entry into the DB on first Beat
   start so operators can adjust
   without redeploy. Matches the
   M7.2-M7.5 posture unchanged.
3. **Task auto-skip: operator-
   triggered only.** `skip_task`
   verb requires an explicit call;
   the beat-surfacer task only
   flags stale tasks in
   :class:`JobRunLog`, never auto-
   transitions state. Auto-skip
   after N days would be a separate
   planning decision (needs
   operator input on the N default
   + the observability of quiet
   state changes); deferred.

None of the three close future
options. Streak stands at 35
as-recommended (planning-time
decisions only).

### SESSION_118 · M11.5 open — BeBack §5.g decisions recorded

§1.5 (BeBack tracking) shipped the
outline at M11.1 planning but was
not put to a §5 vote. Three §5.g
items surfaced at M11.5 open,
resolved with the M11.4-style
implementation-time defaults +
recorded here per the M11.3 / M11.4
precedent.

1. **§5.g.1 — BeBack attach shape:
   Option A.** Mandatory FK to
   `CustomerLead` (CASCADE). No FK
   to `Vehicle` — a be-back is
   about returning to the store,
   not necessarily the same
   vehicle (customers often
   return to negotiate a
   different unit or to check
   trade-in valuation on a
   different candidate). Matches
   SALES §step 15 documented
   reality.
2. **§5.g.2 — Reason vocabulary:
   Option A.** Fixed 4+1 vocab
   (`test_drive` /
   `bring_co_signer` /
   `bring_trade_in` / `other`),
   matching the M11.1 vocab-set
   pattern. Additional reason
   codes are a planning-time
   decision, not a code-refactor
   decision.
3. **§5.g.3 — No-show integration:
   Option B.** Dedicated M11.5
   Celery detector that runs at
   07:00 project-time daily,
   transitions `promised` →
   `no_show` when
   `promised_at + grace_period`
   passes without
   `actual_return_at`. Grace
   period configurable via
   `settings.BE_BACK_NO_SHOW_GRACE_HOURS`
   (default 4). Auto-starting a
   M11.4 `FollowUpCadence` on
   BeBack create (Option A) was
   rejected because it would
   spill the M11.5 state machine
   into the M11.4 cadence engine
   — keeping the no-show rule
   narrow to BeBack itself
   preserves clean separation.
   Manual `mark_no_show` verb is
   also exposed at the service +
   endpoint layer for operator
   overrides.

None close a future option.
Streak stands at 35
as-recommended (planning-time
decisions only).

### SESSION_119 · M11.6 open — Operator UI scoping decisions recorded

§5.f Option C (MVP substrate at
M11.1; extended UI at M11.6) was
confirmed at SESSION_114 open —
M11.6 is that follow-on. Three
implementation-time scoping
decisions surfaced at M11.6 open,
resolved with the recommended
options and recorded here per the
M11.3-M11.5 precedent.

1. **§5.f.1 — Route family:
   Option B.** New
   `/dealer-ai-sales/` route
   family with per-substrate
   child pages. Five new backend
   surfaces (channel intake,
   test-drive log, deal writeup,
   follow-up queue, be-back
   queue) warrant a distinct
   route family rather than tab-
   cramming the existing
   `/dealer-ai-leads/` page.
2. **§5.f.2 — MVP surface scope.**
   Four pages ship in M11.6:
   channel-filtered leads list,
   test-drive log, follow-up
   task work-queue (default
   filter "due today, pending"),
   be-back list with state
   filter. **DealWriteup + F&I
   handoff UI is deferred** to a
   follow-on because the handoff
   flow touches F&I integration
   and needs a distinct UX pass
   (workflow spans two personas
   — sales manager approves,
   F&I manager receives).
3. **§5.f.3 — Test target:** ~15
   Vitest tests per §7 M11.6.
   Backend delta 0 at M11.6
   (frontend-only). Mirrors M10.7
   Vitest coverage pattern
   (`DealerFandIDeals.test.tsx`
   as the reference).

None close a future option — the
deferred DealWriteup UI can land
in a subsequent M12+ increment
without reshaping M11.6's pages.
Streak stands at 35 as-
recommended (planning-time
decisions only).

**§5.f.4 addendum — read-only
list endpoints needed for
operator UI.** At M11.6
implementation time the scope
originally framed as "frontend-
only" hit a substrate reality:
M11.2 (TestDrive) and M11.5
(BeBack) shipped write endpoints
only, and the existing
`/admin/leads/` GET list has no
channel filter. A meaningful
operator UI needs list surfaces.
Three minimal read-only backend
additions land in the M11.6
commit alongside the frontend:

- **`GET /admin/leads/`** —
  extended to accept a
  `?channel=` filter (single or
  comma-separated), preserving
  the existing handed_off /
  urgency / since / ordering
  filters unchanged.
- **`GET /admin/test-drives/`**
  (new) — list with `?lead_id=`
  + `?vehicle_id=` +
  `?driven_since=` filters.
- **`GET /admin/be-backs/`**
  (new) — list with `?state=`
  + `?promised_since=` filters.

All three gated on
`IsSalesManagerOrOwnerAtActiveDealership`
(matches the M11.6 write
posture). No service-layer
changes; the endpoints are thin
QuerySet wrappers with the same
100-row default cap M10.7 uses.
Backend delta at M11.6: ~+8
tests. This is the smallest
substrate change that makes the
M11.6 UI operator-useful; it
doesn't reshape any M11.1-M11.5
write verb.

---

## 1. Design memo

### 1.0 The operational questions Milestone 11 must answer

Nine questions synthesized from
`SALES_DEPARTMENT_MAPPING.md`:

| # | Question | Research citation |
|---|---|---|
| 1 | **How does the platform intake a walk-in lead consistently?** | SALES §lead acquisition (walk-in channel) + pain #3 (poor CRM notes) |
| 2 | **How does the platform intake a phone lead consistently?** | SALES §lead acquisition (phone channel) + pain #13 (multi-channel) |
| 3 | **How does the platform intake a listing-platform-form lead consistently?** | SALES §lead acquisition (form / DR system channel) |
| 4 | **How does the platform intake a referral lead + attribute it?** | SALES §lead acquisition (referral channel) + workflow step 16 (referral capture) |
| 5 | **What test-drive record data does the platform capture?** | SALES §workflow step 6 (demonstration / test drive) |
| 6 | **What deal write-up (four-square) fields does the platform capture?** | SALES §workflow step 10 (deal write-up) |
| 7 | **How does the platform orchestrate follow-up cadence across roles?** | SALES §workflow steps 12-15 (follow-up + be-back) + pains #1 + #2 + #15 + #16 |
| 8 | **How does the platform track be-backs (customer promises to return)?** | SALES §workflow step 15 (be-back management) + pain #15 |
| 9 | **How does the platform link the M11 sales-side artifacts to M10 F&I workflow?** | SALES §workflow step 11 (F&I handoff) + M10 CreditApplication / DealStructure attach points |

### 1.1 Multi-channel lead intake

- **Business questions answered.** Q1, Q2,
  Q3, Q4.
- **Shape.** Extend `CustomerLead` model with
  a `channel` field from a fixed vocabulary
  (`chat` default (M1 legacy) / `walk_in` /
  `phone` / `listing_form` / `referral` /
  `other`). Additive per-channel intake
  surfaces: `POST /admin/leads/walk-in/`,
  `POST /admin/leads/phone/`, webhook
  endpoint(s) for listing platforms (contract
  TBD per §5 decision — one webhook or per-
  platform adapters?), `POST /admin/leads/referral/`
  with attribution fields (referrer =
  CustomerLead FK, referred_at, notes).
  Existing chat-origin lead intake unchanged
  (default channel + backward-compatible on
  historical rows).

### 1.2 Test-drive record entity

- **Business questions answered.** Q5.
- **Shape.** New `TestDrive` model. FK to
  `CustomerLead` + FK to `Vehicle` (attach
  shape TBD per §5 decision — nullable both
  vs mandatory both). Fields: `driven_at`
  datetime, `driven_by_user` FK to User
  (salesperson who accompanied — SET_NULL),
  `duration_minutes`, `route_notes`,
  `customer_reaction`, `objections_captured`
  (JSONField for structured objection
  vocabulary — objections list emerges from
  SALES §5 discovery vocab), `next_action`
  free text.

### 1.3 Deal write-up entity

- **Business questions answered.** Q6, Q9.
- **Shape.** New `DealWriteup` model (four-
  square-style summary tied to
  F&I handoff memo). FK to `CustomerLead`
  + FK to `Vehicle`. Fields: `vehicle_price`
  (proposed), `trade_allowance`, `down_payment`
  (proposed), `monthly_payment_target`, `term_months_target`,
  `apr_target`, `write_up_at` datetime,
  `written_up_by_user` FK User SET_NULL,
  `sales_manager_approved_at` nullable +
  `sales_manager_approved_by_user` FK User
  SET_NULL, `handed_off_to_fandi_at` nullable
  (link into M10.1 CreditApplication).

### 1.4 Follow-up cadence orchestration

- **Business questions answered.** Q7.
- **Shape.** New `FollowUpCadence` +
  `FollowUpTask` models (or single-entity
  with schedule-JSON — §5 decision).
  Cadence has named schedule (`24hr`,
  `1wk`, `30day`, `90day`, `6mo`, `1yr`)
  attached to a CustomerLead. Task rows are
  the scheduled points; each has
  `due_at`, `state` (`pending` /
  `completed` / `skipped`), `completed_by_user`
  FK User SET_NULL, `notes`. M7 async
  substrate schedules the tasks via Celery
  beat. Follow-up drafting (M3.3
  `services/follow_up.py`) is the drafting
  pattern; M11 adds scheduling.

### 1.5 Be-back tracking

- **Business questions answered.** Q8.
- **Shape.** New `BeBack` model. FK to
  `CustomerLead`. Fields: `promised_at`
  datetime (when the customer said they'd
  return), `promised_reason` (test drive /
  bring co-signer / bring trade-in /
  other), `actual_return_at` nullable,
  `follow_up_scheduled_at` (Celery-scheduled
  re-contact if no-show). `state`: `promised`
  / `returned` / `no_show`. Ties into
  §1.4 cadence orchestration for automatic
  re-contact scheduling.

### 1.6 Referral capture + attribution

- **Business questions answered.** Q4.
- **Shape.** Bundled with §1.1 channel
  intake. `CustomerLead.referrer` FK to
  parent CustomerLead (nullable, SET_NULL).
  Referred leads that close (via M10.5 Sale
  attach) get attribution back to referrer
  for future incentive tracking. Referral
  incentive payout logic deferred beyond
  M11 (accounting concern).

### 1.7 M10 F&I handoff integration

- **Business questions answered.** Q9.
- **Shape.** No new M11 entity. `DealWriteup.handed_off_to_fandi_at`
  populated when the F&I manager creates a
  CreditApplication from the write-up. §5
  decision: is the CA creation manually
  triggered from the DealWriteup UI, or
  does it require a distinct "start deal"
  action? Related — do we auto-copy any
  DealWriteup fields into the CA on
  creation?

### 1.8 Operator UI

- **Shape.** New sales-side operator
  surfaces (or extensions to existing).
  Options TBD per §5 decision:
  Option A — extend `/dealer-ai-leads/`
  with channel-filter + test-drive + write-
  up + cadence + be-back sub-tabs. Option
  B — new `/dealer-ai-sales/` route family
  with dedicated pages. Option C — MVP
  (channel filter + test-drive log only;
  cadence + be-back deferred to a follow-
  on increment).

### 1.9 Dashboard endpoint surface

- **Shape.** New DRF endpoints under
  `/api/dealer-ai/admin/` for the M11
  entities. Role-gated per §5 decision —
  likely reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  from M4 for admin surfaces + a new
  `IsSalespersonOrHigherAtActiveDealership`
  for salesperson-facing test-drive /
  write-up entry.

---

## 2. Non-goals (explicit)

- ❌ Listing-platform outbound syndication
  (belongs to Milestone 6 or a dedicated
  integrations milestone).
- ❌ Advertising-spend analytics.
- ❌ CSI survey integration.
- ❌ Referral incentive payout logic
  (accounting concern; belongs to a
  future milestone).
- ❌ Modification of M10 F&I workflow
  semantics.
- ❌ Modification of M9 Sale / Delivery
  workflow semantics.

---

## 3. Compatibility summary

*(To be filled at M11.1 open — after §5
decisions ratify shape. Placeholder rows:)*

- Backend test baseline unchanged at M11.0;
  target delta at M11 close TBD.
- Frontend Vitest baseline unchanged at
  M11.0; target delta at M11 close TBD.
- M1-M10 substrates preserved. Consumption
  is FK-only + additive extensions per the
  M8 §6 lesson 11 pattern.

---

## 4. Migration path (per-increment)

*(To be filled at M11.1 open.)*

---

## 5. Scope discipline + load-bearing decisions

### 5.a `[NEEDS-DECISION-BEFORE-M11.N]` — Channel vocabulary + `CustomerLead.channel` field

**Question.** Add `channel` field to
`CustomerLead` as an additive extension?
Vocabulary: fixed 5-value set (`chat` /
`walk_in` / `phone` / `listing_form` /
`referral`) + `other` fallback?

**Options.**

- **Option A** — additive `channel` CharField
  with 5+1 vocab; historical chat-origin
  rows backfilled to `chat` in migration.
- **Option B** — nullable `channel` CharField
  with 5+1 vocab; historical rows carry NULL.
- **Option C** — per-channel entities
  (`WalkInLead`, `PhoneLead`, etc.) instead
  of a channel field. Overkill.

**Recommended for user review:** Option A —
matches M8 §6 lesson 11 additive-extension
pattern with a required-not-nullable
constraint plus a data migration
backfilling historical rows to `chat`.

### 5.b `[NEEDS-DECISION-BEFORE-M11.N]` — Listing-platform webhook shape

**Question.** One generic webhook endpoint
(`POST /admin/leads/webhook/`) with per-
platform adapter dispatch inside, or per-
platform endpoints (`POST /admin/leads/autotrader/`
etc.)?

**Options.**

- **Option A** — one generic webhook +
  adapter module per platform in
  `services/leads/webhook_adapters/`.
  Extensible.
- **Option B** — per-platform endpoints +
  per-platform serializer. More URLs, more
  code, easier debugging.

**Recommended for user review:** Option A —
adapter pattern scales as platforms are
added without proliferating URLs.

### 5.c `[NEEDS-DECISION-BEFORE-M11.N]` — TestDrive attach shape

**Question.** Mandatory FK to both
`CustomerLead` and `Vehicle`, or nullable
both (walk-in test drives with no CRM
record captured on-the-spot)?

**Options.**

- **Option A** — mandatory FK to both. Test
  drives without a lead record shouldn't
  happen operationally (salesperson creates
  the lead at handshake before the drive).
- **Option B** — nullable both with clean()
  requiring at least Lead. Handles the
  "vehicle demonstration without a specific
  lead in hand" edge case.

**Recommended for user review:** Option A —
force operational discipline. If the "no
CRM record yet" case emerges, add nullable
capability later.

### 5.d `[NEEDS-DECISION-BEFORE-M11.N]` — FollowUpCadence + Task shape

**Question.** Two-entity model
(`FollowUpCadence` header + `FollowUpTask`
rows) vs single-entity with schedule-JSON?

**Options.**

- **Option A** — two entities. Named
  cadences reusable across leads;
  individual tasks queryable /
  transitionable independently.
- **Option B** — single entity with JSON
  schedule + task-state array. Simpler
  schema but less queryable ("show me all
  tasks due today across all leads" needs
  JSON introspection).

**Recommended for user review:** Option A —
task rows are the operator's primary work
unit; keep them queryable.

### 5.e `[NEEDS-DECISION-BEFORE-M11.N]` — DealWriteup → CreditApplication flow

**Question.** Does the DealWriteup UI
directly trigger CreditApplication creation
(handoff), or does F&I manually create the
CA?

**Options.**

- **Option A** — DealWriteup has an "Hand
  off to F&I" action that POSTs to the
  M10.1 CreditApplication endpoint
  server-side (auto-copying applicable
  fields like applicant name from the
  lead).
- **Option B** — DealWriteup marks
  `handed_off_at` when F&I creates the CA
  manually (soft link only).

**Recommended for user review:** Option A —
matches operator reality (sales walks the
customer to F&I with the deal write-up in
hand; the platform should make that a one-
click handoff).

### 5.f `[NEEDS-DECISION-BEFORE-M11.N]` — Operator UI scope

**Question.** Extend `/dealer-ai-leads/`
with sub-tabs (Option A), new
`/dealer-ai-sales/` route family
(Option B), or narrower MVP with just
channel filter + test-drive log +
cadence display (Option C)?

**Options.**

- **Option A** — extend leads page.
  Consistent with existing UX.
- **Option B** — new route family.
  Distinct affordance for sales-
  workflow-focused view.
- **Option C** — MVP. Ship the substrate,
  operator UI polish in a follow-on
  increment.

**Recommended for user review:** Option C
— MVP. Matches M10.7 §1.8.d Option A
precedent. Ship the substrate + a minimal
list view; extended UI when operator
evidence surfaces need.

### 5.g Test posture

Standard. TestCase for models + services;
APIClient for endpoints. Every write path
gated on the appropriate permission class.
Prior-increment count assertions use `>=`
not `==` per M9 §6 lesson 14 / M10
lesson 12.

---

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 11
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
   §6 (nineteen lessons carry into M11)
6. `docs/CAPABILITY_MATRIX.md` §7k
7. `docs/research/SALES_DEPARTMENT_MAPPING.md`

---

## 7. Sequencing draft

*(Initial draft — user refinement expected
at M11.0 open. Sequence adjustable.)*

### Increment 0 (M11.0) — Planning refinement + first-decision review

**Scope.** This session (SESSION_114).
Review §5 decisions with user; refine §7
sequencing if needed. Optional narrow
implementation start.

### Increment 1 (M11.1) — Channel intake + CustomerLead extension

**Scope.** Additive `CustomerLead.channel`
+ data migration backfill + per-channel
POST endpoints (walk-in + phone + referral
inline; webhook adapter shape TBD per §5.b).

**Tests.** ~25 focused.

### Increment 2 (M11.2) — TestDrive entity

**Scope.** New `TestDrive` model + service
+ endpoints + operator log.

**Tests.** ~20 focused.

### Increment 3 (M11.3) — DealWriteup entity + F&I handoff

**Scope.** New `DealWriteup` model + service
+ endpoints + F&I handoff action per §5.e
Option A (auto-CA-creation).

**Tests.** ~25 focused.

### Increment 4 (M11.4) — Follow-up cadence orchestration

**Scope.** `FollowUpCadence` +
`FollowUpTask` models + Celery-beat
scheduling + operator task list.

**Tests.** ~30 focused (larger — includes
Celery-beat schedule locking).

### Increment 5 (M11.5) — Be-back tracking

**Scope.** New `BeBack` model + no-show
auto-scheduling via M11.4 cadence
orchestration.

**Tests.** ~20 focused.

### Increment 6 (M11.6) — Operator UI

**Scope.** Extend `/dealer-ai-leads/` (or
new `/dealer-ai-sales/` per §5.f decision)
with the M11 surfaces.

**Tests.** ~15 backend + ~25 frontend.

### Increment 7 (M11.7) — Closeout

**Scope.** Documentation-only.
Retrospective + capability matrix §7l +
roadmap flip + planning frontmatter +
session-start refresh +
`MILESTONE_12_PLANNING.md` per standing
user directive + coordinated commit +
push.

---

## 8. Related documents

- `docs/PROJECT_RULES.md`
- `docs/DOC_GOVERNANCE.md`
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  §Milestone 11
- `docs/roadmap/AUTHENTICATION_MODEL.md`
- `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
- `docs/roadmap/MILESTONE_10_PLANNING.md`
- `docs/research/SALES_DEPARTMENT_MAPPING.md`
- `docs/CAPABILITY_MATRIX.md` §7k
- Current source code — authoritative.

---

## 9. Load-bearing decisions summary — items requiring user review before M11.N

Every `[NEEDS-DECISION-BEFORE-M11.N]` in
this document, consolidated:

1. **§5.a — CustomerLead.channel field +
   vocabulary.** Recommended: Option A
   (additive with backfill).
2. **§5.b — Listing-platform webhook
   shape.** Recommended: Option A (one
   generic webhook + adapter dispatch).
3. **§5.c — TestDrive attach shape.**
   Recommended: Option A (mandatory both
   FKs).
4. **§5.d — FollowUpCadence + Task
   shape.** Recommended: Option A (two
   entities).
5. **§5.e — DealWriteup → CreditApplication
   flow.** Recommended: Option A (auto-
   create CA from handoff action).
6. **§5.f — Operator UI scope.**
   Recommended: Option C (MVP).

All six recommendations follow the M10
pattern proven at scale (twenty-nine
consecutive as-recommended resolutions).
User is expected to review + confirm /
reopen each at M11.1 open per the
established plan-open pushback pattern
(M9 §6 lesson 15 + M10 §6 lesson 15).
