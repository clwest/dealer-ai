// Milestone 11 · Increment 6 (SESSION_119) — sales-side channel-filtered leads.
//
// Consumes GET /admin/leads/ with the M11.6 channel filter added on
// top of the existing handed_off / urgency / since / ordering
// filters. Rendered as a filterable table.
//
// Role gating: backend enforces IsSalesManagerOrOwnerAtActiveDealership.
// Advisors / other roles receive 403 and the page renders the error.

import { useCallback, useEffect, useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { fetchAdminLeads, type AdminLead } from "@/lib/api";

type ChannelFilter =
  | ""
  | "chat"
  | "walk_in"
  | "phone"
  | "listing_form"
  | "referral"
  | "other";

const CHANNEL_OPTIONS: Array<{ value: ChannelFilter; label: string }> = [
  { value: "", label: "Any channel" },
  { value: "chat", label: "Chat" },
  { value: "walk_in", label: "Walk-in" },
  { value: "phone", label: "Phone" },
  { value: "listing_form", label: "Listing form" },
  { value: "referral", label: "Referral" },
  { value: "other", label: "Other" },
];

export default function DealerAiSalesLeads() {
  const [leads, setLeads] = useState<AdminLead[]>([]);
  const [channel, setChannel] = useState<ChannelFilter>("");
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadState("loading");
    setErrorMessage(null);
    try {
      const res = await fetchAdminLeads({
        limit: 100,
        ordering: "urgency",
        channel: channel ? [channel] : undefined,
      });
      setLeads(res.results);
      setLoadState("ready");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to load leads.",
      );
      setLoadState("error");
    }
  }, [channel]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Sales leads</h1>
        <p className="text-sm text-muted-foreground">
          Every lead across every intake channel. Filter by channel to
          narrow the queue.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filter</CardTitle>
          <CardDescription>Channel</CardDescription>
        </CardHeader>
        <CardContent>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-muted-foreground">
              Intake channel
            </span>
            <select
              aria-label="Channel filter"
              value={channel}
              onChange={(e) => setChannel(e.target.value as ChannelFilter)}
              className="rounded border border-input bg-background px-3 py-2"
            >
              {CHANNEL_OPTIONS.map((opt) => (
                <option key={opt.value || "any"} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        </CardContent>
      </Card>

      {loadState === "loading" && (
        <p className="text-muted-foreground">Loading leads…</p>
      )}
      {loadState === "error" && (
        <p role="alert" className="text-destructive">
          {errorMessage}
        </p>
      )}
      {loadState === "ready" && leads.length === 0 && (
        <Card>
          <CardContent className="py-6 text-center text-muted-foreground">
            No leads match the current filter.
          </CardContent>
        </Card>
      )}
      {loadState === "ready" && leads.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{leads.length} leads</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2">Name</th>
                  <th className="pb-2">Phone</th>
                  <th className="pb-2">Channel</th>
                  <th className="pb-2">Urgency</th>
                  <th className="pb-2">Handed off</th>
                  <th className="pb-2">Created</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr key={lead.id} className="border-b last:border-0">
                    <td className="py-2">{lead.name}</td>
                    <td className="py-2">{lead.phone || "—"}</td>
                    <td className="py-2">{lead.channel ?? "chat"}</td>
                    <td className="py-2">{lead.urgency || "—"}</td>
                    <td className="py-2">{lead.handed_off ? "Yes" : "No"}</td>
                    <td className="py-2 text-muted-foreground">
                      {new Date(lead.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
