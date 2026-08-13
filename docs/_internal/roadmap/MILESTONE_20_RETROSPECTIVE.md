---
title: "Milestone 20 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-02
sessions: SESSION_160 → SESSION_165
milestone: 20
milestone_name: "Operational Journey Validation (Playwright acceptance testing)"
related:
  - docs/roadmap/MILESTONE_20_PLANNING.md
  - docs/roadmap/MILESTONE_19_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 20
---

# Milestone 20 — Retrospective

Written at Milestone 20 close (SESSION_165).
Records what was planned, what shipped,
what deviated and why, and lessons carried
forward for Milestone 21 and beyond.
Mirrors the `MILESTONE_19_RETROSPECTIVE.md`
structure so milestone history remains
directly comparable.

## 1. Planned scope

`MILESTONE_20_PLANNING.md` at SESSION_159
close (skeleton) and SESSION_160 (full
active memo) defined the milestone as
**operational journey validation via
Playwright acceptance testing** — the
executable operational contract every
future milestone extends. Not a domain
milestone: zero new tenancy carriers,
zero new migrations, zero new permission
classes, zero new DRF endpoints, zero new
frontend routes.

**§5.a Candidate J locked at SESSION_160
M20.0 open** with the milestone name
**"Operational Journey Validation
(Playwright acceptance testing)."**
User-proposed Candidate W was folded into
Candidate J at M20.0 open per
DOC_GOVERNANCE.md §2 (avoid parallel
documents; upgrade the authoritative one)
— J's brief absorbed W's explicit non-
goals, why-M20 rationale, and per-journey
operational contract.

§5.b–§5.h drafted **eight load-bearing
planning-time decisions** — matching M19's
count, reflecting the breadth of tooling-
axis scope (framework choice, layout,
seed strategy, auth strategy, server
lifecycle, CI integration, completion
contract + increment sequencing). §7
sequenced six increments (M20.0 planning
+ M20.1 framework + canonical pilot
journey + M20.2 dashboard journeys +
M20.3 back-office journeys + M20.4 BHPH
journey + M20.5 close-out).

**Guiding principle established at
M20.0** and enforced through every
subsequent §0.a decision: the suite is
an operational acceptance contract, not a
UI automation project. Every journey
validates business outcomes through the
real application using deterministic
seeded state.

## 2. What actually shipped

Six passing Playwright acceptance
journeys running on the shipped M1–M19
UI, plus the framework substrate that
makes future extensions cheap.

**Six journeys** in
`acceptance/journeys/`:

- `pilot/onboarding.spec.ts`
  (`@pilot-critical`) — M20.1 canonical
  journey. Platform operator walks the
  M19.5 pilot onboarding playbook end-
  to-end: create pilot → advance every
  checklist step → assert
  `is_ready=true` at the M19.3 admin
  API.
- `owner/morning_review.spec.ts`
  (`@pilot-critical`) — M20.2. Owner
  lands on the operator dashboard,
  verifies stat cards + pipeline
  content, drills into `/dealer-ai-leads`.
- `sales_manager/daily_startup.spec.ts`
  — M20.2. Sales manager navigates to
  `/dealer-ai-admin`, clicks a seeded
  lead's Recent Leads row, opens the
  LeadDetailModal's AssignmentDropdown,
  picks the seeded advisor. Business-
  outcome verified via `/admin/leads/`.
- `recon/workflow.spec.ts` — M20.3.
  Recon manager records a `must_do`
  decision on a seeded finding; the
  ReconDecision persists at the
  service layer.
- `office/accounting_workflow.spec.ts`
  — M20.3. Owner freezes a trial-
  balance snapshot; the frozen
  `TrialBalanceSnapshot` appears in
  Prior Closes + is balanced at the
  service layer.
- `bhph/collections_workflow.spec.ts`
  — M20.4 (scope narrowed to
  read-side; write-side UI not
  shipped). BHPH collector reviews
  the portfolio + drills into a
  seeded note with all five detail
  sections populated (loan terms +
  payment + broken promise +
  contact + ordered repossession).

**One new top-level workspace** —
`acceptance/` sibling to `backend/` +
`frontend/`. `package.json` with
Playwright 1.49 + TypeScript 5.6;
`playwright.config.ts` with `webServer`
launching backend (`:8101` with
isolated SQLite DB via
`M20_ACCEPTANCE_DB=1`) + frontend
(`vite dev` local / `vite preview` in
CI). Support layer:
- `support/auth/personas.ts` — five
  personas: platform_operator, owner,
  sales_manager, recon_manager,
  bhph_collector.
