---
title: "SESSION_105 handoff — Milestone 9 · Increment 6 (M9.6 — closeout)"
status: historical
type: handoff
date: 2026-08-02
session: 105
milestone: 9
milestone_status: shipped
increment: 6
increment_status: shipped
commit: TBD
---

# SESSION_105 — Milestone 9 · Increment 6 (M9.6 — closeout)

## What shipped

Documentation-only closeout + coordinated
commit covering every M9.1–M9.6 stage. **Push
to `origin/main` is deferred pending explicit
user authorization** — this handoff records
local commit only; the push decision is
captured at the end of this file.

**M9.6 deliverables (six docs + one commit):**

1. **`docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`**
   — new. §1 planned scope, §2 what actually
   shipped (per-increment table with commit
   references), §3 five §0.a amendments
   catalog, §4 accepted improvements + full
   deferral list with re-entry paths, §5
   compatibility summary (M2/M4/M5/M8
   substrates preserved; tenancy carriers
   22→24; DRF surface 40→47; frontend routes
   8→9; test baselines 3,274→3,426 backend +
   19→34 frontend), §6 sixteen lessons —
   fifteen carry-forward from M8 + one new:
   **"substrate-gap pushback is a productive
   session-open pattern"** (M9's new lesson,
   drawn from SESSION_103 + SESSION_104
   substrate-gap discoveries).
2. **`docs/CAPABILITY_MATRIX.md` §7j** — new
   subsection for M9. Mirrors §7i shape:
   summary paragraph + 8-row capability table
   (Sale entity / Delivery entity / Q3 true /
   Q6 / Q7 / Q8 true / Operator UI extension /
   Test baseline) + explicit "what is NOT
   shipped" deferral list.
3. **`docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 9 SHIPPED header** — added the
   full-delivery-record italic block above
   the existing §Milestone 9 business-
   objective section, matching the M8
   SHIPPED-header pattern.
4. **`docs/roadmap/MILESTONE_9_PLANNING.md`
   frontmatter flip** — `status: draft` →
   `status: shipped` + `shipped_at_session:
   SESSION_105` added.
5. **`docs/DEALER_KIT_SESSION_START.md`
   refresh** — backend baseline row
   (3,274 → 3,426); frontend baseline row
   (19 → 34); milestones-shipped row (added
   M9 SESSION_105); new M9 substrate row;
   tenancy carriers row (22 → 24); DRF
   admin endpoints row (40 → 47); frontend
   operator routes row (8 → 9); smoke-check
   expectations updated (3,426 backend + 34
   frontend).
6. **`docs/roadmap/MILESTONE_10_PLANNING.md`**
   — new. Mirrors M9 planning shape.
   Business objective + F&I workflow +
   compliance anchors + nine operational
   questions synthesized from
   `FINANCE_DEPARTMENT_MAPPING.md`. Ten
   entity sketches (§1.1–§1.8) covering
   CreditApplication, DealStructure,
   LenderProgram, LenderSubmission,
   Stipulation, Contract, FundingPacket,
   FundingStatus, Chargeback,
   ComplianceRecord. Four
   `[NEEDS-DECISION-BEFORE-M10.N]` items in
   §5. Eight-increment sequencing sketch in
   §7. Zero implementation this session.
7. **Coordinated commit** covering every
   M9.1–M9.6 file (bundling per SESSION_101
   decision; mirrors M8 `34352ed`
   precedent). Message template:
   `"Milestone 9 shipped — sale + delivery closure (SESSION_100-105)"`.

**One new M9-specific lesson recorded in the
retrospective (§6 #16):** *Substrate-gap
pushback is a productive session-open
pattern.* When a planning-time substrate
assumption fails direct inspection at session
open, the correct action is plan-scoped
pushback with explicit trade-offs (Option 1 =
scope creep, Option 2 = defer with re-entry
path, Option 3 = hack), not a silent
workaround. Both M9 gaps (SESSION_103
`LeadVehicleInterest` through-model + SESSION_104
missing GET companions) resolved cleanly this
way; both would have created scope creep or
degraded UX under a silent-workaround
approach.

## Test baseline

- **Backend:** **3,426 pass**, 1 skipped, 0
  fail (unchanged from SESSION_104 close —
  M9.6 is documentation-only).
- **Frontend Vitest:** **34 pass** (unchanged).
- **`manage.py check`:** clean.
- **`manage.py makemigrations --check
  --dry-run`:** "No changes detected."
- **`tsc --noEmit`:** clean.
- **`vite build`:** clean.

## Migrations

`0001` – **`0024`** (unchanged from M9.2;
M9.3–M9.6 shipped no schema changes).

## Files touched (M9.6 scope)

**Docs (added):**

- `docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`
  (~360 lines).
- `docs/roadmap/MILESTONE_10_PLANNING.md`
  (~420 lines).
- `docs/handoffs/SESSION_105_m9_closeout.md`
  (this file).

**Docs (modified):**

- `docs/CAPABILITY_MATRIX.md` — §7j
  subsection added between §7i and §8.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` —
  §Milestone 9 SHIPPED header block added.
- `docs/roadmap/MILESTONE_9_PLANNING.md` —
  frontmatter `status: draft` → `shipped`
  + `shipped_at_session:` field added.
- `docs/DEALER_KIT_SESSION_START.md` —
  baseline rows + milestone-shipped row +
  new M9 substrate row + carrier / endpoint
  / route rows + smoke-check expectations.
- `00-START-NEXT-SESSION.md` — overwritten
  with M10.1 priority (next section).

## Milestone 9 summary — all six increments

Per the retrospective §2 table, replicated
here for handoff-standalone readability:

