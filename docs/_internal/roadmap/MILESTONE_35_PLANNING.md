---
title: "Milestone 35 — Lender Submission Activation: record the latest structure's lender submission, capture the response on that same submission, and derive the current F&I state from verified FK events"
status: active
type: planning-memo
generated: 2026-08-05
generated_at_session: SESSION_216 (skeleton + expansion + all §5 locks)
milestone: 35
milestone_name: "Lender Submission Activation: record the latest structure's lender submission, capture the response on that same submission, and derive the current F&I state from verified FK events"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_34_RETROSPECTIVE.md §9 (M35 candidate list + F&I depth-arc standing question)
  - docs/roadmap/MILESTONE_33_RETROSPECTIVE.md §9 (M32 → M33 F&I depth-arc origin)
  - docs/roadmap/MILESTONE_10_PLANNING.md §1.3 (M10.3 LenderProgram + LenderSubmission substrate contract)
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md rows #93/#94/#95 (three lender endpoints classified defer-candidate-O2 at M34 baseline)
  - backend/dealer_ai/models.py (LenderProgram, LenderSubmission, LENDER_SUBMISSION_STATUS_* constants)
  - backend/dealer_ai/services/f_and_i/lender.py (record_lender_submission, update_lender_submission_status, list_active_lender_programs)
  - backend/dealer_ai/services/f_and_i/credit_application.py (M33.1 D1 subquery-annotation precedent)
  - backend/dealer_ai/views_f_and_i.py (admin_lender_submission_create, admin_lender_submission_update, _project_lender_submission)
  - backend/dealer_ai/urls.py (admin/lender-submissions/ POST + PATCH; admin/lender-programs/ POST — no list; no single-record GET)
  - frontend/src/components/f-and-i/DealStructureForm.tsx + DealStructureReadView.tsx (M33.2 truthful-entry contract precedent)
  - frontend/src/pages/DealerFandIIncoming.tsx (M33.2 derived-status chip + row-action precedent)
  - acceptance/journeys/f_and_i_manager/fandi_intake_activation.spec.ts (M33.2 journey preserved as regression asset)
  - backend/dealer_ai/management/commands/seed_journey_fandi_intake_activation.py (M33.2 Structure Sam seed independence precedent)
---

# Milestone 35 — Lender Submission Activation

> **Active planning memo.** Drafted + expanded + all §5 locks at
> SESSION_216 M35.0 open.
>
> **§5.a locked at open** as **Lender Submission Activation** —
> third link of the M32 → M33 F&I depth arc — under the *primary
> operational-coverage lens* (durable since M22 close). Selected
> over both (b) breadth reset and (c) close-another-deferral per
> the M34 §9 standing question. The M10.3 substrate (LenderProgram
> catalog + LenderSubmission with the four-value status vocabulary
> `pending / approved / counter / declined`) has waited 108
> sessions since SESSION_108 for an operator receiver; M35
> activates it via one shipped-but-dormant CREATE endpoint + one
> shipped-but-dormant PATCH endpoint + one new thin FK-discovery
> endpoint, adding four fully-derived derived states on top of
> M33's two.
>
> **Ten planning-open corrections applied before §5.b lock** (z
> lesson — verification-driven revision cycles at planning-open,
> now on invocation 4). All ten strengthened the locked design; none
> changed the target selection. Two were substantive scope
> reshapes (Option 1 → Option 2; audit projection re-derivation
> from direct artifact inspection); three were UI-language
> tightenings (record-vs-transmit; correct-vs-another-response;
> approved-vocabulary refinement); one closed a discovered
> substrate gap (LenderProgram FK discoverability); one dropped an
> unverifiable endpoint wrapper (`getLenderSubmission` — no GET
> endpoint exists); one narrowed a projection (LenderProgram list
> exposes only `{id, name}`); one downgraded a technical risk from
> "unverified" to "verified working" via live shell test (nested-
> annotation OuterRef pattern on SQLite); one added a fourth
> defense layer to the financial-language contract (Vitest string-
> absence test).
>
> **The anchor question** — *Can an F&I manager record where a
> structured deal was submitted, capture the lender's response, and
> see the resulting operational state without leaving Dealer OS?* —
> governs every M35 scope decision.
>
> **Substrate-compound-value continuation resumes at M35.** M32
> shipped the sales-to-F&I bridge (writeup → intake receiver); M33
> shipped the first F&I operator action (DealStructure creation
> + read); M35 ships the send-and-response loop (LenderSubmission
> creation + status update + four new derived workflow states).
> Three links in the F&I depth arc.
>
> **Zero-drift permission-class streak continues at 38 → 39.** No
> new permission class — three new HTTP surfaces (one M35.1 list
> endpoint + two M35.2 endpoint activations) all reuse the shipped
> `_M101_PERMS` from M10.1. No migration. No schema change. No new
> service verb.
>
> **DoD amendment (M21.0 §5.f Option B) compliance.** M35.1
> backend-only → **DoD exception path invocation #12** (M26 +
> M27.1 + M28.1 + M29.1 + M30.1 + M31.1 + M32.1 + M33.1 + M34.1 +
> M34.2 + M35.1). M35.2 satisfies DoD directly via new
> `fandi_submission_response_loop` Playwright journey.
>
> **Two-increment shape** — backend / frontend boundary matching
> M33's shape exactly. M35.1 ships the FK-discovery endpoint +
> two subquery annotations + projection extension + Django
> regression tests + Postgres OuterRef re-verification. M35.2
> ships API-client wrappers + two new components + status-chip
> extension + Playwright journey + idempotent seed. Rollback
> fully independent in reverse ship order.
>
> **Durable lesson (ff) re-application locked at planning-open**
> (M34.0 origin — first re-application). D9 + D10 preserve the
> `@rerun-hygiene` tag contract and back-to-back double-run proof
> mechanism from M34.2 verbatim; the new Submission Sasha seed is
> idempotent against mutated state from its first shipping day. On
> re-application, (ff) elevates to load-bearing-across-two-
> milestones.
>
> **Durable lesson (cc) fifth invocation at M35.0 planning-open.**
> Audit projection corrected from the initially-proposed
> 165/131/34/321 (double-counted the two shipped LenderSubmission
> endpoints) to the artifact-verified 163/131/32/321 at M35.1 and
> 163/134/29/321 at M35.2 via direct inspection of
> `M21_OPERATIONAL_SURFACE_AUDIT.md` rows #93/#94/#95. (cc)
> continues to demonstrate value: coverage-projection truthfulness
> requires the audit artifact as source of truth, not inference
> from test presence or endpoint count.

## 1. Anchor question

**Can an F&I manager record where a structured deal was submitted,
capture the lender's response, and see the resulting operational
state without leaving Dealer OS?**

M35 answers *yes for the first send-and-response loop* by:

1. Activating the shipped-but-dormant `POST /admin/lender-submissions/`
   endpoint via a truthful "Record lender submission" UI on
   In-progress F&I intake rows (LenderProgram selected via a new
   thin discovery endpoint).
2. Activating the shipped-but-dormant `PATCH /admin/lender-submissions/<pk>/`
   endpoint via a "Record lender response" / "Update lender
   response" UI on Submitted / responded rows (any-to-any status
   correction supported per M10.3 contract).
