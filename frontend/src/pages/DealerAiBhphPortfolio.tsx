// Milestone 12 · Increment 7 (SESSION_127) — BHPH portfolio dashboard.
//
// Consumes GET /admin/bhph/analytics/summary/ (M12.7) and
// GET /admin/bhph-notes/list/ (M12.7 addendum). Shows the five
// portfolio metrics + a browsable list of notes. Per-note detail
// lives at /dealer-ai-bhph/notes/<pk>/.

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  fetchBhphAnalyticsSummary,
  listBhphNotes,
  type BhphAnalyticsSummary,
  type BhphNoteProjection,
} from "@/lib/bhphApi";


const BUCKET_LABELS: Record<string, string> = {
  current: "Current",
  "1_15": "1–15 days",
  "16_30": "16–30 days",
  "31_60": "31–60 days",
  "61_90": "61–90 days",
  over_90: "Over 90 days",
  charge_off_candidate: "Charge-off candidate",
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


function formatRatio(raw: string | null): string {
  if (raw === null) return "—";
  const value = Number(raw);
  if (Number.isNaN(value)) return raw;
  return `${(value * 100).toFixed(2)}%`;
}


function formatDaysPastDue(raw: string | null): string {
  if (raw === null) return "—";
  const value = Number(raw);
  if (Number.isNaN(value)) return raw;
  return `${value.toFixed(1)} days`;
}


function formatApr(raw: string | null): string {
  if (raw === null) return "—";
  return `${raw}%`;
}


export default function DealerAiBhphPortfolio() {
  const [summary, setSummary] = useState<BhphAnalyticsSummary | null>(null);
  const [notes, setNotes] = useState<BhphNoteProjection[]>([]);
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
        const [summaryRes, notesRes] = await Promise.all([
          fetchBhphAnalyticsSummary(),
          listBhphNotes(),
        ]);
        if (cancelled) return;
        setSummary(summaryRes);
        setNotes(notesRes.results);
        setLoadState("ready");
      } catch (err) {
        if (cancelled) return;
        setErrorMessage(
          err instanceof Error ? err.message : "Failed to load portfolio.",
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
          BHPH Portfolio
        </h1>
        <p className="text-sm text-muted-foreground">
          Buy-here-pay-here dealer notes with aging, payment
          collection, and PTP tracking (M12.1–M12.7).
        </p>
      </header>

      {loadState === "loading" && (
        <p className="text-sm text-muted-foreground">Loading portfolio…</p>
      )}
      {loadState === "error" && errorMessage && (
        <p className="text-sm text-destructive">{errorMessage}</p>
      )}

      {summary && (
        <>
          <section className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title="Notes in portfolio"
              value={String(summary.total_note_count)}
              hint={`${formatMoney(summary.total_principal_financed)} principal`}
            />
            <MetricCard
              title="Cure rate"
              value={formatRatio(summary.cure_rate)}
              hint="Share of notes in current bucket"
            />
            <MetricCard
              title="Weighted average APR"
              value={formatApr(summary.weighted_average_apr)}
              hint="Weighted by principal"
            />
            <MetricCard
              title="Weighted average DPD"
              value={formatDaysPastDue(
                summary.weighted_average_days_past_due,
              )}
              hint="Weighted by principal"
            />
          </section>

          <section>
            <Card>
              <CardHeader>
                <CardTitle>Aging histogram</CardTitle>
                <CardDescription>
                  Note counts + principal financed per bucket.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-4">
                  {summary.bucket_histogram.map((row) => (
                    <li
                      key={row.bucket}
                      className="rounded-md border border-border p-3 text-sm"
                    >
                      <div className="font-semibold">
                        {BUCKET_LABELS[row.bucket] ?? row.bucket}
                      </div>
                      <div>{row.note_count} notes</div>
                      <div className="text-muted-foreground">
                        {formatMoney(row.principal_total)}
                      </div>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </section>

          <section>
            <Card>
              <CardHeader>
                <CardTitle>Notes ({notes.length})</CardTitle>
                <CardDescription>
                  Up to 100 most recently originated notes.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {notes.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No BHPH notes yet. Origination happens via
                    `POST /admin/bhph-notes/` on a BHPH sale.
                  </p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left">
                        <th className="py-2">ID</th>
                        <th className="py-2">Principal</th>
                        <th className="py-2">APR</th>
                        <th className="py-2">Cadence</th>
                        <th className="py-2">Bucket</th>
                        <th className="py-2">DPD</th>
                        <th className="py-2">Detail</th>
                      </tr>
                    </thead>
                    <tbody>
                      {notes.map((note) => (
                        <tr key={note.id} className="border-b border-border">
                          <td className="py-2">{note.id}</td>
                          <td className="py-2">
                            {formatMoney(note.principal_financed)}
                          </td>
                          <td className="py-2">{note.apr}%</td>
                          <td className="py-2">{note.payment_frequency}</td>
                          <td className="py-2">
                            {BUCKET_LABELS[note.current_bucket] ?? note.current_bucket}
                          </td>
                          <td className="py-2">{note.days_past_due}</td>
                          <td className="py-2">
                            <Link
                              to={`/dealer-ai-bhph/notes/${note.id}`}
                              className="text-primary underline"
                            >
                              View
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </CardContent>
            </Card>
          </section>
        </>
      )}
    </div>
  );
}


function MetricCard({
  title,
  value,
  hint,
}: {
  title: string;
  value: string;
  hint?: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold">{value}</div>
        {hint && (
          <div className="text-xs text-muted-foreground">{hint}</div>
        )}
      </CardContent>
    </Card>
  );
}
