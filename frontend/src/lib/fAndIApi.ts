// Milestone 10 · Increment 7 (SESSION_112) — F&I operator UI API client.
// Extended at Milestone 32 · Increment 3 (SESSION_209) with the
// M32.1 credit-application list wrapper for the F&I intake queue.
//
// Consumes the M10.7 + M32.1 admin endpoints:
//
//   GET   /admin/f-and-i/deals/                     (M10.7 deals-in-progress list)
//   GET   /admin/deal-jackets/<contract_pk>/        (M10.7 per-deal compliance audit)
//   POST  /admin/compliance-records/                (M10.7 create for contract)
//   PATCH /admin/compliance-records/<pk>/           (M10.7 partial-update columns)
//   GET   /admin/credit-applications/list/          (M32.1 F&I intake queue)
//
// All money on the wire is a Decimal-as-string per the M9.5 + M10.1
// convention; timestamps are ISO-8601 strings.
//
// Kept as its own module because it consumes the M10 F&I admin
// surface and the F&I operator UI (DealerFandIDeals /
// DealerFandICompliance / DealerFandIIncoming) is a discrete
// substrate.

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

// ---------------------------------------------------------------------------
// Milestone 32 · Increment 3 — F&I intake queue
// ---------------------------------------------------------------------------
//
// Consumes GET /admin/credit-applications/list/ per M32.0 §5.b D3.
// Gated on IsFinanceManagerOrOwnerAtActiveDealership (first F&I-role-
// gated list endpoint per M32.0 §5.b D10). Fail-explicit filter
// validation on the backend — invalid `intake`, `lead_id`, or
// `since` values return 400 with a clear message. `intake=false` is
// reserved-and-rejected per §5.h.
//
// Projection includes writeup context via the M32.1 D9-revised²
// nullable OneToOneField backpointer (`deal_writeup`). When the CA
// was created via `hand_off_to_fandi`, writeup_context is populated
// deterministically (no text-parsing of `notes`). When the CA was
// created directly via M10.1, writeup_context is `null`.

export interface CreditApplicationLead {
  id: number;
  name: string;
  phone: string;
  email: string;
}

export interface CreditApplicationVehicle {
  id: number;
  stock_number: string;
  year: number;
  make: string;
  model: string;
}

export interface CreditApplicationTerms {
  vehicle_price: string | null;
  trade_allowance: string | null;
  down_payment: string | null;
  monthly_payment_target: string | null;
  term_months_target: number | null;
  apr_target: string | null;
}

export interface CreditApplicationWriteupContext {
  deal_writeup_id: number;
  written_up_by_user_id: number | null;
  sales_manager_approved_by_user_id: number | null;
  handed_off_to_fandi_at: string | null;
  lead: CreditApplicationLead;
  vehicle: CreditApplicationVehicle;
  terms: CreditApplicationTerms;
}

export interface CreditApplicationProjection {
  id: number;
  lead_id: number | null;
  sale_id: number | null;
  applicant_full_name: string;
  applicant_ssn_last4: string;
  source_format: string;
  status: string;
  captured_at: string;
  retention_expires_at: string;
  notes: string;
  created_at: string;
  updated_at: string;
  writeup_context: CreditApplicationWriteupContext | null;
}

interface CreditApplicationListEnvelope {
  credit_applications: CreditApplicationProjection[];
}

export interface CreditApplicationListFilters {
  /**
   * When true, filters to CAs where no downstream Contract exists
   * (pre-contract F&I intake queue). Sent as `?intake=true`.
   *
   * The backend fails explicitly on any other value (`false`, `1`,
   * `TRUE`, empty, etc. → 400). This wrapper only sends `true`
   * when the caller passes `true`; anything else is omitted, which
   * the backend treats as unfiltered.
   */
  intake?: boolean;
  leadId?: number;
  since?: string;
}

export async function fetchCreditApplications(
  filters: CreditApplicationListFilters = {},
): Promise<CreditApplicationProjection[]> {
  const params = new URLSearchParams();
  if (filters.intake === true) params.set("intake", "true");
  if (filters.leadId !== undefined) {
    params.set("lead_id", String(filters.leadId));
  }
  if (filters.since !== undefined) params.set("since", filters.since);
  const qs = params.toString();
  const response = await authGetJSON<CreditApplicationListEnvelope>(
    `/admin/credit-applications/list/${qs ? `?${qs}` : ""}`,
  );
  return response.credit_applications;
}
