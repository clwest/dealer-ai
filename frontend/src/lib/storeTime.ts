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

// SESSION_244 (walk finding 53) — date-boundary helpers in the store's
// zone. The trial balance's "as of" is a store-day concept: 11:59 PM
// belongs to whichever day it is at the store, not at the browser.
// Building the boundary in the browser's local zone silently truncates
// the last hour east of the store or reaches into the next day west of
// it. Both directions land in the books once the view is frozen.

/** The store's own "today" as a `YYYY-MM-DD` string. Falls back to the
 *  browser's today if the zone is missing / invalid — same contract as
 *  the display helpers above. */
export function storeTodayIsoDate(
  timezone: string | null | undefined,
  reference: Date = new Date(),
): string {
  const zone = resolveZone(timezone);
  // en-CA renders numeric dates as YYYY-MM-DD; simpler than reassembling
  // parts by hand and it respects the `timeZone` option.
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: zone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(reference);
}

/** Convert a `YYYY-MM-DD` date-string to the full ISO instant that is
 *  23:59:59.999 on that date in the given store zone. Falls back to the
 *  browser's zone if the zone is missing / invalid. Empty / malformed
 *  date input returns an empty string so callers can skip the network. */
export function dateEndOfDayInStoreZoneIso(
  dateIso: string | null | undefined,
  timezone: string | null | undefined,
): string {
  if (!dateIso || !/^\d{4}-\d{2}-\d{2}$/.test(dateIso)) return "";
  const [year, month, day] = dateIso.split("-").map(Number);
  const zone = resolveZone(timezone);
  const instantMs = endOfDayInstantMs(year, month, day, zone);
  return new Date(instantMs).toISOString();
}

/** Wall-clock in `zone` for the given UTC instant, as numeric parts. */
function wallClockPartsInZone(
  instantMs: number,
  zone: string,
): { y: number; m: number; d: number; h: number; min: number; s: number } {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: zone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(new Date(instantMs));
  const get = (t: string) => Number(parts.find((p) => p.type === t)?.value ?? "0");
  let h = get("hour");
  // Intl occasionally reports midnight as 24; normalise so downstream
  // arithmetic stays honest.
  if (h === 24) h = 0;
  return { y: get("year"), m: get("month"), d: get("day"), h, min: get("minute"), s: get("second") };
}

/** Offset in ms between the zone's wall-clock and UTC at the given
 *  instant. Positive east of UTC; negative west. */
function zoneOffsetMs(instantMs: number, zone: string): number {
  const wc = wallClockPartsInZone(instantMs, zone);
  const asUtc = Date.UTC(wc.y, wc.m - 1, wc.d, wc.h, wc.min, wc.s);
  const flooredInstant = Math.floor(instantMs / 1000) * 1000;
  return asUtc - flooredInstant;
}

/** UTC instant of 23:59:59.999 on the given calendar date in `zone`.
 *  Uses one DST correction pass — enough for every real IANA zone. */
function endOfDayInstantMs(
  year: number,
  month: number,
  day: number,
  zone: string,
): number {
  const desiredWallAsUtc = Date.UTC(year, month - 1, day, 23, 59, 59, 999);
  const guessOffset = zoneOffsetMs(desiredWallAsUtc, zone);
  let instant = desiredWallAsUtc - guessOffset;
  const actualOffset = zoneOffsetMs(instant, zone);
  if (actualOffset !== guessOffset) {
    instant = desiredWallAsUtc - actualOffset;
  }
  return instant;
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
