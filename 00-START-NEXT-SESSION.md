---
state: active
date: 2026-07-30
last_session_shipped: SESSION_029
next_session: SESSION_030
---

# Next session — Dealer AI Kit (rebrand in progress)

> **Rebrand status:** The kit is mid-rebrand. Tier 1 (all
> user-visible "Sam Wampler" / "Freedom Ford" text) shipped in
> SESSION_029 via runtime templating. Tier 2 (seed data — every
> demo vehicle is still a Ford) and Tier 3 (identifiers — Tailwind
> tokens, module path, logo asset, filename) are open. See
> `docs/handoffs/SESSION_029_audit_openai_and_tier1_rebrand.md`.

## What just shipped (SESSION_029)

Three phases in one session — see the full handoff at
`docs/handoffs/SESSION_029_audit_openai_and_tier1_rebrand.md`:

### 1. Cleanup audit (5 commits)

Verified prior handoff claims against runtime state. Landed
uncommitted SESSION_024 UI polish (`4d9bac3`), backfilled untracked
handoff docs 024–027 (`d8f6af9`), normalized dev host to
`127.0.0.1` (`d516958`), added `redesign/` + `frontend/.vercel/`
to gitignore (`d0e80fc`), refreshed context-kit docs (`9754830`).

### 2. LLM provider swap → OpenAI `gpt-5-mini` (`76a5f2e`)

- `openai_provider.py` gained reasoning-model branch: gpt-5 /
  o1 / o3 / o4 use `max_completion_tokens` (not `max_tokens`),
  drop non-default `temperature`, and get a larger budget to
  leave room for reasoning tokens.
- Django `settings.py` now loads both `backend/.env` and
  repo-root `.env` with `override=True`. `OPENAI_API_KEY` lives
  in the untracked repo-root `.env`.
- Live-tested: chat responds with real OpenAI content and the
  deterministic vehicle matcher still returns matched trucks.

### 3. Tier 1 rebrand (`71f5d48`)

- New `backend/dealer_ai/services/dealer_config.py` exposes
  `get_dealer_name()` — resolution order:
  `settings.DEALER_AI_DEALER_NAME` → `DealerOnboardingProfile
  .dealership_name` → `"the dealership"`.
- Every LLM prompt + hardcoded response constant in 6 backend
  services now contains `{dealer_name}` and is rendered at call
  time via a per-module `_render()` helper.
- Frontend components interpolate `brand.dealershipName` via
  `useBrand()`. `DEFAULT_DEALER` neutralized. `index.html`
  `<title>` de-branded.
- 46 tests fixed via `@override_settings(DEALER_AI_DEALER_NAME=
  "Freedom Ford")` + `_render(...)` wraps — **1218 pass, 1
  skipped preserved.**
- Live grep confirms zero "Sam Wampler" / "Freedom Ford" text
  in user-visible surfaces.

### Deployment state (unchanged during this session)

- Vercel frontend at `vehicle-match-pi.vercel.app` — **deleted**
  mid-session (via dashboard) to remove Sam-branded live URL
  during rebrand.
- Render backend — still not activated.
- Local dev only. GitHub repo `clwest/vehicle-match` intact.

---

## Recommended next session — SESSION_030

Three sensible tracks — pick one, or plug in a real dealer name
first (option A) and evaluate visually before committing to
scope.

### Option A — Configure a dealer name and evaluate

Fastest path to seeing the templating live. Two ways:

1. Set `DEALER_AI_DEALER_NAME=<name>` in `backend/.env` (or repo
   root `.env`), restart Django, done.
2. Open `/dealer-ai-onboarding` in the UI, fill in the
   `Dealership name` field, save.

Then walk `/`, `/assistant`, `/dealer-ai-overview`,
`/dealer-ai-admin` to see how the interpolated copy reads.

**Time:** ~15 min. No code changes required.

### Option B — Tier 2 rebrand (seed data)

Neutralize the demo vehicle inventory. Every seeded vehicle is
still a Ford (Maverick, Ranger, F-150, Bronco, Escape…). The
demo still visibly reads as a Ford dealer even though the
name/tagline are neutralized.

Scope:
- `backend/dealer_ai/management/commands/seed_demo_vehicles.py`
- `backend/dealer_ai/management/commands/seed_demo_scenarios.py`
- `backend/dealer_ai/management/commands/seed_phase3_demo.py`
- `frontend/src/data/freedomFordInventorySample.ts` (contents,
  not filename — filename is Tier 3)

Decision needed: replace with mixed-make sample inventory, or
make seed data configurable per dealer?

### Option C — Focus on the admin dashboard

The original ask that got derailed by the strip-then-revert
detour. `/dealer-ai-admin` is unreachable from the sidebar; only
`/dealer-ai-admin/team` is nav-linked. Add "Admin" to the nav,
then decide what to improve on that page (trends, pipeline,
handoff queue, audit panel, ad-copy generator, demo reset).

### Deferred (still valid, lower urgency)

- **Tier 3 rebrand** — Tailwind `ford.*` color tokens, backend
  `freedom_ford/` module path, `sams-freedom-ford-logo.jpg` asset,
  `freedomFordInventorySample.ts` filename.
- **SESSION_004–007 handoff gap** — either annotate as
  "never existed and numbering skipped" or fill placeholders.
- **Adopt placeholders** in `docs/PROJECT_WHAT_IT_IS.md` and
  `docs/BUILD_PLAN.md`.
