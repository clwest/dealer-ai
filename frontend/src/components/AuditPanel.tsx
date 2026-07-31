// Manager Phase 1: AI safety / guard events panel.
//
// Surfaces the Phase 8m–8r guard activity (rate_inquiry,
// negotiation_request, post_llm_safety_rewrite, etc.) aggregated from
// ChatMessage.metadata.flag over a 24h / 7d / 30d window.
//
// Click a flag bucket → drilldown modal showing recent matching events
// with user/assistant excerpts. No new API call on drilldown — the
// snapshot endpoint returns recent_events[:50] which we filter
// client-side.

import { useEffect, useMemo, useState } from "react";
import { Shield, ShieldAlert, ShieldCheck, ShieldX, X } from "lucide-react";

import StatCard from "@/components/StatCard";
import { fetchAuditEvents } from "@/lib/api";
import type {
  AuditEvent,
  AuditEventsResponse,
  AuditFlagBucket,
  AuditSeverity,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type Window = "24h" | "7d" | "30d";

const WINDOW_LABELS: Record<Window, string> = {
  "24h": "Last 24h",
  "7d": "Last 7d",
  "30d": "Last 30d",
};

const FLAG_DISPLAY_NAMES: Record<string, string> = {
  prompt_injection: "Prompt injection attempt",
  rate_inquiry: "Rate / APR question",
  external_value_inquiry: "Blue Book / KBB / trade-in value",
  identity_request: "Identity question (are you real?)",
  negotiation_request: "Price negotiation",
  handoff_request: "Live agent / handoff request",
  image_request: "Picture / image request",
  image_request_needs_vehicle: "Image request (no vehicle context)",
  appointment_request: "Appointment / test drive",
  appointment_request_needs_vehicle: "Appointment (no vehicle context)",
  post_llm_safety_rewrite: "Post-LLM safety rewrite",
  internal_confusion_fallback: "Internal-confusion fallback",
  post_llm_override: "Post-LLM override",
  rate_language_scrubbed: "Rate language scrubbed",
  internal_directive_scrubbed: "Internal directive scrubbed",
  default_assumption_scrubbed: "Default-assumption scrubbed",
  category_label_scrubbed: "Category label scrubbed",
  multiple_scrubs_fired: "Multiple scrubs fired",
};

const CATEGORY_LABELS: Record<string, string> = {
  pre_llm_guard: "Pre-LLM guard",
  post_llm_rewrite: "Post-LLM rewrite",
  post_llm_override: "Post-LLM override",
  scrub: "Partial scrub",
  unknown: "Other",
};

function severityRowClasses(sev: AuditSeverity): string {
  switch (sev) {
    case "warn":
      return "border-amber-200 bg-amber-50 hover:bg-amber-100";
    case "info":
      return "border-blue-100 bg-white hover:bg-blue-50";
    case "muted":
    default:
      return "border-slate-100 bg-white hover:bg-slate-50";
  }
}

function flagDisplay(flag: string): string {
  return FLAG_DISPLAY_NAMES[flag] ?? flag.replace(/_/g, " ");
}

function timeShort(iso: string) {
  const then = new Date(iso).getTime();
  const diffMin = (Date.now() - then) / 60000;
  if (diffMin < 60) return `${Math.round(diffMin)}m ago`;
  const diffHr = diffMin / 60;
  if (diffHr < 24) return `${Math.round(diffHr)}h ago`;
  return `${Math.round(diffHr / 24)}d ago`;
}

interface DrilldownState {
  flag: string;
  events: AuditEvent[];
  // Total count from the bucket aggregate. When events.length is 0 but
  // bucketTotalCount > 0, the matching events are outside the
  // recent-events sample window — show a different fallback so the
  // user understands the count is real but the samples aren't loaded.
  bucketTotalCount: number;
}

interface Props {
  refreshKey: number;
}

export default function AuditPanel({ refreshKey }: Props) {
  const [window, setWindow] = useState<Window>("24h");
  const [data, setData] = useState<AuditEventsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drilldown, setDrilldown] = useState<DrilldownState | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchAuditEvents({ since: window })
      .then((res) => {
        if (cancelled) return;
        if (!res || !res.totals || !Array.isArray(res.by_flag)) {
          console.error(
            "AuditPanel: fetchAuditEvents returned unexpected payload shape",
            { window, payload: res },
          );
        }
        setData(res);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("AuditPanel: fetchAuditEvents failed", { window, err });
        setError(err instanceof Error ? err.message : "Load failed.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [window, refreshKey]);

  const grouped = useMemo(() => {
    if (!data) return new Map<string, AuditFlagBucket[]>();
    const m = new Map<string, AuditFlagBucket[]>();
    for (const b of data.by_flag) {
      const key = b.category;
      if (!m.has(key)) m.set(key, []);
      m.get(key)!.push(b);
    }
    return m;
  }, [data]);

  const openDrilldown = (flag: string) => {
    if (!data) {
      console.error("AuditPanel.openDrilldown called with no data loaded", {
        flag,
      });
      return;
    }
    if (!Array.isArray(data.recent_events)) {
      console.error(
        "AuditPanel.openDrilldown: data.recent_events is not an array",
        { flag, recentEvents: data.recent_events },
      );
      setDrilldown({ flag, events: [], bucketTotalCount: 0 });
      return;
    }
    const events = data.recent_events.filter((e) => e.flag === flag);
    const bucket = data.by_flag.find((b) => b.flag === flag);
    const bucketTotalCount = bucket?.count ?? events.length;
    if (bucketTotalCount > 0 && events.length === 0) {
      console.error(
        "AuditPanel.openDrilldown: bucket has count > 0 but no recent_events match — likely outside the recent-events sample",
        {
          flag,
          bucketTotalCount,
          totalRecentEvents: data.recent_events.length,
        },
      );
    }
    setDrilldown({ flag, events, bucketTotalCount });
  };

  return (
    <section className="card p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-blue-50 text-blue-600">
            <Shield className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-brand-ink">
              AI safety &amp; guard events
            </h2>
            <div className="text-xs text-slate-500">
              {WINDOW_LABELS[window]}
              {loading ? " · loading…" : ""}
            </div>
          </div>
        </div>
        <div className="flex gap-1">
          {(Object.keys(WINDOW_LABELS) as Window[]).map((w) => (
            <button
              key={w}
              type="button"
              onClick={() => setWindow(w)}
              className={cn(
                "rounded-md border px-2.5 py-1 text-xs font-medium transition",
                window === w
                  ? "border-brand-blue bg-brand-blue text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50",
              )}
            >
              {WINDOW_LABELS[w]}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mb-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="Pre-LLM guards"
          value={data?.totals.pre_llm_short_circuits ?? 0}
          hint="Refused before LLM call"
          icon={<ShieldCheck className="h-4 w-4" />}
        />
        <StatCard
          label="Post-LLM rewrites"
          value={data?.totals.post_llm_rewrites ?? 0}
          hint="Wholesale safety replacements"
          tone={(data?.totals.post_llm_rewrites ?? 0) > 0 ? "warn" : "default"}
          icon={<ShieldAlert className="h-4 w-4" />}
        />
        <StatCard
          label="Post-LLM overrides"
          value={data?.totals.post_llm_overrides ?? 0}
          hint="Negotiation / fake-transfer leaks"
          tone={
            (data?.totals.post_llm_overrides ?? 0) > 0 ? "warn" : "default"
          }
          icon={<ShieldX className="h-4 w-4" />}
        />
        <StatCard
          label="Scrubs fired"
          value={data?.totals.scrubs_fired ?? 0}
          hint="Partial directive / category fixes"
          icon={<Shield className="h-4 w-4" />}
        />
      </div>

      {data && data.by_flag.length === 0 && !loading && (
        <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-4 text-center text-sm text-slate-500">
          No guard events in this window.
        </div>
      )}

      {data && data.by_flag.length > 0 && (
        <div className="mt-4 space-y-3">
          {Array.from(grouped.entries()).map(([category, buckets]) => (
            <div key={category}>
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                {CATEGORY_LABELS[category] ?? category}
              </div>
              <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                {buckets.map((b) => (
                  <button
                    key={b.flag}
                    type="button"
                    onClick={() => openDrilldown(b.flag)}
                    className={cn(
                      "flex items-center justify-between rounded-md border px-3 py-2 text-left text-sm transition",
                      severityRowClasses(b.severity),
                    )}
                  >
                    <span className="text-slate-700">
                      {flagDisplay(b.flag)}
                    </span>
                    <span className="rounded-md bg-white px-2 py-0.5 text-xs font-bold text-slate-700 ring-1 ring-slate-200">
                      {b.count}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {drilldown && (
        <AuditDrilldownModal
          drilldown={drilldown}
          onClose={() => setDrilldown(null)}
        />
      )}
    </section>
  );
}

function AuditDrilldownModal({
  drilldown,
  onClose,
}: {
  drilldown: DrilldownState;
  onClose: () => void;
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-2xl bg-white p-0"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <div>
            <h3 className="text-sm font-bold text-brand-ink">
              {flagDisplay(drilldown.flag)}
            </h3>
            <div className="text-xs text-slate-500">
              {drilldown.events.length} recent event
              {drilldown.events.length === 1 ? "" : "s"}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="max-h-[60vh] overflow-y-auto p-5">
          {drilldown.events.length === 0 ? (
            drilldown.bucketTotalCount > 0 ? (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                <div className="font-semibold">
                  {drilldown.bucketTotalCount} event
                  {drilldown.bucketTotalCount === 1 ? "" : "s"} fired in this
                  window — but their excerpts are outside the most-recent
                  sample.
                </div>
                <div className="mt-2 text-xs text-amber-700">
                  The audit endpoint returns up to 50 recent excerpts per
                  request. Try a narrower time window (24h) or refresh —
                  newer events should surface in the sample.
                </div>
              </div>
            ) : (
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
                No recent matching events in this window.
              </div>
            )
          ) : (
            <ul className="space-y-4">
              {drilldown.events.map((e) => (
                <li
                  key={e.message_id}
                  className="rounded-md border border-slate-200 bg-slate-50 p-3"
                >
                  <div className="mb-1 flex items-center justify-between text-[11px] text-slate-500">
                    <span>{timeShort(e.created_at)}</span>
                    {e.override_kind ? (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 font-semibold text-amber-700">
                        override: {e.override_kind}
                      </span>
                    ) : null}
                  </div>
                  {e.user_message_excerpt ? (
                    <div className="mb-2">
                      <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                        Customer asked
                      </div>
                      <div className="text-sm text-slate-800">
                        “{e.user_message_excerpt}”
                      </div>
                    </div>
                  ) : null}
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                      AI replied
                    </div>
                    <div className="text-sm text-slate-700">
                      {e.assistant_excerpt}
                    </div>
                  </div>
                  {e.scrubs.length > 0 ? (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {e.scrubs.map((s) => (
                        <span
                          key={s}
                          className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] text-slate-700"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
