# SESSION 028 — VehicleMatch Rename + Frontend Deploy

**Date:** 2026-05-20
**Branch:** `main`
**GitHub:** `clwest/vehicle-match` (new repo, pushed from this local dir)
**Live URL (frontend):** https://vehicle-match-pi.vercel.app

## What changed

This dir is still `/Users/donkeyking/development/freedom-ford/` locally, but everything public moved to the **VehicleMatch** brand under `clwest/vehicle-match` on GitHub. The change happened during the 24/7 Global AI portfolio buildout, where this app is the Vertical VI · Match entry.

### Files added (deploy configs only — no source code touched)

- `render.yaml` — Render free Web Service Blueprint for the Django backend
- `backend/freedom_ford/prod_settings.py` — extends `settings.py` with WhiteNoise, env-driven hosts, CSRF trust, Render SSL proxy header
- `backend/render-requirements.txt` — prod-only deps (gunicorn, whitenoise) layered on top of `requirements.txt`
- `vercel.json` — Vite SPA build config (rootDirectory: frontend)
- `frontend/.env.production` — `VITE_API_BASE=https://vehicle-match-api.onrender.com/api/dealer-ai`

### Files NOT touched

The session deliberately did NOT modify the in-progress WIP files left over from session 027 (and earlier). Those remain dirty in the working tree:
- `00-START-NEXT-SESSION.md`, `README.md`, `backend/.env.example`, `backend/freedom_ford/settings.py`
- `docs/CONTEXT_KIT_INVENTORY.md`
- Several frontend TSX components (AssistantChat, AssistantBand, Hero, lib/api.ts, vite.config.ts, PublicAssistantPage)
- Untracked handoff stubs: SESSION_024–027

## Current deployment state

- **Frontend:** ✅ Live on Vercel via GitHub auto-deploy. `vehicle-match-pi.vercel.app` returns 200 OK.
- **Backend:** ⏳ Blueprint queued. Activate at https://render.com/deploy?repo=https://github.com/clwest/vehicle-match — zero extra config (SQLite ephemeral, Ollama fallback). Build takes ~3 min.

## What lights up after the Render click

The frontend already points its API calls at `vehicle-match-api.onrender.com`. The moment Render activates the Blueprint and the service shows "Live":
- Inventory loads from CSV seed data
- Lead capture POSTs work
- Manager dashboard fetches
- Chat returns the Ollama-fallback message ("trouble reaching the AI model right now") because Ollama isn't on Render — set `DEALER_AI_LLM_PROVIDER=openai` + `OPENAI_API_KEY=...` in Render dashboard to get real chat (~$5/mo expected)

## On the 24/7 landing

Card lives in `src/lib/products.ts` of the `24-7-ai-global` repo under VERTICALS. Current state:
- `status: "demo-ready"`
- `subStatus: "Frontend Live"`
- `url: "https://vehicle-match-pi.vercel.app"`
- `repo: "https://github.com/clwest/vehicle-match"`

After the backend goes live and is smoke-tested, flip to `status: "shipped"`, `subStatus: "Demo Tier"`, and update the `note` field.
