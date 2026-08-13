---
title: "SESSION_163 handoff — Milestone 20 · Increment 3 (M20.3 — recon workflow + office/accounting workflow journeys)"
status: historical
type: handoff
date: 2026-08-02
session: 163
milestone: 20
milestone_status: in-progress
milestone_name: "Operational Journey Validation (Playwright acceptance testing)"
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_163 — Milestone 20 · Increment 3 (M20.3 — recon workflow + office/accounting workflow journeys)

## What shipped

Two new operator back-office journeys layered onto the M20.1
framework. Full local acceptance dry-run: **10 passed (16.4s)**
— 5 setup steps (baseline seed + 4 persona logins) + 5 journeys
(pilot onboarding + owner morning review + sales manager daily
startup + recon workflow + office/accounting workflow).

Per M20 planning §7 M20.3 + the guiding principle. Assertions
target business state through the M4 recon dashboard API + the
M17 trial-balance snapshot API.

**Personas.** One new persona (`recon_manager`) added; office/
accounting journey reuses the existing `owner` persona
(`dealer_owner` is a valid role for the M13/M14/M17 accounting
endpoints per `IsSalesManagerOrOwnerAtActiveDealership`, so no
new user needed).

Added to `personas.ts`, `login.setup.ts` (new setup step +
extended `SEED_COMMANDS`), `playwright.config.ts` (two new
project entries: `recon_manager` for `journeys/recon/*`,
`office_accounting` for `journeys/office/*`; the latter reuses
`AUTH_STORAGE.owner`).

**Two new backend seed delta commands** per §5.d Option B:

- `seed_journey_recon_workflow.py` — provisions the
  `acceptance-recon-manager` user + role, plus a fixture
  `Vehicle` with stable stock `M20-RECON-ACCEPT`, a completed
  `ConditionReport`, and one `ConditionFinding` starting with
  no decision. Direct ORM creation matches the pattern in
  `tests/test_admin_recon_endpoints.py` fixtures (there are no
  public write-verb service functions for ConditionReport /
  ConditionFinding outside the demo-store archetypes).
  Idempotent via stable stock + fixture tag on the finding
  description. **13 focused backend tests**.
- `seed_journey_office_accounting_workflow.py` — ensures the
  default COA is seeded and posts one balanced journal entry
  (Dr Bank Operating $100 / Cr Vehicle Sales Retail $100) on
  the default dealership. No new user — reuses
  `acceptance-owner`. Composes `post_journal_entry` +
  `seed_default_coa` service verbs. Idempotent via stable
  entry `description`. **7 focused backend tests**.

**Two new assertion helpers**:

- `acceptance/support/assertions/recon.ts` —
  `expectFinding(request, stock, substring)` and
  `expectDecisionRecorded(request, stock, substring, tier)`
  reading `/admin/vehicles/{stock}/recon/`.
- `acceptance/support/assertions/accounting.ts` —
  `expectSnapshotCountAtLeast(request, minCount)` and
  `expectSnapshotBalanced(request, id)` reading the envelope-
  wrapped `/admin/accounting/trial-balance/snapshots/list/` and
  `.../{id}/` endpoints.

**Two new journey specs**:

- `acceptance/journeys/recon/workflow.spec.ts` — recon manager
  lands on `/dealer-ai-inventory/M20-RECON-ACCEPT/recon`,
  verifies the recon dashboard renders with the seeded finding
  visible + a `Must do` tier button available, clicks it, waits
  for the reconsideration prompt to appear as the UI-side
  settle signal, and asserts via the recon dashboard API that
  the ReconDecision persisted with `tier=must_do`.
- `acceptance/journeys/office/accounting_workflow.spec.ts` —
  owner lands on `/dealer-ai-accounting/trial-balance`, waits
  for the `Freeze this view` button to be enabled (indirect
  readiness signal for the trial-balance load), clicks freeze,
  polls the snapshot list until the count increases, clicks
  the newest snapshot row via its `snapshot-row-<id>`
  data-testid, and asserts the frozen snapshot is balanced
  via the snapshot-detail endpoint.

Neither M20.3 journey is tagged `@pilot-critical` — both run
only in the full-suite CI on `main` push per §5.h.

## Verification

**Backend baseline (post-M20.3):** 4,721 → **4,741 pass** (+20
seed command tests: 13 recon + 7 accounting). Frontend Vitest
baseline unchanged: **153 pass**. `tsc --noEmit` clean in
`frontend/`, `acceptance/`. Django `check` + `makemigrations
--check --dry-run` clean.

