---
title: "Independent Dealer Pivot — Scoping & Execution Plan"
status: shipped
last_updated: 2026-07-31
baseline_commit: 2286557
phase_1_completed_commit: 3460414  # INDIE_MODE_HINT injection
phase_2_completed_commit: 5f2e537  # Copper Canyon scenarios seed
phase_3_completed_commit: 8e969d9  # inventory sample swap
phase_4_completed_commit: 0ec372a  # Django backend/freedom_ford → backend/dealer_kit rename
phase_5_completed_commit: TBD  # SESSION_031 doc + CLAUDE.md refresh (this commit)
target_persona: Copper Canyon Auto (Yuma, AZ)
---

## Status snapshot (2026-07-31)

- **Phase 1 (backend behavior surface):** ✅ shipped in 8 commits
  `36a347f` → `3460414`. Test baseline 1218 → 1261 (+43),
  1 skipped preserved, zero regressions. DealerProfile resolver
  extended; BHPH payment engine variant; indie-prohibited-copy
  post-LLM scrub; Ford-first ranking generalized to `primary_make`
  across chat_engine + inventory_search + ad_copy; SYSTEM_PROMPT
  Ford-model examples neutralized; intent parser Ford lean softened
  + model→make map; pipeline `_band_model_hint` neutralized;
  `INDIE_MODE_HINT` system fragment injected for indie configs.
- **Phase 2 (seed data + demo scenarios):** ✅ substantially shipped
  in commits `4041b91`, `63bcf4f`, `5f2e537`. Test baseline
  1261 → 1281 (+20), zero regressions. `seed_copper_canyon_demo`
  command (45 mixed-make used units). `seed_copper_canyon_scenarios`
  command (4 hand-crafted chat sessions + leads). New canonical
  `docs/demo/COPPER_CANYON_DEMO_SCRIPT.md`. Existing Dealer OS
  seed + scenarios intentionally preserved — additive approach.
- **Deferred within Phase 2:** `seed_phase3_demo` indie
  counterpart (dashboard-population variant). Not blocking — the
  4-scenario Copper Canyon seed gives enough for the ops demo.
- **Phase 3 (frontend identity + tokens):** ✅ shipped in
  commits `058cf4a`, `61c57fa`, `8e969d9`. Tailwind `ford.*`
  → `brand.*` (config + 27 consumers) with Copper Canyon
  palette (desert-sky blue + copper terracotta). `DEFAULT_DEALER`
  pivots from "Your Dealership" fallback to shipped Copper
  Canyon Auto values + placeholder SVG logo at
  `/branding/copper-canyon-logo.svg`. Inventory sample
  renamed to `sampleInventory.ts` and replaced with 12 Copper
  Canyon units matching backend seed stock. All 4 consumers
  (Hero, PublicShowroomPage, DealershipHomePage,
  InventoryPreviewPage) updated. tsc + Vite build clean.
- **Deferred within Phase 3:** Onboarding form new fields
  (dealer_type, bhph_enabled, subprime_lenders, floor_plan_lender,
  warranty_offering, credit_range_served, makes_carried) — needs
  a `DealerOnboardingProfile` migration first. `useBrand()`
  extension to expose the full DealerProfile — same migration
  dependency. The Dealer OS legacy asset
  `public/sams-freedom-ford-logo.jpg` is intentionally not
  deleted (guardrail: pivot doc forbids Tier 3 asset removal).
- **Phase 4 (Django package rename):** ✅ shipped in SESSION_031
  as a single contained-blast-radius commit `0ec372a`.
  `backend/freedom_ford/` → `backend/dealer_kit/` via `git mv`
  (7 files, history preserved) + 11-line edits across
  `dealer_kit/{settings,wsgi,asgi}.py`, `manage.py`,
  `smoke_drift_audit.py`, `render.yaml`. Test baseline
  1281 → 1281, 1 skipped preserved, zero drift.
- **Phase 5 (docs + CLAUDE.md + handoff):** ✅ shipped in SESSION_031.
  Renamed and reframed `docs/FREEDOM_FORD_{SESSION_START,BEHAVIOR_LAYER,TRANSLATION_LAYER}.md`
  → `docs/DEALER_KIT_*.md` with Copper Canyon anchor (contracts +
  worked examples preserved verbatim as historical franchise
  reference implementation). Refreshed `docs/PROJECT_WHAT_IT_IS.md`,
  `docs/BUILD_PLAN.md`, `docs/CAPABILITY_MATRIX.md`,
  `docs/CONTEXT_KIT_INVENTORY.md`. Updated `CLAUDE.md` adopt-managed
  block via `context-kit adopt` re-run + hand-edit of the
  frontend-stack-notes brand-tokens paragraph. Formal handoff
  at `docs/handoffs/SESSION_031_pivot_phase4_5.md`;
  `00-START-NEXT-SESSION.md` rewritten for SESSION_032.



