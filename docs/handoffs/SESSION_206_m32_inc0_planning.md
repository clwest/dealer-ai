---
title: "SESSION_206 handoff — Milestone 32 · Increment 0 (M32.0 — planning refinement + target selection)"
status: active
type: handoff
date: 2026-08-04
session: 206
milestone: 32
milestone_status: active
milestone_name: "Deal Writeups: Sales-Manager-to-F&I Handoff (writeup CRUD substrate + sales-manager UI + F&I intake queue + provenance-FK migration)"
increment: 0
increment_status: shipped
commit: c3d46fd
commit_notes: "M32.0 planning session — local commit landed as c3d46fd at close per M28.0 / M29.0 / M30.0 / M31.0 planning-only cadence; hash backfilled via a subsequent commit; NOT pushed. Coordinated push at M32 close after explicit user confirmation."
---

# SESSION_206 — Milestone 32 · Increment 0 (M32.0 — planning refinement + target selection)

## What shipped

SESSION_206 opened as a planning-only session per the
M31.2 close-out priorities in `00-START-NEXT-SESSION.md`.
One deliverable landed:

1. **M32.0 planning memo** authored at
   `docs/roadmap/MILESTONE_32_PLANNING.md` — target locked
   as **NEW Deal Writeups: Sales-Manager-to-F&I Handoff**
   (§5.a). User-confirmed after direct evaluation against
   NEW C (F&I chargeback substrate), NEW O2/O3 (audit
   integrity), H (test hygiene), and fresh direct-operator
   gaps (deal writeups, vendor detail, photo reorder,
   broader F&I domain) under the primary operational-
   coverage lens with explicit application of the M31 §9
   breadth-vs-depth standing question. All §5.b–§5.h
   decisions locked (D1–D11, risk register R1–R11,
   verifications §4.1–§4.11, three-increment phasing, DoD
   compliance, rollback, non-goals). Three blocking
   findings (writeup pk discoverability, downstream F&I
   receiver, CA↔writeup pairing determinism) and two
   additional inaccessibility findings (F&I role access to
   `admin_lead_detail`, advisor viewer access to
   `LeadDetailModal`) surfaced at §4 verification and
   resolved architecturally before §5.b lock via D1 + D2
   (list + detail endpoints), D3 + D8 (CA list endpoint +
   non-navigational F&I intake page), D9-revised²
   (nullable OneToOneField with three-layer defense),
   D8-revised (non-navigational rows), and D4-revised²
   (transitively manager-only tab; no advisor treatment).

No §0.a M32.0 amendments — the first M31 CI run on
`08fef5f` (M31.2 hash-backfill commit) is green (workflow
`30938122737`, success in 2m57s at 2026-08-04T18:20:06Z);
no regression to correct.

Full active memo authored at
`docs/roadmap/MILESTONE_32_PLANNING.md`.

**Session artifacts:**

- **Starting-state verification (§1):** git clean; `HEAD
  == origin/main @ 08fef5f` (M31 push confirmed pre-
  session); Redis PONG; Django `check` clean;
  `makemigrations --check` clean; frontend `tsc --noEmit`
  clean; acceptance `tsc --noEmit` clean; backend suite
  **4,933 pass, 1 skipped, 0 fail** (164.9s); frontend
  Vitest **319 pass** (36 files, 5.78s); acceptance DB
  proactively reset per SESSION_200 §0.a durable lesson
  (v). All matches M31.2 close baseline exactly.
- **First M31 CI run monitored (§2):** acceptance workflow
  on `08fef5f` (M31.2 hash-backfill commit) **completed
  success** in 2m57s (Playwright 28 passed / 1.7m). Prior
  runs on `main` all successful. Main is CI-verified
  shipped at the M31.2 baseline. No §0.a M32.0 amendment
  triggered. Benign annotation only (Node 20 → 24
  deprecation notice on Actions runners; not a failure).
