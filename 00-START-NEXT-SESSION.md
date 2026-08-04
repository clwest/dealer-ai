---
state: active
date: 2026-08-04
last_session_shipped: SESSION_202
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
milestone_29_status: shipped
milestone_30_status: shipped
next_session: SESSION_203
next_milestone: 31
next_milestone_name: "(target selection pending — locked at M31.0 open)"
next_increment: 0
next_increment_name: "M31.0 — Planning refinement + target selection"
---

# Next session — SESSION_203 · Milestone 31 · Increment 0 (M31.0 — planning refinement + target selection)

> **Milestone 30 — Template Edit / Delete UI — SHIPPED at
> SESSION_202.** M30.0 planning + §0.a M29 CI hotfix +
> M30.1 backend substrate + M30.2 frontend + Playwright +
> close-out all landed. Backend baseline 4,871 → 4,904 (+33
> at M30.1). Frontend Vitest 282 → 300 (+18 at M30.2).
> Acceptance 20 → 21 journeys (+1 M30.2 edit-delete
> describe block). Audit **157 / 123 covered / 34 backend-
> only / 317 service verbs**.
>
> **Zero-drift permission-class streak advanced 29 → 31
> consecutive milestones** (M10 → M30). Planning-time as-
> recommended streak reached **9** at M30.0 close, unchanged
> at M30.1 + M30.2 (both pure implementation).
>
> **Substrate-compound-value continuation reached 4 links
> realized** (M27.1 gl-accounts → M28.1 templates → M29
> variable-amount → M30 template CRUD closure). M30 spent
> zero new migrations by composing on M28.1's `is_active`
> field + model shape.
>
> **Additive-prop pattern (durable lesson (t)) re-applied
> successfully at M30.2** — first re-application of the
> M29.2-surfaced lesson. Elevates from "surfaced" to
> "load-bearing across two milestones."
>
> **§0.a durable lesson (v) preserved through M30.2** —
> M30.2's new test-id conventions mirror the existing
> `template-instantiate-<pk>` pattern; the amount-cell UI
> shape on `NewJournalEntryDialog` was left unchanged.
>
> **Coordinated M30 close push pending.** All M30 non-
> §0.a work is local-only; awaits explicit user
> confirmation. Expected M30 commits at push: **6** (§0.a
> `43b715b` already pushed at SESSION_200 under exception;
> SESSION_200 planning `1956ed7` local; SESSION_201 M30.1
> `6bb5b0f` local; this session's M30.2 + close-out
> commits, plus hash-backfill follow-up per convention).
>
> **Two durable design principles NEW at M30.2**
> (see `MILESTONE_30_RETROSPECTIVE.md` §5):
> (w) *`is_active` mutation surface asymmetry is a load-
>     bearing design constraint* — PATCH must silently drop
>     `is_active` from body; activation is DELETE-only
>     (soft) or a future Restore verb; enforced at
>     serializer + service + endpoint-test layers;
> (x) *Delete UI copy must reframe row-action vocabulary
>     into truth vocabulary* — row button says "Delete"
>     (operator convention); confirmation dialog reframes to
>     "Deactivate" (truth — soft-hide, historically
>     preserved, restorable) + explicit reassurance about
>     historical entries.
>
> **Five NEW M31+ candidates surfaced or elevated during
> M30** (per `MILESTONE_30_RETROSPECTIVE.md` §9):
> (a) **NEW — Restore / "Show inactive" UI toggle on
>     templates** — freshly unblocked at M30 close by
>     M30.1's `include_inactive` service kwarg; endpoint
>     exposure is a one-line view-layer change; toggle on
>     M30.2 templates section is small-to-moderate scope;
>     completes operator-facing soft-delete lifecycle;
> (b) **NEW C — F&I chargeback substrate** — would extend
>     substrate-compound-value lineage to a fifth link on
>     M27.1; gated on pilot evidence today (unchanged from
>     M29 §9);
> (c) NEW O2 — Row 5 public-fetch-helper regex refinement
>     (M26/M27/M28/M29/M30 deferral, unchanged);
> (d) NEW O3 — Rows-1–4 plain-string-literal investigation
>     (M26/M27/M28/M29/M30 deferral, unchanged);
> (e) H — Test-hygiene remediation — same 3 shared-DB non-
>     idempotent journeys unchanged from M27.2 → M28.2 →
>     M29.2 → M30.2 close.
>
> **SESSION_203 opens M31.0 — planning refinement + target
> selection.** No target locked yet — the candidate list
> surfaces at open (elevated: NEW Restore UI, NEW C F&I,
> O2, O3, H; gated: T/U/L/M; deferred pending evidence: D;
> deferred stable: G; plus all M30 §3 + M29 §3 + M28 §3 +
> M27 §3 + M25 §4 deferrals still valid). The assistant
> recommends one option with rationale grounded in the
> durable primary operational-coverage lens (or a
> substrate-compound-value continuation / substrate-
> integrity reframe if evidence supports it); the user
> confirms or redirects.

