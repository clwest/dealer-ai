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

      // M29.2 — fully-fixed template lines render the populated side
      // as a read-only ``LockedAmountChip`` (test-id
      // ``je-line-<index>-<side>-chip``) instead of a labeled
      // ``<Input>``. The chip renders the pre-populated value as
      // ``$1275.00 (from template)``; the underlying line state still
      // carries the numeric value, so submit + balance behavior below
      // remain unchanged. Historical assertion at this call site used
      // ``getByLabel("Line 1 debit").toHaveValue(...)`` — that
      // matched the M28.2 ``<Input>`` shape and no longer resolves
      // after M29.2's chip UI. §0.a M30.0 amendment restored parity.
      await expect(dialog.getByTestId("je-line-0-debit-chip")).toContainText(
        /\$1275\.00/,
      );
      await expect(dialog.getByTestId("je-line-1-credit-chip")).toContainText(
        /\$1275\.00/,
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


// -------------------------------------------------------------------
// Milestone 29 · Increment 2 (SESSION_199) — variable-amount workflow.
// One end-to-end journey covering all six user-specified assertions
// from MILESTONE_29_PLANNING.md §5.b D8 in sequence:
//   1. Create a variable-amount template.
//   2. Instantiate visibly requests the missing amounts.
//   3. An unbalanced entry cannot be submitted.
//   4. A balanced entry posts successfully.
//   5. The saved template remains unchanged afterward.
//   6. The resulting journal entry appears correctly in list/detail.
// -------------------------------------------------------------------

const VARIABLE_FIXTURE_PREFIX = "[M29.2-tmpl-var]";


test.describe(
  "Office / accounting workflow — variable-amount templates",
  () => {
    test("owner can create, instantiate, and post a variable-amount template through the shipped UI", async ({
      page,
      request,
    }) => {
      const runToken = `${Date.now()}-${Math.floor(Math.random() * 1000)}`;
      const templateName = `${VARIABLE_FIXTURE_PREFIX} depreciation ${runToken}`;
      const templateDescription = `Monthly depreciation ${runToken}`;

      // ----------------------------------------------------------------
      // §5.b D8.1 — Create a variable-amount template.
      // ----------------------------------------------------------------
      await page.goto("/dealer-ai-accounting/journal-entries");
      await expect(
        page.getByRole("heading", { level: 1, name: "Journal Entries" }),
      ).toBeVisible({ timeout: 15_000 });
      await page.getByTestId("templates-toggle").click();

      const trigger = page.getByTestId("tmpl-create-trigger");
      await expect(trigger).toBeEnabled({ timeout: 15_000 });
      await trigger.click();
      const createDialog = page.getByRole("dialog", {
        name: /New recurring template/i,
      });
      await expect(createDialog).toBeVisible({ timeout: 15_000 });

      await createDialog.getByTestId("tmpl-name-input").fill(templateName);
      await createDialog
        .getByTestId("tmpl-description-input")
        .fill(templateDescription);

      // Line 1: debit, 800000 Rent Expense, VARIABLE.
      const line1 = createDialog.getByTestId("tmpl-line-0");
      await line1.getByRole("searchbox").fill("800");
      await line1.getByTestId("gl-account-option-800000").click();
      await line1.getByTestId("tmpl-line-0-variable").check();
      // Amount input should now be disabled with the variable placeholder.
      await expect(
        line1.getByTestId("tmpl-line-0-amount"),
      ).toBeDisabled();
      await expect(
        line1.getByTestId("tmpl-line-0-amount"),
      ).toHaveAttribute("placeholder", "Set at instantiate");

      // Line 2: credit, 110000 Bank — Operating, VARIABLE.
      const line2 = createDialog.getByTestId("tmpl-line-1");
      await line2.getByRole("searchbox").fill("Bank");
      await line2.getByTestId("gl-account-option-110000").click();
      await line2.getByTestId("tmpl-line-1-side").selectOption("credit");
      await line2.getByTestId("tmpl-line-1-variable").check();

      // Balance indicator shows the variable-mode badge, not "Unbalanced".
      await expect(
        createDialog.getByTestId("tmpl-create-variable-balance-note"),
      ).toBeVisible();
      await expect(
        createDialog.getByTestId("tmpl-create-balance-indicator"),
      ).not.toContainText(/Unbalanced/i);

      const createSubmit = createDialog.getByTestId("tmpl-create-submit");
      await expect(createSubmit).toBeEnabled();
      await createSubmit.click();
      await expect(createDialog).not.toBeVisible({ timeout: 15_000 });

      // ----------------------------------------------------------------
      // §5.b D8.5 (pre) — Snapshot the saved template projection so
      //                   we can deep-compare after instantiate to
      //                   prove immutability.
      // ----------------------------------------------------------------
      const templatesBefore = await fetchTemplates(request);
      const created = templatesBefore.find(
        (tmpl) => tmpl.name === templateName,
      );
      expect(
        created,
        `admin API should surface the variable-amount template`,
      ).toBeDefined();
      const templateId = created!.id;
      expect(created!.lines).toHaveLength(2);
      expect(created!.lines.every((l) => l.amount === null)).toBe(true);
      const snapshot = JSON.parse(JSON.stringify(created));

      // ----------------------------------------------------------------
      // §5.b D8.2 — Instantiate visibly requests the missing amounts.
      // ----------------------------------------------------------------
      const instantiateBtn = page.getByTestId(
        `template-instantiate-${templateId}`,
      );
      await expect(instantiateBtn).toBeVisible({ timeout: 15_000 });
      await instantiateBtn.click();

      const jeDialog = page.getByRole("dialog", {
        name: /New journal entry/i,
      });
      await expect(jeDialog).toBeVisible({ timeout: 15_000 });
      await expect(
        jeDialog.getByRole("textbox", { name: /Description/i }),
      ).toHaveValue(templateDescription);

      // Variable-debit line 1: debit editable + "Enter amount" placeholder;
      // credit disabled.
      const line1Debit = jeDialog.getByLabel("Line 1 debit");
      await expect(line1Debit).not.toBeDisabled();
      await expect(line1Debit).toHaveAttribute(
        "placeholder",
        "Enter amount",
      );
      await expect(jeDialog.getByLabel("Line 1 credit")).toBeDisabled();
      // Variable-credit line 2: mirror.
      await expect(jeDialog.getByLabel("Line 2 debit")).toBeDisabled();
      const line2Credit = jeDialog.getByLabel("Line 2 credit");
      await expect(line2Credit).not.toBeDisabled();
      await expect(line2Credit).toHaveAttribute(
        "placeholder",
        "Enter amount",
      );
      // No chips on either line (both are variable).
      await expect(
        jeDialog.getByTestId("je-line-0-debit-chip"),
      ).not.toBeAttached();
      await expect(
        jeDialog.getByTestId("je-line-1-credit-chip"),
      ).not.toBeAttached();

      // ----------------------------------------------------------------
      // §5.b D8.3 — Unbalanced entry submission blocked.
      // ----------------------------------------------------------------
      await line1Debit.fill("450.00");
      await line2Credit.fill("451.00");
      await expect(
        jeDialog.getByTestId("je-create-balance-indicator"),
      ).toContainText(/Unbalanced by \$1\.00/);
      const jeSubmit = jeDialog.getByTestId("je-create-submit");
      await expect(jeSubmit).toBeDisabled();

      // ----------------------------------------------------------------
      // §5.b D8.4 — Balanced entry posts successfully.
      // ----------------------------------------------------------------
      await line2Credit.fill("450.00");
      await expect(
        jeDialog.getByTestId("je-create-balance-indicator"),
      ).toContainText(/Balanced/i);
      await expect(jeSubmit).toBeEnabled();
      await jeSubmit.click();
      await expect(jeDialog).not.toBeVisible({ timeout: 15_000 });
      await expect(
        page.getByTestId("je-create-success-badge"),
      ).toBeVisible({ timeout: 15_000 });

      // ----------------------------------------------------------------
      // §5.b D8.5 — Saved template unchanged. Re-fetch and deep-
      //             compare projection to the pre-instantiate snapshot.
      // ----------------------------------------------------------------
      const templatesAfter = await fetchTemplates(request);
      const stillThere = templatesAfter.find((t) => t.id === templateId);
      expect(
        stillThere,
        `template should still exist post-instantiate`,
      ).toBeDefined();
      expect(
        stillThere,
        `template projection should be byte-identical to pre-instantiate snapshot (no template mutation on instantiate)`,
      ).toEqual(snapshot);

      // ----------------------------------------------------------------
      // §5.b D8.6 — Resulting JE appears correctly in list/detail.
      // ----------------------------------------------------------------
      const entries = await fetchAllJournalEntries(request);
      const posted = entries.find((e) =>
        e.description.includes(runToken),
      );
      expect(
        posted,
        `admin API should surface the posted variable-amount JE`,
      ).toBeDefined();
      expect(Number(posted!.total_debit)).toBeCloseTo(450, 2);

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
      expect(Number(debitLine?.debit)).toBeCloseTo(450, 2);
      expect(creditLine?.account_code).toBe("110000");
      expect(Number(creditLine?.credit)).toBeCloseTo(450, 2);
    });
  },
);


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
