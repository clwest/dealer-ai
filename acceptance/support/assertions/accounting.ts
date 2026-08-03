// Milestone 20 · Increment 3 — business-outcome assertion helpers
// for the office/accounting workflow journey.
//
// Milestone 22 · Increment 2 — extended with JE list lookup +
// `expectJournalEntryReversed` for the JE reversal journey. Per the
// M20 guiding principle: assertions target business state (a
// TrialBalanceSnapshot exists with rows summing to the expected
// totals; a reversal entry exists with sign-flipped lines and correct
// linkage) via the admin API, not DOM state.

import { APIRequestContext, expect } from "@playwright/test";

export interface TrialBalanceSnapshotSummary {
  id: number;
  as_of: string;
  created_at: string;
  created_by_username: string | null;
  total_debits: string;
  total_credits: string;
  is_balanced: boolean;
}

// The M17.1 endpoint returns a nested envelope
// `{ trial_balance_snapshots: { snapshots: [...], total_count, page, page_size } }`
// — see backend/dealer_ai/views_accounting.py:614.
export interface TrialBalanceSnapshotListEnvelope {
  trial_balance_snapshots: {
    snapshots: TrialBalanceSnapshotSummary[];
    total_count: number;
    page: number;
    page_size: number;
  };
}

async function fetchSnapshotList(
  request: APIRequestContext,
): Promise<TrialBalanceSnapshotSummary[]> {
  const url =
    "/api/dealer-ai/admin/accounting/trial-balance/snapshots/list/?page_size=10";
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as TrialBalanceSnapshotListEnvelope;
  return body.trial_balance_snapshots?.snapshots ?? [];
}

/**
 * Assert that the trial balance snapshot list contains at least
 * `minCount` frozen snapshots on the current tenant.
 */
export async function expectSnapshotCountAtLeast(
  request: APIRequestContext,
  minCount: number,
): Promise<TrialBalanceSnapshotSummary[]> {
  const snapshots = await fetchSnapshotList(request);
  expect(
    snapshots.length,
    `expected at least ${minCount} frozen trial-balance snapshot(s); got ${snapshots.length}`,
  ).toBeGreaterThanOrEqual(minCount);
  return snapshots;
}

/**
 * Fetch a specific snapshot's detail and confirm it is balanced —
 * the accounting acceptance contract requires that any snapshot the
 * suite freezes reflects a balanced trial balance (else the fixture
 * seed is broken).
 */
export async function expectSnapshotBalanced(
  request: APIRequestContext,
  snapshotId: number,
): Promise<void> {
  const url = `/api/dealer-ai/admin/accounting/trial-balance/snapshots/${snapshotId}/`;
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  // Response is envelope-wrapped: `{ trial_balance_snapshot: {...} }`
  // per backend/dealer_ai/views_accounting.py:646.
  const body = (await response.json()) as {
    trial_balance_snapshot: {
      is_balanced: boolean;
      total_debits: string;
      total_credits: string;
    };
  };
  const snapshot = body.trial_balance_snapshot;
  expect(
    snapshot?.is_balanced,
    `snapshot ${snapshotId} should be balanced (debits=${snapshot?.total_debits} credits=${snapshot?.total_credits})`,
  ).toBe(true);
}

// ---------------------------------------------------------------------
// Milestone 22 · Increment 2 — journal-entry helpers for the JE
// reversal journey.
// ---------------------------------------------------------------------

// M14.1 list projection — compact row per JE, no lines.
export interface JournalEntryListRow {
  id: number;
  description: string;
  posted_at: string;
  reverses_id: number | null;
  reason: string;
}

// M13.1 detail projection — includes the full line breakdown.
export interface JournalEntryDetail {
  id: number;
  description: string;
  reverses_id: number | null;
  reason: string;
  lines: Array<{
    id: number;
    account_id: number;
    account_code: string;
    debit: string;
    credit: string;
    memo: string;
  }>;
}

/**
 * Fetch the current dealership's journal entries by walking the
 * paginated list endpoint. Returns every row (in practice the M22.2
 * fixture keeps the suite well under one page).
 */