3. Extending the M33.1 CA queryset with a second subquery
   annotation (`latest_lender_submission_status`) so the F&I
   intake page displays six derived workflow states —
   `Incoming` / `In progress` / `Submitted — awaiting response` /
   `Approved` / `Counter-offer received` / `Declined` — all
   derived from verified FK events on the latest DealStructure's
   latest LenderSubmission, with deterministic tie-break ordering.

The distinction from "arbitrary F&I workflow-state extensions" is
the anchor: every derived state maps 1:1 to a verified business
event (a row in DealStructure or LenderSubmission with a specific
status); no state carries operator-inferred meaning.

## 2. Business problem this milestone solves

Per the M33 retrospective §9 and the M34 retrospective §9, after
M33.2 shipped DealStructure activation the F&I intake page could
show only two derived states: `Incoming` (no DealStructure) and
`In progress` (has DealStructure). Once an F&I manager submitted
a structured deal to a lender externally (phone / email / lender
portal), Dealer OS had no way to record that fact or to reflect
the lender's response back to the operator.

This has three operational consequences:

- **The F&I intake page understates the true state of every
  active deal.** A deal that was submitted three days ago and
  declined by the lender appears identical to a deal that was
  submitted this morning and is awaiting a response. Both show
  `In progress`. The manager has to consult external memory
  (email, sticky notes, mental model) to disambiguate.
- **No structured audit trail of lender-submission activity.**
  Which programs the dealership has submitted to, which
  responded, how they responded, and when — all lives outside
  Dealer OS. Chargeback investigations, funding disputes, and
  lender-relationship reviews cannot pull authoritative data
  from the system.
- **Every downstream F&I capability (Stipulation, Contract,
  Funding, Chargeback, Compliance, Deal Jacket, Lender Fit
  Recommendations) is architecturally gated on LenderSubmission
  being operational.** Their models + service verbs + endpoints
  are all shipped (M10.3–M10.7) but have no operator entry
  point; none can be activated until the send-and-response loop
  exists. M35 unblocks the entire downstream arc.

M35 solves all three by activating the smallest complete
send-and-response loop: create submission + record response +
derive state. Stipulation, Contract, Funding, Chargeback,
Compliance, Deal Jacket, and Lender Fit UI remain explicitly
deferred per §3 and §5.h.

## 3. Non-goals for this milestone (deferred + future candidates)

**Explicitly deferred out of M35 scope:**

- Stipulation UI (M10.4 substrate shipped; no operator entry point).
- Contract UI (M10.5 substrate shipped; no operator entry point).
- BackEndProduct UI (M10.5 substrate shipped).
- Funding UI (M10.5 substrate shipped).
- Chargeback UI (M10.6 substrate shipped; NEW C in M35 §9 candidate
  list; still pilot-evidence gated).
- ComplianceRecord UI (M10.7 substrate shipped).
- DealJacket read UI (M10.7 substrate shipped).
- Lender Fit Recommendations (D10 elevation from M33; three of
  four blockers remain — M35 does NOT deliver the fourth blocker;
  LenderProgram list projection is intentionally narrow at `{id,
  name}` and does not expose the rule / attribute data that Lender
  Fit would need).
- Structured `counter_terms` / `approval_terms` capture (JSONField
  entry deferred to future milestone if operator evidence surfaces
  on structured-terms need; UI stays free-form-notes only at M35).
- LenderProgram create UI (creation stays server-side via the
  existing `POST /admin/lender-programs/` endpoint + seed data;
  operator UX for creating new programs is separate future scope).
- Alternate-lender resubmission flow (would require iteration UX
  — creating a second LenderSubmission on the same DealStructure).
- Submission history view (would require a list endpoint scoped to
  `deal_structure` — service verb `list_submissions_for_deal_structure`
  exists but has no HTTP surface; future scope).
- Single-record GET endpoint for LenderSubmission — the M35 UI
  reconciles state via the PATCH response body (which returns the
  full projection) + refetch of the CA list after mutation. No
  new endpoint added.
- Any operator-editable `submitted_at` field on the create form
  (server records `timezone.now()` at insert; UI displays the
  returned timestamp verbatim; back-entry validation deferred
  pending operational evidence).
- Any stored `workflow_state` column, migration, or state machine.
  All six M35 derived states derive purely from the FK graph.
- Any transition constraint on LenderSubmission status. M10.3
  any-to-any contract preserved verbatim; UI supports correction
  from any status to any other status (except `pending` — excluded
  from the response form because recording pending as a response
  is nonsensical).
- PATCH or DELETE on DealStructure (M33 activation-vocabulary-
  asymmetry preserved).
- Iteration UX — creating a second DealStructure OR a second
  LenderSubmission on an already-responded CA. First-loop-only
  posture per M33 D9 extended to submission loop.
- Multi-structure UX (list-per-CA, activate, delete, iterate).
- Multi-submission management UX (list, activate, delete, iterate
  on submissions).
- F&I role extension to `admin_lead_detail`.
- Client-side monthly-payment auto-derivation.
- Full desking arithmetic.
- Pagination on `admin/credit-applications/list/`.
- Cross-lead sales-manager pending-approval queue page (unchanged
  M32 §3 deferral).
- F&I-scoped lead-context view (unchanged M32 §3 deferral).
- Retroactive modification of historical migrations (aa
  preservation).

**Non-goals carried forward unchanged from prior milestones:**

- All M34 §3, M33 §3, M32 §3, M31 §3, M30 §3, M29 §3, M28 §3,
  M27 §3, M25 §4 deferrals.
- NEW C — F&I chargeback substrate — pilot-evidence gated.
- Direct-create CA structuring branch — M33 explicit deferral;
  requires a vehicle-picker substrate.
- NEW O2 / NEW O3 — 9-milestone deferral, unchanged.
- Gated T / U / L / M.
- Deferred D (LLM router / cost caps).
- Deferred stable G (dashboard testid hardening).

## 4. Verification pass at planning-open

Eight verifications performed. **One blocking finding resolved
architecturally; two non-blocking scope corrections applied.**

### 4.1 LenderSubmission status vocabulary + defaults

CLEAN. Direct inspection of `models.py:4933-4943`:

- Constants: `LENDER_SUBMISSION_STATUS_PENDING = "pending"`,
  `LENDER_SUBMISSION_STATUS_APPROVED = "approved"`,
  `LENDER_SUBMISSION_STATUS_COUNTER = "counter"`,
  `LENDER_SUBMISSION_STATUS_DECLINED = "declined"`.
- Display labels: `"Pending"`, `"Approved"`, `"Counter-offer"`,
  `"Declined"`.
- Default value: `pending` at both model (`models.py:5080`) and
  service (`lender.py:187`).

Fixed four-value vocabulary — no `null` or unknown states possible
on a persisted row. Derived-state table at D2 covers all four.

### 4.2 Status transition constraints

CLEAN. `update_lender_submission_status` (`lender.py:231-274`):
**any-to-any transition allowed**. Docstring: "No transition
constraints at M10.3 — accepts any-to-any (operator behavior
captured as-recorded); transition rules can be locked at M10.4+
if evidence surfaces need." Model docstring (`models.py:5039-5045`)
confirms: "No transition constraints at M10.3 — the service verb
accepts any-to-any transition and operator behavior is captured
as-recorded."

M35 preserves this contract verbatim. Response form supports
`approved` / `counter` / `declined` selection (excludes `pending`
— recording pending as a response is nonsensical); after any
terminal status is recorded, the form remains available for
same-record corrections ("Update lender response").

### 4.3 Multiple submissions per DealStructure

