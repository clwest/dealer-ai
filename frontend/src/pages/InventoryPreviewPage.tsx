// SESSION_014 — Inventory preview / stub page.
// SESSION_030 pivot — data source renamed to `sampleInventory.ts`
// and pointed at the Copper Canyon Auto persona (mixed-make used).
//
// Read-only visual surface that demos how the OS surfaces inventory.
// Source is the sample at `frontend/src/data/sampleInventory.ts`
// (public, demo-only). The Live Assistant page still uses real
// backend matched_vehicles; this page is intentionally separate.
//
// When CRM/DMS feed integration lands, replace the data import with
// the live source and delete the sample module.

import { ExternalLink, Gauge, Sparkles, Tag, Zap } from "lucide-react";

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
  SAMPLE_INVENTORY_CAPTURED_AT,
  SAMPLE_INVENTORY,
  SAMPLE_INVENTORY_HOMEPAGE_URL,
  type SampleInventoryVehicle,
  type VehicleCondition,
} from "@/data/sampleInventory";

const CONDITION_STYLES: Record<VehicleCondition, string> = {
  new: "border-emerald-200 bg-emerald-50 text-emerald-700",
  used: "border-amber-200 bg-amber-50 text-amber-700",
  certified: "border-sky-200 bg-sky-50 text-sky-700",
};

const CONDITION_LABEL: Record<VehicleCondition, string> = {
  new: "New",
  used: "Used",
  certified: "Certified",
};

export default function InventoryPreviewPage() {
  const totalCount = SAMPLE_INVENTORY.length;
  const newCount = SAMPLE_INVENTORY.filter(
    (v) => v.condition === "new",
  ).length;
  const usedCount = totalCount - newCount;

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Inventory
        </h1>
        <p className="text-sm text-muted-foreground">
          Visual preview of the dealer's lot. {newCount} new ·{" "}
          {usedCount} used / certified.
        </p>
      </header>

      <DemoBanner />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SAMPLE_INVENTORY.map((v) => (
          <InventoryCard key={v.vin} vehicle={v} />
        ))}
      </div>
    </div>
  );
}

function DemoBanner() {
  return (
    <div className="flex items-start gap-3 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <Sparkles className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="space-y-0.5">
        <div className="font-semibold">Demo data</div>
        <div className="text-xs text-amber-800">
          Sample of {SAMPLE_INVENTORY.length} vehicles refreshed on{" "}
          {SAMPLE_INVENTORY_CAPTURED_AT}. Browse the full lot at{" "}
          <a
            href={SAMPLE_INVENTORY_HOMEPAGE_URL}
            target="_blank"
            rel="noreferrer"
            className="underline underline-offset-2"
          >
            the dealership's inventory page
          </a>
          . Used here for visual realism only — the Live Assistant uses real
          backend inventory. Will be replaced by the CRM/DMS feed when that
          integration lands.
        </div>
      </div>
    </div>
  );
}

function InventoryCard({ vehicle }: { vehicle: SampleInventoryVehicle }) {
  const hasMsrp = vehicle.msrp !== null && vehicle.msrp > vehicle.price;
  return (
    <Card className="overflow-hidden p-0">
      <a
        href={vehicle.vdp_url}
        target="_blank"
        rel="noreferrer"
        className="block"
        aria-label={`Open ${vehicle.display_name} details`}
      >
        <div className="relative aspect-video w-full overflow-hidden bg-muted">
          <img
            src={vehicle.image_url}
            alt={vehicle.display_name}
            loading="lazy"
            className="h-full w-full object-cover transition group-hover:scale-[1.02]"
          />
          <span
            className={`absolute left-3 top-3 rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${CONDITION_STYLES[vehicle.condition]}`}
          >
            {CONDITION_LABEL[vehicle.condition]}
          </span>
        </div>
      </a>

      <CardHeader className="pt-4">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-0.5">
            <CardTitle className="text-sm font-semibold leading-tight">
              {vehicle.display_name}
            </CardTitle>
            <div className="text-xs text-muted-foreground">
              Stock #{vehicle.stock_number}
              {vehicle.exterior_color ? ` · ${vehicle.exterior_color}` : ""}
            </div>
          </div>
          <div className="text-right">
            <div className="text-base font-bold text-primary">
              {formatCurrency(vehicle.price)}
            </div>
            {hasMsrp ? (
              <div className="text-[11px] text-muted-foreground line-through">
                {formatCurrency(vehicle.msrp)}
              </div>
            ) : null}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5">
            <Gauge className="h-3 w-3" />
            {vehicle.condition === "new"
              ? "New"
              : `${vehicle.mileage.toLocaleString()} mi`}
          </span>
          {vehicle.drivetrain ? (
            <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5">
              <Tag className="h-3 w-3" />
              {vehicle.drivetrain}
            </span>
          ) : null}
          {vehicle.fuel_type ? (
            <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5">
              <Zap className="h-3 w-3" />
              {vehicle.fuel_type}
            </span>
          ) : null}
        </div>
        {vehicle.condition !== "new" ? (
          <div className="pt-2">
            <Badge variant="outline" className="font-normal">
              VIN ending {vehicle.vin.slice(-6)}
            </Badge>
          </div>
        ) : null}
      </CardContent>

      <CardFooter className="bg-muted/40 px-4 py-2.5">
        <Button
          asChild
          variant="ghost"
          size="sm"
          className="ml-auto h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
        >
          <a href={vehicle.vdp_url} target="_blank" rel="noreferrer">
            <ExternalLink className="h-3.5 w-3.5" />
            View on dealer site
          </a>
        </Button>
      </CardFooter>
    </Card>
  );
}
