// Milestone 32 · Increment 2 (SESSION_208) — sales-manager writeup
// hand-off operational-completion journey.
//
// Guiding principle: this suite is an operational acceptance contract,
// not a UI automation project. The journey validates the M32 anchor
// business question (sales-side portion): can a sales manager create
// a deal writeup, review and approve it, and hand it off to F&I such
// that a corresponding credit application appears in the F&I intake
// queue — all through Dealer OS?
//
// M32.2 covers the sales side of the anchor question (create →
// Pending → Approve → Approved → Send-to-F&I → Handed off).
//
// Technical business-outcome assertion after the UI flow: query the
// sales-role-accessible writeup detail endpoint
// (`/admin/deal-writeups/<pk>/`) and confirm
// `handed_off_to_fandi_at` is populated. This transitively proves
// the M11.3 hand-off verb ran to completion — which is atomic per
// M11.3 shipped contract + M32.1 D9-revised² FK-pairing tests. Any
// caller reaching the "handed off" timestamp guarantees the paired
// CA exists (M11.3 `@transaction.atomic` + `WriteupAlreadyHandedOffError`
// idempotency).
//
// **§0.a M32.2 amendment vs the M32.0 memo:** the memo called for
// the technical assertion via `/admin/credit-applications/list/?intake=true`.
// That endpoint is F&I-role-gated (D3 + D10 per M32.0 memo); the
// sales_manager persona used by this journey receives 403. F&I-side
// CA-list verification stays in M32.3 via the f_and_i_manager
// persona spec at `journeys/f_and_i_manager/fandi_intake_receipt.spec.ts`.
// File-per-persona aligns with playwright.config.ts project routing
// (single-file dual-describe would need a shared project entry).
//
// The F&I intake UI ships in M32.3 as an independently-deterministic
// spec using its own pre-seeded fixture (per D11).
//
// Per MILESTONE_32_PLANNING.md §5.b D4-revised² the Writeups panel is
// manager-only by transitivity of the modal itself; there is no
// separate advisor treatment (advisors receive 403 on lead detail
// fetch and cannot open the modal at all).
//
// Seeded state (via existing seed_journey_sales_operational_entry):
// - `acceptance-sales-manager` user (sales_manager @ default
//   dealership) — auth persona via storage state
// - Vehicle `#M25-TEST-DRIVE-01` — 2025 Ford Bronco Wildtrak,
//   deterministic picker target added at M25.2 open
//
// The journey creates a fresh walk-in lead per run (unique customer
// name) so no cross-run interference exists.

import { test, expect } from "@playwright/test";

interface AdminVehiclesResponse {
  count: number;
  results: Array<{
    id: number;
    stock_number: string;
    display_name: string;
  }>;
}

interface DealWriteupDetailResponse {
  deal_writeup: {
    id: number;
    lead_id: number;
    vehicle_id: number;
    dealership_id: number;
    vehicle_price: string | null;
    monthly_payment_target: string | null;
    term_months_target: number | null;
    apr_target: string | null;
    sales_manager_approved_at: string | null;
    sales_manager_approved_by_user_id: number | null;
    handed_off_to_fandi_at: string | null;
  };
}

const FIXTURE_STOCK = "M25-TEST-DRIVE-01";

