---
title: "SESSION_035 handoff — Milestone 1 planning pass + roadmap reorg"
status: historical
type: handoff
date: 2026-07-31
session: 035
commit: (pending)
---

# SESSION_035 — Milestone 1 planning pass + roadmap reorg

## What shipped

Two things: (1) a full implementation-planning pass for Milestone 1 —
persisted as `docs/roadmap/MILESTONE_1_PLANNING.md` — and (2) a
repository move that groups roadmap artifacts under `docs/roadmap/`.

### 1. Milestone 1 planning pass — `docs/roadmap/MILESTONE_1_PLANNING.md`

Five sections, all completed before any code was written:

- **§1 Design memo.** Five subsystem decisions (tenancy,
  authentication, role-based permissions, advisor-slug replacement,
  singleton→per-tenant migration path) each mapped to a
  research/roadmap citation, an existing implementation to extend,
  and one to leave untouched.
- **§2 Migration impact review.** 18 existing systems inventoried
  with impact classification (Extended / NO IMPACT / Preserved) and
  concrete work required per system.
- **§3 Compatibility checklist.** 9 categories of invariants that
  must remain true after Milestone 1 ships. Testable acceptance
  criteria — Milestone 1 is not complete until every checklist item
  verifies true.
- **§4 Reusable primitives review.** Confirms §3.9 dealer_config
  resolver and §3.10 onboarding profile are sufficient with
  extension (not parallel implementation). Flags the genuinely
  greenfield surfaces (`Dealership` model, `User` role attachment,
  DRF auth/permission classes, frontend login).
- **§5 Scope discipline + deferrals.** 11 ideas that surfaced during
  planning that would expand scope beyond Milestone 1, each deferred
  (per Discovery Rule) to a specific future milestone.

Sources cited: `PROJECT_RULES.md`, `roadmap/IMPLEMENTATION_ROADMAP.md`,
`BUSINESS_DOMAIN_MAP.md`, `CAPABILITY_MATRIX.md`,
`VEHICLE_CENTRIC_PIVOT.md`, `FINANCE_DEPARTMENT_MAPPING.md`,
`BHPH_OPERATIONS_MAPPING.md`.

### 2. Roadmap reorg — `docs/roadmap/`

New directory `docs/roadmap/` created. Two existing roadmap files
moved with `git mv` (history preserved):

- `docs/IMPLEMENTATION_ROADMAP.md` → `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
- `docs/onboarding/ASSISTANT_AGENT_CREATION_ROADMAP.md` → `docs/roadmap/ASSISTANT_AGENT_CREATION_ROADMAP.md`

New: `docs/roadmap/MILESTONE_1_PLANNING.md` (see §1 above).

**Active references updated** (paths repointed to `docs/roadmap/`):

- `00-START-NEXT-SESSION.md` (all pathed references)
- `docs/BUSINESS_DOMAIN_MAP.md`
- `docs/DEALER_KIT_SESSION_START.md`
- `docs/DEALER_KIT_TRANSLATION_LAYER.md` (2 refs)
- `docs/onboarding/FREEDOM_FORD_ONBOARDING_PLAN.md` (5 refs,
  including sibling link updated to `../roadmap/...`)
- `backend/dealer_ai/models.py` (docstring pointer)
- `frontend/src/pages/DealerOnboardingPage.tsx` (comment pointer)

**Historical handoffs left intact** (per doc-governance principle
that historical docs are immutable):

- `docs/handoffs/SESSION_008_*`, `SESSION_011_*`, `SESSION_031_*`,
  `SESSION_033_*`, `SESSION_034_*` — each references the old paths
  because that was accurate at the time.

## No code changed

Every deliverable is a planning artifact or a file move. Backend and
frontend behavior unchanged. Test baseline still 1,300 pass, 1
skipped.

## What's next

**SESSION_036 governance work** shipped immediately after (see
`SESSION_036` handoff). After that, SESSION_037 = Milestone 1
implementation, using `docs/roadmap/MILESTONE_1_PLANNING.md` as
the acceptance contract.

## Deferred to future milestones

All 11 deferrals from §5 of the planning doc are captured there;
this handoff does not re-enumerate them.
