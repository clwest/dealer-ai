---
title: "Dealer AI Kit — Translation Layer"
status: project-owned
generated: 2026-05-02
last_reframed: 2026-07-31
companion_docs:
  - "DEALER_KIT_SESSION_START.md"
  - "PROJECT_WHAT_IT_IS.md"
  - "CONTEXT_KIT_INVENTORY.md"
  - "PROJECT_PIPELINE.md"
  - "DEALER_KIT_BEHAVIOR_LAYER.md"
  - "onboarding/FREEDOM_FORD_ONBOARDING_PLAN.md"
---

# Dealer AI Kit — Translation Layer

> **Project-owned, hand-written.** Not auto-generated. `context-kit
> adopt`, `seed`, or `inventory --write` must not overwrite it. Edit
> freely; if you delete it, `orient` silently omits this section.
>
> **Reference implementation note (2026-07-31 pivot):** the shipped
> default dealer is Copper Canyon Auto (Yuma, AZ — indie). The three
> Example Translations below are drawn from SESSION_008–010, which
> pre-date the pivot and were captured against the Freedom Ford
> franchise reference implementation. **The truth-preservation
> contract and Live Chat Mode rules are identical for the Copper
> Canyon default** — those examples remain accurate as *historical
> worked cases*. The personas, translation modes, and refusal rules
> in this doc are dealer-agnostic and apply to any configured dealer.

---

## Purpose

> **Core rule:** *Same truth → different explanation layer → zero
> distortion.*

The Dealer AI Kit has multiple stakeholders who read the same project
state through different lenses: the builder (Chris), the operator /
tester (Jessica), the dealer owner (any configured dealership), the
sales manager, and eventually individual salespeople. They each need
a different framing of the same facts. This document is the contract
that says:

- The assistant **may** simplify, reframe, reorder, change examples,
  and adjust vocabulary for the audience.
- The assistant **must not** invent features, test results, business
  outcomes, customer value, decisions, or shipping status that the
  source-of-truth doesn't support.
- If a translation cannot be made without inventing or implying
  unsupported facts, the assistant must fall back to a neutral
  summary or qualify the claim explicitly. Never silently upgrade
  uncertainty into certainty.

If a fact is not in the source-of-truth inputs below, the assistant
**must not assert it** to any audience.

---

## Source of Truth Inputs

In `orient` read order. The translation layer reads from these
anchors; it never adds new facts.

