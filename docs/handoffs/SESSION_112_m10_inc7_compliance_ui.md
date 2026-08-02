---
title: "SESSION_112 handoff — Milestone 10 · Increment 7 (M10.7 — ComplianceRecord + operator UI)"
status: historical
type: handoff
date: 2026-08-02
session: 112
milestone: 10
milestone_status: in_progress
increment: 7
increment_status: shipped
commit: TBD
---

# SESSION_112 — Milestone 10 · Increment 7 (M10.7 — ComplianceRecord + operator UI)

## What shipped

`ComplianceRecord` entity + additive
URL fields on `Stipulation` +
`BackEndProductAgreement` +
`services/f_and_i/compliance.py`
module with four verbs +
four new backend endpoints +
first F&I frontend surface
(`/dealer-ai-f-and-i/` two-tab MVP:
deals list + per-deal compliance
audit) + `fAndIApi.ts` client +
tenancy carrier extension (33 → 34)
+ 31 backend + 17 frontend focused
tests.

Six design questions surfaced at
session open and were confirmed
with the user (all as-recommended);
`MILESTONE_10_PLANNING.md` §0.a
amended.

**Load-bearing decisions confirmed at
session open (recorded in
`MILESTONE_10_PLANNING.md` §0.a):**

1. **§1.8.a — ComplianceRecord
   attach shape: Option A.** Per-
   Contract `OneToOne` (CASCADE).
   Matches FINANCE §6.9 deal-
   jacket mental model.
2. **§1.8.b — Per-concern vs
   single-entity: Option A.**
   Single `ComplianceRecord` with
   typed timestamp/boolean/text
   columns per FINANCE §6.1-§6.9
   concern. Flat, queryable, cheap.
3. **§1.8.c — Storage plumbing:
   Option C.** Nullable URL fields
   for external document
   references on ComplianceRecord
   (`deal_jacket_url`),
   Stipulation (`evidence_url`),
   BEPA (`product_agreement_url`).
   Zero upload plumbing at M10.7;
   captures operator reality
   (docs live in Google Drive /
   DMS).
4. **§1.8.d — Operator UI scope:
   Option C.** Two-tab MVP: deals-
   in-progress list + per-deal
   compliance-audit view. Serves
   FINANCE §7.6 pain-point
   directly. Full 7-step workflow
   operates via per-vehicle
   drill-downs from M9.5.
5. **§1.8.e — Frontend route
   family: Option A.** New
   `/dealer-ai-f-and-i/` route
   family. Two routes:
   `/dealer-ai-f-and-i/` (deals
   list) +
   `/dealer-ai-f-and-i/:contract_id/compliance/`.
6. **§1.8.f — M10.7 vs M10.8
   ordering: Option A.** Split.
   M10.7 (this session) ships
   implementation only. M10.8
   (SESSION_113) is doc close-out
   per M9-close SESSION_105
   pattern.

**M10.7 deliverables (seven):**

1. **New `ComplianceRecord` model
   + additive URL extensions +
   migration `0031`.** Migration
   ships three operations: two
   `AddField` on existing entities
   (Stipulation.evidence_url +
   BEPA.product_agreement_url) +
   one `CreateModel` for
   ComplianceRecord. Field
   surface per §1.8.b Option A —
   typed timestamp columns for
   Reg Z / OFAC (+ ofac_hit
   bool) / Red Flags (+
   red_flags_notes) / Privacy /
   Safeguards / Adverse Action
   (+ adverse_action_reason) +
   `retention_expires_at`
   denormalized from parent CA +
   `deal_jacket_url`.
2. **Tenancy carrier extension
   33 → 34.**
