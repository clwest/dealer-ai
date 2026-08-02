---
state: active
date: 2026-08-02
last_session_shipped: SESSION_115
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: shipped
milestone_11_status: in_progress
next_session: SESSION_116
next_milestone: 11
next_milestone_name: "Sales-side non-chat channels + customer-journey completeness"
next_increment: 3
next_increment_name: "M11.3 — DealWriteup entity + F&I handoff action"
---

# Next session — SESSION_116 · Milestone 11 · Increment 3 (M11.3 — DealWriteup entity + F&I handoff action)

> **SESSION_115 shipped M11.2 —**
> new `TestDrive` entity + tenancy
> carrier extension (34 → 35) +
> `services/test_drives/` package
> with `record_test_drive` verb +
> `POST /admin/test-drives/`
> endpoint + 23 focused tests
> (target ~20). §5.c Option A was
> already confirmed at SESSION_114
> open — no new decisions surfaced
> at M11.2 implementation time.
> Streak stands at **35 as-
> recommended M5.1 → M11.1**.
>
> **Backend baseline: 3,758 → 3,781
> (+23, zero regressions).**
> Frontend baseline: **51**
> (unchanged; M11.2 is backend-
> only). Migrations `0001`–`0033`.
> DRF admin surface **68 → 69**.
> Tenancy carriers **34 → 35**.
> Permission classes **8**
> (unchanged — reused M4
> `IsSalesManagerOrOwnerAtActiveDealership`).

## First thing SESSION_116 must do

### 1. Confirm §5.e for M11.3 was already recorded

Per `MILESTONE_11_PLANNING.md`
§0.a (M11.1 amendment), **§5.e
Option A** (DealWriteup → F&I
handoff auto-creates the M10.1
CreditApplication server-side)
was confirmed at SESSION_114
open. No new decisions block
M11.3.

If a new `[NEEDS-DECISION]`
surfaces at implementation time
(e.g. which DealWriteup fields
auto-copy into the
CreditApplication, or whether
the handoff also creates the
M10.2 DealStructure), amend
§0.a narrowly per M5-M10
precedent before writing code.

### 2. Verify starting state

- `git status` — clean (M11.2
  commit landed at SESSION_115
  close).
- `git log --oneline -3` — top
  should be the M11.2 commit.
- `python3 manage.py test dealer_ai`
  → **3,781 pass, 1 skipped, 0
  fail**.
- `python3 manage.py check`
  clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No
  changes detected."
- `redis-cli ping` → `PONG`.

## What M11.3 delivers

Per `MILESTONE_11_PLANNING.md`
§1.3 + §1.7 + §5.e Option A +
§7 M11.3:

- **New `DealWriteup` model**
  (four-square-style summary
  tied to F&I handoff memo).
  - `dealership` FK CASCADE
    (tenancy carrier; extend
    35 → 36).
  - `lead` FK to `CustomerLead`
    CASCADE.
  - `vehicle` FK to `Vehicle`
    CASCADE.
  - `vehicle_price` (proposed),
    `trade_allowance`,
    `down_payment` (proposed),
    `monthly_payment_target`,
    `term_months_target`,
    `apr_target` DecimalFields.
  - `write_up_at` datetime.
  - `written_up_by_user` FK
    User SET_NULL.
  - `sales_manager_approved_at`
    nullable +
    `sales_manager_approved_by_user`
    FK User SET_NULL.
  - `handed_off_to_fandi_at`
    nullable (link into M10.1
    CreditApplication).
  - `notes` TextField (blank OK).
  - Cross-tenant `clean()`
    guard on `lead` + `vehicle`.
- **New `services/deal_writeups/`
  package** (mirrors M11.1
  `services/leads/` + M11.2
  `services/test_drives/`
  layout).
- **Verbs (three):**
  - `record_deal_writeup(...)`
    — create.
  - `approve_deal_writeup(...)`
    — sets
    `sales_manager_approved_*`
    timestamps.
  - `hand_off_to_fandi(...)` —
    per §5.e Option A, server-
    side auto-creates a
    matching M10.1
    `CreditApplication` (copies
    applicant name from lead;
    other CA fields TBD at
    implementation time — mark
    any surfacing decision in
    §0.a).
- **Endpoints (three or four):**
  - `POST /admin/deal-writeups/`
  - `POST /admin/deal-writeups/<pk>/approve/`
  - `POST /admin/deal-writeups/<pk>/hand-off/`
  - (optional) `PATCH
    /admin/deal-writeups/<pk>/`
    for edits pre-approval.
- **~25 focused tests** across
  model / service / endpoint /
  handoff-integration files.
- **Baseline target 3,781 →
  ~3,806.**

### Non-goals for M11.3

- ❌ No cadence orchestration
  (M11.4).
- ❌ No be-back (M11.5).
- ❌ No frontend at M11.3
  (M11.6).
- ❌ No modification of M1-M11.2
  business logic.
