---
date: 2026-05-01
title: Demo polish + UI rebuild + behavior enforcement extension (Items 6–15)
type: state-of-the-system
---

# Session handoff — demo polish, UI rebuild, full behavior enforcement layer

This handoff continues from
`docs/handoffs/SESSION_002_sales_behavior_snapshot.md` §9 (which
documented the original post-LLM scrub stabilization pass, items 1–5).
Code references are inline (`file:line`).

The **post-LLM enforcement layer** is now 14 stages (was 9 at the
SESSION_002 close). The frontend chat card was rebuilt for scan-
friendly density. State-layer fixes added intent-shift reset,
cash-mode persistence + financing scrubbing, weak-intent budget
inference, and debug-stock filtering. Test baseline: **1088 pass,
1 skipped, 0 failed.**

This snapshot describes *what exists*, not *what shipped*. Use it
to act on real state.

---

## 1. Post-LLM scrub pipeline (current order)

After the wholesale-replacement guards (`post_safety_rewritten` /
`internal_confusion_fallback` / `post_llm_override` /
`fabricated_inventory`), the chat engine now runs this chain in
order:

| # | Scrub | Purpose | Code anchor |
|---|---|---|---|
| 1 | `scrub_meta_narration` | strip "Here's a revised response:", "(Note: I've removed…)", "Let's try again", "As requested:" | `chat_engine.py` (item 5) |
| 2 | `scrub_rate_language` | (existing) APR/% / "interest rate" leakage | `chat_engine.py` |
| 3 | `scrub_internal_directives` | (existing) BUDGET ANALYSIS / DO-NOT-RECOMPUTE leaks | `chat_engine.py` |
| 4 | `scrub_default_assumption_language` | (existing) "with no money down" / "default 72-month" | `chat_engine.py` |
| 5 | `scrub_budget_category_labels` | (existing) "## NEARLY IN BUDGET" rebrands | `chat_engine.py` |
| 6 | `scrub_payment_drift` | invented `$X/mo` numbers replaced with phrase | item 2.a (drift) |
| 7 | `scrub_extra_payment_quotes` | enforce one-payment-quote rule | item 1 |
| 8 | `scrub_list_shape` | strip bullets / numbered / pipe-delimited / `**Heading**` lines | item 2 |
| 9 | `scrub_followup_question` | strip duplicate `?`, replace forbidden closers | item 3 |
| 10 | `scrub_generic_use_cases` (model_followup) | strip "perfect for hunting", "ideal for off-road", "great option for those" | item 6 |
| 11 | `scrub_followup_anchors` (model_followup) | drop sentences without constraint / comparison / card-data anchor; `_DEFINITELY_BROCHURE_RE` overrides anchors for hard-coded brochure tokens (`feature-packed`, `standout features`, `top-of-the-line`, …) | item 14 |
| 12 | `scrub_drivetrain_claims` | strip false drivetrain claims about a card | item 4a |
| 13 | `scrub_financing_language` (cash_mode) | strip `$X/mo`, "monthly payment", "financing", "loan", "W.A.C.", "approved credit", "X-month term" | item 9 |
| 14 | `scrub_fallback_stall` | "let me pull our inventory" / "I'll come back with options" / clarifier-only with cards | item 11 |
| 15 | `scrub_both_wording` | replace "both" with "these options" when card count ≠ 2 | item 12 |
| 16 | `cap_model_followup_length` | hard cap 3 sentences + one trailing question for model_followup | item 10 |

State-layer (separate from the scrub chain):

- **`detect_intent_shift` + `apply_intent_reset`** — truck → car
  pivot resets stale anchor + irrelevant constraints (item 7).
- **`infer_budget_from_intent`** — cash + commuter signals
  bootstrap a `max_price=$15,000` ceiling so the discovery gate
  doesn't fire on bare "cheap car cash" (item 8).
- **`merged_profile["cash_mode"]` (sticky)** — once cash signals
  appear, cash_mode is set in profile and persists across turns
  (item 9).
- **`customer_visible_vehicles()`** — single source of truth
  queryset that excludes debug stocks (`-DBG`, `DEBUG-`, `TEST-`,
  `__`) at every customer-facing inventory query site
  (item 13).
- **`_format_cash_mode_block`** — when `cash_mode_active` AND
  `len(matched) >= 2`, an extra system message tells the LLM to
  compare top 2-3 vehicles on price / mileage / reliability /
  fuel economy and never mention monthly/financing (item 15).
