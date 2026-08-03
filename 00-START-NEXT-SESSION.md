---
state: active
date: 2026-08-03
last_session_shipped: SESSION_172
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
milestone_22_status: in-progress
next_session: SESSION_173
next_milestone: 22
next_milestone_name: "Accounting Operational Validation"
next_increment: 2
next_increment_name: "M22.2 — JE reversal journey + seed extension"
---

# Next session — SESSION_173 · Milestone 22 · Increment 2 (M22.2 — JE reversal journey + seed extension)

> **Milestone 22 · Increment 1 —
> Audit tooling correction — SHIPPED
> at SESSION_172.** Targeted three-
> change fix to
> `audit_operational_surface.py`
> reclassified all four accounting
> endpoints from §0.a M22.0
> discovery. Coverage 106 → 110
> (+4); backend-only 47 → 43 (-4).
> Root-cause reframe: not just
> "nested template literals" — the
> actual class is **variable-first
> URL assembly** where wrappers
> pass a `const path` identifier
> to `authGetJSON(path)` instead
> of a literal. Budget guard held
> — ~30-40 min of active work,
> well under the ~2-hour §5.e
> guard.
>
> **Backend baseline unchanged at
> 4,761 pass.** Zero regressions
> verified via full test suite
> post-fix.
>
> **SESSION_173 opens M22.2 — the
> first anchor journey.** JE
> reversal end-to-end via
> Playwright, seed fixture
> extension, business-outcome
> assertion helper. Concurrent
> §5.b page/persona walk during
> authoring feeds the M22.3
> scope decision.
>
> **DoD compliance satisfied by
> construction** for M22.2 — the
> new
> `office/accounting_je_reversal.spec.ts`
> journey directly satisfies the
> M21.0 §5.f Option B amendment.

## First thing SESSION_173 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  should be the M22.1 close
  commit; `origin/main` still at
  the M21.5 shipped head (M22 has
  not pushed).
- `python3 manage.py test dealer_ai`
  → **4,761 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` → **180
  pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `cd acceptance && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Extend the accounting seed

Extend
`backend/dealer_ai/management/commands/seed_journey_office_accounting_workflow.py`
with a **reversible-JE fixture**:

- Post a second balanced journal
  entry (distinct from the M20.3
  trial-balance fixture) that the
  reversal journey can target.
- Stable description tag —
  suggested
  `[M22.2-office-je-reversal] Fixture entry the M22 reversal journey posts a reversal against.`
  — for idempotent detection +
  reuse per the existing seed's
  M20.3 pattern.
- Tenant-scope to the default
  dealership per the existing
  seed pattern (uses
  `get_default_dealership()`).
- Use `post_journal_entry` service
  verb via
  `JournalLineInput` — no
  parallel write paths.

Add a backend test covering
idempotency + tenant scoping per
the M20/M21 seed test precedent.

### 3. Extend the accounting assertion helper

Extend
`acceptance/support/assertions/accounting.ts`
with `expectJournalEntryReversed`:

```typescript
export async function expectJournalEntryReversed(
  request: APIRequestContext,
  originalId: number,
): Promise<void> {
  // Fetch the JE list; find an entry whose reverses_id === originalId.
  // Assert:
  //   - reversal exists
  //   - reversal's lines are the sign-flipped mirror of the original
  //   - reversal.reverses_id === originalId
  //   - reversal.reason is non-empty
}
```

Use the existing
`fetchJournalEntries` /
`fetchJournalEntry` accountingApi
wrappers if the helper file can
import them; otherwise use the
raw admin API endpoints via
`request.get(...)`.

### 4. Author the JE reversal journey

New file:
`acceptance/journeys/office/accounting_je_reversal.spec.ts`.

Walk:
1. Owner (acceptance-owner persona
   provisioned by
   `seed_journey_owner_morning_review`)
   navigates to
   `/dealer-ai-accounting/journal-entries/<id>`
   where `<id>` is the seeded
   reversible JE.
2. Verify JE detail page renders
   with the entry's metadata + line
   breakdown.
3. Click "Reverse this entry"
   button — dialog opens.
4. Fill reason textarea with
   `"M22 acceptance journey — reversal test"`.
5. Click "Confirm reversal" —
   status message appears.
6. Verify page reload shows the
   original entry now has a
   reversal-linkage indicator (or
   navigate to the JE list and
   verify the reversal appears
   with `Reversal of #<id>` badge).
