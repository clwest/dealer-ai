---
title: Sam Wampler's Freedom Ford — public site UX audit
date: 2026-05-02
type: research
source: https://www.samsfreedomford.com/
status: reference
---

# Freedom Ford public site — UX audit

Live audit of `samsfreedomford.com` performed via Playwright MCP on
2026-05-02. Pages walked: home, new-vehicle inventory, vehicle detail
page (2025 Maverick XL), Finance Center, Contact. Screenshots captured
locally and not committed (see `.gitignore`).

This document exists to **anchor product decisions** for the Dealer
Operating System: where the existing public site fails the buyer, what
those failures cost the dealership, what the AI assistant replaces,
and what we should build next.

---

## 1. Customer funnel summary

The site is a single-purpose lead-capture funnel. Every CTA, on every
page, terminates in a contact form. There is no online transaction.

**Conversion paths, ranked by surface area:**

1. **"We Want to Buy Your Car!"** trade-in banner — repeated on home,
   inventory, and every VDP. VIN field → "Start My Offer" → form.
2. **"Buy Now"** button on every vehicle card — opens a popup form, not
   a buying flow.
3. **"Get Estimate Payment"** — opens a form, not a calculator.
4. **"Apply Online" / "Apply for Credit"** — finance application form.
5. **"Schedule Service"** — separate service-department form.
6. **"Text us here"** widget (third-party SMS relay) — captures phone.
7. **"Quick Question?" / "Finance Question?" / "Contact"** — three
   different pages with the same nine-field form (name / email / phone
   / comments / agreement).

**Funnel shape:** customer arrives → browses static marketing →
manually filters inventory → reads a wall of specs → fills a form →
waits for a callback. A 2008-era lead funnel inside a 2018 chrome.

**Implicit assumption:** the customer already knows what they want.
There is no entry point for "I need an SUV under $35k for my family."

---

## 2. What the site does poorly

| # | Problem | Cost |
| --- | --- | --- |
| 1 | **Filter sidebar requires the buyer to already know what they want.** Eight checkbox groups (Year, Body Style, Make, Model, Trim, Fuel, Drivetrain, Mileage) with no narrative entry. | Vague-need shoppers bounce. |
| 2 | **Stock lot photos** instead of real vehicle photos. Every Maverick on the inventory grid shows the dealership building behind it. Trim levels are visually indistinguishable. | Buyer can't compare visually; trims blur together. |
| 3 | **"Get Estimate Payment" is a form, not math.** The site has no payment calculator. | Forces the buyer to call. Hides the highest-friction question. |
| 4 | **Standard features are a flat 50+ row list.** Alphabetical, uncategorized, identical formatting for "Air Conditioning" and "Forward Collision Warning". | Buyer can't find the feature relevant to *their* use case (towing, family, commuting). |
| 5 | **Pricing is itemized but math is hidden.** MSRP / Dealer Discount / Doc Fee / Freedom Price are visible, but the actual monthly payment requires another form. | Worst possible combination — implies transparency, withholds the answer. |
| 6 | **Trade-in banner appears 3× per page.** Same dark navy bar, same VIN field, on home + inventory + VDP. | Visual noise; trains the buyer to ignore it. |
| 7 | **Universal lead form recurs on home / finance / contact / inside every popup.** Same nine fields, slightly different framing. | Implies the dealer doesn't know what to ask; every conversion looks the same. |
| 8 | **"20 people viewed this vehicle" social proof** has no personalization. | Generic urgency theatre. |
| 9 | **Third-party "Text us" widget** is just SMS handoff, not a real Q&A. | The single highest-intent surface on the site is delegated to a relay. |
| 10 | **No memory.** Page does not remember what the visitor looked at, their stated budget, or their trade. Every visit starts at zero. | Repeat visitors get re-funneled instead of re-greeted. |
| 11 | **Disclaimer footer is significant real estate.** Multiple paragraphs of legal copy. | Crowds out useful content. |
| 12 | **Console errors / 7 warnings on every page load.** Slow page weight, outdated tracking pixels. | Search ranking + mobile experience cost. |

**Common root cause:** the site treats the dealership as *closed*.
The conversation a buyer would have on the lot — fit, budget, trade,
trim differences, financing — is exactly the conversation the site
refuses to host. Forms exist *instead of* the conversation.

---

## 3. What AI replaces

The Dealer OS thesis: every form on the public site is a degenerate
substitute for a conversation. Replace the form, host the
conversation, and the funnel collapses from a multi-page click-trail
into a single chat.

