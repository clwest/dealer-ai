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
  fetchJournalEntry,
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
  }, [pk]);

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
                reversal dialog lands at M14.4.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm" disabled>
                Reverse this entry (M14.4)
              </Button>
            </CardContent>
          </Card>
        </>
      )}
    </div>
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
