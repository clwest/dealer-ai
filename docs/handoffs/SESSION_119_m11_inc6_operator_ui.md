---
title: "SESSION_119 handoff — Milestone 11 · Increment 6 (M11.6 — Operator UI)"
status: historical
type: handoff
date: 2026-08-02
session: 119
milestone: 11
milestone_status: in_progress
increment: 6
increment_status: shipped
commit: TBD
---

# SESSION_119 — Milestone 11 · Increment 6 (M11.6 — Operator UI)

## What shipped

First M11 frontend increment.
New `/dealer-ai-sales/` route
family with four pages consuming
the M11.1-M11.5 backend surface.
16 focused Vitest tests (target
~15) + 8 backend tests for the
three read-only list endpoints
added at M11.6 to make the UI
operator-useful.

**M11 backend substrate + first-
pass operator UI both landed by
M11.6.** The M11.7 closeout is
the last remaining M11
increment.

Three §5.f scoping decisions +
one substrate addendum recorded
in `MILESTONE_11_PLANNING.md`
§0.a (M11.6 amendment):

- **§5.f.1 Option B** — new
  `/dealer-ai-sales/` route
  family.
- **§5.f.2 MVP scope** — four
  pages ship (leads with channel
  filter, test-drive log,
  follow-up work-queue, be-back
  list). DealWriteup + F&I
  handoff UI deferred to a
  follow-on (workflow spans two
  personas, needs distinct UX
  pass).
- **§5.f.3 test target** — ~15
  Vitest tests.
- **§5.f.4 substrate addendum**
  — three read-only backend
  list endpoints added at M11.6
  to make the UI operator-
  useful (channel filter on
  existing `admin/leads/`, new
  `GET /admin/test-drives/list/`,
  new `GET /admin/be-backs/list/`).

Streak stays at 35 planning-time
as-recommended.

## Deliverables

### 1. Frontend — API client (`frontend/src/lib/salesApi.ts`)

- New module wrapping the M11.1-
  M11.5 admin surface.
- Exports typed request/response
  interfaces for every verb:
  `createWalkInLead` /
  `createPhoneLead` /
  `createReferralLead` /
  `createWebhookLead` /
  `createTestDrive` +
  `listTestDrives` /
  `createCadence` /
  `pauseCadence` /
  `listFollowUpTasks` /
  `completeTask` / `skipTask` /
  `createBeBack` +
  `listBeBacks` /
  `markBeBackReturned` /
  `markBeBackNoShow`.
- DealWriteup verbs typed but
  no UI at M11.6.
- All Decimals as string;
  timestamps as ISO 8601.

### 2. Frontend — four pages

- `DealerAiSalesLeads.tsx` —
  channel-filtered lead list.
  Reuses existing
  `fetchAdminLeads` from
  `api.ts` (extended with
  `channel?: string[]`
  parameter).
- `DealerAiSalesTestDrives.tsx`
  — test-drive log.
- `DealerAiSalesFollowUps.tsx`
  — work-queue with
  optimistic complete/skip
  transitions; defaults to
  "due today, pending".
- `DealerAiSalesBeBacks.tsx`
  — be-back list with
  optimistic mark-returned /
  mark-no-show transitions.
- All four match the M10.7
  shadcn Card + table pattern.

### 3. Frontend — route registration

- `main.tsx` extended with four
  new routes under
  `/dealer-ai-sales/*` inside
  the `RequireAuth + App`
  outlet.

### 4. Frontend — extended `api.ts`

- `AdminLeadsQuery` gains
  `channel?: string[]` field.
- `fetchAdminLeads` serializes
  the channel filter as a
  comma-joined query param.
- `AdminLead` interface adds
  optional `channel` +
  `referrer` fields (both were
  added to the M11.1
  serializer at M11.6).

### 5. Backend — read-only list endpoints (M11.6 addendum)

- **`admin_lead_list`
  (extended)** — accepts
  `?channel=<comma-joined>`
  filter; garbage tokens
  silently ignored (matches
  the M1 handed_off / urgency
  filter posture).
- **`admin_test_drive_list`
  (new)** — `GET
  /admin/test-drives/list/`;
  filters
  `?lead_id=` / `?vehicle_id=`
  / `?driven_since=`; 100-row
  cap.
- **`admin_be_back_list`
  (new)** — `GET
  /admin/be-backs/list/`;
  filters `?state=` /
  `?promised_since=`; 100-row
  cap.
- All three gated on
  `IsSalesManagerOrOwnerAtActiveDealership`
  (matches the M11.6 write
  posture).

### 6. Backend — serializer extension

- `AdminLeadListSerializer`
  now includes `channel` +
  `referrer` fields (M11.1
  shipped them on the model
  but not on the serializer).
  Purely additive; existing
  clients ignore unknown
  fields.

### 7. Tests — 24 focused tests total

- **Backend:** `test_m116_list_endpoints.py`
  (8 tests) — lead channel
  filter (2), test-drive list
  (3: projection shape,
  driven_since filter,
  lead_id filter), be-back
  list (3: default, state
  filter, garbage-state
  fallback).
