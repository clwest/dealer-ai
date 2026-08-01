---
title: Dealer OS Dealer AI — assistant / agent creation roadmap
status: planning sketch — not yet implemented
generated: 2026-05-01
---

# Assistant / agent creation roadmap

This document defines the **future entities** the onboarding layer
will eventually create and manage. Nothing in this file exists in
the codebase yet — it is a planning sketch so the field shapes
captured by the v0 onboarding page have a target schema to grow
into.

The backend currently exposes only `Salesperson` (Phase 4). Every
entity below is **planned, not built.** When we implement, each
entity should land as its own migration with a focused test pass;
do not rush a giant ORM refactor.

---

## Why these entities

The chat engine today builds its system prompt from:

- A static voice contract (`docs/DEALER_KIT_BEHAVIOR_LAYER.md`).
- Deterministic backend math (payment / budget classification).
- Per-vehicle metadata (drivetrain, body style, etc.).

To let a dealership self-configure their AI, we need data
structures that carry **store-level**, **manager-level**,
**salesperson-level**, and **per-customer-handoff** preferences
into that system prompt without leaking implementation details
into every call site.

The entities below split that responsibility along clean
boundaries.

---

## DealerAssistant

The **store-level AI persona.** One per dealership.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `dealership` | FK → `Dealership` | Owner. One DealerAssistant per dealership in v1; multiple variants (e.g., service vs. sales) deferred. |
| `display_name` | str | "Dealer OS Sales Assistant" |
| `greeting` | text | First message shown on the empty chat. Captured in onboarding Step 5. |
| `voice_profile` | FK → `VoiceProfile` | Selected preset (warm / consultative / etc). |
| `store_policy` | FK → `StorePolicyProfile` | Pricing comfort, finance rules, disclaimers. |
| `approved_phrases` | JSON list | Phrases the AI is encouraged to use. |
| `banned_phrases` | JSON list | Phrases the AI must never use. Enforced at post-LLM scrub. |
| `escalation_rule` | FK → `LeadHandoffRule` | When and how to hand off to a human. |
| `created_at` / `updated_at` | timestamp | |

