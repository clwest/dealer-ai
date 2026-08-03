// Milestone 20 · Increment 1 — Playwright config for the operational
// acceptance contract.
//
// Guiding principle (M20 planning §guiding-principle): the suite is an
// operational acceptance contract, not a UI automation project. Every
// journey validates business outcomes through the real application
// using deterministic seeded state. If a journey passes, the
// conclusion is that a dealership employee can successfully perform
// that operational workflow — not merely that buttons were clicked.
//
// Server lifecycle (§5.f Option A): Playwright `webServer` launches
// both backend (dedicated test DB on :8101) and frontend (vite preview
// in CI, vite dev locally). `reuseExistingServer: true` locally;
// `false` in CI.
//
// Auth strategy (§5.e Option B): the `setup` project logs each
// persona in via the real UI and saves storage state under
// `.auth/{persona}.json`. Persona projects reuse the saved state.

import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const IS_CI = Boolean(process.env.CI);

// Server ports. Backend uses a dedicated port so the acceptance suite
// never touches the local dev DB on :8000.
const BACKEND_PORT = 8101;
const FRONTEND_PORT = IS_CI ? 4173 : 5173; // vite preview vs vite dev
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const FRONTEND_URL = `http://127.0.0.1:${FRONTEND_PORT}`;

// Repo layout: acceptance/ is sibling to backend/ and frontend/.
const REPO_ROOT = path.resolve(__dirname, "..");
const BACKEND_DIR = path.join(REPO_ROOT, "backend");
const FRONTEND_DIR = path.join(REPO_ROOT, "frontend");

// Storage-state file for each persona. Regenerated per suite run by
// the `setup` project.
export const AUTH_STORAGE = {
  platformOperator: path.join(__dirname, ".auth/platform_operator.json"),
} as const;

export default defineConfig({
  testDir: ".",
  fullyParallel: false, // journeys mutate shared DB state; serialize for now
  forbidOnly: IS_CI,
  retries: IS_CI ? 1 : 0,
  workers: 1,
  reporter: IS_CI
    ? [
        ["html", { open: "never" }],
        ["list"],
        ["github"],
      ]
    : [
        ["html", { open: "never" }],
        ["list"],
      ],
  use: {
    baseURL: FRONTEND_URL,
    trace: "on-first-retry",
    video: "retain-on-failure",
    screenshot: "only-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "setup",
      testMatch: /support\/auth\/.*\.setup\.ts/,
    },
    {
      name: "platform_operator",
      testMatch: /journeys\/(pilot|owner|sales_manager|recon|office|bhph)\/.*\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        storageState: AUTH_STORAGE.platformOperator,
      },
      dependencies: ["setup"],
    },
  ],
  webServer: [
    {
      // Backend: dedicated test DB on :8101. `--noreload` avoids the
      // stat-watcher process (extra pid Playwright would have to reap).
      // The `M20_ACCEPTANCE_DB` env flag opts settings.py into the
      // isolated test DB path per M20.1 §0.a decision.
      command: `python3 manage.py migrate --run-syncdb --noinput && python3 manage.py runserver 127.0.0.1:${BACKEND_PORT} --noreload`,
      cwd: BACKEND_DIR,
      url: `${BACKEND_URL}/api/dealer-ai/auth/me/`,
      reuseExistingServer: !IS_CI,
      timeout: 120_000,
      env: {
        M20_ACCEPTANCE_DB: "1",
        DJANGO_SETTINGS_MODULE: "dealer_kit.settings",
      },
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      // Frontend: vite preview against a production build in CI,
      // vite dev locally for faster iteration.
      command: IS_CI ? `npm run build && npm run preview -- --port ${FRONTEND_PORT} --strictPort` : `npm run dev -- --port ${FRONTEND_PORT} --strictPort`,
      cwd: FRONTEND_DIR,
      url: FRONTEND_URL,
      reuseExistingServer: !IS_CI,
      timeout: 240_000,
      env: {
        VITE_API_PROXY_TARGET: BACKEND_URL,
      },
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});

// Re-export for journey code that needs to invoke seed commands or
// reference server URLs.
export { BACKEND_URL, FRONTEND_URL, BACKEND_DIR, BACKEND_PORT };
