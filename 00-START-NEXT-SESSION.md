---
state: active
date: 2026-08-03
last_session_shipped: SESSION_169
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
milestone_21_status: in-progress
next_session: SESSION_170
next_milestone: 21
next_milestone_name: "Operational Surface Completion"
next_increment: 5
next_increment_name: "M21.5 — Close-out (retrospective + capability matrix + M22 skeleton + coordinated push)"
---

# Next session — SESSION_170 · Milestone 21 · Increment 5 (M21.5 — close-out)

> **Milestone 21.3 shipped at
> SESSION_169** — second anchor
> implementation combined with the
> M21-conditional cadence CONFIG
> scope. Three previously wrapper-
> only endpoints (`createBeBack`,
> `createCadence`, `pauseCadence`)
> now have component-level
> consumers on the operator UI.
> `RecordBeBackForm` on
> `DealerAiSalesBeBacks.tsx`;
> `CadenceConfigPanel` (create +
> pause-by-id + inline-pause) on
> `DealerAiSalesFollowUps.tsx`.
> Extended sales-manager seed with
> a stable 24hr cadence for pause
> testing. Extended daily-startup
> journey with three new sub-steps
> covering all three new endpoints.
>
> **Backend:** 4,758 → 4,761 pass.
> **Frontend Vitest:** 171 → 180
> pass (+9 new tests).
> **Acceptance suite:** 6 journeys
> (sales_manager daily startup
> extended; verified locally 7/7
> pass in 1.1s).
>
> **SESSION_170 opens M21.5 — the
> close-out increment.** Docs-only:
> capability matrix update,
> retrospective, M22 skeleton,
> IMPLEMENTATION_ROADMAP amendment,
> M21.1 audit regeneration to
> reflect new coverage, coordinated
> push per M18.6 / M19.6 / M20.5.

