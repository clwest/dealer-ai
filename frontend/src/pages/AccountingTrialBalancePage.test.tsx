// Milestone 14 · Increment 2 (SESSION_135) — trial-balance page tests.

import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/accountingApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/accountingApi")>(
    "@/lib/accountingApi",
  );
  return {
    ...actual,
    fetchTrialBalance: vi.fn(),
    fetchCostPostingFailures: vi.fn(),
  };
});

import {
  fetchCostPostingFailures,
  fetchTrialBalance,
  type CostPostingFailure,
  type CostPostingFailuresResponse,
  type TrialBalanceSnapshot,
} from "@/lib/accountingApi";
import AccountingTrialBalancePage from "@/pages/AccountingTrialBalancePage";


function makeFailure(
  overrides: Partial<CostPostingFailure> = {},
): CostPostingFailure {
  return {
    id: 1,
    vehicle_id: 100,
    vehicle_stock: "STOCK-001",
    category: "parts",
    category_display: "Parts",
    amount: "125.50",
    reference: "INV-9",
    vendor: "Vendor",
    incurred_at: "2026-08-01T00:00:00Z",
    created_at: "2026-08-01T00:00:00Z",
    age_in_hours: 48,
    ...overrides,
  };
}


function makeFailuresResponse(
  overrides: Partial<CostPostingFailuresResponse> = {},
): CostPostingFailuresResponse {
  const defaults: CostPostingFailuresResponse = {
    failures: [],
    count: 0,
    threshold_hours: 24,
    as_of: "2026-08-02T10:00:00Z",
  };
  return { ...defaults, ...overrides };
}


function makeSnapshot(
  overrides: Partial<TrialBalanceSnapshot> = {},
): TrialBalanceSnapshot {
  return {
    dealership_id: 1,
    dealership_slug: "copper-canyon",
    as_of: "2026-08-02T10:00:00Z",
    total_debits: "1250.00",
    total_credits: "1250.00",
    is_balanced: true,
    rows: [
      {
        account_code: "122000",
        account_name: "Recon WIP",
        account_type: "asset",
        debit_total: "1000.00",
        credit_total: "0.00",
        natural_balance: "1000.00",
      },
      {
        account_code: "200000",
        account_name: "A/P Trade",
        account_type: "liability",
        debit_total: "0.00",
        credit_total: "1000.00",
        natural_balance: "1000.00",
      },
      {
        account_code: "400000",
        account_name: "Sales Revenue",
        account_type: "revenue",
        debit_total: "0.00",
        credit_total: "250.00",
        natural_balance: "250.00",
      },
      {
        account_code: "100000",
        account_name: "Cash",
        account_type: "asset",
        debit_total: "250.00",
        credit_total: "0.00",
        natural_balance: "250.00",
      },
    ],
    ...overrides,
  };
}


async function renderPage() {
  const view = render(
    <MemoryRouter initialEntries={["/dealer-ai-accounting/trial-balance"]}>
      <Routes>
        <Route
          path="/dealer-ai-accounting/trial-balance"
          element={<AccountingTrialBalancePage />}
        />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => {
    expect(fetchTrialBalance).toHaveBeenCalled();
  });
  return view;
}