3. **New `services/f_and_i/compliance.py`
   module** — four verbs:
   - `record_compliance(dealership,
     contract, ...)` — transactional.
     Refuses cross-tenant +
     duplicate (OneToOne
     invariant via
     `ComplianceAlreadyExistsError`
     → 409). Auto-populates
     `retention_expires_at` from
     parent CA for deal-jacket
     query-ability.
   - `update_compliance(compliance,
     **field_kwargs)` — targeted
     update via
     `.save(update_fields=...)`.
     Whitelist of 11 updatable
     fields; unknown field
     raises. Unspecified fields
     preserved.
   - `get_compliance(pk,
     dealership)` — tenant-scoped
     read.
   - `deal_jacket_summary(contract)`
     — pure aggregate. Returns
     dict of contract + compliance
     + funding + stipulations +
     BEPA + chargebacks. Powers
     the operator UI's per-deal
     view in one read.
4. **`services/f_and_i/__init__.py`
   facade** — extended to re-
   export the four new M10.7
   verbs + `CrossTenantComplianceError`
   + `ComplianceAlreadyExistsError`
   alongside M10.1-M10.6 exports.
5. **Four new backend endpoints:**
   - `GET /admin/f-and-i/deals/`
     — deals-in-progress list
     (filters: state,
     funding_state,
     has_chargebacks).
     100-row server cap; no
     pagination at M10.7.
   - `POST /admin/compliance-records/`
     — create.
   - `PATCH /admin/compliance-records/<pk>/`
     — partial-update columns.
   - `GET /admin/deal-jackets/<contract_pk>/`
     — aggregated compliance-
     audit view.
6. **Two new frontend pages
   under `/dealer-ai-f-and-i/`:**
   - `DealerFandIDeals.tsx` —
     deals-in-progress list with
     three filter controls
     (contract state, funding
     state, has_chargebacks
     checkbox). Table with
     click-through to per-deal
     view.
   - `DealerFandICompliance.tsx`
     — per-deal compliance-audit
     view. Renders the seven
     concern rows with "Mark
     now" / "Re-mark" buttons
     for each; server-populates
     the timestamp on click.
     Also shows related
     stipulations (with
     evidence-URL links) +
     chargebacks + funding
     state.
7. **`fAndIApi.ts` client + nav
   entry.** `fetchDeals`,
   `fetchDealJacket`,
   `createCompliance`,
   `updateCompliance` +
   TypeScript row types for
   each entity in the aggregate.
   Nav item added to `App.tsx`
   (`ClipboardCheck` icon,
   between Analytics and Setup).

**31 backend + 17 frontend focused tests:**

- **Backend
  `test_m107_compliance.py`
  (31 tests):**
  - Model (3 tests): defaults,
    cross-tenant clean, OneToOne
    uniqueness.
  - Evidence URL extensions (3
    tests): Stipulation
    evidence_url default blank +
    accepts URL; BEPA
    product_agreement_url
    default blank.
  - Tenancy carrier (1).
  - `record_compliance` (4):
    retention auto-populate,
    deal-jacket-url + notes
    persist, cross-tenant,
    duplicate raises.
  - `update_compliance` (4):
    partial-update persists,
    partial-update preserves,
    unknown field raises, no-
    kwargs no-op.
  - `get_compliance` (2):
    tenant hit + cross-tenant
    None.
  - `deal_jacket_summary` (7):
    contract state, stipulations,
    BEPAs, chargebacks, funding
    state, compliance None-when-
    absent, compliance populated
    when created.
  - Endpoint (7): create 201,
    duplicate 409, patch 200,
    deal-jacket read returns
    summary, unknown contract
    404, deals list returns
    contract, state filter
    narrows result.
- **Frontend
  `DealerFandIDeals.test.tsx`
  (8 tests) +
  `DealerFandICompliance.test.tsx`
  (9 tests):** filter
  interactions, empty state,
  error state, create-compliance
  flow, seven concern rows
  rendering, mark-OFAC click,
  stipulation display, chargeback
  display, funding amount
  display.

**Test baseline:** `3,699 → 3,730
pass, 1 skipped, 0 fail` backend +
`34 → 51 pass` frontend. (Planning
§7 M10.7 projected ~20 backend +
~25 frontend; shipped 31 + 17.)

