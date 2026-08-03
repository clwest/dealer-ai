# Dealer AI acceptance suite

Milestone 20 · Operational Journey Validation. Durable Playwright
acceptance suites executing real dealership workflows against the
M1–M19 shipped UI on deterministic seeded state.

## Guiding principle

This suite is an **operational acceptance contract**, not a UI
automation project. Every journey validates business outcomes through
the real application using deterministic seeded state. If a journey
passes, the conclusion is that a dealership employee can successfully
perform that operational workflow — not merely that buttons were
clicked successfully.

Assertions target business state (a lead is assigned, a payment is
posted, a pilot advances to `readiness_confirmed`), not DOM state.

## Layout

```
acceptance/
├── package.json                  # Playwright + TS devDeps
├── playwright.config.ts          # webServer, projects, artifacts
├── tsconfig.json
├── .gitignore
├── journeys/
│   └── pilot/onboarding.spec.ts  # M20.1 canonical journey
└── support/
    ├── auth/
    │   ├── personas.ts           # persona registry
    │   └── login.setup.ts        # storage-state auth setup project
    ├── seed/
    │   └── invoke.ts             # spawn `python3 manage.py <cmd>`
    └── assertions/
        └── pilot.ts              # pilot journey business-outcome
                                  # assertion helpers
```

## Running locally

Prerequisites: Node 20+, Python 3.11+, backend + frontend workspaces
installed.

First-time setup:

```bash
cd acceptance
npm install
npx playwright install chromium
```

Run the full suite:

```bash
npm test
```

Run only the pilot-critical subset (what CI runs on every PR):

```bash
npm run test:pilot-critical
```

Open the HTML report from the last run:

```bash
npm run report
```

The Playwright `webServer` config starts backend (`:8101`, dedicated
test DB) and frontend (`vite dev` locally, `vite preview` in CI) on
first invocation. `reuseExistingServer: true` locally means a second
`npm test` re-uses the running instance; `false` in CI ensures each
job starts fresh.

## Adding a new journey

1. Add a persona to `support/auth/personas.ts` if the journey requires
   a role not already covered.
2. If the journey needs starting state beyond the M18 demo + M19 pilot
   seed, add a Django management command
   `dealer_ai/management/commands/seed_journey_{name}.py`. Make it
   idempotent (`get_or_create` or equivalent) and compose existing
   service verbs — no parallel write paths.
3. Add business-outcome assertion helpers under
   `support/assertions/` if the journey exercises a domain area no
   existing helper covers.
4. Author the journey spec at `journeys/{persona}/{workflow}.spec.ts`.
   Tag `@pilot-critical` only for journeys that must run on every PR
   (defaults: pilot onboarding + owner morning review).
5. Assertions target business state, not DOM state.

## Interpreting CI failures

The GitHub Actions `acceptance` job uploads HTML report + traces +
videos on failure. Download the artifact from the job summary,
extract, and open `playwright-report/index.html` locally. Each failed
journey has a trace file (`.trace.zip`) you can open with
`npx playwright show-trace <path>`.
