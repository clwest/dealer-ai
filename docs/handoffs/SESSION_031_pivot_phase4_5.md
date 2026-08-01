---
date: 2026-07-31
title: SESSION_031 — independent-dealer pivot Phases 4–5 (Django rename + docs refresh)
type: implementation-summary
test_baseline: 1281 pass (held), 1 skipped preserved, 0 regressions
persona: Copper Canyon Auto (Yuma, AZ)
picks_up_from: SESSION_030_independent_dealer_pivot.md
---

# Session handoff — pivot Phases 4–5

Closes out the independent-dealer pivot begun in SESSION_030. Two
discrete phases:

- **Phase 4** — Django project package rename
  `backend/freedom_ford/` → `backend/dealer_kit/`. Single contained-
  blast-radius commit. Test baseline held at 1281/1/0.
- **Phase 5** — Documentation refresh. Renamed 3 `FREEDOM_FORD_*.md`
  anchors → `DEALER_KIT_*.md`; refreshed adopt-managed docs
  (PROJECT_WHAT_IT_IS, BUILD_PLAN, CLAUDE.md managed block) via
  `context-kit adopt --write` with the pivot-aware summary + notes;
  hand-edited the CLAUDE.md frontend-stack-notes brand-tokens
  paragraph; updated cross-references in CAPABILITY_MATRIX,
  CONTEXT_KIT_INVENTORY, DEALER_DUPLICATION_GUIDE,
  ASSISTANT_AGENT_CREATION_ROADMAP, and the pivot doc status
  snapshot.

The full 5-phase pivot is now shipped. Franchise config path
preserved via env overrides throughout — no franchise-support
removal at any layer.

---

## Phase 4 — Django project package rename (`0ec372a`)

**Goal:** `backend/freedom_ford/` → `backend/dealer_kit/`. Discrete
commit, no other changes. Test baseline: **1281 → 1281** (held), 1
skipped preserved, zero drift.

- **`0ec372a` `refactor(pivot): rename Django project backend/freedom_ford/ → backend/dealer_kit/`**
  - `git mv backend/freedom_ford backend/dealer_kit` (7 files,
    100% history-preserved for 5 of them, 57% similarity on
    `wsgi.py`/`asgi.py` due to the 1-line module-path edit,
    96% on `settings.py` due to 3 module-path edits).
  - 11-line edits across the 6 files that referenced the old path:
    - `backend/dealer_kit/settings.py` — 3 refs: middleware entry,
      `ROOT_URLCONF`, `WSGI_APPLICATION`.
    - `backend/dealer_kit/wsgi.py`, `backend/dealer_kit/asgi.py`,
      `backend/manage.py`, `backend/smoke_drift_audit.py` — one
      `DJANGO_SETTINGS_MODULE` line each.
    - `render.yaml` — 4 refs: `collectstatic --settings=`,
      `migrate --settings=`, `gunicorn dealer_kit.wsgi:application`,
      `DJANGO_SETTINGS_MODULE` env var.
  - `backend/dealer_kit/prod_settings.py` uses relative import
    (`from .settings import *`) so it needed no edits.
  - `backend/.env.example` and `backend/render-requirements.txt`
    had no `freedom_ford` refs.
  - Two lingering `freedom_ford` references in
    `backend/dealer_ai/tests/test_post_llm_safety.py` are test *method
    names* (`test_response_offers_freedom_ford_advisor_connection`,
    `test_response_identifies_as_freedom_ford_ai`) that describe
    response *content*, not module paths — they run correctly under
    the new module and were intentionally left untouched. Rename
    them if / when the response content itself is updated.
  - `find backend -type d -name __pycache__ -delete` before test run
    to avoid stale bytecode confusion.
  - **`python3 manage.py test dealer_ai` → 1281 pass, 1 skip, 0
    fail. ~3.6s.**

---

## Phase 5 — Docs, `CLAUDE.md`, handoff (this commit)

**Goal:** documentation reflects the new default. Franchise history
preserved but no longer the primary read.

### 5.1 — Renamed + reframed the three FREEDOM_FORD_* anchors

`git mv` preserves history on all three. Content edits kept the
underlying contracts verbatim (they were dealer-agnostic) and
updated only the framing:

- `docs/FREEDOM_FORD_SESSION_START.md` → `docs/DEALER_KIT_SESSION_START.md`
  — full rewrite of the hand-written orientation index. Title +
  frontmatter updated; SESSION_019 platform-reframe callout replaced
  with a 2026-07-31 pivot callout (Copper Canyon default, franchise
  alternate via env overrides); baseline table updated (1281/1/0,
  OpenAI gpt-5-mini, `backend/dealer_kit/`, Copper Canyon default
  dealer + 12-unit `sampleInventory.ts` + 45-unit backend seed);
  read order updated to reference `DEALER_KIT_*` docs +
  `COPPER_CANYON_DEMO_SCRIPT.md` + `INDEPENDENT_DEALER_PIVOT.md`;
  smoke-check baseline bumped to 1281. Length: 110 → ~112 lines.

- `docs/FREEDOM_FORD_BEHAVIOR_LAYER.md` → `docs/DEALER_KIT_BEHAVIOR_LAYER.md`
  — surgical edits: title + frontmatter, added a
  "Reference implementation note" callout at the top explaining
  the Ford examples are the tested franchise-config reference and
  the contracts are identical for Copper Canyon (with two indie
  additions: `INDIE_MODE_HINT` fragment + `indie_prohibited_copy`
  scrub). Persona identity slot updated from *"friendly Freedom
  Ford salesperson"* to *"friendly salesperson at the configured
  dealership (Copper Canyon Auto by default; whatever
  `useBrand().dealershipName` resolves to at runtime)"*. Last
  Verified section expanded to note contract vs pivot-reframing
  dates. All 15+ voice contracts, GOOD/BAD examples, scrub-stack
  table, reply-rule branches, and small-model behavior notes
  preserved verbatim.

- `docs/FREEDOM_FORD_TRANSLATION_LAYER.md` → `docs/DEALER_KIT_TRANSLATION_LAYER.md`
  — surgical edits: title + frontmatter (including
  `last_reframed: 2026-07-31`); companion_docs list swapped to
  `DEALER_KIT_*`; added the same reference-implementation callout
  as BEHAVIOR_LAYER; source-of-truth list updated (added
  `INDEPENDENT_DEALER_PIVOT.md` as item 6); test-count example in
  Truth-Preservation Rules bumped from `1189` → `1281`. All
  personas, translation modes, truth-preservation rules, Live
  Chat Mode contract, and three SESSION_008–010 worked examples
  preserved verbatim (they remain accurate as historical
  franchise-config cases; the same contract applies to Copper
  Canyon). Last Verified expanded with a pivot-reframing entry.

### 5.2 — Refreshed adopt-managed docs via `context-kit adopt --write`

Ran with pivot-aware args:

```bash
context-kit adopt . \
  --project-summary "<one-sentence Dealer AI Kit + Copper Canyon default>" \
  --next-task    "<SESSION_032 candidates>" \
  --notes        "<SESSION_030+031 shipped summary + deferred list>" \
  --write
```

Result:
- `docs/PROJECT_WHAT_IT_IS.md` — adopt block refreshed with the
  new project summary. Hand-filled *Why it exists* + *Who it's
  for* placeholder sections **inside** the adopt markers with
  pivot-motivated content (indie SMB market thesis; primary /
  secondary / internal audiences). **Caveat:** these placeholder
  fills will be clobbered on next `context-kit adopt` re-run —
  future refresh should either preserve them by copying into
  `--notes`, or context-kit adopt could grow `--why` / `--audience`
  flags. Documented as tech debt.
- `docs/BUILD_PLAN.md` — adopt block refreshed. Cleanly regenerated
  with the new project summary, discovered notes (SESSION_030+031
  summary + deferred items), and SESSION_032 next milestone. No
  hand-editing needed inside markers.
- `CLAUDE.md` — adopt-managed block refreshed. **Hand-written
  frontend stack notes below the marker survived unchanged.** Then
  hand-edited the **Brand tokens** paragraph: swapped the Ford
  palette description (`ford.blue / ford.accent / ford.ink / ford.ash
  / ford.mist`) for the `brand.*` dealer-agnostic palette + Copper
  Canyon values (desert-sky `#3f6b90`, copper terracotta `#c76b3a`,
  warm neutrals) and added a note that franchise dealers can
  override the hex values without touching consumer code. Retained
  the tech-debt callout on the preserved
  `public/sams-freedom-ford-logo.jpg`.
- `00-START-NEXT-SESSION.md` — adopt correctly **skipped** this
  file (exists without adopt markers). The hand-written SESSION_032
  version below was written manually.

