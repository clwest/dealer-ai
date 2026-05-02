---
date: 2026-05-02
title: SESSION_020 — dealer duplication flow
type: implementation-summary
test_baseline: 1210
---

# Session handoff — dealer duplication flow

SESSION_019 reframed the codebase from "Freedom Ford AI" into
the **Dealer AI Kit** with Sam Wampler's Freedom Ford McAlester
as Dealer #1. SESSION_020 makes that reframe operationally
demonstrable: an operator-facing duplication guide spells out
the no-fork path for adding Dealer #2, and a new
"Dealer Kit Status" card on the Setup page lets the manager
preview how their dealer-profile edits will land in the OS
chrome and the public embed before saving.

Zero behavior changes. No backend touched. No chat tuning, no
inventory logic edits, no `DEFAULT_DEALER` edits, no historical
docs rewritten. The kit's behavior was already brand-agnostic;
SESSION_020 makes that fact legible to the next operator who
sits down to onboard a second dealer.

Use this snapshot to pick up at SESSION_021.

---

## What shipped

### 1. `docs/DEALER_DUPLICATION_GUIDE.md` (new)

Operator-facing companion to `docs/PLATFORM_REFRAME.md`. ~270
lines. The reframe doc explains *why* the kit is multi-dealer
capable; the duplication guide explains *how* to actually
onboard a second dealer.

Sections, in order:

- **Mental model** — three-layer identity hierarchy (product /
  default dealer / active dealer) with a resolution-order
  diagram. References `useBrand()` and `defaultDealer.ts`.
- **What can be changed in Setup today** — every field that
  flows live into the OS chrome: dealership name, store
  location, main brands, sales phone, website, sales tone,
  pricing comfort, appointment preference, lead handoff
  style, dealership greeting, approved/banned phrases,
  escalation rule, payment disclaimer, salesperson profile,
  pilot checklist toggles.
- **What still requires code/config** — five named blockers,
  each with *where it lives*, *how to swap*, and *future
  path*: the logo asset, `DEFAULT_DEALER` fallback, demo
  inventory snapshot, embed host / CSP allowlist, repo
  directory name.
- **"Do not fork the repo" rule** — explicit do-not list and
  the one case where forking is actually correct (when the
  kit's *behavior* itself diverges, not when identity
  differs).
- **Recommended workflow — onboarding Dealer #2** — Phase 1
  (developer, ~30 min) through Phase 4 (demo). Step-by-step.
- **Onboarding checklist (printable)** — 13-item kickoff
  doc copy-pasteable into a Notion page or sprint doc.
- **Glossary** — Kit / Dealer / Active dealer / Default
  dealer / Product / Brand surface.
- **Related docs** — links into `PLATFORM_REFRAME.md`, the
  SESSION_019 handoff, the start-of-session walkthrough,
  `defaultDealer.ts`, `lib/brand.ts`.

### 2. Dealer Kit Status card (new)

Added in `frontend/src/pages/DealerOnboardingPage.tsx`. Sits
between the **Dealership profile** form section and the
**Manager preferences** section. Read-only summary using the
existing `SectionCard` primitive for visual consistency, with
slate-tinted `StatusRow` cells that read clearly as outputs
rather than editable fields.

Six rows, in a 2-column grid:

| Row | Source | Live-update? |
| --- | --- | --- |
| **Product** | `PRODUCT.productName` → "Dealer AI Kit" | static |
| **Active dealer** | form state `dealership.name`; fallback to `DEFAULT_DEALER.dealershipName` when blank | live |
| **Location** | form state `dealership.location`; fallback to `DEFAULT_DEALER.storeLocation` | live |
| **Brand(s)** | form state `dealership.brands`; fallback to `DEFAULT_DEALER.brand` | live |
| **Logo** | `DEFAULT_DEALER.logoPath` rendered as inline `<code>` + "(static — swap via config)" hint | static |
| **Status** | green dot + "Single-dealer configuration" | static |

Footer hint: *"Changing these fields updates the visible
dealer identity across the OS and embed. Logo and feed
integrations are configured separately — see
`docs/DEALER_DUPLICATION_GUIDE.md` for the full workflow."*

**The Active dealer / Location / Brand(s) rows mirror form
state, not saved state.** This is deliberate: the manager
types their changes into the form fields above and sees the
card track in real time, so they can preview exactly how the
OS chrome will read before committing the save. The topbar
and the public embed continue to show the *saved* values
until Save is clicked — there's no live broadcast across
already-mounted surfaces.

