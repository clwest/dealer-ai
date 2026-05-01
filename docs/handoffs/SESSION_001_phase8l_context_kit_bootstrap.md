---
date: 2026-05-01
phase: 8l → 8m
title: Context-kit bootstrap + Phase 8l exit state
---

# Session handoff — context-kit bootstrap

## What shipped this session

- Located `contextkit-ai 0.15.0` at `/Users/donkeyking/development/context-kit`
- Installed editable into `backend/.venv` (`pip install -e <path>`)
- Ran `context-kit adopt . --write` with project summary + next-task + notes
  - Wrote `00-START-NEXT-SESSION.md`, `CLAUDE.md`, `docs/BUILD_PLAN.md`,
    `docs/PROJECT_WHAT_IT_IS.md`
- Created the spec-required kit at `context/`:
  - `context/WHAT_IT_IS.md` — narrative anchor (LLM is a language layer; the
    backend owns budget realism, near-fit, W.A.C., guards, multi-brand)
  - `context/INVENTORY.md` — current behavior matrix (term math, budget
    classification, payment-copy consistency, pre/post-LLM safety, multi-brand,
    conversation flow, trim redundancy, demo dataset, API surface, provider)
  - `context/DO_NOTS.md` — hard rules (no APR / no invented payments / no
    over-budget in matched / no shorter-or-equal term suggestions / one
    question per turn / metadata-only audit additions / never bypass the
    payment_engine)
  - `context/HANDOFFS/00-START-NEXT-SESSION.md` — long-form handoff (run
    commands, locked-in behaviors, tests gate, open surfaces)
- Generated `docs/CONTEXT_KIT_INVENTORY.md` via `context-kit inventory --write`

## State at end of session

- 253 backend tests passing (`python manage.py test dealer_ai`)
- Frontend `tsc --noEmit` clean; `vite build` clean
- 55 demo vehicles seeded across 9 makes (Phase 8l)
- Live servers still running on `:8001` (Django) and `:5173` (Vite)
- No application code touched in this session

## Next-session priorities

The next AI session should read in order:

1. `context/WHAT_IT_IS.md`
2. `context/INVENTORY.md`
3. `context/DO_NOTS.md`
4. `context/HANDOFFS/00-START-NEXT-SESSION.md`
5. `docs/PROJECT_WHAT_IT_IS.md` and the adopt-generated `00-START-NEXT-SESSION.md`
   at the repo root for the agent-launch prompt

Then proceed with Phase 8m+ (the user has not yet defined that phase). Open
surfaces noted in `context/HANDOFFS/00-START-NEXT-SESSION.md`:

- `vehicle_assistant.py` doesn't share `BudgetContext` with `chat_engine` —
  the vehicle-ask path could quote a different default-term estimate than
  the chat's BUDGET ANALYSIS for the same vehicle when the customer has a
  budget in their session profile
- `seed_demo_scenarios` predates the multi-brand inventory expansion;
  scripted scenarios still reference Ford-only vehicles
- Frontend has no test runner — only `tsc` + `vite build` are the lint gate

## Do-not list (full rules in `context/DO_NOTS.md`)

- Never expose APR / interest rates in customer-facing copy
- Never invent payment numbers; quote backend estimates exactly
- Never hide near-fit vehicles
- Never compare trims for a single vehicle
- Never suggest a term ≤ the customer's current term
- Never let the LLM override pre/post-LLM guards
