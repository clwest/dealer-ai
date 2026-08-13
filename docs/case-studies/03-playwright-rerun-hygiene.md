# Playwright Rerun Hygiene

A planning-time assumption about a test-runner flag turned out to
be wrong. Empirical verification caught it, the mechanism was
replaced, and the pattern was codified as a durable engineering
lesson.

## Context

Playwright acceptance tests share one seeded database across
journeys (M20.5 committed to serialized workers to avoid parallel
mutation races). Each spec depends on deterministic seeded state;
if a journey mutates the DB in a way that leaves the invariant
broken for the next journey, tests fail non-deterministically on
CI.

M34.0 introduced `_restore_rerun_invariants()` — seed helpers
called between test runs to restore the shape the next journey
expects. To prove rerun-hygiene, the planning memo specified
Playwright's `--repeat-each=2` flag as the verification mechanism:
run the tagged spec set twice against the same DB and confirm both
runs pass.

## Diagnosis

Empirical verification at M34.2 open produced **3 failed / 10
passed** on the second repetition. The assumption that
`--repeat-each` would exercise the between-run restoration was
wrong: the flag reruns test bodies within a *single Playwright
invocation* without re-invoking the setup project. Seeds'
`_restore_rerun_invariants()` fire once at the start of the
invocation and never between repetitions. The second pass runs
against DB state left over from the first pass, not restored
state.

This was not a flaky test problem; it was a wrong theory of what
the flag does. The fix could not be "quiet the failing tests" —
the failing tests were correct.

## Correction

The proof mechanism was replaced with two back-to-back full
invocations of the tagged spec set:

```bash
npx playwright test --grep "@rerun-hygiene"
npx playwright test --grep "@rerun-hygiene"
```

Each invocation runs the setup project, which fires
`_restore_rerun_invariants()` before the test bodies run. If the
DB is genuinely being restored between runs, both invocations
pass. If the first run leaves state that the seed helpers do not
restore, the second run fails on the mutation.

The M34.2 empirical proof: **10 passed / 19.9s (run 1) + 10
passed / 15.9s (run 2)** against the same database. The cache-warm
delta between runs was expected and matched.

## Verification

`@rerun-hygiene` is now a tag applied to any Playwright spec whose
outcome depends on the seed restoration invariant. As of M35.2 the
tagged set is four specs; the second-run pattern still passes.

The invariant restoration helpers themselves are pinned by
backend unit tests in
`backend/dealer_ai/tests/test_m34_inc1_seeds.py` (M34.1) — the
same shape is asserted at every incremental restoration point.

## Lasting Effect

The lesson was tracked as durable-lesson `(cc)` —
**coverage-projection truthfulness** — and elevated to
"load-bearing across three milestones" after two more
independent manifestations (M34.1 test-count decomposition and
M35.1 audit-artifact projection). The written rule now applied
by planning-time decisions:

> Any assertion about "the tool does X" in a planning memo must
> be validated against the tool's actual behavior before it is
> used as the proof mechanism for a milestone.

The `_restore_rerun_invariants()` seed pattern itself was
recognized as durable-lesson `(ff)`, load-bearing across at least
two milestones — every new shared-DB journey inherits the same
restoration contract.

Beyond the specific fix, this is a case study in refusing to
demote a failing test into a flaky one. The failure was
information; the correction was to change the mechanism, not to
retry until green.
