// SESSION_236 (TASK_names-and-money.md) — guard tests for the small
// shared helpers. `formatMoney` is exercised in the components tests;
// this file locks the plural + date shape used across the sales
// workspace so the walk-called `1 notes` / `1 be-backs` regression
// cannot come back.

import { describe, expect, it } from "vitest";

import { formatDate, formatDateTime, plural } from "@/lib/text";
import { formatMoney } from "@/lib/utils";

describe("plural", () => {
  it("keeps singular for count 1", () => {
    expect(plural(1, "note")).toBe("1 note");
    expect(plural(1, "be-back")).toBe("1 be-back");
  });

  it("adds -s for zero and >1", () => {
    expect(plural(0, "note")).toBe("0 notes");
    expect(plural(3, "drive")).toBe("3 drives");
  });

  it("honours an explicit plural form", () => {
    expect(plural(2, "person", "people")).toBe("2 people");
  });
});

describe("formatMoney (frontend guard)", () => {
  it("adds a thousands separator to five-figure amounts", () => {
    expect(formatMoney("11795.00")).toContain(",");
    expect(formatMoney("11795.00")).toBe("$11,795.00");
    expect(formatMoney("9385")).toBe("$9,385.00");
  });

  it("handles null / empty / negative", () => {
    expect(formatMoney(null)).toBe("$0.00");
    expect(formatMoney("")).toBe("$0.00");
    expect(formatMoney("-500")).toContain("\u2212");
  });
});

describe("formatDate / formatDateTime", () => {
  it("does not leak an ISO stamp with microseconds", () => {
    const iso = "2026-08-29T13:11:31.681330+00:00";
    expect(formatDateTime(iso)).not.toContain(".681330");
    expect(formatDate(iso)).not.toContain(":");
  });
});
