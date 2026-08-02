---
title: "SESSION_145 handoff — Milestone 17 · Increment 3 (M17.3 — Close-out)"
status: historical
type: handoff
date: 2026-08-02
session: 145
milestone: 17
milestone_status: shipped
milestone_name: "Trial-balance materialization + as_of picker (monthly-close v1)"
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_145 — Milestone 17 · Increment 3 (M17.3 — Close-out)

> **All four M17 increments in one calendar
> session.** M17.0 planning (`404605e`) + M17.1
> backend (`f217e0d`) + M17.1 docs (`bedc615`)
> + M17.2 frontend (`4235137`) + M17.2 docs
> (`dc064cf`) + **M17.3 close-out (this
> commit)** landed at SESSION_145 per user
> direction "continue" after each earlier
> increment.

## What shipped

Documentation-only per M10.8 / M11.7 / M12.8 /
M13.4 / M14.5 / M15.2 / M16.2 precedent. Six
close-out artifacts + one coordinated commit
landing everything together. **Milestone 17
— Trial-balance materialization + `as_of`
picker (monthly-close v1) — SHIPPED.**

## Delivered

1. **`docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
   written at M17.3 close.** ~9-section
   retrospective following the M16 structure.
   §1 planned scope + §2 what shipped
   (six-row increment table) + §3 deferrals
   (12 M17-specific + 5 universal = 17) + §4
   deviations (sessions collapsed 145-148 →
   145, permission-class miscount correction,
   native `<input type="date">` in place of
   shadcn `Calendar`) + §5 compatibility
   (M1-M16 endpoints unchanged) + §6 six
   lessons (§5-decisions-locked-at-open holds
   for 8th, bundle entity+picker pattern,
   naming discipline pays fast,
   `IntegrityError` → domain exception → 409
   pattern, native primitives over shadcn
   escalation, in-place page extension) + §7
   streak update (70 planning-time as-
   recommended M5.1 → M17.0 across eight
   consecutive milestones) + §8 what M17
   unblocks + §9 standing question response
   (do NOT preemptively lock M18 as UI-
   polish milestone).

2. **`docs/CAPABILITY_MATRIX.md` §7r added.**
   New section describing the M17 shipped
   surface following §7q (M16) template.
   Six-row table covering: backend
   materialization entity + freeze verb;
   backend DRF endpoints; migration; frontend
   API client; TrialBalanceDatePicker
   component; extended trial-balance page.
   Deferrals + operator experience sections
   included.

3. **`docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 17 SHIPPED entry added.**
   Follows §Milestone 16 structure. Delivery
   record + business objective + related
   research + operational pain resolved +
   existing reusable primitives + gap +
   scope (four increments; sessions
   collapsed) + out of scope (deferrals).

4. **`docs/roadmap/MILESTONE_17_PLANNING.md`
   frontmatter flipped:** `status: active`
   → `status: shipped`. Added
   `shipped_at_session: SESSION_145` and
   `retrospective: docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
   pointers.

5. **`docs/roadmap/MILESTONE_18_PLANNING.md`
   skeleton written** from the M17 §8
   unblocked-work list per standing user
   directive. Frontmatter `status: draft`.
   §0 engineering practices to preserve from
   M2-M17 (extended with M17's new patterns:
   `IntegrityError` → domain exception,
   naming discipline, in-place page
   extension, native primitives over shadcn).
   §1 candidate M18 targets (15 options —
   Options A-O) drawn from M17 §8 + M16 §8
   (partly still valid). §5.a `[NEEDS-
   DECISION-BEFORE-M18.0]` target selection
   placeholder. Standing question from M17
   §9 (UI-polish milestone?) carried forward
   for M18.0 consideration.

6. **`00-START-NEXT-SESSION.md` overwritten**
   with M18.0 priority for SESSION_146.
   Records the M17 close totals + baseline
   (backend 4,363 pass, frontend 140 pass)
   + streak (70 planning-time as-recommended
   M5.1 → M17.0 across eight milestones) +
   candidate list for M18.0 target selection.

## Baseline at M17 close

- **Backend baseline: 4,363 pass**, 1
  skipped, 0 fail. **Frontend Vitest
  baseline: 140 pass.** All unchanged since
  M17.2 (M17.3 is docs-only).
- Migrations `0043`–`0046`.
- Tenancy carriers **49** (unchanged since
  M17.1: +TrialBalanceSnapshot +
  TrialBalanceSnapshotRow).
- DRF admin surface **107** (unchanged since
  M17.1: +3 M17 endpoints).
- Frontend operator routes **20** (unchanged
  — M14.2 extended in place at M17.2 per §4
  test binding).
- Permission classes **7 actual** (six
  `Is*` + `ReadOnly`; zero-drift streak
  nine consecutive milestones M10 → M17).
- Celery-beat task families **10**
  (unchanged — M17 uses sync-sibling shape
  per §5.c Option A).
- AI safety stack 17 scrub stages
  (unchanged — M17 has no LLM path).

## Streak update

**70 planning-time as-recommended M5.1 →
M17.0.** Eight consecutive milestones now
(M10 + M11 + M12 + M13 + M14 + M15 + M16 +
M17) with every §5 decision confirmed as-
recommended at planning-time open. Four §0.a
implementation-time micro-decisions across
M17.1 + M17.2 (dataclass rename, detail URL
shape, picker default deferral, native
`<input type="date">`) do not count against
the streak per M10 §9.

## What's next: SESSION_146 M18.0

Per `MILESTONE_18_PLANNING.md`:

- User names M18 target milestone at open
  (§5.a). Candidates in the planning
  skeleton §1 span 15 options (A-O)
  drawn from M17 §8 + M16 §8 unblocked
  work + M17 §9 UI-polish standing
  question.
- Expand §1 (business questions) + §5
  (load-bearing decisions) + §7
  (sequencing) into full memo.
- Ship M18.0 handoff.
- Overwrite `00-START-NEXT-SESSION.md`
  with M18.1 priority.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M17 SHIPPED entry added)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_17_PLANNING.md`
   (frontmatter shipped)
6. `docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
   (new at M17.3)
7. `docs/roadmap/MILESTONE_18_PLANNING.md`
   (new skeleton at M17.3)
8. `docs/handoffs/SESSION_145_m17_inc0_planning.md`
9. `docs/handoffs/SESSION_145_m17_inc1_backend.md`
10. `docs/handoffs/SESSION_145_m17_inc2_frontend.md`
11. `docs/CAPABILITY_MATRIX.md` §7r (new at
    M17.3)
