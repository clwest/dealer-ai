---
date: 2026-05-02
title: SESSION_008 — persist onboarding config (singleton, one-store)
type: implementation-summary
test_baseline: 1121
---

# Session handoff — onboarding config persistence

Replaces local-state-only onboarding with a backend-persisted singleton
profile. One-store v0; the future entity split (DealerAssistant,
SalespersonAgent, etc.) sketched in
`docs/onboarding/ASSISTANT_AGENT_CREATION_ROADMAP.md` is **not** part of
this session — fields are named to match that target schema so a future
migration can split without renames.

Use this snapshot to pick up at SESSION_009.

---

## What shipped

### Backend

- **Model:** `DealerOnboardingProfile` (`backend/dealer_ai/models.py:204`).
  All 27 onboarding fields flat, snake_case, plus `created_at` /
  `updated_at`. Singleton enforced at the view layer (no `unique=True`
  constraint — keeps the migration cheap to revisit).
- **Migration:** `backend/dealer_ai/migrations/0004_dealeronboardingprofile.py`.
- **Serializer:** `DealerOnboardingProfileSerializer` + `ONBOARDING_DEFAULTS`
  in `backend/dealer_ai/serializers.py`. Defaults mirror the v0 frontend
  seed values (`Freedom Ford` name, `Ford (new) + multi-brand used` brands,
  the standard W.A.C. payment disclaimer).
- **View:** `onboarding_profile` (`backend/dealer_ai/views.py:806`),
  `@api_view(["GET", "PUT", "PATCH"])`. GET always returns 200 with either
  the saved row or the default shape (no 404 path). PUT/PATCH upsert the
  singleton; PATCH supports partial updates (used for toggling individual
  checklist booleans without re-sending the rest of the profile).
- **URL:** `path("onboarding/profile/", ...)` in `backend/dealer_ai/urls.py`,
  mounted at `/api/dealer-ai/onboarding/profile/`.
- **Admin:** `DealerOnboardingProfile` registered in `admin.py` for
  inspection / emergency edits.
- **Tests:** new file `backend/dealer_ai/tests/test_onboarding_profile.py` —
  10 tests covering: defaults shape on cold GET, default disclaimer copy,
  PUT for each section (dealership, manager, salesperson, assistant,
  checklist), PATCH partial-update on a single checklist toggle, full GET
  round-trip after save, and PUT-twice singleton-upsert.

### Frontend

- **API helpers:** appended `OnboardingProfilePayload` interface +
  `fetchOnboardingProfile` + `saveOnboardingProfile` to
  `frontend/src/lib/api.ts`. New `putJSON` helper added next to the
  existing `getJSON` / `postJSON` pair.
- **Page rewrite:** `frontend/src/pages/DealerOnboardingPage.tsx` now
  - loads the profile on mount (with a loading spinner state and an
    error retry button),
  - keeps the same camelCase, sectioned state shape internally for
    ergonomics,
  - maps to/from the snake_case API payload via two transformer
    functions (`fromApi` / `toApi`),
  - shows save status (`idle` / `saving` / `saved` / `error`) and
    surfaces backend errors next to the Save button,
  - preserves the existing UI design (six sections, `SectionCard` /
    `Field` / `SelectField` components, completion badge, demo link).
- **No new state library.** Plain `useState` + `useEffect` + `fetch`,
  matching the existing `src/lib/api.ts` patterns.

### Docs

- **`docs/onboarding/FREEDOM_FORD_ONBOARDING_PLAN.md`** — added a
  *Persistence (SESSION_008)* section naming the endpoint, the singleton
  constraint, and what's still deferred (live behavior wiring; full
  entity split). Frontmatter updated; bottom section now reflects the
  shipped persistence approach (no react-query).
- **`docs/FREEDOM_FORD_SESSION_START.md`** — baseline updated:
  test count `1111 → 1121`, onboarding row updated from "no persistence"
  to the new endpoint description.
- **`00-START-NEXT-SESSION.md`** — hand-written section replaced with
  SESSION_009 priorities.

---

## File changes

```
backend/
  dealer_ai/
    admin.py                                            (+10 -1)
    models.py                                           (+65 +0)
    serializers.py                                      (+85 +0)
    urls.py                                             (+6 +0)
    views.py                                            (+45 +0)
    migrations/0004_dealeronboardingprofile.py          (new)
    tests/test_onboarding_profile.py                    (new, 10 tests)
frontend/
  src/
    lib/api.ts                                          (+60 +0)
    pages/DealerOnboardingPage.tsx                      (rewritten,
                                                         same UI shell)
docs/
  FREEDOM_FORD_SESSION_START.md                         (baseline updated)
  onboarding/FREEDOM_FORD_ONBOARDING_PLAN.md            (persistence
                                                         section added)
  handoffs/SESSION_008_persist_onboarding_config.md     (this file)
00-START-NEXT-SESSION.md                                (next-task
                                                         updated to
                                                         SESSION_009)
```

