---
title: "SESSION_210 handoff — Milestone 33 · Increment 0 (M33.0 — planning refinement + target selection)"
status: active
type: handoff
date: 2026-08-04
session: 210
milestone: 33
milestone_status: active
milestone_name: "F&I Intake Activation: Incoming Application to Active Deal Structure (derived DealStructure status + DealStructure read endpoint + F&I structuring UI + Playwright loop)"
increment: 0
increment_status: shipped
commit: pending
commit_notes: "M33.0 planning session — local commit at close per M28.0 / M29.0 / M30.0 / M31.0 / M32.0 planning-only cadence; hash backfilled via a subsequent commit; NOT pushed. Coordinated M33 close push deferred to explicit user confirmation after M33.2 close."
---

# SESSION_210 — Milestone 33 · Increment 0 (M33.0 — planning refinement + target selection)

## What shipped

SESSION_210 opened as a planning-only session per the
M32.3 close-out priorities in `00-START-NEXT-SESSION.md`.
One deliverable landed:

1. **M33.0 planning memo** authored at
   `docs/roadmap/MILESTONE_33_PLANNING.md` — target locked
   as **F&I Intake Activation — Incoming Application to
   Active Deal Structure** (§5.a). User-confirmed after
   direct evaluation against six alternatives (NEW C F&I
   chargeback substrate — still pilot-evidence gated; NEW
   F&I workflow-state extensions — narrowed to M33's two
   derived states only per operator directive; NEW F&I-
   scoped lead-context view — evidence-gated; NEW cross-
   lead sales-manager pending-approval queue — evidence-
   gated; NEW O2 / NEW O3 — tracing-first; H test-hygiene
   — evidence-independent but zero direct-operator-
   coverage gain) plus three fresh direct-operator gaps
   (vendor detail #43, photo reorder #65, broader F&I
   subdomain #89–101). All §5.b–§5.h decisions locked
   (D1–D10; risk register R1–R10; verifications §4.1–§4.9;
   two-increment phasing; DoD compliance; rollback;
   non-goals). One blocking finding on field-level
   prepopulation truthful-entry discipline surfaced at §4
   verification and resolved architecturally before §5.b
   lock via D5 form contract.

No §0.a M33.0 amendments — the first M32 CI run on
`2a1e359` (M32.3 hash-backfill commit) is green (workflow
`30956621258`, success in 3m10s at 2026-08-04T22:30:04Z);
no regression to correct.

Full active memo authored at
`docs/roadmap/MILESTONE_33_PLANNING.md`.

**Session artifacts:**

- **Starting-state verification (§1):** git clean;
  `HEAD == origin/main @ 2a1e359` (M32 push confirmed pre-
  session — 0 commits ahead); Redis PONG; Django `check`
  clean; `makemigrations --check` clean; frontend
  `tsc --noEmit` clean; acceptance `tsc --noEmit` clean;
  backend suite **4,995 pass, 1 skipped, 0 fail** (183.0s);
  frontend Vitest **377 pass** (42 files, 7.91s);
  acceptance DB proactively reset per SESSION_200 §0.a
  durable lesson (v). All matches M32.3 close baseline
  exactly.
- **First M32 CI run monitored (§2):** acceptance workflow
  on `2a1e359` (M32.3 hash-backfill commit) **completed
  success** in 3m10s at 2026-08-04T22:30:04Z. Prior runs
  on `main` all successful. Main is CI-verified shipped at
  the M32.3 baseline. No §0.a M33.0 amendment triggered.
- **Audit regeneration (§3):** `python3 -m
  dealer_ai.scripts.audit_operational_surface` invoked.
  Output: **161 total / 129 covered / 32 backend-only /
  321 service verbs**. Byte-identical to the committed
  M32.3 artifact. Two-source agreement at M33.0 open.
- **Candidate list presented (§4)** across the M32 §9
  tiers:
  - **Elevated (highest recommendation strength at
    M33.0):** NEW C — F&I chargeback substrate (still
    pilot-evidence gated); NEW F&I workflow-state
    extensions (evidence-gated on state model); NEW F&I-
    scoped lead-context view (evidence-gated); NEW cross-
    lead sales-manager pending-approval queue (evidence-
    gated); NEW O2 (7-milestone deferral, unchanged);
    NEW O3 (7-milestone deferral, unchanged); H — test-
    hygiene remediation.
  - **Fresh direct-operator gaps surveyed (breadth
    candidates):** vendor detail (#43 wrapper-only,
    small polish); photo reorder (#65 wrapper-only,
    small polish + D&D primitive selection); broader F&I
    subdomain (#89–101 excl. #101 chargeback — 12
    uncovered, too large without direction).
  - **Gated:** T, U, L, M.
  - **Deferred pending evidence:** D.
  - **Deferred stable:** G.
  - **Deferred at M32 §3 / M31 §3 / M30 §3 / M29 §3 /
    M28 §3 / M27 §3 / M25 §4:** all carried forward
    unchanged.
- **Recommendation (§5) and user confirmation:** F&I
  Intake Activation — Incoming Application to Active Deal
  Structure, under the primary operational-coverage lens
  with F&I depth-arc continuation framing per M32 §9
  standing question. Six load-bearing evidence signals
  recorded (§5.a of planning memo):
  1. Activates 19 sessions of dormant M10.2 substrate
     (`POST /admin/deal-structures/` shipped SESSION_107
     with zero operator receiver until M33.2).
  2. Answers M32 §9 standing question with F&I depth-arc
     continuation over breadth reset.
  3. Restarts substrate-compound-value continuation at 2
     links (M32 + M33) after M32 breadth pivot.
  4. Direct-operator coverage delta of +1 covered (M10.2
     create endpoint) + 1 new (M33.1 read endpoint) = net
     162/130 at M33 close.
  5. Zero-drift preservation — `_M101_PERMS` reused
     unchanged; `f_and_i_manager` persona shipped M32.3.
  6. Narrow scope respects the discovery rule — no state-
     machine invention; no chargeback / lender /
     stipulation / contract / funding extensions; no
     historical-migration modification.
  User confirmed §5.a; requested field-level prepopulation
  truthful-entry verification before §5.b–§5.h draft.
- **Verification pass (§4 of planning memo, §6 of this
  handoff):** nine verifications performed at planning
  open; one blocking finding on field-level prepopulation
  truthful-entry discipline; resolved architecturally
  before §5.b lock via D5 form contract. See §6 of this
  handoff.
- **User review round 1:** approved recommendation with
  latest-only posture direction (Incoming when no
  DealStructure; In progress when at least one;
  "Start structuring" only on Incoming; "Open structure"
  showing latest by `-created_at`; preserve many-
  structures-per-CA domain model; no one-structure
  constraint; no multi-structure UI in M33). Recorded
  future capability — Lender Fit Recommendations as
  structured, auditable, human-controlled ranking with
  hard-eligibility + likely-fit + missing-information
  bands + operator explanation + preserved human decision
  authority; NOT implemented in M33; blocked on named
  prerequisites. Approved M33.1 backend exception path
  and M33.2 customer-facing Playwright coverage. Approved
  all listed non-goals. Requested field-level truthful-
  entry verification before §5.b lock.
- **User review round 2:** four corrections applied before
  §5.b lock:
  1. **Financial-language contract** — at DealStructure
     stage no lender submission or approval exists yet;
     therefore APR / term / monthly payment / amount
     financed are proposed structure values, not lender-
     approved / lender-committed / actual. Sales-side
     values labeled sales targets; F&I-entered values
     labeled proposed structure values. No M33 surface
     describes any value as lender-approved / lender-
     committed / actual. Locked in D5 + D6 + D7 + D8 +
     R10 with Playwright regex assertion.
  2. **Deterministic ordering** — `order_by("-created_at",
     "-pk")` on latest-structure subquery to disambiguate
     when two structures share `created_at` at microsecond
     granularity. Subquery explicitly tenant-scoped via
     `dealership=dealership` filter (belt over model
     `clean()` + service `CrossTenantDealStructureError`
     suspenders). Locked in D3.
  3. **Canonical endpoint path** — `GET /admin/deal-structures/<int:pk>/`
     enforced verbatim across planning memo, handoff,
     frontend wrapper, tests, and Playwright expectations.
     Locked in D2.
  4. **Strengthened truthful-entry validation** — 0 is a
     valid explicit value when operator intentionally
     enters it; blank means not yet confirmed and never
     silently converts to zero; submission requires
     explicit values for `amount_financed`, `taxes`,
     `fees`; `trade_payoff` remains optional only when
     operator explicitly confirms "No trade payoff" via
     dedicated checkbox affordance (not placeholder copy
     alone); basic consistency-warning surface (not full
     desking math) flags obviously contradictory entries
     such as `trade_payoff > 0` with `trade_allowance ==
     0`. Locked in D5 with three-layer defense
     (form validation + submit disable + D8 Playwright
     assertion) and R2 mitigation.
- **All §5 locks confirmed by user.**

## 1. Verification results at open

- **git status:** clean; `HEAD == origin/main @ 2a1e359`
  (0 commits ahead).
- **git log --oneline -10:** shows the expected M32 commit
  sequence (M32.3 hash-backfill `2a1e359`; M32 close-out
  fold `9906938`; M32.2 hash-backfill `2d9bb30`; M32.2 UI
  `2ef039d`; M32.1 hash-backfill `6f2b64d`; M32.1 backend
  `16c54e9`; M32.0 hash-backfill `4e2afc9`; M32.0 planning
  `c3d46fd`; M31.2 hash-backfill `08fef5f`; M31.2 close-
  out fold `4b5f5b9`).
- **`python3 manage.py test dealer_ai`:** 4,995 pass, 1
  skipped, 0 fail (182.97s).
- **`cd frontend && npm test`:** 377 pass across 42 files
  (7.91s).
- **`python3 manage.py check`:** clean (7 benign
  DecimalField warnings — pre-existing, unchanged).
- **`python3 manage.py makemigrations --check --dry-run`:**
  "No changes detected."
- **`cd frontend && npx tsc --noEmit`:** clean (no
  output).
- **`cd acceptance && npx tsc --noEmit`:** clean (no
  output).
- **`redis-cli ping`:** PONG.
- **`rm -f backend/db.acceptance.sqlite3`:** completed
  (no-op if absent) per SESSION_200 §0.a durable lesson
  (v).

All matches M32.3 close baseline exactly.

## 2. First M32 CI run

- **Workflow:** `acceptance` on `main`.
- **Latest run:** `30956621258` on `2a1e359` (M32.3 hash-
  backfill commit, top of `main`).
- **Result:** completed / success.
- **Duration:** 3m10s total.
- **Prior runs on `main`:** all successful.

**M32 is CI-verified shipped.** No §0.a M33.0 amendment
triggered.

## 3. Audit regeneration

- **Command:** `python3 -m
  dealer_ai.scripts.audit_operational_surface`.
- **Output:** 161 total / 129 covered / 32 backend-only /
  321 service verbs.
- **Artifact write:**
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`.
- **Diff:** none. Byte-identical to M32.3 committed
  baseline.

**Two-source agreement** at M33.0 open: audit numbers
match the M32.3 handoff frontmatter and the M32 §7 anchor
(161 / 129 / 32 / 321).

## 4. Candidate list presented at open

Per M32 retrospective §9:

**Elevated (highest recommendation strength at M33.0):**

- **NEW C — F&I chargeback substrate.** Sixth-link
  substrate-compound-value candidate; still gated on
  pilot evidence today. No pilot direction has landed
  since M32 close. Correct to defer at M33.
- **NEW F&I workflow-state extensions on intake rows.**
  Would extend M32.3 single-state Incoming queue to
  multi-state tracker. Evidence-gated on state model;
  narrowed to M33's two derived states (Incoming / In
  progress) only per operator directive.
- **NEW F&I-scoped lead-context view.** Evidence-gated on
  whether M32.3 D8 inline triage suffices.
- **NEW cross-lead sales-manager pending-approval queue
  page.** Evidence-gated on whether per-lead
  LeadDetailModal triage suffices.
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (7-milestone deferral, unchanged).
- **NEW O3 — Rows 1–4 plain-string-literal
  investigation** (7-milestone deferral, unchanged).
- **H — Test-hygiene remediation.** Three shared-DB non-
  idempotent journeys unchanged from M27.2 → M32.3
  close.

**Fresh direct-operator gaps surveyed:**

- **Vendor detail (#43)** — wrapper-only; small polish.
- **Photo reorder (#65)** — wrapper-only; small polish
  + D&D primitive selection.
- **Broader F&I subdomain (#89–101 excl. #101
  chargeback)** — 12 uncovered endpoints; too large
  without operator direction.

**Gated (unchanged):** T, U, L, M.

**Deferred pending evidence:** D.

**Deferred stable:** G.

**Deferred at M32 §3 / M31 §3 / M30 §3 / M29 §3 / M28
§3 / M27 §3 / M25 §4:** all carried forward unchanged.

## 5. Recommendation and user confirmation

**Primary recommendation:** F&I Intake Activation —
Incoming Application to Active Deal Structure.

**Rationale under the primary operational-coverage lens
(with F&I depth-arc continuation framing per M32 §9
standing question resolution):**

- **Activates 19 sessions of dormant M10.2 substrate.**
  `POST /admin/deal-structures/` shipped SESSION_107 but
  has had zero operator receiver until M33.2.
- **Answers M32 §9 standing question with F&I depth-arc
  continuation.** M32 opened the sales-to-F&I bridge;
  M33 continues the arc with the first F&I-side operator
  action.
- **Restarts substrate-compound-value continuation at 2
  links (M32 + M33)** after the M32 breadth pivot.
- **Direct-operator coverage delta** — moves M10.2
  create endpoint from backend-only to covered (161/129
  → 162/130 at M33 close after M33.1 also adds the read
  endpoint).
- **Zero-drift preservation** — no new permission
  classes; `f_and_i_manager` persona already shipped.
- **Narrow scope respects the discovery rule** — M33
  does not invent state machines, does not extend
  chargeback / lender / stipulation / contract / funding
  surfaces, does not touch historical migrations.

**Tradeoffs named explicitly** (not papered over):

1. Zero operator evidence surfaced M32→M33 for the
   specific two-state derivation — narrowed from broader
   NEW F&I workflow-state extensions per operator
   directive at planning open to only Incoming / In
   progress states that are truthfully derivable from
   existing FK-graph presence.
2. First-loop-only posture defers iteration UX
   (subprime counter, revised terms after stip clears,
   etc.) despite the M10.2 domain model allowing
   iteration. Recorded in §5.h non-goals; awaits
   operator evidence.
3. Direct-create CAs (M10.1 without hand-off upstream)
   are rendered on the intake page today but cannot
   "Start structuring" in M33 (no vehicle discovery
   substrate). Explicitly deferred to future milestone.
4. Lender Fit Recommendations recorded as future
   capability with full design contract at planning
   time per operator directive — captured, blocked on
   named prerequisites, not implemented.

**Alternatives with explicit tradeoffs:**

- NEW C — F&I chargeback: pilot-evidence-gated. Recommend
  only if pilot evidence surfaces at M34+.
- NEW broader F&I workflow-state extensions: would
  invent state model without operator evidence.
  Narrowed to M33's two derived states only.
- H — test hygiene: bounded, un-gated, CI-stability
  compound value; zero direct operator-coverage gain.
- NEW O2 + NEW O3 — audit-substrate integrity: tracing-
  first; blast-radius unknown; deferred.
- Vendor detail / Photo reorder / Broader F&I subdomain:
  small polish or too large without direction.

**User confirmation:** F&I Intake Activation locked as
§5.a; requested field-level prepopulation truthful-entry
verification before drafting §5.b–§5.h; four corrections
applied before §5.b lock (financial-language contract;
deterministic ordering + tenant-scope filter; canonical
endpoint path; strengthened truthful-entry with explicit
affordance + basic consistency warning).

## 6. Verifications performed at planning-open

Nine verifications performed. One surfaced blocking
finding on field-level prepopulation truthful-entry
discipline; resolved architecturally before §5.b lock.
See `docs/roadmap/MILESTONE_33_PLANNING.md` §4 for full
detail.

### 6.1 DealStructure model + FK graph inspection

- `DealStructure` (`models.py:4742`) — three CASCADE FKs
  (dealership, credit_application, vehicle); five required
  scalars (sale_price, amount_financed, apr, term_months,
  monthly_payment); five defaulted-to-zero scalars
  (down_payment, trade_allowance, trade_payoff, taxes,
  fees); one JSON list default `[]` (back_end_products);
  three nullable ratios (ltv_pct, pti_pct, dti_pct).
- Cross-tenant `clean()` enforces dealership matches CA
  + vehicle.
- **M-to-1 cardinality** — multiple DealStructures per CA
  explicitly allowed. Preserved unchanged at M33.

### 6.2 Service verb inventory

- `services/f_and_i/deal_structure.py` — six verbs:
  three pure ratios; `record_deal_structure` (create +
  ratios); `get_deal_structure` (single-row tenant-
  scoped read); `recompute_ratios` (helper).
- **No list-by-CA verb exists.** M33 does not add one —
  D1 + D3 subquery annotations replace the need.

### 6.3 Endpoint contract inspection

- Shipped: `POST /admin/deal-structures/` only. No GET,
  LIST, PATCH, DELETE.
- M33 adds one: `GET /admin/deal-structures/<int:pk>/`
  (canonical path).

### 6.4 Permission-class access

- All M10 F&I endpoints gate on `_M101_PERMS`
  (`IsFinanceManagerOrOwnerAtActiveDealership`).
- `f_and_i_manager` persona shipped M32.3 already carries
  it.
- **Zero-drift streak preserved** (36 → 37 projected M33
  close).

### 6.5 FK-graph sequence: DealStructure is genuinely first

- Post-intake F&I FK graph: CA → DealStructure → (
  LenderSubmission | Contract). Stipulation attaches to
  LenderSubmission; Funding OneToOne with Contract;
  Chargeback M-to-1 with Contract.
- DealStructure is the sole gateway from CA to every
  downstream F&I entity.
- LenderSubmission and Contract are independent siblings
  (neither required to precede the other) — cash deals +
  house-paper BHPH can Contract without LenderSubmission.

### 6.6 FK discoverability for CREATE

- **CLEAN for writeup-originated CAs** —
  `credit_application_id` from intake row PK;
  `vehicle_stock` from
  `writeup_context.vehicle.stock_number`.
- **Direct-create CAs (`writeup_context = null`) OUT of
  M33 scope** — no vehicle discovery substrate today.
  Rendered without "Start structuring" action per D5
  extension.

### 6.7 Field-level prepopulation truthful-entry check —
**BLOCKING**

- Six of thirteen DealStructure inputs prepopulate from
  `writeup_context.terms` (sale_price, down_payment,
  trade_allowance, monthly_payment_target,
  term_months_target, apr_target).
- Four require F&I truthful entry with no writeup source:
  `amount_financed`, `taxes`, `fees`, `trade_payoff`.
- Applying the M10.2 backend serializer defaults of
  `0.00` on `taxes` / `fees` / `trade_payoff` from the
  M33 form would silently invent false financial values.
- **Resolved by D5 form contract** — blank ≠ 0; submit
  disabled until explicit values for
  `amount_financed` / `taxes` / `fees`; `trade_payoff`
  requires explicit "No trade payoff" checkbox
  affordance; basic consistency-warning surface (not
  full desking math).

### 6.8 Derivable-status sufficiency

- **CLEAN** — `Exists(DealStructure.objects.filter(...))`
  on CA list projection is sufficient to derive Incoming
  vs In progress without new schema column.
- Downstream states (Submitted / Approved / Contracted /
  Funded / Chargedback) deliberately not derived in M33
  — require underlying workflow verification per §3.

### 6.9 DoD compliance check on §5.e

- **CLEAN.** M33.1 → invocation #8 of exception path
  (M32.1 was #7). M33.2 satisfies DoD directly via new
  Playwright journey.

## 7. §5 locks summary

All ten §5.b design decisions locked in the memo (D1–D10).
Highlights:

- **D1 — Backend `has_deal_structure` annotation.**
  Extends M32.1 CA list queryset with
  `Exists(DealStructure.objects.filter(dealership=dealership,
  credit_application=OuterRef("pk")))`. Tenant-scoped in
  the filter as belt-over-suspenders.
- **D2 — Backend `GET /admin/deal-structures/<int:pk>/`
  read endpoint.** Canonical path locked verbatim. Thin
  wrapper on shipped `get_deal_structure(...)` service
  verb + shipped `_project_deal_structure(deal)`
  projection. `_M101_PERMS`. 404 fail-closed. No PATCH.
- **D3 — Backend `latest_deal_structure_id`
  deterministic subquery.** Ordering
  `("-created_at", "-pk")` — primary sort matches
  `DealStructure.Meta.ordering`; `-pk` disambiguates
  microsecond-shared timestamps. Explicit tenant-scope in
  subquery filter.
- **D4 — Frontend derived-status chip.** Two-state
  vocabulary (Incoming / In progress). Three-signal a11y
  per M31 D6.
- **D5 — Frontend "Start structuring" action + truthful-
  entry form contract.** No silent defaults on financial
  fields; blank ≠ 0; explicit values required for
  `amount_financed` / `taxes` / `fees`; "No trade payoff"
  checkbox for `trade_payoff`; basic consistency-warning
  for obvious contradictions (not full desking math);
  financial-language contract (sales targets / proposed
  structure values only; never lender-approved / lender-
  committed / actual).
- **D6 — Frontend "Open structure" read view.** Read-only
  panel; latest structure via D3 subquery; NULL-safe
  ratio display. No edit / PATCH / delete in M33.
- **D7 — No client-side monthly-payment auto-derivation.**
  `services.payment_engine` not wired to form; F&I types
  proposed structure value explicitly. Cadence
  variability puts calculator UX out of M33 scope.
- **D8 — Playwright `f_and_i_manager` journey extension.**
  New spec (or extension of M32.3) covers full first-loop
  Incoming → structuring → In progress → read view.
  Fixture independence via new `seed_journey_fandi_intake_activation`
  seed command provisioning dedicated `Structure Sam`
  fixture. Financial-language regex assertion + consistency-
  warning coverage.
- **D9 — Latest-only posture locked.** Domain model
  preserved (M-to-1 iteration semantic unchanged); no
  one-structure constraint; no multi-structure UX in M33.
- **D10 — Future Lender Fit Recommendations candidate
  recorded.** Full design contract at planning time per
  operator directive: hard eligibility + likely fit +
  missing information + operator explanation + preserved
  human decision authority. NOT implemented in M33.
  Blocked on named prerequisites.

**Coverage delta at M33 close (projected):** 161 → 162
endpoints (+1 read endpoint at M33.1); 129 → 130 covered
(+1 M10.2 create becomes covered when M33.2 exercises it
via Playwright + Vitest; +1 M33.1 read endpoint covered
via M33.1 tests); 32 backend-only → 31 (net); 321 → 322
service verbs. Two-source agreement gate at M33.1 close
and again at M33.2 close.

## 8. Streaks at M33.0 close

- **Planning-time as-recommended streak:** 11 →
  **12** (projected at M33 close if no §0.a
  amendments). Target selected as recommended after
  seven-alternative comparison + nine-verification pass
  performed at user direction. Four verification-driven
  correction rounds (financial-language contract;
  deterministic ordering + tenant-scope; canonical
  endpoint path; strengthened truthful-entry with explicit
  affordance + basic consistency warning) shaped the final
  locked design but did not change the target selection.
  §0.a M33.0 amendments (none as of M33.0 open) do not
  affect the streak. Historical run of 89 across M10 →
  M23 preserved for the record.
- **Zero-drift permission-class streak:** unchanged at
  **36** (M10 → M32). M33.0 is planning-only; no code
  change. Projection at M33 close: **37 consecutive**
  (M33.1 adds 1 new endpoint reusing existing class;
  M33.2 no new endpoints).
- **Substrate-compound-value continuation:** M32 broke
  the M27.1 → M31 five-link streak by choosing breadth.
  M33 restarts the arc with M32 as link 1 (sales-to-F&I
  bridge) and M33 as link 2 (F&I first-loop activation).
  Framing per M32 §9 standing question resolution.
- **DoD exception path invocations:** 7. Projection at
  M33.1 close: **8** (M26 + M27.1 + M28.1 + M29.1 +
  M30.1 + M31.1 + M32.1 + M33.1). M33.2 satisfies DoD
  directly.
- **First milestone to activate M10.2 substrate
  operationally** — 19 sessions after M10.2 shipped at
  SESSION_107. Longest substrate-to-UI gap closed at
  M33.
- **Second consecutive customer-facing milestone in the
  F&I domain** (M32 shipped intake receiver; M33 ships
  first F&I action). Healthy F&I depth-arc continuation.
- **First milestone to lock a financial-language contract**
  at planning time (sales targets vs proposed structure
  values, with explicit rejection of lender-approved /
  lender-committed / actual). Candidate durable lesson
  at M33 retrospective §5 if the contract survives M33.2
  Playwright verification without drift.
- **First milestone to record a future capability
  (Lender Fit Recommendations) with full design contract
  at planning time** per operator directive. Design
  discipline demonstration — captured, deferred, blocked
  on named prerequisites; not implemented.
- **Verification-driven revision cycles (M32 candidate
  lesson z):** four revision rounds at M33.0 (financial-
  language; deterministic ordering; canonical path;
  truthful-entry strengthening). Second re-application
  since M32.0 origin; eligible for elevation at M33
  retrospective §5 to "load-bearing across two
  milestones."

## 9. Push status

**No push at SESSION_210 close.** M33.0 is planning-only
per the standard M28.0 / M29.0 / M30.0 / M31.0 / M32.0
cadence. Coordinated M33 close push deferred to explicit
user confirmation after M33.2 close, following the
M27 / M28 / M29 / M30 / M31 / M32 coordinated-close
cadence.

Local commits at SESSION_210 close:

- SESSION_210 planning memo
  (`docs/roadmap/MILESTONE_33_PLANNING.md`) + this
  handoff + `00-START-NEXT-SESSION.md` flip land in a
  single local-only commit per planning-only session
  cadence; hash backfill via a subsequent commit.

Expected M33 commit count at coordinated push: **4–6**
(planning + M33.1 backend + M33.2 UI + close-out fold,
plus hash-backfill follow-ups per convention).

## 10. Next session priorities

`00-START-NEXT-SESSION.md` overwritten for **SESSION_211
· Milestone 33 · Increment 1 (M33.1 — backend annotation
+ read endpoint + tests)**. First-thing sequence per
M28.1 / M29.1 / M30.1 / M31.1 / M32.1 pattern:

1. **Verify starting state** (git status; backend tests
   4,995 pass; frontend Vitest 377 pass; checks;
   migrations; tsc; redis;
   `db.acceptance.sqlite3` proactive reset).
2. **Confirm working from M33.0 planning memo** — read
   `docs/roadmap/MILESTONE_33_PLANNING.md` §5.b D1 +
   D2 + D3 + §5.e M33.1 before touching backend code.
3. **Ship M33.1 backend substrate** per §5.e:
   - Extend `list_credit_applications(...)` with
     `Exists(...)` + `Subquery(...)` annotations
     (D1 + D3). Both explicitly tenant-scoped in filter.
   - Extend `_project_credit_application_with_writeup(app)`
     with `has_deal_structure` + `latest_deal_structure_id`
     projection fields (D1 + D3).
   - Add `admin_deal_structure_read(request, pk)` view
     (D2). Thin wrapper on shipped
     `get_deal_structure(pk, dealership=dealership)`
     verb. Reuses shipped
     `_project_deal_structure(deal)` projection.
     `_M101_PERMS`. 404 fail-closed.
   - Add URL pattern
     `path("admin/deal-structures/<int:pk>/",
     views_f_and_i.admin_deal_structure_read,
     name="admin-deal-structure-read")` (canonical
     path verbatim).
   - Model docstring update on `DealStructure`
     (`models.py:4742+`) — reference new read endpoint.
   - Tests ~15 including annotation with 0 / 1 / N
     structures; deterministic tie-break under shared
     `created_at`; tenant-scoped subquery guard; read
     endpoint 200 / 404 unknown / 404 cross-tenant /
     403 non-F&I roles.
   - **Historical migration NOT modified.**
4. **Verify M33.1 close baselines:** backend suite 4,995
   → ~5,010 pass; `check` + `makemigrations --check`
   clean; audit artifact 161 → 162 endpoints / 129 →
   130 covered / 32 → 31 backend-only / 321 → 322
   service verbs.
5. **DoD exception path** — eighth invocation. Document
   in §3 of M33.1 handoff (queryset annotation + read
   endpoint has zero operator-facing behavior change
   on its own; M33.2 satisfies DoD directly).
6. **Ship the M33.1 handoff at
   `docs/handoffs/SESSION_211_m33_inc1_backend.md`.**
   **Do NOT push** — coordinated push at M33 close.

## 11. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_32_RETROSPECTIVE.md` §9
6. **`docs/roadmap/MILESTONE_33_PLANNING.md`** (governing
   contract for M33)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
8. `docs/CAPABILITY_MATRIX.md` §7η (M32 shipped surface);
   §7θ added at M33 close
9. `docs/handoffs/SESSION_209_m32_inc3_fandi_ui.md`
10. `docs/roadmap/MILESTONE_10_PLANNING.md` §1.2 (M10.2
    DealStructure origin — governs the M-to-1 iteration
    semantic that D9 preserves)
11. `docs/research/FINANCE_DEPARTMENT_MAPPING.md` §2 +
    §3.6 (F&I first-action + LTV / PTI / DTI semantics)
12. **This handoff** (`SESSION_210_m33_inc0_planning.md`)
13. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — applied at §4.6 for `vehicle_stock`
    discovery on writeup-originated vs direct-create CAs)
14. Memory record
    `feedback_duplicate_small_stable_logic.md` (M28.0
    origin — applicable at M33.2 for form validation
    helpers)
15. Memory record
    `feedback_playwright_as_operational_contract.md` (D8
    journey extends the operational contract to F&I
    first-loop; financial-language regex assertion
    strengthens the contract)
16. Memory record
    `feedback_terminal_output_discipline.md` (governs
    implementation-session output shape)
