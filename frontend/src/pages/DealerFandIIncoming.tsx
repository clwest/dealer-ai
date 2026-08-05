// Milestone 32 · Increment 3 (SESSION_209) — F&I intake queue page.
// Extended at Milestone 33 · Increment 2 (SESSION_212) with derived
// DealStructure status (Incoming / In progress) + row actions ("Start
// structuring" on Incoming rows only; "Open structure" on In progress
// rows only) per MILESTONE_33_PLANNING.md §5.b D4 + D5 + D6 + D9.
// Extended at Milestone 35 · Increment 2 (SESSION_218) with derived
// LenderSubmission status (Submitted — awaiting response / Approved /
// Counter-offer received / Declined) + state-conditional row actions
// ("Record lender submission" on In progress rows; "Record lender
// response" on Submitted rows; "Update lender response" on terminal-
// status rows) per MILESTONE_35_PLANNING.md §5.b D8.
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
// approved-by; hand-off timestamp; derived-status chip.
//
// M33.2 derived-status chip (D4): "Incoming" when `has_deal_structure`
// is false; "In progress" when true. Three-signal a11y per M31 D6:
// visible label + row aria-label extension + testid double marker
// `incoming-row-status-<state>-<pk>`.
//
// M33.2 row actions (D5 + D6 + D9): "Start structuring" appears only
// on Incoming rows AND only when `writeup_context !== null` (R1
// mitigation — direct-create CAs lack vehicle discovery; documented
// affordance is that structuring is not available in M33 for the
// direct-create branch). "Open structure" appears only on In progress
// rows with a `latest_deal_structure_id`. First-loop only per D9 —
// iteration UX (creating a second structure for an already-In
// progress CA) explicitly deferred per §5.h.
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

import { DealStructureForm } from "@/components/f-and-i/DealStructureForm";
import { DealStructureReadView } from "@/components/f-and-i/DealStructureReadView";
import { LenderSubmissionRecordForm } from "@/components/f-and-i/LenderSubmissionRecordForm";
import { LenderSubmissionResponseForm } from "@/components/f-and-i/LenderSubmissionResponseForm";
import { Button } from "@/components/ui/button";
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
  type LenderSubmissionProjection,
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

/**
 * Per-row action panel state. Only one row's panel is open at a
 * time. M33.2 shipped kinds "form" (Incoming row → DealStructureForm)
 * and "read" (In progress row → DealStructureReadView). M35.2 adds
 * "record-submission" (In progress row → LenderSubmissionRecordForm)
 * and "record-response" (Submitted+ row → LenderSubmissionResponseForm).
 * `null` means no panel open.
 */
type ActivePanel =
  | { kind: "form"; caId: number }
  | { kind: "read"; caId: number; dealStructureId: number }
  | { kind: "record-submission"; caId: number; dealStructureId: number }
  | {
      kind: "record-response";
      caId: number;
      submission: LenderSubmissionProjection;
    }
  | null;

/**
 * Derived M35 chip state per D8 table. Six values total; two
 * preserved from M33 ("incoming" + "in-progress"), four NEW at M35
 * ("submitted" + "approved" + "counter" + "declined"). Consumers
 * translate the enum to visible label + color + testid suffix.
 */
type DerivedChipState =
  | "incoming"
  | "in-progress"
  | "submitted"
  | "approved"
  | "counter"
  | "declined";

function deriveChipState(
  ca: CreditApplicationProjection,
): DerivedChipState {
  if (!ca.has_deal_structure) return "incoming";
  const submissionStatus = ca.latest_lender_submission_status;
  if (submissionStatus === "pending") return "submitted";
  if (submissionStatus === "approved") return "approved";
  if (submissionStatus === "counter") return "counter";
  if (submissionStatus === "declined") return "declined";
  return "in-progress";
}

const CHIP_LABELS: Record<DerivedChipState, string> = {
  incoming: "Incoming",
  "in-progress": "In progress",
  submitted: "Submitted — awaiting response",
  approved: "Approved",
  counter: "Counter-offer received",
  declined: "Declined",
};

const CHIP_ARIA: Record<DerivedChipState, string> = {
  incoming: "Incoming credit application",
  "in-progress": "In progress credit application",
  submitted: "Submitted — awaiting response",
  approved: "Approved lender submission",
  counter: "Counter-offer received from lender",
  declined: "Declined lender submission",
};

