---
title: "SESSION_191 handoff — Milestone 27 · Increment 0 (M27.0 — planning refinement + target selection)"
status: historical
type: handoff
date: 2026-08-03
session: 191
milestone: 27
milestone_status: active
milestone_name: "Journal-Entry Creation UI (via shared GLAccount substrate)"
increment: 0
increment_status: shipped
commit: 4641eaa
---

# SESSION_191 — Milestone 27 · Increment 0 (M27.0 — planning refinement + target selection)

## What shipped

M27.0 opened Milestone 27 as a **direct operator-coverage
milestone** under the primary lens that has governed §5.a
selection since M22 close (durable). All §5 decisions
locked in this session; no code changes; no push. Full
active memo authored at
`docs/roadmap/MILESTONE_27_PLANNING.md`.

**Session artifacts:**

- **Starting-state verification (§1):** git clean, `HEAD
  == origin/main @ a277ab8` (M26 push confirmed), Redis
  PONG, Django check clean, `makemigrations --check`
  clean, frontend `tsc --noEmit` clean, acceptance `tsc
  --noEmit` clean. Backend suite **4,805 pass, 1
  skipped, 0 fail** (157.9s). Frontend Vitest **226 pass**
  (32 files). All matches M26 close baseline.
- **First M26 CI run verified (§2):** acceptance
  workflow on the M26.1-hash-backfill push completed
  **green in 2m14s**. M26 is CI-verified shipped. Five
  most recent acceptance runs on `main` all green
  (M23 → M26).
- **Audit regeneration (§3):** `python3 -m
  dealer_ai.scripts.audit_operational_surface` invoked.
  Output: **154 total / 119 covered / 35 backend-only /
  312 service verbs**. Byte-identical to the committed
  M26.1 artifact — no drift.
- **Candidate list presented (§4)** across five tiers:
  - **Elevated (highest recommendation strength):** A2
    (JE creation UI); NEW O2 (row-5 public-fetch-helper
    regex refinement); NEW O3 (rows-1–4 plain-string-
    literal investigation); H (test-hygiene remediation).
  - **Gated:** T (real tester feedback); U (hosted-demo
    substrate); L (first-live-pilot staging); M
    (multi-operator support — breaks zero-drift streak).
  - **Deferred pending evidence:** D (LLM router / cost
    caps); C (F&I chargeback substrate).
  - **Deferred but stable:** G (dashboard testid
    hardening).
  - **Deferred at M25 §4:** secondary "+ Record test
    drive" launch point; clickable "Referred by" nav;
    named-platform adapters; attribution rollups;
    vehicle-picker advanced filters.
- **Independent AI recommendation:** **A2 — Journal-
  Entry creation UI**, under the primary operational-
  coverage lens. Three grounds: (a) direct operator-
  facing coverage gain in a known scope; (b) O2/O3
  require SESSION-189-§3-style tracing before scope-
  lock (would push real ship work into planning
  ambiguity); (c) M26 already spent a bounded
  substrate-integrity milestone — back-to-back substrate
  work without positive evidence of active mis-selection
  risk consumes operator-facing momentum.

**§7 intake+downstream verification — GLAccount FK
intake gap discovered:**

Before scope-locking §5.b, the standard §7 verification
step (M24–M26 durable lesson) surfaced that the create
endpoint `admin/accounting/journal-entries/` takes
`lines: [{account_id, ...}]` — **numeric GLAccount
primary keys** — while the frontend has:

- ❌ No `GLAccount` list endpoint in `urls.py`.
- ❌ No `GLAccount` viewset in `views_accounting.py`.
- ❌ No `fetchGLAccounts` wrapper in `accountingApi.ts`.
- ❌ No chart-of-accounts picker component anywhere in
  `frontend/src/`.

The nearest existing surface, the Trial Balance page
(`/dealer-ai-accounting/trial-balance`), IS the
operator's de facto CoA navigation — it lists every
GLAccount with activity as of a chosen date, with code
+ name + type + balances. But two constraints make TB
insufficient as a JE-create picker source:

