// Milestone 28 · Increment 2 (SESSION_196) — journal-entry template create dialog.
// Milestone 29 · Increment 2 (SESSION_199) — "Variable amount" checkbox.
// Milestone 30 · Increment 2 (SESSION_202) — additive-mode consolidation.
//
// Peer of the M27.2 NewJournalEntryDialog. Persists a *recipe* (name +
// description + lines with side + amount or variable-marker) via the
// M28.1 createJournalEntryTemplate wrapper OR the M30.1
// updateJournalEntryTemplate wrapper (mode-dependent). Templates are
// recipes, not postings — no posted_at field, no reversal semantics.
//
// Reuses the M27.2 GLAccountPicker verbatim + the same viewport-
// constraint dialog pattern (max-h-[90vh] flex-col + scrollable inner
// body + fixed footer) so a template with many lines stays operable
// on 1280×720 screens.
//
// M30.2 — additive-mode pattern re-application of M29.2 durable lesson
// (t). Optional ``mode?: "create" | "edit"`` (default ``"create"``)
// with safe defaults preserves the M29.2 create-mode behavior byte-
// identical. When ``mode === "edit"`` the caller supplies
// ``initialTemplate`` + ``onEdited`` and uses the controlled-open
// pair (``open`` + ``onOpenChange``) so a row-level trigger can
// programmatically open the dialog. Blank-baseline callers pass none
// of the M30.2 props and continue to see the baked-in
// ``+ New template`` trigger. See MILESTONE_30_PLANNING.md §5.b D2 +
// D4.
//
// Client-side validation blocks submit unless:
//   1. Name is non-empty (trimmed).
//   2. Description is non-empty (trimmed).
//   3. Every line has an account picked.
//   4. Every line has chosen side (debit or credit).
//   5. Every FIXED line (is_variable=false) has positive amount > 0.
//      Variable lines (is_variable=true) submit as amount: null and
//      skip the amount check — the operator supplies the amount at
//      instantiate time.
//   6. The populated (non-variable) portion balances:
//      Σ populated-debit === Σ populated-credit. Fully-variable
//      templates trivially balance (both sums zero — accepted, since
//      the M13.1 posting service will enforce full balance at
//      instantiate time).

import { useEffect, useState } from "react";

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
  updateJournalEntryTemplate,
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
  /** M29 — when true, submits as ``amount: null`` and the operator
   *  is prompted for the amount at instantiate time. */
  is_variable: boolean;
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
    is_variable: false,
  };
}


function parseMoney(raw: string): number {
  if (!raw.trim()) return 0;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : NaN;
}


/**
 * M30.2 — convert a saved template's line projection back into the
 * editable draft shape for edit-mode population. Mirrors the shape
 * ``newTemplateLineDraft`` returns; the ``key`` gets a fresh UUID
 * per line so React reconciles cleanly.
 */
function templateToDraftLines(
  template: JournalEntryTemplate,
): TemplateLineDraft[] {
  return template.lines.map((line) => ({
    key: crypto.randomUUID(),
    account_id: line.account_id,
    side: line.side,
    amount: line.amount ?? "",
    memo: line.memo,
    is_variable: line.amount === null,
  }));
}


export interface JournalEntryTemplateDialogProps {
  accounts: GLAccount[];
  disabled?: boolean;

  /** M30.2 — mode selector. Default ``"create"`` preserves M29.2
   *  behavior byte-identical (baked-in trigger + createJournalEntry
   *  Template on submit). ``"edit"`` requires ``initialTemplate`` +
   *  ``onEdited`` + controlled-open props. */
  mode?: "create" | "edit";

  /** M30.2 — populated on ``mode === "edit"``. Ignored in create
   *  mode. */
  initialTemplate?: JournalEntryTemplate;

  /** Fired after a successful create. Existing M28.2 prop. */
  onCreated?: (template: JournalEntryTemplate) => void;

  /** M30.2 — fired after a successful edit. Required when
   *  ``mode === "edit"``. */
  onEdited?: (template: JournalEntryTemplate) => void;

