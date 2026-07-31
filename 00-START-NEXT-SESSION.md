---
state: active
date: 2026-07-30
last_session_shipped: SESSION_028
next_session: SESSION_029
---

# Next session — Dealer AI Kit / VehicleMatch

> **Platform + brand reframe:** The codebase is the **Dealer AI Kit** — a
> reusable dealer AI platform. Sam Wampler's Freedom Ford McAlester is
> Dealer #1 and the default configuration. The **public brand is
> VehicleMatch** (`clwest/vehicle-match` on GitHub, live at
> https://vehicle-match-pi.vercel.app), the Vertical VI · Match entry
> in the 24/7 Global AI portfolio. Local repo path is still
> `freedom-ford/`. See `docs/PLATFORM_REFRAME.md` for identity hierarchy
> and `docs/DEALER_DUPLICATION_GUIDE.md` for the onboard-a-second-dealer
> workflow.

## What just shipped

### SESSION_028 (2026-05-20) — VehicleMatch rename + deploy configs

- New repo `clwest/vehicle-match`; frontend live on Vercel at
  `vehicle-match-pi.vercel.app`.
- Deploy configs added: `render.yaml`, `backend/freedom_ford/prod_settings.py`,
  `backend/render-requirements.txt`, `vercel.json`, `frontend/.env.production`.
- **Backend Render Blueprint is queued but NOT activated.** The
  frontend points at `vehicle-match-api.onrender.com`, which currently
  returns `x-render-routing: no-server` (no service exists at that
  hostname). Activate at:
  https://render.com/deploy?repo=https://github.com/clwest/vehicle-match

Full handoff: `docs/handoffs/SESSION_028_vehicle_match_rename_and_deploy.md`.

### Between-sessions cleanup (2026-07-30, unnumbered maintenance)

Audit found that the SESSION_024 handoff claimed a "Presentation-only
matched-vehicle deck" was shipped, but the deck (+ softer public copy)
was still uncommitted in the working tree. Cleanup shipped four commits
on top of `dd08d47`:

- `4d9bac3` — **feat: land SESSION_024 public assistant polish** —
  belatedly commits the `VehicleMatchDeck` (3-card stack, prev/next
  controls) in `AssistantChat`, the "current inventory / payment-aware"
  copy in `AssistantBand` + `Hero`, and the `min-w-0` guard on
  `PublicAssistantPage`.
- `d8f6af9` — **docs: backfill session handoffs 024-027** — commits the
  four handoff docs that had been left untracked when `c2c2067` shipped.
- `d516958` — **chore: normalize dev host to 127.0.0.1 + expand CORS
  defaults** — Vite proxy target + CORS defaults now use `127.0.0.1`
  instead of `localhost` (avoids IPv6 resolution breaking the /api
  proxy). Reverted a WIP `api.ts` change that would have bypassed the
  Vite proxy and pinned port 8000 while Django runs on `:8001`.
- `d0e80fc` — **chore: ignore redesign/ scratch dir and vercel-link
  artifacts** — `/redesign/` (before/after competitor screenshots) and
  `frontend/.vercel/` are now gitignored.

Verification during cleanup:

- `python3 manage.py test dealer_ai.tests.test_embed_frame_policy
  dealer_ai.tests.test_onboarding_profile` — **18 tests pass** (matches
  SESSION_026/027 claims).
- `npx tsc --noEmit` — pass (once `npm install` ran; `node_modules` was
  missing).
- `npx vite build` — pass, 488.61 kB bundle / 133.78 kB gzip.
- `curl -sI https://vehicle-match-pi.vercel.app/` — 200, SPA HTML with
  correct `<title>`.
- `curl -sI https://vehicle-match-api.onrender.com/` — 404,
  `x-render-routing: no-server` (blueprint not activated).

---

## Recommended next session — SESSION_029

**Activate the Render backend and unblock end-to-end demo.**

The live frontend at `vehicle-match-pi.vercel.app` currently has
nothing to call. Every API request fails silently against a Render
placeholder. Highest-value next step is turning the backend on and
fixing the CORS mismatch that will hit the moment it comes up.

### Scope

1. **Fix `render.yaml` CORS before activation.** It allowlists
   `https://vehicle-match.vercel.app` — the real live host is
   `https://vehicle-match-pi.vercel.app` (note the `-pi` suffix Vercel
   appended when the project was linked). Same fix needed for
   `CSRF_TRUSTED_ORIGINS`.
2. **Click the Render Blueprint deploy button** for the fixed config.
3. **Smoke-test** once the service reports Live:
   - `GET /api/dealer-ai/inventory/` returns real seed data.
   - Frontend at `vehicle-match-pi.vercel.app` loads inventory cards
     and the assistant page without console errors.
   - Chat returns the expected Ollama-fallback message ("trouble
     reaching the AI model right now") since Ollama isn't on Render.
4. **Decide LLM story for the live demo.** Options:
   - Leave Ollama fallback in place (chat is degraded but everything
     else works).
   - Set `DEALER_AI_LLM_PROVIDER=openai` + `OPENAI_API_KEY` in Render
     dashboard for real chat (~$5/mo).

### Deferred (call these out at end of SESSION_029)

- **Inventory data quality cleanup** — originally the SESSION_028 plan
  that got pivoted to rename/deploy. Still relevant for demo polish
  once backend is up.
- **Adopt placeholders** in `docs/PROJECT_WHAT_IT_IS.md` (Why it
  exists / Who it's for) and `docs/BUILD_PLAN.md`. Doctor still warns.
- **Missing handoffs SESSION_004–007.** Either they never existed and
  the numbering skipped, or the docs were lost. Worth annotating
  explicitly.
- **Live brand broadcast on Setup save** — deferred from earlier.

## NEXT TASK

Fix `render.yaml` CORS + activate Render Blueprint + smoke-test the
live end-to-end pipeline.

**Strict guardrails:**

- ❌ Do not change `DEFAULT_DEALER` / `PRODUCT` / `defaultDealer.ts`.
- ❌ Do not change chat behavior.
- ❌ Do not add CRM/email/SMS.
- ❌ Do not push force / rewrite history on `main`.
- ❌ Do not commit any real `OPENAI_API_KEY` — set it via the Render
  dashboard only.

---

## Agent launch prompt for SESSION_029

Paste into Claude Code / Cursor / any AI coding agent as the session
opener.

```text
You are picking up SESSION_029 on the Dealer AI Kit / VehicleMatch.
Sam Wampler's Freedom Ford McAlester is Dealer #1 / default.

Read first:
- context-kit orient
- 00-START-NEXT-SESSION.md
- docs/handoffs/SESSION_028_vehicle_match_rename_and_deploy.md
- render.yaml
- backend/freedom_ford/prod_settings.py
- docs/PLATFORM_REFRAME.md

Goal:
Activate the Render backend and unblock end-to-end demo for the live
frontend at https://vehicle-match-pi.vercel.app.

Tasks:
1. Fix render.yaml so CORS_ALLOWED_ORIGINS and CSRF_TRUSTED_ORIGINS
   include https://vehicle-match-pi.vercel.app (not just the un-suffixed
   vehicle-match.vercel.app). Commit and push.
2. Ask user to click the Render Blueprint deploy button:
   https://render.com/deploy?repo=https://github.com/clwest/vehicle-match
3. Poll vehicle-match-api.onrender.com until it returns Django responses
   (build takes ~3 min).
4. Smoke-test /api/dealer-ai/inventory/ returns seed data.
5. Load https://vehicle-match-pi.vercel.app in a browser (or Playwright)
   and confirm inventory cards render + assistant page loads without
   console errors.
6. Confirm chat returns Ollama-fallback message OR ask user whether to
   flip DEALER_AI_LLM_PROVIDER=openai in Render dashboard.

Do NOT:
- change DEFAULT_DEALER / PRODUCT / defaultDealer.ts
- change chat behavior
- add CRM/email/SMS work
- commit any real API keys

Verify:
- curl vehicle-match-api.onrender.com returns Django (not Render 404)
- vehicle-match-pi.vercel.app loads inventory without CORS errors

When complete:
- Write docs/handoffs/SESSION_029_<slug>.md.
- Overwrite 00-START-NEXT-SESSION.md for the following session.
```

---

## Operational state

- **Backend (local)**: Django expected on `:8001`, Ollama llama3.2 on `:11434`.
- **Backend (prod)**: `vehicle-match-api.onrender.com` — **NOT active**
  as of 2026-07-30. Blueprint deploy pending.
- **Frontend (local)**: Vite expected on `:5173`.
- **Frontend (prod)**: https://vehicle-match-pi.vercel.app — live.
- **Public routes**:
  - `/` — assistant-first dealership homepage.
  - `/assistant` — full-page public assistant.
  - `/showroom` — public demo showroom.
  - `/embed/assistant` — standalone embeddable assistant.
- **Operator routes**:
  - `/dealer-ai-overview`
  - `/dealer-ai-live-assistant`
  - `/dealer-ai-inventory`
  - `/dealer-ai-leads`
  - `/dealer-ai-manager-chat`
  - `/dealer-ai-admin/team`
  - `/dealer-ai-onboarding`
  - `/dealer-ai-demo` — legacy lab, off-nav.

## Identity quick-reference

| Layer | Source | Examples |
| --- | --- | --- |
| **Product** | `PRODUCT` in `frontend/src/config/defaultDealer.ts` | Sidebar caption "DEALER AI KIT", embed "Powered by AI Sales Assistant", `<title>` prefix |
| **Default dealer** (fallback) | `DEFAULT_DEALER` in same file | `logoPath` fallback, name "Sam Wampler's Freedom Ford", location "McAlester", tagline "Sam Wampler Make It Happen" |
| **Active dealer** (runtime) | `OnboardingProfile` via `useBrand()` | Public nav/header/footer, assistant welcome lines, embed brand bar |

Resolution: `OnboardingProfile.logo_url || DEFAULT_DEALER.logoPath`
for the logo; `OnboardingProfile.<field> || DEFAULT_DEALER.<field>`
for supported identity fields.

## Anchors that win on conflict

If anything in this file disagrees with reality:

1. The latest handoff (`docs/handoffs/SESSION_028_*.md`).
2. `git log --oneline -10` (what actually shipped).
3. `git show HEAD:frontend/src/<path>` (current source).

Narrative docs are claims. Code and handoffs are facts.
