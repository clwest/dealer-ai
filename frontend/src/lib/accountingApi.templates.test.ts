// Milestone 28 · Increment 1 (SESSION_195) — templates wrapper tests.
// Milestone 30 · Increment 2 (SESSION_202) — extended for update +
// delete wrappers on top of the M30.1 detail endpoint.
//
// Guards fetchJournalEntryTemplates + createJournalEntryTemplate +
// updateJournalEntryTemplate + deleteJournalEntryTemplate: envelope
// projection, URL, HTTP verb, payload shape, and DELETE 404-as-
// success semantics. Mocks authFetch so no real network is touched.

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/authFetch", async () => {
  const actual = await vi.importActual<typeof import("@/lib/authFetch")>(
    "@/lib/authFetch",
  );
  return {
    ...actual,
    authGetJSON: vi.fn(),
    authPostJSON: vi.fn(),
    authPatchJSON: vi.fn(),
    authDelete: vi.fn(),
  };
});

import {
  ApiError,
  authDelete,
  authGetJSON,
  authPatchJSON,
  authPostJSON,
} from "@/lib/authFetch";
import {
  createJournalEntryTemplate,
  deleteJournalEntryTemplate,
  fetchJournalEntryTemplates,
  updateJournalEntryTemplate,
  type CreateJournalEntryTemplatePayload,
  type JournalEntryTemplate,
} from "@/lib/accountingApi";

const authGetJSONMock = vi.mocked(authGetJSON);
const authPostJSONMock = vi.mocked(authPostJSON);
const authPatchJSONMock = vi.mocked(authPatchJSON);
const authDeleteMock = vi.mocked(authDelete);

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

  it("M29 — posts amount: null on the wire for variable lines", async () => {
    const template = fixtureTemplate({
      id: 99,
      name: "Monthly depreciation",
      lines: [
        {
          id: 1,
          account_id: 42,
          account_code: "615000",
          side: "debit",
          amount: null,
          memo: "",
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
    authPostJSONMock.mockResolvedValue({
      journal_entry_template: template,
    });
    const payload: CreateJournalEntryTemplatePayload = {
      name: "Monthly depreciation",
      description: "Depreciation per asset per period",
      lines: [
        { account_id: 42, side: "debit", amount: null },
        { account_id: 17, side: "credit", amount: null },
      ],
    };
    await createJournalEntryTemplate(payload);
    expect(authPostJSONMock).toHaveBeenCalledWith(
      "/admin/accounting/journal-entry-templates/",
      payload,
    );
    // Explicit assertion: null passed through unchanged (no coercion
    // to "0.00" or ""); wire contract preserved.
    const wire = authPostJSONMock.mock.calls[0]![1] as
      CreateJournalEntryTemplatePayload;
    expect(wire.lines[0]!.amount).toBeNull();
    expect(wire.lines[1]!.amount).toBeNull();
  });

  it("M29 — mixed populated + null amounts round-trip through fetch", async () => {
    // Analog of the fetch null test above but for a mixed template
    // (fixed base fee + variable usage). Nulls and Decimal strings
    // both survive projection without cross-contamination.
    const template = fixtureTemplate({
      lines: [
        {
          id: 1,
          account_id: 42,
          account_code: "615000",
          side: "debit",
          amount: "25.00",
          memo: "Utility base fee",
          ordering: 0,
        },
        {
          id: 2,
          account_id: 17,
          account_code: "110000",
          side: "credit",
          amount: null,
          memo: "Utility usage (variable)",
          ordering: 1,
        },
      ],
    });
    authGetJSONMock.mockResolvedValue({
      journal_entry_templates: { templates: [template] },
    });
    const result = await fetchJournalEntryTemplates();
    expect(result[0]!.lines[0]!.amount).toBe("25.00");
    expect(result[0]!.lines[1]!.amount).toBeNull();
  });
});


// ======================================================================
// Milestone 30 · Increment 2 (SESSION_202) — update + delete wrappers
// ======================================================================

describe("updateJournalEntryTemplate", () => {
  beforeEach(() => {
    authPatchJSONMock.mockReset();
  });

  it("PATCHes the detail endpoint with the payload and projects the response", async () => {
    const template = fixtureTemplate({ id: 42, name: "Monthly rent (edited)" });
    authPatchJSONMock.mockResolvedValue({
      journal_entry_template: template,
    });
    const payload: CreateJournalEntryTemplatePayload = {
      name: "Monthly rent (edited)",
      description: "Edited",
      lines: [
        { account_id: 42, side: "debit", amount: "4000.00" },
        { account_id: 17, side: "credit", amount: "4000.00" },
      ],
    };
    const result = await updateJournalEntryTemplate(42, payload);
    expect(authPatchJSONMock).toHaveBeenCalledTimes(1);
    expect(authPatchJSONMock).toHaveBeenCalledWith(
      "/admin/accounting/journal-entry-templates/42/",
      payload,
    );
    expect(result).toEqual(template);
  });

  it("propagates rejections (409 duplicate name) to the caller", async () => {
    authPatchJSONMock.mockRejectedValue(
      new ApiError(409, "Duplicate name"),
    );
    await expect(
      updateJournalEntryTemplate(42, {
        name: "Collides",
        description: "—",
        lines: [
          { account_id: 1, side: "debit", amount: "1.00" },
          { account_id: 2, side: "credit", amount: "1.00" },
        ],
      }),
    ).rejects.toBeInstanceOf(ApiError);
  });
});


describe("deleteJournalEntryTemplate", () => {
  beforeEach(() => {
    authDeleteMock.mockReset();
  });

  it("DELETEs the correct detail URL", async () => {
    authDeleteMock.mockResolvedValue(undefined);
    await deleteJournalEntryTemplate(42);
    expect(authDeleteMock).toHaveBeenCalledTimes(1);
    expect(authDeleteMock).toHaveBeenCalledWith(
      "/admin/accounting/journal-entry-templates/42/",
    );
  });

  it("treats 404 as success (race-safe — template already gone)", async () => {
    authDeleteMock.mockRejectedValue(new ApiError(404, "Not found"));
    await expect(deleteJournalEntryTemplate(42)).resolves.toBeUndefined();
  });

  it("propagates non-404 errors (e.g., 500) to the caller", async () => {
    authDeleteMock.mockRejectedValue(new ApiError(500, "Server error"));
    await expect(deleteJournalEntryTemplate(42)).rejects.toBeInstanceOf(
      ApiError,
    );
  });
});
