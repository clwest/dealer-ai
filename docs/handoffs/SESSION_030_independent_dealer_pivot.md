---
date: 2026-07-31
title: SESSION_030 — independent-dealer pivot (Phases 1–3)
type: implementation-summary
test_baseline: 1218 → 1281 pass (+63), 1 skipped preserved, 0 regressions
persona: Copper Canyon Auto (Yuma, AZ)
---

# Session handoff — independent-dealer pivot (Phases 1–3)

The kit's *default* dealer persona pivoted from Sam Wampler's
Freedom Ford (franchise, single-make new+used) to the invented
Copper Canyon Auto (Yuma, AZ — independent, mixed-make used only).
Franchise config path is preserved as a *supported alternative*
via env / setting overrides — this was a default swap, not a
franchise-support removal.

**19 commits shipped**, `1a03a39` → `3e812ba`, spanning three
phases plus a scoping doc and a dep-hygiene commit. Test baseline
moved from 1218 → 1281 (+63 pivot-locked tests). Franchise-shaped
regression tests were retargeted with
`@override_settings(DEALER_AI_PRIMARY_MAKE="Ford")` — every
previously-passing test still passes.

Also: `docs/INDEPENDENT_DEALER_PIVOT.md` was added as the
authoritative pivot scoping + execution plan and updated with
per-phase status at each phase close. It is the north-star
document for Phase 4–5 continuation.

---

## Housekeeping (before Phase 1)

- **`1a03a39` `chore(deps): apply in-range frontend minor/patch bumps`**
  — `npm update` picked up minor/patch bumps within existing
  semver ranges (autoprefixer, playwright 1.62.1, postcss 8.5.25,
  radix-ui 1.6.7, react-router-dom 6.30.4, shadcn 4.16.0,
  `@types/react` 18.3.31). Two major-bump security advisories
  (esbuild via Vite, react-router-dom v7) deferred per pivot
  guardrail. Also (via a global `npm i -g vercel@latest`):
  Vercel CLI 50.44.0 → 58.4.4.

## Phase 0 — Scoping (`984ea53`)

- **`984ea53` `docs: scope full pivot to independent-dealer default (Copper Canyon Auto)`**
  — added `docs/INDEPENDENT_DEALER_PIVOT.md` locking:
  - The invented Copper Canyon Auto persona (Elena Vargas
    2nd-gen owner, mixed-make used, subprime + BHPH, NextGear
    floor plan, warm/practical voice).
  - Product-shape deltas franchise → independent (inventory,
    financing, payment math, buyer conversation, prohibited
    copy, onboarding fields).
  - Scope numbers verified against `2286557`: 1076 backend Ford
    refs, 63 frontend refs, 26 `ford.*` Tailwind consumers, 9
    `freedom_ford` module-path refs.
  - 5-phase execution plan with commit granularity per subsystem.
  - Guardrails preserving the 1218-test baseline and the
    franchise config path.

---

## Phase 1 — Backend behavior surface (8 commits, `36a347f` → `3460414`)

Test baseline: **1218 → 1261 pass** (+43), 1 skipped preserved,
zero regressions.

- **`36a347f` `feat(pivot): extend dealer_config with DealerProfile resolver`**
  — added `get_dealer_profile()` returning a frozen dataclass
  with shape-of-business fields (`dealer_type`, `bhph_enabled`,
  `subprime_lenders`, `floor_plan_lender`, `warranty_offering`,
  `credit_range_served`, `makes_carried`). Ships Copper Canyon
  Auto defaults. `name` and `dealer_type` have full resolution
  paths (env → `DealerOnboardingProfile` → default). Test
  contract locked by new `test_dealer_config` (+9 cases).
- **`ab09159` `feat(pivot): add BHPH payment engine variant for indie deals`**
  — `estimate_bhph_payment()` alongside the existing standard
  amortizer. True periodic (weekly / biweekly) amortization,
  not naive `monthly / 4.333` conversion. Defaults: APR 21.9%,
  30 mo term, weekly cadence, 20% min-down policy field. New
  `test_bhph_payment_engine` (+14 cases).
- **`2207bc7` `feat(pivot): add indie-prohibited-copy post-LLM scrub`**
  — new post-LLM scrub layer catches "brand new" / "CPO" /
  "certified pre-owned" / "manufacturer warranty" / "factory
  warranty" / OEM captive lenders (Ford Credit, Toyota
  Financial, Honda Financial, GM Financial, Nissan Motor
  Acceptance, Chrysler Capital) / "0% APR" / "zero percent
  financing". Gated on
  `get_dealer_profile().dealer_type == "independent"` —
  franchise deployments unaffected. Runs on all safety kinds
  (`chat`, `vehicle_ask`, `ad`, `follow_up`). Flag:
  `indie_prohibited_copy`. Test contract (+9 cases).
