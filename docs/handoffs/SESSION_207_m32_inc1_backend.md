---
title: "SESSION_207 handoff — Milestone 32 · Increment 1 (M32.1 — backend substrate + provenance-FK migration)"
status: active
type: handoff
date: 2026-08-04
session: 207
milestone: 32
milestone_status: active
milestone_name: "Deal Writeups: Sales-Manager-to-F&I Handoff (writeup CRUD substrate + sales-manager UI + F&I intake queue + provenance-FK migration)"
increment: 1
increment_status: shipped
commit: 16c54e9
commit_notes: "M32.1 backend substrate — local commit landed as 16c54e9 at close per M28.1 / M29.1 / M30.1 / M31.1 cadence; hash backfilled via a subsequent commit; NOT pushed. Coordinated push at M32 close after explicit user confirmation."
---

# SESSION_207 — Milestone 32 · Increment 1 (M32.1 — backend substrate + provenance-FK migration)

## What shipped

SESSION_207 opened per the M32.0 first-thing sequence in
`00-START-NEXT-SESSION.md`. Three deliverables landed:

1. **Migration `0051_m32_credit_application_deal_writeup_fk.py`**
   — nullable `OneToOneField` from `CreditApplication` to
   `DealWriteup` (`SET_NULL`, `related_name="credit_application"`).
   Docstring records the D9-revised² architectural rationale +
   three-layer-defense design + reverse-migration behavior. Fully
   reversible; historical migration 0034 preserved unchanged.
2. **Backend substrate** — 3 new service verbs, 3 new endpoints,
   1 new error class, 4 docstring updates on shipped M11.3/M10.1
   files. Details in §7.
3. **51 new tests** across 2 files (`test_m321_deal_writeup_read.py`
   for D1 + D2 read surface; `test_m321_credit_application_intake.py`
   for D3 read surface + D9-revised² provenance-FK behavior including
   mandatory `test_writeup_cannot_link_to_multiple_credit_applications`
   exercising all three defense layers) — total observed: **62
   tests** (+11 vs planned ~51 due to more granular coverage of
   the fail-explicit query matrix + provenance FK behavior).

**DoD exception path invocation #7.** Backend substrate with no
operator-facing behavior change on its own. M32.2 + M32.3 satisfy
DoD directly per the M32.0 §5.f contract.

**Session artifacts:**

- **Starting-state verification (§1):** git clean; `HEAD` ahead
  of `origin/main` by 2 (SESSION_206 M32.0 planning +
  hash-backfill); Redis PONG; Django `check` clean;
  `makemigrations --check` clean; frontend `tsc --noEmit` clean;
  acceptance `tsc --noEmit` clean; backend suite **4,933 pass,
  1 skipped, 0 fail** (166.5s); frontend Vitest **319 pass** (36
  files, 6.24s); acceptance DB reset per SESSION_200 §0.a
  durable lesson (v). Matches M32.0 baseline exactly.
- **Confirmed working from M32.0 planning memo (§2):** read
  §5.b D1 + D2 + D3 + D9-revised² + §5.e M32.1 before touching
  backend code. Zero deviations from planning.
- **M32.1 backend substrate shipped (§3):** see §7.
- **Regression check after schema + service + endpoint changes:**
  full backend suite ran green (**4,933 pass** — no regressions
  from schema addition, service verb signature-additive
  extension, and 3 new endpoints).
- **M32.1 test suite added and green:** **62 pass** on new
  `test_m321_deal_writeup_read.py` (30 tests: service list,
  service get, endpoint list auth, endpoint list filter
  validation, endpoint list projection, endpoint detail) +
  `test_m321_credit_application_intake.py` (32 tests: provenance
  FK behavior including mandatory 3-layer defense test, service
  list, endpoint auth, endpoint filter validation, endpoint
  projection).
- **Close baselines (§4) all match projections:** backend
  **4,995 pass** (+62 vs M32.0), 1 skipped, 0 fail; Django
  `check` clean; `makemigrations --check` clean; audit
  regenerated as **161 total / 124 covered / 37 backend-only /
  321 service verbs** (matches §5.e M32.1 projection exactly:
  158→161 endpoints, 124 unchanged, 34→37 backend-only, 318→321
  verbs).
- **DoD exception path invocation #7 documented** — see §3 rationale.
- **§5.h non-goals respected:** no frontend changes; no
  Playwright; no historical migration 0034 modification; M10.1
  create endpoint URL config preserved exactly (M32.1 list
  endpoint at `/list/` sibling path, not method-dispatched at
  the same URL).

## 1. Verification results at open

