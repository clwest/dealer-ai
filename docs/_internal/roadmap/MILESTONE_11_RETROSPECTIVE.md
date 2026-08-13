---
title: "Milestone 11 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-02
sessions: SESSION_114 → SESSION_120
milestone: 11
milestone_name: "Sales-side non-chat channels + customer-journey completeness"
related:
  - docs/roadmap/MILESTONE_11_PLANNING.md
  - docs/roadmap/MILESTONE_10_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 11
---

# Milestone 11 — Retrospective

Written at Milestone 11 close (SESSION_120).
Records what was planned, what shipped, what
deviated and why, and lessons carried forward
for Milestone 12 and beyond. Mirrors the
`MILESTONE_10_RETROSPECTIVE.md` structure.

## 1. Planned scope

`MILESTONE_11_PLANNING.md` at SESSION_113
close defined the milestone as the sales-side
non-chat channels + customer-journey
completeness substrate: extend the chat-only
lead pipeline to cover walk-in / phone /
listing-form / referral intake, and add the
customer-journey artifacts the chat channel
does not produce (test-drive record, deal
write-up + F&I handoff, follow-up cadence
orchestration, be-back tracking + no-show
detection). §1.0 named nine operational
questions synthesized from
`SALES_DEPARTMENT_MAPPING.md` (§lead
acquisition + §workflow steps 6 / 10 / 11 /
12-15 / 15-16 + §pains 1-3 / 13 / 15-16).

§1.1–§1.8 followed with eight design memos
(multi-channel intake, TestDrive, DealWriteup,
FollowUpCadence orchestration, BeBack
tracking, referral capture bundled with
§1.1, M10 F&I handoff integration, operator
UI). §5.a–§5.f drafted six load-bearing
decisions **all flagged
`[NEEDS-DECISION-BEFORE-M11.N]`**. §7
sequenced seven increments (M11.1–M11.7).

**Original §7 sequencing shipped verbatim.**
The six SESSION_114 decisions confirmed as-
recommended at M11.1 open (Options A / A / A
/ A / A / C). Additional implementation-time
micro-decisions surfaced at M11.3 / M11.4 /
M11.5 / M11.6 open and were recorded in §0.a
amendments per the M5-M10 precedent — but
per M10 §9 those are **implementation-time
defaults, not planning-time decisions**, so
they do not count against the streak. **The
streak is 35 planning-time as-recommended
M5.1 → M11.1 open** — a signal that the
planning framework held across two
milestones now.

## 2. What actually shipped

