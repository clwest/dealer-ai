// Milestone 3 · Increment 7 — severity badge with icon + text label.
//
// A11y-critical: severity must be distinguishable without color.
// Includes both an icon and a text label so operators using
// high-contrast / greyscale / color-blind modes still perceive
// severity at a glance.
//
// Severity vocabulary (per M3.1 model + M3.2 service) — four values
// in escalation order:
//   advisory     → informational, noted only
//   recommended  → should be addressed, non-blocking
//   required     → must be addressed before front-line
//   safety       → must be addressed, highest priority

import {
  AlertTriangle,
  CircleAlert,
  Info,
  ShieldAlert,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type SeverityKey = "advisory" | "recommended" | "required" | "safety";

interface Meta {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  className: string;
}

const SEVERITY_META: Record<SeverityKey, Meta> = {
  advisory: {
    label: "Advisory",
    icon: Info,
    className:
      "border-slate-200 bg-slate-100 text-slate-700",
  },
  recommended: {
    label: "Recommended",
    icon: CircleAlert,
    className:
      "border-yellow-200 bg-yellow-100 text-yellow-800",
  },
  required: {
    label: "Required",
    icon: AlertTriangle,
    className:
      "border-orange-200 bg-orange-100 text-orange-800",
  },
  safety: {
    label: "Safety",
    icon: ShieldAlert,
    className: "border-rose-200 bg-rose-100 text-rose-800",
  },
};

function _lookup(severity: string): Meta {
  if (severity in SEVERITY_META) {
    return SEVERITY_META[severity as SeverityKey];
  }
  return {
    label: severity || "Unknown",
    icon: Info,
    className: "border-slate-200 bg-slate-100 text-slate-700",
  };
}

export function SeverityBadge({
  severity,
  className,
}: {
  severity: string;
  className?: string;
}) {
  const meta = _lookup(severity);
  const Icon = meta.icon;
  return (
    <Badge
      variant="outline"
      className={cn(
        "inline-flex items-center gap-1 font-medium",
        meta.className,
        className,
      )}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      <span>{meta.label}</span>
    </Badge>
  );
}

// Ordering used everywhere severity is displayed. Highest priority
// first so operators see safety-critical findings at the top of each
// category group.
export const SEVERITY_DISPLAY_ORDER: SeverityKey[] = [
  "safety",
  "required",
  "recommended",
  "advisory",
];
