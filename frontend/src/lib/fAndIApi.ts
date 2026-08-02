// Milestone 10 · Increment 7 (SESSION_112) — F&I operator UI API client.
//
// Consumes the four M10.7 admin endpoints:
//
//   GET   /admin/f-and-i/deals/                     (deals-in-progress list)
//   GET   /admin/deal-jackets/<contract_pk>/        (per-deal compliance audit)
//   POST  /admin/compliance-records/                (create for contract)
//   PATCH /admin/compliance-records/<pk>/           (partial-update columns)
//
// All money on the wire is a Decimal-as-string per the M9.5 + M10.1
// convention; timestamps are ISO-8601 strings.
//
// Kept as its own module because it consumes the M10 F&I admin
// surface and the F&I operator UI (DealerFandIDeals /
// DealerFandICompliance) is a discrete substrate.

import { authGetJSON, authPatchJSON, authPostJSON } from "@/lib/authFetch";

// ---------------------------------------------------------------------------
// Deals-in-progress list
// ---------------------------------------------------------------------------

export type ContractState = "unsigned" | "signed" | "voided";
export type FundingState =
  | "pending_funding"
  | "funded"
  | "chargedback";

export interface DealListItem {
  contract_id: number;
  contract_state: ContractState;
  contract_type: "risc" | "lease" | "cash";
  signed_at: string | null;
  voided_at: string | null;
  vehicle_stock: string;
  funding_state: FundingState | null;
  funding_amount: string | null;
  chargeback_count: number;
}

export interface DealsListResponse {
  deals: DealListItem[];
}

export interface DealsListFilters {
  state?: ContractState;
  funding_state?: FundingState;
  has_chargebacks?: boolean;
}

export async function fetchDeals(
  filters: DealsListFilters = {},
): Promise<DealListItem[]> {
  const params = new URLSearchParams();
  if (filters.state) params.set("state", filters.state);
  if (filters.funding_state)
    params.set("funding_state", filters.funding_state);
  if (filters.has_chargebacks) params.set("has_chargebacks", "true");
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await authGetJSON<DealsListResponse>(
    `/admin/f-and-i/deals/${suffix}`,
  );
  return response.deals;
}

// ---------------------------------------------------------------------------
// Deal jacket (per-deal compliance-audit view)
// ---------------------------------------------------------------------------

export interface ComplianceRecord {
  id: number;
  reg_z_disclosed_at: string | null;
  ofac_checked_at: string | null;
  ofac_hit: boolean;
  red_flags_reviewed_at: string | null;
  red_flags_notes: string;
  privacy_notice_delivered_at: string | null;
  safeguards_audit_at: string | null;
  adverse_action_sent_at: string | null;
  adverse_action_reason: string;
  retention_expires_at: string | null;
  deal_jacket_url: string;
  notes: string;
}

export interface DealJacketContract {
  id: number;
  contract_type: string;
  state: ContractState;
  signed_at: string | null;
  voided_at: string | null;
  voided_reason: string;
}

export interface DealJacketFunding {
  id: number;
  state: FundingState;
  funded_at: string | null;
  funding_amount: string | null;
}

export interface DealJacketStipulation {
  id: number;
  lender_submission_id: number;
  stip_type: string;
  state: "open" | "cleared" | "waived";
  cleared_at: string | null;
  documented_by_id: number | null;
  evidence_url: string;
  notes: string;
}

export interface DealJacketBEPA {
  id: number;
  product_type: string;
  provider: string;
  cost: string;
  retail_price: string;
  cancelled_at: string | null;
  cancellation_amount: string | null;
  product_agreement_url: string;
}

export interface DealJacketChargeback {
  id: number;
  chargeback_type: string;
  chargeback_date: string;
  chargeback_amount: string;
  recorded_by_id: number | null;
  bepa_id: number | null;
}

export interface DealJacket {
  contract: DealJacketContract;
  compliance: ComplianceRecord | null;
  funding: DealJacketFunding | null;
  stipulations: DealJacketStipulation[];
  back_end_products: DealJacketBEPA[];
  chargebacks: DealJacketChargeback[];
}

interface DealJacketResponse {
  deal_jacket: DealJacket;
}

export async function fetchDealJacket(
  contractId: number,
): Promise<DealJacket> {
  const response = await authGetJSON<DealJacketResponse>(
    `/admin/deal-jackets/${contractId}/`,
  );
  return response.deal_jacket;
}

// ---------------------------------------------------------------------------
// Compliance record create / update
// ---------------------------------------------------------------------------

export interface CreateComplianceRequest {
  contract_id: number;
  deal_jacket_url?: string;
  notes?: string;
}

interface ComplianceResponse {
  compliance: ComplianceRecord;
}

export async function createCompliance(
  payload: CreateComplianceRequest,
): Promise<ComplianceRecord> {
  const response = await authPostJSON<ComplianceResponse>(
    `/admin/compliance-records/`,
    payload,
  );
  return response.compliance;
}

// PATCH accepts any subset of the columns the service verb whitelists.
// Marker fields (`*_at` timestamps) accept ISO strings or null;
// text fields accept strings.
export interface UpdateComplianceRequest {
  reg_z_disclosed_at?: string | null;
  ofac_checked_at?: string | null;
  ofac_hit?: boolean;
  red_flags_reviewed_at?: string | null;
  red_flags_notes?: string;
  privacy_notice_delivered_at?: string | null;
  safeguards_audit_at?: string | null;
  adverse_action_sent_at?: string | null;
  adverse_action_reason?: string;
  deal_jacket_url?: string;
  notes?: string;
}

export async function updateCompliance(
  complianceId: number,
  payload: UpdateComplianceRequest,
): Promise<ComplianceRecord> {
  const response = await authPatchJSON<ComplianceResponse>(
    `/admin/compliance-records/${complianceId}/`,
    payload,
  );
  return response.compliance;
}
