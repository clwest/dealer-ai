---
title: "SESSION_064 handoff — Milestone 3 · Increment 8 (verification + closeout)"
status: historical
type: handoff
date: 2026-08-01
session: 064
milestone: 3
milestone_status: shipped
increment: 8
increment_status: shipped
commit: 8ce3f84
---

# SESSION_064 — Milestone 3 · Increment 8 (M3.8 — verification + closeout)

## What shipped

Documentation-only session closing out Milestone 3. **Zero code
changes.** Backend baseline **2,124 pass** unchanged. Frontend
`tsc --noEmit` + `vite build` clean.

Milestone 3 is now formally shipped: `MILESTONE_3_PLANNING.md`
frontmatter flipped to `status: shipped`; §7 M3.8 annotated
SHIPPED; every §3 compatibility checkbox annotated with
evidence; new `MILESTONE_3_RETROSPECTIVE.md` written;
`CAPABILITY_MATRIX.md` §7d added; `IMPLEMENTATION_ROADMAP.md`
§M3 marked SHIPPED and §M4 promoted to active.

## Compatibility sweep result

**Every checkbox in `MILESTONE_3_PLANNING.md` §3 annotated with
evidence.** See that document (§3 both subsections) for the
per-row citations.

Summary by section:

- **M1 + M2 preservation (39 rows)** — all verified true.
  Tenancy substrate, identity + auth, endpoint permissions,
  customer-facing surfaces, safety stack, M2 ledger, dealer
  identity resolution, frontend contracts, test baseline all
  unchanged. Evidence includes test class names + git-log
  confirmations that key files (`services/vehicle_ledger.py`,
  `services/llm_safety.py`, `services/dealer_config.py`)
  are byte-for-byte untouched.
- **New M3 invariants (30 rows)** — all verified true via
  focused tests. Model-layer (10 rows) locked by
  test_condition_report / test_condition_finding /
  test_condition_finding_photo; business-layer (5) by
  test_condition_report_service; endpoint-layer (8) by
  test_admin_condition_report + test_admin_condition_report_photos;
  storage-layer (4) by test_photo_storage; frontend (9) by
  code inspection + tsc/build clean.
- **One row honestly downgraded** — the "advisor-role user
  navigating to the URL sees the 403 UI" row was clarified:
  shipped behavior is "read-only presentation for non-write
  roles" (per SESSION_063 spec), not a full-page 403. The
  §3 annotation explains this discrepancy rather than
  silently ticking. Server-side 403 is enforced on all
  M3.6A/B endpoints (locked by 48 permission-matrix tests),
  but the page itself renders read-only content for
  advisors.
- **One row explicitly deferred** — the anonymous-redirect
  behavior is inherited from M1 · 4E `<RequireAuth>` and
  unchanged in M3; the specific "advisor navigates to a
  condition-report URL and sees the redirect" as a rendered
  page remains operator first-live-use verification per the
  SESSION_063 honesty rule.

## Retrospective summary

`docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` written — ~460
lines, 8 sections following the M2 retro shape adapted to
SESSION_064 spec. Highlights:

- **§2 What Actually Shipped** — increment-by-increment
  table with commits: M3.0 `872f8a0` → M3.1 `2e89913` →
  M3.2 `0c98f2e` → M3.3 `c736d03` → M3.4 `3dd56f7` → M3.5
  `5ebdc15` → M3.6A `f80a6d1` → M3.6B `e90af35` → M3.7
  `8e9a5b2` → M3.8 (this session).
- **§3 Sequencing refinements** — 4 material refinements
  documented as planned-vs-executed pairs: UUID public_id
  identity (M3.1), `dealership=` on every function (M3.2),
  storage-first delete strategy (M3.5), M3.6 A/B split
  (M3.6). Plus 3 M3.4 tightenings (`STORAGES` dict,
  dedicated alias, no `moto`).
