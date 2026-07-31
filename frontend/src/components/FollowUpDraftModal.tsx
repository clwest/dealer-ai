// Manager Phase 4: AI-drafted follow-up message modal.
//
// Sibling to GenerateAdModal — same shape (loading/error/warnings, editable
// drafts, copy buttons), but for SMS / email follow-ups to a specific
// assigned lead. Drafts are copy-only by policy: nothing is sent.
//
// Channel and tone are user-selectable. Each call hits the backend's
// /advisor/<slug>/lead/<id>/follow-up/ endpoint, which runs the shared
// post-LLM safety stack with kind="follow_up" (rate / dealer-cost /
// negotiation / invented-promotion / invented-appointment scrubs).

import { useState } from "react";
import { Check, Copy, Loader2, X } from "lucide-react";

import {
  generateFollowUpDrafts,
  type AdminLead,
  type FollowUpDraft,
  type FollowUpResponse,
} from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  /** When non-null the modal is open and drafts are generated for this lead. */
  lead: AdminLead | null;
  salespersonSlug: string;
  onClose: () => void;
}

interface EditableDraft extends FollowUpDraft {
  edited_subject: string;
  edited_body: string;
}

const CHANNEL_LABEL: Record<string, string> = {
  sms: "SMS / text",
  email: "Email",
};

const CHANNEL_TONE: Record<string, string> = {
  sms: "bg-blue-100 text-blue-700",
  email: "bg-emerald-100 text-emerald-700",
};

function copyText(text: string): Promise<void> {
  if (
    typeof navigator !== "undefined" &&
    navigator.clipboard &&
    typeof navigator.clipboard.writeText === "function"
  ) {
    return navigator.clipboard.writeText(text);
  }
  return Promise.reject(new Error("clipboard API unavailable"));
}

function fullDraftText(d: EditableDraft): string {
  if (d.channel === "email") {
    const subject = d.edited_subject.trim();
    const body = d.edited_body.trim();
    return [subject ? `Subject: ${subject}` : "", "", body]
      .filter((s, i) => s !== "" || i === 1)
      .join("\n")
      .trim();
  }
  return d.edited_body.trim();
}

function DraftCard({
  draft,
  onChange,
}: {
  draft: EditableDraft;
  onChange: (next: EditableDraft) => void;
}) {
  const [copiedField, setCopiedField] = useState<string | null>(null);

  function copyAndFlash(field: string, text: string) {
    copyText(text)
      .then(() => {
        setCopiedField(field);
        setTimeout(() => setCopiedField(null), 1500);
      })
      .catch((err) => {
        console.error("Clipboard copy failed", err);
        setCopiedField(`error:${field}`);
        setTimeout(() => setCopiedField(null), 2000);
      });
  }

  const charCount =
    draft.channel === "sms"
      ? draft.edited_body.length
      : draft.edited_body.length;
  const charCap = draft.channel === "sms" ? 320 : 1200;

  return (
    <div className="flex flex-col gap-2 rounded-md border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "rounded-md px-2 py-0.5 text-[10px] font-bold uppercase",
            CHANNEL_TONE[draft.channel] ?? "bg-slate-100 text-slate-700",
          )}
        >
          {CHANNEL_LABEL[draft.channel] ?? draft.channel}
        </span>
        {draft.source === "fallback" ? (
          <span
            className="rounded-md border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-800"
            title="Composed deterministically from lead + advisor data because the LLM didn't return a usable JSON reply. Edit before sending."
          >
            Auto-fallback
          </span>
        ) : null}
        {draft.scrubs_fired.length > 0 ? (
          <span
            className="text-[10px] italic text-amber-700"
            title={draft.scrubs_fired.join(", ")}
          >
            scrubbed: {draft.scrubs_fired.length}
          </span>
        ) : null}
        <span
          className={cn(
            "text-[10px] tabular-nums",
            charCount > charCap ? "text-red-600" : "text-slate-400",
          )}
        >
          {charCount}/{charCap}
        </span>
        <button
          type="button"
          onClick={() => copyAndFlash("full", fullDraftText(draft))}
          className="ml-auto inline-flex items-center gap-1 rounded-md border border-brand-blue bg-brand-blue px-2 py-1 text-[11px] font-semibold text-white hover:bg-brand-blue/90"
        >
          {copiedField === "full" ? (
            <Check className="h-3 w-3" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
          Copy draft
        </button>
      </div>

      {draft.channel === "email" ? (
        <label className="flex flex-col gap-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Subject
          <input
            type="text"
            value={draft.edited_subject}
            onChange={(e) =>
              onChange({ ...draft, edited_subject: e.target.value })
            }
            className="rounded-md border border-slate-300 px-2 py-1 text-sm text-brand-ink"
          />
        </label>
      ) : null}

      <label className="flex flex-col gap-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        Body
        <textarea
          value={draft.edited_body}
          rows={draft.channel === "sms" ? 4 : 7}
          onChange={(e) =>
            onChange({ ...draft, edited_body: e.target.value })
          }
          className="rounded-md border border-slate-300 px-2 py-1 text-sm text-brand-ink"
        />
      </label>
    </div>
  );
}

