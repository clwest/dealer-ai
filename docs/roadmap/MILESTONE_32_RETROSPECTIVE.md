---
title: "Milestone 32 — Deal Writeups: Sales-Manager-to-F&I Handoff — Retrospective"
status: historical
type: retrospective
milestone: 32
milestone_status: shipped
generated: 2026-08-04
generated_at_session: SESSION_209 (M32.3 close + close-out fold)
milestone_name: "Deal Writeups: Sales-Manager-to-F&I Handoff (writeup CRUD substrate + sales-manager UI + F&I intake queue + provenance-FK migration)"
increments_shipped: [0, 1, 2, 3]
close_out_fold: true
sessions: [206, 207, 208, 209]
commits_at_close: 8
---

# Milestone 32 — Deal Writeups: Sales-Manager-to-F&I Handoff — Retrospective

> Milestone 32 opened at SESSION_206 M32.0 planning under the
> durable primary operational-coverage lens, evaluated against
> the M31 §9 breadth-vs-depth standing question. After five
> consecutive planning-time selections in the accounting/
> templates domain (M27.1 → M31), M32 chose breadth (fresh
> direct-operator gap in sales-to-F&I workflow) over depth
> (NEW C F&I chargeback remained pilot-evidence-gated at M32.0
> open). First break out of the accounting/templates domain
> since M27.1.
>
> M32.1 shipped the backend substrate at SESSION_207 (writeup
> list + detail endpoints + CA list endpoint + `credit_application.deal_writeup`
> OneToOneField migration + `DealWriteupAlreadyLinkedError`
> service-layer guard + `hand_off_to_fandi` extended to set FK
> in existing atomic block + 62 new tests including mandatory
> `test_writeup_cannot_link_to_multiple_credit_applications`
> exercising all three defense layers). M32.2 shipped the
> sales-manager UI + sales-side Playwright at SESSION_208 (5
> new `salesApi.ts` wrappers, "UI deferred" comments removed,
> 3 new co-located components, LeadDetailModal wiring, 35 new
> Vitest tests, new `sales-manager-writeup-handoff` describe
> block proving the full sales-side workflow through the real
> UI with D5-revised + D6 irreversibility copy verbatim).
> M32.3 shipped the F&I intake UI + F&I-side Playwright + new
> `f_and_i_manager` persona + M32 close-out fold at SESSION_209
> (new persona addition to personas.ts + login.setup.ts +
> playwright.config.ts + idempotent `seed_journey_fandi_intake_receipt`
> command; new `fetchCreditApplications` wrapper; new
> `DealerFandIIncoming.tsx` page with non-navigational rows;
> 23 new Vitest tests; new `fandi-intake-receipt` describe
> block using pre-seeded `Intake Iris` fixture fully
> independent of M32.2 fixture).
>
> **The anchor business question** — *Can a sales manager
> create a deal writeup, review and approve it, and hand it
> off to F&I such that the F&I team receives a complete,
> actionable incoming credit application with unambiguous
> provenance — all through Dealer OS?* — is answered **yes**.
> Two independently-deterministic Playwright journeys cover
> the full sales-to-F&I workflow: the M32.2 sales journey
> proves create → Pending → Approve → Approved → Send-to-F&I
> → Handed off through the real UI; the M32.3 F&I journey
> proves the resulting credit application appears in the F&I
> intake queue with full inline triage context (four-square
> terms + attribution + hand-off timestamp + M11.3 handoff
> notes prefix).
>
> M32 realized **three firsts** in a single milestone: (1)
> first F&I-role-gated list endpoint (M32.1
> `admin_credit_application_list`), (2) first schema-level
> pairing constraint at the DealWriteup ↔ CreditApplication
> seam (M32.1 nullable OneToOneField with three-layer defense),
> (3) first customer-facing milestone since M11 to ship across
> three increments (scope-driven per M32.0 §4 verification
> findings — three blocking findings + two inaccessibility
> findings forced M32.1 substrate + M32.2 sales UI + M32.3
> F&I UI + persona addition). Also the first milestone since
> M20 to add a new Playwright persona.

## 1. Planned scope