- **§4 Deviations** — 6 accepted improvements + 5 true
  compromises, separated clearly. True compromises
  include: no persistent `UploadIntent` binding (attach-
  side verification is sufficient for v1), not fully
  transactional delete (fails in safer direction), no
  `assertNumQueries` on read-latest endpoint, no
  component-test framework, 3 400-expected test deferrals.
- **§5 Compatibility** — M1 tenancy, M1 auth, M1·4D +
  M2.6 permissions, M2 ledger substrate, safety pipeline,
  public showroom all unchanged. Verified with git-log
  confirmations of untouched files.
- **§6 Lessons** — 10 durable engineering lessons for
  future contributors: increment discipline;
  backend-first architecture; provider-neutral boundaries;
  service ownership; local/prod parity; honest verification
  reporting; storage-first deletion; document refinements
  immediately; compat patches must be honest; avoid
  architectural drift.
- **§7 Remaining deferrals** — 5 items, all with explicit
  rationale (not feature-requests-reclassified).
- **§8 M4 Bootstrap** — engineering context M4 should
  inherit. `ConditionFinding` is the M4 seam;
  `recon_manager` role does not exist yet; M4 first
  surfaces the AI-drafts-vendor-emails role; new post-LLM
  scrub will land alongside.

## Documentation updates

Files touched this session:

- **Modified** `docs/roadmap/MILESTONE_3_PLANNING.md` —
  frontmatter `status: draft` → `shipped`; §3 checklist
  fully annotated (both subsections); §7 M3.8 entry
  annotated SHIPPED with the session's shipped-surface
  manifest.
- **New** `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md`
  (~460 lines, 8 sections).
- **Modified** `docs/CAPABILITY_MATRIX.md` — frontmatter
  `last_verified` + `verified_against_commit` refreshed to
  2026-08-01 / `8e9a5b2`. Objective baseline updated to
  2,124 test count + 553 kB bundle. **New §7d "Structured
  condition report (Milestone 3, shipped)"** with 10-row
  shipped-surface table + explicit deferred-items list.
- **Modified** `docs/roadmap/IMPLEMENTATION_ROADMAP.md` —
  §Milestone 3 heading annotated `SHIPPED at SESSION_064`
  with retrospective link reference block. §Milestone 4
  heading transitioned from "(drafted, not authorized)" to
  "(next active milestone; planning pass at SESSION_065)".
- **New** `docs/handoffs/SESSION_064_m3_inc8_closeout.md`
  — this handoff.
- **Modified** `00-START-NEXT-SESSION.md` — overwritten
  with SESSION_065 = M4.0 planning-pass priority.

**`DEFERRED_IDEAS.md` NOT created.** Every deferral
surfaced during the sweep already has a home in an
existing planning / retrospective / handoff doc. Per
`DOC_GOVERNANCE.md`: avoid creating another place
information can hide.

## Verification results

- `python3 manage.py test dealer_ai` — **2,124 pass, 1
  skipped, 0 fail** (unchanged from post-M3.7).
- `python3 manage.py check` — "System check identified no
  issues (0 silenced)."
- `python3 manage.py makemigrations --check --dry-run` —
  "No changes detected."
- `npx tsc --noEmit` — exit 0.
- `npx vite build` — success. Bundle 552.78 kB (gzip
  150.79 kB). Same pre-existing chunk-size warning.
- Zero code files modified this session (verified via git
  status). Every change is documentation.

## Milestone audit

Four questions from the SESSION_064 spec, answered with
evidence rather than opinion.

### 1. Does the shipped implementation satisfy the original research-backed business problem?

**Yes.** The M3 planning artifact (§1.0) enumerated six
operational questions from the research corpus. Evidence
that each is now answerable through the shipped surface:

- Q1 *"What defects / needed work / missing items were
  found?"* — `ConditionFinding.description` + `category`
  (12-value enum from RECON §2.1). Locked by
  `test_condition_finding.ConditionFindingCreate.*`.
- Q2 *"How severe is each finding?"* — `severity` (4-value
  enum in escalation order per RECON §2.2). Locked by
  `test_condition_finding.SeverityChoicesVocabulary`.
