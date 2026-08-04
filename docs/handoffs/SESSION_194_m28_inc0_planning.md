---
title: "SESSION_194 handoff — Milestone 28 · Increment 0 (M28.0 — planning refinement + target selection)"
status: historical
type: handoff
date: 2026-08-03
session: 194
milestone: 28
milestone_status: active
milestone_name: "Recurring Journal Templates (on M27.1 shared GLAccount substrate)"
increment: 0
increment_status: shipped
commit: TBD
---

# SESSION_194 — Milestone 28 · Increment 0 (M28.0 — planning refinement + target selection)

## What shipped

M28.0 opened Milestone 28 as a **direct operator-coverage
milestone** under the primary lens that has governed §5.a
selection since M22 close (durable), plus the M27.1
substrate-compound-value framing (M28 is the first M28+
consumer of the shared `gl-accounts` infrastructure
beyond the M27.2 dialog). All §5 decisions locked in
this session; two architectural verifications performed
at open; one durable engineering-practices refinement
adopted; no code changes; no push. Full active memo
authored at `docs/roadmap/MILESTONE_28_PLANNING.md`.

**Session artifacts:**

- **Starting-state verification (§1):** git clean, `HEAD
  == origin/main @ 172de87` (M27 push confirmed), Redis
  PONG, Django `check` clean, `makemigrations --check`
  clean, frontend `tsc --noEmit` clean, acceptance `tsc
  --noEmit` clean. Backend suite **4,813 pass, 1
  skipped, 0 fail** (164.1s). Frontend Vitest **246
  pass** (34 files). All matches M27 close baseline.
- **First M27 CI run verified (§2):** acceptance
  workflow on the M27.2-hash-backfill push completed
  **green in 2m22s**. M27 is CI-verified shipped. Five
  most recent acceptance runs on `main` all green
  (M23 → M27).
- **Audit regeneration (§3):** `python3 -m
  dealer_ai.scripts.audit_operational_surface` invoked.
  Output: **155 total / 121 covered / 34 backend-only /
  312 service verbs**. Byte-identical to the committed
  M27.2 artifact — no drift.
- **Candidate list presented (§4)** across the M27 §9
  tiers:
  - **Elevated (highest recommendation strength):** A
    (NEW recurring journal templates); NEW O2 (row-5
    public-fetch-helper regex refinement); NEW O3
    (rows-1–4 plain-string-literal investigation); H
    (test-hygiene remediation — three shared-DB
    non-idempotent journeys confirmed at M27.2 full-suite
    run).
  - **Gated:** T (real tester feedback); U (hosted-demo
    substrate); L (first-live-pilot staging); M
    (multi-operator support — breaks zero-drift streak).
  - **Deferred pending evidence:** D (LLM router / cost
    caps); C (F&I chargeback substrate).
  - **Deferred but stable:** G (dashboard testid
    hardening).
  - **Deferred at M27 §3:** standalone CoA page/route;
    JE edit/update; `posted_by_user` override; advanced
    picker filtering; server-side gl-accounts search /
    pagination; `?include_inactive=true` on gl-accounts.
  - **Deferred at M25 §4:** secondary "+ Record test
    drive" launch point; clickable "Referred by" nav;
    named-platform adapters; attribution rollups;
    vehicle-picker advanced filters.
- **Independent AI recommendation:** **A — NEW
  recurring journal templates**, under the primary
  operational-coverage lens. Four grounds:
  1. Only A is directly operator-facing among the
     elevated set.
  2. A is the first candidate that would demonstrate
     M27.1's "shared accounting infrastructure"
     compound-value framing on a real operator
     workflow.
  3. Scope is bounded and small-to-moderate; comparable
     to M27's size. Fits an intentionally short M28 arc.
  4. Satisfies DoD directly via new + extended Playwright
     journeys (no exception path needed at the
     customer-facing increment).

- **User confirmation of §5.a:** the user confirmed the
  recommended target. Before locking §5.b, the user
  requested a **variable-amount forward-compat
  verification** — asking whether the proposed template
  data model naturally supports future variable-amount
  templates (depreciation, utilities, payroll accruals)
  without requiring a redesign. Design pass was
  performed against the four workflows and confirmed
  that `side` (CharField choices) + nullable `amount`
  accommodates all four with zero DB migration. Dual-
  column `debit`/`credit` mirroring was rejected because
  it cannot express "side known, amount deferred" without
  adding a side column — so adding `side` now, once,
  avoids a future migration. **The `amount IS NULL`
  posture is intentional forward-compat**, documented
  in the model docstring and the memo.

