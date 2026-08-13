---
title: "SESSION_116 handoff — Milestone 11 · Increment 3 (M11.3 — DealWriteup entity + F&I handoff)"
status: historical
type: handoff
date: 2026-08-02
session: 116
milestone: 11
milestone_status: in_progress
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_116 — Milestone 11 · Increment 3 (M11.3 — DealWriteup entity + F&I handoff action)

## What shipped

New `DealWriteup` entity capturing
the four-square deal write-up per
SALES §step 10, plus the F&I
handoff action per §5.e Option A
that server-side auto-creates a
matching M10.1 CreditApplication.
One new model, one migration
(`0034`), one tenancy carrier
extension (35 → 36), one new
`services/deal_writeups/` package
with three write verbs
(`record_deal_writeup`,
`approve_deal_writeup`,
`hand_off_to_fandi`), one new
`views_deal_writeups.py` module
with three DRF endpoints, three
URL routes, and **33 focused
tests** (target ~25).

The §5.e handoff-flow decision
(Option A — auto-CA-creation on
handoff) was already confirmed at
SESSION_114 open and recorded in
`MILESTONE_11_PLANNING.md` §0.a;
no new §5 planning decisions
surfaced.

**Two implementation-time micro-
decisions surfaced at M11.3 open**
(recorded in `MILESTONE_11_PLANNING.md`
§0.a per M5-M10 amendment
convention — planning-time
decisions only count against the
recommend-and-approve streak,
implementation-time defaults do
not):

1. **Auto-created CA
   `source_format` on handoff:
   default `CREDIT_APP_FORMAT_TABLET`**
   (in-store manager tablet is the
   operator reality). Overridable
   via the verb kwarg or via the
   endpoint request body.
2. **DealWriteup → CA field-copy
   shape:** `applicant_full_name`
   ← `lead.name`; `notes` ←
   structured summary of the
   four-square terms
   (vehicle_price /
   monthly_payment_target /
   term_months_target / apr_target
   + free-text notes). No
   `applicant_ssn_last4` (not
   captured on writeup — F&I
   fills from the customer's
   credit-app paperwork).

Neither micro-decision closes any
future option — a subsequent
planning pass can change either
without a migration. Streak
stands at **35 as-recommended
M5.1 → M11.1** (planning-time
only).

## Deliverables

### 1. Model — `dealer_ai/models.py` (appended)

- New `DealWriteup` model.
  - `dealership` FK CASCADE.
  - `lead` FK to `CustomerLead`
    CASCADE (mandatory).
  - `vehicle` FK to `Vehicle`
    CASCADE (mandatory).
  - Four-square DecimalFields
    (`vehicle_price`,
    `trade_allowance`,
    `down_payment`,
    `monthly_payment_target`,
    `apr_target`) — all nullable
    (writeup can be in-progress
    with cells empty).
  - `term_months_target`
    PositiveIntegerField
    (nullable).
  - `write_up_at` DateTimeField.
  - `written_up_by_user` FK to
    User SET_NULL.
  - `sales_manager_approved_at`
    + `sales_manager_approved_by_user`
    (both nullable — unapproved
    writeups are legit drafts).
  - `handed_off_to_fandi_at`
    nullable (not FK to CA — CA
    is a peer row, retention-
    clock record of record).
  - `notes` TextField.
  - Cross-tenant `clean()` guard
    on both `lead` + `vehicle`.
  - Meta ordering
    `["-write_up_at"]`.

### 2. Migration — `dealer_ai/migrations/0034_m113_deal_writeup_entity.py`

- Single `CreateModel` for
  DealWriteup.
- Docstring cites §1.3 + §5.e +
  carrier extension (35 → 36).

### 3. Tenancy carrier extension — `dealer_ai/services/tenancy.py`

- `"DealWriteup"` added to
  `_TENANT_CARRIER_MODEL_NAMES`
  (35 → 36).

### 4. Service package — `dealer_ai/services/deal_writeups/`

- `__init__.py` — re-exports the
  three verbs + three domain
  errors.
- `deal_writeup.py`:
  - `record_deal_writeup(...)`
    — mandatory both FKs, cross-
    tenant guards.
  - `approve_deal_writeup(...)`
    — sets timestamp + user,
    idempotent (re-approval
    overwrites).
  - `hand_off_to_fandi(...)` —
    `@transaction.atomic` wraps
    (a) timestamp update + (b)
    CA auto-creation via
    `services.f_and_i.record_credit_application`.
    Refuses unapproved
    (`WriteupNotApprovedError`)
    + refuses re-handoff
    (`WriteupAlreadyHandedOffError`,
    idempotency guard against
    duplicate M10.1 CA rows
    with active retention
    clocks).
- Three domain errors:
  `CrossTenantDealWriteupError`,
  `WriteupNotApprovedError`,
  `WriteupAlreadyHandedOffError`.

### 5. View module — `dealer_ai/views_deal_writeups.py`

- Three endpoints:
  - `admin_deal_writeup_create`
    (POST /admin/deal-writeups/)
  - `admin_deal_writeup_approve`
    (POST /admin/deal-writeups/:pk/approve/)
  - `admin_deal_writeup_hand_off`
    (POST /admin/deal-writeups/:pk/hand-off/)
