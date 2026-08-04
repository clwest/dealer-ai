---
title: "SESSION_203 handoff — Milestone 31 · Increment 0 (M31.0 — planning refinement + target selection)"
status: historical
type: handoff
date: 2026-08-04
session: 203
milestone: 31
milestone_status: active
milestone_name: "Journal-Entry Template Restore / \"Show inactive\" UI (lifecycle-completion on M28.1 substrate + M30.1 include_inactive kwarg)"
increment: 0
increment_status: shipped
commit: pending
commit_notes: "M31.0 planning session — local commit at close per M28.0 / M29.0 / M30.0 planning-only cadence; hash backfill via a subsequent commit; NOT pushed. Coordinated push at M31 close after explicit user confirmation."
---

# SESSION_203 — Milestone 31 · Increment 0 (M31.0 — planning refinement + target selection)

## What shipped

SESSION_203 opened as a planning-only session per the
M30.2 close-out priorities in `00-START-NEXT-SESSION.md`.
One deliverable landed:

1. **M31.0 planning memo** authored at
   `docs/roadmap/MILESTONE_31_PLANNING.md` — target locked
   as **NEW Restore / "Show inactive" templates UI
   (lifecycle-completion)** (§5.a). User-confirmed after
   direct evaluation against F&I chargeback and other
   fresh direct-operator gaps under the primary
   operational-value lens with explicit instruction *not*
   to select Restore solely because it continues the M28–
   M30 lineage. All §5.b–§5.h decisions locked (D1–D10,
   risk register, verifications, phasing, DoD compliance,
   rollback, non-goals). Lifecycle-integrity precheck (L1
   — user-directed) resolved as a frontend-only guard;
   server-side coupling explicitly rejected to preserve
   the intentional JournalEntry ↔ JournalEntryTemplate
   decoupling.

No §0.a M31.0 amendments — the first M30 CI run on
`f658c06` (hash-backfill commit) is green (workflow
`30930670900`, success in 2m50s at 2026-08-04T16:45:30Z);
no regression to correct.

Full active memo authored at
`docs/roadmap/MILESTONE_31_PLANNING.md`.

**Session artifacts:**

- **Starting-state verification (§1):** git clean; `HEAD
  == origin/main @ f658c06` (M30 push confirmed pre-
  session); Redis PONG; Django `check` clean;
  `makemigrations --check` clean; frontend `tsc --noEmit`
  clean; acceptance `tsc --noEmit` clean; backend suite
  **4,904 pass, 1 skipped, 0 fail** (166.3s); frontend
  Vitest **300 pass** (36 files, 6.4s); acceptance DB
  proactively reset per SESSION_200 §0.a durable lesson
  (v). All matches M30.2 close baseline exactly.
- **First M30 CI run monitored (§2):** acceptance
  workflow on `f658c06` (M30.2 hash-backfill commit)
  **completed success** in 2m50s. Prior run on
  `f1c26df` (M30-shipped commit) was `cancelled` —
  expected, superseded by the immediate `f658c06` push.
  Main is CI-verified shipped at the M30.2 baseline. No
  §0.a M31.0 amendment triggered.
- **Audit regeneration (§3):** `python3 -m
  dealer_ai.scripts.audit_operational_surface` invoked.
  Output: **157 total / 123 covered / 34 backend-only /
  317 service verbs**. Byte-identical to the committed
  M30.2 artifact. No drift.