CLEAN. LenderSubmission FK to DealStructure:
`on_delete=CASCADE, related_name="lender_submissions"`
(`models.py:5064-5068`). No unique constraint on
`(deal_structure, ...)`. Meta ordering: `("-submitted_at",
"-created_at")` (`models.py:5090-5091`). Design intent
(`models.py:5029-5031`): "subprime counter, revised terms after
stip clears, etc."

**Multiple submissions per DealStructure explicitly supported by
the substrate.** M35 does NOT expose second-submission creation
UI — the create action appears only when the derived status is
`In progress` (no existing submission on latest DS); once a
submission exists, subsequent operator actions on that DS are
status updates on the same-record. This preserves the first-loop-
only posture from M33 D9 and matches the anchor question ("record
where a structured deal was submitted" — singular for M35).

### 4.4 Deterministic latest-submission ordering

CLEAN with refinement. Model Meta ordering is
`("-submitted_at", "-created_at")`. For the M35 D2 subquery
annotation (D3-style pattern from M33 preserved), the ordering
must add an explicit `"-pk"` tiebreak for absolute determinism
under seed data with shared timestamps:

```python
.order_by("-submitted_at", "-created_at", "-pk")
```

Business meaning: `submitted_at` is authoritative business time
(operator-recorded date the submission was sent); `created_at` is
the DB write timestamp; `pk` is the ultimate deterministic
fallback. Rare in production, essential in seed data.

### 4.5 `Counter` structured-terms requirement

CLEAN. `counter_terms` is `JSONField(default=dict)`
(`models.py:5084`). A `counter` status without terms is a valid
row. Docstring (`models.py:5083`): "Both default to empty dict so
the row shape is stable regardless of status."

**Semantic:** `counter` status means the lender responded with a
counter-offer; the operator MAY record the terms as free-form
JSON, but is not required to. M35 UI language: "Counter-offer
received" — UI must clearly state that counter terms were not
captured when `counter_terms` is absent or intentionally omitted.
UI must NOT visually imply that the currently displayed
DealStructure values are the lender's counteroffer (D11 revised
per user directive; see below).

### 4.6 Projection sufficiency for truthful UI

CLEAN. `_project_lender_submission` (`views_f_and_i.py:689-702`)
returns:

```
id, deal_structure_id, lender_program_id, lender_program_name,
submitted_at, status, counter_terms, approval_terms, notes,
created_at, updated_at
```

**`lender_program_name` denormalized into the projection** —
critical for M35 UI: "Submitted to [Name]" needs no second
fetch. Complete for M35's needs. Consumers use PATCH response
body for post-update state reconciliation + CA list refetch for
derived-state reconciliation.

### 4.7 External transmission on create — DISCOVERY-RULE-CRITICAL

CLEAN. `record_lender_submission` (`lender.py:180-228`): **pure DB
insert**. No HTTP call, no webhook, no notification, no queued
task. No `signals.py` file in the project. No Celery task matches
for `LenderSubmission`.

**Endpoint records an operator action; it does NOT transmit the
application to the lender externally.** UI language MUST reflect
this. D6 + D11 lock: "Record lender submission" (past-tense
operator action); "Submitted to [Name] on [returned-timestamp]"
(post-hoc record of an operator-completed external action).
NEVER "Send to lender" / "Submit to lender" / "Submitting…" /
"Transmit" / "Contact lender" — any such phrasing falsely implies
Dealer OS makes an outbound call the substrate does not support.

R4 records this risk with a fourth defense layer beyond D11's
three-layer defense (D5 spec + Vitest anti-drift regex + Playwright
regex): a Vitest test asserts these four strings appear nowhere in
`LenderSubmissionRecordForm.tsx` or `LenderSubmissionResponseForm.tsx`.

### 4.8 Nested-annotation OuterRef compilation — TECHNICAL RISK VERIFIED

CLEAN via live shell test at planning-open. Prior codebase search
for `OuterRef` patterns (`services/vehicle_lifecycle.py:478`;
`services/f_and_i/credit_application.py:366`) surfaced only
`OuterRef("pk")` correlations to the outer table's actual column
— no existing precedent for OuterRef on an annotation.

Live shell test executed against the SQLite dev DB via
`manage.py shell -c "..."`:

```python
tenant_structures = DealStructure.objects.filter(
    credit_application_id=OuterRef('pk'),
    dealership=d,
).order_by('-created_at', '-pk')

qs = CreditApplication.objects.filter(dealership=d).annotate(
    latest_deal_structure_id=Subquery(tenant_structures.values('pk')[:1]),
)

tenant_subs = LenderSubmission.objects.filter(
    deal_structure_id=OuterRef('latest_deal_structure_id'),
    dealership=d,
).order_by('-submitted_at', '-created_at', '-pk')

qs = qs.annotate(
    latest_lender_submission_status=Subquery(tenant_subs.values('status')[:1]),
)

sql, params = qs.query.sql_with_params()  # COMPILED_OK
rows = list(qs.values(...))               # EXECUTED_OK
```

Both compilation and execution succeeded on SQLite. Django
generates equivalent ANSI-standard correlated subqueries for both
SQLite and Postgres for this pattern; Postgres tends to be more
forgiving with subquery structure than SQLite, so SQLite success
is strong (but not conclusive) evidence for Postgres. R11 records
the residual risk with mitigation: Postgres re-verification at
M35.1 open as the first §0.a checklist item, plus the 8-case
regression test coverage per D6.

**Discovered non-blocking scope correction #1 at §4.8**:
`getLenderSubmission(id)` HTTP wrapper originally proposed for D5
has no shipped endpoint (only POST + PATCH exist on
`admin/lender-submissions/`; no single-record GET). Wrapper
removed from D5. State reconciliation shifted to PATCH response
body (returns full projection) + CA list refetch.

**Discovered non-blocking scope correction #2 at §4.8**:
`submitted_at` request field originally proposed as operator-
editable in D6. Live serializer test (`manage.py shell`):
future timestamps ACCEPTED (no validation); omitted values
ACCEPTED (server defaults to `timezone.now()`). No operational
evidence in the research corpus supports operator back-entry.
Field removed from D6. Server records; UI displays returned value.

**Discovered blocking finding at §4.8**: NO list endpoint exists
for LenderProgram (only `POST /admin/lender-programs/`). The
service verb `list_active_lender_programs` (`lender.py:161-174`)
is shipped but has no HTTP surface. LenderSubmission's mandatory
`lender_program` FK has no truthful discovery mechanism from the
frontend. Per the durable lesson
`feedback_verify_fk_discoverability_before_lock.md` (M27.0 origin),
this blocks the M35 create workflow. **Resolved architecturally
via D4** — new `GET /admin/lender-programs/list/` thin wrapper on
the shipped verb, added to M35.1 backend substrate. Narrow
projection `{id, name}` per user directive; no exposure of
`contact` / `terms_summary` / `is_active` (audit-trail data not
needed for FK discovery).

---

**All eight verifications resolved.** One blocking finding
architected around via D4 (FK-discovery substrate added to M35.1).
Two non-blocking scope corrections applied before §5.b lock
(getLenderSubmission wrapper removed; submitted_at field omitted).
The z lesson (verification-driven revision cycles at planning-open)
now on invocation 4 — user directed ten planning-time corrections
after §4 tracing surfaced blocking + non-blocking findings that
would have shipped as bugs if §5.b had locked from the initial
draft. Discipline continues to demonstrate value.

## 5. Load-bearing decisions

