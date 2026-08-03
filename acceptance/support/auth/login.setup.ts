// Milestone 20 · Increment 1 — auth setup project. Runs once per
// suite invocation. For each persona in the M20.1 registry, logs in
// via the real UI (fills the LoginPage form + submits) and writes the
// resulting storage state to `.auth/{persona}.json` so subsequent
// journey projects load into an authenticated session.
//
// Per §5.e Option B: login happens via the real UI, not a test-only
// endpoint. The setup project also runs the M20.1 seed delta command
// so the personas exist in the acceptance DB before the login attempt.

import { test as setup, expect } from "@playwright/test";
import { spawnSync } from "node:child_process";
import path from "node:path";

import { PERSONAS } from "./personas";
import { AUTH_STORAGE } from "../../playwright.config";

const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");
const BACKEND_DIR = path.join(REPO_ROOT, "backend");

setup("seed pilot onboarding baseline + provision personas", async () => {
  // Run the M20.1 seed delta. Idempotent — safe to invoke on every
  // suite run. Provisions the platform_operator user + the qualified
  // PilotProspect the canonical journey converts.
  const result = spawnSync(
    "python3",
    ["manage.py", "seed_journey_pilot_onboarding"],
    {
      cwd: BACKEND_DIR,
      env: { ...process.env, M20_ACCEPTANCE_DB: "1" },
      encoding: "utf-8",
    },
  );
  if (result.status !== 0) {
    throw new Error(
      `seed_journey_pilot_onboarding failed (exit=${result.status})\n` +
        `stdout:\n${result.stdout}\n\nstderr:\n${result.stderr}`,
    );
  }
});

setup("authenticate as platform_operator", async ({ page }) => {
  const persona = PERSONAS.platform_operator;

  await page.goto("/login");
  // Wait for the login form to be interactive. The page uses stable
  // id-based selectors (`#login-username`, `#login-password`).
  await page.locator("#login-username").waitFor({ state: "visible" });
  await page.locator("#login-username").fill(persona.username);
  await page.locator("#login-password").fill(persona.password);
  await page.getByRole("button", { name: /sign in/i }).click();

  // Successful login redirects; wait for the post-login destination.
  // Chrome may land on /dealer-ai-overview by default; navigate
  // explicitly to persona.postLoginPath and assert we're not on /login.
  await page.waitForURL((url) => !url.pathname.endsWith("/login"), {
    timeout: 15_000,
  });

  // Belt-and-suspenders: confirm auth cookie was set by hitting /auth/me/.
  const meResponse = await page.request.get("/api/dealer-ai/auth/me/");
  expect(meResponse.status()).toBe(200);
  const me = await meResponse.json();
  expect(me.user?.username).toBe(persona.username);

  await page.context().storageState({
    path: AUTH_STORAGE.platformOperator,
  });
});
