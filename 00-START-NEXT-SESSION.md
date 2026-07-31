---
state: active
date: 2026-07-31
last_session_shipped: SESSION_030
next_session: SESSION_031
---

# Next session — SESSION_031 · pivot Phase 4–5

> **Pivot status:** Phases 1–3 shipped in SESSION_030 (19 commits,
> `1a03a39` → `3e812ba`). The kit's *default* dealer persona is
> now Copper Canyon Auto (Yuma, AZ — invented independent-dealer).
> Franchise config path is preserved via env / setting overrides.
> Backend test suite 1218 → **1281 pass**, 1 skipped, 0
> regressions. Full plan lives in
> `docs/INDEPENDENT_DEALER_PIVOT.md`; formal handoff at
> `docs/handoffs/SESSION_030_independent_dealer_pivot.md`.

## What just shipped (SESSION_030)

Three sequential phases in one session — see the handoff for
per-commit detail:

### Phase 1 — Backend behavior surface (8 commits)

- `36a347f` `dealer_config` extended with `get_dealer_profile()`
  + Copper Canyon indie defaults; env overrides for
  `DEALER_AI_DEALER_TYPE` and `DEALER_AI_PRIMARY_MAKE`.
- `ab09159` BHPH payment engine variant
  (`estimate_bhph_payment` with true weekly / biweekly
  amortization).
- `2207bc7` Indie-prohibited-copy post-LLM scrub (gated on
  `dealer_type == "independent"`).
- `b498d30` Ford-first ranking generalized to
  `primary_make` across `build_budget_context`.
- `949be1e` SYSTEM_PROMPT Ford-model examples neutralized.
- `17ec4b5` Intent parser JSON schema broadened; model → make
  map for future non-Ford model additions.
- `87b4103` Remaining Ford-first sweeps: `search_vehicles`,
  `_ford_first_top` (ad_copy), `_band_model_hint` (pipeline).
- `3460414` `INDIE_MODE_HINT` system fragment injected for
  indie configs.

Test baseline 1218 → 1261 (+43), 0 regressions.

### Phase 2 — Seed data + demo (3 code, 1 doc)

- `4041b91` `seed_copper_canyon_demo` command — 45 mixed-make
  used units (14 trucks / 16 SUVs / 12 cars / 3 vans), $4k–$25k,
  years 2012–2020. `source="copper_canyon_demo"` isolates from
  the Freedom Ford seed.
- `63bcf4f` `docs/demo/COPPER_CANYON_DEMO_SCRIPT.md` — 5-prompt
  canonical demo flow.
- `5f2e537` `seed_copper_canyon_scenarios` command — 4
  hand-crafted chat sessions + leads pointing at CC-* stock.
  Auto-invokes the inventory seed if missing.
- `d84d1bb` Pivot doc status snapshot for Phase 1 + 2.

Test baseline 1261 → 1281 (+20), 0 regressions.

### Phase 3 — Frontend identity + tokens (3 code, 1 doc)

- `058cf4a` Tailwind `ford.*` → `brand.*` rename (config + 27
  consumers) + Copper Canyon palette (desert-sky `#3f6b90` +
  copper terracotta `#c76b3a`). `src/index.css` shadcn vars
  updated to match.
- `61c57fa` `DEFAULT_DEALER` populated with Copper Canyon
  values + placeholder SVG logo at
  `/branding/copper-canyon-logo.svg`.
- `8e969d9` `freedomFordInventorySample.ts` deleted, replaced
  by `sampleInventory.ts` (12 CC-* units matching backend
  seed). All 4 consumers updated.
- `3e812ba` Pivot doc status snapshot for Phase 3.

`tsc --noEmit` + Vite build clean.

### Housekeeping

- `984ea53` Scoping doc `docs/INDEPENDENT_DEALER_PIVOT.md`.
- `1a03a39` `npm update` for in-range frontend minor / patch
  bumps + global Vercel CLI 50.44.0 → 58.4.4.

## Recommended SESSION_031 — Phase 4 + Phase 5

Two discrete phases from `docs/INDEPENDENT_DEALER_PIVOT.md`:

### Phase 4 — Django package rename

`backend/freedom_ford/` → `backend/dealer_kit/`. Contained-
blast-radius commit. Touches:

- `backend/freedom_ford/{settings.py,urls.py,wsgi.py,asgi.py,__init__.py}`
  → `backend/dealer_kit/*`