- **`_resolve_model_followup_vehicle`** — three-step resolution:
  (1) regex model match, (2) substring match of any prior
  vehicle's model name in user_text (catches Camry / Accord /
  Fusion / Sonata which aren't in `regex_extract`'s model
  whitelist), (3) make-only fallback when exactly one prior
  card from that make exists (catches "tell me about the
  Honda") (item 14).

---

## 2. Customer-facing standardization (item 4)

### Drivetrain labels

Inventory canonical values (`Vehicle.drivetrain` field) → customer-
facing labels via `customer_drivetrain_label()` in
`chat_engine.py`:

| Internal | Customer label |
|---|---|
| `4x4` / `4WD` | **`4WD`** |
| `4x2` / `2WD` / `RWD` | **`2WD`** |
| `AWD` | `AWD` |
| `FWD` | `FWD` |

`VehicleSerializer.drivetrain` returns the customer-facing label,
so the frontend chip / spec grid renders 4WD/2WD/AWD/FWD without
any frontend code change. The same helper is used by
`scrub_drivetrain_claims` so contract enforcement and display use
identical vocabulary.

### "Both" wording

When `len(matched_vehicles) != 2`, prose uses "these options" /
"these vehicles" / "all of them" / "all of these" — never "both".
When count is exactly 2, "both" is preserved. Conjunction shape
"both X and Y" (e.g., "both available and affordable") is left
alone via the `\bboth\b(?!\s+\w+\s+and\b)` lookahead.

---

## 3. Frontend ChatVehicleCard rebuild

`frontend/src/components/ChatVehicleCard.tsx` — scan-friendly
re-layout. Path 2 (parsed-only fallback) preserved.

Path 1 layout:

```
┌──────────────────────────────────────────────────────────┐
│ [photo]  Year Make Model Trim                  $XX,XXX  │  ← Title row
│          One-line summary (from vehicle.description)    │  ← Summary
├──────────────────────────────────────────────────────────┤
│ 📅 YEAR Y    🏭 MAKE  M    🚙 MODEL  M T                  │  ← Spec grid
│ ⛽ MILES X   ⚙ DRIVETRAIN D  💰 PRICE  $X                 │     (2-col mobile,
├──────────────────────────────────────────────────────────┤      3-col sm+)
│ [Feature 1] [Feature 2] [Feature 3] [Feature 4]         │  ← Features pills
├──────────────────────────────────────────────────────────┤
│ [BADGE 1] [BADGE 2] [BADGE 3]   est ~$X/mo (W.A.C.)     │  ← Badges + payment
│ Lever-flex explainer caption                            │  ← Caption (when present)
│ Stock #FF-USED-XXX                                      │  ← De-emphasized footer
└──────────────────────────────────────────────────────────┘
```

- Title (Year Make Model Trim) prominent; price right-aligned.
- One-line summary derived from `vehicle.description` via
  `firstSentence()` (truncates at 140 chars with ellipsis).
- 2-column spec grid on mobile, 3-column on `sm:` and up
  (`grid-cols-2 sm:grid-cols-3`). Year / Make / Model+Trim /
  Miles / Drivetrain / Price.
- Features pill row (max 4 features).
- Badges row (budget-fit + lever-flex + condition) with
  estimated payment right-aligned.
- Lever-flex explainer in a tinted band when present.
- Stock # de-emphasized in a muted footer (`text-slate-400`).
- Section separators (`border-t border-slate-100`) for visual
  scan rhythm.

---

## 4. Cash-mode behavior (the validation case)

Customer says *"I am looking for a cheap car I can pay cash for
that gets good gas mileage"* — the system now:

1. **Bootstraps a budget.** `infer_budget_from_intent` sets
   `max_price=$15,000`, `vehicle_type=car` because the customer
   gave a cash + commuter signal but no explicit price. Without
   this, the discovery gate would fire and the customer would
   get "tell me your budget" instead of vehicles.
2. **Sets sticky `cash_mode=True`** in profile so subsequent
   turns inherit the financing-language scrub.
3. **Surfaces 3 cars under $15k** via the keyword search (no
   payment classification because there's no
   `target_monthly_payment`).
4. **Injects `_format_cash_mode_block`** as a system message —
   tells the LLM to compare 2-3 top picks on price / mileage /
   reliability / fuel economy and explicitly forbids monthly
   payment / financing / W.A.C. / approved credit language.
5. **Strips any financing language that slips through** via
   `scrub_financing_language` (items 9 + extension): payment
   quotes, "monthly payment", "per month", "financing", "loan",
   "W.A.C." (any spacing variant), "approved credit", "with
   approved credit", X-month term, etc.

Live verification (last smoke):

> *"For a cash purchase with good gas mileage, let's compare the
> top three options: The Honda Accord LX has a great balance of
> price and fuel efficiency, with an estimated 28 MPG in the
> city and 38 MPG on the highway. The Ford Fusion SE also offers
> decent fuel economy, with 23 MPG in the city and 34 MPG…"*

`metadata.cash_mode = True`, no monthly/financing language, 3
cars compared on real dimensions.

---

## 5. Model-followup behavior

Customer says *"tell me about the Honda"* (with a Honda Accord
on the prior turn's matched_vehicles):

1. **`_resolve_model_followup_vehicle`** — make-fallback resolves
   to the single prior Honda card. Sets `mode=model_followup`.
2. **`_format_budget_block`** — emits the deep-dive branch's
   reply rule (positioning + fit-to-constraints + comparison-
   to-previously-shown). Hard-forbids "perfect for hunting",
   "ideal for", brochure copy, standalone feature lists.
3. **`scrub_generic_use_cases`** — strips "perfect for X",
   "ideal for X", "great option for those" sentences.
4. **`scrub_followup_anchors`** — drops every statement without
   a constraint-fit / comparison / card-data anchor; the
   `_DEFINITELY_BROCHURE_RE` override drops sentences carrying
   `feature-packed`, `standout features`, `top-of-the-line`,
   etc., even when they otherwise have an anchor word.
5. **`cap_model_followup_length`** — hard cap of 3 sentences
   ending with one question.

Live verification (last smoke):

> *"With a trade-in Accord LX, you're getting a great deal on a
> vehicle with excellent fuel economy and a smooth ride. The
> CVT transmission makes it easy to cruise around town or hit
> the highway, and the FWD drivetrain ensures you get good gas
> mileage. Is that the direction you want to go?"*

3 sentences, ends with one question, references real card
attributes (Accord LX, fuel economy, FWD drivetrain). No
brochure, no financing.

---

## 6. Test baseline + verification suites

**Current count:** `1088 pass, 1 skipped, 0 failed`.

Up from 799 at SESSION_002 close (15 implementation passes,
+289 new tests).

Tests that pin contracts (must stay green):

```bash
cd backend && source .venv/bin/activate
python manage.py test dealer_ai

# Pre-existing contract suites
python manage.py test dealer_ai.tests.test_card_presentation_rules
python manage.py test dealer_ai.tests.test_lever_accept
python manage.py test dealer_ai.tests.test_lever_flex_presentation
python manage.py test dealer_ai.tests.test_stretch_options
python manage.py test dealer_ai.tests.test_conversation_flow

# Post-LLM enforcement layer (this stabilization arc)
python manage.py test dealer_ai.tests.test_payment_consistency
python manage.py test dealer_ai.tests.test_list_shape_scrub
python manage.py test dealer_ai.tests.test_followup_question_scrub
python manage.py test dealer_ai.tests.test_meta_narration_scrub
python manage.py test dealer_ai.tests.test_drivetrain_claim_scrub
python manage.py test dealer_ai.tests.test_generic_use_case_scrub
python manage.py test dealer_ai.tests.test_model_followup_length_cap
python manage.py test dealer_ai.tests.test_intent_shift_reset
python manage.py test dealer_ai.tests.test_inferred_budget
python manage.py test dealer_ai.tests.test_cash_mode_financing_scrub
python manage.py test dealer_ai.tests.test_fallback_stall_scrub
python manage.py test dealer_ai.tests.test_both_wording_scrub
python manage.py test dealer_ai.tests.test_ui_leak_fixes

# Frontend
cd frontend
npx tsc --noEmit && npx vite build
```

If any go red, the change is wrong — these collectively are the
behavior + presentation contract.

---

## 7. Known remaining polish items

These are surface-level UX gaps observed in live UI testing
that didn't rise to "regression" status. They're polish, not
bugs.

### Cash comparison could be more decisive / salesy

The cash-mode comparison block produces clean tradeoff prose
("the Honda Accord has great price and fuel efficiency, the
Fusion offers decent fuel economy…") but reads like a research
brief, not a sales pitch. A stronger close would:

- Pick a concrete recommendation ("if I had to pick one for
  daily commuting, the Accord — lowest price + best MPG").
- Anchor each tradeoff to a specific number ("the Camry has
  20k fewer miles for $500 more").
- Use a sales-tone pivot question ("Want me to set up a closer
  look at the Accord?" vs. the current "Are you leaning lowest
  price, or long-term reliability?").

The `_format_cash_mode_block` reply rule could be tightened to
emit one of these shapes. No new architecture needed.

### Model followups can still sound technical

Live smokes for *"tell me about the Honda"* / *"what about the
Fusion"* produce factual prose that hits the anchor filter
correctly but still reads engineering-spec — *"The CVT
transmission makes it easy to cruise around town or hit the
highway, and the FWD drivetrain ensures you get good gas
mileage."* Better salesperson voice: *"Smooth around town,
respectable on the highway, and the front-wheel-drive layout
keeps gas costs low."* Same content, more conversational.

The deep-dive branch's reply rule could carry a stronger voice
example or the followup-anchor scrub could prefer constraint-
fit phrasings over engineering nouns.

### Possible future UI: focused / one-card-at-a-time mode

The redesigned card is scan-friendly but stacking 3 of them in
the chat bubble is still a lot of vertical density on mobile.
Future polish:

- One-card-at-a-time view with swipe / arrow navigation.
- "Focus mode" — first card open with full spec grid, others
  collapsed to title + price + badges.
- Comparison view — side-by-side tradeoff table when the
  customer asks "compare these".

Out of scope for the next session unless explicitly requested.

---

## 8. Changes since SESSION_002 §9

Items shipped in this arc (chronological):

| Item | Description | Tests added |
|---|---|---|
| 6 | Generic-use-case scrub (model_followup) | 21 |
| 7 | Intent-shift state reset (truck → car pivot) | 21 |
| 8 | Cash + commuter inferred-budget bootstrap | 28 |
| 9 | Cash-mode financing-language scrub + sticky cash_mode | 21 |
| 10 | Model-followup hard length cap | 15 |
| 11 | Fallback-routing / clarifier-stall scrub | 19 |
| 12 | "both" wording drift scrub | 20 |
| 13 | Debug-stock customer-visibility filter | 3 |
| 14 | Model-followup anchor filter + improved followup resolver | 9 |
| 15 | Cash-mode multi-card comparison reply rule | 6 |

Plus the **frontend ChatVehicleCard rebuild** (no new tests —
typecheck + vite build cover it).

Single commit `7fd5a86`: *"Stabilize AI sales assistant UI and
behavior enforcement"* (7 files changed, +1447 / −123).

Prior commit `b96c034`: initial repo commit (170 files, +49,676
lines).

---

## 9. Document drift status

- `docs/handoffs/SESSION_002_sales_behavior_snapshot.md` §9
  documented items 1–5. This doc covers items 6–15 and is the
  authoritative state-of-the-system snapshot for the demo
  polish phase.
- `docs/FREEDOM_FORD_BEHAVIOR_LAYER.md` §"Post-LLM Enforcement
  Layer" lists 9 scrubs — **stale**, the actual count is now
  16 (14 partial + 2 wholesale chains, plus state-layer
  helpers). Worth refreshing if a future session needs the
  contract written down for prompt-rule decisions.
- `00-START-NEXT-SESSION.md` adopt-managed block was last
  refreshed at the SESSION_002 close. The outside-the-block
  "Next session priority" section (preserved across adopt
  re-runs) is the source of truth for what comes next.

---

## 10. Next session priority (preview)

**Dealer-demo polish pass: make cash and model-followup responses
more decisive and sales-oriented without adding new architecture.**

Concrete starting points are §7 above. The contract for "decisive"
needs a small spec — what does a decisive cash recommendation
actually look like in this dealership's voice? — before any
prompt-rule changes.

Out of scope for that pass:
- New scrubs / new architecture.
- Inventory selection / payment_engine / `_classify_candidates`.
- Frontend redesign beyond minor copy / layout tweaks.
- LLM provider switch.
