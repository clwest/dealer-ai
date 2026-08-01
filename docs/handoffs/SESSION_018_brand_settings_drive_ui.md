---
date: 2026-05-02
title: SESSION_018 — brand settings drive UI
type: implementation-summary
test_baseline: 1210
---

# Session handoff — brand settings drive UI

SESSION_018 closes the loop between Setup and the rest of the OS.
Until this session every brand surface — sidebar, topbar, mobile
drawer, embed brand bar, embed footer disclaimer, Live Assistant
welcome / footer, Public Preview dialog — hard-coded
*"Sam's Dealer OS"* / *"McAlester"*. The Onboarding profile
already shipped `dealership_name` and `store_location` (used only
by the Overview's Assistant Status card). SESSION_018 lifts those
values into a small `useBrand()` hook and threads them through
every chrome surface, with hard fallbacks to the verified
Sam Wampler's Dealer OS McAlester identity.

Setup is no longer cosmetic — when a manager edits and saves the
dealership name or location, the next route mount picks it up
across the OS and the public embed.

No backend changes, no chat behavior changes, no inventory logic
touched, no logo-asset edits, no embed CSP work. Honored every
guardrail in the SESSION_018 spec.

Use this snapshot to pick up at SESSION_019.

---

## What shipped

### 1. `useBrand()` hook + `brandFromProfile()` helper

`frontend/src/lib/brand.ts` (new). Two exports:

- **`brandFromProfile(profile)`** — pure function. Takes an
  `OnboardingProfilePayload | null | undefined` and returns the
  derived brand strings (no React, easy to unit-test or call
  from a non-hook context later).
- **`useBrand()`** — React hook. Fetches the profile on mount
  via the existing `fetchOnboardingProfile()`, returns the
  derived strings plus a `loaded` boolean. Cancellation-safe
  (suppresses setState after unmount). Falls back to
  Sam Wampler's identity on fetch failure or empty fields.

The `Brand` shape returned to consumers:

| Field | Source | Used by |
| --- | --- | --- |
| `dealershipName` | `profile.dealership_name` or fallback | sidebar fallback, embed brand-mark `alt`, embed footer disclaimer, Live Assistant footer, Public Preview description |
| `storeLocation` | `profile.store_location` or fallback | sidebar fallback line 2, topbar location, drawer SheetTitle |
| `displayName` | `${name} ${location}` | sidebar logo `alt`, mobile drawer SheetTitle |
| `topbarName` | `dealershipName` (alias) | topbar bold name |
| `embedAssistantName` | `${name} Assistant` | embed brand-bar headline, Public Preview iframe `title` |
| `possessiveName` | `toPossessive(name)` | embed welcome ("I'm `<X>` sales assistant"), Live Assistant welcome |
| `tagline` | constant `"Sam Wampler Make It Happen"` | sidebar footer (italic muted) |
| `loaded` | `true` once fetch resolves (success or failure) | (currently unused; available if a consumer ever wants to suppress the fallback flash) |

**Decision: fetch-on-mount per-consumer, no global state.** The
spec explicitly permitted this. Each surface fires its own fetch
on its own route mount. In practice only two consumers live in a
given page session — the OS shell once (for sidebar / topbar /
drawer) and the embed once on its own route — so the
write-amplification cost is trivial. The big upside: navigating
to a new route after a Setup save is enough to pick up the new
values; no global cache to invalidate.

**Decision: possessive helper.** `toPossessive("Sam Wampler's
Dealer OS")` returns the same string with `'s` appended →
`"Sam Wampler's Dealer OS's"`. Reads correctly grammatically:
the outer possessive is the dealership's claim on the assistant;
the inner `'s` is part of the dealership's own name. The helper
short-circuits if the name already ends in `'s` (or smart-quote
`'s`) so we never produce `"Foo's's …"`.

### 2. `App.tsx` — sidebar / topbar / mobile drawer

Replaced the SESSION_017 module-level `STORE_NAME` /
`STORE_LOCATION` constants with a single `useBrand()` call at
the top of the component. The `Brand` is then prop-drilled to
`<DesktopSidebar />`, `<TopBar />`, `<BrandHeader />`, and
`<BrandTextFallback />`. Specific bindings:

- **Sidebar logo `<img alt>`** → `brand.displayName`
- **Sidebar text fallback** (when the image errors) → name +
  location lines
- **Sidebar footer** → was `Local · MVP`, now renders
  `brand.tagline` (italic, muted, small caps wording preserved
  via tracking-tight). The "Local · MVP" caption was developer
  scaffolding; the tagline is the real brand signature.
- **Mobile drawer SheetTitle** (`sr-only`) → `${brand.displayName}
  — Dealer OS`
- **Mobile drawer SheetDescription** (`sr-only`) → unchanged
  ("Primary navigation for the Dealer OS")
- **Topbar primary** → `brand.topbarName`
- **Topbar location chip** → `· ${brand.storeLocation}`

Logo asset path is **still hard-coded** at
`/branding/sams-freedom-ford-logo.jpg`. That's a brand-team
upload, not a derivable string — a future multi-tenant session
would handle dealership-specific logo upload as its own concern.

### 3. `EmbedAssistantPage.tsx`

Now consumes `useBrand()` at the top and propagates through the
brand bar, welcome line, and footer:

- **Brand-bar headline** → `brand.embedAssistantName` (e.g.
  *"Sam Wampler's Dealer OS Assistant"*)
- **AssistantChat `welcomeTitle`** prop → *"Hi — I'm
  ${brand.possessiveName} sales assistant."*
- **Footer disclaimer** → *"Estimates only. A
  ${brand.dealershipName} advisor confirms real numbers."*
- **Logo-fallback chip** when the image errors → derives a
  two-letter monogram from `brand.dealershipName`
  (`Sam Wampler's Dealer OS` → `SF`). Replaces the previous
  hard-coded `FF`.

The `AssistantChat` component itself was **not** touched per
the spec guardrail — only the props passed to it changed.

### 4. `LiveAssistantPage.tsx`

Imports `useBrand()`. Two visible bindings:

- AssistantChat `welcomeTitle` → *"Hi — I'm
  ${brand.possessiveName} sales assistant."* (same string the
  embed uses; both surfaces share the same shared chat under
  the hood, so the welcome is now consistent across both).
