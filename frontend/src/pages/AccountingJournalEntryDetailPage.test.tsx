// Milestone 14 · Increment 3 + 4 (SESSION_136 + SESSION_137) —
// journal-entry detail page tests. Base render + M14.4 reversal dialog.

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
    fetchJournalEntry: vi.fn(),
    reverseJournalEntry: vi.fn(),
  };
});

import {
  fetchJournalEntry,
  reverseJournalEntry,
  type JournalEntry,
} from "@/lib/accountingApi";
import AccountingJournalEntryDetailPage from "@/pages/AccountingJournalEntryDetailPage";


function makeEntry(overrides: Partial<JournalEntry> = {}): JournalEntry {
  return {
    id: 42,
    dealership_id: 1,
    description: "Demo sale posting",
    posted_at: "2026-08-02T10:00:00Z",
    posted_by_user_id: 7,
    reverses_id: null,
    reason: "",
    created_at: "2026-08-02T10:00:00Z",
    lines: [
      {
        id: 1,
        account_id: 10,
        account_code: "100000",
        debit: "1000.00",
        credit: "0.00",
        memo: "Cash in",
      },
      {
        id: 2,
        account_id: 20,
        account_code: "400000",
        debit: "0.00",
        credit: "1000.00",
        memo: "Sale rev",
      },
    ],
    ...overrides,
  };
}


async function renderPage(pk: string = "42") {
  const view = render(
    <MemoryRouter
      initialEntries={[`/dealer-ai-accounting/journal-entries/${pk}`]}
    >
      <Routes>
        <Route
          path="/dealer-ai-accounting/journal-entries/:pk"
          element={<AccountingJournalEntryDetailPage />}
        />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => {
    expect(fetchJournalEntry).toHaveBeenCalled();
  });
  return view;
}


