// Milestone 14 · Increment 3 (SESSION_136) — journal-entry list page tests.
// Milestone 27 · Increment 2 (SESSION_193) — extended with M27.2
// GLAccount fetch mock + "+ New journal entry" button assertions.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/accountingApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/accountingApi")>(
    "@/lib/accountingApi",
  );
  return {
    ...actual,
    fetchJournalEntries: vi.fn(),
    fetchGLAccounts: vi.fn(),
    fetchJournalEntryTemplates: vi.fn(),
    deleteJournalEntryTemplate: vi.fn(),
  };
});

import {
  deleteJournalEntryTemplate,
  fetchGLAccounts,
  fetchJournalEntries,
  fetchJournalEntryTemplates,
  type GLAccount,
  type JournalEntryListEntry,
  type JournalEntryListPage,
  type JournalEntryTemplate,
} from "@/lib/accountingApi";
import AccountingJournalEntriesPage from "@/pages/AccountingJournalEntriesPage";


function makeAccounts(): GLAccount[] {
  return [
    { id: 1, code: "110000", name: "Bank — Operating", type: "asset" },
    { id: 2, code: "400000", name: "Vehicle Sales — Retail", type: "revenue" },
  ];
}


function makeEntry(
  overrides: Partial<JournalEntryListEntry> = {},
): JournalEntryListEntry {
  return {
    id: 1,
    description: "Demo posting",
    posted_at: "2026-08-02T10:00:00Z",
    posted_by_user_id: 42,
    posted_by_username: "sm-alice",
    reverses_id: null,
    reason: "",
    total_debit: "500.00",
    ...overrides,
  };
}


function makePage(
  overrides: Partial<JournalEntryListPage> = {},
): JournalEntryListPage {
  return {
    entries: [
      makeEntry({ id: 1, description: "First posting" }),
      makeEntry({
        id: 2,
        description: "Second posting",
        total_debit: "1200.50",
      }),
    ],
    total_count: 2,
    page: 1,
    page_size: 25,
    ...overrides,
  };
}


async function renderPage() {
  const view = render(
    <MemoryRouter initialEntries={["/dealer-ai-accounting/journal-entries"]}>
      <Routes>
        <Route
          path="/dealer-ai-accounting/journal-entries"
          element={<AccountingJournalEntriesPage />}
        />
        <Route
          path="/dealer-ai-accounting/journal-entries/:pk"
          element={<div>Detail placeholder</div>}
        />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => {
    expect(fetchJournalEntries).toHaveBeenCalled();
  });
  return view;
}


