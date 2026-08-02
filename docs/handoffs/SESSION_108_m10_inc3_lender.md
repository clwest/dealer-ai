---
title: "SESSION_108 handoff — Milestone 10 · Increment 3 (M10.3 — LenderProgram + LenderSubmission entities)"
status: historical
type: handoff
date: 2026-08-02
session: 108
milestone: 10
milestone_status: in_progress
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_108 — Milestone 10 · Increment 3 (M10.3 — LenderProgram + LenderSubmission entities)

## What shipped

`LenderProgram` + `LenderSubmission`
entities as F&I substrate for the
lender-submission workflow +
`services/f_and_i/lender.py` module with
six catalog + submission verbs + three
new DRF endpoints (`POST /admin/lender-programs/`,
`POST /admin/lender-submissions/`,
`PATCH /admin/lender-submissions/<pk>/`)
+ tenancy carrier extensions (26 → 28)
+ 53 focused tests. Four design
questions surfaced at session open and
were confirmed with the user (all four
as-recommended); `MILESTONE_10_PLANNING.md`
§0.a amended.

**Load-bearing decisions confirmed at
session open (recorded in
`MILESTONE_10_PLANNING.md` §0.a):**

1. **§1.3.a — LenderSubmission attach
   point: Option A.** Mandatory FK to
   `DealStructure` (CASCADE). Every
   submission is *of* a deal structure
   to a lender per FINANCE §workflow
   step 8-10. Pre-DealStructure
   pre-qualification defers to a
   distinct entity if it ever surfaces.
2. **§1.3.b — LenderSubmission.status
   vocabulary: Option A.** Fixed set
   of four values (`pending` /
   `approved` / `counter` /
   `declined`). Mirrors M10.1 §5.b
   + M9.1 §5.c fixed-vocabulary
   precedents.
3. **§1.3.c — LenderProgram catalog
   scope: Option A.** Per-dealership
   catalog with FK to `Dealership`.
   Matches §5.d Option C from
   SESSION_106 (catalog is additive
   alongside free-text notes).
   Unique constraint on
   `(dealership, name)`.
4. **§1.3.d — counter_terms /
   approval_terms JSONField shape:
   Option A.** Free-form JSON
   (mirrors M10.2 `back_end_products`).
   Vocabulary partitioning deferred
   to M10.7 compliance layer.

**M10.3 deliverables (six):**

1. **New `LenderProgram` model +
   migration `0027`.** FK to
   `Dealership` CASCADE. Fields:
   `name` CharField(255), `contact`
   CharField(255) blank,
   `terms_summary` TextField blank,
   `is_active` BooleanField
   default=True. Ordering `(name,)`.
   Unique constraint on
   `(dealership, name)` — no
   duplicate program names per
   tenant (across tenants OK).
2. **New `LenderSubmission` model.**
   FK to `DealStructure` CASCADE
   (mandatory) + FK to
   `LenderProgram` **PROTECT** (a
   program with submissions cannot
   be hard-deleted; operators
   deactivate via `is_active`
   instead). Fields: `submitted_at`
   DateTime, `status` from
   `LENDER_SUBMISSION_STATUS_CHOICES`
   default `pending`, `counter_terms`
   + `approval_terms` JSONField
   default=dict, `notes` TextField
   blank. Ordering `(-submitted_at,
   -created_at)`. Model-layer
   `clean()` cross-tenant guards on
   both parent FKs.
3. **Tenancy-carrier extensions
   26 → 28.** Both `LenderProgram`
   and `LenderSubmission` added.
4. **New `services/f_and_i/lender.py`
   module** — six verbs:
   - `record_lender_program(...)` —
     transactional. Refuses
     duplicate `(dealership, name)`
     via typed
     `DuplicateLenderProgramError`
     (maps to 409 at endpoint
     layer).
   - `list_active_lender_programs(dealership)`
     — pure read. Filters
     `is_active=True`, ordering
     inherits from Meta.
   - `record_lender_submission(...)`
     — transactional. Refuses
     cross-tenant deal / program
     (`CrossTenantLenderSubmissionError`)
     and unknown status
     (`ValueError`). Both terms
     default to empty dict.
   - `update_lender_submission_status(submission,
     new_status=..., counter_terms=...,
     approval_terms=..., notes=...)`
     — partial update via targeted
     `.save(update_fields=...)`.
     Any-to-any transition allowed
     at M10.3 (operator behavior
     captured as-recorded);
     transitions may be locked at
     M10.4+ if evidence surfaces.
   - `get_lender_submission(pk,
     dealership)` — pure read,
     tenant-scoped. Returns None
     for unknown / cross-tenant pk.
   - `list_submissions_for_deal_structure(deal)`
     — pure read. Ordered
     queryset.
