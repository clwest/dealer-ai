// Milestone 27 · Increment 2 (SESSION_193) — NewJournalEntryDialog tests.
//
// Asserts the M27 §5.c user-directed contract: dialog opens from the
// trigger, description is required, `posted_at` defaults to today,
// balance indicator gates the submit button, submit posts through
// ``createJournalEntry`` and fires ``onCreated``, cancel closes with
// no side effects.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/accountingApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/accountingApi")>(
    "@/lib/accountingApi",
  );
  return {
    ...actual,
    createJournalEntry: vi.fn(),
  };
});

import { NewJournalEntryDialog } from "@/components/accounting/NewJournalEntryDialog";
import {
  createJournalEntry,
  type GLAccount,
  type JournalEntry,
} from "@/lib/accountingApi";


function makeAccounts(): GLAccount[] {
  return [
    { id: 1, code: "110000", name: "Bank — Operating", type: "asset" },
    { id: 2, code: "400000", name: "Vehicle Sales — Retail", type: "revenue" },
  ];
}


function makeCreatedEntry(overrides: Partial<JournalEntry> = {}): JournalEntry {
  return {
    id: 99,
    dealership_id: 1,
    description: "Test",
    posted_at: "2026-08-03T12:00:00Z",
    posted_by_user_id: 42,
    reverses_id: null,
    reason: "",
    created_at: "2026-08-03T12:00:00Z",
    lines: [],
    ...overrides,
  };
}


describe("NewJournalEntryDialog", () => {
  beforeEach(() => {
    vi.mocked(createJournalEntry).mockReset();
    vi.mocked(createJournalEntry).mockResolvedValue(makeCreatedEntry());
  });

  it("renders the trigger button", () => {
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("button", { name: /\+ New journal entry/i }),
    ).toBeInTheDocument();
  });

  it("disables the trigger when fewer than 2 accounts are available", () => {
    render(
      <NewJournalEntryDialog
        accounts={[makeAccounts()[0]!]}
        onCreated={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("button", { name: /\+ New journal entry/i }),
    ).toBeDisabled();
  });

  it("opens the dialog when the trigger is clicked", async () => {
    const user = userEvent.setup();
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: /\+ New journal entry/i }),
    );
    expect(
      screen.getByRole("heading", { level: 2, name: /New journal entry/i }),
    ).toBeInTheDocument();
  });

  it("defaults posted_at to today", async () => {
    const user = userEvent.setup();
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: /\+ New journal entry/i }),
    );
    const now = new Date();
    const expected = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
    expect(screen.getByLabelText(/Posted at/i)).toHaveValue(expected);
  });

  it("blocks submit until the entry is balanced with a description", async () => {
    const user = userEvent.setup();
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: /\+ New journal entry/i }),
    );
    const submit = screen.getByTestId("je-create-submit");
    expect(submit).toBeDisabled();
  });

  it("shows 'Balanced' badge when debits equal credits", async () => {
    const user = userEvent.setup();
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: /\+ New journal entry/i }),
    );
    // Description
    await user.type(
      screen.getByRole("textbox", { name: /Description/i }),
      "Test posting",
    );
    // Pick account on line 1, enter debit
    await user.click(
      screen.getAllByTestId("gl-account-option-110000")[0]!,
    );
    await user.type(
      screen.getByLabelText("Line 1 debit"),
      "250.00",
    );
    // Pick account on line 2, enter credit
    await user.click(
      screen.getAllByTestId("gl-account-option-400000")[0]!,
    );
    await user.type(
      screen.getByLabelText("Line 2 credit"),
      "250.00",
    );
    const indicator = screen.getByTestId("je-create-balance-indicator");
    expect(indicator).toHaveTextContent(/Balanced/i);
    expect(screen.getByTestId("je-create-submit")).toBeEnabled();
  });

  it("posts the payload and fires onCreated on success", async () => {
    const onCreated = vi.fn();
    const user = userEvent.setup();
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={onCreated}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: /\+ New journal entry/i }),
    );
    await user.type(
      screen.getByRole("textbox", { name: /Description/i }),
      "Bank deposit",
    );
    await user.click(
      screen.getAllByTestId("gl-account-option-110000")[0]!,
    );
    await user.type(
      screen.getByLabelText("Line 1 debit"),
      "500.00",
    );
    await user.click(
      screen.getAllByTestId("gl-account-option-400000")[0]!,
    );
    await user.type(
      screen.getByLabelText("Line 2 credit"),
      "500.00",
    );
    await user.click(screen.getByTestId("je-create-submit"));
    await waitFor(() => {
      expect(createJournalEntry).toHaveBeenCalledTimes(1);
    });
    const call = vi.mocked(createJournalEntry).mock.calls[0]![0];
    expect(call.description).toBe("Bank deposit");
    expect(call.lines).toHaveLength(2);
    expect(call.lines[0]!.account_id).toBe(1);
    expect(call.lines[0]!.debit).toBe("500.00");
    expect(call.lines[0]!.credit).toBe("0.00");
    expect(call.lines[1]!.account_id).toBe(2);
    expect(call.lines[1]!.credit).toBe("500.00");
    await waitFor(() => {
      expect(onCreated).toHaveBeenCalledTimes(1);
    });
  });

  it("surfaces server errors inline without closing the dialog", async () => {
    vi.mocked(createJournalEntry).mockRejectedValue(
      new Error("Journal entry is unbalanced."),
    );
    const onCreated = vi.fn();
    const user = userEvent.setup();
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={onCreated}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: /\+ New journal entry/i }),
    );
    await user.type(
      screen.getByRole("textbox", { name: /Description/i }),
      "Broken",
    );
    await user.click(
      screen.getAllByTestId("gl-account-option-110000")[0]!,
    );
    await user.type(screen.getByLabelText("Line 1 debit"), "100.00");
    await user.click(
      screen.getAllByTestId("gl-account-option-400000")[0]!,
    );
    await user.type(screen.getByLabelText("Line 2 credit"), "100.00");
    await user.click(screen.getByTestId("je-create-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("je-create-error")).toHaveTextContent(
        /unbalanced/i,
      );
    });
    // Dialog remains open — heading still visible.
    expect(
      screen.getByRole("heading", { level: 2, name: /New journal entry/i }),
    ).toBeInTheDocument();
    expect(onCreated).not.toHaveBeenCalled();
  });

  it("cancel closes the dialog without invoking createJournalEntry", async () => {
    const onCreated = vi.fn();
    const user = userEvent.setup();
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={onCreated}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: /\+ New journal entry/i }),
    );
    await user.type(
      screen.getByRole("textbox", { name: /Description/i }),
      "Cancel me",
    );
    await user.click(screen.getByRole("button", { name: /^Cancel$/i }));
    expect(createJournalEntry).not.toHaveBeenCalled();
    expect(onCreated).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(
        screen.queryByRole("heading", { level: 2, name: /New journal entry/i }),
      ).not.toBeInTheDocument();
    });
  });
});
