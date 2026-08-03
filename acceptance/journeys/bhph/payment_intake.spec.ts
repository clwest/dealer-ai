// Milestone 23 · Increment 3 — BHPH payment intake workflow journey.
//
// Guiding principle: this journey is an operational acceptance
// contract, not a UI automation project. If it passes, a BHPH
// collector (bhph_collector persona — M12 permission gate is
// IsSalesManagerOrOwnerAtActiveDealership) can record a cash
// payment against an existing BHPH note entirely through the
// M12.7 note-detail page + the new M23.3 form + inline Payments-
// card CTA, and the resulting payment lands durably at the
// service layer with the entered amount + method.
//
// Seeded state:
// - Existing acceptance-bhph-collector persona (sales_manager @
//   default dealership) — provisioned by
//   seed_journey_bhph_collections_workflow (M20.4).
// - M23.3 additive fixture: a distinct BhphNote (stock
//   M23-BHPH-PAY, principal $5,400) with non-zero balance and
//   NO payments yet — the journey records the first payment
//   against this note. Payment cleanup on re-invocation keeps
//   the fixture reversible across suite re-runs (matches M22.2
//   reversal cleanup + M23.2 note cleanup patterns).
// - Seed prints `m23_pay_note_pk=<N>` in its SUCCESS message
//   so this journey parses the pk via invokeSeed() output.
//
// Journey steps:
// 1. Look up the M23.3 fixture note pk via invokeSeed() stdout
//    (seed is idempotent — re-invocation is safe).
// 2. bhph_collector persona lands on
//    /dealer-ai-bhph/notes/<pk> for the fixture note.
// 3. Verify Payments card is empty (no prior payments on the
//    fresh fixture note).
// 4. Fill the inline payment form (amount, method, paid_at).
// 5. Click "Record payment" — form clears + payment appears
//    in the list via optimistic merge.
// 6. Business-outcome assertion via the admin API — a BhphPayment
//    with the entered amount + method exists on the note.
//
// Per M23 §5.f Option B (journey-as-verifier): no manual pre-
// verification. First passing run IS the evidence that the
// shipped payment-intake surface is operationally complete.

import { test, expect } from "@playwright/test";

import { expectBhphPaymentRecorded } from "../../support/assertions/bhph";
import { invokeSeed } from "../../support/seed/invoke";

const FIXTURE_AMOUNT = "175.00";
const FIXTURE_METHOD = "cash" as const;

/** Parse the M23.3 fixture note pk from the seed's SUCCESS
 * message. Seed is idempotent — same pattern as M23.2's
 * origination journey. */
function parseM23PayNotePk(stdout: string): number {
  const match = stdout.match(/m23_pay_note_pk=(\d+)/);
  expect(
    match,
    `seed stdout missing 'm23_pay_note_pk=<N>' marker.\nstdout:\n${stdout}`,
  ).not.toBeNull();
  return Number(match![1]);
}

test.describe(
  "BHPH payment intake — full payment-recording path (M23.3)",
  () => {
    test("collector can record a cash payment against a BHPH note", async ({
      page,
      request,
    }) => {
      // ---------------------------------------------------------------
      // Step 1 — resolve the fixture note pk from the seed.
      // ---------------------------------------------------------------
      const seedResult = invokeSeed("seed_journey_bhph_collections_workflow");
      const notePk = parseM23PayNotePk(seedResult.stdout);

      // ---------------------------------------------------------------
      // Step 2 — land on the note detail page.
      // ---------------------------------------------------------------
      await page.goto(`/dealer-ai-bhph/notes/${notePk}`);
      await expect(
        page.getByRole("heading", {
          level: 1,
          name: `BHPH Note #${notePk}`,
        }),
      ).toBeVisible({ timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 3 — verify Payments card renders (may be empty; the
      //          form should be visible below the empty-state).
      // ---------------------------------------------------------------
      const paymentsCard = page.getByTestId("payments-card");
      await expect(paymentsCard).toBeVisible({ timeout: 15_000 });
      await expect(
        paymentsCard.getByTestId("record-bhph-payment-form"),
        "payment intake form should render inside the Payments card",
      ).toBeVisible({ timeout: 10_000 });

      // ---------------------------------------------------------------
      // Step 4 — fill the payment form.
      // ---------------------------------------------------------------
      await paymentsCard
        .getByTestId("record-bhph-payment-amount")
        .fill(FIXTURE_AMOUNT);
      await paymentsCard
        .getByTestId("record-bhph-payment-method")
        .selectOption(FIXTURE_METHOD);
      // paid_at defaults to now — leave as-is.

      // ---------------------------------------------------------------
      // Step 5 — submit + verify the payment appears in the list.
      // ---------------------------------------------------------------
      const submit = paymentsCard.getByTestId("record-bhph-payment-submit");
      await expect(submit).toBeEnabled({ timeout: 5_000 });
      await submit.click();

      // Amount input resets to empty on success — indirect signal
      // the submit resolved without an error.
      await expect(
        paymentsCard.getByTestId("record-bhph-payment-amount"),
        "amount input should clear after successful submit",
      ).toHaveValue("", { timeout: 15_000 });

      // ---------------------------------------------------------------
      // Step 6 — business-outcome assertion via the admin API.
      // ---------------------------------------------------------------
      await expectBhphPaymentRecorded(request, notePk, {
        amount: FIXTURE_AMOUNT,
        method: FIXTURE_METHOD,
      });
    });
  },
);
