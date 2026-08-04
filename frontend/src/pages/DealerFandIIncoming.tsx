// Milestone 32 · Increment 3 (SESSION_209) — F&I intake queue page.
//
// Renders incoming credit applications for the F&I team per
// MILESTONE_32_PLANNING.md §5.b D8-revised. Consumes GET
// /admin/credit-applications/list/ via `fetchCreditApplications`
// (M32.3 wrapper on the M32.1 endpoint; gated on
// IsFinanceManagerOrOwnerAtActiveDealership at the backend).
//
// Non-navigational rows per D8-revised: F&I role cannot access
// `admin_lead_detail` (sales-role-gated per M32 §4.8 verification),
// so no row-link would work. All triage info rendered inline:
// lead name + phone + email; vehicle stock + description; four-
// square terms; CA notes verbatim (M11.3 `_format_handoff_notes`
// prefix carries writeup pk + terms summary); written-up-by;
// approved-by; hand-off timestamp; "Incoming" state badge.
//
// Direct-created CAs (M10.1 path — `deal_writeup` FK null) render
// with a "Direct application" placeholder in the writeup-context
// columns.
//
// Role gating: backend enforces
// IsFinanceManagerOrOwnerAtActiveDealership. Other roles receive
// 403 and the page renders the ApiError branch. Advisors +
// sales_managers see an access-denied message; no leakage.

import { useCallback, useEffect, useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError } from "@/lib/authFetch";
import {
  fetchCreditApplications,
  type CreditApplicationProjection,
} from "@/lib/fAndIApi";

const INTAKE_OPTIONS: Array<{ value: "all" | "intake"; label: string }> = [
  { value: "intake", label: "Pre-contract only (default)" },
  { value: "all", label: "All applications" },
];

