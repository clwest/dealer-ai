---
title: "SESSION_177 handoff — Milestone 23 · Increment 2 (M23.2 — note origination UI + journey)"
status: historical
type: handoff
date: 2026-08-03
session: 177
milestone: 23
milestone_status: in-progress
milestone_name: "BHPH Origination + Payment Intake"
increment: 2
increment_status: shipped
commit: TBD
---

# SESSION_177 — Milestone 23 · Increment 2 (M23.2 — note origination UI + journey)

## What shipped

First anchor UI increment per §5.a
scope. Validates the BHPH note-
origination workflow end-to-end via
new frontend components, seed
extension, assertion helper, and
Playwright journey. Second anchor UI
(payment intake) ships at M23.3.

**Verification:** isolated M23.2
journey (`office_accounting` project
+ M23.2): **7 passed @ 13.1s** (6
setup + 1 M23.2). Full clean-DB
dry-run: **14 passed (8 journeys)
@ 18.8s**. All existing journeys
still pass.

**Backend baseline delta: 4,766 →
4,773 (+7)** — seven new M23.2
seed idempotency + note-cleanup
tests. Frontend Vitest: **180 →
187 (+7)** RecordBhphNoteForm
tests. Acceptance suite: **7 → 8
journeys**.

**Zero-drift permission-class
streak:** still 22 consecutive
milestones (M10 → M22). M23.2
introduces zero permission-class
changes. Streak target at M23.4
close: 23.

**Planning-time as-recommended
streak:** still 89 across fourteen
consecutive milestones. M23.2 is
implementation work; no new §5
decisions surfaced.

## Six shipping surfaces

1. **`bhphApi.ts` extended** with
   `createBhphNote(payload)` +
   `CreateBhphNotePayload` +
   `BhphNoteCreateResponse` types.
   Posts to
   `POST /admin/bhph-notes/`.
   Payload shape matches
   `BhphNoteCreateRequestSerializer`
   verbatim: sale_id, principal_
   financed, apr, term_weeks,
   payment_frequency,
   first_payment_due, optional
   default_grace_days.
2. **`RecordBhphNoteForm.tsx`**
   ships at
   `frontend/src/components/bhph/`
   with all six required fields +
   optional default_grace_days
   handling + inline validation +
   `humanizeError` covering 400 /
   404 / 409 responses (409 =
   "sale already has a note",
   404 = "sale not found"). 7
   Vitest tests covering submit,
   initialSaleId prop, missing
   sale_id block, zero principal
   block, 409 duplicate error,
   404 not-found error, field
   reset after successful submit.
3. **`DealerAiBhphPortfolio.tsx`
   extended** with persistent
   "Add note" CTA in the Notes
   card header + shadcn Dialog
   containing `RecordBhphNoteForm`.
   Empty-state message updated to
   reference the new CTA (previous
   text documented the POST curl
   workaround). `reloadTick`
   pattern refreshes the notes
   list on successful submit.
   All 7 existing portfolio tests
   still pass unchanged.
4. **Seed extension** —
   `seed_journey_bhph_collections_workflow.py`
   provisions a distinct BHPH-
   marked Sale (stock
   `M23-BHPH-ORIG`, sold-price
   $8,250, no attached note) that
   the origination journey targets.
   `_drop_notes_targeting()`
   cleans up any BhphNote linked
   to the M23.2 fixture sale on
   re-invocation — matches
   M22.2's reversal-cleanup
   pattern. SUCCESS message
   prints `m23_orig_sale_pk=<N>`
   for the journey to parse.
   `_reset()` extended to also
   sweep the M23.2 fixture chain.
5. **BHPH assertion helper
   extended** at
   `acceptance/support/assertions/bhph.ts`
   with `expectBhphNoteOriginated(request, saleId, expected)`.
   Verifies exactly one note
   targets the sale + terms match
   what the operator entered
   (principal, APR, term_weeks,
   payment_frequency). Fails
   loudly if either invariant
   drifts.
6. **New Playwright journey** at
   `acceptance/journeys/bhph/note_origination.spec.ts`.
   Walks: parse M23.2 sale pk
   from seed stdout →
   `bhph_collector` persona lands
   on `/dealer-ai-bhph/portfolio`
   → click "Add note" → dialog
   opens → fill form (sale_id
   from parsed pk, principal
   $7,500, APR 18.5%, term 78
   weeks, biweekly cadence) →
   click "Originate note" →
   verify dialog closes →
   business-outcome assertion via
   API using the new helper.

