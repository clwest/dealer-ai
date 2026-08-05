// Milestone 35 · Increment 2 (SESSION_218) — LenderSubmissionResponseForm tests.
//
// Covers:
// - Three-value radio (approved / counter / declined). Pending is
//   NOT rendered as a response option (D7 exclusion).
// - Mode-conditional headers + buttons: pending → "Record lender
//   response" / "Record response"; terminal → "Update lender response"
//   / "Update response".
// - Terminal-status form pre-selects the current status (correction
//   mode).
// - PATCH payload shape: status required; notes only when changed.
// - Success handler receives updated projection.
// - No counter_terms/approval_terms fields in the DOM.
// - **PROHIBITED strings absence** via source-file read.

import responseFormSource from "./LenderSubmissionResponseForm.tsx?raw";

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LenderSubmissionResponseForm } from "./LenderSubmissionResponseForm";
import type {
  LenderSubmissionProjection,
  LenderSubmissionStatus,
} from "@/lib/fAndIApi";
import type { LenderSubmissionResponseContext } from "./LenderSubmissionResponseForm";
import { ApiError } from "@/lib/authFetch";

function makeContext(
  overrides: Partial<LenderSubmissionResponseContext> = {},
): LenderSubmissionResponseContext {
  return {
    id: 501,
    status: "pending" as LenderSubmissionStatus,
    ...overrides,
  };
}

function makeProjection(
  overrides: Partial<LenderSubmissionProjection> = {},
): LenderSubmissionProjection {
  return {
    id: 501,
    deal_structure_id: 42,
    lender_program_id: 12,
    lender_program_name: "Bank of America",
    submitted_at: "2026-08-05T15:00:00Z",
    status: "pending",
    counter_terms: {},
    approval_terms: {},
    notes: "",
    created_at: "2026-08-05T15:00:00Z",
    updated_at: "2026-08-05T15:00:00Z",
    ...overrides,
  };
}

describe("LenderSubmissionResponseForm", () => {
  it("shows record-mode language when status is pending", () => {
    render(
      <LenderSubmissionResponseForm
        submission={makeContext()}
        onUpdated={vi.fn()}
      />,
    );
    expect(
      screen.getByTestId("lender-submission-response-header"),
    ).toHaveTextContent("Record lender response");
    expect(
      screen.getByTestId("lender-submission-response-submit"),
    ).toHaveTextContent("Record response");
  });

  it("shows update-mode language when status is approved / counter / declined", () => {
    for (const status of ["approved", "counter", "declined"] as const) {
      const { unmount } = render(
        <LenderSubmissionResponseForm
          submission={makeContext({ status })}
          onUpdated={vi.fn()}
        />,
      );
      expect(
        screen.getByTestId("lender-submission-response-header"),
      ).toHaveTextContent("Update lender response");
      expect(
        screen.getByTestId("lender-submission-response-submit"),
      ).toHaveTextContent("Update response");
      unmount();
    }
  });

  it("renders only three response options — pending is not selectable", () => {
    render(
      <LenderSubmissionResponseForm
        submission={makeContext()}
        onUpdated={vi.fn()}
      />,
    );
    expect(
      screen.getByTestId("lender-submission-response-approved"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("lender-submission-response-counter"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("lender-submission-response-declined"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("lender-submission-response-pending"),
    ).not.toBeInTheDocument();
  });

  it("pre-selects the current terminal status in update mode", () => {
    render(
      <LenderSubmissionResponseForm
        submission={makeContext({ status: "counter" })}
        onUpdated={vi.fn()}
      />,
    );
    const counter = screen.getByTestId(
      "lender-submission-response-counter",
    ) as HTMLInputElement;
    expect(counter.checked).toBe(true);
  });

  it("disables submit until a response is selected in record mode", async () => {
    const user = userEvent.setup();
    render(
      <LenderSubmissionResponseForm
        submission={makeContext()}
        onUpdated={vi.fn()}
      />,
    );
    const button = screen.getByTestId("lender-submission-response-submit");
    expect(button).toBeDisabled();
    await user.click(screen.getByTestId("lender-submission-response-approved"));
    expect(button).toBeEnabled();
  });

  it("PATCHes only the status when notes are unchanged", async () => {
    const user = userEvent.setup();
    const submit = vi.fn().mockResolvedValue(makeProjection({ status: "approved" }));
    const onUpdated = vi.fn();
    render(
      <LenderSubmissionResponseForm
        submission={makeContext()}
        onUpdated={onUpdated}
        submit={submit}
      />,
    );
    await user.click(screen.getByTestId("lender-submission-response-approved"));
    await user.click(screen.getByTestId("lender-submission-response-submit"));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    expect(submit).toHaveBeenCalledWith(501, { status: "approved" });
    expect(onUpdated).toHaveBeenCalled();
  });

  it("includes notes in the PATCH payload when the operator edits them", async () => {
    const user = userEvent.setup();
    const submit = vi.fn().mockResolvedValue(makeProjection({ status: "declined" }));
    render(
      <LenderSubmissionResponseForm
        submission={makeContext()}
        onUpdated={vi.fn()}
        submit={submit}
      />,
    );
    await user.click(screen.getByTestId("lender-submission-response-declined"));
    await user.type(
      screen.getByTestId("lender-submission-response-notes"),
      "credit tier below cutoff",
    );
    await user.click(screen.getByTestId("lender-submission-response-submit"));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    expect(submit.mock.calls[0][1]).toEqual({
      status: "declined",
      notes: "credit tier below cutoff",
    });
  });

  it("does not render counter_terms or approval_terms fields", () => {
    render(
      <LenderSubmissionResponseForm
        submission={makeContext()}
        onUpdated={vi.fn()}
      />,
    );
    expect(screen.queryByText(/counter_terms/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/approval_terms/i)).not.toBeInTheDocument();
  });

  it("shows a submit error when the PATCH returns 400", async () => {
    const user = userEvent.setup();
    const submit = vi
      .fn()
      .mockRejectedValue(new ApiError(400, "Bad request"));
    render(
      <LenderSubmissionResponseForm
        submission={makeContext()}
        onUpdated={vi.fn()}
        submit={submit}
      />,
    );
    await user.click(screen.getByTestId("lender-submission-response-approved"));
    await user.click(screen.getByTestId("lender-submission-response-submit"));
    const err = await screen.findByTestId("lender-submission-response-error");
    expect(err.textContent).toContain("Invalid response fields");
  });

  it("contains no transmit-implying vocabulary in the source", () => {
    // R4 fourth defense layer — Vite ?raw import; no @types/node.
    const prohibited = [
      "Send to lender",
      "Submit to lender",
      "Transmit",
      "Contact lender",
      "Submitting…",
    ];
    for (const bad of prohibited) {
      expect(responseFormSource).not.toContain(bad);
    }
  });
});