**Known cosmetic tech-debt:** the adopt-generated titles in
`PROJECT_WHAT_IT_IS.md` (`# Dealer OS — What It Is`) and
`BUILD_PLAN.md` (`# Dealer OS — Build Plan`) still say "Freedom
Ford" because adopt derives project names from the git working
directory (`freedom-ford/`). The one-paragraph project summary
inside is correct (says "Dealer AI Kit"). Full title fix requires
either (a) renaming the git working directory + repo, or (b) adopt
growing a `--project-name` override flag. Left as tech-debt.

### 5.3 — Refreshed cross-referencing docs

- `docs/CAPABILITY_MATRIX.md` — updated frontmatter
  (`last_verified: 2026-07-31`, `verified_against_commit: 0ec372a`);
  test count `1218 → 1281` (both objective baseline + "honestly
  claim to a prospect" section); "Seed inventory is still 100%
  Ford (Tier 2 rebrand pending)" gap → replaced with a note
  describing the Copper Canyon pivot shipped + Dealer OS
  franchise-config preserved as alternate + `backend/dealer_kit/`
  rename; doc-path refs updated `FREEDOM_FORD_*` → `DEALER_KIT_*`.
- `docs/CONTEXT_KIT_INVENTORY.md` — updated the low-signal intro
  note: replaced Dealer OS framing with "Dealer AI Kit";
  updated the referenced-doc bullet from
  `FREEDOM_FORD_BEHAVIOR_LAYER.md` → `DEALER_KIT_BEHAVIOR_LAYER.md`;
  added `backend/dealer_kit/` to the mentioned directory shape.
- `docs/DEALER_DUPLICATION_GUIDE.md` — updated the "Related docs"
  bullet from `FREEDOM_FORD_SESSION_START.md` (historical
  walkthrough) → `DEALER_KIT_SESSION_START.md` (with a Phase 5
  rename note).
- `docs/onboarding/ASSISTANT_AGENT_CREATION_ROADMAP.md` — updated
  the single `FREEDOM_FORD_BEHAVIOR_LAYER.md` reference.
- `docs/INDEPENDENT_DEALER_PIVOT.md` — frontmatter: `status:
  active` → `status: shipped`, added
  `phase_4_completed_commit: 0ec372a` and Phase 5 marker. Status
  snapshot: expanded the "Phase 4–5: Not started" bullet into
  Phase 4 shipped + Phase 5 shipped bullets with commit hashes.

### 5.4 — Wrote SESSION_031 handoff (this file)

### 5.5 — Overwrote `00-START-NEXT-SESSION.md` for SESSION_032

Full pivot marked complete; SESSION_032 priorities set to the
deferred indie-onboarding-migration work and the two smaller
open items (react-router-dom 6→7 migration, indie counterpart of
`seed_phase3_demo`).

---

## Files touched

**Phase 4 (`0ec372a`):**

- `backend/freedom_ford/` → `backend/dealer_kit/` (7 files via git mv)
- `backend/dealer_kit/settings.py` (3 line edits)
- `backend/dealer_kit/wsgi.py`, `dealer_kit/asgi.py`, `manage.py`,
  `smoke_drift_audit.py` (1 line each)
- `render.yaml` (4 line edits)

**Phase 5 (this commit):**

- `docs/DEALER_KIT_SESSION_START.md` (renamed from FREEDOM_FORD_*, rewritten)
- `docs/DEALER_KIT_BEHAVIOR_LAYER.md` (renamed, surgical edits)
- `docs/DEALER_KIT_TRANSLATION_LAYER.md` (renamed, surgical edits)
- `docs/PROJECT_WHAT_IT_IS.md` (adopt refresh + hand-filled Why/Who)
- `docs/BUILD_PLAN.md` (adopt refresh)
- `docs/CAPABILITY_MATRIX.md` (baseline + doc-path + seed-inventory line)
- `docs/CONTEXT_KIT_INVENTORY.md` (intro reframe)
- `docs/DEALER_DUPLICATION_GUIDE.md` (one bullet updated)
- `docs/INDEPENDENT_DEALER_PIVOT.md` (frontmatter + status snapshot)
- `docs/onboarding/ASSISTANT_AGENT_CREATION_ROADMAP.md` (one line)
- `CLAUDE.md` (adopt refresh + hand-edit of frontend stack notes)
- `docs/handoffs/SESSION_031_pivot_phase4_5.md` (new; this file)
- `00-START-NEXT-SESSION.md` (rewritten for SESSION_032)

---

## Verify

```bash
# Backend baseline held
cd backend && python3 manage.py test dealer_ai
# Expect: 1281 passed, 1 skipped, 0 failed

# No stale module-path refs in code
grep -rn 'freedom_ford' backend --include='*.py'
# Expect: only two matches — test method names in
# test_post_llm_safety.py that describe response content.

# All FREEDOM_FORD_ anchor doc refs updated (docs/handoffs/*
# and docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md still contain the
# name — those are historical + alternate-config reference and
# stay as-is)
grep -rn 'FREEDOM_FORD_\(SESSION_START\|BEHAVIOR_LAYER\|TRANSLATION_LAYER\)' \
  --exclude-dir=handoffs docs/
# Expect: only INDEPENDENT_DEALER_PIVOT.md (plan) and the
# DEALER_KIT_SESSION_START.md read-order bullet pointing at
# the franchise ONBOARDING_PLAN + FREEDOM_FORD_DEMO_SCRIPT.

# Frontend still clean
cd frontend && npx tsc --noEmit && npx vite build
```

---

## Guardrails carried forward (per `docs/INDEPENDENT_DEALER_PIVOT.md`)

- ❌ Do **not** delete the franchise config path. Franchise remains
  a supported *alternate* via
  `DEALER_AI_DEALER_TYPE=franchise` +
  `DEALER_AI_PRIMARY_MAKE=<OEM>` +
  `DEALER_AI_DEALER_NAME=<name>`.
- ❌ Do **not** reintroduce hardcoded "Sam Wampler" /
  "Dealer OS" / Ford-model strings in default paths.
- ❌ Do **not** change chat behavior contracts. 1281-test baseline
  stays green (+ new tests for any new features).
- ❌ Do **not** delete `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md` or
  `public/sams-freedom-ford-logo.jpg` — both are alternate-config
  reference material.
- ❌ Do **not** do dep-major upgrades concurrent with pivot work.
  React 19 / Tailwind 4 / Vite 8 / TypeScript 7 all deferred.
- ❌ Do **not** commit any real `OPENAI_API_KEY`.
- ✅ Do commit per subsystem, not per session. Bisectable diffs.

---

## Recommended SESSION_032

Full pivot is shipped. The three highest-value follow-ons (from
the pivot doc "deferred" lists):

1. **`DealerOnboardingProfile` indie-fields migration + onboarding
   form + `useBrand()` full-profile exposure.** The `DealerProfile`
   resolver in `dealer_ai/services/dealer_config.py` returns 7
   indie fields (`dealer_type`, `bhph_enabled`, `subprime_lenders`,
   `floor_plan_lender`, `warranty_offering`,
   `credit_range_served`, `makes_carried`) but they resolve
   only from env / defaults today. Migration adds the columns to
   `DealerOnboardingProfile`, form adds the inputs, and
   `useBrand()` exposes them to frontend consumers. Largest of
   the three; probably a full session on its own.

2. **`react-router-dom` 6 → 7 migration.** Clears 2 security
   advisories. Small routing-migration blast radius but does need
   a review — the pivot guardrail deferred it while pivot was
   in-flight, and it's now safe to unblock.

3. **Indie counterpart of `seed_phase3_demo` (dashboard population).**
   Non-blocking — the 4 hand-crafted Copper Canyon scenarios
   cover the manager demo needs. Would give admin-dashboard views
   more indie-flavored data.

Also worth considering (cosmetic tech-debt from Phase 5):

- Adopt-generated titles in `PROJECT_WHAT_IT_IS.md` / `BUILD_PLAN.md`
  still say *"Dealer OS — …"* because adopt derives project
  name from the git working directory (`freedom-ford/`). Full fix
  requires either a git-repo rename (large, out of scope) or a
  `context-kit adopt --project-name` flag.
- Move `public/sams-freedom-ford-logo.jpg` under
  `public/branding/franchise/` as an explicit alternate-config
  asset, per SESSION_030's own Phase 3 note.

---

## Operational state after SESSION_031

- **Backend (local):** Django on `:8001`. Package path
  `backend/dealer_kit/`. LLM = OpenAI `gpt-5-mini` (API key in
  repo-root `.env`).
- **Backend (prod):** `vehicle-match-api.onrender.com` — **NOT
  active**. `render.yaml` updated with new `dealer_kit.*` paths
  and will work on next deploy.
- **Frontend (local):** Vite on `:5173`. `useBrand()` returns
  `DEFAULT_DEALER` = Copper Canyon Auto (no `OnboardingProfile`
  yet).
- **Frontend (prod):** **NONE**.
- **Test baseline:** 1281 pass, 1 skipped, 0 fail.
- **Env overrides available for franchise config:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
