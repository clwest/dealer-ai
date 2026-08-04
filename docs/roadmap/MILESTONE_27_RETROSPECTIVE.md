---
title: "Milestone 27 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-03
sessions: SESSION_191 → SESSION_192 → SESSION_193
milestone: 27
milestone_name: "Journal-Entry Creation UI (via shared GLAccount substrate)"
related:
  - docs/roadmap/MILESTONE_27_PLANNING.md
  - docs/roadmap/MILESTONE_26_RETROSPECTIVE.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7β
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 27
---

# Milestone 27 — Retrospective

Written at Milestone 27 close (SESSION_193, close-out folded into
M27.2 per §5.h evidence-sized Option B — both increments' §5.e
Phase 1 + Phase 2 verifications passed cleanly on the first
regeneration). Records what was planned, what shipped, what
deviated and why, and lessons carried forward for Milestone 28.
Mirrors `MILESTONE_26_RETROSPECTIVE.md` shape.

## 1. Planned scope

`MILESTONE_27_PLANNING.md` at SESSION_191 (M27.0 open) defined
the milestone as **Journal-Entry Creation UI (A2)** under the
primary operational-coverage lens (durable per M22 close). The
AI's independent recommendation was A2 after four alternatives
(A2 direct operator coverage, O2 row-5 public-fetch-helper regex,
O3 rows-1–4 plain-string investigation, H test-hygiene) were
presented under two framings (primary operational-coverage vs.
M26 substrate-integrity reframe). §7 verification then surfaced
the GLAccount FK intake gap and drove the two-increment split.

**Locked scope shape:**

- **M27.0** — planning refinement + all §5 locks. No code, no push.
- **M27.1** — backend substrate: `GET admin/accounting/gl-accounts/`
  + `fetchGLAccounts` wrapper. DoD exception path per M21.0 §5.f
  Option B (M26 precedent).
- **M27.2** — JE-create dialog on existing JE list page +
  `GLAccountPicker` + `createJournalEntry` wrapper + Playwright
  journey with two test cases (successful create + cancel-
  without-persistence).
- **M27.3** — close-out. Fold into M27.2 per §5.h Option B unless
  §5.e discrepancies force a split.

**Locked non-goals:** standalone Chart of Accounts page /
route / navigation entry; Trial Balance changes; JE edit / update;
JE templates / recurring journals; `posted_by_user` override;
advanced picker filtering; server-side search / pagination on
gl-accounts; row-5 (O2) / rows-1–4 (O3) audit refinement; H
test-hygiene remediation.

## 2. What actually shipped

Milestone shipped exactly as planned across three sessions
(SESSION_191 → SESSION_193), close-out folded into M27.2 per
§5.h Option B.

### M27.0 — planning refinement (SESSION_191)

Standard planning-only session. All §5 decisions locked. Full
active memo authored at `MILESTONE_27_PLANNING.md`. Handoff at
`docs/handoffs/SESSION_191_m27_inc0_planning.md` (commit
`4641eaa` + hash backfill `c7d9e21`).

**Key discovery at §7:** the `admin/accounting/journal-entries/`
create endpoint requires numeric `account_id` values, but the
frontend had zero GLAccount discovery infrastructure — no list
endpoint, no wrapper, no picker component. Trial Balance was
examined and rejected as a substrate (activity-filtered + no
`id` in projection). Per user direction, split into two
increments and attach the dialog to the existing JE list page
rather than shipping a standalone CoA route.

**Durable planning lesson recorded to memory:** *before locking
any create/edit workflow, verify every required foreign key or
identifier is discoverable and selectable by the operator
through a truthful product surface.* Saved to
`memory/feedback_verify_fk_discoverability_before_lock.md`.

### M27.1 — backend substrate + frontend wrapper (SESSION_192)

- **Backend:** `admin_gl_account_list` view added to
  `views_accounting.py` — DRF `@api_view(["GET"])`,
  `_M131_PERMS`, tenant-scoped, returns active CoA
  (`is_active=True`) sorted by `code` ASC. Response envelope
  follows the `cost_posting_failures` precedent
  (`{"gl_accounts": {"accounts": [{id, code, name, type}, ...]}}`).
  `is_active=False` accounts filtered out by design per the
  M13.1 GLAccount contract.
