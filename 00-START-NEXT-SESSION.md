---
state: active
date: 2026-08-03
last_session_shipped: SESSION_194
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
milestone_28_status: active
next_session: SESSION_195
next_milestone: 28
next_milestone_name: "Recurring Journal Templates (on M27.1 shared GLAccount substrate)"
next_increment: 1
next_increment_name: "M28.1 — Backend substrate + frontend wrappers"
---

# Next session — SESSION_195 · Milestone 28 · Increment 1 (M28.1 — backend substrate + frontend wrappers)

> **Milestone 28 opened at SESSION_194 (M28.0).**
> Target: **A — NEW recurring journal templates** (locked
> under the primary operational-coverage lens). Full active
> memo at `docs/roadmap/MILESTONE_28_PLANNING.md`.
> Two-increment split (M28.1 substrate + M28.2 UI) with
> close-out fold per §5.h Option B (folded unless
> evidence forces a split).
>
> **M28.0 shipped:** planning refinement + target selection
> + all §5 locks + two user-requested architectural
> verifications (variable-amount forward-compat + model
> duplication analysis) + one durable engineering-practices
> refinement (evidence-first duplication over
> DRY-for-its-own-sake — saved to memory as
> `feedback_duplicate_small_stable_logic.md`) + §7 FK-
> discoverability verification + §3 DoD compliance check.
> Backend + frontend + acceptance unchanged (planning only).
>
> **Planning-time as-recommended streak reached 7** (was 6
> at M27.0 close; +1 at M28.0 with target A locked as
> recommended after four alternatives presented, two
> architectural verifications performed, and one durable
> refinement adopted from user pushback on helper
> extraction). Historical run of 89 across M10 → M23
> preserved for the record.
>
> **Zero-drift permission-class streak unchanged at 27**
> consecutive milestones (M10 → M27). M28.0 is planning
> only; no permission-class touches. M28.1 + M28.2 both
> reuse `_M131_PERMS` per §5.b — intended posture at M28
> close: **28 consecutive milestones (M10 → M28)**.
>
> **Two architectural verifications documented in M28
> memo opening block + §5.b commentary:**
> (a) **Variable-amount forward-compat** — `side`
> (CharField choices) + nullable `amount` on
> `JournalEntryTemplateLine` supports all four future
> workflows (monthly rent fixed; depreciation, utilities,
> payroll accruals variable) without a DB migration. Dual-
> column `debit`/`credit` mirroring was rejected because
> it cannot express "side known, amount deferred" without
> adding a side column. `amount IS NULL` posture is
> intentional forward-compat; M28 serializer requires
> non-null.
> (b) **Model duplication analysis** —
> `JournalEntryTemplateLine` does not mirror
> `JournalEntryLine`. Fusion (via inheritance, mixin, or
> `is_template` flag) was rejected: destroys M13.1
> immutability + `posted_at` + reversal invariants and
> forces `WHERE is_template = FALSE` filters on every
> posting query. Templates are recipes; JEs are postings.
> Normalization is correct; sharing would be premature
> coupling. Cross-tenant guard extraction was also
> rejected on evidence-first grounds — see the durable
> refinement below.
>
> **Durable refinement adopted at M28.0** (new engineering-
> practices rule, saved to memory):
> *Duplicate small stable domain logic; extract only on
> evidence.* Short (~5-line), stable, domain-local logic
> stays local to its owning model. Extraction is
> evidence-gated (divergence has happened; ~20+-line
> copies; a third similarly-shaped consumer; measurable
> maintenance burden) — DRY-for-its-own-sake is not
> evidence. Applies broadly across future refactor
> scoping; documented in M28 memo §0 engineering-
> practices, §5.b commentary, and §8 streak-accounting
> note.
>
> **DoD posture:** M28.1 invokes the M21.0 §5.f exception
> path (third invocation — pattern established for
> infrastructure-only sub-increments after M26 audit-
> tooling and M27.1 gl-accounts). M28.2 satisfies DoD
> directly via new `accounting_je_template.spec.ts` (2
> cases: create-template + instantiate-template) + one-
> case extension to `accounting_je_create.spec.ts`
> (blank-path regression guard).
>
> **Coverage arithmetic at M28 close:** backend endpoints
> **155 → 157** (two new template endpoints; POST + GET on
> the same URL count as two audit rows). Both new rows
> land `defer-candidate-O2` at M28.1 close; both flip
> `covered` at M28.2 close. Post-M28.2 target: **157
> total / 123 covered / 34 backend-only** (121 → 123).
>
> **Coordinated push at M28 close pending.** All M28
> work will be local-only through M28.1; awaits explicit
> user confirmation at M28.2 close. Expected M28 commits
> at push: 6 (folded) or 8 (split).

