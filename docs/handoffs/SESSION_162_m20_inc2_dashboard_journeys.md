---
title: "SESSION_162 handoff — Milestone 20 · Increment 2 (M20.2 — owner morning review + sales manager daily startup journeys)"
status: historical
type: handoff
date: 2026-08-02
session: 162
milestone: 20
milestone_status: in-progress
milestone_name: "Operational Journey Validation (Playwright acceptance testing)"
increment: 2
increment_status: shipped
commit: TBD
---

# SESSION_162 — Milestone 20 · Increment 2 (M20.2 — owner morning review + sales manager daily startup journeys)

## What shipped

The **first Playwright dry-run** against the M20.1 framework
uncovered two framework-substrate issues that were resolved as §0.a
M20.2 decisions before layering journey work. After the fixes, the
full three-journey suite runs end-to-end green:

**7 passed (12.6s)** — 4 setup steps (seed baseline + 3 persona
logins) + pilot onboarding (M20.1) + owner morning review (M20.2) +
sales manager daily startup (M20.2).

Per M20 planning §7 M20.2 + the guiding principle. Assertions
target business state through the admin API; UI interactions go
through the real shipped pages.

**Two new personas** in
`acceptance/support/auth/personas.ts`:

- `owner` — `acceptance-owner` user with `dealer_owner` role at
  the default dealership. Post-login lands at
  `/dealer-ai-overview`.
- `sales_manager` — `acceptance-sales-manager` user with
  `sales_manager` role at the default dealership. Post-login lands
  at `/dealer-ai-overview`.

**Auth setup extended** in
`acceptance/support/auth/login.setup.ts`:

- Single seed step now runs all three seed delta commands
  (`seed_journey_pilot_onboarding` +
  `seed_journey_owner_morning_review` +
  `seed_journey_sales_manager_daily_startup`).
- One setup step per persona logs in via the real UI, saves
  storage state to
  `.auth/{platform_operator,owner,sales_manager}.json`.
- Belt-and-suspenders `/auth/me/` check confirms the correct user
  was authenticated (drift between seed + persona registry surfaces
  at setup, not deep in a journey).

**Playwright config extended** with per-persona projects — each
persona project runs only its persona's journey directory (`pilot`
for `platform_operator`, `owner` for `owner`, `sales_manager` for
`sales_manager`), inheriting the persona-specific storage state.

**Two new backend seed delta commands** per §5.d Option B:

- `seed_journey_owner_morning_review.py` — provisions the owner
  user + role + two unassigned overnight phone leads
  ("Overnight Buyer A" + "Overnight Buyer B") on the default
  dealership. Composes `record_phone_lead` service verb.
  Idempotent via the fixture tag `[M20.2-owner-morning-review]`
  in lead notes. **12 focused backend tests** (fresh-run
  provisioning, idempotency, `--reset`, tenant scoping,
  credentials authenticate).
- `seed_journey_sales_manager_daily_startup.py` — provisions the
  sales-manager user + role + an advisor (Salesperson + linked
  auth user, `is_active=True`) + three unassigned overnight
  leads with varied urgency. Idempotent via the fixture tag
  `[M20.2-sales-manager-daily-startup]`. **15 focused backend
  tests** (users, salesperson, memberships, leads, idempotency,
  `--reset` deactivation + re-activation, credentials).

**Dashboard assertion helpers** at
`acceptance/support/assertions/dashboard.ts`:

- `expectLeadListHasAtLeast(request, min, params)` — prove the
  admin leads endpoint returns >= N leads for the given filter.
- `findSeededLead(request, name, params)` — locate a fixture
  lead in the admin list, fail loudly with the observed name
  list on miss.
- `expectLeadAssignedTo(request, leadId, advisorName)` — assert
  the lead is now assigned to the named advisor at the service
  layer.

**Two new journey specs**:

- `acceptance/journeys/owner/morning_review.spec.ts` — tagged
  `@pilot-critical`. Owner lands on `/dealer-ai-overview`, sees
  key dashboard cards (`AI Sales Assistant`, `Today's leads`),
  API-verifies the pipeline has content + the seeded lead is
  present, drills into `/dealer-ai-leads`, confirms the seeded
  lead appears in the queue.
- `acceptance/journeys/sales_manager/daily_startup.spec.ts` —
  sales manager lands on `/dealer-ai-overview`, navigates to
  `/dealer-ai-admin` (the shipped assignment surface — the
  read-only `/dealer-ai-leads` page does not offer assignment
  per LeadsPage.tsx line 3), clicks the seeded lead's row in
  "Recent leads" to open the LeadDetailModal, opens the
  AssignmentDropdown, picks "Acceptance Advisor", and asserts
  the assignment landed at the service layer via the admin
  `/admin/leads/` list.

## Verification

**Backend baseline (post-M20.2):** 4,694 → **4,721 pass** (+27
seed command tests: 12 owner + 15 sales_manager). Frontend
Vitest baseline unchanged: **153 pass**. `tsc --noEmit` clean in
both `frontend/` and `acceptance/`. `manage.py check` clean.
`makemigrations --check --dry-run` → "No changes detected."