- **Route:** wired at `urls.py` as `admin-gl-account-list`.
- **Backend tests:** 8 methods across 1 class in
  `test_m27_gl_account_list.py` (envelope shape, sort order,
  projection fields, zero-balance inclusion, soft-hidden
  exclusion, cross-tenant isolation, advisor 403,
  unauthenticated rejection).
- **Frontend:** `GLAccount` type + `GLAccountListResponse`
  interface + `fetchGLAccounts` wrapper added to
  `accountingApi.ts`. Reuses the existing `GLAccountType`
  alias — no duplicate declaration.
- **No UI change.** DoD exception path invoked per §5.g.
- **Audit at M27.1 close:** 154 → 155 endpoints / 119 covered /
  35 → 36 backend-only. New row 149 disposition
  `defer-candidate-O2` with wrapper detected as
  `⚠ wrapper-only` — matches §5.e M27.1 predicted state
  exactly.
- Handoff at `docs/handoffs/SESSION_192_m27_inc1_substrate.md`
  (commit `f9256c2` + hash backfill `14b1ad6`).

### M27.2 — JE-create dialog + Playwright journey (SESSION_193)

- **Frontend page extension:** `AccountingJournalEntriesPage.tsx`
  gained a `useEffect` to fetch the full CoA on mount, a
  "+ New journal entry" button in the header, a success-badge
  render slot, and a page-refetch handler. **No new route.**
- **New component:** `NewJournalEntryDialog.tsx` — description
  field + `posted_at` defaulting to today's local date +
  dynamic lines table (minimum 2 lines) with per-row picker +
  debit + credit + memo + real-time balance indicator + submit /
  cancel handlers. Reuses the M14.4 reversal-dialog pattern.
  Client-side validation gates submit until description
  non-empty + all lines have picked accounts + each line
  non-zero on exactly one side + Σ debits = Σ credits.
- **New component:** `GLAccountPicker.tsx` — searchable
  single-select over the M27.1 CoA payload. Client-side filter
  matches both `code` AND `name` case-insensitively per user
  direction. Built on shipped `Input` primitive rather than
  shadcn `Command` (not in the installed subset; CLAUDE.md
  forbids re-running `npx shadcn init` under the v3+v4 bridge).
- **New wrapper:** `createJournalEntry` + `CreateJournalEntryPayload`
  + `CreateJournalEntryLine` types added to `accountingApi.ts`
  — envelope + Decimal-as-string conventions match the
  existing `reverseJournalEntry` wrapper.
- **Component tests:** +20 across three files —
  `GLAccountPicker.test.tsx` (+8, covering search-by-code /
  search-by-name / case-insensitive / empty-state / selection
  callback / selected-view / clear), `NewJournalEntryDialog.test.tsx`
  (+9, covering trigger visibility / disabled when <2 accounts /
  dialog open / today-default / submit-gated / balance-flip /
  successful post + payload shape / server-error inline /
  cancel-no-side-effects), `AccountingJournalEntriesPage.test.tsx`
  (+3, covering trigger visibility / disabled when <2 accounts /
  CoA fetch error message).
- **Playwright journey:** new peer spec at
  `acceptance/journeys/office/accounting_je_create.spec.ts`
  with two test cases per §5.d — successful create exercising
  BOTH code-search AND name-search picker modes with business-
  outcome API assertion (correct account_ids + amounts +
  is_balanced); cancel-without-persistence with unique per-run
  token and pre/post admin-API count assertion.
- **UI regression discovered + fixed during Playwright run:**
  first run failed because the dialog was taller than the
  Playwright default viewport (1280×720) and the submit + cancel
  buttons rendered offscreen. Fix: `DialogContent` given
  `max-h-[90vh] flex-col` + inner body given
  `overflow-y-auto pr-1` so the footer stays fixed while the
  middle scrolls. Both journey test cases green after the fix.
