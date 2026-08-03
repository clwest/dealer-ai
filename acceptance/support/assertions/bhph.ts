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
  sale_id: number;
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

// ---------------------------------------------------------------------
// M21.2 write-side helpers. Locate specific rows by state so the
// journey can interact with the correct fixture without leaning on
// list ordering.
// ---------------------------------------------------------------------

interface PromiseRow {
  id: number;
  state: "promised" | "kept" | "broken";
}

interface RepossessionRow {
  id: number;
  state: "ordered" | "recovered" | "re_intaked";
}

interface ContactRow {
  id: number;
}

async function fetchPromiseList(
  request: APIRequestContext,
  notePk: number,
): Promise<PromiseRow[]> {
  const url = `/api/dealer-ai/admin/bhph-notes/${notePk}/promises/list/`;
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as {
    results?: PromiseRow[];
    bhph_promises?: { results?: PromiseRow[] };
  };
  return body.bhph_promises?.results ?? body.results ?? [];
}

async function fetchRepoList(
  request: APIRequestContext,
  notePk: number,
): Promise<RepossessionRow[]> {
  const url = `/api/dealer-ai/admin/bhph-notes/${notePk}/repossessions/list/`;
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as {
    results?: RepossessionRow[];
    repossessions?: { results?: RepossessionRow[] };
  };
  return body.repossessions?.results ?? body.results ?? [];
}

async function fetchContactList(
  request: APIRequestContext,
  notePk: number,
): Promise<ContactRow[]> {
  const url = `/api/dealer-ai/admin/bhph-notes/${notePk}/contacts/list/`;
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as {
    results?: ContactRow[];
    collection_contacts?: { results?: ContactRow[] };
  };
  return body.collection_contacts?.results ?? body.results ?? [];
}

/**
 * Locate the M21.2 seeded promise in ``promised`` state. Asserts
 * exactly one exists (the fixture guarantee); returns its id.
 */
export async function findPromisedStatePromiseId(
  request: APIRequestContext,
  notePk: number,
): Promise<number> {
  const promises = await fetchPromiseList(request, notePk);
  const inState = promises.filter((p) => p.state === "promised");
  expect(
    inState.length,
    `expected at least one promise in 'promised' state on note ${notePk}; ` +
      `got ${inState.length} (states: ${promises.map((p) => p.state).join(", ")})`,
  ).toBeGreaterThanOrEqual(1);
  const first = inState[0];
  if (first === undefined) throw new Error("unreachable — expect guard above");
  return first.id;
}

/**
 * Locate the seeded repossession in ``ordered`` state.
 */
export async function findOrderedRepossessionId(
  request: APIRequestContext,
  notePk: number,
): Promise<number> {
  const repos = await fetchRepoList(request, notePk);
  const inState = repos.filter((r) => r.state === "ordered");
  expect(
    inState.length,
    `expected at least one repossession in 'ordered' state on note ${notePk}; ` +
      `got ${inState.length}`,
  ).toBeGreaterThanOrEqual(1);
  const first = inState[0];
  if (first === undefined) throw new Error("unreachable — expect guard above");
  return first.id;
}

/**
 * Locate the M21.2 seeded repossession in ``recovered`` state.
 */
export async function findRecoveredRepossessionId(
  request: APIRequestContext,
  notePk: number,
): Promise<number> {
  const repos = await fetchRepoList(request, notePk);
  const inState = repos.filter((r) => r.state === "recovered");
  expect(
    inState.length,
    `expected at least one repossession in 'recovered' state on note ${notePk}; ` +
      `got ${inState.length}`,
  ).toBeGreaterThanOrEqual(1);
  const first = inState[0];
  if (first === undefined) throw new Error("unreachable — expect guard above");
  return first.id;
}

interface ConditionReportRow {
  id: number;
  status: string;
}

/**
 * Locate the M21.2 seeded complete ConditionReport for the fixture
 * vehicle. The M12.6 mark-re-intaked endpoint requires the report ID;
 * we surface it via a helper because there's no shipped operator UI
 * for browsing intake reports.
 */
export async function findCompleteConditionReportId(
  request: APIRequestContext,
  stockNumber: string,
): Promise<number> {
  const url =
    `/api/dealer-ai/admin/vehicles/${stockNumber}/condition-report/latest/`;
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as {
    report?: ConditionReportRow;
    condition_report?: ConditionReportRow;
  };
  const report = body.report ?? body.condition_report;
  expect(
    report,
    `no ConditionReport surfaced for vehicle ${stockNumber}`,
  ).toBeDefined();
  expect(
    (report as ConditionReportRow).status,
    `ConditionReport for vehicle ${stockNumber} should be 'complete'`,
  ).toBe("complete");
  return (report as ConditionReportRow).id;
}

/**
 * Assert that a specific promise is in a given state.
 */
export async function expectPromiseState(
  request: APIRequestContext,
  notePk: number,
  promiseId: number,
  expected: "promised" | "kept" | "broken",
): Promise<void> {
  const promises = await fetchPromiseList(request, notePk);
  const row = promises.find((p) => p.id === promiseId);
  expect(row, `promise ${promiseId} missing from note ${notePk}`).toBeDefined();
  expect(
    (row as PromiseRow).state,
    `promise ${promiseId} expected state ${expected}, got ${(row as PromiseRow).state}`,
  ).toBe(expected);
}