Every §3 compatibility item verified true;
enumeration below.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M11.0 planning | 113 | `MILESTONE_11_PLANNING.md` (draft at M10.8 close) resolving zero load-bearing decisions and leaving six for user review at M11.1 open + additional design questions across §1.2 / §1.3 / §1.4 / §1.5 / §1.6 / §1.7 / §1.8 (deferred to per-session opens) | (in M10.8 close commit `11642a7`) |
| M11.1 Channel intake + CustomerLead extension | 114 | Additive `CustomerLead.channel` field (5+1 vocab: `chat` default / `walk_in` / `phone` / `listing_form` / `referral` / `other`) + data-migration backfill (via AddField default) + `CustomerLead.referrer` self-FK (SET_NULL) + migration `0032_m111_lead_channel_and_referrer`. New `services/leads/` package (channel_intake.py) with four verbs (`record_walk_in_lead` / `record_phone_lead` / `record_referral_lead` + cross-tenant referrer guard / `record_webhook_lead` dispatching to adapter registry) + two domain errors (`CrossTenantReferrerError` / `UnknownWebhookPlatformError`). New `services/leads/webhook_adapters/` sub-package with adapter registry + first shipped adapter `generic` (documented dealer-owned envelope; not a fabricated proprietary shape — platform-specific adapters like `autotrader` land as sibling modules when operator evidence surfaces field shapes). Four DRF admin endpoints under `admin/leads/` (walk-in / phone / referral / webhook). All gated on `IsSalesManagerOrOwnerAtActiveDealership` (M4 permission class reused). 28 focused tests. Tenancy carrier count unchanged (34; `CustomerLead` was already a carrier). **Six §5 decisions confirmed as-recommended at session open** (§5.a Option A additive channel + backfill; §5.b Option A generic webhook + adapter dispatch; §5.c Option A mandatory TestDrive both FKs — recorded for M11.2; §5.d Option A two-entity FollowUp — recorded for M11.4; §5.e Option A server-side auto-CA at handoff — recorded for M11.3; §5.f Option C MVP UI at M11.6). | `b0e23ad` |
| M11.2 TestDrive entity + service + endpoint | 115 | New `TestDrive` model + migration `0033_m112_test_drive_entity`. Mandatory FKs to `CustomerLead` + `Vehicle` (both CASCADE) per §5.c Option A. Optional `driven_by_user` FK to auth User (SET_NULL — preserves historical drive record on user delete). Fields per §1.2: `driven_at` DateTime + `duration_minutes` PositiveInteger nullable + `route_notes` / `customer_reaction` / `next_action` TextField + `objections_captured` JSONField default `[]` (free-list at M11.2; structured vocabulary lookup deferred to M12+ if analytics need it). Cross-tenant `clean()` guard on both `lead` + `vehicle` FKs. New `services/test_drives/` package with `record_test_drive` verb + `CrossTenantTestDriveError`. `POST /admin/test-drives/` endpoint gated on `IsSalesManagerOrOwnerAtActiveDealership` (reused). Tenancy carrier 34 → 35. 23 focused tests. **§5.c Option A was pre-confirmed at M11.1 open** — no new load-bearing decisions surfaced at M11.2 implementation time. | `4056ae0` |
| M11.3 DealWriteup + F&I handoff | 116 | New `DealWriteup` model (four-square worksheet) + migration `0034_m113_deal_writeup_entity`. Mandatory FKs to `CustomerLead` + `Vehicle` (both CASCADE). Four-square nullable DecimalFields (`vehicle_price` / `trade_allowance` / `down_payment` / `monthly_payment_target` / `apr_target`) + `term_months_target` + `write_up_at` DateTime + `written_up_by_user` + `sales_manager_approved_at` + `sales_manager_approved_by_user` (both nullable) + `handed_off_to_fandi_at` nullable (linking key to M10.1 CA is the shared `lead` FK, not a direct FK — CA outlives writeup per M10.1 retention lock). Cross-tenant `clean()` on both `lead` + `vehicle`. New `services/deal_writeups/` package with three verbs: `record_deal_writeup` (mandatory both FKs) + `approve_deal_writeup` (idempotent re-approval overwrites) + `hand_off_to_fandi` (`@transaction.atomic` wraps timestamp update + M10.1 `record_credit_application` call per §5.e Option A). Three domain errors: `CrossTenantDealWriteupError` / `WriteupNotApprovedError` (409 — handoff requires prior approval) / `WriteupAlreadyHandedOffError` (409 — idempotency guard prevents duplicate M10.1 CA rows with active retention clocks). Three DRF endpoints under `admin/deal-writeups/`. Tenancy carrier 35 → 36. 33 focused tests. **Two implementation-time micro-decisions recorded in §0.a M11.3 amendment** (auto-CA `source_format` defaults to `tablet` — overridable; DealWriteup → CA field-copy: `applicant_full_name` ← `lead.name` + `notes` ← structured four-square summary; no SSN copy). Neither closes a future option; streak stays at 35 planning-time as-recommended. | `555568e` |
| M11.4 FollowUpCadence + FollowUpTask + Celery-beat | 117 | Two-entity model per §5.d Option A. `FollowUpCadence` header (one per lead per template) + `FollowUpTask` rows (scheduled contact points). Six fixed template constants + `FOLLOW_UP_TEMPLATE_OFFSETS` dict with per-template day-offset schedules (`24hr`: [1] / `1wk`: [1,3,7] / `30day`: [1,3,7,14,30] / `90day`: [1,7,30,60,90] / `6mo`: [7,30,90,180] / `1yr`: [30,90,180,365]). Three-state task machine (`pending` default → `completed` / `skipped`; terminal states final). Cadence + task cross-tenant `clean()` guards. New `services/follow_ups/` package with four verbs (`start_cadence` `@transaction.atomic` seeds tasks; refuses duplicate active per lead+template; `complete_task` + `skip_task` pending → terminal; `pause_cadence` idempotent flip). Five domain errors including `TaskAlreadyTerminalError` (409). Two-task Celery orchestrator (`surface_due_follow_up_tasks_for_tenant` + `_for_all_tenants`) wired into Beat at 06:00 project-time daily via new `CELERY_BEAT_SCHEDULE` entry. **Beat surfacer is read-only — counts + logs due pending tasks per tenant but never mutates state** (operator intent required for every transition). Five DRF admin endpoints under `admin/follow-up-cadences/` + `admin/follow-up-tasks/` (create cadence, pause cadence, list tasks with state / due_before / limit filters, complete task, skip task). Migration `0035_m114_follow_up_cadence_and_task`. Tenancy carriers 36 → 38. Celery-beat task families 4 → 5. 44 focused tests. **Three implementation-time micro-decisions recorded in §0.a M11.4 amendment** (fixed template constants not operator-configurable; DatabaseScheduler overlay; operator-triggered state transitions only). | `d8bd665` |
| M11.5 BeBack tracking + no-show detector | 118 | New `BeBack` model per §5.g Options A/A/B. Mandatory FK to `CustomerLead` CASCADE; **no `Vehicle` FK** (be-backs are about returning to the store, not necessarily the same unit). Fixed 4+1 reason vocab (`test_drive` / `bring_co_signer` / `bring_trade_in` / `other`). Three-state machine (`promised` default → `returned` / `no_show`; terminal states final). `actual_return_at` nullable DateTime (populated on returned; leaves null on no_show by definition). Cross-tenant `clean()` on `lead`. New `services/be_backs/` package with three verbs (`record_be_back` / `mark_returned` sets timestamp default now / `mark_no_show` leaves return null). Three domain errors including `BeBackAlreadyTerminalError` (409). Two-task Celery detector (`detect_no_show_be_backs_for_tenant` + `_for_all_tenants`) wired into Beat at 07:00 project-time daily. **Detector transitions state** — the first M11 Celery task that mutates state (deliberate contrast with the M11.4 read-only surfacer; the promise is the customer's, the task completion is the operator's). Grace period configurable via `BE_BACK_NO_SHOW_GRACE_HOURS` env (default 4). Manual `mark_no_show` verb + endpoint also exposed for operator override. Three DRF endpoints under `admin/be-backs/`. Migration `0036_m115_be_back_entity`. Tenancy carrier 38 → 39. Celery-beat task families 5 → 6. 29 focused tests. **Three §5.g items surfaced at M11.5 open** (§1.5 was outlined at M11.1 planning but not put to a §5 vote); all resolved with recommended options and recorded in §0.a M11.5 amendment. Streak stays at 35 (§5.g items are implementation-time defaults per M11.3/M11.4 precedent). | `186e35a` |
| M11.6 Operator UI | 119 | First M11 frontend increment. New `/dealer-ai-sales/` route family with four pages consuming the M11.1-M11.5 backend surface: `DealerAiSalesLeads.tsx` (channel-filtered lead list), `DealerAiSalesTestDrives.tsx` (drive log), `DealerAiSalesFollowUps.tsx` (work-queue with optimistic complete/skip inline), `DealerAiSalesBeBacks.tsx` (list with optimistic mark-returned / mark-no-show). New `frontend/src/lib/salesApi.ts` wrapping every M11.1-M11.5 admin verb (DealWriteup verbs typed but no UI at M11.6 per §5.f MVP scoping — handoff flow spans two personas + needs distinct UX pass; deferred). Existing `AdminLeadListSerializer` extended with `channel` + `referrer` fields (additive). `fetchAdminLeads` extended with `channel?: string[]` param. **§5.f.4 substrate addendum** — three read-only backend list endpoints added at M11.6 to make the UI operator-useful (`?channel=` filter added to existing `admin/leads/`; new `GET /admin/test-drives/list/`; new `GET /admin/be-backs/list/`); all three gated on `IsSalesManagerOrOwnerAtActiveDealership` (reused); no service-layer changes. Backend +8 tests + frontend +16 Vitest tests (target ~15). Backend baseline 3,887 → 3,895; frontend baseline 51 → 67. DRF admin surface 80 → 82. Frontend operator routes 11 → 15. Zero migrations. Zero tenancy carrier changes. **Three §5.f scoping decisions + one substrate addendum recorded in §0.a M11.6 amendment**. | `b268536` |
| M11.7 Closeout | 120 | Documentation-only per M10.8 precedent. Six close-out docs (this retrospective + capability matrix §7l + implementation roadmap §Milestone 11 flip + planning doc frontmatter flip + session-start refresh + M12 planning skeleton) + coordinated commit landing all M11.7 docs. **Milestone 11 — Sales-side non-chat channels + customer-journey completeness — SHIPPED.** Batch push of seven local commits (SESSION_113 hash fixup + M11.1 through M11.7) queued for user authorization. | (this commit) |

