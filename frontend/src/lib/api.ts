// API helpers for the Dealer AI backend.
// Vite dev server proxies /api → http://127.0.0.1:8000 (see vite.config.ts).
// Override with VITE_API_PROXY_TARGET in frontend/.env.local, or set
// VITE_API_BASE to bypass the proxy entirely (requires CORS).
//
// Milestone 1 · Increment 4E — operator endpoints (admin/*, advisor/*,
// manager-chat, onboarding mutation, logo upload) go through
// `authFetch` from `./authFetch` so session cookies + CSRF are
// handled uniformly and 401 / 403 propagate as typed errors. Public
// endpoints (customer chat, vehicle Q&A, public team page, and the
// branding GET on /onboarding/profile/) stay on plain fetch so a
// broken session can never break a customer-facing page.

import {
  authDelete,
  authGetJSON,
  authPatchJSON,
  authPostForm,
  authPostJSON,
  authPutJSON,
} from "@/lib/authFetch";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/dealer-ai";

export interface Vehicle {
  id: number;
  stock_number: string;
  vin: string;
  year: number;
  make: string;
  model: string;
  trim: string;
  body_style: string;
  condition: string;
  mileage: number;
  price: string;
  msrp: string | null;
  exterior_color: string;
  interior_color: string;
  drivetrain: string;
  transmission: string;
  fuel_type: string;
  engine: string;
  features: string[];
  description: string;
  image_url: string;
  display_name: string;
  // Phase 8s/UX — per-turn budget annotations attached by the backend
  // when the request was a budget-constrained vehicle search. Null on
  // non-budget turns. budget_fit drives the chat-card badge ("in
  // budget" vs "close to target" vs "above target").
  budget_fit?: "fit" | "near_fit" | "over_budget" | null;
  estimated_payment?: number | null;
  payment_delta?: number | null;
  // Phase 8s/UX (lever-flex presentation) — when a card surfaces as a
  // "if you flex one lever from your stated ask" option, the backend
  // tags it with the kind of compromise required and a human-readable
  // explainer ("Needs 84-mo term", "This is 2WD — flexible-drivetrain
  // option"). The chat-card renders a second badge keyed by kind
  // alongside the existing budget_fit badge so the customer can tell
  // a strict match from a labeled flex card at a glance.
  lever_flex_kind?:
    | "longer_term"
    | "more_down"
    | "drivetrain_flex"
    | "stretch_payment"
    | null;
  lever_flex_explainer?: string | null;
}

export interface ChatMessage {
  id: number;
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  matched_vehicles: Vehicle[];
  created_at: string;
}

export interface ChatSession {
  id: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  metadata: Record<string, unknown>;
  messages: ChatMessage[];
  created_at: string;
}

export interface StartChatResponse {
  session: ChatSession;
  assistant_message: ChatMessage | null;
  matched_vehicles: Vehicle[];
}

export interface SendMessageResponse {
  assistant_message: ChatMessage;
  matched_vehicles: Vehicle[];
}

export interface LeadInput {
  session?: string | null;
  name: string;
  phone?: string;
  email?: string;
  target_monthly_payment?: number | null;
  down_payment?: number | null;
  trade_in?: string;
  urgency?: string;
  interested_vehicles?: number[];
  notes?: string;
}

export interface LeadResponse extends LeadInput {
  id: number;
  created_at: string;
  handed_off: boolean;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} failed (${res.status}): ${text}`);
  }
  return res.json() as Promise<T>;
}

export function startDealerChat(input: {
  customer_name?: string;
  customer_email?: string;
  customer_phone?: string;
  initial_message?: string;
}) {
  return postJSON<StartChatResponse>("/chat/start/", input);
}

export function sendDealerMessage(sessionId: string, message: string) {
  return postJSON<SendMessageResponse>("/chat/message/", {
    session_id: sessionId,
    message,
  });
}

export function createDealerLead(lead: LeadInput) {
  return postJSON<LeadResponse>("/leads/", lead);
}

// ---- Admin / dashboard endpoints ------------------------------------------

export interface VehicleSummary {
  id: number;
  stock_number: string;
  year: number;
  make: string;
  model: string;
  trim: string;
  condition: string;
  price: string;
  display_name: string;
}

export interface SalespersonAssignment {
  id: number;
  name: string;
  slug: string;
  title: string;
  photo_url: string;
}

export interface AdminLead {
  id: number;
  session_id: string | null;
  name: string;
  phone: string;
  email: string;
  target_monthly_payment: string | null;
  down_payment: string | null;
  trade_in: string;
  urgency: string;
  credit_range: string;
  interested_vehicles: VehicleSummary[];
  conversation_summary: string;
  recommended_next_action: string;
  handed_off: boolean;
  assigned_to: SalespersonAssignment | null;
  assigned_at: string | null;
  created_at: string;
}

export interface AdminChatSessionRow {
  id: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  extracted_profile: Record<string, unknown>;
  lead_created: boolean;
  message_count: number;
  last_message: {
    role: string;
    content: string;
    created_at: string;
  } | null;
  created_at: string;
  updated_at: string;
}

export interface ListResponse<T> {
  count: number;
  limit: number;
  results: T[];
}

export interface TrendsResponse {
  generated_at: string;
  total_chat_sessions: number;
  total_leads: number;
  total_leads_last_7d: number;
  average_target_monthly_payment: number | null;
  budget_mismatch_count: number;
  top_requested_models: { value: string; count: number }[];
  top_requested_vehicle_types: { value: string; count: number }[];
  most_selected_vehicles: {
    id: number;
    stock_number: string;
    display_name: string;
    price: string;
    lead_count: number;
  }[];
  recent_customer_intents: {
    session_id: string;
    intent: string;
    vehicle_type: string | null;
    model: string | null;
    target_monthly_payment: number | null;
    urgency: string | null;
    updated_at: string;
  }[];
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} failed (${res.status}): ${text}`);
  }
  return res.json() as Promise<T>;
}

export interface AdminLeadsQuery {
  limit?: number;
  handed_off?: boolean;
  urgency?: string[]; // immediate / this_week / this_month / researching
  since?: "24h" | "7d" | "30d";
  ordering?: "urgency" | "created_at";
}

export function fetchAdminLeads(opts: AdminLeadsQuery | number = {}) {
  // Accept either the legacy `fetchAdminLeads(25)` form or the
  // Manager-Phase-1 options object. The number form is preserved for
  // back-compat with the existing dashboard call site.
  const params = new URLSearchParams();
  const o: AdminLeadsQuery = typeof opts === "number" ? { limit: opts } : opts;
  if (o.limit != null) params.set("limit", String(o.limit));
  if (o.handed_off != null) params.set("handed_off", String(o.handed_off));
  if (o.urgency && o.urgency.length > 0)
    params.set("urgency", o.urgency.join(","));
  if (o.since) params.set("since", o.since);
  if (o.ordering) params.set("ordering", o.ordering);
  const qs = params.toString();
  return authGetJSON<ListResponse<AdminLead>>(
    `/admin/leads/${qs ? `?${qs}` : ""}`,
  );
}

// ---- Manager Phase 1: audit/safety panel ----------------------------------

export type AuditCategory =
  | "pre_llm_guard"
  | "post_llm_rewrite"
  | "post_llm_override"
  | "scrub"
  | "unknown";

export type AuditSeverity = "info" | "warn" | "muted";

