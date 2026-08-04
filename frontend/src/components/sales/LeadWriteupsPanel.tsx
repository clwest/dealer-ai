// Milestone 32 · Increment 2 (SESSION_208) — per-lead writeups panel.
//
// Renders inside LeadDetailModal per MILESTONE_32_PLANNING.md §5.b
// D4-revised². Shows the lead's writeups (via `listDealWriteups`
// with `lead_id` filter) with three-signal state a11y per D7
// (Badge + row aria-label + testids), inline Approve button on
// pending rows (D5-revised copy), inline Send-to-F&I button on
// approved rows (D6 irreversibility copy), and a "+ New writeup"
// CTA that opens the inline four-square form.
//
// Manager-only by transitivity — LeadDetailModal itself is sales-
// role-gated at the backend (`admin_lead_detail` requires
// sales_manager or dealer_owner). Advisors cannot open the modal
// at all; no visible-but-disabled tab treatment is possible or
// required per D4-revised².

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

import {
  DealWriteupForm,
  type DealWriteupFormSuggestedVehicle,
} from "@/components/sales/DealWriteupForm";
import {
  WriteupApproveConfirmDialog,
  WriteupHandoffConfirmDialog,
} from "@/components/sales/WriteupConfirmDialogs";
import {
  derivedWriteupState,
  listDealWriteups,
  type DealWriteupProjection,
  type DealWriteupState,
} from "@/lib/salesApi";

// State badge presentation. Kept as three separate case blocks
// (rather than a lookup table) so the three-signal a11y is
// obvious at the call site.
function stateBadge(
  state: DealWriteupState,
  writeupId: number,
): JSX.Element {
  if (state === "pending") {
    return (
      <span
        data-testid={`writeup-row-state-pending-${writeupId}`}
        className="rounded-md bg-amber-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700"
      >
        Pending
      </span>
    );
  }
  if (state === "approved") {
    return (
      <span
        data-testid={`writeup-row-state-approved-${writeupId}`}
        className="rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700"
      >
        Approved
      </span>
    );
  }
  return (
    <span
      data-testid={`writeup-row-state-handed_off-${writeupId}`}
      className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600"
    >
      Handed off
    </span>
  );
}