A new tiny `<StatusRow label>` helper component lives next to
the new card; both are local to `DealerOnboardingPage.tsx`
since neither has obvious reuse outside the Setup surface
yet.

### 3. `frontend/src/config/defaultDealer.ts` — comments expanded

No code changes; comments only. Three additions:

- **Header note** mentions SESSION_020 alongside SESSION_019,
  points readers at `docs/DEALER_DUPLICATION_GUIDE.md` for
  the full operator workflow.
- **Explicit "do not fork" paragraph** spells out what fork
  buys you (every future bug fix duplicated, every
  chat-behavior improvement duplicated, every inventory
  pipeline change duplicated) and the one case fork is
  correct (kit *behavior* diverges).
- **Identity hierarchy callout** repeats the
  `OnboardingProfile → DEFAULT_DEALER → never inline` rule.
- **Step-by-step retargeting recipe** for swapping the kit
  at a new default dealer (drop logo, edit `DEFAULT_DEALER`,
  build, fill Setup).
- **`logoPath` JSDoc** now spells out the future-upload path
  — when `OnboardingProfile.logo_url` lands, `useBrand()`
  will prefer the uploaded URL and fall back to this static
  asset.

### 4. No CLI / scaffolder

The SESSION_020 spec permitted a doc-only checklist if useful
("Do NOT add CLI automation yet unless trivial"). The
printable checklist inside `DEALER_DUPLICATION_GUIDE.md`
satisfies that ask without a separate scripts directory. If a
real second dealer pilots the kit and the manual flow proves
too friction-heavy, a doc-driven `scripts/new-dealer.md`
template-walkthrough is the natural next step.

---

## Files changed

```
docs/DEALER_DUPLICATION_GUIDE.md                         NEW (operator workflow + checklist)
docs/handoffs/SESSION_020_dealer_duplication_flow.md     NEW (this file)
frontend/src/config/defaultDealer.ts                     comments expanded; no code changes
frontend/src/pages/DealerOnboardingPage.tsx              + DealerKitStatusCard + StatusRow helper
00-START-NEXT-SESSION.md                                 closes SESSION_020, opens SESSION_021
```

---

## Verification

| Step | Result |
| --- | --- |
| `npx tsc --noEmit` | ✓ 0 errors |
| `npx vite build` | ✓ 1.10s · 1717 modules · 48.54 kB CSS · 436.21 kB JS (gzip 121.72 kB) |
| `context-kit doctor` | ✓ 0 blocking, 5 pre-existing warnings (missing optional anchor docs, unrelated to this session) |
| `context-kit orient --short` | ✓ resolves cleanly; latest handoff still SESSION_019 (correct — SESSION_020 not committed yet) |
| Playwright `/dealer-ai-onboarding` initial render | ✓ Card shows: Product **Dealer AI Kit**, Active dealer **Sam Wampler's Freedom Ford**, Location **McAlester**, Brand(s) **Ford (new) + multi-brand used**, Logo path with "(static — swap via config)" hint, "Single-dealer configuration" green-dot status. Footer hint with doc link visible. |
| Edit form to **Tulsa Chevrolet** / **Tulsa** / **Chevrolet (new) + multi-brand used** (no save) | ✓ Card mirrored each field as I typed; topbar still showed Sam Wampler's saved values (correct preview-before-save behavior) |
| Revert form to Sam Wampler's values + Save | ✓ Persisted; topbar continues to show `Sam Wampler's Freedom Ford · McAlester` |
| Navigate to `/dealer-ai-overview` after save | ✓ Topbar `Sam Wampler's Freedom Ford`, sidebar caption `Dealer AI Kit`, console 0/0 |
| Navigate to `/embed/assistant` after save | ✓ Brand bar `Sam Wampler's Freedom Ford Assistant`, welcome `Hi — I'm Sam Wampler's Freedom Ford's sales assistant.`, console 0/0 |
| Console (every surface) | ✓ 0 errors, 0 warnings |

Backend baseline unchanged — frontend + docs only. SESSION_011's
1210 / 1 baseline still holds.

Screenshots saved locally (gitignored under `/*.png`):

- `session_020_kit_status_initial.png` — initial render with
  Sam Wampler's values and the inline logo path.
- `session_020_kit_status_edited.png` — same card after
  typing "Tulsa Chevrolet" / "Tulsa" / "Chevrolet (new) +
  multi-brand used" into the form, demonstrating live mirror.

---

## Known limitations

