---
title: Pilot onboarding playbook
status: active
type: reference
date: 2026-08-02
milestone_shipped: 19
increment_shipped: 5
audience: platform operator (Chris)
authoritative_journey: backend/dealer_ai/tests/test_m195_pilot_dry_run.py
---

# Pilot onboarding playbook

Operator reference for converting a demo tester into a live pilot
dealership. Ships at **Milestone 19 · Increment 5 (SESSION_158)**
per `MILESTONE_19_PLANNING.md` §7 M19.5.

## Reading this doc

This is a **text-first playbook**. Per §0.a M19.5 decision 2, we
reference UI controls by their stable `data-testid` selectors
rather than by screenshots — the code-level test suite already
asserts on these selectors, so any rename fires CI failure and
this doc stays honest.

The authoritative end-to-end contract for the flow described here
lives in
`backend/dealer_ai/tests/test_m195_pilot_dry_run.py::FullPilotJourneyDryRun::test_full_journey`.
If the playbook and that test disagree, the test wins.

## Prerequisites

Before starting a pilot conversion:

- A demo dealership already exists with the tester's archetype
  (retail-subprime / floor-planned / BHPH) — see the M18.1-M18.4
  archetype-builder handoffs.
- The tester has expressed intent to convert. Record their
  business context (business name, dealer type, BHPH enabled,
  approximate inventory size).
- A backend Django admin user for the tester's owner
  (`owner_username`) exists — create it out-of-band via
  `createsuperuser` or the standard user-provisioning path
  before running `POST /admin/pilots/create/`.
- The starting-state check from
  `docs/handoffs/SESSION_157_m19_inc4_frontend_and_import_endpoint.md`
  is green (backend + frontend suites passing).

## Journey overview

The playbook covers thirteen phases matching the dry-run test's
narrative. Each phase names the backend verb / endpoint it
exercises and the `data-testid` selector on the frontend admin
surface.

| # | Phase | Backend verb | Frontend selector |
| --- | --- | --- | --- |
| 1 | Record prospect | `create_prospect` | (no UI yet — Django admin) |
| 2 | Qualify prospect | `advance_prospect_state(qualified)` | (no UI yet) |
| 3 | Create pilot dealership | `POST /admin/pilots/create/` | `pilot-create-submit` |
| 4 | Convert prospect | `advance_prospect_state(converted, converted_dealership=pilot)` | (no UI yet) |
| 5 | Configure store shape | `POST /admin/pilots/<slug>/checklist/advance/` | `pilot-advance-profile_configured` |
| 6 | Import inventory | `POST /admin/pilots/<slug>/inventory/import/` | `pilot-upload-submit` |
| 7 | Advance inventory step | `POST .../checklist/advance/` | `pilot-advance-inventory_imported` |
| 8 | Add users + roles | (Django admin / User provisioning) | (no UI yet) |
| 9 | Advance user + capability steps | `POST .../checklist/advance/` (×3) | `pilot-advance-owner_user_added` etc. |
| 10 | Confirm readiness | `POST .../checklist/advance/` (readiness_confirmed) | `pilot-advance-readiness_confirmed` |
| 11 | Verify outbound suppression | `is_outbound_enabled(pilot)` == False | (no UI — check policy) |
| 12 | Cross-tenant + guard sanity | (invariant, not action) | — |
| 13 | Terminate pilot | `POST /admin/pilots/<slug>/terminate/` | `pilot-terminate-confirm` |

## Phase 1 — Record the prospect

A prospect is a **pre-tenant operator record** (§0.a M19.1
decision 1 — not a tenancy carrier). It captures Chris's operator
intent before any tenant-scoped state exists.

**Backend call:** `services.pilot_onboarding.create_prospect`

- Required: `contact_name`, `contact_email`, `dealer_business_name`.
- Optional but recommended: `dealer_type`, `bhph_enabled`,
  `estimated_inventory_size`, `source_demo_dealership`.
- `source_demo_dealership` preserves which demo archetype the
  tester used — valuable audit signal for tracking which
  archetypes convert best.

