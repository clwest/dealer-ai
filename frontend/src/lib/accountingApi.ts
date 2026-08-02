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
