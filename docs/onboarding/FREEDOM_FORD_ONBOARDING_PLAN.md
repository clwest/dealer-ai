---
title: Dealer OS Dealer AI — onboarding plan (v0)
status: foundation — persistence (SESSION_008) + live AI wiring (SESSION_009) shipped
generated: 2026-05-01
updated: 2026-05-02
audience: dealership managers, salespeople, pilot lead
---

# Dealer OS Dealer AI — onboarding plan (v0)

This document covers the **first lightweight onboarding layer** for
the Dealer OS Dealer AI pilot. It is written for two audiences:

- **Pilot lead / GM / sales manager** — what gets configured and why.
- **Engineering** — what is in scope for v0 vs. deferred.

The matching frontend page lives at `/dealer-ai-onboarding`. As of
**SESSION_008** the page reads/writes against a backend singleton
profile (see *Persistence (SESSION_008)* below). The richer entity
split — DealerAssistant / SalespersonAgent / ManagerAgent / etc. —
remains a planning sketch in `docs/roadmap/ASSISTANT_AGENT_CREATION_ROADMAP.md`.

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
(see `docs/roadmap/ASSISTANT_AGENT_CREATION_ROADMAP.md` → `VoiceProfile`).

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

See [`ASSISTANT_AGENT_CREATION_ROADMAP.md`](../roadmap/ASSISTANT_AGENT_CREATION_ROADMAP.md)
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

## Persistence (SESSION_008)

**Status:** implemented.

The onboarding page now reads from and writes to a singleton
`DealerOnboardingProfile` row via:

- **`GET /api/dealer-ai/onboarding/profile/`** — returns the saved
  profile, or the default shape (matching the v0 frontend seed
  values) if none exists yet. The default `payment_disclaimer`
  ships with the standard W.A.C. wording.
- **`PUT /api/dealer-ai/onboarding/profile/`** — full save. Upserts
  the singleton row.
- **`PATCH /api/dealer-ai/onboarding/profile/`** — partial update.
  Useful for toggling individual checklist booleans without
  re-sending the rest of the profile.

The model is one Django row holding all 27 fields flat, with field
names mirroring the future entity split sketched in
`docs/roadmap/ASSISTANT_AGENT_CREATION_ROADMAP.md`. When the `Dealership` /
`DealerAssistant` / `StorePolicyProfile` migration lands, columns
move to the new tables without renames.

### Current limitation

- **One-store profile only.** The view layer enforces the singleton
  by reading `.first()` and upserting on save. Multi-store / multi-
  tenant support arrives with the `Dealership` entity in the
  roadmap, not before.

### Still deferred (despite persistence)

- **No DealerAssistant / SalespersonAgent / ManagerAgent /
  StorePolicyProfile / VoiceProfile entities yet.** Those land
  with the roadmap migration sequence.

---

## Live AI wiring (SESSION_009)

**Status:** implemented.

The persisted onboarding fields now shape live chat behavior. One DB
load per chat turn, no schema changes, no new agent architecture.
Behavior with no profile saved is identical to the pre-SESSION_009
chat engine.

| Onboarding field | What it now does in chat |
|---|---|
| `dealership_greeting` | Injected as a tone-hint in the per-turn store-voice system block. Explicitly told NOT to be repeated verbatim every reply. |
| `sales_tone` | Translated into a one-paragraph voice directive (consultative / direct / fast-paced / formal / friendly / casual). Unknown labels pass through verbatim so the LLM still sees manager intent. |
| `approved_phrases` | Listed in the system block as encouraged phrasing (with explicit "do NOT phrase-stuff" guidance). Capped at 10 phrases. |
| `banned_phrases` | New post-LLM scrub stage. Sentence-strips any sentence containing a banned phrase (case-insensitive substring match). Audit metadata records hits under `banned_phrase_hits`. |
| `payment_disclaimer` | Appended at the end of the reply when (a) the reply mentions payment/financing language, (b) the conversation is **not** in cash-mode (the existing financing-language scrub already strips finance prose there), (c) the disclaimer text (or a W.A.C. fingerprint of it) isn't already in the reply. |
| `escalation_rule` | Added to the store-voice system block as soft-handoff guidance. No auto-lead creation; the existing handoff workflow is unchanged. |

The chat engine loads the singleton profile via
`load_overrides()` (`backend/dealer_ai/services/onboarding_overrides.py`)
near the top of the LLM-bound branch in `handle_user_message`. All helper
functions (`format_store_voice_block`, `scrub_banned_phrases`,
`should_append_disclaimer`, `append_disclaimer`) are pure-input/pure-output
so they unit-test without a chat session.

### Audit metadata

When a banned-phrase scrub fires, `ChatMessage.metadata` gains:

- `scrubs` includes `"banned_phrase"`
- `banned_phrase_hits` lists the matched phrases (deduplicated)
- `flag` becomes `"banned_phrase_scrubbed"` (or `"multiple_scrubs_fired"` when other scrubs also fired)

When the disclaimer is appended, `ChatMessage.metadata.disclaimer_appended = true`.

### Still deferred (after SESSION_009)

- **Salesperson seed not linked to `Salesperson` model.** Saving the
  onboarding profile does not create a `Salesperson` row.
- **No multi-store, no auth, no RBAC.** Same as SESSION_008.
- **No automatic lead creation from `escalation_rule`.** The rule is
  guidance for the LLM's voice; the existing handoff/lead workflow is
  unchanged.
- **No DealerAssistant / SalespersonAgent / ManagerAgent /
  StorePolicyProfile / VoiceProfile entities yet.** Those still land
  with the roadmap migration sequence.

---

## Manager chat tester (SESSION_010)

**Status:** implemented.

Managers now have a sandbox to test how their configured assistant
responds to a customer prompt without affecting real customer
sessions or metrics.

- **Page:** `/dealer-ai-manager-chat` (nav label: *Test assistant*).
- **Endpoint:** `POST /api/dealer-ai/manager-chat/` — body
  `{"message": "..."}`, response `{"reply": "..."}`. No vehicle
  cards in the response (voice/tone test focus).
- **Statelessness:** each request creates an ephemeral `ChatSession`
  tagged `metadata={"channel": "manager_test"}` so customer-facing
  audits / dashboards can filter the test traffic out. The
  frontend keeps a local transcript only — reload resets it.
- **Reuses the chat engine wholesale:** the SESSION_009 onboarding
  overrides (greeting hint, tone directive, approved/banned phrases,
  payment disclaimer, escalation rule) all flow through unchanged,
  so the manager sees exactly what a customer would.

Not customer-facing — the page header explicitly says so, and the
nav label is *Test assistant*, not *Chat*. Customer chat remains at
`/dealer-ai-demo`.

---

## Out of scope (v0)

The following are explicitly **NOT** part of this onboarding
foundation. Adding any of them is a separate, scoped task.

- **Full auth / RBAC system.** No login, no permissions matrix.
  The current backend has session-based admin access for the
  manager dashboard; no further auth work happens here.
- **Multi-tenant isolation.** This codebase serves one dealership
  (Dealer OS). Multi-tenant boundaries are a future architectural
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
- **Future entities sketch:** `docs/roadmap/ASSISTANT_AGENT_CREATION_ROADMAP.md`

**SESSION_008 update:** persistence shipped as a single Django row
(`DealerOnboardingProfile` in `backend/dealer_ai/models.py`). The
frontend swaps local state for plain `fetch` against
`GET|PUT|PATCH /api/dealer-ai/onboarding/profile/` (no react-query
dependency added — keeps the bundle small and matches the rest of
`src/lib/api.ts`).
