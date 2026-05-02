// SESSION_015 — Dealer OS overview page, wired to real APIs.
//
// Five cards, all read-only, all sourced from endpoints already
// serving traffic on the backend (no new endpoints introduced this
// session):
//   • AI Sales Assistant   ← /onboarding/profile/
//   • Coaching summary     ← /admin/audit-events/?since=24h
//                            (totals — guard / scrub / rewrite metrics
//                             surface whether the manager's coaching
//                             rules are being enforced in production)
//   • Recent activity      ← /admin/audit-events/?since=24h
//                            (recent_events[])
//   • Today's leads        ← /admin/leads/?limit=3
//   • Attention items      ← derived from /onboarding/profile/
//
// All four fetches run in parallel and fail independently. One bad
// endpoint doesn't blank the page; downstream cards render their
// own empty state ("—" / "No activity yet").

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  GraduationCap,
  ListChecks,
  Users,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  fetchAdminLeads,
  fetchAuditEvents,
  fetchOnboardingProfile,
  type AdminLead,
  type AuditEvent,
  type AuditEventsResponse,
  type OnboardingProfilePayload,
} from "@/lib/api";

interface AttentionItem {
  id: string;
  text: string;
}

export default function DealerOverviewPage() {
  const [profile, setProfile] = useState<OnboardingProfilePayload | null>(null);
  const [audit, setAudit] = useState<AuditEventsResponse | null>(null);
  const [leads, setLeads] = useState<AdminLead[] | null>(null);
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);

  // Independent fetches with Promise.allSettled so a single broken
  // endpoint doesn't take down the whole page. Each setter falls back
  // to its initial null and downstream cards render their empty
  // states (or "—") gracefully.
  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([
      fetchOnboardingProfile(),
      fetchAuditEvents({ since: "24h", limit: 5 }),
      fetchAdminLeads({ limit: 3 }),
    ]).then(([profileRes, auditRes, leadsRes]) => {
      if (cancelled) return;
      if (profileRes.status === "fulfilled") setProfile(profileRes.value);
      if (auditRes.status === "fulfilled") setAudit(auditRes.value);
      if (leadsRes.status === "fulfilled") setLeads(leadsRes.value.results);
      setLoadedAt(new Date());
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const attentionItems = useMemo(
    () => deriveAttentionItems(profile),
    [profile],
  );

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Overview
        </h1>
        <p className="text-sm text-muted-foreground">
          Your AI sales assistant at a glance.
          {loadedAt ? (
            <span className="ml-1 text-xs text-muted-foreground/70">
              · refreshed {formatClock(loadedAt)}
            </span>
          ) : null}
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <AssistantStatusCard profile={profile} />
        <CoachingSummaryCard audit={audit} />
        <RecentActivityCard events={audit?.recent_events ?? null} />
        <TodaysLeadsCard leads={leads} />
        <AttentionItemsCard items={attentionItems} loaded={profile !== null} />
      </div>
    </div>
  );
}

// ─── Cards ─────────────────────────────────────────────────────────────────

function AssistantStatusCard({
  profile,
}: {
  profile: OnboardingProfilePayload | null;
}) {
  const tone = profile?.sales_tone || null;
  const bannedCount = countBannedPhrases(profile?.banned_phrases);
  const updatedAt = profile?.updated_at ?? null;
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-primary" />
            <CardTitle>AI Sales Assistant</CardTitle>
          </div>
          <Badge>Active</Badge>
        </div>
        <CardDescription>
          Live for customer chat and manager coaching.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4">
        <Stat label="Tone" value={tone ? humanize(tone) : "Not set"} />
        <Stat
          label="Banned phrases"
          value={bannedCount === null ? "—" : String(bannedCount)}
        />
        <Stat label="Last updated" value={formatTimestamp(updatedAt)} />
        <Stat label="Status" value="Active" />
      </CardContent>
    </Card>
  );
}