Per `MILESTONE_32_PLANNING.md` §5.a locked at open: **NEW Deal
Writeups: Sales-Manager-to-F&I Handoff**.

Three-increment split per §5.e (scope-driven):

- **M32.1 (SESSION_207) — Backend substrate + provenance-FK
  migration.** 3 new endpoints (writeup list + detail + CA
  list); 3 new service verbs; 1 new error class; 1 migration
  (nullable OneToOneField); ~51 tests planned including
  mandatory pairing-uniqueness test. DoD exception path
  invocation #7.
- **M32.2 (SESSION_208) — Sales-manager UI + sales-side
  Playwright.** 5 new `salesApi.ts` wrappers; 3 new co-located
  components; LeadDetailModal wiring; ~34 Vitest tests; new
  sales-side Playwright describe block. DoD satisfied directly.
- **M32.3 (SESSION_209) — F&I intake UI + F&I-side Playwright
  + new f_and_i_manager persona + M32 close-out fold.** New
  persona per D11; new `fetchCreditApplications` wrapper; new
  `DealerFandIIncoming.tsx` page; ~20 Vitest tests; new
  F&I-side Playwright describe block. DoD satisfied directly.

## 2. What actually shipped

### M32.0 (SESSION_206 · planning-only)

Full active memo at `docs/roadmap/MILESTONE_32_PLANNING.md`
(1,766 lines). All §5.b–§5.h decisions locked (D1–D11 through
two verification-driven revision rounds). Three blocking
findings + two inaccessibility findings resolved architecturally
before scope-lock:

1. **Writeup pk not discoverable** (M11.3 shipped no list or
   detail endpoint). → Resolved by D1 + D2.
2. **Downstream F&I UI receiver absent** (zero frontend refs
   to CreditApplication; no list endpoint; DealerFandIDeals
   is contract-keyed). → Resolved by D3 + D8.
3. **CA↔writeup pairing non-deterministic** (only link was
   text prefix in `notes`; one lead → N writeups → N CAs).
   → Resolved by D9-revised² nullable OneToOneField with
   three-layer defense.
4. **F&I role can't access `admin_lead_detail`** (sales-role-
   gated). → Resolved by D8-revised non-navigational F&I
   intake rows.
5. **Advisor viewers can't open `LeadDetailModal`** at all
   (modal transitively manager-gated). → Resolved by
   D4-revised² no advisor tab treatment.

Handoff at `docs/handoffs/SESSION_206_m32_inc0_planning.md`.

### M32.1 (SESSION_207 · backend substrate + provenance-FK migration)

- **Migration `0051_m32_credit_application_deal_writeup_fk.py`**
  — nullable `OneToOneField` `CreditApplication.deal_writeup`
  (SET_NULL, related_name="credit_application"). Reversible.
  Existing CAs + direct-create CAs stay NULL. Migration
  docstring records the D9-revised² rationale + three-layer
  defense + reverse-migration behavior.
- **Service layer** (`services/f_and_i/credit_application.py`):
  new `DealWriteupAlreadyLinkedError` error class; extended
  `record_credit_application` signature with optional
  `deal_writeup` kwarg + same-tenant guard + already-linked
  guard raised before DB write; new `list_credit_applications`
  verb (composable `intake` / `lead` / `since` filters; intake
  uses `.exclude(deal_structures__contracts__isnull=False).distinct()`
  for pre-contract CAs).
- **Service layer** (`services/deal_writeups/deal_writeup.py`):
  extended `hand_off_to_fandi` to pass `deal_writeup=writeup`
  inside its existing atomic block (2-line change; docstring
  extended with three-layer defense summary); new derived-state
  constants; new `get_deal_writeup` + `list_deal_writeups`
  verbs (state derived from timestamp presence at query time;
  unknown state raises ValueError → 400 at endpoint).
- **Endpoints:** `admin_deal_writeup_list` (GET) +
  `admin_deal_writeup_detail` (GET, pk) with fail-explicit
  D1 query parsing on `_M113_PERMS`; `admin_credit_application_list`
  (GET) with fail-explicit D3 query parsing (`intake=true`
  only accepted; `intake=false` returns 400 per §5.h) on
  `_M101_PERMS` — **first F&I-role-gated list endpoint**.
