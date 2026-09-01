// TASK_doors-and-matrix-refresh Part B — assertions for the two
// new sidebar entries (BHPH portfolio + trial-balance accounting
// door). Data-level test against the exported NAV_ITEMS: the
// harness for App itself is heavy (AuthContext + brand + router
// + Sheet), and the door-existence claim is a data claim.

import { describe, expect, it } from "vitest";

import { NAV_ITEMS } from "@/App";

describe("NAV_ITEMS — Part B door entries", () => {
  it("includes the BHPH portfolio door pointing at /dealer-ai-bhph/portfolio", () => {
    const bhph = NAV_ITEMS.find((item) => item.to === "/dealer-ai-bhph/portfolio");
    expect(bhph).toBeDefined();
    expect(bhph?.label).toBe("BHPH");
  });

  it("includes the accounting door pointing at /dealer-ai-accounting/trial-balance", () => {
    const accounting = NAV_ITEMS.find(
      (item) => item.to === "/dealer-ai-accounting/trial-balance",
    );
    expect(accounting).toBeDefined();
    expect(accounting?.label).toBe("Accounting");
  });
});
