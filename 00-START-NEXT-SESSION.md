---
state: active
date: 2026-07-31
last_session_shipped: SESSION_054
milestone_1_status: shipped
milestone_2_status: shipped
next_session: SESSION_055
next_milestone: 3
next_milestone_name: "Structured condition report"
---

# Next session — SESSION_055 · Milestone 3 (Structured condition report) — Increment 0 (planning pass, no code)

> **Milestone 2 shipped at SESSION_054.** Every §3 compatibility
> item verified with inline evidence,
> `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` written,
> `docs/CAPABILITY_MATRIX.md` §7c added, `IMPLEMENTATION_ROADMAP.md`
> §Milestone 2 flipped to shipped. Baseline: 1,753 pass, 1
> skipped, 0 fail. Manifest of what shipped: `VehicleAcquisition`
> + `VehicleCost` + service + Vehicle read model + financial
> engine + APR config + accrual command + acquisition-price scrub
> + admin API + operator UI. `MILESTONE_2_PLANNING.md`
> frontmatter now `status: shipped`.
>
> **SESSION_055 opens Milestone 3 with a planning pass — no
> implementation.** Milestone 3 is the Structured Condition
> Report: the human-authored record of what needs to happen
> before a vehicle is front-line ready. Do not start typing
> model code before the plan is written, reviewed, and committed.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3 —
   scope boundary (in-scope / out-of-scope enumeration).
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every ConditionReport
   / ConditionFinding row inherits the tenancy + authorization
   substrate; Milestone 3 must NOT re-derive these decisions.
5. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` — the eleven
   lessons that directly shape Milestone 3's approach
   (increment discipline, actual-vs-estimated semantic contract
   inheritance for cost estimates on findings, immutable rows +
   reversing entries, focused positive/negative test matrices,
   money-as-strings if the report ever exposes cost data,
   frontend manual verification must not be marked complete
   when tooling cannot perform it).
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b — the shipped
   eight-increment sequence M3 planning should mirror in shape.
7. `docs/roadmap/MILESTONE_1_PLANNING.md` §3 (compatibility
   template) + `MILESTONE_2_PLANNING.md` §3 (annotated variant)
   — the acceptance-checklist shape Milestone 3 planning
   mirrors.
8. `docs/research/RECON_MAPPING.md` — the primary business-
   truth source for Milestone 3 (the entire recon workflow,
   pain points around inspection quality variance and jacket
   confusion, the "human-authored inspection discipline is
   non-negotiable" invariant).
9. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 2 — the
   architectural target (`ConditionReport`, `ConditionFinding`,
   category + severity enums; "AI role: NONE yet" — the report
   is proven un-automated first, automation lands with M4).
10. `docs/BUSINESS_DOMAIN_MAP.md` — the recon department
    section for cross-department context.
11. `docs/CAPABILITY_MATRIX.md` — what already exists (M2's
    ledger, M1's tenancy/auth substrate).

## What Milestone 3 delivers (per `IMPLEMENTATION_ROADMAP.md`
§Milestone 3)

For any stock number, answer: **"What needs to happen before this
vehicle is front-line ready?"** Human-authored, structured.

**In scope:**

- `ConditionReport` model (per-vehicle, timestamped, authored by
  a named human, status draft/complete).
- `ConditionFinding` model (category from mechanical/cosmetic/
  body/glass/tires/interior/fluids/electrical/safety/
  accessories/missing/other; severity from advisory/
  recommended/required/safety; description; optional cost
  estimate; optional photos).
- Multi-photo attachment per finding — introduces the first
  real file-storage need beyond the single onboarding logo. The
  planning pass must address whether storage lands with M3 or
  as a pre-M3 half-milestone.
- Operator UI to author + view a condition report.
- Deliberate absence of AI — this milestone ships with NO LLM
  role at all so the data shape gets proven before automation
  lands on top (per VCP Phase 2: *"AI role: NONE yet.
  Deliberately un-automated so the data shape gets proven
  before automation lands on top"*).

**Explicitly out of scope:**

- AI-drafted recon work plans (Milestone 4).
- `Vendor` FK model (Milestone 4).
- `WorkOrder` model (Milestone 4).
- Vehicle lifecycle stage advancement based on findings
  (Milestone 5).
- Auto-minting `VehicleCost` rows from completed work
  (Milestone 4).
- Recon-manager-specific permission class (Milestone 4 when
  recon-manager workflows first surface).
- Warranty callback tracking (Milestone 4 — post-sale repair
  concern).

## What SESSION_055 should do — Increment 0 (planning pass)

Mirror the shape of `MILESTONE_2_PLANNING.md`. No code this
session. The planning artifact is the deliverable.

### Recommended step sequence

1. **Read first (in this order — one pass, do not skim):**
   - `docs/PROJECT_RULES.md` (all six rules).
   - `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 (eleven
     lessons) + §7 (remaining deferred) + §8 (roadmap
     guidance for M3).
   - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3
     (business objective + scope boundary).
   - `docs/research/RECON_MAPPING.md` — the FULL document.
     Note the "human-authored inspection discipline is
     non-negotiable" invariant, the pain points around
     inspection quality variance and jacket confusion, and
     the recon-manager-owned workflow.
   - `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 2
     (~lines 449–470) — the target `ConditionReport` /
     `ConditionFinding` shape and the "AI role: NONE yet"
     rule.
   - `docs/BUSINESS_DOMAIN_MAP.md` §4.2 Recon department.
   - `docs/roadmap/AUTHENTICATION_MODEL.md` — every ledger
     model gets a `dealership` FK + tenant-scoped querysets
     from day one; M3 inherits.
   - `backend/dealer_ai/models.py::Vehicle` + M2's
     `VehicleAcquisition` / `VehicleCost` — the identity
     primitives ConditionReport hangs off.
   - `backend/dealer_ai/services/vehicle_ledger.py` — the
     M2 pattern M3's `services/condition_report.py` (or
     equivalent) will mirror.
   - `backend/dealer_ai/services/tenancy.py` — the tenancy
     primitives every ConditionReport read/write flows
     through.

2. **Address the multi-photo storage tension explicitly.** The
   M2 §5 deferrals list "Multi-photo storage (S3-compatible +
   CDN) — Milestone 3 concern or a pre-M3 half-milestone." M3
   `ConditionFinding` needs photo attachments. The planning
   pass must choose:
   - **Option A: Fold storage into M3.** Storage story
     (S3-compatible + CDN configured via env; MediaField
     wiring; upload flow) lands as its own increment inside
     the M3 sequence, before `ConditionFinding` photos.
   - **Option B: Pre-M3 half-milestone.** Storage ships as
     "M2.9" or "M3.0" before the M3 planning artifact
     targets its use.
   - **Option C: Ship M3 without photos.** Findings text-only
     for v1; photo attachments deferred to a later
     ConditionReport iteration. Weaker for warranty-defense
     use cases but simpler.

   Recommend Option A: storage is truly the first non-trivial
   file-upload need and belongs to the milestone that first
   uses it. Half-milestones defer the coordination without
   avoiding the work. Document the choice in the M3 planning
   artifact §5.

3. **Produce the planning artifact.** New file:
   `docs/roadmap/MILESTONE_3_PLANNING.md`. Mirror the shipped
   `MILESTONE_2_PLANNING.md` structure:
   1. **§0 Engineering practices to preserve.** Lift from M2
      retrospective §6.
   2. **§1 Design memo** — one entry per shipped subsystem
      (`ConditionReport`, `ConditionFinding`, category +
      severity enums, storage story, operator UI). Each
      entry answers: **why** (with RECON_MAPPING citation),
      **existing primitive to extend** (M2 ledger patterns,
      M1 tenancy), **what to leave untouched** (M2 ledger
      service, M2 safety pipeline, M1 auth).
   3. **§2 Migration impact review** — every existing
      system Milestone 3 touches, with concrete work required.
      Reuse the M2 §2 table shape.
   4. **§3 Compatibility checklist** — the acceptance
      contract. Every existing M1 + M2 invariant Milestone 3
      must uphold. Verified inline at Milestone 3 close, not
      by inference. Include: safety pipeline unchanged,
      ledger service contract unchanged, auth substrate
      unchanged, `total_investment` semantic contract
      unchanged (crucial — M3 findings will surface cost
      estimates that flow into M4's cost-posting workflow).
   5. **§4 Reusable primitives review** — extend `Vehicle`,
      inherit tenancy + authorization + service-layer
      patterns from M2. No parallel implementations.
   6. **§5 Scope discipline + deferrals** — every idea that
      surfaces during planning that would expand scope, per
      the Discovery Rule. Include the storage-option
      decision.
   7. **§7 Increment sequencing** — mirror the M2 §7.b
      shape. Given the storage decision (Option A above),
      likely 5-6 increments: models + admin, service layer,
      Vehicle read-model extension for report status,
      storage story, API + permission matrix, operator UI +
      closeout.

4. **Confirm nothing changed in the substrate.** Grep
   verifies: `Vehicle` unchanged (M2 only added properties),
   `services/tenancy.py` stable, `dealer_ai/permissions.py`
   unchanged, safety pipeline byte-for-byte identical.

5. **Do NOT write code this session.** No models, no
   migrations, no service functions. The plan alone.

6. **Close SESSION_055 with:**
   - The planning artifact committed.
   - Handoff at `docs/handoffs/SESSION_055_<slug>.md`.
   - Overwrite this file (`00-START-NEXT-SESSION.md`) with
     the SESSION_056 = Milestone 3 Increment 1 priority (the
     specific sequence the planning artifact chose).

## Explicit non-goals for SESSION_055

- ❌ Do NOT write any Milestone 3 code (models, migrations,
  services, views, tests).
- ❌ Do NOT touch the M1 permission classes, tenancy resolver,
  or safety pipeline. Every ConditionReport row inherits the
  substrate as-is.
- ❌ Do NOT touch the M2 ledger service, API, or UI. M3 is
  additive; the ledger contract is now stable.
- ❌ Do NOT scope in `WorkOrder`, `Vendor`, AI-drafted work
  plans, or auto-minted `VehicleCost` rows from completed
  work. All are Milestone 4 concerns.
- ❌ Do NOT scope in vehicle lifecycle stage transitions based
  on findings (Milestone 5).
- ❌ Do NOT introduce a `recon_manager` permission class in the
  planning artifact. Milestone 4 first surfaces that role's
  need; M3 uses M1 · 4D admin permissions (owner + sales_manager)
  which is the same role composition M2's ledger uses.
- ❌ Do NOT reopen the M2 semantic contracts (`total_investment`
  excludes estimates; `days_in_inventory` returns None on missing
  acquisition; money-as-strings at API boundaries).
- ❌ Do NOT commit any real `OPENAI_API_KEY` or credentials.

## NEXT TASK

Start SESSION_055 with the read-first list above. Produce
`docs/roadmap/MILESTONE_3_PLANNING.md`. Do not write code.
Address the multi-photo storage tension in the planning artifact
§5 before implementation begins.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` (lessons for M3)
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b (shape template)
7. `docs/roadmap/MILESTONE_1_PLANNING.md` §3 +
   `MILESTONE_2_PLANNING.md` §3 (compatibility template)