- `backend/manage.py` — `DJANGO_SETTINGS_MODULE` default
- `backend/**/*.py` — any hardcoded `freedom_ford.` imports
  (grep first: `grep -rn 'freedom_ford' backend --include='*.py'`;
  SESSION_030 audit found 9 refs)
- `render.yaml`, any launch scripts, `.env.example`
- Full test suite re-run afterwards — target: 1281 pass, 1
  skipped preserved, zero drift.

### Phase 5 — Docs + `CLAUDE.md` + fresh handoff

- Rename + rewrite (Copper Canyon anchor, franchise as
  appendix):
  - `docs/FREEDOM_FORD_SESSION_START.md` →
    `docs/DEALER_KIT_SESSION_START.md`
  - `docs/FREEDOM_FORD_BEHAVIOR_LAYER.md` →
    `docs/DEALER_KIT_BEHAVIOR_LAYER.md`
  - `docs/FREEDOM_FORD_TRANSLATION_LAYER.md` →
    `docs/DEALER_KIT_TRANSLATION_LAYER.md`
- Refresh `docs/PROJECT_WHAT_IT_IS.md`, `docs/BUILD_PLAN.md`,
  `docs/CAPABILITY_MATRIX.md` (stale runtime evidence + Ford
  framing).
- Update `CLAUDE.md`:
  - **Adopt-managed block** — either re-run
    `context-kit adopt` with a refreshed
    `--project-summary` + `--next-task` + `--notes`, or
    hand-edit inline if the block is small enough.
  - **Hand-written frontend stack notes** — swap the
    "Ford palette (`ford.blue`, `ford.accent`, …)" paragraph
    to describe the `brand.*` slots + Copper Canyon palette.
    Tailwind v3 / v4 bridge notes stay accurate — no change
    needed to the six variant patterns list.
- Write `docs/handoffs/SESSION_031_pivot_phase4_5.md`.
- Overwrite `00-START-NEXT-SESSION.md` for SESSION_032.

### Also open (lower urgency, not blocking Phase 4–5)

- `DealerOnboardingProfile` migration for the new indie
  fields (`dealer_type`, `bhph_enabled`, `subprime_lenders`,
  `floor_plan_lender`, `warranty_offering`,
  `credit_range_served`, `makes_carried`). Onboarding form
  + `useBrand()` full-profile extension follow.
- Indie counterpart of `seed_phase3_demo` (dashboard
  population). Non-blocking — the 4 Copper Canyon scenarios
  cover the manager demo needs.
- `react-router-dom` 6 → 7 (clears 2 security advisories;
  low blast radius but does need a routing migration review).
- Freedom Ford legacy JPG asset
  `public/sams-freedom-ford-logo.jpg` — the pivot guardrail
  explicitly forbids deletion for Phase 3; Phase 5 can
  revisit whether it should stay or move under
  `public/branding/franchise/` as an alternate-config asset.

## NEXT TASK

Start SESSION_031 with **Phase 4 first** (Django rename —
smaller blast radius, clean commit, unblocks doc renames
mentioning the new module path). Then Phase 5 doc / CLAUDE.md
work.

**Strict guardrails carried forward (per `docs/INDEPENDENT_DEALER_PIVOT.md`):**

- ❌ Do NOT delete the franchise config path. Franchise stays a
  supported *configuration* via
  `DEALER_AI_DEALER_TYPE=franchise` +
  `DEALER_AI_PRIMARY_MAKE=<OEM>`.
- ❌ Do NOT reintroduce hardcoded "Sam Wampler" / "Freedom Ford" /
  Ford-model strings in default paths.
- ❌ Do NOT change chat behavior contracts. 1281-test baseline
  must stay green (plus new tests for anything added).
- ❌ Do NOT do dep-major upgrades concurrent with the rename.
  Defer React 19 / Tailwind 4 / Vite 8 / TypeScript 7.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.

---

## Agent launch prompt for SESSION_031

Paste into Claude Code / Cursor / any AI coding agent as the
session opener.

