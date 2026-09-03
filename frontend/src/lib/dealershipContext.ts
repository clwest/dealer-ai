// SESSION_232 addendum — module-level cache for the resolved
// dealership slug. Public/embed chat + showroom fetches attach it as
// ``X-Dealership-Slug`` so a multi-store backend routes anonymous
// callers to the right store.
//
// The slug is primed by ``fetchOnboardingProfile`` (used by
// ``useBrand``). SESSION_232.2 removed the ``VITE_DEALERSHIP_SLUG``
// build-time fallback — one place, not two: the backend decides
// which store a public deployment belongs to via
// ``DEALER_AI_PUBLIC_DEALERSHIP_SLUG`` in ``backend/.env``. The
// frontend only echoes what the branding endpoint tells it.

let cachedSlug: string = "";

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
