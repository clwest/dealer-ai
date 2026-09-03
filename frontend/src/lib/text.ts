// SESSION_236 (TASK_names-and-money.md, part 3) — small formatting
// helpers that got copy-pasted or, worse, forgotten. The walk called
// out "1 notes" / "1 be-backs" / "1 deals" for the missing plural
// and "2026-08-29T13:11:31.681330+00:00" for the raw ISO stamp.

/**
 * Render a count with a naive plural. Chris's rule: a helper is
 * enough — the app never renders enough count strings to justify
 * a real inflection library, and irregulars can pass their own
 * plural in explicitly.
 */
export function plural(
  count: number,
  singular: string,
  pluralForm?: string,
): string {
  if (count === 1) return `${count} ${singular}`;
  return `${count} ${pluralForm ?? `${singular}s`}`;
}

/**
 * Format an ISO-8601 timestamp for on-screen display. Backend
 * projections emit ISO strings with microseconds + tz offset
 * (``2026-08-29T13:11:31.681330+00:00``); operators do not want to
 * read that. Falls back to the raw string on parse failure so a
 * malformed value at least reveals itself.
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/** Date-only variant of :func:`formatDateTime`. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
