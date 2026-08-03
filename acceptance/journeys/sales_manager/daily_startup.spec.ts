// Milestone 20 · Increment 2 — canonical sales manager daily startup
// journey.
//
// Guiding principle: this suite is an operational acceptance
// contract, not a UI automation project. This journey validates that
// a sales manager arriving for the day can review overnight leads,
// pick one up, and assign it to an advisor through the real UI, with
// the assignment landing at the service layer.
//
// Seeded state (via seed_journey_sales_manager_daily_startup):
// - `acceptance-sales-manager` user (sales_manager @ default
//   dealership)
// - `acceptance-advisor` (Salesperson row + linked auth user,
//   is_active=True) so the assignment dropdown enumerates a stable
//   target
// - three unassigned overnight phone leads with varied urgency
//   ("Overnight SM Lead 1"..3)
//
// **Where assignment happens.** The shipped UI wires assignment
// through the LeadDetailModal opened from /dealer-ai-admin's
// "Recent leads" table + sales pipeline (see DealerAdmin.tsx line
// 572 + LeadDetailModal.tsx). The /dealer-ai-leads page is
// deliberately read-only (LeadsPage.tsx line 3: "No reassignment").
// This journey therefore drives assignment through /dealer-ai-admin.
//
// Journey steps:
// 1. Sales manager lands on /dealer-ai-overview (post-login target).
// 2. Navigate to /dealer-ai-admin (the assignment surface).
// 3. Find the seeded "Overnight SM Lead 1" in the "Recent leads"
//    table and click the row to open the LeadDetailModal.
// 4. In the modal, open the AssignmentDropdown (Unassigned button)
//    and pick "Acceptance Advisor".
// 5. Business-outcome assertion via the admin API: the lead is now
//    assigned to Acceptance Advisor at the service layer.
//
// Explicit non-goals per M20 §3 deferrals: be-back handling defers
// (no shipped frontend surface for be-backs as of M19); follow-up
// cadence queue defers (no dedicated frontend surface); the journey
// scopes to lead-assignment because that is what the shipped UI
// supports through the real operator flow.

import { test, expect } from "@playwright/test";

import {
  expectLeadAssignedTo,
  findSeededLead,
} from "../../support/assertions/dashboard";

test.describe(
  "Sales manager daily startup — triage overnight leads + assign to advisor",
  () => {
    test("sales manager can assign an overnight lead to an advisor through the UI", async ({
      page,
      request,
    }) => {
      const ADVISOR_NAME = "Acceptance Advisor";
      const LEAD_NAME = "Overnight SM Lead 1";

      // ---------------------------------------------------------------
      // Pre-flight — verify the seed produced the state the journey
      // depends on. A bad seed surfaces here rather than deep in the
      // UI interaction.
      // ---------------------------------------------------------------
      const seededLead = await findSeededLead(request, LEAD_NAME, {
        limit: 100,
      });
      expect(seededLead.assigned_to).toBeNull();

      // ---------------------------------------------------------------
      // Step 1 — dashboard first (post-login landing)
      // ---------------------------------------------------------------
      await page.goto("/dealer-ai-overview");
      await expect(
        page.getByRole("heading", { level: 1, name: "Overview" }),
      ).toBeVisible();

      // ---------------------------------------------------------------
      // Step 2 — navigate to the admin/assignment surface
      // ---------------------------------------------------------------
      await page.goto("/dealer-ai-admin");
      await expect(
        page.getByText("Recent leads", { exact: true }),
        "sales manager should see the Recent leads table on /dealer-ai-admin",
      ).toBeVisible({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 3 — find the seeded lead in the "Recent leads" table +
      //          click the row to open the LeadDetailModal. Each row
      //          is a <tr> with cursor-pointer + onClick handler
      //          (DealerAdmin.tsx line 389). The row's first cell
      //          renders lead.name in a semibold div.
      // ---------------------------------------------------------------
      const leadRow = page
        .getByRole("row")
        .filter({ hasText: LEAD_NAME })
        .first();
      await expect(
        leadRow,
        `seeded lead "${LEAD_NAME}" should appear as a clickable row in Recent leads`,
      ).toBeVisible({ timeout: 15_000 });
      await leadRow.click();

      // Modal opens. LeadDetailModal is a plain fixed-position div
      // (not a Radix Dialog — see LeadDetailModal.tsx line 178). Its
      // header renders "Sales handoff packet" + "Lead #<id>". Wait
      // for that header so we know the modal has painted before
      // interacting with the AssignmentDropdown inside it.
      const modalHeader = page
        .getByText("Sales handoff packet", { exact: true })
        .first();
      await expect(
        modalHeader,
        `LeadDetailModal for "${LEAD_NAME}" should be visible after row click`,
      ).toBeVisible({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 4 — open the assignment dropdown + pick the advisor. The
      //          trigger button initially reads "Unassigned"
      //          (AssignmentDropdown.tsx line ~122). Scope the query
      //          to inside the modal's header (which contains the
      //          dropdown per LeadDetailModal.tsx line 196) so we
      //          cannot accidentally match a filter chip or list
      //          badge elsewhere on the page.
      // ---------------------------------------------------------------
      // The LeadDetailModal's outermost wrapper uses the fixed
      // inset-0 z-50 utility trio (LeadDetailModal.tsx line 178) —
      // specific enough to scope selectors to the modal only, not
      // to unrelated "Unassigned" filter buttons elsewhere on the
      // page (e.g. the Handoff queue's Assignment filter).
      const modalRegion = page.locator("div.fixed.inset-0.z-50");
      const assignmentTrigger = modalRegion
        .getByRole("button", { name: /^Unassigned$/ })
        .first();
      await expect(
        assignmentTrigger,
        "assignment dropdown trigger should read 'Unassigned' before assignment",
      ).toBeVisible({ timeout: 10_000 });
      await assignmentTrigger.click();

      // Dropdown panel opens with "Assign advisor" header + advisor
      // list. Advisor options are buttons keyed by name inside a
      // <li>.
      const advisorOption = modalRegion
        .getByRole("button", { name: ADVISOR_NAME })
        .first();
      await expect(
        advisorOption,
        `advisor "${ADVISOR_NAME}" should be selectable in the assignment dropdown`,
      ).toBeVisible({ timeout: 10_000 });
      await advisorOption.click();

      // ---------------------------------------------------------------
      // Step 5 — business-outcome assertion. The assignment PATCH
      //          lands at /admin/lead/<id>/assign/ (M11 Phase 4).
      //          Poll the admin list until the assignment reflects.
      // ---------------------------------------------------------------
      await expect
        .poll(
          async () => {
            const response = await request.get(
              "/api/dealer-ai/admin/leads/?limit=100",
            );
            const body = await response.json();
            const results = Array.isArray(body) ? body : body.results ?? [];
            const found = results.find(
              (l: { id: number }) => l.id === seededLead.id,
            );
            return found?.assigned_to?.name ?? null;
          },
          {
            message: `lead id=${seededLead.id} did not become assigned to ${ADVISOR_NAME} within poll window`,
            timeout: 10_000,
          },
        )
        .toBe(ADVISOR_NAME);

      await expectLeadAssignedTo(request, seededLead.id, ADVISOR_NAME);
    });
  },
);