export interface AuditFlagBucket {
  flag: string;
  count: number;
  category: AuditCategory;
  severity: AuditSeverity;
}

export interface AuditEvent {
  session_id: string | null;
  message_id: number;
  created_at: string;
  flag: string;
  category: AuditCategory;
  user_message_excerpt: string;
  assistant_excerpt: string;
  scrubs: string[];
  override_kind: string | null;
}

export interface AuditEventsResponse {
  since: "24h" | "7d" | "30d";
  window_hours: number;
  generated_at: string;
  totals: {
    total_guard_events: number;
    pre_llm_short_circuits: number;
    post_llm_rewrites: number;
    post_llm_overrides: number;
    scrubs_fired: number;
  };
  by_flag: AuditFlagBucket[];
  recent_events: AuditEvent[];
}

export function fetchAuditEvents(
  opts: { since?: "24h" | "7d" | "30d"; limit?: number } = {},
) {
  const params = new URLSearchParams();
  if (opts.since) params.set("since", opts.since);
  if (opts.limit != null) params.set("limit", String(opts.limit));
  const qs = params.toString();
  return authGetJSON<AuditEventsResponse>(
    `/admin/audit-events/${qs ? `?${qs}` : ""}`,
  );
}

export function fetchAdminChatSessions(limit = 25) {
  return authGetJSON<ListResponse<AdminChatSessionRow>>(
    `/admin/chat-sessions/?limit=${limit}`,
  );
}

export function fetchAdminTrends() {
  return authGetJSON<TrendsResponse>(`/admin/trends/`);
}

// ---- Manager Phase 2: sales pipeline + recommended actions ----------------

export type PipelineStageKey =
  | "high_intent"
  | "new"
  | "needs_handoff"
  | "researching"
  | "contacted";

export interface PipelineLeadVehicle {
  id: number;
  stock_number: string;
  display_name: string;
  price: string;
}

export interface PipelineLead {
  id: number;
  name: string;
  phone: string;
  email: string;
  urgency: string;
  target_monthly_payment: string | null;
  down_payment: string | null;
  handed_off: boolean;
  created_at: string;
  assigned_to: SalespersonAssignment | null;
  assigned_at: string | null;
  interested_vehicles: PipelineLeadVehicle[];
}

export interface PipelineStage {
  key: PipelineStageKey;
  label: string;
  count: number;
  leads: PipelineLead[];
}

export type DemandTier = "mismatch" | "tight" | "healthy";

export interface DemandBucket {
  band_label: string;
  monthly_low: number;
  monthly_high: number | null;
  price_low: number;
  price_high: number | null;
  lead_count: number;
  vehicle_count: number;
  ratio: number;
  tier: DemandTier;
  suggestion: string | null;
}

export interface DemandVsSupply {
  down_payment_assumption: number;
  buckets: DemandBucket[];
}

export type RecommendedActionPriority = "high" | "medium" | "low";
export type RecommendedActionCategory = "inventory" | "sales" | "marketing";

export interface RecommendedActionCTA {
  kind:
    | "view_leads_in_band"
    | "view_high_intent_leads"
    | "view_aging_leads"
    | string;
  params?: Record<string, unknown>;
}

export interface RecommendedAction {
  id: string;
  category: RecommendedActionCategory;
  priority: RecommendedActionPriority;
  title: string;
  explanation: string;
  action_text: string;
  evidence: Record<string, unknown>;
  cta: RecommendedActionCTA | null;
}

export interface PipelineResponse {
  generated_at: string;
  stages: PipelineStage[];
  demand_vs_supply: DemandVsSupply;
  recommended_actions: RecommendedAction[];
}

export function fetchAdminPipeline() {
  return authGetJSON<PipelineResponse>(`/admin/pipeline/`);
}

// ---- Manager Phase 3: ad-copy generation ----------------------------------

export interface AdCopyVariant {
  platform_hint:
    | "facebook"
    | "instagram"
    | "email"
    | "google_search"
    | "showroom"
    | string;
  headline: string;
  body: string;
  cta: string;
  scrubs_fired: string[];
}

export interface AdCopyResponse {
  recommendation_id: string;
  variants: AdCopyVariant[];
  warnings: string[];
  vehicles_used: Vehicle[];
}

export interface AdCopyRequest {
  recommendation: RecommendedAction;
  vehicle_id?: number | null;
}

export function generateAdCopy(req: AdCopyRequest) {
  return authPostJSON<AdCopyResponse>(`/admin/ad-copy/`, {
    recommendation: req.recommendation,
    vehicle_id: req.vehicle_id ?? null,
  });
}

// ---- Manager Phase 4: salespeople + assignment + advisor workspace --------

