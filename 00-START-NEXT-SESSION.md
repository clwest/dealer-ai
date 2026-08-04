---
state: active
date: 2026-08-04
last_session_shipped: SESSION_205
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
milestone_31_status: shipped
next_session: SESSION_206
next_milestone: 32
next_milestone_name: "(target selection pending — locked at M32.0 open)"
next_increment: 0
next_increment_name: "M32.0 — Planning refinement + target selection"
---

# Next session — SESSION_206 · Milestone 32 · Increment 0 (M32.0 — planning refinement + target selection)

> **Milestone 31 — Template Restore / "Show inactive" UI —
> SHIPPED at SESSION_205.** M31.0 planning + M31.1 backend
> substrate + M31.2 frontend + Playwright + close-out fold
> all landed. Backend baseline 4,904 → 4,933 (+29 at M31.1).
> Frontend Vitest 300 → 319 (+19 at M31.2). Acceptance 21
> → 22 journeys (+1 M31.2 restore-inactive describe block).
> Audit 157/123/34/317 → **158 / 124 / 34 / 318**.
>
> **Zero-drift permission-class streak advanced 31 → 33
> consecutive milestones** (M10 → M31). Planning-time
> as-recommended streak reached **10** at M31.0 close,
> unchanged at M31.1 + M31.2 (both pure implementation).
>
> **Substrate-compound-value continuation reached 5 links
> realized** (M27.1 gl-accounts → M28.1 template substrate
> → M29 variable-amount → M30 template CRUD closure → **M31
> template lifecycle closure**). M31 spent zero new
> migrations by composing on M28.1's `is_active` field +
> M30.1's `include_inactive` kwarg.
>
> **Two durable lessons elevated to "load-bearing across
> two milestones" at M31 close** (see
> `MILESTONE_31_RETROSPECTIVE.md` §5): (w) `is_active`
> mutation surface asymmetry (M30.2 surfaced, M31.1
> re-applied via Restore as second dedicated activation
> verb + regression test); (x) row-action truth-vocabulary
> asymmetry (M30.2 surfaced, M31.2 re-applied via "Restore"
> row button → "Reactivate template?" confirmation).
>
> **One NEW durable design principle surfaced at M31.0
> §4.1:** *lifecycle-integrity precheck governs the shape
> of L1-class fail-closed guards* — smallest fix at the
> natural enforcement layer, which may not be the layer
> the new surface touches. Awaits first re-application to
> elevate.
>
> **§9 five NEW/carried M32+ candidates surfaced or
> elevated during M31** (per
> `MILESTONE_31_RETROSPECTIVE.md` §9):
> (a) **NEW C — F&I chargeback substrate** — sixth-link
>     substrate-compound-value candidate; gated on pilot
>     evidence today (unchanged from M30 §9);
> (b) NEW O2 — Row 5 public-fetch-helper regex refinement
>     (M26/M27/M28/M29/M30/M31 deferral, unchanged);
> (c) NEW O3 — Rows-1–4 plain-string-literal investigation
>     (M26/M27/M28/M29/M30/M31 deferral, unchanged);
> (d) H — Test-hygiene remediation — same 3 shared-DB
>     non-idempotent journeys unchanged from M27.2 → M31.2
>     close.
> (e) **Depth vs breadth standing question:** the accounting/
>     templates domain has absorbed FIVE consecutive
>     planning-time selections. Operator-coverage lens may
>     benefit from breadth after depth. Fresh direct-
>     operator gaps to survey: deal writeups (audit
>     #112–114), vendor detail (#43), photo reorder (#65),
>     F&I domain surface (#89–101 excluding chargeback
>     which is already elevated).
>
> **Coordinated M31 close push pending.** All M31 work is
> local-only; awaits explicit user confirmation. Expected
> M31 commits at push: **6** — SESSION_203 M31.0 planning
> `f45a630`; SESSION_203 hash-backfill `5d12184`;
> SESSION_204 M31.1 `b0e21a8`; SESSION_204 hash-backfill
> `7c1cced`; SESSION_205 M31.2 + close-out fold (this
> session's commit); SESSION_205 hash-backfill (this
> session's follow-up commit).
>
> **SESSION_206 opens M32.0 — planning refinement + target
> selection.** No target locked yet — the candidate list
> surfaces at open (elevated: NEW C F&I chargeback, NEW O2,
> NEW O3, H; plus fresh direct-operator gaps surveyed under
> the depth-vs-breadth lens; gated T/U/L/M; deferred D;
> deferred stable G; plus all M31 §3 + prior deferrals still
> valid). The assistant recommends one option with rationale
> grounded in the durable primary operational-coverage lens
> (or a substrate-compound-value continuation / breadth
> reframe if evidence supports it); the user confirms or
> redirects.

## First thing SESSION_206 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches
  `origin/main` post-M31 push (if pushed) OR local `HEAD`
  ahead by 6 commits (SESSION_203–205 planning + impls +
  hash-backfills) if push not yet executed.
- `git log --oneline -10` — top should be the M31.2
  hash-backfill commit; check for expected M31 commit
  sequence.
- `python3 manage.py test dealer_ai` → **4,933 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **319 pass** across 36 files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive reset
  per SESSION_200 §0.a durable lesson (v).

### 2. If M31 pushed — monitor first M31 CI run

If M31 has been pushed, verify the CI acceptance workflow
status via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as §0.a M32.0 amendments before
opening §5.a.

**If green:** M31 is CI-verified shipped; proceed to §3.

### 3. Regenerate the audit artifact

Before candidate presentation, rerun the audit tooling to
confirm the M31.2 baseline holds:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Expected: **158 total / 124 covered / 34 backend-only / 318
service verbs**. If the artifact drifts from this,
investigate before scope-locking.

### 4. Present the M32 candidate list

Per the M31 retrospective §9 evidence:

**Elevated (highest recommendation strength at M32.0):**

- **NEW C — F&I chargeback substrate.** Sixth-link
  substrate-compound-value candidate; still gated on pilot
  evidence today (unchanged from M30/M31 §9). Would reuse
  M27.1 gl-accounts substrate + M28.1 template substrate.
  Endpoint #101 exists but is one of 13 uncovered F&I
  endpoints (audit #89–101); meaningful UI needs contract
  + back-end-product context. Not bounded without operator
  direction.
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (M26/M27/M28/M29/M30/M31 deferral, unchanged). Requires
  SESSION-189-§3-style tracing at M32.0 open. Blast radius
  unknown.
- **NEW O3 — Rows-1–4 plain-string-literal investigation**
  (M26/M27/M28/M29/M30/M31 deferral). Requires tracing.
- **H — Test-hygiene remediation.** Three shared-DB non-
  idempotent journeys unchanged from M27.2 → M31.2 close.

**Fresh direct-operator gaps to survey (breadth candidates
per M31 retrospective §9 standing question):** deal
writeups (audit #112–114 — 3-endpoint create/approve/
hand-off flow, no operator evidence surfaced M28→M31);
vendor detail (#43, wrapper-only, small polish); photo
reorder (#65, wrapper-only, small polish); other backend-
only audit endpoints. None have evidenced operator pain
today.

**Gated (unchanged from M29+M30+M31 close):**

- T (real tester feedback); U (hosted-demo substrate); L
  (first-live-pilot staging); M (multi-operator support —
  breaks the M10 → M31 zero-drift streak with intent).

**Deferred pending evidence (unchanged):**

- D (LLM router / cost caps).

**Deferred but stable:**

- G (dashboard testid hardening).

**Deferred at M31 §3 (all valid for later re-entry):**

Hard-delete escape hatch on templates; bulk delete/
restore/edit on templates; template mutation audit
history; optimistic concurrency control on Restore/
Deactivate; template mutation history / diff viewer;
auto-refresh / websocket invalidation of stale-tab
template list (R1 accepted decoupling consequence);
persistent Show-inactive toggle state; bulk lifecycle
actions across templates list.

**Deferred at M30 §3, M29 §3, M28 §3, M27 §3, M25 §4
(unchanged):** all prior deferrals carried forward.

Present each with two-sentence scope + operator pain
resolved + dependency notes, then present the
recommendation.

### 5. Recommend a target for §5.a

Ground the recommendation in the **primary operational-
coverage lens** ("which candidate most increases
operational coverage for a dealership employee?") OR its
reframes (substrate-compound-value continuation per M27.1
→ M28.1 → M29 → M30 → M31 precedent; substrate-integrity
per M26 precedent) if evidence supports it.

**Standing question from M31 retrospective §9:** the
accounting/templates domain has absorbed **five
consecutive** planning-time selections (M27.1 → M31). The
operator-coverage lens may benefit from breadth after
depth. Two natural next moves: (a) **F&I chargeback**
continues the substrate-compound-value depth arc as a
sixth link IF pilot evidence surfaces; (b) **a fresh
direct-operator gap** (deal writeups, vendor detail,
photo reorder, or elsewhere in the 34 backend-only audit
endpoints) provides breadth. Neither path is forced by
evidence at M31 close. Evaluate through the primary
operational-coverage lens first; secondary reframes only
if evidence surfaces.

**Alternatively:** if the M31 CI run surfaces regression
work at M32.0, address as §0.a amendments first.

### 6. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the standard six-to-ten load-
bearing decisions per M28/M29/M30/M31 shape.

### 7. Verify BOTH intake AND downstream UI surfaces + FK discoverability before locking §5.b + §5.d

**M24.1-open + M25.0 + M25.2-open + SESSION_189 §3 +
SESSION_190 §2 + M27.0 §7 + M28.0 §7 + M29.0 §7 + M30.0
§7 + M31.0 §7 durable lesson.** Every planning-open
surface verification must cover both intake AND downstream
paths, including audit-substrate accuracy checks when
audit is load-bearing on the selection, and **verify FK /
identifier discoverability for any create/edit workflow
candidate**.

### 8. DoD compliance check

Per the M21.0 §5.f amendment: the M32 active memo §3
must either name a Playwright journey addition or
extension OR explicitly document why no journey change is
required (M26 + M27.1 + M28.1 + M29.1 + M30.1 + M31.1
precedents for the exception path — pattern firmly
established at six invocations).

### 9. Expand M32 planning skeleton

Draft fresh per the standard active-memo shape (no
existing skeleton at close of M31).

### 10. Ship the M32.0 handoff

- `docs/handoffs/SESSION_206_m32_inc0_planning.md`.
- **Do NOT push** — M32.0 is planning only; coordinated
  push at M32 close.

## Non-goals for SESSION_206

- ❌ Do NOT ship any backend or frontend code — planning-
  only session.
- ❌ Do NOT open any M32 implementation increment.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M31 shipped surface.
- ❌ Do NOT modify the acceptance suite unless CI
  regression fixes land as §0.a M32.0 amendments.
- ❌ Do NOT skip the DoD compliance check.
- ❌ Do NOT skip the downstream / substrate / FK-
  discoverability verification (M24–M31 durable lessons).
- ❌ Do NOT re-litigate M31 architectural verifications
  (lifecycle-integrity precheck resolved; §5.b review
  points confirmed by user; both locked at M31.0 and
  validated through M31.2 shipping).

## Baseline expected at close

Backend + frontend + acceptance unchanged from M31 close.
Only planning docs change.

## NEXT TASK

Start SESSION_206 with (a) starting-state verification;
(b) if M31 pushed, monitor first M31 CI run + fix any
regressions as §0.a M32.0 amendments; (c) regenerate the
audit artifact and confirm 158/124/34/318 holds;
(d) present the candidate list with recommendation +
rationale under the primary operational-coverage lens
(with breadth-vs-depth framing per M31 §9 standing
question); (e) await user confirmation of §5.a;
(f) draft §5.b–§5.h; (g) DoD compliance check on §3
draft; (h) expand the M32 planning memo; (i) ship the
M32.0 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M1–M28 shipped in-tree; M29–M31 shipped surface in
   CAPABILITY_MATRIX §7δ + §7ε + §7ζ per convention
   adopted at M27+)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_31_RETROSPECTIVE.md`** §5
   (three durable-lesson elevations + one NEW principle)
   + §9 (M32 candidate list origin + breadth-vs-depth
   standing question)
6. `docs/roadmap/MILESTONE_31_PLANNING.md` (shipped;
   governing contract for M31)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (post-M31 baseline — 158 endpoints / **124 covered**
   / 34 backend-only / 318 service verbs)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25) + §7α (M26) +
   §7β (M27) + §7γ (M28) + §7δ (M29) + §7ε (M30) +
   **§7ζ (M31 shipped surface)**
9. `docs/handoffs/SESSION_205_m31_inc2_frontend.md` (M31.2
   shipped + M31 close-out fold)
10. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs future refactor scoping;
    exercised at M31.2 for `TemplateRestoreConfirmDialog`)
11. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified through M31.0)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_205 — Milestone 31 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0050` (unchanged since M28.1). Test baseline:
  **4,933 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  + `vite build` clean. **Vitest baseline: 319 pass**
  across 36 test files.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS
  5.6 operational; **22 journeys** total. Full-suite
  fresh-DB run at M31.2 close: **28 passed / 0 failed /
  32.6s**.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run on
  `origin/main` at `f658c06` (M30.2 hash-backfill
  commit): 26 passed / 0 failed / 2m50s. First real M31
  CI run pending on the M31 push (executes at M31 close
  after explicit user confirmation).
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler. 10
  scheduled task families registered.
- **Milestones shipped:** M1 → **M31**. M32 target
  selection pending (SESSION_206).
- **DRF admin surface:** **118** endpoints (M28.1 116 →
  +1 at M30.1 → +1 at M31.1).
- **Frontend operator routes:** 20 (unchanged; M31.2
  attached Show-inactive toggle + is_active-aware row
  rendering + Restore button + Restore dialog to the
  existing JE list page, no new route).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** **318** verbs (M30 close 317 →
  +1 `restore_journal_entry_template` at M31.1).
- **Frontend surfaces:** M31.2 added Show-inactive
  toggle, `TemplateRestoreConfirmDialog`, is_active-
  aware `TemplateRow` rendering (Inactive badge + row
  aria-label + `template-row-inactive-<pk>` testid +
  muted opacity), L1 lifecycle-integrity guard on
  Instantiate + Edit (visible-but-disabled with
  explanatory aria-labels), Restore success badge, D10
  copy update on `TemplateDeleteConfirmDialog`; extended
  `fetchJournalEntryTemplates` with `includeInactive`
  option; added `restoreJournalEntryTemplate` wrapper.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift
  streak **thirty-three consecutive milestones** (M10 →
  M31). Advanced 31 → 32 at M31.1 → 33 at M31.2.
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 31 status:** SHIPPED (SESSION_205 close-
  out landed all documentation + status flips + close-
  out session-local commits, awaits explicit user push
  confirmation for coordinated M31 push).
- **Audit tooling status:** unchanged from M26.1.
  Coverage **124 / 158** (M30.2 close 123 / 157 → M31.1
  123 / 158 transitional → M31.2 124 / 158 with M31.1
  Restore endpoint re-classified from backend-only to
  covered).
- **§9 evidence for M32:** NEW C F&I chargeback substrate
  (unchanged — still gated pending pilot evidence);
  NEW O2 + NEW O3 (unchanged from M26+M27+M28+M29+M30+
  M31); H (test-hygiene — same 3 failing journeys
  unchanged); plus gated T/U/L/M, deferred D, deferred
  stable G, plus M31 §3 + M30 §3 + M29 §3 + M28 §3 +
  M27 §3 + M25 §4 deferrals. **Standing question at
  M32.0:** depth (continue substrate-compound-value arc
  with F&I chargeback if pilot evidence surfaces) vs
  breadth (fresh direct-operator gap surveyed from the
  34 backend-only audit endpoints).
- **Planning-time streak: 10** (at M31.2 close; unchanged
  from M31.0 as-recommended; M31.1 + M31.2 both pure
  implementation; historical run of 89 across M10 → M23
  preserved).
- **DoD amendment (M21.0 §5.f Option B):** every future
  customer-facing milestone must add or update at least
  one Playwright operational journey, or explicitly
  document in §3 why no journey change is required.
  M26 first invocation; M27.1 second; M28.1 third;
  M29.1 fourth; M30.1 fifth; **M31.1 sixth** (backend-
  only substrate with no operator-facing behavior
  change); M31.2 satisfied DoD directly via new
  `restore-inactive` describe block.
- **M31 audit coverage at close:** 158 endpoints,
  **124 covered / 34 backend-only** (delta from M30.2:
  +1 endpoint, +1 covered, unchanged backend-only —
  Restore endpoint transitioned through backend-only at
  M31.1 then re-covered at M31.2). Two-source agreement
  confirmed both M31.1 and M31.2 coverage numbers.
- **Durable lessons carried into M32+:** all (a)–(x)
  from the SESSION_202 close-state list continue to
  apply. M31 elevated **two** lessons to "load-bearing
  across two milestones": (w) `is_active` mutation
  asymmetry (M30.2 + M31.1); (x) row-action truth-
  vocabulary reframing (M30.2 + M31.2). **One NEW
  principle surfaced at M31.0** — lifecycle-integrity
  precheck governs L1-class fail-closed guard shape;
  awaits first re-application to elevate.