## §5.d gap fix landed in-scope

**Session-invalidation bug in
`_provision_collector` fixed.**
Journey authoring surfaced a
pre-existing latent bug in the
BHPH seed's collector
provisioning:
`_provision_collector` called
`set_password(COLLECTOR_PASSWORD)`
on every seed invocation. Django's
session hash incorporates the
password hash, so re-setting the
password invalidated any active
session — INCLUDING the freshly-
established persona login the
setup step had just created.

The bug never manifested before
M23.2 because no prior journey
re-invoked a seed mid-suite. The
M23.2 journey needs to re-invoke
the seed (idempotently) to parse
the fixture sale pk from stdout —
that's the first usage pattern to
trigger the bug.

Fix: wrap `set_password` +
`is_active` + `save` in an
`if created:` guard so the
password only gets set on new
users. One-file trivial change
per §5.d Option B in-scope
threshold. Recorded in memo §0.a
M23.2 amendment + this handoff.

The fix generalizes: any future
journey that needs to re-invoke
its seed for fixture lookup will
inherit the corrected pattern.
Any other seed doing the same
unconditional `set_password`
pattern is a candidate for the
same fix — surfaces as future
work if operational evidence
demands it.

## Route URL correction

The M23 planning memo pre-
committed the portfolio route as
`/dealer-ai-bhph-portfolio`
based on speculative memory.
Empirical authoring revealed
the actual route in `main.tsx`
is `/dealer-ai-bhph/portfolio`
(under-slash-nested), matching
the M20.4 collections journey's
usage precedent. Corrected in
the journey source during
authoring; no memo amendment
needed beyond the §0.a M23.2
close entry that records the
correction.

**Lesson to carry forward:**
even with the "verify prior
recommendations at planning
open" memory in effect, small
factual details (URL slugs,
component paths) still deserve
verification when authoring
against them. The M23.0
verification correctly caught
the sale_id-vs-vehicle_id
serializer shape; missed the
URL slug detail. Not a
process failure — a reminder
that the granularity of
verification should match the
granularity of the assertion
being made.

## Frontend UX limitation surfaced

The `sale_id` form field is a
manual numeric input because no
admin sale-list endpoint ships
today. Real operator UX
improvement (sale picker,
deep-link from
`VehicleSalePage.tsx`) is
recorded per M23 §3 deferral 1
+ future retrospective §9 as
evidence-based candidate for
M24+ consideration. The form's
helper text acknowledges the
constraint: "The BHPH-marked
sale to originate this note
against."

**Deferred per §5.d Option B
large-gap posture** — building
a sale-list endpoint would
require a new backend service
verb + new DRF endpoint,
violating the M23 governing
contract's "closes a missing
operator-facing UI ON EXISTING
BACKEND" constraint.

## Deferrals catalogued for M23.4 retrospective §9

Findings surfaced during M23.2
authoring that feed the M24
candidate discussion at M23.4
close:

- **Sale picker UI / deep-link
  from VehicleSalePage** —
  §3 deferral 1. Would remove
  the manual sale_id input.
  Requires either a new admin
  sale-list endpoint (new
  service verb + endpoint =
  M23 non-goal) OR deep-link
  parameter handling on the
  portfolio route
  (`?new_note_for_sale=<id>`).
- **Session-invalidation bug
  in other seeds** — the
  `set_password`-on-every-
  invocation pattern may exist
  in other `seed_journey_*`
  commands. Not surveyed at
  M23.2 (only fixed the
  specific instance blocking
  the M23.2 journey). Future
  journey that re-invokes
  those seeds would surface
  the same bug. Small future
  fix per §5.d shape.
- **Route URL discovery
  friction** — no
  discoverable map of "what
  routes exist" for journey
  authors. Currently requires
  grepping `main.tsx`. Not
  urgent but a candidate for
  eventual planning-artifact
  automation per the "generated
  planning artifacts" memory
  established at M22 close.

## Streak

**Planning-time as-recommended:
still 89 across fourteen
consecutive milestones (M10 →
M23).** M23.2 is implementation
work; no new §5 decisions.

**Zero-drift permission-class:
still 22 consecutive milestones
(M10 → M22).** M23.2 introduces
zero permission-class changes.
Streak target at M23.4 close:
23.

## What's next: SESSION_178 M23.3 payment intake UI + journey

Per `MILESTONE_23_PLANNING.md`
§7 M23.3:

- **`createBhphPayment` wrapper**
  in `bhphApi.ts` posting to
  `POST /admin/bhph-notes/<pk>/payments/`.
  Verify the payload shape
  against the backend serializer
  in
  `backend/dealer_ai/views_bhph_payments.py`
  at M23.3 open.
- **`RecordBhphPaymentForm`
  component** in
  `frontend/src/components/bhph/`
  with amount input, method
  picker (cash / check / money
  order / ACH / card per M12
  vocab), paid_at datetime,
  optional memo, submit + error
  handling. Add Vitest coverage.
- **Attached to
  `DealerAiBhphNoteDetail.tsx`**
  as a new Payments card
  matching the existing
  Promises / Contacts /
  Repossessions sibling
  pattern. Optimistic list
  refresh on submit.
- **Extended seed** with a
  fresh-note-with-balance
  fixture — a distinct BhphNote
  with non-zero outstanding
  balance (no payments yet)
  that the payment-intake
  journey targets. Payment
  cleanup on re-invocation.
  Backend idempotency test.
- **Extended assertion helper**
  with
  `expectBhphPaymentRecorded(request, noteId, amount)`
  — asserts payment exists,
  outstanding balance
  decreased by the payment
  amount.
- **New journey** at
  `acceptance/journeys/bhph/payment_intake.spec.ts`
  walking navigate → click
  "Record payment" → fill
  form → submit → verify
  Payments card updates →
  business-outcome assertion
  via API.
- **§5.d small-fixes** if any
  surface (in-scope for one-
  file trivial changes).
- **Session handoff** at
  `docs/handoffs/SESSION_178_m23_inc3_payment_intake.md`.
- **`00-START-NEXT-SESSION.md`**
  refreshed for M23.4.

**Backend baseline target at
M23.3 close:** 4,773 → **~4,777**
(seed fixture + payment cleanup
tests). Frontend Vitest: 187 →
**~194-198**. Acceptance suite:
**8 → 9**.

## What lands at M23.4 (SESSION_179) — close-out

CI validation on all new /
extended journeys + capability
matrix §7x + retrospective
(with §9 evidence for M24
candidate discussion including
the JE creation UI finding
from M23.1 + the sale-picker
UX deferral from M23.2 + the
session-invalidation seed
pattern generalization + any
M23.3 findings) + M24 planning
skeleton + coordinated close-
out push per M18.6 / M19.6 /
M20.5 / M21.5 / M22.4 cadence.

## Non-goals for the remaining M23 increments

Per MILESTONE_23_PLANNING.md §3:

- ❌ Do NOT ship sale-time
  origination trigger (§3
  deferral 1). Portfolio-
  based CTA ships M23.2; sale-
  time trigger revisited on
  operator-use evidence.
- ❌ Do NOT ship the sale
  picker UI / deep-link (M23.2
  §3 deferral 1). Requires
  new backend endpoint =
  violates M23 governing
  contract.
- ❌ Do NOT add new backend
  service verbs, DRF endpoints,
  tenancy carriers, migrations,
  permission classes, or
  frontend routes.
- ❌ Do NOT rewrite the audit
  script — targeted regex fix
  already landed at M23.1.
- ❌ Do NOT manually verify
  workflows before authoring
  journeys — journey-as-
  verifier per §5.f Option B.
- ❌ Do NOT ship JE creation
  UI in M23 — surfaced at
  M23.1 as M24 evidence.
- ❌ Do NOT split the BHPH
  seed into per-workflow
  seeds — extend additively
  per §5.e Option A.
- ❌ Do NOT push M23 commits
  individually — coordinated
  close-out push at M23.4.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M22 shipped section landed
   at M22.4)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (active memo — §0.a M23.2
   amendment records shipped
   UI + seed session fix +
   route URL correction)
6. `docs/handoffs/SESSION_176_m23_inc1_audit_fix.md`
   (M23.1 close — audit
   correction + JE-creation-UI
   evidence for M24)
7. `docs/handoffs/SESSION_175_m23_inc0_planning.md`
   (M23.0 close)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact — now
   authoritative for BHPH
   post-M23.1 fix)
9. `frontend/src/components/bhph/RecordBhphNoteForm.tsx`
   (M23.2 shipped form —
   pattern reference for
   M23.3 `RecordBhphPaymentForm`)
10. `acceptance/journeys/bhph/note_origination.spec.ts`
    (M23.2 shipped journey —
    pattern reference for
    M23.3 `payment_intake.spec.ts`
    including the invokeSeed-
    + stdout-parsing pattern)
11. `docs/CAPABILITY_MATRIX.md` §7w
    (M22 shipped surface)
