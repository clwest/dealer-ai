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

const SUGGESTED_PROMPTS = [
  "Show me F-150s under $65k with $5,000 down.",
  "I need a used SUV under $30k for my family.",
  "What's good for commuting from the city but still useful on the farm?",
  "I need something that can tow a small camper.",
];

export default function DealerAIDemo() {
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
      "Thanks — a Freedom Ford advisor has your details and will follow up shortly.",
    );
  }

  return (
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
                Ask the Freedom Ford concierge
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
                Hi! I'm Freedom Ford's AI concierge. Tell me what you're
                looking for — I'll find vehicles in our inventory, sketch
                realistic payments, and connect you with sales when you're
                ready.
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
              Payments shown are estimates. A Freedom Ford advisor confirms real
              numbers.
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
