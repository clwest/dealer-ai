// Milestone 21 · Increment 2 (SESSION_168) — RepossessionRowActions tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/bhphApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/bhphApi")>(
    "@/lib/bhphApi",
  );
  return {
    ...actual,
    markRepossessionRecovered: vi.fn(),
    markRepossessionReIntaked: vi.fn(),
  };
});

import { ApiError } from "@/lib/authFetch";
import {
  markRepossessionRecovered,
  markRepossessionReIntaked,
  type RepossessionProjection,
} from "@/lib/bhphApi";
import {
  MarkRecoveredButton,
  MarkReIntakedButton,
} from "./RepossessionRowActions";

function makeRepo(
  overrides: Partial<RepossessionProjection> = {},
): RepossessionProjection {
  return {
    id: 33,
    note_id: 100,
    dealership_id: 1,
    ordered_at: "2026-08-03T10:00:00Z",
    ordered_by_user_id: null,
    agent_name: "Bob",
    recovered_at: null,
    recovery_location: "",
    intake_condition_report_id: null,
    state: "ordered",
    notes: "",
    created_at: "2026-08-03T10:00:00Z",
    updated_at: "2026-08-03T10:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("MarkRecoveredButton", () => {
  it("marks recovered via the confirm modal", async () => {
    vi.mocked(markRepossessionRecovered).mockResolvedValue({
      repossession: makeRepo({ state: "recovered", recovery_location: "yard" }),
    });
    const onMarked = vi.fn();

    render(<MarkRecoveredButton repossession={makeRepo()} onMarked={onMarked} />);

    await userEvent.click(screen.getByTestId("mark-recovered-button-33"));
    await userEvent.type(
      screen.getByTestId("mark-recovered-location-33"),
      "yard",
    );
    await userEvent.click(screen.getByTestId("mark-recovered-confirm-33"));

    await waitFor(() => {
      expect(markRepossessionRecovered).toHaveBeenCalledWith(
        33,
        expect.objectContaining({ recovery_location: "yard" }),
      );
    });
    expect(onMarked).toHaveBeenCalledWith(
      expect.objectContaining({ state: "recovered" }),
    );
  });

  it("disables when repossession is not in 'ordered' state", () => {
    render(
      <MarkRecoveredButton
        repossession={makeRepo({ state: "recovered" })}
        onMarked={vi.fn()}
      />,
    );
    expect(
      (
        screen.getByTestId("mark-recovered-button-33") as HTMLButtonElement
      ).disabled,
    ).toBe(true);
  });
});

describe("MarkReIntakedButton", () => {
  it("marks re-intaked with a valid condition report id", async () => {
    vi.mocked(markRepossessionReIntaked).mockResolvedValue({
      repossession: makeRepo({
        state: "re_intaked",
        intake_condition_report_id: 42,
      }),
    });
    const onMarked = vi.fn();

    render(
      <MarkReIntakedButton
        repossession={makeRepo({ state: "recovered" })}
        onMarked={onMarked}
      />,
    );

    await userEvent.click(screen.getByTestId("mark-re-intaked-button-33"));
    await userEvent.type(
      screen.getByTestId("mark-re-intaked-report-id-33"),
      "42",
    );
    await userEvent.click(screen.getByTestId("mark-re-intaked-confirm-33"));

    await waitFor(() => {
      expect(markRepossessionReIntaked).toHaveBeenCalledWith(
        33,
        expect.objectContaining({ condition_report_id: 42 }),
      );
    });
    expect(onMarked).toHaveBeenCalledWith(
      expect.objectContaining({ state: "re_intaked" }),
    );
  });

  it("rejects invalid condition report id without hitting the API", async () => {
    render(
      <MarkReIntakedButton
        repossession={makeRepo({ state: "recovered" })}
        onMarked={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByTestId("mark-re-intaked-button-33"));
    await userEvent.click(screen.getByTestId("mark-re-intaked-confirm-33"));

    await waitFor(() => {
      expect(screen.getByText(/valid conditionreport id/i)).toBeTruthy();
    });
    expect(markRepossessionReIntaked).not.toHaveBeenCalled();
  });

  it("surfaces a 400 cross-tenant condition-report error", async () => {
    vi.mocked(markRepossessionReIntaked).mockRejectedValue(
      new ApiError(400, "x-tenant"),
    );

    render(
      <MarkReIntakedButton
        repossession={makeRepo({ state: "recovered" })}
        onMarked={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByTestId("mark-re-intaked-button-33"));
    await userEvent.type(
      screen.getByTestId("mark-re-intaked-report-id-33"),
      "42",
    );
    await userEvent.click(screen.getByTestId("mark-re-intaked-confirm-33"));

    await waitFor(() => {
      expect(screen.getByText(/not scoped to this dealership/i)).toBeTruthy();
    });
  });
});
