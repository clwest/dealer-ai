---
title: Copper Canyon Auto — 2-minute owner demo
status: active
persona: Copper Canyon Auto (Yuma, AZ — invented independent-dealer persona)
generated: 2026-09-01
baseline_commit: TBD
test_baseline: 5,073 backend tests passing (dealer_ai suite)
supersedes: Dealer OS demo script (docs/DEMO_SCRIPT.md, kept as a
              franchise-config reference — DO NOT run for a Copper
              Canyon demo)
---

# Copper Canyon Auto — 2-minute owner demo

Show this to an owner-operator or sales manager at a subprime-friendly
independent lot. Goal: prove the product does two things no competitor
does, then sweep the supporting screens. Chat is the hook, not the
spine.

Copper Canyon Auto is a 2nd-generation, ~50-vehicle mixed-make used lot
in Yuma, AZ. Owner: Elena Vargas (dad Manuel founded it in 1987).
Financing runs through a subprime lender panel plus in-house BHPH. No
OEM captive. Persona lives in
`docs/research/INDEPENDENT_DEALER_PIVOT.md`.

**Do not read this script cold. Do the setup first, click through it
once yourself, and check that the numbers on the page match what's
written here.** The state was clicked and screenshotted on 2026-09-01.

---

## Setup (60 seconds before the demo)

```bash
# One terminal — backend on :8001
cd backend
rm -f db.sqlite3
python3 manage.py migrate --run-syncdb --noinput
python3 manage.py seed_copper_canyon_auto_demo
python3 manage.py runserver 127.0.0.1:8001 --noreload

# Second terminal — frontend on :5173
cd frontend
VITE_API_PROXY_TARGET=http://127.0.0.1:8001 \
  npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Seed runs in about **2 seconds** from an empty SQLite and lands a
coherent working store:

- **130 vehicles**, one trailing month of sales at ~50/month.
- **45 sales** — 43 delivered to `off_market`, 2 held at
  `hold_reserved` (signed-contract-awaiting-wire and open-stipulation-
  awaiting-docs).
- **All 12 lifecycle stages populated.**
- **Trial balance balances** at $985,711 both sides.

Open `http://127.0.0.1:5173/login` and sign in as
**`demo-owner` / `demo-owner-password`**. You land on
`/dealer-ai-overview`, the owner dashboard.

**LLM provider.** The default in this repo's `.env` is
`DEALER_AI_LLM_PROVIDER=openai` with `OPENAI_MODEL=gpt-5-mini`. That
model uses the reasoning-completions parameter shape (`max_completion_
tokens`, no `temperature`), which the pinned `openai==1.30.5` SDK
doesn't accept — so every chat completion currently falls back to the
"I'm having trouble reaching the AI service" fixed message. The chat
opens and reads clean, but the reply won't be model-generated. If a
live-model demo matters, either bump the SDK (see the pinning tradeoff
in `TASK_c2c3-lot-shape-and-demo-script.md`) or set
`OPENAI_MODEL=gpt-4o-mini` before booting.

---

## The 2-minute flow

Two minutes total. Two spine screens. Everything else is the
supporting sweep.

| # | Screen                                                 | ~ time | What it proves                                                       |
|---|--------------------------------------------------------|--------|----------------------------------------------------------------------|
| 1 | Chat opener (Live Assistant)                            | 20s    | Persona voice + budget-aware. Every competitor has this — cover fast |
| 2 | **Recon authorization gate** (Inventory → RS-07 recon)  | 30s    | Nobody else gates recon spend. This is the strongest screen          |
| 3 | **Aging board decomposed by stage** (Analytics → Aging) | 30s    | Every competitor reports aging as one number. Ours splits it 12 ways |
| 4 | F&I chain (F&I Deals + Incoming)                        | 15s    | Signed contract in `pending_funding` + a stipulation waiting on docs |
| 5 | BHPH portfolio (BHPH)                                   | 15s    | 16-note book, aging histogram, $229k principal outstanding           |
| 6 | Trial balance (Accounting)                              | 10s    | Balanced $985,711 both sides — real books, not a mock                |

Nothing here needs a typed URL except the recon page for a specific
stock. Every other step is a sidebar click.

---

## 1. Chat opener — Live Assistant (20s)

**Click:** `Live Assistant` in the sidebar.

