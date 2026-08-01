---
state: active
date: 2026-07-31
last_session_shipped: SESSION_057
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: in-progress
next_session: SESSION_058
next_milestone: 3
next_milestone_name: "Structured condition report"
next_increment: 3
next_increment_name: "M3.3 — Vehicle read-model extension"
---

# Next session — SESSION_058 · Milestone 3 · Increment 3 (M3.3 — Vehicle read-model extension)

> **Milestone 3 · Increment 2 (M3.2) shipped at SESSION_057.**
> `backend/dealer_ai/services/condition_report.py` is live with
> seven public functions + `CrossTenantConditionReportError` +
> `ConditionReportImmutableError` + 61 focused tests. Every
> function threads `dealership=` explicitly; completed reports
> are immutable; `estimated_cost` never touches `VehicleCost`.
> See `docs/handoffs/SESSION_057_m3_inc2_service_layer.md` for
> the shipped-surface manifest and the reviewed refinement
> (planning contract tightened — `dealership=` on every
> function).
>
> **SESSION_058 opens M3.3 = two `@property` accessors on
> `Vehicle` that delegate to the M3.2 service functions this
> session shipped.** No new models. No new migrations. No
> service changes. No API. No frontend. No caching in v1.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3 —
   scope boundary.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — the property
   accessors read from the tenant substrate via the Vehicle's
   own `dealership_id`; M3.3 must NOT re-derive these
   decisions.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — the acceptance
   contract. §7 M3.1 + §7 M3.2 now annotated SHIPPED. §7
   M3.3 entry locks the sub-scope this session ships.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 — the
   eleven lessons inherit unchanged. Lesson 6 (M2.3
   `assertNumQueries` verification) is load-bearing for M3.3.
7. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b M2.3 entry —
   the Vehicle-read-model-extension shape M3.3 mirrors.
8. `docs/research/RECON_MAPPING.md` §12 + `VEHICLE_CENTRIC_PIVOT.md`
   §Phase 2 — the "does this vehicle have a completed
   condition report?" question the accessors answer.

## What M3.3 delivers (per `MILESTONE_3_PLANNING.md` §7 M3.3)

Two `@property` accessors on `Vehicle`.

**In scope:**

- `Vehicle.latest_condition_report` — returns the most recent
  `ConditionReport` (any status) for the vehicle, or `None`.
  Delegates to
  `services.condition_report.latest_condition_report(self, dealership=self.dealership)`.
- `Vehicle.latest_completed_condition_report` — returns the most
  recent `ConditionReport` with `status="complete"`, or `None`.
  Delegates to
  `services.condition_report.latest_completed_condition_report(self, dealership=self.dealership)`.
- ~15 focused tests: no reports returns None; one draft returned
  by `latest_condition_report` but None by
  `latest_completed_condition_report`; one complete returned by
  both; multiple mixed returns most-recent per accessor;
  cross-tenant vehicles never leak through;
  `assertNumQueries(1)` per property access (locks the query
  cost invariant).

**Explicitly out of scope (deferred to specific later
increments):**

- ❌ `@cached_property` — v1 is uncached. The M2.3
  `ledger_totals` cached-property pattern is proven for
  read-heavy repeated-access data; M3's report accessors are
  lighter (operator UI reads at most both once per page load).
  If subsequent operator UI work reveals repeated access,
  promote to `@cached_property` at that moment; do not
  preemptively cache.
- ❌ Any other `@property` on `Vehicle` beyond the two named
  accessors (`finding count by severity`,
  `most-recent-inspection-date`, etc. — those land as
  targeted properties in M3.7 if the UI surfaces the need,
  not preemptively).
- ❌ Storage abstraction — M3.4.
- ❌ Upload flow — M3.5.
- ❌ API endpoints — M3.6.
- ❌ Frontend — M3.7.
- ❌ AI role — never in M3.
- ❌ Any modification to M3.1 models beyond adding the two
  properties on `Vehicle`.
- ❌ Any modification to the M3.2 service module.

## What SESSION_058 should do

### Recommended step sequence

