// Milestone 5 · Increment 6 (SESSION_080) — vehicle lifecycle stage
// pill. Mirrors the M4.7 WorkOrderStatusBadge shape (icon + text +
// distinct color per state so operators on color-blind /
// high-contrast modes still perceive the value).
//
// 12 stages per §5.a Modified Option C. `null` renders as a
// neutral "No stage" pill (a vehicle without a stage row is a real
// state, not an error).

import {
  Ban,
  Camera,
  CarFront,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  DollarSign,
  Package,
  PackageX,
  Pause,
  Sparkles,
  Truck,
  Wrench,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { getStageMeta } from "@/lib/lifecycle";
import type { VehicleStageKey } from "@/lib/api";
import { cn } from "@/lib/utils";

const STAGE_ICONS: Record<VehicleStageKey, React.ComponentType<{ className?: string }>> = {
  incoming: Truck,
  inspection: ClipboardList,
  recon: Wrench,
  qc: ClipboardCheck,
  detail: Sparkles,
  photography: Camera,
  listing: DollarSign,
  frontline: CarFront,
  wholesale_out: Package,
  hold_reserved: Pause,
  company_use: CheckCircle2,
  off_market: PackageX,
};

export interface StageBadgeProps {
  stage: VehicleStageKey | null;
  className?: string;
}

export function StageBadge({ stage, className }: StageBadgeProps) {
  const meta = getStageMeta(stage);
  const Icon = stage ? STAGE_ICONS[stage] ?? Ban : Ban;
  return (
    <Badge
      variant="outline"
      className={cn("gap-1 text-xs font-medium", meta.className, className)}
    >
      <Icon className="h-3 w-3" />
      {meta.label}
    </Badge>
  );
}
