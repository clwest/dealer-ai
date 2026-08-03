// Milestone 11 · Increment 6 (SESSION_119) — sales-side channel-filtered leads.
// Milestone 24 · Increment 1 (SESSION_181) — Walk-in intake CTA + Dialog +
//   LeadDetailModal wire-in on the sales-side leads page.
// Milestone 24 · Increment 2 (SESSION_182) — Phone intake CTA + Dialog
//   (sibling to walk-in; reuses `<LeadIntakeForm>` unchanged).
//
// Consumes GET /admin/leads/ with the M11.6 channel filter added on
// top of the existing handed_off / urgency / since / ordering
// filters. Rendered as a filterable table.
//
// M24.1 additions (per MILESTONE_24_PLANNING.md §5.b + §5.d, revised
// at SESSION_181 M24.1 open):
// - `+ Walk-in` Dialog CTA in the page header opens a shared
//   `<LeadIntakeForm channel="walk_in">` (posts via `createWalkInLead`).
//   On success the intake Dialog closes, the leads list refetches,
//   and the newly created lead's `LeadDetailModal` opens on the same
//   page (no redirect; the sales-side `/dealer-ai-sales/leads` route
//   is the list view — there is no dedicated detail route today).
// - Row click opens `LeadDetailModal` for any lead in the list.
// - `AssignmentDropdown` reaches via the modal header (unchanged).
//
// M24.2 additions (SESSION_182): `+ Phone` Dialog CTA follows the
// exact walk-in shape — same shared `<LeadIntakeForm>` component
// with `channel="phone"` and `createPhoneLead` as the dispatcher.
// The phone journey adds a downstream cadence step (navigate to
// /dealer-ai-sales/follow-ups + use existing CadenceConfigPanel to
// start a 24hr cadence for the new lead's ID) per §5.d Option C
// phone row.
//
// Referral CTA lands at M24.3 (adds `<ReferralLeadFormExtras>` in
// the shared form's extras slot).
//
// Role gating: backend enforces IsSalesManagerOrOwnerAtActiveDealership.
// Advisors / other roles receive 403 and the page renders the error.

import { useCallback, useEffect, useState } from "react";

import LeadDetailModal from "@/components/LeadDetailModal";
import { LeadIntakeForm } from "@/components/sales/LeadIntakeForm";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { fetchAdminLeads, type AdminLead } from "@/lib/api";
import { createPhoneLead, createWalkInLead } from "@/lib/salesApi";

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
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [walkInDialogOpen, setWalkInDialogOpen] = useState(false);
  const [phoneDialogOpen, setPhoneDialogOpen] = useState(false);

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
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Sales leads</h1>
          <p className="text-sm text-muted-foreground">
            Every lead across every intake channel. Filter by channel to
            narrow the queue.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => setWalkInDialogOpen(true)}
            data-testid="sales-leads-add-walk-in"
          >
            + Walk-in
          </Button>
          <Button
            onClick={() => setPhoneDialogOpen(true)}
            data-testid="sales-leads-add-phone"
          >
            + Phone
          </Button>
        </div>
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
                  <tr
                    key={lead.id}
                    className="cursor-pointer border-b last:border-0 hover:bg-muted/40"
                    onClick={() => setSelectedLeadId(lead.id)}
                    data-testid={`sales-leads-row-${lead.id}`}
                  >
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

      <Dialog open={walkInDialogOpen} onOpenChange={setWalkInDialogOpen}>
        <DialogContent data-testid="sales-leads-walk-in-dialog">
          <DialogHeader>
            <DialogTitle>Record a walk-in lead</DialogTitle>
            <DialogDescription>
              Capture the essentials while the customer is on the lot.
              After you record the lead, the detail view opens so you
              can assign and continue immediately.
            </DialogDescription>
          </DialogHeader>
          <LeadIntakeForm
            channel="walk_in"
            onSubmit={createWalkInLead}
            onCreated={(lead) => {
              setWalkInDialogOpen(false);
              setSelectedLeadId(lead.id);
              void load();
            }}
          />
        </DialogContent>
      </Dialog>

      <Dialog open={phoneDialogOpen} onOpenChange={setPhoneDialogOpen}>
        <DialogContent data-testid="sales-leads-phone-dialog">
          <DialogHeader>
            <DialogTitle>Record a phone lead</DialogTitle>
            <DialogDescription>
              Capture the essentials while the customer is on the
              phone. After you record the lead, the detail view opens
              so you can assign and start a follow-up cadence from
              the follow-up work-queue.
            </DialogDescription>
          </DialogHeader>
          <LeadIntakeForm
            channel="phone"
            onSubmit={createPhoneLead}
            onCreated={(lead) => {
              setPhoneDialogOpen(false);
              setSelectedLeadId(lead.id);
              void load();
            }}
          />
        </DialogContent>
      </Dialog>

      <LeadDetailModal
        leadId={selectedLeadId}
        onClose={() => setSelectedLeadId(null)}
        onHandoffComplete={() => void load()}
      />
    </div>
  );
}
