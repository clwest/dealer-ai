---
title: "SESSION_074 handoff — Milestone 5 · Increment 0 (planning pass)"
status: historical
type: handoff
date: 2026-08-01
session: 074
milestone: 5
milestone_status: planning
increment: 0
increment_status: shipped
commit: ec2b611
---

# SESSION_074 — Milestone 5 · Increment 0 (M5.0 — planning pass)

## What shipped

Documentation-only session. No code changes. Milestone 5
(Vehicle lifecycle stages + retail gating) is now scoped,
sequenced, and ready for implementation subject to four
`[NEEDS-DECISION-BEFORE-M5.1]` items requiring user
review before code lands.

The deliverable is
`docs/roadmap/MILESTONE_5_PLANNING.md` (1,472 lines)
mirroring the eight-section shape (§0–§8) that
`MILESTONE_2_PLANNING.md` (SESSION_045),
`MILESTONE_3_PLANNING.md` (SESSION_055), and
`MILESTONE_4_PLANNING.md` (SESSION_065) proved out. Plus
a new §9 "Load-bearing decisions summary" consolidating
the four items that need user confirmation at the top of
SESSION_075.

## Read-first pass performed

Per the SESSION_073 handoff § "Recommended exact scope
for SESSION_074":

1. `docs/PROJECT_RULES.md` — six governance rules.
2. `docs/DOC_GOVERNANCE.md` — six documentation
   principles.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 5
   — business objective, related research, operational
   pain, gap statement, scope boundary.
4. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` — full
   document. §8 M5 bootstrap notes and §6 (ten lessons)
   are load-bearing inputs.
5. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6 — ten
   lessons carried forward.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 — six
   lessons carried forward.
7. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 4 —
   target M5 shape (`VehicleStage`, `VehicleStageEvent`,
   deterministic transitions, manual overrides, flip
   `search_vehicles` to require `stage='frontline'`).
   Plus §"Workflow / state-machine changes" (thin-service
   module recommendation) and §"Data-model changes"
   (`VehicleStage` OneToOne + `VehicleStageEvent` FK).
8. `docs/research/INVENTORY_ACQUISITION_MAPPING.md` §6
   inventory categorization (7 categories: front-line
   ready, in recon, incoming, wholesale-out, company
   use, hold/reserved, off-market) + §1.4 economics of
   holding + §15 aging pain.
9. `docs/research/RECON_MAPPING.md` pain #12 (recon ETA
   mismatch) + §14 blockers.
10. `docs/roadmap/MILESTONE_4_PLANNING.md` — the 8-
    section shape M5.0 mirrors; §5.f permission-matrix
    pattern reused; §1.0.QC-GAP annotation pattern
    inherited.
11. `docs/roadmap/MILESTONE_3_PLANNING.md` — same shape
    reference.
12. `docs/handoffs/SESSION_065_m4_planning.md` — the
    planning-pass handoff shape M5.0 mirrors.
13. `backend/dealer_ai/models.py` — verified
    `Vehicle.is_available` still a plain Boolean;
    `Vehicle.latest_condition_report` +
    `Vehicle.latest_completed_condition_report` +
    `Vehicle.open_work_orders` +
    `Vehicle.has_recon_decisions` @property accessors
    shipped from M3/M4.
14. `backend/dealer_ai/services/tenancy.py` —
    `_TENANT_CARRIER_MODEL_NAMES` tuple (15 entries at
    M4 close; M5.1 extends to 17).
15. `backend/dealer_ai/services/chat_engine.py` — line
    3116 `_available_vehicles_queryset` currently
    filters on `is_available=True` (the M5.5 retail-
    gating refactor target).
16. `backend/dealer_ai/services/recon.py` — verified
    `open_work_orders_for_vehicle` +
    `has_recon_decisions_for_vehicle` read helpers
    exposed by M4.2 (M5's deterministic rules will
    read them).

## The 4 load-bearing decisions requiring user review

The planning artifact §9 records each. In each case, the
planning doc includes a recommendation with rationale
but leaves the final decision explicitly to the user at
SESSION_075 top per the SESSION_073 start-here mandate
("Do not silently pick a load-bearing decision option
without user review. Mark it
`[NEEDS-DECISION-BEFORE-M5.1]` in the draft instead.").

### §5.a — Stage enum vocabulary

**Question.** Which set of stages does M5 v1 ship?

**Recommendation: Option C** — hybrid VCP fine-grained
pipeline + INVENTORY operational terminals; 12 stages:
`incoming → inspection → recon → qc → detail →
photography → listing → frontline → sold`, plus
`wholesale_out`, `hold_reserved`, `off_market`. Two
carve-outs: (a) `sold` stubbed until M9 ships the
`Sale` model; (b) `detail` kept distinct in v1, may
collapse into `qc` if per-dealer evidence surfaces the
need.

**Alternatives.** Option A (INVENTORY §6 verbatim — 7
stages, coarser); Option B (VCP verbatim — 12 stages,
same as C but without the operational-terminal
justification).

**User: confirm or override.**

### §5.b — Allowed transition table

**Question.** Which transitions are permitted? Which
fire deterministically?

**Recommendation.** The table drafted at §5.b. Highlights:

- Retail-preparation chain (deterministic where possible;
  manual otherwise): `incoming → inspection` (manual);
  `inspection → recon` (deterministic on completed
  condition report ≥1 finding recommended-or-higher);
  `recon → qc` (deterministic when no open WOs remain
  linked to must_do/safety findings); `qc → detail`
  (manual); `detail → photography` (manual);
  `photography → listing` (deterministic on M6 photo
  threshold — stubbed until M6); `listing → frontline`
  (deterministic on `Vehicle.price > 0` + M6 listing
  published — the price check works today, the listing
  check stubs until M6).
- Operational escapes (always manual):
  `<any nonterminal-retail> → wholesale_out` (reason
  required); `<any nonterminal-retail> → hold_reserved`
  (reason required); `<any> → off_market` (reason
  required).
- Escape returns (manual):
  `hold_reserved → <previous retail-preparation stage>`;
  `wholesale_out → inspection`; `off_market →
  inspection`.
- Terminal: `frontline → sold` deferred to M9.

Trigger enum: `manual`, `rule`, `import`, `bootstrap`.

**User: confirm the transition set + `sold` deferral +
`detail` collapse policy.**

### §5.e — `Vehicle.is_available` disposition

**Question.** What happens to the M1
`Vehicle.is_available` boolean when `VehicleStage`
lands?

**Recommendation: Option D** — keep `is_available`
intact for backwards compatibility; add
`is_retail_eligible` as the new authoritative
predicate; refactor retail-side surfaces
(chat/search/showroom) at M5.5 to
`is_retail_eligible`; leave `is_available` for
downstream consumers that haven't migrated yet
(M6/M7/M8 migrate as they land); add a docstring
deprecation flag scheduling removal at M9 or later.

**Alternatives.** Option A (remove immediately —
higher blast radius); Option B (turn into shim —
drift risk); Option C (keep as manual override — breaks
single-source-of-truth).

**User: confirm or choose A/B/C.**

### §5.f — Role permission matrix

**Question.** Which existing roles can transition a
stage, and via which surfaces?

**Recommendation.** Reuse
`IsReconManagerSalesManagerOrOwnerAtActiveDealership`
(M4.6) for recon-adjacent transitions (everything except
`wholesale_out` + `off_market`); reuse
`IsSalesManagerOrOwnerAtActiveDealership` (M2.6) for
`wholesale_out` + `off_market` (commercial decisions).
No new permission class needed in M5. Fine-grained
per-transition gating happens at the service layer.

**Per-transition matrix (drafted at §5.f):**

| M5 surface | dealer_owner | sales_manager | recon_manager |
|---|---|---|---|
| GET lifecycle dashboard | ✓ | ✓ | ✓ |
| POST retail-preparation transition | ✓ | ✓ | ✓ |
| POST → wholesale_out | ✓ | ✓ | ✗ |
| POST → hold_reserved | ✓ | ✓ | ✓ |
| POST → off_market | ✓ | ✓ | ✗ |
| GET suggested transitions | ✓ | ✓ | ✓ |

(advisor / porter / f_and_i_manager / collections all
receive 403 on every M5 endpoint.)

**User: confirm the per-transition matrix + reuse-vs-
new-class choice. Especially: is `recon_manager`
authorized to mark `hold_reserved`? Recommendation is
yes.**

## Chosen decisions (do not require user review)

§5.c bootstrap stage (Option C — existing
`is_available=True` → `frontline`; existing
`is_available=False` → `off_market`; new vehicles →
`incoming`; migration `0017` includes data-migration
step).

§5.d state-machine implementation (Option B — hand-coded
transition table per VCP explicit recommendation + M4
proven pattern).

§5.g aging measurement scope (Option B — raw
`entered_at` timestamps only in M5; per-stage aging
analytics land in M8).

§5.h deterministic-rule execution model (Option A for
M5 v1 — on-demand `suggest_transitions` only; Option B
post-write hook + Option C scheduled scanner deferred
to M7 or later; helper seam `_evaluate_and_apply_all_rules`
exposed for future async use but not wired into
`advance_stage` calls in M5 v1).

§5.i retail-gating strictness (Option A — hard block;
per-dealer configurability deferred to M6 or later).

§5.j prod deployment (deferred outside M5, same shape
as M4 §5.j).

§5.k backdated transitions (Option A — no backdating
in M5 v1; if operational evidence surfaces, add later).

## Concrete deliverables

### `docs/roadmap/MILESTONE_5_PLANNING.md` — new file

Nine sections + frontmatter:

- Frontmatter: `status: draft`,
  `generated_at_session: SESSION_074`, milestone/name.
- **§0 Engineering practices to preserve** — ten lessons
  carried from M2 §6 + M3 §6 + M4 §6 with M5 adaptation
  notes.
- **§1 Design memo** — twelve operational questions +
  seven design-memo entries per subsystem
  (`VehicleStage`, `VehicleStageEvent`, lifecycle
  service, retail-gating refactor, operator UI, Vehicle
  read-model extension, downstream-milestone enablement).
- **§2 Migration impact review** — 22 rows enumerating
  every existing surface M5 touches with the concrete
  work required.
- **§3 Compatibility checklist** — M1 + M2 + M3 + M4
  invariants M5 must not regress + new M5 invariants
  (model / business / retail-gating / endpoint /
  frontend).
- **§4 Reusable primitives review** — every primitive
  M5 extends or directly reuses.
- **§5 Scope discipline + deferrals** — eleven load-
  bearing decisions (five chosen with rationale; four
  marked `[NEEDS-DECISION-BEFORE-M5.1]` for user review;
  two prod-related deferrals).
- **§6 Anchors that win on conflict.**
- **§7 Increment sequencing** — six increments (M5.1
  – M5.7, no M5.8 send/pilot deferral like M4.8; M5
  scope is narrower than M4).
- **§8 Related documents.**
- **§9 Load-bearing decisions summary** — consolidated
  list of the four items requiring user review before
  M5.1.

### `00-START-NEXT-SESSION.md` overwritten

Points at SESSION_075 = M5.1 core persistence, gated on
user confirming the four §9 decisions at session top.

## Verification evidence

- `python3 manage.py test dealer_ai` → **2,518 pass, 1
  skipped, 0 fail** (unchanged since SESSION_071; M5.0
  is docs-only).
- `python3 manage.py check` → clean.
- `python3 manage.py makemigrations --check --dry-run`
  → "No changes detected."
- **No code changes** in this session. Backend +
  frontend files untouched.
- `npx tsc --noEmit` clean (unchanged since SESSION_072).
- `npx vite build` clean (unchanged since SESSION_072).

## Compatibility

Nothing changed except docs. Every code contract
preserved by definition — M5.0 is documentation only.

## Files changed

- `docs/roadmap/MILESTONE_5_PLANNING.md` — new file
  (1,472 lines).
- `docs/handoffs/SESSION_074_m5_planning.md` — this
  handoff.
- `00-START-NEXT-SESSION.md` — overwritten with M5.1
  priority (gated on §9 decisions).

## Recommended exact scope for SESSION_075 (M5.1 — core persistence)

Per `MILESTONE_5_PLANNING.md` §7 M5.1, subject to user
confirmation of the four §9 decisions at session top.

**Scope.** Two new models (`VehicleStage`,
`VehicleStageEvent`) + migration `0017` + admin
registrations + module-level enum constants
(`VEHICLE_STAGE_CHOICES`,
`VEHICLE_STAGE_TRIGGER_CHOICES`) + cross-tenant
`clean()` guards on both models +
`_TENANT_CARRIER_MODEL_NAMES` tuple extended 15 → 17.
Data migration in `0017` bootstraps a `VehicleStage`
row for every existing `Vehicle` per §5.c Option C
(existing `is_available=True` → `frontline`;
`is_available=False` → `off_market`).

No service module in M5.1. Persistence layer only.

**Tests.** ~40 focused model tests: schema, cross-
tenant guards, enum coverage, tenancy-carrier
registration, bootstrap data migration.

**Backend baseline.** 2,518 → ~2,558. No API. No
frontend.

**Explicit non-goals for M5.1:**

- ❌ Do NOT write `services/vehicle_lifecycle.py` — M5.2.
- ❌ Do NOT modify `services/chat_engine.py` or
  `services/inventory_search.py` — M5.5.
- ❌ Do NOT add any endpoint — M5.4.
- ❌ Do NOT touch frontend — M5.6.
- ❌ Do NOT modify `Vehicle.is_available` field — §5.e
  Option D decision (assuming user confirms) leaves it
  intact.
- ❌ Do NOT modify any M2/M3/M4 substrate.

## Anchors that win on conflict for SESSION_075

1. `docs/PROJECT_RULES.md` — six governance rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone
   5 — business objective + scope boundary.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every M5
   model inherits the four-layer separation. Cross-
   tenant guards at model layer are load-bearing (belt-
   and-suspenders with the M5.2 service + M5.4 endpoint
   layers).
5. `docs/roadmap/MILESTONE_5_PLANNING.md` — §1.1
   `VehicleStage`, §1.2 `VehicleStageEvent`, §2
   migration impact, §3 M5 invariants M5.1 must
   satisfy, §5.a stage enum decision (once user
   confirms), §5.b transition table (informs Meta.constraints),
   §5.c bootstrap decision (informs data migration),
   §7 M5.1 detail.
6. `docs/handoffs/SESSION_074_m5_planning.md` — this
   handoff.
7. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` §6
   lessons (ten inherit unchanged) + §8 M5 bootstrap.
8. `docs/research/VEHICLE_CENTRIC_PIVOT.md` §"Data-
   model changes".
9. `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
   §6.