## 3. What was NOT shipped (deferred, not dropped)

Every deferral recorded with a clear
re-entry path.

**In-milestone deferrals:**

1. **DealWriteup + F&I handoff UI (M11.6
   deferred).** M11.3 shipped the backend
   substrate (record + approve + handoff
   verbs; three endpoints; auto-CA-creation
   at handoff). The M11.6 MVP UI omitted
   the DealWriteup pages because the
   handoff flow spans two personas (sales
   manager approves + F&I manager receives
   the auto-created CA) and needs a
   distinct UX pass. Verbs + types are
   typed in `salesApi.ts` so a follow-on
   doesn't re-declare them. M12
   candidate.
2. **Delivery adapters for follow-up /
   be-back notifications.** M11.4's beat
   surfacer counts due tasks + logs
   them; M11.5's detector transitions
   no-show state. Neither dispatches
   SMS/email. Actual outbound delivery
   (Twilio / SendGrid / etc.) is a
   separate integration substrate; the
   task-list endpoint already exposes
   the operator work-queue for
   consumption by a delivery adapter or
   for human-in-the-loop drafting.
3. **Operator-configurable cadence
   templates (M11.4 deferred).** §0.a
   M11.4 decision 1 shipped six fixed
   template constants. Operator-
   configurable rows require a
   `CadenceTemplate` entity + admin CRUD;
   deferred until operator evidence
   surfaces need.
