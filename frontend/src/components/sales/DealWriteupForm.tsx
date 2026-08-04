// Milestone 32 · Increment 2 (SESSION_208) — deal-writeup four-square form.
//
// Posts to POST /admin/deal-writeups/ via createDealWriteup (M11.3
// backend verb; M32.2 first-UI wrapper). Field surface matches
// DealWriteupCreateRequestSerializer in backend/dealer_ai/views_deal_writeups.py:77-102 —
// required lead_id + vehicle_id (lead_id passed by parent); optional
// four-square terms (vehicle_price, trade_allowance, down_payment,
// monthly_payment_target, term_months_target, apr_target), write_up_at,
// notes.
//
// Vehicle picker per MILESTONE_32_PLANNING.md §5.b D4-revised² — reuses
// the M25.2 RecordTestDriveForm picker pattern (`listAdminVehicles`
// with search + suggested + all-inventory zones). Same operator mental
// model, same discovery surface.
//
// Manager-only by transitivity: the parent LeadDetailModal requires
// sales_manager or dealer_owner via `admin_lead_detail` gate
// (backend/dealer_ai/views.py:847-848). Advisors cannot open the
// modal at all; no visible-but-disabled treatment is required.

import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/authFetch";
import {
  createDealWriteup,
  listAdminVehicles,
  type AdminVehicleRow,
  type CreateDealWriteupRequest,
  type DealWriteupProjection,
} from "@/lib/salesApi";

export interface DealWriteupFormSuggestedVehicle {
  id: number;
  stock_number: string;
  display_name: string;
  price: string | number;
  image_url?: string;
}

export interface DealWriteupFormProps {
  leadId: number;
  suggestedVehicles?: DealWriteupFormSuggestedVehicle[];
  onCreated: (writeup: DealWriteupProjection) => void;
  onCancel?: () => void;
  /** Injected for tests. Defaults to shipped `listAdminVehicles`. */
  loadInventory?: typeof listAdminVehicles;
  /** Injected for tests. Defaults to shipped `createDealWriteup`. */
  submit?: typeof createDealWriteup;
}

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) {
      return "Invalid writeup fields. Check the picker + terms and try again.";
    }
    if (err.status === 404) {
      return "Lead or vehicle not found in your dealership.";
    }
    if (err.status === 403) {
      return "Only sales managers or dealer owners can create writeups.";
    }
    return `Server returned ${err.status}.`;
  }
  return "Failed to create the deal writeup.";
}

function decimalOrUndefined(raw: string): string | undefined {
  const trimmed = raw.trim();
  if (!trimmed) return undefined;
  const num = Number(trimmed);
  if (!Number.isFinite(num)) return undefined;
  return num.toFixed(2);
}

function intOrUndefined(raw: string): number | undefined {
  const trimmed = raw.trim();
  if (!trimmed) return undefined;
  const num = Number(trimmed);
  if (!Number.isFinite(num) || !Number.isInteger(num) || num < 1) {
    return undefined;
  }
  return num;
}

