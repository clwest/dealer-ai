---
date: 2026-07-31
title: SESSION_034 — business domain map + implementation roadmap
type: implementation-planning (docs-only)
test_baseline: 1300 pass, 1 skipped (unchanged — docs-only session)
persona: Copper Canyon Auto (Yuma, AZ)
picks_up_from: SESSION_033_discovery_corpus_and_project_rules.md
migration: none (docs-only)
research_commit: ff0e986
domain_map_commit: TBD  # this commit
roadmap_commit: TBD    # same commit
---

# Session handoff — business domain map + implementation roadmap

SESSION_034 executed the implementation-transition-prep session
defined by SESSION_033's start-here doc. It ingested the
completed research corpus, produced a single highest-level
business reference (`docs/BUSINESS_DOMAIN_MAP.md`), reconciled
that business shape against the shipped codebase, and produced
the implementation contract (`docs/IMPLEMENTATION_ROADMAP.md`)
that governs every subsequent implementation session.

**No implementation code was written.** No models were designed.
No endpoints were sketched. Per the SESSION_034 brief, this
session's job was to transform the completed research corpus
into a disciplined implementation strategy — not to begin
building it.

**Test baseline: 1300 pass, 1 skipped, 0 fails, zero regressions
(unchanged — docs-only session).**

## What shipped (this commit)

### `docs/BUSINESS_DOMAIN_MAP.md` (new, 12 sections)

The single highest-level business reference for the project.
It answers one question: *how does an independent used-car
dealership actually operate from beginning to end?* Sections:

1. Core reframe — an indie dealership is two interlocking
   businesses (merchandising + lending) sharing a store.
2. Vehicle journey — 11 canonical stages (acquisition through
   delivered), with primary owner per stage.
3. Customer journey — 8 lifecycle segments (prospect through
   repeat / referral), plus a distinct BHPH portfolio track.
4. Six departments — identity, rhythm, ownership pattern,
   boundary for each of Inventory & Acquisition, Recon, Sales,
   Finance (F&I), Accounting, BHPH Operations.
5. Nine shared business entities — Vehicle, Customer, Deal,
   Vendor, Lender, Employee, Documents, Financial Transactions,
   + Time as the implicit ninth entity.
6. Cross-department information flow matrix — the load-bearing
   handoffs the mapping docs name.
7. Cross-department responsibility flow — who is accountable
   for what, at which event.
8. Critical operational touchpoints — the 10 seams where
   documented pain concentrates.
9. Financial flow overview — three intertwined cycles
   (inventory dollar cycle, deal per-copy cycle, BHPH portfolio
   cycle).
10. Where documented pain concentrates — a heat-map summary.
11. Anchors that win on conflict.
12. Related documents.

The doc is deliberately software-free — zero endpoint paths,
model names, or UI descriptions. Every claim traces to the
research corpus (six mapping docs + two pivots at commit
`ff0e986`).

### `docs/IMPLEMENTATION_ROADMAP.md` (new, 8 sections + 13 milestones)

The implementation contract. Sections:

1. How to read the document.
2. Reconciliation summary — 7 sub-sections mapping every major
   business capability to its status (F / P / N) against the
   shipped codebase, with reusable-primitive citations.
3. Existing reusable primitives — a catalog of 10 numbered
   primitives (§3.1 llm_safety, §3.2 payment_engine, §3.3
   drafting patterns, §3.4 handoff-packet builder, §3.5
   Vehicle model, §3.6 inventory_import, §3.7 recommended-
   actions engine, §3.8 leads + salesperson system, §3.9
   dealer_config resolver, §3.10 onboarding profile).
4. Milestone sequence — 13 milestones each with business
   objective, related research citation, operational pain
   resolved, existing reusable primitives, gap, scope
   boundary, recommended-order justification.
5. Explicit non-goals and deferrals (per the Discovery Rule:
   deferred, never discarded).
6. Scope-discipline verification — self-check table applying
   the two Scope Discipline questions to every milestone.
7. Anchors that win on conflict.
8. Related documents.

The 13 milestones in order:

| # | Milestone | Depends on |
|---|-----------|-----------|
| 1 | Multi-tenant + role-based access foundation | — |
| 2 | Vehicle investment ledger | 1 |
| 3 | Structured condition report | (1) |
| 4 | Recon automation (drafted, not authorized) | 2, 3 |
| 5 | Vehicle lifecycle stages + retail gating | 2, 3, 4 |
| 6 | Photography + listing generation | 1, 5 |
| 7 | Async infrastructure | (M1-M6 generate real work) |
| 8 | Operational intelligence | 2-5, 7 |
| 9 | Sale + delivery closure | 2, 5 |
| 10 | Finance (F&I) deal desk | 1, 9 |
| 11 | Sales non-chat channels + customer-journey completeness | 7, 8 |
| 12 | BHPH portfolio operations (v1) | 1, 7, 9, 10 |
| 13 | Accounting reconciliation core | (layered onto 2, 4, 9, 10, 12) |

Milestones 1-9 adopt the Vehicle-Centric Pivot phase plan
verbatim; Milestones 10-13 add the Finance / Sales-completeness
/ BHPH / Accounting surfaces that the VCP does not cover.

### Session-close artifacts (this commit)

- **This handoff** (`docs/handoffs/SESSION_034_business_domain_map_and_roadmap.md`).
- **`00-START-NEXT-SESSION.md`** overwritten with SESSION_035
  priority (Milestone 1 — multi-tenant + auth foundation).

## Method used (for the audit trail)

