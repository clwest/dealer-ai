---
state: active
date: 2026-08-03
last_session_shipped: SESSION_178
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
milestone_23_status: in-progress
next_session: SESSION_179
next_milestone: 23
next_milestone_name: "BHPH Origination + Payment Intake"
next_increment: 4
next_increment_name: "M23.4 — CI hardening + retrospective + close-out"
---

# Next session — SESSION_179 · Milestone 23 · Increment 4 (M23.4 — close-out)

> **Milestone 23 · Increment 3 —
> Payment intake UI + journey —
> SHIPPED at SESSION_178.** New
> `createBhphPayment` wrapper +
> `RecordBhphPaymentForm` inline
> in the existing Payments card
> + seed extension +
> `expectBhphPaymentRecorded`
> helper +
> `bhph/payment_intake.spec.ts`
> journey. Backend baseline
> **4,773 → 4,780 (+7)** seed
> tests. Frontend Vitest **187
> → 193 (+6)** form tests.
> Acceptance suite **8 → 9**
> journeys. Full clean-DB dry-
> run: **15 passed @ 20.3s**.
> **First-run pass — no §5.d
> fixes required** (sibling
> pattern + inherited M23.2
> lessons).
>
> **M23 anchor UIs complete.**
> Both bookends (origination +
> payment intake) ship with
> Playwright validation.
> BHPH lifecycle now
> operationally complete
> through the product.
>
> **Planning-time as-recommended
> streak still 89 across
> fourteen consecutive
> milestones**. **Zero-drift
> permission-class streak
> target at M23.4 close: 22
> → 23**.
>
> **SESSION_179 opens M23.4 —
> close-out.** CI validation +
> CAPABILITY_MATRIX §7x +
> retrospective + M24 planning
> skeleton + coordinated close-
> out commit + first M23 push
> per M18.6/M19.6/M20.5/M21.5/M22.4
> cadence.

## First thing SESSION_179 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  four should be M23.3 close,
  M23.2 close, M23.1 close,
  M23.0 close; `origin/main`
  still at the M22 durable-
  lessons head (M23 has not
  pushed).
- `python3 manage.py test dealer_ai`
  → **4,780 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **193 pass**.
- `python3 manage.py check`
  clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc
  --noEmit` clean.
- `cd acceptance && npx tsc
  --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. Reset acceptance DB + full-suite clean dry-run

To match the M18.6/M19.6/M20.5
/M21.5/M22.4 close-out pattern,
verify the full acceptance
suite passes on clean-DB state:

```bash
rm backend/db.acceptance.sqlite3
cd acceptance
npx playwright test
```

Expected: **15 passed (~20s)**
(6 setup + 9 journeys).

If any journey fails on clean
DB, address as §0.a M23.4
amendment before advancing to
close-out documentation.

### 3. Update CAPABILITY_MATRIX.md §7x — M23 shipped surface

Add a new §7x section covering:

- **Audit tooling correction
  (M23.1)** — HTTP-verb-agnostic
  URL-prefix matching false-
  positive class closed via
  targeted regex + parser
  enhancement. Coverage 110 →
  108 (row 123 + row 139
  reclassified genuinely
  backend-only). Reveals JE
  creation UI as previously-
  hidden gap for M24
  consideration.
- **BHPH note origination
  (M23.2)** — `createBhphNote`
  wrapper + `RecordBhphNoteForm`
  + `DealerAiBhphPortfolio` CTA
  + Dialog + seed extension +
  `expectBhphNoteOriginated`
  helper + Playwright journey.
- **BHPH payment intake
  (M23.3)** — `createBhphPayment`
  wrapper + `RecordBhphPaymentForm`
  inline in Payments card +
  seed extension +
  `expectBhphPaymentRecorded`
  helper + Playwright journey.
- **§5.d in-scope fix
  (M23.2)** — session-
  invalidation bug in
  `_provision_collector` fixed
  by wrapping `set_password`
  in `if created:` guard.
- **Milestone deltas:**
  Backend 4,766 → 4,780 (+14).
  Frontend Vitest 180 → 193
  (+13). Acceptance suite
  7 → 9 journeys.

Follow existing §7v / §7w
formatting for consistency.

