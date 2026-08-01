---
state: active
date: 2026-07-31
last_session_shipped: SESSION_055
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: planning
next_session: SESSION_056
next_milestone: 3
next_milestone_name: "Structured condition report"
next_increment: 1
next_increment_name: "M3.1 — Core condition-report models"
---

# Next session — SESSION_056 · Milestone 3 · Increment 1 (M3.1 — Core condition-report models)

> **Milestone 3 planning shipped at SESSION_055.**
> `docs/roadmap/MILESTONE_3_PLANNING.md` is the acceptance
> contract for the whole milestone (design memo §1,
> migration-impact review §2, compatibility checklist §3,
> reusable-primitives review §4, scope-discipline table §5,
> anchors §6, eight-increment sequence §7). The
> **load-bearing multi-photo storage decision is Option A**:
> storage abstraction ships as M3.4 before
> `ConditionFindingPhoto` (M3.5); see planning §5.a for the
> full three-option analysis.
>
> **SESSION_056 opens implementation with M3.1 = the
> persistence layer for structured condition reports.** No
> service module, no API, no frontend, no storage story — just
> the models + migration + admin + tenancy-carrier
> registration + focused schema/cross-tenant tests. Mirrors
> the shape M2.1 (SESSION_046) shipped.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3 —
   scope boundary (in-scope / out-of-scope enumeration).
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every
   ConditionReport / ConditionFinding /
   ConditionFindingPhoto row inherits the tenancy +
   authorization substrate; M3.1 must NOT re-derive these
   decisions.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — the acceptance
   contract for the whole milestone. §1.1 / §1.2 / §1.5 lock
   the field shapes. §3 lock the compatibility invariants.
   §7 M3.1 entry locks the sub-scope this session ships.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 — the
   eleven lessons inherit unchanged (increment discipline;
   focused positive/negative test matrices; immutable rows;
   documentation discipline).
7. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b M2.1 entry +
   §3 (annotated variant) — the shape M3.1 mirrors.
8. `docs/research/RECON_MAPPING.md` §2 (condition
   assessment) — the business-truth source for category /
   severity / photo / provenance decisions the model layer
   encodes.
9. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 2 — the
   architectural target and the load-bearing "AI role: NONE
   yet" rule.

## What M3.1 delivers (per `MILESTONE_3_PLANNING.md` §7 M3.1)

The persistence layer for structured condition reports.

**In scope:**

- `ConditionReport` model (many-per-Vehicle; `authored_by` FK
  nullable SET_NULL; `inspector_name` required CharField;
  `inspected_at` DateTimeField; `mileage_at_inspection`
  PositiveIntegerField; `status` choices `draft` / `complete`
  default `draft`; `completed_at` nullable DateTimeField;
  `notes` TextField blank; `dealership` FK NOT NULL;
  timestamps).
- `ConditionFinding` model (FK to `ConditionReport`;
  `dealership` FK NOT NULL; `category` twelve choices;
  `severity` four choices; `description` TextField required;
  `estimated_cost` Decimal `max_digits=10, decimal_places=2`
  nullable; `notes` TextField blank; timestamps).
- `ConditionFindingPhoto` model (FK to `ConditionFinding`;
  `dealership` FK NOT NULL; `storage_key` CharField unique;
  `content_type` CharField four-value whitelist; `size_bytes`
  PositiveIntegerField; `caption` CharField blank;
  `uploaded_by` FK nullable SET_NULL; `created_at`).
- Migration `0015` (verify the next sequential number via
  `showmigrations` at session start; M2 ended at `0014`).
- Admin registrations for all three models mirroring the
  `VehicleAcquisitionAdmin` / `VehicleCostAdmin` pattern.
- Four module-level enum constants:
  - `CONDITION_CATEGORY_CHOICES` (twelve values:
    `mechanical`, `cosmetic`, `body`, `glass`, `tires`,
    `interior`, `fluids`, `electrical`, `safety`,
    `accessories`, `missing`, `other`).
  - `CONDITION_SEVERITY_CHOICES` (four values in escalation
    order: `advisory`, `recommended`, `required`, `safety`).
  - `CONDITION_REPORT_STATUS_CHOICES` (two values:
    `draft`, `complete`).
  - `CONDITION_PHOTO_CONTENT_TYPE_CHOICES` (four values:
    `image/jpeg`, `image/png`, `image/heic`, `image/webp`).
- Cross-tenant model `clean()` guards on all three models
  (same shape as `VehicleAcquisition.clean` /
  `VehicleCost.clean` at
  `backend/dealer_ai/models.py:758` + `1007`).
- `ConditionReport.clean()` additionally enforces
  `completed_at` NULL exactly when `status="draft"`; set
  exactly when `status="complete"`.
- `services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES` extended
  from six carriers to nine (three new: `ConditionReport`,
  `ConditionFinding`, `ConditionFindingPhoto`).