1. `docs/DEALER_KIT_SESSION_START.md` — hand-written entry point.
   Current baseline (test counts, demo-readiness, what's persisted).
2. `docs/PROJECT_WHAT_IT_IS.md` — narrative anchor: one-paragraph
   description of the system.
3. `docs/CONTEXT_KIT_INVENTORY.md` — runtime anchor (low-signal for
   this repo shape; trust `context/INVENTORY.md` instead).
4. `docs/PROJECT_PIPELINE.md` — runtime flow map: how a chat request
   moves through pre-LLM guards → LLM → post-LLM scrub stack.
5. `docs/DEALER_KIT_BEHAVIOR_LAYER.md` — voice / display / constraint
   contract for the customer-facing assistant.
6. `docs/research/INDEPENDENT_DEALER_PIVOT.md` — the 2026-07-31 pivot plan +
   phase-by-phase status snapshot (persona, deltas, guardrails).
7. `docs/onboarding/FREEDOM_FORD_ONBOARDING_PLAN.md` — onboarding
   architecture; SESSION_008 persistence, SESSION_009 wiring,
   SESSION_010 manager chat.
8. Latest `docs/handoffs/SESSION_NNN_*.md` — what last session shipped
   (definitive on shipped status / test count / known gaps).
9. `00-START-NEXT-SESSION.md` — current session priority; the
   hand-written section below the adopt-managed block is canonical.

If any document above says "X is shipped" or "Y is broken", the
translation layer can rephrase X or Y for any audience. If none of
them say it, the translation layer **invents nothing** to fill the
gap.

---

## Personas / Audiences

The four required audiences plus one optional. Each row names what
that person actually cares about for this product, and what they do
not need surfaced.

| Persona | Cares about | Ignores / can skip |
|---|---|---|
| **Chris** (builder, product owner) | Implementation truth, scope boundaries, next engineering move, risks, drift, what's deferred | High-level marketing framing |
| **Jessica** (MBA operator, tester) | What to test, what *good* feels like, how to report feedback, business clarity, edge cases | Internal scrub-stack ordering, regex specifics |
| **Dealer owner** | ROI, risk, adoption path, what is demo-ready vs not, pilot framing, compliance posture | Code internals, model names, library choices |
| **Sales manager** | How the team uses it, workflow impact, voice/tone testing, how onboarding settings change responses, lead handling | Architecture, why tests are structured a certain way |
| **Salesperson** (optional) | How this helps with leads, what it does and doesn't replace, how to trust the output | Ownership / decision-making concerns |

Add or refine personas as the pilot rollout teaches us who actually
reads the explanation in each mode. Don't add a persona unless
someone in that role actually consumes the translation.

---

## Translation Modes

The same source-of-truth fact takes different shapes per audience.
Modes are guidelines, not rigid templates.

| Mode | Audience | Output shape |
|---|---|---|
| Builder summary | Chris | Bullet list of changes, file paths, follow-ups, deferred items, risks |
| Operator / tester walkthrough | Jessica | Numbered scenarios with expected behavior + the line that makes it "wrong" |
| Owner brief | Dealer owner | 3–5 bullets max: what works today, what's a real customer touch, what risk remains, what's the next decision |
| Manager workflow note | Sales manager | One paragraph: what the team does differently because of this change |
| Salesperson trust note | Salesperson | One paragraph: what to lean on the AI for, where to step in yourself |

Two implicit rules:
- The **owner brief** is always tighter than the **builder summary**.
  More than ~5 bullets means the brief is too long for the audience.
- The **manager workflow note** mentions concrete UI surfaces (e.g.
  *Onboarding page*, *Test Assistant Coaching Mode*). The owner
  brief stays at the conversation level and avoids UI specifics.

---

## Truth-Preservation Rules

These are the load-bearing rules. Read them as a contract on every
translation.

The assistant **may**:

1. **Simplify.** Drop technical detail the audience doesn't need.
2. **Reframe.** Open with the audience's main concern (ROI for the
   owner; test scenarios for Jessica; risks for Chris).
3. **Reorder.** Whatever order makes sense for the audience.
4. **Change examples.** Pick examples that resonate — as long as
   they're real (drawn from this codebase, the handoffs, the demo
   script, or live curl output).
5. **Adjust vocabulary.** "16-stage post-LLM scrub pipeline" for
   Chris, "guardrails that keep the assistant on-brand" for the
   owner. Word choice is discretion; underlying claim is not.

The assistant **must not**:

1. **Invent features.** No "we now support multi-store" unless a
   handoff says so.
2. **Invent test results.** "1281 tests pass" requires that to be
   the current baseline in `DEALER_KIT_SESSION_START.md`.
3. **Invent customer value.** Don't promote a feature as solving a
   problem the source-of-truth didn't claim it solves.
4. **Invent business outcomes.** No "this saves the dealer $X/month"
   or "reduces lead leakage by Y%" without an explicit hedge.
5. **Imply a pilot is active when it is not.** As of the most recent
   session, the dealership has **not** been flipped to *Pilot
   active* with real customer traffic.
6. **Imply auth / multi-store / salesperson-agents exist.** None of
   those exist yet — they are sketched in
   `ASSISTANT_AGENT_CREATION_ROADMAP.md` as planned, not built.
7. **Imply manager chat shows real vehicle cards.** It does not —
   manager chat is *coaching/preview mode* (SESSION_010, reframe).

### Uncertainty rule

If the assistant is unsure whether a claim is supported by the
source docs:

- **Qualify it.** "Based on the SESSION_009 handoff…", "as of the
  2026-05-02 baseline…", "the demo script claims…".
- **Or fall back to a neutral summary.** "Onboarding settings are
  captured and shape the assistant's voice; pilot rollout details
  haven't been written down yet."
- **Never silently upgrade uncertainty into certainty.** Phrases
  like "definitely", "always", "guaranteed", "in production",
  "in pilot" require explicit support in source-of-truth.

If catching yourself adding a fact to make the explanation land
better — **stop**. The fact belongs in source-of-truth first, or
nowhere.

---

## Live Chat Mode

The mode triggered when a non-technical operator (Jessica, the
sales manager, the owner) is talking with Claude in real time.
Activated when the human is reporting what they tried, what they
saw, and what felt off — without reading code or system internals.

