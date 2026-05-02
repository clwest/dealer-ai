// SESSION_015 — Leads page stub.
//
// Placeholder destination for the Overview page's "Today's leads →
// View all" link. The full pipeline view (qualification status,
// handoff trail, salesperson assignment, conversation transcripts)
// is scheduled for a later session — leaving this stub keeps the
// navigation feeling complete without committing to the larger
// build.
//
// Renders a lightweight preview of the most recent leads so the
// dealer sees *something* real even before the full page lands.

import { useEffect, useState } from "react";
import { ArrowLeft, Inbox, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { fetchAdminLeads, type AdminLead } from "@/lib/api";

export default function LeadsPage() {
  const [leads, setLeads] = useState<AdminLead[] | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchAdminLeads({ limit: 10 })
      .then((res) => {
        if (cancelled) return;
        setLeads(res.results);
      })
      .catch(() => {
        if (cancelled) return;
        setLeads([]);
      })
      .finally(() => {
        if (cancelled) return;
        setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Leads
          </h1>
          <p className="text-sm text-muted-foreground">
            Assistant-sourced conversations. The full pipeline view —
            qualification status, handoff trail, salesperson assignment —
            ships in a later session.
          </p>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link to="/dealer-ai-overview">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Overview
          </Link>
        </Button>
      </header>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-primary" />
              <CardTitle>Recent leads</CardTitle>
            </div>
            <Badge variant="secondary" className="font-normal">
              Preview · full view coming soon
            </Badge>
          </div>
          <CardDescription>
            Most recent assistant-sourced leads — read-only.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!loaded ? (
            <p className="py-2 text-sm text-muted-foreground">Loading…</p>
          ) : !leads || leads.length === 0 ? (
            <EmptyState />
          ) : (
            <ul className="divide-y divide-border">
              {leads.map((lead) => (
                <LeadRow key={lead.id} lead={lead} />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function LeadRow({ lead }: { lead: AdminLead }) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
      <div className="min-w-0 flex-1 space-y-0.5">
        <div className="truncate font-medium text-foreground">
          {lead.name?.trim() || "Unnamed lead"}
        </div>
        <div className="truncate text-xs text-muted-foreground">
          {[
            lead.phone || null,
            lead.email || null,
            lead.target_monthly_payment
              ? `$${lead.target_monthly_payment}/mo target`
              : null,
          ]
            .filter(Boolean)
            .join(" · ") || "No contact captured."}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {lead.urgency ? (
          <Badge variant="outline" className="font-normal">
            {humanize(lead.urgency)}
          </Badge>
        ) : null}
        {lead.handed_off ? (
          <Badge
            variant="outline"
            className="border-emerald-200 bg-emerald-50 text-emerald-700"
          >
            Handed off
          </Badge>
        ) : (
          <Badge variant="secondary" className="font-normal">
            New
          </Badge>
        )}
      </div>
    </li>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-2 py-6 text-center">
      <Inbox className="h-6 w-6 text-muted-foreground" aria-hidden />
      <p className="text-sm text-muted-foreground">
        No leads yet. They'll appear here as conversations qualify.
      </p>
    </div>
  );
}

function humanize(token: string): string {
  return token
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\w/, (c) => c.toUpperCase());
}
