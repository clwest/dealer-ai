// Milestone 14 · Increment 2 (SESSION_135) — trial-balance page tests.
// Milestone 17 · Increment 2 (SESSION_145) — extended coverage for the
// as_of picker + freeze button + snapshot history list + inline detail.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    listTrialBalanceSnapshots: vi.fn(),
    freezeTrialBalance: vi.fn(),
    fetchTrialBalanceSnapshot: vi.fn(),
  };
});

import { ApiError } from "@/lib/authFetch";
import {
  fetchCostPostingFailures,
  fetchTrialBalance,
  fetchTrialBalanceSnapshot,
  freezeTrialBalance,
  listTrialBalanceSnapshots,
  type CostPostingFailure,
  type CostPostingFailuresResponse,
  type FrozenTrialBalanceSnapshot,
  type TrialBalanceSnapshot,
  type TrialBalanceSnapshotListPage,
  type TrialBalanceSnapshotSummary,
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


function makeSummary(
  overrides: Partial<TrialBalanceSnapshotSummary> = {},
): TrialBalanceSnapshotSummary {
  return {
    id: 100,
    as_of: "2026-07-31T23:59:59Z",
    total_debits: "5000.00",
    total_credits: "5000.00",
    is_balanced: true,
    created_at: "2026-08-01T09:00:00Z",
    created_by_user_id: 7,
    created_by_username: "sm-user",
    ...overrides,
  };
}


function makeSnapshotList(
  overrides: Partial<TrialBalanceSnapshotListPage> = {},
): TrialBalanceSnapshotListPage {
  return {
    snapshots: [],
    total_count: 0,
    page: 1,
    page_size: 10,
    ...overrides,
  };
}


function makeFrozenSnapshot(
  overrides: Partial<FrozenTrialBalanceSnapshot> = {},
): FrozenTrialBalanceSnapshot {
  return {
    ...makeSummary({ id: 100 }),
    rows: [
      {
        account_code: "100000",
        account_name: "Cash on Hand",
        account_type: "asset",
        debit_total: "5000.00",
        credit_total: "0.00",
        natural_balance: "5000.00",
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
    vi.mocked(listTrialBalanceSnapshots).mockReset();
    vi.mocked(listTrialBalanceSnapshots).mockResolvedValue(makeSnapshotList());
    vi.mocked(freezeTrialBalance).mockReset();
    vi.mocked(fetchTrialBalanceSnapshot).mockReset();
  });

  // ---- M14.2 legacy coverage (preserved) --------------------------------

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
    expect(screen.getAllByText("$1,250.00").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("$1,000.00").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("$250.00").length).toBeGreaterThanOrEqual(2);
  });

  it("renders the balanced chip when is_balanced=true", async () => {
    await renderPage();
    expect(screen.getAllByText("Balanced").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText("Unbalanced")).not.toBeInTheDocument();
  });

  it("renders the unbalanced chip when is_balanced=false", async () => {
    vi.mocked(fetchTrialBalance).mockResolvedValue(
      makeSnapshot({ is_balanced: false }),
    );
    await renderPage();
    expect(screen.getByText("Unbalanced")).toBeInTheDocument();
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
    expect(
      screen.getByText(/No postings through this date/i),
    ).toBeInTheDocument();
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
  });

  // ---- M17.2 new coverage -----------------------------------------------

  it("renders the as_of picker with today as default", async () => {
    await renderPage();
    const picker = screen.getByLabelText(/As of/i) as HTMLInputElement;
    expect(picker).toBeInTheDocument();
    expect(picker.type).toBe("date");
    const today = new Date();
    const expected = `${today.getFullYear()}-${String(
      today.getMonth() + 1,
    ).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
    expect(picker.value).toBe(expected);
  });

  it("passes the picker date to fetchTrialBalance as an ISO timestamp", async () => {
    await renderPage();
    const [call] = vi.mocked(fetchTrialBalance).mock.calls;
    expect(call).toBeDefined();
    expect(typeof call[0]).toBe("string");
    // ISO timestamp should be end-of-day.
    expect(call[0]).toMatch(/T\d{2}:\d{2}:\d{2}/);
  });

  it("refetches trial balance when the picker changes", async () => {
    await renderPage();
    vi.mocked(fetchTrialBalance).mockClear();
    const picker = screen.getByLabelText(/As of/i) as HTMLInputElement;
    fireEvent.change(picker, { target: { value: "2026-05-31" } });
    await waitFor(() => {
      expect(fetchTrialBalance).toHaveBeenCalled();
    });
    const [refetchCall] = vi.mocked(fetchTrialBalance).mock.calls;
    expect(refetchCall[0]).toContain("2026");
  });

  it("renders the 'Freeze this view' button", async () => {
    await renderPage();
    expect(
      screen.getByRole("button", { name: /Freeze this view/i }),
    ).toBeInTheDocument();
  });

  it("calls freezeTrialBalance on button click and shows success banner", async () => {
    vi.mocked(freezeTrialBalance).mockResolvedValue(makeFrozenSnapshot());
    await renderPage();
    const button = screen.getByRole("button", { name: /Freeze this view/i });
    fireEvent.click(button);
    await waitFor(() => {
      expect(freezeTrialBalance).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(
        screen.getByText(/snapshot #100 recorded/i),
      ).toBeInTheDocument();
    });
  });

  it("shows the 409 duplicate error banner on ApiError(409)", async () => {
    vi.mocked(freezeTrialBalance).mockRejectedValue(
      new ApiError(409, "duplicate"),
    );
    await renderPage();
    fireEvent.click(
      screen.getByRole("button", { name: /Freeze this view/i }),
    );
    await waitFor(() => {
      expect(
        screen.getByText(/already exists/i),
      ).toBeInTheDocument();
    });
  });

  it("shows the generic error banner on non-409 freeze failure", async () => {
    vi.mocked(freezeTrialBalance).mockRejectedValue(
      new Error("network exploded"),
    );
    await renderPage();
    fireEvent.click(
      screen.getByRole("button", { name: /Freeze this view/i }),
    );
    await waitFor(() => {
      expect(
        screen.getByText(/network exploded/i),
      ).toBeInTheDocument();
    });
  });

  it("refetches the snapshot list after a successful freeze", async () => {
    vi.mocked(freezeTrialBalance).mockResolvedValue(makeFrozenSnapshot());
    await renderPage();
    vi.mocked(listTrialBalanceSnapshots).mockClear();
    fireEvent.click(
      screen.getByRole("button", { name: /Freeze this view/i }),
    );
    await waitFor(() => {
      expect(listTrialBalanceSnapshots).toHaveBeenCalled();
    });
  });

  it("shows the 'no closes yet' state when snapshot list is empty", async () => {
    await renderPage();
    expect(
      screen.getByText(/No period closes have been frozen yet/i),
    ).toBeInTheDocument();
  });

  it("renders the Prior closes list when snapshots exist", async () => {
    vi.mocked(listTrialBalanceSnapshots).mockResolvedValue(
      makeSnapshotList({
        snapshots: [makeSummary({ id: 42, created_by_username: "op-1" })],
        total_count: 1,
      }),
    );
    await renderPage();
    expect(screen.getByText(/Prior closes \(1\)/)).toBeInTheDocument();
    expect(screen.getByText(/op-1/)).toBeInTheDocument();
  });

  it("loads the frozen detail when a prior close row is clicked", async () => {
    vi.mocked(listTrialBalanceSnapshots).mockResolvedValue(
      makeSnapshotList({
        snapshots: [makeSummary({ id: 42 })],
        total_count: 1,
      }),
    );
    vi.mocked(fetchTrialBalanceSnapshot).mockResolvedValue(
      makeFrozenSnapshot({ id: 42 }),
    );
    await renderPage();
    const row = screen.getByTestId("snapshot-row-42");
    fireEvent.click(row);
    await waitFor(() => {
      expect(fetchTrialBalanceSnapshot).toHaveBeenCalledWith(42);
    });
    await waitFor(() => {
      expect(
        screen.getByText(/Frozen snapshot #42/i),
      ).toBeInTheDocument();
    });
  });

  it("closes the frozen detail card when Close is clicked", async () => {
    vi.mocked(listTrialBalanceSnapshots).mockResolvedValue(
      makeSnapshotList({
        snapshots: [makeSummary({ id: 42 })],
        total_count: 1,
      }),
    );
    vi.mocked(fetchTrialBalanceSnapshot).mockResolvedValue(
      makeFrozenSnapshot({ id: 42 }),
    );
    await renderPage();
    fireEvent.click(screen.getByTestId("snapshot-row-42"));
    await waitFor(() =>
      expect(
        screen.getByText(/Frozen snapshot #42/i),
      ).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: /Close/i }));
    await waitFor(() =>
      expect(
        screen.queryByText(/Frozen snapshot #42/i),
      ).not.toBeInTheDocument(),
    );
  });

  it("frozen detail renders frozen row values (not live)", async () => {
    vi.mocked(listTrialBalanceSnapshots).mockResolvedValue(
      makeSnapshotList({
        snapshots: [makeSummary({ id: 42 })],
        total_count: 1,
      }),
    );
    vi.mocked(fetchTrialBalanceSnapshot).mockResolvedValue(
      makeFrozenSnapshot({
        id: 42,
        rows: [
          {
            account_code: "FROZEN-100000",
            account_name: "Frozen Cash",
            account_type: "asset",
            debit_total: "9999.99",
            credit_total: "0.00",
            natural_balance: "9999.99",
          },
        ],
      }),
    );
    await renderPage();
    fireEvent.click(screen.getByTestId("snapshot-row-42"));
    await waitFor(() =>
      expect(screen.getByText("FROZEN-100000")).toBeInTheDocument(),
    );
    expect(screen.getByText("Frozen Cash")).toBeInTheDocument();
    // Frozen debit + natural balance both render as $9,999.99.
    expect(screen.getAllByText("$9,999.99").length).toBeGreaterThanOrEqual(1);
  });

  it("clears the freeze banner when the picker changes", async () => {
    vi.mocked(freezeTrialBalance).mockResolvedValue(makeFrozenSnapshot());
    await renderPage();
    fireEvent.click(
      screen.getByRole("button", { name: /Freeze this view/i }),
    );
    await waitFor(() =>
      expect(
        screen.getByText(/snapshot #100 recorded/i),
      ).toBeInTheDocument(),
    );
    const picker = screen.getByLabelText(/As of/i);
    fireEvent.change(picker, { target: { value: "2026-05-15" } });
    await waitFor(() =>
      expect(
        screen.queryByText(/snapshot #100 recorded/i),
      ).not.toBeInTheDocument(),
    );
  });
});
