---
title: "SESSION_121 handoff — Milestone 12 · Increment 1 (M12.1 — BhphNote origination + payment schedule)"
status: historical
type: handoff
date: 2026-08-02
session: 121
milestone: 12
milestone_status: in_progress
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_121 — Milestone 12 · Increment 1 (M12.1 — BhphNote origination + payment schedule)

## What shipped

Milestone 12 opens. First BHPH-portfolio
entity (`BhphNote`) + amortization math
verbs + service package + endpoints
per `MILESTONE_12_PLANNING.md` §7 M12.1
and §5.a Option A.

**Six planning-time §5 decisions
confirmed as-recommended at M12.1 open**
— streak stands at **41 planning-time
as-recommended M5.1 → M12.1**.

- §5.a: Option A (no M10.5 vocab change;
  M9 `Sale.finance_type == "bhph"` is the
  BHPH signal).
- §5.b: Option A (payment application
  order platform-wide constant — locked
  for M12.2 consumption).
- §5.c: Option A (fixed 7-value aging
  vocab — locked for M12.3).
- §5.d: Option A (operator-triggered
  PTP reconciliation — locked for M12.4).
- §5.e: Option A (extend existing
  `services/llm_safety.py` scrub stack
  at M12.5).
- §5.f: Option C (MVP operator UI at
  M12.7 — portfolio dashboard + note
  detail; collection contact + repo UI
  defer).

## By the numbers

- **Backend baseline: 3,944 pass, 1
  skipped, 0 fail** (was 3,895 at M11
  close — **+49 tests, 0 regressions**).
- **Frontend Vitest baseline: 67 pass**
  (unchanged — no frontend at M12.1).
- **Migrations `0037`**
  (`0037_m121_bhph_note_entity`).
- **Tenancy carriers: 39 → 40**
  (`BhphNote` registered in
  `services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`).
- **DRF admin surface: 82 → 84**
  (`admin-bhph-note-create` +
  `admin-bhph-note-retrieve`).
- **Frontend operator routes:** 15
  (unchanged).
- **Permission classes: 8** (unchanged
  — reused M4
  `IsSalesManagerOrOwnerAtActiveDealership`;
  zero drift, matching M11 posture).
- **`Vehicle.is_available`:**
  unchanged.
- **Celery-beat task families: 6**
  (unchanged — no detector at M12.1).

## Files touched

### New
- `backend/dealer_ai/services/bhph_notes/__init__.py`
- `backend/dealer_ai/services/bhph_notes/bhph_note.py`
- `backend/dealer_ai/views_bhph_notes.py`
- `backend/dealer_ai/migrations/0037_m121_bhph_note_entity.py`
- `backend/dealer_ai/tests/test_m121_bhph_note_payment_engine.py`
  (18 tests)
- `backend/dealer_ai/tests/test_m121_bhph_note_model.py` (8 tests)
- `backend/dealer_ai/tests/test_m121_bhph_note_service.py`
  (12 tests)
- `backend/dealer_ai/tests/test_m121_bhph_note_endpoint.py`
  (11 tests)
- `docs/handoffs/SESSION_121_m12_inc1_bhph_note.md`
  (this file)

### Modified
- `backend/dealer_ai/models.py` — added
  `BhphNote` model + payment-frequency
  vocab constants at end (matches
  M11.5 layout).
- `backend/dealer_ai/services/tenancy.py`
  — extended `_TENANT_CARRIER_MODEL_NAMES`
  39 → 40.
- `backend/dealer_ai/services/payment_engine.py`
  — added `bhph_note_periodic_payment`,
  `bhph_note_schedule`,
  `bhph_note_number_of_periods` pure
  verbs + `UnknownBhphFrequencyError` +
  `BhphNoteFrequency` literal (adds
  `semi_monthly` cadence to the M2
  cadence set). Customer-shopping
  `estimate_bhph_payment` untouched.
- `backend/dealer_ai/urls.py` — two new
  admin paths under `/admin/bhph-notes/`.
- `00-START-NEXT-SESSION.md` — flipped
  to SESSION_122 · M12.2 priority.

## What the endpoints do

### `POST /admin/bhph-notes/`

Body: `sale_id`, `principal_financed`
(Decimal), `apr` (Decimal), `term_weeks`
(int), `payment_frequency` (weekly /
biweekly / semi_monthly),
`first_payment_due` (date), optional
`default_grace_days` (default 5).

Behavior:
- Cross-tenant sale → 404 (fail-closed).
- Non-BHPH sale (finance_type != "bhph")
  → 400.
- Duplicate BhphNote for the same Sale
  → 409.
- Unknown `payment_frequency` → 400
  (serializer-level rejection).

Response: `{ "bhph_note": {...} }` with
`payment_amount` computed at write time
via pure amortization verb.

### `GET /admin/bhph-notes/<pk>/`

Response:
`{ "bhph_note": {...}, "payment_schedule": [{"due_date": ..., "amount": ...}, ...] }`.

Equal-amount installments (final-period
rounding drift settled by a future
payoff verb, not quoted to the buyer).
Schedule length matches
`bhph_note_number_of_periods(term_weeks,
payment_frequency)`.

## Non-goals honored

- ❌ No `BhphPayment` entity (M12.2).
- ❌ No delinquency detection (M12.3).
- ❌ No PTP tracking (M12.4).
- ❌ No collections (M12.5).
- ❌ No repossession (M12.6).
- ❌ No portfolio analytics or UI
  (M12.7).
- ❌ No M10.5 Contract modification.
- ❌ No new `contract_type` vocab
  member.

## Design notes worth remembering

### Two separate BHPH payment engines
`estimate_bhph_payment` (M2 customer-
shopping estimator: consumes sticker
price + taxes + fees + down/trade-in;
supports weekly / biweekly) stays
untouched. `bhph_note_periodic_payment`
(M12.1 dealer-as-lender note math:
consumes net principal + APR +
`term_weeks` + `payment_frequency`;
supports weekly / biweekly /
semi_monthly) is the new pure verb.
Distinct verbs because the two callers
have distinct inputs — the shopper
sees sticker price, the note has net
principal already settled by the M9
Sale row ledger.

### Semi-monthly cadence spacing
15 calendar days between payments.
Chosen over 15.2 (=365/24) for
operator practice (1st + 15th style
schedules).

### OneToOne with Sale, not Contract
Per §5.a Option A — the M9
`Sale.finance_type == "bhph"` is the
load-bearing signal that this is
dealer-carried paper. Preserves M10.5
Contract byte-for-byte. No new
`contract_type` vocab member. M10.5
Contract can still attach to a Sale
via its own OneToOne — the two
records coexist without dependency.

### Belt (model) + suspenders (service)
- `BhphNote.clean()` enforces
  `sale.dealership == dealership` and
  `sale.finance_type == "bhph"`.
- `services.bhph_notes.record_bhph_note`
  raises `CrossTenantBhphNoteError`
  (→ 404) and `NonBhphSaleError`
  (→ 400) before the DB write. The
  service is the primary enforcement
  layer; the model `clean()` is the
  safety net for callers that bypass
  the verb (per M11 pattern).

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_12_PLANNING.md`
   §1.1 + §5.a + §5.b + §7 M12.1
4. `docs/handoffs/SESSION_120_m11_close.md`
5. `backend/dealer_ai/services/payment_engine.py`
6. `backend/dealer_ai/models.py::BhphNote`
7. `backend/dealer_ai/services/bhph_notes/`
