---
state: active
date: 2026-07-31
last_session_shipped: SESSION_032
next_session: SESSION_033
---

# Next session — SESSION_033 · surface indie profile in UI + open cleanups

> **Pivot status:** ✅ shipped end-to-end across SESSION_030
> (Phases 1–3), SESSION_031 (Phases 4–5), and SESSION_032
> (indie-onboarding migration). Copper Canyon Auto is the shipped
> default persona; franchise config preserved via env overrides;
> `DealerOnboardingProfile` now persists all 8 indie
> shape-of-business fields; `useDealerProfile()` hook exposes them
> to frontend consumers.

## What just shipped (SESSION_032)

The `DealerOnboardingProfile` indie-fields migration + form + hook.
See `docs/handoffs/SESSION_032_indie_onboarding_migration.md` for
full per-file detail.

### Backend (6 files, 4 subsystems)

1. **Migration `0006_dealeronboardingprofile_bhph_configured_and_more`** —
   8 new columns on `DealerOnboardingProfile`: `dealer_type`,
   `bhph_enabled`, `bhph_configured`, `subprime_lenders`,
   `floor_plan_lender`, `warranty_offering`, `credit_range_served`,
   `makes_carried`.
2. **Serializer + `ONBOARDING_DEFAULTS`** — 8 fields exposed via
   `DealerOnboardingProfileSerializer` + defaults. Invalid
   `dealer_type` values rejected 400.
3. **Resolver `dealer_config.get_dealer_profile()`** — rewritten to
   read `DealerOnboardingProfile.objects.first()` lazily, with
   per-field resolution order (DB → env where applicable → Copper
   Canyon default). New `_parse_lines` / `_parse_csv` helpers.
   Module docstring documents the order.
4. **Tests** — 15 new dealer_config tests + 4 new onboarding-profile
   tests. Backend baseline **1281 → 1300 pass** (+19), 1 skipped
   preserved, zero regressions.

### Frontend (3 files)

5. **`OnboardingProfilePayload`** in `frontend/src/lib/api.ts` —
   8 new fields with JSDoc-documented "blank = unset" semantics.
6. **`useDealerProfile()`** hook in `frontend/src/lib/brand.ts` —
   sibling of `useBrand()`. Returns typed `DealerProfile` with
   Copper Canyon fallbacks. Kept separate from `useBrand()` so
   display consumers don't fetch business shape they never use.
7. **"Business shape" section** on `/dealer-ai-onboarding` —
   dealer-type radio, BHPH toggle, floor-plan-lender / warranty /
   credit-range text fields, subprime-lender + makes-carried
   textareas. `SECTION_COUNT` bumped 5 → 6. tsc + vite build clean.

### Design decisions locked (per user sign-off before implementation)

- List fields stored as TextField, one entry per line (mirrors
  `approved_phrases` / `banned_phrases` convention).
- `makes_carried` added alongside legacy `main_brands`; resolver
  prefers new field, falls back to CSV parse of legacy for old
  profiles.
- Two separate hooks (`useBrand` + `useDealerProfile`) instead of
  one merged hook.
- `bhph_configured` sentinel gates whether resolver trusts the
  `bhph_enabled` toggle vs falling back to Copper Canyon default
  (True). Distinguishes "user explicitly toggled" from "migration
  default".

## Recommended SESSION_033 — surface indie profile in UI

Backend + form work is done; SESSION_033 is where the persisted
values actually shape user-facing UI (customer + admin).

### Top candidate — conditional UI + prompt threading

Concrete opportunities in priority order:

1. **Admin panel gating.** Show a "BHPH portfolio" card on
   `/dealer-ai-admin` only when
   `useDealerProfile().bhphEnabled === true`. Add a
   "Franchise config" indicator badge when
   `dealerType === "franchise"`.
2. **Ad-copy generator prompt.** Thread
   `useDealerProfile().warrantyOffering` and `creditRangeServed`
   into the ad-copy prompt so generated drafts reference real
   dealer terms instead of the assistant's generic phrasing.
   Test — invented-promotion scrub still fires for anything not
   grounded in these fields.
