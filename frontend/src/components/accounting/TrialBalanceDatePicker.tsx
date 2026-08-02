// Milestone 17 · Increment 2 (SESSION_146 — landed in SESSION_145) —
// date picker for the trial-balance page.
//
// Per MILESTONE_17_PLANNING.md §5.e Option B (date-only granularity;
// server accepts full ISO on the wire). Default: today (§0.a M17.1
// decision 2 — matches current live-view behavior; least surprising).
//
// Implementation note (§0.a M17.2 micro-decision — recommendation):
// Uses the native ``<input type="date">`` element (wrapped in the
// existing shadcn ``Input`` primitive) rather than installing shadcn
// ``Calendar``. Rationale: (1) the picker mental model is calendar
// dates per §5.e; a native date input renders the OS-native picker
// and is fully accessible without JS; (2) skips a new dependency +
// its transitive install; (3) trivially testable via Vitest ``change``
// events; (4) native picker respects the browser locale automatically.
// If operator evidence surfaces the need for a richer picker (multi-
// month, range, presets), swap in shadcn Calendar at that time.
//
// The emitted value is the ISO date-string ``YYYY-MM-DD`` — the caller
// converts to a full ISO timestamp (end-of-day tenant-local) before
// hitting the backend.

import { Input } from "@/components/ui/input";

interface TrialBalanceDatePickerProps {
  /** ISO date-string ``YYYY-MM-DD``. */
  value: string;
  onChange: (value: string) => void;
  /** Optional id for the label ↔ input association. */
  id?: string;
  /** Optional label. Defaults to "As of". */
  label?: string;
  /** Disables the input during network activity. */
  disabled?: boolean;
}

/** Returns today's date as an ISO date-string ``YYYY-MM-DD``. */
export function todayIsoDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Converts an ISO date-string ``YYYY-MM-DD`` to a full ISO timestamp
 * at the end of that day in the browser's local timezone. Matches
 * the operational convention of "reports as of end-of-business."
 * Backend accepts any ISO string per M13.3 ``TrialBalanceQuerySerializer``.
 */
export function dateToEndOfDayIso(dateIso: string): string {
  const [year, month, day] = dateIso.split("-").map(Number);
  // Local end-of-day. Constructing with day-1 and calling setHours
  // wraps around DST cleanly.
  const dt = new Date(year, month - 1, day, 23, 59, 59, 0);
  return dt.toISOString();
}

export function TrialBalanceDatePicker({
  value,
  onChange,
  id = "trial-balance-as-of",
  label = "As of",
  disabled = false,
}: TrialBalanceDatePickerProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <Input
        id={id}
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        aria-label={label}
        className="w-44"
      />
    </div>
  );
}
