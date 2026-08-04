---
state: active
date: 2026-08-03
last_session_shipped: SESSION_191
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
milestone_11_status: shipped
milestone_12_status: shipped
milestone_13_status: shipped
milestone_14_status: shipped
milestone_15_status: shipped
milestone_16_status: shipped
milestone_17_status: shipped
milestone_18_status: shipped
milestone_19_status: shipped
milestone_20_status: shipped
milestone_21_status: shipped
milestone_22_status: shipped
milestone_23_status: shipped
milestone_24_status: shipped
milestone_25_status: shipped
milestone_26_status: shipped
milestone_27_status: active
next_session: SESSION_192
next_milestone: 27
next_milestone_name: "Journal-Entry Creation UI (via shared GLAccount substrate)"
next_increment: 1
next_increment_name: "M27.1 — Backend substrate + frontend wrapper (admin/accounting/gl-accounts/ + fetchGLAccounts)"
---

# Next session — SESSION_192 · Milestone 27 · Increment 1 (M27.1 — backend substrate + frontend wrapper)

> **Milestone 27 — Journal-Entry Creation UI (via shared
> GLAccount substrate) — OPENED at SESSION_191 M27.0.**
> All §5 decisions locked in the M27.0 planning-only
> session. Full active memo at
> `docs/roadmap/MILESTONE_27_PLANNING.md`.
>
> **§5.a locked as A2 — Journal-Entry creation UI**, under
> the primary operational-coverage lens (durable per M22
> close). §7 verification at M27.0 surfaced the GLAccount
> FK intake gap — the create endpoint takes numeric
> `account_id`s with no discovery surface. Per user
> direction, M27 splits into two increments and attaches
> the JE-create dialog to the existing
> `AccountingJournalEntriesPage` rather than shipping a
> standalone Chart of Accounts route. `gl-accounts` is
> framed as **shared accounting infrastructure** for
> future workflows (recurring journals, adjustments,
> budget uploads, statement reconciliation, F&I
> chargebacks, period-open entries), not JE-only.
>
> **M27.1 is an infrastructure-only increment** — pure
> backend endpoint + frontend wrapper, no UI change.
> DoD exception path per M21.0 §5.f Option B invoked
> (M26 precedent). The new endpoint's operational
> journey coverage arrives at M27.2 via the JE-create
> journey extension.
>
> **Zero-drift permission-class streak enters M27 at 26
> consecutive milestones** (M10 → M26). M27 reuses
> `_M131_PERMS` for both new surfaces; no permission
> classes evolve. Intended posture at M27 close:
> extend to 27.
>
> **Planning-time as-recommended streak enters M27 at 5
> and increments to 6 at M27.0 close.** The user
> confirmed the AI's A2 recommendation; the §7
> substrate-attachment scope adjustment refined shape
> without shifting the target (empirical-discovery-
> refinement precedent per M25.0 + M25.2-open + M26.1-open
> + SESSION_189 §3 + SESSION_190 §2). Historical run of
> 89 across M10 → M23 preserved for the record.
>
> **Coverage arithmetic at M27 close (expected per §5.e):**
> backend endpoints 154 → 155 (new gl-accounts row).
> Row 140 flips → `covered` at M27.2. New gl-accounts
> row lands `covered` at M27.2 (M27.1 introduces the
> endpoint before the consumer exists). Post-M27.2:
> **155 total / 121 covered / 34 backend-only** (119 →
> 121: +row 140 + gl-accounts).
>
> **Durable planning lesson recorded at M27.0** (saved to
> memory as `feedback_verify_fk_discoverability_before_lock.md`):
> Before locking any create/edit workflow, verify that
> every required foreign key or identifier is
> discoverable and selectable by the operator through
> a truthful product surface. Governs all future
> create/edit workflow scoping.
>
> **M27.0 handoff shipped** at
> `docs/handoffs/SESSION_191_m27_inc0_planning.md`.
> No push (M27.0 is planning; coordinated push at M27
> close per §5.h Option B).

