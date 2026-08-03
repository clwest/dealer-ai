---
title: "SESSION_178 handoff — Milestone 23 · Increment 3 (M23.3 — payment intake UI + journey)"
status: historical
type: handoff
date: 2026-08-03
session: 178
milestone: 23
milestone_status: in-progress
milestone_name: "BHPH Origination + Payment Intake"
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_178 — Milestone 23 · Increment 3 (M23.3 — payment intake UI + journey)

## What shipped

Second anchor UI increment per §5.a
scope. Completes the M23 anchor
pair — both BHPH lifecycle bookends
(origination + payment intake) now
ship with Playwright validation
end-to-end. Ready for M23.4 close-
out.

**Verification:** isolated M23.3
journey: **7 passed @ 13.1s** (6
setup + 1 M23.3). Full clean-DB
dry-run: **15 passed (9 journeys)
@ 20.3s**. All existing journeys
still pass.

**Backend baseline delta: 4,773 →
4,780 (+7)** — seven new M23.3
seed idempotency + payment-
cleanup tests. Frontend Vitest:
**187 → 193 (+6)**
RecordBhphPaymentForm tests.
Acceptance suite: **8 → 9
journeys**.

**Zero-drift permission-class
streak:** still 22 consecutive
milestones (M10 → M22). M23.3
introduces zero permission-class
changes. Streak target at M23.4
close: 23.

**Planning-time as-recommended
streak:** still 89 across
fourteen consecutive milestones.
M23.3 is implementation work; no
new §5 decisions surfaced.

## Six shipping surfaces

1. **`bhphApi.ts` extended** with
   `createBhphPayment(notePk, payload)`
   + `CreateBhphPaymentPayload` +
   `BhphPaymentCreateResponse`
   types + new `BhphPaymentMethod`
   union type. Posts to
   `POST /admin/bhph-notes/<pk>/payments/`.
   Payload shape matches
   `BhphPaymentCreateRequestSerializer`
   verbatim.
2. **`RecordBhphPaymentForm.tsx`**
   ships at
   `frontend/src/components/bhph/`
   with 3 required fields
   (paid_at, amount, method) +
   inline validation +
   `humanizeError` covering
   400 / 404 responses. 6
   Vitest tests covering submit,
   zero-amount block, missing-
   amount block, 400 error, 404
   note-not-found error, field
   reset after successful submit.
   Follows M23.2 §5.d lesson —
   no HTML5 `required`/`min`
   attrs that short-circuit
   onSubmit.
3. **`DealerAiBhphNoteDetail.tsx`
   Payments card extended** —
   now includes the inline
   `RecordBhphPaymentForm`
   matching the M21.2 sibling
   pattern
   (`RecordPromiseToPayForm`
   inline in Promises card).
   Added
   `data-testid="payments-card"`,
   `data-testid="payments-list"`,
   `data-testid="payment-row-<id>"`
   markers per §5.g opportunistic-
   testid posture. Optimistic
   list refresh via `mergeById`
   on submit success.
4. **Seed extension** —
   `seed_journey_bhph_collections_workflow.py`
   provisions a distinct BhphNote
   (stock `M23-BHPH-PAY`,
   principal $5,400, APR 19.5%,
   52w weekly term) with non-
   zero balance and NO payments
   yet.
   `_drop_payments_targeting()`
   cleans up any BhphPayment
   linked to the M23.3 fixture
   note on re-invocation —
   matches M22.2 reversal +
   M23.2 note cleanup patterns.
   SUCCESS message prints
   `m23_pay_note_pk=<N>` for
   the journey to parse.
   `_reset()` extended to also
   sweep the M23.3 fixture
   chain.
5. **BHPH assertion helper
   extended** at
   `acceptance/support/assertions/bhph.ts`
   with
   `expectBhphPaymentRecorded(request, notePk, expected)`.
   Verifies at least one
   payment with matching amount
   + method exists on the note.
6. **New Playwright journey**
   at
   `acceptance/journeys/bhph/payment_intake.spec.ts`.
   Walks: parse M23.3 note pk
   from seed stdout →
   `bhph_collector` persona
   lands on note detail →
   verify Payments card + form
   render → fill amount (150) +
   method (cash) → click "Record
   payment" → verify amount
   input clears (success signal)
   → business-outcome assertion
   via API using the new helper.

## First-run pass — no §5.d fixes required

M23.3 journey authoring
proceeded cleanly against the
shipped M23.3 markup with zero
§5.d in-scope fixes. Key
reasons:

1. **M23.2's `_provision_collector`
   session-preservation fix** was
   inherited — my journey's
   `invokeSeed()` call at test
   start no longer invalidates
   the persona's cookie. Bug
   would have surfaced again
   here without that fix; it
   didn't.
2. **M23.2's URL-slug lesson**
   was applied at authoring
   time — I checked the actual
   route in main.tsx / M20.4
   collections_workflow before
   authoring rather than
   relying on the memo. The
   `/dealer-ai-bhph/notes/<pk>`
   route was correct on first
   try.