1. **Read first (in this order — one pass, do not skim):**
   - `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.3 detail
     + §1.3 Vehicle-read-model-extension design memo.
   - `docs/handoffs/SESSION_057_m3_inc2_service_layer.md` —
     the shipped-surface manifest for the service module the
     new properties delegate to.
   - `backend/dealer_ai/services/condition_report.py` —
     specifically the `latest_condition_report` and
     `latest_completed_condition_report` signatures the
     new properties delegate to.
   - `backend/dealer_ai/models.py::Vehicle` — read the
     class to see the current property surface + M2.3
     `ledger_totals` `@cached_property` pattern.
   - `backend/dealer_ai/tests/test_vehicle_ledger.py`
     (relevant `Vehicle`-property test classes if any) OR
     the equivalent M2.3 tests for the read-model pattern.

2. **Verify starting state.**
   - `git status` — clean (or only the pre-existing
     `Dealer OS/` untracked dir).
   - `python3 manage.py test dealer_ai` → **1,874 pass, 1
     skipped, 0 fail**.
   - `python3 manage.py showmigrations dealer_ai` →
     migrations current through `0015_condition_report`.
   - `python3 manage.py makemigrations dealer_ai --check
     --dry-run` → "No changes detected."

3. **Add properties on Vehicle.** Two `@property` methods in
   `backend/dealer_ai/models.py::Vehicle`, each a one-liner
   delegator. Import the service functions at the *top* of
   the file (not inside the property body) so the import
   graph is inspectable — no lazy imports for internal
   modules. Watch for import cycles (the service module
   imports from `models`, so `models` cannot import from the
   service at module top). If a cycle surfaces, use a
   function-local import inside the property body and
   document why.

4. **No migration.** M3.3 is pure Python. Confirm at
   session end.

5. **Write focused tests.** New file
   `backend/dealer_ai/tests/test_vehicle_condition_report_properties.py`.
   Target ~15 tests. Include `assertNumQueries(1)` per
   property access — this locks the invariant that each
   access is a single query. If the number surprises (e.g.
   2 queries because the tenant guard triggers a lookup),
   surface that as a scope question rather than silently
   accepting.

6. **Full suite + baseline.**
   `python3 manage.py test dealer_ai` should produce
   ~1,889 pass (1,874 + ~15 new), 1 skipped, 0 fail.

7. **Close SESSION_058 with:**
   - Vehicle property additions + focused tests committed.
   - Handoff at
     `docs/handoffs/SESSION_058_m3_inc3_read_model.md`.
   - Overwrite this file (`00-START-NEXT-SESSION.md`) with
     the SESSION_059 = M3.4 (storage abstraction) priority.
   - `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.3 entry
     annotated in-place with `SHIPPED at SESSION_058` +
     shipped-surface manifest.

## Explicit non-goals for SESSION_058

- ❌ Do NOT introduce `@cached_property` — v1 is uncached
  by design.
- ❌ Do NOT add any `@property` beyond the two named
  accessors.
- ❌ Do NOT modify `services/condition_report.py`.
- ❌ Do NOT modify any M3.1 model beyond adding the two
  property definitions on `Vehicle`.
- ❌ Do NOT add API endpoints, frontend, storage abstraction,
  presigned URLs, or photo functions.
- ❌ Do NOT touch `services/tenancy.py`.
- ❌ Do NOT modify `services/vehicle_ledger.py`,
  `services/llm_safety.py`, or any pre / post-LLM guard.
- ❌ Do NOT reopen M2 semantic contracts.
- ❌ Do NOT introduce any AI role.
- ❌ Do NOT commit any real `OPENAI_API_KEY` or credentials.

## NEXT TASK

Start SESSION_058 with the read-first list above. Add two
`@property` methods to `Vehicle`, each a one-line delegator
to the M3.2 service. Write ~15 focused tests including
`assertNumQueries(1)` per property access. Do NOT touch
storage, photo, API, or UI — those are M3.4 through M3.7.

Test baseline at SESSION_058 close: 1,874 → ~1,889.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — the acceptance
   contract; §7 M3.1 + §7 M3.2 now annotated SHIPPED; §7
   M3.3 is the sub-scope this session ships.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 (lessons)
7. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b M2.3 (shape
   template)
8. `docs/research/RECON_MAPPING.md` §2 + §12 +
   `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 2
9. `docs/CAPABILITY_MATRIX.md`
10. Most recent handoffs
    (`SESSION_057_m3_inc2_service_layer.md`,
    `SESSION_056_m3_inc1_core_models.md`,
    `SESSION_055_milestone_3_planning.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_057 — M3.2 service layer shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015` applied. Default `Dealership` row exists
  (`slug='default'`). No pending migrations. Test baseline:
  **1,874 pass**, 1 skipped, 0 fail.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 3 does not require prod.
- **Frontend (local):** Vite on `:5173`. Unchanged this
  session.
- **Frontend (prod):** NONE.
- **Frontend build:** unchanged this session; `npx tsc
  --noEmit` clean; `npx vite build` clean.
- **DRF defaults + CSRF + endpoint-level permissions:** all
  unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
  No new migration in M3.2; last verified clean-slate
  round-trip was SESSION_056.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR`. Unchanged this session. M3.4
  will add the optional `AWS_*` set.
- **Dev DB seeded users:** `smoke_owner` (dealer_owner) +
  `smoke_advisor` (advisor). Unchanged.
- **Milestone 2 shipped surface (locked, do not touch):**
  see `docs/CAPABILITY_MATRIX.md` §7c.
- **Milestone 3 shipped surface (in-progress):** M3.0
  planning (SESSION_055) + M3.1 core models (SESSION_056) +
  M3.2 service layer (SESSION_057 — this session). M3.3
  through M3.8 queued for SESSION_058 through SESSION_063.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Every deferred idea from Milestones 1 + 2 + M3
  planning + M3.1 + M3.2 is recorded in the respective
  planning + retrospective + handoff docs.