- `DATABASES["migration_check"]` alias verified against the
  new migration (per M1 lesson 2 + M2.1 precedent).
- ~40 focused model tests (schema NOT NULL, choices
  validation, enum vocabulary counts, cascade behavior,
  cross-tenant guards, `_TENANT_CARRIER_MODEL_NAMES`
  extension, photo whitelist, `completed_at` invariant).

**Explicitly out of scope (deferred to specific later
increments):**

- ❌ Service module (`services/condition_report.py`) — M3.2.
- ❌ Vehicle read-model `@property` methods — M3.3.
- ❌ Storage abstraction (`django-storages`, presigned URLs)
  — M3.4.
- ❌ Upload flow (`request_photo_upload`, `attach_photo`,
  `delete_photo` service functions) — M3.5.
- ❌ API endpoints — M3.6.
- ❌ Frontend — M3.7.
- ❌ AI role of any kind — never in M3 (load-bearing
  invariant per VCP §Phase 2).

## What SESSION_056 should do

### Recommended step sequence

1. **Read first (in this order — one pass, do not skim):**
   - `docs/roadmap/MILESTONE_3_PLANNING.md` — the whole
     planning artifact drafted at SESSION_055. Especially
     §0 practices, §1.1 `ConditionReport` fields, §1.2
     `ConditionFinding` fields + category/severity enums,
     §1.5 `ConditionFindingPhoto` fields, §2 migration
     impact (rows 1, 2, 7 apply to this session), §3
     M3-invariants checklist rows M3.1 must satisfy at
     close, §7 M3.1 detail.
   - `backend/dealer_ai/models.py` — reread
     `VehicleAcquisition` (lines 685–787) + `VehicleCost`
     (lines 925–1028) as the persistence-layer template
     M3.1 mirrors, especially the `clean()` cross-tenant
     guards.
   - `backend/dealer_ai/services/tenancy.py` — the
     `_TENANT_CARRIER_MODEL_NAMES` tuple (line 260) + the
     `register_default_dealership_autofill` function
     (line 334) M3.1 extends.
   - `backend/dealer_ai/tests/test_vehicle_acquisition.py`
     + `test_vehicle_cost.py` (SESSION_046 shape) — the
     test-file shape M3.1 mirrors.
   - `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b M2.1 entry
     — the "core ledger models" increment shape.
   - `docs/handoffs/SESSION_055_milestone_3_planning.md` —
     the storage decision + increment sequence.

2. **Verify starting state.**
   - `git status` — clean (or only the pre-existing
     `Dealer OS/` untracked dir).
   - `python3 manage.py test dealer_ai` → 1,753 pass.
   - `python3 manage.py showmigrations dealer_ai` →
     migrations current through `0014`.
   - `python3 manage.py makemigrations dealer_ai --check
     --dry-run` → "No changes detected."

3. **Author models.** Add the three model classes to
   `backend/dealer_ai/models.py` alongside the M2 models
   (append after `class VehicleCost` per file convention).
   Add the four enum constants as module-level constants
   above the model class definitions (mirroring the
   `ROLE_CHOICES` and `VEHICLE_COST_CATEGORY_CHOICES`
   pattern).

4. **Extend tenancy.** In
   `backend/dealer_ai/services/tenancy.py`, add the three
   new model names to `_TENANT_CARRIER_MODEL_NAMES`. Verify
   the extension by running the existing
   `test_dealership.WritePathFallback.*` tests, then adding
   focused tests that instantiate each new model without
   an explicit `dealership=` and confirm the default is
   attached.

5. **Author migration.** `python3 manage.py makemigrations
   dealer_ai --name condition_report`. Inspect the
   generated migration for any surprises (photo whitelist
   `choices=` should appear; cross-tenant `clean()` guards
   don't produce schema — they're pure Python).

6. **Register admin.** In `backend/dealer_ai/admin.py`,
   add `ConditionReportAdmin`, `ConditionFindingAdmin`,
   `ConditionFindingPhotoAdmin` mirroring the
   `VehicleAcquisitionAdmin` / `VehicleCostAdmin` shape
   (list_display, list_filter, search_fields,
   readonly_fields for timestamps).

7. **Write focused tests.** Three new test files:
   `test_condition_report.py`, `test_condition_finding.py`,
   `test_condition_finding_photo.py`. Coverage per the
   test surface in `MILESTONE_3_PLANNING.md` §7 M3.1 (see
   also SESSION_055 handoff § "Test surface").

8. **Migration-check.** Verify against
   `DATABASES["migration_check"]` (per M1 lesson 2):
   `python3 manage.py migrate dealer_ai zero
   --database=migration_check && python3 manage.py migrate
   dealer_ai --database=migration_check`. Confirms the
   forward path works from a clean slate.

9. **Full suite + baseline.**
   `python3 manage.py test dealer_ai` should produce
   ~1,793 pass (1,753 + ~40 new), 1 skipped, 0 fail.
   `python3 manage.py makemigrations --check --dry-run`
   still reports "No changes detected."

10. **Close SESSION_056 with:**
    - Model code + migration `0015` + admin registrations
      + focused tests committed.
    - Handoff at
      `docs/handoffs/SESSION_056_m3_inc1_core_models.md`
      (or similar slug).
    - Overwrite this file (`00-START-NEXT-SESSION.md`)
      with the SESSION_057 = M3.2 (service layer) priority.
    - `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.1 entry
      annotated in-place with `SHIPPED at SESSION_056`
      + the shipped-surface manifest (mirroring how M2.1
      annotated the M2 planning §7.b).

