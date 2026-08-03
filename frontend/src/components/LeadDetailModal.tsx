import { useEffect, useState } from "react";
import {
  Bot,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clipboard,
  Loader2,
  User,
  X,
} from "lucide-react";

import AssignmentDropdown from "@/components/AssignmentDropdown";
import { RecordTestDriveForm } from "@/components/sales/RecordTestDriveForm";
import {
  buildLeadHandoff,
  fetchAdminLeads,
  fetchLeadDetail,
  type HandoffPacket,
  type LeadDetailResponse,
  type SalespersonAssignment,
} from "@/lib/api";
import { cn, formatCurrency } from "@/lib/utils";

interface Props {
  leadId: number | null;
  onClose: () => void;
  onHandoffComplete?: () => void;
}

const URGENCY_LABEL: Record<string, string> = {
  immediate: "Buying now",
  this_week: "This week",
  this_month: "This month",
  researching: "Researching",
};

// M25.1 attribution helpers per MILESTONE_25_PLANNING.md §5.c.
// Rendering rules:
//   chat / walk_in / phone / other → omit Source section entirely.
//   listing_form → "Source: {platform_label}" or "Listing form" fallback.
//   referral → "Referred by: {referrer_name}" or "Referral (referrer not linked)".
// Exported for direct unit testing.
export function displayPlatform(raw: unknown): string {
  if (typeof raw !== "string" || !raw) return "";
  return raw
    .split(/[-_ ]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function computeSourceLine(
  lead: LeadDetailResponse["lead"],
): string | null {
  if (lead.channel === "referral") {
    return lead.referrer_name
      ? `Referred by: ${lead.referrer_name}`
      : "Referral (referrer not linked)";
  }
  if (lead.channel === "listing_form") {
    const platform = displayPlatform(lead.source_metadata?.platform);
    return platform ? `Source: ${platform}` : "Source: Listing form";
  }
  return null;
}

export default function LeadDetailModal({
  leadId,
  onClose,
  onHandoffComplete,
}: Props) {
  const [detail, setDetail] = useState<LeadDetailResponse | null>(null);
  const [packet, setPacket] = useState<HandoffPacket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [building, setBuilding] = useState(false);
  const [copied, setCopied] = useState<"text" | "message" | null>(null);
  // Manager Phase 4: live assignment state. Sourced from /admin/leads/?id=
  // because the existing /admin/lead/<id>/ payload predates the
  // assigned_to field on AdminLead and we want to avoid changing its
  // contract. Updated optimistically by the AssignmentDropdown.
  const [assignment, setAssignment] = useState<SalespersonAssignment | null>(
    null,
  );
  // M25.2 — Schedule test drive collapsible. Collapsed by default per
  // MILESTONE_25_PLANNING.md §5.d. `justRecorded` triggers a success
  // indicator that clears when the operator reopens the collapsible.
  const [testDriveOpen, setTestDriveOpen] = useState(false);
  const [testDriveJustRecorded, setTestDriveJustRecorded] = useState(false);

  useEffect(() => {
    if (leadId == null) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setPacket(null);
    setDetail(null);

    // Pull the assignment from the admin list payload (which now includes
    // assigned_to as of Phase 4) so the dropdown initializes correctly.
    // Garbage-shielded: a failure here is non-fatal — we still render
    // the modal as Unassigned.
    fetchAdminLeads({ limit: 200 })
      .then((list) => {
        if (cancelled) return;
        const row = list.results.find((r) => r.id === leadId);
        if (row) setAssignment(row.assigned_to);
      })
      .catch(() => {
        // Non-fatal — leave assignment as null/whatever it was.
      });
    Promise.all([fetchLeadDetail(leadId), buildLeadHandoff(leadId)])
      .then(([d, p]) => {
        if (cancelled) return;
        // Defensive: log loudly when either fetch resolved but the
        // payload is unexpectedly missing fields. This used to render
        // the modal as a blank header with no content area below.
        if (!d || !d.lead) {
          console.error(
            "LeadDetailModal: fetchLeadDetail returned no usable detail payload",
            { leadId, payload: d },
          );
        }
        if (!p || !p.customer || !p.budget) {
          console.error(
            "LeadDetailModal: buildLeadHandoff returned no usable packet payload",
            { leadId, payload: p },
          );
        }
        setDetail(d);
        setPacket(p);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("LeadDetailModal: fetch failed", { leadId, err });
        setError(err instanceof Error ? err.message : "Failed to load lead.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [leadId]);

  if (leadId == null) return null;

  // Defensive: minimum-shape validators. Used to gate the main render
  // and surface a visible fallback instead of an empty modal body when
  // the API resolved but a critical field is missing.
  const detailValid = !!(
    detail &&
    detail.lead &&
    Array.isArray(detail.messages) &&
    Array.isArray(detail.interested_vehicles)
  );
  const packetValid = !!(packet && packet.customer && packet.budget);

  // Debug: log every render-state transition so the browser console
  // shows exactly what the modal saw. Also flags the "blank-body"
  // condition explicitly for grep-ability.
  const renderState = {
    leadId,
    loading,
    error,
    hasDetail: !!detail,
    hasPacket: !!packet,
    detailValid,
    packetValid,
    willRenderContent: !loading && !error && detailValid && packetValid,
    willRenderFallback:
      !loading && !error && (!detailValid || !packetValid),
  };
  // eslint-disable-next-line no-console
  console.debug("[LeadDetailModal] render", renderState);
  if (renderState.willRenderFallback) {
    // eslint-disable-next-line no-console
    console.warn(
      "[LeadDetailModal] BLANK-BODY GUARD FIRED — detail or packet missing",
      {
        ...renderState,
        rawDetail: detail,
        rawPacket: packet,
      },
    );
  }

  async function copyToClipboard(text: string, kind: "text" | "message") {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(kind);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      // Fallback: select & alert.
      window.prompt("Copy this:", text);
    }
  }

  async function markHandedOff() {
    if (!leadId) return;
    setBuilding(true);
    try {
      const updated = await buildLeadHandoff(leadId, { markHandedOff: true });
      setPacket(updated);
      onHandoffComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to mark hand-off.");
    } finally {
      setBuilding(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="card flex h-[90vh] w-full max-w-4xl flex-col overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-6 py-4">
          <div>
            <div className="text-sm font-bold text-brand-ink">
              Sales handoff packet
            </div>
            <div className="text-xs text-slate-500">
              Lead #{leadId}
              {packet?.handed_off && (
                <span className="ml-2 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
                  Handed off
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {leadId != null ? (
              <AssignmentDropdown
                leadId={leadId}
                current={assignment}
                onChange={(next) => setAssignment(next)}
              />
            ) : null}
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-brand-ink"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="space-y-4 p-6">
              <div className="h-4 w-1/3 animate-pulse rounded bg-slate-100" />
              <div className="h-32 w-full animate-pulse rounded bg-slate-100" />
              <div className="h-24 w-full animate-pulse rounded bg-slate-100" />
            </div>
          )}

          {error && (
            <div className="m-6 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Defensive fallback: API resolved but data is incomplete.
              Previously this state rendered an empty modal body. */}
          {!loading && !error && (!detailValid || !packetValid) && (
            <div className="m-6 space-y-3">
              <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                <div className="font-semibold">
                  Lead loaded, but its detail payload is incomplete.
                </div>
                <ul className="mt-2 list-disc pl-5 text-amber-800">
                  {!detailValid && (
                    <li>
                      Lead detail (transcript, vehicle interest, profile) is
                      missing or malformed.
                    </li>
                  )}
                  {!packetValid && (
                    <li>
                      Handoff packet (customer info, budget, suggested
                      message) is missing or malformed.
                    </li>
                  )}
                </ul>
                <div className="mt-3 text-xs text-amber-700">
                  Try refreshing the dashboard. If this keeps happening,
                  open the browser console — the underlying fetch failure
                  is logged there.
                </div>
              </div>
              {detail?.lead && (
                <div className="rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Partial info recovered
                  </div>
                  <div className="mt-1">
                    <span className="font-semibold">{detail.lead.name}</span>
                    {detail.lead.phone ? ` · ${detail.lead.phone}` : ""}
                    {detail.lead.email ? ` · ${detail.lead.email}` : ""}
                  </div>
                </div>
              )}

              {/* Temporary raw payload preview so the operator can see
                  exactly what came back when the modal would otherwise
                  be blank. Collapsed by default; click to expand. */}
              <details className="rounded-md border border-slate-200 bg-slate-50">
                <summary className="cursor-pointer select-none px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-600 hover:bg-slate-100">
                  Raw payload (debug)
                </summary>
                <div className="space-y-3 px-4 py-3 text-xs">
                  <div>
                    <div className="mb-1 font-semibold text-slate-700">
                      detail (
                      <span
                        className={
                          detailValid ? "text-emerald-700" : "text-red-700"
                        }
                      >
                        {detailValid ? "valid" : "invalid"}
                      </span>
                      )
                    </div>
                    <pre className="max-h-48 overflow-auto rounded bg-white p-2 text-[11px] leading-snug text-slate-700 ring-1 ring-slate-200">
                      {detail
                        ? JSON.stringify(detail, null, 2)
                        : "null / undefined"}
                    </pre>
                  </div>
                  <div>
                    <div className="mb-1 font-semibold text-slate-700">
                      packet (
                      <span
                        className={
                          packetValid ? "text-emerald-700" : "text-red-700"
                        }
                      >
                        {packetValid ? "valid" : "invalid"}
                      </span>
                      )
                    </div>
                    <pre className="max-h-48 overflow-auto rounded bg-white p-2 text-[11px] leading-snug text-slate-700 ring-1 ring-slate-200">
                      {packet
                        ? JSON.stringify(packet, null, 2)
                        : "null / undefined"}
                    </pre>
                  </div>
                </div>
              </details>
            </div>
          )}

          {detailValid && packetValid && detail && packet && (
            <div className="grid gap-6 p-6 md:grid-cols-[1fr_320px]">
              {/* Left column: handoff */}
              <div className="space-y-5">
                {/* Source (M25.1) — attribution surface for referral +
                    listing_form leads. Omitted for chat / walk_in /
                    phone / other channels where no attribution
                    exists. */}
                {(() => {
                  const sourceLine = computeSourceLine(detail.lead);
                  if (!sourceLine) return null;
                  return (
                    <section
                      data-testid="lead-source-section"
                      className="card border border-slate-200 p-4"
                    >
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Source
                      </div>
                      <div
                        data-testid="lead-source-line"
                        className="mt-1 text-sm text-brand-ink"
                      >
                        {sourceLine}
                      </div>
                    </section>
                  );
                })()}
                {/* Customer */}
                <section className="card border border-slate-200 p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Customer
                  </div>
                  <div className="mt-1 text-base font-bold text-brand-ink">
                    {packet.customer.name}
                  </div>
                  <div className="text-sm text-slate-600">
                    {packet.customer.phone || "—"}
                    {packet.customer.email
                      ? ` · ${packet.customer.email}`
                      : ""}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs">
                    {packet.urgency_label && (
                      <span className="rounded-md bg-amber-50 px-2 py-0.5 text-amber-700">
                        {URGENCY_LABEL[packet.urgency] ?? packet.urgency_label}
                      </span>
                    )}
                    {packet.budget.target_monthly_payment && (
                      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
                        {formatCurrency(packet.budget.target_monthly_payment)}
                        /mo target
                      </span>
                    )}
                    {packet.budget.down_payment && (
                      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
                        {formatCurrency(packet.budget.down_payment)} down
                      </span>
                    )}
                    {packet.credit_range && (
                      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700 capitalize">
                        Credit: {packet.credit_range}
                      </span>
                    )}
                  </div>
                  {packet.trade_in && (
                    <div className="mt-2 text-xs text-slate-600">
                      <span className="font-semibold">Trade-in:</span>{" "}
                      {packet.trade_in}
                    </div>
                  )}
                </section>

                {/* Vehicles */}
                <section>
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Interested vehicles
                  </div>
                  {detail.interested_vehicles.length === 0 ? (
                    <div className="rounded-md border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                      No vehicles flagged.
                    </div>
                  ) : (
                    <ul className="space-y-2">
                      {detail.interested_vehicles.map((v) => (
                        <li
                          key={v.id}
                          className="flex items-center gap-3 rounded-lg border border-slate-200 p-3"
                        >
                          {v.image_url ? (
                            <img
                              src={v.image_url}
                              alt={v.display_name}
                              className="h-12 w-20 rounded object-cover"
                            />
                          ) : (
                            <div className="h-12 w-20 rounded bg-slate-100" />
                          )}
                          <div className="flex-1">
                            <div className="text-sm font-semibold text-brand-ink">
                              {v.display_name}
                            </div>
                            <div className="text-xs text-slate-500">
                              Stock #{v.stock_number} · {v.condition}
                            </div>
                          </div>
                          <div className="text-sm font-bold text-brand-blue">
                            {formatCurrency(v.price)}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                {/* M25.2 — Schedule test drive collapsible. Modal-
                    attached only per §5.d; DealerAiSalesTestDrives
                    remains the canonical visibility surface. */}
                <section
                  data-testid="schedule-test-drive-section"
                  className="rounded-lg border border-slate-200"
                >
                  <button
                    type="button"
                    onClick={() => {
                      setTestDriveOpen((prev) => !prev);
                      if (!testDriveOpen) setTestDriveJustRecorded(false);
                    }}
                    data-testid="schedule-test-drive-toggle"
                    aria-expanded={testDriveOpen}
                    className="flex w-full items-center justify-between px-3 py-2 text-left"
                  >
                    <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Schedule test drive
                    </span>
                    <span className="flex items-center gap-2">
                      {testDriveJustRecorded ? (
                        <span
                          data-testid="schedule-test-drive-success"
                          className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700"
                        >
                          Recorded
                        </span>
                      ) : null}
                      {testDriveOpen ? (
                        <ChevronUp className="h-4 w-4 text-slate-500" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-slate-500" />
                      )}
                    </span>
                  </button>
                  {testDriveOpen ? (
                    <div className="border-t border-slate-100 p-3">
                      <RecordTestDriveForm
                        leadId={detail.lead.id}
                        suggestedVehicles={detail.interested_vehicles.map(
                          (v) => ({
                            id: v.id,
                            stock_number: v.stock_number,
                            display_name: v.display_name,
                            price: v.price,
                            image_url: v.image_url,
                          }),
                        )}
                        onCreated={() => {
                          setTestDriveOpen(false);
                          setTestDriveJustRecorded(true);
                        }}
                        onCancel={() => setTestDriveOpen(false)}
                      />
                    </div>
                  ) : null}
                </section>

                {/* Summary */}
                <section>
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    AI conversation summary
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-brand-mist/40 p-3 text-sm leading-relaxed text-brand-ink">
                    {packet.conversation_summary || "—"}
                  </div>
                </section>

                {/* Next action */}
                <section>
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Recommended next action
                  </div>
                  <div className="rounded-lg border border-emerald-100 bg-emerald-50 p-3 text-sm leading-relaxed text-emerald-900">
                    {packet.recommended_next_action || "Reach out within 24 hours."}
                  </div>
                </section>

                {/* Suggested message */}
                <section>
                  <div className="mb-2 flex items-center justify-between">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Suggested first message
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        copyToClipboard(packet.suggested_message, "message")
                      }
                      className="btn-ghost h-8 px-2 text-xs"
                    >
                      {copied === "message" ? (
                        <Check className="h-3.5 w-3.5" />
                      ) : (
                        <Clipboard className="h-3.5 w-3.5" />
                      )}
                      {copied === "message" ? "Copied" : "Copy message"}
                    </button>
                  </div>
                  <div className="whitespace-pre-wrap rounded-lg border border-slate-200 bg-white p-3 text-sm leading-relaxed text-brand-ink">
                    {packet.suggested_message}
                  </div>
                </section>

                {/* Chat history */}
                {detail.messages.length > 0 && (
                  <section>
                    <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Conversation transcript
                    </div>
                    <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3 max-h-64 overflow-y-auto">
                      {detail.messages.map((m) => (
                        <div
                          key={m.id}
                          className={cn(
                            "flex gap-2 text-sm",
                            m.role === "user"
                              ? "text-brand-ink"
                              : m.role === "system"
                                ? "text-amber-700"
                                : "text-slate-700",
                          )}
                        >
                          <span className="mt-0.5 shrink-0">
                            {m.role === "user" ? (
                              <User className="h-3.5 w-3.5 text-brand-blue" />
                            ) : m.role === "system" ? (
                              <span className="text-[10px] font-bold uppercase">
                                sys
                              </span>
                            ) : (
                              <Bot className="h-3.5 w-3.5 text-slate-700" />
                            )}
                          </span>
                          <span className="whitespace-pre-wrap">{m.content}</span>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </div>

              {/* Right column: actions */}
              <aside className="space-y-3">
                <button
                  type="button"
                  onClick={() => copyToClipboard(packet.text, "text")}
                  className="btn-primary w-full justify-center"
                >
                  {copied === "text" ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Clipboard className="h-4 w-4" />
                  )}
                  {copied === "text" ? "Copied!" : "Copy full handoff"}
                </button>
                <button
                  type="button"
                  onClick={markHandedOff}
                  disabled={building || packet.handed_off}
                  className="btn-ghost w-full justify-center"
                >
                  {building ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4" />
                  )}
                  {packet.handed_off
                    ? "Handed off"
                    : "Mark as handed off"}
                </button>
                <div className="rounded-lg border border-dashed border-slate-200 p-3 text-xs text-slate-500">
                  No emails or texts are sent automatically. Use Copy handoff to
                  paste into your CRM, dialer, or messaging tool.
                </div>
              </aside>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
