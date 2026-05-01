# What This Is

Freedom Ford Dealer AI is a **budget-constrained vehicle selection system**.

It is **not a chatbot**. The chat surface is a thin language layer over a
deterministic backend that does the actual work: parsing intent, computing
estimated payments, classifying vehicles by affordability, and producing
sales-handoff packets.

The LLM never makes pricing, eligibility, or compliance decisions. It only
phrases the answers.

## What the system enforces

These rules are owned by the backend and protected with regex guards,
pre-LLM short-circuits, and post-LLM scrubs — not by hoping the model
follows instructions.

- **Budget realism.** Every customer message that includes a $/month target
  is classified through `payment_engine.estimate_payment` against the
  actual vehicle prices. No vehicle reaches the customer unless it has been
  bucketed as `fit` or `near_fit` (or `over_budget` when there's nothing
  closer to show).
- **Near-fit logic.** Vehicles whose computed monthly payment is within
  `max($75, 15% of target)` of the target are surfaced as "close to your
  target" — never as exact fits.
- **No APR exposure (W.A.C.).** Rate language is stripped from system
  prompts, system blocks, the vehicle detail modal, and a post-LLM scrub
  catches model leakage. Customer-facing copy uses "with approved credit"
  qualification only.
- **No prompt injection.** Pre-LLM regex guard short-circuits to a canned
  refusal on injection attempts and dealer-cost / invoice-price questions
  before any model is invoked.
- **Multi-brand used inventory.** Used inventory includes Toyota / Honda /
  Chevy / GMC / etc. — Ford ranks first, but other brands appear in
  results unless the customer explicitly says "Ford only".
- **One narrowing question per turn.** When budget doesn't fit, the system
  asks exactly one focused question (longer term, more down, smaller
  vehicle, or used) — never a list of four.

## Where the LLM fits

The LLM is invoked exactly twice per turn (intent extraction + reply
generation), only after the deterministic guards have decided the message
is safe to forward. The LLM is never the source of truth for:

- Whether a vehicle fits a budget
- What the estimated payment is
- Whether the customer is asking about dealer cost
- Whether to suggest a longer term (and if so, which one)
- Whether to include non-Ford brands

If you find yourself adding model-side logic for any of those, the rule is
in the wrong place.
