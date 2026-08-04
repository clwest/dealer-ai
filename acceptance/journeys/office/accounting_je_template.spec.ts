// Milestone 28 · Increment 2 — recurring journal template workflow journey.
//
// Guiding principle: this journey is an operational acceptance
// contract, not a UI automation project. If it passes, an office
// manager (dealer_owner persona) can (a) save a recurring journal-
// entry template through the M28.2 template dialog and (b)
// instantiate that template into a real balanced posting via the
// pre-populated M27.2 JE dialog — both entirely through the shipped
// application.
//
// Seeded state:
// - Existing `acceptance-owner` persona (dealer_owner @ default
//   dealership) — provisioned by seed_journey_owner_morning_review.
// - `seed_journey_office_accounting_workflow` invokes
//   `seed_default_coa`, guaranteeing the tenant has the M13 default
//   chart-of-accounts including 800000 Rent Expense (expense) and
//   110000 Bank — Operating (asset).
//
// Two test cases per M28 planning §5.d:
// 1. Create template — operator opens "Recurring templates" section,
//    clicks "+ New template", fills name + description + two
//    balanced lines using both code-search and name-search picker
//    modes, submits. Business-outcome assertion via admin API —
//    template exists with expected shape.
// 2. Instantiate template — operator expands templates section,
//    clicks Instantiate on the template seeded in case 1, verifies
//    JE dialog opens pre-populated, submits. Business-outcome
//    assertion via admin API — new JE exists with template's
//    account_ids + amounts + description.

import { test, expect, APIRequestContext } from "@playwright/test";


const CREATE_FIXTURE_PREFIX = "[M28.2-tmpl-create]";
const INSTANTIATE_FIXTURE_PREFIX = "[M28.2-tmpl-inst]";


interface TemplateLineRow {
  account_id: number;
  account_code: string;
  side: "debit" | "credit";
  amount: string | null;
  memo: string;
  ordering: number;
}

interface TemplateRow {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
  line_count: number;
  lines: TemplateLineRow[];
}


async function fetchTemplates(
  request: APIRequestContext,
): Promise<TemplateRow[]> {
  const url =
    "/api/dealer-ai/admin/accounting/journal-entry-templates/";
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as {
    journal_entry_templates: { templates: TemplateRow[] };
  };
  return body.journal_entry_templates?.templates ?? [];
}


async function fetchAllJournalEntries(
  request: APIRequestContext,
): Promise<Array<{ id: number; description: string; total_debit: string }>> {
  const url =
    "/api/dealer-ai/admin/accounting/journal-entries/list/?page_size=100";
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as {
    journal_entries: {
      entries: Array<{ id: number; description: string; total_debit: string }>;
    };
  };
  return body.journal_entries?.entries ?? [];
}


