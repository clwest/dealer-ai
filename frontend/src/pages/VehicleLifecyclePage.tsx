// Milestone 5 · Increment 6 (SESSION_080) — operator vehicle
// lifecycle page.
//
// Consumes the 3 M5.4 admin endpoints:
//   GET  /admin/vehicles/<stock>/lifecycle/
//   POST /admin/vehicles/<stock>/lifecycle/transition/
//   POST /admin/vehicles/<stock>/lifecycle/transition/rule/
//
// State-owning container. Presentation lives in
// components/lifecycle/.
//
// Role gating (per §5.f SESSION_075 refined): write affordances
// (manual transition + rule accept) are gated to
// recon_manager / sales_manager / dealer_owner (WRITE_ROLES).
// Per-transition role authority is enforced at the M5.2 service
// layer — even a stale UI submitting a commercial target as
// recon_manager receives HTTP 403 with a distinct error message.
//
// Distinct 400 / 401 / 403 / 404 / 409 UX per M5.4 domain-error
// mapping (SESSION_078 handoff).

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { ManualTransitionForm } from "@/components/lifecycle/ManualTransitionForm";
import { StageBadge } from "@/components/lifecycle/StageBadge";
import { StageTimeline } from "@/components/lifecycle/StageTimeline";
import { SuggestedTransitionsPanel } from "@/components/lifecycle/SuggestedTransitionsPanel";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/lib/AuthContext";
import {
  ApiError,
  ForbiddenError,
  UnauthenticatedError,
} from "@/lib/authFetch";
import {
  fetchLifecycleDashboard,
  postLifecycleManualTransition,
  postLifecycleRuleTransition,
  type LifecycleDashboardResponse,
  type VehicleStageKey,
} from "@/lib/api";
import { getStageMeta, type RoleKey } from "@/lib/lifecycle";

const WRITE_ROLES = ["recon_manager", "sales_manager", "dealer_owner"];

function _humanizeLoadError(err: unknown): string {
  if (err instanceof UnauthenticatedError) {
    return "Your session expired. Please sign in again.";
  }
  if (err instanceof ForbiddenError) {
    return "You don't have permission to view this vehicle's lifecycle.";
  }
  if (err instanceof ApiError) {
    if (err.status === 404) {
      return "Vehicle not found (or belongs to another dealership).";
    }
    return err.message || `Request failed (HTTP ${err.status}).`;
  }
  return "Failed to load lifecycle dashboard.";
}

function _humanizeTransitionError(err: unknown): string {
  if (err instanceof UnauthenticatedError) {
    return "Your session expired. Please sign in again.";
  }
  if (err instanceof ApiError) {
    if (err.status === 400) {
      return err.message || "Invalid request — check the target stage.";
    }
    if (err.status === 403) {
      return (
        err.message ||
        "You don't have permission to move this vehicle to that stage."
      );
    }
    if (err.status === 404) {
      return "Vehicle not found (or belongs to another dealership).";
    }
    if (err.status === 409) {
      return err.message || "Transition refused (structural or no-op).";
    }
    return err.message || `Request failed (HTTP ${err.status}).`;
  }
  return "Failed to apply the transition.";
}

