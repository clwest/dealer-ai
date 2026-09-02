// SESSION_227 — recon-one-card. The recon page is finding-centric.
//
// One card per finding on the latest completed inspection report.
// The card carries the finding, the decision, and — once it exists
// — the work order and every action the operator can take. The
// standalone "Create work order" form is gone.
//
// Orphan WOs (WOs with no linked finding on the latest report — the
// legacy WO #8 case) still render below the job list with a
// "Link finding" affordance inside the card, so the operator has a
// way out that isn't Cancel.
//
// Role gating: write affordances are gated to recon_manager /
// sales_manager / dealer_owner (WRITE_ROLES). Server authorization
// remains authoritative — the M4.6 endpoints enforce it.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ClipboardList,
  Loader2,
  Plus,
  Wand2,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { JobCard } from "@/components/recon/JobCard";
import { VendorCommDraftPanel } from "@/components/recon/VendorCommDraftPanel";
import { VendorPickerModal } from "@/components/recon/VendorPickerModal";
import { WorkOrderCard } from "@/components/recon/WorkOrderCard";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/lib/AuthContext";
import {
  ApiError,
  ForbiddenError,
  UnauthenticatedError,
} from "@/lib/authFetch";
import {
  createMustDoWorkOrders,
  fetchReconDashboard,
  logVendorComm,
  VENDOR_COMMUNICATION_CHANNEL_CHOICES,
  VENDOR_COMMUNICATION_DIRECTION_CHOICES,
  VENDOR_COMMUNICATION_KIND_CHOICES,
  type ReconDashboardFinding,
  type ReconDashboardResponse,
  type ReconDecision,
  type VendorCommunication,
  type WorkOrder,
} from "@/lib/api";

const WRITE_ROLES = ["recon_manager", "sales_manager", "dealer_owner"];

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

function _humanizeLoadError(err: unknown): string {
  if (err instanceof UnauthenticatedError) return "Sign in to view this recon page.";
  if (err instanceof ForbiddenError)
    return "You do not have permission to view recon data. Requires recon_manager, sales_manager, or dealer_owner.";
  if (err instanceof ApiError) {
    if (err.status === 404) return "Vehicle not found in this dealership.";
    return `Server returned ${err.status}.`;
  }
  return "Failed to load the recon dashboard.";
}

function _humanizeMutationError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409)
      return "This action conflicts with the current state. Refresh and try again.";
    if (err.status === 422)
      return "The AI draft was rejected by the safety scrub. Review your inputs and retry.";
    if (err.status === 502)
      return "The AI service returned no draft. Retry in a moment.";
    if (err.status === 400) return "Invalid request. Please check the fields.";
    if (err.status === 404) return "Not found. Refresh the page.";
    return `Server returned ${err.status}.`;
  }
  return "Request failed.";
}

