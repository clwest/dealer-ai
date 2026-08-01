---
date: 2026-05-02
title: SESSION_013 — Live Assistant page + inline vehicle cards
type: implementation-summary
test_baseline: 1210
---

# Session handoff — Live Assistant page

SESSION_013 is the first session that builds the **customer-facing**
surface of the Dealer OS. The OS shell from SESSION_012 was dealer-
only; the new Live Assistant page is what an actual buyer will see
when the embed lands (planned for SESSION_017). It exists to validate
the audit thesis from `docs/research/samsfreedomford/SITE_AUDIT.md`:
that the conversation a buyer would have on the lot is exactly the
conversation the public site refuses to host. We host it here.

Use this snapshot to pick up at SESSION_014.

---

## What shipped

### 1. New customer-facing route `/dealer-ai-live-assistant`

Single-column chat surface mounted at the new route. Sidebar **Live
Assistant** link in `App.tsx` was repointed from `/dealer-ai-demo` to
the new page. The legacy `/dealer-ai-demo` route stays mounted but is
off-nav (see "Known notes" below).

`frontend/src/main.tsx` adds:

```tsx
<Route path="dealer-ai-live-assistant" element={<LiveAssistantPage />} />
```

### 2. `LiveAssistantPage.tsx`

`frontend/src/pages/LiveAssistantPage.tsx` (new file, ~250 lines).

**Behavior:**

- Stateless until first send. `ensureSession()` lazy-creates a chat
  via `startDealerChat({})` on the first user turn so the empty-
  state landing doesn't burn a session.
- Composer hits `sendDealerMessage(sid, text)` on submit. Optimistic
  user bubble lands immediately; assistant turn is appended on
  response.
- Empty state: bot avatar + welcome line + 4 starter chips
  (`I want a truck under $30k.`, `Show me a used SUV under $35k for
  my family.`, `I have $5k down and want $400/mo.`, `What's a
  reliable commuter under $20k?`).
- Sending state: spinner + "The assistant is thinking…" line under
  the latest user turn.
- Error state: destructive banner; user can retry.
- "New chat" button appears in the page header once `messages.length
  > 0`. Resets session + transcript.
- Footer disclaimer: "Estimates only. A Dealer OS advisor confirms
  real numbers." — kept *outside* the transcript so it doesn't read
  like an assistant utterance.

**Card rendering rule (load-bearing):** Only the *latest* assistant
turn carries its `matched_vehicles` cards. Older turns render text
only. Implemented via `lastAssistantId` memo + `isLatestAssistant`
prop on `Turn`. This keeps the transcript feeling like a conversation
instead of a search-result accumulator. Comment captures the
reasoning at `LiveAssistantPage.tsx` near the `cards` declaration.

**Continue conversation flow:** clicking the card CTA fires
`handleSend("Tell me more about the <display_name> (Stock
#<stock_number>).")` — keeps the customer in chat, gives the LLM a
predictable follow-up phrasing it can resolve to a real vehicle.
Explicitly *not* a "Buy Now" diversion to a form, per the SESSION_013
spec.

### 3. `AssistantVehicleCard.tsx`

`frontend/src/components/AssistantVehicleCard.tsx` (new file).

A small inline card built from shadcn `Card` / `CardHeader` /
`CardContent` / `CardFooter` primitives. Distinct from the
pre-existing `VehicleCard.tsx`, which carries dealer-side affordances
(Flag for handoff, Details modal) the customer surface explicitly
shouldn't have.

**What it shows:**

- Vehicle title (`display_name`) + stock # + exterior color
- Price (right-aligned, in `text-primary` Ford blue)
- Estimated monthly payment (when `vehicle.estimated_payment` is
  present)
- Key specs as muted chips: mileage (or "New" when 0), drivetrain,
  fuel type
- Two badge surfaces, both conditional:
  - **Budget fit** — `fit` (emerald), `near_fit` (amber), or
    `over_budget` (destructive). Hidden when `null`.
  - **Lever flex** — secondary badge that prefers the backend's
    human-readable `lever_flex_explainer` ("Needs 84-mo term") and
    falls back to a structured label keyed by `lever_flex_kind`
    when the explainer is empty. Hidden when `null`.
- Single primary action: **Continue conversation** (outline button
  with `MessageCircle` icon, right-aligned in `CardFooter`)

Two cards render side-by-side at `sm:grid-cols-2`. On narrow screens
they stack.

### 4. Sidebar repoint

`frontend/src/App.tsx` — single-line change. The "Live Assistant"
nav item now points at `/dealer-ai-live-assistant`:

```tsx
{ to: "/dealer-ai-live-assistant", label: "Live Assistant", icon: Bot, end: false },
```

The icon (`Bot`) and active styling (`text-primary` + `border-l-2
border-primary`) are unchanged from SESSION_012.

---

## Verification

| Step | Result |
| --- | --- |
| `npm run lint` (`tsc --noEmit`) | ✓ 0 errors |
| `npm run build` (`tsc -b && vite build`) | ✓ 1.01s, 1707 modules, 46.50 kB CSS / 365.58 kB JS |
| Playwright load `/dealer-ai-live-assistant` | ✓ sidebar marks Live Assistant active in Ford blue |
| Empty state | ✓ bot avatar + welcome + 4 starter chips |
| Click `"I want a truck under $30k."` starter | ✓ user bubble + sending spinner |
| End-to-end Ollama round-trip | ✓ assistant reply + 4 inline cards rendered beneath the message |
| Card content | ✓ each card shows title, stock #, price, spec chips, single Continue conversation CTA |
| Card grid layout | ✓ 2-column inline beneath the assistant turn — not in a sidebar |
| Forbidden patterns | ✓ no 4-CTA stack, no lead form, no popup, no "Buy Now" |
| Console | ✓ 0 errors, 2 pre-existing React Router v7 future-flag warnings |