**Acceptance suite (local dry-run):**
- Setup: 4 steps (baseline seed + 3 persona logins) — pass.
- `pilot/onboarding.spec.ts` (@pilot-critical) — pass.
- `owner/morning_review.spec.ts` (@pilot-critical) — pass.
- `sales_manager/daily_startup.spec.ts` — pass.
- **Total: 7 passed (12.6s).**

**Zero drift:**
- Migrations unchanged at `0001`–`0048`.
- Tenancy carriers unchanged at **52**.
- Permission classes unchanged at **7** (zero-drift streak
  intact at nineteen consecutive milestones).
- DRF admin surface unchanged at **113**.
- Frontend operator routes unchanged at **20**.
- No existing backend service verb, endpoint, migration, or
  frontend route modified.

## §0.a — Implementation-time decisions

**M20.2 decision 1 — ES module dirname portability.**
`playwright.config.ts`, `support/auth/login.setup.ts`, and
`support/seed/invoke.ts` used `__dirname`, which is undefined
in ES module scope. Replaced with the portable idiom
`path.dirname(fileURLToPath(import.meta.url))`. Surfaced by the
first M20.1 dry-run — exactly the class of issue the M20.2 §2
dry-run step was designed to catch.

**M20.2 decision 2 — vite bind to 127.0.0.1.** Vite's default
`localhost` bind resolves to `::1` only on macOS, which
Playwright's IPv4 poll misses (`webServer` timed out despite
vite reporting "ready in 124 ms"). Added explicit `--host
127.0.0.1` to the vite dev + preview commands in
`playwright.config.ts`. Applies in both local dev and CI.

**M20.2 decision 3 — sales manager journey targets
/dealer-ai-admin, not /dealer-ai-leads.** The LeadsPage
(/dealer-ai-leads) is deliberately read-only
(LeadsPage.tsx line 3: "No reassignment"). The
LeadDetailModal + AssignmentDropdown are wired only through
DealerAdmin.tsx's SalesPipeline + Recent leads table. Journey
retargeted to `/dealer-ai-admin` accordingly.

**M20.2 decision 4 — modal scoping via
`div.fixed.inset-0.z-50`.** LeadDetailModal is not a Radix
Dialog (no `role="dialog"`). The initial modal-scoping locator
matched a page-level ancestor that contained "Sales handoff
packet" text (making the scope useless) or picked up the
Handoff queue's "Unassigned" filter button. Fixed by scoping
to the modal's outermost fixed-position wrapper via its class
signature `div.fixed.inset-0.z-50`. Selector-stability defect
in the dashboard (no `data-testid` on cards or modal) deferred
to a future increment if the class-based selector proves
brittle.

**M20.2 decision 5 — CardTitle is a `<div>`, not a heading.**
shadcn/ui's `CardTitle` renders as `<div>`
(frontend/src/components/ui/card.tsx line 36), not a semantic
heading. Journey selectors that assumed
`getByRole("heading", { name: "..." })` for card titles were
updated to `getByText("...", { exact: true })`. Frontend-side
fix (adding semantic heading roles) deferred; not required
for the acceptance contract.

## What's next: SESSION_163 M20.3

Per `MILESTONE_20_PLANNING.md` §7 M20.3 — two operator back-
office journeys:

- `seed_journey_recon_workflow` +
  `seed_journey_office_accounting_workflow` seed delta
  commands + backend tests (~10-20).
- `acceptance/journeys/recon/workflow.spec.ts` +
  `acceptance/journeys/office/accounting_workflow.spec.ts`.
- New personas: `recon_manager` + `office_manager` in
  `personas.ts` + auth setup + config projects.
- Extend assertion helpers as needed
  (`support/assertions/recon.ts` /
  `support/assertions/accounting.ts`).

**Acceptance baseline target at M20.3 close:** **5 journeys**
(pilot onboarding + owner morning review + sales manager
daily startup + recon workflow + office/accounting workflow).
Pilot-critical subset unchanged at 2 (pilot onboarding + owner
morning review). Backend baseline ~4,721 → ~4,731-4,741.

## What lands at M20.4 (SESSION_164)

BHPH collections journey + seed + tests + `bhph_collector`
persona.

## What lands at M20.5 (SESSION_165)

Close-out: full-suite CI validation (verify ~5–8 min on
`main`; ~90s on PR pilot-critical), intentional dry-run
failure to confirm artifact upload, capability matrix §7u,
retrospective + §9 standing M21 question, M21 skeleton,
IMPLEMENTATION_ROADMAP flip, coordinated close-out commit +
first push (which will surface the M20 commits to GitHub
Actions and trigger the first real CI run).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_20_PLANNING.md`
   (this milestone's active memo)
6. `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
   §9 (Candidate J origin)
7. `docs/CAPABILITY_MATRIX.md` §7t
   (M19 shipped surface — the substrate M20 validates)
8. `docs/handoffs/SESSION_161_m20_inc1_framework.md`
   (M20.1 framework substrate)
9. `docs/handoffs/SESSION_160_m20_inc0_planning.md`
   (M20.0 planning close)
