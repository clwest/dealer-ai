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
// (currently Sam Wampler's Freedom Ford McAlester). The embed
// surface in particular can load before the OS ever boots —
// graceful degradation matters.

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
  /** True once the fetch has resolved (success OR failure). Useful for
   *  surfaces that want to avoid flashing the fallback during first
   *  paint — both branches are valid, so most consumers can ignore it. */
  loaded: boolean;
}

/**
 * Compose the user-facing brand strings from a (possibly partial)
 * onboarding profile. Any missing field falls through to the
 * verified Sam Wampler's identity. Pure function — easy to call
 * from non-hook contexts (tests, SSR, etc.) if needed later.
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
  return {
    dealershipName,
    storeLocation,
    displayName: `${dealershipName} ${storeLocation}`,
    topbarName: dealershipName,
    embedAssistantName: `${dealershipName} Assistant`,
    possessiveName: toPossessive(dealershipName),
    tagline: FALLBACK.tagline,
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
 * "Sam Wampler's Freedom Ford" → "Sam Wampler's Freedom Ford's"
 * "Freedom Ford" → "Freedom Ford's"
 *
 * If the name already ends in "'s" (apostrophe-s) we leave it as-is
 * so we don't produce double possessives like "Sam's's Freedom Ford".
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
