// Milestone 10 · Increment 7 (SESSION_112) — DealerFandIDeals tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/fAndIApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/fAndIApi")>(
    "@/lib/fAndIApi",
  );
  return {
    ...actual,
    fetchDeals: vi.fn(),
  };
});

vi.mock("@/lib/AuthContext", () => ({
  useAuth: () => ({
    hasRole: () => true,
  }),
}));

import { fetchDeals, type DealListItem } from "@/lib/fAndIApi";
import DealerFandIDeals from "@/pages/DealerFandIDeals";


const DEAL_SIGNED_FUNDED: DealListItem = {
  contract_id: 101,
  contract_state: "signed",
  contract_type: "risc",
  signed_at: "2026-08-15T10:00:00Z",
  voided_at: null,
  vehicle_stock: "STOCK-101",
  funding_state: "funded",
  funding_amount: "24500.00",
  chargeback_count: 0,
};

const DEAL_UNSIGNED: DealListItem = {
  contract_id: 102,
  contract_state: "unsigned",
  contract_type: "cash",
  signed_at: null,
  voided_at: null,
  vehicle_stock: "STOCK-102",
  funding_state: null,
  funding_amount: null,
  chargeback_count: 0,
};

async function renderPage() {
  const view = render(
    <MemoryRouter initialEntries={["/dealer-ai-f-and-i"]}>
      <Routes>
        <Route path="/dealer-ai-f-and-i" element={<DealerFandIDeals />} />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => {
    expect(fetchDeals).toHaveBeenCalled();
  });
  return view;
}


describe("DealerFandIDeals", () => {
  beforeEach(() => {
    vi.mocked(fetchDeals).mockResolvedValue([
      DEAL_SIGNED_FUNDED,
      DEAL_UNSIGNED,
    ]);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders both deals in the table", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("STOCK-101")).toBeInTheDocument();
    });
    expect(screen.getByText("STOCK-102")).toBeInTheDocument();
  });

  it("shows the funded amount for a funded deal", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText(/24500.00/)).toBeInTheDocument();
    });
  });

  it("shows em-dash for a deal without funding", async () => {
    await renderPage();
    await waitFor(() => {
      // STOCK-102 has funding_state=null — funding cell renders "—".
      expect(screen.getByText("STOCK-102")).toBeInTheDocument();
    });
    // The dash is present at least once (the unfunded row).
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("renders an 'Open jacket' link per row", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getAllByText("Open jacket").length).toBe(2);
    });
  });

  it("refetches when the contract-state filter changes", async () => {
    await renderPage();
    await waitFor(() => {
      expect(fetchDeals).toHaveBeenCalledTimes(1);
    });
    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByLabelText(/contract state filter/i),
      "signed",
    );
    await waitFor(() => {
      expect(fetchDeals).toHaveBeenCalledTimes(2);
    });
    expect(fetchDeals).toHaveBeenLastCalledWith({
      state: "signed",
      funding_state: undefined,
      has_chargebacks: undefined,
    });
  });

  it("refetches with has_chargebacks when the checkbox is checked", async () => {
    await renderPage();
    await waitFor(() => {
      expect(fetchDeals).toHaveBeenCalledTimes(1);
    });
    const user = userEvent.setup();
    await user.click(screen.getByLabelText(/has chargebacks/i));
    await waitFor(() => {
      expect(fetchDeals).toHaveBeenCalledTimes(2);
    });
    expect(fetchDeals).toHaveBeenLastCalledWith({
      state: undefined,
      funding_state: undefined,
      has_chargebacks: true,
    });
  });

  it("shows empty state when no deals match", async () => {
    vi.mocked(fetchDeals).mockResolvedValue([]);
    await renderPage();
    await waitFor(() => {
      expect(
        screen.getByText(/no deals match the current filters/i),
      ).toBeInTheDocument();
    });
  });

  it("shows an error state when the API fails", async () => {
    vi.mocked(fetchDeals).mockRejectedValue(new Error("Boom"));
    await renderPage();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Boom");
    });
  });
});
