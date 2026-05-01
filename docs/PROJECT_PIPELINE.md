---
title: "Freedom Ford — Runtime Flow Map"
status: live
generated: 2026-05-01
companion_docs: ["PROJECT_WHAT_IT_IS.md", "CONTEXT_KIT_INVENTORY.md", "../context/WHAT_IT_IS.md", "../context/INVENTORY.md", "../context/DO_NOTS.md"]
phase: 8r
test_baseline: 253
---

# Freedom Ford — Runtime Flow Map (PIPELINE.md)

> Companion to the project anchor (`PROJECT_WHAT_IT_IS.md`,
> `context/WHAT_IT_IS.md`) and the behavior inventory
> (`context/INVENTORY.md`). The anchors hold *what exists*; this doc
> holds **how a request actually moves through the system** — entry
> points, guard order, scrub order, state writes, retrieval paths, and
> the asymmetries between them.
>
> The two paths that reach the LLM are **`/chat/message/`** (full chat
> engine) and **`/vehicles/<id>/ask/`** (per-vehicle Q&A). They share
> the pre-LLM guard chain. They do **not** share the post-LLM scrub
> stack. That asymmetry is the most important thing in this doc — see
> *Known Asymmetries / Risks* below.

---

## 1. Entry Points

Every URL that can result in an LLM call, a deterministic guard reply,
or a vehicle/lead state write.

### 1a. Customer-facing — invokes LLM via `ChatEngine.handle_user_message`

| Verb | URL | View | LLM? | Notes |
|---|---|---|---|---|
| `POST` | `/api/dealer-ai/chat/start/` | `views.start_chat` | Optional | Creates `ChatSession`. If `initial_message` is provided, runs the full chat engine on it. |
| `POST` | `/api/dealer-ai/chat/message/` | `views.send_message` | Yes | The canonical chat turn. |

Both routes funnel into the same `ChatEngine(session).handle_user_message(text)`
pipeline (`backend/dealer_ai/services/chat_engine.py:2272`). Identical guards,
identical scrubs.

### 1b. Customer-facing — invokes LLM via `vehicle_assistant.answer_vehicle_question`

| Verb | URL | View | LLM? | Notes |
|---|---|---|---|---|
| `GET` | `/api/dealer-ai/vehicles/<id>/` | `views.vehicle_detail` | No | Pure deterministic: `analyze_vehicle` returns payment estimates @ 60/72/84mo, affordability notes, similar vehicles. |
| `POST` | `/api/dealer-ai/vehicles/<id>/ask/` | `views.vehicle_ask` | Yes | Per-vehicle natural-language Q&A. |

`vehicle_ask` calls `answer_vehicle_question(vehicle, question, profile, session)`
in `backend/dealer_ai/services/vehicle_assistant.py:163`. It runs the **same
pre-LLM guard chain** as the chat engine (Phase 8o+ fix —
`_check_pre_llm_guards`, `vehicle_assistant.py:111`), but **does not run any
post-LLM scrub**. See *Known Asymmetries* §6.

### 1c. Customer-facing — no LLM

| Verb | URL | View | Purpose |
|---|---|---|---|
| `POST` | `/api/dealer-ai/leads/` | `views.create_lead` | Persist a `CustomerLead` from a session payload. Validation only. |
| `GET` | `/api/dealer-ai/chat/session/<uuid>/` | `views.session_detail` | Read-only session + full message history. |
| `GET` | `/api/dealer-ai/salespeople/` | `views.public_salespeople` | "Meet the team" list — active salespeople only, contact details (phone/email/bio) intentionally omitted. (Manager Phase 4.) |
| `GET` | `/api/dealer-ai/salespeople/<slug>/` | `views.public_salesperson_detail` | Single-salesperson public detail. (Manager Phase 4.) |
| `GET` | `/api/dealer-ai/advisor/<slug>/` | `views.advisor_workspace` | Per-advisor workspace: profile + open leads + contacted leads (last 30d) for the slug-identified salesperson. Slug-by-obscurity is the only access control in v1; real auth lands in Phase 5. (Manager Phase 4.) |
| `POST` | `/api/dealer-ai/advisor/<slug>/lead/<id>/follow-up/` | `views.advisor_follow_up` | `follow_up.generate_follow_up_drafts()` — SMS / email follow-up drafts for an assigned lead. Same shared post-LLM safety stack as ad-copy + chat **plus** an `invented_appointment` scrub. 403 when the lead isn't assigned to this advisor. (Manager Phase 4.) |

### 1d. Admin / dashboard — read-only, no LLM