- **Audit at M27.2 close:** 154 → 155 endpoints /
  **119 → 121 covered** / 35 → 34 backend-only. Row 140
  (`admin/accounting/journal-entries/`) → `covered` (wrapper
  `accountingApi.ts:377 createJournalEntry`). Row 149
  (`admin/accounting/gl-accounts/`) → `covered` (wrapper
  `accountingApi.ts:343 fetchGLAccounts` now has a non-test
  consumer via the dialog). Matches §5.e M27.2 predicted state
  exactly.
- Close-out folded into M27.2 per §5.h Option B — both
  increments' §5.e Phase 1 + Phase 2 checks agreed cleanly.

## 3. Deviations from plan and reason

Three small, in-scope refinements landed during implementation.
None shifted the target or broke any §5 lock.

1. **Wrapper-vitest for `fetchGLAccounts` skipped at M27.1**
   in favor of exercising via M27.2 component tests. Justification:
   `frontend/src/lib/analyticsApi.test.ts` documents the
   established convention *"The API-client fetch wrappers are
   exercised end-to-end via the tab tests, not stub-tested
   here."* — the M27.1 test plan predated this discovery.
   Deviation recorded in the SESSION_192 handoff and the M27
   planning §2 primitives entry. Zero test-coverage loss —
   `fetchGLAccounts` is exercised via `GLAccountPicker.test.tsx`
   + `NewJournalEntryDialog.test.tsx` +
   `AccountingJournalEntriesPage.test.tsx` (page-mount fetch
   mock) + the Playwright journey (real backend integration).

2. **Picker built on shipped `Input` primitive rather than
   shadcn `Command`.** The M27.0 memo §5.b named
   `Command`/`Popover` as the intended shadcn primitives, but
   the installed shadcn subset does not include them. CLAUDE.md
   frontend-stack notes explicitly forbid re-running
   `npx shadcn init` under the current Tailwind v3 + shadcn
   radix-nova v4 bridge without user confirmation. Simplest
   truthful path: build a plain searchable list with `Input` +
   list rendering + Tailwind utility classes. UX is functionally
   equivalent (search-by-code + search-by-name + click-to-select
   + clear); the M27 §5.b user directive was satisfied without
   adding new UI primitives.

3. **`DialogContent` height constraint added during Playwright
   run.** First journey run failed because the dialog's height
   exceeded Playwright's default 720px viewport, pushing submit
   + cancel offscreen. Adding `max-h-[90vh] flex-col` +
   `overflow-y-auto pr-1` on the middle body fixed the offscreen
   issue while preserving the shadcn Dialog contract. This is a
   test-driven fix — the Playwright journey caught a real
   operator-facing regression (smaller viewports would have
   surfaced the same problem) before merge, exactly the
   contract §5.d describes.

## 4. Deferrals from M27 (all valid for later re-entry)

All items in `MILESTONE_27_PLANNING.md` §3 remain deferred:

- **Standalone Chart of Accounts page / route / nav entry.**
  Per user substrate-attachment direction. Picker inside the
  M27.2 dialog IS the browsable CoA surface. Re-entry gated on
  operator evidence that a dedicated CoA browsing surface adds
  value beyond the picker context.
- **Trial Balance changes.** No feature creep on a report page.
- **JE edit / update.** Append-only ledger; corrections via
  reverse-and-repost (M14.4).
- **JE templates / recurring journals.** Distinct workflow;
  separate M28+ candidate. Would reuse the M27.1 gl-accounts
  substrate.
- **`posted_by_user` override.** Authenticated operator IS the
  posting user.
- **Advanced picker filtering (filter-by-type dropdown, etc.).**
  Text search over code + name is sufficient at M27.2.
- **Server-side search / pagination on `gl-accounts`.** Full
  CoA is small; client-side filter is sufficient.
  `?include_inactive=true` query param deferred until a
  consumer needs inactive accounts.
- **Row 5 public-fetch-helper regex refinement (M26 O2).**
  Still deferred; M28+ candidate.
- **Rows-1–4 plain-string-literal investigation (M26 O3).**
  Still deferred; M28+ candidate.
