// Milestone 28 · Increment 2 (SESSION_196) — JournalEntryTemplateDialog tests.
//
// Guards the M28.2 template-create workflow: dialog opens from its
// trigger, name + description required, side selector present per row,
// balance indicator gates submit, submit posts through
// ``createJournalEntryTemplate`` and fires ``onCreated``, cancel closes
// with no side effects, server errors render inline.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/accountingApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/accountingApi")>(
    "@/lib/accountingApi",
  );
  return {
    ...actual,
    createJournalEntryTemplate: vi.fn(),
    updateJournalEntryTemplate: vi.fn(),
  };
});

import { JournalEntryTemplateDialog } from "@/components/accounting/JournalEntryTemplateDialog";
import {
  createJournalEntryTemplate,
  updateJournalEntryTemplate,
  type GLAccount,
  type JournalEntryTemplate,
} from "@/lib/accountingApi";


function makeAccounts(): GLAccount[] {
  return [
    { id: 1, code: "615000", name: "Rent Expense", type: "expense" },
    { id: 2, code: "110000", name: "Bank — Operating", type: "asset" },
  ];
}


function makeCreatedTemplate(
  overrides: Partial<JournalEntryTemplate> = {},
): JournalEntryTemplate {
  return {
    id: 42,
    name: "Monthly rent",
    description: "Rent expense — monthly",
    is_active: true,
    line_count: 2,
    lines: [
      {
        id: 1,
        account_id: 1,
        account_code: "615000",
        side: "debit",
        amount: "3500.00",
        memo: "",
        ordering: 0,
      },
      {
        id: 2,
        account_id: 2,
        account_code: "110000",
        side: "credit",
        amount: "3500.00",
        memo: "",
        ordering: 1,
      },
    ],
    ...overrides,
  };
}


async function openDialog(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByTestId("tmpl-create-trigger"));
  await waitFor(() => {
    expect(
      screen.getByRole("heading", { level: 2, name: /New recurring template/i }),
    ).toBeInTheDocument();
  });
}


async function fillBalancedTemplate(
  user: ReturnType<typeof userEvent.setup>,
  overrides: { name?: string; description?: string; amount?: string } = {},
) {
  await user.type(
    screen.getByTestId("tmpl-name-input"),
    overrides.name ?? "Monthly rent",
  );
  await user.type(
    screen.getByTestId("tmpl-description-input"),
    overrides.description ?? "Rent expense — monthly",
  );
  const amount = overrides.amount ?? "3500.00";
  // Line 1: debit, Rent Expense.
  await user.click(screen.getAllByTestId("gl-account-option-615000")[0]!);
  await user.type(screen.getByLabelText("Line 1 amount"), amount);
  // Line 2: credit, Bank — Operating (default side is "debit"; flip it).
  await user.selectOptions(screen.getByTestId("tmpl-line-1-side"), "credit");
  await user.click(screen.getAllByTestId("gl-account-option-110000")[0]!);
  await user.type(screen.getByLabelText("Line 2 amount"), amount);
}