describe("AccountingTrialBalancePage", () => {
  beforeEach(() => {
    vi.mocked(fetchTrialBalance).mockReset();
    vi.mocked(fetchTrialBalance).mockResolvedValue(makeSnapshot());
    vi.mocked(fetchCostPostingFailures).mockReset();
    vi.mocked(fetchCostPostingFailures).mockResolvedValue(
      makeFailuresResponse(),
    );
  });

  it("renders the header", async () => {
    await renderPage();
    expect(
      screen.getByRole("heading", { level: 1, name: /Trial Balance/i }),
    ).toBeInTheDocument();
  });

  it("shows a loading state before data resolves", async () => {
    let resolveIt: (snapshot: TrialBalanceSnapshot) => void = () => {};
    vi.mocked(fetchTrialBalance).mockImplementation(
      () =>
        new Promise<TrialBalanceSnapshot>((resolve) => {
          resolveIt = resolve;
        }),
    );
    render(
      <MemoryRouter initialEntries={["/dealer-ai-accounting/trial-balance"]}>
        <Routes>
          <Route
            path="/dealer-ai-accounting/trial-balance"
            element={<AccountingTrialBalancePage />}
          />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText(/Loading trial balance/i)).toBeInTheDocument();
    resolveIt(makeSnapshot());
    await waitFor(() =>
      expect(screen.queryByText(/Loading trial balance/i)).not.toBeInTheDocument(),
    );
  });

  it("renders every account row", async () => {
    await renderPage();
    expect(screen.getByText("122000")).toBeInTheDocument();
    expect(screen.getByText("Recon WIP")).toBeInTheDocument();
    expect(screen.getByText("200000")).toBeInTheDocument();
    expect(screen.getByText("A/P Trade")).toBeInTheDocument();
    expect(screen.getByText("400000")).toBeInTheDocument();
    expect(screen.getByText("Sales Revenue")).toBeInTheDocument();
    expect(screen.getByText("100000")).toBeInTheDocument();
    expect(screen.getByText("Cash")).toBeInTheDocument();
  });

  it("formats money values with locale-aware currency", async () => {
    await renderPage();
    // Grand totals appear once in the footer.
    expect(screen.getAllByText("$1,250.00").length).toBeGreaterThanOrEqual(2);
    // Per-row values render as currency.
    expect(screen.getAllByText("$1,000.00").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("$250.00").length).toBeGreaterThanOrEqual(2);
  });

  it("renders the balanced chip when is_balanced=true", async () => {
    await renderPage();
    expect(screen.getByText("Balanced")).toBeInTheDocument();
    expect(screen.queryByText("Unbalanced")).not.toBeInTheDocument();
  });

  it("renders the unbalanced chip when is_balanced=false", async () => {
    vi.mocked(fetchTrialBalance).mockResolvedValue(
      makeSnapshot({ is_balanced: false }),
    );
    await renderPage();
    expect(screen.getByText("Unbalanced")).toBeInTheDocument();
    expect(screen.queryByText("Balanced")).not.toBeInTheDocument();
  });

  it("shows the empty-state message when rows is empty", async () => {
    vi.mocked(fetchTrialBalance).mockResolvedValue(
      makeSnapshot({
        rows: [],
        total_debits: "0.00",
        total_credits: "0.00",
      }),
    );
    await renderPage();
    expect(screen.getByText(/No postings yet/i)).toBeInTheDocument();
  });

  it("hides the totals footer when rows is empty", async () => {
    vi.mocked(fetchTrialBalance).mockResolvedValue(
      makeSnapshot({
        rows: [],
        total_debits: "0.00",
        total_credits: "0.00",
      }),
    );
    await renderPage();
    expect(screen.queryByText(/Total debits/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Total credits/i)).not.toBeInTheDocument();
  });

  it("renders the error state when fetchTrialBalance rejects", async () => {
    vi.mocked(fetchTrialBalance).mockRejectedValue(new Error("boom"));
    render(
      <MemoryRouter initialEntries={["/dealer-ai-accounting/trial-balance"]}>
        <Routes>
          <Route
            path="/dealer-ai-accounting/trial-balance"
            element={<AccountingTrialBalancePage />}
          />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByText("boom")).toBeInTheDocument(),
    );
  });

  it("renders the account-type badge per row", async () => {
    await renderPage();
    // Asset appears twice (Cash + Recon WIP), liability once, revenue once.
    expect(screen.getAllByText("Asset").length).toBe(2);
    expect(screen.getByText("Liability")).toBeInTheDocument();
    expect(screen.getByText("Revenue")).toBeInTheDocument();
  });

  it("renders the dealership slug in the card title", async () => {
    await renderPage();
    expect(screen.getByText(/copper-canyon/i)).toBeInTheDocument();
  });

  it("hides the cost-posting failures card when count is 0", async () => {
    await renderPage();
    expect(
      screen.queryByText(/Cost-posting failures/i),
    ).not.toBeInTheDocument();
  });

  it("renders the cost-posting failures card when count > 0", async () => {
    vi.mocked(fetchCostPostingFailures).mockResolvedValue(
      makeFailuresResponse({
        failures: [
          makeFailure({
            id: 1,
            vehicle_stock: "STOCK-A",
            category_display: "Parts",
            amount: "125.50",
            age_in_hours: 48,
          }),
          makeFailure({
            id: 2,
            vehicle_stock: "STOCK-B",
            category_display: "Labor",
            amount: "300.00",
            age_in_hours: 72,
          }),
        ],
        count: 2,
      }),
    );
    await renderPage();
    expect(screen.getByText(/Cost-posting failures \(2\)/)).toBeInTheDocument();
    expect(screen.getByText("STOCK-A")).toBeInTheDocument();
    expect(screen.getByText("STOCK-B")).toBeInTheDocument();
    expect(screen.getByText("$125.50")).toBeInTheDocument();
    expect(screen.getByText("$300.00")).toBeInTheDocument();
    expect(screen.getByText("48")).toBeInTheDocument();
    expect(screen.getByText("72")).toBeInTheDocument();
  });

  it("renders the attention badge on the failures card", async () => {
    vi.mocked(fetchCostPostingFailures).mockResolvedValue(
      makeFailuresResponse({ failures: [makeFailure()], count: 1 }),
    );
    await renderPage();
    expect(screen.getByText("Attention")).toBeInTheDocument();
  });
});
