# Postgres OuterRef Verification

Spin up the real database before you ship code that assumes the
ORM did the right thing.

## Context

M35.0 planning specified a nested Subquery annotation for the
lender-submission FK discovery endpoint. The outer query annotates
each credit application with the status of its latest lender
submission — using a Subquery that references an OuterRef whose
value comes from another Subquery annotation defined at M33.1.

Nested Subquery correlation with OuterRef is legal Django ORM
syntax. Whether it compiles to valid SQL on a given database
backend is another question. SQLite was known to compile it
(that's what dev and CI use). Postgres was the production target
and had never been exercised against this specific pattern.

Risk R11 in the M35.0 planning memo flagged the possibility of
Postgres compilation failure and reserved a fallback (rewrite the
annotation without nesting). The safe path was to ship on SQLite
and discover the problem when the first production query ran on
Postgres. The disciplined path was to verify empirically before
committing.

## Correction

At M35.1 open, an ephemeral Postgres 15.13 database was spun up
locally, the full Dealer AI migration graph was applied to it, and
the M35.0 §4.8 shell test was executed verbatim against the live
Postgres connection.

The result:

- `POSTGRES_COMPILED_OK` — the ORM produced valid Postgres SQL
  without raising a translation error.
- `POSTGRES_EXECUTED_OK` — the SQL executed and returned the
  expected annotated rows.
- SQL length: 1620 characters — identical to the SQLite compilation.

The temp database was dropped after verification.

## Verification

Risk R11 was demoted from "may require fallback rewrite" to
resolved. The planning memo update recorded the specific commit
producing the empirical result and the timestamp of the temp-DB
teardown, so a future reader can reproduce the check.

The M35.1 implementation shipped the nested-Subquery annotation as
originally specified. Zero-drift cadence between M35.0 planning
and M35.1 implementation was preserved (38 → 39 backend-only
endpoints, exactly as planned).

## Lasting Effect

This is the pattern for any risk that hinges on "does the
underlying tool behave the way the docs say?" — the answer is
almost never speculation and almost always cheap to verify against
the real system.

Preserving the disciplined rewrite path (the R11 fallback plan)
even when it turned out not to be needed also had value: had the
verification failed, the correction was already scoped and could
have shipped without extending the milestone window. Planning
against the pessimistic branch and then discovering the optimistic
outcome is a fine outcome; planning against only the optimistic
branch and discovering the pessimistic outcome is a milestone-
level miss.
