// Milestone 8 · Increment 5 (SESSION_098) — analytics API client.
//
// Consumes the six operator-analytics endpoints shipped M8.1-M8.4:
//
//   GET /admin/analytics/recon-cost-per-source/           (Q1, M8.1)
//   GET /admin/analytics/vendor-performance/              (Q2 + Q4, M8.2)
//   GET /admin/analytics/stage-aging-trend/               (Q5 + Q9, M8.3)
//   GET /admin/analytics/sla-breach-patterns/             (Q10, M8.3)
//   GET /admin/analytics/vehicle-type-recon-cost/         (Q3 proxy, M8.4)
//   GET /admin/analytics/days-at-frontline-proxy/         (Q8 proxy, M8.4)
//
// Money handling: every dollar / percent figure travels as a two-
// decimal-place string on the wire and stays a string in this
// module. The backend is the authoritative source; the frontend
// NEVER recomputes totals or percentages — display-only string
// manipulation.
//
// Kept as its own module (rather than folded into ``lib/api.ts``)
// because ``api.ts`` is already 800+ lines and analytics is a
// discrete surface with its own row-type vocabulary.

import { authGetJSON } from "@/lib/authFetch";

// ---------------------------------------------------------------------------
// Q1 — recon cost per acquisition source
// ---------------------------------------------------------------------------

export interface SourcePerformanceRow {
  source: string;
  source_display: string;
  vehicle_count: number;
  total_recon_cost: string;
  mean_recon_cost: string;
}

export interface ReconCostPerSourceResponse {
  rows: SourcePerformanceRow[];
}

export function fetchReconCostPerSource(): Promise<ReconCostPerSourceResponse> {
  return authGetJSON<ReconCostPerSourceResponse>(
    "/admin/analytics/recon-cost-per-source/",
  );
}

// ---------------------------------------------------------------------------
// Q2 + Q4 — vendor performance
// ---------------------------------------------------------------------------

export interface VendorPerformanceRow {
  vendor_slug: string;
  vendor_name: string;
  completed_count: number;
  mean_completion_days: number | null;
  mean_variance_pct: string | null;
  over_budget_count: number;
}

export interface VendorPerformanceResponse {
  rows: VendorPerformanceRow[];
}

export function fetchVendorPerformance(): Promise<VendorPerformanceResponse> {
  return authGetJSON<VendorPerformanceResponse>(
    "/admin/analytics/vendor-performance/",
  );
}

// ---------------------------------------------------------------------------
// Q5 + Q9 — stage aging trend
// ---------------------------------------------------------------------------

export interface AgingTrendPoint {
  snapshot_at: string;
  vehicle_count: number;
  p50_days: number;
  p90_days: number;
}

export interface StageAgingTrendResponse {
  stage: string;
  window_days: number;
  points: AgingTrendPoint[];
}

export function fetchStageAgingTrend(
  stage: string,
  windowDays = 30,
): Promise<StageAgingTrendResponse> {
  const params = new URLSearchParams({
    stage,
    window_days: String(windowDays),
  });
  return authGetJSON<StageAgingTrendResponse>(
    `/admin/analytics/stage-aging-trend/?${params.toString()}`,
  );
}

// ---------------------------------------------------------------------------
// Q10 — SLA-breach patterns
// ---------------------------------------------------------------------------

export interface VendorBreachCount {
  vendor_name: string;
  breach_count: number;
}

export interface KindBreachCount {
  kind: string;
  kind_display: string;
  breach_count: number;
}

export interface BreachPatternReport {
  total_breach_count: number;
  average_breach_days: string | null;
  top_vendors_by_breach_count: VendorBreachCount[];
  breaches_by_kind: KindBreachCount[];
}

export interface SlaBreachPatternsResponse {
  window_days: number;
  report: BreachPatternReport;
}

export function fetchSlaBreachPatterns(
  windowDays = 30,
): Promise<SlaBreachPatternsResponse> {
  const params = new URLSearchParams({ window_days: String(windowDays) });
  return authGetJSON<SlaBreachPatternsResponse>(
    `/admin/analytics/sla-breach-patterns/?${params.toString()}`,
  );
}

// ---------------------------------------------------------------------------
// Q3 proxy — vehicle-type recon cost
// ---------------------------------------------------------------------------

export interface VehicleTypeReconCostRow {
  make: string;
  model: string;
  vehicle_count: number;
  total_recon_cost: string;
  mean_recon_cost: string;
}

export interface VehicleTypeReconCostResponse {
  rows: VehicleTypeReconCostRow[];
}

export function fetchVehicleTypeReconCost(): Promise<VehicleTypeReconCostResponse> {
  return authGetJSON<VehicleTypeReconCostResponse>(
    "/admin/analytics/vehicle-type-recon-cost/",
  );
}

// ---------------------------------------------------------------------------
// Q8 proxy — days at frontline
// ---------------------------------------------------------------------------

export interface DaysAtFrontlineReport {
  snapshot_count: number;
  mean_p50_days: string | null;
  mean_p90_days: string | null;
  latest_vehicle_count: number | null;
  latest_snapshot_at: string | null;
}

export interface DaysAtFrontlineResponse {
  window_days: number;
  report: DaysAtFrontlineReport;
}

