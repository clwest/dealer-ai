// Milestone 28 · Increment 2 (SESSION_196) — journal-entry template create dialog.
//
// Peer of the M27.2 NewJournalEntryDialog. Persists a *recipe* (name +
// description + lines with side + amount) via the M28.1
// createJournalEntryTemplate wrapper. Templates are recipes, not
// postings — no posted_at field, no reversal semantics.
//
// Reuses the M27.2 GLAccountPicker verbatim + the same viewport-
// constraint dialog pattern (max-h-[90vh] flex-col + scrollable inner
// body + fixed footer) so a template with many lines stays operable
// on 1280×720 screens.
//
// Client-side validation blocks submit unless:
//   1. Name is non-empty (trimmed).
//   2. Description is non-empty (trimmed).
//   3. Every line has an account picked.
//   4. Every line has chosen side (debit or credit).
//   5. Every line has positive amount > 0.
//   6. Σ debit-side amounts === Σ credit-side amounts (balanced).

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
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  createJournalEntryTemplate,
  type CreateJournalEntryTemplatePayload,
  type GLAccount,
  type JournalEntryTemplate,
  type JournalEntryTemplateLineSide,
} from "@/lib/accountingApi";

import { GLAccountPicker } from "./GLAccountPicker";


interface TemplateLineDraft {
  key: string;
  account_id: number | null;
  side: JournalEntryTemplateLineSide;
  amount: string;
  memo: string;
}


function newTemplateLineDraft(
  side: JournalEntryTemplateLineSide = "debit",
): TemplateLineDraft {
  return {
    key: crypto.randomUUID(),
    account_id: null,
    side,
    amount: "",
    memo: "",
  };
}


function parseMoney(raw: string): number {
  if (!raw.trim()) return 0;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : NaN;
}


export interface NewJournalEntryTemplateDialogProps {
  accounts: GLAccount[];
  onCreated: (template: JournalEntryTemplate) => void;
  disabled?: boolean;
}


export function NewJournalEntryTemplateDialog({
  accounts,
  onCreated,
  disabled = false,
}: NewJournalEntryTemplateDialogProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [lines, setLines] = useState<TemplateLineDraft[]>(() => [
    newTemplateLineDraft("debit"),
    newTemplateLineDraft("credit"),
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmedName = name.trim();
  const trimmedDescription = description.trim();
  const nameInvalid = trimmedName.length === 0;
  const descriptionInvalid = trimmedDescription.length === 0;

  const parsedLines = lines.map((line) => ({
    key: line.key,
    account_id: line.account_id,
    side: line.side,
    amount: parseMoney(line.amount),
    memo: line.memo,
  }));

  const hasInvalidNumber = parsedLines.some((line) =>
    Number.isNaN(line.amount),
  );
  const missingAccount = parsedLines.some(
    (line) => line.account_id === null,
  );
  const missingAmount = parsedLines.some((line) => line.amount <= 0);

  const totalDebit = parsedLines
    .filter((line) => line.side === "debit")
    .reduce((sum, line) => sum + (line.amount || 0), 0);
  const totalCredit = parsedLines
    .filter((line) => line.side === "credit")
    .reduce((sum, line) => sum + (line.amount || 0), 0);
  const balanceDelta = Math.round((totalDebit - totalCredit) * 100) / 100;
  const isBalanced = balanceDelta === 0 && totalDebit > 0;

  const canSubmit =
    !nameInvalid &&
    !descriptionInvalid &&
    !hasInvalidNumber &&
    !missingAccount &&
    !missingAmount &&
    isBalanced &&
    !submitting;

  function reset() {
    setName("");
    setDescription("");
    setLines([
      newTemplateLineDraft("debit"),
      newTemplateLineDraft("credit"),
    ]);
    setError(null);
    setSubmitting(false);
  }

  function updateLine(key: string, patch: Partial<TemplateLineDraft>) {
    setLines((current) =>
      current.map((line) =>
        line.key === key ? { ...line, ...patch } : line,
      ),
    );
  }

  function addLine() {
    setLines((current) => [...current, newTemplateLineDraft("debit")]);
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
    const payload: CreateJournalEntryTemplatePayload = {
      name: trimmedName,
      description: trimmedDescription,
      lines: parsedLines.map((line) => ({
        account_id: line.account_id as number,
        side: line.side,
        amount: (line.amount || 0).toFixed(2),
        memo: line.memo,
      })),
    };
    try {
      const template = await createJournalEntryTemplate(payload);
      setOpen(false);
      reset();
      onCreated(template);
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
      <Button
        variant="outline"
        size="sm"
        disabled={disabled || accounts.length < 2}
        onClick={() => setOpen(true)}
        data-testid="tmpl-create-trigger"
      >
        + New template
      </Button>
      <DialogContent className="flex max-h-[90vh] max-w-3xl flex-col">
        <DialogHeader>
          <DialogTitle>New recurring template</DialogTitle>
          <DialogDescription>
            Save a reusable journal-entry recipe. Debit-side and
            credit-side amounts must balance. You can instantiate this
            template into a new journal entry later.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-1 flex-col gap-4 overflow-y-auto pr-1">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">
              Name <span className="text-destructive">*</span>
            </span>
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. Monthly rent"
              aria-required
              aria-invalid={nameInvalid}
              data-testid="tmpl-name-input"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">
              Description <span className="text-destructive">*</span>
            </span>
            <Textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Default description applied when this template is instantiated."
              rows={2}
              aria-required
              aria-invalid={descriptionInvalid}
              data-testid="tmpl-description-input"
            />
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
                <TemplateLineRow
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

          <TemplateBalanceIndicator
            totalDebit={totalDebit}
            totalCredit={totalCredit}
            balanceDelta={balanceDelta}
            isBalanced={isBalanced}
          />

          {error && (
            <p
              className="text-sm text-destructive"
              role="alert"
              data-testid="tmpl-create-error"
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
            data-testid="tmpl-create-submit"
          >
            {submitting ? "Saving…" : "Save template"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


function TemplateLineRow({
  index,
  line,
  accounts,
  canRemove,
  disabled,
  onChange,
  onRemove,
}: {
  index: number;
  line: TemplateLineDraft;
  accounts: GLAccount[];
  canRemove: boolean;
  disabled: boolean;
  onChange: (patch: Partial<TemplateLineDraft>) => void;
  onRemove: () => void;
}) {
  const labelId = `tmpl-line-${line.key}-label`;
  return (
    <div
      className="flex flex-col gap-2 rounded-md border border-border p-3"
      data-testid={`tmpl-line-${index}`}
    >
      <div className="flex items-center justify-between">
        <span
          id={labelId}
          className="text-xs font-medium uppercase text-muted-foreground"
        >
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
          <span className="text-muted-foreground">Side</span>
          <select
            value={line.side}
            onChange={(event) =>
              onChange({
                side: event.target.value as JournalEntryTemplateLineSide,
              })
            }
            disabled={disabled}
            aria-label={`Line ${index + 1} side`}
            data-testid={`tmpl-line-${index}-side`}
            className="h-9 rounded-md border border-input bg-transparent px-2 text-sm shadow-sm"
          >
            <option value="debit">Debit</option>
            <option value="credit">Credit</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span className="text-muted-foreground">Amount</span>
          <Input
            type="number"
            inputMode="decimal"
            step="0.01"
            min="0"
            value={line.amount}
            onChange={(event) => onChange({ amount: event.target.value })}
            disabled={disabled}
            aria-label={`Line ${index + 1} amount`}
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


function TemplateBalanceIndicator({
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
      data-testid="tmpl-create-balance-indicator"
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
