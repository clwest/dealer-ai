---
state: active
date: 2026-08-04
last_session_shipped: SESSION_211
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
milestone_27_status: shipped
milestone_28_status: shipped
milestone_29_status: shipped
milestone_30_status: shipped
milestone_31_status: shipped
milestone_32_status: shipped
milestone_33_status: active
next_session: SESSION_212
next_milestone: 33
next_milestone_name: "F&I Intake Activation: Incoming Application to Active Deal Structure"
next_increment: 2
next_increment_name: "M33.2 — Frontend UI + Playwright loop"
---

# Next session — SESSION_212 · Milestone 33 · Increment 2 (M33.2 — frontend UI + Playwright loop)

> **Milestone 33.1 — Backend annotation + read endpoint shipped
> at SESSION_211.** Two subquery annotations on the M32.1 CA
> list queryset (`has_deal_structure` + `latest_deal_structure_id`),
> both explicitly tenant-scoped; one new read endpoint at the
> canonical path `GET /admin/deal-structures/<int:pk>/` reusing
> shipped `_M101_PERMS`; **20 new tests all pass**. Backend
> baseline advanced **4,995 → 5,015**. Audit **161/129/32/321 →
> 162/129/33/321** (§0.a truthfulness correction on M33.0
> projection — new endpoint ships as backend-only until M33.2
> lands the frontend consumer, matching the M32.1 precedent
> verbatim).
>
> **Zero-drift permission-class streak advanced 36 → 37.** All
> M33.1 endpoints reuse `_M101_PERMS` unchanged.
>
> **DoD exception path invocation #8** invoked at M33.1
> (M26 + M27.1 + M28.1 + M29.1 + M30.1 + M31.1 + M32.1 →
> M33.1). M33.2 satisfies DoD directly via the D8 Playwright
> journey.
>
> **First §0.a truthfulness correction on a coverage
> projection** landed at M33.1 close — M33.0 §5.e projected
> 129 → 130 covered / 32 → 31 backend-only / 321 → 322 service
> verbs; all three were overstated. Correction category
> documented in `SESSION_211_m33_inc1_backend.md` §5 so future
> planning sessions distinguish frontend-consumer coverage
> from backend-test coverage explicitly.
>
> **M33.2 (this session) — frontend UI + Playwright loop.**
> Ships the full first-loop operator contract from Incoming →
> structuring form → In progress → read view. Adds derived-
> status chip; "Start structuring" / "Open structure" row
> actions; `DealStructureForm` component with the D5 truthful-
> entry contract (blank ≠ 0; explicit values required for
> `amount_financed` / `taxes` / `fees`; "No trade payoff"
> checkbox affordance; basic consistency-warning surface;
> financial-language contract — only "sales target" and
> "proposed structure value" labels, never "lender-approved" /
> "lender-committed" / "actual"); `DealStructureReadView`
> component per D6; API-client extensions; ~15 new Vitest
> tests; new Playwright spec (or M32.3 extension) per D8 with
> dedicated `Structure Sam` fixture via new
> `seed_journey_fandi_intake_activation` idempotent seed
> command; financial-language regex assertion; consistency-
> warning coverage.
>
> **Projected baselines at M33.2 close:** Vitest 377 → ~392;
> acceptance 24 spec files / 31 tests → 25 spec files / 32
> tests (fresh-DB); backend suite unchanged at 5,015; audit
> 162/129/33/321 → **162/131/31/321** (both M10.2 create + M33.1
> read move from backend-only to covered when frontend
> wrappers + Playwright journey land).
>
> **SESSION_212 opens M33.2 frontend implementation.** All
> planning locks in `docs/roadmap/MILESTONE_33_PLANNING.md`;
> M33.1 backend surface in
> `docs/handoffs/SESSION_211_m33_inc1_backend.md`.

## First thing SESSION_212 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` ahead of `origin/main`
  by 4 commits (SESSION_210 planning + hash-backfill;
  SESSION_211 backend + hash-backfill).
- `git log --oneline -10` — top should be the SESSION_211
  hash-backfill commit; verify M33.0 + M33.1 commit sequence
  intact.
- `python3 manage.py test dealer_ai` → **5,015 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **377 pass** across 42 files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive reset per
  SESSION_200 §0.a durable lesson (v).

