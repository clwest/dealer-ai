// SESSION_244 (walk finding 53) — store-zone date-boundary tests.
//
// The failure this file guards is: an "as of today" trial balance
// rendered on a laptop in Denver for a store in Yuma reads
// "10:59 PM" for what should be end-of-business at 11:59 PM. If the
// helpers under test fall back to the browser's clock, the test host's
// zone must NOT be the store's — otherwise the test agrees with the
// bug. See ``setBrowserTimezone`` below.

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import {
  dateEndOfDayInStoreZoneIso,
  formatDateInStoreZone,
  storeNowLabel,
  storeTodayIsoDate,
} from "@/lib/storeTime";

const PHOENIX = "America/Phoenix";

// Force the test host into a zone that disagrees with Arizona. Any
// zone works as long as it is not America/Phoenix; New_York keeps
// the delta obvious in failure messages (-4 or -5h from Phoenix in DST
// season, -3h during winter after the Phoenix offset flips vs Mountain).
const HOST_TZ_FOR_TESTS = "America/New_York";

let originalDateTimeFormat: typeof Intl.DateTimeFormat;

function setBrowserTimezone(zone: string): void {
  // jsdom does not honour the TZ env var per-test, so shim the default
  // Intl formatter's resolvedOptions to advertise a chosen zone. The
  // per-call ``timeZone`` option always wins over the default, which
  // is what the store-zone helpers rely on — this shim only affects
  // "what the browser thinks it is."
  const Original = originalDateTimeFormat;
  const Patched = function (locale?: string | string[], options?: Intl.DateTimeFormatOptions) {
    const effective: Intl.DateTimeFormatOptions = { ...(options ?? {}) };
    if (!effective.timeZone) effective.timeZone = zone;
    return new Original(locale, effective);
  } as unknown as typeof Intl.DateTimeFormat;
  // Preserve statics so ``Intl.DateTimeFormat.supportedLocalesOf`` still works.
  Patched.supportedLocalesOf = Original.supportedLocalesOf.bind(Original);
  Object.setPrototypeOf(Patched, Original);
  Object.setPrototypeOf(Patched.prototype, Original.prototype);
  Intl.DateTimeFormat = Patched;
}

beforeAll(() => {
  originalDateTimeFormat = Intl.DateTimeFormat;
  setBrowserTimezone(HOST_TZ_FOR_TESTS);
});

afterAll(() => {
  Intl.DateTimeFormat = originalDateTimeFormat;
});


describe("host-timezone shim", () => {
  it("advertises the chosen zone as the browser default", () => {
    // Guard the guard: if the shim is silently no-op'd, the store-zone
    // tests below could still pass by coincidence when host === store.
    expect(Intl.DateTimeFormat().resolvedOptions().timeZone).toBe(
      HOST_TZ_FOR_TESTS,
    );
    expect(Intl.DateTimeFormat().resolvedOptions().timeZone).not.toBe(PHOENIX);
  });
});


describe("storeTodayIsoDate", () => {
  it("returns the store's today when host and store disagree on the date", () => {
    // 04:30 UTC on 2026-09-05 is: 21:30 on 2026-09-04 in Phoenix
    // (UTC-7, no DST) but 00:30 on 2026-09-05 in New_York (EDT, UTC-4).
    const utcInstant = new Date("2026-09-05T04:30:00Z");
    expect(storeTodayIsoDate(PHOENIX, utcInstant)).toBe("2026-09-04");
    expect(storeTodayIsoDate(HOST_TZ_FOR_TESTS, utcInstant)).toBe("2026-09-05");
  });

  it("falls back to the browser's today when the zone is missing", () => {
    const utcInstant = new Date("2026-09-05T04:30:00Z");
    expect(storeTodayIsoDate("", utcInstant)).toBe("2026-09-05");
    expect(storeTodayIsoDate(null, utcInstant)).toBe("2026-09-05");
  });

  it("falls back to the browser's today when the zone name is invalid", () => {
    const utcInstant = new Date("2026-09-05T04:30:00Z");
    expect(storeTodayIsoDate("Not/A_Zone", utcInstant)).toBe("2026-09-05");
  });
});


describe("dateEndOfDayInStoreZoneIso", () => {
  it("returns the UTC instant that reads 11:59 PM in the store's zone", () => {
    // Phoenix is UTC-7 year round. End-of-day 2026-09-04 in Phoenix is
    // 06:59:59.999Z on 2026-09-05.
    const iso = dateEndOfDayInStoreZoneIso("2026-09-04", PHOENIX);
    expect(iso).toBe("2026-09-05T06:59:59.999Z");
    // And that same instant rendered back into Phoenix reads 11:59 PM
    // on 2026-09-04 — the header claim the operator sees.
    expect(formatDateInStoreZone(iso, PHOENIX)).toBe("Sep 4, 2026");
    const time = new Intl.DateTimeFormat("en-US", {
      timeZone: PHOENIX,
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(iso));
    expect(time).toBe("11:59 PM");
  });

  it("handles a spring-forward DST boundary in America/Denver", () => {
    // Denver springs forward on 2026-03-08; end-of-day is still 23:59:59
    // Mountain, which is UTC-6 after the switch. Guards the DST
    // correction pass in ``endOfDayInstantMs``.
    const iso = dateEndOfDayInStoreZoneIso("2026-03-08", "America/Denver");
    expect(iso).toBe("2026-03-09T05:59:59.999Z");
  });

  it("returns empty string for missing or malformed input", () => {
    expect(dateEndOfDayInStoreZoneIso("", PHOENIX)).toBe("");
    expect(dateEndOfDayInStoreZoneIso(null, PHOENIX)).toBe("");
    expect(dateEndOfDayInStoreZoneIso("2026/09/04", PHOENIX)).toBe("");
  });

  it("does not match the browser-zone boundary the old helper produced", () => {
    // Regression fence: the previous helper built 23:59:59 in the
    // browser's zone. In New_York (UTC-4 on this date), that instant is
    // 03:59:59Z on 2026-09-05 — an hour earlier than the store-zone
    // truth. If someone re-introduces the old shape this catches it.
    const storeZoneIso = dateEndOfDayInStoreZoneIso("2026-09-04", PHOENIX);
    const browserZoneIso = new Date(2026, 8, 4, 23, 59, 59, 0).toISOString();
    expect(storeZoneIso).not.toBe(browserZoneIso);
    expect(new Date(storeZoneIso).getTime()).toBeGreaterThan(
      new Date(browserZoneIso).getTime(),
    );
  });
});


describe("storeNowLabel (sanity check under the shim)", () => {
  it("renders the store's wall-clock, not the browser's", () => {
    // Confirms the existing formatter still routes through the store's
    // zone once the host-zone shim is in place.
    const utcInstant = new Date("2026-09-05T04:30:00Z");
    expect(storeNowLabel(PHOENIX, utcInstant)).toBe("9:30 PM");
    expect(storeNowLabel(HOST_TZ_FOR_TESTS, utcInstant)).toBe("12:30 AM");
  });
});
