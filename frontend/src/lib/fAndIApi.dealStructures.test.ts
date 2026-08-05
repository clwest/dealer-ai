// Milestone 33 · Increment 2 (SESSION_212) — DealStructure API
// wrapper tests.
//
// Guards URL shape (canonical path GET /admin/deal-structures/<int:pk>/
// per D2) and payload passthrough for the M10.2 create endpoint.

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/authFetch", async () => {
  const actual = await vi.importActual<typeof import("@/lib/authFetch")>(
    "@/lib/authFetch",
  );
  return {
    ...actual,
    authGetJSON: vi.fn(),
    authPostJSON: vi.fn(),
  };
});

import { authGetJSON, authPostJSON } from "@/lib/authFetch";
import {
  createDealStructure,
  getDealStructure,
  type CreateDealStructureRequest,
  type DealStructureProjection,
} from "@/lib/fAndIApi";

const authGetJSONMock = vi.mocked(authGetJSON);
const authPostJSONMock = vi.mocked(authPostJSON);

function fixtureDeal(): DealStructureProjection {
  return {
    id: 77,
    credit_application_id: 42,
    vehicle_stock: "FANDI-STRUCT-1",
    sale_price: "38750.00",
    down_payment: "2500.00",
    trade_allowance: "5250.00",
    trade_payoff: "0.00",
    taxes: "2800.00",
    fees: "699.00",
    amount_financed: "34499.00",
    apr: "7.4900",
    term_months: 66,
    monthly_payment: "600.00",
    back_end_products: [],
    ltv_pct: "89.03",
    pti_pct: "12.00",
    dti_pct: "30.00",
    created_at: "2026-08-04T18:00:00Z",
    updated_at: "2026-08-04T18:00:00Z",
  };
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("getDealStructure", () => {
  it("GETs the canonical path /admin/deal-structures/<id>/", async () => {
    authGetJSONMock.mockResolvedValueOnce({ deal_structure: fixtureDeal() });
    await getDealStructure(77);
    expect(authGetJSONMock).toHaveBeenCalledWith(
      "/admin/deal-structures/77/",
    );
  });

  it("unwraps the { deal_structure } envelope", async () => {
    authGetJSONMock.mockResolvedValueOnce({ deal_structure: fixtureDeal() });
    const row = await getDealStructure(77);
    expect(row.id).toBe(77);
    expect(row.vehicle_stock).toBe("FANDI-STRUCT-1");
    expect(row.ltv_pct).toBe("89.03");
  });
});

describe("createDealStructure", () => {
  it("POSTs to /admin/deal-structures/ with the full payload", async () => {
    authPostJSONMock.mockResolvedValueOnce({
      deal_structure: fixtureDeal(),
    });
    const payload: CreateDealStructureRequest = {
      credit_application_id: 42,
      vehicle_stock: "FANDI-STRUCT-1",
      sale_price: "38750.00",
      amount_financed: "34499.00",
      apr: "7.4900",
      term_months: 66,
      monthly_payment: "600.00",
      down_payment: "2500.00",
      trade_allowance: "5250.00",
      trade_payoff: "0.00",
      taxes: "2800.00",
      fees: "699.00",
    };
    await createDealStructure(payload);
    expect(authPostJSONMock).toHaveBeenCalledWith(
      "/admin/deal-structures/",
      payload,
    );
  });

  it("returns the created structure with server-computed ratios", async () => {
    authPostJSONMock.mockResolvedValueOnce({
      deal_structure: fixtureDeal(),
    });
    const created = await createDealStructure({
      credit_application_id: 42,
      vehicle_stock: "FANDI-STRUCT-1",
      sale_price: "38750.00",
      amount_financed: "34499.00",
      apr: "7.4900",
      term_months: 66,
      monthly_payment: "600.00",
      taxes: "2800.00",
      fees: "699.00",
      trade_payoff: "0.00",
    });
    // Ratios are server-computed; wrapper does not compute or
    // validate them.
    expect(created.ltv_pct).toBe("89.03");
    expect(created.pti_pct).toBe("12.00");
    expect(created.dti_pct).toBe("30.00");
  });
});
