// Milestone 24 · Increment 3 (SESSION_183) — referral intake journey.
//
// Guiding principle: this suite is an operational acceptance contract,
// not a UI automation project. The journey validates that a sales
// operator can capture a referral customer through the real UI on
// /dealer-ai-sales/leads with the correct referring-customer link,
// then assign the new lead through the shipped operator workflow.
//
// Per MILESTONE_24_PLANNING.md §5.d Option C (referral row): scope
// is intake with referring-customer picker → list channel visibility
// → open LeadDetailModal → assign. Backend attribution verified via
// API-side assertion since LeadDetailModal does not currently display
// referrer_id (deferred per M24 §3 deferral 13 to M25).
//
// Seeded state (via seed_journey_sales_operational_entry +
// seed_journey_sales_manager_daily_startup):
// - `acceptance-sales-manager` user (sales_manager @ default
//   dealership) — auth persona via storage state
// - `Acceptance Advisor` (M20 seed's Salesperson) — assignment target
// - `Priya Prior-Customer` (M24.1 seed's referring-customer fixture,
//   walk-in channel) — the picker target
//
// Journey steps:
// 1. Look up Priya's id via the admin API (findSeededLead) so the
//    referrer assertion at step 13 has a stable id to compare
//    against — the seed re-creates Priya on --reset so her pk shifts
//    across suite runs.
// 2. Navigate to /dealer-ai-sales/leads.
// 3. Click `+ Referral` CTA — Dialog opens.
// 4. In the picker, search for "Priya" and pick her match row.
// 5. Assert the picker's "selected" chip appears with Priya's name.
// 6. Fill the LeadIntakeForm base fields with a unique per-run
//    customer name.
// 7. Submit — Dialog closes, LeadDetailModal opens for the new lead.
// 8. Extract the new lead's id from the modal header.
// 9. Assign "Acceptance Advisor" via AssignmentDropdown.
// 10. Business-outcome assertions via admin API: new lead exists +
//     assigned to Acceptance Advisor + channel="referral" + referrer
//     FK matches Priya's id.
// 11. Reload → assert list row for new lead shows channel="referral".

import { test, expect } from "@playwright/test";

import {
  expectLeadAssignedTo,
  findSeededLead,
} from "../../support/assertions/dashboard";

