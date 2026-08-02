// Milestone 8 · Increment 5 (SESSION_098) — AcquisitionReconTab tests.
//
// End-to-end render tests with the analytics API-client fetches
// mocked. Recharts is heavy and requires layout — mock the
// ResponsiveContainer to a plain div so the chart region renders
// deterministically without a browser-level layout engine.

import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ForbiddenError } from "@/lib/authFetch";

// Mock the API-client module before importing the component so the
// component picks up the stubbed exports on first import.
vi.mock("@/lib/analyticsApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/analyticsApi")>(
    "@/lib/analyticsApi",
  );
  return {
    ...actual,
    fetchReconCostPerSource: vi.fn(),
    fetchVehicleTypeReconCost: vi.fn(),
  };
});

// Recharts ResponsiveContainer measures the DOM — jsdom has no
// layout, so it renders 0×0 and the chart body never mounts. Stub
// it to a plain div so the chart region is discoverable.
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
  fetchReconCostPerSource,
  fetchVehicleTypeReconCost,
} from "@/lib/analyticsApi";
import { AcquisitionReconTab } from "@/components/analytics/AcquisitionReconTab";

beforeEach(() => {
  vi.mocked(fetchReconCostPerSource).mockReset();
  vi.mocked(fetchVehicleTypeReconCost).mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AcquisitionReconTab", () => {
  it("shows loading state initially", () => {
    vi.mocked(fetchReconCostPerSource).mockReturnValue(new Promise(() => {}));
    vi.mocked(fetchVehicleTypeReconCost).mockReturnValue(new Promise(() => {}));
    render(<AcquisitionReconTab />);
    // Both sections show a loading spinner.
    expect(screen.getAllByText("Loading…").length).toBeGreaterThanOrEqual(1);
  });

  it("renders rows from a successful source-rollup fetch", async () => {
    vi.mocked(fetchReconCostPerSource).mockResolvedValue({
      rows: [
        {
          source: "auction",
          source_display: "Auction",
          vehicle_count: 3,
          total_recon_cost: "1500.00",
          mean_recon_cost: "500.00",
        },
      ],
    });
    vi.mocked(fetchVehicleTypeReconCost).mockResolvedValue({ rows: [] });
    render(<AcquisitionReconTab />);
    await waitFor(() => {
      expect(screen.getByText("Auction")).toBeInTheDocument();
    });
    expect(screen.getByText("$1,500.00")).toBeInTheDocument();
    expect(screen.getByText("$500.00")).toBeInTheDocument();
  });

  it("shows the empty state when the source rollup returns zero rows", async () => {
    vi.mocked(fetchReconCostPerSource).mockResolvedValue({ rows: [] });
    vi.mocked(fetchVehicleTypeReconCost).mockResolvedValue({ rows: [] });
    render(<AcquisitionReconTab />);
    await waitFor(() => {
      expect(
        screen.getByText(/no recon-cost history yet/i),
      ).toBeInTheDocument();
    });
  });

  it("shows the forbidden banner when the fetch throws ForbiddenError", async () => {
    vi.mocked(fetchReconCostPerSource).mockRejectedValue(
      new ForbiddenError("nope"),
    );
    vi.mocked(fetchVehicleTypeReconCost).mockResolvedValue({ rows: [] });
    render(<AcquisitionReconTab />);
    await waitFor(() => {
      expect(
        screen.getByText(/access denied/i),
      ).toBeInTheDocument();
    });
  });
});
