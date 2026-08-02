// Milestone 9 · Increment 5 (SESSION_104) — operator vehicle sale page.
//
// Consumes the M9.1 Sale endpoints + M9.2 Delivery endpoints:
//   GET  /admin/vehicles/<stock>/sale/
//   POST /admin/vehicles/<stock>/sale/
//   GET  /admin/vehicles/<stock>/delivery/
//   POST /admin/vehicles/<stock>/delivery/
//   PATCH /admin/deliveries/<id>/
//
// State-owning single-file container per Decision B Option A
// (§0.a SESSION_104). Renders:
//
//   - Sale summary + gross_realized (when Sale exists).
//   - Sale-create form (when no Sale).
//   - Delivery summary + checklist toggle buttons + verify-insurance
//     button (when Sale + Delivery exist).
//   - Delivery-create button (when Sale exists but no Delivery).
//
// Role gating: all writes go through the backend's
// IsReconManagerSalesManagerOrOwnerAtActiveDealership gate; the
// frontend hides write affordances from advisors / porters as UX
// convenience.

import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/lib/AuthContext";
import { formatMoney } from "@/lib/analyticsApi";
import {
  createDelivery,
  createSale,
  readDelivery,
  readSale,
  updateDelivery,
  type CreateSaleRequest,
  type Delivery,
  type DeliveryChecklistKey,
  type Sale,
  type SaleFinanceType,
} from "@/lib/saleApi";

const WRITE_ROLES = ["recon_manager", "sales_manager", "dealer_owner"];

const CHECKLIST_LABELS: Record<DeliveryChecklistKey, string> = {
  detail_booked: "Detail booked",
  fueled: "Fueled",
  temp_tag: "Temp tag issued",
  insurance_verified: "Insurance verified",
  customer_walkthrough: "Customer walkthrough",
};

const CHECKLIST_ORDER: DeliveryChecklistKey[] = [
  "detail_booked",
  "fueled",
  "temp_tag",
  "insurance_verified",
  "customer_walkthrough",
];

export default function VehicleSalePage() {
  const { stock } = useParams<{ stock: string }>();
  const { hasRole } = useAuth();

  const [sale, setSale] = useState<Sale | null>(null);
  const [delivery, setDelivery] = useState<Delivery | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canWrite = hasRole(...WRITE_ROLES);

  const refresh = useCallback(async () => {
    if (!stock) return;
    setLoadState("loading");
    try {
      const [nextSale, nextDelivery] = await Promise.all([
        readSale(stock),
        readDelivery(stock),
      ]);
      setSale(nextSale);
      setDelivery(nextDelivery);
      setLoadState("ready");
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Unknown error");
      setLoadState("error");
    }
  }, [stock]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (!stock) {
    return <p className="text-sm text-destructive">Missing stock number.</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Link to="/dealer-ai-inventory" className="hover:underline">
            ← Inventory
          </Link>
          <span>·</span>
          <span>Stock #{stock}</span>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Sale &amp; Delivery
        </h1>
        <p className="text-sm text-muted-foreground">
          Record the closing event + delivery workflow for this vehicle.
        </p>
      </header>

      {loadState === "loading" ? (
        <p className="text-sm text-muted-foreground" role="status">
          Loading…
        </p>
      ) : loadState === "error" ? (
        <p className="text-sm text-destructive" role="alert">
          Failed to load: {errorMessage ?? "unknown error"}
        </p>
      ) : (
        <>
          <SaleSection
            sale={sale}
            stock={stock}
            canWrite={!!canWrite}
            busy={busy}
            setBusy={setBusy}
            onCreated={refresh}
          />
          {sale ? (
            <DeliverySection
              sale={sale}
              delivery={delivery}
              stock={stock}
              canWrite={!!canWrite}
              busy={busy}
              setBusy={setBusy}
              onChanged={refresh}
            />
          ) : null}
        </>
      )}
    </div>
  );
}

interface SaleSectionProps {
  sale: Sale | null;
  stock: string;
  canWrite: boolean;
  busy: boolean;
  setBusy: (v: boolean) => void;
  onCreated: () => void;
}

function SaleSection({
  sale,
  stock,
  canWrite,
  busy,
  setBusy,
  onCreated,
}: SaleSectionProps) {
  if (sale) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Sale</CardTitle>
          <CardDescription>Closed {sale.sale_date}</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          <Stat label="Sold price" value={formatMoney(sale.sold_price)} />
          <Stat
            label="Gross realized"
            value={formatMoney(sale.gross_realized)}
          />
          <Stat label="Finance type" value={sale.finance_type} />
          <Stat label="Lender" value={sale.lender_name || "—"} />
        </CardContent>
      </Card>
    );
  }
  return (
    <SaleCreateForm
      stock={stock}
      disabled={!canWrite || busy}
      onCreated={onCreated}
      setBusy={setBusy}
    />
  );
}

interface SaleCreateFormProps {
  stock: string;
  disabled: boolean;
  onCreated: () => void;
  setBusy: (v: boolean) => void;
}

