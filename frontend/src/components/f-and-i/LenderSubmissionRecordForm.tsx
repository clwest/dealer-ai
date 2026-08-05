// Milestone 35 · Increment 2 (SESSION_218) — LenderSubmission record form.
//
// Posts to POST /admin/lender-submissions/ (M10.3 shipped endpoint;
// M35.2 operational activation) via `recordLenderSubmission`. Per
// MILESTONE_35_PLANNING.md §5.b D6 + D11:
//
// - Two fields: LenderProgram select (populated from
//   `listLenderPrograms()` on mount) + optional notes textarea.
// - Submit disabled until a LenderProgram is selected.
// - **NO `submitted_at` field.** Server records `timezone.now()` at
//   insert (M35.0 §4.8 non-blocking correction — no operational back-
//   entry evidence).
// - **NO `status` override.** Server defaults to "pending"; response
//   is recorded separately via LenderSubmissionResponseForm.
// - **NO `counter_terms` / `approval_terms` capture.** Structured
//   entry deferred per §5.h.
//
// **UI language contract (D6 + D11 + R4 — critical):**
// - Header: "Record lender submission" (past-tense operator action).
// - Button: "Record submission".
// - Success confirmation surfaces the returned lender_program_name +
//   returned timestamp verbatim.
// - The companion Vitest string-absence test enforces R4's fourth
//   defense layer: it reads this file's source and asserts a
//   prohibited list of transmit-implying words is absent. The
//   prohibited words themselves live in that test — not here — so
//   this file's docstring cannot accidentally cause the test to
//   self-match. Rule of thumb: describe the intent ("record-vs-
//   transmit vocabulary") in prose, never list the prohibited words
//   in this file.
//
// **Rationale for the record-vs-transmit language** (M35.0 §4.7
// verification): `record_lender_submission` service verb is a pure DB
// insert — no HTTP call, no webhook, no Celery task. The operator
// completes the external submission (phone / email / lender portal)
// BEFORE opening Dealer OS; this form records that already-completed
// action. Language must never falsely imply Dealer OS initiates the
// outbound call.

import { useEffect, useMemo, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/authFetch";
import {
  listLenderPrograms,
  recordLenderSubmission,
  type LenderProgramSelectorProjection,
  type LenderSubmissionProjection,
  type RecordLenderSubmissionRequest,
} from "@/lib/fAndIApi";

export interface LenderSubmissionRecordFormProps {
  dealStructureId: number;
  onRecorded: (submission: LenderSubmissionProjection) => void;
  onCancel?: () => void;
  /** Injected for tests. Defaults to shipped `listLenderPrograms`. */
  fetchPrograms?: typeof listLenderPrograms;
  /** Injected for tests. Defaults to shipped `recordLenderSubmission`. */
  submit?: typeof recordLenderSubmission;
}

type LoadState = "loading" | "ready" | "error";

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) {
      return "Invalid submission fields. Check the values and try again.";
    }
    if (err.status === 404) {
      return "Deal structure or lender program not found in your dealership.";
    }
    if (err.status === 403) {
      return "Only F&I managers or dealer owners can record lender submissions.";
    }
    return `Server returned ${err.status}.`;
  }
  return "Failed to record the lender submission.";
}

function humanizeProgramsError(err: unknown): string {
  if (err instanceof ApiError && err.status === 403) {
    return "Only F&I managers or dealer owners can view lender programs.";
  }
  return "Failed to load lender programs.";
}

export function LenderSubmissionRecordForm({
  dealStructureId,
  onRecorded,
  onCancel,
  fetchPrograms = listLenderPrograms,
  submit = recordLenderSubmission,
}: LenderSubmissionRecordFormProps) {
  const [programs, setPrograms] = useState<
    LenderProgramSelectorProjection[]
  >([]);
  const [programsLoadState, setProgramsLoadState] =
    useState<LoadState>("loading");
  const [programsError, setProgramsError] = useState<string | null>(null);
  const [selectedProgramId, setSelectedProgramId] = useState<number | "">(
    "",
  );
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setProgramsLoadState("loading");
    setProgramsError(null);
    fetchPrograms()
      .then((rows) => {
        if (cancelled) return;
        setPrograms(rows);
        setProgramsLoadState("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setProgramsError(humanizeProgramsError(err));
        setProgramsLoadState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [fetchPrograms]);

  const missingReasons = useMemo(() => {
    const reasons: string[] = [];
    if (programsLoadState !== "ready") {
      reasons.push("Wait for the lender program list to load.");
    }
    if (selectedProgramId === "") {
      reasons.push("Choose the lender program the submission went to.");
    }
    return reasons;
  }, [programsLoadState, selectedProgramId]);

  const canSubmit = missingReasons.length === 0 && !submitting;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit || selectedProgramId === "") return;
    setSubmitting(true);
    setError(null);
    const payload: RecordLenderSubmissionRequest = {
      deal_structure_id: dealStructureId,
      lender_program_id: selectedProgramId,
    };
    if (notes.trim()) {
      payload.notes = notes.trim();
    }
    try {
      const submission = await submit(payload);
      onRecorded(submission);
    } catch (err) {
      setError(humanizeError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      data-testid="lender-submission-record-form"
      className="space-y-4"
    >
      <div>
        <h3 className="text-lg font-semibold">Record lender submission</h3>
        <p className="text-sm text-muted-foreground">
          Record which lender program the structured deal was submitted
          to. The response is recorded separately once the lender
          replies.
        </p>
      </div>

      {programsLoadState === "loading" && (
        <p
          className="text-sm text-muted-foreground"
          data-testid="lender-programs-loading"
        >
          Loading lender programs…
        </p>
      )}

      {programsLoadState === "error" && (
        <p
          className="text-sm text-destructive"
          data-testid="lender-programs-error"
          role="alert"
        >
          {programsError}
        </p>
      )}

      {programsLoadState === "ready" && programs.length === 0 && (
        <p
          className="text-sm text-muted-foreground"
          data-testid="lender-programs-empty"
        >
          No active lender programs are configured for this dealership.
          Ask the dealer owner to add a lender program before recording
          submissions.
        </p>
      )}

      {programsLoadState === "ready" && programs.length > 0 && (
        <label className="flex flex-col text-sm">
          <span className="mb-1 font-medium">Lender program</span>
          <select
            data-testid="lender-submission-program-select"
            aria-label="Lender program"
            value={selectedProgramId}
            onChange={(event) => {
              const value = event.target.value;
              setSelectedProgramId(value === "" ? "" : Number(value));
            }}
            className="rounded border border-input bg-background px-3 py-2"
          >
            <option value="">Choose a lender program…</option>
            {programs.map((program) => (
              <option key={program.id} value={program.id}>
                {program.name}
              </option>
            ))}
          </select>
        </label>
      )}

      <label className="flex flex-col text-sm">
        <span className="mb-1 font-medium">Notes (optional)</span>
        <Input
          data-testid="lender-submission-notes"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          placeholder="Anything to remember about this submission"
        />
      </label>

      {missingReasons.length > 0 && (
        <ul
          className="text-xs text-muted-foreground"
          data-testid="lender-submission-missing-reasons"
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
          data-testid="lender-submission-error"
        >
          {error}
        </p>
      )}

      <div className="flex items-center gap-2">
        <Button
          type="submit"
          disabled={!canSubmit}
          data-testid="lender-submission-record-submit"
        >
          Record submission
        </Button>
        {onCancel && (
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            data-testid="lender-submission-record-cancel"
          >
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
