---
state: active
date: 2026-07-31
last_session_shipped: SESSION_056
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: in-progress
next_session: SESSION_057
next_milestone: 3
next_milestone_name: "Structured condition report"
next_increment: 2
next_increment_name: "M3.2 — Condition-report service layer"
---

# Next session — SESSION_057 · Milestone 3 · Increment 2 (M3.2 — Condition-report service layer)

> **Milestone 3 · Increment 1 (M3.1) shipped at SESSION_056.**
> The persistence layer for structured condition reports —
> `ConditionReport` + `ConditionFinding` + `ConditionFindingPhoto`
> models + migration `0015` + admin + tenancy-carrier
> registration (6 → 9) + 60 focused tests — is live. See
> `docs/handoffs/SESSION_056_m3_inc1_core_models.md` for the
> full shipped-surface manifest and the reviewed planning-doc
> refinement (UUID public identity added to
> `ConditionFindingPhoto`; §1.5 + §3 amended narrowly).
>
> **SESSION_057 opens M3.2 = the service layer that lets
> callers create reports, add findings, and complete reports
> — one authoritative write path per operation, every function
> threads `dealership=` explicitly, fail-closed cross-tenant
> guards at entry.** No API. No frontend. No storage. No AI.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3 —
   scope boundary (in-scope / out-of-scope enumeration).
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every
   condition-report service function inherits the tenancy +
   authorization substrate; M3.2 must NOT re-derive these
   decisions.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — the acceptance
   contract for the whole milestone. §1.1 / §1.2 / §1.5 lock
   the field shapes (annotated at SESSION_056 with the
   M3.1 SHIPPED manifest). §3 locks the compatibility
   invariants. §7 M3.2 entry locks the sub-scope this
   session ships.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 — the
   eleven lessons inherit unchanged. Lesson 4 (`full_clean()`
   before save on every service write) and lesson 5
   (immutability once committed) are load-bearing for M3.2.
7. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b M2.2 entry —
   the shape M3.2 mirrors (extracted service module with
   fail-closed cross-tenant guard).
8. `docs/research/RECON_MAPPING.md` §2 (condition assessment)
   + §3.1 (three-tier planning framework) — the business-truth
   source for the "complete report is immutable" and
   "estimated_cost is documentation only" invariants the
   service layer encodes.
9. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 2 — the
   architectural target and the load-bearing "AI role: NONE
   yet" rule.

## What M3.2 delivers (per `MILESTONE_3_PLANNING.md` §7 M3.2)

The service layer that owns the one authoritative write path
per condition-report operation.

**In scope:**

- New module `backend/dealer_ai/services/condition_report.py`
  exporting:
  - `create_report(vehicle, *, dealership, authored_by,
    inspector_name, inspected_at, mileage_at_inspection,
    notes="") -> ConditionReport` — always creates in
    `status="draft"`.
  - `complete_report(report) -> ConditionReport` — one-way
    transition draft → complete; sets `completed_at`
    atomically; raises on `complete → *`.
  - `add_finding(report, *, category, severity, description,
    estimated_cost=None, notes="") -> ConditionFinding` —
    refuses when `report.status == "complete"`.
  - `update_finding(finding, **kwargs) -> ConditionFinding`
    — refuses when parent report is complete.
  - `delete_finding(finding) -> None` — refuses when parent
    report is complete.
  - `latest_condition_report(vehicle, *, dealership) ->
    Optional[ConditionReport]` — deterministic ordering.
  - `latest_completed_condition_report(vehicle, *,
    dealership) -> Optional[ConditionReport]` — filter to
    `status="complete"`.
  - `CrossTenantConditionReportError(ValueError)` —
    fail-closed guard shape identical to
    `CrossTenantLedgerError`.
- Every function calls `full_clean()` before save (M2
  retrospective §6 lesson 4).
- Every function raises `CrossTenantConditionReportError` at
  entry when `dealership=` does not match
  `vehicle.dealership` or `report.dealership`.
