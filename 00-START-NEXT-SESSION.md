---
state: active
date: 2026-08-03
last_session_shipped: SESSION_193
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: shipped
milestone_11_status: shipped
milestone_12_status: shipped
milestone_13_status: shipped
milestone_14_status: shipped
milestone_15_status: shipped
milestone_16_status: shipped
milestone_17_status: shipped
milestone_18_status: shipped
milestone_19_status: shipped
milestone_20_status: shipped
milestone_21_status: shipped
milestone_22_status: shipped
milestone_23_status: shipped
milestone_24_status: shipped
milestone_25_status: shipped
milestone_26_status: shipped
milestone_27_status: shipped
next_session: SESSION_194
next_milestone: 28
next_milestone_name: "(target selection pending — locked at M28.0 open)"
next_increment: 0
next_increment_name: "M28.0 — Planning refinement + target selection"
---

# Next session — SESSION_194 · Milestone 28 · Increment 0 (M28.0 — planning refinement + target selection)

> **Milestone 27 — Journal-Entry Creation UI (via shared
> GLAccount substrate) — SHIPPED at SESSION_193.**
> Three-session milestone (SESSION_191 → SESSION_192 →
> SESSION_193). M27.3 close-out folded into M27.2 per §5.h
> Option B — both increments' §5.e Phase 1 + Phase 2 checks
> passed cleanly on the first regeneration. **Backend
> baseline 4,805 → 4,813 (+8 M27.1 regression tests).
> Frontend Vitest 226 → 246 (+20 across GLAccountPicker +
> NewJournalEntryDialog + page extensions). Acceptance 14 →
> 16 journeys (+2 in accounting_je_create.spec.ts).** Audit
> coverage **119 / 154 → 121 / 155** (row 140
> `admin/accounting/journal-entries/` create-endpoint flipped
> → `covered`; new row 149 `admin/accounting/gl-accounts/`
> shipped and flipped → `covered` on the same run).
>
> **§5.e two-source agreement confirmed** at both M27.1 close
> (155 / 119 covered / 36 backend-only; new row
> `defer-candidate-O2` with `⚠ wrapper-only`) and M27.2 close
> (155 / 121 covered / 34 backend-only; row 140 + row 149 both
> flipped) across all recording sites: `CAPABILITY_MATRIX.md`
> §7β, `IMPLEMENTATION_ROADMAP.md` §Milestone 27,
> `MILESTONE_27_RETROSPECTIVE.md` §7, this doc's operational-
> state block.
>
> **Zero-drift permission-class streak extends 26 → 27**
> consecutive milestones (M10 → M27). Both new M27 surfaces
> reuse `_M131_PERMS`; no permission classes evolve. One
> new backend endpoint added (`gl-accounts`); one existing
> uncovered endpoint (create) wired.
>
> **Planning-time as-recommended streak reached 6** (was 5 at
> M26.1 close; +1 at M27.0 with target A2 locked as recommended
> after four alternatives presented under two framings, §7
> substrate-attachment scope adjustment applied without shifting
> target). Historical run of 89 across M10 → M23 preserved for
> the record. M27.1 + M27.2 both pure implementation increments
> executing the M27.0 locked plan — streak unchanged.
>
> **Coordinated push at M27 close pending.** All M27 work is
> local-only; awaits explicit user confirmation before push.
> Expected M27 commits at push: 6 (M27.0 planning + hash
> backfill + M27.1 substrate + hash backfill + M27.2 close +
> hash backfill), or 8 if M27.3 splits (evidence-sized fold
> held, so 6 is the expected count).
>
> **Five durable design principles surfaced or reinforced at
> M27** (see `MILESTONE_27_RETROSPECTIVE.md` §5):
> (a) *verify FK / identifier discoverability at planning-open*
> — NEW at M27.0, saved to
> `memory/feedback_verify_fk_discoverability_before_lock.md`;
> governs all future create/edit workflow scoping;
> (b) *substrate-attachment beats parallel-surface for adjacent
> workflows* — reinforced by user direction at M27.0 §7;
> (c) *shared-infrastructure framing over one-off substrate* —
> reinforced by user direction to record `gl-accounts` as
> shared accounting infrastructure for future workflows;
> (d) *DoD exception path applies cleanly to infrastructure-only
> sub-increments* — second post-M21.0 invocation (M26 was the
> first);
> (e) *test-driven UI viewport constraints* — NEW at M27.2;
> Playwright's 1280×720 viewport surfaces dialog-overflow bugs
> that manual testing on larger monitors misses.
>
> **Four NEW M28+ candidates surfaced or elevated during M27**:
> (a) **NEW recurring journal templates** — would reuse M27.1
> gl-accounts substrate + M27.2 dialog pattern; direct operator
> gain;
> (b) **O2 row-5 public-fetch-helper regex refinement** (M26
> deferral, unchanged);
> (c) **O3 rows-1–4 plain-string-literal investigation** (M26
> deferral, unchanged);
> (d) **H test-hygiene remediation** — 3 shared-DB non-idempotent
> journeys confirmed at M27.2 full-suite run
> (`sales_manager/daily_startup`, `recon/workflow`,
> `office/accounting_workflow`).
>
> **SESSION_194 opens M28.0 — planning refinement + target
> selection.** No target locked yet — the candidate list
> surfaces at open (elevated: NEW recurring journal templates,
> O2, O3, H; gated: T / U / L / M; deferred pending evidence:
> D / C; deferred stable: G; plus all M27 §3 deferrals + all
> M25 §4 deferrals still valid). The assistant recommends one
> option with rationale grounded in the durable primary
> operational-coverage lens (or a reframe if evidence supports
> it); the user confirms or redirects.

