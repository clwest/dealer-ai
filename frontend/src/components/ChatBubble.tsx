import { Bot, User } from "lucide-react";

import ChatVehicleCard from "@/components/ChatVehicleCard";
import { cn } from "@/lib/utils";
import type { ChatMessage, Vehicle } from "@/lib/api";
import {
  parseAssistantMessage,
  type ParsedVehicle,
} from "@/lib/parseAssistantMessage";

interface Props {
  message: Pick<ChatMessage, "role" | "content" | "matched_vehicles">;
}

function findMatched(
  parsed: ParsedVehicle,
  pool: Vehicle[] | undefined,
): Vehicle | null {
  if (!pool || pool.length === 0) return null;
  const stock = parsed.stock_number.toUpperCase();
  return (
    pool.find((v) => v.stock_number?.toUpperCase() === stock) ?? null
  );
}

export default function ChatBubble({ message }: Props) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  if (isSystem) {
    return (
      <div className="my-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
        {message.content}
      </div>
    );
  }

  // For assistant messages, try the structured parse so the bubble can
  // render intro / vehicle cards / explanation / question instead of one
  // pre-wrapped wall of text. Parser returns null when there's nothing to
  // structure; in that case we render the original content unchanged.
  const parsed =
    !isUser && message.content
      ? parseAssistantMessage(message.content)
      : null;

  return (
    <div className="flex flex-col gap-1">
      {!isUser ? (
        // Subtle framing label so non-technical viewers immediately
        // understand the bubble below is what the salesperson would
        // say to a customer. Aligns with the avatar (left side).
        <div className="ml-11 text-[10.5px] font-medium uppercase tracking-wider text-slate-400">
          Recommended response to customer
        </div>
      ) : null}
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
        {isUser ? (
          <User className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </div>
      <div
        className={cn(
          "max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-soft",
          isUser
            ? "rounded-br-md bg-ford-blue text-white"
            : "rounded-bl-md bg-white text-ford-ink",
        )}
      >
        {parsed ? (
          <div className="flex flex-col gap-2.5">
            {parsed.intro ? (
              <div className="whitespace-pre-wrap">{parsed.intro}</div>
            ) : null}
            {parsed.vehicles.length > 0 ? (
              // Cards parsed from the assistant text (Stock # mentions).
              // findMatched fills in the full Vehicle data when available.
              <div className="flex flex-col gap-1.5">
                {parsed.vehicles.map((v, idx) => (
                  <ChatVehicleCard
                    key={`${v.stock_number}-${idx}`}
                    parsed={v}
                    matched={findMatched(v, message.matched_vehicles)}
                  />
                ))}
              </div>
            ) : message.matched_vehicles &&
              message.matched_vehicles.length > 0 ? (
              // Fix 2: parser found no Stock # mentions in the assistant
              // text, but the backend attached real matched_vehicles. The
              // LLM described them in prose without the Stock # marker —
              // render the cards directly from the matched_vehicles[]
              // payload so the customer's eye still anchors on real
              // inventory. We never reach this branch when the text DID
              // mention a Stock #, so there's no double-render risk.
              <div className="flex flex-col gap-1.5">
                {message.matched_vehicles.map((v) => (
                  <ChatVehicleCard
                    key={`mv-${v.stock_number}`}
                    matched={v}
                  />
                ))}
              </div>
            ) : null}
            {parsed.explanation ? (
              <div className="whitespace-pre-wrap">{parsed.explanation}</div>
            ) : null}
            {parsed.question ? (
              <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-ford-ink">
                {parsed.question}
              </div>
            ) : null}
          </div>
        ) : (
          <div className="whitespace-pre-wrap">{message.content}</div>
        )}
      </div>
    </div>
    </div>
  );
}
