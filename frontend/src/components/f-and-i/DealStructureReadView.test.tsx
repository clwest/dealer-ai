// Milestone 33 · Increment 2 (SESSION_212) — DealStructureReadView
// tests per MILESTONE_33_PLANNING.md §5.b D6.

import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DealStructureReadView } from "@/components/f-and-i/DealStructureReadView";
import { ApiError } from "@/lib/authFetch";
import type { DealStructureProjection } from "@/lib/fAndIApi";

function fixtureDeal(
  overrides: Partial<DealStructureProjection> = {},
): DealStructureProjection {
  return {
    id: 77,
    credit_application_id: 42,
    vehicle_stock: "FANDI-STRUCT-1",
    sale_price: "38750.00",
    down_payment: "2500.00",
    trade_allowance: "5250.00",
    trade_payoff: "0.00",
    taxes: "2800.00",
    fees: "699.00",
    amount_financed: "34499.00",
    apr: "7.4900",
    term_months: 66,
    monthly_payment: "600.00",
    back_end_products: [],
    ltv_pct: "89.03",
    pti_pct: "12.00",
    dti_pct: "30.00",
    created_at: "2026-08-04T18:00:00Z",
    updated_at: "2026-08-04T18:00:00Z",
    ...overrides,
  };
}

describe("DealStructureReadView", () => {
  it("renders every projected value in the ready state", async () => {
    const load = vi.fn().mockResolvedValueOnce(fixtureDeal());
    render(
      <DealStructureReadView dealStructureId={77} load={load} />,
    );
    await waitFor(() =>
      expect(
        screen.getByTestId("deal-structure-read-values-section"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("deal-structure-read-vehicle-stock"))
      .toHaveTextContent("FANDI-STRUCT-1");
    expect(screen.getByTestId("deal-structure-read-sale-price"))
      .toHaveTextContent("38750.00");
    expect(screen.getByTestId("deal-structure-read-amount-financed"))
      .toHaveTextContent("34499.00");
    expect(screen.getByTestId("deal-structure-read-apr"))
      .toHaveTextContent("7.4900%");
    expect(screen.getByTestId("deal-structure-read-term-months"))
      .toHaveTextContent("66 mo");
    expect(screen.getByTestId("deal-structure-read-monthly-payment"))
      .toHaveTextContent("600.00");
    expect(screen.getByTestId("deal-structure-read-ltv"))
      .toHaveTextContent("89.03%");
  });

  it("renders NULL-safe placeholders for null ratios", async () => {
    const load = vi.fn().mockResolvedValueOnce(
      fixtureDeal({ pti_pct: null, dti_pct: null }),
    );
    render(
      <DealStructureReadView dealStructureId={77} load={load} />,
    );
    await waitFor(() =>
      expect(
        screen.getByTestId("deal-structure-read-ratios-section"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("deal-structure-read-pti"))
      .toHaveTextContent(/Not computable — requires income/);
    expect(screen.getByTestId("deal-structure-read-dti"))
      .toHaveTextContent(/Not computable — requires income/);
    // LTV still renders because sale_price > 0.
    expect(screen.getByTestId("deal-structure-read-ltv"))
      .toHaveTextContent("89.03%");
  });

  it("renders 404 error state when fetch fails", async () => {
    const load = vi.fn().mockRejectedValueOnce(new ApiError(404, "nf"));
    render(
      <DealStructureReadView dealStructureId={999} load={load} />,
    );
    await waitFor(() =>
      expect(
        screen.getByTestId("deal-structure-read-error"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByText(/Deal structure not found in your dealership/),
    ).toBeInTheDocument();
  });

  it("financial-language contract: no 'lender-approved' / 'lender-committed' / 'actual' vocabulary in read view", async () => {
    // R10 mitigation — belt over the Playwright regex assertion at D8.
    const load = vi.fn().mockResolvedValueOnce(fixtureDeal());
    const { container } = render(
      <DealStructureReadView dealStructureId={77} load={load} />,
    );
    await waitFor(() =>
      expect(
        screen.getByTestId("deal-structure-read-values-section"),
      ).toBeInTheDocument(),
    );
    const text = container.textContent ?? "";
    expect(text).not.toMatch(/lender[- ]approved/i);
    expect(text).not.toMatch(/lender[- ]committed/i);
    expect(text).not.toMatch(/actual (rate|payment|apr|term|amount)/i);
    // But "proposed" language must be present — every value should
    // be framed as a proposed structure value.
    expect(text.toLowerCase()).toContain("proposed structure value");
  });
});