## First thing SESSION_203 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches `origin/main`
  post-M30 push (if pushed) OR local `HEAD` ahead by 4–6
  commits (SESSION_200 handoff + M30.1 + M30.2 impl +
  M30.2 close-out + potential hash-backfill) if push not
  yet executed.
- `git log --oneline -10` — top should be the M30.2 close-
  out or hash-backfill commit; check for expected M30
  commit sequence.
- `python3 manage.py test dealer_ai` → **4,904 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **300 pass** across 36 files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive reset
  per SESSION_200 §0.a durable lesson (v).

### 2. If M30 pushed — monitor first M30 CI run

If M30 has been pushed, verify the CI acceptance workflow
status via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as §0.a M31.0 amendments before opening
§5.a.

**If green:** M30 is CI-verified shipped; proceed to §3.

### 3. Regenerate the audit artifact

Before candidate presentation, rerun the audit tooling to
confirm the M30.2 baseline holds:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Expected: **157 total / 123 covered / 34 backend-only / 317
service verbs**. If the artifact drifts from this,
investigate before scope-locking.

### 4. Present the M31 candidate list

Per the M30 retrospective §9 evidence:

**Elevated (highest recommendation strength at M31.0):**

- **NEW — Restore / "Show inactive" UI toggle on templates.**
  M28 §3 deferral, freshly unblocked at M30 close by
  M30.1's `include_inactive` service kwarg. Endpoint
  exposure is a one-line view-layer change; a "Show
  inactive" toggle on the M30.2 templates section is small-
  to-moderate scope. Direct sequential complement to M30 —
  completes the operator-facing soft-delete lifecycle.
- **NEW C — F&I chargeback substrate.** Would reuse M27.1
  gl-accounts substrate + M28.1 template substrate.
  Continues the substrate-compound-value lineage into a
  **fifth link** if operator evidence surfaces during a
  pilot (gated).
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (M26/M27/M28/M29/M30 deferral, unchanged). Requires
  SESSION-189-§3-style tracing at M31.0 open. Blast radius
  unknown.
- **NEW O3 — Rows-1–4 plain-string-literal investigation**
  (M26/M27/M28/M29/M30 deferral). Requires tracing.
- **H — Test-hygiene remediation.** Three shared-DB non-
  idempotent journeys unchanged from M27.2 → M30.2 close.

**Gated (unchanged from M30 close):**

- T (real tester feedback); U (hosted-demo substrate); L
  (first-live-pilot staging); M (multi-operator support —
  breaks the zero-drift streak with intent).

**Deferred pending evidence (unchanged):**

- D (LLM router / cost caps).

**Deferred but stable:**

- G (dashboard testid hardening).

**Deferred at M30 §3 (all valid for later re-entry):**

Hard-delete escape hatch on templates; template mutation
audit trail; optimistic concurrency control on template
edit; bulk delete/edit.

**Deferred at M29 §3, M28 §3, M27 §3, M25 §4 (unchanged):**

All prior deferrals carried forward.

Present each with two-sentence scope + operator pain
resolved + dependency notes, then present the recommendation.

### 5. Recommend a target for §5.a