- **Candidate list presented (§4)** across the M30 §9
  tiers:
  - **Elevated (highest recommendation strength at
    M31.0):** NEW Restore / Show-inactive UI (freshly
    unblocked by M30.1 kwarg); NEW C — F&I chargeback
    substrate (gated pending pilot evidence); NEW O2
    (M26/M27/M28/M29/M30 deferral, unchanged); NEW O3
    (deferral, unchanged); H — test-hygiene remediation.
  - **Gated:** T, U, L, M.
  - **Deferred pending evidence:** D.
  - **Deferred stable:** G.
  - **Deferred at M30 §3 / M29 §3 / M28 §3 / M27 §3 /
    M25 §4:** all carried forward unchanged.
  - **Fresh direct-operator gaps surveyed from audit
    backend-only list:** deal writeups (#112–114 — no
    operator evidence, opens new domain surface); vendor
    detail (#43 wrapper-only, small polish); photo
    reorder (#65 wrapper-only, small polish); demo-store
    feedback (#152 — not operator-facing). None
    presented as evidenced operator pain the way Restore
    does.
- **Recommendation (§5):** NEW Restore / "Show inactive"
  templates UI (lifecycle-completion), under the primary
  operational-coverage lens, evaluated against the
  user's specific test: *"favor it only if the evidence
  shows that completing the reversible template
  lifecycle is the highest-value bounded operator
  workflow available."* Four load-bearing evidence
  signals recorded (§5.a of planning memo):
  1. M30.2 shipped a copy promise
     (`AccountingJournalEntriesPage.tsx:670-672` — *"You
     can restore this template later. (Restore UX
     ships in a future milestone.)"*) that the shipped
     surface does not yet fulfill.
  2. Backend intervention (Django shell) is the only
     path to un-hide a deactivated template today.
  3. Scope is bounded: one new endpoint + one new
     service verb + one one-line view-layer extension +
     toggle + row state + Restore button + confirmation
     + L1 button-disable guard + single Playwright
     describe block.
  4. Substrate is at 60%+ readiness (M30.1
     `include_inactive` kwarg present on both
     `list_journal_entry_templates` and
     `get_journal_entry_template`); zero new migration.
- **User confirmation:** §5.a locked as **NEW Restore /
  "Show inactive" templates UI (lifecycle-completion)**
  with all lifecycle-completion constraints preserved
  (Deactivate/Restore vocabulary consistency; inactive
  templates out of default active list; explicit
  operator toggle; visually + semantically distinct
  inactive rows with a11y status text; idempotent +
  tenant-scoped Restore; PATCH cannot mutate is_active;
  historical JEs untouched; Restore preserves everything
  except lifecycle timestamp; complete-reversible-
  lifecycle Playwright per user 7-step spec; hard delete
  + bulk + audit history + concurrency control +
  mutation history all out of scope).
- **Lifecycle-integrity precheck resolved.** Trace of
  the instantiate flow confirmed instantiation is purely
  client-side hydration
  (`AccountingJournalEntriesPage.tsx:271`
  `handleInstantiate` copies template state into React
  state; the JE that gets POSTed via `createJournalEntry`
  does not carry the template pk). Consequences: (a)
  stale-tab race outcomes are accepted per intentional
  decoupling (M28.0 §5.b + M30.0 §4.7) — server-side
  coupling explicitly rejected; (b) Show-inactive view
  requires the smallest fail-closed frontend guard (L1)
  — disable Edit + Instantiate on inactive rows with
  explanatory aria-label. Recorded as lifecycle-
  integrity, not feature expansion, per user
  confirmation of §5.b review point 6.
- **§5 locks (all):** target (§5.a); ten load-bearing
  design decisions D1–D10 (§5.b); ten-item risk register
  (§5.c); eight verifications (§5.d); two-increment
  phasing (§5.e — M31.1 backend + M31.2 UI); DoD
  compliance (§5.f — exception path at M31.1 as sixth
  precedent, direct satisfaction at M31.2); rollback
  plan (§5.g); non-goals (§5.h — nine explicit
  exclusions carried as future re-entry candidates plus
  the coupling-preserving R1 acceptance).

## 1. Verification results at open

| Check | Expected | Actual |
|---|---|---|
| `git status` | clean | ✅ clean |
| `HEAD == origin/main` | true | ✅ true (f658c06) |
| `git log --oneline -10` top | M30.2 hash backfill | ✅ f658c06 |
| Backend suite | 4,904 pass, 1 skip | ✅ 4,904 pass, 1 skip (166.3s) |
| Frontend Vitest | 300 pass, 36 files | ✅ 300 pass, 36 files (6.4s) |
| Django `check` | clean | ✅ clean |
| `makemigrations --check` | No changes | ✅ No changes |
| Frontend `tsc --noEmit` | clean | ✅ clean |
| Acceptance `tsc --noEmit` | clean | ✅ clean |
| `redis-cli ping` | PONG | ✅ PONG |
| Acceptance DB reset | done | ✅ removed proactively |
| Audit artifact | 157 / 123 / 34 / 317 | ✅ 157 / 123 / 34 / 317 (byte-identical) |
| First M30 CI run | green (expected) | ✅ **GREEN** (26 passed / 0 failed / 2m50s on f658c06) |

## 2. First M30 CI run

Run ID: `30930670900`. Status: **success**. Duration:
2m50s on `main` at commit `f658c06` (M30.2 hash-backfill
commit). **26 passed / 0 failed.** Main is CI-verified
shipped at the M30.2 baseline.

Prior run on `f1c26df` (M30 shipped commit): `cancelled`
after 42s — expected, superseded by the immediate
`f658c06` hash-backfill push. Two runs back on `43b715b`
(SESSION_200 §0.a hotfix): also success in 2m43s.

No regression to correct. No §0.a M31.0 amendment
triggered.

## 3. Audit regeneration

`python3 -m dealer_ai.scripts.audit_operational_surface`
produced **157 total / 123 covered / 34 backend-only /
317 service verbs**. Byte-identical to the committed
M30.2 artifact. No drift.

## 4. Candidate list presented at open

Presented under the M30 retrospective §9 evidence
structure. Each candidate carried scope + operator pain
resolved + dependency notes:

**Elevated (highest recommendation strength at M31.0):**

- **(a) NEW — Restore / "Show inactive" templates UI
  (lifecycle-completion).** Freshly unblocked at M30
  close by M30.1's `include_inactive` service kwarg.
  Small-to-moderate scope; substrate at 60%+ readiness;
  closes shipped-surface Restore promise; removes
  Django-shell operator blocker. *Deps:* M28.1 substrate,
  M30.1 kwarg; no new migration.
- **(b) NEW C — F&I chargeback substrate.** Fifth link
  in substrate-compound-value lineage. Would reuse
  M27.1 gl-accounts + M28.1 templates. **Gating**
  explicit per M30 §9 — deferred pending pilot evidence
  (unchanged at M31.0). Endpoint #101 exists but is one
  of 13 uncovered F&I endpoints (audit #89–101);
  meaningful UI needs contract + back-end-product
  context. Not bounded without operator direction.
- **(c) NEW O2 — Row 5 public-fetch-helper regex
  refinement.** Audit-tooling accuracy work.
  M26/M27/M28/M29/M30 deferral, unchanged. Requires
  SESSION-189-§3-style tracing at open; blast radius
  unknown.
- **(d) NEW O3 — Rows 1–4 plain-string-literal
  investigation.** Audit-tooling accuracy work.
  M26/M27/M28/M29/M30 deferral, unchanged. Requires
  tracing.
- **(e) H — Test-hygiene remediation.** Three shared-DB
  non-idempotent journeys (`sales_manager/daily_startup`,
  `recon/workflow`,
  `office/accounting_workflow` trial-balance snapshot).
  CI-stability infra; zero direct operator gain.

**Gated (unchanged from M29+M30 close):** T (real tester
feedback), U (hosted-demo substrate), L (first-live-
pilot staging), M (multi-operator support — breaks the
zero-drift permission-class streak with intent).

**Deferred pending evidence:** D (LLM router / cost
caps).

**Deferred but stable:** G (dashboard testid hardening).

**Deferred at M30 §3, M29 §3, M28 §3, M27 §3, M25 §4
(all valid for later re-entry):** hard-delete escape
hatch on templates; template mutation audit trail;
optimistic concurrency control on template edit; bulk
delete/edit; fully-variable UX polish; server-recorded
instantiation audit trail; named / shared template
variables; historical-template back-reference on
JournalEntry; server-side template search/pagination;
standalone template detail page; standalone Chart of
Accounts page/route; JE edit/update; `posted_by_user`
override; advanced picker filtering; server-side gl-
accounts search/pagination; secondary "+ Record test
drive" launch point; clickable "Referred by" nav; named-
platform webhook adapters; attribution rollups; vehicle-
picker advanced filters.

**Fresh direct-operator gaps surveyed from audit
backend-only list** (per user direction to compare
Restore against fresh gaps under the primary
operational-value lens):

- **Deal writeups (audit #112–114).** 3-endpoint
  create/approve/hand-off flow. No operator pain
  evidence surfaced M28→M30. Would open a new domain
  surface without operator direction.
- **Vendor detail (#43, wrapper-only)** and **photo
  reorder (#65, wrapper-only).** Small polish gaps.
  Wrappers exist; no component imports them. Not
  evidenced operator pain.
- **Demo-store feedback (#152).** Not operator-facing
  (internal telemetry).

None of these surface as bounded, evidenced operator
workflows the way Restore does.

## 5. Recommendation and user confirmation

**Recommended:** NEW Restore / "Show inactive" templates
UI (lifecycle-completion) as the M31 target.

**Rationale (§5.a of planning memo):** four load-bearing
evidence signals — (1) shipped-surface Restore promise
at `AccountingJournalEntriesPage.tsx:670-672`; (2)
Django-shell-only current path to Restore; (3) bounded
scope fitting a two-increment M31; (4) substrate at
60%+ readiness with zero new migration required. The
substrate-compound-value framing (fifth link) was noted
as *supporting*, not *load-bearing*, per explicit user
direction not to select on lineage grounds alone.

**User confirmation.** §5.a locked with the full set of
lifecycle-completion constraints (see §7 §5 locks
below). Six §5.b review points confirmed:

1. D3 query parsing: fail-closed — only literal `true`,
   case-insensitive (accepts `true`, `TRUE`, `True`;
   rejects `1`, `yes`, empty, malformed, omitted).
2. D7 inactive-row actions: visible-but-disabled Edit +
   Instantiate with explanatory accessible labels; not
   silently hidden.
3. D8 confirmation copy: as drafted — row action
   "Restore"; confirmation reframes to "Reactivate".
4. D10 copy fulfillment: bundled into M31.2 (no shipped
   UI carries stale "future milestone" reference after
   M31 close).
5. M31.1 test budget: ~24–26 focused tests confirmed
   reasonable given the lifecycle, idempotency,
   tenancy, authorization, preservation, timestamp, and
   query-parsing contracts.
6. L1 framing: lifecycle-integrity guard, not feature
   expansion — necessary to make the newly exposed
   inactive-state UI truthful and safe.

Additional explicit preservation confirmed by user: the
documented stale-tab outcome (JE created from previously
hydrated template values is a valid standalone posting)
remains — do NOT introduce server-side template coupling
merely to prevent that accepted race.

## 6. Verifications performed at planning-open

All eight verifications performed at M31.0 open (memo
§4). All resolved CLEAN.

### 6.1 Lifecycle-integrity precheck (L1 — user-directed)

Directed by user at §5.a lock request: verify whether
inactive templates can currently still be instantiated
through any stale client state or direct UI path.

**Trace.** `handleInstantiate` at
`AccountingJournalEntriesPage.tsx:271` is purely client-
side hydration — copies `template.description` +
`template.lines` + lock configuration into local React
state; opens `NewJournalEntryDialog` prepopulated. The
JE that gets POSTed via `createJournalEntry` does not
carry the template pk. There is no server "instantiate"
endpoint that would check `template.is_active`.

**Result.** Two consequences separated:

- **Stale-tab race:** accepted per user direction and
  M28.0 §5.b + M30.0 §4.7 intentional decoupling.
  Server-side coupling explicitly rejected.
- **Show-inactive view (new at M31.2):** requires L1
  guard — disable Edit + Instantiate on inactive rows
  with explanatory aria-label. Smallest fail-closed fix
  because a server guard would have nothing to check.

### 6.2 Substrate readiness

Both `get_journal_entry_template` and
`list_journal_entry_templates` accept
`include_inactive: bool = False` kwarg (M30.1 —
`services/accounting/template.py:270-282` + `285-315`).
Neither endpoint currently exposes the kwarg. One
one-line view-layer addition needed on the list
endpoint; zero addition needed for the detail endpoint
(edit + delete already operate on soft-hidden rows via
M30.1 substrate).

### 6.3 No FK from JournalEntry to JournalEntryTemplate

Structurally verified at M30.0 §4.7 and unchanged;
re-verified at M31.0 open. `JournalEntry` model has no
`template` FK, no `template_id` column, no reverse
relation. Restore + Deactivate cannot cascade to any
existing JE, snapshot, trial-balance report, or JE
list/detail surface.

### 6.4 Copy-promise audit on M30.2 shipped surface

`AccountingJournalEntriesPage.tsx:670-672` shipped
delete-confirmation copy contains verbatim promise
*"You can restore this template later. (Restore UX
ships in a future milestone.)"*. D10 fulfillment
scope in §5.b requires updating this copy in M31.2 to
point at the new Show-inactive toggle.

### 6.5 Endpoint-shape precedent

`admin/vehicle-photos/<uuid:public_id>/restore/` (audit
endpoint #68, covered) already exists in the codebase
as a dedicated-Restore-verb pattern. M31 uses the same
URL shape and HTTP verb.

### 6.6 FK / row-action discoverability

Not applicable — Restore is state-mutation, not
create/edit. Pk needed to Restore is present on every
Show-inactive-view row via
`data-testid="template-row-inactive-<pk>"`. No
substrate work required for discoverability
(feedback-memory rule satisfied).

### 6.7 Downstream + intake symmetry

Intake: Show-inactive toggle is sole intake surface.
Downstream: after Restore, row re-enters default
active list AND becomes valid instantiation target
AND becomes editable. Both directions of reversible
lifecycle covered.

### 6.8 DoD compliance

M31.1 invokes exception path (backend substrate; no
operator-facing behavior change on its own) — **sixth
invocation** (M26 + M27.1 + M28.1 + M29.1 + M30.1 +
M31.1). M31.2 satisfies DoD directly via new
`restore-inactive` describe block (journey count 21 →
22).

## 7. §5 locks summary

All ten §5.b design decisions locked in the memo (§5.b
D1–D10). Most detailed:

- **D1 — Restore is a dedicated verb, never a PATCH
  side-effect.** New `restore_journal_entry_template(*,
  pk, dealership)` service verb + new endpoint
  `admin/accounting/journal-entry-templates/<int:pk>/restore/`
  (POST). PATCH continues to silently drop `is_active`
  per M30.2 lesson (w).
- **D2 — Restore is idempotent, tenant-scoped,
  preserves everything except lifecycle timestamp.**
  Full service contract spelled out in memo; endpoint
  tests assert `name`, `description`, lines (fields +
  amounts + ordering), and `created_at` untouched;
  `updated_at` advances only on state-change branch.
- **D3 — Endpoint list exposure fail-closed.** Only
  literal `"true"` (case-insensitive) enables inactive
  rows. `1`, `yes`, empty, malformed, missing all
  resolve to active-only default.
- **D4 — Frontend list wrapper accepts explicit
  `includeInactive` parameter.** Toggle label "Show
  inactive"; wrapper param `includeInactive` (camel);
  URL param `include_inactive` (snake).
- **D5 — Show-inactive is an explicit operator toggle.**
  Default off; never auto-toggles; no silent mixed-
  status list.
- **D6 — Inactive rows visually AND semantically
  distinct (a11y-first).** Three independent signals:
  Inactive badge + row aria-label + testid; muted
  styling is reinforcement, not primary channel.
- **D7 — Row-action asymmetry with L1 guard.** Delete
  slot → Restore button on inactive rows; Edit +
  Instantiate visible-but-disabled with explanatory
  aria-labels.
- **D8 — Restore confirmation reframes vocabulary.**
  Row "Restore" → confirmation "Reactivate template?".
  Mandated copy spelled out in memo.
- **D9 — Historical JEs untouched.** Playwright
  asserts byte-identical JE description + `total_debit`
  + trial-balance total before and after full
  deactivate-restore round-trip.
- **D10 — M30.2 copy update bundled in M31.2.** New
  text points at Show-inactive toggle; Vitest + Playwright
  assertions updated.

**Coverage delta at M31 close (projected):** 157 → 158
endpoints (+1); 123 → 124 covered (+1); 34 backend-
only unchanged; 317 → 318 service verbs. Two-source
agreement gate at M31.2 close.

## 8. Streaks at M31.0 close

- **Planning-time as-recommended streak:** 9 → **10**.
  Target selected as recommended after five-alternative
  comparison + lifecycle-integrity precheck performed
  at user direction. §0.a M31.0 amendments (none as of
  M31.0 open) do not affect the streak. Historical run
  of 89 across M10 → M23 preserved for the record.
- **Zero-drift permission-class streak:** unchanged at
  **31** (M10 → M30). M31.0 is planning-only; no code
  change. Projection at M31 close: **32 consecutive**
  (M31.1 adds Restore endpoint reusing `_M131_PERMS`;
  M31.2 no permission change).
- **Substrate-compound-value continuation:** 4 links
  realized. Projection at M31 close: **5 links** (M27.1
  → M28.1 → M29 → M30 → **M31**). Zero new migration.
- **DoD exception path invocations:** 5. Projection at
  M31.1 close: **6** (M26 + M27.1 + M28.1 + M29.1 +
  M30.1 + M31.1).
- **Additive-prop pattern (durable lesson (t)):** M31
  does not add new mode branches; the co-located
  inline-dialog choice for D8 confirms the M28.0
  `feedback_duplicate_small_stable_logic.md` rule
  continues to govern small stable dialog logic.
- **Copy-vocabulary asymmetry (durable lesson (x)):**
  first re-application at M31.2 (Restore/Reactivate)
  will elevate from "surfaced" (M30.2) to "load-
  bearing across two milestones."

## 9. Push status

**No push at SESSION_203 close.** M31.0 is planning-only
per the standard M28.0 / M29.0 / M30.0 cadence.
Coordinated M31 close push deferred to explicit user
confirmation after M31.2 close, following the M27 /
M28 / M29 / M30 coordinated-close cadence.

Local commits at SESSION_203 close:

- SESSION_203 planning memo (`docs/roadmap/MILESTONE_31_PLANNING.md`)
  + this handoff + `00-START-NEXT-SESSION.md` flip land
  in a single local-only commit per planning-only session
  cadence; hash backfill via a subsequent commit.

Expected M31 commit count at coordinated push: **4–6**
(planning + M31.1 backend + M31.2 UI + close-out fold,
plus hash-backfill follow-ups per convention).

## 10. Next session priorities

`00-START-NEXT-SESSION.md` overwritten for **SESSION_204
· Milestone 31 · Increment 1 (M31.1 — backend
substrate)**. First-thing sequence per M28.1 / M29.1 /
M30.1 pattern:

1. **Verify starting state** (git status, backend
   tests 4,904 pass, frontend Vitest 300 pass, checks,
   migrations, tsc, redis, `db.acceptance.sqlite3`
   proactive reset).
2. **Confirm working from M31.0 planning memo** —
   read `docs/roadmap/MILESTONE_31_PLANNING.md` §5.b
   D1–D3 before touching backend code.
3. **Ship M31.1 backend substrate** per §5.e:
   - Service verb `restore_journal_entry_template`.
   - Endpoint `admin/accounting/journal-entry-templates/<int:pk>/restore/`
     (POST) reusing `_M131_PERMS`.
   - Extend list endpoint with `?include_inactive=true`
     fail-closed parsing per D3.
   - Zero migration.
   - Tests ~24–26 (D2 + D3 coverage; extended endpoint
     + service coverage per M30.1 lesson).
4. **Verify M31.1 close baselines:** backend suite
   4,904 → ~4,930 pass; `check` + `makemigrations
   --check` clean; audit artifact 157 → 158 / 123
   backend-only shift by 1 during transitional state
   (M31.2 will re-cover the new endpoint).
5. **DoD exception path** — sixth invocation. Document
   in §3 of M31.1 handoff (no operator-facing behavior
   change on its own; M31.2 satisfies DoD directly).
6. **Ship the M31.1 handoff at
   `docs/handoffs/SESSION_204_m31_inc1_backend.md`.**
   **Do NOT push** — coordinated push at M31 close.

## 11. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_30_RETROSPECTIVE.md` §9
6. **`docs/roadmap/MILESTONE_31_PLANNING.md`** (governing
   contract for M31)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
8. `docs/CAPABILITY_MATRIX.md` §7ε (M30 shipped surface)
9. `docs/handoffs/SESSION_202_m30_inc2_frontend.md`
10. **This handoff** (`SESSION_203_m31_inc0_planning.md`)
11. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs D8 co-located inline-dialog)
12. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified through M31.0 §6.6)