### 4. Author docs/roadmap/MILESTONE_23_RETROSPECTIVE.md

Mirror the
`MILESTONE_22_RETROSPECTIVE.md`
structure. Nine sections:

- **§1 Planned scope** —
  Candidate O2 (BHPH note
  origination + payment
  intake sub-scope) confirmed
  at M23.0 open per
  operational-coverage lens.
  Eight §5 decisions resolved
  as-recommended. Cross-
  milestone pattern: M23
  inherits M21 Candidate O
  UI-creation contract (vs
  M22's validation-shape
  refinement).
- **§2 What actually shipped**
  — 5 increments across 5
  sessions (SESSION_175 →
  SESSION_179). All planned
  increments shipped; no
  scope changes. Different
  from M22 (M22.3 skipped)
  and M21 (M21.4 skipped) —
  M23 shape matched the
  planned 5-increment
  target exactly.
- **§3 Deviations vs.
  planning memo** — none
  major. Small route URL
  correction at M23.2 (memo
  pre-committed
  `/dealer-ai-bhph-portfolio`;
  actual route is
  `/dealer-ai-bhph/portfolio`).
  Sale-picker UX limitation
  surfaced but pre-cataloged
  in §3 deferral 1.
- **§4 Deferrals reviewed**
  — every M23 §3 deferral
  reviewed. New deferrals
  surfaced: JE creation UI
  (M23.1 finding), session-
  invalidation seed pattern
  in other seeds (M23.2
  finding), route URL
  discovery friction (M23.2
  finding).