## Explicit non-goals for M10.7 (deferred)

- ❌ Upload plumbing for
  photos/documents (§1.8.c
  Option C — URL fields only).
  Full Cloudinary/S3 wiring is
  a post-M10 initiative if
  operator evidence demands.
- ❌ Full 7-step operator
  workflow (§1.8.d Option C —
  two-tab MVP only). Credit-app
  intake / deal desking /
  lender submission / stip
  chase / contract signing /
  funding operate via existing
  per-vehicle / per-endpoint
  admin surfaces.
- ❌ Server-side pagination on
  the deals list (100-row
  server cap; client-side
  pagination). Add in M11+ if
  operator evidence surfaces.
- ❌ Compliance-record close-
  out for a voided Contract
  (deferred — voided contracts
  keep their compliance rows
  as historical records; no
  automatic close-out logic).
- ❌ M10.8 doc close-out
  (§1.8.f Option A — split
  into SESSION_113).

## Reality check

- **Backend baseline:** `3,730
  pass, 1 skipped, 0 fail` (was
  `3,699` at SESSION_111 close).
- **Migrations:** `0001`–`0031`
  (added
  `0031_compliance_record_and_evidence_urls`
  — three operations: two
  AddField + one CreateModel).
- **Tenancy carriers:** 33 → 34
  (added `ComplianceRecord`).
- **DRF admin surface:** 60 → 64
  (added four M10.7 endpoints).
- **Frontend baseline:** `51
  pass` (was `34`; added 17
  M10.7 tests).
- **Frontend operator routes:**
  9 → 11 (added two
  `/dealer-ai-f-and-i/*`
  routes).
- **`git status`:** clean pending
  the M10.7 commit.
- **Django check:** clean (0
  issues).
- **`makemigrations --check
  --dry-run`:** "No changes
  detected."
- **`tsc --noEmit` + `vite build`:**
  both clean.

## What SESSION_113 (M10.8) opens with

Per `MILESTONE_10_PLANNING.md` §7
M10.8: **Documentation-only
closeout.** Matches the M9-close
SESSION_105 pattern.

Recommended step sequence for
SESSION_113:

1. Push-authorization check for
   the M10.1-M10.7 commits (seven
   pending push; M10.8 will
   likely be the push moment
   per M9-close convention).
2. **M10.8 deliverables (six
   docs + one coordinated
   commit):**
   - `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
     — new. Mirror M9
     retrospective shape.
   - `docs/CAPABILITY_MATRIX.md`
     §7k — new subsection for
     M10.
   - `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
     §Milestone 10 SHIPPED
     header.
   - `docs/roadmap/MILESTONE_10_PLANNING.md`
     frontmatter flip
     (`status: draft` →
     `status: shipped`).
   - `docs/DEALER_KIT_SESSION_START.md`
     refresh (baseline
     updates).
   - `docs/roadmap/MILESTONE_11_PLANNING.md`
     — new per standing user
     directive.
3. Verify starting state.
4. Coordinated commit landing
   every M10.1-M10.7 stage +
   the six close-out docs.
5. Push all M10 commits
   together after explicit user
   authorization.

## Commit

Local only. Push to `origin/main`
deferred per M9-close convention
— the M10.8 close will be the
push moment. Message:

