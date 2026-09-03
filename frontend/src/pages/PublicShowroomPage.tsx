// SESSION_022 — public showroom.
//
// Demo showroom for the assistant-first public site. Every vehicle
// gives shoppers a direct "Ask AI" path instead of pushing them
// through a generic VDP-only funnel.
//
// SESSION_226 (TASK_walkable-demo-and-servers-up 1d): inventory now
// comes from the AllowAny `/api/dealer-ai/showroom/vehicles/`
// endpoint via `listShowroomVehicles`. The old sampleInventory.ts
// snapshot is deleted; twelve fake CC-{T|S|C|V}-NN stock numbers no
// longer 404 against the seed.

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, ExternalLink, Gauge, Search, SlidersHorizontal, Tag, Zap } from "lucide-react";

import SiteFooter from "@/components/dealership/SiteFooter";
import SiteNav from "@/components/dealership/SiteNav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  listShowroomVehicles,
  type ShowroomCondition,
  type ShowroomVehicle,
} from "@/lib/showroomApi";
import { fetchOnboardingProfile } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

type FilterKey = "all" | ShowroomCondition | "hybrid" | "awd";

const FILTER_LABELS: Record<FilterKey, string> = {
  all: "All",
  new: "New",
  used: "Used",
  certified: "Certified",
  hybrid: "Hybrid",
  awd: "AWD / 4WD",
};

const CONDITION_LABEL: Record<string, string> = {
  new: "New",
  used: "Used",
  certified: "Certified",
};

export default function PublicShowroomPage() {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");
  const [inventory, setInventory] = useState<ShowroomVehicle[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    // SESSION_232 addendum — prime the dealership-slug cache so the
    // list is scoped to the caller's store on multi-store installs.
    fetchOnboardingProfile()
      .catch(() => null)
      .then(() => listShowroomVehicles({ limit: 200 }))
      .then((response) => {
        if (cancelled || !response) return;
        setInventory(response.results);
        setStatus("ready");
      })
      .catch(() => {
        if (cancelled) return;
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const vehicles = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return inventory.filter((vehicle) => {
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
  }, [filter, inventory, query]);

  const availableFilters = useMemo<FilterKey[]>(() => {
    if (inventory.length === 0) return ["all"];
    const conditions = new Set(inventory.map((v) => String(v.condition).toLowerCase()));
    const hasHybrid = inventory.some((v) => v.fuel_type.toLowerCase().includes("hybrid"));
    const hasAwd = inventory.some((v) => /awd|4wd|4×4|4x4/i.test(v.drivetrain));
    const order: FilterKey[] = ["all", "new", "used", "certified", "hybrid", "awd"];
    return order.filter((key) => {
      if (key === "all") return true;
      if (key === "hybrid") return hasHybrid;
      if (key === "awd") return hasAwd;
      return conditions.has(key);
    });
  }, [inventory]);

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
                  Live inventory from the store. Use the AI assistant for
                  budget and fit questions.
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
                  {availableFilters.map((key) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setFilter(key)}
                      className={
                        key === filter
                          ? "inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground"
                          : "inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-background px-3 text-xs font-medium text-muted-foreground hover:text-foreground"
                      }
                    >
                      {key === "all" ? (
                        <SlidersHorizontal className="h-3.5 w-3.5" />
                      ) : null}
                      {FILTER_LABELS[key]}
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
              <span className="font-medium">
                {status === "loading" ? "Loading inventory…" : null}
                {status === "ready" ? `${vehicles.length} vehicles` : null}
                {status === "error" ? "Inventory unavailable" : null}
              </span>
              <Link
                to="/assistant?prompt=Help me choose from the showroom"
                className="inline-flex items-center gap-1.5 text-primary hover:underline"
              >
                Ask AI to choose
                <Bot className="h-4 w-4" />
              </Link>
            </div>
            {status === "error" ? (
              <div className="rounded-lg border border-destructive/40 bg-destructive/5 px-4 py-10 text-center text-sm text-destructive">
                Inventory feed isn't reachable right now. Try again in a moment.
              </div>
            ) : null}
            {status === "ready" ? (
              <>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {vehicles.map((vehicle) => (
                    <ShowroomCard key={vehicle.stock_number} vehicle={vehicle} />
                  ))}
                </div>
                {vehicles.length === 0 ? (
                  <div className="rounded-lg border border-border bg-muted/40 px-4 py-10 text-center text-sm text-muted-foreground">
                    No vehicles match those filters.
                  </div>
                ) : null}
              </>
            ) : null}
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

function ShowroomCard({ vehicle }: { vehicle: ShowroomVehicle }) {
  const priceValue = Number.parseFloat(vehicle.price) || 0;
  const detailHref = vehicle.vdp_url || undefined;
  const conditionKey = String(vehicle.condition).toLowerCase();
  const conditionLabel = CONDITION_LABEL[conditionKey] ?? vehicle.condition;
  return (
    <article className="overflow-hidden rounded-lg border border-border bg-card shadow-soft">
      <a
        href={detailHref}
        target={detailHref ? "_blank" : undefined}
        rel={detailHref ? "noreferrer" : undefined}
        className="block"
        aria-label={`Open ${vehicle.display_name}${
          detailHref ? " on dealer site" : ""
        }`}
      >
        <div className="relative aspect-[16/10] overflow-hidden bg-muted">
          {vehicle.image_url ? (
            <img
              src={vehicle.image_url}
              alt={vehicle.display_name}
              className="h-full w-full object-cover transition hover:scale-[1.02]"
              loading="lazy"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-xs uppercase tracking-wider text-muted-foreground">
              No photo yet
            </div>
          )}
          <span className="absolute left-3 top-3 rounded-md bg-background/95 px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-foreground shadow-sm">
            {conditionLabel}
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
            {formatCurrency(priceValue)}
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1">
            <Gauge className="h-3 w-3" />
            {conditionKey === "new"
              ? "New"
              : `${vehicle.mileage.toLocaleString()} mi`}
          </span>
          {vehicle.drivetrain ? (
            <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1">
              <Tag className="h-3 w-3" />
              {vehicle.drivetrain}
            </span>
          ) : null}
          {vehicle.fuel_type ? (
            <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1">
              <Zap className="h-3 w-3" />
              {vehicle.fuel_type}
            </span>
          ) : null}
        </div>

        <div className="flex items-center justify-between border-t border-border pt-3">
          {detailHref ? (
            <Button asChild variant="ghost" size="sm" className="gap-1.5">
              <a href={detailHref} target="_blank" rel="noreferrer">
                <ExternalLink className="h-3.5 w-3.5" />
                Details
              </a>
            </Button>
          ) : (
            <span aria-hidden />
          )}
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
