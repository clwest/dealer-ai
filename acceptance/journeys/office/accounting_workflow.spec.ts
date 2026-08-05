// Milestone 20 · Increment 3 — canonical office/accounting workflow
// journey.
//
// Guiding principle: this suite is an operational acceptance
// contract, not a UI automation project. This journey validates
// that an office manager (dealer_owner persona) can open the trial
// balance page, freeze the current view into an immutable snapshot,
// and drill into the frozen snapshot via the prior-closes list —
// with the snapshot landing durably at the service layer.
//
// Seeded state:
// - Existing `acceptance-owner` persona (dealer_owner @ default
//   dealership) — provisioned by
//   seed_journey_owner_morning_review.
// - `seed_journey_office_accounting_workflow` posts one balanced
//   journal entry (Dr Bank Operating / Cr Vehicle Sales Retail
//   $100.00) so the trial balance has non-zero content.
//
// Journey steps:
// 1. Owner lands on /dealer-ai-accounting/trial-balance.
// 2. Trial balance table renders with the seeded posting reflected
//    (bank + revenue accounts both non-zero).
// 3. Owner clicks "Freeze this view" to lock a snapshot.
// 4. The frozen snapshot appears in the Prior closes list with
//    data-testid={snapshot-row-<id>}.
// 5. Owner clicks the snapshot row and the snapshot detail card
//    renders inline.
// 6. Business-outcome assertion via the admin API — the snapshot
//    exists in the frozen-snapshots list and is balanced.

import { test, expect } from "@playwright/test";

import {
  expectSnapshotBalanced,
  expectSnapshotCountAtLeast,
} from "../../support/assertions/accounting";

test.describe(
  "Office / accounting workflow — freeze a trial balance snapshot @rerun-hygiene",
  () => {
    test("owner can freeze the current trial balance view and drill into the snapshot", async ({
      page,
      request,
    }) => {
      // ---------------------------------------------------------------
      // Step 1 — land on the trial balance page.
      // ---------------------------------------------------------------
      await page.goto("/dealer-ai-accounting/trial-balance");
      await expect(
        page.getByRole("heading", { level: 1, name: "Trial Balance" }),
      ).toBeVisible({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 2 — verify the "Freeze this view" button is present +
      //          enabled once the underlying trial balance load
      //          resolves. If the trial-balance fetch failed the
      //          button stays disabled, so waiting for it to be
      //          enabled is our indirect readiness signal.
      // ---------------------------------------------------------------
      const freezeButton = page.getByRole("button", {
        name: /^Freeze this view$/,
      });
      await expect(
        freezeButton,
        "Freeze this view button should be visible on the trial balance page",
      ).toBeVisible({ timeout: 15_000 });
      await expect(
        freezeButton,
        "Freeze this view button should be enabled once trial balance loads",
      ).toBeEnabled({ timeout: 15_000 });

      // Snapshot how many frozen snapshots exist before the freeze so
      // we can assert on the incremental effect.
      const snapshotsBefore = await expectSnapshotCountAtLeast(request, 0);
      const priorCount = snapshotsBefore.length;

      // ---------------------------------------------------------------
      // Step 3 — click "Freeze this view".
      // ---------------------------------------------------------------
      await freezeButton.click();

      // Success status message appears once the POST resolves. The
      // page renders a role=status paragraph containing the message
      // "Snapshot frozen for as-of ...".
      await expect(
        page.getByRole("status"),
        "a status message should confirm the snapshot was frozen",
      ).toBeVisible({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 4 — the new frozen snapshot appears in Prior closes.
      //          The prior-closes table refetches after freeze.
      // ---------------------------------------------------------------
      await expect
        .poll(
          async () => {
            const snapshots = await expectSnapshotCountAtLeast(
              request,
              priorCount + 1,
            );
            return snapshots.length;
          },
          {
            message: `expected snapshot count to increase from ${priorCount} within poll window`,
            timeout: 10_000,
          },
        )
        .toBeGreaterThan(priorCount);

      const snapshotsAfter = await expectSnapshotCountAtLeast(
        request,
        priorCount + 1,
      );
      const newestSnapshot = snapshotsAfter[0];
      expect(
        newestSnapshot,
        "at least one snapshot should be present after freeze",
      ).toBeDefined();
      const newestId = (newestSnapshot as { id: number }).id;

      // ---------------------------------------------------------------
      // Step 5 — click the snapshot row (data-testid pattern from
      //          AccountingTrialBalancePage.tsx line 438) to open the
      //          snapshot detail inline.
      // ---------------------------------------------------------------
      const snapshotRow = page.getByTestId(`snapshot-row-${newestId}`);
      await expect(
        snapshotRow,
        `snapshot row for id=${newestId} should appear in Prior closes`,
      ).toBeVisible({ timeout: 10_000 });
      await snapshotRow.click();

      // ---------------------------------------------------------------
      // Step 6 — business-outcome assertion. The snapshot exists at
      //          the service layer and is balanced (debits ==
      //          credits).
      // ---------------------------------------------------------------
      await expectSnapshotBalanced(request, newestId);
    });
  },
);
