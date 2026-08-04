// Milestone 28 · Increment 1 (SESSION_195) — templates wrapper tests.
//
// Guards fetchJournalEntryTemplates + createJournalEntryTemplate:
// envelope projection, URL, HTTP verb, and payload shape. Mocks
// authFetch so no real network is touched.

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/authFetch", () => ({
  authGetJSON: vi.fn(),
  authPostJSON: vi.fn(),
}));

import { authGetJSON, authPostJSON } from "@/lib/authFetch";
import {
  createJournalEntryTemplate,
  fetchJournalEntryTemplates,
  type CreateJournalEntryTemplatePayload,
  type JournalEntryTemplate,
} from "@/lib/accountingApi";

const authGetJSONMock = vi.mocked(authGetJSON);
const authPostJSONMock = vi.mocked(authPostJSON);

function fixtureTemplate(overrides: Partial<JournalEntryTemplate> = {}): JournalEntryTemplate {
  return {
    id: 1,
    name: "Monthly rent",
    description: "Rent expense — monthly",
    is_active: true,
    line_count: 2,
    lines: [
      {
        id: 1,
        account_id: 42,
        account_code: "615000",
        side: "debit",
        amount: "3500.00",
        memo: "",
        ordering: 0,
      },
      {
        id: 2,
        account_id: 17,
        account_code: "110000",
        side: "credit",
        amount: "3500.00",
        memo: "",
        ordering: 1,
      },
    ],
    ...overrides,
  };
}

describe("fetchJournalEntryTemplates", () => {
  beforeEach(() => {
    authGetJSONMock.mockReset();
  });

  it("calls the correct endpoint and projects the envelope", async () => {
    const template = fixtureTemplate();
    authGetJSONMock.mockResolvedValue({
      journal_entry_templates: { templates: [template] },
    });
    const result = await fetchJournalEntryTemplates();
    expect(authGetJSONMock).toHaveBeenCalledTimes(1);
    expect(authGetJSONMock).toHaveBeenCalledWith(
      "/admin/accounting/journal-entry-templates/",
    );
    expect(result).toEqual([template]);
  });

  it("returns an empty array for an empty envelope", async () => {
    authGetJSONMock.mockResolvedValue({
      journal_entry_templates: { templates: [] },
    });
    const result = await fetchJournalEntryTemplates();
    expect(result).toEqual([]);
  });

  it("supports templates with nullable line amounts (forward-compat)", async () => {
    // Schema reserves NULL for future variable-amount templates; the
    // wrapper must preserve NULL through the projection without
    // coercing it (a coercion would drop information the M-N variable-
    // amount UI will need).
    const template = fixtureTemplate({
      lines: [
        {
          id: 1,
          account_id: 42,
          account_code: "615000",
          side: "debit",
          amount: null,
          memo: "Amount entered at instantiation",
          ordering: 0,
        },
        {
          id: 2,
          account_id: 17,
          account_code: "110000",
          side: "credit",
          amount: null,
          memo: "",
          ordering: 1,
        },
      ],
    });
    authGetJSONMock.mockResolvedValue({
      journal_entry_templates: { templates: [template] },
    });
    const result = await fetchJournalEntryTemplates();
    expect(result[0]!.lines[0]!.amount).toBeNull();
    expect(result[0]!.lines[1]!.amount).toBeNull();
  });
});

describe("createJournalEntryTemplate", () => {
  beforeEach(() => {
    authPostJSONMock.mockReset();
  });

  it("posts to the correct endpoint with the payload and projects the response", async () => {
    const template = fixtureTemplate({ id: 42, name: "Monthly rent" });
    authPostJSONMock.mockResolvedValue({
      journal_entry_template: template,
    });
    const payload: CreateJournalEntryTemplatePayload = {
      name: "Monthly rent",
      description: "Rent expense — monthly",
      lines: [
        {
          account_id: 42,
          side: "debit",
          amount: "3500.00",
          memo: "",
        },
        {
          account_id: 17,
          side: "credit",
          amount: "3500.00",
          memo: "",
        },
      ],
    };
    const result = await createJournalEntryTemplate(payload);
    expect(authPostJSONMock).toHaveBeenCalledTimes(1);
    expect(authPostJSONMock).toHaveBeenCalledWith(
      "/admin/accounting/journal-entry-templates/",
      payload,
    );
    expect(result).toEqual(template);
  });

  it("propagates rejections from authPostJSON to the caller", async () => {
    authPostJSONMock.mockRejectedValue(new Error("HTTP 409"));
    await expect(
      createJournalEntryTemplate({
        name: "Duplicate",
        description: "—",
        lines: [
          { account_id: 1, side: "debit", amount: "1.00" },
          { account_id: 2, side: "credit", amount: "1.00" },
        ],
      }),
    ).rejects.toThrow(/HTTP 409/);
  });
});