## First thing SESSION_192 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches
  `origin/main` post-M26 push (or +2 ahead if M27.0
  planning commits ship as a stack — depends on
  coordinated-push cadence choice).
- `git log --oneline -10` — top should be M26.1 hash
  backfill or the M27.0 planning commit.
- `python3 manage.py test dealer_ai` → **4,805 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **226 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run`
  → "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. Regenerate the audit artifact

Before starting implementation, confirm the M26 baseline
still holds:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Expected: **154 total / 119 covered / 35 backend-only /
312 service verbs**. If the artifact drifts, investigate
before opening §5.b implementation.

### 3. Implement M27.1 backend substrate

Per `MILESTONE_27_PLANNING.md` §5.b + §7:

1. Add `admin_gl_account_list` view to
   `backend/dealer_ai/views_accounting.py`. Shape:
   - `@api_view(["GET"])`.
   - `@permission_classes(_M131_PERMS)`.
   - `dealership = get_current_dealership(request)`.
   - Returns full CoA (all `GLAccount` rows for the
     tenant, including zero-balance) sorted by `code`
     ASC.
   - Projection per account: `{id, code, name, type}`
     where `type` is one of `asset` / `liability` /
     `equity` / `revenue` / `expense`.
   - Response envelope (per §5.c —
     `cost_posting_failures` precedent):
     ```json
     {"gl_accounts": {"accounts": [{...}, ...]}}
     ```
2. Add the `urls.py` route:
   ```python
   path("admin/accounting/gl-accounts/",
        views_accounting.admin_gl_account_list,
        name="admin-gl-account-list")
   ```

### 4. Write backend tests

New file:
`backend/dealer_ai/tests/test_m27_gl_account_list.py`.

Coverage:

- **Positive:** returns full tenant CoA sorted by code;
  zero-balance accounts included; envelope shape matches
  `{"gl_accounts": {"accounts": [...]}}`; each row has
  `id`, `code`, `name`, `type`.
- **Negative — cross-tenant:** another tenant's
  GLAccounts do NOT appear in the response.
- **Negative — permission:** non-`_M131_PERMS`
  authenticated user gets 403.
- **Negative — unauthenticated:** anonymous request
  gets 401 (or the module's authentication convention).

Run `python3 manage.py test dealer_ai` — assert green
(4,805 → ~4,810–4,812).

### 5. Implement M27.1 frontend wrapper

Add to `frontend/src/lib/accountingApi.ts`:

- `GLAccount` type (id + code + name + type; reuse
  existing `GLAccountType` alias).
- `GLAccountListResponse` interface matching the
  backend envelope.
- `fetchGLAccounts(): Promise<GLAccount[]>` — invokes
  `authGetJSON`, projects `body.gl_accounts.accounts`.

### 6. Write wrapper vitest

New file:
`frontend/src/lib/accountingApi.gl_accounts.test.ts`.

Coverage:

- Wrapper posts against the expected path.
- Response projection returns the array.
- Error propagation (network failure surfaces).

Run `cd frontend && npm test` — assert green (226 →
~228).

### 7. Regenerate audit + §5.e Phase 2 verification

- `python3 -m dealer_ai.scripts.audit_operational_surface`.
- Assert diff: **154 → 155 endpoints**. New gl-accounts
  row disposition: **`defer-candidate-O2`** (endpoint
  exists; no consumer wrapper referenced from a non-
  test frontend file yet — `fetchGLAccounts` exists at
  M27.1 but is not called anywhere until M27.2).
- **§5.e Phase 2 per-row verification for the new row:**
  - Endpoint file:line matches `views_accounting.py`
    view symbol.
  - Permissions match `_M131_PERMS`.
  - HTTP method matches GET.
- If any check fails: halt, document, treat as §5.b
  implementation gap.

### 8. Update docs

Per `MILESTONE_27_PLANNING.md` §5.e recording sites:

- `docs/CAPABILITY_MATRIX.md` — add §7β block noting
  M27.1 partial shipped surface (endpoint added;
  wrapper added; framing: shared accounting
  infrastructure for future workflows).
- Do NOT update `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  yet — M27 shipped table entry lands at M27.2 / M27.3
  close with full arithmetic.

