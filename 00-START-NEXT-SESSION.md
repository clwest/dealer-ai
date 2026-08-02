---
state: active
date: 2026-08-02
last_session_shipped: SESSION_108
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: in_progress
next_session: SESSION_109
next_milestone: 10
next_milestone_name: "Finance (F&I) deal desk"
next_increment: 4
next_increment_name: "M10.4 — Stipulation tracking"
---

# Next session — SESSION_109 · Milestone 10 · Increment 4 (M10.4 — Stipulation tracking)

> **SESSION_108 shipped M10.3 —**
> `LenderProgram` + `LenderSubmission`
> entities + `services/f_and_i/lender.py`
> module (six verbs) + three new
> endpoints (`POST /admin/lender-programs/`,
> `POST /admin/lender-submissions/`,
> `PATCH /admin/lender-submissions/<pk>/`)
> + tenancy carrier extensions (26 → 28)
> + 53 focused tests. Four design
> questions resolved at session open
> (all four as-recommended, all Option
> A): §1.3.a (attach FK to
> DealStructure), §1.3.b (fixed 4-value
> status), §1.3.c (per-dealership
> catalog), §1.3.d (free-form JSON
> terms).
>
> **Backend baseline: 3,586 pass, 1
> skipped, 0 fail** (was 3,533 at
> SESSION_107 close). Frontend Vitest
> baseline: 34 pass (unchanged; no
> frontend at M10.3). Migrations
> `0001`–`0027`. Tenancy carriers 28.
> DRF admin surface 52.
>
> **Push to `origin/main` for the
> M10.1 + M10.2 + M10.3 commits is
> deferred pending explicit user
> authorization** per M9-close
> convention. Three commits pending.
>
> **SESSION_109 opens M10.4 —
> Stipulation tracking.** Attach shape
> and vocabulary decisions surface at
> session open. `§5.b Option A` from
> SESSION_106 already ratified the
> fixed 5-value stipulation vocabulary
> (`proof_of_income` / `proof_of_insurance`
> / `proof_of_residence` /
> `references` / `other`).

## First thing SESSION_109 must do

### 1. Check push authorization for the M10.1 + M10.2 + M10.3 commits

Three M10 commits live locally on
`main` only. Verify with the user:

- `git log origin/main..HEAD
  --oneline` — should show three
  commits (M10.1, M10.2, M10.3).
- Should they push now? If yes:
  `git push origin main` after
  explicit user "go."

Push is a shared-state action; per
CLAUDE.md safety posture, requires
per-push confirmation independent of
the per-increment authorization that
landed each commit.

### 2. Confirm M10.4 §5-equivalent decisions

Planning §1.4 covers Stipulation
sketch but leaves several decisions
for session open. Re-read
`MILESTONE_10_PLANNING.md` §1.4 +
§5.b at session open. Questions
likely to surface:

- **Stipulation attach point.** Per
  `§1.4`: "attached to a
  `LenderSubmission`" — is that
  mandatory (Option A), or should
  it be nullable + also attach to
  `DealStructure` for deal-level
  stips that predate lender
  submission (Option B, mirrors
  M10.1 §5.a Option C pattern)?
- **State vocabulary.** Planning
  §1.4 suggests three values
  (`open` / `cleared` / `waived`).
  Fixed set (matches M10.1 §5.b /
  M10.3 §1.3.b) or extensible?
- **`documented_by` field.** User FK
  vs free-text string? User FK
  requires the F&I manager to be
  logged in as themselves;
  free-text is more forgiving but
  loses audit-trail rigor.
- **Photo / document evidence
  capture.** Nested at M10.4
  (Stipulation gains `evidence_photo`
  field + storage plumbing) or
  defer to M10.7 compliance layer
  (this session ships state
  tracking only)?

**If any decision surfaces, do NOT
write M10.4 code until it's resolved
with the user.** Amend
`MILESTONE_10_PLANNING.md` §0.a
narrowly per prior precedent.

