---
title: "SESSION_127 handoff — Milestone 12 · Increment 7 (M12.7 — Portfolio analytics + operator UI MVP)"
status: historical
type: handoff
date: 2026-08-02
session: 127
milestone: 12
milestone_status: in_progress
increment: 7
increment_status: shipped
commit: TBD
---

# SESSION_127 — Milestone 12 · Increment 7 (M12.7 — Portfolio analytics + operator UI MVP)

## What shipped

First cross-stack M12 increment.
Five pure aggregate verbs, one
summary endpoint, one addendum
list endpoint, and a new
`/dealer-ai-bhph/` frontend route
family (portfolio dashboard +
per-note detail). Per
`MILESTONE_12_PLANNING.md` §1.7 +
§1.9 + §5.f Option C (MVP scope
locked at SESSION_121 open).

**Five §0.a M12.7 open decisions
recorded as-recommended:**

1. **Analytics metric set** —
   five verbs as spec'd.
2. **Endpoint shape** — single
   summary endpoint at MVP.
3. **Route split** — portfolio
   dashboard + per-note detail.
4. **Detail composition** —
   compose existing endpoints
   (no bundle endpoint).
5. **Framework consistency** —
   React Router + Tailwind +
   shadcn/ui matching M11.6
   posture.

Streak stands at **41 planning-time
as-recommended M5.1 → M12.1** (§0.a
implementation-time decisions don't
count against streak per M10 §9).

## By the numbers

- **Backend baseline: 4,150 pass,
  1 skipped, 0 fail** (was 4,126
  at M12.6 close — **+24 tests,
  0 regressions**).
- **Frontend Vitest baseline: 78
  pass** (was 67 at M11.6 close
  — **+11 tests, 0 regressions**).
- **Migrations: 0042** (unchanged
  — M12.7 is aggregation + UI,
  no new entity).
- **Tenancy carriers: 44**
  (unchanged).
- **DRF admin surface: 96 → 98**
  (M12.7 summary endpoint +
  M12.7-addendum list endpoint
  for BhphNote).
- **Frontend operator routes:
  15 → 17** (`/dealer-ai-bhph/
  portfolio` + `/dealer-ai-bhph/
  notes/:pk`).
- **Permission classes: 8**
  (unchanged).
- **Celery-beat task families:
  8** (unchanged).
- **AI safety stack: 17 scrub
  stages** (unchanged).

## Files touched

### New backend
- `backend/dealer_ai/services/bhph_analytics/__init__.py`
- `backend/dealer_ai/services/bhph_analytics/compute.py`
  (five pure verbs +
  `portfolio_summary` bundler)
- `backend/dealer_ai/views_bhph_analytics.py`
  (summary endpoint)
- `backend/dealer_ai/tests/test_m127_bhph_analytics_service.py`
  (19 tests)
- `backend/dealer_ai/tests/test_m127_bhph_analytics_endpoint.py`
  (5 tests)

### Modified backend
- `backend/dealer_ai/views_bhph_notes.py`
  — added
  `admin_bhph_note_list`
  (M12.7 addendum for browsing
  the portfolio).
- `backend/dealer_ai/urls.py` — two
  new admin paths.

### New frontend
- `frontend/src/lib/bhphApi.ts`
  — API client for M12.1-M12.7
  reads.
- `frontend/src/pages/DealerAiBhphPortfolio.tsx`
  (dashboard).
- `frontend/src/pages/DealerAiBhphPortfolio.test.tsx`
  (7 tests).
- `frontend/src/pages/DealerAiBhphNoteDetail.tsx`
  (detail).
- `frontend/src/pages/DealerAiBhphNoteDetail.test.tsx`
  (4 tests).

### Modified frontend
- `frontend/src/main.tsx` —
  registered the new route
  family.

### Docs
- `docs/handoffs/SESSION_127_m12_inc7_analytics_ui.md`
  (this file).
- `00-START-NEXT-SESSION.md` —
  flipped to SESSION_128 · M12.8
  (M12 close-out).

## The five analytics verbs

All tenant-scoped, all read-only,
all pure aggregation.

### `bucket_histogram(dealership)`
Returns a fixed-order 7-row tuple
of `BucketHistogramRow(bucket,
note_count, principal_total)`.
Buckets with zero notes come
back as zeros — the frontend
renders the full histogram
without conditional slot filling.

### `cure_rate(dealership)`
Snapshot MVP interpretation:
`current_bucket_count /
total_notes`. True time-windowed
cure rate defers until M12+
time-series storage lands (§0.a
M12.7 decision 1 as-recommended).
Returns `None` for empty
portfolios.

