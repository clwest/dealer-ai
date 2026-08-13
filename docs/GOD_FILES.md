# God-File Decisions

Several files in this repository are much larger than typical
"one thing per file" style would recommend. This document
explains why each grew, why it has not been split, and what
boundary a future split would draw.

The short version: none of these files actively blocks testing,
safety, or public runnability. Splitting them now would add
churn without product value. The scars are visible; the reasons
are documented.

## `backend/dealer_ai/models.py` — ~8,185 LOC, 59 models

### Why it grew

Every domain model — dealership, salesperson, vehicle,
acquisition, cost, stage, event, photo, listing, condition
report, finding, decision, work order, part, vendor, sale,
delivery, credit application, deal structure, lender program,
lender submission, stipulation, contract, funding, chargeback,
compliance record, lead, chat session, message, follow-up
cadence, be-back, test drive, deal writeup, BHPH note, payment,
promise-to-pay, collection contact, repossession, GL account,
journal entry, journal entry line, template, template line,
trial balance snapshot, snapshot row, job log, stage aging
snapshot, SLA breach record, tester feedback, pilot prospect,
pilot onboarding checklist, pilot onboarding step, dealer
onboarding profile, user dealership role — is defined in this
one file.

The convention was set early (M1) and preserved deliberately
through each subsequent milestone. Django tolerates a single
`models.py`; the alternative (`models/` package with sub-
modules) requires manual `app_label` configuration and creates
import-order fragility during signal registration.

### Why it has not been split

- The Django migration graph tracks models by app label +
  class name, not file path. Splitting `models.py` does not
  affect the schema.
- Every model has extensive test coverage in
  `backend/dealer_ai/tests/`, organized per-milestone (not
  per-model). Splitting `models.py` would not simplify test
  discovery.
- Model relationships (FKs, reverse accessors, signal
  handlers) cross domain boundaries constantly. A vehicle
  references acquisition; acquisition posts to GL; GL posts
  from BHPH payments; BHPH payments come from sales; sales
  came from leads. Any partition would still have imports
  cutting across the boundary.
- The one legitimate cost — reading time when navigating with
  a plain editor — is mitigated by tag-based navigation and
  IDE symbol jumps. In practice the file is opened at a
  specific model definition, not read top-to-bottom.

### Future split boundary

If this file needs to be split, the natural boundary is by
department (finance, inventory, BHPH, accounting, admin, sales),
using a `models/` package with `__init__.py` re-exports so
existing imports do not break. Migrations would be unaffected
because the app label stays `dealer_ai`.

Trigger for that work: model count crossing 100, or model
addition rate exceeding one per week sustained over two
milestones.

## `backend/dealer_ai/services/chat_engine.py` — ~7,311 LOC

### Why it grew

Every function that participates in the customer-facing chat
turn — intent detection (`detect_unsafe_request`,
`detect_rate_inquiry`, `detect_appointment_request`, ~15
detectors), pre-LLM guards (~8 guard invocations),
post-LLM scrub orchestration (~12 scrubbers), inventory lookup
helpers (`customer_visible_vehicles`,
`customer_lookup_visible_vehicle_by_id`,
`customer_lookup_visible_vehicle_by_stock`), response builders
(`build_negotiation_response`, cash-mode reply builder), and
prompt assembly (system prompt template, dealer profile
injection) — lives in this one module.

The chat turn is the most heavily tested subsystem in the
repository. The functions are pure enough that unit testing
them individually against the mocked LLM works well; that
constrained the growth trajectory into "many small functions
in one file" rather than "several huge functions across many
files."

### Why it has not been split

- The intent detectors, guards, and scrubbers form an ordered
  pipeline. The order is load-bearing (documented in
  `docs/PROJECT_PIPELINE.md`). Splitting them across files
  makes the ordering less legible, not more.
- Post-LLM scrubs share regex patterns and helper functions
  that would need to be re-exported across files if split.
- Every function is testable in isolation; test files are
  already organized per-scrub or per-detector.

### Future split boundary