Ground the recommendation in the **primary operational-
coverage lens** ("which candidate most increases operational
coverage for a dealership employee?") OR its reframes
(substrate-compound-value continuation per M27.1 → M28.1 →
M29 → M30 precedent; substrate-integrity per M26 precedent)
if evidence supports it.

**Standing question from M30 retrospective §9:** with the
substrate-compound-value framing now proven across FOUR
consecutive links, the fifth link is the natural next move
under the compound-value lens. Two candidates continue this
lineage: (a) F&I chargeback on M27.1 (gated on pilot
evidence today); (b) Restore / Show-inactive on M28.1 +
M30.1 (available today; primary operational-coverage lens).
Evidence at M30 close does not force either path — both are
compelling; both are additive to the lineage.

**Alternatively:** if the M30 CI run surfaces regression
work at M31.0, address as §0.a amendments first.

### 6. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the standard six-to-eight load-bearing
decisions.

### 7. Verify BOTH intake AND downstream UI surfaces + FK discoverability before locking §5.b + §5.d

**M24.1-open + M25.0 + M25.2-open + SESSION_189 §3 +
SESSION_190 §2 + M27.0 §7 + M28.0 §7 + M29.0 §7 + M30.0 §7
durable lesson.** Every planning-open surface verification
must cover both intake AND downstream paths, including
audit-substrate accuracy checks when audit is load-bearing
on the selection, and **verify FK / identifier discoverability
for any create/edit workflow candidate**.

### 8. DoD compliance check

Per the M21.0 §5.f amendment: the M31 active memo §3 must
either name a Playwright journey addition or extension OR
explicitly document why no journey change is required
(M26 + M27.1 + M28.1 + M29.1 + M30.1 precedents for the
exception path — pattern firmly established at five
invocations).

### 9. Expand M31 planning skeleton

Draft fresh per the standard active-memo shape (no existing
skeleton at close of M30).

### 10. Ship the M31.0 handoff

- `docs/handoffs/SESSION_203_m31_inc0_planning.md`.
- **Do NOT push** — M31.0 is planning only; coordinated push
  at M31 close.

## Non-goals for SESSION_203

- ❌ Do NOT ship any backend or frontend code — planning-
  only session.
- ❌ Do NOT open any M31 implementation increment.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M30 shipped surface.
- ❌ Do NOT modify the acceptance suite unless CI regression
  fixes land as §0.a M31.0 amendments.
- ❌ Do NOT skip the DoD compliance check.
- ❌ Do NOT skip the downstream / substrate / FK-
  discoverability verification (M24–M30 durable lessons).
- ❌ Do NOT re-litigate M30.0 architectural verifications
  (dialog consolidation + soft-delete integrity — both
  locked at M30.0 and validated through M30.2 shipping).

## Baseline expected at close

Backend + frontend + acceptance unchanged from M30 close.
Only planning docs change.

## NEXT TASK

Start SESSION_203 with (a) starting-state verification;
(b) if M30 pushed, monitor first M30 CI run + fix any
regressions as §0.a M31.0 amendments; (c) regenerate the
audit artifact and confirm 123 / 157 holds; (d) present the
candidate list with recommendation + rationale under the
primary operational-coverage lens (or substrate-compound-
value continuation reframe if evidence supports it);
(e) await user confirmation of §5.a; (f) draft §5.b–§5.h;
(g) DoD compliance check on §3 draft; (h) expand the M31
planning memo; (i) ship the M31.0 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M1–M28 shipped in-tree; M29–M30 shipped surface in
   CAPABILITY_MATRIX §7δ + §7ε per convention adopted at
   M27+)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_30_RETROSPECTIVE.md`
   §3 (deviations) + §5 (durable lessons — especially
   (t) additive-prop pattern now load-bearing, (v)
   acceptance-selector-sweep, (w) is_active mutation
   asymmetry, (x) delete-UI copy vocabulary asymmetry)
   + §9 (standing M31 question)
6. `docs/roadmap/MILESTONE_30_PLANNING.md`
   (M30 governing contract + §0.a + all §5 locks + two
   architectural verifications at §4.6 and §4.7)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (post-M30 baseline — 157 endpoints / **123 covered** /
   34 backend-only / 317 service verbs)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25) + §7α (M26) +
   §7β (M27) + §7γ (M28) + §7δ (M29) + §7ε (M30 shipped
   surface)
9. `docs/handoffs/SESSION_202_m30_inc2_frontend.md`
   (M30.2 shipped + M30 close-out fold)
10. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs future refactor scoping)
11. Memory record `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified through M30.0)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_202 — Milestone 30 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0050` (unchanged since M28.1). Test baseline:
  **4,904 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest baseline: 300 pass** across
  36 test files.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS
  5.6 operational; **21 journeys** total. Full-suite fresh-
  DB run at M30.2 close: **27 passed / 0 failed / 36.5s**.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run on
  `origin/main` at `43b715b` (SESSION_200 §0.a hotfix
  push): 26 passed / 0 failed / 2m43s. First real M30 CI
  run pending on the M30 push (executes at M30 close after
  explicit user confirmation).
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler. 10
  scheduled task families registered.
- **Milestones shipped:** M1 → **M30**. M31 target
  selection pending (SESSION_203).
- **DRF admin surface:** **117** endpoints (M28.1 116 → +1
  at M30.1).
- **Frontend operator routes:** 20 (unchanged; M30.2
  attached Edit + Delete buttons to existing rows on the
  JE list page, no new route).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** M30.1 added `update_journal_entry
  _template` + `delete_journal_entry_template` verbs +
  `include_inactive` kwarg on `get_journal_entry_template`.
  M30.2 added no service verbs.
- **Frontend surfaces:** M30.2 renamed
  `NewJournalEntryTemplateDialog.tsx` →
  `JournalEntryTemplateDialog.tsx` (via `git mv` + import
  sweep in same commit); added additive `mode` /
  `initialTemplate` / `onEdited` / `open` / `onOpenChange`
  props; attached Edit + Delete row buttons to templates
  section; added inline `TemplateDeleteConfirmDialog` with
  mandated D3 copy.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **thirty-one consecutive milestones** (M10 → M30).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 30 status:** SHIPPED (SESSION_202 close-out
  landed all documentation + status flips + M31 handoff +
  coordinated close-out session-local commits, awaits
  explicit user push confirmation).
- **Audit tooling status:** unchanged from M26.1. Coverage
  **123 / 157** (M29.2 close 122 / 156 → M30.1 122 / 157
  → M30.2 123 / 157 with M30.1 endpoint re-classified to
  covered by M30.2's wrappers).
- **§9 evidence for M31:** NEW Restore / "Show inactive"
  UI toggle (elevated — freshly unblocked by M30.1
  `include_inactive` kwarg); NEW C F&I chargeback
  substrate (elevated pending pilot — would be fifth
  substrate-compound-value link on M27.1); NEW O2 + NEW O3
  (unchanged from M26+M27+M28+M29+M30); H (test-hygiene —
  same 3 failing journeys unchanged from M27.2+M28.2+M29.2
  +M30.2); plus gated T/U/L/M, deferred D, deferred stable
  G, plus M30 §3 + M29 §3 + M28 §3 + M27 §3 + M25 §4
  deferrals.
- **Planning-time streak: 9** (at M30.2 close; unchanged
  from M30.0 as-recommended; M30.1 + M30.2 both pure
  implementation; historical run of 89 across M10 → M23
  preserved).
- **DoD amendment (M21.0 §5.f Option B):** every future
  customer-facing milestone must add or update at least
  one Playwright operational journey, or explicitly
  document in §3 why no journey change is required. M26
  invoked the exception path (audit-tooling
  infrastructure); M27.1 was the second invocation; M28.1
  was the third; M29.1 was the fourth; **M30.1 was the
  fifth invocation** (backend-only detail endpoint with
  no operator-facing behavior change); M30.2 satisfied DoD
  directly via new `edit-delete` describe block.
- **M30 audit coverage at close:** 157 endpoints, **123
  covered / 34 backend-only** (delta from M29.2: +1
  endpoint, +1 covered, unchanged backend-only). Two-
  source agreement confirmed both M30.1 and M30.2 coverage
  numbers.
- **Durable lessons carried into M31+:** all (a)–(x) from
  the SESSION_202 close-state list continue to apply. M30
  added two new: (w) **NEW at M30.2** — `is_active`
  mutation surface asymmetry (PATCH silently drops it;
  activation is DELETE/Restore only); (x) **NEW at M30.2**
  — Delete UI copy must reframe row-action vocabulary
  ("Delete" button, "Deactivate" confirmation) into truth
  vocabulary + include historical-entries reassurance.
