// Milestone 11 · Increment 6 (SESSION_119) — Sales operator UI API client.
// Extended at Milestone 32 · Increment 2 (SESSION_208) with the M11.3
// DealWriteup wrappers (create / approve / hand-off) + M32.1 read
// wrappers (list / detail).
//
// Consumes the M11.1–M11.5 + M32.1 admin surfaces:
//
//   POST /admin/leads/walk-in/                          (M11.1)
//   POST /admin/leads/phone/                            (M11.1)
//   POST /admin/leads/referral/                         (M11.1)
//   POST /admin/leads/webhook/                          (M11.1)
//   POST /admin/test-drives/                            (M11.2)
//   POST /admin/deal-writeups/                          (M11.3)
//   POST /admin/deal-writeups/<pk>/approve/             (M11.3)
//   POST /admin/deal-writeups/<pk>/hand-off/            (M11.3)
//   GET  /admin/deal-writeups/list/                     (M32.1)
//   GET  /admin/deal-writeups/<pk>/                     (M32.1)
//   POST /admin/follow-up-cadences/                     (M11.4)
//   POST /admin/follow-up-cadences/<pk>/pause/          (M11.4)
//   GET  /admin/follow-up-tasks/                        (M11.4)
//   POST /admin/follow-up-tasks/<pk>/complete/          (M11.4)
//   POST /admin/follow-up-tasks/<pk>/skip/              (M11.4)
//   POST /admin/be-backs/                               (M11.5)
//   POST /admin/be-backs/<pk>/mark-returned/            (M11.5)
//   POST /admin/be-backs/<pk>/mark-no-show/             (M11.5)
//
// M32.2 wires the M11.3 writeup verbs into the sales-manager
// Writeups tab on LeadDetailModal per MILESTONE_32_PLANNING.md
// §5.b D4-revised² + D5 + D6 + D7 + §5.e M32.2.
//
// All money on the wire is Decimal-as-string per the M9.5 + M10.1
// convention; timestamps are ISO-8601.

import { authGetJSON, authPostJSON } from "@/lib/authFetch";

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

export type LeadChannel =
  | "chat"
  | "walk_in"
  | "phone"
  | "listing_form"
  | "referral"
  | "other";

export type FollowUpTemplate =
  | "24hr"
  | "1wk"
  | "30day"
  | "90day"
  | "6mo"
  | "1yr";

export type FollowUpTaskState = "pending" | "completed" | "skipped";

export type BeBackReason =
  | "test_drive"
  | "bring_co_signer"
  | "bring_trade_in"
  | "other";

export type BeBackState = "promised" | "returned" | "no_show";

// ---------------------------------------------------------------------------
// Lead intake (M11.1)
// ---------------------------------------------------------------------------

export interface LeadProjection {
  id: number;
  name: string;
  phone: string;
  email: string;
  channel: LeadChannel;
  referrer_id: number | null;
  dealership_id: number;
  created_at: string;
}

interface LeadEnvelope {
  lead: LeadProjection;
}

export interface CreateBaseLeadRequest {
  name: string;
  phone?: string;
  email?: string;
  notes?: string;
  target_monthly_payment?: string | null;
  down_payment?: string | null;
  trade_in?: string;
  credit_range?: string;
  urgency?: "" | "immediate" | "this_week" | "this_month" | "researching";
}

export interface CreateReferralLeadRequest extends CreateBaseLeadRequest {
  referrer_lead_id?: number | null;
}

export interface CreateWebhookLeadRequest {
  platform: string;
  payload: Record<string, unknown>;
}

export async function createWalkInLead(
  payload: CreateBaseLeadRequest,
): Promise<LeadProjection> {
  const res = await authPostJSON<LeadEnvelope>(
    "/admin/leads/walk-in/",
    payload,
  );
  return res.lead;
}

export async function createPhoneLead(
  payload: CreateBaseLeadRequest,
): Promise<LeadProjection> {
  const res = await authPostJSON<LeadEnvelope>("/admin/leads/phone/", payload);
  return res.lead;
}

export async function createReferralLead(
  payload: CreateReferralLeadRequest,
): Promise<LeadProjection> {
  const res = await authPostJSON<LeadEnvelope>(
    "/admin/leads/referral/",
    payload,
  );
  return res.lead;
}