export default function VehicleReconPage() {
  const { stock } = useParams();
  const { hasRole } = useAuth();
  const [dashboard, setDashboard] = useState<ReconDashboardResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creatingMustDos, setCreatingMustDos] = useState(false);
  const [mustDosError, setMustDosError] = useState<string | null>(null);
  const [vendorPickerOpen, setVendorPickerOpen] = useState(false);
  const [logCommOpen, setLogCommOpen] = useState(false);

  const canEdit = useMemo(() => hasRole(...WRITE_ROLES), [hasRole]);

  const _refetch = useCallback(async () => {
    if (!stock) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReconDashboard(stock);
      setDashboard(data);
    } catch (err) {
      setError(_humanizeLoadError(err));
    } finally {
      setLoading(false);
    }
  }, [stock]);

  useEffect(() => {
    _refetch();
  }, [_refetch]);

  function _onDecisionRecorded(
    finding: ReconDashboardFinding,
    decision: ReconDecision,
  ) {
    if (!dashboard?.latest_condition_report) return;
    setDashboard({
      ...dashboard,
      latest_condition_report: {
        ...dashboard.latest_condition_report,
        findings: dashboard.latest_condition_report.findings.map((f) =>
          f.id === finding.id ? { ...f, decision } : f,
        ),
      },
    });
  }

  function _onWorkOrderUpdated(wo: WorkOrder) {
    if (!dashboard) return;
    setDashboard({
      ...dashboard,
      work_orders: dashboard.work_orders.some((w) => w.id === wo.id)
        ? dashboard.work_orders.map((w) => (w.id === wo.id ? wo : w))
        : [wo, ...dashboard.work_orders],
    });
  }

  function _onWorkOrderCreated(wo: WorkOrder) {
    if (!dashboard) return;
    // The dashboard's per-finding work_order_id is what JobCard uses to
    // find the WO. Update both places so the card can re-render with
    // the newly minted WO without needing a full refetch.
    const linkedFindingIds = wo.findings.map((f) => f.finding_id);
    setDashboard({
      ...dashboard,
      work_orders: dashboard.work_orders.some((w) => w.id === wo.id)
        ? dashboard.work_orders.map((w) => (w.id === wo.id ? wo : w))
        : [wo, ...dashboard.work_orders],
      latest_condition_report: dashboard.latest_condition_report
        ? {
            ...dashboard.latest_condition_report,
            findings: dashboard.latest_condition_report.findings.map((f) =>
              linkedFindingIds.includes(f.id)
                ? { ...f, work_order_id: wo.id }
                : f,
            ),
          }
        : null,
    });
  }

  function _onCommUpdated(comm: VendorCommunication) {
    if (!dashboard) return;
    setDashboard({
      ...dashboard,
      communications: dashboard.communications.some((c) => c.id === comm.id)
        ? dashboard.communications.map((c) => (c.id === comm.id ? comm : c))
        : [comm, ...dashboard.communications],
    });
  }

  async function _createAllMustDos() {
    if (!stock) return;
    setCreatingMustDos(true);
    setMustDosError(null);
    try {
      await createMustDoWorkOrders(stock);
      await _refetch();
    } catch (err) {
      setMustDosError(_humanizeMutationError(err));
    } finally {
      setCreatingMustDos(false);
    }
  }

  if (loading && !dashboard) {
    return (
      <div className="flex items-center gap-2 p-8 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading recon dashboard…
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl p-6 space-y-4">
        <div className="text-sm text-destructive">{error}</div>
        <Button
          asChild
          variant="ghost"
          size="sm"
          className="gap-1 text-xs"
        >
          <Link to="/dealer-ai-inventory">
            <ArrowLeft className="h-3 w-3" />
            Back to inventory
          </Link>
        </Button>
      </div>
    );
  }

  if (!dashboard) return null;

  const report = dashboard.latest_condition_report;
  const woById = new Map<number, WorkOrder>(
    dashboard.work_orders.map((w) => [w.id, w]),
  );
  const reportFindingIds = new Set<number>(
    report ? report.findings.map((f) => f.id) : [],
  );
  const orphanWorkOrders = dashboard.work_orders.filter((w) => {
    if (w.status === "completed" || w.status === "cancelled") return false;
    if (w.findings.length === 0) return true;
    return !w.findings.some((f) => reportFindingIds.has(f.finding_id));
  });
  const terminalWorkOrders = dashboard.work_orders.filter(
    (w) => w.status === "completed" || w.status === "cancelled",
  );
  const hasMustDoWithoutWo = !!report && report.findings.some(
    (f) => f.decision?.tier === "must_do" && !f.work_order_id,
  );

  return (
    <div className="max-w-5xl space-y-6 p-6">
      <div className="flex items-center justify-between gap-2">
        <div className="space-y-1">
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="gap-1 text-xs text-muted-foreground"
          >
            <Link to="/dealer-ai-inventory">
              <ArrowLeft className="h-3 w-3" />
              Back to inventory
            </Link>
          </Button>
          <h1 className="text-2xl font-semibold">
            Recon · Stock #{dashboard.vehicle.stock_number}
          </h1>
          <div className="text-sm text-muted-foreground">
            {dashboard.vehicle.year} {dashboard.vehicle.model}
          </div>
          {dashboard.recon_budget != null && (
            <div className="mt-1 inline-flex rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-800">
              Recon spend: ${dashboard.recon_spend} of ${dashboard.recon_budget}
            </div>
          )}
        </div>
      </div>

      {/* Inspection summary + per-finding job cards. */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-2 text-lg">
            <span className="flex items-center gap-2">
              <ClipboardList className="h-4 w-4" />
              Recon decisions
            </span>
            {canEdit && report && hasMustDoWithoutWo && (
              <Button
                size="sm"
                onClick={_createAllMustDos}
                disabled={creatingMustDos}
                className="gap-1"
              >
                {creatingMustDos ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Wand2 className="h-3 w-3" />
                )}
                Create work orders for all must-dos
              </Button>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {report == null ? (
            <div className="text-sm text-muted-foreground">
              No completed condition report yet. Complete one before
              recording recon decisions.
            </div>
          ) : (
            <>
              <div className="text-xs text-muted-foreground">
                From inspection by {report.inspector_name} at{" "}
                {_formatDateTime(report.inspected_at)}
                {" · "}
                {report.mileage_at_inspection.toLocaleString()} miles
              </div>
              {mustDosError && (
                <div className="text-xs text-destructive">{mustDosError}</div>
              )}
              {report.findings.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No findings on the latest completed report.
                </div>
              ) : (
                <div className="space-y-3">
                  {report.findings.map((f) => (
                    <JobCard
                      key={f.id}
                      stock={stock!}
                      finding={f}
                      workOrder={
                        f.work_order_id != null
                          ? (woById.get(f.work_order_id) ?? null)
                          : null
                      }
                      reportFindings={report.findings}
                      activeReportId={report.id}
                      canEdit={canEdit}
                      onDecisionRecorded={_onDecisionRecorded}
                      onWorkOrderUpdated={_onWorkOrderUpdated}
                      onWorkOrderCreated={_onWorkOrderCreated}
                      onCommDrafted={_onCommUpdated}
                      onFindingDiscovered={_refetch}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Legacy / orphan work orders — WOs with no finding on the
          latest completed report. They get a "Link finding" control
          inside the card so the operator can hook them up instead of
          cancelling and starting over. */}
      {orphanWorkOrders.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Unlinked work orders</h2>
          {orphanWorkOrders.map((wo) => (
            <WorkOrderCard
              key={wo.id}
              wo={wo}
              stock={stock!}
              canEdit={canEdit}
              reportFindings={report?.findings ?? []}
              activeReportId={report?.id ?? null}
              onWorkOrderUpdated={_onWorkOrderUpdated}
              onCommDrafted={_onCommUpdated}
              onFindingDiscovered={_refetch}
            />
          ))}
        </div>
      )}

      {/* Completed / cancelled — history at the bottom, read-only. */}
      {terminalWorkOrders.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-muted-foreground">
            Completed & cancelled
          </h2>
          {terminalWorkOrders.map((wo) => (
            <WorkOrderCard
              key={wo.id}
              wo={wo}
              stock={stock!}
              canEdit={canEdit}
              reportFindings={report?.findings ?? []}
              activeReportId={report?.id ?? null}
              onWorkOrderUpdated={_onWorkOrderUpdated}
              onCommDrafted={_onCommUpdated}
              onFindingDiscovered={_refetch}
            />
          ))}
        </div>
      )}

      {/* Communications */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Vendor communications</h2>
          {canEdit && (
            <Button
              size="sm"
              variant="outline"
              className="gap-1"
              onClick={() => setLogCommOpen((v) => !v)}
            >
              <Plus className="h-3 w-3" />
              {logCommOpen ? "Cancel" : "Log off-system comm"}
            </Button>
          )}
        </div>

        {logCommOpen && (
          <LogCommForm
            workOrders={dashboard.work_orders}
            onCreated={(comm) => {
              _onCommUpdated(comm);
              setLogCommOpen(false);
            }}
          />
        )}

        {dashboard.communications.length === 0 && !logCommOpen && (
          <div className="rounded border bg-muted/30 p-6 text-center text-sm text-muted-foreground">
            No vendor communications recorded on this vehicle yet.
          </div>
        )}

        <div className="space-y-3">
          {dashboard.communications.map((c) => (
            <VendorCommDraftPanel
              key={c.id}
              comm={c}
              canEdit={canEdit}
              onCommUpdated={_onCommUpdated}
            />
          ))}
        </div>
      </div>

      <VendorPickerModal
        open={vendorPickerOpen}
        onClose={() => setVendorPickerOpen(false)}
        onPick={(_vendor) => setVendorPickerOpen(false)}
      />
    </div>
  );
}


// ---- Inline sub-components (page-local) -----------------------------------


interface LogCommFormProps {
  workOrders: WorkOrder[];
  onCreated: (comm: VendorCommunication) => void;
}

function LogCommForm({ workOrders, onCreated }: LogCommFormProps) {
  const [workOrderId, setWorkOrderId] = useState<string>("");
  const [kind, setKind] = useState("narrative");
  const [channel, setChannel] = useState("phone");
  const [direction, setDirection] = useState("inbound");
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function _submit() {
    if (!body.trim()) {
      setError("Body is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await logVendorComm({
        work_order_id: workOrderId ? Number(workOrderId) : null,
        kind,
        channel,
        direction,
        body,
      });
      onCreated(res.communication);
      setBody("");
    } catch (err) {
      setError(_humanizeMutationError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-3 rounded border bg-muted/40 p-4 text-sm">
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="space-y-1">
          <label className="font-medium">Kind</label>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            className="w-full rounded border bg-background px-2 py-1"
          >
            {VENDOR_COMMUNICATION_KIND_CHOICES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="font-medium">Channel</label>
          <select
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            className="w-full rounded border bg-background px-2 py-1"
          >
            {VENDOR_COMMUNICATION_CHANNEL_CHOICES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="font-medium">Direction</label>
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value)}
            className="w-full rounded border bg-background px-2 py-1"
          >
            {VENDOR_COMMUNICATION_DIRECTION_CHOICES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="space-y-1 text-xs">
        <label className="font-medium">Link to work order (optional)</label>
        <select
          value={workOrderId}
          onChange={(e) => setWorkOrderId(e.target.value)}
          className="w-full rounded border bg-background px-2 py-1"
        >
          <option value="">— No work order —</option>
          {workOrders.map((wo) => (
            <option key={wo.id} value={String(wo.id)}>
              WO #{wo.id} · {wo.category} · {wo.status}
            </option>
          ))}
        </select>
      </div>
      <Textarea
        placeholder="What was said or heard. This becomes the recorded body of the communication."
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={4}
        className="text-xs"
      />
      {error && <div className="text-xs text-destructive">{error}</div>}
      <div className="flex justify-end">
        <Button size="sm" onClick={_submit} disabled={saving}>
          Log communication
        </Button>
      </div>
    </div>
  );
}
