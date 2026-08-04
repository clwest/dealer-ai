// Milestone 32 · Increment 2 (SESSION_208) — LeadWriteupsPanel tests.
//
// Covers per-lead writeup list rendering (three state variants),
// three-signal a11y (Badge + row aria-label + testids per D7),
// row-action visibility (Approve on Pending, Send-to-F&I on
// Approved, none on Handed-off), + inline "+ New writeup" form
// visibility. Confirmation-dialog copy is asserted in
// WriteupConfirmDialogs.test.tsx.

import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DealWriteupProjection } from "@/lib/salesApi";

import { LeadWriteupsPanel } from "./LeadWriteupsPanel";

function fixtureWriteup(
  overrides: Partial<DealWriteupProjection> = {},
): DealWriteupProjection {
  return {
    id: 42,
    lead_id: 100,
    vehicle_id: 200,
    dealership_id: 1,
    vehicle_price: "28500.00",
    trade_allowance: "4500.00",
    down_payment: "2000.00",
    monthly_payment_target: "450.00",
    term_months_target: 72,
    apr_target: "7.49",
    write_up_at: "2026-08-04T10:00:00Z",
    written_up_by_user_id: 5,
    sales_manager_approved_at: null,
    sales_manager_approved_by_user_id: null,
    handed_off_to_fandi_at: null,
    notes: "",
    created_at: "2026-08-04T10:00:00Z",
    updated_at: "2026-08-04T10:00:00Z",
    ...overrides,
  };
}

