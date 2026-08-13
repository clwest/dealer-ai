# Indie / Franchise Compliance Scrub

Same code, different rules per dealer type. The post-LLM scrub
that strips OEM captive lender names, CPO claims, and 0% APR when
the dealer profile is independent.

## Context

An independent used-car dealer cannot legally advertise "Ford
Credit approved!" — they do not have access to captive
manufacturer finance. They cannot claim "Certified Pre-Owned"
(CPO) — that is a manufacturer-issued designation. They cannot
offer "manufacturer warranty" on used vehicles. They typically
cannot quote "0% APR" — subprime funding does not price that low.

A franchise dealer of the same brand *can* claim all of these
things, legally and truthfully.

The LLM does not know which of these constraints applies to the
dealer it is currently representing. It has been trained on a
corpus that contains every dealer type. Absent enforcement, it
will happily hallucinate captive-lender approval or CPO status,
and the customer will hear something the dealer cannot back up —
compliance violation, reputational damage, and a lost sale.

## Correction

The post-LLM scrub in
`backend/dealer_ai/services/llm_safety.py` (approximately lines
103–174) runs after every model response and before the customer
sees it. When the dealer profile is independent
(`dealer_profile.dealer_type == "independent"`), the scrub applies
a set of regexes:

- Captive lender names are replaced with a generic phrase:
  `Ford Credit`, `Toyota Financial`, `Honda Financial`,
  `GM Financial`, `Nissan Motor Acceptance`, `Chrysler Capital`
  → `our lending partners`.
- CPO language and manufacturer-warranty claims are stripped:
  `certified pre-owned`, `CPO`, `manufacturer's warranty`,
  `factory warranty`, `manufacturer-backed`.
- Adjective claims that only apply to new vehicles are downgraded:
  `brand new` → `great-condition`.
- Rate claims that indies cannot support are deleted outright:
  `0% APR`, `zero percent financing` → `""` (empty).

The replacement policy differs deliberately. Substantive
adjective claims are *replaced* with a substitute so the output
stays fluent for the customer. False rate claims are *deleted*
because there is no honest short substitute — "some financing
available" is not equivalent to "0% APR" and would read as an
awkward patch.

The scrub is gated on dealer type:

```python
if dealer_profile.dealer_type != "independent":
    return response_text   # franchise → no indie scrubs apply
```

A franchise Ford store can legitimately say "Ford Credit" and
"0% APR" — the scrub is not applied in that configuration. Same
code, same LLM prompt, different runtime behavior based on
profile.

## Verification

Compliance scrubs are the most thoroughly tested subsystem in the
repo:

- `test_wac_compliance.py` — 17 tests: rate-inquiry pre-LLM
  guard, APR/interest-rate regex scrub, W.A.C. qualifier
  injection, backend payment math unchanged (estimate computed
  but not disclosed).
- `test_m107_compliance.py` — post-LLM prohibited-terms list:
  invented APR, false urgency, false approval guarantees.
- `test_m125_collection_language_scrub.py` — FDCPA-adjacent
  scrub for BHPH collection scripting.
- `test_cash_mode_financing_scrub.py`,
  `test_following_question_scrub.py` — additional post-LLM
  scrubbers with the same test discipline.

The scrub set was also validated against a curated 21-case
negative corpus during M25 — phrases that *look* like violations
but are legitimate (e.g. "we don't offer 0% APR, but here's what
we can do") that must pass through unchanged. The regexes are
narrow by design; false positives are more damaging than the
occasional false negative because they degrade fluency without
adding safety.

## Lasting Effect

The pattern generalized. Any post-LLM safety rule that depends on
dealer configuration follows the same shape:

- Regexes at module scope, tested as pure functions.
- Gate on `dealer_profile.<attribute>` at the callsite.
- Replacement policy varies by claim type: adjective replacements
  preserve fluency, false-fact deletions accept a small
  fluency cost.

The load-bearing insight is that compliance for independent
dealers is *not the same product* as compliance for franchise
dealers. The naive approach — a single system prompt telling the
LLM the rules — does not survive contact with model drift.
Structural regex enforcement runs after every response and
catches what the prompt did not.

This is also the strongest signal in the codebase that the design
came from someone who has read dealer compliance bulletins and
understands the specific claims each dealer type can and cannot
make. The list of captive lenders and the specific replacement
strings are the kind of detail that does not come from reading a
general "auto retail" article.