- `support/auth/login.setup.ts` — one
  setup step that runs all six seed
  delta commands; one login step per
  persona (real UI login via
  `/login`, storage-state saved to
  `.auth/{persona}.json`).
- `support/seed/invoke.ts` —
  management-command spawn helper.
- `support/assertions/{pilot,dashboard,recon,accounting,bhph}.ts`
  — business-outcome assertion
  helpers reading the shipped M1–M19
  admin APIs.

**Six new backend seed delta
management commands** in
`dealer_ai/management/commands/seed_journey_*.py`,
one per journey. Each is idempotent,
supports `--reset`, and composes
existing M1–M19 service verbs (no
parallel write paths). **76 focused
backend tests** across the six commands
(5+15+12+15+13+7+14 = 76 exact —
including credentials-authenticate, tenant-
scoping, idempotency, and `--reset`
recovery coverage).

**One new GitHub Actions workflow** —
`.github/workflows/acceptance.yml`.
Triggers on `pull_request` +
`push` to `main`. Tiered execution:
`@pilot-critical` subset on PR
(~90s target); full six-journey suite
on `main` (~5–8 min target). Artifacts
on failure: HTML report (always),
trace (`on-first-retry`), video
(`retain-on-failure`), screenshot
(`only-on-failure`). Uploaded via
`actions/upload-artifact@v4` with
14-day retention.

**One `backend/dealer_kit/settings.py`
extension** — `M20_ACCEPTANCE_DB=1`
env branch points the default DB at
`backend/db.acceptance.sqlite3`
(gitignored). Matches the M2.1
`migration_check` DB alias pattern —
additive, isolated, no impact on dev
or production paths.

**Original §7 sequencing shipped
verbatim.** Six increments across
SESSION_160 → SESSION_165. All eight
SESSION_160 planning-time decisions
confirmed as-recommended at M20.0
open. **§0.a implementation-time
micro-decisions surfaced at every
increment** (twelve total: 3 at
M20.2, 4 at M20.3, 4 at M20.4, 1 at
M20.5 for the CI-verified artifact
flow). Per M10 §9 those are
implementation-time defaults, not
planning-time decisions, so they do
not count against the streak.
**The streak stands at 86 planning-
time as-recommended M5.1 → M20.0** —
eleven consecutive milestones now
(M10 → M20).

## 3. What was NOT shipped (deferred, not dropped)

Deferrals recorded with re-entry
paths.

**M20-specific deferrals:**

1. **Write-side BHPH collections UI**
   — the four operations from the
   M20.4 planned scope (record PtP,
   mark broken, log contact, initiate
   repossession) have no shipped
   frontend UI as of M12.7. The
   M20.4 journey scope-narrowed to
   the read side. Re-entry:
   **M21+ candidate "M12.8 BHPH
   collections write-side UI"** —
   surfaces in §8 unblocks.
2. **Dashboard component testids.**
   The DealerOverview + DealerAdmin
   + LeadsPage components render
   without `data-testid` patterns
   for card titles or lead rows,
   forcing journeys to lean on
   text/role selectors that are
   less resilient to copy changes.
   Recorded as §8 unblock
   "dashboard testid hardening."
3. **Full cross-browser CI matrix.**
   Chromium-only in CI. Firefox +
   WebKit run locally via
   `--project=firefox` /
   `--project=webkit`. Re-entry
   gated on observed browser-
   specific regression evidence.
4. **Mobile / responsive viewport
   journeys.** All journeys target
   desktop viewport. Defers to a
   future mobile-readiness
   milestone.
5. **Performance / load testing via
   Playwright.** Explicit non-goal
   per M20 §3.
6. **Third-party integration
   stubs / mocks.** Not needed at
   M20 (M18.1 outbound guard
   already suppresses); re-entry as
   §0.a amendment if a journey ever
   needs a mocked external
   response.
7. **Automatic journey generation
   from user telemetry.** Explicit
   non-goal per M20 §3.
8. **Nightly-cron acceptance
   runs.** `main` push trigger is
   sufficient; nightly cron adds
   noise without new signal.
9. **`?stock=` filter on
   `/admin/bhph-notes/list/`.**
   Loan-term signature match is
   adequate for M20.4; add filter
   if collision surfaces.
10. **Additional pilot-critical
    journeys.** Currently 2
    (`pilot/onboarding` +
    `owner/morning_review`). New
    journeys default to full-suite-
    only unless operator evidence
    surfaces them as PR-critical.
