---
title: "Milestone 34 — Test-Hygiene Remediation: Idempotent seeds + rerun-safe acceptance journeys"
status: historical
type: planning-memo
generated: 2026-08-05
generated_at_session: SESSION_213 (skeleton + expansion + all §5 locks)
milestone: 34
milestone_name: "Test-Hygiene Remediation: Idempotent seeds + rerun-safe acceptance journeys (three shared-DB non-idempotent journeys: sales_manager/daily_startup + recon/workflow + office/accounting_workflow)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/MILESTONE_20_PLANNING.md (M20.2 sales-manager + M20.3 recon + M20.3 accounting journey origin; §5.d Option B compose-service-verbs-not-ORM rule)
  - docs/roadmap/MILESTONE_33_RETROSPECTIVE.md §9 (M34 candidate list + H test-hygiene 6-milestone deferral note)
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - acceptance/journeys/sales_manager/daily_startup.spec.ts
  - acceptance/journeys/recon/workflow.spec.ts
  - acceptance/journeys/office/accounting_workflow.spec.ts
  - acceptance/support/auth/login.setup.ts (seed sequence + M20_ACCEPTANCE_DB env guard)
  - acceptance/support/assertions/accounting.ts (fetchSnapshotList helper — D5 target)
  - backend/dealer_ai/management/commands/seed_journey_sales_manager_daily_startup.py
  - backend/dealer_ai/management/commands/seed_journey_recon_workflow.py
  - backend/dealer_ai/management/commands/seed_journey_office_accounting_workflow.py
  - backend/dealer_ai/models.py (ReconDecision OneToOne to ConditionFinding; TrialBalanceSnapshot dealership scope)
---

# Milestone 34 — Test-Hygiene Remediation: Idempotent seeds + rerun-safe acceptance journeys

> **Active planning memo.** Drafted + expanded + all §5 locks at
> SESSION_213 M34.0 open.
>
> **§5.a locked at open** as **Test-Hygiene Remediation — idempotent
> seeds + rerun-safe acceptance journeys** under the *primary
> operational-coverage lens* (durable since M22 close). Selected as
> "close a deferral" over both continuation (F&I depth arc; still
> pilot-evidence gated) and breadth reset (no fresh direct-operator
> gap with landed evidence). H has waited six milestones (M27.2 →
> M33.2) with three shared-DB non-idempotent Playwright journeys
> unchanged. The primary operational-coverage lens argues *now*, not
> "if evidence surfaces later": H protects the durability of the
> 131-endpoint coverage set that every future depth-arc addition
> builds on.
>
> **Zero blocking findings at §4 verification.** First M34 planning-
> open cycle with zero corrections needed. Tracing pass on all three
> journeys at open validated that no product-code changes are
> required — every fix lives in the three seed commands + one
> Playwright assertion helper. Attributable to (z) verification-
> driven revision cycles at planning-open, now on invocation 3.
>
> **The anchor question** — *After a Playwright journey runs, mutates
> shared state, and completes, can the same journey run again against
> that same shared state and pass without human intervention?* —
> governs every M34 scope decision.
>
> **Substrate-compound-value continuation breaks intentionally at
> M34.** M32 sales-to-F&I bridge + M33 F&I first-loop-activation
> reached 2 links; M34 is a "close a deferral" milestone per M33 §9
> standing question resolution. Not a depth-arc reset — the F&I
> depth arc remains the primary continuation candidate for M35 if
> pilot evidence surfaces on NEW C chargeback, NEW F&I workflow-
> state extensions, or Lender Fit Recommendations.
>
> **Zero-drift permission-class streak continues at 37 → 38.** No
> new permission class. No new endpoint. No migration. No schema
> change. No shipped operator behavior change.
>
> **DoD amendment (M21.0 §5.f Option B) compliance.** M34.1 backend-
> only → **DoD exception path invocation #9** (M26 + M27.1 + M28.1 +
> M29.1 + M30.1 + M31.1 + M32.1 + M33.1 + M34.1). M34.2 acceptance-
> workspace-only → continuation of exception path (no new customer-
> facing journey; existing three tagged for rerun-proof). M34 is
> the first fully non-customer-facing milestone since M20.
>
> **Two-increment shape** — backend / acceptance boundary. M34.1
> ships seed extensions + Django regression tests; M34.2 ships
> assertion-helper defense + `@rerun-hygiene` tag + repeated-run
> proof. Rollback fully independent in reverse ship order.
>
> **Durable lesson locked at planning-open (D8, verbatim per user
> directive):** *Acceptance journeys must be independently rerunnable
> against shared state; green-on-clean-DB alone is insufficient
> evidence of operational reliability.* Recorded as candidate lesson
> (ff) at M34 retrospective §5; awaits first re-application to
> elevate.

