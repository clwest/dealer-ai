// Milestone 21 · Increment 2 (SESSION_168) — initiate-repossession form.
//
// Attaches to the Repossessions card in DealerAiBhphNoteDetail.tsx.
// Posts to POST /admin/bhph-notes/<pk>/repossessions/ via bhphApi.ts
// wrapper.

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/authFetch";
import {
  initiateRepossession,
  type RepossessionProjection,
} from "@/lib/bhphApi";

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) return "Invalid repossession order. Check the fields.";
    if (err.status === 404) return "Note not found. Refresh the page.";
    return `Server returned ${err.status}.`;
  }
  return "Failed to initiate repossession.";
}

function nowLocalDatetimeInput(): string {
  const now = new Date();
  const tzOffsetMinutes = now.getTimezoneOffset();
  const local = new Date(now.getTime() - tzOffsetMinutes * 60_000);
  return local.toISOString().slice(0, 16);
}

export interface InitiateRepossessionFormProps {
  notePk: number;
  onInitiated: (repossession: RepossessionProjection) => void;
}

export function InitiateRepossessionForm({
  notePk,
  onInitiated,
}: InitiateRepossessionFormProps) {
  const [orderedAt, setOrderedAt] = useState<string>(nowLocalDatetimeInput());
  const [agentName, setAgentName] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!agentName.trim()) {
      setError("Agent name is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await initiateRepossession(notePk, {
        ordered_at: new Date(orderedAt).toISOString(),
        agent_name: agentName.trim(),
        notes: notes.trim() || undefined,
      });
      onInitiated(res.repossession);
      setAgentName("");
      setNotes("");
      setOrderedAt(nowLocalDatetimeInput());
    } catch (err) {
      setError(humanizeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-col gap-3 rounded-md border border-border p-3"
      data-testid="initiate-repo-form"
    >
      <div className="text-sm font-medium">Initiate a repossession</div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs">
          Ordered at
          <Input
            type="datetime-local"
            value={orderedAt}
            onChange={(e) => setOrderedAt(e.target.value)}
            required
            data-testid="initiate-repo-ordered-at"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Agent name
          <Input
            type="text"
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            data-testid="initiate-repo-agent"
          />
        </label>
      </div>
      <label className="flex flex-col gap-1 text-xs">
        Notes (optional)
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          data-testid="initiate-repo-notes"
        />
      </label>
      {error ? (
        <p className="text-xs text-destructive" data-testid="initiate-repo-error">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end">
        <Button type="submit" disabled={submitting} data-testid="initiate-repo-submit">
          {submitting ? "Initiating…" : "Initiate repossession"}
        </Button>
      </div>
    </form>
  );
}
