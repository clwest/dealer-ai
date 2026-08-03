---
state: active
date: 2026-08-03
last_session_shipped: SESSION_184
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
next_session: SESSION_185
next_milestone: 25
next_milestone_name: "(target selection pending — locked at M25.0 open)"
next_increment: 0
next_increment_name: "M25.0 — Planning refinement + target selection"
---

# Next session — SESSION_185 · Milestone 25 · Increment 0 (M25.0 — planning refinement + target selection)

> **Milestone 24 — Sales
> Operational Entry — SHIPPED
> at SESSION_184.** Five-
> increment milestone across
> SESSION_180 → SESSION_184
> (M24.4 folded into M24.5
> close-out per §5.h Option B
> evidence-sized collapse
> posture). **Backend
> baseline 4,780 (unchanged
> — M24 added zero backend
> logic).** Frontend Vitest
> **193 → 209 (+16 across
> LeadIntakeForm + ReferralLeadFormExtras)**.
> Acceptance suite **9 → 13
> journeys**. Full clean-DB
> dry-run: **19 passed
> (~26.8s)**.
>
> **Sales front-of-funnel
> operationally complete at
> the assign level** — walk-
> in, phone, referral all
> reach salesperson via
> Dialog CTA + shared
> `<LeadIntakeForm>` + post-
> create `LeadDetailModal`
> open + `AssignmentDropdown`
> reach. Phone additionally
> reaches follow-ups page +
> 24hr cadence creation.
> Webhook integration
> validated end-to-end via
> real `/admin/leads/webhook/`
> POST + operator handling
> in real UI.
>
> **Zero-drift permission-
> class streak extends 23 →
> 24** consecutive milestones
> (M10 → M24).
>
> **Planning-time as-
> recommended streak stayed
> at 0** through M24 close
> — two mid-milestone
> planning corrections
> (M24.0 webhook posture
> redirect + M24.1-open
> downstream-verb UI
> substrate revision) both
> recorded honestly rather
> than reclassified.
> Historical run of 89
> across fourteen
> consecutive milestones
> (M10 → M23) preserved for
> the record; new counter
> begins fresh at M25.0.
>
> **First M24 push executed
> at M24.5** — all M24
> commits surface to
> `origin/main` in one
> coordinated push per
> M18/M19/M20/M21/M22/M23
> cadence. **First real M24
> CI run fires on that
> push — verify status at
> M25.0 open.**
>
> **NEW audit-verified
> genuine gaps surfaced at
> M24.1 open:** three §3
> deferrals added — test-
> drive UI (§3-12),
> referrer_id display in
> modal (§3-13), platform
> display in modal for
> webhook-origin leads
> (§3-14). All three are
> elevated M25 candidates
> (A4 + A3 respectively).
>
> **Test-hygiene Candidate H
> reinforcement** at M24.1
> close: three pre-existing
> shared-DB non-idempotent
> journeys break full-suite
> runs on state-dirty DB.
> Clean-DB runs pass all.
> Elevated as M25 candidate.
>
> **SESSION_185 opens M25.0
> — planning refinement +
> target selection.** No
> target locked yet — the
> candidate list surfaces at
> open (elevated: A3 [Lead
> source attribution display
> bundle, NEW at M24.1-
> open], A4 [RecordTestDriveForm
> UI, NEW at M24.1-open], H
> [test-hygiene, reinforced
> at M24.1 close], A2 [JE
> creation UI, unchanged];
> plus O2 sub-scopes;
> gated: T/U/L/M; deferred
> pending evidence: D/C;
> deferred stable: G). The
> assistant recommends one
> option with rationale
> grounded in the primary
> operational-coverage
> lens; the user confirms
> or redirects.

## First thing SESSION_185 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -8` —
  top should be the M24.5
  close-out commit;
  `origin/main` should now
  be at the same head
  (push executed at
  M24.5).