test.describe("Sales operator can record a referral customer with backend attribution linked", () => {
  test("referral intake with picker → LeadDetailModal → assign lands as a business outcome + referrer FK persists", async ({
    page,
    request,
  }) => {
    const ADVISOR_NAME = "Acceptance Advisor";
    const REFERRER_NAME = "Priya Prior-Customer";
    // Unique per-run customer name.
    const CUSTOMER_NAME = `M24.3 Referral Reggie ${Date.now()}`;
    const CUSTOMER_PHONE = "+15551243003";
    const CUSTOMER_EMAIL = "m243-referral-reggie@example.com";

    // ---------------------------------------------------------------
    // Step 1 — look up the seeded referring customer's id.
    // ---------------------------------------------------------------
    const referrer = await findSeededLead(request, REFERRER_NAME, {
      limit: 200,
    });
    expect(referrer.id, "seeded Priya should have a stable id").toBeGreaterThan(
      0,
    );

    // ---------------------------------------------------------------
    // Step 2 — navigate to the sales-side leads page.
    // ---------------------------------------------------------------
    await page.goto("/dealer-ai-sales/leads");
    await expect(
      page.getByRole("heading", { level: 1, name: "Sales leads" }),
    ).toBeVisible({ timeout: 15_000 });

    // ---------------------------------------------------------------
    // Step 3 — click + Referral CTA. Dialog opens.
    // ---------------------------------------------------------------
    await page.getByTestId("sales-leads-add-referral").click();
    await expect(
      page.getByTestId("sales-leads-referral-dialog"),
      "referral Dialog should open after clicking + Referral",
    ).toBeVisible({ timeout: 10_000 });

    // ---------------------------------------------------------------
    // Step 4 — search for Priya in the picker + click her match row.
    //          Match row testid is `referral-lead-form-extras-match-<id>`
    //          per the component's testid convention.
    // ---------------------------------------------------------------
    await page
      .getByTestId("referral-lead-form-extras-search")
      .fill("Priya");
    const matchRow = page.getByTestId(
      `referral-lead-form-extras-match-${referrer.id}`,
    );
    await expect(
      matchRow,
      `Priya's picker match row (id=${referrer.id}) should appear after searching`,
    ).toBeVisible({ timeout: 10_000 });
    await matchRow.click();

    // ---------------------------------------------------------------
    // Step 5 — assert the "selected" chip appears with Priya's name.
    // ---------------------------------------------------------------
    const selectedChip = page.getByTestId(
      "referral-lead-form-extras-selected",
    );
    await expect(
      selectedChip,
      "selected-referrer chip should appear after picking Priya",
    ).toBeVisible({ timeout: 5_000 });
    await expect(selectedChip).toContainText(REFERRER_NAME);

    // ---------------------------------------------------------------
    // Step 6 — fill the LeadIntakeForm base fields (channel="referral").
    // ---------------------------------------------------------------
    await page
      .getByTestId("lead-intake-referral-name")
      .fill(CUSTOMER_NAME);
    await page
      .getByTestId("lead-intake-referral-phone")
      .fill(CUSTOMER_PHONE);
    await page
      .getByTestId("lead-intake-referral-email")
      .fill(CUSTOMER_EMAIL);
    await page
      .getByTestId("lead-intake-referral-notes")
      .fill(
        `[M24.3 journey] Referral intake recorded via Playwright acceptance suite; referrer = ${REFERRER_NAME}.`,
      );

    // ---------------------------------------------------------------
    // Step 7 — submit. Post-create closes intake Dialog + opens
    //          LeadDetailModal + refetches list.
    // ---------------------------------------------------------------
    await page.getByTestId("lead-intake-referral-submit").click();

    const modalRegion = page.locator("div.fixed.inset-0.z-50");
    await expect(
      modalRegion.getByText("Sales handoff packet", { exact: true }).first(),
      "LeadDetailModal should open for the newly created referral lead",
    ).toBeVisible({ timeout: 15_000 });

    // ---------------------------------------------------------------
    // Step 8 — extract the new lead's id from the modal header.
    // ---------------------------------------------------------------
    const leadIdText = await modalRegion
      .getByText(/^Lead #\d+/)
      .first()
      .textContent();
    expect(leadIdText).toMatch(/^Lead #\d+/);
    const newLeadId = Number((leadIdText ?? "").replace(/^Lead #/, ""));
    expect(Number.isInteger(newLeadId) && newLeadId > 0).toBe(true);

    // ---------------------------------------------------------------
    // Step 9 — assign Acceptance Advisor via AssignmentDropdown.
    // ---------------------------------------------------------------
    const assignmentTrigger = modalRegion
      .getByRole("button", { name: /^Unassigned$/ })
      .first();
    await expect(assignmentTrigger).toBeVisible({ timeout: 10_000 });
    await assignmentTrigger.click();

    const advisorOption = modalRegion
      .getByRole("button", { name: ADVISOR_NAME })
      .first();
    await expect(advisorOption).toBeVisible({ timeout: 10_000 });
    await advisorOption.click();

    await expect(
      modalRegion.getByRole("button", { name: ADVISOR_NAME }).first(),
      `assignment trigger should reflect ${ADVISOR_NAME} after selection`,
    ).toBeVisible({ timeout: 10_000 });

    // ---------------------------------------------------------------
    // Step 10 — business-outcome assertions via admin API:
    //           - lead assigned to Acceptance Advisor
    //           - channel="referral"
    //           - referrer FK matches Priya's id (backend contract
    //             preserved even though the modal does not display
    //             it today; that display is deferred to M25 per
    //             §3 deferral 13).
    // ---------------------------------------------------------------
    const lead = await expectLeadAssignedTo(request, newLeadId, ADVISOR_NAME);
    expect(
      lead.channel,
      `lead id=${newLeadId} should have channel="referral"`,
    ).toBe("referral");

    // The admin list projection exposes `referrer` as a FK id (see
    // frontend/src/lib/api.ts:195). If the picker selection didn't
    // fold into the createReferralLead payload correctly, this
    // assertion fails loudly — proves the operator's picker choice
    // actually persists to the backend.
    const referrerFk = (lead as unknown as { referrer?: number | null })
      .referrer;
    expect(
      referrerFk,
      `lead id=${newLeadId} should link to referring customer id=${referrer.id}`,
    ).toBe(referrer.id);

    // ---------------------------------------------------------------
    // Step 11 — dismiss modal + list-row channel assertion.
    // ---------------------------------------------------------------
    await page.reload();
    await expect(
      page.getByRole("heading", { level: 1, name: "Sales leads" }),
    ).toBeVisible({ timeout: 15_000 });

    const newLeadRow = page.getByTestId(`sales-leads-row-${newLeadId}`);
    await expect(
      newLeadRow,
      `new lead row (id=${newLeadId}) should appear in the leads table after intake`,
    ).toBeVisible({ timeout: 15_000 });
    await expect(newLeadRow).toContainText(CUSTOMER_NAME);
    await expect(newLeadRow).toContainText("referral");
  });
});
