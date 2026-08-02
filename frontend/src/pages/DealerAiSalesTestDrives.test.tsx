// Milestone 11 · Increment 6 (SESSION_119) — DealerAiSalesTestDrives tests.

import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/salesApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/salesApi")>(
    "@/lib/salesApi",
  );
  return {
    ...actual,
    listTestDrives: vi.fn(),
  };
});

import { listTestDrives, type TestDriveProjection } from "@/lib/salesApi";
import DealerAiSalesTestDrives from "@/pages/DealerAiSalesTestDrives";


function makeDrive(overrides: Partial<TestDriveProjection> = {}): TestDriveProjection {
  return {
    id: 1,
    lead_id: 10,
    vehicle_id: 100,
    dealership_id: 1,
    driven_by_user_id: 5,
    driven_at: "2026-08-01T14:00:00Z",
    duration_minutes: 30,
    route_notes: "Highway loop",
    customer_reaction: "Positive",
    objections_captured: ["Wants leather"],
    next_action: "Send pricing",
    created_at: "2026-08-01T14:30:00Z",
    updated_at: "2026-08-01T14:30:00Z",
    ...overrides,
  };
}

async function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/dealer-ai-sales/test-drives"]}>
      <Routes>
        <Route
          path="/dealer-ai-sales/test-drives"
          element={<DealerAiSalesTestDrives />}
        />
      </Routes>
    </MemoryRouter>,
  );
}


describe("DealerAiSalesTestDrives", () => {
  beforeEach(() => {
    vi.mocked(listTestDrives).mockResolvedValue({
      count: 2,
      results: [
        makeDrive({ id: 1, lead_id: 10 }),
        makeDrive({ id: 2, lead_id: 11, duration_minutes: null }),
      ],
    });
  });

  afterEach(() => vi.clearAllMocks());

  it("renders every drive with duration + reaction + objections", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("#10")).toBeInTheDocument();
    });
    expect(screen.getByText("#11")).toBeInTheDocument();
    expect(screen.getByText("30 min")).toBeInTheDocument();
    // The second drive has null duration → dash rendered.
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Wants leather").length).toBeGreaterThan(0);
  });

  it("shows an empty state when no drives are recorded", async () => {
    vi.mocked(listTestDrives).mockResolvedValue({ count: 0, results: [] });
    await renderPage();
    await waitFor(() => {
      expect(
        screen.getByText(/no test drives recorded yet/i),
      ).toBeInTheDocument();
    });
  });

  it("shows the error message when the list fetch fails", async () => {
    vi.mocked(listTestDrives).mockRejectedValue(new Error("Boom"));
    await renderPage();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Boom");
    });
  });
});
