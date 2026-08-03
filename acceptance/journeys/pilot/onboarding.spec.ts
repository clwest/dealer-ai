// Milestone 20 · Increment 1 — canonical pilot onboarding journey.
//
// Guiding principle (M20 planning): the suite is an operational
// acceptance contract, not a UI automation project. This journey
// validates that a dealership employee can successfully perform the
// M19.5 pilot onboarding playbook end-to-end through the shipped UI
// on deterministic seeded state.
//
// Seeded state (via seed_journey_pilot_onboarding management command):
// - `acceptance-operator` user (sales_manager @ default dealership)
// - `acceptance-pilot-owner` user (nominated as the pilot's owner)
// - one PilotProspect in `qualified` state ("Acceptance Motors")
//
// Journey steps:
// 1. Operator lands on /dealer-ai-admin and sees the Pilot onboarding
//    section.
// 2. Operator fills the "Create pilot" form with a unique slug,
//    display name, and the seeded pilot-owner username.
// 3. Operator submits. Business outcome: pilot appears in the list;
//    checklist auto-fires with `dealership_created` completed.
// 4. Operator opens the new pilot's detail panel.
// 5. Operator advances each remaining checklist step in order
//    (profile_configured → owner_user_added → staff_users_added →
//    inventory_imported → capabilities_enabled → readiness_confirmed).
// 6. Business outcome: pilot's is_ready flag flips to true; the
//    readiness_confirmed step shows completed; the operator surface
//    would now allow the pilot's staff to log in.
//
// Assertions target business state via the M19.3 admin API surface
// (see `../../support/assertions/pilot.ts`), not DOM state.

import { test, expect } from "@playwright/test";

import { PERSONAS } from "../../support/auth/personas";
import {
  expectPilotExists,
  expectPilotReady,
  expectStepCompleted,
  PILOT_ONBOARDING_STEP_ORDER,
} from "../../support/assertions/pilot";

// Each test run generates a unique slug so re-runs against a
// reuseExistingServer local backend accumulate cleanly. In CI the
// backend is fresh so this only matters locally.
const PILOT_SLUG = `acceptance-${Date.now()}`;
const PILOT_NAME = "Acceptance Motors (M20.1)";

test.describe(
  "Pilot onboarding — operator converts a qualified prospect into a live pilot",
  { tag: "@pilot-critical" },
  () => {
    test("operator can walk the M19.5 playbook end-to-end", async ({
      page,
      request,
    }) => {
      const owner = PERSONAS.platform_operator;

      // ---------------------------------------------------------------
      // Step 1 — land on /dealer-ai-admin, see the onboarding section
      // ---------------------------------------------------------------
      await page.goto("/dealer-ai-admin");
      const section = page.getByTestId("pilot-onboarding-section");
      await expect(
        section,
        "operator should see the Pilot onboarding section on /dealer-ai-admin",
      ).toBeVisible();

      // ---------------------------------------------------------------
      // Step 2 — fill the create-pilot form
      // ---------------------------------------------------------------
      await page.getByTestId("pilot-create-slug").fill(PILOT_SLUG);
      await page.getByTestId("pilot-create-name").fill(PILOT_NAME);
      await page.getByTestId("pilot-create-owner").fill("acceptance-pilot-owner");
      await page.getByTestId("pilot-create-submit").click();

      // ---------------------------------------------------------------
      // Step 3 — pilot appears in the list; checklist auto-fired
      //           the dealership_created step per M19.1 §5.d/§5.f
      // ---------------------------------------------------------------
      const pilotRow = page.getByTestId(`pilot-row-${PILOT_SLUG}`);
      await expect(
        pilotRow,
        `newly-created pilot ${PILOT_SLUG} should appear in the pilot list`,
      ).toBeVisible({ timeout: 10_000 });

      await expectPilotExists(request, PILOT_SLUG);
      await expectStepCompleted(request, PILOT_SLUG, "dealership_created");

      // ---------------------------------------------------------------
      // Step 4 — open the pilot's detail panel
      // ---------------------------------------------------------------
      await pilotRow.click();
      const detailPanel = page.getByTestId(`pilot-detail-${PILOT_SLUG}`);
      await expect(
        detailPanel,
        "operator should see the pilot detail panel after clicking the row",
      ).toBeVisible();

      // ---------------------------------------------------------------
      // Step 5 — advance each remaining checklist step in order
      // ---------------------------------------------------------------
      const remainingSteps = PILOT_ONBOARDING_STEP_ORDER.filter(
        (slug) => slug !== "dealership_created",
      );

      for (const stepSlug of remainingSteps) {
        const advanceButton = page.getByTestId(`pilot-advance-${stepSlug}`);
        await expect(
          advanceButton,
          `step ${stepSlug} should be pending and offer a Complete button`,
        ).toBeVisible();
        await advanceButton.click();

        // Wait for the button to disappear (step complete → the UI
        // stops rendering the button per PilotOnboardingSection.tsx
        // line 379: {!isComplete && <Button ...>}).
        await expect(
          advanceButton,
          `step ${stepSlug} should be marked complete after clicking Complete`,
        ).toBeHidden({ timeout: 10_000 });

        // Business-outcome assertion: the step is committed at the
        // service layer, not just the UI.
        await expectStepCompleted(request, PILOT_SLUG, stepSlug);
      }

      // ---------------------------------------------------------------
      // Step 6 — pilot is ready. Business outcome: is_ready=true;
      //          readiness_confirmed step complete; the operator's
      //          onboarding contract for this pilot is satisfied.
      // ---------------------------------------------------------------
      await expectPilotReady(request, PILOT_SLUG);

      // Belt-and-suspenders — the UI badge on the pilot row should
      // flip from "In progress" to "Ready" once is_ready=true.
      // The pilot list re-fetches after each checklist advance
      // (PilotOnboardingSection.tsx line 344 `onChanged={onChanged}`).
      await expect(
        pilotRow.getByText(/^Ready$/),
        `pilot row for ${PILOT_SLUG} should show the "Ready" badge`,
      ).toBeVisible({ timeout: 10_000 });
    });
  },
);
