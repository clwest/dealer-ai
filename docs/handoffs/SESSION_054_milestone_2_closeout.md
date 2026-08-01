---
title: "SESSION_054 handoff — Milestone 2 · Increment 8 (verification + closeout)"
status: historical
type: handoff
date: 2026-07-31
session: 054
milestone: 2
milestone_status: shipped
increment: 8
increment_status: shipped
commit: (pending)
---

# SESSION_054 — Milestone 2 · Increment 8 (M2.8 — verification + closeout)

## What shipped

Documentation-only session. No code changes. Milestone 2 is
closed with every §3 compatibility item verified with inline
evidence, `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` written,
`docs/CAPABILITY_MATRIX.md` §7c added, `IMPLEMENTATION_ROADMAP.md`
§Milestone 2 flipped to shipped, and
`MILESTONE_2_PLANNING.md` frontmatter marked `status: shipped`
with the full session/commit shipping table.

## Final Milestone 2 capabilities

**All eight Milestone 2 increments landed** (SESSION_046 →
SESSION_054):

| Increment | Session | What shipped |
|-----------|---------|--------------|
| M2.1 core ledger models | 046 | `VehicleAcquisition` + `VehicleCost` + migrations `0012` + `0013` + admin registrations + `SOURCE_*` × 8 + `CATEGORY_*` × 26 + `DATABASES["migration_check"]` alias |
| M2.2 ledger business service | 047 | `services/vehicle_ledger.py` (`record_acquisition` / `add_cost` / `compute_totals` / `category_group_of` / `LedgerTotals` / `CrossTenantLedgerError` / `ZERO`) + category groupings. Load-bearing semantic contract: `total_investment` excludes `is_estimate=True` |
| M2.3 Vehicle read model | 048 | `@cached_property ledger_totals` + 9 delegator `@property` accessors + `days_in_inventory` (returns `None` when no acquisition — no misleading `imported_at` fallback) |
| M2.4a financial math + APR config | 049 | `daily_floor_plan_interest` pure engine (365-day, ROUND_HALF_UP, `ValueError` on negative principal/APR) + `get_floor_plan_apr` layered resolver + `DealerOnboardingProfile.floor_plan_apr` field + migration `0014` + `DEALER_AI_FLOOR_PLAN_APR` env |
| M2.4b accrual command | 050 | `manage.py accrue_floor_plan_interest --dealership=<slug> [--as-of=DATE] [--dry-run]`. Plan/execute split via `AccrualPlan`. Workflow-owned idempotency via `ACCRUAL:<date>` reference tag. Whole-run atomic transaction |
| M2.5 acquisition-price safety scrub | 051 | `_scrub_acquisition_price` + 12 verbal-framing patterns + branch in `apply_post_llm_scrubs`. Runs after `detect_unsafe_response`. Fires on every kind. Deliberately NOT called "stage 17" in code |
| M2.6 admin API + permission matrix | 052 | Three endpoints under `/api/dealer-ai/admin/vehicles/<stock_number>/` (`ledger/` GET, `acquisition/` POST, `costs/` POST). M1·4D permission class reused. Money as fixed two-decimal strings. Cross-tenant + nonexistent → identical 404 |
| M2.7 operator ledger UI | 053 | `/dealer-ai-inventory/:stock/ledger` inside `<RequireAuth>`. Three typed `lib/api.ts` helpers via `authFetch`. Money-as-strings end-to-end; frontend never recomputes totals |
| M2.8 verification + closeout | 054 | This session (docs-only) |

## Checklist result

**Every `MILESTONE_2_PLANNING.md` §3 item verified [x] with inline
evidence** (test class / code location / migration result /
runtime probe). One intentional annotation surfaced:

- **Anonymous → 403, not 401 on M2.6 endpoints.** DRF's default
  behavior for permission-gated endpoints when the
  `IsAuthenticated & <other>` composition fails without an
  explicit `WWW-Authenticate` challenge. The M2.6 tests assert
  `status_code in (401, 403)`; SESSION_054 runtime smoke confirmed
  anon → 403 on all three endpoints. Recorded in the annotated
  §3 as an "intentional shift" — same shape as SESSION_044's
  advisor-slug 404-→403 recording.

