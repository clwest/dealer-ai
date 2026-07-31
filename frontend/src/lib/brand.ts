// SESSION_018 — brand identity helper.
// SESSION_019 — fallbacks now read from `config/defaultDealer.ts`
// so the kit can be retargeted at a different default dealer in
// one place.
//
// Reads the dealer's identity from the existing onboarding profile
// (`fetchOnboardingProfile()` — the endpoint already used by the
// Overview page) and exposes a small set of computed strings used by
// every brand surface in the app: sidebar, topbar, mobile drawer,
// embed brand bar, embed footer, AssistantChat welcome line.
//
// **Fetch-on-mount, no global state.** Each consumer fires its own
// fetch. Save-then-navigate is the expected refresh pattern;
// module-level caching would defeat that.
//
// **Hard fallbacks.** When the fetch fails or fields are empty, we
// fall back to `DEFAULT_DEALER` from `config/defaultDealer.ts`
// (a neutral default dealer). The embed surface in particular can
// load before the OS ever boots — graceful degradation matters.

import { useEffect, useState } from "react";

import { DEFAULT_DEALER } from "@/config/defaultDealer";
import {
  fetchOnboardingProfile,
  type OnboardingProfilePayload,
} from "@/lib/api";

const FALLBACK = {
  dealershipName: DEFAULT_DEALER.dealershipName,
  storeLocation: DEFAULT_DEALER.storeLocation,
  tagline: DEFAULT_DEALER.tagline,
} as const;

export interface Brand {
  /** Raw dealership name from the profile, or fallback. Headline string. */
  dealershipName: string;
  /** City / location from the profile, or fallback. */
  storeLocation: string;
  /** Long-form "<Name> <Location>" used for accessibility / sr-only text. */
  displayName: string;
  /** Short name suitable for the topbar — the dealership name itself. */
  topbarName: string;
  /** "<Name> Assistant" — used as the embed brand bar headline. */
  embedAssistantName: string;
  /** Possessive form for sentences like "Hi — I'm <X>'s sales assistant." */
  possessiveName: string;
  /** Marketing tagline. Constant for now (no profile field for it yet). */
  tagline: string;
  /** SESSION_021 — resolved logo URL. Profile-supplied hosted URL when
   *  set; otherwise the kit's static fallback (`DEFAULT_DEALER.logoPath`).
   *  Always a non-empty string — consumers can pass it straight to
   *  `<img src>` and rely on the image's own `onError` for the
   *  asset-missing case. */
  logoUrl: string;
  /** True iff the profile supplied a non-empty `logo_url`. Useful for
   *  Setup-side surfaces that want to label the logo source ("from
   *  profile" vs "default"). */
  logoFromProfile: boolean;
  /** True once the fetch has resolved (success OR failure). Useful for
   *  surfaces that want to avoid flashing the fallback during first
   *  paint — both branches are valid, so most consumers can ignore it. */
  loaded: boolean;
}

/**
 * Compose the user-facing brand strings from a (possibly partial)
 * onboarding profile. Any missing field falls through to the
 * neutral default identity. Pure function — easy to call from
 * non-hook contexts (tests, SSR, etc.) if needed later.
 */
export function brandFromProfile(
  profile: OnboardingProfilePayload | null | undefined,
): Omit<Brand, "loaded"> {
  const dealershipName =
    (profile?.dealership_name && profile.dealership_name.trim()) ||
    FALLBACK.dealershipName;
  const storeLocation =
    (profile?.store_location && profile.store_location.trim()) ||
    FALLBACK.storeLocation;
  // SESSION_021 — logo resolution. Profile-supplied hosted URL wins;
  // otherwise the kit's static fallback under /branding/. Either
  // branch yields a usable string for <img src>; the image's own
  // onError handler catches a 404 / bad URL.
  const trimmedLogo = profile?.logo_url?.trim() ?? "";
  const logoFromProfile = trimmedLogo.length > 0;
  const logoUrl = logoFromProfile ? trimmedLogo : DEFAULT_DEALER.logoPath;
  return {
    dealershipName,
    storeLocation,
    displayName: `${dealershipName} ${storeLocation}`,
    topbarName: dealershipName,
    embedAssistantName: `${dealershipName} Assistant`,
    possessiveName: toPossessive(dealershipName),
    tagline: FALLBACK.tagline,
    logoUrl,
    logoFromProfile,
  };
}

/**
 * React hook that loads the brand strings on mount. Use anywhere a
 * component needs to render dealership-aware copy.
 *
 * Cancellation-safe: a setState after unmount is suppressed.
 */
