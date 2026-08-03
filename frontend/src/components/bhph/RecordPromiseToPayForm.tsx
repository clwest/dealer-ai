// Milestone 21 · Increment 2 (SESSION_168) — record-promise-to-pay form.
//
// Attaches to the Promises card in DealerAiBhphNoteDetail.tsx. Posts
// to POST /admin/bhph-notes/<pk>/promises/ via bhphApi.ts wrapper.
//
// Form fields match PromiseCreateRequestSerializer in
// backend/dealer_ai/views_bhph_promises.py: promised_at (datetime),
// promised_amount (decimal), promised_reason (enum), notes.

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/authFetch";
import {
  recordPromiseToPay,
  type BhphPromiseProjection,
  type BhphPromiseReason,
} from "@/lib/bhphApi";

const PROMISED_REASON_OPTIONS: { value: BhphPromiseReason; label: string }[] = [
  { value: "paycheck", label: "Next paycheck" },
  { value: "tax_refund", label: "Tax refund" },
  { value: "family_help", label: "Family help" },
  { value: "other", label: "Other" },
];

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) return "Invalid promise. Check the amount and date.";
    if (err.status === 404) return "Note not found. Refresh the page.";
    return `Server returned ${err.status}.`;
  }
  return "Failed to record promise-to-pay.";
}

function nowLocalDatetimeInput(): string {
  const now = new Date();
  const tzOffsetMinutes = now.getTimezoneOffset();
  const local = new Date(now.getTime() - tzOffsetMinutes * 60_000);
  return local.toISOString().slice(0, 16);
}

export interface RecordPromiseToPayFormProps {
  notePk: number;
  onRecorded: (promise: BhphPromiseProjection) => void;
}

export function RecordPromiseToPayForm({
  notePk,
  onRecorded,
}: RecordPromiseToPayFormProps) {
  const [promisedAt, setPromisedAt] = useState<string>(nowLocalDatetimeInput());
  const [promisedAmount, setPromisedAmount] = useState<string>("");
  const [promisedReason, setPromisedReason] = useState<BhphPromiseReason>("paycheck");
  const [notes, setNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!promisedAmount || Number(promisedAmount) <= 0) {
      setError("Promised amount must be greater than zero.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await recordPromiseToPay(notePk, {
        promised_at: new Date(promisedAt).toISOString(),
        promised_amount: promisedAmount,
        promised_reason: promisedReason,
        notes: notes.trim() || undefined,
      });
      onRecorded(res.bhph_promise);
      setPromisedAmount("");
      setNotes("");
      setPromisedAt(nowLocalDatetimeInput());
    } catch (err) {
      setError(humanizeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-col gap-3 rounded-md border border-border p-3"
      data-testid="record-ptp-form"
    >
      <div className="text-sm font-medium">Record a promise-to-pay</div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <label className="flex flex-col gap-1 text-xs">
          Promised at
          <Input
            type="datetime-local"
            value={promisedAt}
            onChange={(e) => setPromisedAt(e.target.value)}
            required
            data-testid="record-ptp-promised-at"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Amount ($)
          <Input
            type="number"
            step="0.01"
            value={promisedAmount}
            onChange={(e) => setPromisedAmount(e.target.value)}
            data-testid="record-ptp-amount"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Reason
          <select
            className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
            value={promisedReason}
            onChange={(e) =>
              setPromisedReason(e.target.value as BhphPromiseReason)
            }
            data-testid="record-ptp-reason"
          >
            {PROMISED_REASON_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="flex flex-col gap-1 text-xs">
        Notes (optional)
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          data-testid="record-ptp-notes"
        />
      </label>
      {error ? (
        <p className="text-xs text-destructive" data-testid="record-ptp-error">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end">
        <Button type="submit" disabled={submitting} data-testid="record-ptp-submit">
          {submitting ? "Recording…" : "Record promise"}
        </Button>
      </div>
    </form>
  );
}
