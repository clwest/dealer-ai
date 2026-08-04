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

import { authGetJSON, authPostJSON } from "@/lib/authFetch";

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

export async function fetchTrialBalance(
  asOf?: string,
): Promise<TrialBalanceSnapshot> {
  // Milestone 17 · Increment 2 — optional ``asOf`` param feeds
  // the M13.3 endpoint's existing ``?as_of=`` query parameter.
  // Backward-compatible: callers without the arg get the live
  // "as of now" behavior.
  const path = asOf
    ? `/admin/accounting/trial-balance/?as_of=${encodeURIComponent(asOf)}`
    : "/admin/accounting/trial-balance/";
  const body = await authGetJSON<TrialBalanceResponse>(path);
  return body.trial_balance;
}

// ---------------------------------------------------------------------------
// Trial-balance snapshots — freeze / list / detail (M17.1 endpoints)
// ---------------------------------------------------------------------------
//
// Consumed by AccountingTrialBalancePage at M17.2. Freeze is operator-
// triggered ("Freeze this view" button); list + detail feed the
// "Prior closes" section. Duplicate freeze at the same instant surfaces
// as a 409 per §5.d Option A.

/** Compact projection returned by the snapshot list endpoint. */
export interface TrialBalanceSnapshotSummary {
  id: number;
  as_of: string;
  total_debits: string;
  total_credits: string;
  is_balanced: boolean;
  created_at: string;
  created_by_user_id: number | null;
  created_by_username: string | null;
}

/** One frozen per-account row on a snapshot (M17.1 projection). */
export interface FrozenSnapshotRow {
  account_code: string;
  account_name: string;
  account_type: GLAccountType;
  debit_total: string;
  credit_total: string;
  natural_balance: string;
}

/** Full detail projection (summary fields + frozen rows). */
export interface FrozenTrialBalanceSnapshot
  extends TrialBalanceSnapshotSummary {
  rows: FrozenSnapshotRow[];
}

export interface TrialBalanceSnapshotListPage {
  snapshots: TrialBalanceSnapshotSummary[];
  total_count: number;
  page: number;
  page_size: number;
}

interface TrialBalanceSnapshotDetailResponse {
  trial_balance_snapshot: FrozenTrialBalanceSnapshot;
}

interface TrialBalanceSnapshotListResponse {
  trial_balance_snapshots: TrialBalanceSnapshotListPage;
}

export function freezeTrialBalance(
  asOf: string,
): Promise<FrozenTrialBalanceSnapshot> {
  return authPostJSON<TrialBalanceSnapshotDetailResponse>(
    "/admin/accounting/trial-balance/snapshots/",
    { as_of: asOf },
  ).then((body) => body.trial_balance_snapshot);
}

export function listTrialBalanceSnapshots(
  params: { page?: number; pageSize?: number } = {},
): Promise<TrialBalanceSnapshotListPage> {
  const search = new URLSearchParams();
  if (params.page !== undefined) search.set("page", String(params.page));
  if (params.pageSize !== undefined) {
    search.set("page_size", String(params.pageSize));
  }
  const query = search.toString();
  const path = `/admin/accounting/trial-balance/snapshots/list/${
    query ? `?${query}` : ""
  }`;
  return authGetJSON<TrialBalanceSnapshotListResponse>(path).then(
    (body) => body.trial_balance_snapshots,
  );
}

