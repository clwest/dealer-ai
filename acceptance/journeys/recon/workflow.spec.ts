// Milestone 20 · Increment 3 — canonical recon workflow journey.
//
// Guiding principle: this suite is an operational acceptance
// contract, not a UI automation project. This journey validates
// that a recon manager can open the recon dashboard for a vehicle
// with a completed condition report, review the findings, and
// record a decision through the shipped UI — with the decision
// persisting at the service layer.
//
// Seeded state (via seed_journey_recon_workflow):
// - `acceptance-recon-manager` user (recon_manager @ default
//   dealership)
// - Vehicle stock "M20-RECON-ACCEPT" on the default dealership
// - Completed ConditionReport for that vehicle with one undecided
//   ConditionFinding (mechanical, required severity: "brake pads
//   worn below 3mm")
//
// Journey steps:
// 1. Recon manager lands on
//    /dealer-ai-inventory/M20-RECON-ACCEPT/recon.
// 2. Recon dashboard renders with the vehicle heading + the
//    "Recon decisions" card.
// 3. The seeded finding is visible with three tier buttons
//    ("Must do" / "Should do" / "Won't do") because it has no
//    decision yet.
// 4. Recon manager clicks "Must do" on the finding.
// 5. Business-outcome assertion via /admin/vehicles/{stock}/recon/
//    — the finding now carries a ReconDecision with tier=must_do.

import { test, expect } from "@playwright/test";

import {
  expectDecisionRecorded,
  expectFinding,
} from "../../support/assertions/recon";

const FIXTURE_STOCK = "M20-RECON-ACCEPT";
const FIXTURE_FINDING_SUBSTRING = "brake pads worn below 3mm";

test.describe(
  "Recon workflow — recon manager records a decision on a condition finding @rerun-hygiene",
  () => {
    test("recon manager clicks a tier button and the decision persists", async ({
      page,
      request,
    }) => {
      // ---------------------------------------------------------------
      // Pre-flight — verify seed produced the state the journey
      // depends on (finding exists, no decision yet).
      // ---------------------------------------------------------------
      const finding = await expectFinding(
        request,
        FIXTURE_STOCK,
        FIXTURE_FINDING_SUBSTRING,
      );
      expect(
        finding.decision,
        "fixture finding should start with no decision",
      ).toBeNull();

      // ---------------------------------------------------------------
      // Step 1 — land on the recon page.
      // ---------------------------------------------------------------
      await page.goto(`/dealer-ai-inventory/${FIXTURE_STOCK}/recon`);
      await expect(
        page.getByRole("heading", {
          level: 1,
          name: `Recon · Stock #${FIXTURE_STOCK}`,
        }),
        "recon manager should see the recon heading for the fixture vehicle",
      ).toBeVisible({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 2 — "Recon decisions" card renders. CardTitle is a
      //          <div>, not a heading (per M20.2 §0.a decision 5).
      // ---------------------------------------------------------------
      await expect(
        page.getByText("Recon decisions", { exact: true }),
        "the Recon decisions card should be visible",
      ).toBeVisible();

      // ---------------------------------------------------------------
      // Step 3 — the seeded finding is visible with three tier
      //          buttons (finding has no decision yet).
      // ---------------------------------------------------------------
      await expect(
        page.getByText(FIXTURE_FINDING_SUBSTRING).first(),
        `the seeded finding "${FIXTURE_FINDING_SUBSTRING}" should be visible`,
      ).toBeVisible({ timeout: 10_000 });

      const mustDoButton = page
        .getByRole("button", { name: /^Must do$/ })
        .first();
      await expect(
        mustDoButton,
        `Must-do tier button should be visible for the undecided finding`,
      ).toBeVisible({ timeout: 10_000 });

      // ---------------------------------------------------------------
      // Step 4 — click "Must do".
      // ---------------------------------------------------------------
      await mustDoButton.click();

      // Once a decision is recorded the tier-picker "Must do" Button
      // is replaced with a Badge (DecisionRow.tsx line 119-133) —
      // the row's reconsideration menu offers "→ Should do" and
      // "→ Won't do", NOT a bare "Must do" Button. Wait for the
      // reconsideration prompt to appear as our UI-side settle
      // signal; the definitive assertion is at the service layer
      // below.
      await expect(
        page.getByRole("button", { name: /^→ Should do$/ }).first(),
        "reconsideration button should appear after decision is recorded",
      ).toBeVisible({ timeout: 10_000 });

      // ---------------------------------------------------------------
      // Step 5 — business-outcome assertion. The decision landed at
      //          the service layer, not just the UI.
      // ---------------------------------------------------------------
      await expectDecisionRecorded(
        request,
        FIXTURE_STOCK,
        FIXTURE_FINDING_SUBSTRING,
        "must_do",
      );
    });
  },
);
