// SESSION_232 addendum — module-level cache for the resolved
// dealership slug. Public/embed chat + showroom fetches attach it as
// ``X-Dealership-Slug`` so the multi-store backend routes anonymous
// callers to the right store.
//
// The slug is primed by ``fetchOnboardingProfile`` (used by
// ``useBrand``); the app boots that on first render, so by the time
// the customer starts a chat or the showroom fetches inventory the
// header is available. Falls back to a build-time default from
// ``import.meta.env.VITE_DEALERSHIP_SLUG`` when set (useful for
// embedded / cross-domain deployments that never call the branding
// endpoint before the first chat turn).

const BUILD_TIME_FALLBACK =
  ((import.meta.env.VITE_DEALERSHIP_SLUG as string | undefined) ?? "").trim();

let cachedSlug: string = BUILD_TIME_FALLBACK;

export function setDealershipSlug(slug: string | null | undefined): void {
  const trimmed = (slug ?? "").trim();
  if (trimmed) cachedSlug = trimmed;
}

export function getDealershipSlug(): string {
  return cachedSlug;
}

export function dealershipHeader(): Record<string, string> {
  return cachedSlug ? { "X-Dealership-Slug": cachedSlug } : {};
}
