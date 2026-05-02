// SESSION_012 — Dealer OS overview page.
//
// Read-only landing surface. Pulls tone from the onboarding profile so
// the status card feels live; everything else is static placeholder per
// the SESSION_012 spec ("mock ok"). No mutations, no chat side effects.

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Bot,
  GraduationCap,
  ListChecks,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { fetchOnboardingProfile } from "@/lib/api";

interface ActivityItem {
  id: string;
  text: string;
  meta: string;
}

const RECENT_ACTIVITY: ActivityItem[] = [
  { id: "a1", text: "Customer asked: Truck under $30k", meta: "2 min ago" },
  { id: "a2", text: "Manager tested tone: Firm", meta: "18 min ago" },
  { id: "a3", text: "Banned phrase updated", meta: "1 hr ago" },
  { id: "a4", text: "Lead handed off to sales", meta: "3 hr ago" },
];

const ATTENTION_ITEMS = [
  "No banned phrases configured",
  "Sales team incomplete",
];

export default function DealerOverviewPage() {
  const [tone, setTone] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  // Best-effort fetch — page renders fine without it.
  useEffect(() => {
    let cancelled = false;
    fetchOnboardingProfile()
      .then((profile) => {
        if (cancelled) return;
        setTone(profile.sales_tone || null);
        setUpdatedAt(profile.updated_at ?? null);
      })
      .catch(() => {
        // Profile is optional context for this page; swallow errors.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Overview
        </h1>
        <p className="text-sm text-muted-foreground">
          Your AI sales assistant at a glance.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <AssistantStatusCard tone={tone} updatedAt={updatedAt} />
        <CoachingSummaryCard />
        <RecentActivityCard items={RECENT_ACTIVITY} />
        <AttentionItemsCard items={ATTENTION_ITEMS} />
      </div>
    </div>
  );
}

function AssistantStatusCard({
  tone,
  updatedAt,
}: {
  tone: string | null;
  updatedAt: string | null;
}) {
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
        <Stat label="Last updated" value={formatTimestamp(updatedAt)} />
      </CardContent>
    </Card>
  );
}

function RecentActivityCard({ items }: { items: ActivityItem[] }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <ListChecks className="h-4 w-4 text-primary" />
          <CardTitle>Recent activity</CardTitle>
        </div>
        <CardDescription>What the assistant handled recently.</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="divide-y divide-border">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between py-2.5 text-sm"
            >
              <span className="text-foreground">{item.text}</span>
              <span className="text-xs text-muted-foreground">{item.meta}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function CoachingSummaryCard() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <GraduationCap className="h-4 w-4 text-primary" />
          <CardTitle>Coaching summary</CardTitle>
        </div>
        <CardDescription>Manager training activity, this week.</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4">
        <Stat label="Scenarios tested" value="3" />
        <Stat label="Adjustments made" value="1" />
      </CardContent>
    </Card>
  );
}

function AttentionItemsCard({ items }: { items: string[] }) {
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
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item}
              className="flex items-start gap-2 text-sm text-foreground"
            >
              <span
                aria-hidden
                className="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500"
              />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

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

function humanize(token: string): string {
  return token
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\w/, (c) => c.toUpperCase());
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
