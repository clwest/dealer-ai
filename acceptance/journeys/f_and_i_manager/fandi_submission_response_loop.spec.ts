// Milestone 35 · Increment 2 (SESSION_218) — F&I lender-submission
// send-and-response loop operational-completion journey.
//
// Guiding principle: this suite is an operational acceptance contract,
// not a UI automation project. The journey validates the M35 anchor
// business question: can an F&I manager record where a structured
// deal was submitted, capture the lender's response, and see the
// resulting operational state — all without leaving Dealer OS?
//
// **Fixture independence guarantee per M35 §5.c R7 + M35 D10.** This
// spec reads a pre-seeded `Submission Sasha` fixture provisioned by
// `seed_journey_fandi_submission_response` — a dedicated lead +
// vehicle + approved+handed-off writeup + paired CA + pre-created
// DealStructure + Yuma Community Bank LenderProgram (no
// LenderSubmission yet). Distinct rows from M32.3 Intake Iris + M33.2
// Structure Sam fixtures. Test order irrelevant; parallelism-safe.
//
// **`@rerun-hygiene` tag** per M34.0 D7 + M35 D9. First re-application
// of durable lesson (ff): acceptance journeys must be independently
// rerunnable against shared state. Submission Sasha seed idempotent
// from first shipping day — deletes any prior-run LenderSubmissions
// at re-entry. M35.2 proof at close: back-to-back
// `npx playwright test --grep "@rerun-hygiene"` invocations
// (NOT `--repeat-each=2` per M34.2 §0.a correction).
//
// **UI language contract per M35 D6 + D11 + R4 (verified §4.7):**
// the journey asserts (a) the record-submission action uses
// record-vs-transmit vocabulary; (b) the pending state chip label is
// "Submitted — awaiting response"; (c) the response action headers
// differentiate between record mode (pending) and update mode
// (terminal); (d) the approved chip appears after recording the
// response; (e) proposed DealStructure values are NEVER labeled as
// lender-approved terms in the read view.
//
// Runs under the `f_and_i_manager` project (persona shipped M32.3;
// reused unchanged for M35.2 — no new persona work).

import { test, expect } from "@playwright/test";

const FIXTURE_LEAD_NAME = "Submission Sasha";
const FIXTURE_LENDER_PROGRAM_NAME = "Yuma Community Bank";

// M35 D11 + R4 prohibited language. Extends the M33 forbidden
// vocabulary with M35's record-vs-transmit invariant.
const FORBIDDEN_LENDER_APPROVED_TERMS_LANGUAGE =
  /lender[- ]approved (terms|value|amount|apr|payment|rate)/i;
const FORBIDDEN_TRANSMIT_LANGUAGE =
  /(send to lender|submit to lender|transmit(?:ting|ted)?|contact lender)/i;