| Verb | URL | View | Purpose |
|---|---|---|---|
| `GET` | `/api/dealer-ai/admin/leads/` | `views.admin_lead_list` | Lead queue with `handed_off` / `urgency` / `since` / `ordering` filters. |
| `GET` | `/api/dealer-ai/admin/lead/<id>/` | `views.admin_lead_detail` | Lead + interested vehicles + session profile + full message transcript. |
| `POST` | `/api/dealer-ai/admin/lead/<id>/handoff/` | `views.admin_lead_handoff` | Build handoff packet (`handoff_service.build_handoff_packet`); optionally flips `handed_off=True`. |
| `GET` | `/api/dealer-ai/admin/chat-sessions/` | `views.admin_chat_session_list` | Session list w/ last-message snippet. |
| `GET` | `/api/dealer-ai/admin/trends/` | `views.admin_trends` | `trends_snapshot()` aggregate. |
| `GET` | `/api/dealer-ai/admin/pipeline/` | `views.admin_pipeline` | `pipeline_snapshot()` — derived sales pipeline (5 disjoint stages), demand-vs-supply buckets, and deterministic recommended actions (Manager Phase 2). |
| `POST` | `/api/dealer-ai/admin/ad-copy/` | `views.admin_ad_copy` | `ad_copy.generate_ad_copy()` — LLM-generated ad drafts (2–3 variants) for an inventory or marketing recommendation. Reuses the same post-LLM safety stack the chat path uses (rate / dealer-cost / negotiation / internal-directive scrubs) **plus** an `invented_promotion` scrub for invented "save $X" / "limited time" / "$0 down" / "guaranteed approval" phrasings. Read-only with respect to system state. (Manager Phase 3.) |
| `GET` | `/api/dealer-ai/admin/salespeople/` | `views.admin_salespeople` | List of every salesperson (active + inactive). Includes phone/email + bio. Used by the manager team page and the assignment dropdown. (Manager Phase 4.) |
| `POST` | `/api/dealer-ai/admin/lead/<id>/assign/` | `views.admin_lead_assign` | Assign a lead to a salesperson, or clear the assignment with `salesperson_id=null`. Refuses inactive advisors with 400. (Manager Phase 4.) |
| `GET` | `/api/dealer-ai/admin/audit-events/` | `views.admin_audit_events` | `audit_events_snapshot()` — surfaces flags from `ChatMessage.metadata`. |

### 1e. Demo control

| Verb | URL | View | Purpose |
|---|---|---|---|
| `POST` | `/api/dealer-ai/demo/reset/` | `views.demo_reset` | Wipe sessions/messages/leads, optionally reload `seed_demo_vehicles`. CSV imports (`source != "demo_seed"`) survive by default. |
| `POST` | `/api/dealer-ai/demo/scenarios/` | `views.demo_load_scenarios` | Run `seed_demo_scenarios` management command. |

> **Bypass register.** Anything that calls `ChatEngine.handle_user_message`
> or `answer_vehicle_question` must be listed in §1a or §1b. No new
> route may invoke the LLM without going through one of those two
> entry-point functions.

---

## 2. Pre-LLM Guard Order (chat_engine)

Implemented top-to-bottom in `ChatEngine.handle_user_message`
(`chat_engine.py:2272`). The first guard that fires returns immediately
— **no intent extraction, no LLM call**. The user message is always
persisted before any guard runs (with `flag="prompt_injection"` when
`detect_unsafe_request` matched).

| # | Guard | Detector | Canned reply | `metadata.flag` | Inventory attached? |
|---|---|---|---|---|---|
| 1 | Prompt injection / dealer-cost | `detect_unsafe_request` | `GUARD_RESPONSE` | `prompt_injection` | Yes — `search_vehicles(text, limit=5)` still runs (deterministic ORM, safe to expose). |
| 2 | Rate inquiry ("what's my APR?") | `detect_rate_inquiry` | `RATE_INQUIRY_RESPONSE` | `rate_inquiry` | Yes — same as #1. |
| 3 | External-value request (KBB / NADA / "what's my trade worth") | `detect_external_value_inquiry` | `EXTERNAL_VALUE_RESPONSE` | `external_value_inquiry` | Yes — same as #1. |
| 4 | Identity challenge ("are you a bot?") | `detect_identity_request` | `IDENTITY_RESPONSE` | `identity_request` | No. |
| 5 | Negotiation / price-match / OTD / discount | `detect_negotiation_request` | `build_negotiation_response(session)` (Phase 8p — context-aware: pulls focus vehicle / category / budget from `extracted_profile`) | `negotiation_request` | No. |
| 6 | Image request ("send pics") | `detect_image_request` | `_format_image_response_for(v)` if a current vehicle resolves; else `IMAGE_REQUEST_NEEDS_VEHICLE_RESPONSE` | `image_request` / `image_request_needs_vehicle` | One vehicle (the current) when resolved. Persists `current_vehicle_id` to profile. |
| 7 | Appointment / test-drive ("can I come see it?") | `detect_appointment_request` | `_format_appointment_response_for(v)` if resolved; else `APPOINTMENT_REQUEST_NEEDS_VEHICLE_RESPONSE` | `appointment_request` / `appointment_request_needs_vehicle` | One vehicle when resolved. Persists `current_vehicle_id`. |
| 8 | Live-agent / handoff request ("talk to a real person") | `detect_handoff_request` | `HANDOFF_RESPONSE` | `handoff_request` | No. |