No compatibility item failed verification. No hardening fix was
needed. If any had failed, the SESSION_044 pattern (small,
documented, one-line fix in the same closeout commit) would
have applied — the pattern is preserved and available for future
milestones.

## Browser-smoke result

**Runtime smoke via HTTP + build tooling completed
end-to-end.** Interactive browser click-through remains a
manual step for the operator's first live use (the SESSION_054
environment could not drive an interactive browser).

Runtime smoke performed:

1. **Anonymous → M2.6 API endpoint → 403.** ✓ Direct HTTP
   probe; DRF's default response for permission-gated
   endpoints when the composed `IsAuthenticated & ...` fails.
2. **Owner authenticates via `POST /auth/login/`.** ✓ Returned
   200 + `{authenticated: true, ...}` payload.
3. **Owner GET empty ledger.** ✓ 200 + `acquisition: null`,
   `costs: []`, totals all `"0.00"`, `days_in_inventory: null`.
4. **Owner POST acquisition (create).** ✓ 201 + `created: true`,
   `purchase_price: "18500.00"`, `source_display: "Auction"`.
5. **Owner POST acquisition (upsert).** ✓ 200 + `created: false`.
6. **Owner POST cost (actual).** ✓ 201 + `is_estimate: false`,
   `created_by: "smoke_owner"`, `category_group: "recon"`.
7. **Owner POST cost (estimate).** ✓ 201 + `is_estimate: true`.
8. **Owner POST cost (negative reversal).** ✓ 201 +
   `amount: "-50.00"`.
9. **GET ledger — verify actual/estimated distinction.** ✓
   `total_investment: "20200.00"` (acquisition 19950 + actual
   250 — EXCLUDES 1200 estimate),
   `projected_total_investment: "21400.00"` (INCLUDES
   estimate), `costs count: 3`, `days_in_inventory: 92`.
10. **Cross-tenant / nonexistent stock → 404 identical body.**
    ✓ `{"detail": "Vehicle not found."}` on unknown stock.
11. **Invalid source → 400 with field error.** ✓
    `{"source": ["\"carfax\" is not a valid choice."]}`.
12. **Invalid category → 400 with field error.** ✓
    `{"category": ["\"bogus\" is not a valid choice."]}`.
13. **PUT `/costs/` → 405 (immutable, no update route).** ✓
14. **Public `/vehicles/<id>/` endpoint scanned for 7 ledger
    keywords → all clean.** ✓ (`acquisition_total`,
    `total_investment`, `projected_gross`, `purchase_price`,
    `floor_plan_interest`, `actual_cost_total`,
    `estimated_cost_total` — none appear).
15. **Accrual command dry-run.** ✓ Evaluated 135 vehicles;
    reported "Accrued: 1 ($396.36 total)" for the one with an
    acquisition; wrote zero rows.
16. **Accrual command live run.** ✓ Posted one
    `VehicleCost` row: `category=floor_plan_interest`,
    `amount=396.36`, `reference="ACCRUAL:2026-08-01"`,
    `notes="Auto-accrual: principal $18500.00 × apr 8.5% × 92
    days / 365"`.
17. **Same-day re-run.** ✓ "Accrued: 0", "duplicate: 1" — zero
    new rows posted (workflow-owned idempotency working
    correctly).
18. **Franchise env-override fresh-process smoke.** ✓
    `DEALER_AI_DEALER_TYPE=franchise DEALER_AI_PRIMARY_MAKE=Ford`
    → `dealer_type='franchise', primary_make='Ford',
    bhph_enabled=True`.
19. **Copper Canyon defaults fresh-process smoke.** ✓ No env
    vars → `dealer_type='independent', primary_make=None,
    floor_plan_lender='NextGear'`.
20. **`get_floor_plan_apr` layered fall-through.** ✓
    `DEALER_AI_FLOOR_PLAN_APR=6.25` → `6.25`; no env → `8.5`
    Copper Canyon default.
21. **Vite frontend routes served (200 SPA fallback).** ✓ `/`,
    `/login`, `/assistant`, `/showroom`,
    `/dealer-ai-inventory/CC-T-01/ledger` all returned 200.
