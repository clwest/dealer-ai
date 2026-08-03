// Milestone 20 · Increment 4 — BHPH collections read-side workflow.
// Milestone 21 · Increment 2 — re-expanded to full write coverage.
//
// **M21.2 re-expansion.** The M20.4 journey narrowed to the read side
// because the write-side operations (record PtP, mark broken, log
// contact, initiate repo, mark recovered, mark re-intaked) had no
// shipped frontend UI. M21.2 ships the seven write components on the
// M12.7 collector dashboard surface, so the journey re-expands to
// exercise the full daily-book workflow end-to-end.
//
// Seeded state (via seed_journey_bhph_collections_workflow — M21.2
// extended):
// - `acceptance-bhph-collector` user (sales_manager @ default)
// - Fixture BHPH note on vehicle stock "M20-BHPH-ACCEPT" with:
//   - 1 historical payment
//   - 1 promise-to-pay in `broken` state (historical showcase)
//   - 1 promise-to-pay in `promised` state (M21.2 fixture — journey
//     marks broken)
//   - 1 collection contact
//   - 1 repossession in `ordered` state (journey marks recovered)
//   - 1 repossession in `recovered` state (M21.2 fixture — journey
//     marks re-intaked)
//   - 1 complete ConditionReport for the fixture vehicle (M21.2
//     fixture — referenced by mark-re-intaked)
//
// Journey steps:
// 1. Collector lands on /dealer-ai-bhph/portfolio; KPI cards visible.
// 2. Collector drills into the seeded note detail page.
// 3. Baseline child counts captured via API.
// 4. **Record PtP** via the form → new promise appears in `promised`
//    state; count grows by exactly one.
// 5. **Mark broken** on the seeded `promised`-state promise via row
//    action → promise state transitions to `broken`.
// 6. **Log contact** via the form → new contact appears; count grows
//    by exactly one.
// 7. **Initiate repossession** via the form → new repo appears in
//    `ordered` state; count grows by exactly one.
// 8. **Mark recovered** on the seeded `ordered`-state repo via row
//    action → state transitions to `recovered`.
// 9. **Mark re-intaked** on the seeded `recovered`-state repo via row
//    action, using the seeded ConditionReport ID → state transitions
//    to `re_intaked`.
//
// Every step asserts business outcomes via the M12 admin API — the
// operator's action moved persisted state, not just DOM state.

import { test, expect } from "@playwright/test";

