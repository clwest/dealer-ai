---
date: 2026-05-02
title: SESSION_009 — onboarding config now shapes live chat behavior
type: implementation-summary
test_baseline: 1172
---

# Session handoff — onboarding config controls chat behavior

Connects the SESSION_008 persistence layer to the live chat engine.
Six fields now flow into chat output: greeting, sales tone, approved
phrases, banned phrases, payment disclaimer, escalation rule. One DB
load per chat turn, no schema changes, no new agent architecture.
Behavior with no profile saved is **identical** to the pre-SESSION_009
chat engine — explicit fallback tested.

Use this snapshot to pick up at SESSION_010.

---

## What shipped

### Backend

- **New module:** `backend/dealer_ai/services/onboarding_overrides.py`.
  Pure-ish helpers (only `load_overrides` touches the DB):
  - `OnboardingOverrides` (frozen dataclass; `is_empty` property)
  - `load_overrides()` — singleton lookup with empty fallback
  - `parse_phrase_list(text)` — multi-line text → deduped phrase list
  - `tone_directive(label)` — maps `consultative` / `direct` /
    `fast-paced` / `formal` / `friendly` / `casual` to a one-paragraph
    voice directive
  - `format_store_voice_block(overrides)` — builds the system-message
    block (returns "" when empty so caller skips injection)
  - `scrub_banned_phrases(reply, banned)` — sentence-strip,
    case-insensitive, returns `(cleaned, fired, hits)`
  - `reply_mentions_payment(reply)` — narrow detection for `$X/mo`,
    `monthly payment`, `finance`, `estimated payment`
  - `disclaimer_already_present(reply, disclaimer)` — full-string +
    W.A.C. / "approved credit" fingerprint dedup
  - `should_append_disclaimer(reply, cash_mode, disclaimer)` —
    gate combining all rules
  - `append_disclaimer(reply, disclaimer)` — clean separator + trim

- **Wired into `chat_engine.py`** (`handle_user_message`):
  1. `load_overrides()` called once near the top of the LLM-bound
     branch, before the messages list is built.
  2. `format_store_voice_block(...)` injected into the system messages
     immediately after `SYSTEM_PROMPT` and before the budget /
     inventory / cash blocks.
  3. New banned-phrases scrub stage placed AFTER the existing content
     scrubs (`both_wording_scrubbed`) and BEFORE the model-followup
     length cap, so the cap fires on cleaned text.
  4. Disclaimer append placed AFTER the length cap and AFTER the
     auto-set-current-vehicle step, just before message persistence.
     Audit metadata sets `disclaimer_appended: true` when fired.

- **Tests:** `backend/dealer_ai/tests/test_onboarding_overrides.py`,
  51 tests across:
  - `LoadOverridesTests` (3) — defaults / loaded / whitespace
  - `ParsePhraseListTests` (5) — empties / strips / dedup / quotes /
    no comma split
  - `ToneDirectiveTests` (4) — empty / consultative / fast-paced /
    unknown
  - `FormatStoreVoiceBlockTests` (8) — header, greeting, known/unknown
    tone, approved/banned, escalation, 10-phrase cap
  - `ScrubBannedPhrasesTests` (6) — no-op cases, sentence strip, case
    insensitivity, multi-hit, all-banned safe fallback
  - `ReplyMentionsPaymentTests` (5) — pattern detection
  - `DisclaimerAlreadyPresentTests` (4) — full + fingerprint dedup
  - `ShouldAppendDisclaimerTests` (5) — full gating matrix
  - `AppendDisclaimerTests` (3) — separator / trim / empty-reply
  - `StoreVoiceBlockIntegrationTests` (2) — `MockLLMProvider`
    introspection: no profile → no block; profile → block with all
    components
  - `BannedPhraseIntegrationTests` (1) — chat reply containing a
    banned phrase has the offending sentence stripped + audit
    metadata recorded
  - `DisclaimerIntegrationTests` (3) — append on payment reply, skip
    on already-present W.A.C., skip on no payment language
  - `FallbackBehaviorIntegrationTests` (2) — no profile = no
    metadata mutations; benign reply unchanged

