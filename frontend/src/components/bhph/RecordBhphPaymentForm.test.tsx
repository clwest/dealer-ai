// Milestone 23 · Increment 3 (SESSION_178) — RecordBhphPaymentForm tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/bhphApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/bhphApi")>(
    "@/lib/bhphApi",
  );
  return {
    ...actual,
    createBhphPayment: vi.fn(),
  };
});

import { ApiError } from "@/lib/authFetch";
import {
  createBhphPayment,
  type BhphPaymentProjection,
} from "@/lib/bhphApi";
import { RecordBhphPaymentForm } from "./RecordBhphPaymentForm";

function makePayment(
  overrides: Partial<BhphPaymentProjection> = {},
): BhphPaymentProjection {
  return {
    id: 1,
    note_id: 100,
    dealership_id: 1,
    paid_at: "2026-08-03T14:00:00Z",
    amount: "150.00",
    method: "cash",
    applied_to_fees: "0.00",
    applied_to_interest: "10.00",
    applied_to_principal: "140.00",
    created_at: "2026-08-03T00:00:00Z",
    updated_at: "2026-08-03T00:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("RecordBhphPaymentForm", () => {
  it("submits with the entered fields and calls onRecorded", async () => {
    vi.mocked(createBhphPayment).mockResolvedValue({
      bhph_payment: makePayment({ id: 42, amount: "200.00" }),
    });
    const onRecorded = vi.fn();
    render(<RecordBhphPaymentForm notePk={100} onRecorded={onRecorded} />);

    await userEvent.type(
      screen.getByTestId("record-bhph-payment-amount"),
      "200",
    );
    await userEvent.selectOptions(
      screen.getByTestId("record-bhph-payment-method"),
      "check",
    );
    await userEvent.click(screen.getByTestId("record-bhph-payment-submit"));

    await waitFor(() => {
      expect(createBhphPayment).toHaveBeenCalledWith(
        100,
        expect.objectContaining({
          amount: "200",
          method: "check",
        }),
      );
    });
    expect(onRecorded).toHaveBeenCalledWith(
      expect.objectContaining({ id: 42 }),
    );
  });

  it("blocks submit when amount is zero", async () => {
    const onRecorded = vi.fn();
    render(<RecordBhphPaymentForm notePk={100} onRecorded={onRecorded} />);

    await userEvent.type(
      screen.getByTestId("record-bhph-payment-amount"),
      "0",
    );
    await userEvent.click(screen.getByTestId("record-bhph-payment-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("record-bhph-payment-error")).toBeTruthy();
    });
    expect(createBhphPayment).not.toHaveBeenCalled();
    expect(onRecorded).not.toHaveBeenCalled();
  });

  it("blocks submit when amount is missing", async () => {
    const onRecorded = vi.fn();
    render(<RecordBhphPaymentForm notePk={100} onRecorded={onRecorded} />);

    await userEvent.click(screen.getByTestId("record-bhph-payment-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("record-bhph-payment-error")).toBeTruthy();
    });
    expect(createBhphPayment).not.toHaveBeenCalled();
  });

  it("surfaces a backend 400 as a human-readable error", async () => {
    vi.mocked(createBhphPayment).mockRejectedValue(
      new ApiError(400, "invalid"),
    );
    const onRecorded = vi.fn();
    render(<RecordBhphPaymentForm notePk={100} onRecorded={onRecorded} />);

    await userEvent.type(
      screen.getByTestId("record-bhph-payment-amount"),
      "150",
    );
    await userEvent.click(screen.getByTestId("record-bhph-payment-submit"));

    await waitFor(() => {
      expect(
        screen.getByTestId("record-bhph-payment-error").textContent,
      ).toContain("Invalid payment");
    });
    expect(onRecorded).not.toHaveBeenCalled();
  });

  it("surfaces a backend 404 as a note-not-found message", async () => {
    vi.mocked(createBhphPayment).mockRejectedValue(
      new ApiError(404, "not found"),
    );
    const onRecorded = vi.fn();
    render(<RecordBhphPaymentForm notePk={999} onRecorded={onRecorded} />);

    await userEvent.type(
      screen.getByTestId("record-bhph-payment-amount"),
      "150",
    );
    await userEvent.click(screen.getByTestId("record-bhph-payment-submit"));

    await waitFor(() => {
      expect(
        screen.getByTestId("record-bhph-payment-error").textContent,
      ).toContain("Note not found");
    });
  });

  it("resets fields after successful submit", async () => {
    vi.mocked(createBhphPayment).mockResolvedValue({
      bhph_payment: makePayment({ id: 1 }),
    });
    render(<RecordBhphPaymentForm notePk={100} onRecorded={vi.fn()} />);

    const amountInput = screen.getByTestId(
      "record-bhph-payment-amount",
    ) as HTMLInputElement;
    await userEvent.type(amountInput, "150");
    await userEvent.click(screen.getByTestId("record-bhph-payment-submit"));

    await waitFor(() => {
      expect(amountInput.value).toBe("");
    });
  });
});
