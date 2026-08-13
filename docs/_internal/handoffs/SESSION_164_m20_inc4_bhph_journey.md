---
title: "SESSION_164 handoff — Milestone 20 · Increment 4 (M20.4 — BHPH collections workflow, scope-narrowed to read-side)"
status: historical
type: handoff
date: 2026-08-02
session: 164
milestone: 20
milestone_status: in-progress
milestone_name: "Operational Journey Validation (Playwright acceptance testing)"
increment: 4
increment_status: shipped
commit: TBD
---

# SESSION_164 — Milestone 20 · Increment 4 (M20.4 — BHPH collections read-side workflow)

## What shipped

The sixth (and final planned) journey layered onto the M20.1
framework — **BHPH collections read-side workflow**. **Scope
narrowed from the original M20 plan** per §0.a M20.4 decision 1
(details below). Full local acceptance dry-run: **12 passed
(19.1s)** — 6 setup steps + 6 journeys.

Per M20 planning §7 M20.4 (as adjusted). Assertions target
business state through the M12 BHPH admin API.

**One new persona.** `bhph_collector` (username
`acceptance-bhph-collector`) — underlying role is
`sales_manager` because the M12 collections endpoints gate on
`IsSalesManagerOrOwnerAtActiveDealership`; the model-level
`ROLE_COLLECTIONS` constant is defined but not wired to any
endpoint. Persona name reflects the operational role even though
the role assignment is different. Recorded as §0.a M20.4
decision 2.

Added to `personas.ts`, `login.setup.ts` (new setup step +
extended `SEED_COMMANDS`), `playwright.config.ts` (new project
entry `bhph_collector` for `journeys/bhph/*` with dedicated
storage state).

**One new backend seed delta command:**

- `seed_journey_bhph_collections_workflow.py` — provisions the
  collector user + role plus a full fixture chain: buyer
  (`CustomerLead`) + vehicle (stock `M20-BHPH-ACCEPT`) + BHPH
  sale + `BhphNote` (weekly cadence, $6,500 principal, 21.99%
  APR, 78 weeks) + 1 historical payment + 1 `BhphPromiseToPay`
  in the `broken` state + 1 `CollectionContact` + 1
  `Repossession` in the `ordered` state. Uses direct object
  creation for Vehicle/Buyer/Sale/BhphNote (matches the demo
  archetype pattern at
  `services/demo_store/archetypes/bhph.py:672-711`), and M12
  service verbs for the child rows (`record_payment`,
  `record_promise` + `mark_broken`, `record_contact`,
  `record_repossession`). Idempotent via stable stock number.
  **14 focused backend tests**.

**One new assertion helper**
(`acceptance/support/assertions/bhph.ts`):

- `findSeededNoteId(request, {principal, apr, termWeeks})` —
  the M12 list endpoint returns bare `{count, results}` (not
  envelope-wrapped like the M17 accounting endpoints), and the
  note detail response does NOT expose `sale.vehicle.stock_number`.
  Matches the seeded note on its distinctive loan-term
  signature.
- `expectNoteDetailPopulated(request, notePk)` — verifies all
  four child collections (payments, promises, contacts, repos)
  return >= 1 row on the given note. Handles both wrapped
  (e.g. `{bhph_payments: {count, results}}`) and bare
  (`{count, results}`) response shapes since M12 endpoints are
  not fully consistent.

**One new journey spec**
(`acceptance/journeys/bhph/collections_workflow.spec.ts`):

- Collector lands on `/dealer-ai-bhph/portfolio`, sees the
  BHPH Portfolio heading + KPI cards (Notes in portfolio +
  Cure rate).
- Journey pre-flight uses the API to (a) resolve the seeded
  note's PK via loan-term signature match, and (b) confirm
  the note detail is fully populated at the service layer.
- Collector navigates to `/dealer-ai-bhph/notes/<pk>` and
  verifies all five card sections render (Loan terms,
  Payments (N), Promises (N), Contacts (N), Repossessions (N)).
- Business-outcome assertion re-verifies the note detail is
  populated — the collector can trust the UI's non-zero
  counts reflect persisted state.

Not tagged `@pilot-critical` — runs only in the full-suite CI
on `main` push per §5.h.

## Verification

**Backend baseline (post-M20.4):** 4,741 → **4,755 pass** (+14
BHPH seed command tests). Frontend Vitest baseline unchanged:
**153 pass**. `tsc --noEmit` clean in `frontend/` +
`acceptance/`. Django `check` + `makemigrations --check
--dry-run` clean.

**Acceptance suite (local dry-run):**
- Setup: 6 steps (baseline seed + 5 persona logins) — pass.
- `pilot/onboarding.spec.ts` (@pilot-critical) — pass.
- `owner/morning_review.spec.ts` (@pilot-critical) — pass.
- `sales_manager/daily_startup.spec.ts` — pass.
- `recon/workflow.spec.ts` — pass.
- `office/accounting_workflow.spec.ts` — pass.
- `bhph/collections_workflow.spec.ts` (M20.4) — pass.
- **Total: 12 passed (19.1s).**

**Zero drift:**
- Migrations unchanged at `0001`–`0048`.
- Tenancy carriers unchanged at **52**.
- Permission classes unchanged at **7** (zero-drift streak
  intact at nineteen consecutive milestones; extends to
  twenty at M20.5 close).