export default function FollowUpDraftModal({
  lead,
  salespersonSlug,
  onClose,
}: Props) {
  const [channel, setChannel] = useState<"sms" | "email">("sms");
  const [tone, setTone] = useState<"warm" | "direct">("warm");
  const [response, setResponse] = useState<FollowUpResponse | null>(null);
  const [drafts, setDrafts] = useState<EditableDraft[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function generate() {
    if (lead == null) return;
    setLoading(true);
    setError(null);
    setResponse(null);
    setDrafts([]);
    generateFollowUpDrafts(salespersonSlug, lead.id, { channel, tone })
      .then((res) => {
        setResponse(res);
        setDrafts(
          res.drafts.map((d) => ({
            ...d,
            edited_subject: d.subject ?? "",
            edited_body: d.body,
          })),
        );
      })
      .catch((err) => {
        const msg =
          err instanceof Error
            ? err.message
            : "Follow-up draft generation failed.";
        console.error("generateFollowUpDrafts failed", err);
        setError(msg);
      })
      .finally(() => {
        setLoading(false);
      });
  }

  if (lead == null) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4">
      <div className="my-8 w-full max-w-3xl rounded-lg bg-white shadow-2xl">
        <div className="flex items-start justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Draft follow-up
            </div>
            <h2 className="text-lg font-bold text-brand-ink">
              {lead.name || "Lead"}
            </h2>
            <div className="mt-1 text-xs text-slate-500">
              {lead.recommended_next_action ||
                lead.conversation_summary ||
                "No prior summary on this lead."}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4 px-6 py-5">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex rounded-md border border-slate-200 bg-slate-50 p-1">
              {(["sms", "email"] as const).map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setChannel(c)}
                  className={cn(
                    "rounded px-2.5 py-1 text-xs font-semibold",
                    channel === c
                      ? "bg-white text-brand-ink shadow"
                      : "text-slate-500 hover:text-slate-700",
                  )}
                >
                  {CHANNEL_LABEL[c]}
                </button>
              ))}
            </div>
            <div className="flex rounded-md border border-slate-200 bg-slate-50 p-1">
              {(["warm", "direct"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTone(t)}
                  className={cn(
                    "rounded px-2.5 py-1 text-xs font-semibold capitalize",
                    tone === t
                      ? "bg-white text-brand-ink shadow"
                      : "text-slate-500 hover:text-slate-700",
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={generate}
              disabled={loading}
              className="ml-auto inline-flex items-center gap-1 rounded-md border border-brand-blue bg-brand-blue px-3 py-1 text-xs font-semibold text-white hover:bg-brand-blue/90 disabled:opacity-60"
            >
              {loading ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
              {response ? "Regenerate" : "Generate drafts"}
            </button>
          </div>

          {!response && !loading && !error ? (
            <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
              Click <span className="font-semibold">Generate drafts</span> to
              produce two short follow-ups for {lead.name || "this lead"}.
              Drafts are editable and copy-only.
            </div>
          ) : null}

          {loading ? (
            <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Drafting follow-ups…
            </div>
          ) : null}

          {error ? (
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <div className="font-semibold">Draft generation failed</div>
              <div className="mt-1 break-words">{error}</div>
              <div className="mt-2 text-xs text-red-600">
                Confirm the LLM provider is reachable. The modal stays open
                so you can retry.
              </div>
            </div>
          ) : null}

          {response && response.warnings.length > 0 ? (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              <div className="font-semibold">Notes from the safety scrub</div>
              <ul className="mt-1 list-inside list-disc space-y-0.5">
                {response.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {!loading && !error && response && drafts.length === 0 ? (
            <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
              No drafts survived safety review. Try a different tone or
              regenerate.
            </div>
          ) : null}

          {drafts.length > 0 ? (
            <div className="space-y-3">
              {drafts.map((d, idx) => (
                <DraftCard
                  key={idx}
                  draft={d}
                  onChange={(next) =>
                    setDrafts((curr) => {
                      const cp = [...curr];
                      cp[idx] = next;
                      return cp;
                    })
                  }
                />
              ))}
            </div>
          ) : null}

          <div className="border-t border-slate-100 pt-3 text-[11px] text-slate-500">
            Drafts only — review and send manually. The AI does not promise
            specific appointment times, rates, or discounts. Customer name
            and vehicle details come from real lead/inventory data only.
          </div>
        </div>
      </div>
    </div>
  );
}