## First thing SESSION_194 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches `origin/main`
  post-M27 push (if pushed) OR local `HEAD` ahead by 6 commits
  (M27.0 planning + hash backfill + M27.1 substrate + hash
  backfill + M27.2 close + hash backfill) if push not yet
  executed.
- `git log --oneline -10` — top should be the M27.2
  hash-backfill commit; six M27 commits total.
- `python3 manage.py test dealer_ai` → **4,813 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **246 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. If M27 pushed — monitor first M27 CI run

If M27 has been pushed, verify the CI acceptance workflow
status via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as §0.a M28.0 amendments before opening
§5.a.

**If green:** M27 is CI-verified shipped; proceed to §3.

### 3. Regenerate the audit artifact

Before candidate presentation, rerun the audit tooling to
confirm the M27.2 baseline holds:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Expected: **155 total / 121 covered / 34 backend-only /
312 service verbs**. If the artifact drifts from this,
investigate before scope-locking.

### 4. Present the M28 candidate list

Per the M27 retrospective §9 evidence:

**Elevated (highest recommendation strength at M28.0):**

- **NEW recurring journal templates.** Would reuse M27.1
  gl-accounts substrate + M27.2 dialog pattern. Direct
  operator gain for accounting staff (post recurring
  entries like monthly rent without re-entering line
  items). Distinct scope; small-to-moderate. First
  candidate to demonstrate M27.1 substrate compound value.
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (M26 deferral). Extend `_HELPER_CALL_RE` to include
  public helpers (`getJSON` / `postJSON` / etc.), OR
  broaden `_PUBLIC_FETCH_RE` filters. Blast radius
  unknown pre-tracing; requires SESSION-189-§3-style
  tracing at M28.0 open.
- **NEW O3 — Rows 1–4 plain-string-literal investigation**
  (M26 deferral). Likely `component_consumed`
  word-boundary check defect. Requires tracing at
  M28.0 open.
- **H — test-hygiene remediation.** 3 shared-DB
  non-idempotent journeys (`sales_manager/daily_startup`,
  `recon/workflow`, `office/accounting_workflow`)
  confirmed at M27.2 full-suite run. High compound value
  as suite grows. Not operator-facing directly.

**Gated (unchanged from M27 close):**

- **T** — process real tester feedback.
- **U** — hosted-demo substrate.
- **L** — first-live-pilot staging.
- **M** — multi-operator support (breaks zero-drift
  streak with intent).

**Deferred pending evidence (unchanged):**

- **D** — LLM router / cost caps.
- **C** — F&I chargeback substrate (would reuse M27.1
  gl-accounts substrate).

**Deferred but stable:**

- **G** — dashboard testid hardening.

**Deferred at M27 §3 (all valid for later re-entry):**

Standalone Chart of Accounts page/route; Trial Balance
changes; JE edit/update; `posted_by_user` override in JE
dialog; advanced picker filtering; server-side gl-accounts
search / pagination; `?include_inactive=true` query param.

**Deferred at M25 §4 (all remain valid for later re-entry):**

Secondary "+ Record test drive" launch point on
`DealerAiSalesTestDrives`; clickable "Referred by"
attribution navigation; named-platform webhook adapters
(Autotrader / Cars.com / etc.) — JSONField substrate
ready; attribution analytics / rollups; vehicle picker
advanced filters.

Present each with two-sentence scope + operator pain
resolved + dependency notes, then present the
recommendation.

### 5. Recommend a target for §5.a

