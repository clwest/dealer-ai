# Inventory of Current Behavior

The behaviors below are implemented and locked by tests
(`backend/dealer_ai/tests/`). 253 backend tests pass as of Phase 8l.

## Term math

- **Default term**: 60 months when the customer hasn't said one.
- **Term expansion (narrowing question)**: only suggests terms strictly
  longer than the current one.
  - `< 60` → suggest "60, 72, or 84 months"
  - `< 72` → suggest "72 or 84 months"
  - `< 84` → suggest "84 months"
  - `>= 84` → do **not** suggest a longer term; redirect to trade-in,
    larger down, smaller vehicle, or used.
- **Term parsing**: regex extracts both `5 years` (→60) and `60 months`,
  clamped to the 12-96 range.

## Budget classification

For each candidate, `payment_engine.estimate_payment(price, down, term)`
computes the monthly. Buckets:

| Bucket | Rule |
| --- | --- |
| `fit` | `payment <= target` |
| `near_fit` | `payment <= target + max($75, 15% of target)` |
| `over_budget` | anything above the near-fit ceiling |

The chat response surfaces `in_budget + near_fit` as `matched_vehicles`.
`closest_above` is shown to the LLM as OVER BUDGET context **only** when
both `fit` and `near_fit` are empty.

Per-vehicle annotations (`_budget_fit`, `_estimated_payment`,
`_payment_delta`) flow through `VehicleSerializer` for the frontend cards.

## Payment-copy consistency

- The inventory block reuses the annotated payment from BUDGET ANALYSIS —
  it does NOT recompute at engine defaults. Two different numbers for the
  same vehicle was the Phase 8g bug.
- Post-LLM `check_payment_consistency` scans the reply for `$X/mo`
  amounts. Anything not within $1 of the customer's target or $5 of any
  backend estimate is logged + flagged as `payment_drift`.
- The metadata key `assistant_message.metadata.budget_query.payment_drift`
  records any drift for dashboard surfacing.

## Pre-LLM guard (short-circuit, no model call)

Triggers and canned responses:

- **Prompt injection / dealer-cost**: detect_unsafe_request → `GUARD_RESPONSE`,
  `flag = "prompt_injection"`. Inventory search still runs so the customer
  sees real options alongside the refusal.
- **Rate inquiry** ("what's the APR / interest rate / what rate do I qualify
  for"): `RATE_INQUIRY_RESPONSE`, `flag = "rate_inquiry"`.

## Post-LLM safety

In order, applied to the model's draft reply:

1. `detect_unsafe_response` — if the model leaked dealer-cost / invoice
   language, body is replaced with `GUARD_RESPONSE`,
   `flag = "post_llm_safety_rewrite"`. Original text only in server logs.
2. `scrub_rate_language` — strips `@ X.XX%`, `APR of X%`, `interest rate
   of X%`, bare `APR`, bare `interest rate`. Replacement uses W.A.C.
   phrasing. Sets `flag = "rate_language_scrubbed"` when fired.
3. `check_payment_consistency` — non-rewriting drift detector. Logs and
   flags but never edits the body.

## Rate compliance (W.A.C.)

Customer-facing copy never states a rate / APR / financing percentage.
- SYSTEM_PROMPT bans rate language and tells the model to use
  "(W.A.C. — with approved credit)".
- BUDGET ANALYSIS block: never includes a percentage.
- Inventory block: payment lines say `est ~$X/mo for N months (W.A.C.)`.
- Vehicle detail modal payment table has Term + Down + Estimated monthly
  columns; no APR column.

## Multi-brand used inventory

- Default behavior: `make` is **not** filtered. Used inventory includes
  trade-ins from other brands.
- `make_lock = True` (set by intent_parser when the customer says "Ford
  only" / "I want a Ford" / "just Ford") restricts the candidate query to
  one make.
- **Ford-first ranking**: in budget mode and in `search_vehicles`, the
  Python-level sort puts Ford ahead of every other brand at equal
  classification.
- 13 brand aliases recognized (Ford, Toyota, Honda, Chevrolet/Chevy, Ram,
  Dodge, GMC, Nissan, Hyundai, Kia, Subaru, Mazda, Jeep, VW, BMW, Audi,
  Lexus, Tesla).

## Conversation flow

- Phrasing rotation: `Want me to…`, `I can also…`, `If you're open to…`,
  `We could also look at…` — the SYSTEM_PROMPT bans repetitive
  "Would you like…".
- Context-matched follow-up:
  - 1 vehicle → highlight it, no preference question
  - Near-fit → name the tradeoff, then ONE narrowing question
  - Multiple → preference question
  - No fit / no near-fit → explain gap, ONE narrowing question

## Trim redundancy

- 1 vehicle → "Do NOT explain or compare trim levels"
- Multiple vehicles, same trim → "no meaningful difference"
- Multiple vehicles, distinct trims → comparison allowed (no directive)

## Demo dataset

- `seed_demo_vehicles` — 55 entries across 9 makes (Ford 27, Toyota 7,
  Chevrolet 6, Honda 4, GMC 3, Nissan 3, Ram 2, Jeep 2, Kia 1).
- 21 trucks, 21 SUVs, 11 cars, 2 EVs.
- Price bands: <$15k (5), $15-25k (9), $25-35k (12), $35-50k (17),
  $50k+ (12). Multiple vehicles fit/near-fit at each $/mo target.
- `seed_demo_scenarios` — 5 scripted customer conversations preloaded for
  the demo dashboard.
- `source="demo_seed"` on every entry; CSV imports use a different source
  so `/demo/reset/` preserves them.

## API surface (no shape changes since Phase 1)

Customer:
- `POST /api/dealer-ai/chat/start/`, `/chat/message/`, `/leads/`
- `GET /api/dealer-ai/vehicles/<id>/`, `POST /vehicles/<id>/ask/`

Manager / dashboard:
- `GET /admin/trends/`, `/admin/leads/`, `/admin/lead/<id>/`,
  `/admin/chat-sessions/`, `/chat/session/<uuid>/`
- `POST /admin/lead/<id>/handoff/`

Demo control:
- `POST /demo/reset/`, `POST /demo/scenarios/`

The `metadata` JSON on `ChatMessage` is the additive surface for new
audit data — it has accumulated `flag`, `budget_query.*`,
`extracted_this_turn`, `provider`, `payment_drift` over Phase 8.

## LLM provider

- Default: Ollama local (`llama3.2` is what's actually pulled on this
  machine; `OLLAMA_MODEL` in `backend/.env` can switch).
- Switchable to OpenAI via `DEALER_AI_LLM_PROVIDER=openai` + `OPENAI_API_KEY`.
- Provider abstraction lives in `services/llm/{base,ollama,openai_provider,factory}.py`.
- Tests use `MockLLMProvider` from `tests/_mocks.py`; never hits a real model.
