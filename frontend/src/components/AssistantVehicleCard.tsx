// SESSION_013 — inline vehicle card rendered beneath an assistant
// message on the customer-facing Live Assistant page.
//
// Deliberately small: one shadcn Card, key specs, one badge per
// available signal (budget_fit, lever_flex_kind), and a single CTA
// — "Continue conversation". This is NOT VehicleCard.tsx; that
// component carries dealer-side affordances (Flag for handoff,
// Details modal) we explicitly do not want in the customer surface.
// The whole point is "the assistant found this for you", not a
// shopping-cart row.

import { Gauge, MessageCircle, Tag, Zap } from "lucide-react";

import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
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

export default function AssistantVehicleCard({ vehicle, onContinue }: Props) {
  const monthlyPayment =
    typeof vehicle.estimated_payment === "number"
      ? Math.round(vehicle.estimated_payment)
      : null;

  return (
    <Card size="sm" className="bg-card">
      <CardHeader className="border-b pb-3">
        <div className="flex items-start justify-between gap-3">
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
            {monthlyPayment ? (
              <div className="text-[11px] text-muted-foreground">
                ~${monthlyPayment}/mo
              </div>
            ) : null}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 pt-0">
        <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground">
          {vehicle.mileage > 0 ? (
            <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5">
              <Gauge className="h-3 w-3" />
              {vehicle.mileage.toLocaleString()} mi
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5">
              <Gauge className="h-3 w-3" />
              New
            </span>
          )}
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
