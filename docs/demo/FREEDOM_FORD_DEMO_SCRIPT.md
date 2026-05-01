---
title: Freedom Ford Dealer AI — 5-minute demo script
status: active
generated: 2026-05-01
test_baseline: 1111 backend tests passing, frontend tsc/build clean
---

# Freedom Ford Dealer AI — 5-minute demo script

Run this script when showing the AI Sales Assistant to dealership
staff (sales managers, owner, GM). Goal: prove the system handles
real customer shapes and stays compliant, without hand-waving.

## Setup (60 seconds before the demo)

1. Backend running on `:8001` — verify `Ollama llama3.2:latest`
   loaded (`curl -s -m 4 localhost:11434/api/tags | grep llama3.2`).
2. Frontend running on `:5173`.
3. Open `http://localhost:5173/` in a clean browser tab. The empty
   chat shows four suggested prompts (the demo openers below).
4. **Don't** click "Load 5 scripted demo scenarios" in the
   DemoHelperPanel before the demo — that resets sessions and
   creates synthetic leads on the dashboard. Use the live chat
   from a fresh state instead.
5. Optional: have `docs/handoffs/SESSION_003_demo_polish_snapshot.md`
   open in a second tab to point at if anyone asks "how does
   that work?".

If the backend is down: see *Fallback talking points → backend
unavailable* below.

---

## The 5-prompt flow