## 1. Anchor question

**After a Playwright journey runs, mutates shared state, and
completes, can the same journey run again against that same shared
state and pass without human intervention?**

M34 answers *yes for the three named journeys* by making their
`seed_journey_*` commands **idempotent against mutated state**, not
just idempotent against a fresh migrated DB. The distinction is the
core M34 insight: for six milestones the seed contract was
"create-if-missing" — sufficient for first-run correctness against
CI's per-run fresh DB, insufficient for any run where the DB carries
prior-run mutations.

## 2. Business problem this milestone solves

Per the M33 retrospective §9 and every retrospective from M27.2
onward, three Playwright acceptance journeys have persisted with
known non-idempotency:

- `sales_manager/daily_startup.spec.ts` — mutates `assigned_to`,
  creates persistent BeBack rows, creates persistent
  FollowUpCadences.
- `recon/workflow.spec.ts` — creates a persistent ReconDecision on
  the seeded ConditionFinding.
- `office/accounting_workflow.spec.ts` — creates persistent
  TrialBalanceSnapshots that grow past the helper's page cap after
  10 successful runs.

CI reset masks the class today (each CI run migrates a fresh
`db.acceptance.sqlite3`), so this has not surfaced as CI red. The
operational risk is threefold: (a) any future move toward
CI parallelization, DB persistence across CI runs, or shared
staging DB use would trip these journeys immediately; (b) developer
reruns locally are noisy in ways developers work around rather than
fix, eroding trust in the acceptance contract; (c) any future
journey author copying the shape of these three seeds re-introduces
the class silently. M34 removes the class before it constrains
future milestone architecture.

## 3. Non-goals for this milestone (deferred + future candidates)

**Explicitly deferred out of M34 scope:**

- Any product-code change (views, services, models, permissions,
  URLs, migrations, schemas).
- Modifications to the three journey `.spec.ts` files beyond
  adding a `@rerun-hygiene` tag to the `test.describe` string.
- Extending scope to fix any of the other 22 acceptance journeys
  unless a failure surfaces during D7 repeated-run testing AND
  belongs to the same non-idempotency class (per user directive;
  see §5.h).
- Introducing a shared reset helper across seed commands. Per
  `feedback_duplicate_small_stable_logic.md`, three short domain-
  local resets are preferable to one premature abstraction.
- Modifying the CI workflow (`.github/workflows/acceptance.yml`)
  to add DB persistence, parallelization, or repeated-run gating.
  D7 Option A is developer-side; Option B upgrade path preserved
  for a future milestone if CI DB persistence is ever introduced.
- Modifying the shipped M32.3 Intake Iris or M33.2 Structure Sam
  fixtures — both already independently rerunnable per M32 D11 +
  M33 R7.
- Introducing a `TrialBalanceSnapshot.fixture_tag` field — schema
  change; not needed under D4's dealership-scoped wipe.
- Modifying the `--reset` flag semantics on the three seed
  commands — reset remains a manual escape hatch even after M34
  makes reruns automatic.

**Non-goals carried forward unchanged from prior milestones:**

- All M33 §3, M32 §3, M31 §3, M30 §3, M29 §3, M28 §3, M27 §3,
  M25 §4 deferrals.
- NEW C F&I chargeback substrate — pilot-evidence gated.
- Lender Fit Recommendations (D10 elevation from M33) — three of
  four blockers remain.
- NEW F&I workflow-state extensions.
- NEW F&I-scoped lead-context view.
- NEW cross-lead sales-manager pending-approval queue.
- Direct-create CA structuring branch.
- Iteration UX.
- PATCH on DealStructure.
- NEW O2 / NEW O3.
- Gated T / U / L / M.
- Deferred D (LLM router / cost caps).
- Deferred stable G (dashboard testid hardening).

## 4. Verification pass at planning-open

Six verifications performed. **Zero blocking findings.**

### 4.1 Journey trace — `sales_manager/daily_startup.spec.ts`

CLEAN. Three leak sources identified:

- **A** — `assigned_to` on "Overnight SM Lead 1" mutated by journey
  step 4 (Assignment dropdown → Acceptance Advisor); seed's
  `_provision_leads` only creates rows when fewer than 3 exist and
  never resets `assigned_to`. Line 76 pre-flight
  `expect(seededLead.assigned_to).toBeNull()` fails on rerun.
- **B** — BeBack rows created on "Overnight SM Lead 2" via journey
  line 227 (Record Be-back form); accumulate unbounded across runs.
  Assertion is count-delta so it passes, but leaks state.
