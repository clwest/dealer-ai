# Start Next Session — Phase 8l → Phase 8m+ Handoff

## Where we are

Phases 1 through 8l are complete. **253 backend tests pass.** TypeScript
clean. Live `/dealer-ai-demo` and `/dealer-ai-admin` both serve. Demo
inventory is now 55 vehicles across 9 makes (Ford 27, Toyota 7, Chevrolet
6, Honda 4, GMC 3, Nissan 3, Ram 2, Jeep 2, Kia 1) — multiple fit /
near-fit options exist at every common $/mo target.

Read `context/WHAT_IT_IS.md` and `context/INVENTORY.md` first. Read
`context/DO_NOTS.md` before changing `chat_engine.py`,
`intent_parser.py`, `inventory_search.py`, `payment_engine.py`, or the
post-LLM scrubs.

## How to run locally

```bash
# Backend (already on :8001 in the dev session)
cd backend
source .venv/bin/activate
python manage.py migrate
python manage.py seed_demo_vehicles      # 55 vehicles
python manage.py seed_demo_scenarios     # 5 scripted leads (optional)
python manage.py runserver 0.0.0.0:8001  # :8000 is taken by another local service

# LLM (Ollama default)
ollama serve                              # llama3.2 is what's pulled here

# Frontend (separate terminal, on :5173 with proxy → :8001)
cd frontend
npm install
npm run dev
```

`backend/.env` already exists with `OLLAMA_MODEL=llama3.2` (overrides the
shipped `.env.example` default of `llama3.1`). `frontend/.env.local`
already exists with `VITE_API_PROXY_TARGET=http://localhost:8001`.

## Tests

```bash
cd backend && source .venv/bin/activate
python manage.py test dealer_ai          # 253 tests, ~0.5s

cd frontend
npx tsc --noEmit                         # type-check (no runner installed)
npx vite build                           # production bundle
```

## What is locked in (do not undo unless explicitly asked)

- **Budget classification** with `fit / near_fit / over_budget`, where
  `near_fit = payment <= target + max($75, 15%)`. Tests in
  `test_near_fit.py` lock the math.
- **Term-aware narrowing** — never suggests a term ≤ current. Tests in
  `test_term_narrowing.py` lock the matrix.
- **Pre-LLM guard** for prompt injection / dealer cost / rate inquiry —
  short-circuits before any LLM call. Tests in `test_prompt_guard.py`
  and `test_wac_compliance.py`.
- **Post-LLM safety** — `detect_unsafe_response`, `scrub_rate_language`,
  and `check_payment_consistency` run in that order. Tests in
  `test_post_llm_safety.py`, `test_wac_compliance.py`,
  `test_payment_consistency.py`.
- **Multi-brand used inventory** with `make_lock` and Ford-first ranking.
  Tests in `test_multi_brand.py`.
- **Conversation flow** rules (one question per turn, varied phrasing,
  context-matched follow-ups). Tests in `test_conversation_flow.py`.
- **Trim redundancy** suppression — single vehicle / same-trim sets
  don't trigger trim commentary. Tests in `test_trim_redundancy.py`.
- **API shapes** — never broken since Phase 1. New audit data lives
  inside `ChatMessage.metadata` (e.g. `flag`, `budget_query.*`,
  `payment_drift`).

## What's open / interesting for next session

(Not bugs — these are surfaces with room to grow.)

- The vehicle-detail / vehicle-ask path (`vehicle_assistant.py`) still
  uses its own narrative blocks (`_payment_math_block`,
  `_affordability_notes`). Those are W.A.C.-clean as of Phase 8h, but
  they don't yet share the `BudgetContext` or the per-vehicle
  annotations from `chat_engine`. If a customer asks about a vehicle
  with a budget already in their session profile, the vehicle-ask LLM
  reply could quote a different default-term estimate than the chat's
  BUDGET ANALYSIS estimate. Worth aligning if Phase 8m has time.
- `seed_demo_scenarios` was hand-crafted before the multi-brand seed
  expanded. Two scenarios reference vehicles that still exist (good)
  but the seeded chat copy could mention the new alternatives if a
  scenario is reseeded.
- Frontend has no test runner installed. `tsc --noEmit` and `vite build`
  are the lint contract. If the next phase wants real assertions on
  React behavior, install `vitest` + `@testing-library/react` first.

## Quick smoke commands

```bash
# Live admin trends
curl -sS http://localhost:5173/api/dealer-ai/admin/trends/ | python -m json.tool | head -20

# Reset demo state without touching CSV imports
curl -sS -X POST http://localhost:5173/api/dealer-ai/demo/reset/ \
  -H "Content-Type: application/json" -d '{}'

# Reload scripted scenarios
curl -sS -X POST http://localhost:5173/api/dealer-ai/demo/scenarios/ \
  -H "Content-Type: application/json" -d '{"reset": true}'
```

## If anything feels off

- 253 tests + tsc + vite-build is the gate. If any of those break,
  the change is wrong.
- The metadata flag distribution on `ChatMessage` tells you which
  guards fired during a session. Useful for diagnosing odd replies.
- Original (unsafe / drifted) LLM output only lives in server logs,
  never in DB. Check `logger.warning` lines under
  `dealer_ai.services.chat_engine`.
