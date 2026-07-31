---
date: 2026-07-31
title: SESSION_032 — indie onboarding migration (DealerOnboardingProfile + form + useDealerProfile)
type: implementation-summary
test_baseline: 1281 → 1300 pass (+19), 1 skipped preserved, 0 regressions
persona: Copper Canyon Auto (Yuma, AZ)
picks_up_from: SESSION_031_pivot_phase4_5.md
migration: 0006_dealeronboardingprofile_bhph_configured_and_more
---

# Session handoff — indie onboarding migration

`DealerOnboardingProfile` now persists the 8 indie shape-of-business
fields exposed by `services/dealer_config.DealerProfile`. A real
dealer can customize their `dealer_type`, `bhph_enabled`,
`subprime_lenders`, `floor_plan_lender`, `warranty_offering`,
`credit_range_served`, and `makes_carried` via the `/dealer-ai-onboarding`
Setup UI, and every chat prompt / payment engine call reads the
persisted values through the resolver's new resolution order.

Frontend gets a new `useDealerProfile()` hook (alongside `useBrand()`)
that exposes the same fields to UI consumers with typed access +
Copper Canyon fallbacks.

**Backend baseline: 1281 → 1300 pass (+19), 1 skipped preserved,
0 regressions.** Frontend `tsc --noEmit` + `vite build` clean.

Pre-SESSION_032, the resolver returned hardcoded Copper Canyon
defaults for these 7 fields (dealer_type had an env override only).
Any real dealer running the kit couldn't customize their
shape-of-business without editing source; SESSION_032 closes that
gap.

---

## What shipped — backend

### 1. Migration + model — `0006_dealeronboardingprofile_bhph_configured_and_more`

Added 8 columns to `DealerOnboardingProfile` (existing 27 → 35):

| Column | Type | Default | Purpose |
|---|---|---|---|
| `dealer_type` | CharField(20, choices) | `""` | `"independent"` / `"franchise"` / `""` (unset — resolver falls back to env then default) |
| `bhph_enabled` | BooleanField | `True` | Buy-Here-Pay-Here financing toggle |
| `bhph_configured` | BooleanField | `False` | Sentinel — flips true on first Setup save, gates resolver's trust of `bhph_enabled` (see below) |
| `subprime_lenders` | TextField | `""` | Newline-separated list of subprime lender partner names |
| `floor_plan_lender` | CharField(128) | `""` | Single wholesale floor-plan lender |
| `warranty_offering` | CharField(255) | `""` | Human-readable retail warranty |
| `credit_range_served` | CharField(255) | `""` | Human-readable credit-tier range |
| `makes_carried` | TextField | `""` | Newline-separated list of makes (supersedes legacy CSV `main_brands`) |

Design decisions locked with the user:

- **List fields** = TextField, one entry per line. Matches the
  existing `approved_phrases` / `banned_phrases` convention. JSONField
  would have been cleaner typing but would have been the odd one out.
- **`makes_carried` vs legacy `main_brands`** = additive. New field
  takes priority in the resolver; legacy `main_brands` CSV parsed as
  fallback so existing dealer data isn't lost. `main_brands` can be
  dropped in a later cleanup.
- **`bhph_configured` sentinel** = required because `bhph_enabled`
  defaults to `True` (matching Copper Canyon). Without the sentinel,
  a fresh install couldn't distinguish "user explicitly enabled BHPH"
  from "user never touched the form and got the DB default". Sentinel
  flips true on first save through the Setup UI (any change to the
  BHPH toggle sets it).

### 2. Serializer — `DealerOnboardingProfileSerializer`