5. **Three new endpoints.** All
   role-gated on the M10.1
   `_M101_PERMS` composition
   (`IsAuthenticated &
   IsFinanceManagerOrOwnerAtActiveDealership`):
   - `POST /api/dealer-ai/admin/lender-programs/`
     (name: `admin-lender-program-create`).
     Domain-error mapping:
     `DuplicateLenderProgramError`
     → 409 Conflict.
   - `POST /api/dealer-ai/admin/lender-submissions/`
     (name: `admin-lender-submission-create`).
     Cross-tenant deal / program → 404
     (never leak);
     `ValueError` → 400.
   - `PATCH /api/dealer-ai/admin/lender-submissions/<int:pk>/`
     (name: `admin-lender-submission-update`).
     Status change + optional
     terms / notes. Unknown status
     → 400; unknown / cross-tenant
     pk → 404.
6. **`services/f_and_i/__init__.py`
   facade** — extended to re-export
   the six new M10.3 verbs +
   `CrossTenantLenderSubmissionError`
   + `DuplicateLenderProgramError`
   alongside M10.1 / M10.2 exports.

**53 focused tests across three files:**

- **`test_m103_lender_model.py` (17
  tests)** — LenderProgram field
  defaults, unique constraint per
  tenant, cross-tenant same-name
  allowed, `__str__`, ordering;
  LenderSubmission field defaults,
  all four status values, terms
  default empty dict, ordering
  desc; cross-tenant clean guards
  on both parents; CASCADE on
  deal-structure delete + PROTECT
  on program delete (with and
  without submissions); tenancy
  carrier registry membership.
- **`test_m103_lender_service.py`
  (19 tests)** —
  `record_lender_program` (happy /
  full-fields / duplicate-name
  rejection / cross-tenant same-
  name allowed);
  `list_active_lender_programs`
  (filter / empty-tenant case);
  `record_lender_submission`
  (defaults / explicit / cross-
  tenant deal / cross-tenant
  program / unknown status);
  `update_lender_submission_status`
  (all three canonical transitions
  from pending / any-to-any
  allowed / unknown status);
  `get_lender_submission` (tenant
  hit / unknown None /
  cross-tenant None);
  `list_submissions_for_deal_structure`
  (all submissions for a deal).
- **`test_m103_lender_endpoint.py`
  (17 tests)** — `POST
  /admin/lender-programs/` (owner
  can create / all-fields persist
  / duplicate 409 / missing-name
  400); `POST /admin/lender-submissions/`
  (happy / defaults-pending /
  cross-tenant deal 404 /
  cross-tenant program 404 /
  missing-deal 400); `PATCH
  /admin/lender-submissions/<pk>/`
  (status change 200 / partial-
  update preserves other fields
  / unknown status 400 / unknown
  pk 404 / cross-tenant pk 404).

**Test baseline:** `3,533 → 3,586
pass, 1 skipped, 0 fail`. (Planning
§7 M10.3 projected ~25 tests; shipped
53 — same overshoot pattern as M10.1
/ M10.2, covering the auth × cross-
tenant × validation × status-
transition matrix completely.)

## Explicit non-goals for M10.3 (deferred to M10.4+)

- ❌ `Stipulation` model + lifecycle
  verbs (M10.4).
- ❌ `Contract` + `FundingPacket` +
  `FundingStatus` entities (M10.5).
- ❌ `Chargeback` + `net_realized`
  verb (M10.6).
- ❌ `ComplianceRecord` entity +
  `/dealer-ai-f-and-i/` operator UI
  (M10.7).
- ❌ Status-transition constraints.
  M10.3 accepts any-to-any
  transition — operator behavior
  captured as-recorded. Transition
  rules land at M10.4 or M10.7 if
  operator evidence surfaces.
- ❌ Direct lender-portal
  integrations. `record_lender_submission`
  is operator-recorded, not
  lender-portal-driven.
- ❌ Data migration from
  `DealerOnboardingProfile.subprime_lenders`
  free-text field. Per §5.d Option
  C — operators re-populate the
  structured catalog manually.
- ❌ Structured vocabulary for
  `counter_terms` / `approval_terms`.
  Free-form JSON at M10.3;
  vocabulary emerges at M10.7
  compliance layer.
- ❌ Frontend UI (M10.7).

## Reality check

- **Backend baseline:** `3,586 pass, 1
  skipped, 0 fail` (was `3,533` at
  SESSION_107 close).
- **Migrations:** `0001`–`0027`
  (added `0027_lender_entities` —
  three operations: two CreateModel
  + one AddConstraint).
- **Tenancy carriers:** 26 → 28
  (added `LenderProgram` +
  `LenderSubmission`).
- **DRF admin surface:** 49 → 52
  (added three lender endpoints).
- **Frontend baseline:** unchanged
  (34 pass); no frontend at M10.3.
- **`git status`:** clean pending
  the M10.3 commit.
- **Django check:** clean (0
  issues).
- **`makemigrations --check --dry-run`:**
  "No changes detected."

## What SESSION_109 (M10.4) opens with

Per `MILESTONE_10_PLANNING.md` §7
M10.4 + §5.b (Option A confirmed at
SESSION_106): **Stipulation model +
lifecycle verbs**, attached to
`LenderSubmission`. Fixed vocabulary
(`proof_of_income` / `proof_of_insurance`
/ `proof_of_residence` / `references`
/ `other`) per §5.b Option A.

