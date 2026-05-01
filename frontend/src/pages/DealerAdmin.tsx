import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CarFront,
  CircleDollarSign,
  MessagesSquare,
  RefreshCw,
  RotateCcw,
  Users,
} from "lucide-react";

import AuditPanel from "@/components/AuditPanel";
import GenerateAdModal from "@/components/GenerateAdModal";
import HandoffQueue from "@/components/HandoffQueue";
import LeadDetailModal from "@/components/LeadDetailModal";
import RecommendedActions from "@/components/RecommendedActions";
import SalesPipeline from "@/components/SalesPipeline";
import StatCard from "@/components/StatCard";
import {
  fetchAdminChatSessions,
  fetchAdminLeads,
  fetchAdminTrends,
  resetDemo,
  type AdminChatSessionRow,
  type AdminLead,
  type PipelineResponse,
  type RecommendedAction,
  type RecommendedActionCTA,
  type TrendsResponse,
} from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

function urgencyLabel(value: string | null | undefined) {
  switch (value) {
    case "immediate":
      return "Buying now";
    case "this_week":
      return "This week";
    case "this_month":
      return "This month";
    case "researching":
      return "Researching";
    default:
      return value || "—";
  }
}

function timeAgo(iso: string) {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const seconds = Math.floor((Date.now() - then) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function DealerAdmin() {
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [leads, setLeads] = useState<AdminLead[]>([]);
  const [sessions, setSessions] = useState<AdminChatSessionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [resetting, setResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [pipelinePayload, setPipelinePayload] = useState<PipelineResponse | null>(null);
  const [adAction, setAdAction] = useState<RecommendedAction | null>(null);

  function handleRecommendedActionCTA(
    cta: RecommendedActionCTA,
    _action: RecommendedAction,
  ) {
    // CTAs are navigation hints in v1 — scroll to the relevant panel.
    // The HandoffQueue panel handles "view leads" intents; the
    // SalesPipeline handles band/stage focus.
    if (
      cta.kind === "view_high_intent_leads" ||
      cta.kind === "view_aging_leads" ||
      cta.kind === "view_leads_in_band"
    ) {
      const target = document.getElementById("handoff-queue-anchor");
      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }

  async function load() {
    setError(null);
    try {
      const [t, l, s] = await Promise.all([
        fetchAdminTrends(),
        fetchAdminLeads({ limit: 25 }),
        fetchAdminChatSessions(25),
      ]);
      setTrends(t);
      setLeads(l.results);
      setSessions(s.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard.");
    }
  }

  useEffect(() => {
    setLoading(true);
    load().finally(() => setLoading(false));
  }, []);

  async function handleRefresh() {
    setRefreshing(true);
    await load();
    setRefreshKey((k) => k + 1); // Triggers HandoffQueue + AuditPanel reloads.
    setRefreshing(false);
  }

  async function handleReset() {
    if (
      !window.confirm(
        "Reset the demo? This deletes all chat sessions and leads, then reloads the bundled demo vehicles. Imported (CSV) vehicles are kept.",
      )
    ) {
      return;
    }
    setResetting(true);
    setResetMessage(null);
    try {
      const res = await resetDemo();
      setResetMessage(
        `Reset done — cleared ${res.cleared.leads} leads and ${res.cleared.chat_sessions} sessions; ${res.demo_vehicles} demo vehicles loaded; ${res.imported_vehicles_remaining} imported vehicles preserved.`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed.");
    } finally {
      setResetting(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-end justify-between">
          <div>
            <div className="h-7 w-56 animate-pulse rounded bg-slate-200" />
            <div className="mt-2 h-4 w-72 animate-pulse rounded bg-slate-100" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="card h-28 animate-pulse bg-white p-5" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="card h-48 animate-pulse bg-white p-5" />
          ))}
        </div>
        <div className="card h-64 animate-pulse bg-white" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ford-ink">Manager dashboard</h1>
          <p className="text-sm text-slate-500">
            Snapshot of customer activity, lead pipeline, and inventory pull.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleRefresh}
            className="btn-ghost"
            disabled={refreshing}
          >
            <RefreshCw
              className={refreshing ? "h-4 w-4 animate-spin" : "h-4 w-4"}
            />
            Refresh
          </button>
          <button
            type="button"
            onClick={handleReset}
            className="btn-ghost text-amber-700"
            disabled={resetting}
            title="Wipe demo conversations and reload demo vehicles. Imported vehicles are preserved."
          >
            <RotateCcw
              className={resetting ? "h-4 w-4 animate-spin" : "h-4 w-4"}
            />
            Reset demo
          </button>
        </div>
      </div>

      {resetMessage && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {resetMessage}
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Chat sessions"
          value={trends?.total_chat_sessions ?? 0}
          hint={`${sessions.filter((s) => s.lead_created).length} converted to leads`}
          icon={<MessagesSquare className="h-4 w-4" />}
        />
        <StatCard
          label="Leads"
          value={trends?.total_leads ?? 0}
          hint={`${trends?.total_leads_last_7d ?? 0} in last 7 days`}
          tone="good"
          icon={<Users className="h-4 w-4" />}
        />
        <StatCard
          label="Avg target payment"
          value={
            trends?.average_target_monthly_payment != null
              ? `${formatCurrency(trends.average_target_monthly_payment)}/mo`
              : "—"
          }
          hint="Across captured leads"
          icon={<CircleDollarSign className="h-4 w-4" />}
        />
        <StatCard
          label="Budget mismatches"
          value={trends?.budget_mismatch_count ?? 0}
          hint="Leads with vehicles 25%+ over budget"
          tone={
            (trends?.budget_mismatch_count ?? 0) > 0 ? "warn" : "default"
          }
          icon={<AlertTriangle className="h-4 w-4" />}
        />
      </div>

      {/* Manager Phase 2 / Feature C: deterministic next-action cards.
          Reads recommended_actions from the SalesPipeline payload below
          so we make exactly one /admin/pipeline/ call per refresh. */}
      <RecommendedActions
        actions={pipelinePayload?.recommended_actions ?? []}
        onCTA={handleRecommendedActionCTA}
        onGenerateAd={(action) => setAdAction(action)}
      />

      {/* Manager Phase 2: 5-column sales pipeline + demand-vs-supply panel. */}
      <SalesPipeline
        refreshKey={refreshKey}
        onCardClick={(id) => setSelectedLeadId(id)}
        onPayloadChange={setPipelinePayload}
      />

      {/* Manager Phase 1: AI safety / guard events panel. */}
      <AuditPanel refreshKey={refreshKey} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Top models */}
        <section className="card p-5">
          <h2 className="mb-3 text-sm font-bold text-ford-ink">
            Top requested models
          </h2>
          {trends && trends.top_requested_models.length > 0 ? (
            <ul className="space-y-2">
              {trends.top_requested_models.map((m) => (
                <li
                  key={m.value}
                  className="flex items-center justify-between text-sm"
                >
                  <span>{m.value}</span>
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                    {m.count}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-slate-500">No data yet.</div>
          )}
        </section>

        {/* Top vehicle types */}
        <section className="card p-5">
          <h2 className="mb-3 text-sm font-bold text-ford-ink">
            Top requested vehicle types
          </h2>
          {trends && trends.top_requested_vehicle_types.length > 0 ? (
            <ul className="space-y-2">
              {trends.top_requested_vehicle_types.map((t) => (
                <li
                  key={t.value}
                  className="flex items-center justify-between text-sm capitalize"
                >
                  <span>{t.value}</span>
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                    {t.count}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-slate-500">No data yet.</div>
          )}
        </section>

        {/* Most selected vehicles */}
        <section className="card p-5">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-ford-ink">
            <CarFront className="h-4 w-4" /> Most-selected vehicles
          </h2>
          {trends && trends.most_selected_vehicles.length > 0 ? (
            <ul className="space-y-2">
              {trends.most_selected_vehicles.map((v) => (
                <li
                  key={v.id}
                  className="flex items-center justify-between text-sm"
                >
                  <div>
                    <div className="font-medium">{v.display_name}</div>
                    <div className="text-xs text-slate-500">
                      Stock #{v.stock_number} · {formatCurrency(v.price)}
                    </div>
                  </div>
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                    {v.lead_count}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-slate-500">
              No vehicles flagged on a lead yet.
            </div>
          )}
        </section>
      </div>

      {/* Manager Phase 1: handoff/triage queue. */}
      <div id="handoff-queue-anchor" />
      <HandoffQueue
        refreshKey={refreshKey}
        onRowClick={(id) => setSelectedLeadId(id)}
      />

      {/* Recent leads table */}
      <section className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h2 className="text-sm font-bold text-ford-ink">Recent leads</h2>
          <span className="text-xs text-slate-500">
            {leads.length} of {trends?.total_leads ?? 0}
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">When</th>
                <th className="px-4 py-2">Customer</th>
                <th className="px-4 py-2">Target</th>
                <th className="px-4 py-2">Urgency</th>
                <th className="px-4 py-2">Vehicles</th>
                <th className="px-4 py-2">Next action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {leads.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-6 text-center text-slate-500"
                  >
                    No leads yet — go run a chat in the demo.
                  </td>
                </tr>
              )}
              {leads.map((lead) => (
                <tr
                  key={lead.id}
                  className="cursor-pointer hover:bg-slate-50"
                  onClick={() => setSelectedLeadId(lead.id)}
                >
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {timeAgo(lead.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-semibold text-ford-ink">{lead.name}</div>
                    <div className="text-xs text-slate-500">
                      {lead.phone || lead.email || "—"}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {lead.target_monthly_payment ? (
                      <div>
                        {formatCurrency(lead.target_monthly_payment)}/mo
                        {lead.down_payment ? (
                          <div className="text-xs text-slate-500">
                            {formatCurrency(lead.down_payment)} down
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs capitalize">
                    {urgencyLabel(lead.urgency)}
                  </td>
                  <td className="px-4 py-3">
                    {lead.interested_vehicles.length > 0 ? (
                      <ul className="space-y-0.5">
                        {lead.interested_vehicles.slice(0, 3).map((v) => (
                          <li
                            key={v.id}
                            className="text-xs text-slate-700"
                            title={`${v.display_name} · ${v.stock_number}`}
                          >
                            {v.display_name}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-xs text-slate-400">none flagged</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-600">
                    {lead.recommended_next_action || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Recent sessions table */}
      <section className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h2 className="text-sm font-bold text-ford-ink">Recent chat sessions</h2>
          <span className="text-xs text-slate-500">
            {sessions.length} of {trends?.total_chat_sessions ?? 0}
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Updated</th>
                <th className="px-4 py-2">Customer</th>
                <th className="px-4 py-2">Profile</th>
                <th className="px-4 py-2">Last message</th>
                <th className="px-4 py-2 text-right">Msgs</th>
                <th className="px-4 py-2 text-right">Lead</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sessions.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-6 text-center text-slate-500"
                  >
                    No sessions yet.
                  </td>
                </tr>
              )}
              {sessions.map((s) => {
                const profile = s.extracted_profile as Record<string, unknown>;
                const profileBits: string[] = [];
                if (profile.intent) profileBits.push(String(profile.intent));
                if (profile.vehicle_type)
                  profileBits.push(String(profile.vehicle_type));
                if (profile.model) profileBits.push(String(profile.model));
                if (profile.target_monthly_payment)
                  profileBits.push(`$${profile.target_monthly_payment}/mo`);
                return (
                  <tr key={s.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {timeAgo(s.updated_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-ford-ink">
                        {s.customer_name || "Anonymous"}
                      </div>
                      <div className="text-xs text-slate-500">
                        {s.customer_email || s.customer_phone || s.id.slice(0, 8)}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {profileBits.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {profileBits.map((b) => (
                            <span
                              key={b}
                              className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-700"
                            >
                              {b}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">no profile yet</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      {s.last_message?.content || "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-slate-700">
                      {s.message_count}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {s.lead_created ? (
                        <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
                          captured
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Recent intents */}
      {trends && trends.recent_customer_intents.length > 0 && (
        <section className="card p-5">
          <h2 className="mb-3 text-sm font-bold text-ford-ink">
            Recent customer intents
          </h2>
          <div className="flex flex-wrap gap-2">
            {trends.recent_customer_intents.map((r) => (
              <span
                key={r.session_id + r.updated_at}
                className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-700"
                title={`Updated ${timeAgo(r.updated_at)}`}
              >
                <span className="font-semibold capitalize">
                  {r.intent.replace("_", " ")}
                </span>
                {r.model ? ` · ${r.model}` : ""}
                {r.vehicle_type && !r.model ? ` · ${r.vehicle_type}` : ""}
                {r.target_monthly_payment
                  ? ` · $${r.target_monthly_payment}/mo`
                  : ""}
              </span>
            ))}
          </div>
        </section>
      )}

      <LeadDetailModal
        // Force remount on leadId change so no stale detail/packet
        // state from a previous lead can bleed into the current one.
        key={selectedLeadId ?? "closed"}
        leadId={selectedLeadId}
        onClose={() => setSelectedLeadId(null)}
        onHandoffComplete={() => load()}
      />

      {/* Manager Phase 3: Generate Ad modal. */}
      <GenerateAdModal
        key={adAction?.id ?? "ad-closed"}
        action={adAction}
        onClose={() => setAdAction(null)}
      />
    </div>
  );
}
