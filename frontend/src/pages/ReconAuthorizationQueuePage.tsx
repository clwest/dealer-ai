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
import {
  Ban,
  ChevronDown,
  ChevronRight,
  Inbox,
  Loader2,
  Truck,
  UnlockKeyhole,
} from "lucide-react";
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
import { formatMoney } from "@/lib/utils";
import {
  authorizeWithOverride,
  cancelWorkOrder,
  fetchNeedsAuthorizationQueue,
  sendVehicleToWholesale,
  type NeedsAuthorizationQueueRow,
  type ReconList,
  type ReconListFindingItem,
  type ReconListWorkOrderItem,
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

  // SESSION_229 Part 6c — one line at the top so a manager sees
  // total over-budget dollars before triaging the list. Kept above
  // the early returns so the hook order stays stable.
  const totalOverage = useMemo(() => {
    let cents = 0n;
    for (const row of rows) {
      const [whole = "0", frac = "00"] = row.overage.split(".");
      const padded = (frac + "00").slice(0, 2);
      cents += BigInt(whole) * 100n + BigInt(padded);
    }
    const whole = cents / 100n;
    const frac = (cents % 100n).toString().padStart(2, "0");
    return `${whole.toString()}.${frac}`;
  }, [rows]);

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
        {rows.length > 0 && (
          <p className="mt-2 text-sm font-medium text-amber-900">
            You have {formatMoney(totalOverage)} of over-budget work waiting.
          </p>
        )}
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

  const vehicleLabel = [
    row.vehicle.year,
    row.vehicle.make,
    row.vehicle.model,
    row.vehicle.trim,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-2">
        <div className="space-y-1">
          <CardTitle className="text-base">
            <Link
              to={`/dealer-ai-inventory/${encodeURIComponent(wo.vehicle_stock_number)}/recon`}
              className="hover:underline"
            >
              #{wo.vehicle_stock_number} · {vehicleLabel} · {wo.category}
            </Link>
          </CardTitle>
          <div className="text-xs text-muted-foreground">
            WO #{wo.id} · {wo.venue}
            {wo.vendor && <span> · {wo.vendor.name}</span>}
          </div>
          {/* SESSION_229 Part 6b — acquisition + asking answer
              "is this car worth it?" without leaving the queue. */}
          <div className="text-xs text-muted-foreground">
            Acquired for {formatMoney(row.vehicle.acquisition_total)} · asking{" "}
            {formatMoney(row.vehicle.asking_price)}
          </div>
          {wo.findings.length > 0 && (
            <div className="mt-1 text-sm">
              {wo.findings.map((f) => f.description).join(" · ")}
            </div>
          )}
        </div>
        <div className="rounded bg-amber-50 px-2 py-1 text-xs text-amber-900">
          Over budget · {formatMoney(row.overage)}
          {row.budget && (
            <div className="text-muted-foreground">
              Store cap: {formatMoney(row.budget)}
            </div>
          )}
          {/* SESSION_229 Part 6a — the missing row. Cap + prior +
              this job now reads as a sum. */}
          <div className="text-muted-foreground">
            Already committed on this car: {formatMoney(row.prior_spend)}
          </div>
          <div className="text-muted-foreground">
            This WO: labor {formatMoney(wo.estimated_cost ?? "0.00")} + parts{" "}
            {formatMoney(wo.parts_estimate)} ={" "}
            {formatMoney(wo.total_estimate)}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <ReconListSection recon={row.recon_list} />
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

// SESSION_230 finding 12 — the whole recon list on this car,
// bucketed, collapsed by default. Chris's objection on 2026-09-02
// after the first real queue use: "theres no breakdown of
// everything that is on the list it just says that its going to be
// over budget." The one-line summary is always visible so the
// manager sees committed vs pending totals before deciding whether
// to expand and read jobs one by one.
function ReconListSection({ recon }: { recon: ReconList }) {
  const [open, setOpen] = useState(false);
  const committedCents = sumMoneyCents([
    recon.spent.total,
    recon.committed.total,
    recon.this_wo.total,
    recon.other_queued.total,
  ]);
  const pendingCents = sumMoneyCents([
    recon.decided_pending.total,
    recon.proposed.total,
    recon.undecided.total,
  ]);
  const pendingItemCount =
    recon.decided_pending.items.length +
    recon.proposed.items.length +
    recon.undecided.items.length;
  const totalItems =
    recon.spent.items.length +
    recon.committed.items.length +
    recon.this_wo.items.length +
    recon.other_queued.items.length +
    pendingItemCount +
    recon.declined.items.length;
  return (
    <div className="rounded border bg-muted/30 p-3 text-xs">
      <button
        type="button"
        className="flex w-full items-center gap-1 text-left text-xs font-medium"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        {totalItems} jobs on this car:{" "}
        <span className="font-semibold">
          {formatMoney(centsToString(committedCents))} committed
        </span>
        {pendingItemCount > 0 && (
          <>
            ,{" "}
            <span className="font-semibold text-muted-foreground">
              {formatMoney(centsToString(pendingCents))} pending across{" "}
              {pendingItemCount}{" "}
              {pendingItemCount === 1 ? "finding" : "findings"}
            </span>
          </>
        )}
      </button>
      {open && (
        <div className="mt-3 space-y-3">
          <WorkOrderBucket
            label="Spent (completed)"
            bucket={recon.spent}
          />
          <WorkOrderBucket
            label="Committed (approved / in progress)"
            bucket={recon.committed}
          />
          <WorkOrderBucket
            label="This WO"
            bucket={recon.this_wo}
          />
          <WorkOrderBucket
            label="Other queued drafts on this car"
            bucket={recon.other_queued}
          />
          <FindingBucket
            label="Must-do, no WO yet"
            note="inspector estimate, not committed"
            bucket={recon.decided_pending}
          />
          <FindingBucket
            label="Should-do (proposed)"
            note="inspector estimate, not committed"
            bucket={recon.proposed}
          />
          <FindingBucket
            label="Undecided"
            note="inspector estimate, not committed"
            bucket={recon.undecided}
          />
          <FindingBucket
            label="Declined (won't-do)"
            note="declined by manager — shown for context, not summed"
            bucket={recon.declined}
            muted
          />
        </div>
      )}
    </div>
  );
}

function WorkOrderBucket({
  label,
  bucket,
}: {
  label: string;
  bucket: { total: string; items: ReconListWorkOrderItem[] };
}) {
  if (bucket.items.length === 0) return null;
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="font-medium">{label}</span>
        <span>{formatMoney(bucket.total)}</span>
      </div>
      <ul className="mt-1 space-y-0.5 text-muted-foreground">
        {bucket.items.map((it) => (
          <li key={it.work_order_id} className="flex justify-between gap-2">
            <span>
              WO #{it.work_order_id} · {it.category} ·{" "}
              <span className="italic">{it.work_order_status}</span>
            </span>
            <span>{formatMoney(it.money)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function FindingBucket({
  label,
  note,
  bucket,
  muted,
}: {
  label: string;
  note: string;
  bucket: { total: string; items: ReconListFindingItem[] };
  muted?: boolean;
}) {
  if (bucket.items.length === 0) return null;
  return (
    <div className={muted ? "opacity-60" : undefined}>
      <div className="flex items-baseline justify-between">
        <span className="font-medium">{label}</span>
        <span>{muted ? "" : formatMoney(bucket.total)}</span>
      </div>
      <div className="text-[11px] italic text-muted-foreground">
        {note}
      </div>
      <ul className="mt-1 space-y-0.5 text-muted-foreground">
        {bucket.items.map((it) => (
          <li key={it.finding_id} className="flex justify-between gap-2">
            <span>
              {it.category} · {it.severity} · {it.description}
            </span>
            <span>
              {it.estimated_cost
                ? formatMoney(it.estimated_cost)
                : "—"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// Add money strings ("1234.56") without hitting Number's rounding.
// formatMoney does display formatting; here we just need to sum a
// handful of decimal strings.
function sumMoneyCents(values: string[]): bigint {
  let cents = 0n;
  for (const v of values) {
    const [whole = "0", frac = "00"] = v.split(".");
    const padded = (frac + "00").slice(0, 2);
    const sign = whole.startsWith("-") ? -1n : 1n;
    const absWhole = whole.replace(/^-/, "");
    cents += sign * (BigInt(absWhole) * 100n + BigInt(padded));
  }
  return cents;
}

function centsToString(cents: bigint): string {
  const sign = cents < 0n ? "-" : "";
  const abs = cents < 0n ? -cents : cents;
  const whole = abs / 100n;
  const frac = (abs % 100n).toString().padStart(2, "0");
  return `${sign}${whole.toString()}.${frac}`;
}
