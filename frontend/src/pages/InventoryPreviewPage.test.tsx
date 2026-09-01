// TASK_doors-and-matrix-refresh Part B — Photos / Listing / Sale
// links must render on the vehicle detail row. Ledger + Condition
// Report + Recon were already there and are asserted alongside to
// pin the shape of the row.

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import InventoryPreviewPage from "@/pages/InventoryPreviewPage";
import { SAMPLE_INVENTORY } from "@/data/sampleInventory";

function renderPage() {
  return render(
    <MemoryRouter>
      <InventoryPreviewPage />
    </MemoryRouter>,
  );
}

describe("InventoryPreviewPage — vehicle-detail action row", () => {
  it("renders Ledger, Condition Report, Recon, Photos, Listing and Sale links for every vehicle card", () => {
    renderPage();
    const first = SAMPLE_INVENTORY[0];
    const stock = encodeURIComponent(first.stock_number);

    for (const [label, href] of [
      ["Ledger", `/dealer-ai-inventory/${stock}/ledger`],
      ["Condition Report", `/dealer-ai-inventory/${stock}/condition-report`],
      ["Recon", `/dealer-ai-inventory/${stock}/recon`],
      ["Photos", `/dealer-ai-inventory/${stock}/photos`],
      ["Listing", `/dealer-ai-inventory/${stock}/listing`],
      ["Sale", `/dealer-ai-inventory/${stock}/sale`],
    ] as const) {
      const link = screen.getAllByRole("link", { name: label })[0];
      expect(link).toBeDefined();
      expect(link).toHaveAttribute("href", href);
    }
  });
});
