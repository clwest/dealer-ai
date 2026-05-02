---
title: Freedom Ford Dealer AI — onboarding plan (v0)
status: foundation — not yet wired to backend persistence
generated: 2026-05-01
audience: dealership managers, salespeople, pilot lead
---

# Freedom Ford Dealer AI — onboarding plan (v0)

This document covers the **first lightweight onboarding layer** for
the Freedom Ford Dealer AI pilot. It is written for two audiences:

- **Pilot lead / GM / sales manager** — what gets configured and why.
- **Engineering** — what is in scope for v0 vs. deferred.

The matching frontend page lives at `/dealer-ai-onboarding`. All
fields are currently **local-state only**; nothing persists to the
backend yet (see *Out of scope* below).

---

## Onboarding goals

The onboarding system exists so a dealership can take the demo to a
**pilot configuration** in one sitting. By the end of onboarding the
store should have:

1. **A store profile** — name, location, brands, contact channels.
2. **Manager preferences** — sales tone, pricing comfort, lead-handoff
   style. These shape the system prompt the AI uses store-wide.
3. **At least one salesperson profile** — name, role, contact, voice
   preferences, personal intro. This becomes the basis of a
   per-salesperson agent later.
4. **AI assistant behavior baseline** — greeting, approved phrases,
   banned phrases, escalation rules, payment/inventory disclaimer.
5. **A go/no-go pilot checklist** that the manager can walk through
   before flipping the system live to real customers.

The goal is *not* to capture every preference perfectly — it is to
prove the dealership can self-serve the basic configuration that
shapes the AI's voice and handoff rules.

---

## Manager onboarding flow

A sales manager / GM / owner is the primary onboarder. The flow is
linear (each section unlocks the next conceptually, though the v0
UI keeps everything visible on one scrollable page so they can
review and revise).