7. Business-outcome assertion via
   `expectJournalEntryReversed(request, originalId)`.

Follow the fail-loud contract per
M20 §0 — journey test name
identifies the operational
workflow; failure messages target
the business outcome that failed;
screenshots + traces attach on
failure per the M20 CI job config.

### 5. Concurrent §5.b page/persona walk

While authoring the journey, walk
the three shipped accounting
pages from the office-manager
persona perspective:

- **`AccountingTrialBalancePage`
  (`/dealer-ai-accounting/trial-balance`)**
  — freeze journey exists (M20.3).
  Any distinct workflows not
  covered? (as-of picker
  interaction, cost-posting
  failures rendering path).
- **`AccountingJournalEntriesPage`
  (`/dealer-ai-accounting/journal-entries`)**
  — list navigation + drill-in
  to detail. Distinct enough from
  the reversal journey's implicit
  navigation to warrant its own
  journey?
- **`AccountingJournalEntryDetailPage`
  (`/dealer-ai-accounting/journal-entries/:pk`)**
  — covered by reversal journey.
  Any other affordances?

Document findings in the M22.2
handoff. Findings feed the M22.3
scope decision:

- **Zero additional workflows
  warrant journeys** → M22.3
  SKIPPED per §5.h Option B;
  M22.4 close-out becomes
  SESSION_174.
- **One or more additional
  workflows** → M22.3 authors
  those journeys as separate
  sibling spec files per §5.c
  Option B; M22.4 becomes
  SESSION_175 (or later).

### 6. Small operator-surface gap fixes per §5.d

If journey authoring reveals a
one-file trivial change is needed
to make the workflow completable
(missing testid at an insertion
point, broken link, label typo,
form validation bug), fix it
in-scope with a §0.a M22.2
amendment recording the fix.

If a larger gap surfaces (missing
form, missing wrapper, missing
service verb, new UI structure),
DO NOT fix in-scope. Document as
future accounting candidate
evidence in the M22.2 handoff for
inclusion in the M22.4
retrospective §9.

### 7. Verify journey passes locally

Before shipping the handoff, run:

```bash
cd acceptance
npx playwright test office/accounting_je_reversal.spec.ts --project=chromium
```

Full-suite dry-run recommended
before M22.4 close, but per-
journey verification at M22.2 is
sufficient.

### 8. Ship the M22.2 handoff

- `docs/handoffs/SESSION_173_m22_inc2_je_reversal.md`.
- Overwrite `00-START-NEXT-SESSION.md`
  with M22.3 priority (if
  additional journeys surfaced)
  or M22.4 priority (if walk
  surfaced no additional
  journeys — SKIP M22.3 per §5.h
  Option B).
- **Do NOT push** — M22 uses
  coordinated close-out push per
  M18.6 / M19.6 / M20.5 / M21.5
  cadence at M22.4.

## Non-goals for SESSION_173

- ❌ Do NOT ship new UI components
  or wrappers (rebuilding what
  already ships from M14/M17).
- ❌ Do NOT add new backend service
  verbs, DRF endpoints, tenancy
  carriers, migrations, permission
  classes, or frontend routes.
- ❌ Do NOT rewrite the audit
  script further — M22.1 shipped
  the targeted fix per §5.e
  Option B budget guard.
- ❌ Do NOT manually verify the
  reversal workflow before
  authoring the journey —
  journey-as-verifier per §5.f
  Option B.
- ❌ Do NOT force-scope additional
  journeys into M22.2 —
  concurrent §5.b walk documents
  candidates; M22.3 authors any
  additional journeys.
- ❌ Do NOT split the accounting
  seed into per-workflow seeds —
  extend additively per §5.g
  Option A.
- ❌ Do NOT push M22.2 commits.

## Baseline expected at close

- Backend baseline: 4,761 →
  **~4,763** (seed fixture
  idempotency tests).
- Frontend Vitest: 180 (unchanged
  unless §5.d fixes add cases).
- Acceptance suite: **6 → 7**
  (JE reversal journey added).
- Migrations `0001`–`0048`
  unchanged.
- Tenancy carriers 52 unchanged.
- Permission classes 7 unchanged
  (zero-drift streak intact).

## NEXT TASK