### 9. Compose M27.1 handoff

- `docs/handoffs/SESSION_192_m27_inc1_substrate.md`.
- Frontmatter: `commit: pending-post-push` until push,
  then hash backfill in a follow-up commit.

### 10. Coordinated push at M27.1 close

Per M18 → M26 cadence: coordinated push once, at M27
close. **However**, M27.1 close IS a natural push
point if the M27.0 planning commits haven't shipped
yet AND M27.2 is likely to be a separate session.
Two acceptable postures:

- **Push M27.0 + M27.1 together at M27.1 close** (this
  session). CI verifies substrate landing. M27.2 opens
  on a clean base.
- **Defer all M27 pushes to M27.2 close** (single
  coordinated push at true milestone close per §5.h
  Option B).

**Recommended: push at M27.1 close.** Rationale: the
substrate endpoint is a self-contained shippable unit;
early CI verification catches any tenant-scope or
permission bug before M27.2 builds on top. M18 → M26
"push once per milestone" is a default, not an absolute
— split pushes are acceptable when they add safety.

Confirm push posture with user at M27.1 close before
executing.

## Non-goals for SESSION_192

- ❌ Do NOT ship any frontend UI change. M27.1 is
  backend + wrapper only.
- ❌ Do NOT add a "+ New journal entry" button. That's
  M27.2.
- ❌ Do NOT create `NewJournalEntryDialog` or
  `GLAccountPicker`. M27.2.
- ❌ Do NOT add a `createJournalEntry` wrapper. M27.2.
- ❌ Do NOT extend or add any Playwright journey.
  M27.1 invokes the §5.g exception path.
- ❌ Do NOT create a standalone Chart of Accounts
  page, route, or navigation entry. Per user direction
  at M27.0 §7.
- ❌ Do NOT modify the Trial Balance page, endpoint, or
  response shape.
- ❌ Do NOT modify any existing accounting endpoint,
  serializer, service, page, or component beyond the
  additions listed above.
- ❌ Do NOT hand-edit
  `M21_OPERATIONAL_SURFACE_AUDIT.md`. Regenerate only.
- ❌ Do NOT record the M27.1 coverage baseline without
  both §5.e sources agreeing.
- ❌ Do NOT investigate the M26-deferred O2 (row-5
  public-fetch-helper regex) or O3 (rows-1–4
  plain-string-literal) audit defects.
- ❌ Do NOT combine test-hygiene (Candidate H) into
  M27.

## Baseline expected at close

- Backend: 4,805 → ~4,810–4,812 pass.
- Frontend Vitest: 226 → ~228 pass.
- Acceptance: 14 journeys unchanged.
- Audit: **155 total / 119 covered / 36 backend-only**
  (new gl-accounts row `defer-candidate-O2`).
- CAPABILITY_MATRIX §7β partial (M27.1 shipped
  surface).
- Coordinated push posture confirmed with user.

## NEXT TASK

Start SESSION_192 with (a) starting-state
verification, (b) audit regen to confirm 119 / 154
holds, (c) M27.1 backend view + urls + tests, (d)
M27.1 frontend wrapper + vitest, (e) audit regen for
§5.e Phase 1 + Phase 2 verification of the new row,
(f) CAPABILITY_MATRIX §7β partial update, (g) compose
SESSION_192 handoff, (h) confirm push posture with
user (recommended: push M27.0 + M27.1 together at
M27.1 close for early CI verification).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_27_PLANNING.md` §5 (all
   locks)
4. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (current 119 / 154 baseline; source of truth
   pre-M27)
5. `backend/dealer_ai/views_accounting.py` (existing
   accounting-module patterns)
6. `frontend/src/lib/accountingApi.ts` (existing
   wrapper conventions)
7. `docs/handoffs/SESSION_191_m27_inc0_planning.md`
   (M27.0 close; records all locks)
8. Memory record
   `feedback_verify_fk_discoverability_before_lock.md`

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_191 — Milestone 27 OPENED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0049`. Test baseline: **4,805
  pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 226 pass** across 32 test
  files.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49
  + TS 5.6 operational; **14 journeys** passing
  end-to-end on clean DB. Full dry-run baseline:
  **20 passed (~30s)** (6 setup + 14 journeys).
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. M26.1-hash-
  backfill run green (2m14s); five most recent `main`
  runs all green.
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler.
  10 scheduled task families registered.