**No frontend UI at M19.5.** Prospects are managed via the Django
admin or a Python shell for now. A future increment can surface
them if volume warrants.

**Expected outcome:** a `PilotProspect` row with
`eligibility_state='prospect'`. The state machine now permits
transitions to `qualified` or `declined`.

## Phase 2 — Qualify the prospect

**Backend call:** `advance_prospect_state(prospect, new_state='qualified', notes_append=...)`.

The `notes_append` field is your running commentary — it appends
to `chris_notes` with a blank-line separator so the audit trail
preserves your judgment.

**Legal transitions from `prospect`:** `qualified`, `declined`.
Skipping straight to `converted` raises
`InvalidProspectTransitionError` (mapped to 409 if surfaced via a
future endpoint).

**Expected outcome:** `prospect.eligibility_state == 'qualified'`.

## Phase 3 — Create the pilot dealership

**Endpoint:** `POST /admin/pilots/create/`

**Frontend surface:** `<PilotOnboardingSection>` embedded in
`/dealer-ai-admin`. Fill in:

- `data-testid="pilot-create-slug"` — kebab-case slug, unique
  across every Dealership (demo, pilot, or live). Collisions
  return 409 with a friendly error surfaced under
  `data-testid="pilot-create-error"`.
- `data-testid="pilot-create-name"` — human-facing store name.
- `data-testid="pilot-create-owner"` — Django username of the
  pre-created owner user. Unknown usernames return 400.
- Click `data-testid="pilot-create-submit"`.

**What the backend does atomically:**

- Creates the `Dealership` row with `is_pilot=True`,
  `is_demo=False`, `outbound_enabled=False`.
- Seeds the M13.1 default chart of accounts.
- Attaches the owner as `UserDealershipRole(role='dealer_owner')`.
- Creates a `DealerOnboardingProfile` (any `profile_kwargs`
  populated at create time; otherwise Chris fills it during the
  `profile_configured` step).
- Creates the `PilotOnboardingChecklist` with `is_ready=False`.
- Fires the `dealership_created` step (already complete).

**Expected outcome:** the pilot appears in the list panel with an
"In progress" badge (`data-testid="pilot-row-<slug>"`).

## Phase 4 — Convert the prospect

**Backend call:**
`advance_prospect_state(prospect, new_state='converted', converted_dealership=<new pilot>)`.

The `converted_dealership` FK is REQUIRED — advancing to
`converted` without it raises `ConvertedRequiresDealershipError`
(the `PilotProspect.clean` invariant enforces this at the model
layer too).

**Expected outcome:** `prospect.eligibility_state == 'converted'`
+ `prospect.converted_dealership_id == pilot.pk`.

## Phase 5 — Configure store shape

**Endpoint:** `POST /admin/pilots/<slug>/checklist/advance/`
with `step_slug='profile_configured'`.

**Frontend selector:** `data-testid="pilot-advance-profile_configured"`
inside the detail panel (open the pilot by clicking its list row —
detail panel is at `data-testid="pilot-detail-<slug>"`).

Before advancing, populate the `DealerOnboardingProfile` fields
via the existing Django admin or the `/dealer-ai-onboarding` page:
`main_brands`, `sales_phone`, dealer_type, subprime_lenders,
etc. Advancing the checklist step is a **codified acknowledgment**
that Chris finished the store-shape work; it does NOT edit the
profile.

**Expected outcome:** `profile_configured` step row exists with
`completed_at` populated. Optimistic UI refresh reflects the
green checkmark; the step's Complete button disappears.

## Phase 6 — Import inventory

**Endpoint:** `POST /admin/pilots/<slug>/inventory/import/`
(multipart `csv` field).

**Frontend selectors:**

- `data-testid="pilot-upload-input"` — file input; expects a CSV.
- `data-testid="pilot-upload-submit"` — triggers the upload.

**CSV schema:** see `docs/PILOT_INVENTORY_TEMPLATE.md` — the
21-column vocab from `services/inventory_import.py::CSV_FIELDS`.
Required per row: `year`, `model`, `price` + one of `stock_number`
or `vin`.