- ~50 focused service tests covering: create semantics
  (always draft, explicit `dealership=` required), complete
  transition (one-way, raises on double-complete), finding
  CRUD gated by report status (add / update / delete refuse
  once report is complete), cross-tenant guards on all
  seven functions, deterministic ordering for `latest_*`
  accessors, `full_clean()` fires before save on every
  write path.

**Explicitly out of scope (deferred to specific later
increments):**

- ❌ Vehicle read-model `@property` methods — M3.3.
- ❌ Storage abstraction (`django-storages`, presigned URLs)
  — M3.4.
- ❌ Upload flow (`request_photo_upload`, `attach_photo`,
  `delete_photo`) — M3.5. **No photo service functions
  ship in M3.2** — the storage backend they depend on
  doesn't exist yet.
- ❌ API endpoints — M3.6.
- ❌ Frontend — M3.7.
- ❌ Any modification to M3.1 model shape unless a test
  reveals a real defect (raise as a scope question first,
  do not silently patch).
- ❌ AI role of any kind — never in M3 (VCP §Phase 2).

## What SESSION_057 should do

### Recommended step sequence

1. **Read first (in this order — one pass, do not skim):**
   - `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.2 detail
     + §3 business-layer invariants (rows on
     `CrossTenantConditionReportError`, `complete_report`
     transition rules, `add_finding` / `update_finding` /
     `delete_finding` gating).
   - `docs/handoffs/SESSION_056_m3_inc1_core_models.md` —
     the shipped-surface manifest + the planning-doc
     refinement rationale.
   - `backend/dealer_ai/services/vehicle_ledger.py` — the
     M2.2 service pattern M3.2 mirrors. Especially:
     `CrossTenantLedgerError` shape, `full_clean()` call
     ordering, explicit-`dealership=` kwarg discipline,
     idempotent-safe write path.
   - `backend/dealer_ai/tests/test_vehicle_ledger.py` (full)
     — the service-tests shape M3.2 mirrors.
   - `backend/dealer_ai/models.py` M3.1 additions
     (`ConditionReport`, `ConditionFinding`,
     `ConditionFindingPhoto`) + module-level enum constants
     — the persistence surface M3.2 sits on top of.

2. **Verify starting state.**
   - `git status` — clean (or only the pre-existing
     `Dealer OS/` untracked dir).
   - `python3 manage.py test dealer_ai` → **1,813 pass, 1
     skipped, 0 fail**.
   - `python3 manage.py showmigrations dealer_ai` →
     migrations current through `0015_condition_report`.
   - `python3 manage.py makemigrations dealer_ai --check
     --dry-run` → "No changes detected."

3. **Author service module.** Create
   `backend/dealer_ai/services/condition_report.py`. Import
   the models + enum constants from `dealer_ai.models`.
   Define `CrossTenantConditionReportError(ValueError)` at
   the top of the module. Author the seven functions in the
   order listed in §7 M3.2, one at a time, testing each
   before writing the next (M2.2 shipped this way — the
   discipline caught two design errors that would have
   compounded).

4. **No migration.** M3.2 is pure Python. Confirm by
   running `python3 manage.py makemigrations dealer_ai
   --check --dry-run` at end of session — must still report
   "No changes detected."

5. **Write focused tests.** New file
   `backend/dealer_ai/tests/test_condition_report_service.py`
   covering the seven functions plus the cross-tenant error
   plus the `full_clean()` before-save invariant. Target
   ~50 tests.

6. **Full suite + baseline.**
   `python3 manage.py test dealer_ai` should produce
   ~1,863 pass (1,813 + ~50 new), 1 skipped, 0 fail.

7. **Close SESSION_057 with:**
   - Service module + focused tests committed.
   - Handoff at
     `docs/handoffs/SESSION_057_m3_inc2_service_layer.md`.
   - Overwrite this file (`00-START-NEXT-SESSION.md`) with
     the SESSION_058 = M3.3 (Vehicle read-model
     `@property` accessors) priority.
   - `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.2 entry
     annotated in-place with `SHIPPED at SESSION_057` +
     the shipped-surface manifest.

