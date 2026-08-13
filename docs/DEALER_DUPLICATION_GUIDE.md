---
title: "Dealer Duplication Guide — Onboarding a Second Dealer"
audience: developer + dealership operations
---

# Dealer Duplication Guide

This guide is for taking Dealer AI — currently shipping with the
Copper Canyon Auto default persona — and standing up a second
dealership (Chevy, Toyota, another independent used-car lot, anything)
**without forking the repository**.

If you find yourself reaching for `git clone` to spin up Dealer
#2, stop. The kit is built so that adding a dealer is a config +
setup operation, not a fork operation. Forking duplicates every
future bug fix, every chat-behavior improvement, and every
inventory pipeline change across two codebases. Don't do it.

## Mental model (read first)

Three identity layers, in resolution order:

| Layer | Source | Per-dealer? |
| --- | --- | --- |
| Product / platform | `frontend/src/config/defaultDealer.ts` → `PRODUCT` | No — every install ships as "Dealer AI" |
| Default dealer (fallback) | `frontend/src/config/defaultDealer.ts` → `DEFAULT_DEALER` | Yes — edit when retargeting the kit at a different dealer |
| Active dealer (runtime) | `OnboardingProfile` via `useBrand()` | Yes — edited live in `/dealer-ai-onboarding` (Setup) |

Brand surfaces always resolve identity in this order:

```
OnboardingProfile  →  DEFAULT_DEALER  →  (never inline)
```

If a value can be edited in Setup, it must come from the profile
first. If the profile is empty or the fetch fails, fall back to
`DEFAULT_DEALER`. Never hard-code a dealer-specific string in a
component.

---

## What can be changed in Setup today

Everything in this list flows from the existing `OnboardingProfile`
and updates the OS shell, the embed, and the Public Preview dialog
on the next route mount. **No code changes required.**

- Dealership name (`dealership_name`)
- Store location (`store_location`)
- Main brands carried (`main_brands`) — informational; visible in
  the Setup form and the Dealer Kit Status card
- **Logo URL (`logo_url`)** — hosted URL for the dealer's logo
  image. When blank, the kit's static fallback
  (`DEFAULT_DEALER.logoPath`) is used. Consumed by the sidebar
  `BrandHeader`, the embed `BrandMark`, and the Setup Dealer Kit
  Status card.
- Sales phone / website
- Sales tone / pricing comfort / appointment preference / lead
  handoff style
- Dealership greeting + approved phrases + banned phrases +
  escalation rule + payment disclaimer (these drive chat behavior
  — the assistant is brand-agnostic and reads these per-store)
- One salesperson profile (full Sales Team via
  `/dealer-ai-admin/team`)
- Pilot checklist toggles

Save in Setup → navigate any other surface → fresh fetch picks up
the new identity.

## What still requires code/config

These are not user-editable yet. Each one has a documented path to
becoming editable in a later milestone.

### Static logo fallback (developer, optional)

**Where:** `frontend/public/branding/<slug>-logo.<ext>` referenced
via `DEFAULT_DEALER.logoPath`. **This is the fallback, not the
primary path.** The primary path is the `logo_url` field in Setup,
which any manager can edit live and have flow into every brand
surface on the next route mount.

**To swap (preferred — no developer):**

1. Open `/dealer-ai-onboarding`.
2. Paste a hosted logo URL into the **Logo URL** field in the
   Dealership profile section.
3. Save. Navigate to Overview → confirm sidebar logo updated.
   Navigate to `/embed/assistant` → confirm embed brand bar
   logo updated.

**To swap the static fallback (developer-only, optional):**

1. Drop the new dealer's logo into
   `frontend/public/branding/<dealer-slug>-logo.<ext>`.
   Acceptable formats: SVG (preferred), PNG with transparent
   background, JPG.
2. Update `DEFAULT_DEALER.logoPath` to point at the new file.

The static fallback only matters when the profile's `logo_url` is
empty (e.g. a fresh kit installation, a manager who hasn't filled
in the field, or a dealer who wants the kit's shipped asset rather
than a hosted URL). Most real deployments will set a profile URL
and never touch the fallback.

**Future path:** a multipart upload control + object storage would
let a manager upload the file directly through Setup instead of
pasting a URL. The `logo_url` field shape supports either.

### Default fallback config

**Where:** `frontend/src/config/defaultDealer.ts` → `DEFAULT_DEALER`.

**To swap** (single-tenant install, retargeting at a different
dealer):

```ts
// frontend/src/config/defaultDealer.ts
export const DEFAULT_DEALER: DealerConfig = {
  dealershipName: "Tulsa Chevrolet",         // your dealer
  storeLocation: "Tulsa",                     // your city
  tagline: "Drive Your Best Life",            // your tagline
  brand: "Chevrolet",                          // brand carried
  logoPath: "/branding/tulsa-chevrolet.svg",  // dropped above
  primaryColorNote: "Tailwind 'chevy.gold' (oklch ~0.78 0.15 90)",
};
```

Then run `OnboardingProfile` save through Setup for the live dealer
name/location to commit those values to the backend profile.

**Future path:** a per-dealer config registry keyed by hostname or
env var would let multiple dealers share one deploy. Not built yet.

### Embed host / CSP allowlist

**Today:** `/embed/assistant` loads same-origin. Public Preview
inside the OS works because the iframe is on the same host as the
OS itself.

