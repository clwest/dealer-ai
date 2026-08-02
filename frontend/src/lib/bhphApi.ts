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
// M12.7 §5.f Option C: portfolio dashboard + per-note detail ship;
// collection-contact + repo-order UI defer.
//
// Money on the wire is Decimal-as-string per the M9.5 + M10.1
// convention.

import { authGetJSON } from "@/lib/authFetch";

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
