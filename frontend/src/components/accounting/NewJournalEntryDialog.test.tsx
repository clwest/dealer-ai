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


// Milestone 28 · Increment 2 (SESSION_196) — pre-populate + controlled-open
// extensions covering the template Instantiate flow.

describe("NewJournalEntryDialog — M28.2 template Instantiate flow", () => {
  beforeEach(() => {
    vi.mocked(createJournalEntry).mockReset();
    vi.mocked(createJournalEntry).mockResolvedValue(makeCreatedEntry());
  });

  it("hides the built-in trigger when hideTrigger is set", () => {
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
        open={false}
        onOpenChange={vi.fn()}
        hideTrigger
      />,
    );
    expect(
      screen.queryByRole("button", { name: /\+ New journal entry/i }),
    ).not.toBeInTheDocument();
  });

  it("pre-populates description + lines from initialValues on open", async () => {
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
        open
        onOpenChange={vi.fn()}
        hideTrigger
        initialValues={{
          description: "Monthly rent",
          lines: [
            {
              account_id: 1,
              debit: "3500.00",
              credit: "",
              memo: "",
            },
            {
              account_id: 2,
              debit: "",
              credit: "3500.00",
              memo: "",
            },
          ],
        }}
      />,
    );

    // Description pre-filled.
    expect(
      screen.getByRole("textbox", { name: /Description/i }),
    ).toHaveValue("Monthly rent");

    // Line 1 debit pre-filled + account pre-selected.
    expect(screen.getByLabelText("Line 1 debit")).toHaveValue(3500);
    expect(screen.getByLabelText("Line 2 credit")).toHaveValue(3500);

    // Balance indicator immediately reads "Balanced".
    const indicator = screen.getByTestId("je-create-balance-indicator");
    expect(indicator).toHaveTextContent(/Balanced/i);

    // Submit enabled without any typing.
    expect(screen.getByTestId("je-create-submit")).toBeEnabled();
  });

  it("submitting a pre-populated dialog posts the visible payload", async () => {
    const onCreated = vi.fn();
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={onCreated}
        open
        onOpenChange={onOpenChange}
        hideTrigger
        initialValues={{
          description: "Monthly rent",
          lines: [
            { account_id: 1, debit: "3500.00", credit: "", memo: "" },
            { account_id: 2, debit: "", credit: "3500.00", memo: "" },
          ],
        }}
      />,
    );

    await user.click(screen.getByTestId("je-create-submit"));
    await waitFor(() => {
      expect(createJournalEntry).toHaveBeenCalledTimes(1);
    });
    const call = vi.mocked(createJournalEntry).mock.calls[0]![0];
    expect(call.description).toBe("Monthly rent");
    expect(call.lines[0]!.account_id).toBe(1);
    expect(call.lines[0]!.debit).toBe("3500.00");
    expect(call.lines[1]!.credit).toBe("3500.00");
    expect(onCreated).toHaveBeenCalledTimes(1);
    // Cancel-close side effect fired once submission succeeded.
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});


// Milestone 29 · Increment 2 (SESSION_199) — variable-amount UI (D3
// additive lockedLines prop + Override toggle + regression guard).

