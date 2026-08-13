---
title: "SESSION_151 handoff — Milestone 18 · Increment 5 (M18.5 — Briefs + feedback endpoint + CSV exporter)"
status: historical
type: handoff
date: 2026-08-02
session: 151
milestone: 18
milestone_status: in-progress
milestone_name: "Demo Store Simulation + Pilot Validation Readiness"
increment: 5
increment_status: shipped
commit: 957a7ba
---

# SESSION_151 — Milestone 18 · Increment 5 (M18.5 — Briefs + feedback endpoint + CSV exporter)

## What shipped

Single backend increment per
`MILESTONE_18_PLANNING.md` §7 M18.5.
Ships the operator-facing surfaces
the M18.1 substrate anticipated —
role-based daily briefs for every
archetype + TesterFeedback POST
endpoint + end-to-end CSV export.

**§0.a M18.2 decision 1 continues
to apply** — Chargeback still
deferred. The retail_subprime and
floor_planned accounting briefs
mention the chargeback deferral
explicitly; the F&I audit scenario
will surface at a later milestone
if operator evidence justifies.

## Delivered

**13 hand-written daily briefs**
in `services/demo_store/briefs/`:

- **`retail_subprime/`** (4 briefs):
  owner, sales_manager, recon,
  accounting.
- **`floor_planned/`** (4 briefs):
  owner, sales_manager, recon,
  accounting. **The recon brief is
  the $825 overrun intervention
  centerpiece** — walks the tester
  through the F-150 XLT SuperCrew
  (FP-01) transmission scenario:
  timeline from initial $600
  authorization to $1,425 revised
  estimate, verbal approval,
  vendor communications history,
  ledger + work-order + vendor
  comms all pointing at the same
  $1,425 number.
- **`bhph/`** (5 briefs): owner,
  sales_manager, recon,
  accounting, collector. **The
  accounting brief walks the M16
  detector timing story** — recent
  payments with `posted_at=NULL`
  flow into the GL after the 11:00
  detector cycle; freeze pre- vs
  post-11:00 to see the difference.
  **The collector brief exercises
  the full BHPH collection
  workflow** — promise-to-pay
  states (promised / kept /
  broken), CollectionContact log,
  repossession detail escalation.

Each brief follows the standard
structure per §Store-story
coherence:

- What happened before login.
- What to accomplish today.
- What's intentionally
  incomplete.
- Which shipped capabilities
  help.
- What successful completion
  looks like.
- What's discoverable without a
  guided click path.

**Brief loader** —
`services/demo_store/briefs/__init__.py`:

- `BRIEF_ROLES` fixed vocab (owner
  + sales_manager + recon +
  accounting + collector).
- `Brief` frozen dataclass
  (archetype, role, content).
- `BriefNotFoundError` domain
  exception.
- `list_briefs(archetype) ->
  tuple[str, ...]` — returns only
  roles that ship for the
  archetype (retail_subprime +
  floor_planned have no collector
  brief).
- `get_brief(archetype, role) ->
  Brief` — reads the .md file at
  request time.
- Package `__init__.py` extended
  with new exports.

**TesterFeedback POST endpoint** —
new `views_demo_store.py`:

- Path: `POST
  /admin/demo-store/feedback/`.
- Reuses
  `IsSalesManagerOrOwnerAtActiveDealership`
  — **zero-drift streak extends
  to fourteen consecutive
  milestones now** (M10 → M18.5).
- Body validated by
  `TesterFeedbackCreateRequestSerializer`
  with category vocab check
  against
  `TESTER_FEEDBACK_CATEGORY_CHOICES`.
- **Refuses non-demo
  dealership with 403** —
  descriptive message explaining
  that TesterFeedback submissions
  are only accepted against
  demo dealerships. Belt-and-
  suspenders with M18.1 service-
  layer discipline.
- Returns 201 with the
  persisted TesterFeedback
  projection.

**URL registration** — one new
pattern in `urls.py`. DRF admin
surface **107 → 108**.

**Test coverage — 24 focused
tests** in new
`tests/test_m185_briefs_and_feedback.py`:

