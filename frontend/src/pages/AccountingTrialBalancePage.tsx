// Milestone 14 · Increment 2 (SESSION_135) — trial-balance render page.
// Milestone 17 · Increment 2 (SESSION_145) — extended in place with the
// ``as_of`` picker + "Freeze this view" button + "Prior closes" list +
// inline snapshot detail view.
//
// Consumes GET /admin/accounting/trial-balance/[?as_of=] (M13.3) plus
// the three M17.1 snapshot endpoints (POST snapshots/, GET
// snapshots/list/, GET snapshots/<pk>/).
//
// Per MILESTONE_17_PLANNING.md §7 M17.2 the page extends in place
// rather than growing a new route (§4 endpoint-count binding stays at
// 20 frontend operator routes; the snapshot detail renders inline).
//
// UX per §5.e Option B — date-only picker; §5.d Option A — 409 on
// duplicate freeze surfaces as an inline error banner; §5.f Option A
// — frozen snapshots are immutable and rendered with their frozen row
// values (not re-fetched from live).
//
// Money on the wire is Decimal-as-string per §5.c Option A; format
// with Intl.NumberFormat at render time.

import { useCallback, useEffect, useState } from "react";

import {
  TrialBalanceDatePicker,
  dateToEndOfDayIso,
  todayIsoDate,
} from "@/components/accounting/TrialBalanceDatePicker";
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
import { ApiError } from "@/lib/authFetch";
import {
  fetchCostPostingFailures,
  fetchTrialBalance,
  fetchTrialBalanceSnapshot,
  freezeTrialBalance,
  listTrialBalanceSnapshots,
  type CostPostingFailure,
  type FrozenSnapshotRow,
  type FrozenTrialBalanceSnapshot,
  type GLAccountType,
  type TrialBalanceRow,
  type TrialBalanceSnapshot,
  type TrialBalanceSnapshotListPage,
} from "@/lib/accountingApi";


const ACCOUNT_TYPE_LABELS: Record<GLAccountType, string> = {
  asset: "Asset",
  liability: "Liability",
  equity: "Equity",
  revenue: "Revenue",
  expense: "Expense",
};


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