**Partial-success semantics:** accepted rows commit; rejected
rows surface with per-row reason strings. Chris fixes the
rejected rows and re-uploads without losing the good rows.

**Expected outcome (frontend):**

- `data-testid="pilot-upload-result"` shows
  `Accepted: <N> · Rejected: <M>`.
- If `M > 0`, `data-testid="pilot-upload-rejected"` expands to
  show `stock_number` + reason per rejected row.
- Vehicles carry `source="pilot-inventory-import"`
  (`PILOT_IMPORT_SOURCE` constant) so pilot rows stay isolatable
  from franchise-scraper rows.

**Common rejects and remedies:**

| Reason | Remedy |
| --- | --- |
| `invalid year: '...'` | Ensure year is 1980–2100 inclusive. |
| `missing model` | Populate the `model` column. |
| `invalid price: '...'` | Ensure `price` parses as `Decimal > 0`. Excel `$18,995` OK. |
| `missing both stock_number and VIN` | At least one identifier per row. |

## Phase 7 — Advance the inventory step

**Endpoint:** `POST /admin/pilots/<slug>/checklist/advance/`
with `step_slug='inventory_imported'`.

**Frontend selector:** `data-testid="pilot-advance-inventory_imported"`.

Chris signs off after reviewing accepted / rejected counts. Not
gated by "must have zero rejects" — that's an operator judgment,
not a machine invariant.

## Phase 8 — Add users + roles

Currently a Django-admin exercise. Provision the tester's staff
(sales manager, advisors, recon manager) as `User` rows +
`UserDealershipRole` rows scoped to the pilot Dealership.

A future increment may add a user-provisioning UI. Not blocked
by M19.

## Phase 9 — Advance user + capability steps

Three sequential advances via the checklist stepper:

- `owner_user_added` → `data-testid="pilot-advance-owner_user_added"`.
- `staff_users_added` → `data-testid="pilot-advance-staff_users_added"`.
- `capabilities_enabled` → `data-testid="pilot-advance-capabilities_enabled"`.

Each is a codified acknowledgment; no cross-step invariants until
the final step.

## Phase 10 — Confirm readiness

**Endpoint:** `POST /admin/pilots/<slug>/checklist/advance/` with
`step_slug='readiness_confirmed'`.

**Frontend selector:** `data-testid="pilot-advance-readiness_confirmed"`.

**Precondition:** every prior step in
`PILOT_ONBOARDING_STEP_ORDER` must already have a completed row.
Advancing prematurely returns 409
(`PilotReadinessNotConfirmedError`); the frontend surfaces this
at `data-testid="pilot-advance-error"` with copy
"Cannot advance — prior steps incomplete or step already done."

**Expected outcome:**

- `PilotOnboardingChecklist.is_ready` flips to `True` in the
  same transaction.
- List row badge flips to "Ready" (`data-testid="pilot-row-<slug>"`
  now contains a filled badge).
- `is_pilot_ready(pilot)` predicate returns `True`.

## Phase 11 — Verify outbound suppression

M19.1's outbound guard is orthogonal to tenant-type flags: it
checks the policy field `Dealership.outbound_enabled`. A
freshly-created pilot has `outbound_enabled=False` by design.

**Sanity check:** in a Django shell:

```python
from dealer_ai.services.demo_store import is_outbound_enabled, suppress_if_outbound_disabled
is_outbound_enabled(pilot)  # False
suppress_if_outbound_disabled(pilot, verb_name="playbook.check")  # SuppressedOutbound marker
```

Only explicitly flip `outbound_enabled=True` when the pilot has
been vetted end-to-end AND you've reviewed which verbs egress
(the M18.1 outbound-egress scanner allowlist).

## Phase 12 — Cross-tenant + guard sanity

The M19 substrate carries three invariants that hold silently but
matter for operator confidence:

- **Cross-tenant isolation.** Pilot inventory is scoped by the
  Dealership FK. A second dealership's Vehicles never leak into
  the pilot's queries.
