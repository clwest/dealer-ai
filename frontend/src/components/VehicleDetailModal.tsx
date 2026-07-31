import { useEffect, useState } from "react";
import {
  CheckCircle2,
  CircleDollarSign,
  Gauge,
  Loader2,
  Send,
  Sparkles,
  X,
  Zap,
} from "lucide-react";

import {
  askVehicleQuestion,
  fetchVehicleDetail,
  type PaymentEstimate,
  type Vehicle,
  type VehicleDetailResponse,
} from "@/lib/api";
import { cn, formatCurrency } from "@/lib/utils";

interface Props {
  vehicleId: number | null;
  sessionId?: string | null;
  targetMonthly?: number | null;
  downPayment?: number | null;
  selected?: boolean;
  onClose: () => void;
  onToggleSelect?: (v: Vehicle) => void;
}

const SUGGESTED_QUESTIONS = [
  "Is this good for towing?",
  "Would this fit a $600/month budget?",
  "How does this compare to similar options?",
  "Is the new one worth it over a used model?",
];

export default function VehicleDetailModal({
  vehicleId,
  sessionId,
  targetMonthly,
  downPayment,
  selected,
  onClose,
  onToggleSelect,
}: Props) {
  const [detail, setDetail] = useState<VehicleDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);

  useEffect(() => {
    if (!vehicleId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setAnswer(null);
    setQuestion("");
    fetchVehicleDetail(vehicleId, {
      sessionId,
      targetMonthly: targetMonthly ?? null,
      downPayment: downPayment ?? null,
    })
      .then((d) => {
        if (!cancelled) setDetail(d);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load vehicle.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [vehicleId, sessionId, targetMonthly, downPayment]);

  if (vehicleId == null) return null;

  async function handleAsk(text?: string) {
    if (!vehicleId) return;
    const q = (text ?? question).trim();
    if (!q) return;
    setAsking(true);
    setAnswer(null);
    setError(null);
    try {
      const res = await askVehicleQuestion(vehicleId, {
        question: q,
        sessionId: sessionId ?? null,
        targetMonthly: targetMonthly ?? null,
        downPayment: downPayment ?? null,
      });
      setAnswer(res.answer);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to ask.");
    } finally {
      setAsking(false);
    }
  }

  const v = detail?.vehicle;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="card flex h-[90vh] w-full max-w-4xl flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div className="text-sm font-bold text-brand-ink">
            Vehicle details
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-brand-ink"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="grid gap-4 p-6 sm:grid-cols-2">
              <div className="h-56 animate-pulse rounded-lg bg-slate-100" />
              <div className="space-y-3">
                <div className="h-6 w-2/3 animate-pulse rounded bg-slate-100" />
                <div className="h-4 w-1/2 animate-pulse rounded bg-slate-100" />
                <div className="h-4 w-1/3 animate-pulse rounded bg-slate-100" />
                <div className="h-24 w-full animate-pulse rounded bg-slate-100" />
              </div>
            </div>
          )}

          {error && (
            <div className="m-6 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          {detail && v && (
            <div className="space-y-6 p-6">
              <div className="grid gap-6 sm:grid-cols-2">
                <div className="overflow-hidden rounded-lg bg-slate-100">
                  {v.image_url ? (
                    <img
                      src={v.image_url}
                      alt={v.display_name}
                      className="h-64 w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-64 w-full items-center justify-center text-slate-400">
                      No photo
                    </div>
                  )}
                </div>
                <div className="space-y-3">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-slate-500">
                      Stock #{v.stock_number}
                    </div>
                    <div className="text-xl font-bold text-brand-ink">
                      {v.display_name}
                    </div>
                  </div>
                  <div className="flex items-baseline gap-3">
                    <span className="text-2xl font-bold text-brand-blue">
                      {formatCurrency(v.price)}
                    </span>
                    {v.msrp && Number(v.msrp) > Number(v.price) && (
                      <span className="text-sm text-slate-400 line-through">
                        {formatCurrency(v.msrp)}
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-slate-700">
                    <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-2 py-1">
                      <Gauge className="h-3.5 w-3.5" />
                      {v.mileage.toLocaleString()} mi
                    </span>
                    {v.drivetrain && (
                      <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-2 py-1">
                        {v.drivetrain}
                      </span>
                    )}
                    {v.fuel_type && (
                      <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-2 py-1">
                        <Zap className="h-3.5 w-3.5" />
                        {v.fuel_type}
                      </span>
                    )}
                    {v.transmission && (
                      <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-2 py-1">
                        {v.transmission}
                      </span>
                    )}
                  </div>
                  {v.engine && (
                    <div className="text-xs text-slate-600">
                      <span className="font-semibold">Engine:</span> {v.engine}
                    </div>
                  )}
                  {v.exterior_color && (
                    <div className="text-xs text-slate-600">
                      <span className="font-semibold">Color:</span>{" "}
                      {v.exterior_color}
                      {v.interior_color ? ` / ${v.interior_color}` : ""}
                    </div>
                  )}
                  {v.features?.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {v.features.slice(0, 6).map((f) => (
                        <span
                          key={f}
                          className="rounded-md border border-slate-200 px-2 py-0.5 text-[11px] text-slate-600"
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  )}
                  {v.description && (
                    <p className="text-sm text-slate-700">{v.description}</p>
                  )}
                  {onToggleSelect && (
                    <button
                      type="button"
                      onClick={() => onToggleSelect(v)}
                      className={cn(
                        "btn-ghost mt-2 w-full justify-center",
                        selected &&
                          "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100",
                      )}
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      {selected
                        ? "Flagged for sales handoff"
                        : "Flag for sales handoff"}
                    </button>
                  )}
                </div>
              </div>

              {/* Payment table */}
              <section>
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-brand-ink">
                  <CircleDollarSign className="h-4 w-4" /> Payment estimates
                </h3>
                <div className="overflow-hidden rounded-lg border border-slate-200">
                  <table className="min-w-full text-sm">
                    <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-4 py-2 text-left">Term</th>
                        <th className="px-4 py-2 text-left">Down</th>
                        <th className="px-4 py-2 text-right">Estimated monthly</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {detail.payment_estimates.map((est: PaymentEstimate) => (
                        <tr key={est.term_months}>
                          <td className="px-4 py-2">{est.term_months} months</td>
                          <td className="px-4 py-2">
                            {formatCurrency(est.down_payment)}
                          </td>
                          <td className="px-4 py-2 text-right font-semibold">
                            {formatCurrency(est.monthly_payment)}/mo
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  W.A.C. — with approved credit. Estimates only; final rate and
                  terms depend on credit and lender approval.
                </p>
              </section>

              {/* Affordability notes */}
              {detail.affordability_notes.length > 0 && (
                <section>
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-brand-ink">
                    <Sparkles className="h-4 w-4" /> Affordability notes
                  </h3>
                  <ul className="space-y-2 text-sm text-slate-700">
                    {detail.affordability_notes.map((n: string) => (
                      <li
                        key={n}
                        className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2"
                      >
                        {n}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {/* Ask AI */}
              <section>
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-brand-ink">
                  <Sparkles className="h-4 w-4" /> Ask about this vehicle
                </h3>
                <div className="mb-3 flex flex-wrap gap-2">
                  {SUGGESTED_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => handleAsk(q)}
                      className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:bg-slate-50"
                      disabled={asking}
                    >
                      {q}
                    </button>
                  ))}
                </div>
                <form
                  className="flex items-center gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleAsk();
                  }}
                >
                  <input
                    className="input flex-1"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Ask anything about this vehicle…"
                    disabled={asking}
                  />
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={asking || !question.trim()}
                  >
                    {asking ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                    Ask
                  </button>
                </form>
                {answer && (
                  <div className="mt-3 rounded-lg bg-brand-mist p-4 text-sm leading-relaxed text-brand-ink">
                    {answer}
                  </div>
                )}
              </section>

              {/* Similar */}
              {detail.similar_vehicles.length > 0 && (
                <section>
                  <h3 className="mb-2 text-sm font-bold text-brand-ink">
                    Similar vehicles
                  </h3>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {detail.similar_vehicles.map((sv) => (
                      <div
                        key={sv.id}
                        className="flex gap-3 rounded-lg border border-slate-200 p-3"
                      >
                        {sv.image_url ? (
                          <img
                            src={sv.image_url}
                            alt={sv.display_name}
                            className="h-16 w-24 rounded object-cover"
                          />
                        ) : (
                          <div className="h-16 w-24 rounded bg-slate-100" />
                        )}
                        <div className="flex flex-col justify-between text-sm">
                          <div className="font-medium leading-tight">
                            {sv.display_name}
                          </div>
                          <div className="text-xs text-slate-500">
                            Stock #{sv.stock_number} · {sv.condition}
                          </div>
                          <div className="text-sm font-semibold text-brand-blue">
                            {formatCurrency(sv.price)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
