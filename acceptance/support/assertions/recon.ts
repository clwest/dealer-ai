// Milestone 20 · Increment 3 — business-outcome assertion helpers
// for the recon workflow journey.
//
// Per the M20 guiding principle: assertions target business state
// (a ReconDecision was persisted with the expected tier) via the
// admin API, not DOM state.

import { APIRequestContext, expect } from "@playwright/test";

export interface ReconDashboardFinding {
  id: number;
  category: string;
  severity: string;
  description: string;
  estimated_cost: string | null;
  decision: {
    tier: string;
    decided_by: string | null;
    decided_at: string | null;
    notes: string;
  } | null;
}

export interface ReconDashboard {
  vehicle: {
    id: number;
    stock_number: string;
    year: number;
    model: string;
  };
  latest_condition_report: {
    id: number;
    inspector_name: string;
    inspected_at: string;
    mileage_at_inspection: number;
    findings: ReconDashboardFinding[];
  } | null;
  work_orders: unknown[];
  communications: unknown[];
}

async function fetchReconDashboard(
  request: APIRequestContext,
  stock: string,
): Promise<ReconDashboard> {
  const url = `/api/dealer-ai/admin/vehicles/${encodeURIComponent(
    stock,
  )}/recon/`;
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  return (await response.json()) as ReconDashboard;
}

/**
 * Assert that the recon dashboard for the given stock number has a
 * finding whose description contains `descriptionSubstring`.
 * Returns the matched finding for further assertions (e.g. tier
 * checking after the journey clicks a decision button).
 */
export async function expectFinding(
  request: APIRequestContext,
  stock: string,
  descriptionSubstring: string,
): Promise<ReconDashboardFinding> {
  const dashboard = await fetchReconDashboard(request, stock);
  expect(
    dashboard.latest_condition_report,
    `vehicle ${stock} should have a completed condition report`,
  ).not.toBeNull();
  const findings = dashboard.latest_condition_report?.findings ?? [];
  const match = findings.find((f) =>
    f.description.includes(descriptionSubstring),
  );
  expect(
    match,
    `expected finding containing "${descriptionSubstring}" on vehicle ${stock}; got ${findings
      .map((f) => f.description)
      .join(" | ") || "(no findings)"}`,
  ).toBeDefined();
  return match as ReconDashboardFinding;
}

/**
 * Assert that the named finding now has a persisted ReconDecision
 * with the expected tier. Business-outcome assertion for the
 * recon workflow journey — proves the tier-button click landed at
 * the service layer.
 */
export async function expectDecisionRecorded(
  request: APIRequestContext,
  stock: string,
  descriptionSubstring: string,
  expectedTier: "must_do" | "should_do" | "wont_do",
): Promise<void> {
  const finding = await expectFinding(
    request,
    stock,
    descriptionSubstring,
  );
  expect(
    finding.decision,
    `expected finding "${descriptionSubstring}" on vehicle ${stock} to have a recorded decision`,
  ).not.toBeNull();
  expect(
    finding.decision?.tier,
    `expected finding "${descriptionSubstring}" on vehicle ${stock} to be tier=${expectedTier}`,
  ).toBe(expectedTier);
}
