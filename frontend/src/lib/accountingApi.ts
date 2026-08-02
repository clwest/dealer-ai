// Milestone 14 · Increment 2 (SESSION_135) — accounting API client.
//
// Consumes the M13.1 + M13.3 + M14.1 admin surfaces:
//
//   GET  /admin/accounting/trial-balance/[?as_of=<ISO8601>]  (M13.3)
//   GET  /admin/accounting/journal-entries/list/             (M14.1)
//   GET  /admin/accounting/journal-entries/<pk>/             (M13.1)
//   GET  /admin/accounting/cost-posting-failures/            (M14.1)
//   POST /admin/accounting/journal-entries/<pk>/reverse/     (M13.1)
//
// At M14.2 only ``fetchTrialBalance`` ships. Journal-entry list +
// detail land at M14.3; reversal + failure card at M14.4.
//
// Money on the wire is Decimal-as-string per M9.5 / M10.1 / M12 BHPH /
// M13.1 + M13.3 + M14.1 convention (§5.c Option A confirmed at M14.0
// open). Callers format for display via Intl.NumberFormat rather than
// coercing to Number in the API layer — preserves precision boundaries.

import { authGetJSON } from "@/lib/authFetch";

// ---------------------------------------------------------------------------
// Trial balance (M13.3 endpoint)
// ---------------------------------------------------------------------------

export type GLAccountType =
  | "asset"
  | "liability"
  | "equity"
  | "revenue"
  | "expense";

export interface TrialBalanceRow {
  account_code: string;
  account_name: string;
  account_type: GLAccountType;
  debit_total: string;
  credit_total: string;
  natural_balance: string;
}

export interface TrialBalanceSnapshot {
  dealership_id: number;
  dealership_slug: string;
  as_of: string;
  total_debits: string;
  total_credits: string;
  is_balanced: boolean;
  rows: TrialBalanceRow[];
}

interface TrialBalanceResponse {
  trial_balance: TrialBalanceSnapshot;
}

export async function fetchTrialBalance(): Promise<TrialBalanceSnapshot> {
  const body = await authGetJSON<TrialBalanceResponse>(
    "/admin/accounting/trial-balance/",
  );
  return body.trial_balance;
}

// ---------------------------------------------------------------------------
// Journal-entry list (M14.1 endpoint) + detail (M13.1 endpoint)
// ---------------------------------------------------------------------------
//
// The list projection is intentionally compact (no lines, includes
// ``total_debit`` annotation) — the detail projection carries the full
// line breakdown for one entry. Two distinct types on the wire.

/** One row in the paginated journal-entry list (M14.1 projection). */
export interface JournalEntryListEntry {
  id: number;
  description: string;
  posted_at: string;
  posted_by_user_id: number | null;
  posted_by_username: string | null;
  /** Populated when this entry reverses another. Points at the original. */
  reverses_id: number | null;
  /** Reason recorded on reversal entries; blank on originals. */
  reason: string;
  /** Sum of line debits — quantized 2dp per §5.c Option A. */
  total_debit: string;
}

export interface JournalEntryListPage {
  entries: JournalEntryListEntry[];
  total_count: number;
  page: number;
  page_size: number;
}

interface JournalEntryListResponse {
  journal_entries: JournalEntryListPage;
}

export function fetchJournalEntries(
  params: { page?: number; pageSize?: number } = {},
): Promise<JournalEntryListPage> {
  const search = new URLSearchParams();
  if (params.page !== undefined) search.set("page", String(params.page));
  if (params.pageSize !== undefined) {
    search.set("page_size", String(params.pageSize));
  }
  const query = search.toString();
  const path = `/admin/accounting/journal-entries/list/${
    query ? `?${query}` : ""
  }`;
  return authGetJSON<JournalEntryListResponse>(path).then(
    (body) => body.journal_entries,
  );
}

/** One debit/credit row on a JournalEntry (M13.1 projection). */
export interface JournalEntryLine {
  id: number;
  account_id: number;
  account_code: string;
  debit: string;
  credit: string;
  memo: string;
}

/** Detail projection returned by GET /admin/accounting/journal-entries/<pk>/. */
export interface JournalEntry {
  id: number;
  dealership_id: number;
  description: string;
  posted_at: string;
  posted_by_user_id: number | null;
  /** Populated when this entry reverses another. */
  reverses_id: number | null;
  /** Non-blank on reversal entries per M13.1 audit-trail requirement. */
  reason: string;
  created_at: string;
  lines: JournalEntryLine[];
}

interface JournalEntryDetailResponse {
  journal_entry: JournalEntry;
}

export function fetchJournalEntry(pk: number): Promise<JournalEntry> {
  return authGetJSON<JournalEntryDetailResponse>(
    `/admin/accounting/journal-entries/${pk}/`,
  ).then((body) => body.journal_entry);
}