function TermsCell({
  ctx,
}: {
  ctx: CreditApplicationProjection["writeup_context"];
}) {
  if (!ctx) {
    return (
      <span
        data-testid="incoming-terms-none"
        className="text-xs text-muted-foreground"
      >
        Direct application
      </span>
    );
  }
  const cells: Array<[string, string | null]> = [
    ["Vehicle", ctx.terms.vehicle_price],
    ["Trade", ctx.terms.trade_allowance],
    ["Down", ctx.terms.down_payment],
    ["Mo. payment", ctx.terms.monthly_payment_target],
    [
      "Term",
      ctx.terms.term_months_target != null
        ? `${ctx.terms.term_months_target} mo`
        : null,
    ],
    ["APR", ctx.terms.apr_target != null ? `${ctx.terms.apr_target}%` : null],
  ];
  const populated = cells.filter(([, v]) => v !== null && v !== "");
  if (populated.length === 0) {
    return (
      <span className="text-xs text-muted-foreground">No terms captured</span>
    );
  }
  return (
    <dl
      data-testid="incoming-terms-summary"
      className="grid grid-cols-3 gap-x-3 gap-y-1 text-[11px]"
    >
      {populated.map(([label, value]) => (
        <div key={label}>
          <dt className="uppercase tracking-wide text-muted-foreground">
            {label}
          </dt>
          <dd className="font-medium">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export default function DealerFandIIncoming() {
  const [rows, setRows] = useState<CreditApplicationProjection[]>([]);
  const [intakeFilter, setIntakeFilter] = useState<"all" | "intake">("intake");
  const [loadState, setLoadState] = useState<
    "loading" | "ready" | "error" | "forbidden"
  >("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadState("loading");
    setErrorMessage(null);
    try {
      const result = await fetchCreditApplications(
        intakeFilter === "intake" ? { intake: true } : {},
      );
      setRows(result);
      setLoadState("ready");
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setLoadState("forbidden");
      } else {
        setErrorMessage(
          err instanceof Error
            ? err.message
            : "Failed to load incoming applications.",
        );
        setLoadState("error");
      }
    }
  }, [intakeFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div
      className="mx-auto max-w-6xl space-y-6 p-6"
      data-testid="fandi-incoming-page"
    >
      <div>
        <h1 className="text-2xl font-semibold">Incoming Applications</h1>
        <p className="text-sm text-muted-foreground">
          Credit applications from sales-manager hand-offs. Each row
          shows the four-square terms, lead + vehicle context, and
          who authored + approved the deal writeup.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>
            Default view shows pre-contract applications only. Switch
            to "All applications" to include CAs that already have
            contracts.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-muted-foreground">Scope</span>
            <select
              aria-label="Intake scope"
              data-testid="incoming-intake-filter"
              value={intakeFilter}
              onChange={(e) =>
                setIntakeFilter(e.target.value as "all" | "intake")
              }
              className="rounded border border-input bg-background px-3 py-2"
            >
              {INTAKE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        </CardContent>
      </Card>

      {loadState === "loading" && (
        <p
          className="text-muted-foreground"
          data-testid="incoming-loading"
        >
          Loading incoming applications…
        </p>
      )}
      {loadState === "forbidden" && (
        <Card>
          <CardContent
            className="py-6 text-center text-sm text-muted-foreground"
            data-testid="incoming-forbidden"
          >
            Only F&amp;I managers or dealer owners can view incoming
            applications.
          </CardContent>
        </Card>
      )}
      {loadState === "error" && (
        <p
          role="alert"
          className="text-destructive"
          data-testid="incoming-error"
        >
          {errorMessage}
        </p>
      )}
      {loadState === "ready" && rows.length === 0 && (
        <Card>
          <CardContent
            className="py-6 text-center text-muted-foreground"
            data-testid="incoming-empty"
          >
            No incoming applications. Credit applications from sales-
            manager hand-offs appear here.
          </CardContent>
        </Card>
      )}
      {loadState === "ready" && rows.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{rows.length} incoming</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y divide-slate-200">
              {rows.map((ca) => {
                const ctx = ca.writeup_context;
                return (
                  <li
                    key={ca.id}
                    data-testid={`incoming-row-${ca.id}`}
                    className="grid gap-3 py-4 md:grid-cols-[1.5fr_1fr_1.4fr_1fr]"
                  >
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Applicant
                      </div>
                      <div className="text-sm font-semibold">
                        {ctx ? ctx.lead.name : ca.applicant_full_name}
                      </div>
                      {ctx ? (
                        <div className="text-xs text-muted-foreground">
                          {ctx.lead.phone || "—"}
                          {ctx.lead.email
                            ? ` · ${ctx.lead.email}`
                            : ""}
                        </div>
                      ) : null}
                      <div
                        data-testid={`incoming-state-${ca.id}`}
                        className="mt-2 inline-flex rounded-md bg-amber-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700"
                      >
                        Incoming
                      </div>
                    </div>
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Vehicle
                      </div>
                      {ctx ? (
                        <>
                          <div className="text-sm font-semibold">
                            {ctx.vehicle.year} {ctx.vehicle.make}{" "}
                            {ctx.vehicle.model}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Stock #{ctx.vehicle.stock_number}
                          </div>
                        </>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          —
                        </span>
                      )}
                    </div>
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Four-square terms
                      </div>
                      <div className="mt-1">
                        <TermsCell ctx={ctx} />
                      </div>
                    </div>
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Timing
                      </div>
                      <div className="text-xs">
                        Captured {new Date(ca.captured_at).toLocaleString()}
                      </div>
                      {ctx?.handed_off_to_fandi_at ? (
                        <div className="text-xs">
                          Handed off{" "}
                          {new Date(
                            ctx.handed_off_to_fandi_at,
                          ).toLocaleString()}
                        </div>
                      ) : null}
                      {ctx ? (
                        <div className="mt-1 text-[11px] text-muted-foreground">
                          Written up by #{ctx.written_up_by_user_id ?? "—"} ·
                          Approved by #
                          {ctx.sales_manager_approved_by_user_id ?? "—"}
                        </div>
                      ) : null}
                      {ca.notes ? (
                        <details className="mt-2">
                          <summary className="cursor-pointer text-[11px] text-muted-foreground">
                            Handoff notes
                          </summary>
                          <pre
                            data-testid={`incoming-notes-${ca.id}`}
                            className="mt-1 whitespace-pre-wrap rounded bg-slate-50 p-2 text-[11px] leading-snug"
                          >
                            {ca.notes}
                          </pre>
                        </details>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