async function openPanel() {
  await userEvent.click(screen.getByTestId("lead-writeups-toggle"));
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("LeadWriteupsPanel — collapsible", () => {
  it("does not load writeups until the section is expanded", async () => {
    const loadWriteups = vi.fn().mockResolvedValue([]);
    render(
      <LeadWriteupsPanel
        leadId={100}
        leadName="Alice"
        suggestedVehicles={[]}
        loadWriteups={loadWriteups}
      />,
    );
    expect(loadWriteups).not.toHaveBeenCalled();
    await openPanel();
    await waitFor(() => expect(loadWriteups).toHaveBeenCalledTimes(1));
    expect(loadWriteups).toHaveBeenCalledWith({ leadId: 100 });
  });

  it("renders the empty state when the lead has no writeups", async () => {
    const loadWriteups = vi.fn().mockResolvedValue([]);
    render(
      <LeadWriteupsPanel
        leadId={100}
        leadName="Alice"
        suggestedVehicles={[]}
        loadWriteups={loadWriteups}
      />,
    );
    await openPanel();
    await waitFor(() =>
      expect(screen.getByTestId("lead-writeups-empty")).toBeInTheDocument(),
    );
  });

  it("renders the error state when the load fails", async () => {
    const loadWriteups = vi.fn().mockRejectedValue(new Error("boom"));
    render(
      <LeadWriteupsPanel
        leadId={100}
        leadName="Alice"
        suggestedVehicles={[]}
        loadWriteups={loadWriteups}
      />,
    );
    await openPanel();
    await waitFor(() =>
      expect(screen.getByTestId("lead-writeups-error")).toBeInTheDocument(),
    );
  });
});

describe("LeadWriteupsPanel — state visual signals (D7 three-signal a11y)", () => {
  it("renders Pending badge + row testid + aria-label for pending writeup", async () => {
    const loadWriteups = vi.fn().mockResolvedValue([fixtureWriteup()]);
    render(
      <LeadWriteupsPanel
        leadId={100}
        leadName="Alice"
        suggestedVehicles={[]}
        loadWriteups={loadWriteups}
      />,
    );
    await openPanel();
    const row = await screen.findByTestId("writeup-row-42");
    expect(row).toHaveAttribute(
      "aria-label",
      "Writeup #42, Alice, pending",
    );
    expect(within(row).getByTestId("writeup-row-state-pending-42")).toBeInTheDocument();
    expect(within(row).getByText("Pending")).toBeInTheDocument();
  });

  it("renders Approved badge + aria-label for approved writeup", async () => {
    const loadWriteups = vi.fn().mockResolvedValue([
      fixtureWriteup({
        sales_manager_approved_at: "2026-08-04T11:00:00Z",
        sales_manager_approved_by_user_id: 5,
      }),
    ]);
    render(
      <LeadWriteupsPanel
        leadId={100}
        leadName="Alice"
        suggestedVehicles={[]}
        loadWriteups={loadWriteups}
      />,
    );
    await openPanel();
    const row = await screen.findByTestId("writeup-row-42");
    expect(row).toHaveAttribute(
      "aria-label",
      "Writeup #42, Alice, approved",
    );
    expect(within(row).getByTestId("writeup-row-state-approved-42")).toBeInTheDocument();
  });

  it("renders Handed off badge + aria-label for handed_off writeup", async () => {
    const loadWriteups = vi.fn().mockResolvedValue([
      fixtureWriteup({
        sales_manager_approved_at: "2026-08-04T11:00:00Z",
        handed_off_to_fandi_at: "2026-08-04T12:00:00Z",
      }),
    ]);
    render(
      <LeadWriteupsPanel
        leadId={100}
        leadName="Alice"
        suggestedVehicles={[]}
        loadWriteups={loadWriteups}
      />,
    );
    await openPanel();
    const row = await screen.findByTestId("writeup-row-42");
    expect(row).toHaveAttribute(
      "aria-label",
      "Writeup #42, Alice, handed off",
    );
    expect(within(row).getByTestId("writeup-row-state-handed_off-42")).toBeInTheDocument();
  });
});

describe("LeadWriteupsPanel — row action visibility per state", () => {
  it("shows Approve trigger on pending rows only", async () => {
    const loadWriteups = vi.fn().mockResolvedValue([
      fixtureWriteup({ id: 1 }),
      fixtureWriteup({
        id: 2,
        sales_manager_approved_at: "2026-08-04T11:00:00Z",
      }),
      fixtureWriteup({
        id: 3,
        sales_manager_approved_at: "2026-08-04T11:00:00Z",
        handed_off_to_fandi_at: "2026-08-04T12:00:00Z",
      }),
    ]);
    render(
      <LeadWriteupsPanel
        leadId={100}
        leadName="Alice"
        suggestedVehicles={[]}
        loadWriteups={loadWriteups}
      />,
    );
    await openPanel();
    await screen.findByTestId("writeup-row-1");
    expect(screen.getByTestId("writeup-approve-trigger-1")).toBeInTheDocument();
    expect(screen.queryByTestId("writeup-approve-trigger-2")).toBeNull();
    expect(screen.queryByTestId("writeup-approve-trigger-3")).toBeNull();
  });

  it("shows Send-to-F&I trigger on approved rows only", async () => {
    const loadWriteups = vi.fn().mockResolvedValue([
      fixtureWriteup({ id: 1 }),
      fixtureWriteup({
        id: 2,
        sales_manager_approved_at: "2026-08-04T11:00:00Z",
      }),
      fixtureWriteup({
        id: 3,
        sales_manager_approved_at: "2026-08-04T11:00:00Z",
        handed_off_to_fandi_at: "2026-08-04T12:00:00Z",
      }),
    ]);
    render(
      <LeadWriteupsPanel
        leadId={100}
        leadName="Alice"
        suggestedVehicles={[]}
        loadWriteups={loadWriteups}
      />,
    );
    await openPanel();
    await screen.findByTestId("writeup-row-2");
    expect(screen.queryByTestId("writeup-handoff-trigger-1")).toBeNull();
    expect(screen.getByTestId("writeup-handoff-trigger-2")).toBeInTheDocument();
    expect(screen.queryByTestId("writeup-handoff-trigger-3")).toBeNull();
  });

  it("handed_off rows are read-only history (no action buttons)", async () => {
    const loadWriteups = vi.fn().mockResolvedValue([
      fixtureWriteup({
        id: 3,
        sales_manager_approved_at: "2026-08-04T11:00:00Z",
        handed_off_to_fandi_at: "2026-08-04T12:00:00Z",
      }),
    ]);
    render(
      <LeadWriteupsPanel
        leadId={100}
        leadName="Alice"
        suggestedVehicles={[]}
        loadWriteups={loadWriteups}
      />,
    );
    await openPanel();
    await screen.findByTestId("writeup-row-3");
    expect(screen.queryByTestId("writeup-approve-trigger-3")).toBeNull();
    expect(screen.queryByTestId("writeup-handoff-trigger-3")).toBeNull();
  });
});

describe("LeadWriteupsPanel — inline new-writeup form", () => {
  it("shows the '+ New writeup' CTA by default", async () => {
    const loadWriteups = vi.fn().mockResolvedValue([]);
    render(
      <LeadWriteupsPanel
        leadId={100}
        leadName="Alice"
        suggestedVehicles={[]}
        loadWriteups={loadWriteups}
      />,
    );
    await openPanel();
    expect(await screen.findByTestId("lead-writeups-new")).toBeInTheDocument();
    expect(screen.queryByTestId("deal-writeup-form")).toBeNull();
  });

  it("opens the inline form on '+ New writeup' click", async () => {
    const loadWriteups = vi.fn().mockResolvedValue([]);
    render(
      <LeadWriteupsPanel
        leadId={100}
        leadName="Alice"
        suggestedVehicles={[]}
        loadWriteups={loadWriteups}
      />,
    );
    await openPanel();
    await userEvent.click(await screen.findByTestId("lead-writeups-new"));
    expect(screen.getByTestId("deal-writeup-form")).toBeInTheDocument();
  });
});
