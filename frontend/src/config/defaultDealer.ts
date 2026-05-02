// SESSION_019 — platform reframe.
//
// This codebase is the **Dealer AI Kit** — a reusable dealer
// AI platform. Sam Wampler's Freedom Ford McAlester is Dealer #1,
// the default configuration shipped with the kit.
//
// Future dealers (Chevy, Toyota, etc.) are added as additional
// dealer configs **inside this same repo**, not as forks. Single
// codebase, many configurations.
//
// What lives in this file
// -----------------------
// - **Dealer-specific defaults** (name, location, tagline, brand,
//   logo path) used as fallbacks by `useBrand()` when the
//   onboarding profile is empty or the fetch fails.
// - **Product-level identity** (productName, productSubtitle,
//   primaryColorNote) used by the OS shell and embed for
//   product-voice copy.
//
// What does NOT live here
// -----------------------
// - Anything driven by the onboarding profile. The hierarchy is:
//   onboarding-profile → defaultDealer fallback. If a value can
//   be edited in Setup, it must come from the profile first.
// - Per-dealer configuration that should be runtime-loaded. A
//   future multi-tenant session could replace this static export
//   with a registry keyed by dealer slug; the current kit ships
//   with a single default to keep the frontend simple.

export interface DealerConfig {
  /** Dealership legal/marketing name. Headline string. */
  dealershipName: string;
  /** City / location ("McAlester", "Tulsa, OK", etc.). */
  storeLocation: string;
  /** Marketing tagline shown in the sidebar footer. */
  tagline: string;
  /** Vehicle brand carried by this dealership ("Ford", "Chevy"). */
  brand: string;
  /** Path to a static logo asset under /public. Until per-dealer
   *  logo upload exists, this stays a single shipped asset. */
  logoPath: string;
  /** Hex / token note describing the brand's primary color. The
   *  OS shell already uses Ford-blue tokens via Tailwind; this
   *  field is informational for future skinning sessions. */
  primaryColorNote: string;
}

export interface ProductConfig {
  /** Platform / kit name. Replaces "Dealer OS" / "Freedom Ford AI"
   *  as the user-facing product label in the OS shell. */
  productName: string;
  /** Customer-facing product subtitle ("Powered by …", footer
   *  attributions, etc.). */
  productSubtitle: string;
}

/**
 * Sam Wampler's Freedom Ford McAlester — the kit's first dealer
 * and the active default configuration.
 *
 * Edit this block to point the kit at a different default dealer
 * (or rename Freedom Ford if the dealership changes its name).
 * Do not edit chat behavior, prompt strings, scrub layer, or
 * inventory logic to swap the dealer — those concerns are
 * already brand-agnostic.
 */
export const DEFAULT_DEALER: DealerConfig = {
  dealershipName: "Sam Wampler's Freedom Ford",
  storeLocation: "McAlester",
  tagline: "Sam Wampler Make It Happen",
  brand: "Ford",
  logoPath: "/branding/sams-freedom-ford-logo.jpg",
  primaryColorNote:
    "Tailwind 'ford.blue' token (oklch ~0.30 0.13 264). See tailwind.config.js.",
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