describe("NewJournalEntryDialog — M29.2 variable-amount UI", () => {
  beforeEach(() => {
    vi.mocked(createJournalEntry).mockReset();
    vi.mocked(createJournalEntry).mockResolvedValue(makeCreatedEntry());
  });

  it("M29 REGRESSION GUARD — blank-entry path unchanged when lockedLines is undefined", async () => {
    // This test explicitly locks the M27.2 blank-entry contract:
    // opening the dialog without lockedLines renders normal editable
    // inputs for both debit and credit on every line, with no chip,
    // no Override pencil, no amber ring.
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
        open
        onOpenChange={vi.fn()}
        hideTrigger
      />,
    );

    // Two default lines with normal editable inputs on both sides.
    expect(screen.getByLabelText("Line 1 debit")).toBeInTheDocument();
    expect(screen.getByLabelText("Line 1 credit")).toBeInTheDocument();
    expect(screen.getByLabelText("Line 2 debit")).toBeInTheDocument();
    expect(screen.getByLabelText("Line 2 credit")).toBeInTheDocument();
    // No chip anywhere.
    expect(
      screen.queryByTestId("je-line-0-debit-chip"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("je-line-1-credit-chip"),
    ).not.toBeInTheDocument();
    // No Override buttons anywhere.
    expect(
      screen.queryByRole("button", { name: /Override/i }),
    ).not.toBeInTheDocument();
  });

  it("M29 — lockedLines[i] === true renders the populated side as a read-only chip with Override", async () => {
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
        open
        onOpenChange={vi.fn()}
        hideTrigger
        initialValues={{
          description: "Monthly rent",
          lines: [
            { account_id: 1, debit: "3500.00", credit: "", memo: "" },
            { account_id: 2, debit: "", credit: "3500.00", memo: "" },
          ],
        }}
        lockedLines={[true, true]}
      />,
    );

    // Debit chip on line 0 + Credit chip on line 1.
    expect(
      screen.getByTestId("je-line-0-debit-chip"),
    ).toHaveTextContent(/\$3500\.00/);
    expect(
      screen.getByTestId("je-line-1-credit-chip"),
    ).toHaveTextContent(/\$3500\.00/);
    // Override pencils on both.
    expect(
      screen.getByTestId("je-line-0-debit-override"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("je-line-1-credit-override"),
    ).toBeInTheDocument();
    // The unpopulated side of a fixed line is disabled empty input.
    expect(screen.getByLabelText("Line 1 credit")).toBeDisabled();
    expect(screen.getByLabelText("Line 2 debit")).toBeDisabled();
  });

  it("M29 — clicking Override transitions a locked line to editable input", async () => {
    const user = userEvent.setup();
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
        open
        onOpenChange={vi.fn()}
        hideTrigger
        initialValues={{
          description: "Monthly rent",
          lines: [
            { account_id: 1, debit: "3500.00", credit: "", memo: "" },
            { account_id: 2, debit: "", credit: "3500.00", memo: "" },
          ],
        }}
        lockedLines={[true, true]}
      />,
    );

    // Precondition: chip.
    expect(
      screen.getByTestId("je-line-0-debit-chip"),
    ).toBeInTheDocument();
    // Click Override on the line 0 debit chip.
    await user.click(screen.getByTestId("je-line-0-debit-override"));
    // Now the chip is gone; a normal editable input is present.
    expect(
      screen.queryByTestId("je-line-0-debit-chip"),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("Line 1 debit")).toBeInTheDocument();
    // Line 1's chip is unaffected — Override is per-line.
    expect(
      screen.getByTestId("je-line-1-credit-chip"),
    ).toBeInTheDocument();
  });

  it("M29 — variable line renders with amber ring on the correct side and disabled opposite side", async () => {
    render(
      <NewJournalEntryDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
        open
        onOpenChange={vi.fn()}
        hideTrigger
        initialValues={{
          description: "Monthly depreciation",
          lines: [
            {
              account_id: 1,
              debit: "",
              credit: "",
              memo: "",
              variableSide: "debit",
            },
            {
              account_id: 2,
              debit: "",
              credit: "",
              memo: "",
              variableSide: "credit",
            },
          ],
        }}
        lockedLines={[false, false]}
      />,
    );

    // Variable-debit line 1: debit editable + amber-ring class +
    // "Enter amount" placeholder; credit disabled.
    const line1Debit = screen.getByLabelText("Line 1 debit");
    expect(line1Debit).not.toBeDisabled();
    expect(line1Debit).toHaveAttribute("placeholder", "Enter amount");
    expect(line1Debit.className).toMatch(/ring-2 ring-amber-500/);
    expect(screen.getByLabelText("Line 1 credit")).toBeDisabled();
    // Variable-credit line 2: mirror config.
    expect(screen.getByLabelText("Line 2 debit")).toBeDisabled();
    const line2Credit = screen.getByLabelText("Line 2 credit");
    expect(line2Credit).not.toBeDisabled();
    expect(line2Credit).toHaveAttribute("placeholder", "Enter amount");
    expect(line2Credit.className).toMatch(/ring-2 ring-amber-500/);
  });
});