  /** M30.2 controlled-open pair. When both are supplied the baked-in
   *  trigger button is NOT rendered and the parent controls the open
   *  state (row-level trigger elsewhere). When absent (M29.2
   *  default), the baked-in ``+ New template`` button renders and
   *  controls its own open state. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}


export function JournalEntryTemplateDialog({
  accounts,
  disabled = false,
  mode = "create",
  initialTemplate,
  onCreated,
  onEdited,
  open: openProp,
  onOpenChange: onOpenChangeProp,
}: JournalEntryTemplateDialogProps) {
  // Controlled-open pattern: when both open + onOpenChange props are
  // supplied, parent controls state (baked-in trigger not rendered).
  // Otherwise the dialog manages its own open state (M29.2 default).
  const isControlled =
    openProp !== undefined && onOpenChangeProp !== undefined;
  const [openUncontrolled, setOpenUncontrolled] = useState(false);
  const open = isControlled ? openProp : openUncontrolled;
  const setOpen = (next: boolean) => {
    if (isControlled) {
      onOpenChangeProp?.(next);
    } else {
      setOpenUncontrolled(next);
    }
  };

  const isEditMode = mode === "edit";

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [lines, setLines] = useState<TemplateLineDraft[]>(() => [
    newTemplateLineDraft("debit"),
    newTemplateLineDraft("credit"),
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // M30.2 edit-mode population — on open transition or initialTemplate
  // reference change, hydrate the form fields from the template. In
  // create-mode this effect is a no-op (initialTemplate is undefined).
  useEffect(() => {
    if (!open || !isEditMode || !initialTemplate) return;
    setName(initialTemplate.name);
    setDescription(initialTemplate.description);
    setLines(templateToDraftLines(initialTemplate));
    setError(null);
    setSubmitting(false);
  }, [open, isEditMode, initialTemplate]);

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
    is_variable: line.is_variable,
  }));

  // Variable lines skip amount + number validation — they submit as
  // amount: null and the operator supplies the amount at instantiate
  // time.
  const hasInvalidNumber = parsedLines.some(
    (line) => !line.is_variable && Number.isNaN(line.amount),
  );
  const missingAccount = parsedLines.some(
    (line) => line.account_id === null,
  );
  const missingAmount = parsedLines.some(
    (line) => !line.is_variable && line.amount <= 0,
  );

  const hasVariableLine = parsedLines.some((line) => line.is_variable);
  const populatedLines = parsedLines.filter((line) => !line.is_variable);
  const totalDebit = populatedLines
    .filter((line) => line.side === "debit")
    .reduce((sum, line) => sum + (line.amount || 0), 0);
  const totalCredit = populatedLines
    .filter((line) => line.side === "credit")
    .reduce((sum, line) => sum + (line.amount || 0), 0);
  const balanceDelta = Math.round((totalDebit - totalCredit) * 100) / 100;
  // Populated portion must self-balance. Fully-variable templates
  // trivially pass (both sums zero). Fully-fixed templates preserve
  // M28.2 behavior (must have totalDebit > 0).
  const isBalanced = hasVariableLine
    ? balanceDelta === 0
    : balanceDelta === 0 && totalDebit > 0;

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
        amount: line.is_variable ? null : (line.amount || 0).toFixed(2),
        memo: line.memo,
      })),
    };
    try {
      if (isEditMode) {
        if (!initialTemplate) {
          throw new Error(
            "JournalEntryTemplateDialog: edit mode requires initialTemplate.",
          );
        }
        const template = await updateJournalEntryTemplate(
          initialTemplate.id,
          payload,
        );
        setOpen(false);
        reset();
        onEdited?.(template);
      } else {
        const template = await createJournalEntryTemplate(payload);
        setOpen(false);
        reset();
        onCreated?.(template);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  const dialogTitle = isEditMode ? "Edit template" : "New recurring template";
  const dialogDescription = isEditMode
    ? "Update the recipe. Debit-side and credit-side amounts must balance. Historical journal entries created from this template are not affected by edits."
    : "Save a reusable journal-entry recipe. Debit-side and credit-side amounts must balance. You can instantiate this template into a new journal entry later.";
  const submitLabel = submitting
    ? isEditMode
      ? "Saving…"
      : "Saving…"
    : isEditMode
      ? "Save changes"
      : "Save template";
  const submitTestId = isEditMode ? "tmpl-edit-submit" : "tmpl-create-submit";

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      {!isControlled && (
        <Button
          variant="outline"
          size="sm"
          disabled={disabled || accounts.length < 2}
          onClick={() => setOpen(true)}
          data-testid="tmpl-create-trigger"
        >
          + New template
        </Button>
      )}
      <DialogContent className="flex max-h-[90vh] max-w-3xl flex-col">
        <DialogHeader>
          <DialogTitle data-testid="tmpl-dialog-title">
            {dialogTitle}
          </DialogTitle>
          <DialogDescription>{dialogDescription}</DialogDescription>
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
            hasVariableLine={hasVariableLine}
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
            data-testid={submitTestId}
          >
            {submitLabel}
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
            value={line.is_variable ? "" : line.amount}
            onChange={(event) => onChange({ amount: event.target.value })}
            disabled={disabled || line.is_variable}
            placeholder={line.is_variable ? "Set at instantiate" : ""}
            aria-label={`Line ${index + 1} amount`}
            data-testid={`tmpl-line-${index}-amount`}
          />
        </label>
      </div>
      <label className="flex items-center gap-2 text-xs">
        <input
          type="checkbox"
          checked={line.is_variable}
          onChange={(event) =>
            onChange({
              is_variable: event.target.checked,
              // Clear the amount input when marking variable so a
              // stale populated value doesn't get re-marshaled if the
              // operator toggles back.
              ...(event.target.checked ? { amount: "" } : {}),
            })
          }
          disabled={disabled}
          aria-label={`Line ${index + 1} variable amount`}
          data-testid={`tmpl-line-${index}-variable`}
        />
        <span className="text-muted-foreground">
          Variable amount (supplied at instantiate)
        </span>
      </label>
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
  hasVariableLine,
}: {
  totalDebit: number;
  totalCredit: number;
  balanceDelta: number;
  isBalanced: boolean;
  hasVariableLine: boolean;
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
        {hasVariableLine
          ? `Populated debits $${debit} · Populated credits $${credit}`
          : `Debits $${debit} · Credits $${credit}`}
      </span>
      {isBalanced ? (
        hasVariableLine ? (
          <span
            className="rounded-md bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
            data-testid="tmpl-create-variable-balance-note"
          >
            Balance validated at instantiate
          </span>
        ) : (
          <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
            Balanced
          </span>
        )
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