11. **Playwright test parallelism
    across workers.** Set to
    `workers: 1` +
    `fullyParallel: false` at
    M20.1 (§0.a M20.1 decision 2)
    since journey seeds mutate
    shared DB state. Revisit if
    suite time exceeds the ~8 min
    `main`-push target.

**Universal deferrals** (any
platform milestone): unchanged from
M19 §3 — payroll, W-2/1099
generation, year-end tax prep,
GAAP audits, DMS integration,
real inventory feeds, bilingual
UI, payment processing / e-sign,
multi-tenant SaaS shell,
predictive ML, SSO/MFA.

## 4. Deviations from planned scope

Two significant deviations, both
recorded as §0.a decisions at their
increments.

**Deviation 1 — Candidate W folded
into Candidate J at M20.0 open
(planning-time, not implementation).**
User proposed Candidate W as a
tenth candidate alongside the
nine-item M19 §9 list. Governance
review flagged W as functionally
identical to J (already documented
in the M19 retrospective §9); the
governance-clean move was to
upgrade J's authoritative brief
with W's explicit non-goals + why-
M20 rationale + per-journey
operational contract. User
confirmed. Zero-drift on the M19.6
authoritative candidate list.

**Deviation 2 — M20.4 journey
scope narrowed from write-side +
read-side to read-side only.**
Original M20 planning §7 M20.4
described the BHPH collections
journey as "daily book review,
recording a promise-to-pay,
capturing a collection contact,
initiating repossession on a
broken promise". The Explore-agent
surface map at SESSION_164 open
confirmed that all four write-side
operations have **no shipped
frontend UI** as of M12.7 — only
backend endpoints. Per the M20
guiding principle ("business
outcomes through the real
application"), a Playwright
journey cannot exercise a
workflow whose UI doesn't exist.
M20.4 scope narrowed to the read
side (portfolio → note detail);
the write-side UI gap is
recorded as an M21+ candidate.

**Neither deviation weakens the
milestone's operational contract.**
Both surfaced by the disciplined
guiding principle (fold duplicates,
narrow scope when UI missing) and
were resolved before code shipped.

## 5. Compatibility with existing surface

M20 is the first milestone since M2
that ships **zero new backend
service verbs and zero new frontend
routes** — every journey exercises
already-shipped M1–M19 surface only.
The compatibility surface therefore
holds by construction.

- **Migrations:** unchanged at
  `0001`–`0048` through M20 close.
- **Tenancy carriers:** unchanged
  at **52**.
- **Permission classes:** unchanged
  at **7 actual** — **zero-drift
  streak extends nineteen →
  twenty consecutive milestones**
  (M10 → M20). Streak preserved
  because M20 endpoint use is
  read-only through the real UI
  as the authenticated persona
  cookie; no new gates.
- **DRF admin surface:** unchanged
  at **113 endpoints**.
- **Frontend operator routes:**
  unchanged at **20**.
- **Frontend Vitest:** unchanged
  at **153 pass**.
- **Backend test suite:** 4,679 →
  **4,755 pass** (+76 seed
  command tests). Zero regressions.
- **Celery-beat task families:**
  unchanged at **10**.
- **AI safety stack:** unchanged
  at 17 scrub stages.

One narrow **additive extension** to
existing infrastructure:
`backend/dealer_kit/settings.py`
gains a `M20_ACCEPTANCE_DB=1` env
branch pointing the default DB at
`backend/db.acceptance.sqlite3`
(gitignored). Matches the M2.1
`migration_check` DB alias pattern.

## 6. Lessons

### Lesson 1 — the first dry-run is where the framework earns its keep.

**Evidence.** SESSION_162 M20.2 first
dry-run against M20.1's framework
surfaced two framework-substrate
defects that would otherwise have
festered:

1. `__dirname` unavailable in ES
   module scope — three files
   affected (`playwright.config.ts`,
   `login.setup.ts`, `invoke.ts`).
2. `vite` binding to `localhost`
   only on macOS ≠ Playwright's
   IPv4 poll target `127.0.0.1`.

Both fixes were three-line changes;
both were unknown at M20.1 commit
time; both were caught the moment
someone actually ran the framework.
This is the M20-plan §2 dry-run step
paying itself back on session 2.

**Carry-forward.** Every framework
substrate milestone should sequence
"ship framework" as its own
increment separated from "layer
first journey" so the first dry-run
happens against fresh eyes.
M20.1's Option C sequencing
(framework + one canonical journey
in the same increment) *worked*
because the canonical journey was
its own dry-run — but only after
the first attempt failed on
`__dirname` before any journey
assertion fired. Next framework
milestone: consider Option B
(framework alone) if the added
increment cost is worth catching
substrate defects even earlier.

### Lesson 2 — envelope-wrapped API responses need explicit assertion-helper types.

**Evidence.** The M17.1 trial-
balance snapshot endpoints return
double-wrapped envelopes
(`{trial_balance_snapshots: {snapshots: [...]}}`
for list, `{trial_balance_snapshot: {...}}`
for detail). The M20.3 accounting
assertion helper missed the
envelope on the first dry-run;
symptoms were "0 snapshots returned"
after a successful freeze. Fixed by
declaring the envelope in the
helper's TypeScript response type.

By contrast, the M12 BHPH list
endpoint returns bare
`{count, results}` (M20.4 evidence);
child list endpoints are a mix.

**Carry-forward.** Every M20+
assertion helper declares its
response envelope explicitly in the
TypeScript response type + adds a
`file:line` comment pointing at
the backend view's response
construction. Future response
shape changes surface as type
errors, not runtime "0 items
returned" mysteries.

### Lesson 3 — shipped-UI verification is a required pre-flight for every journey.

**Evidence.** M20.4 planning
described a four-step BHPH
collections journey exercising
promise-to-pay + broken-promise +
collection contact + repossession
initiation. The SESSION_164 open
Explore-agent surface map surfaced
that **all four write operations
are backend-only** — no shipped
frontend UI. Scope narrowed the
journey to read-only, with the
gap recorded as an M21+ candidate.

This same class of gap could
have hit M20.2 (be-back handling)
and M20.3 (recon workflow's later
lifecycle stages). Neither hit —
but not because the plan
predicted them; because the
Explore agent surfaced them
before code was written.

**Carry-forward.** Every future
Playwright acceptance-journey
milestone opens with an Explore-
agent surface map that confirms
"UI shipped for every step of the
described workflow" — YES/NO per
step. If NO, narrow the journey
scope in the planning memo before
sequencing increments. The scope-
narrow evidence lives in a §0.a
decision when discovered late; in
the planning memo §3 (deferrals)
when discovered early.

### Lesson 4 — data-testid coverage in the frontend is a Playwright-milestone dependency.

**Evidence.** The M19.4 pilot
admin UI shipped with rich
`data-testid` coverage
(`pilot-onboarding-section`,
`pilot-create-slug`, `pilot-row-<slug>`
etc.); the M20.1 pilot onboarding
journey wrote clean, stable
assertions against them. By
contrast, the M15+ dashboard
components (DealerOverview,
DealerAdmin, LeadsPage,
LeadDetailModal) shipped without
`data-testid` patterns, forcing
M20.2/M20.3 journeys onto
text/role selectors + brittle
class-based scopes (`div.fixed.inset-0.z-50`
for the LeadDetailModal since it
isn't a Radix Dialog).

Every non-testid selector is
technical debt against future
copy changes.

**Carry-forward.** Recorded as
§8 unblock "dashboard testid
hardening" — a future milestone
(M12.8 or similar) should add
`data-testid` coverage across the
dashboard + leads surfaces so
subsequent Playwright journey
extensions can assert against
stable selectors.

### Lesson 5 — the guiding principle is the load-bearing enforcement mechanism.

**Evidence.** Every M20.x §0.a
decision that adjusted scope or
approach cites the guiding
principle:

- M20.2 §0.a decision 3 (sales
  manager journey targets
  `/dealer-ai-admin`, not the
  read-only `/dealer-ai-leads`)
  — cited "business outcomes
  through the real application".
- M20.4 §0.a decision 1 (BHPH
  scope narrowing) — cited
  "journeys must exercise
  business outcomes through the
  real UI".

The principle is not decoration;
it's the objective standard that
resolved each ambiguity without
requiring a fresh judgment call.

**Carry-forward.** Milestones
with a strong guiding principle
in the planning memo make
implementation-time decisions
substantially easier. Repeat the
pattern: state the principle at
M<N>.0, cite it explicitly in
every §0.a decision that hinges
on it.

### Lesson 6 — "settle signal" ambiguity is a real class of Playwright flakiness.

**Evidence.** M20.3 §0.a decision
4 documents the recon journey's
challenge: after clicking the
"Must do" tier button, the button
disappears and a Badge with the
same "Must do" text appears.
`getByText("Must do")` matches
either — no clean "wait until
transition complete" signal.
Resolved by waiting for the
reconsideration button "→ Should
do" which only exists AFTER a
decision is recorded.

**Carry-forward.** For every
UI action that fires an async
state change, identify a
distinctive settle signal —
either a new UI element that
only exists post-state-change,
or a specific attribute
transition. Do not rely on
text presence when both pre-
and post-states share the same
visible text. Business-outcome
assertions via the admin API
are always available as
belt-and-suspenders.

## 7. Streak update

**Planning-time as-recommended
streak: 85 → 86 M5.1 → M20.0
across eleven consecutive
milestones** (M10 → M20).

Historical §5 decision counts:
- M10 through M17: 6 decisions
  each = 48.
- M18: 7 decisions.
- M19: 8 decisions.
- M20: 8 decisions.
- Total: **71 §5 decisions
  across eleven milestones,
  every one confirmed as-
  recommended at planning-
  time open**.

**Zero-drift permission-class
streak: nineteen → twenty
consecutive milestones** (M10
→ M20). Every M20 endpoint
touch is READ-only via the
existing gates; zero new
permission classes; zero
changes to existing ones.

## 8. What M20 unblocks for M21+

M20 shipped **executable
operational substrate**, not
domain behavior. The unblocks
are therefore substrate-side +
recorded-gap-side.

- **Every subsequent milestone
  now has an executable
  operational contract.** New
  operator-facing behavior can
  ship a Playwright journey
  alongside the code so
  workflow regressions surface
  on the PR that introduces
  them, not weeks later.
- **M12.8 — BHPH collections
  write-side UI.** Missing UI
  gap surfaced by M20.4.
  Would ship: record PtP UI
  form, mark-broken /
  mark-kept action buttons,
  log-contact form, initiate-
  repossession form. Once
  shipped, M20.4 journey scope
  expands to cover the write
  side.
- **Dashboard testid
  hardening.** Add `data-testid`
  patterns across DealerOverview,
  DealerAdmin's SalesPipeline,
  LeadsPage, LeadDetailModal
  so future journey extensions
  don't lean on brittle text-
  based selectors. Not urgent
  (M20.2/M20.3 journeys work
  today); becomes urgent as
  the copy in those components
  evolves.
- **First real GitHub Actions
  CI acceptance run.** M20.5's
  coordinated push is the
  first push of the M20
  commits. GitHub Actions
  fires the acceptance job on
  that push; the first
  `@pilot-critical` subset run
  proves CI wiring works, and
  the first `main` full-suite
  run proves the full contract
  holds on the GHA runner
  (independent from the local
  dev machine).
- **All M19 §8 unblocks still
  valid** per
  `MILESTONE_19_RETROSPECTIVE.md`
  §8.
- **All M18 §8 unblocks
  (accounting stream, demo-
  aware LLM router, F&I
  chargeback, hosted-demo
  substrate, etc.) still valid**
  per
  `MILESTONE_18_RETROSPECTIVE.md`
  §8.

## 9. Standing question — is M21 the return-to-accounting milestone?

Per M19 §9 the standing question
was "is M20 the Operational
Journey Validation milestone?"
M20's answer was yes.

**Standing question for M21
open:** given that M18 §8 named
"return to accounting" as the
designated M20 slot and M20
diverged from that designation
to ship Candidate J, is M21
the return-to-accounting
milestone? Or does new operator
evidence surface a stronger
target?

**Recommendation to bring to
M21.0 open:** do not preemptively
lock M21 as any specific
candidate. M21 target selection
follows the standard business-
priority pattern at M21.0 open.
The candidate list expands at
M21.0 per the M20 retrospective
§8 unblocks + carry-forwards
from M19 §9:

- **Carry-forward candidates:**
  T (process real tester
  feedback), U (hosted-demo
  substrate), A (return to
  accounting), P (onboarding
  UX polish), L (first-live-
  pilot staging dry-run), M
  (multi-operator support), D
  (demo-aware LLM router /
  cost caps), C (F&I chargeback
  substrate).
- **New at M20 §8:**
  - **M12.8 (BHPH collections
    write-side UI)** — missing
    UI gap surfaced by M20.4.
  - **Dashboard testid
    hardening** — technical
    debt against Playwright
    journey extensions.

The full M21 planning memo
(SESSION_166 or later) scopes
each candidate + presents the
recommended selection at open.
Chris picks with the full brief
in hand.

**Accounting slot posture.** M18
retrospective §8 designated M20
as the "return to accounting"
slot; M20 diverged. Three
consecutive milestones (M18,
M19, M20) diverging from
accounting risks ossifying the
divergence. Recommendation
strength for A at M21.0 open is
correspondingly higher than at
M20.0 open, but the standard
business-priority rubric still
applies.
