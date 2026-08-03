// Milestone 20 · Increment 1 — business-outcome assertion helpers for
// the pilot onboarding journey.
//
// Per M20 guiding principle: assertions target business state (the
// pilot's checklist advanced, is_ready=True at completion), not DOM
// state. These helpers wrap the M19.3 admin API surface so a journey
// can confirm outcomes without duplicating fetcher logic in the spec.

import { APIRequestContext, expect } from "@playwright/test";

export interface PilotChecklistStep {
  step_slug: string;
  completed_at: string | null;
  completed_by_username: string | null;
  notes: string;
}

export interface PilotChecklist {
  id: number;
  dealership_id: number;
  is_ready: boolean;
  steps: PilotChecklistStep[];
}

export interface PilotDealership {
  id: number;
  slug: string;
  name: string;
  is_pilot: boolean;
  is_demo: boolean;
  outbound_enabled: boolean;
  terminated_at: string | null;
  termination_reason: string;
  created_at: string;
}

export interface PilotWithChecklist {
  dealership: PilotDealership;
  checklist: PilotChecklist | null;
}

async function fetchPilotList(
  request: APIRequestContext,
): Promise<PilotWithChecklist[]> {
  const response = await request.get("/api/dealer-ai/admin/pilots/");
  expect(
    response.status(),
    "GET /admin/pilots/ returned non-200",
  ).toBe(200);
  const body = await response.json();
  return body.pilots as PilotWithChecklist[];
}

/**
 * Assert that a pilot with the given slug exists in the active-pilot
 * list. Returns the matched pilot for further assertions.
 */
export async function expectPilotExists(
  request: APIRequestContext,
  slug: string,
): Promise<PilotWithChecklist> {
  const pilots = await fetchPilotList(request);
  const match = pilots.find((p) => p.dealership.slug === slug);
  expect(
    match,
    `expected pilot with slug=${slug} in active list; got ${pilots
      .map((p) => p.dealership.slug)
      .join(", ")}`,
  ).toBeDefined();
  return match as PilotWithChecklist;
}

/**
 * Assert that a specific checklist step is completed on the pilot.
 */
export async function expectStepCompleted(
  request: APIRequestContext,
  slug: string,
  stepSlug: string,
): Promise<void> {
  const pilot = await expectPilotExists(request, slug);
  const step = pilot.checklist?.steps.find((s) => s.step_slug === stepSlug);
  expect(
    step,
    `expected step ${stepSlug} on pilot ${slug}; got ${
      pilot.checklist?.steps.map((s) => s.step_slug).join(", ") ?? "no checklist"
    }`,
  ).toBeDefined();
  expect(
    step?.completed_at,
    `expected step ${stepSlug} on pilot ${slug} to be completed`,
  ).not.toBeNull();
}

/**
 * Assert that the pilot's checklist is fully complete
 * (is_ready=True + readiness_confirmed step marked done).
 */
export async function expectPilotReady(
  request: APIRequestContext,
  slug: string,
): Promise<void> {
  const pilot = await expectPilotExists(request, slug);
  expect(
    pilot.checklist?.is_ready,
    `expected pilot ${slug} to have is_ready=true`,
  ).toBe(true);
  const readinessStep = pilot.checklist?.steps.find(
    (s) => s.step_slug === "readiness_confirmed",
  );
  expect(
    readinessStep?.completed_at,
    `expected readiness_confirmed step on pilot ${slug} to be completed`,
  ).not.toBeNull();
}

/**
 * Return the seven canonical M19 checklist step slugs in the order the
 * operator must advance them.
 */
export const PILOT_ONBOARDING_STEP_ORDER: readonly string[] = [
  "dealership_created",
  "profile_configured",
  "owner_user_added",
  "staff_users_added",
  "inventory_imported",
  "capabilities_enabled",
  "readiness_confirmed",
] as const;
