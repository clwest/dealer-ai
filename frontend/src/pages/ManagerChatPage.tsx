// SESSION_010 — manager-side chat tester.
//
// Stateless: each Send creates a fresh ephemeral chat session on the
// backend. Local message history is kept only in component state so the
// manager can scroll through their own test transcript. Reload = reset.
//
// Deliberately does NOT render vehicle cards — this is a voice / tone
// test surface, not a customer chat. Coupling the manager UI to
// inventory shape changes was out of scope per the SESSION_010 spec.

import { FormEvent, useEffect, useRef, useState } from "react";
import { Bot, Send, User } from "lucide-react";

import { sendManagerChat } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Turn {
  id: number;
  role: "user" | "assistant";
  content: string;
}

type SendStatus = "idle" | "sending" | "error";

export default function ManagerChatPage() {
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [status, setStatus] = useState<SendStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const nextIdRef = useRef(1);
  const transcriptRef = useRef<HTMLDivElement | null>(null);

  // Scroll to bottom when a new turn lands so the latest reply is
  // immediately visible without manual scrolling.
  useEffect(() => {
    const el = transcriptRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text || status === "sending") return;

    const userTurn: Turn = {
      id: nextIdRef.current++,
      role: "user",
      content: text,
    };
    setTurns((prev) => [...prev, userTurn]);
    setDraft("");
    setStatus("sending");
    setError(null);

    try {
      const { reply } = await sendManagerChat(text);
      setTurns((prev) => [
        ...prev,
        { id: nextIdRef.current++, role: "assistant", content: reply },
      ]);
      setStatus("idle");
    } catch (err: unknown) {
      setStatus("error");
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="space-y-4">
      {/* Header note — SESSION_010 spec calls this out explicitly. */}
      <div className="card flex items-start gap-3 px-6 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-ford-blue text-white">
          <Bot className="h-4 w-4" />
        </div>
        <div>
          <h1 className="text-base font-bold text-ford-ink">
            Manager chat tester
          </h1>
          <p className="text-sm text-slate-500">
            Test how your configured sales assistant responds to customers.
            Saved settings on the Onboarding page (voice, banned phrases,
            disclaimer) shape the replies you see here. Each message is
            stateless — reload to reset the transcript.
          </p>
          <p className="mt-1 text-xs text-amber-700">
            Not customer-facing. Use{" "}
            <span className="font-semibold">Customer demo</span> for the live
            customer view.
          </p>
        </div>
      </div>

      {/* Transcript */}
      <div
        ref={transcriptRef}
        className="card max-h-[60vh] min-h-[24rem] space-y-3 overflow-y-auto px-6 py-4"
      >
        {turns.length === 0 ? (
          <div className="text-sm text-slate-400">
            No messages yet. Send a prompt below — for example:{" "}
            <em>"I want a 4WD truck for $500/mo."</em>
          </div>
        ) : (
          turns.map((t) => <ManagerBubble key={t.id} turn={t} />)
        )}
        {status === "sending" ? (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-ford-blue" />
            Assistant is replying…
          </div>
        ) : null}
        {status === "error" ? (
          <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
            Send failed: {error ?? "unknown error"}
          </div>
        ) : null}
      </div>

      {/* Composer */}
      <form
        onSubmit={submit}
        className="card flex flex-col gap-3 px-6 py-4 sm:flex-row sm:items-end"
      >
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-xs font-semibold text-slate-600">
            Message as a customer
          </span>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Try: I'm looking for a cheap car I can pay cash for that gets good gas mileage."
            className="input min-h-[60px] resize-y"
            onKeyDown={(e) => {
              // Cmd/Ctrl+Enter to send, matching the demo page's UX.
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                submit(e as unknown as FormEvent);
              }
            }}
          />
        </label>
        <button
          type="submit"
          disabled={!draft.trim() || status === "sending"}
          className={cn(
            "inline-flex items-center gap-2 rounded-md bg-ford-blue px-4 py-2 text-sm font-semibold text-white transition",
            "hover:bg-ford-blue/90 disabled:cursor-not-allowed disabled:bg-slate-300",
          )}
        >
          <Send className="h-4 w-4" />
          {status === "sending" ? "Sending…" : "Send"}
        </button>
      </form>
    </div>
  );
}

function ManagerBubble({ turn }: { turn: Turn }) {
  const isUser = turn.role === "user";
  return (
    <div
      className={cn(
        "flex gap-3",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-ford-blue text-white" : "bg-slate-900 text-white",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={cn(
          "max-w-[78%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-soft",
          isUser
            ? "rounded-br-md bg-ford-blue text-white"
            : "rounded-bl-md bg-white text-ford-ink",
        )}
      >
        {turn.content}
      </div>
    </div>
  );
}