### Step 1 — Welcome / setup status
- One-line status of the dealership setup ("0 of 6 sections
  completed", "Live").
- Link to the customer demo (`/dealer-ai-demo`) so the manager can
  see the assistant they're configuring.

### Step 2 — Dealership profile
- Name, primary store location, main brands carried (Ford + used
  inventory mix), main sales phone, website.
- Used by the assistant for greetings, handoff lines, and fallback
  references ("Visit our showroom at…").

### Step 3 — Manager preferences
- Sales tone (warm / consultative / fast-paced / formal).
- Pricing comfort (firm / negotiable / disclose ranges).
- Appointment preference (book online / call back / walk-in).
- Lead handoff style (hand to next available / round-robin /
  preferred salesperson).

### Step 4 — Salesperson profile setup
- A simple inline form to add **one** salesperson during onboarding.
  Multi-salesperson management lives on the existing Sales Team
  page (`/dealer-ai-admin/team`).
- Fields: name, role, phone, email, specialties, preferred tone,
  personal intro.

### Step 5 — AI assistant behavior
- Dealership greeting line.
- Approved phrases (e.g., *"with approved credit"*, *"Want me to
  set up a closer look?"*).
- Banned phrases (e.g., *"guaranteed approval"*, *"best price
  ever"*).
- Escalation / handoff rule (when does the AI hand off to a
  human?).
- Inventory / payment disclaimer line shown alongside payment
  estimates.

### Step 6 — Pilot checklist
A go/no-go list:
- [ ] Inventory connected (DMS or seed file)
- [ ] Finance rules reviewed (rate, term, down payment defaults)
- [ ] Salespeople added
- [ ] Demo prompts tested (the 5-prompt flow in the demo script)
- [ ] Pilot approved

When all items are checked, the manager can flip the dealership to
*Pilot active*. v0 simply visualizes this — the live state flag is
a future backend concern.

---

## Salesperson onboarding flow

Salespeople do **not** complete the full manager flow. Their
onboarding is a subset:

1. The manager (or admin) creates the salesperson record from
   `/dealer-ai-onboarding` Step 4 or `/dealer-ai-admin/team`.
2. The salesperson logs into their workspace
   (`/dealer-ai-advisor/<slug>`, already exists).
3. The salesperson reviews and personalizes:
   - Their personal intro line (used when the AI hands off a lead
     in their name).
   - Their preferred tone (warm / direct / consultative).
   - Their specialties (e.g., *trucks*, *first-time buyers*,
     *finance pre-quals*).
4. Save → the salesperson's profile is now wired into the
   handoff routing.

Salesperson onboarding is intentionally lightweight — most of the
voice configuration lives at the **store level** in the manager
flow. Salesperson-level voice overrides are a future extension
(see `ASSISTANT_AGENT_CREATION_ROADMAP.md` → `VoiceProfile`).

---

## Data we need to collect (v0)

The frontend page captures the following as plain local state.
Persistence is deferred to a follow-up backend task.

| Section | Fields |
|---|---|
| Dealership profile | dealership name, store location, main brands, sales phone, website |
| Manager preferences | sales tone, pricing comfort, appointment preference, lead handoff style |
| Salesperson profile | name, role, phone, email, specialties, preferred tone, personal intro |
| Assistant behavior | dealership greeting, approved phrases, banned phrases, escalation rule, inventory/payment disclaimer |
| Pilot checklist | 5 boolean flags (see Step 6 above) |

Free-text fields are bounded to a sensible size on the frontend.
None of these are required to ship; the system runs with sensible
defaults if a field is blank.

---

## Assistant / agent creation — roadmap

See [`ASSISTANT_AGENT_CREATION_ROADMAP.md`](./ASSISTANT_AGENT_CREATION_ROADMAP.md)
for the full sketch.

Short version:

- **DealerAssistant** — one per dealership. Carries the store-level
  voice profile, greeting, banned/approved phrases, escalation rule.
- **SalespersonAgent** — one per salesperson. Inherits from
  DealerAssistant; overrides tone + intro line + specialties.
- **ManagerAgent** — one per manager (post-pilot). Provides the
  manager dashboard with insight summaries, lead triage suggestions.
- **StorePolicyProfile** — pricing comfort, finance rules,
  disclaimers. Loaded into every assistant prompt.
- **LeadHandoffRule** — when (intent, urgency, dollar amount) and
  to whom (next-available / round-robin / by-specialty).
- **VoiceProfile** — discrete voice presets (warm / consultative
  / fast-paced / formal) that ship with sample phrasing the AI is
  trained to imitate.

These are **planned entities, not yet implemented.** The current
backend has `Salesperson` (already exists) and the chat engine's
deterministic budget/payment math. Everything else above is a
future feature.

---

## Demo-to-pilot checklist

Use this as the runbook when moving a dealership from "saw the
demo" to "running the pilot with their data".

1. **Demo recap** — walk through the 5-prompt flow from
   `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md`. Confirm the dealership
   wants to proceed.
2. **Onboarding session (60–90 min)** — manager fills out
   `/dealer-ai-onboarding`. Capture the screen / save the JSON
   blob from local storage so we can replay or migrate later.
3. **Inventory swap** — replace the seed inventory with the
   dealership's actual stock (Phase 5+ work; the seed is a CSV
   under `backend/dealer_ai/management/commands/seed_*.py`).
4. **Salesperson roster** — manager adds the rest of the team via
   `/dealer-ai-admin/team`.
5. **Voice review** — manager reviews 3–5 sample replies (cash,
   finance, deep-dive). Confirms the assistant sounds like *their*
   dealership, not generic.
6. **Test prompts** — run the 5-prompt flow against the live
   inventory. Verify cards surface correctly and prose is on-brand.
7. **Pilot flip** — set the dealership to *Pilot active*. Customer
   chat now serves real visitors.
8. **Day-7 review** — manager reviews leads, voice samples, any
   handoff misroutes. Iterate on banned phrases / approved phrases.

---

## Out of scope (v0)

The following are explicitly **NOT** part of this onboarding
foundation. Adding any of them is a separate, scoped task.

- **Full auth / RBAC system.** No login, no permissions matrix.
  The current backend has session-based admin access for the
  manager dashboard; no further auth work happens here.
- **Backend persistence for onboarding fields.** The page captures
  values to component state. No `OnboardingProfile` model, no
  migration, no API endpoints. A follow-up task can wire this up
  once the field shape is validated by a real dealership session.
- **Multi-tenant isolation.** This codebase serves one dealership
  (Freedom Ford). Multi-tenant boundaries are a future architectural
  concern.
- **Live AI behavior changes from onboarding inputs.** The fields
  for assistant greeting / banned phrases / approved phrases are
  captured in v0 but **do not** flow into the chat engine system
  prompt yet. Wiring them through `_build_system_message` is a
  Phase-2 task.
- **Salesperson self-service onboarding screen.** v0 has manager-
  facing onboarding only. Salesperson personalization is captured
  via the existing advisor workspace; a dedicated salesperson
  onboarding flow is deferred.
- **Inventory / DMS integration wizard.** Inventory swap remains
  a manual seed-file replacement. A guided DMS integration step
  is a separate workstream.
- **Compliance review checklist** (W.A.C. wording, FTC
  advertising rules, state-specific disclosures). v0 asks the
  manager to review compliance externally; the system enforces
  payment-quote and W.A.C. rules at the post-LLM scrub layer
  but does not validate the manager's banned-phrase list against
  legal requirements.

---

## Where this lives in the codebase

- **Frontend page:** `frontend/src/pages/DealerOnboardingPage.tsx`
- **Route:** `/dealer-ai-onboarding` in `frontend/src/main.tsx`
- **Nav entry:** `NAV_LINKS` array in `frontend/src/App.tsx`
- **This plan:** `docs/onboarding/FREEDOM_FORD_ONBOARDING_PLAN.md`
- **Future entities sketch:** `docs/onboarding/ASSISTANT_AGENT_CREATION_ROADMAP.md`

When the backend persistence layer lands, fields will move into a
new `dealer_ai/models/onboarding.py` module and the page will swap
local state for `react-query` mutations against new DRF endpoints.
That work is **not** in this commit.
