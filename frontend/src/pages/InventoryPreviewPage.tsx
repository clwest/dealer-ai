// SESSION_014 — Inventory preview page.
// SESSION_030 pivot — pointed at the Copper Canyon Auto persona.
// TASK_losing-deals-and-the-inventory-page (2026-09-01) — wired to
// the backend via `/admin/vehicles/`. Previously read a static
// twelve-car sample module that showed different stock numbers than
// the seed, which made every per-vehicle door 404 from this page and
// dead-ended step 2 of the demo script.
//
// SESSION_226 (TASK_walkable-demo-and-servers-up 1d) — the public
// showroom / dealership home page / hero component were also
// rewired to their own AllowAny endpoint
// (`/api/dealer-ai/showroom/vehicles/` via `listShowroomVehicles`),
// so `frontend/src/data/sampleInventory.ts` was deleted this session.
// This operator page continues to use the admin endpoint above;
// customer-facing surfaces use the public one.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BookOpen,
  Camera,
  ClipboardCheck,
  DollarSign,
  ClipboardList,
  FileText,
  Gauge,
  Wrench,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";
import {
  listAdminVehicles,
  type AdminVehicleRow,
  type AdminVehicleListResponse,
} from "@/lib/salesApi";
import { ApiError } from "@/lib/authFetch";

const PAGE_SIZE = 24;

const CONDITION_STYLES: Record<string, string> = {
  new: "border-emerald-200 bg-emerald-50 text-emerald-700",
  used: "border-amber-200 bg-amber-50 text-amber-700",
  certified: "border-sky-200 bg-sky-50 text-sky-700",
};

const CONDITION_LABEL: Record<string, string> = {
  new: "New",
  used: "Used",
  certified: "Certified",
};

type AvailabilityFilter = "all" | "available" | "sold";

interface Props {
  /** Injected for tests. Defaults to shipped `listAdminVehicles`. */
  loadInventory?: typeof listAdminVehicles;
}

