// Milestone 14 · Increment 3 (SESSION_136) — journal-entry browser page.
// Milestone 27 · Increment 2 (SESSION_193) — extended in place with
// the "+ New journal entry" dialog trigger + success indicator per
// M27.0 §5.b substrate-attachment rule (no new frontend route).
//
// Consumes GET /admin/accounting/journal-entries/list/ (M14.1). Read-
// only browsing surface; JE origination happens through the M27.2
// dialog attached to the header. Reversal entries appear as ordinary
// list rows with a reversal-linkage indicator column.
//
// No filter surface at M14.3 — §5.b Option B locks filter-less MVP at
// both backend (M14.1) and frontend (M14.3). Filters land at M15+ per
// operator evidence.

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { NewJournalEntryDialog } from "@/components/accounting/NewJournalEntryDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  fetchGLAccounts,
  fetchJournalEntries,
  type GLAccount,
  type JournalEntry,
  type JournalEntryListEntry,
  type JournalEntryListPage,
} from "@/lib/accountingApi";


const DEFAULT_PAGE_SIZE = 25;


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


function formatPostedAt(iso: string): string {
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


export default function AccountingJournalEntriesPage() {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(DEFAULT_PAGE_SIZE);
  const [result, setResult] = useState<JournalEntryListPage | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [accounts, setAccounts] = useState<GLAccount[]>([]);
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [lastCreated, setLastCreated] = useState<JournalEntry | null>(null);

  const refetchList = useCallback(() => {
    setReloadTick((tick) => tick + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoadState("loading");
      setErrorMessage(null);
      try {
        const response = await fetchJournalEntries({ page, pageSize });
        if (cancelled) return;
        setResult(response);
        setLoadState("ready");
      } catch (err) {
        if (cancelled) return;
        setErrorMessage(
          err instanceof Error
            ? err.message
            : "Failed to load journal entries.",
        );
        setLoadState("error");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [page, pageSize, reloadTick]);

  useEffect(() => {
    // Fetch the chart of accounts once on mount — the M27.1 substrate
    // returns the full active tenant CoA (typically 20–100 accounts)
    // in a single response, sufficient for the M27.2 picker's
    // client-side filter without re-fetching per open.
    let cancelled = false;
    async function loadAccounts() {
      try {
        const response = await fetchGLAccounts();
        if (cancelled) return;
        setAccounts(response);
        setAccountsError(null);
      } catch (err) {
        if (cancelled) return;
        setAccountsError(
          err instanceof Error
            ? err.message
            : "Failed to load chart of accounts.",
        );
      }
    }
    void loadAccounts();
    return () => {
      cancelled = true;
    };
  }, []);

  const totalPages = result
    ? Math.max(1, Math.ceil(result.total_count / result.page_size))
    : 1;
  const canPrev = page > 1;
  const canNext = result ? page < totalPages : false;

  const handleCreated = useCallback(
    (entry: JournalEntry) => {
      setLastCreated(entry);
      // If not on page 1 the new entry (recent-first ordering) won't
      // appear where the operator is looking — jump to page 1 in that
      // case so the success badge sits above the freshly-posted row.
      if (page !== 1) {
        setPage(1);
      } else {
        refetchList();
      }
    },
    [page, refetchList],
  );

  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">
            Journal Entries
          </h1>
          <p className="text-sm text-muted-foreground">
            Every double-entry posting to the general ledger, recent
            first. Reversal entries appear inline with a linkage to the
            original.
          </p>
        </div>
        <NewJournalEntryDialog
          accounts={accounts}
          onCreated={handleCreated}
          disabled={accounts.length < 2}
        />
      </header>

      {accountsError && (
        <p className="text-sm text-destructive" role="alert">
          Could not load the chart of accounts — {accountsError}. New
          journal entry creation is unavailable until this loads.
        </p>
      )}

      {lastCreated && (
        <div
          role="status"
          className="rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
          data-testid="je-create-success-badge"
        >
          Journal Entry #{lastCreated.id} posted — {lastCreated.description}
        </div>
      )}

      {loadState === "loading" && (
        <p className="text-sm text-muted-foreground">
          Loading journal entries…
        </p>
      )}
      {loadState === "error" && errorMessage && (
        <p className="text-sm text-destructive">{errorMessage}</p>
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>
              {result.total_count} {result.total_count === 1 ? "entry" : "entries"}
            </CardTitle>
            <CardDescription>
              Page {result.page} of {totalPages}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {result.entries.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No journal entries yet. The M13.2 detector runs daily
                at 10:00 project-time and posts unposted VehicleCost
                rows automatically.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left">
                    <th className="py-2">ID</th>
                    <th className="py-2">Posted</th>
                    <th className="py-2">Description</th>
                    <th className="py-2">Posted by</th>
                    <th className="py-2 text-right">Total (debits)</th>
                    <th className="py-2">Kind</th>
                    <th className="py-2">Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {result.entries.map((entry) => (
                    <EntryRow key={entry.id} entry={entry} />
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
          {result.entries.length > 0 && (
            <CardFooter className="flex items-center justify-between border-t border-border pt-4">
              <span className="text-xs text-muted-foreground">
                Showing {(page - 1) * result.page_size + 1}–
                {Math.min(page * result.page_size, result.total_count)}{" "}
                of {result.total_count}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!canPrev}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!canNext}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </CardFooter>
          )}
        </Card>
      )}
    </div>
  );
}


function EntryRow({ entry }: { entry: JournalEntryListEntry }) {
  const isReversal = entry.reverses_id !== null;
  return (
    <tr className="border-b border-border">
      <td className="py-2 font-medium">#{entry.id}</td>
      <td className="py-2 whitespace-nowrap">
        {formatPostedAt(entry.posted_at)}
      </td>
      <td className="py-2">{entry.description}</td>
      <td className="py-2">
        {entry.posted_by_username ?? (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
      <td className="py-2 text-right tabular-nums">
        {formatMoney(entry.total_debit)}
      </td>
      <td className="py-2">
        {isReversal ? (
          <Badge variant="destructive">
            Reversal of #{entry.reverses_id}
          </Badge>
        ) : (
          <Badge variant="outline">Original</Badge>
        )}
      </td>
      <td className="py-2">
        <Link
          to={`/dealer-ai-accounting/journal-entries/${entry.id}`}
          className="text-primary underline"
        >
          View
        </Link>
      </td>
    </tr>
  );
}