| Increment | Session | Baseline delta |
|---|---|---|
| M9.0 planning | 099 | 0 (planning-only, doc landed in M8 close commit) |
| M9.1 Sale entity + gross_realized | 100 | +46 backend |
| M9.2 Delivery entity + checklist | 101 | +42 backend |
| M9.3 Q3 + Q6 + Q8 analytics extensions | 102 | +32 backend |
| M9.4 Q7 buyer estimate accuracy | 103 | +20 backend |
| M9.5 Operator UI extension | 104 | +12 backend + 15 frontend |
| M9.6 closeout | 105 | +0 (docs-only) |
| **Total M9 delta** | | **+152 backend / +15 frontend** |

**Zero regressions.** Zero migration drift
after `0024`. Every M8.4 proxy verb still
returns its original shape (locked by smoke
tests in `test_m9_analytics_extensions.py`).

## What SESSION_105 confirmed vs deferred

**Ready for consumption at M10 open:**

- Sale + Delivery entities are the
  operational close-out surface F&I builds
  its per-deal jacket on top of.
- Q7 buyer-estimate-accuracy verb consumes
  M9.1's `VehicleAcquisition.buyer` FK —
  the FK exists at nullable, so M10 credit-
  app work does not have to introduce it.
- The M8.5 + M9.5 operator UI shape
  (analytics tabs + per-vehicle dedicated
  pages under `dealer-ai-inventory/:stock/…`)
  is the pattern M10 UI will extend.

**Still deferred (from prior sessions):**

- `LeadVehicleInterest.stage_at_interest`
  annotation (SESSION_103 §0.a — through-
  model doesn't exist).
- Sale / Delivery cross-vehicle list views
  (M9.5 §1.7 Option A chose per-vehicle
  pages).
- Dense gross-profit series (M9.3 sparse
  shipped).
- `Vehicle.is_available` flip on Delivery
  completion (M9.2 declined; today
  operator-controlled).
- `AnalyticsCache` materialization
  (carry-forward from M8; no latency
  evidence yet).
- DMS write-back, state e-filing, sales-tax
  computation, portfolio-level BHPH
  analytics — carry-forward non-goals.

## Push authorization state

- Working tree at handoff-write time
  contains every M9.1–M9.6 file staged for
  the coordinated commit.
- `main` is up to date with `origin/main`
  before this session (last pushed:
  `4923997`).
- **Coordinated M9 commit lands as part of
  this session's work.** Per M8 precedent
  (SESSION_099 landed commit `34352ed`
  locally; push was a separate explicit
  go-ahead at SESSION_100 open), the push
  is deferred pending user authorization
  — check with the user at SESSION_106
  open whether the commit should push or
  stay local.

## What SESSION_106 (M10.1) should do

Per `MILESTONE_10_PLANNING.md` §7 M10.1:

1. **Push-authorization check for the M9-
   close commit** — same as SESSION_100
   opened the M8-close-commit push check.
2. **Confirm the §5 decisions** at
   session open. Recommendations per
   §9 summary:
   - **§5.a** (CreditApplication attach
     point) — TBD; will surface after
     re-reading FINANCE §workflow at
     session open.
   - **§5.b** (Stipulation vocabulary):
     Option A (small fixed set).
   - **§5.c** (Chargeback impact on
     `Sale.gross_realized`): Option B
     (additive `net_realized` verb; no
     M9 schema change).
   - **§5.d** (Onboarding lender
     migration): Option C (leave both).
3. **Read first:**
   `MILESTONE_10_PLANNING.md` §1.1 + §5 +
   §7 M10.1;
   `docs/handoffs/SESSION_105_m9_closeout.md`;
   `docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`
   §6 (sixteen lessons carry into M10);
   `docs/CAPABILITY_MATRIX.md` §7j (M9
   substrate M10 layers on top of);
   `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
   §workflow + §compliance + pains #1 /
   #4 / #6 / #7 / #9;
   `backend/dealer_ai/models.py::CustomerLead`
   (potential CreditApplication attach
   target — §5.a);
   `backend/dealer_ai/models.py::Sale`
   (M9.1 substrate for chargeback →
   commission-reversal plumbing —
   §5.c).
4. **Verify starting state:** M9-close
   commit in `git log`; `manage.py test
   dealer_ai` → **3,426 pass**; `check`
   + migrations clean.
5. **Draft (in order):**
   - `CreditApplication` model +
     migration `0025` + model-layer
     retention-clock enforcement.
   - `services/f_and_i/` package +
     first verbs.
   - Tenancy carrier addition.
   - First endpoint + role gate
     (`IsFinanceManagerOrOwnerAtActiveDealership`
     — new permission class in
     `permissions.py`).
   - ~30 focused tests.
6. **Baseline projection:** 3,426 →
   **~3,456**.
7. **Ship handoff at
   `docs/handoffs/SESSION_106_m10_inc1_credit_application.md`.**

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 10
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_10_PLANNING.md`
6. `docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_104_m9_inc5_operator_ui.md`
8. `docs/handoffs/SESSION_103_m9_inc4_buyer_accuracy.md`
9. `docs/handoffs/SESSION_102_m9_inc3_analytics_extensions.md`
10. `docs/handoffs/SESSION_101_m9_inc2_delivery.md`
11. `docs/handoffs/SESSION_100_m9_inc1_sale_entity.md`
12. `docs/handoffs/SESSION_099_m8_closeout.md` (M8 closeout template)
13. `docs/CAPABILITY_MATRIX.md` §7j
14. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
15. Current source code — authoritative.

Planning docs are claims. Rules + research
+ code are facts.
