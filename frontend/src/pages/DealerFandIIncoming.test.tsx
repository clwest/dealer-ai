// Milestone 32 · Increment 3 (SESSION_209) — DealerFandIIncoming page tests.
//
// Covers: page renders happy path, filter param passthrough,
// empty state, loading state, forbidden (403) state, inline field
// rendering per D8-revised (lead/vehicle/four-square/notes/attribution),
// non-navigational-row assertions (no <a>, no click handler on row).

import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/authFetch";
import type { CreditApplicationProjection } from "@/lib/fAndIApi";

vi.mock("@/lib/fAndIApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/fAndIApi")>(
    "@/lib/fAndIApi",
  );
  return {
    ...actual,
    fetchCreditApplications: vi.fn(),
  };
});

import { fetchCreditApplications } from "@/lib/fAndIApi";
import DealerFandIIncoming from "./DealerFandIIncoming";

const fetchMock = vi.mocked(fetchCreditApplications);

function fixtureHandoffCA(
  overrides: Partial<CreditApplicationProjection> = {},
): CreditApplicationProjection {
  return {
    id: 1,
    lead_id: 100,
    sale_id: null,
    applicant_full_name: "Intake Iris",
    applicant_ssn_last4: "",
    source_format: "tablet",
    status: "received",
    captured_at: "2026-08-04T12:00:00Z",
    retention_expires_at: "2033-08-04T12:00:00Z",
    notes: "Deal write-up #42 handoff:\n- Vehicle price: $42500.00",
    created_at: "2026-08-04T12:00:00Z",
    updated_at: "2026-08-04T12:00:00Z",
    writeup_context: {
      deal_writeup_id: 42,
      written_up_by_user_id: 5,
      sales_manager_approved_by_user_id: 5,
      handed_off_to_fandi_at: "2026-08-04T12:00:00Z",
      lead: {
        id: 100,
        name: "Intake Iris",
        phone: "+15553201501",
        email: "intake-iris@example.com",
      },
      vehicle: {
        id: 200,
        stock_number: "FANDI-INTAKE-1",
        year: 2024,
        make: "Ford",
        model: "F-150",
      },
      terms: {
        vehicle_price: "42500.00",
        trade_allowance: "7500.00",
        down_payment: "3000.00",
        monthly_payment_target: "585.00",
        term_months_target: 60,
        apr_target: "6.99",
      },
    },
    ...overrides,
  };
}