export async function createWebhookLead(
  payload: CreateWebhookLeadRequest,
): Promise<LeadProjection> {
  const res = await authPostJSON<LeadEnvelope>(
    "/admin/leads/webhook/",
    payload,
  );
  return res.lead;
}

// ---------------------------------------------------------------------------
// Test drive (M11.2)
// ---------------------------------------------------------------------------

export interface TestDriveProjection {
  id: number;
  lead_id: number;
  vehicle_id: number;
  dealership_id: number;
  driven_by_user_id: number | null;
  driven_at: string;
  duration_minutes: number | null;
  route_notes: string;
  customer_reaction: string;
  objections_captured: string[];
  next_action: string;
  created_at: string;
  updated_at: string;
}

export interface CreateTestDriveRequest {
  lead_id: number;
  vehicle_id: number;
  driven_at?: string | null;
  duration_minutes?: number | null;
  route_notes?: string;
  customer_reaction?: string;
  objections_captured?: string[];
  next_action?: string;
}

interface TestDriveEnvelope {
  test_drive: TestDriveProjection;
}

export async function createTestDrive(
  payload: CreateTestDriveRequest,
): Promise<TestDriveProjection> {
  const res = await authPostJSON<TestDriveEnvelope>(
    "/admin/test-drives/",
    payload,
  );
  return res.test_drive;
}

export interface TestDriveListFilters {
  lead_id?: number;
  vehicle_id?: number;
  driven_since?: string;
}

export interface TestDriveListResponse {
  count: number;
  results: TestDriveProjection[];
}

export async function listTestDrives(
  filters: TestDriveListFilters = {},
): Promise<TestDriveListResponse> {
  const params = new URLSearchParams();
  if (filters.lead_id) params.set("lead_id", String(filters.lead_id));
  if (filters.vehicle_id) params.set("vehicle_id", String(filters.vehicle_id));
  if (filters.driven_since) params.set("driven_since", filters.driven_since);
  const qs = params.toString();
  return authGetJSON<TestDriveListResponse>(
    `/admin/test-drives/list/${qs ? `?${qs}` : ""}`,
  );
}

// ---------------------------------------------------------------------------
// Admin vehicle list (M25.2) — tenant vehicles for operator pickers.
// ---------------------------------------------------------------------------
//
// Added at M25.2 open per MILESTONE_25_PLANNING.md §5.e when
// empirical verification surfaced that no tenant-wide admin
// vehicle-list endpoint existed. The M25.2 test-drive form picker
// consumes this to render "Suggested" (from
// `detail.interested_vehicles`) + "All inventory" (this endpoint's
// results) selection zones. Compact projection — enough to render
// year/make/model/trim + thumbnail + price without hitting per-stock
// endpoints.

export interface AdminVehicleRow {
  id: number;
  stock_number: string;
  year: number;
  make: string;
  model: string;
  trim: string;
  condition: string;
  price: string;
  image_url: string;
  is_available: boolean;
  display_name: string;
}

export interface AdminVehicleListResponse {
  count: number;
  results: AdminVehicleRow[];
}

export interface AdminVehicleListFilters {
  search?: string;
  condition?: "new" | "used" | "certified";
  is_available?: boolean;
}

export async function listAdminVehicles(
  filters: AdminVehicleListFilters = {},
): Promise<AdminVehicleListResponse> {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.condition) params.set("condition", filters.condition);
  if (filters.is_available !== undefined) {
    params.set("is_available", filters.is_available ? "true" : "false");
  }
  const qs = params.toString();
  return authGetJSON<AdminVehicleListResponse>(
    `/admin/vehicles/${qs ? `?${qs}` : ""}`,
  );
}

// ---------------------------------------------------------------------------
// Follow-up cadence + tasks (M11.4)
// ---------------------------------------------------------------------------

export interface CadenceProjection {
  id: number;
  lead_id: number;
  dealership_id: number;
  template: FollowUpTemplate;
  started_at: string;
  is_active: boolean;
  task_count: number;
  created_at: string;
  updated_at: string;
}

