---
title: "SESSION_124 handoff — Milestone 12 · Increment 4 (M12.4 — PTP tracking)"
status: historical
type: handoff
date: 2026-08-02
session: 124
milestone: 12
milestone_status: in_progress
increment: 4
increment_status: shipped
commit: TBD
---

# SESSION_124 — Milestone 12 · Increment 4 (M12.4 — PTP promise-to-pay tracking)

## What shipped

Third BHPH-portfolio entity
(`BhphPromiseToPay`) + three verbs
+ state-transitioning Celery
detector at 09:00 daily + four DRF
endpoints. Per
`MILESTONE_12_PLANNING.md` §1.4 +
§5.d Option A (operator-triggered
reconciliation locked at
SESSION_121 open).

Mirrors the M11.5 BeBack state
machine (promised → kept / broken)
with an added
:class:`BhphPayment` reference on
the `mark_kept` transition per
§5.d.

**Four §0.a M12.4 open decisions
recorded as-recommended:**

1. **Promised-reason vocab** —
   PTP-specific 3+1 vocab
   (`paycheck` / `tax_refund` /
   `family_help` / `other`).
2. **Broken detector cadence** —
   09:00 project-time daily.
3. **Broken grace period** —
   `BHPH_PTP_BROKEN_GRACE_HOURS`
   env default 24.
4. **Reconciliation shape** —
   operator-triggered
   `mark-kept` endpoint accepting
   `bhph_payment_id`.

Streak stands at **41 planning-time
as-recommended M5.1 → M12.1** (§0.a
implementation-time decisions don't
count against streak per M10 §9).

## By the numbers

- **Backend baseline: 4,058 pass, 1
  skipped, 0 fail** (was 4,024 at
  M12.3 close — **+34 tests, 0
  regressions**).
- **Frontend Vitest baseline: 67
  pass** (unchanged — no frontend
  at M12.4).
- **Migrations `0040`**
  (`0040_m124_bhph_promise_to_pay`).
- **Tenancy carriers: 41 → 42**
  (`BhphPromiseToPay` registered).
- **DRF admin surface: 86 → 90**
  (four new endpoints — create /
  list / mark-kept / mark-broken).
- **Frontend operator routes:** 15
  (unchanged).
- **Permission classes: 8**
  (unchanged).
- **Celery-beat task families:
  7 → 8** (new M12.4 broken-PTP
  detector at 09:00).

## Files touched

### New
- `backend/dealer_ai/services/bhph_promises/__init__.py`
- `backend/dealer_ai/services/bhph_promises/bhph_promise.py`
  (three verbs)
- `backend/dealer_ai/services/bhph_promises/tasks.py`
  (per-tenant task + orchestrator)
- `backend/dealer_ai/views_bhph_promises.py`
  (four endpoints)
- `backend/dealer_ai/migrations/0040_m124_bhph_promise_to_pay.py`
- `backend/dealer_ai/tests/test_m124_bhph_promise_model.py`
  (8 tests)
- `backend/dealer_ai/tests/test_m124_bhph_promise_service.py`
  (11 tests)
- `backend/dealer_ai/tests/test_m124_bhph_promise_detector.py`
  (5 tests)
- `backend/dealer_ai/tests/test_m124_bhph_promise_endpoint.py`
  (10 tests)
- `docs/handoffs/SESSION_124_m12_inc4_ptp.md`
  (this file)

### Modified
- `backend/dealer_ai/models.py` — added
  `BhphPromiseToPay` model + vocab
  constants at end.
- `backend/dealer_ai/services/tenancy.py`
  — extended
  `_TENANT_CARRIER_MODEL_NAMES` 41
  → 42.
- `backend/dealer_ai/urls.py` — four
  new admin paths.
- `backend/dealer_kit/settings.py`
  — registered
  `bhph-broken-ptp-detector-daily-09-00`
  + `BHPH_PTP_BROKEN_GRACE_HOURS`
  env setting.
- `00-START-NEXT-SESSION.md` —
  flipped to SESSION_125 · M12.5
  priority.

## State machine

Two terminal states + one initial:

```
promised ──mark_kept──▶ kept   (+ actual_payment)
    │
    └────mark_broken──▶ broken (detector-triggered auto or manual)
```

**No re-transitions** from
terminal. Terminal is final at
M12.4 (matches M11.5 posture — a
future `reopen` verb can add the
un-do path when operator UI
surfaces the need).

## Reconciliation shape (§5.d Option A)

Operator identifies which
:class:`BhphPayment` fulfilled the
promise; the endpoint accepts
`bhph_payment_id` and the service
verb links the two. Cross-tenant
checks are belt+suspenders:

- `payment.dealership == promise.dealership` (tenant match).
- `payment.note_id == promise.note_id` (payment against the same
  note the promise is on).

Both mismatches raise
`CrossPromisePaymentError` → 400.

**No auto-reconciliation.** A
BhphPayment landing on the same
note that has an open promise
does NOT auto-link — the operator
makes the linkage explicitly.
This preserves audit clarity: a
kept promise is always a
deliberate operator judgment.

## Non-goals honored

- ❌ No collections (M12.5).
- ❌ No repossession (M12.6).
- ❌ No portfolio analytics or UI
  (M12.7).
- ❌ No auto-payment
  reconciliation (§5.d Option A
  ruled out auto-linking).
- ❌ No configurable promised-
  reason vocab.
- ❌ No `reopen` transition from
  terminal states.

## Design notes worth remembering

### Detector uses simple queryset .update()
`stale_qs.update(state=broken)`
is one bulk SQL update, no per-row
`save()` calls. Matches M11.5
no-show detector shape. Trade-off:
`updated_at` gets set to now for
all transitioned rows, but no
`pre_save` / `post_save` signals
fire — acceptable at M12.4
because there are no PTP signal
listeners.

### `mark_kept` requires payment
The operator must supply
`bhph_payment_id` at the endpoint
layer — no path exists to mark
kept without a payment reference.
This enforces the §5.d Option A
audit trail: a kept promise
always points to the specific
payment that fulfilled it.

### `mark_broken` populates no payment
By definition — a broken promise
has no fulfilling payment. The
`actual_payment` FK stays null on
both `promised → broken`
transitions (detector-triggered
and operator-triggered).

### Reason vocab tailored to BHPH
Distinct from M11.5 BeBack reasons
(`test_drive` / `bring_co_signer`
/ `bring_trade_in` / `other`).
PTP-specific reasons match what
customers actually cite:
`paycheck`, `tax_refund`,
`family_help`, `other`. Extension
defers to operator evidence per
M11.1 vocab-set pattern.

### 09:00 slot after M12.3 08:00
Non-overlapping-window pattern
preserved (M7.2 02:00, M7.3 03:00,
M7.4 04:00, M7.5 05:00, M11.4
06:00, M11.5 07:00, M12.3 08:00,
M12.4 09:00).

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_12_PLANNING.md`
   §1.4 + §5.d + §7 M12.4
4. `docs/handoffs/SESSION_123_m12_inc3_delinquency.md`
   (previous session)
5. `backend/dealer_ai/services/bhph_promises/`
6. `backend/dealer_ai/services/be_backs/`
   (M11.5 shape mirrored)
7. `backend/dealer_ai/models.py::BhphPromiseToPay`
