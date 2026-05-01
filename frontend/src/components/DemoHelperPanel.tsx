import { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Loader2,
  PlayCircle,
  RotateCcw,
  Sparkles,
  Wand2,
} from "lucide-react";

import { loadDemoScenarios, resetDemo } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  onPromptClick?: (prompt: string) => void;
  onAfterAction?: () => void;
}

export const DEMO_PROMPTS: { label: string; prompt: string }[] = [
  {
    label: "Budget mismatch — $500/mo on a $78k truck",
    prompt:
      "I want a new F-150 Lariat but I'm targeting $500/month with no money down. What can you do?",
  },
  {
    label: "Used SUV under $30k",
    prompt: "I need a used SUV under $30k for my family.",
  },
  {
    label: "Trade-in + fair credit",
    prompt:
      "I have a 2018 Escape to trade in for a used truck. My credit is fair. What are my options?",
  },
  {
    label: "Family + camper towing",
    prompt:
      "We have a small camper trailer (~3,500 lb) and three kids — need an SUV with a third row that can tow it.",
  },
  {
    label: "Service / oil change",
    prompt: "Do you have affordable service or oil change options for a 2019 F-150?",
  },
];

export default function DemoHelperPanel({ onPromptClick, onAfterAction }: Props) {
  const [open, setOpen] = useState(true);
  const [busy, setBusy] = useState<"scenarios" | "reset" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleLoadScenarios() {
    if (
      !window.confirm(
        "Load 5 scripted demo scenarios? Existing chat sessions and leads will be reset first so the dashboard reflects only the scripted state.",
      )
    ) {
      return;
    }
    setBusy("scenarios");
    setMessage(null);
    setError(null);
    try {
      const res = await loadDemoScenarios({ reset: true });
      setMessage(
        `Loaded ${res.chat_sessions} demo sessions and ${res.leads} leads. Open the Manager dashboard to see them.`,
      );
      onAfterAction?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load scenarios.");
    } finally {
      setBusy(null);
    }
  }

  async function handleReset() {
    if (
      !window.confirm(
        "Reset the demo? This clears all chat sessions and leads and reloads the bundled demo vehicles. Imported (CSV) vehicles are preserved.",
      )
    ) {
      return;
    }
    setBusy("reset");
    setMessage(null);
    setError(null);
    try {
      const res = await resetDemo();
      setMessage(
        `Reset done — cleared ${res.cleared.leads} leads and ${res.cleared.chat_sessions} sessions; ${res.demo_vehicles} demo vehicles loaded.`,
      );
      onAfterAction?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="card overflow-hidden">
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center gap-2">
          <Wand2 className="h-4 w-4 text-ford-accent" />
          <span className="text-sm font-bold text-ford-ink">Demo controls</span>
        </div>
        {open ? (
          <ChevronUp className="h-4 w-4 text-slate-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-slate-400" />
        )}
      </button>

      {open && (
        <div className="space-y-3 border-t border-slate-100 px-4 py-3">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <button
              type="button"
              onClick={handleLoadScenarios}
              className="btn-primary justify-center"
              disabled={busy !== null}
            >
              {busy === "scenarios" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <PlayCircle className="h-4 w-4" />
              )}
              Load demo scenarios
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="btn-ghost justify-center text-amber-700"
              disabled={busy !== null}
            >
              {busy === "reset" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RotateCcw className="h-4 w-4" />
              )}
              Reset demo
            </button>
          </div>

          {(message || error) && (
            <div
              className={cn(
                "rounded-md px-3 py-2 text-xs",
                error
                  ? "border border-red-200 bg-red-50 text-red-700"
                  : "border border-emerald-200 bg-emerald-50 text-emerald-800",
              )}
            >
              {error || message}
            </div>
          )}

          <div>
            <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Sparkles className="h-3.5 w-3.5" />
              Suggested customer prompts
            </div>
            <ul className="space-y-1">
              {DEMO_PROMPTS.map((p) => (
                <li key={p.prompt}>
                  <button
                    type="button"
                    onClick={() => onPromptClick?.(p.prompt)}
                    className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-left text-xs text-slate-700 hover:bg-slate-50"
                    title={p.prompt}
                  >
                    <span className="font-semibold text-ford-ink">
                      {p.label}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