```text
You are picking up SESSION_031 on the Dealer AI Kit. Phases 1–3
of the independent-dealer pivot shipped in SESSION_030 (Copper
Canyon Auto is now the default persona; franchise config
preserved via env). Full plan + status:
docs/INDEPENDENT_DEALER_PIVOT.md.

Read first:
- context-kit orient
- 00-START-NEXT-SESSION.md
- docs/INDEPENDENT_DEALER_PIVOT.md
- docs/handoffs/SESSION_030_independent_dealer_pivot.md
- docs/CAPABILITY_MATRIX.md (some Ford framing may be stale
  after Phase 3; refresh in Phase 5)

Goal: Phase 4 (Django backend/freedom_ford/ →
backend/dealer_kit/ rename) then Phase 5 (docs + CLAUDE.md
refresh + handoff).

Local dev setup:
1. LLM provider is OpenAI gpt-5-mini — API key in repo-root
   .env (untracked).
2. Django on :8001, Vite on :5173. Start both if not running.
3. Backend baseline: python3 manage.py test dealer_ai → 1281
   pass, 1 skipped.

Do NOT:
- Delete the franchise config path (franchise is still
  supported via DEALER_AI_DEALER_TYPE=franchise +
  DEALER_AI_PRIMARY_MAKE=<OEM>).
- Reintroduce hardcoded "Sam Wampler" / "Freedom Ford" strings
  in default paths.
- Change chat behavior contracts. Keep 1281-test baseline.
- Do dep-major upgrades concurrent with the rename.
- Commit any real API keys.

Phase 4 checklist:
1. grep -rn 'freedom_ford' backend --include='*.py' — expect
   ~9 refs.
2. git mv backend/freedom_ford backend/dealer_kit
3. Update manage.py, wsgi.py, asgi.py, and each grep hit for
   the new module path.
4. Update render.yaml + any .env.example if they reference the
   old path.
5. Re-run python3 manage.py test dealer_ai — target 1281 pass,
   1 skipped, 0 drift.
6. Discrete commit.

Phase 5 checklist:
1. Rename docs/FREEDOM_FORD_{SESSION_START,BEHAVIOR_LAYER,
   TRANSLATION_LAYER}.md → docs/DEALER_KIT_*.md; rewrite
   contents for Copper Canyon anchor + franchise appendix.
2. Refresh docs/PROJECT_WHAT_IT_IS.md, docs/BUILD_PLAN.md,
   docs/CAPABILITY_MATRIX.md.
3. Update CLAUDE.md hand-written frontend stack notes:
   ford.* palette description → brand.* + Copper Canyon
   palette. Tailwind v3/v4 bridge notes stay accurate.
   Consider whether to re-run context-kit adopt for the
   adopt-managed block, or hand-edit.
4. Write docs/handoffs/SESSION_031_pivot_phase4_5.md.
5. Overwrite 00-START-NEXT-SESSION.md for SESSION_032.

Verify after each phase:
- python3 manage.py test dealer_ai → 1281 pass, 1 skipped.
- npx tsc --noEmit clean.
- cd frontend && ./node_modules/.bin/vite build clean.
- grep -rn 'freedom_ford' backend --include='*.py' → 0 in
  code (docs may still mention it in Phase 4's aftermath).
```

---

## Operational state carried from SESSION_030

- **Backend (local):** Django on `:8001`. LLM provider =
  OpenAI `gpt-5-mini` (API key in repo-root `.env`).
- **Backend (prod):** `vehicle-match-api.onrender.com` — **NOT
  active**.
- **Frontend (local):** Vite on `:5173`. `useBrand()` returns
  `DEFAULT_DEALER` = Copper Canyon Auto values (no
  `OnboardingProfile` yet).
- **Frontend (prod):** **NONE**.
- **Public routes:** `/`, `/assistant`, `/showroom`,
  `/embed/assistant` — all render Copper Canyon persona from
  the shipped default.
- **Operator routes:** `/dealer-ai-overview`,
  `/dealer-ai-live-assistant`, `/dealer-ai-inventory`,
  `/dealer-ai-leads`, `/dealer-ai-manager-chat`,
  `/dealer-ai-admin`, `/dealer-ai-admin/team`,
  `/dealer-ai-onboarding`, `/dealer-ai-demo` (legacy),
  `/dealer-ai-advisor/:slug`.
- **Env overrides available for franchise config:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.

## Anchors that win on conflict

If anything here disagrees with reality:

1. `docs/INDEPENDENT_DEALER_PIVOT.md` — pivot living plan.
2. `docs/handoffs/SESSION_030_independent_dealer_pivot.md`.
3. `git log --oneline -25` (what actually shipped).
4. `git show HEAD:<path>` (current source).

Narrative docs are claims. Code and handoffs are facts.
