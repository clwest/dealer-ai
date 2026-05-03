// SESSION_025 — read-only Leads pipeline.
//
// Uses existing admin lead/detail endpoints only. No reassignment,
// handoff toggles, notes, or CRM actions live here; this page is a
// triage and context surface for managers to decide who needs attention.

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  Bot,
  CalendarClock,
  CarFront,
  CheckCircle2,
  Clock3,
  Inbox,
  Mail,
  Phone,
  Search,
  UserRound,
  Users,
} from "lucide-react";
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
import { Input } from "@/components/ui/input";
import {
  fetchAdminLeads,
  fetchLeadDetail,
  type AdminLead,
  type ChatMessage,
  type LeadDetailResponse,
  type Vehicle,
} from "@/lib/api";
import { useBrand } from "@/lib/brand";
import { cn, formatCurrency } from "@/lib/utils";

type UrgencyFilter = "all" | "immediate" | "this_week" | "this_month" | "researching";
type StatusFilter = "all" | "new" | "handed_off" | "assigned" | "unassigned";

const URGENCY_OPTIONS: { value: UrgencyFilter; label: string }[] = [
  { value: "all", label: "All urgency" },
  { value: "immediate", label: "Immediate" },
  { value: "this_week", label: "This week" },
  { value: "this_month", label: "This month" },
  { value: "researching", label: "Researching" },
];

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All status" },
  { value: "new", label: "New" },
  { value: "handed_off", label: "Handed off" },
  { value: "assigned", label: "Assigned" },
  { value: "unassigned", label: "Unassigned" },
];

const URGENCY_STYLES: Record<string, string> = {
  immediate: "border-rose-200 bg-rose-50 text-rose-700",
  this_week: "border-amber-200 bg-amber-50 text-amber-700",
  this_month: "border-sky-200 bg-sky-50 text-sky-700",
  researching: "border-slate-200 bg-slate-50 text-slate-700",
};

