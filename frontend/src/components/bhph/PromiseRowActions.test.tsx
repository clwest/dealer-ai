// Milestone 21 · Increment 2 (SESSION_168) — PromiseRowActions tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/bhphApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/bhphApi")>(
    "@/lib/bhphApi",
  );
  return {
    ...actual,
    listBhphPayments: vi.fn(),
    markPromiseKept: vi.fn(),
    markPromiseBroken: vi.fn(),
  };
});

import { ApiError } from "@/lib/authFetch";
import {
  listBhphPayments,
  markPromiseBroken,
  markPromiseKept,
  type BhphPaymentProjection,
  type BhphPromiseProjection,
} from "@/lib/bhphApi";
import {
  MarkBrokenPromiseButton,
  MarkKeptPromiseButton,
} from "./PromiseRowActions";

function makePromise(
  overrides: Partial<BhphPromiseProjection> = {},
): BhphPromiseProjection {
  return {
    id: 5,
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

function makePayment(
  overrides: Partial<BhphPaymentProjection> = {},
): BhphPaymentProjection {
  return {
    id: 900,
    note_id: 100,
    dealership_id: 1,
    paid_at: "2026-08-10T09:00:00Z",
    amount: "250.00",
    method: "cash",
    applied_to_fees: "0.00",
    applied_to_interest: "10.00",
    applied_to_principal: "240.00",
    created_at: "2026-08-10T09:00:00Z",
    updated_at: "2026-08-10T09:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("MarkKeptPromiseButton", () => {
  it("opens the payment picker and marks kept when a payment is chosen", async () => {
    vi.mocked(listBhphPayments).mockResolvedValue({
      count: 1,
      results: [makePayment({ id: 900 })],
    });
    vi.mocked(markPromiseKept).mockResolvedValue({
      bhph_promise: makePromise({ state: "kept", actual_payment_id: 900 }),
    });
    const onMarked = vi.fn();

    render(
      <MarkKeptPromiseButton
        notePk={100}
        promise={makePromise()}
        onMarked={onMarked}
      />,
    );

    await userEvent.click(screen.getByTestId("mark-kept-button-5"));
    await waitFor(() => {
      expect(listBhphPayments).toHaveBeenCalledWith(100);
    });
    await userEvent.click(screen.getByTestId("payment-picker-row-900"));
    await waitFor(() => {
      expect(markPromiseKept).toHaveBeenCalledWith(5, {
        bhph_payment_id: 900,
      });
    });
    expect(onMarked).toHaveBeenCalledWith(
      expect.objectContaining({ state: "kept" }),
    );
  });

  it("disables the button when the promise is already terminal", () => {
    render(
      <MarkKeptPromiseButton
        notePk={100}
        promise={makePromise({ state: "kept" })}
        onMarked={vi.fn()}
      />,
    );
    expect(
      (screen.getByTestId("mark-kept-button-5") as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("surfaces a 400 cross-promise-payment error", async () => {
    vi.mocked(listBhphPayments).mockResolvedValue({
      count: 1,
      results: [makePayment({ id: 900 })],
    });
    vi.mocked(markPromiseKept).mockRejectedValue(new ApiError(400, "x-promise"));

    render(
      <MarkKeptPromiseButton
        notePk={100}
        promise={makePromise()}
        onMarked={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByTestId("mark-kept-button-5"));
    await waitFor(() =>
      expect(listBhphPayments).toHaveBeenCalled(),
    );
    await userEvent.click(screen.getByTestId("payment-picker-row-900"));
    await waitFor(() => {
      expect(screen.getByTestId("mark-kept-error-5").textContent).toMatch(
        /does not belong/i,
      );
    });
  });
});

describe("MarkBrokenPromiseButton", () => {
  it("marks broken via the confirm modal", async () => {
    vi.mocked(markPromiseBroken).mockResolvedValue({
      bhph_promise: makePromise({ state: "broken" }),
    });
    const onMarked = vi.fn();

    render(
      <MarkBrokenPromiseButton
        promise={makePromise()}
        onMarked={onMarked}
      />,
    );

    await userEvent.click(screen.getByTestId("mark-broken-button-5"));
    await userEvent.type(
      screen.getByTestId("mark-broken-notes-5"),
      "no answer",
    );
    await userEvent.click(screen.getByTestId("mark-broken-confirm-5"));

    await waitFor(() => {
      expect(markPromiseBroken).toHaveBeenCalledWith(5, {
        notes: "no answer",
      });
    });
    expect(onMarked).toHaveBeenCalledWith(
      expect.objectContaining({ state: "broken" }),
    );
  });

  it("surfaces a 409 terminal-state conflict", async () => {
    vi.mocked(markPromiseBroken).mockRejectedValue(
      new ApiError(409, "terminal"),
    );

    render(
      <MarkBrokenPromiseButton
        promise={makePromise()}
        onMarked={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByTestId("mark-broken-button-5"));
    await userEvent.click(screen.getByTestId("mark-broken-confirm-5"));

    await waitFor(() =>
      expect(markPromiseBroken).toHaveBeenCalled(),
    );
    expect(screen.getByText(/already in a terminal state/i)).toBeTruthy();
  });
});