- Q3 *"Who inspected the vehicle, and when?"* —
  `ConditionReport.inspector_name` (required CharField per
  RECON §2.4) + `inspected_at` (required DateTimeField) +
  `mileage_at_inspection` (required PositiveIntegerField).
  Distinct from `authored_by` (transcriber) per RECON §2.4
  discipline.
- Q4 *"What does each finding look like?"* —
  `ConditionFindingPhoto` many-per-Finding with signed
  read URLs (M3.4 storage + M3.5 upload workflow + M3.6B
  photo endpoints). Public identity is `public_id` UUID
  per M3.1 refinement.
- Q5 *"What is the estimated cost to address?"* —
  `ConditionFinding.estimated_cost` (Decimal, nullable).
  Documentation-only per RECON §3.1 three-tier framework
  (M4 owns the recon-plan decision); invariant locked by
  three test classes across model/service/endpoint layers.
- Q6 *"Is the report finished or still being authored?"*
  — `ConditionReport.status` two-value enum with `draft →
  complete` one-way transition + immutable-once-complete
  semantics. Locked by
  `test_condition_report_service.CompletedReportImmutability`
  (4 tests).

M3 operator UI (SESSION_063) walks the operator through
the workflow end-to-end: create report → add findings →
upload photos → attach → complete. Every M3 endpoint is
tenant-scoped + fail-closed cross-tenant + role-gated
(sales_manager + dealer_owner have write; anyone
authenticated has read). No feature from the research
corpus's M3 scope is missing.

### 2. Is any M3 implementation incomplete enough that M4 would be forced to compensate for it?

**No.** M4 (Recon Automation) reads `ConditionFinding`
records to draft recon plans and vendor communications.
The seams M4 needs are all shipped and stable:

- `ConditionFinding.estimated_cost` (documentation-only
  today; M4 reads to draft work-order estimates).
- `ConditionReport.status="complete"` (M4 recon-plan
  drafting only reads completed reports).
- `Vehicle.latest_completed_condition_report` `@property`
  accessor (M3.3 shipped this as the M4 entry point).
- `ConditionReport.inspector_name` + `inspected_at` (M4
  vendor emails cite this provenance).
- Public identity `public_id` for photos (M4 attachments
  reference this).

**One structural pre-work item M4 needs but should own
itself** — the `recon_manager` permission class. M2's §5
deferral acknowledged it; M3 did not add it (M3.6A/B
composed `IsSalesManagerOrOwnerAtActiveDealership`
verbatim); M4 is the first milestone that surfaces
recon-manager workflows (vendor-facing users who are not
sales managers per RECON §12.2). This is planned M4 scope,
not M3 debt.

### 3. Is there any architectural debt introduced by M3 that should be paid before M4?

**Minor debt, none blocking M4.** Documented in
`MILESTONE_3_RETROSPECTIVE.md` §4 (True compromises) and
§7 (Remaining deferrals):

- **`assertNumQueries` not locked on
  `admin_condition_report_latest`.** Read cost is 4
  queries baseline (vehicle + report + findings prefetch +
  photos prefetch); no N+1 currently. A future edit could
  regress without a test catching it. Targeted
  query-hardening pass in a later session — does NOT block
  M4.
- **Not-fully-transactional storage delete.** Storage-first
  strategy fails in safer direction (never orphans storage
  objects) but is not transactional across DB + object
  store. No outbox in v1. M4 delete flows can inherit the
  same pattern; if M4 introduces a case where full
  transactionality is required (unlikely for photos), the
  outbox lands then.
- **Three ambiguous 400-expected tests in
  `test_salesperson_and_assignment.py`** (surfaced at M3.4
  compat patch). Pass under both buggy and correct request
  shapes because the endpoint returns 400 either way. Pure
  test-hardening; does not affect production. Not M3 debt
  per se — pre-existing latent bugs surfaced by the M3.4
  pip install; M3.4 fixed the four that mattered (the
  ones expected to return 200).