**Relationships:**
- 1 ↔ 1 with `Dealership` (in v1).
- 1 → many `SalespersonAgent` (each salesperson agent inherits
  this assistant's profile).

**Lifecycle:** created during onboarding Step 5. Edited from the
manager dashboard.

---

## SalespersonAgent

The **per-salesperson AI persona.** Inherits from
`DealerAssistant`; overrides voice + intro + specialties.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `salesperson` | FK → `Salesperson` (existing) | Owner. |
| `parent_assistant` | FK → `DealerAssistant` | Inherits store-level config. |
| `personal_intro` | text | Used when the AI hands off a lead in this salesperson's name. |
| `voice_override` | FK → `VoiceProfile` (nullable) | If set, overrides the store voice for this salesperson's chats. |
| `specialties` | JSON list | "trucks", "first-time buyers", "finance pre-quals". Already exists on Salesperson; mirrored here for prompt assembly speed. |
| `is_active` | bool | Enables / disables this agent for routing. |
| `created_at` / `updated_at` | timestamp | |

**Relationships:**
- 1 ↔ 1 with `Salesperson`.
- many → 1 to `DealerAssistant`.

**Lifecycle:** created when the manager adds a salesperson via
onboarding Step 4 or `/dealer-ai-admin/team`. Salesperson can
edit their own `personal_intro` and `voice_override` from their
advisor workspace.

---

## ManagerAgent

A **manager-facing AI persona** for the dashboard. Different from
the customer-facing assistant — this one summarizes leads,
suggests follow-ups, and drafts manager replies.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `manager` | FK → `User` (post-auth) | Owner. v0: one ManagerAgent per dealership; per-manager variants land with auth. |
| `dealership` | FK → `Dealership` | Scope. |
| `summary_style` | enum | "bullet" / "narrative" / "deal-focused". |
| `daily_brief_enabled` | bool | Whether the agent emits a morning brief to the manager. |
| `escalation_thresholds` | JSON | Ticket size / urgency triggers for escalation surfaces. |
| `created_at` / `updated_at` | timestamp | |

**Lifecycle:** auto-created when a manager runs the onboarding
flow. v0: not exposed in onboarding UI; future manager-dashboard
settings panel.

---

## StorePolicyProfile

The **policy-and-numbers profile** used to build deterministic
constraints into every chat turn. Pricing comfort, finance rules,
disclaimers.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `dealership` | FK → `Dealership` | One per dealership. |
| `pricing_comfort` | enum | "firm" / "negotiable" / "disclose-ranges". |
| `default_apr` | decimal | Fallback when finance preflight is unavailable. |
| `default_term_months` | int | Default loan term used in budget math. |
| `default_down_payment_pct` | decimal | Default down payment if customer doesn't supply one. |
| `payment_disclaimer` | text | "(W.A.C.)" / "On approved credit" / etc. |
| `inventory_disclaimer` | text | Shown alongside cards. |
| `finance_disclosure` | text | Long-form regulatory disclosure (FTC / state). |
| `created_at` / `updated_at` | timestamp | |

**Loaded into:** every `_build_system_message` call. Drives the
post-LLM payment / W.A.C. scrubs.

---

## LeadHandoffRule

When and how the AI hands a customer off to a human salesperson.
Multiple rules per dealership; the engine picks the **first
matching** rule by priority.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `dealership` | FK → `Dealership` | Scope. |
| `priority` | int | Lower = checked first. |
| `name` | str | Human-readable ("VIP shoppers", "Truck buyers > $40k"). |
| `match_intent` | JSON list (nullable) | E.g., `["truck_4wd", "luxury_suv"]`. |
| `match_min_price` | decimal (nullable) | Only fires for vehicles ≥ this price. |
| `match_urgency` | enum (nullable) | "today" / "this_week" / "browsing". |
| `match_specialty_tag` | str (nullable) | Routes to a salesperson with this specialty. |
| `assignment_strategy` | enum | "next-available" / "round-robin" / "named-salesperson" / "specialty-match". |
| `assigned_salesperson` | FK → `Salesperson` (nullable) | When `assignment_strategy = "named-salesperson"`. |
| `is_active` | bool | |
| `created_at` / `updated_at` | timestamp | |

**Lifecycle:** seeded with one default rule (next-available) when
a `DealerAssistant` is created. Manager edits via a future rules
panel; not in v0 onboarding UI.

---

## VoiceProfile

A **named voice preset** the AI is configured to imitate. Stored
as data so dealerships can pick one from a list rather than
authoring prompt prose.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `slug` | str (unique) | "warm" / "consultative" / "fast-paced" / "formal" / "custom-<dealer-slug>". |
| `display_name` | str | "Warm and consultative" |
| `description` | text | One-sentence summary shown in onboarding picker. |
| `tone_directives` | JSON list | Bullet directives loaded into the system prompt. |
| `good_examples` | JSON list | Sample phrases the AI imitates. |
| `bad_examples` | JSON list | Sample phrases the AI avoids. |
| `is_builtin` | bool | True for shipped presets; false for dealership-custom. |
| `dealership` | FK → `Dealership` (nullable) | Set only on custom profiles. |
| `created_at` / `updated_at` | timestamp | |

**Why this is its own table:** dealerships will eventually want
custom voice profiles per channel (sales vs. service) and per
seasonal tone (peak season vs. off-season). Storing voice as data
makes A/B testing trivial.

---

## Implementation order (when we build)

1. **`Dealership` table.** Currently the codebase assumes a
   single dealership; adding the model unlocks every entity above.
2. **`StorePolicyProfile`** — wired into `_build_system_message`
   and the post-LLM scrub layer. Lowest risk; pure data swap.
3. **`VoiceProfile`** + 3–4 builtin presets. The chat engine
   already has voice contract directives; this just makes them
   data-driven.
4. **`DealerAssistant`** — composes 2 + 3.
5. **`SalespersonAgent`** — overrides on top of 4. Light because
   `Salesperson` already exists.
6. **`LeadHandoffRule`** — last because it's the most complex
   and the v0 default ("next-available") works without it.
7. **`ManagerAgent`** — post-auth. Defer until we have real
   manager identities.

---

## Out of scope here

This file does not propose:

- API endpoints (separate DRF design pass).
- Migration plans (handled when each entity is implemented).
- Auth / multi-tenant boundaries (separate architectural pass).
- UI for editing each entity (each gets its own focused screen).

The point of this document is to **lock the entity shapes** so
the v0 onboarding page captures fields with a known target
schema. Field rename or restructure later is fine; the names
above are *intent signals*, not contracts.
