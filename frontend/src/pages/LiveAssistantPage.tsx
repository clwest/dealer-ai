// SESSION_013 / SESSION_016 — customer-facing Live Assistant page.
//
// One column. Chat is primary. When the assistant attaches
// `matched_vehicles`, they render *inline beneath the assistant
// message* as small shadcn Cards. No 4-CTA stack, no lead form, no
// popup, no fake checkout — patterns the public-site audit
// retired.
//
// SESSION_016 polish (visual only):
//   - Customer-facing header copy + small trust row.
//   - Buyer-friendly starter prompts.
//   - Tighter spacing between turns; smoother loading copy.
//   - Friendly error retry instead of a raw error wall.
//
// Backend, chat behavior, API contracts, and inventory matching
// are all untouched per the SESSION_016 guardrails.

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  CircleCheck,
  Loader2,
  RotateCcw,
  Send,
  User,
} from "lucide-react";

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
  "I need a truck under $30k",
  "I have $400/mo and want a sedan",
  "I need a family SUV with good gas mileage",
  "I'm not sure what I want yet",
];

const TRUST_POINTS = ["Real inventory", "Payment-aware", "No pressure"];

export default function LiveAssistantPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<SendStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  // Track the most recent user message text separately so the error
  // retry button can re-send it even after the assistant turn fails
  // and the user clears the composer.
  const [lastUserMessage, setLastUserMessage] = useState<string | null>(null);

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
    setLastUserMessage(text);

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

  function handleRetry() {
    if (!lastUserMessage) return;
    // Drop the failed user turn so retry doesn't double-render the
    // same prompt. handleSend will append a fresh optimistic bubble.
    setMessages((prev) => {
      for (let i = prev.length - 1; i >= 0; i--) {
        if (prev[i].role === "user" && prev[i].content === lastUserMessage) {
          return prev.slice(0, i);
        }
      }
      return prev;
    });
    void handleSend(lastUserMessage);
  }

  function handleReset() {
    setSessionId(null);
    setMessages([]);
    setStatus("idle");
    setError(null);
    setInput("");
    setLastUserMessage(null);
    inputRef.current?.focus();
  }

  const showStarters = messages.length === 0 && !sending;

  return (
    <div className="mx-auto flex h-[calc(100vh-9rem)] max-w-3xl flex-col gap-4">
      <PageHeader
        showReset={messages.length > 0}
        onReset={handleReset}
      />

      {/* Transcript */}
      <div
        ref={transcriptRef}
        className="flex-1 overflow-y-auto rounded-xl border border-border bg-muted/30 px-4 py-5"
      >
        {showStarters ? (
          <Starters onPick={(p) => void handleSend(p)} />
        ) : (
          <div className="space-y-6">
            {messages.map((m) => (
              <Turn
                key={m.id}
                message={m}
                onContinue={handleContinue}
                isLatestAssistant={m.id === lastAssistantId}
              />
            ))}
            {sending ? <ThinkingIndicator /> : null}
            {error ? (
              <ErrorRetry
                onRetry={lastUserMessage ? handleRetry : undefined}
                detail={error}
              />
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

// ─── Pieces ─────────────────────────────────────────────────────────────────

function PageHeader({
  showReset,
  onReset,
}: {
  showReset: boolean;
  onReset: () => void;
}) {
  return (
    <header className="space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Find Your Next Vehicle
          </h1>
          <p className="max-w-xl text-sm text-muted-foreground">
            Tell us your budget, needs, or must-haves. The assistant will
            narrow the lot for you.
          </p>
        </div>
        {showReset ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="gap-1.5"
            onClick={onReset}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            New chat
          </Button>
        ) : null}
      </div>
      <TrustRow />
    </header>
  );
}

function TrustRow() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
      {TRUST_POINTS.map((point) => (
        <span key={point} className="inline-flex items-center gap-1.5">
          <CircleCheck className="h-3.5 w-3.5 text-primary" aria-hidden />
          <span>{point}</span>
        </span>
      ))}
    </div>
  );
}

function Starters({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-5 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm">
        <Bot className="h-5 w-5" />
      </div>
      <div className="max-w-md space-y-1">
        <div className="text-base font-medium text-foreground">
          Hi — I'm Freedom Ford's sales assistant.
        </div>
        <p className="text-sm text-muted-foreground">
          Tell me what you're looking for and I'll show you what we have.
          Try one of these to start, or type your own.
        </p>
      </div>
      <div className="grid w-full max-w-xl gap-2 sm:grid-cols-2">
        {STARTERS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onPick(p)}
            className={cn(
              "rounded-lg border border-border bg-background px-3 py-2.5",
              "text-left text-sm text-foreground transition",
              "hover:border-primary/50 hover:bg-card hover:shadow-sm",
            )}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 pl-11 text-sm text-muted-foreground">
      <span className="flex gap-1" aria-hidden>
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
      </span>
      <span>Finding the best matches…</span>
    </div>
  );
}

function ErrorRetry({
  onRetry,
  detail,
}: {
  onRetry?: () => void;
  detail?: string | null;
}) {
  return (
    <div className="ml-11 max-w-[85%] rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <div className="font-medium">
        That didn't go through.
      </div>
      <p className="mt-0.5 text-xs text-amber-800">
        Connection might be slow on our end — let's try once more.
      </p>
      {onRetry ? (
        <Button
          variant="outline"
          size="sm"
          className="mt-2.5 h-8 gap-1.5 border-amber-300 bg-white text-xs text-amber-900 hover:bg-amber-100"
          onClick={onRetry}
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Try again
        </Button>
      ) : null}
      {detail ? (
        <details className="mt-2 text-[11px] text-amber-800/80">
          <summary className="cursor-pointer select-none">Details</summary>
          <pre className="mt-1 whitespace-pre-wrap font-mono text-[11px] text-amber-900/70">
            {detail}
          </pre>
        </details>
      ) : null}
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
      <div
        className={cn(
          "flex min-w-0 flex-col gap-3",
          isUser ? "items-end" : "items-start",
        )}
      >
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
          <div className="grid w-full max-w-[85%] gap-3 sm:grid-cols-2">
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