22. **Public `/showroom` HTML shell ledger-keyword scan.** ✓
    None of the 5 ledger keywords appeared in the initial
    HTML.

**Remaining manual operator step** (queued for first live use):

Click-through walkthrough of the M2.7 UI:
- Anonymous → ledger URL → `/login?next=...` redirect.
- Owner signs in via the LoginPage form.
- Owner opens a vehicle ledger via the "Ledger" button on the
  inventory card.
- Owner records acquisition via the inline form.
- Owner posts an actual cost + an estimated cost via the
  Add Cost form.
- Owner posts a negative reversing entry.
- Refresh preserves the complete ledger.
- Advisor signs in and receives the "Not authorized" UI.
- Public `/showroom` still renders (no ledger link on public
  cards).

Every backend + framework primitive these steps exercise is
locked by the 1,753-test baseline + the SESSION_054 HTTP smoke.
The remaining step is exclusively the human-observable UI
behavior (button clicks, form submissions, redirect
observations, card rendering) which no non-interactive tooling
can produce a trustworthy result for.

## Final backend baseline

- **`python3 manage.py test dealer_ai` → 1,753 pass**, 1
  skipped, 0 fail. Verified twice this session (opening +
  closing).
- **`makemigrations dealer_ai --check --dry-run` → "No changes
  detected in app 'dealer_ai'".** Zero schema drift.
- **Migrations current through `0014`** (verified via
  `showmigrations`).

## Frontend verification

- **`npx tsc --noEmit` → clean.**
- **`npx vite build` → clean** (same pre-existing 524KB
  chunk-size warning as SESSION_044, unrelated to M2).
- **Vite dev server smoke** — all five sampled routes (`/`,
  `/login`, `/assistant`, `/showroom`, ledger URL) returned
  200.

## Financial verification

**All financial invariants verified live via runtime smoke +
by the 44 M2.2 + 20 M2.4a + 19 M2.4b + 57 M2.6 focused tests
that all pass at the 1,753 baseline:**

- Acquisition totals use Decimal values. ✓ Serializer `DecimalField`; JSON output as strings.
- Cost totals use Decimal values. ✓ Same shape.
- Frontend never recomputes financial totals. ✓ M2.7 code inspection + M2.7 handoff § "Money-handling approach".
- Money remains fixed two-decimal strings across the API boundary. ✓ `_money_str` quantize helper in `views.py`; runtime-verified output like `"total_investment": "20200.00"`.
- `total_investment` includes acquisition + actual costs only. ✓ Runtime: acquisition 19950 + actual 250 = 20200; estimate 1200 NOT included.
- Estimated rows do not appear as money already spent. ✓ Same runtime probe.
- `projected_total_investment` includes actual + estimated. ✓ Runtime: 20200 + 1200 = 21400.
- Negative reversing entries reduce the appropriate totals. ✓ Runtime: parts 300 + (-50) = 250 net (not 350).
- Floor-plan interest uses ROUND_HALF_UP. ✓ `test_daily_floor_plan_interest.DecimalPrecisionAndRounding.test_round_half_up_pushes_the_five_up`.
- 365-day convention locked. ✓ Runtime: 18500 × 8.5% × 92 days / 365 = $396.36 hand-verified.
- Repeated same-date accrual creates no duplicate row. ✓ Runtime: 1 row after first run; 0 new rows + `duplicate: 1` after re-run.
- `--dry-run` creates no rows. ✓ Runtime: dry-run reported "Accrued: 1 ($396.36)" but wrote zero rows.
- Every accrual write passes through `add_cost`. ✓ Command code inspection (line 320 of `accrue_floor_plan_interest.py`).
- No financial result depends on an LLM. ✓ Grep of ledger service, accrual command, and payment engine: zero references to `chat_engine`, `llm_safety.apply_post_llm_scrubs`, or any LLM client. Financial math is deterministic Python.

## Security and tenant-isolation verification

**All isolation invariants verified live via runtime smoke +
by the tests that pass at the 1,753 baseline:**

