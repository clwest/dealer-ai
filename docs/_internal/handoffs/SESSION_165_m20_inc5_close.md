---
title: "SESSION_165 handoff — Milestone 20 · Increment 5 (M20.5 — close-out + first push)"
status: historical
type: handoff
date: 2026-08-02
session: 165
milestone: 20
milestone_status: shipped
milestone_name: "Operational Journey Validation (Playwright acceptance testing)"
increment: 5
increment_status: shipped
commit: TBD
---

# SESSION_165 — Milestone 20 · Increment 5 (M20.5 — close-out + first push)

## What shipped

Milestone 20 close-out. Full local
acceptance dry-run **12 passed (18.4s)**
after intentional-failure verification of
the CI artifact flow. All docs updated,
retrospective written, M21 planning
skeleton drafted, roadmap flipped,
frontmatter of M20 planning memo flipped
to `shipped`. Coordinated close-out
commit + **first push** — surfaces all
six M20 commits (M20.0 → M20.5) to
`origin/main` and triggers the first
real GitHub Actions acceptance CI run.

### Intentional-failure verification (§5.g Option A)

Per the M20 planning §5.g Option A
artifact contract. Temporarily broke
the owner morning review journey by
changing the "Overview" heading name
to a bogus value; ran
`npx playwright test --project=owner`;
verified all four artifact types land
in the expected paths:

- `playwright-report/index.html` —
  HTML report always generated ✓
- `test-results/.../test-failed-1.png`
  — screenshot on failure ✓
- `test-results/.../video.webm` —
  video on failure ✓
- `test-results/.../error-context.md`
  — Playwright error context ✓

Reverted the intentional break;
re-ran full suite — **12 passed
(18.4s)**. CI upload step at
`.github/workflows/acceptance.yml`
uses the same `test-results/` +
`playwright-report/` directories,
so the CI artifact flow is provably
correct.

Note on traces: Playwright's
`trace: 'on-first-retry'` config only
produces `.trace.zip` files when a
test retries. Locally with
`retries: 0`, no trace file lands.
In CI with `retries: 1` (per
`playwright.config.ts` line 46 —
`IS_CI ? 1 : 0`), traces will land
on the second attempt of any
failing test.

### Docs shipped

**`docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`**
(new). Nine sections mirroring the M19
retrospective structure: planned scope,
what actually shipped, deferrals (11
M20-specific), deviations (2:
Candidate W folded into J at open;
M20.4 scope narrowed to read side),
compatibility with existing surface,
lessons (6), streak update, unblocks,
standing question. Explicit six-
journey delivery record + 76 backend
test additions + zero drift on every
shipped-surface metric.

**`docs/CAPABILITY_MATRIX.md`** —
new §7u section between §7t (M19) and
§8 (dealer branding). Documents the
M20 shipped surface: framework
substrate, support layer, six seed
delta management commands, six
journey specs, GitHub Actions CI job,
settings.py extension. Deferrals
enumerated with re-entry paths.
"What operators experienced" summary.

**`docs/roadmap/IMPLEMENTATION_ROADMAP.md`**
— new Milestone 20 entry inserted
between M19 and §5 non-goals.
Business objective + guiding principle
+ related research + operational pain
resolved + existing reusable
primitives + gap + six-increment
scope + non-goals. Follows the M19
entry shape verbatim.

**`docs/roadmap/MILESTONE_21_PLANNING.md`**
(new, `status: draft`). Skeleton with
candidate list — eight carry-forward
candidates from M19 §9 (T, U, A, D, C,
P, L, M) + two new candidates from
M20 §8 (M12.8 BHPH collections write-
side UI, dashboard testid hardening).
"Recommendation strength elevated at
M21.0" note for Candidate A per M18
§8 accounting-slot posture.

**`docs/roadmap/MILESTONE_20_PLANNING.md`**
frontmatter flipped: `status: active`
→ `status: shipped`; added
`shipped_at_session: SESSION_165` +
`shipped_date: 2026-08-02`.

**`00-START-NEXT-SESSION.md`** —
refreshed for SESSION_166 / M21.0
open. Standing question restated,
candidate list surfaced, planning-
time streak (86 → 87 target
recorded).

## Verification

**Backend baseline (post-M20.5):**
unchanged at **4,755 pass**, 1 skipped,
0 fail (M20.5 is docs-only). Frontend
Vitest baseline unchanged at **153
pass**. `tsc --noEmit` clean in
`frontend/` + `acceptance/`. Django
`check` + `makemigrations --check
--dry-run` clean.

**Local acceptance suite:** **12
passed (18.4s)** — 6 setup steps + 6
journeys — after intentional-failure
verification + revert. This is the
M20 final local baseline.

**Zero drift:**
- Migrations unchanged at
  `0001`–`0048`.
- Tenancy carriers unchanged at
  **52**.
- **Permission classes unchanged at
  7 — zero-drift streak extends
  nineteen → twenty consecutive
  milestones** (M10 → M20).
- DRF admin surface unchanged at
  **113**.
- Frontend operator routes
  unchanged at **20**.

## First push

**`git push origin main`** —
surfaces all six M20 commits to
`origin/main` in one coordinated
push per the M18/M19 cadence:

- `69b8214` M20.0 planning
- `66ee652` M20.1 framework + canonical pilot journey
- `e634c34` M20.2 dashboard journeys
- `59dc43d` M20.3 back-office journeys
- `d7e92c2` M20.4 BHPH read-side journey
- **M20.5 close-out (this commit)**

This is the first push containing
the new `.github/workflows/acceptance.yml`
CI job. Push triggers:

1. The acceptance job on `main`
   push — full six-journey suite,
   target ~5–8 min.
2. On subsequent PRs, the
   `@pilot-critical` subset — target
   ~90s.

**Fault mode:** if the first CI run
fails, the failure is either (a) a
CI-environment-specific issue that
didn't surface locally (Node/Python
version drift, Playwright browser
install differences, permissions) or
(b) a bug in the acceptance suite
that only manifests in the fresh CI
DB. Address as SESSION_166 §0.a
amendments before declaring M20
shipped as CI-verified.

## What's next: SESSION_166 M21.0

Per `MILESTONE_21_PLANNING.md` §"What
M21.0 must do":

1. Verify starting state.
2. **Monitor first real CI run** —
   check the acceptance job status on
   the M20.5 push commit; if red,
   address as §0.a amendments.
3. Present the M21 candidate list
   (10 candidates: 8 carry-forwards
   + 2 new from M20 §8).
4. Recommend a target for §5.a with
   rationale.
5. Await user confirmation.
6. Draft §5.b–§5.h with confirm-as-
   recommended posture (streak
   86 → 87 target).
7. Expand `MILESTONE_21_PLANNING.md`
   from skeleton to active memo.
8. Ship M21.0 handoff.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`
   (this session's primary deliverable)
6. `docs/roadmap/MILESTONE_20_PLANNING.md`
   (frontmatter shipped this session)
7. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (skeleton this session; active at
   SESSION_166)
8. `docs/CAPABILITY_MATRIX.md` §7u
   (M20 shipped surface)
9. `docs/handoffs/SESSION_164_m20_inc4_bhph_journey.md`
   (M20.4)
10. `docs/handoffs/SESSION_163_m20_inc3_backoffice_journeys.md`
    (M20.3)
11. `docs/handoffs/SESSION_162_m20_inc2_dashboard_journeys.md`
    (M20.2)
12. `docs/handoffs/SESSION_161_m20_inc1_framework.md`
    (M20.1)
13. `docs/handoffs/SESSION_160_m20_inc0_planning.md`
    (M20.0)
