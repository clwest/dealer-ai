---
state: active
date: 2026-08-01
last_session_shipped: SESSION_070
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: in-progress
next_session: SESSION_071
next_milestone: 4
next_milestone_name: "Recon automation"
next_increment: 6
next_increment_name: "M4.6 — Admin API + permission matrix"
---

# Next session — SESSION_071 · Milestone 4 · Increment 6 (M4.6 — admin API + permission matrix)

> **Milestone 4 · Increment 5 shipped at SESSION_070.**
> New `services/vendor_comm.py` (4 functions) +
> `_scrub_invented_recon_fact` extension to
> `services/llm_safety.py`. 62 focused tests (29 scrub +
> 33 service). Backend baseline **2,367 → 2,429 pass**, 1
> skipped, 0 fail. Zero real LLM API access
> (MockLLMProvider throughout). No SMTP / SMS wiring.
>
> **SESSION_071 opens M4.6 — the admin API + permission
> matrix.** New DRF endpoints under
> `/api/dealer-ai/admin/vehicles/<stock>/` and
> `/api/dealer-ai/admin/vendors/` per planning §7 M4.6.
> New permission class
> `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
> per §5.f. Domain-error mapping to 409 / 404. Endpoints
> delegate entirely to `services/recon.py` +
> `services/vendor_comm.py`.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md` §8b — every
   endpoint threads `dealership=` explicitly.
5. `docs/roadmap/MILESTONE_4_PLANNING.md`:
   - §5.f — role permission matrix (per-endpoint role
     access table).
   - §7 M4.6 — endpoint list (Vendor CRUD, recon
     dashboard, ReconDecision, WorkOrder create/approve/
     start/complete/cancel/patch, findings attach/detach,
     parts CRUD/transition, comm draft/approve/mark-sent/
     log).
6. `docs/handoffs/SESSION_070_m4_inc5_vendor_comm.md` —
   this session's authoritative closeout + "Recommended
   exact scope for SESSION_071".
7. Prior handoffs (066, 067, 068, 069).
8. `backend/dealer_ai/permissions.py` — existing role
   classes; M4.6 composes an additive new class.
9. `backend/dealer_ai/views.py` — M2.6 ledger + M3.6
   condition-report admin endpoint patterns M4.6 mirrors.