## First thing SESSION_170 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  should be the M21.3 commit.
- `python3 manage.py test dealer_ai`
  → **4,761 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **180 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `cd acceptance && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Regenerate the M21.1 audit artifact

Rerun the audit tooling to reflect
new coverage:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Expected changes vs. the M21.1
snapshot:

- **BHPH write path (7
  endpoints):** move from
  `M21-anchor` → `covered` (the
  bhphApi.ts wrappers now exist
  AND `DealerAiBhphNoteDetail.tsx`
  imports the components that
  use them).
- **Be-back CREATE (1
  endpoint):** move from
  `M21-anchor` → `covered`
  (RecordBeBackForm imported by
  `DealerAiSalesBeBacks.tsx`).
- **Follow-up cadence CONFIG (2
  endpoints):** move from
  `M21-conditional` → `covered`
  (CadenceConfigPanel imported
  by `DealerAiSalesFollowUps.tsx`).
- **Total coverage delta:**
  ~96 → ~106 covered; ~57 → ~47
  backend-only.

Review the regenerated artifact
before commit — if the
recommender misclassifies any
new row (e.g. a new
`defer-candidate-O2` that's
actually intentional-omission),
edit the disposition manually
per the M21.1 human-review
posture.

### 3. Verify the full acceptance suite passes locally

```bash
rm -f backend/db.acceptance.sqlite3
cd acceptance
npx playwright test
```

Expected: **12 passed** (6 setup
projects + 6 journeys) matching
the M20 close baseline shape.
The two extended journeys
(BHPH + sales_manager) plus the
four unchanged journeys all
pass. If a journey fails, address
as §0.a M21.5 amendment before
close-out commit.

### 4. Ship the capability matrix update

Add **§7v — Milestone 21 shipped
surface** to
`docs/CAPABILITY_MATRIX.md`:

- New surface: 10 frontend
  components across two domains
  (bhph/ + sales/), 7 new
  bhphApi.ts write wrappers,
  extended seeds (2), extended
  journey (1 BHPH re-expanded +
  1 sales_manager extended), 1
  new operator-invoked audit
  script + audit artifact.
- Backend delta: 4,755 → 4,761
  (+6 seed coverage tests
  across BHPH + sales_manager
  extensions).
- Frontend delta: 153 → 180
  (+27 new tests across 7
  component test files).
- Acceptance delta: 6 → 6
  journeys (2 extended, 4
  unchanged).
- Zero-drift streak: **twenty
  → twenty-one** consecutive
  milestones (M10 → M21).
- Planning-time streak: **86
  → 87** as-recommended across
  twelve consecutive milestones
  (M10 → M21).

### 5. Ship the M21 retrospective

`docs/roadmap/MILESTONE_21_RETROSPECTIVE.md`.
Structure matches M18-M20
retrospectives:

- §1 What shipped (summary).
- §2 What worked well.
- §3 What was harder than
  expected.
- §4 Deferred items (M21-
  conditional cadence CONFIG
  landed; M21.4 skipped;
  defer-candidate-O2 endpoints
  carried forward).
- §5 Lessons learned.
- §6 Deltas against planning
  memo estimates.
- §7 Governing-contract
  validation.
- §8 Unblocks / new candidates
  surfaced by M21 work.
- §9 Standing M22 question
  (should M22 pick another
  OSC iteration or the return-
  to-accounting candidate?).

### 6. Draft the M22 planning skeleton

`docs/roadmap/MILESTONE_22_PLANNING.md`
with frontmatter `status: draft`.
Candidate list refreshed from
M21 retrospective §8 + §9 +
carry-forwards:

- **Elevated:** Candidate A
  (return to accounting stream)
  — now four consecutive
  milestones diverging (M18 →
  M21); the M21 audit surfaced
  three accounting endpoints
  (journal-entry-reverse +
  snapshot create/list/retrieve)
  with `defer-domain-milestone`
  disposition — clean scope
  target.
- **Elevated:** Candidate O2
  (next OSC iteration) —
  regenerated M21.1 audit
  should show ~47 backend-only
  endpoints available for
  future OSC scope.
- **Gated:** T (tester
  feedback), U (hosted demo),
  L (staging pilot dry-run),
  M (multi-operator) —
  unchanged from M21.0.
- **Deferred pending
  evidence:** D (LLM router),
  C (F&I chargeback) — same
  posture as M20/M21.

### 7. Update IMPLEMENTATION_ROADMAP

`docs/roadmap/IMPLEMENTATION_ROADMAP.md`:
- Mark M21 as shipped.
- Add M21 to shipped-milestones
  list with completion note.
- **Formalize the DoD amendment**
  (M21.0 §5.f Option B) in the
  roadmap's milestone-contract
  section: every future customer-
  facing milestone MUST add or
  update at least one Playwright
  operational journey OR
  explicitly document in §3 why
  no journey change is required.

### 8. Ship the M21.5 handoff

`docs/handoffs/SESSION_170_m21_inc5_close.md`.
Match the M20.5 handoff shape:
what shipped, streak update,
what's next, anchors.

### 9. Refresh entry point + coordinated push

- Overwrite
  `00-START-NEXT-SESSION.md`
  for SESSION_171 / M22.0
  (planning refinement + target
  selection).
- Create the coordinated close-
  out commit that lands all
  M21.5 documentation together
  (matches M18.6 / M19.6 /
  M20.5 pattern).
- **Push** the M21 branch to
  `origin/main` — this is the
  first M21 push. Six commits:
  M21.0 planning + M21.1 audit
  + M21.2 BHPH + M21.3 be-back
  + cadence + M21.5 close-out.

## Non-goals for SESSION_170

- ❌ Do NOT ship any new frontend
  code — M21.5 is docs-only
  close-out.
- ❌ Do NOT ship any new backend
  code (except possibly a tweak
  to the audit script if the
  regen surfaces a false-positive
  disposition worth fixing;
  guard as §0.a M21.5).
- ❌ Do NOT modify shipped seed
  commands or acceptance
  journeys unless a regression
  surfaces during the local
  full-suite run.
- ❌ Do NOT open M22 planning
  §5.a — that's SESSION_171's
  work.
- ❌ Do NOT force-push or amend
  earlier commits.
- ❌ Do NOT bundle any additional
  scope items from the audit —
  M21 scope is locked.

## Baseline expected at close

- **Backend:** 4,761 pass
  (unchanged from M21.3 close).
- **Frontend Vitest:** 180 pass
  (unchanged).
- **Acceptance suite:** 6
  journeys (unchanged; full
  suite verified locally).
- **Migrations:** `0001`–`0048`
  (unchanged).
- **Tenancy carriers:** 52
  (unchanged).
- **Permission classes:** 7
  (zero-drift streak extends
  **twenty → twenty-one**
  consecutive milestones at
  M21 close).
- **Frontend operator
  routes:** 20 (unchanged).
- **DRF admin surface:** 113
  (unchanged).

## NEXT TASK

Start SESSION_170 with (a)
starting-state verification, (b)
regenerate the audit artifact
+ human-review dispositions,
(c) verify full acceptance
suite locally, (d) capability
matrix §7v, (e) retrospective,
(f) M22 planning skeleton, (g)
IMPLEMENTATION_ROADMAP update
+ DoD amendment formalization,
(h) M21.5 handoff, (i) entry
point refresh, (j) coordinated
close-out commit + **first M21
push**.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (active — §0.a M21.1 scope
   lock recorded)
6. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (regenerate at M21.5 open)
7. `docs/handoffs/SESSION_169_m21_inc3_be_back_cadence.md`
   (M21.3 shipped)
8. `docs/handoffs/SESSION_168_m21_inc2_bhph_write.md`
9. `docs/handoffs/SESSION_167_m21_inc1_audit.md`
10. `docs/handoffs/SESSION_166_m21_inc0_planning.md`
11. `docs/CAPABILITY_MATRIX.md` §7u

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_169 — Milestone 21 · Increment 3 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,761 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 180 pass** (up from
  171 at M21.2 close; +9 M21.3
  component tests).
- **Frontend (prod):** NONE.
- **Acceptance workspace
  (local):** Playwright 1.49 +
  TS 5.6 operational. **Six
  journeys** — BHPH re-expanded
  at M21.2, sales_manager
  extended at M21.3, other four
  unchanged. M21.3 journey
  verified locally 7/7 pass
  (1.1s).
- **Acceptance (CI):** last
  green run predates M21
  commits. First M21 CI run
  triggers at M21.5 coordinated
  push.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  **M20**. **M21 in progress
  (M21.0 + M21.1 + M21.2 + M21.3
  shipped locally). M21.5 close-
  out next.**
- **DRF admin surface:** 113
  endpoints (unchanged).
- **Frontend operator routes:**
  20 (unchanged).
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all
  M1–M20 packages unchanged.
  M21 adds zero service verbs.
- **Frontend surfaces:** M12.7
  BHPH collector dashboard +
  M11.5/M11.6 sales pages
  extended with M21 write
  panels. 10 new components
  under
  `frontend/src/components/bhph/`
  (7) and
  `frontend/src/components/sales/`
  (3, counting bundled sub-
  components).
- **Tenancy carriers:** 52
  (unchanged).
- **Permission classes:** 7
  actual — zero-drift streak
  twenty consecutive milestones
  (M10 → M20). M21 targets
  extension to twenty-one at
  M21.5 close.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 21 status:** IN
  PROGRESS. M21.0 (planning) +
  M21.1 (audit + scope lock) +
  M21.2 (BHPH write-side UI) +
  M21.3 (Be-back CREATE +
  cadence CONFIG) shipped
  locally. Four commits ahead
  of `origin/main`; M21.5
  will land the fifth and
  coordinated push per
  M18/M19/M20 cadence.
- **Audit tooling:**
  `backend/dealer_ai/scripts/audit_operational_surface.py`
  ready for regen at M21.5
  open to reflect the coverage
  gains from M21.2 + M21.3.
- **Planning-time streak:**
  **87 as-recommended M5.1 →
  M21.0** across twelve
  consecutive milestones (M10 →
  M21). No new §5 decisions in
  M21.2, M21.3, or M21.5
  (execution/close-out
  sessions); streak preserved.
- **DoD amendment (formalized
  at M21.0 §5.f Option B):**
  every future customer-facing
  milestone must add or update
  at least one Playwright
  operational journey, or
  explicitly document in §3 why
  no journey change is
  required. M21.2 + M21.3 both
  satisfied via journey
  extensions. Formal amendment
  text lands in
  IMPLEMENTATION_ROADMAP at
  M21.5.
- **Governing contract
  (Candidate O):** every M21
  shipped surface maps to an
  already-shipped backend
  capability, closes a missing
  operator-facing UI, adds or
  extends a Playwright
  operational journey, and is
  not generic UX polish.
