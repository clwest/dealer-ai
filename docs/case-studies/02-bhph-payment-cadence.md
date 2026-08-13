# BHPH Payment Cadence

Buy-here-pay-here (BHPH) customers do not pay monthly. They pay
Friday. Amortizing a BHPH loan against a 12-month/year calendar
misprices every deal and misreads every collection cycle.

## Context

Standard retail auto financing uses monthly amortization: 12
periods per year, monthly APR = annual APR / 12. That works when
customers have bank accounts, direct deposit, and mortgage-style
payment behavior.

BHPH customers — the credit-challenged buyers an independent
dealer's own finance operation serves — typically do not. They get
paid weekly or biweekly, in cash or by check that they cash the
same day, and they pay their car note by driving down to the lot
on the same schedule. The dealership operator sees them 52 times a
year on a weekly note, 26 times on a biweekly note. That contact
cadence is not incidental; it is the collections mechanism.

Pricing a BHPH deal against a monthly amortization schedule
mispresents the customer's obligation and disconnects the payment
plan from the customer's actual cash flow. The engine had to
support both cadences as first-class citizens.

## Diagnosis

Two payment engines share the same module but do not share the
period model: `backend/dealer_ai/services/payment_engine.py`.

Standard-APR amortization (used for retail deals through F&I):

```python
def estimate_payment(price, down_payment=0.0, apr=7.49, term_months=72, ...):
    monthly_rate = (apr / 100.0) / 12.0
    n = term_months
    financed = max(0.0, price - down_payment - trade_in_value)
    monthly_payment = (
        financed * monthly_rate * (1 + monthly_rate) ** n
        / ((1 + monthly_rate) ** n - 1)
    )
```

BHPH amortization (used when the dealership is the lender):

```python
BHPHCadence = Literal["weekly", "biweekly"]
CADENCE_PERIODS = {"weekly": 52.0, "biweekly": 26.0}

def estimate_bhph_payment(price, apr, term_months, cadence, ...):
    periods_per_year = CADENCE_PERIODS[cadence]
    n = int(round(term_months * periods_per_year / 12.0))
    periodic_rate = (apr / 100.0) / periods_per_year
    ...
```

The BHPH function also enforces a portfolio-typical minimum down
payment (approximately 15–20% of sticker), reflecting the fact
that subprime defaults are higher and the dealer's own capital is
at risk. `bhph_min_down_payment(price)` returns the policy floor;
callers refuse to quote a deal below it.

## Correction

Cadence is not derivable from the term. A 24-month BHPH note on a
weekly schedule is 104 periods; on a biweekly schedule it is 52
periods; a monthly retail equivalent is 24. Every downstream
calculation — allocation of interest vs. principal, delinquency
buckets, collection contact scheduling — reads the cadence field
directly rather than inferring it.

Payment allocation (interest → fees → principal, in that order)
is tested exhaustively in
`backend/dealer_ai/tests/test_m122_bhph_payment_allocation.py` —
19 cases covering weekly and biweekly cadences, overpayment,
missed periods, and partial catch-up.

## Verification

Two dedicated test files pin the math:

- `test_bhph_payment_engine.py` — 16 tests covering cadence
  conversion (52/26 periods), APR at 21.9% default, interest
  accrual over 30-month terms, trade-in and down-payment reduction
  of the financed amount, minimum-down floor.
- `test_m122_bhph_payment_allocation.py` — 19 tests covering the
  interest-first split, fee prioritization, principal reduction,
  and overpayment handling.

The Playwright BHPH journey
(`acceptance/journeys/bhph/payment_intake.spec.ts`) exercises the
end-to-end flow: record a weekly payment, verify the account
balance, verify the interest/principal split matches the engine's
computed values.

## Lasting Effect

The cadence field cascades through the entire BHPH domain:
delinquency detection reads it to compute how many periods a
customer is behind; the promise-to-pay grace period respects it
(a weekly customer who broke a promise is materially different
from a biweekly one at the same clock time); the collections
contact log is scheduled against the customer's next payday, not
the calendar.

The pattern also documents a boundary between generic SaaS payment
math (which almost always assumes monthly) and BHPH-specific math
(which cannot). Any future work that involves BHPH — repossession
accounting, note-refinance, deficiency judgments — inherits this
model of "period is the unit, not the month."
