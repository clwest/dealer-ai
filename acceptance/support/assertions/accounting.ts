// Milestone 20 · Increment 3 — business-outcome assertion helpers
// for the office/accounting workflow journey.
//
// Per the M20 guiding principle: assertions target business state
// (a TrialBalanceSnapshot exists with rows summing to the expected
// totals) via the admin API, not DOM state.

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