- **C** — 1wk FollowUpCadence created on "Overnight SM Lead 1" via
  journey line 265; journey pauses it via inline row action. On
  rerun the 1wk create hits `DuplicateActiveCadenceError` because
  the paused cadence still constrains the unique-active
  (lead, template) invariant.

**Fix scope:** three lines in
`seed_journey_sales_manager_daily_startup.py`. See D2. No product-
code changes.

### 4.2 Journey trace — `recon/workflow.spec.ts`

CLEAN. One leak source:

- **D** — ReconDecision created on the seeded ConditionFinding via
  journey step 4 (Must-do click). Seed's
  `_provision_report_and_finding` reuses the existing finding but
  never clears its child decision. Line 58 pre-flight
  `expect(finding.decision).toBeNull()` fails on rerun. Model
  relationship: `ReconDecision.finding` is
  `OneToOneField(on_delete=CASCADE, related_name="recon_decision")`
  — direct `ReconDecision.objects.delete()` does not cascade
  upward to ConditionFinding, so seed-time deletion is safe.

**Fix scope:** one line in `seed_journey_recon_workflow.py`. See
D3. No product-code changes.

### 4.3 Journey trace — `office/accounting_workflow.spec.ts`

CLEAN. One leak source, subtler than #1 and #2:

- **E** — TrialBalanceSnapshot rows accumulate unbounded across
  runs. `expectSnapshotCountAtLeast`
  (`acceptance/support/assertions/accounting.ts:39`) fetches
  `?page_size=10` and returns `snapshots.length`. Journey captures
  `priorCount = length` (capped at 10) before freeze; asserts
  `.toBeGreaterThan(priorCount)` after. On the 11th run,
  `priorCount === 10` and `.length` stays 10 — assertion fails
  deterministically. The response envelope carries `total_count`;
  the helper discards it.

**Fix scope:** dual defense — one line in
`seed_journey_office_accounting_workflow.py` (D4) + one refactor
in the helper (D5). No product-code changes.

### 4.4 D4 scoped-wipe safety verification

CLEAN. `runManagementCommand`
(`acceptance/support/auth/login.setup.ts:59`) sets
`M20_ACCEPTANCE_DB=1`. The three seed commands are invoked only
from that setup step; they are not part of any dev/prod seed
sequence. Verified via absence of external references to
`seed_journey_office_accounting_workflow` outside the acceptance
workspace. D4's `TrialBalanceSnapshot.objects.filter(dealership=...).delete()`
is dealership-scoped and env-scoped; no production or dev DB
snapshot is at risk.

### 4.5 Model relationship + cascade verification

CLEAN.

- `ReconDecision.finding`:
  `OneToOneField(ConditionFinding, on_delete=CASCADE, related_name="recon_decision")`.
  Deleting the decision does not affect the finding.
- `BeBack.lead`: FK confirmed present.
- `FollowUpCadence.lead` + `template`: fields confirmed via
  existing `_provision_seed_cadence` in
  `seed_journey_sales_manager_daily_startup.py`.
- `TrialBalanceSnapshot.dealership`: FK confirmed via
  `expectSnapshotCountAtLeast` querying by tenant.
- `CustomerLead.assigned_to`: field confirmed via journey pre-
  flight assertion.

### 4.6 DoD compliance check on §5.e

CLEAN. M34 is infra-only (no shipped operator behavior changes);
exception path invocation #9 (following M26 + M27.1 + M28.1 +
M29.1 + M30.1 + M31.1 + M32.1 + M33.1). Pattern firmly established
at nine invocations. §5.f documents rationale.

---

**Zero blocking findings. Zero corrections required before §5.b
lock.** First M34 planning-open cycle needing no revision. The z
lesson (verification-driven revision cycles at planning-open) is
on invocation 3 — anticipated revision rounds did not materialize
because the tracing pass was thorough enough to resolve ambiguity
inline.

## 5. Load-bearing decisions

### 5.a Target selection (locked at open)

**Milestone 34 — Test-Hygiene Remediation: idempotent seeds +
rerun-safe acceptance journeys.**

Scope M34 strictly to the three known shared-DB non-idempotent
Playwright journeys: `sales_manager/daily_startup`,
`recon/workflow`, `office/accounting_workflow`. For each, identify
the exact leaked state, root cause, and smallest durable cleanup
or idempotent-seed correction. Prefer deterministic seed/reset
behavior over test-order dependence, broad database wipes, or per-
test hacks. Preserve parallel-safety and rerun-safety: each
journey must pass alone; each must pass twice against the same DB;
the three must pass in arbitrary order; the full acceptance suite
must remain green.