Recommended step sequence for SESSION_109:

1. Push-authorization check for the
   M10.1 + M10.2 + M10.3 commits
   (three commits pending push per
   the M9-close convention).
2. Confirm M10.4 §5-equivalent
   decisions:
   - Stipulation state vocabulary
     (`open` / `cleared` /
     `waived` from planning §1.4)?
   - Attach shape — direct FK to
     `LenderSubmission`, or
     nullable FKs to both
     `LenderSubmission` and
     `DealStructure` (deal-level
     stips vs lender-level stips)?
   - Who satisfies (`documented_by`
     as a User FK vs free-text
     string)?
   - Photo/document evidence
     capture — nested M10.4 or
     defer to M10.7?
3. Read first:
   - `MILESTONE_10_PLANNING.md`
     §1.4 + §7 M10.4.
   - `docs/handoffs/SESSION_108_m10_inc3_lender.md`
     (this file).
   - `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
     §1.9 (stipulations workflow)
     + §7.3 (stipulation-tracking
     pain).
   - `backend/dealer_ai/models.py::LenderSubmission`
     (M10.3 substrate — attach
     target).
   - `backend/dealer_ai/services/f_and_i/lender.py`
     (pattern to mirror for
     `stipulation.py`).
4. Verify starting state:
   `python3 manage.py test dealer_ai`
   → `3,586 pass, 1 skipped, 0
   fail`.
5. Draft: `Stipulation` model +
   migration `0028`, tenancy
   carrier extension 28 → 29,
   `services/f_and_i/stipulation.py`
   with lifecycle verbs,
   endpoints, ~20 focused tests.
6. Full-suite verification. Target
   3,586 → ~3,606.
7. Ship handoff
   `docs/handoffs/SESSION_109_m10_inc4_stipulation.md`.
8. Overwrite
   `00-START-NEXT-SESSION.md` with
   M10.5 priority.

## Commit

Local only. Push to `origin/main`
deferred per M9-close convention.
Message:

```
Milestone 10 · Increment 3 — LenderProgram + LenderSubmission entities (SESSION_108)

M10.3 ships the lender substrate for the F&I workflow:

- New LenderProgram model + migration 0027 (three operations).
  Per-dealership catalog with unique constraint on
  (dealership, name). is_active soft-delete pattern.
- New LenderSubmission model. Mandatory FK to DealStructure
  (CASCADE) + FK to LenderProgram (PROTECT — deactivate rather
  than delete). Fixed 4-value status vocabulary. Free-form
  counter_terms / approval_terms JSONFields.
- Tenancy carrier extension 26 → 28 (both entities).
- New services/f_and_i/lender.py — six verbs.
  record_lender_program (typed duplicate error) +
  list_active_lender_programs (pure filter) +
  record_lender_submission (transactional with cross-tenant
  guards) + update_lender_submission_status (partial update via
  update_fields) + get_lender_submission (tenant-scoped read) +
  list_submissions_for_deal_structure (FK filter).
- Three new endpoints under /api/dealer-ai/admin/ — all reuse
  M10.1's IsFinanceManagerOrOwnerAtActiveDealership permission
  class. POST /lender-programs/ (409 on duplicate), POST
  /lender-submissions/ (404 on cross-tenant), PATCH
  /lender-submissions/<pk>/ (400 on unknown status, 404 on
  cross-tenant pk).
- 53 focused tests. Baseline 3,533 → 3,586 pass.

Four §1.3 decisions resolved at session open (all as-
recommended): §1.3.a Option A (attach FK to DealStructure),
§1.3.b Option A (fixed 4-value status), §1.3.c Option A
(per-dealership catalog), §1.3.d Option A (free-form JSON
terms).
```

## Deferred / observations for M10.4+

- `services/f_and_i/` now has three
  submodules (`credit_application.py`,
  `deal_structure.py`, `lender.py`).
  Same shape as `services/analytics/`
  from M8. M10.4-M10.7 will add
  `stipulation.py`, `contract.py`,
  `funding.py`, `chargeback.py`.
- The `IsFinanceManagerOrOwnerAtActiveDealership`
  permission class introduced at
  M10.1 is now reused verbatim by
  every M10 endpoint (M10.1, M10.2,
  M10.3). Zero permission-class
  drift across the F&I admin
  surface.
- `on_delete=PROTECT` on
  `LenderSubmission.lender_program`
  is a new pattern for this project
  (M1-M9 used CASCADE or SET_NULL
  exclusively). If M10.4-M10.7
  encounter similar "historical
  record shouldn't cascade away"
  scenarios, PROTECT is the right
  shape.
- The `update_lender_submission_status`
  verb pattern (accept `new_status`
  + optional terms/notes; use
  `.save(update_fields=...)`) is
  the reusable shape for M10.4
  Stipulation lifecycle
  (`open` → `cleared` / `waived`)
  and M10.5-M10.6 contract /
  funding / chargeback verbs.
- Nothing in M10.3 required amending
  M1-M9 or M10.1-M10.2 behavior.
  Consumption is FK-only.
