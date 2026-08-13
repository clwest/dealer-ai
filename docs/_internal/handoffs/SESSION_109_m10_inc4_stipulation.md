---
title: "SESSION_109 handoff — Milestone 10 · Increment 4 (M10.4 — Stipulation tracking)"
status: historical
type: handoff
date: 2026-08-02
session: 109
milestone: 10
milestone_status: in_progress
increment: 4
increment_status: shipped
commit: e9d311f
---

# SESSION_109 — Milestone 10 · Increment 4 (M10.4 — Stipulation tracking)

## What shipped

`Stipulation` entity as F&I substrate
for the stip-lifecycle workflow +
`services/f_and_i/stipulation.py` module
with four verbs + two new DRF endpoints
(`POST /admin/stipulations/`, `PATCH
/admin/stipulations/<pk>/`) + tenancy
carrier extension (28 → 29) + 35
focused tests. Four design questions
surfaced at session open and were
confirmed with the user (all four as-
recommended, all Option A);
`MILESTONE_10_PLANNING.md` §0.a
amended. §5.b (stipulation vocabulary)
was already resolved at SESSION_106 as
Option A.

**Load-bearing decisions confirmed at
session open (recorded in
`MILESTONE_10_PLANNING.md` §0.a):**

1. **§1.4.a — Stipulation attach
   point: Option A.** Mandatory FK to
   `LenderSubmission` (CASCADE). Stips
   are lender-specific per FINANCE
   §1.9 — every stip belongs to
   exactly one submission. Deal-level
   pre-delivery items (insurance,
   odometer) belong to M9.2
   `Delivery`'s checklist.
2. **§1.4.b — State vocabulary:
   Option A.** Fixed three-value set
   (`open` default / `cleared` /
   `waived`). Matches FINANCE §1.9.
   "Stip creep" manifests as new stip
   rows opened after previous ones
   cleared, not as a state
   transition.
3. **§1.4.c — `documented_by`:
   Option A.** FK to
   `settings.AUTH_USER_MODEL`
   nullable, `SET_NULL` on user
   delete. Audit-trail rigor — the
   F&I manager who cleared the stip
   is traceable. `SET_NULL`
   preserves historical rows when a
   user leaves.
4. **§1.4.d — Photo / document
   evidence capture: Option A.**
   Deferred to M10.7 compliance
   layer. M10.4 ships state
   tracking only; operators use the
   free-text `notes` field for
   evidence attribution until
   structured storage lands.

**M10.4 deliverables (five):**

1. **New `Stipulation` model +
   migration `0028`.** Mandatory FK
   to `LenderSubmission` CASCADE +
   FK to `settings.AUTH_USER_MODEL`
   nullable SET_NULL (`documented_by`).
   Fields: `stip_type` from
   `STIPULATION_TYPE_CHOICES` (fixed
   5-value set per §5.b Option A —
   `proof_of_income` /
   `proof_of_insurance` /
   `proof_of_residence` /
   `references` / `other`), `state`
   from `STIPULATION_STATE_CHOICES`
   (fixed 3-value set per §1.4.b
   Option A — `open` default /
   `cleared` / `waived`),
   `cleared_at` DateTime nullable
   (auto-populated by service on
   state transition to
   cleared/waived; reset to NULL on
   transition back to open),
   `notes` TextField blank.
   Ordering `(-created_at,)`.
   Model-layer `clean()` cross-
   tenant guard on
   `lender_submission` FK.
2. **Tenancy-carrier extension
   28 → 29.**
3. **New `services/f_and_i/stipulation.py`**
   module — four verbs:
   - `record_stipulation(...)` —
     transactional. Refuses cross-
     tenant submission
     (`CrossTenantStipulationError`)
     and unknown stip_type
     (`ValueError`). Initial state
     is always `open` — clearing /
     waiving is a distinct event
     captured by
     `update_stipulation_state`.
   - `update_stipulation_state(stip,
     new_state=..., documented_by=...,
     notes=...)` — partial update
     via targeted
     `.save(update_fields=...)`.
     Auto-populates `cleared_at` on
     first transition to
     `cleared`/`waived`; preserves
     the original `cleared_at` on
     subsequent transitions between
     cleared and waived (first-
     clear moment stays as
     historical anchor); resets
     `cleared_at` to NULL on
     transition back to `open`
     (operator error correction
     path). Any-to-any transition
     allowed at M10.4.
   - `get_stipulation(pk,
     dealership)` — pure read,
     tenant-scoped. Returns None
     for unknown / cross-tenant
     pk. Never raises, never
     leaks.
   - `list_stipulations_for_submission(submission)`
     — pure read. FK filter with
     ordering inheriting from
     Meta.
