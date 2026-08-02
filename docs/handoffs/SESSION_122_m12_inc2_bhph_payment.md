---
title: "SESSION_122 handoff — Milestone 12 · Increment 2 (M12.2 — BhphPayment intake + application)"
status: historical
type: handoff
date: 2026-08-02
session: 122
milestone: 12
milestone_status: in_progress
increment: 2
increment_status: shipped
commit: TBD
---

# SESSION_122 — Milestone 12 · Increment 2 (M12.2 — BhphPayment intake + application)

## What shipped

Second BHPH-portfolio entity
(`BhphPayment`) + payment allocation
math + service package + two DRF
endpoints. Per
`MILESTONE_12_PLANNING.md` §1.2 +
§5.b Option A (locked at SESSION_121
open — no §5 decisions to confirm at
M12.2 open).

Streak stands at **41 planning-time
as-recommended M5.1 → M12.1** (M12.2
inherited §5.b — not a new
resolution).

## By the numbers

- **Backend baseline: 3,986 pass, 1
  skipped, 0 fail** (was 3,944 at
  M12.1 close — **+42 tests, 0
  regressions**).
- **Frontend Vitest baseline: 67
  pass** (unchanged — no frontend
  at M12.2).
- **Migrations `0038`**
  (`0038_m122_bhph_payment_entity`).
- **Tenancy carriers: 40 → 41**
  (`BhphPayment` registered in
  `services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`).
- **DRF admin surface: 84 → 86**
  (`admin-bhph-payment-create` +
  `admin-bhph-payment-list`).
- **Frontend operator routes:** 15
  (unchanged).
- **Permission classes: 8**
  (unchanged — reused M4
  `IsSalesManagerOrOwnerAtActiveDealership`;
  zero drift, matching M11/M12.1
  posture).
- **`Vehicle.is_available`:**
  unchanged.
- **Celery-beat task families: 6**
  (unchanged — no detector at
  M12.2; M12.3 lands the aging
  detector).

## Files touched

### New
- `backend/dealer_ai/services/bhph_payments/__init__.py`
- `backend/dealer_ai/services/bhph_payments/apply.py`
  (pure allocation math)
- `backend/dealer_ai/services/bhph_payments/bhph_payment.py`
  (write + list verbs)
- `backend/dealer_ai/views_bhph_payments.py`
- `backend/dealer_ai/migrations/0038_m122_bhph_payment_entity.py`
- `backend/dealer_ai/tests/test_m122_bhph_payment_model.py`
  (7 tests)
- `backend/dealer_ai/tests/test_m122_bhph_payment_allocation.py`
  (18 tests)
- `backend/dealer_ai/tests/test_m122_bhph_payment_service.py`
  (8 tests)
- `backend/dealer_ai/tests/test_m122_bhph_payment_endpoint.py`
  (9 tests)
- `docs/handoffs/SESSION_122_m12_inc2_bhph_payment.md`
  (this file)

### Modified
- `backend/dealer_ai/models.py` — added
  `BhphPayment` model + method vocab
  constants at end (matches M12.1
  layout).
- `backend/dealer_ai/services/tenancy.py`
  — extended
  `_TENANT_CARRIER_MODEL_NAMES` 40 →
  41.
- `backend/dealer_ai/urls.py` — two
  new admin paths nested under
  `/admin/bhph-notes/<pk>/payments/`.
- `00-START-NEXT-SESSION.md` —
  flipped to SESSION_123 · M12.3
  priority.

## What the endpoints do

### `POST /admin/bhph-notes/<pk>/payments/`

Nested under the note per RESTful
convention (payments always belong
to a note).

Body: `paid_at` (ISO datetime),
`amount` (Decimal), `method`
(cash / check / debit / ach / other).

Behavior:
- Cross-tenant note → 404
  (fail-closed).
- Missing note → 404.
- Invalid method → 400 (serializer
  ChoiceField rejects).
- Overpayment
  (amount > outstanding_balance +
  interest_owed + outstanding_fees)
  → 400. Refund / reversal is a
  M12+ decision; silent absorption
  refused.
- Amount exceeding
  DecimalField(8,2) max → 400
  (serializer).

Response:
`{ "bhph_payment": { ..., "applied_to_fees", "applied_to_interest", "applied_to_principal", ... } }`
with denormalized allocation
columns populated at write time
via the pure `allocate_payment`
verb.

### `GET /admin/bhph-notes/<pk>/payments/list/`

Response:
`{ "count": N, "results": [ ... ] }`
— ordered by `-paid_at`,
`-created_at` (Meta ordering).

## Application order (§5.b Option A)

Platform-wide constant:
**fees → interest → principal.**

Fees are always **0** at M12.2 (no
fee-charging entity exists yet).
Column preserved so a future M12.5+
late-fee / NSF-fee entity can
allocate without a schema change.

Interest computed per-period from
current outstanding balance:

    period_rate =
        note.apr / periods_per_year / 100
    interest_owed =
        outstanding_balance * period_rate

Principal is the remainder after
fees + interest. Overpayment raises.

Outstanding balance recomputed on
every intake:

    outstanding_balance =
        note.principal_financed
        - SUM(applied_to_principal
              across prior payments)

## Non-goals honored

- ❌ No delinquency detection
  (M12.3).
- ❌ No PTP tracking (M12.4).
- ❌ No collections (M12.5).
- ❌ No repossession (M12.6).
- ❌ No portfolio analytics or UI
  (M12.7).
- ❌ No refunds / reversals
  (deferred beyond M12).
- ❌ No configurable application
  order (§5.b constant).
- ❌ No fee-charging entity.

## Design notes worth remembering

### Split pure verb from write verb
`allocate_payment(amount,
outstanding_balance_now,
interest_owed, outstanding_fees)`
is truly pure — no DB access. Tests
lock its math surface with
`SimpleTestCase`. `record_payment`
handles DB-facing balance
recomputation independently
(queries `BhphPayment` aggregate
sum, calls the pure verb, persists
inside `transaction.atomic`).

### Overpayment refused, not absorbed
`OverpaymentError` maps to 400.
Silent absorption would corrupt
payoff math (a $100 payment
allocated as $95 principal + $5
"applied elsewhere" leaves the
note under-tracked). Refund /
reversal is M12+ scope.

### Interest computed from live balance
Not from a schedule. Because M12.1's
`get_payment_schedule` returns
equal-installment quotes for the
buyer, but real intake often
diverges from schedule (partial
payments, timing drift, prepayment).
The intake path always computes
current interest from current
balance so allocation stays accurate
regardless of schedule adherence.

### Nested route under BhphNote
`POST /admin/bhph-notes/<pk>/payments/`
follows RESTful nesting — a payment
never exists without a parent note.
No top-level `/admin/bhph-payments/`
surface.

### transaction.atomic on write
Serializes concurrent `record_payment`
calls on the same note so the
balance snapshot stays consistent.
Matches M9.1 `record_sale` pattern
for concurrent-safety on
denormalized aggregates.

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_12_PLANNING.md`
   §1.2 + §5.b + §7 M12.2
4. `docs/handoffs/SESSION_121_m12_inc1_bhph_note.md`
   (previous session)
5. `backend/dealer_ai/services/bhph_payments/apply.py`
6. `backend/dealer_ai/services/bhph_payments/bhph_payment.py`
7. `backend/dealer_ai/models.py::BhphPayment`