Ground the recommendation in the **primary operational-
coverage lens** ("which candidate most increases
operational coverage for a dealership employee?") OR its
reframe (planning-substrate integrity, per M26 precedent)
if evidence supports it.

Elevated candidates evaluated under the primary lens:

- **NEW recurring journal templates** — direct operator-
  facing; small-to-moderate scope; demonstrates M27.1
  substrate compound value. Would need FK-discoverability
  verification at §7 (accounts + line-count-per-template
  identifier surfaces).
- **NEW O2 audit refinement** — indirect (planning-substrate
  accuracy). Very small scope. Wins on compound-infrastructure
  grounds ONLY if row-5 defect is causing active
  mis-selection at M28+.
- **NEW O3 audit refinement** — indirect; scope unknown
  pre-tracing.
- **H (test-hygiene)** — indirect (CI stability); high
  compound value as suite grows; 3-journey population is
  bounded.

**Judgment call for M28:** at M27 close, M27.1 shipped
shared accounting infrastructure with explicit "compound
value" framing. Recurring templates is the first
operator-facing candidate that would demonstrate that
compound value on top of the substrate — an intentionally
short M28 that validates the substrate framing. Alternatively,
audit-refinement work (O2 + O3) could be spent together
per M26 precedent, or H could clear the shared-DB
non-idempotency debt before the acceptance suite grows
further.

**Alternatively:** if the M27 CI run surfaces regression
work at M28.0, address as §0.a amendments first.

### 6. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the standard six-to-eight
load-bearing decisions.

### 7. Verify BOTH intake AND downstream UI surfaces + FK discoverability before locking §5.b + §5.d

**M24.1-open + M25.0 + M25.2-open + SESSION_189 §3 +
SESSION_190 §2 + M27.0 §7 durable lesson reinforced
across M24 through M27.** Every planning-open surface
verification must cover both intake AND downstream paths,
including audit-substrate accuracy checks when audit is
load-bearing on the selection, and **verify FK / identifier
discoverability for any create/edit workflow candidate**
(M27.0 origin — saved to memory as
`feedback_verify_fk_discoverability_before_lock.md`).

### 8. DoD compliance check

Per the M21.0 §5.f amendment: the M28 active memo §3
must either name a Playwright journey addition or
extension OR explicitly document why no journey change
is required (M26 + M27.1 precedent for the exception
path).

### 9. Expand M28 planning skeleton

Draft fresh per the standard active-memo shape (no
existing skeleton at close of M27).

### 10. Ship the M28.0 handoff

- `docs/handoffs/SESSION_194_m28_inc0_planning.md`.
- **Do NOT push** — M28.0 is planning only; coordinated
  push at M28 close.

## Non-goals for SESSION_194

- ❌ Do NOT ship any backend or frontend code — planning-
  only session.
- ❌ Do NOT open any M28 implementation increment.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M27 shipped surface.
- ❌ Do NOT modify the acceptance suite unless CI
  regression fixes land as §0.a M28.0 amendments.
- ❌ Do NOT skip the DoD compliance check.
- ❌ Do NOT skip the downstream / substrate / FK-
  discoverability verification (M24–M27 durable lessons).

## Baseline expected at close

Backend + frontend unchanged from M27 close. Acceptance
suite unchanged. Only planning docs change.

## NEXT TASK

Start SESSION_194 with (a) starting-state verification,
(b) if M27 pushed, monitor first M27 CI run + fix any
regressions as §0.a M28.0 amendments, (c) regenerate the
audit artifact and confirm 121/155 holds, (d) present
the candidate list with recommendation + rationale
under the primary operational-coverage lens (or
substrate-integrity or substrate-compound-value reframe
if evidence supports it), (e) await user confirmation
of §5.a, (f) draft §5.b–§5.h, (g) DoD compliance check
on §3 draft, (h) expand the M28 planning memo, (i) ship
the M28.0 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M27 shipped section landed at M27.2)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_27_RETROSPECTIVE.md`
   §3 (deviations) + §5 (durable lessons) + §9
   (standing M28 question)
6. `docs/roadmap/MILESTONE_27_PLANNING.md`
   (M27 governing contract + all §5 locks + M27.0
   §7 substrate-attachment discovery record)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (post-M27 baseline — 155 endpoints /
   **121 covered** / 34 backend-only)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25 shipped surface)
   + §7α (M26 audit-tooling refinement) + §7β (M27
   shipped surface)
9. `docs/handoffs/SESSION_193_m27_close.md`
   (M27.2 shipped + M27.3 close-out fold)
10. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_193 — Milestone 27 SHIPPED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0049`. Test baseline: **4,813
  pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 246 pass** across 34 test
  files.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49
  + TS 5.6 operational; **16 journeys** passing
  end-to-end on clean DB. Full dry-run baseline:
  **22 passed (~30s)** (6 setup + 16 journeys).
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. First real
  M27 CI run pending on the M27 push (executes at
  M27 close after explicit user confirmation).
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler.
  10 scheduled task families registered.