### 3. Verify starting state

- `git status` — clean (M10.3
  commit landed at SESSION_108
  close).
- `git log --oneline -3` — top
  should be `Milestone 10 ·
  Increment 3 — LenderProgram +
  LenderSubmission entities …
  (SESSION_108)` or similar.
- `python3 manage.py test dealer_ai`
  → **3,586 pass, 1 skipped, 0
  fail.**
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npm test` →
  **34 pass**.
- `npx tsc --noEmit` + `npx vite
  build` both clean.
- `redis-cli ping` → `PONG`.

## What M10.4 delivers

Per `MILESTONE_10_PLANNING.md` §7
M10.4:

- **New `Stipulation` model +
  migration `0028`.** FK to
  `LenderSubmission` (attach
  shape per §5-equivalent). Fields:
  `stip_type` from fixed
  vocabulary (per §5.b Option A —
  `proof_of_income` /
  `proof_of_insurance` /
  `proof_of_residence` /
  `references` / `other`),
  `state` (`open` / `cleared` /
  `waived`), `documented_by`
  (User FK OR free-text — TBD),
  `cleared_at` DateTime null,
  `notes` TextField.
- **Tenancy-carrier extension
  28 → 29.**
- **New `services/f_and_i/stipulation.py`**
  module — sibling to
  `services/f_and_i/credit_application.py`
  / `deal_structure.py` /
  `lender.py`. Verbs:
  record_stipulation, clear/waive
  (state transitions), get, list
  by submission.
- **New endpoints** —
  `POST /admin/stipulations/`,
  `PATCH /admin/stipulations/<pk>/`
  (state update).
- **~20 focused tests.**
- **Baseline target 3,586 →
  ~3,606.**

### Non-goals for M10.4

- ❌ No `Contract` / `FundingPacket`
  / `FundingStatus` entities
  (M10.5).
- ❌ No `Chargeback` / `net_realized`
  verb (M10.6).
- ❌ No `ComplianceRecord` /
  operator UI (M10.7).
- ❌ No photo / document storage
  plumbing (deferred to M10.7 per
  the design question above,
  unless user rules otherwise at
  session open).

## What SESSION_109 should do

### Recommended step sequence

0. **Push authorization check** (§1
   above).

1. **Confirm M10.4 §5-equivalent
   decisions with the user** (§2
   above). Do NOT write code until
   every open decision is
   resolved.

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_10_PLANNING.md`
     §1.4 + §5.b + §7 M10.4.
   - `docs/handoffs/SESSION_108_m10_inc3_lender.md`
     (previous session).
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

3. **Verify starting state** (§3
   above).

4. **Draft (in order):**
   - `Stipulation` model +
     migration `0028`.
   - Tenancy carrier addition
     (28 → 29).
   - `services/f_and_i/stipulation.py`
     module.
   - Endpoints + URLs.
   - ~20 focused tests.

5. **Full-suite verification.**
   Target 3,586 → ~3,606.

6. **Ship handoff at
   `docs/handoffs/SESSION_109_m10_inc4_stipulation.md`.**

7. **Overwrite
   `00-START-NEXT-SESSION.md`** with
   M10.5 priority.

## Explicit non-goals for SESSION_109

- ❌ Do NOT ship Contract /
  FundingPacket / FundingStatus /
  Chargeback / ComplianceRecord
  entities (M10.5-M10.7).
- ❌ Do NOT ship frontend UI
  (M10.7).
- ❌ Do NOT modify M1-M9 or M10.1-
  M10.3 business logic.
- ❌ Do NOT force-push or amend the
  M10.1 / M10.2 / M10.3 commits.

## NEXT TASK

Start SESSION_109 with (a) push-
authorization check for M10.1 +
M10.2 + M10.3 commits, (b)
confirming M10.4 §5-equivalent
decisions with the user, (c) the
read-first list, (d) starting-state
verification, then (e) `Stipulation`
model + service + endpoints + ~20
tests. Target baseline 3,586 →
~3,606. Ship the M10.4 handoff.

