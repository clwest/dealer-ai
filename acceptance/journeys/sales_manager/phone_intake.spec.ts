// Milestone 24 · Increment 2 (SESSION_182) — phone intake journey.
//
// Guiding principle: this suite is an operational acceptance contract,
// not a UI automation project. The journey validates that a sales
// operator can capture a phone customer through the real UI on
// /dealer-ai-sales/leads, assign it, and immediately start a 24-hour
// follow-up cadence through the existing CadenceConfigPanel on
// /dealer-ai-sales/follow-ups.
//
// Per MILESTONE_24_PLANNING.md §5.d Option C (phone row): scope is
// intake → list channel visibility → open LeadDetailModal → assign
// → navigate to follow-ups → create 24hr cadence via existing
// CadenceConfigPanel. Both downstream verbs (assign + cadence) are
// already-shipped operator UI reachable through the normal sales
// workflow.
//
// Seeded state (via seed_journey_sales_operational_entry +
// seed_journey_sales_manager_daily_startup):
// - `acceptance-sales-manager` user (sales_manager @ default
//   dealership) — auth persona via storage state
// - `Acceptance Advisor` (M20 seed's Salesperson row + linked auth
//   user, is_active=True) — the assignment target
//
// Journey steps:
// 1. Navigate to /dealer-ai-sales/leads.
// 2. Click `+ Phone` CTA — Dialog opens.
// 3. Fill the LeadIntakeForm with a unique per-run customer name.
// 4. Submit — Dialog closes, LeadDetailModal opens for the new lead.
// 5. Extract the new lead's id from the modal header ("Lead #N").
// 6. Assign "Acceptance Advisor" via AssignmentDropdown inside the
//    modal.
// 7. Business-outcome assertion via admin API: lead assigned to
//    Acceptance Advisor + channel="phone".
// 8. Reload → assert list row for new lead shows channel="phone".
// 9. Navigate to /dealer-ai-sales/follow-ups.
// 10. Use existing CadenceConfigPanel (CreateCadenceForm) to start
//     a 24hr cadence for the new lead's id.
// 11. Business-outcome assertion: the newly-created cadence row
//     appears in the recent-cadences panel + spawned at least one
//     follow-up task via the admin API.

import { test, expect } from "@playwright/test";

import { expectLeadAssignedTo } from "../../support/assertions/dashboard";

