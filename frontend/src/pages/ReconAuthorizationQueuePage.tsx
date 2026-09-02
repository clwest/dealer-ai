// SESSION_228 — cross-lot Needs-authorization queue.
//
// One row per over-budget draft WorkOrder with a linked finding.
// Three exits for each row:
//
// - **Authorize with reason** — raises the car's budget by the
//   overage (VehicleReconBudgetOverride) with the operator's
//   reason, then approves the WO. Post-authorization the row
//   disappears from the queue.
// - **Cancel WO** — the ordinary cancel verb.
// - **Send to wholesale** — cancels every open WO on the car,
//   moves the vehicle to `wholesale_out`, keeps prior spend on
//   the ledger. Chris's third exit: "yes, that should be an
//   option if the cost is higher than expected".

import { useCallback, useEffect, useMemo, useState } from "react";
import { Ban, Inbox, Loader2, Truck, UnlockKeyhole } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/lib/AuthContext";
import { ApiError, ForbiddenError, UnauthenticatedError } from "@/lib/authFetch";
import {
  authorizeWithOverride,
  cancelWorkOrder,
  fetchNeedsAuthorizationQueue,
  sendVehicleToWholesale,
  type NeedsAuthorizationQueueRow,
} from "@/lib/api";

const WRITE_ROLES = ["recon_manager", "sales_manager", "dealer_owner"];
const WHOLESALE_ROLES = ["sales_manager", "dealer_owner"];

function _humanizeLoadError(err: unknown): string {
  if (err instanceof UnauthenticatedError) return "Sign in to view the recon queue.";
  if (err instanceof ForbiddenError)
    return "You do not have permission to view the recon queue.";
  if (err instanceof ApiError) return `Server returned ${err.status}.`;
  return "Failed to load the recon queue.";
}

export default function ReconAuthorizationQueuePage() {
  const { hasRole } = useAuth();
  const canEdit = useMemo(() => hasRole(...WRITE_ROLES), [hasRole]);
  const canWholesale = useMemo(
    () => hasRole(...WHOLESALE_ROLES),
    [hasRole],
  );

  const [rows, setRows] = useState<NeedsAuthorizationQueueRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const _load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchNeedsAuthorizationQueue();
      setRows(res.queue);
    } catch (err) {
      setError(_humanizeLoadError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    _load();
  }, [_load]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 p-8 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading recon queue…
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl p-6 text-sm text-destructive">{error}</div>
    );
  }

  return (
    <div className="max-w-4xl space-y-6 p-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <Inbox className="h-5 w-5" />
          Recon — needs authorization
        </h1>
        <p className="text-sm text-muted-foreground">
          Over-budget work orders across the lot. We only bother you about
          cars that go over.
        </p>
      </div>

      {rows.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            No jobs waiting on authorization. Every open WO is under its
            car's recon budget.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {rows.map((row) => (
            <QueueRow
              key={row.work_order.id}
              row={row}
              canEdit={canEdit}
              canWholesale={canWholesale}
              onChanged={_load}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function QueueRow({
  row,
  canEdit,
  canWholesale,
  onChanged,
}: {
  row: NeedsAuthorizationQueueRow;
  canEdit: boolean;
  canWholesale: boolean;
  onChanged: () => void;
}) {
  const wo = row.work_order;
  const [action, setAction] = useState<null | "authorize" | "cancel" | "wholesale">(
    null,
  );
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function _submit() {
    if (!reason.trim()) {
      setErr("A reason is required.");
      return;
    }
    setSaving(true);
    setErr(null);
    try {
      if (action === "authorize") {
        await authorizeWithOverride(wo.id, reason);
      } else if (action === "cancel") {
        await cancelWorkOrder(wo.id, { cancellation_reason: reason });
      } else if (action === "wholesale") {
        await sendVehicleToWholesale(wo.vehicle_stock_number, reason);
      }
      onChanged();
    } catch (e) {
      setErr(
        e instanceof ApiError
          ? `Server returned ${e.status}: ${e.body ?? ""}`
          : "Request failed.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-2">
        <div className="space-y-1">
          <CardTitle className="text-base">
            <Link
              to={`/dealer-ai-inventory/${encodeURIComponent(wo.vehicle_stock_number)}/recon`}
              className="hover:underline"
            >
              #{wo.vehicle_stock_number} · {wo.category}
            </Link>
          </CardTitle>
          <div className="text-xs text-muted-foreground">
            WO #{wo.id} · {wo.venue}
            {wo.vendor && <span> · {wo.vendor.name}</span>}
          </div>
          {wo.findings.length > 0 && (
            <div className="mt-1 text-sm">
              {wo.findings.map((f) => f.description).join(" · ")}
            </div>
          )}
        </div>
        <div className="rounded bg-amber-50 px-2 py-1 text-xs text-amber-900">
          Over budget · ${row.overage}
          {row.budget && (
            <div className="text-muted-foreground">
              Store cap: ${row.budget}
            </div>
          )}
          <div className="text-muted-foreground">
            Labor ${wo.estimated_cost ?? "0.00"} + Parts $
            {wo.parts_estimate} = ${wo.total_estimate}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {canEdit && action == null && (
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              className="gap-1"
              onClick={() => {
                setAction("authorize");
                setErr(null);
                setReason("");
              }}
            >
              <UnlockKeyhole className="h-3 w-3" />
              Authorize with reason
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="gap-1 text-xs text-destructive"
              onClick={() => {
                setAction("cancel");
                setErr(null);
                setReason("");
              }}
            >
              <Ban className="h-3 w-3" />
              Cancel WO
            </Button>
            {canWholesale && (
              <Button
                size="sm"
                variant="ghost"
                className="gap-1 text-xs"
                onClick={() => {
                  setAction("wholesale");
                  setErr(null);
                  setReason("");
                }}
              >
                <Truck className="h-3 w-3" />
                Send to wholesale
              </Button>
            )}
          </div>
        )}

        {action != null && (
          <div className="space-y-2 rounded border bg-muted/40 p-3">
            <div className="text-xs font-medium">
              {action === "authorize" &&
                "This raises this car's recon budget by the overage — record why."}
              {action === "cancel" && "Reason for cancelling this WO."}
              {action === "wholesale" &&
                "This cancels every open WO on the car and moves it to wholesale_out. Prior spend stays on the ledger."}
            </div>
            <Textarea
              rows={2}
              placeholder="Reason (required)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="text-xs"
            />
            {err && <div className="text-xs text-destructive">{err}</div>}
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setAction(null)}
              >
                Back
              </Button>
              <Button
                size="sm"
                onClick={_submit}
                disabled={saving || !reason.trim()}
                variant={action === "cancel" ? "destructive" : "default"}
              >
                {saving && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                Confirm
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
