// SESSION_019 — platform reframe.
// SESSION_020 — expanded comments on the no-fork rule and the
// future logo upload path. See docs/DEALER_DUPLICATION_GUIDE.md
// for the full operator workflow.
//
// This codebase is the **Dealer AI Kit** — a reusable dealer
// AI platform. It ships with a neutral default dealer; real
// dealers are configured either by editing this file or by
// filling in the OnboardingProfile via Setup.
//
// Additional dealers (Chevy, Toyota, etc.) are added as
// additional dealer configs **inside this same repo**, not as
// forks. Single codebase, many configurations.
//
// **Do not fork the repo to add a dealer.** Every fork
// duplicates every future bug fix, every chat-behavior
// improvement, and every inventory-pipeline change. The kit is
// designed so that adding a dealer is a config edit + a Setup
// save, not a `git clone`. Fork only when the kit's *behavior*
// itself diverges from the platform's intent — at that point
// it's a different product, and a fork is honest.
//
// Identity hierarchy (resolution order)
// -------------------------------------
// 1. `OnboardingProfile` (live, edited in /dealer-ai-onboarding,
//    persisted to the backend) — overrides everything visible.
// 2. `DEFAULT_DEALER` (this file) — fallback when the profile
//    is empty, the fetch fails, or the kit hasn't booted yet
//    (e.g. the embed surface loaded before any manager opened
//    the OS).
// 3. Inline literals in components — banned. If you find a
//    dealer-specific string baked into a component, route it
//    through `useBrand()` instead.
//
// What lives in this file
// -----------------------
// - **Dealer-specific defaults** (name, location, tagline, brand,
//   logo path) used as fallbacks by `useBrand()` when the
//   onboarding profile is empty or the fetch fails.
// - **Product-level identity** (productName, productSubtitle)
//   used by the OS shell and embed for product-voice copy.
//   These are the *kit's* voice — they don't change per-dealer.
//
// What does NOT live here
// -----------------------
// - Anything driven by the onboarding profile. If a value can
//   be edited in Setup, it must come from the profile first.
// - Per-dealer configuration that should be runtime-loaded. A
//   future multi-tenant session could replace this static export
//   with a registry keyed by dealer slug; the current kit ships
//   with a single default to keep the frontend simple.
//
// How to retarget the kit at a different default dealer
// -----------------------------------------------------
// 1. Drop the new dealer's logo into
//    `frontend/public/branding/<slug>.<ext>`. Prefer SVG.
// 2. Edit the `DEFAULT_DEALER` block below — `dealershipName`,
//    `storeLocation`, `tagline`, `brand`, `logoPath`,
//    `primaryColorNote`. Touch nothing else.
// 3. Run `npx tsc --noEmit && npx vite build`. Both should
//    pass without code changes elsewhere.
// 4. Open `/dealer-ai-onboarding` and let the manager fill in
//    the live profile via Setup. The shell + embed pick up
//    the new identity on the next route mount.
//
// See `docs/DEALER_DUPLICATION_GUIDE.md` for the full
// operator-facing checklist.

export interface DealerConfig {
  /** Dealership legal/marketing name. Headline string. */
  dealershipName: string;
  /** City / location ("McAlester", "Tulsa, OK", etc.). */
  storeLocation: string;
  /** Marketing tagline shown in the sidebar footer. */
  tagline: string;
  /** Vehicle brand carried by this dealership ("Ford", "Chevy"). */
  brand: string;
  /** Path to a static logo asset under /public. Static for now —
   *  there is no `OnboardingProfile.logo_url` field yet, so swapping
   *  the displayed logo means dropping a new file under
   *  `frontend/public/branding/` and editing this constant. A
   *  future multi-tenant session adds a per-dealer upload field on
   *  the profile, at which point `useBrand()` will prefer the
   *  uploaded URL and fall back to this static asset. */
  logoPath: string;
  /** Hex / token note describing the brand's primary color. The
   *  OS shell uses the `brand.blue` Tailwind token by default; this
   *  field is informational for future skinning sessions. */
  primaryColorNote: string;
}

export interface ProductConfig {
  /** Platform / kit name. The user-facing product label used in
   *  the OS shell, independent of any specific dealer. */
  productName: string;
  /** Customer-facing product subtitle ("Powered by …", footer
   *  attributions, etc.). */
  productSubtitle: string;
}

/**
 * The kit's shipped default dealer.
 *
 * Post-SESSION_030 pivot, this ships the Copper Canyon Auto
 * (Yuma, AZ) invented independent-dealer persona. See
 * docs/INDEPENDENT_DEALER_PIVOT.md for the full persona and
 * docs/demo/COPPER_CANYON_DEMO_SCRIPT.md for the demo flow.
 *
 * Real dealers still override this via the OnboardingProfile
 * (Setup UI at /dealer-ai-onboarding) — that path is unchanged.
 * When the profile is empty (fresh install pre-Setup, embed
 * surface loaded before the OS booted), the values below fill
 * in so the shell reads coherently rather than showing blank
 * strings.
 *
 * Do not edit chat behavior, prompt strings, scrub layer, or
 * inventory logic to swap the dealer — those concerns are
 * already brand-agnostic and drive from the backend's
 * DealerProfile resolver.
 */
export const DEFAULT_DEALER: DealerConfig = {
  dealershipName: "Copper Canyon Auto",
  storeLocation: "Yuma, AZ",
  tagline: "Yuma's trusted lot since 1987.",
  // Mixed-make used lot — no single primary brand. Franchise
  // configs set this to their OEM ("Ford", "Toyota", etc.).
  brand: "",
  logoPath: "/branding/copper-canyon-logo.svg",
  primaryColorNote:
    "brand.blue = #3f6b90 (desert-sky). brand.accent = #c76b3a " +
    "(copper terracotta). Configure in tailwind.config.js + " +
    "src/index.css for palette swaps.",
};

/**
 * Platform identity. These strings are the **kit's** voice, not
 * the dealer's — a Chevy installation of this codebase would
 * still ship as "Dealer AI Kit". The dealer's name lives in
 * `DEFAULT_DEALER.dealershipName` and the onboarding profile.
 */
export const PRODUCT: ProductConfig = {
  productName: "Dealer AI Kit",
  productSubtitle: "AI Sales Assistant",
};