- **Second user-requested verification — model duplication
  analysis:** the user asked whether
  `JournalEntryTemplateLine` should intentionally mirror
  `JournalEntryLine` or whether a smaller shared
  substrate would reduce long-term maintenance. Four
  sharing options were considered: (A) abstract base
  class, (B) fuse into `JournalEntry` via `is_template`
  flag, (C) small cross-tenant guard helper, (D) mirror
  the dual-column amount storage. All except C rejected:
  A retrofits inheritance on shipped M13.1 code for
  negative ROI; B destroys the M13.1 immutability +
  `posted_at` + reversal invariants and forces
  `WHERE is_template = FALSE` on every posting query; D
  forecloses variable-amount forward-compat.

- **Third refinement — user applied the evidence-first
  standard to helper extraction:** the AI's initial §5.b
  draft included Option C (extract cross-tenant guard
  as shared helper `_validate_line_cross_tenant()`).
  The user pushed back: don't extract just because it
  can be extracted. The two `clean()` methods stay ~5
  lines each, enforce the same invariant against
  different parents, and are unlikely to diverge —
  duplicating small stable domain logic preserves local
  clarity; extraction should be evidence-gated, not
  DRY-driven. Memo updated to reflect this as a durable
  engineering-practices rule (§0), documented in the
  §5.b commentary block, and removed from M28.1
  sequencing.

- **§7 FK-discoverability verification:** all M28.1
  backend FKs (Template.dealership,
  TemplateLine.template, TemplateLine.account,
  TemplateLine.dealership) and all M28.2 frontend FKs
  (Template ID for Instantiate, GLAccount ID for
  template line + JE line) have discovery surfaces
  before §5.b lock. Template IDs surface via the
  templates section on `AccountingJournalEntriesPage`;
  GLAccount IDs reuse the M27.2 `GLAccountPicker`
  (which consumes the M27.1 `fetchGLAccounts` wrapper).
  No new FK without a truthful discovery surface.

- **DoD compliance check:** M28.1 (backend substrate +
  wrappers) invokes the M21.0 §5.f exception path
  (third invocation after M26 audit-tooling and M27.1
  gl-accounts substrate). M28.2 satisfies DoD directly
  via new `accounting_je_template.spec.ts` (2 cases:
  create-template + instantiate-template) + one-case
  extension to `accounting_je_create.spec.ts`
  (blank-path regression guard).

## What was NOT touched this session

- **No code changes.** All work landed in the planning
  memo + this handoff + one memory record.
- **No push.** Coordinated push at M28 close per §5.h.
- **Anchors + narrative + inventory** — untouched (M27
  close overwrote `00-START-NEXT-SESSION.md` at
  SESSION_193; this session updates it for SESSION_195).
- **Existing shipped surface** — no modification to any
  M1–M27 backend, frontend, service, or acceptance
  code.

## Files created / modified this session