- Every ledger model has NOT NULL `dealership` FK. ✓ Schema tests + `git log` inspection of models.
- Every ledger row's `dealership` matches its parent Vehicle. ✓ Model `clean()` guards; test_vehicle_acquisition.CrossTenantClean + test_vehicle_cost.CrossTenantClean.
- Every ledger endpoint resolves the active dealership once. ✓ Code inspection: `views.py` M2.6 views all call `dealership = get_current_dealership(request)` at top.
- Every vehicle lookup is tenant-scoped. ✓ Code inspection: `Vehicle.objects.filter(dealership=dealership).get(stock_number=...)`.
- Every ledger service call receives explicit `dealership=`. ✓ Code inspection + `test_vehicle_ledger.CrossTenantGuards` (4 tests).
- Cross-tenant and nonexistent stock numbers fail identically. ✓ Runtime: `GET /admin/vehicles/DOES-NOT-EXIST/ledger/` → 404 + `{"detail": "Vehicle not found."}` (same body as cross-tenant case).
- Unauthorized roles receive 403. ✓ Runtime: advisor session → 403 on all three M2.6 endpoints.
- Anonymous callers receive authentication denial. ✓ Runtime: anon → 403 (see "Browser-smoke result" for the 401-vs-403 note).
- Public routes remain unauthenticated. ✓ Runtime: 6 public routes returned 200 without a session.
- Acquisition and investment figures do not appear in customer-facing responses. ✓ Runtime: 7-keyword scan against `GET /vehicles/<id>/` returned zero hits.
- Acquisition-price scrub does not damage valid customer language. ✓ `NegativeCorpusLegitimateCustomerLanguage` (21 tests) covering asking price / monthly payment / trade / budget / warranty / "purchase price IS $X" boundary.
- `DEFAULT_PERMISSION_CLASSES` remains unset. ✓ Two tests + `settings.py` inspection.

## Documentation updated

- **`docs/roadmap/MILESTONE_2_PLANNING.md`** — §3 walked with
  inline evidence per checkbox (Milestone 1 invariants +
  every new M2 invariant). Frontmatter flipped
  `status: planning → shipped` with
  `shipped_at_session: SESSION_054`, `shipped_over: [046..054]`,
  `retrospective: docs/roadmap/MILESTONE_2_RETROSPECTIVE.md`.
- **`docs/CAPABILITY_MATRIX.md`** — `last_verified` +
  `verified_against_commit` refreshed. New §7c "Vehicle
  investment ledger (Milestone 2, shipped)" block with 10
  shipped-surface rows + explicit not-shipped list. §2.1 rows
  (Acquisition record + Per-vehicle cost basis) flipped N → F.
  §2.5 row (Per-vehicle cost accumulation) flipped N → F with
  vendor-entity-remains-N note.
- **`docs/roadmap/IMPLEMENTATION_ROADMAP.md`** — §2.1 and §2.5
  status rows updated. §Milestone 2 recommended-order
  paragraph updated with "Shipped SESSION_046 → SESSION_054"
  + retrospective link + demo-flow quote.
- **`docs/roadmap/MILESTONE_2_RETROSPECTIVE.md`** — new file,
  mirrors M1 retrospective structure (§1 planned / §2 shipped
  with commit table / §3 sequencing refinements / §4
  intentional deviations / §5 regressions avoided / §6 lessons
  (11) / §7 remaining deferred / §8 roadmap adjustment).
- **`docs/handoffs/SESSION_054_milestone_2_closeout.md`** —
  this file.
- **`00-START-NEXT-SESSION.md`** — overwritten for SESSION_055
  = Milestone 3 planning-pass priority (mirror SESSION_045
  shape; deliverable is
  `docs/roadmap/MILESTONE_3_PLANNING.md`; explicit
  multi-photo-storage decision required in §5 of the
  planning artifact; no code).

## Retrospective path

`docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` — full retrospective
written this session per SESSION_054 brief §9. 11 lessons
recorded per brief, plus the M1 retrospective's own template
structure honored.

## Commit hashes

(Filled in immediately after commit.)