- **git status:** clean; `HEAD` ahead of `origin/main` by 2
  commits.
- **git log --oneline -4:** M32.0 hash-backfill `4e2afc9`;
  M32.0 planning `c3d46fd`; M31.2 hash-backfill `08fef5f`; M31
  shipped `4b5f5b9`.
- **`python3 manage.py test dealer_ai`:** 4,933 pass, 1 skipped,
  0 fail (166.5s).
- **`cd frontend && npm test`:** 319 pass across 36 files (6.24s).
- **`python3 manage.py check`:** clean (7 benign DecimalField
  warnings — pre-existing).
- **`python3 manage.py makemigrations --check --dry-run`:** "No
  changes detected."
- **`cd frontend && npx tsc --noEmit`:** clean.
- **`cd acceptance && npx tsc --noEmit`:** clean.
- **`redis-cli ping`:** PONG.
- **`rm -f backend/db.acceptance.sqlite3`:** completed per
  SESSION_200 §0.a durable lesson (v).

All matches M32.0 close baseline exactly.

## 2. Migration 0051

`backend/dealer_ai/migrations/0051_m32_credit_application_deal_writeup_fk.py`.

- **Schema change:** `CreditApplication.deal_writeup` — nullable
  `OneToOneField` to `DealWriteup`, `on_delete=SET_NULL`,
  `related_name="credit_application"`.
- **Migration docstring** (76 lines) records: why-a-schema-change-
  now rationale (M11.3 peer-not-child preference → M32 peer-
  with-optional-backpointer as pairing determinism becomes load-
  bearing on F&I intake UI); why-OneToOneField-not-FK-plus-unique
  (Django-native + auto unique index + M11.3 lifecycle-contract
  match); nullability preserved (direct-create + historical CAs
  stay NULL); three-layer defense summary; peer-with-backpointer
  semantics (retention-clock ownership stays on CA per M10.1
  §5.e); reverse-migration behavior (fully reversible; linkage
  data drop on revert is operationally recoverable from M11.3
  `notes` text prefix).
- **Historical migration 0034 NOT modified** per M32.0 §5.h non-
  goals. Architectural evolution recorded in models.py
  `CreditApplication` + `DealWriteup` docstrings + service
  docstrings + migration 0051 docstring + M32.0 planning memo +
  (upcoming M32 retrospective + CAPABILITY_MATRIX §7η).
- **`makemigrations --check --dry-run`:** clean after migration
  landed.

## 3. DoD exception path invocation #7

Per M21.0 §5.f Option B (M26 lineage): every customer-facing
milestone must add or update at least one Playwright operational
journey, or explicitly document why no journey change is
required.

**M32.1 rationale for exception:**

- Backend substrate only — no operator-facing behavior change on
  its own. New endpoints (writeup list, writeup detail, CA list)
  are read verbs behind role gates; they surface no new
  functionality until M32.2 (sales-manager UI) and M32.3 (F&I
  intake UI) wire them up.
- Migration 0051 adds a nullable schema column; no visible-
  behavior change today (existing CAs unaffected; new hand-offs
  populate the FK but hand-off UX identical from operator
  perspective).
- New tests cover the substrate at the service + endpoint layers
  (62 tests). Playwright coverage will land in M32.2 + M32.3
  where operator-facing behavior surfaces.

**Seventh consecutive invocation** (M26 + M27.1 + M28.1 + M29.1
+ M30.1 + M31.1 + **M32.1**). Pattern firmly established.
M32.2 + M32.3 will satisfy DoD directly.

## 4. Baselines at close

- Backend suite: **4,933 → 4,995 pass** (+62), 1 skipped, 0 fail.
- Frontend Vitest: 319 pass across 36 files (unchanged — no
  frontend work in M32.1).
- Acceptance: 22 journeys (unchanged — no Playwright in M32.1).
- Django `check`: clean.
- `makemigrations --check --dry-run`: "No changes detected."
- Audit artifact regenerated: **161 endpoints / 124 covered / 37
  backend-only / 321 service verbs**.
  - Endpoints 158 → 161 (+3): `admin-deal-writeup-list`,
    `admin-deal-writeup-detail`, `admin-credit-application-list`.
  - Covered 124 → 124 (unchanged — three new endpoints classified
    as backend-only at M32.1; re-cover at M32.2 + M32.3 via UI
    wrappers).
  - Backend-only 34 → 37 (+3, matching the three new endpoints
    transitionally).
  - Service verbs 318 → 321 (+3): `list_deal_writeups`,
    `get_deal_writeup`, `list_credit_applications`.
- DRF admin surface: 118 → 121 (+3).
- Migration count: 0050 → 0051 (+1).

