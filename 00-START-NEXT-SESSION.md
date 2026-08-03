---
state: active
date: 2026-08-03
last_session_shipped: SESSION_187
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
next_session: SESSION_188
next_milestone: 26
next_milestone_name: "(target selection pending — locked at M26.0 open)"
next_increment: 0
next_increment_name: "M26.0 — Planning refinement + target selection"
---

# Next session — SESSION_188 · Milestone 26 · Increment 0 (M26.0 — planning refinement + target selection)

> **Milestone 25 — Lead-to-Test-Drive Operational Completion —
> SHIPPED at SESSION_187.** Three-increment milestone across
> SESSION_185 → SESSION_187 (M25.3 close-out folded into M25.2
> per §5.h Option B evidence-sized posture). **Backend baseline
> 4,780 → 4,793 (+13; M25.1 +2 admin_lead_detail tests + M25.2
> +11 admin_vehicle_list tests).** Frontend Vitest **209 → 226
> (+17 across LeadDetailModal source-line + RecordTestDriveForm).**
> Acceptance suite **13 → 14 journeys.** Full clean-DB dry-run:
> **20 passed (~30s)**.
>
> **M24.1-open §3 deferrals 12 + 13 + 14 all closed.** The sales
> front-of-funnel is now operationally complete not just at the
> assign level but at the schedule-test-drive level — a
> salesperson can receive a lead, see its source (referrer or
> platform), assign it, and schedule the test drive entirely
> through the modal. `DealerAiSalesTestDrives` remains the
> canonical read-only visibility surface.
>
> **Zero-drift permission-class streak extends 24 → 25**
> consecutive milestones (M10 → M25).
>
> **Planning-time as-recommended streak reached 3** across the
> M25 increments (fresh counter reset at M24.0; historical run
> of 89 across M10 → M23 preserved for the record). Two mid-
> planning refinements at M25.0 (§5.b JSONField selection over
> CharField, §5.d modal-only over dual entry points) and one at
> M25.2-open (§5.e admin/vehicles/ endpoint addition) all
> presented as empirical-discovery refinements with options +
> recommendation + user confirmation — counted as as-recommended
> increments because the recommendation process was transparent.
>
> **Coordinated push at M25 close pending.** M25.3 completed
> all documentation + status flips + M26 skeleton + close-out
> handoff — awaits explicit user confirmation before push. Six
> M25 commits (M25.0 + hash backfill + M25.1 + hash backfill +
> M25.2 + hash backfill + M25.3 close-out + hash backfill) land
> together in a single coordinated push per the M18 → M24
> cadence.
>
> **Two durable design principles surfaced at M25:**
> (a) *one operational workflow beats two partially overlapping
> ones* — for customer-facing features, default to one canonical
> entry point; defer secondary launch points until operator
> evidence demands them. Captured as user-feedback memory.
> (b) *Planning-open verification must cover the persistence
> path, not just the UI path* — the M25.0 (`platform`-not-
> persisted) and M25.2 (`admin/vehicles/`-not-shipped)
> empirical discoveries validated this reflex; both were caught
> before scope commit.
>
> **NEW M26 candidate surfaced at M25.3 audit regen:**
> audit-script refinement for trailing-optional-querystring
> template patterns. Two shipped UI-consumed endpoints
> (`admin/test-drives/list/` M11.6 + `admin/vehicles/` M25.2)
> currently audit as `defer-candidate-O2` due to a parser gap
> in the audit script. Reality is 116 covered / 154 total; audit
> reports 114 / 154. Small bounded fix per the "audit
> correctness as supporting infrastructure" durable principle.
>
> **SESSION_188 opens M26.0 — planning refinement + target
> selection.** No target locked yet — the candidate list
> surfaces at open (elevated: H test-hygiene [reinforced M24.1
> close], A2 JE creation UI [unchanged since M23 close], NEW
> audit-script refinement [M25.3 discovery], plus any O2 sub-
> scopes; gated: T/U/L/M; deferred pending evidence: D/C;
> deferred stable: G). The assistant recommends one option with
> rationale grounded in the primary operational-coverage lens;
> the user confirms or redirects.

