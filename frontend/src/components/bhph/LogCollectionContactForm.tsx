// Milestone 21 · Increment 2 (SESSION_168) — log-collection-contact form.
//
// Attaches to the Contacts card in DealerAiBhphNoteDetail.tsx. Posts
// to POST /admin/bhph-notes/<pk>/contacts/ via bhphApi.ts wrapper.
//
// The backend applies the M12.5 FDCPA-adjacent scrub layer via
// services.llm_safety.apply_post_llm_scrubs; the form does not
// pre-scrub — trust the backend contract.

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/authFetch";
import {
  logCollectionContact,
  type CollectionContactChannel,
  type CollectionContactOutcome,
  type CollectionContactProjection,
} from "@/lib/bhphApi";

const CHANNEL_OPTIONS: { value: CollectionContactChannel; label: string }[] = [
  { value: "phone", label: "Phone" },
  { value: "sms", label: "SMS" },
  { value: "email", label: "Email" },
  { value: "letter", label: "Letter" },
  { value: "in_person", label: "In person" },
];

const OUTCOME_OPTIONS: { value: CollectionContactOutcome; label: string }[] = [
  { value: "contact_made", label: "Contact made" },
  { value: "left_message", label: "Left message" },
  { value: "no_answer", label: "No answer" },
  { value: "refused_to_speak", label: "Refused to speak" },
];

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) return "Invalid contact. Check channel and outcome.";
    if (err.status === 404) return "Note not found. Refresh the page.";
    return `Server returned ${err.status}.`;
  }
  return "Failed to log contact.";
}

function nowLocalDatetimeInput(): string {
  const now = new Date();
  const tzOffsetMinutes = now.getTimezoneOffset();
  const local = new Date(now.getTime() - tzOffsetMinutes * 60_000);
  return local.toISOString().slice(0, 16);
}

export interface LogCollectionContactFormProps {
  notePk: number;
  onLogged: (contact: CollectionContactProjection) => void;
}

export function LogCollectionContactForm({
  notePk,
  onLogged,
}: LogCollectionContactFormProps) {
  const [contactedAt, setContactedAt] = useState<string>(nowLocalDatetimeInput());
  const [channel, setChannel] = useState<CollectionContactChannel>("phone");
  const [outcome, setOutcome] = useState<CollectionContactOutcome>("contact_made");
  const [notes, setNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await logCollectionContact(notePk, {
        contacted_at: new Date(contactedAt).toISOString(),
        channel,
        outcome,
        notes: notes.trim() || undefined,
      });
      onLogged(res.collection_contact);
      setNotes("");
      setContactedAt(nowLocalDatetimeInput());
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
      data-testid="log-contact-form"
    >
      <div className="text-sm font-medium">Log a collection contact</div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <label className="flex flex-col gap-1 text-xs">
          Contacted at
          <Input
            type="datetime-local"
            value={contactedAt}
            onChange={(e) => setContactedAt(e.target.value)}
            required
            data-testid="log-contact-contacted-at"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Channel
          <select
            className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
            value={channel}
            onChange={(e) =>
              setChannel(e.target.value as CollectionContactChannel)
            }
            data-testid="log-contact-channel"
          >
            {CHANNEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Outcome
          <select
            className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
            value={outcome}
            onChange={(e) =>
              setOutcome(e.target.value as CollectionContactOutcome)
            }
            data-testid="log-contact-outcome"
          >
            {OUTCOME_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="flex flex-col gap-1 text-xs">
        Notes (optional)
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          data-testid="log-contact-notes"
        />
      </label>
      {error ? (
        <p className="text-xs text-destructive" data-testid="log-contact-error">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end">
        <Button type="submit" disabled={submitting} data-testid="log-contact-submit">
          {submitting ? "Logging…" : "Log contact"}
        </Button>
      </div>
    </form>
  );
}