- **URLs:** 3 new patterns on distinct `/list/` sibling paths
  preserving M10.1 + M11.3 shipped URL config verbatim.
- **Model docstring updates** on `CreditApplication` +
  `DealWriteup` recording M32.1 architectural evolution to
  peer-with-optional-backpointer semantics.
- **Historical migration 0034 NOT modified** per §5.h.
- **62 new tests** (planned ~51; +11 for more granular
  fail-explicit + FK-behavior coverage) across 2 files:
  - `test_m321_deal_writeup_read.py` (30 tests) — service
    list/get + endpoint auth + fail-explicit filter validation
    + projection + detail endpoint.
  - `test_m321_credit_application_intake.py` (32 tests) —
    provenance FK behavior including mandatory
    `test_writeup_cannot_link_to_multiple_credit_applications`
    exercising all three defense layers (service
    `DealWriteupAlreadyLinkedError`, DB `IntegrityError` via
    bypass-service direct ORM, M11.3
    `WriteupAlreadyHandedOffError` via `hand_off_to_fandi`) +
    service list + endpoint auth (sales_manager 403,
    f_and_i_manager 200, dealer_owner 200) + fail-explicit
    validation (**`intake=false` → 400**) + projection.
- **DoD exception path invocation #7** — backend substrate
  with no operator-facing behavior change on its own.

Handoff at `docs/handoffs/SESSION_207_m32_inc1_backend.md`.

### M32.2 (SESSION_208 · sales-manager UI + sales-side Playwright)

- **Frontend wrappers** in `salesApi.ts`: 5 new typed wrappers
  + `derivedWriteupState` helper. Module docstring updated;
  **"UI deferred" language removed per §5.h** — closes the
  shipped-source deferral promise that had shipped 9 sessions
  ago at M11.6 (SESSION_119).
- **`main.tsx`** route header comment updated to reference
  M32.2 shipping.
- **3 new co-located components** in
  `frontend/src/components/sales/`:
  - `DealWriteupForm.tsx` — four-square form with vehicle
    picker (reuses M25.2 `listAdminVehicles` pattern).
  - `WriteupConfirmDialogs.tsx` — two co-located dialogs per
    M28.0 duplicate-small-stable-domain-logic lesson.
    `WriteupApproveConfirmDialog` uses D5-revised copy
    verbatim (no false re-approval advertisement — removed
    language is asserted absent in tests).
    `WriteupHandoffConfirmDialog` uses D6 irreversibility
    copy verbatim.
  - `LeadWriteupsPanel.tsx` — per-lead collapsible with
    three-signal state a11y per D7; Approve on Pending only;
    Send-to-F&I on Approved only; Handed-off rows are read-
    only history.
- **`LeadDetailModal.tsx`** renders `<LeadWriteupsPanel>` in
  the left column. Manager-only by transitivity of the modal
  itself.
- **35 new Vitest tests** across 4 files (planned ~34; +1 for
  §5.h "UI deferred" removal-verification test).
- **New Playwright describe block `sales-manager-writeup-handoff`**
  at `acceptance/journeys/sales_manager/sales_to_fandi_handoff.spec.ts`.
  8-step journey through the real UI: walk-in intake →
  Writeups panel → four-square form + picker → Pending badge
  → Approve (D5 copy verbatim) → Approved badge → Send-to-F&I
  (D6 irreversibility copy verbatim + customer name in body)
  → Handed off badge → technical assertion via sales-role-
  accessible writeup detail endpoint (**§0.a M32.2 Amendment 1**
  vs the memo's F&I-gated CA list assertion — 403 for
  sales_manager).
- **DoD satisfied directly** — no exception at customer-facing
  increment.

Handoff at `docs/handoffs/SESSION_208_m32_inc2_sales_ui.md`.

### M32.3 (SESSION_209 · F&I intake UI + F&I-side Playwright + new persona + M32 close-out fold)

