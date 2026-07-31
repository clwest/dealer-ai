---
title: Copper Canyon Auto — 5-minute demo script
status: active
persona: Copper Canyon Auto (Yuma, AZ — invented independent-dealer persona)
generated: 2026-07-31
baseline_commit: 4041b91
test_baseline: 1272 backend tests passing (dealer_ai suite)
supersedes: Freedom Ford demo script (docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md)
              is retained as the franchise-config reference.
---

# Copper Canyon Auto — 5-minute demo script

Run this script when showing the AI Sales Assistant to independent-dealer
prospects (owner-operators, sales managers at BHPH / used-car lots).
Goal: prove the system handles indie customer shapes — cash-and-carry,
credit-challenged buyers, mixed-make used inventory, BHPH conversations
— and stays compliant, without hand-waving.

Copper Canyon Auto is a *2nd-generation, 40–60-vehicle, mixed-make
used lot in Yuma, AZ*, owned by Elena Vargas (dad Manuel started it
in 1987). Financing runs through a subprime lender panel + in-house
BHPH; no OEM captive. See `docs/INDEPENDENT_DEALER_PIVOT.md` for the
full persona.

## Setup (60 seconds before the demo)

1. Backend on `:8001`. LLM provider = OpenAI `gpt-5-mini`
   (`OPENAI_API_KEY` in `.env`). Confirm with a
   `POST /api/dealer-ai/chat/…` smoke test if in doubt.
2. Frontend on `:5173`.
3. **Seed the Copper Canyon inventory:**
   `cd backend && python3 manage.py seed_copper_canyon_demo`.
   Confirms 45 units created / updated.
4. Optional but recommended: set the dealer name in the environment
   or the onboarding form so `useBrand()` / `get_dealer_name()`
   render "Copper Canyon Auto" everywhere:
   - Env: add `DEALER_AI_DEALER_NAME=Copper Canyon Auto` to `.env`
     and restart Django.
   - UI: `/dealer-ai-onboarding` → set *Dealership name* + save.
5. Open `http://localhost:5173/` in a clean browser tab.

If the backend is down: fall back to explaining the deterministic
math + scrub stack from `docs/CAPABILITY_MATRIX.md`.

---

## Presenter talking points

Drop one at a natural pause:

- *"Independent-dealer mode is on by default — the assistant never
  says 'brand new', 'certified pre-owned', or 'Ford Credit'. If the
  LLM tries, the post-LLM scrub catches it."*
  (Best after Prompt 3 or 4, when BHPH / credit conversation lands.)
- *"This isn't a franchise assistant with the OEM branding filed off —
  it's a real indie-shaped voice: credit-inclusive, payment-first, no
  manufacturer captive to lean on."*
  (Best at the close, after Prompt 5.)

---

## The 5-prompt flow

| # | Prompt | ~ time | What it proves |
|---|---|---|---|
| 1 | *"I need a work truck, got about $8k cash to spend"* | 30s | Cash-mode detection, price-first ranking, mixed-make surfacing (Tacoma, Ranger, older Silverado), no financing pitch |
| 2 | *"Looking for a reliable SUV, I can do about $250 a week"* | 45s | BHPH-shaped ask, weekly-payment framing, credit conversation opener, no specific-APR quote |
| 3 | *"My credit's not great, will I still qualify?"* | 30s | Credit-tier acknowledgement without judgment, path forward (advisor / in-house), no manufacturer-captive hallucination |
| 4 | *"What about the Toyota Tundra? I've got a trade-in"* | 30s | Model anchor across makes, trade-in dynamics, no fabricated appraisal, honest "advisor confirms number" language |
| 5 | *"Which one would you show first?"* | 30s | Decisive lead-with-pick recommendation, salesperson voice, indie-friendly framing (no CPO / manufacturer warranty) |

Total: ~3 minutes of prompts + ~2 minutes of explanation.

---

## Prompt 1 — *"I need a work truck, got about $8k cash to spend"*

### What it proves

- Cash-mode detection: no monthly-payment math, no W.A.C. language.
- Price-first ranking under the indie default (no OEM primary-make
  bias).
- Mixed-make surfacing: the response should mention units from
  different brands, not lean into any single make.

### Expected behavior

- Cards on the right show units at or under $8k — Toyota Tacoma
  (2012 PreRunner), Ford Ranger (older XLT), Kia Forte, or the
  under-$5k Focus.
- Reply picks one and frames the trade-off honestly: e.g., *"The
  older Tacoma PreRunner at $12,495 stretches the budget but the
  4.0L V6 lasts forever; the older Ranger comes in at $8,995 and
  is closer to your cash number, but has 176k miles. Want to see
  the Ranger up close, or should we look at what a couple hundred
  more opens up?"*

### If it goes off-script

If the reply pitches financing on a cash-declared budget → the
scrub stack should catch it. If it doesn't, that's a bug worth
capturing.

---

## Prompt 2 — *"Looking for a reliable SUV, I can do about $250 a week"*

### What it proves

- Weekly-payment ask is native indie territory. The assistant
  should engage with the weekly cadence, not silently convert to
  monthly.
