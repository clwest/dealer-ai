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
  // M33.1 derived-status fields (backend: services/f_and_i/credit_application.py
  // + views_f_and_i.py). `has_deal_structure` drives the M33 intake-row chip
  // ("Incoming" when false; "In progress" when true). `latest_deal_structure_id`
  // drives the "Open structure" action — fetches the full row via
  // GET /admin/deal-structures/<int:pk>/ (canonical path). Both null on
  // Incoming rows.
  has_deal_structure: boolean;
  latest_deal_structure_id: number | null;
  // M35.1 derived-status field (backend: services/f_and_i/credit_application.py
  // D2 subquery annotation on latest DealStructure's latest LenderSubmission).
  // Drives the M35 six-state chip:
  //   null when latest DS has no LenderSubmission (or CA has no DS) → M33
  //     Incoming or In progress by prior fields.
  //   "pending"  → "Submitted — awaiting response"
  //   "approved" → "Approved"
  //   "counter"  → "Counter-offer received"
  //   "declined" → "Declined"
  // Current-iteration semantic (per M35.0 §4.8 test case 7): the value
  // reflects the latest DealStructure's latest submission — prior
  // approvals on abandoned structures do not project through.
  latest_lender_submission_status:
    | "pending"
    | "approved"
    | "counter"
    | "declined"
    | null;
  // M35.2 §0.a amendment — pk of the latest LenderSubmission on the
  // latest DealStructure, or null under the same conditions as
  // `latest_lender_submission_status`. Enables the LenderSubmissionResponseForm
  // to PATCH the submission directly without a preceding GET (§5.h
  // explicit deferral of GET single-record endpoint preserved).
  latest_lender_submission_id: number | null;
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

// ---------------------------------------------------------------------------
// Milestone 33 · Increment 2 — DealStructure create + read
// ---------------------------------------------------------------------------
//
// Consumes the M10.2 create endpoint (shipped SESSION_107) + the M33.1
// read endpoint (shipped SESSION_211) per MILESTONE_33_PLANNING.md
// §5.b D2 + D5:
//
//   POST /admin/deal-structures/                (M10.2 create)
//   GET  /admin/deal-structures/<int:pk>/       (M33.1 read; canonical path)
//
// Both gated on IsFinanceManagerOrOwnerAtActiveDealership
// (`_M101_PERMS`) — zero-drift streak preserved at 37 consecutive
// milestones (M10 → M33.1).
//
// Server-computed ratios (`ltv_pct`, `pti_pct`, `dti_pct`) — never
// client-submitted; surface as stringified Decimals or `null` when
// not computable (M10.1-era CA without income captured).
//
// Financial-language contract per D5: form + read view label
// prepopulated values as "sales targets" and F&I-entered values as
// "proposed structure values". Never "lender-approved" /
// "lender-committed" / "actual" — those categories become valid
// only once a verified LenderSubmission or approval workflow exists.

export interface DealStructureProjection {
  id: number;
  credit_application_id: number;
  vehicle_stock: string;
  sale_price: string;
  down_payment: string;
  trade_allowance: string;
  trade_payoff: string;
  taxes: string;
  fees: string;
  amount_financed: string;
  apr: string;
  term_months: number;
  monthly_payment: string;
  back_end_products: unknown[];
  ltv_pct: string | null;
  pti_pct: string | null;
  dti_pct: string | null;
  created_at: string;
  updated_at: string;
}

interface DealStructureEnvelope {
  deal_structure: DealStructureProjection;
}

/**
 * Payload for POST /admin/deal-structures/. All monetary fields are
 * strings (Decimal-as-string per the M9.5 + M10.1 convention) so the
 * caller controls rounding/precision.
 *
 * Truthful-entry contract per D5: the M33.2 UI never sends
 * `taxes` / `fees` / `trade_payoff` / `amount_financed` as silent 0
 * defaults. Blank fields on the form disable submit — this payload
 * always carries explicit operator-entered values (or an explicit
 * "No trade payoff" acknowledgment that submits `0.00` for
 * `trade_payoff`).
 *
 * `back_end_products` intentionally omitted from the M33 UI — defaults
 * to `[]` server-side (truthful: no BEPAs at structuring time).
 */
export interface CreateDealStructureRequest {
  credit_application_id: number;
  vehicle_stock: string;
  sale_price: string;
  amount_financed: string;
  apr: string;
  term_months: number;
  monthly_payment: string;
  down_payment?: string;
  trade_allowance?: string;
  trade_payoff?: string;
  taxes?: string;
  fees?: string;
}

export async function createDealStructure(
  payload: CreateDealStructureRequest,
): Promise<DealStructureProjection> {
  const response = await authPostJSON<DealStructureEnvelope>(
    `/admin/deal-structures/`,
    payload,
  );
  return response.deal_structure;
}

/**
 * Fetches a single DealStructure by pk via the canonical M33.1 path
 * GET /admin/deal-structures/<int:pk>/. 404 on unknown or cross-tenant
 * (fail-closed — the M9.1 / M10.1 / M10.2 / M33.1 shape).
 *
 * Used by the M33.2 "Open structure" action to hydrate the read view
 * once the operator clicks a row's action. The `latest_deal_structure_id`
 * on the CA list projection drives which pk to fetch.
 */
export async function getDealStructure(
  id: number,
): Promise<DealStructureProjection> {
  const response = await authGetJSON<DealStructureEnvelope>(
    `/admin/deal-structures/${id}/`,
  );
  return response.deal_structure;
}

