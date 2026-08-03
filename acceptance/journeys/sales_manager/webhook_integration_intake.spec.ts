// Milestone 24 · Increment 4 (SESSION_184) — webhook integration-to-
// operator intake journey.
//
// Guiding principle: this suite is an operational acceptance contract,
// not a UI automation project. Webhook is a system-to-system
// integration boundary — listing platforms and dealer DR systems POST
// leads to the dealership's webhook endpoint, and operators handle
// the ingested lead through the real UI. The journey exercises that
// full path: real endpoint ingestion in the setup step, then browser-
// side operator handling (filter list by channel → open lead detail
// modal → assign).
//
// Per MILESTONE_24_PLANNING.md §5.d Option C (webhook row): the
// journey is the only M24 increment that does not ship or exercise
// a new operator form. No `+ Webhook` CTA, no `<WebhookIntakeForm>` —
// those were considered at M24.0 and rejected before lock (webhook is
// not a salesperson-created lead source). See the M24 memo's M24.1-
// open correction preamble + §5.b + §5.d for the full framing.
//
// Ingestion setup uses the shipped `generic` adapter
// (backend/dealer_ai/services/leads/webhook_adapters/__init__.py:40)
// — no test-only backend surface, no fabricated adapter registration.
// The generic adapter's documented envelope
// (backend/dealer_ai/services/leads/webhook_adapters/generic.py:14)
// mirrors the minimum payload any listing platform sends: full_name
// + phone/email/message + optional budget hints.
//
// Seeded state (via seed_journey_sales_operational_entry +
// seed_journey_sales_manager_daily_startup):
// - `acceptance-sales-manager` user (sales_manager @ default
//   dealership) — auth persona via storage state (satisfies
//   IsSalesManagerOrOwnerAtActiveDealership permission)
// - `Acceptance Advisor` (M20 seed's Salesperson) — assignment
//   target
//
// Journey steps:
// 1. Setup: POST to real /api/dealer-ai/admin/leads/webhook/ with
//    platform="generic" + realistic dealer-owned envelope. Capture
//    the new lead's id from the 201 response body.
// 2. Login as salesperson (via storage state — Playwright project
//    config).
// 3. Navigate to /dealer-ai-sales/leads.
// 4. Change the channel filter to "listing_form" (the channel
//    constant record_webhook_lead writes per
//    dealer_ai/services/leads/channel_intake.py — every webhook lead
//    lands under channel="listing_form" regardless of platform).
// 5. Assert the ingested lead row appears in the filtered list.
// 6. Click the row → LeadDetailModal opens.
// 7. Assign Acceptance Advisor via AssignmentDropdown.
// 8. Business-outcome assertion via admin API: assigned to
//    Acceptance Advisor + channel="listing_form".
//
// M25.1 (SESSION_186) extended this journey with a Source-line
// assertion — platform value now surfaces in LeadDetailModal via the
// `source_metadata` JSONField that record_webhook_lead writes at
// ingestion time. See MILESTONE_25_PLANNING.md §5.b + §5.c. §3
// deferral 14 from M24.1 is closed by this increment.

import { test, expect } from "@playwright/test";

import { expectLeadAssignedTo } from "../../support/assertions/dashboard";

interface WebhookResponseBody {
  lead: {
    id: number;
    name: string;
    channel: string;
    dealership_id: number;
  };
}

