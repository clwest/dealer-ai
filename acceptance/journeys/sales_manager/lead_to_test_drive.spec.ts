// Milestone 25 · Increment 2 (SESSION_187) — lead-to-test-drive
// operational-completion journey.
//
// Guiding principle: this suite is an operational acceptance contract,
// not a UI automation project. The journey validates the M25 anchor
// business question: can a salesperson receive a lead, assign it, and
// schedule the customer's test drive entirely through the normal
// product workflow?
//
// Per MILESTONE_25_PLANNING.md §5.d locked as modal-only: the
// RecordTestDriveForm is attached inside LeadDetailModal as a
// collapsible "Schedule test drive" section. DealerAiSalesTestDrives
// remains the canonical visibility surface — the journey creates the
// drive in the modal and then asserts it appears on the read-only
// page.
//
// Seeded state (via seed_journey_sales_operational_entry):
// - `acceptance-sales-manager` user (sales_manager @ default
//   dealership) — auth persona via storage state
// - `Acceptance Advisor` (M20 seed's Salesperson) — assignment
//   target
// - Vehicle `#M25-TEST-DRIVE-01` — 2025 Ford Bronco Wildtrak, the
//   deterministic picker target added at M25.2 open
//
// Journey steps:
// 1. Navigate to /dealer-ai-sales/leads.
// 2. Click `+ Walk-in` CTA → intake Dialog opens.
// 3. Fill LeadIntakeForm with a unique per-run customer name.
// 4. Submit → LeadDetailModal opens for the new lead.
// 5. Extract the new lead's id from the modal header.
// 6. Assign Acceptance Advisor via AssignmentDropdown.
// 7. Expand "Schedule test drive" collapsible.
// 8. Wait for the picker to load, search for "Bronco", click the
//    seeded fixture vehicle's row (M25-TEST-DRIVE-01).
// 9. Submit the test-drive form.
// 10. Assert the collapsible closes with a "Recorded" success
//     indicator.
// 11. Close the modal.
// 12. Business-outcome assertion via admin/test-drives/list/ API:
//     the drive exists + associates lead + vehicle + dealership +
//     driven_at (recent) correctly.
// 13. Navigate to /dealer-ai-sales/test-drives → assert the drive
//     row is visible on the operator page.
//
// Explicit non-goals per M25 §3:
// - No secondary launch point from DealerAiSalesTestDrives — the
//   page stays read-only.
// - No edit/delete UI on existing drives.
// - No advanced picker filters (year/make/model dropdowns) — search
//   text field is the sole narrowing UI in M25.2.

import { test, expect } from "@playwright/test";

interface AdminVehiclesResponse {
  count: number;
  results: Array<{
    id: number;
    stock_number: string;
    display_name: string;
  }>;
}

interface TestDriveListResponse {
  count: number;
  results: Array<{
    id: number;
    lead_id: number;
    vehicle_id: number;
    dealership_id: number;
    driven_by_user_id: number | null;
    driven_at: string;
    duration_minutes: number | null;
    customer_reaction: string;
    next_action: string;
  }>;
}

const FIXTURE_STOCK = "M25-TEST-DRIVE-01";

