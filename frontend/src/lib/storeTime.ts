// SESSION_240 (walk finding 28) — one clock per store, on the frontend.
//
// The backend stores every timestamp as UTC and hands the frontend an
// ISO 8601 string with offset. What "today" reads on the operator's
// ledger, on the overview card, on the follow-up due dates and on a
// journal entry must be the STORE's local day, not the browser's.
//
// The store's IANA zone (e.g. "America/Phoenix") comes down inside the
// onboarding profile payload the shell already fetches; callers pass
// it into these helpers instead of relying on the browser's clock.
//
// One formatter, grep'd in. Prefer these over `new Date(iso).toLocale*`
// anywhere the value represents store-local business time.

/** Format an ISO 8601 timestamp as a short date string in the store's
 *  zone, e.g. `Sep 3, 2026`. Missing / invalid input renders as `—`
 *  so a null column doesn't crash the row. */
export function formatDateInStoreZone(
  iso: string | null | undefined,
  timezone: string | null | undefined,
): string {
  const zone = resolveZone(timezone);
  const date = parseIso(iso);
  if (date === null) return "—";
  return new Intl.DateTimeFormat("en-US", {
    timeZone: zone,
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

/** Format an ISO 8601 timestamp as a short time string in the store's
 *  zone, e.g. `3:12 PM`. */
export function formatTimeInStoreZone(
  iso: string | null | undefined,
  timezone: string | null | undefined,
): string {
  const zone = resolveZone(timezone);
  const date = parseIso(iso);
  if (date === null) return "—";
  return new Intl.DateTimeFormat("en-US", {
    timeZone: zone,
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

/** Format an ISO 8601 timestamp as a combined date + time in the
 *  store's zone, e.g. `Sep 3, 2026 · 3:12 PM`. */
export function formatDateTimeInStoreZone(
  iso: string | null | undefined,
  timezone: string | null | undefined,
): string {
  const date = formatDateInStoreZone(iso, timezone);
  const time = formatTimeInStoreZone(iso, timezone);
  if (date === "—" || time === "—") return "—";
  return `${date} · ${time}`;
}

/** The store's own `now` as `HH:MM AM/PM` — used by the onboarding
 *  page's live "It is 3:12 PM at the store right now" hint. */
export function storeNowLabel(
  timezone: string | null | undefined,
  reference: Date = new Date(),
): string {
  const zone = resolveZone(timezone);
  return new Intl.DateTimeFormat("en-US", {
    timeZone: zone,
    hour: "numeric",
    minute: "2-digit",
  }).format(reference);
}

function parseIso(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d;
}

function resolveZone(timezone: string | null | undefined): string {
  // A bad name would throw inside Intl. Fall back to the browser's
  // zone (never guess Chicago in this direction — a browser-based
  // fallback at least keeps the display truthful about which clock
  // it is reading).
  if (!timezone) {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  }
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: timezone });
    return timezone;
  } catch {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  }
}
