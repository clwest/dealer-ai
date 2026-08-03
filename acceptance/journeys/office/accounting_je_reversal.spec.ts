// Milestone 22 · Increment 2 — JE reversal workflow journey.
//
// Guiding principle: this journey is an operational acceptance
// contract, not a UI automation project. If it passes, an office
// manager (dealer_owner persona) can reverse a posted journal entry
// entirely through the shipped application — the M14.3/M14.4 detail
// page + reversal dialog — and the resulting reversal lands durably
// at the service layer with the sign-flipped-lines +
// original-linkage invariants intact.
//
// Seeded state:
// - Existing `acceptance-owner` persona (dealer_owner @ default
//   dealership) — provisioned by
//   `seed_journey_owner_morning_review`.
// - `seed_journey_office_accounting_workflow` (M20.3 + M22.2)
//   posts one balanced M22.2 fixture entry
//   (Dr Bank Operating $250 / Cr Vehicle Sales Retail $250) with
//   the description `[M22.2-office-je-reversal] ...` and clears any
//   pre-existing reversal targeting it so the fixture stays
//   reversible across suite re-runs.
//
// Journey steps:
// 1. Look up the fixture JE by description prefix via the M14.1
//    admin API so the journey can navigate directly to detail
//    without depending on JE list pagination behavior.
// 2. Owner lands on /dealer-ai-accounting/journal-entries/<pk>.
// 3. Owner opens the reversal dialog via "Reverse this entry".
// 4. Owner fills the reason textarea and clicks "Confirm reversal".
// 5. Business-outcome assertion via the admin API — a reversal
//    entry exists with reverses_id === originalId, non-empty
//    reason, and sign-flipped line totals.
//
// Per M22.2 §5.f Option B (journey-as-verifier): if the shipped page
// cannot complete the workflow, this test fails loudly and the §5.d
// gap-handling posture governs the response. No manual pre-verification
// happened before authoring — the first passing run IS the evidence
// that the shipped surface is operationally complete.

import { test, expect } from "@playwright/test";

import {
  expectJournalEntryReversed,
  findJournalEntryByDescriptionPrefix,
} from "../../support/assertions/accounting";

const M22_FIXTURE_DESCRIPTION_PREFIX = "[M22.2-office-je-reversal]";
const M22_REVERSAL_REASON =
  "M22 acceptance journey — verifying the reversal workflow is operational";

test.describe(
  "Office / accounting workflow — reverse a posted journal entry",
  () => {
    test("owner can reverse a journal entry via the detail page", async ({
      page,
      request,
    }) => {
      // ---------------------------------------------------------------
      // Step 1 — locate the seeded reversible fixture via admin API.
      // ---------------------------------------------------------------
      const fixture = await findJournalEntryByDescriptionPrefix(
        request,
        M22_FIXTURE_DESCRIPTION_PREFIX,
      );
      expect(
        fixture.reverses_id,
        "fixture entry itself must be an original, not a reversal",
      ).toBeNull();

      // ---------------------------------------------------------------
      // Step 2 — land on the JE detail page for the fixture.
      // ---------------------------------------------------------------
      await page.goto(
        `/dealer-ai-accounting/journal-entries/${fixture.id}`,
      );
      await expect(
        page.getByRole("heading", { level: 1 }),
        "detail page heading should identify the entry by id",
      ).toContainText(`Journal Entry #${fixture.id}`, {
        timeout: 15_000,
      });

      // The Corrections card renders the reversal trigger. Wait for
      // it to be enabled — indirectly signals the detail-fetch is done.
      const reverseButton = page.getByRole("button", {
        name: /^Reverse this entry$/,
      });
      await expect(
        reverseButton,
        "'Reverse this entry' button should appear on the detail page",
      ).toBeVisible({ timeout: 15_000 });
      await expect(reverseButton).toBeEnabled({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 3 — open the reversal dialog.
      // ---------------------------------------------------------------
      await reverseButton.click();
      const dialog = page.getByRole("dialog", {
        name: new RegExp(`Reverse journal entry #${fixture.id}`, "i"),
      });
      await expect(
        dialog,
        "reversal dialog should open with the entry id in the heading",
      ).toBeVisible({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 4 — fill reason + confirm.
      // ---------------------------------------------------------------
      const reasonField = dialog.getByRole("textbox", {
        name: /Reason/i,
      });
      await reasonField.fill(M22_REVERSAL_REASON);

      const confirmButton = dialog.getByRole("button", {
        name: /^Confirm reversal$/,
      });
      await expect(
        confirmButton,
        "confirm button should be enabled once reason is filled",
      ).toBeEnabled({ timeout: 5_000 });
      await confirmButton.click();

      // Dialog closes on success (the page reloads detail data and
      // dismisses the dialog per AccountingJournalEntryDetailPage.tsx
      // handleConfirm — setOpen(false) + reset() + onReversed()).
      await expect(
        dialog,
        "reversal dialog should close after a successful confirm",
      ).not.toBeVisible({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 5 — business-outcome assertion via API.
      // ---------------------------------------------------------------
      const reversal = await expectJournalEntryReversed(
        request,
        fixture.id,
      );
      expect(
        reversal.reason,
        "reversal should carry the reason the operator submitted",
      ).toContain("M22 acceptance journey");
    });
  },
);