## First thing SESSION_188 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches `origin/main`
  (post-push).
- `git log --oneline -10` — top should be the M25.3 close-out
  commit; `origin/main` should now be at the same head (push
  executed at M25.3 close after explicit user confirmation
  at SESSION_187).
- `python3 manage.py test dealer_ai` → **4,793 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **226 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. Monitor first M25 CI run

The M25.3 push at SESSION_187 was the first push of the M25
commits. The acceptance job fires on that `main` push —
verify its status via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as §0.a M26.0 amendments before opening
§5.a.

**If green:** M25 is CI-verified shipped; proceed to §3.

### 3. Regenerate the audit artifact

Before candidate presentation, rerun the audit tooling:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Post-M25 the audit script reports **114 / 154** covered / 40
backend-only. Reality is 116 / 154 (two false-positive
`defer-candidate-O2` classifications on M11.6
`admin/test-drives/list/` and M25.2 `admin/vehicles/` — both
consumed by shipped UI but tripped by the trailing-optional-
querystring template pattern per M25.3 §Deferrals). The
audit-script refinement is a NEW M26 candidate — if elevated,
this discrepancy resolves post-M26 shipping.

### 4. Present the M26 candidate list

Per `MILESTONE_26_PLANNING.md` skeleton (create at M25.3 close
if time permits, or draft fresh at SESSION_188 open):

**Elevated (highest recommendation strength at M26.0):**

- **Candidate H — test-hygiene remediation** (reinforced
  M24.1 close, carried unchanged through M25). Three
  shared-DB non-idempotent journeys
  (`sales_manager/daily_startup`, `recon/workflow`,
  `office/accounting_workflow`) break full-suite runs on
  state-dirty DB. Clean-DB runs pass all 14. High compound
  value for CI baseline stability as the suite grows.
  M22.§9 original scope + M23.2 session-invalidation sweep
  expansion + M24.1 close reinforcement.
- **NEW Candidate — Audit-script refinement** (M25.3
  discovery). Small bounded fix to the audit script's
  TypeScript template-literal parser so it handles
  trailing-optional-querystring patterns
  (`\`/path/${qs ? \\\`?${qs}\\\` : ""}\``). Two currently-
  false-positive `defer-candidate-O2` classifications flip
  to `covered` post-fix. Compounds every future audit read.
  Matches "audit correctness as supporting infrastructure"
  durable principle.
- **Candidate A2 — JE creation UI** (unchanged since M23
  close). Small scope; audit-verified genuine gap for
  accounting operators.

**Gated candidates:**

- **Candidate T** — process real tester feedback.
- **Candidate U** — hosted-demo substrate.
- **Candidate L** — first-live-pilot staging.
- **Candidate M** — multi-operator support. **Breaks
  zero-drift streak with intent.**

**Deferred pending evidence:**

- **Candidate D** — LLM router / cost caps.
- **Candidate C** — F&I chargeback substrate.

**Deferred but stable:**

- **Candidate G** — dashboard testid hardening.

**Deferred at M25 §4 (all valid for later re-entry):**

- Secondary "+ Record test drive" launch point on
  `DealerAiSalesTestDrives` (M25 §5.d durable — needs
  operator evidence).
- Clickable "Referred by" attribution navigation (M25 §5.c
  durable — needs operator evidence).
- Named-platform webhook adapters (Autotrader / Cars.com /
  etc.) — JSONField substrate ready.
- Attribution analytics / rollups.
- Vehicle picker advanced filters.

Present each with two-sentence scope + operator pain
resolved + dependency notes, then present the recommendation.

### 5. Recommend a target for §5.a