4. **Auto-skip of stale tasks (M11.4
   deferred).** §0.a M11.4 decision 3
   shipped operator-triggered state
   transitions only. Auto-skip after N
   days would be a separate planning
   decision (needs operator input on N
   default + observability of quiet
   state changes).
5. **Auto-cadence-on-BeBack integration
   (M11.5 deferred).** §5.g.3 Option B
   chose a dedicated M11.5 detector
   over auto-starting a M11.4
   FollowUpCadence on BeBack create.
   The two systems can be wired
   together in a follow-on when
   operator evidence names the specific
   cadence template.
6. **`reopen_task` verb for terminal
   follow-up tasks.** M11.4 terminal
   states are final at M11.4. A future
   `reopen_task` verb can add the un-do
   path when the operator UI surfaces
   the need. Same shape considered for
   M11.5 BeBack terminal states.
7. **Named-platform webhook adapters
   (Autotrader / Cars.com / Facebook
   Marketplace / CarGurus).** M11.1
   shipped the `generic` adapter + the
   registry substrate. Named-platform
   adapters plug in as sibling modules
   when operator evidence surfaces
   platform-specific envelope shapes.
   Not fabricating proprietary shapes
   without evidence per project rule 3
   (research-before-design).

**Cross-milestone carry-forwards** (still
deferred from M10 or earlier):

- **Photo / document upload plumbing** —
  M10.4/M10.5/M10.7 deferral. No M11
  increment surfaced need.
