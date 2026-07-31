// Manager Phase 4: per-advisor workspace.
//
// Reachable via /dealer-ai-advisor/<slug>. URL slug is the only access
// control in v1 (see PROJECT_PIPELINE.md §6 — slug-by-obscurity, real
// auth lands in Phase 5). Renders the salesperson hero, an open-leads
// table, and a contacted-leads table. Each row supports drill-through
// to the existing LeadDetailModal and a "Draft follow-up" action that
// opens FollowUpDraftModal.

import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronLeft, RefreshCw } from "lucide-react";

import FollowUpDraftModal from "@/components/FollowUpDraftModal";
import LeadDetailModal from "@/components/LeadDetailModal";
import MyLeadsTable from "@/components/MyLeadsTable";
import SalespersonCard from "@/components/SalespersonCard";
import {
  fetchAdvisorWorkspace,
  type AdminLead,
  type AdvisorWorkspaceResponse,
} from "@/lib/api";

export default function AdvisorWorkspacePage() {
  const { slug } = useParams<{ slug: string }>();
  const [data, setData] = useState<AdvisorWorkspaceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [draftLead, setDraftLead] = useState<AdminLead | null>(null);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchAdvisorWorkspace(slug)
      .then((res) => {
        if (cancelled) return;
        setData(res);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load advisor workspace.",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug, refreshKey]);

  if (!slug) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link
            to="/dealer-ai-admin"
            className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700"
          >
            <ChevronLeft className="h-3 w-3" />
            Back to dashboard
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-brand-ink">
            Advisor workspace
          </h1>
          <p className="text-sm text-slate-500">
            Your assigned leads, prior conversation summaries, and
            AI-drafted follow-ups (drafts only — never auto-sent).
          </p>
        </div>
        <button
          type="button"
          onClick={() => setRefreshKey((k) => k + 1)}
          className="btn-ghost"
          disabled={loading}
        >
          <RefreshCw
            className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"}
          />
          Refresh
        </button>
      </div>

      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {data ? (
        <>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
            <SalespersonCard
              advisor={data.salesperson}
              showWorkspaceLink={false}
            />
            <div className="card flex flex-col justify-between gap-3 p-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    Open leads
                  </div>
                  <div className="text-3xl font-bold text-brand-ink">
                    {data.counts.open}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    Contacted (30d)
                  </div>
                  <div className="text-3xl font-bold text-brand-ink">
                    {data.counts.contacted}
                  </div>
                </div>
              </div>
              <div className="text-xs text-slate-500">
                Click a row to open the lead. Use{" "}
                <span className="font-semibold">Draft follow-up</span> to
                generate an SMS or email draft for any open lead.
              </div>
            </div>
          </div>

          <section className="space-y-2">
            <div className="flex items-end justify-between">
              <h2 className="text-sm font-bold text-brand-ink">
                Open leads
              </h2>
              <span className="text-xs text-slate-500">
                {data.open_leads.length} of {data.counts.open}
              </span>
            </div>
            <MyLeadsTable
              leads={data.open_leads}
              emptyText="No open leads assigned to you. Manager assigns leads from the dashboard."
              onRowClick={(id) => setSelectedLeadId(id)}
              onDraftFollowUp={(lead) => setDraftLead(lead)}
            />
          </section>

          <section className="space-y-2">
            <div className="flex items-end justify-between">
              <h2 className="text-sm font-bold text-brand-ink">
                Contacted recently
              </h2>
              <span className="text-xs text-slate-500">
                Last 30 days · {data.counts.contacted}
              </span>
            </div>
            <MyLeadsTable
              leads={data.contacted_leads}
              emptyText="No contacted leads in the last 30 days."
              onRowClick={(id) => setSelectedLeadId(id)}
            />
          </section>
        </>
      ) : null}

      <LeadDetailModal
        key={selectedLeadId ?? "closed"}
        leadId={selectedLeadId}
        onClose={() => setSelectedLeadId(null)}
        onHandoffComplete={() => setRefreshKey((k) => k + 1)}
      />

      <FollowUpDraftModal
        key={draftLead?.id ?? "draft-closed"}
        lead={draftLead}
        salespersonSlug={slug}
        onClose={() => setDraftLead(null)}
      />
    </div>
  );
}
