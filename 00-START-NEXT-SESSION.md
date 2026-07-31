---
state: active
date: 2026-07-31
last_session_shipped: SESSION_031
next_session: SESSION_032
---

# Next session — SESSION_032 · post-pivot open work

> **Pivot status:** ✅ **Full pivot shipped.** All 5 phases complete
> across SESSION_030 (Phases 1–3, 19 commits `1a03a39` → `3e812ba`,
> baseline 1218 → 1281) and SESSION_031 (Phase 4 rename `0ec372a`
> + Phase 5 docs refresh, baseline held at 1281). Copper Canyon
> Auto is the shipped default persona; franchise config preserved
> as a supported alternate via env overrides. Living plan +
> per-phase status: `docs/INDEPENDENT_DEALER_PIVOT.md`. Formal
> handoffs at
> `docs/handoffs/SESSION_030_independent_dealer_pivot.md` and
> `docs/handoffs/SESSION_031_pivot_phase4_5.md`.

## What just shipped (SESSION_031)

Two discrete phases in one session — see the handoff for full
per-file detail:

### Phase 4 — Django package rename (`0ec372a`, 1 commit)

- `git mv backend/freedom_ford backend/dealer_kit` (7 files,
  history preserved).
- 11-line edits across `dealer_kit/{settings,wsgi,asgi}.py`,
  `manage.py`, `smoke_drift_audit.py`, `render.yaml` to swap
  `freedom_ford.*` → `dealer_kit.*` module paths.
- Test baseline held: **1281 pass, 1 skipped, 0 fail** (no drift).
- `prod_settings.py` uses relative imports — no edits needed.
- `.env.example` had no matching refs.
- Two `freedom_ford` references remain in
  `backend/dealer_ai/tests/test_post_llm_safety.py` — both are
  test *method names* about response content, not module paths.
  They run correctly under the new module and stay untouched.

### Phase 5 — Docs, `CLAUDE.md`, handoff (this commit)

- Renamed 3 anchor docs via `git mv`:
  - `docs/FREEDOM_FORD_SESSION_START.md` → `docs/DEALER_KIT_SESSION_START.md` (full rewrite)
  - `docs/FREEDOM_FORD_BEHAVIOR_LAYER.md` → `docs/DEALER_KIT_BEHAVIOR_LAYER.md` (surgical reframe; contracts preserved verbatim)
  - `docs/FREEDOM_FORD_TRANSLATION_LAYER.md` → `docs/DEALER_KIT_TRANSLATION_LAYER.md` (surgical reframe; personas, worked examples, Live Chat Mode contract preserved verbatim)
- Refreshed adopt-managed docs via
  `context-kit adopt . --write --project-summary ... --next-task ... --notes ...`:
  - `docs/PROJECT_WHAT_IT_IS.md` + hand-filled Why/Who
  - `docs/BUILD_PLAN.md`
  - `CLAUDE.md` adopt block (hand-written frontend stack notes
    below markers preserved unchanged; **Brand tokens** paragraph
    hand-edited to describe `brand.*` palette + Copper Canyon
    hex values + franchise-override callout).
- Cross-reference updates in `docs/CAPABILITY_MATRIX.md`,
  `docs/CONTEXT_KIT_INVENTORY.md`, `docs/DEALER_DUPLICATION_GUIDE.md`,
  `docs/onboarding/ASSISTANT_AGENT_CREATION_ROADMAP.md`, and
  `docs/INDEPENDENT_DEALER_PIVOT.md` (frontmatter status → shipped;
  Phase 4/5 status snapshot filled in).
- Wrote formal handoff `docs/handoffs/SESSION_031_pivot_phase4_5.md`.
- Overwrote this file for SESSION_032.

`context-kit adopt` correctly **skipped** `00-START-NEXT-SESSION.md`
because the file has no adopt markers — the hand-written
SESSION_032 priorities below are preserved.

## Recommended SESSION_032 — indie onboarding migration

Full pivot is shipped; nothing here is blocked on prior pivot
work. Pick the highest-value item that fits the session length.

### Top candidate — `DealerOnboardingProfile` indie-fields migration

**Why:** the `DealerProfile` resolver in
`backend/dealer_ai/services/dealer_config.py` returns 7 indie
fields (`dealer_type`, `bhph_enabled`, `subprime_lenders`,
`floor_plan_lender`, `warranty_offering`, `credit_range_served`,
`makes_carried`) but they resolve only from env / hardcoded
Copper Canyon defaults today. A real dealer running the kit
can't currently customize them via the onboarding UI —
onboarding still only saves the dealer *name* + the original
Freedom-Ford-era voice fields.

**Scope (probably a full session on its own):**

1. `DealerOnboardingProfile` migration — add the 7 columns +
   their sensible indie defaults.
2. Serializer + view — accept + return the new fields.
3. Onboarding form (`/dealer-ai-onboarding`) — add inputs (form
   sections: dealer type radio; BHPH toggle; subprime-lender
   list editor; floor-plan-lender text; warranty text; credit
   range text; makes-carried multi-select or text).
4. `dealer_config.get_dealer_profile()` — resolution order
   updated to prefer `DealerOnboardingProfile` field values over
   env / hardcoded defaults (mirroring the existing
   `get_dealer_name()` resolution pattern).
5. `useBrand()` — extend to expose the full profile, not just
   name / tagline / logo. Frontend consumers can then read
   `useBrand().dealerType`, etc. for conditional UI.
6. Tests — model, serializer, view, resolution-order, form
   integration. Target: 1281 + N pass.

### Also open (lower urgency, not blocking)

- **`react-router-dom` 6 → 7 migration.** Clears 2 security
  advisories. Small blast radius but does need a routing-migration
  review; deferred during pivot work is now unblocked.
