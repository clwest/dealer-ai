// Milestone 14 · Increment 2 (SESSION_135) — trial-balance render page.
//
// Consumes GET /admin/accounting/trial-balance/ (M13.3). Read-only.
// Renders per-account rows in a table + grand totals in a footer
// card + an ``is_balanced`` chip. Empty-state UI for zero-portfolio
// tenants per M13.3 §0.a decision 5 semantics.
//
// No ``as_of`` picker at M14.2 (deferred to M15+ per MILESTONE_14_
// PLANNING.md §3 deferral 2 — belongs with the close-workflow slice).
//
// Money on the wire is Decimal-as-string per §5.c Option A; format
// with Intl.NumberFormat at render time.

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  fetchCostPostingFailures,
  fetchTrialBalance,
  type CostPostingFailure,
  type GLAccountType,
  type TrialBalanceSnapshot,
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


export default function AccountingTrialBalancePage() {
  const [snapshot, setSnapshot] = useState<TrialBalanceSnapshot | null>(null);
  const [failures, setFailures] = useState<CostPostingFailure[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoadState("loading");
      setErrorMessage(null);
      try {
        // Fetch trial balance + failures in parallel so the page
        // renders in a single paint. Failures endpoint returning an
        // empty list is a valid state — the card hides itself when
        // count is 0.
        const [snap, failuresResult] = await Promise.all([
          fetchTrialBalance(),
          fetchCostPostingFailures(),
        ]);
        if (cancelled) return;
        setSnapshot(snap);
        setFailures(failuresResult.failures);
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
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Trial Balance
        </h1>
        <p className="text-sm text-muted-foreground">
          Per-account debit and credit totals across every journal
          entry posted to date (M13.3).
        </p>
      </header>

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
                No postings yet. Once journal entries are posted (via
                the M13.2 cost-reconciliation detector or any future
                sale-booking / payment GL post), account balances
                will appear here.
              </p>
            ) : (
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
                  {snapshot.rows.map((row) => (
                    <tr
                      key={row.account_code}
                      className="border-b border-border"
                    >
                      <td className="py-2">
                        <div className="font-medium">
                          {row.account_code}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {row.account_name}
                        </div>
                      </td>
                      <td className="py-2">
                        <Badge variant="outline">
                          {ACCOUNT_TYPE_LABELS[row.account_type] ??
                            row.account_type}
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
    </div>
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
                  {failure.reference || (
                    <span>—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
