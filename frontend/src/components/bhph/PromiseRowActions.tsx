// Milestone 21 · Increment 2 (SESSION_168) — promise row actions.
//
// Bundles MarkKeptPromiseButton (with payment picker) + MarkBrokenPromiseButton
// for a single BhphPromiseToPay row. Buttons are disabled when the
// promise is already in a terminal state.
//
// Mark-kept requires a payment reference per M12.4 §5.d Option A
// operator-triggered reconciliation. The picker lists the note's
// payments so the collector can attribute the promise to a specific
// receipt.

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/authFetch";
import {
  listBhphPayments,
  markPromiseBroken,
  markPromiseKept,
  type BhphPaymentProjection,
  type BhphPromiseProjection,
} from "@/lib/bhphApi";

function humanizeMarkKeptError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) return "Payment does not belong to this promise's note.";
    if (err.status === 404) return "Promise or payment not found. Refresh the page.";
    if (err.status === 409) return "Promise is already in a terminal state.";
    return `Server returned ${err.status}.`;
  }
  return "Failed to mark promise kept.";
}

function humanizeMarkBrokenError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return "Promise is already in a terminal state.";
    if (err.status === 404) return "Promise not found. Refresh the page.";
    return `Server returned ${err.status}.`;
  }
  return "Failed to mark promise broken.";
}

function formatMoney(raw: string): string {
  const amount = Number(raw);
  if (Number.isNaN(amount)) return `$${raw}`;
  return amount.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export interface PaymentPickerModalProps {
  open: boolean;
  notePk: number;
  onClose: () => void;
  onPick: (payment: BhphPaymentProjection) => void;
}

export function PaymentPickerModal({
  open,
  notePk,
  onClose,
  onPick,
}: PaymentPickerModalProps) {
  const [payments, setPayments] = useState<BhphPaymentProjection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    listBhphPayments(notePk)
      .then((res) => setPayments(res.results))
      .catch(() => setError("Failed to load payments."))
      .finally(() => setLoading(false));
  }, [open, notePk]);

  return (
    <Dialog open={open} onOpenChange={(v) => (!v ? onClose() : null)}>
      <DialogContent className="max-w-lg" data-testid="payment-picker-modal">
        <DialogHeader>
          <DialogTitle>Attribute promise to a payment</DialogTitle>
        </DialogHeader>
        <div className="max-h-80 overflow-y-auto">
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading payments…</p>
          ) : error ? (
            <p className="text-sm text-destructive">{error}</p>
          ) : payments.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No payments on file. Record a payment before marking kept.
            </p>
          ) : (
            <ul className="flex flex-col gap-1">
              {payments.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => onPick(p)}
                    className="w-full rounded border border-border px-3 py-2 text-left text-sm hover:bg-muted"
                    data-testid={`payment-picker-row-${p.id}`}
                  >
                    <span className="font-medium">
                      {formatMoney(p.amount)}
                    </span>{" "}
                    · {p.paid_at} · {p.method}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export interface MarkKeptPromiseButtonProps {
  notePk: number;
  promise: BhphPromiseProjection;
  onMarked: (promise: BhphPromiseProjection) => void;
}

export function MarkKeptPromiseButton({
  notePk,
  promise,
  onMarked,
}: MarkKeptPromiseButtonProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const disabled = promise.state !== "promised";

  async function handlePick(payment: BhphPaymentProjection) {
    setSubmitting(true);
    setError(null);
    try {
      const res = await markPromiseKept(promise.id, {
        bhph_payment_id: payment.id,
      });
      onMarked(res.bhph_promise);
      setPickerOpen(false);
    } catch (err) {
      setError(humanizeMarkKeptError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setPickerOpen(true)}
        disabled={disabled || submitting}
        data-testid={`mark-kept-button-${promise.id}`}
      >
        {submitting ? "Marking…" : "Mark kept"}
      </Button>
      {error ? (
        <span
          className="text-xs text-destructive"
          data-testid={`mark-kept-error-${promise.id}`}
        >
          {error}
        </span>
      ) : null}
      <PaymentPickerModal
        open={pickerOpen}
        notePk={notePk}
        onClose={() => {
          setPickerOpen(false);
          setError(null);
        }}
        onPick={handlePick}
      />
    </>
  );
}

export interface MarkBrokenPromiseButtonProps {
  promise: BhphPromiseProjection;
  onMarked: (promise: BhphPromiseProjection) => void;
}

export function MarkBrokenPromiseButton({
  promise,
  onMarked,
}: MarkBrokenPromiseButtonProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const disabled = promise.state !== "promised";

  async function onConfirm() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await markPromiseBroken(promise.id, {
        notes: notes.trim() || undefined,
      });
      onMarked(res.bhph_promise);
      setConfirmOpen(false);
      setNotes("");
    } catch (err) {
      setError(humanizeMarkBrokenError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setConfirmOpen(true)}
        disabled={disabled || submitting}
        data-testid={`mark-broken-button-${promise.id}`}
      >
        Mark broken
      </Button>
      <Dialog
        open={confirmOpen}
        onOpenChange={(v) => (!v ? setConfirmOpen(false) : null)}
      >
        <DialogContent data-testid={`mark-broken-modal-${promise.id}`}>
          <DialogHeader>
            <DialogTitle>Mark promise broken</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            The delinquency detector may already have fired; this action
            documents the operator-triggered decision with an optional
            reason.
          </p>
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Reason (optional)"
            rows={3}
            data-testid={`mark-broken-notes-${promise.id}`}
          />
          {error ? (
            <p className="text-sm text-destructive">{error}</p>
          ) : null}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setConfirmOpen(false);
                setError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={onConfirm}
              disabled={submitting}
              data-testid={`mark-broken-confirm-${promise.id}`}
            >
              {submitting ? "Marking…" : "Mark broken"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
