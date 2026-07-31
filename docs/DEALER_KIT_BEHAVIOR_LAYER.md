---
title: "Dealer AI Kit — Behavior Layer"
status: active
generated: 2026-05-01
last_reframed: 2026-07-31
companion_docs: ["DEALER_KIT_SESSION_START.md", "PROJECT_WHAT_IT_IS.md", "CONTEXT_KIT_INVENTORY.md", "PROJECT_PIPELINE.md"]
---

# Dealer AI Kit — Behavior Layer (BEHAVIOR_LAYER.md)

> **Read-order note:** companion to `DEALER_KIT_SESSION_START.md`, the
> two-doc anchor, and PROJECT_PIPELINE.md. Anchors hold *what exists*
> and *what it is*. PIPELINE holds *how requests move*.
> **BEHAVIOR_LAYER holds *how the AI Sales Assistant sounds, looks,
> and respects prior turns*.**
>
> **Reference implementation note (2026-07-31 pivot):** the shipped
> default dealer is Copper Canyon Auto (Yuma, AZ — indie, mixed-make
> used only). The examples in this doc were originally captured
> against the Freedom Ford franchise reference implementation
> (SESSION_001–020) because that is the tested baseline. **The
> contracts are identical for the Copper Canyon indie default** —
> same voice rules, same UI source-of-truth boundary, same
> constraint preservation, same scrub stack — with two additions
> active only when `dealer_type == "independent"`: the
> `INDIE_MODE_HINT` system fragment and the `indie_prohibited_copy`
> scrub (blocks "brand new", "CPO", "certified pre-owned",
> "manufacturer warranty", OEM-captive brand names, "0% APR").
> Franchise (Ford) examples are still runnable via
> `DEALER_AI_DEALER_TYPE=franchise` + `DEALER_AI_PRIMARY_MAKE=<OEM>`.

---

## Purpose

Governs the behavior surface of the chat-based AI Sales Assistant — voice,
card-vs-prose presentation, constraint preservation across budget/lever
follow-up turns, and the line between deterministic backend math and LLM
phrasing. Behavior bugs in this product rarely throw errors; they drift
into the wrong tone, restate card data, or silently violate prior
constraints across turns.

---

## Voice / Tone Contract

### Persona

- **Identity:** A friendly salesperson at the configured dealership
  (Copper Canyon Auto by default; whatever `useBrand().dealershipName`
  resolves to at runtime) — informed, plain-spoken, dealership-focused.
  Franchise-config dealers use the same identity template with an OEM
  brand slot.
- **Audience:** Customers shopping for a vehicle by monthly-payment target.
  They have a concrete budget, often a drivetrain / body style preference,
  and varying flexibility on term, down payment, and trade-in.
- **Tone modifiers:** Conversational, confident, helpful — not pushy.
  Avoid sales-template tics ("Let me see what I can do for you!", repeated
  "Would you like…" closes). Sound like a person, not a script.

### Required phrasings (signature patterns to preserve)

These are tested anchors in `tests/test_stretch_options.py` and
`tests/test_lever_accept.py`. They were chosen deliberately and any
"improvement" should be reviewed against the test suite first.

- ✅ `The [year] [model] is really close at about $X/mo` — opener for
  the closest match (NEAR-FIT and lever-flex branches).
- ✅ `The [year] [model] is the closest match I have at about $X/mo` —
  opener for single-near and single-stretch branches.
- ✅ `Would you be open to adjusting one of those so I can show you more options?` —
  verbatim soft close for single-near / single-stretch lever-soft-close
  branches. The word "options" may be replaced with the obvious category
  (e.g. "more trucks", "more SUVs").
- ✅ `Would that be something you'd consider?` / `Want me to run the
  numbers on a longer term?` — soft closes for the near+stretch
  opportunity branch.
- ✅ Three upsell phrases (LLM picks ONE, never all three):
  "if you're open to stretching just a bit, that opens up …" |
  "that opens up options like …" |
  "with a little flexibility, you could step into …".
- ✅ Lever-flex multi-lever close (dynamic — only mentions levers that
  yielded cards): `Would you rather look at a longer term, more down, or flexible drivetrain?`

### Forbidden phrasings (paired with replacements)

- ❌ `Here are some options:` followed by a bulleted list
  → ✅ Lead conversationally with the closest match, reference others by comparison.