- **`b498d30` `feat(pivot): generalize Ford-first ranking to primary_make`**
  — replaced `_ford_first` sort key in `build_budget_context`
  with `_primary_make_first` reading
  `DealerProfile.primary_make`. Indie default = `None` = no
  OEM bias. Franchise config sets `DEALER_AI_PRIMARY_MAKE=Ford`
  to restore Ford-first ranking. Two existing franchise-shaped
  ranking tests
  (`test_ford_first_in_truck_results_at_500_mo`,
  `test_ford_first_in_budget_ranking`) now run under
  `@override_settings(DEALER_AI_PRIMARY_MAKE="Ford")`; new
  companion tests lock indie no-bias behavior.
- **`949be1e` `feat(pivot): neutralize Ford-model examples in chat_engine prompts`**
  — SYSTEM_PROMPT + helper-prompt examples now use body-style-
  generic phrasing. "smaller vehicle (Maverick / Bronco Sport /
  Escape)" → "smaller / less-expensive vehicle from inventory"
  (3 sites). Narrowing example "the Ranger or the Maverick" →
  "the pickup or the smaller crossover". Cash-mode BAD example
  swapped Ford Fusion → Toyota Camry. Near-fit GOOD example
  rebuilt around card slots (lead pick / second card / third
  card). Convertible discovery block: "sporty Ford coupe" →
  "sporty coupe" with Mustang/Camaro kept as category examples
  (preserves test_post_llm_safety's Mustang assertion).
- **`17ec4b5` `feat(pivot): neutralize intent parser Ford lean + model→make map`**
  — `_EXTRACT_PROMPT` JSON schema example broadened to mixed
  makes/models. `out.setdefault("make", "Ford")` replaced with
  `_MODEL_TO_MAKE.get(model)` lookup so future non-Ford model
  additions carry their own make. `test_detects_used_condition`
  still passes (F-150 → Ford).
- **`87b4103` `feat(pivot): sweep remaining Ford-first ranking + Ford-model hints`**
  — `_ford_first_top` in ad_copy → `_primary_make_first_top`;
  `inventory_search` sort key → primary-make-first;
  `pipeline._band_model_hint` per-band Ford-model strings
  replaced with body-style-generic suggestions
  ("compact crossovers, subcompact SUVs", etc). One more
  franchise-shaped test
  (`test_ford_appears_first_when_mixed_brands_match`)
  retargeted with `@override_settings`.
- **`3460414` `feat(pivot): inject INDIE_MODE_HINT system fragment for indie configs`**
  — new `INDIE_MODE_HINT` constant appended to LLM message
  list right after SYSTEM_PROMPT, gated on
  `dealer_type == "independent"`. Carries the "how this lot
  operates" context: mixed-make used, no OEM captive, retail
  units carry limited powertrain / cash units AS-IS,
  credit-tier conversation is normal and non-judgmental,
  down-payment framing lever, BHPH / in-house-financing
  path. Renders `{dealer_name}` via existing `_render()`
  helper. Test contract locked (+5 cases).

---

## Phase 2 — Seed data + demo (3 code commits + 1 doc commit, `4041b91` → `d84d1bb`)

Test baseline: **1261 → 1281 pass** (+20), 1 skipped preserved,
zero regressions.

- **`4041b91` `feat(pivot): add seed_copper_canyon_demo — 45-unit indie inventory`**
  — new management command creating 45 mixed-make used units
  (14 trucks, 16 SUVs, 12 cars, 3 vans). Every unit
  `condition="used"`, prices $4k–$25k, years 2012–2020,
  `source="copper_canyon_demo"` (different marker than the
  Freedom Ford seed's `"demo_seed"`). Idempotent by
  `stock_number`. Test contract locked by
  `test_copper_canyon_seed` (+11 cases): ≥6 distinct makes;
  no single make >40% share; price band ≤$6k min, ≤$27k max;
  ≥10 trucks + ≥12 SUVs + ≥8 cars + ≥2 vans.
- **`63bcf4f` `docs(pivot): add Copper Canyon demo script for Phase 2`**
  — new `docs/demo/COPPER_CANYON_DEMO_SCRIPT.md`. 5-prompt
  canonical flow exercising indie sales motion: cash work
  truck / BHPH weekly-pay SUV / "my credit's not great" /
  Toyota + trade-in / "which would you show first". Includes
  presenter talking points, setup steps, "if it goes
  off-script" guardrails, and honest scope notes on what
  Phase 3–5 still owes. Freedom Ford demo script intentionally
  preserved as the franchise-config reference.
- **`5f2e537` `feat(pivot): add seed_copper_canyon_scenarios — 4 indie chat sessions`**
  — 4 hand-crafted chat sessions + leads pointed at
  Copper Canyon inventory (CC-* stock). Auto-invokes
  `seed_copper_canyon_demo` if any referenced stock is
  missing. `demo_tag="copper_canyon_scenario"` isolates from
  the Freedom Ford scenarios. Scenarios: cash work truck
  (Carlos, handed off), BHPH weekly-pay SUV (Michelle, poor
  credit, immediate, open), snowbird cash Pilot (Diane,
  excellent credit, this_week), first-time buyer + cosigner
  (Marcus, fair credit, immediate). Test contract locked
  (+9 cases).
- **`d84d1bb` `docs(pivot): add Phase 1+2 status snapshot to pivot doc`**
  — pivot doc frontmatter tracks
  `phase_1_completed_commit: 3460414` and
  `phase_2_completed_commit: 5f2e537`. Body records what
  shipped, what's deferred within each phase, and the test
  baseline at each close.

**Deferred within Phase 2:** an indie counterpart of
`seed_phase3_demo` (dashboard-population variant). Not blocking
— the 4-scenario Copper Canyon seed already gives enough for
the manager ops demo.

---

## Phase 3 — Frontend identity + tokens (3 code commits + 1 doc commit, `058cf4a` → `3e812ba`)

Backend baseline unchanged. `npx tsc --noEmit` clean; local Vite
build clean.

- **`058cf4a` `feat(pivot): rename Tailwind ford.* → brand.* + shift to Copper Canyon palette`**
  — 30 files touched. `tailwind.config.js` `ford:` key renamed
  to `brand:` with new palette values (blue `#003478` →
  `#3f6b90` desert sky; accent `#1c69d4` → `#c76b3a` copper
  terracotta; ink / ash / mist unchanged). 27 `.ts`/`.tsx`
  consumers updated via `perl -i -pe` sweep. `src/index.css`
  shadcn CSS vars (`--primary`, `--accent`, `--ring`) updated
  to match on both `:root` and `.dark`.
- **`61c57fa` `feat(pivot): ship Copper Canyon Auto as DEFAULT_DEALER + placeholder logo`**
  — `DEFAULT_DEALER` in `src/config/defaultDealer.ts`
  populated with Copper Canyon values (`dealershipName`,
  `storeLocation="Yuma, AZ"`, tagline, empty `brand` for
  mixed-lot, `logoPath="/branding/copper-canyon-logo.svg"`).
  New placeholder SVG at
  `frontend/public/branding/copper-canyon-logo.svg` — abstract
  canyon-and-sun mark + wordmark using the new palette.
- **`8e969d9` `feat(pivot): replace inventory sample with Copper Canyon 12-unit dataset`**
  — old `src/data/freedomFordInventorySample.ts` deleted,
  replaced by `src/data/sampleInventory.ts` (12 CC-* units
  matching backend seed stock). Type / const renames:
  `FreedomFordSampleVehicle → SampleInventoryVehicle`;
  `FREEDOM_FORD_SAMPLE_INVENTORY → SAMPLE_INVENTORY`;
  `FREEDOM_FORD_SAMPLE_CAPTURED_AT → SAMPLE_INVENTORY_CAPTURED_AT`;
  `FREEDOM_FORD_SAMPLE_SOURCE_URL → SAMPLE_INVENTORY_HOMEPAGE_URL`.
  All 4 consumers updated (Hero, PublicShowroomPage,
  DealershipHomePage, InventoryPreviewPage). Adjacent cleanup:
  demo-data caption + card aria-label + SiteNav header comment
  drop samsfreedomford.com references; DEMO_SALES_PHONE
  swapped to Yuma AZ area-code placeholder.
- **`3e812ba` `docs(pivot): update pivot doc with Phase 3 completion status`**
  — pivot doc frontmatter adds
  `phase_3_completed_commit: 8e969d9`. Body records what
  shipped, what's deferred within Phase 3, Phase 4–5 outstanding.

**Deferred within Phase 3:**

- Onboarding form new fields (`dealer_type`, `bhph_enabled`,
  `subprime_lenders`, `floor_plan_lender`, `warranty_offering`,
  `credit_range_served`, `makes_carried`) — needs a
  `DealerOnboardingProfile` migration.
- `useBrand()` extension exposing the full `DealerProfile` —
  same migration dependency.
- Freedom Ford legacy JPG asset
  `public/sams-freedom-ford-logo.jpg` intentionally preserved
  per pivot guardrail ("do not delete tier-3 assets").

---

## Guardrails observed

- ✅ Franchise config path preserved. The 3 franchise-shaped
  tests (Ford-first budget ranking, mixed-brand default
  results, search Ford-first) run under
  `@override_settings(DEALER_AI_PRIMARY_MAKE="Ford")` and
  still pin the franchise behavior.
- ✅ No hardcoded "Sam Wampler" / "Freedom Ford" strings
  reintroduced in default paths — every dealer identity in
  the shipped default flows through `useBrand()` /
  `get_dealer_profile()`.
- ✅ Chat behavior contracts unchanged — pre-LLM guards +
  post-LLM scrubs may *gain* rules (the new
  `indie_prohibited_copy` scrub), but no existing rule was
  removed. 1218-test baseline preserved (+63 net new tests).
- ✅ No dep-major upgrades concurrent with the pivot. React
  18 → 19, Tailwind 3 → 4, Vite 5 → 8, TypeScript 5 → 7 all
  intentionally deferred.
- ✅ Commit-per-subsystem discipline. Every commit passes
  the full test suite on its own; the diff is bisectable.
- ✅ `docs/FREEDOM_FORD_*.md` files left intact — they stay
  as franchise-config appendix material until Phase 5 renames
  them.

## Operational state at end of session

- **Backend (local):** Django on `:8001`, LLM provider =
  OpenAI `gpt-5-mini` (`OPENAI_API_KEY` in repo-root `.env`).
  `DealerOnboardingProfile` empty →
  `get_dealer_name()` returns `"the dealership"` fallback.
- **Backend (prod):** `vehicle-match-api.onrender.com` — **NOT
  active** (unchanged from SESSION_029).
- **Frontend (local):** Vite on `:5173`. `useBrand()` returns
  `DEFAULT_DEALER` = Copper Canyon Auto values.
- **Frontend (prod):** **NONE** (unchanged from SESSION_029).
- **Test suite:** 1281 pass, 1 skipped, 0 failed.
- **Frontend build:** `tsc --noEmit` clean; local Vite build
  clean; 491.94 kB JS + 56.56 kB CSS bundles.

## What's left for SESSION_031

Phases 4 and 5 from `docs/INDEPENDENT_DEALER_PIVOT.md`:

### Phase 4 — Django package rename

`backend/freedom_ford/` → `backend/dealer_kit/`. Discrete
commit. Touches `manage.py`, `wsgi.py`, `asgi.py`,
`DJANGO_SETTINGS_MODULE` env references, any launch scripts,
`render.yaml`. Full test suite re-run to confirm zero drift.

### Phase 5 — Docs + `CLAUDE.md` + handoff

- Rename `docs/FREEDOM_FORD_SESSION_START.md` →
  `docs/DEALER_KIT_SESSION_START.md`.
- Rename `docs/FREEDOM_FORD_BEHAVIOR_LAYER.md` →
  `docs/DEALER_KIT_BEHAVIOR_LAYER.md`.
- Rename `docs/FREEDOM_FORD_TRANSLATION_LAYER.md` →
  `docs/DEALER_KIT_TRANSLATION_LAYER.md`.
- Rewrite contents for Copper Canyon as the anchor example.
  Franchise section becomes an appendix.
- Refresh `docs/PROJECT_WHAT_IT_IS.md`, `docs/BUILD_PLAN.md`,
  `docs/CAPABILITY_MATRIX.md` (stale runtime evidence).
- Update `CLAUDE.md`: the adopt-managed block (auto),
  hand-written frontend stack notes (`ford.*` → `brand.*`
  palette description, tailwind bridge documentation still
  accurate).
- Overwrite `00-START-NEXT-SESSION.md` for SESSION_032.

### Also open (lower urgency)

- Onboarding form + `DealerOnboardingProfile` migration for
  the new indie fields.
- `useBrand()` extension to expose full `DealerProfile`.
- Indie counterpart of `seed_phase3_demo`.
- react-router-dom 6 → 7 upgrade (clears 2 security
  advisories; low blast radius, does need routing migration
  review).

## Anchors that win on conflict

If anything in this handoff disagrees with reality:

1. `docs/INDEPENDENT_DEALER_PIVOT.md` — living pivot plan.
2. `git log --oneline -25` (what actually shipped).
3. `git show HEAD:<path>` (current source).

Narrative docs are claims. Code and the pivot doc's
phase-completed commits are facts.
