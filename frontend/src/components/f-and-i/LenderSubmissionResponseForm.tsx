// Milestone 35 · Increment 2 (SESSION_218) — LenderSubmission response form.
//
// PATCHes /admin/lender-submissions/<pk>/ (M10.3 shipped endpoint;
// M35.2 operational activation) via `updateLenderSubmissionStatus`.
// Per MILESTONE_35_PLANNING.md §5.b D7 + D11:
//
// - Three-value status radio: approved / counter / declined.
//   `pending` is intentionally excluded — the initial state comes
//   from create; recording pending as a response is nonsensical.
// - Optional notes textarea.
// - **NO `counter_terms` / `approval_terms` capture.** Structured
//   entry deferred per §5.h.
//
// **Mode-conditional UI language (D7 + user directive #3 + #4):**
// - Current status = `pending` → header "Record lender response";
//   button "Record response".
// - Current status ∈ {approved, counter, declined} → header
//   "Update lender response"; button "Update response".
//
// Any-to-any status transition supported per M10.3 contract
// (verified M35.0 §4.2). After a terminal status is recorded, the
// form remains available for same-record correction — but M35 does
// NOT support creating a second LenderSubmission (first-loop-only
// per D8 explicit boundary). Alternate-lender resubmission is
// deferred.
//
// **Financial-language contract (D11 refined per user directive
// #10):** Once `status="approved"` is recorded, the chip may
// truthfully display "Approved" — but individual DealStructure
// values may NOT be labeled as "lender-approved terms" unless
// verified approval_terms data is captured (M35 does NOT capture).
// This form displays only status + notes; it never labels
// DealStructure values.
//
// The companion Vitest string-absence test enforces R4's fourth
// defense layer via the same pattern used by
// `LenderSubmissionRecordForm.test.tsx`. Prohibited words live in
// the test, not this file.

import { useMemo, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/authFetch";
import {
  updateLenderSubmissionStatus,
  type LenderSubmissionProjection,
  type LenderSubmissionStatus,
  type UpdateLenderSubmissionStatusRequest,
} from "@/lib/fAndIApi";

/**
 * Minimal context the response form needs to PATCH the correct
 * LenderSubmission and render mode-conditional UI. Sourced from the
 * CA-list row (M35.2 §0.a amendment added `latest_lender_submission_id`
 * to the CA projection so the intake page can construct this context
 * without a preceding GET). `initialNotes` is optional — the CA
 * projection does not carry submission notes, so the form starts with
 * blank notes on page refresh (post-record it carries whatever the
 * operator entered locally).
 */
export interface LenderSubmissionResponseContext {
  id: number;
  status: LenderSubmissionStatus;
  initialNotes?: string;
}

export interface LenderSubmissionResponseFormProps {
  submission: LenderSubmissionResponseContext;
  onUpdated: (submission: LenderSubmissionProjection) => void;
  onCancel?: () => void;
  /** Injected for tests. Defaults to shipped `updateLenderSubmissionStatus`. */
  submit?: typeof updateLenderSubmissionStatus;
}

type ResponseStatus = "approved" | "counter" | "declined";

const RESPONSE_OPTIONS: Array<{ value: ResponseStatus; label: string }> = [
  { value: "approved", label: "Approved" },
  { value: "counter", label: "Counter-offer" },
  { value: "declined", label: "Declined" },
];

function isTerminalStatus(
  status: LenderSubmissionStatus,
): status is ResponseStatus {
  return status === "approved" || status === "counter" || status === "declined";
}

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) {
      return "Invalid response fields. Check the values and try again.";
    }
    if (err.status === 404) {
      return "Lender submission not found in your dealership.";
    }
    if (err.status === 403) {
      return "Only F&I managers or dealer owners can update lender responses.";
    }
    return `Server returned ${err.status}.`;
  }
  return "Failed to update the lender response.";
}

export function LenderSubmissionResponseForm({
  submission,
  onUpdated,
  onCancel,
  submit = updateLenderSubmissionStatus,
}: LenderSubmissionResponseFormProps) {
  const [selectedStatus, setSelectedStatus] = useState<ResponseStatus | "">(
    isTerminalStatus(submission.status) ? submission.status : "",
  );
  const terminal = isTerminalStatus(submission.status);
  const initialNotes = submission.initialNotes ?? "";
  const [notes, setNotes] = useState<string>(initialNotes);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isRecordMode = !terminal;
  const headerText = isRecordMode
    ? "Record lender response"
    : "Update lender response";
  const buttonText = isRecordMode ? "Record response" : "Update response";
  const helperText = isRecordMode
    ? "The submission is awaiting a response. Record it once the lender replies."
    : `The response is currently ${humanTerminalLabel(submission.status)}. Correct it if the lender's response changed after it was first recorded.`;

  const missingReasons = useMemo(() => {
    const reasons: string[] = [];
    if (selectedStatus === "") {
      reasons.push("Choose the lender's response.");
    }
    return reasons;
  }, [selectedStatus]);

  const canSubmit = missingReasons.length === 0 && !submitting;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit || selectedStatus === "") return;
    setSubmitting(true);
    setError(null);
    const payload: UpdateLenderSubmissionStatusRequest = {
      status: selectedStatus,
    };
    if (notes.trim() !== initialNotes.trim()) {
      payload.notes = notes.trim();
    }
    try {
      const updated = await submit(submission.id, payload);
      onUpdated(updated);
    } catch (err) {
      setError(humanizeError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      data-testid="lender-submission-response-form"
      className="space-y-4"
    >
      <div>
        <h3
          className="text-lg font-semibold"
          data-testid="lender-submission-response-header"
        >
          {headerText}
        </h3>
        <p className="text-sm text-muted-foreground">{helperText}</p>
      </div>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Response</legend>
        {RESPONSE_OPTIONS.map((option) => {
          const inputId = `lender-submission-response-${option.value}`;
          return (
            <label
              key={option.value}
              htmlFor={inputId}
              className="flex items-center gap-2 text-sm"
            >
              <input
                type="radio"
                id={inputId}
                name="lender-submission-response"
                value={option.value}
                data-testid={inputId}
                checked={selectedStatus === option.value}
                onChange={() => setSelectedStatus(option.value)}
              />
              {option.label}
            </label>
          );
        })}
      </fieldset>

      <label className="flex flex-col text-sm">
        <span className="mb-1 font-medium">Notes (optional)</span>
        <Input
          data-testid="lender-submission-response-notes"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          placeholder="Anything to remember about this response"
        />
      </label>

      {missingReasons.length > 0 && (
        <ul
          className="text-xs text-muted-foreground"
          data-testid="lender-submission-response-missing-reasons"
        >
          {missingReasons.map((reason) => (
            <li key={reason}>• {reason}</li>
          ))}
        </ul>
      )}

      {error && (
        <p
          role="alert"
          className="text-sm text-destructive"
          data-testid="lender-submission-response-error"
        >
          {error}
        </p>
      )}

      <div className="flex items-center gap-2">
        <Button
          type="submit"
          disabled={!canSubmit}
          data-testid="lender-submission-response-submit"
        >
          {buttonText}
        </Button>
        {onCancel && (
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            data-testid="lender-submission-response-cancel"
          >
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}

function humanTerminalLabel(status: LenderSubmissionStatus): string {
  switch (status) {
    case "approved":
      return "approved";
    case "counter":
      return "a counter-offer";
    case "declined":
      return "declined";
    default:
      return status;
  }
}
