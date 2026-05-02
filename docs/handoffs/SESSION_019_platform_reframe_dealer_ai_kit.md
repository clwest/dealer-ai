---
date: 2026-05-02
title: SESSION_019 — platform reframe (Dealer AI Kit)
type: implementation-summary
test_baseline: 1210
---

# Session handoff — platform reframe

SESSION_019 reframes the project's mental model. The codebase is
no longer *"Freedom Ford AI"* — it is the **Dealer AI Kit**, a
reusable AI sales assistant platform for franchise dealerships.
**Sam Wampler's Freedom Ford McAlester** remains Dealer #1 and
the default configuration shipped with the kit; future
dealerships are added as additional configurations **inside this
same repository**, not as forks or separate codebases.

Zero behavior changes. The reframe is identity / configuration /
copy / docs only. No chat, no API, no inventory, no scrubs, no
prompt strings, no migrations. The kit's behavior was already
brand-agnostic by design; SESSION_019 made that fact legible in
code.

Use this snapshot to pick up at SESSION_020.

---

## What shipped

### 1. New config module — `frontend/src/config/defaultDealer.ts`

Single source of truth for two distinct concepts:

- **`DEFAULT_DEALER: DealerConfig`** — the active dealer
  fallback when the onboarding profile is empty. Today
  Sam Wampler's Freedom Ford McAlester:
  - `dealershipName` — *"Sam Wampler's Freedom Ford"*
  - `storeLocation` — *"McAlester"*
  - `tagline` — *"Sam Wampler Make It Happen"*
  - `brand` — *"Ford"*
  - `logoPath` — `/branding/sams-freedom-ford-logo.jpg`
  - `primaryColorNote` — informational; OS already uses Ford-
    blue Tailwind tokens.
- **`PRODUCT: ProductConfig`** — the kit's voice, constant
  across every dealer:
  - `productName` — *"Dealer AI Kit"*
  - `productSubtitle` — *"AI Sales Assistant"*

Both are typed (`DealerConfig`, `ProductConfig`) so a future
session can swap either set of constants in one place without
risking drift across surfaces.

### 2. Identity hierarchy enforced

Every brand surface now resolves identity in this order:

```
OnboardingProfile (live, edited in Setup)
       │  fallback when profile is empty / fetch fails
       ▼
DEFAULT_DEALER  (config/defaultDealer.ts)
       │
       ▼
(never hard-coded inline anywhere else)
```

Product strings (sidebar caption, embed footer attribution,
HTML `<title>` prefix) come from `PRODUCT` only — they don't
flow through `useBrand()` because they are not dealer-specific.

### 3. Files that consume the new config

| Surface | Was | Now |
| --- | --- | --- |
| `App.tsx` — `LOGO_SRC` constant | hard-coded path | `DEFAULT_DEALER.logoPath` |
| `App.tsx` — `PRODUCT_LABEL` constant | `"Dealer OS"` | `PRODUCT.productName` → renders **DEALER AI KIT** in the sidebar caption |
| `EmbedAssistantPage.tsx` — `<img src>` | hard-coded path | `DEFAULT_DEALER.logoPath` |
| `EmbedAssistantPage.tsx` — `Powered by …` footer | string literal | `Powered by ${PRODUCT.productSubtitle}` |
| `lib/brand.ts` — `FALLBACK` | inline literals | re-export of `DEFAULT_DEALER.{dealershipName, storeLocation, tagline}` |
| `index.html` — `<title>` | `"Sam's Freedom Ford McAlester — Dealer OS"` | `"Dealer AI Kit — Sam Wampler's Freedom Ford McAlester"` |

### 4. Brand-neutral defaults in shared components

- **`AssistantChat.tsx`** default `welcomeTitle` softened from
  `"Hi — I'm Freedom Ford's sales assistant."` to
  `"Hi — I'm your dealership's sales assistant."` — both call
  sites still override with brand-aware copy via the prop, but
  if a future surface ever forgets to override, the fallback
  is now neutral instead of branded for Dealer #1.

### 5. Brand-neutral placeholders in Setup

`DealerOnboardingPage.tsx` placeholders that hinted at
"Freedom Ford" / `freedomford.example.com` were softened so a
hypothetical second dealer setting up doesn't see Dealer #1's
identity bleeding into their hint copy:

| Field | Was | Now |
| --- | --- | --- |
| Dealership name | `"Freedom Ford"` | `"Your dealership name"` |
| Website | `"https://freedomford.example.com"` | `"https://your-dealership.example.com"` |
| Salesperson email | `"sarah@freedomford.example.com"` | `"sarah@your-dealership.example.com"` |
| Personal intro | `"…right Ford for 12 years."` | `"…right vehicle for 12 years."` |
| Dealership greeting | `"Welcome to Freedom Ford. …"` | `"Welcome to your dealership. …"` |