For a real third-party embed on the dealer's marketing site, set
`VITE_EMBED_ALLOWED_ORIGINS` at build time to the dealer's origin
list (comma-separated). Vite auto-configures the `Content-Security-Policy:
frame-ancestors` header on the `/embed/assistant` route from that
env var. See `frontend/vite.config.ts` lines 5–21.

---

## "Do not fork the repo" rule

When considering whether to fork:

- ❌ **Don't fork** to support a different dealer.
- ❌ **Don't fork** to skin the OS in a different brand color.
- ❌ **Don't fork** to swap the logo.
- ❌ **Don't fork** to point at a different inventory feed.

Fork is correct only when:

- The kit's behavior itself diverges (different chat language,
  different scrub layer, different deal flow). At that point it's
  no longer the same product, and a fork is honest.

If you find yourself reaching for `git clone` because "this dealer
is different", check whether the difference is actually identity
(config) or behavior (code). 99% of the time it's identity.

---

## Recommended workflow — onboarding Dealer #2

Step-by-step. Skip steps already complete.

### Phase 1 — Static fallback (developer, optional, ~5 min)

Only required if you want the kit's *shipped* asset to match the
new dealer (e.g. when no hosted logo URL is available yet, or you
want the kit to look right even before any manager fills out
Setup):

1. **Drop the new dealer's logo** into
   `frontend/public/branding/<slug>.<ext>`. SVG preferred.
2. **Edit `DEFAULT_DEALER`** in
   `frontend/src/config/defaultDealer.ts` for the new dealership
   name / location / tagline / brand / logoPath.
3. **Run `npx tsc --noEmit && npx vite build`** to confirm the
   kit still compiles.

If you have a hosted URL for the dealer's logo, skip this phase
entirely and configure it in Phase 2.

### Phase 2 — Dynamic identity (manager, ~15 min)

1. **Open `/dealer-ai-onboarding`** in a browser.
2. **Fill in** Dealership name, Store location, Main brands, Sales
   phone, Website, **Logo URL** (a hosted image URL — leave blank
   to use the kit's static fallback). The "Dealer Kit Status" card
   mirrors these fields in real time so the manager can see
   exactly what the OS chrome will look like before saving.
3. **Set** sales tone, pricing comfort, appointment preference,
   lead handoff style.
4. **Add at least one salesperson** (full team via the Team page
   later).
5. **Configure** dealership greeting, banned phrases, escalation
   rule, payment disclaimer. These drive chat behavior — the
   assistant reads them per-store.
6. **Save**. Navigate to Overview → confirm topbar + sidebar logo
   show the new identity. Navigate to `/embed/assistant` → confirm
   the embed brand bar reads correctly.

### Phase 3 — Verification (5 min)

- Tab title in the browser reads
  `Dealer AI — <New Dealer Name> <Location>`.
- Sidebar caption reads `DEALER AI`. Logo asset displays.
- Sidebar tagline footer shows the new tagline (or the default if
  you didn't edit it — taglines aren't a profile field yet).
- Topbar reads `<New Dealer Name> · <Location>`.
- Embed brand bar reads `<New Dealer Name> Assistant`.
- Embed welcome line reads
  `Hi — I'm <New Dealer Name>'s sales assistant.`.
- Embed footer reads
  `Estimates only. A <New Dealer Name> advisor confirms real
  numbers.`.
- Public Preview dialog description reads `This is how the
  <New Dealer Name> assistant appears on your website.`.
- Console: 0 errors, 0 warnings on every brand surface.

---

## Onboarding checklist (printable)

Copy this into a kickoff doc when standing up Dealer #2.

```
□ Setup form opened (/dealer-ai-onboarding)
□ Dealership name + Store location + Main brands filled
□ Logo URL pasted (or left blank to use the static fallback)
□ Setup form saved
□ Overview page shows new identity in topbar + sidebar logo
□ Embed page shows new identity in brand bar + footer
□ Public Preview dialog description shows new dealer name
□ Console clean across brand surfaces
□ Optional (developer): static fallback updated in
  /public/branding/ + DEFAULT_DEALER.logoPath
□ Optional: salesperson profiles added
□ Optional: tagline + banned phrases + greeting set
□ Pilot review checked (Setup → Pilot review pending → toggled)
```

If every box ticks for a new dealer, the kit is serving them
without a fork. That's the contract.

---

## Glossary

- **Kit** — this codebase. One repository, many possible dealer
  configurations.
- **Dealer** — the dealership using the kit. Currently the
  shipped default persona (Copper Canyon Auto, a fictional
  independent lot in Yuma, AZ).
- **Active dealer** — the dealer identity edited in Setup and
  loaded at runtime via `useBrand()`.
- **Default dealer** — the fallback identity in `DEFAULT_DEALER`,
  used when the profile is empty or the fetch fails.
- **Product** — the kit's voice. Constant across every dealer.
  "Dealer AI", "AI Sales Assistant".
- **Brand surface** — any UI element that displays dealership
  name / location / tagline / logo. Examples: topbar, sidebar,
  embed brand bar, embed footer disclaimer, Public Preview dialog
  description.

---

## Related docs

- `docs/DEALER_KIT_TRANSLATION_LAYER.md` — persona/translation-mode
  contract.
- `docs/DEALER_KIT_BEHAVIOR_LAYER.md` — behavior-layer architecture.
- `frontend/src/config/defaultDealer.ts` — the config module this
  guide references throughout.
- `frontend/src/lib/brand.ts` — the `useBrand()` hook every brand
  surface routes through.
