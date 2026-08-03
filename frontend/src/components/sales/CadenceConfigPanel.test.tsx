// Milestone 21 · Increment 3 (SESSION_169) — CadenceConfigPanel tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/salesApi", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/salesApi")>("@/lib/salesApi");
  return {
    ...actual,
    createCadence: vi.fn(),
    pauseCadence: vi.fn(),
  };
});

import { ApiError } from "@/lib/authFetch";
import {
  createCadence,
  pauseCadence,
  type CadenceProjection,
} from "@/lib/salesApi";
import { CadenceConfigPanel } from "./CadenceConfigPanel";

function makeCadence(
  overrides: Partial<CadenceProjection> = {},
): CadenceProjection {
  return {
    id: 7,
    lead_id: 42,
    dealership_id: 1,
    template: "24hr",
    started_at: "2026-08-03T09:00:00Z",
    is_active: true,
    task_count: 5,
    created_at: "2026-08-03T09:00:00Z",
    updated_at: "2026-08-03T09:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("CreateCadenceForm", () => {
  it("creates a cadence and reflects it in the recent list", async () => {
    vi.mocked(createCadence).mockResolvedValue(
      makeCadence({ id: 12, lead_id: 55, template: "1wk" }),
    );
    const onChanged = vi.fn();
    render(<CadenceConfigPanel onChanged={onChanged} />);

    await userEvent.type(
      screen.getByTestId("create-cadence-lead-id"),
      "55",
    );
    await userEvent.selectOptions(
      screen.getByTestId("create-cadence-template"),
      "1wk",
    );
    await userEvent.click(screen.getByTestId("create-cadence-submit"));

    await waitFor(() => {
      expect(createCadence).toHaveBeenCalledWith({
        lead_id: 55,
        template: "1wk",
      });
    });
    expect(onChanged).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByTestId("cadence-config-recent")).toBeTruthy();
      expect(screen.getByTestId("cadence-state-12").textContent).toMatch(
        /active/,
      );
    });
  });

  it("blocks submit on invalid lead id and does not hit the API", async () => {
    render(<CadenceConfigPanel />);

    await userEvent.click(screen.getByTestId("create-cadence-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("create-cadence-error").textContent).toMatch(
        /valid lead id/i,
      );
    });
    expect(createCadence).not.toHaveBeenCalled();
  });

  it("surfaces a 409 conflict when the lead already has that cadence", async () => {
    vi.mocked(createCadence).mockRejectedValue(new ApiError(409, "dup"));
    render(<CadenceConfigPanel />);

    await userEvent.type(
      screen.getByTestId("create-cadence-lead-id"),
      "42",
    );
    await userEvent.click(screen.getByTestId("create-cadence-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("create-cadence-error").textContent).toMatch(
        /already has an active cadence/i,
      );
    });
  });
});

describe("PauseCadenceByIdForm + inline pause button", () => {
  it("pauses a cadence by ID via the modal", async () => {
    vi.mocked(pauseCadence).mockResolvedValue(
      makeCadence({ id: 88, is_active: false }),
    );
    const onChanged = vi.fn();
    render(<CadenceConfigPanel onChanged={onChanged} />);

    await userEvent.click(screen.getByTestId("pause-cadence-by-id-button"));
    await userEvent.type(
      screen.getByTestId("pause-cadence-by-id-input"),
      "88",
    );
    await userEvent.click(screen.getByTestId("pause-cadence-by-id-confirm"));

    await waitFor(() => {
      expect(pauseCadence).toHaveBeenCalledWith(88);
    });
    expect(onChanged).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByTestId("cadence-state-88").textContent).toMatch(
        /paused/,
      );
    });
  });

  it("inline pause button on a recent cadence pauses it", async () => {
    vi.mocked(createCadence).mockResolvedValue(makeCadence({ id: 21 }));
    vi.mocked(pauseCadence).mockResolvedValue(
      makeCadence({ id: 21, is_active: false }),
    );
    render(<CadenceConfigPanel />);

    // First create so a row appears with an inline pause.
    await userEvent.type(
      screen.getByTestId("create-cadence-lead-id"),
      "42",
    );
    await userEvent.click(screen.getByTestId("create-cadence-submit"));

    await waitFor(() =>
      expect(screen.getByTestId("cadence-row-21")).toBeTruthy(),
    );

    await userEvent.click(screen.getByTestId("pause-cadence-button-21"));

    await waitFor(() => {
      expect(pauseCadence).toHaveBeenCalledWith(21);
    });
    await waitFor(() => {
      expect(screen.getByTestId("cadence-state-21").textContent).toMatch(
        /paused/,
      );
    });
  });

  it("surfaces a 404 when the cadence ID is unknown", async () => {
    vi.mocked(pauseCadence).mockRejectedValue(new ApiError(404, "unknown"));
    render(<CadenceConfigPanel />);

    await userEvent.click(screen.getByTestId("pause-cadence-by-id-button"));
    await userEvent.type(
      screen.getByTestId("pause-cadence-by-id-input"),
      "9999",
    );
    await userEvent.click(screen.getByTestId("pause-cadence-by-id-confirm"));

    await waitFor(() => {
      expect(screen.getByText(/cadence not found/i)).toBeTruthy();
    });
  });
});
