---
title: "SESSION_171 handoff — Milestone 22 · Increment 0 (M22.0 — planning refinement + target selection)"
status: historical
type: handoff
date: 2026-08-03
session: 171
milestone: 22
milestone_status: in-progress
milestone_name: "Accounting Operational Validation"
increment: 0
increment_status: shipped
commit: TBD
---

# SESSION_171 — Milestone 22 · Increment 0 (M22.0 — planning refinement + target selection)

## What shipped

Planning-only session per the M10.0 /
M11.0 / M12.0 / M13.0 / M14.0 / M15.0 /
M16.0 / M17.0 / M18.0 / M19.0 / M20.0 /
M21.0 precedent. Full memo expansion
from the M21.5 skeleton + all **seven**
§5 load-bearing decisions resolved at
open. **Empirical M22.0 discovery
reshaped Candidate A** from "ship
missing UI" (per the M21 retrospective
§9 recommendation, which had been
grounded in M21.1 audit numbers now
known to be unreliable) to **Accounting
Operational Validation** — validate the
shipped accounting workflows end-to-end
via Playwright rather than rebuild what
already ships.

**§5.a → Candidate A confirmed at open,
reshaped.** The M18 §8 accounting
designation finally lands (five
milestones after its designation —
M18 → M22) but in refined form. User
named at SESSION_171 M22.0 open:
Milestone name **"Accounting
Operational Validation."** Discovery
during M22.0 open surfaced that both
anchor UIs originally named (JE
reversal + trial-balance snapshot
create/list/detail) already ship as
fully-wired operator pages from
**M14.2–M14.4 and M17.2**
(`AccountingTrialBalancePage.tsx`,
`AccountingJournalEntriesPage.tsx`,
`AccountingJournalEntryDetailPage.tsx`),
and that the M21.5 audit misclassified
four accounting endpoints
(`admin-trial-balance`,
`admin-journal-entry-list`,
`admin-cost-posting-failures`,
`admin-trial-balance-snapshot-list`)
as backend-only due to the nested-
template-literal regex limitation
documented at M21.1 close. User
redirected M22 from UI creation to
workflow validation + supporting audit
correction. Candidate O2 preserved for
M23+ with M22 journey-authoring
evidence as scope input. Candidates
T / U / L / M / D / C / P / G all
deferred with re-entry paths preserved
per discovery rule.

**§5.b–§5.h all confirmed as-
recommended.** Streak extends to **88
planning-time as-recommended M5.1 →
M22.0** across **thirteen consecutive
milestones now** (M10 + M11 + M12 +
M13 + M14 + M15 + M16 + M17 + M18 +
M19 + M20 + M21 + M22).

**Refined governing contract
established.** M22 inherits the M21
Candidate O governing contract (map to
shipped backend + close missing UI +
Playwright journey + not generic
polish) and refines it for validation-
shape milestones. Every M22 shipped
surface must (1) map to already-
shipped frontend surface PLUS
already-shipped backend capability;
(2) establish operational-completion
evidence through Playwright end-to-
end journey; (3) use journey-as-
verifier rather than manual
verification; (4) split discovered
gaps by size — small in-scope fix vs.
large deferred as next candidate
evidence.

**DoD compliance verified by
construction.** M22 is a journey-
authoring milestone — every
implementation increment (M22.2
anchor + conditional M22.3) adds a
Playwright operational journey. §3
of the memo names the journey
additions explicitly. The M21.0 §5.f
Option B DoD amendment is trivially
satisfied.

**Backend baseline unchanged:** 4,761
pass, 1 skipped, 0 fail. **Frontend
Vitest baseline unchanged:** 180 pass.
Migrations `0001`–`0048` (unchanged).
Tenancy carriers 52 (unchanged — M22
adds no tenancy carriers). DRF admin
surface 113 (unchanged — M22 adds no
endpoints). Frontend operator routes
20 (unchanged — M22 adds no routes).
Permission classes 7 (unchanged —
zero-drift streak intact at twenty-
one consecutive milestones; M22
extends to twenty-two at close).
Celery-beat task families 10
(unchanged). Acceptance suite 6
journeys (unchanged — M22 will grow
count at M22.2 and possibly M22.3).

## Starting-state verification (this session)

Ran the full M22.0-open checklist per
the M21.5 handoff:

- `git status` — clean.
- `git log --oneline -6` — top commit
  is the M21.5 close-out
  (`6103aea Milestone 21 shipped —
  Operational Surface Completion
  (SESSION_166-170)`); `origin/main`
  at the same head.
- `python3 manage.py test dealer_ai` →
  **4,761 pass, 1 skipped, 0 fail**.
