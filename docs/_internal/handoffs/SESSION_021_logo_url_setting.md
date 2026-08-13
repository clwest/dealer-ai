---
date: 2026-05-02
title: SESSION_021 — multi-tenant logo upload via OnboardingProfile.logo_url
type: implementation-summary
test_baseline: 1214
---

# Session handoff — multi-tenant logo upload

SESSION_020 surfaced the manual logo file-drop as the single
biggest remaining developer-only step in the second-dealer
onboarding flow — the Dealer Kit Status card called it out
explicitly with `(static — swap via config)`. SESSION_021
collapses that step. A new `OnboardingProfile.logo_url` field
makes the dealer logo configurable directly from
`/dealer-ai-onboarding`, and every brand surface in the OS
shell + public embed now resolves
`profile.logo_url || DEFAULT_DEALER.logoPath` via the existing
`useBrand()` hook.

The kit's static asset under `frontend/public/branding/`
remains the documented fallback for fresh installations and
for dealers without a hosted URL. **Net effect**: a manager
can stand up a second dealer's brand identity end-to-end from
Setup without any developer involvement.

Zero chat behavior changes. No CRM/DMS integration. No
multi-tenant routing. `PRODUCT` identity untouched. Honored
every guardrail in the SESSION_021 spec.

Use this snapshot to pick up at SESSION_022.

---

## What shipped

### 1. Backend — `OnboardingProfile.logo_url`

`backend/dealer_ai/models.py`. New field on
`DealerOnboardingProfile`:

```python
logo_url = models.CharField(max_length=512, blank=True, default="")
```

`CharField` rather than `URLField` so the form can save
partial drafts without strict URL validation; the frontend
`<input type="url">` provides browser-side hint validation
and the consumer's `<img onError>` handles bad URLs at render
time.

Wired through the API:

- `backend/dealer_ai/serializers.py` — added `logo_url` to
  `ONBOARDING_DEFAULTS` (default `""`) and to
  `DealerOnboardingProfileSerializer.Meta.fields`.
- `backend/dealer_ai/migrations/0005_dealeronboardingprofile_logo_url.py`
  — auto-generated, applied to the dev DB during
  verification.

### 2. Backend tests

`backend/dealer_ai/tests/test_onboarding_profile.py` — new
`OnboardingLogoUrlTests` class with four cases:

- `test_default_logo_url_is_empty_string` — fresh GET returns
  `logo_url: ""` and the field is present in the payload.
- `test_put_saves_logo_url` — round-trip persistence.
- `test_get_after_save_returns_logo_url` — the saved URL
  comes back on subsequent reads.
- `test_clearing_logo_url_persists_empty` — saving the value
  back to `""` actually persists empty (so the frontend's
  "clear to revert to fallback" path works at the API
  boundary).

Backend baseline: **1214 / 1** (was 1210/1; +4 new tests, no
regressions).

### 3. Frontend — brand hook + types

`frontend/src/lib/api.ts`:

```ts
export interface OnboardingProfilePayload {
  …
  logo_url: string;
}
```

`frontend/src/lib/brand.ts`:

- Added `Brand.logoUrl` — always a non-empty string,
  resolves as `profile.logo_url?.trim() ||
  DEFAULT_DEALER.logoPath`.
- Added `Brand.logoFromProfile` — `true` iff the profile
  supplied a non-empty value. Currently consumed only by the
  Setup status card to render the source label
  ("from profile" vs "static default").

### 4. Frontend — brand surfaces

Both surfaces now read `brand.logoUrl` instead of a
module-level `LOGO_SRC` constant. Both reset their image-
error flag via `useEffect([brand.logoUrl])` so a Setup edit
doesn't leave the surface stuck on the text/initials
fallback after a previous bad URL errored out.

- `frontend/src/App.tsx` — `BrandHeader`'s `<img>` (used by
  the desktop sidebar and the mobile drawer). Removed the
  unused `DEFAULT_DEALER` import — `useBrand()` is the only
  consumer of dealer-side identity now.
- `frontend/src/pages/EmbedAssistantPage.tsx` — `BrandMark`'s
  `<img>` for the public embed brand bar.

### 5. Setup — Logo URL input

`frontend/src/pages/DealerOnboardingPage.tsx`:

- Added `logoUrl: string` to the page's
  `DealershipProfile` shape, `EMPTY_STATE`, `fromApi()`,
  and `toApi()` round-trip.
- New `<Field label="Logo URL">` in the Dealership profile
  section with placeholder `https://cdn.example.com/dealer-
  logo.svg` and helper text:

  > Paste a hosted logo URL. If blank, the default dealer
  > logo is used.

- `<Field>` gained a `helperText?: string` prop — small
  subtext rendered beneath the input. Used here and
  available to any future field that needs the same hint
  pattern.
