---
title: "SESSION_167 handoff — Milestone 21 · Increment 1 (M21.1 — systematic operational-surface audit + M21 scope lock)"
status: historical
type: handoff
date: 2026-08-03
session: 167
milestone: 21
milestone_status: in-progress
milestone_name: "Operational Surface Completion"
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_167 — Milestone 21 · Increment 1 (M21.1 — systematic operational-surface audit + M21 scope lock)

## What shipped

Audit-execution session per
MILESTONE_21_PLANNING.md §7 M21.1.
Landed the audit tooling + the
audit artifact + user-confirmed
scope selection for M21.2 onward.

**Audit tooling** at
`backend/dealer_ai/scripts/audit_operational_surface.py`
per §5.b Option C combined
methodology. Single script; ~500
lines; not runtime code. Walks
`backend/dealer_ai/urls.py` for
function-based DRF views + all seven
`frontend/src/lib/*Api.ts` wrapper
modules for typed helper functions
+ every non-test `.tsx` / `.ts`
file under `frontend/src/` for
component-level wrapper
consumption. Wrappers that exist
in an `*Api.ts` module but are
never imported by a component get
a `wrapper-only` tag — the
endpoint is reachable in
principle but not through the
operator UI. That
component-consumption check
reclassified 6 endpoints from
apparent-coverage to backend-only,
which is exactly the failure mode
the M20 evidence predicted.

**Audit artifact** at
`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
per §5.c Option A schema. **153
backend endpoints enumerated.**
**96 covered** by frontend
components. **57 backend-only
findings** distributed as:

- **`M21-anchor` — 8 endpoints.**
  BHPH write path (7) + be-back
  CREATE (1).
- **`M21-conditional` — 2
  endpoints.** Follow-up
  cadence CONFIG (create +
  pause).
- **`defer-domain-milestone` —
  3 endpoints.** Accounting
  reversal + trial-balance
  snapshot create / list /
  retrieve. Belongs to
  Candidate A for M22.
- **`defer-candidate-O2` — 44
  endpoints.** Uncovered but
  out of M21 scope — F&I write
  UI (16), walk-in / phone /
  referral lead creation (4),
  deal-writeup mutations (3),
  test-drive creation (2),
  BHPH note origination (1),
  BHPH payment intake (1),
  accounting journal create +
  list + trial balance (4),
  misc dashboards. Each is a
  legitimate future OSC
  candidate; bolting any onto
  M21 would violate scope
  discipline.
- **`intentional-omission` — 5
  endpoints.** Auth flows +
  demo utilities. Not meant
  to be operator-facing.

**One known false-positive
class documented in the
artifact:** nested TypeScript
template literals
(`${qs ? \`?${qs}\` : ""}`)
confuse the URL normalizer.
~3 endpoints appear as
backend-only in the artifact
that are actually consumed by
components
(`admin/be-backs/list/` +
`admin/vehicles/<stock>/photos/<uuid>/`
+ one report list). Deferred
as a known limitation rather
than more regex complexity;
future audit-tooling
iterations may add TS-aware
parsing if the false-
positive rate matters.

## Reconciliations against M20 planning skeleton Input 1

Three concrete reconciliations
against the assumptions carried
into M21.0:

1. **Be-back write path is
   smaller than assumed.** The
   M20 skeleton said all three
   verbs (create + mark-returned
   + mark-no-show) were missing
   UI. Reality: both mark verbs
   ship in
   `DealerAiSalesBeBacks.tsx`.
   Only `POST /admin/be-backs/`
   (record be-back) is missing.
   **Anchor 2 narrows from
   three verbs to one.**
2. **Follow-up cadence queue
   is already partly UI-
   consumed.**
   `DealerAiSalesFollowUps.tsx`
   consumes list / complete /
   skip. Only the cadence
   CONFIG surface (create +
   pause a cadence template)
   is genuinely missing.
3. **BHPH write path confirmed
   at exactly seven verbs.**
   Promise create / mark-kept /
   mark-broken, contact
   create, repossession
   create / mark-recovered /
   mark-re-intaked. No extra
   state transitions or alias
   endpoints surfaced.

## Scope locked at SESSION_167 close

Per §5.d Option B — assistant
recommended, user confirmed.
Recorded as §0.a M21.1
amendment in
`MILESTONE_21_PLANNING.md`.

**M21.2 (SESSION_168) — BHPH
write-side UI (7 endpoints).**
Attach to the M12.7 collector
dashboard surface (Promises
card, Contacts card,
Repossessions card). Ship
seven forms / buttons plus
the missing `bhphApi.ts`
write wrappers (module has
zero write helpers today).
Extend
`bhph/collections_workflow.spec.ts`
end-to-end.

**M21.3 (SESSION_169) — Be-
back CREATE + Follow-up
cadence CONFIG (3
endpoints).** Combined into
one increment per size
discipline:
- `RecordBeBackForm` on
  `DealerAiSalesBeBacks.tsx`.
