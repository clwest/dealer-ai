// Milestone 12 · Increment 7 (SESSION_127) — portfolio dashboard tests.

import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/bhphApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/bhphApi")>(
    "@/lib/bhphApi",
  );
  return {
    ...actual,
    fetchBhphAnalyticsSummary: vi.fn(),
    listBhphNotes: vi.fn(),
  };
});

import {
  fetchBhphAnalyticsSummary,
  listBhphNotes,
  type BhphAnalyticsSummary,
  type BhphNoteProjection,
} from "@/lib/bhphApi";
import DealerAiBhphPortfolio from "@/pages/DealerAiBhphPortfolio";


function makeSummary(
  overrides: Partial<BhphAnalyticsSummary> = {},
): BhphAnalyticsSummary {
  return {
    bucket_histogram: [
      { bucket: "current", note_count: 3, principal_total: "24000.00" },
      { bucket: "1_15", note_count: 1, principal_total: "8000.00" },
      { bucket: "16_30", note_count: 0, principal_total: "0.00" },
      { bucket: "31_60", note_count: 0, principal_total: "0.00" },
      { bucket: "61_90", note_count: 0, principal_total: "0.00" },
      { bucket: "over_90", note_count: 0, principal_total: "0.00" },
      {
        bucket: "charge_off_candidate",
        note_count: 0,
        principal_total: "0.00",
      },
    ],
    total_note_count: 4,
    total_principal_financed: "32000.00",
    cure_rate: "0.7500",
    weighted_average_apr: "21.90",
    weighted_average_days_past_due: "3.75",
    ptp_kept_ratio: "0.6667",
    ...overrides,
  };
}


function makeNote(
  overrides: Partial<BhphNoteProjection> = {},
): BhphNoteProjection {
  return {
    id: 1,
    sale_id: 100,
    dealership_id: 1,
    principal_financed: "8000.00",
    apr: "21.90",
    term_weeks: 104,
    payment_frequency: "weekly",
    payment_amount: "95.00",
    first_payment_due: "2026-09-01",
    default_grace_days: 5,
    current_bucket: "current",
    days_past_due: 0,
    created_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T00:00:00Z",
    ...overrides,
  };
}


async function renderPage() {
  const view = render(
    <MemoryRouter initialEntries={["/dealer-ai-bhph/portfolio"]}>
      <Routes>
        <Route
          path="/dealer-ai-bhph/portfolio"
          element={<DealerAiBhphPortfolio />}
        />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => {
    expect(fetchBhphAnalyticsSummary).toHaveBeenCalled();
    expect(listBhphNotes).toHaveBeenCalled();
  });
  return view;
}


describe("DealerAiBhphPortfolio", () => {
  beforeEach(() => {
    vi.mocked(fetchBhphAnalyticsSummary).mockResolvedValue(makeSummary());
    vi.mocked(listBhphNotes).mockResolvedValue({
      count: 2,
      results: [
        makeNote({ id: 1, principal_financed: "8000.00" }),
        makeNote({
          id: 2,
          principal_financed: "5000.00",
          current_bucket: "1_15",
          days_past_due: 8,
        }),
      ],
    });
  });

  it("renders the header", async () => {
    await renderPage();
    expect(screen.getByText(/BHPH Portfolio/i)).toBeInTheDocument();
  });

  it("renders the metric cards with formatted values", async () => {
    await renderPage();
    // Cure rate formatted as percent.
    expect(screen.getByText("75.00%")).toBeInTheDocument();
    // APR appears in the metric card AND per-note rows — assert
    // multiple matches to future-proof against layout changes.
    expect(screen.getAllByText("21.90%").length).toBeGreaterThan(0);
    // Days-past-due formatted with unit (metric card only — unique).
    expect(screen.getByText("3.8 days")).toBeInTheDocument();
  });

  it("renders all 7 aging-bucket rows", async () => {
    await renderPage();
    // Bucket labels may appear in multiple places (histogram + notes
    // table when a note is in that bucket); assert at least one match.
    for (const label of [
      /Current/,
      /1–15 days/,
      /16–30 days/,
      /31–60 days/,
      /61–90 days/,
      /Over 90 days/,
      /Charge-off candidate/,
    ]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
  });

  it("renders a row per note", async () => {
    await renderPage();
    expect(screen.getByText("Notes (2)")).toBeInTheDocument();
    const viewLinks = screen.getAllByRole("link", { name: /view/i });
    expect(viewLinks).toHaveLength(2);
  });

  it("shows empty state when no notes", async () => {
    vi.mocked(listBhphNotes).mockResolvedValueOnce({
      count: 0,
      results: [],
    });
    await renderPage();
    expect(
      screen.getByText(/No BHPH notes yet/i),
    ).toBeInTheDocument();
  });

  it("renders null metric values as em-dash", async () => {
    vi.mocked(fetchBhphAnalyticsSummary).mockResolvedValueOnce(
      makeSummary({
        cure_rate: null,
        weighted_average_apr: null,
        weighted_average_days_past_due: null,
        ptp_kept_ratio: null,
      }),
    );
    await renderPage();
    // At least one em-dash rendered for null metrics.
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("shows error state on fetch failure", async () => {
    vi.mocked(fetchBhphAnalyticsSummary).mockRejectedValueOnce(
      new Error("Analytics API failed."),
    );
    render(
      <MemoryRouter initialEntries={["/dealer-ai-bhph/portfolio"]}>
        <Routes>
          <Route
            path="/dealer-ai-bhph/portfolio"
            element={<DealerAiBhphPortfolio />}
          />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Analytics API failed.")).toBeInTheDocument();
    });
  });
});