10. `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.6A/B —
    the exact shape M4.6 mirrors most closely.

## What M4.6 delivers

**Admin API + permission class only.** No new service
modules. No new domain errors. No migrations. No frontend
(that's M4.7).

### The new permission class

`IsReconManagerSalesManagerOrOwnerAtActiveDealership`
in `backend/dealer_ai/permissions.py`. Composed from
existing `ROLE_RECON_MANAGER` + `ROLE_SALES_MANAGER` +
`ROLE_DEALER_OWNER` (all shipped M1 · 4A). Follows the
existing composition pattern in
`IsSalesManagerOrOwnerAtActiveDealership`.

Per-endpoint matrix locked at §5.f. Every M4.6 admin
endpoint composes this new class. Advisor / porter /
f_and_i_manager / collections get 403.

### Endpoint list (per §7 M4.6)

Under `/api/dealer-ai/admin/`:

- **Vendor CRUD** — list / create / detail / patch. No
  delete surface (PROTECT contract from §5.b; deactivate
  via `is_active=False` patch).
- **GET vehicles/<stock>/recon/** — recon dashboard:
  latest completed condition report + decisions + WOs +
  parts + comms.
- **POST vehicles/<stock>/findings/<id>/recon-decision/**
  — record decision.
- **POST vehicles/<stock>/work-orders/** — create draft.
- **POST work-orders/<wo_id>/approve/** — approve.
- **POST work-orders/<wo_id>/start/** — start.
- **POST work-orders/<wo_id>/complete/** — complete.
- **POST work-orders/<wo_id>/cancel/** — cancel.
- **PATCH work-orders/<wo_id>/** — edit whitelisted
  fields + revise-estimate re-ledger flow.
- **POST work-orders/<wo_id>/findings/** — attach
  findings.
- **DELETE work-orders/<wo_id>/findings/<fid>/** —
  detach finding.
- **POST work-orders/<wo_id>/parts/** — add part.
- **PATCH parts/<part_id>/** — update part / transition
  status.
- **DELETE parts/<part_id>/** — delete (draft-only).
- **POST work-orders/<wo_id>/comms/draft/** — draft comm.
- **POST comms/<comm_id>/approve/** — approve.
- **POST comms/<comm_id>/mark-sent/** — mark sent.
- **POST comms/log/** — log off-system comm.

### Domain-error mapping

- `CrossTenantReconError` / `CrossTenantVendorCommError`
  → 404 (never leak whether the resource exists across
  tenants).
- `ReconImmutableError` / `VendorCommImmutableError` →
  409 Conflict.
- `InvalidReconTransitionError` → 409.
- `IncompleteConditionReportError` → 409.
- `ReconFactScrubDroppedError` → 422 (unprocessable —
  the operator should review and retry).
- `EmptyDraftError` → 502 Bad Gateway (LLM upstream
  returned nothing).
- `ValueError` (invalid vocabulary / structural) → 400.

### Provenance surfaces

Comm serializer response includes `source_provenance`
(the source_bundle + scrubs_fired + llm_provider) so the
M4.7 UI can render "here's what the AI had to work from"
alongside the draft.

## What SESSION_071 should do

### Recommended step sequence

1. **Read first (in order):**
   - `docs/roadmap/MILESTONE_4_PLANNING.md` §5.f + §7 M4.6.
   - `docs/handoffs/SESSION_070_m4_inc5_vendor_comm.md`
     — the scope block above.
   - `backend/dealer_ai/permissions.py` — the existing
     `IsSalesManagerOrOwnerAtActiveDealership` composition
     pattern M4.6 mirrors.
   - `backend/dealer_ai/views.py` — M2.6 admin ledger
     endpoints (`admin_vehicle_ledger`, etc.) and M3.6
     condition-report endpoints. Note the tenant-scoping
     + cross-tenant-fail-closed pattern.
   - `backend/dealer_ai/urls.py` — route registration
     pattern.
   - `backend/dealer_ai/services/recon.py` +
     `services/vendor_comm.py` — the service surfaces
     M4.6 delegates to.
   - `backend/dealer_ai/tests/test_admin_endpoints.py` +
     `test_admin_endpoints_auth.py` — the M2.6 test shape
     M4.6 mirrors.

2. **Verify starting state.**
   - `git status` clean (or only pre-existing untracked).
   - `python3 manage.py test dealer_ai` → **2,429 pass, 1
     skipped, 0 fail**.
   - `python3 manage.py check` clean.
   - `python3 manage.py makemigrations --check --dry-run`
     → "No changes detected."

3. **Add the permission class** to
   `dealer_ai/permissions.py`. Follow the composition
   pattern of the existing sales_manager/owner class.

4. **Add endpoint views** to `dealer_ai/views.py` (or a
   new `views_recon.py` if the file is getting large —
   check current size first; M3.6 stayed in views.py).

5. **Register routes** in `dealer_ai/urls.py`.

6. **Write ~90 focused endpoint tests** in
   `backend/dealer_ai/tests/test_admin_recon_endpoints.py`
   (or split by resource — vendor / recon / work-order /
   parts / comms — if the single-file version gets
   unwieldy).

7. **Full-suite verification.** Target 2,429 → ~2,519 pass.

8. **Ship handoff at
   `docs/handoffs/SESSION_071_m4_inc6_admin_api.md`**
   mirroring the previous handoff shape.

9. **Overwrite `00-START-NEXT-SESSION.md`** with M4.7
   priority (frontend operator UI).

## Explicit non-goals for SESSION_071

- ❌ Do NOT add any new service module. Delegate
  entirely to `services/recon.py` +
  `services/vendor_comm.py`.
- ❌ Do NOT modify M4.1 – M4.5 substrate.
- ❌ Do NOT add outbound SMTP / SMS send. Planning §5.i
  deferred.
- ❌ Do NOT add any new domain errors — use the ones the
  services already expose.
- ❌ Do NOT touch frontend — M4.7.
- ❌ Do NOT add real LLM API calls in tests.
  MockLLMProvider only.
- ❌ Do NOT add QC verification fields / endpoints
  (§1.0.QC-GAP annotation defers to a future increment).
- ❌ Do NOT introduce any new migration.

## NEXT TASK

Start SESSION_071 with the read-first list above. Add the
new permission class + admin endpoints + URL routes. Write
~90 focused endpoint tests covering the permission matrix
+ business flows + domain-error mapping + cross-tenant
fail-closed 404s. Target baseline 2,429 → ~2,519. Ship the
M4.6 handoff.

Backend baseline at SESSION_071 close: **~2,519 pass**.
Frontend baseline: unchanged.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_4_PLANNING.md` (SESSION_066 +
   SESSION_067 + SESSION_068 amendments; §5.f + §7 M4.6
   anchor M4.6)