// ---------------------------------------------------------------------------
// Milestone 35 · Increment 2 — LenderSubmission activation (create + status
// update) + LenderProgram FK-discovery
// ---------------------------------------------------------------------------
//
// Consumes three admin endpoints:
//
//   GET   /admin/lender-programs/list/          (M35.1 D4 FK-discovery)
//   POST  /admin/lender-submissions/            (M10.3 shipped; activated
//                                                operationally at M35.2)
//   PATCH /admin/lender-submissions/<int:pk>/   (M10.3 shipped; activated
//                                                operationally at M35.2)
//
// All three gated on IsFinanceManagerOrOwnerAtActiveDealership
// (_M101_PERMS) — zero-drift streak preserved at 39 consecutive milestones
// (M10 → M35).
//
// **UI language contract (M35.0 D6 + D11 + §4.7 verification #7):**
// `record_lender_submission` is a **pure DB insert**; no HTTP call, no
// webhook, no Celery task. UI language MUST reflect this — "Record"
// (past-tense operator action recording an already-completed external
// submission), NEVER "Send" / "Submit to lender" / "Transmit" /
// "Contact lender" / "Submitting…". Verified against a hypothetical
// future scenario where the backend adds outbound transmission —
// language would need to be re-evaluated at that milestone.
//
// **First-loop boundary (M35.0 D8 + §5.h):**
// - Allowed: same-record status update on the latest LenderSubmission
//   via `updateLenderSubmissionStatus`. Any-to-any per M10.3 contract
//   (verified M35.0 §4.2).
// - Deferred: creating a second LenderSubmission on the same
//   DealStructure; alternate-lender resubmission; submission history;
//   multi-submission management.
//
// **State reconciliation:** No `getLenderSubmission` HTTP wrapper — the
// M35.1 audit confirmed no single-record GET endpoint exists (only POST
// + PATCH). Consumers reconcile state via (a) PATCH response body
// carrying the full projection with denormalized `lender_program_name`
// and (b) CA-list refetch after mutation to update derived
// `latest_lender_submission_status`.

export type LenderSubmissionStatus =
  | "pending"
  | "approved"
  | "counter"
  | "declined";

/**
 * Narrow projection returned by GET /admin/lender-programs/list/
 * (M35.1 D4). NO `contact`, `terms_summary`, `is_active`, `created_at`,
 * or `updated_at` — audit-trail data not needed for the FK-discovery
 * workflow. Exposing more would falsely broaden the Lender Fit
 * Recommendations blocker scope (rule / attribute retrieval remains an
 * explicit deferred blocker per M33.0 §5.b D10).
 */
export interface LenderProgramSelectorProjection {
  id: number;
  name: string;
}

interface LenderProgramListEnvelope {
  lender_programs: LenderProgramSelectorProjection[];
}

/**
 * Fetches active LenderPrograms for the LenderSubmissionRecordForm
 * selector. Called on mount by `LenderSubmissionRecordForm`.
 */
export async function listLenderPrograms(): Promise<
  LenderProgramSelectorProjection[]
> {
  const response = await authGetJSON<LenderProgramListEnvelope>(
    `/admin/lender-programs/list/`,
  );
  return response.lender_programs;
}

/**
 * Full projection matching backend `_project_lender_submission`. Note
 * `lender_program_name` is denormalized into the projection so post-
 * mutation UI can display "Submitted to [Name]" without a second
 * fetch. `counter_terms` / `approval_terms` are free-form JSON objects
 * — M35 does NOT capture them; they remain on the projection for
 * completeness but consumers do not surface them.
 */
export interface LenderSubmissionProjection {
  id: number;
  deal_structure_id: number;
  lender_program_id: number;
  lender_program_name: string;
  submitted_at: string;
  status: LenderSubmissionStatus;
  counter_terms: Record<string, unknown>;
  approval_terms: Record<string, unknown>;
  notes: string;
  created_at: string;
  updated_at: string;
}

interface LenderSubmissionEnvelope {
  lender_submission: LenderSubmissionProjection;
}

/**
 * Payload for POST /admin/lender-submissions/ (M10.3 shipped; M35.2
 * activation).
 *
 * NO `submitted_at` field — server records `timezone.now()` at insert
 * (verified M35.0 §4.8 non-blocking correction; no operational back-
 * entry evidence).
 *
 * NO `status` override — server defaults to "pending" per the
 * LENDER_SUBMISSION_STATUS_PENDING contract. The initial submission is
 * ALWAYS pending; response is recorded separately via
 * `updateLenderSubmissionStatus`.
 *
 * NO `counter_terms` / `approval_terms` — structured entry deferred to
 * future milestone if operator evidence surfaces.
 */
export interface RecordLenderSubmissionRequest {
  deal_structure_id: number;
  lender_program_id: number;
  notes?: string;
}

export async function recordLenderSubmission(
  payload: RecordLenderSubmissionRequest,
): Promise<LenderSubmissionProjection> {
  const response = await authPostJSON<LenderSubmissionEnvelope>(
    `/admin/lender-submissions/`,
    payload,
  );
  return response.lender_submission;
}

/**
 * Payload for PATCH /admin/lender-submissions/<pk>/ (M10.3 shipped;
 * M35.2 activation).
 *
 * `status` is required (the response form always changes status).
 * `pending` is intentionally excluded from the type — recording
 * pending as a response is nonsensical; the initial `pending` state
 * comes from create, not update.
 *
 * NO `counter_terms` / `approval_terms` — structured entry deferred.
 */
export interface UpdateLenderSubmissionStatusRequest {
  status: "approved" | "counter" | "declined";
  notes?: string;
}

export async function updateLenderSubmissionStatus(
  id: number,
  payload: UpdateLenderSubmissionStatusRequest,
): Promise<LenderSubmissionProjection> {
  const response = await authPatchJSON<LenderSubmissionEnvelope>(
    `/admin/lender-submissions/${id}/`,
    payload,
  );
  return response.lender_submission;
}
