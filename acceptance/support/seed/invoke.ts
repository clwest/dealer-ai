// Milestone 20 · Increment 1 — helper to invoke a Django management
// command from a Playwright test. Used for per-journey seed delta
// commands that plant journey-specific state on top of the M18/M19
// base seed.
//
// Per §5.d Option B: journeys never reach into the ORM directly.
// They spawn `python3 manage.py <cmd>` and let the command compose
// existing service verbs.

import { spawnSync } from "node:child_process";
import path from "node:path";

const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");
const BACKEND_DIR = path.join(REPO_ROOT, "backend");

export interface SeedInvocationResult {
  stdout: string;
  stderr: string;
}

/**
 * Invoke a Django management command against the acceptance test DB.
 * Throws with the captured stdout + stderr if the command exits
 * non-zero, so a failing seed step aborts the journey visibly.
 */
export function invokeSeed(
  command: string,
  args: string[] = [],
): SeedInvocationResult {
  const result = spawnSync(
    "python3",
    ["manage.py", command, ...args],
    {
      cwd: BACKEND_DIR,
      env: { ...process.env, M20_ACCEPTANCE_DB: "1" },
      encoding: "utf-8",
    },
  );
  if (result.status !== 0) {
    throw new Error(
      `manage.py ${command} ${args.join(" ")} failed (exit=${result.status})\n` +
        `stdout:\n${result.stdout}\n\nstderr:\n${result.stderr}`,
    );
  }
  return { stdout: result.stdout, stderr: result.stderr };
}
