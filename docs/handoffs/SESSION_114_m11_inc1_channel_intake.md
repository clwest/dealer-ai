---
title: "SESSION_114 handoff — Milestone 11 · Increment 1 (M11.1 — Channel intake + CustomerLead extension)"
status: historical
type: handoff
date: 2026-08-02
session: 114
milestone: 11
milestone_status: in_progress
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_114 — Milestone 11 · Increment 1 (M11.1 — Channel intake + CustomerLead extension)

## What shipped

Additive extension to `CustomerLead`
opening the sales-side non-chat
intake surface. Two new columns
(`channel`, `referrer`), one data
migration (default-backed backfill),
one new `services/leads/` package
with four write verbs, one new
`services/leads/webhook_adapters/`
package with a documented generic
adapter + registry, one new
`views_leads.py` module with four
DRF endpoints, four URL routes, and
28 focused tests (targeting
`~25` per the planning skeleton).

**Six §5 planning decisions confirmed
at session open (recorded in
`MILESTONE_11_PLANNING.md` §0.a) —
all as-recommended (M10 streak → 35
consecutive as-recommended
resolutions M5.1 → M11.1 open):**

1. **§5.a — `CustomerLead.channel`
   field + vocabulary: Option A.**
   Additive CharField with fixed
   5+1 vocab
   (`chat`/`walk_in`/`phone`/`listing_form`/`referral`/`other`),
   data migration backfills every
   historical row to `chat` (all
   pre-M11 rows originated in the
   M1 chat funnel).
2. **§5.b — Listing-platform
   webhook shape: Option A.** One
   generic
   `POST /admin/leads/webhook/`
   endpoint + per-platform adapter
   modules under
   `services/leads/webhook_adapters/`.
   First adapter shipped: `generic`
   (documented dealer-owned
   envelope). Named-platform
   adapters (Autotrader / Cars.com
   / Facebook Marketplace / etc.)
   ship as sibling modules when
   operator evidence surfaces the
   platform-specific field shapes.
3. **§5.c — TestDrive attach
   shape: Option A.** Mandatory FK
   to both `CustomerLead` +
   `Vehicle`. Recorded for M11.2
   model-shape stability.
4. **§5.d — FollowUpCadence +
   Task shape: Option A.** Two
   entities; task rows queryable.
   Recorded for M11.4.
5. **§5.e — DealWriteup →
   CreditApplication flow:
   Option A.** Handoff auto-
   creates CA server-side.
   Recorded for M11.3.
6. **§5.f — Operator UI scope:
   Option C.** MVP substrate at
   M11.1 (no frontend). Extended
   UI in a follow-on increment.
   Matches M10.7 §1.8.d precedent.

## Deliverables

### 1. Model — `dealer_ai/models.py`

- New module-level constants
  `LEAD_CHANNEL_CHAT` /
  `LEAD_CHANNEL_WALK_IN` /
  `LEAD_CHANNEL_PHONE` /
  `LEAD_CHANNEL_LISTING_FORM` /
  `LEAD_CHANNEL_REFERRAL` /
  `LEAD_CHANNEL_OTHER` +
  `LEAD_CHANNEL_CHOICES` tuple.
- `CustomerLead.channel` CharField
  (max 32, choices=vocab,
  default=`chat`).
- `CustomerLead.referrer` self-FK
  (SET_NULL, nullable), reverse
  accessor `referred_leads`.
- Docstring cites §1.1 + §1.6 +
  §5.a + §5.b + §5.f.

### 2. Migration — `dealer_ai/migrations/0032_m111_lead_channel_and_referrer.py`

- Two `AddField` operations
  (channel + referrer).
- `channel`'s AddField carries
  `default="chat"` — Django
  backfills every existing row
  atomically as part of the same
  operation. No separate
  `RunPython` op required (the
  field-level default IS the
  backfill; docstring at the top
  of the migration documents
  this).

### 3. Service package — `dealer_ai/services/leads/`

- `__init__.py` — re-exports the
  four write verbs + two domain
  errors.
- `channel_intake.py`:
  - `record_walk_in_lead(...)`
  - `record_phone_lead(...)`
  - `record_referral_lead(...)`
    (with optional
    `referrer_lead_id` +
    cross-tenant guard →
    `CrossTenantReferrerError`).
  - `record_webhook_lead(...)`
    (dispatches to adapter registry
    → `UnknownWebhookPlatformError`
    for unregistered platforms).
- `webhook_adapters/__init__.py`
  — registry + `get_adapter()` +
  `registered_platforms()`.
- `webhook_adapters/generic.py`
  — first adapter. Documents the
  dealer-owned envelope
  (`full_name` required; `phone`,
  `email`, `message`,
  `target_monthly_payment`,
  `down_payment`, `trade_in`,
  `credit_range` optional). Not
  a fabricated proprietary shape.

### 4. View module — `dealer_ai/views_leads.py`

- Four `@api_view(["POST"])`
  functions, all gated on
  `IsAuthenticated &
  IsSalesManagerOrOwnerAtActiveDealership`
  (M4 permission class reused
  unchanged per §1.9).