export interface FollowUpTaskProjection {
  id: number;
  cadence_id: number;
  dealership_id: number;
  due_at: string;
  state: FollowUpTaskState;
  completed_by_user_id: number | null;
  completed_at: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface FollowUpTaskListResponse {
  count: number;
  results: FollowUpTaskProjection[];
}

export interface FollowUpTaskListFilters {
  state?: FollowUpTaskState;
  due_before?: string;
  limit?: number;
}

interface CadenceEnvelope {
  cadence: CadenceProjection;
}

interface TaskEnvelope {
  task: FollowUpTaskProjection;
}

export interface CreateCadenceRequest {
  lead_id: number;
  template: FollowUpTemplate;
  started_at?: string | null;
}

export async function createCadence(
  payload: CreateCadenceRequest,
): Promise<CadenceProjection> {
  const res = await authPostJSON<CadenceEnvelope>(
    "/admin/follow-up-cadences/",
    payload,
  );
  return res.cadence;
}

export async function pauseCadence(
  cadenceId: number,
): Promise<CadenceProjection> {
  const res = await authPostJSON<CadenceEnvelope>(
    `/admin/follow-up-cadences/${cadenceId}/pause/`,
    {},
  );
  return res.cadence;
}

export async function listFollowUpTasks(
  filters: FollowUpTaskListFilters = {},
): Promise<FollowUpTaskListResponse> {
  const params = new URLSearchParams();
  if (filters.state) params.set("state", filters.state);
  if (filters.due_before) params.set("due_before", filters.due_before);
  if (filters.limit) params.set("limit", String(filters.limit));
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return authGetJSON<FollowUpTaskListResponse>(
    `/admin/follow-up-tasks/${suffix}`,
  );
}

export async function completeTask(
  taskId: number,
  notes = "",
): Promise<FollowUpTaskProjection> {
  const res = await authPostJSON<TaskEnvelope>(
    `/admin/follow-up-tasks/${taskId}/complete/`,
    { notes },
  );
  return res.task;
}

export async function skipTask(
  taskId: number,
  notes = "",
): Promise<FollowUpTaskProjection> {
  const res = await authPostJSON<TaskEnvelope>(
    `/admin/follow-up-tasks/${taskId}/skip/`,
    { notes },
  );
  return res.task;
}

// ---------------------------------------------------------------------------
// Be-back tracking (M11.5)
// ---------------------------------------------------------------------------

export interface BeBackProjection {
  id: number;
  lead_id: number;
  dealership_id: number;
  promised_at: string;
  promised_reason: BeBackReason;
  actual_return_at: string | null;
  state: BeBackState;
  notes: string;
  created_at: string;
  updated_at: string;
}

interface BeBackEnvelope {
  be_back: BeBackProjection;
}

export interface CreateBeBackRequest {
  lead_id: number;
  promised_at: string;
  promised_reason: BeBackReason;
  notes?: string;
}

export async function createBeBack(
  payload: CreateBeBackRequest,
): Promise<BeBackProjection> {
  const res = await authPostJSON<BeBackEnvelope>("/admin/be-backs/", payload);
  return res.be_back;
}

export interface BeBackListFilters {
  state?: BeBackState;
  promised_since?: string;
}

export interface BeBackListResponse {
  count: number;
  results: BeBackProjection[];
}

export async function listBeBacks(
  filters: BeBackListFilters = {},
): Promise<BeBackListResponse> {
  const params = new URLSearchParams();
  if (filters.state) params.set("state", filters.state);
  if (filters.promised_since)
    params.set("promised_since", filters.promised_since);
  const qs = params.toString();
  return authGetJSON<BeBackListResponse>(
    `/admin/be-backs/list/${qs ? `?${qs}` : ""}`,
  );
}

export async function markBeBackReturned(
  beBackId: number,
  actualReturnAt?: string,
  notes = "",
): Promise<BeBackProjection> {
  const body: Record<string, unknown> = { notes };
  if (actualReturnAt) body.actual_return_at = actualReturnAt;
  const res = await authPostJSON<BeBackEnvelope>(
    `/admin/be-backs/${beBackId}/mark-returned/`,
    body,
  );
  return res.be_back;
}

export async function markBeBackNoShow(
  beBackId: number,
  notes = "",
): Promise<BeBackProjection> {
  const res = await authPostJSON<BeBackEnvelope>(
    `/admin/be-backs/${beBackId}/mark-no-show/`,
    { notes },
  );
  return res.be_back;
}

// ---------------------------------------------------------------------------
// Deal writeup (M11.3 verbs + M32.1 read wrappers)
// ---------------------------------------------------------------------------
//
// M32.2 wires the M11.3 backend verbs into the sales-manager Writeups
// tab. State is derived at the projection layer from timestamp
// presence: pending / approved / handed_off (see
// `derivedWriteupState()` helper).

export type DealWriteupState = "pending" | "approved" | "handed_off";

export interface DealWriteupProjection {
  id: number;
  lead_id: number;
  vehicle_id: number;
  dealership_id: number;
  vehicle_price: string | null;
  trade_allowance: string | null;
  down_payment: string | null;
  monthly_payment_target: string | null;
  term_months_target: number | null;
  apr_target: string | null;
  write_up_at: string;
  written_up_by_user_id: number | null;
  sales_manager_approved_at: string | null;
  sales_manager_approved_by_user_id: number | null;
  handed_off_to_fandi_at: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface CreateDealWriteupRequest {
  lead_id: number;
  vehicle_id: number;
  write_up_at?: string | null;
  vehicle_price?: string | null;
  trade_allowance?: string | null;
  down_payment?: string | null;
  monthly_payment_target?: string | null;
  term_months_target?: number | null;
  apr_target?: string | null;
  notes?: string;
}

interface DealWriteupEnvelope {
  deal_writeup: DealWriteupProjection;
}

interface DealWriteupListEnvelope {
  deal_writeups: DealWriteupProjection[];
}

interface DealWriteupHandoffEnvelope {
  deal_writeup: DealWriteupProjection;
  credit_application: {
    id: number;
    lead_id: number | null;
    source_format: string;
    captured_at: string;
  };
}

export interface DealWriteupListFilters {
  leadId?: number;
  state?: DealWriteupState;
}

/**
 * Derive UI state from timestamp presence.
 *
 * Mirrors the backend service verb `list_deal_writeups` derivation
 * (`services/deal_writeups/deal_writeup.py`). Kept in sync manually —
 * both surfaces read the same three timestamp fields on the writeup.
 */
export function derivedWriteupState(
  writeup: DealWriteupProjection,
): DealWriteupState {
  if (writeup.handed_off_to_fandi_at !== null) return "handed_off";
  if (writeup.sales_manager_approved_at !== null) return "approved";
  return "pending";
}

export async function listDealWriteups(
  filters: DealWriteupListFilters = {},
): Promise<DealWriteupProjection[]> {
  const params = new URLSearchParams();
  if (filters.leadId !== undefined) {
    params.set("lead_id", String(filters.leadId));
  }
  if (filters.state !== undefined) {
    params.set("state", filters.state);
  }
  const qs = params.toString();
  const res = await authGetJSON<DealWriteupListEnvelope>(
    `/admin/deal-writeups/list/${qs ? `?${qs}` : ""}`,
  );
  return res.deal_writeups;
}

export async function getDealWriteup(
  pk: number,
): Promise<DealWriteupProjection> {
  const res = await authGetJSON<DealWriteupEnvelope>(
    `/admin/deal-writeups/${pk}/`,
  );
  return res.deal_writeup;
}

export async function createDealWriteup(
  payload: CreateDealWriteupRequest,
): Promise<DealWriteupProjection> {
  const res = await authPostJSON<DealWriteupEnvelope>(
    "/admin/deal-writeups/",
    payload,
  );
  return res.deal_writeup;
}

export async function approveDealWriteup(
  pk: number,
): Promise<DealWriteupProjection> {
  const res = await authPostJSON<DealWriteupEnvelope>(
    `/admin/deal-writeups/${pk}/approve/`,
    {},
  );
  return res.deal_writeup;
}

export async function handOffDealWriteup(
  pk: number,
): Promise<DealWriteupHandoffEnvelope> {
  return authPostJSON<DealWriteupHandoffEnvelope>(
    `/admin/deal-writeups/${pk}/hand-off/`,
    {},
  );
}