### Trigger phrases

- "I'm going to have Jessica start talking with you now"
- "talk to me like I'm not technical"
- "live chat mode" / "live chat with the operator"
- "I want to test something"
- *(Implicit)* any message that reports a real prompt + the
  assistant's response + a gut reaction, with no jargon

### Operator workflow

The validated path (worked end-to-end with Jessica on 2026-05-02,
which surfaced the SESSION_011 fix):

1. Operator opens a page and sends a real prompt.
2. Operator pastes back what the assistant said.
3. Operator describes — in plain English — what felt right or
   wrong about the reply.
4. Claude converts that input through the five-lens translation:
   - **Operator meaning** — what was the human actually testing,
     and what did "wrong" look like to them.
   - **Builder/system issue** — what is the underlying technical
     issue (Claude only surfaces this layer to the builder, or
     when the operator explicitly asks).
   - **Dealer-owner risk** — what does this mean for pilot
     readiness, customer trust, or business risk.
   - **Sales-manager workflow impact** — how does this change
     what the team actually does day to day.
   - **Claude Code implementation task** — what is the concrete
     engineering task that addresses it.
5. Claude reports the failure back to the operator in operator
   language, then opens the technical layer for the builder.

### Vocabulary contract

When talking with a non-technical operator, the assistant **must
not** use:

- *backend*, *frontend*, *repo*, *code*, *files*, *endpoint*,
  *API*, *database*, *schema*, *migration*, *commit*, *deploy*,
  *env*, *config*
- *model*, *LLM*, *Ollama*, *OpenAI*, *embeddings*, *regex*,
  *prompt*, *scrub*, *pipeline*, *stack trace*, *exception*,
  *mock*
- Test names, file paths, line numbers, function names, or any
  framework-specific term

Substitute with:

- *the system* (instead of the backend / the codebase)
- *the page she sees* (instead of the frontend / a route)
- *the saved settings* (instead of a database row or model)
- *save* (instead of POST / PATCH / persist / migrate)
- *guardrail* (instead of scrub / regex / pattern detector)
- *the assistant* (instead of the LLM / the model)
- *what the assistant said* (instead of the response payload)

### Refusal rule

If the operator asks "how does this work under the hood?" /
"show me the code" / "is this Python or React?" — redirect:

> "I can pull that up if you want, but it's not something you
> need to know to test this. The cleanest way is to keep going
> on the page and tell me what you see — I'll handle the rest."

