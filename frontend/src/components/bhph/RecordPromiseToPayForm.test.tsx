// Milestone 21 · Increment 2 (SESSION_168) — RecordPromiseToPayForm tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/bhphApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/bhphApi")>(
    "@/lib/bhphApi",
  );
  return {
    ...actual,
    recordPromiseToPay: vi.fn(),
  };
});

import { ApiError } from "@/lib/authFetch";
import {
  recordPromiseToPay,
  type BhphPromiseProjection,
} from "@/lib/bhphApi";
import { RecordPromiseToPayForm } from "./RecordPromiseToPayForm";

function makePromise(
  overrides: Partial<BhphPromiseProjection> = {},
): BhphPromiseProjection {
  return {
    id: 1,
    note_id: 100,
    dealership_id: 1,
    promised_at: "2026-08-10T14:00:00Z",
    promised_amount: "250.00",
    promised_reason: "paycheck",
    actual_payment_id: null,
    state: "promised",
    notes: "",
    created_at: "2026-08-03T00:00:00Z",
    updated_at: "2026-08-03T00:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("RecordPromiseToPayForm", () => {
  it("submits with the entered fields and calls onRecorded", async () => {
    vi.mocked(recordPromiseToPay).mockResolvedValue({
      bhph_promise: makePromise({ id: 42, promised_amount: "300.00" }),
    });
    const onRecorded = vi.fn();
    render(<RecordPromiseToPayForm notePk={100} onRecorded={onRecorded} />);

    await userEvent.clear(screen.getByTestId("record-ptp-amount"));
    await userEvent.type(screen.getByTestId("record-ptp-amount"), "300");
    await userEvent.selectOptions(
      screen.getByTestId("record-ptp-reason"),
      "tax_refund",
    );
    await userEvent.click(screen.getByTestId("record-ptp-submit"));

    await waitFor(() => {
      expect(recordPromiseToPay).toHaveBeenCalledWith(
        100,
        expect.objectContaining({
          promised_amount: "300",
          promised_reason: "tax_refund",
        }),
      );
    });
    expect(onRecorded).toHaveBeenCalledWith(
      expect.objectContaining({ id: 42 }),
    );
  });

  it("blocks submit when amount is zero", async () => {
    const onRecorded = vi.fn();
    render(<RecordPromiseToPayForm notePk={100} onRecorded={onRecorded} />);

    await userEvent.clear(screen.getByTestId("record-ptp-amount"));
    await userEvent.type(screen.getByTestId("record-ptp-amount"), "0");
    await userEvent.click(screen.getByTestId("record-ptp-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("record-ptp-error")).toBeTruthy();
    });
    expect(recordPromiseToPay).not.toHaveBeenCalled();
    expect(onRecorded).not.toHaveBeenCalled();
  });

  it("surfaces a backend 400 as a human-readable error", async () => {
    vi.mocked(recordPromiseToPay).mockRejectedValue(
      new ApiError(400, "invalid"),
    );
    const onRecorded = vi.fn();
    render(<RecordPromiseToPayForm notePk={100} onRecorded={onRecorded} />);

    await userEvent.clear(screen.getByTestId("record-ptp-amount"));
    await userEvent.type(screen.getByTestId("record-ptp-amount"), "50");
    await userEvent.click(screen.getByTestId("record-ptp-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("record-ptp-error").textContent).toMatch(
        /invalid/i,
      );
    });
    expect(onRecorded).not.toHaveBeenCalled();
  });
});
