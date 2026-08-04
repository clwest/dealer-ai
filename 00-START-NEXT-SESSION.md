---
state: active
date: 2026-08-03
last_session_shipped: SESSION_196
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
milestone_28_status: shipped
next_session: SESSION_197
next_milestone: 29
next_milestone_name: "(target selection pending — locked at M29.0 open)"
next_increment: 0
next_increment_name: "M29.0 — Planning refinement + target selection"
---

# Next session — SESSION_197 · Milestone 29 · Increment 0 (M29.0 — planning refinement + target selection)

> **Milestone 28 — Recurring Journal Templates (on M27.1
> shared GLAccount substrate) — SHIPPED at SESSION_196.**
> Three-session milestone (SESSION_194 → SESSION_195 →
> SESSION_196). M28.3 close-out folded into M28.2 per §5.h
> Option B — both increments' §5.e Phase 1 + Phase 2 checks
> passed cleanly on the first regeneration. **Backend
> baseline 4,813 → 4,855 (+42 across three M28 test files
> at M28.1); unchanged at M28.2. Frontend Vitest 246 → 270
> pass (+24 across accountingApi.templates.test.ts +
> NewJournalEntryTemplateDialog + NewJournalEntryDialog
> extensions + AccountingJournalEntriesPage extensions).
> Acceptance 16 → 19 journeys (+3 across
> `accounting_je_template.spec.ts` + blank-path extension in
> `accounting_je_create.spec.ts`).** Full acceptance run: 22
> passed / 3 pre-existing shared-DB failures unchanged from
> M27.2 (Candidate H remediation, not M28 scope). Audit
> coverage **121 / 155 → 122 / 156** (row 150
> `admin/accounting/journal-entry-templates/` shipped +
> flipped `covered` at M28.2).
>
> **Zero-drift permission-class streak extends 27 → 28**
> consecutive milestones (M10 → M28). Both new M28 endpoints
> (GET + POST via `@api_view(["GET","POST"])`) reuse
> `_M131_PERMS`; zero permission classes evolved.
>
> **Planning-time as-recommended streak reached 7** (was 6
> at M27.2 close; +1 at M28.0 with target A locked as
> recommended after four alternatives presented + two
> architectural verifications performed + one durable
> engineering-practices refinement adopted from user
> pushback on helper extraction). Historical run of 89
> across M10 → M23 preserved for the record. M28.1 + M28.2
> both pure implementation increments executing the M28.0
> locked plan — streak unchanged.
>
> **Coordinated push at M28 close pending.** All M28 work
> is local-only; awaits explicit user confirmation before
> push. Expected M28 commits at push: 6 (M28.0 planning +
> hash backfill + M28.1 substrate + hash backfill + M28.2
> close + hash backfill).
>
> **Seven durable design principles surfaced or reinforced
> at M28** (see `MILESTONE_28_RETROSPECTIVE.md` §5):
> (a) *duplicate small stable domain logic; extract only on
> evidence* — NEW at M28.0, saved to memory as
> `feedback_duplicate_small_stable_logic.md`; governs all
> future refactor scoping;
> (b) *variable-amount forward-compat via `side` + nullable
> `amount` separation* — new architectural pattern;
> documented in model docstring;
> (c) *recipes vs postings are different domain concepts* —
> fusion destroys separation of concerns and forces defensive
> filters on every posting-query consumer;
> (d) *verify FK / identifier discoverability at planning-
> open* — REINFORCED (M27.0 origin);
> (e) *DoD exception path for infrastructure-only sub-
> increments* — third invocation (M26 + M27.1 + M28.1),
> pattern established;
> (f) *combined GET+POST endpoints count as ONE audit row,
> not two* — NEW at M28.1; refines memo-prediction pattern
> for `@api_view(["GET","POST"])`;
> (g) *Playwright APIRequestContext does NOT auto-populate
> `X-CSRFToken` from storage-state csrftoken cookie* — NEW
> at M28.2; `postWithCsrf` helper available for future specs.
>
> **Five NEW M29+ candidates surfaced or elevated during
> M28**:
> (a) **NEW variable-amount templates** — would relax M28.1
> serializer's non-null `amount` + add instantiation-prompt
> UI; zero DB migration (schema reserved at M28.1); direct
> operator gain for depreciation / utilities / payroll
> accruals; recorded as intended payoff of M28 §5.b forward-
> compat design;
> (b) **NEW template edit / delete UI** — currently
> `is_active` at DB layer with no operator surface;
> (c) **O2 row-5 public-fetch-helper regex refinement**
> (M26/M27/M28 deferral, unchanged);
> (d) **O3 rows-1–4 plain-string-literal investigation**
> (M26/M27/M28 deferral, unchanged);
> (e) **H test-hygiene remediation** — same 3 shared-DB
> non-idempotent journeys unchanged from M27.2 confirmed at
> M28.2 full-suite run.
>
> **SESSION_197 opens M29.0 — planning refinement + target
> selection.** No target locked yet — the candidate list
> surfaces at open (elevated: NEW variable-amount templates,
> NEW template edit/delete UI, O2, O3, H; gated: T / U / L /
> M; deferred pending evidence: D / C; deferred stable: G;
> plus all M28 §3 deferrals + all M27 §3 deferrals + all
> M25 §4 deferrals still valid). The assistant recommends
> one option with rationale grounded in the durable primary
> operational-coverage lens (or a reframe if evidence
> supports it); the user confirms or redirects.

