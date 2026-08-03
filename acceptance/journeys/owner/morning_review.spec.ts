// Milestone 20 · Increment 2 — canonical owner morning review journey.
//
// Guiding principle: this suite is an operational acceptance
// contract, not a UI automation project. This journey validates that
// a dealership owner arriving for a morning review can land on the
// operator dashboard, see meaningful pipeline content, and drill into
// the leads pipeline without manual intervention.
//
// Seeded state (via seed_journey_owner_morning_review):
// - `acceptance-owner` user (dealer_owner @ default dealership)
// - two unassigned overnight phone leads on the default dealership
//   ("Overnight Buyer A" + "Overnight Buyer B")
//
// Journey steps:
// 1. Owner lands on /dealer-ai-overview (post-login redirect target).
// 2. Dashboard header + key cards visible (via text — CardTitle is a
//    `<div>` in shadcn/ui, not a semantic heading).
// 3. API business-outcome check: /admin/leads/ returns >= 1 lead
//    (proving the pipeline has content that the owner's dashboard
//    can render).
// 4. One seeded lead ("Overnight Buyer A") is present in the admin
//    list — the seed is producing the state the owner needs.
// 5. Navigate to /dealer-ai-leads (drilling into pipeline detail),
//    verify the page renders with the seeded lead visible in the
//    queue.

import { test, expect } from "@playwright/test";

import {
  expectLeadListHasAtLeast,
  findSeededLead,
} from "../../support/assertions/dashboard";

test.describe(
  "Owner morning review — dashboard scan + drill into pipeline",
  { tag: "@pilot-critical" },
  () => {
    test("owner lands on dashboard, sees today's pipeline, drills into leads", async ({
      page,
      request,
    }) => {
      // ---------------------------------------------------------------
      // Step 1 — dashboard loads
      // ---------------------------------------------------------------
      await page.goto("/dealer-ai-overview");
      await expect(
        page.getByRole("heading", { level: 1, name: "Overview" }),
        "owner should see the Overview heading on the operator dashboard",
      ).toBeVisible();

      // ---------------------------------------------------------------
      // Step 2 — key cards visible. shadcn/ui CardTitle is rendered
      //          as a `<div>` with no heading role (see
      //          frontend/src/components/ui/card.tsx:36), so target by
      //          visible text instead of role. Selector-stability
      //          fixes for the dashboard defer to a future increment
      //          if these prove brittle (§0.a M20.2 decision 4).
      // ---------------------------------------------------------------
      await expect(
        page.getByText("AI Sales Assistant", { exact: true }),
        "AI Sales Assistant card should be visible",
      ).toBeVisible();
      await expect(
        page.getByText("Today's leads", { exact: true }),
        "Today's leads card should be visible on the dashboard",
      ).toBeVisible();

      // ---------------------------------------------------------------
      // Step 3 — business-outcome assertions via the admin API. The
      //          dashboard fetches /admin/leads/?limit=3; if the API
      //          returns fewer than one lead the card renders empty
      //          and the morning review has no content.
      // ---------------------------------------------------------------
      await expectLeadListHasAtLeast(request, 1, { limit: 3 });

      const seeded = await findSeededLead(request, "Overnight Buyer A", {
        limit: 100,
      });
      expect(seeded.channel).toBe("phone");
      expect(seeded.urgency).toBe("immediate");
      expect(seeded.assigned_to).toBeNull();

      // ---------------------------------------------------------------
      // Step 4 — drill from dashboard into the full leads pipeline.
      // ---------------------------------------------------------------
      await page.goto("/dealer-ai-leads");
      await expect(
        page.getByRole("heading", { level: 1, name: "Leads" }),
        "owner should reach the leads page from the dashboard",
      ).toBeVisible();

      await expect(
        page.getByText("Overnight Buyer A").first(),
        `seeded lead "Overnight Buyer A" should appear in the leads queue`,
      ).toBeVisible({ timeout: 10_000 });
    });
  },
);
