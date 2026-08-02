// Milestone 11 · Increment 6 (SESSION_119) — DealerAiSalesFollowUps tests.

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
    listFollowUpTasks: vi.fn(),
    completeTask: vi.fn(),
    skipTask: vi.fn(),
  };
});

import {
  completeTask,
  listFollowUpTasks,
  skipTask,
  type FollowUpTaskProjection,
} from "@/lib/salesApi";
import DealerAiSalesFollowUps from "@/pages/DealerAiSalesFollowUps";


function makeTask(overrides: Partial<FollowUpTaskProjection> = {}): FollowUpTaskProjection {
  return {
    id: 1,
    cadence_id: 42,
    dealership_id: 1,
    due_at: "2026-08-02T15:00:00Z",
    state: "pending",
    completed_by_user_id: null,
    completed_at: null,
    notes: "",
    created_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T00:00:00Z",
    ...overrides,
  };
}

async function renderPage() {
  const view = render(
    <MemoryRouter initialEntries={["/dealer-ai-sales/follow-ups"]}>
      <Routes>
        <Route
          path="/dealer-ai-sales/follow-ups"
          element={<DealerAiSalesFollowUps />}
        />
      </Routes>
    </MemoryRouter>,
  );
  await waitFor(() => {
    expect(listFollowUpTasks).toHaveBeenCalled();
  });
  return view;
}


describe("DealerAiSalesFollowUps", () => {
  beforeEach(() => {
    vi.mocked(listFollowUpTasks).mockResolvedValue({
      count: 2,
      results: [
        makeTask({ id: 1, state: "pending" }),
        makeTask({ id: 2, state: "completed", cadence_id: 43 }),
      ],
    });
    vi.mocked(completeTask).mockResolvedValue(
      makeTask({ id: 1, state: "completed" }),
    );
    vi.mocked(skipTask).mockResolvedValue(
      makeTask({ id: 1, state: "skipped" }),
    );
  });

  afterEach(() => vi.clearAllMocks());

  it("renders every task with its cadence + state", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("#42")).toBeInTheDocument();
    });
    expect(screen.getByText("#43")).toBeInTheDocument();
  });

  it("shows action buttons only for pending tasks", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("#42")).toBeInTheDocument();
    });
    // Exactly one row is pending; that row has Complete + Skip.
    expect(screen.getAllByRole("button", { name: /complete/i })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: /skip/i })).toHaveLength(1);
  });

  it("completes a task optimistically", async () => {
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText("#42")).toBeInTheDocument();
    });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /complete/i }));
    await waitFor(() => {
      expect(completeTask).toHaveBeenCalledWith(1);
    });
  });

  it("refetches when the state filter changes", async () => {
    await renderPage();
    await waitFor(() => {
      expect(listFollowUpTasks).toHaveBeenCalledTimes(1);
    });
    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByLabelText(/state filter/i),
      "completed",
    );
    await waitFor(() => {
      expect(listFollowUpTasks).toHaveBeenCalledTimes(2);
    });
    expect(listFollowUpTasks).toHaveBeenLastCalledWith(
      expect.objectContaining({ state: "completed" }),
    );
  });

  it("shows empty state when the queue is clear", async () => {
    vi.mocked(listFollowUpTasks).mockResolvedValue({ count: 0, results: [] });
    await renderPage();
    await waitFor(() => {
      expect(screen.getByText(/queue is clear/i)).toBeInTheDocument();
    });
  });
});
