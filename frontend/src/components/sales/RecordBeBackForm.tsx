// Milestone 21 · Increment 3 (SESSION_169) — record-be-back form.
//
// Attaches to DealerAiSalesBeBacks.tsx above the queue table. Posts
// to POST /admin/be-backs/ via the createBeBack wrapper. Payload
// matches BeBackCreateRequestSerializer in
// backend/dealer_ai/views_be_backs.py:
//   lead_id, promised_at, promised_reason enum, notes.

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/authFetch";
import {
  createBeBack,
  type BeBackProjection,
  type BeBackReason,
} from "@/lib/salesApi";

const REASON_OPTIONS: { value: BeBackReason; label: string }[] = [
  { value: "test_drive", label: "Bring back for test drive" },
  { value: "bring_co_signer", label: "Bring co-signer" },
  { value: "bring_trade_in", label: "Bring trade-in" },
  { value: "other", label: "Other" },
];

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) return "Invalid be-back. Check the fields.";
    if (err.status === 404) return "Lead not found. Check the lead ID.";
    return `Server returned ${err.status}.`;
  }
  return "Failed to record be-back.";
}

function nowLocalDatetimeInput(): string {
  const now = new Date();
  const tzOffsetMinutes = now.getTimezoneOffset();
  const local = new Date(now.getTime() - tzOffsetMinutes * 60_000);
  return local.toISOString().slice(0, 16);
}

export interface RecordBeBackFormProps {
  onRecorded: (beBack: BeBackProjection) => void;
}

export function RecordBeBackForm({ onRecorded }: RecordBeBackFormProps) {
  const [leadIdText, setLeadIdText] = useState<string>("");
  const [promisedAt, setPromisedAt] = useState<string>(nowLocalDatetimeInput());
  const [promisedReason, setPromisedReason] =
    useState<BeBackReason>("test_drive");
  const [notes, setNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const leadId = Number(leadIdText);
    if (!Number.isFinite(leadId) || leadId <= 0) {
      setError("Enter a valid lead ID.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const beBack = await createBeBack({
        lead_id: leadId,
        promised_at: new Date(promisedAt).toISOString(),
        promised_reason: promisedReason,
        notes: notes.trim() || undefined,
      });
      onRecorded(beBack);
      setLeadIdText("");
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
      data-testid="record-be-back-form"
    >
      <div className="text-sm font-medium">Record a be-back</div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <label className="flex flex-col gap-1 text-xs">
          Lead ID
          <Input
            type="number"
            min="1"
            step="1"
            value={leadIdText}
            onChange={(e) => setLeadIdText(e.target.value)}
            placeholder="e.g. 42"
            data-testid="record-be-back-lead-id"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Promised at
          <Input
            type="datetime-local"
            value={promisedAt}
            onChange={(e) => setPromisedAt(e.target.value)}
            data-testid="record-be-back-promised-at"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Reason
          <select
            className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
            value={promisedReason}
            onChange={(e) =>
              setPromisedReason(e.target.value as BeBackReason)
            }
            data-testid="record-be-back-reason"
          >
            {REASON_OPTIONS.map((opt) => (
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
          data-testid="record-be-back-notes"
        />
      </label>
      {error ? (
        <p className="text-xs text-destructive" data-testid="record-be-back-error">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={submitting}
          data-testid="record-be-back-submit"
        >
          {submitting ? "Recording…" : "Record be-back"}
        </Button>
      </div>
    </form>
  );
}