- **Milestones shipped:** M1 → **M27**. M28
  target selection pending (SESSION_194).
- **DRF admin surface:** **115** endpoints (was 114
  at M26 close; +1 for M27.1 `gl-accounts`).
- **Frontend operator routes:** 20 (unchanged — M27.2
  attached to existing JE list route).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** all M1–M27 packages
  unchanged. Zero new M27 service verbs (the M27.1
  view uses ORM directly, not a service helper).
- **Frontend surfaces:** two new components at M27.2
  (`GLAccountPicker`, `NewJournalEntryDialog`);
  `AccountingJournalEntriesPage` extended in place.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** —
  zero-drift streak **twenty-seven consecutive
  milestones** (M10 → M27).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 27 status:** SHIPPED (SESSION_193
  close-out landed all documentation + status
  flips + M28 handoff + coordinated close-out
  session-local commits, awaits explicit user
  push confirmation).
- **Audit tooling status:** unchanged from M26.1
  (parser fix + regression suite + shared
  substrate). Coverage 121 / 155 (was 119 / 154
  at M26 close; +2 covered rows at M27.2 +1
  total row at M27.1).
- **§9 evidence for M28:** NEW recurring journal
  templates (elevated — would demonstrate M27.1
  substrate compound value); NEW O2 (row-5
  public-fetch-helper); NEW O3 (rows-1–4
  plain-string); H (test-hygiene — confirmed 3
  failing journeys at M27.2 full-suite run); plus
  gated T/U/L/M, deferred D/C, deferred stable G,
  plus M27 §3 deferrals (standalone CoA
  page/route, JE edit/update, advanced picker
  filtering, server-side gl-accounts pagination,
  etc.), plus all M25 §4 deferrals.
- **Planning-time streak: 6** (at M27.2 close;
  unchanged from M27.0 as-recommended; M27.1 +
  M27.2 both pure implementation; historical run
  of 89 across M10 → M23 preserved for the record).
- **DoD amendment (M21.0 §5.f Option B):** every
  future customer-facing milestone must add or
  update at least one Playwright operational
  journey, or explicitly document in §3 why no
  journey change is required. M26 invoked the
  exception path (audit-tooling infrastructure);
  M27.1 was the second invocation
  (infrastructure-only backend + wrapper); M27.2
  satisfied DoD directly via
  `accounting_je_create.spec.ts` extension.
- **M27 audit coverage at close:** 155 endpoints,
  **121 covered / 34 backend-only** (was 119 / 35
  at M26 close; §5.e two-source agreement
  confirmed both increments' coverage numbers).
- **Durable lessons carried into M28+:** (a) one
  operational workflow beats two overlapping
  (M25.0); (b) planning-open verification must
  cover persistence path (M25.0 §5.b + M25.2
  §5.e); (c) additive-forever JSONField beats
  CharField (M25.0 §5.b); (d) record empirical-
  discovery refinements honestly (M25.0 + M25.2
  + SESSION_189 §3 + SESSION_190 §2; four
  reinforcements across M24–M26); (e) modal-
  attached collapsible + success badge > toast
  (M25.2 — reinforced at M27.2 JE-create); (f)
  dependency-injectable helpers over network
  mocks in unit tests (M25.2); (g) audit
  correctness is supporting infrastructure —
  every accuracy gain compounds (M25.3 → M26);
  (h) two-source agreement is the mechanical
  guard against baseline drift (M26.1;
  reinforced at both M27.1 + M27.2 §5.e checks);
  (i) DoD exception path applies cleanly to
  infrastructure-focused milestones (M26 + M27.1
  — second invocation); (j) **verify FK /
  identifier discoverability at planning-open
  for any create/edit workflow** (M27.0 origin —
  saved to
  `memory/feedback_verify_fk_discoverability_before_lock.md`);
  (k) **substrate-attachment beats parallel-
  surface for adjacent workflows** (M27.0 §7
  reinforcement); (l) **shared-infrastructure
  framing over one-off substrate** (M27.1
  reinforcement); (m) **NEW at M27.2** — modal
  dialogs with >3 sections need
  `max-h-[90vh] flex-col` + scrollable inner
  body from the start (test-driven UI viewport
  constraint; Playwright's 1280×720 default
  surfaces overflow bugs manual testing misses).