test.describe("Sales operator can record a phone customer + start a 24hr cadence through the UI", () => {
  test("phone intake → LeadDetailModal → assign → 24hr cadence lands as a business outcome", async ({
    page,
    request,
  }) => {
    const ADVISOR_NAME = "Acceptance Advisor";
    // Unique name per run.
    const CUSTOMER_NAME = `M24.2 Phone Priya ${Date.now()}`;
    const CUSTOMER_PHONE = "+15551242002";
    const CUSTOMER_EMAIL = "m242-phone-priya@example.com";

    // ---------------------------------------------------------------
    // Step 1 — navigate to the sales-side leads page.
    // ---------------------------------------------------------------
    await page.goto("/dealer-ai-sales/leads");
    await expect(
      page.getByRole("heading", { level: 1, name: "Sales leads" }),
    ).toBeVisible({ timeout: 15_000 });

    // ---------------------------------------------------------------
    // Step 2 — click + Phone CTA. Dialog opens.
    // ---------------------------------------------------------------
    await page.getByTestId("sales-leads-add-phone").click();
    await expect(
      page.getByTestId("sales-leads-phone-dialog"),
      "phone Dialog should open after clicking + Phone",
    ).toBeVisible({ timeout: 10_000 });

    // ---------------------------------------------------------------
    // Step 3 — fill the LeadIntakeForm (channel="phone").
    // ---------------------------------------------------------------
    await page.getByTestId("lead-intake-phone-name").fill(CUSTOMER_NAME);
    await page.getByTestId("lead-intake-phone-phone").fill(CUSTOMER_PHONE);
    await page.getByTestId("lead-intake-phone-email").fill(CUSTOMER_EMAIL);
    await page
      .getByTestId("lead-intake-phone-notes")
      .fill(
        `[M24.2 journey] Phone intake recorded via Playwright acceptance suite.`,
      );

    // ---------------------------------------------------------------
    // Step 4 — submit. Post-create closes intake Dialog + opens
    //          LeadDetailModal + refetches list.
    // ---------------------------------------------------------------
    await page.getByTestId("lead-intake-phone-submit").click();

    const modalRegion = page.locator("div.fixed.inset-0.z-50");
    await expect(
      modalRegion.getByText("Sales handoff packet", { exact: true }).first(),
      "LeadDetailModal should open for the newly created phone lead",
    ).toBeVisible({ timeout: 15_000 });

    // ---------------------------------------------------------------
    // Step 5 — extract the new lead's id from the modal header.
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

    await expect(
      modalRegion.getByRole("button", { name: ADVISOR_NAME }).first(),
      `assignment trigger should reflect ${ADVISOR_NAME} after selection`,
    ).toBeVisible({ timeout: 10_000 });

    // ---------------------------------------------------------------
    // Step 7 — business-outcome assertion via admin API.
    // ---------------------------------------------------------------
    const lead = await expectLeadAssignedTo(request, newLeadId, ADVISOR_NAME);
    expect(
      lead.channel,
      `lead id=${newLeadId} should have channel="phone"`,
    ).toBe("phone");

    // ---------------------------------------------------------------
    // Step 8 — dismiss modal + list-row channel assertion. Reload
    //          (avoids the strict-mode Close collision inside the
    //          modal region + proves state survives a fresh fetch).
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
    await expect(newLeadRow).toContainText("phone");

    // ---------------------------------------------------------------
    // Step 9 — navigate to the follow-ups work-queue page.
    // ---------------------------------------------------------------
    await page.goto("/dealer-ai-sales/follow-ups");
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: "Follow-up work-queue",
      }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("cadence-config-panel")).toBeVisible();

    // ---------------------------------------------------------------
    // Step 10 — create a 24hr cadence for the new phone lead's id
    //           via the existing CadenceConfigPanel (M21.3 shipped
    //           UI). Uses the wrapper createCadence under the hood.
    // ---------------------------------------------------------------
    await page
      .getByTestId("create-cadence-lead-id")
      .fill(String(newLeadId));
    await page
      .getByTestId("create-cadence-template")
      .selectOption("24hr");
    await page.getByTestId("create-cadence-submit").click();

    // The recent-cadences panel appears with the newly-created row.
    // Its testid is `cadence-row-{id}` where id comes from the API
    // response. Locate dynamically since IDs vary per run.
    await expect(page.getByTestId("cadence-config-recent")).toBeVisible({
      timeout: 10_000,
    });
    const recentCadenceRow = page
      .getByTestId("cadence-config-recent")
      .locator('[data-testid^="cadence-row-"]')
      .first();
    await expect(recentCadenceRow).toBeVisible();

    // Extract the cadence id from the row testid.
    const recentCadenceTestid = await recentCadenceRow.getAttribute(
      "data-testid",
    );
    expect(recentCadenceTestid).toMatch(/^cadence-row-\d+$/);
    const newCadenceId = Number(
      (recentCadenceTestid ?? "").replace("cadence-row-", ""),
    );

    // The state before pause is "active".
    await expect(
      page.getByTestId(`cadence-state-${newCadenceId}`),
    ).toHaveText(/active/);

    // ---------------------------------------------------------------
    // Step 11 — business-outcome assertion via admin API: at least
    //           one follow-up task exists for the newly-created
    //           cadence. Task lifecycle for a 24hr template spawns
    //           a single task at 24h from started_at, so this
    //           assertion proves the cadence engine actually ran.
    // ---------------------------------------------------------------
    await expect
      .poll(
        async () => {
          const res = await request.get(
            "/api/dealer-ai/admin/follow-up-tasks/?limit=100",
          );
          expect(res.status()).toBe(200);
          const body = (await res.json()) as {
            results?: { cadence_id: number }[];
          };
          const results = body.results ?? [];
          return results.filter((t) => t.cadence_id === newCadenceId).length;
        },
        {
          message: `expected at least one follow-up task spawned for new 24hr cadence id=${newCadenceId} (phone lead id=${newLeadId})`,
          timeout: 10_000,
        },
      )
      .toBeGreaterThanOrEqual(1);
  });
});