### `weighted_average_apr(dealership)`
`sum(principal * apr) /
sum(principal)`. Returns `None`
for zero-principal portfolios.

### `weighted_average_days_past_due(dealership)`
`sum(principal * days_past_due) /
sum(principal)`. Returns `None`
for zero-principal portfolios.

### `ptp_kept_ratio(dealership)`
`kept / (kept + broken)`. Open
`promised` promises excluded from
the denominator. Returns `None`
when no promises have resolved.

## The summary endpoint

`GET /admin/bhph/analytics/summary/`
returns the bundle:

```
{
  "bucket_histogram": [...7 rows...],
  "total_note_count": N,
  "total_principal_financed": "...",
  "cure_rate": "..." | null,
  "weighted_average_apr": "..." | null,
  "weighted_average_days_past_due": "..." | null,
  "ptp_kept_ratio": "..." | null
}
```

Per §0.a M12.7 decision 2 — one
endpoint, one payload. Per-metric
endpoints defer until operator
evidence surfaces need.

## The frontend routes

### `/dealer-ai-bhph/portfolio/`
Consumes summary + note list.
Renders:

- Four metric cards (notes,
  cure rate, weighted APR,
  weighted DPD).
- Aging histogram (all 7
  buckets, counts + principal
  totals).
- Notes table (up to 100 rows,
  with a link to per-note
  detail).

### `/dealer-ai-bhph/notes/:pk/`
Composes M12.1–M12.6 read
endpoints. Renders:

- Loan terms card.
- Payments list (M12.2).
- Promises list (M12.4).
- Contacts list (M12.5).
- Repossessions list (M12.6).

Empty-state message per section
when no rows.

## Non-goals honored

- ❌ No collection contact UI
  (defer per §5.f Option C).
- ❌ No repossession UI (defer
  per §5.f Option C).
- ❌ No per-metric detail
  endpoints — summary bundle
  only at MVP.
- ❌ No new detector task.
- ❌ No time-series storage —
  metrics computed live per
  request; historical trending
  defers.
- ❌ No CSV export — JSON
  payload only at MVP.

## Design notes worth remembering

### Frozen dataclass for bundle
`BhphAnalyticsSummary` and
`BucketHistogramRow` are frozen
dataclasses matching M8 analytics
pattern. Callers project into
serialized shape; no mutation of
aggregation output.

### Zero-portfolio semantics
Every weighted-average verb
returns `None` (not zero) when the
portfolio has zero notes — the
distinction between "0% APR" and
"no notes to compute an APR for"
is real. The endpoint ships
`None` verbatim; the frontend
renders em-dash.

### Portfolio metric formatting
`cure_rate` and `ptp_kept_ratio`
quantized to 4 decimal places
(`0.7500` for 75%). APR quantized
to 2 decimal places matching the
`BhphNote.apr` field width.
Money quantized to cents. All
transported as strings; frontend
`Number(...)` for display formatting
only.

### `admin_bhph_note_list` addendum
Added at M12.7 as a companion to
the existing retrieve endpoint —
the portfolio dashboard needs a
browsable list. Thin QuerySet
wrapper capped at 100 rows
(matches M11.6 admin list
convention). Rejected the
alternative of client-side
enumeration via retrieve calls.

### Two-page split, deferred UI
per §5.f Option C
Portfolio dashboard + per-note
detail cover the MVP scope.
Collection-contact create UI and
repo-order UI defer to a follow-
on if operator evidence surfaces
need. The paired backend
endpoints already exist (M12.5 +
M12.6) so the follow-on can add
just the React code.

### Compose, don't bundle
Detail page fetches five separate
endpoints (`GET .../<pk>/`,
`.../payments/list/`,
`.../promises/list/`,
`.../contacts/list/`,
`.../repossessions/list/`) via
`Promise.all` rather than adding
a bundle endpoint. Each backend
endpoint stays focused; frontend
composition costs a single
render-blocking round trip.

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_12_PLANNING.md`
   §1.7 + §1.9 + §5.f + §7 M12.7
4. `docs/handoffs/SESSION_126_m12_inc6_repossession.md`
   (previous session)
5. `backend/dealer_ai/services/bhph_analytics/compute.py`
6. `frontend/src/pages/DealerAiBhphPortfolio.tsx`
7. `frontend/src/pages/DealerAiBhphNoteDetail.tsx`
8. `frontend/src/lib/bhphApi.ts`
