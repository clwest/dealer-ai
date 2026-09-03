// SESSION_233.1 — engineer the "fresh DB every run" invariant instead
// of leaving it as a warning in the README. Removes
// backend/db.acceptance.sqlite3 and re-migrates so every ``npm test``
// invocation starts from a known-empty state. The setup project's
// journey seeds then plant fixtures on that clean state.
//
// Wired via ``pretest`` in acceptance/package.json so it runs
// automatically before ``playwright test``. Idempotent — the delete
// step is a no-op if the file was already gone.

import { spawnSync } from "node:child_process";
import { existsSync, unlinkSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, "..");
const BACKEND_DIR = path.join(REPO_ROOT, "backend");
const DB_FILE = path.join(BACKEND_DIR, "db.acceptance.sqlite3");

function log(msg) {
  process.stdout.write(`[reset-acceptance-db] ${msg}\n`);
}

if (existsSync(DB_FILE)) {
  try {
    unlinkSync(DB_FILE);
    log(`removed ${path.relative(REPO_ROOT, DB_FILE)}`);
  } catch (err) {
    process.stderr.write(
      `[reset-acceptance-db] failed to remove DB file: ${err}\n`,
    );
    process.exit(1);
  }
} else {
  log("no db.acceptance.sqlite3 to remove; migrating fresh");
}

log("running migrate --run-syncdb");
const result = spawnSync(
  "python3",
  ["manage.py", "migrate", "--run-syncdb", "--noinput"],
  {
    cwd: BACKEND_DIR,
    env: {
      ...process.env,
      M20_ACCEPTANCE_DB: "1",
      DJANGO_SETTINGS_MODULE: "dealer_kit.settings",
    },
    stdio: "inherit",
  },
);
if (result.status !== 0) {
  process.stderr.write(
    `[reset-acceptance-db] migrate failed with exit=${result.status}\n`,
  );
  process.exit(result.status ?? 1);
}
log("done");
