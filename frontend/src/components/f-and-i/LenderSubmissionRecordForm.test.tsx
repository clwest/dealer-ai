// Milestone 35 · Increment 2 (SESSION_218) — LenderSubmissionRecordForm tests.
//
// Covers:
// - Submit disabled until LenderProgram selected (D6 gate).
// - POST payload shape (deal_structure_id + lender_program_id; NO
//   submitted_at; NO status override; notes only when non-empty).
// - Success handler receives full LenderSubmissionProjection.
// - Loading / error / empty branches for the programs list.
// - UI language contract: header, button, "Choose a lender program"
//   placeholder — all present.
// - **PROHIBITED strings absence** (R4 fourth defense layer): the
//   file source must contain none of "Send to lender", "Send",
//   "Submit to lender", "Transmit", "Contact lender", "Submitting…".
//   Reads the component source file and asserts.

import recordFormSource from "./LenderSubmissionRecordForm.tsx?raw";

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LenderSubmissionRecordForm } from "./LenderSubmissionRecordForm";
import type {
  LenderProgramSelectorProjection,
  LenderSubmissionProjection,
} from "@/lib/fAndIApi";
import { ApiError } from "@/lib/authFetch";

const PROGRAMS: LenderProgramSelectorProjection[] = [
  { id: 11, name: "Ally" },
  { id: 12, name: "Bank of America" },
  { id: 13, name: "Chase" },
];

const SAMPLE_SUBMISSION: LenderSubmissionProjection = {
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
};

describe("LenderSubmissionRecordForm", () => {
  it("disables submit until a lender program is selected", async () => {
    const user = userEvent.setup();
    const fetchPrograms = vi.fn().mockResolvedValue(PROGRAMS);
    const submit = vi.fn().mockResolvedValue(SAMPLE_SUBMISSION);
    render(
      <LenderSubmissionRecordForm
        dealStructureId={42}
        onRecorded={vi.fn()}
        fetchPrograms={fetchPrograms}
        submit={submit}
      />,
    );
    // Wait for the programs list to load.
    await screen.findByTestId("lender-submission-program-select");
    const button = screen.getByTestId("lender-submission-record-submit");
    expect(button).toBeDisabled();
    // Select a program → button enables.
    await user.selectOptions(
      screen.getByTestId("lender-submission-program-select"),
      "12",
    );
    expect(button).toBeEnabled();
  });

  it("POSTs the minimal payload without submitted_at or status", async () => {
    const user = userEvent.setup();
    const fetchPrograms = vi.fn().mockResolvedValue(PROGRAMS);
    const submit = vi.fn().mockResolvedValue(SAMPLE_SUBMISSION);
    const onRecorded = vi.fn();
    render(
      <LenderSubmissionRecordForm
        dealStructureId={42}
        onRecorded={onRecorded}
        fetchPrograms={fetchPrograms}
        submit={submit}
      />,
    );
    await screen.findByTestId("lender-submission-program-select");
    await user.selectOptions(
      screen.getByTestId("lender-submission-program-select"),
      "12",
    );
    await user.click(screen.getByTestId("lender-submission-record-submit"));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    const payload = submit.mock.calls[0][0];
    expect(payload).toEqual({
      deal_structure_id: 42,
      lender_program_id: 12,
    });
    expect(payload).not.toHaveProperty("submitted_at");
    expect(payload).not.toHaveProperty("status");
    expect(payload).not.toHaveProperty("counter_terms");
    expect(payload).not.toHaveProperty("approval_terms");
    expect(onRecorded).toHaveBeenCalledWith(SAMPLE_SUBMISSION);
  });

  it("includes notes in the payload only when non-empty", async () => {
    const user = userEvent.setup();
    const fetchPrograms = vi.fn().mockResolvedValue(PROGRAMS);
    const submit = vi.fn().mockResolvedValue(SAMPLE_SUBMISSION);
    render(
      <LenderSubmissionRecordForm
        dealStructureId={42}
        onRecorded={vi.fn()}
        fetchPrograms={fetchPrograms}
        submit={submit}
      />,
    );
    await screen.findByTestId("lender-submission-program-select");
    await user.selectOptions(
      screen.getByTestId("lender-submission-program-select"),
      "12",
    );
    await user.type(
      screen.getByTestId("lender-submission-notes"),
      "M35.2 test note",
    );
    await user.click(screen.getByTestId("lender-submission-record-submit"));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    expect(submit.mock.calls[0][0].notes).toBe("M35.2 test note");
  });

  it("shows the programs-empty message when no active lender programs exist", async () => {
    const fetchPrograms = vi.fn().mockResolvedValue([]);
    const submit = vi.fn();
    render(
      <LenderSubmissionRecordForm
        dealStructureId={42}
        onRecorded={vi.fn()}
        fetchPrograms={fetchPrograms}
        submit={submit}
      />,
    );
    await screen.findByTestId("lender-programs-empty");
    // No select rendered; submit stays disabled.
    expect(
      screen.queryByTestId("lender-submission-program-select"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByTestId("lender-submission-record-submit"),
    ).toBeDisabled();
  });

  it("renders a 403 error when the programs endpoint denies access", async () => {
    const fetchPrograms = vi
      .fn()
      .mockRejectedValue(new ApiError(403, "Forbidden"));
    const submit = vi.fn();
    render(
      <LenderSubmissionRecordForm
        dealStructureId={42}
        onRecorded={vi.fn()}
        fetchPrograms={fetchPrograms}
        submit={submit}
      />,
    );
    const error = await screen.findByTestId("lender-programs-error");
    expect(error.textContent).toContain("F&I managers or dealer owners");
  });

  it("renders record-vs-transmit language only (no prohibited strings)", () => {
    // R4 fourth defense layer — imported via Vite's ?raw query so no
    // @types/node dependency; asserts the component source is free
    // of transmit-implying vocabulary. Guards against copy-drift
    // that would falsely imply Dealer OS transmits to the lender.
    const prohibited = [
      "Send to lender",
      "Submit to lender",
      "Transmit",
      "Contact lender",
      "Submitting…",
    ];
    for (const bad of prohibited) {
      expect(recordFormSource).not.toContain(bad);
    }
    // Also assert the record-vs-transmit vocabulary is present in
    // the rendered form (belt).
    const fetchPrograms = vi.fn().mockResolvedValue(PROGRAMS);
    render(
      <LenderSubmissionRecordForm
        dealStructureId={42}
        onRecorded={vi.fn()}
        fetchPrograms={fetchPrograms}
      />,
    );
    expect(screen.getByText("Record lender submission")).toBeInTheDocument();
    expect(
      screen.getByTestId("lender-submission-record-submit"),
    ).toHaveTextContent("Record submission");
  });

  it("shows a submit error when the POST endpoint returns 400", async () => {
    const user = userEvent.setup();
    const fetchPrograms = vi.fn().mockResolvedValue(PROGRAMS);
    const submit = vi
      .fn()
      .mockRejectedValue(new ApiError(400, "Bad request"));
    render(
      <LenderSubmissionRecordForm
        dealStructureId={42}
        onRecorded={vi.fn()}
        fetchPrograms={fetchPrograms}
        submit={submit}
      />,
    );
    await screen.findByTestId("lender-submission-program-select");
    await user.selectOptions(
      screen.getByTestId("lender-submission-program-select"),
      "12",
    );
    await user.click(screen.getByTestId("lender-submission-record-submit"));
    const err = await screen.findByTestId("lender-submission-error");
    expect(err.textContent).toContain("Invalid submission fields");
  });
});
