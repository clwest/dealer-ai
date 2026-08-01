// Milestone 3 · Increment 7 — operator condition-report page.
//
// Consumes the M3.6A + M3.6B admin API contracts. State-owning
// container for the condition-report workflow — presentation lives
// in the components/condition-report/ subdirectory.
//
// Workflow this page exposes (M3.7 spec, in order):
//
//   Vehicle → Create report → Add findings → Request upload →
//   Upload → Attach → Review → Complete report
//
// Findings are grouped by CATEGORY (per M3.7 pushback:
// "operators generally think by inspection area first"), then by
// SEVERITY within each category (safety → advisory). Empty
// categories are skipped.
//
// Draft vs complete distinction: draft renders edit affordances +
// "Complete report" button; complete renders a visible
// CompletionBanner (locked, not merely disabled) and hides all
// edit controls. Data itself is never hidden — completed reports
// remain fully readable.
//
// Role gating: only sales_manager / dealer_owner see edit
// affordances (WRITE_ROLES — same convention as VehicleLedgerPage).
// Server authorization remains authoritative — the M3.6A + 6B
// endpoints enforce it.
//
// Security invariants:
//   - Never render storage_key, bucket names, provider names,
//     LOCAL_UPLOAD_URL_MARKER strings, or AWS credentials.
//   - Photos are identified by public_id everywhere.

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, Loader2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { AddFindingForm } from "@/components/condition-report/AddFindingForm";
import { CompletionBanner } from "@/components/condition-report/CompletionBanner";
import { CreateReportForm } from "@/components/condition-report/CreateReportForm";
import { FindingCard } from "@/components/condition-report/FindingCard";
import {
  SEVERITY_DISPLAY_ORDER,
} from "@/components/condition-report/SeverityBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/lib/AuthContext";
import {
  ApiError,
  ForbiddenError,
  UnauthenticatedError,
} from "@/lib/authFetch";
import {
  CONDITION_CATEGORY_CHOICES,
  completeConditionReport,
  fetchLatestConditionReport,
  type ConditionFinding,
  type ConditionPhoto,
  type ConditionReport,
  type ConditionReportLatestResponse,
} from "@/lib/api";

const WRITE_ROLES = ["dealer_owner", "sales_manager"];

// Category -> display label lookup for section headers.
const CATEGORY_LABEL: Record<string, string> = Object.fromEntries(
  CONDITION_CATEGORY_CHOICES.map((c) => [c.value, c.label]),
);
const CATEGORY_ORDER: string[] = CONDITION_CATEGORY_CHOICES.map(
  (c) => c.value,
);

function _formatDateTime(iso: string): string {
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
  if (err instanceof UnauthenticatedError) return "Sign in to view this report.";
  if (err instanceof ForbiddenError) return "You do not have access to this vehicle's condition report.";
  if (err instanceof ApiError) {
    if (err.status === 404) return "Vehicle not found in this dealership.";
    return `Server returned ${err.status}.`;
  }
  return "Failed to load the condition report.";
}

function _humanizeCompleteError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return "Report is already complete.";
    if (err.status === 404) return "Report not found. Refresh the page.";
    return `Server returned ${err.status}.`;
  }
  return "Complete request failed.";
}

// Group findings by category, then order by severity within each
// category. Empty categories are skipped (M3.7 spec).
function _groupFindings(
  findings: ConditionFinding[],
): Array<{ category: string; label: string; findings: ConditionFinding[] }> {
  const bucket: Record<string, ConditionFinding[]> = {};
  for (const f of findings) {
    (bucket[f.category] ??= []).push(f);
  }
  const severityRank = new Map<string, number>(
    SEVERITY_DISPLAY_ORDER.map((s, i) => [s, i]),
  );
  const sections: Array<{
    category: string;
    label: string;
    findings: ConditionFinding[];
  }> = [];
  for (const category of CATEGORY_ORDER) {
    const list = bucket[category];
    if (!list || list.length === 0) continue;
    const sorted = [...list].sort((a, b) => {
      const aR = severityRank.get(a.severity) ?? 999;
      const bR = severityRank.get(b.severity) ?? 999;
      if (aR !== bR) return aR - bR;
      // Fall back to created_at for stable ordering within severity.
      return a.created_at.localeCompare(b.created_at);
    });
    sections.push({
      category,
      label: CATEGORY_LABEL[category] ?? category,
      findings: sorted,
    });
  }
  return sections;
}

