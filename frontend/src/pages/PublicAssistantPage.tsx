// SESSION_022 — full-page public assistant.
//
// Customer-facing takeover route for the dealership website. Uses the
// shared AssistantChat component; query-string prompts become the
// first starter chip so deep links from vehicle cards and CTAs keep
// their intent without auto-sending duplicate messages in React
// StrictMode.

import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, Bot, Car, RotateCcw, ShieldCheck } from "lucide-react";

import AssistantChat from "@/components/AssistantChat";
import SiteFooter from "@/components/dealership/SiteFooter";
import SiteNav from "@/components/dealership/SiteNav";
import { Button } from "@/components/ui/button";
import { useBrand } from "@/lib/brand";

const DEFAULT_STARTERS = [
  "I need a 4WD truck around $500/mo with $3k down",
  "I have cash and want good gas mileage",
  "I need a family SUV with good gas mileage",
  "Which vehicle would you show first?",
];

const INTENT_PROMPTS: Record<string, string> = {
  payment: "Help me find a vehicle that fits my monthly payment",
};

export default function PublicAssistantPage() {
  const brand = useBrand();
  const [params] = useSearchParams();
  const [chatKey, setChatKey] = useState(0);
  const prompt = (params.get("prompt") || INTENT_PROMPTS[params.get("intent") || ""] || "").trim();

  const starters = useMemo(() => {
    if (!prompt) return DEFAULT_STARTERS;
    return [prompt, ...DEFAULT_STARTERS.filter((item) => item !== prompt)];
  }, [prompt]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteNav />
      <main className="border-b border-border bg-muted/30">
        <div className="mx-auto grid min-h-[calc(100vh-9rem)] w-full max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[340px_1fr] lg:px-8">
          <aside className="space-y-5 lg:py-8">
            <Button asChild variant="ghost" className="gap-2 px-0">
              <Link to="/">
                <ArrowLeft className="h-4 w-4" />
                Back to home
              </Link>
            </Button>
            <div>
              <div className="inline-flex items-center gap-2 rounded-md border border-primary/20 bg-primary/5 px-2.5 py-1 text-xs font-medium uppercase tracking-[0.14em] text-primary">
                <Bot className="h-3.5 w-3.5" />
                AI Assistant
              </div>
              <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
                Start with what matters to you.
              </h1>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                Tell {brand.dealershipName} what you need. Budget, body style,
                must-haves, trade-in, or a specific vehicle are all fair game.
              </p>
            </div>
            <div className="grid gap-3 text-sm">
              <Proof icon={Car} text="Matches come from dealership inventory." />
              <Proof icon={ShieldCheck} text="Payment details stay on the cards." />
              <Proof icon={Bot} text="A salesperson can pick up the context." />
            </div>
          </aside>

          <section className="flex min-h-[620px] flex-col rounded-lg border border-border bg-card p-3 shadow-soft sm:p-5 lg:min-h-0">
            <div className="mb-3 flex items-center justify-between gap-3 px-1">
              <div>
                <div className="text-sm font-semibold">
                  {brand.embedAssistantName}
                </div>
                <div className="text-xs text-muted-foreground">
                  Real inventory, plain-language guidance
                </div>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => setChatKey((k) => k + 1)}
              >
                <RotateCcw className="h-3.5 w-3.5" />
                New chat
              </Button>
            </div>
            <AssistantChat
              key={chatKey}
              starters={starters}
              welcomeTitle={`Hi — I'm ${brand.possessiveName} sales assistant.`}
              welcomeBody="Tell me what you are shopping for and I will narrow the lot. Pick a starter or type your own."
              className="min-h-0 flex-1"
            />
            <p className="pt-3 text-center text-[11px] text-muted-foreground">
              Estimates only. A {brand.dealershipName} advisor confirms real numbers.
            </p>
          </section>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}

function Proof({
  icon: Icon,
  text,
}: {
  icon: typeof Bot;
  text: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-background px-3 py-3">
      <Icon className="h-4 w-4 text-primary" />
      <span>{text}</span>
    </div>
  );
}