- **`render.yaml` CORS hostname update** — only relevant if/when a
  new frontend gets deployed.

## NEXT TASK

Pick between Option A (evaluate templating with a real dealer
name), Option B (Tier 2 seed data rebrand), or Option C (admin
dashboard focus).

**Strict guardrails (all options):**

- ❌ Do not re-introduce hardcoded "Sam Wampler" / "Freedom Ford"
  strings — everything goes through `useBrand()` / `get_dealer_name()`.
- ❌ Do not delete or rename `backend/freedom_ford/` (Tier 3).
- ❌ Do not delete `sams-freedom-ford-logo.jpg` yet (Tier 3).
- ❌ Do not change chat behavior contracts (pre-LLM guards,
  post-LLM scrubs — 1218 tests must stay green).
- ❌ Do not commit any real `OPENAI_API_KEY`.

---

## Agent launch prompt for SESSION_030

Paste into Claude Code / Cursor / any AI coding agent as the
session opener.

```text
You are picking up SESSION_030 on the Dealer AI Kit. The kit is
mid-rebrand — Tier 1 (user-visible text) shipped last session via
runtime dealer-name templating.

Read first:
- context-kit orient
- 00-START-NEXT-SESSION.md
- docs/handoffs/SESSION_029_audit_openai_and_tier1_rebrand.md
- docs/FREEDOM_FORD_SESSION_START.md
- backend/dealer_ai/services/dealer_config.py

Goal:
Ask the user which track to pursue:
- Option A: configure a real dealer name and evaluate visually
- Option B: Tier 2 rebrand (seed data — vehicles + scenarios)
- Option C: focus on the /dealer-ai-admin dashboard

Local dev setup:
1. Ollama is OFF. LLM provider is OpenAI (gpt-5-mini) — API key
   in repo-root .env (untracked). Confirmed working end-to-end.
2. Django on :8001, Vite on :5173.
3. Backend uses OpenAIProvider with reasoning-model params.
4. DealerOnboardingProfile is currently empty →
   get_dealer_name() returns "the dealership" as fallback.

Do NOT:
- Re-introduce hardcoded "Sam Wampler" / "Freedom Ford" strings.
- Change chat behavior contracts (must keep 1218 tests green).
- Delete or rename backend/freedom_ford/ (Tier 3 scope).
- Commit any real API keys.

Verify (all options):
- python3 manage.py test → 1218 pass, 1 skipped
- npx tsc --noEmit → clean
- npx vite build → clean
- grep -rn "Sam Wampler\|Freedom Ford" frontend/src backend/dealer_ai/services
  → still zero (only historical docstring in dealer_config.py)

When complete:
- Write docs/handoffs/SESSION_030_<slug>.md.
- Overwrite 00-START-NEXT-SESSION.md for the next session.
```

---

## Operational state

- **Backend (local)**: Django on `:8001`, LLM provider = OpenAI
  `gpt-5-mini` (API key in repo-root `.env`).
- **Backend (prod)**: `vehicle-match-api.onrender.com` — **NOT
  active**. Blueprint deploy still pending.
- **Frontend (local)**: Vite on `:5173`. `useBrand()` returns
  `DEFAULT_DEALER` fallback (`"Your Dealership"`, empty tagline).
- **Frontend (prod)**: **NONE**. Vercel project was deleted
  during SESSION_029 to prevent Sam-branded URL from being live
  during rebrand.
- **Public routes**:
  - `/` — assistant-first dealership homepage (uses `useBrand()`)
  - `/assistant` — full-page public assistant
  - `/showroom` — public demo showroom
  - `/embed/assistant` — standalone embeddable assistant
- **Operator routes**:
  - `/dealer-ai-overview` (in sidebar)
  - `/dealer-ai-live-assistant` (in sidebar)
  - `/dealer-ai-inventory` (in sidebar)
  - `/dealer-ai-leads` (in sidebar)
  - `/dealer-ai-manager-chat` (in sidebar)
  - `/dealer-ai-admin` (**not in sidebar** — direct URL only)
  - `/dealer-ai-admin/team` (in sidebar)
  - `/dealer-ai-onboarding` (in sidebar)
  - `/dealer-ai-demo` — legacy lab, off-nav
  - `/dealer-ai-advisor/:slug` — per-advisor workspace

## Identity quick-reference

| Layer | Source | How it resolves |
| --- | --- | --- |
| **Product** | `PRODUCT` in `frontend/src/config/defaultDealer.ts` | Sidebar caption "DEALER AI KIT", `<title>` "Dealer AI Kit" |
| **Default dealer** (fallback) | `DEFAULT_DEALER` in same file | Neutralized: `"Your Dealership"`, empty location/tagline/brand/logo |
| **Active dealer** (frontend runtime) | `OnboardingProfile` via `useBrand()` | Overrides `DEFAULT_DEALER` field-by-field; currently empty in DB |
| **Active dealer** (backend runtime, LLM prompts) | `get_dealer_name()` in `dealer_ai.services.dealer_config` | env `DEALER_AI_DEALER_NAME` → `DealerOnboardingProfile.dealership_name` → `"the dealership"` |

## Anchors that win on conflict

If anything in this file disagrees with reality:

1. The latest handoff (`docs/handoffs/SESSION_029_*.md`).
2. `git log --oneline -10` (what actually shipped).
3. `git show HEAD:<path>` (current source).

Narrative docs are claims. Code and handoffs are facts.