Ground the recommendation in the **primary operational-
coverage lens** ("which candidate most increases operational
coverage for a dealership employee?").

Elevated candidates evaluated under the lens:

- **H (test-hygiene)** — indirect operational-coverage
  delta (CI stability), but high compound value as the
  acceptance suite grows. Not operator-facing directly.
- **NEW audit-script refinement** — indirect (accuracy of
  the roadmap-planning substrate). Very small scope.
- **A2 (JE creation UI)** — direct operator-facing;
  small population (1-2 accounting users weekly) × moderate
  frequency; small scope.

Ranking under the lens: A2 > H > audit-refinement on
direct operator coverage, but H > A2 > audit-refinement on
compound infrastructure value. Judgment call for M26 —
present both framings and let the user pick.

**Alternatively:** if the M25 CI run surfaces regression
work at M26.0, address as §0.a amendments first.

### 6. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the standard six-to-eight
load-bearing decisions.

### 7. Verify BOTH intake AND downstream UI surfaces before locking §5.b + §5.d

**M24.1-open durable lesson, reinforced at M25.0 + M25.2
open.** Two M25 empirical discoveries (`platform` not
persisted; `admin/vehicles/` not shipped) validated this
reflex — both caught before scope commit. Continue at
every M26 planning-open surface verification.

### 8. DoD compliance check

Per the M21.0 §5.f amendment: the M26 active memo §3 must
either name a Playwright journey addition or extension OR
explicitly document why no journey change is required.

Note: Candidate H (test-hygiene) is an
infrastructure-focused candidate — if selected, §3 can
document the exception path (no operational journey
change; the milestone hardens existing journey seeds).

### 9. Expand M26 planning skeleton

If a skeleton exists (drafted at M25.3 close), expand at
SESSION_188. Otherwise draft fresh per the standard
active-memo shape.

### 10. Ship the M26.0 handoff

- `docs/handoffs/SESSION_188_m26_inc0_planning.md`.
- **Do NOT push** — M26.0 is planning only; coordinated
  push at M26 close.

## Non-goals for SESSION_188

- ❌ Do NOT ship any backend or frontend code — planning-
  only session.
- ❌ Do NOT open any M26 implementation increment.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M25 shipped surface.
- ❌ Do NOT modify the acceptance suite unless CI
  regression fixes land as §0.a M26.0 amendments.
- ❌ Do NOT skip the DoD compliance check.
- ❌ Do NOT skip the downstream UI surface verification
  (M24.1-open + M25.0/M25.2-open durable lesson —
  planning-open must cover the persistence path, not
  just the UI path).

## Baseline expected at close

Backend + frontend unchanged from M25 close. Acceptance
suite unchanged. Only planning docs change.

## NEXT TASK

Start SESSION_188 with (a) starting-state verification,
(b) monitor first real M25 acceptance CI run + fix any
regressions as §0.a M26.0 amendments, (c) regenerate the
audit artifact, (d) present the candidate list with
recommendation + rationale under primary operational-
coverage lens, (e) await user confirmation of §5.a, (f)
draft §5.b–§5.h with intake AND downstream UI substrate
verification per M24.1-open + M25 durable lesson, (g) DoD
compliance check on §3 draft, (h) expand the M26 planning
skeleton into a full active memo, (i) ship the M26.0
handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M25 shipped section landed at M25.3)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_25_RETROSPECTIVE.md`
   §8 (M25 corrections) + §9 (standing M26 question)
6. `docs/roadmap/MILESTONE_25_PLANNING.md`
   (M25 governing contract + M25.0 §5.b JSONField
   selection + M25.2-open admin/vehicles/ empirical
   discovery record)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit-driven scope pool — 154 endpoints /
   114 covered per script / 116 covered in reality
   with two false-positive `defer-candidate-O2`
   classifications documented in M25 §4)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25 shipped
   surface)
9. `docs/handoffs/SESSION_187_m25_inc2_test_drive_ui.md`
   (M25.2 shipped + M25.3 close-out fold)

Narrative docs are claims. Rules + research + code are
facts.

---

## Operational state (post-SESSION_187 — Milestone 25 SHIPPED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0049`. Test baseline: **4,793
  pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 226 pass** across 32 test
  files.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49
  + TS 5.6 operational; **14 journeys** passing
  end-to-end on clean DB. Full dry-run baseline:
  **20 passed (~30s)** (6 setup + 14 journeys).
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. First real
  M25 CI run triggered by the M25.3 push at
  SESSION_187 — status verified at SESSION_188
  open.
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler.
  10 scheduled task families registered.