- Shared `_BaseIntakeSerializer`
  for walk-in / phone / referral;
  `ReferralLeadRequestSerializer`
  adds optional `referrer_lead_id`;
  `WebhookLeadRequestSerializer`
  takes `platform` + `payload`.
- Domain-error → HTTP mapping:
  `UnknownWebhookPlatformError` →
  400 (with
  `registered_platforms` in
  body); `CrossTenantReferrerError`
  → 404 (fail-closed); serializer
  error → 400.
- `_project_lead()` response
  shape:
  `{id, name, phone, email,
  channel, referrer_id,
  dealership_id, created_at}`.

### 5. URL routes — `dealer_ai/urls.py`

Four new patterns:

- `admin/leads/walk-in/` →
  `admin-lead-walk-in-create`
- `admin/leads/phone/` →
  `admin-lead-phone-create`
- `admin/leads/referral/` →
  `admin-lead-referral-create`
- `admin/leads/webhook/` →
  `admin-lead-webhook-create`

The existing `admin/leads/` GET
list endpoint (line 33) and the
`/leads/` M1 chat-funnel create
endpoint (line 26) are unchanged.

### 6. Tests — three new files, 28 focused tests

- `test_m111_channel_intake_model.py`
  (6 tests) — channel default,
  vocab exact-set assertion,
  referrer FK nullable / link /
  SET_NULL / reverse accessor.
- `test_m111_channel_intake_service.py`
  (11 tests) — walk-in / phone /
  referral (4 cases including
  cross-tenant + nonexistent) /
  webhook (2 cases) / generic
  adapter unit tests (2).
- `test_m111_channel_intake_endpoint.py`
  (11 tests) — auth gates (4:
  unauth on every endpoint + no-
  membership + advisor +
  f_and_i_manager) / happy paths
  (4: walk-in, phone under owner,
  referral with valid ref,
  webhook with generic) / error
  mapping (3: cross-tenant
  referrer, unknown platform,
  missing name).

## Compatibility

- Backend baseline: **3,730 →
  3,758** (+28, target ~25).
  Zero regressions.
- Frontend baseline: **51**
  (unchanged; M11.1 is backend-
  only per §7 non-goal).
- Migrations `0001`–`0032`.
- Tenancy carriers **34**
  (unchanged; `CustomerLead` was
  already a carrier).
- Permission classes **8**
  (unchanged; reused
  `IsSalesManagerOrOwnerAtActiveDealership`
  from M4).
- DRF admin surface: **64 → 68**
  (+4 M11.1 endpoints).
- Frontend operator routes: **11**
  (unchanged).
- No new module-path renames,
  no M1-M10 model/service
  changes.

## Governance / posture notes

- **Additive-extension pattern
  (M8 §6 lesson 11)** applied
  cleanly: two new columns on an
  existing model with a
  data-migration-safe default,
  no NULL-vs-not-NULL flipping.
- **Fail-closed cross-tenant
  reads** for the referrer FK
  match the M2.6 / M3.6 / M4.6 /
  M9.1 / M10.1 convention (404
  not 403).
- **Reuse over invention** —
  `IsSalesManagerOrOwnerAtActiveDealership`
  reused unchanged (M4). No new
  permission class.
- **Test posture** —
  `LEAD_CHANNEL_CHOICES` uses
  exact-set equality (not `>=`)
  because the 5+1 vocab is a
  planning decision, not a
  growth-only list (M10 §6
  lesson 12 applies to
  growth-only lists; explicit
  vocabs are the exception).
- **First webhook adapter is
  `generic`, not `autotrader`**
  — no operator evidence exists
  for an invented dealer (Copper
  Canyon), and fabricating a
  proprietary envelope shape
  would violate research-before-
  design (rule 3). The generic
  envelope is a documented
  dealer-owned contract that
  platform-specific adapters
  will map into.

## Non-goals honored

- ❌ No `TestDrive` (M11.2).
- ❌ No `DealWriteup` (M11.3).
- ❌ No cadence orchestration
  (M11.4).
- ❌ No be-back (M11.5).
- ❌ No frontend at M11.1 (§5.f
  Option C — MVP substrate;
  extended UI at M11.6).
- ❌ No modification of M1-M10
  business logic.
- ❌ No listing-platform
  outbound syndication.
- ❌ No HMAC signature
  verification on the webhook
  endpoint (deferred to a
  hardening increment when a
  specific third-party
  integration lands; current
  webhook is admin-gated for the
  operator "paste-JSON" flow).

## What's next

**SESSION_115 opens M11.2 —
TestDrive entity + service +
endpoint** per §7 M11.2. Model
shape confirmed at M11.1 open
(§5.c Option A — mandatory FK to
both `CustomerLead` + `Vehicle`).

**Backend baseline at
SESSION_115 open: 3,758 pass.**
Frontend baseline unchanged
(no frontend at M11.2 either).

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 11
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_11_PLANNING.md`
   (§0.a M11.1 amendment)
6. `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
   §6 (nineteen lessons carry
   into M11)
7. `docs/handoffs/SESSION_113_m10_close.md`
   (previous session)
8. `docs/research/SALES_DEPARTMENT_MAPPING.md`
9. `docs/CAPABILITY_MATRIX.md` §7k
