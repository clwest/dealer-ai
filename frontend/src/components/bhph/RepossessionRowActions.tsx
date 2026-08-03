// Milestone 21 · Increment 2 (SESSION_168) — repossession row actions.
//
// Bundles MarkRecoveredButton + MarkReIntakedButton for a single
// Repossession row. State machine (M12.6):
//
//   ordered → recovered → re_intaked
//
// Mark-recovered captures the recovery timestamp + location.
// Mark-re-intaked requires a ConditionReport reference; the operator
// enters the report ID directly (creating the ConditionReport lives
// in the M3 recon workflow and is out of scope for M21.2).

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/authFetch";
import {
  markRepossessionRecovered,
  markRepossessionReIntaked,
  type RepossessionProjection,
} from "@/lib/bhphApi";

function humanizeMarkRecoveredError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return "Repossession is already recovered / re-intaked.";
    if (err.status === 404) return "Repossession not found. Refresh the page.";
    if (err.status === 400) return "Invalid recovery details.";
    return `Server returned ${err.status}.`;
  }
  return "Failed to mark recovered.";
}

function humanizeMarkReIntakedError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return "Repossession is not in a re-intake-eligible state.";
    if (err.status === 404) return "Repossession or condition report not found.";
    if (err.status === 400)
      return "Condition report is not scoped to this dealership. Enter a valid ID.";
    return `Server returned ${err.status}.`;
  }
  return "Failed to mark re-intaked.";
}

function nowLocalDatetimeInput(): string {
  const now = new Date();
  const tzOffsetMinutes = now.getTimezoneOffset();
  const local = new Date(now.getTime() - tzOffsetMinutes * 60_000);
  return local.toISOString().slice(0, 16);
}

export interface MarkRecoveredButtonProps {
  repossession: RepossessionProjection;
  onMarked: (repo: RepossessionProjection) => void;
}

export function MarkRecoveredButton({
  repossession,
  onMarked,
}: MarkRecoveredButtonProps) {
  const [open, setOpen] = useState(false);
  const [recoveredAt, setRecoveredAt] = useState<string>(nowLocalDatetimeInput());
  const [location, setLocation] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const disabled = repossession.state !== "ordered";

  async function onConfirm() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await markRepossessionRecovered(repossession.id, {
        recovered_at: new Date(recoveredAt).toISOString(),
        recovery_location: location.trim() || undefined,
        notes: notes.trim() || undefined,
      });
      onMarked(res.repossession);
      setOpen(false);
      setLocation("");
      setNotes("");
    } catch (err) {
      setError(humanizeMarkRecoveredError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        disabled={disabled || submitting}
        data-testid={`mark-recovered-button-${repossession.id}`}
      >
        Mark recovered
      </Button>
      <Dialog open={open} onOpenChange={(v) => (!v ? setOpen(false) : null)}>
        <DialogContent data-testid={`mark-recovered-modal-${repossession.id}`}>
          <DialogHeader>
            <DialogTitle>Mark repossession recovered</DialogTitle>
          </DialogHeader>
          <label className="flex flex-col gap-1 text-xs">
            Recovered at
            <Input
              type="datetime-local"
              value={recoveredAt}
              onChange={(e) => setRecoveredAt(e.target.value)}
              data-testid={`mark-recovered-at-${repossession.id}`}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs">
            Recovery location
            <Input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. borrower home, storage lot address"
              data-testid={`mark-recovered-location-${repossession.id}`}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs">
            Notes (optional)
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              data-testid={`mark-recovered-notes-${repossession.id}`}
            />
          </label>
          {error ? (
            <p className="text-sm text-destructive">{error}</p>
          ) : null}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setOpen(false);
                setError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={onConfirm}
              disabled={submitting}
              data-testid={`mark-recovered-confirm-${repossession.id}`}
            >
              {submitting ? "Marking…" : "Mark recovered"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export interface MarkReIntakedButtonProps {
  repossession: RepossessionProjection;
  onMarked: (repo: RepossessionProjection) => void;
}

export function MarkReIntakedButton({
  repossession,
  onMarked,
}: MarkReIntakedButtonProps) {
  const [open, setOpen] = useState(false);
  const [conditionReportId, setConditionReportId] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const disabled = repossession.state !== "recovered";

  async function onConfirm() {
    const parsed = Number(conditionReportId);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError("Enter a valid ConditionReport ID.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await markRepossessionReIntaked(repossession.id, {
        condition_report_id: parsed,
        notes: notes.trim() || undefined,
      });
      onMarked(res.repossession);
      setOpen(false);
      setConditionReportId("");
      setNotes("");
    } catch (err) {
      setError(humanizeMarkReIntakedError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        disabled={disabled || submitting}
        data-testid={`mark-re-intaked-button-${repossession.id}`}
      >
        Mark re-intaked
      </Button>
      <Dialog open={open} onOpenChange={(v) => (!v ? setOpen(false) : null)}>
        <DialogContent data-testid={`mark-re-intaked-modal-${repossession.id}`}>
          <DialogHeader>
            <DialogTitle>Mark repossession re-intaked</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Re-intake requires a completed intake ConditionReport for the
            recovered vehicle. Create the report via the recon workflow
            first, then enter its ID here.
          </p>
          <label className="flex flex-col gap-1 text-xs">
            ConditionReport ID
            <Input
              type="number"
              min="1"
              step="1"
              value={conditionReportId}
              onChange={(e) => setConditionReportId(e.target.value)}
              placeholder="e.g. 42"
              data-testid={`mark-re-intaked-report-id-${repossession.id}`}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs">
            Notes (optional)
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              data-testid={`mark-re-intaked-notes-${repossession.id}`}
            />
          </label>
          {error ? (
            <p className="text-sm text-destructive">{error}</p>
          ) : null}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setOpen(false);
                setError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={onConfirm}
              disabled={submitting}
              data-testid={`mark-re-intaked-confirm-${repossession.id}`}
            >
              {submitting ? "Marking…" : "Mark re-intaked"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