- `CreateCadenceForm` +
  `PauseCadenceButton` on
  `DealerAiSalesFollowUps.tsx`
  or adjacent cadence-config
  panel.
- Journey extension or
  addition per §5.e Option C
  decision at M21.3 open.

**M21.4 SKIPPED.** No
additional audit-surfaced
items warrant M21 scope. All
44 `defer-candidate-O2`
endpoints defer to Candidate
O2 for future OSC-shaped
milestones. Increment slot
returned; M21.5 becomes
SESSION_170.

**M21.5 (SESSION_170) —
close-out.** Retrospective,
capability matrix §7v, M22
skeleton, IMPLEMENTATION_ROADMAP
updated with DoD amendment,
coordinated push per M18.6 /
M19.6 / M20.5 cadence.

## Milestone shape revised

**Five increments total** —
M21.0 planning + M21.1 audit +
M21.2 BHPH + M21.3 be-back-
create + cadence-config +
M21.5 close-out. Down from
the six expected at §5.h
Option B; M21.4 collapsed per
audit evidence.

## Baselines unchanged

- **Backend:** 4,755 pass
  (audit scripts are operator-
  invoked, not tested — no
  baseline movement in this
  increment).
- **Frontend Vitest:** 153
  pass (unchanged).
- **Acceptance suite:** 6
  journeys (unchanged).
- **Migrations:** `0001`–`0048`
  (unchanged).
- **Tenancy carriers:** 52
  (unchanged).
- **Permission classes:** 7
  (unchanged — zero-drift
  streak at twenty
  consecutive milestones,
  targets twenty-one at M21
  close).
- **DRF admin surface:** 113
  (unchanged — M21.1 adds
  zero endpoints).
- **Frontend operator
  routes:** 20 (unchanged).

## Planning-time streak

**87 planning-time as-
recommended M5.1 → M21.0.**
Twelve consecutive milestones
(M10 → M21). M21.1 is an
execution session — no new §5
decisions land here; the scope-
lock recorded as §0.a M21.1
amendment continues the
established amendment
convention (see M20.5 §0.a for
precedent).

## What's next: SESSION_168 M21.2 BHPH write-side UI + journey extension

Per `MILESTONE_21_PLANNING.md`
§7 M21.2:

- **`bhphApi.ts` write
  wrappers.** The module
  currently has ZERO write
  helpers. Ship seven new
  exported functions:
  - `recordPromiseToPay`
  - `markPromiseKept`
  - `markPromiseBroken`
  - `logCollectionContact`
  - `initiateRepossession`
  - `markRepossessionRecovered`
  - `markRepossessionReIntaked`
- **Frontend components.**
  Attach to the M12.7
  collector dashboard surface:
  - `RecordPromiseToPayForm`
    on Promises card.
  - `MarkBrokenPromiseButton` +
    `MarkKeptPromiseButton`
    row actions on Promises
    card.
  - `LogCollectionContactForm`
    on Contacts card.
  - `InitiateRepossessionForm`
    on Repossessions card.
  - `MarkRecoveredButton` +
    `MarkReIntakedButton`
    row actions on
    Repossessions card.
- **Vitest coverage** for
  the new forms + buttons
  (submit + validation +
  error paths + click
  handlers + confirm dialogs
  where applicable).
- **Extended
  `seed_journey_bhph_collections_workflow`**
  covering the write-side
  setup (fresh PtP-ready
  note; existing PtP ready
  to mark broken; existing
  contact history; existing
  repossession-ready state).
  Backend tests for
  idempotency + tenant
  scoping.
- **Extended
  `acceptance/journeys/bhph/collections_workflow.spec.ts`**
  covering: record PtP →
  mark broken → log contact
  → initiate repossession,
  with business-outcome
  assertions at each step.
- **Opportunistic testids
  per §5.g** on the new
  forms / buttons that the
  extended journey needs to
  target reliably.

**Backend baseline target at
M21.2 close:** 4,755 → ~4,760-
4,770. Frontend Vitest: 153 →
~163-170. Acceptance suite: 6
journeys (BHPH re-expanded).

## What lands at M21.3 (SESSION_169)

Be-back CREATE + Follow-up
cadence CONFIG. See §7 M21.3
in the planning memo.

## What lands at M21.5 (SESSION_170) — close-out

Retrospective, capability
matrix update, M22 skeleton,
coordinated close-out commit +
push. See §7 M21.5.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (active — §0.a M21.1
   amendment landed here)
6. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (this session's primary
   deliverable — scope
   decisions for M21.2+
   trace to it)
7. `docs/handoffs/SESSION_166_m21_inc0_planning.md`
   (M21.0 shipped —
   governing contract +
   eight §5 decisions)
8. `docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`
   §8 + §9 (M20 substrate
   M21 consumes)
9. `docs/CAPABILITY_MATRIX.md`
   §7u (M20 shipped surface)
