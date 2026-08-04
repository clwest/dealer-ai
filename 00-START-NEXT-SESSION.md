---
state: active
date: 2026-08-04
last_session_shipped: SESSION_199
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
next_session: SESSION_200
next_milestone: 30
next_milestone_name: "(target selection pending — locked at M30.0 open)"
next_increment: 0
next_increment_name: "M30.0 — Planning refinement + target selection"
---

# Next session — SESSION_200 · Milestone 30 · Increment 0 (M30.0 — planning refinement + target selection)

> **Milestone 29 — Variable-Amount Journal Templates —
> SHIPPED at SESSION_199.** M29.0 planning + M29.1 backend
> substrate + M29.2 frontend + Playwright all landed;
> close-out folded into M29.2 per §5.h Option B. Backend
> baseline 4,855 → 4,871 (+16 at M29.1). Frontend Vitest 270
> → 282 (+12 at M29.2). Acceptance 19 → 20 journeys (+1 M29.2
> combined variable-amount describe block).
>
> **Zero-drift permission-class streak advanced 28 → 29
> consecutive milestones** (M10 → M29). Planning-time as-
> recommended streak reached **8** at M29.0 close, unchanged
> at M29.1 + M29.2 (both pure implementation). Historical
> run of 89 across M10 → M23 preserved for the record.
>
> **Substrate-compound-value continuation reached 3 links
> realized** (M27.1 gl-accounts → M28.1 templates → M29
> variable-amount extension). M29 spent the M28.1 nullable-
> amount schema reservation via migration 0050 — zero new
> migrations across M29.
>
> **Coordinated push at M29 close pending.** All M29 work is
> local-only; awaits explicit user confirmation before push.
> Expected M29 commits at push: **6** (M29.0 planning + hash
> backfill + M29.1 substrate + hash backfill + M29.2 close +
> hash backfill).
>
> **Two durable design principles surfaced or reinforced at
> M29** (see `MILESTONE_29_RETROSPECTIVE.md` §5):
> (a) *additive-prop pattern for UI reuse* — NEW at M29.2;
>     prefer additive optional prop with safe default over
>     thin wrapper when divergent UI must render inside an
>     existing cell; recorded in retrospective §5;
> (b) *reset every override / annotation state in every reset
>     path* — NEW at M29.2; failure mode is UI state leaking
>     between usage contexts (e.g., overrides from template A
>     leak into template B);
> (c) *DoD exception path for infrastructure-only sub-
>     increments* — REINFORCED at fourth invocation (M26 +
>     M27.1 + M28.1 + M29.1);
> (d) *substrate-compound-value continuation across
>     milestones* — REINFORCED at third link realized.
>
> **Five NEW M30+ candidates surfaced or elevated during M29**
> (per `MILESTONE_29_RETROSPECTIVE.md` §9):
> (a) **NEW template edit / delete UI** — third increment on
>     the M28+M29 template surface; would use the M29.2
>     chip/Override infrastructure;
> (b) **NEW C — F&I chargeback substrate** — would extend the
>     substrate-compound-value lineage to a fourth link on
>     M27.1;
> (c) NEW O2 — Row 5 public-fetch-helper regex refinement
>     (M26/M27/M28/M29 deferral, unchanged);
> (d) NEW O3 — Rows-1–4 plain-string-literal investigation
>     (M26/M27/M28/M29 deferral, unchanged);
> (e) H — Test-hygiene remediation — same 3 shared-DB non-
>     idempotent journeys unchanged from M27.2 → M28.2 →
>     M29.2 close.
>
> **SESSION_200 opens M30.0 — planning refinement + target
> selection.** No target locked yet — the candidate list
> surfaces at open (elevated: NEW template edit/delete UI,
> NEW C F&I substrate, O2, O3, H; gated: T/U/L/M; deferred
> pending evidence: D; deferred stable: G; plus all M29 §3 +
> M28 §3 + M27 §3 + M25 §4 deferrals still valid). The
> assistant recommends one option with rationale grounded in
> the durable primary operational-coverage lens (or a
> substrate-compound-value continuation / substrate-integrity
> reframe if evidence supports it); the user confirms or
> redirects.

## First thing SESSION_200 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches `origin/main`
  post-M29 push (if pushed) OR local `HEAD` ahead by 6
  commits (M29.0 planning + hash backfill + M29.1 substrate +
  hash backfill + M29.2 close + hash backfill) if push not
  yet executed.
- `git log --oneline -10` — top should be the M29.2 hash-
  backfill commit; six M29 commits total.
- `python3 manage.py test dealer_ai` → **4,871 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **282 pass** across 36 files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. If M29 pushed — monitor first M29 CI run

If M29 has been pushed, verify the CI acceptance workflow
status via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as §0.a M30.0 amendments before opening
§5.a.

**If green:** M29 is CI-verified shipped; proceed to §3.

### 3. Regenerate the audit artifact

Before candidate presentation, rerun the audit tooling to
confirm the M29.2 baseline holds:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Expected: **156 total / 122 covered / 34 backend-only / 315
service verbs**. If the artifact drifts from this,
investigate before scope-locking.

