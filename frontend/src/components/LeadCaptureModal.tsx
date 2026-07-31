import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";

import type { LeadInput, Vehicle } from "@/lib/api";
import { useBrand } from "@/lib/brand";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (lead: LeadInput) => Promise<void>;
  interestedVehicles?: Vehicle[];
  defaultName?: string;
  defaultEmail?: string;
  defaultPhone?: string;
}

const URGENCY_OPTIONS = [
  { value: "immediate", label: "Buying now" },
  { value: "this_week", label: "This week" },
  { value: "this_month", label: "This month" },
  { value: "researching", label: "Just researching" },
];

export default function LeadCaptureModal({
  open,
  onClose,
  onSubmit,
  interestedVehicles = [],
  defaultName = "",
  defaultEmail = "",
  defaultPhone = "",
}: Props) {
  const brand = useBrand();
  const [name, setName] = useState(defaultName);
  const [phone, setPhone] = useState(defaultPhone);
  const [email, setEmail] = useState(defaultEmail);
  const [targetMonthly, setTargetMonthly] = useState("");
  const [downPayment, setDownPayment] = useState("");
  const [tradeIn, setTradeIn] = useState("");
  const [urgency, setUrgency] = useState("this_week");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setName(defaultName);
      setPhone(defaultPhone);
      setEmail(defaultEmail);
      setError(null);
    }
  }, [open, defaultName, defaultPhone, defaultEmail]);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Please enter your name.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        name: name.trim(),
        phone: phone.trim() || undefined,
        email: email.trim() || undefined,
        target_monthly_payment: targetMonthly
          ? Number(targetMonthly)
          : undefined,
        down_payment: downPayment ? Number(downPayment) : undefined,
        trade_in: tradeIn.trim() || undefined,
        urgency: urgency || undefined,
        interested_vehicles: interestedVehicles.map((v) => v.id),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="card w-full max-w-lg p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-lg font-bold text-ford-ink">
              {`Connect with a ${brand.dealershipName} advisor`}
            </div>
            <div className="mt-1 text-sm text-slate-500">
              We'll prepare a real quote and reach out shortly.
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-ford-ink"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs font-semibold text-slate-600">
                Name *
              </span>
              <input
                className="input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-semibold text-slate-600">
                Phone
              </span>
              <input
                className="input"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="(405) 555-0199"
              />
            </label>
          </div>

          <label className="block">
            <span className="mb-1 block text-xs font-semibold text-slate-600">
              Email
            </span>
            <input
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </label>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs font-semibold text-slate-600">
                Target monthly payment (USD)
              </span>
              <input
                className="input"
                type="number"
                inputMode="decimal"
                value={targetMonthly}
                onChange={(e) => setTargetMonthly(e.target.value)}
                placeholder="650"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-semibold text-slate-600">
                Down payment (USD)
              </span>
              <input
                className="input"
                type="number"
                inputMode="decimal"
                value={downPayment}
                onChange={(e) => setDownPayment(e.target.value)}
                placeholder="5000"
              />
            </label>
          </div>

          <label className="block">
            <span className="mb-1 block text-xs font-semibold text-slate-600">
              Trade-in (year/make/model + condition)
            </span>
            <input
              className="input"
              value={tradeIn}
              onChange={(e) => setTradeIn(e.target.value)}
              placeholder="2018 SUV, ~75,000 miles, good condition"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-xs font-semibold text-slate-600">
              Timing
            </span>
            <select
              className="input"
              value={urgency}
              onChange={(e) => setUrgency(e.target.value)}
            >
              {URGENCY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>

          {interestedVehicles.length > 0 && (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
              <div className="mb-1 font-semibold text-slate-700">
                We'll attach interest in:
              </div>
              <ul className="list-disc pl-4">
                {interestedVehicles.map((v) => (
                  <li key={v.id}>
                    {v.display_name} (Stock #{v.stock_number})
                  </li>
                ))}
              </ul>
            </div>
          )}

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={submitting}
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Submit to sales
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