- **New `f_and_i_manager` persona** per D11:
  `acceptance/support/auth/personas.ts` type + entry;
  `AUTH_STORAGE.fAndIManager` in playwright.config.ts + new
  project entry with `testMatch: /journeys\/f_and_i_manager\/.*\.spec\.ts/`;
  new `authenticate as f_and_i_manager` setup task in
  `login.setup.ts`.
- **New management command
  `seed_journey_fandi_intake_receipt.py`** — idempotent per
  M20 lesson; provisions persona (`acceptance-f-and-i-manager`
  user with `f_and_i_manager` role at default dealership) +
  `Intake Iris` lead + `FANDI-INTAKE-1` vehicle + approved+
  handed-off deal writeup with distinct four-square terms
  (vehicle_price 42500 / trade_allowance 7500 / down_payment
  3000 / monthly_payment_target 585 / term 60mo / apr 6.99%)
  + paired CA via real `hand_off_to_fandi` code path (uses
  M32.1 D9-revised² FK backpointer). Registered in `SEED_COMMANDS`.
- **Frontend wrapper `fetchCreditApplications`** in
  `fAndIApi.ts` — typed projections matching D3 endpoint
  shape; only sends `intake=true` when boolean true (never
  sends `intake=false` per §5.h — omit for unfiltered).
- **New page `DealerFandIIncoming.tsx`** at
  `/dealer-ai-f-and-i/incoming` per D8-revised — non-
  navigational rows with all triage info inline (no `<a>`
  wrapping; no click handler; no cursor-pointer); scope
  filter defaulting to intake=true; forbidden state for
  non-F&I roles; TermsCell renders four-square inline;
  direct-create CAs (writeup_context null) render "Direct
  application" placeholder.
- **`App.tsx` nav** adds "Incoming" entry adjacent to
  existing "F&I"; existing F&I entry flipped to `end: true`
  to prevent double-highlight on `/dealer-ai-f-and-i/incoming`.
- **23 new Vitest tests** across 2 files (planned ~20; +3
  for granular load-state + non-navigational-row coverage).
- **New Playwright describe block `fandi-intake-receipt`** at
  `acceptance/journeys/f_and_i_manager/fandi_intake_receipt.spec.ts`
  (**§0.a M32.2 Amendment 2**: file-per-persona rather than
  extending the M32.2 spec — file-per-persona strengthens
  R11 independence guarantee by construction). Uses new
  `f_and_i_manager` persona; reads pre-seeded `Intake Iris`
  fixture deterministically by lead name. **Fully
  independent of M32.2 fixture** — distinct rows; no shared
  state; test order irrelevant; parallelism-safe. 10-step
  journey covers navigation + inline lead/vehicle/four-square
  assertions + Incoming badge + attribution + M11.3 handoff
  notes prefix + non-navigational-row assertions.
- **M32 close-out fold** — this retrospective +
  `CAPABILITY_MATRIX.md` §7η + roadmap milestone_32_status
  flip + audit re-baseline (**161 / 129 / 32 / 321**) +
  START-NEXT-SESSION flip for SESSION_210.
- **DoD satisfied directly** — no exception at customer-facing
  increment.

Handoff at `docs/handoffs/SESSION_209_m32_inc3_fandi_ui.md`.

## 3. Deviations from plan and reason

### §0.a M32.2 Amendment 1 (SESSION_208): technical assertion switched from F&I-gated CA list to sales-role-accessible writeup detail endpoint

**M32.0 §5.e M32.2** called for the sales-side journey's
technical business-outcome assertion via
`page.request.get('/admin/credit-applications/list/?intake=true')`.
Implementation-time discovery: this endpoint is F&I-role-gated
per D3 + D10; the `sales_manager` persona used by the M32.2
journey receives 403. **Amendment:** use the sales-role-
accessible `/admin/deal-writeups/<pk>/` detail endpoint
(added at M32.1 per D2). Confirms all three state timestamps
populated post-UI-flow; transitively proves the M11.3
`hand_off_to_fandi` `@transaction.atomic` block ran to
completion including CA creation per M32.1 D9-revised² FK-
pairing tests (belt + suspenders composition).

F&I-side CA-list verification stayed as M32.3 scope via the
`f_and_i_manager` persona spec.

### §0.a M32.2 Amendment 2 (SESSION_208): M32.3 spec file placement