### Frontend

- **`frontend/src/pages/DealerOnboardingPage.tsx`** —
  - Save bar gained a small subline:
    *"Saved settings shape the live sales assistant — voice, encouraged
    phrasing, banned phrases, and the payment disclaimer all flow into
    the chat engine on the next reply."*
  - The `Saved.` status now reads *"Saved. Live AI behavior updated."*
  - No layout change, no new pages, no new state library.

### Docs

- **`docs/onboarding/FREEDOM_FORD_ONBOARDING_PLAN.md`** — added a
  *Live AI wiring (SESSION_009)* section with a per-field behavior
  table, audit metadata reference, and a refreshed *Still deferred*
  list (salesperson-seed link, multi-store, auth, automatic lead
  creation, DealerAssistant entity split).
- **`docs/FREEDOM_FORD_SESSION_START.md`** — baseline updated:
  test count `1121 → 1172`, onboarding row updated to reference live
  AI wiring.
- **`00-START-NEXT-SESSION.md`** — hand-written section replaced
  with SESSION_010 priorities.

---

## File changes

```
backend/
  dealer_ai/
    services/
      chat_engine.py                                       (+~75 -1)
      onboarding_overrides.py                              (new, ~325 lines)
    tests/
      test_onboarding_overrides.py                         (new, 51 tests)
frontend/
  src/
    pages/DealerOnboardingPage.tsx                          (+13 -3)
docs/
  FREEDOM_FORD_SESSION_START.md                            (baseline updated)
  onboarding/FREEDOM_FORD_ONBOARDING_PLAN.md               (live AI section)
  handoffs/SESSION_009_onboarding_controls_chat_behavior.md (this file)
00-START-NEXT-SESSION.md                                   (next-task → SESSION_010)
```

No changes to `payment_engine.py`, `_classify_candidates`, inventory
selection, intent parser, demo seeders, or the seven other backend
test suites that pin behavior.

---

## Verification

### Backend

```bash
cd backend && source .venv/bin/activate
python manage.py test dealer_ai
# Ran 1172 tests in 2.711s — OK (skipped=1)
```

New baseline: **1172 pass, 1 skipped, 0 failed** (was 1121 + 51 new).
All pre-existing scrub / behavior / state-layer / demo-script suites
remain green.

### Frontend

```bash
cd frontend
npx tsc --noEmit       # 0 errors
npx vite build         # built in 914ms; 339kB JS, 32kB CSS
```

### Manual smoke

Not run by the agent — requires browser interaction. Recommended
sequence (per the SESSION_009 task spec):

1. Open `http://localhost:5173/dealer-ai-onboarding`.
2. Set a banned phrase (e.g., `guaranteed approval`) → Save.
3. Ask the chat (`http://localhost:5173/dealer-ai-demo`) something
   that might produce that phrase. Confirm the phrase doesn't appear.
4. Set sales tone (e.g., *"Direct + fast-paced"*) → Save.
5. Run one canonical demo prompt
   (`docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md`).
6. Confirm the reply still produces cards and reads as a salesperson
   (no behavior regression).

### Pinned demo scenarios

The four canonical demo scenarios were not re-run live against
Ollama. The 1172-test suite (including
`test_demo_polish_voice`, `test_demo_scenarios`, the full post-LLM
scrub suite, and the new SESSION_009 tests) covers the structural
guarantees. If the manual smoke surfaces any voice regression in
cash mode, model-followup, or budget flow, **stop and revert** —
SESSION_009 is intentionally additive and should not change demo
behavior when no profile is saved (the `FallbackBehaviorIntegrationTests`
prove that branch).

---

## API / metadata reference

### System-message block (when overrides are saved)

