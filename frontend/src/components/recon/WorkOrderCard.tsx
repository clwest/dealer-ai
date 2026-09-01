// SESSION_227 — recon-one-card. WorkOrderCard shows the WO's state
// and every action the operator can take on it, on the same card.
//
// Buttons name what they do (product word — "Authorize $N", not
// "Approve"). Disabled reasons live in the card as visible text, not
// hover tooltips. Revise-estimate requires a reason. "Add a job
// found during work" is available while the WO is in progress —
// techs find things on the lift and that new job is a first-class
// finding, not an edit to the existing estimate. Legacy drafts with
// no linked finding get a "Link finding" picker inline, so the WO
// stops being a dead end.
//
// Completed WOs show the estimate → actual story in one line, with
// the raw ledger rows behind a disclosure.

import { useMemo, useState } from "react";
import {
  Ban,
  ChevronRight,
  Link2,
  Loader2,
  PackagePlus,
  Send,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { PartRow } from "@/components/recon/PartRow";
import { WorkOrderStatusBadge } from "@/components/recon/WorkOrderStatusBadge";
import { ApiError } from "@/lib/authFetch";
import {
  addFindingDuringWork,
  addWorkOrderPart,
  approveWorkOrder,
  attachFindings,
  cancelWorkOrder,
  completeWorkOrder,
  detachFinding,
  draftVendorComm,
  reviseEstimate,
  startWorkOrder,
  CONDITION_CATEGORY_CHOICES,
  CONDITION_SEVERITY_CHOICES,
  VENDOR_COMMUNICATION_CHANNEL_CHOICES,
  VENDOR_COMMUNICATION_KIND_CHOICES,
  WORK_ORDER_PART_SOURCE_TYPE_CHOICES,
  type ReconDashboardFinding,
  type VendorCommunication,
  type WorkOrder,
  type WorkOrderPart,
} from "@/lib/api";

function _formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function _humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return "This action conflicts with the current state. Refresh and try again.";
    if (err.status === 422) return "The AI draft was rejected by the safety scrub. Review the source data and retry.";
    if (err.status === 502) return "The AI service returned no draft. Retry in a moment.";
    if (err.status === 400) return "Invalid input. Please check the fields.";
    if (err.status === 404) return "Not found. Refresh the page.";
    return `Server returned ${err.status}.`;
  }
  return "Request failed.";
}

export interface WorkOrderCardProps {
  wo: WorkOrder;
  stock: string;
  canEdit: boolean;
  // Undecided-decision role message — surfaced as the reason a role
  // cannot authorize (never as a tooltip). Empty means the role can
  // authorize.
  authorizeBlockedReason?: string | null;
  // Findings on the latest completed report — the picker for a
  // legacy draft WO that has no linked finding uses this list.
  reportFindings?: ReconDashboardFinding[];
  // Which report id "add finding found during work" writes into. When
  // omitted, the "found on the lift" affordance stays hidden.
  activeReportId?: number | null;
  onWorkOrderUpdated: (wo: WorkOrder) => void;
  onCommDrafted: (comm: VendorCommunication) => void;
  onFindingDiscovered?: () => void;
}

