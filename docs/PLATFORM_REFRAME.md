---
title: "Platform Reframe — Dealer AI Kit"
date: 2026-05-02
status: active
session: SESSION_019
---

# Platform Reframe — Dealer AI Kit

## What this codebase is now

This repository is the **Dealer AI Kit** — a reusable AI sales
assistant platform for franchise auto dealerships. It ships with
**Sam Wampler's Freedom Ford McAlester** as Dealer #1 and the
default configuration. Future dealers (Chevy, Toyota, etc.) are
added as additional dealer configurations **inside this same
repository**, not as forks or separate codebases.

**One repo. Many dealer configurations.** The product (the kit)
and the dealer (whoever's running it) are now distinct concepts
with separate identity.

## Identity hierarchy

| Layer | Purpose | Source of truth |
| --- | --- | --- |
| **Product / platform** | The kit itself. Constant across every dealer. | `frontend/src/config/defaultDealer.ts` → `PRODUCT` |
| **Default dealer** | The fallback dealer identity used when the onboarding profile is empty. Currently Sam Wampler's Freedom Ford. | `frontend/src/config/defaultDealer.ts` → `DEFAULT_DEALER` |
| **Active dealer** | The runtime identity edited by the manager in Setup and persisted to the backend. | `OnboardingProfile` (PUT `/api/dealer-ai/onboarding/profile/`) |

### Resolution rule

Brand surfaces resolve runtime identity in this order:

```
OnboardingProfile.dealership_name  →  DEFAULT_DEALER.dealershipName
OnboardingProfile.store_location   →  DEFAULT_DEALER.storeLocation
(no profile field for tagline)     →  DEFAULT_DEALER.tagline
```

The `useBrand()` hook in `frontend/src/lib/brand.ts` enforces
this order. Every brand-aware surface goes through `useBrand()`
— no component reads the profile or `DEFAULT_DEALER` directly
for brand-display purposes.

### Product identity is separate

`PRODUCT.productName = "Dealer AI Kit"` and
`PRODUCT.productSubtitle = "AI Sales Assistant"` are the kit's
voice. They appear in chrome that talks about *the platform*
(sidebar caption, embed footer attribution). They never reflect
the dealer.

The dealer's voice ("Sam Wampler's Freedom Ford Assistant",
"A Sam Wampler's Freedom Ford advisor confirms real numbers")
is always profile-driven, never product-driven.

## What's still Freedom-Ford-specific (intentional)

These are dealer-specific artifacts that ship with the kit but
would be replaced or augmented when adding a second dealer.
They are **not bugs** — they are the kit's first dealer
configuration:

- **Logo asset**:
  `frontend/public/branding/sams-freedom-ford-logo.jpg`. The
  current installation displays this image because
  `DEFAULT_DEALER.logoPath` points at it. A multi-tenant
  upgrade would let the onboarding profile carry an uploaded
  asset URL.
- **Sample inventory snapshot**:
  `frontend/src/data/freedomFordInventorySample.ts`. 18
  vehicles captured from samsfreedomford.com on 2026-05-02 for
  the demo Inventory page. Will be replaced by a CRM/DMS feed
  integration; until then it's Freedom-Ford-specific demo data.
- **Public-site research**:
  `docs/research/samsfreedomford/` — captured screenshots and
  the SITE_AUDIT. Frozen as historical reference; not
  generalized into a "dealer audit framework".
- **Historical handoffs**: `docs/handoffs/SESSION_*.md` and
  `docs/handoffs/screenshots/`. Names and copy reflect the
  Freedom-Ford era of the project. **Not rewritten** —
  history is the record of how the project got here, and
  rewriting it would be a much larger and lower-value
  exercise.
- **Repo name**: directory name `freedom-ford` is unchanged.
  Renaming touches every developer's local clone path; defer
  until there's a concrete reason.

## What was generalized in SESSION_019

| Surface | Before | After |
| --- | --- | --- |
| Sidebar product caption | "DEALER OS" | "DEALER AI KIT" |
| HTML `<title>` | "Sam's Freedom Ford McAlester — Dealer OS" | "Dealer AI Kit — Sam Wampler's Freedom Ford McAlester" |
| Embed footer attribution | "Powered by AI Sales Assistant" | "Powered by AI Sales Assistant" (now sourced from `PRODUCT.productSubtitle`) |
| Logo path constant | inline string in `App.tsx` and `EmbedAssistantPage.tsx` | `DEFAULT_DEALER.logoPath` |
| Brand fallbacks in `useBrand()` | inline `FALLBACK` object | re-export of `DEFAULT_DEALER` fields |
| `AssistantChat` default `welcomeTitle` | "Hi — I'm Freedom Ford's sales assistant." | "Hi — I'm your dealership's sales assistant." (brand-neutral default; both call sites override) |
| Setup placeholders | "Freedom Ford", "freedomford.example.com", "right Ford for 12 years", "Welcome to Freedom Ford…" | brand-neutral hints ("Your dealership name", "your-dealership.example.com", "right vehicle", "your dealership") |

## Adding a second dealer (future)

The intended path for onboarding a second dealer onto this
kit, **without forking the codebase**:

1. Edit `DEFAULT_DEALER` in `frontend/src/config/defaultDealer.ts`
   for that dealer's name, location, tagline, brand, and logo
   path. Drop the new logo into `frontend/public/branding/`.
2. Run a fresh `OnboardingProfile` for the new dealer (PUT to
   the backend with the new identity).
3. (Future) replace step 1 with a per-dealer config registry
   keyed by hostname or environment variable, and replace step
   2 with profile creation through the kit's own UI.

What you don't change to add a second dealer:

- Chat behavior, prompt strings, scrub layer, structural
  enforcement.
- Inventory matching logic, budget-fit / lever-flex inference.
- The `<AssistantChat>` component, the embed page, the
  Public Preview dialog.
- The onboarding form itself.

The kit's behavior is brand-agnostic by design. Only the
identity layer is per-dealer.

## Why this reframe matters

Before SESSION_019, "Freedom Ford" was hard-coded into the
mental model of the project — both in code and in
conversation. That's the trap that keeps software stuck as a
custom project for one customer instead of a product. The
reframe doesn't change a single behavior, but it changes how
the next dealer is onboarded: not by forking, not by
search-and-replace, but by editing a single config module and
seeding a new onboarding profile.

The kit is now Dealer #1's tool, **and** Dealer #2's tool, and
Dealer #N's tool — the same kit.
