// Milestone 4 · Increment 7 — operator recon page.
//
// Consumes the 18 M4.6 admin endpoints. State-owning container for
// the recon workflow — presentation lives in the
// components/recon/ subdirectory.
//
// Workflow this page exposes (M4.7 spec):
//
//   Vehicle recon dashboard
//     ├── Latest completed condition report + per-finding decisions
//     ├── WorkOrder cards (create → attach findings → approve →
//     │   start → complete; or cancel; or revise estimate)
//     │     ├── Part rows with transition dropdowns
//     │     └── Draft-vendor-comm affordance
//     └── Vendor communication panels (draft → approve → mark-sent;
//         or log off-system)
//
// Role gating: write affordances (approve / start / complete /
// cancel / add-part / transition-part / delete-part / draft-comm /
// approve-comm / mark-sent / log-comm / record-decision) are gated
// to recon_manager / sales_manager / dealer_owner (WRITE_ROLES).
// Server authorization remains authoritative — the M4.6 endpoints
// enforce it via IsReconManagerSalesManagerOrOwnerAtActiveDealership.
//
// Distinct 401 / 403 / 404 / 409 / 422 / 502 UX per planning §5.g +
// SESSION_071 handoff.

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, ClipboardList, Loader2, Plus } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { DecisionRow } from "@/components/recon/DecisionRow";
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
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/lib/AuthContext";
import {
  ApiError,
  ForbiddenError,
  UnauthenticatedError,
} from "@/lib/authFetch";
import {
  attachFindings,
  createWorkOrder,
  fetchReconDashboard,
  logVendorComm,
  CONDITION_CATEGORY_CHOICES,
  VENDOR_COMMUNICATION_CHANNEL_CHOICES,
  VENDOR_COMMUNICATION_DIRECTION_CHOICES,
  VENDOR_COMMUNICATION_KIND_CHOICES,
  WORK_ORDER_VENUE_CHOICES,
  type ReconDashboardFinding,
  type ReconDashboardResponse,
  type ReconDecision,
  type Vendor,
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
  const [createOpen, setCreateOpen] = useState(false);
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

  function _onCommUpdated(comm: VendorCommunication) {
    if (!dashboard) return;
    setDashboard({
      ...dashboard,
      communications: dashboard.communications.some((c) => c.id === comm.id)
        ? dashboard.communications.map((c) => (c.id === comm.id ? comm : c))
        : [comm, ...dashboard.communications],
    });
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
        </div>
      </div>

      {/* Latest condition report + decisions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <ClipboardList className="h-4 w-4" />
            Recon decisions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {dashboard.latest_condition_report == null ? (
            <div className="text-sm text-muted-foreground">
              No completed condition report yet. Complete one before
              recording recon decisions.
            </div>
          ) : (
            <>
              <div className="text-xs text-muted-foreground">
                From inspection by{" "}
                {dashboard.latest_condition_report.inspector_name} at{" "}
                {_formatDateTime(dashboard.latest_condition_report.inspected_at)}
                {" · "}
                {dashboard.latest_condition_report.mileage_at_inspection.toLocaleString()}{" "}
                miles
              </div>
              {dashboard.latest_condition_report.findings.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No findings on the latest completed report.
                </div>
              ) : (
                <div className="space-y-2">
                  {dashboard.latest_condition_report.findings.map((f) => (
                    <DecisionRow
                      key={f.id}
                      stock={stock!}
                      finding={f}
                      canEdit={canEdit}
                      onDecisionRecorded={_onDecisionRecorded}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Work orders */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Work orders</h2>
          {canEdit && (
            <Button
              size="sm"
              className="gap-1"
              onClick={() => setCreateOpen((v) => !v)}
            >
              <Plus className="h-3 w-3" />
              {createOpen ? "Cancel" : "Create work order"}
            </Button>
          )}
        </div>

        {createOpen && (
          <CreateWorkOrderForm
            stock={stock!}
            findings={dashboard.latest_condition_report?.findings ?? []}
            onOpenVendorPicker={() => setVendorPickerOpen(true)}
            onCreated={(wo) => {
              _onWorkOrderUpdated(wo);
              setCreateOpen(false);
            }}
          />
        )}

        {dashboard.work_orders.length === 0 && !createOpen && (
          <div className="rounded border bg-muted/30 p-6 text-center text-sm text-muted-foreground">
            No work orders on this vehicle yet.
          </div>
        )}

        <div className="space-y-3">
          {dashboard.work_orders.map((wo) => (
            <WorkOrderCard
              key={wo.id}
              wo={wo}
              canEdit={canEdit}
              onWorkOrderUpdated={_onWorkOrderUpdated}
              onCommDrafted={_onCommUpdated}
            />
          ))}
        </div>
      </div>

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


interface CreateWorkOrderFormProps {
  stock: string;
  findings: ReconDashboardFinding[];
  onOpenVendorPicker: () => void;
  onCreated: (wo: WorkOrder) => void;
}

function CreateWorkOrderForm({
  stock,
  findings,
  onCreated,
}: CreateWorkOrderFormProps) {
  const [category, setCategory] = useState(CONDITION_CATEGORY_CHOICES[0].value);
  const [venue, setVenue] = useState("in_house");
  const [vendorSlug, setVendorSlug] = useState("");
  const [estimatedCost, setEstimatedCost] = useState("");
  const [selectedFindingIds, setSelectedFindingIds] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);

  async function _create() {
    if (venue === "outsourced" && !vendorSlug.trim()) {
      setError("Outsourced work orders require a vendor. Pick one below.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await createWorkOrder(stock, {
        category,
        venue,
        vendor_slug: vendorSlug.trim() || null,
        estimated_cost: estimatedCost.trim() || null,
      });
      // Attach selected findings if any.
      let wo = res.work_order;
      if (selectedFindingIds.length > 0) {
        const attached = await attachFindings(wo.id, selectedFindingIds);
        wo = attached.work_order;
      }
      onCreated(wo);
    } catch (err) {
      setError(_humanizeMutationError(err));
    } finally {
      setSaving(false);
    }
  }

  function _toggleFinding(id: number) {
    setSelectedFindingIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  return (
    <div className="space-y-3 rounded border bg-muted/40 p-4 text-sm">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs font-medium">Category</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full rounded border bg-background px-2 py-1"
          >
            {CONDITION_CATEGORY_CHOICES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">Venue</label>
          <select
            value={venue}
            onChange={(e) => setVenue(e.target.value)}
            className="w-full rounded border bg-background px-2 py-1"
          >
            {WORK_ORDER_VENUE_CHOICES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      {venue === "outsourced" && (
        <div className="space-y-1">
          <label className="text-xs font-medium">Vendor</label>
          <div className="flex gap-2">
            <Input
              value={vendorSlug}
              onChange={(e) => setVendorSlug(e.target.value)}
              placeholder="vendor slug (e.g. yuma-body)"
              className="text-xs"
            />
            <Button
              size="sm"
              variant="outline"
              onClick={() => setPickerOpen(true)}
            >
              Pick…
            </Button>
          </div>
          <VendorPickerModal
            open={pickerOpen}
            onClose={() => setPickerOpen(false)}
            onPick={(v: Vendor) => {
              setVendorSlug(v.slug);
              setPickerOpen(false);
            }}
          />
        </div>
      )}
      <div className="space-y-1">
        <label className="text-xs font-medium">Estimated cost (optional)</label>
        <Input
          value={estimatedCost}
          onChange={(e) => setEstimatedCost(e.target.value)}
          placeholder="0.00"
          className="text-xs"
        />
      </div>
      {findings.length > 0 && (
        <div className="space-y-1">
          <label className="text-xs font-medium">
            Link findings (at least one required to approve)
          </label>
          <div className="space-y-1">
            {findings.map((f) => (
              <label
                key={f.id}
                className="flex cursor-pointer items-start gap-2 rounded border bg-background p-2 text-xs"
              >
                <input
                  type="checkbox"
                  checked={selectedFindingIds.includes(f.id)}
                  onChange={() => _toggleFinding(f.id)}
                  className="mt-0.5"
                />
                <div className="flex-1">
                  <div>{f.description}</div>
                  <div className="text-muted-foreground">
                    {f.category} · {f.severity}
                  </div>
                </div>
              </label>
            ))}
          </div>
        </div>
      )}
      {error && <div className="text-xs text-destructive">{error}</div>}
      <div className="flex justify-end">
        <Button size="sm" onClick={_create} disabled={saving}>
          {saving && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
          Create work order
        </Button>
      </div>
    </div>
  );
}


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
