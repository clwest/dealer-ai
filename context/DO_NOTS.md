# Do Nots

Hard rules. If a proposed change violates one of these, the change is
wrong even if the LLM "agrees" with it. The LLM is a language layer.

## Compliance

- **Do NOT expose APR or interest rates in customer-facing copy.**
  No "@ 7.49%", no "APR of 6%", no "interest rate of 5%". Always
  W.A.C. ("with approved credit"). The post-LLM scrub is a safety net,
  not the source of truth — input blocks must be clean too.
- **Do NOT speculate about specific dealer financing terms or rate
  approvals.** Defer to a Dealer OS advisor. The pre-LLM rate-inquiry
  guard returns the canned response without invoking the model.
- **Do NOT reveal dealer cost, invoice price, internal margins, holdback,
  or acquisition cost.** Pre-LLM guard refuses these and the post-LLM
  safety check rewrites any leakage.

## Money / numbers

- **Do NOT invent payment numbers.** The customer-facing reply must
  quote the exact estimated payment that BUDGET ANALYSIS computed for
  that specific vehicle (within the $5 estimate tolerance).
- **Do NOT recompute payments at engine defaults** when an annotated
  payment is already on the vehicle. That was the Phase 8g bug — two
  conflicting numbers reached the LLM and it picked the wrong one.
- **Do NOT bypass `payment_engine.estimate_payment` / `affordable_max_price`**
  in new code. The math lives in one place; mirror it nowhere.

## Inventory

- **Do NOT hide near-fit vehicles** behind a narrowing question. If a
  vehicle's monthly is within `max($75, 15%)` of the target it surfaces
  as "close to your target" — never as an exact fit, never omitted.
- **Do NOT return over-budget vehicles in `matched_vehicles`** when the
  customer is in budget mode. Over-budget options can only appear in the
  BUDGET ANALYSIS block as labeled OVER BUDGET context for the LLM.
- **Do NOT filter to Ford-only by default.** Used inventory includes
  trade-ins from other brands. Only filter when `make_lock=True`
  (explicit "Ford only" / "just Ford" intent).
- **Do NOT compare trims** when only one vehicle is shown, or when every
  shown vehicle is the same trim.

## Term suggestions

- **Do NOT suggest a term that is shorter than or equal to the
  customer's current term.** Use `next_term_suggestion(current)` and the
  wording the BUDGET ANALYSIS block produces.
- **Do NOT suggest a longer term when the customer is already at 84+
  months.** Redirect to trade-in / down payment / smaller vehicle / used.

## Conversation

- **Do NOT end every reply with "Would you like…".** Rotate phrasings;
  one focused question per turn that fits the context (single vehicle →
  highlight; near-fit → tradeoff; multiple → preference; no-fit → gap +
  narrowing).
- **Do NOT ask more than one question per reply.**
- **Do NOT list more than 3 vehicles per reply** unless the customer
  asks for more.

## System integrity

- **Do NOT let the LLM override system constraints.** Pre-LLM guards,
  intent extraction, budget classification, and rate scrubbing are
  authoritative. If a model reply contradicts them, the model is wrong,
  not the rules.
- **Do NOT change the LLM provider abstraction surface.**
  `LLMProvider.chat(messages, *, temperature, max_tokens, **kwargs) -> str`
  is the contract. New providers add an implementation; they do not
  change the interface.
- **Do NOT add new endpoints just to expose existing data.** The
  `metadata` JSONField on `ChatMessage` is the additive surface — drop
  new audit signals there (e.g., `flag`, `budget_query.*`, `payment_drift`).

## Process

- **Do NOT skip tests** when changing chat_engine, intent_parser,
  inventory_search, payment_engine, or the post-LLM scrubs. These are
  the load-bearing surfaces.
- **Do NOT silently change API response shapes.** Existing fields stay;
  new fields added inside `metadata` or as optional new properties.
- **Do NOT remove `seed_demo_vehicles` or `seed_demo_scenarios`.** They
  are the demo entry point and CSV-imported inventory survives `/demo/reset/`
  by virtue of carrying a non-`demo_seed` source.