- **§5 Lessons learned** —
  candidate lessons:
  (a) empirical verification
  at each M23.N open
  successfully validated
  memory-guided planning
  discipline; (b) audit
  correctness compounds
  (M22.1 + M23.1 patterns
  reinforce that bounded
  audit fixes are worth the
  budget); (c) sibling-
  pattern discipline
  eliminates journey-
  authoring gaps (M23.3
  first-run pass vs M23.2's
  one §5.d fix); (d) new
  journey patterns surface
  latent bugs that inherited
  fixes then prevent (session-
  invalidation pattern
  generalizes across all
  seeds); (e) route URL
  discovery is real friction
  that a generated planning
  artifact could reduce
  (memory-linked to
  "generated planning
  artifacts" from M22 close).
- **§6 Streak status** —
  Planning-time as-
  recommended **89 across
  fourteen consecutive
  milestones** (M10 → M23).
  Zero-drift permission-
  class **twenty-three
  consecutive milestones**
  (M10 → M23).
- **§7 Governing-contract
  validation** — every M23
  shipped surface satisfies
  the M21 Candidate O UI-
  creation contract.
- **§8 Unblocks / corrections
  landed** — HTTP-verb
  audit false-positive class
  closed; BHPH lifecycle
  operationally complete;
  JE creation UI gap
  surfaced.
- **§9 Standing M24 question**
  — evidence-based candidates
  from M23 close:
  (1) JE creation UI
  (revealed at M23.1 audit
  correction) — completes
  the accounting-write
  substrate started at M22
  (Candidate A continuation).
  (2) Sale picker UI /
  deep-link (M23.2 §3
  deferral 1) — small
  operator-workflow-quality
  improvement.
  (3) Session-invalidation
  seed pattern sweep — other
  seeds may have the same
  bug. Small future-work
  cluster.
  (4) Route URL discovery
  friction — candidate for
  a "generated planning
  artifact" experiment per
  M22 durable-lesson memory.
  Plus carry-forward
  candidates (H test-
  hygiene, remaining OSC
  sub-scopes, T/U/L/M
  gated).

### 5. Author docs/roadmap/MILESTONE_24_PLANNING.md skeleton

Mirror the
`MILESTONE_23_PLANNING.md`
skeleton shape at M22.4
close. Frontmatter
`status: draft` until M24.0
expansion. Candidate list
carries forward + adds M23
findings.

**New M24.0 elevated
candidates from M23 §9:**

- **Candidate A2 — JE
  creation UI** (evidence
  from M23.1). Small
  bounded scope: single
  new form + wrapper +
  journey attached to
  existing JE list page.
  Fits M21 Candidate O
  contract.
- **Candidate H — test-
  hygiene remediation**
  (unchanged from M22 §9;
  now includes session-
  invalidation seed pattern
  sweep per M23.2).

### 6. Update IMPLEMENTATION_ROADMAP.md with M23 shipped status

Add M23 section covering BHPH
Origination + Payment Intake
deliverables: audit tooling
fix + note origination UI +
payment intake UI + inherited
seed session-preservation fix.
Reference the retrospective
for detail.

### 7. Ship the M23.4 close-out commit + push

Follow the M18.6/M19.6/M20.5/M21.5/M22.4
cadence:

```bash
git add \
  00-START-NEXT-SESSION.md \
  docs/CAPABILITY_MATRIX.md \
  docs/roadmap/IMPLEMENTATION_ROADMAP.md \
  docs/roadmap/MILESTONE_23_PLANNING.md \
  docs/roadmap/MILESTONE_23_RETROSPECTIVE.md \
  docs/roadmap/MILESTONE_24_PLANNING.md \
  docs/handoffs/SESSION_179_m23_inc4_close.md
git commit -m "Milestone 23 shipped — BHPH Origination + Payment Intake (SESSION_175-179)"
git push
```

**This is the first M23 push.**
All five M23 commits (M23.0
+ M23.1 + M23.2 + M23.3 + M23.4)
surface to `origin/main`
together per coordinated
cadence.

Then **monitor the M23 CI
run**:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

If green, M23 is CI-verified
shipped. Refresh
`00-START-NEXT-SESSION.md`
for M24.0.

If red, address as §0.a M23.4
amendments before opening
M24.0.

## Non-goals for SESSION_179

- ❌ Do NOT ship any backend
  or frontend code — close-
  out is documentation +
  coordinated push only.
- ❌ Do NOT open any M24
  implementation increment.
- ❌ Do NOT force-push or
  amend the M23.0 / M23.1 /
  M23.2 / M23.3 commits.
- ❌ Do NOT modify shipped
  M1-M22 surface.
- ❌ Do NOT modify the
  acceptance suite (unless
  CI regression fixes land
  as §0.a M23.4 amendments).
- ❌ Do NOT extend M23 scope
  by pulling in future-work
  candidates — all recorded
  in retrospective §9 for
  M24+ consideration.

## Baseline expected at close

- Backend baseline: **4,780
  pass**, 1 skipped, 0 fail
  (unchanged from M23.3
  close).
- Frontend Vitest: **193
  pass** (unchanged).
- Acceptance suite: **15
  passed** on clean DB (6
  setup + 9 journeys).
- Migrations `0001`–`0048`
  unchanged.
- Tenancy carriers 52
  unchanged.
- Permission classes 7
  unchanged — **zero-drift
  streak extends 22 → 23
  consecutive milestones**
  (M10 → M23).
- DRF admin surface 113
  unchanged.
- Frontend operator routes
  20 unchanged.
- Celery-beat task families
  10 unchanged.

## NEXT TASK

Start SESSION_179 with (a)
starting-state verification,
(b) reset acceptance DB +
full-suite clean-DB dry-run
(target: 15 passed / ~20s),
(c) update CAPABILITY_MATRIX
§7x with M23 shipped surface,
(d) author
MILESTONE_23_RETROSPECTIVE.md
with §1-§9 mirroring the M22
retrospective structure, (e)
author MILESTONE_24_PLANNING.md
skeleton with candidate list
refreshed from M23 §9
findings, (f) update
IMPLEMENTATION_ROADMAP.md
with M23 shipped status, (g)
ship the SESSION_179 handoff,
(h) refresh
`00-START-NEXT-SESSION.md`
for M24.0, (i) coordinated
close-out commit + first M23
push, (j) monitor the M23 CI
run.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M22 shipped section
   landed at M22.4)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (active memo — §0.a
   M23.3 amendment records
   shipped payment intake
   + first-run pass)
6. `docs/handoffs/SESSION_178_m23_inc3_payment_intake.md`
   (M23.3 close —
   sibling-pattern discipline
   + cross-milestone pattern
   observation)
7. `docs/handoffs/SESSION_177_m23_inc2_note_origination.md`
   (M23.2 close)
