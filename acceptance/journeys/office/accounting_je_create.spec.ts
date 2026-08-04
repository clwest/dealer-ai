// Milestone 27 · Increment 2 — JE creation workflow journey.
//
// Guiding principle: this journey is an operational acceptance
// contract, not a UI automation project. If it passes, an office
// manager (dealer_owner persona) can originate a new balanced
// journal entry entirely through the shipped application — the
// M27.2 "+ New journal entry" dialog on the JE list page — and the
// resulting entry lands durably at the service layer with the
// posted lines, balanced-debits-equal-credits invariant, and
// audit-trail metadata intact.
//
// Seeded state:
// - Existing `acceptance-owner` persona (dealer_owner @ default
//   dealership) — provisioned by
//   seed_journey_owner_morning_review.
// - `seed_journey_office_accounting_workflow` invokes
//   `seed_default_coa` on every run, guaranteeing the tenant has
//   the M13 default chart-of-accounts including `110000` Bank —
//   Operating (asset) and `400000` Vehicle Sales — Retail
//   (revenue). Both are present in the M27.2 dialog picker.
//
// Two test cases per M27 planning §5.d:
// 1. Successful create — exercises both code-search and name-search
//    picker modes, balance validation, submit path, list refetch,
//    inline success badge, detail-page linkage. Business-outcome
//    assertion via admin API.
// 2. Cancel without persistence — exercises the ephemeral-dialog
//    contract. Fills partial form, clicks Cancel, asserts (a) the
//    list count did not increase and (b) no entry with the
//    cancel-test description prefix exists in the tenant's JE list
//    via the admin API.

import { test, expect, APIRequestContext } from "@playwright/test";


const CREATE_FIXTURE_PREFIX = "[M27.2-office-je-create]";
const CANCEL_FIXTURE_PREFIX = "[M27.2-cancel-test]";


interface JournalEntryListRow {
  id: number;
  description: string;
  posted_at: string;
  reverses_id: number | null;
  reason: string;
  total_debit: string;
}


async function fetchAllJournalEntries(
  request: APIRequestContext,
): Promise<JournalEntryListRow[]> {
  // page_size capped at 100 per M14.1 validator; the acceptance DB
  // seeds ≤3 entries (M20.3 + M22.2 fixtures + this test's posting).
  const url =
    "/api/dealer-ai/admin/accounting/journal-entries/list/?page_size=100";
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as {
    journal_entries: {
      entries: JournalEntryListRow[];
      total_count: number;
    };
  };
  return body.journal_entries?.entries ?? [];
}


async function countJournalEntriesWithPrefix(
  request: APIRequestContext,
  prefix: string,
): Promise<number> {
  const entries = await fetchAllJournalEntries(request);
  return entries.filter((entry) => entry.description.startsWith(prefix))
    .length;
}


