// Milestone 27 · Increment 2 (SESSION_193) — journal-entry create dialog.
//
// Attached to the existing AccountingJournalEntriesPage as a modal
// dialog per M27.0 §5.b substrate-attachment rule (no new frontend
// route; the JE list page is the canonical origination context).
// Reuses the M14.4 reversal-dialog pattern from
// AccountingJournalEntryDetailPage: shadcn Dialog + Textarea +
// Button + local form state + inline error banner + M25.2 durable
// "modal-attached + success badge > toast" success flow.
//
// Client-side validation blocks submit unless all four hold:
//   1. Description is non-empty (trimmed).
//   2. Every line has an account picked.
//   3. Every line has non-zero on exactly one side (debit XOR credit).
//   4. Σ debits === Σ credits (balanced).
// Balance indicator badge in the footer surfaces the delta in real
// time so operators see the balance shift as they type.

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  createJournalEntry,
  type CreateJournalEntryPayload,
  type GLAccount,
  type JournalEntry,
} from "@/lib/accountingApi";

import { GLAccountPicker } from "./GLAccountPicker";


interface LineDraft {
  key: string;
  account_id: number | null;
  debit: string;
  credit: string;
  memo: string;
}


function newLineDraft(): LineDraft {
  return {
    key: crypto.randomUUID(),
    account_id: null,
    debit: "",
    credit: "",
    memo: "",
  };
}


/**
 * Optional pre-populate seed for the dialog. When supplied, dialog
 * fields are initialized from these values on each open transition.
 * Introduced at M28.2 (SESSION_196) for the template-instantiate flow —
 * clicking "Instantiate" on a template row builds an object of this
 * shape and passes it to a second controlled mount of the dialog.
 */
export interface NewJournalEntryInitialValues {
  description: string;
  /** ISO YYYY-MM-DD. Defaults to today if omitted. */
  postedAt?: string;
  lines: Array<{
    account_id: number;
    /** Decimal-as-string. Zero when this line's amount lands on the
     * opposite side. */
    debit: string;
    credit: string;
    memo: string;
  }>;
}


function draftFromInitialValues(
  initial: NewJournalEntryInitialValues,
): LineDraft[] {
  if (initial.lines.length === 0) return [newLineDraft(), newLineDraft()];
  return initial.lines.map((line) => ({
    key: crypto.randomUUID(),
    account_id: line.account_id,
    debit: line.debit,
    credit: line.credit,
    memo: line.memo,
  }));
}


function todayIsoDate(): string {
  // Returns YYYY-MM-DD in the operator's local timezone. The backend
  // JournalEntryCreateRequestSerializer accepts ISO 8601 date or
  // datetime; date-only lands as midnight local on the server after
  // DRF's field parser.
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}


function parseMoney(raw: string): number {
  if (!raw.trim()) return 0;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : NaN;
}


export interface NewJournalEntryDialogProps {
  accounts: GLAccount[];
  onCreated: (entry: JournalEntry) => void;
  disabled?: boolean;
  /** Controlled-open mode. When both ``open`` and ``onOpenChange``
   * are supplied, they override the internal open state (used by the
   * M28.2 template Instantiate flow). Uncontrolled behavior — the
   * built-in "+ New journal entry" trigger button plus internal open
   * state — is preserved when omitted. */
  open?: boolean;
  onOpenChange?: (next: boolean) => void;
  /** Optional pre-populate seed applied on each open transition. Used
   * by the M28.2 template Instantiate flow to open the dialog with a
   * template's description + lines already filled in. */
  initialValues?: NewJournalEntryInitialValues;
  /** When true, the built-in "+ New journal entry" trigger button is
   * not rendered. Used by controlled mounts that trigger opening
   * externally. Defaults to false (backward-compatible). */
  hideTrigger?: boolean;
}