| # | Prompt | Time | What it proves |
|---|---|---|---|
| 1 | *"I need a 4WD truck around $500/mo with $3k down"* | ~30s | Budget classification, lever-flex picker, payment math, multi-card |
| 2 | *"I have cash and want good gas mileage"* | ~45s | Cash-mode detection, inferred budget bootstrap, financing-language scrub, decisive comparison voice |
| 3 | *"Tell me more about the Honda"* | ~30s | Make-fallback model anchor, deep-dive ownership-fit voice, length cap |
| 4 | *"What about the Fusion?"* | ~30s | Substring model anchor (works on non-Ford models the regex doesn't list), short clean reply |
| 5 | *"Which one would you show first?"* | ~30s | Decisive lead-with-pick recommendation, salesperson voice |

Total: ~3 minutes of prompts + ~2 minutes of explanation.

---

## Prompt 1 — *"I need a 4WD truck around $500/mo with $3k down"*

### What it proves
- The system extracts `target_monthly_payment=$500`, `down_payment=$3000`,
  `vehicle_type=truck`, `drivetrain=4WD` from one natural sentence.
- Budget classification surfaces 3 cards: a near-fit, a longer-term
  flex, and a drivetrain-flex 2WD truck.
- Each card carries a lever-flex badge and explainer caption so the
  customer can tell why a 2WD truck is being shown.
- The prose stays at 3-5 sentences, quotes ONE payment for the
  lead vehicle, references the others qualitatively.

### Expected behavior
- 3 cards on the right (Ranger 4x4, Tundra 4x4, Colorado 2WD).
- Reply lands as: *"The Ranger is really close at about $517/mo.
  If you're flexible on drivetrain the Colorado actually slips
  under your target, and if you stretch the term a bit the Tundra
  opens up as a bigger truck. Would you rather look at a longer
  term or flexible drivetrain?"*
- Cards display **4WD** / **2WD** chip labels (not raw `4x4` /
  `RWD`).

### Talking points
- *"The system reads natural sentences — no form-filling."*
- *"It found a 2WD truck and labeled it as a flex pick — the
  customer knows they'd be giving up the 4WD they asked for."*
- *"That payment number is real backend math, not LLM guessing
  — there's a payment-consistency check that catches drift."*

### Fallback if the LLM gives a weaker answer
- If the prose is shorter than expected: *"Customer still sees
  three real options on the right. The prose is the soft pitch
  — the cards are the source of truth."*
- If the prose mentions monthly payments for two vehicles: the
  extra-payment-quote scrub will have replaced the second one
  with *"the payment shown on the card"*. Show that's the
  contract: one payment quote per turn, others on the cards.

---

## Prompt 2 — *"I have cash and want good gas mileage"*

### What it proves
- Cash + commuter intent detection. The customer didn't name a
  budget; the system infers `max_price=$15,000` so cards still
  surface (no "tell me your budget" stall).
- Sticky `cash_mode` flag. Subsequent turns inherit the
  financing-language scrub.
- Decisive sales voice: leads with the strongest fit, frames the
  alternative as a value play. NO monthly payment, NO W.A.C., NO
  *"with approved credit"*.

### Expected behavior
- 3 cards (typically Fusion / Accord / Sonata or Malibu — all
  under $15k).
- Reply lands like: *"The Honda Accord LX is the lower-mileage
  pick here. It's a reliable and fuel-efficient vehicle that
  will get you around 28 MPG in the city and 38 MPG on the
  highway. If you're looking for something even more
  budget-friendly, the Chevrolet Malibu LT is…"*
- Tradeoff in buyer terms (price vs. miles vs. MPG).
- One next-step close question.
- **Inspect the metadata** (browser devtools → network →
  `chat/message` response): `metadata.cash_mode = true`,
  `metadata.scrubs` likely contains `list_shape` and possibly
  `financing_language` if the LLM tried to mention a payment.

### Talking points
- *"Customer didn't say a budget. The system inferred a
  reasonable cash ceiling so cards still appear."*
- *"There's a 14-stage post-LLM scrub layer. Anything the model
  emits about monthly payments or W.A.C. on a cash turn gets
  stripped before the customer sees it."*
- *"The voice picks a side — 'the Honda Accord is the
  lower-mileage pick' — instead of reciting specs side-by-side.
  That's intentional dealership voice."*

### Fallback if the LLM gives a weaker answer
- If reply is too short ("Here are some options. Which one are
  you leaning towards?"): point at the cards on the right —
  *"The customer sees three real cars under $15k. The prose
  could be richer; the inventory contract is met."*
- If reply says *"In your budget, right?"* or similar tentative
  trailing tag: that's the trailing-tag anti-pattern; the
  followup-question scrub catches it. Click "send" again to
  resample. (This is the polish item from
  `SESSION_003` we just shipped.)

---

## Prompt 3 — *"Tell me more about the Honda"*

### What it proves
- The model anchor resolves *Honda* (the make, not the model)
  to the single Honda card from the prior turn. Three-step
  resolver: regex model match → substring match of any prior
  model name → make-only fallback when exactly 1 prior card
  from that make.
- Deep-dive branch fires (`metadata.mode = "model_followup"`).
- Ownership-fit voice — explains WHY the Honda fits this
  customer in real-world terms, not engineering specs.
- Length cap to ≤ 3 sentences ending with one question.

### Expected behavior
- 1 card on the right (the Honda Accord LX from prior turn).
- Reply lands like: *"The Honda Accord LX is the everyday
  driver pick here — solid fuel economy and low maintenance
  costs make it easy to live with. The main tradeoff is it
  gives up some of the newer-feeling polish you'd get from
  spending a bit more. Want me to keep you on this one or look
  for something cheaper?"*
- The brochure phrases (*"feature-packed"*, *"standout
  features"*, *"perfect for hunting"*) and engineering-spec
  leads (*"the CVT transmission ensures…"*) are explicitly
  filtered.

### Talking points
- *"The customer said 'Honda' — that's a make, not a model.
  The system figured out which Honda from context."*
- *"That reads like a salesperson explaining ownership, not
  reading a spec sheet."*
- *"There's a hard 3-sentence cap on these turns — keeps the
  reply scannable."*

### Fallback if the LLM gives a weaker answer
- If the reply still has light brochure ("a great option for
  someone looking for…"): point at how many scrubs fired
  (`metadata.scrubs` will show several). *"Each one is catching
  something specific. The remaining prose still passes the
  cards-are-source-of-truth contract."*

---

## Prompt 4 — *"What about the Fusion?"*

### What it proves
- Substring model match — *"Fusion"* isn't in `regex_extract`'s
  hardcoded model list, but the resolver does a word-bounded
  substring match against any prior matched vehicle's model.
- Same model_followup deep-dive flow.
- Short, clean reply with one natural close.

### Expected behavior
- 1 card on the right (the Ford Fusion SE).
- Reply lands like: *"The Ford Fusion SE is the budget pick —
  cheaper than the Honda but still gets respectable gas
  mileage. The tradeoff is more miles on the clock. Is that
  the kind of fit you had in mind?"*

### Talking points
- *"The customer said 'Fusion' — single word, no make. The
  system pinned it to the right card."*
- *"The close is a real next-step question, not 'right?' or
  'sound good?'"*

### Fallback if the LLM gives a weaker answer
- If the reply is very short (e.g., *"It comes with Sync and a
  Backup Camera. Is that the direction you want to go?"*):
  *"The card has the rest. The prose is intentionally short
  — the customer's already looking at the spec grid."*

---

## Prompt 5 — *"Which one would you show first?"*

### What it proves
- The system gives a **decisive recommendation** rather than
  hedging.
- Cash-mode comparison block fires when ≥ 2 cards are present.
  Reply leads with a pick.
- Salesperson voice ("I'd lead with the Honda — lower miles, better
  long-term reliability") not researcher voice ("Option A has X,
  Option B has Y").

### Expected behavior
- Reply lands like: *"I'd lead with the Honda Accord LX — lower
  miles and the strongest reliability reputation of the three.
  The Fusion is the fallback if they want to spend less and
  don't mind the higher miles. The Malibu sits in between.
  Want me to set up a closer look at the Honda?"*
- **One concrete pick + one tradeoff frame + one next-step
  question.**

### Talking points
- *"This is the sales question every dealership gets. The system
  picks a side and explains the tradeoff in buyer terms."*
- *"Notice it doesn't say 'compare the three options' or 'each
  has its strengths' — that's the kind of soft-fail voice the
  scrub stack explicitly blocks."*

### Fallback if the LLM gives a weaker answer
- If the reply is neutral ("Each has its strengths"): the
  cash-mode comparison directive specifically forbids that
  shape. The post-LLM scrubs catch the brochure tells but
  can't force decisiveness if the model wanders. Point at:
  *"This is one of the polish items in the next session — the
  scrub stack catches the worst stuff but the LLM occasionally
  hedges on subjective picks. We'd plug a stronger model here
  for production."*

---

## "Do not demo yet" prompts

These have known rough edges or hit code paths still in flight.
Avoid them on stage:

| Prompt | Why to skip |
|---|---|
| *"Tell me about your dealer cost"* / *"What's your margin?"* | Triggers the sensitive-info guard — replies with a refusal canned message. Fine in a security-review demo, awkward in a sales-tool demo. |
| *"Show me a Tesla"* | We have no Teslas in inventory. The fabricated-inventory guard will redirect. Demonstrates compliance but reads like a failure to a non-technical audience. |
| *"What's the APR on financing?"* | Triggers the rate-inquiry canned response (compliance — we can't quote rates). Same audience-mismatch issue as above. |
| Trade-in valuation prompts (*"What's my 2018 Escape worth?"*) | Path exists but the LLM can fall into recommending an external valuation tool. Uneven demo experience. |
| Multi-pivot conversation (4WD truck → cash car → back to truck) | Intent-shift reset works, but the 3rd pivot can confuse the model_followup anchor. The DEMO_PROMPTS scenarios are linear; keep it that way. |
| Anything with the words *"both"* + 3+ matched cards | The both-wording scrub catches it, but the customer briefly sees a slightly artificial *"these options"* substitution if they're watching closely. |
| Any prompt that needs the manager dashboard | The dashboard works, but its own demo flow is a separate script (not yet written). Stay in the chat for this 5-min flow. |

---

## Common audience questions + short answers

| Question | Short answer |
|---|---|
| *"Is this hooked up to our DMS?"* | Not in the demo build — uses a 90-vehicle seed inventory. Production wiring is a separate integration. |
| *"What model is this?"* | Ollama llama3.2:latest, 3.2B parameters, runs locally. The post-LLM scrub layer is what makes a small model viable. |
| *"How does it know the math is right?"* | Backend computes payments deterministically. The LLM is told the numbers and a post-LLM check catches any drift before the customer sees it. |
| *"Can it lie about a vehicle we don't have?"* | If it cites a Stock # not in the matched set, the fabricated-inventory guard replaces the whole reply. Drivetrain claims that contradict the card get the offending sentence stripped. |
| *"What about W.A.C. compliance?"* | When a customer signals cash, financing language including *"with approved credit"* is stripped post-generation. When they're financing, W.A.C. qualifiers are preserved. |
| *"How long did this take to build?"* | Behavior-enforcement layer landed in 17 polish items across a few sessions. See `docs/handoffs/SESSION_002_..._snapshot.md` and `SESSION_003_demo_polish_snapshot.md`. |

---

## What success looks like (definition)

After the 5-prompt flow:
- The audience has seen 3 vehicles surface, then a single deep
  dive on one, then a decisive recommendation.
- No card has shown a debug stock number (`-DBG`,
  `DEBUG-`, etc. — filtered server-side).
- No prose has mentioned a monthly payment or W.A.C. during
  the cash-mode segment.
- No reply has been longer than 3-5 sentences.
- One natural close question has appeared at the end of every
  reply.

If the audience nods and asks *"can we use this with our actual
inventory?"* — the demo worked.

---

## Recovery plan if something goes wrong

### Backend unavailable

- The chat input shows the spinner and eventually returns an
  error banner. Don't click around — narrate calmly: *"The
  backend's offline; let me restart it."*
- In a fresh terminal: `cd backend && python manage.py runserver
  0.0.0.0:8001`. Wait 2-3 seconds, refresh the browser tab.
- Chat history is per-session (UUID). A page refresh starts
  fresh.

### LLM produces something embarrassing

- The post-LLM scrub layer should catch most things. If
  something does slip through:
  - Don't pretend it didn't. *"That one slipped through — the
    scrub layer has 14 stages but they're not infinite. The
    behavior contract is enforced; the voice is iterating."*
  - Move to the next prompt. Don't try to recover the bad
    turn.

### A demo prompt produces 0 cards

- Possible if the dev DB seed got modified. *"I'd expect to
  see [N] cars under $15k here — the inventory got resliced.
  Let me show you the next prompt."*
- Move on. Don't try to debug live.

### The audience asks a question you can't answer

- *"Good question — that's in the
  `SESSION_003_demo_polish_snapshot.md` doc. Let me get back to
  you with the specific code path."*
- Don't guess. The codebase has clear anchors; consult after.

---

## Reference

- Test baseline: **1111 pass, 1 skipped, 0 failed**
- Stack: Django 5 + DRF + SQLite (`:8001`), React 18 + Vite +
  Tailwind (`:5173`), Ollama llama3.2:latest (`:11434`)
- Scrub stack: see `docs/FREEDOM_FORD_BEHAVIOR_LAYER.md` *Post-LLM
  Enforcement Layer* section (14 stages + length cap)
- Implementation log: `docs/handoffs/SESSION_003_demo_polish_snapshot.md`
- Last commit: `a5c8b46 Polish dealer demo response voice`