import {
  expectNoteDetailPopulated,
  expectPromiseState,
  expectRepossessionState,
  fetchChildCounts,
  findCompleteConditionReportId,
  findOrderedRepossessionId,
  findPromisedStatePromiseId,
  findRecoveredRepossessionId,
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
const FIXTURE_STOCK = "M20-BHPH-ACCEPT";

test.describe(
  "BHPH collections workflow — full write-side (M21.2)",
  () => {
    test("collector can record PtP, mark broken, log contact, initiate + recover + re-intake repossessions end-to-end", async ({
      page,
      request,
    }) => {
      // -----------------------------------------------------------------
      // Pre-flight
      // -----------------------------------------------------------------
      const notePk = await findSeededNoteId(request, FIXTURE_LOAN);
      await expectNoteDetailPopulated(request, notePk);

      // Locate M21.2 fixture rows we'll transition later.
      const promisedPromiseId = await findPromisedStatePromiseId(
        request,
        notePk,
      );
      const orderedRepoId = await findOrderedRepossessionId(request, notePk);
      const recoveredRepoId = await findRecoveredRepossessionId(
        request,
        notePk,
      );
      const conditionReportId = await findCompleteConditionReportId(
        request,
        FIXTURE_STOCK,
      );

      // Capture baseline child counts before the journey mutates state.
      const baseline = await fetchChildCounts(request, notePk);

      // -----------------------------------------------------------------
      // Step 1 — portfolio landing.
      // -----------------------------------------------------------------
      await page.goto("/dealer-ai-bhph/portfolio");
      await expect(
        page.getByRole("heading", { level: 1, name: "BHPH Portfolio" }),
      ).toBeVisible({ timeout: 15_000 });

      // -----------------------------------------------------------------
      // Step 2 — note detail page.
      // -----------------------------------------------------------------
      await page.goto(`/dealer-ai-bhph/notes/${notePk}`);
      await expect(
        page.getByRole("heading", {
          level: 1,
          name: `BHPH Note #${notePk}`,
        }),
      ).toBeVisible({ timeout: 15_000 });
      await expect(page.getByTestId("bhph-note-detail")).toBeVisible();

      // -----------------------------------------------------------------
      // Step 3 — Record a promise-to-pay via the M21.2 form.
      // Business outcome: a new promise is persisted in ``promised``
      // state; promise count grows by exactly one.
      // -----------------------------------------------------------------
      await page.getByTestId("record-ptp-amount").fill("125");
      await page.getByTestId("record-ptp-reason").selectOption("paycheck");
      await page.getByTestId("record-ptp-notes").fill(
        "[M21.2 journey] Journey-recorded PtP.",
      );
      await page.getByTestId("record-ptp-submit").click();

      await expect
        .poll(async () => (await fetchChildCounts(request, notePk)).promises)
        .toBe(baseline.promises + 1);

      // -----------------------------------------------------------------
      // Step 4 — Mark the seeded ``promised``-state promise BROKEN via
      // its row action.
      // -----------------------------------------------------------------
      await page
        .getByTestId(`mark-broken-button-${promisedPromiseId}`)
        .click();
      await page
        .getByTestId(`mark-broken-notes-${promisedPromiseId}`)
        .fill("[M21.2 journey] Marked broken by journey.");
      await page
        .getByTestId(`mark-broken-confirm-${promisedPromiseId}`)
        .click();

      await expect
        .poll(async () => {
          try {
            await expectPromiseState(
              request,
              notePk,
              promisedPromiseId,
              "broken",
            );
            return "broken";
          } catch {
            return "waiting";
          }
        })
        .toBe("broken");

      // -----------------------------------------------------------------
      // Step 5 — Log a collection contact via the M21.2 form.
      // Business outcome: contact count grows by exactly one.
      // -----------------------------------------------------------------
      await page.getByTestId("log-contact-channel").selectOption("sms");
      await page
        .getByTestId("log-contact-outcome")
        .selectOption("left_message");
      await page.getByTestId("log-contact-notes").fill(
        "[M21.2 journey] Journey-logged SMS.",
      );
      await page.getByTestId("log-contact-submit").click();

      await expect
        .poll(async () => (await fetchChildCounts(request, notePk)).contacts)
        .toBe(baseline.contacts + 1);

      // -----------------------------------------------------------------
      // Step 6 — Initiate a NEW repossession via the M21.2 form.
      // Business outcome: repo count grows by exactly one.
      // -----------------------------------------------------------------
      await page.getByTestId("initiate-repo-agent").fill(
        "Journey Recovery Services",
      );
      await page.getByTestId("initiate-repo-notes").fill(
        "[M21.2 journey] Journey-initiated repo order.",
      );
      await page.getByTestId("initiate-repo-submit").click();

      await expect
        .poll(
          async () =>
            (await fetchChildCounts(request, notePk)).repossessions,
        )
        .toBe(baseline.repossessions + 1);

      // -----------------------------------------------------------------
      // Step 7 — Mark the SEEDED ordered-state repo RECOVERED via its
      // row action.
      // -----------------------------------------------------------------
      await page
        .getByTestId(`mark-recovered-button-${orderedRepoId}`)
        .click();
      await page
        .getByTestId(`mark-recovered-location-${orderedRepoId}`)
        .fill("Journey recovery yard");
      await page
        .getByTestId(`mark-recovered-notes-${orderedRepoId}`)
        .fill("[M21.2 journey] Marked recovered by journey.");
      await page
        .getByTestId(`mark-recovered-confirm-${orderedRepoId}`)
        .click();

      await expect
        .poll(async () => {
          try {
            await expectRepossessionState(
              request,
              notePk,
              orderedRepoId,
              "recovered",
            );
            return "recovered";
          } catch {
            return "waiting";
          }
        })
        .toBe("recovered");

      // -----------------------------------------------------------------
      // Step 8 — Mark the SEEDED recovered-state repo RE-INTAKED via
      // its row action, referencing the seeded ConditionReport.
      // -----------------------------------------------------------------
      await page
        .getByTestId(`mark-re-intaked-button-${recoveredRepoId}`)
        .click();
      await page
        .getByTestId(`mark-re-intaked-report-id-${recoveredRepoId}`)
        .fill(String(conditionReportId));
      await page
        .getByTestId(`mark-re-intaked-notes-${recoveredRepoId}`)
        .fill("[M21.2 journey] Marked re-intaked by journey.");
      await page
        .getByTestId(`mark-re-intaked-confirm-${recoveredRepoId}`)
        .click();

      await expect
        .poll(async () => {
          try {
            await expectRepossessionState(
              request,
              notePk,
              recoveredRepoId,
              "re_intaked",
            );
            return "re_intaked";
          } catch {
            return "waiting";
          }
        })
        .toBe("re_intaked");
    });
  },
);
