// Milestone 32 · Increment 2 (SESSION_208) — writeup Approve + Hand-off
// confirmation dialogs.
//
// Per MILESTONE_32_PLANNING.md §5.b D5 (approve copy — state-machine-
// truthful; no false re-approval advertisement) + D6 (hand-off copy
// — irreversibility flagged verbatim).
//
// Two small co-located dialog components. Kept together in this file
// because both:
//   - operate on a DealWriteup pk;
//   - render the same confirmation shell (title + body + Cancel +
//     primary action);
//   - are consumed only by LeadDetailModal's Writeups section.
//
// Per M28.0 `feedback_duplicate_small_stable_logic.md` lesson:
// duplicate small stable dialog logic rather than extracting to a
// shared abstraction. The two dialogs share render shape but their
// copy + action semantics differ meaningfully — they are not
// candidates for a shared helper.

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ApiError } from "@/lib/authFetch";
import {
  approveDealWriteup,
  handOffDealWriteup,
  type DealWriteupProjection,
} from "@/lib/salesApi";

// ---------------------------------------------------------------------------
// Approve confirmation (D5-revised copy)
// ---------------------------------------------------------------------------

export interface WriteupApproveConfirmDialogProps {
  writeup: DealWriteupProjection;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onApproved: (writeup: DealWriteupProjection) => void;
  /** Injected for tests. */
  submit?: typeof approveDealWriteup;
}

export function WriteupApproveConfirmDialog({
  writeup,
  open,
  onOpenChange,
  onApproved,
  submit = approveDealWriteup,
}: WriteupApproveConfirmDialogProps) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleApprove() {
    setSubmitting(true);
    setError(null);
    try {
      const updated = await submit(writeup.id);
      onApproved(updated);
      onOpenChange(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError("Writeup not found. It may have been deleted.");
      } else if (err instanceof ApiError && err.status === 403) {
        setError("Only sales managers or dealer owners can approve.");
      } else {
        setError("Failed to approve. Try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="writeup-approve-confirm-body">
        <DialogHeader>
          <DialogTitle>Approve deal writeup?</DialogTitle>
          <DialogDescription>
            Approving marks this writeup ready for F&amp;I hand-off. Review
            the terms carefully before continuing. After it is sent to
            F&amp;I, the hand-off cannot be repeated or undone.
          </DialogDescription>
        </DialogHeader>
        {error ? (
          <p
            role="alert"
            className="text-xs text-destructive"
            data-testid="writeup-approve-error"
          >
            {error}
          </p>
        ) : null}
        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
            data-testid="writeup-approve-cancel"
          >
            Cancel
          </Button>
          <Button
            onClick={handleApprove}
            disabled={submitting}
            data-testid="writeup-approve-submit"
          >
            {submitting ? "Approving…" : "Approve"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Hand-off confirmation (D6 irreversibility copy)
// ---------------------------------------------------------------------------

export interface WriteupHandoffConfirmDialogProps {
  writeup: DealWriteupProjection;
  leadName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onHandedOff: (writeup: DealWriteupProjection) => void;
  /** Injected for tests. */
  submit?: typeof handOffDealWriteup;
}

export function WriteupHandoffConfirmDialog({
  writeup,
  leadName,
  open,
  onOpenChange,
  onHandedOff,
  submit = handOffDealWriteup,
}: WriteupHandoffConfirmDialogProps) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await submit(writeup.id);
      onHandedOff(res.deal_writeup);
      onOpenChange(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError(
          "This writeup has already been handed off to F&I. Refresh the list to see the current state.",
        );
      } else if (err instanceof ApiError && err.status === 404) {
        setError("Writeup not found. It may have been deleted.");
      } else if (err instanceof ApiError && err.status === 403) {
        setError("Only sales managers or dealer owners can hand off writeups.");
      } else {
        setError("Failed to send to F&I. Try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="writeup-handoff-confirm-body">
        <DialogHeader>
          <DialogTitle>Send to F&amp;I?</DialogTitle>
          <DialogDescription>
            This creates a credit application for{" "}
            <span className="font-semibold">{leadName}</span> and hands off
            to F&amp;I. <strong>This cannot be undone</strong> — a second
            attempt will be refused to protect against duplicate
            applications and their retention-clock consequences. Continue?
          </DialogDescription>
        </DialogHeader>
        {error ? (
          <p
            role="alert"
            className="text-xs text-destructive"
            data-testid="writeup-handoff-error"
          >
            {error}
          </p>
        ) : null}
        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
            data-testid="writeup-handoff-cancel"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting}
            data-testid="writeup-handoff-submit"
          >
            {submitting ? "Sending…" : "Send to F&I"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