The Sarah Lin name and the brand-mix example
(`"Ford (new) + multi-brand used"`) were left as concrete
sample copy — they're agnostic enough not to confuse a
non-Ford dealer.

### 6. New doc — `docs/PLATFORM_REFRAME.md`

Documents the reframe canonically. Contains:

- The new mental model (one repo, many dealer configs).
- The identity hierarchy table (product / default dealer /
  active dealer).
- The full mapping of what was generalized in SESSION_019.
- An explicit list of what *intentionally* remains
  Freedom-Ford-specific (logo asset, sample inventory snapshot,
  research / SITE_AUDIT, historical handoffs, repo directory
  name) — and *why* those are not bugs.
- The intended path for onboarding a second dealer onto the
  kit without forking.

### 7. Augmented start-file — `docs/FREEDOM_FORD_SESSION_START.md`

Prepended a 12-line callout block titled
*"SESSION_019 platform reframe (read first)"* that points
at the new doc. The rest of the file is preserved verbatim.
**Historical docs are not rewritten** per the SESSION_019
spec; the callout makes the new mental model the first thing
a new agent reads, while leaving the established session
walkthrough intact.

---

## Files changed

```
frontend/src/config/defaultDealer.ts                       NEW (DEFAULT_DEALER + PRODUCT, typed)
frontend/src/lib/brand.ts                                  FALLBACK now sources DEFAULT_DEALER
frontend/src/App.tsx                                       LOGO_SRC + PRODUCT_LABEL via config
frontend/src/pages/EmbedAssistantPage.tsx                  logo path + footer attribution via config
frontend/src/pages/DealerOnboardingPage.tsx                placeholders softened
frontend/src/components/AssistantChat.tsx                  default welcomeTitle softened
frontend/index.html                                        <title> reframed
docs/PLATFORM_REFRAME.md                                   NEW (canonical reframe doc)
docs/FREEDOM_FORD_SESSION_START.md                         + reframe callout (rest preserved)
docs/handoffs/SESSION_019_platform_reframe_dealer_ai_kit.md  NEW (this file)
```

---

## Verification

| Step | Result |
| --- | --- |
| `npx tsc --noEmit` | ✓ 0 errors |
| `npx vite build` | ✓ 1.05s · 1717 modules · 48.54 kB CSS · 433.50 kB JS (gzip 120.99 kB) |
| `context-kit doctor` (from project root) | ✓ 0 blocking, 5 warnings (all pre-existing — missing optional anchor docs, not introduced by SESSION_019) |
| `context-kit orient --short` | ✓ resolves cleanly; flags the new SESSION_019 handoff after commit |
| Playwright `/dealer-ai-overview` | Sidebar caption **DEALER AI KIT**; topbar `Sam Wampler's Freedom Ford · McAlester`; tab title `Dealer AI Kit — Sam Wampler's Freedom Ford McAlester`; console 0/0 |
| Playwright `/dealer-ai-live-assistant` | Welcome `Hi — I'm Sam Wampler's Freedom Ford's sales assistant.`; footer `A Sam Wampler's Freedom Ford advisor confirms real numbers.`; sidebar tagline footer `Sam Wampler Make It Happen`; console 0/0 |
| Playwright `/embed/assistant` | Brand bar `Sam Wampler's Freedom Ford Assistant`; footer `Powered by AI Sales Assistant` (now from PRODUCT); console 0/0 |
| Playwright Public Preview dialog | Description `This is how the Sam Wampler's Freedom Ford assistant appears on your website.`; iframe renders the full brand-aware embed; console 0/0 |
| Logo asset loads | ✓ same shipped `/branding/sams-freedom-ford-logo.jpg` resolves through `DEFAULT_DEALER.logoPath` |

Backend baseline unchanged — SESSION_019 is frontend + docs
only. SESSION_011's 1210 / 1 baseline still holds.

Screenshots saved locally as `session_019_overview.png`,
`session_019_live_assistant.png`, `session_019_embed.png`,
`session_019_public_preview.png` (gitignored under `/*.png`).

---

## Product vs dealer identity — quick reference

