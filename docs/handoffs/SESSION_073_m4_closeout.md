---
title: "SESSION_073 handoff — Milestone 4 · Increment 9 (closeout)"
status: historical
type: handoff
date: 2026-08-01
session: 073
milestone: 4
milestone_status: shipped
increment: 9
increment_status: shipped
commit: c070deb
---

# SESSION_073 — Milestone 4 · Increment 9 (M4.9 — closeout)

## What shipped

Documentation-only closeout of Milestone 4. Six deliverables:

1. §3 compatibility sweep in `MILESTONE_4_PLANNING.md`
   with inline evidence citations on every row (~60 rows
   across M1/M2/M3 preserved invariants + M4 new
   invariants).
2. New `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` (8
   sections, ~470 lines) mirroring
   `MILESTONE_3_RETROSPECTIVE.md` shape.
3. New `docs/CAPABILITY_MATRIX.md` §7e "Recon automation
   (Milestone 4, shipped)" enumerating every M4.1 – M4.7
   surface.
4. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §M4 flipped to
   SHIPPED; §M5 promoted to "next active milestone
   (planning pass pending)".
5. `MILESTONE_4_PLANNING.md` frontmatter flipped to
   `status: shipped`; `shipped_at_session: SESSION_073`
   annotation added.
6. `00-START-NEXT-SESSION.md` overwritten with M5.0
   planning-pass priority.

**Zero code changes.** Backend baseline **2,518 pass**,
1 skipped, 0 fail (unchanged). Frontend baseline
unchanged. No migrations. No frontend files touched.

## Session preamble

No planning refinements needed. M4.9 is docs-only per §7
M4.9 + SESSION_072 handoff. **M4.8 (outbound send) is
NOT landing** — planning §5.i + §5.j lock the "no live
send in M4 v1" posture; without a pilot-store engagement,
M4.8 stays deferred. M4 closes at M4.9.

## Read-first pass performed

Per the start-here doc's recommended sequence:

1. `docs/roadmap/MILESTONE_4_PLANNING.md` §3 checklist +
   §5.i + §5.j + §7 M4.9.
2. `docs/handoffs/SESSION_072_m4_inc7_operator_ui.md` —
   scope block for M4.9.
3. All prior M4 handoffs (066 – 072) for commit hashes +
   baseline deltas.
4. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` — the
   8-section retrospective shape M4.9 mirrors.
5. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` — same
   template.
6. `docs/CAPABILITY_MATRIX.md` §7c + §7d — the surface-
   entry shape §7e mirrors.
7. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §M3 SHIPPED
   annotation shape + §M4 + §M5 sections.
8. `docs/handoffs/SESSION_064_m3_inc8_closeout.md` — the
   M3.8 closeout handoff shape.

## Concrete deliverables

### 1. §3 compatibility sweep

Every row in the M1 + M2 + M3 invariants list + the new
M4 invariants list gets an inline `*Evidence: ...*` block
naming the test class / code location / runtime probe
that locks it. ~60 rows total, organized by concern
(Tenancy / Identity / Permissions / Customer-facing /
Safety stack / M2 ledger / M3 substrate / Dealer identity
/ Frontend contracts / Test baseline / Model-layer /
Business-layer / Endpoint-layer / AI + safety-layer /
Ledger integration / Frontend).

Every row is now `[x]` with the evidence recorded. The
few rows that reference specific concrete numbers (test
count 2,518; delta +394; frontend clean) are anchored
against SESSION_073 open state.

### 2. `MILESTONE_4_RETROSPECTIVE.md` — new file

Eight sections mirroring M3 retro:

- §1 Planned scope — RECON research citations + seven
  design-memo entries + ten load-bearing decisions.
- §2 What actually shipped — nine-increment table with
  commit hashes + one-line summaries + test baseline
  evolution (2,124 → 2,518 = +394, zero regressions).
- §3 Sequencing refinements — ten material refinements
  from SESSION_065 plan (Vendor PROTECT, estimate
  retirement, logged semantics, QC-GAP, enum
  reconciliation, no-ledger-stubs, reconsideration
  policy, approve-requires-findings, category mapping,
  `revise_estimate`).
- §4 Deviations — seven accepted improvements; no
  planned scope dropped; M4.8 explicitly deferred.
- §5 Compatibility — highlights zero regressions across
  M1/M2/M3 substrate; M2 ledger byte-for-byte preserved;
  M3 substrate preserved; M4.7 frontend has zero backend
  impact.
- §6 Lessons — ten lessons (seven inherited from M2 §6 +
  M3 §6 with M4 evidence; three new to M4: document
  refinements immediately, compat patches must be honest,
  avoid architectural drift).
- §7 Remaining deferrals — eight items (M4.8 send,
  QcVerification, vendor CRUD UI, per-sentence
  provenance, cost-variance analytics, aging dashboards,
  parts marketplace, re-order draft flow).
- §8 Milestone 5 bootstrap — read-model prerequisites
  already shipped, M5 planning shape mirrors M3.0 +
  M4.0, M4→M5 handoff surface.

### 3. `CAPABILITY_MATRIX.md` §7e — new section

12-row table enumerating every M4 surface:

- Vendor (model + PROTECT contract).
- Recon decision (model + tenant chain guard).
- Work order (model + 4 clean invariants + state
  machine).
- Work-order finding link (through model + 3 clean
  invariants).
- Work-order part (model + 6-status + 7-source
  vocabularies incl. `customer_supplied`).
- Vendor communication (model + 6 clean invariants +
  §1.6.SHIPPED enum reconciliation reference).
