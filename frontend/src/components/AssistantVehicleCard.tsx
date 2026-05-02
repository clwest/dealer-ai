// SESSION_013 / SESSION_016 — inline vehicle card rendered beneath
// an assistant message on the customer-facing Live Assistant page.
//
// Distinct from VehicleCard.tsx (dealer-side, carries Flag for
// handoff and Details modal). This card stays customer-facing:
// one CTA — "Continue conversation" — and a strict visual
// hierarchy that puts the photo and the price ahead of operational
// metadata (stock #, VIN, color tag, etc.).
//
// SESSION_016 polish:
//   - Vehicle image at the top with a condition pill overlay and a
//     graceful fallback when the URL is missing or fails to load.
//   - Vertical hierarchy: image → title → price/payment → specs →
//     badges → CTA. Each layer has its own visual weight.
//   - Cards now feel like dealer inventory rather than generic chat
//     attachments without giving up the chat-first framing.

import { useState } from "react";
import { CarFront, Gauge, MessageCircle, Tag, Zap } from "lucide-react";

import {
  Card,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, formatCurrency } from "@/lib/utils";
import type { Vehicle } from "@/lib/api";

interface Props {
  vehicle: Vehicle;
  onContinue: (vehicle: Vehicle) => void;
}

const BUDGET_FIT_LABEL: Record<NonNullable<Vehicle["budget_fit"]>, string> = {
  fit: "In budget",
  near_fit: "Close to budget",
  over_budget: "Above budget",
};

const LEVER_FLEX_LABEL: Record<NonNullable<Vehicle["lever_flex_kind"]>, string> = {
  longer_term: "Needs longer term",
  more_down: "Needs more down",
  drivetrain_flex: "Drivetrain flex",
  stretch_payment: "Stretch payment",
};

const CONDITION_STYLES: Record<string, string> = {
  new: "border-emerald-200 bg-emerald-50 text-emerald-700",
  used: "border-amber-200 bg-amber-50 text-amber-700",
  certified: "border-sky-200 bg-sky-50 text-sky-700",
};

export default function AssistantVehicleCard({ vehicle, onContinue }: Props) {
  const monthlyPayment =
    typeof vehicle.estimated_payment === "number"
      ? Math.round(vehicle.estimated_payment)
      : null;

  return (
    <Card
      size="sm"
      className="overflow-hidden bg-card p-0 transition hover:ring-2 hover:ring-primary/30"
    >
      <VehicleImage vehicle={vehicle} />

      <CardContent className="space-y-3 px-4 pt-3">
        {/* Title block */}
        <div className="space-y-0.5">
          <div className="text-sm font-semibold leading-tight text-foreground">
            {vehicle.display_name}
          </div>
          <div className="text-xs text-muted-foreground">
            Stock #{vehicle.stock_number}
            {vehicle.exterior_color ? ` · ${vehicle.exterior_color}` : ""}
          </div>
        </div>

        {/* Price block — clearly the headline */}
        <div className="flex items-baseline gap-2">
          <div className="text-lg font-bold tracking-tight text-primary">
            {formatCurrency(vehicle.price)}
          </div>
          {monthlyPayment ? (
            <div className="text-xs text-muted-foreground">
              ~${monthlyPayment}/mo
            </div>
          ) : null}
        </div>

        {/* Spec chips */}
        <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground">
          {vehicle.mileage > 0 ? (
            <SpecChip icon={Gauge}>
              {vehicle.mileage.toLocaleString()} mi
            </SpecChip>
          ) : (
            <SpecChip icon={Gauge}>New</SpecChip>
          )}
          {vehicle.drivetrain ? (
            <SpecChip icon={Tag}>{vehicle.drivetrain}</SpecChip>
          ) : null}
          {vehicle.fuel_type ? (
            <SpecChip icon={Zap}>{vehicle.fuel_type}</SpecChip>
          ) : null}
        </div>

        {/* Match-quality badges (only when backend attached them) */}
        {(vehicle.budget_fit || vehicle.lever_flex_kind) && (
          <div className="flex flex-wrap gap-1.5">
            {vehicle.budget_fit ? (
              <BudgetFitBadge fit={vehicle.budget_fit} />
            ) : null}
            {vehicle.lever_flex_kind ? (
              <LeverFlexBadge
                kind={vehicle.lever_flex_kind}
                explainer={vehicle.lever_flex_explainer}
              />
            ) : null}
          </div>
        )}
      </CardContent>

      <CardFooter className="bg-muted/40 px-3 py-2">
        <Button
          variant="outline"
          size="sm"
          className="ml-auto h-8 gap-1.5 text-xs"
          onClick={() => onContinue(vehicle)}
        >
          <MessageCircle className="h-3.5 w-3.5" />
          Continue conversation
        </Button>
      </CardFooter>
    </Card>
  );
}

function VehicleImage({ vehicle }: { vehicle: Vehicle }) {
  const [errored, setErrored] = useState(false);
  const conditionRaw = (vehicle.condition || "").toLowerCase();
  const conditionLabel = formatCondition(conditionRaw);
  const conditionStyle =
    CONDITION_STYLES[conditionRaw] ??
    "border-slate-200 bg-slate-50 text-slate-700";

  const showImage = !!vehicle.image_url && !errored;

  return (
    <div className="relative aspect-video w-full overflow-hidden bg-muted">
      {showImage ? (
        <img
          src={vehicle.image_url}
          alt={`Photo of ${vehicle.display_name}`}
          loading="lazy"
          onError={() => setErrored(true)}
          className="h-full w-full object-cover"
        />
      ) : (
        <ImageFallback />
      )}
      {conditionLabel ? (
        <span
          className={cn(
            "absolute left-2 top-2 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
            conditionStyle,
          )}
        >
          {conditionLabel}
        </span>
      ) : null}
    </div>
  );
}

function ImageFallback() {
  // Calm Ford-blue tint so the missing-photo state still reads as
  // "this is a real vehicle from the lot" — not as broken UI.
  return (
    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-primary/5 to-primary/15 text-primary/40">
      <CarFront className="h-8 w-8" aria-hidden />
      <span className="sr-only">Photo coming soon</span>
    </div>
  );
}

function SpecChip({
  icon: Icon,
  children,
}: {
  icon: typeof Gauge;
  children: React.ReactNode;
}) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5">
      <Icon className="h-3 w-3" />
      {children}
    </span>
  );
}

function BudgetFitBadge({ fit }: { fit: NonNullable<Vehicle["budget_fit"]> }) {
  const label = BUDGET_FIT_LABEL[fit];
  if (fit === "fit") {
    return (
      <Badge
        variant="outline"
        className="border-emerald-200 bg-emerald-50 text-emerald-700"
      >
        {label}
      </Badge>
    );
  }
  if (fit === "near_fit") {
    return (
      <Badge
        variant="outline"
        className="border-amber-200 bg-amber-50 text-amber-700"
      >
        {label}
      </Badge>
    );
  }
  return <Badge variant="destructive">{label}</Badge>;
}

function LeverFlexBadge({
  kind,
  explainer,
}: {
  kind: NonNullable<Vehicle["lever_flex_kind"]>;
  explainer?: string | null;
}) {
  // Prefer the backend's human-readable explainer when present; fall
  // back to the structured kind label so the UI never shows a raw enum.
  const label = explainer?.trim() || LEVER_FLEX_LABEL[kind];
  return (
    <Badge variant="secondary" className="font-normal">
      {label}
    </Badge>
  );
}

function formatCondition(condition: string): string {
  if (!condition) return "";
  if (condition === "certified") return "Certified";
  return condition.charAt(0).toUpperCase() + condition.slice(1);
}
