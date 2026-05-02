---
date: 2026-05-02
title: SESSION_010 — manager-side chat tester (+ hotfix)
type: implementation-summary
test_baseline: 1186
---

# Session handoff — manager chat tester

A small sandbox that lets a dealership manager preview how the
configured assistant responds to a customer prompt without affecting
real customer sessions. Stateless API + minimal UI; reuses the
existing chat engine wholesale so the SESSION_009 onboarding overrides
flow through unchanged.

Use this snapshot to pick up at SESSION_011.

---

## What shipped

### Backend

- **Serializer:** `ManagerChatInputSerializer` in `serializers.py`
  (single field, `message: CharField`).
- **View:** `manager_chat` in `views.py` (`@api_view(["POST"])`).
  Creates an ephemeral `ChatSession` with
  `metadata={"channel": "manager_test"}`, runs `ChatEngine`, returns
  `{"reply": <text>}`. No vehicle cards in the response.
- **URL:** `path("manager-chat/", ...)` → mounted at
  `/api/dealer-ai/manager-chat/`.
- **Tests:** `tests/test_manager_chat.py`, 8 tests covering:
  happy path returns reply, session tagged manager_test, response
  shape (reply only — no cards), each call creates a new session
  (statelessness), missing message → 400, empty/whitespace
  message → 400, banned-phrase scrub fires through this path
  (proves SESSION_009 overrides apply), no-profile pass-through is
  unmodified.

### Frontend

- **API helper:** `sendManagerChat(message)` and
  `ManagerChatResponse` type appended to `lib/api.ts`. Uses the
  existing `postJSON` helper (no new abstractions).