## First thing SESSION_197 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches
  `origin/main` post-M28 push (if pushed) OR local `HEAD`
  ahead by 6 commits (M28.0 planning + hash backfill + M28.1
  substrate + hash backfill + M28.2 close + hash backfill)
  if push not yet executed.
- `git log --oneline -10` — top should be the M28.2 hash-
  backfill commit; six M28 commits total.
- `python3 manage.py test dealer_ai` → **4,855 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **270 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. If M28 pushed — monitor first M28 CI run

If M28 has been pushed, verify the CI acceptance workflow
status via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as §0.a M29.0 amendments before opening
§5.a.

**If green:** M28 is CI-verified shipped; proceed to §3.

### 3. Regenerate the audit artifact

Before candidate presentation, rerun the audit tooling to
confirm the M28.2 baseline holds:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Expected: **156 total / 122 covered / 34 backend-only /
315 service verbs**. If the artifact drifts from this,
investigate before scope-locking.

### 4. Present the M29 candidate list

Per the M28 retrospective §9 evidence:

**Elevated (highest recommendation strength at M29.0):**

- **NEW variable-amount templates.** Relax M28.1 serializer's
  non-null `amount` constraint + add instantiation-prompt UI
  when instantiating a template with NULL-amount lines. Zero
  DB migration (schema reserved at M28.1 exactly for this
  case). Direct operator gain for accounting staff posting
  depreciation, utilities, payroll accruals. Recorded as
  intended payoff of M28 §5.b forward-compat design.
  Substrate-compound-value framing continuation of M27.1 +
  M28.1.
- **NEW template edit / delete UI.** Currently `is_active`
  exists at DB layer with no operator surface. If operator
  evidence supports mid-year chart-of-accounts edits or
  template deactivation, promote. Small-to-moderate scope.
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (M26/M27/M28 deferral). Requires SESSION-189-§3-style
  tracing at M29.0 open. Blast radius unknown.
- **NEW O3 — Rows-1–4 plain-string-literal investigation**
  (M26/M27/M28 deferral). Requires tracing at M29.0 open.
- **H — Test-hygiene remediation.** 3 shared-DB
  non-idempotent journeys confirmed at M28.2 full-suite
  run (unchanged from M27.2 close). Compound CI-stability
  value grows as suite grows.

**Gated (unchanged from M28 close):**

- **T** — process real tester feedback.
- **U** — hosted-demo substrate.
- **L** — first-live-pilot staging.
- **M** — multi-operator support (breaks zero-drift streak
  with intent).

**Deferred pending evidence (unchanged):**

