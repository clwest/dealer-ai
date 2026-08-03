// Milestone 21 · Increment 2 (SESSION_168) — InitiateRepossessionForm tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/bhphApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/bhphApi")>(
    "@/lib/bhphApi",
  );
  return {
    ...actual,
    initiateRepossession: vi.fn(),
  };
});

import { ApiError } from "@/lib/authFetch";
import {
  initiateRepossession,
  type RepossessionProjection,
} from "@/lib/bhphApi";
import { InitiateRepossessionForm } from "./InitiateRepossessionForm";

function makeRepo(
  overrides: Partial<RepossessionProjection> = {},
): RepossessionProjection {
  return {
    id: 20,
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

describe("InitiateRepossessionForm", () => {
  it("requires an agent name", async () => {
    const onInitiated = vi.fn();
    render(
      <InitiateRepossessionForm notePk={100} onInitiated={onInitiated} />,
    );

    await userEvent.click(screen.getByTestId("initiate-repo-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("initiate-repo-error").textContent).toMatch(
        /agent name/i,
      );
    });
    expect(initiateRepossession).not.toHaveBeenCalled();
  });

  it("submits with agent + notes and calls onInitiated", async () => {
    vi.mocked(initiateRepossession).mockResolvedValue({
      repossession: makeRepo({ id: 99, agent_name: "Alice" }),
    });
    const onInitiated = vi.fn();
    render(
      <InitiateRepossessionForm notePk={100} onInitiated={onInitiated} />,
    );

    await userEvent.type(
      screen.getByTestId("initiate-repo-agent"),
      "Alice",
    );
    await userEvent.type(
      screen.getByTestId("initiate-repo-notes"),
      "broken PtP + 45 days past due",
    );
    await userEvent.click(screen.getByTestId("initiate-repo-submit"));

    await waitFor(() => {
      expect(initiateRepossession).toHaveBeenCalledWith(
        100,
        expect.objectContaining({
          agent_name: "Alice",
          notes: "broken PtP + 45 days past due",
        }),
      );
    });
    expect(onInitiated).toHaveBeenCalledWith(
      expect.objectContaining({ id: 99 }),
    );
  });

  it("surfaces backend errors", async () => {
    vi.mocked(initiateRepossession).mockRejectedValue(
      new ApiError(404, "not found"),
    );
    render(
      <InitiateRepossessionForm notePk={100} onInitiated={vi.fn()} />,
    );

    await userEvent.type(
      screen.getByTestId("initiate-repo-agent"),
      "Alice",
    );
    await userEvent.click(screen.getByTestId("initiate-repo-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("initiate-repo-error").textContent).toMatch(
        /note not found/i,
      );
    });
  });
});
