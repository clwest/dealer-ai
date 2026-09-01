// TASK_doors-and-matrix-refresh Part B — assertions for the shared
// sales workspace nav strip. Covers the door claims for be-backs
// and test-drives (both routed but previously unlinked) plus the
// two sibling links (leads, follow-ups) that share the strip.

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { SalesWorkspaceNav } from "@/components/sales/SalesWorkspaceNav";

describe("SalesWorkspaceNav", () => {
  it("renders the four sales-workspace links with their hrefs", () => {
    render(
      <MemoryRouter>
        <SalesWorkspaceNav />
      </MemoryRouter>,
    );

    for (const [label, href] of [
      ["Leads", "/dealer-ai-sales/leads"],
      ["Follow-ups", "/dealer-ai-sales/follow-ups"],
      ["Be-backs", "/dealer-ai-sales/be-backs"],
      ["Test drives", "/dealer-ai-sales/test-drives"],
    ] as const) {
      const link = screen.getByRole("link", { name: label });
      expect(link).toHaveAttribute("href", href);
    }
  });
});
