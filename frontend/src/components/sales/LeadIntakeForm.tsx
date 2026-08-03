// Milestone 24 · Increment 1 (SESSION_181) — shared sales intake form.
//
// Posts to POST /admin/leads/{walk-in|phone|referral}/ via the
// corresponding wrappers in `salesApi.ts` (createWalkInLead /
// createPhoneLead / createReferralLead). Field surface matches
// `_BaseIntakeSerializer` in backend/dealer_ai/views_leads.py:52-95
// (name / phone / email / notes / target_monthly_payment /
// down_payment / trade_in / credit_range / urgency). Referral adds
// a referring-customer picker via the `extras` slot below.
//
// Dispatch to the specific wrapper is delegated to the parent via
// the `onSubmit` callback so the form stays channel-agnostic and
// testable in isolation. Parent (DealerAiSalesLeads Dialog CTA
// handler) picks the wrapper based on the channel it wants.
//
// Not consumed for webhook. Webhook is a system-to-system boundary
// per M24 §5.b + §5.d (SESSION_180 redirect + SESSION_181 M24.1
// correction).
import { useState, type FormEvent, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/authFetch";
import type {
  CreateBaseLeadRequest,
  LeadProjection,
} from "@/lib/salesApi";

export type LeadIntakeChannel = "walk_in" | "phone" | "referral";

const URGENCY_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "— (unspecified)" },
  { value: "immediate", label: "Buying now" },
  { value: "this_week", label: "This week" },
  { value: "this_month", label: "This month" },
  { value: "researching", label: "Researching" },
];

const CHANNEL_LABEL: Record<LeadIntakeChannel, string> = {
  walk_in: "walk-in",
  phone: "phone",
  referral: "referral",
};

function humanizeError(err: unknown, channel: LeadIntakeChannel): string {
  if (err instanceof ApiError) {
    if (err.status === 400) {
      return "Invalid intake fields. Check the required fields and try again.";
    }
    if (err.status === 404 && channel === "referral") {
      return "Referring customer not found. Pick a customer from your dealership.";
    }
    return `Server returned ${err.status}.`;
  }
  return `Failed to record ${CHANNEL_LABEL[channel]} lead.`;
}

export interface LeadIntakeFormProps {
  /** Channel constant, used for wrapper dispatch + error copy. */
  channel: LeadIntakeChannel;
  /**
   * Dispatched by the parent — picks the specific wrapper
   * (createWalkInLead / createPhoneLead / createReferralLead)
   * based on `channel`, and (for referral) attaches any extras
   * captured via the `extras` slot.
   */
  onSubmit: (payload: CreateBaseLeadRequest) => Promise<LeadProjection>;
  /** Fires after successful create. Parent opens LeadDetailModal. */
  onCreated: (lead: LeadProjection) => void;
  /**
   * Channel-specific extras (referring-customer picker for
   * referral; nothing for walk-in / phone). Rendered inside the
   * form so the extras submit alongside the base fields.
   */
  extras?: ReactNode;
}

export function LeadIntakeForm({
  channel,
  onSubmit,
  onCreated,
  extras,
}: LeadIntakeFormProps) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [targetMonthlyPayment, setTargetMonthlyPayment] = useState("");
  const [downPayment, setDownPayment] = useState("");
  const [tradeIn, setTradeIn] = useState("");
  const [creditRange, setCreditRange] = useState("");
  const [urgency, setUrgency] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setName("");
    setPhone("");
    setEmail("");
    setNotes("");
    setTargetMonthlyPayment("");
    setDownPayment("");
    setTradeIn("");
    setCreditRange("");
    setUrgency("");
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Customer name is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload: CreateBaseLeadRequest = {
        name: name.trim(),
        phone: phone.trim() || undefined,
        email: email.trim() || undefined,
        notes: notes.trim() || undefined,
        target_monthly_payment: targetMonthlyPayment.trim() || undefined,
        down_payment: downPayment.trim() || undefined,
        trade_in: tradeIn.trim() || undefined,
        credit_range: creditRange.trim() || undefined,
        urgency: (urgency as CreateBaseLeadRequest["urgency"]) || undefined,
      };
      const lead = await onSubmit(payload);
      onCreated(lead);
      reset();
    } catch (err) {
      setError(humanizeError(err, channel));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-3"
      data-testid={`lead-intake-form-${channel}`}
    >
      <label className="flex flex-col gap-1 text-xs">
        Customer name
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Full name"
          data-testid={`lead-intake-${channel}-name`}
          autoFocus
          required
        />
      </label>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs">
          Phone
          <Input
            type="tel"
            inputMode="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="555-0100"
            data-testid={`lead-intake-${channel}-phone`}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Email
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="customer@example.com"
            data-testid={`lead-intake-${channel}-email`}
          />
        </label>
      </div>
      <label className="flex flex-col gap-1 text-xs">
        Notes
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Any context worth capturing (interested vehicles, timing, etc.)"
          className="min-h-[64px] rounded-md border border-input bg-background px-3 py-2 text-sm"
          data-testid={`lead-intake-${channel}-notes`}
        />
      </label>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <label className="flex flex-col gap-1 text-xs">
          Target monthly payment ($)
          <Input
            type="number"
            step="0.01"
            inputMode="decimal"
            value={targetMonthlyPayment}
            onChange={(e) => setTargetMonthlyPayment(e.target.value)}
            placeholder="450"
            data-testid={`lead-intake-${channel}-target-monthly-payment`}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Down payment ($)
          <Input
            type="number"
            step="0.01"
            inputMode="decimal"
            value={downPayment}
            onChange={(e) => setDownPayment(e.target.value)}
            placeholder="3000"
            data-testid={`lead-intake-${channel}-down-payment`}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Credit range
          <Input
            value={creditRange}
            onChange={(e) => setCreditRange(e.target.value)}
            placeholder="good / fair / rebuilding"
            data-testid={`lead-intake-${channel}-credit-range`}
          />
        </label>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs">
          Trade-in
          <Input
            value={tradeIn}
            onChange={(e) => setTradeIn(e.target.value)}
            placeholder="2018 Civic 82k"
            data-testid={`lead-intake-${channel}-trade-in`}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Urgency
          <select
            className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
            value={urgency}
            onChange={(e) => setUrgency(e.target.value)}
            data-testid={`lead-intake-${channel}-urgency`}
          >
            {URGENCY_OPTIONS.map((opt) => (
              <option key={opt.value || "any"} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {extras}
      {error ? (
        <p
          className="text-xs text-destructive"
          role="alert"
          data-testid={`lead-intake-${channel}-error`}
        >
          {error}
        </p>
      ) : null}
      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={submitting}
          data-testid={`lead-intake-${channel}-submit`}
        >
          {submitting ? "Recording…" : "Record lead"}
        </Button>
      </div>
    </form>
  );
}