```
DEALER VOICE OVERRIDES (apply on top of the base style rules above):
- Store greeting (use as a tone hint, do NOT repeat verbatim every reply): "Welcome to Dealer OS."
- Voice: warm and consultative. Help the customer think through ...
- Encouraged phrasing (use naturally when the moment fits — do NOT phrase-stuff): "Want a closer look?"; "Happy to help"
- Phrasings the dealership has explicitly disallowed — do not use any of these: "guaranteed approval"
- Soft-handoff rule (use this as guidance for when to suggest a human follow-up): "Hand off when finance terms come up."
```

The block is omitted entirely when `OnboardingOverrides.is_empty` —
no profile, no extra system message, identical to pre-SESSION_009.

### Assistant metadata additions

| Key | Type | When set |
|---|---|---|
| `scrubs` includes `"banned_phrase"` | list | Banned-phrase scrub fired |
| `banned_phrase_hits` | list[str] | Banned-phrase scrub fired (matched phrases) |
| `flag` = `"banned_phrase_scrubbed"` | string | Banned-phrase was the only scrub |
| `flag` = `"multiple_scrubs_fired"` | string | Banned-phrase fired alongside another scrub |
| `disclaimer_appended` | bool (true) | Configured payment disclaimer was appended |

---

## Limitations / known gaps

1. **No salesperson-seed → `Salesperson` row link.** Saving the
   onboarding profile still does not create or update a `Salesperson`
   record. Same gap as SESSION_008.
2. **Banned-phrase match is substring-based.** A banned phrase like
   `cheap` would also strip sentences that say `cheaper` (substring
   contains it). Managers should prefer multi-word phrases.
3. **Disclaimer append uses simple regex detection.** A reply that
   only references payment in a fragmented way (e.g., the LLM splits
   `$475` and `/mo` across a hyphen-break) might escape detection.
   Acceptable for v0; the existing rate-language scrub catches most
   payment phrasing on the way in.
4. **Tone directive matching is substring-only.** `consultative` matches
   "Warm + consultative", but a tone like "consult-style" wouldn't.
   The fallback (verbatim free-form pass-through) keeps the behavior
   non-zero in that case.
5. **No live preview of how the AI will respond.** The frontend save
   bar simply states "Live AI behavior updated." after Save. A real
   preview ("ask a sample prompt with these settings") is a future
   feature.
6. **No automatic lead creation from `escalation_rule`.** The rule
   shapes the LLM's voice but does not trigger backend handoff /
   lead-creation workflows. The existing `/admin/lead/<id>/handoff/`
   workflow remains the source of truth.
7. **No multi-tenant boundaries, no auth, no RBAC.** Same as
   SESSION_008.

---

## Recommended next session (SESSION_010)

In order of payoff:

1. **Link salesperson seed to `Salesperson` model.** On save, if
   `salesperson_name` is set and no matching `Salesperson` row exists,
   create one (with slug derived from name, the seed phone/email/intro
   carried in). Avoids manager re-entering the same data on
   `/dealer-ai-admin/team`. Small migration possible if we want a FK
   from the onboarding profile to `Salesperson`.

2. **Address context-kit drift surfaced in part-2 review.** Bump
   `docs/PROJECT_PIPELINE.md` frontmatter `test_baseline: 253 → 1172`,
   refresh the *9 scrubs* mention in
   `docs/FREEDOM_FORD_BEHAVIOR_LAYER.md` to reflect the now-17-stage
   chain (16 pre-SESSION_009 + the new banned-phrase stage), backfill
   thin SESSION_004–007 handoffs (or renumber the gap), and decide on
   the `context/` vs `docs/` parallel-anchor question.

3. **Add a sample-reply preview panel.** Below the save bar, render
   one canonical demo prompt (`"I want a 4WD truck for $500/mo"`)
   against the saved settings using the existing chat API. Lets the
   manager see how their voice changes affect output before going
   live.

4. **Add a banned-phrase audit panel.** Surface `banned_phrase_hits`
   from `ChatMessage.metadata` in the existing audit dashboard so the
   manager can see which banned phrases the LLM keeps generating and
   tune the list (or the approved phrases) to reduce hits.

Recommend **option 1** if the dealership-pilot workflow is the next
real-world driver — closing the salesperson seed gap is the last
loose end in the onboarding loop.
