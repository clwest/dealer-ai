# Case Studies

Seven curated engineering stories from the 219-session build record.
These are the strongest concrete examples of dealership-domain
decisions and engineering process — the ones worth pulling out of
the broader handoff archive because they show *how* the software
absorbed operator knowledge and empirical failure.

Each case study follows the same shape: **Context → Diagnosis →
Correction → Verification → Lasting Effect** (some sections are
skipped where they don't apply). Every file cites the actual code
and the actual handoff session where the decision was recorded.

1. [Recon reconsideration lock](01-recon-reconsideration-lock.md)
   — Why recon tier decisions are mutable until work is authorized,
   then locked. A dealership-operational rule enforced in the
   service layer, not the database.
2. [BHPH payment cadence](02-bhph-payment-cadence.md)
   — Why buy-here-pay-here loans are amortized weekly or biweekly,
   not monthly. Priced to the payday, not the calendar.
3. [Playwright rerun hygiene](03-playwright-rerun-hygiene.md)
   — How a planning-time assumption about `--repeat-each` was
   empirically falsified and turned into a durable rerun-invariant
   pattern.
4. [Postgres OuterRef verification](04-postgres-outerref-verification.md)
   — Spinning up an ephemeral Postgres to verify a nested-Subquery
   annotation compiles, instead of shipping and hoping the ORM did
   the right thing.
5. [Lender submission projection correction](05-lender-submission-projection-correction.md)
   — A mid-implementation scope amendment that traced back to a
   deliberate omission in the prior increment's projection.
6. [Accounting immutability + reversal](06-accounting-immutability-reversal.md)
   — Why journal entries are never mutated and how reversal
   entries preserve the audit trail without a "who edited what"
   history.
7. [Indie / franchise compliance scrub](07-indie-franchise-compliance-scrub.md)
   — Same code, different rules per dealer type. The post-LLM
   scrub that strips OEM captive lenders, CPO claims, and 0% APR
   when the profile is independent.

These stories are the reason the 219-session handoff record exists.
The rest of the archive is preserved locally but excluded from the
public tree.
