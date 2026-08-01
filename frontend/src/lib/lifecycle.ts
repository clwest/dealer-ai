// Milestone 5 · Increment 6 (SESSION_080) — vehicle lifecycle
// client-side transition table + role-authority map.
//
// Mirrors backend ``services/vehicle_lifecycle.py``:
// ``_ALLOWED_TRANSITIONS`` and ``_STAGE_ROLE_AUTHORITY``. Kept in
// TypeScript so the ManualTransitionForm dropdown can compute
// allowed targets without a server round-trip. The backend is
// authoritative; if a stale client submits a disallowed target,
// the M5.2 service rejects with 409 (structural) or 403 (role).
//
// **Do NOT drift.** Any change to ``_ALLOWED_TRANSITIONS`` or
// ``_STAGE_ROLE_AUTHORITY`` on the backend must land here too, or
// the UI's affordances will disagree with the service's contract.
// SESSION_075 §5.b + §5.f (SESSION_075 refined).

import type { VehicleStageKey } from "@/lib/api";

// Retail-preparation pipeline stages (§5.a Modified Option C —
// 8 stages, includes frontline as the terminal retail-eligible
// state).
export const RETAIL_PREPARATION_STAGES: Set<VehicleStageKey> = new Set([
  "incoming",
  "inspection",
  "recon",
  "qc",
  "detail",
  "photography",
  "listing",
  "frontline",
]);

// Operational-disposition stages (§5.f — gated to
// dealer_owner + sales_manager only at the service layer).
export const COMMERCIAL_DISPOSITION_STAGES: Set<VehicleStageKey> = new Set([
  "wholesale_out",
  "hold_reserved",
  "company_use",
  "off_market",
]);

// Full allowed-transitions table. Key = from_stage, value = set of
// allowed to_stages. Mirrors backend ``_ALLOWED_TRANSITIONS``.
export const ALLOWED_TRANSITIONS: Record<VehicleStageKey, VehicleStageKey[]> = {
  incoming: [
    "inspection",
    "hold_reserved",
    "wholesale_out",
    "company_use",
    "off_market",
  ],
  inspection: [
    "recon",
    "hold_reserved",
    "wholesale_out",
    "company_use",
    "off_market",
  ],
  recon: [
    "qc",
    "hold_reserved",
    "wholesale_out",
    "company_use",
    "off_market",
  ],
  qc: [
    "detail",
    "photography", // detail-collapse escape hatch
    "hold_reserved",
    "wholesale_out",
    "company_use",
    "off_market",
  ],
  detail: [
    "photography",
    "hold_reserved",
    "wholesale_out",
    "company_use",
    "off_market",
  ],
  photography: [
    "listing",
    "hold_reserved",
    "wholesale_out",
    "company_use",
    "off_market",
  ],
  listing: [
    "frontline",
    "hold_reserved",
    "wholesale_out",
    "company_use",
    "off_market",
  ],
  frontline: [
    // §5.b — post-frontline operational transitions.
    "hold_reserved",
    "wholesale_out",
    "company_use",
    "off_market",
    // No `frontline → sold` in M5 (§5.a — sold deferred to M9).
  ],
  // hold_reserved return targets: any retail-preparation stage.
  hold_reserved: [
    "incoming",
    "inspection",
    "recon",
    "qc",
    "detail",
    "photography",
    "listing",
    "frontline",
  ],
  // Fixed operational returns via inspection.
  wholesale_out: ["inspection"],
  company_use: ["inspection"],
  off_market: ["inspection"],
};

// Role authority — per target stage, the set of roles authorized to
// move a vehicle INTO that stage. Mirrors backend
// ``_STAGE_ROLE_AUTHORITY`` (§5.f SESSION_075 refined).
//
// `recon_manager` may participate in retail-preparation transitions
// (including frontline) but is EXCLUDED from every commercial /
// disposition target.

export type RoleKey =
  | "dealer_owner"
  | "sales_manager"
  | "recon_manager"
  | "f_and_i_manager"
  | "collections"
  | "advisor"
  | "porter";

const RETAIL_PREP_ROLES: RoleKey[] = [
  "dealer_owner",
  "sales_manager",
  "recon_manager",
];