- **Milestones shipped:** M1 → **M25**. M26
  target selection pending (SESSION_188).
- **DRF admin surface:** **114** endpoints (+1
  `admin/vehicles/` at M25.2).
- **Frontend operator routes:** 20.
- **Public endpoints:** +1 M6.5 showroom.
- **Service surface:** all M1–M25 packages
  unchanged. M25 added zero service verbs;
  `record_webhook_lead` gained one additive
  kwarg for `source_metadata`.
- **Frontend surfaces:** M25 added one component
  (`<RecordTestDriveForm>` in
  `frontend/src/components/sales/`), one API
  wrapper (`listAdminVehicles`), and two additive
  sections in `LeadDetailModal` ("Source" +
  "Schedule test drive" collapsible). No new
  routes.
- **Tenancy carriers:** 52.
- **Permission classes:** **7 actual** —
  zero-drift streak **twenty-five consecutive
  milestones** (M10 → M25).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages
  (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 25 status:** SHIPPED (SESSION_187
  close-out landed all documentation + status
  flips + M26 handoff + coordinated close-out
  commit + first M25 push).
- **Sales front-of-funnel operationally
  complete:** walk-in (M24.1) + phone (M24.2) +
  referral (M24.3) + webhook (M24.4)
  operator-side intake + assign + (M25.1) source
  attribution visible + (M25.2) schedule test
  drive through the modal. **M24.1-open §3
  deferrals 12 + 13 + 14 all closed by M25.**
- **Audit tooling:** authoritative for BHPH +
  accounting + sales intake + attribution + test-
  drive-create post-M25. Post-M25.2 audit
  discovery: two shipped UI-consumed endpoints
  (`admin/test-drives/list/` + `admin/vehicles/`)
  audit as `defer-candidate-O2` due to
  trailing-optional-querystring template parser
  gap. Documented in M25 §4; NEW M26 candidate for
  the small bounded fix.
- **§9 evidence for M26:** Candidate H (test-
  hygiene, carried unchanged from M25), Candidate
  A2 (JE creation UI, unchanged since M23 close),
  NEW audit-script refinement (M25.3 discovery,
  small bounded), plus gated T/U/L/M, deferred
  pending evidence D/C, deferred stable G, plus
  all M25 §4 deferrals recorded for later re-
  entry.
- **Planning-time streak: 3** (at M25.2 close;
  reset at M24.0 open, historical run of 89 across
  M10 → M23 preserved for the record).
- **DoD amendment (M21.0 §5.f Option B):** every
  future customer-facing milestone must add or
  update at least one Playwright operational
  journey, or explicitly document in §3 why no
  journey change is required. Applies to M26
  forward. Note: Candidate H is
  infrastructure-focused; if selected, §3 can
  document the exception path.
- **M25 audit coverage at close:** 114 / 154
  endpoints covered per script (116 / 154 in
  reality — see M25 §4 audit-script gap
  documentation).
- **Durable lessons from M25:** (a) one
  operational workflow beats two partially
  overlapping ones (M25.0 §5.d origin); (b)
  planning-open verification must cover the
  persistence path, not just the UI path (M25.0
  §5.b + M25.2 §5.e origin); (c) additive-forever
  JSONField beats CharField for capturing adapter
  extras (M25.0 §5.b origin); (d) record
  empirical-discovery refinements honestly —
  they preserve streak integrity (M25.0 + M25.2
  origin); (e) modal-attached collapsible +
  success badge > toast for post-action
  confirmation (M25.2 origin); (f) dependency-
  injectable helpers over network mocks in unit
  tests (M25.2 origin).
