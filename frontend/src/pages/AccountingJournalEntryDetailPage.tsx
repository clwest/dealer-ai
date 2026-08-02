// Milestone 14 · Increment 3 (SESSION_136) — journal-entry detail page.
//
// Consumes GET /admin/accounting/journal-entries/<pk>/ (M13.1). Shows
// entry metadata + per-line breakdown + reversal-linkage panel (if
// this entry reverses another).
//
// The "Reverse this entry" button is a M14.3 placeholder — the actual
// shadcn <Dialog> wiring lands at M14.4 per §5.e Option A. The
// placeholder button is disabled + carries a tooltip-style hint so
// operators understand the action is coming.

import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  fetchJournalEntry,
  reverseJournalEntry,
  type JournalEntry,
} from "@/lib/accountingApi";


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


function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}


export default function AccountingJournalEntryDetailPage() {
  const params = useParams<{ pk: string }>();
  const pk = params.pk ? Number(params.pk) : NaN;
  const [entry, setEntry] = useState<JournalEntry | null>(null);
  const [loadState, setLoadState] = useState<
    "loading" | "ready" | "not_found" | "error"
  >("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    if (Number.isNaN(pk)) {
      setLoadState("not_found");
      return;
    }
    let cancelled = false;
    async function load() {
      setLoadState("loading");
      setErrorMessage(null);
      try {
        const result = await fetchJournalEntry(pk);
        if (cancelled) return;
        setEntry(result);
        setLoadState("ready");
      } catch (err) {
        if (cancelled) return;
        // authFetch throws typed errors on 4xx/5xx. Treat 404 as
        // not-found; everything else as generic error.
        const message = err instanceof Error ? err.message : String(err);
        if (/not found/i.test(message) || /404/.test(message)) {
          setLoadState("not_found");
        } else {
          setErrorMessage(message);
          setLoadState("error");
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [pk, reloadTick]);

  const isReversal = entry?.reverses_id !== null && entry?.reverses_id !== undefined;
  const totalDebit = entry
    ? entry.lines.reduce((sum, line) => sum + Number(line.debit), 0)
    : 0;
  const totalCredit = entry
    ? entry.lines.reduce((sum, line) => sum + Number(line.credit), 0)
    : 0;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Link
            to="/dealer-ai-accounting/journal-entries"
            className="underline"
          >
            ← Back to journal entries
          </Link>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">
          {entry ? `Journal Entry #${entry.id}` : "Journal Entry"}
        </h1>
      </header>

      {loadState === "loading" && (
        <p className="text-sm text-muted-foreground">Loading entry…</p>
      )}
      {loadState === "not_found" && (
        <p className="text-sm text-muted-foreground">
          Journal entry not found.
        </p>
      )}
      {loadState === "error" && errorMessage && (
        <p className="text-sm text-destructive">{errorMessage}</p>
      )}

      {entry && (
        <>
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <CardTitle>{entry.description}</CardTitle>
                  <CardDescription>
                    Posted {formatDateTime(entry.posted_at)}
                  </CardDescription>
                </div>
                {isReversal ? (
                  <Badge variant="destructive">
                    Reversal of #{entry.reverses_id}
                  </Badge>
                ) : (
                  <Badge variant="outline">Original entry</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 text-sm">
              <MetaRow label="Entry ID" value={`#${entry.id}`} />
              <MetaRow
                label="Posted by user"
                value={
                  entry.posted_by_user_id !== null
                    ? `#${entry.posted_by_user_id}`
                    : "—"
                }
              />
              <MetaRow
                label="Row created"
                value={formatDateTime(entry.created_at)}
              />
              {isReversal && (
                <MetaRow
                  label="Reversal reason"
                  value={entry.reason || "(none)"}
                />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Lines</CardTitle>
              <CardDescription>
                {entry.lines.length}{" "}
                {entry.lines.length === 1 ? "line" : "lines"} · Total
                debits {formatMoney(String(totalDebit))} · Total
                credits {formatMoney(String(totalCredit))}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left">
                    <th className="py-2">Account</th>
                    <th className="py-2 text-right">Debit</th>
                    <th className="py-2 text-right">Credit</th>
                    <th className="py-2">Memo</th>
                  </tr>
                </thead>
                <tbody>
                  {entry.lines.map((line) => (
                    <tr key={line.id} className="border-b border-border">
                      <td className="py-2 font-medium">
                        {line.account_code}
                      </td>
                      <td className="py-2 text-right tabular-nums">
                        {Number(line.debit) > 0
                          ? formatMoney(line.debit)
                          : ""}
                      </td>
                      <td className="py-2 text-right tabular-nums">
                        {Number(line.credit) > 0
                          ? formatMoney(line.credit)
                          : ""}
                      </td>
                      <td className="py-2 text-xs text-muted-foreground">
                        {line.memo || <span>—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Corrections</CardTitle>
              <CardDescription>
                Journal entries are immutable — corrections happen by
                posting a reversal (per M13.1 §5.c Option A). The
                reversal creates a new entry with debits/credits
                swapped and a link back to this original.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ReverseEntryDialog
                entry={entry}
                onReversed={() => setReloadTick((tick) => tick + 1)}
              />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}


function ReverseEntryDialog({
  entry,
  onReversed,
}: {
  entry: JournalEntry;
  onReversed: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [postedAt, setPostedAt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmedReason = reason.trim();
  const reasonInvalid = trimmedReason.length === 0;

  function reset() {
    setReason("");
    setPostedAt("");
    setError(null);
    setSubmitting(false);
  }

  async function handleConfirm() {
    if (reasonInvalid || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await reverseJournalEntry(entry.id, {
        reason: trimmedReason,
        posted_at: postedAt.trim() || undefined,
      });
      setOpen(false);
      reset();
      onReversed();
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
        onClick={() => setOpen(true)}
      >
        Reverse this entry
      </Button>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reverse journal entry #{entry.id}</DialogTitle>
          <DialogDescription>
            Posts a new entry with debits and credits swapped. The
            original is preserved (immutability per M13.1 §5.c
            Option A).
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">
              Reason <span className="text-destructive">*</span>
            </span>
            <Textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Why is this entry being reversed?"
              rows={3}
              aria-required
              aria-invalid={reasonInvalid}
            />
            <span className="text-xs text-muted-foreground">
              Required. Stored on the reversal entry for the audit
              trail.
            </span>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">Posted at (optional)</span>
            <input
              type="text"
              value={postedAt}
              onChange={(event) => setPostedAt(event.target.value)}
              placeholder="Leave blank for now (ISO 8601 accepted)"
              className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <span className="text-xs text-muted-foreground">
              Blank posts the reversal at the current server
              timestamp.
            </span>
          </label>

          {error && (
            <p className="text-sm text-destructive" role="alert">
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
            onClick={handleConfirm}
            disabled={reasonInvalid || submitting}
          >
            {submitting ? "Posting…" : "Confirm reversal"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}