- **Full F&I operator UI (7-step
  workflow)** — M10.7 two-tab MVP still
  the current F&I surface. M11.6 shipped
  the sales-side UI counterpart; the F&I
  side stays at the M10.7 shape.
- **Server-side pagination on all admin
  lists** — carry-forward from M10.7.
  M11.6 list endpoints use the same
  100-row server cap.
- **Bureau-response / lender-portal /
  DMS integrations** — carry-forward
  from M10.
- **BHPH portfolio + collections** —
  Milestone 12 substrate.
- **Accounting integration** — future
  milestone.
- **`AnalyticsCache` materialization
  layer** — carry-forward from M8. No
  M11 endpoint produced latency
  evidence justifying materialization.

**No planned scope dropped** in the sense
of a shipped-but-broken feature or
silently-missing invariant. Every
deferral has a re-entry path.

## 4. Deviations from plan

Two shape adjustments landed at
implementation time, both recorded in §0.a
amendments before code shipped:

1. **§5.g items surfaced at M11.5 open**
   — §1.5 (BeBack) was outlined at M11.1
   planning but not put to a §5 vote.
   Three items resolved at M11.5 open
   with recommended options (mandatory
   lead FK + no vehicle FK; fixed 4+1
   reason vocab; dedicated M11.5
   detector). Not counted against the
   streak per M10 §9 (implementation-
   time defaults only).
2. **§5.f.4 substrate addendum at M11.6
   open** — M11.6 was framed as
   "frontend-only" in the planning doc,
   but M11.2 (TestDrive) and M11.5
   (BeBack) shipped write-only
   endpoints, and the existing
   `admin/leads/` GET list had no
   channel filter. Three minimal read-
   only backend list additions landed
   in the M11.6 commit alongside the
   frontend — channel filter on existing
   `admin/leads/` + new
   `GET /admin/test-drives/list/` + new
   `GET /admin/be-backs/list/`. No
   service-layer changes; no new
   permission class. Explicit in §0.a
   M11.6 amendment §5.f.4. Backend
   delta 0 → +8 at M11.6 (target ~15
   Vitest tests + 8 backend
   additions).

**Structural patterns established:**

1. **Two-verb transition pattern
   (M11.5 no-show detector).** M11.5's
   Celery detector auto-transitions
   `promised` → `no_show`; the manual
   `mark_no_show` endpoint also exists.
   Deliberate — the operator override
   handles the "customer called to
   cancel before grace elapses" case
   that the automatic detector alone
   cannot address. This differs from
   M10.5's two-verb pattern (both verbs
   were operator-triggered); here one
   is auto, one is manual, but both
   land at the same state.
2. **Read-only surfacer vs state-
   transitioning detector.** M11.4's
   beat surfacer is read-only (operator
   intent required); M11.5's detector
   mutates state (grace period is
   objective). This is the deliberate
   design contrast that gave both
   substrate shapes clean scope
   boundaries. Future beat tasks should
   pick the shape that matches whether
   the trigger is operator intent
   (surfacer) vs elapsed condition
   (detector).
3. **Atomic sibling-service side
   effects (M11.3 handoff).**
   `hand_off_to_fandi` wraps timestamp
   update + M10.1 CA auto-creation in a
   single `@transaction.atomic` — same
   pattern as M10.6's atomic cross-
   model side effects but crossing the
   M10 F&I boundary. The refusal to
   re-handoff (`WriteupAlreadyHandedOffError`)
   is the idempotency guard preventing
   duplicate M10.1 retention clocks.
4. **Vocab-set exact assertions vs
   growth-only `>=`.** M11 tests use
   exact-set equality on M11.1 channel
   vocab (5+1) + M11.4 template vocab
   (6) + M11.5 reason vocab (4+1) +
   M11.5 state vocab (3). Rationale:
   these are planning-locked vocabs;
   adding a member is a planning
   decision, not a code-refactor
   decision. **Growth-only lists (M9
   §6 lesson 14 / M10 §6 lesson 12)
   still use `>=`** — tenant-carriers,
   permission classes, routes. **Both
   patterns coexist.**