- **Non-pilot import guard.** `import_pilot_inventory` against a
  demo / live Dealership raises `NonPilotImportError` (500). The
  endpoint layer's slug filter catches this first with 404; the
  domain error is defense-in-depth.
- **Non-pilot terminate guard.** `terminate_pilot` against a
  non-pilot raises `NonPilotTerminationError` (500). Same
  defense-in-depth posture.

These invariants are asserted in
`test_m195_pilot_dry_run.py::SafetyGuardDryRunTests` — if any of
them regress, CI fails before the code ships.

## Phase 13 — Terminate the pilot

**Endpoint:** `POST /admin/pilots/<slug>/terminate/`

**Frontend selectors:**

- `data-testid="pilot-terminate-mode"` — mode selector:
  - `archive` (default) — flips `is_pilot=False`, populates
    `terminated_at` + `termination_reason`, but preserves every
    child row (Vehicles, Users, Salespeople, memberships,
    checklist history). The pilot leaves the operator list but
    stays queryable in the DB for post-mortem review.
  - `cleanup` — cascades reverse-order per the M18.2 pattern:
    child rows are deleted (Vehicles, etc.), pilot-owned Users
    are deleted so a future re-create doesn't collide on
    `username`. Use for PII removal at pilot end.
- `data-testid="pilot-terminate-reason"` — free-form reason
  textarea.
- `data-testid="pilot-terminate-init"` — first click reveals the
  confirm gate.
- `data-testid="pilot-terminate-confirm"` — second click actually
  posts.

The two-click gate prevents accidental single-click termination —
particularly important for `cleanup` mode which is destructive.

**Expected outcome:**

- Pilot leaves the response of
  `GET /admin/pilots/` (`list_pilot_dealerships` filters on
  `terminated_at IS NULL`).
- `PilotProspect.converted_dealership` FK remains populated
  under archive mode (the row still exists) so the audit trail
  is preserved.
- Under cleanup mode, the `PilotProspect.converted_dealership`
  FK becomes `None` (SET_NULL cascade fires when the Dealership
  row is deleted... wait — the Dealership row is NOT deleted;
  only children are. So the FK stays valid under cleanup too.)
  Correct read: under BOTH modes the FK stays intact.

## Rollback / recovery

If something goes wrong mid-flow:

- **Bad slug used at create:** the create atomicity means nothing
  committed. Try again with a fresh slug.
- **Wrong owner attached:** create fresh dealer_owner
  `UserDealershipRole` for the correct user; delete the wrong
  one via Django admin. Advance the checklist normally after.
- **Bad inventory upload:** re-upload with corrections — M6.3
  semantics inherited via M19.2 mean an existing `stock_number`
  gets UPDATED (not rejected) on re-import.
- **Readiness precondition failed:** the frontend surfaces the
  missing step names in the 409 body. Complete them, then re-
  attempt.
- **Wrong pilot terminated:** archive mode is recoverable — flip
  `is_pilot=True` + null `terminated_at` via Django admin. Cleanup
  mode is NOT recoverable (children deleted); tread carefully.

## References

- `MILESTONE_19_PLANNING.md` §7 M19.1–M19.5 — the shipped scope.
- `docs/handoffs/SESSION_154_m19_inc1_backend_substrate.md` —
  M19.1 substrate handoff.
- `docs/handoffs/SESSION_155_m19_inc2_inventory_import.md` —
  M19.2 inventory-import handoff.
- `docs/handoffs/SESSION_156_m19_inc3_endpoints.md` — M19.3
  endpoint handoff.
- `docs/handoffs/SESSION_157_m19_inc4_frontend_and_import_endpoint.md` —
  M19.4 frontend handoff.
- `docs/PILOT_INVENTORY_TEMPLATE.md` — CSV schema.
- `backend/dealer_ai/tests/test_m195_pilot_dry_run.py::FullPilotJourneyDryRun::test_full_journey` —
  authoritative end-to-end contract.
- `frontend/src/components/pilots/PilotOnboardingSection.tsx` +
  its test file — component selector contract.