## 5. Streaks at M32.1 close

- **Planning-time as-recommended streak:** unchanged at **11**
  (from M32.0 close). M32.1 is pure implementation.
- **Zero-drift permission-class streak:** 33 → **34** consecutive
  (M10 → M32.1). M32.1 endpoints all reuse existing classes:
  writeup list/detail use `_M113_PERMS` (M11.3
  `IsSalesManagerOrOwnerAtActiveDealership`); CA list uses
  `_M101_PERMS` (M10.1
  `IsFinanceManagerOrOwnerAtActiveDealership`). No new class.
- **DoD exception path invocations:** 6 → **7** (M26 + M27.1 +
  M28.1 + M29.1 + M30.1 + M31.1 + M32.1).
- **Substrate-compound-value continuation:** 5 links unchanged.
  M32 chose breadth over depth per M31 §9 standing question.
- **First schema-level pairing constraint added at M32.1** — the
  nullable OneToOneField backpointer, three-layer defense
  (documented + tested).
- **First F&I-role-gated list endpoint** shipped (M32.1
  `admin_credit_application_list` on
  `IsFinanceManagerOrOwnerAtActiveDealership`).
- **Historical-migration-immutability discipline preserved** —
  migration 0034 untouched; architectural evolution recorded in
  currently-mutable surfaces per M32.0 §5.h non-goals.

## 6. What did NOT change

Per M32.0 §5.h non-goals:

- ❌ **Historical migration 0034 not modified.**
- ❌ **M10.1 `admin_credit_application_create` view function
  and URL not modified.** M32.1 CA list endpoint lives at
  `/admin/credit-applications/list/` sibling path.
- ❌ **M11.3 `admin_deal_writeup_create` view function and URL
  not modified.** M32.1 writeup list endpoint lives at
  `/admin/deal-writeups/list/` sibling path.
- ❌ **M11.3 `admin_deal_writeup_approve` /
  `admin_deal_writeup_hand_off` view functions not modified**
  (`hand_off_to_fandi` service verb has a 1-line signature-
  additive extension per D9-revised² but the endpoint call
  path is unchanged).
- ❌ **No new permission classes.**
- ❌ **No frontend code touched.**
- ❌ **No Playwright code touched.**

## 7. §7 shipped surface details

### Migration

- `0051_m32_credit_application_deal_writeup_fk.py` (76-line
  docstring recording D9-revised² rationale, three-layer
  defense, reverse-migration behavior).

### Model changes (`backend/dealer_ai/models.py`)

- `CreditApplication` — added `deal_writeup` nullable
  `OneToOneField(SET_NULL, related_name="credit_application")`.
- `CreditApplication` — extended class docstring with new
  "M32.1 extension — provenance backpointer" paragraph.
- `DealWriteup` — extended class docstring "Handoff link"
  paragraph with M32.1 provenance-link note.

### Service layer

- **`services/f_and_i/credit_application.py`:**
  - New error class `DealWriteupAlreadyLinkedError` (endpoint
    layer maps to 409 CONFLICT).
  - `record_credit_application` — signature-additive
    `deal_writeup: Optional[DealWriteup] = None` kwarg;
    same-tenant guard via new `_assert_same_tenant_deal_writeup`
    helper; already-linked guard via new
    `_assert_writeup_not_already_linked` helper (raises
    `DealWriteupAlreadyLinkedError` before DB write);
    persistence extended to include `deal_writeup=deal_writeup`.
    Existing kwargs + return shape unchanged.
  - New verb `list_credit_applications(*, dealership,
    intake=False, lead=None, since=None)` — tenant-scoped;
    composable filters; `intake=True` uses
    `.exclude(deal_structures__contracts__isnull=False).distinct()`
    to select pre-contract CAs; `select_related` extended to
    include `deal_writeup`.
  - Module docstring updated to reflect four verbs (was three).
- **`services/f_and_i/__init__.py`:** exports
  `DealWriteupAlreadyLinkedError` + `list_credit_applications`.
- **`services/deal_writeups/deal_writeup.py`:**
  - `hand_off_to_fandi` — passes `deal_writeup=writeup` to
    `record_credit_application` inside existing atomic block
    (2-line addition; docstring extended with M32.1 note +
    three-layer-defense summary).
  - New constants `DEAL_WRITEUP_STATE_PENDING`,
    `DEAL_WRITEUP_STATE_APPROVED`,
    `DEAL_WRITEUP_STATE_HANDED_OFF`, `DEAL_WRITEUP_STATES`.
  - New verb `get_deal_writeup(*, pk, dealership)` — tenant-
    scoped read; `select_related` on lead + vehicle + user
    attributions.
  - New verb `list_deal_writeups(*, dealership, state=None,
    lead=None)` — state derived from timestamp presence at
    query time; unknown `state` raises `ValueError` (endpoint
    layer maps to 400).
  - Module docstring updated to reflect five verbs (was three).