- **D** — LLM router / cost caps.
- **C** — F&I chargeback substrate (would reuse M27.1
  gl-accounts substrate).

**Deferred but stable:**

- **G** — dashboard testid hardening.

**Deferred at M28 §3 (all valid for later re-entry):**

Named template variables (multi-line shared input);
historical-template back-reference on JournalEntry;
server-side template search / pagination;
`?include_inactive=true` endpoint exposure; save-as-template
checkbox on JE dialog; standalone template detail page.

**Deferred at M27 §3 (all valid for later re-entry):**

Standalone Chart of Accounts page/route; JE edit/update;
`posted_by_user` override; advanced picker filtering;
server-side gl-accounts search / pagination;
`?include_inactive=true` on gl-accounts.

**Deferred at M25 §4 (all valid for later re-entry):**

Secondary "+ Record test drive" launch point; clickable
"Referred by" nav; named-platform webhook adapters;
attribution rollups; vehicle-picker advanced filters.

Present each with two-sentence scope + operator pain
resolved + dependency notes, then present the recommendation.

### 5. Recommend a target for §5.a

Ground the recommendation in the **primary operational-
coverage lens** ("which candidate most increases
operational coverage for a dealership employee?") OR its
reframe (planning-substrate integrity, per M26 precedent;
substrate-compound-value continuation, per M27.1 → M28
precedent) if evidence supports it.

Elevated candidates evaluated under the primary lens:

- **NEW variable-amount templates** — direct operator-facing;
  small-to-moderate scope; second consumer of M28.1 template
  substrate on top of the M27.1 gl-accounts substrate;
  compound value on compound value.
- **NEW template edit / delete UI** — direct operator-
  facing; smaller scope than variable-amount templates but
  arguably higher-frequency operational value (mid-year
  edits are more common than depreciation-style variable
  templates).
- **NEW O2 audit refinement** — indirect (planning-substrate
  accuracy). Wins on compound-infrastructure grounds ONLY if
  active mis-selection defects surface.
- **NEW O3 audit refinement** — indirect; scope unknown
  pre-tracing.
- **H (test-hygiene)** — indirect (CI stability); high
  compound value as suite grows; 3-journey population is
  bounded.

**Standing question from M28 retrospective §9:** should
the substrate-integrity audit-refinement path (O2 + O3
M26-analogous) be spent, OR the substrate-compound-value
continuation (variable-amount templates would be the next
operator-facing consumer of the M28.1 substrate)? Evidence
at M28 close does not force either path.

**Alternatively:** if the M28 CI run surfaces regression
work at M29.0, address as §0.a amendments first.

### 6. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the standard six-to-eight
load-bearing decisions.

### 7. Verify BOTH intake AND downstream UI surfaces + FK discoverability before locking §5.b + §5.d

**M24.1-open + M25.0 + M25.2-open + SESSION_189 §3 +
SESSION_190 §2 + M27.0 §7 + M28.0 §7 durable lesson
reinforced across M24 through M28.** Every planning-open
surface verification must cover both intake AND downstream
paths, including audit-substrate accuracy checks when
audit is load-bearing on the selection, and **verify FK /
identifier discoverability for any create/edit workflow
candidate**.

### 8. DoD compliance check

Per the M21.0 §5.f amendment: the M29 active memo §3
must either name a Playwright journey addition or
extension OR explicitly document why no journey change
is required (M26 + M27.1 + M28.1 precedents for the
exception path).

### 9. Expand M29 planning skeleton

Draft fresh per the standard active-memo shape (no
existing skeleton at close of M28).

### 10. Ship the M29.0 handoff

- `docs/handoffs/SESSION_197_m29_inc0_planning.md`.
- **Do NOT push** — M29.0 is planning only; coordinated
  push at M29 close.

## Non-goals for SESSION_197

- ❌ Do NOT ship any backend or frontend code — planning-
  only session.
- ❌ Do NOT open any M29 implementation increment.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M28 shipped surface.
- ❌ Do NOT modify the acceptance suite unless CI
  regression fixes land as §0.a M29.0 amendments.
- ❌ Do NOT skip the DoD compliance check.
- ❌ Do NOT skip the downstream / substrate / FK-
  discoverability verification (M24–M28 durable lessons).
- ❌ Do NOT re-litigate the M28.0 architectural
  verifications (variable-amount forward-compat + duplication
  analysis) — both were correct; carry forward as durable.

## Baseline expected at close

Backend + frontend unchanged from M28 close. Acceptance
suite unchanged. Only planning docs change.

## NEXT TASK

Start SESSION_197 with (a) starting-state verification,
(b) if M28 pushed, monitor first M28 CI run + fix any
regressions as §0.a M29.0 amendments, (c) regenerate the
audit artifact and confirm 122/156 holds, (d) present
the candidate list with recommendation + rationale
under the primary operational-coverage lens (or
substrate-integrity or substrate-compound-value reframe
if evidence supports it), (e) await user confirmation
of §5.a, (f) draft §5.b–§5.h, (g) DoD compliance check
on §3 draft, (h) expand the M29 planning memo, (i) ship
the M29.0 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M28 shipped section landed at M28.2)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_28_RETROSPECTIVE.md`
   §3 (deviations) + §5 (durable lessons) + §9
   (standing M29 question)
6. `docs/roadmap/MILESTONE_28_PLANNING.md`
   (M28 governing contract + all §5 locks + M28.0
   two architectural verifications + evidence-first
   duplication decision)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (post-M28 baseline — 156 endpoints /
   **122 covered** / 34 backend-only)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25 shipped surface)
   + §7α (M26 audit refinement) + §7β (M27 shipped
   surface) + §7γ (M28 shipped surface)
9. `docs/handoffs/SESSION_196_m28_close.md`
   (M28.2 shipped + M28.3 close-out fold)
10. Memory record
    `feedback_duplicate_small_stable_logic.md`
    (NEW at M28.0)
11. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified at M28.0 §7)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_196 — Milestone 28 SHIPPED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0050`. Test baseline: **4,855
  pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 270 pass** across 36 test files.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49
  + TS 5.6 operational; **19 journeys** total.
  Full acceptance run: 22 passed / 3 pre-existing
  shared-DB failures unchanged from M27.2 close
  (Candidate H remediation, not M28 scope).
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. First real
  M28 CI run pending on the M28 push (executes at
  M28 close after explicit user confirmation).
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler.
  10 scheduled task families registered.