- **CREATED:** `docs/roadmap/MILESTONE_28_PLANNING.md`
  — full active memo per the standard planning shape
  (see M27 planning as reference). Contains:
  frontmatter + opening block (with both architectural
  verifications summarized + the evidence-first
  duplication refinement documented) + §0 engineering
  practices (with new "duplicate small stable domain
  logic; extract only on evidence" rule) + §1 business
  questions + §2 primitives extended + §3 deferrals +
  §4 tests bound + §5.a–§5.h locks + §6 anchors + §7
  sequencing + §8 streak accounting + §9 non-goals.
- **CREATED:** `memory/feedback_duplicate_small_stable_logic.md`
  — new durable rule surfaced at M28.0 from the
  helper-extraction pushback.
- **UPDATED:** `memory/MEMORY.md` — index entry for
  the new memory record.
- **CREATED:** `docs/handoffs/SESSION_194_m28_inc0_planning.md`
  — this handoff.
- **OVERWRITTEN:** `00-START-NEXT-SESSION.md` — for
  SESSION_195.

## Session numbers

- **Backend:** 4,813 pass, 1 skipped, 0 fail (unchanged
  — no code).
- **Frontend:** 246 pass across 34 files (unchanged).
- **Acceptance:** 16 journeys, ~30s clean-DB
  (unchanged).
- **Audit:** 155 endpoints / 121 covered / 34
  backend-only / 312 service verbs (unchanged).
- **Django check:** clean (0 issues).
- **Migrations:** No changes detected.
- **Frontend tsc:** clean.
- **Acceptance tsc:** clean.
- **Redis:** PONG.
- **CI:** M27 acceptance run green (2m22s @
  `172de87`).

## Streak accounting (post-SESSION_194)

- **Zero-drift permission-class streak:** unchanged at
  **27 consecutive milestones (M10 → M27)**. M28 is
  planning-only; no permission classes touched.
- **Planning-time as-recommended streak:** **6 → 7**.
  M28.0 locked as recommended after user confirmation
  + two architectural verifications + one evidence-
  first refinement. Historical run of 89 across M10 →
  M23 preserved for the record.

## Durable lessons carried forward from M28.0

- **NEW at M28.0** — *Duplicate small stable domain
  logic; extract only on evidence.* Prefer local
  clarity (each model owns its own invariant) over
  DRY-for-its-own-sake. Extraction is reserved for
  the point where evidence of divergence or genuine
  maintenance burden appears. Saved to memory at
  `feedback_duplicate_small_stable_logic.md`. Governs
  future refactor scoping across all milestones — not
  a template-specific rule.
- **REINFORCED at M28.0** — *Verify FK /
  discoverability at planning-open* (M27.0 origin).
  All M28 FKs verified against discovery surfaces
  before §5.b lock.
- **REINFORCED at M28.0** — *Variable-amount forward-
  compat via schema separation of side + nullable
  amount* (new architectural pattern; documented in
  M28 memo §5.b commentary block for future
  contributors).
- **REINFORCED at M28.0** — *Recipes vs postings are
  different domain concepts* — fusing them via
  inheritance or flags destroys separation of
  concerns and forces defensive filters on every
  posting-query consumer. M13.1 immutability contract
  is protected.
- **REINFORCED at M28.0** — *DoD exception path for
  infrastructure-only sub-increments* is now on its
  third invocation (M26, M27.1, M28.1). The pattern
  is established.

## What SESSION_195 must do

Follow the §7 sequencing steps for M28.1 exactly:

1. Verify M28.0 close baseline holds (backend 4,813
   pass, frontend 246 pass, acceptance 16 journeys,
   audit 121 / 155, HEAD at M28.0 close local commit).
2. Regenerate audit to confirm 121 / 155 still holds.
3. Add `JournalEntryTemplate` + `JournalEntryTemplateLine`
   models. **Do not modify** `JournalEntryLine` —
   duplicate the cross-tenant guard inline on the new
   model per §5.b evidence-first duplication decision.
4. `makemigrations` → verify `0050_m281_je_template.py`.
5. Add service verbs + `TemplateLineInput` + new
   domain errors in `services/accounting.py`.
6. Add serializers + view function + URL route.
7. Write model + service + endpoint tests.
8. Backend suite → assert green (4,813 → ≥4,830).
9. Add frontend wrappers in `accountingApi.ts`.
10. Write wrapper vitest.
11. Frontend suite → assert green (246 → ~249).
12. Regenerate audit; assert 155 → 157 with two new
    rows at `defer-candidate-O2`.
13. §5.e Phase 2 per-row verification.
14. Update `docs/CAPABILITY_MATRIX.md` §7γ (M28.1
    partial).
15. Draft M28.1 handoff
    `docs/handoffs/SESSION_195_m28_inc1_substrate.md`.
16. **No push at M28.1 close.**

## Non-goals for SESSION_195

- ❌ Do NOT ship any frontend UI at M28.1 (M28.2
  scope).
- ❌ Do NOT modify shipped `JournalEntryLine`.
- ❌ Do NOT extract the cross-tenant guard as a
  helper (§5.b evidence-first duplication decision).
- ❌ Do NOT ship variable-amount serializer support
  (schema-reserved only).
- ❌ Do NOT push at M28.1 close.
- ❌ Do NOT skip the two-source agreement check at
  audit regeneration.

## Coordination

- **Push posture:** local-only at M28.0 close.
  Coordinated push at M28 close per §5.h Option B
  (folded close-out inside M28.2 unless evidence
  forces a split).
- **Expected M28 commits at close:** 6 folded or 8
  split.
