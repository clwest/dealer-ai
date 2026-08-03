// Milestone 23 · Increment 2 (SESSION_177) — RecordBhphNoteForm tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/bhphApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/bhphApi")>(
    "@/lib/bhphApi",
  );
  return {
    ...actual,
    createBhphNote: vi.fn(),
  };
});

import { ApiError } from "@/lib/authFetch";
import {
  createBhphNote,
  type BhphNoteProjection,
} from "@/lib/bhphApi";
import { RecordBhphNoteForm } from "./RecordBhphNoteForm";

function makeNote(
  overrides: Partial<BhphNoteProjection> = {},
): BhphNoteProjection {
  return {
    id: 1,
    sale_id: 42,
    dealership_id: 1,
    principal_financed: "5000.00",
    apr: "18.50",
    term_weeks: 52,
    payment_frequency: "weekly",
    payment_amount: "120.00",
    first_payment_due: "2026-08-10",
    default_grace_days: 5,
    current_bucket: "current",
    days_past_due: 0,
    created_at: "2026-08-03T00:00:00Z",
    updated_at: "2026-08-03T00:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("RecordBhphNoteForm", () => {
  it("submits with the entered fields and calls onOriginated", async () => {
    vi.mocked(createBhphNote).mockResolvedValue({
      bhph_note: makeNote({ id: 99, principal_financed: "7500.00" }),
    });
    const onOriginated = vi.fn();
    render(<RecordBhphNoteForm onOriginated={onOriginated} />);

    await userEvent.type(
      screen.getByTestId("record-bhph-note-sale-id"),
      "42",
    );
    await userEvent.type(
      screen.getByTestId("record-bhph-note-principal"),
      "7500",
    );
    await userEvent.type(
      screen.getByTestId("record-bhph-note-apr"),
      "18.5",
    );
    await userEvent.selectOptions(
      screen.getByTestId("record-bhph-note-frequency"),
      "biweekly",
    );
    await userEvent.click(screen.getByTestId("record-bhph-note-submit"));

    await waitFor(() => {
      expect(createBhphNote).toHaveBeenCalledWith(
        expect.objectContaining({
          sale_id: 42,
          principal_financed: "7500",
          apr: "18.5",
          payment_frequency: "biweekly",
          term_weeks: 52,
        }),
      );
    });
    expect(onOriginated).toHaveBeenCalledWith(
      expect.objectContaining({ id: 99 }),
    );
  });

  it("prefills sale_id from initialSaleId prop", () => {
    render(
      <RecordBhphNoteForm onOriginated={vi.fn()} initialSaleId={123} />,
    );
    const input = screen.getByTestId(
      "record-bhph-note-sale-id",
    ) as HTMLInputElement;
    expect(input.value).toBe("123");
  });

  it("blocks submit when sale_id is missing", async () => {
    const onOriginated = vi.fn();
    render(<RecordBhphNoteForm onOriginated={onOriginated} />);

    await userEvent.type(
      screen.getByTestId("record-bhph-note-principal"),
      "5000",
    );
    await userEvent.type(
      screen.getByTestId("record-bhph-note-apr"),
      "18.5",
    );
    await userEvent.click(screen.getByTestId("record-bhph-note-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("record-bhph-note-error")).toBeTruthy();
    });
    expect(createBhphNote).not.toHaveBeenCalled();
    expect(onOriginated).not.toHaveBeenCalled();
  });

  it("blocks submit when principal is zero", async () => {
    const onOriginated = vi.fn();
    render(<RecordBhphNoteForm onOriginated={onOriginated} />);

    await userEvent.type(
      screen.getByTestId("record-bhph-note-sale-id"),
      "42",
    );
    await userEvent.type(
      screen.getByTestId("record-bhph-note-principal"),
      "0",
    );
    await userEvent.type(
      screen.getByTestId("record-bhph-note-apr"),
      "18.5",
    );
    await userEvent.click(screen.getByTestId("record-bhph-note-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("record-bhph-note-error")).toBeTruthy();
    });
    expect(createBhphNote).not.toHaveBeenCalled();
  });

  it("surfaces a backend 409 duplicate as a human-readable error", async () => {
    vi.mocked(createBhphNote).mockRejectedValue(
      new ApiError(409, "duplicate"),
    );
    const onOriginated = vi.fn();
    render(<RecordBhphNoteForm onOriginated={onOriginated} />);

    await userEvent.type(
      screen.getByTestId("record-bhph-note-sale-id"),
      "42",
    );
    await userEvent.type(
      screen.getByTestId("record-bhph-note-principal"),
      "5000",
    );
    await userEvent.type(
      screen.getByTestId("record-bhph-note-apr"),
      "18.5",
    );
    await userEvent.click(screen.getByTestId("record-bhph-note-submit"));

    await waitFor(() => {
      expect(
        screen.getByTestId("record-bhph-note-error").textContent,
      ).toContain("already has a BHPH note");
    });
    expect(onOriginated).not.toHaveBeenCalled();
  });

  it("surfaces a backend 404 as a sale-not-found message", async () => {
    vi.mocked(createBhphNote).mockRejectedValue(
      new ApiError(404, "not found"),
    );
    const onOriginated = vi.fn();
    render(<RecordBhphNoteForm onOriginated={onOriginated} />);

    await userEvent.type(
      screen.getByTestId("record-bhph-note-sale-id"),
      "99",
    );
    await userEvent.type(
      screen.getByTestId("record-bhph-note-principal"),
      "5000",
    );
    await userEvent.type(
      screen.getByTestId("record-bhph-note-apr"),
      "18.5",
    );
    await userEvent.click(screen.getByTestId("record-bhph-note-submit"));

    await waitFor(() => {
      expect(
        screen.getByTestId("record-bhph-note-error").textContent,
      ).toContain("Sale not found");
    });
  });

  it("resets fields after successful submit", async () => {
    vi.mocked(createBhphNote).mockResolvedValue({
      bhph_note: makeNote({ id: 1 }),
    });
    render(<RecordBhphNoteForm onOriginated={vi.fn()} />);

    const saleIdInput = screen.getByTestId(
      "record-bhph-note-sale-id",
    ) as HTMLInputElement;
    const principalInput = screen.getByTestId(
      "record-bhph-note-principal",
    ) as HTMLInputElement;
    await userEvent.type(saleIdInput, "42");
    await userEvent.type(principalInput, "5000");
    await userEvent.type(
      screen.getByTestId("record-bhph-note-apr"),
      "18.5",
    );
    await userEvent.click(screen.getByTestId("record-bhph-note-submit"));

    await waitFor(() => {
      expect(saleIdInput.value).toBe("");
      expect(principalInput.value).toBe("");
    });
  });
});
