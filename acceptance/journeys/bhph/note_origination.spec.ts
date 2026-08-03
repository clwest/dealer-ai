// Milestone 23 · Increment 2 — BHPH note origination workflow journey.
//
// Guiding principle: this journey is an operational acceptance
// contract, not a UI automation project. If it passes, a dealership
// operator (bhph_collector persona — the M12/M21 permission gate is
// IsSalesManagerOrOwnerAtActiveDealership so the collector persona
// has origination authority in practice) can originate a BHPH note
// against a shipped BHPH-marked sale entirely through the M12.7
// portfolio dashboard + the new M23.2 form + dialog, and the
// resulting note lands durably at the service layer with the
// expected terms.
//
// Seeded state:
// - Existing acceptance-bhph-collector persona (sales_manager @
//   default dealership) — provisioned by
//   seed_journey_bhph_collections_workflow (M20.4).
// - M23.2 additive fixture: a distinct BHPH-marked Sale
//   (finance_type=SALE_FINANCE_TYPE_BHPH) with the "M23-BHPH-ORIG"
//   vehicle attached and NO BhphNote — the journey creates the
//   note against this sale. Seed prints
//   `m23_orig_sale_pk=<N>` in its SUCCESS message so this journey
//   parses the pk via invokeSeed() output before running.
// - Payment cleanup on re-invocation keeps the fixture reversible
//   across suite re-runs without --reset (analogous to M22.2's
//   reversal cleanup).
//
// Journey steps:
// 1. Look up the M23.2 origination fixture sale pk via
//    invokeSeed() stdout (the seed is idempotent — re-invocation
//    is safe).
// 2. Owner (bhph_collector persona) lands on
//    /dealer-ai-bhph/portfolio.
// 3. Click "Add note" — the origination dialog opens.
// 4. Fill sale_id, principal, APR, term weeks, cadence, first
//    payment due.
// 5. Click "Originate note" — dialog closes on success.
// 6. Business-outcome assertion via the admin API — a BhphNote
//    exists targeting the fixture sale with the expected terms.
//
// Per M23 §5.f Option B (journey-as-verifier): no manual pre-
// verification. The first passing run IS the evidence that the
// shipped surface is operationally complete.

import { test, expect } from "@playwright/test";

import { expectBhphNoteOriginated } from "../../support/assertions/bhph";
import { invokeSeed } from "../../support/seed/invoke";

const FIXTURE_PRINCIPAL = "7500.00";
const FIXTURE_APR = "18.50";
const FIXTURE_TERM_WEEKS = 78;
const FIXTURE_PAYMENT_FREQUENCY = "biweekly" as const;

/** Parse the M23.2 origination fixture sale pk from the seed's
 * SUCCESS message. The seed is idempotent — running it again is
 * safe and gives us the current pk without needing a separate
 * lookup endpoint. */
function parseM23OrigSalePk(stdout: string): number {
  const match = stdout.match(/m23_orig_sale_pk=(\d+)/);
  expect(
    match,
    `seed stdout missing 'm23_orig_sale_pk=<N>' marker.\nstdout:\n${stdout}`,
  ).not.toBeNull();
  return Number(match![1]);
}

test.describe(
  "BHPH note origination — full origination path (M23.2)",
  () => {
    test("operator can originate a BHPH note against a BHPH-marked sale", async ({
      page,
      request,
    }) => {
      // ---------------------------------------------------------------
      // Step 1 — resolve the fixture sale pk from the seed.
      // ---------------------------------------------------------------
      const seedResult = invokeSeed("seed_journey_bhph_collections_workflow");
      const saleId = parseM23OrigSalePk(seedResult.stdout);

      // ---------------------------------------------------------------
      // Step 2 — land on the BHPH portfolio.
      // ---------------------------------------------------------------
      await page.goto("/dealer-ai-bhph/portfolio");
      await expect(
        page.getByRole("heading", { level: 1, name: "BHPH Portfolio" }),
      ).toBeVisible({ timeout: 15_000 });

      const addNoteCta = page.getByTestId("portfolio-add-note-cta");
      await expect(
        addNoteCta,
        "'Add note' CTA should be visible on the portfolio's Notes card",
      ).toBeVisible({ timeout: 15_000 });
      await expect(addNoteCta).toBeEnabled({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 3 — open the origination dialog.
      // ---------------------------------------------------------------
      await addNoteCta.click();
      const dialog = page.getByRole("dialog", {
        name: /Originate a BHPH note/i,
      });
      await expect(
        dialog,
        "origination dialog should open with the expected heading",
      ).toBeVisible({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 4 — fill the form with the M23.2 fixture terms.
      // ---------------------------------------------------------------
      await dialog
        .getByTestId("record-bhph-note-sale-id")
        .fill(String(saleId));
      await dialog
        .getByTestId("record-bhph-note-principal")
        .fill(FIXTURE_PRINCIPAL);
      await dialog.getByTestId("record-bhph-note-apr").fill(FIXTURE_APR);
      await dialog
        .getByTestId("record-bhph-note-term-weeks")
        .fill(String(FIXTURE_TERM_WEEKS));
      await dialog
        .getByTestId("record-bhph-note-frequency")
        .selectOption(FIXTURE_PAYMENT_FREQUENCY);
      // first_payment_due defaults to today — leave it as-is.

      // ---------------------------------------------------------------
      // Step 5 — submit + verify the dialog closes.
      // ---------------------------------------------------------------
      const submit = dialog.getByTestId("record-bhph-note-submit");
      await expect(submit).toBeEnabled({ timeout: 5_000 });
      await submit.click();

      await expect(
        dialog,
        "origination dialog should close after a successful confirm",
      ).not.toBeVisible({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 6 — business-outcome assertion via the admin API.
      // ---------------------------------------------------------------
      await expectBhphNoteOriginated(request, saleId, {
        principal: FIXTURE_PRINCIPAL,
        apr: FIXTURE_APR,
        termWeeks: FIXTURE_TERM_WEEKS,
        paymentFrequency: FIXTURE_PAYMENT_FREQUENCY,
      });
    });
  },
);
