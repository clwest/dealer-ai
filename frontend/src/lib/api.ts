// API helpers for the Dealer AI backend.
// Vite dev server proxies /api → http://localhost:8000 (see vite.config.ts).

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

async function putJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
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
  return getJSON<ListResponse<AdminLead>>(
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
  return getJSON<AuditEventsResponse>(
    `/admin/audit-events/${qs ? `?${qs}` : ""}`,
  );
}

export function fetchAdminChatSessions(limit = 25) {
  return getJSON<ListResponse<AdminChatSessionRow>>(
    `/admin/chat-sessions/?limit=${limit}`,
  );
}

export function fetchAdminTrends() {
  return getJSON<TrendsResponse>(`/admin/trends/`);
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
  return getJSON<PipelineResponse>(`/admin/pipeline/`);
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
  return postJSON<AdCopyResponse>(`/admin/ad-copy/`, {
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
  return getJSON<{ count: number; results: SalespersonAdmin[] }>(
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
  return postJSON<AdminLead>(`/admin/lead/${leadId}/assign/`, {
    salesperson_id: salespersonId,
  });
}

export function fetchAdvisorWorkspace(slug: string) {
  return getJSON<AdvisorWorkspaceResponse>(`/advisor/${slug}/`);
}

export function generateFollowUpDrafts(
  slug: string,
  leadId: number,
  body: { channel?: "sms" | "email"; tone?: "warm" | "direct" } = {},
) {
  return postJSON<FollowUpResponse>(
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
  return getJSON<LeadDetailResponse>(`/admin/lead/${leadId}/`);
}

export function buildLeadHandoff(
  leadId: number,
  opts: { markHandedOff?: boolean } = {},
) {
  return postJSON<HandoffPacket>(`/admin/lead/${leadId}/handoff/`, {
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
  // Server-managed; present on GET, ignored on PUT.
  created_at?: string;
  updated_at?: string;
}

export function fetchOnboardingProfile() {
  return getJSON<OnboardingProfilePayload>(`/onboarding/profile/`);
}

export function saveOnboardingProfile(payload: OnboardingProfilePayload) {
  return putJSON<OnboardingProfilePayload>(`/onboarding/profile/`, payload);
}

// ---- SESSION_010: stateless manager-chat tester ---------------------------

export interface ManagerChatResponse {
  reply: string;
}

export function sendManagerChat(message: string) {
  return postJSON<ManagerChatResponse>(`/manager-chat/`, { message });
}