/**
 * Assert that a specific repossession is in a given state.
 */
export async function expectRepossessionState(
  request: APIRequestContext,
  notePk: number,
  repoId: number,
  expected: "ordered" | "recovered" | "re_intaked",
): Promise<void> {
  const repos = await fetchRepoList(request, notePk);
  const row = repos.find((r) => r.id === repoId);
  expect(row, `repo ${repoId} missing from note ${notePk}`).toBeDefined();
  expect(
    (row as RepossessionRow).state,
    `repo ${repoId} expected state ${expected}, got ${(row as RepossessionRow).state}`,
  ).toBe(expected);
}

/**
 * Fetch current child counts — used by the journey to assert deltas
 * after a successful write.
 */
export interface NoteChildCounts {
  promises: number;
  contacts: number;
  repossessions: number;
}

export async function fetchChildCounts(
  request: APIRequestContext,
  notePk: number,
): Promise<NoteChildCounts> {
  const [promises, contacts, repos] = await Promise.all([
    fetchPromiseList(request, notePk),
    fetchContactList(request, notePk),
    fetchRepoList(request, notePk),
  ]);
  return {
    promises: promises.length,
    contacts: contacts.length,
    repossessions: repos.length,
  };
}

/**
 * Verify the note detail's four child collections all have the
 * expected minimum count. The M20.4 seed plants exactly one of each,
 * so this asserts >= 1.
 */
// ---------------------------------------------------------------------
// M23.3 — payment intake assertion helper.
// ---------------------------------------------------------------------

interface BhphPaymentRow {
  id: number;
  note_id: number;
  amount: string;
  method: string;
  paid_at: string;
}

async function fetchPaymentList(
  request: APIRequestContext,
  notePk: number,
): Promise<BhphPaymentRow[]> {
  const url = `/api/dealer-ai/admin/bhph-notes/${notePk}/payments/list/`;
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as {
    results?: BhphPaymentRow[];
    bhph_payments?: { results?: BhphPaymentRow[] };
  };
  return body.bhph_payments?.results ?? body.results ?? [];
}

/**
 * Assert that a BhphPayment with the given amount + method exists
 * on the note. The M23.3 payment-intake journey uses this to prove
 * the payment landed durably at the service layer after the form
 * submit. Since the M23.3 seed's fresh-note fixture starts with
 * zero payments, asserting "at least one payment exists with
 * matching amount+method" is a stable business-outcome check that
 * doesn't require baseline arithmetic.
 */
export async function expectBhphPaymentRecorded(
  request: APIRequestContext,
  notePk: number,
  expected: {
    amount: string;
    method: "cash" | "check" | "debit" | "ach" | "other";
  },
): Promise<BhphPaymentRow> {
  const payments = await fetchPaymentList(request, notePk);
  const matches = payments.filter(
    (p) =>
      Number(p.amount) === Number(expected.amount) &&
      p.method === expected.method,
  );
  expect(
    matches.length,
    `expected at least one BhphPayment on note ${notePk} with amount=${expected.amount} method=${expected.method}; found ${matches.length} in ${JSON.stringify(payments)}`,
  ).toBeGreaterThanOrEqual(1);
  return matches[0]!;
}


// ---------------------------------------------------------------------
// M23.2 — note origination assertion helper.
// ---------------------------------------------------------------------

/**
 * Assert that a BhphNote exists targeting the given sale, and that
 * its terms match the values the origination journey submitted.
 * Fails loudly if no note exists for the sale or if the persisted
 * terms drift from what the operator entered — either is an
 * operational-completeness regression on the M12 origination path.
 */
export async function expectBhphNoteOriginated(
  request: APIRequestContext,
  saleId: number,
  expected: {
    principal: string;
    apr: string;
    termWeeks: number;
    paymentFrequency: "weekly" | "biweekly" | "semi_monthly";
  },
): Promise<BhphNoteProjection> {
  const notes = await fetchNoteList(request);
  const matches = notes.filter((n) => n.sale_id === saleId);
  expect(
    matches.length,
    `expected exactly one BhphNote targeting sale ${saleId}; found ${matches.length}`,
  ).toBe(1);
  const note = matches[0]!;
  expect(
    Number(note.principal_financed),
    `note ${note.id} principal_financed=${note.principal_financed} vs expected ${expected.principal}`,
  ).toBeCloseTo(Number(expected.principal), 2);
  expect(
    Number(note.apr),
    `note ${note.id} apr=${note.apr} vs expected ${expected.apr}`,
  ).toBeCloseTo(Number(expected.apr), 2);
  expect(
    note.term_weeks,
    `note ${note.id} term_weeks=${note.term_weeks} vs expected ${expected.termWeeks}`,
  ).toBe(expected.termWeeks);
  expect(
    note.payment_frequency,
    `note ${note.id} payment_frequency=${note.payment_frequency} vs expected ${expected.paymentFrequency}`,
  ).toBe(expected.paymentFrequency);
  return note;
}


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
