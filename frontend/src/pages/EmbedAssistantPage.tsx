// SESSION_017 / SESSION_018 — public-embed surface.
//
// Lives at /embed/assistant, mounted *outside* the OS shell so a
// dealer can drop it into their public marketing site via iframe
// without inheriting any sidebar / topbar / dashboard chrome.
//
// Same chat behavior as the dealer-side Live Assistant — the
// underlying AssistantChat component is shared so the two
// surfaces never drift. Differences are pure framing.
//
// SESSION_018: brand strings (dealership name, location, footer
// disclaimer, welcome line) now flow from the existing
// onboarding profile via `useBrand()`. Hard-coded fallbacks
// use the kit's neutral default dealer when the profile is
// missing or empty.

import { useEffect, useState } from "react";
import { CircleCheck, RotateCcw } from "lucide-react";

import AssistantChat from "@/components/AssistantChat";
import { Button } from "@/components/ui/button";
import { PRODUCT } from "@/config/defaultDealer";
import { useBrand, type Brand } from "@/lib/brand";

const TRUST_POINTS = ["Real inventory", "Payment-aware", "No pressure"];

export default function EmbedAssistantPage() {
  const brand = useBrand();
  const [chatKey, setChatKey] = useState(0);
  const [hasMessages, setHasMessages] = useState(false);

  function handleReset() {
    setChatKey((k) => k + 1);
    setHasMessages(false);
  }

  return (
    <div className="flex h-dvh min-h-[480px] flex-col bg-background text-foreground">
      <BrandBar
        brand={brand}
        showReset={hasMessages}
        onReset={handleReset}
      />

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-3 px-4 py-4 sm:px-6 sm:py-5">
        <AssistantChat
          key={chatKey}
          onActivityChange={setHasMessages}
          welcomeTitle={`Hi — I'm ${brand.possessiveName} sales assistant.`}
          welcomeBody="Tell me what you're looking for and I'll show you what's on our lot. Try one of these to start, or type your own."
        />
      </main>

      <Footer brand={brand} />
    </div>
  );
}

function BrandBar({
  brand,
  showReset,
  onReset,
}: {
  brand: Brand;
  showReset: boolean;
  onReset: () => void;
}) {
  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex w-full max-w-3xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <BrandMark brand={brand} />
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-tight text-foreground">
              {brand.embedAssistantName}
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

function BrandMark({ brand }: { brand: Brand }) {
  // SESSION_021 — sources `brand.logoUrl`, which is the
  // profile-supplied hosted URL when set or the kit's static
  // fallback otherwise. If even that fails to load, fall through
  // to a small Ford-blue chip with the dealer's initials so the
  // brand bar never collapses.
  const [errored, setErrored] = useState(false);
  // Reset the error flag when the resolved URL changes so a Setup
  // edit doesn't leave the embed permanently on the initials chip.
  useEffect(() => {
    setErrored(false);
  }, [brand.logoUrl]);
  if (errored) {
    return (
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary text-xs font-bold text-primary-foreground">
        {initials(brand.dealershipName)}
      </span>
    );
  }
  return (
    <img
      src={brand.logoUrl}
      alt={brand.dealershipName}
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

function Footer({ brand }: { brand: Brand }) {
  return (
    <footer className="border-t border-border bg-card">
      <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-3 px-4 py-2 text-[11px] text-muted-foreground sm:px-6">
        <span>
          Estimates only. A {brand.dealershipName} advisor confirms real
          numbers.
        </span>
        <span className="hidden sm:inline">Powered by {PRODUCT.productSubtitle}</span>
      </div>
    </footer>
  );
}

function initials(name: string): string {
  // Two-letter chip fallback when the logo image fails. Walks the
  // first words; "Downtown Motors" → "DM".
  const parts = name
    .split(/\s+/)
    .map((s) => s.replace(/[^A-Za-z]/g, ""))
    .filter(Boolean);
  if (parts.length === 0) return "FF";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