- **Brief role vocab (1):**
  exact-set equality.
- **`list_briefs` (4):**
  retail_subprime lists 4;
  floor_planned lists 4; bhph
  lists 5; unknown archetype
  raises.
- **`get_brief` matrix (4):**
  every listed (archetype, role)
  yields a loadable Brief with
  >100 chars content; unknown
  role raises;
  retail_subprime has no
  collector brief; floor_planned
  has no collector brief.
- **Brief content shape (5):**
  every brief starts with H1;
  every brief names its
  scenario slug; every brief
  contains the six standard
  section markers;
  floor_planned/recon names
  the overrun ($1,425 +
  FP-01); bhph/accounting
  names the 11:00 detector +
  posted_at.
- **POST endpoint happy path
  (2):** 201 + projection;
  blank referenced_route
  accepted.
- **POST endpoint guards
  (4):** 400 missing category;
  400 unknown category; 403
  non-demo dealership; 403
  non-permitted role
  (advisor).
- **Tenant scoping (1):**
  each dealership only sees
  its own feedback.
- **CSV export end-to-end
  (1):** submit via endpoint,
  export via CLI, assert
  header + row content.
- **Endpoint count (1):**
  DRF admin surface ≥108.
- **Zero-drift permission-
  class set (1):** streak
  fourteen consecutive
  milestones.

## Baseline delta

- **Backend: 4,514 → 4,538
  pass**, 1 skipped, 0 fail.
  **+24 tests, 0 regressions.**
  Exceeded 15-20 target by 4.
- Migrations 0043-0047
  (unchanged).
- Tenancy carriers **50**
  (unchanged).
- **DRF admin surface 107 →
  108** (+1 feedback POST).
- Frontend Vitest **140**
  (unchanged — no frontend at
  M18.5; feedback capture
  form deferred per §5.f
  evidence-driven boundary).
- Frontend operator routes
  **20** (unchanged).
- Permission classes **7** —
  **zero-drift streak
  fourteen consecutive
  milestones** (M10 →
  M18.5).
- Celery-beat task families
  **10** (unchanged).

## Streak update

**77 planning-time as-recommended
M5.1 → M18.0** (unchanged —
M18.5 is implementation-time).
§0.a decisions continue to hold.

## What's next: SESSION_152 M18.6 close-out

Per `MILESTONE_18_PLANNING.md` §7
M18.6. Documentation-only per
M10.8 / M11.7 / M12.8 / M13.4 /
M14.5 / M15.2 / M16.2 / M17.3
precedent:

- Write
  `docs/roadmap/MILESTONE_18_
  RETROSPECTIVE.md`.
- Add
  `docs/CAPABILITY_MATRIX.md`
  §7s section describing the
  M18 shipped surface.
- Add
  `docs/roadmap/IMPLEMENTATION_
  ROADMAP.md` §Milestone 18
  SHIPPED entry.
- Flip
  `docs/roadmap/MILESTONE_18_
  PLANNING.md` frontmatter
  `active` → `shipped`.
- Draft
  `docs/roadmap/MILESTONE_19_
  PLANNING.md` skeleton per
  standing user directive.
- Overwrite
  `00-START-NEXT-SESSION.md`
  with M19.0 priority.
- Coordinated commit landing
  all M18.6 docs together.

**Backend baseline at M18.6
close:** 4,538 pass (unchanged
— docs only). Frontend Vitest:
140 pass (unchanged).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_PLANNING.md`
6. `docs/handoffs/SESSION_150_m18_inc4_bhph_archetype.md`
7. `docs/handoffs/SESSION_149_m18_inc3_floor_planned_archetype.md`
8. `docs/handoffs/SESSION_148_m18_inc2_retail_subprime_archetype.md`
9. `docs/handoffs/SESSION_147_m18_inc1_backend_substrate.md`
10. `docs/CAPABILITY_MATRIX.md` §7r
11. `backend/dealer_ai/services/demo_store/briefs/`
    (13 markdown briefs — the
    operator-facing surface M18
    delivered)