function SaleCreateForm({
  stock,
  disabled,
  onCreated,
  setBusy,
}: SaleCreateFormProps) {
  const today = new Date().toISOString().slice(0, 10);
  const [saleDate, setSaleDate] = useState(today);
  const [soldPrice, setSoldPrice] = useState("");
  const [financeType, setFinanceType] = useState<SaleFinanceType>("cash");
  const [lenderName, setLenderName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!soldPrice.trim()) {
      setFormError("Sold price is required.");
      return;
    }
    const payload: CreateSaleRequest = {
      sale_date: saleDate,
      sold_price: soldPrice,
      finance_type: financeType,
      lender_name: lenderName,
    };
    setBusy(true);
    try {
      await createSale(stock, payload);
      onCreated();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Create failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Record sale</CardTitle>
        <CardDescription>
          No sale on file for this vehicle yet. Fill in the closing
          details to record it.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="grid gap-3 md:grid-cols-2">
          <Field label="Sale date">
            <input
              type="date"
              className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
              value={saleDate}
              onChange={(e) => setSaleDate(e.target.value)}
              disabled={disabled}
              required
            />
          </Field>
          <Field label="Sold price">
            <input
              type="number"
              step="0.01"
              inputMode="decimal"
              className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
              value={soldPrice}
              onChange={(e) => setSoldPrice(e.target.value)}
              disabled={disabled}
              placeholder="25000.00"
              required
            />
          </Field>
          <Field label="Finance type">
            <select
              className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
              value={financeType}
              onChange={(e) =>
                setFinanceType(e.target.value as SaleFinanceType)
              }
              disabled={disabled}
            >
              <option value="cash">Cash</option>
              <option value="retail">Retail (bank / credit union)</option>
              <option value="bhph">Buy-here-pay-here</option>
            </select>
          </Field>
          <Field label="Lender (optional)">
            <input
              type="text"
              className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
              value={lenderName}
              onChange={(e) => setLenderName(e.target.value)}
              disabled={disabled}
              placeholder="First National"
            />
          </Field>
          {formError ? (
            <p
              className="md:col-span-2 text-sm text-destructive"
              role="alert"
            >
              {formError}
            </p>
          ) : null}
          <div className="md:col-span-2">
            <Button type="submit" disabled={disabled}>
              Record sale
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

interface DeliverySectionProps {
  sale: Sale;
  delivery: Delivery | null;
  stock: string;
  canWrite: boolean;
  busy: boolean;
  setBusy: (v: boolean) => void;
  onChanged: () => void;
}

function DeliverySection({
  sale,
  delivery,
  stock,
  canWrite,
  busy,
  setBusy,
  onChanged,
}: DeliverySectionProps) {
  async function startDelivery() {
    setBusy(true);
    try {
      await createDelivery(stock);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function toggle(key: DeliveryChecklistKey, current: boolean) {
    if (!delivery) return;
    setBusy(true);
    try {
      await updateDelivery(delivery.id, {
        checklist_key: key,
        checklist_value: !current,
      });
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function verifyInsurance() {
    if (!delivery) return;
    setBusy(true);
    try {
      await updateDelivery(delivery.id, { verify_insurance: true });
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  if (!delivery) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Delivery</CardTitle>
          <CardDescription>
            No delivery workflow started yet. Sale #{sale.id} is
            ready to move to delivery preparation.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            onClick={startDelivery}
            disabled={!canWrite || busy}
          >
            Start delivery
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Delivery checklist</CardTitle>
        <CardDescription>
          {delivery.delivery_date
            ? `Scheduled for ${delivery.delivery_date}`
            : "Delivery date not scheduled yet."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <ul className="flex flex-col gap-2" data-testid="delivery-checklist">
          {CHECKLIST_ORDER.map((key) => {
            const done = delivery.checklist[key];
            // Insurance is toggled via the dedicated "verify"
            // button (writes the timestamp column atomically), not
            // via the regular checklist toggle. The button below
            // matches that shape.
            const isInsurance = key === "insurance_verified";
            return (
              <li
                key={key}
                className="flex items-center justify-between rounded border border-border p-2"
              >
                <span className="text-sm">
                  {CHECKLIST_LABELS[key]}
                  {done ? " ✓" : ""}
                </span>
                {isInsurance ? (
                  <Button
                    size="sm"
                    variant={done ? "outline" : "default"}
                    disabled={!canWrite || busy || done}
                    onClick={verifyInsurance}
                  >
                    {done ? "Verified" : "Verify insurance"}
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant={done ? "outline" : "default"}
                    disabled={!canWrite || busy}
                    onClick={() => toggle(key, done)}
                  >
                    {done ? "Undo" : "Mark done"}
                  </Button>
                )}
              </li>
            );
          })}
        </ul>
        {delivery.temp_tag_number ? (
          <p className="text-sm text-muted-foreground">
            Temp tag: <span className="font-mono">{delivery.temp_tag_number}</span>
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-sm font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
  );
}