- `python3 manage.py test dealer_ai`
  → **4,780 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test`
  → **209 pass**.
- `python3 manage.py check`
  clean.
- `python3 manage.py
  makemigrations --check
  --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc
  --noEmit` clean.
- `cd acceptance && npx
  tsc --noEmit` clean.
- `redis-cli ping` →
  `PONG`.

### 2. Monitor first M24 CI run

The M24.5 push at
SESSION_184 was the first
push of the M24 commits.
The acceptance job fires
on that `main` push —
verify its status via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as
§0.a M25.0 amendments
before opening §5.a.

**If green:** M24 is CI-
verified shipped; proceed
to §3.

### 3. Regenerate the audit artifact

Before candidate
presentation, rerun the
audit tooling:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Post-M23.1 fix the audit
is trustworthy for BHPH +
accounting. Post-M24
should reflect the four
sales intake endpoints as
`covered` now (walk_in /
phone / referral wrappers
consumed by M24.1/2/3
UI; webhook endpoint
exercised by M24.4
journey via real POST —
but audit is UI-consumer
based so webhook remains
wrapper-only per the
M24.4 no-operator-UI
design decision).

### 4. Present the M25 candidate list

Per
`docs/roadmap/MILESTONE_25_PLANNING.md`
skeleton (§Candidate
list):

**Elevated (highest
recommendation strength
at M25.0):**

- **Candidate A3 — Lead
  source attribution
  display bundle (NEW at
  M24.1 open).** Bundles
  §3 deferrals 13 + 14.
  Small UI extensions to
  `LeadDetailModal` for
  `referrer` display +
  `platform` display for
  webhook-origin leads.
  **Highest per-item
  operational-coverage
  delta at smallest
  scope** — leads the
  operational-coverage-
  lens ranking. Every
  referral/webhook lead
  the salesperson opens
  is a moment where the
  gap surfaces.
- **Candidate A4 —
  RecordTestDriveForm UI
  (NEW at M24.1 open).**
  §3 deferral 12.
  Completes the M24.1
  walk-in journey's
  original operational-
  entry story (create →
  assign → schedule test
  drive as intended
  before the M24.1
  substrate
  verification). Matches
  M24.1 substrate
  pattern.
- **Candidate H — test-
  hygiene remediation
  (reinforced at M24.1
  close).** Extends three
  affected seeds with
  cleanup; sweeps
  session-invalidation
  `set_password` pattern
  + non-idempotent
  assertions across
  other seeds. Enables
  stable full-suite
  baseline on state-
  dirty DB.
- **Candidate A2 — JE
  creation UI (unchanged
  since M23 close).**
  Small scope; smallest
  per-item delta of the
  elevated candidates
  but still real gap.

**Gated candidates:**

- **Candidate T** —
  process real tester
  feedback.
- **Candidate U** —
  hosted-demo substrate.
- **Candidate L** —
  first-live-pilot
  staging.
- **Candidate M** —
  multi-operator
  support. **Breaks
  zero-drift streak
  with intent.**

**Deferred pending
evidence:**

- **Candidate D** — LLM
  router / cost caps.
- **Candidate C** — F&I
  chargeback substrate.

**Deferred but stable:**

- **Candidate G** —
  dashboard testid
  hardening.

Present each with two-
sentence scope + operator
pain resolved + dependency
notes, then present the
recommendation.

### 5. Recommend a target for §5.a

Ground the recommendation
in the **primary
operational-coverage lens**
("which candidate most
increases operational
coverage for a dealership
employee?"). Suggested
ranking from M24 §9
retrospective: A3 > A4 >
H > A2.

Additional considerations:

- Whether A3 + A4 fit as
  a "sales UI
  completeness" bundle
  milestone.
- Operator pain resolved.
- Dependencies on shipped
  substrate.
- Whether the M24 CI run
  surfaced any
  operational friction
  that reshuffles
  priority.

### 6. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft
the standard six-to-
eight load-bearing
decisions.

### 7. Verify BOTH intake AND downstream UI surfaces before locking §5.b + §5.d

**New durable lesson
from M24.1 open** —
mandatory M25+ planning-
open checklist item.
Failing to verify the
downstream verb UI
substrate is what caused
the M24.1-open
correction. M25 planning
must not repeat that
mistake.

### 8. DoD compliance check

Per the M21.0 §5.f
amendment: the M25
active memo §3 must
either name a Playwright
journey addition or
extension OR explicitly
document why no journey
change is required.

### 9. Expand M25 planning skeleton

`MILESTONE_25_PLANNING.md`
exists as a draft
skeleton. SESSION_185
expands to full active
memo per the standard
shape.

### 10. Ship the M25.0 handoff

- `docs/handoffs/SESSION_185_m25_inc0_planning.md`.
- **Do NOT push** — M25.0
  is planning only;
  coordinated push at M25
  close.

## Non-goals for SESSION_185

- ❌ Do NOT ship any
  backend or frontend
  code — planning-only
  session.
- ❌ Do NOT open any M25
  implementation
  increment.
- ❌ Do NOT force-push or
  amend earlier commits.
- ❌ Do NOT modify M1–M24
  shipped surface.
- ❌ Do NOT modify the
  acceptance suite unless
  CI regression fixes
  land as §0.a M25.0
  amendments.
- ❌ Do NOT skip the DoD
  compliance check.
- ❌ Do NOT skip the
  downstream-verb UI
  substrate verification
  (M24.1-open durable
  lesson).

## Baseline expected at close

Backend + frontend
unchanged from M24 close.
Acceptance suite
unchanged. Only planning
docs change.

## NEXT TASK

Start SESSION_185 with
(a) starting-state
verification, (b)
monitor first real M24
acceptance CI run + fix
any regressions as §0.a
M25.0 amendments, (c)
regenerate the audit
artifact, (d) present
the candidate list with
recommendation +
rationale under primary
operational-coverage
lens, (e) await user
confirmation of §5.a,
(f) draft §5.b–§5.h
with intake AND
downstream UI substrate
verification per M24.1-
open durable lesson,
(g) DoD compliance
check on §3 draft, (h)
expand the M25 planning
skeleton into a full
active memo, (i) ship
the M25.0 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M24 shipped section
   landed at M24.5)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_25_PLANNING.md`
   (skeleton — expanded
   at SESSION_185)
