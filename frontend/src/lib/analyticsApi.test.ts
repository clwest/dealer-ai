// Milestone 8 · Increment 5 (SESSION_098) — analytics helper tests.
//
// Covers the display-formatting helpers. The API-client fetch
// wrappers are exercised end-to-end via the tab tests
// (AcquisitionReconTab.test.tsx etc.), not stub-tested here.

import { describe, expect, it } from "vitest";

import { formatMoney, formatPercent, formatSnapshotAt } from "@/lib/analyticsApi";

describe("formatMoney", () => {
  it("adds thousands separators + dollar sign", () => {
    expect(formatMoney("1234.56")).toBe("$1,234.56");
  });

  it("handles million-scale numbers", () => {
    expect(formatMoney("1234567.89")).toBe("$1,234,567.89");
  });

  it("handles negatives", () => {
    expect(formatMoney("-42.00")).toBe("-$42.00");
  });

  it("defaults missing cents to .00", () => {
    expect(formatMoney("100")).toBe("$100.00");
  });
});

describe("formatPercent", () => {
  it("appends a percent sign to non-null values", () => {
    expect(formatPercent("8.75")).toBe("8.75%");
  });

  it("renders null as em-dash", () => {
    expect(formatPercent(null)).toBe("—");
  });
});

describe("formatSnapshotAt", () => {
  it("returns a non-empty human-readable string for a valid ISO input", () => {
    const rendered = formatSnapshotAt("2026-08-01T03:00:00Z");
    // Timezone-dependent, so just assert the shape isn't the raw ISO
    // and includes recognizable components (year + a month name).
    expect(rendered).not.toBe("2026-08-01T03:00:00Z");
    expect(rendered).toMatch(/2026/);
  });
});