export default function VehicleLifecyclePage() {
  const { stock } = useParams();
  const { hasRole, roles } = useAuth();
  const [dashboard, setDashboard] =
    useState<LifecycleDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [transitionError, setTransitionError] = useState<string | null>(null);
  const [transitionInFlight, setTransitionInFlight] = useState(false);

  const canWrite = useMemo(() => hasRole(...WRITE_ROLES), [hasRole]);

  // Pick the "highest-authority" role the user holds at the active
  // dealership so the client-side transition-target filter
  // matches what the server will allow. Prefer dealer_owner >
  // sales_manager > recon_manager.
  const activeRole = useMemo<RoleKey | null>(() => {
    if (roles.includes("dealer_owner")) return "dealer_owner";
    if (roles.includes("sales_manager")) return "sales_manager";
    if (roles.includes("recon_manager")) return "recon_manager";
    return null;
  }, [roles]);

  const _refetch = useCallback(async () => {
    if (!stock) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchLifecycleDashboard(stock);
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

  async function handleManualTransition(
    toStage: VehicleStageKey,
    notes: string,
  ) {
    if (!stock) return;
    setTransitionError(null);
    setTransitionInFlight(true);
    try {
      await postLifecycleManualTransition(stock, {
        to_stage: toStage,
        notes,
      });
      await _refetch();
    } catch (err) {
      setTransitionError(_humanizeTransitionError(err));
    } finally {
      setTransitionInFlight(false);
    }
  }

  async function handleRuleAccept(ruleName: string) {
    if (!stock) return;
    setTransitionError(null);
    setTransitionInFlight(true);
    try {
      await postLifecycleRuleTransition(stock, { rule_name: ruleName });
      await _refetch();
    } catch (err) {
      setTransitionError(_humanizeTransitionError(err));
    } finally {
      setTransitionInFlight(false);
    }
  }

  const currentStage: VehicleStageKey | null =
    dashboard?.current_stage?.value ?? null;
  const returnHint = dashboard?.hold_reserved_return_target ?? null;

  return (
    <div className="mx-auto max-w-4xl space-y-4 px-4 py-6">
      <div className="flex items-center justify-between">
        <Link
          to="/dealer-ai-inventory"
          className="text-sm text-slate-600 hover:underline"
        >
          <ArrowLeft className="mr-1 inline h-4 w-4" />
          Back to inventory
        </Link>
        <h1 className="text-xl font-semibold">
          Vehicle lifecycle · #{stock}
        </h1>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading lifecycle…
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {dashboard && !loading && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Current stage
                <StageBadge stage={currentStage} />
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {dashboard.has_stage && dashboard.current_stage ? (
                <>
                  <p>
                    <span className="text-muted-foreground">
                      Entered at:
                    </span>{" "}
                    {new Date(
                      dashboard.current_stage.entered_at,
                    ).toLocaleString()}
                  </p>
                  <p>
                    <span className="text-muted-foreground">
                      Entered by:
                    </span>{" "}
                    {dashboard.current_stage.entered_by
                      ? dashboard.current_stage.entered_by.username
                      : "system"}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Trigger:</span>{" "}
                    {dashboard.current_stage.trigger}
                  </p>
                  {dashboard.current_stage.last_transition_note && (
                    <p>
                      <span className="text-muted-foreground">Note:</span>{" "}
                      {dashboard.current_stage.last_transition_note}
                    </p>
                  )}
                </>
              ) : (
                <p className="italic text-muted-foreground">
                  This vehicle has no lifecycle stage yet.
                </p>
              )}
              {currentStage === "hold_reserved" && returnHint && (
                <p className="rounded-sm border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
                  Suggested return target: {getStageMeta(returnHint).label}
                </p>
              )}
            </CardContent>
          </Card>

          {transitionError && (
            <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800">
              {transitionError}
            </div>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Suggested transitions</CardTitle>
            </CardHeader>
            <CardContent>
              <SuggestedTransitionsPanel
                suggestions={dashboard.suggested_transitions}
                canWrite={canWrite}
                onAccept={handleRuleAccept}
                disabled={transitionInFlight}
              />
            </CardContent>
          </Card>

          {canWrite && (
            <Card>
              <CardHeader>
                <CardTitle>Manual transition</CardTitle>
              </CardHeader>
              <CardContent>
                <ManualTransitionForm
                  currentStage={currentStage}
                  role={activeRole}
                  onSubmit={handleManualTransition}
                  disabled={transitionInFlight}
                />
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Recent events</CardTitle>
            </CardHeader>
            <CardContent>
              <StageTimeline events={dashboard.recent_events} />
            </CardContent>
          </Card>

          <div>
            <Button
              variant="outline"
              size="sm"
              onClick={_refetch}
              disabled={loading}
            >
              Refresh
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
