// Milestone 33 · Increment 2 (SESSION_212) — DealStructureForm tests.
//
// Locks the D5 truthful-entry contract from
// MILESTONE_33_PLANNING.md §5.b:
//
// - Prepopulation from writeup context for sales-side targets.
// - `amount_financed` / `taxes` / `fees` blank on load and required
//   before submit.
// - `trade_payoff` requires either explicit numeric entry OR the
//   "No trade payoff" checkbox (untouched blank blocks submit).
// - Blank ≠ 0 anywhere on financial fields.
// - Submit-gate wires reason messages.
// - Consistency warning fires when `trade_payoff > 0` with
//   `trade_allowance == 0`.
// - Financial-language contract: no "lender-approved" /
//   "lender-committed" / "actual" anywhere in the DOM.
// - Submit path calls the API wrapper with the full payload.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DealStructureForm } from "@/components/f-and-i/DealStructureForm";
import type {
  CreditApplicationWriteupContext,
  DealStructureProjection,
} from "@/lib/fAndIApi";

function fixtureCtx(
  overrides: Partial<CreditApplicationWriteupContext> = {},
): CreditApplicationWriteupContext {
  return {
    deal_writeup_id: 42,
    written_up_by_user_id: 5,
    sales_manager_approved_by_user_id: 5,
    handed_off_to_fandi_at: "2026-08-04T12:00:00Z",
    lead: {
      id: 100,
      name: "Structure Sam",
      phone: "+15553301502",
      email: "structure-sam@example.com",
    },
    vehicle: {
      id: 200,
      stock_number: "FANDI-STRUCT-1",
      year: 2024,
      make: "Ford",
      model: "Bronco",
    },
    terms: {
      vehicle_price: "38750.00",
      trade_allowance: "5250.00",
      down_payment: "2500.00",
      monthly_payment_target: "520.00",
      term_months_target: 66,
      apr_target: "7.49",
    },
    ...overrides,
  };
}

function fixtureCreatedDeal(): DealStructureProjection {
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
    monthly_payment: "520.00",
    back_end_products: [],
    ltv_pct: "89.03",
    pti_pct: "12.00",
    dti_pct: "30.00",
    created_at: "2026-08-04T18:00:00Z",
    updated_at: "2026-08-04T18:00:00Z",
  };
}

describe("DealStructureForm — prepopulation from writeup context", () => {
  it("populates sales-side targets from writeup_context.terms", () => {
    render(
      <DealStructureForm
        creditApplicationId={42}
        writeupContext={fixtureCtx()}
        onCreated={vi.fn()}
      />,
    );
    expect(
      screen.getByTestId("deal-structure-form-field-sale-price"),
    ).toHaveValue("38750.00");
    expect(
      screen.getByTestId("deal-structure-form-field-down-payment"),
    ).toHaveValue("2500.00");
    expect(
      screen.getByTestId("deal-structure-form-field-trade-allowance"),
    ).toHaveValue("5250.00");
    expect(
      screen.getByTestId("deal-structure-form-field-apr"),
    ).toHaveValue("7.49");
    expect(
      screen.getByTestId("deal-structure-form-field-term-months"),
    ).toHaveValue("66");
    expect(
      screen.getByTestId("deal-structure-form-field-monthly-payment"),
    ).toHaveValue("520.00");
  });

  it("leaves amount_financed, taxes, fees, trade_payoff blank on load (blank ≠ 0)", () => {
    render(
      <DealStructureForm
        creditApplicationId={42}
        writeupContext={fixtureCtx()}
        onCreated={vi.fn()}
      />,
    );
    expect(
      screen.getByTestId("deal-structure-form-field-amount-financed"),
    ).toHaveValue("");
    expect(screen.getByTestId("deal-structure-form-field-taxes")).toHaveValue(
      "",
    );
    expect(screen.getByTestId("deal-structure-form-field-fees")).toHaveValue(
      "",
    );
    expect(
      screen.getByTestId("deal-structure-form-field-trade-payoff"),
    ).toHaveValue("");
  });
});

describe("DealStructureForm — submit gate", () => {
  it("disables submit on load until all required F&I fields are filled", () => {
    render(
      <DealStructureForm
        creditApplicationId={42}
        writeupContext={fixtureCtx()}
        onCreated={vi.fn()}
      />,
    );
    expect(
      screen.getByTestId("deal-structure-form-submit"),
    ).toBeDisabled();
    // Reasons list should surface every missing field.
    const reasons = screen.getByTestId(
      "deal-structure-form-missing-reasons",
    );
    expect(reasons.textContent).toContain("Enter amount financed.");
    expect(reasons.textContent).toContain("Enter taxes.");
    expect(reasons.textContent).toContain("Enter fees.");
    expect(reasons.textContent).toContain("Confirm trade payoff");
  });

  it("still disabled after amount/taxes/fees filled but trade_payoff untouched", async () => {
    render(
      <DealStructureForm
        creditApplicationId={42}
        writeupContext={fixtureCtx()}
        onCreated={vi.fn()}
      />,
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-amount-financed"),
      "34499.00",
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-taxes"),
      "2800.00",
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-fees"),
      "699.00",
    );
    // Trade payoff still untouched — submit still disabled with the
    // confirm-trade-payoff reason.
    expect(
      screen.getByTestId("deal-structure-form-submit"),
    ).toBeDisabled();
    expect(
      screen.getByTestId("deal-structure-form-missing-reasons").textContent,
    ).toContain("Confirm trade payoff");
  });

  it("enables submit when 'No trade payoff' checkbox is checked", async () => {
    render(
      <DealStructureForm
        creditApplicationId={42}
        writeupContext={fixtureCtx()}
        onCreated={vi.fn()}
      />,
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-amount-financed"),
      "34499.00",
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-taxes"),
      "2800.00",
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-fees"),
      "699.00",
    );
    await userEvent.click(
      screen.getByTestId("deal-structure-form-field-no-trade-payoff"),
    );
    expect(
      screen.getByTestId("deal-structure-form-submit"),
    ).toBeEnabled();
  });

  it("enables submit when trade_payoff receives an explicit numeric value", async () => {
    render(
      <DealStructureForm
        creditApplicationId={42}
        writeupContext={fixtureCtx()}
        onCreated={vi.fn()}
      />,
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-amount-financed"),
      "34499.00",
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-taxes"),
      "2800.00",
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-fees"),
      "699.00",
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-trade-payoff"),
      "1200.00",
    );
    expect(
      screen.getByTestId("deal-structure-form-submit"),
    ).toBeEnabled();
  });

  it("accepts explicit 0 as a valid confirmed value (blank ≠ 0)", async () => {
    render(
      <DealStructureForm
        creditApplicationId={42}
        writeupContext={fixtureCtx()}
        onCreated={vi.fn()}
      />,
    );
    // Explicit 0 satisfies the "explicit-entry" contract for
    // amount_financed / taxes / fees just like any other value.
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-amount-financed"),
      "0",
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-taxes"),
      "0",
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-fees"),
      "0",
    );
    await userEvent.click(
      screen.getByTestId("deal-structure-form-field-no-trade-payoff"),
    );
    expect(
      screen.getByTestId("deal-structure-form-submit"),
    ).toBeEnabled();
  });
});