- **No `UploadIntent` model.** Deferred by spec per
  SESSION_060/062. Attach-side verification (canonical key
  shape + dealership namespace + HEAD metadata match) is
  sufficient for v1. M4 does not need pre-upload intent
  binding.
- **Frontend component-test framework.** Deferred by
  spec since M2.7. Backend tests + `tsc --noEmit` + `vite
  build` are the current safety net. M4 will not change
  this posture without an explicit design decision.

None of the above forces M4 to compensate architecturally.

### 4. If you were onboarding a brand-new engineer tomorrow, would M3 be understandable from the documentation alone?

**Yes.** Evidence:

- **`MILESTONE_3_PLANNING.md`** — full acceptance contract,
  8 sections including design memo (§1), migration impact
  (§2), compatibility checklist (§3, now annotated with
  evidence), reusable-primitives review (§4), scope
  discipline (§5), anchors (§6), 8-increment sequencing
  (§7, all SHIPPED-annotated), related documents (§8).
- **`MILESTONE_3_RETROSPECTIVE.md`** — 8 sections
  synthesizing what shipped, what deviated, what remains
  deferred, and the M4 bootstrap context.
- **`CAPABILITY_MATRIX.md` §7d** — 10-row shipped-surface
  table with concrete file paths + test class references +
  invariant citations, plus explicit deferred-items list.
- **`docs/handoffs/SESSION_055_..._064_*.md`** — 10
  per-session handoffs, each carrying its own
  read-first list, shipped-surface manifest, and
  recommended scope for the next session. A new engineer
  walking these in order would replay the milestone
  decision-by-decision.
- **`docs/roadmap/IMPLEMENTATION_ROADMAP.md` §M3** —
  business objective + related research + operational pain
  + gap statement + scope boundary + shipped annotation.
- **In-code documentation** — every service module carries
  a module docstring explaining layer discipline + deferred
  scope. `services/condition_report.py` (~830 lines) and
  `services/photo_storage.py` (~1000 lines) are readable
  standalone; every domain error class carries a docstring
  citing which HTTP status the endpoint layer maps it to
  and why.
- **Test files as documentation** — test class names
  spell out the invariants they lock (e.g.
  `CompletedReportImmutability`, `EstimatedCostStillNoOp`,
  `StorageKeyLeakageNegative`, `NoStorageKeyLeakage`,
  `PublicSurfacesNeverExposeConditionReports`).

**One residual friction for the new engineer** — the M3.6
A/B split appears as two separate handoffs (SESSION_061 +
SESSION_062) and two SHIPPED annotations in the planning
doc; the retro §3 explicitly documents this as one M3.6
delivered in two sub-increments, so the split is
discoverable but requires reading both handoffs.

## Final test baseline

- Backend: **2,124 pass, 1 skipped, 0 fail** (unchanged
  from post-M3.7).
- Frontend: `tsc --noEmit` clean; `vite build` clean.
- Delta across Milestone 3: +371 tests (1,753 → 2,124),
  zero regressions.

## Files changed (SESSION_064)

- Modified: `docs/roadmap/MILESTONE_3_PLANNING.md` —
  frontmatter status flipped to `shipped`; §3 checklist
  annotated in-place; §7 M3.8 annotated SHIPPED.
- New: `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md`.
- Modified: `docs/CAPABILITY_MATRIX.md` — frontmatter
  refreshed; §Objective baseline refreshed; new §7d added.
- Modified: `docs/roadmap/IMPLEMENTATION_ROADMAP.md` —
  §M3 SHIPPED annotation; §M4 promotion.
- New: `docs/handoffs/SESSION_064_m3_inc8_closeout.md` —
  this handoff.
- Modified: `00-START-NEXT-SESSION.md` — overwritten with
  SESSION_065 = M4.0 planning-pass priority.

**Zero code files modified this session.**

## Recommended exact scope for SESSION_065 (M4.0 — Milestone 4 planning pass)