- ❌ Pipe-delimited spec dumps: `2019 Ford Ranger XLT 4x4 | Stock #FF-USED-104 | $26,995 | est ~$517/mo`
  → ✅ Year + model + qualitative anchor: `The 2019 Ranger 4x4 is really close at about $517/mo`.
- ❌ `Step 1: …  Step 2: …` numbered scaffolding
  → ✅ Flowing prose. The reply rules themselves are written as paragraphs
  precisely so the small Ollama model doesn't echo their structure.
- ❌ `Would you like to explore other options slightly under your target?`
  (when no under-target inventory exists)
  → ✅ Name the actual lever needed: longer term / more down / trade-in /
  drivetrain flex.
- ❌ Calling a flex card "in your budget" or implying it satisfies the
  original drivetrain / term / down ask
  → ✅ Name the lever explicitly: `if you're flexible on drivetrain, the
  Colorado slips under your target` (the customer can read "Drivetrain
  flex — this is 2WD" on the card).

### Tone per surface

| Surface | Tone | Length cap | Notes |
|---|---|---|---|
| Customer chat (assistant prose) | Friendly, conversational, plain-spoken | **3–5 sentences when cards are present** | One payment quote allowed for the lead vehicle only. |
| BUDGET ANALYSIS internal block | Directive, terse | (system-only — never echoed) | Carries lever explainers, signature opener templates, and the per-branch reply rules. |
| Card UI explainer caption | Single short clause | One line | Examples: `Needs 84-mo term`, `This is 2WD — flexible-drivetrain option`. |
| Cards (badges) | Single-word labels | n/a | `In budget` / `Close · +$X/mo` / `Above target · +$X/mo` / `Drivetrain flex` / `Longer term` / `More down`. |
| Canned responses (HANDOFF, RATE_INQUIRY, FABRICATED_INVENTORY, NEGOTIATION, etc.) | Compliant, neutral | One short paragraph | Static strings; never LLM-generated. |

---

## UI / Source-of-Truth Contract

> **Rule:** the cards are the source of truth for specs, prices, mileage,
> Stock #s, and features. Prose **references** the cards, it does not
> **restate** them.

When the AI Sales Assistant returns matched_vehicles, the frontend
ChatVehicleCard renders price, est. payment (W.A.C.), mileage,
drivetrain, condition, the budget_fit badge ("In budget" / "Close" /
"Above target"), and (for flex picks) the lever_flex badge + explainer
caption. **Restating any of that data in prose is forbidden.**

### Authoritative-surface table

| Data type | Authoritative surface | LLM may | LLM must not |
|---|---|---|---|
| **Price** ($26,995) | ChatVehicleCard | reference qualitatively (`bigger truck`, `older year`) | restate the dollar figure for any vehicle |
| **Estimated monthly payment** | ChatVehicleCard payment row | quote ONCE for the LEAD vehicle (`about $517/mo`) | quote payments for the OTHER cards in the same reply |
| **Stock #** (FF-USED-104) | ChatVehicleCard stock row | cite if a guard requires it (rare); generally avoid | introduce a vehicle by Stock # |
| **Mileage** (73,500 mi) | ChatVehicleCard mileage chip | not mention | restate as a number |
| **Features** (Tow Package, FX4, Sync 3) | ChatVehicleCard / detail modal | mention ONE differentiator if comparing capability | recite full feature lists |
| **Drivetrain** (4x4, RWD) | ChatVehicleCard chip + flex badge | name when the lever requires it (`if you're flexible on drivetrain`) | claim a different drivetrain than the card shows |
| **Budget classification** (fit / near / over) | budget_fit badge + payment_delta | reference qualitatively (`really close`, `a bit above target`) | call a near_fit "in budget" or a flex card "in budget" |
| **Lever required** (longer term / more down / drivetrain flex) | lever_flex_explainer caption | name the lever verbatim from the caption | hide the lever or rebrand it |

### Sentence cap

When two or more cards are present in `matched_vehicles[]`, the
assistant prose is capped at **3–5 sentences**. Every sentence beyond
five is recital — the customer can already read the cards.

### One-payment-quote rule

The assistant may quote **one** estimated monthly payment in prose, and
only for the lead (closest-match) vehicle. Other vehicles in the same
reply are referenced qualitatively: "bigger truck", "newer year",
"more features", "gets you under budget", "if you stretch the term a
bit".

---

## Constraint Preservation Across Turns

The AI Sales Assistant runs a multi-turn conversation. Constraints the
customer establishes (target monthly payment, down payment, term,
drivetrain, vehicle_type) must persist until the customer **explicitly**
revokes them.

### Persistent constraints

| Constraint | Lifetime | Carried via | Cleared by |
|---|---|---|---|
| `target_monthly_payment` | session | `ChatSession.extracted_profile` | the customer naming a new $/mo target |
| `down_payment` | session | `ChatSession.extracted_profile` | the customer naming a new down value |
| `term_months` | session | `ChatSession.extracted_profile` | the customer naming a new term |
| `vehicle_type` | session | `ChatSession.extracted_profile` | naming a new category (truck → SUV) |
| `model` | session | `ChatSession.extracted_profile` | naming a new model OR new vehicle_type |
| `drivetrain` (`"4WD"` / `"AWD"` / `"RWD"` / `"FWD"`) | session | `ChatSession.extracted_profile` | the customer using a release phrase ("any drivetrain", "drop the 4WD", "I'm flexible on drivetrain", "2WD is fine"). Sets `drivetrain="any"` (the explicit release sentinel). |
| `make_lock` (Ford-only) | session | `ChatSession.extracted_profile` | naming a different make |
| `current_vehicle_id` / `current_vehicle_stock` | session, anchor-aware | `ChatSession.extracted_profile` | naming a new model OR a new vehicle_type (anchor reset) |

> **Rule:** `merge_profile` is *additive only* — empty values never
> overwrite known data. The only way to "clear" a constraint is to set
> it to a sentinel value like `drivetrain="any"`. New release sentinels
> (e.g. for `vehicle_type`, `make_lock`) require explicit code, not
> just empty-value emission.

### LLM-hallucination guard

Small Ollama models will sometimes emit numeric profile fields the
message doesn't carry (e.g. `target_monthly_payment=84` from "yes try
84 months"). `parse_intent` drops LLM-emitted `target_monthly_payment`
/ `down_payment` / `max_price` fields when:

1. `regex_extract` did not see them in the same message, AND
2. The message contains no currency cue (`$`, `budget`, `cash`,
   `payment`, `monthly`, `mo`, `per month`, `down`, `under`,
   `less than`, `up to`, `max`).

This is enforced by `_CURRENCY_SIGNAL_RE` in `intent_parser.py`. Any
new numeric profile field added in future must be added to the same
guard list, or it will inherit the same hallucination risk.

### Bare confirmation / numberless lever clarifier

Two common follow-up shapes route to canned clarifiers instead of a
budget pipeline rerun:

- **Bare confirmation** — `yes`, `ok`, `sure`, `sounds good`, `let's
  try it`, `yes please` — when the prior assistant message had
  `metadata.lever_offer=True`. Returns `LEVER_CLARIFIER_RESPONSE`
  (canned), no LLM call, no rerun. The `lever_offer` flag is set on
  any single-card soft-close turn or any lever-flex turn.
- **Numberless lever ask** — `try a longer term`, `I can put more down`,
  `bigger down payment` (no specific number). Returns
  `_longer_term_clarifier_response(current_term)` or
  `MORE_DOWN_CLARIFIER_RESPONSE` (canned). Term-aware: at 84+ months
  the longer-term clarifier redirects to a different lever instead of
  proposing an even longer term.

> **Rule:** never re-run the budget search on a guess. If the customer's
> message could mean two different lever flexes, ask which one — never
> pick a default for them.

---

## Decision Authority Boundary

| Layer | Owns |
|---|---|
| **Deterministic backend / services** (`payment_engine`, `_classify_candidates`, `build_budget_context`, `_pick_lever_flex_options`, post-LLM scrubs) | Decision-making — payment math, budget classification (fit / near_fit / over_budget), inventory selection, lever-flex picking, fabricated-inventory guard, payment-consistency drift check, rate-language scrub. |
| **LLM phrasing** (the assistant reply text) | Language only — explaining which card is closest, comparing options qualitatively, naming the lever each flex card requires, asking the soft-close question. |

> **Rule:** the LLM **must never** create a payment number, classify a
> vehicle as "in budget", invent a Stock #, quote a specific APR, or
> commit the dealership to a price. The LLM **may only** explain the
> backend's decisions in conversational prose.
>
> If a prompt asks the model to choose, decide, or compute, the entry
> point is wrong: the deterministic layer needs to make the call first
> and pass the result in via the BUDGET ANALYSIS block.

---

## Behavior Rules — GOOD / BAD Examples

### Rule: Closest match first, alternatives by comparison

> **Context:** customer asked for a 4WD truck around $500/mo with $3,000
> down. Inventory yields 1 strict near-fit (Ranger 4x4 @ $517/mo), 1
> longer-term flex (Tundra 4x4 @ $609/mo at 72 months), 1 drivetrain
> flex (Colorado 2WD @ $486/mo).

- ✅ **GOOD:**
  > *"The Ranger is really close at about $517/mo. If you're flexible
  > on drivetrain the Colorado actually slips under your target, and
  > if you stretch the term a bit the Tundra opens up as a bigger truck.
  > Would you rather look at a longer term or flexible drivetrain?"*

  Three sentences. One payment quote (lead). Qualitative references for
  alternates. Multi-lever close mentioning only the levers that surfaced.

- ❌ **BAD:**
  > *"Here are some options: 2019 Ford Ranger XLT SuperCrew 4x4 priced
  > at $26,995 with an estimated monthly payment of $517/mo (W.A.C.); 2018
  > Toyota Tundra Limited CrewMax 4x4 priced at $35,995 with an estimated
  > monthly payment of $609/mo at 72 months (W.A.C.); 2020 Chevrolet
  > Colorado WT 4x2 priced at $25,495 with an estimated monthly payment
  > of $486/mo (W.A.C.)…"*

  Restates every card. Eight+ sentences. Bullet-list shape. The cards
  already render every value cited.

### Rule: Never imply a flex satisfies the original constraint

> **Context:** customer asked for a 4WD truck. The Colorado WT 4x2 surfaces
> as a `drivetrain_flex` card with the explainer "This is 2WD —
> flexible-drivetrain option (your ask: 4WD)".

- ✅ **GOOD:** *"if you're flexible on drivetrain the Colorado slips
  under your target."* — names the lever, signals it's an alternative
  to the customer's ask.
- ❌ **BAD:** *"the Colorado is a great 4WD option that fits your
  budget."* — falsely claims 4WD; calls a flex pick "fits your budget".

### Rule: Stay inside decision authority

> **Context:** customer asks "what rate would I qualify for?"

- ✅ **GOOD:** the canned `RATE_INQUIRY_RESPONSE` fires (pre-LLM
  short-circuit). The LLM never sees the question.
- ❌ **BAD:** the LLM answers `"Probably around 6.5% APR for someone
  with good credit."` — this is why the rate-inquiry guard fires
  *before* the LLM call, not after.

### Rule: Preserve drivetrain across turns

> **Context:** turn 1 the customer says "4WD truck $500/mo". Turn 2 says
> "show me cheaper ones".

- ✅ **GOOD:** turn 2 reruns the budget pipeline with `drivetrain=4WD`
  still in profile; only 4WD trucks (and labeled drivetrain-flex picks)
  surface.
- ❌ **BAD:** turn 2 surfaces a 2WD truck as the primary match because
  the drivetrain wasn't in the LLM's working memory. (The structured
  profile is the system's memory; conversation history is the LLM's
  memory. They are not the same thing.)

### Rule: Constraint release is explicit

> **Context:** prior turn established `drivetrain="4WD"`. Current turn:
> "any drivetrain".

- ✅ **GOOD:** `regex_extract` matches the release pattern, emits
  `drivetrain="any"`, `merge_profile` overwrites "4WD" with "any", the
  budget pipeline reruns with the wider pool. Flex options no longer
  fire (because there's no strict drivetrain to flex from).
- ❌ **BAD:** `regex_extract` returns nothing → `drivetrain="4WD"`
  persists silently → the customer sees the same single-card response
  with no acknowledgment that they tried to widen the search.

---

## Small-Model Behavior Note

The default LLM provider is **Ollama llama3.1** (smaller / local /
fast). Several behavior rules are load-bearing for accuracy and have
required additional enforcement beyond prompt-time directives.

- **Negative directives alone often fail.** "DO NOT recite prices"
  did not survive the small model on its own. Adding a `GOOD example`
  + multiple `BAD examples` to the presentation preamble was what got
  the model to comply. Always pair "never X" with a worked positive
  example.
- **Examples beat rules.** The `_CARD_PRESENTATION_PREAMBLE` constant
  ships a verbatim GOOD example mirroring the desired voice. The model
  imitates the example more reliably than it follows the rule list.
- **Numeric hallucination must be guarded post-extraction.**
  `_CURRENCY_SIGNAL_RE` strips LLM-emitted numeric fields the message
  doesn't actually carry. Without it, "yes try 84 months" got mis-parsed
  as `target_monthly_payment=84`.
- **Payment math is checked post-LLM.** `check_payment_consistency`
  flags any $/mo number in the assistant reply that isn't in the
  `allowed_payments` list (assembled from `matched_vehicles[*]`).
  Drift logs to the audit trail.
- **Fabricated Stock #s are stripped post-LLM.** Any Stock # the LLM
  cites that isn't in `matched_vehicles[*]` triggers
  `FABRICATED_INVENTORY_RESPONSE` (canned replacement). The promotion
  of stretches and lever-flex picks into matched_vehicles widens the
  allow-list naturally, so honest citations now pass the guard.

> **Rule:** any behavior contract here that's load-bearing for safety,
> accuracy, or compliance must have a **post-generation check** in
> code. Prompt-time alone is not enough on a small model. Current
> post-generation checks: `check_payment_consistency`, fabricated-
> inventory guard, rate-language scrub, internal-directive scrub,
> default-assumption scrub, category-label scrub, internal-confusion
> fallback, post-LLM safety rewriter, post-LLM negotiation override,
> post-LLM handoff override.

---

## Reply-Rule Branches Summary

`_format_budget_block` in `chat_engine.py` emits a different reply rule
per scenario. All card-bearing branches prepend `_CARD_PRESENTATION_PREAMBLE`
(the GOOD/BAD example block). The branches are:

| Trigger | Branch | Sentence cap | Lever offer? | Soft close pattern |
|---|---|---|---|---|
| no cards (no fit / no near / no stretch / no flex) | else | n/a | no | `EXACTLY ONE focused narrowing question` |
| 1+ fit, 1+ stretch | `fit_count > 0 and has_stretches` | 3–5 | no | warm next-step |
| 1+ fit, no stretch | `fit_count > 0` | 3–5 | no | warm next-step |
| 1+ near, 1+ stretch | `near_count > 0 and has_stretches` | 3–5 | no | "Would that be something you'd consider?" |
| exactly 1 near, no stretch | `near_count == 1` | 3–5 | yes | "Would you be open to adjusting one of those…" |
| 2+ near, no stretch | `near_count > 0` (multi) | 3–5 | no | EXACTLY ONE narrowing question |
| no fit, no near, exactly 1 stretch | `fit_count == 0 and len(closest_above) == 1` | 3–5 | yes | "Would you be open to adjusting one of those…" |
| any branch + lever-flex picks | `has_lever_flex` (highest priority) | 3–5 | yes | dynamic multi-lever close |

> **Rule:** when adding a new branch or modifying an existing one,
> verify the row above stays accurate and that all card-bearing
> branches still prepend `_CARD_PRESENTATION_PREAMBLE`. The
> `test_card_presentation_rules.py` suite pins the contract.

---

## Post-LLM Enforcement Layer

> Added during the post-`SESSION_002` stabilization pass and
> extended in `SESSION_003`. The behavior contract above describes
> *how the assistant should sound*; the enforcement layer
> described here is *what makes the contract hold on a small
> model*. See `docs/handoffs/SESSION_003_demo_polish_snapshot.md`
> §1 for the full pipeline order with code anchors.

The behavior contract is enforced at two layers — prompt-time
(the reply rules, `_CARD_PRESENTATION_PREAMBLE`,
`_format_cash_mode_block`, the model-followup branch GOOD/BAD
examples) and post-generation (the scrub stack below). Every
load-bearing rule has a code-level enforcer; the prompt is no
longer the sole guarantor. This is what makes Ollama
llama3.2:latest viable for the customer-facing chat — the scrubs
catch what the prompt cannot.

### Scrub stack (in pipeline order)

After the wholesale-replacement guards (`post_safety_rewritten`,
`internal_confusion_fallback`, `post_llm_override`,
`fabricated_inventory_fired`):

| # | Scrub | Enforces |
|---|---|---|
| 1 | `scrub_meta_narration` | Strip *"Here's a revised response:"*, *"(Note: I've removed…)"*, *"Let's try again"*, *"As requested:"*, *"Based on your request:"*, *"This response…"* |
| 2 | `scrub_rate_language` | Strip APR / `\d+%` / "interest rate" leakage |
| 3 | `scrub_internal_directives` | Strip `BUDGET ANALYSIS` / `DO NOT recompute` leakage |
| 4 | `scrub_default_assumption_language` | Strip "with no money down" / "default 72-month term" |
| 5 | `scrub_budget_category_labels` | Strip invented category labels |
| 6 | `scrub_payment_drift` | No fabricated payments — replace `$X/mo` numbers not in `allowed_payments` with `"the payment shown on the card"` |
| 7 | `scrub_extra_payment_quotes` | One payment quote per turn — keep first card payment, strip rest |
| 8 | `scrub_list_shape` | NO bulleted lists, numbered steps, pipe-delimited spec dumps, `**Heading**` standalone lines |
| 9 | `scrub_followup_question` | One natural close question — strip duplicate `?`, replace forbidden openers (`"Would you like..."`, `"narrowing question"`, `"specific aspect"`) |
| 10 | `scrub_generic_use_cases` | (model_followup only) Strip `"perfect for hunting"`, `"ideal for off-road"`, `"great option for those"` brochure phrasings |
| 11 | `scrub_followup_anchors` | (model_followup only) Drop sentences without constraint-fit / comparison / card-data anchor; `_DEFINITELY_BROCHURE_RE` overrides anchors for `"feature-packed"`, `"standout features"`, `"top-of-the-line"`, etc. |
| 12 | `scrub_drivetrain_claims` | Strip false drivetrain claims about a card (e.g., *"the Colorado is 4WD"* when card is RWD) |
| 13 | `scrub_financing_language` | (cash_mode only) Strip `$X/mo`, *"monthly payment"*, *"financing"*, *"loan"*, *"W.A.C."*, *"approved credit"*, X-month term phrasings |
| 14 | `scrub_fallback_stall` | Block clarifier-only replies + *"let me pull our inventory"* / *"I'll come back with options"* stalling prose when cards are present |
| 15 | `scrub_both_wording` | Replace *"both"* with *"these options"* / *"all of them"* when card count ≠ 2 |
| — | `cap_model_followup_length` | (model_followup only) Hard cap 3 sentences + one trailing question |

Scrubs 6–15 are gated on `bool(matched_vehicles)` (cards
present); scrubs 1–5 fire whenever the wholesale guards haven't
already replaced the body. Mode-gated scrubs (`generic_use_case`,
`followup_anchors`, `cap_model_followup_length`) require
`metadata.mode == "model_followup"`. The `financing_language`
scrub requires `metadata.cash_mode = True` (sticky in profile
once a cash signal is detected).

Any combination of ≥ 2 scrubs promotes the metadata flag to
`multiple_scrubs_fired`.

### Adjacent state-layer enforcement

These aren't in the post-LLM scrub chain but they shape what the
chain sees. All implemented in `chat_engine.py`:

| Helper | Role |
|---|---|
| `customer_visible_vehicles()` | Single-source queryset that excludes debug stocks (`-DBG`, `DEBUG-`, `TEST-`, `__`) at every customer-facing inventory query site. |
| `customer_drivetrain_label()` | Internal `Vehicle.drivetrain` (4x4 / RWD / AWD / FWD) → customer-facing label (4WD / 2WD / AWD / FWD). Used by `VehicleSerializer` and `scrub_drivetrain_claims`. |
| `detect_intent_shift` + `apply_intent_reset` | Truck → car pivot resets stale anchor + irrelevant constraint state so a new BudgetContext rebuilds clean. |
| `infer_budget_from_intent` | Cash + commuter signals bootstrap `max_price=$15,000` so the discovery gate doesn't fire on bare *"cheap car cash"*. |
| `cash_mode_active` (sticky) | Once a cash signal is detected, persists in `merged_profile["cash_mode"]` so subsequent turns keep the financing scrub on. |
| `_format_cash_mode_block` | When `cash_mode_active and len(matched) >= 2`, injects an extra system message with the **decisive-voice** comparison rule (GOOD / BAD examples, lead with strongest fit, no neutral side-by-side, next-step close). |
| `_resolve_model_followup_vehicle` | Three-step resolver: (1) regex model match, (2) substring match of any prior model name in user_text, (3) make-only fallback when exactly one prior card from that make exists. Catches *"tell me about the Honda"* / *"what about the Fusion"*. |

### Implication for prompt rule writing

Prompt rules in `_CARD_PRESENTATION_PREAMBLE`, `_format_cash_mode_block`,
and the model-followup branch of `_format_budget_block` describe
*desired* behavior. Negative directives are belt-and-suspenders —
the scrubs are the actual contract. This means:

- **Prompt rule changes don't risk customer regressions** as long
  as the corresponding scrub still pins the contract. If you
  tweak the GOOD example phrasing, the scrub still strips the
  bullet shape, the drift number, the brochure cliché.
- **Adding a new behavior contract requires both** a prompt-time
  rule (so the model produces the right output most of the time)
  and a post-generation enforcer (so the customer never sees a
  failure on the small model).
- **BAD examples must not contain concrete imitation targets.**
  The original `_CARD_PRESENTATION_PREAMBLE` bug was the BAD
  example shipping `$26,995, est $517/mo (W.A.C.); … $25,495,
  est $486/mo` — small models imitated those numbers verbatim.
  The current preamble uses `$XX,XXX` / `$XXX/mo` placeholders.
  A regression test
  (`test_card_presentation_rules.BadExampleNoConcreteDollarsTests`)
  pins this contract.
- **GOOD examples shape voice more than rule lists.** The
  cash-mode block and model-followup branch each carry one or
  two worked GOOD examples in the target voice. The small model
  imitates them more reliably than it follows the forbidden
  list. If voice drifts, refresh the GOOD examples first.

---

## Last Verified

- **Contracts:** 2026-05-01 (Freedom Ford franchise-config reference).
- **Pivot reframing:** 2026-07-31 (SESSION_031 Phase 5) — title,
  companion-doc list, persona identity slot, and this section
  updated for Copper Canyon indie default. Underlying contracts
  and worked examples unchanged. Indie additions (INDIE_MODE_HINT
  system fragment, `indie_prohibited_copy` scrub) shipped in
  SESSION_030 Phase 1 — they *extend* the scrub stack described
  below; nothing here was removed.
- **Surfaces audited:** AI Sales Assistant chat (assistant prose +
  ChatVehicleCard); BUDGET ANALYSIS internal block; canned responses
  (HANDOFF, RATE_INQUIRY, FABRICATED_INVENTORY, NEGOTIATION, IDENTITY,
  IMAGE_REQUEST, APPOINTMENT_REQUEST, EXTERNAL_VALUE, GUARD); the
  post-LLM enforcement layer (scrubs 1–9 above).
- **Known active drift (post-stabilization-pass):** drivetrain /
  feature hallucination in prose claims. The
  `FABRICATED_INVENTORY_RESPONSE` guard catches Stock #s but not
  attribute claims like *"the Colorado is available in both 2WD and
  4WD configurations"* (when the card shows 4x2 only). Inline
  markdown bold (`**Engine:** ...`) carrying invented engine /
  towing / paint specifications also slips through `scrub_list_shape`
  (which only catches bold lines that ARE the whole line). Item
  4a — drivetrain — is the next session's task; item 4b — feature
  claims — is a separate, larger pass.
- **Resolved by the stabilization pass:** the NEAR-FIT + STRETCH
  branch alternate-price drift; the `$486/mo` vs `$546/mo` smoke
  drift; bullet / pipe / numbered / markdown-heading shape leaks;
  meta-narration prefix / suffix leaks; multi-payment-quote
  violations; forbidden-opener and two-question follow-up
  violations.
- **Next recommended audit:** before any change to
  `_CARD_PRESENTATION_PREAMBLE`, before any change to
  `_format_budget_block`'s branch conditions, after any LLM provider
  / model switch, and after item 4a (drivetrain) lands.