describe("JournalEntryTemplateDialog", () => {
  beforeEach(() => {
    vi.mocked(createJournalEntryTemplate).mockReset();
    vi.mocked(createJournalEntryTemplate).mockResolvedValue(
      makeCreatedTemplate(),
    );
  });

  it("renders the trigger button", () => {
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    expect(screen.getByTestId("tmpl-create-trigger")).toBeInTheDocument();
  });

  it("disables the trigger when fewer than 2 accounts are available", () => {
    render(
      <JournalEntryTemplateDialog
        accounts={[makeAccounts()[0]!]}
        onCreated={vi.fn()}
      />,
    );
    expect(screen.getByTestId("tmpl-create-trigger")).toBeDisabled();
  });

  it("opens the dialog when the trigger is clicked", async () => {
    const user = userEvent.setup();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    await openDialog(user);
    expect(screen.getByTestId("tmpl-name-input")).toBeInTheDocument();
    expect(screen.getByTestId("tmpl-description-input")).toBeInTheDocument();
  });

  it("has no posted_at field (templates are recipes, not postings)", async () => {
    const user = userEvent.setup();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    await openDialog(user);
    expect(screen.queryByLabelText(/Posted at/i)).not.toBeInTheDocument();
  });

  it("blocks submit when name is blank", async () => {
    const user = userEvent.setup();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    await openDialog(user);
    expect(screen.getByTestId("tmpl-create-submit")).toBeDisabled();
  });

  it("blocks submit when unbalanced", async () => {
    const user = userEvent.setup();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    await openDialog(user);
    await user.type(screen.getByTestId("tmpl-name-input"), "Broken");
    await user.type(
      screen.getByTestId("tmpl-description-input"),
      "Description",
    );
    await user.click(screen.getAllByTestId("gl-account-option-615000")[0]!);
    await user.type(screen.getByLabelText("Line 1 amount"), "100.00");
    await user.selectOptions(screen.getByTestId("tmpl-line-1-side"), "credit");
    await user.click(screen.getAllByTestId("gl-account-option-110000")[0]!);
    await user.type(screen.getByLabelText("Line 2 amount"), "50.00");
    expect(
      screen.getByTestId("tmpl-create-balance-indicator"),
    ).toHaveTextContent(/Unbalanced/i);
    expect(screen.getByTestId("tmpl-create-submit")).toBeDisabled();
  });

  it("shows Balanced badge when debit-side sum equals credit-side sum", async () => {
    const user = userEvent.setup();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    await openDialog(user);
    await fillBalancedTemplate(user);
    expect(
      screen.getByTestId("tmpl-create-balance-indicator"),
    ).toHaveTextContent(/Balanced/i);
    expect(screen.getByTestId("tmpl-create-submit")).toBeEnabled();
  });

  it("posts the payload and fires onCreated on success", async () => {
    const onCreated = vi.fn();
    const user = userEvent.setup();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={onCreated}
      />,
    );
    await openDialog(user);
    await fillBalancedTemplate(user);
    await user.click(screen.getByTestId("tmpl-create-submit"));
    await waitFor(() => {
      expect(createJournalEntryTemplate).toHaveBeenCalledTimes(1);
    });
    const call = vi.mocked(createJournalEntryTemplate).mock.calls[0]![0];
    expect(call.name).toBe("Monthly rent");
    expect(call.description).toBe("Rent expense — monthly");
    expect(call.lines).toHaveLength(2);
    expect(call.lines[0]!.side).toBe("debit");
    expect(call.lines[0]!.amount).toBe("3500.00");
    expect(call.lines[0]!.account_id).toBe(1);
    expect(call.lines[1]!.side).toBe("credit");
    expect(call.lines[1]!.amount).toBe("3500.00");
    expect(call.lines[1]!.account_id).toBe(2);
    await waitFor(() => {
      expect(onCreated).toHaveBeenCalledTimes(1);
    });
  });

  it("surfaces server errors inline without closing the dialog", async () => {
    vi.mocked(createJournalEntryTemplate).mockRejectedValue(
      new Error("A template with that name already exists."),
    );
    const onCreated = vi.fn();
    const user = userEvent.setup();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={onCreated}
      />,
    );
    await openDialog(user);
    await fillBalancedTemplate(user);
    await user.click(screen.getByTestId("tmpl-create-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("tmpl-create-error")).toHaveTextContent(
        /already exists/i,
      );
    });
    expect(
      screen.getByRole("heading", { level: 2, name: /New recurring template/i }),
    ).toBeInTheDocument();
    expect(onCreated).not.toHaveBeenCalled();
  });

  it("cancel closes the dialog without invoking createJournalEntryTemplate", async () => {
    const onCreated = vi.fn();
    const user = userEvent.setup();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={onCreated}
      />,
    );
    await openDialog(user);
    await user.type(screen.getByTestId("tmpl-name-input"), "Cancel me");
    await user.click(screen.getByRole("button", { name: /^Cancel$/i }));
    expect(createJournalEntryTemplate).not.toHaveBeenCalled();
    expect(onCreated).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(
        screen.queryByRole("heading", { level: 2, name: /New recurring template/i }),
      ).not.toBeInTheDocument();
    });
  });

  it("allows adding and removing lines beyond the minimum-two enforcement", async () => {
    const user = userEvent.setup();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    await openDialog(user);
    // Two default lines; Remove buttons hidden.
    expect(screen.queryByRole("button", { name: /− Remove/i })).not.toBeInTheDocument();
    // Add a third line.
    await user.click(screen.getByRole("button", { name: /\+ Add line/i }));
    expect(screen.getByTestId("tmpl-line-2")).toBeInTheDocument();
    // Remove buttons now visible on the row cluster.
    const removes = screen.getAllByRole("button", { name: /− Remove/i });
    expect(removes.length).toBe(3);
    // Remove the third line.
    await user.click(removes[2]!);
    expect(screen.queryByTestId("tmpl-line-2")).not.toBeInTheDocument();
  });

  // ----------------------------------------------------------------
  // M29 (SESSION_199) — "Variable amount" checkbox coverage
  // ----------------------------------------------------------------

  it("M29 — variable checkbox disables the amount input", async () => {
    const user = userEvent.setup();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    await openDialog(user);
    const line0Amount = screen.getByTestId("tmpl-line-0-amount");
    expect(line0Amount).not.toBeDisabled();
    await user.click(screen.getByTestId("tmpl-line-0-variable"));
    expect(line0Amount).toBeDisabled();
    expect(line0Amount).toHaveAttribute(
      "placeholder",
      "Set at instantiate",
    );
    // Unchecking re-enables it.
    await user.click(screen.getByTestId("tmpl-line-0-variable"));
    expect(line0Amount).not.toBeDisabled();
  });

  it("M29 — balance indicator suppresses fixed-only wording when any line is variable", async () => {
    const user = userEvent.setup();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    await openDialog(user);
    // Baseline (no variable lines): "Enter amounts" surface.
    expect(
      screen.getByTestId("tmpl-create-balance-indicator"),
    ).toHaveTextContent(/Enter amounts/i);
    await user.click(screen.getByTestId("tmpl-line-0-variable"));
    await user.click(screen.getByTestId("tmpl-line-1-variable"));
    // Fully-variable template: variable-note badge appears; no
    // "Unbalanced" wording.
    expect(
      screen.getByTestId("tmpl-create-variable-balance-note"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("tmpl-create-balance-indicator"),
    ).not.toHaveTextContent(/Unbalanced/i);
  });

  it("M29 — fully-variable template posts amount: null on both lines", async () => {
    const onCreated = vi.fn();
    const user = userEvent.setup();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={onCreated}
      />,
    );
    await openDialog(user);
    await user.type(
      screen.getByTestId("tmpl-name-input"),
      "Monthly depreciation",
    );
    await user.type(
      screen.getByTestId("tmpl-description-input"),
      "Depreciation per asset per period",
    );
    // Line 1: debit, Rent Expense, variable.
    await user.click(screen.getAllByTestId("gl-account-option-615000")[0]!);
    await user.click(screen.getByTestId("tmpl-line-0-variable"));
    // Line 2: credit, Bank — Operating, variable.
    await user.selectOptions(
      screen.getByTestId("tmpl-line-1-side"),
      "credit",
    );
    await user.click(screen.getAllByTestId("gl-account-option-110000")[0]!);
    await user.click(screen.getByTestId("tmpl-line-1-variable"));
    await user.click(screen.getByTestId("tmpl-create-submit"));
    await waitFor(() => {
      expect(createJournalEntryTemplate).toHaveBeenCalledTimes(1);
    });
    const payload = vi.mocked(createJournalEntryTemplate).mock.calls[0]![0];
    expect(payload.lines).toHaveLength(2);
    expect(payload.lines[0]!.amount).toBeNull();
    expect(payload.lines[1]!.amount).toBeNull();
    expect(payload.lines[0]!.side).toBe("debit");
    expect(payload.lines[1]!.side).toBe("credit");
  });

  it("M29 — mixed template validates fixed-portion balance", async () => {
    const user = userEvent.setup();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        onCreated={vi.fn()}
      />,
    );
    await openDialog(user);
    await user.type(
      screen.getByTestId("tmpl-name-input"),
      "Mixed template",
    );
    await user.type(
      screen.getByTestId("tmpl-description-input"),
      "Fixed debit + variable credit",
    );
    // Line 1: fixed debit $500.
    await user.click(screen.getAllByTestId("gl-account-option-615000")[0]!);
    await user.type(screen.getByLabelText("Line 1 amount"), "500.00");
    // Line 2: variable credit.
    await user.selectOptions(
      screen.getByTestId("tmpl-line-1-side"),
      "credit",
    );
    await user.click(screen.getAllByTestId("gl-account-option-110000")[0]!);
    await user.click(screen.getByTestId("tmpl-line-1-variable"));
    // Populated portion is imbalanced ($500 debit vs $0 credit).
    // Submit stays disabled.
    expect(screen.getByTestId("tmpl-create-submit")).toBeDisabled();
    expect(
      screen.getByTestId("tmpl-create-balance-indicator"),
    ).toHaveTextContent(/Unbalanced by \$500\.00/);
  });
});