- **Frontend:**
  - `DealerAiSalesLeads.test.tsx`
    (4 tests) — rows with
    channel column, filter
    refetch, empty state,
    error state.
  - `DealerAiSalesTestDrives.test.tsx`
    (3 tests) — rows, empty,
    error.
  - `DealerAiSalesFollowUps.test.tsx`
    (5 tests) — rows, action-
    button visibility on
    pending only, optimistic
    complete, state-filter
    refetch, empty state.
  - `DealerAiSalesBeBacks.test.tsx`
    (4 tests) — rows, mark-
    returned, mark-no-show,
    state-filter refetch.

## Compatibility

- Backend baseline: **3,887 →
  3,895** (+8, matches §5.f.4
  addendum).
- Frontend baseline: **51 →
  67** (+16, target ~15).
- Migrations `0001`–`0036`
  (unchanged; M11.6 added no
  schema).
- Tenancy carriers **39**
  (unchanged).
- Permission classes **8**
  (unchanged; reused M4
  `IsSalesManagerOrOwnerAtActiveDealership`
  on all three list
  endpoints).
- DRF admin surface: **80 →
  82** (+2 new list endpoints;
  channel filter added to
  existing `admin/leads/`
  in place).
- Frontend operator routes:
  **11 → 15** (+4 sales
  routes).
- **Celery-beat task families:
  6** (unchanged).
- `tsc --noEmit` clean; `vite
  build` clean; zero backend
  regressions.

## Governance / posture notes

- **Scope adjustment recorded
  in §0.a.** The plan framed
  M11.6 as "frontend-only",
  but M11.2 + M11.5 shipped
  write-only endpoints, so
  three minimal read-only
  list additions land in the
  same M11.6 commit. Explicit
  in §5.f.4 addendum. This
  is the smallest substrate
  change that makes the M11.6
  UI operator-useful — no
  service-layer changes, no
  new permission class.
- **Optimistic transitions
  with refetch fallback.**
  The follow-up + be-back
  transition endpoints update
  local state on success;
  on error the page refetches
  the list to re-sync. Matches
  M10.7 compliance-audit
  interaction posture.
- **DealWriteup UI
  deliberately deferred.**
  The M11.3 handoff flow
  spans two personas (sales
  manager approves, F&I
  manager receives the auto-
  created CA) and needs a
  distinct UX pass. Verbs +
  types are in `salesApi.ts`
  so a follow-on doesn't
  re-declare them.
- **Additive-only serializer
  changes.** The
  `AdminLeadListSerializer`
  extension adds two fields;
  existing consumers keep
  working. The M1 chat
  funnel's `CustomerLeadSerializer`
  is unchanged.
- **Reuse over invention** —
  no new permission classes,
  no new fetch primitives
  (uses `authFetch` +
  `authGetJSON` /
  `authPostJSON` per the
  M1.4E convention). shadcn
  Card / table pattern
  mirrored from M10.7.
- **Streak update** — no
  planning-time §5 decisions
  surfaced at M11.6
  implementation. §5.f items
  were implementation-time
  scoping per M11.3-M11.5
  precedent. Streak stands at
  **35 as-recommended M5.1 →
  M11.1**.

## Non-goals honored

- ❌ No DealWriteup UI at
  M11.6 (deferred to a
  follow-on).
- ❌ No delivery-adapter UI
  (SMS/email drafting +
  sending remain deferred).
- ❌ No M12 planning at M11.6
  (that lands at M11.7
  closeout).
- ❌ No modification of M1-M11.5
  business logic.
- ❌ No new permission class.
- ❌ No new backend write
  endpoints (only the three
  read-only list additions
  per §5.f.4 addendum).

## What's next

**SESSION_120 opens M11.7 —
Closeout** per §7 M11.7. This
is the last M11 increment.
Documentation-only per the
M10.8 precedent:

- `docs/roadmap/MILESTONE_11_RETROSPECTIVE.md`
  (nineteen-lessons-style
  reflection).
- `docs/CAPABILITY_MATRIX.md`
  §7l (new section for M11).
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  §Milestone 11 flip to
  "shipped".
- Planning frontmatter flip
  (state: shipped).
- `docs/DEALER_KIT_SESSION_START.md`
  refresh.
- `docs/roadmap/MILESTONE_12_PLANNING.md`
  planning skeleton per the
  standing user directive
  (M10.8 precedent).
- Coordinated commit landing
  every M11.1-M11.6 stage
  (already committed
  separately; M11.7 is docs
  + a single close-out
  commit).

**Backend baseline at
SESSION_120 open: 3,895 pass.**
Frontend baseline: **67 pass**.

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 11
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_11_PLANNING.md`
   (§0.a M11.1 + M11.3 + M11.4
   + M11.5 + M11.6 amendments)
6. `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_118_m11_inc5_be_back.md`
   (previous session)
8. `docs/handoffs/SESSION_117_m11_inc4_follow_up_cadence.md`
9. `docs/handoffs/SESSION_116_m11_inc3_deal_writeup.md`
10. `docs/handoffs/SESSION_115_m11_inc2_test_drive.md`
11. `docs/handoffs/SESSION_114_m11_inc1_channel_intake.md`
12. `docs/CAPABILITY_MATRIX.md` §7k
13. `docs/research/SALES_DEPARTMENT_MAPPING.md`
