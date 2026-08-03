---
state: active
date: 2026-08-03
last_session_shipped: SESSION_171
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: shipped
milestone_11_status: shipped
milestone_12_status: shipped
milestone_13_status: shipped
milestone_14_status: shipped
milestone_15_status: shipped
milestone_16_status: shipped
milestone_17_status: shipped
milestone_18_status: shipped
milestone_19_status: shipped
milestone_20_status: shipped
milestone_21_status: shipped
milestone_22_status: in-progress
next_session: SESSION_172
next_milestone: 22
next_milestone_name: "Accounting Operational Validation"
next_increment: 1
next_increment_name: "M22.1 — Audit tooling correction + artifact refresh"
---

# Next session — SESSION_172 · Milestone 22 · Increment 1 (M22.1 — audit tooling correction + artifact refresh)

> **Milestone 22 · Increment 0 —
> Accounting Operational Validation
> planning refinement — SHIPPED at
> SESSION_171.** Full memo expansion
> from M21.5 skeleton + seven §5
> load-bearing decisions resolved as-
> recommended at open. **Empirical
> M22.0 discovery reshaped Candidate
> A** from "ship missing UI" (per
> the M21 retrospective §9
> recommendation, now known to have
> been grounded in unreliable audit
> numbers) to **Accounting
> Operational Validation** —
> validate the shipped accounting
> workflows end-to-end via Playwright
> rather than rebuild what already
> ships.
>
> **Planning-time as-recommended
> streak extends 87 → 88 across
> thirteen consecutive milestones**
> (M10 → M22). **Zero-drift
> permission-class streak target for
> M22 close: 21 → 22 consecutive
> milestones.**
>
> **SESSION_172 opens M22.1 —
> audit tooling correction +
> artifact refresh.** Supporting
> work per §5.e Option B (targeted
> regex fix). Not the milestone
> centerpiece; the anchor JE
> reversal journey ships at M22.2.
> Budget guard: if targeted fix
> exceeds ~2 hours, stop and defer
> deeper refactor to a future audit-
> tooling milestone per §5.e.
>
> **DoD compliance verified by
> construction** for M22 — every
> implementation increment (M22.2
> anchor + conditional M22.3) adds
> a Playwright operational journey.
> The M21.0 §5.f Option B DoD
> amendment is trivially satisfied.

## First thing SESSION_172 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  should be the M21.5 close-out
  commit (`6103aea Milestone 21
  shipped`); no new commits at
  origin/main (M22.0 was planning-
  only, no push).
- `python3 manage.py test dealer_ai`
  → **4,761 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` → **180
  pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `cd acceptance && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Inspect the audit script's URL-normalizer regex

Open
`backend/dealer_ai/scripts/audit_operational_surface.py`
and locate the URL-normalization
path that walks
`frontend/src/lib/*Api.ts` wrapper
modules. Identify where nested
template literals (`${qs ? \`?${qs}\` : ""}`)
lose their consumer signal.

Cross-check against the four known
misclassifications by grepping the
`accountingApi.ts` module for
`fetchTrialBalance`,
`fetchJournalEntries`,
`fetchCostPostingFailures`,
`listTrialBalanceSnapshots` — each
wrapper's actual URL pattern is the
test case.

### 3. Ship the targeted regex fix

Per §5.e Option B — narrow scope.
Enhance the URL normalizer to handle
one additional level of template-
literal nesting (`\`prefix${qs ? \`?${qs}\` : ""}\``
style). Do NOT attempt a full AST
rewrite. Do NOT expand scope to
handle other classes of false-
negative unless they surface as
side-effects of the same fix.

**Budget guard.** If the targeted
fix exceeds ~2 hours (from opening
the script to green-passing test),
stop. Document the remaining
false-negative patterns as future
audit-tooling milestone scope in
§0.a M22.1 amendment, land a
partial fix (or no fix), and
proceed to M22.2 with the audit
still partially unreliable.
Preserves scope discipline over
completionism.

### 4. Optional: add audit-script correctness test

If the audit script has an existing
test module, extend it with a
regression test for the nested-
template-literal case. If not, adding
a new test is discretionary — the
regenerated artifact itself is the
functional test in the sense that
the four misclassifications either
reclassify to `covered` or they
don't.

### 5. Regenerate the audit artifact

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Verify the M21 audit artifact updates
with:
- `admin-trial-balance` →
  `covered` (was `defer-candidate-O2`).
- `admin-journal-entry-list` →
  `covered` (was `defer-candidate-O2`).
- `admin-cost-posting-failures` →
  `covered` (was `defer-candidate-O2`).
- `admin-trial-balance-snapshot-list`
  → `covered` (was `defer-domain-
  milestone`).
- Coverage count: 106 → **≥110**.
- Backend-only count: 47 → **≤43**.

If any of the four does NOT
reclassify, the fix is incomplete
— either extend the regex or
document the residual limitation
in §0.a M22.1 amendment.

If additional endpoints reclassify
(from any domain), catalog them in
§0.a with brief context. These are
audit-noise reductions that don't
change M22 scope but strengthen
future OSC candidates.

### 6. Update M22 planning memo §0.a with M22.1 outcome

Add an `**SESSION_172 M22.1 close
(YYYY-MM-DD):**` entry to the §0.a
change log capturing: audit fix
shipped (yes/partial/skipped),
misclassifications corrected, any
additional false-negatives
surfaced, budget-guard triggered
(yes/no), notes on the fix
approach.

### 7. Ship the M22.1 handoff

- `docs/handoffs/SESSION_172_m22_inc1_audit_correction.md`.
- Overwrite `00-START-NEXT-SESSION.md`
  with M22.2 priority (first
  anchor journey — JE reversal).