- Footer disclaimer → *"Estimates only. A
  ${brand.dealershipName} advisor confirms real numbers."*

The dealer-side header (`Find Your Next Vehicle` + trust row)
is intentionally unchanged — that copy is product-voice, not
dealer-identity-driven.

### 5. `PublicPreviewDialog.tsx`

Two strings now flow from the brand:

- **DialogDescription** → *"This is how the
  ${brand.dealershipName} assistant appears on your website."*
- **Iframe `title` attribute** →
  `${brand.embedAssistantName} preview`

The button label, embed-code snippet, and copy affordance are
unchanged.

### 6. No serializer / API contract change

Confirmed `OnboardingProfilePayload` already exposes
`dealership_name` and `store_location`. No edits to
`frontend/src/lib/api.ts`. The optional "tiny serializer
field-sync" carve-out in the SESSION_018 spec was not needed.

---

## How Setup values flow into the UI

```
DealerOnboardingPage  ──[PUT /onboarding/profile/]──▶  Backend
                                                          │
                                                       persisted
                                                          │
On any subsequent route mount of a brand-aware surface:   ▼
  App.tsx · EmbedAssistantPage · LiveAssistantPage · PublicPreviewDialog
                       │
                       ▼
                useBrand() ──▶ fetchOnboardingProfile()
                       │
                       ▼
            brandFromProfile(payload) → Brand
                       │
                       ▼
        Component renders the new strings
```

Save in Setup → navigate to any other surface → fresh
`useBrand()` fetch on mount → updated brand strings. No global
state machine, no broadcast, no cache invalidation. The
contract is "fresh route mount = fresh brand read".

