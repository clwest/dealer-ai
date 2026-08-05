// Milestone 20 · Increment 1 (extended at M20.2) — auth setup
// project. Runs once per suite invocation. For each persona in the
// registry: runs the persona's seed delta command (idempotent), logs
// the persona in via the real UI, and writes the resulting storage
// state to `.auth/{persona}.json`.
//
// Per §5.e Option B: login happens via the real UI, not a test-only
// endpoint. Per §5.d Option B: seeds compose existing service verbs
// via management commands, not parallel test-only write paths.

import { test as setup, expect } from "@playwright/test";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { PERSONAS, type Persona } from "./personas";
import { AUTH_STORAGE } from "../../playwright.config";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, "..", "..", "..");
const BACKEND_DIR = path.join(REPO_ROOT, "backend");

// Seed delta commands run before any persona logs in. Each command is
// idempotent and provisions its persona's user + role membership +
// the journey-specific state (leads, prospects, etc.) that persona's
// journeys need.
const SEED_COMMANDS = [
  "seed_journey_pilot_onboarding",
  "seed_journey_owner_morning_review",
  "seed_journey_sales_manager_daily_startup",
  "seed_journey_recon_workflow",
  "seed_journey_office_accounting_workflow",
  "seed_journey_bhph_collections_workflow",
  // Milestone 24 · Increment 1 (SESSION_181) — Sales Operational Entry
  // journeys (walk-in / phone / referral / webhook). The seed
  // provisions its own operator + advisor + a referring-customer
  // lead used by the M24.3 referral picker. The M24.1-4 journeys
  // reuse the existing sales_manager persona (acceptance-sales-
  // manager) for auth; the M20 seed provisions Acceptance Advisor,
  // which the M24 journeys use as the assignment target.
  "seed_journey_sales_operational_entry",
  // Milestone 32 · Increment 3 (SESSION_209) — F&I intake receipt
  // journey. Provisions the f_and_i_manager persona + Intake Iris
  // fixture (lead + vehicle + approved+handed-off writeup + paired
  // CA) fully independent of any M32.2 sales-side fixture per M32
  // §5.c R11 independence guarantee.
  "seed_journey_fandi_intake_receipt",
  // Milestone 33 · Increment 2 (SESSION_212) — F&I intake activation
  // journey. Provisions the Structure Sam fixture (lead + vehicle +
  // approved+handed-off writeup + paired CA — NO DealStructure) so
  // the M33.2 journey creates the first structure via the M33.2 UI.
  // Fully independent of the M32.3 Intake Iris fixture per M33 §5.c
  // R7 independence guarantee — distinct rows, no shared state, test
  // order irrelevant, parallelism-safe. Reuses the M32.3
  // f_and_i_manager persona; no new persona provisioning.
  "seed_journey_fandi_intake_activation",
] as const;

function runManagementCommand(command: string): void {
  const result = spawnSync("python3", ["manage.py", command], {
    cwd: BACKEND_DIR,
    env: { ...process.env, M20_ACCEPTANCE_DB: "1" },
    encoding: "utf-8",
  });
  if (result.status !== 0) {
    throw new Error(
      `manage.py ${command} failed (exit=${result.status})\n` +
        `stdout:\n${result.stdout}\n\nstderr:\n${result.stderr}`,
    );
  }
}

setup("seed acceptance baseline (all personas + journey fixtures)", async () => {
  for (const command of SEED_COMMANDS) {
    runManagementCommand(command);
  }
});

async function loginPersona(
  page: import("@playwright/test").Page,
  persona: Persona,
  storagePath: string,
): Promise<void> {
  await page.goto("/login");
  await page.locator("#login-username").waitFor({ state: "visible" });
  await page.locator("#login-username").fill(persona.username);
  await page.locator("#login-password").fill(persona.password);
  await page.getByRole("button", { name: /sign in/i }).click();

  // Successful login redirects; wait for the post-login destination.
  await page.waitForURL((url) => !url.pathname.endsWith("/login"), {
    timeout: 15_000,
  });

  // Belt-and-suspenders: confirm the auth cookie is set + identifies
  // the correct user. Drift between seed and persona surfaces here
  // rather than deep inside a journey.
  const meResponse = await page.request.get("/api/dealer-ai/auth/me/");
  expect(meResponse.status()).toBe(200);
  const me = await meResponse.json();
  expect(
    me.user?.username,
    `authenticated as wrong user for persona ${persona.name}`,
  ).toBe(persona.username);

  await page.context().storageState({ path: storagePath });
}

setup("authenticate as platform_operator", async ({ page }) => {
  await loginPersona(
    page,
    PERSONAS.platform_operator,
    AUTH_STORAGE.platformOperator,
  );
});

setup("authenticate as owner", async ({ page }) => {
  await loginPersona(page, PERSONAS.owner, AUTH_STORAGE.owner);
});

setup("authenticate as sales_manager", async ({ page }) => {
  await loginPersona(page, PERSONAS.sales_manager, AUTH_STORAGE.salesManager);
});

setup("authenticate as recon_manager", async ({ page }) => {
  await loginPersona(page, PERSONAS.recon_manager, AUTH_STORAGE.reconManager);
});

setup("authenticate as bhph_collector", async ({ page }) => {
  await loginPersona(page, PERSONAS.bhph_collector, AUTH_STORAGE.bhphCollector);
});

setup("authenticate as f_and_i_manager", async ({ page }) => {
  await loginPersona(
    page,
    PERSONAS.f_and_i_manager,
    AUTH_STORAGE.fAndIManager,
  );
});