- **Milestones shipped:** M1 → **M28**. M29 target
  selection pending (SESSION_197).
- **DRF admin surface:** **116** endpoints (was 115
  at M27 close; +1 for M28.1 combined-verb
  `journal-entry-templates` endpoint).
- **Frontend operator routes:** 20 (unchanged — M28.2
  attached to existing JE list route).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** all M1–M27 packages
  unchanged. M28.1 adds three new template service
  verbs + one dataclass + four domain errors to
  `services/accounting/template.py`.
- **Frontend surfaces:** M28.2 added one new
  component (`NewJournalEntryTemplateDialog`);
  extended `NewJournalEntryDialog` with additive
  props; extended `AccountingJournalEntriesPage`
  with templates section + Instantiate wiring +
  second controlled JE dialog mount.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** —
  zero-drift streak **twenty-eight consecutive
  milestones** (M10 → M28).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 28 status:** SHIPPED (SESSION_196
  close-out landed all documentation + status
  flips + M29 handoff + coordinated close-out
  session-local commits, awaits explicit user
  push confirmation).
- **Audit tooling status:** unchanged from M26.1
  (parser fix + regression suite + shared
  substrate). Coverage 122 / 156 (was 121 / 155
  at M27 close; +1 covered row at M28.2 +1
  total row at M28.1).
