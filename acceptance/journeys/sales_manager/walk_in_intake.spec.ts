// Milestone 24 · Increment 1 (SESSION_181) — walk-in intake journey.
//
// Guiding principle: this suite is an operational acceptance contract,
// not a UI automation project. The journey validates that a sales
// operator can capture a walk-in customer through the real UI on
// /dealer-ai-sales/leads and immediately hand the new lead into the
// existing downstream operational workflow (open the detail modal +
// assign to an advisor) without leaving the page.
//
// Per MILESTONE_24_PLANNING.md §5.d Option C (walk-in row): scope is
// intake → list channel visibility → open LeadDetailModal → assign.
// Test-drive scheduling is a genuine downstream verb operators would
// want next, but no test-drive creation UI ships today
// (DealerAiSalesTestDrives.tsx line 4-5 explicitly deferred at M11.6);
// M24.1-open correction §3 deferral 12 records it as an M25 candidate.
//
// Seeded state (via seed_journey_sales_operational_entry +
// seed_journey_sales_manager_daily_startup):
// - `acceptance-sales-manager` user (sales_manager @ default
//   dealership) — auth persona via storage state
// - `Acceptance Advisor` (M20 seed's Salesperson row + linked auth
//   user, is_active=True) — the assignment target
// - one referring-customer lead (used by M24.3, not this journey)
//
// Journey steps:
// 1. Navigate to /dealer-ai-sales/leads.
// 2. Click `+ Walk-in` CTA — Dialog opens.
// 3. Fill the LeadIntakeForm with a unique per-run customer name.
// 4. Submit — Dialog closes, LeadDetailModal opens for the new lead,
//    list refetches in the background.
// 5. Extract the new lead's id from the modal header ("Lead #N").
// 6. Assign "Acceptance Advisor" via AssignmentDropdown inside the
//    modal.
// 7. Close the modal.
// 8. List row assertion: the new lead's row shows channel="walk_in".
// 9. Business-outcome assertion via admin API: lead exists + is
//    assigned to Acceptance Advisor + channel is walk_in.
//
// Explicit non-goals per §3 (M24.1-open correction):
// - No test-drive scheduling step (UI absent; deferred to M25).
// - No referrer assertion (this is walk-in, not referral).
// - No cadence step (this is walk-in, not phone).

import { test, expect } from "@playwright/test";

import { expectLeadAssignedTo } from "../../support/assertions/dashboard";

