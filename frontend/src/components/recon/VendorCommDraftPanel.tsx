// Milestone 4 · Increment 7 — vendor communication panel.
//
// Renders a single VendorCommunication in the state that panel
// finds it. Four visual states (draft, approved, sent, logged),
// each distinct (not merely disabled) per M4.7 spec.
//
// SOURCE PROVENANCE rendering (planning §5.g): draft + approved
// rows expose a collapsible provenance panel showing the source
// bundle the AI drew from. Operators can compare the draft against
// ground truth before approving/sending. The 'scrubs_fired' list
// is also shown — if the invented_recon_fact scrub fired, the
// operator sees a subtle indicator that the safety stack modified
// the AI output.
//
// Actions per state:
// - draft     → approve  (write-role only)
// - approved  → mark-sent [with optional edited sent_content]
// - sent      → (read-only; historical)
// - logged    → (read-only; operator-recorded)

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  CircleCheck,
  Copy,
  Loader2,
  Send,
  ShieldCheck,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/authFetch";
import {
  approveVendorComm,
  markVendorCommSent,
  type VendorCommunication,
} from "@/lib/api";

const STATUS_CLASS: Record<string, string> = {
  draft: "border-slate-300 bg-slate-50",
  approved: "border-blue-300 bg-blue-50",
  sent: "border-green-300 bg-green-50",
  logged: "border-amber-300 bg-amber-50",
};

const STATUS_ICON: Record<
  string,
  React.ComponentType<{ className?: string }>
> = {
  draft: Loader2,
  approved: CircleCheck,
  sent: Send,
  logged: ShieldCheck,
};

function _humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) {
      return "Comm state changed. Refresh the page and try again.";
    }
    if (err.status === 404) return "Communication not found.";
    if (err.status === 400) return "Invalid request.";
    return `Server returned ${err.status}.`;
  }
  return "Action failed.";
}

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

export interface VendorCommDraftPanelProps {
  comm: VendorCommunication;
  canEdit: boolean;
  onCommUpdated: (comm: VendorCommunication) => void;
}

export function VendorCommDraftPanel({
  comm,
  canEdit,
  onCommUpdated,
}: VendorCommDraftPanelProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provenanceOpen, setProvenanceOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(comm.draft_content);

  const StatusIcon = STATUS_ICON[comm.status] ?? Loader2;

  async function _approve() {
    setSaving(true);
    setError(null);
    try {
      const res = await approveVendorComm(comm.id);
      onCommUpdated(res.communication);
    } catch (err) {
      setError(_humanizeError(err));
    } finally {
      setSaving(false);
    }
  }

  async function _markSent(useEdited: boolean) {
    setSaving(true);
    setError(null);
    try {
      const payload = useEdited
        ? { sent_content: editedContent }
        : {};
      const res = await markVendorCommSent(comm.id, payload);
      onCommUpdated(res.communication);
      setEditing(false);
    } catch (err) {
      setError(_humanizeError(err));
    } finally {
      setSaving(false);
    }
  }

  function _copyBody() {
    const body = comm.status === "sent" ? comm.sent_content : comm.draft_content;
    navigator.clipboard?.writeText(body).catch(() => undefined);
  }

  const bodyText = comm.status === "sent" ? comm.sent_content : comm.draft_content;
  const scrubs = comm.source_provenance?.scrubs_fired ?? [];
  const loggedOffSystem = Boolean(comm.source_provenance?.logged_off_system);
  const sourceBundle = comm.source_provenance?.source_bundle;

  return (
    <div
      className={cn(
        "space-y-3 rounded-md border p-3",
        STATUS_CLASS[comm.status] ?? "border-slate-300",
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm">
          <StatusIcon className="h-4 w-4" />
          <span className="font-medium">
            {comm.kind} · {comm.channel} · {comm.direction}
          </span>
          <Badge variant="outline" className="text-xs">
            {comm.status}
          </Badge>
          {loggedOffSystem && (
            <Badge variant="outline" className="text-xs bg-amber-100 text-amber-700">
              Off-system record
            </Badge>
          )}
        </div>
        <Button
          size="sm"
          variant="ghost"
          className="h-6 gap-1 text-xs"
          onClick={_copyBody}
        >
          <Copy className="h-3 w-3" />
          Copy body
        </Button>
      </div>

      {/* Body */}
      <div className="rounded bg-background p-2 text-sm whitespace-pre-wrap">
        {bodyText || (
          <span className="text-muted-foreground italic">No body content.</span>
        )}
      </div>

      {/* Scrubs indicator */}
      {scrubs.length > 0 && (
        <div className="flex flex-wrap items-center gap-1 text-xs">
          <ShieldCheck className="h-3 w-3 text-amber-600" />
          <span className="text-amber-700">Safety scrubs applied:</span>
          {scrubs.map((s) => (
            <Badge
              key={s}
              variant="outline"
              className="bg-amber-100 text-xs text-amber-700"
            >
              {s}
            </Badge>
          ))}
        </div>
      )}

      {/* Provenance panel (collapsible; draft + approved only) */}
      {sourceBundle && (comm.status === "draft" || comm.status === "approved") && (
        <div>
          <Button
            size="sm"
            variant="ghost"
            className="h-6 gap-1 text-xs text-muted-foreground"
            onClick={() => setProvenanceOpen((v) => !v)}
          >
            {provenanceOpen ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
            Source provenance
          </Button>
          {provenanceOpen && (
            <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-950 p-2 text-xs text-slate-200">
              {JSON.stringify(sourceBundle, null, 2)}
            </pre>
          )}
        </div>
      )}

      <Separator />

      {/* Provenance / actor timestamps */}
      <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground">
        <div>
          <div className="font-medium text-foreground">Drafted</div>
          <div>{comm.drafted_by ?? "—"}</div>
          <div>{_formatDateTime(comm.drafted_at)}</div>
        </div>
        <div>
          <div className="font-medium text-foreground">Approved</div>
          <div>{comm.approved_by ?? "—"}</div>
          <div>{_formatDateTime(comm.approved_at)}</div>
        </div>
        <div>
          <div className="font-medium text-foreground">
            {comm.status === "logged" ? "Logged" : "Sent"}
          </div>
          <div>{comm.sent_by ?? "—"}</div>
          <div>{_formatDateTime(comm.sent_at)}</div>
        </div>
      </div>

      {/* Actions */}
      {canEdit && comm.status === "draft" && (
        <div className="flex justify-end gap-2">
          <Button size="sm" onClick={_approve} disabled={saving}>
            Approve
          </Button>
        </div>
      )}
      {canEdit && comm.status === "approved" && (
        <div className="space-y-2">
          {editing ? (
            <>
              <Textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                rows={5}
                className="text-sm"
              />
              <div className="flex justify-end gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setEditing(false);
                    setEditedContent(comm.draft_content);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={() => _markSent(true)}
                  disabled={saving || !editedContent.trim()}
                >
                  Mark sent (with edits)
                </Button>
              </div>
            </>
          ) : (
            <div className="flex justify-end gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setEditing(true)}
              >
                Edit before sending
              </Button>
              <Button
                size="sm"
                onClick={() => _markSent(false)}
                disabled={saving}
              >
                Mark sent (as drafted)
              </Button>
            </div>
          )}
        </div>
      )}

      {error && <div className="text-xs text-destructive">{error}</div>}
    </div>
  );
}