1. **Activity-filtered.** Accounts with zero balance
   never render (backend `snapshot.py:172` aggregates
   by `account__code`). A JE-create picker needs the
   full CoA including zero-balance accounts.
2. **Response lacks `id`.** `TrialBalanceRow` returns
   only `account_code`, `account_name`, `account_type`,
   plus balances — no primary key. The create endpoint
   requires numeric ids.

A naive A2 scope would have shipped a form operators
could not actually use — the exact intake gap §7 exists
to catch.

**User direction at M27.0 — substrate-attachment rule:**

Rather than ship a standalone Chart of Accounts page as
an M27.1 operator surface, the user directed the
substrate-attachment response:

- Split M27 into two increments.
- M27.1 = backend endpoint + wrapper only, no UI
  change, no parallel accounting surface.
- M27.2 = "+ New journal entry" dialog on the existing
  `AccountingJournalEntriesPage` (no new frontend
  route); dialog picker IS the browsable CoA.
- Trial Balance stays unchanged.
- Preserve the single-entry-point rule: journal entries
  are created from the journal-entry list page.
- Extend Playwright coverage to verify BOTH successful
  creation AND cancellation-without-persistence.
- Record that `gl-accounts` is shared accounting
  infrastructure intended to support future workflows,
  not just JE creation.

**Durable planning lesson recorded to memory:**

> Before locking any create/edit workflow, verify that
> every required foreign key or identifier is
> discoverable and selectable by the operator through a
> truthful product surface.

Saved to
`memory/feedback_verify_fk_discoverability_before_lock.md`
with full rationale (why: M27.0 §7 GLAccount FK gap
discovery) and application notes (enumerate FK fields
on create serializer; verify truthful discovery surface
exists for each; add substrate creation to milestone
scope before §5.b lock; prefer attaching to existing
navigation over parallel surfaces; split into
substrate + UI increments with infra invoking M21.0
§5.f Option B DoD exception path).

**§5 locks (all captured in
`MILESTONE_27_PLANNING.md`):**

- **§5.a** — LOCKED as A2 (JE creation UI), primary
  operational-coverage lens.
- **§5.b** — LOCKED as two-increment split:
  - **M27.1** ships `GET admin/accounting/gl-accounts/`
    (tenant-scoped, `_M131_PERMS`, full CoA including
    zero-balance accounts, id + code + name + type,
    sorted by code) + `fetchGLAccounts` wrapper. No UI
    change. `gl-accounts` framed as shared accounting
    infrastructure for future workflows.
  - **M27.2** ships "+ New journal entry" button on
    existing `AccountingJournalEntriesPage`, modal
    `<Dialog>` reusing the M14.4 reversal-dialog
    pattern, `NewJournalEntryDialog` +
    `GLAccountPicker` components, `createJournalEntry`
    wrapper. Picker searchable by BOTH code and name.
    `posted_at` defaults to today (editable).
- **§5.c** — LOCKED to match existing accounting API
  response envelope convention (`cost_posting_failures`
  precedent — unpaginated-collection envelope
  `{<resource>: {<items>: [...]}}`). Full contract for
  both `gl-accounts` list response and
  `createJournalEntry` payload documented (money as
  Decimal-as-string per M9.5 / M14.0 §5.c Option A;
  client-side balance + non-empty + one-side-non-zero
  validation; inline dialog error surfaces on 400/404;
  M25.2 success-badge pattern on success).
- **§5.d** — LOCKED as two Playwright test cases in a
  single spec: (1) successful create exercising both
  code-search and name-search picker modes with
  business-outcome API assertion; (2) cancel-without-
  persistence with API assertion that no entry with
  the cancel-test description prefix exists. Prefer
  extending `accounting_workflow.spec.ts` (M20.3 +
  M22.2 substrate) over adding a peer spec.
- **§5.e** — LOCKED as two-source agreement discipline
  inherited from M26 §5.e, applied at each M27
  increment close. M27.1 close: 154 → 155 endpoints,
  gl-accounts row `defer-candidate-O2`. M27.2 close:
  row 140 → `covered` + gl-accounts row → `covered`
  (119 → 121 covered / 155 total / 34 backend-only).