export function NewJournalEntryDialog({
  accounts,
  onCreated,
  disabled = false,
  open: controlledOpen,
  onOpenChange: controlledOnOpenChange,
  initialValues,
  hideTrigger = false,
}: NewJournalEntryDialogProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const isControlled =
    controlledOpen !== undefined && controlledOnOpenChange !== undefined;
  const open = isControlled ? (controlledOpen as boolean) : internalOpen;
  const setOpen = (next: boolean) => {
    if (isControlled) {
      (controlledOnOpenChange as (n: boolean) => void)(next);
    } else {
      setInternalOpen(next);
    }
  };

  const initialDescription = initialValues?.description ?? "";
  const initialPostedAt = initialValues?.postedAt ?? todayIsoDate();
  const initialLines = (): LineDraft[] =>
    initialValues
      ? draftFromInitialValues(initialValues)
      : [newLineDraft(), newLineDraft()];

  const [description, setDescription] = useState(initialDescription);
  const [postedAt, setPostedAt] = useState(initialPostedAt);
  const [lines, setLines] = useState<LineDraft[]>(initialLines);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Re-seed fields on each open transition so re-opening a fresh
  // dialog (either blank or from a different template) starts from a
  // clean state derived from the current ``initialValues``.
  const prevOpen = useRef(open);
  useEffect(() => {
    if (open && !prevOpen.current) {
      setDescription(initialValues?.description ?? "");
      setPostedAt(initialValues?.postedAt ?? todayIsoDate());
      setLines(
        initialValues
          ? draftFromInitialValues(initialValues)
          : [newLineDraft(), newLineDraft()],
      );
      setError(null);
      setSubmitting(false);
    }
    prevOpen.current = open;
  }, [open, initialValues]);

  const trimmedDescription = description.trim();
  const descriptionInvalid = trimmedDescription.length === 0;

  const parsedLines = lines.map((line) => ({
    key: line.key,
    account_id: line.account_id,
    debit: parseMoney(line.debit),
    credit: parseMoney(line.credit),
    memo: line.memo,
  }));

  const hasInvalidNumber = parsedLines.some(
    (line) => Number.isNaN(line.debit) || Number.isNaN(line.credit),
  );
  const missingAccount = parsedLines.some(
    (line) => line.account_id === null,
  );
  const oneSidedInvalid = parsedLines.some((line) => {
    const debitNonZero = line.debit > 0;
    const creditNonZero = line.credit > 0;
    // Exactly-one-side rule: not both, not neither.
    return debitNonZero === creditNonZero;
  });
  const totalDebit = parsedLines.reduce(
    (sum, line) => sum + (Number.isFinite(line.debit) ? line.debit : 0),
    0,
  );
  const totalCredit = parsedLines.reduce(
    (sum, line) => sum + (Number.isFinite(line.credit) ? line.credit : 0),
    0,
  );
  const balanceDelta = Math.round((totalDebit - totalCredit) * 100) / 100;
  const isBalanced = balanceDelta === 0 && totalDebit > 0;

  const canSubmit =
    !descriptionInvalid &&
    !hasInvalidNumber &&
    !missingAccount &&
    !oneSidedInvalid &&
    isBalanced &&
    !submitting;

  function reset() {
    setDescription(initialValues?.description ?? "");
    setPostedAt(initialValues?.postedAt ?? todayIsoDate());
    setLines(
      initialValues
        ? draftFromInitialValues(initialValues)
        : [newLineDraft(), newLineDraft()],
    );
    setError(null);
    setSubmitting(false);
  }

  function updateLine(key: string, patch: Partial<LineDraft>) {
    setLines((current) =>
      current.map((line) =>
        line.key === key ? { ...line, ...patch } : line,
      ),
    );
  }

  function addLine() {
    setLines((current) => [...current, newLineDraft()]);
  }

  function removeLine(key: string) {
    setLines((current) =>
      current.length <= 2
        ? current
        : current.filter((line) => line.key !== key),
    );
  }

  async function handleSubmit() {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    const payload: CreateJournalEntryPayload = {
      description: trimmedDescription,
      posted_at: postedAt || undefined,
      lines: parsedLines.map((line) => ({
        // Non-null asserted; missingAccount guard above forbids null.
        account_id: line.account_id as number,
        debit: (line.debit || 0).toFixed(2),
        credit: (line.credit || 0).toFixed(2),
        memo: line.memo,
      })),
    };
    try {
      const entry = await createJournalEntry(payload);
      setOpen(false);
      reset();
      onCreated(entry);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      {!hideTrigger && (
        <Button
          variant="default"
          size="sm"
          disabled={disabled || accounts.length < 2}
          onClick={() => setOpen(true)}
        >
          + New journal entry
        </Button>
      )}
      <DialogContent className="flex max-h-[90vh] max-w-3xl flex-col">
        <DialogHeader>
          <DialogTitle>New journal entry</DialogTitle>
          <DialogDescription>
            Post a balanced entry to the general ledger. Debits and
            credits must sum to the same amount; the entry appears in
            the list immediately on success.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-1 flex-col gap-4 overflow-y-auto pr-1">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">
              Description <span className="text-destructive">*</span>
            </span>
            <Textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What is this entry for? (visible in the JE list)"
              rows={2}
              aria-required
              aria-invalid={descriptionInvalid}
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">Posted at</span>
            <Input
              type="date"
              value={postedAt}
              onChange={(event) => setPostedAt(event.target.value)}
              aria-label="Posted at"
            />
            <span className="text-xs text-muted-foreground">
              Defaults to today.
            </span>
          </label>

          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Lines</span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addLine}
                disabled={submitting}
              >
                + Add line
              </Button>
            </div>

            <div className="flex flex-col gap-3">
              {lines.map((line, index) => (
                <LineRow
                  key={line.key}
                  index={index}
                  line={line}
                  accounts={accounts}
                  canRemove={lines.length > 2}
                  disabled={submitting}
                  onChange={(patch) => updateLine(line.key, patch)}
                  onRemove={() => removeLine(line.key)}
                />
              ))}
            </div>
          </div>

          <BalanceIndicator
            totalDebit={totalDebit}
            totalCredit={totalCredit}
            balanceDelta={balanceDelta}
            isBalanced={isBalanced}
          />

          {error && (
            <p
              className="text-sm text-destructive"
              role="alert"
              data-testid="je-create-error"
            >
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!canSubmit}
            data-testid="je-create-submit"
          >
            {submitting ? "Posting…" : "Create journal entry"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


function LineRow({
  index,
  line,
  accounts,
  canRemove,
  disabled,
  onChange,
  onRemove,
}: {
  index: number;
  line: LineDraft;
  accounts: GLAccount[];
  canRemove: boolean;
  disabled: boolean;
  onChange: (patch: Partial<LineDraft>) => void;
  onRemove: () => void;
}) {
  const labelId = `je-line-${line.key}-label`;
  return (
    <div
      className="flex flex-col gap-2 rounded-md border border-border p-3"
      data-testid={`je-line-${index}`}
    >
      <div className="flex items-center justify-between">
        <span id={labelId} className="text-xs font-medium uppercase text-muted-foreground">
          Line {index + 1}
        </span>
        {canRemove && (
          <button
            type="button"
            className="text-xs text-muted-foreground underline"
            disabled={disabled}
            onClick={onRemove}
          >
            − Remove
          </button>
        )}
      </div>
      <GLAccountPicker
        accounts={accounts}
        value={line.account_id}
        onChange={(id) => onChange({ account_id: id })}
        disabled={disabled}
        labelledBy={labelId}
      />
      <div className="grid grid-cols-2 gap-2">
        <label className="flex flex-col gap-1 text-xs">
          <span className="text-muted-foreground">Debit</span>
          <Input
            type="number"
            inputMode="decimal"
            step="0.01"
            min="0"
            value={line.debit}
            onChange={(event) => onChange({ debit: event.target.value })}
            disabled={disabled}
            aria-label={`Line ${index + 1} debit`}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span className="text-muted-foreground">Credit</span>
          <Input
            type="number"
            inputMode="decimal"
            step="0.01"
            min="0"
            value={line.credit}
            onChange={(event) => onChange({ credit: event.target.value })}
            disabled={disabled}
            aria-label={`Line ${index + 1} credit`}
          />
        </label>
      </div>
      <label className="flex flex-col gap-1 text-xs">
        <span className="text-muted-foreground">Memo (optional)</span>
        <Input
          type="text"
          value={line.memo}
          onChange={(event) => onChange({ memo: event.target.value })}
          disabled={disabled}
          aria-label={`Line ${index + 1} memo`}
        />
      </label>
    </div>
  );
}


function BalanceIndicator({
  totalDebit,
  totalCredit,
  balanceDelta,
  isBalanced,
}: {
  totalDebit: number;
  totalCredit: number;
  balanceDelta: number;
  isBalanced: boolean;
}) {
  const debit = totalDebit.toFixed(2);
  const credit = totalCredit.toFixed(2);
  const delta = Math.abs(balanceDelta).toFixed(2);

  return (
    <div
      className="flex items-center justify-between rounded-md border border-border bg-muted/30 px-3 py-2 text-sm"
      role="status"
      data-testid="je-create-balance-indicator"
    >
      <span className="tabular-nums text-muted-foreground">
        Debits ${debit} · Credits ${credit}
      </span>
      {isBalanced ? (
        <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
          Balanced
        </span>
      ) : (
        <span className="rounded-md bg-destructive/15 px-2 py-0.5 text-xs font-medium text-destructive">
          {totalDebit === 0 && totalCredit === 0
            ? "Enter amounts"
            : `Unbalanced by $${delta}`}
        </span>
      )}
    </div>
  );
}