- **Audit regeneration (§3):** `python3 -m
  dealer_ai.scripts.audit_operational_surface` invoked.
  Output: **158 total / 124 covered / 34 backend-only /
  318 service verbs**. Byte-identical to the committed
  M31.2 artifact after reverting a cosmetic ordering diff
  in row 42 (frontend-consumer wrapper list ordering
  shifted; no coverage change; reverted to keep tree
  clean per planning-only session).
- **Candidate list presented (§4)** across the M31 §9
  tiers:
  - **Elevated (highest recommendation strength at
    M32.0):** NEW C — F&I chargeback substrate (gated
    pending pilot evidence); NEW O2 (M26/M27/M28/M29/
    M30/M31 deferral, unchanged); NEW O3 (deferral,
    unchanged); H — test-hygiene remediation.
  - **Fresh direct-operator gaps surveyed from audit
    backend-only list (breadth candidates per M31 §9
    standing question):** deal writeups (#112–114 —
    three-endpoint create/approve/hand-off flow, no
    operator evidence surfaced M28→M31, no frontend
    consumer today per `salesApi.ts:10-25` "UI deferred"
    comment); vendor detail (#43 wrapper-only, small
    polish); photo reorder (#65 wrapper-only, small
    polish); broader F&I domain surface (#89–101 excl.
    #101 chargeback = 12 uncovered endpoints).
  - **Gated:** T, U, L, M.
  - **Deferred pending evidence:** D.
  - **Deferred stable:** G.
  - **Deferred at M31 §3 / M30 §3 / M29 §3 / M28 §3 /
    M27 §3 / M25 §4:** all carried forward unchanged.
- **Recommendation (§5) and user confirmation:** NEW Deal
  Writeups: Sales-Manager-to-F&I Handoff, under the
  primary operational-coverage lens with breadth-vs-depth
  framing per M31 §9 standing question. Four load-bearing
  evidence signals recorded (§5.a of planning memo):
  1. Shipped-source deferral promise unfulfilled
     (`salesApi.ts:10-25` "UI deferred" nine sessions
     after M11.3 shipped).
  2. Largest un-gated direct operator-coverage gain of
     any M32 candidate (3 backend-only → 3 covered).
  3. Natural bridge domain — beachhead into F&I without
     the pilot-evidence gate.
  4. Answers M31 §9 breadth-vs-depth standing question
     with breadth after five consecutive accounting/
     templates selections.
  User confirmed §5.a; requested full workflow verification
  pass before §5.b–§5.h draft.
- **Verification pass (§4 of planning memo, §6 of this
  handoff):** eleven verifications performed at planning
  open; three blocking findings + two inaccessibility
  findings surfaced; all resolved architecturally before
  §5.b lock. See §6 of this handoff.
- **User review round 1:** identified four load-bearing
  issues in first §5.b–§5.h draft — DoD posture on M32.2
  (no exception; ship Playwright); fail-explicit query
  validation (revised from fail-closed-to-unfiltered);
  approval copy state-machine truthfulness (removed
  false re-approval advertisement); F&I destination
  accessibility (D8 non-navigational rows since
  `admin_lead_detail` is sales-role-gated). Plus three
  cleanups (R3 null-lead schema truthfulness; D3 pairing
  determinism; F&I page only if role gating supports).
  All resolved in second draft.
- **User review round 2:** identified four more load-
  bearing issues — one-to-one provenance link (upgraded
  from nullable FK to nullable OneToOneField with three-
  layer defense including service-level
  `DealWriteupAlreadyLinkedError`); historical migration
  0034 must not be retroactively rewritten (evolution
  recorded in current docstrings + migration 0051 + memos
  instead); M32.3 Playwright must be independently
  deterministic (new `seed_journey_fandi_intake_receipt`
  idempotent seed command provisioning `Intake Iris`
  fixture separate from any M32.2 fixture); non-manager
  Writeups-tab posture must reflect actual behavior
  (advisor cannot open modal at all — no visible-disabled
  tab possible or required). Plus three cleanups
  (`intake=false` semantics — reject with 400; M32.1
  rollback wording — not zero-writes; mandatory pairing-
  uniqueness test). All resolved in third draft.
- **All §5 locks confirmed by user.**

## 1. Verification results at open

- **git status:** clean; `HEAD == origin/main @ 08fef5f`.
- **git log --oneline -10:** shows the expected M31 commit
  sequence (M31.2 hash-backfill `08fef5f`; M31.2 close-
  out fold `4b5f5b9`; M31.1 hash-backfill `7c1cced`;
  M31.1 backend `b0e21a8`; M31.0 hash-backfill
  `5d12184`; M31.0 planning `f45a630`; M30.2 hash-backfill
  `f658c06`; M30.2 shipped `f1c26df`; M30.1 backend
  `6bb5b0f`; M30.0 planning `1956ed7`).
- **`python3 manage.py test dealer_ai`:** 4,933 pass, 1
  skipped, 0 fail (164.87s).
- **`cd frontend && npm test`:** 319 pass across 36
  files (5.78s).
- **`python3 manage.py check`:** clean (7 benign
  DecimalField warnings — pre-existing, unchanged).
- **`python3 manage.py makemigrations --check
  --dry-run`:** "No changes detected."
- **`cd frontend && npx tsc --noEmit`:** clean (no
  output).
- **`cd acceptance && npx tsc --noEmit`:** clean (no
  output).
- **`redis-cli ping`:** PONG.
- **`rm -f backend/db.acceptance.sqlite3`:** completed
  (no-op if absent) per SESSION_200 §0.a durable lesson
  (v).

All matches M31.2 close baseline exactly.

## 2. First M31 CI run

- **Workflow:** `acceptance` on `main`.
- **Latest run:** `30938122737` on `08fef5f` (M31.2 hash-
  backfill commit, top of `main`).
- **Result:** completed / success.
- **Duration:** 2m57s total (Playwright 28 passed / 1.7m).
- **Prior runs on `main`:** all successful (M30.2 hash-
  backfill `30930670900`; §0.a M30.0 amendment
  `30926157616`).
- **Benign annotation:** Actions runner forces Node.js
  20-targeted actions onto Node 24 (deprecation notice
  from GitHub; not a failure). Not blocking; not new.

**M31 is CI-verified shipped.** No §0.a M32.0 amendment
triggered.

## 3. Audit regeneration

- **Command:** `python3 -m dealer_ai.scripts.audit_operational_surface`.
- **Output:** 158 total / 124 covered / 34 backend-only /
  318 service verbs.
- **Artifact write:**
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`.
- **Diff:** cosmetic only — row 42 frontend-consumer
  wrapper list ordering shifted (`fetchVendor` moved to
  head of list). No coverage change; no total change.
  **Reverted** to keep tree clean per planning-only
  session cadence.
- **Byte-identical** to M31.2 committed baseline after
  revert.

**Two-source agreement** at M32.0 open: audit numbers
match the M31.2 handoff frontmatter and the M31 §7 anchor
(158 / 124 / 34 / 318).

## 4. Candidate list presented at open

Per M31 retrospective §9:

**Elevated (highest recommendation strength at M32.0):**

- **NEW C — F&I chargeback substrate.** Sixth-link
  substrate-compound-value candidate; still gated on
  pilot evidence today (unchanged from M30/M31 §9). No
  pilot direction has landed since M31 close. Correct to
  defer.
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (M26/M27/M28/M29/M30/M31 deferral). Requires SESSION-
  189-§3-style tracing at open. Blast radius unknown.
- **NEW O3 — Rows 1–4 plain-string-literal
  investigation** (M26/M27/M28/M29/M30/M31 deferral).
  Requires tracing.
- **H — Test-hygiene remediation.** Three shared-DB non-
  idempotent journeys unchanged from M27.2 → M31.2
  close. CI-stability compound value grows with journey
  count.

**Fresh direct-operator gaps surveyed (breadth candidates
per M31 retrospective §9 standing question):**

- **Deal writeups (audit #112–114)** — three-endpoint
  create/approve/hand-off flow; backend-only today; no
  frontend consumer per `salesApi.ts:10-25` "UI
  deferred" comment. No operator evidence surfaced
  M28→M31 but shipped-source deferral promise reads as
  an operator-safety-promise-fulfillment candidate.
- **Vendor detail (#43)** — GET/PATCH wrapper-only;
  small polish; low coverage gain standalone.
- **Photo reorder (#65)** — wrapper-only; small polish;
  requires D&D primitive selection.
- **F&I domain surface (#89–101 excl. #101 chargeback)**
  — 12 uncovered endpoints; entire subdomain unwired;
  too large without operator direction.

**Gated (unchanged from M29+M30+M31 close):**

- T (real tester feedback); U (hosted-demo substrate);
  L (first-live-pilot staging); M (multi-operator
  support — breaks the M10 → M31 zero-drift streak with
  intent).

**Deferred pending evidence:**

- D (LLM router / cost caps).

**Deferred but stable:**

- G (dashboard testid hardening).

**Deferred at M31 §3 / M30 §3 / M29 §3 / M28 §3 / M27
§3 / M25 §4:** all carried forward unchanged.

## 5. Recommendation and user confirmation

**Primary recommendation:** NEW Deal Writeups: Sales-
Manager-to-F&I Handoff.

**Rationale under the primary operational-coverage lens:**

- **Largest un-gated direct operator-coverage gain of any
  candidate:** 3 backend-only endpoints (#112–114) → 3
  covered in one milestone. No other un-gated candidate
  on the list moves the covered-count needle by 3.
- **Natural bridge domain — beachhead into F&I without
  the pilot-evidence gate:** sales domain is already
  covered (leads #106–109, test drives #110–111,
  cadences/tasks #115–118); F&I is mostly uncovered
  (#89–101). Deal writeups sit at the seam and connect
  the two departments the operator most needs stitched
  together.
- **Answers M31 §9 breadth-vs-depth standing question:**
  shifts out of the accounting/templates domain after 5
  consecutive selections (M27.1 → M31) into a genuinely
  new surface, per the operator-coverage-benefits-from-
  breadth-after-depth framing.
- **Endpoint semantics suggest a discoverable workflow:**
  create → approve → hand-off. The three-endpoint shape
  mirrors approved patterns (e.g., work orders create/
  approve/complete #46/47/49).

**Tradeoffs named explicitly** (not papered over):

1. Zero operator evidence surfaced M28→M31 — recommendation
   is workflow-inference from endpoint naming + audit
   position + shipped-source deferral promise, not
   evidence-driven.
2. Does not continue substrate-compound-value depth arc.
3. FK discoverability verification required at §5.b per
   memory `feedback_verify_fk_discoverability_before_lock`
   (M27.0 durable lesson).
4. Backend-substrate state unknown at recommendation
   time; verification pass required before §5.b lock.

**Alternatives with explicit tradeoffs:**

- H — test hygiene: bounded, un-gated, CI-stability
  compound value; zero direct operator-coverage gain.
- NEW C — F&I chargeback: highest ceiling, pilot-
  evidence-gated. Recommend only if pilot evidence
  surfaces.
- NEW O2 + NEW O3 — audit-substrate integrity:
  compelling only if audit fidelity is blocking a
  specific upcoming lock-in. Audit currently
  conservative-in-the-right-direction; deferring is
  defensible.
- Vendor detail / Photo reorder: small polish; low
  standalone coverage gain.

**User confirmation:** Deal Writeups locked as §5.a;
requested full workflow verification pass before drafting
§5.b–§5.h; requested §5 draft address the eight-item
verification checklist (model / serializers / service /
views / permissions / FK discovery / state machine /
role separation / hand-off target semantics / downstream
receiver / sales-side context / three-endpoint
sufficiency); requested honest-milestone-shape presentation
if any surface missing before locking §5.b.

## 6. Verifications performed at planning-open

Eleven verifications performed. Three surfaced blocking
findings; two surfaced inaccessibility findings; all
resolved architecturally before §5.b lock. See
`docs/roadmap/MILESTONE_32_PLANNING.md` §4 for full
detail.

### 6.1 Model + FK inspection

- `DealWriteup` (`migrations/0034_m113_deal_writeup_entity.py`)
  — mandatory FKs to dealership + lead + vehicle (all
  CASCADE, non-nullable); optional user attributions
  (SET_NULL); terms fields all optional Decimal; state
  timestamps `write_up_at` (required), `sales_manager_approved_at`,
  `handed_off_to_fandi_at`.
- `CreditApplication` (`models.py:4454+`) — mandatory
  dealership FK; nullable lead + sale FKs (both SET_NULL)
  per M10.1 §5.a Option C retention-of-record semantics.
- **Asymmetric lifecycle contract identified:**
  `DealWriteup.lead` CASCADE-deletes; `CreditApplication.lead`
  becomes NULL. Deliberate — CA is legal record-of-record
  with 7-year retention. Documented in R3.

### 6.2 Service verb inspection

- `services/deal_writeups/deal_writeup.py` — three verbs:
  `record_deal_writeup` (cross-tenant FK check →
  `CrossTenantDealWriteupError`); `approve_deal_writeup`
  (idempotent — overwrites approver + timestamp on
  re-approval); `hand_off_to_fandi` (`@transaction.atomic`;
  `WriteupNotApprovedError`; `WriteupAlreadyHandedOffError`;
  auto-creates CA via `record_credit_application`).
- `services/f_and_i/credit_application.py` —
  `record_credit_application` (M10.1 direct create;
  model-layer retention enforcement).

### 6.3 State machine + role separation

- Derived state via timestamp presence: `{created}` →
  `{approved}` → `{handed_off}` (once only).
- Re-approval verified via
  `test_re_approval_overwrites` — overwrites approver +
  timestamp. **Not exposed in M32 UI** since no PATCH
  surface and no re-open surface exist.
- All three verbs gated on
  `IsSalesManagerOrOwnerAtActiveDealership`.
- **Anchor question corrected** — "sales manager" not
  "salesperson" (M11.3 gates create on manager-only).

### 6.4 FK / identifier discoverability for CREATE

- `lead_id` — discoverable via `LeadDetailModal` (M24.1+).
- `vehicle_id` — discoverable via `listAdminVehicles`
  (M11.2/M11.6).
- **CLEAN** — no new discovery surface required for
  create.

### 6.5 FK / identifier discoverability for APPROVE /
HAND-OFF — **BLOCKING**

- Writeup `pk` not discoverable — no list endpoint, no
  detail endpoint, no frontend wrapper.
- **Resolved by D1 + D2** (writeup list + detail
  endpoints in M32.1 substrate).

### 6.6 Downstream F&I UI receiver — **BLOCKING**

- Zero frontend files reference `CreditApplication`.
- `admin/credit-applications/` is create-only; no list;
  no detail.
- `DealerFandIDeals` is contract-keyed; excludes pre-
  contract CAs.
- Zero acceptance journeys exercise deal-writeup flow.
- **Resolved by D3 + D8** (credit-app list endpoint +
  non-navigational F&I intake page).

### 6.7 CA ↔ DealWriteup pairing determinism —
**BLOCKING**

- Only structural link today is text prefix in CA
  `notes` written by `_format_handoff_notes`
  (fragile — operator-writable field).
- One lead can have N writeups → N CAs, all sharing
  `lead` FK. Non-deterministic.
- **Resolved by D9-revised²** (nullable OneToOneField
  `credit_application.deal_writeup` with three-layer
  defense: DB unique via OneToOne + service
  `DealWriteupAlreadyLinkedError` + M11.3
  `WriteupAlreadyHandedOffError`).
- **Historical migration 0034 NOT modified.**
  Architectural evolution recorded in current
  `models.py` docstrings on `CreditApplication` +
  `DealWriteup`, service docstrings on
  `record_credit_application` + `hand_off_to_fandi`,
  migration 0051 docstring, this planning memo, M32
  retrospective, and `docs/CAPABILITY_MATRIX.md` §7η.

### 6.8 F&I role access to `admin_lead_detail` —
**BLOCKING for prior D8 draft**

- `admin_lead_detail` (`views.py:847-848`) gated on
  `IsSalesManagerOrOwnerAtActiveDealership`. F&I gets
  403.
- Prior D8 draft promised row-link to lead detail;
  would ship broken 403 link.
- **Resolved by D8-revised** (non-navigational F&I
  intake rows; all triage info rendered inline).

### 6.9 Advisor viewer `LeadDetailModal` access —
**BLOCKING for prior D4 draft**

- Same `IsSalesManagerOrOwnerAtActiveDealership` gate
  excludes advisor viewers. Modal cannot open at all
  (403 → modal error branch renders).
- Prior D4 draft promised visible-but-disabled tab for
  advisors; unshippable — advisors never see the modal.
- **Resolved by D4-revised²** (transitively manager-
  only tab; no advisor treatment possible or required).

### 6.10 Playwright role transition + persona registry

- Existing personas: platform_operator, owner,
  sales_manager, recon_manager, bhph_collector.
- **No `f_and_i_manager` persona.**
- Existing multi-persona pattern (owner + sales_manager
  use `AUTH_STORAGE.*` per-persona storage-state files).
- **Resolved by D11** (M32.3 adds `f_and_i_manager`
  persona + new `seed_journey_fandi_intake_receipt`
  idempotent seed command provisioning both persona and
  independent `Intake Iris` fixture).

### 6.11 DoD compliance check

- M32.1 invokes DoD exception path #7 (M26 + M27.1 +
  M28.1 + M29.1 + M30.1 + M31.1 + M32.1).
- M32.2 satisfies DoD directly (new `sales-manager-
  writeup-handoff` describe block).
- M32.3 satisfies DoD directly (new
  `fandi-intake-receipt` describe block using pre-
  seeded independent fixture).
- **No customer-facing increment ships without journey
  coverage.**

## 7. §5 locks summary

All eleven §5.b design decisions locked in the memo (D1–
D11). Highlights:

- **D1 — Writeup list endpoint: fail-explicit filter
  validation.** `state` allowlist; invalid values return
  400 (not silent unfiltering). Explicit test matrix
  including case-sensitivity + empty-but-present + malformed.
- **D2 — Writeup detail endpoint: read-only projection.**
  No PATCH/DELETE — activation-vocabulary-asymmetry per
  M31 lesson w.
- **D3 — Credit-application list endpoint: F&I intake
  queue with fail-explicit validation.** `intake=true`
  only (accepts) / `intake=false` rejects with 400 /
  omission = unfiltered. First F&I-role-gated list
  endpoint. Projection includes writeup context via new
  D9 FK.
- **D4 — Sales-manager entry point: manager-only Writeups
  tab on LeadDetailModal (revised²).** Transitively
  manager-only by virtue of modal itself. No advisor tab
  treatment (advisor cannot open modal at all).
- **D5 — Approve action: state-machine-truthful
  confirmation copy.** *"Approving marks this writeup
  ready for F&I hand-off. Review the terms carefully
  before continuing. After it is sent to F&I, the hand-off
  cannot be repeated or undone."* No false re-approval
  advertisement (re-approval remains backend contract but
  is not an M32 UI operator path).
- **D6 — Hand-off action: irreversibility-flagged
  confirmation.** *"This cannot be undone — a second
  attempt will be refused to protect against duplicate
  applications and their retention-clock consequences."*
- **D7 — Writeup state visual signals (three-signal
  a11y per M31 D6).** Badge + row aria-label + testids
  (double marker `writeup-row-state-<state>-<pk>`).
- **D8 — F&I intake queue: new page, non-navigational
  rows, all intake info inline (revised).** All triage
  fields rendered inline (lead name/phone/email; vehicle
  stock/description; four-square terms; notes verbatim;
  written-up-by; approved-by; hand-off timestamp). No
  lead-detail link (would 403 for F&I).
- **D9 — CreditApplication carries a nullable
  OneToOneField backpointer to DealWriteup (revised²).**
  Three-layer defense: DB unique (OneToOne) + service
  `DealWriteupAlreadyLinkedError` + M11.3
  `WriteupAlreadyHandedOffError`. Nullable + SET_NULL
  preserved for direct-created + historical CAs. Peer-
  with-optional-backpointer semantics; retention-clock
  ownership stays on CA.
- **D10 — Role gating: reuse existing permission classes;
  zero-drift streak preserved.** 33 → 34 → 35 → 36.
- **D11 — New Playwright persona: f_and_i_manager.**
  M32.3 substrate. New idempotent seed command provisions
  persona + independent `Intake Iris` fixture.

**Coverage delta at M32 close (projected):** 158 → 161
endpoints (+3); 124 → 127 covered (+3); 34 backend-only
unchanged (three backend-only endpoints #112–114 remain
backend-only at M32.1 close since UI ships in M32.2/
M32.3; re-classify at M32 close-out per M31 precedent);
318 → 321 service verbs. Two-source agreement gate at
M32.3 close.

## 8. Streaks at M32.0 close

- **Planning-time as-recommended streak:** 10 → **11**.
  Target selected as recommended after seven-alternative
  comparison + eleven-verification pass performed at user
  direction. Two verification-driven revision rounds (D3
  fail-explicit; D4-revised² manager-only tab; D8-revised
  non-navigational rows; D9-revised² OneToOneField with
  three-layer defense) shaped the final locked design but
  did not change the target selection. §0.a M32.0
  amendments (none as of M32.0 open) do not affect the
  streak. Historical run of 89 across M10 → M23 preserved
  for the record.
- **Zero-drift permission-class streak:** unchanged at
  **33** (M10 → M31). M32.0 is planning-only; no code
  change. Projection at M32 close: **36 consecutive**
  (M32.1 adds 3 endpoints reusing existing classes;
  M32.2 + M32.3 no new endpoints).
- **Substrate-compound-value continuation:** 5 links
  unchanged. M27.1 → M28.1 → M29 → M30 → M31 preserved
  as the depth arc. M32 chooses breadth (fresh direct-
  operator gap in sales-to-F&I workflow) over depth
  (sixth substrate-compound-value link would have been
  NEW C, still pilot-evidence-gated). M31 §9 breadth-vs-
  depth standing question resolved with breadth answer.
- **DoD exception path invocations:** 6. Projection at
  M32.1 close: **7** (M26 + M27.1 + M28.1 + M29.1 +
  M30.1 + M31.1 + M32.1). M32.2 + M32.3 satisfy DoD
  directly.
- **First break out of accounting/templates domain since
  M27** (six milestones ago). Signals healthy operator-
  coverage domain diversification.
- **First schema-level pairing constraint added to
  DealWriteup ↔ CreditApplication seam** (M32.1).
  Evolutionary step from M11.3 peer-not-child preference
  to M32 peer-with-optional-backpointer, recorded
  truthfully in current docstrings + migration 0051 +
  memos.
- **First milestone since M20 to add a new Playwright
  persona** (`f_and_i_manager`). Existing multi-persona
  pattern followed exactly.
- **First customer-facing milestone since M11 to ship
  across three increments.** Scope-driven per §4
  verification findings.
- **Playwright-independent-fixture pattern (NEW):** M32.3
  seed-command approach establishes idempotent independence
  guarantee for downstream-receiver journeys. Candidate
  for durable lesson elevation at M32 retrospective §5
  if re-applies at M33+.

## 9. Push status

**No push at SESSION_206 close.** M32.0 is planning-only
per the standard M28.0 / M29.0 / M30.0 / M31.0 cadence.
Coordinated M32 close push deferred to explicit user
confirmation after M32.3 close, following the M27 / M28
/ M29 / M30 / M31 coordinated-close cadence.

Local commits at SESSION_206 close:

- SESSION_206 planning memo
  (`docs/roadmap/MILESTONE_32_PLANNING.md`) + this
  handoff + `00-START-NEXT-SESSION.md` flip land in a
  single local-only commit per planning-only session
  cadence; hash backfill via a subsequent commit.

Expected M32 commit count at coordinated push: **6–8**
(planning + M32.1 backend + M32.2 UI + M32.3 F&I UI +
close-out fold, plus hash-backfill follow-ups per
convention).

## 10. Next session priorities

`00-START-NEXT-SESSION.md` overwritten for **SESSION_207
· Milestone 32 · Increment 1 (M32.1 — backend substrate
+ provenance-FK migration)**. First-thing sequence per
M28.1 / M29.1 / M30.1 / M31.1 pattern:

1. **Verify starting state** (git status; backend tests
   4,933 pass; frontend Vitest 319 pass; checks;
   migrations; tsc; redis; `db.acceptance.sqlite3`
   proactive reset).
2. **Confirm working from M32.0 planning memo** — read
   `docs/roadmap/MILESTONE_32_PLANNING.md` §5.b D1 + D2
   + D3 + D9 + §5.e M32.1 before touching backend code.
3. **Ship M32.1 backend substrate** per §5.e:
   - Migration `0051_m32_credit_application_deal_writeup_fk.py`
     — add nullable OneToOneField.
   - Service verb `list_deal_writeups` (D1).
   - Service verb `get_deal_writeup` (D2).
   - Service verb `list_credit_applications` (D3).
   - Update `hand_off_to_fandi` to set FK (2-line change
     inside existing atomic block).
   - Update `record_credit_application` signature +
     add `DealWriteupAlreadyLinkedError` service-layer
     guard.
   - Endpoint `admin/deal-writeups/` (GET) reusing
     `_M113_PERMS`.
   - Endpoint `admin/deal-writeups/<int:pk>/` (GET)
     reusing `_M113_PERMS`.
   - Endpoint `admin/credit-applications/` (GET) reusing
     `IsFinanceManagerOrOwnerAtActiveDealership`.
   - Model docstring updates on `CreditApplication` +
     `DealWriteup` per D9-revised² Point 2.
   - Service docstring updates on `hand_off_to_fandi` +
     `record_credit_application`.
   - **Historical migration 0034 NOT modified.**
   - Tests ~51 including mandatory
     `test_writeup_cannot_link_to_multiple_credit_applications`
     exercising all three defense layers.
4. **Verify M32.1 close baselines:** backend suite 4,933
   → ~4,984 pass; `check` + `makemigrations --check`
   clean; audit artifact 158 → 161 endpoints / 124
   covered unchanged at M32.1 (three new endpoints
   backend-only at M32.1; re-cover at M32.2 + M32.3).
5. **DoD exception path** — seventh invocation. Document
   in §3 of M32.1 handoff (no operator-facing behavior
   change on its own; M32.2 + M32.3 satisfy DoD
   directly).
6. **Ship the M32.1 handoff at
   `docs/handoffs/SESSION_207_m32_inc1_backend.md`.**
   **Do NOT push** — coordinated push at M32 close.

## 11. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_31_RETROSPECTIVE.md` §9
6. **`docs/roadmap/MILESTONE_32_PLANNING.md`** (governing
   contract for M32)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
8. `docs/CAPABILITY_MATRIX.md` §7ζ (M31 shipped surface);
   §7η added at M32 close
9. `docs/handoffs/SESSION_205_m31_inc2_frontend.md`
10. `docs/roadmap/MILESTONE_11_PLANNING.md` §7 M11.3
    (M11.3 DealWriteup entity origin — governs the
    architectural preference that M32.1 D9-revised²
    evolves)
11. **This handoff** (`SESSION_206_m32_inc0_planning.md`)
12. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs M32.2 co-located inline-
    dialog choice)
13. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified through M32.0 §4.5 for
    APPROVE / HAND-OFF discoverability)
14. Memory record
    `feedback_playwright_as_operational_contract.md`
    (M32.2 + M32.3 Playwright journeys are the
    operational contract; independent fixture guarantee
    at M32.3 is a strengthening)