6. `docs/roadmap/MILESTONE_24_RETROSPECTIVE.md`
   §8 (M24 corrections)
   + §9 (standing M25
   question)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit-driven scope
   pool — authoritative
   for BHPH + accounting
   post-M23.1; sales
   intake post-M24)
8. `docs/roadmap/MILESTONE_24_PLANNING.md`
   (M24 governing
   contract + M24.1-open
   correction record)
9. `docs/CAPABILITY_MATRIX.md`
   §7y (M24 shipped
   surface)
10. `docs/handoffs/SESSION_184_m24_inc4_5_webhook_and_close.md`
    (M24 shipped)

Narrative docs are
claims. Rules +
research + code are
facts.

---

## Operational state (post-SESSION_184 — Milestone 24 SHIPPED)

- **Backend (local):**
  Django on `:8001`.
  Migrations
  `0001`–`0048`. Test
  baseline: **4,780
  pass**, 1 skipped, 0
  fail.
- **Backend (prod):**
  NOT active.
- **Frontend (local):**
  Vite on `:5173`.
  `tsc --noEmit` +
  `vite build` clean.
  **Vitest baseline:
  209 pass**.
- **Frontend (prod):**
  NONE.
- **Acceptance workspace
  (local):** Playwright
  1.49 + TS 5.6
  operational; **13
  journeys** passing
  end-to-end on clean
  DB. Full dry-run
  baseline: **19 passed
  (~26.8s)** (6 setup +
  13 journeys).
- **Acceptance (CI):**
  live on
  `.github/workflows/acceptance.yml`.
  First real M24 CI
  run triggered by the
  M24.5 push at
  SESSION_184 — status
  verified at
  SESSION_185 open.