- **Test-hygiene remediation (Candidate H).** Kept separate.
  3 shared-DB non-idempotent journeys (identified pre-M25 and
  confirmed at M27.2 full-suite run: `sales_manager/daily_startup`,
  `recon/workflow`, `office/accounting_workflow`) fail on
  polluted DB and pass on clean DB. Live M28+ candidate.
- **All M25 §4 deferrals** — remain valid for later re-entry.

## 5. Durable design principles surfaced or reinforced

**(a) Verify FK / identifier discoverability at planning-open,
not implementation-open (NEW at M27.0).** Saved to memory as
`feedback_verify_fk_discoverability_before_lock.md`. Extends
the §7 verification lineage (M24.1-open + M25.0 + M25.2-open +
SESSION_189 §3 + SESSION_190 §2) to a specific class of intake
gap: **every required identifier on the create endpoint's
serializer must have a truthful discovery surface before §5.b
locks**. At M27.0, this rule caught the GLAccount FK gap before
the wrong scope shape shipped.

**(b) Substrate-attachment beats parallel-surface for adjacent
workflows.** Reinforced at M27.0 §7 by the user's direction:
attach the JE-create dialog to the existing
`AccountingJournalEntriesPage` rather than shipping a standalone
Chart of Accounts route. Preserves one-workflow-beats-two
(M25.0 durable) + preserve-existing-code (PROJECT_RULES §5) +
avoids frontend route inflation. Also reinforces that when a
create workflow needs a "browsing" affordance for an identifier
picker, the picker itself IS the browse surface — no separate
page needed unless operator evidence demands one.

**(c) Shared infrastructure framing over one-off substrate.**
Reinforced at M27.0 §5.b user direction: record `gl-accounts`
as shared accounting infrastructure for future workflows
(recurring journals, adjustments, budget uploads, statement
reconciliation, F&I chargebacks, period-open) rather than
JE-specific. Every future accounting create workflow inherits
the substrate cost as zero. Frames M27.1 as a compound
investment rather than a per-milestone tax.

**(d) DoD exception path applies cleanly to
infrastructure-only sub-increments (reinforced from M26).**
M27.1 is the second post-M21.0 invocation of the M21.0 §5.f
Option B exception path (first was M26 audit-tooling refinement).
Pattern established: within a multi-increment milestone, one
increment may ship pure infrastructure without a Playwright
journey addition IF (a) it has no operator-facing surface
change AND (b) subsequent increments consume the infrastructure
via a journey extension. §5.g documents the invocation; §3
mirrors it; the retrospective §journey-plan-per-increment
records it. Enables clean split-milestone patterns without
weakening the DoD.

**(e) Test-driven UI viewport constraints (NEW at M27.2).**
Playwright's default 1280×720 viewport surfaces overflow bugs
that manual testing on a 1920×1080 dev monitor misses. Dialogs
tall enough to push footers offscreen at 720px height are a
real operator-facing regression (smaller laptops, split-screen
sessions, browser-devtools open). Rule: **any modal dialog
that renders a substantial form (>3 sections) needs
`max-h-[90vh] flex-col` + scrollable inner body from the
start.** The M27.2 fix is the M27 origin of this pattern; add
to the shadcn Dialog usage patterns going forward.

## 6. Streak accounting at M27 close

- **Zero-drift permission-class streak:** enters M27 at 26
  consecutive milestones (M10 → M26). M27 adds two new
  surfaces — the M27.1 `admin/accounting/gl-accounts/` endpoint
  and the M27.2 JE-create dialog wiring to the pre-existing
  create endpoint — both reuse `_M131_PERMS`. No permission
  classes evolve. **Extends to 27 consecutive milestones
  (M10 → M27).**
- **Planning-time as-recommended streak:** enters M27 at 5. M27.0
  target A2 locked as recommended after alternatives presented
  under two framings. §7 substrate-attachment scope adjustment
  refined the scope shape (split into M27.1 / M27.2, no
  standalone CoA page) without shifting the target. Per the
  empirical-discovery-refinement precedent (M25.0 + M25.2-open +
  M26.1-open + SESSION_189 §3 + SESSION_190 §2), scope
  refinements that narrow evidence without changing the target
  count as as-recommended. **Streak increments 5 → 6 at M27.0
  close** and holds at 6 through M27.1 + M27.2 (both pure
  implementation increments executing the M27.0 locked plan).
  Historical run of 89 across M10 → M23 preserved for the record.