**Rationale under the primary operational-coverage lens:**

- **No M34 candidate has fresh operator evidence.** NEW C is still
  pilot-gated; Lender Fit still has three of four blockers; F&I
  workflow-state extensions and F&I-scoped lead-context view are
  both explicitly evidence-gated ("if operator evidence
  surfaces"); direct-create / iteration / PATCH are all "elevate
  if operator evidence surfaces." Without operator evidence,
  choosing any of them would violate the *Build Around Operational
  Problems* project rule.
- **H is the one candidate where the operational-coverage lens
  argues *now*, not "if evidence surfaces later."** Three shared-
  DB non-idempotent journeys have persisted unchanged M27.2 →
  M33.2 (six milestones). They constrain future acceptance-suite
  parallelization, force CI ordering discipline, and one flake in
  any of them would erode confidence in the entire 32-test suite.
- **Breadth pivot (fresh gap) has no strong evidence either** —
  the 26 defer-candidate-O2 endpoints include auth / chat /
  vehicle endpoints where "direct operator wrapper" isn't the
  shape (chat has its own frontend surface via the sales
  assistant). The three named breadth gaps (vendor detail #43,
  photo reorder #65, broader F&I #89–101) are wrapper-only polish
  or too-large-without-direction.
- **F&I depth arc preservation** — M34 breaks the M32+M33 2-link
  arc intentionally per M33 §9 standing question resolution
  ("close a deferral"). The arc remains the primary continuation
  candidate for M35 if pilot evidence surfaces on NEW C, NEW F&I
  workflow-state extensions, or Lender Fit.

**Alternatives considered explicitly:**

- NEW C — F&I chargeback substrate: still pilot-evidence gated
  (unchanged M30 / M31 / M32 / M33 §9). Not selected.
- Lender Fit Recommendations (D10 elevation): three of four
  blockers remain. Not selected.
- NEW F&I workflow-state extensions: evidence-gated on state
  model. Not selected.
- NEW F&I-scoped lead-context view: evidence-gated. Not selected.
- NEW cross-lead sales-manager pending-approval queue: evidence-
  gated. Not selected.
- Direct-create CA structuring branch: M33 explicit deferral;
  requires vehicle-picker substrate. Not selected.
- Iteration UX: M33 D9 explicit deferral. Not selected.
- PATCH on DealStructure: M33 activation-vocabulary-asymmetry
  preservation. Not selected.
- NEW O2 / NEW O3 audit refinement: 8-milestone deferral;
  tracing-first. Not selected.
- Fresh direct-operator gaps (vendor detail #43, photo reorder
  #65, broader F&I #89–101): all small polish or too-large-
  without-direction. Not selected.

**User confirmation at open:** target locked; zero corrections
applied before §5.b lock (first M34 planning-open cycle with
zero revisions). Explicit user constraints locked into §5.b–§5.h:

1. Scope strictly to the three named journeys.
2. For each, identify exact leaked state + root cause + smallest
   durable cleanup.
3. Prefer deterministic seed/reset behavior over test-order
   dependence, broad DB wipes, or per-test hacks.
4. Preserve parallel + rerun safety (four invariants per §5.a
   locked text).
5. Do NOT hide failures via assertion-weakening, sleeps, retries,
   or full-DB-reset-between-tests.
6. Add focused regression coverage proving the corrected journeys
   no longer depend on pristine shared state.
7. Any new failure discovered during repeated-run testing is in
   scope only if same non-idempotency class; otherwise record
   and defer.
8. Use customer-facing DoD exception path explicitly.
9. Record durable lesson verbatim per §5.b D8.
10. Keep operator-facing M35 candidate list unchanged unless M34
    evidence materially alters urgency.

### 5.b Design decisions (D1–D8)

#### D1 — Seed-idempotency contract (project-wide statement)

Every `seed_journey_*` management command must be **rerun-safe
against a mutated DB**: after any prior journey run has left state
behind, running the seed again must restore each pre-flight
invariant the journey depends on. Restored invariants are named
explicitly in each command's module docstring under a new
`## Rerun invariants` section (e.g. "Overnight SM Lead 1 has
`assigned_to IS NULL`"; "seeded ConditionFinding has no
`recon_decision`"; "TrialBalanceSnapshots on the fixture
dealership count 0").

No shared reset helper across commands. Per
`feedback_duplicate_small_stable_logic.md`, three short domain-
local resets are preferable to one premature abstraction. If a
fourth seed with a similar leak class ships in the future,
elevate the abstraction on evidence at that time.

**Locks:** the contract; the docstring section name.

#### D2 — Sales-manager seed reset extensions (three leak sources)

In `seed_journey_sales_manager_daily_startup.py`, add reset logic
before the existing `_provision_leads` call, gated on the same
`_existing_leads` queryset the command already owns:

```python
# Rerun-safe: unassign, drop journey-created be-backs, drop non-24hr
# cadences, resurrect the seed 24hr cadence to active/unpaused.
seeded = _existing_leads(dealership)
seeded.update(assigned_to=None)
BeBack.objects.filter(lead__in=seeded).delete()
FollowUpCadence.objects.filter(lead__in=seeded).exclude(template="24hr").delete()
FollowUpCadence.objects.filter(
    lead__in=seeded, template="24hr"
).update(is_active=True, paused_at=None)
```

No new service verb; uses existing model queries. `--reset` path
retained but no longer required for rerun safety.

**Locks:** the exact reset order; the tag-scoped queryset (never
`.all()`); the placement (before `_provision_leads`).

#### D3 — Recon seed reset extension (one leak source)

In `seed_journey_recon_workflow.py`, add one line before
`_provision_report_and_finding`:

```python
ReconDecision.objects.filter(
    finding__description__startswith=FIXTURE_FINDING_TAG,
    dealership=dealership,
).delete()
```

The `dealership=dealership` filter is defense-in-depth against
fixture-tag collision across tenants.

**Locks:** the tag-scoped + dealership-scoped deletion; the
placement (before reuse-or-create).

#### D4 — Accounting seed reset extension (one leak source, scoped-wipe)

In `seed_journey_office_accounting_workflow.py`, add before
`_provision_journal_entry`:

```python
TrialBalanceSnapshot.objects.filter(dealership=dealership).delete()
```

**Scoped-wipe justification.** TrialBalanceSnapshot rows do not
carry a `description` or `fixture_tag` field (freeze does not
accept operator metadata), so tag-based scoping is not available.
The command runs only under `M20_ACCEPTANCE_DB=1` (verified §4.4);
no shipped snapshot on any production or dev DB is at risk. The
dealership-scoped filter is defense-in-depth against multi-tenant
snapshot pollution (unlikely today, cheap to preserve).

**Locks:** the dealership-scoped wipe (never `.all()`); the
`M20_ACCEPTANCE_DB` env-guard invariant re-documented in the
module docstring.

#### D5 — Assertion helper defense: `total_count` over `.length`

In `acceptance/support/assertions/accounting.ts`, refactor
`fetchSnapshotList` and `expectSnapshotCountAtLeast` to prefer the
response envelope's `total_count`:

```typescript
async function fetchSnapshotList(request): Promise<{
  snapshots: TrialBalanceSnapshotSummary[];
  totalCount: number;
}> {
  const url = "/api/dealer-ai/admin/accounting/trial-balance/snapshots/list/?page_size=10";
  const response = await request.get(url);
  expect(response.status()).toBe(200);
  const body = await response.json();
  const envelope = body.trial_balance_snapshots ?? {};
  return {
    snapshots: envelope.snapshots ?? [],
    totalCount: envelope.total_count ?? 0,
  };
}
```

`expectSnapshotCountAtLeast` asserts against `totalCount`; the
returned object exposes both so the drill-in
`newestSnapshot = snapshots[0]` continues to use the paged list.

Defense-in-depth: with D4 in place the count starts at 0 each
run, but the helper is now robust against a hypothetical future
scenario where snapshots accumulate (e.g. if D4 is ever reverted
or scoping shifts). `fetchAllJournalEntries` is untouched — the
M22.2 JE-reversal journey continues to work verbatim.

**Locks:** helper uses `total_count`; return shape documented in
`accounting.ts` module comment.

#### D6 — Regression coverage: Django unit tests prove invariants across mutate → re-seed cycles

Add `backend/dealer_ai/tests/test_seed_journey_idempotency.py`
with three tests, one per seed:

- `test_sales_manager_daily_startup_idempotent`: run seed →
  mutate (assign lead, create be-back, create 1wk cadence, pause
  seed 24hr) → run seed → assert all pre-flight invariants
  restored.
- `test_recon_workflow_idempotent`: run seed → create
  ReconDecision on the fixture finding → run seed → assert
  `finding.recon_decision` is None.
- `test_office_accounting_workflow_idempotent`: run seed →
  freeze a TrialBalanceSnapshot → run seed → assert count on
  default dealership is 0.

Each test uses `call_command()` + direct model queries + the same
fixture selectors the seed uses. Tests run under Django's per-test
transaction rollback so they don't affect the acceptance DB.

**Backend baseline projection:** 5,015 → **~5,018** pass at M34.1
close.

**Locks:** file path; three tests, one per journey; the
mutate → re-seed → invariant-check shape.

#### D7 — Acceptance-suite repeated-run proof (Option A locked)

At M34.2 close, exercise the three tagged journeys twice against
the same DB via **Option A** — developer-side invocation:

- Tag the three specs with `@rerun-hygiene` in the
  `test.describe` string.
- Document the invocation in `acceptance/README.md`:

```
# Prove the three previously-shared-DB-fragile journeys survive a
# second run against the mutated DB:
npx playwright test --repeat-each=2 --grep "@rerun-hygiene"
```

- Author runs this at M34.2 close; records pass output in the
  M34.2 handoff §7 as evidence.

**Rationale for Option A over CI gate (Option B):** CI already
resets the acceptance DB per run (`webServer` restart with
`migrate --run-syncdb`), so the repeated-run proof is developer-
facing evidence rather than a permanent CI gate today. Option B
(dedicated CI step) upgrade path preserved for a future milestone
if CI DB persistence is ever introduced.

**Locks:** Option A; `@rerun-hygiene` tag string; README section
placement.

#### D8 — Durable lesson recording (verbatim per user directive)

Add to `docs/CAPABILITY_MATRIX.md` §7 durable-lessons narrative
and to `docs/roadmap/MILESTONE_34_RETROSPECTIVE.md` §5 as
candidate lesson (ff):

> **Acceptance journeys must be independently rerunnable against
> shared state; green-on-clean-DB alone is insufficient evidence
> of operational reliability.**

**Why:** M34 exists because three journeys shipped M20.2 → M20.3
passed against fresh migrated DBs in CI but leaked state that
would trip a rerun. CI DB reset masked the class for six
milestones after first observation (M27.2 → M33.2). Durable
lesson protects future infra work from re-introducing the same
class.

**How to apply:** at every planning-open verification (§4) for
any journey add or extension, name the concrete invariants the
journey depends on and confirm the seed restores them across
mutations the journey applies. Elevate (ff) to load-bearing-
across-two-milestones on first re-application.

**Locks:** verbatim lesson text; CAPABILITY_MATRIX + retrospective
§5 placement.

### 5.c Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Fixture tag drift — a seed reset targets rows a different fixture also owns | Very Low | Med | Every seed reset scopes by both `fixture_tag` / `description__startswith` AND `dealership=default_dealership`; no `.all()` deletion anywhere; D2 + D3 + D4 comments make the scope explicit |
| R2 | D4 scoped wipe accidentally runs against a non-acceptance DB | None (by construction) | Critical | `runManagementCommand` sets `M20_ACCEPTANCE_DB=1`; wipe happens inside `seed_journey_*` invocation only reachable via the acceptance workspace; module docstring restates the invariant; production/dev DBs never load these seed commands under normal ops |
| R3 | Test #D6 dropped by another test's teardown (shared transactional state) | Low | Low | Each D6 test wrapped in Django's default per-test `TransactionTestCase` rollback; direct DB queries not asserted against side effects of other tests |
| R4 | D2 cadence reset breaks the M21.3 journey extension expectation that the seed 24hr cadence is active | None (by construction) | Med | D2 explicitly restores `is_active=True, paused_at=None` on the seed 24hr cadence — matches M21.3 journey assumption; regression test in D6 covers this exact invariant |
| R5 | D5 helper change breaks the M22.2 JE-reversal journey (uses `fetchAllJournalEntries`, different endpoint) | None (D5 touches only snapshot fetcher) | Med | D5 scope-locked to `fetchSnapshotList` + `expectSnapshotCountAtLeast`; `fetchAllJournalEntries` untouched; Vitest / TSC gates catch shape drift |
| R6 | Non-idempotency class other than seed-leak surfaces during D7 repeated-run testing (e.g. Django cache, session state, Redis) | Med | Med | Per user directive: in-scope only if same non-idempotency class (seed leak); otherwise record in M34 §3 deferral list and defer to a future milestone. D7 output logged verbatim; new failure modes fully characterized before deferral |
| R7 | Adding cleanup logic slows seed sufficiently to push acceptance suite over CI budget | Very Low (3 targeted deletes) | Low | D7 measurement: record suite time before + after M34.2; regression >2s triggers investigation |
| R8 | A future journey author copies the leak-and-forget pattern from historical seeds and re-introduces the class | Med (documentation doesn't enforce) | Low-Med | D1 seed-idempotency contract lives in each command's docstring; D8 durable lesson elevates the class to a project-wide review checklist; retrospective §9 records "planning-open verification must confirm seed restores journey invariants" as the anti-pattern reminder |
| R9 | D3 finding-scoped deletion silently no-ops (fixture tag substring drifts) | Very Low | Med | Regression test D6 asserts `finding.recon_decision is None` post-re-seed; if fixture tag ever drifts, the test fails loud |

### 5.d Verifications completed at planning-open

Six verifications (§4.1–§4.6 above) all resolved:

- §4.1 Journey trace — sales_manager/daily_startup: CLEAN.
- §4.2 Journey trace — recon/workflow: CLEAN.
- §4.3 Journey trace — office/accounting_workflow: CLEAN.
- §4.4 D4 scoped-wipe safety verification: CLEAN.
- §4.5 Model relationship + cascade verification: CLEAN.
- §4.6 DoD compliance check on §5.e: CLEAN.

**Zero blocking findings.** First M34 planning-open cycle with
zero corrections required. Attributable to the tracing pass being
thorough enough to resolve ambiguity inline.

### 5.e Phase / increment structure

**Two-increment split** — backend / acceptance boundary. Both
revertable independently; no migrations; no schema changes.

#### M34.1 (SESSION_214) — Backend: seed extensions + Django regression tests

**DoD exception path invocation #9.**

- **Seed command extensions** (three files under
  `backend/dealer_ai/management/commands/`):
  - `seed_journey_sales_manager_daily_startup.py`: D2 reset
    lines + docstring `## Rerun invariants` section + import
    for `BeBack` model.
  - `seed_journey_recon_workflow.py`: D3 reset line + docstring
    `## Rerun invariants` section.
  - `seed_journey_office_accounting_workflow.py`: D4 wipe line
    + docstring `## Rerun invariants` section + explicit
    `M20_ACCEPTANCE_DB` invariant note + import for
    `TrialBalanceSnapshot` model.
- **Regression tests**
  (`backend/dealer_ai/tests/test_seed_journey_idempotency.py` —
  new file, ~120 lines): three tests per D6.
- **No new service verb; no new URL; no new permission class;
  no migration.**
- **Backend baseline projection:** 5,015 → **~5,018** pass at
  M34.1 close.
- **Audit projection:** 162 / 131 / 31 / 321 unchanged (M34.1
  adds no endpoints, no service verbs).
- **Zero-drift streak preservation:** 37 → 38 consecutive
  milestones with no new permission class.
- **Two-source agreement gate** at M34.1 close: run
  `python3 -m dealer_ai.scripts.audit_operational_surface`;
  confirm baseline holds.

#### M34.2 (SESSION_215) — Acceptance workspace: helper defense + repeated-run proof

**DoD exception path continuation.**

- **Assertion helper change**
  (`acceptance/support/assertions/accounting.ts`):
  - D5 refactor of `fetchSnapshotList` +
    `expectSnapshotCountAtLeast`.
  - `fetchAllJournalEntries` untouched (M22.2 JE-reversal
    journey unaffected).
- **Spec tagging** (three files):
  - `journeys/sales_manager/daily_startup.spec.ts`,
    `journeys/recon/workflow.spec.ts`,
    `journeys/office/accounting_workflow.spec.ts`: add
    `@rerun-hygiene` to `test.describe` string per D7.
- **README update** (`acceptance/README.md`): document the
  `npx playwright test --repeat-each=2 --grep "@rerun-hygiene"`
  invocation per D7 Option A.
- **Repeated-run evidence at M34.2 close:** author runs the
  tagged subset with `--repeat-each=2` locally; records pass
  output in the M34.2 handoff §7.
- **Frontend baseline:** unchanged (Vitest 402 pass; no
  frontend code changes).
- **Acceptance suite:** 25 spec files / 32 tests / ≤37s (allow
  +2s budget for the three seed extensions; measure at close).
- **Audit projection:** unchanged.
- **Two-source agreement gate** at M34.2 close: run audit;
  confirm 162 / 131 / 31 / 321 holds.

Rollback order at M34 close (reverse ship order):

- **M34.2 revert first** — acceptance workspace only; removes
  helper defense + tags + README. Backend regression tests
  continue to pass.
- **M34.1 revert second** — backend commit; removes seed
  extensions + regression tests. Acceptance suite reverts to
  leak-behavior on repeated runs.

M34.1 revertable standalone (M34.2 doesn't depend on it
structurally). Shipping order enforces backend-before-acceptance
for review clarity.

### 5.f DoD compliance check (M21.0 §5.f Option B)

- **M34.1 backend-only** — invocation #9 of exception path. §3
  documents: seed idempotency + Django regression tests have
  zero operator-visible behavior. No shipped operator flow
  changes.
- **M34.2 acceptance-workspace-only** — continuation of
  exception path. No new customer-facing journey added; existing
  three journeys tagged for rerun-proof invocation. Preserves
  operational contract by making the existing 25 journeys more
  durable, but does not add a new operator surface.

M34 is the ninth invocation of the exception path. Pattern firmly
established. **This is also the first fully non-customer-facing
milestone since M20** (all M21 → M33 shipped operator-visible
behavior or extended operator-facing infra). The exception is
justified by the primary operational-coverage lens argument in
§5.a: H protects the durability of every previously-shipped
customer-facing surface.

### 5.g Rollback plan

- **M34.1 rollback:** revert the single commit. Three seed files
  revert to pre-M34 state; test file deletion removes ~3 tests.
  Backend baseline returns to 5,015 pass. Audit returns to
  162 / 131 / 31 / 321 (unchanged). Acceptance journeys resume
  leaking state on reruns.
- **M34.2 rollback:** revert the single commit. Helper reverts
  to `.length`-based counting; `@rerun-hygiene` tags dropped;
  README reverts. Acceptance suite baseline returns to 25 spec
  files / 32 tests. Backend surface stays valid.
- **Reverse-order rollback discipline** (M34.2 → M34.1) matches
  M32.2/M32.3/M32.1 + M33.1/M33.2 shape.

Fixture rollback: the three seed commands revert to their pre-
M34 create-if-missing shape; existing acceptance DB state (CI or
dev) is not corrupted by rollback because the commands remain
idempotent in the weaker sense (won't crash, won't duplicate).

### 5.h Non-goals for M34

- ❌ Do NOT modify any product-code file (views, services,
  models, permissions, URLs, migrations). M34 is seed + test-
  harness only.
- ❌ Do NOT modify the three journey `.spec.ts` files' step
  logic, timeouts, waits, or assertions. Only add
  `@rerun-hygiene` tag to `test.describe` string per D7.
- ❌ Do NOT add sleeps, increase retries, or weaken any
  assertion to mask a failure.
- ❌ Do NOT reset the entire acceptance database between
  individual tests (D4 is a scoped delete on one dealership's
  snapshots, not a full DB wipe).
- ❌ Do NOT extend M34 scope to fix any of the other 22
  journeys unless a failure surfaces during D7 repeated-run
  testing AND belongs to the same non-idempotency class
  (per user directive).
- ❌ Do NOT introduce a shared reset helper across seed
  commands (per feedback_duplicate_small_stable_logic.md —
  three short domain-local resets, not one abstraction).
- ❌ Do NOT change the CI workflow to add DB persistence,
  parallelization, or repeated-run gating. D7 Option A is
  developer-side; Option B is a deferred future upgrade.
- ❌ Do NOT modify the shipped M32.3 Intake Iris or M33.2
  Structure Sam fixtures — they are already independently
  rerunnable per M32 D11 + M33 R7.
- ❌ Do NOT invent a `TrialBalanceSnapshot.fixture_tag` field
  to enable tag-scoped wipes — schema change out of scope; D4
  dealership-scoped wipe is sufficient under the
  `M20_ACCEPTANCE_DB` invariant.
- ❌ Do NOT touch the `--reset` flag semantics on the three
  seed commands — reset remains a manual escape hatch even
  after M34 makes reruns automatic.
- ❌ Do NOT propose changes to any M35 candidate in this
  milestone; the operator-facing candidate list stays exactly
  as recorded in `MILESTONE_33_RETROSPECTIVE.md` §9 unless M34
  evidence materially alters urgency (none anticipated).

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_33_RETROSPECTIVE.md` §9
6. **`docs/roadmap/MILESTONE_34_PLANNING.md`** (this document —
   governing contract for M34)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
8. `docs/CAPABILITY_MATRIX.md` §7θ (M33 shipped surface);
   §7ι added at M34 close
9. `docs/handoffs/SESSION_212_m33_inc2_frontend.md`
10. `docs/roadmap/MILESTONE_20_PLANNING.md` §5.d (compose-
    service-verbs-not-ORM rule for seeds; superseded at M34
    for reset-scoped ORM queries per D2 + D3 + D4)
11. Memory record
    `feedback_duplicate_small_stable_logic.md` (M28.0 origin —
    governs D1 no-shared-helper decision)
12. Memory record
    `feedback_playwright_as_operational_contract.md` (M33 D8
    strengthening invocation; M34 preserves the contract by
    making it rerun-safe)
13. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — applied at §4.5 for cascade behavior on
    ReconDecision.finding OneToOne)