# Independent Dealer Pivot — Scoping & Execution Plan

> **Decision (2026-07-31):** Full pivot. The kit's default / demo dealer
> stops being Sam Wampler's Dealer OS (McAlester, OK — franchise,
> single-make new+used) and becomes **Copper Canyon Auto** (Yuma, AZ —
> independent, mixed-make used). Franchise-specific scaffolding
> (OEM captive finance, CPO language, single-make inventory feeds) is
> pulled out of the default path. The kit stays multi-tenant capable —
> a future franchise deployment is still possible via configuration,
> but nothing in the *default* code assumes franchise semantics.

## Why this pivot

Independent used-car dealers are a bigger, more addressable SMB market
than franchise stores, and franchise dealers already have OEM-issued
tooling they're locked into. Independents run leaner, have less OEM
support, and buy their own tools — a better fit for this platform's
sales motion.

## Scope estimate (verified 2026-07-31, commit 2286557)

- **Backend Ford / model-name references:** 1,076 (`backend/dealer_ai/**/*.py`)
- **Frontend Ford / model-name references:** 63 (`frontend/src/**/*.ts{,x}`)
- **Tailwind `ford.*` token consumers:** 26 (`frontend/src/**/*.ts{,x}`)
- **`freedom_ford` module-path references:** 9 (backend)
- **`FREEDOM_FORD_*.md` docs to rename/rewrite:** 3
- **Backend test suite baseline:** 1218 pass, 1 skipped

Realistic total: **2–3 focused sessions.** Today (SESSION_030) = scoping
doc + Phase 1.

---

## The persona — Copper Canyon Auto

| Field | Value |
|---|---|
| Dealership name | Copper Canyon Auto |
| Location | Yuma, AZ |
| Established | 1987 |
| Owner | Elena Vargas (2nd gen — her dad Manuel started the lot) |
| Positioning | *Yuma's trusted lot since 1987. Straight talk on payments and credit.* |
| Voice | Warm, practical, bilingual-friendly, low-pressure, credit-inclusive |
| Lot size | 40–60 vehicles |
| Inventory | Mixed-make **used only**, 3–10 yrs old, truck/SUV-heavy (border + ag economy) |
| Make mix | Toyota, Honda, Ford, Chevy, Nissan, Kia dominant; occasional GMC/Ram/Subaru/Hyundai |
| Financing | Subprime lender panel (3 partners) + in-house BHPH portfolio; **no OEM captive** |
| Floor plan lender | NextGear |
| Warranty | 30-day / 1000-mile powertrain on retail units; AS-IS on wholesale/cash units |
| Target buyer | Working families, ag workers, snowbirds, credit-challenged buyers who need transportation |

## Product-shape deltas — franchise → independent

| Area | Franchise (Dealer OS, was) | Independent (Copper Canyon, new) |
|---|---|---|
| Inventory source | OEM feed, single make | Dealer-managed mixed-make; VINs sourced from auction + trades + private-party |
| Vehicle condition | New + CPO + used | Used only |
| Financing partners | Captive (Ford Credit) + prime banks | Subprime lender panel + in-house BHPH; no captive |
| Payment math | APR band relatively tight (~4–10%) | Two-track: standard APR + BHPH variant (weekly/biweekly, 18–24% APR, down-payment-sensitive) |
| Buyer conversation | Trim/spec-led | Credit-tier-first, payment-first, trade-in dynamics |
| Prohibited copy (new scrubs) | (few) | "brand new", "CPO", "certified pre-owned", "manufacturer warranty", "Ford Credit" / any OEM captive, "0% APR" (rare in indie world) |
| Required disclosures | OEM + standard | AS-IS disclosure by default unless retail warranty triggers; Reg Z / TILA language on financed deals |
| Onboarding fields | `dealership_name`, tone, greeting, banned words, disclaimer, escalation | + `dealer_type`, `bhph_enabled`, `subprime_lenders[]`, `floor_plan_lender`, `warranty_offering`, `credit_range_served`, `lot_size`, `make_mix[]` |

## Non-goals (out of scope for this pivot)

- Multi-tenant SaaS shell (login, org, billing) — separate future project.
- Real inventory-feed integrations (auction APIs, dealer DMS) — synthetic sample inventory only.
- Bilingual UI — persona *supports* Spanish-speaking buyers via voice, but the platform ships English-only.
- Payment processing / e-sign / DMS write-back — same as before, out of scope.
- Franchise support removal — the *code* still allows a franchise config via the same identity/onboarding layer; only the *default* path is being changed.

---

## Phase-by-phase execution plan