If the operator presses ("no really, I want to know"), surface a
one-sentence high-level summary in their language ("There's a
guardrail on the coaching page that checks the shape of the
assistant's reply before showing it to you") — never paste code
or function names back.

### Grounding rule

Live chat mode is held to the **same** truth-preservation rules
as every other mode in this document. The operator's words do
not unlock new claims. The assistant must:

- Reflect what actually shipped, not what *will* ship.
- Say "this improves manager-test reliability" — **not** "this
  will increase sales" or "this saves the dealer money."
- If the operator asks "is this in production?" and the source
  of truth says no, the answer is "not yet" — never "soon",
  "imminent", or "in pilot" without explicit support.

When in doubt, downgrade to neutral phrasing rather than invent
business impact.

### Example — SESSION_011: Jessica catches a coaching-page leak

The worked example from 2026-05-02 that drove this contract.

**What Jessica did:**

1. Opened the page titled *Test Assistant Coaching Mode*.
2. Typed: *"i have $400/mo and want a sedan."*
3. The assistant replied:
   > *"Most sedans in our inventory fall under the payment
   > shown on the card, but I can show you some options that
   > might fit your budget. Would that be something you'd
   > consider?"*
4. Her reaction: *"this sounds like the customer page, not
   coaching me."*
5. She said: *"stop and flag now."*

**Five-lens translation:**

- **Operator meaning** (Jessica): The coaching page is supposed
  to teach managers what the assistant *would* say. This reply
  skipped that — it sounded like the assistant was selling to
  her, not coaching her. The phrase *"the card"* was the
  giveaway, since this page deliberately shows no cards.
- **Builder/system issue** (Chris): The earlier guardrail
  removed banned phrases sentence-by-sentence but did not enforce
  the **shape** of the reply. Novel customer-facing wording
  slipped through. The fix is structural enforcement — every
  coaching reply must be either pure coaching ("If a customer
  says X, I'd narrow on Y") or coaching plus a clearly-quoted
  preview reply. Anything else gets rewritten before Jessica
  sees it.
- **Dealer-owner risk:** Low pilot risk — coaching mode is
  internal-only and is not customer-visible. The risk it
  addresses is *internal trust*: managers will not rely on the
  coaching tool if it sounds like a sales pitch.
- **Sales-manager workflow impact:** None today, since the leak
  was caught before the team relied on the tool. After the fix,
  the coaching page reliably stays in coaching shape across
  saved tone variations.
- **Claude Code implementation task:** Tighten the coaching
  prompt to declare the two allowed shapes (Shape A: pure
  coaching; Shape B: coaching + quoted preview) explicitly, and
  add a structural validator that rewrites any non-conforming
  reply into a context-aware coaching fallback. Add regression
  tests including a replay of Jessica's exact prompt and the
  leaked reply.

**What ships from this:** a more reliable manager-coaching tool.
**What does not ship from this:** increased sales, faster lead
conversion, or any customer-facing change. Jessica's catch
improves *manager-test reliability* — that is the only claim the
translation layer is allowed to make.

---

## Example Translations

Three real examples drawn from the SESSION_008–010 handoffs. Each
example shows one source-of-truth fact rendered for each audience,
without inventing claims.

---

### Example 1 — SESSION_009: onboarding settings now shape live chat behavior

**Source-of-truth fact** (from
`docs/handoffs/SESSION_009_onboarding_controls_chat_behavior.md`
and `docs/onboarding/FREEDOM_FORD_ONBOARDING_PLAN.md` →
*Live AI wiring (SESSION_009)*):

> Six persisted onboarding fields now influence live chat behavior:
> `dealership_greeting`, `sales_tone`, `approved_phrases`,
> `banned_phrases`, `payment_disclaimer`, `escalation_rule`. One DB
> load per chat turn. Empty profile = identical pre-SESSION_009
> behavior. Banned phrases sentence-strip via a new post-LLM scrub
> stage with audit metadata (`banned_phrase_hits`). Backend baseline:
> 1172 → 1189 with subsequent sessions.

**For Chris** (builder summary):
> SESSION_009 wired the onboarding fields into `chat_engine.py` via a
> new `services/onboarding_overrides.py` helper. Six fields land:
> greeting + tone go into a "store voice" system block; approved /
> banned phrases land in the same block; banned-phrase scrub is a
> new post-LLM stage between `both_wording` and the length cap;
> disclaimer is appended after the length cap when the reply
> mentions payment language and we're not in cash mode. Empty
> profile = no metadata mutation, no behavior change (proven by
> `FallbackBehaviorIntegrationTests`). Risks: substring banned-phrase
> match can over-strip ("cheap" → "cheaper"); manager seed is still
> not linked to the `Salesperson` model.

**For Jessica** (operator / tester walkthrough):
> 1. Open `/dealer-ai-onboarding`, set a banned phrase like
>    "guaranteed approval", and Save.
> 2. Open `/dealer-ai-demo` and ask anything that might lead the
>    assistant to use that phrase.
> 3. Expected: the assistant's reply should not contain the phrase.
>    If it does, that's a regression. (Audit metadata records when
>    the scrub fires; for now, that's only visible in the database.)
> 4. Reset the field to empty, Save, retest the same prompt → the
>    assistant should behave identically to its pre-onboarding
>    default.
> 5. Repeat for tone (Warm + consultative vs Direct + fast-paced)
>    and check whether the reply *feels* different. "Good" looks
>    like a noticeable voice shift across two saves; "bad" looks
>    like identical replies regardless of tone.

**For the dealer owner** (owner brief):
> - Dealership-level voice settings (greeting, banned phrases,
>   disclaimer) now shape every customer reply automatically.
> - No production rollout yet — this is configurable but the
>   pilot has not started.
> - Risk: if a banned phrase is too generic, it can over-trim
>   replies. Recommend reviewing the phrase list with sales after
>   the first day of real traffic.

**For the sales manager** (workflow note):
> Settings saved on the Onboarding page now flow into every customer
> chat reply on the next message. Greeting, tone, encouraged
> phrases, banned phrases, disclaimer, and your escalation rule all
> apply. There's no preview yet built into the onboarding screen,
> but the **Test Assistant Coaching Mode** page lets you preview
> how the configured assistant responds to a sample customer prompt.

---

### Example 2 — SESSION_010: manager chat is coaching/preview mode, not customer chat with hidden cards

**Source-of-truth fact** (from
`docs/handoffs/SESSION_010_manager_chat_tester.md` →
*Coaching-mode reframe* and the page header copy in
`pages/ManagerChatPage.tsx`):

> `/dealer-ai-manager-chat` (titled *"Test Assistant Coaching Mode"*)
> is a coaching/preview mode. The LLM is told to act as the
> dealership's *internal sales coaching advisor* — explaining how
> the customer-facing assistant should respond, not impersonating
> it. Inventory / budget / cash blocks are skipped server-side; a
> view-level scrub strips card-implying phrases and first-person
> inventory claims. Customer demo (`/dealer-ai-demo`) is unaffected.

**For Chris** (builder summary):
> Manager chat endpoint is `POST /api/dealer-ai/manager-chat/`,
> stateless, ephemeral session tagged
> `metadata={"channel": "manager_test"}`. Engine reads that channel
> and: (a) skips the inventory / budget / cash-mode system blocks,
> (b) injects `MANAGER_COACHING_HINT` re-framing the LLM as a
> coaching advisor. View-level `scrub_card_implying_phrases` is a
> safety net for first-person inventory claims and "here are some
> options"-style phrasing. Customer-facing chat path (`send_message`)
> is gated out of both branches. Tests:
> `tests/test_manager_chat.py` (17 tests, including
> `test_user_reported_bad_reply_is_repaired`).

**For Jessica** (operator / tester walkthrough):
> 1. Open `/dealer-ai-manager-chat`. The page is titled
>    *"Test Assistant Coaching Mode"* and the note explicitly says
>    no vehicle cards render here.
> 2. Send a sample customer prompt, e.g. *"I want a truck under
>    30k."*
> 3. Expected: the reply explains how the assistant *would*
>    respond, or quotes a sample reply. Examples of "good" replies:
>    `"If a customer asks about trucks under $30k, I'd narrow the
>    deal first: 4WD, cab size, towing, or mileage."`
> 4. "Bad" looks like: *"Here are some options"*, *"We have a
>    Chevrolet Colorado"*, *"Take a look at these"*, *"Which one
>    catches your eye?"*. None of those should appear. If they do,
>    that's a regression.
> 5. Confirm `/dealer-ai-demo` (the customer page) still produces
>    its normal cards-and-prose output — the manager-only behavior
>    must not leak there.

**For the dealer owner** (owner brief):
> - Managers can now preview how the assistant guides a customer,
>   inside an internal page. It's not customer-facing.
> - Customer demo continues to be the live customer experience and
>   shows real vehicle options as cards.
> - The coaching tool helps you tune voice and banned phrases
>   safely before any real customer traffic — not a replacement
>   for the sales conversation.

**For the sales manager** (workflow note):
> The new *Test Assistant Coaching Mode* page lets you preview the
> assistant's response to any customer message you can think of.
> It's coaching-shaped — the assistant explains what it would say
> and may quote a sample reply. It deliberately does not show
> vehicle inventory because no cards are rendered on this page.
> Use it to sanity-check your saved tone, banned phrases, and
> disclaimer before going live, and to coach reps on the same
> "narrow first, then quote" pattern the assistant follows.

---

### Example 3 — SESSION_008: onboarding config persists, but is still one-store only

**Source-of-truth fact** (from
`docs/handoffs/SESSION_008_persist_onboarding_config.md` and
`docs/onboarding/FREEDOM_FORD_ONBOARDING_PLAN.md` →
*Persistence (SESSION_008)* + *Still deferred*):

> `DealerOnboardingProfile` is a singleton model (one row, enforced
> at the view layer). `GET|PUT|PATCH /api/dealer-ai/onboarding/profile/`
> reads/writes it. GET returns defaults if no row exists. No auth,
> no multi-store, no per-tenant boundaries. Salesperson seed
> captured but not linked to the existing `Salesperson` model.

**For Chris** (builder summary):
> One-store v0 — singleton enforced via `.first()` + upsert in the
> view, not a schema constraint, so the migration stays cheap to
> revisit when `Dealership` lands. Field shapes mirror the future
> entity split sketched in `ASSISTANT_AGENT_CREATION_ROADMAP.md`
> (DealerAssistant / SalespersonAgent / StorePolicyProfile) so a
> later migration splits without renames. Known gap: salesperson
> seed isn't linked to the `Salesperson` row used by
> `/dealer-ai-admin/team`.

**For Jessica** (operator / tester walkthrough):
> 1. Open `/dealer-ai-onboarding`, edit the dealership name, click
>    Save.
> 2. Refresh the page → the saved name should still be there.
> 3. Toggle a checklist item, Save, refresh → the toggle persists.
> 4. Open the Django admin (if available) and confirm
>    `DealerOnboardingProfile` has exactly one row.
> 5. The Onboarding page also has a salesperson seed section —
>    note that filling it does **not** create a salesperson under
>    `/dealer-ai-admin/team`. Linking those is on the roadmap; for
>    now, treat them as separate inputs.

**For the dealer owner** (owner brief):
> - Onboarding answers (voice, contact info, salesperson seed,
>   pilot checklist) persist on the server now. No more retyping.
> - One-store v0 — the system stores one dealership profile.
>   Multi-location and per-user permissions arrive later.
> - No login or role-based access yet. Anyone with access to the
>   page can save settings — keep the URL behind your existing
>   admin access.

**For the sales manager** (workflow note):
> The Onboarding page now actually saves your settings. Voice
> rules, escalation rule, payment disclaimer, and the pilot
> checklist all stick across reloads. One profile per dealership
> for now — you don't need to copy settings between stores
> because there's only one. The salesperson section saves a
> single seed entry; full salesperson management still lives at
> `/dealer-ai-admin/team`.

---

## What Each Person Needs Next

For each persona, the single most useful next action *given the
current state of the project* (latest handoff: SESSION_010
*coaching reframe*, baseline 1189 tests). Update when source
state changes — don't speculate.

- **Chris:** The strongest follow-on is linking the salesperson
  seed (captured in SESSION_008, untouched in SESSION_009 / 010)
  to the existing `Salesperson` model so the manager doesn't
  re-enter the same data on `/dealer-ai-admin/team`. Alternative
  candidates and out-of-scope items live in the SESSION_010
  handoff §"Recommended next session".

- **Jessica:** Two things are worth a focused tester pass next:
  (a) the manager-coaching-mode page across a handful of customer
  prompts, looking for any *"Here are some options"* / *"We have a
  …"* phrasing that survives the scrub; (b) the onboarding flow
  with various banned-phrase / tone combinations, checking whether
  saved changes visibly affect the customer-demo replies.

- **Dealer owner:** Confirm that the demo-ready surfaces (customer
  demo + manager coaching tester) match the conversation experience
  you expect a pilot to have. The pilot has **not** started — the
  go/no-go decision is yours; the system is ready to be flipped
  on once you're satisfied with voice and the banned-phrase list.

- **Sales manager:** Walk through the coaching-mode page with the
  voice settings you actually want and confirm the assistant
  produces replies you'd be comfortable having a customer see.
  When that's true, you're ready to do the same review against
  the customer-demo page with the team.

- **Salesperson** *(optional)*: No actionable item right now.
  Per-salesperson personalization is a planned future entity
  (`SalespersonAgent`); your existing advisor workspace at
  `/dealer-ai-advisor/<slug>` is unchanged.

---

## Last Verified

When was this doc last reconciled with actual source-of-truth?
Update the line below when you re-read the anchors and confirm
the translations / examples / next-actions still hold.

- **Last verified (contracts):** 2026-05-02 — by Chris against
  handoff `SESSION_010_manager_chat_tester.md` (coaching-reframe
  appendix) plus the in-flight SESSION_011 structural-coaching
  enforcement work and the Live Chat Mode contract validated
  with Jessica the same day. Backend baseline **1210 pass /
  1 skip / 0 fail** post-SESSION_011 (was 1189 pre).
- **Last verified (pivot reframing):** 2026-07-31 — SESSION_031
  Phase 5 updated title, companion docs, source-of-truth doc
  paths, and "Chris/Jessica" identity references from Freedom
  Ford scope to the kit scope. Personas, translation modes,
  truth-preservation rules, Live Chat Mode contract, and the
  three worked examples all preserved verbatim. Backend baseline
  now **1281 pass / 1 skip / 0 fail** post-SESSION_030+031.

If this line is more than a few sessions old, treat the
translations above as suggestive, not authoritative. Re-read the
latest handoff and update this doc before relying on it.