```
Milestone 10 · Increment 7 — ComplianceRecord + operator UI (SESSION_112)

M10.7 ships the compliance-audit substrate + first F&I operator UI
for the F&I workflow. This is the final implementation increment
of Milestone 10 — M10.8 will close the milestone documentation-
only per the M9-close SESSION_105 pattern.

- New ComplianceRecord model + migration 0031 (three operations:
  Stipulation.evidence_url + BEPA.product_agreement_url AddField +
  ComplianceRecord CreateModel). OneToOne to Contract (CASCADE)
  per §1.8.a Option A — FINANCE §6.9 deal-jacket alignment.
  Single-entity typed-columns model per §1.8.b Option A — Reg Z /
  OFAC (+ hit) / Red Flags (+ notes) / Privacy / Safeguards /
  Adverse Action (+ reason) / Retention + external
  deal_jacket_url.
- Additive URL extensions per §1.8.c Option C — Stipulation and
  BEPA gain nullable URL fields for external document references
  (Google Drive / DMS). Zero upload plumbing at M10.7; full
  storage infrastructure is a discrete post-M10 initiative.
- Tenancy carrier extension 33 → 34.
- New services/f_and_i/compliance.py — four verbs. record + update
  (targeted save with field whitelist) + get + deal_jacket_summary
  (pure aggregate powering the operator UI's per-deal view).
- Four new backend endpoints — deals-in-progress list (filters:
  state / funding_state / has_chargebacks), POST + PATCH
  compliance-records (409 on duplicate), GET deal-jackets/pk.
- First F&I operator UI surface — /dealer-ai-f-and-i/ two-tab MVP
  per §1.8.d Option A. DealerFandIDeals (filterable list) +
  DealerFandICompliance (seven concern rows with mark-timestamp
  actions). New fAndIApi.ts client. Nav entry added.
- 31 backend + 17 frontend focused tests. Backend baseline 3,699
  → 3,730 pass. Frontend baseline 34 → 51 pass.

Six §1.8 decisions resolved at session open (all as-recommended):
§1.8.a Option A (OneToOne per Contract), §1.8.b Option A (single-
entity typed columns), §1.8.c Option C (URL fields, no upload
plumbing), §1.8.d Option C (two-tab MVP), §1.8.e Option A (new
route family), §1.8.f Option A (split M10.7 impl / M10.8 close-
out).
```

## Deferred / observations for M10.8+ (and post-M10)

- `services/f_and_i/` now has
  seven submodules (M10.1
  `credit_application` + M10.2
  `deal_structure` + M10.3
  `lender` + M10.4 `stipulation`
  + M10.5 `contract` +
  `funding` + M10.6 `chargeback`
  + **M10.7 `compliance`**).
  Complete F&I service surface.
- **New pattern — field
  whitelist for partial-update
  verbs** (`_UPDATABLE_FIELDS`
  frozenset in
  `compliance.py::update_compliance`).
  Protects against typos and
  misplaced kwargs. Worth
  preserving for any future
  partial-update service verb.
- **New pattern — pure
  aggregate for operator UI**
  (`deal_jacket_summary`).
  Bundles multiple related
  entities into one dict in one
  service call. Contrasts with
  M9.3 analytics verbs (which
  return typed row objects) —
  operator-UI aggregates need
  nested dicts for the frontend
  render. Both shapes are valid;
  choose based on downstream
  consumer.
- **Frontend F&I surface is
  MVP.** Two tabs cover the
  deal-jacket compliance-audit
  workflow. Full CRUD across
  credit-apps / deal structures
  / lender submissions / stips
  / chargebacks operates via
  the existing admin API
  endpoints (no dedicated
  frontend yet). If operator
  evidence surfaces a need for
  richer UI on those entities,
  it lands as a post-M10
  initiative — the two-tab MVP
  is the minimum viable
  compliance surface, not the
  full operator workstation.
- **Retention denormalization
  on ComplianceRecord.**
  `retention_expires_at` is
  copied from parent
  CreditApplication at
  ComplianceRecord create time.
  If CA retention is later
  extended (retention rule
  change, legal hold), the CA
  is source-of-truth; the
  ComplianceRecord denorm
  becomes stale until re-
  populated. Add a
  `resync_retention` verb at
  M10.8+ if operator evidence
  demands.
- Nothing in M10.7 required
  amending M1-M9 or M10.1-M10.6
  business logic. Consumption
  is FK-only + additive URL
  extensions.