### 5.a Target selection (locked at open)

**Milestone 35 — Lender Submission Activation: record the latest
structure's lender submission, capture the response on that same
submission, and derive the current F&I state from verified FK
events.**

Scope M35 strictly to the smallest complete send-and-response loop:
one create + one status-update + four new derived states. Activate
the shipped-but-dormant M10.3 endpoints via truthful record-vs-
transmit UI language. Preserve M33's philosophy of pure derivation
— no stored workflow state, no state machine, no schema change.

**Rationale under the primary operational-coverage lens:**

- **The F&I depth arc has strongest continuation evidence at
  M35.** M32 established the F&I intake receiver; M33 established
  the first F&I operator action (DealStructure creation). The
  natural next operational question — "Can the F&I manager
  accurately understand where every deal is in the F&I process?"
  — is directly answered by activating the send-and-response loop.
- **Every other F&I candidate remains deferred by construction.**
  NEW C (F&I chargeback substrate): still pilot-evidence gated.
  Lender Fit Recommendations (D10 elevation): three of four
  blockers remain, and M35 does NOT deliver the fourth (narrow
  LenderProgram list projection intentionally does not expose
  rule / attribute data). NEW F&I-scoped lead-context view:
  evidence-gated. NEW cross-lead pending-approval queue:
  evidence-gated. Direct-create CA structuring branch: M33
  deferred; requires vehicle-picker substrate. Iteration UX: M33
  D9 deferred. PATCH on DealStructure: M33 activation-vocabulary
  preservation.