6. `docs/handoffs/SESSION_070_m4_inc5_vendor_comm.md`
7. Prior M4 handoffs (066, 067, 068, 069)
8. `docs/handoffs/SESSION_065_m4_planning.md`
9. `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.6A/B (the
   endpoint shape M4.6 mirrors most closely)
10. `docs/CAPABILITY_MATRIX.md` §7c + §7d
11. Most recent handoffs
    (`SESSION_070_m4_inc5_vendor_comm.md`,
    `SESSION_069_m4_inc4_parts.md`,
    `SESSION_068_m4_inc3_ledger.md`,
    `SESSION_067_m4_inc2_service_state_machine.md`,
    `SESSION_066_m4_inc1_core_models.md`,
    `SESSION_065_m4_planning.md`,
    `SESSION_064_m3_inc8_closeout.md`,
    `SESSION_063_m3_inc7_operator_ui.md`,
    `SESSION_062_m3_inc6b_photo_api.md`,
    `SESSION_061_m3_inc6a_admin_api.md`,
    `SESSION_060_m3_inc5_upload_flow.md`,
    `SESSION_059_m3_inc4_storage.md`,
    `SESSION_058_m3_inc3_read_model.md`,
    `SESSION_057_m3_inc2_service_layer.md`,
    `SESSION_056_m3_inc1_core_models.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_070 — M4.5 vendor comm drafting + scrub shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0016` (unchanged since SESSION_066). Test
  baseline: **2,429 pass**, 1 skipped, 0 fail (up from
  2,367; +62 M4.5 tests).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  clean. `vite build` clean. Unchanged.
- **Frontend (prod):** NONE.
- **DRF defaults + CSRF + permissions:** unchanged. New
  permission class lands in M4.6.
- **Milestone 4 status:** M4.1 + M4.2 + M4.3 + M4.4 +
  M4.5 shipped; admin API + permission matrix (M4.6) is
  the next in-scope increment.
- **Dev DB seeded users:** `smoke_owner` + `smoke_advisor`.
- **New M4 tables:** unchanged from SESSION_066.
- **Service surface:**
  - `services/recon.py`: 11 recon + 4 parts + 2 Vehicle
    read helpers + 4 domain errors + ledger integration.
  - `services/vendor_comm.py`: 4 functions
    (draft/approve/mark_sent/log) + 4 domain errors.
- **Scrub surface:** `apply_post_llm_scrubs` now accepts
  `recon_source_bundle=` kwarg. `_scrub_invented_recon_fact`
  fires on `kind in {"vendor_comm", "parts_order"}`.
- **LLM path:** existing provider factory unchanged.
  Vendor comm drafting stubbed via MockLLMProvider in
  tests. Real LLM path via Ollama / OpenAI wired but
  never exercised in the automated suite.