- **§9 evidence for M29:** NEW variable-amount
  templates (elevated — would extend M28.1
  substrate compound value); NEW template edit /
  delete UI (elevated); NEW O2 + NEW O3 (unchanged
  from M26+M27+M28); H (test-hygiene — same 3
  failing journeys unchanged from M27.2+M28.2);
  plus gated T/U/L/M, deferred D/C, deferred stable
  G, plus M28 §3 deferrals (named template
  variables, template detail page, server-side
  search/pagination, `?include_inactive=true`
  endpoint, etc.), plus M27 §3 + M25 §4 deferrals.
- **Planning-time streak: 7** (at M28.2 close;
  unchanged from M28.0 as-recommended; M28.1 +
  M28.2 both pure implementation; historical run
  of 89 across M10 → M23 preserved for the record).
- **DoD amendment (M21.0 §5.f Option B):** every
  future customer-facing milestone must add or
  update at least one Playwright operational
  journey, or explicitly document in §3 why no
  journey change is required. M26 invoked the
  exception path (audit-tooling infrastructure);
  M27.1 was the second invocation; M28.1 was the
  third invocation (template substrate + wrappers);
  M28.2 satisfied DoD directly via new
  `accounting_je_template.spec.ts` + JE-create
  extension.
- **M28 audit coverage at close:** 156 endpoints,
  **122 covered / 34 backend-only** (was 121 / 34
  at M27 close; §5.e two-source agreement
  confirmed both increments' coverage numbers).
- **Durable lessons carried into M29+:** (a) one
  operational workflow beats two overlapping
  (M25.0); (b) planning-open verification must
  cover persistence path (M25.0 §5.b + M25.2
  §5.e); (c) additive-forever JSONField beats
  CharField (M25.0 §5.b); (d) record empirical-
  discovery refinements honestly (M25.0 + M25.2
  + SESSION_189 §3 + SESSION_190 §2 + M28.1); (e)
  modal-attached collapsible + success badge >
  toast (M25.2 — reinforced at M27.2 JE-create +
  M28.2 template dialog); (f) dependency-
  injectable helpers over network mocks in unit
  tests (M25.2); (g) audit correctness is
  supporting infrastructure — every accuracy gain
  compounds (M25.3 → M26); (h) two-source
  agreement is the mechanical guard against
  baseline drift (M26.1; reinforced at M27.1 +
  M27.2 + M28.1 + M28.2 §5.e checks); (i) DoD
  exception path applies cleanly to
  infrastructure-only sub-increments (M26 +
  M27.1 + M28.1 — third invocation); (j) verify
  FK / identifier discoverability at planning-
  open for any create/edit workflow (M27.0
  origin; reinforced at M28.0); (k) substrate-
  attachment beats parallel-surface for adjacent
  workflows (M27.0 §7; reinforced at M28.2 —
  templates section attached to existing JE list
  page); (l) shared-infrastructure framing over
  one-off substrate (M27.1 origin; validated by
  M28.1 template substrate becoming the second
  operator-facing consumer of the M27.1 gl-
  accounts substrate); (m) modal dialogs with >3
  sections need `max-h-[90vh] flex-col` +
  scrollable inner body from the start (M27.2 —
  reused at M28.2 template dialog); (n) **NEW at
  M28.0** — recipes vs postings are different
  domain concepts; fusing them via inheritance /
  flags destroys separation of concerns; (o)
  **NEW at M28.0** — variable-amount forward-
  compat via `side` + nullable `amount`
  separation; (p) **NEW at M28.0** — duplicate
  small stable domain logic; extract only on
  evidence (short, stable, domain-local logic
  stays local; extraction is evidence-gated, not
  DRY-driven); (q) **NEW at M28.1** — combined
  GET+POST endpoints count as ONE audit row, not
  two (refines memo-prediction pattern for
  `@api_view(["GET","POST"])`); (r) **NEW at
  M28.2** — Playwright APIRequestContext does
  NOT auto-populate `X-CSRFToken` from storage-
  state csrftoken cookie (`postWithCsrf` helper
  pattern available for future specs); (s)
  **NEW at M28.2** — numeric input value pre-
  population may normalize trailing zeros;
  Playwright assertions on `<input type="number">`
  values should use regex when comparing to
  pre-formatted numeric strings.