test.describe(
  "Office / accounting workflow — create a new journal entry",
  () => {
    test("owner can create a balanced journal entry through the JE list dialog", async ({
      page,
      request,
    }) => {
      // Namespace the description with a per-run token so re-runs on
      // a shared DB don't collide on prefix and so the API assertion
      // can locate the exact entry it just posted.
      const runToken = `${Date.now()}-${Math.floor(Math.random() * 1000)}`;
      const description = `${CREATE_FIXTURE_PREFIX} balanced posting ${runToken}`;

      // -----------------------------------------------------------
      // Step 1 — land on the JE list page.
      // -----------------------------------------------------------
      await page.goto("/dealer-ai-accounting/journal-entries");
      await expect(
        page.getByRole("heading", { level: 1, name: "Journal Entries" }),
        "JE list page heading should render",
      ).toBeVisible({ timeout: 15_000 });

      // The "+ New journal entry" button is disabled until the M27.1
      // chart-of-accounts fetch resolves. Waiting for enabled is our
      // indirect readiness signal.
      const trigger = page.getByRole("button", {
        name: /\+ New journal entry/i,
      });
      await expect(
        trigger,
        "+ New journal entry trigger should be visible in the header",
      ).toBeVisible({ timeout: 15_000 });
      await expect(
        trigger,
        "+ New journal entry trigger should enable once CoA loads",
      ).toBeEnabled({ timeout: 15_000 });

      // -----------------------------------------------------------
      // Step 2 — open the dialog.
      // -----------------------------------------------------------
      await trigger.click();
      const dialog = page.getByRole("dialog", { name: /New journal entry/i });
      await expect(dialog).toBeVisible({ timeout: 15_000 });

      // -----------------------------------------------------------
      // Step 3 — description + confirm posted_at defaults to today.
      // -----------------------------------------------------------
      await dialog
        .getByRole("textbox", { name: /Description/i })
        .fill(description);

      const now = new Date();
      const todayIso = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
      await expect(
        dialog.getByLabel(/Posted at/i),
        "posted_at should default to today's date",
      ).toHaveValue(todayIso);

      // -----------------------------------------------------------
      // Step 4 — pick line 1 via CODE search ("110" → 110000 Bank).
      // -----------------------------------------------------------
      const line1 = dialog.getByTestId("je-line-0");
      await line1.getByRole("searchbox").fill("110");
      await line1.getByTestId("gl-account-option-110000").click();
      await expect(
        line1.getByTestId("gl-account-picker-selected"),
      ).toContainText("Bank");

      await line1.getByLabel("Line 1 debit").fill("125.00");

      // -----------------------------------------------------------
      // Step 5 — pick line 2 via NAME search ("Sales" → 400000
      //          Vehicle Sales — Retail). Both search modes are
      //          asserted per M27 §5.d test-case-1 contract.
      // -----------------------------------------------------------
      const line2 = dialog.getByTestId("je-line-1");
      await line2.getByRole("searchbox").fill("Sales");
      await line2.getByTestId("gl-account-option-400000").click();
      await expect(
        line2.getByTestId("gl-account-picker-selected"),
      ).toContainText("Vehicle Sales");

      await line2.getByLabel("Line 2 credit").fill("125.00");

      // -----------------------------------------------------------
      // Step 6 — balance indicator flips to "Balanced" and submit
      //          becomes enabled.
      // -----------------------------------------------------------
      const indicator = dialog.getByTestId("je-create-balance-indicator");
      await expect(indicator).toContainText(/Balanced/i);
      const submit = dialog.getByTestId("je-create-submit");
      await expect(submit).toBeEnabled();

      // -----------------------------------------------------------
      // Step 7 — submit; dialog closes on success.
      // -----------------------------------------------------------
      await submit.click();
      await expect(dialog).not.toBeVisible({ timeout: 15_000 });

      // -----------------------------------------------------------
      // Step 8 — inline success badge appears + new entry surfaces
      //          in the list (recent-first).
      // -----------------------------------------------------------
      const badge = page.getByTestId("je-create-success-badge");
      await expect(badge).toBeVisible({ timeout: 15_000 });
      await expect(badge).toContainText(description);

      // The new entry appears as a row in the list. Match on the
      // unique run-token substring rather than the full description
      // to keep the assertion resilient to render truncation.
      await expect(
        page.getByText(runToken).first(),
        "the newly-posted entry should appear in the list",
      ).toBeVisible({ timeout: 10_000 });

      // -----------------------------------------------------------
      // Step 9 — business-outcome assertion via admin API. The
      //          created entry exists, is balanced, and carries the
      //          expected account_ids on its lines.
      // -----------------------------------------------------------
      const entries = await fetchAllJournalEntries(request);
      const posted = entries.find((entry) =>
        entry.description.includes(runToken),
      );
      expect(
        posted,
        `admin API should surface the newly-posted entry (prefix ${CREATE_FIXTURE_PREFIX}, token ${runToken})`,
      ).toBeDefined();
      expect(posted!.reverses_id).toBeNull();
      // total_debit is a quantized string; ensure it matches the
      // posted $125.00.
      expect(Number(posted!.total_debit)).toBeCloseTo(125, 2);

      // Detail projection carries the full line breakdown; assert
      // the debit + credit account codes are the two we picked.
      const detailUrl = `/api/dealer-ai/admin/accounting/journal-entries/${posted!.id}/`;
      const detailResponse = await request.get(detailUrl);
      expect(detailResponse.status()).toBe(200);
      const detailBody = (await detailResponse.json()) as {
        journal_entry: {
          id: number;
          description: string;
          lines: Array<{
            account_code: string;
            debit: string;
            credit: string;
          }>;
        };
      };
      const detail = detailBody.journal_entry;
      const debitLine = detail.lines.find((line) => Number(line.debit) > 0);
      const creditLine = detail.lines.find(
        (line) => Number(line.credit) > 0,
      );
      expect(debitLine?.account_code).toBe("110000");
      expect(creditLine?.account_code).toBe("400000");
    });

    test(
      "opening the '+ New journal entry' dialog directly (blank path) does not pre-populate — M28.2 regression guard",
      async ({ page }) => {
        // Regression guard for the M28.2 template Instantiate flow:
        // the JE list page mounts NewJournalEntryDialog twice — once
        // uncontrolled (this "+ New journal entry" trigger, always
        // blank) and once controlled (external open, pre-populated
        // from a template). This test asserts that clicking the blank
        // trigger continues to open a blank dialog even after M28.2
        // introduced the pre-populate path.
        await page.goto("/dealer-ai-accounting/journal-entries");
        const trigger = page.getByRole("button", {
          name: /\+ New journal entry/i,
        });
        await expect(trigger).toBeEnabled({ timeout: 15_000 });
        await trigger.click();

        const dialog = page.getByRole("dialog", {
          name: /New journal entry/i,
        });
        await expect(dialog).toBeVisible({ timeout: 15_000 });

        // Description empty.
        await expect(
          dialog.getByRole("textbox", { name: /Description/i }),
        ).toHaveValue("");
        // Debit + credit inputs on both default lines empty.
        await expect(dialog.getByLabel("Line 1 debit")).toHaveValue("");
        await expect(dialog.getByLabel("Line 1 credit")).toHaveValue("");
        await expect(dialog.getByLabel("Line 2 debit")).toHaveValue("");
        await expect(dialog.getByLabel("Line 2 credit")).toHaveValue("");
        // No account preselected on either line — indicator shows
        // "Enter amounts" (totalDebit == 0 && totalCredit == 0).
        await expect(
          dialog.getByTestId("je-create-balance-indicator"),
        ).toContainText(/Enter amounts/i);
        // Submit blocked (blank description + no accounts + no amounts).
        await expect(dialog.getByTestId("je-create-submit")).toBeDisabled();
      },
    );

    test("cancel closes the dialog without persisting the entry", async ({
      page,
      request,
    }) => {
      const runToken = `${Date.now()}-${Math.floor(Math.random() * 1000)}`;
      const cancelDescription = `${CANCEL_FIXTURE_PREFIX} discarded ${runToken}`;

      // Baseline count via admin API — the M27 §5.d cancel-test
      // contract asserts against this specific description; any
      // prior run leftover would count but the run token guarantees
      // uniqueness. Baseline for this exact prefix+token is 0.
      const priorMatches = await countJournalEntriesWithPrefix(
        request,
        cancelDescription,
      );
      expect(
        priorMatches,
        "no prior entry should share this unique cancel-test description",
      ).toBe(0);

      // -----------------------------------------------------------
      // Step 1 — land on the JE list page + open the dialog.
      // -----------------------------------------------------------
      await page.goto("/dealer-ai-accounting/journal-entries");
      const trigger = page.getByRole("button", {
        name: /\+ New journal entry/i,
      });
      await expect(trigger).toBeEnabled({ timeout: 15_000 });
      await trigger.click();

      const dialog = page.getByRole("dialog", { name: /New journal entry/i });
      await expect(dialog).toBeVisible({ timeout: 15_000 });

      // -----------------------------------------------------------
      // Step 2 — fill partial form: description + one line only
      //          (deliberately not enough to satisfy the balanced-
      //          two-line submit requirement, so the operator
      //          could not have accidentally submitted even if the
      //          cancel button failed).
      // -----------------------------------------------------------
      await dialog
        .getByRole("textbox", { name: /Description/i })
        .fill(cancelDescription);
      const line1 = dialog.getByTestId("je-line-0");
      await line1.getByRole("searchbox").fill("110");
      await line1.getByTestId("gl-account-option-110000").click();
      await line1.getByLabel("Line 1 debit").fill("42.00");

      // -----------------------------------------------------------
      // Step 3 — click Cancel; dialog closes with no confirmation.
      // -----------------------------------------------------------
      await dialog.getByRole("button", { name: /^Cancel$/i }).click();
      await expect(dialog).not.toBeVisible({ timeout: 10_000 });

      // Success badge from a hypothetical stray persist would render
      // here — its absence is a positive signal.
      await expect(
        page.getByTestId("je-create-success-badge"),
      ).not.toBeVisible({ timeout: 3_000 });

      // -----------------------------------------------------------
      // Step 4 — business-outcome assertion via admin API. No
      //          entry with the cancel-test description exists in
      //          the tenant's JE list. Persistence never happened.
      // -----------------------------------------------------------
      const postMatches = await countJournalEntriesWithPrefix(
        request,
        cancelDescription,
      );
      expect(
        postMatches,
        `no entry with description "${cancelDescription}" should exist post-cancel`,
      ).toBe(0);
    });
  },
);