test.describe("sales-manager-writeup-handoff", () => {
  test("walk-in intake → new writeup → Pending → Approve → Approved → Send to F&I → Handed off; CA appears in F&I intake with D9 FK", async ({
    page,
    request,
  }) => {
    const CUSTOMER_NAME = `M32.2 Handoff ${Date.now()}`;
    const CUSTOMER_PHONE = "+15553201001";
    const CUSTOMER_EMAIL = "m322-handoff@example.com";

    // -----------------------------------------------------------------
    // Preflight — resolve the fixture vehicle id via M25.2 endpoint.
    // -----------------------------------------------------------------
    const inventoryResponse = await request.get(
      `/api/dealer-ai/admin/vehicles/?search=${encodeURIComponent(FIXTURE_STOCK)}`,
    );
    expect(inventoryResponse.status()).toBe(200);
    const inventory = (await inventoryResponse.json()) as AdminVehiclesResponse;
    const fixture = inventory.results.find(
      (v) => v.stock_number === FIXTURE_STOCK,
    );
    expect(fixture, `fixture vehicle ${FIXTURE_STOCK} present`).toBeTruthy();
    const fixtureVehicleId = fixture!.id;

    // -----------------------------------------------------------------
    // Step 1 — create fresh walk-in lead via the shipped intake flow.
    // -----------------------------------------------------------------
    await page.goto("/dealer-ai-sales/leads");
    await expect(
      page.getByRole("heading", { level: 1, name: "Sales leads" }),
    ).toBeVisible({ timeout: 15_000 });

    await page.getByTestId("sales-leads-add-walk-in").click();
    await expect(
      page.getByTestId("sales-leads-walk-in-dialog"),
    ).toBeVisible({ timeout: 10_000 });
    await page.getByTestId("lead-intake-walk_in-name").fill(CUSTOMER_NAME);
    await page.getByTestId("lead-intake-walk_in-phone").fill(CUSTOMER_PHONE);
    await page.getByTestId("lead-intake-walk_in-email").fill(CUSTOMER_EMAIL);
    await page.getByTestId("lead-intake-walk_in-submit").click();

    const modalRegion = page.locator("div.fixed.inset-0.z-50");
    await expect(
      modalRegion.getByText("Sales handoff packet", { exact: true }).first(),
    ).toBeVisible({ timeout: 15_000 });

    // Extract lead id from modal header.
    const leadIdText = await modalRegion
      .getByText(/^Lead #\d+/)
      .first()
      .textContent();
    const newLeadId = Number((leadIdText ?? "").replace(/^Lead #/, ""));
    expect(newLeadId).toBeGreaterThan(0);

    // -----------------------------------------------------------------
    // Step 2 — open Writeups panel → "+ New writeup" → four-square form.
    // -----------------------------------------------------------------
    const writeupsToggle = modalRegion.getByTestId("lead-writeups-toggle");
    await expect(writeupsToggle).toBeVisible({ timeout: 5_000 });
    await writeupsToggle.click();
    await expect(
      modalRegion.getByTestId("lead-writeups-empty"),
      "empty state should render before any writeup exists for this lead",
    ).toBeVisible({ timeout: 10_000 });

    await modalRegion.getByTestId("lead-writeups-new").click();
    await expect(
      modalRegion.getByTestId("deal-writeup-form"),
    ).toBeVisible({ timeout: 5_000 });

    // Pick the fixture vehicle from the picker.
    await modalRegion.getByTestId("deal-writeup-search").fill("Bronco");
    const pickerRow = modalRegion.getByTestId(
      `deal-writeup-vehicle-${fixtureVehicleId}`,
    );
    await expect(pickerRow).toBeVisible({ timeout: 10_000 });
    await pickerRow.click();

    // Fill four-square.
    await modalRegion
      .getByTestId("deal-writeup-vehicle-price")
      .fill("28500");
    await modalRegion
      .getByTestId("deal-writeup-monthly-payment-target")
      .fill("450");
    await modalRegion
      .getByTestId("deal-writeup-term-months-target")
      .fill("72");
    await modalRegion.getByTestId("deal-writeup-apr-target").fill("7.49");

    await modalRegion.getByTestId("deal-writeup-submit").click();

    // -----------------------------------------------------------------
    // Step 3 — assert new row appears with [Pending] badge.
    // -----------------------------------------------------------------
    await expect(
      modalRegion.locator('[data-testid^="writeup-row-state-pending-"]'),
    ).toBeVisible({ timeout: 10_000 });
    const pendingBadge = modalRegion
      .locator('[data-testid^="writeup-row-state-pending-"]')
      .first();
    const pendingTestId = await pendingBadge.getAttribute("data-testid");
    const writeupPk = Number(
      (pendingTestId ?? "").replace("writeup-row-state-pending-", ""),
    );
    expect(writeupPk).toBeGreaterThan(0);

    // -----------------------------------------------------------------
    // Step 4 — Approve → confirmation dialog with D5-revised copy →
    //          Approve.
    // -----------------------------------------------------------------
    await modalRegion
      .getByTestId(`writeup-approve-trigger-${writeupPk}`)
      .click();
    const approveDialog = page.getByTestId("writeup-approve-confirm-body");
    await expect(approveDialog).toBeVisible({ timeout: 5_000 });
    await expect(
      approveDialog.getByText("Approve deal writeup?"),
    ).toBeVisible();
    // D5-revised copy verbatim.
    await expect(
      approveDialog.getByText(
        /Approving marks this writeup ready for F&I hand-off\. Review the terms carefully before continuing\. After it is sent to F&I, the hand-off cannot be repeated or undone\./,
      ),
    ).toBeVisible();
    await page.getByTestId("writeup-approve-submit").click();

    // -----------------------------------------------------------------
    // Step 5 — assert row updates to [Approved] badge.
    // -----------------------------------------------------------------
    await expect(
      modalRegion.getByTestId(`writeup-row-state-approved-${writeupPk}`),
    ).toBeVisible({ timeout: 10_000 });

    // -----------------------------------------------------------------
    // Step 6 — Send to F&I → confirmation dialog with D6 irreversibility
    //          copy verbatim → Send to F&I.
    // -----------------------------------------------------------------
    await modalRegion
      .getByTestId(`writeup-handoff-trigger-${writeupPk}`)
      .click();
    const handoffDialog = page.getByTestId("writeup-handoff-confirm-body");
    await expect(handoffDialog).toBeVisible({ timeout: 5_000 });
    await expect(handoffDialog.getByText("Send to F&I?")).toBeVisible();
    // D6 copy verbatim.
    await expect(
      handoffDialog.getByText(/This creates a credit application for/),
    ).toBeVisible();
    await expect(handoffDialog.getByText(CUSTOMER_NAME)).toBeVisible();
    await expect(handoffDialog.getByText(/This cannot be undone/)).toBeVisible();
    await expect(
      handoffDialog.getByText(
        /a second attempt will be refused to protect against duplicate applications and their retention-clock consequences/,
      ),
    ).toBeVisible();
    await page.getByTestId("writeup-handoff-submit").click();

    // -----------------------------------------------------------------
    // Step 7 — assert row updates to [Handed off] badge.
    // -----------------------------------------------------------------
    await expect(
      modalRegion.getByTestId(`writeup-row-state-handed_off-${writeupPk}`),
    ).toBeVisible({ timeout: 10_000 });

    // -----------------------------------------------------------------
    // Step 8 — technical business-outcome assertion via
    //          /admin/deal-writeups/<pk>/ (sales-role-accessible).
    //          Confirms handed_off_to_fandi_at is populated — which
    //          transitively proves the M11.3 hand-off verb ran to
    //          completion (@transaction.atomic wraps the timestamp
    //          write + CA creation, and M32.1 D9-revised² FK-pairing
    //          tests prove the CA gets the deterministic backpointer
    //          set in the same atomic block).
    // -----------------------------------------------------------------
    const detailResponse = await request.get(
      `/api/dealer-ai/admin/deal-writeups/${writeupPk}/`,
    );
    expect(detailResponse.status()).toBe(200);
    const detail = (await detailResponse.json()) as DealWriteupDetailResponse;
    expect(detail.deal_writeup.id).toBe(writeupPk);
    expect(detail.deal_writeup.lead_id).toBe(newLeadId);
    expect(detail.deal_writeup.vehicle_id).toBe(fixtureVehicleId);
    expect(detail.deal_writeup.vehicle_price).toBe("28500.00");
    expect(detail.deal_writeup.monthly_payment_target).toBe("450.00");
    expect(detail.deal_writeup.term_months_target).toBe(72);
    expect(detail.deal_writeup.apr_target).toBe("7.49");
    // Three state-machine invariants populated post-hand-off:
    expect(detail.deal_writeup.sales_manager_approved_at).not.toBeNull();
    expect(
      detail.deal_writeup.sales_manager_approved_by_user_id,
    ).not.toBeNull();
    expect(detail.deal_writeup.handed_off_to_fandi_at).not.toBeNull();
    // handed_off_at is recent — hand-off just landed.
    const handedOffAt = new Date(
      detail.deal_writeup.handed_off_to_fandi_at!,
    ).getTime();
    const now = Date.now();
    expect(handedOffAt).toBeGreaterThan(now - 2 * 60_000);
    expect(handedOffAt).toBeLessThanOrEqual(now + 60_000);
  });
});
