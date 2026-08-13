---
title: "SESSION_168 handoff — Milestone 21 · Increment 2 (M21.2 — BHPH write-side UI + journey extension)"
status: historical
type: handoff
date: 2026-08-03
session: 168
milestone: 21
milestone_status: in-progress
milestone_name: "Operational Surface Completion"
increment: 2
increment_status: shipped
commit: TBD
---

# SESSION_168 — Milestone 21 · Increment 2 (M21.2 — BHPH write-side UI + journey extension)

## What shipped

First M21 anchor implementation.
BHPH collector daily-book workflow
now reachable end-to-end through
the shipped product. Seven backend
endpoints previously reachable only
via curl / Postman / Django shell
now have operator-facing UI on the
M12.7 collector dashboard surface.

**Seven new `bhphApi.ts` write
wrappers** —
`frontend/src/lib/bhphApi.ts`
extended from read-only to full
read+write. Typed request payloads
match the backend serializers
verbatim:

- `recordPromiseToPay(notePk,
  payload)` → POST
  `/admin/bhph-notes/{pk}/promises/`
- `markPromiseKept(promisePk,
  payload)` → POST
  `/admin/bhph-promises/{pk}/mark-kept/`
- `markPromiseBroken(promisePk,
  payload={})` → POST
  `/admin/bhph-promises/{pk}/mark-broken/`
- `logCollectionContact(notePk,
  payload)` → POST
  `/admin/bhph-notes/{pk}/contacts/`
- `initiateRepossession(notePk,
  payload)` → POST
  `/admin/bhph-notes/{pk}/repossessions/`
- `markRepossessionRecovered(reposPk,
  payload={})` → POST
  `/admin/bhph-repossessions/{pk}/mark-recovered/`
- `markRepossessionReIntaked(reposPk,
  payload)` → POST
  `/admin/bhph-repossessions/{pk}/mark-re-intaked/`

**Seven new frontend components**
under
`frontend/src/components/bhph/`
(consolidated into 5 files to keep
tightly-coupled row actions
together):

- `RecordPromiseToPayForm.tsx` —
  attaches to Promises card;
  fields: promised_at,
  promised_amount,
  promised_reason enum, notes.
- `PromiseRowActions.tsx` —
  bundles `MarkKeptPromiseButton`
  (with `PaymentPickerModal`) +
  `MarkBrokenPromiseButton` (with
  confirm modal for optional
  reason notes). Buttons
  disabled when promise is
  already terminal.
- `LogCollectionContactForm.tsx`
  — attaches to Contacts card;
  fields: contacted_at,
  channel enum, outcome enum,
  notes. Backend FDCPA scrub
  applies post-submit.
- `InitiateRepossessionForm.tsx`
  — attaches to Repossessions
  card; fields: ordered_at,
  agent_name, notes.
- `RepossessionRowActions.tsx`
  — bundles `MarkRecoveredButton`
  (recovery_at + location +
  notes) + `MarkReIntakedButton`
  (condition_report_id +
  notes; button disabled when
  state ≠ `recovered`). Both
  wrap confirm modals.

All components wired into
`DealerAiBhphNoteDetail.tsx`.
State updates optimistically merge
the returned projection back into
the corresponding sub-list; a full
re-fetch happens on route change
per existing `useEffect`. Zero new
routes; zero new pages. Attachment
posture matches the M17 §6 lesson
6 + M19.4 in-place-page extension
convention.

**18 new Vitest tests** across five
test files
(`RecordPromiseToPayForm.test.tsx`,
`PromiseRowActions.test.tsx`,
`LogCollectionContactForm.test.tsx`,
`InitiateRepossessionForm.test.tsx`,
`RepossessionRowActions.test.tsx`).
Cover submit + validation + error
paths + button handlers + confirm
dialogs + button-disabled states.
Frontend Vitest baseline **153 →
171 pass**.

**Extended
`seed_journey_bhph_collections_workflow`**
with three new M21.2 fixtures on
top of the M20.4 base:
- A second `BhphPromiseToPay` in
  `promised` state (fixture for
  the mark-broken journey step).
- A second `Repossession` pre-
  transitioned to `recovered`
  (fixture for the mark-re-intaked
  journey step).
- One complete `ConditionReport`
  for the fixture vehicle
  (referenced by the mark-re-
  intaked step).

Seed remains idempotent + tenant-
scoped; `--reset` correctly cleans
up including the ConditionReport.
Backend seed tests extended from
15 → 17 (three new coverage
tests: promised-state promise,
recovered-state repossession,
complete ConditionReport; also
updated the existing counts +
idempotency tests).

**Re-expanded
`acceptance/journeys/bhph/collections_workflow.spec.ts`**
from the M20.4 read-only narrowed
scope to full write coverage. Nine
journey steps exercise all seven
new endpoints:

1. Portfolio landing (unchanged
   from M20.4).
