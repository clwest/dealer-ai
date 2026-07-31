// SESSION_022 — public showroom.
//
// Demo showroom for the assistant-first public site. Inventory is the
// existing SESSION_014 sample snapshot, not a new backend contract.
// Every vehicle gives shoppers a direct "Ask AI" path instead of
// pushing them through a generic VDP-only funnel.

import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, ExternalLink, Gauge, Search, SlidersHorizontal, Tag, Zap } from "lucide-react";

import SiteFooter from "@/components/dealership/SiteFooter";
import SiteNav from "@/components/dealership/SiteNav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  SAMPLE_INVENTORY_CAPTURED_AT,
  SAMPLE_INVENTORY,
  type SampleInventoryVehicle,
  type VehicleCondition,
} from "@/data/sampleInventory";
import { formatCurrency } from "@/lib/utils";

type FilterKey = "all" | VehicleCondition | "hybrid" | "awd";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "new", label: "New" },
  { key: "used", label: "Used" },
  { key: "certified", label: "Certified" },
  { key: "hybrid", label: "Hybrid" },
  { key: "awd", label: "AWD / 4WD" },
];

const CONDITION_LABEL: Record<VehicleCondition, string> = {
  new: "New",
  used: "Used",
  certified: "Certified",
};

export default function PublicShowroomPage() {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");

  const vehicles = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return SAMPLE_INVENTORY.filter((vehicle) => {
      const matchesQuery =
        !normalized ||
        [
          vehicle.display_name,
          vehicle.stock_number,
          vehicle.make,
          vehicle.model,
          vehicle.trim,
          vehicle.exterior_color ?? "",
        ]
          .join(" ")
          .toLowerCase()
          .includes(normalized);
      const matchesFilter =
        filter === "all" ||
        vehicle.condition === filter ||
        (filter === "hybrid" && vehicle.fuel_type.toLowerCase().includes("hybrid")) ||
        (filter === "awd" && /awd|4wd|4×4|4x4/i.test(vehicle.drivetrain));
      return matchesQuery && matchesFilter;
    });
  }, [filter, query]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteNav />
      <main>
        <section className="border-b border-border bg-muted/30 py-10">
          <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
            <Badge variant="outline" className="mb-3">
              Showroom
            </Badge>
            <div className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr] lg:items-end">
              <div>
                <h1 className="text-4xl font-semibold tracking-tight">
                  Browse the lot, then ask the assistant to narrow it.
                </h1>
                <p className="mt-3 text-sm text-muted-foreground">
                  Demo inventory captured {SAMPLE_INVENTORY_CAPTURED_AT}.
                  Use the AI assistant for budget and fit questions.
                </p>
              </div>
              <div className="rounded-lg border border-border bg-card p-3 shadow-soft">
                <div className="flex items-center gap-2 rounded-md border border-input bg-background px-3">
                  <Search className="h-4 w-4 text-muted-foreground" />
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search make, model, stock number..."
                    className="h-10 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                    aria-label="Search inventory"
                  />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {FILTERS.map((item) => (
                    <button
                      key={item.key}
                      type="button"
                      onClick={() => setFilter(item.key)}
                      className={
                        item.key === filter
                          ? "inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground"
                          : "inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-background px-3 text-xs font-medium text-muted-foreground hover:text-foreground"
                      }
                    >
                      {item.key === "all" ? (
                        <SlidersHorizontal className="h-3.5 w-3.5" />
                      ) : null}
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="py-8">
          <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mb-4 flex items-center justify-between text-sm">
              <span className="font-medium">{vehicles.length} vehicles</span>
              <Link
                to="/assistant?prompt=Help me choose from the showroom"
                className="inline-flex items-center gap-1.5 text-primary hover:underline"
              >
                Ask AI to choose
                <Bot className="h-4 w-4" />
              </Link>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {vehicles.map((vehicle) => (
                <ShowroomCard key={vehicle.vin} vehicle={vehicle} />
              ))}
            </div>
            {vehicles.length === 0 ? (
              <div className="rounded-lg border border-border bg-muted/40 px-4 py-10 text-center text-sm text-muted-foreground">
                No vehicles match those filters.
              </div>
            ) : null}
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

function ShowroomCard({ vehicle }: { vehicle: SampleInventoryVehicle }) {
  return (
    <article className="overflow-hidden rounded-lg border border-border bg-card shadow-soft">
      <a
        href={vehicle.vdp_url}
        target="_blank"
        rel="noreferrer"
        className="block"
        aria-label={`Open ${vehicle.display_name} on dealer site`}
      >
        <div className="relative aspect-[16/10] overflow-hidden bg-muted">
          <img
            src={vehicle.image_url}
            alt={vehicle.display_name}
            className="h-full w-full object-cover transition hover:scale-[1.02]"
            loading="lazy"
          />
          <span className="absolute left-3 top-3 rounded-md bg-background/95 px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-foreground shadow-sm">
            {CONDITION_LABEL[vehicle.condition]}
          </span>
        </div>
      </a>

      <div className="space-y-4 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold leading-tight">
              {vehicle.display_name}
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Stock #{vehicle.stock_number}
              {vehicle.exterior_color ? ` · ${vehicle.exterior_color}` : ""}
            </p>
          </div>
          <div className="text-right text-base font-bold text-primary">
            {formatCurrency(vehicle.price)}
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1">
            <Gauge className="h-3 w-3" />
            {vehicle.condition === "new"
              ? "New"
              : `${vehicle.mileage.toLocaleString()} mi`}
          </span>
          <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1">
            <Tag className="h-3 w-3" />
            {vehicle.drivetrain}
          </span>
          <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1">
            <Zap className="h-3 w-3" />
            {vehicle.fuel_type}
          </span>
        </div>

        <div className="flex items-center justify-between border-t border-border pt-3">
          <Button asChild variant="ghost" size="sm" className="gap-1.5">
            <a href={vehicle.vdp_url} target="_blank" rel="noreferrer">
              <ExternalLink className="h-3.5 w-3.5" />
              Details
            </a>
          </Button>
          <Button asChild size="sm" className="gap-1.5">
            <Link
              to={`/assistant?prompt=${encodeURIComponent(
                `Would the ${vehicle.display_name} fit my budget?`,
              )}`}
            >
              <Bot className="h-3.5 w-3.5" />
              Ask AI
            </Link>
          </Button>
        </div>
      </div>
    </article>
  );
}