4. **`services/f_and_i/__init__.py`
   facade** — extended to re-export
   the four new M10.4 verbs +
   `CrossTenantStipulationError`
   alongside M10.1 / M10.2 / M10.3
   exports.
5. **Two new endpoints** — both
   role-gated on the same
   `_M101_PERMS` composition:
   - `POST /api/dealer-ai/admin/stipulations/`
     (name:
     `admin-stipulation-create`).
     Cross-tenant submission → 404;
     unknown stip_type → 400.
   - `PATCH /api/dealer-ai/admin/stipulations/<int:pk>/`
     (name:
     `admin-stipulation-update`).
     Unknown state → 400; unknown /
     cross-tenant pk → 404.
     `documented_by` populated
     server-side from
     `request.user` — the endpoint
     doesn't accept it in the
     request body. This mirrors
     M4's audit-trail pattern and
     removes a class of "wrong
     user" bugs.

**35 focused tests across three files:**

- **`test_m104_stipulation_model.py`
  (11 tests)** — field defaults,
  all five stip_type values
  accepted, `__str__`; cross-tenant
  clean guards; CASCADE from
  lender_submission +
  SET_NULL from user delete
  (row survives, documented_by
  nulled); tenant-carrier registry.
- **`test_m104_stipulation_service.py`
  (16 tests)** — `record_stipulation`
  (creates in `open` state /
  persists notes / cross-tenant
  raises / unknown stip_type raises);
  `update_stipulation_state`
  (open→cleared populates
  cleared_at + documented_by /
  open→waived populates cleared_at
  / cleared→open resets cleared_at
  to NULL / cleared→waived
  preserves original cleared_at /
  notes partial update / notes
  preserved when omitted / unknown
  state raises / any-to-any
  allowed); `get_stipulation`
  (tenant hit / cross-tenant None
  / unknown None);
  `list_stipulations_for_submission`.
- **`test_m104_stipulation_endpoint.py`
  (8 tests)** — `POST` (dealer_owner
  201 / f_and_i_manager 201 with
  projected row / cross-tenant
  submission 404 / invalid
  stip_type 400 / missing
  submission_id 400); `PATCH`
  (state→cleared populates
  cleared_at + documented_by from
  request.user / state→waived
  populates cleared_at / notes
  partial update persists /
  unknown state 400 / unknown pk
  404 / cross-tenant pk 404).

**Test baseline:** `3,586 → 3,621
pass, 1 skipped, 0 fail`. (Planning
§7 M10.4 projected ~20 tests;
shipped 35 — same overshoot pattern
as M10.1-M10.3, covering the state-
transition matrix completely
including cleared_at reset
semantics.)

## Explicit non-goals for M10.4 (deferred to M10.5+)

- ❌ `Contract` + `FundingPacket` +
  `FundingStatus` entities (M10.5).
- ❌ `Chargeback` + `net_realized`
  verb (M10.6).
- ❌ `ComplianceRecord` entity +
  `/dealer-ai-f-and-i/` operator UI
  (M10.7).
- ❌ Photo / document file storage
  plumbing (M10.7 per §1.4.d
  Option A).
- ❌ State-transition constraints
  (M10.7 if evidence surfaces).
- ❌ Frontend UI (M10.7).

## Reality check

- **Backend baseline:** `3,621 pass,
  1 skipped, 0 fail` (was `3,586`
  at SESSION_108 close).
- **Migrations:** `0001`–`0028`
  (added `0028_stipulation_entity`
  — one CreateModel operation).
- **Tenancy carriers:** 28 → 29
  (added `Stipulation`).
- **DRF admin surface:** 52 → 54
  (added POST + PATCH
  stipulation endpoints).
- **Frontend baseline:** unchanged
  (34 pass); no frontend at M10.4.
- **`git status`:** clean pending
  the M10.4 commit.
- **Django check:** clean (0
  issues).
- **`makemigrations --check
  --dry-run`:** "No changes
  detected."

## What SESSION_110 (M10.5) opens with

Per `MILESTONE_10_PLANNING.md` §7
M10.5: **Contract + FundingPacket +
FundingStatus entities.** This is
the largest single M10 increment
sketch — three entities in one
session. Several design questions
likely to surface:

Recommended step sequence for SESSION_110:

1. Push-authorization check for the
   M10.1-M10.4 commits (four
   pending push per M9-close
   convention).
