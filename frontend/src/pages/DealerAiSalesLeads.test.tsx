// Milestone 11 · Increment 6 (SESSION_119) — DealerAiSalesLeads tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchAdminLeads: vi.fn(),
  };
});

import { fetchAdminLeads, type AdminLead } from "@/lib/api";
import DealerAiSalesLeads from "@/pages/DealerAiSalesLeads";


function makeLead(overrides: Partial<AdminLead> = {}): AdminLead {
  return {
    id: 1,
    session_id: null,
    name: "Wanda Walkup",
    phone: "555-0100",
    email: "",
    target_monthly_payment: null,
    down_payment: null,
    trade_in: "",
    urgency: "this_week",
    credit_range: "",
    interested_vehicles: [],
    conversation_summary: "",
    recommended_next_action: "",
    handed_off: false,
    assigned_to: null,
    assigned_at: null,
    created_at: "2026-08-01T12:00:00Z",
    channel: "walk_in",
    referrer: null,
    ...overrides,
  };
}

async function renderPage() {
  const view = render(
    <MemoryRouter initialEntries={["/dealer-ai-sales/leads"]}>
      <Routes>
        <Route path="/dealer-ai-sales/leads" element={<DealerAiSalesLeads />} />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => {
    expect(fetchAdminLeads).toHaveBeenCalled();
  });
  return view;
}

describe("DealerAiSalesLeads", () => {
  beforeEach(() => {
    vi.mocked(fetchAdminLeads).mockResolvedValue({
      count: 2,
      limit: 100,
      results: [
        makeLead({ id: 1, name: "Wanda Walkup", channel: "walk_in" }),
        makeLead({ id: 2, name: "Pat Phoner", channel: "phone" }),
      ],
    });
  });

  afterEach(() => vi.clearAllMocks());

  it("renders every lead row with its channel", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("Wanda Walkup")).toBeInTheDocument();
    });
    expect(screen.getByText("Pat Phoner")).toBeInTheDocument();
    expect(screen.getByText("walk_in")).toBeInTheDocument();
    expect(screen.getByText("phone")).toBeInTheDocument();
  });

  it("refetches with a channel filter on change", async () => {
    await renderPage();
    await waitFor(() => {
      expect(fetchAdminLeads).toHaveBeenCalledTimes(1);
    });
    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByLabelText(/channel filter/i),
      "walk_in",
    );
    await waitFor(() => {
      expect(fetchAdminLeads).toHaveBeenCalledTimes(2);
    });
    expect(fetchAdminLeads).toHaveBeenLastCalledWith({
      limit: 100,
      ordering: "urgency",
      channel: ["walk_in"],
    });
  });

  it("shows an empty state when the filter returns nothing", async () => {
    vi.mocked(fetchAdminLeads).mockResolvedValue({
      count: 0,
      limit: 100,
      results: [],
    });
    await renderPage();
    await waitFor(() => {
      expect(
        screen.getByText(/no leads match the current filter/i),
      ).toBeInTheDocument();
    });
  });

  it("surfaces the error message when the API fails", async () => {
    vi.mocked(fetchAdminLeads).mockRejectedValue(new Error("Backend down"));
    await renderPage();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Backend down");
    });
  });
});
