// Milestone 5 · Increment 6 (SESSION_080) — manual transition
// authoring form.
//
// Dropdown of allowed target stages (computed client-side from the
// current stage + operator's role via ``allowedTargetsForRole``)
// + reason textarea + submit. Submit → POST
// /lifecycle/transition/ with { to_stage, notes }.
//
// **Client-side filtering is UX only.** The M5.2 service is the
// authoritative validator — a stale UI submitting an
// unauthorized target still receives 403 (role) or 409
// (structural) from the backend.

import { useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { VehicleStageKey } from "@/lib/api";
import {
  allowedTargetsForRole,
  getStageMeta,
  type RoleKey,
} from "@/lib/lifecycle";

export interface ManualTransitionFormProps {
  currentStage: VehicleStageKey | null;
  role: RoleKey | null;
  onSubmit: (toStage: VehicleStageKey, notes: string) => Promise<void> | void;
  disabled?: boolean;
}

export function ManualTransitionForm({
  currentStage,
  role,
  onSubmit,
  disabled,
}: ManualTransitionFormProps) {
  const [toStage, setToStage] = useState<VehicleStageKey | "">("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const targets = allowedTargetsForRole(currentStage, role);

  if (targets.length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic">
        No manual transitions available from this stage for your role.
      </p>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (toStage === "") return;
    setSubmitting(true);
    try {
      await onSubmit(toStage, notes);
      setToStage("");
      setNotes("");
    } finally {
      setSubmitting(false);
    }
  }

  const busy = disabled || submitting;

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label
          htmlFor="lifecycle-to-stage"
          className="mb-1 block text-sm font-medium"
        >
          Advance to
        </label>
        <select
          id="lifecycle-to-stage"
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          value={toStage}
          onChange={(e) => setToStage(e.target.value as VehicleStageKey | "")}
          disabled={busy}
          required
        >
          <option value="">— select stage —</option>
          {targets.map((tgt) => (
            <option key={tgt} value={tgt}>
              {getStageMeta(tgt).label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label
          htmlFor="lifecycle-notes"
          className="mb-1 block text-sm font-medium"
        >
          Reason / notes
        </label>
        <Textarea
          id="lifecycle-notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="Optional — e.g. 'Reserved for cash customer.'"
          disabled={busy}
        />
      </div>
      <Button type="submit" disabled={busy || toStage === ""}>
        {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Advance stage
      </Button>
    </form>
  );
}
