// Milestone 12 · Increment 7 (SESSION_127) — BHPH portfolio API client.
//
// Consumes the M12.1–M12.7 admin surfaces:
//
//   GET  /admin/bhph/analytics/summary/                    (M12.7)
//   GET  /admin/bhph-notes/list/                           (M12.7)
//   GET  /admin/bhph-notes/<pk>/                           (M12.1)
//   GET  /admin/bhph-notes/<pk>/payments/list/             (M12.2)
//   GET  /admin/bhph-notes/<pk>/promises/list/             (M12.4)
//   GET  /admin/bhph-notes/<pk>/contacts/list/             (M12.5)
//   GET  /admin/bhph-notes/<pk>/repossessions/list/        (M12.6)
//
// Milestone 21 · Increment 2 (SESSION_168) — BHPH write-side wrappers:
//
//   POST /admin/bhph-notes/<pk>/promises/                  (M12.4)
//   POST /admin/bhph-promises/<pk>/mark-kept/              (M12.4)
//   POST /admin/bhph-promises/<pk>/mark-broken/            (M12.4)
//   POST /admin/bhph-notes/<pk>/contacts/                  (M12.5)
//   POST /admin/bhph-notes/<pk>/repossessions/             (M12.6)
//   POST /admin/bhph-repossessions/<pk>/mark-recovered/    (M12.6)
//   POST /admin/bhph-repossessions/<pk>/mark-re-intaked/   (M12.6)
//
// Every write wrapper attaches to the M12.7 collector dashboard
// surface via a component in DealerAiBhphNoteDetail.tsx.
//
// Milestone 23 · Increment 2 (SESSION_177) — BHPH note-origination
// wrapper:
//
//   POST /admin/bhph-notes/                                (M12.1)
//
// Closes the origination-side gap that M12 backend + M12.7 read UI
// + M20.4 Playwright coverage + M21.2 write-side UI for collections
// established. Attaches to DealerAiBhphPortfolio.tsx Notes card as
// a persistent "Add note" CTA + modal per M23 §5.b Option A.
//
// Milestone 23 · Increment 3 (SESSION_178) — BHPH payment-intake
// wrapper:
//
//   POST /admin/bhph-notes/<pk>/payments/                  (M12.2)
//
// Closes the payment-intake gap so a collector can record cash
// payments against an existing note through the product rather
// than via curl / Django shell. Attaches inline to the existing
// Payments card on DealerAiBhphNoteDetail.tsx, matching the
// M21.2 sibling pattern (RecordPromiseToPayForm inline in
// Promises card).
//
// Money on the wire is Decimal-as-string per the M9.5 + M10.1
// convention.

import { authGetJSON, authPostJSON } from "@/lib/authFetch";

// ---------------------------------------------------------------------------
// Analytics summary
// ---------------------------------------------------------------------------

export type BhphAgingBucket =
  | "current"
  | "1_15"
  | "16_30"
  | "31_60"
  | "61_90"
  | "over_90"
  | "charge_off_candidate";

export interface BucketHistogramRow {
  bucket: BhphAgingBucket;
  note_count: number;
  principal_total: string;
}

export interface BhphAnalyticsSummary {
  bucket_histogram: BucketHistogramRow[];
  total_note_count: number;
  total_principal_financed: string;
  cure_rate: string | null;
  weighted_average_apr: string | null;
  weighted_average_days_past_due: string | null;
  ptp_kept_ratio: string | null;
}

export function fetchBhphAnalyticsSummary(): Promise<BhphAnalyticsSummary> {
  return authGetJSON<BhphAnalyticsSummary>(
    "/admin/bhph/analytics/summary/",
  );
}

// ---------------------------------------------------------------------------
// BhphNote list + detail
// ---------------------------------------------------------------------------

export type BhphPaymentFrequency = "weekly" | "biweekly" | "semi_monthly";

export interface BhphNoteProjection {
  id: number;
  sale_id: number;
  dealership_id: number;
  principal_financed: string;
  apr: string;
  term_weeks: number;
  payment_frequency: BhphPaymentFrequency;
  payment_amount: string;
  first_payment_due: string;
  default_grace_days: number;
  current_bucket: BhphAgingBucket;
  days_past_due: number;
  created_at: string;
  updated_at: string;
}

export interface BhphNoteListResponse {
  count: number;
  results: BhphNoteProjection[];
}

export function listBhphNotes(): Promise<BhphNoteListResponse> {
  return authGetJSON<BhphNoteListResponse>("/admin/bhph-notes/list/");
}

export interface BhphPaymentScheduleRow {
  due_date: string;
  amount: string;
}

export interface BhphNoteDetailResponse {
  bhph_note: BhphNoteProjection;
  payment_schedule: BhphPaymentScheduleRow[];
}

export function getBhphNote(pk: number): Promise<BhphNoteDetailResponse> {
  return authGetJSON<BhphNoteDetailResponse>(`/admin/bhph-notes/${pk}/`);
}

