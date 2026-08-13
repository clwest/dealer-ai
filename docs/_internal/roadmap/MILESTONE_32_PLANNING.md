---
title: "Milestone 32 — Deal Writeups: Sales-Manager-to-F&I Handoff (writeup CRUD substrate + sales-manager UI + F&I intake queue + provenance-FK migration)"
status: active
type: planning-memo
generated: 2026-08-04
generated_at_session: SESSION_206 (skeleton + expansion + all §5 locks)
milestone: 32
milestone_name: "Deal Writeups: Sales-Manager-to-F&I Handoff (writeup CRUD substrate + sales-manager UI + F&I intake queue + provenance-FK migration)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_11_PLANNING.md (M11.3 DealWriteup entity + service verbs + endpoints)
  - docs/roadmap/MILESTONE_31_PLANNING.md
  - docs/roadmap/MILESTONE_31_RETROSPECTIVE.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7ζ
  - backend/dealer_ai/models.py (CreditApplication M10.1 record-of-record + DealWriteup M11.3 entity)
  - backend/dealer_ai/migrations/0034_m113_deal_writeup_entity.py (DealWriteup schema)
  - backend/dealer_ai/services/deal_writeups/deal_writeup.py (M11.3 record / approve / hand-off verbs)
  - backend/dealer_ai/services/f_and_i/credit_application.py (M10.1 record_credit_application verb)
  - backend/dealer_ai/views_deal_writeups.py (M11.3 create / approve / hand-off endpoints)
  - backend/dealer_ai/views_f_and_i.py (M10.1 CA create + M10.7 F&I deals list)
  - backend/dealer_ai/views.py (admin_lead_detail — sales-manager-gated)
  - backend/dealer_ai/permissions.py (IsSalesManagerOrOwnerAtActiveDealership + IsFinanceManagerOrOwnerAtActiveDealership)
  - backend/dealer_ai/urls.py (M11.3 + M10.1 + M10.7 URL patterns)
  - frontend/src/lib/salesApi.ts (M11.6 sales operator UI — "UI deferred" comment on writeup verbs)
  - frontend/src/lib/fAndIApi.ts (M10.7 F&I operator UI — contract-keyed deals list)
  - frontend/src/components/LeadDetailModal.tsx (M24.1+ lead-context anchor surface)
  - frontend/src/pages/DealerFandIDeals.tsx (M10.7 F&I contract-in-progress list)
  - acceptance/support/auth/personas.ts (existing personas: platform_operator, owner, sales_manager, recon_manager, bhph_collector)
  - acceptance/support/auth/login.setup.ts (idempotent seed + login pattern per M20)
---

# Milestone 32 — Deal Writeups: Sales-Manager-to-F&I Handoff (writeup CRUD substrate + sales-manager UI + F&I intake queue + provenance-FK migration)