- Dealer Kit Status card's **Logo** row now reflects the
  resolved URL with a source label:
  - profile-supplied value → `(from profile)`
  - empty profile field → `(static default)`

The card mirrors form state, not saved state — so the
manager types a URL into the field and sees the source label
flip immediately, before clicking Save.

### 6. Docs — `DEALER_DUPLICATION_GUIDE.md`

- **"What can be changed in Setup today"** — added a Logo
  URL row that explicitly notes the
  `DEFAULT_DEALER.logoPath` fallback.
- **"Logo asset"** subsection retitled to
  *"Logo asset (fallback only — SESSION_021 collapsed
  this)"*. Lays out the new "preferred" path (paste a URL
  in Setup) above the legacy developer-only path.
- **Phase 1** retitled *"Static fallback (developer,
  optional, ~5 min)"* — was *"Static brand (developer,
  ~30 min)"*. Most second-dealer onboardings can now skip
  Phase 1 entirely.
- **Phase 2** mentions Logo URL alongside the other
  Dealership profile fields.
- **Printable checklist** — Setup form is now item #1; the
  static-fallback steps moved to "Optional (developer)".

### 7. `Field` helper text prop

`frontend/src/pages/DealerOnboardingPage.tsx` — `Field`
accepts an optional `helperText` rendered as a small muted
subtext beneath the input. Local to the Setup page; not
exported. Used by the Logo URL field to surface the
"blank → fallback" rule inline.

---

## Files changed

```
backend/dealer_ai/models.py                                          + logo_url CharField
backend/dealer_ai/serializers.py                                     + logo_url in defaults + Meta.fields
backend/dealer_ai/migrations/0005_dealeronboardingprofile_logo_url.py  NEW (auto-generated)
backend/dealer_ai/tests/test_onboarding_profile.py                   + OnboardingLogoUrlTests (4 tests)
frontend/src/lib/api.ts                                              + logo_url on OnboardingProfilePayload
frontend/src/lib/brand.ts                                            + Brand.logoUrl + Brand.logoFromProfile
frontend/src/App.tsx                                                 BrandHeader uses brand.logoUrl
frontend/src/pages/EmbedAssistantPage.tsx                            BrandMark uses brand.logoUrl
frontend/src/pages/DealerOnboardingPage.tsx                          + Logo URL Field + status-card source label
docs/DEALER_DUPLICATION_GUIDE.md                                     SESSION_021 collapse documented
docs/handoffs/SESSION_021_logo_url_setting.md                        NEW (this file)
00-START-NEXT-SESSION.md                                             closes SESSION_021, opens SESSION_022
```

---

## Verification

| Step | Result |
| --- | --- |
| Migration `0005_dealeronboardingprofile_logo_url` applied to dev DB | ✓ |
| `python manage.py test dealer_ai` | ✓ **1214 / 1** (baseline 1210/1 + 4 new tests, no regressions) |
| `npx tsc --noEmit` | ✓ 0 errors |
| `npx vite build` | ✓ 1.07s · 1717 modules · 48.62 kB CSS · 436.98 kB JS (gzip 121.98 kB) |
| Setup loads with new Logo URL field + helper copy | ✓ |
| Status card Logo row reads `(static default)` when field empty | ✓ |
| Type a URL → status card swaps to `(from profile)` live (no save needed) | ✓ |
| Save with `http://localhost:5173/branding/sams-freedom-ford-logo.jpg` → Overview sidebar `<img src>` matches the saved URL, `naturalWidth=586`, `complete=true` | ✓ |
| Embed `<img src>` matches the saved URL after the same save | ✓ |
| Clear field + Save → sidebar `<img src>` reverts to `/branding/sams-freedom-ford-logo.jpg` (`DEFAULT_DEALER.logoPath` fallback) | ✓ |
| Bad URL handling — saved a Wikimedia URL that 4xx'd in this environment | `BrandTextFallback` rendered cleanly; layout intact |
| Console (every surface) | ✓ 0 errors, 0 warnings |

Screenshots saved locally (gitignored under `/*.png`):
`session_021_setup_initial.png`,
`session_021_status_with_url.png`,
`session_021_overview_with_url_logo_v2.png`.

---

## Logo resolution chain

```
Setup form input (DealerOnboardingPage)
        │  PUT /onboarding/profile/
        ▼
OnboardingProfile.logo_url      (single source of truth)
        │  GET /onboarding/profile/  via fetchOnboardingProfile()
        ▼
brandFromProfile(profile)
   ├─ profile.logo_url non-empty  → brand.logoUrl = profile.logo_url
   │                                brand.logoFromProfile = true
   └─ profile.logo_url empty/null → brand.logoUrl = DEFAULT_DEALER.logoPath
                                    brand.logoFromProfile = false
        │
        ▼
useBrand() returns Brand
        │
        ▼
Sidebar BrandHeader  +  Embed BrandMark  +  Setup Dealer Kit Status row
        │
        └─ <img src={brand.logoUrl} onError={ → text/initials fallback }>
```