Backend baseline at SESSION_109
close: **~3,606 pass**. Frontend
baseline: unchanged (no frontend at
M10.4).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 10
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_10_PLANNING.md`
6. `docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_108_m10_inc3_lender.md`
8. `docs/handoffs/SESSION_107_m10_inc2_deal_structure.md`
9. `docs/handoffs/SESSION_106_m10_inc1_credit_application.md`
10. `docs/handoffs/SESSION_105_m9_closeout.md`
11. `docs/handoffs/SESSION_104_m9_inc5_operator_ui.md`
12. `docs/handoffs/SESSION_103_m9_inc4_buyer_accuracy.md`
13. `docs/handoffs/SESSION_102_m9_inc3_analytics_extensions.md`
14. `docs/handoffs/SESSION_101_m9_inc2_delivery.md`
15. `docs/handoffs/SESSION_100_m9_inc1_sale_entity.md`
16. `docs/CAPABILITY_MATRIX.md` §7j
17. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules + research +
code are facts.

---

## Operational state (post-SESSION_108 — M10.3 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations `0001`–`0027`.
  Test baseline: **3,586 pass**, 1
  skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` + `vite
  build` clean. **Vitest baseline:
  34 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery 5.5.3 +
  Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. 4 scheduled
  task families registered
  (unchanged since M7).
- **Milestones shipped:** M1 →
  **M9** (SESSION_105 close); M10
  in progress (SESSION_106 M10.1;
  SESSION_107 M10.2; SESSION_108
  M10.3).
- **DRF admin surface:** 52
  endpoints (M9 47 + M10.1
  credit-applications + M10.2
  deal-structures + M10.3 lender-
  programs + lender-submissions
  POST + lender-submissions PATCH).
- **Frontend operator routes:** 9
  (unchanged; no frontend at
  M10.1-M10.3).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** M8 added
  `services/analytics/` (4
  submodules); M9.1
  `services/sale/`; M9.2
  `services/delivery/`; M9.3-M9.4
  extended M8 modules; M10.1
  added `services/f_and_i/`
  (with `credit_application.py`);
  M10.2 extended
  `services/f_and_i/` with
  `deal_structure.py`; **M10.3
  extended `services/f_and_i/`
  with `lender.py`** — now three
  submodules in the F&I package.
- **Tenancy carriers:** 28 (M1 six
  + M3 three + M4 six + M5 two +
  M6 two + M7 two + M8 one + M9.1
  one — `Sale` + M9.2 one —
  `Delivery` + M10.1 one —
  `CreditApplication` + M10.2 one
  — `DealStructure` + **M10.3
  two — `LenderProgram` +
  `LenderSubmission`**).
- **Permission classes:** 8 in
  `dealer_ai/permissions.py` (M1
  four + M4 one + M9 uses M4's +
  M10.1 one —
  `IsFinanceManagerOrOwnerAtActiveDealership`,
  reused unchanged at M10.2 and
  M10.3).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** unchanged.
- **Deterministic rules:**
  unchanged.
- **M10.3 substrate (shipped):**
  `LenderProgram` per-dealership
  catalog (unique
  `(dealership, name)`;
  `is_active` soft-delete pattern)
  + `LenderSubmission` linking a
  `DealStructure` to a
  `LenderProgram` (CASCADE +
  PROTECT respectively) with
  fixed 4-value status vocabulary
  (`pending` / `approved` /
  `counter` / `declined`) and
  free-form JSON `counter_terms`
  + `approval_terms`. Any-to-any
  status transition allowed at
  M10.3.
- **Milestone 10 next:** M10.4
  `Stipulation` model + lifecycle
  verbs, attached to
  `LenderSubmission`. Fixed
  5-value vocabulary per §5.b
  Option A. Verify §5-equivalent
  decisions at session open. ~20
  tests. Baseline 3,586 →
  ~3,606.
