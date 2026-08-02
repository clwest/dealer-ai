// Milestone 14 · Increment 3 (SESSION_136) — journal-entry detail page tests.

import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/accountingApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/accountingApi")>(
    "@/lib/accountingApi",
  );
  return {
    ...actual,
    fetchJournalEntry: vi.fn(),
  };
});

import { fetchJournalEntry, type JournalEntry } from "@/lib/accountingApi";
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
    expect(screen.getByText("100000")).toBeInTheDocument();
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

  it("shows the disabled Reverse-entry placeholder button", async () => {
    await renderPage();
    const button = screen.getByRole("button", {
      name: /Reverse this entry \(M14.4\)/i,
    });
    expect(button).toBeDisabled();
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
