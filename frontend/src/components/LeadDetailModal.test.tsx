// Milestone 25 · Increment 1 (SESSION_186) — LeadDetailModal Source
// section tests per MILESTONE_25_PLANNING.md §5.c.
//
// Pure-function coverage for the source-line helpers. The full modal
// is not mounted here — the fetch orchestration is exercised by
// existing tests and the Playwright acceptance journeys (M24.3 +
// M24.4 extended in this increment). What matters at unit level is
// the channel × attribution decision table.

import { describe, expect, it } from "vitest";

import type { LeadDetailResponse } from "@/lib/api";
import { computeSourceLine, displayPlatform } from "./LeadDetailModal";

function makeLead(
  overrides: Partial<LeadDetailResponse["lead"]> = {},
): LeadDetailResponse["lead"] {
  return {
    id: 1,
    name: "Alice Buyer",
    phone: "555-0100",
    email: "alice@example.com",
    created_at: "2026-08-03T00:00:00Z",
    handed_off: false,
    interested_vehicles: [],
    conversation_summary: "",
    recommended_next_action: "",
    credit_range: "",
    channel: "chat",
    referrer: null,
    referrer_name: "",
    source_metadata: {},
    ...overrides,
  };
}

describe("displayPlatform", () => {
  it("returns empty string for missing / non-string input", () => {
    expect(displayPlatform(undefined)).toBe("");
    expect(displayPlatform(null)).toBe("");
    expect(displayPlatform("")).toBe("");
    expect(displayPlatform(42)).toBe("");
  });

  it("title-cases single-word platform identifiers", () => {
    expect(displayPlatform("autotrader")).toBe("Autotrader");
    expect(displayPlatform("generic")).toBe("Generic");
  });

  it("splits + title-cases multi-word identifiers", () => {
    expect(displayPlatform("cars_com")).toBe("Cars Com");
    expect(displayPlatform("facebook-marketplace")).toBe("Facebook Marketplace");
    expect(displayPlatform("car gurus")).toBe("Car Gurus");
  });
});

describe("computeSourceLine", () => {
  it("returns null for chat channel (no attribution)", () => {
    expect(computeSourceLine(makeLead({ channel: "chat" }))).toBeNull();
  });

  it("returns null for walk_in / phone / other channels", () => {
    expect(computeSourceLine(makeLead({ channel: "walk_in" }))).toBeNull();
    expect(computeSourceLine(makeLead({ channel: "phone" }))).toBeNull();
    expect(computeSourceLine(makeLead({ channel: "other" }))).toBeNull();
  });

  it("returns 'Referred by: {name}' for referral leads with a referrer_name", () => {
    expect(
      computeSourceLine(
        makeLead({ channel: "referral", referrer_name: "Ray Referrer" }),
      ),
    ).toBe("Referred by: Ray Referrer");
  });

  it("falls back for referral leads with no linked referrer", () => {
    expect(
      computeSourceLine(
        makeLead({ channel: "referral", referrer: null, referrer_name: "" }),
      ),
    ).toBe("Referral (referrer not linked)");
  });

  it("returns 'Source: {platform}' for listing_form leads with a platform", () => {
    expect(
      computeSourceLine(
        makeLead({
          channel: "listing_form",
          source_metadata: { platform: "autotrader" },
        }),
      ),
    ).toBe("Source: Autotrader");
  });

  it("title-cases multi-word listing_form platforms", () => {
    expect(
      computeSourceLine(
        makeLead({
          channel: "listing_form",
          source_metadata: { platform: "facebook-marketplace" },
        }),
      ),
    ).toBe("Source: Facebook Marketplace");
  });

  it("falls back to 'Source: Listing form' when platform metadata missing", () => {
    expect(
      computeSourceLine(
        makeLead({ channel: "listing_form", source_metadata: {} }),
      ),
    ).toBe("Source: Listing form");
    expect(
      computeSourceLine(
        makeLead({
          channel: "listing_form",
          source_metadata: { platform: "" },
        }),
      ),
    ).toBe("Source: Listing form");
  });
});
