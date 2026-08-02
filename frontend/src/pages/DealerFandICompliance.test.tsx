// Milestone 10 · Increment 7 (SESSION_112) — DealerFandICompliance tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/fAndIApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/fAndIApi")>(
    "@/lib/fAndIApi",
  );
  return {
    ...actual,
    fetchDealJacket: vi.fn(),
    createCompliance: vi.fn(),
    updateCompliance: vi.fn(),
  };
});

vi.mock("@/lib/AuthContext", () => ({
  useAuth: () => ({
    hasRole: () => true,
  }),
}));

import {
  createCompliance,
  fetchDealJacket,
  updateCompliance,
  type DealJacket,
} from "@/lib/fAndIApi";
import DealerFandICompliance from "@/pages/DealerFandICompliance";


const CONTRACT_ID = 42;

const BASE_JACKET: DealJacket = {
  contract: {
    id: CONTRACT_ID,
    contract_type: "risc",
    state: "signed",
    signed_at: "2026-08-15T10:00:00Z",
    voided_at: null,
    voided_reason: "",
  },
  compliance: null,
  funding: {
    id: 7,
    state: "funded",
    funded_at: "2026-08-20T14:00:00Z",
    funding_amount: "24500.00",
  },
  stipulations: [],
  back_end_products: [],
  chargebacks: [],
};

const POPULATED_JACKET: DealJacket = {
  ...BASE_JACKET,
  compliance: {
    id: 3,
    reg_z_disclosed_at: "2026-08-15T11:00:00Z",
    ofac_checked_at: null,
    ofac_hit: false,
    red_flags_reviewed_at: null,
    red_flags_notes: "",
    privacy_notice_delivered_at: null,
    safeguards_audit_at: null,
    adverse_action_sent_at: null,
    adverse_action_reason: "",
    retention_expires_at: "2033-08-15T11:00:00Z",
    deal_jacket_url: "",
    notes: "",
  },
  stipulations: [
    {
      id: 1,
      lender_submission_id: 10,
      stip_type: "proof_of_income",
      state: "cleared",
      cleared_at: "2026-08-18T09:00:00Z",
      documented_by_id: 5,
      evidence_url: "https://drive.example.com/paystub.pdf",
      notes: "",
    },
  ],
  chargebacks: [
    {
      id: 1,
      chargeback_type: "first_payment_default",
      chargeback_date: "2026-09-15",
      chargeback_amount: "500.00",
      recorded_by_id: 5,
      bepa_id: null,
    },
  ],
};


async function renderPage() {
  const view = render(
    <MemoryRouter initialEntries={[`/dealer-ai-f-and-i/${CONTRACT_ID}/compliance`]}>
      <Routes>
        <Route
          path="/dealer-ai-f-and-i/:contract_id/compliance"
          element={<DealerFandICompliance />}
        />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => {
    expect(fetchDealJacket).toHaveBeenCalled();
  });
  return view;
}


describe("DealerFandICompliance", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows 'Compliance record not started' when compliance is null", async () => {
    vi.mocked(fetchDealJacket).mockResolvedValue(BASE_JACKET);
    await renderPage();
    await waitFor(() => {
      expect(
        screen.getByText(/compliance record not started/i),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: /start compliance record/i }),
    ).toBeInTheDocument();
  });

  it("creates a compliance record and refetches on button click", async () => {
    vi.mocked(fetchDealJacket)
      .mockResolvedValueOnce(BASE_JACKET)
      .mockResolvedValueOnce(POPULATED_JACKET);
    vi.mocked(createCompliance).mockResolvedValue(
      POPULATED_JACKET.compliance!,
    );
    await renderPage();
    const user = userEvent.setup();
    await user.click(
      await screen.findByRole("button", { name: /start compliance record/i }),
    );
    await waitFor(() => {
      expect(createCompliance).toHaveBeenCalledWith({
        contract_id: CONTRACT_ID,
      });
    });
    // fetchDealJacket called again after create.
    await waitFor(() => {
      expect(fetchDealJacket).toHaveBeenCalledTimes(2);
    });
  });

  it("renders the seven compliance-concern rows when compliance exists", async () => {
    vi.mocked(fetchDealJacket).mockResolvedValue(POPULATED_JACKET);
    await renderPage();
    await waitFor(() => {
      expect(
        screen.getByText(/reg z disclosures reviewed/i),
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/ofac screen completed/i)).toBeInTheDocument();
    expect(screen.getByText(/red flags reviewed/i)).toBeInTheDocument();
    expect(screen.getByText(/privacy notice delivered/i)).toBeInTheDocument();
    expect(screen.getByText(/safeguards audit/i)).toBeInTheDocument();
    expect(
      screen.getByText(/adverse action notice sent/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/retention window/i)).toBeInTheDocument();
  });

  it("marks OFAC checked when the OFAC row action is clicked", async () => {
    vi.mocked(fetchDealJacket)
      .mockResolvedValueOnce(POPULATED_JACKET)
      .mockResolvedValueOnce(POPULATED_JACKET);
    vi.mocked(updateCompliance).mockResolvedValue(
      POPULATED_JACKET.compliance!,
    );
    await renderPage();
    const user = userEvent.setup();
    // Row order in CONCERNS: reg_z, ofac, red_flags, privacy,
    // safeguards, adverse_action. The OFAC row shows "Mark now"
    // (ofac_checked_at is null in POPULATED_JACKET). Find by row.
    const ofacRow = screen.getByText(/ofac screen completed/i).closest("tr");
    expect(ofacRow).not.toBeNull();
    const markButton = ofacRow!.querySelector("button");
    expect(markButton).not.toBeNull();
    await user.click(markButton!);
    await waitFor(() => {
      expect(updateCompliance).toHaveBeenCalledWith(
        POPULATED_JACKET.compliance!.id,
        expect.objectContaining({ ofac_checked_at: expect.any(String) }),
      );
    });
  });

  it("shows the reg-z timestamp when populated", async () => {
    vi.mocked(fetchDealJacket).mockResolvedValue(POPULATED_JACKET);
    await renderPage();
    await waitFor(() => {
      // The reg_z_disclosed_at value is present. Row layout renders
      // the "Re-mark" button when a timestamp exists.
      expect(screen.getAllByText(/re-mark/i).length).toBeGreaterThan(0);
    });
  });

  it("shows related stipulations", async () => {
    vi.mocked(fetchDealJacket).mockResolvedValue(POPULATED_JACKET);
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("proof_of_income")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: /evidence/i })).toHaveAttribute(
      "href",
      "https://drive.example.com/paystub.pdf",
    );
  });

  it("shows related chargebacks", async () => {
    vi.mocked(fetchDealJacket).mockResolvedValue(POPULATED_JACKET);
    await renderPage();
    await waitFor(() => {
      expect(
        screen.getByText("first_payment_default"),
      ).toBeInTheDocument();
    });
  });

  it("shows funding state and amount", async () => {
    vi.mocked(fetchDealJacket).mockResolvedValue(POPULATED_JACKET);
    await renderPage();
    // The funding section renders "State: funded · $24500.00" —
    // the amount is the unambiguous marker.
    await waitFor(() => {
      expect(screen.getByText(/24500\.00/)).toBeInTheDocument();
    });
  });

  it("shows an error state when the API fails", async () => {
    vi.mocked(fetchDealJacket).mockRejectedValue(new Error("Boom"));
    await renderPage();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Boom");
    });
  });
});