## Explicit non-goals for SESSION_056

- ❌ Do NOT write `services/condition_report.py` — that is
  M3.2 (SESSION_057).
- ❌ Do NOT add `@property` methods on `Vehicle` — that is
  M3.3 (SESSION_058).
- ❌ Do NOT add `django-storages` to `requirements.txt` —
  that is M3.4 (SESSION_059).
- ❌ Do NOT write any API endpoint — that is M3.6
  (SESSION_061).
- ❌ Do NOT modify any existing model, service, view, or
  frontend file (this includes `Vehicle`,
  `services/vehicle_ledger.py`, M2.6 ledger endpoints,
  M2.7 `VehicleLedgerPage.tsx`).
- ❌ Do NOT modify `dealer_ai/permissions.py`.
- ❌ Do NOT modify `services/tenancy.py::get_current_dealership`
  or `get_active_membership` signatures — the only edit is
  extending `_TENANT_CARRIER_MODEL_NAMES`.
- ❌ Do NOT modify `services/llm_safety.py` or any pre/post-
  LLM guard.
- ❌ Do NOT introduce any AI role — M3 is deliberately
  AI-free per VCP §Phase 2.
- ❌ Do NOT reopen the M2 semantic contracts.
- ❌ Do NOT commit any real `OPENAI_API_KEY` or credentials.

## NEXT TASK

Start SESSION_056 with the read-first list above. Ship
`ConditionReport` + `ConditionFinding` + `ConditionFindingPhoto`
models + migration `0015` + admin + tenancy-carrier
registration + ~40 focused model tests. Do NOT ship the
service layer, storage story, API, or UI — those are M3.2
through M3.7.

Test baseline at SESSION_056 close: 1,753 → ~1,793.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — the acceptance
   contract for the whole milestone.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 (lessons)
7. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b M2.1 (shape
   template)
8. `docs/research/RECON_MAPPING.md` §2 +
   `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 2
9. `docs/CAPABILITY_MATRIX.md`
10. Most recent handoffs
    (`SESSION_055_milestone_3_planning.md`,
    `SESSION_054_milestone_2_closeout.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_055 — Milestone 3 planning shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0014` applied. Default `Dealership` row exists
  (`slug='default'`). No pending migrations. Test baseline:
  **1,753 pass**, 1 skipped, 0 fail.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 3 does not require prod (recon sign-off
  happens at the store per RECON §12.2; field-based operator
  sessions land with M4 vendor emails or later).
- **Frontend (local):** Vite on `:5173`. Auth flow wired
  end-to-end. Operator ledger page at
  `/dealer-ai-inventory/:stock/ledger` shipped M2.7. Route
  `/dealer-ai-inventory/:stock/condition-report` will land
  M3.7.
- **Frontend (prod):** NONE.
- **Frontend build:** `npx tsc --noEmit` clean; `npx vite
  build` clean (pre-existing 524KB chunk-size warning,
  unchanged).
- **DRF defaults + CSRF + endpoint-level permissions:** all
  as documented in `AUTHENTICATION_MODEL.md`. Unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR`. M3.4 will add optional
  `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`,
  `AWS_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_S3_CUSTOM_DOMAIN` (all
  optional; unset = local `FileSystemStorage` fall-through).
- **Dev DB seeded users:** `smoke_owner` (dealer_owner) +
  `smoke_advisor` (advisor). Password `smoke-pass-4e`. Not
  committed to source.
- **Milestone 2 shipped surface (locked, do not touch):**
  see `docs/CAPABILITY_MATRIX.md` §7c for the enumerated
  ledger surface (models, migrations, service, read model,
  financial engine, APR config, accrual command, safety
  scrub, admin API, operator UI).
- **Milestone 3 shipped surface (in-progress; M3.0 planning
  landed this session):** `docs/roadmap/MILESTONE_3_PLANNING.md`.
  M3.1 through M3.8 queued for SESSION_056 through
  SESSION_063.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Every deferred idea from Milestones 1 + 2 + M3
  planning is recorded in the respective planning +
  retrospective + handoff docs. If an M3 session surfaces a
  deferral that does not fit any existing planning doc,
  create the file at that moment.