test.describe("fandi-submission-response-loop @rerun-hygiene", () => {
  test("F&I manager records a submission, records the lender response, then corrects the response", async ({
    page,
  }) => {
    // -----------------------------------------------------------------
    // Step 1 — navigate to the F&I incoming intake page.
    // -----------------------------------------------------------------
    await page.goto("/dealer-ai-f-and-i/incoming");
    await expect(
      page.getByRole("heading", { level: 1, name: "Incoming Applications" }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("incoming-loading")).not.toBeVisible({
      timeout: 10_000,
    });

    // -----------------------------------------------------------------
    // Step 2 — locate the Submission Sasha row by lead name.
    // -----------------------------------------------------------------
    const sashaRow = page
      .locator('[data-testid^="incoming-row-"]')
      .filter({ hasText: FIXTURE_LEAD_NAME });
    await expect(
      sashaRow,
      "Submission Sasha fixture row should appear in F&I intake queue",
    ).toHaveCount(1, { timeout: 10_000 });

    // -----------------------------------------------------------------
    // Step 3 — assert pre-flight state = In progress (DealStructure
    // exists, no LenderSubmission yet).
    // -----------------------------------------------------------------
    await expect(
      sashaRow.locator(
        '[data-testid^="incoming-row-status-in-progress-"]',
      ),
    ).toBeVisible();

    // -----------------------------------------------------------------
    // Step 4 — assert "Record lender submission" action is visible;
    // the response actions are absent (D8 state-conditional gating).
    // -----------------------------------------------------------------
    const recordSubmissionButton = sashaRow.locator(
      '[data-testid^="incoming-row-record-lender-submission-"]',
    );
    await expect(recordSubmissionButton).toBeVisible();
    await expect(
      sashaRow.locator(
        '[data-testid^="incoming-row-record-lender-response-"]',
      ),
    ).toHaveCount(0);
    await expect(
      sashaRow.locator(
        '[data-testid^="incoming-row-update-lender-response-"]',
      ),
    ).toHaveCount(0);
    // The record-submission button text asserts record-vs-transmit
    // vocabulary explicitly (D6 + R4).
    await expect(recordSubmissionButton).toHaveText(
      "Record lender submission",
    );

    // -----------------------------------------------------------------
    // Step 5 — click "Record lender submission" to open the panel.
    // -----------------------------------------------------------------
    await recordSubmissionButton.click();
    const recordPanel = page.getByTestId("lender-submission-record-panel");
    await expect(recordPanel).toBeVisible();
    const recordForm = page.getByTestId("lender-submission-record-form");
    await expect(recordForm).toBeVisible();

    // -----------------------------------------------------------------
    // Step 6 — assert record-form language contract:
    //  - header uses "Record lender submission"
    //  - submit button reads "Record submission"
    //  - form contains no transmit-implying vocabulary
    // -----------------------------------------------------------------
    await expect(
      recordForm.getByRole("heading", { name: "Record lender submission" }),
    ).toBeVisible();
    const recordSubmitButton = recordForm.getByTestId(
      "lender-submission-record-submit",
    );
    await expect(recordSubmitButton).toHaveText("Record submission");
    const recordFormText = (await recordForm.textContent()) ?? "";
    expect(
      recordFormText,
      "Record form must not imply Dealer OS transmits to the lender",
    ).not.toMatch(FORBIDDEN_TRANSMIT_LANGUAGE);

    // -----------------------------------------------------------------
    // Step 7 — the LenderProgram selector loads; the Yuma Community
    // Bank option appears.
    // -----------------------------------------------------------------
    const programSelect = recordForm.getByTestId(
      "lender-submission-program-select",
    );
    await expect(programSelect).toBeVisible({ timeout: 10_000 });
    await expect(
      programSelect.locator("option", {
        hasText: FIXTURE_LENDER_PROGRAM_NAME,
      }),
    ).toHaveCount(1);

    // Submit is disabled until a program is selected.
    await expect(recordSubmitButton).toBeDisabled();

    // -----------------------------------------------------------------
    // Step 8 — select the program + submit.
    // -----------------------------------------------------------------
    await programSelect.selectOption({ label: FIXTURE_LENDER_PROGRAM_NAME });
    await expect(recordSubmitButton).toBeEnabled();
    await recordSubmitButton.click();
    await expect(recordPanel).not.toBeVisible({ timeout: 10_000 });

    // -----------------------------------------------------------------
    // Step 9 — re-locate the row (post-refetch) and assert chip flips
    // to "Submitted — awaiting response". Three-signal a11y verified.
    // -----------------------------------------------------------------
    const sashaRowAfterRecord = page
      .locator('[data-testid^="incoming-row-"]')
      .filter({ hasText: FIXTURE_LEAD_NAME });
    await expect(sashaRowAfterRecord).toHaveCount(1, { timeout: 10_000 });
    const submittedChip = sashaRowAfterRecord.locator(
      '[data-testid^="incoming-row-status-submitted-"]',
    );
    await expect(submittedChip).toBeVisible();
    await expect(submittedChip).toHaveText(
      "Submitted — awaiting response",
    );
    await expect(
      sashaRowAfterRecord.getByLabel("Submitted — awaiting response"),
    ).toBeVisible();
    // In-progress / Approved / Counter / Declined chips must be absent.
    await expect(
      sashaRowAfterRecord.locator(
        '[data-testid^="incoming-row-status-in-progress-"]',
      ),
    ).toHaveCount(0);
    await expect(
      sashaRowAfterRecord.locator(
        '[data-testid^="incoming-row-status-approved-"]',
      ),
    ).toHaveCount(0);

    // -----------------------------------------------------------------
    // Step 10 — the "Record lender submission" action is now hidden
    // (first-loop boundary per D8); "Record lender response" appears.
    // -----------------------------------------------------------------
    await expect(
      sashaRowAfterRecord.locator(
        '[data-testid^="incoming-row-record-lender-submission-"]',
      ),
    ).toHaveCount(0);
    const recordResponseButton = sashaRowAfterRecord.locator(
      '[data-testid^="incoming-row-record-lender-response-"]',
    );
    await expect(recordResponseButton).toBeVisible();
    await expect(recordResponseButton).toHaveText("Record lender response");
    await expect(
      sashaRowAfterRecord.locator(
        '[data-testid^="incoming-row-update-lender-response-"]',
      ),
    ).toHaveCount(0);

    // -----------------------------------------------------------------
    // Step 11 — open the response panel; header confirms record mode.
    // -----------------------------------------------------------------
    await recordResponseButton.click();
    const responsePanel = page.getByTestId(
      "lender-submission-response-panel",
    );
    await expect(responsePanel).toBeVisible();
    const responseForm = page.getByTestId(
      "lender-submission-response-form",
    );
    await expect(responseForm).toBeVisible();
    await expect(
      page.getByTestId("lender-submission-response-header"),
    ).toHaveText("Record lender response");
    const responseSubmitButton = responseForm.getByTestId(
      "lender-submission-response-submit",
    );
    await expect(responseSubmitButton).toHaveText("Record response");

    // -----------------------------------------------------------------
    // Step 12 — select "approved" + submit.
    // -----------------------------------------------------------------
    await responseForm
      .getByTestId("lender-submission-response-approved")
      .check();
    await responseSubmitButton.click();
    await expect(responsePanel).not.toBeVisible({ timeout: 10_000 });

    // -----------------------------------------------------------------
    // Step 13 — re-locate the row and assert chip flips to "Approved".
    // -----------------------------------------------------------------
    const sashaRowAfterResponse = page
      .locator('[data-testid^="incoming-row-"]')
      .filter({ hasText: FIXTURE_LEAD_NAME });
    await expect(sashaRowAfterResponse).toHaveCount(1, { timeout: 10_000 });
    const approvedChip = sashaRowAfterResponse.locator(
      '[data-testid^="incoming-row-status-approved-"]',
    );
    await expect(approvedChip).toBeVisible();
    await expect(approvedChip).toHaveText("Approved");

    // -----------------------------------------------------------------
    // Step 14 — assert the row-action switches to "Update lender
    // response" (D7 mode-conditional per D8 state gating).
    // -----------------------------------------------------------------
    const updateResponseButton = sashaRowAfterResponse.locator(
      '[data-testid^="incoming-row-update-lender-response-"]',
    );
    await expect(updateResponseButton).toBeVisible();
    await expect(updateResponseButton).toHaveText("Update lender response");
    // Record actions must not reappear on terminal rows.
    await expect(
      sashaRowAfterResponse.locator(
        '[data-testid^="incoming-row-record-lender-submission-"]',
      ),
    ).toHaveCount(0);
    await expect(
      sashaRowAfterResponse.locator(
        '[data-testid^="incoming-row-record-lender-response-"]',
      ),
    ).toHaveCount(0);

    // -----------------------------------------------------------------
    // Step 15 — open the update-response panel; header confirms update
    // mode; the current status is pre-selected.
    // -----------------------------------------------------------------
    await updateResponseButton.click();
    await expect(responsePanel).toBeVisible();
    await expect(
      page.getByTestId("lender-submission-response-header"),
    ).toHaveText("Update lender response");
    await expect(
      responseForm.getByTestId("lender-submission-response-submit"),
    ).toHaveText("Update response");
    // Pre-selected: approved.
    await expect(
      responseForm.getByTestId("lender-submission-response-approved"),
    ).toBeChecked();

    // -----------------------------------------------------------------
    // Step 16 — correct the response: switch to counter-offer + submit.
    // Exercises the any-to-any correction contract (M10.3 preserved).
    // -----------------------------------------------------------------
    await responseForm
      .getByTestId("lender-submission-response-counter")
      .check();
    await responseForm
      .getByTestId("lender-submission-response-submit")
      .click();
    await expect(responsePanel).not.toBeVisible({ timeout: 10_000 });

    // -----------------------------------------------------------------
    // Step 17 — chip flips to "Counter-offer received". Same-record
    // update per D7; NOT a new LenderSubmission.
    // -----------------------------------------------------------------
    const sashaRowAfterCorrection = page
      .locator('[data-testid^="incoming-row-"]')
      .filter({ hasText: FIXTURE_LEAD_NAME });
    await expect(sashaRowAfterCorrection).toHaveCount(1, { timeout: 10_000 });
    const counterChip = sashaRowAfterCorrection.locator(
      '[data-testid^="incoming-row-status-counter-"]',
    );
    await expect(counterChip).toBeVisible();
    await expect(counterChip).toHaveText("Counter-offer received");
    // Approved chip must be gone; only one terminal chip at a time.
    await expect(
      sashaRowAfterCorrection.locator(
        '[data-testid^="incoming-row-status-approved-"]',
      ),
    ).toHaveCount(0);

    // -----------------------------------------------------------------
    // Step 18 — full-page D11-refined language contract assertion.
    // The chip may say "Approved" or "Counter-offer received" — those
    // are truthful workflow-state labels. But no text anywhere may
    // label individual DealStructure values as "lender-approved terms"
    // (M35 does not capture approval_terms).
    // -----------------------------------------------------------------
    const pageText = (await page.textContent("body")) ?? "";
    expect(
      pageText,
      "Page must not label individual DealStructure values as lender-approved terms",
    ).not.toMatch(FORBIDDEN_LENDER_APPROVED_TERMS_LANGUAGE);
    expect(
      pageText,
      "Page must not imply Dealer OS transmits to the lender",
    ).not.toMatch(FORBIDDEN_TRANSMIT_LANGUAGE);
  });
});
