// Milestone 2 · Increment 7 — Vehicle investment ledger operator page.
//
// Consumes the M2.6 admin API contract (see SESSION_052 handoff):
//
//   GET  /admin/vehicles/<stock>/ledger/       — full read
//   POST /admin/vehicles/<stock>/acquisition/  — upsert
//   POST /admin/vehicles/<stock>/costs/        — post immutable row
//
// Money handling: every dollar figure travels as a two-decimal-place
// string on the wire and stays a string in this component. The
// backend is the authoritative source for every total; the frontend
// NEVER recomputes totals, projected_gross, or category rollups —
// M2.2 owns the "actual vs. estimated" semantic contract and this
// page displays what the backend returns verbatim.
//
// Corrections are reversing entries per the ledger's immutable-cost
// invariant (planning §1.6 design note; no PUT/PATCH/DELETE routes
// exist on the M2.6 API surface). The Add-cost form permits negative
// amounts for that pattern.

import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, PencilLine, Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/lib/AuthContext";
import {
  ApiError,
  ForbiddenError,
  UnauthenticatedError,
} from "@/lib/authFetch";
import {
  ACQUISITION_SOURCE_CHOICES,
  COST_CATEGORY_CHOICES,
  createVehicleCost,
  fetchVehicleLedger,
  upsertVehicleAcquisition,
  type AcquisitionSource,
  type AcquisitionUpsertPayload,
  type CostCategoryGroup,
  type CostCreatePayload,
  type LedgerAcquisition,
  type LedgerCost,
  type VehicleLedgerResponse,
} from "@/lib/api";

const WRITE_ROLES = ["dealer_owner", "sales_manager"];

const CATEGORY_GROUP_LABEL: Record<CostCategoryGroup, string> = {
  flooring: "Flooring",
  recon: "Reconditioning",
  administrative: "Administrative",
  photography: "Photography",
};

// Aging-bucket colors for the days-in-inventory badge. Display-only
// per the SESSION_053 brief — no aging recommendations, no alerts.
function daysInInventoryBadgeClass(days: number | null): string {
  if (days === null) return "bg-slate-100 text-slate-700 border-slate-200";
  if (days <= 30) return "bg-emerald-100 text-emerald-800 border-emerald-200";
  if (days <= 60) return "bg-yellow-100 text-yellow-800 border-yellow-200";
  if (days <= 90) return "bg-orange-100 text-orange-800 border-orange-200";
  return "bg-rose-100 text-rose-800 border-rose-200";
}