---

## Known limitations

- **No multipart upload yet.** v1 is a URL paste — works for
  any hosted asset but doesn't handle "I have a PNG on my
  desktop." A later session adds a real upload control +
  object storage; the `logo_url` shape supports either.
- **No URL validation server-side.** A malformed string
  saves successfully; the consumer's `<img onError>` catches
  it at render time and renders the text fallback.
  Acceptable for v1; a `URLField` migration is a one-line
  escalation.
- **Cross-origin URLs may fail in some host environments.**
  During verification a `upload.wikimedia.org` URL hit a
  CORS / referrer-policy block in this environment; the
  frontend correctly fell through to the text fallback.
  Real-world dealer logos hosted on permissive CDNs work;
  same-origin hosting always works.
- **No live broadcast across already-mounted surfaces.**
  Save in Setup → navigate to Overview → fresh fetch picks
  up the new URL. The OS shell rendered behind the Setup
  form does not update its sidebar logo until the user
  navigates. Same SESSION_018 contract; would require a
  `BrandContext` + revalidation broadcast to change.
- **Status pill still hard-coded to "Single-dealer
  configuration".** No change this session; tracked since
  SESSION_020.
- **Image cache.** The browser caches by URL. If a dealer
  overwrites the file at the same URL upstream, a hard
  refresh is needed. Not a kit problem.
- **`AssistantChat` default `welcomeTitle`** still mentions
  `"Hi — I'm your dealership's sales assistant."` (brand-
  neutral). Both call sites override the prop. Per
  guardrail, the shared component itself was not touched.
- **`/dealer-ai-demo` legacy route** still mounted from
  prior sessions, untouched.
- **Historical handoffs left intact.** Per the
  SESSION_019 reframe rule.

---

## Recommended next session

**SESSION_022 — Leads pipeline page (turn the stub into
real).**

This is the same recommendation that's been on the board
since SESSION_018, deferred four times now (in favor of the
platform reframe, the duplication flow, and the logo upload).
Each of those was correctly higher-priority at the time;
SESSION_021 has finished the brand-identity loop, so the
deepest unfilled value gap in the OS is once again the Leads
pipeline.

`/dealer-ai-leads` is currently a SESSION_015-era stub: 10
most recent leads with a *"Preview · full view coming soon"*
badge and basic name / phone / email / urgency fields. The
full pipeline view was deferred. SESSION_022 turns it into
the real surface.

**Scope:**

- Per-lead detail (modal or side panel) showing:
  - Full conversation transcript (assistant + user turns).
  - `extracted_profile` rendering (budget, body style, model
    intent, urgency).
  - `interested_vehicles` list rendered with the existing
    `AssistantVehicleCard`.
  - `recommended_next_action` text from the lead payload.
  - Handoff status + `assigned_to` salesperson chip.
- Filtering on the list:
  - urgency (`immediate` / `this_week` / `this_month` /
    `researching`).
  - handoff state (`new` / `handed off`).
  - free-text search by name / email / phone (client-side
    over the loaded page, no new endpoint).
- Reuse the existing `fetchAdminLeads()` and
  `fetchLeadDetail()` helpers in `lib/api.ts`.
- Brand-aware copy via `useBrand()` where appropriate
  (handoff narratives, dealer name in detail headers).

**Strict guardrails:**

- ❌ No new backend endpoints.
- ❌ No chat behavior changes.
- ❌ No edits to `AssistantChat`, `EmbedAssistantPage`, the
  inventory snapshot, or `/dealer-ai-demo`.
- ❌ No edits to `DEFAULT_DEALER` / `PRODUCT` /
  `defaultDealer.ts`.
- ❌ No write actions on the leads page in v1 (read-only —
  no reassign, no manual handoff toggle, no notes).
- ❌ No new API contracts beyond a TypeScript field-sync if a
  leads/session payload field is missing from the
  interface.

**Alternates** (still on the board):

- `SESSION_022b` — Multipart logo upload (extends
  SESSION_021's URL paste with real file uploads + object
  storage). Pick if a real second-dealer pilot is imminent
  and the URL paste turns out to be friction.
- `SESSION_022c` — Backend X-Frame-Options / CSP allowlist
  for cross-origin embedding (backend-touching). Pick when a
  third-party-embed deadline is real.
- `SESSION_022d` — Inventory data quality / image cleanup
  (deferred since SESSION_016).
- `SESSION_022e` — Live broadcast on Setup save
  (`BrandContext` so the topbar updates without
  navigation).

Default to **SESSION_022 (Leads pipeline)** unless a specific
alternate is dictated by the next demo audience.
