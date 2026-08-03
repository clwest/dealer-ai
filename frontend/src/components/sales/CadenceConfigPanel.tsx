// Milestone 21 · Increment 3 (SESSION_169) — cadence config panel.
//
// Attaches to DealerAiSalesFollowUps.tsx above the follow-up task
// queue. Bundles two operator actions:
//
// - `CreateCadenceForm`: start a new follow-up cadence for a lead.
//   Posts to POST /admin/follow-up-cadences/ via createCadence.
// - `PauseCadenceButton`: pause an existing cadence by ID. Posts to
//   POST /admin/follow-up-cadences/<pk>/pause/ via pauseCadence.
//
// The pause action takes the cadence ID as text input because M11.4
// ships no cadence-list endpoint. The follow-up-tasks list under
// the panel shows `cadence_id` on each task row so operators can
// locate the ID they want to pause.
//
// Recently-created cadences from this panel also appear in a small
// local list with an inline pause action, so a freshly-created
// cadence can be paused without copying the ID.

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/authFetch";
import {
  createCadence,
  pauseCadence,
  type CadenceProjection,
  type FollowUpTemplate,
} from "@/lib/salesApi";

const TEMPLATE_OPTIONS: { value: FollowUpTemplate; label: string }[] = [
  { value: "24hr", label: "24-hour follow-up" },
  { value: "1wk", label: "1-week follow-up" },
  { value: "30day", label: "30-day check-in" },
  { value: "90day", label: "90-day check-in" },
  { value: "6mo", label: "6-month check-in" },
  { value: "1yr", label: "1-year check-in" },
];

function humanizeCreateError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) return "Invalid cadence. Check the fields.";
    if (err.status === 404) return "Lead not found. Check the lead ID.";
    if (err.status === 409) return "Lead already has an active cadence with this template.";
    return `Server returned ${err.status}.`;
  }
  return "Failed to create cadence.";
}

function humanizePauseError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 404) return "Cadence not found.";
    if (err.status === 409) return "Cadence is already paused.";
    return `Server returned ${err.status}.`;
  }
  return "Failed to pause cadence.";
}

interface CreateCadenceFormProps {
  onCreated: (cadence: CadenceProjection) => void;
}

function CreateCadenceForm({ onCreated }: CreateCadenceFormProps) {
  const [leadIdText, setLeadIdText] = useState<string>("");
  const [template, setTemplate] = useState<FollowUpTemplate>("24hr");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const leadId = Number(leadIdText);
    if (!Number.isFinite(leadId) || leadId <= 0) {
      setError("Enter a valid lead ID.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const cadence = await createCadence({
        lead_id: leadId,
        template,
      });
      onCreated(cadence);
      setLeadIdText("");
    } catch (err) {
      setError(humanizeCreateError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-col gap-3 rounded-md border border-border p-3"
      data-testid="create-cadence-form"
    >
      <div className="text-sm font-medium">Start a follow-up cadence</div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs">
          Lead ID
          <Input
            type="number"
            min="1"
            step="1"
            value={leadIdText}
            onChange={(e) => setLeadIdText(e.target.value)}
            placeholder="e.g. 42"
            data-testid="create-cadence-lead-id"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Template
          <select
            className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
            value={template}
            onChange={(e) => setTemplate(e.target.value as FollowUpTemplate)}
            data-testid="create-cadence-template"
          >
            {TEMPLATE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error ? (
        <p
          className="text-xs text-destructive"
          data-testid="create-cadence-error"
        >
          {error}
        </p>
      ) : null}
      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={submitting}
          data-testid="create-cadence-submit"
        >
          {submitting ? "Creating…" : "Start cadence"}
        </Button>
      </div>
    </form>
  );
}

interface PauseCadenceButtonProps {
  cadenceId: number;
  disabled?: boolean;
  onPaused: (cadence: CadenceProjection) => void;
}

