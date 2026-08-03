// Milestone 20 · Increment 2 — business-outcome assertion helpers for
// the dashboard-centric journeys (owner morning review + sales
// manager daily startup).
//
// Per M20 guiding principle: assertions target business state (a
// lead exists, a lead is assigned to a named advisor), not DOM state.
// The M18/M19 admin API surface is the source of truth; UI state
// that doesn't match the admin API is a rendering bug the acceptance
// suite is meant to catch.

import { APIRequestContext, expect } from "@playwright/test";

export interface AdminLeadAssignment {
  id: number;
  slug: string;
  name: string;
}

export interface AdminLead {
  id: number;
  name: string;
  phone: string;
  email: string;
  urgency: string;
  channel: string;
  handed_off: boolean;
  assigned_to: AdminLeadAssignment | null;
  assigned_at: string | null;
  notes: string;
  created_at: string;
}

interface AdminLeadListResponse {
  results?: AdminLead[];
  count?: number;
}

async function fetchLeadList(
  request: APIRequestContext,
  params: Record<string, string | number> = {},
): Promise<AdminLead[]> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    query.set(key, String(value));
  }
  const url = `/api/dealer-ai/admin/leads/${
    query.toString() ? `?${query.toString()}` : ""
  }`;
  const response = await request.get(url);
  expect(response.status(), `GET ${url} returned non-200`).toBe(200);
  const body = (await response.json()) as AdminLeadListResponse | AdminLead[];

  // The endpoint historically has returned either a bare list or a
  // paginated object depending on the query. Handle both.
  if (Array.isArray(body)) {
    return body;
  }
  return body.results ?? [];
}

/**
 * Assert that the admin leads endpoint returns at least `min` leads.
 * Used by the owner morning review journey to prove that the pipeline
 * has content (the "Today's leads" card only shows content if the
 * underlying endpoint returns leads).
 */
export async function expectLeadListHasAtLeast(
  request: APIRequestContext,
  min: number,
  params: Record<string, string | number> = {},
): Promise<AdminLead[]> {
  const leads = await fetchLeadList(request, params);
  expect(
    leads.length,
    `expected at least ${min} leads from admin list; got ${leads.length}`,
  ).toBeGreaterThanOrEqual(min);
  return leads;
}

/**
 * Find a lead by its full name (as seeded). Fails loudly if the lead
 * isn't in the admin list — the journey can't proceed without the
 * seeded fixture visible.
 */
export async function findSeededLead(
  request: APIRequestContext,
  name: string,
  params: Record<string, string | number> = {},
): Promise<AdminLead> {
  const leads = await fetchLeadList(request, params);
  const match = leads.find((lead) => lead.name === name);
  const seenNames = leads.map((l) => l.name).join(", ") || "(empty list)";
  expect(
    match,
    `seeded lead "${name}" not found in admin list; got ${seenNames}`,
  ).toBeDefined();
  return match as AdminLead;
}

/**
 * Assert that a specific lead (by id) is now assigned to the named
 * advisor. Business-outcome assertion for the sales manager daily
 * startup journey — proves the assignment PATCH actually landed.
 */
export async function expectLeadAssignedTo(
  request: APIRequestContext,
  leadId: number,
  advisorName: string,
): Promise<AdminLead> {
  const leads = await fetchLeadList(request);
  const lead = leads.find((l) => l.id === leadId);
  expect(
    lead,
    `lead id=${leadId} not found in admin list`,
  ).toBeDefined();
  expect(
    lead?.assigned_to,
    `lead id=${leadId} should be assigned, got null`,
  ).not.toBeNull();
  expect(
    lead?.assigned_to?.name,
    `lead id=${leadId} assigned to wrong advisor`,
  ).toBe(advisorName);
  return lead as AdminLead;
}
