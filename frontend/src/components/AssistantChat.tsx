// SESSION_017 — shared chat surface used by both LiveAssistantPage
// (dealer-side, lives inside the OS shell) and EmbedAssistantPage
// (the public-embed widget that has no shell). Owns chat state,
// transcript scroll, composer, and starter prompts.
//
// Reset is parent-driven via React's `key` prop — increment the key
// to remount with fresh state. No imperative handle / ref API
// surface. Keeps both call sites simple.

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  ChevronLeft,
  ChevronRight,
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

const DEFAULT_STARTERS: readonly string[] = [
  "I need a truck under $30k",
  "I have $400/mo and want a sedan",
  "I need a family SUV with good gas mileage",
  "I'm not sure what I want yet",
];

export interface AssistantChatProps {
  /** Override the default 4 starter prompts shown in the empty state. */
  starters?: readonly string[];
  /** Composer placeholder. Defaults to a budget-aware nudge. */
  placeholder?: string;
  /** Container className. Caller controls the chat box's outer shape so
   *  the dealer-side and embed surfaces can frame it differently. */
  className?: string;
  /** Welcome line shown above the starter chips. */
  welcomeTitle?: string;
  welcomeBody?: string;
  /** Notifies the parent whenever the conversation transitions
   *  between empty and non-empty so the parent can show or hide its
   *  own affordances (e.g. a "New chat" button in the page header). */
  onActivityChange?: (hasMessages: boolean) => void;
}

export default function AssistantChat({
  starters = DEFAULT_STARTERS,
  placeholder = "Ask about budget, body style, payments, trim…",
  className,
  // SESSION_019 — defaults are kept brand-neutral so a leak on a
  // newly-installed kit doesn't display Freedom-Ford-specific copy.
  // Both call sites override these via props with brand-aware text.
  welcomeTitle = "Hi — I'm your dealership's sales assistant.",
  welcomeBody = "Tell me what you're looking for and I'll show you what we have. Try one of these to start, or type your own.",
  onActivityChange,
}: AssistantChatProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<SendStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [lastUserMessage, setLastUserMessage] = useState<string | null>(null);

  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Pin transcript to the latest message so the most recent reply is
  // always visible without scrolling.
  useEffect(() => {
    const el = transcriptRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, status]);

  // Tell the parent when the conversation flips between empty and
  // non-empty. Parent uses this to render its own "New chat" reset
  // button only after the user has sent at least one message.
  useEffect(() => {
    onActivityChange?.(messages.length > 0);
  }, [messages.length, onActivityChange]);

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
    void handleSend(
      `Tell me more about the ${vehicle.display_name} (Stock #${vehicle.stock_number}).`,
    );
  }

  function handleRetry() {
    if (!lastUserMessage) return;
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

  const showStarters = messages.length === 0 && !sending;

  return (
    <div className={cn("flex min-h-0 flex-1 flex-col gap-4", className)}>
      {/* Transcript */}
      <div
        ref={transcriptRef}
        className="flex-1 overflow-y-auto overflow-x-hidden rounded-xl border border-border bg-muted/30 px-4 py-5"
      >
        {showStarters ? (
          <Starters
            onPick={(p) => void handleSend(p)}
            starters={starters}
            welcomeTitle={welcomeTitle}
            welcomeBody={welcomeBody}
          />
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
          placeholder={placeholder}
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
    </div>
  );
}

// ─── Pieces ────────────────────────────────────────────────────────────────

function Starters({
  onPick,
  starters,
  welcomeTitle,
  welcomeBody,
}: {
  onPick: (prompt: string) => void;
  starters: readonly string[];
  welcomeTitle: string;
  welcomeBody: string;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-5 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm">
        <Bot className="h-5 w-5" />
      </div>
      <div className="max-w-md space-y-1">
        <div className="text-base font-medium text-foreground">
          {welcomeTitle}
        </div>
        <p className="text-sm text-muted-foreground">{welcomeBody}</p>
      </div>
      <div className="grid w-full max-w-xl gap-2 sm:grid-cols-2">
        {starters.map((p) => (
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
      <div className="font-medium">That didn't go through.</div>
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
  // Only render cards under the *latest* assistant message — older
  // turns drop their match grid so the transcript reads as a
  // conversation, not a search-result tape.
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
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={cn(
          "flex min-w-0 flex-1 flex-col gap-3",
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
          <VehicleMatchDeck vehicles={cards} onContinue={onContinue} />
        ) : null}
      </div>
    </div>
  );
}

function VehicleMatchDeck({
  vehicles,
  onContinue,
}: {
  vehicles: Vehicle[];
  onContinue: (v: Vehicle) => void;
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const count = vehicles.length;

  useEffect(() => {
    setActiveIndex(0);
  }, [vehicles]);

  function move(delta: number) {
    setActiveIndex((index) => (index + delta + count) % count);
  }

  const visibleIndexes = Array.from(
    { length: Math.min(3, count) },
    (_, offset) => (activeIndex + offset) % count,
  );

  return (
    <div className="w-full max-w-[85%]" aria-label="Matched vehicles">
      <div className="mb-2 flex w-[min(100%,360px)] items-center justify-between gap-2">
        <div className="text-xs font-medium text-muted-foreground">
          {count} vehicle{count === 1 ? "" : "s"} matched
        </div>
        {count > 1 ? (
          <div className="flex items-center gap-1">
            <Button
              type="button"
              variant="outline"
              size="icon-sm"
              aria-label="Previous vehicle"
              onClick={() => move(-1)}
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </Button>
            <span className="min-w-10 text-center text-xs text-muted-foreground">
              {activeIndex + 1}/{count}
            </span>
            <Button
              type="button"
              variant="outline"
              size="icon-sm"
              aria-label="Next vehicle"
              onClick={() => move(1)}
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        ) : null}
      </div>

      <div className="relative h-[450px] w-[min(100%,360px)] overflow-visible">
        {[...visibleIndexes].reverse().map((vehicleIndex) => {
          const stackIndex = visibleIndexes.indexOf(vehicleIndex);
          const vehicle = vehicles[vehicleIndex];
          const isActive = stackIndex === 0;
          return (
            <div
              key={vehicle.id}
              className={cn(
                "absolute left-0 top-0 w-[min(100%,320px)] transition duration-200",
                isActive ? "pointer-events-auto" : "pointer-events-none",
              )}
              style={{
                transform: `translate(${stackIndex * 18}px, ${
                  stackIndex * 18
                }px) scale(${1 - stackIndex * 0.035})`,
                zIndex: visibleIndexes.length - stackIndex,
                opacity: 1 - stackIndex * 0.1,
              }}
              aria-hidden={!isActive}
            >
              <AssistantVehicleCard vehicle={vehicle} onContinue={onContinue} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