> **Active planning memo.** Drafted + expanded + all §5 locks at
> SESSION_206 M32.0 open.
>
> **§5.a locked at open** as **NEW Deal Writeups: Sales-Manager-
> to-F&I Handoff**, under the *primary operational-coverage lens*
> (durable since M22 close) evaluated via a full workflow
> verification pass that surfaced three blocking findings before
> scope-lock. Deal writeups was selected against the M31 §9
> standing question (breadth vs. depth after five consecutive
> accounting/templates selections M27.1 → M31) as the largest
> un-gated direct operator-coverage gain on the M32 candidate
> list — three backend-only endpoints (#112–114) → three covered
> in a single milestone, bridging the sales domain (fully covered
> M11.1–M11.6) to the F&I domain (mostly uncovered #89–101).
>
> **The anchor business question** — *Can a sales manager create
> a deal writeup, review and approve it, and hand it off to F&I
> such that the F&I team receives a complete, actionable incoming
> credit application with unambiguous provenance — all through
> Dealer OS?* — governs every M32 scope decision.
>
> **Three blocking findings surfaced at §4 verification and
> resolved architecturally before §5.b lock.**
>
> 1. **Writeup pk not discoverable** post-create (approve + hand-
>    off both operate on `<pk>` but M11.3 shipped no list or
>    detail endpoint). Resolved by D1 + D2 — writeup list + detail
>    substrate in M32.1.
> 2. **No downstream F&I UI receiver for handoff.** Zero frontend
>    files reference `CreditApplication`; no list endpoint on the
>    backend; `DealerFandIDeals` is contract-keyed (excludes pre-
>    contract CAs). Resolved by D3 + D8 — credit-application list
>    substrate + new non-navigational F&I intake page.
> 3. **CA ↔ DealWriteup pairing non-deterministic.** Only link
>    today is a text prefix in `CreditApplication.notes` written
>    by `_format_handoff_notes` — one lead can have N writeups →
>    N CAs, all sharing `lead` FK. Resolved by D9-revised² —
>    nullable `OneToOneField` from `CreditApplication` to
>    `DealWriteup` in a new migration, three-layer defense (DB
>    unique + service-layer `DealWriteupAlreadyLinkedError` +
>    M11.3 `WriteupAlreadyHandedOffError`).
>
> **Two additional findings resolved by making implicit
> promises truthful.**
>
> 4. **F&I role access to `admin_lead_detail` denied** (endpoint
>    gated on `IsSalesManagerOrOwnerAtActiveDealership`). Prior
>    D8 draft promised a row-link that would 403. Resolved by
>    D8-revised — F&I intake rows are **non-navigational**; every
>    triage field rendered inline. F&I-scoped lead-context view
>    deferred to M33+ evidence-gated.
> 5. **Advisor viewers cannot open `LeadDetailModal`** at all
>    (modal transitively manager-gated). Prior D4 draft promised
>    a visible-but-disabled Writeups tab for advisors. Resolved
>    by D4-revised² — no advisor treatment on the Writeups tab
>    is possible or required; the tab is manager-only by
>    transitivity of the modal itself.
>
> **First break out of the accounting/templates domain since
> M27.1** (five consecutive planning-time selections M27.1 →
> M31). Answers the M31 §9 standing question with breadth after
> depth — operator-coverage lens favored a fresh direct-operator
> gap over a sixth substrate-compound-value link (F&I chargeback
> NEW C remained gated on pilot evidence at M32.0 open).
>
> **First customer-facing milestone that ships across three
> increments** (M28 through M31 were all two-increment
> substrate+UI shapes). Rationale: two independent frontend
> receivers (sales-manager UI on `LeadDetailModal`, F&I UI on new
> `/dealer-ai-f-and-i/incoming` page) each with distinct role
> gating and each requiring independent Playwright coverage per
> the "no exception on customer-facing UI" DoD posture applied
> at M32.2. Three-increment shape is scope-driven, not
> convention-driven — the alternative (bundling both UIs into
> M32.2) would have made the increment large enough to violate
> the M28→M31 "one bounded increment" discipline.
>
> **First milestone since M20 to add a new Playwright persona.**
> `f_and_i_manager` persona addition surfaces at M32.3 as
> substrate work — new entry in `personas.ts`, new seed
> provisioning, new `AUTH_STORAGE.fAndIManager` storage-state
> file. Existing multi-persona pattern (owner + sales_manager)
> is the precedent.
>
> **First milestone to add a schema-level pairing constraint.**
> The `CreditApplication.deal_writeup` nullable `OneToOneField`
> introduced at M32.1 is the smallest structural change that
> makes hand-off provenance deterministic without violating the
> M10.1 retention-clock record-of-record semantics or the M11.3
> peer-not-child architectural preference. Three-layer defense
> (DB unique via OneToOne + service-layer
> `DealWriteupAlreadyLinkedError` + M11.3
> `WriteupAlreadyHandedOffError`) prevents duplicate CAs from
> any caller path.

## 0.a Change log (implementation-time amendments)

Per M5–M31 §0.a mandates, load-bearing planning decisions may
need narrow amendment at implementation time as substrate
reality asserts itself. Every amendment records the session,
option, and the affected sections.

_None yet at M32.0._

## 1. Context

### 1.1 Why now

Four forces converge to make sales-manager-to-F&I handoff the
highest-value bounded M32 target:

1. **Backend-only endpoints #112–114 shipped in M11.3 with an
   explicit "UI deferred" comment** at
   `frontend/src/lib/salesApi.ts:10-25`:
   > *"M11.6 §5.f.2 scope: leads / test-drives / follow-ups /
   > be-backs pages ship; deal-writeup UI deferred. This module
   > exposes the full surface (writeup verbs included) so the
   > follow-on doesn't need to re-declare types."*
   Nine sessions later the "follow-on" has not landed and the
   comment reads as a shipped promise the frontend has not
   fulfilled. Same posture as M30.2's Delete-confirmation
   Restore-promise that M31 was elevated to close.
2. **The sales → F&I workflow has an unbridged operator gap.**
   Every dealership deal transitions from sales floor to F&I
   office at the moment a manager approves a writeup and hands
   it off. Today this transition happens outside Dealer OS —
   the M11.3 API exists but has no operator UI on either side,
   so the workflow is entirely paper/verbal. Handoff quality
   (four-square terms, approver identity, timing) is invisible
   to the F&I intake process.
3. **The F&I intake queue does not exist as a Dealer OS
   surface.** `DealerFandIDeals` shows contracts-in-progress
   (post-hand-off, post-credit-decision, post-structure). There
   is no view of *incoming* credit applications awaiting F&I
   triage. When a hand-off does happen through the M11.3 API
   (backend-only today), the resulting CA is invisible to
   every frontend surface — a genuine dead-drop.
4. **Substrate is at 80%+ readiness.** M11.3 create / approve /
   hand-off verbs and endpoints ship and are unchanged. M10.1
   `record_credit_application` verb exists and hand-off already
   calls it in an atomic block. `admin/f-and-i/deals/` list
   endpoint pattern is well-established (M10.7). Vehicle
   discovery via `listAdminVehicles` already exists
   (M11.2/M11.6). Lead discovery via `LeadDetailModal` is the
   established context anchor (M24.1+). What's missing is (a)
   writeup list + detail read surfaces, (b) CA list surface,
   (c) provenance FK for deterministic pairing, and (d) two
   operator UIs on the manager and F&I sides.

### 1.2 What the operator gets

At M32 close:

- **Sales-manager side (`LeadDetailModal` → new "Writeups"
  tab):**
  - Per-lead writeup list showing state (Pending / Approved /
    Handed off) via three-signal a11y rendering (Badge +
    row aria-label + testids).
  - "+ New writeup" CTA opening an inline four-square form
    with vehicle picker (reuses existing `listAdminVehicles`).
  - Inline Approve button on Pending rows → confirmation
    dialog with copy matching the actual state machine
    ("Approving marks this writeup ready for F&I hand-off.
    Review the terms carefully before continuing. After it is
    sent to F&I, the hand-off cannot be repeated or undone.").
  - Inline Send-to-F&I button on Approved rows → confirmation
    dialog explicitly naming irreversibility ("This cannot be
    undone — a second attempt will be refused to protect
    against duplicate applications and their retention-clock
    consequences.").
  - Handed-off rows are read-only history with attribution
    (written-up-by + approved-by + hand-off timestamp).
- **F&I side (new `/dealer-ai-f-and-i/incoming` page):**
  - Non-navigational F&I intake queue keyed on incoming
    credit applications (CAs without a Contract row —
    pre-contract).
  - Each row renders inline: lead name + phone + email;
    vehicle stock + description; full four-square terms;
    CA notes (verbatim M11.3 `_format_handoff_notes` output);
    written-up-by; approved-by; hand-off timestamp; "Incoming"
    state badge.
  - Empty state: *"No incoming applications. Credit
    applications from sales-manager hand-offs appear here."*
  - Navigation link "Incoming" adjacent to existing "Deals"
    in F&I side nav.
- **Deterministic provenance link** — every hand-off-created
  CA carries a `deal_writeup` OneToOneField backpointer set
  in the same atomic block as the hand-off timestamp. Direct-
  created CAs (M10.1 direct path) keep `deal_writeup=NULL`.
  Three-layer defense against duplicate pairings.
- **A fulfilled shipped promise.** The `salesApi.ts:10-25`
  "UI deferred" comment removed in M32.2 — no shipped source
  file carries a stale "deferred" reference after M32 close.

### 1.3 What the operator does not get at M32

Explicitly out of scope — carried as future re-entry
candidates or evidence-gated:

- **Salesperson-authored writeups.** M11.3 gating (sales
  manager / owner only) preserved. Broader role expansion
  requires selective permission-class work and is M33+
  evidence-gated.
- **Writeup edit (PATCH).** Activation-surface-asymmetry
  preservation per M31 lesson w. Re-approval remains a
  backend contract (M11.3) but is not exposed in M32 UI —
  Approved rows hide the Approve button.
- **Cross-lead sales-manager pending-approval queue page.**
  Assumption per §5.c R6: same-day approval happens via
  `LeadDetailModal`. Elevate if operator evidence surfaces.
- **F&I-scoped lead-context view or per-CA detail page.**
  D8 non-navigational intake rows carry all triage info
  inline. Elevate to M33+ as either (a) new endpoint
  `GET /admin/f-and-i/lead-context/<lead_id>/` gated on F&I
  role with narrowed projection, or (b) selective role-gating
  expansion on `admin_lead_detail` with explicit review of
  what leaks to F&I.
- **Separation-of-duties enforcement** (approver ≠ writer).
  Matches M11.3 shipped behavior. Multi-user policy is M33+.
- **Pagination / server-side sort** on the 3 new list
  endpoints. Matches M10.7 / M11 sales substrate precedent
  (100-row cap defer). Elevate if evidence.
- **Websocket / auto-refresh** of F&I intake queue or
  Writeups tab. Accepted stale-tab race per M31 R1 precedent.
- **F&I workflow state extensions on intake rows** (In
  progress / Structuring / Submitted to lender / etc.). M32
  intake rows carry the single "Incoming" state. Extending
  is a separate future milestone with F&I-workflow scope.
- **`intake=false` as an operator filter.** Reserved-and-
  rejected value in M32 to preserve semantic clarity
  ("intake" refers to *the incoming queue*, not a boolean
  toggle of contract presence). Use a distinct future param
  (e.g. `has_contract=true`) if the already-contracted
  filter surfaces evidence.
- **Backfill of `credit_application.deal_writeup` for
  existing rows.** Existing CAs stay NULL (truthful — they
  were not created via hand-off). Only new hand-offs
  populate.
- **Any modification to M11.3 M10.1 M10.7 shipped surfaces**
  except the four surgical M32.1 changes documented in D9-
  revised² (models.py docstring updates on CreditApplication
  + DealWriteup; `hand_off_to_fandi` writes new FK;
  `record_credit_application` accepts new optional kwarg
  and raises new `DealWriteupAlreadyLinkedError`) and one
  M32.2 change (removal of `salesApi.ts:10-25` "UI deferred"
  comments).

## 2. Increment structure

**Three increments — scope-driven three-way split. First
customer-facing milestone since M11 to ship across three
increments; every prior M28→M31 customer-facing milestone
was two increments (substrate + UI).**

- **M32.1 (SESSION_207) — Backend substrate + provenance-FK
  migration.** New writeup list + detail endpoints (D1 + D2);
  new credit-application list endpoint (D3); new
  `credit_application.deal_writeup` nullable OneToOneField
  migration (D9-revised²); new `DealWriteupAlreadyLinkedError`
  service-layer error class; `hand_off_to_fandi` updated to
  set FK inside its existing atomic block;
  `record_credit_application` signature-additive `deal_writeup`
  kwarg + service-layer guard; ~51 tests (including the
  mandatory `test_writeup_cannot_link_to_multiple_credit_applications`).
  **DoD exception path invocation #7** (M26 + M27.1 + M28.1 +
  M29.1 + M30.1 + M31.1 + M32.1) — backend substrate with no
  operator-facing behavior change on its own; DoD satisfied
  by M32.2 + M32.3 customer-facing follow-ons.
- **M32.2 (SESSION_208) — Sales-manager UI + sales-side
  Playwright.** New Writeups tab on `LeadDetailModal` with
  form + list + inline Approve/Send-to-F&I buttons + two
  confirmation dialogs (D5-revised approve copy + D6
  irreversibility copy). Frontend wrappers for all M11.3
  verbs. Removal of `salesApi.ts:10-25` "UI deferred"
  comments. ~34 Vitest tests. **New Playwright describe
  block `sales-manager-writeup-handoff`** (single-persona
  journey using existing `sales_manager` storageState)
  proving create → Pending → Approve → Approved →
  Send-to-F&I → Handed off through the real UI, with inline
  technical assertion that the CA was created. Journey
  count 22 → 23. **DoD satisfied directly** — no exception.
- **M32.3 (SESSION_209) — F&I intake UI + F&I-side Playwright
  extension + new persona.** New `DealerFandIIncoming.tsx`
  page at `/dealer-ai-f-and-i/incoming` (D8 non-navigational
  rows), new F&I nav "Incoming" link, `fetchCreditApplications`
  wrapper, new `f_and_i_manager` persona addition to
  `personas.ts` + `login.setup.ts` + new
  `seed_journey_fandi_intake_receipt` idempotent seed command,
  ~20 Vitest tests. **New Playwright describe block
  `fandi-intake-receipt`** using pre-seeded fixture (fully
  independent of M32.2 fixture — deterministic under any
  test order or parallelism) proving F&I role can receive
  and view a valid incoming CA. Journey count stays 23
  (extension of same spec, not new file). **DoD satisfied
  directly** — no exception.

All three increments are independently revertable via `git
revert`. M32.1 revert removes the FK migration (reversible
column drop; linkage data for hand-offs occurring between
deploy and revert is dropped but recoverable from M11.3
`notes` text prefix — see §5.g). M32.2 + M32.3 reverts are
pure code (no data cost).

## 3. Deferrals (all valid for later re-entry)

Recorded per M30–M31 §3 pattern. All are explicit non-goals
for M32 (see §5.h) and carried forward as candidates for
future milestones when evidence surfaces:

- **Salesperson-authored writeups** (broader role gating on
  M11.3 create endpoint). New M32 §3 deferral. M33+ evidence-
  gated. Requires selective permission-class work + acceptance
  coverage.
- **Writeup edit (PATCH)** (operator-facing surface for
  amending pre-approval terms). New M32 §3 deferral. Backend
  contract explicitly forbids it today; adding it requires
  activation-surface-asymmetry review per M31 lesson w.
- **Cross-lead sales-manager pending-approval queue page**
  (single view listing all Pending writeups across leads).
  New M32 §3 deferral. Assumption: same-day approval via
  per-lead `LeadDetailModal`. Elevate if evidence surfaces
  need.
- **F&I-scoped lead-context endpoint or per-CA detail page.**
  New M32 §3 deferral. Non-navigational F&I intake rows
  carry all triage info inline per D8.
- **Separation-of-duties enforcement.** New M32 §3 deferral.
  Multi-user policy is M33+ scope.
- **Pagination / server-side sort** on writeup + CA list
  endpoints. New M32 §3 deferral. Matches M10.7 / M11 sales
  substrate precedent.
- **Websocket / auto-refresh** of F&I intake queue or
  Writeups tab. New M32 §3 deferral. Accepted stale-tab
  race per M31 R1 precedent.
- **F&I workflow state extensions on intake rows** (In
  progress / Structuring / Submitted to lender / etc.). New
  M32 §3 deferral. Requires F&I-workflow scope selection at
  a future milestone.
- **`intake=false` operator filter.** New M32 §3 deferral.
  Rejected-and-reserved value. If already-contracted filter
  surfaces need, add distinct `has_contract=true` param —
  do not overload `intake`.
- **Backfill of `credit_application.deal_writeup` for
  existing rows.** New M32 §3 deferral. Existing CAs stay
  NULL by construction (truthful).
- **F&I-scoped acceptance journey for post-intake workflow**
  (creating contract, submitting to lender, etc.). New M32
  §3 deferral. M32.3 journey stops at F&I *receipt*.

All prior M31 §3 + M30 §3 + M29 §3 + M28 §3 + M27 §3 + M25
§4 deferrals carried forward unchanged.

## 4. Verifications performed at planning-open

Eleven verifications performed at M32.0 open. All must
resolve CLEAN before §5.b locks. Three surfaced blocking
findings that reshaped the milestone shape; five surfaced
architectural evidence that governed design decisions; three
surfaced infrastructure evidence that governed increment
structure.

### 4.1 Model + FK inspection

Verified: `DealWriteup` schema at
`backend/dealer_ai/migrations/0034_m113_deal_writeup_entity.py`
carries mandatory FKs to `dealership` (CASCADE), `lead →
CustomerLead` (CASCADE, non-nullable), `vehicle → Vehicle`
(CASCADE); optional user attributions `written_up_by_user`
+ `sales_manager_approved_by_user` (both SET_NULL,
nullable). Terms fields (`vehicle_price`, `trade_allowance`,
`down_payment`, `monthly_payment_target`, `term_months_target`,
`apr_target`) all optional Decimal. State timestamps
`write_up_at` (required), `sales_manager_approved_at`
(nullable), `handed_off_to_fandi_at` (nullable). No FK to
sale, contract, test drive, or CreditApplication.

**CreditApplication** at `backend/dealer_ai/models.py:4454+`
carries mandatory FK to `dealership` (CASCADE); nullable FKs
to `lead` (SET_NULL) and `sale` (SET_NULL) per M10.1 §5.a
Option C (retention-clock record-of-record semantics —
CA persists across parent deletion). `clean()` requires at
least one of lead / sale set; both are cross-tenant-guarded.

**Asymmetric lifecycle contract identified.** `DealWriteup.lead`
CASCADE-deletes with the CustomerLead; `CreditApplication.lead`
becomes NULL. This asymmetry is deliberate — CA is the legal
record-of-record with a 7-year retention clock. Documented
in §5.c R3 (no operator surface deletes CustomerLead in
M32, so NULL-lead CAs cannot arise from operator action;
if a future lead-delete surface lands, F&I intake row
rendering must handle NULL lead — deferred).

### 4.2 Service verb inspection

Verified: `services/deal_writeups/deal_writeup.py` ships
three verbs — `record_deal_writeup` (create with cross-tenant
FK check raising `CrossTenantDealWriteupError`),
`approve_deal_writeup` (idempotent — re-approval overwrites
approver + timestamp), and `hand_off_to_fandi`
(`@transaction.atomic`; raises `WriteupNotApprovedError` if
not approved; raises `WriteupAlreadyHandedOffError` if
already handed off, preventing duplicate CA rows and their
M10.1 §5.e retention-clock consequences; auto-creates CA via
`record_credit_application` with structured four-square
terms folded into `notes` via `_format_handoff_notes`).

Verified: `services/f_and_i/credit_application.py` ships
`record_credit_application` (M10.1) — direct create path
for CAs originating outside the writeup flow. Retention-
clock enforcement at model layer per M10.1 §5.e.

### 4.3 State machine + role separation

Verified: state derived from timestamp presence — `{created}`
→ `{approved}` (via approve) → `{handed_off}` (via hand-off,
once only). Re-approval permitted pre-handoff via
idempotent write. No un-approve. No un-hand-off.

Verified via `backend/dealer_ai/tests/test_m113_deal_writeup_service.py:155-165`
(`test_re_approval_overwrites`): re-approval overwrites
`sales_manager_approved_by_user` (M2 replaces M1) and
refreshes `sales_manager_approved_at`. Since M32 ships no
writeup PATCH surface and no operator surface to re-open
approvals, re-approval has no meaningful operator workflow
— it only rewrites approver identity. **Not exposed in the
M32 UI** (Approved rows hide the Approve button per state-
machine display). Backend contract preserved for M11.3
compatibility.

Verified: all three M11.3 verbs (create, approve, hand-off)
gated on `IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership`.
**Approve AND hand-off share the same permission class.**
F&I role (`IsFinanceManagerOrOwnerAtActiveDealership`) is
uninvolved on the writeup side. The auto-created CA is
written under the sales-manager's auth via a server-side
call inside the atomic block.

**Implication for M32 anchor question.** Because M11.3 gates
create on manager-only, a plain salesperson cannot create
writeups today. The anchor question was **corrected** from
its original draft ("Can a salesperson create... a manager
approve...") to reflect the shipped contract: *"Can a sales
manager create a deal writeup, review and approve it, and
hand it off to F&I such that the F&I team receives a
complete, actionable incoming credit application with
unambiguous provenance — all through Dealer OS?"* Broader
role expansion is M33+ evidence-gated per §3 and §5.h.

### 4.4 FK / identifier discoverability for CREATE

Verified: for the create endpoint (`POST /admin/deal-writeups/`
requires `lead_id` + `vehicle_id`), both identifiers are
discoverable through existing operator surfaces:

- **`lead_id`** — discoverable via `/dealer-ai-sales/leads`
  page + `LeadDetailModal` (row click). Established M11.6 +
  M24.1+ pattern.
- **`vehicle_id`** — discoverable via `listAdminVehicles`
  search wrapper (`frontend/src/lib/salesApi.ts:246-259`),
  used today by `RecordTestDriveForm` for the same operator
  pattern.

No new discovery surfaces required for create.

### 4.5 FK / identifier discoverability for APPROVE / HAND-OFF — BLOCKING FINDING

Verified: for approve (`POST /admin/deal-writeups/<pk>/approve/`)
and hand-off (`POST /admin/deal-writeups/<pk>/hand-off/`),
the writeup `pk` is **not discoverable** through any
operator surface today:

- No list endpoint (`grep` of `backend/dealer_ai/urls.py`
  confirms only the 3 POST endpoints exist for deal
  writeups: create, approve, hand-off).
- No detail/read endpoint.
- No frontend wrapper (`frontend/src/lib/salesApi.ts:10-25`
  explicitly says "UI deferred"; grep of `frontend/` for
  `DealWriteup` or `deal-writeup` returns only the
  deferral comment + a related note in `main.tsx:143-147`).

**Blocking finding.** A sales manager cannot see writeups
awaiting approval; hand-off has no operator queue. Approve
and hand-off endpoints exist but cannot be exercised from
any UI without knowing the pk out-of-band.

**Resolved by D1 + D2:** new writeup list endpoint
(filterable by state + optional per-lead) + new writeup
detail endpoint. Both land in M32.1 backend substrate.

### 4.6 Downstream F&I UI receiver — BLOCKING FINDING

Verified via `grep -R "CreditApplication\|credit_application"
frontend/` — **zero frontend files reference CreditApplication.**

Verified via `backend/dealer_ai/urls.py`: `admin/credit-applications/`
(audit #89) is **create-only**. No list endpoint on the
backend either. No detail endpoint.

Verified: `DealerFandIDeals` page (`frontend/src/pages/DealerFandIDeals.tsx`)
is keyed on **Contract** state (`contract_id`,
`contract_state`, `contract_type`, `vehicle_stock`,
`funding_state`, `chargeback_count`) — a newly-handed-off
CA has no contract yet, so it is invisible to this page.

Verified via `grep -R "deal[-_]?writeup\|DealWriteup"
acceptance/` — **zero acceptance journeys** exercise the
deal-writeup flow.

**Blocking finding.** The M11.3 hand-off endpoint creates a
CA row that no frontend surface displays. The entire hand-
off is a dead-drop from the F&I perspective.

**Resolved by D3 + D8:** new credit-application list
endpoint (F&I-gated, filterable by intake state) + new
non-navigational F&I intake page. Both land as substrate
in M32.1 (endpoint) and receiver in M32.3 (page).

### 4.7 CA ↔ DealWriteup pairing determinism — BLOCKING FINDING

Verified: the only structural link between a CA and its
originating writeup today is a text prefix written into the
CA's `notes` field by `_format_handoff_notes` at
`backend/dealer_ai/services/deal_writeups/deal_writeup.py:141-167`:

```
Deal write-up #<pk> handoff:
- Vehicle price: $<...>
- Trade allowance: $<...>
...
```

Verified: **one lead can have N writeups → N CAs**, all
sharing the same `lead` FK. No unique constraint on
lead-writeup, lead-CA, or writeup-CA. Text-based pairing
via `notes` prefix is fragile (operator-writable field;
brittle to parse at query time). Time-window pairing is
non-deterministic when a lead has multiple concurrent
writeups.

**Blocking finding.** The F&I intake queue cannot show
writeup context (four-square terms, approver, timestamps)
against a CA row deterministically without a structural
link.

**Resolved by D9-revised²:** nullable `OneToOneField` from
`CreditApplication` to `DealWriteup` in a new M32.1
migration. Three-layer defense:

1. **Database layer** — `OneToOneField` auto-generates a
   unique index. `IntegrityError` on any second insert.
2. **Service layer (`record_credit_application`)** — new
   guard raising `DealWriteupAlreadyLinkedError` when the
   incoming `deal_writeup=W` already has a paired CA.
   Kicks in before the DB write, giving a clean domain
   error rather than an `IntegrityError`.
3. **Service layer (`hand_off_to_fandi`)** — existing
   `WriteupAlreadyHandedOffError` (M11.3 shipped) catches
   the writeup-side path.

Nullability + SET_NULL preserved for direct-created CAs
(M10.1 direct path) and for historical CAs (backfill-free).
Semantic: peer-with-optional-backpointer; retention-clock
ownership stays on CA per M10.1 §5.e.

### 4.8 F&I role access to `admin_lead_detail` — BLOCKING FINDING

Verified: `admin_lead_detail` at
`backend/dealer_ai/views.py:847-848` is gated on
`IsSalesManagerOrOwnerAtActiveDealership`. An F&I manager
would receive `403 Forbidden` on any lead-detail fetch.

**Blocking finding for prior D8 draft** (row-link-to-lead-
detail on F&I intake page). Prior draft would have shipped
a row link that always 403s.

**Resolved by D8-revised:** F&I intake rows are **non-
navigational** — no `<a>` wrapping, no click handler on
row. Every triage field the F&I operator needs is rendered
inline (lead name/phone/email, vehicle stock/description,
four-square terms, notes verbatim, written-up-by,
approved-by, hand-off timestamp).

**Explicit non-goal for M32:** F&I-scoped lead-context view.
If evidence surfaces need, elevate to M33+ as either (a)
new endpoint `GET /admin/f-and-i/lead-context/<lead_id>/`
gated on F&I role with narrowed projection, or (b)
selective role-gating expansion on `admin_lead_detail`
with explicit review of what leaks to F&I (internal sales
notes, urgency ranking, salesperson-assignment history).

### 4.9 Advisor viewer LeadDetailModal access — BLOCKING FINDING

Verified: `admin_lead_detail` (§4.8) is also inaccessible
to advisor viewers — the same `IsSalesManagerOrOwnerAtActiveDealership`
gate excludes any role that is not sales_manager or owner.
Advisor viewers cannot open `LeadDetailModal` at all — the
modal's `fetchLeadDetail` call returns 403, and the modal
renders its API-error branch (not a lead-context surface
at all).

**Blocking finding for prior D4 draft** (visible-but-
disabled Writeups tab for advisor viewers). Prior draft
promised a UI surface that could never render — advisors
cannot reach the modal in the first place.

**Resolved by D4-revised²:** the Writeups tab is transitively
manager-only by virtue of the modal itself being manager-
only. No separate visible-but-disabled treatment for advisor
viewers is required or possible. Corrected posture:

- **Sales manager / owner viewer**: Writeups tab renders
  normally with list + "+ New writeup" CTA + inline
  approve/hand-off buttons per D5 / D6.
- **Advisor / other role viewer**: `LeadDetailModal` cannot
  open (backend 403). The existing modal error branch
  renders the "you don't have access" message. No Writeups-
  specific advisor UI ships.

Test-plan implication: drop the "advisor viewer disabled
tab + tooltip" test row from M32.2 (~35 → ~34 tests).

### 4.10 Playwright role transition + persona registry

Verified via `acceptance/support/auth/login.setup.ts`:
existing personas are platform_operator, owner,
sales_manager, recon_manager, bhph_collector. **No
`f_and_i_manager` persona exists.** M32.3 F&I journey
requires a new persona.

Verified: existing multi-persona pattern (owner +
sales_manager both use `AUTH_STORAGE.*` per-persona
storage-state files at `.auth/{persona}.json`). Journeys
use `test.use({ storageState: AUTH_STORAGE.persona })` to
authenticate as a specific persona for a describe block —
not session mutation.

Verified: seed provisioning at `login.setup.ts` runs a
`SEED_COMMANDS` array of idempotent management commands
before any test executes. New personas require additions
to (a) `personas.ts` registry, (b) `login.setup.ts` new
setup task, (c) `AUTH_STORAGE.*` registry, (d) a seed
command that provisions the persona's user + role
membership + any journey-specific fixtures.

**Resolved by D11:** M32.3 adds `f_and_i_manager` persona
following the established pattern. New idempotent seed
command `seed_journey_fandi_intake_receipt` provisions
both the persona and the pre-seeded fixture (dedicated
`Intake Iris` lead + `FANDI-INTAKE-1` vehicle + `handed_off`
writeup + paired CA via real `hand_off_to_fandi` code path)
so the M32.3 journey is fully independent of M32.2 state.

### 4.11 DoD compliance check on §3 draft

Per M21.0 §5.f Option B (M26 lineage): every customer-
facing milestone must add or update at least one Playwright
operational journey, or explicitly document why no journey
change is required.

- **M32.1** invokes the DoD exception path — backend
  substrate with no operator-facing behavior change on its
  own. **Seventh invocation** (M26 + M27.1 + M28.1 + M29.1
  + M30.1 + M31.1 + M32.1). Pattern firmly established.
  Exception rationale documented in §3 of the M32.1
  handoff.
- **M32.2** satisfies DoD directly via new
  `sales-manager-writeup-handoff` describe block. Sales-
  side create → Pending → Approve → Approved → Send-to-F&I
  → Handed off through the real UI, with inline technical
  assertion that the CA was created. Coverage 22 → 23
  journeys.
- **M32.3** satisfies DoD directly via new
  `fandi-intake-receipt` describe block extending
  `sales_to_fandi_handoff.spec.ts`. F&I role receives and
  views a valid incoming CA using pre-seeded fixture
  (fully independent of M32.2 fixture). Coverage stays
  23 journeys (extension of same spec, not new file).

**No customer-facing increment ships without journey
coverage.** M32.2 does not defer Playwright to M32.3; each
increment's operator-facing behavior is journey-asserted
independently. This is the M31 pattern applied to a three-
increment milestone.

## 5. Load-bearing decisions (all locked at M32.0)

### 5.a Target selection (locked at open)

**NEW Deal Writeups: Sales-Manager-to-F&I Handoff.**

Selected under the **primary operational-coverage lens**
(durable since M22 close) evaluated against the M31 §9
breadth-vs-depth standing question. The substrate-compound-
value continuation framing (M27.1 → M28.1 → M29 → M30 →
M31 = fifth link) is **available but not selected** — after
five consecutive accounting/templates selections, the
operator-coverage lens favored a fresh direct-operator gap
for breadth over a sixth substrate-compound-value link.

**Evidence.** Four load-bearing signals:

1. **Shipped-source deferral promise unfulfilled.**
   `frontend/src/lib/salesApi.ts:10-25` reads verbatim:
   > *"POST /admin/deal-writeups/ (M11.3, UI deferred)
   > POST /admin/deal-writeups/<pk>/approve/ (M11.3, UI
   > deferred) POST /admin/deal-writeups/<pk>/hand-off/
   > (M11.3, UI deferred) ... M11.6 §5.f.2 scope: leads /
   > test-drives / follow-ups / be-backs pages ship; deal-
   > writeup UI deferred. This module exposes the full
   > surface (writeup verbs included) so the follow-on
   > doesn't need to re-declare types."*
   Nine sessions later the "follow-on" has not landed.
   Same operator-safety-promise-fulfillment posture as
   M30.2 → M31.
2. **Largest un-gated direct operator-coverage gain of any
   M32 candidate.** 3 backend-only endpoints (#112–114) →
   3 covered in one milestone (with the +1 CA list
   endpoint added at M32.1 for the F&I receiver). No
   other un-gated candidate on the list moves the covered-
   count needle by 3.
3. **Natural bridge domain — beachhead into F&I without
   the pilot-evidence gate.** Sales domain is fully
   covered M11.1–M11.6 (leads, test drives, follow-ups,
   be-backs). F&I is mostly uncovered (audit #89–101 =
   13 uncovered endpoints). Deal writeups sit at the seam
   and stitch the two departments the operator most needs
   connected. Not gated on pilot evidence (unlike NEW C
   F&I chargeback, which requires operator direction on
   which subset of the F&I domain comprises the
   substrate).
4. **Answers M31 §9 breadth-vs-depth standing question.**
   Shifts out of the accounting/templates domain after
   five consecutive selections (M27.1 → M31) into a
   genuinely new surface (sales-to-F&I workflow), per
   the operator-coverage-benefits-from-breadth-after-
   depth framing.

**Alternatives considered (per M32.0 candidate list
presented at §4 of SESSION_206 handoff):**

- **NEW C — F&I chargeback substrate.** Sixth-link
  substrate-compound-value candidate. Explicitly gated on
  pilot evidence per M30 §9 → M31 §9 (unchanged). No
  pilot direction has landed since M31 close. Correct to
  defer.
- **NEW O2 / NEW O3.** Audit-tooling accuracy work.
  Unchanged M26/M27/M28/M29/M30/M31 deferrals. Require
  SESSION-189-§3-style tracing at open; blast radius
  unknown; no direct operator gain.
- **H — Test-hygiene remediation.** CI-stability infra;
  zero direct operator gain. Compound value grows with
  journey count but does not close a shipped-source gap.
- **Vendor detail (#43) / Photo reorder (#65).** Small
  polish (~1-endpoint each). Low operator-coverage gain
  standalone; could bundle as a wrapper-only completion
  milestone but does not answer any shipped-source
  promise.
- **F&I domain surface (#89–101 excl. chargeback).** 12
  uncovered endpoints; entire subdomain unwired. Too
  large without operator direction on scoping; correct
  to defer to evidence-driven candidate elevation.
- **Gated (T/U/L/M):** unchanged gating; no upgrade at
  M32.0. Deferred **D** and deferred-stable **G**
  unchanged.

Deal writeups was the only candidate that fulfilled a
shipped-source deferral promise AND removed a real
"dead-drop-from-F&I" operational blocker AND met the
bounded-scope test (three-increment shape locked at
§5.e).

**Verification rigor at planning-open:** the initial
target-lock triggered a full workflow verification pass
(§4.1–§4.11) that surfaced three blocking findings and
two additional inaccessibility findings before §5.b lock.
Prior drafts of D3, D4, D8, and D9 were revised in
response. Milestone shape is scope-driven, not
convention-driven — three increments were required by the
verification findings, not chosen for narrative symmetry.

### 5.b Design decisions (D1–D11)

#### D1 — Writeup list endpoint: fail-explicit filter validation

Add `GET /admin/deal-writeups/`, gated on
`IsSalesManagerOrOwnerAtActiveDealership`. Query parameters:

- **`state`** — one of `pending | approved | handed_off`
  (state derived at query time from timestamp presence;
  not a stored column). Case-sensitive allowlist.
- **`lead_id`** — integer.

**Validation posture (fail-explicit, not fail-closed-to-
unfiltered):**

- **Missing filter param** → normal unfiltered behavior.
- **Valid filter value** → apply filter.
- **Supplied but invalid value** → **`400 Bad Request`
  with `{"detail": "Invalid value for <param>: <received>.
  Expected: <allowlist>"}`.**

Explicit test matrix: `state=pending` filters; `state=Pending`
returns 400 (case-sensitive); `state=all` returns 400;
`state=` returns 400 (empty-but-present); missing `state`
returns unfiltered; `lead_id=abc` returns 400; `lead_id=999999`
returns empty list (not 400 — well-formed value, no rows).

**Rationale.** Silent conversion of invalid restrictive
filters into "show everything" is not fail-closed and
could expose more tenant-scoped records than the operator
intended. Explicit 400 lets the caller correct malformed
requests deliberately.

Default sort: newest-first by `write_up_at`.

**No pagination in M32.1** — matches M10.7 (100-row cap
defer) and M11 sales substrate precedent; deferred per
§5.h.

#### D2 — Writeup detail endpoint: read-only projection

Add `GET /admin/deal-writeups/<int:pk>/`, gated on
`IsSalesManagerOrOwnerAtActiveDealership`. Returns the same
projection shape as `_project_writeup` in
`views_deal_writeups.py`. 404 on cross-tenant or missing.

**Read-only — no PATCH/DELETE.** Activation-vocabulary-
asymmetry per M31 lesson w: state changes only through
dedicated verbs (approve, hand-off); term edits explicitly
out of M32 scope per §5.h.

#### D3 — Credit-application list endpoint: F&I intake queue with fail-explicit validation

Add `GET /admin/credit-applications/`, gated on
`IsFinanceManagerOrOwnerAtActiveDealership` — **first
F&I-role-gated list endpoint** (approve/handoff-adjacent
surface finally has an F&I-side receiver).

Query parameters (all validated fail-explicit per D1
posture):

- **`intake`** — accepts only `true` (any other value
  returns 400 with clear message). `true` filters to CAs
  with no `Contract.credit_application_id` reverse-
  relation match (pre-contract intake queue).
- **`lead_id`** — integer; malformed returns 400.
- **`since`** — ISO-8601 datetime string; malformed
  returns 400.

**`intake=false` explicitly rejected** — reserved-and-
unavailable in M32 to preserve semantic clarity. If a
future already-contracted filter surfaces evidence, add a
distinct `has_contract=true` param — do not overload
`intake`. Test matrix: `intake=true` filters; `intake=false`
returns 400; `intake=1` returns 400; missing `intake`
returns unfiltered.

Projection includes writeup-context fields **via the D9-
revised² deterministic FK** (not text-parsing of `notes`):
`deal_writeup_id`, `writeup_terms` (four-square Decimal-
as-string bundle joined at query time), `written_up_by_user_id`,
`sales_manager_approved_by_user_id`, `handed_off_to_fandi_at`.
When `deal_writeup_id` is NULL (CA created directly via
M10.1 without a writeup upstream), the writeup-context
fields are all NULL.

Default sort: newest-first by `captured_at`.

**Rationale for F&I-role gating.** M10.7 established the
`IsFinanceManagerOrOwnerAtActiveDealership` class for
contract-in-progress access. Extending to CA list is the
same operator-authority axis (F&I is the CA owner
throughout its lifecycle). No new permission class.

#### D4 — Sales-manager entry point: manager-only Writeups tab on LeadDetailModal (revised²)

Add a "Writeups" tab to `LeadDetailModal` (parallel to
existing test-drive flow via `RecordTestDriveForm`). The
tab is transitively manager-only by virtue of the modal
itself being sales-manager-gated at the backend
(`admin_lead_detail` at `views.py:847-848`).

**Truthful posture (no visible-but-disabled tab for
non-manager viewers):**

- **Sales manager / owner viewer**: tab renders list (via
  D1 with `lead_id=<pk>`) + "+ New writeup" CTA opening
  an inline four-square form (with vehicle picker via
  `listAdminVehicles`) + inline approve/hand-off buttons
  per D5 / D6.
- **Advisor / other role viewer**: `LeadDetailModal`
  cannot open at all (backend 403 on lead detail fetch).
  The existing modal error branch renders the "you don't
  have access" message. **No Writeups-specific advisor
  UI is possible or required** — advisors cannot reach
  the modal in the first place.

**Prior draft (D4) promised a visible-but-disabled tab for
advisor viewers.** That promise was verified at §4.9 as
unshippable (advisors never see the modal). The revised
posture honors the truthful behavior supported by the
existing route and permissions.

Form uses `listAdminVehicles` for vehicle discovery (same
pattern as `RecordTestDriveForm`; already-proven surface).

Rationale for the LeadDetailModal placement: keeps lead +
vehicle + writeup in one natural workflow anchor per M24.1+
precedent; a11y-first visibility of manager surfaces
preserves operator mental model; no new route required.

#### D5 — Approve action: state-machine-truthful confirmation copy

On any `pending` writeup row (sales_manager or owner
viewer only): **"Approve" button** (primary variant) →
confirmation dialog. On non-`pending` rows: **no button**
(Approved row shows only Send-to-F&I; Handed-off row is
read-only history with attribution).

**Confirmation copy (revised from prior draft to remove
false re-approval advertisement):**

- **Title:** *"Approve deal writeup?"*
- **Body:** *"Approving marks this writeup ready for F&I
  hand-off. Review the terms carefully before continuing.
  After it is sent to F&I, the hand-off cannot be repeated
  or undone."*
- **Footer:** `[Cancel] [Approve]`

**Rationale for removing re-approval mention.** Verified
at §4.3 (`test_re_approval_overwrites`): re-approval
overwrites approver identity and refreshes timestamp.
Since M32 ships **no writeup PATCH surface** and **no
operator surface to re-open approvals**, re-approval has
no meaningful operator workflow — it only rewrites approver
credit. **Not exposed in the M32 UI** (Approved rows hide
the button per state-machine display). Re-approval remains
possible via direct API call (backend contract preserved
from M11.3) but is not advertised as an operator path.

**Testids:** `writeup-approve-trigger-<pk>`,
`writeup-approve-confirm-body`, `writeup-approve-cancel`,
`writeup-approve-submit`.

#### D6 — Hand-off action: irreversibility-flagged confirmation

On any `approved` writeup row (sales_manager or owner
viewer only): **"Send to F&I" button** (primary variant) →
confirmation dialog. Copy explicitly names the
irreversibility (backed by M11.3 `WriteupAlreadyHandedOffError`
idempotency guard):

- **Title:** *"Send to F&I?"*
- **Body:** *"This creates a credit application for
  `<lead name>` and hands off to F&I. **This cannot be
  undone** — a second attempt will be refused to protect
  against duplicate applications and their retention-clock
  consequences. Continue?"*
- **Footer:** `[Cancel] [Send to F&I]`

**Testids:** `writeup-handoff-trigger-<pk>`,
`writeup-handoff-confirm-body`, `writeup-handoff-cancel`,
`writeup-handoff-submit`.

#### D7 — Writeup state visual signals (three-signal a11y per M31 D6)

Each row in the Writeups tab carries **three independent
signals** for state (per M31 D6 lesson):

1. **Semantic status Badge** — one of `[Pending]`
   `[Approved]` `[Handed off]`, visible text, not
   aria-hidden.
2. **Row `aria-label`** — e.g., `aria-label="Writeup
   #{pk}, {lead name}, approved"`.
3. **Testids** — `writeup-row-<pk>`,
   `writeup-row-state-<state>-<pk>` (double marker so
   Playwright + Vitest can assert on state independent
   of visual styling).

Reinforcement via muted styling on Handed-off rows (they
are read-only history). Muted styling is not the load-
bearing signal per M31 D6 lesson — the badge + aria-label
+ testids survive color-blindness modes, high-contrast
mode, and dark mode.

#### D8 — F&I intake queue: new page, non-navigational rows, all intake info inline (revised)

New page `DealerFandIIncoming.tsx` at
`/dealer-ai-f-and-i/incoming`, backend-gated via D3 on
`IsFinanceManagerOrOwnerAtActiveDealership`.

**Rows are NON-NAVIGATIONAL** — no link to lead detail
(which is sales-role-gated per §4.8 and would 403 for F&I).
Every field the F&I operator needs for triage is rendered
inline:

- Lead name (from projection).
- Lead phone + email (add to D3 projection).
- Vehicle stock + description (add to D3 projection —
  resolved from `writeup.vehicle` via join).
- Four-square terms: vehicle_price / trade_allowance /
  down_payment / monthly_payment_target /
  term_months_target / apr_target — all inline.
- `notes` from CreditApplication (verbatim M11.3
  `_format_handoff_notes` output).
- Written up by (user display name from projection).
- Approved by (user display name from projection).
- Handed off (relative timestamp).
- **State badge:** currently only "Incoming" — future
  extensions (e.g., "In progress" once F&I starts a
  Contract) deferred per §5.h.

**Empty state:** *"No incoming applications. Credit
applications from sales-manager hand-offs appear here."*

**Navigation:** add "Incoming" link in F&I side navigation
adjacent to "Deals".

**Rationale.** Prior draft (D8) promised a row-link to
lead detail. Verified at §4.8: `admin_lead_detail` is
gated on `IsSalesManagerOrOwnerAtActiveDealership`; F&I
gets 403. Row-link would ship a broken promise. Non-
navigational rows honor the truthful behavior supported
by the existing route and permissions.

**Explicit non-goal for M32:** F&I-scoped lead-context
view or per-CA detail page. If evidence surfaces need,
elevate to M33 per §3.

#### D9 — CreditApplication carries a nullable OneToOneField backpointer to DealWriteup (revised²)

Add a **nullable `OneToOneField`** `credit_application.deal_writeup`
in a new M32.1 migration (`0051_m32_credit_application_deal_writeup_fk.py`):

```python
# In CreditApplication model:
deal_writeup = models.OneToOneField(
    "DealWriteup",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="credit_application",
)
```

**Three-layer defense against duplicate pairings:**

1. **Database layer** — `OneToOneField` auto-generates a
   unique index on the FK column. `IntegrityError` on any
   second insert. Catches all callers, including alternate
   ORM paths, management commands, and future migrations.
2. **Service layer (`record_credit_application`)** — new
   guard raising `DealWriteupAlreadyLinkedError` when the
   incoming `deal_writeup=W` already has a paired CA.
   Kicks in before the DB write, giving a clean domain
   error rather than an `IntegrityError`. Endpoint layer
   maps to `409 CONFLICT` (matches
   `WriteupAlreadyHandedOffError` shape).
3. **Service layer (`hand_off_to_fandi`)** — existing
   `WriteupAlreadyHandedOffError` (M11.3 shipped) catches
   the writeup-side path. Composed with the new guard:
   writeup-side idempotency prevents second hand-off;
   CA-side uniqueness prevents any alternate caller
   (including `record_credit_application` called directly
   with a `deal_writeup=W1` that's already handed off)
   from creating a duplicate.

**Nullability preserved.** Direct-created CAs via M10.1
stay `deal_writeup=NULL`. Historical CAs (all existing
rows at M32.1 deploy time) stay NULL — backfill-free.

**New service verb signature (`record_credit_application`):**

```python
def record_credit_application(
    *,
    dealership: Dealership,
    applicant_full_name: str,
    source_format: str = CREDIT_APP_FORMAT_TABLET,
    lead: Optional[CustomerLead] = None,
    sale: Optional[Sale] = None,
    notes: str = "",
    deal_writeup: Optional[DealWriteup] = None,  # NEW at M32.1
) -> CreditApplication:
    """... existing docstring ...
    
    M32.1 extension: optional ``deal_writeup`` backpointer set
    at handoff-created-CA path. Direct-create callers omit;
    the field defaults to None. Raises
    ``DealWriteupAlreadyLinkedError`` if the writeup is
    already paired.
    """
```

**`hand_off_to_fandi` update (2-line change):** pass
`deal_writeup=writeup` when calling `record_credit_application`
inside the existing `@transaction.atomic` block.

**Semantic:** peer-with-optional-backpointer. Retention-
clock ownership stays on the CA per M10.1 §5.e. The FK is
a **discovery aid, not a compositional dependency**. The
peer semantics of M11.3 preserved — the FK is a
backpointer, not a parent-child link.

**Historical migration 0034 is NOT modified.** Per project
directive: architectural evolution is recorded in the
current model/service docstrings (M32.1 amends both
`CreditApplication` and `DealWriteup` model docstrings +
both service verb docstrings), in migration 0051 docstring,
in this planning memo, in the M32 retrospective, and in
`docs/CAPABILITY_MATRIX.md` §7η — not by retroactively
rewriting M11.3's historical migration.

**Mandatory test (M32.1 test plan)** —
`test_writeup_cannot_link_to_multiple_credit_applications`:
exercises all three defense layers (service `DealWriteupAlreadyLinkedError`,
DB `IntegrityError` via bypass-service direct ORM, and
by composition the M11.3 `WriteupAlreadyHandedOffError`
via `hand_off_to_fandi` second-call path).

#### D10 — Role gating: reuse existing permission classes; zero-drift streak preserved

All three new endpoints reuse existing permission classes:

- **D1 writeup list** — `IsSalesManagerOrOwnerAtActiveDealership`
  (M11.3 class, unchanged).
- **D2 writeup detail** — same as D1.
- **D3 credit-app list** — `IsFinanceManagerOrOwnerAtActiveDealership`
  (existing M10.7 class, unchanged).

**Zero-drift permission-class streak:**
- 33 (M31) → **34** (M32.1) → **35** (M32.2 — no new
  backend endpoints) → **36** (M32.3 — no new backend
  endpoints).

#### D11 — New Playwright persona: f_and_i_manager

New persona addition (M32.3 substrate scope):

- **`acceptance/support/auth/personas.ts`** — new entry
  with `roles: ["f_and_i_manager"]`.
- **`acceptance/support/auth/login.setup.ts`** — new
  setup task `setup("authenticate as f_and_i_manager",
  ...)` following the established pattern.
- **`AUTH_STORAGE.fAndIManager`** — new storage-state
  file at `.auth/f_and_i_manager.json` per per-persona
  isolation.
- **New idempotent seed command
  `seed_journey_fandi_intake_receipt`** — provisions the
  persona's user + `f_and_i_manager` role membership at
  the seed's dealership; also provisions the M32.3
  journey fixture (dedicated `Intake Iris` lead +
  `FANDI-INTAKE-1` vehicle + `handed_off` writeup + paired
  CA via real `hand_off_to_fandi` code path). Idempotent
  per M20 lesson.
- **Registration in `login.setup.ts` `SEED_COMMANDS` array.**

M32.3 Playwright journey uses `test.use({ storageState:
AUTH_STORAGE.fAndIManager })` in the F&I describe block —
separate authenticated context, not a session mutation.
Matches existing multi-persona pattern (owner +
sales_manager already use this per-persona storage-state
approach).

**Independence guarantee.** M32.2 sales journey creates
its own lead/vehicle/writeup through the real UI (using
existing `sales_manager` persona + seed fixtures). M32.3
F&I journey reads the pre-seeded `Intake Iris` fixture
specifically (deterministic lookup by lead name /
writeup pk from seed output). **Distinct fixture rows;
no shared state; test order irrelevant; parallelism-safe.**

### 5.c Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Salesperson expects to create writeups but is blocked by M11.3 role gating | Med | Low | D4-revised² confirms modal is manager-only by transitivity. No advisor-facing tab surface. Broader role gating is M33+ evidence-gated per §3. |
| R2 | Stale-tab race: writeup approved in one tab, F&I hands off in another before approval propagates | Low | Low | `hand_off_to_fandi` re-reads `sales_manager_approved_at` inside `@transaction.atomic` (M11.3 shipped). No lost update; UI shows stale state until refetch. Accepted per M31 R1 precedent. |
| R3 | CA schema permits NULL `lead` (SET_NULL); DealWriteup schema does not (CASCADE) — asymmetric lifecycle | N/A (no lead-delete operator surface in M32) | Med (hypothetical) | **Documented, not guarded.** `CreditApplication.lead` is nullable + SET_NULL per M10.1 §5.a Option C (retention-of-record contract); `DealWriteup.lead` is CASCADE + non-nullable per M11.3 migration. No operator surface deletes CustomerLead in M32. If a future lead-delete surface lands, F&I intake row rendering must handle NULL lead (`[lead deleted]` placeholder) — deferred. |
| R4 | Cross-tenant CA appears in another tenant's intake queue | None (by construction) | Critical | D3 filters unconditionally by `dealership=get_current_dealership(request)`. Endpoint test asserts cross-tenant returns empty. M10/M11 tenant-scoping pattern. |
| R5 | Malformed query filter values silently include more records than operator intended | None (by D1+D3 fail-explicit design) | High | **D1 + D3 return 400 on invalid values.** Explicit test matrix: valid → apply; missing → unfiltered; invalid → 400 with clear message. Silent unfiltering explicitly rejected. |
| R6 | Sales manager can't find writeups awaiting approval because Writeups tab is per-lead only | Med | Med | Two paths: (a) per-lead Writeups tab (M32.2); (b) cross-lead sales-manager pending-approval queue page — **deferred to M33 per §3/§5.h**, evidence-gated. Assumption: same-day approval via LeadDetailModal. |
| R7 | Deterministic pairing between CA and DealWriteup absent — one lead can have N writeups → N CAs, all sharing lead FK | None (by D9-revised² construction) | High | **D9-revised² adds nullable OneToOneField backpointer** at DB layer (unique constraint) + service-layer `DealWriteupAlreadyLinkedError` + M11.3 `WriteupAlreadyHandedOffError`. Three-layer defense. Mandatory test asserts all three. Deterministic pairing at query time via FK; no text-parsing of `notes`. |
| R8 | Testid collision between M32 writeup rows and existing M11 sales rows | None (by construction) | Low | New testids all prefixed `writeup-*`. Grep confirms no collision with `lead-*`, `test-drive-*`, `follow-up-*` patterns. |
| R9 | F&I row link to `admin_lead_detail` returns 403 (F&I role not in `IsSalesManagerOrOwnerAtActiveDealership` allowlist) | None (by D8-revised construction) | Med | **D8-revised makes F&I intake rows NON-NAVIGATIONAL** — all triage info rendered inline (lead name/phone/email, vehicle stock/description, four-square terms, notes, attribution). No lead-detail link. F&I-scoped lead-context view deferred to M33+. |
| R10 | New `f_and_i_manager` Playwright persona seed/login flakes on first fresh-DB run | Low | Med | Seed provisioning follows M20 idempotent-command pattern; storageState file per persona (existing infrastructure). Belt-and-suspenders `/api/dealer-ai/auth/me/` assertion in `login.setup.ts` catches drift early. |
| R11 | M32.3 Playwright fandi-intake-receipt depends on M32.2 fixture leaking between tests | None (by D11 construction) | High | **D11 seed command `seed_journey_fandi_intake_receipt` provisions dedicated `Intake Iris` fixture** — distinct lead / vehicle / writeup from any M32.2 test data. M32.3 journey looks up fixture by known name / pk from seed output. Distinct rows; no shared state; test order irrelevant; parallelism-safe. |

### 5.d Verifications completed at planning-open

Eleven verifications (§4.1–§4.11 above) all resolved:

- §4.1 Model + FK inspection: CLEAN (asymmetric CA/writeup
  lead lifecycle documented in R3, deferred).
- §4.2 Service verb inspection: CLEAN.
- §4.3 State machine + role separation: CLEAN (re-approval
  semantic verified; not exposed in M32 UI).
- §4.4 FK discoverability for CREATE: CLEAN
  (lead + vehicle both discoverable via existing surfaces).
- §4.5 FK discoverability for APPROVE / HAND-OFF: BLOCKING
  → resolved by D1 + D2 (writeup list + detail endpoints).
- §4.6 Downstream F&I UI receiver: BLOCKING → resolved by
  D3 + D8 (credit-app list endpoint + non-navigational F&I
  intake page).
- §4.7 CA ↔ DealWriteup pairing determinism: BLOCKING →
  resolved by D9-revised² (nullable OneToOneField + three-
  layer defense).
- §4.8 F&I role access to `admin_lead_detail`: BLOCKING for
  prior D8 draft → resolved by D8-revised (non-navigational
  rows).
- §4.9 Advisor viewer LeadDetailModal access: BLOCKING for
  prior D4 draft → resolved by D4-revised² (no advisor tab
  posture; transitively manager-only).
- §4.10 Playwright role transition + persona registry:
  CLEAN → D11 adds `f_and_i_manager` persona following
  established M20 pattern.
- §4.11 DoD compliance check on §3 draft: CLEAN (M32.1
  exception path #7; M32.2 + M32.3 satisfy directly).

**Three blocking findings + two additional inaccessibility
findings all resolved architecturally before scope-lock.**
Verification rigor at planning-open reshaped D3, D4, D8,
and D9 from initial drafts to final locked shapes; three-
increment shape is scope-driven, not convention-driven.

### 5.e Phase / increment structure

**Three-increment split** — scope-driven per §5.a
verification findings. All revertable independently;
M32.1 migration is reversible (nullable column drop).

#### M32.1 (SESSION_207) — Backend substrate + provenance-FK migration

**DoD exception path invocation #7.**

- **Migration** (`0051_m32_credit_application_deal_writeup_fk.py`):
  - Add `credit_application.deal_writeup` nullable
    `OneToOneField`, `on_delete=SET_NULL`, `related_name="credit_application"`.
    Backward compat — existing rows stay NULL. Reversible
    (column drop). No data migration.
- **Service layer** (`services/deal_writeups/deal_writeup.py`
  + `services/f_and_i/credit_application.py`):
  - New `list_deal_writeups(*, dealership, state=None,
    lead=None)` verb — derived-state filter (state from
    timestamp presence); filters composable.
  - New `get_deal_writeup(*, pk, dealership)` verb —
    returns row or None (tenant-scoped).
  - New `list_credit_applications(*, dealership,
    intake=False, lead=None, since=None)` verb —
    `intake=True` filters CAs without a
    `Contract.credit_application_id` reverse-relation
    match; projection includes writeup context via new
    FK when set.
  - Update `hand_off_to_fandi` to set
    `credit_app.deal_writeup=writeup` at creation
    (2-line change inside existing atomic block).
  - Update `record_credit_application` signature to
    accept optional `deal_writeup` kwarg (default None
    to preserve M10.1 direct-create path); add
    `DealWriteupAlreadyLinkedError` guard.
  - New error class `DealWriteupAlreadyLinkedError` in
    `services/f_and_i/credit_application.py` (endpoint
    layer maps to 409 CONFLICT).
  - **Model docstring updates** on `CreditApplication`
    (`models.py:4454+` — amend "Attach shape" paragraph)
    and on `DealWriteup` (add reference to `credit_application`
    reverse relation) per D9-revised² Point 2.
  - **Service docstring updates** on `hand_off_to_fandi`
    (reference FK write + `DealWriteupAlreadyLinkedError`)
    and on `record_credit_application` (describe new
    `deal_writeup` kwarg + guard).
- **Endpoint layer** (`views_deal_writeups.py` +
  `views_f_and_i.py`):
  - `admin_deal_writeup_list(request)` (GET) — D1 fail-
    explicit query parsing; permission `_M113_PERMS`.
  - `admin_deal_writeup_detail(request, pk)` (GET) — D2.
  - `admin_credit_application_list(request)` (GET) — D3
    fail-explicit query parsing; F&I-gated
    (`IsFinanceManagerOrOwnerAtActiveDealership`).
- **URL** (`urls.py`): 3 new patterns, siblings to
  existing M11.3 + M10.1 patterns.
  - `admin/deal-writeups/` → `admin-deal-writeup-list`
  - `admin/deal-writeups/<int:pk>/` →
    `admin-deal-writeup-detail`
  - `admin/credit-applications/` (M32.1 upgrade — same
    URL as M10.1 create; adding GET handler) →
    `admin-credit-application-list`
- **Historical migration 0034 NOT modified** per D9-
  revised² Point 2.
- **Tests planned (~51):**
  - ~14 for writeup list (state matrix, lead filter,
    fail-explicit 400 matrix, tenant-scope, permission
    matrix).
  - ~8 for writeup detail (happy path, 404 missing, 404
    cross-tenant, permission matrix).
  - ~16 for CA list (intake filter, lead filter, since
    filter, fail-explicit 400 matrix including
    `intake=false → 400`, tenant-scope, permission matrix,
    projection includes writeup context, NULL backpointer
    for direct-created CAs).
  - ~7 for pairing FK behavior (hand-off sets backpointer;
    direct-create CAs stay NULL; writeup delete → backpointer
    becomes NULL not CA delete; determinism when lead has
    multiple writeups → multiple CAs → each pairs unambiguously;
    **mandatory `test_writeup_cannot_link_to_multiple_credit_applications`**
    exercising all 3 defense layers).
  - ~6 auth/tenancy coverage.
- **Expected count:** 4,933 → **~4,984** (+~51 tests).
- **`manage.py check` + `makemigrations --check
  --dry-run`:** clean.
- **DRF admin surface:** 118 → 121 (+3 endpoints).
- **Service verbs:** 318 → 321 (+3 verbs; signature-
  additive changes to `hand_off_to_fandi` +
  `record_credit_application` don't count as new verbs).
- **Non-goals in M32.1:** no frontend changes; no
  Playwright; no DRF admin count re-baselining (rolls into
  M32 close-out per convention); no operator-facing
  behavior change on M32.1's own (DoD exception path #7).

#### M32.2 (SESSION_208) — Sales-manager UI + sales-side Playwright

**DoD satisfied directly via new `sales-manager-writeup-
handoff` describe block.**

- **Frontend list wrappers** (`salesApi.ts`):
  - `listDealWriteups({leadId?, state?})` — consumes D1.
  - `getDealWriteup(pk)` — consumes D2.
  - `createDealWriteup(payload)` — consumes M11.3 create.
  - `approveDealWriteup(pk)` — consumes M11.3 approve.
  - `handOffDealWriteup(pk)` — consumes M11.3 hand-off.
  - **Remove `salesApi.ts:10-25` "UI deferred" comments.**
- **`LeadDetailModal`**: new "Writeups" tab per D4-revised².
  Manager-only by transitivity of the modal itself; no
  visible-but-disabled advisor treatment.
- **New inline components** (co-located inside
  `LeadDetailModal` per M28.0 `feedback_duplicate_small_stable_logic`
  lesson):
  - `DealWriteupForm` — four-square form with vehicle
    picker (reuses `listAdminVehicles` pattern from
    `RecordTestDriveForm`).
  - `WriteupApproveConfirmDialog` — D5-revised copy.
  - `WriteupHandoffConfirmDialog` — D6 irreversibility
    copy.
- **State visual signals** per D7 — Badge + row aria-label
  + testids.
- **Frontend tests planned (~34):**
  - Form validation matrix (~6).
  - POST success + failure paths (~6).
  - List rendering by state (~4).
  - Approve happy path + confirmation copy verbatim
    (~4).
  - Hand-off happy path + irreversibility copy verbatim
    (~4).
  - State badge + testid assertions (~4).
  - Comment removal verification (~1 — grep-style test
    or negative assertion on the removed comments).
  - Manager viewer sees tab + all controls (~3).
  - Non-manager viewer receives modal 403 error branch
    (~2 — verifies the modal error branch renders, not
    a phantom disabled tab).
- **Expected counts:** frontend 319 → **~353**.
- **Playwright (+1 journey — new spec
  `sales_to_fandi_handoff.spec.ts` with `test.describe
  ("sales-manager-writeup-handoff", …)`):** sales-side
  only in M32.2. Uses existing `sales_manager` persona
  (existing storageState — no new persona in M32.2). Six
  steps:
  1. Sales manager opens LeadDetailModal for a seeded
     lead (uses existing M24.1+ sales_operational_entry
     seed fixture; add a fresh lead + vehicle to the
     seed if needed for isolation).
  2. Writeups tab → "+ New writeup" → four-square form
     (with vehicle picker) → post.
  3. Assert new row appears with `[Pending]` badge +
     `writeup-row-state-pending-<pk>` testid.
  4. Approve button → confirmation with D5-revised copy
     verbatim → confirm.
  5. Assert row updates to `[Approved]` badge + approver
     name + timestamp visible.
  6. Send to F&I button → confirmation with D6
     irreversibility copy verbatim → confirm.
  7. Assert row updates to `[Handed off]` badge; assert
     `handed_off_to_fandi_at` visible; assert a matching
     `credit_application` was created via a direct
     `page.request.get('/admin/credit-applications/?intake=true')`
     fetch as a technical assertion — proves the backend
     side of the handoff regardless of the F&I UI (F&I
     UI ships in M32.3).
- **Acceptance count:** 22 → **23 journeys**.
- **`tsc --noEmit`:** clean across frontend +
  acceptance.
- **Grep verification** (`git grep "UI deferred"
  frontend/`): empty (removal verified).

#### M32.3 (SESSION_209) — F&I intake UI + F&I-side Playwright extension + new persona

**DoD satisfied directly via new `fandi-intake-receipt`
describe block extending `sales_to_fandi_handoff.spec.ts`.**

- **New persona provisioning per D11:**
  - `personas.ts` addition for `f_and_i_manager`.
  - `login.setup.ts` new setup task + new
    `AUTH_STORAGE.fAndIManager`.
  - New seed command `seed_journey_fandi_intake_receipt`
    provisioning persona + `Intake Iris` fixture.
  - Registration in `login.setup.ts` `SEED_COMMANDS`.
- **Frontend list wrapper** (`fAndIApi.ts`):
  - `fetchCreditApplications({intake?, leadId?, since?})`
    — consumes D3.
- **New page** `DealerFandIIncoming.tsx` at
  `/dealer-ai-f-and-i/incoming` per D8-revised (non-
  navigational rows). Route registered in `main.tsx`
  under existing F&I section.
- **Navigation:** "Incoming" link added to F&I side nav
  adjacent to "Deals" (extend existing F&I nav
  component).
- **Frontend tests planned (~20):**
  - Page renders happy path (~2).
  - Filter parameter passthrough (~4).
  - Empty state (~2).
  - Rows render all inline intake fields — lead
    name/phone/email; vehicle stock/description; four-
    square terms; notes; written-up-by; approved-by;
    hand-off timestamp (~6).
  - Rows are non-navigational — assert no `<a>`
    wrapping, no click handler on row, no cursor-pointer
    (~3).
  - Advisor viewer receives 403 (backend enforcement; UI
    shows access-denied branch) (~2).
  - Navigation link visible to F&I role; absent for
    other roles (~1).
- **Expected counts:** frontend ~353 → **~373**.
- **Playwright (extend existing spec with new describe
  block `fandi-intake-receipt`):**
  - `test.use({ storageState: AUTH_STORAGE.fAndIManager })`
    at describe-block level — separate authenticated
    context, not a session mutation.
  - Reads pre-seeded `Intake Iris` fixture (deterministic
    lookup by lead name / writeup pk from seed output).
  - **Fully independent of M32.2 fixture** — distinct
    rows; no shared state; test order irrelevant;
    parallelism-safe.
  - Steps:
    1. Navigate to `/dealer-ai-f-and-i/incoming`.
    2. Assert row for the pre-seeded handed-off writeup
       (`Intake Iris` fixture) appears with full inline
       data: lead name + phone + email; vehicle stock;
       four-square terms verbatim; written-up-by;
       approved-by; hand-off timestamp within tolerance.
    3. Assert row is non-navigational (no `<a>`
       wrapping, no click handler, no cursor-pointer).
    4. Assert `notes` field carries the M11.3 `Deal
       write-up #<pk> handoff:` prefix + four-square
       summary.
- **Acceptance count:** stays **23 journeys** (extension
  of same spec, not new file).
- **`tsc --noEmit`:** clean across frontend +
  acceptance.

### 5.f DoD compliance check

Per M21.0 §5.f Option B (M26 lineage): every customer-
facing milestone must add or update at least one Playwright
operational journey, or explicitly document why no journey
change is required.

- **M32.1** invokes the DoD exception path — backend
  substrate with no operator-facing behavior change on its
  own. **Seventh invocation** (M26 + M27.1 + M28.1 + M29.1
  + M30.1 + M31.1 + M32.1). Pattern firmly established.
  Exception rationale documented in §3 of the M32.1
  handoff.
- **M32.2** satisfies DoD directly via new
  `sales-manager-writeup-handoff` describe block. Sales-
  side create → Pending → Approve → Approved → Send-to-F&I
  → Handed off through the real UI, with inline technical
  assertion that the CA was created. Coverage 22 → 23
  journeys.
- **M32.3** satisfies DoD directly via new
  `fandi-intake-receipt` describe block extending the
  sales-side spec. F&I role receives and views a valid
  incoming CA using pre-seeded fixture (fully independent
  of M32.2 fixture). Coverage stays 23 journeys
  (extension of same spec, not new file).

**No customer-facing increment ships without journey
coverage.** M32.2 does not defer Playwright to M32.3;
each increment's operator-facing behavior is journey-
asserted independently. This is the M31 pattern applied
to a three-increment milestone.

### 5.g Rollback plan

All three increments independently revertable via `git
revert`. M32.1 migration is reversible (nullable column
drop).

- **M32.1 revert.** Removes 3 GET endpoints + 3 service
  verbs + `DealWriteupAlreadyLinkedError` class +
  `credit_application.deal_writeup` OneToOneField
  migration.
  
  **Data behavior on revert:** the migration is reversible
  (drops the nullable OneToOneField column). Existing
  `CreditApplication` and `DealWriteup` rows are preserved.
  The provenance linkage data (the `deal_writeup_id` values
  written on any hand-offs that occurred between M32.1
  deploy and revert) is **dropped** — not literally zero-
  writes / zero-data-loss, but **operationally recoverable**
  because the M11.3 `_format_handoff_notes` text prefix
  in `CreditApplication.notes` remains (the pre-M32.1
  pairing hint). A future re-application of M32.1 would
  repopulate the FK only for future hand-offs; historical
  hand-offs between original M32.1 and revert would remain
  paired only via the text prefix.
  
  Operator impact: falls back to Django-shell for writeup
  / CA discovery. The `record_credit_application`
  signature reverts (drops `deal_writeup` kwarg). The
  `hand_off_to_fandi` code reverts (stops writing the FK;
  behavior returns to pre-M32.1 CA creation, matching
  M11.3 shipped).
- **M32.2 revert.** Pure code revert. Removes Writeups
  tab from `LeadDetailModal` + inline components +
  wrappers. M11.3 POST verbs return to unwired state
  (comment `salesApi.ts:10-25` "UI deferred" reinstates).
  M32.1 GET endpoints remain — future re-attempt has
  substrate.
- **M32.3 revert.** Pure code revert. Removes
  `/dealer-ai-f-and-i/incoming` page + navigation link +
  F&I persona setup + seed command registration. M32.1
  CA-list endpoint remains. M32.2 sales-manager UI
  remains functional; hand-off actions still work but
  land in a CA queue without an F&I UI (state pre-M32.3,
  superset of pre-M32 — matches M11.3 shipped baseline
  plus sales-manager UI).
- **Coordinated M32 close push** deferred to explicit
  user confirmation per M27 → M28 → M29 → M30 → M31
  coordinated-close cadence.

### 5.h Non-goals for M32

Explicitly out of scope per user constraints (see §1.3
for operator-facing framing):

- ❌ **Salesperson-authored writeups.** M11.3 role gating
  (manager/owner-only) preserved. Broader role expansion
  is M33+ evidence-gated.
- ❌ **Writeup edit (PATCH).** Activation-surface-
  asymmetry preservation per M31 lesson w. Re-approval
  remains a backend contract (M11.3) but is not exposed
  in M32 UI.
- ❌ **Cross-lead sales-manager pending-approval queue
  page.** Assumption per §5.c R6 (same-day approval via
  LeadDetailModal); elevate if evidence surfaces.
- ❌ **F&I-scoped lead-context view.** Non-navigational
  intake rows per D8 provide sufficient triage info.
  Elevate to M33+ as new endpoint or selective role-
  gating expansion if evidence surfaces.
- ❌ **Per-CreditApplication detail page.** All intake
  info rendered inline per D8.
- ❌ **Separation-of-duties enforcement** (approver ≠
  writer). Matches M11.3 shipped behavior.
- ❌ **Pagination / server-side sort** on the 3 new list
  endpoints. Matches M10.7 / M11 sales substrate
  precedent (100-row cap defer).
- ❌ **Websocket / auto-refresh** of F&I intake queue or
  Writeups tab. Accepted stale-tab race per M31 R1
  precedent.
- ❌ **New permission classes.** All 3 endpoints reuse
  existing classes; zero-drift streak 33 → 34 → 35 → 36.
- ❌ **Backfill of `credit_application.deal_writeup` for
  existing rows.** Existing CAs stay NULL (truthful —
  they were not created via hand-off). Only new hand-
  offs populate.
- ❌ **F&I state extensions on intake rows** (In progress
  / Structuring / Submitted to lender / etc.). M32 intake
  rows carry the single "Incoming" state. Extending to
  F&I workflow states is a separate future milestone.
- ❌ **`intake=false` as an operator filter.** Reserved-
  and-rejected value in M32; use `has_contract=true` (or
  similar) in a future milestone if the "already-
  contracted" filter surfaces evidence.
- ❌ **Retroactive rewriting of historical migration 0034**
  to describe M32-introduced architecture. Per project
  directive: historical migrations are immutable
  historical artifacts. Architectural evolution recorded
  in current model/service docstrings + migration 0051 +
  this planning memo + M32 retrospective + capability
  matrix §7η.
- ❌ **Any change to M11.3 M10.1 M10.7 shipped surfaces**
  except the four surgical M32.1 changes documented in
  D9-revised² (models.py docstring updates on
  CreditApplication + DealWriteup; `hand_off_to_fandi`
  writes new FK; `record_credit_application` accepts new
  optional kwarg and raises new
  `DealWriteupAlreadyLinkedError`) and one M32.2 change
  (removal of `salesApi.ts:10-25` "UI deferred"
  comments).

## 6. Streak accounting projections (at M32.0)

- **Planning-time as-recommended streak: 10 → 11.** Target
  selected as recommended after seven-alternative
  comparison + eleven-verification pass performed at user
  direction. Two verification-driven revision rounds
  (D3 fail-explicit; D4-revised² manager-only tab; D8-
  revised non-navigational rows; D9-revised² OneToOneField
  with three-layer defense) shaped the final locked design
  but did not change the target selection. §0.a M32.0
  amendments (none as of M32.0 open) are corrective and
  do not affect the streak. Historical run of 89 across
  M10 → M23 preserved for the record.
- **Zero-drift permission-class streak: 33 → 34 (projected
  at M32.1 close) → 35 (projected at M32.2 close) → 36
  (projected at M32.3 close).** All new endpoints reuse
  existing classes verbatim; M32.2 + M32.3 ship no new
  backend endpoints.
- **Substrate-compound-value continuation: 5 links (unchanged).**
  M27.1 → M28.1 → M29 → M30 → M31 preserved as the depth
  arc. M32 chooses breadth (fresh direct-operator gap in
  sales-to-F&I workflow) over depth (sixth substrate-
  compound-value link would have been NEW C F&I chargeback,
  still pilot-evidence-gated). Standing question elevated
  from M31 §9 resolved with breadth answer.
- **DoD exception path invocations: 6 → 7.** M26 + M27.1
  + M28.1 + M29.1 + M30.1 + M31.1 + **M32.1**. Pattern
  firmly established. M32.2 + M32.3 satisfy DoD directly.
- **Playwright-independent-fixture pattern (NEW):** M32.3
  is the first Playwright increment to explicitly require
  fixture independence from a same-milestone earlier
  increment's UI-created state. Establishes idempotent
  seed-command pattern for downstream-receiver journeys.
  Candidate for durable lesson elevation at M32
  retrospective §5 if the pattern re-applies at M33+.
- **Two-consecutive-DoD-exception-invocations pattern
  (candidate lesson):** M32.1 + M32.2 is the first time
  since DoD exception path was introduced (M26) that two
  consecutive increments both satisfy DoD (M32.1 via
  exception; M32.2 directly). Wait — reversed: M32.1
  invokes exception, M32.2 satisfies directly. Pattern
  clarification: no two consecutive exception invocations.
  Six consecutive substrate-first exception invocations
  (M26 + M27.1 + M28.1 + M29.1 + M30.1 + M31.1 + M32.1)
  each followed by direct DoD satisfaction in the
  customer-facing increment.
- **First break out of accounting/templates domain since
  M27 (SIX milestones ago; M22-M23 was last non-
  accounting).** Signals healthy operator-coverage
  domain diversification. M31 §9 standing question
  answered with breadth after depth.
- **First schema-level pairing constraint added to
  DealWriteup ↔ CreditApplication seam** (M32.1).
  Documented as evolutionary step from M11.3 peer-not-
  child preference to M32 peer-with-optional-backpointer.
  Not a violation of prior architectural decision — the
  M11.3 docstring's "no FK on either side" was accurate
  at that time; M32.1 records the evolution truthfully in
  current model/service docstrings without rewriting the
  historical migration.
- **First milestone since M20 to add a new Playwright
  persona** (`f_and_i_manager`). Existing multi-persona
  pattern followed exactly; no new infrastructure
  required.
- **First customer-facing milestone since M11 to ship
  across three increments.** Three-increment shape is
  scope-driven per verification findings, not
  convention-driven. M28 → M31 all shipped two-increment
  substrate + UI shapes.
- **Audit coverage projected at M32 close:** 158 → 161
  endpoints (+3: writeup list + writeup detail + CA
  list); 124 → 127 covered (+3, all M32.3-covered per
  D8 F&I intake page + D4-revised²/D5/D6 sales-manager
  UI); 34 backend-only unchanged (three backend-only
  endpoints #112–114 remain classified as such at M32.1
  close since UI ships in M32.2/M32.3; re-classify at
  M32 close-out per M31 precedent).

## 7. Anchors that win on conflict (for M32.1 / M32.2 / M32.3)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M1–M28 shipped in-tree; M29–M31 shipped surface in
   CAPABILITY_MATRIX §7δ + §7ε + §7ζ per convention
   adopted at M27+; M32 shipped surface will be §7η per
   M31 precedent)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_31_RETROSPECTIVE.md` §9 (M32
   candidate list origin — deal writeups elevated on the
   basis of shipped-source deferral promise + largest un-
   gated direct operator-coverage gain + natural sales-
   to-F&I bridge + M31 §9 breadth-vs-depth standing-
   question resolution)
6. **`docs/roadmap/MILESTONE_32_PLANNING.md`** (this
   document — M32 governing contract + §0.a + all §5
   locks + §4.1–§4.11 verifications including the three
   blocking findings resolved architecturally + two
   inaccessibility findings resolved by truthful posture)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (M31
   baseline — 158 endpoints / 124 covered / 34 backend-
   only / 318 service verbs; M32 projected delta +3
   endpoints, +3 covered, +3 verbs)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25) + §7α (M26) +
   §7β (M27) + §7γ (M28) + §7δ (M29) + §7ε (M30) + §7ζ
   (M31 shipped surface); M32 §7η added at M32 close
9. `docs/roadmap/MILESTONE_11_PLANNING.md` §7 M11.3 (M11.3
   DealWriteup entity + service verbs + endpoints origin
   — governs the "no FK on either side" architectural
   preference that M32.1 D9-revised² evolves to peer-
   with-optional-backpointer)
10. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs the M32.2 co-located inline-
    dialog choice; no shared abstraction for
    `WriteupApproveConfirmDialog` /
    `WriteupHandoffConfirmDialog`)
11. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified through M32.0 §4.5 for
    APPROVE / HAND-OFF FK discoverability; M32.1 D1 + D2
    resolve the blocking finding)
12. Memory record
    `feedback_playwright_as_operational_contract.md`
    (M32.2 + M32.3 Playwright journeys are the operational
    contract for the anchor business question; independent
    fixture guarantee at M32.3 is a strengthening of the
    contract)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.
