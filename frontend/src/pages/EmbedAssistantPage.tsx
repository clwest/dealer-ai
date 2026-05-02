// SESSION_017 — public-embed surface.
//
// Lives at /embed/assistant, mounted *outside* the OS shell so a
// dealer can drop it into their public marketing site via iframe
// without inheriting any sidebar / topbar / dashboard chrome.
//
// Same chat behavior as the dealer-side Live Assistant — the
// underlying AssistantChat component is shared so the two
// surfaces never drift. Differences are pure framing:
//   - No OS shell (this page is rendered as a top-level route).
//   - Mini brand bar at the top with the dealer name.
//   - Trust row sits inline with the brand bar so first-time
//     visitors see the value props above the fold.
//   - Subtle "Powered by AI Sales Assistant" footer instead of
//     the dealer-side estimate disclaimer.
//
// No backend, no chat tuning, no inventory logic touched per the
// SESSION_017 guardrails.

import { useState } from "react";
import { CircleCheck, RotateCcw } from "lucide-react";

import AssistantChat from "@/components/AssistantChat";
import { Button } from "@/components/ui/button";

const STORE_NAME = "Sam's Freedom Ford";
const TRUST_POINTS = ["Real inventory", "Payment-aware", "No pressure"];

export default function EmbedAssistantPage() {
  const [chatKey, setChatKey] = useState(0);
  const [hasMessages, setHasMessages] = useState(false);

  function handleReset() {
    setChatKey((k) => k + 1);
    setHasMessages(false);
  }

  return (
    <div className="flex h-dvh min-h-[480px] flex-col bg-background text-foreground">
      <BrandBar
        showReset={hasMessages}
        onReset={handleReset}
      />

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-3 px-4 py-4 sm:px-6 sm:py-5">
        <AssistantChat
          key={chatKey}
          onActivityChange={setHasMessages}
          welcomeTitle={`Hi — I'm ${STORE_NAME}'s sales assistant.`}
          welcomeBody="Tell me what you're looking for and I'll show you what's on our lot. Try one of these to start, or type your own."
        />
      </main>

      <Footer />
    </div>
  );
}

function BrandBar({
  showReset,
  onReset,
}: {
  showReset: boolean;
  onReset: () => void;
}) {
  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex w-full max-w-3xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <BrandMark />
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-tight text-foreground">
              {STORE_NAME} Assistant
            </div>
            <TrustRow />
          </div>
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
    </header>
  );
}

function BrandMark() {
  // Use the same dealer asset the OS shell loads so the brand reads
  // identically in both contexts. If the asset is missing, fall
  // back to a small Ford-blue chip so the bar doesn't collapse.
  const [errored, setErrored] = useState(false);
  if (errored) {
    return (
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary text-xs font-bold text-primary-foreground">
        FF
      </span>
    );
  }
  return (
    <img
      src="/branding/sams-freedom-ford-logo.jpg"
      alt={STORE_NAME}
      onError={() => setErrored(true)}
      className="h-9 w-auto select-none"
      draggable={false}
    />
  );
}

function TrustRow() {
  return (
    <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
      {TRUST_POINTS.map((point) => (
        <span key={point} className="inline-flex items-center gap-1">
          <CircleCheck className="h-3 w-3 text-primary" aria-hidden />
          <span>{point}</span>
        </span>
      ))}
    </div>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border bg-card">
      <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-3 px-4 py-2 text-[11px] text-muted-foreground sm:px-6">
        <span>Estimates only. A {STORE_NAME} advisor confirms real numbers.</span>
        <span className="hidden sm:inline">Powered by AI Sales Assistant</span>
      </div>
    </footer>
  );
}