8. `docs/handoffs/SESSION_176_m23_inc1_audit_fix.md`
   (M23.1 close)
9. `docs/handoffs/SESSION_175_m23_inc0_planning.md`
   (M23.0 close)
10. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
    (audit artifact —
    authoritative for BHPH
    + accounting post-M23.1)
11. `docs/CAPABILITY_MATRIX.md` §7w
    (M22 shipped surface —
    §7x lands at M23.4)

Narrative docs are claims.
Rules + research + code are
facts.

---

## Operational state (post-SESSION_178 — Milestone 23.3 payment intake UI shipped)

- **Backend (local):** Django
  on `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,780 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT
  active.
- **Frontend (local):** Vite
  on `:5173`. `tsc --noEmit`
  + `vite build` clean.
  **Vitest baseline: 193
  pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace
  (local):** Playwright 1.49
  + TS 5.6 operational;
  **nine journeys** passing
  end-to-end on clean DB.
  Full dry-run baseline:
  **15 passed (~20.3s)** (6
  setup + 9 journeys). M23.2
  added
  `bhph/note_origination.spec.ts`;
  M23.3 added
  `bhph/payment_intake.spec.ts`.
- **Acceptance (CI):** live
  on
  `.github/workflows/acceptance.yml`.
  Last verified green: run
  `30831196864` (M22 durable-
  lessons carry-forward push,
  2m3s). M23 has not pushed
  yet — coordinated push at
  M23.4.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1
  → **M22**. M23 in-progress
  (M23.0 planning + M23.1
  audit fix + M23.2
  origination + M23.3 payment
  intake shipped; M23.4
  close-out next at
  SESSION_179).
- **DRF admin surface:**
  **113** endpoints.
- **Frontend operator
  routes:** **20**.
- **Public endpoints:** +1
  M6.5 showroom.
- **Service surface:** all
  M1–M22 packages unchanged.
  M23 adds zero service
  verbs.
- **Frontend surfaces:** M23
  added `RecordBhphNoteForm`
  attached to
  `DealerAiBhphPortfolio`
  Notes card as CTA + Dialog
  (M23.2); +
  `RecordBhphPaymentForm`
  attached inline to
  `DealerAiBhphNoteDetail`
  Payments card (M23.3).
  Two new components; two
  new wrappers.
- **Tenancy carriers:**
  **52**.
- **Permission classes:**
  **7 actual** — zero-drift
  streak **twenty-two
  consecutive milestones**
  (M10 → M22). Target at
  M23.4 close: 23.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 23 status:**
  IN-PROGRESS. M23.0
  planning + M23.1 audit fix
  + M23.2 origination UI +
  M23.3 payment intake UI
  shipped. M23.4 close-out
  next.
- **BHPH lifecycle
  operationally complete:**
  M12 backend + M12.7 read
  UI + M20.4 Playwright +
  M21.2 collections write-
  side + M23.2 origination
  + M23.3 payment intake.
  All BHPH workflows now
  reachable through the
  product with Playwright
  validation.
- **Audit tooling:**
  authoritative for BHPH +
  accounting endpoints post-
  M23.1 fix. Coverage
  **108/153**. Backend-only
  **45**.
- **§9 evidence for M24**
  accumulating: JE creation
  UI (M23.1); sale picker
  UX (M23.2); session-
  invalidation seed pattern
  generalization (M23.2);
  route URL discovery
  friction (M23.2). Plus
  carry-forward from M22 §9:
  H test-hygiene, remaining
  O2 sub-scopes, T/U/L/M
  gated.
- **Planning-time streak:**
  **89 as-recommended M5.1
  → M23.0** across fourteen
  consecutive milestones (M10
  → M23).
- **DoD amendment (M21.0
  §5.f Option B):** M23
  satisfies by construction
  — M23.2 added
  `bhph/note_origination.spec.ts`;
  M23.3 added
  `bhph/payment_intake.spec.ts`.
- **M23 remaining
  increments:** M23.4 close-
  out only. Coordinated
  close-out commit + first
  M23 push per M18.6 /
  M19.6 / M20.5 / M21.5 /
  M22.4 cadence.
