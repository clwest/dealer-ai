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
// resolves the store's zone (via ``useBrand`` + ``lib/storeTime``) and
// converts to a full ISO timestamp before hitting the backend.
// SESSION_244 (walk finding 53): the "today" default + end-of-day
// conversion used to live here in the browser's zone. They moved to
// ``lib/storeTime`` and now key off the store's IANA zone so freezing
// "as of today" from a laptop east of the store no longer truncates
// the last hour of the store's business day.

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
