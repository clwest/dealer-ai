---
title: "Milestone 4 — Implementation-Planning Pass"
status: draft
type: planning-artifact
generated: 2026-08-01
generated_at_session: SESSION_065 (pre-implementation)
milestone: 4
milestone_name: "Recon automation"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_3_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_3_PLANNING.md
  - docs/roadmap/MILESTONE_2_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_2_PLANNING.md
  - docs/BUSINESS_DOMAIN_MAP.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/RECON_MAPPING.md
  - docs/research/VEHICLE_CENTRIC_PIVOT.md
  - docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md
  - docs/research/INVENTORY_ACQUISITION_MAPPING.md
---

# Milestone 4 — Implementation-Planning Pass

**Purpose.** Acceptance contract for Milestone 4 (Recon
Automation). Every implementation increment cites back here for
scope, invariants, and refinement provenance. Mirrors the shape
`MILESTONE_2_PLANNING.md` (SESSION_045) and
`MILESTONE_3_PLANNING.md` (SESSION_055) proved out.

**Business objective (from
`IMPLEMENTATION_ROADMAP.md` §Milestone 4).** Reduce the "chase
vendor for status, chase vendor for invoice, chase parts store
for order" pain by having the AI **draft** the artifacts that
today require manual composition — recon plans, work orders,
vendor emails, purchase orders, work-order narratives — while
humans retain approval and sending authority.

**Zero implementation this session.** Planning artifact only.
SESSION_066 opens M4.1.

---

## 0. Engineering practices to preserve from M2 + M3

Synthesized from `MILESTONE_2_RETROSPECTIVE.md` §6 (six
lessons) and `MILESTONE_3_RETROSPECTIVE.md` §6 (ten lessons).
Carry-forward set for M4:

1. **Increment discipline.** Each M4 sub-increment ships
   independently verifiable in one session. If a proposed
   increment cannot be described in one sentence with one
   locked invariant, it is too large — split. M3.6 A/B split
   is the load-bearing precedent.
2. **Backend-first architecture; frontend never owns business
   rules.** The M4 operator UI is a thin orchestrator around
   an authoritative backend service.
3. **Provider-neutral boundaries.** Vendor-communication
   drafting must not embed provider-specific email / SMS
   SDKs in service code. If M4 introduces outbound send in
   scope, adapters + protocol; if deferred, the surface stays
   provider-neutral for M5+ integration.
4. **Service ownership — one authoritative write path per
   operation.** Every M4 endpoint delegates to a service
   function; no endpoint calls `WorkOrder.objects.create`
   directly. Cross-tenant guards live in the service.
5. **Local vs production parity.** Every M4 external
   dependency (vendor email, SMS, calendar, invoicing) must
   have a local-mode substitute that lets `tests/*.py` +
   `dev` walk the same workflow shape as production.
6. **Honest verification reporting.** When a verification
   cannot be completed (browser walkthrough, real vendor
   send), record it as operator-verification-pending. Do not
   silently tick the box.
7. **Storage-first / safer-direction deletion.** Any M4 delete
   flow that spans DB + external system runs the external
   side first; DB row retained on real failure.
8. **Document implementation refinements immediately.** Every
   reviewed refinement lands in the per-increment SHIPPED
   annotation; the retro synthesizes, does not archaeologize.
9. **Compat patches must be honest.** Latent bugs surfaced by
   dependency updates get fixed with explicit user-visible
   documentation, not silent absorption.
10. **Avoid architectural drift.** Do not generalize into a
    universal framework without a second proven consumer.
    Vendor comms drafted for recon; do not build a "generic
    notification engine" M5 will refactor.

---

## 1. Design memo

**Rule from M3 §1: start with the operational questions, not
the models.** Every entry below answers *what operational
question does this subsystem answer?* first, then *which
primitive does it extend?* and *what does it leave untouched?*

### 1.0 The operational questions Milestone 4 must answer

Fifteen questions synthesized from the research corpus. These
are the acceptance test for whether the milestone shipped the
right thing.