3. **Assistant persona line** in the public homepage / embed
   header — display makes carried ("Yuma's used-car home for
   Toyota, Honda, Ford, Chevy, Nissan, and Kia") from
   `useDealerProfile().makesCarried`.
4. **Backend prompt scaffolding.** Update the
   `INDIE_MODE_HINT` fragment to interpolate concrete
   `floor_plan_lender` / `warranty_offering` / `credit_range_served`
   into the system prompt when a real profile is configured.

### Also open (lower urgency)

- **`react-router-dom` 6 → 7 migration.** Clears 2 security
  advisories. Small blast radius. Standalone commit.
- **Indie counterpart of `seed_phase3_demo`.** Dashboard-data
  enrichment.
- **Move `public/sams-freedom-ford-logo.jpg`** → `public/branding/franchise/`.
- **Data migration** to copy `main_brands` → `makes_carried` and
  deprecate the CSV column (once we're confident no external
  consumers read `main_brands` from the API).

### Cosmetic tech-debt (deferred)

- Adopt-generated titles in `docs/PROJECT_WHAT_IT_IS.md` /
  `docs/BUILD_PLAN.md` still say `# Freedom Ford — …`. Full fix
  requires git-repo rename or `context-kit adopt --project-name`
  flag.
- `bhph_configured` sentinel field is a UX hack; cleaner design
  would use a nullable BooleanField, but Django's nullable-bool
  support is awkward. Current design works and is testable.

## NEXT TASK

Start SESSION_033 with the **admin panel gating + ad-copy prompt
threading** — smallest scoped wins that let a real dealer see their
saved indie profile influence the UI. Save the persona-line + full
prompt-scaffolding for a follow-up if time allows.

**Strict guardrails carried forward:**

- ❌ Do NOT delete the franchise config path.
- ❌ Do NOT reintroduce hardcoded "Sam Wampler" / "Freedom Ford" /
  Ford-model strings in default paths.
- ❌ Do NOT change chat behavior contracts. 1300-test baseline
  must stay green.
- ❌ Do NOT delete `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md` or
  `public/sams-freedom-ford-logo.jpg`.
- ❌ Do NOT do dep-major upgrades concurrent with feature work.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.

---

## Agent launch prompt for SESSION_033

Paste into Claude Code / Cursor / any AI coding agent as the
session opener.

```text
You are picking up SESSION_033 on the Dealer AI Kit. The
independent-dealer pivot shipped across SESSION_030 (backend +
seed + frontend tokens), SESSION_031 (Django rename + docs), and
SESSION_032 (DealerOnboardingProfile persistence for the 8 indie
shape-of-business fields + useDealerProfile hook + onboarding form
section). Copper Canyon Auto is the default; franchise config
preserved via env overrides.

Read first:
- context-kit orient
- 00-START-NEXT-SESSION.md
- docs/DEALER_KIT_SESSION_START.md
- docs/handoffs/SESSION_032_indie_onboarding_migration.md
- docs/research/INDEPENDENT_DEALER_PIVOT.md

Goal: surface the saved indie profile in the actual UI. Top
candidates in priority order (from the handoff):
1. Admin panel gating — show "BHPH portfolio" card only when
   useDealerProfile().bhphEnabled === true; add "Franchise
   config" badge when dealerType === "franchise".
2. Ad-copy generator prompt — thread warrantyOffering +
   creditRangeServed into the ad-copy prompt so generated drafts
   reference real dealer terms. Verify invented-promotion scrub
   still fires for anything not grounded in these fields.
3. Backend prompt scaffolding — update INDIE_MODE_HINT to
   interpolate concrete floor_plan_lender / warranty_offering /
   credit_range_served when a real profile is configured.

Local dev:
- LLM = OpenAI gpt-5-mini (API key in repo-root .env).
- Django on :8001, Vite on :5173.
- Backend baseline: python3 manage.py test dealer_ai → 1300
  pass, 1 skipped. Django project package = backend/dealer_kit/
  (SESSION_031 Phase 4).
- Frontend: 6-section onboarding form; use useDealerProfile()
  for shape-of-business, useBrand() for display strings.

Do NOT:
- Delete the franchise config path.
- Change chat behavior contracts. Keep 1300 baseline green.
- Do dep-major upgrades concurrent with feature work.
- Commit any real API keys.
```

---

## Operational state carried from SESSION_032

- **Backend (local):** Django on `:8001`. Package
  `backend/dealer_kit/`. Migration `0006` applied.
  LLM = OpenAI `gpt-5-mini` (repo-root `.env`).
- **Backend (prod):** `vehicle-match-api.onrender.com` — **NOT
  active**.
- **Frontend (local):** Vite on `:5173`. `/dealer-ai-onboarding`
  has 6 sections. `useBrand()` unchanged; `useDealerProfile()`
  available.
- **Frontend (prod):** **NONE**.
- **Test baseline:** 1300 pass, 1 skipped, 0 fail.
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
  DB values override env for the 8 indie fields.

## Anchors that win on conflict

If anything here disagrees with reality:

1. `docs/research/INDEPENDENT_DEALER_PIVOT.md` — pivot living plan.
2. `docs/handoffs/SESSION_032_indie_onboarding_migration.md` —
   most recent handoff.
3. `docs/handoffs/SESSION_031_pivot_phase4_5.md` — Phase 4/5.
4. `docs/handoffs/SESSION_030_independent_dealer_pivot.md` — Phases 1–3.
5. `git log --oneline -25` (what actually shipped).
6. `git show HEAD:<path>` (current source).

Narrative docs are claims. Code and handoffs are facts.