### 4. Present the M30 candidate list

Per the M29 retrospective §9 evidence:

**Elevated (highest recommendation strength at M30.0):**

- **NEW template edit / delete UI.** Third increment on the
  M28+M29 template surface. Substrate to build on: M28.2
  templates section + M29.2 chip/Override infrastructure.
  Small-to-moderate scope; direct operator-facing value
  (mid-year chart-of-accounts correction; deactivate stale
  templates without DB access). Would extend the M28/M29
  template surface into a third increment on the same
  lineage.
- **NEW C — F&I chargeback substrate.** Would reuse M27.1
  gl-accounts substrate. Continues the substrate-compound-
  value lineage into a fourth link if operator evidence
  surfaces during a pilot.
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (M26/M27/M28/M29 deferral, unchanged). Requires SESSION-189-
  §3-style tracing at M30.0 open. Blast radius unknown.
- **NEW O3 — Rows-1–4 plain-string-literal investigation**
  (M26/M27/M28/M29 deferral). Requires tracing.
- **H — Test-hygiene remediation.** Three shared-DB non-
  idempotent journeys unchanged from M27.2 → M28.2 → M29.2
  close.

**Gated (unchanged from M29 close):**

- T (real tester feedback); U (hosted-demo substrate); L
  (first-live-pilot staging); M (multi-operator support —
  breaks the zero-drift streak with intent).

**Deferred pending evidence (unchanged):**

- D (LLM router / cost caps).

**Deferred but stable:**

- G (dashboard testid hardening).

**Deferred at M29 §3 (all valid for later re-entry):**

Fully-variable UX polish ("Repeat last amounts");
server-recorded instantiation audit trail; named / shared
template variables.

**Deferred at M28 §3 (unchanged):**

Historical-template back-reference on `JournalEntry`; server-
side template search / pagination; `?include_inactive=true`
endpoint exposure; standalone template detail page.

**Deferred at M27 §3 + M25 §4 (unchanged):**

Standalone Chart of Accounts page/route; JE edit/update;
`posted_by_user` override; advanced picker filtering;
server-side gl-accounts search / pagination;
`?include_inactive=true` on gl-accounts; secondary
"+ Record test drive" launch point; clickable "Referred by"
nav; named-platform webhook adapters; attribution rollups;
vehicle-picker advanced filters.

Present each with two-sentence scope + operator pain
resolved + dependency notes, then present the recommendation.

### 5. Recommend a target for §5.a