- **Breadth reset has no stronger evidence than the F&I arc.**
  Vendor detail #43 and photo reorder #65 are wrapper-only
  polish. Broader F&I subdomain (#89–101 excl. chargeback) is
  11 uncovered endpoints — too large without operator direction,
  and choosing any one of them at random would violate the
  *Build Around Operational Problems* project rule.
- **Close-another-deferral per M34 precedent is available but
  not obviously higher-value than the arc continuation.** M34
  demonstrated deferral-close is a legitimate value-shipping
  mode when the deferral has genuine compound value; M35 could
  close (e.g.) NEW O2 or NEW O3 (9-milestone deferrals) or
  another §3 deferral, but the F&I arc's compound value is
  higher: activating LenderSubmission unblocks the entire
  downstream chain (Stipulation → Contract → BEPA → Funding →
  Chargeback → Compliance → Deal Jacket → Lender Fit).

**Alternatives considered explicitly:**

- NEW C — F&I chargeback substrate: still pilot-evidence gated.
  Would leapfrog the send-and-response loop that Chargeback
  ultimately depends on. Not selected.
- Lender Fit Recommendations: three blockers remain; M35 does
  not deliver any additional blockers (narrow LenderProgram
  projection intentional). Not selected.
- Direct-create CA structuring branch (M33 §5.h explicit
  deferral): requires vehicle-picker substrate; would leapfrog
  the sales-to-F&I bridge that already covers the primary flow.
  Not selected.
- Iteration UX (M33 D9 deferral): would enable second
  DealStructure / second LenderSubmission on the same CA;
  premature before the first-loop end-to-end works. Not selected.
- PATCH on DealStructure: activation-vocabulary-asymmetry
  preservation — creating a structure is a first-time operator
  action; editing an existing one has different meaning that
  needs its own scoping. Not selected.
- NEW O2 / NEW O3 (9-milestone deferrals): audit-refinement
  work; small compound value; tracing-first at open (still not
  performed). Not selected.
- Fresh direct-operator gaps (vendor detail #43, photo reorder
  #65, broader F&I #89–101): all small polish or too-large-
  without-direction. Not selected.
- Close another §3 deferral (per M34 precedent): NEW F&I-scoped
  lead-context view / NEW cross-lead pending-approval queue —
  both still evidence-gated; deferral-close is a legitimate mode
  but the F&I arc's compound value is higher at M35. Not
  selected.

**User confirmation at open:** target locked; ten planning-time
corrections applied before §5.b lock (verification-driven
revision cycles per z on invocation 4). Explicit user constraints
locked into §5.b–§5.h:

1. Scope strictly to the smallest complete send-and-response loop.
2. Activate LenderSubmission create + PATCH via truthful record-
   vs-transmit UI language.
3. Do not add new persistence, migration, or state machine.
4. Derive every state from verified FK events on the latest
   DealStructure's latest LenderSubmission.
5. Preserve M10.3 four-value status vocabulary verbatim (no
   collapse; no relabeling).
6. Do not expand into structured terms capture, alternate-lender
   flow, submission history, multi-submission UX, or lender
   ranking / recommendations.
7. First-loop boundary explicit: same-record status corrections
   allowed; new-submission / alternate-lender / history /
   multi-submission mgmt deferred.
8. Narrow every projection to what the workflow actually needs
   (LenderProgram list = `{id, name}`; no exposure of contact /
   terms / active-status).
9. If a proposed HTTP wrapper points at a nonexistent endpoint,
   drop the wrapper rather than adding a new endpoint out of
   scope.
10. Preserve M34.2 rerun-hygiene contract on the new journey
    (`@rerun-hygiene` tag + back-to-back double-run proof, NOT
    `--repeat-each=2`).

### 5.b Design decisions (D1–D11)

#### D1 — Backend queryset annotation: latest_deal_structure_id (M33.1 preserved)

Preserve the M33.1 D1 annotation on `list_credit_applications`
verbatim:

```python
tenant_deal_structures = DealStructure.objects.filter(
    credit_application_id=OuterRef("pk"),
    dealership=dealership,
).order_by("-created_at", "-pk")

qs = qs.annotate(
    has_deal_structure=Exists(tenant_deal_structures),
    latest_deal_structure_id=Subquery(tenant_deal_structures.values("pk")[:1]),
)
```

M35 adds no changes to D1. The dealership-scoped filter (belt
over model `clean()` + service `CrossTenantLenderSubmissionError`
suspenders) is preserved.

**Locks:** M33.1 pattern unchanged; annotation names unchanged;
tenant-scope filter preserved.

#### D2 — Backend queryset annotation: latest_lender_submission_status (NEW)

Layer a second subquery annotation on `list_credit_applications`
correlating on the D1 annotation:

```python
tenant_latest_submissions = LenderSubmission.objects.filter(
    deal_structure_id=OuterRef("latest_deal_structure_id"),
    dealership=dealership,
).order_by("-submitted_at", "-created_at", "-pk")

qs = qs.annotate(
    latest_lender_submission_status=Subquery(
        tenant_latest_submissions.values("status")[:1]
    ),
)
```

Returns `null` when no DealStructure OR when latest DealStructure
has no LenderSubmission. Consumers treat null uniformly.

**Correlation-on-annotation pattern verified live on SQLite at
§4.8** (COMPILED_OK + EXECUTED_OK). Postgres re-verification is
the first §0.a checklist item at M35.1 open. R11 mitigation
retains fallback (rewrite D2 without depending on D1's annotation
by using `NOT EXISTS(newer DealStructure)` guard).

**Locks:** correlation on `OuterRef("latest_deal_structure_id")`;
deterministic ordering `("-submitted_at", "-created_at", "-pk")`;
tenant-scope filter belt; null on missing.

#### D3 — Projection extension on `_project_credit_application_with_writeup`

Extend the projection helper with two fields:

```python
{
    ...
    "latest_deal_structure_id": app.latest_deal_structure_id,  # M33 preserved
    "latest_lender_submission_status": app.latest_lender_submission_status,  # NEW
}
```

**No `latest_lender_submission_id` field** — no consumer needs it
(M35 UI does not GET individual submissions; state reconciled via
PATCH response body + list refetch).

**Locks:** two fields (M33 preserved + NEW); no id field for
LenderSubmission.

#### D4 — NEW backend endpoint: LenderProgram list (FK-discovery substrate)

Add `GET /admin/lender-programs/list/` — thin wrapper on shipped
`list_active_lender_programs`. Route name
`admin-lender-program-list`. `_M101_PERMS` (zero-drift preserved).

**Narrow projection** per user directive:

```python
{
    "lender_programs": [
        {"id": program.pk, "name": program.name}
        for program in programs
    ]
}
```

Server filters `is_active=True` implicitly (matches shipped
verb). **NO exposure of `contact`, `terms_summary`, or
`is_active`** — audit-trail data not required for FK discovery;
extra exposure violates principle-of-least-surface and would
falsely broaden Lender Fit Recommendations blocker-completion
scope.

**Resolves §4.8 blocking finding** (FK discoverability gap on
LenderSubmission's mandatory `lender_program` FK).

**Locks:** route path; route name; permission class; narrow
`{id, name}` projection; active-only server filter.

#### D5 — Frontend `fAndIApi.ts` extensions

Type extensions:

- `CreditApplicationProjection` gains
  `latest_lender_submission_status: 'pending' | 'approved' |
  'counter' | 'declined' | null` (M33 preserved fields unchanged).
- NEW `LenderProgramSelectorProjection = {id: number; name: string}`
  (narrow — matches D4 projection).
- NEW `LenderSubmissionProjection` mirroring `_project_lender_submission`
  fields (full — used for post-mutation state).
- NEW `RecordLenderSubmissionRequest = {deal_structure_id: number;
  lender_program_id: number; notes?: string}`. **NO
  `submitted_at`; NO `status` override.**
- NEW `UpdateLenderSubmissionStatusRequest = {status: 'approved' |
  'counter' | 'declined'; notes?: string}`. `pending` excluded
  from the type — response form does not surface it.

Three typed wrappers:

- `listLenderPrograms(): Promise<LenderProgramSelectorProjection[]>`
- `recordLenderSubmission(req: RecordLenderSubmissionRequest):
  Promise<LenderSubmissionProjection>`
- `updateLenderSubmissionStatus(id: number, req:
  UpdateLenderSubmissionStatusRequest):
  Promise<LenderSubmissionProjection>`

**`getLenderSubmission` REMOVED** — no GET single-record endpoint
exists (verified §4.8). PATCH response body carries full
projection; CA list refetch handles derived-state reconciliation.

**Locks:** three wrappers only; four types (two request, one full
projection, one selector projection); no getter; no submitted_at;
no status override on create; response type excludes pending.

#### D6 — NEW component `LenderSubmissionRecordForm.tsx`

Fields:

- LenderProgram select (populated from `listLenderPrograms()` on
  mount).
- Optional `notes` textarea.
- **NO `submitted_at` field** (server records; §4.8 correction).

Submit disabled until a LenderProgram is selected.

**UI language contract** per §4.7 + user directive:

- Header: "Record lender submission" (past-tense operator action).
- Button: "Record submission".
- Success confirmation: "Submitted to [Name] on [returned-
  timestamp]" — displays returned `submitted_at` +
  `lender_program_name` from POST response body verbatim.
- **PROHIBITED strings anywhere in the file**: "Send to lender",
  "Send", "Submit to lender", "Transmit", "Contact lender",
  "Submitting…". R4 fourth-defense-layer Vitest test asserts
  string absence.

Financial-language contract from M33 D5 preserved: no "lender-
approved" / "lender-committed" / "actual" (D11 refined; see below).

**Locks:** two fields (LenderProgram select + notes); UI language
contract exact wording; prohibited-strings list; submit-disabled
gate.

#### D7 — NEW component `LenderSubmissionResponseForm.tsx`

Fields:

- Status radio: `approved` / `counter` / `declined` (`pending`
  excluded — initial state on create; recording pending from
  response UI is nonsensical).
- Optional `notes` textarea.
- **`counter_terms` and `approval_terms` NOT captured** —
  structured entry deferred to future milestone (M35 §3).

**UI language contract per current status** (per user directive
#3 + #4 — same-record status update, not "another response"):

- Current status = `pending` → header "Record lender response";
  button "Record response".
- Current status ∈ `{approved, counter, declined}` → header
  "Update lender response"; button "Update response".

Any-to-any correction supported per M10.3 contract (§4.2). No
transition constraint enforced by UI.

**Locks:** three-value status radio (pending excluded); UI
language mode-conditional (record vs update); no structured terms
capture; any-to-any preserved.

#### D8 — `DealerFandIIncoming.tsx` extension: chip 2 → 6 states + state-conditional row actions

Chip states (per derived-state table below):

| latest_ds | latest_sub.status | Chip label | Chip color | Testid suffix |
|---|---|---|---|---|
| None | — | Incoming | amber (M33 unchanged) | `incoming` |
| exists | None | In progress | blue (M33 unchanged) | `in-progress` |
| exists | `pending` | Submitted — awaiting response | slate (NEW) | `submitted` |
| exists | `approved` | Approved | green (NEW) | `approved` |
| exists | `counter` | Counter-offer received | purple (NEW) | `counter` |
| exists | `declined` | Declined | red (NEW) | `declined` |

Three-signal a11y pattern from M33 preserved: `data-testid` +
`aria-label` + visible label.

Row actions state-conditional:

- **Incoming**: "Start structuring" (M33 unchanged; direct-
  create CAs still render documented affordance per M33 R1).
- **In progress**: "Open structure" (M33) + "Record lender
  submission" (NEW).
- **Submitted (pending)**: "Open structure" + "Record lender
  response" (NEW).
- **Approved / Counter-offer received / Declined**: "Open
  structure" + "Update lender response" (NEW; per D7 same-record
  correction).

**First-loop boundary explicit** (per user directive #4):

- Allowed: same-record status update on the latest LenderSubmission.
- Deferred: create a second LenderSubmission on the same
  DealStructure (iteration); select an alternate lender for
  resubmission; display submission history; manage multiple
  submissions per DealStructure.

Inline panel state (form-vs-null); refetch CA list after
successful create OR update.

**Locks:** six chip states with testid suffix + color + label;
state-conditional row actions; first-loop boundary in code
comments referencing D7 + D8 wording.

#### D9 — NEW Playwright spec + rerun-hygiene contract

NEW spec `acceptance/journeys/f_and_i_manager/fandi_submission_response_loop.spec.ts`.
Tagged `@rerun-hygiene` per M34.2 contract.

Journey shape (14–18 steps):

1. Login as `f_and_i_manager` persona.
2. Navigate to F&I intake page.
3. Locate Submission Sasha's CA row.
4. Pre-flight: verify chip = "In progress" (Sasha starts with an
   existing DS, no submission).
5. Click "Record lender submission" row action.
6. Select LenderProgram "Yuma Community Bank" from the dropdown.
7. Fill notes = "M35.2 journey submission".
8. Assert record button text = "Record submission" (never "Send").
9. Submit.
10. Assert chip flips to "Submitted — awaiting response".
11. Click "Record lender response" row action.
12. Assert response header = "Record lender response" (while
    status pending).
13. Select `approved`.
14. Fill notes = "M35.2 journey approval".
15. Submit.
16. Assert chip flips to "Approved".
17. Click "Update lender response" (same row; status now
    terminal).
18. Assert header text = "Update lender response" (correction
    mode).

Truthfulness assertions per user directive #9:

- Create button text regex-asserted as "Record lender submission"
  or "Record submission"; strings "Send", "Transmit", "Submit to
  lender", "Contact lender", "Submitting…" MUST NOT appear
  anywhere in either form or its buttons (double-scope: form DOM
  + record view DOM).
- Pending state chip label = "Submitted — awaiting response"
  (visible + aria-label + testid `incoming-row-status-submitted-<pk>`).
- Response header text differentiation: "Record lender response"
  while pending, "Update lender response" after terminal.
- Approved chip appears after recording the response.
- Proposed DealStructure values NEVER labeled "lender-approved
  terms" / "approved terms" — regex assertion across form + read
  view (D11 preserved + refined).
- Financial-language regex from M33 D5 preserved.

**M35.2 proof mechanism** per user directive #9 + M34.2 §0.a
correction: back-to-back `npx playwright test --grep "@rerun-hygiene"`
executions (setup runs each invocation; seeds re-fire; invariants
restore). **NOT `--repeat-each=2`.** Both runs must pass. Timings
recorded in M35.2 handoff §7.

**Locks:** new spec (not extension of M33); `@rerun-hygiene`
tag; 6 truthfulness assertions verbatim; back-to-back double-
run proof mechanism.

#### D10 — NEW idempotent seed: Submission Sasha fixture

New file
`backend/dealer_ai/management/commands/seed_journey_fandi_submission_response.py`.

Provisions:

- Distinct four-square identity from Intake Iris (M32.3) + Structure
  Sam (M33.2). Suggested tag: "Submission Sasha".
- Approved + handed-off DealWriteup.
- Paired CreditApplication.
- Existing DealStructure (fresh — not shared with Structure Sam;
  distinct sale price / financing terms so accidental cross-fixture
  matches fail loudly).
- One active LenderProgram named "Yuma Community Bank" (or
  Copper-Canyon-consistent name).
- NO existing LenderSubmission on the DealStructure.

Seed asserts + restores pre-flight invariants across mutate →
re-seed cycles per M34 (ff) contract:

1. DealStructure exists on the CA.
2. LenderProgram exists AND `is_active=True`.
3. NO LenderSubmission on the DealStructure (idempotently deletes
   any created by a prior run — matches M34 D2 / D3 / D4
   pattern).

`M20_ACCEPTANCE_DB` env-guard match (per M34 seed-guard pattern).

`login.setup.ts` `SEED_COMMANDS` extended with the new seed
command.

**Locks:** file path; fixture identity distinct from Iris + Sam;
three rerun invariants; `M20_ACCEPTANCE_DB` guard.

#### D11 — Financial-language contract refinement (revised per user directive)

Locked verbatim per user directive #10:

> Before a verified LenderSubmission response exists, UI language
> may describe only operator-recorded submission activity and
> proposed structure values. After `status="approved"` is
> recorded, Dealer OS may describe the submission or deal
> workflow state as approved, but may not describe individual
> structure values as lender-approved terms unless verified
> approval-term data is captured and displayed.

M35 omits `approval_terms` capture (per §3), so the UI may state:

- "Approved" (chip label).
- "Submission approved" (headline).
- "Approved by [program name]" (using the returned
  `lender_program_name` from PATCH response body).

The UI must NOT label the displayed proposed DealStructure values
themselves as approved terms.

Likewise, "Counter-offer received" is truthful, but the UI must
clearly state that counter terms were not captured when
`counter_terms` is absent or intentionally omitted (M35 always
omits capture). UI must NOT visually imply the currently
displayed DealStructure values are the lender's counteroffer.

**Four-layer defense:**

1. D11 spec (this section).
2. Vitest anti-drift regex assertion on both new forms (record +
   response).
3. Playwright regex assertion on both forms + the read view.
4. Vitest test asserts the prohibited strings ("Send to lender",
   "Send", "Submit to lender", "Transmit", "Contact lender",
   "Submitting…") appear nowhere in either component file
   (R4 fourth defense layer).

**Locks:** revised rule verbatim; four-layer defense; prohibited-
strings list.

### 5.c Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | D2 subquery correlated on `latest_deal_structure_id` returns null when D1 annotation is null; test class asserts 0 / 1 / N=3 submissions per structure + tie-break under shared `submitted_at` + shared `submitted_at`+`created_at` | Verified working | Low | D6 eight-case regression test coverage; §4.8 live shell verification |
| R2 | LenderProgram selector accidentally lists inactive programs | Low | Low | D4 server filters `is_active=True`; test asserts inactive programs excluded from selector response |
| R3 | Concurrent submission-create races — two operators recording the same submission for the same DS. Not a data-integrity issue (no unique constraint per business intent) but could confuse UI | Very Low | Low | Refetch CA list after successful create; UI displays latest submission's `lender_program_name` from PATCH response body |
| R4 | UI language drift toward "Send to lender" during copy revision | Med | High | D11 four-layer defense: D5 spec + Vitest anti-drift regex + Playwright regex + Vitest string-absence test on both component files |
| R5 | Multi-DealStructure scenarios where operator records a submission on an outdated DS | None (by construction) | Med | `latest_deal_structure_id` annotation prevents this — record form is only reachable via the latest-DS row action (D8 gates by chip state) |
| R6 | PATCH endpoint accepts any-to-any (per §4.2) — operator could accidentally set `approved → declined` via response form. Not a bug (matches M10.3 contract); UI supports correction via same-record update | Low (matches operator behavior) | Low | UI-side: response form only offers `approved / counter / declined` (excludes `pending`); post-response the form remains available for corrections; operator behavior captured as-recorded per M10.3 |
| R7 | Journey independence — Submission Sasha fixture must not collide with Structure Sam or Intake Iris | Very Low | Med | Distinct fixture identity per D10 (M33 R7 + M32.3 D11 precedents); regression test asserts all three fixtures coexist |
| R8 | Rerun-hygiene — the response Playwright journey mutates submission state; second run must find seed invariant restored | Low | High | D10 seed deletes and recreates Submission Sasha state including any submissions from prior journey run; M34 (ff) contract preserved; D9 back-to-back double-run proof mechanism validates this at M35.2 close |
| R9 | Audit projection truthfulness (cc — load-bearing-across-three-milestones after M34) | Low | Med | Projections locked from direct inspection of `M21_OPERATIONAL_SURFACE_AUDIT.md` rows #93/#94/#95: M35.1 close = 163/131/32/321 (+1 total, +1 backend-only); M35.2 close = 163/134/29/321 (3 endpoints move backend-only → covered). NO inference from test coverage |
| R10 | Rerun-safety against shared state (ff — M34.0 D8, awaiting first re-application) | Very Low | High | D9 + D10 preserve M34.2 contract verbatim: `@rerun-hygiene` tag + back-to-back double-run proof mechanism (NOT `--repeat-each=2`); Submission Sasha seed idempotent from first shipping day. First re-application elevates (ff) to load-bearing-across-two-milestones |
| R11 | Nested-annotation OuterRef compilation on Postgres (SQLite verified §4.8 live) | Low (SQLite success is strong evidence for Postgres — Django generates equivalent ANSI-standard correlated subqueries) | High if fails | §0.a first item at M35.1 open: Postgres compilation + execution re-verification via same live-shell test pattern. Fallback if Postgres fails: rewrite D2 without depending on D1 annotation — use `NOT EXISTS(newer DealStructure)` guard inside the LenderSubmission subquery filter. Fallback preserves derived-state semantics; D6 tests unchanged |

### 5.d Verifications completed at planning-open

Eight verifications (§4.1–§4.8 above) all resolved:

- §4.1 Status vocabulary + defaults: CLEAN.
- §4.2 Transition constraints: CLEAN — any-to-any preserved.
- §4.3 Multiple submissions per DealStructure: CLEAN — explicitly
  supported, but M35 UI does not surface second-submission
  creation.
- §4.4 Deterministic latest-submission ordering: CLEAN with
  refinement (add explicit `-pk` tiebreak).
- §4.5 `Counter` structured-terms: CLEAN — not required; M35 UI
  omits capture and states so clearly.
- §4.6 Projection sufficiency: CLEAN — `lender_program_name`
  denormalized; complete for M35 needs.
- §4.7 External transmission on create: CLEAN — pure DB insert;
  UI language contract locked (D6 + D11 + R4).
- §4.8 Nested-annotation OuterRef compilation + discovered scope
  corrections: verified working on SQLite (Postgres re-verify at
  M35.1 open per R11); one blocking finding resolved via D4 (FK
  discoverability); two non-blocking corrections applied
  (getLenderSubmission wrapper removed; submitted_at field
  omitted).

Ten planning-open corrections applied by user directive
before §5.b lock (z on invocation 4). Discipline continues to
demonstrate value.

### 5.e Phase / increment structure

**Two-increment split** — backend / frontend boundary matching
M33 shape. Both revertable independently; no migrations; no
schema changes.

#### M35.1 (SESSION_217) — Backend: FK-discovery endpoint + subquery annotations + projection extension

**DoD exception path invocation #12.**

- **§0.a first item at M35.1 open**: Postgres OuterRef re-
  verification via `manage.py shell` live-test (mirrors §4.8
  SQLite test). If Postgres compilation OR execution fails,
  apply R11 fallback (rewrite D2 without depending on D1
  annotation) as §0.a M35.1 amendment before proceeding to D4.
- **NEW endpoint** (D4): `GET /admin/lender-programs/list/` in
  `views_f_and_i.py` + URL route in `urls.py`. Named
  `admin-lender-program-list`. Narrow `{id, name}` projection.
  `_M101_PERMS`.
- **Queryset annotation extensions** (D1 + D2): extend
  `list_credit_applications` in
  `services/f_and_i/credit_application.py` with the M33-preserved
  D1 annotation + new D2 annotation.
- **Projection extension** (D3): extend
  `_project_credit_application_with_writeup(app)` in
  `views_f_and_i.py` with the two new fields.
- **Regression tests** (~20–25 tests across 2 new / extended
  files):
  - New `test_m351_lender_program_list.py` — endpoint permission
    matrix (5 negative + 2 positive per M33.1 pattern); response
    projection shape (narrow `{id, name}`; no
    contact/terms/is_active fields); active-only filter; empty-
    tenant + N-programs cases.
  - New `test_m351_lender_submission_status_annotation.py` — 8-
    case matrix per R11: no DealStructure; DealStructure with no
    submissions; one submission (pending); multiple submissions
    (latest = approved); shared `submitted_at` tie-break; shared
    `submitted_at`+`created_at` tie-break; multiple
    DealStructures where older has approved submission but
    latest has none (proves current-iteration semantic); cross-
    tenant rows via direct ORM bypass excluded (belt-and-
    suspenders per M33.1 pattern).
  - Extend `test_m331_deal_structure_read.py` OR add new
    `test_m351_credit_application_projection.py` — CA list
    projection carries new `latest_lender_submission_status`
    field; null-safe when no annotation match.
- **No new service verb.** D2 annotation uses ORM directly (same
  pattern as M33.1 D1); D4 endpoint reuses shipped
  `list_active_lender_programs` verb.
- **No new URL beyond `admin/lender-programs/list/`.**
- **No new permission class** — zero-drift streak 38 → 39.
- **No migration; no schema change.**
- **Backend baseline projection:** 5,021 → **~5,041** pass at
  M35.1 close (+20 tests).
- **Audit projection at M35.1 close: 163 / 131 / 32 / 321**
  (+1 endpoint total; +1 backend-only; covered unchanged;
  service verbs unchanged). Locked from direct artifact
  inspection per (cc) discipline.
- **Two-source agreement gate** at M35.1 close: run
  `python3 -m dealer_ai.scripts.audit_operational_surface`;
  confirm 163/131/32/321.

#### M35.2 (SESSION_218) — Frontend: API-client + components + status chip + Playwright + seed

**DoD satisfied directly** via new `fandi_submission_response_loop`
Playwright journey.

- **API-client extensions** (D5) in `fAndIApi.ts`: types +
  three wrappers (`listLenderPrograms`,
  `recordLenderSubmission`, `updateLenderSubmissionStatus`).
- **NEW component**
  `frontend/src/components/f-and-i/LenderSubmissionRecordForm.tsx`
  per D6 + accompanying `.test.tsx` covering: submit disabled
  until LenderProgram selected; POST request shape; success
  handling with lender_program_name display; language-contract
  regex assertions (D11 + R4); no submitted_at field rendered;
  no prohibited strings.
- **NEW component**
  `frontend/src/components/f-and-i/LenderSubmissionResponseForm.tsx`
  per D7 + accompanying `.test.tsx` covering: three-value radio
  (pending excluded); header language differentiation (record vs
  update); PATCH request shape; language-contract regex
  assertions; no counter_terms/approval_terms fields; any-to-any
  update supported.
- **Chip + row-action extension** (D8) in
  `DealerFandIIncoming.tsx` + `.test.tsx` extension covering: 6
  chip states with testid + aria-label + visible label; state-
  conditional row actions; first-loop boundary comments; refetch
  after mutation.
- **NEW Playwright spec** (D9) at
  `acceptance/journeys/f_and_i_manager/fandi_submission_response_loop.spec.ts`
  tagged `@rerun-hygiene` with 6 truthfulness assertions
  verbatim.
- **NEW idempotent seed** (D10) at
  `backend/dealer_ai/management/commands/seed_journey_fandi_submission_response.py`
  provisioning Submission Sasha fixture with 3 rerun invariants.
- **`login.setup.ts`** — extend `SEED_COMMANDS` list with the
  new seed.
- **Reuses shipped M32.3 `f_and_i_manager` persona**; no new
  persona work.
- **M35.2 proof mechanism at close** (per D9 + M34.2 §0.a
  correction): back-to-back `npx playwright test --grep
  "@rerun-hygiene"` — 4 tags total after M35.2 (M34's 3 +
  M35's 1) — both runs must pass. Timings recorded in M35.2
  handoff §7.
- **Vitest baseline projection:** 402 → **~430** pass at M35.2
  close (+28 tests across 4 new / extended files).
- **Acceptance suite projection:** 25 → **26** spec files;
  32 → **33** tests; runtime ≤37s (budget +2s for new spec).
- **Audit projection at M35.2 close: 163 / 134 / 29 / 321**
  (three endpoints move backend-only → covered: new list
  endpoint + two shipped-but-dormant LenderSubmission endpoints).
- **Two-source agreement gate** at M35.2 close: run audit;
  confirm 163/134/29/321.

Rollback order at M35 close (reverse ship order):

- **M35.2 revert first** — frontend + Playwright + seed +
  acceptance workspace. Backend M35.1 surface stays valid (safe
  — annotations are query-only; new list endpoint is additive
  and unused by any consumer without M35.2).
- **M35.1 revert second** — backend commit. Removes list
  endpoint + annotations + projection extension + regression
  tests. Baseline returns to M34.2 close.

M35.1 revertable standalone (M35.2 doesn't depend on it
structurally — well, actually M35.2 requires D1+D2+D3+D4 to
function, so if M35.2 shipped but M35.1 were reverted M35.2 would
break). Shipping order enforces backend-before-frontend for
review clarity and safe rollback.

### 5.f DoD compliance check (M21.0 §5.f Option B)

- **M35.1 backend-only** — invocation #12 of exception path.
  §3 documents: FK-discovery endpoint + queryset annotations +
  projection extension have zero operator-visible behavior. No
  shipped operator flow changes.
- **M35.2 frontend + Playwright** — direct satisfaction. New
  `fandi_submission_response_loop.spec.ts` covers the full send-
  and-response loop end-to-end.

M35 is the twelfth invocation of the exception path across
customer-facing milestones (M26 + M27.1 + M28.1 + M29.1 + M30.1
+ M31.1 + M32.1 + M33.1 + M34.1 + M34.2 + M35.1). Pattern firmly
established at twelve invocations.

### 5.g Rollback plan

- **M35.1 rollback:** revert the single commit. New list
  endpoint route + view + tests removed; queryset annotations
  removed; projection returns to M34.2 shape. Backend baseline
  returns to 5,021 pass. Audit returns to 162 / 131 / 31 / 321.
  Frontend + acceptance unchanged (nothing yet depends on the
  M35.1 surface).
- **M35.2 rollback:** revert the single commit. Two components
  + chip extension + Playwright spec + seed + API-client
  extensions removed. Vitest returns to 402 pass. Acceptance
  returns to 25 spec files / 32 tests. Backend + M35.1 surface
  stays valid but unused (safe — additive endpoint + query-only
  annotations).
- **Reverse-order rollback discipline** (M35.2 → M35.1) matches
  M33/M34 shape.

Fixture rollback: Submission Sasha seed command deletion via
M35.2 revert; existing acceptance DB state not corrupted (the
seed is idempotent and only mutates its own scoped rows).
`login.setup.ts` `SEED_COMMANDS` list reverts to M34.2 shape.

### 5.h Non-goals for M35

- ❌ Do NOT ship Stipulation / Contract / BEPA / Funding /
  Chargeback / Compliance / DealJacket UI. M10.4–M10.7 substrate
  stays dormant beyond LenderSubmission.
- ❌ Do NOT ship Lender Fit Recommendations UI. Three of four
  blockers remain; the narrow `{id, name}` LenderProgram list
  projection is INTENTIONAL and does not deliver the fourth
  blocker.
- ❌ Do NOT ship structured `counter_terms` or `approval_terms`
  capture. Free-form JSONField stays server-side only.
- ❌ Do NOT ship LenderProgram create UI (creation stays server-
  side via existing endpoint + seed).
- ❌ Do NOT ship an alternate-lender resubmission flow (requires
  iteration UX).
- ❌ Do NOT ship a submission history view (would require a
  list endpoint scoped to deal_structure).
- ❌ Do NOT add a single-record GET endpoint for LenderSubmission
  (state reconciled via PATCH response body + list refetch;
  §5.h explicit).
- ❌ Do NOT add an operator-editable `submitted_at` field on the
  create form. Server records; UI displays returned value.
- ❌ Do NOT collapse the M10.3 four-value status vocabulary. UI
  preserves `pending` / `approved` / `counter` / `declined`
  verbatim.
- ❌ Do NOT introduce a stored `workflow_state` column, state
  machine, or transition constraint.
- ❌ Do NOT ship PATCH or DELETE on DealStructure (M33
  activation-vocabulary-asymmetry preserved).
- ❌ Do NOT ship iteration UX (second DealStructure OR second
  LenderSubmission on already-responded CA; first-loop-only
  posture preserved and extended to submission loop).
- ❌ Do NOT ship multi-structure or multi-submission management
  UX.
- ❌ Do NOT extend F&I role access to `admin_lead_detail`.
- ❌ Do NOT add client-side monthly-payment auto-derivation OR
  full desking arithmetic.
- ❌ Do NOT add pagination on
  `admin/credit-applications/list/`.
- ❌ Do NOT ship cross-lead sales-manager pending-approval queue
  (unchanged M32 §3 deferral).
- ❌ Do NOT ship F&I-scoped lead-context view (unchanged M32 §3
  deferral).
- ❌ Do NOT expose `contact` / `terms_summary` / `is_active` via
  the D4 list endpoint (narrow `{id, name}` projection locked).
- ❌ Do NOT modify historical migrations (aa preservation).
- ❌ Do NOT modify M33 Intake Iris / Structure Sam OR M34 rerun-
  hygiene seed contracts. Submission Sasha fixture is
  additively-added, fully independent from all three.
- ❌ Do NOT use `--repeat-each=2` as the rerun-hygiene proof
  mechanism. Back-to-back `--grep "@rerun-hygiene"` invocations
  per M34.2 §0.a correction.
- ❌ Do NOT propose changes to any M36+ candidate in this
  milestone; M35 retrospective §9 will surface the M36 candidate
  list at close.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_34_RETROSPECTIVE.md` §9 (M35 candidate
   list origin + F&I depth-arc standing question)
6. **`docs/roadmap/MILESTONE_35_PLANNING.md`** (this document —
   governing contract for M35)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` rows #93/#94/#95
   (three lender endpoints classified defer-candidate-O2 at M34
   baseline — source of truth for §5.e audit projections)
8. `docs/roadmap/MILESTONE_10_PLANNING.md` §1.3 (LenderProgram +
   LenderSubmission substrate contract — any-to-any transition;
   four-value status; `counter_terms`/`approval_terms` JSONField
   free-form)
9. `docs/roadmap/MILESTONE_33_PLANNING.md` §5.b D1 + D3 (subquery-
   annotation pattern preserved verbatim at D1; extended at D2)
10. `docs/roadmap/MILESTONE_33_PLANNING.md` §5.b D5 (financial-
    language contract three-layer defense — extended to four
    layers at M35 D11 + R4)
11. `docs/roadmap/MILESTONE_34_PLANNING.md` §5.b D7 + D10
    (rerun-hygiene contract preserved verbatim; Submission Sasha
    seed idempotent from first shipping day)
12. `docs/CAPABILITY_MATRIX.md` §7ι (M34 shipped surface); §7κ
    added at M35 close
13. `docs/handoffs/SESSION_215_m34_inc2_acceptance.md` (M34.2
    shipped + M34 close-out fold)
14. Memory record
    `feedback_verify_fk_discoverability_before_lock.md` (M27.0
    origin — applied at §4.8 for LenderProgram FK discovery;
    resolved via D4)
15. Memory record
    `feedback_playwright_as_operational_contract.md` (M33 D8
    strengthening invocation; M34 preserves; M35 extends journey
    coverage to send-and-response loop)
16. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — no shared helper between M33's DealStructure
    forms and M35's LenderSubmission forms; duplicate small stable
    domain logic instead)
17. Memory record `feedback_terminal_output_discipline.md`
    (governs implementation-session output shape)
