// Milestone 4 · Increment 7 — one WorkOrderPart row with transition
// dropdown.
//
// Renders the part metadata + status pill + a transition button
// group whose contents depend on the current status (per M4.4
// transition table).
//
// Transitions per planning §1.5 + SESSION_069:
//   needed       → ordered
//   ordered      → received, backordered, returned
//   backordered  → ordered
//   received     → installed, returned
//   installed    → (terminal)
//   returned     → (terminal)
//
// A separate delete action is shown only when the parent WO is a
// draft (per M4.4 delete_part gating). The parent page passes
// woStatus so this row knows whether to expose delete.

import { useState } from "react";
import { PackageX, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/authFetch";
import {
  deleteWorkOrderPart,
  updateWorkOrderPart,
  type WorkOrderPart,
} from "@/lib/api";

const NEXT_STATES: Record<string, Array<{ value: string; label: string }>> = {
  needed: [{ value: "ordered", label: "Mark ordered" }],
  ordered: [
    { value: "received", label: "Mark received" },
    { value: "backordered", label: "Mark backordered" },
    { value: "returned", label: "Mark returned" },
  ],
  backordered: [{ value: "ordered", label: "Re-order" }],
  received: [
    { value: "installed", label: "Mark installed" },
    { value: "returned", label: "Mark returned" },
  ],
  installed: [],
  returned: [],
};

const STATUS_CLASS: Record<string, string> = {
  needed: "border-slate-300 bg-slate-100 text-slate-600",
  ordered: "border-blue-300 bg-blue-100 text-blue-700",
  backordered: "border-orange-300 bg-orange-100 text-orange-700",
  received: "border-cyan-300 bg-cyan-100 text-cyan-700",
  installed: "border-green-300 bg-green-100 text-green-700",
  returned: "border-red-300 bg-red-100 text-red-700",
};

function _humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return "This transition is not allowed from the current state.";
    if (err.status === 400) return "Invalid transition request.";
    if (err.status === 404) return "Part not found. Refresh the page.";
    return `Server returned ${err.status}.`;
  }
  return "Part update failed.";
}

export interface PartRowProps {
  part: WorkOrderPart;
  woStatus: string;
  canEdit: boolean;
  onPartUpdated: (part: WorkOrderPart) => void;
  onPartDeleted: (partId: number) => void;
}

export function PartRow({
  part,
  woStatus,
  canEdit,
  onPartUpdated,
  onPartDeleted,
}: PartRowProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function _transition(newStatus: string) {
    setSaving(true);
    setError(null);
    try {
      const res = await updateWorkOrderPart(part.id, { new_status: newStatus });
      onPartUpdated(res.part);
    } catch (err) {
      setError(_humanizeError(err));
    } finally {
      setSaving(false);
    }
  }

  async function _delete() {
    if (!confirm(`Delete part "${part.name}"? This cannot be undone.`)) return;
    setSaving(true);
    setError(null);
    try {
      await deleteWorkOrderPart(part.id);
      onPartDeleted(part.id);
    } catch (err) {
      setError(_humanizeError(err));
    } finally {
      setSaving(false);
    }
  }

  const transitions = NEXT_STATES[part.status] ?? [];
  const canDelete = canEdit && woStatus === "draft";
  const statusClass = STATUS_CLASS[part.status] ?? "border-slate-300";

  return (
    <div className="flex items-start gap-3 rounded border bg-background p-2 text-sm">
      <div className="flex-1">
        <div className="font-medium">
          {part.name}
          {part.quantity > 1 && (
            <span className="text-muted-foreground"> × {part.quantity}</span>
          )}
        </div>
        <div className="text-xs text-muted-foreground">
          {part.part_number && <>#{part.part_number} · </>}
          {part.source_type}
          {part.source_name && ` (${part.source_name})`}
          {part.unit_cost && <> · ${part.unit_cost}/unit</>}
        </div>
      </div>
      <div className="flex flex-col items-end gap-1">
        <Badge variant="outline" className={cn("text-xs", statusClass)}>
          {part.status}
        </Badge>
        {canEdit && transitions.length > 0 && (
          <div className="flex flex-wrap justify-end gap-1">
            {transitions.map((t) => (
              <Button
                key={t.value}
                size="sm"
                variant="ghost"
                className="h-6 text-xs"
                disabled={saving}
                onClick={() => _transition(t.value)}
              >
                {t.label}
              </Button>
            ))}
          </div>
        )}
        {canDelete && (
          <Button
            size="sm"
            variant="ghost"
            className="h-6 gap-1 text-xs text-destructive"
            disabled={saving}
            onClick={_delete}
          >
            <Trash2 className="h-3 w-3" />
            Delete
          </Button>
        )}
        {!canEdit && transitions.length === 0 && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <PackageX className="h-3 w-3" />
            Terminal
          </div>
        )}
        {error && <div className="text-xs text-destructive">{error}</div>}
      </div>
    </div>
  );
}