## 5. Compatibility

Every §3 compatibility row verified true.

- **Backend test baseline:** **3,895
  pass**, 1 skipped, 0 fail at
  SESSION_119 close. Delta: **+165
  tests** over M10 close baseline
  (3,730 → 3,895); 0 regressions.
- **Frontend Vitest baseline:** **67
  pass** at SESSION_119 close (was 51
  at M10 close; +16 exactly per M11.6
  target).
- **M1 CustomerLead substrate byte-for-
  byte preserved.** M11.1 extension is
  additive (two new columns with
  default backfill). Chat funnel
  intake unchanged; historical rows
  backfilled to `channel="chat"`.
- **M4 permission class reused across
  every M11 write endpoint.** Zero
  permission-class drift.
- **M7 Celery-beat substrate
  preserved.** M11.4 + M11.5 added two
  Beat entries via
  `CELERY_BEAT_SCHEDULE` in
  `dealer_kit/settings.py`; no
  changes to
  `dealer_kit/celery.py` or
  `services/jobs/instrumentation.py`.
- **M10.1 CreditApplication + retention
  lock preserved.** M11.3 `hand_off_to_fandi`
  calls the existing
  `record_credit_application` verb
  unchanged; M10.1 retention lock still
  refuses unexpired deletes.
- **M10.7 F&I frontend surface
  preserved.** M11.6 added a sibling
  `/dealer-ai-sales/` route family;
  `/dealer-ai-f-and-i/` unchanged.
- **Tenancy carriers 34 → 39.** M11.1
  added 0 (CustomerLead already a
  carrier), M11.2 added `TestDrive`
  (35), M11.3 added `DealWriteup` (36),
  M11.4 added `FollowUpCadence` (37) +
  `FollowUpTask` (38), M11.5 added
  `BeBack` (39). M11.6 added 0.
- **Permission classes: 8
  (unchanged).** Every M11 endpoint
  reused `IsSalesManagerOrOwnerAtActiveDealership`
  (M4). Zero new permission classes
  across all six increments.
- **DRF admin surface: 64 → 82** (+18
  M11 endpoints across M11.1 (+4),
  M11.2 (+1), M11.3 (+3), M11.4 (+5),
  M11.5 (+3), M11.6 (+2 list
  endpoints)).
- **Celery-beat task families: 4 → 6.**
  M11.4 added `follow-up-task-surface-
  daily-06-00`; M11.5 added `be-back-
  no-show-detector-daily-07-00`.
  Preserves the non-overlapping-window
  pattern (M7.2 02:00 → M7.5 05:00 →
  M11.4 06:00 → M11.5 07:00).
- **Frontend operator routes: 11 →
  15.** M11.6 added four
  `/dealer-ai-sales/*` routes.
- **Migrations `0032`–`0036`** shipped
  at M11.1 (+1), M11.2 (+1), M11.3 (+1),
  M11.4 (+1), M11.5 (+1). M11.6 shipped
  no migrations (three new list
  endpoints; one serializer field
  addition). M11.7 shipped no
  migrations.
- **Service surface added:**
  - `services/leads/` (M11.1) —
    channel_intake + webhook_adapters.
  - `services/test_drives/` (M11.2).
  - `services/deal_writeups/` (M11.3).
  - `services/follow_ups/` (M11.4) —
    cadence + tasks (Celery).
  - `services/be_backs/` (M11.5) —
    be_back + tasks (Celery).
- **`services/tenancy.py`
  `_TENANT_CARRIER_MODEL_NAMES`
  extended in place** at M11.2, M11.3,
  M11.4, M11.5. Every extension carries
  a comment citing the session +
  planning-doc §.

## 6. Lessons

**Nineteen** lessons carried forward for
Milestone 12 and beyond. Sixteen inherit
from M10 §6 with M11 evidence; three are
new to M11.

1. **Increment discipline.** Every M11
   sub-increment shipped independently
   verifiable in one session. Every
   session opened with load-bearing
   decisions (planning-time §5 items
   at M11.1 open; implementation-time
   micro-decisions at M11.3-M11.6
   opens) recorded in §0.a before code
   landed. Carry-forward.