test.describe("Sales operator can schedule a test drive from LeadDetailModal", () => {
  test("walk-in intake → assign → schedule test drive → row appears in test-drive workflow", async ({
    page,
    request,
  }) => {
    const ADVISOR_NAME = "Acceptance Advisor";
    const CUSTOMER_NAME = `M25.2 TD Customer ${Date.now()}`;
    const CUSTOMER_PHONE = "+15552520001";
    const CUSTOMER_EMAIL = "m252-td-customer@example.com";

    // ---------------------------------------------------------------
    // Preflight — resolve the fixture vehicle's id via the M25.2
    // admin/vehicles/ endpoint. Stable across suite runs because the
    // stock number is a deterministic seed fixture per
    // seed_journey_sales_operational_entry._provision_test_drive_vehicle.
    // ---------------------------------------------------------------
    const inventoryResponse = await request.get(
      `/api/dealer-ai/admin/vehicles/?search=${encodeURIComponent(FIXTURE_STOCK)}`,
    );
    expect(inventoryResponse.status()).toBe(200);
    const inventory = (await inventoryResponse.json()) as AdminVehiclesResponse;
    const fixture = inventory.results.find(
      (v) => v.stock_number === FIXTURE_STOCK,
    );
    expect(
      fixture,
      `seeded fixture vehicle #${FIXTURE_STOCK} should be present`,
    ).toBeTruthy();
    const fixtureVehicleId = fixture!.id;

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
    ).toBeVisible({ timeout: 10_000 });

    // ---------------------------------------------------------------
    // Step 3 — fill LeadIntakeForm.
    // ---------------------------------------------------------------
    await page.getByTestId("lead-intake-walk_in-name").fill(CUSTOMER_NAME);
    await page.getByTestId("lead-intake-walk_in-phone").fill(CUSTOMER_PHONE);
    await page.getByTestId("lead-intake-walk_in-email").fill(CUSTOMER_EMAIL);
    await page
      .getByTestId("lead-intake-walk_in-notes")
      .fill(
        "[M25.2 journey] Walk-in intake for lead-to-test-drive Playwright acceptance suite.",
      );

    // ---------------------------------------------------------------
    // Step 4 — submit → LeadDetailModal opens.
    // ---------------------------------------------------------------
    await page.getByTestId("lead-intake-walk_in-submit").click();
    const modalRegion = page.locator("div.fixed.inset-0.z-50");
    await expect(
      modalRegion.getByText("Sales handoff packet", { exact: true }).first(),
      "LeadDetailModal should open for the newly created walk-in lead",
    ).toBeVisible({ timeout: 15_000 });

    // ---------------------------------------------------------------
    // Step 5 — extract new lead's id from modal header.
    // ---------------------------------------------------------------
    const leadIdText = await modalRegion
      .getByText(/^Lead #\d+/)
      .first()
      .textContent();
    expect(leadIdText).toMatch(/^Lead #\d+/);
    const newLeadId = Number((leadIdText ?? "").replace(/^Lead #/, ""));
    expect(Number.isInteger(newLeadId) && newLeadId > 0).toBe(true);

    // ---------------------------------------------------------------
    // Step 6 — assign Acceptance Advisor via AssignmentDropdown.
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
    ).toBeVisible({ timeout: 10_000 });

    // ---------------------------------------------------------------
    // Step 7 — expand "Schedule test drive" collapsible.
    // ---------------------------------------------------------------
    const scheduleToggle = modalRegion.getByTestId(
      "schedule-test-drive-toggle",
    );
    await expect(scheduleToggle).toBeVisible({ timeout: 5_000 });
    await scheduleToggle.click();
    await expect(
      modalRegion.getByTestId("record-test-drive-form"),
      "form should render after expanding the collapsible",
    ).toBeVisible({ timeout: 10_000 });

    // ---------------------------------------------------------------
    // Step 8 — search inventory + click the fixture vehicle row.
    //          The picker's inventory zone lazy-loads via
    //          listAdminVehicles; typing "Bronco" narrows the fetch.
    // ---------------------------------------------------------------
    await modalRegion.getByTestId("record-test-drive-search").fill("Bronco");
    const vehicleRow = modalRegion.getByTestId(
      `record-test-drive-vehicle-${fixtureVehicleId}`,
    );
    await expect(
      vehicleRow,
      `fixture vehicle row (id=${fixtureVehicleId}, stock=${FIXTURE_STOCK}) should appear in the picker after searching "Bronco"`,
    ).toBeVisible({ timeout: 10_000 });
    await vehicleRow.click();

    // Optional field for a fuller assertion downstream.
    await modalRegion
      .getByTestId("record-test-drive-duration-minutes")
      .fill("22");
    await modalRegion
      .getByTestId("record-test-drive-customer-reaction")
      .fill("Very positive — asked about financing.");

    // ---------------------------------------------------------------
    // Step 9 — submit.
    // ---------------------------------------------------------------
    await modalRegion.getByTestId("record-test-drive-submit").click();

    // ---------------------------------------------------------------
    // Step 10 — collapsible closes with "Recorded" success indicator.
    //           The parent flips testDriveOpen=false + testDriveJustRecorded=true.
    // ---------------------------------------------------------------
    await expect(
      modalRegion.getByTestId("schedule-test-drive-success"),
      "Schedule test drive header should show the Recorded success indicator after submit",
    ).toBeVisible({ timeout: 10_000 });
    await expect(
      modalRegion.getByTestId("record-test-drive-form"),
      "form should collapse (unmount) after successful submit",
    ).not.toBeVisible();

    // ---------------------------------------------------------------
    // Step 11 — close the modal.
    // ---------------------------------------------------------------
    await modalRegion.getByRole("button", { name: /close/i }).first().click();

    // ---------------------------------------------------------------
    // Step 12 — business-outcome assertion via admin/test-drives/list/.
    //           The M11.6 list endpoint's ?lead_id= filter narrows to
    //           the newly-created drive. Assert every association
    //           surfaces correctly: lead, vehicle, dealership,
    //           driven_by_user (recorded from request.user, i.e. the
    //           sales_manager persona), driven_at (recent), and the
    //           optional fields we filled in.
    // ---------------------------------------------------------------
    const driveListResponse = await request.get(
      `/api/dealer-ai/admin/test-drives/list/?lead_id=${newLeadId}`,
    );
    expect(driveListResponse.status()).toBe(200);
    const driveList =
      (await driveListResponse.json()) as TestDriveListResponse;
    expect(
      driveList.count,
      `exactly one drive should exist for the new lead id=${newLeadId}`,
    ).toBe(1);
    const drive = driveList.results[0]!;
    expect(drive.lead_id).toBe(newLeadId);
    expect(drive.vehicle_id).toBe(fixtureVehicleId);
    expect(drive.dealership_id).toBeGreaterThan(0);
    // driven_by_user_id is set from request.user at endpoint layer
    // per M11.2. Salesperson persona is the sales_manager, so this
    // must be non-null.
    expect(
      drive.driven_by_user_id,
      "driven_by_user_id should reflect the sales_manager persona (M11.2 endpoint reads request.user)",
    ).toBeGreaterThan(0);
    expect(drive.duration_minutes).toBe(22);
    expect(drive.customer_reaction).toBe(
      "Very positive — asked about financing.",
    );
    // driven_at defaults to timezone.now() server-side per M11.2
    // when omitted from the request. Confirm it lands within the
    // last two minutes.
    const drivenAt = new Date(drive.driven_at).getTime();
    const now = Date.now();
    expect(
      drivenAt,
      `driven_at should be recent — got ${drive.driven_at}`,
    ).toBeGreaterThan(now - 2 * 60_000);
    expect(drivenAt).toBeLessThanOrEqual(now + 60_000);

    // ---------------------------------------------------------------
    // Step 13 — navigate to DealerAiSalesTestDrives → assert row is
    //           visible with the expected reaction text (deterministic
    //           per-run string, safer than lead_id text which appears
    //           on multiple rows across suite runs).
    // ---------------------------------------------------------------
    await page.goto("/dealer-ai-sales/test-drives");
    await expect(
      page.getByRole("heading", { level: 1, name: "Test drives" }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(
      page.getByText("Very positive — asked about financing.").first(),
      "newly-recorded drive should appear on DealerAiSalesTestDrives (M11.6 list surface, unchanged by M25.2)",
    ).toBeVisible({ timeout: 10_000 });
    await expect(
      page.getByText(`#${newLeadId}`).first(),
      `lead id text #${newLeadId} should render in the drive row's Lead column`,
    ).toBeVisible({ timeout: 5_000 });
  });
});