**Acceptance suite (local dry-run):**
- Setup: 5 steps (baseline seed + 4 persona logins) — pass.
- `pilot/onboarding.spec.ts` (@pilot-critical) — pass.
- `owner/morning_review.spec.ts` (@pilot-critical) — pass.
- `sales_manager/daily_startup.spec.ts` — pass.
- `recon/workflow.spec.ts` (M20.3) — pass.
- `office/accounting_workflow.spec.ts` (M20.3) — pass.
- **Total: 10 passed (16.4s).**

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

**M20.3 decision 1 — accounting journey reuses `owner`
persona.** The M13/M14/M17 accounting endpoints gate on
`IsSalesManagerOrOwnerAtActiveDealership`; `dealer_owner`
(the `owner` persona's role) qualifies. No `office_manager`
role exists in the M1 auth model, so the `office_accounting`
Playwright project reuses `AUTH_STORAGE.owner`. Cleanest
possible extension — one fewer user + login step.

**M20.3 decision 2 — recon seed uses direct ORM object
creation.** `ConditionReport` / `ConditionFinding` do not
have public write-verb service functions outside the
`services/demo_store/archetypes/*.py` scenario builders
(which construct entire demo-store fixtures, not narrow
journey deltas). The existing test-fixture pattern
(`tests/test_admin_recon_endpoints.py:83-118` +
`tests/test_condition_finding.py:62-79`) uses direct
`.objects.create()` calls; the M20.3 seed matches that
convention. Explicitly noted so this doesn't drift into a
"parallel write path" concern — it isn't; it's the
established test-fixture pattern for this substrate.

**M20.3 decision 3 — API response envelopes required
unwrapping in helpers.** The M17.1 trial-balance snapshot
endpoints return envelope-wrapped responses
(`{trial_balance_snapshots: {snapshots: [...]}}` for list;
`{trial_balance_snapshot: {...}}` for detail). Initial
assertion helper missed the envelope; dry-run surfaced the
mismatch. Helpers updated with explicit envelope-typed
response types + comment linking to
`backend/dealer_ai/views_accounting.py:614,646` as the source
of truth.

**M20.3 decision 4 — recon journey UI settle signal via
reconsideration button.** After clicking a tier button in
`DecisionRow`, the tier picker is replaced with a Badge
showing the tier + reconsideration buttons prefixed with
"→" (per `DecisionRow.tsx:137-153`). Initial attempt to wait
for the "Must do" badge failed because both the pre-click
Button and the post-click Badge carry the "Must do" text,
making `getByText("Must do")` ambiguous. Settled instead on
waiting for the "→ Should do" reconsideration button — which
only exists AFTER a decision has been recorded. Definitive
business-outcome assertion still happens at the service
layer via the recon dashboard API.

## What's next: SESSION_164 M20.4

Per `MILESTONE_20_PLANNING.md` §7 M20.4 — BHPH collections
workflow journey (standalone).

**Scope caveat:** the M20.4 plan says the BHPH collections
journey exercises "M12 promise-to-pay + repossession
lifecycle". The M20.2 SESSION_162 handoff §0.a decision noted
that the be-back frontend UI didn't exist as of M19. The M20.4
work should first verify how much of the BHPH collections
workflow has shipped frontend UI (`/dealer-ai-bhph-*` routes,
`BhphNoteDetail`, etc.) before designing the journey. If the
end-to-end promise-to-pay → broken-promise → repossession-
initiation flow doesn't have shipped UI at every step, the
journey scope will need to narrow — record scope adjustments
as §0.a M20.4 decisions.

**Backend baseline target at M20.4 close:** 4,741 → ~4,750-
4,760 (seed command tests). Frontend Vitest: 153
(unchanged).

**Acceptance baseline target at M20.4 close:** **6 journeys**
(add BHPH collections). Pilot-critical subset unchanged at
**2**.

## What lands at M20.5 (SESSION_165)

Close-out: full-suite CI validation (verify targets on `main`
+ PR), intentional dry-run failure to confirm artifact upload,
capability matrix §7u, retrospective + §9 standing M21
question, M21 skeleton, IMPLEMENTATION_ROADMAP flip,
coordinated close-out commit + first push (which will surface
the M20 commits to GitHub Actions and trigger the first real
CI run).

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
8. `docs/handoffs/SESSION_162_m20_inc2_dashboard_journeys.md`
   (M20.2)
9. `docs/handoffs/SESSION_161_m20_inc1_framework.md`
   (M20.1 framework substrate)
10. `docs/handoffs/SESSION_160_m20_inc0_planning.md`
    (M20.0 planning close)