Start SESSION_173 with (a)
starting-state verification, (b)
extend the accounting seed with
a reversible-JE fixture + backend
idempotency test, (c) extend the
accounting assertion helper with
`expectJournalEntryReversed`, (d)
author the JE reversal Playwright
journey walking dialog interaction
+ business-outcome assertion, (e)
concurrent §5.b page/persona walk
to identify M22.3 scope, (f)
apply small operator-surface gap
fixes per §5.d if any surfaced,
(g) verify journey passes locally,
(h) ship the M22.2 handoff + refresh
`00-START-NEXT-SESSION.md` for
M22.3 or M22.4. Do NOT push.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M21 shipped + DoD amendment
   landed at M21.5)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_22_PLANNING.md`
   (active memo — §0.a M22.1
   amendment records shipped audit
   fix)
6. `docs/handoffs/SESSION_172_m22_inc1_audit_correction.md`
   (M22.1 close — audit correction
   root-cause reframe + shipped
   changes)
7. `docs/handoffs/SESSION_171_m22_inc0_planning.md`
   (M22.0 close — empirical
   discovery record)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact — now
   authoritative for accounting
   post-M22.1 fix)
9. `acceptance/journeys/office/accounting_workflow.spec.ts`
   (existing M20.3 trial-balance
   freeze journey — pattern
   reference for M22.2 authoring)
10. `docs/CAPABILITY_MATRIX.md` §7v
    (M21 shipped surface)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_172 — Milestone 22.1 audit correction shipped)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,761 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 180 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace
  (local):** Playwright 1.49 +
  TS 5.6 operational; **six
  journeys** passing end-to-end.
  Full dry-run baseline: **12
  passed (~18s)**. M22.2 will
  grow to 7 journeys.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`.
  Last verified green: run
  `30822664811` (M21.5 push,
  2m3s). M22 has not pushed yet
  — coordinated push at M22.4.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  **M21**. M22 in-progress
  (M22.0 planning shipped;
  M22.1 audit correction
  shipped; M22.2 next at
  SESSION_173).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all
  M1–M21 packages unchanged.
  M22 adds zero service verbs.
- **Frontend surfaces:** three
  shipped accounting pages
  (`AccountingTrialBalancePage`,
  `AccountingJournalEntriesPage`,
  `AccountingJournalEntryDetailPage`)
  from M14 + M17.2 snapshot
  lifecycle + M21 BHPH/sales
  extensions. M22 adds zero
  new components.
- **Tenancy carriers:** **52**.
- **Permission classes:** **7
  actual** — zero-drift streak
  **twenty-one consecutive
  milestones** (M10 → M21).
  Target at M22 close: 22.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 22 status:** IN-
  PROGRESS. M22.0 planning +
  M22.1 audit correction
  shipped. M22.2 anchor journey
  next.
- **Audit tooling:**
  authoritative for accounting
  endpoints post-M22.1 fix. All
  four M22.0-identified
  misclassifications
  reclassified to `covered`.
  Regex + parser enhancements
  in
  `backend/dealer_ai/scripts/audit_operational_surface.py`
  handle variable-first URL
  assembly + nested template
  literals correctly.
- **Audit artifact:** current at
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`.
  Coverage **110/153**. Backend-
  only **43**. Trusted source
  material for M22.2+ journey
  authoring + future OSC
  candidate selection.
- **Planning-time streak:** **88
  as-recommended M5.1 → M22.0**
  across thirteen consecutive
  milestones (M10 → M22).
- **DoD amendment (M21.0 §5.f
  Option B):** M22 satisfies by
  construction — every
  implementation increment adds
  a Playwright operational
  journey. M22.2 will add
  `office/accounting_je_reversal.spec.ts`.
- **M22 governing contract:**
  (1) maps to shipped frontend
  surface + shipped backend
  capability; (2) establishes
  operational-completion
  evidence through Playwright
  end-to-end journey; (3) uses
  journey-as-verifier; (4)
  splits discovered gaps by
  size — small in-scope fix vs.
  large deferred as next
  candidate evidence.
- **M22 remaining increments:**
  M22.2 JE reversal journey +
  seed extension (first anchor,
  SESSION_173); M22.3
  additional journeys per §5.b
  enumeration (conditional,
  SESSION_174 if any); M22.4
  close-out (SESSION_174 or
  SESSION_175 depending on
  M22.3).
