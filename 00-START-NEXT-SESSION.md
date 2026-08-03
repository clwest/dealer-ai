---
state: active
date: 2026-08-02
last_session_shipped: SESSION_159
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
next_session: SESSION_160
next_milestone: 20
next_milestone_name: "(target selection pending — locked at M20.0 open)"
next_increment: 0
next_increment_name: "M20.0 — Planning refinement + target selection"
---

# Next session — SESSION_160 · Milestone 20 · Increment 0 (M20.0 — Planning + target selection)

> **Milestone 19 — Founding Dealer
> Pilot Onboarding — SHIPPED at
> SESSION_159.** Seven-increment
> milestone across SESSION_153 → 159.
> Substrate + inventory import + five
> lifecycle endpoints + embedded
> frontend admin sub-section + end-to-
> end dry-run + operator playbook +
> close-out. Backend baseline 4,538
> → **4,679 pass** (+141, zero
> regressions). Frontend Vitest 140
> → **153 pass** (+13). DRF admin
> surface 108 → **113** (+5).
> Tenancy carriers 50 → **52**.
> Migrations 0043-0047 → 0043-**0048**.
> Zero-drift permission-class streak
> extended from fourteen → **nineteen
> consecutive milestones** (M10 →
> M19.5). Planning-time streak
> extends to **85 planning-time as-
> recommended M5.1 → M19.0** across
> ten consecutive milestones.
>
> **SESSION_160 opens M20.0 —
> planning refinement + target
> selection.** No target locked yet
> — the nine-candidate list surfaces
> at open, the assistant recommends
> one option with rationale, the
> user confirms or redirects. Once
> §5.a locks, §5.b–§5.h
> planning-time decisions get
> drafted with confirm-as-
> recommended posture expected
> (streak 85 → 86 across eleven
> consecutive milestones).

## First thing SESSION_160 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -5` — top
  should be the M19.6 close-out
  commit.
- `python3 manage.py test dealer_ai`
  → **4,679 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **153 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc
  --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. Present the M20 candidate list

Nine candidates surfaced across M18
retrospective §9 + M19 retrospective
§9 + §0.a M19.6 decision 2 expansion.
Present each with a two-sentence
scope summary + operator pain
resolved + dependency notes, then
present the recommendation.

**Carry-forward candidates:**

- **Candidate T** — process real
  tester feedback (M18.5 CSV
  export). Gated on Chris running
  tester sessions between M19 close
  and M20.0 open.
- **Candidate U** — hosted-demo
  substrate (public self-serve
  signup). Gated on willingness to
  hand demo stores to operators
  Chris doesn't already know.
- **Candidate A** — return to
  accounting stream (M18
  retrospective's designated M20
  slot). Multiple accounting sub-
  candidates listed in
  `MILESTONE_18_RETROSPECTIVE.md` §8.
- **Candidate D** — demo-aware LLM
  router / cost caps (M18.1 §0.a
  decision 1 deferral).
- **Candidate C** — F&I chargeback
  substrate (M18.2 §0.a decision 1
  deferral).

**New from M19 retrospective:**

- **Candidate P** — onboarding UX
  polish (prospect intake UI,
  checklist progress bar,
  terminate-flow refinements).
  Intentionally distinct from
  Candidate J.
- **Candidate L** — first-live-
  pilot staging dry-run (codify
  M19.5 dry-run against real
  staging DB with a real pilot
  dealer). Could bundle with
  Candidate J.
- **Candidate M** — multi-operator
  support (`IsPlatformOperator`
  permission class). **Breaks the
  zero-drift streak with intent.**
  Gated on a second operator
  actually being introduced.

**New at M19.6 per §0.a decision 2:**

- **Candidate J — Operational
  Journey Validation (Playwright
  acceptance testing).** Build
  durable Playwright acceptance
  suites executing real dealership
  workflows against the M18 demo
  stores + M19 pilot substrate.
  Representative journeys: owner
  morning review, sales manager
  daily startup, recon workflow,
  office / accounting workflow,
  BHPH collections workflow,
  pilot onboarding journey.
  Establishes executable
  operational acceptance tests as
  part of the milestone completion
  contract. **Intentionally
  distinct from Candidate P** —
  the objective is business-
  workflow validation, not UI
  regression testing.

### 3. Recommend a target for §5.a

Ground the recommendation in:

- Operator pain resolved by that
  candidate.
- Dependencies on already-shipped
  substrate.
- Deferred items with re-entry
  paths.
- Whether the candidate blocks
  future milestones or is blocked
  by them.

Present with rationale + trade-
offs; expect user confirmation or
a redirection to a different
candidate.

### 4. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the standard
six-to-eight load-bearing decisions
(architecture / ownership /
representation / safety / UI /
docs / validation-contract) with
recommendations for confirm-as-
recommended. Expected streak
extension: 85 → **86** planning-
time as-recommended M5.1 → M20.0
across eleven consecutive
milestones.

### 5. Expand the M20 planning skeleton

`docs/roadmap/MILESTONE_20_PLANNING.md`
exists as a draft skeleton
(SESSION_159 M19.6 close-out).
SESSION_160 expands to full active
memo shape (§1 business context +
§2 primitives to extend + §3
deferrals + §5 load-bearing
decisions + §7 increment
sequencing) analogous to
`MILESTONE_18_PLANNING.md` /
`MILESTONE_19_PLANNING.md`.
Frontmatter `status: draft` →
`status: active`; `milestone_name`
populated from §5.a lock.

## Non-goals for SESSION_160

- ❌ Do NOT ship any backend or
  frontend code — planning-only
  session.
- ❌ Do NOT open any implementation
  increment — M20.1 is a separate
  session.
- ❌ Do NOT force-push or amend
  earlier commits.
- ❌ Do NOT modify M1-M19 shipped
  surface.

## Baseline expected at close

Backend + frontend unchanged from
M19 close. Only planning docs
change.

## NEXT TASK

Start SESSION_160 with (a)
starting-state verification, (b)
presenting the nine-candidate list
with recommendation + rationale
for one, (c) awaiting user
confirmation of §5.a, (d) drafting
§5.b–§5.h with confirm-as-
recommended posture, (e)
expanding the M20 planning
skeleton into a full active memo.
Ship the M20.0 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_20_PLANNING.md`
   (skeleton — expanded at
   SESSION_160)
6. `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
   §9 (candidate list source of
   truth)
7. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
   §8 + §9 (carry-forward
   candidates)
8. `docs/CAPABILITY_MATRIX.md` §7t
   (M19 shipped surface)
9. `docs/handoffs/SESSION_159_m19_inc6_close.md`
   (this milestone's close-out)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_159 — Milestone 19 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,679 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 153 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  **M19**. M20 target
  selection pending
  (SESSION_160).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages + seven M12
  packages + `services/
  accounting/` (seven modules) +
  `services/demo_store/` (ten
  modules including briefs
  package; M19.1 outbound-guard
  refactor) +
  `services/pilot_onboarding/`
  (six modules; M19.2 wrapper +
  M19.4 bytes-mode fix).
- **Frontend surfaces:**
  `<PilotOnboardingSection>`
  embedded in `/dealer-ai-admin`
  since M19.4.
- **Tenancy carriers:** **52**.
- **Permission classes:**
  **7 actual** — zero-drift
  streak **nineteen consecutive
  milestones** (M10 → M19.5).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 19 status:**
  SHIPPED (SESSION_159 close-out
  landed all documentation +
  status flips + M20 skeleton).