// ======================================================================
// Milestone 30 · Increment 2 (SESSION_202) — edit-mode branch coverage
// ======================================================================

describe("JournalEntryTemplateDialog · edit mode", () => {
  beforeEach(() => {
    vi.mocked(updateJournalEntryTemplate).mockReset();
    vi.mocked(updateJournalEntryTemplate).mockResolvedValue(
      makeCreatedTemplate({ name: "Monthly rent (edited)" }),
    );
  });

  function renderEditMode(overrides: {
    initialTemplate?: JournalEntryTemplate;
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
    onEdited?: (t: JournalEntryTemplate) => void;
  } = {}) {
    const initialTemplate =
      overrides.initialTemplate ?? makeCreatedTemplate();
    const open = overrides.open ?? true;
    const onOpenChange = overrides.onOpenChange ?? vi.fn();
    const onEdited = overrides.onEdited ?? vi.fn();
    render(
      <JournalEntryTemplateDialog
        accounts={makeAccounts()}
        mode="edit"
        initialTemplate={initialTemplate}
        open={open}
        onOpenChange={onOpenChange}
        onEdited={onEdited}
      />,
    );
    return { initialTemplate, onOpenChange, onEdited };
  }

  it("populates form fields from initialTemplate on open", async () => {
    renderEditMode();
    await waitFor(() => {
      expect(screen.getByTestId("tmpl-name-input")).toHaveValue(
        "Monthly rent",
      );
    });
    expect(screen.getByTestId("tmpl-description-input")).toHaveValue(
      "Rent expense — monthly",
    );
    // Line amounts pre-populated.
    expect(screen.getByLabelText("Line 1 amount")).toHaveValue(3500);
    expect(screen.getByLabelText("Line 2 amount")).toHaveValue(3500);
  });

  it("renders 'Edit template' title (not 'New recurring template')", async () => {
    renderEditMode();
    await waitFor(() => {
      expect(screen.getByTestId("tmpl-dialog-title")).toHaveTextContent(
        "Edit template",
      );
    });
  });

  it("renders 'Save changes' submit label (not 'Save template')", async () => {
    renderEditMode();
    await waitFor(() => {
      expect(screen.getByTestId("tmpl-edit-submit")).toHaveTextContent(
        "Save changes",
      );
    });
  });

  it("does NOT render the baked-in create trigger when controlled-open", () => {
    renderEditMode();
    expect(screen.queryByTestId("tmpl-create-trigger")).not.toBeInTheDocument();
  });

  it("submit calls updateJournalEntryTemplate with pk + payload", async () => {
    const user = userEvent.setup();
    renderEditMode();
    await waitFor(() => {
      expect(screen.getByTestId("tmpl-edit-submit")).toBeEnabled();
    });
    await user.click(screen.getByTestId("tmpl-edit-submit"));
    await waitFor(() => {
      expect(updateJournalEntryTemplate).toHaveBeenCalledTimes(1);
    });
    const [pk, payload] = vi.mocked(updateJournalEntryTemplate).mock.calls[0]!;
    expect(pk).toBe(42);
    expect(payload.name).toBe("Monthly rent");
    expect(payload.lines).toHaveLength(2);
  });

  it("fires onEdited on successful submit", async () => {
    const user = userEvent.setup();
    const onEdited = vi.fn();
    renderEditMode({ onEdited });
    await waitFor(() => {
      expect(screen.getByTestId("tmpl-edit-submit")).toBeEnabled();
    });
    await user.click(screen.getByTestId("tmpl-edit-submit"));
    await waitFor(() => {
      expect(onEdited).toHaveBeenCalledTimes(1);
    });
    expect(onEdited.mock.calls[0]![0].name).toBe("Monthly rent (edited)");
  });

  it("closes via onOpenChange(false) on successful edit", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    renderEditMode({ onOpenChange });
    await waitFor(() => {
      expect(screen.getByTestId("tmpl-edit-submit")).toBeEnabled();
    });
    await user.click(screen.getByTestId("tmpl-edit-submit"));
    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("surfaces inline error when updateJournalEntryTemplate rejects", async () => {
    const user = userEvent.setup();
    vi.mocked(updateJournalEntryTemplate).mockRejectedValue(
      new Error("HTTP 409 Duplicate name"),
    );
    renderEditMode();
    await waitFor(() => {
      expect(screen.getByTestId("tmpl-edit-submit")).toBeEnabled();
    });
    await user.click(screen.getByTestId("tmpl-edit-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("tmpl-create-error")).toHaveTextContent(
        /HTTP 409/,
      );
    });
  });
});