1. **Read the corpus.** Read `docs/PROJECT_RULES.md` and
   `docs/CAPABILITY_MATRIX.md` directly. Read
   `INDEPENDENT_DEALER_PIVOT.md` and `VEHICLE_CENTRIC_PIVOT.md`
   directly. Delegated the six large department mapping docs
   to parallel Explore agents with structured extraction
   prompts (scope, workflow, entities owned, entities consumed,
   outputs, pain points verbatim, decisions, roles,
   documents, money flows, external parties, quotes to
   preserve). The extractions preserved verbatim wording where
   requested and were the primary synthesis input.
2. **Synthesize domain map.** Wrote
   `docs/BUSINESS_DOMAIN_MAP.md` from the extractions, cross-
   referencing every claim to a specific mapping doc.
3. **Reconcile.** Walked every business capability in the
   domain map against every capability in
   `CAPABILITY_MATRIX.md`. Result is Section 2 of the roadmap.
4. **Sequence milestones.** Adopted VCP's Phase 0-8 plan for
   the vehicle-operational track (Milestones 1-9). Added
   Milestones 10-13 for the Finance / Sales-completeness /
   BHPH / Accounting surfaces from SESSION_033 mappings.
5. **Scope-discipline self-check.** Verified every milestone
   traces to at least one documented pain, cites at least one
   reusable primitive or documents its greenfield honesty, and
   has an explicit scope boundary. Section 6 of the roadmap.

## Two roadmap-level tensions preserved for user decision

Both are captured in Section 6 of the roadmap; noting here for
next-session visibility.

1. **Multi-photo storage.** Milestone 3 introduces the first
   real multi-photo storage need. The user may prefer to
   ship a small pre-M3 storage-story milestone (S3-compatible
   + CDN, env-configured) rather than absorbing it into M3's
   scope. VCP §"Technical debt to pay down FIRST" flags this
   as a real dependency but doesn't fully scope it.
2. **Accounting shape.** Milestone 13 is deliberately
   structured as an incremental overlay on Milestones 2, 4,
   9, 10, 12 rather than a monolithic milestone. If a future
   session decides accounting is easier to reason about as a
   discrete phase, that structural decision can be revisited
   with explicit user approval.

## What did NOT happen

Per the SESSION_034 brief, explicitly *not* attempted:

- ❌ No implementation code changes.
- ❌ No new research topics introduced (discovery remained
  closed).
- ❌ No specific Django models, API endpoints, or UI layouts
  designed.
- ❌ No roadmap expansion into a comprehensive architectural
  document.
- ❌ No re-litigating of the VCP phase sequence (the sequence
  was adopted as-is, extended with M10-M13).

Two edge cases handled:

- Two operational judgment calls (Milestone 3 storage, Milestone
  13 accounting shape) are captured as deferred user decisions
  in Section 6 of the roadmap, per the Discovery Rule.
- Where the VCP used code language ("VehicleAcquisition
  model") the roadmap milestones translated to business
  capability ("acquisition record") because the SESSION_034
  brief explicitly said "Do not describe models, APIs, UI, or
  code structure. Remain focused on business capability."

## Final review verification

Per the SESSION_034 brief's Final Review criteria:

- ✅ No new product capabilities introduced. Every milestone
  traces to a research doc committed at `ff0e986`.
- ✅ Every implementation recommendation traces back to the
  research corpus. Each milestone has a "Related research"
  subsection with specific doc + section citations.
- ✅ Existing capabilities reused whenever practical. Section
  3 catalogs 10 reusable primitives; every non-greenfield
  milestone cites specific primitive numbers. Milestones 1,
  3, 7, and 13 have honest greenfield notes.
- ✅ Discovery did not resume. No new research docs created.
  No mapping-doc content re-interpreted or expanded.
- ✅ Scope remained controlled. Section 5 lists explicit
  deferrals. Each milestone has a scope boundary. Section 6
  verification passed for all 13 milestones.

## Deferred to future milestones

Captured in `docs/IMPLEMENTATION_ROADMAP.md` §5. Nothing
requires attention this session; the deferrals are the
already-scoped-but-out-of-current-milestone list.

## Notes for the next session

- **Start-here (00-START-NEXT-SESSION.md)** now points at
  **Milestone 1 — Multi-tenant + role-based access foundation**.
- **Read order** for the next session: (1) `PROJECT_RULES.md`,
  (2) `IMPLEMENTATION_ROADMAP.md` §Milestone 1 + §Section 3
  primitives, (3) `BUSINESS_DOMAIN_MAP.md` §5.5 Lender + §7
  Responsibility flow (both call out Milestone 1's
  compliance context), (4) `CAPABILITY_MATRIX.md` §7 advisor
  slug-obscurity (the specific auth debt Milestone 1
  resolves).
- **Test baseline** remains 1300 pass, 1 skipped. Any
  implementation session must preserve that.
- **Franchise config path** remains supported via env
  overrides. Multi-tenancy in Milestone 1 must not break
  the singleton-onboarding-profile fallback for
  single-tenant local dev.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md` — governance layer.
2. `docs/research/*_MAPPING.md` + pivots — business-truth
   corpus (commit `ff0e986`).
3. `docs/BUSINESS_DOMAIN_MAP.md` — business-shape reference
   (this commit).
4. `docs/IMPLEMENTATION_ROADMAP.md` — implementation contract
   (this commit).
5. `docs/CAPABILITY_MATRIX.md` — verified capability snapshot.
6. `git log --oneline -25` (what actually shipped).
7. `git show HEAD:<path>` (current source).

Narrative synthesis (domain map + roadmap) is a claim.
Research + code + rules are facts.