function formatMoney(value: string): string {
  // The backend already sends fixed two-decimal-place strings; we
  // just need to add a thousands separator + dollar sign for display.
  // Never parse through Number for arithmetic — this is display-only
  // string manipulation.
  const negative = value.startsWith("-");
  const bare = negative ? value.slice(1) : value;
  const [whole = "0", frac = "00"] = bare.split(".");
  const withCommas = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${negative ? "−" : ""}$${withCommas}.${frac}`;
}

function formatDate(iso: string): string {
  // ISO YYYY-MM-DD or full datetime → user-facing MMM D, YYYY.
  const asDate = new Date(iso);
  if (Number.isNaN(asDate.getTime())) return iso;
  return asDate.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatDateTime(iso: string): string {
  const asDate = new Date(iso);
  if (Number.isNaN(asDate.getTime())) return iso;
  return asDate.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

type LoadError =
  | { kind: "unauthenticated" }
  | { kind: "forbidden" }
  | { kind: "not_found" }
  | { kind: "other"; message: string };

function classifyError(err: unknown): LoadError {
  if (err instanceof UnauthenticatedError) return { kind: "unauthenticated" };
  if (err instanceof ForbiddenError) return { kind: "forbidden" };
  if (err instanceof ApiError && err.status === 404) {
    return { kind: "not_found" };
  }
  const message =
    err instanceof Error ? err.message : "Unexpected error while loading ledger.";
  return { kind: "other", message };
}

// ---- Page ----------------------------------------------------------------

export default function VehicleLedgerPage() {
  const { stock: rawStock } = useParams<{ stock: string }>();
  const stock = rawStock ?? "";
  const { hasRole } = useAuth();
  const canWrite = hasRole(...WRITE_ROLES);

  const [ledger, setLedger] = useState<VehicleLedgerResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<LoadError | null>(null);

  const reload = useCallback(async () => {
    if (!stock) return;
    setLoading(true);
    setLoadError(null);
    try {
      const data = await fetchVehicleLedger(stock);
      setLedger(data);
    } catch (err) {
      setLoadError(classifyError(err));
    } finally {
      setLoading(false);
    }
  }, [stock]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Link
        to="/dealer-ai-inventory"
        className="mb-4 inline-flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to inventory
      </Link>

      {loading && <LoadingSkeleton />}

      {!loading && loadError && (
        <ErrorPanel error={loadError} stock={stock} />
      )}

      {!loading && !loadError && ledger && (
        <LedgerContent
          ledger={ledger}
          canWrite={canWrite}
          onChanged={reload}
        />
      )}
    </div>
  );
}

// ---- Loading / error panels ---------------------------------------------

function LoadingSkeleton() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-slate-500">Loading ledger…</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-32 animate-pulse rounded bg-slate-100" />
      </CardContent>
    </Card>
  );
}

function ErrorPanel({ error, stock }: { error: LoadError; stock: string }) {
  // 401 is not surfaced here in practice — RequireAuth wraps the
  // route and redirects to /login before this component renders on
  // an anonymous session. The case is preserved as a safety net for
  // mid-session token expiry.
  if (error.kind === "unauthenticated") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Please sign in</CardTitle>
        </CardHeader>
        <CardContent className="text-slate-600">
          Your session has expired. Reload the page to sign in again.
        </CardContent>
      </Card>
    );
  }
  if (error.kind === "forbidden") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Not authorized</CardTitle>
        </CardHeader>
        <CardContent className="text-slate-600">
          The vehicle investment ledger is available to dealer owners and
          sales managers at this dealership. Contact your owner or sales
          manager if you need access.
        </CardContent>
      </Card>
    );
  }
  if (error.kind === "not_found") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Vehicle not found</CardTitle>
        </CardHeader>
        <CardContent className="text-slate-600">
          No vehicle with stock number{" "}
          <span className="font-mono">#{stock}</span> was found in this
          dealership.
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Something went wrong loading the ledger</CardTitle>
      </CardHeader>
      <CardContent className="text-slate-600">{error.message}</CardContent>
    </Card>
  );
}

// ---- Main content --------------------------------------------------------

function LedgerContent({
  ledger,
  canWrite,
  onChanged,
}: {
  ledger: VehicleLedgerResponse;
  canWrite: boolean;
  onChanged: () => void | Promise<void>;
}) {
  return (
    <div className="flex flex-col gap-6">
      <LedgerHeader
        vehicle={ledger.vehicle}
        daysInInventory={ledger.days_in_inventory}
      />
      <LedgerSummary
        totals={ledger.totals}
        askingPrice={ledger.vehicle.price}
        projectedGross={ledger.projected_gross}
      />
      <AcquisitionCard
        stock={ledger.vehicle.stock_number}
        acquisition={ledger.acquisition}
        canWrite={canWrite}
        onSaved={onChanged}
      />
      <CategoryTotals totals={ledger.totals} />
      <CostLedgerTable costs={ledger.costs} />
      {canWrite && (
        <AddCostForm
          stock={ledger.vehicle.stock_number}
          onCreated={onChanged}
        />
      )}
    </div>
  );
}

// ---- Header --------------------------------------------------------------

function LedgerHeader({
  vehicle,
  daysInInventory,
}: {
  vehicle: VehicleLedgerResponse["vehicle"];
  daysInInventory: number | null;
}) {
  const badgeClass = daysInInventoryBadgeClass(daysInInventory);
  const badgeText =
    daysInInventory === null
      ? "Record acquisition to track aging"
      : `${daysInInventory} day${daysInInventory === 1 ? "" : "s"} in inventory`;
  return (
    <div>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h1 className="text-2xl font-semibold text-slate-900">
          {vehicle.display_name || `${vehicle.year} ${vehicle.make} ${vehicle.model}`}
        </h1>
        <span className="text-sm font-mono text-slate-500">
          #{vehicle.stock_number}
        </span>
      </div>
      <div className="mt-2">
        <Badge variant="outline" className={`border ${badgeClass}`}>
          {badgeText}
        </Badge>
      </div>
    </div>
  );
}

// ---- Financial summary ---------------------------------------------------

function LedgerSummary({
  totals,
  askingPrice,
  projectedGross,
}: {
  totals: VehicleLedgerResponse["totals"];
  askingPrice: string;
  projectedGross: string;
}) {
  // Deliberate ordering + labels per the SESSION_053 brief: actual
  // investment and estimated remaining must be visibly distinct;
  // projected total must never be labeled as money already spent.
  return (
    <Card>
      <CardHeader>
        <CardTitle>Investment summary</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <SummaryStat
            label="Actual investment"
            value={formatMoney(totals.total_investment)}
            help="Committed spending: acquisition + actual costs."
          />
          <SummaryStat
            label="Estimated remaining"
            value={formatMoney(totals.estimated_cost_total)}
            help="Open estimates — projected but not yet committed."
          />
          <SummaryStat
            label="Projected total investment"
            value={formatMoney(totals.projected_total_investment)}
            help="Actual + estimated. Do not treat as sunk cost."
          />
          <SummaryStat
            label="Asking price"
            value={formatMoney(askingPrice)}
            help="Current retail sticker."
          />
          <SummaryStat
            label="Projected gross"
            value={formatMoney(projectedGross)}
            help="Asking price − actual investment."
          />
        </dl>
      </CardContent>
    </Card>
  );
}

function SummaryStat({
  label,
  value,
  help,
}: {
  label: string;
  value: string;
  help: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </dt>
      <dd className="mt-1 text-2xl font-semibold text-slate-900">{value}</dd>
      <p className="mt-1 text-xs text-slate-500">{help}</p>
    </div>
  );
}

// ---- Acquisition card (read + edit) --------------------------------------

function AcquisitionCard({
  stock,
  acquisition,
  canWrite,
  onSaved,
}: {
  stock: string;
  acquisition: LedgerAcquisition | null;
  canWrite: boolean;
  onSaved: () => void | Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Acquisition</CardTitle>
        {canWrite && !editing && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setEditing(true)}
          >
            {acquisition ? (
              <>
                <PencilLine className="mr-1 h-4 w-4" /> Edit
              </>
            ) : (
              <>
                <Plus className="mr-1 h-4 w-4" /> Record acquisition
              </>
            )}
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {editing ? (
          <AcquisitionForm
            stock={stock}
            initial={acquisition}
            onCancel={() => setEditing(false)}
            onSaved={async () => {
              setEditing(false);
              await onSaved();
            }}
          />
        ) : acquisition ? (
          <AcquisitionRead acquisition={acquisition} />
        ) : (
          <p className="text-sm text-slate-600">
            No acquisition on file yet.{" "}
            {canWrite
              ? "Record acquisition details to enable aging tracking and gross projection."
              : "A sales manager or owner will record acquisition details."}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function AcquisitionRead({
  acquisition,
}: {
  acquisition: LedgerAcquisition;
}) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
      <ReadField label="Source" value={acquisition.source_display} />
      <ReadField
        label="Source detail"
        value={acquisition.source_detail || "—"}
      />
      <ReadField
        label="Purchase price"
        value={formatMoney(acquisition.purchase_price)}
      />
      <ReadField
        label="Purchase date"
        value={formatDate(acquisition.purchase_date)}
      />
      <ReadField
        label="Buyer fees"
        value={formatMoney(acquisition.buyer_fees)}
      />
      <ReadField
        label="Arbitration fees"
        value={formatMoney(acquisition.arbitration_fees)}
      />
      <ReadField
        label="Transportation"
        value={formatMoney(acquisition.transportation_cost)}
      />
      <ReadField
        label="Title acquisition"
        value={formatMoney(acquisition.title_acquisition_cost)}
      />
      {acquisition.notes && (
        <div className="sm:col-span-2">
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Notes
          </dt>
          <dd className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
            {acquisition.notes}
          </dd>
        </div>
      )}
    </dl>
  );
}

function ReadField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </dt>
      <dd className="mt-1 text-sm text-slate-900">{value}</dd>
    </div>
  );
}

function AcquisitionForm({
  stock,
  initial,
  onCancel,
  onSaved,
}: {
  stock: string;
  initial: LedgerAcquisition | null;
  onCancel: () => void;
  onSaved: () => void | Promise<void>;
}) {
  const [source, setSource] = useState<AcquisitionSource>(
    initial?.source ?? "auction",
  );
  const [sourceDetail, setSourceDetail] = useState(initial?.source_detail ?? "");
  const [purchasePrice, setPurchasePrice] = useState(
    initial?.purchase_price ?? "",
  );
  const [purchaseDate, setPurchaseDate] = useState(initial?.purchase_date ?? "");
  const [buyerFees, setBuyerFees] = useState(initial?.buyer_fees ?? "0");
  const [arbitrationFees, setArbitrationFees] = useState(
    initial?.arbitration_fees ?? "0",
  );
  const [transportationCost, setTransportationCost] = useState(
    initial?.transportation_cost ?? "0",
  );
  const [titleAcquisitionCost, setTitleAcquisitionCost] = useState(
    initial?.title_acquisition_cost ?? "0",
  );
  const [notes, setNotes] = useState(initial?.notes ?? "");

  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [genericError, setGenericError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setFieldErrors({});
    setGenericError(null);
    const payload: AcquisitionUpsertPayload = {
      source,
      source_detail: sourceDetail,
      purchase_price: purchasePrice,
      purchase_date: purchaseDate,
      buyer_fees: buyerFees,
      arbitration_fees: arbitrationFees,
      transportation_cost: transportationCost,
      title_acquisition_cost: titleAcquisitionCost,
      notes,
    };
    try {
      await upsertVehicleAcquisition(stock, payload);
      await onSaved();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        try {
          const parsed = JSON.parse(err.body) as Record<string, string[] | string>;
          const flat: Record<string, string> = {};
          for (const [key, val] of Object.entries(parsed)) {
            flat[key] = Array.isArray(val) ? val.join(" ") : String(val);
          }
          setFieldErrors(flat);
        } catch {
          setGenericError(err.message);
        }
      } else if (err instanceof ForbiddenError) {
        setGenericError("You are not authorized to record acquisition details.");
      } else {
        setGenericError(
          err instanceof Error ? err.message : "Unexpected error saving acquisition.",
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField label="Source" error={fieldErrors.source}>
          <select
            value={source}
            onChange={(e) => setSource(e.target.value as AcquisitionSource)}
            className="h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
          >
            {ACQUISITION_SOURCE_CHOICES.map((choice) => (
              <option key={choice.value} value={choice.value}>
                {choice.label}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Source detail" error={fieldErrors.source_detail}>
          <Input
            value={sourceDetail}
            onChange={(e) => setSourceDetail(e.target.value)}
            placeholder="e.g. Manheim Phoenix, lane 4"
          />
        </FormField>
        <FormField label="Purchase price" error={fieldErrors.purchase_price}>
          <Input
            value={purchasePrice}
            onChange={(e) => setPurchasePrice(e.target.value)}
            placeholder="18500.00"
            inputMode="decimal"
            required
          />
        </FormField>
        <FormField label="Purchase date" error={fieldErrors.purchase_date}>
          <Input
            type="date"
            value={purchaseDate}
            onChange={(e) => setPurchaseDate(e.target.value)}
            required
          />
        </FormField>
        <FormField label="Buyer fees" error={fieldErrors.buyer_fees}>
          <Input
            value={buyerFees}
            onChange={(e) => setBuyerFees(e.target.value)}
            inputMode="decimal"
          />
        </FormField>
        <FormField
          label="Arbitration fees"
          error={fieldErrors.arbitration_fees}
        >
          <Input
            value={arbitrationFees}
            onChange={(e) => setArbitrationFees(e.target.value)}
            inputMode="decimal"
          />
        </FormField>
        <FormField
          label="Transportation cost"
          error={fieldErrors.transportation_cost}
        >
          <Input
            value={transportationCost}
            onChange={(e) => setTransportationCost(e.target.value)}
            inputMode="decimal"
          />
        </FormField>
        <FormField
          label="Title acquisition cost"
          error={fieldErrors.title_acquisition_cost}
        >
          <Input
            value={titleAcquisitionCost}
            onChange={(e) => setTitleAcquisitionCost(e.target.value)}
            inputMode="decimal"
          />
        </FormField>
      </div>
      <FormField label="Notes" error={fieldErrors.notes}>
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
        />
      </FormField>
      {genericError && (
        <p className="text-sm text-rose-700">{genericError}</p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : initial ? "Update acquisition" : "Record acquisition"}
        </Button>
      </div>
    </form>
  );
}

function FormField({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-600">
        {label}
      </label>
      {children}
      {error && <p className="mt-1 text-xs text-rose-700">{error}</p>}
    </div>
  );
}

// ---- Category totals -----------------------------------------------------

function CategoryTotals({
  totals,
}: {
  totals: VehicleLedgerResponse["totals"];
}) {
  const rows: Array<{ label: string; value: string; help?: string }> = [
    {
      label: "Acquisition",
      value: totals.acquisition_total,
      help: "From acquisition record.",
    },
    { label: "Flooring", value: totals.flooring_total },
    { label: "Reconditioning", value: totals.recon_total },
    { label: "Administrative", value: totals.administrative_total },
    { label: "Photography", value: totals.photography_total },
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Category breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3">
          {rows.map((row) => (
            <div
              key={row.label}
              className="flex items-baseline justify-between rounded border border-slate-200 px-3 py-2"
            >
              <dt className="text-sm text-slate-600">{row.label}</dt>
              <dd className="text-sm font-semibold text-slate-900">
                {formatMoney(row.value)}
              </dd>
            </div>
          ))}
        </dl>
        <Separator className="my-4" />
        <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3">
          <TotalsRow label="Actual costs" value={totals.actual_cost_total} />
          <TotalsRow
            label="Estimated (open)"
            value={totals.estimated_cost_total}
          />
          <TotalsRow
            label="Total investment"
            value={totals.total_investment}
            emphasis
          />
        </dl>
      </CardContent>
    </Card>
  );
}

function TotalsRow({
  label,
  value,
  emphasis = false,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
}) {
  return (
    <div
      className={`flex items-baseline justify-between rounded border px-3 py-2 ${
        emphasis
          ? "border-slate-900 bg-slate-900 text-white"
          : "border-slate-200"
      }`}
    >
      <dt className="text-sm">{label}</dt>
      <dd className="text-sm font-semibold">{formatMoney(value)}</dd>
    </div>
  );
}

// ---- Cost ledger table ---------------------------------------------------

function CostLedgerTable({ costs }: { costs: LedgerCost[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Cost history</CardTitle>
      </CardHeader>
      <CardContent>
        {costs.length === 0 ? (
          <p className="text-sm text-slate-600">
            No costs posted yet. Costs are immutable — corrections are
            recorded as reversing entries with a negative amount.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="py-2 pr-4">Incurred</th>
                  <th className="py-2 pr-4">Category</th>
                  <th className="py-2 pr-4 text-right">Amount</th>
                  <th className="py-2 pr-4">Vendor</th>
                  <th className="py-2 pr-4">Reference</th>
                  <th className="py-2 pr-4">Posted by</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {costs.map((cost) => (
                  <CostRow key={cost.id} cost={cost} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CostRow({ cost }: { cost: LedgerCost }) {
  const isReversal = cost.amount.startsWith("-");
  return (
    <tr>
      <td className="py-2 pr-4 text-slate-700">{formatDateTime(cost.incurred_at)}</td>
      <td className="py-2 pr-4">
        <div className="flex flex-wrap items-center gap-2">
          <span>{cost.category_display}</span>
          {cost.is_estimate && (
            <Badge variant="outline" className="border-yellow-300 bg-yellow-50 text-yellow-800">
              estimate
            </Badge>
          )}
          {isReversal && (
            <Badge variant="outline" className="border-slate-300 bg-slate-100 text-slate-700">
              reversal
            </Badge>
          )}
        </div>
        {cost.notes && (
          <p className="mt-1 text-xs text-slate-500">{cost.notes}</p>
        )}
      </td>
      <td
        className={`py-2 pr-4 text-right font-mono ${
          isReversal ? "text-slate-600" : "text-slate-900"
        }`}
      >
        {formatMoney(cost.amount)}
      </td>
      <td className="py-2 pr-4 text-slate-700">{cost.vendor || "—"}</td>
      <td className="py-2 pr-4 font-mono text-xs text-slate-500">
        {cost.reference || "—"}
      </td>
      <td className="py-2 pr-4 text-slate-600">{cost.created_by || "—"}</td>
    </tr>
  );
}

// ---- Add cost form -------------------------------------------------------

function AddCostForm({
  stock,
  onCreated,
}: {
  stock: string;
  onCreated: () => void | Promise<void>;
}) {
  const [category, setCategory] = useState(COST_CATEGORY_CHOICES[0]?.value ?? "");
  const [amount, setAmount] = useState("");
  const [incurredAt, setIncurredAt] = useState(
    () => new Date().toISOString().slice(0, 16), // datetime-local expects YYYY-MM-DDTHH:mm
  );
  const [vendor, setVendor] = useState("");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");
  const [isEstimate, setIsEstimate] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [genericError, setGenericError] = useState<string | null>(null);

  const groupedChoices = useMemo(() => {
    const groups: Record<string, typeof COST_CATEGORY_CHOICES> = {};
    for (const choice of COST_CATEGORY_CHOICES) {
      const group = CATEGORY_GROUP_LABEL[choice.group];
      groups[group] = groups[group] ?? [];
      groups[group].push(choice);
    }
    return groups;
  }, []);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setFieldErrors({});
    setGenericError(null);
    // Convert datetime-local (no timezone) → ISO with local offset so
    // the backend treats it as a real moment. `new Date(local).toISOString()`
    // converts through the browser's timezone which is what the
    // operator expects.
    const incurredIso = new Date(incurredAt).toISOString();
    const payload: CostCreatePayload = {
      category,
      amount,
      incurred_at: incurredIso,
      vendor,
      reference,
      notes,
      is_estimate: isEstimate,
    };
    try {
      await createVehicleCost(stock, payload);
      // Reset the form for the next entry — preserves incurred_at
      // as the most-recently-used moment so back-to-back same-day
      // entries stay ergonomic.
      setAmount("");
      setVendor("");
      setReference("");
      setNotes("");
      setIsEstimate(false);
      await onCreated();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        try {
          const parsed = JSON.parse(err.body) as Record<string, string[] | string>;
          const flat: Record<string, string> = {};
          for (const [key, val] of Object.entries(parsed)) {
            flat[key] = Array.isArray(val) ? val.join(" ") : String(val);
          }
          setFieldErrors(flat);
        } catch {
          setGenericError(err.message);
        }
      } else if (err instanceof ForbiddenError) {
        setGenericError("You are not authorized to post costs.");
      } else {
        setGenericError(
          err instanceof Error ? err.message : "Unexpected error posting cost.",
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add a cost</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Category" error={fieldErrors.category}>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
              >
                {Object.entries(groupedChoices).map(([groupLabel, choices]) => (
                  <optgroup key={groupLabel} label={groupLabel}>
                    {choices.map((choice) => (
                      <option key={choice.value} value={choice.value}>
                        {choice.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </FormField>
            <FormField label="Amount" error={fieldErrors.amount}>
              <Input
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="300.00 (negative for reversal)"
                inputMode="decimal"
                required
              />
            </FormField>
            <FormField
              label="Incurred at"
              error={fieldErrors.incurred_at}
            >
              <Input
                type="datetime-local"
                value={incurredAt}
                onChange={(e) => setIncurredAt(e.target.value)}
                required
              />
            </FormField>
            <FormField label="Vendor" error={fieldErrors.vendor}>
              <Input
                value={vendor}
                onChange={(e) => setVendor(e.target.value)}
                placeholder="Rick's Auto Repair"
              />
            </FormField>
            <FormField label="Reference" error={fieldErrors.reference}>
              <Input
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="Invoice # / PO #"
              />
            </FormField>
            <FormField label="Estimate?" error={fieldErrors.is_estimate}>
              <label className="mt-2 flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={isEstimate}
                  onChange={(e) => setIsEstimate(e.target.checked)}
                  className="h-4 w-4"
                />
                Not yet committed — projected only
              </label>
            </FormField>
          </div>
          <FormField label="Notes" error={fieldErrors.notes}>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Optional context, e.g. what the invoice covered"
            />
          </FormField>
          {genericError && (
            <p className="text-sm text-rose-700">{genericError}</p>
          )}
          <p className="text-xs text-slate-500">
            Cost entries are immutable. To correct a mistake, post a reversing
            entry with a negative amount and reference the original.
          </p>
          <div className="flex justify-end">
            <Button type="submit" disabled={submitting}>
              {submitting ? "Posting…" : "Post cost"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