- Recon service (15 public functions + 4 domain errors +
  ledger integration constants).
- Vendor communication service (4 functions + 4 domain
  errors + zero real LLM API access).
- Invented-recon-fact scrub (4 regex families + wire-up
  in `apply_post_llm_scrubs`).
- Vehicle read-model extension (`open_work_orders` +
  `has_recon_decisions` @property accessors).
- Ledger integration (5 reference-key families + category
  mapping + vendor snapshot invariant).
- Recon admin API (18 endpoints + new permission class +
  domain-error → HTTP mapping + delegate-only view
  layer).
- Operator recon UI (route + page + 6 extracted
  components + 18 typed API helpers + role gating +
  distinct 401/403/404/409/422/502 UX).

"What is NOT shipped in Milestone 4" tail block
enumerates all eight deferrals with cross-references to
the retrospective §7.

### 4. `IMPLEMENTATION_ROADMAP.md` flip

- §Milestone 4 header changed from "next active milestone;
  planning pass at SESSION_065" to
  "SHIPPED at SESSION_073" with the standard delivery-
  record block (full retrospective + capability matrix
  reference + test baseline delta + session range + M4.8
  deferred note + frontend clean).
- §Milestone 5 header changed to "next active milestone;
  planning pass pending".

### 5. Planning-doc frontmatter flip

`MILESTONE_4_PLANNING.md`:
- `status: draft` → `status: shipped`.
- `shipped_at_session: SESSION_073` added under
  `generated_at_session`.

### 6. `00-START-NEXT-SESSION.md` overwritten

Points at SESSION_074 = M5.0 planning pass. Structured
after SESSION_055 → M3.0 and SESSION_065 → M4.0 planning-
pass invocations.

## Verification evidence

- `python3 manage.py test dealer_ai` → **2,518 pass, 1
  skipped, 0 fail** (unchanged since SESSION_071).
- `python3 manage.py check` → clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- **No code changes** in this session. Backend + frontend
  files untouched.
- `npx tsc --noEmit` clean (unchanged since SESSION_072).
- `npx vite build` clean (unchanged since SESSION_072).

## Compatibility

Nothing changed except docs. Every code contract
preserved by definition — the M4.9 sweep confirms with
inline evidence that every §3 checklist row holds true.

## Files changed

- `docs/roadmap/MILESTONE_4_PLANNING.md` — §3 checklist
  swept with evidence (~60 rows updated `[ ]` → `[x]` +
  inline citations); frontmatter `status: draft` →
  `shipped`; `shipped_at_session` annotation.
- `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` — new file
  (~470 lines).
- `docs/CAPABILITY_MATRIX.md` — new §7e section.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` — §M4 header
  flipped to SHIPPED with delivery-record block; §M5
  header flipped to "next active milestone".
- `docs/handoffs/SESSION_073_m4_closeout.md` — this
  handoff.
- `00-START-NEXT-SESSION.md` — overwritten with M5.0
  planning-pass priority.

## Recommended exact scope for SESSION_074 (M5.0 — planning pass)

Per `IMPLEMENTATION_ROADMAP.md` §Milestone 5.

**Scope.** Documentation-only planning pass mirroring
SESSION_055 (M3.0) + SESSION_065 (M4.0):

- Frame the four operational questions M5 must answer
  (candidates: "is this vehicle front-line ready?"; "what
  stage is this vehicle in?"; "who authorized the stage
  transition?"; "when did stage transitions happen?").
- §1 design memo per subsystem (VehicleStage entity;
  VehicleStageEvent audit log; retail-gating service;
  stage-transition rules per VCP Phase 4).
- §2 migration impact review (M4 substrate is read-only
  from M5's perspective — no changes needed).
- §3 compatibility checklist (M1 + M2 + M3 + M4
  invariants M5 must preserve).
- §4 reusable primitives review.
- §5 load-bearing decisions (state-machine granularity;
  auto-transitions from M4 recon completion vs manual
  transitions; retail-gating hard-block vs advisory;
  aging-per-stage vs static-stage semantics).
- §6 anchors that win on conflict.
- §7 increment sequencing (target: 5–7 increments, one
  per session, ending at M5.N closeout).
- §8 related documents.

**Boundary.** No code changes. Backend baseline **2,518
pass** unchanged. Frontend baseline unchanged.

**Explicit non-goals for M5.0:**

- ❌ Any code change (M5.0 is docs-only per SESSION_055 +
  SESSION_065 precedent).
- ❌ Any migration.
- ❌ Any endpoint / permission / frontend change.

## Anchors that win on conflict for SESSION_074

1. `docs/PROJECT_RULES.md` — six governance rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 5.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every M5
   service entry inherits the tenancy + authorization
   substrate.
5. `docs/handoffs/SESSION_073_m4_closeout.md` — this
   handoff.
6. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` §8 —
   M5 bootstrap notes; read-model prerequisites shipped.
7. `docs/roadmap/MILESTONE_4_PLANNING.md` — M4 acceptance
   contract (shape M5 planning mirrors).
8. `docs/roadmap/MILESTONE_3_PLANNING.md` +
   `MILESTONE_3_RETROSPECTIVE.md` — same shape reference.
9. `docs/research/RECON_MAPPING.md` §"pains" (recon ETA
   mismatch drives the stage-truth need).
10. `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
    §"Inventory categorization" — the seven-value stage
    vocabulary M5 formalizes.
11. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 4 +
    §"Retail eligibility rule" — the VCP semantic contract
    M5 implements.
12. `docs/CAPABILITY_MATRIX.md` §7e — M4 shipped
    surfaces M5 reads.
