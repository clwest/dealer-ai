# Dealer AI — Demo Script

This is the script to run when showing the system to dealership management. It
assumes the app is running locally:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Default LLM: local Ollama (`llama3.1`) — no paid API calls

## One-time setup before any demo

```bash
# Backend
cd backend
source .venv/bin/activate
python manage.py migrate
python manage.py seed_demo_vehicles
python manage.py seed_demo_scenarios   # populates dashboard with realistic leads
python manage.py runserver

# LLM
ollama pull llama3.1
ollama serve

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/dealer-ai-demo` in a browser. Have the **Manager
dashboard** open in a second tab at `http://localhost:5173/dealer-ai-admin`.

If you want a clean slate at any moment during the demo, click **Demo controls
→ Reset demo** on the demo page (or **Reset demo** on the dashboard). To bring
the dashboard back to a "five active customers" state, click
**Demo controls → Load demo scenarios**.

---

## 5-minute demo (when you have one elevator pitch)

> **Goal**: prove the AI does three things — finds the right vehicle, talks
> honestly about money, and produces a usable handoff for sales.

| Time | What you do | What you say |
| --- | --- | --- |
| 0:00 | Open the demo page. Click **Demo controls → Load demo scenarios**. | "Before I show you the AI in action, I'm going to load five sample customer chats so the manager dashboard isn't empty." |
| 0:30 | Click **Manager dashboard** in the top nav. | "This is the view your sales manager sees. Five chats, four leads, average target payment, and a budget-mismatch counter." |
| 1:00 | Click any lead row → **Lead detail modal** opens. | "Every captured lead gets an AI summary, a recommended next action, and a draft first message your salesperson can copy and send." |
| 1:30 | Click **Copy full handoff** → paste into a notes app to show the format. | "This is what they paste into their CRM or text the customer. Friendly, accurate, no invented numbers." |
| 2:00 | Click **Customer demo** in the top nav. Click **New chat**. | "Now let me show you what the customer sees." |
| 2:15 | Click the suggested prompt **"I need a used SUV under $30k for my family."** | "Watch — it answers using only what's actually in your inventory." |
| 2:45 | When matched vehicles appear, click any card → **Details**. | "From any matched vehicle the customer can ask questions about that specific vehicle — towing, payments at their budget, comparisons." |
| 3:15 | In the modal, click **"Would this fit a $600/month budget?"**. | "It runs the math against three loan terms and tells the customer the truth — including when the vehicle is a stretch." |
| 4:00 | Click **Talk to a real advisor →** at the bottom of the chat. Fill in name + phone. Submit. | "When the customer is ready, this captures the lead. The summary I showed you on the dashboard? That's auto-generated from this conversation." |
| 4:45 | Switch back to **Manager dashboard** tab. Refresh. | "There's the new lead, ready for handoff." |

**Wow moments to land hard**:
- The AI **says no honestly** to unrealistic budgets ("$78k Lariat at $500/mo? Math says closer to $36-40k.")
- The handoff packet has **zero copy-paste work** — name, phone, vehicles flagged, summary, and a draft message all in one click.
- All of this runs **on a local model** — no per-query API cost.

---

## 15-minute demo (when management wants to dig in)

### Act 1 — Customer experience (5 min)

1. **Open the demo page.** Click **Reset demo** to start clean.
2. **Type a real customer-style prompt**: *"Looking for a 2023 or newer F-150 around $700/month, I have $5,000 down."*
   - Point out: it parsed the budget signals (target $/mo + down) and the model.
3. **Click the top matched vehicle → Details.** Show the modal.
   - **Payment table** for 60/72/84 months.
   - **Affordability notes** that change based on the customer's stated budget.
   - **Suggested questions** like *"Is this good for towing?"* — click one and read the AI answer aloud.
4. **Click "Compare this to similar options"** in the suggested questions.
   - Show that it stays grounded — it only references vehicles in the similar-inventory block, never invents a model.
5. **Talk about the limits**: "It tells the customer when something needs a real advisor. Watch."
   - Type: *"Can you guarantee approval on a 96-month term?"*
   - The AI declines to promise terms it can't quote — a real reason this is dealership-safe.

### Act 2 — Sales manager view (5 min)

6. **Click Manager dashboard.**
7. **Walk through the cards** left to right: chats, leads, average budget, budget mismatches.
   - "The mismatch counter is the number I'd watch — it's how often a customer is reaching past their stated budget. That's a coaching moment for sales, not a problem."
8. **Click "Top requested models" / "Top requested vehicle types"**.
   - "This is real demand signal. If trucks are 80% of chats this week, that's a marketing input."
9. **Click a lead row** → handoff modal.
10. **Read the suggested message aloud.** Note that it:
    - Uses the customer's first name.
    - Mentions specific vehicles they were interested in.
    - Suggests one concrete next step.
    - Doesn't invent rates or rebates.