---

## Verification

| Step | Result |
| --- | --- |
| `npx tsc --noEmit` | ✓ 0 errors |
| `npx vite build` | ✓ 1.04s · 1716 modules · 48.52 kB CSS · 433.32 kB JS (gzip 120.92 kB) |
| Initial `/onboarding/profile/` GET | `{ dealership_name: "Sam Wampler's Dealer OS", store_location: "McAlester, Oklahoma" }` |
| Topbar at first paint | `Sam Wampler's Dealer OS · McAlester, Oklahoma` ✓ |
| Sidebar tagline footer | `Sam Wampler Make It Happen` ✓ |
| Edit Setup — name unchanged, location → `McAlester` (drop the `, Oklahoma` suffix to verify the change actually flows), Save | ✓ |
| Re-read profile after save | `{ store_location: "McAlester" }` ✓ |
| Navigate to `/dealer-ai-overview` | Topbar updates to `Sam Wampler's Dealer OS · McAlester` ✓ |
| Navigate to `/embed/assistant` | Brand bar: `Sam Wampler's Dealer OS Assistant`. Welcome: `Hi — I'm Sam Wampler's Dealer OS's sales assistant.` Footer: `A Sam Wampler's Dealer OS advisor confirms real numbers.` ✓ |
| Open `Public Preview` dialog | Description: `This is how the Sam Wampler's Dealer OS assistant appears on your website.` Iframe inside dialog renders the brand-aware embed verbatim. ✓ |
| Console (every surface above) | 0 errors, 0 warnings ✓ |

Backend baseline unchanged — frontend-only session.
SESSION_011's 1210 pass / 1 skip baseline still holds.

Screenshots (gitignored under `/*.png`):
`session_018_shell_initial.png`,
`session_018_overview_after_save.png`,
`session_018_embed_after_save.png`,
`session_018_public_preview_after_save.png`.

---

## Files changed

```
frontend/src/lib/brand.ts                            NEW (useBrand hook + brandFromProfile)
frontend/src/App.tsx                                 sidebar/topbar/drawer consume useBrand; tagline replaces "Local · MVP"
frontend/src/pages/EmbedAssistantPage.tsx            brand bar/welcome/footer/fallback chip from brand
frontend/src/pages/LiveAssistantPage.tsx             welcome + footer from brand
frontend/src/components/PublicPreviewDialog.tsx      description + iframe title from brand
docs/handoffs/SESSION_018_brand_settings_drive_ui.md NEW (this file)
```

---

## Known limitations

- **No live broadcast across already-mounted surfaces.** Saving
  in Setup updates the persisted profile, but a tab where the
  topbar is currently rendered behind the Setup form won't
  update until the user navigates. Acceptable per the spec
  ("refresh / navigate is the contract"). A future session
  could add a tiny `BrandContext` + `revalidate()` to broadcast
  on save if "live update without navigation" becomes a
  requirement.
- **Logo asset is still hard-coded** at
  `/branding/sams-freedom-ford-logo.jpg`. A different dealer
  with this codebase would need the asset replaced manually.
  Multi-tenant logo upload is a separate session.
- **`document.title`** in `index.html` is still the static
  `Sam's Dealer OS McAlester — Dealer OS`. Cosmetic; only
  matters in the browser tab, and only when Setup hasn't been
  edited.
- **Tagline is a constant** in `lib/brand.ts`. Onboarding
  profile has no tagline field. If a `tagline` (or
  `dealership_tagline`) field is ever added to the profile,
  swap the constant for `profile?.tagline`.
- **Possessive helper handles common cases.** Names ending in
  lowercase `s` (e.g. `Hess's Auto`) get an `'s` appended,
  which is grammatically defensible. If a real dealer hits a
  weird edge, the rule lives in one place.