8. `docs/BUSINESS_DOMAIN_MAP.md`
9. `docs/research/RECON_MAPPING.md` +
   `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 2
10. `docs/CAPABILITY_MATRIX.md`
11. Most recent handoffs (`SESSION_054_...`, `SESSION_053_...`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_054 — Milestone 2 closed)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0014` applied. Default `Dealership` row exists
  (`slug='default'`). No pending migrations.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 2 did not require prod; Milestone 3 does
  not either (recon is an in-store workflow; field-based
  operator sessions land with M4 vendor emails or later).
- **Frontend (local):** Vite on `:5173`. Auth flow wired
  end-to-end. Operator ledger page at
  `/dealer-ai-inventory/:stock/ledger` shipped M2.7.
- **Frontend (prod):** NONE.
- **Test baseline (backend):** **1,753 pass**, 1 skipped,
  0 fail.
- **Frontend build:** `npx tsc --noEmit` clean; `npx vite
  build` clean (pre-existing 524KB chunk-size warning,
  unchanged).
- **DRF defaults + CSRF + endpoint-level permissions:** all
  as documented in `AUTHENTICATION_MODEL.md`. Unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR`.
- **Dev DB seeded users:** `smoke_owner` (dealer_owner) +
  `smoke_advisor` (advisor). Password `smoke-pass-4e`. Not
  committed to source. Also present after SESSION_054's
  runtime smoke.
- **Milestone 2 shipped surface (locked):**
  - Models: `VehicleAcquisition`, `VehicleCost`, `SOURCE_*` ×
    8, `CATEGORY_*` × 26, migrations `0012` + `0013`.
  - Category groupings: `FLOORING/RECON/ADMIN/PHOTOGRAPHY_CATEGORIES`.
  - Ledger service: `record_acquisition`, `add_cost`,
    `compute_totals`, `category_group_of`, `LedgerTotals`,
    `CrossTenantLedgerError`, `ZERO`.
  - Vehicle read model: `@cached_property ledger_totals` +
    9 delegators + `days_in_inventory`.
  - Financial engine + APR config: `daily_floor_plan_interest`,
    `get_floor_plan_apr`,
    `DealerOnboardingProfile.floor_plan_apr` + migration
    `0014`, `DEALER_AI_FLOOR_PLAN_APR` env.
  - Accrual command:
    `manage.py accrue_floor_plan_interest --dealership=<slug>
    [--as-of=DATE] [--dry-run]`. Workflow-owned idempotency
    via `ACCRUAL:<date>` reference tag.
  - Safety pipeline addition: `acquisition_price` scrub in
    `apply_post_llm_scrubs`.
  - Admin API: three endpoints under
    `/api/dealer-ai/admin/vehicles/<stock_number>/`
    (`ledger/` GET, `acquisition/` POST, `costs/` POST).
  - Operator UI:
    `/dealer-ai-inventory/:stock/ledger` inside
    `<RequireAuth>`. Three typed `lib/api.ts` helpers via
    `authFetch`. Money-as-strings end-to-end.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Every deferred idea from Milestones 1 + 2 is
  recorded in the respective planning + retrospective +
  handoff docs. Milestone 3 planning may want to create
  this file if new cross-milestone deferrals surface that
  don't cleanly fit any planning doc.