### 2. Confirm working from M33.0 planning memo

Read before touching any frontend code:

- `docs/roadmap/MILESTONE_33_PLANNING.md` §5.b D4 (derived-
  status chip) + D5 (Start structuring + truthful-entry form
  contract) + D6 (Open structure read view) + D7 (no client-
  side monthly-payment auto-derivation) + D8 (Playwright
  journey + fixture independence + financial-language regex
  assertion) + D9 (latest-only posture — Start structuring
  hidden on In progress rows; Open structure shows latest by
  `-created_at` via D3 subquery).
- §5.e M33.2 phase contract.
- §5.h non-goals (no stored status column; no Submitted /
  Approved / Contracted / Funded / Chargedback derivation;
  no lender / stipulation / contract / funding UI; no
  Lender Fit Recommendations; no PATCH / DELETE; no vehicle-
  picker for direct-create CAs; no client-side payment auto-
  derivation; no desking arithmetic).
- `docs/handoffs/SESSION_211_m33_inc1_backend.md` §7 (what the
  backend now exposes — projection fields + read endpoint
  canonical path).

### 3. Ship M33.2 frontend UI + Playwright per §5.e

**A. API-client extensions** (`frontend/src/lib/fAndIApi.ts`):

- Extend `CreditApplicationProjection` type with
  `has_deal_structure: boolean` and
  `latest_deal_structure_id: number | null`.
- Add `createDealStructure(payload)` — wraps
  `POST /admin/deal-structures/` (shipped M10.2).
- Add `getDealStructure(id: number)` — wraps
  `GET /admin/deal-structures/<int:pk>/` (canonical path;
  shipped M33.1).
- Add DealStructure response type matching backend
  `_project_deal_structure` shape (13 stored fields + three
  nullable ratios + timestamps).

**B. `DealStructureForm` component** (per D5):

- Three-section layout: Vehicle (read-only from
  writeup_context.vehicle) / Sales-side targets
  (prepopulated from writeup_context.terms; editable;
  visual affordance) / F&I proposed structure values
  (blank on load; explicit-entry required).
