// Milestone 24 · Increment 3 (SESSION_183) — ReferralLeadFormExtras tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>(
    "@/lib/api",
  );
  return {
    ...actual,
    fetchAdminLeads: vi.fn(),
  };
});

import { fetchAdminLeads, type AdminLead } from "@/lib/api";
import { ReferralLeadFormExtras } from "./ReferralLeadFormExtras";

function makeLead(overrides: Partial<AdminLead> = {}): AdminLead {
  return {
    id: 1,
    session_id: null,
    name: "Priya Prior-Customer",
    phone: "+15551240100",
    email: "priya@example.com",
    target_monthly_payment: null,
    down_payment: null,
    trade_in: "",
    urgency: "researching",
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

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchAdminLeads).mockResolvedValue({
    count: 3,
    limit: 200,
    results: [
      makeLead({
        id: 1,
        name: "Priya Prior-Customer",
        phone: "+15551240100",
        email: "priya@example.com",
      }),
      makeLead({
        id: 2,
        name: "Sam Referrer",
        phone: "+15551240200",
        email: "sam@example.com",
      }),
      makeLead({
        id: 3,
        name: "Chris Chatter",
        phone: "+15551240300",
        email: "chris@example.com",
      }),
    ],
  });
});

describe("ReferralLeadFormExtras", () => {
  it("fetches tenant-scoped leads on mount with limit=200", async () => {
    render(<ReferralLeadFormExtras value={null} onSelect={vi.fn()} />);
    await waitFor(() => {
      expect(fetchAdminLeads).toHaveBeenCalledWith({ limit: 200 });
    });
  });

  it("shows no matches until the operator types a search string", async () => {
    render(<ReferralLeadFormExtras value={null} onSelect={vi.fn()} />);
    await waitFor(() => {
      expect(fetchAdminLeads).toHaveBeenCalled();
    });
    // No matches list rendered when search is empty.
    expect(
      screen.queryByTestId("referral-lead-form-extras-matches"),
    ).toBeNull();
  });

  it("filters matches by name substring (case-insensitive)", async () => {
    render(<ReferralLeadFormExtras value={null} onSelect={vi.fn()} />);
    await waitFor(() => {
      expect(fetchAdminLeads).toHaveBeenCalled();
    });
    await userEvent.type(
      screen.getByTestId("referral-lead-form-extras-search"),
      "priya",
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("referral-lead-form-extras-match-1"),
      ).toBeInTheDocument();
    });
    // Only the Priya match — Sam and Chris don't contain "priya".
    expect(
      screen.queryByTestId("referral-lead-form-extras-match-2"),
    ).toBeNull();
    expect(
      screen.queryByTestId("referral-lead-form-extras-match-3"),
    ).toBeNull();
  });

  it("filters matches by phone or email substring", async () => {
    render(<ReferralLeadFormExtras value={null} onSelect={vi.fn()} />);
    await waitFor(() => {
      expect(fetchAdminLeads).toHaveBeenCalled();
    });
    await userEvent.type(
      screen.getByTestId("referral-lead-form-extras-search"),
      "sam@",
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("referral-lead-form-extras-match-2"),
      ).toBeInTheDocument();
    });
  });

  it("shows an empty state when no matches", async () => {
    render(<ReferralLeadFormExtras value={null} onSelect={vi.fn()} />);
    await waitFor(() => {
      expect(fetchAdminLeads).toHaveBeenCalled();
    });
    await userEvent.type(
      screen.getByTestId("referral-lead-form-extras-search"),
      "nobody",
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("referral-lead-form-extras-empty"),
      ).toBeInTheDocument();
    });
  });

  it("calls onSelect with the picked lead's id", async () => {
    const onSelect = vi.fn();
    render(<ReferralLeadFormExtras value={null} onSelect={onSelect} />);
    await waitFor(() => {
      expect(fetchAdminLeads).toHaveBeenCalled();
    });
    await userEvent.type(
      screen.getByTestId("referral-lead-form-extras-search"),
      "sam",
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("referral-lead-form-extras-match-2"),
      ).toBeInTheDocument();
    });
    await userEvent.click(
      screen.getByTestId("referral-lead-form-extras-match-2"),
    );
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("renders selected chip when value is set + supports Unselect", async () => {
    const onSelect = vi.fn();
    render(<ReferralLeadFormExtras value={1} onSelect={onSelect} />);
    // Wait for the leads fetch to resolve so the component can
    // look up the selected lead's details.
    await waitFor(() => {
      expect(
        screen.getByTestId("referral-lead-form-extras-selected"),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("referral-lead-form-extras-selected").textContent,
    ).toContain("Priya Prior-Customer");
    await userEvent.click(
      screen.getByTestId("referral-lead-form-extras-clear"),
    );
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("surfaces a load error", async () => {
    vi.mocked(fetchAdminLeads).mockRejectedValue(new Error("Backend down"));
    render(<ReferralLeadFormExtras value={null} onSelect={vi.fn()} />);
    await waitFor(() => {
      expect(
        screen.getByTestId("referral-lead-form-extras-error"),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("referral-lead-form-extras-error").textContent,
    ).toContain("Backend down");
  });
});