export function WorkOrderCard({
  wo,
  stock,
  canEdit,
  authorizeBlockedReason,
  reportFindings = [],
  activeReportId,
  onWorkOrderUpdated,
  onCommDrafted,
  onFindingDiscovered,
}: WorkOrderCardProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAddPart, setShowAddPart] = useState(false);
  const [showDraftComm, setShowDraftComm] = useState(false);
  const [showRevise, setShowRevise] = useState(false);
  const [showAddFoundJob, setShowAddFoundJob] = useState(false);
  const [showLinkFinding, setShowLinkFinding] = useState(false);
  const [showLedger, setShowLedger] = useState(false);

  // Add-part form state.
  const [partName, setPartName] = useState("");
  const [partQty, setPartQty] = useState("1");
  const [partCost, setPartCost] = useState("");
  const [partSource, setPartSource] = useState("in_stock");

  // Revise-estimate form state.
  const [newEstimate, setNewEstimate] = useState(wo.estimated_cost ?? "");
  const [reviseReason, setReviseReason] = useState("");

  // Add-a-found-job form state.
  const [foundCategory, setFoundCategory] = useState(
    CONDITION_CATEGORY_CHOICES[0].value,
  );
  const [foundSeverity, setFoundSeverity] = useState("required");
  const [foundDescription, setFoundDescription] = useState("");
  const [foundEstimate, setFoundEstimate] = useState("");

  // Complete form state.
  const [actualCost, setActualCost] = useState("");

  // Cancel form state.
  const [cancelReason, setCancelReason] = useState("");
  const [showCancel, setShowCancel] = useState(false);

  // Comm draft form state.
  const [commKind, setCommKind] = useState("vendor_comm");
  const [commChannel, setCommChannel] = useState("email");

  // Link-finding picker state.
  const [linkFindingIds, setLinkFindingIds] = useState<number[]>([]);

  const hasFinding = wo.findings.length > 0;
  const isDraft = wo.status === "draft";
  const isApproved = wo.status === "approved";
  const isInProgress = wo.status === "in_progress";
  const isTerminal = wo.status === "completed" || wo.status === "cancelled";
  const authorizeAmount = wo.estimated_cost ?? "0.00";

  const authorizeBlocked = useMemo<string | null>(() => {
    if (!hasFinding) return "Attach a finding to authorize.";
    if (authorizeBlockedReason) return authorizeBlockedReason;
    return null;
  }, [hasFinding, authorizeBlockedReason]);

  async function _guard<T>(fn: () => Promise<T>): Promise<T | null> {
    setSaving(true);
    setError(null);
    try {
      return await fn();
    } catch (err) {
      setError(_humanizeError(err));
      return null;
    } finally {
      setSaving(false);
    }
  }

  async function _authorize() {
    const res = await _guard(() => approveWorkOrder(wo.id));
    if (res) onWorkOrderUpdated(res.work_order);
  }

  async function _start() {
    const res = await _guard(() => startWorkOrder(wo.id));
    if (res) onWorkOrderUpdated(res.work_order);
  }

  async function _complete() {
    if (!actualCost.trim()) {
      setError("Actual cost is required.");
      return;
    }
    const res = await _guard(() =>
      completeWorkOrder(wo.id, { actual_cost: actualCost }),
    );
    if (res) onWorkOrderUpdated(res.work_order);
  }

  async function _cancel() {
    const needsReason =
      wo.status === "approved" || wo.status === "in_progress";
    if (needsReason && !cancelReason.trim()) {
      setError("A cancellation reason is required at this state.");
      return;
    }
    const res = await _guard(() =>
      cancelWorkOrder(wo.id, {
        cancellation_reason: cancelReason,
      }),
    );
    if (res) {
      onWorkOrderUpdated(res.work_order);
      setShowCancel(false);
    }
  }

  async function _revise() {
    if (!newEstimate.trim()) {
      setError("A new estimated cost is required.");
      return;
    }
    if (!reviseReason.trim()) {
      setError("A reason is required — this shows on the Ledger.");
      return;
    }
    const res = await _guard(() =>
      reviseEstimate(wo.id, {
        new_estimated_cost: newEstimate,
        reason: reviseReason,
      }),
    );
    if (res) {
      onWorkOrderUpdated(res.work_order);
      setShowRevise(false);
      setReviseReason("");
    }
  }

  async function _addFoundJob() {
    if (activeReportId == null) {
      setError("No completed report on this vehicle to attach to.");
      return;
    }
    if (!foundDescription.trim()) {
      setError("A description is required for the found job.");
      return;
    }
    const ok = await _guard(async () => {
      await addFindingDuringWork(stock, activeReportId, {
        category: foundCategory,
        severity: foundSeverity,
        description: foundDescription,
        estimated_cost: foundEstimate.trim() || null,
        discovered_on_work_order_id: wo.id,
      });
      return true;
    });
    if (ok) {
      setShowAddFoundJob(false);
      setFoundDescription("");
      setFoundEstimate("");
      onFindingDiscovered?.();
    }
  }

  async function _addPart() {
    if (!partName.trim()) {
      setError("Part name is required.");
      return;
    }
    const res = await _guard(() =>
      addWorkOrderPart(wo.id, {
        name: partName,
        quantity: parseInt(partQty, 10) || 1,
        unit_cost: partCost.trim() || null,
        source_type: partSource,
      }),
    );
    if (res) {
      onWorkOrderUpdated({ ...wo, parts: [...wo.parts, res.part] });
      setShowAddPart(false);
      setPartName("");
      setPartCost("");
      setPartQty("1");
    }
  }

  async function _draftComm() {
    const res = await _guard(() =>
      draftVendorComm(wo.id, {
        kind: commKind,
        channel: commChannel,
      }),
    );
    if (res) {
      onCommDrafted(res.communication);
      setShowDraftComm(false);
    }
  }

  async function _detachFinding(findingId: number) {
    const ok = await _guard(async () => {
      await detachFinding(wo.id, findingId);
      return true;
    });
    if (ok) {
      onWorkOrderUpdated({
        ...wo,
        findings: wo.findings.filter((f) => f.finding_id !== findingId),
      });
    }
  }

  async function _linkFinding() {
    if (linkFindingIds.length === 0) {
      setError("Pick at least one finding to link.");
      return;
    }
    const res = await _guard(() => attachFindings(wo.id, linkFindingIds));
    if (res) {
      onWorkOrderUpdated(res.work_order);
      setShowLinkFinding(false);
      setLinkFindingIds([]);
    }
  }

  function _updatePart(updated: WorkOrderPart) {
    onWorkOrderUpdated({
      ...wo,
      parts: wo.parts.map((p) => (p.id === updated.id ? updated : p)),
    });
  }

  function _deletePart(partId: number) {
    onWorkOrderUpdated({
      ...wo,
      parts: wo.parts.filter((p) => p.id !== partId),
    });
  }

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
        <div className="space-y-1">
          <CardTitle className="text-base">
            {wo.category} · {wo.venue}
            {wo.vendor && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                → {wo.vendor.name}
              </span>
            )}
          </CardTitle>
          <div className="text-xs text-muted-foreground">
            WO #{wo.id} · created {_formatDateTime(wo.created_at)}
          </div>
        </div>
        <WorkOrderStatusBadge status={wo.status} />
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Estimate → actual story on completed. */}
        {wo.status === "completed" ? (
          <div className="rounded border bg-emerald-50 p-2 text-sm text-emerald-900">
            Estimated {wo.estimated_cost != null ? `$${wo.estimated_cost}` : "—"} ·
            actual {wo.actual_cost != null ? `$${wo.actual_cost}` : "—"}
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div>
              <div className="text-muted-foreground">Estimated</div>
              <div className="font-medium">
                {wo.estimated_cost != null ? `$${wo.estimated_cost}` : "—"}
              </div>
            </div>
            <div>
              <div className="text-muted-foreground">Authorized</div>
              <div className="font-medium">
                {wo.authorized_cost != null ? `$${wo.authorized_cost}` : "—"}
              </div>
            </div>
            <div>
              <div className="text-muted-foreground">Actual</div>
              <div className="font-medium">
                {wo.actual_cost != null ? `$${wo.actual_cost}` : "—"}
              </div>
            </div>
          </div>
        )}

        {/* Finding links */}
        {wo.findings.length > 0 && (
          <div>
            <div className="mb-1 text-xs font-medium">Linked findings</div>
            <div className="space-y-1">
              {wo.findings.map((f) => (
                <div
                  key={f.finding_id}
                  className="flex items-start justify-between rounded border p-2 text-xs"
                >
                  <div className="flex-1">
                    <div>{f.description}</div>
                    <div className="text-muted-foreground">
                      Finding #{f.finding_id} · {f.category} · {f.severity}
                    </div>
                  </div>
                  {canEdit && isDraft && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 text-xs text-destructive"
                      disabled={saving}
                      onClick={() => _detachFinding(f.finding_id)}
                    >
                      Detach
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Link-finding control for a draft WO with no findings —
            SESSION_227 fixes the dead-end case. */}
        {canEdit && isDraft && !hasFinding && (
          <div className="rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900 space-y-2">
            <div>
              This draft is not linked to any finding on the latest
              inspection. Attach one to authorize.
            </div>
            {reportFindings.length === 0 ? (
              <div className="text-muted-foreground">
                No findings available on the latest completed report.
              </div>
            ) : !showLinkFinding ? (
              <Button
                size="sm"
                className="gap-1"
                onClick={() => setShowLinkFinding(true)}
              >
                <Link2 className="h-3 w-3" />
                Link finding
              </Button>
            ) : (
              <div className="space-y-1">
                {reportFindings.map((f) => (
                  <label
                    key={f.id}
                    className="flex cursor-pointer items-start gap-2 rounded border bg-white p-2 text-xs"
                  >
                    <input
                      type="checkbox"
                      className="mt-0.5"
                      checked={linkFindingIds.includes(f.id)}
                      onChange={() =>
                        setLinkFindingIds((prev) =>
                          prev.includes(f.id)
                            ? prev.filter((x) => x !== f.id)
                            : [...prev, f.id],
                        )
                      }
                    />
                    <div className="flex-1">
                      <div>{f.description}</div>
                      <div className="text-muted-foreground">
                        {f.category} · {f.severity}
                      </div>
                    </div>
                  </label>
                ))}
                <div className="flex justify-end gap-2 pt-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setShowLinkFinding(false);
                      setLinkFindingIds([]);
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={_linkFinding}
                    disabled={saving || linkFindingIds.length === 0}
                  >
                    Link {linkFindingIds.length || ""}
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Parts */}
        {wo.parts.length > 0 && (
          <div>
            <div className="mb-1 text-xs font-medium">Parts</div>
            <div className="space-y-1">
              {wo.parts.map((p) => (
                <PartRow
                  key={p.id}
                  part={p}
                  woStatus={wo.status}
                  canEdit={canEdit && !isTerminal}
                  onPartUpdated={_updatePart}
                  onPartDeleted={_deletePart}
                />
              ))}
            </div>
          </div>
        )}

        {/* Revisions history — surfaces WHY the estimate moved. */}
        {wo.estimate_revisions.length > 0 && (
          <div>
            <div className="mb-1 text-xs font-medium">Revisions</div>
            <div className="space-y-1">
              {wo.estimate_revisions.map((r) => (
                <div
                  key={r.id}
                  className="rounded border bg-slate-50 p-2 text-xs"
                >
                  <div>
                    {r.from_amount != null ? `$${r.from_amount}` : "—"} → $
                    {r.to_amount}
                  </div>
                  <div className="text-slate-700">{r.reason}</div>
                  <div className="text-muted-foreground">
                    {r.revised_by ?? "—"} · {_formatDateTime(r.revised_at)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Add-part form (collapsible) */}
        {canEdit && !isTerminal && (
          <div className="space-y-1">
            {!showAddPart ? (
              <Button
                size="sm"
                variant="ghost"
                className="gap-1 text-xs"
                onClick={() => setShowAddPart(true)}
              >
                <PackagePlus className="h-3 w-3" />
                Add part
              </Button>
            ) : (
              <div className="rounded border bg-muted/40 p-2 text-xs space-y-2">
                <Input
                  placeholder="Part name"
                  value={partName}
                  onChange={(e) => setPartName(e.target.value)}
                />
                <div className="grid grid-cols-3 gap-2">
                  <Input
                    placeholder="Qty"
                    type="number"
                    value={partQty}
                    onChange={(e) => setPartQty(e.target.value)}
                  />
                  <Input
                    placeholder="Unit cost"
                    value={partCost}
                    onChange={(e) => setPartCost(e.target.value)}
                  />
                  <select
                    value={partSource}
                    onChange={(e) => setPartSource(e.target.value)}
                    className="rounded border bg-background px-2 py-1 text-xs"
                  >
                    {WORK_ORDER_PART_SOURCE_TYPE_CHOICES.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex justify-end gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowAddPart(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={_addPart}
                    disabled={saving || !partName.trim()}
                  >
                    Save part
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Draft vendor comm affordance */}
        {canEdit && !isTerminal && (
          <div className="space-y-1">
            {!showDraftComm ? (
              <Button
                size="sm"
                variant="ghost"
                className="gap-1 text-xs"
                onClick={() => setShowDraftComm(true)}
              >
                <Send className="h-3 w-3" />
                Draft vendor comm
              </Button>
            ) : (
              <div className="rounded border bg-muted/40 p-2 text-xs space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <select
                    value={commKind}
                    onChange={(e) => setCommKind(e.target.value)}
                    className="rounded border bg-background px-2 py-1 text-xs"
                  >
                    {VENDOR_COMMUNICATION_KIND_CHOICES.filter(
                      (c) => c.value !== "narrative",
                    ).map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                  <select
                    value={commChannel}
                    onChange={(e) => setCommChannel(e.target.value)}
                    className="rounded border bg-background px-2 py-1 text-xs"
                  >
                    {VENDOR_COMMUNICATION_CHANNEL_CHOICES.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex justify-end gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowDraftComm(false)}
                  >
                    Cancel
                  </Button>
                  <Button size="sm" onClick={_draftComm} disabled={saving}>
                    {saving && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                    Draft
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Add a job found during work — SESSION_227. */}
        {canEdit && (isApproved || isInProgress) && activeReportId != null && (
          <div className="space-y-1">
            {!showAddFoundJob ? (
              <Button
                size="sm"
                variant="ghost"
                className="gap-1 text-xs"
                onClick={() => setShowAddFoundJob(true)}
              >
                <PackagePlus className="h-3 w-3" />
                Add a job found during work
              </Button>
            ) : (
              <div className="rounded border bg-muted/40 p-2 text-xs space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <select
                    value={foundCategory}
                    onChange={(e) => setFoundCategory(e.target.value)}
                    className="rounded border bg-background px-2 py-1 text-xs"
                  >
                    {CONDITION_CATEGORY_CHOICES.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                  <select
                    value={foundSeverity}
                    onChange={(e) => setFoundSeverity(e.target.value)}
                    className="rounded border bg-background px-2 py-1 text-xs"
                  >
                    {CONDITION_SEVERITY_CHOICES.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>
                <Input
                  placeholder="What did the tech find?"
                  value={foundDescription}
                  onChange={(e) => setFoundDescription(e.target.value)}
                />
                <Input
                  placeholder="Estimated cost (optional)"
                  value={foundEstimate}
                  onChange={(e) => setFoundEstimate(e.target.value)}
                />
                <div className="flex justify-end gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowAddFoundJob(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={_addFoundJob}
                    disabled={saving || !foundDescription.trim()}
                  >
                    Save finding
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Cancellation-reason narrative on cancelled rows */}
        {wo.status === "cancelled" && wo.cancellation_reason && (
          <div className="rounded bg-slate-100 p-2 text-xs">
            <div className="font-medium">Cancellation reason</div>
            <div className="text-slate-700">{wo.cancellation_reason}</div>
          </div>
        )}

        {/* Ledger rows disclosure — SESSION_227 replaces bare journal
            lines with a collapsed disclosure so completed rows don't
            drown the page. */}
        {wo.ledger_rows.length > 0 && (
          <div className="space-y-1">
            <button
              type="button"
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => setShowLedger((v) => !v)}
            >
              <ChevronRight
                className={`h-3 w-3 transition-transform ${
                  showLedger ? "rotate-90" : ""
                }`}
              />
              Ledger rows ({wo.ledger_rows.length})
            </button>
            {showLedger && (
              <div className="space-y-1">
                {wo.ledger_rows.map((r) => (
                  <div
                    key={r.id}
                    className="rounded border bg-slate-50 p-2 text-xs"
                  >
                    <div className="flex justify-between">
                      <div className="font-mono text-[10px] text-muted-foreground">
                        {r.reference}
                      </div>
                      <div
                        className={
                          Number(r.amount) < 0
                            ? "text-destructive font-medium"
                            : "font-medium"
                        }
                      >
                        ${r.amount}
                      </div>
                    </div>
                    {r.notes && (
                      <div className="text-slate-700">{r.notes}</div>
                    )}
                    <div className="text-muted-foreground">
                      {_formatDateTime(r.incurred_at)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <Separator />

        {/* Provenance timeline */}
        <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
          {wo.approved_at && (
            <div>
              <div className="font-medium text-foreground">Authorized</div>
              <div>{wo.approved_by ?? "—"}</div>
              <div>{_formatDateTime(wo.approved_at)}</div>
            </div>
          )}
          {wo.started_at && (
            <div>
              <div className="font-medium text-foreground">Started</div>
              <div>{wo.started_by ?? "—"}</div>
              <div>{_formatDateTime(wo.started_at)}</div>
            </div>
          )}
          {wo.completed_at && (
            <div>
              <div className="font-medium text-foreground">Completed</div>
              <div>{wo.completed_by ?? "—"}</div>
              <div>{_formatDateTime(wo.completed_at)}</div>
            </div>
          )}
          {wo.cancelled_at && (
            <div>
              <div className="font-medium text-foreground">Cancelled</div>
              <div>{wo.cancelled_by ?? "—"}</div>
              <div>{_formatDateTime(wo.cancelled_at)}</div>
            </div>
          )}
        </div>

        {error && <div className="text-xs text-destructive">{error}</div>}
      </CardContent>

      <CardFooter className="flex flex-wrap justify-end gap-2 pt-0">
        {canEdit && isDraft && (
          <>
            <Button
              size="sm"
              variant="ghost"
              className="gap-1 text-xs text-destructive"
              onClick={() => setShowCancel(true)}
            >
              <Ban className="h-3 w-3" />
              Cancel WO
            </Button>
            {authorizeBlocked ? (
              <div className="text-xs text-amber-800 self-center">
                {authorizeBlocked}
              </div>
            ) : (
              <Button size="sm" onClick={_authorize} disabled={saving}>
                Authorize ${authorizeAmount}
              </Button>
            )}
          </>
        )}
        {canEdit && isApproved && (
          <>
            <Button
              size="sm"
              variant="ghost"
              className="gap-1 text-xs text-destructive"
              onClick={() => setShowCancel(true)}
            >
              <Ban className="h-3 w-3" />
              Cancel WO
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="gap-1 text-xs"
              onClick={() => setShowRevise(true)}
            >
              Revise estimate
            </Button>
            <Button size="sm" onClick={_start} disabled={saving}>
              Start
            </Button>
          </>
        )}
        {canEdit && isInProgress && (
          <>
            <Button
              size="sm"
              variant="ghost"
              className="gap-1 text-xs"
              onClick={() => setShowRevise(true)}
            >
              Revise estimate
            </Button>
            <Input
              placeholder="Actual cost"
              value={actualCost}
              onChange={(e) => setActualCost(e.target.value)}
              className="h-8 w-28 text-xs"
            />
            <Button
              size="sm"
              variant="ghost"
              className="gap-1 text-xs text-destructive"
              onClick={() => setShowCancel(true)}
            >
              <Ban className="h-3 w-3" />
              Cancel WO
            </Button>
            <Button size="sm" onClick={_complete} disabled={saving}>
              Complete — actual ${actualCost || "…"}
            </Button>
          </>
        )}
      </CardFooter>

      {/* Revise-estimate form — SESSION_227 requires a reason. */}
      {showRevise && (
        <div className="border-t bg-muted/40 p-3 text-xs space-y-2">
          <Input
            placeholder="New estimated cost"
            value={newEstimate}
            onChange={(e) => setNewEstimate(e.target.value)}
            className="h-8 text-xs"
          />
          <Textarea
            placeholder="Why is the number changing? Shows on the Ledger and stays on the WO's history."
            value={reviseReason}
            onChange={(e) => setReviseReason(e.target.value)}
            rows={2}
            className="text-xs"
          />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setShowRevise(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={_revise}
              disabled={saving || !reviseReason.trim()}
            >
              Save revision
            </Button>
          </div>
        </div>
      )}

      {/* Cancel form */}
      {showCancel && (
        <div className="border-t bg-muted/40 p-3 text-xs space-y-2">
          <Textarea
            placeholder={
              wo.status === "draft"
                ? "Reason (optional for draft cancellation)"
                : "Reason is required — a vendor was told this work was authorized."
            }
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
            rows={2}
            className="text-xs"
          />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setShowCancel(false)}>
              Back
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={_cancel}
              disabled={saving}
            >
              Confirm cancel
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}