- **Do NOT push** — M22 uses
  coordinated close-out push per
  M18.6 / M19.6 / M20.5 / M21.5
  cadence at M22.4.

## Non-goals for SESSION_172

- ❌ Do NOT ship the JE reversal
  journey (that's M22.2 scope).
- ❌ Do NOT attempt a full AST-
  based audit rewrite (explicit
  non-goal per §5.e Option B).
- ❌ Do NOT modify shipped
  accounting UI (rebuilding what
  already ships from M14/M17).
- ❌ Do NOT let audit correction
  bleed past the ~2-hour budget
  guard.
- ❌ Do NOT expand fix scope to
  audit patterns unrelated to the
  nested-template-literal class
  unless they surface as side-
  effects of the same fix.
- ❌ Do NOT push M22.1 commits
  individually.

## Baseline expected at close

- Backend baseline: 4,761 →
  **~4,762–4,763** (possible
  audit-script correctness tests).
- Frontend Vitest: 180 (unchanged
  — no frontend changes).
- Acceptance suite: 6 journeys
  (unchanged — M22.2 introduces
  the first new M22 journey).
- Migrations `0001`–`0048`
  unchanged.
- Tenancy carriers 52 unchanged.
- Permission classes 7 unchanged
  (zero-drift streak intact).
- Audit artifact updated with ≥4
  reclassifications; coverage
  count increases by ≥4.

## NEXT TASK

Start SESSION_172 with (a)
starting-state verification, (b)
inspect the audit script's URL-
normalizer regex against the four
known accounting misclassifications,
(c) ship the targeted regex fix
under the ~2-hour budget guard, (d)
optional audit-script correctness
test, (e) regenerate the audit
artifact and verify at least the
four accounting endpoints
reclassify, (f) update M22 planning
memo §0.a with M22.1 outcome, (g)
ship the M22.1 handoff and refresh
`00-START-NEXT-SESSION.md` for
M22.2. Do NOT push.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M21 shipped + DoD amendment
   landed at M21.5)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_22_PLANNING.md`
   (active memo — governing
   contract for M22.1 audit
   correction posture)
6. `docs/handoffs/SESSION_171_m22_inc0_planning.md`
   (M22.0 close — empirical
   discovery record)
7. `docs/roadmap/MILESTONE_21_RETROSPECTIVE.md`
   §4 (documented nested-template-
   literal audit limitation being
   fixed at M22.1)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact being
   regenerated — known unreliable
   for accounting until M22.1
   correction lands)
9. `docs/CAPABILITY_MATRIX.md` §7v
   (M21 shipped surface)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_171 — Milestone 22.0 planning shipped)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,761 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 180 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace
  (local):** Playwright 1.49 +
  TS 5.6 operational; **six
  journeys** passing end-to-end.
  Full dry-run baseline: **12
  passed (~18s)** (6 setup + 6
  journeys). No M22 journeys
  ship until M22.2 open.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`.
  First real M21 CI run verified
  green at SESSION_171 M22.0
  open (run `30822664811`,
  2m3s).
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  **M21**. M22 in-progress
  (M22.0 planning shipped;
  M22.1 next at SESSION_172).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all
  M1–M21 packages unchanged.
  M22 will add zero service
  verbs.
- **Frontend surfaces:** M14
  accounting pages
  (`AccountingTrialBalancePage`,
  `AccountingJournalEntriesPage`,
  `AccountingJournalEntryDetailPage`)
  + M17.2 trial-balance snapshot
  lifecycle UI + M21 BHPH write
  surfaces + M21 sales-manager
  extensions. M22 will add zero
  new components.
- **Tenancy carriers:** **52**.
- **Permission classes:** **7
  actual** — zero-drift streak
  **twenty-one consecutive
  milestones** (M10 → M21).
  Target at M22 close: 22.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 22 status:**
  IN-PROGRESS. M22.0 planning
  shipped at SESSION_171 with
  seven §5 load-bearing
  decisions resolved as-
  recommended at open. Full
  active memo landed at
  `docs/roadmap/MILESTONE_22_PLANNING.md`.
- **Audit tooling:** operator-
  invoked from `backend/`
  (`python3 -m dealer_ai.scripts.audit_operational_surface`).
  Known unreliable for
  accounting until M22.1
  targeted regex fix lands.
- **Planning-time streak:** **88
  as-recommended M5.1 → M22.0**
  across thirteen consecutive
  milestones (M10 → M22).
- **DoD amendment (M21.0 §5.f
  Option B, formalized in
  IMPLEMENTATION_ROADMAP at
  M21.5):** every future
  customer-facing milestone
  must add or update at least
  one Playwright operational
  journey, or explicitly
  document in §3 why no
  journey change is required.
  M22 satisfies by construction
  — every implementation
  increment adds a journey.
- **M22 governing contract
  (refined from M21 Candidate
  O):** (1) maps to shipped
  frontend surface + shipped
  backend capability; (2)
  establishes operational-
  completion evidence through
  Playwright end-to-end
  journey; (3) uses journey-
  as-verifier; (4) splits
  discovered gaps by size —
  small in-scope fix vs. large
  deferred as next candidate
  evidence.
- **M22 anchor implementations:**
  M22.1 audit tooling correction
  (supporting), M22.2 JE
  reversal journey + seed
  extension (first anchor),
  M22.3 additional journeys per
  §5.b enumeration
  (conditional), M22.4 close-
  out.
- **M22 audit correction scope
  (M22.1):** targeted regex fix
  for nested template literals;
  reclassifies at minimum four
  known accounting endpoints
  (`admin-trial-balance`,
  `admin-journal-entry-list`,
  `admin-cost-posting-failures`,
  `admin-trial-balance-snapshot-list`)
  from backend-only to covered.
  Budget guard: ~2 hours.