const CHIP_CLASSES: Record<DerivedChipState, string> = {
  incoming: "bg-amber-50 text-amber-700",
  "in-progress": "bg-blue-50 text-blue-700",
  submitted: "bg-slate-100 text-slate-700",
  approved: "bg-emerald-50 text-emerald-700",
  counter: "bg-purple-50 text-purple-700",
  declined: "bg-red-50 text-red-700",
};

export default function DealerFandIIncoming() {
  const [rows, setRows] = useState<CreditApplicationProjection[]>([]);
  const [intakeFilter, setIntakeFilter] = useState<"all" | "intake">("intake");
  const [loadState, setLoadState] = useState<
    "loading" | "ready" | "error" | "forbidden"
  >("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activePanel, setActivePanel] = useState<ActivePanel>(null);

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

  // Cache of most-recently-recorded LenderSubmissions keyed by CA id.
  // Populated when the operator records a submission in-session; used
  // by `openResponsePanel` to seed the response form with the
  // freshly-returned lender program name (available at record time but
  // not on the CA projection). On page refresh this cache is empty and
  // the response form runs without the display context — the D8
  // amendment `latest_lender_submission_id` still lets the PATCH URL
  // resolve.
  const [recentSubmissions, setRecentSubmissions] = useState<
    Record<number, LenderSubmissionProjection>
  >({});

  const openResponsePanel = useCallback(
    (caId: number, _dealStructureId: number) => {
      const row = rows.find((r) => r.id === caId);
      if (!row) return;
      const submissionId = row.latest_lender_submission_id;
      const submissionStatus = row.latest_lender_submission_status;
      if (submissionId === null || submissionStatus === null) return;
      const recent = recentSubmissions[caId];
      setActivePanel({
        kind: "record-response",
        caId,
        submission: recent ?? {
          id: submissionId,
          deal_structure_id: 0,
          lender_program_id: 0,
          lender_program_name: "",
          submitted_at: "",
          status: submissionStatus,
          counter_terms: {},
          approval_terms: {},
          notes: "",
          created_at: "",
          updated_at: "",
        },
      });
    },
    [rows, recentSubmissions],
  );

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
                      {/* M35.2 D8 derived-status chip. Six states
                          (M33's Incoming + In progress + M35's
                          Submitted + Approved + Counter-offer +
                          Declined). Three-signal a11y preserved:
                          visible label + aria-label + testid double
                          marker `incoming-row-status-<state>-<pk>`.
                          Historical `incoming-state-<pk>` testid
                          preserved for M32.3 acceptance-suite
                          compatibility. */}
                      {(() => {
                        const chipState = deriveChipState(ca);
                        return (
                          <div
                            data-testid={`incoming-state-${ca.id}`}
                            className="mt-2 inline-flex flex-wrap gap-1"
                          >
                            <span
                              data-testid={`incoming-row-status-${chipState}-${ca.id}`}
                              aria-label={CHIP_ARIA[chipState]}
                              className={`rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${CHIP_CLASSES[chipState]}`}
                            >
                              {CHIP_LABELS[chipState]}
                            </span>
                          </div>
                        );
                      })()}
                      {/* M35.2 D8 state-conditional row actions.
                          First-loop boundary explicit: same-record
                          status updates allowed via "Update lender
                          response"; new-submission / alternate-lender
                          / history / multi-submission mgmt deferred.
                          Actions gated on writeup_context !== null
                          per R1 (M33) — direct-create CAs have no
                          discovery path. */}
                      {ctx && !ca.has_deal_structure ? (
                        <div className="mt-2">
                          <Button
                            size="sm"
                            variant="outline"
                            data-testid={`incoming-row-start-structuring-${ca.id}`}
                            onClick={() =>
                              setActivePanel({ kind: "form", caId: ca.id })
                            }
                          >
                            Start structuring
                          </Button>
                        </div>
                      ) : null}
                      {ctx &&
                      ca.has_deal_structure &&
                      ca.latest_deal_structure_id !== null ? (
                        <div className="mt-2 flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            data-testid={`incoming-row-open-structure-${ca.id}`}
                            onClick={() =>
                              setActivePanel({
                                kind: "read",
                                caId: ca.id,
                                dealStructureId:
                                  ca.latest_deal_structure_id!,
                              })
                            }
                          >
                            Open structure
                          </Button>
                          {/* Record lender submission — only when
                              chip = "in-progress" (no existing
                              submission on latest DS). */}
                          {ca.latest_lender_submission_status === null ? (
                            <Button
                              size="sm"
                              variant="outline"
                              data-testid={`incoming-row-record-lender-submission-${ca.id}`}
                              onClick={() =>
                                setActivePanel({
                                  kind: "record-submission",
                                  caId: ca.id,
                                  dealStructureId:
                                    ca.latest_deal_structure_id!,
                                })
                              }
                            >
                              Record lender submission
                            </Button>
                          ) : null}
                          {/* Record lender response — chip =
                              "submitted" (pending). Same-record
                              status update per D7. */}
                          {ca.latest_lender_submission_status ===
                          "pending" ? (
                            <Button
                              size="sm"
                              variant="outline"
                              data-testid={`incoming-row-record-lender-response-${ca.id}`}
                              onClick={() =>
                                openResponsePanel(
                                  ca.id,
                                  ca.latest_deal_structure_id!,
                                )
                              }
                            >
                              Record lender response
                            </Button>
                          ) : null}
                          {/* Update lender response — chip ∈
                              {approved, counter, declined}. Same-
                              record status correction per D7. */}
                          {ca.latest_lender_submission_status ===
                            "approved" ||
                          ca.latest_lender_submission_status === "counter" ||
                          ca.latest_lender_submission_status ===
                            "declined" ? (
                            <Button
                              size="sm"
                              variant="outline"
                              data-testid={`incoming-row-update-lender-response-${ca.id}`}
                              onClick={() =>
                                openResponsePanel(
                                  ca.id,
                                  ca.latest_deal_structure_id!,
                                )
                              }
                            >
                              Update lender response
                            </Button>
                          ) : null}
                        </div>
                      ) : null}
                      {!ctx ? (
                        <div
                          className="mt-2 text-[11px] text-muted-foreground"
                          data-testid={`incoming-row-no-writeup-${ca.id}`}
                        >
                          No sales-side writeup — direct-create CA;
                          structuring not available in M33.
                        </div>
                      ) : null}
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

      {/* M33.2 active-panel render (D5 + D6). Inline panel per D5
          implementation-choice note — modal-vs-panel is either
          satisfying the contract; inline keeps the CA row context
          visible while the operator works the structure. */}
      {activePanel !== null &&
        (() => {
          const targetRow = rows.find((r) => r.id === activePanel.caId);
          if (!targetRow) return null;
          if (activePanel.kind === "form") {
            if (targetRow.writeup_context === null) return null;
            return (
              <Card data-testid="deal-structure-form-panel">
                <CardContent className="pt-6">
                  <DealStructureForm
                    creditApplicationId={targetRow.id}
                    writeupContext={targetRow.writeup_context}
                    onCancel={() => setActivePanel(null)}
                    onCreated={() => {
                      setActivePanel(null);
                      void load();
                    }}
                  />
                </CardContent>
              </Card>
            );
          }
          if (activePanel.kind === "read") {
            return (
              <Card data-testid="deal-structure-read-panel">
                <CardContent className="pt-6">
                  <DealStructureReadView
                    dealStructureId={activePanel.dealStructureId}
                    onClose={() => setActivePanel(null)}
                  />
                </CardContent>
              </Card>
            );
          }
          if (activePanel.kind === "record-submission") {
            return (
              <Card data-testid="lender-submission-record-panel">
                <CardContent className="pt-6">
                  <LenderSubmissionRecordForm
                    dealStructureId={activePanel.dealStructureId}
                    onCancel={() => setActivePanel(null)}
                    onRecorded={(submission) => {
                      setRecentSubmissions((prev) => ({
                        ...prev,
                        [activePanel.caId]: submission,
                      }));
                      setActivePanel(null);
                      void load();
                    }}
                  />
                </CardContent>
              </Card>
            );
          }
          // activePanel.kind === "record-response"
          return (
            <Card data-testid="lender-submission-response-panel">
              <CardContent className="pt-6">
                <LenderSubmissionResponseForm
                  submission={{
                    id: activePanel.submission.id,
                    status: activePanel.submission.status,
                    initialNotes: activePanel.submission.notes,
                  }}
                  onCancel={() => setActivePanel(null)}
                  onUpdated={(submission) => {
                    setRecentSubmissions((prev) => ({
                      ...prev,
                      [activePanel.caId]: submission,
                    }));
                    setActivePanel(null);
                    void load();
                  }}
                />
              </CardContent>
            </Card>
          );
        })()}
    </div>
  );
}