function CoachingSummaryCard({
  audit,
}: {
  audit: AuditEventsResponse | null;
}) {
  const totals = audit?.totals;
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <GraduationCap className="h-4 w-4 text-primary" />
          <CardTitle>Coaching summary</CardTitle>
        </div>
        <CardDescription>
          How well the assistant is following your training, last 24 hours.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4">
        <Stat
          label="Rules enforced"
          value={formatCount(totals?.total_guard_events)}
        />
        <Stat
          label="Phrases scrubbed"
          value={formatCount(totals?.scrubs_fired)}
        />
        <Stat
          label="Replies rewritten"
          value={formatCount(totals?.post_llm_rewrites)}
        />
        <Stat
          label="Early stops"
          value={formatCount(totals?.pre_llm_short_circuits)}
        />
      </CardContent>
    </Card>
  );
}

function RecentActivityCard({
  events,
}: {
  events: AuditEvent[] | null;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <ListChecks className="h-4 w-4 text-primary" />
          <CardTitle>Recent activity</CardTitle>
        </div>
        <CardDescription>
          Latest moments the assistant enforced a rule.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {events === null ? (
          <SkeletonList rows={3} />
        ) : events.length === 0 ? (
          <EmptyLine text="No assistant activity in the last 24 hours." />
        ) : (
          <ul className="divide-y divide-border">
            {events.slice(0, 4).map((e, idx) => (
              <li
                key={`${e.session_id ?? "anon"}-${e.message_id}-${idx}`}
                className="flex items-start justify-between gap-3 py-2.5 text-sm"
              >
                <div className="min-w-0">
                  <div className="text-foreground">
                    {humanizeFlag(e.flag, e.category)}
                  </div>
                  {e.user_message_excerpt ? (
                    <div className="truncate text-xs text-muted-foreground">
                      "{e.user_message_excerpt}"
                    </div>
                  ) : null}
                </div>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {formatRelative(e.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function TodaysLeadsCard({ leads }: { leads: AdminLead[] | null }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-primary" />
            <CardTitle>Today's leads</CardTitle>
          </div>
          <Link
            to="/dealer-ai-leads"
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            View all
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
        <CardDescription>
          Most recent assistant-sourced conversations.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {leads === null ? (
          <SkeletonList rows={3} />
        ) : leads.length === 0 ? (
          <EmptyLine text="No leads yet — they'll appear here as conversations qualify." />
        ) : (
          <ul className="divide-y divide-border">
            {leads.slice(0, 3).map((lead) => (
              <li
                key={lead.id}
                className="flex items-start justify-between gap-3 py-2.5 text-sm"
              >
                <div className="min-w-0">
                  <div className="truncate text-foreground">
                    {lead.name?.trim() || "Unnamed lead"}
                  </div>
                  <div className="truncate text-xs text-muted-foreground">
                    {leadSummaryLine(lead)}
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <UrgencyBadge urgency={lead.urgency} />
                  <span className="text-xs text-muted-foreground">
                    {formatRelative(lead.created_at)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function AttentionItemsCard({
  items,
  loaded,
}: {
  items: AttentionItem[];
  loaded: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-primary" />
          <CardTitle>Attention items</CardTitle>
        </div>
        <CardDescription>Setup steps still pending.</CardDescription>
      </CardHeader>
      <CardContent>
        {!loaded ? (
          <SkeletonList rows={2} />
        ) : items.length === 0 ? (
          <EmptyLine text="All clear — your assistant is fully configured." />
        ) : (
          <ul className="space-y-2">
            {items.map((item) => (
              <li
                key={item.id}
                className="flex items-start gap-2 text-sm text-foreground"
              >
                <span
                  aria-hidden
                  className="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500"
                />
                <span>{item.text}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Pieces ────────────────────────────────────────────────────────────────

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-background p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-base font-semibold text-foreground">
        {value}
      </div>
    </div>
  );
}

function SkeletonList({ rows }: { rows: number }) {
  return (
    <ul className="space-y-2.5">
      {Array.from({ length: rows }).map((_, i) => (
        <li key={i} className="flex items-center justify-between gap-3">
          <div className="h-3 w-1/2 animate-pulse rounded bg-muted" />
          <div className="h-3 w-16 animate-pulse rounded bg-muted" />
        </li>
      ))}
    </ul>
  );
}

function EmptyLine({ text }: { text: string }) {
  return <p className="py-1 text-sm text-muted-foreground">{text}</p>;
}

function UrgencyBadge({ urgency }: { urgency: string | null | undefined }) {
  if (!urgency) return null;
  const label = humanize(urgency);
  if (urgency === "immediate") {
    return (
      <Badge variant="outline" className="border-rose-200 bg-rose-50 text-rose-700">
        {label}
      </Badge>
    );
  }
  if (urgency === "this_week") {
    return (
      <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700">
        {label}
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="font-normal">
      {label}
    </Badge>
  );
}

// ─── Derivations ───────────────────────────────────────────────────────────

function countBannedPhrases(raw: string | null | undefined): number | null {
  if (raw === null || raw === undefined) return null;
  const trimmed = raw.trim();
  if (!trimmed) return 0;
  // Banned phrases are stored as comma- or newline-separated text in
  // the onboarding payload. Count distinct non-empty entries.
  return trimmed
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter(Boolean).length;
}

function deriveAttentionItems(
  profile: OnboardingProfilePayload | null,
): AttentionItem[] {
  if (!profile) return [];
  const items: AttentionItem[] = [];
  if (!profile.banned_phrases?.trim()) {
    items.push({ id: "banned", text: "Banned phrases not configured." });
  }
  if (!profile.salespeople_added) {
    items.push({ id: "team", text: "Sales team not added yet." });
  }
  if (!profile.payment_disclaimer?.trim()) {
    items.push({ id: "disclaimer", text: "Payment disclaimer not set." });
  }
  if (!profile.inventory_connected) {
    items.push({ id: "inventory", text: "Inventory feed not connected." });
  }
  if (!profile.finance_rules_reviewed) {
    items.push({ id: "finance", text: "Finance rules not reviewed." });
  }
  if (!profile.demo_prompts_tested) {
    items.push({ id: "demo", text: "Demo prompts not tested." });
  }
  if (!profile.pilot_approved) {
    items.push({ id: "pilot", text: "Pilot review pending." });
  }
  return items.slice(0, 4); // keep the card scannable
}

function leadSummaryLine(lead: AdminLead): string {
  const parts: string[] = [];
  if (lead.target_monthly_payment) {
    parts.push(`~$${lead.target_monthly_payment}/mo`);
  }
  if (lead.interested_vehicles && lead.interested_vehicles.length > 0) {
    const first = lead.interested_vehicles[0];
    if (first?.display_name) parts.push(first.display_name);
  } else if (lead.conversation_summary) {
    parts.push(lead.conversation_summary.slice(0, 60));
  }
  return parts.length ? parts.join(" · ") : "No details captured yet.";
}

// ─── Formatters ────────────────────────────────────────────────────────────

function humanize(token: string): string {
  return token
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\w/, (c) => c.toUpperCase());
}

function humanizeFlag(flag: string, category: string): string {
  const flagText = humanize(flag);
  const categoryText = humanize(category);
  if (flagText.toLowerCase() === categoryText.toLowerCase()) return flagText;
  return `${flagText} (${categoryText})`;
}

function formatCount(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString();
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatClock(d: Date): string {
  return d.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatRelative(iso: string | null | undefined): string {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "—";
  const diffMs = Date.now() - t;
  const sec = Math.max(0, Math.round(diffMs / 1000));
  if (sec < 45) return "just now";
  const min = Math.round(sec / 60);
  if (min < 60) return `${min} min ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr} hr ago`;
  const day = Math.round(hr / 24);
  if (day < 7) return `${day} day${day === 1 ? "" : "s"} ago`;
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}
