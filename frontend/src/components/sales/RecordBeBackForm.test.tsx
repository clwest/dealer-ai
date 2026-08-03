// Milestone 21 · Increment 3 (SESSION_169) — RecordBeBackForm tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/salesApi", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/salesApi")>("@/lib/salesApi");
  return {
    ...actual,
    createBeBack: vi.fn(),
  };
});

import { ApiError } from "@/lib/authFetch";
import { createBeBack, type BeBackProjection } from "@/lib/salesApi";
import { RecordBeBackForm } from "./RecordBeBackForm";

function makeBeBack(
  overrides: Partial<BeBackProjection> = {},
): BeBackProjection {
  return {
    id: 1,
    lead_id: 42,
    dealership_id: 1,
    promised_at: "2026-08-04T14:00:00Z",
    promised_reason: "test_drive",
    actual_return_at: null,
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

describe("RecordBeBackForm", () => {
  it("submits and calls onRecorded with the returned be-back", async () => {
    vi.mocked(createBeBack).mockResolvedValue(
      makeBeBack({ id: 99, lead_id: 55, promised_reason: "bring_co_signer" }),
    );
    const onRecorded = vi.fn();
    render(<RecordBeBackForm onRecorded={onRecorded} />);

    await userEvent.type(
      screen.getByTestId("record-be-back-lead-id"),
      "55",
    );
    await userEvent.selectOptions(
      screen.getByTestId("record-be-back-reason"),
      "bring_co_signer",
    );
    await userEvent.type(
      screen.getByTestId("record-be-back-notes"),
      "wife needs to sign",
    );
    await userEvent.click(screen.getByTestId("record-be-back-submit"));

    await waitFor(() => {
      expect(createBeBack).toHaveBeenCalledWith(
        expect.objectContaining({
          lead_id: 55,
          promised_reason: "bring_co_signer",
          notes: "wife needs to sign",
        }),
      );
    });
    expect(onRecorded).toHaveBeenCalledWith(
      expect.objectContaining({ id: 99 }),
    );
  });

  it("blocks submit on invalid lead id and does not hit the API", async () => {
    render(<RecordBeBackForm onRecorded={vi.fn()} />);

    await userEvent.click(screen.getByTestId("record-be-back-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("record-be-back-error").textContent).toMatch(
        /valid lead id/i,
      );
    });
    expect(createBeBack).not.toHaveBeenCalled();
  });

  it("surfaces a 404 as a lead-not-found error", async () => {
    vi.mocked(createBeBack).mockRejectedValue(new ApiError(404, "no lead"));
    render(<RecordBeBackForm onRecorded={vi.fn()} />);

    await userEvent.type(
      screen.getByTestId("record-be-back-lead-id"),
      "9999",
    );
    await userEvent.click(screen.getByTestId("record-be-back-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("record-be-back-error").textContent).toMatch(
        /lead not found/i,
      );
    });
  });
});
