// Milestone 4 · Increment 7 — WorkOrder status pill.
//
// Reusable across every recon surface (dashboard, WO card, comm
// panel). Uses both a color + text label so operators on
// high-contrast / color-blind modes still perceive the state.
//
// States per planning §5.c: draft, approved, in_progress,
// completed, cancelled. Terminal states (completed, cancelled)
// use different color families from the active states.

import {
  Ban,
  CheckCircle2,
  CircleDot,
  FileEdit,
  Loader2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type StatusKey =
  | "draft"
  | "approved"
  | "in_progress"
  | "completed"
  | "cancelled";

interface Meta {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  className: string;
}

const META: Record<StatusKey, Meta> = {
  draft: {
    label: "Draft",
    icon: FileEdit,
    className: "border-slate-300 bg-slate-100 text-slate-700",
  },
  approved: {
    label: "Approved",
    icon: CircleDot,
    className: "border-blue-300 bg-blue-100 text-blue-700",
  },
  in_progress: {
    label: "In progress",
    icon: Loader2,
    className: "border-amber-300 bg-amber-100 text-amber-700",
  },
  completed: {
    label: "Completed",
    icon: CheckCircle2,
    className: "border-green-300 bg-green-100 text-green-700",
  },
  cancelled: {
    label: "Cancelled",
    icon: Ban,
    className: "border-gray-300 bg-gray-100 text-gray-500 line-through",
  },
};

export interface WorkOrderStatusBadgeProps {
  status: string;
  className?: string;
}

export function WorkOrderStatusBadge({
  status,
  className,
}: WorkOrderStatusBadgeProps) {
  const key = (status as StatusKey) in META ? (status as StatusKey) : "draft";
  const meta = META[key];
  const Icon = meta.icon;
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