**What lands:** A "Find Your Next Vehicle" panel with the persona
greeting *"Hi — I'm Copper Canyon Auto's sales assistant."* and four
starter prompt chips (truck under $30k, $400/mo sedan, family SUV, not
sure yet).

**What to say:** *"Every competitor in this space ships a chatbot. So
we're not going to spend the demo on the chat — I want to show you the
two things that only exist here."*

**Optional tap:** Click the "I need a family SUV with good gas
mileage" chip so the presenter's screen shows the assistant thinking
before you move on. See the LLM note in Setup — the reply is currently
the fallback message; the point of this step is voice and framing, not
the model's answer.

---

## 2. Recon authorization gate — the pitch screen (30s)

**Click:** `Inventory` in the sidebar → paste the URL bar with
`http://127.0.0.1:5173/dealer-ai-inventory/RS-07/recon` or scroll the
inventory grid until you find RS-07 (2016 Nissan Rogue) and click its
**Recon** tile link.

*(Every route the sidebar covers is reachable by a click. The
per-vehicle Recon page is reached via the vehicle row's Recon tile;
there is no sidebar door for "all draft WOs across the lot." That is a
finding worth writing down, not a step to fake.)*

**What lands:** "Recon · Stock #RS-07 · 2016 Rogue." Two condition
findings at the top ("Rear tires below 4/32", "Front brake pads at
3mm"). Below, a **Work orders** section with two rows:

1. WO #2 — outsourced to Desert Auto Repair, status **Completed**,
   $600 estimate / $660 actual.
2. WO #4 — outsourced to Yuma Transmission Specialists, status
   **Draft**, $1,450 estimate, **Authorized: —**.

The draft row is the point. Scroll to it.

**What to say:** *"This is the recon manager saying he wants to send
this Rogue out for $1,450 of transmission work. The estimate came in
above the budget line, so nothing happens until the owner clicks
Approve. Every other product in this category records recon spend
after the vendor does the work. Here the money doesn't move until
the person paying the bill says yes. Two of these are sitting on the
lot right now — pull up RS-17 to see the other one."*

**Optional:** Click **Approve** on WO #4 to show the flow. If you do,
the row moves from Draft to Approved and posts an authorized-cost
number. Skip if you want the queue to still read as a queue at the
end of the demo.

---

## 3. Aging board, decomposed by stage (30s)

**Click:** `Analytics` in the sidebar → **Lifecycle Aging** tab.

**What lands:** "Operational Intelligence" with the Lifecycle Aging
tab active. Two panels:

- **Days at frontline (proxy)** — 15 snapshots, mean p50 ~15 days,
  mean p90 ~71 days, latest 53 vehicles on the front line as of
  today.
- **Stage aging trend** — a p50/p90 line chart with a **Stage:**
  dropdown next to it. Default is Recon.

**What to say:** *"Every dealer software reports 'days in inventory'
as one number. That's useless — the story is completely different
depending on which stage a car is stuck in."*

**Do the click:** Open the **Stage:** dropdown, cycle it through
three stages the audience will recognise — start on **Recon**, then
**Frontline**, then **Off market**. Each one redraws.

*"A car sitting in recon 14 days is a vendor problem. A car sitting
at frontline 60 days is a pricing problem. A car sitting in
photography is a photographer problem. The chart splits into twelve
because the problems are twelve different problems, and behind each
one there's an append-only event log — every transition, every
trigger, every operator who moved it."*

---

## 4. F&I chain — signed contract + open stipulation (15s)

**Click:** `F&I` in the sidebar.

**What lands:** "F&I Deals in Progress" — one row.

- **RS-15** · type `risc` · contract state `signed` · funding state
  `pending_funding`.

**What to say:** *"Signed, funding packet's out to the lender,
waiting on the wire."*

**Click:** `Incoming` in the sidebar (right below F&I).

**What lands:** "Incoming Applications" — two rows. One
"Umbria Rehearsalton" (submitted — awaiting response) and one
"Nathan Wei" (incoming — no writeup yet).

*(**Finding, not a demo step:** the first applicant name is the
archetype's synthetic-tester name — "Rehearsalton" gives it away.
The persona-rename step in the seed touches CustomerLead but not
CreditApplication.applicant_full_name. Note it, don't fix it here —
it'll need a small extension to the persona-rename map in a follow-
up.)*

**What to say:** *"On the other side of the desk, this application is
submitted to the lender waiting on a proof-of-income stipulation.
Both of these deals are 'sold' but neither vehicle has left the lot —
that's what the two hold-reserved units on the sales board are."*

---

## 5. BHPH portfolio (15s)

**Click:** `BHPH` in the sidebar.

**What lands:** "BHPH Portfolio" with four headline cards:

- **16 notes in portfolio** — $229,317 principal.
- **Weighted average APR** — 19.01 %.
- **Weighted average DPD** — 0.0 days.
- **Cure rate** — 100 %.

Below that, an aging histogram (buckets: Current / 1-15 / 16-30 /
31-60 / 61-90 / Over 90 / Charge-off candidate).

**What to say:** *"This is the in-house book. Sixteen active notes,
weekly-pay cadence, weighted APR around 19 %. The aging histogram
splits the book by days-past-due bucket — the collection team works
this every morning."*

*(**Finding, not a demo step:** the aging histogram currently reads
all 16 notes in the Current bucket, cure rate 100 %. The
`_extend_bhph_portfolio` step intended one delinquent note (RS-13,
~20 days past first payment) and one in repossession (RS-10), but
whatever the portfolio endpoint bins on isn't picking them up in the
seed as written. Skip the "look at the delinquent one" line until
that's diagnosed — the 16-note total + APR read is strong on its
own.)*

---

## 6. Trial balance (10s)

**Click:** `Accounting` in the sidebar.

**What lands:** "Trial Balance" — a "Balanced" badge in the top
right, real per-account totals, everything sums.

Highlights on the top rows:

- Cash on Hand — $127,742 debit, $19,490 credit ($108,252 natural).
- Contracts in Transit — $223,463 asset.
- BHPH Notes Receivable — $205,827 asset.
- Recon Work in Process — $379,854 negative natural balance (the
  archetype's acquisition-double-count workaround; see task file for
  the underlying defect).

**What to say:** *"This is the real trial balance for this store's
month. Every sale posts here automatically, every BHPH payment
posts here, every manual journal entry the bookkeeper writes lands
here. It balances at $985,711 both sides. This is not a mockup — it
is the output of a real double-entry system that ran for the last
thirty days of the demo data."*

---

## Fallback talking points — backend down mid-demo

- Talk to `docs/_internal/CAPABILITY_MATRIX.md` — walk the 8-stage
  pre-LLM guard, the 12-stage post-LLM scrub, and the
  `indie_prohibited_copy` scrub.
- Deterministic math still runs — see
  `backend/dealer_ai/services/payment_engine.py` and
  `test_bhph_payment_engine.py`.
- Voice-of-brand is templated: a franchise install
  (`DEALER_AI_DEALER_TYPE=franchise` + `DEALER_AI_PRIMARY_MAKE=Ford`)
  re-enables the franchise voice without a code change.

---

## What this script does NOT cover

- **Sales-side workflows** (walk-in intake, referral picker,
  test-drive scheduling). Those live under Leads and
  `dealer-ai-sales/*` and are worth their own five-minute demo.
- **The AI conversation on live models.** The LLM SDK pin has
  drifted in this environment (see setup note) — every chat reply
  currently reads the fallback. Fix the SDK/model pairing before
  demoing the AI in front of a dealer who will ask it a hard
  question.
- **Delinquent BHPH note detail** — surface-level total is real, the
  per-bucket split needs diagnosis (see the BHPH finding above).

---

## Findings written down (per the session rule)

Recorded here so a future session picks them up, not as
demo-step avoidance.

- **F&I Incoming applicant name is still the archetype's tester
  name** ("Umbria Rehearsalton"). Fix: extend the persona-rename map
  in `_persona_rename_archetype_rows` to touch
  `CreditApplication.applicant_full_name` when the archetype seeded
  it from `SYNTHETIC_NAMES`.
- **BHPH portfolio delinquency is not reading through** even though
  the seed originates RS-13 with `first_payment_days_ago=25` and no
  payments. Endpoint or note-status computation is bucketing
  differently than the seed expects. Diagnose against
  `_extend_bhph_portfolio` and the portfolio endpoint's aging query.
- **No sidebar door for "all draft WOs across the lot"** — the
  authorization queue is per-vehicle only. A cross-lot queue would
  make the recon-gate pitch stronger (one screen shows every pending
  authorization). Follow-up UI.
- **Recon page shows completed WO first, draft WO second** — sort
  order buries the demo-relevant row under history. Consider putting
  drafts and in-progress ahead of completed for the recon dashboard.