function PauseCadenceButton({
  cadenceId,
  disabled,
  onPaused,
}: PauseCadenceButtonProps) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onClick() {
    setSubmitting(true);
    setError(null);
    try {
      const cadence = await pauseCadence(cadenceId);
      onPaused(cadence);
    } catch (err) {
      setError(humanizePauseError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <span className="flex flex-col gap-1">
      <Button
        variant="outline"
        size="sm"
        onClick={onClick}
        disabled={disabled || submitting}
        data-testid={`pause-cadence-button-${cadenceId}`}
      >
        {submitting ? "Pausing…" : "Pause"}
      </Button>
      {error ? (
        <span
          className="text-xs text-destructive"
          data-testid={`pause-cadence-error-${cadenceId}`}
        >
          {error}
        </span>
      ) : null}
    </span>
  );
}

interface PauseCadenceByIdFormProps {
  onPaused: (cadence: CadenceProjection) => void;
}

function PauseCadenceByIdForm({ onPaused }: PauseCadenceByIdFormProps) {
  const [open, setOpen] = useState(false);
  const [cadenceIdText, setCadenceIdText] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onConfirm() {
    const cadenceId = Number(cadenceIdText);
    if (!Number.isFinite(cadenceId) || cadenceId <= 0) {
      setError("Enter a valid cadence ID.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const cadence = await pauseCadence(cadenceId);
      onPaused(cadence);
      setOpen(false);
      setCadenceIdText("");
    } catch (err) {
      setError(humanizePauseError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        data-testid="pause-cadence-by-id-button"
      >
        Pause a cadence by ID
      </Button>
      <Dialog open={open} onOpenChange={(v) => (!v ? setOpen(false) : null)}>
        <DialogContent data-testid="pause-cadence-by-id-modal">
          <DialogHeader>
            <DialogTitle>Pause a follow-up cadence</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Enter the cadence ID (visible on each row in the follow-up
            queue below as{" "}
            <code className="rounded bg-muted px-1 text-xs">#N</code>).
          </p>
          <label className="flex flex-col gap-1 text-xs">
            Cadence ID
            <Input
              type="number"
              min="1"
              step="1"
              value={cadenceIdText}
              onChange={(e) => setCadenceIdText(e.target.value)}
              data-testid="pause-cadence-by-id-input"
            />
          </label>
          {error ? (
            <p className="text-sm text-destructive">{error}</p>
          ) : null}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setOpen(false);
                setError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={onConfirm}
              disabled={submitting}
              data-testid="pause-cadence-by-id-confirm"
            >
              {submitting ? "Pausing…" : "Pause"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export interface CadenceConfigPanelProps {
  /**
   * Called after any successful create or pause so the parent page
   * can refresh downstream state (e.g. the follow-up-task queue may
   * need re-fetching when a new cadence spawns fresh tasks or a
   * pause stops future tasks from being created).
   */
  onChanged?: () => void;
}

export function CadenceConfigPanel({ onChanged }: CadenceConfigPanelProps) {
  const [recent, setRecent] = useState<CadenceProjection[]>([]);

  function mergeRecent(cadence: CadenceProjection) {
    setRecent((current) => {
      const without = current.filter((c) => c.id !== cadence.id);
      return [cadence, ...without].slice(0, 5);
    });
    onChanged?.();
  }

  return (
    <div className="flex flex-col gap-3" data-testid="cadence-config-panel">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <CreateCadenceForm onCreated={mergeRecent} />
        <div className="flex flex-col gap-3 rounded-md border border-border p-3">
          <div className="text-sm font-medium">Pause an existing cadence</div>
          <p className="text-xs text-muted-foreground">
            Pausing halts future tasks; already-pending tasks stay in the
            queue until completed or skipped.
          </p>
          <PauseCadenceByIdForm onPaused={mergeRecent} />
        </div>
      </div>

      {recent.length > 0 ? (
        <div
          className="flex flex-col gap-2 rounded-md border border-border p-3"
          data-testid="cadence-config-recent"
        >
          <div className="text-sm font-medium">Recent cadences</div>
          <ul className="flex flex-col gap-2 text-sm">
            {recent.map((cadence) => (
              <li
                key={cadence.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded border border-border/60 px-3 py-2"
                data-testid={`cadence-row-${cadence.id}`}
              >
                <span>
                  #{cadence.id} · lead #{cadence.lead_id} ·{" "}
                  {cadence.template} ·{" "}
                  <strong data-testid={`cadence-state-${cadence.id}`}>
                    {cadence.is_active ? "active" : "paused"}
                  </strong>
                </span>
                <PauseCadenceButton
                  cadenceId={cadence.id}
                  disabled={!cadence.is_active}
                  onPaused={mergeRecent}
                />
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