**Order is load-bearing.** Identity (#4) sits before negotiation (#5)
because "are you real?" is a stronger persona-stability signal.
Negotiation (#5) sits before image (#6)/appointment (#7) so a customer
who says "can I come see it for the lowest price?" hits the
negotiation guard first — appointment scheduling cannot agree to a
discount. Handoff (#8) is last among the guard family because it's
the broadest pattern — it must not pre-empt a more specific guard
(appointment, negotiation) that already has a tighter response.

### Pre-LLM guard order (vehicle_assistant)

`_check_pre_llm_guards` (`vehicle_assistant.py:111`) mirrors the chat
order **minus image and appointment** (the per-vehicle endpoint already
has the vehicle in context, so those guards aren't needed):

1. `detect_unsafe_request` → `GUARD_RESPONSE`
2. `detect_rate_inquiry` → `RATE_INQUIRY_RESPONSE`
3. `detect_external_value_inquiry` → `EXTERNAL_VALUE_RESPONSE`
4. `detect_identity_request` → `IDENTITY_RESPONSE`
5. `detect_negotiation_request` → `build_negotiation_response(session, profile=…)`
   — when the per-vehicle endpoint supplies a vehicle it's pinned as
   `current_vehicle_*` so the reply names the vehicle.
6. `detect_handoff_request` → `HANDOFF_RESPONSE`

When a guard fires here, both the user question and the canned
assistant reply are written into the session transcript with
`metadata.kind="vehicle_ask"` and `metadata.vehicle_id=<id>`, and the
asked-about vehicle is attached via M2M.

---

## 3. Post-LLM Scrub Stack (chat_engine ONLY)

Runs only on the chat-engine path. Order is enforced by the conditional
chain in `handle_user_message` (`chat_engine.py:2654`–`2792`). Stages
1–3 are **wholesale-replacement** — when any of them fire, the partial
scrubs (4–7) skip. Stages 4–7 are **partial scrubs** that operate on
already-cleaned text. Stage 8 is a **non-rewriting drift detector**
that only logs/flags.

| # | Stage | Function | Behavior | Skip if earlier stage fired? |
|---|---|---|---|---|
| 1 | Sensitive-language safety rewrite | `detect_unsafe_response` → replace with `GUARD_RESPONSE` | Wholesale | n/a |
| 2 | Internal-confusion fallback | `detect_internal_confusion` → replace with `INTERNAL_CONFUSION_FALLBACK` | Wholesale | Skipped if #1 fired (severity priority) |
| 3 | Negotiation / fake-handoff override | `scrub_post_llm_override` → replace with `NEGOTIATION_RESPONSE` or `HANDOFF_RESPONSE` | Wholesale | Skipped if #1 or #2 fired |
| 4 | Rate-language scrub | `scrub_rate_language` → strip `@ 7.49%`, `APR of X%`, `interest rate`, `APR` | Partial | Skipped if #1, #2, or #3 fired |
| 5 | Internal-directive scrub | `scrub_internal_directives` → strip `BUDGET ANALYSIS`, `see full math`, `DO NOT recompute`, `(W.A.C. — see BUDGET ANALYSIS …)` parentheticals | Partial | Skipped if #1, #2, or #3 fired |
| 6 | Default-assumption scrub | `scrub_default_assumption_language` → strip "with no money down", "assuming 72 months", "default 72-month term" | Partial | Skipped if #1, #2, or #3 fired |
| 7 | Budget category-label scrub | `scrub_budget_category_labels(only_near_fits=…)` → rewrite "nearly in budget", "slightly above budget", `_budget_fit=fit` echo to canonical "close to your target" | Partial | Skipped if #1, #2, or #3 fired |
| 8 | Payment-consistency check | `check_payment_consistency` (chat_engine.py:1492) | Non-rewriting; logs warning + sets `metadata.budget_query.payment_drift = [floats]` | **Only runs when `budget_ctx.is_budget_query` and `target_monthly is not None` and #1 did not fire.** |

**Why this order is load-bearing:**

- #1 must run first because dealer-cost / invoice-price leaks are the
  highest-severity compliance failures. A partial scrub that left a
  cleaned but still-leaking sentence is worse than wholesale-replace.
- #2 (internal-confusion fallback) runs before partial scrubs because
  partial scrubs leave half-baked sentences when the model dumped
  guideline prose. Wholesale replacement is the safer recovery.
- #3 (post-LLM negotiation/handoff override) runs before partial scrubs
  for the same reason as #2.
- #4 (rate scrub) runs **before** #5 (directive scrub) so rate-scrub's
  `(W.A.C.)` replacements survive into the directive pass — the
  directive scrub knows about that parenthetical and won't strip it.
- #5 runs **before** #8 (payment-consistency) so the `$X/mo` extraction
  in #8 operates on cleaned text — otherwise leaked directive prose
  would mask drift detection.
- #6 (default-assumption) runs after #5 to operate on already-cleaned
  text — its tidying step expects directive prose to have been stripped.
- #7 (category-label) is last among the partial scrubs because its
  `only_near_fits` mode depends on the budget-context counts produced
  much earlier; it doesn't constrain ordering against the others.

**Flag precedence on the assistant message** (`metadata.flag`):

```
post_safety_rewrite             > internal_confusion_fallback
                                > post_llm_override (+ override_kind)
                                > multiple_scrubs_fired (≥ 2 partial scrubs)
                                > rate_language_scrubbed
                                > internal_directive_scrubbed
                                > default_assumption_scrubbed
                                > category_label_scrubbed
```

`metadata.scrubs` is the full list of partial scrubs that fired, in
detection order, regardless of which `flag` was chosen for the headline.

---

## 4. State Surfaces

| Surface | Lifetime | Shape | What lives here |
|---|---|---|---|
| **`ChatSession.extracted_profile`** | Session-durable, merged across turns by `merge_profile` | JSON dict, allow-listed by `intent_parser.PROFILE_FIELDS` | Structured customer state: `intent`, `vehicle_type`, `make`, `make_lock`, `model`, `condition`, `target_monthly_payment`, `down_payment`, `term_months`, `trade_in`, `credit_range`, `urgency`, `financing_interest`, `service_interest`, `current_vehicle_id`, `current_vehicle_stock`, `drivetrain`, `max_price`. |
| **`ChatMessage.metadata`** (assistant) | Per-turn, forever | JSON dict, free-form | Audit signals: `provider`, `matched_count`, `extracted_this_turn`, `flag`, `mode` (e.g. `discovery`), `scrubs[]`, `override_kind`, `current_vehicle_stock`, `budget_query{target_monthly, down_payment, term_months, max_price, tolerance, in_budget_count, near_fit_count, no_fit, vehicle_fits{<id>{budget_fit, estimated_payment, payment_delta}}, payment_drift?}`. |
| **`ChatMessage.metadata`** (user) | Per-turn, forever | JSON dict | `flag="prompt_injection"` when `detect_unsafe_request` fired pre-LLM. For vehicle_ask path: `vehicle_id`, `kind="vehicle_ask"`, optional `flag`. |
| **`ChatMessage.matched_vehicles`** | Per-turn, forever | M2M | Vehicles surfaced in this turn. Order preserved via through-table pk (`_matched_vehicles_in_order`) so ordinal references ("the second one") work. |
| **`ChatSession.metadata`** | Session-durable | JSON dict | Free-form session metadata (UTM / page / channel). Declared on the model; not heavily written by current code. |
| **`Vehicle._budget_fit` / `_estimated_payment` / `_payment_delta`** | Single request, in-memory | Transient instance attrs | Annotations applied by `_classify_candidates` (`chat_engine.py:1837`). Read by `VehicleSerializer` via `SerializerMethodField`. Not persisted. |
| **`Salesperson` table** | Persistent | Typed model fields + `specialties` JSONField | Manager Phase 4: dealership advisor profiles (name, slug, title, phone/email, photo_url, specialties, bio, is_active). Inactive advisors are kept around so historical assignments still resolve. |
| **`CustomerLead.assigned_to`** | Persistent | Nullable FK → Salesperson | Manager Phase 4: which advisor owns this lead. `SET_NULL` on advisor delete. Per Phase 4 decision #1, deactivating an advisor does NOT auto-unassign existing leads. |
| **`CustomerLead.assigned_at`** | Persistent | Nullable DateTimeField | Manager Phase 4: timestamp of the most recent assignment (cleared on unassign). Sorted by the advisor workspace open-leads list. |

> **Rule:** durable session state → `extracted_profile` (allow-listed,
> typed enums). Per-turn audit / scrub / drift signals →
> `ChatMessage.metadata` (free-form). Mixing them is the silent bug
> from PROJECT_PIPELINE.md's drift-surface list — a "what did the
> customer say their budget is?" answered from the latest message's
> metadata is wrong as soon as the customer reaffirms the budget on
> turn 2 without restating the number.

### Allow-lists / drop zones

| Allow-list | Location | Failure mode if a new field is missed |
|---|---|---|
| **`PROFILE_FIELDS`** | `intent_parser.py:44` | New profile field is captured by regex/LLM but **silently dropped by `merge_profile`** — never persisted to `extracted_profile`. |
| **`INTENT_VALUES` / `VEHICLE_TYPES` / `CONDITIONS` / `URGENCIES` / `CREDIT_RANGES` / `DRIVETRAINS`** | `intent_parser.py:26-40` | LLM emits a new enum value (e.g. "wagon"), `_validate` drops it; the regex fallback is the only path that can land it. |
| **`VehicleSerializer.fields`** | `serializers.py:18` | New `Vehicle` model column is not exposed to the frontend even after migrations. |
| **`ChatMessageSerializer.fields = ["id", "role", "content", "matched_vehicles", "created_at"]`** | `serializers.py:63` | **`metadata` is intentionally not exposed.** Frontend chat consumers never see `flag`, `scrubs`, `budget_query`, `payment_drift`. Audits live in `/admin/audit-events/` and `/admin/lead/<id>/` where the metadata is read server-side. Adding a new audit signal to `metadata` won't surface in `/chat/message/` responses — that's the design, but it's an asymmetry the next session should know about. |
| **`SYSTEM_PROMPT` / `BUDGET ANALYSIS` block / `AVAILABLE INVENTORY` block** | `chat_engine.py:23` (system) and `_format_budget_block` / `_format_vehicle_block` | New fact added to `Vehicle` or `extracted_profile` is not visible to the LLM unless the formatter adds it. Especially: a new structural filter must be reflected in the inventory line so the LLM doesn't recommend a vehicle that fails the filter. |
| **`KEYWORD_SIGNALS`** | `inventory_search.py:21` | Customer uses a new vocabulary term ("crew cab", "shortbed") that the keyword path doesn't recognize → falls through to broad keyword OR clause; no structural narrowing. |

---

## 5. Retrieval Paths

There are **two retrieval entry points**. They share most filters but
diverge on a handful — when a new structural filter is added, both
must be updated or the chat path will return different results
depending on whether the customer has a budget.

### Path A — Budget-constrained: `build_budget_context` (`chat_engine.py:1912`)

Triggers when `_detect_budget_query` returns True (explicit budget
cue, monthly target this turn, or a `target_monthly_payment` already
in profile) and a `target_monthly_payment` is present.

Filters applied to `Vehicle.objects.filter(is_available=True)`:

- `body_style` — from `profile.vehicle_type` (one of truck/suv/car/ev/van).
- `model__iexact` — from `profile.model`.
- `condition` — from `profile.condition` (when set and not "any").
- `drivetrain` — `4WD` → `Q(drivetrain__icontains="4x4") | Q(drivetrain__icontains="4WD")`; `AWD` / `RWD` / `FWD` → exact-match. Canonical values from `intent_parser.DRIVETRAINS`.
- `make__iexact` — only when `profile.make_lock=True` and `profile.make` set.

Then every candidate is scored by `_classify_candidates` (`chat_engine.py:1837`):

- `payment <= target` → `_budget_fit="fit"`.
- `payment - target <= max($75, 15% × target)` → `_budget_fit="near_fit"`.
- otherwise → `_budget_fit="over_budget"`.

Each vehicle is annotated in-place with `_budget_fit`, `_estimated_payment`,
`_payment_delta`. Ordering: Ford-first within bucket; in_budget by
descending payment (price-up); near/over by ascending delta.

`closest_above` (over-budget context) is only returned when **both**
in_budget and near_fit are empty.

### Path B — Keyword search: `search_vehicles` (`inventory_search.py:160`)

Used when budget mode is False (no monthly target). The chat engine
also passes `make` (when `make_lock`) and `max_price` (when
`profile.max_price` is set, Phase 8r).

Filters applied via `parse_filters(query)` + kwargs:

- `body_style` — from `KEYWORD_SIGNALS["truck"|"suv"|"ev"|...]`.
- `condition` — from `KEYWORD_SIGNALS["used"|"new"|"certified"|"pre-owned"|"preowned"]`.
- `model__iexact` — from `KEYWORD_SIGNALS["f-150"|"ranger"|"maverick"|"explorer"|"escape"]`.
- `model__icontains` — from `KEYWORD_SIGNALS["bronco"|"mach-e"|"mache"|"mustang"]`.
- `drivetrain__icontains` — from `KEYWORD_SIGNALS["4x4"|"awd"|"4wd"]` (note: only "4" or "AWD" tokens — no "RWD" / "FWD" recognition).
- `max_price` — parsed from "under $X" / "under Xk" *or* passed as kwarg (the kwarg + parsed ceiling intersect, the tighter wins).
- `min_year` — parsed from `20\d{2}` mentions.
- `make__iexact` — only when `make` kwarg supplied.

Loose-fallback re-runs the queryset with `keywords=[]` if the first
pass returned nothing, preserving structural filters (price ceiling,
make lock, etc.).

Final ordering: Ford-first → year DESC → price ASC.

### Path C — Pronoun follow-up (chat_engine.py:2589)

When `_is_followup_about_current_vehicle(text, profile)` returns True
and `profile.current_vehicle_id` resolves, the engine **skips both
retrieval paths** and uses `[current_vehicle]` as the matched set. If
budget mode is also active, the single vehicle is re-classified by
`_classify_candidates` so the line carries `_budget_fit` /
`_estimated_payment` annotations.

### Path D — Discovery mode (chat_engine.py:2554)

When `_should_enter_discovery_mode` returns True (no budget signals,
broad request like "I want a convertible" or "looking for an SUV"),
the engine **skips both retrieval paths** and substitutes
`_format_discovery_block` for the inventory block. `matched=[]`,
`budget_block=""`, `budget_mode=False`.

### Path E — Vehicle-detail / vehicle-ask "similar inventory"
(`vehicle_assistant._similar_vehicles`)

For the per-vehicle endpoints. Filters:

- `body_style` (anchor's body_style)
- `price` within ±20% of anchor.
- Loose fallback: any body, ±15-20% widened band.

This path only feeds the LLM's `SIMILAR INVENTORY` block in
`/vehicles/<id>/ask/`. It does not write `_budget_fit` annotations
and does not flow into `matched_vehicles`.

### Shared filters across Path A and Path B

| Filter | Path A (budget) | Path B (keyword) |
|---|:---:|:---:|
| `body_style` | profile.vehicle_type | KEYWORD_SIGNALS |
| `condition` | profile.condition | KEYWORD_SIGNALS |
| `model` (iexact) | profile.model | KEYWORD_SIGNALS |
| `drivetrain` 4WD/AWD | profile.drivetrain | KEYWORD_SIGNALS (4x4/4wd/awd) |
| `drivetrain` RWD/FWD | profile.drivetrain (`__iexact`) | **not recognized** — keyword path drops them |
| `max_price` (sticker ceiling) | **not applied** — payment classification supersedes | parsed from text **or** kwarg from profile.max_price |
| `make` (brand lock) | profile.make_lock + profile.make | `make` kwarg only when `make_lock` |
| `min_year` | not applied | parsed from text |
| Payment classification (fit/near_fit/over_budget) | yes — `_classify_candidates` | **no** — keyword path has no notion of "fit" |
| Ford-first ranking | yes | yes |

**Asymmetry to remember:** `profile.max_price` (cash-budget ceiling
captured Phase 8r) only narrows results in **Path B**. In Path A the
sticker ceiling is implicit in the payment-classification math; the
filter list above does **not** apply `max_price` directly. If a
customer says "I want to spend under $20k AND keep it under $400/mo",
Path A's near-fit window (15% over $400) might surface a $24k vehicle
whose payment is within tolerance — that vehicle's sticker exceeds
the customer's stated cash ceiling. The current behavior is "budget
mode wins" — re-evaluate before adding new cash-ceiling logic.

---

## 6. Known Asymmetries / Risks

This is the section that exists so the next session doesn't add a
guard or filter to one path and silently bypass it on the other.

### 6.1 ~~`vehicle_assistant` runs pre-LLM guards but no post-LLM scrubs~~ — **CLOSED in Manager Phase 4**

**Status: closed. The shared scrub helper now serves four LLM call sites.**

`services/llm_safety.py` exposes `apply_post_llm_scrubs(text, *, kind)`
as the single source of truth for the post-LLM scrub stack. Four call
sites consume it:

- `chat_engine` — keeps its existing per-stage scrub functions, which
  `llm_safety` delegates to. Behaviour is byte-for-byte identical
  (locked by ~580 chat tests).
- `ad_copy` (Manager Phase 3) — refactored to call
  `apply_post_llm_scrubs(kind="ad")` instead of importing chat-engine
  scrubs directly.
- `vehicle_assistant.answer_vehicle_question` (Manager Phase 4) — now
  calls `apply_post_llm_scrubs(kind="vehicle_ask")` after the LLM
  reply. Hard-rewrite cases (`dealer_cost_safety`,
  `post_llm_override:negotiation`, `post_llm_override:handoff`)
  substitute `GUARD_RESPONSE` / `NEGOTIATION_RESPONSE` /
  `HANDOFF_RESPONSE` respectively. Partial scrubs strip rate /
  directive / default-assumption phrases inline. The `metadata.flag`
  on the persisted assistant message records which stage fired so
  audits surface this just like the chat path.
- `follow_up` (Manager Phase 4) — calls
  `apply_post_llm_scrubs(kind="follow_up")` which adds **two**
  follow-up-only scrubs on top of the chat parity stack:
  `invented_promotion` (shared with ad_copy) and
  `invented_appointment` (the AI must never claim a specific
  appointment slot).

If a future LLM call site is added it MUST go through `llm_safety`
or this section gets re-opened.

### 6.2 `ChatMessage.metadata` is not exposed by `ChatMessageSerializer`

**Status: by design, but a frontend foot-gun.**

`ChatMessageSerializer.fields = ["id", "role", "content", "matched_vehicles", "created_at"]`
omits `metadata`. New audit signals added to `metadata` by the chat
engine (Phase 8 has accumulated `flag`, `mode`, `scrubs`,
`budget_query{...}`, `payment_drift`, `override_kind`,
`current_vehicle_stock`, `extracted_this_turn`) **never reach** the
customer-facing chat frontend. They are read by:

- `/admin/audit-events/` (`audit_events_snapshot`).
- `/admin/lead/<id>/` (returns full transcript via
  `_serialize_lead_messages` → `ChatMessageSerializer`, so it hits the
  same drop). Audits at the lead-detail level rely on the message
  content, not metadata. The metadata is reachable via
  `/admin/chat-sessions/` only via aggregate stats, not raw rows.
- `/chat/session/<uuid>/` (read-only session view) — also drops
  `metadata` because it serializes through `ChatSessionSerializer →
  ChatMessageSerializer`.

This is fine for a customer chat surface (we don't want flags showing
up in the UI), but a manager dashboard wanting per-message scrub
visibility cannot use the existing serializers. Adding a new
admin-only `AdminChatMessageSerializer` that includes `metadata` is
the clean fix when that need arises.

### 6.3 `max_price` profile field is honored in Path B but not Path A

**Status: documented above (§5). Not a bug — design choice.**

`profile.max_price` (Phase 8r) routes into `search_vehicles(max_price=…)`
in the non-budget keyword path. In budget mode, `build_budget_context`
ignores it and lets payment-classification do the bounding. A
customer who states both ("$500/mo and under $20k") will hit budget
mode and the sticker cap won't apply. Re-evaluate before changing.

### 6.4 `KEYWORD_SIGNALS` does not recognize RWD / FWD

**Status: real gap.**

`inventory_search.KEYWORD_SIGNALS` has entries for `"4x4"`, `"awd"`,
`"4wd"` only. `_DRIVETRAIN_KEYWORDS` in `intent_parser` recognizes
`RWD` / `FWD` / `2wd` / `4x2` / `rear-wheel drive` / `front-wheel drive`
and stores canonical `"RWD"` / `"FWD"` in profile. Path A
(build_budget_context) honors all four. Path B (search_vehicles) only
honors 4WD/AWD via keyword, so a non-budget customer asking for a
"FWD car under $15k" will see results that include AWD/4x4 vehicles.

### 6.5 Discovery mode skips payment-consistency check

**Status: by design — discovery mode has no inventory.**

When `discovery_mode=True`, `matched=[]` and `budget_ctx.is_budget_query=False`.
The post-LLM payment-consistency check (§3 #8) is gated on
`budget_ctx.is_budget_query`, so it doesn't run. Discovery replies
shouldn't quote `$X/mo` numbers (the discovery block tells the LLM not
to), but if one leaks there is no drift detection. The
internal-confusion fallback (§3 #2) catches the worst case (echoed
guideline prose) but not a quietly invented payment.

### 6.6 `start_chat` shares the chat path; admin/demo do not invoke LLM

`POST /chat/start/` with `initial_message` runs the same
`ChatEngine.handle_user_message` as `/chat/message/`, so it inherits
the full guard + scrub stack. Admin endpoints and `/demo/reset/` /
`/demo/scenarios/` don't invoke the LLM at all — they're deterministic
ORM operations and management commands.

### 6.7 Drift surfaces still classified as **external / unmanaged**

- **No external scheduler.** Nothing in this repo registers a
  Celery / RQ / cron beat. `seed_demo_vehicles` and `seed_demo_scenarios`
  are management commands invoked synchronously from `views.demo_reset` /
  `views.demo_load_scenarios`. No orphaned task risk today.
- **No webhook receivers.** No third-party callback routes register the
  LLM path.
- **No module-load reorder fragility known.** `chat_engine` and
  `vehicle_assistant` import each other only one direction
  (`vehicle_assistant` imports the guards from `chat_engine`); the
  service module imports are top-of-file in every entry point.

If any of those change, add the new surface to §6 with an explicit
"covered by guard" or "intentionally unmanaged" tag.

---

## 7. Decision Authority

The deterministic / language boundary as it actually maps to this
codebase.

| Layer | Files | Responsibility |
|---|---|---|
| **Pre-LLM guards** | `chat_engine.py` `detect_*` + `vehicle_assistant._check_pre_llm_guards` | Refuse / canned response. No LLM call. |
| **Intent extraction** | `intent_parser.parse_intent` (regex pre-pass + LLM JSON, regex wins on numerics) | Extract structured profile. LLM is only used for enums/keywords. |
| **Inventory + classification** | `inventory_search.search_vehicles`, `chat_engine.build_budget_context`, `_classify_candidates` | Decide what's available, what fits, what doesn't. |
| **Payment math** | `payment_engine.estimate_payment`, `affordable_max_price` | Sole source of truth for monthly numbers. The LLM **must not** invent or recompute. |
| **Compliance scrubs** | `chat_engine.scrub_*`, `detect_unsafe_response` | Last-line defense for rate language, dealer cost, leaked directives, invented categories. |
| **LLM (`provider.chat`)** | `services/llm/{base,ollama,openai_provider,factory}.py` | Language only — explain the deterministic decisions, ask the next narrowing question, rephrase for tone. |

> **Rule (from `context/DO_NOTS.md`):** the LLM **must never** create
> pricing, determine eligibility, or make commitments. If a request
> appears to ask the LLM to do any of those, the entry point is wrong
> — route it through the deterministic layer (intent → inventory →
> classification → payment math) first, and use the LLM to explain
> the result.

---

## 8. Operational Hazards

- **Two dev servers:** backend on `:8001` (Django + DRF), frontend on
  `:5173` (Vite). The frontend proxies API calls via
  `VITE_API_PROXY_TARGET`. Stale processes on either side leave
  "fixed it once, the other still has the old code" dead-ends.
- **No background workers.** No Celery, no cron beat. Demo / inventory
  loads happen synchronously inside `views.demo_reset` /
  `views.demo_load_scenarios`. If Celery is added later, the ChatEngine
  call must remain on the request path or all the post-LLM scrubs
  become a different audit problem.
- **Demo reset preserves CSV-imported inventory.** `views.demo_reset`
  only deletes `Vehicle.objects.exclude(source="demo_seed")` when the
  caller passes `delete_imported_vehicles: true`. The default leaves
  imported inventory alone. Tests assume this — don't flip the default.
- **LLM provider is swappable.** `DEALER_AI_LLM_PROVIDER=openai` flips
  to `openai_provider.OpenAIProvider`. Tests use
  `tests/_mocks.MockLLMProvider` and never hit a real model. Provider
  contract is `chat(messages, *, temperature, max_tokens, **kwargs) -> str`
  — do not change this surface (per `context/DO_NOTS.md`).
- **Test count baseline: 253 backend tests passing as of Phase 8l.**
  Drops below this without an explanation are a regression. Run with
  `python manage.py test` from `backend/`.

---

## 9. Drift Surfaces (claim-or-disclaim)

| Surface | Status | Notes |
|---|---|---|
| Alternate LLM entry point: `/vehicles/<id>/ask/` | **Claimed** — pre-LLM guards mirror chat_engine; **post-LLM scrubs missing** (see §6.1). |
| Budget retrieval (Path A) vs keyword retrieval (Path B) | **Claimed** — filter matrix in §5; known gaps: RWD/FWD recognition (§6.4), `max_price` ignored in budget mode (§6.3). |
| Allow-list: `PROFILE_FIELDS` | **Claimed** — listed in §4. New profile field MUST be added or it silently drops. |
| Allow-list: `ChatMessageSerializer` drops `metadata` | **Claimed** (§6.2) — by design. |
| External schedulers / orphan tasks | **Disclaimed** — none exist (§6.7). |
| Webhook receivers / signal handlers calling LLM | **Disclaimed** — none exist. |
| Module-load reorder fragility | **Disclaimed** — none observed. Re-check if `chat_engine` is split. |

---

## 10. Last Verified

- **Date:** 2026-05-01
- **Customer chat:** stabilized through Phase 8r (budget classification,
  near-fit logic, prompt-injection / rate / external-value / identity /
  negotiation / image / appointment / handoff guards, full post-LLM
  scrub stack, multi-brand used inventory with Ford-first ranking,
  cash-budget ceiling, drivetrain narrowing).
- **Manager dashboard:** Phases 1 + 2 + 3 + **Phase 4 complete**.
  Phase 1 = lead queue with `handed_off` / `urgency` / `since` /
  `ordering` filters, lead detail + handoff packet, chat-session list,
  trends, audit-events snapshot. Phase 2 = sales pipeline (5 derived
  stages), demand-vs-supply mismatch panel, deterministic recommended
  actions. Phase 3 = LLM-backed ad-copy generation
  (`POST /admin/ad-copy/`) with shared safety scrubs. Phase 4 =
  Salesperson directory + lead assignment + per-advisor workspace
  + AI follow-up draft generation (SMS + email). The shared post-LLM
  scrub helper `services/llm_safety.py` now serves chat_engine,
  vehicle_assistant, ad_copy, AND follow_up — **§6.1 is closed**.
- **Schema delta (Phase 4):** **one migration** —
  `0003_salesperson_customerlead_assigned_at_and_more`. Adds the
  `Salesperson` table and two nullable fields on `CustomerLead`
  (`assigned_to` FK + `assigned_at` timestamp). No customer-chat
  code paths read or write these fields.
- **Test baseline:** 640/640 backend tests passing (was 586; +54 from
  Phase 4: shared `llm_safety` parity, vehicle_assistant scrub
  closure, `Salesperson` model behaviour, lead-assignment endpoint
  with deactivated/unknown/null edge cases, public + admin
  salespeople listings, advisor workspace listing/404 paths,
  follow-up generator scrubs for rate / dealer-cost / appointment
  promises, endpoint 400/403/404 paths, pipeline payload now
  includes `assigned_to`). Drops below this without an explanation
  are a regression.
- **Frontend:** `tsc --noEmit` clean, `vite build` succeeds. New
  routes: `/dealer-ai-admin/team` (manager team page) and
  `/dealer-ai-advisor/:slug` (per-advisor workspace). New
  components: `SalespersonCard`, `AssignmentDropdown`,
  `MyLeadsTable`, `FollowUpDraftModal`, `SalesTeamPage`,
  `AdvisorWorkspacePage`. Existing `LeadDetailModal` gains an
  assignment chip; `HandoffQueue` gains assignment filter chips;
  `SalesPipeline` lead cards show an advisor avatar badge.
- **Auth posture (v1):** the advisor workspace is currently
  slug-by-obscurity. This is an explicit demo-acceptable trade-off,
  flagged here so Phase 5 picks it up.
- **Known active gap to close next:** real authentication for
  `/dealer-ai-admin/*` and `/dealer-ai-advisor/<slug>/*` routes
  (currently anyone with the URL can view advisor leads).
- **Next priority:** Phase 5 — advisor / manager auth (likely
  Django auth + a per-Salesperson `user` link), and **outcome states**
  beyond `Contacted` on `CustomerLead` so the pipeline can show
  `Won` / `Lost` / `Test drive booked`. Both are schema-touching
  changes deferred from earlier phases.
- **Next recommended audit:** before any new entry point is added that
  invokes the LLM, or any new structural inventory filter.