2. **Backend-first architecture;
   frontend never owns business rules.**
   M11.1-M11.5 shipped zero frontend.
   M11.6 wired four pages as pure
   consumers of the M11 admin surface.
   `written_up_by_user` /
   `sales_manager_approved_by_user` /
   `driven_by_user` /
   `completed_by_user` FK values sourced
   server-side from `request.user` at
   the endpoint layer, not client body
   — same audit-trail pattern
   established at M10.4 stipulation +
   M10.6 chargeback. Carry-forward.

3. **Provider-neutral boundaries.** No
   new provider dependencies added by
   M11. Beat entries wired against
   existing `django_celery_beat`
   `DatabaseScheduler` substrate.
   `@instrumented_task` decorator
   reused for M11.4 + M11.5 tasks
   unchanged. No new LLM integration
   in M11. Carry-forward.

4. **Service ownership — one
   authoritative write path per
   operation.** Five service packages
   under `services/`, each owning its
   entity's writes. Endpoint layer is
   thin translation. No business
   logic in views. `services/leads/`
   webhook adapter registry is the
   only substrate expansion beyond
   single-module packages — the
   adapter dispatch pattern models
   how M12+ might handle multi-
   provider substrates.
   Carry-forward.

5. **Local vs production parity.** M11
   shipped no new runtime dependencies.
   `CELERY_TASK_ALWAYS_EAGER=True` in
   test settings makes M11.4 + M11.5
   beat tasks execute synchronously
   in tests without a separate worker.
   Carry-forward.

6. **Honest verification reporting.**
   Every M11 endpoint carries a role-
   gate matrix test. Detector /
   surfacer tests verify state stays
   `pending` after the M11.4 surfacer
   runs (proves read-only claim);
   detector tests verify grace-period
   boundary (proves not-yet-stale
   left alone). Carry-forward.

7. **Storage-first / safer-direction
   deletion.** M11 entities all use
   CASCADE on parent FKs
   (CustomerLead / Vehicle / Cadence)
   — the child rows are subsidiary
   records that lose meaning when the
   parent disappears. **SET_NULL on
   User FKs** preserves historical
   attribution when a user is
   deleted / deactivated. Same
   posture as M10 audit-trail FKs.
   Carry-forward.

8. **Load-bearing decisions get user
   review BEFORE code.** M11's core
   pattern. **Six planning-time §5
   decisions confirmed as-recommended
   at M11.1 open**, plus **twelve
   implementation-time micro-decisions
   across four sessions** (M11.3
   handoff-CA source-format + field-
   copy shape; M11.4 template
   constants + Beat schedule + auto-
   skip; M11.5 attach shape + reason
   vocab + no-show integration; M11.6
   route family + MVP scope + test
   target + substrate addendum). Zero
   mid-implementation churn.
   Carry-forward.

9. **Distinct domain errors → distinct
   behaviors.** M11 endpoints return
   400 for unknown vocab (reasons,
   channels, templates) + malformed
   args; 404 for missing / cross-
   tenant references; 409 for state-
   machine violations
   (`WriteupNotApprovedError` /
   `WriteupAlreadyHandedOffError` /
   `DuplicateActiveCadenceError` /
   `TaskAlreadyTerminalError` /
   `BeBackAlreadyTerminalError`).
   **Five distinct 409-emitting error
   classes across M11.3-M11.5.**
   Carry-forward.

10. **Read-model properties are pure
    reads.** Preserved. M11 has no
    read-model verbs analogous to
    M10.7's `deal_jacket_summary` —
    the operator UI (M11.6) consumes
    list endpoints directly. If M12
    surfaces a bundled "customer
    journey" view, that's the shape
    to reach for.

11. **Additive extension over fork.**
    M11.1 added two columns to
    `CustomerLead` without modifying
    the M1 model shape or the M1
    chat-funnel intake path. M11.6
    extended `AdminLeadListSerializer`
    with two additive fields.
    Textbook additive extension.
    Carry-forward.

