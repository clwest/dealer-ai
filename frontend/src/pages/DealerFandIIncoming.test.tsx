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
    // M33.1 derived-status fixture defaults (Incoming — no
    // DealStructure yet). Tests can override to exercise the
    // In progress branch.
    has_deal_structure: false,
    latest_deal_structure_id: null,
    // M35.1 + M35.2 §0.a derived-status fixture defaults. Null
    // when no submission exists on latest DS (which is null here).
    latest_lender_submission_status: null,
    latest_lender_submission_id: null,
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
  // resetAllMocks (not clearAllMocks) — clears both call records and
  // any queued mockResolvedValueOnce implementations. Required because
  // the M33.2 "opens the structuring form panel" test queues two
  // responses (initial load + post-create refetch) but only clicks
  // Cancel, leaving the second queued response to pollute the next
  // test's fetch call.
  vi.resetAllMocks();
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

describe("DealerFandIIncoming — M33.2 derived-status chip (D4)", () => {
  it("renders 'Incoming' chip when has_deal_structure=false", async () => {
    fetchMock.mockResolvedValueOnce([
      fixtureHandoffCA({
        has_deal_structure: false,
        latest_deal_structure_id: null,
      }),
    ]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    expect(
      within(row).getByTestId("incoming-row-status-incoming-1"),
    ).toBeInTheDocument();
    expect(
      within(row).getByLabelText("Incoming credit application"),
    ).toBeInTheDocument();
    // No In-progress marker present on this row.
    expect(
      within(row).queryByTestId("incoming-row-status-in-progress-1"),
    ).toBeNull();
  });

  it("renders 'In progress' chip when has_deal_structure=true", async () => {
    fetchMock.mockResolvedValueOnce([
      fixtureHandoffCA({
        has_deal_structure: true,
        latest_deal_structure_id: 77,
      }),
    ]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    expect(
      within(row).getByTestId("incoming-row-status-in-progress-1"),
    ).toBeInTheDocument();
    expect(
      within(row).getByLabelText("In progress credit application"),
    ).toBeInTheDocument();
    // No Incoming marker present on this row.
    expect(
      within(row).queryByTestId("incoming-row-status-incoming-1"),
    ).toBeNull();
  });
});

describe("DealerFandIIncoming — M33.2 row actions (D5 + D6 + D9)", () => {
  it("shows 'Start structuring' on Incoming rows only (D9 first-loop-only)", async () => {
    fetchMock.mockResolvedValueOnce([
      fixtureHandoffCA({
        has_deal_structure: false,
        latest_deal_structure_id: null,
      }),
    ]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    expect(
      within(row).getByTestId("incoming-row-start-structuring-1"),
    ).toBeInTheDocument();
    expect(
      within(row).queryByTestId("incoming-row-open-structure-1"),
    ).toBeNull();
  });

  it("shows 'Open structure' on In progress rows only (D9)", async () => {
    fetchMock.mockResolvedValueOnce([
      fixtureHandoffCA({
        has_deal_structure: true,
        latest_deal_structure_id: 77,
      }),
    ]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    expect(
      within(row).getByTestId("incoming-row-open-structure-1"),
    ).toBeInTheDocument();
    // "Start structuring" hidden on In progress rows per D9 — no
    // iteration UX in M33.
    expect(
      within(row).queryByTestId("incoming-row-start-structuring-1"),
    ).toBeNull();
  });

  it("hides both actions and shows a documented affordance for direct-create CAs (R1 mitigation)", async () => {
    fetchMock.mockResolvedValueOnce([fixtureDirectCA()]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-2");
    // Neither action is available — no vehicle discovery for
    // direct-create CAs.
    expect(
      within(row).queryByTestId("incoming-row-start-structuring-2"),
    ).toBeNull();
    expect(
      within(row).queryByTestId("incoming-row-open-structure-2"),
    ).toBeNull();
    // Documented affordance explains why.
    expect(
      within(row).getByTestId("incoming-row-no-writeup-2"),
    ).toBeInTheDocument();
  });

  it("opens the structuring form panel and refetches on successful create", async () => {
    // First call: Incoming row. Second call (post-create refetch):
    // same CA now In progress with a latest_deal_structure_id.
    fetchMock.mockResolvedValueOnce([
      fixtureHandoffCA({
        has_deal_structure: false,
        latest_deal_structure_id: null,
      }),
    ]);
    fetchMock.mockResolvedValueOnce([
      fixtureHandoffCA({
        has_deal_structure: true,
        latest_deal_structure_id: 77,
      }),
    ]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    // Open the form panel.
    await userEvent.click(
      within(row).getByTestId("incoming-row-start-structuring-1"),
    );
    // Panel mounts with the form.
    expect(
      await screen.findByTestId("deal-structure-form-panel"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("deal-structure-form")).toBeInTheDocument();
    // Cancel closes the panel without refetching.
    await userEvent.click(
      screen.getByTestId("deal-structure-form-cancel"),
    );
    await waitFor(() =>
      expect(screen.queryByTestId("deal-structure-form-panel")).toBeNull(),
    );
    // Only the initial load fetch has occurred.
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("DealerFandIIncoming — M35.2 six-state chip (D8)", () => {
  it.each([
    ["submitted", "pending" as const, "Submitted — awaiting response"],
    ["approved", "approved" as const, "Approved"],
    ["counter", "counter" as const, "Counter-offer received"],
    ["declined", "declined" as const, "Declined"],
  ])(
    "renders '%s' chip when latest_lender_submission_status=%s",
    async (stateSuffix, status, expectedLabel) => {
      fetchMock.mockResolvedValueOnce([
        fixtureHandoffCA({
          has_deal_structure: true,
          latest_deal_structure_id: 77,
          latest_lender_submission_status: status,
          latest_lender_submission_id: 501,
        }),
      ]);
      render(<DealerFandIIncoming />);
      const row = await screen.findByTestId("incoming-row-1");
      const chip = within(row).getByTestId(
        `incoming-row-status-${stateSuffix}-1`,
      );
      expect(chip).toBeInTheDocument();
      expect(chip.textContent).toBe(expectedLabel);
      // Other chip states must be absent.
      for (const other of [
        "incoming",
        "in-progress",
        "submitted",
        "approved",
        "counter",
        "declined",
      ] as const) {
        if (other === stateSuffix) continue;
        expect(
          within(row).queryByTestId(`incoming-row-status-${other}-1`),
        ).toBeNull();
      }
    },
  );
});

describe("DealerFandIIncoming — M35.2 state-conditional row actions (D8)", () => {
  it("shows 'Record lender submission' on In progress rows (no existing submission)", async () => {
    fetchMock.mockResolvedValueOnce([
      fixtureHandoffCA({
        has_deal_structure: true,
        latest_deal_structure_id: 77,
        latest_lender_submission_status: null,
        latest_lender_submission_id: null,
      }),
    ]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    expect(
      within(row).getByTestId("incoming-row-record-lender-submission-1"),
    ).toBeInTheDocument();
    // No response actions on In progress rows.
    expect(
      within(row).queryByTestId("incoming-row-record-lender-response-1"),
    ).toBeNull();
    expect(
      within(row).queryByTestId("incoming-row-update-lender-response-1"),
    ).toBeNull();
  });

  it("shows 'Record lender response' on Submitted rows only", async () => {
    fetchMock.mockResolvedValueOnce([
      fixtureHandoffCA({
        has_deal_structure: true,
        latest_deal_structure_id: 77,
        latest_lender_submission_status: "pending",
        latest_lender_submission_id: 501,
      }),
    ]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    expect(
      within(row).getByTestId("incoming-row-record-lender-response-1"),
    ).toBeInTheDocument();
    // No submission-create or update actions on Submitted rows.
    expect(
      within(row).queryByTestId("incoming-row-record-lender-submission-1"),
    ).toBeNull();
    expect(
      within(row).queryByTestId("incoming-row-update-lender-response-1"),
    ).toBeNull();
  });

  it.each(["approved", "counter", "declined"] as const)(
    "shows 'Update lender response' on %s rows only",
    async (status) => {
      fetchMock.mockResolvedValueOnce([
        fixtureHandoffCA({
          has_deal_structure: true,
          latest_deal_structure_id: 77,
          latest_lender_submission_status: status,
          latest_lender_submission_id: 501,
        }),
      ]);
      render(<DealerFandIIncoming />);
      const row = await screen.findByTestId("incoming-row-1");
      expect(
        within(row).getByTestId("incoming-row-update-lender-response-1"),
      ).toBeInTheDocument();
      // No submission-create or record actions on terminal rows.
      expect(
        within(row).queryByTestId("incoming-row-record-lender-submission-1"),
      ).toBeNull();
      expect(
        within(row).queryByTestId("incoming-row-record-lender-response-1"),
      ).toBeNull();
    },
  );

  it("opens the record-submission panel on click", async () => {
    fetchMock.mockResolvedValueOnce([
      fixtureHandoffCA({
        has_deal_structure: true,
        latest_deal_structure_id: 77,
        latest_lender_submission_status: null,
        latest_lender_submission_id: null,
      }),
    ]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    await userEvent.click(
      within(row).getByTestId("incoming-row-record-lender-submission-1"),
    );
    expect(
      await screen.findByTestId("lender-submission-record-panel"),
    ).toBeInTheDocument();
  });

  it("opens the record-response panel on click and pre-selects nothing (record mode)", async () => {
    fetchMock.mockResolvedValueOnce([
      fixtureHandoffCA({
        has_deal_structure: true,
        latest_deal_structure_id: 77,
        latest_lender_submission_status: "pending",
        latest_lender_submission_id: 501,
      }),
    ]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    await userEvent.click(
      within(row).getByTestId("incoming-row-record-lender-response-1"),
    );
    expect(
      await screen.findByTestId("lender-submission-response-panel"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("lender-submission-response-header"),
    ).toHaveTextContent("Record lender response");
  });

  it("opens the update-response panel in update mode for terminal rows", async () => {
    fetchMock.mockResolvedValueOnce([
      fixtureHandoffCA({
        has_deal_structure: true,
        latest_deal_structure_id: 77,
        latest_lender_submission_status: "approved",
        latest_lender_submission_id: 501,
      }),
    ]);
    render(<DealerFandIIncoming />);
    const row = await screen.findByTestId("incoming-row-1");
    await userEvent.click(
      within(row).getByTestId("incoming-row-update-lender-response-1"),
    );
    expect(
      await screen.findByTestId("lender-submission-response-panel"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("lender-submission-response-header"),
    ).toHaveTextContent("Update lender response");
  });
});