## First thing SESSION_195 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches
  `origin/main` post-M28.0 push (if pushed) OR local
  `HEAD` ahead by 2 commits (M28.0 planning + hash
  backfill) if push not yet executed. **Note:** M28.0
  is planning-only; per §5.h Option B the coordinated
  push happens at M28 close, not per-increment.
- `git log --oneline -10` — top should be the M28.0
  hash-backfill commit (or the M27.2 hash-backfill
  commit `172de87` if M28.0 not yet committed).
- `python3 manage.py test dealer_ai` → **4,813 pass,
  1 skipped, 0 fail**.
- `cd frontend && npm test` → **246 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run`
  → "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. Regenerate the audit artifact

Confirm the M27.2 baseline holds:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Expected: **155 total / 121 covered / 34 backend-only /
312 service verbs**. If it drifts, investigate before
opening implementation.

### 3. Follow the M28.1 §7 sequencing steps exactly

Per `docs/roadmap/MILESTONE_28_PLANNING.md` §7 M28.1:

1. Add `JournalEntryTemplate` +
   `JournalEntryTemplateLine` models in `models.py`.
   **Do not modify** `JournalEntryLine`. Duplicate the
   cross-tenant guard inline on the new model per the
   evidence-first duplication decision.
2. Run `makemigrations` — verify auto-detected
   `0050_m281_je_template.py`.
3. Add service verbs (`create_journal_entry_template`,
   `list_journal_entry_templates`,
   `get_journal_entry_template`) + `TemplateLineInput`
   dataclass + four new domain errors in
   `services/accounting.py`.
4. Add serializers + view function + URL route in
   `views_accounting.py` + `urls.py`.
5. Write `test_m28_journal_entry_template_model.py`,
   `test_m28_journal_entry_template_service.py`,
   `test_m28_journal_entry_template_endpoint.py`.
6. Backend suite → assert green (4,813 → ≥4,830).
7. Add `fetchJournalEntryTemplates` +
   `createJournalEntryTemplate` wrappers + types in
   `accountingApi.ts`.
8. Write `accountingApi.templates.test.ts` vitest.
9. Frontend suite → assert green (246 → ~249).
10. Regenerate audit; assert exactly **155 → 157**
    with two new rows at `defer-candidate-O2`.
11. §5.e Phase 2 per-row verification for the new
    rows.
12. Update `docs/CAPABILITY_MATRIX.md` §7γ (M28.1
    partial shipped surface).
13. Draft M28.1 handoff at
    `docs/handoffs/SESSION_195_m28_inc1_substrate.md`.
14. **Do NOT push.** M28.1 is substrate-only;
    coordinated push at M28 close per §5.h.

### 4. Do not exceed M28.1 scope

- No frontend UI (M28.2 scope).
- No modification to shipped `JournalEntryLine`.
- No cross-tenant guard helper extraction (evidence-
  first decision per §5.b).
- No variable-amount serializer support (schema-
  reserved only).
- No template edit / update / delete endpoints.
- No back-reference on `JournalEntry`.
- No server-side search / pagination.
- No `?include_inactive=true` exposure.

## Non-goals for SESSION_195

- ❌ Do NOT ship any frontend UI (M28.2 scope).
- ❌ Do NOT modify M1–M27 shipped surface (including
  `JournalEntryLine`).
- ❌ Do NOT extract the cross-tenant guard as a
  shared helper (evidence-first duplication decision).
- ❌ Do NOT ship variable-amount templates.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT push at M28.1 close.
- ❌ Do NOT skip the two-source agreement check at
  audit regeneration.
- ❌ Do NOT skip the M28.1 open baseline
  verification.
- ❌ Do NOT introduce new permission classes (both
  new endpoints reuse `_M131_PERMS`).

## Baseline expected at close

- **Backend:** 4,813 → **≥4,830 pass** (M28.1 adds
  ~20–25 model + service + endpoint tests).
- **Frontend Vitest:** 246 → **~249 pass** (M28.1
  adds ~3 wrapper tests only; UI at M28.2).
- **Acceptance:** 16 journeys (unchanged at M28.1;
  extended to 19 at M28.2).
- **Audit:** **157 total / 121 covered / 36
  backend-only** (was 155 / 121 / 34 at M27 close;
  denominator +2 for the new template endpoints; both
  new rows disposition `defer-candidate-O2` at M28.1
  close, flip `covered` at M28.2 close).
- **Migrations:** 0049 → 0050 (`0050_m281_je_template.py`).
- **Frontend operator routes:** unchanged at 20.
- **DRF admin surface:** 115 → 117 (+2 template
  endpoints).
- **Permission classes:** unchanged (7 actual;
  streak intact).

## NEXT TASK

Start SESSION_195 with (a) starting-state
verification, (b) audit regeneration to confirm 121 /
155 holds, (c) execute M28.1 §7 steps 1–14 in order,
(d) DoD exception path documentation in the M28.1
retrospective §journey-plan section, (e) ship the
M28.1 handoff (no push). Full memo governs at
`docs/roadmap/MILESTONE_28_PLANNING.md`.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M27 shipped section landed at M27.2)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_28_PLANNING.md`
   (M28 governing contract + all §5 locks + M28.0
   architectural verifications + evidence-first
   duplication decision)