| # | Question | Research citation |
|---|---|---|
| 1 | **Which completed findings will the dealership actually repair?** (three-tier decision: must-do / should-do / won't-do) | `RECON_MAPPING.md` §3.1 |
| 2 | **Who made the recon decision, and when?** — warranty defense on skipped items | `RECON_MAPPING.md` §3.1 + §13.1 |
| 3 | **Is each job performed in-house or outsourced?** | `RECON_MAPPING.md` §4.6 + §5.1 |
| 4 | **Which vendor or employee owns each job?** | `RECON_MAPPING.md` §3.6 + §4.1 |
| 5 | **What parts does the job need, and where do they come from?** | `RECON_MAPPING.md` §3.5 + §6.1–§6.6 |
| 6 | **What parts have been ordered, received, installed, returned, or backordered?** | `RECON_MAPPING.md` §6.6 + §14.3 |
| 7 | **What did we estimate this job would cost?** | `RECON_MAPPING.md` §3.3 + §5.4 |
| 8 | **What did we authorize the vendor to spend?** | `RECON_MAPPING.md` §5.4 |
| 9 | **What was actually invoiced when the work completed?** | `RECON_MAPPING.md` §5.4 |
| 10 | **What was posted against the vehicle's investment ledger?** | Extends M2 `VehicleCost` semantic contract |
| 11 | **What is blocking the work right now?** (waiting parts / waiting vendor / waiting decision) | `RECON_MAPPING.md` §14.1 + §14.3 |
| 12 | **When is the work expected to complete? When did it actually complete?** | `RECON_MAPPING.md` §5.3 + §14.1 |
| 13 | **Was the work verified after completion?** (QC pass; test drive result) | `RECON_MAPPING.md` §7.1–§7.4 |
| 14 | **What was communicated to the vendor?** (email / SMS / phone log) | `RECON_MAPPING.md` §5.6 + §16.5 |
| 15 | **Which statements in that communication came from human-authored data vs. AI-generated wording?** | `RECON_MAPPING.md` §2.6 + §2.7 |

Questions 1-2 belong to the **recon decision** subsystem
(§1.1). Questions 3-5, 7-9 belong to the **work order**
subsystem (§1.2 + §1.3). Question 6 belongs to the **parts
tracking** subsystem (§1.4). Question 10 is the M2 ledger
seam (§1.5). Questions 11-12 belong to the work-order state
machine (§1.6). Question 13 — see §1.0.QC-GAP annotation
immediately below. Questions 14-15 belong to the **vendor
communication** subsystem (§1.7).

#### 1.0.QC-GAP — Q13 renegotiated (SESSION_067)

> **M4 does not answer Q13 "Was the work verified after
> completion?" as originally phrased.** The persistence
> layer stores only `WorkOrder.completed_at` +
> `WorkOrder.completed_by`, which prove *when the work was
> marked complete and by whom*, not *whether it was
> verified*. There is no `qc_verified_at`, no
> `qc_verified_by`, no `qc_notes`, no `test_drive_result`
> field on `WorkOrder`; and the M4 planning scope did not
> introduce a `QcVerification` model. Claiming Q13 is
> answered by completion timestamps would be dishonest
> per M2/M3 retro §6 lesson 6 ("honest verification
> reporting").

**Two paths for Q13.**

- **Path A (recommended, deferred).** Add a `QcVerification`
  model in a future increment (M4.5+ or a scope-refinement
  session before M5). Fields: `work_order` (FK),
  `verified_at`, `verified_by`, `notes`, `test_drive_result`
  (nullable Boolean or three-state), timestamps. Add a
  service function `verify_work_order(work_order, *,
  dealership, verified_by, test_drive_result, notes)` that
  refuses unless `work_order.status == "completed"`. The
  M4 scope stays "recon automation" — QC is a lightweight
  extension, not a redesign.
- **Path B (narrower).** Add `qc_verified_at` +
  `qc_verified_by` + `qc_notes` fields directly to
  `WorkOrder`. Simpler schema, but does not model repeat
  verifications (a re-test after a rework) and conflates
  the recon-execution actor with the QC actor.

**Scope of Path A / B is NOT within M4.2, M4.3, or M4.4.**
Documented here so it does not silently disappear. The
question "which increment adds QC verification?" belongs
in the M4.9 retrospective or the M5 planning pass.

**Narrowed answer M4 does provide for Q13:** M4 records
*when a WorkOrder was marked complete and by whom*, which
is a *precondition* for QC but is not QC itself. Anyone
reading `WorkOrder.completed_at` who assumes it means
"verified" is drawing an unsupported inference from the
data. The M4.2 service layer therefore does not accept a
`qc_verified=True` parameter to `complete_work_order`;
the M4.6 API does not surface a "verified" boolean; the
M4.7 operator UI shows "Marked complete on YYYY-MM-DD by
NAME" without a green-check "verified" icon.

**M4 does answer Q3, Q4, Q7, Q8, Q9, Q11, Q12** at the
work-order subsystem. Q13 is renegotiated per this
annotation.

**Questions Milestone 4 does NOT answer** (deliberate, per
`IMPLEMENTATION_ROADMAP.md` §Milestone 4 scope boundary and
`RECON_MAPPING.md` §16 automation opportunities):

- Q: *Is this vehicle ready for front-line retail?* — Milestone
  5 (lifecycle stages).
- Q: *Which vehicles are stuck at which vendor?* (aging
  dashboard) — Milestone 8 (operational intelligence).
- Q: *What is the historical cost variance per vendor?* —
  M4 records the data; M8 aggregates.
- Q: *Which vendor should we recommend for this job type?*
  (data-driven ranking) — Milestone 8. M4 may draft a
  suggestion from operator-entered preferences but does not
  compute a data-driven ranking.
- Q: *Can we auto-order the parts?* — Explicit out-of-scope
  (§5.a load-bearing decision below).
- Q: *Did the vendor reply to our email?* (inbound processing)
  — Not in M4 scope.
- Q: *What is the salesperson broadcast when the vehicle goes
  front-line?* — Milestone 5 + 6.

### 1.1 Recon decision — `ReconDecision` (one-per-ConditionFinding)

- **Business question answered.** Q1 + Q2.
- **Citation.** `RECON_MAPPING.md` §3.1 three-tier framework;
  §13.1 warranty exposure; §2.6 "AI must never author
  findings" (AI may draft decisions from findings; the human
  approves).
- **Fields (planning shape — final in M4.1).**
  - `finding` (OneToOne to `ConditionFinding` — one decision
    per finding; on_delete=CASCADE).
  - `dealership` (FK NOT NULL from day one; denormalized
    tenancy carrier — same rationale as every M2/M3 model).
  - `tier` (CharField choices: `must_do`, `should_do`,
    `wont_do`).
  - `decided_by` (FK to `AUTH_USER_MODEL`, nullable
    SET_NULL — historical rows survive user deletion).
  - `decided_at` (DateTimeField).
  - `notes` (TextField, blank — free text explaining the
    decision, especially load-bearing for `wont_do` warranty
    defense).
  - Timestamps.
- **Extend.** OneToOne on `ConditionFinding`. Zero changes to
  M3.1 model — the M3 immutability contract stays intact
  (findings can only be edited on `draft` reports; decisions
  can only be recorded on findings whose parent report is
  `complete`).
- **Leave untouched.** No modifications to `ConditionFinding`
  or `ConditionReport`. No re-parenting.
- **Design note — decisions require a completed report.** A
  `ReconDecision` can only be created when
  `finding.report.status == "complete"`. Locked at service
  entry. Rationale: draft reports may have findings that get
  edited or deleted; recording planning decisions against
  those would corrupt the historical truth of what the
  inspector actually saw + what the store actually decided.

### 1.2 Vendor — `Vendor` (many-per-Dealership)

- **Business question answered.** Q4 (vendor identity) +
  supporting infrastructure for Q3, Q8, Q9, Q14.
- **Citation.** `RECON_MAPPING.md` §5.1 vendor categories;
  §5.2 vendor selection criteria; §5.6 vendor relationship
  maintenance.
- **Fields.**
  - `dealership` (FK NOT NULL from day one).
  - `name` (CharField required).
  - `slug` (SlugField unique-per-dealership — for URL
    routing without exposing PK).
  - `categories` (JSONField list of category slugs matching
    `WorkOrder.category` enum — see §1.3. `["mechanical",
    "diagnostic"]` for a mechanic; `["paint", "body"]` for
    a body shop). JSON not FK because vendor categories are
    a small closed set and the coupling to
    `WorkOrder.category` is one-way.
  - `phone` (CharField blank).
  - `email` (EmailField blank).
  - `notes` (TextField blank — operator's own vendor notes:
    "prefers text over email"; "invoices net 15").
  - `is_active` (Boolean default True — the **normal
    removal path**. Operators mark a vendor inactive when
    they stop doing business with them; historical rows keep
    the FK intact). Hard-delete is **prevented at the schema
    layer** by `on_delete=PROTECT` on every FK that points
    at `Vendor` (`WorkOrder.vendor`, `VendorCommunication.vendor`).
    An unreferenced Vendor may be deleted through Django or
    admin only when project conventions permit; a referenced
    Vendor cannot be deleted without first migrating the
    references. Renaming a vendor is allowed and never
    rewrites the `VehicleCost.vendor` snapshot on historical
    rows (see §5.b). — planning refinement adopted
    SESSION_066 before M4.1 implementation.
  - Timestamps.
- **Extend.** No existing primitive to extend — new entity.
- **Leave untouched.** `VehicleCost.vendor` free-text field
  from M2 stays exactly as-is (see §5.b load-bearing vendor
  migration decision below). The name captured at posting
  time is the immutable snapshot; a subsequent vendor rename
  does not rewrite it.

### 1.3 Work order — `WorkOrder` (many-per-Vehicle)

- **Business question answered.** Q3 + Q4 + Q7 + Q8 + Q9 +
  Q11 + Q12. Q13 is renegotiated — see §1.0.QC-GAP above.
  Completion timestamps prove *when work was marked
  complete*, not *whether it was verified*; QC verification
  is not in M4 scope and would require a future
  `QcVerification` model or field addition.
- **Citation.** `RECON_MAPPING.md` §4.2 R.O. flow ("The
  R.O. is the work order — the document that authorizes and
  tracks a specific job on a specific vehicle"). §5 vendor
  categories drive `category` enum.
- **Fields.**
  - `vehicle` (FK on_delete=CASCADE — vehicle removal removes
    orphan work orders; M2/M3 precedent).
  - `dealership` (FK NOT NULL from day one).
  - `category` (CharField choices — same 12 categories as
    `ConditionFinding.category` for direct traceability
    when a work order addresses findings in a single
    category. When a work order addresses multiple
    categories, pick the dominant one — the through-model
    `WorkOrderFinding` records the actual finding→WO
    mapping).
  - `venue` (CharField choices: `in_house`, `outsourced`).
  - `vendor` (FK to `Vendor` nullable
    `on_delete=PROTECT` — required when
    `venue="outsourced"`; NULL for in-house. PROTECT
    prevents hard-deleting a `Vendor` still referenced by a
    historical `WorkOrder`; the normal removal path is
    `Vendor.is_active=False`. Planning refinement adopted
    SESSION_066).
  - `assignee` (FK to `AUTH_USER_MODEL` nullable SET_NULL
    — the in-house tech; NULL for outsourced or unassigned).
  - `status` (CharField choices — see §5.c state machine
    decision below for the enum values).
  - `estimated_cost` (Decimal `max_digits=10, decimal_places=2`
    nullable — the store's projected cost at approval time).
  - `authorized_cost` (Decimal nullable — the ceiling the
    store communicated to the vendor; may differ from
    `estimated_cost` if the vendor asked for a higher cap).
  - `actual_cost` (Decimal nullable — set when work
    completes; drives the auto-mint into `VehicleCost`).
  - `estimated_completion_date` (DateField nullable —
    operator's projected completion; may be vendor-provided).
  - `actual_completion_date` (DateField nullable — set on
    `status="completed"` transition).
  - `notes` (TextField blank).
  - Provenance timestamps + actor FKs (see §1.6 state
    machine): `approved_at`, `approved_by`,
    `started_at`, `started_by`, `completed_at`,
    `completed_by`, `cancelled_at`, `cancelled_by`,
    `cancellation_reason` (TextField blank).
  - Standard timestamps.
- **Extend.** New `condition_findings` reverse relation on
  the through model (§1.4 below); reads
  `latest_condition_report` on `Vehicle` (M3.3) to seed
  work-order creation.
- **Leave untouched.** No `Vehicle` field changes. No
  `ConditionReport` field changes. No `ConditionFinding`
  field changes.

### 1.4 Work-order finding link — `WorkOrderFinding` (through model, many-to-many)

- **Business question answered.** Q1 backwards-traceability
  and Q15 provenance ("which claims in the vendor comm come
  from which finding?").
- **Citation.** `RECON_MAPPING.md` §3.7 combined work
  efficiency; §5.a load-bearing decision below.
- **Fields.**
  - `work_order` (FK on_delete=CASCADE).
  - `finding` (FK on_delete=CASCADE — deletion of a finding
    in draft would remove the link; on complete-parent
    reports the finding is immutable so this is a
    non-issue).
  - `dealership` (FK NOT NULL from day one — denormalized).
  - `created_at`.
  - `Meta.unique_together = ("work_order", "finding")` —
    same finding can only be linked once per work order.
- **Extend.** New relations on `WorkOrder.condition_findings`
  and `ConditionFinding.work_orders` (both accessed via
  through model).
- **Leave untouched.** No `ConditionFinding` field changes;
  the relationship is expressed as the through table.

### 1.5 Work-order part — `WorkOrderPart` (many-per-WorkOrder)

- **Business question answered.** Q5 + Q6.
- **Citation.** `RECON_MAPPING.md` §3.5 parts pre-ordering;
  §6.1–§6.6 parts sourcing (OEM vs aftermarket; local vs
  online; special-order + back-order handling). §5.d
  load-bearing decision below limits scope to **operational
  tracking only** — no marketplace, no auto-order, no
  payment.
- **Fields.**
  - `work_order` (FK on_delete=CASCADE).
  - `dealership` (FK NOT NULL from day one).
  - `name` (CharField required — human-readable, e.g.
    "Front brake pads, driver side").
  - `part_number` (CharField blank — OEM or aftermarket
    part number when known).
  - `description` (TextField blank).
  - `quantity` (PositiveIntegerField default 1).
  - `unit_cost` (Decimal `max_digits=10, decimal_places=2`
    nullable — the store's cost per unit).
  - `source_type` (CharField choices: `oem_dealer`,
    `local_parts`, `online`, `salvage`, `in_stock`,
    `other` — per RECON §6.1 + §6.2).
  - `source_name` (CharField blank — vendor / store name,
    e.g. "NAPA Yuma"; free text — no `Vendor` FK because
    parts vendors are a different population from recon
    vendors).
  - `status` (CharField choices: `needed`, `ordered`,
    `backordered`, `received`, `installed`, `returned`).
  - `ordered_at` / `received_at` / `installed_at` /
    `returned_at` (DateFields nullable — set on status
    transitions).
  - `notes` (TextField blank).
  - Timestamps.
- **Extend.** New relation on
  `WorkOrder.parts`.
- **Leave untouched.** Nothing.

### 1.6 Vendor communication — `VendorCommunication` (many-per-WorkOrder, many-per-Vendor)

- **Business question answered.** Q14 + Q15.
- **Citation.** `RECON_MAPPING.md` §5.6 vendor relationship
  maintenance; §14.7 chasing vendors for status; §14.8
  chasing vendors for invoices; §16.5 vendor communication
  drafting.
- **Fields.**
  - `dealership` (FK NOT NULL).
  - `vendor` (FK on_delete=**PROTECT** nullable — a
    referenced `Vendor` cannot be hard-deleted; the normal
    removal path is `Vendor.is_active=False`. NULL is
    permitted only when the row was authored before a
    `Vendor` was chosen (e.g. an inbound phone message
    logged against a work-order before the vendor is
    identified). Planning refinement adopted SESSION_066).
  - `work_order` (FK on_delete=SET_NULL nullable — comms
    can precede assignment).
  - `channel` (CharField choices: `email`, `sms`, `phone`,
    `in_person`).
  - `direction` (CharField choices: `outbound`, `inbound`).
  - `kind` (CharField choices: `assignment`,
    `status_check`, `invoice_question`, `general_note`).
  - `draft_content` (TextField — the AI-drafted or
    operator-typed content; the durable draft record).
  - `sent_content` (TextField blank — set only when
    `status="sent"`; captures any operator edits applied
    before send).
  - `status` (CharField choices: `draft`, `approved`,
    `sent`, `logged`, `failed` — `logged` = the
    operator sent the message outside the system (phone /
    in-person) and is recording it after the fact).
  - `drafted_by` (FK to AUTH_USER_MODEL nullable SET_NULL).
  - `approved_by` (FK nullable SET_NULL — who clicked
    Approve).
  - `sent_by` (FK nullable SET_NULL — who clicked Send /
    who logged the phone call).
  - `drafted_at` / `approved_at` / `sent_at` (DateTimeFields
    nullable).
  - `source_provenance` (JSONField default dict — records
    which sentences came from which structured source per
    §5.g AI-boundary decision below).
  - `notes` (TextField blank).
  - Timestamps.
- **Extend.** New relations on `WorkOrder.communications`
  and `Vendor.communications`.
- **Leave untouched.** Nothing.

#### 1.6.SHIPPED — enum reconciliation (SESSION_067)

Three enum vocabularies shipped in M4.1 diverged from the
draft §1.6 field-shape list above. The divergences are
intentional and are recorded here as an M4.1 **reviewed
refinement** rather than silent drift. Each divergence is
justified below.

**Kind — shipped `(vendor_comm, parts_order, narrative)`.**
Draft §1.6 proposed `(assignment, status_check,
invoice_question, general_note)`. The shipped set is a
smaller, durable *classification of communication role*
rather than a per-message *intent taxonomy*:

- `vendor_comm` — any outbound-drafted communication with a
  vendor about a work order (the AI-drafted path — email /
  SMS / phone talking-points). Covers the intent originally
  named by `assignment`, `status_check`, and
  `invoice_question`: those are all *purposes* the operator
  states in `notes` or the AI derives from source-bundle
  fields, not a schema-level partition. Trying to force
  intent into an enum would require the operator to disambiguate
  three near-adjacent categories on every draft (does
  "hey Bob, are these parts here yet?" get logged as
  `status_check` or `invoice_question` if the reply might
  include a bill?). A one-way `vendor_comm` classification
  keeps the schema honest and pushes intent into the
  content, where language actually captures it.
- `parts_order` — communication whose *content* is a parts
  order (an explicit purchase request). Distinct from
  `vendor_comm` because §5.h vs §5.g routes the M4.5 scrub
  slightly differently (parts orders reference
  `WorkOrderPart` rows; recon comms reference findings +
  authorized cost).
- `narrative` — operator-authored internal note or off-system
  communication record (phone call notes, in-person
  conversation summaries, inbound-email transcriptions).
  This is the durable home for the `general_note` intent
  from the draft.

**Where the draft `assignment / status_check /
invoice_question / general_note` intents live in the shipped
schema.** They are not lost; they are represented by other
existing fields:

- Content itself (`draft_content` / `sent_content`) —
  human-language intent lives in the words. "Hey Bob, can
  you take a look at the F-150" is an assignment;
  "just checking in on the ETA" is a status check.
- `direction` (`outbound` / `inbound`) — status-check
  responses and invoice-question responses often come back
  as `direction='inbound'`.
- `channel` (see below) — phone / in-person /
  internal_note distinguish off-system status conversations
  from in-system drafts.
- Optional future addition — if operational data reveals
  that recon-manager dashboards genuinely need to slice
  by intent (e.g., "how many status-check comms did we
  send this week?"), the enum can be extended additively
  in M8 (operational intelligence) without breaking
  existing rows.

**Channel — shipped adds `internal_note` (5 values instead
of 4).** Draft §1.6 listed `(email, sms, phone, in_person)`.
`internal_note` is a genuine channel — a note the operator
records against a work order that is NOT a communication to
the vendor at all ("Bob mentioned in passing they're
short-staffed this week; may impact ETA"). Recording it as
`channel='internal_note'` with `direction='outbound'`
(operator-authored, staying internal) preserves the
distinction between "sent to vendor" and "recorded for
future recon-manager reference" without inventing a
separate model. **`internal_note` is a channel, not a
kind**, because it applies to any of the three kinds:
narrative internal notes are the common case; but an
operator may also record an internal note that is *about* a
vendor_comm or parts_order that already went out via a
different channel.

**Status — shipped 4 values `(draft, approved, sent, logged)`;
draft included `failed`.** `failed` was removed because M4
v1 has no live send path — every outbound goes out via
operator copy-paste from the draft UI (per §5.i deployment
decision). A `failed` status without a live send code path
is a false affordance. When outbound delivery is introduced
in the post-M4 prod-readiness pass (per §5.j), the future
locations for provider-send failure are:

- **Option A (recommended).** Add `failed` back as a fifth
  enum value at the time send is wired. The transition
  matrix acquires `approved → failed` and possibly
  `failed → approved` (retry) or `failed → cancelled`.
- **Option B.** Introduce a sibling model
  `VendorCommunicationSendAttempt` that records each attempt
  with its own status enum, preserving the fact that a
  single communication may have multiple send attempts with
  different providers.

The choice between A and B belongs to whoever picks up the
prod-send scope. It is explicitly out of M4.1 – M4.6.

**No research-cited operational question loses answerability
under the shipped enums.** Q14 ("what was communicated to
the vendor?") and Q15 ("which claims came from human data
vs. AI wording?") remain answerable via `draft_content` +
`sent_content` + `source_provenance`. The Q11 question
"what is blocking the work right now?" (waiting parts /
waiting vendor / waiting decision) is answered by
`WorkOrderPart.status` aggregates + `WorkOrder.status`, not
by comm kind. Enum reconciliation preserves the shipped
schema; no persistence-contract correction is required.

### 1.7 Vehicle read-model extension

- **Business question answered.** Q11 aggregated at the
  vehicle level ("what work is open on this vehicle right
  now?").
- **Citation.** M3.3 established the Vehicle-as-read-model
  pattern (`MILESTONE_3_PLANNING.md` §1.3).
- **Shape.** Two additional `@property` accessors on
  `Vehicle`, delegating to the recon service:
  - `open_work_orders` — returns a queryset of `WorkOrder`
    rows where `status not in ("completed", "cancelled")`.
  - `has_recon_decisions` — returns `True` if
    `.latest_completed_condition_report` exists and has at
    least one `ReconDecision` attached to a finding.
- **What M4 does NOT add.** No `has_open_recon` boolean, no
  `days_in_recon` temporal metric, no `recon_bottleneck`
  computed status. Those are M8 (operational intelligence)
  concerns. M4 exposes the raw data; M8 aggregates.

### 1.8 What Milestone 4 enables for future milestones

- **Milestone 5 (Lifecycle stages)** reads
  `WorkOrder.status="completed"` for all `must_do` /
  `safety` findings as one input to the "front-line ready"
  gate. M5 owns the *decision*; M4 owns the *data*.
- **Milestone 6 (Photography)** reads work-order completion
  status to know when a vehicle is detail-complete and
  photo-ready.
- **Milestone 7 (Async infrastructure)** picks up vendor SLA
  warnings, ETA drift alerts, and estimate-vs-actual
  aggregations — all read from the M4 data shape.
- **Milestone 8 (Operational intelligence)** aggregates M4
  data: vendor performance dashboards, cost-variance per
  category, aging by stage, bottleneck detection. M4 is the
  data-generation layer; M8 is the analytics layer.
- **Milestone 11+ (Sale + delivery)** attaches
  work-order + vendor-invoice records to the deal jacket as
  provenance for post-sale warranty defense (per RECON
  §13.1).

---

## 2. Migration impact review

Every existing surface Milestone 4 touches, with the concrete
work required. Same shape as `MILESTONE_2_PLANNING.md` §2 and
`MILESTONE_3_PLANNING.md` §2.

| # | Existing surface | Location | M4 impact | Required work |
|---|---|---|---|---|
| 1 | `Vehicle` model | `dealer_ai/models.py::Vehicle` | **Additive relationships only.** New reverse `work_orders` (FK from `WorkOrder`). Two new `@property` accessors on `Vehicle` in M4.2 (`open_work_orders`, `has_recon_decisions`) — delegates to service, no field changes. | None on `Vehicle` itself. Service layer in M4.2. Property additions in M4.2 (bundled with the service that reads them). |
| 2 | `ConditionReport` / `ConditionFinding` / `ConditionFindingPhoto` | `dealer_ai/models.py` | **Zero field changes.** M3 immutability contract preserved. New reverse `recon_decision` OneToOne on `ConditionFinding` (from `ReconDecision`). New reverse `work_orders` M:N on `ConditionFinding` (via `WorkOrderFinding` through table). | None on the M3 models. |
| 3 | `services/condition_report.py` | Existing M3.2/M3.5 service | **Zero signature changes.** M4's recon service reads `ConditionReport.status="complete"` + `Vehicle.latest_completed_condition_report` — no new calls into `condition_report.py`. | None. Recon service imports M3 models directly but never mutates them. |
| 4 | `services/tenancy.py` | `_TENANT_CARRIER_MODEL_NAMES` | **Additive.** Six new tenant carriers (`Vendor`, `ReconDecision`, `WorkOrder`, `WorkOrderFinding`, `WorkOrderPart`, `VendorCommunication`) register with the `pre_save` autofill signal. | Extend `_TENANT_CARRIER_MODEL_NAMES` tuple in M4.1 (six new entries — 9 → 15). Test coverage extends existing `WritePathFallback.*` matrix. |
| 5 | `dealer_ai/permissions.py` | Existing role classes | **Additive — new permission class.** `IsReconManagerSalesManagerOrOwnerAtActiveDealership` composed for M4 admin surfaces. `recon_manager` role constant already exists (`ROLE_RECON_MANAGER` — M1 · 4A shipped it); M4 adds the permission class that composes it with `sales_manager` + `dealer_owner`. Per-endpoint least-privilege matrix in §5.f below. | New permission class + focused tests. Zero changes to existing classes. |
| 6 | `services/llm_safety.py` | `apply_post_llm_scrubs` | **Additive — one new post-LLM scrub.** New `_scrub_invented_recon_fact` runs on `kind="vendor_comm"` — rejects vendor comms that reference findings, part numbers, quotes, appointments, or completion dates NOT present in the drafted-from source. Mirrors M2.5 `_scrub_acquisition_price` shape. See §5.g. | New scrub function + focused tests. Zero changes to existing scrubs. |
| 7 | `services/vehicle_ledger.py` | `add_cost` service function | **Zero signature change; M4 becomes a new caller.** M4.3 estimate-to-ledger contract calls `add_cost` on work-order approval (`is_estimate=True`) and completion (`is_estimate=False`). Never calls `VehicleCost.objects.create` directly. | None on `vehicle_ledger.py`. M4.3 service module wraps `add_cost` with idempotency (`reference="WORKORDER:<id>:estimate"` and `:actual`). |
| 8 | Customer-facing chat surfaces | `services/chat_engine.py`, `views.py::chat_start` / `chat_message` / `vehicle_ask` | **Zero impact.** Recon / vendor / work-order data never enters customer chat context. Vendor names, invoice amounts, part costs — all internal. Same discipline as M2 ledger + M3 condition-report. | None. |
| 9 | Public branding endpoints | `views.py::onboarding_profile` (GET), `views.py::salespeople_list` (public) | **Zero impact.** No change to any public-facing endpoint. | None. |
| 10 | Django admin | `admin.py` | **Additive.** Six new admin registrations mirroring M3.1 admin shape. | Ship in M4.1 alongside the models. |
| 11 | `settings.py` | `dealer_kit/settings.py` | **Additive iff M4 includes outbound send.** If M4.6 ships vendor-email send in scope (see §5.i deployment decision), add `EMAIL_*` env vars. If M4 defers send (v1: operator copy-paste from draft UI), zero settings change. | Decision locked in §5.i — likely deferred to a post-M4 pilot. |
| 12 | `requirements.txt` | `backend/requirements.txt` | **Additive iff M4 includes outbound send.** If send in scope, add SMTP-safe library (`django.core.mail` is sufficient — no new dependency). If not, zero change. | Same as row 11. |
| 13 | Frontend `main.tsx` (route registration) | `frontend/src/main.tsx` | **Additive.** Register `/dealer-ai-inventory/:stock/recon` (or similar) inside `<RequireAuth>`. Sits alongside M2.7 ledger + M3.7 condition-report routes. | Ship in M4.7. |
| 14 | Frontend `lib/api.ts` | `frontend/src/lib/api.ts` | **Additive.** New typed helpers for M4 admin endpoints. All via `authFetch`. Zero change to existing helpers. | Ship in M4.7. |
| 15 | Frontend `pages/` | `frontend/src/pages/` | **Additive.** New `VehicleReconPage.tsx` + small extracted components (per M3.7 discipline). | Ship in M4.7. |
| 16 | Operator inventory card | Wherever M2.7 "Ledger" + M3.7 "Condition Report" buttons live. | **Additive.** New "Recon" button, URL-encoded stock, next to existing operator buttons. NOT surfaced on public `/showroom`. | Ship in M4.7. |
| 17 | `services/dealer_config.py` | `services/dealer_config.py` | **Zero impact.** No new dealer config field for M4 v1. If prod deployment lands (§5.i), operator email address for vendor comms may live here — or on `Vendor.our_reply_to_email`. Decide at implementation time. | None v1. |
| 18 | M2 ledger substrate | `services/vehicle_ledger.py`, `models::VehicleCost`, `views.py::admin_vehicle_ledger` etc., `pages/VehicleLedgerPage.tsx` | **Zero impact on write path** to `VehicleCost.vendor` free-text field. M4 posts new `VehicleCost` rows via `add_cost` service call with `vendor=vendor.name` (snapshot). Historical M2 rows unchanged. See §5.b. | None. |
| 19 | M3 substrate (models, service, storage, admin API, UI) | All | **Zero impact.** M4 reads M3 data but never mutates M3 rows. M3.6A/B endpoint permissions unchanged. M3.7 operator UI unchanged. Photo storage abstraction unchanged. | None. |
| 20 | `Vehicle.is_available` | `models.py::Vehicle` | **Zero impact.** No change to `is_available`. Milestone 5 refactors to computed lifecycle. | None. |
| 21 | Prod deployment | Render Blueprint | **Deferred per §5.i.** M4 recon is still in-store workflow (RECON §12.2 sign-off at store); AI-drafted vendor emails can ship in-UI without live SMTP. First-live-prod deployment coincides with a real pilot store engagement — likely between M4 and M5, but explicitly not gated by M4.8 closeout. | None in M4 v1. Documented as separate pre-pilot readiness pass. |
| 22 | Test infrastructure | `dealer_ai/tests/*.py` | **Additive.** M4 tests use existing test helpers (`_auth_helpers.py`, `_tenancy_helpers.py`). No new fixture framework. | Ship inside each M4 increment. |

---

## 3. Compatibility checklist

**Milestone 4 ships with this checklist verified true; evidence
recorded inline at milestone close.** Original invariants
preserved from M1 + M2 + M3; each row cites the test class,
code location, or runtime probe that locks it. Mirrors the
shape M2.8 / M3.8 established.

### Milestone 1 + 2 + 3 invariants Milestone 4 must not regress

Tenancy substrate:
- [ ] `Dealership` model + migration `0007` unchanged.
- [ ] Every existing tenant-carrying model still has
  `dealership` FK NOT NULL.
- [ ] `services/tenancy.py::get_default_dealership` /
  `get_current_dealership` / `get_active_membership`
  unchanged in signature and contract.
- [ ] M4 tenant carriers (`Vendor`, `ReconDecision`,
  `WorkOrder`, `WorkOrderFinding`, `WorkOrderPart`,
  `VendorCommunication`) register with the `pre_save`
  autofill signal.
- [ ] Every new M4 tenant-carrying model has `dealership` FK
  NOT NULL from day one.

Identity + authentication:
- [ ] `DEFAULT_PERMISSION_CLASSES` remains **unset**.
- [ ] `SessionAuthentication` + `TokenAuthentication` still
  installed.
- [ ] `/auth/{login,logout,me}` endpoints unchanged.
- [ ] CSRF still enforced on authenticated mutations.

M1 · 4D + M2.6 + M3.6 permissions:
- [ ] M2.6 admin ledger endpoints still authorized by
  `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`.
- [ ] M3.6A/B admin endpoints still authorized by the same
  class.
- [ ] Cross-tenant pk lookups on all admin endpoints still
  fail closed (404).

Customer-facing surfaces:
- [ ] Public branding renders unauthenticated.
- [ ] Customer chat unchanged.
- [ ] Per-vehicle Q&A unchanged.
- [ ] No recon / vendor / work-order data appears in any
  customer-facing surface response body.

Safety stack (the moat):
- [ ] All 8 pre-LLM guards fire in existing order.
- [ ] All post-LLM scrubs (including M2.5 acquisition_price)
  unchanged in behavior.
- [ ] Every dollar figure in customer chat still comes from
  `services/payment_engine.py`.

M2 ledger substrate:
- [ ] `services/vehicle_ledger.py` API unchanged in signature.
- [ ] `Vehicle.ledger_totals` + delegators unchanged.
- [ ] `VehicleCost` immutability unchanged.
- [ ] `total_investment` semantic contract (excludes
  estimates) unchanged.
- [ ] `VehicleCost.vendor` free-text field unchanged (M2
  data readable regardless of M4 `Vendor` entity — see §5.b).

M3 substrate:
- [ ] `services/condition_report.py` API unchanged.
- [ ] `Vehicle.latest_condition_report` / `latest_completed_condition_report`
  unchanged.
- [ ] `services/photo_storage.py` API unchanged.
- [ ] Completed condition reports remain immutable
  (`ConditionReportImmutableError`).
- [ ] `ConditionFinding.estimated_cost` still documentation-
  only; the M3 invariant "never touches VehicleCost" is
  preserved by the M4 `add_cost` calls being triggered by
  work-order approval, NOT by finding creation.
- [ ] M3.6A/B admin API + M3.7 operator UI unchanged.

Dealer identity resolution:
- [ ] `get_dealer_name()` + `get_dealer_profile()` +
  `get_floor_plan_apr()` still resolve DB → env → default.

Frontend contracts:
- [ ] `useBrand()` + `useDealerProfile()` still resolve
  unauthenticated.
- [ ] `brand.*` Tailwind tokens unchanged.
- [ ] `authFetch` / `AuthContext` / `RequireAuth` / `LoginPage`
  unchanged in contract.
- [ ] `npx tsc --noEmit` clean.
- [ ] `npx vite build` clean.

Test baseline:
- [ ] `python3 manage.py test dealer_ai` → **2,124 pass** or
  greater; 1 skipped, 0 fail.
- [ ] No test suppressed with `@skip` to make the baseline
  pass.

### New invariants Milestone 4 introduces

Model-layer:
- [ ] Every M4 model row has `dealership` FK NOT NULL matching
  its parent Vehicle's tenant (cross-tenant `clean()` guards
  same shape as M2/M3).
- [ ] `ReconDecision.tier` validated at model layer via
  `choices=` (three values: `must_do`, `should_do`,
  `wont_do`).
- [ ] `WorkOrder.status` validated at model layer via
  `choices=` (see §5.c state machine).
- [ ] `WorkOrder.category` restricted to the same 12
  canonical values as `ConditionFinding.category`
  (imported from `CONDITION_CATEGORY_CHOICES` — single
  source of truth).
- [ ] `WorkOrder.venue == "outsourced"` implies
  `vendor IS NOT NULL` (model `clean()` guard).
- [ ] `Vendor.slug` unique-per-dealership.
- [ ] `WorkOrderFinding` unique-together on
  (`work_order`, `finding`).
- [ ] `WorkOrderPart.status` validated at model layer via
  `choices=` (six values).
- [ ] `VendorCommunication.status` validated at model layer
  via `choices=` (five values).
- [ ] `VendorCommunication.status="sent"` implies
  `sent_content IS NOT NULL` (model `clean()` guard).
- [ ] `WorkOrder.vendor` uses `on_delete=PROTECT`; hard
  deletion of a referenced `Vendor` raises `ProtectedError`
  at the DB layer (planning refinement SESSION_066).
- [ ] `VendorCommunication.vendor` uses `on_delete=PROTECT`;
  same semantics as above.
- [ ] `VendorCommunication` `sent`-state structural
  requirements: `approved_by`, `sent_by`, `sent_at`, and
  nonblank `sent_content` all required.
- [ ] `VendorCommunication` `approved`-state structural
  requirements: `approved_by` and `approved_at` required
  (no `sent_by` / `sent_content` required at this state).
- [ ] `VendorCommunication` `logged`-state structural
  requirements: human actor (`sent_by`) and timestamp
  (`sent_at`) plus nonblank `sent_content` (the recorded
  body) required; `approved_by` / `approved_at` NOT
  required (planning refinement SESSION_066 — separates
  operator-recorded phone / inbound / in-person comms
  from the AI-drafted `draft → approved → sent` workflow).
- [ ] AI-drafted `VendorCommunication` rows (any row
  populated via `services/vendor_comm.py::draft_communication`)
  may never transition directly to `logged`; the invariant
  is enforced at the M4.5 service layer, not at model
  layer (a persistence-only guard cannot distinguish
  AI-drafted from operator-recorded rows).

Business-layer:
- [ ] `services/recon.py::record_decision(finding, *,
  dealership, tier, decided_by, notes)` refuses cross-tenant
  writes at entry (new `CrossTenantReconError`).
- [ ] `record_decision` refuses when
  `finding.report.status != "complete"` (analog to M3.2
  `_refresh_and_assert_draft` but reversed — decisions can
  only be made after report completion).
- [ ] `create_work_order(vehicle, *, dealership, category,
  venue, ...)` refuses cross-tenant.
- [ ] `approve_work_order(work_order, *, dealership,
  approved_by, ...)` refuses cross-tenant + only allowed
  from `draft`.
- [ ] `start_work_order(...)` only from `approved` (or
  `approved` → `in_progress` transition per §5.c).
- [ ] `complete_work_order(...)` only from `in_progress` or
  `approved` (per state machine); sets `actual_completion_date`,
  `actual_cost`, `completed_by`, `completed_at`
  atomically; posts actual `VehicleCost` via `add_cost` with
  reference `WORKORDER:<id>:actual`.
- [ ] `cancel_work_order(...)` posts reversing `VehicleCost`
  row for any `is_estimate=True` row previously posted
  (idempotent via reference tag).
- [ ] No M4 service function ever posts a `VehicleCost` row
  directly — all posts through `services.vehicle_ledger.add_cost`.
- [ ] No M4 service function ever creates a
  `ConditionFinding` or `ConditionReport` row — the M3.1
  invariant "AI is never allowed to author findings"
  (RECON §2.6) extends to the M4 backend.

Endpoint-layer:
- [ ] Every new M4 admin endpoint composes the new
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  class (or the stricter M1 · 4D class for endpoints that
  are dealer-owner-only per §5.f matrix).
- [ ] Every new endpoint calls
  `dealership = get_current_dealership(request)` once at
  top.
- [ ] Every new endpoint's queryset carries explicit
  `.filter(dealership=dealership)`.
- [ ] Cross-tenant `stock_number` / `work_order_id` /
  `finding_id` / `vendor_slug` / `comm_id` lookups fail
  closed (404).
- [ ] Full permission matrix locked per endpoint (unauth,
  no-role, advisor-only, porter-only, recon_manager,
  sales_manager, dealer_owner).

AI + safety-layer:
- [ ] New scrub `_scrub_invented_recon_fact` fires on
  `kind="vendor_comm"` and rejects mentions of finding IDs
  / part numbers / quote amounts / dates that don't appear
  in the structured source data attached to the draft.
- [ ] Existing scrubs (all 8 pre-LLM + all post-LLM) fire
  unchanged.
- [ ] Every `VendorCommunication` row records
  `source_provenance` naming the M3 findings / M4
  work-order data / operator-entered facts that supported
  each factual claim.
- [ ] No `VendorCommunication` row transitions to `sent` or
  `logged` without an explicit human `approved_by` +
  `sent_by` field set — server-side invariant, locked by
  service tests.
- [ ] AI-drafted content never includes findings that the
  operator did not attach to the work order.

Ledger integration:
- [ ] Reference tag on auto-minted VehicleCost rows follows
  one of the five families locked in §5.e:
  `WORKORDER:<id>:estimate:<seq>`,
  `WORKORDER:<id>:estimate_reversal:<seq>`,
  `WORKORDER:<id>:completion_estimate_reversal`,
  `WORKORDER:<id>:estimate_reversal:cancel`,
  `WORKORDER:<id>:actual`.
- [ ] `add_cost` idempotency check: before posting, the M4
  service verifies no existing row with the target
  reference tag exists (skip if it does — logged as
  duplicate-suppressed).
- [ ] `WorkOrder` completion posts an actual **and** a
  matching estimate reversal atomically (single DB
  transaction) using the
  `completion_estimate_reversal` one-shot reference
  (planning refinement SESSION_066).
- [ ] `WorkOrder` cancellation posts a reversing entry
  (negative amount, reference
  `WORKORDER:<id>:estimate_reversal:cancel`); never edits
  or deletes the original row (M2 immutable-cost invariant
  preserved).
- [ ] After a WO reaches a terminal state, the net
  estimate contribution for that WO in the ledger is
  `Decimal("0.00")` — original estimate(s) + revisions +
  reversals sum to zero (locked by M4.3 test).
- [ ] After WO completion, `projected_total_investment`
  does not double-count the completed WO — locked by
  M4.3 test that computes projected before + after
  completion and asserts the delta equals actual − last
  outstanding estimate.
- [ ] The M3 finding.estimated_cost invariant remains:
  three tests still pass unchanged (model layer, service
  layer, condition-report endpoint layer). M4 posts happen
  from work-order transitions, NOT from finding creation.
- [ ] `total_investment` still excludes estimates.

Frontend:
- [ ] Recon page is inside `<RequireAuth>`.
- [ ] Recon page fetch calls use `authFetch`.
- [ ] Anonymous navigation redirects to `/login?next=…`.
- [ ] No recon / vendor / work-order figure appears in any
  customer-facing surface.
- [ ] "Recon" button on operator inventory cards but NOT on
  public `/showroom`.
- [ ] Draft-vs-approved vs sent UI states are visually
  distinct (not merely disabled) — same discipline as
  M3.7's `CompletionBanner`.
- [ ] Vendor-communication draft edit affordances gated on
  role (`sales_manager` / `dealer_owner` / `recon_manager`).

---

## 4. Reusable primitives review

Primitives from `IMPLEMENTATION_ROADMAP.md` §3 cited by
Milestone 4. All should be **extended or directly reused**,
not paralleled.

### §3.1 LLM safety stack — `services/llm_safety.py`

- **Current shape.** `apply_post_llm_scrubs(text, *, kind) ->
  (cleaned_text, scrubs_fired, dropped_reason)`. Extended in
  M2.5 with `_scrub_acquisition_price`.
- **M4 extension.** Adds `_scrub_invented_recon_fact` firing
  on `kind="vendor_comm"`. Mirrors M2.5 shape (part of the
  always-runs section after `detect_unsafe_response`).
  Text-only, zero DB. Regex patterns anchored on invented-
  fact signals: finding IDs not in source; part numbers not
  in source; dollar figures not matching structured
  authorized_cost; dates outside authorized-schedule range.
- **New `kind` value.** `"vendor_comm"` — added to the kind
  enum. Existing kinds unchanged.

### §3.3 Ad-copy / follow-up drafting patterns

- **Reused directly.** `services/ad_copy.py` +
  `services/follow_up.py` established the "AI drafts N
  variants; safety stack scrubs; operator picks + edits"
  pattern. M4 vendor-communication drafting follows the same
  three-step shape: (1) call LLM with structured source
  data; (2) run through post-LLM scrubs including new
  `invented_recon_fact`; (3) persist as `VendorCommunication`
  with `status="draft"` for operator review.

### §3.4 Handoff-packet builder

- **Pattern reused.** The M1 handoff-packet builder shape
  (structured facts → text draft → operator approval) maps
  directly to the M4 vendor-communication draft flow.

### §3.5 Vehicle model + inventory identity

- **Reused unchanged.** `WorkOrder.vehicle` FK; new
  `Vehicle.open_work_orders` / `has_recon_decisions`
  `@property` accessors mirror M2.3 / M3.3 pattern.

### §3.9 Dealer identity resolver — `services/dealer_config.py`

- **Reused unchanged.** No new dealer-config field for M4
  v1. If prod send lands, operator reply-to email may live
  here — decide at implementation time.

### Directly reused (no extension) — `services/tenancy.py`

- `_TENANT_CARRIER_MODEL_NAMES` extended 9 → 15 in M4.1
  (add six carriers). Handler shape unchanged.
- `get_current_dealership(request)` unchanged.
- Every M4 endpoint uses this resolver + explicit
  `dealership=` threading, same as M3.6.

### Directly reused (no extension) — `dealer_ai/permissions.py`

- `IsSalesManagerOrOwnerAtActiveDealership` still used on
  the ledger endpoints (M2.6).
- New permission class in M4.7 adds recon_manager to the
  mix for M4 endpoints. Existing classes untouched.

### Directly reused (no extension) — M2 ledger service

- `services.vehicle_ledger.add_cost(vehicle, *,
  dealership, category, amount, incurred_at, ...,
  is_estimate=False, created_by=None)` — M4 calls this on
  work-order approve (`is_estimate=True`), on
  complete (`is_estimate=False`), and on cancel
  (reversing entry, negative amount). Never bypasses to
  `VehicleCost.objects.create`.
- `services.vehicle_ledger.CrossTenantLedgerError` — M4
  services catch this as a lower-level error and
  re-raise as `CrossTenantReconError` for stable API
  contract. (Same shape as how M3.5 wrapped storage errors.)

### Directly reused (no extension) — M3 condition-report service

- `services.condition_report.latest_completed_condition_report(vehicle,
  *, dealership)` — M4.2 recon service reads this to
  populate the finding list when the operator opens the
  recon page for a vehicle.
- `services.condition_report.CrossTenantConditionReportError` —
  M4 catches this at recon-service entry (should be
  impossible if tenancy is threaded correctly, but
  defense-in-depth).
- M3 model layer imports — `ConditionFinding` (for FK) +
  `ConditionReport` (for read-only status check).

### Directly reused (no extension) — M3 photo storage service

- `services.photo_storage` is **NOT** extended by M4. Vendor
  comms are text; parts tracking has no photos in v1.
  Future milestone (M6 photography? M8 warranty defense?)
  may attach post-recon or vendor-invoice photos.

### Genuinely greenfield in Milestone 4

- **`services/recon.py`** — new service module (design in
  M4.2). Owns: `ReconDecision` writes, `WorkOrder` writes +
  state transitions, `WorkOrderPart` writes,
  `VendorCommunication` writes (except AI drafting which
  lives in a new `services/vendor_comm.py`).
- **`services/vendor_comm.py`** — new module (M4.5). Owns:
  LLM-drafted vendor communication with `invented_recon_fact`
  scrub integration, `source_provenance` recording.
- **New Django admin registrations** for six models (M4.1).
- **`Vendor` slug pattern** — new SlugField validation +
  unique-per-dealership constraint.
- **The invented-recon-fact scrub** — extends the M2.5 shape
  but is genuinely new content (different regex corpus,
  different `kind` value).

---

## 5. Scope discipline + deferrals

### 5.a Load-bearing decision — Recon Plan vs. Work Order

**Question.** Does M4 require both a `ReconPlan` container
entity representing dealership decisions across findings AND
individual `WorkOrder` records representing execution
assignments? Or can one entity truthfully serve both?

**Options.**

- **Option A.** Two entities: `ReconPlan` (per-vehicle
  planning container, holds decisions + total cost cap) +
  `WorkOrder` (per-job execution record). `ReconPlanItem`
  links them.
- **Option B.** One entity: `WorkOrder` (per-job); the
  three-tier decision lives on `ReconDecision` (per-finding).
  There is no separate "plan" container — the plan is
  emergent from the collection of decisions + work orders
  attached to a vehicle at a point in time.
- **Option C.** One entity: `WorkOrder` with a
  `is_planning_only=True` flag for jobs in the "should-do"
  bucket that haven't been approved yet.

**Chosen: Option B.**

**Why.** RECON §3.1 describes recon planning as a *decision
process* the recon manager runs across findings, not a
container document. The three-tier framework (must / should /
won't) is per-finding. Once the "must-do" list is decided,
work orders get created for each; the "won't-do" list produces
`ReconDecision(tier="wont_do")` rows with no work orders. A
separate `ReconPlan` container would either duplicate this
decision data or become a stale snapshot. Independent-dealer
workflow (RECON §3.7: "the recon calendar is often kept in
someone's head at smaller stores") doesn't have a plan
document that needs to be edited as a first-class object; the
plan is emergent.

**Relationship.** `ConditionFinding` → `ReconDecision` (one
decision per finding, three-tier) → optional `WorkOrder(s)`
via `WorkOrderFinding` through table → `WorkOrder` completion
→ `VehicleCost` via `add_cost`.

**Traceability.** Every `WorkOrder` links back to the
finding(s) it addresses via `WorkOrderFinding`; every
`ConditionFinding` reveals whether it has a decision + which
work orders address it. No standalone "plan" document exists
or is needed.

### 5.b Load-bearing decision — Vendor entity migration strategy

**Question.** The M2 `VehicleCost.vendor` field is a
free-text CharField shipped at SESSION_048. M4 introduces a
`Vendor` model. How does the migration work without breaking
existing historical rows or the M2 semantic contract?

**Options.**

- **Option A.** Replace `VehicleCost.vendor` with a
  nullable FK to `Vendor`. Migrate existing rows by
  best-effort name match. **Rejected** — destructive; lossy;
  M2 contract change.
- **Option B.** Add nullable FK `VehicleCost.vendor_link`
  alongside the existing free-text `vendor` field. Historical
  rows unchanged; new rows populated by both fields when
  posted from a work order. **Rejected** — two fields
  representing the same concept invites drift; UI has to
  render both.
- **Option C.** Do NOT modify `VehicleCost` at all.
  `WorkOrder.vendor` is the FK to `Vendor`; when a work
  order auto-mints a `VehicleCost` row via `add_cost`, the
  service passes `vendor=<work_order.vendor.name>` as the
  snapshot free-text value. Historical rows unchanged.
  Renaming a vendor does not rewrite ledger history.
  **Chosen.**

**Why Option C.**

- M2 ledger substrate stays byte-for-byte unchanged. §3
  checklist row "M2 ledger substrate → `services/vehicle_ledger.py`
  API unchanged" locks the invariant.
- Historical readability preserved: renaming
  `Vendor(id=7).name` from "Bob's Body Shop" to "Bob's
  Auto Body" does not rewrite the `VehicleCost.vendor`
  free-text on posts made under the old name.
- Vendor removal is soft-only in normal operation
  (`is_active=False`). Hard delete is **prevented at the
  schema layer** by `on_delete=PROTECT` on
  `WorkOrder.vendor` and `VendorCommunication.vendor`.
  Postgres / SQLite raise `ProtectedError` when a delete
  is attempted against a referenced row; the M4 admin
  surfaces mirror that by not offering delete affordances
  for referenced vendors. Historical `VehicleCost.vendor`
  strings remain readable regardless because they are
  free-text snapshots (see §5.b Option C rationale above).
  Planning refinement adopted SESSION_066 — resolves the
  earlier "soft-delete only" note vs. planned SET_NULL FKs
  contradiction.
- Zero migration risk on M2 data. No backfill script needed.

**Do not** silently promote historical rows to FKs. The M2
contract "cost rows are immutable" applies here — even
metadata rewrites are forbidden.

### 5.c Load-bearing decision — Work-order state machine

**Question.** What is the smallest honest lifecycle for
`WorkOrder.status`?

**Candidate states.**

- `draft` — created but not yet approved.
- `approved` — recon manager approved; work authorized;
  estimate posted to ledger.
- `waiting_parts` — approved but blocked on part delivery.
- `scheduled` — approved + assigned + calendar date set.
- `in_progress` — vendor / tech has begun work.
- `completed` — work done; actual cost posted to ledger.
- `cancelled` — work not going to happen (walk-away,
  vendor unavailable, operator error); reversing entry
  posted if estimate was on ledger.

**Chosen (M4 v1 — five states):** `draft`, `approved`,
`in_progress`, `completed`, `cancelled`.

**Rejected additions.**

- `waiting_parts` — a work order can be "approved but
  waiting parts" — express this via `WorkOrderPart.status`
  aggregates rather than the WO status enum. Reason: parts
  status is many-per-WO and independently tracked.
- `scheduled` — the `estimated_completion_date` field
  captures the schedule; a separate status adds transition
  complexity without a distinct workflow trigger.

**Allowed transitions (service-owned; no FSM library).**

- `draft → approved` — recon_manager/sales_manager/dealer_owner
  approves.
- `draft → cancelled` — operator scrapped the WO before
  approval.
- `approved → in_progress` — vendor/tech started (may be
  the same operator hitting "start" in the UI).
- `approved → cancelled` — cancellation before work
  begins; reversing entry posted.
- `in_progress → completed` — actual cost captured; actual
  posted to ledger.
- `in_progress → cancelled` — partial completion or
  abandonment. Actual cost captured for work performed;
  ledger posts actual + reverses remaining estimate. Rare
  but must be supported per RECON §14.11 (partial vendor
  work).
- `approved → approved` — allowed for cost/date updates
  (idempotent re-approve; audit trail preserved via
  `approved_at` update).
- Terminal states: `completed`, `cancelled`. **No re-open**
  in v1 — mirrors M3 completed-report immutability. If
  post-completion issue surfaces, create a new WO.

**No FSM library.** Service-owned transition table + focused
tests suffice. Six transitions × ~5 negative-case tests each
= ~30 focused state-machine tests. FSM library adoption
requires proof that service-level transition validation is
insufficient — no such evidence today. Same discipline as M3
photo-workflow state ("draft / complete" done service-side).

### 5.d Load-bearing decision — Findings-to-work mapping

**Question.** One finding per work order, or many findings
per work order?

**Chosen: many-to-many via `WorkOrderFinding` through model.**

**Why.** RECON §3.7 combined-work-efficiency example: "drop
three units at the body man at once to save trips." A single
outsourced trip to a paint vendor could address (a) a body
panel dent finding + (b) a paint chip finding + (c) a fender
scratch finding. Three findings, one work order, one vendor
invoice. Forcing 1:1 would create three parallel work orders
with the same vendor + same dates + a coordination burden
the store does not experience in reality.

**Reverse case.** Can one finding require multiple work
orders? Yes but rarely (e.g. a "brakes worn" finding might
require a parts order WO + an install WO). Allow but don't
require.

**Traceability.** Every `WorkOrder.condition_findings.all()`
returns the human-authored findings it addresses; every
`ConditionFinding.work_orders.all()` returns the WOs
addressing it. Full bidirectional traceability preserved.

### 5.e Load-bearing decision — Estimate-to-ledger contract

**Question.** When does an `is_estimate=True` `VehicleCost`
row get created? How are updates + cancellations + completion
handled?

**Chosen contract** *(refined SESSION_066 — completion must
reverse the outstanding estimate; without this, a completed
WorkOrder is double-counted in `projected_total_investment`)*.

The load-bearing invariant driving the refinement:

> **After a WorkOrder reaches a terminal state
> (`completed` or `cancelled`), the net estimate
> contribution for that WorkOrder in the ledger must be
> zero.** Estimate rows and their matching reversal rows
> both remain visible as immutable history, but their
> signed sum for a terminal WO is `Decimal("0.00")`.

Bullet-by-bullet:

1. **Estimate post — on `WorkOrder` approval.** When
   `approve_work_order` runs and the WO has a non-null
   `estimated_cost`, the service calls `add_cost` with
   `is_estimate=True`, `amount=estimated_cost`, `category=`
   (mapped from `WorkOrder.category` — same 12-value enum),
   `incurred_at=now`,
   `reference=f"WORKORDER:{wo.id}:estimate:{seq}"` where
   `seq` starts at 1 for the first estimate post.
2. **Estimate revision — post reversal + new.** If the
   `estimated_cost` changes while the WO is still non-terminal,
   the service posts a reversing entry
   (`amount=-outstanding_estimate`,
   `reference=f"WORKORDER:{wo.id}:estimate_reversal:{seq}"`)
   followed by a new estimate entry
   (`reference=f"WORKORDER:{wo.id}:estimate:{seq+1}"`).
   Never edits the original row — preserves M2 immutability.
   Sequence increments monotonically for the WorkOrder's
   lifetime.
3. **Completion — reverse outstanding estimate atomically
   with actual post.** When `complete_work_order` runs,
   the service (a) captures `actual_cost`
   (operator-entered or vendor-invoice-parsed), (b) posts
   a reversing entry for the currently-outstanding estimate
   with the dedicated one-shot reference
   `WORKORDER:{wo.id}:completion_estimate_reversal`, and
   (c) posts the actual cost with
   `reference=f"WORKORDER:{wo.id}:actual"`. All three
   ledger operations happen inside a single DB transaction
   so a mid-completion crash leaves the ledger with either
   no change or the full set — never a half-reversed
   estimate. The dedicated one-shot reference lets the
   idempotency check distinguish "we already reversed on
   completion" from "we reversed during a mid-life estimate
   revision." **After this transaction: estimate rows and
   the completion reversal net to zero, and
   `total_investment` picks up only the actual.**
4. **Cancellation — reverse outstanding estimate.**
   `cancel_work_order` posts a reversing entry for the
   currently-outstanding estimate with
   `reference=f"WORKORDER:{wo.id}:estimate_reversal:cancel"`.
   If the WO was `in_progress` with a partial actual post
   already made, actual rows remain on the ledger (they
   represent work truly performed); the estimate is still
   reversed because the WO will never complete against it.
5. **Idempotency.** Before every `add_cost` call, the M4
   service checks
   `VehicleCost.objects.filter(reference=<tag>).exists()`
   and skips if true. Prevents double-posting on race /
   retry. The four distinct reference key families —
   `estimate:<seq>`, `estimate_reversal:<seq>`,
   `completion_estimate_reversal`, `estimate_reversal:cancel`,
   `actual` — make idempotency deterministic without
   ambiguity between mid-life reversals and terminal-state
   reversals.

**Reference key vocabulary — single source of truth.** The
`services/recon.py` module in M4.3 exposes these as
module-level constants (mirrors M2/M3 enum-constant house
style) so tests and future callers reference the string
literals identically:

- `WORKORDER_LEDGER_REF_ESTIMATE = "WORKORDER:{wo_id}:estimate:{seq}"`
- `WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL = "WORKORDER:{wo_id}:estimate_reversal:{seq}"`
- `WORKORDER_LEDGER_REF_COMPLETION_ESTIMATE_REVERSAL = "WORKORDER:{wo_id}:completion_estimate_reversal"`
- `WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL_CANCEL = "WORKORDER:{wo_id}:estimate_reversal:cancel"`
- `WORKORDER_LEDGER_REF_ACTUAL = "WORKORDER:{wo_id}:actual"`

**M3 invariant preserved.** `ConditionFinding.estimated_cost`
NEVER posts to `VehicleCost`. Only work-order approval
triggers a post. This is the load-bearing rule from M3.5
retro §4; three focused tests already lock it and continue
to pass.

**M2 immutability preserved.** No `VehicleCost` row is ever
edited or deleted. Every change is a reversing entry.

**Semantic corollary on `projected_total_investment`.** With
completion-time reversal in place, `projected_total_investment`
(estimate rows + actuals) no longer double-counts completed
WorkOrders: after completion, the estimate rows and their
completion reversal cancel out, leaving only the actual
contributing to both `total_investment` and
`projected_total_investment`. Locked by M4.3 tests.

### 5.f Load-bearing decision — Role permission matrix

**Question.** Which existing role can access each M4 surface?

**Existing roles** (all shipped in M1 · 4A):
`dealer_owner`, `sales_manager`, `recon_manager`,
`f_and_i_manager`, `collections`, `advisor`, `porter`.

**M4 does NOT add a new role.** `ROLE_RECON_MANAGER` already
exists. M4 adds a new **permission class**:
`IsReconManagerSalesManagerOrOwnerAtActiveDealership`
(composed of the three roles authorized on M4 admin
surfaces).

**Per-surface matrix.**

| M4 surface | dealer_owner | sales_manager | recon_manager | f_and_i_manager | collections | advisor | porter |
|---|---|---|---|---|---|---|---|
| GET `Vendor` list / detail | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| POST/PATCH/DELETE `Vendor` | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| GET recon dashboard (vehicle) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| POST `ReconDecision` | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| POST/PATCH `WorkOrder` (create/approve) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| POST `WorkOrder` complete | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| POST `WorkOrder` cancel | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| POST/PATCH `WorkOrderPart` | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| POST/PATCH `VendorCommunication` (draft/approve/log) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| GET auto-minted VehicleCost | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |

**Least-privilege notes.**

- Recon manager gets READ access to `VehicleCost` rows for
  vehicles with active work orders (they need to see the
  running recon cost). Recon manager does NOT get access to
  `VehicleAcquisition` fields (purchase price, buyer fees)
  — that's dealer-owner / sales-manager territory. Enforce
  via a scoped serializer, not a filtered queryset (the
  data is still accessible via M2.6 endpoints, but M4 does
  not surface the acquisition side to recon_manager).
- Recon manager can create + approve their own vendor
  comms. Only `dealer_owner` and `sales_manager` can
  `mark_sent` a comm on a `VendorCommunication` with total
  authorized amount above a threshold — TBD in M4 planning
  amendment IF the workflow surfaces this need. For v1, any
  authorized role can `mark_sent`.
- `porter` and `advisor` remain read-only to non-recon
  surfaces; they get 403 on every M4 endpoint. Documented
  in M4.6 test class `ReconEndpointPermissionMatrix`.

### 5.g Load-bearing decision — Vendor communication AI boundary + safety scrub

**Question.** What is the exact AI boundary for vendor
comms? How does the new safety scrub interact with the
existing stack?

**AI boundary — locked invariants.**

AI drafts vendor communications. AI **may**:

- Compose greeting / closing / prose.
- Summarize findings the operator selected.
- Suggest tone (formal / casual).
- Group multiple findings into readable bullets.
- Restate operator-entered dates / dollar amounts.

AI **may NOT** invent:

- Findings (must be sourced from
  `WorkOrder.condition_findings.all()`).
- Part numbers (must be sourced from
  `WorkOrder.parts.all()` where
  `WorkOrderPart.part_number != ""`).
- Quoted prices (must equal `WorkOrder.authorized_cost` or
  a `WorkOrderPart.unit_cost * quantity`).
- Vendor availability (no calendar API in M4 v1).
- Appointment times (must equal
  `WorkOrder.estimated_completion_date` operator-entered
  value).
- Pickup / drop-off commitments (out of scope; operator
  enters as free-text notes).
- Completion dates (must equal
  `WorkOrder.estimated_completion_date` or
  `WorkOrder.actual_completion_date`).
- Authorization amounts (must equal
  `WorkOrder.authorized_cost`).
- Vehicle condition facts NOT present in the linked
  `ConditionFinding.description` rows.

**Draft input contract.** `services/vendor_comm.py::draft_communication(work_order,
*, dealership, drafted_by, kind, channel, extra_notes="")`
takes a structured source-data bundle:

```python
source = {
    "vehicle": {stock, year, make, model, vin_last_6},
    "vendor": {name},
    "findings": [
        {id, category, severity, description},
        ...
    ],
    "authorized_cost": str_two_decimals or None,
    "estimated_completion_date": iso or None,
    "parts_needed": [
        {name, part_number, quantity, source_type},
        ...
    ],
    "operator_notes": str,
}
```

The LLM prompt template gets this bundle rendered into text
and is instructed to draft the communication using ONLY
facts from the bundle. No external context, no memory across
requests.

**Post-LLM safety scrub — new: `_scrub_invented_recon_fact`.**

Runs on `kind="vendor_comm"` after `detect_unsafe_response`.
Text-only. Zero DB access at scrub time — the source-bundle
values are passed in as scrub parameters.

Detection regex families:

- **Invented finding IDs** — the draft mentions "Finding
  #123" but 123 is not in `source["findings"][*]["id"]`.
  Rewrite: strip the ID reference; retain the description
  if present in source.
- **Invented part numbers** — the draft mentions a part
  number pattern (`[A-Z0-9-]{5,}`) not present in
  `source["parts_needed"][*]["part_number"]`. Rewrite:
  strip the part number.
- **Invented dollar amounts** — the draft mentions a
  `$\d+` amount not equal to `authorized_cost` or the sum
  of `parts_needed[*].unit_cost * quantity`. Rewrite: strip
  the amount; log for operator review.
- **Invented dates** — the draft mentions a date not equal
  to `estimated_completion_date`. Rewrite: replace with a
  neutral phrase or strip.

**Provenance recording.** After the scrub succeeds, the
service persists `VendorCommunication.source_provenance` as
a JSONField mapping sentence indices to source-bundle keys:

```json
{
  "sentence_0": {"source": "findings", "ids": [12, 15]},
  "sentence_1": {"source": "authorized_cost"},
  "sentence_2": {"source": "estimated_completion_date"},
  "sentence_3": {"source": "operator_notes"},
  "sentence_4": {"source": "ai_prose"}
}
```

Operators reviewing the draft see which sentences carry
factual claims vs. AI prose. UI treatment TBD in M4.7 —
minimally, `ai_prose` sentences render with a subtle color
tint or margin marker.

**Human approval required before send.** The
`VendorCommunication.status="sent"` transition requires
`approved_by IS NOT NULL` and `sent_by IS NOT NULL`. The
service raises `ReconImmutableError` if these fields are
NULL at the transition attempt. Locked by focused tests.

### 5.h Load-bearing decision — Parts procurement scope

**Question.** RECON §16.4 lists automated parts sourcing +
ordering as an M4 automation opportunity. Which parts of
that opportunity are in M4 scope?

**In M4 scope — operational tracking data only.**

- `WorkOrderPart` model with fields listed in §1.5.
- Service functions: `add_part`, `update_part`,
  `mark_ordered`, `mark_received`, `mark_installed`,
  `mark_returned`, `mark_backordered`.
- Read endpoints to render parts status.
- Draft parts-order prose that the operator copy-pastes
  into their vendor portal (via `VendorCommunication` with
  `kind="parts_order"` — new `kind` value if needed, or
  reuse `assignment`).

**Explicitly OUT of M4 scope.**

- Live parts marketplace search (RockAuto / PartsGeek /
  OEM parts counter APIs).
- Automated purchase-order creation via vendor API.
- Vendor payment / invoicing.
- Parts inventory management (per-store SKU tracking).
- Recall check automation (RECON §16.17 — separate scope).

**Why.** RECON §16 lists 17 automation opportunities, most
of them deferred to Milestones 5-8. Live marketplace + auto-
ordering + payment would require vendor API integrations M4
does not have infrastructure for (async, credentials
management, error-recovery workflow). Ship the operational
data shape; extension seams stay open; do not pretend
integrations exist.

### 5.i Load-bearing decision — Outsourced scheduling

**Question.** RECON §3.7 discusses scheduling with vendors.
What does "sets the appointment" mean in M4?

**M4 v1 meaning:**

- Operator records `WorkOrder.estimated_completion_date`
  (operator-entered based on verbal or written vendor
  commitment).
- System drafts an email / text (via `services/vendor_comm.py`)
  requesting the appointment or confirming it.
- **Operator sends via their own email / SMS client.** The
  system does not send.
- Vendor response is recorded manually by the operator as
  another `VendorCommunication` row with
  `direction="inbound"` + `channel="phone"` (or
  `"email"` if the operator forwards it).

**Explicitly OUT of M4 scope.**

- Calendar API integration (Google Calendar / Outlook).
- Vendor portal booking (each vendor has their own scheduling
  system).
- Automated scheduling optimization.
- Inbound email parsing.
- SMS provider integration (Twilio, etc.).

**Why.** RECON §3.7 explicitly notes "the recon calendar is
often kept in someone's head at smaller stores; larger stores
use a whiteboard or a shop management system." Independent
dealers do not have vendor APIs for the majority of vendors
they work with. Building an integration surface before we
have vendor coverage would be premature and drift toward
"enterprise service software" the target market does not
use.

### 5.j Load-bearing decision — First-live-prod deployment

**Question.** M4 introduces workflows that may be used by
an actual dealership employee or reference an external
vendor. Does prod deployment happen inside M4, as a separate
pre-pilot increment, or when a real pilot store is identified?

**Chosen: prod deployment is a separate concern deferred
outside M4.**

**Rationale.**

- Every M4 workflow ships operator-copy-paste-ready. No
  send code path is production-critical for v1.
- Real vendor communications need real vendor
  relationships. The pilot-store engagement is what
  provides that; M4 code cannot pretend to have vendors
  without one.
- Auth substrate is prod-ready (M1 · 4E shipped SessionAuth +
  Token + CSRF). Storage substrate is prod-ready (M3.4
  S3-compatible). What M4 adds is business logic that
  needs no new prod surface beyond what M3 shipped.
- Deferring prod does not block M4 work — every M4
  increment ships fully verifiable against the local
  stack.

**Acceptance criteria for a future prod-readiness pass** (NOT
M4 scope; documented here so future planning knows what to
build):

- SMTP (Django's `EmailMessage`) wiring — decide whether
  `SendGrid` / `Postmark` / plain SMTP is the v1 send path.
- Vendor `our_reply_to_email` field on `Vendor` or
  `DealerOnboardingProfile`.
- Per-tenant sending quota / rate limit.
- `VendorCommunication` retry queue (Celery — Milestone 7
  concern).
- Bounced-email handling.
- Legal review of vendor-facing wording (some states
  require identity + license disclosure in commercial
  outreach).
- Real pilot store identified with contact list of real
  vendors.

**When it lands.** Between M4 and M5, or during / after M5.
Documented explicitly rather than buried as an architectural
note.

---

## 6. Anchors that win on conflict

If this planning doc disagrees with:

1. `docs/PROJECT_RULES.md` — the rules win.
2. `docs/DOC_GOVERNANCE.md` — the doc governance wins.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4 —
   the roadmap wins on scope questions.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — the auth model
   wins on identity / tenancy / permission questions.
5. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6 lessons —
   the lessons win on engineering-process questions.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons —
   same weight as M3 §6.
7. `docs/research/RECON_MAPPING.md` +
   `docs/research/VEHICLE_CENTRIC_PIVOT.md` — the research
   wins on business-truth questions.
8. `docs/CAPABILITY_MATRIX.md` — the matrix wins on "what
   does the software actually do today?" questions.
9. Current source code — the code wins on "what does the
   software actually do today?" questions.

Planning docs are claims. Rules + research + code are facts.

---

## 7. Increment sequencing

The design memo (§1) describes *what* Milestone 4 delivers.
This section records *how* the work is sliced into per-session
increments so each session ends with the app deployable and the
test baseline healthy.

Mirrors the shape `MILESTONE_2_PLANNING.md` §7.b + `MILESTONE_3_PLANNING.md`
§7 proved out. **Nine increments.** Increment discipline
inherited from M3 retro §6 lesson 1: no session ever bundles
two increments to "save time"; the M3.6 A/B split precedent
demonstrates that discipline pays for itself in verification
clarity.

### Increment 1 (M4.1) — Core persistence (Vendor + recon models)

**Scope.** Six models (`Vendor`, `ReconDecision`, `WorkOrder`,
`WorkOrderFinding`, `WorkOrderPart`, `VendorCommunication`) +
migration `0016` + admin registrations + module-level enum
constants (`WORK_ORDER_STATUS_CHOICES`,
`WORK_ORDER_VENUE_CHOICES`, `RECON_DECISION_TIER_CHOICES`,
`WORK_ORDER_PART_STATUS_CHOICES`,
`VENDOR_COMMUNICATION_STATUS_CHOICES`,
`VENDOR_COMMUNICATION_CHANNEL_CHOICES`,
`VENDOR_COMMUNICATION_KIND_CHOICES`,
`VENDOR_COMMUNICATION_DIRECTION_CHOICES`,
`WORK_ORDER_PART_SOURCE_TYPE_CHOICES`). Cross-tenant
`clean()` guards on all six models. `_TENANT_CARRIER_MODEL_NAMES`
tuple extended from 9 → 15. `DATABASES["migration_check"]`
alias verified.

**No service module in M4.1.** Persistence layer only.

**Tests.** ~65 focused model tests: schema (dealership FK NOT
NULL, choices validation, one-to-many + many-to-many
relationships, cascade-delete behavior), cross-tenant guards
(clean() rejects mismatched dealership on all six models),
enum coverage, `_TENANT_CARRIER_MODEL_NAMES` extension (six
new registrations without breaking the nine existing ones).

**Boundary.** Test baseline: 2,124 → ~2,189.

**Invariant locked.** Every M4 persistence-layer invariant
from §4 model-layer subsection is testable at commit.

### Increment 2 (M4.2) — Recon service + WorkOrder state machine

**Scope.** `services/recon.py` module with:

- `record_decision(finding, *, dealership, tier, decided_by,
  notes="") -> ReconDecision` — refuses when
  `finding.report.status != "complete"`; refuses cross-tenant;
  one-per-finding enforced by OneToOne.
- `create_work_order(vehicle, *, dealership, category, venue,
  vendor=None, assignee=None, estimated_cost=None,
  estimated_completion_date=None, notes="") -> WorkOrder` —
  always creates in `status="draft"`.
- `attach_findings(work_order, *, dealership, finding_ids:
  list[int]) -> list[WorkOrderFinding]` — creates the
  through-table rows; refuses if any finding is cross-tenant
  or from a non-completed report.
- `detach_finding(work_order, finding, *, dealership) -> None`
  — refuses when WO status is not `draft`.
- `approve_work_order(work_order, *, dealership, approved_by,
  authorized_cost=None) -> WorkOrder` — draft→approved
  transition; sets provenance fields; **calls M4.3
  ledger-posting hook** (implemented in M4.3, imported here
  as a lazy hook to avoid cycle).
- `start_work_order(work_order, *, dealership, started_by)
  -> WorkOrder` — approved→in_progress.
- `complete_work_order(work_order, *, dealership,
  completed_by, actual_cost, actual_completion_date=None)
  -> WorkOrder` — approved/in_progress→completed; sets
  provenance; **calls M4.3 ledger-posting hook**.
- `cancel_work_order(work_order, *, dealership, cancelled_by,
  cancellation_reason="") -> WorkOrder` — any non-terminal
  state → cancelled; **calls M4.3 reversing-entry hook**.
- `CrossTenantReconError(ValueError)` — fail-closed guard on
  every function.
- `ReconImmutableError(ValueError)` — refused state transition
  (draft→completed skipping approved, re-open attempt,
  edit-on-terminal etc.). Distinct class so M4.6 API can map
  to 409.
- Two new `@property` accessors on `Vehicle`:
  `open_work_orders`, `has_recon_decisions` (function-local
  imports per M3.3 pattern).
- Every function threads `dealership=` explicitly per
  `AUTHENTICATION_MODEL.md` §8b.

**Ledger hook stub.** M4.2 leaves the ledger-posting hook as
a no-op or a stubbed integration point; M4.3 implements it.
The state machine itself is complete + verifiable in M4.2.

**Tests.** ~55 focused service tests: decision semantics
(one-per-finding, completed-report required, cross-tenant
refusal); state-machine transitions (each allowed transition
succeeds; each disallowed raises); attach/detach findings
(cross-tenant refusal; through-table integrity);
`_refresh_and_assert_status` pattern; `full_clean` before
save on every write path.

**Boundary.** Test baseline: ~2,189 → ~2,244. No migrations.

**Invariant locked.** Every business-layer invariant from §4
locked at service level (except ledger integration —
comes in M4.3).

### Increment 3 (M4.3) — Estimate-to-ledger contract + idempotency

**Scope.** `services/recon.py` gains the ledger-posting hook
functions. Reference-key vocabulary imported from
`services/recon.py` module-level constants per §5.e locked
list.

- `_post_estimate(work_order, *, seq) -> VehicleCost` —
  called from `approve_work_order` (and from the estimate
  revision path); posts
  `add_cost(is_estimate=True, reference=WORKORDER_LEDGER_REF_ESTIMATE.format(wo_id=..., seq=seq))`;
  computes `seq` from prior `WORKORDER:{wo.id}:estimate:*`
  count + 1; idempotent (skip if the target reference already
  exists).
- `_post_estimate_reversal(work_order, *, outstanding_amount,
  seq) -> VehicleCost` — negative-amount reversing entry
  under `WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL`.
- `_post_completion_reversal(work_order, *, outstanding_amount)
  -> VehicleCost` — negative-amount reversing entry under
  the one-shot `WORKORDER_LEDGER_REF_COMPLETION_ESTIMATE_REVERSAL`
  reference; called only from the completion flow (planning
  refinement SESSION_066).
- `_post_cancel_reversal(work_order, *, outstanding_amount)
  -> VehicleCost` — negative-amount reversing entry under
  `WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL_CANCEL`; called
  only from the cancellation flow.
- `_post_actual(work_order) -> VehicleCost` — called from
  `complete_work_order`; posts
  `add_cost(is_estimate=False, reference=WORKORDER_LEDGER_REF_ACTUAL...)`;
  refuses (via idempotency check) if an `:actual` row
  already exists.
- Handles the vendor snapshot: passes
  `vendor=work_order.vendor.name if work_order.vendor else ""`
  to `add_cost` so `VehicleCost.vendor` free-text captures
  the vendor name at posting time.

Wires the hooks into M4.2's `approve_work_order` /
`complete_work_order` / `cancel_work_order`.
`complete_work_order` runs `_post_completion_reversal` and
`_post_actual` inside a single `transaction.atomic()` block
so a mid-completion failure leaves the ledger with either
no change or the full set — never a half-reversed estimate.
The estimate-revision path (WO patch with new
`estimated_cost` while `status=approved`) posts
`_post_estimate_reversal` + `_post_estimate(seq=seq+1)`.

**Tests.** ~35 focused tests: estimate posts on approval;
actual posts on completion; **completion-time estimate
reversal posts atomically with actual** (planning refinement
SESSION_066 — new test); **net estimate contribution equals
`Decimal("0.00")` for a completed WO**; **projected_total_investment
does not double-count completed WOs**; reversing entry on
cancel; double-approve idempotent; double-complete raises
(per state machine); ConditionFinding.estimated_cost never
triggers a post (regression coverage — M3.5 invariant
preserved); VehicleCost.vendor free-text captures
work_order.vendor.name; inactive vendor still readable in
historical rows; sequential estimate updates produce correct
reversing pattern; mid-completion crash leaves ledger
untouched (transaction atomicity test).

**Boundary.** Test baseline: ~2,244 → ~2,279. No migrations.

**Invariant locked.** Every ledger-integration invariant from
§4.

### Increment 4 (M4.4) — Parts tracking service

**Scope.** `services/recon.py` gains part-tracking functions:

- `add_part(work_order, *, dealership, name, quantity=1,
  part_number="", source_type="in_stock", source_name="",
  unit_cost=None, notes="") -> WorkOrderPart` — refuses
  when WO is not in a state that permits parts changes
  (`draft`, `approved`, `in_progress`).
- `update_part(part, *, dealership, **updates) ->
  WorkOrderPart` — whitelist: name, description, part_number,
  quantity, unit_cost, source_type, source_name, notes.
  Status transitions happen via dedicated functions.
- `transition_part_status(part, *, dealership, new_status,
  actor)` — validates transition (`needed → ordered`,
  `ordered → received`, `received → installed`, `ordered
  → backordered`, `ordered → returned`, `received →
  returned`); sets appropriate timestamp field.
- `delete_part(part, *, dealership) -> None` — only when
  parent WO is `draft`.

**Tests.** ~30 focused tests: add on draft/approved/in_progress
allowed; add on completed/cancelled refused; update whitelist;
each part-status transition succeeds; disallowed transitions
raise; parts survive WO cancellation (they're documentation).

**Boundary.** Test baseline: ~2,279 → ~2,309. No migrations.

**Invariant locked.** `WorkOrderPart.status` choices + valid
transitions + parts-changes-gated-by-WO-status.

### Increment 5 (M4.5) — Vendor communication drafting + `invented_recon_fact` scrub

**Scope.**

- New module `services/vendor_comm.py`:
  - `draft_communication(work_order, *, dealership,
    drafted_by, kind, channel, extra_notes="") ->
    VendorCommunication` — assembles source bundle;
    calls LLM via `services/llm/factory.py`; runs
    output through post-LLM scrubs including new
    `invented_recon_fact`; persists row with
    `status="draft"`, `drafted_by`, `drafted_at`,
    `source_provenance`.
  - `approve_communication(comm, *, dealership,
    approved_by) -> VendorCommunication` — draft→approved.
  - `mark_sent(comm, *, dealership, sent_by, sent_content=None)
    -> VendorCommunication` — approved→sent; captures
    optional edited `sent_content` (falls back to
    `draft_content`).
  - `log_communication(comm, *, dealership, sent_by,
    logged_content) -> VendorCommunication` — records
    an off-system comm (phone / in-person).
- `services/llm_safety.py` extended with
  `_scrub_invented_recon_fact` firing on
  `kind="vendor_comm"`. Regex families per §5.g.
- Two new `kind` values recognized by
  `apply_post_llm_scrubs`: `"vendor_comm"`, `"parts_order"`
  (subtype of vendor comm, same scrub).

**Tests.** ~55 focused tests split across:
- `services/vendor_comm` — draft happy path;
  source_provenance recording; state transitions;
  human-approval-required-before-send invariant.
- `services/llm_safety._scrub_invented_recon_fact` —
  invented finding IDs stripped; invented part numbers
  stripped; invented $ amounts stripped; invented dates
  stripped; correctly-attributed content passes untouched.
- Full LLM path stubbed via existing mock provider
  (`services/llm/mock_provider.py` if present, else via
  `unittest.mock.patch`).

**Boundary.** Test baseline: ~2,309 → ~2,364. No migrations.
Zero real LLM API access in tests.

**Invariant locked.** AI cannot invent recon facts.

### Increment 6 (M4.6) — Admin API + permission matrix

**Scope.** Admin endpoints under
`/api/dealer-ai/admin/vehicles/<stock_number>/` and
`/api/dealer-ai/admin/vendors/`. Roughly:

- Vendor CRUD (list/create/detail/patch — no delete;
  `is_active` toggle only).
- `GET .../recon/` — recon dashboard for a vehicle:
  latest completed condition report + decisions + work
  orders + parts + comms.
- `POST .../findings/<finding_id>/recon-decision/` — record
  decision.
- `POST .../work-orders/` — create draft.
- `POST .../work-orders/<wo_id>/approve/` — approve.
- `POST .../work-orders/<wo_id>/start/` — start.
- `POST .../work-orders/<wo_id>/complete/` — complete.
- `POST .../work-orders/<wo_id>/cancel/` — cancel.
- `PATCH .../work-orders/<wo_id>/` — edit whitelisted
  fields (estimated_cost, notes, etc.) with re-estimate
  ledger flow.
- `POST .../work-orders/<wo_id>/findings/` — attach findings.
- `DELETE .../work-orders/<wo_id>/findings/<finding_id>/` —
  detach finding.
- `POST .../work-orders/<wo_id>/parts/` — add part.
- `PATCH .../parts/<part_id>/` — update part / transition
  status.
- `POST .../work-orders/<wo_id>/comms/draft/` — draft comm.
- `POST .../comms/<comm_id>/approve/` — approve.
- `POST .../comms/<comm_id>/mark-sent/` — mark sent.
- `POST .../comms/<comm_id>/log/` — log off-system comm.

New permission class
`IsReconManagerSalesManagerOrOwnerAtActiveDealership` per
§5.f. Domain-error mapping per §5.g + §5.e.

**Tests.** ~90 focused endpoint tests: permission matrix
per endpoint (7 role cases minimum), business flows,
domain-error mapping, cross-tenant fail-closed 404s,
no-storage-key-leak, no-recon-data-on-public-surfaces.

**Boundary.** Test baseline: ~2,364 → ~2,454. No migrations.

**Invariant locked.** Every endpoint-layer invariant from §4.

### Increment 7 (M4.7) — Operator UI

**Scope.** Frontend surface:

- Route `/dealer-ai-inventory/:stock/recon` inside
  `<RequireAuth>` in `main.tsx`.
- `frontend/src/pages/VehicleReconPage.tsx` (~500 lines
  target — extract components per M3.7 discipline).
- Small extracted components in
  `frontend/src/components/recon/`:
  `ReconDashboard`, `DecisionRow`, `WorkOrderCard`,
  `WorkOrderStatusBadge`, `PartRow`, `VendorCommDraftPanel`,
  `VendorPickerModal`.
- Typed API helpers in `lib/api.ts` for every M4.6
  endpoint.
- "Recon" button on operator inventory card (beside
  M2.7 "Ledger" + M3.7 "Condition Report").
- Role gating (recon_manager + sales_manager +
  dealer_owner see write affordances).
- Draft-vs-approved-vs-sent visual states.
- `source_provenance` rendered on vendor-comm drafts (AI
  prose sentences visually distinct).
- Distinct 401/403/404/409/502 UX.

**Verification.** `npx tsc --noEmit` clean; `npx vite build`
clean. Backend baseline unchanged. Manual browser
walkthrough deferred to operator first-live-use per M3.7
honesty precedent.

**Boundary.** Frontend files only. Backend baseline
~2,454 unchanged.

**Invariant locked.** Every frontend invariant from §4.

### Increment 8 (M4.8) — Communication send / scheduling API (deferred subset)

**Scope.** Per §5.i deployment decision — v1 M4 ships with
operator-copy-paste-from-draft-UI as the send workflow. This
increment is **explicitly reserved but not planned in scope**
for the M4 sequence unless a real pilot store engagement
surfaces during M4 that requires it.

**If it lands in M4:**
- `services/vendor_comm.py::send_via_smtp(comm)` —
  Django `EmailMessage`; per-tenant reply-to config;
  bounce handling deferred.
- `services/vendor_comm.py::send_via_sms(comm)` —
  provider adapter (Twilio); NOT included unless pilot
  requires.
- Frontend "Send" button wired to the endpoint instead of
  copy-paste UI.

**If deferred (default):** SESSION marker in M4 closeout
retro §7 as "deferred to prod-readiness pass."

**Tests.** ~30 if landed; zero if deferred.

**Boundary.** Deferrable increment — do NOT commit to
building it in M4 planning without pilot-store evidence.

### Increment 9 (M4.9) — Verification + closeout

**Scope.** Documentation-only session mirroring M2.8 /
M3.8:

- §3 compatibility sweep with evidence citations.
- `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` (mirror M3
  retro shape).
- `docs/CAPABILITY_MATRIX.md` §7e "Recon automation
  (Milestone 4, shipped)".
- `IMPLEMENTATION_ROADMAP.md` §M4 marked SHIPPED; §M5
  promoted.
- Frontmatter flip on THIS planning doc: `status: shipped`.
- Overwrite `00-START-NEXT-SESSION.md` with M5.0 priority.

**Boundary.** No code. Backend baseline unchanged.

---

## 8. Related documents

- `docs/PROJECT_RULES.md` — governance layer.
- `docs/DOC_GOVERNANCE.md` — documentation rules.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4 —
  scope contract.
- `docs/roadmap/AUTHENTICATION_MODEL.md` — auth substrate.
- `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` — §8 M4
  bootstrap; §6 lessons.
- `docs/roadmap/MILESTONE_3_PLANNING.md` — shape template.
- `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` — lessons +
  deferrals; §6 ledger-integration precedent for M4.3.
- `docs/roadmap/MILESTONE_2_PLANNING.md` — shape template.
- `docs/research/RECON_MAPPING.md` — full document; §§3, 4,
  5, 6, 7, 11, 14, 15, 16 all cited.
- `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 3.
- `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md` — §2.11
  reversing-entry pattern (M4.3 inherits).
- `docs/CAPABILITY_MATRIX.md` — §7c M2 ledger + §7d M3
  condition-report surfaces M4 builds on.
- Current source code — authoritative for what M4 is
  extending vs. replacing.