| Public-site element | AI replacement | Backend hook (already shipped) |
| --- | --- | --- |
| Filter sidebar (8 checkbox groups) | Conversational intake → 3 ranked candidates | `Vehicle.budget_fit`, `lever_flex_kind` |
| "Get Estimate Payment" form | Live payment math in the chat reply | `estimated_payment`, `payment_delta` |
| 50-row standard features list | AI summary keyed to stated need | LLM + structural enforcement (SESSION_011) |
| "Buy Now" popup form | Guided pre-qualification conversation | manager-chat structural validator pattern |
| Trade-in banner | Trade-in raised conversationally **only when relevant** | (state-layer enforcement pattern) |
| Universal contact form | Context-rich handoff transcript with the salesperson | onboarding profile + `lead_handoff_style` |
| Reviews carousel | (Removed — not load-bearing for a buyer) | — |
| Static "20 people viewed this" urgency | Personalized "based on your last visit, 3 new fits this week" | (future: session memory) |
| Third-party SMS chat widget | First-party assistant in dealership voice with banned phrases + escalation | full backend |
| 6-dropdown top nav | Sidebar (dealer side) + assistant routing (customer side) | — |

**What AI does NOT replace:** brand identity (logo, blue, "Make It
Happen"), compliance disclaimers (footer-only), service-department
scheduling (different team), service-department forms, parts catalog,
hours / directions, the actual lot.

The pitch in one line: **the website is a flyer. The OS is the
showroom.**

---

## 4. Recommended Dealer OS pages

The OS has two audiences, served by one shell:

- **Dealer-facing (primary):** sidebar app for the GM, sales manager,
  and floor staff. SESSION_012 shipped this shell.
- **Customer-facing:** the **Live Assistant** is *one page* of the OS,
  exposed via embeddable URL on the dealer's existing marketing site.
  Same backend, same tone enforcement, no separate stack.

### Sidebar (after SESSION_017)

```
Freedom Ford AI
───────────────
▸ Overview         daily home, attention items, today's leads
▸ Live Assistant   customer chat (manager preview + embed link)
▸ Inventory        coverage health, gaps, top-asked
▸ Leads            assistant-sourced pipeline + handoff trail
▸ Coaching Mode    train the AI (SESSION_011 — shipped)
▸ Team             salespeople + routing
▸ Setup            tone, banned phrases, hours, brands
```

### Page-by-page intent

| Page | What it shows | What it replaces |
| --- | --- | --- |
| **Overview** | Today's leads, attention items, AI status, recent activity. Real data, not placeholders. | The CRM dashboard the GM stares at. |
| **Live Assistant** | The customer chat surface. Manager preview + copyable embed URL. Vehicle cards render *inline* in the chat with `budget_fit` + `lever_flex_kind` badges. | The website's "Buy Now" popup form. |
| **Inventory** | Coverage health: synced count, low-photo vehicles, top-asked models this week, vehicles the assistant struggled to answer questions about. **Not** a search UI. | The dealer's spreadsheet for "what do we have?" |
| **Leads** | Assistant-sourced conversations → qualification status → handoff trail → outcome. | The CRM lead inbox (for assistant traffic). |
| **Coaching Mode** | "Train Your AI Sales Assistant" — already shipped, structural enforcement live. | The training meeting. |
| **Team** | Salesperson roster + routing rules (who gets which lead type). | The whiteboard. |
| **Setup** | Tone, banned phrases, payment disclaimer, hours, brands, escalation rule. | The "tell me about your store" interview. |

### Inventory representation rule

- **Customer side:** vehicles render *inside the chat*, never in a
  grid. Three cards max per turn. `budget_fit` + `lever_flex_kind`
  badges are the headline, not afterthoughts.
- **Dealer side:** the Inventory page is a *coverage* surface, not a
  shopping surface. Manager fixes gaps there.
- **Never:** reproduce the public site's filter-grid pattern. That is
  exactly the UX the OS exists to retire.

### Concrete deltas to SESSION_012 informed by this audit

1. **Add Inventory + Leads to the sidebar** between Live Assistant and
   Coaching Mode. Stub them as empty pages with "Coming next session"
   so the architecture reads correctly even before they're built.
2. **Overview page** — replace placeholder cards with real signal:
   - Recent activity → real `/api/dealer-ai/admin/audit-events/`
     rows.
   - Coaching summary → real coaching-scenario counts.
   - Attention items → derived from `OnboardingProfile`
     (`banned_phrases` empty, `salespeople_added=false`, etc.).
   - Add a fourth card: **Today's leads** preview + link.
3. **Live Assistant page** — render `ChatMessage.matched_vehicles`
   inline with the assistant reply. One primary action per card
   ("Open conversation"), not the public site's 4-CTA stack.
4. **Topbar** — add a **Public preview** pill that opens a modal with
   the embeddable chat URL. Reframes Live Assistant from "demo" to
   "production embed."
5. **No contact form anywhere in the OS.** The OS exists because the
   form is the thing being replaced.
6. **No marketing essay copy.** The Finance Center page on
   samsfreedomford.com burns half its real estate on a "Buying Vs
   Leasing a Ford" essay no buyer reads. The OS does not produce
   that kind of content.

---

## 5. Roadmap — SESSION_013 to SESSION_017

Sequencing assumes one focused session per slot. Order is dictated by
*highest demonstrable value first* — the Live Assistant page is the
single most important deliverable because it is the surface the
dealership can immediately measure against the public site's lead
form.

### SESSION_013 — Live Assistant page + inline vehicle cards

**Why first:** the single highest-leverage page in the OS. Once it
exists, every conversation about the OS becomes a demo instead of an
explanation.

**Scope:**

- `frontend/src/pages/LiveAssistantPage.tsx` mounted at
  `/dealer-ai-demo` (rename optional).
- Hook to existing `start_chat` / `send_message` API.
- Render `ChatMessage.matched_vehicles` as inline shadcn `Card`s
  beneath each assistant turn.
- Surface `budget_fit` and `lever_flex_kind` as `Badge`s on the card.
- One primary action per card: **"Open conversation"** (opens the
  vehicle in a side `Sheet`).
- No 4-CTA stack. No filter sidebar. No reproduction of the public
  site's grid.

**Out of scope:** customer-facing embed (that's SESSION_017). Memory
across sessions. Trade-in flow.

### SESSION_014 — Wire Overview to real data

**Why second:** the OS landing page should not lie to the dealer.
Today's Overview shows static placeholders.

**Scope:**

- Recent activity → `/api/dealer-ai/admin/audit-events/?since=24h`.
- Coaching summary → real coaching-scenario count (may need a small
  backend rollup endpoint or derive from `manager_chat` audit events).
- Attention items → derived rules over `OnboardingProfile` flags.
- Add **Today's leads** card with a 3-row preview + link.

**Out of scope:** building the Leads page itself (SESSION_015).

### SESSION_015 — Leads pipeline page

**Why third:** Overview will dead-end at "Today's leads → see all"
once SESSION_014 lands. SESSION_015 builds the destination.

**Scope:**

- `frontend/src/pages/LeadsPage.tsx` mounted at `/dealer-ai-leads`.
- List view sourced from `/api/dealer-ai/admin/leads/`.
- Per-lead: conversation transcript, qualification fields,
  `handed_off` status, salesperson assigned, urgency.
- Backend: small additions if needed for handoff trail metadata
  (likely already there per the runtime traffic seen at session
  start).

**Out of scope:** rich filtering, bulk actions, write APIs. Read-only
in v0.

### SESSION_016 — Inventory coverage page

**Why fourth:** once Leads exist, "what's the assistant *not*
answering well?" becomes the next operator question. Inventory
coverage is the answer surface.

**Scope:**

- `frontend/src/pages/InventoryCoveragePage.tsx`.
- Stats: total synced, last sync timestamp, vehicles with stub
  descriptions (under N chars), top 5 vehicles asked about this week,
  vehicles where the assistant fell back / refused.
- Backend: add a small `/api/dealer-ai/admin/inventory-coverage/`
  rollup endpoint.
- **Not** a shopping UI. **Not** a filter grid. Coverage health only.

**Out of scope:** vehicle CRUD, photo uploads, description editing
(those are CMS features, not OS features).

### SESSION_017 — Public embed + iframe-friendly Live Assistant route

**Why last:** SESSIONS 013–016 build the dealer side. SESSION_017
is the moment the customer-facing surface goes live. By the time we
get here, the assistant has a polished page (013), the dealer can see
its impact in Overview (014) and Leads (015), and inventory coverage
(016) tells the dealer where to invest.

**Scope:**

- New route `/embed/assistant` rendering Live Assistant with no
  sidebar / topbar chrome — pure chat surface, dealer-themed.
- CSP / iframe-safe headers on the backend.
- Topbar **Public preview** pill in the OS that copies the embed URL.
- Optional: `?theme=` or `?intent=` query params for embedding
  variants (e.g. trade-in-first vs inventory-first).
- Documented snippet for the dealer to drop into their existing
  Elementor / WordPress / vendor CMS.

**Out of scope:** white-label hosting, multi-store routing, tenant
auth (one-store assumption from SESSION_008 still holds).

### After SESSION_017 — what becomes possible

Once SESSION_017 ships, the dealer can run a controlled experiment:

- A/B the existing samsfreedomford "Buy Now" lead form against the
  embedded assistant on the same VDP.
- Measure: form submissions vs. assistant-qualified leads,
  median-time-to-handoff, eventual sale rate.

That comparison is the proof point the entire project rolls up to. It
is the reason this audit exists.

---

## Appendix — captured screenshots (local, not committed)

Stored under this directory; ignored via `.gitignore`. Reference
the audit text alongside them when reviewing.

- `samsfreedom_01_home.png` — homepage above + below fold
- `samsfreedom_02_inventory.png` — new inventory grid + filter sidebar
- `samsfreedom_03_vdp.png` — 2025 Maverick XL vehicle detail page
- `samsfreedom_04_finance.png` — Finance Center
- `samsfreedom_05_contact.png` — Contact form

If any of these become load-bearing for a handoff or external deck,
copy the curated subset under `docs/handoffs/screenshots/SESSION_NNN/`
and commit explicitly.