**M32.0 §5.e M32.3** said the M32.3 `fandi-intake-receipt`
journey would "extend the existing spec". Implementation-time
discovery: Playwright's project routing in `playwright.config.ts`
scopes each project by `testMatch` regex against journey path;
a single spec file cannot span two personas without introducing
a new project entry. **Amendment:** M32.3 ships at
`acceptance/journeys/f_and_i_manager/fandi_intake_receipt.spec.ts`
under a new project entry that references
`AUTH_STORAGE.fAndIManager`. File-per-persona strengthens the
R11 independence guarantee by construction — no shared state
possible.

### Two-verification-round revision at M32.0

The initial §5.b D1–D11 draft required **two rounds of user-
directed revision** before scope-lock:

- **Round 1** identified four load-bearing issues: M32.2 DoD
  posture must not invoke exception; query validation must
  fail-explicit (400) instead of silently unfiltering; approve
  copy must match actual state machine (remove false re-
  approval advertisement); F&I destination must be accessible
  (D8 non-navigational rows since `admin_lead_detail` is sales-
  role-gated).
- **Round 2** identified four more: provenance link upgraded
  from nullable FK to nullable OneToOneField with three-layer
  defense; historical migration 0034 immutability enforced;
  M32.3 fixture must be independently deterministic (dedicated
  seed command); non-manager Writeups-tab posture corrected to
  reflect actual behavior (advisors cannot open modal at all).

Both rounds strengthened the milestone — none changed the
§5.a target selection. Planning-time as-recommended streak
10 → 11 preserved.

### Test counts exceeded planned estimates at every increment

- M32.1 planned ~51, shipped 62 (+11 for more granular fail-
  explicit + FK-behavior coverage).
- M32.2 planned ~34, shipped 35 (+1 for §5.h "UI deferred"
  removal-verification test).
- M32.3 planned ~20, shipped 23 (+3 for granular load-state
  + non-navigational-row coverage).