- **Indie counterpart of `seed_phase3_demo`** (admin dashboard
  population variant). Non-blocking — the 4 hand-crafted Copper
  Canyon scenarios (`seed_copper_canyon_scenarios`) cover the
  manager demo needs; this would only enrich admin-dashboard views
  with more indie-flavored data.
- **Freedom Ford legacy JPG asset** —
  `public/sams-freedom-ford-logo.jpg` still lives at the top of
  `public/`. SESSION_030's own guardrail forbade deletion in
  Phase 3. Cleanest move: `git mv` it under
  `public/branding/franchise/` with a small README noting it's
  an alternate-config asset.
- **Cosmetic tech-debt (adopt-generated titles).**
  `docs/PROJECT_WHAT_IT_IS.md` and `docs/BUILD_PLAN.md` still
  say `# Freedom Ford — …` in their titles because
  `context-kit adopt` derives project name from the git working
  directory. Full fix requires either a git-repo rename (large,
  out of scope) or `context-kit adopt` growing a
  `--project-name` override flag. Leave alone for now.

## NEXT TASK

Start SESSION_032 with the **indie onboarding migration** if a
full session is available. If shorter, `react-router-dom 6 → 7`
is a self-contained afternoon.

**Strict guardrails carried forward (per `docs/INDEPENDENT_DEALER_PIVOT.md`):**

- ❌ Do NOT delete the franchise config path. Franchise stays a
  supported *configuration* via
  `DEALER_AI_DEALER_TYPE=franchise` +
  `DEALER_AI_PRIMARY_MAKE=<OEM>` +
  `DEALER_AI_DEALER_NAME=<name>`.
- ❌ Do NOT reintroduce hardcoded "Sam Wampler" / "Freedom Ford" /
  Ford-model strings in default paths.
- ❌ Do NOT change chat behavior contracts. 1281-test baseline
  must stay green (plus new tests for anything added).
- ❌ Do NOT delete `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md` or
  `public/sams-freedom-ford-logo.jpg` (may move the JPG — see
  above — but do not delete).
- ❌ Do NOT do dep-major upgrades concurrent with other feature
  work. If picking the react-router-dom 6→7 migration, do that
  as its own commit / session.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.

---

## Agent launch prompt for SESSION_032

Paste into Claude Code / Cursor / any AI coding agent as the
session opener.

```text
You are picking up SESSION_032 on the Dealer AI Kit. The
independent-dealer pivot shipped end-to-end across SESSION_030
(Phases 1–3, backend + seed data + frontend tokens) and
SESSION_031 (Phase 4 Django backend/freedom_ford → backend/dealer_kit
rename, Phase 5 docs + CLAUDE.md refresh). Copper Canyon Auto is
the default persona; franchise supported via env overrides. Full
plan + status: docs/INDEPENDENT_DEALER_PIVOT.md.

Read first:
- context-kit orient
- 00-START-NEXT-SESSION.md
- docs/DEALER_KIT_SESSION_START.md
- docs/handoffs/SESSION_031_pivot_phase4_5.md
- docs/INDEPENDENT_DEALER_PIVOT.md

Goal (top candidate): DealerOnboardingProfile indie-fields
migration. The DealerProfile resolver in
backend/dealer_ai/services/dealer_config.py returns 7 indie
fields but they only resolve from env / hardcoded defaults. Add
the columns + form inputs + resolution order + tests so a real
dealer can customize their profile via the onboarding UI.

Alternate goals (if shorter session):
- react-router-dom 6 → 7 migration (clears 2 security advisories).
- Indie counterpart of seed_phase3_demo (admin dashboard data).
- Move public/sams-freedom-ford-logo.jpg to public/branding/franchise/.

Local dev setup:
1. LLM provider is OpenAI gpt-5-mini — API key in repo-root
   .env (untracked).
2. Django on :8001, Vite on :5173. Start both if not running.
3. Backend baseline: python3 manage.py test dealer_ai → 1281
   pass, 1 skipped.
4. Django project package is backend/dealer_kit/ (as of
   SESSION_031 Phase 4).

Do NOT:
- Delete the franchise config path (franchise is still
  supported via DEALER_AI_DEALER_TYPE=franchise +
  DEALER_AI_PRIMARY_MAKE=<OEM>).
- Reintroduce hardcoded "Sam Wampler" / "Freedom Ford" strings
  in default paths.
- Change chat behavior contracts. Keep 1281-test baseline.
- Do dep-major upgrades concurrent with feature work.
- Commit any real API keys.
```

---

## Operational state carried from SESSION_031

- **Backend (local):** Django on `:8001`. Package path
  `backend/dealer_kit/` (as of SESSION_031 Phase 4). LLM
  provider = OpenAI `gpt-5-mini` (API key in repo-root `.env`).
- **Backend (prod):** `vehicle-match-api.onrender.com` — **NOT
  active**. `render.yaml` updated with new `dealer_kit.*` paths
  and ready to deploy.
- **Frontend (local):** Vite on `:5173`. `useBrand()` returns
  `DEFAULT_DEALER` = Copper Canyon Auto values (no
  `OnboardingProfile` yet — that's SESSION_032's top candidate).
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
- **Test baseline:** 1281 pass, 1 skipped, 0 fail.
- **Env overrides available for franchise config:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.

## Anchors that win on conflict

If anything here disagrees with reality:

1. `docs/INDEPENDENT_DEALER_PIVOT.md` — pivot living plan.
2. `docs/handoffs/SESSION_031_pivot_phase4_5.md` — most recent handoff.
3. `docs/handoffs/SESSION_030_independent_dealer_pivot.md` — pivot Phases 1–3.
4. `git log --oneline -25` (what actually shipped).
5. `git show HEAD:<path>` (current source).

Narrative docs are claims. Code and handoffs are facts.