- DRF admin surface unchanged at **113**.
- Frontend operator routes unchanged at **20**.
- No existing backend service verb, endpoint, migration, or
  frontend route modified.

## §0.a — Implementation-time decisions

**M20.4 decision 1 — journey scope narrowed to READ SIDE
only.** The M20 planning §7 M20.4 originally described the
BHPH collections journey as "daily book review, recording a
promise-to-pay, capturing a collection contact, initiating
repossession on a broken promise". As of M12.7, the four
write-side operations (record PtP, mark broken, log contact,
initiate repo) have **no shipped frontend UI** — only backend
endpoints. Per M20's guiding principle ("business outcomes
through the real application"), a Playwright journey cannot
validate a workflow whose UI doesn't exist. M20.4 therefore
validates the READ SIDE of the daily book review workflow: the
seed plants the operationally-relevant state via M12 service
verbs, and the journey verifies the collector can see it
through the shipped portfolio + note detail UI.

**Operator-friction data point for M21+ candidate
consideration:** the write-side BHPH collections UI is
missing. This surfaces as a candidate scope item for M21 or
later — probable naming: "M12.8 BHPH collections write-side
UI". Recorded here so future planning can surface it.

**M20.4 decision 2 — `bhph_collector` persona uses
`sales_manager` role.** The M12 collections endpoints gate on
`IsSalesManagerOrOwnerAtActiveDealership`; the model-level
`ROLE_COLLECTIONS` constant is defined (models.py:23) but not
wired to any endpoint. Persona name reflects operational role
even though the underlying auth role is different. If M12.8
ships write-side UI, the endpoint auth may or may not fine-
grain to `ROLE_COLLECTIONS` — persona role assignment can
change then.

**M20.4 decision 3 — fixture-note lookup by loan-term
signature.** The M12 note list endpoint returns bare
`{count, results}` (not envelope-wrapped like the M17
accounting endpoints), and the note detail response
(`BhphNoteDetailResponse`) does NOT expose
`sale.vehicle.stock_number`. The assertion helper matches
the seeded note by its distinctive loan-term signature
(principal + APR + term_weeks). Acceptable on the acceptance
DB where the M20.4 seed is the sole source of BHPH notes; if
this pattern later collides with additional BHPH seeds, add
a `?stock=` filter to the list endpoint as a future
increment.

**M20.4 decision 4 — direct ORM creation for Vehicle/Buyer/
Sale/BhphNote.** Matches the demo archetype pattern
(`services/demo_store/archetypes/bhph.py:672-711`). The
alternative — going through `record_sale` + `record_bhph_note`
— fires M15 GL posting side effects that add noise to the
JournalEntry table without adding value for a single fixture
note. Child rows (payment, promise, contact, repossession)
DO go through service verbs (`record_payment`, `record_promise`
+ `mark_broken`, `record_contact`, `record_repossession`) so
the state machines fire correctly.

## What's next: SESSION_165 M20.5 close-out

Per `MILESTONE_20_PLANNING.md` §7 M20.5 — milestone close-out:

- **Full-suite CI validation.** Verify targets on `main` (~5–8
  min full suite) + PR (~90s pilot-critical subset). Since
  M20.1 CI job wired but has NOT actually run (push held), the
  first real CI execution will happen on the M20.5 push.
- **Intentional dry-run failure** to confirm artifact upload
  (HTML report + trace + video). Fix, then verify green run
  before the coordinated push.
- **`docs/CAPABILITY_MATRIX.md` §7u** — M20 shipped surface:
  new `acceptance/` workspace + 6 journeys + CI job + 6 seed
  delta commands + settings.py extension.
- **`docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`** covering
  lessons learned, what shipped, deferrals reviewed, §8/§9
  standing questions. Include the M20.4 §0.a decision 1
  scope narrowing + candidate "M12.8 BHPH collections write-
  side UI" as an M21+ candidate.
- **`docs/roadmap/MILESTONE_21_PLANNING.md`** skeleton drafted
  with M20 retrospective §9 candidate list refreshed.
- **`docs/roadmap/IMPLEMENTATION_ROADMAP.md`** updated with
  M20 shipped status.
- **`00-START-NEXT-SESSION.md`** refreshed for SESSION_166 /
  M21.0.
- **Coordinated close-out commit + FIRST PUSH.** All five M20
  commits (M20.0-M20.4 already local + M20.5 close-out) push
  together per the M18/M19 cadence. This triggers the first
  real GitHub Actions acceptance job run.

**Backend baseline target at M20.5 close:** ~4,755 pass
(unchanged — M20.5 is docs + retrospective, no new tests).
Frontend Vitest: 153 (unchanged).

**Acceptance baseline at M20.5 close:** **6 journeys full-suite
passing on `main` CI** (target metric); pilot-critical subset
of **2** passing on PR.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_20_PLANNING.md`
   (this milestone's active memo)
6. `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
   §9 (Candidate J origin)
7. `docs/CAPABILITY_MATRIX.md` §7t
   (M19 shipped surface — the substrate M20 validates)
8. `docs/handoffs/SESSION_163_m20_inc3_backoffice_journeys.md`
   (M20.3)
9. `docs/handoffs/SESSION_162_m20_inc2_dashboard_journeys.md`
   (M20.2)
10. `docs/handoffs/SESSION_161_m20_inc1_framework.md`
    (M20.1 framework substrate)
11. `docs/handoffs/SESSION_160_m20_inc0_planning.md`
    (M20.0 planning close)