## Explicit non-goals for SESSION_057

- ❌ Do NOT modify any M3.1 model, enum constant, migration,
  or admin registration. If a service test surfaces a
  genuine model defect, raise as a scope question first —
  do not silently patch.
- ❌ Do NOT ship any photo-related service function
  (`request_photo_upload`, `attach_photo`, `delete_photo`).
  Those depend on the M3.4 storage abstraction that hasn't
  been built yet.
- ❌ Do NOT add `@property` methods on `Vehicle` — that is
  M3.3 (SESSION_058).
- ❌ Do NOT add `django-storages` to `requirements.txt` —
  that is M3.4 (SESSION_059).
- ❌ Do NOT write any API endpoint — M3.6.
- ❌ Do NOT touch `services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`
  — it was extended in M3.1 and is final for M3.
- ❌ Do NOT modify `services/vehicle_ledger.py`,
  `services/llm_safety.py`, or any pre / post-LLM guard.
- ❌ Do NOT reopen M2 semantic contracts.
- ❌ Do NOT introduce any AI role — M3 is deliberately
  AI-free per VCP §Phase 2.
- ❌ Do NOT commit any real `OPENAI_API_KEY` or credentials.

## NEXT TASK

Start SESSION_057 with the read-first list above. Ship
`services/condition_report.py` with the seven exported
functions + `CrossTenantConditionReportError` + ~50 focused
service tests. Do NOT ship the Vehicle read-model, storage
story, photo service, API, or UI — those are M3.3 through
M3.7.

Test baseline at SESSION_057 close: 1,813 → ~1,863.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — the acceptance
   contract; §7 M3.1 now annotated SHIPPED at SESSION_056;
   §7 M3.2 is the sub-scope this session ships.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 (lessons)
7. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b M2.2 (shape
   template for extracted service modules)
8. `docs/research/RECON_MAPPING.md` §2 + §3.1 +
   `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 2
9. `docs/CAPABILITY_MATRIX.md`
10. Most recent handoffs
    (`SESSION_056_m3_inc1_core_models.md`,
    `SESSION_055_milestone_3_planning.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_056 — M3.1 core models shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015` applied. Default `Dealership` row exists
  (`slug='default'`). No pending migrations. Test baseline:
  **1,813 pass**, 1 skipped, 0 fail.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 3 does not require prod (recon sign-off
  happens at the store per RECON §12.2).
- **Frontend (local):** Vite on `:5173`. Auth flow wired
  end-to-end. Operator ledger page at
  `/dealer-ai-inventory/:stock/ledger` shipped M2.7. Route
  `/dealer-ai-inventory/:stock/condition-report` will land
  M3.7.
- **Frontend (prod):** NONE.
- **Frontend build:** unchanged this session (no frontend
  edits). `npx tsc --noEmit` clean; `npx vite build` clean.
- **DRF defaults + CSRF + endpoint-level permissions:** all
  unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
  Reset + re-applied clean this session; forward path from
  empty schema through `0015_condition_report` verified.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR`. M3.4 will add optional
  `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`,
  `AWS_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_S3_CUSTOM_DOMAIN`.
- **Dev DB seeded users:** `smoke_owner` (dealer_owner) +
  `smoke_advisor` (advisor). Unchanged.
- **Milestone 2 shipped surface (locked, do not touch):**
  see `docs/CAPABILITY_MATRIX.md` §7c.
- **Milestone 3 shipped surface (in-progress):** M3.0
  planning (SESSION_055) + M3.1 core models (SESSION_056 —
  this session). M3.2 through M3.8 queued for SESSION_057
  through SESSION_063.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Every deferred idea from Milestones 1 + 2 + M3
  planning + M3.1 is recorded in the respective planning +
  retrospective + handoff docs.