// ---------------------------------------------------------------------------
// M23.2 — BHPH note origination (POST /admin/bhph-notes/)
// ---------------------------------------------------------------------------
//
// Creates a new BhphNote against a BHPH-marked Sale. Payload shape
// matches BhphNoteCreateRequestSerializer in
// backend/dealer_ai/views_bhph_notes.py verbatim. Server enforces:
//   - sale must belong to caller's tenant (M12.1)
//   - sale.finance_type must be BHPH (409 → NonBhphSaleError → 400)
//   - no existing BhphNote for the sale (M12 one-note-per-sale rule → 409 →
//     DuplicateBhphNoteError)
//   - payment_frequency must be a known cadence (400 →
//     UnknownBhphFrequencyError)

export interface CreateBhphNotePayload {
  sale_id: number;
  principal_financed: string; // Decimal-as-string (min 0.01)
  apr: string;                // Decimal-as-string (min 0.00)
  term_weeks: number;         // int (min 1)
  payment_frequency: BhphPaymentFrequency;
  first_payment_due: string;  // ISO 8601 date (YYYY-MM-DD)
  default_grace_days?: number; // optional (default 5, min 0)
}

export interface BhphNoteCreateResponse {
  bhph_note: BhphNoteProjection;
}

export function createBhphNote(
  payload: CreateBhphNotePayload,
): Promise<BhphNoteCreateResponse> {
  return authPostJSON<BhphNoteCreateResponse>(
    "/admin/bhph-notes/",
    payload,
  );
}

// ---------------------------------------------------------------------------
// Per-note sub-lists (payments / promises / contacts / repossessions)
// ---------------------------------------------------------------------------

export interface BhphPaymentProjection {
  id: number;
  note_id: number;
  dealership_id: number;
  paid_at: string;
  amount: string;
  method: "cash" | "check" | "debit" | "ach" | "other";
  applied_to_fees: string;
  applied_to_interest: string;
  applied_to_principal: string;
  created_at: string;
  updated_at: string;
}

export interface BhphPaymentListResponse {
  count: number;
  results: BhphPaymentProjection[];
}

export function listBhphPayments(
  notePk: number,
): Promise<BhphPaymentListResponse> {
  return authGetJSON<BhphPaymentListResponse>(
    `/admin/bhph-notes/${notePk}/payments/list/`,
  );
}

// M23.3 — Payment method vocab (matches BHPH_PAYMENT_METHOD_CHOICES
// in backend/dealer_ai/models.py verbatim).
export type BhphPaymentMethod = "cash" | "check" | "debit" | "ach" | "other";

export interface CreateBhphPaymentPayload {
  paid_at: string;   // ISO 8601 datetime
  amount: string;    // Decimal-as-string (min 0.01)
  method: BhphPaymentMethod;
}

export interface BhphPaymentCreateResponse {
  bhph_payment: BhphPaymentProjection;
}

export function createBhphPayment(
  notePk: number,
  payload: CreateBhphPaymentPayload,
): Promise<BhphPaymentCreateResponse> {
  return authPostJSON<BhphPaymentCreateResponse>(
    `/admin/bhph-notes/${notePk}/payments/`,
    payload,
  );
}