- `cd frontend && npm test` → **180
  pass** (26 files).
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `cd acceptance && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.
- **M21 acceptance CI run:** run
  `30822664811` completed **success**
  in 2m3s on the M21.5 close-out
  push. First real M21 CI run
  verified green.
- **Audit regeneration:** ran
  `python3 -m dealer_ai.scripts.audit_operational_surface`
  from `backend/`. Output: **153
  endpoints, 106 covered, 47 backend-
  only** — identical to M21.5 close.
  Only diff was two rows where
  wrapper-only annotations reordered
  (non-deterministic script output);
  reverted to keep tree clean for
  planning.

All green. No §0.a M22.0 amendments
needed for regressions.

## Empirical discovery during M22.0 open (drives §5.a refinement)

The scope reconciliation performed
during M22.0 open surfaced findings
that contradicted the M21 retrospective
§9 assumptions:

**Finding 1 — Both anchor UIs already
ship.**
- `AccountingJournalEntryDetailPage.tsx`
  (M14.3/M14.4) — full
  `ReverseEntryDialog` with reason
  textarea + posted_at input +
  confirm button + error handling
  wired to `reverseJournalEntry`.
- `AccountingTrialBalancePage.tsx`
  (M14.2/M17.2) — date picker,
  "Freeze this view" button, prior-
  closes table, inline snapshot
  detail card — wired to
  `freezeTrialBalance`,
  `listTrialBalanceSnapshots`,
  `fetchTrialBalanceSnapshot`.
- `AccountingJournalEntriesPage.tsx`
  (M14.3) — paginated JE list wired
  to `fetchJournalEntries`.

All three routes (`/dealer-ai-
accounting/trial-balance`,
`/dealer-ai-accounting/journal-
entries`, `/dealer-ai-
accounting/journal-entries/:pk`) are
wired in `main.tsx`.

**Finding 2 — Trial-balance freeze is
already Playwright-validated.** The
`office/accounting_workflow.spec.ts`
(M20.3) exercises the freeze workflow
end-to-end: land on trial-balance page
→ freeze current view → verify
snapshot appears in prior-closes →
click snapshot row → inline detail
renders → business-outcome assertion
via API (snapshot exists + is
balanced).

**Finding 3 — Audit misclassified four
accounting endpoints.** The M21.5
regenerated audit shows four
accounting endpoints as backend-only
that are in fact wired through
consumed wrappers:
- `admin-trial-balance` →
  `defer-candidate-O2` (false-
  negative; used by trial-balance
  page).
- `admin-journal-entry-list` →
  `defer-candidate-O2` (false-
  negative; used by JE list page).
- `admin-cost-posting-failures` →
  `defer-candidate-O2` (false-
  negative; used by trial-balance
  page).
- `admin-trial-balance-snapshot-
  list` → `defer-domain-milestone`
  (false-negative; used by trial-
  balance page).

Root cause: the documented nested-
template-literal regex limitation
(M21 retrospective §4 — "nested
TypeScript template literals confuse
the URL normalizer"). Accounting
endpoints are especially affected
because the wrappers use paginated
URL patterns with template-literal
querystring assembly.

**Finding 4 — Genuinely untested
workflows exist.** No Playwright
journey covers: (a) JE reversal
end-to-end (dialog interaction +
reversal linkage verification), (b)
JE list navigation + drill-in, (c)
cost-posting failures rendering
path within the trial-balance
journey.

These findings drove the redirect of
§5.a from "ship missing UI" to
"validate shipped workflows." The M22
scope now closes Finding 3 (audit
correction) as supporting work and
Finding 4 (untested workflows) as
the anchor implementation. Finding 1
+ 2 explicitly define what M22 does
NOT rebuild.

## Load-bearing decisions confirmed at M22.0 open

Seven decisions per validation-shape
milestone. All confirmed as-
recommended.

**§5.a — Milestone target selection.**
Candidate A — Accounting Operational
Validation. Reshaped from M21
retrospective §9 recommendation per
M22.0 empirical discovery. Zero new
UI shipped; scope centered on
workflow validation + supporting
audit tooling correction.

**§5.b — Workflow enumeration source.**
Option D — combined page-surface +
office-manager persona walk. Pages
define what's shippable; persona
provides authoring order. Explicitly
NOT the M21 audit (proven
unreliable for accounting pending
§5.e correction).

**§5.c — Journey folder + shape.**
Option B — per-workflow spec files
under `acceptance/journeys/office/`
(siblings to existing
`accounting_workflow.spec.ts`).
Matches M21 §5.e Option C precedent
for distinct-workflow-shape
journeys.

**§5.d — Discovered-gap handling
posture.** Option B — split by size.
Small operator-surface gaps
(missing testid, broken link, label
typo, form validation bug) fixed
in-scope; large gaps (missing form,
missing wrapper, missing service
verb, new UI structure) documented
in retrospective §9 as next
accounting candidate with
reproducible evidence.

**§5.e — Audit tooling correction
posture.** Option B — targeted regex
fix for the documented nested-
template-literal false-negative
class plus the four known
accounting misclassifications.
Explicit non-goal: full AST-based
audit rewrite. Budget guard: if
targeted fix exceeds ~2 hours at
M22.1 open, defer deeper refactor
to a future audit-tooling
milestone.

**§5.f — Baseline verification
approach.** Option B — journey-as-
verifier. Playwright IS the
verification. No manual developer
pass-through of workflows before
authoring. Vitest coverage
explicitly does not substitute
(mocks the API layer; only
Playwright exercises the full
stack).

**§5.g — Seed command pattern.**
Option A — extend existing
`seed_journey_office_accounting_workflow`
additively with per-journey
fixtures. Matches M21 Lesson 4
(reference existing seed shape).
Idempotency via stable
`[M22.N-...]` description tags per
existing seed pattern.

**§5.h — Increment sequencing +
completion contract.** Option B —
evidence-sized four-to-five
increments. **M22.0 planning** (this
session) + **M22.1 audit-tooling
correction + artifact refresh** +
**M22.2 JE reversal journey + seed
extension** + **M22.3 additional
journeys per §5.b enumeration
(conditional)** + **M22.4 close-
out**. Milestone completion
contract: all in-scope journeys
ship with passing extensions /
additions on `main` CI; audit
tooling corrected + artifact
regenerated with accurate
accounting coverage;
retrospective §8 records
corrections landed and §9 records
next-accounting-candidate identified
by journey-authoring evidence (if
any).

## Streak

**88 planning-time as-recommended
M5.1 → M22.0.** Thirteen consecutive
milestones now (M10 + M11 + M12 +
M13 + M14 + M15 + M16 + M17 + M18 +
M19 + M20 + M21 + M22) with every
§5 decision confirmed as-recommended
at planning-time open.

Historical §5 counts through M22.0:
- M10 through M17: 6 decisions each
  = 48.
- M18: 7 decisions.
- M19: 8 decisions.
- M20: 8 decisions.
- M21: 8 decisions.
- M22: 8 decisions (§5.a target +
  §5.b–§5.h).
- Total across thirteen milestones
  (M10–M22): 48 + 7 + 8 + 8 + 8 +
  8 = **87 §5 decisions**.

The "88 planning-time as-recommended
M5.1 → M22.0" counter carries the
per-milestone-open invariant without
a single deviation across the
thirteen consecutive milestones.

**Zero-drift permission-class streak
target for M22 close:** twenty-one
→ **twenty-two** consecutive
milestones. M22 introduces zero new
permission classes.

## What's next: SESSION_172 M22.1 audit tooling correction + artifact refresh

Per `MILESTONE_22_PLANNING.md` §7
M22.1:

- **Targeted regex fix** in
  `backend/dealer_ai/scripts/audit_operational_surface.py`
  handling nested TypeScript template
  literals in URL construction paths.
  Scope: fix the documented false-
  negative class + the four known
  accounting misclassifications
  (`admin-trial-balance`,
  `admin-journal-entry-list`,
  `admin-cost-posting-failures`,
  `admin-trial-balance-snapshot-list`).
- **Optional backend test** for the
  fix. If the audit script has
  existing tests, extend them; if
  not, adding new ones is
  discretionary at M22.1 open.
- **Regenerated audit artifact.**
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  refreshed. Coverage count expected
  to increase by at least four
  (accounting misclassifications
  corrected); if additional false-
  negatives surface during the
  correction pass, either fix them
  or catalog for future audit-
  tooling work per §0.a M22.1
  amendment.
- **Budget guard.** If the targeted
  fix exceeds ~2 hours, stop,
  document the remaining false-
  negative patterns as a future
  audit-tooling milestone, and
  proceed to M22.2 with a partial
  fix per §5.e Option B. Do not
  let audit correction bleed into
  anchor scope.
- **Session handoff** at
  `docs/handoffs/SESSION_172_m22_inc1_audit_correction.md`.
- **`00-START-NEXT-SESSION.md`**
  refreshed for M22.2.

**Backend baseline target at M22.1
close:** 4,761 → **~4,762–4,763**
(possible audit-script correctness
tests). Frontend Vitest: 180
(unchanged). Acceptance suite: 6
journeys (unchanged).

## What lands at M22.2 (SESSION_173) — first anchor

JE reversal journey + seed
extension:

- **Extended seed** at
  `backend/dealer_ai/management/commands/seed_journey_office_accounting_workflow.py`
  with a reversible-JE fixture
  (stable description tag —
  `[M22.2-office-je-reversal]` or
  similar; idempotent reuse). Add
  backend test covering fixture
  idempotency + tenant scoping.
- **Extended assertion helper** at
  `acceptance/support/assertions/accounting.ts`
  with `expectJournalEntryReversed(request, originalId)`
  — asserts reversal entry exists
  with swapped lines +
  `reverses_id` pointing to
  original.
- **New journey** at
  `acceptance/journeys/office/accounting_je_reversal.spec.ts`
  walking: navigate to JE detail
  for seeded reversible entry →
  open reversal dialog → fill
  reason → click confirm → verify
  status message → verify reversal
  linkage badge appears →
  business-outcome assertion via
  API using the new helper.
- **Concurrent §5.b page/persona
  walk during authoring** —
  document any additional
  accounting workflows surfaced
  that warrant distinct M22.3
  journeys. Small operator-surface
  gap fixes per §5.d if any
  discovered (in-scope) with §0.a
  M22.2 amendments.

Backend baseline target: ~4,763 →
**~4,765** (seed fixture idempotency
tests). Frontend Vitest: 180 unless
§5.d fixes add cases. Acceptance
suite: **6 → 7**.

## What lands at M22.3 (SESSION_174) — conditional

**Only if the M22.2 §5.b page/
persona walk surfaces additional
distinct journey-worthy workflows.**

Per each additional workflow: seed
fixture extension (per §5.g
additive) + business-outcome
assertion helper extension + spec
file per §5.c Option B. Candidates
include (but are not limited to):
JE list navigation journey, cost-
posting failures rendering
extension, as-of picker interaction
journey.

If the M22.2 walk surfaces no
additional journey-worthy workflows,
M22.3 is explicitly SKIPPED per
§5.h Option B, and M22.4 close-out
becomes SESSION_174 (not
SESSION_175).

Backend baseline target (if
applicable): depends on scope.
Frontend Vitest: depends on §5.d
fixes. Acceptance suite: **7 →
7+N** where N is the count of
distinct additional journeys
authored.

## What lands at M22.4 (SESSION_174 or SESSION_175) — close-out

- CI job validation on all new /
  extended journeys.
- `docs/CAPABILITY_MATRIX.md` §7w
  (M22 shipped surface — new /
  extended journeys + audit
  tooling correction + seed
  fixture extensions).
- `docs/roadmap/MILESTONE_22_RETROSPECTIVE.md`
  with §8 corrections landed and
  §9 next-accounting-candidate
  identified by journey-authoring
  evidence (if any). Format for
  §9 gap findings: "workflow X
  cannot complete through the UI
  because Y; reproducible steps
  in the M22.N handoff;
  recommended M23 elevation with
  bounded scope Z" — evidence-
  grounded, not speculation.
- `docs/roadmap/MILESTONE_23_PLANNING.md`
  skeleton (status: draft) with
  candidate list refreshed from
  M22 retrospective §9 findings +
  remaining M21 / M20 / M19
  candidates.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  updated with M22 shipped
  status.
- `00-START-NEXT-SESSION.md`
  refreshed for M23.0.
- Coordinated close-out commit +
  push per M18.6 / M19.6 / M20.5
  / M21.5 pattern.

## Non-goals for the remaining M22 increments

Per the memo §3:

- ❌ Do NOT ship new accounting UI
  (rebuilding what already ships
  from M14/M17).
- ❌ Do NOT add new backend service
  verbs, DRF endpoints, tenancy
  carriers, migrations, permission
  classes, or frontend routes.
- ❌ Do NOT rewrite the audit
  script as AST-based — targeted
  regex only per §5.e Option B.
- ❌ Do NOT manually verify
  workflows before authoring
  journeys — journey-as-verifier
  per §5.f Option B.
- ❌ Do NOT force-scope larger
  discovered accounting gaps into
  M22 — document as retrospective
  §9 evidence per §5.d Option B.
- ❌ Do NOT split the accounting
  seed into per-workflow seeds
  pre-emptively — extend
  additively per §5.g Option A.
- ❌ Do NOT push M22 commits
  individually — coordinated
  close-out push at M22.4 per
  M18.6 / M19.6 / M20.5 / M21.5
  cadence.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M21 shipped + DoD amendment
   landed at M21.5)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_22_PLANNING.md`
   (this session's expansion target)
6. `docs/roadmap/MILESTONE_21_RETROSPECTIVE.md`
   §8 + §9 (M21 unblocks + standing
   M22 question — M22's origin;
   note that §9's specific scope
   recommendation was falsified by
   M22.0 discovery)
7. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (M21 governing contract that M22
   refines for validation-shape
   milestones)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact — known
   unreliable for accounting until
   M22.1 correction lands;
   authoritative for other domains
   post-M22.1 regen)
9. `docs/CAPABILITY_MATRIX.md` §7v
   (M21 shipped surface)