export interface SalespersonAdmin {
  id: number;
  name: string;
  slug: string;
  title: string;
  email: string;
  phone: string;
  photo_url: string;
  bio: string;
  specialties: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SalespersonPublic {
  id: number;
  name: string;
  slug: string;
  title: string;
  photo_url: string;
  specialties: string[];
  is_active: boolean;
}

export interface AdvisorWorkspaceResponse {
  salesperson: SalespersonPublic;
  open_leads: AdminLead[];
  contacted_leads: AdminLead[];
  counts: { open: number; contacted: number };
}

export interface FollowUpDraft {
  channel: "sms" | "email";
  subject: string | null;
  body: string;
  scrubs_fired: string[];
  /**
   * "llm" when the draft came from the model. "fallback" when the
   * service synthesized a deterministic draft from real lead/advisor
   * data (e.g. LLM offline, prose-only reply, every variant scrubbed).
   * Optional for forward-compat with older payloads.
   */
  source?: "llm" | "fallback";
}

export interface FollowUpResponse {
  lead_id: number;
  salesperson_slug: string;
  channel: "sms" | "email";
  tone: "warm" | "direct";
  drafts: FollowUpDraft[];
  warnings: string[];
}

export function fetchAdminSalespeople(opts: { activeOnly?: boolean } = {}) {
  const qs = opts.activeOnly ? "?active=true" : "";
  return authGetJSON<{ count: number; results: SalespersonAdmin[] }>(
    `/admin/salespeople/${qs}`,
  );
}

export function fetchPublicSalespeople() {
  return getJSON<{ count: number; results: SalespersonPublic[] }>(
    `/salespeople/`,
  );
}

export function fetchSalesperson(slug: string) {
  return getJSON<SalespersonPublic>(`/salespeople/${slug}/`);
}

export function assignLead(
  leadId: number,
  salespersonId: number | null,
) {
  return authPostJSON<AdminLead>(`/admin/lead/${leadId}/assign/`, {
    salesperson_id: salespersonId,
  });
}

export function fetchAdvisorWorkspace(slug: string) {
  return authGetJSON<AdvisorWorkspaceResponse>(`/advisor/${slug}/`);
}

export function generateFollowUpDrafts(
  slug: string,
  leadId: number,
  body: { channel?: "sms" | "email"; tone?: "warm" | "direct" } = {},
) {
  return authPostJSON<FollowUpResponse>(
    `/advisor/${slug}/lead/${leadId}/follow-up/`,
    {
      channel: body.channel ?? "sms",
      tone: body.tone ?? "warm",
    },
  );
}

export function fetchSessionDetail(sessionId: string) {
  return getJSON<ChatSession>(`/chat/session/${sessionId}/`);
}

// ---- Vehicle detail / vehicle ask -----------------------------------------

export interface PaymentEstimate {
  term_months: number;
  monthly_payment: number;
  total_financed: number;
  apr: number;
  down_payment: number;
  trade_in_value: number;
  taxes: number;
  fees: number;
}

export interface VehicleDetailResponse {
  vehicle: Vehicle;
  payment_estimates: PaymentEstimate[];
  affordability_notes: string[];
  similar_vehicles: Vehicle[];
}

export interface VehicleAskResponse extends VehicleDetailResponse {
  answer: string;
}

export function fetchVehicleDetail(
  vehicleId: number,
  opts: {
    sessionId?: string | null;
    targetMonthly?: number | null;
    downPayment?: number | null;
  } = {},
) {
  const params = new URLSearchParams();
  if (opts.sessionId) params.set("session_id", opts.sessionId);
  if (opts.targetMonthly != null)
    params.set("target_monthly_payment", String(opts.targetMonthly));
  if (opts.downPayment != null)
    params.set("down_payment", String(opts.downPayment));
  const qs = params.toString();
  return getJSON<VehicleDetailResponse>(
    `/vehicles/${vehicleId}/${qs ? `?${qs}` : ""}`,
  );
}

export function askVehicleQuestion(
  vehicleId: number,
  body: {
    question: string;
    sessionId?: string | null;
    targetMonthly?: number | null;
    downPayment?: number | null;
  },
) {
  return postJSON<VehicleAskResponse>(`/vehicles/${vehicleId}/ask/`, {
    question: body.question,
    session_id: body.sessionId ?? null,
    target_monthly_payment: body.targetMonthly ?? null,
    down_payment: body.downPayment ?? null,
  });
}

// ---- Lead detail / handoff / demo reset -----------------------------------

export interface LeadDetailResponse {
  lead: LeadResponse & {
    interested_vehicles: number[];
    conversation_summary: string;
    recommended_next_action: string;
    credit_range: string;
  };
  interested_vehicles: Vehicle[];
  session_profile: Record<string, unknown>;
  messages: ChatMessage[];
}

export interface HandoffPacket {
  lead_id: number;
  generated_at: string;
  customer: { name: string; phone: string; email: string };
  interested_vehicles: {
    id: number;
    stock_number: string;
    display_name: string;
    price: string;
    url: string;
  }[];
  budget: {
    target_monthly_payment: string | null;
    down_payment: string | null;
  };
  trade_in: string;
  credit_range: string;
  urgency: string;
  urgency_label: string;
  conversation_summary: string;
  recommended_next_action: string;
  suggested_message: string;
  session_id: string | null;
  text: string;
  handed_off: boolean;
}

export interface DemoResetResponse {
  ok: boolean;
  cleared: { chat_messages: number; chat_sessions: number; leads: number };
  deleted_imported_vehicles: number;
  demo_vehicles: number;
  imported_vehicles_remaining: number;
}

export function fetchLeadDetail(leadId: number) {
  return authGetJSON<LeadDetailResponse>(`/admin/lead/${leadId}/`);
}

export function buildLeadHandoff(
  leadId: number,
  opts: { markHandedOff?: boolean } = {},
) {
  return authPostJSON<HandoffPacket>(`/admin/lead/${leadId}/handoff/`, {
    mark_handed_off: opts.markHandedOff ?? false,
  });
}

export function resetDemo(
  opts: { reloadDemoVehicles?: boolean; deleteImportedVehicles?: boolean } = {},
) {
  return postJSON<DemoResetResponse>(`/demo/reset/`, {
    reload_demo_vehicles: opts.reloadDemoVehicles ?? true,
    delete_imported_vehicles: opts.deleteImportedVehicles ?? false,
  });
}

export interface LoadScenariosResponse {
  ok: boolean;
  reset: boolean;
  chat_sessions: number;
  leads: number;
  stdout: string;
}

export function loadDemoScenarios(opts: { reset?: boolean } = {}) {
  return postJSON<LoadScenariosResponse>(`/demo/scenarios/`, {
    reset: opts.reset ?? false,
  });
}

// ---- SESSION_008: dealer onboarding profile (singleton) -------------------

export interface OnboardingProfilePayload {
  dealership_name: string;
  store_location: string;
  main_brands: string;
  sales_phone: string;
  website: string;
  /** SESSION_021 — hosted logo URL. Empty string falls back to
   *  DEFAULT_DEALER.logoPath via useBrand(). */
  logo_url: string;
  sales_tone: string;
  pricing_comfort: string;
  appointment_preference: string;
  lead_handoff_style: string;
  salesperson_name: string;
  salesperson_role: string;
  salesperson_phone: string;
  salesperson_email: string;
  salesperson_specialties: string;
  salesperson_preferred_tone: string;
  salesperson_intro: string;
  dealership_greeting: string;
  approved_phrases: string;
  banned_phrases: string;
  escalation_rule: string;
  payment_disclaimer: string;
  inventory_connected: boolean;
  finance_rules_reviewed: boolean;
  salespeople_added: boolean;
  demo_prompts_tested: boolean;
  pilot_approved: boolean;
  // SESSION_032 — indie shape-of-business. Blank / false defaults
  // mean "unset — backend resolver falls back to env or Copper Canyon
  // default"; see services/dealer_config.get_dealer_profile.
  dealer_type: "" | "independent" | "franchise";
  bhph_enabled: boolean;
  /** Sentinel that gates whether the backend reads `bhph_enabled`.
   *  Flips true on the first save via the Setup UI. Keep false in
   *  fresh drafts so the resolver falls back to defaults. */
  bhph_configured: boolean;
  /** Newline-separated list of lender names. */
  subprime_lenders: string;
  floor_plan_lender: string;
  warranty_offering: string;
  credit_range_served: string;
  /** Newline-separated list of make names. Supersedes `main_brands`
   *  (CSV, legacy franchise-oriented) — backend prefers this field
   *  and falls back to `main_brands` for legacy profiles. */
  makes_carried: string;
  // Server-managed; present on GET, ignored on PUT.
  created_at?: string;
  updated_at?: string;
}

export function fetchOnboardingProfile() {
  return getJSON<OnboardingProfilePayload>(`/onboarding/profile/`);
}

export function saveOnboardingProfile(payload: OnboardingProfilePayload) {
  return authPutJSON<OnboardingProfilePayload>(`/onboarding/profile/`, payload);
}

export function uploadOnboardingLogo(file: File) {
  const body = new FormData();
  body.set("logo", file);
  return authPostForm<OnboardingProfilePayload>(
    `/onboarding/profile/logo/`,
    body,
  );
}

// ---- SESSION_010: stateless manager-chat tester ---------------------------

export interface ManagerChatResponse {
  reply: string;
}

export function sendManagerChat(message: string) {
  return authPostJSON<ManagerChatResponse>(`/manager-chat/`, { message });
}

// ---- Milestone 2 · Increment 7: vehicle investment ledger admin API ------
//
// Types mirror the JSON contract shipped by SESSION_052 (M2.6). Every
// money field is a fixed two-decimal-place string on the wire — do NOT
// parse through JavaScript ``Number``; the backend is the source of
// truth for totals and the frontend never recomputes them.
//
// Canonical enums are duplicated here for form UX (dropdown choices,
// group labels). The backend re-validates every write via
// ``AcquisitionUpsertRequestSerializer`` / ``CostCreateRequestSerializer``
// so any drift between these lists and the backend enum surfaces as
// a 400 with a field-level error — the frontend cannot silently
// accept an invalid value.

export type AcquisitionSource =
  | "auction"
  | "trade"
  | "wholesale"
  | "private"
  | "off_lease"
  | "rental"
  | "repo"
  | "fleet";

export const ACQUISITION_SOURCE_CHOICES: Array<{
  value: AcquisitionSource;
  label: string;
}> = [
  { value: "auction", label: "Auction" },
  { value: "trade", label: "Trade-in" },
  { value: "wholesale", label: "Wholesale (dealer-to-dealer)" },
  { value: "private", label: "Private party" },
  { value: "off_lease", label: "Off-lease" },
  { value: "rental", label: "Rental return" },
  { value: "repo", label: "Repossession" },
  { value: "fleet", label: "Fleet disposal" },
];

export type CostCategoryGroup =
  | "flooring"
  | "recon"
  | "administrative"
  | "photography";

export const COST_CATEGORY_CHOICES: Array<{
  value: string;
  label: string;
  group: CostCategoryGroup;
}> = [
  // Flooring (5)
  { value: "floor_plan_interest", label: "Floor plan interest", group: "flooring" },
  { value: "floor_plan_fees", label: "Floor plan fees", group: "flooring" },
  { value: "curtailment", label: "Curtailment", group: "flooring" },
  { value: "wire_fees", label: "Wire fees", group: "flooring" },
  { value: "banking_fees", label: "Banking fees", group: "flooring" },
  // Recon (13)
  { value: "parts", label: "Parts", group: "recon" },
  { value: "mechanical_labor", label: "Mechanical labor", group: "recon" },
  { value: "tires", label: "Tires", group: "recon" },
  { value: "brakes", label: "Brakes", group: "recon" },
  { value: "battery", label: "Battery", group: "recon" },
  { value: "oil_service", label: "Oil service", group: "recon" },
  { value: "diagnostics", label: "Diagnostics", group: "recon" },
  { value: "glass", label: "Glass", group: "recon" },
  { value: "body_work", label: "Body work", group: "recon" },
  { value: "paint", label: "Paint", group: "recon" },
  { value: "upholstery", label: "Upholstery", group: "recon" },
  { value: "wheel_repair", label: "Wheel repair", group: "recon" },
  { value: "detail", label: "Detail", group: "recon" },
  // Administrative (7)
  { value: "fuel", label: "Fuel", group: "administrative" },
  { value: "listing_fees", label: "Listing fees", group: "administrative" },
  { value: "advertising_allocation", label: "Advertising allocation", group: "administrative" },
  { value: "registration", label: "Registration", group: "administrative" },
  { value: "title_work", label: "Title work", group: "administrative" },
  { value: "shipping", label: "Shipping", group: "administrative" },
  { value: "misc_dealer_expenses", label: "Miscellaneous dealer expenses", group: "administrative" },
  // Photography (1)
  { value: "photography", label: "Photography", group: "photography" },
];

export interface LedgerVehicleHeader {
  stock_number: string;
  vin: string;
  year: number;
  make: string;
  model: string;
  trim: string;
  price: string;
  display_name: string;
}

export interface LedgerAcquisition {
  source: AcquisitionSource;
  source_display: string;
  source_detail: string;
  purchase_price: string;
  purchase_date: string;
  buyer_fees: string;
  arbitration_fees: string;
  transportation_cost: string;
  title_acquisition_cost: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface LedgerCost {
  id: number;
  category: string;
  category_display: string;
  category_group: CostCategoryGroup | null;
  amount: string;
  incurred_at: string;
  vendor: string;
  reference: string;
  notes: string;
  is_estimate: boolean;
  created_by: string | null;
  created_at: string;
}

export interface LedgerTotals {
  acquisition_total: string;
  flooring_total: string;
  recon_total: string;
  administrative_total: string;
  photography_total: string;
  actual_cost_total: string;
  estimated_cost_total: string;
  total_investment: string;
  projected_total_investment: string;
}

export interface VehicleLedgerResponse {
  vehicle: LedgerVehicleHeader;
  acquisition: LedgerAcquisition | null;
  costs: LedgerCost[];
  totals: LedgerTotals;
  days_in_inventory: number | null;
  projected_gross: string;
}

export interface AcquisitionUpsertPayload {
  source: AcquisitionSource;
  source_detail?: string;
  purchase_price: string;
  purchase_date: string;
  buyer_fees?: string;
  arbitration_fees?: string;
  transportation_cost?: string;
  title_acquisition_cost?: string;
  notes?: string;
}

export interface AcquisitionUpsertResponse {
  acquisition: LedgerAcquisition;
  created: boolean;
}

export interface CostCreatePayload {
  category: string;
  amount: string;
  incurred_at: string;
  vendor?: string;
  reference?: string;
  notes?: string;
  is_estimate?: boolean;
}

export interface CostCreateResponse {
  cost: LedgerCost;
}

function _ledgerBasePath(stock: string): string {
  // URL-encode the stock number — dealers may use slashes / special
  // characters in their stock conventions and an unencoded segment
  // would break the URL structure.
  return `/admin/vehicles/${encodeURIComponent(stock)}`;
}

export function fetchVehicleLedger(stock: string) {
  return authGetJSON<VehicleLedgerResponse>(`${_ledgerBasePath(stock)}/ledger/`);
}

export function upsertVehicleAcquisition(
  stock: string,
  body: AcquisitionUpsertPayload,
) {
  return authPostJSON<AcquisitionUpsertResponse>(
    `${_ledgerBasePath(stock)}/acquisition/`,
    body,
  );
}

export function createVehicleCost(
  stock: string,
  body: CostCreatePayload,
) {
  return authPostJSON<CostCreateResponse>(
    `${_ledgerBasePath(stock)}/costs/`,
    body,
  );
}

// ---- Milestone 3 · Increment 7 — condition-report admin API ------------
//
// Consumes the M3.6A + M3.6B endpoint contracts. Every helper wraps
// authFetch (session cookies + CSRF handled uniformly) and returns a
// typed interface mirroring the backend projections.
//
// The three-step photo-upload workflow (request-upload → upload bytes
// → attach) is DELIBERATELY kept as three separate function calls so
// callers see the backend contract literally. Do not create a
// one-shot ``uploadAndAttachPhoto`` helper — the M3.5 planning
// contract's "photo rows represent attached objects, never upload
// intentions" invariant is easier to reason about when the workflow
// is visible in the call site.

// Marker prefix emitted by the local storage adapter (M3.4). If the
// upload target's ``upload_url`` starts with this prefix, the caller
// MUST route to the local multipart receiver instead of doing a
// direct PUT — see uploadPhotoBytes.
export const LOCAL_UPLOAD_URL_MARKER = "local-dev-no-signature-upload";

export const CONDITION_CATEGORY_CHOICES: {
  value: string;
  label: string;
}[] = [
  { value: "mechanical", label: "Mechanical" },
  { value: "cosmetic", label: "Cosmetic / paint" },
  { value: "body", label: "Body / structural" },
  { value: "glass", label: "Glass" },
  { value: "tires", label: "Tires" },
  { value: "interior", label: "Interior" },
  { value: "fluids", label: "Fluids" },
  { value: "electrical", label: "Electrical" },
  { value: "safety", label: "Safety" },
  { value: "accessories", label: "Accessories / features present" },
  { value: "missing", label: "Missing items" },
  { value: "other", label: "Other" },
];

export const CONDITION_SEVERITY_CHOICES: {
  value: string;
  label: string;
}[] = [
  { value: "advisory", label: "Advisory" },
  { value: "recommended", label: "Recommended" },
  { value: "required", label: "Required" },
  { value: "safety", label: "Safety" },
];

export const CONDITION_PHOTO_CONTENT_TYPES: string[] = [
  "image/jpeg",
  "image/png",
  "image/heic",
  "image/webp",
];

export type ConditionReportStatus = "draft" | "complete";

export interface ConditionPhoto {
  public_id: string;
  content_type: string;
  size_bytes: number;
  caption: string;
  uploaded_by: string | null;
  created_at: string;
  signed_read_url: string;
  read_url_expires_at: string;
}

export interface ConditionFinding {
  id: number;
  category: string;
  category_display: string;
  severity: string;
  severity_display: string;
  description: string;
  estimated_cost: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
  photos: ConditionPhoto[];
}

export interface ConditionReport {
  id: number;
  status: ConditionReportStatus;
  status_display: string;
  inspector_name: string;
  inspected_at: string;
  mileage_at_inspection: number;
  completed_at: string | null;
  notes: string;
  authored_by: string | null;
  created_at: string;
  updated_at: string;
  findings: ConditionFinding[];
}

export interface ConditionReportLatestResponse {
  vehicle: LedgerVehicleHeader;
  report: ConditionReport | null;
}

export interface ConditionReportCreatePayload {
  inspector_name: string;
  inspected_at: string; // ISO datetime
  mileage_at_inspection: number;
  notes?: string;
}

export interface ConditionFindingCreatePayload {
  category: string;
  severity: string;
  description: string;
  estimated_cost?: string | null;
  notes?: string;
}

export interface ConditionFindingUpdatePayload {
  category?: string;
  severity?: string;
  description?: string;
  estimated_cost?: string | null;
  notes?: string;
}

export interface PhotoUploadTarget {
  method: string;
  upload_url: string;
  storage_key: string;
  required_headers: Record<string, string>;
  expires_at: string;
}

export interface PhotoRequestUploadResponse {
  upload_target: PhotoUploadTarget;
}

export interface PhotoAttachPayload {
  storage_key: string;
  content_type: string;
  size_bytes: number;
  caption?: string;
}

export interface PhotoAttachResponse {
  photo: ConditionPhoto;
}

function _conditionReportBasePath(stock: string): string {
  return `/admin/vehicles/${encodeURIComponent(stock)}`;
}

// ---- Report + finding endpoints ----

export function fetchLatestConditionReport(stock: string) {
  return authGetJSON<ConditionReportLatestResponse>(
    `${_conditionReportBasePath(stock)}/condition-report/latest/`,
  );
}

export function createConditionReport(
  stock: string,
  body: ConditionReportCreatePayload,
) {
  return authPostJSON<{ report: ConditionReport }>(
    `${_conditionReportBasePath(stock)}/condition-reports/`,
    body,
  );
}

export function completeConditionReport(
  stock: string,
  reportId: number,
) {
  return authPostJSON<{ report: ConditionReport }>(
    `${_conditionReportBasePath(stock)}/condition-reports/${reportId}/complete/`,
    {},
  );
}

export function createConditionFinding(
  stock: string,
  reportId: number,
  body: ConditionFindingCreatePayload,
) {
  return authPostJSON<{ finding: ConditionFinding }>(
    `${_conditionReportBasePath(stock)}/condition-reports/${reportId}/findings/`,
    body,
  );
}

export function updateConditionFinding(
  stock: string,
  findingId: number,
  body: ConditionFindingUpdatePayload,
) {
  return authPatchJSON<{ finding: ConditionFinding }>(
    `${_conditionReportBasePath(stock)}/findings/${findingId}/`,
    body,
  );
}

export function deleteConditionFinding(
  stock: string,
  findingId: number,
) {
  return authDelete(
    `${_conditionReportBasePath(stock)}/findings/${findingId}/`,
  );
}

// ---- Photo endpoints — three-step upload workflow kept literal ----

export function requestPhotoUpload(
  stock: string,
  findingId: number,
  contentType: string,
) {
  return authPostJSON<PhotoRequestUploadResponse>(
    `${_conditionReportBasePath(stock)}/findings/${findingId}/photos/request-upload/`,
    { content_type: contentType },
  );
}

/**
 * Step 2 of the three-step photo-upload workflow. Delivers the raw
 * bytes to whichever endpoint the presigned upload target names.
 *
 * The upload target may be one of two shapes:
 *
 * - **Production (S3-compatible presigned PUT):** ``upload_url``
 *   is a real HTTPS URL. Uploads bytes via a direct PUT with the
 *   ``required_headers`` (typically ``Content-Type``). This request
 *   goes to the storage provider, NOT to the Django backend, so it
 *   uses plain ``fetch`` (no session cookie, no CSRF).
 *
 * - **Local dev (``LOCAL_UPLOAD_URL_MARKER`` prefix):** the target
 *   URL is a marker string, not a real URL. Route to the M3.6B
 *   local-upload receiver via ``authPostForm`` — this DOES require
 *   session cookies + CSRF because it hits the Django app server.
 *
 * Returns the observed HTTP status so callers can distinguish
 * network / provider failures cleanly.
 */
export async function uploadPhotoBytes(args: {
  stock: string;
  findingId: number;
  uploadTarget: PhotoUploadTarget;
  contentType: string;
  file: Blob;
}): Promise<{ status: number }> {
  const { stock, findingId, uploadTarget, contentType, file } = args;

  if (uploadTarget.upload_url.startsWith(LOCAL_UPLOAD_URL_MARKER)) {
    // Local path: hand off to Django multipart receiver. authPostForm
    // sends the CSRF token + session cookie for us.
    const form = new FormData();
    form.append("file", file);
    form.append("storage_key", uploadTarget.storage_key);
    form.append("content_type", contentType);
    await authPostForm(
      `${_conditionReportBasePath(stock)}/findings/${findingId}/photos/local-upload/`,
      form,
    );
    return { status: 201 };
  }

  // Production path: direct browser-to-S3 PUT. Bypasses the Django
  // backend entirely — no cookies, no CSRF.
  const res = await fetch(uploadTarget.upload_url, {
    method: uploadTarget.method,
    headers: uploadTarget.required_headers,
    body: file,
  });
  return { status: res.status };
}

export function attachPhoto(
  stock: string,
  findingId: number,
  body: PhotoAttachPayload,
) {
  return authPostJSON<PhotoAttachResponse>(
    `${_conditionReportBasePath(stock)}/findings/${findingId}/photos/`,
    body,
  );
}

export function deletePhoto(stock: string, publicId: string) {
  return authDelete(
    `${_conditionReportBasePath(stock)}/photos/${publicId}/`,
  );
}

// ----------------------------------------------------------------------------
// Milestone 4 · Increment 6 — recon admin API contract.
// ----------------------------------------------------------------------------
//
// Types + helpers for the 18 endpoints under /admin/vendors/,
// /admin/vehicles/<stock>/recon/, /admin/vehicles/<stock>/work-orders/,
// /admin/work-orders/<id>/*, /admin/parts/<id>/, and /admin/comms/*.
// Every helper uses authFetch — session cookies + CSRF are handled
// uniformly. Domain-error → HTTP status mapping (locked at the
// backend's _map_service_error):
//
// - 404 → cross-tenant or missing (never leaks cross-tenant existence)
// - 409 → immutable state (ReconImmutableError / VendorCommImmutableError
//   / InvalidReconTransitionError / IncompleteConditionReportError)
// - 422 → LLM output rejected by safety scrub (ReconFactScrubDroppedError)
// - 502 → LLM upstream returned empty (EmptyDraftError)
// - 400 → validation / invalid vocabulary
//
// Callers should surface these distinctly (see VehicleReconPage
// error-humanizer helpers).

// ---- Enum vocabularies (mirrored from backend) ----

export const RECON_DECISION_TIER_CHOICES: Array<{
  value: string;
  label: string;
}> = [
  { value: "must_do", label: "Must do" },
  { value: "should_do", label: "Should do" },
  { value: "wont_do", label: "Won't do" },
];

export const WORK_ORDER_STATUS_CHOICES: Array<{
  value: string;
  label: string;
}> = [
  { value: "draft", label: "Draft" },
  { value: "approved", label: "Approved" },
  { value: "in_progress", label: "In progress" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

export const WORK_ORDER_VENUE_CHOICES: Array<{
  value: string;
  label: string;
}> = [
  { value: "in_house", label: "In-house" },
  { value: "outsourced", label: "Outsourced" },
];

export const WORK_ORDER_PART_STATUS_CHOICES: Array<{
  value: string;
  label: string;
}> = [
  { value: "needed", label: "Needed" },
  { value: "ordered", label: "Ordered" },
  { value: "backordered", label: "Backordered" },
  { value: "received", label: "Received" },
  { value: "installed", label: "Installed" },
  { value: "returned", label: "Returned" },
];

export const WORK_ORDER_PART_SOURCE_TYPE_CHOICES: Array<{
  value: string;
  label: string;
}> = [
  { value: "oem_dealer", label: "OEM dealer counter" },
  { value: "local_parts", label: "Local parts store" },
  { value: "online", label: "Online" },
  { value: "salvage", label: "Salvage / recycled" },
  { value: "in_stock", label: "In-house stock" },
  { value: "customer_supplied", label: "Customer supplied" },
  { value: "other", label: "Other" },
];

export const VENDOR_COMMUNICATION_KIND_CHOICES: Array<{
  value: string;
  label: string;
}> = [
  { value: "vendor_comm", label: "Vendor communication" },
  { value: "parts_order", label: "Parts order" },
  { value: "narrative", label: "Narrative note" },
];

export const VENDOR_COMMUNICATION_CHANNEL_CHOICES: Array<{
  value: string;
  label: string;
}> = [
  { value: "email", label: "Email" },
  { value: "sms", label: "SMS" },
  { value: "phone", label: "Phone" },
  { value: "in_person", label: "In person" },
  { value: "internal_note", label: "Internal note" },
];

export const VENDOR_COMMUNICATION_DIRECTION_CHOICES: Array<{
  value: string;
  label: string;
}> = [
  { value: "outbound", label: "Outbound" },
  { value: "inbound", label: "Inbound" },
];

export const VENDOR_COMMUNICATION_STATUS_CHOICES: Array<{
  value: string;
  label: string;
}> = [
  { value: "draft", label: "Draft" },
  { value: "approved", label: "Approved" },
  { value: "sent", label: "Sent" },
  { value: "logged", label: "Logged" },
];

// ---- Response types ----

export interface Vendor {
  id: number;
  slug: string;
  name: string;
  categories: string[];
  phone: string;
  email: string;
  notes: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkOrderFindingLink {
  finding_id: number;
  category: string;
  severity: string;
  description: string;
}

export interface WorkOrderPart {
  id: number;
  work_order_id: number;
  name: string;
  description: string;
  part_number: string;
  quantity: number;
  unit_cost: string | null;
  status: string;
  source_type: string;
  source_name: string;
  ordered_at: string | null;
  received_at: string | null;
  installed_at: string | null;
  returned_at: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface WorkOrder {
  id: number;
  vehicle_stock_number: string;
  category: string;
  venue: string;
  vendor: { id: number; slug: string; name: string } | null;
  assignee_username: string | null;
  status: string;
  estimated_cost: string | null;
  authorized_cost: string | null;
  actual_cost: string | null;
  estimated_completion_date: string | null;
  actual_completion_date: string | null;
  notes: string;
  approved_by: string | null;
  approved_at: string | null;
  started_by: string | null;
  started_at: string | null;
  completed_by: string | null;
  completed_at: string | null;
  cancelled_by: string | null;
  cancelled_at: string | null;
  cancellation_reason: string;
  created_at: string;
  updated_at: string;
  findings: WorkOrderFindingLink[];
  parts: WorkOrderPart[];
}

export interface ReconDecision {
  id: number;
  finding_id: number;
  tier: string;
  notes: string;
  decided_by: string | null;
  decided_at: string;
  created_at: string;
  updated_at: string;
}

export interface VendorCommunicationSourceBundle {
  vehicle?: Record<string, unknown>;
  vendor?: Record<string, unknown>;
  findings?: Array<Record<string, unknown>>;
  parts_needed?: Array<Record<string, unknown>>;
  authorized_cost?: string | null;
  estimated_completion_date?: string | null;
  operator_notes?: string;
  [k: string]: unknown;
}

export interface VendorCommunicationProvenance {
  source_bundle?: VendorCommunicationSourceBundle;
  scrubs_fired?: string[];
  llm_provider?: string;
  logged_off_system?: boolean;
  note?: string;
  [k: string]: unknown;
}

export interface VendorCommunication {
  id: number;
  kind: string;
  channel: string;
  direction: string;
  status: string;
  vendor: { id: number; slug: string; name: string } | null;
  work_order_id: number | null;
  draft_content: string;
  sent_content: string;
  source_provenance: VendorCommunicationProvenance;
  notes: string;
  drafted_by: string | null;
  drafted_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
  sent_by: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReconDashboardFinding {
  id: number;
  category: string;
  severity: string;
  description: string;
  estimated_cost: string | null;
  decision: ReconDecision | null;
}

export interface ReconDashboardReport {
  id: number;
  inspected_at: string;
  inspector_name: string;
  mileage_at_inspection: number;
  completed_at: string;
  findings: ReconDashboardFinding[];
}

export interface ReconDashboardResponse {
  vehicle: {
    stock_number: string;
    year: number;
    model: string;
  };
  latest_condition_report: ReconDashboardReport | null;
  work_orders: WorkOrder[];
  communications: VendorCommunication[];
}

// ---- Request payload types ----

export interface VendorCreatePayload {
  name: string;
  slug: string;
  categories?: string[];
  phone?: string;
  email?: string;
  notes?: string;
  is_active?: boolean;
}

export interface VendorUpdatePayload {
  name?: string;
  categories?: string[];
  phone?: string;
  email?: string;
  notes?: string;
  is_active?: boolean;
}

export interface WorkOrderCreatePayload {
  category: string;
  venue: string;
  vendor_slug?: string | null;
  assignee_id?: number | null;
  estimated_cost?: string | null;
  estimated_completion_date?: string | null;
  notes?: string;
}

export interface WorkOrderApprovePayload {
  authorized_cost?: string | null;
}

export interface WorkOrderCompletePayload {
  actual_cost: string;
  actual_completion_date?: string | null;
}

export interface WorkOrderCancelPayload {
  cancellation_reason?: string;
}

export interface WorkOrderPatchPayload {
  new_estimated_cost?: string | null;
}

export interface WorkOrderPartCreatePayload {
  name: string;
  description?: string;
  part_number?: string;
  quantity?: number;
  unit_cost?: string | null;
  source_type?: string;
  source_name?: string;
  notes?: string;
}

export interface WorkOrderPartPatchPayload {
  name?: string;
  description?: string;
  part_number?: string;
  quantity?: number;
  unit_cost?: string | null;
  source_type?: string;
  source_name?: string;
  notes?: string;
  new_status?: string;
}

export interface ReconDecisionPayload {
  tier: string;
  notes?: string;
}

export interface VendorCommDraftPayload {
  kind: string;
  channel: string;
  direction?: string;
  extra_notes?: string;
}

export interface VendorCommMarkSentPayload {
  sent_content?: string | null;
}

export interface VendorCommLogPayload {
  work_order_id?: number | null;
  kind: string;
  channel: string;
  direction: string;
  body: string;
}

// ---- Helpers ----

function _adminBase(): string {
  return `/admin`;
}

// Vendor CRUD.
export function fetchVendors() {
  return authGetJSON<{ vendors: Vendor[] }>(`${_adminBase()}/vendors/`);
}

export function createVendor(body: VendorCreatePayload) {
  return authPostJSON<{ vendor: Vendor }>(`${_adminBase()}/vendors/`, body);
}

export function fetchVendor(slug: string) {
  return authGetJSON<{ vendor: Vendor }>(
    `${_adminBase()}/vendors/${encodeURIComponent(slug)}/`,
  );
}

export function updateVendor(slug: string, body: VendorUpdatePayload) {
  return authPatchJSON<{ vendor: Vendor }>(
    `${_adminBase()}/vendors/${encodeURIComponent(slug)}/`,
    body,
  );
}

// Recon dashboard.
export function fetchReconDashboard(stock: string) {
  return authGetJSON<ReconDashboardResponse>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/recon/`,
  );
}

// Recon decision.
export function recordReconDecision(
  stock: string,
  findingId: number,
  body: ReconDecisionPayload,
) {
  return authPostJSON<{ decision: ReconDecision }>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/findings/${findingId}/recon-decision/`,
    body,
  );
}

// WorkOrder.
export function createWorkOrder(stock: string, body: WorkOrderCreatePayload) {
  return authPostJSON<{ work_order: WorkOrder }>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/work-orders/`,
    body,
  );
}

export function approveWorkOrder(
  woId: number,
  body: WorkOrderApprovePayload = {},
) {
  return authPostJSON<{ work_order: WorkOrder }>(
    `${_adminBase()}/work-orders/${woId}/approve/`,
    body,
  );
}

export function startWorkOrder(woId: number) {
  return authPostJSON<{ work_order: WorkOrder }>(
    `${_adminBase()}/work-orders/${woId}/start/`,
    {},
  );
}

export function completeWorkOrder(
  woId: number,
  body: WorkOrderCompletePayload,
) {
  return authPostJSON<{ work_order: WorkOrder }>(
    `${_adminBase()}/work-orders/${woId}/complete/`,
    body,
  );
}

export function cancelWorkOrder(
  woId: number,
  body: WorkOrderCancelPayload = {},
) {
  return authPostJSON<{ work_order: WorkOrder }>(
    `${_adminBase()}/work-orders/${woId}/cancel/`,
    body,
  );
}

export function reviseEstimate(woId: number, body: WorkOrderPatchPayload) {
  return authPatchJSON<{ work_order: WorkOrder }>(
    `${_adminBase()}/work-orders/${woId}/`,
    body,
  );
}

export function attachFindings(woId: number, findingIds: number[]) {
  return authPostJSON<{ work_order: WorkOrder }>(
    `${_adminBase()}/work-orders/${woId}/findings/`,
    { finding_ids: findingIds },
  );
}

export function detachFinding(woId: number, findingId: number) {
  return authDelete(
    `${_adminBase()}/work-orders/${woId}/findings/${findingId}/`,
  );
}

// Parts.
export function addWorkOrderPart(
  woId: number,
  body: WorkOrderPartCreatePayload,
) {
  return authPostJSON<{ part: WorkOrderPart }>(
    `${_adminBase()}/work-orders/${woId}/parts/`,
    body,
  );
}

export function updateWorkOrderPart(
  partId: number,
  body: WorkOrderPartPatchPayload,
) {
  return authPatchJSON<{ part: WorkOrderPart }>(
    `${_adminBase()}/parts/${partId}/`,
    body,
  );
}

export function deleteWorkOrderPart(partId: number) {
  return authDelete(`${_adminBase()}/parts/${partId}/`);
}

// Vendor communications.
export function draftVendorComm(woId: number, body: VendorCommDraftPayload) {
  return authPostJSON<{ communication: VendorCommunication }>(
    `${_adminBase()}/work-orders/${woId}/comms/draft/`,
    body,
  );
}

export function approveVendorComm(commId: number) {
  return authPostJSON<{ communication: VendorCommunication }>(
    `${_adminBase()}/comms/${commId}/approve/`,
    {},
  );
}

export function markVendorCommSent(
  commId: number,
  body: VendorCommMarkSentPayload = {},
) {
  return authPostJSON<{ communication: VendorCommunication }>(
    `${_adminBase()}/comms/${commId}/mark-sent/`,
    body,
  );
}

export function logVendorComm(body: VendorCommLogPayload) {
  return authPostJSON<{ communication: VendorCommunication }>(
    `${_adminBase()}/comms/log/`,
    body,
  );
}

// ----------------------------------------------------------------------------
// Milestone 5 · Increment 4 — vehicle lifecycle admin API contract.
// ----------------------------------------------------------------------------
//
// Types + helpers for the 3 endpoints under
// /admin/vehicles/<stock>/lifecycle/*. Every helper uses authFetch.
// Domain-error → HTTP status mapping (SESSION_075 §0.a item 5 —
// distinct classes, distinct status codes; do not overload):
//
// - 404 → cross-tenant or missing vehicle (fail-closed;
//   CrossTenantLifecycleError)
// - 403 → role refusal (UnauthorizedStageTransitionError — e.g.
//   recon_manager attempting a commercial/disposition target)
// - 409 → structurally illegal from/to
//   (InvalidStageTransitionError) OR no-op refused
//   (StageAlreadyCurrentError) OR rule no longer fires at apply time
// - 400 → validation / invalid vocabulary
//
// Callers surface these distinctly — VehicleLifecyclePage's
// error-humanizer helpers.

export type VehicleStageKey =
  | "incoming"
  | "inspection"
  | "recon"
  | "qc"
  | "detail"
  | "photography"
  | "listing"
  | "frontline"
  | "wholesale_out"
  | "hold_reserved"
  | "company_use"
  | "off_market";

export type VehicleStageTriggerKey =
  | "manual"
  | "rule"
  | "import"
  | "bootstrap";

export const VEHICLE_STAGE_CHOICES: Array<{
  value: VehicleStageKey;
  label: string;
}> = [
  { value: "incoming", label: "Incoming" },
  { value: "inspection", label: "Inspection" },
  { value: "recon", label: "Recon" },
  { value: "qc", label: "QC" },
  { value: "detail", label: "Detail" },
  { value: "photography", label: "Photography" },
  { value: "listing", label: "Listing" },
  { value: "frontline", label: "Frontline" },
  { value: "wholesale_out", label: "Wholesale out" },
  { value: "hold_reserved", label: "Hold / reserved" },
  { value: "company_use", label: "Company use" },
  { value: "off_market", label: "Off market" },
];

export interface LifecycleActor {
  id: number;
  username: string;
}

export interface LifecycleStage {
  value: VehicleStageKey;
  label: string;
  entered_at: string;
  entered_by: LifecycleActor | null;
  trigger: VehicleStageTriggerKey;
  last_transition_note: string;
}

export interface LifecycleEvent {
  id: number;
  from_stage: VehicleStageKey | null;
  to_stage: VehicleStageKey;
  entered_at: string;
  by: LifecycleActor | null;
  trigger: VehicleStageTriggerKey;
  rule_name: string;
  notes: string;
  created_at: string;
}

export interface LifecycleSuggestedTransition {
  to_stage: VehicleStageKey;
  rule_name: string;
  evidence: string;
  unmet_prerequisites: string[];
}

export interface LifecycleDashboardResponse {
  stock_number: string;
  has_stage: boolean;
  current_stage: LifecycleStage | null;
  recent_events: LifecycleEvent[];
  suggested_transitions: LifecycleSuggestedTransition[];
  hold_reserved_return_target: VehicleStageKey | null;
}

export interface LifecycleTransitionResponse {
  current_stage: LifecycleStage;
}

export interface LifecycleManualTransitionPayload {
  to_stage: VehicleStageKey;
  notes?: string;
}

export interface LifecycleRuleTransitionPayload {
  rule_name: string;
}

export function fetchLifecycleDashboard(stock: string) {
  return authGetJSON<LifecycleDashboardResponse>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/lifecycle/`,
  );
}

export function postLifecycleManualTransition(
  stock: string,
  body: LifecycleManualTransitionPayload,
) {
  return authPostJSON<LifecycleTransitionResponse>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/lifecycle/transition/`,
    body,
  );
}

export function postLifecycleRuleTransition(
  stock: string,
  body: LifecycleRuleTransitionPayload,
) {
  return authPostJSON<LifecycleTransitionResponse>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/lifecycle/transition/rule/`,
    body,
  );
}

// ----------------------------------------------------------------------------
// Milestone 6 · Increment 5 (SESSION_086) — photo gallery + listing admin API.
//
// URL shape per SESSION_086 §1 Option A user-confirmed:
//   - Vehicle-scoped operations nested under
//     /admin/vehicles/<stock>/photos/ + /listing/.
//   - Photo mutations by public_id under
//     /admin/vehicle-photos/<public_id>/.
//
// Domain-error → HTTP mapping surfaces distinctly to the M6.5 UI:
// 400 (validation) / 404 (not found or cross-tenant) / 409 (state
// conflict — already-deleted, invalid transition, etc.) / 415
// (unsupported content type) / 422 (AI safety refused) / 502
// (storage backend fault).
// ----------------------------------------------------------------------------

export type VehiclePhotoContentType =
  | "image/jpeg"
  | "image/png"
  | "image/webp";

export interface VehiclePhotoActor {
  id: number;
  username: string;
}

export interface VehiclePhotoDTO {
  public_id: string;
  vehicle_id: number;
  storage_key: string;
  content_type: VehiclePhotoContentType;
  width_px: number;
  height_px: number;
  sort_order: number;
  is_primary: boolean;
  caption: string;
  read_url: string;
  uploaded_by: VehiclePhotoActor | null;
  uploaded_at: string;
  marked_deleted_at: string | null;
  deleted_by: VehiclePhotoActor | null;
  updated_at: string;
}

export interface VehiclePhotoListResponse {
  stock_number: string;
  photos: VehiclePhotoDTO[];
}

export interface VehiclePhotoUploadFields {
  file: File;
  width_px: number;
  height_px: number;
  caption?: string;
  sort_order?: number;
}

export function fetchVehiclePhotos(stock: string) {
  return authGetJSON<VehiclePhotoListResponse>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/photos/`,
  );
}

export function uploadVehiclePhoto(
  stock: string,
  fields: VehiclePhotoUploadFields,
) {
  const form = new FormData();
  form.append("file", fields.file);
  form.append("width_px", String(fields.width_px));
  form.append("height_px", String(fields.height_px));
  if (fields.caption !== undefined) {
    form.append("caption", fields.caption);
  }
  if (fields.sort_order !== undefined) {
    form.append("sort_order", String(fields.sort_order));
  }
  return authPostForm<VehiclePhotoDTO>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/photos/upload/`,
    form,
  );
}

export function reorderVehiclePhotos(
  stock: string,
  orderedPublicIds: string[],
) {
  return authPostJSON<VehiclePhotoListResponse>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/photos/reorder/`,
    { ordered_public_ids: orderedPublicIds },
  );
}

export function setPrimaryVehiclePhoto(publicId: string) {
  return authPostJSON<VehiclePhotoDTO>(
    `${_adminBase()}/vehicle-photos/${encodeURIComponent(publicId)}/set-primary/`,
    {},
  );
}

export function markDeletedVehiclePhoto(publicId: string) {
  // authDelete returns void — the M6.5 UI refetches the list after
  // deletion to observe the marked-deleted state transition.
  return authDelete(
    `${_adminBase()}/vehicle-photos/${encodeURIComponent(publicId)}/`,
  );
}

export function restoreVehiclePhoto(publicId: string) {
  return authPostJSON<VehiclePhotoDTO>(
    `${_adminBase()}/vehicle-photos/${encodeURIComponent(publicId)}/restore/`,
    {},
  );
}

// Listing types + helpers.

export type VehicleListingStatus =
  | "draft"
  | "approved"
  | "published"
  | "unpublished";

export interface VehicleListingDTO {
  id: number;
  vehicle_id: number;
  status: VehicleListingStatus;
  title: string;
  body: string;
  source_provenance: Record<string, unknown>;
  drafted_by: VehiclePhotoActor | null;
  drafted_at: string | null;
  approved_by: VehiclePhotoActor | null;
  approved_at: string | null;
  published_by: VehiclePhotoActor | null;
  published_at: string | null;
  unpublished_by: VehiclePhotoActor | null;
  unpublished_at: string | null;
  unpublished_reason: string;
  created_at: string;
  updated_at: string;
}

export interface VehicleListingReadResponse {
  stock_number: string;
  listing: VehicleListingDTO | null;
}

export function fetchVehicleListing(stock: string) {
  return authGetJSON<VehicleListingReadResponse>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/listing/`,
  );
}

export function draftVehicleListing(stock: string) {
  return authPostJSON<VehicleListingDTO>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/listing/draft/`,
    {},
  );
}

export function regenerateVehicleListing(stock: string) {
  return authPostJSON<VehicleListingDTO>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/listing/regenerate/`,
    {},
  );
}

export function approveVehicleListing(stock: string) {
  return authPostJSON<VehicleListingDTO>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/listing/approve/`,
    {},
  );
}

export function publishVehicleListing(stock: string) {
  return authPostJSON<VehicleListingDTO>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/listing/publish/`,
    {},
  );
}

export function unpublishVehicleListing(stock: string, reason: string) {
  return authPostJSON<VehicleListingDTO>(
    `${_adminBase()}/vehicles/${encodeURIComponent(stock)}/listing/unpublish/`,
    { reason },
  );
}