function fixtureDirectCA(
  overrides: Partial<CreditApplicationProjection> = {},
): CreditApplicationProjection {
  return {
    ...fixtureHandoffCA(overrides),
    id: 2,
    applicant_full_name: "Direct Applicant",
    writeup_context: null,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("DealerFandIIncoming — load states", () => {
  it("renders loading state initially", () => {
    fetchMock.mockImplementation(() => new Promise(() => {}));
    render(<DealerFandIIncoming />);
    expect(screen.getByTestId("incoming-loading")).toBeInTheDocument();
  });

  it("renders empty state when no incoming applications", async () => {
    fetchMock.mockResolvedValueOnce([]);
    render(<DealerFandIIncoming />);
    await waitFor(() =>
      expect(screen.getByTestId("incoming-empty")).toBeInTheDocument(),
    );
  });

  it("renders forbidden state on 403", async () => {
    fetchMock.mockRejectedValueOnce(new ApiError(403, "forbidden"));
    render(<DealerFandIIncoming />);
    await waitFor(() =>
      expect(screen.getByTestId("incoming-forbidden")).toBeInTheDocument(),
    );
    expect(
      screen.getByText(
        /Only F&I managers or dealer owners can view incoming applications\./,
      ),
    ).toBeInTheDocument();
  });

  it("renders error state on non-403 failure", async () => {
    fetchMock.mockRejectedValueOnce(new Error("boom"));
    render(<DealerFandIIncoming />);
    await waitFor(() =>
      expect(screen.getByTestId("incoming-error")).toBeInTheDocument(),
    );
  });
});

describe("DealerFandIIncoming — filter passthrough", () => {
  it("defaults to intake=true", async () => {
    fetchMock.mockResolvedValueOnce([]);
    render(<DealerFandIIncoming />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock).toHaveBeenCalledWith({ intake: true });
  });

  it("switches to unfiltered when scope changes to All", async () => {
    fetchMock.mockResolvedValueOnce([]);
    fetchMock.mockResolvedValueOnce([]);
    render(<DealerFandIIncoming />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    await userEvent.selectOptions(
      screen.getByTestId("incoming-intake-filter"),
      "all",
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock).toHaveBeenNthCalledWith(2, {});
  });
});

describe("DealerFandIIncoming — hand-off row rendering (D8-revised inline fields)", () => {
  it("renders lead name + phone + email", async () => {
    fetchMock.mockResolvedValueOnce([fixtureHandoffCA()]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    expect(within(row).getByText("Intake Iris")).toBeInTheDocument();
    expect(within(row).getByText(/\+15553201501/)).toBeInTheDocument();
    expect(within(row).getByText(/intake-iris@example.com/)).toBeInTheDocument();
  });

  it("renders vehicle year + make + model + stock", async () => {
    fetchMock.mockResolvedValueOnce([fixtureHandoffCA()]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    expect(within(row).getByText("2024 Ford F-150")).toBeInTheDocument();
    expect(within(row).getByText(/FANDI-INTAKE-1/)).toBeInTheDocument();
  });

  it("renders four-square terms via TermsCell", async () => {
    fetchMock.mockResolvedValueOnce([fixtureHandoffCA()]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    expect(
      within(row).getByTestId("incoming-terms-summary"),
    ).toBeInTheDocument();
    expect(within(row).getByText("42500.00")).toBeInTheDocument();
    expect(within(row).getByText("585.00")).toBeInTheDocument();
    expect(within(row).getByText("60 mo")).toBeInTheDocument();
    expect(within(row).getByText("6.99%")).toBeInTheDocument();
  });

  it("renders Incoming state badge", async () => {
    fetchMock.mockResolvedValueOnce([fixtureHandoffCA()]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    expect(within(row).getByTestId("incoming-state-1")).toBeInTheDocument();
    expect(within(row).getByText("Incoming")).toBeInTheDocument();
  });

  it("renders CA notes verbatim inside collapsible details", async () => {
    fetchMock.mockResolvedValueOnce([fixtureHandoffCA()]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    // Notes are rendered inside a <details> — expand it to check
    // the content is present in the DOM.
    const notes = within(row).getByTestId("incoming-notes-1");
    expect(notes.textContent).toContain("Deal write-up #42 handoff:");
    expect(notes.textContent).toContain("Vehicle price: $42500.00");
  });

  it("renders written-up-by + approved-by attribution", async () => {
    fetchMock.mockResolvedValueOnce([fixtureHandoffCA()]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    expect(within(row).getByText(/Written up by #5/)).toBeInTheDocument();
    expect(within(row).getByText(/Approved by #5/)).toBeInTheDocument();
  });
});

describe("DealerFandIIncoming — direct-create CA rendering (writeup_context=null)", () => {
  it("renders 'Direct application' placeholder in terms cell", async () => {
    fetchMock.mockResolvedValueOnce([fixtureDirectCA()]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-2");
    expect(within(row).getByTestId("incoming-terms-none")).toBeInTheDocument();
    expect(within(row).getByText("Direct application")).toBeInTheDocument();
  });

  it("falls back to applicant_full_name when no writeup_context lead", async () => {
    fetchMock.mockResolvedValueOnce([fixtureDirectCA()]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-2");
    expect(within(row).getByText("Direct Applicant")).toBeInTheDocument();
  });
});

describe("DealerFandIIncoming — non-navigational rows (D8-revised)", () => {
  it("row is not wrapped in an <a> and has no click handler", async () => {
    fetchMock.mockResolvedValueOnce([fixtureHandoffCA()]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    // No anchor ancestor. F&I role cannot access admin_lead_detail
    // (sales-role-gated per M32 §4.8), so no row-link would work.
    expect(row.closest("a")).toBeNull();
    // Row is a plain <li> — no onClick attribute.
    expect(row.tagName).toBe("LI");
    expect(row.getAttribute("onclick")).toBeNull();
    // No cursor-pointer utility class — visual affordance matches
    // non-clickable behavior.
    expect(row.className).not.toContain("cursor-pointer");
  });
});