export default function LeadsPage() {
  const brand = useBrand();
  const [leads, setLeads] = useState<AdminLead[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<LeadDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [urgency, setUrgency] = useState<UrgencyFilter>("all");
  const [status, setStatus] = useState<StatusFilter>("all");

  useEffect(() => {
    let cancelled = false;
    setLoaded(false);
    setError(null);
    fetchAdminLeads({ limit: 100, ordering: "urgency" })
      .then((res) => {
        if (cancelled) return;
        setLeads(res.results);
        setSelectedId((current) => current ?? res.results[0]?.id ?? null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load leads.");
        setLeads([]);
      })
      .finally(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (selectedId == null) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);
    fetchLeadDetail(selectedId)
      .then((payload) => {
        if (!cancelled) setDetail(payload);
      })
      .catch((err) => {
        if (cancelled) return;
        setDetailError(
          err instanceof Error ? err.message : "Failed to load lead detail.",
        );
        setDetail(null);
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const filteredLeads = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return leads.filter((lead) => {
      if (urgency !== "all" && lead.urgency !== urgency) return false;
      if (status === "new" && lead.handed_off) return false;
      if (status === "handed_off" && !lead.handed_off) return false;
      if (status === "assigned" && !lead.assigned_to) return false;
      if (status === "unassigned" && lead.assigned_to) return false;
      if (!needle) return true;
      return [
        lead.name,
        lead.email,
        lead.phone,
        lead.trade_in,
        lead.conversation_summary,
        lead.recommended_next_action,
        lead.assigned_to?.name,
        ...lead.interested_vehicles.map((v) => v.display_name),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(needle);
    });
  }, [leads, query, status, urgency]);

  const selectedLead =
    leads.find((lead) => lead.id === selectedId) ?? filteredLeads[0] ?? null;

  useEffect(() => {
    if (!loaded) return;
    if (filteredLeads.length === 0) {
      setSelectedId(null);
      return;
    }
    if (!filteredLeads.some((lead) => lead.id === selectedId)) {
      setSelectedId(filteredLeads[0].id);
    }
  }, [filteredLeads, loaded, selectedId]);

  const stats = useMemo(() => buildStats(leads), [leads]);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Leads
          </h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Read-only pipeline for assistant-sourced shoppers at{" "}
            {brand.dealershipName}. Filter the list, open a lead, and review the
            context before a salesperson follows up.
          </p>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link to="/dealer-ai-overview">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Overview
          </Link>
        </Button>
      </header>

      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard icon={Users} label="Loaded leads" value={leads.length} />
        <MetricCard icon={AlertCircle} label="Immediate" value={stats.immediate} />
        <MetricCard icon={UserRound} label="Assigned" value={stats.assigned} />
        <MetricCard icon={CheckCircle2} label="Handed off" value={stats.handedOff} />
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>Lead pipeline</CardTitle>
              <CardDescription>
                Client-side filters over the current admin lead page.
              </CardDescription>
            </div>
            <Badge variant="outline" className="font-normal">
              Read-only
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 lg:grid-cols-[minmax(220px,1fr)_auto_auto]">
            <div className="relative min-w-0">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-8"
                placeholder="Search name, phone, email, vehicle, notes..."
              />
            </div>
            <SegmentedControl
              label="Urgency"
              options={URGENCY_OPTIONS}
              value={urgency}
              onChange={setUrgency}
            />
            <SegmentedControl
              label="Status"
              options={STATUS_OPTIONS}
              value={status}
              onChange={setStatus}
            />
          </div>

          {error ? (
            <InlineState icon={AlertCircle} text={error} />
          ) : !loaded ? (
            <InlineState icon={Clock3} text="Loading leads..." />
          ) : leads.length === 0 ? (
            <EmptyState />
          ) : filteredLeads.length === 0 ? (
            <InlineState
              icon={Search}
              text="No leads match the current filters."
            />
          ) : (
            <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(320px,0.85fr)_minmax(0,1.15fr)]">
              <LeadList
                leads={filteredLeads}
                selectedId={selectedLead?.id ?? null}
                onSelect={setSelectedId}
              />
              <LeadDetailPanel
                lead={selectedLead}
                detail={detail}
                loading={detailLoading}
                error={detailError}
              />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Users;
  label: string;
  value: number;
}) {
  return (
    <Card size="sm">
      <CardContent className="flex items-center justify-between gap-3 p-4">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </div>
          <div className="mt-1 text-2xl font-semibold text-foreground">
            {value}
          </div>
        </div>
        <Icon className="h-5 w-5 text-primary" aria-hidden />
      </CardContent>
    </Card>
  );
}

function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="min-w-0">
      <div className="sr-only">{label}</div>
      <div className="flex max-w-full gap-1 overflow-x-auto rounded-lg bg-muted p-1">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={cn(
              "h-7 shrink-0 rounded-md px-2.5 text-xs font-medium transition",
              value === option.value
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function LeadList({
  leads,
  selectedId,
  onSelect,
}: {
  leads: AdminLead[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  return (
    <div className="min-w-0 overflow-hidden rounded-lg border border-border">
      <div className="flex items-center justify-between border-b border-border bg-muted/40 px-3 py-2">
        <div className="text-sm font-medium text-foreground">Lead queue</div>
        <div className="text-xs text-muted-foreground">
          {leads.length} shown
        </div>
      </div>
      <div className="overflow-y-auto xl:max-h-[720px]">
        {leads.map((lead) => (
          <button
            key={lead.id}
            type="button"
            onClick={() => onSelect(lead.id)}
            className={cn(
              "block w-full border-b border-border px-3 py-3 text-left last:border-b-0 transition hover:bg-muted/50",
              selectedId === lead.id && "bg-primary/5 ring-1 ring-inset ring-primary/30",
            )}
          >
            <div className="flex min-w-0 items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-foreground">
                  {lead.name?.trim() || "Unnamed lead"}
                </div>
                <div className="mt-0.5 truncate text-xs text-muted-foreground">
                  {leadSummaryLine(lead)}
                </div>
              </div>
              <UrgencyBadge urgency={lead.urgency} />
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <StatusBadge lead={lead} />
              {lead.assigned_to ? (
                <Badge variant="outline" className="font-normal">
                  {lead.assigned_to.name}
                </Badge>
              ) : (
                <Badge variant="secondary" className="font-normal">
                  Unassigned
                </Badge>
              )}
              {lead.interested_vehicles.length > 0 ? (
                <Badge variant="outline" className="font-normal">
                  {lead.interested_vehicles.length} vehicle
                  {lead.interested_vehicles.length === 1 ? "" : "s"}
                </Badge>
              ) : null}
            </div>
            <div className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
              {lead.recommended_next_action ||
                lead.conversation_summary ||
                "No summary captured yet."}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function LeadDetailPanel({
  lead,
  detail,
  loading,
  error,
}: {
  lead: AdminLead | null;
  detail: LeadDetailResponse | null;
  loading: boolean;
  error: string | null;
}) {
  if (!lead) {
    return <InlineState icon={Inbox} text="Select a lead to review context." />;
  }

  const profileEntries = Object.entries(detail?.session_profile ?? {}).filter(
    ([, value]) => value !== null && value !== "" && value !== undefined,
  );
  const messages = detail?.messages.filter((m) => m.role !== "system") ?? [];
  const vehicles = detail?.interested_vehicles ?? [];

  return (
    <div className="min-w-0 overflow-hidden rounded-lg border border-border bg-background">
      <div className="border-b border-border p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="truncate text-lg font-semibold text-foreground">
              {lead.name?.trim() || "Unnamed lead"}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <ContactPiece icon={Phone} text={lead.phone} fallback="No phone" />
              <ContactPiece icon={Mail} text={lead.email} fallback="No email" />
              <ContactPiece
                icon={CalendarClock}
                text={formatDateTime(lead.created_at)}
              />
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <UrgencyBadge urgency={lead.urgency} />
            <StatusBadge lead={lead} />
          </div>
        </div>
      </div>

      <div className="space-y-4 overflow-y-auto p-4 xl:max-h-[720px]">
        {error ? (
          <InlineState icon={AlertCircle} text={error} />
        ) : loading ? (
          <InlineState icon={Clock3} text="Loading lead context..." />
        ) : null}

        <section className="grid gap-3 md:grid-cols-2">
          <InfoTile label="Target payment" value={moneyPerMonth(lead.target_monthly_payment)} />
          <InfoTile label="Down payment" value={formatCurrency(lead.down_payment)} />
          <InfoTile label="Credit range" value={humanize(lead.credit_range)} />
          <InfoTile label="Assigned to" value={lead.assigned_to?.name ?? "Unassigned"} />
        </section>

        {lead.trade_in ? (
          <Section title="Trade-in">
            <p className="text-sm leading-relaxed text-foreground">
              {lead.trade_in}
            </p>
          </Section>
        ) : null}

        <Section title="Recommended next action">
          <p className="text-sm leading-relaxed text-foreground">
            {lead.recommended_next_action ||
              "No recommended next action captured yet."}
          </p>
        </Section>

        <Section title="Conversation summary">
          <p className="text-sm leading-relaxed text-foreground">
            {lead.conversation_summary || "No conversation summary captured yet."}
          </p>
        </Section>

        <Section title="Shopper profile">
          {profileEntries.length > 0 ? (
            <div className="grid gap-2 sm:grid-cols-2">
              {profileEntries.map(([key, value]) => (
                <InfoTile
                  key={key}
                  label={humanize(key)}
                  value={formatProfileValue(value)}
                />
              ))}
            </div>
          ) : (
            <EmptyText text="No extracted profile fields on this session." />
          )}
        </Section>

        <Section title="Interested vehicles">
          {vehicles.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2">
              {vehicles.map((vehicle) => (
                <VehicleTile key={vehicle.id} vehicle={vehicle} />
              ))}
            </div>
          ) : lead.interested_vehicles.length > 0 ? (
            <div className="grid gap-2 sm:grid-cols-2">
              {lead.interested_vehicles.map((vehicle) => (
                <VehicleSummaryTile key={vehicle.id} vehicle={vehicle} />
              ))}
            </div>
          ) : (
            <EmptyText text="No interested vehicles attached yet." />
          )}
        </Section>

        <Section title="Transcript">
          {messages.length > 0 ? (
            <div className="space-y-2">
              {messages.map((message) => (
                <TranscriptBubble key={message.id} message={message} />
              ))}
            </div>
          ) : (
            <EmptyText text="No transcript is attached to this lead." />
          )}
        </Section>
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border p-3">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h2>
      {children}
    </section>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-3">
      <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 break-words text-sm font-semibold text-foreground">
        {value || "Not captured"}
      </div>
    </div>
  );
}

function VehicleTile({ vehicle }: { vehicle: Vehicle }) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      <div className="aspect-[16/9] bg-muted">
        {vehicle.image_url ? (
          <img
            src={vehicle.image_url}
            alt={vehicle.display_name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <CarFront className="h-6 w-6" aria-hidden />
          </div>
        )}
      </div>
      <div className="space-y-2 p-3">
        <div>
          <div className="text-sm font-semibold leading-tight text-foreground">
            {vehicle.display_name}
          </div>
          <div className="text-xs text-muted-foreground">
            Stock #{vehicle.stock_number}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span className="text-base font-bold text-primary">
            {formatCurrency(vehicle.price)}
          </span>
          <span>{vehicle.drivetrain}</span>
          <span>{vehicle.mileage ? `${vehicle.mileage.toLocaleString()} mi` : "New"}</span>
        </div>
      </div>
    </div>
  );
}

function VehicleSummaryTile({
  vehicle,
}: {
  vehicle: AdminLead["interested_vehicles"][number];
}) {
  return (
    <div className="rounded-lg border border-border p-3">
      <div className="text-sm font-semibold text-foreground">
        {vehicle.display_name}
      </div>
      <div className="text-xs text-muted-foreground">
        Stock #{vehicle.stock_number} · {formatCurrency(vehicle.price)}
      </div>
    </div>
  );
}

function TranscriptBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[86%] rounded-lg px-3 py-2 text-sm leading-relaxed",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground",
        )}
      >
        <div className="mb-1 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide opacity-70">
          {isUser ? <UserRound className="h-3 w-3" /> : <Bot className="h-3 w-3" />}
          {message.role}
        </div>
        <div className="whitespace-pre-wrap">{message.content}</div>
      </div>
    </div>
  );
}

function ContactPiece({
  icon: Icon,
  text,
  fallback,
}: {
  icon: typeof Phone;
  text?: string | null;
  fallback?: string;
}) {
  return (
    <span className="inline-flex min-w-0 items-center gap-1">
      <Icon className="h-3.5 w-3.5 shrink-0" />
      <span className="truncate">{text || fallback || ""}</span>
    </span>
  );
}

function UrgencyBadge({ urgency }: { urgency: string }) {
  if (!urgency) return null;
  return (
    <Badge
      variant="outline"
      className={cn("font-normal", URGENCY_STYLES[urgency])}
    >
      {humanize(urgency)}
    </Badge>
  );
}

function StatusBadge({ lead }: { lead: AdminLead }) {
  return lead.handed_off ? (
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
  );
}

function InlineState({
  icon: Icon,
  text,
}: {
  icon: typeof Inbox;
  text: string;
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/20 px-3 py-2 text-sm text-muted-foreground">
      <Icon className="h-4 w-4 shrink-0" aria-hidden />
      <span>{text}</span>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-2 py-8 text-center">
      <Inbox className="h-6 w-6 text-muted-foreground" aria-hidden />
      <p className="text-sm text-muted-foreground">
        No leads yet. They'll appear here as conversations qualify.
      </p>
    </div>
  );
}

function EmptyText({ text }: { text: string }) {
  return <p className="text-sm text-muted-foreground">{text}</p>;
}

function buildStats(leads: AdminLead[]) {
  return {
    immediate: leads.filter((lead) => lead.urgency === "immediate").length,
    assigned: leads.filter((lead) => lead.assigned_to).length,
    handedOff: leads.filter((lead) => lead.handed_off).length,
  };
}

function leadSummaryLine(lead: AdminLead): string {
  return (
    [
      lead.phone || null,
      lead.email || null,
      moneyPerMonth(lead.target_monthly_payment) || null,
      lead.interested_vehicles[0]?.display_name || null,
    ]
      .filter(Boolean)
      .join(" · ") || "No contact captured."
  );
}

function moneyPerMonth(value: string | number | null | undefined): string {
  const formatted = formatCurrency(value);
  return formatted ? `${formatted}/mo` : "";
}

function formatDateTime(value: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function formatProfileValue(value: unknown): string {
  if (Array.isArray(value)) return value.map(formatProfileValue).join(", ");
  if (typeof value === "object" && value !== null) {
    return Object.entries(value)
      .map(([key, nested]) => `${humanize(key)}: ${formatProfileValue(nested)}`)
      .join(" · ");
  }
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function humanize(token: string | null | undefined): string {
  if (!token) return "";
  return token
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\w/, (c) => c.toUpperCase());
}