- **Async runtime:**
  Celery 5.5.3 + Redis
  6.4.0 +
  `django-celery-beat`
  2.8.1
  DatabaseScheduler. **10
  scheduled task
  families
  registered**.
- **Milestones shipped:**
  M1 → **M24**. M25
  target selection
  pending (SESSION_185).
- **DRF admin surface:**
  **113** endpoints.
- **Frontend operator
  routes:** **20**.
- **Public endpoints:**
  +1 M6.5 showroom.
- **Service surface:**
  all M1–M24 packages
  unchanged. M24 added
  zero service verbs.
- **Frontend surfaces:**
  M24 added two
  components
  (`<LeadIntakeForm>` +
  `<ReferralLeadFormExtras>`)
  in
  `frontend/src/components/sales/`.
  Three Dialog CTAs on
  `DealerAiSalesLeads.tsx`
  (`+ Walk-in`, `+ Phone`,
  `+ Referral`).
  `LeadDetailModal` +
  `AssignmentDropdown`
  wired into
  `DealerAiSalesLeads.tsx`
  as M24.1 in-scope
  extension. No new
  routes.
- **Tenancy carriers:**
  **52**.
- **Permission
  classes:** **7
  actual** — zero-drift
  streak **twenty-four
  consecutive
  milestones** (M10 →
  M24).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:**
  17 scrub stages
  (unchanged).
- **Deterministic
  rules:** unchanged.
- **Milestone 24
  status:** SHIPPED
  (SESSION_184 close-
  out landed all
  documentation +
  status flips + M25
  skeleton +
  coordinated close-
  out commit + first
  M24 push).
- **Sales front-of-
  funnel operationally
  complete:** walk-in
  (M24.1) + phone
  (M24.2) + referral
  (M24.3) operator UI-
  native intake +
  reachable end-to-end
  through sales-side
  leads page + post-
  create modal +
  assignment (+
  cadence for phone; +
  referrer FK backend
  attribution for
  referral); webhook
  (M24.4) integration-
  to-operator flow
  validated via real
  endpoint POST + real
  UI handling.
- **Audit tooling:**
  authoritative for
  BHPH + accounting +
  sales intake post-
  M24. Rerun at M25.0
  open to reflect any
  drift.
- **§9 evidence for
  M25:** Candidate A3
  (Lead source
  attribution display
  bundle, NEW at
  M24.1 open —
  highest per-item
  operational-coverage
  delta under primary
  lens), Candidate A4
  (RecordTestDriveForm
  UI, NEW at M24.1
  open — completes
  M24.1 walk-in
  journey's original
  operational-entry
  story), Candidate H
  (test-hygiene,
  reinforced at M24.1
  close — enables
  stable full-suite
  baseline), Candidate
  A2 (JE creation UI,
  unchanged since M23
  close — small scope,
  audit-verified
  genuine gap).
- **Planning-time
  streak: 0** (RESET
  at M24.0 open;
  stayed at 0 through
  M24.1-open
  correction).
  Historical run: 89
  across fourteen
  consecutive
  milestones (M10 →
  M23). Preserved for
  the record. New
  counter begins
  fresh at M25.0.
- **DoD amendment
  (M21.0 §5.f Option
  B):** every future
  customer-facing
  milestone must add
  or update at least
  one Playwright
  operational journey,
  or explicitly
  document in §3 why
  no journey change
  is required.
  Applies to M25
  forward.
- **M24 audit coverage
  at close:** 110 / 153
  endpoints covered
  post-M24 (walk-in +
  phone + referral
  wrappers now
  consumed by UI;
  webhook remains
  wrapper-only per
  M24 no-operator-UI
  design decision).
  Audit rerun at
  M25.0 open will
  reflect the delta.
- **Durable lessons
  from M24:** (a)
  planning-open
  verification must
  cover both intake
  AND downstream UI
  surfaces before
  locking §5.b + §5.d
  (M24.1-open origin);
  (b) record planning
  redirects honestly
  — streak integrity
  beats streak count
  (M24.0 + M24.1
  origin).