Ground the recommendation in the **primary operational-
coverage lens** ("which candidate most increases operational
coverage for a dealership employee?") OR its reframes
(substrate-compound-value continuation per M27.1 → M28.1 →
M29 precedent; substrate-integrity per M26 precedent) if
evidence supports it.

**Standing question from M29 retrospective §9:** should the
substrate-compound-value framing continue for a fourth link
(template edit/delete UI on the M28+M29 base, OR F&I
chargeback substrate on the M27.1 base), or should M30 spend
the substrate-integrity audit-refinement path (O2 + O3 as a
combined M26-analogous milestone)? Evidence at M29 close
does not force either path.

**Alternatively:** if the M29 CI run surfaces regression
work at M30.0, address as §0.a amendments first.

### 6. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the standard six-to-eight load-bearing
decisions.

### 7. Verify BOTH intake AND downstream UI surfaces + FK discoverability before locking §5.b + §5.d

**M24.1-open + M25.0 + M25.2-open + SESSION_189 §3 +
SESSION_190 §2 + M27.0 §7 + M28.0 §7 + M29.0 §7
durable lesson.** Every planning-open surface verification
must cover both intake AND downstream paths, including
audit-substrate accuracy checks when audit is load-bearing
on the selection, and **verify FK / identifier discoverability
for any create/edit workflow candidate**.

### 8. DoD compliance check

Per the M21.0 §5.f amendment: the M30 active memo §3 must
either name a Playwright journey addition or extension OR
explicitly document why no journey change is required
(M26 + M27.1 + M28.1 + M29.1 precedents for the exception
path — pattern now well-established).

### 9. Expand M30 planning skeleton

Draft fresh per the standard active-memo shape (no existing
skeleton at close of M29).

### 10. Ship the M30.0 handoff

- `docs/handoffs/SESSION_200_m30_inc0_planning.md`.
- **Do NOT push** — M30.0 is planning only; coordinated push
  at M30 close.

## Non-goals for SESSION_200

- ❌ Do NOT ship any backend or frontend code — planning-
  only session.
- ❌ Do NOT open any M30 implementation increment.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M29 shipped surface.
- ❌ Do NOT modify the acceptance suite unless CI regression
  fixes land as §0.a M30.0 amendments.
- ❌ Do NOT skip the DoD compliance check.
- ❌ Do NOT skip the downstream / substrate / FK-
  discoverability verification (M24–M29 durable lessons).
- ❌ Do NOT re-litigate the M29.0 D3 implementation-boundary
  verification (the additive-prop pattern was locked and
  proven correct at M29.2).

## Baseline expected at close

Backend + frontend + acceptance unchanged from M29 close.
Only planning docs change.

## NEXT TASK

Start SESSION_200 with (a) starting-state verification;
(b) if M29 pushed, monitor first M29 CI run + fix any
regressions as §0.a M30.0 amendments; (c) regenerate the
audit artifact and confirm 122/156 holds; (d) present the
candidate list with recommendation + rationale under the
primary operational-coverage lens (or substrate-compound-
value continuation / substrate-integrity reframe if evidence
supports it); (e) await user confirmation of §5.a; (f) draft
§5.b–§5.h; (g) DoD compliance check on §3 draft;
(h) expand the M30 planning memo; (i) ship the M30.0
handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M29 shipped section landed at M29.2)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_29_RETROSPECTIVE.md`
   §3 (deviations) + §5 (durable lessons) + §9
   (standing M30 question)
6. `docs/roadmap/MILESTONE_29_PLANNING.md`
   (M29 governing contract + all §5 locks + M29.0
   implementation-boundary verification)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (post-M29 baseline — 156 endpoints / **122 covered** /
   34 backend-only)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25) + §7α (M26) +
   §7β (M27) + §7γ (M28) + §7δ (M29 shipped surface)
9. `docs/handoffs/SESSION_199_m29_inc2_frontend.md`
   (M29.2 shipped + M29 close-out fold)
10. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs future refactor scoping)
11. Memory record `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — reinforced through M29.0)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_199 — Milestone 29 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0050` (unchanged since M28.1). Test baseline:
  **4,871 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest baseline: 282 pass** across
  36 test files.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS
  5.6 operational; **20 journeys** total.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. First real M29 CI run
  pending on the M29 push (executes at M29 close after
  explicit user confirmation).
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler. 10 scheduled
  task families registered.
- **Milestones shipped:** M1 → **M29**. M30 target
  selection pending (SESSION_200).
- **DRF admin surface:** **116** endpoints (unchanged since
  M28.1).
- **Frontend operator routes:** 20 (unchanged).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** all M1–M28 packages unchanged. M29.1
  refined `_validate_template_lines` in
  `services/accounting/template.py` (three-state balance
  logic).
- **Frontend surfaces:** M29.2 added the "Variable amount"
  checkbox to `NewJournalEntryTemplateDialog`; the additive
  `lockedLines` prop + internal `overridden: Set<number>`
  state + `LockedAmountChip` sub-component + `variableSide`
  amber-ring on `NewJournalEntryDialog`; extended
  `AccountingJournalEntriesPage` `handleInstantiate` with
  `templateToLockedLines` wiring.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **twenty-nine consecutive milestones** (M10 → M29).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 29 status:** SHIPPED (SESSION_199 close-out
  landed all documentation + status flips + M30 handoff +
  coordinated close-out session-local commits, awaits
  explicit user push confirmation).
- **Audit tooling status:** unchanged from M26.1. Coverage
  **122 / 156** (unchanged from M28.2 close).
- **§9 evidence for M30:** NEW template edit / delete UI
  (elevated — third increment on the M28+M29 template
  surface); NEW C F&I chargeback substrate (elevated —
  fourth substrate-compound-value link on M27.1); NEW O2 +
  NEW O3 (unchanged from M26+M27+M28+M29); H (test-hygiene —
  same 3 failing journeys unchanged from M27.2+M28.2+M29.2);
  plus gated T/U/L/M, deferred D, deferred stable G, plus
  M29 §3 + M28 §3 + M27 §3 + M25 §4 deferrals.
- **Planning-time streak: 8** (at M29.2 close; unchanged
  from M29.0 as-recommended; M29.1 + M29.2 both pure
  implementation; historical run of 89 across M10 → M23
  preserved).
- **DoD amendment (M21.0 §5.f Option B):** every future
  customer-facing milestone must add or update at least one
  Playwright operational journey, or explicitly document in
  §3 why no journey change is required. M26 invoked the
  exception path (audit-tooling infrastructure); M27.1 was
  the second invocation; M28.1 was the third invocation;
  **M29.1 was the fourth invocation** (backend serializer +
  service substrate relaxation); M29.2 satisfied DoD
  directly via new `variable-amount` describe block.
- **M29 audit coverage at close:** 156 endpoints, **122
  covered / 34 backend-only** (unchanged from M28.2 close;
  no new endpoint at M29). Two-source agreement confirmed
  both M29.1 and M29.2 coverage numbers.
- **Durable lessons carried into M30+:** all (a)–(s) from
  the M28 close-state list continue to apply. M29 adds two
  new: (t) **NEW at M29.2** — *additive-prop pattern for UI
  reuse* — prefer additive optional prop with safe default
  over thin wrapper when divergent UI must render inside an
  existing cell; (u) **NEW at M29.2** — *reset every
  override / annotation state in every reset path* — failure
  mode is UI state leaking between usage contexts.