export function fetchTrialBalanceSnapshot(
  pk: number,
): Promise<FrozenTrialBalanceSnapshot> {
  return authGetJSON<TrialBalanceSnapshotDetailResponse>(
    `/admin/accounting/trial-balance/snapshots/${pk}/`,
  ).then((body) => body.trial_balance_snapshot);
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

// ---------------------------------------------------------------------------
// Reverse a journal entry (M13.1 endpoint)
// ---------------------------------------------------------------------------
//
// Wired at M14.4 into the AccountingJournalEntryDetailPage
// Corrections card. Empty reason is blocked client-side matching
// M13.1's serializer 400 (belt+suspenders per §5.e Option A). The
// endpoint returns the newly-posted reversal JournalEntry.

export interface ReverseJournalEntryPayload {
  reason: string;
  /** Optional ISO8601 timestamp. Omit for now (defaults to server time). */
  posted_at?: string;
}

export function reverseJournalEntry(
  pk: number,
  payload: ReverseJournalEntryPayload,
): Promise<JournalEntry> {
  return authPostJSON<JournalEntryDetailResponse>(
    `/admin/accounting/journal-entries/${pk}/reverse/`,
    payload,
  ).then((body) => body.journal_entry);
}

// ---------------------------------------------------------------------------
// Cost-posting failures (M14.1 endpoint)
// ---------------------------------------------------------------------------
//
// Consumed by the trial-balance page as a failure card. Empty count
// hides the card entirely per §0.a M14.4 decision (zero-noise
// posture — no "0 failures" banner).

export interface CostPostingFailure {
  id: number;
  vehicle_id: number;
  vehicle_stock: string | null;
  category: string;
  category_display: string;
  amount: string;
  reference: string;
  vendor: string;
  incurred_at: string;
  created_at: string;
  age_in_hours: number;
}

export interface CostPostingFailuresResponse {
  failures: CostPostingFailure[];
  count: number;
  threshold_hours: number;
  as_of: string;
}

interface CostPostingFailuresBody {
  cost_posting_failures: CostPostingFailuresResponse;
}

export function fetchCostPostingFailures(
  params: { thresholdHours?: number } = {},
): Promise<CostPostingFailuresResponse> {
  const search = new URLSearchParams();
  if (params.thresholdHours !== undefined) {
    search.set("threshold_hours", String(params.thresholdHours));
  }
  const query = search.toString();
  const path = `/admin/accounting/cost-posting-failures/${
    query ? `?${query}` : ""
  }`;
  return authGetJSON<CostPostingFailuresBody>(path).then(
    (body) => body.cost_posting_failures,
  );
}

// ---------------------------------------------------------------------------
// Chart-of-accounts list (M27.1 endpoint — shared accounting substrate)
// ---------------------------------------------------------------------------
//
// Milestone 27 · Increment 1 (SESSION_192). Consumes GET
// /admin/accounting/gl-accounts/ — returns the tenant's active
// chart of accounts sorted by ``code`` ASC. Immediate consumer is
// the M27.2 JE-create dialog account picker; future consumers
// include recurring journals, adjustments, budget uploads,
// statement reconciliation, F&I chargebacks, and period-open
// workflows.
//
// Reuses the existing ``GLAccountType`` alias exported above from
// the M14 trial-balance types — no duplicate declaration.

/** One row on the M27.1 chart-of-accounts projection. */
export interface GLAccount {
  id: number;
  code: string;
  name: string;
  type: GLAccountType;
}

interface GLAccountListResponse {
  gl_accounts: { accounts: GLAccount[] };
}

export function fetchGLAccounts(): Promise<GLAccount[]> {
  return authGetJSON<GLAccountListResponse>(
    "/admin/accounting/gl-accounts/",
  ).then((body) => body.gl_accounts.accounts);
}

// ---------------------------------------------------------------------------
// Journal-entry creation (M13.1 endpoint, wired at M27.2)
// ---------------------------------------------------------------------------
//
// Milestone 27 · Increment 2 (SESSION_193). Consumes the pre-existing
// POST /admin/accounting/journal-entries/ endpoint (row 140 in the
// M21 audit — endpoint has shipped since M13.1 without a frontend
// consumer). Envelope + Decimal-as-string conventions match the
// existing ``reverseJournalEntry`` wrapper.

export interface CreateJournalEntryLine {
  account_id: number;
  /** Decimal-as-string per §5.c Option A. Zero on the credit side of
   * a debit-line and vice versa. */
  debit: string;
  credit: string;
  memo?: string;
}

export interface CreateJournalEntryPayload {
  description: string;
  /** Optional ISO 8601 timestamp. Server defaults to now when omitted. */
  posted_at?: string;
  lines: CreateJournalEntryLine[];
}

export function createJournalEntry(
  payload: CreateJournalEntryPayload,
): Promise<JournalEntry> {
  return authPostJSON<JournalEntryDetailResponse>(
    "/admin/accounting/journal-entries/",
    payload,
  ).then((body) => body.journal_entry);
}
