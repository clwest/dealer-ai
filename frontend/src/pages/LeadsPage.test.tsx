// TASK_doors-and-matrix-refresh Part B — pins the header "Sales
// workspace" link that is the sole click-path from the sidebar
// into the /dealer-ai-sales/* cluster. Without this link none of
// the shared SalesWorkspaceNav tabs are reachable.

import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchAdminLeads: vi.fn(),
    fetchLeadDetail: vi.fn(),
  };
});

import { fetchAdminLeads } from "@/lib/api";
import LeadsPage from "@/pages/LeadsPage";

describe("LeadsPage — header link into /dealer-ai-sales/*", () => {
  beforeEach(() => {
    vi.mocked(fetchAdminLeads).mockResolvedValue({
      count: 0,
      limit: 100,
      results: [],
    });
  });

  it("renders a Sales workspace link pointing at /dealer-ai-sales/leads", async () => {
    render(
      <MemoryRouter>
        <LeadsPage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(fetchAdminLeads).toHaveBeenCalled());

    const link = screen.getByRole("link", { name: "Sales workspace" });
    expect(link).toHaveAttribute("href", "/dealer-ai-sales/leads");
  });
});