The cleanest split is by phase:
`chat_engine/intent.py` (all detectors),
`chat_engine/guards.py` (pre-LLM guards),
`chat_engine/prompt.py` (system prompt assembly),
`chat_engine/scrub.py` (post-LLM scrubbers, using the shared
regex helpers from `llm_safety.py`),
`chat_engine/response.py` (response builders),
`chat_engine/__init__.py` (public entry points:
`handle_user_message`, `handle_operator_message`).

Trigger: another scrubbing subsystem is added (e.g. voice
transcription cleanup) that would double the file size again.

## `backend/dealer_ai/views.py` — ~2,525 LOC
## `backend/dealer_ai/views_f_and_i.py` — ~2,014 LOC

### Why they grew

Function-based views (`@api_view(["POST"])`) rather than DRF
ViewSets, by design. The decision was made at M1 to keep
cross-tenant authorization checks explicit at the view level
rather than hidden behind ViewSet generics. Every endpoint gets
its own function with its own permission checks, its own error
translation, its own serializer call. That is verbose by design.

`views.py` holds the core surface (chat, leads, vehicles,
admin, onboarding, auth, demo — ~40 endpoints). `views_f_and_i.py`
holds the F&I surface (credit app, deal structure, lender,
stipulation, contract, funding, chargeback, compliance —
~35 endpoints).

### Why they have not been split

Splitting either file would be a mechanical rearrangement
without functional benefit. Every view's imports are already
grouped, permission classes are already named, and test files
are organized per-milestone rather than per-view.

### Future split boundary

For `views_f_and_i.py`: split by F&I sub-workflow —
`views_f_and_i_credit_app.py`, `views_f_and_i_deal_structure.py`,
`views_f_and_i_lender.py`, `views_f_and_i_contract.py`,
`views_f_and_i_compliance.py`. Each ~400–500 LOC. The URL
router already groups by prefix so this is a rename-only split.

For `views.py`: split by domain — `views_chat.py`,
`views_leads.py`, `views_admin.py`, `views_onboarding.py`,
`views_demo.py`. Similar shape.

Trigger: any single view file crosses 3,000 LOC.

## `frontend/src/pages/VehicleLedgerPage.tsx` — ~1,059 LOC
## `frontend/src/components/sales/LeadDetailModal.tsx` — ~675 LOC
## `frontend/src/pages/DealerFandIIncoming.tsx` — ~686 LOC

### Why they grew

Each is the surface for a multi-feature workflow that a single
operator does in one session. `VehicleLedgerPage` is the
per-vehicle GL ledger with role-gated write forms (record cost,
add trade-in, mark unavailable) and the read view (all
transactions, running balance). `LeadDetailModal` is the modal
that opens from any lead row and contains assignment,
writeups, chat transcript, follow-up cadence configuration, and
the audit panel — everything a sales manager does with a lead
in one place. `DealerFandIIncoming` is the F&I intake queue
with inline four-square terms, deal-structure launch, lender-
submission recording, and derived status chips.

The alternative — sub-page navigation for each sub-feature —
was rejected explicitly at M11 and M32 planning on the grounds
that operators complete these workflows in one sitting and
context-switching across sub-pages is more expensive than
scrolling through one page.

### Why they have not been split

Splitting any of these would remove the "everything is in one
place" affordance that the operator explicitly benefits from.
Component decomposition inside the file has already been done
(each sub-feature is its own component, imported at the top);
the file is large because it wires them together, not because
it duplicates logic.

### Future split boundary

For each of these, the natural next split is to move the
sub-feature components out of the file itself into a sibling
`components/` folder colocated with the page:

```
pages/VehicleLedgerPage.tsx
components/vehicle-ledger/
  RecordCostForm.tsx
  TradeInSection.tsx
  TransactionTable.tsx
  RunningBalanceCard.tsx
```

The page file itself stays as the wiring layer.

Trigger: any single page component crosses 1,500 LOC.

## Summary

None of these files is a bug. Each was a considered decision
that came out of a specific milestone context. They are large
because the domain is large; the alternative (many small files
with hidden coupling) does not obviously improve reviewability.

If any of them starts actively blocking work — a test file
becomes too slow because it imports the whole module, an
import-order bug creates a hard-to-debug signal issue, or a
reviewer says "I can't find X" — the split boundaries above
are the answer. Until then, the scars stay.