export function fetchDaysAtFrontlineProxy(
  windowDays = 30,
): Promise<DaysAtFrontlineResponse> {
  const params = new URLSearchParams({ window_days: String(windowDays) });
  return authGetJSON<DaysAtFrontlineResponse>(
    `/admin/analytics/days-at-frontline-proxy/?${params.toString()}`,
  );
}

// ---------------------------------------------------------------------------
// Milestone 9 · Increment 3 (SESSION_102) + Increment 4 (SESSION_103) —
// analytics extensions unlocking M8 deferrals.
//
// Q3 true / Q6 gross-profit trend / Q7 buyer estimate accuracy / Q8
// true inventory turn. Shipped alongside the M8.4 proxy verbs — both
// coexist (per M8 §6 lesson 11 additive extension). M9.5 UI reads
// the true verbs.
// ---------------------------------------------------------------------------

// Q3 true — vehicle-type profitability.
export interface VehicleTypeProfitabilityRow {
  make: string;
  model: string;
  sold_count: number;
  total_sale_gross: string;
  total_sold_price: string;
  mean_gross_pct: string;
}

export interface VehicleTypeProfitabilityResponse {
  rows: VehicleTypeProfitabilityRow[];
}

export function fetchVehicleTypeProfitability(): Promise<VehicleTypeProfitabilityResponse> {
  return authGetJSON<VehicleTypeProfitabilityResponse>(
    "/admin/analytics/vehicle-type-profitability/",
  );
}

// Q6 — gross-profit trend (sparse per-day series).
export interface GrossProfitPoint {
  sale_date: string; // ISO date (YYYY-MM-DD)
  sale_count: number;
  total_gross_realized: string;
}

export interface GrossProfitTrendResponse {
  window_days: number;
  points: GrossProfitPoint[];
}

export function fetchGrossProfitTrend(
  windowDays = 90,
): Promise<GrossProfitTrendResponse> {
  const params = new URLSearchParams({ window_days: String(windowDays) });
  return authGetJSON<GrossProfitTrendResponse>(
    `/admin/analytics/gross-profit-trend/?${params.toString()}`,
  );
}

// Q8 true — days-from-frontline-to-sale distribution.
export interface InventoryTurnReport {
  sold_count: number;
  mean_days: string | null;
  p50_days: number | null;
  p90_days: number | null;
  min_days: number | null;
  max_days: number | null;
}

export interface InventoryTurnResponse {
  window_days: number;
  report: InventoryTurnReport;
}

export function fetchInventoryTurn(
  windowDays = 90,
): Promise<InventoryTurnResponse> {
  const params = new URLSearchParams({ window_days: String(windowDays) });
  return authGetJSON<InventoryTurnResponse>(
    `/admin/analytics/inventory-turn/?${params.toString()}`,
  );
}

// Q7 — per-buyer recon-cost estimate accuracy.
export interface BuyerAccuracyRow {
  buyer_user_id: number;
  buyer_display: string;
  vehicle_count: number;
  work_order_count: number;
  mean_absolute_variance_pct: string;
  bias_pct: string;
}

export interface BuyerEstimateAccuracyResponse {
  window_days: number;
  buyer_user_id: number | null;
  rows: BuyerAccuracyRow[];
}

export function fetchBuyerEstimateAccuracy(
  windowDays = 90,
  buyerUserId: number | null = null,
): Promise<BuyerEstimateAccuracyResponse> {
  const params = new URLSearchParams({ window_days: String(windowDays) });
  if (buyerUserId !== null) {
    params.set("buyer_user_id", String(buyerUserId));
  }
  return authGetJSON<BuyerEstimateAccuracyResponse>(
    `/admin/analytics/buyer-estimate-accuracy/?${params.toString()}`,
  );
}

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

// Format a stringified dollar amount for display. The backend always
// sends fixed two-decimal-place strings — this helper just adds a
// thousands separator + dollar sign for readability. Never parse
// through Number for arithmetic; the backend owns every total.
export function formatMoney(value: string): string {
  const [dollars, cents] = value.split(".");
  const dollarsWithCommas = dollars
    .replace(/^-/, "")
    .replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const sign = value.startsWith("-") ? "-" : "";
  return `${sign}$${dollarsWithCommas}.${cents ?? "00"}`;
}

// Format a stringified percent for display. Also handles null (the
// aggregation returns null when there is no signal, distinct from
// "the percent happens to be zero").
export function formatPercent(value: string | null): string {
  if (value === null) return "—";
  return `${value}%`;
}

// Human-readable ISO datetime → "Aug 1, 2026, 3:00 AM" style.
export function formatSnapshotAt(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// ISO date-only string (YYYY-MM-DD) → "Aug 1" for compact trend
// chart x-axis labels. Locale-neutral month abbreviation. Kept
// separate from formatSnapshotAt because a date-only value has no
// time component to render.
export function formatShortDate(iso: string): string {
  // Parse as UTC to avoid the "one-day-off in negative-offset
  // timezones" bug that hits `new Date("2026-08-01")` — the JSON
  // wire format is a bare date, not a timestamp.
  const [y, m, d] = iso.split("-").map(Number);
  const date = new Date(Date.UTC(y, (m ?? 1) - 1, d ?? 1));
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}