- **Milestones shipped:** M1 → **M26**. M27 active
  (M27.0 planning shipped SESSION_191).
- **DRF admin surface:** **114** endpoints
  (unchanged — M27.0 added zero endpoints).
- **Frontend operator routes:** 20 (unchanged; M27.2
  attaches to existing JE list route).
- **Public endpoints:** +1 M6.5 showroom
  (unchanged).
- **Service surface:** all M1–M26 packages
  unchanged. Zero M27.0 service verbs.
- **Frontend surfaces:** unchanged (M27.0 is
  planning-only).
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift
  streak **twenty-six consecutive milestones** (M10
  → M26). M27 intended posture: extend to 27.
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 27 status:** ACTIVE (M27.0 planning
  shipped SESSION_191; M27.1 substrate opens
  SESSION_192; M27.2 create dialog opens SESSION_193;
  coordinated push at M27 close per §5.h Option B).
- **Audit tooling status:** unchanged from M26.1.
  Coverage 119 / 154 / 35 backend-only / 312 service
  verbs. Row 5 remains `defer-candidate-O2` per M26.1
  empirical refinement (separate `getJSON` public-
  helper defect deferred to M28+).
- **§9 evidence for M28:** all M27 candidates that
  weren't picked remain — O2 (row-5 public-fetch-
  helper), O3 (rows-1–4 plain-string), H
  (test-hygiene). Plus new M27 §3 deferrals (JE
  templates / recurring journals, `posted_by_user`
  override, advanced picker filtering, server-side
  gl-accounts search / pagination). Plus gated
  T/U/L/M, deferred D/C, deferred stable G, plus all
  M25 §4 deferrals. Reuse of the M27.1 gl-accounts
  substrate lowers the scope cost of any future
  accounting workflow.
- **Planning-time streak: 6** (at M27.0 close;
  extends M26.1 close of 5 through M27.0 as-
  recommended increment; historical run of 89 across
  M10 → M23 preserved for the record).
- **DoD amendment (M21.0 §5.f Option B):** every
  future customer-facing milestone must add or
  update at least one Playwright operational
  journey, or explicitly document in §3 why no
  journey change is required. M27.1 invokes the
  exception path (infrastructure-only increment;
  new endpoint's journey arrives at M27.2). M27.2
  satisfies DoD directly.
- **M27.0 audit coverage at close:** unchanged —
  154 endpoints, **119 covered / 35 backend-only**
  (M27.0 is planning-only).
- **Durable lessons carried into M27+:** (a) one
  operational workflow beats two overlapping
  (M25.0); (b) planning-open verification must
  cover persistence path (M25.0 §5.b + M25.2 §5.e);
  (c) additive-forever JSONField beats CharField
  (M25.0 §5.b); (d) record empirical-discovery
  refinements honestly (M25.0 + M25.2 + SESSION_189
  §3 + SESSION_190 §2; four reinforcements across
  M24–M26); (e) modal-attached collapsible +
  success badge > toast (M25.2); (f) dependency-
  injectable helpers over network mocks in unit
  tests (M25.2); (g) audit correctness is
  supporting infrastructure — every accuracy gain
  compounds (M25.3 → M26); (h) two-source
  agreement is the mechanical guard against
  baseline drift (M26.1); (i) DoD exception path
  applies cleanly to infrastructure-focused
  milestones (M26; M27.1 second invocation);
  (j) **NEW at M27.0** — before locking any
  create/edit workflow, verify every required FK
  or identifier is discoverable and selectable by
  the operator through a truthful product surface
  (M27.0 §7 origin; saved to memory as
  `feedback_verify_fk_discoverability_before_lock.md`).