function makeTemplate(
  overrides: Partial<JournalEntryTemplate> = {},
): JournalEntryTemplate {
  return {
    id: 1,
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


describe("AccountingJournalEntriesPage", () => {
  beforeEach(() => {
    vi.mocked(fetchJournalEntries).mockReset();
    vi.mocked(fetchJournalEntries).mockResolvedValue(makePage());
    vi.mocked(fetchGLAccounts).mockReset();
    vi.mocked(fetchGLAccounts).mockResolvedValue(makeAccounts());
    vi.mocked(fetchJournalEntryTemplates).mockReset();
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([]);
  });

  it("renders the h1 header", async () => {
    await renderPage();
    expect(
      screen.getByRole("heading", { level: 1, name: /Journal Entries/i }),
    ).toBeInTheDocument();
  });

  it("renders each entry row with formatted total", async () => {
    await renderPage();
    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(screen.getByText("First posting")).toBeInTheDocument();
    expect(screen.getByText("#2")).toBeInTheDocument();
    expect(screen.getByText("Second posting")).toBeInTheDocument();
    expect(screen.getByText("$500.00")).toBeInTheDocument();
    expect(screen.getByText("$1,200.50")).toBeInTheDocument();
  });

  it("shows the count and page metadata", async () => {
    await renderPage();
    expect(screen.getByText(/2 entries/)).toBeInTheDocument();
    expect(screen.getByText(/Page 1 of 1/)).toBeInTheDocument();
  });

  it("renders posted_by_username when present", async () => {
    await renderPage();
    expect(screen.getAllByText("sm-alice").length).toBeGreaterThan(0);
  });

  it("renders em-dash for null posted_by_username", async () => {
    vi.mocked(fetchJournalEntries).mockResolvedValue(
      makePage({
        entries: [
          makeEntry({ posted_by_user_id: null, posted_by_username: null }),
        ],
        total_count: 1,
      }),
    );
    await renderPage();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("shows reversal badge when reverses_id set", async () => {
    vi.mocked(fetchJournalEntries).mockResolvedValue(
      makePage({
        entries: [makeEntry({ id: 7, reverses_id: 3, reason: "correction" })],
        total_count: 1,
      }),
    );
    await renderPage();
    expect(screen.getByText(/Reversal of #3/i)).toBeInTheDocument();
  });

  it("shows original badge when reverses_id null", async () => {
    await renderPage();
    expect(screen.getAllByText(/Original/i).length).toBeGreaterThan(0);
  });

  it("shows empty-state message when entries is empty", async () => {
    vi.mocked(fetchJournalEntries).mockResolvedValue(
      makePage({ entries: [], total_count: 0 }),
    );
    await renderPage();
    expect(screen.getByText(/No journal entries yet/i)).toBeInTheDocument();
  });

  it("renders View link pointing at the detail route", async () => {
    await renderPage();
    const links = screen.getAllByRole("link", { name: /View/i });
    expect(links[0]).toHaveAttribute(
      "href",
      "/dealer-ai-accounting/journal-entries/1",
    );
  });

  it("advances to page 2 when Next clicked", async () => {
    vi.mocked(fetchJournalEntries).mockResolvedValue(
      makePage({ total_count: 30, page_size: 25 }),
    );
    await renderPage();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /Next/i }));
    await waitFor(() => {
      expect(fetchJournalEntries).toHaveBeenCalledWith({
        page: 2,
        pageSize: 25,
      });
    });
  });

  it("disables Previous on page 1", async () => {
    await renderPage();
    expect(screen.getByRole("button", { name: /Previous/i })).toBeDisabled();
  });

  it("disables Next when only one page", async () => {
    await renderPage();
    expect(screen.getByRole("button", { name: /Next/i })).toBeDisabled();
  });

  it("renders error state on fetch failure", async () => {
    vi.mocked(fetchJournalEntries).mockRejectedValue(new Error("nope"));
    render(
      <MemoryRouter initialEntries={["/dealer-ai-accounting/journal-entries"]}>
        <Routes>
          <Route
            path="/dealer-ai-accounting/journal-entries"
            element={<AccountingJournalEntriesPage />}
          />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("nope")).toBeInTheDocument();
    });
  });

  // ---- Milestone 27 · Increment 2 additions -----------------------

  it("renders the '+ New journal entry' trigger button", async () => {
    await renderPage();
    await waitFor(() => {
      expect(fetchGLAccounts).toHaveBeenCalled();
    });
    expect(
      screen.getByRole("button", { name: /\+ New journal entry/i }),
    ).toBeInTheDocument();
  });

  it("disables the create trigger when the CoA has fewer than 2 accounts", async () => {
    vi.mocked(fetchGLAccounts).mockResolvedValue([
      { id: 1, code: "110000", name: "Bank", type: "asset" },
    ]);
    await renderPage();
    await waitFor(() => {
      expect(fetchGLAccounts).toHaveBeenCalled();
    });
    expect(
      screen.getByRole("button", { name: /\+ New journal entry/i }),
    ).toBeDisabled();
  });

  it("surfaces a chart-of-accounts fetch error message", async () => {
    vi.mocked(fetchGLAccounts).mockRejectedValue(
      new Error("coa unavailable"),
    );
    await renderPage();
    await waitFor(() => {
      expect(
        screen.getByText(/Could not load the chart of accounts/i),
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/coa unavailable/)).toBeInTheDocument();
  });

  // ---- Milestone 28 · Increment 2 templates section ---------------

  it("renders the templates section with a count badge", async () => {
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    expect(screen.getByTestId("templates-section")).toBeInTheDocument();
    expect(screen.getByTestId("templates-count")).toHaveTextContent("0");
  });

  it("renders the templates section empty state when expanded", async () => {
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    expect(
      screen.getByText(/Save your first template/i),
    ).toBeInTheDocument();
  });

  it("renders template rows with Instantiate buttons when expanded", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeTemplate({ id: 7, name: "Monthly rent" }),
      makeTemplate({ id: 8, name: "Depreciation" }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    // Count badge reflects the two templates.
    expect(screen.getByTestId("templates-count")).toHaveTextContent("2");
    // Expand the section to reveal rows.
    await user.click(screen.getByTestId("templates-toggle"));
    expect(screen.getByTestId("template-row-7")).toBeInTheDocument();
    expect(screen.getByTestId("template-row-8")).toBeInTheDocument();
    expect(screen.getByTestId("template-instantiate-7")).toBeInTheDocument();
    expect(screen.getByTestId("template-instantiate-8")).toBeInTheDocument();
  });

  it("opens the JE dialog pre-populated when Instantiate is clicked", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeTemplate({ id: 42, name: "Monthly rent" }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    await user.click(screen.getByTestId("template-instantiate-42"));

    // JE dialog opens with description pre-populated from the template.
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 2, name: /New journal entry/i }),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole("textbox", { name: /Description/i }),
    ).toHaveValue("Rent expense — monthly");
    // M29.2 — fixed template lines render as read-only chips with an
    // Override pencil; the amounts are visible but the amount inputs
    // themselves do not exist until Override is clicked.
    expect(
      screen.getByTestId("je-line-0-debit-chip"),
    ).toHaveTextContent(/\$3500\.00/);
    expect(
      screen.getByTestId("je-line-1-credit-chip"),
    ).toHaveTextContent(/\$3500\.00/);
    expect(
      screen.getByTestId("je-line-0-debit-override"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("je-line-1-credit-override"),
    ).toBeInTheDocument();
    // Balance indicator shows Balanced immediately (chip values still
    // populate the underlying debit/credit state).
    expect(
      screen.getByTestId("je-create-balance-indicator"),
    ).toHaveTextContent(/Balanced/i);
  });

  it("surfaces a templates fetch error inline when expanded", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockRejectedValue(
      new Error("templates unavailable"),
    );
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    await waitFor(() => {
      expect(screen.getByText(/Could not load templates/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/templates unavailable/)).toBeInTheDocument();
  });

  // ---------------------------------------------------------------
  // M29 (SESSION_199) — variable-amount instantiate wiring
  // ---------------------------------------------------------------

  it("M29 — instantiating a fully-variable template renders both lines with amber ring", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeTemplate({
        id: 99,
        name: "Monthly depreciation",
        description: "Depreciation per asset per period",
        lines: [
          {
            id: 1,
            account_id: 1,
            account_code: "671000",
            side: "debit",
            amount: null,
            memo: "",
            ordering: 0,
          },
          {
            id: 2,
            account_id: 2,
            account_code: "160000",
            side: "credit",
            amount: null,
            memo: "",
            ordering: 1,
          },
        ],
      }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    await user.click(screen.getByTestId("template-instantiate-99"));
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 2, name: /New journal entry/i }),
      ).toBeInTheDocument();
    });
    // No chips (nothing is fixed).
    expect(
      screen.queryByTestId("je-line-0-debit-chip"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("je-line-1-credit-chip"),
    ).not.toBeInTheDocument();
    // Variable-debit line 1: debit amber-ringed + editable; credit
    // disabled empty.
    const line1Debit = screen.getByLabelText("Line 1 debit");
    expect(line1Debit).not.toBeDisabled();
    expect(line1Debit.className).toMatch(/ring-2 ring-amber-500/);
    expect(screen.getByLabelText("Line 1 credit")).toBeDisabled();
    // Variable-credit line 2: mirror.
    const line2Credit = screen.getByLabelText("Line 2 credit");
    expect(line2Credit).not.toBeDisabled();
    expect(line2Credit.className).toMatch(/ring-2 ring-amber-500/);
    expect(screen.getByLabelText("Line 2 debit")).toBeDisabled();
  });

  it("M29 — instantiating a mixed template renders one chip and one amber-ring", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeTemplate({
        id: 100,
        name: "Utilities monthly",
        description: "Base fee fixed; usage varies",
        lines: [
          {
            id: 1,
            account_id: 1,
            account_code: "671000",
            side: "debit",
            amount: "25.00",
            memo: "Base fee",
            ordering: 0,
          },
          {
            id: 2,
            account_id: 2,
            account_code: "110000",
            side: "credit",
            amount: null,
            memo: "Variable usage",
            ordering: 1,
          },
        ],
      }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    await user.click(screen.getByTestId("template-instantiate-100"));
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 2, name: /New journal entry/i }),
      ).toBeInTheDocument();
    });
    // Line 1 (fixed debit): chip + Override present.
    expect(
      screen.getByTestId("je-line-0-debit-chip"),
    ).toHaveTextContent(/\$25\.00/);
    expect(
      screen.getByTestId("je-line-0-debit-override"),
    ).toBeInTheDocument();
    // Line 2 (variable credit): amber-ring editable + placeholder;
    // debit side disabled.
    const line2Credit = screen.getByLabelText("Line 2 credit");
    expect(line2Credit).toHaveAttribute("placeholder", "Enter amount");
    expect(line2Credit.className).toMatch(/ring-2 ring-amber-500/);
    expect(screen.getByLabelText("Line 2 debit")).toBeDisabled();
  });


  // ------------------------------------------------------------------
  // Milestone 30 · Increment 2 — Edit + Delete row buttons + inline
  // delete confirmation dialog.
  // ------------------------------------------------------------------

  it("M30.2 — template row renders Edit + Delete buttons", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeTemplate({ id: 55, name: "Row-buttons target" }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    expect(
      screen.getByTestId("tmpl-edit-trigger-55"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("tmpl-delete-trigger-55"),
    ).toBeInTheDocument();
  });

  it("M30.2 — Edit click opens dialog in edit mode with initial values", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeTemplate({ id: 77, name: "Edit-open target" }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    await user.click(screen.getByTestId("tmpl-edit-trigger-77"));
    await waitFor(() => {
      expect(screen.getByTestId("tmpl-dialog-title")).toHaveTextContent(
        "Edit template",
      );
    });
    // Populated with template values.
    expect(screen.getByTestId("tmpl-name-input")).toHaveValue(
      "Edit-open target",
    );
    // Submit button uses edit-mode test-id and label.
    expect(screen.getByTestId("tmpl-edit-submit")).toHaveTextContent(
      "Save changes",
    );
  });

  it("M30.2 — Delete click opens confirmation dialog with mandated copy", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeTemplate({ id: 88, name: "Confirmation target" }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    await user.click(screen.getByTestId("tmpl-delete-trigger-88"));
    await waitFor(() => {
      expect(
        screen.getByTestId("tmpl-delete-confirm-title"),
      ).toHaveTextContent("Deactivate template?");
    });
    expect(screen.getByTestId("tmpl-delete-confirm-body")).toHaveTextContent(
      /Historical journal entries created from this template are not affected/,
    );
    expect(screen.getByTestId("tmpl-delete-confirm-body")).toHaveTextContent(
      /You can restore this template later/,
    );
    // Buttons present.
    expect(screen.getByTestId("tmpl-delete-cancel")).toHaveTextContent(
      "Cancel",
    );
    expect(screen.getByTestId("tmpl-delete-confirm")).toHaveTextContent(
      "Deactivate",
    );
  });

  it("M30.2 — Delete confirm calls deleteJournalEntryTemplate and refetches", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeTemplate({ id: 99, name: "Delete flow target" }),
    ]);
    vi.mocked(deleteJournalEntryTemplate).mockReset();
    vi.mocked(deleteJournalEntryTemplate).mockResolvedValue(undefined);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    const fetchCallsBeforeDelete =
      vi.mocked(fetchJournalEntryTemplates).mock.calls.length;
    await user.click(screen.getByTestId("tmpl-delete-trigger-99"));
    await user.click(screen.getByTestId("tmpl-delete-confirm"));
    await waitFor(() => {
      expect(deleteJournalEntryTemplate).toHaveBeenCalledWith(99);
    });
    await waitFor(() => {
      expect(
        vi.mocked(fetchJournalEntryTemplates).mock.calls.length,
      ).toBeGreaterThan(fetchCallsBeforeDelete);
    });
    // Confirmation closes on success.
    expect(
      screen.queryByTestId("tmpl-delete-confirm-dialog"),
    ).not.toBeInTheDocument();
  });

  it("M30.2 — Delete failure surfaces inline error without closing", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeTemplate({ id: 111, name: "Delete-failure target" }),
    ]);
    vi.mocked(deleteJournalEntryTemplate).mockReset();
    vi.mocked(deleteJournalEntryTemplate).mockRejectedValue(
      new Error("HTTP 500 Server error"),
    );
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    await user.click(screen.getByTestId("tmpl-delete-trigger-111"));
    await user.click(screen.getByTestId("tmpl-delete-confirm"));
    await waitFor(() => {
      expect(screen.getByTestId("tmpl-delete-error")).toHaveTextContent(
        /HTTP 500/,
      );
    });
    // Dialog stays open on error.
    expect(
      screen.getByTestId("tmpl-delete-confirm-dialog"),
    ).toBeInTheDocument();
  });
});
