# AI-Assisted Development Disclosure

This project was built by one person (Chris West, an automotive
industry operator turned software builder) working with Claude
Code (Anthropic's CLI coding agent) over approximately 14 weeks —
May 1 to August 5, 2026 — across 219 numbered engineering
sessions and 344 commits.

The bulk of the implementation was written by Claude Code. The
engineering judgment — what to build, what to defer, how to
verify assumptions, how to respond to empirical failure — was
human.

## What the model did

- Wrote the Python and TypeScript implementation for most
  features across the 35-milestone build.
- Produced the initial drafts of the milestone planning memos
  and per-session handoff documents (219 total in
  `docs/_internal/handoffs/`).
- Drafted the tests that pin down each milestone's contract,
  under the discipline of "one test per invariant."
- Populated the research corpus in `docs/research/` from
  operator conversations Chris relayed into the session context.

## What Chris did

- Defined the product requirements — the dealership workflows,
  the tenant/role model, the compliance boundaries, the pilot
  scope.
- Made every scope decision: what shipped in each milestone,
  what was deferred, what was killed.
- Directed the milestone loop: each milestone opened with a
  planning increment (0.a), shipped in one or more
  implementation increments, and closed with a retrospective.
  Chris was the person choosing the target and validating the
  outcome; the model produced the code.
- Enforced runtime verification. Planning-time claims about
  tool behavior, ORM behavior, seed-fixture behavior were
  validated empirically rather than accepted at face value.
- Captured the operational reasoning behind dealership-specific
  decisions from years of automotive-industry experience.

## Five concrete examples where Chris's decisions materially
changed the implementation

Each of these was a moment where accepting the model's default
would have produced a worse outcome. All are documented in more
detail in [`docs/case-studies/`](docs/case-studies/) and in the
session handoff record.

1. **Deferring 9 of 10 candidates in M34 planning.** M34.0
   evaluated ten possible targets. The model would have
   defaulted to the one with the most features. Chris framed
   the discovery rule — "which documented business problem does
   this solve, and is solving it required for the current
   milestone?" — and deferred nine on the grounds of no pilot
   evidence, no operational demand, or premature scope. M34
   became a test-hygiene remediation because that was the only
   candidate that had *actually failed* three shared-DB
   journeys across six milestones.

2. **Verifying nested-OuterRef on real Postgres before shipping
   the M35.1 annotation.** The planning memo flagged risk R11
   (nested Subquery correlation might not compile on Postgres
   as it does on SQLite). The model was ready to ship on
   SQLite and let the fallback handle a production failure.
   Chris insisted on empirical verification against an
   ephemeral Postgres 15 database. Result: the SQL compiled
   identically. Risk R11 was demoted, the fallback was
   unneeded, and the pattern generalized as "verify against the
   real system before shipping." Case study
   [04](docs/case-studies/04-postgres-outerref-verification.md).

3. **Abandoning `--repeat-each` after empirical failure.**
   M34.0 specified Playwright's `--repeat-each=2` as the proof
   mechanism for rerun-hygiene. Empirical run produced 3
   failed / 10 passed. The default response would have been to
   quarantine the failing tests as flaky. Chris insisted on
   root-causing the flag's actual behavior; the flag reruns
   test bodies within a single invocation without re-firing
   setup projects. The correction was back-to-back full
   invocations, and the lesson was elevated as durable-lesson
   `(cc)`, load-bearing across three subsequent milestones.
   Case study [03](docs/case-studies/03-playwright-rerun-hygiene.md).

4. **Recon reconsideration lock (SESSION_067).** The generic
   database default is either "everything is mutable" or
   "everything is immutable." Neither is right for recon.
   Managers legitimately reconsider tier decisions until a work
   order is authorized; once labor is authorized, the record
   must freeze. This distinction only comes from someone who
   has been in the recon operational cycle. Chris supplied it;
   the model implemented it as a service-layer policy with
   row-locking on state transitions. Case study
   [01](docs/case-studies/01-recon-reconsideration-lock.md).

5. **M35.2 lender-submission projection amendment as legitimate
   scope correction.** During M35.2 frontend implementation,
   the response form needed a submission id that M35.1's
   deliberately narrow projection had omitted. The default
   response would have been to open a new endpoint (scope
   creep) or defer the work (scope violation). Chris framed the
   correct middle path — widen the existing annotation by two
   lines without adding a new endpoint — and documented it as a
   §0.a scope amendment, not scope creep. Case study
   [05](docs/case-studies/05-lender-submission-projection-correction.md).

## What this pattern proves and what it doesn't

**It proves:** the ability to define a product, direct
milestone-scale engineering work, verify runtime behavior,
recognize when a planning assumption has been falsified, and
translate operational domain knowledge into software
constraints.

**It does not prove:** ability to hand-author every line of the
implementation, or ability to work in a team environment with
review culture and disagreement. Every commit is authored by
`chris@donkeybetz.com`.

## The honest engineering model

At the scale this project ships at, the model-vs-human question
is not "who typed the code?" It is "who made the decisions, who
took responsibility for the runtime, and who recognized when the
model produced something wrong?" Those answers, in this
repository, are all one person.

That is a legitimate way to build software. It is also a
different mode from a team environment, and interview
conversations about this repository should address both what it
proves and what it does not.
