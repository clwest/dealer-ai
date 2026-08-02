// Milestone 12 · Increment 7 (SESSION_127) — note-detail tests.

import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/bhphApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/bhphApi")>(
    "@/lib/bhphApi",
  );
  return {
    ...actual,
    getBhphNote: vi.fn(),
    listBhphPayments: vi.fn(),
    listBhphPromises: vi.fn(),
    listCollectionContacts: vi.fn(),
    listRepossessions: vi.fn(),
  };
});

import {
  getBhphNote,
  listBhphPayments,
  listBhphPromises,
  listCollectionContacts,
  listRepossessions,
} from "@/lib/bhphApi";
import DealerAiBhphNoteDetail from "@/pages/DealerAiBhphNoteDetail";


async function renderPage(pk: string = "1") {
  const view = render(
    <MemoryRouter initialEntries={[`/dealer-ai-bhph/notes/${pk}`]}>
      <Routes>
        <Route
          path="/dealer-ai-bhph/notes/:pk"
          element={<DealerAiBhphNoteDetail />}
        />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => {
    expect(getBhphNote).toHaveBeenCalled();
  });
  return view;
}


describe("DealerAiBhphNoteDetail", () => {
  beforeEach(() => {
    vi.mocked(getBhphNote).mockResolvedValue({
      bhph_note: {
        id: 42,
        sale_id: 100,
        dealership_id: 1,
        principal_financed: "8000.00",
        apr: "21.90",
        term_weeks: 104,
        payment_frequency: "weekly",
        payment_amount: "95.00",
        first_payment_due: "2026-09-01",
        default_grace_days: 5,
        current_bucket: "current",
        days_past_due: 0,
        created_at: "2026-08-01T00:00:00Z",
        updated_at: "2026-08-01T00:00:00Z",
      },
      payment_schedule: [
        { due_date: "2026-09-01", amount: "95.00" },
        { due_date: "2026-09-08", amount: "95.00" },
      ],
    });
    vi.mocked(listBhphPayments).mockResolvedValue({
      count: 0,
      results: [],
    });
    vi.mocked(listBhphPromises).mockResolvedValue({
      count: 0,
      results: [],
    });
    vi.mocked(listCollectionContacts).mockResolvedValue({
      count: 0,
      results: [],
    });
    vi.mocked(listRepossessions).mockResolvedValue({
      count: 0,
      results: [],
    });
  });

  it("renders the note ID in the header", async () => {
    await renderPage("42");
    expect(screen.getByText(/BHPH Note #42/i)).toBeInTheDocument();
  });

  it("fetches all five sub-lists on mount", async () => {
    await renderPage();
    await waitFor(() => {
      expect(listBhphPayments).toHaveBeenCalledWith(1);
      expect(listBhphPromises).toHaveBeenCalledWith(1);
      expect(listCollectionContacts).toHaveBeenCalledWith(1);
      expect(listRepossessions).toHaveBeenCalledWith(1);
    });
  });

  it("renders empty-state messages when no sub-data", async () => {
    await renderPage();
    expect(
      screen.getByText(/No payments recorded/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No promises on file/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No collection contacts logged/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No repossessions on file/i),
    ).toBeInTheDocument();
  });

  it("shows error when the note lookup fails", async () => {
    vi.mocked(getBhphNote).mockRejectedValueOnce(
      new Error("Note not found."),
    );
    render(
      <MemoryRouter initialEntries={[`/dealer-ai-bhph/notes/999`]}>
        <Routes>
          <Route
            path="/dealer-ai-bhph/notes/:pk"
            element={<DealerAiBhphNoteDetail />}
          />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("Note not found.")).toBeInTheDocument();
    });
  });
});