function formatAsOf(iso: string): string {
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


type FreezeState = "idle" | "posting" | "success" | "error";


export default function AccountingTrialBalancePage() {
  const [asOfDate, setAsOfDate] = useState<string>(todayIsoDate);
  const [snapshot, setSnapshot] = useState<TrialBalanceSnapshot | null>(null);
  const [failures, setFailures] = useState<CostPostingFailure[]>([]);
  const [snapshotList, setSnapshotList] =
    useState<TrialBalanceSnapshotListPage | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] =
    useState<FrozenTrialBalanceSnapshot | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [freezeState, setFreezeState] = useState<FreezeState>("idle");
  const [freezeMessage, setFreezeMessage] = useState<string | null>(null);

  const refreshSnapshotList = useCallback(async () => {
    try {
      const page = await listTrialBalanceSnapshots({ pageSize: 10 });
      setSnapshotList(page);
    } catch (err) {
      // Non-fatal — the live trial balance still renders even if the
      // snapshot history is unreachable.
      setSnapshotList(null);
      console.warn("Failed to load snapshot history", err);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoadState("loading");
      setErrorMessage(null);
      try {
        const asOfIso = asOfDate ? dateToEndOfDayIso(asOfDate) : undefined;
        const [snap, failuresResult, list] = await Promise.all([
          fetchTrialBalance(asOfIso),
          fetchCostPostingFailures(),
          listTrialBalanceSnapshots({ pageSize: 10 }).catch(() => null),
        ]);
        if (cancelled) return;
        setSnapshot(snap);
        setFailures(failuresResult.failures);
        setSnapshotList(list);
        setLoadState("ready");
      } catch (err) {
        if (cancelled) return;
        setErrorMessage(
          err instanceof Error ? err.message : "Failed to load trial balance.",
        );
        setLoadState("error");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [asOfDate]);

  async function handleFreeze() {
    if (!asOfDate) return;
    setFreezeState("posting");
    setFreezeMessage(null);
    try {
      const asOfIso = dateToEndOfDayIso(asOfDate);
      const frozen = await freezeTrialBalance(asOfIso);
      setFreezeState("success");
      setFreezeMessage(
        `Frozen — snapshot #${frozen.id} recorded for ${formatAsOf(
          frozen.as_of,
        )}.`,
      );
      await refreshSnapshotList();
    } catch (err) {
      setFreezeState("error");
      if (err instanceof ApiError && err.status === 409) {
        setFreezeMessage(
          `A snapshot for this exact moment already exists. Pick a different date or open the existing snapshot from the Prior closes list below.`,
        );
      } else {
        setFreezeMessage(
          err instanceof Error
            ? `Freeze failed: ${err.message}`
            : "Freeze failed.",
        );
      }
    }
  }

  async function handleSelectSnapshot(pk: number) {
    setSelectedSnapshot(null);
    try {
      const detail = await fetchTrialBalanceSnapshot(pk);
      setSelectedSnapshot(detail);
    } catch (err) {
      console.warn("Failed to load snapshot detail", err);
    }
  }

  function handleAsOfChange(next: string) {
    setAsOfDate(next);
    // Clear any stale freeze banner when the picker changes — the
    // message referred to the previous ``as_of``.
    setFreezeState("idle");
    setFreezeMessage(null);
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Trial Balance
        </h1>
        <p className="text-sm text-muted-foreground">
          Per-account debit and credit totals across every journal
          entry posted to date (M13.3). Pick a historical date to see
          the trial balance as of that moment, and freeze the view to
          record a durable period close (M17).
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Query controls</CardTitle>
          <CardDescription>
            The picker selects an end-of-day moment; freeze captures
            the current view as an immutable snapshot for later
            reference.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <TrialBalanceDatePicker
            value={asOfDate}
            onChange={handleAsOfChange}
            disabled={freezeState === "posting" || loadState === "loading"}
          />
          <Button
            type="button"
            onClick={handleFreeze}
            disabled={
              freezeState === "posting" ||
              loadState !== "ready" ||
              !asOfDate
            }
          >
            {freezeState === "posting" ? "Freezing…" : "Freeze this view"}
          </Button>
        </CardContent>
        {freezeMessage && (
          <CardFooter>
            <p
              role="status"
              className={
                freezeState === "error"
                  ? "text-sm text-destructive"
                  : "text-sm text-emerald-600"
              }
            >
              {freezeMessage}
            </p>
          </CardFooter>
        )}
      </Card>

      {loadState === "loading" && (
        <p className="text-sm text-muted-foreground">
          Loading trial balance…
        </p>
      )}
      {loadState === "error" && errorMessage && (
        <p className="text-sm text-destructive">{errorMessage}</p>
      )}

      {snapshot && failures.length > 0 && (
        <CostPostingFailuresCard failures={failures} />
      )}

      {snapshot && (
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardTitle>
                  {snapshot.dealership_slug || "Dealership"} · Trial Balance
                </CardTitle>
                <CardDescription>
                  As of {formatAsOf(snapshot.as_of)}
                </CardDescription>
              </div>
              <Badge
                variant={snapshot.is_balanced ? "secondary" : "destructive"}
                aria-label={
                  snapshot.is_balanced
                    ? "Trial balance is balanced"
                    : "Trial balance is not balanced"
                }
              >
                {snapshot.is_balanced ? "Balanced" : "Unbalanced"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            {snapshot.rows.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No postings through this date. Once journal entries
                are posted (via M13.2 cost reconciliation, M15 sale
                booking, or M16 BHPH payments), account balances
                will appear here.
              </p>
            ) : (
              <TrialBalanceTable rows={snapshot.rows} />
            )}
          </CardContent>
          {snapshot.rows.length > 0 && (
            <CardFooter className="flex-col items-stretch gap-2 border-t border-border pt-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Total debits</span>
                <span className="tabular-nums font-semibold">
                  {formatMoney(snapshot.total_debits)}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Total credits</span>
                <span className="tabular-nums font-semibold">
                  {formatMoney(snapshot.total_credits)}
                </span>
              </div>
            </CardFooter>
          )}
        </Card>
      )}

      {snapshotList && (
        <PriorClosesCard
          list={snapshotList}
          onSelect={handleSelectSnapshot}
          selectedId={selectedSnapshot?.id ?? null}
        />
      )}

      {selectedSnapshot && (
        <FrozenSnapshotDetailCard
          snapshot={selectedSnapshot}
          onClose={() => setSelectedSnapshot(null)}
        />
      )}
    </div>
  );
}


function TrialBalanceTable({ rows }: { rows: TrialBalanceRow[] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border text-left">
          <th className="py-2">Account</th>
          <th className="py-2">Type</th>
          <th className="py-2 text-right">Debits</th>
          <th className="py-2 text-right">Credits</th>
          <th className="py-2 text-right">Natural balance</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.account_code} className="border-b border-border">
            <td className="py-2">
              <div className="font-medium">{row.account_code}</div>
              <div className="text-xs text-muted-foreground">
                {row.account_name}
              </div>
            </td>
            <td className="py-2">
              <Badge variant="outline">
                {ACCOUNT_TYPE_LABELS[row.account_type] ?? row.account_type}
              </Badge>
            </td>
            <td className="py-2 text-right tabular-nums">
              {formatMoney(row.debit_total)}
            </td>
            <td className="py-2 text-right tabular-nums">
              {formatMoney(row.credit_total)}
            </td>
            <td className="py-2 text-right tabular-nums font-medium">
              {formatMoney(row.natural_balance)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}


function PriorClosesCard({
  list,
  onSelect,
  selectedId,
}: {
  list: TrialBalanceSnapshotListPage;
  onSelect: (pk: number) => void;
  selectedId: number | null;
}) {
  if (list.total_count === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Prior closes</CardTitle>
          <CardDescription>
            No period closes have been frozen yet.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Prior closes ({list.total_count})</CardTitle>
        <CardDescription>
          Recent frozen snapshots. Click a row to view the frozen
          per-account detail; the historical values are preserved
          even if the underlying journal entries change afterwards.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              <th className="py-2">As of</th>
              <th className="py-2">Frozen by</th>
              <th className="py-2">Frozen at</th>
              <th className="py-2 text-right">Total debits</th>
              <th className="py-2 text-right">Total credits</th>
              <th className="py-2">Balance</th>
            </tr>
          </thead>
          <tbody>
            {list.snapshots.map((s) => (
              <tr
                key={s.id}
                className={`cursor-pointer border-b border-border hover:bg-muted/40 ${
                  selectedId === s.id ? "bg-muted/60" : ""
                }`}
                onClick={() => onSelect(s.id)}
                aria-selected={selectedId === s.id}
                data-testid={`snapshot-row-${s.id}`}
              >
                <td className="py-2 font-medium">
                  {formatAsOf(s.as_of)}
                </td>
                <td className="py-2 text-xs text-muted-foreground">
                  {s.created_by_username ?? "—"}
                </td>
                <td className="py-2 text-xs text-muted-foreground">
                  {formatAsOf(s.created_at)}
                </td>
                <td className="py-2 text-right tabular-nums">
                  {formatMoney(s.total_debits)}
                </td>
                <td className="py-2 text-right tabular-nums">
                  {formatMoney(s.total_credits)}
                </td>
                <td className="py-2">
                  <Badge
                    variant={s.is_balanced ? "secondary" : "destructive"}
                  >
                    {s.is_balanced ? "Balanced" : "Unbalanced"}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}


function FrozenSnapshotDetailCard({
  snapshot,
  onClose,
}: {
  snapshot: FrozenTrialBalanceSnapshot;
  onClose: () => void;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle>Frozen snapshot #{snapshot.id}</CardTitle>
            <CardDescription>
              As of {formatAsOf(snapshot.as_of)} · frozen{" "}
              {formatAsOf(snapshot.created_at)}
              {snapshot.created_by_username &&
                ` by ${snapshot.created_by_username}`}
            </CardDescription>
          </div>
          <div className="flex items-start gap-2">
            <Badge
              variant={snapshot.is_balanced ? "secondary" : "destructive"}
            >
              {snapshot.is_balanced ? "Balanced" : "Unbalanced"}
            </Badge>
            <Button variant="outline" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {snapshot.rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            This snapshot has no per-account rows — a zero-portfolio
            close through {formatAsOf(snapshot.as_of)}.
          </p>
        ) : (
          <FrozenRowsTable rows={snapshot.rows} />
        )}
      </CardContent>
      {snapshot.rows.length > 0 && (
        <CardFooter className="flex-col items-stretch gap-2 border-t border-border pt-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Total debits</span>
            <span className="tabular-nums font-semibold">
              {formatMoney(snapshot.total_debits)}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Total credits</span>
            <span className="tabular-nums font-semibold">
              {formatMoney(snapshot.total_credits)}
            </span>
          </div>
        </CardFooter>
      )}
    </Card>
  );
}


function FrozenRowsTable({ rows }: { rows: FrozenSnapshotRow[] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border text-left">
          <th className="py-2">Account</th>
          <th className="py-2">Type</th>
          <th className="py-2 text-right">Debits</th>
          <th className="py-2 text-right">Credits</th>
          <th className="py-2 text-right">Natural balance</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.account_code} className="border-b border-border">
            <td className="py-2">
              <div className="font-medium">{row.account_code}</div>
              <div className="text-xs text-muted-foreground">
                {row.account_name}
              </div>
            </td>
            <td className="py-2">
              <Badge variant="outline">
                {ACCOUNT_TYPE_LABELS[row.account_type] ?? row.account_type}
              </Badge>
            </td>
            <td className="py-2 text-right tabular-nums">
              {formatMoney(row.debit_total)}
            </td>
            <td className="py-2 text-right tabular-nums">
              {formatMoney(row.credit_total)}
            </td>
            <td className="py-2 text-right tabular-nums font-medium">
              {formatMoney(row.natural_balance)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}


function CostPostingFailuresCard({
  failures,
}: {
  failures: CostPostingFailure[];
}) {
  return (
    <Card className="border-destructive/40">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="text-destructive">
              Cost-posting failures ({failures.length})
            </CardTitle>
            <CardDescription>
              VehicleCost rows the M13.2 detector could not post
              (older than 24 hours; typically a missing / inactive
              default COA account). Fix the underlying invariant
              and the next detector run at 10:00 project-time will
              pick them up.
            </CardDescription>
          </div>
          <Badge variant="destructive" aria-label="Attention required">
            Attention
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              <th className="py-2">Vehicle stock</th>
              <th className="py-2">Category</th>
              <th className="py-2 text-right">Amount</th>
              <th className="py-2 text-right">Age (hrs)</th>
              <th className="py-2">Reference</th>
            </tr>
          </thead>
          <tbody>
            {failures.map((failure) => (
              <tr key={failure.id} className="border-b border-border">
                <td className="py-2 font-medium">
                  {failure.vehicle_stock ?? (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
                <td className="py-2">{failure.category_display}</td>
                <td className="py-2 text-right tabular-nums">
                  {formatMoney(failure.amount)}
                </td>
                <td className="py-2 text-right tabular-nums">
                  {failure.age_in_hours}
                </td>
                <td className="py-2 text-xs text-muted-foreground">
                  {failure.reference || <span>—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
