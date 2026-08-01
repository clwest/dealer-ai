// Milestone 4 · Increment 7 — one WorkOrder card.
//
// Composes WorkOrderStatusBadge, PartRow, and a compact action bar
// that varies per current WO status:
//
//   draft       → Approve / Cancel
//   approved    → Start / Revise estimate / Cancel
//   in_progress → Complete / Cancel
//   completed   → (read-only)
//   cancelled   → (read-only)
//
// Also exposes the "Add part" affordance while the WO is in a
// nonterminal state and the operator has write role.
//
// The card intentionally displays every provenance field
// (approved_by / approved_at / started_* / completed_* / cancelled_*
// with cancellation_reason) so the operator can see the full
// timeline at a glance — matches the M2.7 / M3.7 provenance
// discipline.

import { useState } from "react";
import { Ban, ListPlus, Loader2, PackagePlus, Send } from "lucide-react";

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
  addWorkOrderPart,
  approveWorkOrder,
  cancelWorkOrder,
  completeWorkOrder,
  detachFinding,
  draftVendorComm,
  reviseEstimate,
  startWorkOrder,
  VENDOR_COMMUNICATION_CHANNEL_CHOICES,
  VENDOR_COMMUNICATION_KIND_CHOICES,
  WORK_ORDER_PART_SOURCE_TYPE_CHOICES,
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
  canEdit: boolean;
  onWorkOrderUpdated: (wo: WorkOrder) => void;
  onCommDrafted: (comm: VendorCommunication) => void;
}

export function WorkOrderCard({
  wo,
  canEdit,
  onWorkOrderUpdated,
  onCommDrafted,
}: WorkOrderCardProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAddPart, setShowAddPart] = useState(false);
  const [showDraftComm, setShowDraftComm] = useState(false);
  const [showRevise, setShowRevise] = useState(false);

  // Add-part form state.
  const [partName, setPartName] = useState("");
  const [partQty, setPartQty] = useState("1");
  const [partCost, setPartCost] = useState("");
  const [partSource, setPartSource] = useState("in_stock");

  // Revise-estimate form state.
  const [newEstimate, setNewEstimate] = useState(wo.estimated_cost ?? "");

  // Complete form state.
  const [actualCost, setActualCost] = useState("");

  // Cancel form state.
  const [cancelReason, setCancelReason] = useState("");
  const [showCancel, setShowCancel] = useState(false);

  // Comm draft form state.
  const [commKind, setCommKind] = useState("vendor_comm");
  const [commChannel, setCommChannel] = useState("email");

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

  async function _approve() {
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
      setError("New estimated cost is required.");
      return;
    }
    const res = await _guard(() =>
      reviseEstimate(wo.id, { new_estimated_cost: newEstimate }),
    );
    if (res) {
      onWorkOrderUpdated(res.work_order);
      setShowRevise(false);
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

  const isTerminal = wo.status === "completed" || wo.status === "cancelled";

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
        {/* Cost provenance */}
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
                  {canEdit && wo.status === "draft" && (
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

        {/* Cancellation-reason narrative on cancelled rows */}
        {wo.status === "cancelled" && wo.cancellation_reason && (
          <div className="rounded bg-slate-100 p-2 text-xs">
            <div className="font-medium">Cancellation reason</div>
            <div className="text-slate-700">{wo.cancellation_reason}</div>
          </div>
        )}

        <Separator />

        {/* Provenance timeline */}
        <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
          {wo.approved_at && (
            <div>
              <div className="font-medium text-foreground">Approved</div>
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
        {canEdit && wo.status === "draft" && (
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
              onClick={_approve}
              disabled={saving || wo.findings.length === 0}
              title={
                wo.findings.length === 0
                  ? "Attach at least one finding first"
                  : undefined
              }
            >
              Approve
            </Button>
          </>
        )}
        {canEdit && wo.status === "approved" && (
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
              <ListPlus className="h-3 w-3" />
              Revise estimate
            </Button>
            <Button size="sm" onClick={_start} disabled={saving}>
              Start
            </Button>
          </>
        )}
        {canEdit && wo.status === "in_progress" && (
          <>
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
              Complete
            </Button>
          </>
        )}
      </CardFooter>

      {/* Revise-estimate form */}
      {showRevise && (
        <div className="border-t bg-muted/40 p-3 text-xs space-y-2">
          <Input
            placeholder="New estimated cost"
            value={newEstimate}
            onChange={(e) => setNewEstimate(e.target.value)}
            className="h-8 text-xs"
          />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setShowRevise(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={_revise} disabled={saving}>
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
