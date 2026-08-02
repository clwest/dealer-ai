// Milestone 11 · Increment 6 (SESSION_119) — DealerAiSalesBeBacks tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/salesApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/salesApi")>(
    "@/lib/salesApi",
  );
  return {
    ...actual,
    listBeBacks: vi.fn(),
    markBeBackReturned: vi.fn(),
    markBeBackNoShow: vi.fn(),
  };
});

import {
  listBeBacks,
  markBeBackNoShow,
  markBeBackReturned,
  type BeBackProjection,
} from "@/lib/salesApi";
import DealerAiSalesBeBacks from "@/pages/DealerAiSalesBeBacks";


function makeBeBack(overrides: Partial<BeBackProjection> = {}): BeBackProjection {
  return {
    id: 1,
    lead_id: 42,
    dealership_id: 1,
    promised_at: "2026-08-03T14:00:00Z",
    promised_reason: "test_drive",
    actual_return_at: null,
    state: "promised",
    notes: "",
    created_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T00:00:00Z",
    ...overrides,
  };
}

async function renderPage() {
  const view = render(
    <MemoryRouter initialEntries={["/dealer-ai-sales/be-backs"]}>
      <Routes>
        <Route
          path="/dealer-ai-sales/be-backs"
          element={<DealerAiSalesBeBacks />}
        />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => {
    expect(listBeBacks).toHaveBeenCalled();
  });
  return view;
}


describe("DealerAiSalesBeBacks", () => {
  beforeEach(() => {
    vi.mocked(listBeBacks).mockResolvedValue({
      count: 2,
      results: [
        makeBeBack({ id: 1, state: "promised" }),
        makeBeBack({
          id: 2,
          state: "returned",
          actual_return_at: "2026-08-03T15:30:00Z",
        }),
      ],
    });
    vi.mocked(markBeBackReturned).mockResolvedValue(
      makeBeBack({ id: 1, state: "returned" }),
    );
    vi.mocked(markBeBackNoShow).mockResolvedValue(
      makeBeBack({ id: 1, state: "no_show" }),
    );
  });

  afterEach(() => vi.clearAllMocks());

  it("renders every be-back with its state + reason", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getAllByText("#42").length).toBe(2);
    });
    expect(screen.getByText("promised")).toBeInTheDocument();
    expect(screen.getByText("returned")).toBeInTheDocument();
    expect(screen.getAllByText("test_drive").length).toBe(2);
  });

  it("marks a be-back returned via the inline button", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("promised")).toBeInTheDocument();
    });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^returned$/i }));
    await waitFor(() => {
      expect(markBeBackReturned).toHaveBeenCalledWith(1);
    });
  });

  it("marks a be-back no-show via the inline button", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("promised")).toBeInTheDocument();
    });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /no-show/i }));
    await waitFor(() => {
      expect(markBeBackNoShow).toHaveBeenCalledWith(1);
    });
  });

  it("refetches when the state filter changes", async () => {
    await renderPage();
    await waitFor(() => {
      expect(listBeBacks).toHaveBeenCalledTimes(1);
    });
    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByLabelText(/be-back state filter/i),
      "no_show",
    );
    await waitFor(() => {
      expect(listBeBacks).toHaveBeenCalledTimes(2);
    });
    expect(listBeBacks).toHaveBeenLastCalledWith(
      expect.objectContaining({ state: "no_show" }),
    );
  });
});
