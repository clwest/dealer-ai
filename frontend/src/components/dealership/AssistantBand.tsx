// SESSION_022 — homepage band that embeds the live AssistantChat.
//
// This is the redesign's primary conversion path. Hudiburg leads
// with a search bar over inventory; we lead with the AI assistant.
// AssistantChat is the *same* component that powers /embed/assistant
// and the operator-side LiveAssistantPage — wrapped here in a
// homepage-friendly card framing with intent chips and a "Full
// assistant" affordance that hops to the takeover view.

import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Bot } from "lucide-react";

import AssistantChat from "@/components/AssistantChat";
import { Button } from "@/components/ui/button";
import { useBrand } from "@/lib/brand";

const HOMEPAGE_STARTERS = [
  "I need a truck under $30k",
  "Family SUV with good gas mileage",
  "I have $400/mo and want a sedan",
  "F-150 with tow package",
  "What's my 2018 Ranger worth on trade?",
];

export default function AssistantBand() {
  const brand = useBrand();
  // Bumping the key remounts AssistantChat with a fresh session.
  // Homepage rarely needs reset, but offering it is cheap.
  const [chatKey, setChatKey] = useState(0);

  const possessive = useMemo(() => brand.possessiveName, [brand.possessiveName]);

  return (
    <section
      id="assistant"
      aria-labelledby="assistant-heading"
      className="border-b border-border bg-background py-16 sm:py-20"
    >
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-12">
          <div className="lg:sticky lg:top-32 lg:self-start">
            <div className="inline-flex items-center gap-2 rounded-full border border-ford-blue/20 bg-ford-blue/5 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-ford-blue">
              <Bot className="h-3.5 w-3.5" />
              The AI difference
            </div>
            <h2
              id="assistant-heading"
              className="mt-4 text-balance text-3xl font-semibold tracking-tight text-foreground sm:text-4xl"
            >
              Tell us what you need.
              <span className="block text-ford-blue">
                We'll do the homework.
              </span>
            </h2>
            <p className="mt-4 max-w-md text-sm text-muted-foreground sm:text-base">
              {brand.dealershipName}'s AI assistant pulls from our real lot,
              runs honest payment math, and never pushes a deal that doesn't
              fit your budget. Start with one of the prompts on the right —
              or just type what's on your mind.
            </p>

            <ul className="mt-6 space-y-3 text-sm text-foreground">
              <li className="flex gap-3">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-ford-blue" />
                <span>
                  <strong className="font-semibold">Real inventory.</strong>{" "}
                  Every match is a vehicle on the lot today.
                </span>
              </li>
              <li className="flex gap-3">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-ford-blue" />
                <span>
                  <strong className="font-semibold">Honest payments.</strong>{" "}
                  Math runs server-side; the AI never invents a number.
                </span>
              </li>
              <li className="flex gap-3">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-ford-blue" />
                <span>
                  <strong className="font-semibold">Live human handoff.</strong>{" "}
                  When you're ready, a real {brand.storeLocation} salesperson
                  picks up where the AI left off.
                </span>
              </li>
            </ul>

            <Button
              asChild
              variant="outline"
              size="lg"
              className="mt-8 h-11 gap-2 border-ford-blue/30 px-4 text-sm font-semibold text-ford-blue hover:bg-ford-blue/5"
            >
              <Link to="/assistant">
                Open full assistant
                <ArrowUpRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>

          <div className="rounded-2xl border border-border bg-card p-4 shadow-soft sm:p-6">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <span className="flex h-7 w-7 items-center justify-center rounded-md bg-ford-blue text-white">
                  <Bot className="h-4 w-4" />
                </span>
                {brand.embedAssistantName}
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setChatKey((k) => k + 1)}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Reset
              </Button>
            </div>

            <AssistantChat
              key={chatKey}
              welcomeTitle={`Hi — I'm ${possessive} sales assistant.`}
              welcomeBody="Tell me what you're looking for and I'll show you what's on our lot. Try one of these to start, or type your own."
              starters={HOMEPAGE_STARTERS}
              className="h-[520px]"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