Added the 8 fields to the `fields` list + `ONBOARDING_DEFAULTS` dict.
Docstring updated from "27 fields" → "35 fields (27 pre-SESSION_032
+ 8 indie shape-of-business)". Invalid `dealer_type` values return
400 (Django REST framework's `ChoiceField` behavior).

### 3. Resolver — `dealer_config.get_dealer_profile()`

Rewrote the function to read `DealerOnboardingProfile.objects.first()`
lazily (single query, exception-swallowed for pre-migrate / DB-offline
paths). Resolution order per field:

- **`dealer_type`**: DB (non-empty) → env → default `"independent"`.
- **`primary_make`**: env → default (`None` for indie mixed-lot; no
  DB field — franchise config stays env-driven).
- **`bhph_enabled`**: DB when `bhph_configured=True` → default `True`.
- **`subprime_lenders`**: DB parsed newlines (non-empty) → Copper
  Canyon defaults tuple.
- **`floor_plan_lender`**, **`warranty_offering`**,
  **`credit_range_served`**: DB non-empty → default.
- **`makes_carried`**: DB `makes_carried` parsed newlines →
  legacy `main_brands` CSV → Copper Canyon defaults.

Added two module-private helpers:
- `_parse_lines(raw)` → `tuple[str, ...]` — newline splitter for
  the two list fields.
- `_parse_csv(raw)` → `tuple[str, ...]` — comma splitter for the
  legacy `main_brands` field.

Module docstring updated to document the per-field resolution order.

### 4. Tests

New coverage:

- `test_dealer_config.GetDealerProfileIndieFieldsResolution` (+15 tests):
  each field's resolution order, `bhph_configured` sentinel semantics,
  `makes_carried` new-field vs legacy-CSV precedence, blank-fallback
  behavior for every field.
- `test_onboarding_profile.OnboardingIndieFieldsTests` (+4 tests):
  default GET returns unset values, PUT saves all 8 fields, GET
  round-trips the values, invalid `dealer_type` rejected with 400.

Backend suite: **1281 → 1300 pass** (+19), 1 skipped preserved,
zero regressions. ~3.5s.

---

## What shipped — frontend

### 5. API contract — `OnboardingProfilePayload`

Added the 8 fields to the interface in `frontend/src/lib/api.ts`.
JSDoc comments document the "blank = unset → backend falls back"
semantics for each field. `dealer_type` is typed as a discriminated
union: `"" | "independent" | "franchise"`.

### 6. New hook — `useDealerProfile()`

Added to `frontend/src/lib/brand.ts` alongside `useBrand()`.
Deliberately separate hooks: `useBrand()` handles display strings
(chrome / name / logo), `useDealerProfile()` handles
shape-of-business (dealer type, BHPH, lenders, credit range, makes).
Rationale: display consumers shouldn't fetch business shape they
never use; business consumers get typed access without threading
through the display API.

Exports:
- `DealerType` = `"independent" | "franchise"`.
- `DealerProfile` interface with 8 fields plus `configured` flag +
  `loaded` sentinel.
- `dealerProfileFromPayload(payload)` — pure function; mirrors
  `brandFromProfile`. Copper Canyon indie defaults for any unset
  field.
- `useDealerProfile()` — React hook. Fetch-on-mount, cancellation-safe.
- Private `splitLines` / `splitCsv` parsers mirror the backend's
  `_parse_lines` / `_parse_csv`.

Both hooks share `fetchOnboardingProfile()` under the hood.

### 7. Onboarding form — "Business shape" section

Added a new section card to `DealerOnboardingPage.tsx` between the
existing Assistant Behavior and Pilot Checklist sections
(`SECTION_COUNT` bumped from 5 → 6). Controls:

- Dealer type: two-button radio (Independent / Franchise).
- BHPH: toggle button (same styling as the checklist toggle);
  clicking flips both `bhphEnabled` and `bhphConfigured=true` so
  the resolver starts trusting the user's choice.
- Floor plan lender: text field (default hint "NextGear, Kinetic
  Advantage, AFC").
- Warranty offering: text field with helper text noting AS-IS lots
  leave it blank.
- Credit range served: text field.
- Subprime lender panel: textarea, one per line.
- Makes carried: textarea, one per line, with helper text
  distinguishing mixed-make lots from franchise stores.

Progress completion heuristic updated: indie section counts as
"complete" when both `dealerType` is set AND `bhphConfigured=true`.

`state.indie` slot added to `OnboardingState`. `EMPTY_STATE`,
`fromApi`, `toApi`, and the destructuring / setter block all
extended. New `setIndie` setter uses the updater-function pattern
(mirrors `setChecklist`).

Icon: `Coins` from `lucide-react`.

Frontend `tsc --noEmit` clean; `vite build` clean (~496 kB / ~137 kB
gzip, up from ~490 kB / ~134 kB pre-SESSION_032 — the 6 kB delta is
the new form section + hook).

---

## Files touched

**Backend (6):**

- `backend/dealer_ai/models.py` — 8 new fields on `DealerOnboardingProfile`
- `backend/dealer_ai/migrations/0006_dealeronboardingprofile_bhph_configured_and_more.py` — new
- `backend/dealer_ai/serializers.py` — 8 fields added to `DealerOnboardingProfileSerializer` + `ONBOARDING_DEFAULTS`
- `backend/dealer_ai/services/dealer_config.py` — rewritten `get_dealer_profile()` + new `_parse_lines` / `_parse_csv` helpers + module docstring
- `backend/dealer_ai/tests/test_dealer_config.py` — +15 tests
- `backend/dealer_ai/tests/test_onboarding_profile.py` — +4 tests

**Frontend (3):**

- `frontend/src/lib/api.ts` — 8 fields on `OnboardingProfilePayload`
- `frontend/src/lib/brand.ts` — `useDealerProfile` hook + `dealerProfileFromPayload` pure fn + types
- `frontend/src/pages/DealerOnboardingPage.tsx` — `IndieBusiness` state slot + transformers + "Business shape" section render

Net: **9 files changed, +741/-28 lines.**

---

## Verify

```bash
# Backend
cd backend && python3 manage.py test dealer_ai
# Expect: 1300 pass, 1 skipped, 0 failed

# Migration applies cleanly on a fresh DB
python3 manage.py migrate --run-syncdb

# Frontend
cd frontend && npx tsc --noEmit && npx vite build
# Expect: 0 errors, ~496 kB bundle

# Smoke — resolver reads DB values
python3 manage.py shell -c "
from dealer_ai.models import DealerOnboardingProfile
from dealer_ai.services.dealer_config import get_dealer_profile
DealerOnboardingProfile.objects.all().delete()
DealerOnboardingProfile.objects.create(
    dealer_type='franchise',
    floor_plan_lender='AFC',
    makes_carried='Ford\nLincoln',
    bhph_enabled=False,
    bhph_configured=True,
)
p = get_dealer_profile()
print(p.dealer_type, p.floor_plan_lender, p.makes_carried, p.bhph_enabled)
# Expect: franchise AFC ('Ford', 'Lincoln') False
"

# Smoke — form persists the fields end-to-end
# 1. Start Django on :8001 and Vite on :5173.
# 2. Open /dealer-ai-onboarding.
# 3. Fill in Business shape section, click Save.
# 4. Reload the page — fields still populated.
# 5. Restart Django. Fields still populated (persisted to DB).
```

---

## Guardrails carried forward

Unchanged from SESSION_031. Full pivot remains shipped; all
franchise-config paths preserved.

- ❌ Do not delete the franchise config path.
- ❌ Do not reintroduce hardcoded "Sam Wampler" / "Freedom Ford" /
  Ford-model strings in default paths.
- ❌ Do not change chat behavior contracts. 1300-test baseline
  must stay green.
- ❌ Do not delete `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md` or
  `public/sams-freedom-ford-logo.jpg`.
- ❌ Do not do dep-major upgrades concurrent with feature work.
- ❌ Do not commit any real `OPENAI_API_KEY`.

---

## Recommended SESSION_033

Two natural follow-ons and one cleanup:

### Top candidate — surface indie profile fields in the assistant + admin UI

The backend resolver now reads the fields, but the customer-facing
chat + admin dashboards don't yet *display* dealer-type-specific UI.
Concrete opportunities:

- **Conditional admin panels.** Show a "BHPH portfolio" card on
  `/dealer-ai-admin` only when `useDealerProfile().bhphEnabled`.
- **Assistant persona-line** in the embed / homepage header showing
  the makes carried ("Yuma's used-car home for Toyota, Honda, Ford,
  Chevy, Nissan, and Kia") via `useDealerProfile().makesCarried`.
- **Ad-copy generator** — pass `useDealerProfile().warrantyOffering`
  and `creditRangeServed` into the ad-copy prompt so generated
  drafts reference real dealer terms instead of the assistant's
  generic phrasing.

### Also open

- **`react-router-dom` 6 → 7 migration.** Clears 2 security
  advisories. Small blast radius. Deferred throughout the pivot;
  now unblocked.
- **Indie counterpart of `seed_phase3_demo`.** Non-blocking dashboard
  demo enrichment.
- **Move `public/sams-freedom-ford-logo.jpg`** → `public/branding/franchise/`
  as explicit alternate-config asset.
- **Consolidate `main_brands` → `makes_carried`.** Data migration
  to copy CSV values to the new field, deprecate the legacy column.
  Depends on being confident no external consumers read `main_brands`
  from the API.

### Cosmetic tech-debt still open

- Adopt-generated titles in `docs/PROJECT_WHAT_IT_IS.md` and
  `docs/BUILD_PLAN.md` still say `# Freedom Ford — …` because
  `context-kit adopt` derives project name from git working
  directory. Full fix requires either a git-repo rename or a
  `--project-name` flag in adopt.
- `bhph_configured` sentinel field is a UX hack. Cleaner design
  might use a nullable BooleanField, but that requires custom
  serializer / form handling and Django's ORM support for
  nullable bools is awkward. Current design works and is testable.

---

## Operational state after SESSION_032

- **Backend (local):** Django on `:8001`. Package `backend/dealer_kit/`.
  Migration `0006` applied. LLM = OpenAI `gpt-5-mini`.
- **Backend (prod):** `vehicle-match-api.onrender.com` — **NOT
  active**. `render.yaml` still points at the correct paths from
  SESSION_031 Phase 4.
- **Frontend (local):** Vite on `:5173`. `/dealer-ai-onboarding`
  now has 6 sections (was 5). `useBrand()` unchanged; new
  `useDealerProfile()` hook available for shape-of-business
  consumers.
- **Frontend (prod):** **NONE**.
- **Test baseline:** 1300 pass, 1 skipped, 0 fail (was 1281).
- **Env overrides still available for franchise config:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
  DB values override env for the fields that have DB storage —
  ``dealer_type`` prefers DB when non-empty, env when DB is blank.
