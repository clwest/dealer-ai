// Milestone 6 · Increment 5 (SESSION_086) — operator listing editor.
// Consumes the six M6.5 listing admin endpoints.
//
// URL: /dealer-ai-inventory/:stock/listing
//
// Role gating (per §5.f SESSION_075 refined): write affordances
// (draft / regenerate / approve / publish / unpublish) are gated to
// recon_manager / sales_manager / dealer_owner.
//
// Publish semantics (planning §5.e): publishing makes the listing
// visible on /api/dealer-ai/showroom/vehicles/<stock>/. M6 v1
// does NOT push to Facebook Marketplace / AutoTrader — that's M11+.

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/AuthContext";
import {
  ApiError,
  ForbiddenError,
  UnauthenticatedError,
} from "@/lib/authFetch";
import {
  approveVehicleListing,
  draftVehicleListing,
  fetchVehicleListing,
  publishVehicleListing,
  regenerateVehicleListing,
  unpublishVehicleListing,
  type VehicleListingDTO,
  type VehicleListingStatus,
} from "@/lib/api";

const WRITE_ROLES = ["recon_manager", "sales_manager", "dealer_owner"];

const STATUS_LABEL: Record<VehicleListingStatus, string> = {
  draft: "Draft",
  approved: "Approved",
  published: "Published",
  unpublished: "Unpublished",
};

const STATUS_STYLE: Record<VehicleListingStatus, string> = {
  draft: "bg-slate-100 text-slate-800",
  approved: "bg-blue-100 text-blue-800",
  published: "bg-emerald-100 text-emerald-800",
  unpublished: "bg-amber-100 text-amber-800",
};

function humanizeError(err: unknown): string {
  if (err instanceof UnauthenticatedError) {
    return "Your session expired. Please sign in again.";
  }
  if (err instanceof ForbiddenError) {
    return "You don't have permission to edit this listing.";
  }
  if (err instanceof ApiError) {
    if (err.status === 404) {
      return err.message || "Vehicle or listing not found.";
    }
    if (err.status === 409) {
      return (
        err.message ||
        "Listing operation refused (state conflict — check current status)."
      );
    }
    if (err.status === 422) {
      return (
        err.message ||
        "AI drafting failed. Retry to generate a new draft; if repeated, escalate."
      );
    }
    return err.message || `Request failed (HTTP ${err.status}).`;
  }
  return "Listing operation failed.";
}

function StatusBadge({ status }: { status: VehicleListingStatus }) {
  return (
    <span
      className={`rounded-md px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[status]}`}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}

export default function VehicleListingEditorPage() {
  const { stock } = useParams();
  const { hasRole } = useAuth();
  const [listing, setListing] = useState<VehicleListingDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionInFlight, setActionInFlight] = useState(false);
  const [unpublishReason, setUnpublishReason] = useState("");

  const canWrite = useMemo(() => hasRole(...WRITE_ROLES), [hasRole]);

  const refetch = useCallback(async () => {
    if (!stock) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchVehicleListing(stock);
      setListing(data.listing);
    } catch (err) {
      setError(humanizeError(err));
    } finally {
      setLoading(false);
    }
  }, [stock]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  async function withAction<T>(fn: () => Promise<T>) {
    setActionError(null);
    setActionInFlight(true);
    try {
      await fn();
      await refetch();
    } catch (err) {
      setActionError(humanizeError(err));
    } finally {
      setActionInFlight(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
      <div className="flex items-center justify-between">
        <Link
          to="/dealer-ai-inventory"
          className="text-sm text-slate-600 hover:underline"
        >
          <ArrowLeft className="mr-1 inline h-4 w-4" />
          Back to inventory
        </Link>
        <h1 className="text-xl font-semibold">Listing · #{stock}</h1>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading listing…
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {actionError && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {actionError}
        </div>
      )}

      {!loading && !error && !listing && (
        <Card>
          <CardHeader>
            <CardTitle>No listing yet</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              No listing exists for this vehicle. Draft one to begin the
              approve / publish workflow.
            </p>
            {canWrite && (
              <Button
                disabled={actionInFlight}
                onClick={() => withAction(() => draftVehicleListing(stock!))}
              >
                {actionInFlight ? "Drafting…" : "Draft with AI"}
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {listing && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Status
                <StatusBadge status={listing.status} />
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              {listing.drafted_at && (
                <p>
                  Drafted{" "}
                  {new Date(listing.drafted_at).toLocaleString()} by{" "}
                  {listing.drafted_by?.username ?? "system"}
                </p>
              )}
              {listing.approved_at && (
                <p>
                  Approved{" "}
                  {new Date(listing.approved_at).toLocaleString()} by{" "}
                  {listing.approved_by?.username ?? "system"}
                </p>
              )}
              {listing.published_at && (
                <p>
                  Published{" "}
                  {new Date(listing.published_at).toLocaleString()} by{" "}
                  {listing.published_by?.username ?? "system"}
                </p>
              )}
              {listing.unpublished_at && (
                <p>
                  Unpublished{" "}
                  {new Date(listing.unpublished_at).toLocaleString()} by{" "}
                  {listing.unpublished_by?.username ?? "system"}
                  {listing.unpublished_reason && (
                    <> — {listing.unpublished_reason}</>
                  )}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Listing body</CardTitle>
            </CardHeader>
            <CardContent>
              {listing.body ? (
                <p className="whitespace-pre-wrap text-sm">{listing.body}</p>
              ) : (
                <p className="italic text-muted-foreground text-sm">
                  Body is empty.
                </p>
              )}
            </CardContent>
          </Card>

          {canWrite && (
            <Card>
              <CardHeader>
                <CardTitle>Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {listing.status === "draft" && (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      disabled={actionInFlight}
                      onClick={() =>
                        withAction(() => regenerateVehicleListing(stock!))
                      }
                    >
                      {actionInFlight ? "Regenerating…" : "Regenerate draft"}
                    </Button>
                    <Button
                      disabled={actionInFlight}
                      onClick={() =>
                        withAction(() => approveVehicleListing(stock!))
                      }
                    >
                      {actionInFlight ? "Approving…" : "Approve"}
                    </Button>
                  </div>
                )}
                {listing.status === "approved" && (
                  <Button
                    disabled={actionInFlight}
                    onClick={() =>
                      withAction(() => publishVehicleListing(stock!))
                    }
                  >
                    {actionInFlight ? "Publishing…" : "Publish to showroom"}
                  </Button>
                )}
                {listing.status === "published" && (
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={unpublishReason}
                      onChange={(e) => setUnpublishReason(e.target.value)}
                      placeholder="Reason for withdrawal (required)"
                      className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                    />
                    <Button
                      disabled={
                        actionInFlight || unpublishReason.trim() === ""
                      }
                      onClick={() =>
                        withAction(() =>
                          unpublishVehicleListing(stock!, unpublishReason),
                        )
                      }
                    >
                      {actionInFlight ? "Unpublishing…" : "Unpublish"}
                    </Button>
                  </div>
                )}
                {listing.status === "unpublished" && (
                  <p className="text-sm text-muted-foreground italic">
                    Listing is unpublished. Draft a new one via a fresh
                    vehicle intake or contact your admin to reset the
                    listing state.
                  </p>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