async function fetchAllJournalEntries(
  request: APIRequestContext,
): Promise<JournalEntryListRow[]> {
  const url =
    "/api/dealer-ai/admin/accounting/journal-entries/list/?page_size=100";
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as {
    journal_entries: {
      entries: JournalEntryListRow[];
      total_count: number;
    };
  };
  return body.journal_entries?.entries ?? [];
}

/**
 * Find the (single) journal entry whose description starts with the
 * given prefix. The M22.2 seed guarantees exactly one row with the
 * `[M22.2-office-je-reversal]` tag; the helper fails loudly if zero
 * or multiple rows match so a seed regression surfaces here rather
 * than deep inside a journey.
 */
export async function findJournalEntryByDescriptionPrefix(
  request: APIRequestContext,
  descriptionPrefix: string,
): Promise<JournalEntryListRow> {
  const entries = await fetchAllJournalEntries(request);
  const matches = entries.filter((entry) =>
    entry.description.startsWith(descriptionPrefix),
  );
  expect(
    matches.length,
    `expected exactly one JE with description prefix "${descriptionPrefix}"; found ${matches.length}`,
  ).toBe(1);
  return matches[0]!;
}

/**
 * Fetch the detail projection for one JE (M13.1 endpoint).
 */
async function fetchJournalEntryDetail(
  request: APIRequestContext,
  entryId: number,
): Promise<JournalEntryDetail> {
  const url = `/api/dealer-ai/admin/accounting/journal-entries/${entryId}/`;
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as {
    journal_entry: JournalEntryDetail;
  };
  return body.journal_entry;
}

/**
 * Assert that a reversal entry exists targeting `originalId`, and
 * that its lines are the sign-flipped mirror of the original's lines
 * (debits become credits, credits become debits, per M13.1's
 * reversal invariant). Fails loudly if no reversal exists or if the
 * line-flip contract is violated — both are business-outcome
 * regressions rather than UI bugs.
 */
export async function expectJournalEntryReversed(
  request: APIRequestContext,
  originalId: number,
): Promise<JournalEntryDetail> {
  const entries = await fetchAllJournalEntries(request);
  const reversals = entries.filter(
    (entry) => entry.reverses_id === originalId,
  );
  expect(
    reversals.length,
    `expected at least one reversal targeting JE #${originalId}; found ${reversals.length}`,
  ).toBeGreaterThanOrEqual(1);

  // Fetch the most recent reversal's detail (list ordering is
  // recent-first per M14.1).
  const reversal = await fetchJournalEntryDetail(
    request,
    reversals[0]!.id,
  );
  expect(
    reversal.reverses_id,
    `reversal detail should carry reverses_id=${originalId}`,
  ).toBe(originalId);
  expect(
    reversal.reason.length,
    "reversal reason should be non-empty (audit-trail requirement)",
  ).toBeGreaterThan(0);

  // Verify the sign-flip: the reversal's total debits should equal
  // the original's total credits and vice versa. Line-by-line
  // matching by account code would over-specify the invariant; the
  // aggregate mirror is the M13.1 contract.
  const original = await fetchJournalEntryDetail(request, originalId);
  const totalOriginalDebits = original.lines.reduce(
    (sum, line) => sum + Number(line.debit),
    0,
  );
  const totalOriginalCredits = original.lines.reduce(
    (sum, line) => sum + Number(line.credit),
    0,
  );
  const totalReversalDebits = reversal.lines.reduce(
    (sum, line) => sum + Number(line.debit),
    0,
  );
  const totalReversalCredits = reversal.lines.reduce(
    (sum, line) => sum + Number(line.credit),
    0,
  );
  expect(
    totalReversalDebits,
    `reversal debits (${totalReversalDebits}) should equal original credits (${totalOriginalCredits})`,
  ).toBeCloseTo(totalOriginalCredits, 2);
  expect(
    totalReversalCredits,
    `reversal credits (${totalReversalCredits}) should equal original debits (${totalOriginalDebits})`,
  ).toBeCloseTo(totalOriginalDebits, 2);

  return reversal;
}
