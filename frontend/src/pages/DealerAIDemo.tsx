import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Car, Loader2, MessageSquarePlus, Send, Sparkles } from "lucide-react";

import ChatBubble from "@/components/ChatBubble";
import DemoHelperPanel from "@/components/DemoHelperPanel";
import LeadCaptureModal from "@/components/LeadCaptureModal";
import VehicleCard from "@/components/VehicleCard";
import VehicleDetailModal from "@/components/VehicleDetailModal";
import {
  createDealerLead,
  sendDealerMessage,
  startDealerChat,
  type ChatMessage,
  type LeadInput,
  type Vehicle,
} from "@/lib/api";
import { useBrand } from "@/lib/brand";

// Demo openers — match the verified scenarios in
// `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md`. Two are the canonical
// SESSION_003 smoke shapes (4WD-finance + cash-commuter); the
// others are dealer-realistic shape variants that exercise the
// same code paths (budget classification, lever-flex, model
// followup) without overlapping the canonical pair.
const SUGGESTED_PROMPTS = [
  "I need a 4WD truck around $500/mo with $3k down.",
  "I have cash and want good gas mileage.",
  "Show me a used SUV under $30k for my family.",
  "What's a reliable commuter under $15k?",
];

export default function DealerAIDemo() {
  const brand = useBrand();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [matchedVehicles, setMatchedVehicles] = useState<Vehicle[]>([]);
  const [selectedVehicleIds, setSelectedVehicleIds] = useState<Set<number>>(
    new Set(),
  );
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [starting, setStarting] = useState(false);
  const [leadOpen, setLeadOpen] = useState(false);
  const [leadConfirmation, setLeadConfirmation] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [detailVehicleId, setDetailVehicleId] = useState<number | null>(null);

  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages, sending]);

  const interestedVehicles = useMemo(
    () => matchedVehicles.filter((v) => selectedVehicleIds.has(v.id)),
    [matchedVehicles, selectedVehicleIds],
  );

  function toggleVehicle(v: Vehicle) {
    setSelectedVehicleIds((prev) => {
      const next = new Set(prev);
      if (next.has(v.id)) next.delete(v.id);
      else next.add(v.id);
      return next;
    });
  }

  async function ensureSession(): Promise<string> {
    if (sessionId) return sessionId;
    setStarting(true);
    try {
      // Create a fresh empty session. We deliberately do NOT pass
      // `initial_message` here — the caller (handleSend) has already shown
      // an optimistic user bubble and will follow up with sendDealerMessage,
      // which gives us a single, predictable update path. Replacing the
      // local messages array with the server's empty session list at this
      // point would wipe the optimistic bubble and make the conversation
      // feel broken (Phase 8d bug).
      const res = await startDealerChat({});
      setSessionId(res.session.id);
      if (res.matched_vehicles.length) {
        setMatchedVehicles(res.matched_vehicles);
      }
      return res.session.id;
    } finally {
      setStarting(false);
    }
  }

  async function handleSend(text?: string) {
    const content = (text ?? input).trim();
    if (!content) return;
    setError(null);
    setInput("");

    const optimistic: ChatMessage = {
      id: Date.now(),
      role: "user",
      content,
      matched_vehicles: [],
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, optimistic]);
    setSending(true);

    try {
      const sid = await ensureSession();
      const res = await sendDealerMessage(sid, content);
      setMessages((m) => [...m, res.assistant_message]);
      if (res.matched_vehicles.length > 0) {
        setMatchedVehicles(res.matched_vehicles);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message.");
    } finally {
      setSending(false);
    }
  }

  function handleNewConversation() {
    setSessionId(null);
    setMessages([]);
    setMatchedVehicles([]);
    setSelectedVehicleIds(new Set());
    setLeadConfirmation(null);
    setError(null);
  }

  async function handleLeadSubmit(lead: LeadInput) {
    const payload: LeadInput = { ...lead, session: sessionId };
    await createDealerLead(payload);
    setLeadOpen(false);
    setLeadConfirmation(
      `Thanks — a ${brand.dealershipName} advisor has your details and will follow up shortly.`,
    );
  }

  return (
    <div className="space-y-4">
      {/* Demo Mode banner — frames the page for non-technical viewers
          so they immediately understand they're looking at the live
          customer-facing assistant. Pure presentational; no state. */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-ford-blue/20 bg-gradient-to-r from-ford-blue/5 via-white to-ford-accent/5 px-5 py-3 shadow-soft">
        <div>
          <div className="flex items-center gap-2 text-base font-bold text-ford-ink">
            <Sparkles className="h-4 w-4 text-ford-accent" />
            AI Sales Assistant — Live Demo
          </div>
          <div className="text-xs text-slate-500">
            Ask like a customer. I'll show you what your team would say.
          </div>
        </div>
        <div
          className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700"
          title="Backend + Ollama healthy"
        >
          <span
            aria-hidden
            className="inline-block h-2 w-2 animate-pulse rounded-full bg-emerald-500"
          />
          Live
        </div>
      </div>

    <div className="grid gap-6 lg:grid-cols-[1fr_400px]">
      {/* Chat column */}
      <section className="card flex h-[78vh] flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-ford-blue text-white">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-bold text-ford-ink">
                {`Ask the ${brand.dealershipName} sales assistant`}
              </div>
              <div className="text-xs text-slate-500">
                Inventory · Payments · Comparisons · Handoff to sales
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={handleNewConversation}
            className="btn-ghost"
            disabled={starting || sending}
          >
            <MessageSquarePlus className="h-4 w-4" />
            New chat
          </button>
        </header>

        <div
          ref={chatRef}
          className="flex-1 space-y-4 overflow-y-auto bg-ford-mist/40 px-5 py-4"
        >
          {messages.length === 0 && !sending && (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-slate-500">
              <Sparkles className="h-6 w-6 text-ford-accent" />
              <div className="max-w-md text-sm">
                {`Welcome to ${brand.dealershipName}. Tell me what you're shopping for — a payment, a body style, a must-have feature. I'll pull live inventory, sketch realistic numbers, and hand you off to a real advisor when you're ready.`}
              </div>
              <div className="mt-2 flex flex-wrap justify-center gap-2">
                {SUGGESTED_PROMPTS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50"
                    onClick={() => handleSend(p)}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m) => (
            <ChatBubble key={m.id} message={m} />
          ))}
          {sending && (
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Thinking…
            </div>
          )}
          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}
          {leadConfirmation && (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              {leadConfirmation}
            </div>
          )}
        </div>

        <form
          className="border-t border-slate-200 bg-white p-4"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <div className="flex items-center gap-2">
            <input
              className="input flex-1"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about an F-150, payments, comparisons…"
              disabled={sending || starting}
            />
            <button
              type="submit"
              className="btn-primary"
              disabled={sending || starting || !input.trim()}
            >
              {sending || starting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Send
            </button>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
            <span>
              {`Payments shown are estimates. A ${brand.dealershipName} advisor confirms real numbers.`}
            </span>
            <button
              type="button"
              className="font-semibold text-ford-accent hover:underline"
              onClick={() => setLeadOpen(true)}
            >
              Talk to a real advisor →
            </button>
          </div>
        </form>
      </section>

      {/* Vehicles column */}
      <aside className="space-y-4">
        <DemoHelperPanel
          onPromptClick={(p) => handleSend(p)}
          onAfterAction={handleNewConversation}
        />

        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-bold text-ford-ink">
                Matched vehicles
              </div>
              <div className="text-xs text-slate-500">
                Tap to flag for the lead handoff
              </div>
            </div>
            <button
              type="button"
              className="btn-primary"
              onClick={() => setLeadOpen(true)}
            >
              Capture lead
            </button>
          </div>
        </div>

        {sending && matchedVehicles.length === 0 ? (
          <VehicleSkeletonList />
        ) : matchedVehicles.length === 0 ? (
          <div className="card flex flex-col items-center justify-center gap-3 p-8 text-center text-sm text-slate-500">
            <Car className="h-7 w-7 text-ford-accent" />
            <div className="font-semibold text-ford-ink">
              No vehicles matched yet
            </div>
            <p className="max-w-xs text-xs text-slate-500">
              Tell the concierge what body style, model, or budget you have in
              mind — live inventory matches will appear here.
            </p>
            <Link
              to="/dealer-ai-admin"
              className="text-xs font-semibold text-ford-accent hover:underline"
            >
              Manager view: dashboard →
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {matchedVehicles.map((v) => (
              <VehicleCard
                key={v.id}
                vehicle={v}
                selected={selectedVehicleIds.has(v.id)}
                onSelect={toggleVehicle}
                onOpenDetails={(vehicle) => setDetailVehicleId(vehicle.id)}
              />
            ))}
          </div>
        )}
      </aside>

      <LeadCaptureModal
        open={leadOpen}
        onClose={() => setLeadOpen(false)}
        onSubmit={handleLeadSubmit}
        interestedVehicles={interestedVehicles}
      />

      <VehicleDetailModal
        vehicleId={detailVehicleId}
        sessionId={sessionId}
        selected={
          detailVehicleId != null
            ? selectedVehicleIds.has(detailVehicleId)
            : undefined
        }
        onClose={() => setDetailVehicleId(null)}
        onToggleSelect={toggleVehicle}
      />
    </div>
    </div>
  );
}

function VehicleSkeletonList() {
  return (
    <div className="grid grid-cols-1 gap-3">
      {[0, 1, 2].map((i) => (
        <div key={i} className="card overflow-hidden">
          <div className="h-40 w-full animate-pulse bg-slate-100" />
          <div className="space-y-2 p-4">
            <div className="h-4 w-2/3 animate-pulse rounded bg-slate-100" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-slate-100" />
            <div className="flex gap-2 pt-1">
              <div className="h-5 w-12 animate-pulse rounded bg-slate-100" />
              <div className="h-5 w-12 animate-pulse rounded bg-slate-100" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
