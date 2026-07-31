// Manager Phase 4: "Meet the team" page.
//
// Manager-facing in v1 (linked from the dashboard nav). Lists every
// salesperson with photo, title, specialties, phone/email + workspace
// link. Customer-side selection is a Phase 5 concern and intentionally
// not wired here.

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, RefreshCw } from "lucide-react";

import SalespersonCard from "@/components/SalespersonCard";
import {
  fetchAdminSalespeople,
  type SalespersonAdmin,
} from "@/lib/api";

export default function SalesTeamPage() {
  const [advisors, setAdvisors] = useState<SalespersonAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchAdminSalespeople()
      .then((res) => {
        if (cancelled) return;
        setAdvisors(res.results);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Failed to load the team.",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
            Sales team
          </h1>
          <p className="text-sm text-slate-500">
            Assign leads, hand off conversations, and open per-advisor
            workspaces.
          </p>
        </div>
        {loading ? (
          <RefreshCw className="h-4 w-4 animate-spin text-slate-400" />
        ) : null}
      </div>

      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {!loading && advisors.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-300 bg-white px-4 py-8 text-center text-sm text-slate-500">
          No salespeople have been seeded yet. Run{" "}
          <code className="rounded bg-slate-100 px-1 font-mono text-[11px]">
            python manage.py seed_phase4_demo
          </code>{" "}
          to populate the team.
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {advisors.map((a) => (
          <SalespersonCard
            key={a.id}
            advisor={a}
            showWorkspaceLink
            showInactiveBadge
          />
        ))}
      </div>
    </div>
  );
}
