// Milestone 23 · Increment 3 (SESSION_178) — BHPH payment intake form.
//
// Posts to POST /admin/bhph-notes/<pk>/payments/ via the
// `createBhphPayment` wrapper. Form fields match
// BhphPaymentCreateRequestSerializer in
// backend/dealer_ai/views_bhph_payments.py: paid_at (datetime),
// amount (decimal), method (enum from BHPH_PAYMENT_METHOD_CHOICES).
//
// Attached inline to the Payments card on
// DealerAiBhphNoteDetail.tsx, matching the sibling M21.2 pattern
// (RecordPromiseToPayForm inline in Promises card).
//
// Following M23.2 §5.d gap-fix lesson — no HTML5 validation attrs
// that short-circuit onSubmit. JS validation governs.

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/authFetch";
import {
  createBhphPayment,
  type BhphPaymentMethod,
  type BhphPaymentProjection,
} from "@/lib/bhphApi";

const PAYMENT_METHOD_OPTIONS: {
  value: BhphPaymentMethod;
  label: string;
}[] = [
  { value: "cash", label: "Cash" },
  { value: "check", label: "Check" },
  { value: "debit", label: "Debit card" },
  { value: "ach", label: "ACH" },
  { value: "other", label: "Other" },
];

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) {
      return "Invalid payment. Check the amount, method, and paid-at timestamp.";
    }
    if (err.status === 404) {
      return "Note not found. Refresh the page.";
    }
    return `Server returned ${err.status}.`;
  }
  return "Failed to record payment.";
}

function nowLocalDatetimeInput(): string {
  const now = new Date();
  const tzOffsetMinutes = now.getTimezoneOffset();
  const local = new Date(now.getTime() - tzOffsetMinutes * 60_000);
  return local.toISOString().slice(0, 16);
}

export interface RecordBhphPaymentFormProps {
  notePk: number;
  onRecorded: (payment: BhphPaymentProjection) => void;
}

export function RecordBhphPaymentForm({
  notePk,
  onRecorded,
}: RecordBhphPaymentFormProps) {
  const [paidAt, setPaidAt] = useState<string>(nowLocalDatetimeInput());
  const [amount, setAmount] = useState<string>("");
  const [method, setMethod] = useState<BhphPaymentMethod>("cash");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!amount || Number(amount) <= 0) {
      setError("Payment amount must be greater than zero.");
      return;
    }
    if (!paidAt) {
      setError("Paid-at timestamp is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await createBhphPayment(notePk, {
        paid_at: new Date(paidAt).toISOString(),
        amount,
        method,
      });
      onRecorded(res.bhph_payment);
      setAmount("");
      setPaidAt(nowLocalDatetimeInput());
      setMethod("cash");
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
      data-testid="record-bhph-payment-form"
    >
      <div className="text-sm font-medium">Record a payment</div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <label className="flex flex-col gap-1 text-xs">
          Paid at
          <Input
            type="datetime-local"
            value={paidAt}
            onChange={(e) => setPaidAt(e.target.value)}
            data-testid="record-bhph-payment-paid-at"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Amount ($)
          <Input
            type="number"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            data-testid="record-bhph-payment-amount"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Method
          <select
            className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
            value={method}
            onChange={(e) =>
              setMethod(e.target.value as BhphPaymentMethod)
            }
            data-testid="record-bhph-payment-method"
          >
            {PAYMENT_METHOD_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error ? (
        <p
          className="text-xs text-destructive"
          role="alert"
          data-testid="record-bhph-payment-error"
        >
          {error}
        </p>
      ) : null}
      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={submitting}
          data-testid="record-bhph-payment-submit"
        >
          {submitting ? "Recording…" : "Record payment"}
        </Button>
      </div>
    </form>
  );
}