- **`services/deal_writeups/__init__.py`:** exports new
  constants + `get_deal_writeup` + `list_deal_writeups`.

### Endpoint layer

- **`views_deal_writeups.py`:**
  - Added `typing.Optional` import.
  - Extended import from `services.deal_writeups` to include
    `DEAL_WRITEUP_STATES`, `get_deal_writeup`,
    `list_deal_writeups`.
  - New view `admin_deal_writeup_list` (GET) — D1 fail-explicit
    query validation for `state` + `lead_id`; permission
    `_M113_PERMS`; projection `_project_writeup` (reused).
  - New view `admin_deal_writeup_detail` (GET, pk) — D2;
    permission `_M113_PERMS`; delegates to `get_deal_writeup`;
    404 on missing/cross-tenant.
- **`views_f_and_i.py`:**
  - Added `typing.Optional` and `django.utils.dateparse.parse_datetime`
    imports.
  - New helper `_project_writeup_context` — projects nested
    writeup context (lead + vehicle + terms + attribution +
    hand-off timestamp) from `app.deal_writeup`; returns None
    when backpointer is NULL.
  - New helper `_project_credit_application_with_writeup` —
    extends M10.1 `_project_credit_application` with
    `writeup_context` field.
  - New constant `_VALID_INTAKE_VALUES = frozenset(["true"])`
    per D3 fail-explicit `intake=false → 400` posture.
  - New view `admin_credit_application_list` (GET) — D3 fail-
    explicit query validation for `intake` (accepts only
    literal `"true"`; `false`, `1`, `TRUE`, empty → 400) +
    `lead_id` + `since`; permission `_M101_PERMS` (F&I-role-
    gated); projection includes writeup context.

### URL patterns (`urls.py`)

- `admin/deal-writeups/list/` → `admin-deal-writeup-list`
  (comment block explains `/list/` sibling path avoids touching
  M11.3 create URL).
- `admin/deal-writeups/<int:pk>/` → `admin-deal-writeup-detail`.
- `admin/credit-applications/list/` → `admin-credit-application-list`
  (comment block explains F&I-first-list-endpoint status +
  `/list/` sibling path preserves M10.1 create URL).

### Tests

- **`tests/test_m321_deal_writeup_read.py`** (30 tests):
  - `ListDealWriteupsServiceTests` (8) — no-filter returns all
    dealership-scoped; state=pending/approved/handed_off filter
    matrix (3); unknown state raises ValueError; lead filter;
    state+lead composition; ordering newest-first.
  - `GetDealWriteupServiceTests` (3) — happy path; cross-tenant
    → None; missing → None.
  - `DealWriteupListEndpointAuthTests` (6) — unauth 401/403;
    no membership 403; advisor 403; f_and_i_manager 403;
    sales_manager 200; dealer_owner 200.
  - `DealWriteupListEndpointFilterValidationTests` (9) —
    missing filter; state=pending happy; state=not-a-state 400;
    state=Pending (case-sensitive) 400; state= 400;
    lead_id=abc 400; lead_id=999999 empty; cross-tenant
    lead_id empty.
  - `DealWriteupListEndpointProjectionTests` (2) — projection
    keys; tenant-scoped.
  - `DealWriteupDetailEndpointTests` (5) — unauth; advisor 403;
    happy; missing 404; cross-tenant 404.
- **`tests/test_m321_credit_application_intake.py`** (32 tests):
  - `ProvenanceFKBehaviorTests` (7) — hand-off sets backpointer;
    direct-create leaves NULL; kwarg accepted; writeup delete
    → SET_NULL (CA survives); cross-tenant writeup → error;
    multiple writeups per lead → deterministic pairing;
    **mandatory** `test_writeup_cannot_link_to_multiple_credit_applications`
    exercising all 3 defense layers (service
    `DealWriteupAlreadyLinkedError`; DB `IntegrityError` via
    bypass-service direct ORM; M11.3
    `WriteupAlreadyHandedOffError` composed by
    `hand_off_to_fandi`).
  - `ListCreditApplicationsServiceTests` (5) — no filter
    dealership-scoped; intake=True returns pre-contract CAs;
    lead filter; cross-tenant lead raises; since filter.
  - `CreditApplicationListEndpointAuthTests` (6) — unauth;
    no membership 403; advisor 403; **sales_manager 403**
    (F&I-gated); f_and_i_manager 200; dealer_owner 200.
  - `CreditApplicationListEndpointFilterValidationTests` (9)
    — missing intake unfiltered; intake=true applies; **intake=false
    → 400** (reserved-and-rejected per §5.h); intake=TRUE 400
    (case-sensitive); intake=1 400; intake= 400;
    lead_id=abc 400; lead_id=999999 empty; since=not-a-date
    400.
  - `CreditApplicationListEndpointProjectionTests` (3) —
    direct-CA writeup_context NULL; hand-off CA has full
    writeup_context (asserts lead name + vehicle stock + all
    four-square terms); tenant-scoped.