- **Truthful-entry contract (D5 — critical):**
  - Blank ≠ 0 anywhere.
  - Submit disabled until explicit values for
    `amount_financed`, `taxes`, `fees` (visible reason).
  - `trade_payoff` requires **explicit "No trade payoff"
    checkbox** OR explicit numeric value (untouched blank
    disables submit with the reason "Confirm trade payoff
    (enter amount or check 'No trade payoff')").
  - Prepopulated field editing transitions affordance from
    "sales target" → "proposed structure value".
  - Basic non-blocking consistency warning when
    `trade_payoff > 0 && trade_allowance == 0`.
  - `back_end_products` omitted from form (defaults to `[]`
    server-side).
- **Financial-language discipline (D5 — critical):** only
  "sales target" and "proposed structure value" labels;
  never "lender-approved" / "lender-committed" / "actual"
  anywhere in labels / placeholders / tooltips / aria-labels
  / confirmation copy.
- **No client-side monthly-payment auto-derivation (D7).**
- Submit path: POST `/admin/deal-structures/` → close →
  refetch intake list → row transitions Incoming → In
  progress.
- Testid discipline: `deal-structure-form-*` prefix;
  `deal-structure-form-field-<field-name>` for each input.

**C. `DealStructureReadView` component** (per D6):

- Read-only three-section layout; every value labeled as
  "proposed structure value" (never "sales target" at read
  time — all values are committed to the structure).
- NULL-safe ratio display ("Not computable — requires
  income" for NULL PTI/DTI).
- No edit / PATCH / delete controls in M33.
- Testid discipline: `deal-structure-read-*` prefix.

**D. `DealerFandIIncoming.tsx` extensions:**

- Derived-status chip per D4 — three-signal a11y (label +
  aria-label extension + testid double marker
  `incoming-row-status-<state>-<pk>`).
- "Start structuring" button on Incoming rows only per D9
  (hidden on In progress rows in M33; iteration UX
  deferred).
- "Open structure" button on In progress rows only per D9.
- Both actions open respective component (implementation
  choice: modal or inline panel — either satisfies D5/D6).
- Refetch intake list after successful create.
- **R1 mitigation:** "Start structuring" further gated on
  `writeup_context !== null`. Direct-create CAs (M10.1
  without hand-off upstream) render inline triage but no
  Start action; documented affordance ("No sales-side
  writeup — direct-create CA; structuring not available
  in M33").

**E. Vitest (~15 new tests):**

- Form prepopulation from writeup context.
- Form blank-required validation for `amount_financed` /
  `taxes` / `fees` (blank blocks submit; explicit 0 allows).
- Form "No trade payoff" checkbox behavior (untouched
  blocks; explicit numeric allows; checkbox allows).
- Form consistency-warning surface (renders on contradictory
  entry; non-blocking).
- Form submit path (mocked POST → refetch).
- Read view rendering of all fields.
- Read view NULL-safe ratio display.
- Status chip rendering for each derived state.
- Row-action visibility (Start on Incoming, Open on In
  progress; both gated on writeup_context).
- Financial-language assertion: no form or read view label
  contains `lender[- ]approved|lender[- ]committed|actual (rate|payment|apr|term|amount)`.

**F. Playwright (new; per D8):**

- New spec file `f_and_i_intake_activation.spec.ts` (or
  extension of M32.3 spec — either satisfies contract).
- New idempotent seed command
  `seed_journey_fandi_intake_activation` provisioning
  `Structure Sam` fixture (distinct lead + vehicle +
  writeup + CA row from M32.2 `Sales Sam` and M32.3
  `Intake Iris`).
- Journey: sign in as `f_and_i_manager` → locate seed row
  → assert Incoming chip → Start structuring → assert
  prepopulation + blank F&I fields + disabled submit →
  fill required F&I values → check "No trade payoff" (or
  enter explicit 0) → assert submit enabled → submit →
  assert transition to In progress chip → Open structure
  → assert read view with all "proposed structure value"
  labeling.
- Consistency-warning coverage (secondary journey or
  extension of primary — implementation choice).
- **Financial-language regex assertion** — at least one
  assertion verifies no form or read view text matches
  `/lender[- ]approved|lender[- ]committed|actual (rate|payment|apr|term|amount)/i`.

**G. Non-goals for M33.2 (per §5.h):**

- ❌ Do NOT introduce a new stored `status` column.
- ❌ Do NOT design Submitted / Approved / Contracted /
  Funded / Chargedback state derivation.
- ❌ Do NOT touch LenderSubmission / Stipulation / Contract
  / Funding / Chargeback surfaces.
- ❌ Do NOT implement Lender Fit Recommendations
  (recorded as future capability per D10).
- ❌ Do NOT enforce a "one deal structure per CA"
  constraint; preserve M10.2 M-to-1.
- ❌ Do NOT build multi-structure UX.
- ❌ Do NOT add PATCH or DELETE on DealStructure.
- ❌ Do NOT extend F&I role to `admin_lead_detail`.
- ❌ Do NOT silently default `taxes` / `fees` /
  `trade_payoff` / `amount_financed` to 0.
- ❌ Do NOT auto-derive `monthly_payment` client-side.
- ❌ Do NOT enforce full desking arithmetic.
- ❌ Do NOT add vehicle-picker for direct-create CAs.
- ❌ Do NOT describe any UI value as *lender-approved*,
  *lender-committed*, or *actual*.

### 4. Verify M33.2 close baselines

- Backend suite unchanged: **5,015 pass**, 1 skipped, 0
  fail.
- Frontend Vitest: 377 → **≈392 pass**.
- Acceptance fresh-DB run: 24 spec files / 31 tests →
  **25 spec files / 32 tests**; suite time under 40s.
- Frontend + acceptance `tsc --noEmit` clean.
- Regenerate audit:
  ```bash
  python3 -m dealer_ai.scripts.audit_operational_surface
  ```
  Expected: **162 / 131 / 31 / 321** (both M10.2 create +
  M33.1 read move from backend-only to covered).

### 5. DoD compliance directly satisfied

Per M21.0 §5.f Option B: M33.2 ships new Playwright journey
per D8 — DoD satisfied directly. No exception path invocation.
Document in §3 of M33.2 handoff.

### 6. Coordinated M33 close-out fold

At M33.2 close (after verifying baselines):

- Flip M33 status to `shipped` in `00-START-NEXT-SESSION.md`
  frontmatter.
- Update `docs/CAPABILITY_MATRIX.md` with new §7θ M33 shipped
  surface entry (per M32 §7η precedent).
- Author M33 retrospective at
  `docs/roadmap/MILESTONE_33_RETROSPECTIVE.md` — record
  final baselines, lesson candidates (M32 y/z/aa/bb
  eligible for elevation on M33 re-application; any new
  candidates surfaced during M33.1/M33.2 implementation),
  §9 M34 candidate list.
- Flip `00-START-NEXT-SESSION.md` to SESSION_213 M34.0
  planning.

### 7. Ship the M33.2 handoff

`docs/handoffs/SESSION_212_m33_inc2_frontend.md`.

**Do NOT push** — coordinated push at M33 close after
explicit user confirmation.

## Non-goals for SESSION_212

- ❌ Do NOT ship any backend code beyond what's needed to
  wire the frontend (no signature changes; no new endpoints;
  no schema changes).
- ❌ Do NOT open M34.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M32 shipped surface.
- ❌ Do NOT modify the M33.1 shipped surface.
- ❌ Do NOT skip the DoD compliance documentation.
- ❌ Do NOT skip the two-source audit agreement gate.
- ❌ Do NOT re-litigate M33.0 architectural verifications
  (latest-only posture; deterministic tie-break; canonical
  endpoint path; financial-language contract; truthful-entry
  form contract — all locked at M33.0 and validated through
  M33.1).
- ❌ Do NOT skip the financial-language regex assertion in
  the Playwright journey — required per D8 to prevent
  language drift.

## Baseline expected at close

- Backend: **5,015 pass**, 1 skipped, 0 fail (unchanged from
  M33.1).
- Frontend Vitest: **≈392 pass**.
- Acceptance: **25 spec files / 32 tests** fresh-DB run.
- Audit: **162 / 131 / 31 / 321** (M33.1 close was
  162/129/33/321; both M10.2 create + M33.1 read move from
  backend-only to covered).
- Migrations: **0001–0051** (unchanged since M32.1).
- Permission classes: **7 actual**, zero-drift streak
  **37 consecutive** (M10 → M33).
- Playwright personas: **6** (unchanged — `f_and_i_manager`
  shipped M32.3).

## NEXT TASK

Start SESSION_212 with (a) starting-state verification;
(b) read M33.0 memo §5.b D4-D9 + §5.e M33.2 + §5.h +
SESSION_211 §7; (c) ship API-client extensions + form + read
view + status chip + row actions + Vitest + Playwright per
§5.e; (d) verify baselines including two-source audit
agreement (162/131/31/321); (e) document DoD direct
satisfaction; (f) run coordinated M33 close-out fold
(capability matrix §7θ + retrospective + status flip);
(g) ship the M33.2 handoff at
`docs/handoffs/SESSION_212_m33_inc2_frontend.md`; **do NOT
push**.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_33_PLANNING.md`** (governing
   contract for M33)
6. `docs/roadmap/MILESTONE_32_RETROSPECTIVE.md` §9
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (M33.1 close: **162/129/33/321**; M33.2 close projection:
   162/131/31/321)
8. `docs/CAPABILITY_MATRIX.md` §7η (M32 shipped surface);
   §7θ added at M33 close
9. `docs/handoffs/SESSION_210_m33_inc0_planning.md` (M33.0
   planning + all §5 locks)
10. **`docs/handoffs/SESSION_211_m33_inc1_backend.md`** (M33.1
    shipped surface — what the frontend receives)
11. `docs/handoffs/SESSION_209_m32_inc3_fandi_ui.md` (M32
    close-out fold + F&I intake page — the receiver page)
12. Memory record
    `feedback_playwright_as_operational_contract.md` (M33
    D8 journey extends operational contract to F&I first-loop;
    financial-language regex assertion strengthens it)
13. Memory record `feedback_terminal_output_discipline.md`

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_211 — Milestone 33.1 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0051` (unchanged since M32.1). Test baseline:
  **5,015 pass**, 1 skipped, 0 fail (+20 vs M32.3).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest baseline: 377 pass** across
  42 test files (unchanged).
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS
  5.6 operational; **24 journeys** total (unchanged).
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run on
  `origin/main` at `2a1e359` (M32.3 hash-backfill commit):
  **success in 3m10s** at 2026-08-04T22:30:04Z. M33.0 +
  M33.1 are local-only; awaiting coordinated M33 close
  push before next CI run.
- **Async runtime:** unchanged (Celery 5.5.3 + Redis 6.4.0).
- **Milestones shipped:** M1 → **M32**. M33 active (M33.0
  shipped at SESSION_210; M33.1 shipped at SESSION_211;
  M33.2 opens at SESSION_212).
- **DRF admin surface:** **122** endpoints (M32.1 121 → +1
  at M33.1 via `admin-deal-structure-read`).
- **Frontend operator routes:** **21** (unchanged since
  M32.3). M33.2 will not add new routes; extends
  `DealerFandIIncoming.tsx` in place.
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** **321** verbs (unchanged at M33.1
  — new endpoint reuses shipped `get_deal_structure`
  service verb).
- **Frontend surfaces:** M32.2 sales-manager Writeups tab on
  `LeadDetailModal`; M32.3 `DealerFandIIncoming.tsx` page.
  M33.2 will add status chip + row actions +
  `DealStructureForm` + `DealStructureReadView`.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **37 consecutive milestones** (M10 → M33.1). Projection at
  M33.2: 37 (no new endpoints).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 33 status:** ACTIVE. M33.0 SHIPPED SESSION_210;
  M33.1 SHIPPED SESSION_211; M33.2 opens SESSION_212.
- **Audit tooling status:** unchanged. Coverage **129 / 162**
  at M33.1 close (§0.a truthfulness correction on M33.0
  projection); projection at M33.2 close: 131 / 162 (both
  M10.2 create + M33.1 read move from backend-only to
  covered).
- **Playwright personas:** **6 actual** (unchanged since
  M32.3). No new persona in M33.
- **§9 evidence for M34:** Lender Fit Recommendations
  elevated to future candidate list per operator directive
  at M33.0; NEW C F&I chargeback substrate (still pilot-
  evidence gated); NEW F&I workflow state extensions
  (beyond M33's two derived states — awaits operator
  evidence); NEW F&I-scoped lead-context view; NEW cross-
  lead pending-approval queue; NEW O2 + NEW O3 (unchanged);
  H (test-hygiene); plus gated T/U/L/M, deferred D,
  deferred stable G, plus M32 §3 + M31 §3 + M30 §3 +
  M29 §3 + M28 §3 + M27 §3 + M25 §4 deferrals.
- **Planning-time as-recommended streak: 11** (unchanged at
  M33.1; M33.0 planning-only shape). Projection at M33
  close: **12** if no further §5.a amendments.
- **DoD amendment (M21.0 §5.f Option B):** M33.1 invoked
  exception path #8 (backend-only annotation + read endpoint
  with no operator-visible behavior). M33.2 satisfies DoD
  directly via D8 Playwright journey.
- **Financial-language contract (locked at M33.0):** sales
  targets / proposed structure values only; never lender-
  approved / lender-committed / actual. First planning-time
  contract on financial-value language semantics; M33.2
  Playwright regex assertion is the enforcement layer.
- **Future capability recorded (at M33.0):** Lender Fit
  Recommendations — structured, auditable, human-controlled.
  NOT implemented in M33.
- **First §0.a truthfulness correction on a coverage
  projection** landed at M33.1 close — M33.0 §5.e projected
  129 → 130 covered / 32 → 31 backend-only / 321 → 322
  service verbs; all three overstated. Correction category
  documented in `SESSION_211_m33_inc1_backend.md` §5 so
  future planning sessions distinguish frontend-consumer
  coverage from backend-test coverage explicitly. Candidate
  durable lesson at M33 retrospective §5.
- **Durable lessons carried into M34+:** all (a)–(x) plus
  M31-elevated (w) + (x). M32 candidate lessons (y) / (z) /
  (aa) / (bb) awaiting first re-application. M33.0
  re-applied (z) — verification-driven revision cycles
  applied four times at M33.0 planning-open. M33.1
  surfaced one new candidate lesson: (cc) coverage-
  projection truthfulness — distinguish frontend-consumer
  coverage from backend-test coverage in planning
  projections. Awaits first re-application to elevate.
