// Milestone 23 · Increment 2 (SESSION_177) — BHPH note origination form.
//
// Posts to POST /admin/bhph-notes/ via the `createBhphNote` wrapper.
// Form fields match BhphNoteCreateRequestSerializer in
// backend/dealer_ai/views_bhph_notes.py: sale_id (int),
// principal_financed (decimal), apr (decimal), term_weeks (int),
// payment_frequency (enum), first_payment_due (date),
// default_grace_days (optional int, default 5).
//
// The sale_id is a manual numeric input rather than a picker
// because no admin sale-list endpoint ships today. Real operator UX
// improvement (sale picker, deep-link from VehicleSalePage) is
// recorded in M23 §3 deferral 1 + retrospective §9 as evidence-
// based candidate for M24+ consideration.

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/authFetch";
import {
  createBhphNote,
  type BhphNoteProjection,
  type BhphPaymentFrequency,
} from "@/lib/bhphApi";

const PAYMENT_FREQUENCY_OPTIONS: {
  value: BhphPaymentFrequency;
  label: string;
}[] = [
  { value: "weekly", label: "Weekly" },
  { value: "biweekly", label: "Biweekly" },
  { value: "semi_monthly", label: "Semi-monthly" },
];

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) {
      return "Invalid note terms. Check sale ID, principal, APR, term, and cadence.";
    }
    if (err.status === 404) {
      return "Sale not found. The sale must exist and belong to this dealership.";
    }
    if (err.status === 409) {
      return "This sale already has a BHPH note — only one note per sale is allowed.";
    }
    return `Server returned ${err.status}.`;
  }
  return "Failed to originate BHPH note.";
}

function todayIsoDate(): string {
  const now = new Date();
  const tzOffsetMinutes = now.getTimezoneOffset();
  const local = new Date(now.getTime() - tzOffsetMinutes * 60_000);
  return local.toISOString().slice(0, 10);
}

export interface RecordBhphNoteFormProps {
  onOriginated: (note: BhphNoteProjection) => void;
  /** Optional initial sale_id, e.g. from a deep-link. Defaults to blank. */
  initialSaleId?: number;
}

export function RecordBhphNoteForm({
  onOriginated,
  initialSaleId,
}: RecordBhphNoteFormProps) {
  const [saleId, setSaleId] = useState<string>(
    initialSaleId !== undefined ? String(initialSaleId) : "",
  );
  const [principal, setPrincipal] = useState<string>("");
  const [apr, setApr] = useState<string>("");
  const [termWeeks, setTermWeeks] = useState<string>("52");
  const [frequency, setFrequency] = useState<BhphPaymentFrequency>("weekly");
  const [firstPaymentDue, setFirstPaymentDue] = useState<string>(todayIsoDate());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const saleIdNum = Number(saleId);
    if (!saleId || !Number.isInteger(saleIdNum) || saleIdNum <= 0) {
      setError("Sale ID must be a positive integer.");
      return;
    }
    if (!principal || Number(principal) <= 0) {
      setError("Principal must be greater than zero.");
      return;
    }
    if (!apr || Number(apr) < 0) {
      setError("APR must be zero or greater.");
      return;
    }
    const termWeeksNum = Number(termWeeks);
    if (!Number.isInteger(termWeeksNum) || termWeeksNum < 1) {
      setError("Term weeks must be a positive integer.");
      return;
    }
    if (!firstPaymentDue) {
      setError("First payment date is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await createBhphNote({
        sale_id: saleIdNum,
        principal_financed: principal,
        apr,
        term_weeks: termWeeksNum,
        payment_frequency: frequency,
        first_payment_due: firstPaymentDue,
      });
      onOriginated(res.bhph_note);
      // Reset the form so it's ready for another origination.
      setSaleId("");
      setPrincipal("");
      setApr("");
      setTermWeeks("52");
      setFrequency("weekly");
      setFirstPaymentDue(todayIsoDate());
    } catch (err) {
      setError(humanizeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-col gap-3"
      data-testid="record-bhph-note-form"
    >
      <label className="flex flex-col gap-1 text-xs">
        Sale ID
        <Input
          type="number"
          inputMode="numeric"
          step={1}
          value={saleId}
          onChange={(e) => setSaleId(e.target.value)}
          placeholder="e.g. 42"
          data-testid="record-bhph-note-sale-id"
        />
        <span className="text-muted-foreground">
          The BHPH-marked sale to originate this note against.
        </span>
      </label>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <label className="flex flex-col gap-1 text-xs">
          Principal financed ($)
          <Input
            type="number"
            step="0.01"
            value={principal}
            onChange={(e) => setPrincipal(e.target.value)}
            data-testid="record-bhph-note-principal"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          APR (%)
          <Input
            type="number"
            step="0.01"
            value={apr}
            onChange={(e) => setApr(e.target.value)}
            data-testid="record-bhph-note-apr"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Term (weeks)
          <Input
            type="number"
            step={1}
            value={termWeeks}
            onChange={(e) => setTermWeeks(e.target.value)}
            data-testid="record-bhph-note-term-weeks"
          />
        </label>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs">
          Payment cadence
          <select
            className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
            value={frequency}
            onChange={(e) =>
              setFrequency(e.target.value as BhphPaymentFrequency)
            }
            data-testid="record-bhph-note-frequency"
          >
            {PAYMENT_FREQUENCY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs">
          First payment due
          <Input
            type="date"
            value={firstPaymentDue}
            onChange={(e) => setFirstPaymentDue(e.target.value)}
            data-testid="record-bhph-note-first-payment-due"
          />
        </label>
      </div>
      {error ? (
        <p
          className="text-xs text-destructive"
          role="alert"
          data-testid="record-bhph-note-error"
        >
          {error}
        </p>
      ) : null}
      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={submitting}
          data-testid="record-bhph-note-submit"
        >
          {submitting ? "Originating…" : "Originate note"}
        </Button>
      </div>
    </form>
  );
}
