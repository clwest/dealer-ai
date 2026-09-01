// TASK_losing-deals-and-the-inventory-page (2026-09-01) — the page
// used to import a static twelve-car sample module. Its test asserted
// the six operator door links (Ledger / Condition Report / Recon /
// Photos / Listing / Sale) render on the sample rows. Rewired to
// exercise the backend-fed shape and pass a mocked `loadInventory`
// so the same door-link shape is still guarded.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import InventoryPreviewPage from "@/pages/InventoryPreviewPage";
import type { AdminVehicleListResponse } from "@/lib/salesApi";

function makeRow(overrides: Partial<AdminVehicleListResponse["results"][number]> = {}) {
  return {
    id: 1,
    stock_number: "RS-07",
    year: 2016,
    make: "Nissan",
    model: "Rogue",
    trim: "SV",
    condition: "used",
    price: "12500.00",
    image_url: "",
    is_available: true,
    display_name: "2016 Nissan Rogue SV",
    ...overrides,
  };
}

function makeResponse(
  overrides: Partial<AdminVehicleListResponse> = {},
): AdminVehicleListResponse {
  return {
    count: 1,
    limit: 24,
    offset: 0,
    next: null,
    previous: null,
    has_more: false,
    results: [makeRow()],
    ...overrides,
  };
}

function renderPage(loadInventory = vi.fn().mockResolvedValue(makeResponse())) {
  return {
    loadInventory,
    ...render(
      <MemoryRouter>
        <InventoryPreviewPage loadInventory={loadInventory} />
      </MemoryRouter>,
    ),
  };
}

describe("InventoryPreviewPage — backend wiring", () => {
  it("renders Ledger, Condition Report, Recon, Photos, Listing and Sale links for every vehicle card", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Ledger" })).toBeInTheDocument();
    });
    const stock = encodeURIComponent("RS-07");
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

  it("defaults the availability filter to Available and calls the API with is_available=true", async () => {
    const { loadInventory } = renderPage();
    await waitFor(() => expect(loadInventory).toHaveBeenCalled());
    expect(loadInventory).toHaveBeenCalledWith(
      expect.objectContaining({ is_available: true, limit: 24, offset: 0 }),
    );
  });

  it("shows an error surface when the backend rejects", async () => {
    const loadInventory = vi
      .fn()
      .mockRejectedValue(new Error("Server unavailable"));
    renderPage(loadInventory);
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Server unavailable",
      );
    });
  });

  it("reports the real total from `count` and honours pagination", async () => {
    const loadInventory = vi.fn().mockResolvedValue(
      makeResponse({
        count: 130,
        limit: 24,
        offset: 0,
        next: "http://testserver/admin/vehicles/?limit=24&offset=24",
        has_more: true,
      }),
    );
    renderPage(loadInventory);
    await waitFor(() => {
      expect(screen.getByText(/Showing 1–1 of 130/i)).toBeInTheDocument();
    });
    // Second-page click advances the offset in the request.
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /Next/i }));
    await waitFor(() => {
      expect(loadInventory).toHaveBeenCalledWith(
        expect.objectContaining({ offset: 24, limit: 24 }),
      );
    });
  });
});
