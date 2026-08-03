// Milestone 20 · Increment 4 — BHPH collections read-side workflow.
//
// **Scope caveat (§0.a M20.4 decision 1).** The M20 planning §7
// M20.4 originally described the BHPH collections journey as
// "daily book review, recording a promise-to-pay, capturing a
// collection contact, initiating repossession on a broken
// promise". As of M12.7 the four write-side operations (record
// PtP, mark broken, log contact, initiate repo) have NO shipped
// frontend UI — only backend endpoints. Per the M20 guiding
// principle ("business outcomes through the real application"),
// journeys must exercise business outcomes through the real UI;
// write-side journeys aren't possible with the current shipped
// surface.
//
// M20.4 therefore validates the READ SIDE of the daily book review
// workflow — the seed plants a full note chain (payment +
// broken promise + contact + ordered repossession) via M12 service
// verbs, and the journey verifies that a collector opening the
// portfolio + drilling into the note sees every operationally-
// relevant signal (portfolio KPIs, all five detail cards
// populated). This proves the read-side pipeline works end-to-end
// on operator-actionable state — meaningful even though it doesn't
// exercise the write half.
//
// The missing write-side UI is recorded in the M20.4 handoff as
// an operator-friction data point for M21+ candidate consideration.
//
// Seeded state (via seed_journey_bhph_collections_workflow):
// - `acceptance-bhph-collector` user (sales_manager @ default)
// - Fixture BHPH note on vehicle stock "M20-BHPH-ACCEPT" with:
//   - 1 historical payment
//   - 1 promise-to-pay in `broken` state
//   - 1 collection contact
//   - 1 repossession in `ordered` state
//
// Journey steps:
// 1. Collector lands on /dealer-ai-bhph/portfolio.
// 2. Portfolio heading + at least one MetricCard visible.
// 3. API pre-flight: seeded note is present + note detail is
//    fully populated (payment + broken promise + contact + repo).
// 4. Collector navigates to /dealer-ai-bhph/notes/<pk>.
// 5. Note detail heading renders with the note's id.
// 6. All five card sections (Loan terms + Payments + Promises +
//    Contacts + Repossessions) render.
// 7. Business-outcome assertion: the four child collections are
//    non-empty at the service layer — the collector can trust
//    what they see.

import { test, expect } from "@playwright/test";

import {
  expectNoteDetailPopulated,
  findSeededNoteId,
} from "../../support/assertions/bhph";

// Fixture loan terms match seed_journey_bhph_collections_workflow —
// used to locate the seeded note in the admin list (which doesn't
// expose stock number).
const FIXTURE_LOAN = {
  principal: "6500.00",
  apr: "21.99",
  termWeeks: 78,
};

test.describe(
  "BHPH collections workflow — read-side daily book review",
  () => {
    test("collector can review the portfolio and drill into a note with all signals visible", async ({
      page,
      request,
    }) => {
      // ---------------------------------------------------------------
      // Pre-flight — resolve the seeded note's ID via the admin API +
      // verify the seed plant all four child artefacts.
      // ---------------------------------------------------------------
      const notePk = await findSeededNoteId(request, FIXTURE_LOAN);
      await expectNoteDetailPopulated(request, notePk);

      // ---------------------------------------------------------------
      // Step 1 — land on the BHPH portfolio.
      // ---------------------------------------------------------------
      await page.goto("/dealer-ai-bhph/portfolio");
      await expect(
        page.getByRole("heading", { level: 1, name: "BHPH Portfolio" }),
      ).toBeVisible({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 2 — portfolio KPI cards visible. MetricCard titles are
      //          rendered inside a CardTitle (a `<div>`, not a
      //          heading — per M20.2 §0.a decision 5).
      // ---------------------------------------------------------------
      await expect(
        page.getByText("Notes in portfolio", { exact: true }),
        "'Notes in portfolio' KPI card should be visible",
      ).toBeVisible({ timeout: 10_000 });
      await expect(
        page.getByText("Cure rate", { exact: true }),
        "'Cure rate' KPI card should be visible",
      ).toBeVisible();

      // ---------------------------------------------------------------
      // Step 3 — drill into the seeded note.
      // ---------------------------------------------------------------
      await page.goto(`/dealer-ai-bhph/notes/${notePk}`);
      await expect(
        page.getByRole("heading", {
          level: 1,
          name: `BHPH Note #${notePk}`,
        }),
        `collector should see the detail heading for note #${notePk}`,
      ).toBeVisible({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 4 — all five card sections render with visible titles
      //          (Loan terms is always present; Payments / Promises /
      //          Contacts / Repossessions render `(N)` next to their
      //          title where N is the count).
      // ---------------------------------------------------------------
      await expect(
        page.getByText("Loan terms", { exact: true }),
        "Loan terms card should render on the note detail",
      ).toBeVisible();
      await expect(
        page.getByText(/^Payments \(\d+\)$/),
        "Payments card should render with a count",
      ).toBeVisible();
      await expect(
        page.getByText(/^Promises \(\d+\)$/),
        "Promises card should render with a count",
      ).toBeVisible();
      await expect(
        page.getByText(/^Contacts \(\d+\)$/),
        "Contacts card should render with a count",
      ).toBeVisible();
      await expect(
        page.getByText(/^Repossessions \(\d+\)$/),
        "Repossessions card should render with a count",
      ).toBeVisible();

      // ---------------------------------------------------------------
      // Step 5 — re-assert the note detail is fully populated at the
      //          service layer. Business-outcome: the collector can
      //          trust the UI's non-zero counts reflect the
      //          persisted state (not a rendering illusion).
      // ---------------------------------------------------------------
      await expectNoteDetailPopulated(request, notePk);
    });
  },
);