Total M32.1 tests: **62**.

## 8. Push status

**No push at SESSION_207 close.** M32.1 is pure implementation
per the standard M28.1 / M29.1 / M30.1 / M31.1 cadence.
Coordinated M32 close push deferred to explicit user
confirmation after M32.3 close.

Local commits at SESSION_207 close:

- SESSION_207 M32.1 substrate + this handoff +
  `00-START-NEXT-SESSION.md` flip land in a single local-only
  commit per implementation-session cadence; hash backfill
  via a subsequent commit.

Expected M32 commit count at coordinated push: **6–8**
(M32.0 planning + M32.0 hash-backfill + M32.1 backend + M32.1
hash-backfill + M32.2 UI + M32.2 hash-backfill + M32.3 F&I UI
+ close-out fold, plus hash-backfill follow-ups per convention).

## 9. Next session priorities

`00-START-NEXT-SESSION.md` overwritten for **SESSION_208 ·
Milestone 32 · Increment 2 (M32.2 — sales-manager UI + sales-
side Playwright)**. First-thing sequence per M28.2 / M29.2 /
M30.2 / M31.2 pattern:

1. **Verify starting state** (git; backend 4,995 pass; frontend
   319 pass; checks; migrations; tsc; redis;
   `db.acceptance.sqlite3` proactive reset).
2. **Confirm working from M32.0 planning memo** — read
   `docs/roadmap/MILESTONE_32_PLANNING.md` §5.b D4-revised² +
   D5 + D6 + D7 + §5.e M32.2 before touching frontend code.
3. **Ship M32.2 sales-manager UI** per §5.e:
   - Frontend wrappers in `salesApi.ts` (5 new) + remove
     `salesApi.ts:10-25` "UI deferred" comments.
   - New Writeups tab on `LeadDetailModal` (manager-only by
     transitivity per D4-revised²).
   - Inline components co-located per M28.0
     `feedback_duplicate_small_stable_logic` lesson:
     `DealWriteupForm`, `WriteupApproveConfirmDialog`
     (D5-revised copy), `WriteupHandoffConfirmDialog`
     (D6 irreversibility copy).
   - State visual signals per D7 (Badge + row aria-label +
     testids).
   - ~34 Vitest tests.
4. **Playwright:** new spec `sales_to_fandi_handoff.spec.ts`
   with `test.describe("sales-manager-writeup-handoff", …)` —
   sales-side only in M32.2, uses existing `sales_manager`
   persona; six-step journey per §5.e M32.2.
5. **Verify M32.2 close baselines:** frontend 319 → ~353;
   acceptance 22 → 23 journeys; `tsc --noEmit` clean;
   `git grep "UI deferred" frontend/` empty.
6. **DoD satisfied directly** — no exception.
7. **Ship the M32.2 handoff at
   `docs/handoffs/SESSION_208_m32_inc2_sales_ui.md`.**
   **Do NOT push** — coordinated push at M32 close.

## 10. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_32_PLANNING.md`** (governing
   contract for M32; §5.b D4-revised² + D5 + D6 + D7 + §5.e
   M32.2 for the next increment)
6. `docs/handoffs/SESSION_206_m32_inc0_planning.md` (M32.0
   close-out)
7. **This handoff** (`SESSION_207_m32_inc1_backend.md`)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (post-M32.1
   baseline — 161 endpoints / 124 covered / 37 backend-only /
   321 service verbs)
9. `docs/roadmap/MILESTONE_11_PLANNING.md` §7 M11.3 (M11.3
   DealWriteup entity origin)
10. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs M32.2 co-located inline-dialog
    choice)
11. Memory record
    `feedback_verify_fk_discoverability_before_lock.md` (M27.0
    origin — verified at M32.0 §4.5; resolved by M32.1 D1 + D2)

Narrative docs are claims. Rules + research + code + regenerated
artifact are facts.