- ❌ No modification of M10.1
  CreditApplication semantics —
  the handoff creates via the
  existing service verb,
  doesn't extend the model.
- ❌ No DealStructure auto-
  creation at handoff (deferred
  — CreditApplication only).

## What SESSION_116 should do

### Recommended step sequence

1. **Confirm §5.e Option A**
   still fits at implementation
   time. If field-copy specifics
   need a decision (e.g. does
   the handoff copy the deal's
   monthly-payment target into
   the CA notes?), record in
   §0.a.

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_11_PLANNING.md`
     §1.3 + §1.7 + §5.e + §7
     M11.3.
   - `docs/handoffs/SESSION_115_m11_inc2_test_drive.md`
     (previous session).
   - `docs/research/SALES_DEPARTMENT_MAPPING.md`
     §workflow step 10 (deal
     write-up) + §workflow step
     11 (F&I handoff).
   - `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
     §1.1 (CreditApplication
     intake — the F&I side of
     the handoff).
   - `backend/dealer_ai/models.py::CreditApplication`
     (M10.1 model — target of
     the handoff).
   - `backend/dealer_ai/services/f_and_i/credit_application.py`
     (`record_credit_application`
     — the verb the handoff
     calls).
   - `backend/dealer_ai/services/test_drives/`
     (M11.2 pattern to mirror).

3. **Verify starting state**
   (§2 above).

4. **Draft (in order):**
   - `DealWriteup` model +
     tenancy carrier (35 → 36).
   - Migration `0034`.
   - `services/deal_writeups/`
     package + three verbs.
   - `views_deal_writeups.py`
     + serializers + endpoints.
   - URL routes.
   - ~25 focused tests
     (including handoff round-
     trip integration test:
     writeup → handoff →
     CreditApplication exists +
     properly attached to the
     same lead).

5. **Full-suite verification.**
   Target 3,781 → ~3,806.

6. **Ship handoff at
   `docs/handoffs/SESSION_116_m11_inc3_deal_writeup.md`.**

7. **Overwrite
   `00-START-NEXT-SESSION.md`**
   with M11.4 priority
   (FollowUpCadence + FollowUpTask
   + Celery-beat scheduling).

## Explicit non-goals for SESSION_116

- ❌ Do NOT ship M11.4-M11.7
  scope.
- ❌ Do NOT modify M1-M11.2
  business logic.
- ❌ Do NOT modify the M10.1
  CreditApplication model shape.
- ❌ Do NOT force-push or amend
  the M11.1 / M11.2 commits.

## NEXT TASK

Start SESSION_116 with (a)
verifying §5.e Option A still
fits (M11.1 recorded it in
§0.a), (b) the read-first list,
(c) starting-state verification,
then (d) `DealWriteup` model +
tenancy carrier extension (35 →
36) + migration + service
package with three verbs
(record / approve / hand-off) +
endpoints + ~25 tests including
the handoff → CA round-trip.
Target baseline 3,781 → ~3,806.
Ship the M11.3 handoff.

Backend baseline at SESSION_116
close: **~3,806 pass**.
Frontend baseline: unchanged
(no frontend at M11.3).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 11
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_11_PLANNING.md`
   (§0.a M11.1 amendment carrying
   §5.e Option A)
6. `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_115_m11_inc2_test_drive.md`
   (this session's close)
8. `docs/handoffs/SESSION_114_m11_inc1_channel_intake.md`
9. `docs/CAPABILITY_MATRIX.md` §7k
10. `docs/research/SALES_DEPARTMENT_MAPPING.md`
11. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_115 — M11.2 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0033`. Test baseline:
  **3,781 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 51 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. 4 scheduled
  task families registered
  (unchanged since M7).
- **Milestones shipped:** M1 →
  **M10**. M11 in progress
  (M11.1 + M11.2 shipped).
- **DRF admin surface:** **69**
  (68 + M11.2's TestDrive
  endpoint).
- **Frontend operator routes:**
  **11** (unchanged; M11.2
  backend-only).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` package
  (M10 close) + `services/leads/`
  (M11.1) + `services/test_drives/`
  (M11.2).
- **Tenancy carriers:** **35**
  (34 → 35 for TestDrive).
- **Permission classes:** **8**
  (unchanged).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:**
  unchanged.
- **Deterministic rules:**
  unchanged.
- **`CustomerLead.channel`:** 5+1
  vocab (chat / walk_in / phone
  / listing_form / referral /
  other); historical rows
  backfilled to `chat` (M11.1
  migration).
- **Webhook adapter registry:**
  `{"generic": ...}` (M11.1;
  extensible).
- **`TestDrive` FK shape:**
  mandatory both `CustomerLead`
  + `Vehicle` (M11.2 §5.c
  Option A).
- **Milestone 11 next:** M11.3
  `DealWriteup` entity + three-
  verb service (record / approve
  / hand-off) with server-side
  auto-CA-creation on handoff
  per §5.e Option A. ~25 tests.
  Baseline 3,781 → ~3,806.
