// Milestone 33 · Increment 2 (SESSION_212) — F&I intake activation
// operational-completion journey.
//
// Guiding principle: this suite is an operational acceptance contract,
// not a UI automation project. The journey validates the M33 anchor
// business question: given a hand-off from sales, can the F&I team
// take an incoming credit application, create the first durable
// deal-structure record through the real product, and see the
// structure surface back to the intake queue as "In progress" — all
// without leaving Dealer OS?
//
// **Fixture independence guarantee per M33 §5.c R7.** This spec reads
// a pre-seeded `Structure Sam` fixture provisioned by
// `seed_journey_fandi_intake_activation` — a dedicated lead + vehicle
// + approved+handed-off writeup + paired CA (no DealStructure yet).
// Distinct rows from the M32.3 `Intake Iris` fixture; distinct rows
// from any M32.2 `Sales Sam` fixture. Test order irrelevant;
// parallelism-safe.
//
// Runs under the `f_and_i_manager` project (persona shipped M32.3;
// reused unchanged for M33.2 — no new persona work).
//
// Financial-language contract per D5 + R10: the journey asserts that
// no form or read view text matches
// /lender[- ]approved|lender[- ]committed|actual (rate|payment|apr|term|amount)/i
// across the full operator flow. Prevents accidental language drift
// in future refactors (the corresponding Vitest assertion is a belt
// over this Playwright suspenders).

import { test, expect } from "@playwright/test";

const FIXTURE_LEAD_NAME = "Structure Sam";
const FIXTURE_VEHICLE_STOCK = "FANDI-STRUCT-1";
const FORBIDDEN_LANGUAGE =
  /lender[- ]approved|lender[- ]committed|actual (rate|payment|apr|term|amount)/i;

