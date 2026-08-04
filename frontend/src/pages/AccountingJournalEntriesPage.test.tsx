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
    restoreJournalEntryTemplate: vi.fn(),
  };
});

import {
  deleteJournalEntryTemplate,
  fetchGLAccounts,
  fetchJournalEntries,
  fetchJournalEntryTemplates,
  restoreJournalEntryTemplate,
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
    vi.mocked(restoreJournalEntryTemplate).mockReset();
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
      /You can restore this template later — turn on Show inactive to find and reactivate it/,
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

  // ================================================================
  // Milestone 31 · Increment 2 (SESSION_205) — Show-inactive toggle +
  // inactive-row rendering + Restore UI + D10 copy update coverage.
  //
  // Per MILESTONE_31_PLANNING.md §5.b D4–D10. Covers: toggle renders +
  // default off (D5); toggle flip triggers refetch with
  // includeInactive=true (D4); three inactive-row signals (D6 — badge,
  // aria-label, dedicated testid); L1 guard visible-but-disabled
  // Edit + Instantiate with explanatory aria-labels (D7); Restore row
  // button replaces Delete on inactive rows (D7); Restore confirmation
  // dialog with mandated Reactivate copy (D8); Restore confirm path
  // calls restoreJournalEntryTemplate + refetches (D8); Restore
  // failure surfaces inline error without closing (D8).
  // ================================================================

  function makeInactiveTemplate(
    overrides: Partial<JournalEntryTemplate> = {},
  ): JournalEntryTemplate {
    return makeTemplate({ is_active: false, ...overrides });
  }

  it("M31.2 — Show-inactive toggle renders in templates section header (default off)", async () => {
    await renderPage();
    const toggle = await screen.findByTestId(
      "templates-show-inactive-toggle",
    );
    expect(toggle).toBeInTheDocument();
    expect(toggle).not.toBeChecked();
  });

  it("M31.2 — flipping Show-inactive toggle refetches with includeInactive=true", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalledWith({
        includeInactive: false,
      });
    });
    await user.click(screen.getByTestId("templates-show-inactive-toggle"));
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalledWith({
        includeInactive: true,
      });
    });
  });

  it("M31.2 — inactive row renders three independent signals (badge + aria-label + testid)", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeInactiveTemplate({ id: 205, name: "Hidden template" }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));

    // Signal 1: dedicated inactive testid (not the active-row shape).
    const row = await screen.findByTestId("template-row-inactive-205");
    expect(row).toBeInTheDocument();
    expect(screen.queryByTestId("template-row-205")).toBeNull();

    // Signal 2: visible Inactive badge.
    const badge = screen.getByTestId("template-inactive-badge-205");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("Inactive");

    // Signal 3: row aria-label announces lifecycle state.
    expect(row).toHaveAttribute(
      "aria-label",
      "Template Hidden template, inactive",
    );
  });

  it("M31.2 — inactive row disables Instantiate with explanatory aria-label (L1 guard)", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeInactiveTemplate({ id: 206 }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    const button = await screen.findByTestId("template-instantiate-206");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute(
      "aria-label",
      "Instantiate template — template is inactive; restore it first to enable",
    );
  });

  it("M31.2 — inactive row disables Edit with explanatory aria-label (L1 guard)", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeInactiveTemplate({ id: 207 }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    const button = await screen.findByTestId("tmpl-edit-trigger-207");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute(
      "aria-label",
      "Edit template — restore it first to enable",
    );
  });

  it("M31.2 — inactive row swaps Delete slot for a Restore button", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeInactiveTemplate({ id: 208 }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    expect(
      await screen.findByTestId("tmpl-restore-trigger-208"),
    ).toBeInTheDocument();
    // Delete slot must NOT appear on an inactive row.
    expect(screen.queryByTestId("tmpl-delete-trigger-208")).toBeNull();
  });

  it("M31.2 — active row still renders Delete (not Restore) after M31.2 changes", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeTemplate({ id: 209, is_active: true }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    expect(
      screen.getByTestId("tmpl-delete-trigger-209"),
    ).toBeInTheDocument();
    // No Inactive badge on an active row.
    expect(screen.queryByTestId("template-inactive-badge-209")).toBeNull();
    // Instantiate button not disabled on an active row.
    expect(screen.getByTestId("template-instantiate-209")).not.toBeDisabled();
  });

  it("M31.2 — Restore click opens confirmation dialog with mandated Reactivate copy (D8)", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeInactiveTemplate({ id: 210, name: "Restore-target" }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    await user.click(screen.getByTestId("tmpl-restore-trigger-210"));
    await waitFor(() => {
      expect(
        screen.getByTestId("tmpl-restore-confirm-title"),
      ).toHaveTextContent("Reactivate template?");
    });
    expect(
      screen.getByTestId("tmpl-restore-confirm-body"),
    ).toHaveTextContent(
      /This template will reappear in the active templates list/,
    );
    expect(
      screen.getByTestId("tmpl-restore-confirm-body"),
    ).toHaveTextContent(
      /Existing journal entries created from this template are not affected/,
    );
    expect(screen.getByTestId("tmpl-restore-cancel")).toHaveTextContent(
      "Cancel",
    );
    expect(screen.getByTestId("tmpl-restore-submit")).toHaveTextContent(
      "Reactivate",
    );
  });

  it("M31.2 — Restore confirm calls restoreJournalEntryTemplate + refetches + shows success badge", async () => {
    const restored = makeTemplate({
      id: 211,
      name: "Restore flow target",
      is_active: true,
    });
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeInactiveTemplate({ id: 211, name: "Restore flow target" }),
    ]);
    vi.mocked(restoreJournalEntryTemplate).mockResolvedValue(restored);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    const fetchCallsBefore =
      vi.mocked(fetchJournalEntryTemplates).mock.calls.length;
    await user.click(screen.getByTestId("tmpl-restore-trigger-211"));
    await user.click(screen.getByTestId("tmpl-restore-submit"));
    await waitFor(() => {
      expect(restoreJournalEntryTemplate).toHaveBeenCalledWith(211);
    });
    await waitFor(() => {
      expect(
        vi.mocked(fetchJournalEntryTemplates).mock.calls.length,
      ).toBeGreaterThan(fetchCallsBefore);
    });
    // Confirmation closes on success.
    expect(
      screen.queryByTestId("tmpl-restore-confirm-dialog"),
    ).not.toBeInTheDocument();
    // Success badge surfaces.
    expect(
      screen.getByTestId("tmpl-restore-success-badge"),
    ).toHaveTextContent(/Restore flow target/);
  });

  it("M31.2 — Restore failure surfaces inline error without closing", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeInactiveTemplate({ id: 212, name: "Restore-failure target" }),
    ]);
    vi.mocked(restoreJournalEntryTemplate).mockRejectedValue(
      new Error("HTTP 500 Server error"),
    );
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    await user.click(screen.getByTestId("tmpl-restore-trigger-212"));
    await user.click(screen.getByTestId("tmpl-restore-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("tmpl-restore-error")).toHaveTextContent(
        /HTTP 500/,
      );
    });
    // Dialog stays open on error.
    expect(
      screen.getByTestId("tmpl-restore-confirm-dialog"),
    ).toBeInTheDocument();
  });

  it("M31.2 — Restore cancel closes dialog without calling the wrapper", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeInactiveTemplate({ id: 213 }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    await user.click(screen.getByTestId("tmpl-restore-trigger-213"));
    await user.click(screen.getByTestId("tmpl-restore-cancel"));
    expect(
      screen.queryByTestId("tmpl-restore-confirm-dialog"),
    ).not.toBeInTheDocument();
    expect(restoreJournalEntryTemplate).not.toHaveBeenCalled();
  });

  it("M31.2 — D10 delete-confirm copy points at the new Show inactive toggle (fulfillment)", async () => {
    vi.mocked(fetchJournalEntryTemplates).mockResolvedValue([
      makeTemplate({ id: 214, name: "D10 target" }),
    ]);
    const user = userEvent.setup();
    await renderPage();
    await waitFor(() => {
      expect(fetchJournalEntryTemplates).toHaveBeenCalled();
    });
    await user.click(screen.getByTestId("templates-toggle"));
    await user.click(screen.getByTestId("tmpl-delete-trigger-214"));
    await waitFor(() => {
      expect(
        screen.getByTestId("tmpl-delete-confirm-body"),
      ).toHaveTextContent(
        /turn on Show inactive to find and reactivate it/,
      );
    });
    // Guard: the M30.2 "Restore UX ships in a future milestone"
    // promise must not appear anywhere in the shipped body.
    expect(
      screen.getByTestId("tmpl-delete-confirm-body").textContent,
    ).not.toContain("Restore UX ships in a future milestone");
  });
});
