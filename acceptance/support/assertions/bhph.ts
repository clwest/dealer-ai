// Milestone 20 · Increment 4 — business-outcome assertion helpers
// for the BHPH collections read-side journey.
//
// Per the M20 guiding principle: assertions target business state
// (the seeded note is visible in the list; the note detail's
// promise/contact/repo cards render the seeded content) via the
// M12 admin API, not DOM state.
//
// M20.4 is scope-narrowed to the read side per §0.a M20.4
// decision 1 — the write-side operations (record PtP, mark broken,
// log contact, initiate repo) have no shipped frontend UI as of
// M12.7. The seed provisions all four write-side artefacts via
// M12 service verbs; the journey verifies they're visible.

import { APIRequestContext, expect } from "@playwright/test";

export interface BhphNoteProjection {
  id: number;
  principal_financed: string;
  apr: string;
  term_weeks: number;
  payment_frequency: string;
  payment_amount: string;
  first_payment_due: string;
  current_bucket: string;
  days_past_due: number;
}

// The list endpoint returns a bare `{count, results}` (see
// frontend/src/lib/bhphApi.ts line 79-82), not an envelope-wrapped
// response. Different from the M17 accounting endpoints.
export interface BhphNoteListResponse {
  count: number;
  results: BhphNoteProjection[];
}

async function fetchNoteList(
  request: APIRequestContext,
): Promise<BhphNoteProjection[]> {
  const url = "/api/dealer-ai/admin/bhph-notes/list/";
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as BhphNoteListResponse;
  return body.results ?? [];
}

/**
 * Find the note that matches the seeded fixture's principal +
 * APR + term (a stable signature on the acceptance DB where the
 * M20.4 seed is the sole source of BHPH notes). The note detail
 * response doesn't expose `sale.vehicle.stock_number` (see
 * bhphApi.ts BhphNoteDetailResponse), so we match on the
 * distinctive loan terms.
 */
export async function findSeededNoteId(
  request: APIRequestContext,
  fixture: {
    principal: string;
    apr: string;
    termWeeks: number;
  },
): Promise<number> {
  const notes = await fetchNoteList(request);
  expect(
    notes.length,
    `expected at least one BHPH note; got ${notes.length}`,
  ).toBeGreaterThan(0);
  const match = notes.find(
    (n) =>
      Number(n.principal_financed) === Number(fixture.principal) &&
      Number(n.apr) === Number(fixture.apr) &&
      n.term_weeks === fixture.termWeeks,
  );
  expect(
    match,
    `seeded fixture note not found on acceptance DB. ` +
      `Expected principal=${fixture.principal} apr=${fixture.apr} ` +
      `term=${fixture.termWeeks}w. Got: ` +
      notes
        .map(
          (n) =>
            `[pk=${n.id} p=${n.principal_financed} apr=${n.apr} t=${n.term_weeks}w]`,
        )
        .join(" "),
  ).toBeDefined();
  return (match as BhphNoteProjection).id;
}

interface CountedListResponse {
  count?: number;
  results?: unknown[];
  // some M12 list endpoints envelope-wrap
  bhph_payments?: { count?: number; results?: unknown[] };
  bhph_promises?: { count?: number; results?: unknown[] };
  collection_contacts?: { count?: number; results?: unknown[] };
  repossessions?: { count?: number; results?: unknown[] };
}

async function fetchChildListCount(
  request: APIRequestContext,
  notePk: number,
  path: "payments" | "promises" | "contacts" | "repossessions",
  envelopeKey:
    | "bhph_payments"
    | "bhph_promises"
    | "collection_contacts"
    | "repossessions",
): Promise<number> {
  const url = `/api/dealer-ai/admin/bhph-notes/${notePk}/${path}/list/`;
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as CountedListResponse;
  // Handle both wrapped `{envelopeKey: {results: [], count: N}}` and
  // bare `{results: [], count: N}` shapes.
  const nested = body[envelopeKey];
  if (nested !== undefined) {
    if (typeof nested.count === "number") return nested.count;
    if (Array.isArray(nested.results)) return nested.results.length;
  }
  if (typeof body.count === "number") return body.count;
  if (Array.isArray(body.results)) return body.results.length;
  return 0;
}

/**
 * Verify the note detail's four child collections all have the
 * expected minimum count. The M20.4 seed plants exactly one of each,
 * so this asserts >= 1.
 */
export async function expectNoteDetailPopulated(
  request: APIRequestContext,
  notePk: number,
): Promise<void> {
  const payments = await fetchChildListCount(
    request,
    notePk,
    "payments",
    "bhph_payments",
  );
  expect(
    payments,
    `note ${notePk} should have at least one payment`,
  ).toBeGreaterThanOrEqual(1);

  const promises = await fetchChildListCount(
    request,
    notePk,
    "promises",
    "bhph_promises",
  );
  expect(
    promises,
    `note ${notePk} should have at least one promise-to-pay`,
  ).toBeGreaterThanOrEqual(1);

  const contacts = await fetchChildListCount(
    request,
    notePk,
    "contacts",
    "collection_contacts",
  );
  expect(
    contacts,
    `note ${notePk} should have at least one collection contact`,
  ).toBeGreaterThanOrEqual(1);

  const repos = await fetchChildListCount(
    request,
    notePk,
    "repossessions",
    "repossessions",
  );
  expect(
    repos,
    `note ${notePk} should have at least one repossession`,
  ).toBeGreaterThanOrEqual(1);
}