- (this session's commit) — `docs(m2-inc8): Milestone 2 closeout — §3 sweep, retrospective, capability matrix + roadmap flips`

## Exact SESSION_055 Milestone 3 planning scope

**SESSION_055 = Milestone 3 · Increment 0 (planning pass, no
code).** Mirror the SESSION_045 pattern.

### Deliverable

`docs/roadmap/MILESTONE_3_PLANNING.md` — the acceptance contract
for Milestone 3 (Structured Condition Report).

### Mirror the shipped `MILESTONE_2_PLANNING.md` structure

- **§0 Engineering practices to preserve.** Lift from
  `MILESTONE_2_RETROSPECTIVE.md` §6 (all 11 lessons apply).
- **§1 Design memo.** Begin with operational questions the
  Condition Report must answer (from `RECON_MAPPING.md`), then
  one entry per subsystem:
  1. `ConditionReport` model.
  2. `ConditionFinding` model.
  3. Category + severity enums (module-level constants, same
     shape as M2's `SOURCE_*` / `CATEGORY_*`).
  4. Multi-photo storage story (see below).
  5. Operator UI for author + view.
- **§2 Migration impact review.** Every existing system M3
  touches. Reuse M2 §2 table shape.
- **§3 Compatibility checklist.** Every M1 + M2 invariant M3
  must uphold — safety pipeline, ledger service contract,
  auth substrate, `total_investment` semantic contract.
- **§4 Reusable primitives review.** Inherit M1 tenancy + M2
  ledger patterns; no parallel implementations.
- **§5 Scope discipline + deferrals.** Include the
  storage-option decision (see below).
- **§7 Increment sequencing.** Mirror the M2 §7.b eight-
  increment shape. Likely 5–6 increments given the storage
  work.

### Load-bearing pre-implementation decision — multi-photo storage

`ConditionFinding` needs photo attachments. The planning pass
must choose:

- **Option A (recommended): fold storage into M3.** The
  storage story (S3-compatible + CDN configured via env;
  file-upload flow; MediaField wiring) lands as its own
  increment inside the M3 sequence, before findings-with-photos
  land.
- **Option B: pre-M3 half-milestone.** Storage ships as
  "M2.9" or "M3.0" before M3 targets its use.
- **Option C: findings without photos in v1.** Text-only for
  the first iteration; photos deferred.

Recommendation A is the cleanest: storage is truly the first
non-trivial file-upload need and belongs to the milestone that
first uses it. Half-milestones defer the coordination without
avoiding the work.

### Read-first list for SESSION_055

1. `docs/PROJECT_RULES.md` (all six rules).
2. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons +
   §7 deferrals + §8 roadmap guidance.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3.
4. `docs/research/RECON_MAPPING.md` — full document.
5. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 2.
6. `docs/BUSINESS_DOMAIN_MAP.md` §4.2 Recon.
7. `docs/roadmap/AUTHENTICATION_MODEL.md` — every
   ConditionReport row inherits the substrate.
8. Existing M2 code — `models.py`, `services/vehicle_ledger.py`,
   `services/tenancy.py`, `dealer_ai/permissions.py`, and the
   M2.6 API pattern in `views.py`.

### Explicit non-goals for SESSION_055

- ❌ No Milestone 3 code (models, migrations, services, views,
  tests).
- ❌ No changes to M2 ledger service, API, or UI.
- ❌ No `WorkOrder` / `Vendor` (Milestone 4).
- ❌ No AI-drafted work plans (Milestone 4).
- ❌ No vehicle lifecycle stage transitions (Milestone 5).
- ❌ No changes to the safety pipeline.
- ❌ No `recon_manager` permission class (Milestone 4 first
  surfaces this role's need).

## Anchors that win on conflict (for the next session)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` (lessons + §8
   guidance for M3)
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b (shape template)
7. `docs/roadmap/MILESTONE_1_PLANNING.md` §3 +
   `MILESTONE_2_PLANNING.md` §3 (annotated compatibility
   template).
8. `docs/handoffs/SESSION_054_milestone_2_closeout.md` (this
   file — M3.0 authoritative scope + browser-smoke deferred
   note).
9. Earlier M2 handoffs (SESSION_045 – SESSION_053).
10. Current source code — the shipped M2.1–M2.7 surface.

Planning docs are claims. Rules + research + code are facts.