- **AssistantChat default `welcomeTitle` still mentions
  "Dealer OS".** Both call sites override the prop now, so
  the default never renders. Per spec guardrail, the shared
  component itself was not touched.
- **Fetch-per-consumer cost.** Each `useBrand()` mount fires
  its own GET. Two consumers per page session at most —
  trivial. If a future surface uses the hook many times in a
  single tree, batching becomes worth it; today, not a concern.
- **No backend changes.** Honored every guardrail. The
  X-Frame-Options / CSP allowlist needed for cross-origin
  embed (called out in SESSION_017) is still untouched.
- **`/dealer-ai-demo` legacy route** still mounted from prior
  sessions, untouched.

---

## Recommended next session

**SESSION_019 — Leads pipeline page (turn the stub into real).**

The Overview's "Today's leads → View all" link lands on
`/dealer-ai-leads`, which is a SESSION_015 stub: it lists the
10 most recent leads with a *"Preview · full view coming
soon"* badge and basic name / phone / email / urgency fields.
The full pipeline view — qualification stages, handoff trail,
salesperson assignment, conversation transcript drill-down —
was deferred. SESSION_019 turns that stub into a useful page.

**Scope:**

- Per-lead detail surface (modal or side panel) with:
  - Full conversation transcript (assistant + user turns).
  - `extracted_profile` rendering (budget, body style, model
    intent, urgency, etc. — fields the backend already
    captures on `ChatSession`).
  - `interested_vehicles` list with the same
    `AssistantVehicleCard` shape used elsewhere.
  - `recommended_next_action` text from the lead payload.
  - Handoff status + `assigned_to` salesperson chip.
- Filtering on the list:
  - urgency (`immediate` / `this_week` / `this_month` /
    `researching`)
  - handoff state (`new` / `handed off`)
  - free-text search by name / email / phone (client-side over
    the loaded page, no new endpoint)
- Reuse the existing `fetchAdminLeads()` and
  `fetchLeadDetail()` helpers in `lib/api.ts`. Both are
  already wired to live endpoints serving traffic.
- Brand-aware copy via `useBrand()` where appropriate
  (referring to the dealer in handoff narratives, etc.).

**Strict out-of-scope guardrails for SESSION_019:**

- ❌ No new backend endpoints.
- ❌ No chat behavior changes.
- ❌ No edits to `AssistantChat`, `EmbedAssistantPage`, the
  inventory snapshot, or the `/dealer-ai-demo` legacy route.
- ❌ No write actions on the leads page in v1 (read-only — no
  reassign, no manual handoff toggle, no notes). Adding write
  actions is a focused later session that touches backend.
- ❌ No new API contracts in `lib/api.ts` beyond a TypeScript
  field-sync if any leads/session payload field is missing
  from the existing interface.

**Alternate paths if Leads isn't the priority:**

- **SESSION_019b — Inventory data quality.** SESSION_016
  verification noted seed-image quality issues
  (placeholder-quality photos on backend-attached vehicles).
  A focused pass to refresh seed data, or to surface coverage
  metrics on the Inventory preview page header (e.g.
  *"148 vehicles · 122 with photos"*), would land visible
  quality. Pick this if the next demo audience cares more
  about vehicle browse than lead pipeline.
- **SESSION_019c — Backend embed CSP.** Required for actual
  cross-origin embedding (the dealer dropping the iframe
  into `samsfreedomford.com`). Touches Django settings and
  needs a backend-touching session. Pick this if a real
  third-party embed deadline is approaching.
- **SESSION_019d — Multi-tenant logo upload.** Onboarding
  profile gains a logo-image upload field; sidebar /
  embed BrandMark switch from the hard-coded path to the
  uploaded URL with the current asset as fallback. Pick
  this if the project is about to onboard a second dealer.

If none is decided, default to **SESSION_019 (Leads pipeline)**
— it's the highest-leverage frontend-only surface the OS still
hasn't earned, and it's the natural follow-on to the
"Today's leads" Overview card SESSION_015 introduced.