- The `INDIE_MODE_HINT` scaffolding tells the LLM this indicates
  a BHPH conversation is on the table. The assistant should
  acknowledge in-house / weekly financing exists without quoting
  a specific APR.

### Expected behavior

- Cards on the right show mid-priced SUVs: CR-V, RAV4, Rogue,
  Equinox, Escape, or older Highlander.
- Reply should either (a) ask a clarifying credit-range question
  or (b) surface 1–2 SUVs and note that weekly payments are
  something the advisor can walk through in detail. Never quotes
  a specific weekly payment number without a BUDGET ANALYSIS
  block backing it.

### If it goes off-script

If the reply fabricates a specific weekly payment (e.g., *"about
$225 a week over 30 months"*) → that's a payment-inference leak
the LLM shouldn't make. Real weekly math needs the BHPH engine
call, not vibes.

---

## Prompt 3 — *"My credit's not great, will I still qualify?"*

### What it proves

- Credit-tier conversation is normal at Copper Canyon and the
  assistant handles it without judgment (per `INDIE_MODE_HINT`).
- No OEM captive lender is invented (post-LLM `indie_prohibited_copy`
  scrub catches "Ford Credit" / "Toyota Financial" if the LLM leaks).
- Path forward is offered: in-house / advisor walk-through.

### Expected behavior

- Warm acknowledgement of the customer's credit reality.
- Explanation that the dealership works with multiple lenders,
  including in-house options for credit-challenged buyers.
- Handoff opener: "Let's have an advisor walk through the specifics
  — we'll get you into something reliable" — with no specific APR /
  rate quote.

### If it goes off-script

If the reply says "Ford Credit approved" / "0% APR available" /
"certified pre-owned warranty" — the indie scrub should strip
those. Grep the logged reply for `indie_prohibited_copy` in the
scrub-fired flags.

---

## Prompt 4 — *"What about the Toyota Tundra? I've got a trade-in"*

### What it proves

- Model anchor across makes (`_MODEL_TO_MAKE` covers Ford models;
  the LLM handles broader mixed-make anchoring).
- Trade-in dynamics: acknowledged, but no fabricated dollar amount
  (SYSTEM_PROMPT rule + pre-LLM external-value guard).
- Honest "an advisor from Copper Canyon Auto can run a real
  appraisal" language when appraisal-adjacent questions come up.

### Expected behavior

- Card for the 2016 Toyota Tundra SR5 surfaces.
- Reply describes the specific unit (year, mileage, engine),
  acknowledges the trade-in interest, and offers to have an
  advisor confirm the trade-in valuation. Never invents a
  Kelley Blue Book number or a specific trade-in credit.

### If it goes off-script

Fabricated trade value ("your trade is probably worth around $8k")
→ scrub or refuse. External-value guard should short-circuit before
the LLM sees a trade-value question that names an outside source.

---

## Prompt 5 — *"Which one would you show first?"*

### What it proves

- Decisive lead-with-pick recommendation, not a neutral spec-sheet
  comparison.
- Voice stays warm and practical — the Elena Vargas persona
  ("straight talk on payments and credit").
- No franchise-shaped franchise language (no "brand new", no CPO,
  no manufacturer warranty).

### Expected behavior

- Reply picks ONE unit from the current session's cards and gives
  one clear reason it leads. Backup pick mentioned qualitatively.
- Soft close: "Want me to line one up?" / "Want a closer look?"
  — but never a fabricated appointment time.

### If it goes off-script

Neutral side-by-side prose (spec sheet dump) → the SYSTEM_PROMPT's
cash-mode / cards-shown directive should prevent this. If a
research-brief shape lands, that's the reply's structural
regression.

---

## Fallback talking points — backend unavailable

If the backend is down mid-demo:

- Talk to `docs/CAPABILITY_MATRIX.md` — walk the auditor through the
  8-stage pre-LLM guard and 8-stage post-LLM scrub stack (plus the
  new `indie_prohibited_copy` scrub).
- Deterministic backend math + BHPH periodic amortization runs
  regardless of LLM state — see
  `backend/dealer_ai/services/payment_engine.py` and
  `test_bhph_payment_engine.py`.
- Explain that dealer identity is templated at runtime — Copper
  Canyon is the *shipped default*, but a franchise config
  (`DEALER_AI_DEALER_TYPE=franchise`, `DEALER_AI_PRIMARY_MAKE=Ford`,
  etc.) re-enables the Freedom Ford voice without any code changes.

## What this script does NOT cover (yet)

- **Onboarding form for indie fields** — Phase 3 work. The
  dealership can override name and voice today; BHPH-enabled,
  lender panel, warranty offering, credit range served, and
  make mix are on the `DealerProfile` in code but not yet in the
  UI form.
- **Live BHPH card UI** — the payment engine has the math, but
  the frontend cards render standard-loan monthly figures.
  Phase 3 will surface weekly / biweekly for BHPH-eligible units.
- **Copper Canyon logo + palette** — Phase 3 rebrand ships
  `brand.*` Tailwind tokens replacing `ford.*` and a placeholder
  Copper Canyon logo asset.

Until Phase 3 lands, the demo shines on backend behavior and voice.
The chrome is still franchise-legacy in places.