| Where | Identity | Source |
| --- | --- | --- |
| Sidebar caption | product | `PRODUCT.productName` → "Dealer AI Kit" |
| Sidebar logo + name fallback | dealer | `DEFAULT_DEALER` / profile |
| Sidebar tagline footer | dealer | `DEFAULT_DEALER.tagline` (no profile field yet) |
| Topbar bold text | dealer | profile `dealership_name` → fallback |
| Topbar location chip | dealer | profile `store_location` → fallback |
| HTML `<title>` | mixed | `Dealer AI Kit — <Default Dealer>` |
| Mobile drawer SheetTitle (sr-only) | mixed | `<dealer.displayName> — Dealer AI Kit` |
| Embed brand bar headline | dealer | `<dealer.dealershipName> Assistant` |
| Embed welcome line | dealer | `Hi — I'm <dealer.possessiveName> sales assistant.` |
| Embed left footer | dealer | `Estimates only. A <dealer.dealershipName> advisor…` |
| Embed right footer | product | `Powered by AI Sales Assistant` |
| Public Preview dialog title | product | `Public Preview` |
| Public Preview dialog description | dealer | `This is how the <dealer.dealershipName> assistant appears on your website.` |
| Public Preview iframe `title` | dealer | `<dealer.embedAssistantName> preview` |

---

## What's still Freedom-Ford-specific (intentional)

These are **not bugs** — they are Dealer #1's shipped
artifacts. Documented in `docs/PLATFORM_REFRAME.md` and
repeated here for the next agent's quick-read:

- **Logo asset** at
  `frontend/public/branding/sams-freedom-ford-logo.jpg`. A
  multi-tenant upgrade adds a per-dealer upload field on
  `OnboardingProfile`.
- **Sample inventory snapshot**
  `frontend/src/data/freedomFordInventorySample.ts`. 18
  vehicles, demo only. Replaced by the future CRM/DMS feed.
- **Public-site research** at
  `docs/research/samsfreedomford/`. Frozen as historical
  reference.
- **Historical handoffs** at `docs/handoffs/SESSION_*.md`.
  Names + copy reflect the Freedom-Ford era. Per spec, **not**
  rewritten.
- **Repo / directory name** `freedom-ford`. Renaming touches
  every developer's local clone path; deferred until there's
  a concrete reason.

---

## Known limitations

- **No multi-tenant logo upload yet.** `DEFAULT_DEALER.logoPath`
  is a single static asset. A second dealer needs either an
  edit to `defaultDealer.ts` plus a logo drop into
  `frontend/public/branding/`, or a future session that adds
  a per-dealer upload field on `OnboardingProfile`.
- **No runtime dealer registry.** `DEFAULT_DEALER` is a single
  static export. Adding a second dealer today still means
  editing this constant before deploying for them. A future
  session could replace it with a config-driven registry keyed
  by hostname or env var.
- **Repo / directory name unchanged.** Still `freedom-ford`.
- **Historical handoffs left intact.** Voice from the
  Freedom-Ford era preserved on purpose; rewriting history
  would be much larger and lower-value.
- **No backend touched.** No new endpoints, no model changes,
  no migrations. The backend already serves a single per-store
  profile; multi-tenant routing on the backend is a separate
  concern for whenever it becomes real.
- **AssistantChat default still active.** Both call sites
  override `welcomeTitle` today, but the default
  `"Hi — I'm your dealership's sales assistant."` will render
  if a future surface forgets to override. Intentional
  graceful degradation.
- **`/dealer-ai-demo` legacy route** still mounted. Decision
  deferred again.

---

## Recommended next session

**SESSION_020 — Leads pipeline page (turn the stub into real).**

This was the recommendation in the SESSION_018 handoff that
got pre-empted by the SESSION_019 platform reframe. It remains
the highest-leverage outstanding frontend-only work:

`/dealer-ai-leads` is currently a SESSION_015-era stub showing
the 10 most recent leads with a *"Preview · full view coming
soon"* badge and basic name/phone/email/urgency fields. The
full pipeline view was deferred. SESSION_020 turns it into the
real surface.

**Scope:**

- Per-lead detail (modal or side panel) showing:
  - Full conversation transcript (assistant + user turns).
  - `extracted_profile` rendering (budget, body style, model
    intent, urgency, etc.).
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
  inventory snapshot, or the `/dealer-ai-demo` legacy route.
- ❌ No write actions on the leads page in v1 (read-only).
- ❌ No edits to `DEFAULT_DEALER` / `PRODUCT` config (the
  reframe is settled; SESSION_020 *consumes* it, doesn't edit
  it).
- ❌ No new API contracts beyond a TypeScript field-sync if a
  leads/session payload field is missing from the interface.

**Alternates** (covered briefly in SESSION_018 handoff):

- `SESSION_020b` — Inventory data quality / image cleanup.
  Pick if the next demo audience cares about the customer-
  facing browse surface more than the dealer-facing pipeline.
- `SESSION_020c` — Backend X-Frame-Options / CSP allowlist
  for cross-origin embedding. Backend-touching. Pick if a
  third-party-embed deadline is real.
- `SESSION_020d` — Multi-tenant logo upload (onboarding
  profile field + UI consumption). Pick if Dealer #2 is
  about to onboard.

Default to **SESSION_020 (Leads pipeline)** unless a specific
alternate is dictated by the next demo audience.