3. **Sibling-pattern discipline**
   — following the M21.2
   RecordPromiseToPayForm-in-
   Promises-card structure
   verbatim meant no novel UI
   design decisions had to be
   verified. Payments card
   already existed; I just
   added the inline form the
   same way Promises card has
   its form.
4. **Test-id conventions
   established at M23.2** —
   `record-<workflow>-<field>`
   pattern already validated;
   no ambiguity.

## Cross-milestone pattern observation

Milestone / journey / §5.d
fixes:

| Milestone | Journey | §5.d fixes |
|---|---|---|
| M22.2 (JE reversal) | accounting_je_reversal | 0 |
| M23.2 (note origination) | note_origination | 1 (seed session bug) |
| M23.3 (payment intake) | payment_intake | 0 |

The pattern: **new UI on a
new page** (M22.2 — new
dialog on shipped page) tends
to reveal 0 gaps because the
shipped page framework has
been proven; **new UI on a
new page with a new persona-
integration pattern** (M23.2
— first journey to re-invoke
seed mid-suite) tends to
reveal 1 latent bug; **new
UI following an established
sibling pattern** (M23.3 —
Payments card matches
Promises card structure)
tends to reveal 0 gaps.
Reinforces the value of
sibling-pattern discipline
and of small in-scope fixes
per §5.d Option B — the
first-of-a-kind change
surfaces the bug once; then
future work inherits the
fix.

## Streak

**Planning-time as-recommended:
still 89 across fourteen
consecutive milestones (M10 →
M23).** M23.3 is implementation
work; no new §5 decisions.

**Zero-drift permission-class:
still 22 consecutive milestones
(M10 → M22).** M23.3 introduces
zero permission-class changes.
Streak target at M23.4 close:
23.

## What's next: SESSION_179 M23.4 close-out

Per `MILESTONE_23_PLANNING.md`
§7 M23.4:

- **Clean-DB acceptance dry-
  run verification** — verify
  15 passed (~20s) on fresh
  DB matches this session's
  baseline.
- **`docs/CAPABILITY_MATRIX.md`
  §7x — M23 shipped surface:**
  new BHPH origination +
  payment intake UIs + audit
  tooling correction + seed
  fixture extensions + assertion
  helpers + 2 new Playwright
  journeys.
- **`docs/roadmap/MILESTONE_23_RETROSPECTIVE.md`**
  covering §1 planned scope +
  §2 what shipped + §3
  deviations + §4 deferrals
  reviewed + §5 lessons
  learned + §6 streak status
  + §7 governing-contract
  validation + §8 corrections
  landed + §9 standing M24
  question with evidence-
  based candidate discussion
  (JE creation UI + sale
  picker UX + session-
  invalidation seed pattern
  generalization + route URL
  discovery friction).
- **`docs/roadmap/MILESTONE_24_PLANNING.md`**
  skeleton (status: draft)
  with candidate list
  refreshed from M23 §9
  findings + remaining M20 /
  M21 / M22 candidates.
- **`docs/roadmap/IMPLEMENTATION_ROADMAP.md`**
  updated with M23 shipped
  status.
- **Session handoff** at
  `docs/handoffs/SESSION_179_m23_inc4_close.md`.
- **`00-START-NEXT-SESSION.md`**
  refreshed for M24.0
  planning session.
- **Coordinated close-out
  commit + push** per M18.6
  / M19.6 / M20.5 / M21.5 /
  M22.4 cadence. All four
  M23 commits (M23.0 planning
  + M23.1 audit fix + M23.2
  origination + M23.3 payment
  intake + M23.4 close) push
  to origin/main together.
- **Monitor first M23 CI
  run** after push.

## Non-goals for SESSION_179

- ❌ Do NOT ship any backend
  or frontend code — close-
  out is documentation +
  coordinated push only.
- ❌ Do NOT open M24
  implementation increment —
  M24.0 is a separate
  planning session.
- ❌ Do NOT force-push or
  amend earlier M23 commits.
- ❌ Do NOT modify M1-M22
  shipped surface.
- ❌ Do NOT modify the
  acceptance suite unless CI
  regression fixes land as
  §0.a M23.4 amendments.
- ❌ Do NOT extend M23 scope
  by pulling in future-work
  candidates surfaced during
  M23 — all recorded in
  retrospective §9.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M22 shipped section
   landed at M22.4)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (active memo — §0.a
   M23.3 amendment records
   shipped payment intake
   UI + first-run pass)
6. `docs/handoffs/SESSION_177_m23_inc2_note_origination.md`
   (M23.2 close — origination
   pattern reference for
   M23.3)
7. `docs/handoffs/SESSION_176_m23_inc1_audit_fix.md`
   (M23.1 close)
8. `docs/handoffs/SESSION_175_m23_inc0_planning.md`
   (M23.0 close)
9. `frontend/src/pages/DealerAiBhphNoteDetail.tsx`
   (M23.3 attach target —
   Payments card now
   includes inline form)
10. `docs/CAPABILITY_MATRIX.md` §7w
    (M22 shipped surface)