6. `docs/roadmap/MILESTONE_27_RETROSPECTIVE.md`
   §3 (deviations) + §5 (durable lessons) + §9
   (M28 candidate evidence)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (pre-M28 baseline — 155 endpoints / **121
   covered** / 34 backend-only)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25 shipped
   surface) + §7α (M26 audit refinement) + §7β
   (M27 shipped surface)
9. `docs/handoffs/SESSION_194_m28_inc0_planning.md`
   (M28.0 shipped)
10. Memory record
    `feedback_duplicate_small_stable_logic.md`
    (NEW at M28.0)
11. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified at M28.0 §7)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_194 — Milestone 28 M28.0 SHIPPED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0049`. Test baseline: **4,813
  pass**, 1 skipped, 0 fail (unchanged at M28.0).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 246 pass** across 34 test
  files (unchanged at M28.0).
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49
  + TS 5.6 operational; **16 journeys** passing
  end-to-end on clean DB.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. M27 CI-
  verified green (2m22s @ `172de87`).
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler.
  10 scheduled task families registered.
- **Milestones shipped:** M1 → **M27**. **M28 opened
  at M28.0 (SESSION_194)**; M28.1 substrate opens at
  SESSION_195.
- **DRF admin surface:** **115** endpoints
  (unchanged at M28.0; +2 at M28.1 for template
  create + list).
- **Frontend operator routes:** 20 (unchanged;
  M28.2 attaches to existing JE list route).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** all M1–M27 packages
  unchanged. M28.1 adds three new service verbs +
  one dataclass + four domain errors to
  `services/accounting.py`.
- **Frontend surfaces:** M28.0 shipped no frontend.
  M28.2 will add one new component
  (`NewJournalEntryTemplateDialog`), one section
  extension on `AccountingJournalEntriesPage`, and
  one additive prop on `NewJournalEntryDialog`.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift
  streak **twenty-seven consecutive milestones
  (M10 → M27)**. M28 preserves the streak (both
  new endpoints reuse `_M131_PERMS`).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 28 status:** **M28.0 SHIPPED**
  (planning + all §5 locks + two architectural
  verifications + evidence-first duplication
  refinement + M28.1 handoff + this
  `00-START-NEXT-SESSION.md` overwrite). M28.1
  substrate opens at SESSION_195.
- **Audit tooling status:** unchanged from M26.1.
  Coverage 121 / 155 (post-M27.2 baseline; M28.1
  will land 121 / 157 with two new rows at
  `defer-candidate-O2`; M28.2 will flip to 123 /
  157).
- **§9 evidence for M29:** deferred — surfaced at
  M28 close after evidence gathered.
- **Planning-time streak: 7** (at M28.0 close;
  M28.0 locked as-recommended after user
  confirmation + two verifications + one durable
  refinement adopted from pushback on helper
  extraction). Historical run of 89 across M10 →
  M23 preserved for the record.
- **DoD amendment (M21.0 §5.f Option B):** every
  future customer-facing milestone must add or
  update at least one Playwright operational
  journey, or explicitly document in §3 why no
  journey change is required. M26 invoked the
  exception path (audit-tooling infrastructure);
  M27.1 was the second invocation; **M28.1 is the
  third invocation** (backend substrate + wrappers,
  no operator surface). M28.2 satisfies DoD
  directly via the new template spec + JE-create
  extension.
- **M28.0 planning artifacts:** memo at
  `docs/roadmap/MILESTONE_28_PLANNING.md`;
  handoff at
  `docs/handoffs/SESSION_194_m28_inc0_planning.md`;
  new memory record at
  `memory/feedback_duplicate_small_stable_logic.md`.
- **Durable lessons carried into M28+ increments:**
  (a) one operational workflow beats two overlapping
  (M25.0); (b) planning-open verification must cover
  persistence path (M25.0 §5.b + M25.2 §5.e);
  (c) additive-forever JSONField beats CharField
  (M25.0 §5.b); (d) record empirical-discovery
  refinements honestly (M25.0 + M25.2 + SESSION_189
  §3 + SESSION_190 §2); (e) modal-attached
  collapsible + success badge > toast (M25.2 —
  reinforced at M27.2 JE-create); (f) dependency-
  injectable helpers over network mocks in unit
  tests (M25.2); (g) audit correctness is
  supporting infrastructure (M25.3 → M26); (h)
  two-source agreement is the mechanical guard
  against baseline drift (M26.1; reinforced at
  M27.1 + M27.2 + M28 §5.e checks); (i) DoD
  exception path applies cleanly to
  infrastructure-only sub-increments (M26 + M27.1
  + M28.1 — third invocation); (j) verify FK /
  identifier discoverability at planning-open for
  any create/edit workflow (M27.0 origin);
  (k) substrate-attachment beats parallel-surface
  for adjacent workflows (M27.0 §7); (l) shared-
  infrastructure framing over one-off substrate
  (M27.1); (m) modal dialogs with >3 sections
  need `max-h-[90vh] flex-col` + scrollable inner
  body from the start (M27.2 — reused at M28.2
  template dialog); (n) **NEW at M28.0** — recipes
  vs postings are different domain concepts;
  fusing them via inheritance / flags destroys
  separation of concerns and forces defensive
  filters on every posting-query consumer;
  (o) **NEW at M28.0** — variable-amount forward-
  compat via `side` + nullable `amount` separation
  (documented as intentional forward-compat, not
  accidental permissiveness); (p) **NEW at M28.0**
  — duplicate small stable domain logic; extract
  only on evidence (short, stable, domain-local
  logic stays local; extraction is evidence-gated,
  not DRY-driven).