### Phase 0 — Scoping (THIS DOC)

Ship this file. Commit. Nothing else touched.

### Phase 1 — Backend behavior surface

**Goal:** the assistant reasons like an independent-dealer salesperson,
not a Ford-franchise one. Tests stay green.

- `backend/dealer_ai/services/dealer_config.py`
  - Extend beyond `get_dealer_name()`. Add `get_dealer_profile()` returning:
    ```python
    DealerProfile(
        name: str,
        dealer_type: Literal["independent", "franchise"] = "independent",
        bhph_enabled: bool = True,
        subprime_lenders: list[str] = [...],
        floor_plan_lender: str = "NextGear",
        warranty_offering: str = "30-day / 1000-mile powertrain",
        credit_range_served: str = "580+ with strong down; BHPH below",
        makes_carried: list[str] = [...],
    )
    ```
  - Resolution order for each field mirrors the current name resolution:
    env → `DealerOnboardingProfile` → sensible independent default.
- `backend/dealer_ai/services/` prompt templates & response constants
  - Audit every occurrence of Ford / F-150 / Maverick / Bronco / Ranger /
    Escape / OEM-captive-finance / CPO. Neutralize or make dealer-driven.
  - Add prompt scaffolding for indie sales motion: credit-tier probing,
    down-payment framing, BHPH mode framing, AS-IS language.
- **Payment engine (`payment_engine.py` or equivalent)**
  - Keep current standard-APR path.
  - Add BHPH variant: weekly / biweekly cadence, higher APR band, sensitivity
    to down-payment as % of vehicle price. Deterministic — no LLM math.
- **Post-LLM scrub stack**
  - New scrubs for indie-prohibited copy: "brand new", "CPO",
    "certified pre-owned", "manufacturer warranty", "Ford Credit" (and any
    OEM captive-brand name), "0% APR".
  - Preserve every existing scrub — they still apply.
- **Tests**
  - Every test that pins a Ford model or scenario budget: retarget to
    Copper Canyon persona strings via `@override_settings` + the new
    profile fixture. This mirrors SESSION_029's `_render()` pattern.
  - New tests for BHPH math + the new scrub rules.
  - **Target: 1218 → 1218+N pass, 1 skipped preserved.**

**Files touched (rough):** ~30–50 backend files. Discrete commits per
subsystem (config, prompts, engine, scrubs, tests).

### Phase 2 — Seed data & demo scenarios

**Goal:** the demo tells a Copper Canyon story that stress-tests the new
indie surface.

- `backend/dealer_ai/management/commands/seed_demo_vehicles.py` — replace
  with 40–60-unit Copper Canyon inventory (mixed make, 3–10 yr, truck-
  heavy, priced $3k–$25k, ~30% flagged BHPH-eligible).
- `backend/dealer_ai/management/commands/seed_demo_scenarios.py` and
  `seed_phase3_demo.py` — rewrite for indie buyer archetypes:
  1. Cash-and-carry ag worker, $6k budget, wants a work truck
  2. Credit-challenged single mom, needs weekly-pay BHPH, reliable SUV
  3. Snowbird retiree, $18k cash, wants low miles for AZ→MI drives
  4. First-time buyer with cosigner, 620 credit, sedan or crossover
  5. Trade-in buyer, financing $12k after $4k trade + $2k down
  6. Credit-rebuilder returning customer, third car from Elena
- New canonical demo script at `docs/demo/COPPER_CANYON_DEMO_SCRIPT.md`
  (parallel to the current `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md`,
  which stays as a franchise-config reference).

**Files touched:** ~5 seed files + 1 new doc.

### Phase 3 — Frontend identity & tokens

**Goal:** UI looks and reads like Copper Canyon, not Ford.

- `frontend/tailwind.config.js` — rename `ford.*` color slots to `brand.*`.
  Palette shifts to Copper Canyon feel:
  - `brand.terracotta` (primary warm) — replaces `ford.blue` as primary
  - `brand.sky` (accent cool) — desert-sky secondary
  - `brand.ink`, `brand.ash`, `brand.mist` — retained as neutral slots
- Every `ford.*` consumer (26 files) updated to `brand.*`.
- `frontend/src/data/freedomFordInventorySample.ts` → `sampleInventory.ts`,
  content replaced with mixed-make Copper Canyon sample matching Phase 2
  seed shape.
- `public/sams-freedom-ford-logo.jpg` → `copper-canyon-logo.svg` (simple
  placeholder — canyon-and-truck silhouette, warm palette; user can
  supply a real one later).
- `frontend/src/config/defaultDealer.ts` — `DEFAULT_DEALER` populated
  with Copper Canyon values as the shipped-default, not a fallback.