2. Note detail page load
   (unchanged).
3. Baseline child counts
   captured via API.
4. **Record PtP** via form →
   assert promise count grows by
   exactly one.
5. **Mark broken** on seeded
   `promised`-state promise via
   row action → assert state
   transitions to `broken`.
6. **Log contact** via form →
   assert contact count grows by
   exactly one.
7. **Initiate repossession**
   via form → assert repo count
   grows by exactly one.
8. **Mark recovered** on seeded
   `ordered`-state repo → assert
   state transitions to
   `recovered`.
9. **Mark re-intaked** on
   seeded `recovered`-state repo
   with the seeded
   ConditionReport ID → assert
   state transitions to
   `re_intaked`.

Assertions target business state
via the M12 admin API (promise
state, repo state, count deltas)
— not DOM state. Nine new
assertion helpers added to
`acceptance/support/assertions/bhph.ts`
(find-by-state row locators,
condition-report locator, state
transition assertions, child-
count fetcher).

Journey verified locally with
Playwright: **7/7 setup + journey
tests pass** (846ms journey
execution).

## Baselines

- **Backend:** 4,755 → **4,758
  pass**, 1 skipped, 0 fail
  (+3 new seed coverage tests
  minus one merged into an
  existing test).
- **Frontend Vitest:** 153 →
  **171 pass** (+18 new
  component tests).
- **Acceptance suite:** 6
  journeys (BHPH re-expanded
  from read-only narrow to full
  write coverage; other 5
  unchanged).
- **Migrations:** `0001`–`0048`
  (unchanged — zero new
  migrations per M21 §0
  posture).
- **Tenancy carriers:** 52
  (unchanged).
- **Permission classes:** 7
  (unchanged — zero-drift
  streak at twenty consecutive
  milestones; on track for
  twenty-one at M21 close).
- **DRF admin surface:** 113
  (unchanged — every M21.2 UI
  attaches to an already-shipped
  endpoint).
- **Frontend operator routes:**
  20 (unchanged — every M21.2
  component attaches to
  `DealerAiBhphNoteDetail.tsx`
  in place).
- **Celery-beat task
  families:** 10 (unchanged).

## Governing-contract compliance

Every M21.2 shipped surface
satisfies the four Candidate O
conditions from M21.0:

1. **Maps to already-shipped
   backend capability** — all 7
   endpoints ship since M12.
2. **Closes a missing operator-
   facing UI** — every endpoint
   was previously reachable
   only via curl / Postman /
   Django shell (per M21.1
   audit).
3. **Adds or extends a
   Playwright operational
   journey** — journey re-
   expanded end-to-end; DoD
   amendment (§5.f) satisfied.
4. **Is not generic UX polish**
   — every component maps 1:1
   to a backend verb + missing
   form/button/action.

## Reconciliations against M21.1 audit

The audit surfaced the exact 7-
endpoint BHPH write scope this
increment ships. No new gaps
surfaced during implementation.
The audit artifact
(`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`)
can be regenerated after this
commit to reflect the reduced
backend-only count (57 → 50, if
the audit correctly detects the
new wrappers + component imports).

## What's next: SESSION_169 M21.3 — Be-back CREATE + Follow-up cadence CONFIG

Per `MILESTONE_21_PLANNING.md`
§7 M21.3:

- **Be-back CREATE** (1 endpoint)
  — `RecordBeBackForm` attached
  to `DealerAiSalesBeBacks.tsx`.
  Wrapper `createBeBack` already
  exists in `salesApi.ts` (M11.6);
  the gap is component-level
  consumption per the M21.1
  audit's wrapper-only tagging.
- **Follow-up cadence CONFIG**
  (2 endpoints) —
  `CreateCadenceForm` +
  `PauseCadenceButton` attached
  to `DealerAiSalesFollowUps.tsx`
  or an adjacent cadence-config
  panel. Wrappers `createCadence`
  + `pauseCadence` already
  exist; same wrapper-only
  gap.
- Vitest coverage.
- Extended
  `seed_journey_sales_manager_daily_startup`
  (or new
  `seed_journey_sales_manager_cadence_config`)
  + backend tests.
- Extended
  `acceptance/journeys/sales_manager/daily_startup.spec.ts`
  or new
  `sales_manager/cadence_config.spec.ts`
  per §5.e Option C decision
  made at M21.3 open.

**Backend baseline target at
M21.3 close:** ~4,770–4,780
pass. **Frontend Vitest:** ~180–
185 pass. **Acceptance suite:**
6 journeys (extended) or 7 (if
cadence config gets its own
journey).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_21_PLANNING.md`
6. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
7. `docs/handoffs/SESSION_167_m21_inc1_audit.md`
8. `docs/handoffs/SESSION_166_m21_inc0_planning.md`
9. `docs/CAPABILITY_MATRIX.md` §7u
   (M20 shipped surface)