Total: planned ~105, shipped 120. Test-count discipline
preserved (all M32.0 §5.e budgets clearly labeled as "planned
~N"; overshoot within expected variance per M28 lesson).

## 4. Deferrals from M32 (all valid for later re-entry)

All per `MILESTONE_32_PLANNING.md` §3 + §5.h + this retrospective:

- **Salesperson-authored writeups** — M33+ evidence-gated;
  broader role gating requires selective permission-class work
  + acceptance coverage; breaks the M10 → M32 zero-drift
  streak with intent.
- **Writeup edit (PATCH)** — activation-surface-asymmetry
  preservation per M31 lesson w. Re-approval remains a
  backend M11.3 contract but not exposed in M32 UI.
- **Cross-lead sales-manager pending-approval queue page** —
  assumption: same-day approval via LeadDetailModal.
- **F&I-scoped lead-context view or per-CA detail page** —
  D8 non-navigational intake rows carry all triage info
  inline.
- **Separation-of-duties enforcement** (approver ≠ writer) —
  matches M11.3 shipped behavior.
- **Pagination / server-side sort** on the 3 new list
  endpoints — matches M10.7 / M11 sales substrate precedent.
- **Websocket / auto-refresh** of F&I intake queue or
  Writeups tab — accepted stale-tab race per M31 R1.
- **F&I workflow state extensions on intake rows** (In
  progress / Structuring / Submitted to lender / etc.) —
  M32 intake rows carry only "Incoming" state.
- **`intake=false` operator filter** — reserved-and-rejected;
  use `has_contract=true` in a future milestone if evidence.
- **Backfill of `credit_application.deal_writeup` for
  existing rows** — existing CAs stay NULL truthfully.
- **F&I-scoped acceptance journey for post-intake workflow**
  — M32.3 journey stops at F&I receipt.
- **Retroactive modification of historical migrations** —
  historical migrations are immutable historical artifacts.
- All prior M31 §3 + M30 §3 + M29 §3 + M28 §3 + M27 §3 +
  M25 §4 deferrals — unchanged.

## 5. Durable design principles surfaced or reinforced

### (w) Activation-surface asymmetry — M32.1 re-application (third milestone; load-bearing across three milestones)

M30.2 surfaced. M31.1 re-applied (Restore as dedicated activation
verb, never a PATCH side-effect). **M32.1 re-applies** — the
new `list_deal_writeups` verb rejects unknown state values
(unknown `state` raises ValueError → 400 at endpoint); the D3
CA list endpoint accepts only literal `intake=true` (reserved-
and-rejected `intake=false` per §5.h). State-machine surfaces
never silently broaden on invalid input.

**Status:** load-bearing across three milestones (M30 + M31 +
M32). Elevate to "core project principle" if it re-applies at
M33+.

### (x) Row-action truth-vocabulary asymmetry — M32.2 partial re-application

M30.2 surfaced. M31.2 re-applied (row button "Restore" →
confirmation title "Reactivate template?"). **M32.2 partially
re-applies** — the row button "Send to F&I" opens a
confirmation titled "Send to F&I?" with body copy that
explicitly names the truth ("This cannot be undone — a second
attempt will be refused to protect against duplicate
applications and their retention-clock consequences.").
Vocabulary is aligned rather than reframed (both surfaces use
"Send to F&I"), but the truth-vocabulary discipline is
preserved — the body copy makes the semantic consequences
explicit.

**Status:** load-bearing across three milestones (M30 + M31 +
M32) in principle; M32 exercised the principle via body-copy
truthfulness rather than title-reframing.

### (y) Playwright-independent-fixture pattern — M32.3 origin — NEW

**M32.3 establishes a new durable pattern for downstream-
receiver journeys.** When a customer-facing milestone ships
across two persona-scoped increments (M32.2 sales-side; M32.3
F&I-side), each increment's Playwright coverage must be
independently deterministic — test order irrelevant;
parallelism-safe.

**Mechanism:** dedicated idempotent seed command per persona-
scoped increment provisions its own fixture (distinct lead
name, distinct vehicle stock number). M32.2 creates its own
fixture via the real UI (walk-in intake → writeup → hand-off);
M32.3 reads a pre-seeded `Intake Iris` fixture provisioned by
`seed_journey_fandi_intake_receipt`.

**File-per-persona placement** further strengthens the pattern
by construction — Playwright's project routing scopes each spec
file to a persona, so cross-spec state leakage is architecturally
impossible.

**Status:** surfaced at M32.3. Awaits first re-application to
elevate to "load-bearing across two milestones."

### (z) Verification-driven revision cycles at planning-open — M32.0 origin — NEW

**M32.0 established the pattern of accepting multiple user-
directed revision rounds at §5.b–§5.h before scope-lock.** The
initial D1–D11 draft went through two rounds:

- Round 1 (four load-bearing issues): M32.2 DoD posture, fail-
  explicit query validation, approve copy state-machine
  truthfulness, F&I destination accessibility.
- Round 2 (four more): provenance link OneToOneField upgrade,
  historical migration immutability, M32.3 fixture
  independence, non-manager tab posture truthfulness.

**Pattern:** the M32.0 §4 verification pass surfaces blocking
findings; the initial §5.b draft resolves them plausibly; user
review then identifies where the initial resolution violates
some invariant (fail-safe posture, shipped-surface immutability,
truthfulness of promised UI). Revision rounds strengthen the
milestone without changing target selection.

**Status:** surfaced at M32.0. Awaits first re-application to
elevate. Candidate elevation criterion: if M33+ or M34+ also
requires multi-round revision at planning-open before scope-
lock, this pattern becomes a formal expected step in the M-
open cadence rather than an ad-hoc discovery.

### (aa) Historical-migration-immutability discipline — M32.1 origin — NEW

**M32.1 established the discipline that historical migrations
are immutable historical artifacts.** The initial §5.b D9
draft included "update M11.3 migration 0034 docstring to
reference the M32.1 architectural evolution." User feedback
rejected this: historical migrations record what shipped at
that point in time; rewriting them retroactively makes old
decisions appear as though they included later changes.

**Alternate placement:** architectural evolution recorded in
(1) current model/service docstrings that consumers actually
read, (2) the new migration's docstring, (3) the planning
memo, (4) this retrospective, (5) `CAPABILITY_MATRIX.md`
§7η.

**Status:** surfaced at M32.1. Awaits first re-application to
elevate.

### (bb) Non-navigational cross-role UI when role-gating conflicts — M32.3 origin — NEW

**M32.3 established a pattern for cross-role UI where the
consuming role cannot access the naturally-linked resource.**
The initial §5.b D8 draft promised F&I intake rows would
link to lead detail. Verification surfaced that
`admin_lead_detail` is sales-role-gated; F&I would 403 on
any row-link. **Amendment:** F&I intake rows are non-
navigational; all triage info rendered inline.

**Pattern:** when a UI surface would naturally cross role
boundaries via a navigational link, and the target endpoint
is gated on the source role's opposite, either (a) build a
role-scoped alternate endpoint with narrower projection, or
(b) render the info inline without navigation. Option (b) is
the smaller M-scope choice when the inline info is
sufficient for the operator's task.

**Status:** surfaced at M32.3. Awaits first re-application to
elevate.

## 6. Streak accounting at M32 close

- **Planning-time as-recommended streak: 10 → 11.** Target
  selected as recommended after seven-alternative comparison
  + eleven-verification pass + two verification-driven
  revision rounds. §0.a amendments (2 at M32.2; 0 at M32.1;
  0 at M32.3) are corrective and do not affect the streak.
  Historical run of 89 across M10 → M23 preserved.
- **Zero-drift permission-class streak: 33 → 34 → 35 → 36
  consecutive milestones** (M10 → M32). M32.1 added 3
  endpoints all reusing existing classes verbatim; M32.2 +
  M32.3 shipped no new backend endpoints.
- **Substrate-compound-value continuation: 5 links unchanged.**
  M27.1 → M28.1 → M29 → M30 → M31 preserved as the depth
  arc. M32 chose breadth (fresh direct-operator gap) over
  depth (NEW C F&I chargeback remained pilot-evidence-gated).
- **DoD exception path invocations: 6 → 7.** M26 + M27.1 +
  M28.1 + M29.1 + M30.1 + M31.1 + M32.1. M32.2 + M32.3
  satisfy DoD directly.
- **First break out of accounting/templates domain since
  M27.1** (six-milestone lineage broken).
- **First customer-facing milestone since M11 to ship across
  three increments** (scope-driven per M32.0 §4 verification
  findings).
- **First F&I-role-gated list endpoint** — M32.1
  `admin_credit_application_list`.
- **First schema-level pairing constraint at the DealWriteup ↔
  CreditApplication seam** — M32.1 nullable OneToOneField
  with three-layer defense.
- **First milestone since M20 to add a new Playwright
  persona** — `f_and_i_manager` at M32.3.
- **Two §0.a M32.2 amendments** — first M32-era milestone to
  record implementation-time amendments; both scope-preserving
  (Amendment 1 = alternate technical assertion path;
  Amendment 2 = file-per-persona placement).
- **Test-count discipline preserved** — planned ~105, shipped
  120 (+15 for granular coverage; well within expected
  variance).

## 7. Baselines at M32 close

- Backend: **4,933 → 4,995 pass** (+62 at M32.1); unchanged
  M32.2 + M32.3 (frontend + Playwright + seed only). 1
  skipped, 0 fail throughout.
- Frontend Vitest: **319 → 354 → 377 pass** across 36 → 40 →
  42 test files (+35 M32.2 + +23 M32.3).
- Acceptance: **22 → 23 → 24 journeys** (+1 M32.2 sales;
  +1 M32.3 F&I). **29 → 31 tests / 0 failed / 32.5s** on
  fresh DB.
- Django `check`: clean throughout.
- `makemigrations --check --dry-run`: "No changes detected"
  throughout (0051 landed at M32.1).
- Frontend + acceptance `tsc --noEmit`: clean throughout.
- Audit artifact: **158 / 124 / 34 / 318 → 161 / 128 / 33 /
  321 → 161 / 129 / 32 / 321**. Two-source agreement
  confirmed at M32.3 close.
- DRF admin surface: 118 → **121** endpoints (+3 at M32.1).
- Migration count: 0050 → **0051** (+1 at M32.1).
- `git grep "UI deferred" frontend/`: returns only the M32.2
  removal-verification test file — shipped-source deferral
  promise fully closed.

## 8. Corrections (post-close)

_None yet — added to this section as any post-close corrections
land._

## 9. Evidence-based candidates for M33

**Elevated (highest recommendation strength for M33.0):**

- **NEW C — F&I chargeback substrate** — sixth-link substrate-
  compound-value candidate; still gated on pilot evidence
  today (unchanged from M30/M31/M32 §9). Now that M32 has
  established both the CA-side surface (M32.1 list endpoint +
  M32.3 UI) and the sales-to-F&I bridge, the chargeback
  substrate has a stronger operator context than at M31 open
  — the F&I team can see incoming CAs and would benefit from
  tracking their post-funding chargeback exposure. If pilot
  evidence surfaces at M33.0 open, this becomes the natural
  next depth-arc link.
- **F&I workflow state extensions on intake rows** (In progress
  / Structuring / Submitted to lender / etc.) — NEW at M32.3
  §3. Would extend the M32.3 intake page from single-state
  "Incoming" to a proper F&I workflow tracker. Adjacent to
  M10.2–M10.6 F&I entities (deal structure, lender submission,
  stipulation, contract, funding, chargeback) that already
  exist as backend entities but have no incoming-queue
  progression UI. Evidence-gated on operator direction.
- **F&I-scoped lead-context view** — NEW at M32.3 §3.
  Currently F&I sees inline triage data (D8 non-navigational
  rows) but cannot open a richer lead context. Two paths per
  M32.0 §5.h: (a) new endpoint `GET /admin/f-and-i/lead-context/<lead_id>/`
  with narrowed projection, or (b) selective role-gating
  expansion on `admin_lead_detail` with explicit review of
  what leaks to F&I. Evidence-gated.
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (M26/M27/M28/M29/M30/M31/M32 deferral, unchanged). Requires
  SESSION-189-§3-style tracing at open. Blast radius unknown.
- **NEW O3 — Rows 1–4 plain-string-literal investigation**
  (M26/M27/M28/M29/M30/M31/M32 deferral). Requires tracing.
- **H — Test-hygiene remediation.** Three shared-DB non-
  idempotent journeys unchanged from M27.2 → M32.3 close.
  CI-stability compound value grows with journey count (now
  24 journeys).

**Fresh direct-operator gaps surveyed (breadth candidates):**

- **Vendor detail (#43)** — GET/PATCH wrapper-only; small
  polish; low coverage gain standalone.
- **Photo reorder (#65)** — wrapper-only; small polish;
  requires D&D primitive selection.
- **Broader F&I domain surface (#89–101 excl. #101 chargeback
  which is NEW C)** — 12 uncovered endpoints; entire subdomain
  unwired; too large without operator direction.
- **Cross-lead sales-manager pending-approval queue page** —
  NEW at M32.3 §3. If operator evidence surfaces that per-lead
  Writeups tab is insufficient for sales-manager triage.

**Gated (unchanged from M29+M30+M31+M32 close):**

- T (real tester feedback); U (hosted-demo substrate); L
  (first-live-pilot staging); M (multi-operator support —
  breaks the M10 → M32 zero-drift streak with intent).

**Deferred pending evidence:**

- D (LLM router / cost caps).

**Deferred but stable:**

- G (dashboard testid hardening).

**Deferred at M32 §3 / M31 §3 / M30 §3 / M29 §3 / M28 §3 /
M27 §3 / M25 §4:** all carried forward unchanged.

**Standing question for M33:** the sales-to-F&I workflow is
now bridged. Two natural next moves: (a) **F&I chargeback
substrate** (NEW C — sixth substrate-compound-value link if
pilot evidence surfaces; would extend the M32-shipped F&I-
side surface); (b) **F&I workflow state extensions on intake
rows** — take the M32.3 intake page from single-state to
multi-state F&I workflow tracker; would use M10.2–M10.6
entities that ship as backend-only today. Both continue the
sales-to-F&I depth arc M32 opened, but each requires operator
evidence to scope properly.