test.describe("fandi-intake-activation", () => {
  test("F&I manager creates the first DealStructure and returns to In progress", async ({
    page,
  }) => {
    // -----------------------------------------------------------------
    // Step 1 — navigate to the F&I incoming intake page.
    // -----------------------------------------------------------------
    await page.goto("/dealer-ai-f-and-i/incoming");
    await expect(
      page.getByRole("heading", { level: 1, name: "Incoming Applications" }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("incoming-loading")).not.toBeVisible({
      timeout: 10_000,
    });

    // -----------------------------------------------------------------
    // Step 2 — locate the Structure Sam row by lead name.
    // -----------------------------------------------------------------
    const samRow = page
      .locator('[data-testid^="incoming-row-"]')
      .filter({ hasText: FIXTURE_LEAD_NAME });
    await expect(
      samRow,
      "Structure Sam fixture row should appear in F&I intake queue",
    ).toHaveCount(1, { timeout: 10_000 });

    // -----------------------------------------------------------------
    // Step 3 — assert derived-status chip = Incoming (D4). Three-signal
    // a11y: visible label + aria-label + testid double marker.
    // -----------------------------------------------------------------
    await expect(
      samRow.locator('[data-testid^="incoming-row-status-incoming-"]'),
    ).toBeVisible();
    await expect(
      samRow.getByLabel("Incoming credit application"),
    ).toBeVisible();
    await expect(samRow.getByText("Incoming").first()).toBeVisible();

    // -----------------------------------------------------------------
    // Step 4 — assert "Start structuring" available (D5 + D9) and
    // "Open structure" NOT available on Incoming rows.
    // -----------------------------------------------------------------
    const startButton = samRow.locator(
      '[data-testid^="incoming-row-start-structuring-"]',
    );
    await expect(startButton).toBeVisible();
    await expect(
      samRow.locator('[data-testid^="incoming-row-open-structure-"]'),
    ).toHaveCount(0);

    // -----------------------------------------------------------------
    // Step 5 — click "Start structuring" to open the form panel.
    // -----------------------------------------------------------------
    await startButton.click();
    const formPanel = page.getByTestId("deal-structure-form-panel");
    await expect(formPanel).toBeVisible();
    const form = page.getByTestId("deal-structure-form");
    await expect(form).toBeVisible();

    // -----------------------------------------------------------------
    // Step 6 — assert prepopulation of sales-side targets (D5).
    // Values must match the Structure Sam FIXTURE_TERMS exactly:
    // sale_price=38750.00, down=2500.00, trade_allowance=5250.00,
    // apr=7.49, term=66, monthly=520.00.
    // -----------------------------------------------------------------
    await expect(
      form.getByTestId("deal-structure-form-field-sale-price"),
    ).toHaveValue("38750.00");
    await expect(
      form.getByTestId("deal-structure-form-field-down-payment"),
    ).toHaveValue("2500.00");
    await expect(
      form.getByTestId("deal-structure-form-field-trade-allowance"),
    ).toHaveValue("5250.00");
    await expect(form.getByTestId("deal-structure-form-field-apr")).toHaveValue(
      "7.49",
    );
    await expect(
      form.getByTestId("deal-structure-form-field-term-months"),
    ).toHaveValue("66");
    await expect(
      form.getByTestId("deal-structure-form-field-monthly-payment"),
    ).toHaveValue("520.00");

    // -----------------------------------------------------------------
    // Step 7 — assert F&I fields are blank and submit is disabled.
    // Blank ≠ 0 per D5.
    // -----------------------------------------------------------------
    await expect(
      form.getByTestId("deal-structure-form-field-amount-financed"),
    ).toHaveValue("");
    await expect(
      form.getByTestId("deal-structure-form-field-taxes"),
    ).toHaveValue("");
    await expect(
      form.getByTestId("deal-structure-form-field-fees"),
    ).toHaveValue("");
    await expect(
      form.getByTestId("deal-structure-form-field-trade-payoff"),
    ).toHaveValue("");
    await expect(
      form.getByTestId("deal-structure-form-submit"),
    ).toBeDisabled();

    // -----------------------------------------------------------------
    // Step 8 — fill required F&I proposed structure values, then
    // check "No trade payoff" (D5 dedicated checkbox affordance).
    // -----------------------------------------------------------------
    await form
      .getByTestId("deal-structure-form-field-amount-financed")
      .fill("33750.00");
    await form
      .getByTestId("deal-structure-form-field-taxes")
      .fill("2531.25");
    await form
      .getByTestId("deal-structure-form-field-fees")
      .fill("799.00");
    await form
      .getByTestId("deal-structure-form-field-no-trade-payoff")
      .check();

    // Submit should now be enabled.
    await expect(
      form.getByTestId("deal-structure-form-submit"),
    ).toBeEnabled();

    // -----------------------------------------------------------------
    // Step 9 — financial-language regex assertion on the FORM. Belt
    // over the Vitest anti-drift assertion.
    // -----------------------------------------------------------------
    const formText = (await form.textContent()) ?? "";
    expect(
      formText,
      "Form must not use lender-approved / lender-committed / actual language",
    ).not.toMatch(FORBIDDEN_LANGUAGE);

    // -----------------------------------------------------------------
    // Step 10 — submit; form closes; intake list refetches.
    // -----------------------------------------------------------------
    await form.getByTestId("deal-structure-form-submit").click();
    await expect(formPanel).not.toBeVisible({ timeout: 10_000 });

    // -----------------------------------------------------------------
    // Step 11 — locate the same fixture row (re-query after refetch);
    // assert transition to In progress chip.
    // -----------------------------------------------------------------
    const samRowAfter = page
      .locator('[data-testid^="incoming-row-"]')
      .filter({ hasText: FIXTURE_LEAD_NAME });
    await expect(samRowAfter).toHaveCount(1, { timeout: 10_000 });
    await expect(
      samRowAfter.locator(
        '[data-testid^="incoming-row-status-in-progress-"]',
      ),
    ).toBeVisible();
    await expect(
      samRowAfter.getByLabel("In progress credit application"),
    ).toBeVisible();

    // Start structuring is now hidden (D9 first-loop-only).
    await expect(
      samRowAfter.locator(
        '[data-testid^="incoming-row-start-structuring-"]',
      ),
    ).toHaveCount(0);

    // -----------------------------------------------------------------
    // Step 12 — click "Open structure" to load the read view.
    // -----------------------------------------------------------------
    const openButton = samRowAfter.locator(
      '[data-testid^="incoming-row-open-structure-"]',
    );
    await expect(openButton).toBeVisible();
    await openButton.click();

    const readPanel = page.getByTestId("deal-structure-read-panel");
    await expect(readPanel).toBeVisible();
    const readView = page.getByTestId("deal-structure-read");
    await expect(readView).toBeVisible();
    await expect(
      readView.getByTestId("deal-structure-read-values-section"),
    ).toBeVisible({ timeout: 10_000 });

    // -----------------------------------------------------------------
    // Step 13 — assert read view carries the values we submitted.
    // -----------------------------------------------------------------
    await expect(
      readView.getByTestId("deal-structure-read-vehicle-stock"),
    ).toHaveText(FIXTURE_VEHICLE_STOCK);
    await expect(
      readView.getByTestId("deal-structure-read-sale-price"),
    ).toHaveText("38750.00");
    await expect(
      readView.getByTestId("deal-structure-read-amount-financed"),
    ).toHaveText("33750.00");
    await expect(
      readView.getByTestId("deal-structure-read-taxes"),
    ).toHaveText("2531.25");
    await expect(
      readView.getByTestId("deal-structure-read-fees"),
    ).toHaveText("799.00");
    await expect(
      readView.getByTestId("deal-structure-read-trade-payoff"),
    ).toHaveText("0.00");
    await expect(
      readView.getByTestId("deal-structure-read-term-months"),
    ).toHaveText("66 mo");
    // LTV should be computable (sale_price > 0). Format is
    // "<decimal>%" per the read view's nullSafeRatio helper.
    await expect(
      readView.getByTestId("deal-structure-read-ltv"),
    ).toContainText("%");

    // -----------------------------------------------------------------
    // Step 14 — financial-language regex assertion on the READ view.
    // Belt over the Vitest anti-drift assertion.
    // -----------------------------------------------------------------
    const readText = (await readView.textContent()) ?? "";
    expect(
      readText,
      "Read view must not use lender-approved / lender-committed / actual language",
    ).not.toMatch(FORBIDDEN_LANGUAGE);
    // Positive assertion — "proposed structure value" vocabulary IS
    // present at read time (all values are proposed structure values;
    // never sales targets at read time).
    expect(readText.toLowerCase()).toContain("proposed structure value");
  });
});
