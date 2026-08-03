// Milestone 25 · Increment 2 (SESSION_187) — RecordTestDriveForm tests.
//
// Covers the vehicle picker (suggested + inventory zones), search
// filter, submit path, and error surfaces. The parent modal wiring
// (collapsible + success indicator) is covered by the M25.2
// Playwright journey `lead_to_test_drive.spec.ts`.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/authFetch";
import type {
  AdminVehicleListResponse,
  TestDriveProjection,
} from "@/lib/salesApi";

import { RecordTestDriveForm } from "./RecordTestDriveForm";

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

function makeDrive(
  overrides: Partial<TestDriveProjection> = {},
): TestDriveProjection {
  return {
    id: 1,
    lead_id: 42,
    vehicle_id: 100,
    dealership_id: 1,
    driven_by_user_id: null,
    driven_at: "2026-08-03T00:00:00Z",
    duration_minutes: null,
    route_notes: "",
    customer_reaction: "",
    objections_captured: [],
    next_action: "",
    created_at: "2026-08-03T00:00:00Z",
    updated_at: "2026-08-03T00:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("RecordTestDriveForm", () => {
  it("loads inventory on mount and renders 'All inventory' zone", async () => {
    const loadInventory = vi.fn().mockResolvedValue({
      count: 2,
      results: [
        makeVehicleRow({ id: 100, stock_number: "F150-01" }),
        makeVehicleRow({
          id: 101,
          stock_number: "RANGER-02",
          model: "Ranger",
          display_name: "2024 Ford Ranger XLT",
        }),
      ],
    });
    render(
      <RecordTestDriveForm
        leadId={42}
        onCreated={vi.fn()}
        loadInventory={loadInventory}
      />,
    );
    await waitFor(() => {
      expect(loadInventory).toHaveBeenCalled();
    });
    expect(
      await screen.findByTestId("record-test-drive-inventory-zone"),
    ).toBeVisible();
    expect(screen.getByTestId("record-test-drive-vehicle-100")).toBeVisible();
    expect(screen.getByTestId("record-test-drive-vehicle-101")).toBeVisible();
  });

  it("renders 'Suggested for this lead' zone when interested_vehicles provided", async () => {
    render(
      <RecordTestDriveForm
        leadId={42}
        suggestedVehicles={[
          {
            id: 200,
            stock_number: "BRONCO-99",
            display_name: "2025 Ford Bronco Wildtrak",
            price: "58000.00",
          },
        ]}
        onCreated={vi.fn()}
        loadInventory={vi
          .fn()
          .mockResolvedValue({ count: 0, results: [] })}
      />,
    );
    expect(
      await screen.findByTestId("record-test-drive-suggested-zone"),
    ).toBeVisible();
    expect(screen.getByTestId("record-test-drive-vehicle-200")).toBeVisible();
  });

  it("submit disabled until a vehicle is selected", async () => {
    render(
      <RecordTestDriveForm
        leadId={42}
        onCreated={vi.fn()}
        loadInventory={vi.fn().mockResolvedValue({
          count: 1,
          results: [makeVehicleRow()],
        })}
      />,
    );
    const submit = screen.getByTestId("record-test-drive-submit");
    expect(submit).toBeDisabled();
    await userEvent.click(
      await screen.findByTestId("record-test-drive-vehicle-100"),
    );
    expect(submit).toBeEnabled();
  });

  it("submits with picker + optional fields, invokes onCreated + resets", async () => {
    const submit = vi.fn().mockResolvedValue(makeDrive({ id: 999 }));
    const onCreated = vi.fn();
    render(
      <RecordTestDriveForm
        leadId={42}
        onCreated={onCreated}
        submit={submit}
        loadInventory={vi.fn().mockResolvedValue({
          count: 1,
          results: [makeVehicleRow()],
        })}
      />,
    );
    await userEvent.click(
      await screen.findByTestId("record-test-drive-vehicle-100"),
    );
    await userEvent.type(
      screen.getByTestId("record-test-drive-duration-minutes"),
      "25",
    );
    await userEvent.type(
      screen.getByTestId("record-test-drive-customer-reaction"),
      "positive",
    );
    await userEvent.type(
      screen.getByTestId("record-test-drive-objections"),
      "price too high, want AWD",
    );
    await userEvent.click(screen.getByTestId("record-test-drive-submit"));

    await waitFor(() => {
      expect(submit).toHaveBeenCalledWith({
        lead_id: 42,
        vehicle_id: 100,
        duration_minutes: 25,
        customer_reaction: "positive",
        objections_captured: ["price too high", "want AWD"],
        route_notes: undefined,
        next_action: undefined,
      });
    });
    expect(onCreated).toHaveBeenCalledWith(expect.objectContaining({ id: 999 }));
    // Optional fields cleared after submit; picker also resets.
    expect(
      screen.getByTestId("record-test-drive-customer-reaction"),
    ).toHaveValue("");
    expect(screen.getByTestId("record-test-drive-submit")).toBeDisabled();
  });

  it("surfaces a 404 as a targeted error message", async () => {
    const submit = vi
      .fn()
      .mockRejectedValue(new ApiError(404, "not found"));
    render(
      <RecordTestDriveForm
        leadId={42}
        onCreated={vi.fn()}
        submit={submit}
        loadInventory={vi.fn().mockResolvedValue({
          count: 1,
          results: [makeVehicleRow()],
        })}
      />,
    );
    await userEvent.click(
      await screen.findByTestId("record-test-drive-vehicle-100"),
    );
    await userEvent.click(screen.getByTestId("record-test-drive-submit"));
    const err = await screen.findByTestId("record-test-drive-error");
    expect(err).toHaveTextContent(/lead or vehicle not found/i);
  });

  it("shows an inventory-load error when the endpoint fails", async () => {
    render(
      <RecordTestDriveForm
        leadId={42}
        onCreated={vi.fn()}
        loadInventory={vi.fn().mockRejectedValue(new Error("boom"))}
      />,
    );
    expect(
      await screen.findByTestId("record-test-drive-inventory-error"),
    ).toBeVisible();
  });

  it("search text refetches inventory and filters suggested vehicles", async () => {
    const loadInventory = vi
      .fn()
      .mockResolvedValueOnce({ count: 1, results: [makeVehicleRow()] })
      .mockResolvedValueOnce({
        count: 1,
        results: [
          makeVehicleRow({
            id: 101,
            stock_number: "RANGER-02",
            model: "Ranger",
            display_name: "2024 Ford Ranger XLT",
          }),
        ],
      });
    render(
      <RecordTestDriveForm
        leadId={42}
        suggestedVehicles={[
          {
            id: 200,
            stock_number: "BRONCO-99",
            display_name: "2025 Ford Bronco Wildtrak",
            price: "58000.00",
          },
        ]}
        onCreated={vi.fn()}
        loadInventory={loadInventory}
      />,
    );
    await screen.findByTestId("record-test-drive-vehicle-100");
    await userEvent.type(
      screen.getByTestId("record-test-drive-search"),
      "Ranger",
    );
    await waitFor(() => {
      expect(loadInventory).toHaveBeenLastCalledWith({ search: "Ranger" });
    });
    // Suggested Bronco falls out of the filtered list because
    // "Ranger" does not match its display_name.
    await waitFor(() => {
      expect(
        screen.queryByTestId("record-test-drive-vehicle-200"),
      ).not.toBeInTheDocument();
    });
  });
});
