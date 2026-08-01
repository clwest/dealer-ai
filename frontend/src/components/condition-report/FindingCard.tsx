// Milestone 3 · Increment 7 — one condition finding + its photo gallery.
//
// Renders the finding metadata (severity, description, estimated
// cost, notes) plus the per-finding PhotoGallery. On draft reports
// with a write-role caller, exposes edit + delete affordances.
//
// Edit is a small inline form (severity + description + estimated
// cost + notes). Category and photo re-parenting are intentionally
// out of scope for update — the service layer's whitelist would
// refuse.

import { useState } from "react";
import { PencilLine, Trash2, Loader2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/authFetch";
import {
  CONDITION_SEVERITY_CHOICES,
  deleteConditionFinding,
  updateConditionFinding,
  type ConditionFinding,
  type ConditionPhoto,
} from "@/lib/api";

import { PhotoGallery } from "./PhotoGallery";
import { PhotoUploadButton } from "./PhotoUploadButton";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  stock: string;
  finding: ConditionFinding;
  canWrite: boolean;
  onUpdated: (finding: ConditionFinding) => void;
  onDeleted: (findingId: number) => void;
  onPhotoAttached: (findingId: number, photo: ConditionPhoto) => void;
  onPhotoDeleted: (findingId: number, publicId: string) => void;
}

function _humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return "Report is complete — edits are locked.";
    if (err.status === 400) return "Invalid input.";
    if (err.status === 404) return "Finding not found. Refresh the page.";
    return `Server returned ${err.status}.`;
  }
  return "Request failed.";
}

export function FindingCard({
  stock,
  finding,
  canWrite,
  onUpdated,
  onDeleted,
  onPhotoAttached,
  onPhotoDeleted,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [severity, setSeverity] = useState(finding.severity);
  const [description, setDescription] = useState(finding.description);
  const [estimatedCost, setEstimatedCost] = useState(
    finding.estimated_cost ?? "",
  );
  const [notes, setNotes] = useState(finding.notes);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function cancelEdit() {
    setEditing(false);
    setSeverity(finding.severity);
    setDescription(finding.description);
    setEstimatedCost(finding.estimated_cost ?? "");
    setNotes(finding.notes);
    setError(null);
  }

  async function saveEdit() {
    setError(null);
    setSaving(true);
    try {
      const payload: Parameters<typeof updateConditionFinding>[2] = {
        severity,
        description,
        notes,
        estimated_cost: estimatedCost.trim() === "" ? null : estimatedCost,
      };
      const { finding: updated } = await updateConditionFinding(
        stock,
        finding.id,
        payload,
      );
      onUpdated(updated);
      setEditing(false);
    } catch (err) {
      setError(_humanizeError(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setError(null);
    setDeleting(true);
    try {
      await deleteConditionFinding(stock, finding.id);
      onDeleted(finding.id);
    } catch (err) {
      setError(_humanizeError(err));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <article className="rounded-lg border border-border bg-card p-3">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={finding.severity} />
          <span className="text-xs text-muted-foreground">
            {finding.category_display}
          </span>
        </div>
        {canWrite && !editing ? (
          <div className="flex items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => setEditing(true)}
            >
              <PencilLine className="h-3 w-3" aria-hidden="true" />
              Edit
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs text-muted-foreground hover:text-rose-700"
              disabled={deleting}
              onClick={handleDelete}
            >
              {deleting ? (
                <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
              ) : (
                <Trash2 className="h-3 w-3" aria-hidden="true" />
              )}
              Delete
            </Button>
          </div>
        ) : null}
      </header>

      {editing ? (
        <div className="mt-3 flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-xs font-medium">
            Severity
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="rounded border border-input bg-background px-2 py-1.5 text-sm"
            >
              {CONDITION_SEVERITY_CHOICES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Description
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Estimated cost{" "}
            <span className="text-muted-foreground">
              (documentation only — not part of vehicle investment)
            </span>
            <Input
              type="text"
              inputMode="decimal"
              placeholder="e.g. 165.00"
              value={estimatedCost}
              onChange={(e) => setEstimatedCost(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Notes
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
            />
          </label>
          {error ? (
            <p role="alert" className="text-xs text-rose-700">
              {error}
            </p>
          ) : null}
          <div className="flex items-center gap-2">
            <Button
              type="button"
              size="sm"
              disabled={saving}
              onClick={saveEdit}
            >
              {saving ? "Saving…" : "Save"}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={cancelEdit}
            >
              <X className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <>
          <p className="mt-2 whitespace-pre-line text-sm text-foreground">
            {finding.description}
          </p>
          {finding.notes ? (
            <p className="mt-1 whitespace-pre-line text-xs text-muted-foreground">
              {finding.notes}
            </p>
          ) : null}
          {finding.estimated_cost ? (
            <div className="mt-2 flex flex-col gap-0.5">
              <span className="text-xs font-medium text-foreground">
                Estimated cost: ${finding.estimated_cost}
              </span>
              <span className="text-[10px] italic text-muted-foreground">
                Documentation only — not yet part of vehicle investment.
              </span>
            </div>
          ) : null}
          {error ? (
            <p role="alert" className="mt-2 text-xs text-rose-700">
              {error}
            </p>
          ) : null}
        </>
      )}

      <div className="mt-3 flex flex-col gap-2 border-t border-border pt-3">
        <div className="flex items-center justify-between gap-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Photos ({finding.photos.length})
          </h4>
          {canWrite ? (
            <PhotoUploadButton
              stock={stock}
              findingId={finding.id}
              onAttached={(photo) => onPhotoAttached(finding.id, photo)}
            />
          ) : null}
        </div>
        <PhotoGallery
          stock={stock}
          photos={finding.photos}
          canDelete={canWrite}
          onDeleted={(publicId) => onPhotoDeleted(finding.id, publicId)}
        />
      </div>
    </article>
  );
}