11. **Click Copy full handoff** → paste somewhere visible.
    - "This is what your salesperson texts the customer 30 seconds after the lead lands. No more 'I'll call you back when I'm at my desk'."

### Act 3 — Operations / safety (5 min)

12. **Open a terminal alongside the browser.** Run `python manage.py import_inventory --file sample.csv --dry-run`.
    - "We can ingest your real inventory feed. Dry-run first to validate."
13. **Switch back to the demo page.** Click **Demo controls → Reset demo**.
    - Mention: "Reset wipes the demo conversations. Your real imported inventory is preserved — different data source."
14. **Show the LLM provider switch** in `backend/.env`:
    ```
    DEALER_AI_LLM_PROVIDER=ollama   # local, free
    # DEALER_AI_LLM_PROVIDER=openai # OpenAI gpt-4o-mini
    ```
    - "We can run this entirely on a machine in the dealership — no per-query bill — or flip to OpenAI if you ever want to."
15. **Show that no real email/SMS goes out without a person clicking send.**
    - Open the handoff modal again and point at the "No emails or texts are sent automatically" sidebar note.
    - "This is intentional. Your salespeople own the contact moment. The AI prepares them, it doesn't pretend to be them."

---

## What to click — quick reference

| Action | Where |
| --- | --- |
| Customer chat | `/dealer-ai-demo` |
| Demo controls (load / reset / prompts) | Right sidebar of demo page |
| Manager dashboard | Top nav → "Manager dashboard" |
| Reset demo button | Manager dashboard top-right (and demo page sidebar) |
| Lead handoff modal | Click any lead row in the dashboard |
| Vehicle detail / ask | Click any matched-vehicle card → "Details" |
| Lead capture | "Talk to a real advisor →" link below chat input |

## Suggested customer prompts to use live

These match the seeded scenarios — the AI's responses will feel realistic
because the inventory backs them up.

1. "Show me F-150s under $65k with $5,000 down." — discovery + budget signal.
2. "I need a used SUV under $30k for my family." — budget-aware, used inventory.
3. "Can I get close to $500/month on a truck?" — budget-mismatch coaching when paired with a Lariat ask.
4. "What's good for commuting from the city but still useful on the farm?" — Oklahoma-flavored capability ask.
5. "I need something that can tow a small camper." — capability + practicality.
6. "Do you have affordable service or oil change options?" — service triage (not a sales lead).

---

## Wow moments — narrate them

When these land, **stop and say so out loud**. Don't let them slip past:

- **Honest budget pushback.** When the AI tells a customer the $78k Lariat is a stretch on $500/mo and offers alternatives, say:
  > "That's the line the dealership normally has to deliver in person. The AI gets it out of the way before the customer walks in — which means the test drive is about the right vehicle, not a renegotiation."
- **Real inventory only.** When matched vehicles appear, say:
  > "Notice these are stock numbers. The AI literally cannot recommend a vehicle you don't have on the lot. No phantom inventory."
- **Zero-effort handoff.** When you click Copy full handoff, say:
  > "Thirty seconds, no typing. Compare that to the time it takes to summarize a chat conversation by hand."
- **Local model.** When the inventory CSV import runs, say:
  > "Everything you saw — the chat, the matching, the summaries — runs on a local model. There's no AI subscription cost per customer."

---

## Follow-up questions to ask the dealer

End the demo with these. The answers tell you whether to ship and what to ship next.

1. **What does your current lead capture look like end-to-end?** Are leads coming in as web forms, calls, walk-ins, or texts?
2. **How does your sales team prefer to receive a new lead?** CRM? Slack? SMS? Phone call from BDC?
3. **What inventory feed do you have today?** CSV export? DMS API? Scrape from your public site? (We support CSV today and can add the rest.)
4. **What's the biggest frustration with your current online chat or lead form?** ("Customers ghost," "leads are unqualified," "we don't know which trucks they actually saw" — each one points at a different feature.)
5. **What's a realistic pilot scope?** A page on the public site? An after-hours-only widget? A test on a single salesperson's customers?
6. **Who in the dealership would own the AI handoff dashboard?** Sales manager? BDC lead? GM?
7. **What's the one number that makes this a business win for you?** (Test drives booked? Leads-per-month? Time-to-first-contact?)

If they're noncommittal, the simplest follow-up offer:

> "Give me a real CSV export of your inventory and I'll have this running with your stock by next week. Free pilot, no commitment."

---

## Troubleshooting during a live demo

| Symptom | Fix |
| --- | --- |
| Chat says "trouble reaching the local AI model" | `ollama serve` not running. Start it in a side terminal. |
| Vehicle cards don't appear | Run `python manage.py seed_demo_vehicles` again. |
| Manager dashboard is empty | Click **Demo controls → Load demo scenarios**. |
| Looks stale after a previous demo | Click **Reset demo** in the sidebar. Imported inventory survives. |
| Need to start from absolute zero | `python manage.py flush --no-input && python manage.py migrate && python manage.py seed_demo_vehicles && python manage.py seed_demo_scenarios` |
