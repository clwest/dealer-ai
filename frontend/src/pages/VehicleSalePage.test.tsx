// Milestone 9 · Increment 5 (SESSION_104) — VehicleSalePage tests.
//
// Covers the three main render states: no Sale (create form), Sale
// present but no Delivery (start-delivery button), Sale + Delivery
// (checklist toggle + verify-insurance).

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock the saleApi module before importing the page component.
vi.mock("@/lib/saleApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/saleApi")>(
    "@/lib/saleApi",
  );
  return {
    ...actual,
    readSale: vi.fn(),
    readDelivery: vi.fn(),
    createSale: vi.fn(),
    createDelivery: vi.fn(),
    updateDelivery: vi.fn(),
  };
});

// Mock the auth context — the page reads hasRole() for write
// affordance gating. Return a full-authority user so buttons render.
vi.mock("@/lib/AuthContext", () => ({
  useAuth: () => ({
    hasRole: () => true,
  }),
}));

import {
  createDelivery,
  createSale,
  readDelivery,
  readSale,
  updateDelivery,
  type Delivery,
  type Sale,
} from "@/lib/saleApi";
import VehicleSalePage from "@/pages/VehicleSalePage";


const DEFAULT_SALE: Sale = {
  id: 1,
  vehicle_stock: "TEST-1",
  buyer_id: null,
  sale_date: "2026-08-01",
  sold_price: "32000.00",
  finance_type: "cash",
  lender_name: "",
  gross_realized: "3500.00",
  created_at: "2026-08-01T10:00:00Z",
  updated_at: "2026-08-01T10:00:00Z",
};

const DEFAULT_DELIVERY: Delivery = {
  id: 7,
  sale_id: 1,
  vehicle_stock: "TEST-1",
  delivery_date: "2026-08-05",
  checklist: {
    detail_booked: false,
    fueled: false,
    temp_tag: false,
    insurance_verified: false,
    customer_walkthrough: false,
  },
  temp_tag_number: "",
  insurance_verified: false,
  insurance_verified_at: null,
  notes: "",
  created_at: "2026-08-02T10:00:00Z",
  updated_at: "2026-08-02T10:00:00Z",
};

async function renderPage() {
  render(
    <MemoryRouter initialEntries={["/dealer-ai-inventory/TEST-1/sale"]}>
      <Routes>
        <Route
          path="/dealer-ai-inventory/:stock/sale"
          element={<VehicleSalePage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(readSale).mockReset();
  vi.mocked(readDelivery).mockReset();
  vi.mocked(createSale).mockReset();
  vi.mocked(createDelivery).mockReset();
  vi.mocked(updateDelivery).mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("VehicleSalePage", () => {
  it("shows loading state initially", async () => {
    vi.mocked(readSale).mockReturnValue(new Promise(() => {}));
    vi.mocked(readDelivery).mockReturnValue(new Promise(() => {}));
    await renderPage();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders the create form when no Sale exists", async () => {
    vi.mocked(readSale).mockResolvedValue(null);
    vi.mocked(readDelivery).mockResolvedValue(null);
    await renderPage();
    await waitFor(() => {
      // "Record sale" appears both as CardTitle and Button label —
      // assert on the button (unambiguous) rather than getByText
      // (which would collapse the two matches into an error).
      expect(
        screen.getByRole("button", { name: /record sale/i }),
      ).toBeInTheDocument();
    });
  });

  it("renders Sale summary + Start-delivery button when Sale but no Delivery", async () => {
    vi.mocked(readSale).mockResolvedValue(DEFAULT_SALE);
    vi.mocked(readDelivery).mockResolvedValue(null);
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("$32,000.00")).toBeInTheDocument();
    });
    expect(screen.getByText("$3,500.00")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /start delivery/i }),
    ).toBeInTheDocument();
  });

  it("renders the delivery checklist when Sale + Delivery both exist", async () => {
    vi.mocked(readSale).mockResolvedValue(DEFAULT_SALE);
    vi.mocked(readDelivery).mockResolvedValue(DEFAULT_DELIVERY);
    await renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("delivery-checklist")).toBeInTheDocument();
    });
    // Five checklist rows, one per M9.2 key.
    expect(screen.getByText("Detail booked")).toBeInTheDocument();
    expect(screen.getByText("Fueled")).toBeInTheDocument();
    expect(screen.getByText("Temp tag issued")).toBeInTheDocument();
    expect(screen.getByText("Insurance verified")).toBeInTheDocument();
    expect(screen.getByText("Customer walkthrough")).toBeInTheDocument();
    // Insurance uses the dedicated verify button.
    expect(
      screen.getByRole("button", { name: /verify insurance/i }),
    ).toBeInTheDocument();
  });

  it("toggles a checklist item on button click", async () => {
    vi.mocked(readSale).mockResolvedValue(DEFAULT_SALE);
    vi.mocked(readDelivery).mockResolvedValue(DEFAULT_DELIVERY);
    vi.mocked(updateDelivery).mockResolvedValue({
      ...DEFAULT_DELIVERY,
      checklist: { ...DEFAULT_DELIVERY.checklist, fueled: true },
    });
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("Fueled")).toBeInTheDocument();
    });
    const fueledRow = screen.getByText("Fueled").closest("li");
    expect(fueledRow).not.toBeNull();
    const fueledButton = fueledRow!.querySelector("button");
    expect(fueledButton).not.toBeNull();
    const user = userEvent.setup();
    await user.click(fueledButton!);
    await waitFor(() => {
      expect(updateDelivery).toHaveBeenCalledWith(
        7,
        expect.objectContaining({
          checklist_key: "fueled",
          checklist_value: true,
        }),
      );
    });
  });

  it("calls verify-insurance with the boolean flag", async () => {
    vi.mocked(readSale).mockResolvedValue(DEFAULT_SALE);
    vi.mocked(readDelivery).mockResolvedValue(DEFAULT_DELIVERY);
    vi.mocked(updateDelivery).mockResolvedValue({
      ...DEFAULT_DELIVERY,
      insurance_verified: true,
      insurance_verified_at: "2026-08-05T10:00:00Z",
      checklist: { ...DEFAULT_DELIVERY.checklist, insurance_verified: true },
    });
    await renderPage();
    const user = userEvent.setup();
    const button = await screen.findByRole("button", {
      name: /verify insurance/i,
    });
    await user.click(button);
    await waitFor(() => {
      expect(updateDelivery).toHaveBeenCalledWith(
        7,
        expect.objectContaining({ verify_insurance: true }),
      );
    });
  });

  it("shows an error message when load fails", async () => {
    vi.mocked(readSale).mockRejectedValue(new Error("boom"));
    vi.mocked(readDelivery).mockRejectedValue(new Error("boom"));
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });
});
