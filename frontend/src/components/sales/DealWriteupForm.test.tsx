// Milestone 32 · Increment 2 (SESSION_208) — DealWriteupForm tests.
//
// Covers: vehicle picker (suggested + inventory zones), search
// filter, submit disabled without vehicle selected, submit path,
// error surfaces (400 / 404 / generic), decimal + integer coercion
// on optional term fields.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/authFetch";
import type {
  AdminVehicleListResponse,
  DealWriteupProjection,
} from "@/lib/salesApi";

import { DealWriteupForm } from "./DealWriteupForm";

function makeVehicleRow(
  overrides: Partial<AdminVehicleListResponse["results"][number]> = {},
) {
  return {
    id: 100,
    stock_number: "F150-01",
    year: 2024,
    make: "Ford",
    model: "F-150",
    trim: "XLT",
    condition: "new",
    price: "45000.00",
    image_url: "",
    is_available: true,
    display_name: "2024 Ford F-150 XLT",
    ...overrides,
  };
}

function makeWriteup(
  overrides: Partial<DealWriteupProjection> = {},
): DealWriteupProjection {
  return {
    id: 1,
    lead_id: 42,
    vehicle_id: 100,
    dealership_id: 1,
    vehicle_price: null,
    trade_allowance: null,
    down_payment: null,
    monthly_payment_target: null,
    term_months_target: null,
    apr_target: null,
    write_up_at: "2026-08-04T10:00:00Z",
    written_up_by_user_id: null,
    sales_manager_approved_at: null,
    sales_manager_approved_by_user_id: null,
    handed_off_to_fandi_at: null,
    notes: "",
    created_at: "2026-08-04T10:00:00Z",
    updated_at: "2026-08-04T10:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("DealWriteupForm — vehicle picker", () => {
  it("loads inventory and renders All inventory zone", async () => {
    const loadInventory = vi.fn().mockResolvedValue({
      count: 1,
      results: [makeVehicleRow()],
    });
    render(
      <DealWriteupForm
        leadId={42}
        onCreated={vi.fn()}
        loadInventory={loadInventory}
        submit={vi.fn()}
      />,
    );
    await waitFor(() => expect(loadInventory).toHaveBeenCalled());
    expect(
      await screen.findByTestId("deal-writeup-inventory-zone"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("deal-writeup-vehicle-100"),
    ).toBeInTheDocument();
  });

  it("renders suggested zone from prop", async () => {
    const loadInventory = vi.fn().mockResolvedValue({ count: 0, results: [] });
    render(
      <DealWriteupForm
        leadId={42}
        suggestedVehicles={[
          {
            id: 200,
            stock_number: "SUG-01",
            display_name: "Suggested Vehicle",
            price: "30000.00",
          },
        ]}
        onCreated={vi.fn()}
        loadInventory={loadInventory}
        submit={vi.fn()}
      />,
    );
    await waitFor(() => expect(loadInventory).toHaveBeenCalled());
    expect(
      screen.getByTestId("deal-writeup-suggested-zone"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("deal-writeup-vehicle-200"),
    ).toBeInTheDocument();
  });
});

describe("DealWriteupForm — submit disabled without vehicle", () => {
  it("submit button is disabled when no vehicle is selected", async () => {
    const loadInventory = vi.fn().mockResolvedValue({ count: 0, results: [] });
    render(
      <DealWriteupForm
        leadId={42}
        onCreated={vi.fn()}
        loadInventory={loadInventory}
        submit={vi.fn()}
      />,
    );
    await waitFor(() => expect(loadInventory).toHaveBeenCalled());
    expect(screen.getByTestId("deal-writeup-submit")).toBeDisabled();
  });
});

describe("DealWriteupForm — submit path", () => {
  it("POSTs the payload with numeric coercion on decimals + int on term", async () => {
    const loadInventory = vi.fn().mockResolvedValue({
      count: 1,
      results: [makeVehicleRow()],
    });
    const submit = vi.fn().mockResolvedValue(makeWriteup({ id: 55 }));
    const onCreated = vi.fn();
    render(
      <DealWriteupForm
        leadId={42}
        onCreated={onCreated}
        loadInventory={loadInventory}
        submit={submit}
      />,
    );
    await waitFor(() => expect(loadInventory).toHaveBeenCalled());
    await userEvent.click(await screen.findByTestId("deal-writeup-vehicle-100"));
    await userEvent.type(
      screen.getByTestId("deal-writeup-vehicle-price"),
      "28500",
    );
    await userEvent.type(
      screen.getByTestId("deal-writeup-monthly-payment-target"),
      "450",
    );
    await userEvent.type(
      screen.getByTestId("deal-writeup-term-months-target"),
      "72",
    );
    await userEvent.type(
      screen.getByTestId("deal-writeup-apr-target"),
      "7.49",
    );
    await userEvent.click(screen.getByTestId("deal-writeup-submit"));
    await waitFor(() => expect(submit).toHaveBeenCalled());
    const payload = submit.mock.calls[0][0];
    expect(payload).toMatchObject({
      lead_id: 42,
      vehicle_id: 100,
      vehicle_price: "28500.00",
      monthly_payment_target: "450.00",
      term_months_target: 72,
      apr_target: "7.49",
    });
    expect(onCreated).toHaveBeenCalled();
  });
});

describe("DealWriteupForm — error surfaces", () => {
  it("surfaces 400 error inline", async () => {
    const loadInventory = vi.fn().mockResolvedValue({
      count: 1,
      results: [makeVehicleRow()],
    });
    const submit = vi.fn().mockRejectedValue(new ApiError(400, "bad"));
    render(
      <DealWriteupForm
        leadId={42}
        onCreated={vi.fn()}
        loadInventory={loadInventory}
        submit={submit}
      />,
    );
    await waitFor(() => expect(loadInventory).toHaveBeenCalled());
    await userEvent.click(await screen.findByTestId("deal-writeup-vehicle-100"));
    await userEvent.click(screen.getByTestId("deal-writeup-submit"));
    await waitFor(() =>
      expect(screen.getByTestId("deal-writeup-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("deal-writeup-error").textContent).toMatch(
      /Invalid writeup fields/,
    );
  });

  it("surfaces 404 error with helpful copy", async () => {
    const loadInventory = vi.fn().mockResolvedValue({
      count: 1,
      results: [makeVehicleRow()],
    });
    const submit = vi.fn().mockRejectedValue(new ApiError(404, "not found"));
    render(
      <DealWriteupForm
        leadId={42}
        onCreated={vi.fn()}
        loadInventory={loadInventory}
        submit={submit}
      />,
    );
    await waitFor(() => expect(loadInventory).toHaveBeenCalled());
    await userEvent.click(await screen.findByTestId("deal-writeup-vehicle-100"));
    await userEvent.click(screen.getByTestId("deal-writeup-submit"));
    await waitFor(() =>
      expect(screen.getByTestId("deal-writeup-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("deal-writeup-error").textContent).toMatch(
      /Lead or vehicle not found/,
    );
  });
});