- **Page:** `pages/ManagerChatPage.tsx`. Header note ("Test how
  your configured sales assistant responds to customers."), local
  transcript with user/assistant bubbles (no vehicle cards), draft
  textarea, Send button (Cmd/Ctrl+Enter shortcut), idle/sending/
  error status, auto-scroll to latest turn.
- **Route:** `/dealer-ai-manager-chat` registered in `main.tsx`.
- **Nav:** new top-level link *"Test assistant"* in `App.tsx`'s
  `NAV_LINKS`.

### Docs

- **`docs/onboarding/FREEDOM_FORD_ONBOARDING_PLAN.md`** — added a
  *Manager chat tester (SESSION_010)* section naming the page,
  endpoint, statelessness model, and the explicit non-customer-
  facing distinction.
- **`docs/FREEDOM_FORD_SESSION_START.md`** — baseline updated:
  test count `1172 → 1180`, new row for the manager chat tester.
- **`00-START-NEXT-SESSION.md`** — hand-written section replaced
  with SESSION_011 priorities.

---

## File changes

```
backend/
  dealer_ai/
    serializers.py                              (+13 +0)
    urls.py                                     (+6 +0)
    views.py                                    (+38 +0)
    tests/test_manager_chat.py                  (new, 8 tests)
frontend/
  src/
    App.tsx                                     (+2 +0)
    lib/api.ts                                  (+10 +0)
    main.tsx                                    (+5 +0)
    pages/ManagerChatPage.tsx                   (new, ~175 lines)
docs/
  FREEDOM_FORD_SESSION_START.md                 (baseline updated)
  onboarding/FREEDOM_FORD_ONBOARDING_PLAN.md    (manager-tester section)
  handoffs/SESSION_010_manager_chat_tester.md   (this file)
00-START-NEXT-SESSION.md                        (next-task → SESSION_011)
```

No changes to chat engine, scrub stack, payment engine, candidate
classifier, inventory selection, intent parser, demo seeders. The
manager-chat endpoint is a pure call site — it consumes the engine,
doesn't modify it.

---

## Verification

### Backend

```bash
cd backend && source .venv/bin/activate
python manage.py test dealer_ai
# Ran 1180 tests in 2.563s — OK (skipped=1)
```

New baseline: **1180 pass, 1 skipped, 0 failed** (was 1172 + 8 new).

### Frontend

```bash
cd frontend
npx tsc --noEmit       # 0 errors
npx vite build         # built in 876ms; 343kB JS, 32kB CSS
```

### Live smoke

Verified end-to-end against the running dev servers:

```bash
$ curl -s -X POST http://localhost:8001/api/dealer-ai/manager-chat/ \
       -H "Content-Type: application/json" \
       -d '{"message":"hello"}'
{"reply":"Hello! Are you looking for information on purchasing a vehicle or need help with something else?"}
```

The frontend route at `http://localhost:5173/dealer-ai-manager-chat`
returns 200 (page renders).

### Manual tone-change smoke

The user-spec ask was:

1. Send a message at `/dealer-ai-manager-chat`.
2. Change onboarding tone, save.
3. Send the same message again.
4. Confirm behavior changes.

The agent could not run the manual tone-change comparison
(no headless browser); please run it against the live servers. The
underlying mechanism is the same SESSION_009 wiring already covered
by `test_onboarding_overrides.py` integration tests.

---

## API reference

### Request

```
POST /api/dealer-ai/manager-chat/
Content-Type: application/json

{"message": "hello"}
```

### Success response (200)

```json
{"reply": "Hello! Are you looking for information on purchasing a vehicle or need help with something else?"}
```

### Validation errors (400)

```json
{"message": ["This field is required."]}
{"detail": "message is required."}   // empty / whitespace-only message
```

### Statelessness contract

- No `session_id` in the request or response.
- A fresh `ChatSession` is created server-side per request, tagged
  with `metadata={"channel": "manager_test"}`. These sessions
  accumulate over time; if dashboards or audits surface them, filter
  by `metadata.channel`.

---

## Limitations / known gaps

1. **No multi-turn context.** Each request runs in its own session, so
   a manager can't have a back-and-forth conversation in the tester.
   Acceptable for v1 voice/tone testing; the recommended next session
   notes this as a candidate.
2. **Manager-test sessions are not auto-cleaned.** They live in the
   `ChatSession` table forever (filterable by
   `metadata.channel == "manager_test"`). A periodic cleanup task is
   future work if the table grows.
3. **No vehicle cards in the manager UI.** Intentional per the spec —
   this is a voice-and-tone tester. The manager's `Customer demo`
   page covers the full customer-side view including cards.
4. **Hits the live LLM.** Each Send round-trips Ollama. If Ollama is
   down, the chat engine returns its existing fallback prose
   ("I want to make sure I get this right…"), which is the same
   behavior real customers see — that's correct, not a bug.
5. **No transcript export.** The local in-page transcript is kept in
   React state only; reload resets it.
6. **No rate limiting.** A manager could hammer the endpoint and
   create unbounded `ChatSession` rows. Acceptable for v1; revisit
   if the tester gets external exposure.

---

## Recommended next session (SESSION_011)

Three plausible directions, in order of payoff:

1. **Link salesperson seed to `Salesperson` model.** Still the most
   user-visible loose end in the onboarding loop — on save, if
   `salesperson_name` is set and no matching `Salesperson` exists,
   create one with the seed values. Same scope as the option-1 from
   SESSION_009's recommended-next list, deferred again because
   SESSION_010 was a smaller direct ask.
2. **Make manager chat conversation-aware.** Add an optional
   `session_id` to the request/response so the manager can carry
   context across multiple turns. Keeps statelessness as the default;
   conversation continuity becomes opt-in.
3. **Banned-phrase audit panel.** Surface
   `ChatMessage.metadata.banned_phrase_hits` (introduced in
   SESSION_009) in the existing audit dashboard so the manager can
   see which banned phrases the LLM keeps generating across both
   customer-facing AND manager-test traffic, and tune the list.
4. **Context-kit drift cleanup.** Bump `docs/PROJECT_PIPELINE.md`
   frontmatter `test_baseline: 253 → 1180`, refresh the *9 scrubs*
   mention in `docs/FREEDOM_FORD_BEHAVIOR_LAYER.md` to *17 scrubs*,
   backfill SESSION_004–007 handoffs (or renumber the gap), and
   decide the `context/` vs `docs/` parallel-anchor question.

Recommend **option 1** if the dealership-pilot workflow is the next
real-world driver.

---

## Hotfix appendix (2026-05-02)

After SESSION_010 shipped, the user reported a broken-feeling manager
reply when changing onboarding tone to *"Firm"* and prompting *"I want
a truck under 30k"*:

> *"Wanting a truck under $30k means you're looking at some great
> options. Let me show you some trucks that fit your budget. Here are
> a few options: Which one of these trucks catches your eye?"*

The reply implied vehicle cards were rendered, but the manager-chat
endpoint never returns cards. Two-layer fix:

### 1. Pre-LLM hint — `MANAGER_TEST_HINT`

New module `backend/dealer_ai/services/manager_chat_response.py`. The
chat engine reads `session.metadata["channel"]` and, when set to
`manager_test`:

- **Skips the inventory / budget / cash-mode system blocks entirely.**
  Without this, the LLM sees the AVAILABLE INVENTORY block and
  produces phrases like *"the cards above have the details"* — the
  inventory block was actively reinforcing the broken behavior.
- **Adds the `MANAGER_TEST_HINT` system message** explicitly listing
  the forbidden phrasings (*"Here are a few options"*, *"Let me show
  you"*, *"Let's take a look"*, *"Take a look at some"*, *"These
  trucks/cars/SUVs"*, *"Which one catches your eye"*, *"options
  below"*, *"check out these"*) and instructing the LLM to speak as
  if no inventory list is visible.

Customer-facing chat (`/dealer-ai-demo`, `/api/dealer-ai/chat/...`)
is unaffected — the hint is gated on the channel metadata which only
the manager-chat view sets.

### 2. Post-LLM scrub — `scrub_card_implying_phrases`

Pure-function safety net invoked in `views.manager_chat` after the
engine returns. Strips sentences that match any card-implying pattern.
If every sentence strips, returns a safe fallback:

> *"Under that budget I'd start by narrowing what matters most — 4WD,
> crew cab, towing, or lowest miles — so the conversation focuses
> before quoting specific inventory. What's the priority for this
> customer?"*

### Live before / after

**Before:** the user's reported reply (above).

**After (no profile saved):**
> *"Most trucks are above $30,000. What's your budget for down payment
> and financing?"*

**After (with onboarding tone = "Firm"):**
> *"Let's explore some options. We have a few models available in that
> price range. One option is the Chevrolet Colorado LT, which starts
> at around $25,000 and offers a good balance of features and fuel
> efficiency. Another option is the Ford Ranger XL, starting at about
> $24,000, with a strong engine and decent towing capacity. What's most
> important to you: payload capacity, towing capacity, or something
> else?"*

Both end with a focused next-step question and avoid every reported
card-implying phrasing.

### Tests added (6)

In `tests/test_manager_chat.py`:

- `ManagerChatNoCardImplicationTests.test_user_reported_bad_reply_is_repaired`
  — replays the exact bad reply from the issue through `MockLLMProvider`
  and asserts every reported forbidden phrasing is stripped.
- `ManagerChatNoCardImplicationTests.test_safe_fallback_when_every_sentence_strips`
  — pathological case: every sentence card-implying.
- `ManagerChatNoCardImplicationTests.test_clean_reply_passes_through_unmodified`
  — no false positives on coaching prose.
- `ManagerChatNoCardImplicationTests.test_hint_reaches_llm_call`
  — `MockLLMProvider` introspection: chat-reply call's system messages
  contain the `MANAGER TEST MODE` marker.
- `CustomerChatNotAffectedByManagerHintTests.test_send_message_does_not_inject_manager_hint`
  — regular chat path has NO `MANAGER TEST MODE` marker.
- `CustomerChatNotAffectedByManagerHintTests.test_send_message_reply_is_not_card_scrubbed`
  — customer-facing replies keep card-implying phrasing (cards are
  there).

### File changes

```
backend/dealer_ai/
  services/chat_engine.py                    (+18 -7) channel-aware skip
  services/manager_chat_response.py          (new, ~140 lines)
  views.py                                   (+11 -1) view-level scrub
  tests/test_manager_chat.py                 (+~110 lines, 6 new tests)
docs/handoffs/SESSION_010_manager_chat_tester.md  (this appendix)
```

### Verification

```bash
cd backend && source .venv/bin/activate
python manage.py test dealer_ai
# Ran 1186 tests in 2.582s — OK (skipped=1)
```

New baseline: **1186 pass, 1 skipped, 0 failed** (was 1180; +6 new).

Live curl against the running dev backend confirmed both the
no-profile and `sales_tone="Firm"` scenarios produce coaching prose
without card-implying language.

Frontend not touched.