2. Confirm M10.5 §5-equivalent
   decisions:
   - Contract entity split — one
     `Contract` model or separate
     `Contract` (RISC) +
     `BackEndProductAgreement`
     (per-product agreement)?
   - FundingPacket vs FundingStatus
     — one entity or two? What's
     the actual difference?
   - Contract state machine —
     `unsigned` → `signed` → …?
   - Contract attach point —
     DealStructure (the version
     that was signed) or
     LenderSubmission (the
     approved terms that were
     contracted)?
   - Product-agreement vocabulary
     (VSC / GAP / etc.) —
     structured now or free-form
     like M10.2's `back_end_products`?
3. Read first:
   - `MILESTONE_10_PLANNING.md`
     §1.5 + §1.6 + §7 M10.5.
   - `docs/handoffs/SESSION_109_m10_inc4_stipulation.md`
     (this file).
   - `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
     §5 (contract), §6 (funding),
     §4.3-§4.5 (back-end products).
   - `backend/dealer_ai/models.py::DealStructure`
     (M10.2 substrate — likely
     Contract attach target).
   - `backend/dealer_ai/services/f_and_i/stipulation.py`
     (pattern to mirror for
     `contract.py`, `funding.py`).
4. Verify starting state:
   `python3 manage.py test
   dealer_ai` → `3,621 pass, 1
   skipped, 0 fail`.
5. Draft: three new models +
   migration `0029`, tenancy
   carrier extensions 29 → 32,
   `services/f_and_i/contract.py`
   + `services/f_and_i/funding.py`,
   endpoints, ~25 focused tests.
6. Full-suite verification. Target
   3,621 → ~3,646.
7. Ship handoff
   `docs/handoffs/SESSION_110_m10_inc5_contract_funding.md`.
8. Overwrite
   `00-START-NEXT-SESSION.md` with
   M10.6 priority.

## Commit

Local only. Push to `origin/main`
deferred per M9-close convention.
Message:

```
Milestone 10 · Increment 4 — Stipulation tracking (SESSION_109)

M10.4 ships the stipulation-lifecycle substrate for the F&I
workflow:

- New Stipulation model + migration 0028. Mandatory FK to
  LenderSubmission (CASCADE) + FK to AUTH_USER_MODEL
  (nullable SET_NULL as documented_by). Fixed 5-value
  stip_type vocabulary per §5.b Option A (proof_of_income /
  proof_of_insurance / proof_of_residence / references /
  other). Fixed 3-value state vocabulary (open default /
  cleared / waived). cleared_at auto-populated by service on
  first cleared/waived transition; reset to NULL on
  transition back to open.
- Tenancy carrier extension 28 → 29.
- New services/f_and_i/stipulation.py — four verbs.
  record_stipulation (transactional, creates in open state,
  cross-tenant guard) + update_stipulation_state (partial
  update via update_fields, cleared_at auto-populate/reset,
  any-to-any transition) + get_stipulation (tenant-scoped
  read) + list_stipulations_for_submission (FK filter).
- Two new endpoints — both reuse M10.1's
  IsFinanceManagerOrOwnerAtActiveDealership. POST
  /admin/stipulations/ + PATCH /admin/stipulations/<pk>/.
  PATCH sources documented_by from request.user server-side
  (endpoint doesn't accept it in the body — removes a class
  of "wrong user" bugs).
- 35 focused tests. Baseline 3,586 → 3,621 pass.

Four §1.4 decisions resolved at session open (all as-
recommended): §1.4.a Option A (mandatory FK to
LenderSubmission), §1.4.b Option A (fixed 3-value state),
§1.4.c Option A (documented_by as User FK SET_NULL),
§1.4.d Option A (defer photo/document evidence to M10.7).
```

## Deferred / observations for M10.5+

- `services/f_and_i/` now has four
  submodules
  (`credit_application.py`,
  `deal_structure.py`, `lender.py`,
  `stipulation.py`). M10.5-M10.7
  will add `contract.py`,
  `funding.py`, `chargeback.py`,
  `compliance.py`.
- The `cleared_at` auto-populate /
  reset pattern in
  `update_stipulation_state` is a
  useful shape for M10.5 Contract
  (`signed_at`) and M10.5
  FundingStatus (`funded_at`).
  Same "first transition to
  terminal state populates
  timestamp; back-transition
  resets" semantics.
- The `documented_by=request.user`
  endpoint pattern (server-side
  sourced FK, not client-provided)
  is the right shape for any
  future audit-trail FKs
  (contract signer, funding
  approver, chargeback recorder).
  Should be reused verbatim.
- Nothing in M10.4 required
  amending M1-M9 or M10.1-M10.3
  behavior. Consumption is
  FK-only.