export interface BhphPromiseProjection {
  id: number;
  note_id: number;
  dealership_id: number;
  promised_at: string;
  promised_amount: string;
  promised_reason: "paycheck" | "tax_refund" | "family_help" | "other";
  actual_payment_id: number | null;
  state: "promised" | "kept" | "broken";
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface BhphPromiseListResponse {
  count: number;
  results: BhphPromiseProjection[];
}

export function listBhphPromises(
  notePk: number,
): Promise<BhphPromiseListResponse> {
  return authGetJSON<BhphPromiseListResponse>(
    `/admin/bhph-notes/${notePk}/promises/list/`,
  );
}

export interface CollectionContactProjection {
  id: number;
  note_id: number;
  dealership_id: number;
  contacted_at: string;
  contacted_by_user_id: number | null;
  channel: "phone" | "letter" | "sms" | "email" | "in_person";
  outcome:
    | "contact_made"
    | "left_message"
    | "no_answer"
    | "refused_to_speak";
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface CollectionContactListResponse {
  count: number;
  results: CollectionContactProjection[];
}

export function listCollectionContacts(
  notePk: number,
): Promise<CollectionContactListResponse> {
  return authGetJSON<CollectionContactListResponse>(
    `/admin/bhph-notes/${notePk}/contacts/list/`,
  );
}

export interface RepossessionProjection {
  id: number;
  note_id: number;
  dealership_id: number;
  ordered_at: string;
  ordered_by_user_id: number | null;
  agent_name: string;
  recovered_at: string | null;
  recovery_location: string;
  intake_condition_report_id: number | null;
  state: "ordered" | "recovered" | "re_intaked";
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface RepossessionListResponse {
  count: number;
  results: RepossessionProjection[];
}

export function listRepossessions(
  notePk: number,
): Promise<RepossessionListResponse> {
  return authGetJSON<RepossessionListResponse>(
    `/admin/bhph-notes/${notePk}/repossessions/list/`,
  );
}

// ---------------------------------------------------------------------------
// M21.2 write-side wrappers — BHPH promise / contact / repossession.
// ---------------------------------------------------------------------------

// Promise CREATE — POST /admin/bhph-notes/<pk>/promises/
// Payload matches PromiseCreateRequestSerializer in
// backend/dealer_ai/views_bhph_promises.py.

export type BhphPromiseReason =
  | "paycheck"
  | "tax_refund"
  | "family_help"
  | "other";

export interface RecordPromiseToPayPayload {
  promised_at: string; // ISO 8601 datetime
  promised_amount: string; // Decimal-as-string
  promised_reason: BhphPromiseReason;
  notes?: string;
}

export interface BhphPromiseResponse {
  bhph_promise: BhphPromiseProjection;
}

export function recordPromiseToPay(
  notePk: number,
  payload: RecordPromiseToPayPayload,
): Promise<BhphPromiseResponse> {
  return authPostJSON<BhphPromiseResponse>(
    `/admin/bhph-notes/${notePk}/promises/`,
    payload,
  );
}

// Promise MARK-KEPT — POST /admin/bhph-promises/<pk>/mark-kept/
// Requires a payment reference per M12.4 §5.d Option A operator-
// triggered reconciliation.

export interface MarkPromiseKeptPayload {
  bhph_payment_id: number;
  notes?: string;
}

export function markPromiseKept(
  promisePk: number,
  payload: MarkPromiseKeptPayload,
): Promise<BhphPromiseResponse> {
  return authPostJSON<BhphPromiseResponse>(
    `/admin/bhph-promises/${promisePk}/mark-kept/`,
    payload,
  );
}

// Promise MARK-BROKEN — POST /admin/bhph-promises/<pk>/mark-broken/
// The delinquency detector auto-fires; this endpoint is for manual
// operator override with optional reason notes.

export interface MarkPromiseBrokenPayload {
  notes?: string;
}

export function markPromiseBroken(
  promisePk: number,
  payload: MarkPromiseBrokenPayload = {},
): Promise<BhphPromiseResponse> {
  return authPostJSON<BhphPromiseResponse>(
    `/admin/bhph-promises/${promisePk}/mark-broken/`,
    payload,
  );
}

// Collection contact CREATE — POST /admin/bhph-notes/<pk>/contacts/
// FDCPA-adjacent scrub layer applies at the backend.

export type CollectionContactChannel =
  | "phone"
  | "letter"
  | "sms"
  | "email"
  | "in_person";

export type CollectionContactOutcome =
  | "contact_made"
  | "left_message"
  | "no_answer"
  | "refused_to_speak";

export interface LogCollectionContactPayload {
  contacted_at: string; // ISO 8601 datetime
  channel: CollectionContactChannel;
  outcome: CollectionContactOutcome;
  notes?: string;
}

export interface CollectionContactResponse {
  collection_contact: CollectionContactProjection;
}

export function logCollectionContact(
  notePk: number,
  payload: LogCollectionContactPayload,
): Promise<CollectionContactResponse> {
  return authPostJSON<CollectionContactResponse>(
    `/admin/bhph-notes/${notePk}/contacts/`,
    payload,
  );
}

// Repossession CREATE — POST /admin/bhph-notes/<pk>/repossessions/

export interface InitiateRepossessionPayload {
  ordered_at: string; // ISO 8601 datetime
  agent_name: string;
  notes?: string;
}

export interface RepossessionResponse {
  repossession: RepossessionProjection;
}

export function initiateRepossession(
  notePk: number,
  payload: InitiateRepossessionPayload,
): Promise<RepossessionResponse> {
  return authPostJSON<RepossessionResponse>(
    `/admin/bhph-notes/${notePk}/repossessions/`,
    payload,
  );
}

// Repossession MARK-RECOVERED —
// POST /admin/bhph-repossessions/<pk>/mark-recovered/

export interface MarkRepossessionRecoveredPayload {
  recovered_at?: string | null; // ISO 8601 datetime; defaults to now server-side
  recovery_location?: string;
  notes?: string;
}

export function markRepossessionRecovered(
  repossessionPk: number,
  payload: MarkRepossessionRecoveredPayload = {},
): Promise<RepossessionResponse> {
  return authPostJSON<RepossessionResponse>(
    `/admin/bhph-repossessions/${repossessionPk}/mark-recovered/`,
    payload,
  );
}

// Repossession MARK-RE-INTAKED —
// POST /admin/bhph-repossessions/<pk>/mark-re-intaked/
// Requires a ConditionReport reference scoped to the recovered vehicle.

export interface MarkRepossessionReIntakedPayload {
  condition_report_id: number;
  notes?: string;
}

export function markRepossessionReIntaked(
  repossessionPk: number,
  payload: MarkRepossessionReIntakedPayload,
): Promise<RepossessionResponse> {
  return authPostJSON<RepossessionResponse>(
    `/admin/bhph-repossessions/${repossessionPk}/mark-re-intaked/`,
    payload,
  );
}