test.describe(
  "Office / accounting workflow — recurring journal templates",
  () => {
    test("owner can save a balanced recurring template through the templates dialog", async ({
      page,
      request,
    }) => {
      const runToken = `${Date.now()}-${Math.floor(Math.random() * 1000)}`;
      const templateName = `${CREATE_FIXTURE_PREFIX} monthly rent ${runToken}`;
      const templateDescription = `Rent expense — monthly ${runToken}`;

      // -----------------------------------------------------------
      // Step 1 — land on the JE list page.
      // -----------------------------------------------------------
      await page.goto("/dealer-ai-accounting/journal-entries");
      await expect(
        page.getByRole("heading", { level: 1, name: "Journal Entries" }),
        "JE list page heading should render",
      ).toBeVisible({ timeout: 15_000 });

      // -----------------------------------------------------------
      // Step 2 — expand the "Recurring templates" section.
      // -----------------------------------------------------------
      const toggle = page.getByTestId("templates-toggle");
      await expect(
        toggle,
        "Templates section toggle should be visible",
      ).toBeVisible({ timeout: 15_000 });
      await toggle.click();

      // -----------------------------------------------------------
      // Step 3 — open the template create dialog.
      // -----------------------------------------------------------
      const trigger = page.getByTestId("tmpl-create-trigger");
      await expect(
        trigger,
        "+ New template trigger should enable once CoA loads",
      ).toBeEnabled({ timeout: 15_000 });
      await trigger.click();

      const dialog = page.getByRole("dialog", {
        name: /New recurring template/i,
      });
      await expect(dialog).toBeVisible({ timeout: 15_000 });

      // -----------------------------------------------------------
      // Step 4 — fill name + description.
      // -----------------------------------------------------------
      await dialog.getByTestId("tmpl-name-input").fill(templateName);
      await dialog
        .getByTestId("tmpl-description-input")
        .fill(templateDescription);

      // -----------------------------------------------------------
      // Step 5 — pick line 1 via CODE search ("800" → 800000 Rent
      //          Expense), leave side default (debit), enter amount.
      // -----------------------------------------------------------
      const line1 = dialog.getByTestId("tmpl-line-0");
      await line1.getByRole("searchbox").fill("800");
      await line1.getByTestId("gl-account-option-800000").click();
      await expect(
        line1.getByTestId("gl-account-picker-selected"),
      ).toContainText("Rent Expense");
      await line1.getByLabel("Line 1 amount").fill("3500.00");

      // -----------------------------------------------------------
      // Step 6 — pick line 2 via NAME search ("Bank" → 110000 Bank
      //          — Operating), flip side to credit, enter amount.
      //          Both search modes exercised per §5.d.
      // -----------------------------------------------------------
      const line2 = dialog.getByTestId("tmpl-line-1");
      await line2.getByRole("searchbox").fill("Bank");
      await line2.getByTestId("gl-account-option-110000").click();
      await expect(
        line2.getByTestId("gl-account-picker-selected"),
      ).toContainText("Bank");
      await line2.getByTestId("tmpl-line-1-side").selectOption("credit");
      await line2.getByLabel("Line 2 amount").fill("3500.00");

      // -----------------------------------------------------------
      // Step 7 — balance indicator flips to "Balanced" and submit
      //          becomes enabled.
      // -----------------------------------------------------------
      await expect(
        dialog.getByTestId("tmpl-create-balance-indicator"),
      ).toContainText(/Balanced/i);
      const submit = dialog.getByTestId("tmpl-create-submit");
      await expect(submit).toBeEnabled();

      // -----------------------------------------------------------
      // Step 8 — submit; dialog closes on success.
      // -----------------------------------------------------------
      await submit.click();
      await expect(dialog).not.toBeVisible({ timeout: 15_000 });

      // -----------------------------------------------------------
      // Step 9 — success badge + template row visible in the list.
      // -----------------------------------------------------------
      await expect(
        page.getByTestId("tmpl-create-success-badge"),
      ).toBeVisible({ timeout: 15_000 });
      await expect(page.getByText(runToken).first()).toBeVisible({
        timeout: 10_000,
      });

      // -----------------------------------------------------------
      // Step 10 — business-outcome assertion via admin API. The
      //           template exists with the expected shape.
      // -----------------------------------------------------------
      const templates = await fetchTemplates(request);
      const saved = templates.find((tmpl) => tmpl.name === templateName);
      expect(
        saved,
        `admin API should surface the newly-saved template (name ${templateName})`,
      ).toBeDefined();
      expect(saved!.description).toBe(templateDescription);
      expect(saved!.is_active).toBe(true);
      expect(saved!.line_count).toBe(2);
      const debitLine = saved!.lines.find((l) => l.side === "debit");
      const creditLine = saved!.lines.find((l) => l.side === "credit");
      expect(debitLine?.account_code).toBe("800000");
      expect(debitLine?.amount).toBe("3500.00");
      expect(creditLine?.account_code).toBe("110000");
      expect(creditLine?.amount).toBe("3500.00");
    });

    test("owner can instantiate a template into a balanced posting via the pre-populated JE dialog", async ({
      page,
      request,
    }) => {
      const runToken = `${Date.now()}-${Math.floor(Math.random() * 1000)}`;
      const templateName = `${INSTANTIATE_FIXTURE_PREFIX} recipe ${runToken}`;
      const templateDescription = `Monthly rent recipe ${runToken}`;

      // Seed a fresh template via the admin API so this case is
      // independent of case 1's DB state and re-runs cleanly on the
      // shared acceptance DB. The instantiate flow itself is what
      // this case asserts, not template creation.
      const seedResponse = await postWithCsrf(
        request,
        "/api/dealer-ai/admin/accounting/journal-entry-templates/",
        {
          name: templateName,
          description: templateDescription,
          lines: [
            {
              account_id: await accountIdByCode(request, "800000"),
              side: "debit",
              amount: "1275.00",
              memo: "",
            },
            {
              account_id: await accountIdByCode(request, "110000"),
              side: "credit",
              amount: "1275.00",
              memo: "",
            },
          ],
        },
      );
      expect(
        seedResponse.status(),
        "seed template POST should return 201",
      ).toBe(201);
      const seedBody = (await seedResponse.json()) as {
        journal_entry_template: { id: number };
      };
      const templateId = seedBody.journal_entry_template.id;

      // -----------------------------------------------------------
      // Step 1 — land on the JE list page + expand templates.
      // -----------------------------------------------------------
      await page.goto("/dealer-ai-accounting/journal-entries");
      await expect(
        page.getByRole("heading", { level: 1, name: "Journal Entries" }),
      ).toBeVisible({ timeout: 15_000 });
      await page.getByTestId("templates-toggle").click();

      // -----------------------------------------------------------
      // Step 2 — click Instantiate on the seeded template row.
      // -----------------------------------------------------------
      const instantiate = page.getByTestId(
        `template-instantiate-${templateId}`,
      );
      await expect(instantiate).toBeVisible({ timeout: 15_000 });
      await instantiate.click();

      // -----------------------------------------------------------
      // Step 3 — JE dialog opens pre-populated.
      // -----------------------------------------------------------
      const dialog = page.getByRole("dialog", {
        name: /New journal entry/i,
      });
      await expect(dialog).toBeVisible({ timeout: 15_000 });
      await expect(
        dialog.getByRole("textbox", { name: /Description/i }),
        "description should pre-populate from template",
      ).toHaveValue(templateDescription);

      // posted_at defaults to today.
      const now = new Date();
      const todayIso = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
      await expect(dialog.getByLabel(/Posted at/i)).toHaveValue(todayIso);

      // Line amounts pre-populated on the correct sides. Numeric
      // inputs may render the value as "1275" or "1275.00" depending
      // on how the browser normalizes trailing zeros on set — regex
      // matches both.
      await expect(dialog.getByLabel("Line 1 debit")).toHaveValue(
        /^1275(\.00)?$/,
      );
      await expect(dialog.getByLabel("Line 2 credit")).toHaveValue(
        /^1275(\.00)?$/,
      );

      // Balance indicator immediately reads Balanced.
      await expect(
        dialog.getByTestId("je-create-balance-indicator"),
      ).toContainText(/Balanced/i);

      // Submit enabled without further typing.
      const submit = dialog.getByTestId("je-create-submit");
      await expect(submit).toBeEnabled();

      // -----------------------------------------------------------
      // Step 4 — submit the instantiated posting.
      // -----------------------------------------------------------
      await submit.click();
      await expect(dialog).not.toBeVisible({ timeout: 15_000 });

      // Success badge for the newly-posted JE.
      await expect(
        page.getByTestId("je-create-success-badge"),
      ).toBeVisible({ timeout: 15_000 });
      await expect(page.getByText(runToken).first()).toBeVisible({
        timeout: 10_000,
      });

      // -----------------------------------------------------------
      // Step 5 — business-outcome assertion via admin API. The
      //          new JE carries the template's description +
      //          account codes + amounts.
      // -----------------------------------------------------------
      const entries = await fetchAllJournalEntries(request);
      const posted = entries.find((e) => e.description.includes(runToken));
      expect(
        posted,
        `admin API should surface the newly-posted JE (token ${runToken})`,
      ).toBeDefined();
      expect(Number(posted!.total_debit)).toBeCloseTo(1275, 2);

      const detailUrl = `/api/dealer-ai/admin/accounting/journal-entries/${posted!.id}/`;
      const detailResponse = await request.get(detailUrl);
      expect(detailResponse.status()).toBe(200);
      const detailBody = (await detailResponse.json()) as {
        journal_entry: {
          description: string;
          lines: Array<{
            account_code: string;
            debit: string;
            credit: string;
          }>;
        };
      };
      const detail = detailBody.journal_entry;
      expect(detail.description).toBe(templateDescription);
      const debitLine = detail.lines.find((l) => Number(l.debit) > 0);
      const creditLine = detail.lines.find((l) => Number(l.credit) > 0);
      expect(debitLine?.account_code).toBe("800000");
      expect(creditLine?.account_code).toBe("110000");
    });
  },
);