describe("DealStructureForm — consistency warning (D5)", () => {
  it("fires warning when trade_payoff > 0 with trade_allowance == 0", async () => {
    render(
      <DealStructureForm
        creditApplicationId={42}
        writeupContext={fixtureCtx({
          terms: {
            vehicle_price: "38750.00",
            trade_allowance: "0",
            down_payment: "2500.00",
            monthly_payment_target: "520.00",
            term_months_target: 66,
            apr_target: "7.49",
          },
        })}
        onCreated={vi.fn()}
      />,
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-trade-payoff"),
      "1200.00",
    );
    await waitFor(() =>
      expect(
        screen.getByTestId("deal-structure-form-consistency-warning"),
      ).toBeInTheDocument(),
    );
    // Warning is non-blocking — does not affect the submit gate on
    // its own.
    expect(
      screen.getByTestId("deal-structure-form-consistency-warning").textContent,
    ).toMatch(/Trade payoff entered without a trade allowance/);
  });

  it("does not fire the warning when both trade fields are populated", async () => {
    render(
      <DealStructureForm
        creditApplicationId={42}
        writeupContext={fixtureCtx()}
        onCreated={vi.fn()}
      />,
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-trade-payoff"),
      "1200.00",
    );
    // trade_allowance prepopulated to 5250.00 from fixture — no warning.
    expect(
      screen.queryByTestId("deal-structure-form-consistency-warning"),
    ).toBeNull();
  });
});

describe("DealStructureForm — submit path", () => {
  it("calls submit with the full payload including trade_payoff=0.00 when checkbox is used", async () => {
    const submit = vi.fn().mockResolvedValueOnce(fixtureCreatedDeal());
    const onCreated = vi.fn();
    render(
      <DealStructureForm
        creditApplicationId={42}
        writeupContext={fixtureCtx()}
        onCreated={onCreated}
        submit={submit}
      />,
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-amount-financed"),
      "34499.00",
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-taxes"),
      "2800.00",
    );
    await userEvent.type(
      screen.getByTestId("deal-structure-form-field-fees"),
      "699.00",
    );
    await userEvent.click(
      screen.getByTestId("deal-structure-form-field-no-trade-payoff"),
    );
    await userEvent.click(
      screen.getByTestId("deal-structure-form-submit"),
    );
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    const payload = submit.mock.calls[0][0];
    expect(payload.credit_application_id).toBe(42);
    expect(payload.vehicle_stock).toBe("FANDI-STRUCT-1");
    expect(payload.sale_price).toBe("38750.00");
    expect(payload.amount_financed).toBe("34499.00");
    expect(payload.taxes).toBe("2800.00");
    expect(payload.fees).toBe("699.00");
    expect(payload.trade_payoff).toBe("0.00");
    expect(payload.term_months).toBe(66);
    expect(payload.apr).toBe("7.49");
    // back_end_products intentionally omitted per §5.b D5.
    expect(payload.back_end_products).toBeUndefined();
    // onCreated fires with the created deal.
    expect(onCreated).toHaveBeenCalledWith(fixtureCreatedDeal());
  });
});

describe("DealStructureForm — financial-language contract (D5 + R10)", () => {
  it("no 'lender-approved' / 'lender-committed' / 'actual' vocabulary anywhere in the form", () => {
    // Belt over the Playwright regex assertion at D8. If any future
    // refactor drifts into lender-outcome language before a
    // LenderSubmission entity exists, this test surfaces it in
    // Vitest before Playwright.
    const { container } = render(
      <DealStructureForm
        creditApplicationId={42}
        writeupContext={fixtureCtx()}
        onCreated={vi.fn()}
      />,
    );
    const text = container.textContent ?? "";
    expect(text).not.toMatch(/lender[- ]approved/i);
    expect(text).not.toMatch(/lender[- ]committed/i);
    expect(text).not.toMatch(/actual (rate|payment|apr|term|amount)/i);
    // Positive assertions — the intended vocabulary IS present.
    expect(text.toLowerCase()).toContain("sales-side targets");
    expect(text.toLowerCase()).toContain("proposed structure values");
  });
});