- **§5.f** — LOCKED as 2 implementation increments +
  close-out with fold per §5.h. Total 2–3 sessions.
- **§5.g** — LOCKED with M21.0 §5.f exception path
  invoked for M27.1 (infrastructure-only; new
  endpoint's journey coverage arrives at M27.2).
  M27.2 satisfies DoD directly.
- **§5.h** — LOCKED as evidence-sized Option B fold
  (M18 → M26 precedent). Expected commit count 6 if
  folded, 8 if split.

**§3 deferrals recorded (all valid for later re-entry
with evidence):**

- Standalone Chart of Accounts page / route / nav
  entry — per user direction; picker IS the browse
  surface.
- Trial Balance changes — no scope creep on a report page.
- JE edit / update — append-only ledger; corrections
  via reverse-and-repost (M14.4).
- JE templates / recurring journals — separate M28+
  candidate.
- `posted_by_user` override — authenticated operator
  IS the posting user.
- Account-picker advanced filtering — client-side
  code+name search is sufficient at M27.2.
- Server-side search or pagination on `gl-accounts` —
  CoA is small enough for client-side filter.
- **O2** (row-5 public-fetch-helper regex refinement)
  — M28+ candidate.
- **O3** (rows-1–4 plain-string-literal investigation)
  — M28+ candidate.
- **H** (test-hygiene) — kept separate; M28+
  candidate.
- All M25 §4 deferrals — valid for later re-entry.
- Gated **T / U / L / M**; deferred **D / C**;
  deferred stable **G** — unchanged posture.

## What changed in the repo

- **Created:** `docs/roadmap/MILESTONE_27_PLANNING.md`
  — full active planning memo (all §5 locks).
- **Created:** `docs/handoffs/SESSION_191_m27_inc0_
  planning.md` — this handoff.
- **Modified:** `00-START-NEXT-SESSION.md` — overwritten
  with SESSION_192 (M27.1 backend substrate + wrapper)
  priorities.
- **Created (memory):**
  `memory/feedback_verify_fk_discoverability_before_lock.md`
  — durable planning lesson surfaced at M27.0 §7.

**No code changes.** M27.0 is planning-only per §5.f.
No push per §5.h coordinated-push discipline.

## Verification / baselines at close

- **Backend:** 4,805 pass, 1 skipped, 0 fail (unchanged
  from M26 close).
- **Frontend Vitest:** 226 pass across 32 files
  (unchanged).
- **Acceptance:** 14 journeys unchanged. §5.d journey
  extension planned at M27.2.
- **Django check:** clean (pre-existing Decimal-type
  warnings unrelated to M27).
- **Migrations:** no changes detected.
- **Frontend + acceptance `tsc --noEmit`:** clean.
- **Redis:** PONG.
- **CI:** M26.1-hash-backfill acceptance run green
  (2m14s); five most recent `main` runs all green.
- **Audit artifact:** 154 total / 119 covered / 35
  backend-only / 312 service verbs — byte-identical to
  the committed M26.1 artifact after regen.

## Deferrals / follow-on items

All deferrals recorded in
`MILESTONE_27_PLANNING.md` §3. Summary:

- Standalone CoA page / route / nav entry (per user
  substrate-attachment rule).
- Trial Balance changes.
- JE edit / update endpoints.
- JE templates / recurring journals.
- `posted_by_user` override.
- Advanced account-picker filtering.
- Server-side search / pagination on gl-accounts.
- **O2 + O3 + H** — remain M28+ candidates.
- All M25 §4 deferrals.
- Gated / deferred candidate pool unchanged.

## Non-goals achieved (SESSION_191)

- ❌ No code shipped (planning-only session).
- ❌ No push (M27.0 is planning; coordinated push at
  M27 close).
- ❌ No implementation increment opened.
- ❌ No M1–M26 shipped surface modified.
- ❌ No acceptance journey added / extended.
- ❌ No endpoint disposition changes.
- ❌ No standalone Chart of Accounts page proposed
  (substrate-attachment rule applied).
- ❌ No Trial Balance modifications proposed.

## Streak accounting at M27.0 close

- **Zero-drift permission-class streak:** 26
  consecutive milestones (M10 → M26). M27 adds two
  new endpoints (`admin/accounting/gl-accounts/` at
  M27.1 + row 140's create-endpoint newly wired at
  M27.2) — both reuse `_M131_PERMS`; no permission
  classes evolve. Intended posture at M27 close: **27
  consecutive milestones (M10 → M27)**.
- **Planning-time as-recommended streak:** 5 → **6**.
  M27.0 target A2 was locked as recommended after
  alternatives (A2, O2, O3, H) presented with two
  framings (primary operational-coverage lens vs. M26
  substrate-integrity reframe). The user confirmed the
  AI's recommendation. The §7 substrate-attachment
  scope adjustment (split into M27.1/M27.2, no
  standalone CoA page) refined the scope shape without
  shifting the selected target. Per the empirical-
  discovery-refinement precedent (M25.0 + M25.2-open +
  M26.1-open + SESSION_189 §3 + SESSION_190 §2), scope
  refinements that narrow evidence without changing
  the target count as as-recommended. Counts as
  as-recommended. Historical run of 89 across M10 →
  M23 preserved for the record.

## Next session (SESSION_192 — M27.1 backend substrate + wrapper)

Per `MILESTONE_27_PLANNING.md` §7 and the overwritten
`00-START-NEXT-SESSION.md`:

1. Verify M26 close baseline holds (backend 4,805 pass,
   frontend 226 pass, acceptance 14 journeys clean-DB,
   audit 119 / 154, HEAD at `a277ab8` or later, Redis
   PONG).
2. Regenerate audit to confirm 119 / 154 still holds.
3. Implement `admin_gl_account_list` view + serializer
   in `views_accounting.py` (DRF `@api_view(["GET"])`,
   `_M131_PERMS`, tenant scoping, sorted-by-code
   projection).
4. Wire the `urls.py` route.
5. Write `test_m27_gl_account_list.py` backend tests
   (positive: full CoA sorted; zero-balance included;
   negative: cross-tenant isolation; permission
   enforcement; unauthenticated 401/403).
6. Add `fetchGLAccounts` + `GLAccount` type +
   `GLAccountListResponse` interface to
   `accountingApi.ts`.
7. Write `accountingApi.gl_accounts.test.ts` vitest.
8. Regenerate audit; assert 154 → 155 with new row
   `defer-candidate-O2` disposition (no consumer yet).
9. Perform §5.e Phase 2 per-row verification for the
   new row.
10. Update `docs/CAPABILITY_MATRIX.md` §7β with M27.1
    partial shipped surface.
11. Compose SESSION_192 handoff.
12. Coordinated push at M27.1 close (M27.1 commit +
    hash backfill).

## Anchors that win on conflict (M27.0 close)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_27_PLANNING.md` §5 (all
   locks)
4. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` row
   140 (target row; current `defer-candidate-O2`)
5. `backend/dealer_ai/views_accounting.py` (existing
   accounting-module patterns — permission classes,
   tenant scoping, response envelopes)
6. `frontend/src/lib/accountingApi.ts` (existing
   wrapper conventions)
7. `frontend/src/pages/AccountingJournalEntryDetailPage.tsx`
   (M14.4 reversal-dialog pattern — the template for
   the M27.2 create dialog)
8. `acceptance/journeys/office/accounting_je_reversal.spec.ts`
   (M22.2 journey pattern — the template for the M27.2
   journey)
9. Memory record
   `feedback_verify_fk_discoverability_before_lock.md`
10. Memory record
    `feedback_one_workflow_over_two_overlapping.md`
11. Memory record `feedback_preserve_existing_code.md`
12. `docs/handoffs/SESSION_190_m26_close.md` (M26
    close; records the 119 / 154 baseline M27 opens on)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.
