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
import { fileURLToPath } from "node:url";

const IS_CI = Boolean(process.env.CI);

// Server ports. Backend uses a dedicated port so the acceptance suite
// never touches the local dev DB on :8000.
const BACKEND_PORT = 8101;
// Vite dev in both local + CI per §0.a M20.5 amendment (see webServer
// block below). Single port for both modes.
const FRONTEND_PORT = 5173;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const FRONTEND_URL = `http://127.0.0.1:${FRONTEND_PORT}`;

// ES module dirname equivalent (see §0.a M20.2 decision 1). `__dirname`
// is not defined when Playwright loads playwright.config.ts as an ES
// module; `import.meta.url` + `fileURLToPath` is the portable idiom.
const HERE = path.dirname(fileURLToPath(import.meta.url));

// Repo layout: acceptance/ is sibling to backend/ and frontend/.
const REPO_ROOT = path.resolve(HERE, "..");
const BACKEND_DIR = path.join(REPO_ROOT, "backend");
const FRONTEND_DIR = path.join(REPO_ROOT, "frontend");

// Storage-state file for each persona. Regenerated per suite run by
// the `setup` project. Adding a new persona requires (a) a new entry
// here, (b) a new setup step in login.setup.ts, and (c) a new project
// entry below that references the storage state.
export const AUTH_STORAGE = {
  platformOperator: path.join(HERE, ".auth/platform_operator.json"),
  owner: path.join(HERE, ".auth/owner.json"),
  salesManager: path.join(HERE, ".auth/sales_manager.json"),
  reconManager: path.join(HERE, ".auth/recon_manager.json"),
  bhphCollector: path.join(HERE, ".auth/bhph_collector.json"),
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
      // Pilot admin journeys run as the platform_operator persona.
      name: "platform_operator",
      testMatch: /journeys\/pilot\/.*\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        storageState: AUTH_STORAGE.platformOperator,
      },
      dependencies: ["setup"],
    },
    {
      // Owner-facing journeys (M20.2: morning review) run as the
      // owner persona.
      name: "owner",
      testMatch: /journeys\/owner\/.*\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        storageState: AUTH_STORAGE.owner,
      },
      dependencies: ["setup"],
    },
    {
      // Sales-manager journeys (M20.2: daily startup) run as the
      // sales_manager persona.
      name: "sales_manager",
      testMatch: /journeys\/sales_manager\/.*\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        storageState: AUTH_STORAGE.salesManager,
      },
      dependencies: ["setup"],
    },
    {
      // Recon-manager journeys (M20.3: recon workflow) run as the
      // recon_manager persona.
      name: "recon_manager",
      testMatch: /journeys\/recon\/.*\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        storageState: AUTH_STORAGE.reconManager,
      },
      dependencies: ["setup"],
    },
    {
      // Office / accounting journeys (M20.3: accounting workflow)
      // reuse the owner persona — dealer_owner is a valid role for
      // the M13/M14/M17 accounting endpoints per
      // IsSalesManagerOrOwnerAtActiveDealership.
      name: "office_accounting",
      testMatch: /journeys\/office\/.*\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        storageState: AUTH_STORAGE.owner,
      },
      dependencies: ["setup"],
    },
    {
      // BHPH collections journeys (M20.4) run as the bhph_collector
      // persona (which uses `sales_manager` role because the M12
      // collections endpoints gate on
      // `IsSalesManagerOrOwnerAtActiveDealership` — see §0.a M20.4
      // decision 2).
      name: "bhph_collector",
      testMatch: /journeys\/bhph\/.*\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        storageState: AUTH_STORAGE.bhphCollector,
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
      // Frontend: vite dev in both local + CI (§0.a M20.5 amendment).
      // Original §5.f Option A used `vite preview` in CI to catch
      // build-only regressions, but on the first real CI run the
      // preview-mode proxy for /api/* didn't work reliably even
      // after adding `preview.proxy` to vite.config.ts — auth
      // bootstrap hung indefinitely because the SPA couldn't reach
      // the backend. Defer preview-mode CI to a future increment;
      // vite dev in CI keeps the acceptance contract executable
      // today. Explicit `--host 127.0.0.1` bind so Playwright's
      // IPv4 readiness poll succeeds per §0.a M20.2 decision 2.
      command: `npm run dev -- --host 127.0.0.1 --port ${FRONTEND_PORT} --strictPort`,
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