export function DealWriteupForm({
  leadId,
  suggestedVehicles = [],
  onCreated,
  onCancel,
  loadInventory = listAdminVehicles,
  submit = createDealWriteup,
}: DealWriteupFormProps) {
  const [vehicleId, setVehicleId] = useState<number | null>(null);
  const [inventory, setInventory] = useState<AdminVehicleRow[]>([]);
  const [inventoryState, setInventoryState] = useState<
    "idle" | "loading" | "ready" | "error"
  >("idle");
  const [search, setSearch] = useState("");
  const [vehiclePrice, setVehiclePrice] = useState("");
  const [tradeAllowance, setTradeAllowance] = useState("");
  const [downPayment, setDownPayment] = useState("");
  const [monthlyPaymentTarget, setMonthlyPaymentTarget] = useState("");
  const [termMonthsTarget, setTermMonthsTarget] = useState("");
  const [aprTarget, setAprTarget] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setInventoryState("loading");
    const timer = window.setTimeout(
      () => {
        loadInventory(search ? { search } : {})
          .then((res) => {
            if (cancelled) return;
            setInventory(res.results);
            setInventoryState("ready");
          })
          .catch(() => {
            if (cancelled) return;
            setInventoryState("error");
          });
      },
      search ? 200 : 0,
    );
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [search, loadInventory]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (vehicleId == null) {
      setError("Pick a vehicle before recording the writeup.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload: CreateDealWriteupRequest = {
        lead_id: leadId,
        vehicle_id: vehicleId,
        vehicle_price: decimalOrUndefined(vehiclePrice) ?? null,
        trade_allowance: decimalOrUndefined(tradeAllowance) ?? null,
        down_payment: decimalOrUndefined(downPayment) ?? null,
        monthly_payment_target:
          decimalOrUndefined(monthlyPaymentTarget) ?? null,
        term_months_target: intOrUndefined(termMonthsTarget) ?? null,
        apr_target: decimalOrUndefined(aprTarget) ?? null,
        notes: notes.trim() || undefined,
      };
      const writeup = await submit(payload);
      onCreated(writeup);
      // Reset for a follow-on writeup on the same lead.
      setVehicleId(null);
      setVehiclePrice("");
      setTradeAllowance("");
      setDownPayment("");
      setMonthlyPaymentTarget("");
      setTermMonthsTarget("");
      setAprTarget("");
      setNotes("");
    } catch (err) {
      setError(humanizeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  const needle = search.trim().toLowerCase();
  const suggestedFiltered = suggestedVehicles.filter((v) => {
    if (!needle) return true;
    return (
      v.display_name.toLowerCase().includes(needle) ||
      v.stock_number.toLowerCase().includes(needle)
    );
  });
  const suggestedIds = new Set(suggestedFiltered.map((v) => v.id));
  const inventoryFiltered = inventory.filter((v) => !suggestedIds.has(v.id));

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-3"
      data-testid="deal-writeup-form"
    >
      <label className="flex flex-col gap-1 text-xs">
        Search inventory
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Stock #, year, make, model, or trim"
          data-testid="deal-writeup-search"
        />
      </label>

      <div className="max-h-52 overflow-y-auto rounded-md border border-slate-200 bg-white">
        {suggestedFiltered.length > 0 ? (
          <div data-testid="deal-writeup-suggested-zone">
            <div className="border-b border-slate-100 bg-slate-50 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
              Suggested for this lead
            </div>
            <ul>
              {suggestedFiltered.map((v) => (
                <li key={`sug-${v.id}`}>
                  <button
                    type="button"
                    onClick={() => setVehicleId(v.id)}
                    data-testid={`deal-writeup-vehicle-${v.id}`}
                    className={`flex w-full items-center justify-between gap-2 border-b border-slate-100 px-3 py-2 text-left text-sm hover:bg-brand-mist/40 ${
                      vehicleId === v.id
                        ? "bg-brand-mist/60 font-semibold text-brand-ink"
                        : "text-slate-700"
                    }`}
                  >
                    <span>
                      {v.display_name}{" "}
                      <span className="text-xs text-slate-500">
                        · #{v.stock_number}
                      </span>
                    </span>
                    <span className="text-xs text-slate-500">${v.price}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <div data-testid="deal-writeup-inventory-zone">
          <div className="border-b border-slate-100 bg-slate-50 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            All inventory
          </div>
          {inventoryState === "loading" ? (
            <p className="px-3 py-3 text-xs text-slate-500">Loading…</p>
          ) : null}
          {inventoryState === "error" ? (
            <p
              className="px-3 py-3 text-xs text-destructive"
              role="alert"
              data-testid="deal-writeup-inventory-error"
            >
              Failed to load inventory.
            </p>
          ) : null}
          {inventoryState === "ready" && inventoryFiltered.length === 0 ? (
            <p
              className="px-3 py-3 text-xs text-slate-500"
              data-testid="deal-writeup-inventory-empty"
            >
              No vehicles match.
            </p>
          ) : null}
          {inventoryState === "ready" && inventoryFiltered.length > 0 ? (
            <ul>
              {inventoryFiltered.map((v) => (
                <li key={`inv-${v.id}`}>
                  <button
                    type="button"
                    onClick={() => setVehicleId(v.id)}
                    data-testid={`deal-writeup-vehicle-${v.id}`}
                    className={`flex w-full items-center justify-between gap-2 border-b border-slate-100 px-3 py-2 text-left text-sm hover:bg-brand-mist/40 ${
                      vehicleId === v.id
                        ? "bg-brand-mist/60 font-semibold text-brand-ink"
                        : "text-slate-700"
                    }`}
                  >
                    <span>
                      {v.display_name}{" "}
                      <span className="text-xs text-slate-500">
                        · #{v.stock_number} · {v.condition}
                      </span>
                    </span>
                    <span className="text-xs text-slate-500">${v.price}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs">
          Vehicle price ($)
          <Input
            type="number"
            inputMode="decimal"
            step="0.01"
            value={vehiclePrice}
            onChange={(e) => setVehiclePrice(e.target.value)}
            placeholder="28500.00"
            data-testid="deal-writeup-vehicle-price"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Trade allowance ($)
          <Input
            type="number"
            inputMode="decimal"
            step="0.01"
            value={tradeAllowance}
            onChange={(e) => setTradeAllowance(e.target.value)}
            placeholder="4500.00"
            data-testid="deal-writeup-trade-allowance"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Down payment ($)
          <Input
            type="number"
            inputMode="decimal"
            step="0.01"
            value={downPayment}
            onChange={(e) => setDownPayment(e.target.value)}
            placeholder="2000.00"
            data-testid="deal-writeup-down-payment"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Monthly payment target ($)
          <Input
            type="number"
            inputMode="decimal"
            step="0.01"
            value={monthlyPaymentTarget}
            onChange={(e) => setMonthlyPaymentTarget(e.target.value)}
            placeholder="450.00"
            data-testid="deal-writeup-monthly-payment-target"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Term (months)
          <Input
            type="number"
            inputMode="numeric"
            value={termMonthsTarget}
            onChange={(e) => setTermMonthsTarget(e.target.value)}
            placeholder="72"
            data-testid="deal-writeup-term-months-target"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          APR target (%)
          <Input
            type="number"
            inputMode="decimal"
            step="0.01"
            value={aprTarget}
            onChange={(e) => setAprTarget(e.target.value)}
            placeholder="7.49"
            data-testid="deal-writeup-apr-target"
          />
        </label>
      </div>
      <label className="flex flex-col gap-1 text-xs">
        Notes
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Deal-specific context, promises, contingencies…"
          className="min-h-[48px] rounded-md border border-input bg-background px-3 py-2 text-sm"
          data-testid="deal-writeup-notes"
        />
      </label>

      {error ? (
        <p
          className="text-xs text-destructive"
          role="alert"
          data-testid="deal-writeup-error"
        >
          {error}
        </p>
      ) : null}
      <div className="flex justify-end gap-2">
        {onCancel ? (
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            data-testid="deal-writeup-cancel"
          >
            Cancel
          </Button>
        ) : null}
        <Button
          type="submit"
          disabled={submitting || vehicleId == null}
          data-testid="deal-writeup-submit"
        >
          {submitting ? "Recording…" : "Record writeup"}
        </Button>
      </div>
    </form>
  );
}
