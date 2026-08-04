// Milestone 32 · Increment 2 (SESSION_208) — deal-writeup API wrappers.
//
// Guards listDealWriteups + getDealWriteup + createDealWriteup +
// approveDealWriteup + handOffDealWriteup + derivedWriteupState:
// URL shape, HTTP verb, payload shape, envelope unwrapping, filter
// param serialization. Mocks authFetch so no real network is touched.
//
// Also guards removal of the "UI deferred" comments per §5.h — the
// module docstring must not carry "UI deferred" language after M32.2.
// The source-text assertion uses Vite's ?raw import (available in
// the vitest environment) rather than node:fs, keeping the test
// portable across jsdom / node test environments.

import { beforeEach, describe, expect, it, vi } from "vitest";

import salesApiSource from "@/lib/salesApi.ts?raw";

vi.mock("@/lib/authFetch", async () => {
  const actual = await vi.importActual<typeof import("@/lib/authFetch")>(
    "@/lib/authFetch",
  );
  return {
    ...actual,
    authGetJSON: vi.fn(),
    authPostJSON: vi.fn(),
  };
});

import { authGetJSON, authPostJSON } from "@/lib/authFetch";
import {
  approveDealWriteup,
  createDealWriteup,
  derivedWriteupState,
  getDealWriteup,
  handOffDealWriteup,
  listDealWriteups,
  type DealWriteupProjection,
} from "@/lib/salesApi";

const authGetJSONMock = vi.mocked(authGetJSON);
const authPostJSONMock = vi.mocked(authPostJSON);

function fixtureWriteup(
  overrides: Partial<DealWriteupProjection> = {},
): DealWriteupProjection {
  return {
    id: 42,
    lead_id: 100,
    vehicle_id: 200,
    dealership_id: 1,
    vehicle_price: "28500.00",
    trade_allowance: "4500.00",
    down_payment: "2000.00",
    monthly_payment_target: "450.00",
    term_months_target: 72,
    apr_target: "7.49",
    write_up_at: "2026-08-04T10:00:00Z",
    written_up_by_user_id: 5,
    sales_manager_approved_at: null,
    sales_manager_approved_by_user_id: null,
    handed_off_to_fandi_at: null,
    notes: "",
    created_at: "2026-08-04T10:00:00Z",
    updated_at: "2026-08-04T10:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("listDealWriteups", () => {
  it("posts to /admin/deal-writeups/list/ with no params", async () => {
    authGetJSONMock.mockResolvedValueOnce({
      deal_writeups: [fixtureWriteup()],
    });
    const rows = await listDealWriteups();
    expect(authGetJSONMock).toHaveBeenCalledWith(
      "/admin/deal-writeups/list/",
    );
    expect(rows).toHaveLength(1);
  });

  it("serializes leadId + state into query params", async () => {
    authGetJSONMock.mockResolvedValueOnce({ deal_writeups: [] });
    await listDealWriteups({ leadId: 100, state: "pending" });
    expect(authGetJSONMock).toHaveBeenCalledWith(
      "/admin/deal-writeups/list/?lead_id=100&state=pending",
    );
  });

  it("propagates authGetJSON errors", async () => {
    const err = new Error("network");
    authGetJSONMock.mockRejectedValueOnce(err);
    await expect(listDealWriteups()).rejects.toBe(err);
  });
});

describe("getDealWriteup", () => {
  it("posts to /admin/deal-writeups/<pk>/ and unwraps envelope", async () => {
    authGetJSONMock.mockResolvedValueOnce({
      deal_writeup: fixtureWriteup({ id: 77 }),
    });
    const row = await getDealWriteup(77);
    expect(authGetJSONMock).toHaveBeenCalledWith("/admin/deal-writeups/77/");
    expect(row.id).toBe(77);
  });
});

describe("createDealWriteup", () => {
  it("POSTs to /admin/deal-writeups/ with the exact payload", async () => {
    authPostJSONMock.mockResolvedValueOnce({
      deal_writeup: fixtureWriteup(),
    });
    const payload = {
      lead_id: 100,
      vehicle_id: 200,
      vehicle_price: "28500.00",
      monthly_payment_target: "450.00",
      term_months_target: 72,
    };
    const created = await createDealWriteup(payload);
    expect(authPostJSONMock).toHaveBeenCalledWith(
      "/admin/deal-writeups/",
      payload,
    );
    expect(created.id).toBe(42);
  });

  it("propagates authPostJSON errors", async () => {
    const err = new Error("boom");
    authPostJSONMock.mockRejectedValueOnce(err);
    await expect(
      createDealWriteup({ lead_id: 1, vehicle_id: 2 }),
    ).rejects.toBe(err);
  });
});

describe("approveDealWriteup", () => {
  it("POSTs to /admin/deal-writeups/<pk>/approve/ with an empty body", async () => {
    authPostJSONMock.mockResolvedValueOnce({
      deal_writeup: fixtureWriteup({
        sales_manager_approved_at: "2026-08-04T11:00:00Z",
      }),
    });
    const row = await approveDealWriteup(42);
    expect(authPostJSONMock).toHaveBeenCalledWith(
      "/admin/deal-writeups/42/approve/",
      {},
    );
    expect(row.sales_manager_approved_at).toBe("2026-08-04T11:00:00Z");
  });
});

describe("handOffDealWriteup", () => {
  it("POSTs to /admin/deal-writeups/<pk>/hand-off/ and returns the CA envelope", async () => {
    authPostJSONMock.mockResolvedValueOnce({
      deal_writeup: fixtureWriteup({
        handed_off_to_fandi_at: "2026-08-04T12:00:00Z",
      }),
      credit_application: {
        id: 999,
        lead_id: 100,
        source_format: "tablet",
        captured_at: "2026-08-04T12:00:00Z",
      },
    });
    const res = await handOffDealWriteup(42);
    expect(authPostJSONMock).toHaveBeenCalledWith(
      "/admin/deal-writeups/42/hand-off/",
      {},
    );
    expect(res.credit_application.id).toBe(999);
    expect(res.deal_writeup.handed_off_to_fandi_at).toBe(
      "2026-08-04T12:00:00Z",
    );
  });
});

describe("derivedWriteupState", () => {
  it("returns pending when neither timestamp is set", () => {
    expect(derivedWriteupState(fixtureWriteup())).toBe("pending");
  });

  it("returns approved when only approved_at is set", () => {
    expect(
      derivedWriteupState(
        fixtureWriteup({
          sales_manager_approved_at: "2026-08-04T11:00:00Z",
        }),
      ),
    ).toBe("approved");
  });

  it("returns handed_off when handed_off_at is set (regardless of approved)", () => {
    expect(
      derivedWriteupState(
        fixtureWriteup({
          sales_manager_approved_at: "2026-08-04T11:00:00Z",
          handed_off_to_fandi_at: "2026-08-04T12:00:00Z",
        }),
      ),
    ).toBe("handed_off");
  });
});

describe("§5.h non-goal — UI deferred comment removed", () => {
  it("salesApi.ts source no longer carries 'UI deferred' language", () => {
    expect(salesApiSource).not.toMatch(/UI deferred/i);
  });
});
