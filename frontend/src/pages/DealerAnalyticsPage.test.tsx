// Milestone 8 · Increment 5 (SESSION_098) — DealerAnalyticsPage tests.
//
// Page-level render + tab-switching smoke tests. Each tab's internal
// data-fetching + rendering is covered separately (see
// AcquisitionReconTab.test.tsx et al.), so this file mocks the tab
// components to avoid firing every endpoint under test.

import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

// Stub every tab body so the page-level test doesn't trip fetch or
// pull in recharts — the tab-body content is exercised by each
// tab's own test file. We just want to see that the tab shell
// wires up correctly.
vi.mock("@/components/analytics/AcquisitionReconTab", () => ({
  AcquisitionReconTab: () => <div>MOCK-acquisition</div>,
}));
vi.mock("@/components/analytics/VendorPerformanceTab", () => ({
  VendorPerformanceTab: () => <div>MOCK-vendor</div>,
}));
vi.mock("@/components/analytics/LifecycleAgingTab", () => ({
  LifecycleAgingTab: () => <div>MOCK-aging</div>,
}));
vi.mock("@/components/analytics/SlaBreachTab", () => ({
  SlaBreachTab: () => <div>MOCK-sla</div>,
}));
vi.mock("@/components/analytics/RealizedGrossTab", () => ({
  RealizedGrossTab: () => <div>MOCK-realized-gross</div>,
}));

// Reset the URL hash between tests — the page reads it on mount to
// resolve the initial tab.
afterEach(() => {
  window.location.hash = "";
});

async function renderPage() {
  const mod = await import("@/pages/DealerAnalyticsPage");
  render(<mod.default />);
}

describe("DealerAnalyticsPage", () => {
  it("renders all five tab triggers", async () => {
    await renderPage();
    expect(
      screen.getByRole("tab", { name: /acquisition & recon cost/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: /vendor performance/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: /lifecycle aging/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: /sla breach patterns/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: /realized gross/i }),
    ).toBeInTheDocument();
  });

  it("honors the realized-gross URL hash on first mount", async () => {
    window.location.hash = "#realized-gross";
    await renderPage();
    expect(screen.getByText("MOCK-realized-gross")).toBeInTheDocument();
  });

  it("defaults to the Acquisition & Recon Cost tab", async () => {
    await renderPage();
    expect(screen.getByText("MOCK-acquisition")).toBeInTheDocument();
    // The other tab bodies must NOT render — Radix uses
    // aria-hidden on inactive panels, so their content should be
    // absent from the accessibility tree via queryByText.
    expect(screen.queryByText("MOCK-vendor")).not.toBeInTheDocument();
  });

  it("switches the active tab body on click", async () => {
    const user = userEvent.setup();
    await renderPage();
    await user.click(
      screen.getByRole("tab", { name: /vendor performance/i }),
    );
    expect(screen.getByText("MOCK-vendor")).toBeInTheDocument();
  });

  it("honors the URL hash on first mount", async () => {
    window.location.hash = "#sla";
    await renderPage();
    expect(screen.getByText("MOCK-sla")).toBeInTheDocument();
  });
});