// Compact four-square summary — inline row detail so the operator
// can review terms without opening a separate detail view.
function TermsSummary({ writeup }: { writeup: DealWriteupProjection }) {
  const cells: Array<[string, string | null]> = [
    ["Vehicle", writeup.vehicle_price],
    ["Trade", writeup.trade_allowance],
    ["Down", writeup.down_payment],
    ["Mo. payment", writeup.monthly_payment_target],
    [
      "Term",
      writeup.term_months_target != null
        ? `${writeup.term_months_target} mo`
        : null,
    ],
    ["APR", writeup.apr_target != null ? `${writeup.apr_target}%` : null],
  ];
  const populated = cells.filter(([, v]) => v !== null && v !== "");
  if (populated.length === 0) return null;
  return (
    <dl className="mt-1 grid grid-cols-3 gap-x-3 gap-y-1 text-[11px] text-slate-600">
      {populated.map(([label, value]) => (
        <div key={label}>
          <dt className="uppercase tracking-wide text-slate-400">{label}</dt>
          <dd className="font-medium text-slate-700">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export interface LeadWriteupsPanelProps {
  leadId: number;
  leadName: string;
  /** Interested vehicles from LeadDetailResponse for the picker's
   *  "Suggested" zone. */
  suggestedVehicles: DealWriteupFormSuggestedVehicle[];
  /** Injected for tests. */
  loadWriteups?: typeof listDealWriteups;
}

export function LeadWriteupsPanel({
  leadId,
  leadName,
  suggestedVehicles,
  loadWriteups = listDealWriteups,
}: LeadWriteupsPanelProps) {
  const [writeups, setWriteups] = useState<DealWriteupProjection[]>([]);
  const [loadState, setLoadState] = useState<
    "loading" | "ready" | "error"
  >("loading");
  const [formOpen, setFormOpen] = useState(false);
  const [approveTarget, setApproveTarget] =
    useState<DealWriteupProjection | null>(null);
  const [handoffTarget, setHandoffTarget] =
    useState<DealWriteupProjection | null>(null);
  const [sectionOpen, setSectionOpen] = useState(false);

  const reload = useCallback(async () => {
    setLoadState("loading");
    try {
      const rows = await loadWriteups({ leadId });
      setWriteups(rows);
      setLoadState("ready");
    } catch {
      setLoadState("error");
    }
  }, [leadId, loadWriteups]);

  useEffect(() => {
    if (!sectionOpen) return;
    reload();
  }, [sectionOpen, reload]);

  function replaceWriteup(updated: DealWriteupProjection) {
    setWriteups((prev) =>
      prev.map((w) => (w.id === updated.id ? updated : w)),
    );
  }

  return (
    <section
      data-testid="lead-writeups-section"
      className="rounded-lg border border-slate-200"
    >
      <button
        type="button"
        onClick={() => setSectionOpen((prev) => !prev)}
        data-testid="lead-writeups-toggle"
        aria-expanded={sectionOpen}
        className="flex w-full items-center justify-between px-3 py-2 text-left"
      >
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Deal writeups
        </span>
        {sectionOpen ? (
          <ChevronUp className="h-4 w-4 text-slate-500" />
        ) : (
          <ChevronDown className="h-4 w-4 text-slate-500" />
        )}
      </button>

      {sectionOpen ? (
        <div className="border-t border-slate-100 p-3">
          {loadState === "loading" ? (
            <p
              className="text-xs text-slate-500"
              data-testid="lead-writeups-loading"
            >
              Loading writeups…
            </p>
          ) : null}
          {loadState === "error" ? (
            <p
              className="text-xs text-destructive"
              role="alert"
              data-testid="lead-writeups-error"
            >
              Failed to load writeups.
            </p>
          ) : null}
          {loadState === "ready" && writeups.length === 0 ? (
            <p
              className="text-xs text-slate-500"
              data-testid="lead-writeups-empty"
            >
              No writeups yet for this lead.
            </p>
          ) : null}
          {loadState === "ready" && writeups.length > 0 ? (
            <ul className="space-y-2">
              {writeups.map((w) => {
                const state = derivedWriteupState(w);
                return (
                  <li
                    key={w.id}
                    data-testid={`writeup-row-${w.id}`}
                    aria-label={`Writeup #${w.id}, ${leadName}, ${state.replace("_", " ")}`}
                    className={`rounded-md border border-slate-200 p-3 text-sm ${
                      state === "handed_off"
                        ? "bg-slate-50 opacity-90"
                        : "bg-white"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-slate-700">
                        Writeup #{w.id}
                      </span>
                      {stateBadge(state, w.id)}
                    </div>
                    <TermsSummary writeup={w} />
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
                      {w.sales_manager_approved_at ? (
                        <span>
                          Approved{" "}
                          {new Date(
                            w.sales_manager_approved_at,
                          ).toLocaleString()}
                        </span>
                      ) : null}
                      {w.handed_off_to_fandi_at ? (
                        <span>
                          Handed off{" "}
                          {new Date(
                            w.handed_off_to_fandi_at,
                          ).toLocaleString()}
                        </span>
                      ) : null}
                    </div>
                    {state === "pending" ? (
                      <div className="mt-2 flex justify-end">
                        <button
                          type="button"
                          onClick={() => setApproveTarget(w)}
                          data-testid={`writeup-approve-trigger-${w.id}`}
                          className="btn-primary h-8 px-3 text-xs"
                        >
                          Approve
                        </button>
                      </div>
                    ) : null}
                    {state === "approved" ? (
                      <div className="mt-2 flex justify-end">
                        <button
                          type="button"
                          onClick={() => setHandoffTarget(w)}
                          data-testid={`writeup-handoff-trigger-${w.id}`}
                          className="btn-primary h-8 px-3 text-xs"
                        >
                          Send to F&amp;I
                        </button>
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          ) : null}

          <div className="mt-3">
            {!formOpen ? (
              <button
                type="button"
                onClick={() => setFormOpen(true)}
                data-testid="lead-writeups-new"
                className="btn-ghost h-8 px-3 text-xs"
              >
                + New writeup
              </button>
            ) : (
              <div className="rounded-md border border-slate-200 p-3">
                <DealWriteupForm
                  leadId={leadId}
                  suggestedVehicles={suggestedVehicles}
                  onCreated={() => {
                    setFormOpen(false);
                    reload();
                  }}
                  onCancel={() => setFormOpen(false)}
                />
              </div>
            )}
          </div>
        </div>
      ) : null}

      {approveTarget ? (
        <WriteupApproveConfirmDialog
          writeup={approveTarget}
          open={approveTarget !== null}
          onOpenChange={(open) => {
            if (!open) setApproveTarget(null);
          }}
          onApproved={(updated) => {
            replaceWriteup(updated);
            setApproveTarget(null);
          }}
        />
      ) : null}
      {handoffTarget ? (
        <WriteupHandoffConfirmDialog
          writeup={handoffTarget}
          leadName={leadName}
          open={handoffTarget !== null}
          onOpenChange={(open) => {
            if (!open) setHandoffTarget(null);
          }}
          onHandedOff={(updated) => {
            replaceWriteup(updated);
            setHandoffTarget(null);
          }}
        />
      ) : null}
    </section>
  );
}
