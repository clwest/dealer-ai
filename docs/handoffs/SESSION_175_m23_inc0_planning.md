---
title: "SESSION_175 handoff — Milestone 23 · Increment 0 (M23.0 — planning refinement + target selection)"
status: historical
type: handoff
date: 2026-08-03
session: 175
milestone: 23
milestone_status: in-progress
milestone_name: "BHPH Origination + Payment Intake"
increment: 0
increment_status: shipped
commit: TBD
---

# SESSION_175 — Milestone 23 · Increment 0 (M23.0 — planning refinement + target selection)

## What shipped

Planning-only session per the M10.0
/ M11.0 / M12.0 / M13.0 / M14.0 /
M15.0 / M16.0 / M17.0 / M18.0 /
M19.0 / M20.0 / M21.0 / M22.0
precedent. Full memo expansion from
the M22.4 skeleton + all **eight**
§5 load-bearing decisions resolved
at open.

**§5.a → O2 (BHPH note origination
+ payment intake sub-scope)
confirmed at open** per the primary
operational-coverage lens ("which
candidate most increases operational
coverage for a dealership
employee?") established at M22 close
as durable guidance. Milestone name:
**"BHPH Origination + Payment
Intake."** Completes the BHPH
lifecycle bookends from M12 backend
+ M12.7 read UI + M20.4 Playwright
coverage + M21.2 write-side UI for
collections. Two anchor endpoints:
`admin-bhph-note-create` (POST
`admin/bhph-notes/`) +
`admin-bhph-payment-create` (POST
`admin/bhph-notes/<pk>/payments/`).
Both empirically verified as backend-
only at M23.0 open — neither has a
wrapper in `bhphApi.ts` today; both
require curl / Django shell.
Candidates H (test-hygiene), A2
(accounting iteration), other O2
sub-scopes (F&I, lead-source
intake, deal-writeup, test-drive),
and T/U/L/M/D/C/P/G all deferred
with re-entry paths preserved per
discovery rule.

**Empirical M23.0 verification
surfaced NEW audit false-positive
class** distinct from M22.1's
variable-first URL assembly:
**HTTP-verb-agnostic URL-prefix
matching**. Audit row 123
(`admin-bhph-note-create`) claims
coverage via `getBhphNote` — but
that's the GET wrapper for the
pk-suffixed path, not the POST
create endpoint. The audit
script matches URL patterns
without discriminating HTTP verb.
Grep-verified: no `createBhphNote`
in `bhphApi.ts`. Ships M23.1
targeted fix per §5.d Option A
under a ~2-hour budget guard.

**§5.b–§5.h all confirmed as-
recommended.** Streak extends to
**89 planning-time as-recommended
M5.1 → M23.0** across **fourteen
consecutive milestones now** (M10
+ M11 + M12 + M13 + M14 + M15 +
M16 + M17 + M18 + M19 + M20 + M21
+ M22 + M23).

**Governing contract inherited
from M21 (UI-creation shape).** M23
returns to the M21 Candidate O
governing contract after M22's
validation-shape milestone. Every
M23 surface (a) maps to shipped
backend + missing frontend,
(b) closes a missing operator-
facing UI, (c) adds or extends a
Playwright operational journey,
(d) is not generic UX polish.

**DoD compliance verified by
construction.** M23.2 ships
`bhph/note_origination.spec.ts`;
M23.3 ships
`bhph/payment_intake.spec.ts`. §3
of the memo names both journey
additions explicitly. The M21.0
§5.f Option B DoD amendment is
satisfied.

**Backend baseline unchanged:**
4,766 pass, 1 skipped, 0 fail.
**Frontend Vitest baseline
unchanged:** 180 pass. Migrations
`0001`–`0048` (unchanged). Tenancy
carriers 52 (unchanged — M23 adds
no tenancy carriers). DRF admin
surface 113 (unchanged — M23 adds
no endpoints). Frontend operator
routes 20 (unchanged — M23 adds
no routes; both new components
attach to existing pages).
Permission classes 7 (unchanged —
zero-drift streak intact at
twenty-two consecutive milestones;
M23 extends to twenty-three at
close). Celery-beat task families
10 (unchanged). Acceptance suite
7 journeys (unchanged — M23.2 +
M23.3 grow count to 9 at close).

## Starting-state verification (this session)

Ran the full M23.0-open checklist
per the M22.4 handoff:

- `git status` — clean.
- `git log --oneline -6` — top
  commit is `8786163` (M22
  durable-lessons carry-forward);
  `origin/main` at the same head.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `cd acceptance && npx tsc
  --noEmit` clean.
- `redis-cli ping` → `PONG`.
- Full backend test suite skipped
  per handoff guidance — no code
  changed since M22.4 verified
  4,766 pass.
- **M22 acceptance CI runs
  verified green:** run
  `30830291129` (M22 shipped push,
  2m8s) + `30831196864` (M22
  durable-lessons carry-forward
  push, 2m3s) both completed
  success. First real M22 CI runs
  passed cleanly.
- **Audit regeneration:** ran
  `python3 -m
  dealer_ai.scripts.audit_operational_surface`
  from `backend/`. Output: **153
  endpoints, 110 covered, 43
  backend-only** — identical to
  M22.4 close. Only diff was two
  rows of non-deterministic
  wrapper-order noise; reverted
  to keep tree clean.

All green. No §0.a M23.0
amendments needed for regressions.

## Empirical discovery during M23.0 open (informs §5.d)

The scope-verification performed
during M23.0 open surfaced NEW
audit false-positive class:

**Finding: HTTP-verb-agnostic
URL-prefix matching.** The audit
script matches URL patterns
without discriminating HTTP verb.
Row 123 of the audit shows
`admin-bhph-note-create` (POST
`admin/bhph-notes/`) as `covered`
via `bhphApi.ts:109 getBhphNote`.
But `getBhphNote` is a GET wrapper
for `admin/bhph-notes/<pk>/` — a
different HTTP verb AND a different
URL path shape (pk-suffixed, not
bare). The URL-prefix match
happens because both endpoints
share the `admin/bhph-notes/`
prefix; the audit script doesn't
verify the wrapper's HTTP verb
matches the endpoint's declared
verb.

**Grep verification:** `grep '^export
(async )?function' bhphApi.ts`
lists all 14 exported wrappers.
None are named `createBhphNote`
or `createBhphPayment`. Both
anchor endpoints are genuinely
backend-only. The audit false-
positive on row 123 misled M22
retrospective §9's assumption
that BHPH origination was
"already covered" — a class of
error that could recur in future
planning without the M23.1
targeted fix.

**Root cause fix approach** (per
§5.d Option A):
- Enhance the audit script to
  extract the HTTP verb from the
  wrapper's helper-call name
  (`authGetJSON` → GET,
  `authPostJSON` → POST,
  `authPatchJSON` → PATCH,
  `authPutJSON` → PUT,
  `authDelete` → DELETE,
  `authPostForm` → POST).
- Compare against the endpoint's
  view callable's HTTP verb
  (declared via `@api_view([...])`
  or the view function's shape).
- Only claim coverage when the
  wrapper's verb matches the
  endpoint's verb.
- Preserves M22.1's
  `_resolve_variable_url` and
  balanced-brace parsing.

## Load-bearing decisions confirmed at M23.0 open

Eight decisions per M22 precedent.
All confirmed as-recommended.

**§5.a — Milestone target
selection.** O2 (BHPH note
origination + payment intake sub-
scope). Reshaped from generic
"O2" per operational-coverage
lens — chose the highest per-
item coverage delta at smallest
scope. Completes the BHPH
lifecycle story.

**§5.b — Component attachment
plan.** Option A — note
origination attaches to
`DealerAiBhphPortfolio.tsx`
(Notes card header CTA + modal);
payment intake attaches to
`DealerAiBhphNoteDetail.tsx` as
a new Payments card matching
Promises/Contacts/Repossessions
sibling pattern. In-place page
extension per M17 §6 lesson 6 +
M21.2 precedent.

**§5.c — Journey folder + shape.**
Option B — two new sibling spec
files under
`acceptance/journeys/bhph/`:
`note_origination.spec.ts` +
`payment_intake.spec.ts`.
Distinct workflow shapes (finance
manager originating vs. collector
recording cash) warrant distinct
specs. `collections_workflow.spec.ts`
stays untouched.

**§5.d — Audit-tool false-
positive side-fix posture.**
Option A — bounded targeted fix
in-scope as M23.1 supporting-
work increment per M22.1
precedent. ~2-hour budget guard.
Explicit non-goal: AST-based
audit rewrite.

**§5.e — Seed command pattern.**
Option A — extend
`seed_journey_bhph_collections_workflow`
additively with vehicle fixture
(origination target) + fresh-
note-with-balance fixture
(payment intake target) +
payment cleanup on re-
invocation. Matches M21 Lesson
4 + M22.2 §5.g Option A.

**§5.f — Baseline verification
approach.** Option B — journey-
as-verifier. Carries forward
from M22.2 §5.f Option B.
Playwright IS the verification;
if the shipped workflow doesn't
complete, the journey fails
loudly. Vitest doesn't
substitute (mocks API layer).

**§5.g — Testid hardening
posture.** Option B —
opportunistic. Carries forward
from M21 §5.g + M22 practice.
Add `data-testid` only where
new M23 journeys need stable
selectors.

**§5.h — Increment sequencing +
completion contract.** Option
B — evidence-sized four-to-
five increments. **M23.0
planning** (this session) +
**M23.1 audit-tool fix**
(supporting work) + **M23.2
note origination UI + journey**
+ **M23.3 payment intake UI +
journey** + **M23.4 close-
out**. Milestone completion
contract: both anchor UIs ship
with passing operational
journeys on `main` CI; audit
correction closes the HTTP-
verb-agnostic false-positive
class; retrospective §9
records the BHPH lifecycle now
operationally complete + M24
next-candidate identified.

## Streak

**89 planning-time as-recommended
M5.1 → M23.0.** Fourteen
consecutive milestones now (M10
+ M11 + M12 + M13 + M14 + M15 +
M16 + M17 + M18 + M19 + M20 +
M21 + M22 + M23) with every §5
decision confirmed as-recommended
at planning-time open.

Historical §5 counts through
M23.0:
- M10 through M17: 6 decisions
  each = 48.
- M18: 7 decisions.
- M19: 8 decisions.
- M20: 8 decisions.
- M21: 8 decisions.
- M22: 8 decisions.
- M23: 8 decisions (§5.a
  target + §5.b–§5.h).
- Total across fourteen
  milestones (M10–M23): 48 +
  7 + 8 + 8 + 8 + 8 + 8 = **95
  §5 decisions**.

The "89 planning-time as-
recommended M5.1 → M23.0"
counter carries the per-
milestone-open invariant
without a single deviation
across the fourteen
consecutive milestones.

**Zero-drift permission-class
streak target for M23 close:**
twenty-two → **twenty-three**
consecutive milestones. M23
introduces zero new permission
classes.

## What's next: SESSION_176 M23.1 audit-tool false-positive fix + artifact refresh

Per `MILESTONE_23_PLANNING.md`
§7 M23.1:

- **Targeted fix** in
  `backend/dealer_ai/scripts/audit_operational_surface.py`
  to discriminate HTTP verb
  between wrapper calls and
  endpoint patterns. Extract
  wrapper verb from helper-call
  name (`authGetJSON` → GET,
  etc.); compare against
  endpoint's view callable's
  declared verb. Only claim
  coverage when verbs match.
- **Optional backend test** for
  the fix. Discretionary at
  M23.1 open per M22.1
  precedent.
- **Regenerated audit
  artifact.** Row 123
  (`admin-bhph-note-create`)
  reclassifies from `covered`
  to `defer-candidate-O2`
  matching row 126's
  (`admin-bhph-payment-
  create`) handling. Coverage
  count expected to change by
  small delta as false-
  positives get corrected
  (potentially -1 to -5
  depending on how many other
  URLs share a prefix with a
  different-verb wrapper).
- **Budget guard.** If the
  targeted fix exceeds ~2
  hours, stop, document the
  remaining false-positive
  patterns, and proceed to
  M23.2 with partial fix per
  §5.d Option A.
- **Session handoff** at
  `docs/handoffs/SESSION_176_m23_inc1_audit_fix.md`.
- **`00-START-NEXT-SESSION.md`**
  refreshed for M23.2.

**Backend baseline target at
M23.1 close:** 4,766 →
**~4,767** (possible audit-
script correctness test).
Frontend Vitest: 180
(unchanged). Acceptance
suite: 7 journeys
(unchanged).

## What lands at M23.2 (SESSION_177) — first anchor UI

Note origination UI + seed
extension + journey:

- **`createBhphNote` wrapper**
  in `bhphApi.ts` (POST
  `admin/bhph-notes/`).
- **`RecordBhphNoteForm`
  component** in
  `frontend/src/components/bhph/`
  with vehicle picker,
  principal, APR, cadence,
  first-payment-date, submit
  + error handling.
- **Attached to
  `DealerAiBhphPortfolio.tsx`**
  Notes card as persistent
  "Add note" CTA + modal.
- **Vitest coverage** for
  the new component.
- **Extended seed** with
  vehicle fixture (origination
  target) + backend
  idempotency test.
- **Extended assertion
  helper** at
  `acceptance/support/assertions/bhph.ts`
  with
  `expectBhphNoteOriginated(request, vehicleId)`.
- **New journey** at
  `acceptance/journeys/bhph/note_origination.spec.ts`.
- **Small operator-surface
  gap fixes** per §5.d (in-
  scope) if any surface
  during authoring.

Backend baseline target:
~4,767 → **~4,770**. Frontend
Vitest: 180 → **~187-192**.
Acceptance suite: **7 → 8**.

## What lands at M23.3 (SESSION_178) — second anchor UI

Payment intake UI + seed
extension + journey:

- **`createBhphPayment`
  wrapper** in `bhphApi.ts`
  (POST `admin/bhph-notes/<pk>/payments/`).
- **`RecordBhphPaymentForm`
  component** with amount,
  method picker, date, memo,
  submit + error handling.
- **Attached to
  `DealerAiBhphNoteDetail.tsx`**
  as new Payments card
  matching sibling pattern.
- **Vitest coverage** for
  the new component.
- **Extended seed** with
  fresh-note-with-balance
  fixture + payment cleanup
  on re-invocation.
- **Extended assertion
  helper** with
  `expectBhphPaymentRecorded(request, noteId, amount)`.
- **New journey** at
  `acceptance/journeys/bhph/payment_intake.spec.ts`.
- **Small operator-surface
  gap fixes** per §5.d.

Backend baseline target:
~4,770 → **~4,774**. Frontend
Vitest: ~192 → **~200-205**.
Acceptance suite: **8 → 9**.

## What lands at M23.4 (SESSION_179) — close-out

- CI job validation on all
  new / extended journeys.
- `docs/CAPABILITY_MATRIX.md`
  §7x — M23 shipped surface.
- `docs/roadmap/MILESTONE_23_RETROSPECTIVE.md`
  with §8 corrections + §9
  next-candidate.
- `docs/roadmap/MILESTONE_24_PLANNING.md`
  skeleton (status: draft).
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  updated with M23 shipped
  status.
- `00-START-NEXT-SESSION.md`
  refreshed for M24.0.
- Coordinated close-out
  commit + push per M18.6 /
  M19.6 / M20.5 / M21.5 /
  M22.4 pattern.

## Non-goals for the remaining M23 increments

Per MILESTONE_23_PLANNING.md §3:

- ❌ Do NOT ship sale-time
  origination trigger (Option
  B attachment for
  `RecordBhphNoteForm` on
  `VehicleSalePage.tsx`).
  Deferred to operator-use
  evidence per §3 deferral 1.
- ❌ Do NOT add new backend
  service verbs, DRF
  endpoints, tenancy
  carriers, migrations,
  permission classes, or
  frontend routes.
- ❌ Do NOT rewrite the audit
  script as AST-based per
  §5.d Option A explicit
  non-goal.
- ❌ Do NOT manually verify
  workflows before authoring
  journeys — journey-as-
  verifier per §5.f Option B.
- ❌ Do NOT force-scope
  larger discovered accounting
  or F&I gaps into M23 —
  document as retrospective
  §9 evidence per §5.d
  inherited posture.
- ❌ Do NOT split the BHPH
  seed into per-workflow
  seeds pre-emptively —
  extend additively per §5.e
  Option A.
- ❌ Do NOT push M23 commits
  individually — coordinated
  close-out push at M23.4
  per M18.6 / M19.6 / M20.5
  / M21.5 / M22.4 cadence.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M22 shipped section
   landed at M22.4)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (this session's expansion
   target)
6. `docs/roadmap/MILESTONE_22_RETROSPECTIVE.md`
   §8 + §9 (M22 corrections
   + standing M23 question)
7. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (M21 Candidate O
   governing contract that
   M23 inherits directly)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact —
   authoritative for
   accounting post-M22.1;
   authoritative for BHPH
   post-M23.1 fix)
9. `docs/CAPABILITY_MATRIX.md`
   §7w (M22 shipped surface)