test.describe("Sales operator can record a walk-in customer through the UI", () => {
  test("walk-in intake → LeadDetailModal → assign lands as a business outcome", async ({
    page,
    request,
  }) => {
    const ADVISOR_NAME = "Acceptance Advisor";
    // Unique name per run — avoids collisions across suite re-runs
    // where prior runs' leads persist in the DB.
    const CUSTOMER_NAME = `M24.1 Walk-In Alice ${Date.now()}`;
    const CUSTOMER_PHONE = "+15551241001";
    const CUSTOMER_EMAIL = "m241-walkin-alice@example.com";

    // ---------------------------------------------------------------
    // Step 1 — navigate to the sales-side leads page.
    // ---------------------------------------------------------------
    await page.goto("/dealer-ai-sales/leads");
    await expect(
      page.getByRole("heading", { level: 1, name: "Sales leads" }),
    ).toBeVisible({ timeout: 15_000 });

    // ---------------------------------------------------------------
    // Step 2 — click + Walk-in CTA. Dialog opens.
    // ---------------------------------------------------------------
    await page.getByTestId("sales-leads-add-walk-in").click();
    await expect(
      page.getByTestId("sales-leads-walk-in-dialog"),
      "walk-in Dialog should open after clicking + Walk-in",
    ).toBeVisible({ timeout: 10_000 });

    // ---------------------------------------------------------------
    // Step 3 — fill the LeadIntakeForm.
    // ---------------------------------------------------------------
    await page
      .getByTestId("lead-intake-walk_in-name")
      .fill(CUSTOMER_NAME);
    await page
      .getByTestId("lead-intake-walk_in-phone")
      .fill(CUSTOMER_PHONE);
    await page
      .getByTestId("lead-intake-walk_in-email")
      .fill(CUSTOMER_EMAIL);
    await page
      .getByTestId("lead-intake-walk_in-notes")
      .fill(
        `[M24.1 journey] Walk-in intake recorded via Playwright acceptance suite.`,
      );

    // ---------------------------------------------------------------
    // Step 4 — submit. Post-create closes intake Dialog + opens
    //          LeadDetailModal for the new lead + refetches list.
    // ---------------------------------------------------------------
    await page.getByTestId("lead-intake-walk_in-submit").click();

    // Modal header renders "Sales handoff packet" + "Lead #<id>".
    // Wait for that header so we know the modal has painted before
    // interacting with the AssignmentDropdown inside it.
    const modalRegion = page.locator("div.fixed.inset-0.z-50");
    await expect(
      modalRegion
        .getByText("Sales handoff packet", { exact: true })
        .first(),
      "LeadDetailModal should open for the newly created walk-in lead",
    ).toBeVisible({ timeout: 15_000 });

    // ---------------------------------------------------------------
    // Step 5 — extract the new lead's id from the modal header.
    //          Header text pattern: "Lead #<id>" (per
    //          LeadDetailModal.tsx line 186).
    // ---------------------------------------------------------------
    const leadIdText = await modalRegion
      .getByText(/^Lead #\d+/)
      .first()
      .textContent();
    expect(
      leadIdText,
      "modal header should contain 'Lead #<id>' after intake",
    ).toMatch(/^Lead #\d+/);
    const newLeadId = Number((leadIdText ?? "").replace(/^Lead #/, ""));
    expect(
      Number.isInteger(newLeadId) && newLeadId > 0,
      `extracted lead id should be a positive integer; got ${leadIdText}`,
    ).toBe(true);

    // ---------------------------------------------------------------
    // Step 6 — assign Acceptance Advisor via AssignmentDropdown.
    //          The trigger reads "Unassigned" initially
    //          (AssignmentDropdown.tsx). Scope to inside the modal
    //          to avoid matching filter chips elsewhere on the page.
    // ---------------------------------------------------------------
    const assignmentTrigger = modalRegion
      .getByRole("button", { name: /^Unassigned$/ })
      .first();
    await expect(
      assignmentTrigger,
      "assignment dropdown trigger should read 'Unassigned' before assignment",
    ).toBeVisible({ timeout: 10_000 });
    await assignmentTrigger.click();

    const advisorOption = modalRegion
      .getByRole("button", { name: ADVISOR_NAME })
      .first();
    await expect(
      advisorOption,
      `advisor "${ADVISOR_NAME}" should be selectable in the assignment dropdown`,
    ).toBeVisible({ timeout: 10_000 });
    await advisorOption.click();

    // Wait for the assignment PATCH to land — dropdown label flips
    // to the advisor's name.
    await expect(
      modalRegion.getByRole("button", { name: ADVISOR_NAME }).first(),
      `assignment trigger should reflect ${ADVISOR_NAME} after selection`,
    ).toBeVisible({ timeout: 10_000 });

    // ---------------------------------------------------------------
    // Step 7 — business-outcome assertions via admin API:
    //          - lead exists + is assigned to Acceptance Advisor
    //          - channel is walk_in
    //          The API is authoritative — if the assignment PATCH
    //          landed at the service layer, the UI closing/reopening
    //          is cosmetic. Assert now before touching the page.
    // ---------------------------------------------------------------
    const lead = await expectLeadAssignedTo(request, newLeadId, ADVISOR_NAME);
    expect(
      lead.channel,
      `lead id=${newLeadId} should have channel="walk_in"`,
    ).toBe("walk_in");

    // ---------------------------------------------------------------
    // Step 8 — dismiss modal + list-row assertion. Reload the page
    //          (rather than clicking one of the two "Close" buttons
    //          — AssignmentDropdown has its own, which collides in
    //          strict mode). Reload also proves the row + channel
    //          attribution survive a fresh fetch, not just optimistic
    //          state.
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
    await expect(newLeadRow).toContainText("walk_in");
  });
});