test.describe("Webhook integration-to-operator: listing platform POST → operator picks up in UI", () => {
  test("real webhook POST + salesperson can filter + assign the ingested lead", async ({
    page,
    request,
  }) => {
    const ADVISOR_NAME = "Acceptance Advisor";
    // Unique per-run name so suite re-runs don't collide on the
    // same ingested-lead identity.
    const CUSTOMER_NAME = `M24.4 Webhook Winnie ${Date.now()}`;
    const CUSTOMER_PHONE = "+15551244004";
    const CUSTOMER_EMAIL = "m244-webhook-winnie@example.com";

    // ---------------------------------------------------------------
    // Step 1 — real webhook POST at the integration boundary. This
    //          is the ONLY step that lives outside the browser; the
    //          producer is an external system (listing platform / DR
    //          system), so simulating it via HTTP is honest about
    //          the origination path. Everything after this step is
    //          real operator UI.
    //
    //          DRF's SessionAuthentication enforces CSRF on unsafe
    //          methods when a session cookie is present. The persona's
    //          storage state (populated by login.setup.ts) includes
    //          both `sessionid` and `csrftoken`. Read the csrftoken
    //          out of the request context's cookies and pass it as
    //          `X-CSRFToken` — same contract the shipped frontend
    //          uses (frontend/src/lib/authFetch.ts:84-86).
    // ---------------------------------------------------------------
    const storageState = await request.storageState();
    const csrfCookie = storageState.cookies.find(
      (c) => c.name === "csrftoken",
    );
    expect(
      csrfCookie?.value,
      "acceptance-sales-manager storage state should carry a csrftoken cookie from login",
    ).toBeTruthy();

    const webhookResponse = await request.post(
      "/api/dealer-ai/admin/leads/webhook/",
      {
        headers: {
          "X-CSRFToken": csrfCookie?.value ?? "",
        },
        data: {
          platform: "generic",
          payload: {
            full_name: CUSTOMER_NAME,
            phone: CUSTOMER_PHONE,
            email: CUSTOMER_EMAIL,
            message:
              "[M24.4 journey] Interested in the F-150. Journey-generated payload for the acceptance suite.",
            target_monthly_payment: "450",
            down_payment: "3000",
            trade_in: "2018 Civic 82k",
            credit_range: "good",
          },
        },
      },
    );
    expect(
      webhookResponse.status(),
      "webhook POST should return 201 for the shipped 'generic' adapter",
    ).toBe(201);
    const webhookBody = (await webhookResponse.json()) as WebhookResponseBody;
    expect(
      webhookBody.lead?.id,
      "webhook response should include the newly-created lead's id",
    ).toBeGreaterThan(0);
    expect(
      webhookBody.lead.channel,
      "webhook-ingested lead should land with channel='listing_form'",
    ).toBe("listing_form");
    expect(
      webhookBody.lead.name,
      "webhook-ingested lead's name should reflect the POSTed full_name",
    ).toBe(CUSTOMER_NAME);
    const ingestedLeadId = webhookBody.lead.id;

    // ---------------------------------------------------------------
    // Step 2 — navigate to the sales-side leads page as salesperson
    //          (storage state provides the session cookie).
    // ---------------------------------------------------------------
    await page.goto("/dealer-ai-sales/leads");
    await expect(
      page.getByRole("heading", { level: 1, name: "Sales leads" }),
    ).toBeVisible({ timeout: 15_000 });

    // ---------------------------------------------------------------
    // Step 3 — change the channel filter to `listing_form` via the
    //          existing filter select. Refetches the leads list
    //          scoped to webhook-origin leads.
    // ---------------------------------------------------------------
    await page
      .getByLabel(/channel filter/i)
      .selectOption("listing_form");

    // ---------------------------------------------------------------
    // Step 4 — assert the ingested lead row appears in the filtered
    //          table with the expected name + channel attribution.
    // ---------------------------------------------------------------
    const ingestedRow = page.getByTestId(
      `sales-leads-row-${ingestedLeadId}`,
    );
    await expect(
      ingestedRow,
      `webhook-ingested lead row (id=${ingestedLeadId}) should appear when filtering by channel=listing_form`,
    ).toBeVisible({ timeout: 15_000 });
    await expect(ingestedRow).toContainText(CUSTOMER_NAME);
    await expect(ingestedRow).toContainText("listing_form");

    // ---------------------------------------------------------------
    // Step 5 — click the row → LeadDetailModal opens.
    // ---------------------------------------------------------------
    await ingestedRow.click();
    const modalRegion = page.locator("div.fixed.inset-0.z-50");
    await expect(
      modalRegion.getByText("Sales handoff packet", { exact: true }).first(),
      "LeadDetailModal should open for the webhook-ingested lead",
    ).toBeVisible({ timeout: 15_000 });

    // ---------------------------------------------------------------
    // Step 5b (M25.1) — assert the modal Source section renders the
    //                    platform captured at ingestion. The generic
    //                    adapter's source_metadata is
    //                    {"platform": "generic"} per
    //                    record_webhook_lead
    //                    (services/leads/channel_intake.py); the
    //                    display helper title-cases it. Before M25.1
    //                    the operator saw only channel="listing_form"
    //                    with no way to distinguish platforms.
    // ---------------------------------------------------------------
    const sourceLine = modalRegion.getByTestId("lead-source-line");
    await expect(
      sourceLine,
      "M25.1 Source section should render for webhook-origin leads",
    ).toBeVisible({ timeout: 10_000 });
    await expect(sourceLine).toHaveText("Source: Generic");

    // ---------------------------------------------------------------
    // Step 6 — assign Acceptance Advisor via AssignmentDropdown.
    // ---------------------------------------------------------------
    const assignmentTrigger = modalRegion
      .getByRole("button", { name: /^Unassigned$/ })
      .first();
    await expect(
      assignmentTrigger,
      "assignment dropdown trigger should read 'Unassigned' before assignment",
    ).toBeVisible({ timeout: 10_000 });
    await assignmentTrigger.click();

    const advisorOption = modalRegion
      .getByRole("button", { name: ADVISOR_NAME })
      .first();
    await expect(
      advisorOption,
      `advisor "${ADVISOR_NAME}" should be selectable in the assignment dropdown`,
    ).toBeVisible({ timeout: 10_000 });
    await advisorOption.click();

    await expect(
      modalRegion.getByRole("button", { name: ADVISOR_NAME }).first(),
      `assignment trigger should reflect ${ADVISOR_NAME} after selection`,
    ).toBeVisible({ timeout: 10_000 });

    // ---------------------------------------------------------------
    // Step 7 — business-outcome assertions via admin API:
    //          - lead assigned to Acceptance Advisor
    //          - channel="listing_form" (proves the webhook adapter
    //            + service verb persisted the correct channel and
    //            no post-ingestion mutation lost the attribution)
    // ---------------------------------------------------------------
    const lead = await expectLeadAssignedTo(
      request,
      ingestedLeadId,
      ADVISOR_NAME,
    );
    expect(
      lead.channel,
      `lead id=${ingestedLeadId} should have channel="listing_form"`,
    ).toBe("listing_form");
  });
});