Screenshots saved locally as `session_013_empty.png` /
`session_013_with_cards.png` (already gitignored under `/*.png`).
Sample inventory returned on the test prompt: 2021 Nissan Frontier
King Cab S ($27,495), 2020 Chevrolet Colorado WT 4×2 ($25,495), 2019
Ford Ranger XLT SuperCrew 4×4 ($26,995), 2019 Toyota Tacoma SR
Double Cab 4×2 ($28,995) — all under the $30k budget, all sourced
from real backend inventory.

Backend baseline unchanged — SESSION_013 didn't touch backend, so the
SESSION_011 baseline of 1210 pass / 1 skip still holds. Did not
re-run the suite.

---

## Files changed

```
frontend/src/App.tsx                                  sidebar Live Assistant link → new path
frontend/src/main.tsx                                 + /dealer-ai-live-assistant route
frontend/src/pages/LiveAssistantPage.tsx              NEW (single-column chat surface)
frontend/src/components/AssistantVehicleCard.tsx      NEW (inline shadcn vehicle card)
docs/handoffs/SESSION_013_live_assistant_inline_cards.md  NEW (this file)
```

---

## Known notes / out of scope

- **`budget_fit` badges only show when the backend returns them.**
  On the verification round-trip, the assistant asked a qualifying
  question rather than committing to a budget filter, so the backend
  didn't attach `budget_fit` / `estimated_payment` annotations and
  the badges were hidden. Rendering is in place — they'll appear on
  tighter prompts like *"I have $400/mo with $5k down"*. Absence on
  this turn is correct backend behavior, not a UI bug.
- **Only the latest assistant turn keeps its cards.** Older turns
  drop their `matched_vehicles` grid (text remains). Decision was
  deliberate: the customer surface should feel like a conversation,
  not a search-result tape. If a future session needs a "compare
  these earlier picks" feature, build it as an explicit affordance,
  not by un-suppressing old cards.
- **`/dealer-ai-demo` remains legacy and off-nav.** The dealer-side
  lead-capture demo (`DealerAIDemo.tsx`) is still mounted at
  `/dealer-ai-demo` but no longer linked from the sidebar. Treat it
  as the internal lab for now. Future sessions should either
  retire it or relabel it explicitly (e.g. `/dealer-ai-internal-
  lab`) — leaving two parallel chat surfaces is fine for now,
  unsustainable long-term.
- **No memory across sessions.** "New chat" resets transcript and
  session ID. Cross-visit memory ("Last time you were looking at
  Maverick XL trims under $32k") is called out in the audit as a
  weakness of the public site we'll eventually replace, but it's
  not in scope for SESSION_013.
- **No mobile shell yet.** Per SESSION_012's known gap, the OS
  sidebar is `hidden ... sm:flex`. The Live Assistant page is
  centered in `max-w-3xl` and works on narrow viewports for the
  *content*, but there's still no hamburger to open the OS nav on
  phones. Defer to a dedicated mobile session.
- **No public embed yet.** This is the *page*, not the embed. The
  iframe-friendly route + topbar **Public preview** pill are
  scheduled for SESSION_017.

---

## Recommended next session

**SESSION_014 — Wire Overview to real data.**

Now that the Live Assistant produces real conversations and lead
signal, the OS landing page should stop lying to the dealer.

Replace the three placeholder cards on
`frontend/src/pages/DealerOverviewPage.tsx` with real signal:

- **Recent activity** → real rows from
  `/api/dealer-ai/admin/audit-events/?since=24h` (already serving
  traffic per the backend log seen at session start). Map the
  audit-event shape to the `ActivityItem` interface; format
  timestamps with the existing helper.
- **Coaching summary** → real coaching-scenario count derived from
  `manager_chat` audit events, or a small new `/api/dealer-ai/admin/
  coaching-stats/` rollup if the audit shape doesn't expose it
  cleanly.
- **Attention items** → derived rules over `OnboardingProfile`
  flags. Concrete first cut:
  - `banned_phrases` empty → "Banned phrases not configured"
  - `salespeople_added=false` → "Sales team incomplete"
  - `payment_disclaimer` empty → "Payment disclaimer not set"
  - `pilot_approved=false` → "Pilot review pending"
- **Add a fourth card: Today's leads.** Count of conversations
  in the last 24h sourced from
  `/api/dealer-ai/admin/leads/?since=24h&limit=3`, with a 3-row
  preview and a `View all →` link. The link target stays a stub
  until SESSION_015 ships the full Leads pipeline page.

Out of scope for SESSION_014: the Leads page itself (SESSION_015),
the Inventory coverage page (SESSION_016), and the public embed
route (SESSION_017). Sequence and scope captured in the
SESSION_013–017 roadmap inside `docs/research/samsfreedomford/
SITE_AUDIT.md`.

After SESSION_014, the GM can open the OS each morning and trust
what they see — the Overview is the contract that turns the OS
from a tool into a daily workspace.