async function accountIdByCode(
  request: APIRequestContext,
  code: string,
): Promise<number> {
  const response = await request.get(
    "/api/dealer-ai/admin/accounting/gl-accounts/",
  );
  expect(response.status()).toBe(200);
  const body = (await response.json()) as {
    gl_accounts: { accounts: Array<{ id: number; code: string }> };
  };
  const found = body.gl_accounts.accounts.find((a) => a.code === code);
  expect(found, `GLAccount ${code} should exist in the tenant`).toBeDefined();
  return found!.id;
}


// DRF SessionAuthentication requires the ``X-CSRFToken`` header on
// mutating requests. The persona storage state carries a ``csrftoken``
// cookie; the browser's fetch/XHR wiring copies it into the header
// automatically, but Playwright's APIRequestContext does not. This
// helper extracts the cookie and adds the header explicitly.
async function postWithCsrf(
  request: APIRequestContext,
  url: string,
  data: unknown,
): Promise<import("@playwright/test").APIResponse> {
  const state = await request.storageState();
  const csrf = state.cookies.find((c) => c.name === "csrftoken");
  expect(
    csrf,
    "persona storage state should carry a csrftoken cookie for CSRF-protected POSTs",
  ).toBeDefined();
  return request.post(url, {
    data,
    headers: { "X-CSRFToken": csrf!.value },
  });
}