Per `IMPLEMENTATION_ROADMAP.md` §Milestone 4 + the M2.0
(SESSION_045) and M3.0 (SESSION_055) precedents:

**Scope. Documentation-only.** Write
`docs/roadmap/MILESTONE_4_PLANNING.md`. Mirror the shape
`MILESTONE_2_PLANNING.md` + `MILESTONE_3_PLANNING.md`
proved out. Eight sections:

1. **Engineering practices to preserve** (M2 + M3
   retrospectives §6 lessons).
2. **Design memo** — subsystems M4 will ship, each
   citing research (`RECON_MAPPING.md` §3, §4, §6, §7,
   §11) + business question answered + primitive
   extended.
3. **Migration impact review** — every existing surface
   M4 touches with required work.
4. **Compatibility checklist** — invariants M4 must
   preserve (M1 + M2 + M3).
5. **Reusable primitives review** — what M4 extends vs.
   parallels.
6. **Scope discipline + deferrals** — including any
   load-bearing decisions (e.g. how the AI vendor-email
   draft flow interacts with the safety stack).
7. **Anchors that win on conflict.**
8. **Increment sequencing** — 6-8 increments, one per
   session.

**Explicit non-goals for M4.0:**

- ❌ Any code change.
- ❌ Any migration.
- ❌ Drafting `services/recon_plan.py` or any M4
  implementation module.
- ❌ Frontend work.

**Key M4 design decisions the planning pass must resolve:**

- Recon-manager permission class shape (does it split
  further into "recon-manager" vs "recon-tech"?).
- Work-order lifecycle (draft → assigned → in-progress →
  complete → invoiced) — service or FSM library?
- Vendor entity design — M2 `VehicleCost.vendor` is
  free-text; does M4 promote to FK?
- AI vendor-email drafting — new post-LLM scrub for
  vendor-facing text (analogous to M2.5
  `_scrub_acquisition_price`).
- Findings → work-order → estimate `VehicleCost` seam —
  how does the M2 ledger's `is_estimate=True` flow tie
  in?
- First-live-prod deployment — M4 is likely the first
  milestone that requires prod (RECON §12.2 sign-off
  happens at the store; vendor emails go outbound).

**Boundary.** Backend baseline unchanged (2,124).
Frontend unchanged. No test files touched.

## Anchors that win on conflict for SESSION_065

1. `docs/PROJECT_RULES.md`.
2. `docs/DOC_GOVERNANCE.md`.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4.
4. `docs/roadmap/AUTHENTICATION_MODEL.md`.
5. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §8 —
   engineering context M4 inherits from M3.
6. `docs/roadmap/MILESTONE_2_PLANNING.md` + M3_PLANNING —
   shape templates.
7. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 + M3_RETRO
   §6 — lessons.
8. `docs/research/RECON_MAPPING.md` §3 (recon planning +
   three-tier framework) + §4 (vendor mgmt) + §6 (parts
   procurement) + §7 (workflow) + §11 (vendor
   communications).
9. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 3 (M4
   phase).
10. `docs/CAPABILITY_MATRIX.md` §7c + §7d (M2 + M3 surface
    M4 builds on).

## Operational state (post-SESSION_064)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015`. Test baseline: **2,124 pass**, 1 skipped,
  0 fail (unchanged).
- **Backend (prod):** NOT active (M4 is likely the first
  milestone that requires it).
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  clean. `vite build` clean.
- **Frontend (prod):** NONE.
- **DRF defaults + CSRF + permissions:** unchanged.
- **Env-override surface:** unchanged.
- **Milestone 3 shipped surface:** COMPLETE (all 8
  sub-increments SHIPPED and annotated in the planning
  doc). `MILESTONE_3_PLANNING.md` frontmatter is now
  `status: shipped`. `IMPLEMENTATION_ROADMAP.md` §M3 is
  SHIPPED; §M4 is the active milestone.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Every deferral has a home in an existing
  planning / retrospective / handoff doc.
- **Dev DB seeded users:** `smoke_owner` + `smoke_advisor`.
  Unchanged.