export default function VehicleConditionReportPage() {
  const { stock } = useParams<{ stock: string }>();
  const { hasRole } = useAuth();
  const canWrite = hasRole(...WRITE_ROLES);

  const [data, setData] = useState<ConditionReportLatestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [completing, setCompleting] = useState(false);
  const [completeError, setCompleteError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!stock) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchLatestConditionReport(stock);
      setData(res);
    } catch (err) {
      setError(_humanizeLoadError(err));
    } finally {
      setLoading(false);
    }
  }, [stock]);

  useEffect(() => {
    void load();
  }, [load]);

  // Local state mutators — keep the wire state in ``data`` in sync
  // with per-finding + per-photo operations so the UI reflects
  // changes without a full refetch.
  const patchReport = useCallback(
    (patch: (report: ConditionReport) => ConditionReport) => {
      setData((prev) => {
        if (!prev || !prev.report) return prev;
        return { ...prev, report: patch(prev.report) };
      });
    },
    [],
  );

  const onReportCreated = useCallback(
    (report: ConditionReport) => {
      setData((prev) => (prev ? { ...prev, report } : prev));
    },
    [],
  );

  const onFindingCreated = useCallback(
    (finding: ConditionFinding) => {
      patchReport((r) => ({ ...r, findings: [...r.findings, finding] }));
    },
    [patchReport],
  );

  const onFindingUpdated = useCallback(
    (updated: ConditionFinding) => {
      patchReport((r) => ({
        ...r,
        findings: r.findings.map((f) => (f.id === updated.id ? updated : f)),
      }));
    },
    [patchReport],
  );

  const onFindingDeleted = useCallback(
    (findingId: number) => {
      patchReport((r) => ({
        ...r,
        findings: r.findings.filter((f) => f.id !== findingId),
      }));
    },
    [patchReport],
  );

  const onPhotoAttached = useCallback(
    (findingId: number, photo: ConditionPhoto) => {
      patchReport((r) => ({
        ...r,
        findings: r.findings.map((f) =>
          f.id === findingId ? { ...f, photos: [...f.photos, photo] } : f,
        ),
      }));
    },
    [patchReport],
  );

  const onPhotoDeleted = useCallback(
    (findingId: number, publicId: string) => {
      patchReport((r) => ({
        ...r,
        findings: r.findings.map((f) =>
          f.id === findingId
            ? { ...f, photos: f.photos.filter((p) => p.public_id !== publicId) }
            : f,
        ),
      }));
    },
    [patchReport],
  );

  async function handleComplete() {
    if (!data?.report || !stock) return;
    setCompleteError(null);
    setCompleting(true);
    try {
      const { report } = await completeConditionReport(stock, data.report.id);
      onReportCreated(report);
    } catch (err) {
      setCompleteError(_humanizeCompleteError(err));
    } finally {
      setCompleting(false);
    }
  }

  const findingSections = useMemo(
    () => (data?.report ? _groupFindings(data.report.findings) : []),
    [data],
  );

  if (loading) {
    return (
      <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        Loading condition report…
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div
          role="alert"
          className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
        >
          {error}
        </div>
        <div className="mt-4">
          <BackToInventoryLink />
        </div>
      </div>
    );
  }

  if (!data) return null;
  const { vehicle, report } = data;
  const isDraft = report?.status === "draft";
  const isComplete = report?.status === "complete";

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4 p-4 sm:p-6">
      <BackToInventoryLink />

      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Condition report
          </h1>
          <p className="text-sm text-muted-foreground">
            {vehicle.display_name} · Stock #{vehicle.stock_number}
          </p>
        </div>
        {report ? (
          <Badge
            variant={isDraft ? "outline" : "default"}
            className={
              isDraft
                ? "border-slate-300 bg-white text-slate-700"
                : "border-emerald-300 bg-emerald-100 text-emerald-800"
            }
          >
            {report.status_display}
          </Badge>
        ) : null}
      </header>

      {!report && canWrite ? (
        <CreateReportForm stock={vehicle.stock_number} onCreated={onReportCreated} />
      ) : null}

      {!report && !canWrite ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No condition report yet. A sales manager or dealer owner
            can author one from this page.
          </CardContent>
        </Card>
      ) : null}

      {report ? (
        <>
          {isComplete ? (
            <CompletionBanner
              completedAt={report.completed_at ?? report.updated_at}
              authoredBy={report.authored_by}
            />
          ) : null}

          <ReportHeaderCard report={report} />

          <section className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Findings ({report.findings.length})
              </h2>
              {isDraft && canWrite ? (
                <AddFindingForm
                  stock={vehicle.stock_number}
                  reportId={report.id}
                  onCreated={onFindingCreated}
                />
              ) : null}
            </div>

            {findingSections.length === 0 ? (
              <p className="text-xs italic text-muted-foreground">
                No findings recorded.
              </p>
            ) : (
              findingSections.map((section) => (
                <section
                  key={section.category}
                  aria-label={section.label}
                  className="flex flex-col gap-2"
                >
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {section.label}
                  </h3>
                  {section.findings.map((f) => (
                    <FindingCard
                      key={f.id}
                      stock={vehicle.stock_number}
                      finding={f}
                      canWrite={isDraft && canWrite}
                      onUpdated={onFindingUpdated}
                      onDeleted={onFindingDeleted}
                      onPhotoAttached={onPhotoAttached}
                      onPhotoDeleted={onPhotoDeleted}
                    />
                  ))}
                </section>
              ))
            )}
          </section>

          {isDraft && canWrite ? (
            <div className="flex flex-col gap-2 rounded-lg border border-border bg-muted/20 p-4">
              <h3 className="text-sm font-semibold text-foreground">
                Complete report
              </h3>
              <p className="text-xs text-muted-foreground">
                Marks the report as the durable inspection record.
                This is one-way — you cannot re-open a completed
                report. To capture additional findings later,
                author a new report.
              </p>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  onClick={handleComplete}
                  disabled={completing}
                  className="gap-1.5"
                >
                  {completing ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                  )}
                  Complete report
                </Button>
              </div>
              {completeError ? (
                <p role="alert" className="text-xs text-rose-700">
                  {completeError}
                </p>
              ) : null}
            </div>
          ) : null}

          {isDraft && !canWrite ? (
            <p className="text-xs italic text-muted-foreground">
              Read-only view. Only sales managers and dealer owners
              can edit or complete condition reports.
            </p>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function BackToInventoryLink() {
  return (
    <Button
      asChild
      variant="ghost"
      size="sm"
      className="h-8 w-fit gap-1.5 text-xs text-muted-foreground hover:text-foreground"
    >
      <Link to="/dealer-ai-inventory">
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
        Back to inventory
      </Link>
    </Button>
  );
}

function ReportHeaderCard({ report }: { report: ConditionReport }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Inspection details</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Inspector
          </div>
          <div className="text-foreground">{report.inspector_name}</div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Inspection date
          </div>
          <div className="text-foreground">
            {_formatDateTime(report.inspected_at)}
          </div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Mileage
          </div>
          <div className="text-foreground">
            {report.mileage_at_inspection.toLocaleString()} mi
          </div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Entered by
          </div>
          <div className="text-foreground">
            {report.authored_by ?? "—"}
          </div>
        </div>
        {report.notes ? (
          <div className="sm:col-span-2">
            <Separator className="my-2" />
            <div className="text-xs uppercase tracking-wide text-muted-foreground">
              Notes
            </div>
            <p className="whitespace-pre-line text-sm text-foreground">
              {report.notes}
            </p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
