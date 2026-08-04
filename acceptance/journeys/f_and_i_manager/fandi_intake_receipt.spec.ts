// Milestone 32 · Increment 3 (SESSION_209) — F&I intake receipt
// operational-completion journey.
//
// Guiding principle: this suite is an operational acceptance contract,
// not a UI automation project. The journey validates the M32 anchor
// business question (F&I-side portion): given a hand-off from sales,
// can the F&I team receive and view a complete, actionable incoming
// credit application in Dealer OS — with unambiguous provenance
// (four-square terms + who authored + who approved + hand-off
// timing) — all without needing sales-side access?
//
// **Fixture independence guarantee per M32 §5.c R11.** This spec
// reads a pre-seeded `Intake Iris` fixture provisioned by
// `seed_journey_fandi_intake_receipt` — a dedicated lead + vehicle +
// approved+handed-off writeup + paired CA. Distinct rows from any
// M32.2 sales-side fixture. Test order irrelevant; parallelism-safe.
//
// Runs under the `f_and_i_manager` project per M32.2 handoff §7
// Amendment 2 (file-per-persona rather than dual-describe in one
// file). Uses the new M32.3 `AUTH_STORAGE.fAndIManager` storage
// state.
//
// Per MILESTONE_32_PLANNING.md §5.b D8-revised: the incoming intake
// row is **non-navigational** — F&I role cannot access
// `admin_lead_detail` (sales-role-gated), so no row-link would work.
// Every triage field is rendered inline. The journey asserts both
// the inline data presence AND the non-navigational posture.

import { test, expect } from "@playwright/test";

const FIXTURE_LEAD_NAME = "Intake Iris";
const FIXTURE_VEHICLE_STOCK = "FANDI-INTAKE-1";

test.describe("fandi-intake-receipt", () => {
  test("F&I manager sees the Intake Iris incoming application with full inline context (non-navigational)", async ({
    page,
  }) => {
    // -----------------------------------------------------------------
    // Step 1 — navigate to the F&I incoming intake page.
    // -----------------------------------------------------------------
    await page.goto("/dealer-ai-f-and-i/incoming");
    await expect(
      page.getByRole("heading", { level: 1, name: "Incoming Applications" }),
    ).toBeVisible({ timeout: 15_000 });

    // -----------------------------------------------------------------
    // Step 2 — wait for the load state to settle. Confirm the page is
    // populated (not empty / not forbidden / not error).
    // -----------------------------------------------------------------
    await expect(page.getByTestId("incoming-loading")).not.toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByTestId("incoming-empty")).not.toBeVisible();
    await expect(page.getByTestId("incoming-forbidden")).not.toBeVisible();
    await expect(page.getByTestId("incoming-error")).not.toBeVisible();

    // -----------------------------------------------------------------
    // Step 3 — locate the Intake Iris row by lead name. We don't hard-
    // code the CA pk because seed order may vary; instead we scope
    // by the deterministic lead name in the row.
    // -----------------------------------------------------------------
    const irisRow = page
      .locator('[data-testid^="incoming-row-"]')
      .filter({ hasText: FIXTURE_LEAD_NAME });
    await expect(
      irisRow,
      "Intake Iris fixture row should appear in F&I intake queue",
    ).toHaveCount(1, { timeout: 10_000 });

    // -----------------------------------------------------------------
    // Step 4 — assert inline lead context (name + phone + email).
    // Non-navigational: F&I cannot fetch admin_lead_detail (sales-
    // role-gated), so all lead info must be inline.
    // -----------------------------------------------------------------
    await expect(irisRow.getByText(FIXTURE_LEAD_NAME)).toBeVisible();
    await expect(irisRow.getByText(/\+15553201501/)).toBeVisible();
    await expect(irisRow.getByText(/intake-iris@example.com/)).toBeVisible();

    // -----------------------------------------------------------------
    // Step 5 — assert inline vehicle context.
    // -----------------------------------------------------------------
    await expect(
      irisRow.getByText(new RegExp(`Stock #${FIXTURE_VEHICLE_STOCK}`)),
    ).toBeVisible();
    await expect(irisRow.getByText(/2024 Ford F-150/)).toBeVisible();

    // -----------------------------------------------------------------
    // Step 6 — assert inline four-square terms (matches the seed
    // fixture's FIXTURE_TERMS exactly). Scoped to the terms-summary
    // testid to avoid strict-mode collision with the notes <pre>
    // (which contains the M11.3 handoff-prefix text like
    // "- Vehicle price: $42500.00" that would also match).
    // -----------------------------------------------------------------
    const terms = irisRow.locator('[data-testid="incoming-terms-summary"]');
    await expect(terms).toBeVisible();
    await expect(terms.getByText("42500.00", { exact: true })).toBeVisible();
    await expect(terms.getByText("7500.00", { exact: true })).toBeVisible();
    await expect(terms.getByText("3000.00", { exact: true })).toBeVisible();
    await expect(terms.getByText("585.00", { exact: true })).toBeVisible();
    await expect(terms.getByText("60 mo", { exact: true })).toBeVisible();
    await expect(terms.getByText("6.99%", { exact: true })).toBeVisible();

    // -----------------------------------------------------------------
    // Step 7 — assert Incoming state badge.
    // -----------------------------------------------------------------
    await expect(
      irisRow.locator('[data-testid^="incoming-state-"]'),
    ).toBeVisible();
    await expect(irisRow.getByText("Incoming").first()).toBeVisible();

    // -----------------------------------------------------------------
    // Step 8 — assert attribution (written-up-by + approved-by user
    // IDs — the seed provisions the sales-manager persona for both).
    // -----------------------------------------------------------------
    await expect(irisRow.getByText(/Written up by #\d+/)).toBeVisible();
    await expect(irisRow.getByText(/Approved by #\d+/)).toBeVisible();

    // -----------------------------------------------------------------
    // Step 9 — assert M11.3 handoff notes prefix in the notes
    // <details> block (proves the paired CA carries the writeup
    // provenance text prefix even before consulting the D9-revised²
    // FK — belt + suspenders).
    // -----------------------------------------------------------------
    const notesElement = irisRow.locator(
      '[data-testid^="incoming-notes-"]',
    );
    // The <details> starts collapsed but the notes content is present
    // in the DOM. Assert the notes text contains the handoff prefix.
    await expect(notesElement).toContainText(/Deal write-up #\d+ handoff:/);
    await expect(notesElement).toContainText("Vehicle price: $42500.00");

    // -----------------------------------------------------------------
    // Step 10 — non-navigational-row assertion per D8-revised.
    // Confirms the row is not wrapped in an <a> and has no click
    // handler. F&I role can't access admin_lead_detail; a row-link
    // would 403.
    // -----------------------------------------------------------------
    // Row's parent chain should not include an <a>.
    const anchorCount = await irisRow.locator("xpath=ancestor::a").count();
    expect(
      anchorCount,
      "F&I intake rows must be non-navigational — no anchor ancestor",
    ).toBe(0);
    // Row itself is a plain <li> (not <button>, not a role that
    // implies clickability).
    const tagName = await irisRow.evaluate((el) => el.tagName);
    expect(tagName).toBe("LI");
  });
});
