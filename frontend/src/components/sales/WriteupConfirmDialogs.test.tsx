// Milestone 32 · Increment 2 (SESSION_208) — writeup confirmation dialogs.
//
// Asserts the D5-revised approve copy verbatim (no false re-approval
// advertisement) and the D6 irreversibility hand-off copy verbatim.
// The dialogs' submit paths + error states are exercised end-to-end
// through the LeadWriteupsPanel + Playwright journey; unit tests
// here focus on copy fidelity + submit invocation.

import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DealWriteupProjection } from "@/lib/salesApi";

import {
  WriteupApproveConfirmDialog,
  WriteupHandoffConfirmDialog,
} from "./WriteupConfirmDialogs";

function fixtureWriteup(
  overrides: Partial<DealWriteupProjection> = {},
): DealWriteupProjection {
  return {
    id: 42,
    lead_id: 100,
    vehicle_id: 200,
    dealership_id: 1,
    vehicle_price: "28500.00",
    trade_allowance: null,
    down_payment: null,
    monthly_payment_target: "450.00",
    term_months_target: 72,
    apr_target: "7.49",
    write_up_at: "2026-08-04T10:00:00Z",
    written_up_by_user_id: null,
    sales_manager_approved_at: null,
    sales_manager_approved_by_user_id: null,
    handed_off_to_fandi_at: null,
    notes: "",
    created_at: "2026-08-04T10:00:00Z",
    updated_at: "2026-08-04T10:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("WriteupApproveConfirmDialog — D5-revised copy", () => {
  it("renders the exact approve title + body copy (no false re-approval advertisement)", () => {
    render(
      <WriteupApproveConfirmDialog
        writeup={fixtureWriteup()}
        open
        onOpenChange={vi.fn()}
        onApproved={vi.fn()}
        submit={vi.fn()}
      />,
    );
    expect(screen.getByText("Approve deal writeup?")).toBeInTheDocument();
    // D5-revised body copy verbatim — no "re-approve" language.
    expect(
      screen.getByText(
        /Approving marks this writeup ready for F&I hand-off\. Review the terms carefully before continuing\. After it is sent to F&I, the hand-off cannot be repeated or undone\./,
      ),
    ).toBeInTheDocument();
    // Belt: the removed re-approval advertisement must NOT be present.
    expect(
      screen.queryByText(/re-approve/i),
    ).toBeNull();
    expect(
      screen.queryByText(/another manager/i),
    ).toBeNull();
  });

  it("invokes submit(pk) and onApproved on submit-click, then closes", async () => {
    const submit = vi.fn().mockResolvedValue(
      fixtureWriteup({
        sales_manager_approved_at: "2026-08-04T11:00:00Z",
      }),
    );
    const onApproved = vi.fn();
    const onOpenChange = vi.fn();
    render(
      <WriteupApproveConfirmDialog
        writeup={fixtureWriteup()}
        open
        onOpenChange={onOpenChange}
        onApproved={onApproved}
        submit={submit}
      />,
    );
    await userEvent.click(screen.getByTestId("writeup-approve-submit"));
    expect(submit).toHaveBeenCalledWith(42);
    expect(onApproved).toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("cancel button calls onOpenChange(false) without submitting", async () => {
    const submit = vi.fn();
    const onOpenChange = vi.fn();
    render(
      <WriteupApproveConfirmDialog
        writeup={fixtureWriteup()}
        open
        onOpenChange={onOpenChange}
        onApproved={vi.fn()}
        submit={submit}
      />,
    );
    await userEvent.click(screen.getByTestId("writeup-approve-cancel"));
    expect(submit).not.toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});

describe("WriteupHandoffConfirmDialog — D6 irreversibility copy", () => {
  it("renders the exact hand-off title + body copy (irreversibility explicit)", () => {
    render(
      <WriteupHandoffConfirmDialog
        writeup={fixtureWriteup()}
        leadName="Alice Applicant"
        open
        onOpenChange={vi.fn()}
        onHandedOff={vi.fn()}
        submit={vi.fn()}
      />,
    );
    expect(screen.getByText("Send to F&I?")).toBeInTheDocument();
    // D6 body copy — asserts key phrases verbatim (irreversibility +
    // duplicate-CA rationale).
    expect(
      screen.getByText(
        /This creates a credit application for/,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Alice Applicant")).toBeInTheDocument();
    expect(
      screen.getByText(
        /This cannot be undone/,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /a second attempt will be refused to protect against duplicate applications and their retention-clock consequences/,
      ),
    ).toBeInTheDocument();
  });

  it("invokes submit(pk) and onHandedOff on submit-click, then closes", async () => {
    const submit = vi.fn().mockResolvedValue({
      deal_writeup: fixtureWriteup({
        handed_off_to_fandi_at: "2026-08-04T12:00:00Z",
      }),
      credit_application: {
        id: 999,
        lead_id: 100,
        source_format: "tablet",
        captured_at: "2026-08-04T12:00:00Z",
      },
    });
    const onHandedOff = vi.fn();
    const onOpenChange = vi.fn();
    render(
      <WriteupHandoffConfirmDialog
        writeup={fixtureWriteup()}
        leadName="Alice"
        open
        onOpenChange={onOpenChange}
        onHandedOff={onHandedOff}
        submit={submit}
      />,
    );
    await userEvent.click(screen.getByTestId("writeup-handoff-submit"));
    expect(submit).toHaveBeenCalledWith(42);
    expect(onHandedOff).toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("cancel button calls onOpenChange(false) without submitting", async () => {
    const submit = vi.fn();
    const onOpenChange = vi.fn();
    render(
      <WriteupHandoffConfirmDialog
        writeup={fixtureWriteup()}
        leadName="Alice"
        open
        onOpenChange={onOpenChange}
        onHandedOff={vi.fn()}
        submit={submit}
      />,
    );
    await userEvent.click(screen.getByTestId("writeup-handoff-cancel"));
    expect(submit).not.toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