- `frontend/index.html` — favicon regenerated from new logo.
- Onboarding form (`/dealer-ai-onboarding`) — new fields matching
  `DealerProfile` shape (dealer_type, bhph_enabled, lenders, floor plan,
  warranty, credit range, make mix).
- `useBrand()` — extend to expose the full profile, not just name/logo.

**Files touched:** ~30–40 frontend files.

### Phase 4 — Django project package rename

**Goal:** `backend/freedom_ford/` → `backend/dealer_kit/`. Discrete
commit, no other changes.

- `backend/freedom_ford/` (settings, urls, wsgi, asgi, __init__) → `backend/dealer_kit/`
- `backend/manage.py` — `DJANGO_SETTINGS_MODULE` string
- `backend/*/wsgi.py` and `asgi.py` — same
- Any `.env.example` / `render.yaml` / launch scripts referencing the path
- Full test suite re-run to confirm zero-drift.

### Phase 5 — Docs, `CLAUDE.md`, handoff

**Goal:** documentation reflects the new default. Franchise history is
preserved but no longer the primary read.

- Rename:
  - `docs/FREEDOM_FORD_SESSION_START.md` → `docs/DEALER_KIT_SESSION_START.md`
  - `docs/FREEDOM_FORD_BEHAVIOR_LAYER.md` → `docs/DEALER_KIT_BEHAVIOR_LAYER.md`
  - `docs/FREEDOM_FORD_TRANSLATION_LAYER.md` → `docs/DEALER_KIT_TRANSLATION_LAYER.md`
- Rewrite contents for Copper Canyon as the anchor example. Franchise
  section demoted to "Alternate config: franchise dealer" appendix.
- `docs/PROJECT_WHAT_IT_IS.md`, `docs/BUILD_PLAN.md`, `docs/CAPABILITY_MATRIX.md`
  — rewrite blurbs.
- `CLAUDE.md` — update the adopt-managed block and the hand-written
  frontend stack notes (Ford tokens → brand tokens).
- `00-START-NEXT-SESSION.md` — overwritten with the SESSION_031 priority.
- New handoff `docs/handoffs/SESSION_030_independent_dealer_pivot.md`
  (or multi-session — one handoff per session executed).

---

## Guardrails (all phases)

- ❌ **Do not delete the franchise config path.** Franchise remains a
  supported *configuration*; only the *default* changes.
- ❌ **Do not re-introduce hardcoded "Sam Wampler" / "Dealer OS" /
  Ford-model strings** in default paths. Everything routes through
  `useBrand()` / `get_dealer_profile()`.
- ❌ **Do not change existing chat behavior contracts** — pre-LLM guards
  and post-LLM scrubs may *gain* rules but must not lose any. 1218-test
  baseline must stay green (+ new tests for BHPH + new scrubs).
- ❌ **Do not concurrently do dep-major upgrades** (React 18→19, Tailwind
  3→4, Vite 5→8, TypeScript 5→7). All deferred until pivot lands.
- ✅ **Do commit per subsystem**, not per phase. Small readable diffs;
  bisectable if a test breaks.
- ✅ **Do keep the `docs/FREEDOM_FORD_*` files reachable** (as renamed
  appendix or historical reference) — the franchise demo represents real
  work and stays as an alternate-config example, not deleted history.

## Success criteria for the pivot

- `python3 manage.py test` → **1218 + N pass, 1 skipped**, zero fail.
- `npx tsc --noEmit` clean; `npx vite build` clean.
- `grep -rn -E '\b(Ford|F-150|Maverick|Bronco|Sam Wampler|Dealer OS)\b' backend/dealer_ai/services frontend/src`
  → zero results in default paths (matches allowed only inside
  `# franchise-config example` scoped blocks and inside `docs/handoffs/`).
- Live walkthrough: onboarding profile empty → assistant introduces
  itself as Copper Canyon Auto; ask about a work truck → deterministic
  matcher returns mixed-make used-truck options; ask about BHPH → engine
  produces weekly-pay math; scrub stack blocks any accidental "brand
  new" / "CPO" leak.
- `docs/CAPABILITY_MATRIX.md` refreshed with new evidence markers.

---

## Open questions (to answer before Phase 3)

1. **Logo:** placeholder-only for now, or does the user want to
   commission / supply a real Copper Canyon logo before Phase 3 ships?
2. **Palette specifics:** hex values for `brand.terracotta` / `brand.sky`
   — user preference, or agent picks and user approves in Playwright
   screenshot?
3. **Subprime lender panel names:** invented (e.g. "Sonoran Credit",
   "Desert Auto Finance", "Vista Lending") or leave as generic
   "Lender A / B / C"? Invented reads better in demos but requires
   consistency across seed data.

Non-blocking for Phase 1 — flag when Phase 2/3 begins.
