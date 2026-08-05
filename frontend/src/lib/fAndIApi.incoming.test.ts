// Milestone 32 · Increment 3 (SESSION_209) — fetchCreditApplications
// wrapper tests.
//
// Guards URL shape, filter param serialization, envelope
// unwrapping, and the D8-revised `intake=true`-only posture (only
// `intake === true` sends the param; every other truthy value is
// omitted, which the backend treats as unfiltered).

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/authFetch", async () => {
  const actual = await vi.importActual<typeof import("@/lib/authFetch")>(
    "@/lib/authFetch",
  );
  return {
    ...actual,
    authGetJSON: vi.fn(),
  };
});

import { authGetJSON } from "@/lib/authFetch";
import {
  fetchCreditApplications,
  type CreditApplicationProjection,
} from "@/lib/fAndIApi";

const authGetJSONMock = vi.mocked(authGetJSON);

function fixtureCA(
  overrides: Partial<CreditApplicationProjection> = {},
): CreditApplicationProjection {
  return {
    id: 1,
    lead_id: 100,
    sale_id: null,
    applicant_full_name: "Intake Iris",
    applicant_ssn_last4: "",
    source_format: "tablet",
    status: "received",
    captured_at: "2026-08-04T12:00:00Z",
    retention_expires_at: "2033-08-04T12:00:00Z",
    notes: "Deal write-up #42 handoff:\n- Vehicle price: $42500.00",
    created_at: "2026-08-04T12:00:00Z",
    updated_at: "2026-08-04T12:00:00Z",
    writeup_context: {
      deal_writeup_id: 42,
      written_up_by_user_id: 5,
      sales_manager_approved_by_user_id: 5,
      handed_off_to_fandi_at: "2026-08-04T12:00:00Z",
      lead: {
        id: 100,
        name: "Intake Iris",
        phone: "+15553201501",
        email: "intake-iris@example.com",
      },
      vehicle: {
        id: 200,
        stock_number: "FANDI-INTAKE-1",
        year: 2024,
        make: "Ford",
        model: "F-150",
      },
      terms: {
        vehicle_price: "42500.00",
        trade_allowance: "7500.00",
        down_payment: "3000.00",
        monthly_payment_target: "585.00",
        term_months_target: 60,
        apr_target: "6.99",
      },
    },
    // M33.1 derived-status fixture defaults (Incoming — no
    // DealStructure yet). Tests can override to exercise the
    // In progress branch.
    has_deal_structure: false,
    latest_deal_structure_id: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("fetchCreditApplications", () => {
  it("posts to /admin/credit-applications/list/ with no params", async () => {
    authGetJSONMock.mockResolvedValueOnce({ credit_applications: [] });
    const rows = await fetchCreditApplications();
    expect(authGetJSONMock).toHaveBeenCalledWith(
      "/admin/credit-applications/list/",
    );
    expect(rows).toEqual([]);
  });

  it("sends intake=true when intake is boolean true", async () => {
    authGetJSONMock.mockResolvedValueOnce({ credit_applications: [] });
    await fetchCreditApplications({ intake: true });
    expect(authGetJSONMock).toHaveBeenCalledWith(
      "/admin/credit-applications/list/?intake=true",
    );
  });

  it("omits intake when intake is boolean false (D8-revised: never sends intake=false)", async () => {
    authGetJSONMock.mockResolvedValueOnce({ credit_applications: [] });
    await fetchCreditApplications({ intake: false });
    // Backend rejects `intake=false` per §5.h. Wrapper must not send
    // it — unfiltered = omit.
    expect(authGetJSONMock).toHaveBeenCalledWith(
      "/admin/credit-applications/list/",
    );
  });

  it("serializes leadId + since into query params", async () => {
    authGetJSONMock.mockResolvedValueOnce({ credit_applications: [] });
    await fetchCreditApplications({
      leadId: 100,
      since: "2026-08-01T00:00:00Z",
    });
    expect(authGetJSONMock).toHaveBeenCalledWith(
      "/admin/credit-applications/list/?lead_id=100&since=2026-08-01T00%3A00%3A00Z",
    );
  });

  it("unwraps the credit_applications envelope", async () => {
    authGetJSONMock.mockResolvedValueOnce({
      credit_applications: [fixtureCA(), fixtureCA({ id: 2 })],
    });
    const rows = await fetchCreditApplications({ intake: true });
    expect(rows).toHaveLength(2);
    expect(rows[0]!.id).toBe(1);
    expect(rows[1]!.id).toBe(2);
  });

  it("returns rows with populated writeup_context for hand-off CAs", async () => {
    authGetJSONMock.mockResolvedValueOnce({
      credit_applications: [fixtureCA()],
    });
    const rows = await fetchCreditApplications();
    const ctx = rows[0]!.writeup_context;
    expect(ctx).not.toBeNull();
    expect(ctx!.deal_writeup_id).toBe(42);
    expect(ctx!.lead.name).toBe("Intake Iris");
    expect(ctx!.terms.vehicle_price).toBe("42500.00");
  });

  it("returns rows with null writeup_context for direct-create CAs", async () => {
    authGetJSONMock.mockResolvedValueOnce({
      credit_applications: [fixtureCA({ writeup_context: null })],
    });
    const rows = await fetchCreditApplications();
    expect(rows[0]!.writeup_context).toBeNull();
  });

  it("propagates authGetJSON errors", async () => {
    const err = new Error("boom");
    authGetJSONMock.mockRejectedValueOnce(err);
    await expect(fetchCreditApplications()).rejects.toBe(err);
  });
});