export default function InventoryPreviewPage({
  loadInventory = listAdminVehicles,
}: Props = {}) {
  const [availability, setAvailability] =
    useState<AvailabilityFilter>("available");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<AdminVehicleListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const availabilityParam = useMemo<boolean | undefined>(() => {
    if (availability === "available") return true;
    if (availability === "sold") return false;
    return undefined;
  }, [availability]);

  const fetchPage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const body = await loadInventory({
        is_available: availabilityParam,
        limit: PAGE_SIZE,
        offset,
      });
      setData(body);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Unable to load inventory.";
      setError(message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [loadInventory, availabilityParam, offset]);

  useEffect(() => {
    void fetchPage();
  }, [fetchPage]);

  // Reset paging when the availability filter changes.
  useEffect(() => {
    setOffset(0);
  }, [availability]);

  const total = data?.count ?? 0;
  const rows = data?.results ?? [];
  const showingFrom = total === 0 ? 0 : offset + 1;
  const showingTo = Math.min(offset + rows.length, total);

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Inventory
        </h1>
        <p className="text-sm text-muted-foreground">
          Live view of the dealer's lot from{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-xs">
            /admin/vehicles/
          </code>
          .
        </p>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div
          className="inline-flex rounded-md border border-border bg-muted/40 p-0.5"
          role="tablist"
          aria-label="Availability filter"
        >
          {(
            [
              { key: "available", label: "Available" },
              { key: "sold", label: "Sold" },
              { key: "all", label: "All" },
            ] as const
          ).map(({ key, label }) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={availability === key}
              onClick={() => setAvailability(key)}
              className={`rounded-sm px-3 py-1 text-xs font-medium transition ${
                availability === key
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="text-xs text-muted-foreground">
          {loading && !data
            ? "Loading…"
            : total === 0
              ? "No vehicles match."
              : `Showing ${showingFrom.toLocaleString()}–${showingTo.toLocaleString()} of ${total.toLocaleString()}`}
        </div>
      </div>

      {error ? (
        <div
          role="alert"
          className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
        >
          {error}
        </div>
      ) : null}

      {loading && !data ? (
        <LoadingSkeleton />
      ) : rows.length === 0 && !error ? (
        <EmptyState />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map((v) => (
            <InventoryCard key={v.id} vehicle={v} />
          ))}
        </div>
      )}

      {data && total > PAGE_SIZE ? (
        <div className="flex items-center justify-between gap-3 border-t border-border pt-4">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!data.previous || loading}
            onClick={() => setOffset(Math.max(offset - PAGE_SIZE, 0))}
          >
            ← Previous
          </Button>
          <span className="text-xs text-muted-foreground">
            Page {Math.floor(offset / PAGE_SIZE) + 1} of{" "}
            {Math.max(1, Math.ceil(total / PAGE_SIZE))}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!data.has_more || loading}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Next →
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="h-64 animate-pulse rounded-lg border border-border bg-muted/40"
        />
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-md border border-dashed border-border px-6 py-10 text-center text-sm text-muted-foreground">
      No vehicles match the current filter.
    </div>
  );
}

function InventoryCard({ vehicle }: { vehicle: AdminVehicleRow }) {
  const stock = encodeURIComponent(vehicle.stock_number);
  const conditionClass =
    CONDITION_STYLES[vehicle.condition] ??
    "border-slate-200 bg-slate-50 text-slate-700";
  const conditionLabel =
    CONDITION_LABEL[vehicle.condition] ?? vehicle.condition;
  const price = Number(vehicle.price);
  return (
    <Card className="overflow-hidden p-0">
      <div className="relative aspect-video w-full overflow-hidden bg-muted">
        {vehicle.image_url ? (
          <img
            src={vehicle.image_url}
            alt={vehicle.display_name}
            loading="lazy"
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
            No photo on file
          </div>
        )}
        <span
          className={`absolute left-3 top-3 rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${conditionClass}`}
        >
          {conditionLabel}
        </span>
        {!vehicle.is_available ? (
          <span className="absolute right-3 top-3 rounded-full border border-slate-300 bg-white/90 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-slate-700">
            Sold
          </span>
        ) : null}
      </div>

      <CardHeader className="pt-4">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-0.5">
            <CardTitle className="text-sm font-semibold leading-tight">
              {vehicle.display_name}
            </CardTitle>
            <div className="text-xs text-muted-foreground">
              Stock #{vehicle.stock_number}
            </div>
          </div>
          <div className="text-right">
            <div className="text-base font-bold text-primary">
              {Number.isFinite(price) ? formatCurrency(price) : vehicle.price}
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5">
            <Gauge className="h-3 w-3" />
            {conditionLabel}
          </span>
          <Badge variant="outline" className="font-normal">
            {vehicle.is_available ? "On lot" : "Sold"}
          </Badge>
        </div>
      </CardContent>

      <CardFooter className="flex items-center justify-between gap-2 bg-muted/40 px-4 py-2.5">
        <div className="flex flex-wrap items-center gap-1">
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <Link to={`/dealer-ai-inventory/${stock}/ledger`}>
              <BookOpen className="h-3.5 w-3.5" />
              Ledger
            </Link>
          </Button>
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <Link to={`/dealer-ai-inventory/${stock}/condition-report`}>
              <ClipboardCheck className="h-3.5 w-3.5" />
              Condition Report
            </Link>
          </Button>
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <Link to={`/dealer-ai-inventory/${stock}/recon`}>
              <Wrench className="h-3.5 w-3.5" />
              Recon
            </Link>
          </Button>
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <Link to={`/dealer-ai-inventory/${stock}/photos`}>
              <Camera className="h-3.5 w-3.5" />
              Photos
            </Link>
          </Button>
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <Link to={`/dealer-ai-inventory/${stock}/listing`}>
              <FileText className="h-3.5 w-3.5" />
              Listing
            </Link>
          </Button>
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <Link to={`/dealer-ai-inventory/${stock}/sale`}>
              <DollarSign className="h-3.5 w-3.5" />
              Sale
            </Link>
          </Button>
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <Link to={`/dealer-ai-inventory/${stock}/lifecycle`}>
              <ClipboardList className="h-3.5 w-3.5" />
              Lifecycle
            </Link>
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}
