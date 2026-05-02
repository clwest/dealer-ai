// SESSION_013 / SESSION_016 / SESSION_017 — customer-facing chat
// surface inside the dealer OS shell. The actual chat (state,
// transcript, composer, starters, retry) lives in
// `components/AssistantChat.tsx` and is shared with the public
// embed at `/embed/assistant` so behavior never drifts between
// the two surfaces. This file is the dealer-side framing only —
// page header, trust row, reset button, footer disclaimer.

import { useState } from "react";
import { CircleCheck, RotateCcw } from "lucide-react";

import AssistantChat from "@/components/AssistantChat";
import { Button } from "@/components/ui/button";
import { useBrand } from "@/lib/brand";

const TRUST_POINTS = ["Real inventory", "Payment-aware", "No pressure"];

export default function LiveAssistantPage() {
  const brand = useBrand();
  // Bump `chatKey` to remount AssistantChat with fresh state. No
  // imperative API needed; the child component owns its own state
  // and `key` is React's contract for "start over".
  const [chatKey, setChatKey] = useState(0);
  const [hasMessages, setHasMessages] = useState(false);

  function handleReset() {
    setChatKey((k) => k + 1);
    setHasMessages(false);
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-9rem)] max-w-3xl flex-col gap-4">
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
          {hasMessages ? (
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
        </div>
        <TrustRow />
      </header>

      <AssistantChat
        key={chatKey}
        onActivityChange={setHasMessages}
        welcomeTitle={`Hi — I'm ${brand.possessiveName} sales assistant.`}
      />

      <p className="text-center text-[11px] text-muted-foreground">
        Estimates only. A {brand.dealershipName} advisor confirms real numbers.
      </p>
    </div>
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