## 7. Baselines at M27 close

| Surface | M26 close | M27 close | Delta |
| --- | --- | --- | --- |
| Backend tests | 4,805 pass / 1 skip / 0 fail | **4,813 pass** / 1 skip / 0 fail | +8 |
| Frontend Vitest | 226 pass / 32 files | **246 pass** / 34 files | +20 / +2 files |
| Acceptance journeys | 14 | **16** | +2 (both in one M27.2 spec) |
| Full clean-DB acceptance run | 20 passed (6 setup + 14) | **22 passed** (6 setup + 16) | +2 |
| DRF admin endpoints | 154 | **155** | +1 (new gl-accounts) |
| Audit coverage | 119 / 154 | **121 / 155** | +2 covered (+1 total) |
| Backend-only endpoints | 35 | **34** | -1 (row 140 flipped) |
| Frontend operator routes | 20 | **20** | 0 (attached to existing route) |
| Permission classes | 7 | **7** | 0 (zero-drift preserved) |
| Migrations | 0001–0049 | 0001–0049 | 0 (no schema change) |

- **Django check:** clean.
- **`makemigrations --check --dry-run`:** No changes detected.
- **Frontend + acceptance `tsc --noEmit`:** clean.
- **Redis:** PONG.
- **Audit artifact:** 155 total / 121 covered / 34 backend-only /
  312 service verbs.

## 8. Corrections (post-close)

None as of this writing. Add here if any surface at push.

## 9. Evidence-based candidates for M28

**Elevated (strong recommendation strength for M28.0):**

- **NEW O2 — Row 5 public-fetch-helper regex refinement** (M26
  deferral). Extend `_HELPER_CALL_RE` to include public helpers
  (`getJSON` / `postJSON` / etc.), OR broaden
  `_PUBLIC_FETCH_RE` filters. Blast radius unknown pre-tracing.
  Compound value: unblocks future substrate-integrity work.
- **NEW O3 — Rows 1–4 plain-string-literal investigation** (M26
  deferral). Likely `component_consumed` word-boundary check
  defect. Requires SESSION-189-§3-style tracing at M28.0 open.
- **H — Test-hygiene remediation.** 3 shared-DB non-idempotent
  journeys confirmed at M27.2 full-suite run
  (`sales_manager/daily_startup`, `recon/workflow`,
  `office/accounting_workflow`). Compound CI-stability value
  grows as the acceptance suite grows.
- **NEW — Recurring journal templates.** Would reuse the M27.1
  gl-accounts substrate + M27.2 dialog pattern. Direct operator
  gain for accounting staff. Distinct scope; separate milestone.

**Gated (unchanged from M27 close):**

- T (real tester feedback); U (hosted-demo substrate); L
  (first-live-pilot staging); M (multi-operator support —
  breaks zero-drift streak with intent).

**Deferred pending evidence (unchanged):**

- D (LLM router / cost caps); C (F&I chargeback substrate —
  would reuse M27.1 gl-accounts substrate).

**Deferred but stable:**

- G (dashboard testid hardening).

**Deferred at M27 §3 (all valid for later re-entry):**

Standalone CoA page/route; JE edit/update; JE templates /
recurring; `posted_by_user` override; advanced picker
filtering; server-side gl-accounts search / pagination;
`?include_inactive=true` query param.

**Deferred at M25 §4 (all remain valid):**

Secondary "+ Record test drive" launch point; clickable
"Referred by" attribution nav; named-platform webhook adapters;
attribution rollups; vehicle-picker advanced filters.

**Standing question for M28:** should the substrate-integrity
audit-refinement candidates (O2 + O3) be spent together as a
single M28 milestone (analogous to M26), or split across
milestones as bounded sub-scope inside operator-facing
milestones (audit-correctness-as-supporting-infrastructure per
the M25.3 → M26 durable)? Evidence at M27 close does not force
either path — both are viable.