export function useBrand(): Brand {
  const [profile, setProfile] = useState<OnboardingProfilePayload | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchOnboardingProfile()
      .then((p) => {
        if (cancelled) return;
        setProfile(p);
      })
      .catch(() => {
        // Profile fetch is allowed to fail — fallbacks render.
      })
      .finally(() => {
        if (cancelled) return;
        setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { ...brandFromProfile(profile), loaded };
}

/**
 * "Downtown Motors" → "Downtown Motors's"
 * "Sam's Auto Center" → "Sam's Auto Center" (unchanged)
 *
 * If the name already ends in "'s" (apostrophe-s) we leave it as-is
 * so we don't produce double possessives like "Sam's's Auto Center".
 */
function toPossessive(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return trimmed;
  if (/['\u2019]s$/i.test(trimmed)) return trimmed;
  // Names ending in s ("Hess") still take "'s" in modern style; we
  // could special-case, but the dealer profile is unlikely to hit
  // that edge in practice. Keep it simple.
  return `${trimmed}'s`;
}

// ---- SESSION_032: shape-of-business hook ---------------------------------
//
// `useBrand()` above is the display-string hook (name / tagline /
// logo — anything that ends up as chrome copy). `useDealerProfile()`
// is the shape-of-business hook (dealer type, BHPH toggle, lender
// panel, warranty / credit range, makes carried). Kept as a separate
// hook so display consumers don't fetch business shape they never
// use, and business consumers get typed access without threading
// through the display API.
//
// Both hooks share `fetchOnboardingProfile()` under the hood — React
// Query would let this hit the network once, but we're consistent
// with the existing fetch-on-mount pattern until a real cache lands.

const _INDIE_FALLBACK = {
  dealerType: "independent" as const,
  bhphEnabled: true,
  subprimeLenders: [
    "Sonoran Credit",
    "Desert Auto Finance",
    "Vista Lending",
  ] as readonly string[],
  floorPlanLender: "NextGear",
  warrantyOffering: "30-day / 1000-mile powertrain",
  creditRangeServed: "580+ with strong down; BHPH below",
  makesCarried: [
    "Toyota",
    "Honda",
    "Ford",
    "Chevy",
    "Nissan",
    "Kia",
  ] as readonly string[],
};

export type DealerType = "independent" | "franchise";

export interface DealerProfile {
  /** Independent (mixed-lot used) or franchise (OEM-affiliated). */
  dealerType: DealerType;
  /** Buy-Here-Pay-Here financing offered at this store. */
  bhphEnabled: boolean;
  /** True once the profile has been saved via the Setup UI. When
   *  false, the shape-of-business fields reflect Copper Canyon
   *  defaults rather than persisted user choices. */
  configured: boolean;
  /** Parsed list of subprime lender partner names. */
  subprimeLenders: readonly string[];
  /** Primary floor-plan lender (single value). */
  floorPlanLender: string;
  /** Human-readable warranty offering. */
  warrantyOffering: string;
  /** Human-readable credit-tier range. */
  creditRangeServed: string;
  /** Parsed list of makes carried. Prefers new `makes_carried`
   *  field; falls back to legacy CSV `main_brands`. */
  makesCarried: readonly string[];
  /** True once the fetch has resolved (success OR failure). */
  loaded: boolean;
}

function splitLines(raw: string | undefined): string[] {
  return (raw ?? "")
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

function splitCsv(raw: string | undefined): string[] {
  return (raw ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * Compose the shape-of-business fields from a (possibly partial)
 * onboarding profile. Falls back to the Copper Canyon indie defaults
 * for any unset field so consumers can always trust the values are
 * usable. Pure function — mirror of `brandFromProfile`.
 */
export function dealerProfileFromPayload(
  profile: OnboardingProfilePayload | null | undefined,
): Omit<DealerProfile, "loaded"> {
  const dealerType: DealerType =
    profile?.dealer_type === "franchise" || profile?.dealer_type === "independent"
      ? profile.dealer_type
      : _INDIE_FALLBACK.dealerType;

  // Only trust `bhph_enabled` when the profile has been explicitly
  // configured — mirrors the backend resolver's `bhph_configured`
  // sentinel so display and prompts stay coherent.
  const bhphEnabled = profile?.bhph_configured
    ? profile.bhph_enabled
    : _INDIE_FALLBACK.bhphEnabled;

  const subprimeParsed = splitLines(profile?.subprime_lenders);
  const subprimeLenders: readonly string[] =
    subprimeParsed.length > 0 ? subprimeParsed : _INDIE_FALLBACK.subprimeLenders;

  const makesParsed = splitLines(profile?.makes_carried);
  const makesLegacy = splitCsv(profile?.main_brands);
  const makesCarried: readonly string[] =
    makesParsed.length > 0
      ? makesParsed
      : makesLegacy.length > 0
        ? makesLegacy
        : _INDIE_FALLBACK.makesCarried;

  const floorPlanLender =
    (profile?.floor_plan_lender?.trim() ?? "") || _INDIE_FALLBACK.floorPlanLender;
  const warrantyOffering =
    (profile?.warranty_offering?.trim() ?? "") || _INDIE_FALLBACK.warrantyOffering;
  const creditRangeServed =
    (profile?.credit_range_served?.trim() ?? "") || _INDIE_FALLBACK.creditRangeServed;

  return {
    dealerType,
    bhphEnabled,
    configured: Boolean(profile),
    subprimeLenders,
    floorPlanLender,
    warrantyOffering,
    creditRangeServed,
    makesCarried,
  };
}

/**
 * React hook that loads the shape-of-business fields on mount.
 * Cancellation-safe. Consumers that only need display strings
 * should prefer `useBrand()` instead.
 */
export function useDealerProfile(): DealerProfile {
  const [profile, setProfile] = useState<OnboardingProfilePayload | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchOnboardingProfile()
      .then((p) => {
        if (cancelled) return;
        setProfile(p);
      })
      .catch(() => {
        // Fetch is allowed to fail — Copper Canyon fallbacks render.
      })
      .finally(() => {
        if (cancelled) return;
        setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { ...dealerProfileFromPayload(profile), loaded };
}