No code changes outside `dealer_ai/` (backend) and the onboarding page
(frontend). No changes to chat engine, scrub stack, payment engine,
candidate classifier, or inventory selection.

---

## Verification

### Backend tests

```bash
cd backend && source .venv/bin/activate
python manage.py test dealer_ai
```

**Result:** `Ran 1121 tests in 2.540s — OK (skipped=1)`. New baseline:
**1121 pass, 1 skipped, 0 failed** (was 1111 + 10 new onboarding tests).

### Frontend typecheck + build

```bash
cd frontend
npx tsc --noEmit       # 0 errors
npx vite build         # built in 889ms; 339kB JS, 32kB CSS
```

### Smoke

The four canonical demo scenarios were not re-run — this session
**did not touch chat engine, scrub stack, prompt construction, or
state-layer logic**. The onboarding page is on a separate route
(`/dealer-ai-onboarding`) and its persistence is independent of the
chat path. The 1121-test suite includes all post-LLM safety, scrub,
state-layer, and demo-script suites; they remain green.

If you touch chat behavior in SESSION_009, re-run the live demo
scenarios in `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md` against a
running Ollama before claiming done.

---

## API shape reference

`GET /api/dealer-ai/onboarding/profile/` always returns 200. Body shape
(snake_case, flat):

```json
{
  "dealership_name": "Freedom Ford",
  "store_location": "",
  "main_brands": "Ford (new) + multi-brand used",
  "sales_phone": "",
  "website": "",
  "sales_tone": "",
  "pricing_comfort": "",
  "appointment_preference": "",
  "lead_handoff_style": "",
  "salesperson_name": "",
  "salesperson_role": "",
  "salesperson_phone": "",
  "salesperson_email": "",
  "salesperson_specialties": "",
  "salesperson_preferred_tone": "",
  "salesperson_intro": "",
  "dealership_greeting": "",
  "approved_phrases": "",
  "banned_phrases": "",
  "escalation_rule": "",
  "payment_disclaimer": "Payments shown are estimates. Final terms with approved credit (W.A.C.).",
  "inventory_connected": false,
  "finance_rules_reviewed": false,
  "salespeople_added": false,
  "demo_prompts_tested": false,
  "pilot_approved": false,
  "created_at": "...",   // present after first save
  "updated_at": "..."    // present after first save
}
```

`PUT` accepts the same shape (full save). `PATCH` accepts any subset.

---

## Limitations / known gaps

1. **No live AI wiring.** The `dealership_greeting`, `approved_phrases`,
   `banned_phrases`, `escalation_rule`, and `payment_disclaimer` fields
   are persisted but **not** consumed by the chat engine yet. Wiring them
   into `_build_system_message` (and into the post-LLM scrub stack for
   banned phrases) is a Phase-2 task documented in the onboarding plan.
2. **One-store only.** Multi-tenant boundaries land with the `Dealership`
   entity from the roadmap, not in this session.
3. **No auth.** Anyone who can hit the API can save the profile. RBAC
   lands with the broader auth pass.
4. **No optimistic concurrency.** Two managers saving simultaneously will
   last-write-win. Acceptable for v0; revisit when multi-user landed.
5. **Salesperson seed not linked to `Salesperson` model.** The onboarding
   seed captures one salesperson record as flat fields; it does **not**
   create a `Salesperson` row. The full team still lives at
   `/dealer-ai-admin/team`. Linking the seed to a real `Salesperson` row
   on save is a candidate for SESSION_009 if it proves needed.

---

## Recommended next session (SESSION_009)

Three plausible directions, in order of payoff:

1. **Wire onboarding fields into the chat engine.** The biggest user
   value sitting unused is `dealership_greeting` (could replace the
   hard-coded greeting in the chat init), `banned_phrases` (could feed a
   new post-LLM scrub stage), and `payment_disclaimer` (already
   referenced by the W.A.C. scrub but currently hard-coded). Touches
   `_build_system_message` and the scrub stack — read
   `docs/PROJECT_PIPELINE.md` and `docs/FREEDOM_FORD_BEHAVIOR_LAYER.md`
   first.
2. **Link salesperson seed to `Salesperson` model.** On save, if
   `salesperson_name` is set and no matching `Salesperson` exists, create
   one with the seed values. Avoids the manager re-entering the same
   data on `/dealer-ai-admin/team`.
3. **Address context-kit drift surfaced earlier.** Backfill thin
   SESSION_004–007 handoffs (or renumber), reconcile the test-count drift
   across `PIPELINE.md` frontmatter (`test_baseline: 253` → `1121`) and
   the `BEHAVIOR_LAYER.md` `9 scrubs` mention, and decide on the
   `context/` vs `docs/` parallel-anchor question. Lower payoff than 1
   or 2, but clears persistent friction.

Recommend **option 1** if the dealership-pilot conversation is the next
real-world driver — making the onboarding fields actually shape AI voice
is the user-visible payoff for the persistence work this session.