- All three gated on
  `IsAuthenticated &
  IsSalesManagerOrOwnerAtActiveDealership`
  (M4 permission class reused).
- Domain-error mapping:
  cross-tenant → 404,
  not-approved → 409,
  already-handed-off → 409,
  serializer → 400.
- Handoff endpoint response
  carries both `deal_writeup` +
  `credit_application` for the
  operator UI.

### 6. URL routes — `dealer_ai/urls.py`

Three new patterns under
`admin/deal-writeups/`.

### 7. Tests — three new files, 33 focused tests

- `test_m113_deal_writeup_model.py`
  (8 tests) — defaults, ordering,
  cross-tenant `clean()` for
  lead + vehicle, CASCADE on
  lead + vehicle delete,
  SET_NULL on writer + approver
  delete.
- `test_m113_deal_writeup_service.py`
  (11 tests) — record verb
  (4: happy, minimal, cross-
  tenant × 2), approve verb
  (2: sets timestamps,
  re-approval overwrites),
  handoff verb (5: creates CA,
  notes contain terms, refuses
  unapproved, refuses re-
  handoff, source_format
  override).
- `test_m113_deal_writeup_endpoint.py`
  (14 tests) — create auth
  (4: unauth, no membership,
  advisor, f_and_i_manager),
  create happy (2:
  sales_manager + response
  shape, dealer_owner), create
  errors (3: missing lead_id,
  cross-tenant × 2), approve
  (2: happy, nonexistent 404),
  handoff (3: pre-approval
  409, happy path 201 with CA,
  re-handoff 409).

## Compatibility

- Backend baseline: **3,781 →
  3,814** (+33, target ~25).
  Zero regressions.
- Frontend baseline: **51**
  (unchanged; M11.3 is backend-
  only per §7 non-goal).
- Migrations `0001`–`0034`.
- Tenancy carriers **36** (35 →
  36 for DealWriteup).
- Permission classes **8**
  (unchanged).
- DRF admin surface: **69 → 72**
  (+3 M11.3 endpoints).
- Frontend operator routes: **11**
  (unchanged).
- No M1-M11.2 model / service
  changes.

## Governance / posture notes

- **Handoff atomicity.** The
  `hand_off_to_fandi` verb wraps
  the timestamp update + CA
  creation in a single
  `@transaction.atomic` — a mid-
  handoff failure never leaves
  the writeup marked handed-off
  without a matching CA row.
- **Idempotency at the service
  layer.** Re-handoff is refused
  with a distinct exception, not
  a silent no-op. The refusal is
  a hard 409, matching M10.5
  ContractAlreadyVoidedError +
  M10.5 FundingAlreadyExistsError
  posture. Silent-idempotent
  handoff would let a UI double-
  click create two CAs, each
  starting its own retention
  clock (M10.1 §5.e legal
  concern).
- **CA is peer, not child.** The
  auto-created CA is not FK-
  linked from the writeup — it
  is linked via the shared
  `lead` FK. Rationale: the CA
  outlives the writeup per M10.1
  retention lock; a cascading FK
  would let a writeup delete
  short-circuit the retention
  clock.
- **No M10.2 DealStructure at
  handoff.** The M11 plan
  scopes the handoff to CA
  creation only. The F&I
  manager creates the
  DealStructure separately after
  reviewing the auto-created CA.
- **Reuse over invention** —
  M4's
  `IsSalesManagerOrOwnerAtActiveDealership`
  reused unchanged. No new
  permission class. Same as
  M11.1 / M11.2.
- **Test posture** — 33 focused
  tests, all against real DB
  round-trips (no mocks). The
  handoff integration test
  proves the CA is persisted
  and lead-linked, not just
  that the verb returned.

## Non-goals honored

- ❌ No cadence orchestration
  (M11.4).
- ❌ No be-back (M11.5).
- ❌ No frontend at M11.3
  (§5.f Option C — MVP
  substrate; extended UI at
  M11.6).
- ❌ No modification of M1-M11.2
  business logic.
- ❌ No modification of the
  M10.1 CreditApplication model
  shape — the handoff calls the
  existing service verb
  unchanged.
- ❌ No auto-DealStructure
  creation at handoff (deferred
  — CA only).
- ❌ No modifications to M10.1
  retention-clock enforcement.
- ❌ No PATCH endpoint for
  editing a writeup post-
  approval (deferred; MVP is
  create + approve + handoff
  only).

## What's next

**SESSION_117 opens M11.4 —
FollowUpCadence + FollowUpTask
+ Celery-beat scheduling** per
§7 M11.4. Model shape confirmed
at M11.1 open (§5.d Option A —
two-entity model with queryable
task rows).

**Backend baseline at
SESSION_117 open: 3,814 pass.**
Frontend baseline unchanged.

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 11
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_11_PLANNING.md`
   (§0.a M11.1 amendment carrying
   §5.e + SESSION_116 §0.a M11.3
   micro-decisions)
6. `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_115_m11_inc2_test_drive.md`
   (previous session)
8. `docs/handoffs/SESSION_114_m11_inc1_channel_intake.md`
9. `docs/CAPABILITY_MATRIX.md` §7k
10. `docs/research/SALES_DEPARTMENT_MAPPING.md`
    §workflow steps 10 + 11
11. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
    §1.1 (CreditApplication intake)
