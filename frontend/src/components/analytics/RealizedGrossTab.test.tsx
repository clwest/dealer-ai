// Milestone 9 · Increment 5 (SESSION_104) — RealizedGrossTab tests.
//
// End-to-end render tests for the fifth "Realized Gross" tab.
// Follows the M8.5 AcquisitionReconTab test pattern: mock the four
// API fetches, mock recharts ResponsiveContainer, assert on rendered
// text.

import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ForbiddenError } from "@/lib/authFetch";

vi.mock("@/lib/analyticsApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/analyticsApi")>(
    "@/lib/analyticsApi",
  );
  return {
    ...actual,
    fetchVehicleTypeProfitability: vi.fn(),
    fetchGrossProfitTrend: vi.fn(),
    fetchInventoryTurn: vi.fn(),
    fetchBuyerEstimateAccuracy: vi.fn(),
  };
});

vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 400, height: 300 }}>{children}</div>
    ),
  };
});

import {
  fetchBuyerEstimateAccuracy,
  fetchGrossProfitTrend,
  fetchInventoryTurn,
  fetchVehicleTypeProfitability,
} from "@/lib/analyticsApi";
import { RealizedGrossTab } from "@/components/analytics/RealizedGrossTab";

beforeEach(() => {
  vi.mocked(fetchVehicleTypeProfitability).mockReset();
  vi.mocked(fetchGrossProfitTrend).mockReset();
  vi.mocked(fetchInventoryTurn).mockReset();
  vi.mocked(fetchBuyerEstimateAccuracy).mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("RealizedGrossTab", () => {
  it("shows loading state initially across all four sections", () => {
    vi.mocked(fetchVehicleTypeProfitability).mockReturnValue(
      new Promise(() => {}),
    );
    vi.mocked(fetchGrossProfitTrend).mockReturnValue(new Promise(() => {}));
    vi.mocked(fetchInventoryTurn).mockReturnValue(new Promise(() => {}));
    vi.mocked(fetchBuyerEstimateAccuracy).mockReturnValue(new Promise(() => {}));
    render(<RealizedGrossTab />);
    expect(screen.getAllByText("Loading…").length).toBe(4);
  });

  it("renders Q3 vehicle-type profitability rows with formatted money + percent", async () => {
    vi.mocked(fetchVehicleTypeProfitability).mockResolvedValue({
      rows: [
        {
          make: "Ford",
          model: "F-150",
          sold_count: 4,
          total_sale_gross: "12500.00",
          total_sold_price: "135000.00",
          mean_gross_pct: "9.26",
        },
      ],
    });
    vi.mocked(fetchGrossProfitTrend).mockResolvedValue({
      window_days: 90,
      points: [],
    });
    vi.mocked(fetchInventoryTurn).mockResolvedValue({
      window_days: 90,
      report: {
        sold_count: 0,
        mean_days: null,
        p50_days: null,
        p90_days: null,
        min_days: null,
        max_days: null,
      },
    });
    vi.mocked(fetchBuyerEstimateAccuracy).mockResolvedValue({
      window_days: 90,
      buyer_user_id: null,
      rows: [],
    });

    render(<RealizedGrossTab />);
    await waitFor(() => {
      expect(screen.getByText("F-150")).toBeInTheDocument();
    });
    expect(screen.getByText("$12,500.00")).toBeInTheDocument();
    expect(screen.getByText("$135,000.00")).toBeInTheDocument();
    expect(screen.getByText("9.26%")).toBeInTheDocument();
  });

  it("renders Q6 gross-profit chart when points exist", async () => {
    vi.mocked(fetchVehicleTypeProfitability).mockResolvedValue({ rows: [] });
    vi.mocked(fetchGrossProfitTrend).mockResolvedValue({
      window_days: 90,
      points: [
        {
          sale_date: "2026-07-20",
          sale_count: 2,
          total_gross_realized: "8500.00",
        },
      ],
    });
    vi.mocked(fetchInventoryTurn).mockResolvedValue({
      window_days: 90,
      report: {
        sold_count: 0,
        mean_days: null,
        p50_days: null,
        p90_days: null,
        min_days: null,
        max_days: null,
      },
    });
    vi.mocked(fetchBuyerEstimateAccuracy).mockResolvedValue({
      window_days: 90,
      buyer_user_id: null,
      rows: [],
    });

    render(<RealizedGrossTab />);
    await waitFor(() => {
      expect(
        screen.getByTestId("gross-profit-trend-chart"),
      ).toBeInTheDocument();
    });
  });

  it("renders Q8 inventory-turn summary card when sold_count > 0", async () => {
    vi.mocked(fetchVehicleTypeProfitability).mockResolvedValue({ rows: [] });
    vi.mocked(fetchGrossProfitTrend).mockResolvedValue({
      window_days: 90,
      points: [],
    });
    vi.mocked(fetchInventoryTurn).mockResolvedValue({
      window_days: 90,
      report: {
        sold_count: 12,
        mean_days: "18.50",
        p50_days: 17,
        p90_days: 32,
        min_days: 4,
        max_days: 55,
      },
    });
    vi.mocked(fetchBuyerEstimateAccuracy).mockResolvedValue({
      window_days: 90,
      buyer_user_id: null,
      rows: [],
    });

    render(<RealizedGrossTab />);
    await waitFor(() => {
      expect(screen.getByTestId("inventory-turn-summary")).toBeInTheDocument();
    });
    expect(screen.getByText("18.50")).toBeInTheDocument();
    expect(screen.getByText("17")).toBeInTheDocument();
    expect(screen.getByText("32")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("renders Q7 buyer accuracy rank rows with formatted percent", async () => {
    vi.mocked(fetchVehicleTypeProfitability).mockResolvedValue({ rows: [] });
    vi.mocked(fetchGrossProfitTrend).mockResolvedValue({
      window_days: 90,
      points: [],
    });
    vi.mocked(fetchInventoryTurn).mockResolvedValue({
      window_days: 90,
      report: {
        sold_count: 0,
        mean_days: null,
        p50_days: null,
        p90_days: null,
        min_days: null,
        max_days: null,
      },
    });
    vi.mocked(fetchBuyerEstimateAccuracy).mockResolvedValue({
      window_days: 90,
      buyer_user_id: null,
      rows: [
        {
          buyer_user_id: 42,
          buyer_display: "Alice Bidder",
          vehicle_count: 5,
          work_order_count: 13,
          mean_absolute_variance_pct: "8.50",
          bias_pct: "-2.25",
        },
      ],
    });

    render(<RealizedGrossTab />);
    await waitFor(() => {
      expect(screen.getByText("Alice Bidder")).toBeInTheDocument();
    });
    expect(screen.getByText("8.50%")).toBeInTheDocument();
    expect(screen.getByText("-2.25%")).toBeInTheDocument();
  });

  it("shows empty-state text when every section returns zero", async () => {
    vi.mocked(fetchVehicleTypeProfitability).mockResolvedValue({ rows: [] });
    vi.mocked(fetchGrossProfitTrend).mockResolvedValue({
      window_days: 90,
      points: [],
    });
    vi.mocked(fetchInventoryTurn).mockResolvedValue({
      window_days: 90,
      report: {
        sold_count: 0,
        mean_days: null,
        p50_days: null,
        p90_days: null,
        min_days: null,
        max_days: null,
      },
    });
    vi.mocked(fetchBuyerEstimateAccuracy).mockResolvedValue({
      window_days: 90,
      buyer_user_id: null,
      rows: [],
    });

    render(<RealizedGrossTab />);
    await waitFor(() => {
      expect(
        screen.getAllByText(/no sales in the window yet/i).length,
      ).toBeGreaterThanOrEqual(1);
    });
    expect(
      screen.getByText(/no sold vehicles with frontline history/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/no buyer data in the window yet/i),
    ).toBeInTheDocument();
  });

  it("shows Access denied when the profitability fetch throws ForbiddenError", async () => {
    vi.mocked(fetchVehicleTypeProfitability).mockRejectedValue(
      new ForbiddenError(),
    );
    vi.mocked(fetchGrossProfitTrend).mockResolvedValue({
      window_days: 90,
      points: [],
    });
    vi.mocked(fetchInventoryTurn).mockResolvedValue({
      window_days: 90,
      report: {
        sold_count: 0,
        mean_days: null,
        p50_days: null,
        p90_days: null,
        min_days: null,
        max_days: null,
      },
    });
    vi.mocked(fetchBuyerEstimateAccuracy).mockResolvedValue({
      window_days: 90,
      buyer_user_id: null,
      rows: [],
    });

    render(<RealizedGrossTab />);
    await waitFor(() => {
      expect(screen.getAllByText(/access denied/i).length).toBeGreaterThanOrEqual(1);
    });
  });
});
