import { CheckCircle2, Eye, Gauge, Tag, Zap } from "lucide-react";

import { cn, formatCurrency } from "@/lib/utils";
import type { Vehicle } from "@/lib/api";

interface Props {
  vehicle: Vehicle;
  selected?: boolean;
  onSelect?: (v: Vehicle) => void;
  onOpenDetails?: (v: Vehicle) => void;
}

const conditionStyle: Record<string, string> = {
  new: "bg-emerald-50 text-emerald-700 border-emerald-200",
  used: "bg-amber-50 text-amber-700 border-amber-200",
  certified: "bg-sky-50 text-sky-700 border-sky-200",
};

export default function VehicleCard({
  vehicle,
  selected,
  onSelect,
  onOpenDetails,
}: Props) {
  const conditionLabel =
    vehicle.condition === "certified" ? "Certified" : vehicle.condition;

  return (
    <div
      className={cn(
        "card group flex w-full flex-col overflow-hidden text-left transition hover:-translate-y-0.5 hover:shadow-lg",
        selected && "ring-2 ring-ford-accent",
      )}
    >
      <button
        type="button"
        onClick={() => onOpenDetails?.(vehicle)}
        className="relative h-40 w-full bg-slate-100"
      >
        {vehicle.image_url ? (
          // eslint-disable-next-line jsx-a11y/img-redundant-alt
          <img
            src={vehicle.image_url}
            alt={`Photo of ${vehicle.display_name}`}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-slate-400">
            No photo
          </div>
        )}
        <span
          className={cn(
            "absolute left-3 top-3 rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
            conditionStyle[vehicle.condition] ??
              "bg-slate-50 text-slate-700 border-slate-200",
          )}
        >
          {conditionLabel}
        </span>
      </button>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="text-base font-semibold leading-tight text-ford-ink">
              {vehicle.display_name}
            </div>
            <div className="text-xs text-slate-500">
              Stock #{vehicle.stock_number}
              {vehicle.exterior_color ? ` · ${vehicle.exterior_color}` : ""}
            </div>
          </div>
          <div className="text-right">
            <div className="text-base font-bold text-ford-blue">
              {formatCurrency(vehicle.price)}
            </div>
            {vehicle.msrp && Number(vehicle.msrp) > Number(vehicle.price) ? (
              <div className="text-xs text-slate-400 line-through">
                {formatCurrency(vehicle.msrp)}
              </div>
            ) : null}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 text-xs text-slate-600">
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-2 py-1">
            <Gauge className="h-3.5 w-3.5" />
            {vehicle.mileage.toLocaleString()} mi
          </span>
          {vehicle.drivetrain && (
            <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-2 py-1">
              <Tag className="h-3.5 w-3.5" />
              {vehicle.drivetrain}
            </span>
          )}
          {vehicle.fuel_type && (
            <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-2 py-1">
              <Zap className="h-3.5 w-3.5" />
              {vehicle.fuel_type}
            </span>
          )}
        </div>

        {vehicle.features?.length ? (
          <div className="flex flex-wrap gap-1.5">
            {vehicle.features.slice(0, 4).map((f) => (
              <span
                key={f}
                className="rounded-md border border-slate-200 px-2 py-0.5 text-[11px] text-slate-600"
              >
                {f}
              </span>
            ))}
          </div>
        ) : null}

        <div className="mt-auto flex gap-2 pt-3">
          <button
            type="button"
            onClick={() => onOpenDetails?.(vehicle)}
            className="btn-ghost flex-1 justify-center"
          >
            <Eye className="h-4 w-4" />
            Details
          </button>
          {onSelect && (
            <button
              type="button"
              onClick={() => onSelect(vehicle)}
              className={cn(
                "inline-flex flex-1 items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition",
                selected
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                  : "border-slate-200 bg-white text-ford-ink hover:bg-slate-50",
              )}
            >
              <CheckCircle2 className="h-4 w-4" />
              {selected ? "Flagged" : "Flag"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