const COMMERCIAL_ROLES: RoleKey[] = ["dealer_owner", "sales_manager"];

export const STAGE_ROLE_AUTHORITY: Record<VehicleStageKey, RoleKey[]> = {
  incoming: RETAIL_PREP_ROLES,
  inspection: RETAIL_PREP_ROLES,
  recon: RETAIL_PREP_ROLES,
  qc: RETAIL_PREP_ROLES,
  detail: RETAIL_PREP_ROLES,
  photography: RETAIL_PREP_ROLES,
  listing: RETAIL_PREP_ROLES,
  frontline: RETAIL_PREP_ROLES,
  hold_reserved: COMMERCIAL_ROLES,
  wholesale_out: COMMERCIAL_ROLES,
  company_use: COMMERCIAL_ROLES,
  off_market: COMMERCIAL_ROLES,
};

/** Return true when `role` is authorized to move a vehicle INTO
 * `toStage`. Roles not listed for a target → false. */
export function canRoleAdvanceTo(
  role: RoleKey | null | undefined,
  toStage: VehicleStageKey,
): boolean {
  if (!role) return false;
  return STAGE_ROLE_AUTHORITY[toStage].includes(role);
}

/** Return the set of stages `role` can advance a vehicle to, given
 * a current stage. Used by ManualTransitionForm to populate the
 * dropdown. */
export function allowedTargetsForRole(
  currentStage: VehicleStageKey | null,
  role: RoleKey | null | undefined,
): VehicleStageKey[] {
  if (currentStage === null) return [];
  const structuralTargets = ALLOWED_TRANSITIONS[currentStage] ?? [];
  return structuralTargets.filter((tgt) => canRoleAdvanceTo(role, tgt));
}

// Stage vocabulary — labels + icon key for the StageBadge component.
// Each stage gets a distinct visual so operators on color-blind /
// high-contrast modes still perceive the state (icon + text). Follows
// the M4.7 WorkOrderStatusBadge convention.
export interface StageMeta {
  label: string;
  className: string; // Tailwind classes for the badge
}

export const STAGE_META: Record<VehicleStageKey, StageMeta> = {
  incoming: {
    label: "Incoming",
    className: "border-slate-300 bg-slate-100 text-slate-700",
  },
  inspection: {
    label: "Inspection",
    className: "border-cyan-300 bg-cyan-100 text-cyan-700",
  },
  recon: {
    label: "Recon",
    className: "border-amber-300 bg-amber-100 text-amber-700",
  },
  qc: {
    label: "QC",
    className: "border-indigo-300 bg-indigo-100 text-indigo-700",
  },
  detail: {
    label: "Detail",
    className: "border-violet-300 bg-violet-100 text-violet-700",
  },
  photography: {
    label: "Photography",
    className: "border-pink-300 bg-pink-100 text-pink-700",
  },
  listing: {
    label: "Listing",
    className: "border-blue-300 bg-blue-100 text-blue-700",
  },
  frontline: {
    label: "Frontline",
    className: "border-green-300 bg-green-100 text-green-700",
  },
  wholesale_out: {
    label: "Wholesale out",
    className: "border-orange-300 bg-orange-100 text-orange-700",
  },
  hold_reserved: {
    label: "Hold / reserved",
    className: "border-yellow-300 bg-yellow-100 text-yellow-700",
  },
  company_use: {
    label: "Company use",
    className: "border-teal-300 bg-teal-100 text-teal-700",
  },
  off_market: {
    label: "Off market",
    className: "border-gray-300 bg-gray-100 text-gray-500",
  },
};

/** Get the label + class for a stage. Falls back to a neutral
 * shape if the stage isn't recognized (client version drifted from
 * server). */
export function getStageMeta(stage: VehicleStageKey | null): StageMeta {
  if (stage === null) {
    return {
      label: "No stage",
      className: "border-gray-300 bg-gray-50 text-gray-500 italic",
    };
  }
  return (
    STAGE_META[stage] ?? {
      label: stage,
      className: "border-gray-300 bg-gray-100 text-gray-700",
    }
  );
}