- **Logo row is static text only.** No upload control yet. To
  swap the logo a developer still drops the file under
  `frontend/public/branding/` and edits
  `DEFAULT_DEALER.logoPath` in
  `frontend/src/config/defaultDealer.ts`. **This is the
  biggest gap the duplication guide and the status card both
  surface as today's blocker** — and it's the SESSION_021
  target.
- **Status pill is hard-coded to "Single-dealer
  configuration".** When per-dealer routing or a config
  registry lands, this should derive from the active runtime
  config.
- **Tagline is not visible in the status card.** It lives only
  in the sidebar footer (rendered from
  `DEFAULT_DEALER.tagline`). Adding it to the card felt
  redundant for SESSION_020 — the card is already six rows.
  If a tagline field is added to the profile in a future
  session, surface it here.
- **No backend touched.** Onboarding profile shape and
  persistence behavior unchanged. The "tiny backend sync"
  carve-out in the spec was not exercised — every value the
  card displays already exists in `OnboardingProfilePayload`
  or `defaultDealer.ts`.
- **Card does not yet warn about logo / brand mismatch.** A
  future polish could detect when the saved `dealership_name`
  no longer matches the logo path's slug and flag the
  inconsistency. Out of scope for the current pass.
- **No CLI scaffold.** Per the spec, satisfied by the
  printable checklist inside `DEALER_DUPLICATION_GUIDE.md`
  rather than a separate scripts directory.
- **No live broadcast across already-mounted surfaces.** Save
  in Setup → navigate any other route → fresh fetch picks up
  the new identity. The topbar visible behind the Setup form
  doesn't update until the user navigates. Acceptable per
  the SESSION_018 contract; would require a `BrandContext`
  or revalidation broadcast to change.
- **`/dealer-ai-demo` legacy route** still mounted from prior
  sessions, untouched.
- **Historical handoffs left intact.** Voice from the
  Freedom-Ford era preserved on purpose; rewriting history
  would be much larger and lower-value.

---

## Recommended next session

**SESSION_021 — Multi-tenant logo upload / `logo_url` setting.**

The Dealer Kit Status card and the Duplication Guide both
surface the manual logo file-drop as the single biggest
remaining developer-only step in the second-dealer onboarding
flow. SESSION_021 closes that gap.

**Scope:**

- Add `logo_url` (or equivalent — could be uploaded asset URL,
  could be a remote URL string) to the onboarding /
  dealership profile. Tiny backend touch:
  - new `OnboardingProfile.logo_url` field (CharField with
    `blank=True, default=""`)
  - serializer addition (one line)
  - migration (auto-generated)
- Frontend Setup gains a logo input — start with a simple URL
  field for v1; a real file upload via multipart can come
  later. The Dealer Kit Status card's **Logo** row updates
  to display the configured URL when present.
- `useBrand()` — add `logoUrl` to the `Brand` shape, sourcing
  from `profile.logo_url` first, falling back to
  `DEFAULT_DEALER.logoPath`.
- Brand surfaces (`App.tsx` `BrandHeader`, embed
  `BrandMark`) consume `brand.logoUrl` instead of the
  hard-coded `LOGO_SRC` constant. Keep the existing
  static asset as the fallback path.
- Update `docs/DEALER_DUPLICATION_GUIDE.md`:
  - Remove "logo asset is static" from "What still requires
    code/config".
  - Update the Phase 1 / Phase 2 workflow to reflect that
    logo is now a Setup field.

**Strict guardrails:**

- ❌ No chat behavior changes.
- ❌ No CRM/DMS integration.
- ❌ No full multi-tenant routing — the `logo_url` is per-
  store, not per-tenant. Single profile still.
- ❌ No edits to `AssistantChat`, `EmbedAssistantPage`'s
  chat behavior, `/dealer-ai-demo`, the inventory snapshot,
  or `PRODUCT` constants.
- ❌ No new top-level routes.
- ❌ Don't move the static logo file. The shipped Sam Wampler
  asset stays in `frontend/public/branding/` and remains the
  documented fallback in `DEFAULT_DEALER.logoPath`.

**Alternates** (still on the board from SESSION_019):

- `SESSION_021b` — Leads pipeline (now deferred three times;
  pick if the next demo audience is dealer-ops more than
  marketing).
- `SESSION_021c` — Backend X-Frame-Options / CSP allowlist
  for cross-origin embedding (backend-touching; pick when a
  third-party-embed deadline is real).

Default to **SESSION_021 (logo upload)** — it directly closes
the gap the new SESSION_020 guide and status card both surface
as the highest-friction operator-blocking task today.

After SESSION_021, the second-dealer onboarding flow is
fully self-serve: Setup field for name/location/brand/logo,
no developer file-drop required.
