// SESSION_013 — customer-facing Live Assistant page.
//
// One column. Chat is primary. When the assistant attaches
// `matched_vehicles`, they render *inline beneath the assistant
// message* as small shadcn Cards. No 4-CTA stack, no lead form, no
// popup, no fake checkout — explicitly off the spec.
//
// This is the surface that will eventually be embedded on the
// dealer's public site (SESSION_017). Treat every UX decision as
// "would a customer feel like the assistant is helping them" — not
// "does this dealer-side feature get a button". For dealer-side
// affordances (flag for handoff, lead capture modal), use the
// legacy /dealer-ai-demo page; this one stays clean.

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Bot, Loader2, RotateCcw, Send, User } from "lucide-react";

import AssistantVehicleCard from "@/components/AssistantVehicleCard";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  sendDealerMessage,
  startDealerChat,
  type ChatMessage,
  type Vehicle,
} from "@/lib/api";

type SendStatus = "idle" | "sending" | "error";

const STARTERS = [
  "I want a truck under $30k.",
  "Show me a used SUV under $35k for my family.",
  "I have $5k down and want $400/mo.",
  "What's a reliable commuter under $20k?",
];

export default function LiveAssistantPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<SendStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Pin the transcript to the latest message so customers always see
  // the assistant's most recent reply without scrolling.
  useEffect(() => {
    const el = transcriptRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, status]);

  const sending = status === "sending";

  const lastAssistantId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return messages[i].id;
    }
    return null;
  }, [messages]);

  async function ensureSession(): Promise<string> {
    if (sessionId) return sessionId;
    const res = await startDealerChat({});
    setSessionId(res.session.id);
    return res.session.id;
  }

  async function handleSend(textOverride?: string) {
    const text = (textOverride ?? input).trim();
    if (!text || sending) return;

    setError(null);
    setInput("");

    const userTurn: ChatMessage = {
      id: Date.now(),
      role: "user",
      content: text,
      matched_vehicles: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userTurn]);
    setStatus("sending");

    try {
      const sid = await ensureSession();
      const res = await sendDealerMessage(sid, text);
      setMessages((prev) => [...prev, res.assistant_message]);
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Something went wrong.");
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    void handleSend();
  }

  function handleContinue(vehicle: Vehicle) {
    // "Continue conversation" follow-up: the customer wants to keep
    // talking about this specific vehicle, not be punted to a form.
    // Fire the natural-language follow-up that the LLM can pick up,
    // mentioning the stock number so the backend's vehicle lookup
    // still resolves cleanly.
    void handleSend(
      `Tell me more about the ${vehicle.display_name} (Stock #${vehicle.stock_number}).`,
    );
  }

  function handleReset() {
    setSessionId(null);
    setMessages([]);
    setStatus("idle");
    setError(null);
    setInput("");
    inputRef.current?.focus();
  }

  const showStarters = messages.length === 0 && !sending;

  return (
    <div className="mx-auto flex h-[calc(100vh-9rem)] max-w-3xl flex-col gap-4">
      {/* Page header — keeps the customer-facing framing explicit. */}
      <header className="flex items-start justify-between gap-3">
        <div className="space-y-0.5">
          <h1 className="text-xl font-semibold tracking-tight text-foreground">
            Live Assistant
          </h1>
          <p className="text-sm text-muted-foreground">
            Tell the assistant what you're looking for. It will pull live
            inventory, sketch realistic numbers, and stay in the
            conversation with you.
          </p>
        </div>
        {messages.length > 0 ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="gap-1.5"
            onClick={handleReset}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            New chat
          </Button>
        ) : null}
      </header>

      {/* Transcript */}
      <div
        ref={transcriptRef}
        className="flex-1 overflow-y-auto rounded-xl border border-border bg-muted/30 px-4 py-5"
      >
        {showStarters ? (
          <Starters onPick={(p) => void handleSend(p)} />
        ) : (
          <div className="space-y-5">
            {messages.map((m) => (
              <Turn
                key={m.id}
                message={m}
                onContinue={handleContinue}
                isLatestAssistant={m.id === lastAssistantId}
              />
            ))}
            {sending ? (
              <div className="flex items-center gap-2 pl-11 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                The assistant is thinking…
              </div>
            ) : null}
            {error ? (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            ) : null}
          </div>
        )}
      </div>

      {/* Composer */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 rounded-xl border border-border bg-background p-2 shadow-sm"
      >
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about budget, body style, payments, trim…"
          disabled={sending}
          className="flex-1 border-0 bg-transparent px-3 py-2 text-sm text-foreground outline-none placeholder:text-muted-foreground disabled:opacity-60"
          aria-label="Message"
        />
        <Button
          type="submit"
          disabled={sending || !input.trim()}
          className="gap-1.5"
        >
          {sending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          Send
        </Button>
      </form>
      <p className="text-center text-[11px] text-muted-foreground">
        Estimates only. A Freedom Ford advisor confirms real numbers.
      </p>
    </div>
  );
}

function Starters({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground">
        <Bot className="h-5 w-5" />
      </div>
      <div className="max-w-md text-sm text-foreground">
        Hi — I'm Freedom Ford's sales assistant. Tell me what you're looking
        for and I'll show you what we have. Try one of these to start.
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {STARTERS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onPick(p)}
            className={cn(
              "rounded-full border border-border bg-background px-3 py-1.5",
              "text-xs text-muted-foreground transition",
              "hover:border-primary/40 hover:bg-background hover:text-foreground",
            )}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}

function Turn({
  message,
  onContinue,
  isLatestAssistant,
}: {
  message: ChatMessage;
  onContinue: (v: Vehicle) => void;
  isLatestAssistant: boolean;
}) {
  if (message.role === "system") {
    return (
      <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
        {message.content}
      </div>
    );
  }

  const isUser = message.role === "user";
  // Only render cards under the *latest* assistant message. Older turns
  // keep their text but drop their cards so the transcript doesn't
  // accumulate stale match sets — feels like a real conversation, not
  // a search history.
  const cards = !isUser && isLatestAssistant ? message.matched_vehicles : [];

  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-slate-900 text-white",
        )}
        aria-hidden
      >
        {isUser ? (
          <User className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </div>
      <div className={cn("flex flex-col gap-3", isUser ? "items-end" : "items-start")}>
        <div
          className={cn(
            "max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm",
            isUser
              ? "rounded-br-md bg-primary text-primary-foreground"
              : "rounded-bl-md bg-card text-card-foreground ring-1 ring-foreground/10",
          )}
        >
          {message.content}
        </div>

        {cards && cards.length > 0 ? (
          <div className="grid w-full max-w-[85%] gap-2 sm:grid-cols-2">
            {cards.map((v) => (
              <AssistantVehicleCard
                key={v.id}
                vehicle={v}
                onContinue={onContinue}
              />
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
