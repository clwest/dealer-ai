// Milestone 14 · Increment 3 (SESSION_136) — journal-entry list page tests.

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
  };
});

import {
  fetchJournalEntries,
  type JournalEntryListEntry,
  type JournalEntryListPage,
} from "@/lib/accountingApi";
import AccountingJournalEntriesPage from "@/pages/AccountingJournalEntriesPage";


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


describe("AccountingJournalEntriesPage", () => {
  beforeEach(() => {
    vi.mocked(fetchJournalEntries).mockReset();
    vi.mocked(fetchJournalEntries).mockResolvedValue(makePage());
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
});