describe("AccountingJournalEntryDetailPage", () => {
  beforeEach(() => {
    vi.mocked(fetchJournalEntry).mockReset();
    vi.mocked(fetchJournalEntry).mockResolvedValue(makeEntry());
    vi.mocked(reverseJournalEntry).mockReset();
  });

  it("renders the h1 with the entry ID", async () => {
    await renderPage();
    expect(
      screen.getByRole("heading", { level: 1, name: /Journal Entry #42/i }),
    ).toBeInTheDocument();
  });

  it("renders the description in the header card", async () => {
    await renderPage();
    expect(screen.getByText("Demo sale posting")).toBeInTheDocument();
  });

  it("renders every line row with formatted debit/credit", async () => {
    await renderPage();
    expect(await screen.findByText("100000")).toBeInTheDocument();
    expect(screen.getByText("400000")).toBeInTheDocument();
    expect(screen.getAllByText("$1,000.00").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Cash in")).toBeInTheDocument();
    expect(screen.getByText("Sale rev")).toBeInTheDocument();
  });

  it("renders original-entry badge when reverses_id is null", async () => {
    await renderPage();
    expect(screen.getByText(/Original entry/i)).toBeInTheDocument();
  });

  it("renders reversal badge + reason when reverses_id set", async () => {
    vi.mocked(fetchJournalEntry).mockResolvedValue(
      makeEntry({
        id: 99,
        reverses_id: 42,
        reason: "operator correction — wrong amount",
      }),
    );
    await renderPage("99");
    expect(screen.getByText(/Reversal of #42/i)).toBeInTheDocument();
    expect(
      screen.getByText(/operator correction — wrong amount/i),
    ).toBeInTheDocument();
  });

  it("renders back link to journal entries list", async () => {
    await renderPage();
    const backLink = screen.getByRole("link", {
      name: /Back to journal entries/i,
    });
    expect(backLink).toHaveAttribute(
      "href",
      "/dealer-ai-accounting/journal-entries",
    );
  });

  it("shows the enabled Reverse-entry trigger button (M14.4)", async () => {
    await renderPage();
    const button = screen.getByRole("button", {
      name: /^Reverse this entry$/i,
    });
    expect(button).toBeEnabled();
  });

  it("opens the reversal dialog when the trigger is clicked", async () => {
    await renderPage();
    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: /^Reverse this entry$/i }),
    );
    expect(
      await screen.findByRole("heading", {
        name: /Reverse journal entry #42/i,
      }),
    ).toBeInTheDocument();
  });

  it("disables Confirm when the reason is blank", async () => {
    await renderPage();
    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: /^Reverse this entry$/i }),
    );
    const confirm = await screen.findByRole("button", {
      name: /Confirm reversal/i,
    });
    expect(confirm).toBeDisabled();
  });

  it("enables Confirm once the reason is populated", async () => {
    await renderPage();
    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: /^Reverse this entry$/i }),
    );
    const textarea = await screen.findByPlaceholderText(
      /Why is this entry being reversed/i,
    );
    await user.type(textarea, "Wrong amount");
    expect(
      screen.getByRole("button", { name: /Confirm reversal/i }),
    ).toBeEnabled();
  });

  it("posts the reversal and re-fetches on success", async () => {
    vi.mocked(reverseJournalEntry).mockResolvedValue(
      makeEntry({ id: 99, reverses_id: 42, reason: "Wrong amount" }),
    );
    await renderPage();
    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: /^Reverse this entry$/i }),
    );
    await user.type(
      await screen.findByPlaceholderText(/Why is this entry being reversed/i),
      "Wrong amount",
    );
    await user.click(
      screen.getByRole("button", { name: /Confirm reversal/i }),
    );
    await waitFor(() => {
      expect(reverseJournalEntry).toHaveBeenCalledWith(42, {
        reason: "Wrong amount",
        posted_at: undefined,
      });
    });
    // Detail re-fetches — fetchJournalEntry called at least twice
    // (initial load + post-reversal reload).
    await waitFor(() => {
      expect(vi.mocked(fetchJournalEntry).mock.calls.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("surfaces backend error inline without closing the dialog", async () => {
    vi.mocked(reverseJournalEntry).mockRejectedValue(
      new Error("API request failed (400): reason required"),
    );
    await renderPage();
    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: /^Reverse this entry$/i }),
    );
    await user.type(
      await screen.findByPlaceholderText(/Why is this entry being reversed/i),
      "attempt",
    );
    await user.click(
      screen.getByRole("button", { name: /Confirm reversal/i }),
    );
    await waitFor(() => {
      expect(
        screen.getByRole("alert"),
      ).toHaveTextContent(/reason required/i);
    });
    // Dialog stays open — heading still visible.
    expect(
      screen.getByRole("heading", { name: /Reverse journal entry #42/i }),
    ).toBeInTheDocument();
  });

  it("does not post when Cancel is clicked", async () => {
    await renderPage();
    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: /^Reverse this entry$/i }),
    );
    await user.type(
      await screen.findByPlaceholderText(/Why is this entry being reversed/i),
      "typed but cancelled",
    );
    await user.click(screen.getByRole("button", { name: /Cancel/i }));
    expect(reverseJournalEntry).not.toHaveBeenCalled();
  });

  it("renders posted_by_user_id when populated", async () => {
    await renderPage();
    expect(screen.getByText("#7")).toBeInTheDocument();
  });

  it("renders em-dash when posted_by_user_id is null", async () => {
    vi.mocked(fetchJournalEntry).mockResolvedValue(
      makeEntry({ posted_by_user_id: null }),
    );
    await renderPage();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("shows the not-found state when the API rejects with 404-ish error", async () => {
    vi.mocked(fetchJournalEntry).mockRejectedValue(
      new Error("JournalEntry not found."),
    );
    render(
      <MemoryRouter initialEntries={["/dealer-ai-accounting/journal-entries/9999"]}>
        <Routes>
          <Route
            path="/dealer-ai-accounting/journal-entries/:pk"
            element={<AccountingJournalEntryDetailPage />}
          />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/Journal entry not found/i)).toBeInTheDocument();
    });
  });

  it("renders generic error for non-404 failures", async () => {
    vi.mocked(fetchJournalEntry).mockRejectedValue(new Error("boom"));
    render(
      <MemoryRouter initialEntries={["/dealer-ai-accounting/journal-entries/42"]}>
        <Routes>
          <Route
            path="/dealer-ai-accounting/journal-entries/:pk"
            element={<AccountingJournalEntryDetailPage />}
          />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("boom")).toBeInTheDocument();
    });
  });
});