12. **Prior-increment count assertions
    use `>=` not `==`** (growth-only
    lists). Applied cleanly at every
    M11 test that touched tenant-
    carrier / permission-class /
    endpoint counts. **Contrast
    exact-set vocabs** — M11.1
    channel (5+1) + M11.4 template
    (6) + M11.5 reason (4+1) + M11.5
    state (3) all use exact-equality
    assertions because they are
    planning-locked; adding a member
    is a planning decision, not a
    code-refactor decision. **Both
    patterns coexist.** Carry-forward
    from M10 lesson 12 with M11
    evidence.

13. **Two-tier customer-visibility
    gate.** Not exercised in M11 (all
    endpoints admin-scoped).
    Preserved.

14. **Verify handoff / planning
    claims via direct inspection
    before acting.** Applied at
    M11.5 open when reviewing SALES
    §step 15 before proposing the
    reason vocab; applied at M11.6
    open when discovering that
    M11.2 + M11.5 shipped write-
    only endpoints (surfaced the
    substrate gap that became the
    §5.f.4 addendum). Carry-forward
    from M10 lesson 14 with M11
    evidence.

15. **Substrate-gap pushback is a
    productive session-open pattern.**
    Exercised at M11.5 open (§5.g
    items surfaced from an under-
    voted §1.5 planning memo) and at
    M11.6 open (§5.f.4 backend
    additions surfaced from a
    "frontend-only" framing that
    collided with substrate
    reality). **Both cases resolved
    by narrow §0.a amendments +
    proceeding**, not by re-opening
    the full planning doc.
    Carry-forward.

16. **Streak-pattern confidence.**
    **Streak stands at 35 planning-
    time as-recommended M5.1 →
    M11.1** across two milestones now.
    The signal isn't proof of
    correctness — it's that the
    planning framework works and the
    user's context has stayed aligned
    with the recommendations. Twelve
    implementation-time micro-
    decisions at M11 did not count
    against the streak per M10 §9
    (implementation-time defaults are
    always subject to the user's
    context; the count is a
    planning-time signal). Continue
    to present recommendations with
    reasoning + trade-offs; the
    trust is the goal, not the
    streak.

17. **[NEW] Read-only surfacer vs
    state-transitioning detector.**
    M11.4's beat surfacer counts +
    logs due tasks but never mutates
    state (operator intent
    required). M11.5's detector
    auto-transitions promised →
    no_show when the grace period
    elapses. **Deliberate contrast**
    — the promise is the customer's
    (objectively elapsed), task
    completion is the operator's
    (subjective judgment). Future
    Beat tasks should pick the shape
    that matches whether the trigger
    is elapsed condition (detector)
    vs operator intent (surfacer).
    Carry-forward as a project
    convention.

18. **[NEW] Fixed-vocab exact-set
    equality vs growth-only `>=`.**
    Both assertion styles coexist
    in M11 tests. Vocabs that live
    at the planning level (channel,
    template, reason, state) use
    exact-set equality because
    adding a member is a planning
    decision. Growth-only lists
    (tenant carriers, permission
    classes, endpoints) use `>=`.
    **The choice is semantic, not
    stylistic** — pick based on
    whether the list grows by
    engineering or by planning.
    Carry-forward as a project
    convention.

19. **[NEW] Atomic sibling-service
    boundary crossings.** M11.3's
    `hand_off_to_fandi` wraps a
    DealWriteup timestamp update +
    a call into the M10.1 F&I
    service (`record_credit_application`)
    in one `@transaction.atomic`.
    The idempotency guard
    (`WriteupAlreadyHandedOffError`
    409) prevents duplicate M10.1
    retention clocks. **Pattern
    generalizes** — any verb that
    spans two service packages
    should (a) wrap in
    `@transaction.atomic` for the
    same all-or-nothing atomicity
    guarantee as intra-service
    verbs, and (b) refuse re-
    execution rather than silently
    duplicating. **The refusal is
    the safer default** —
    duplicate work often has
    legal / audit consequences
    that silent success would
    hide.
