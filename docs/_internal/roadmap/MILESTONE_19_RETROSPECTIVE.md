---
title: "Milestone 19 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-02
sessions: SESSION_153 → SESSION_159
milestone: 19
milestone_name: "Founding Dealer Pilot Onboarding"
related:
  - docs/roadmap/MILESTONE_19_PLANNING.md
  - docs/roadmap/MILESTONE_18_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 19
  - docs/PILOT_INVENTORY_TEMPLATE.md
  - docs/PILOT_ONBOARDING_PLAYBOOK.md
---

# Milestone 19 — Retrospective

Written at Milestone 19 close (SESSION_159).
Records what was planned, what shipped,
what deviated and why, and lessons carried
forward for Milestone 20 and beyond.
Mirrors the `MILESTONE_18_RETROSPECTIVE.md`
structure so milestone history remains
directly comparable.

## 1. Planned scope

`MILESTONE_19_PLANNING.md` at SESSION_152
close (drafted at M18.6 per standing user
directive) defined the milestone as
**founder-led pilot conversion substrate**:
the controlled path from a demo tester who
says "I want to try this with my store" to
a safe, usable real-store pilot without ad
hoc database work or code edits.

**§5.a Option V locked at SESSION_153 M19.0
open** with the milestone name **"Founding
Dealer Pilot Onboarding."** Rationale:
tester sessions had not yet happened
between M18 close and M19 open, so Option
T ("process real tester feedback") stayed
deferred. Option V builds the controlled
conversion path so testers who commit have
a place to land — a natural M18 → M19
follow-through.

§5.b–§5.h drafted **eight load-bearing
planning-time decisions** — one more than
the historical seven per milestone,
reflecting the mixed schema / service /
frontend / doc / validation-contract
scope (fourteen planning topics compressed
into eight decisions). §7 sequenced seven
increments (M19.0 planning + M19.1
substrate + M19.2 inventory import + M19.3
endpoints + M19.4 frontend + M19.5 playbook
+ dry-run + M19.6 close-out).

**Original §7 sequencing shipped verbatim.**
All eight SESSION_153 planning-time
decisions confirmed as-recommended at
M19.0 open. §0.a implementation-time
micro-decisions surfaced at every
increment (eleven total across M19.1
through M19.5) — recorded in §0.a
amendments per M5-M18 precedent. Per M10
§9 those are **implementation-time
defaults, not planning-time decisions**,
so they do not count against the streak.
**The streak stands at 85 planning-time
as-recommended M5.1 → M19.0** — ten
consecutive milestones now (M10 + M11 +
M12 + M13 + M14 + M15 + M16 + M17 + M18 +
M19) with every §5 decision confirmed as-
recommended at planning-time open.

## 2. What actually shipped

Every §3 compatibility item verified true;
enumeration below.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M19.0 planning | 153 | `MILESTONE_19_PLANNING.md` expanded from ~800-line skeleton to ~2,200-line active memo. Frontmatter `status: draft` → `status: active`; `milestone_name` set. All eight §5 decisions resolved (Option V + Option A × 5 + Option C × 1 + one-off) — §5.a target selection, §5.b `PilotProspect` pre-tenant operator record, §5.c `services/pilot_onboarding/create_pilot_dealership` shape, §5.d `services/pilot_onboarding/` package layout, §5.e `import_pilot_inventory` result contract, §5.f seven-step `PilotOnboardingChecklist` fixed vocab + readiness precondition, §5.g outbound-guard extension posture, §5.h termination archive / cleanup modes with belt-and-suspenders guard. §1 seven business questions; §2 primitives to extend (M6.3 `services/inventory_import`, M18.1 outbound guard, M13.1 default COA seed, tenancy autofill); §3 M19-specific + universal deferrals; §7 seven-increment sequencing. **Eight §5 decisions confirmed as-recommended** — streak 85 M5.1 → M19.0. | `8892447` |
| M19.1 Backend substrate | 154 | Migration `0048_m191_pilot_substrate.py` bundling four `AddField` on Dealership (`is_pilot`, `outbound_enabled`, `terminated_at`, `termination_reason`) + three `CreateModel` (`PilotProspect`, `PilotOnboardingChecklist`, `PilotOnboardingStep`) + one unique constraint on `(checklist, step_slug)`. Vocab constants: `PILOT_PROSPECT_STATE_*` (4), `PILOT_ONBOARDING_STEP_*` (7 + ORDER tuple), `PILOT_TERMINATION_MODE_*` (2). **New `services/pilot_onboarding/` package** (six modules): `errors.py` (three domain errors), `registry.py` (`create_pilot_dealership` + `list_pilot_dealerships` + `terminate_pilot` with belt-and-suspenders + M18.2 reverse-order cascade), `prospects.py` (`create_prospect` + `advance_prospect_state` state machine + `list_prospects`), `checklist.py` (`advance_step` with readiness precondition + `is_pilot_ready` predicate), `inventory_import.py` (`PilotInventoryImportResult` frozen dataclass + `NotImplementedError` stub), `__init__.py` (18 public symbols). **Register `PilotOnboardingChecklist` + `PilotOnboardingStep` in `_TENANT_CARRIER_MODEL_NAMES`** (50 → **52**; `PilotProspect` intentionally NOT registered per §0.a M19.1 decision 1). **Outbound guard refactored** from identity-based (`is_demo`) to policy-field (`outbound_enabled`) predicate per §0.a M19.1 decision 2 — new `suppress_if_outbound_disabled` verb, deprecated `suppress_if_demo` alias preserved. Test helper `make_pilot_dealership(slug, outbound_enabled)`. 58 focused tests (net +59 after retiring the M18.1 `SuppressIfDemoTests` stub-behavior assertion + rewriting for the new policy-field semantics). **Two §0.a M19.1 implementation-time decisions recorded** — PilotProspect stays pre-tenant (autofill signal requires dealership FK; two SET_NULL FKs preserve conversion audit trail); outbound-guard policy field (`outbound_enabled`) instead of identity-based rename. | `4ffb514` |
| M19.2 Inventory import wrapper + CSV schema doc | 155 | Full body for `services/pilot_onboarding/inventory_import.py::import_pilot_inventory` replacing the M19.1 stub. **Thin wrapper delegating to the shipped M6.3 `services/inventory_import.py::import_rows`** per §0.a M19.2 decision 1 (reuse M6.3's 21-column vocab verbatim — no fork). Three pilot-specific policy overrides per §0.a M19.2 decision 2: belt-and-suspenders `assert dealership.is_pilot` + `NonPilotImportError` (500) domain guard; `mark_missing_unavailable=False` (pilots build inventory over time); stable `source="pilot-inventory-import"` label. Partial-success + re-import-updates semantics inherited from M6.3. Accepts `str`/`Path`/file-like `csv_source` — tests use `StringIO`; endpoint layer passes `UploadedFile`. **New reference doc** `docs/PILOT_INVENTORY_TEMPLATE.md` documenting the shipping M6.3 vocab as the authoritative pilot schema (required vs. recommended vs. optional columns + alias tables + example CSV + partial-success semantics + rollback / recovery). 32 focused tests (constant + shape contracts + guards + happy paths + rejected rows + CSV edge cases inherited from M6.3 + re-import + zero-drift). One M19.1 stub-behavior test retired; dataclass-shape test preserved. | `23e92da` |
| M19.3 Backend admin endpoints | 156 | New view module `dealer_ai/views_pilot_onboarding.py` (343 lines) with four lifecycle handlers wrapping the M19.1 service verbs: `admin_pilot_create` (`POST /admin/pilots/create/`, 201/400/409), `admin_pilot_list` (`GET /admin/pilots/`, 200 active-only), `admin_pilot_checklist_advance` (`POST /admin/pilots/<slug>/checklist/advance/`, 200/400/404/409), `admin_pilot_terminate` (`POST /admin/pilots/<slug>/terminate/`, 200/400/404/500). Three request-body serializers + three projection helpers including `_project_checklist` which surfaces steps in `PILOT_ONBOARDING_STEP_ORDER` order with placeholder rows for uncompleted steps (stable UI render regardless of insertion order). URL wiring adds four paths — **admin surface 108 → 112**. 31 focused tests. **Two §0.a M19.3 implementation-time decisions recorded** — inventory-import endpoint deferred to M19.4 alongside its frontend consumer (M19.3 stays lifecycle-focused); `IsAuthenticated` alone (neither `IsDealerOwnerAtActiveDealership` nor `IsSalesManagerOrOwnerAtActiveDealership` fits — at create time no target pilot exists; adding a new `IsPlatformOperator` class would break the zero-drift streak). | `c3b58ba` |
| M19.4 Frontend admin surface + inventory-import endpoint | 157 | **Fifth pilot admin endpoint** `POST /admin/pilots/<slug>/inventory/import/` in `views_pilot_onboarding.py` — multipart CSV upload wrapping `import_pilot_inventory`. DRF `FileField` on `InventoryImportRequestSerializer` per §0.a M19.4 decision 1 + `@parser_classes([MultiPartParser])` (fixed a 415 discovered at implementation time). URL wiring adds one path — **admin surface 112 → 113**. **Additive fix** in `services/pilot_onboarding/inventory_import.py::_read_csv_rows` — detects bytes-mode file-likes (Django `UploadedFile`) and wraps them in `io.TextIOWrapper` with `utf-8-sig` encoding (preserves BOM tolerance); text-mode `StringIO` path unchanged. New API client functions + DTO types in `frontend/src/lib/api.ts`. **New component** `frontend/src/components/pilots/PilotOnboardingSection.tsx` (~530 lines) with four sub-panels: `PilotCreateForm` (slug + name + owner_username with disabled-until-filled submit + friendly 409/400 error surfaces), `PilotList` (clickable rows with ready / in-progress badges), `PilotDetailPanel` wrapping `ChecklistStepper` (ordered steps + complete button per uncompleted step + readiness-precondition 409 error surface), `InventoryUploadPanel` (file input + submit + accepted / rejected counters + expandable rejected-rows details block), `TerminateForm` (mode picker + reason textarea + two-step confirm gate). Embedded into `DealerAdmin.tsx` per §0.a M19.4 decision 2 (extend `/dealer-ai-admin` in place; operator route count stays at 20). 10 backend + 13 frontend Vitest tests. | `ad9bf21` |
| M19.5 Playbook + end-to-end dry-run | 158 | **New end-to-end test suite** `tests/test_m195_pilot_dry_run.py` (571 lines, 10 focused tests) per §0.a M19.5 decision 1 (dry-run ships as Django `TestCase` for per-push CI signal). `FullPilotJourneyDryRun.test_full_journey` — one coherent narrative test method walking thirteen phases: prospect intake → qualify → pilot create → convert prospect → configure store → import inventory (partial success 2 accepted + 1 rejected) → advance user + capability steps → readiness gate → outbound suppression (both pilot AND demo via policy field) → cross-tenant isolation → non-pilot safety guards → terminate archive → verify pilot leaves operator surface + children survive + prospect FK still resolves. `EndpointE2EDryRunTests` drives all five M19.3+M19.4 admin endpoints through one authenticated `APIClient` session. `SafetyGuardDryRunTests` covers non-pilot / non-demo refusal + deprecated alias compatibility + prospect FK survival across archive termination. `M195ZeroDriftTests` holds tenancy carriers (`>=` 52), admin endpoints (`>=` 113), permission-class exact-set equality (streak now nineteen consecutive milestones M10 → M19.5). **New operator playbook** `docs/PILOT_ONBOARDING_PLAYBOOK.md` per §0.a M19.5 decision 2 — text + `data-testid` selectors, no screenshots (frontend test asserts on selectors so playbook stays honest). Covers all thirteen phases + rollback / recovery + refs to the authoritative dry-run test. One implementation-time correction: initial dry-run passed `dealer_business_name` to `profile_kwargs` but `DealerOnboardingProfile` has `dealership_name` (test caught its own guessing). | `89a58c8` |
| M19.6 Close-out | 159 | Documentation-only per M10.8 / M11.7 / M12.8 / M13.4 / M14.5 / M15.2 / M16.2 / M17.3 / M18.6 precedent. Six close-out docs (this retrospective + capability matrix §7t + implementation roadmap §Milestone 19 SHIPPED entry + planning doc frontmatter flip + M20 planning skeleton + session-start refresh) + coordinated commit landing all M19.6 docs. **Milestone 19 — Founding Dealer Pilot Onboarding — SHIPPED.** | (this commit) |

## 3. What was NOT shipped (deferred, not dropped)

Every deferral recorded with a clear
re-entry path.

**M19-specific deferrals** (surfaced at
planning or implementation time; all
carry-forward to M20+):

1. **Prospect intake UI.** `PilotProspect`
   management is currently a Django-admin
   / Python-shell exercise. A future
   increment surfaces prospects to Chris
   via a dedicated admin panel. Re-entry:
   any milestone that touches the pilot
   admin surface with intent to expand
   operator ergonomics.
2. **First live-pilot dry-run against
   staging.** The M19.5 dry-run codifies
   the substrate contract, but does not
   exercise the full stack against a
   staging DB with a real pilot dealer.
   Re-entry: a Milestone 20 candidate on
   its own or bundled with the Playwright
   acceptance-testing candidate.
3. **Demo-aware LLM router / cost caps.**
   Deferred from M18.1 (§0.a decision 1
   there). Re-entry: unchanged — future
   "demo LLM cost caps" decision.
4. **Multi-operator permission class
   (`IsPlatformOperator`).** M19.3
   endpoints gate on `IsAuthenticated`
   alone per §0.a M19.3 decision 2. If
   a second platform operator is ever
   introduced, `IsPlatformOperator`
   scoped to the DealerKit control
   tenant is the natural surface —
   breaks the zero-drift streak with
   intent.
5. **Management-command diagnostic for
   the dry-run.** The M19.5 dry-run is
   TestCase-only per §0.a M19.5
   decision 1. A management-command
   layer (`manage.py pilot_dry_run`)
   would give Chris an operator smoke
   button against staging/prod. Not
   blocked; ships when demand surfaces.
6. **Public / self-serve pilot signup.**
   Every pilot is hand-created by Chris.
   Follows the M18 posture: no public
   surface until commercial validation.
7. **Non-CSV inventory ingest.** No
   pandas / openpyxl / xlrd; no direct
   DMS integration; no scraper adapter
   for pilots. Excel-saved CSV works;
   everything else defers.
8. **Cross-tenant PilotProspect visibility.**
   `list_prospects` returns every row
   with no operator scoping today.
   Acceptable because Chris is the only
   platform operator; re-visit alongside
   the multi-operator deferral.

**Universal deferrals (still valid from
earlier milestones per M18.6 §3):**

- Public self-serve demo signup + hosted-
  demo substrate.
- Production deployment solely for
  validation infrastructure.
- Full customer onboarding automation.
- Product tours / walkthrough overlays.
- Broad clickstream analytics.
- Session recording (video / DOM replay).
- Generic whole-platform UI polish.
- Fake stubs for unfinished capabilities.
- Outbound email / SMS to real
  destinations.
- DMS / lender / bank / auction / bureau /
  payment / accounting-provider
  integrations.
- Pricing logic, billing, subscriptions,
  contracts.
- Chargeback substrate.
- Feedback capture UI form (M18.5
  deferral).
- Every still-valid unblocked-work item
  from M17 §8 (period-close comparison
  view; financial-reports substrate;
  CSV / PDF export of frozen snapshots;
  auto-freeze on schedule; reopen /
  unfreeze; M10 chargeback GL reversal;
  NSF / payment-reversal; category-group-
  aware GL mapping; M14 UX polish;
  sale-reversal; VehicleCost variance;
  deposit / bank reconciliation; method-
  aware fund-flow; BhphFee entity; BHPH
  interest accrual detector).

## 4. Deviations from planned scope

Four deviations from the SESSION_153
M19.0 planning brief. All were
implementation-time responses to
newly-discovered facts, resolved via
§0.a amendments without re-voting the §5
posture.

### 4.1 PilotProspect is NOT a tenancy carrier

**M19.0 planning recommendation** was to
register `PilotProspect` in
`_TENANT_CARRIER_MODEL_NAMES` so the
pre-save autofill signal defensively
attaches the default dealership.

**M19.1 open discovery:** the autofill
signal calls
`instance.dealership = get_default_dealership()`,
which fails if the model has no
`dealership` FK. `PilotProspect` by
design has no such FK (§5.b Option C —
pre-tenant operator record). Registering
would break the autofill contract on
every insert.

**Correction** at §0.a M19.1 decision 1:
`PilotProspect` stays pre-tenant. Two
optional `SET_NULL` FKs
(`source_demo_dealership`,
`converted_dealership`) preserve the
conversion audit trail without forcing
tenant scope. Tenancy carrier count
50 → **52** (only checklist + step
carriers registered) instead of the
planned 50 → 53.

### 4.2 Outbound-guard policy field replaces identity-based rename

**M19.0 planning recommendation** was
to rename `suppress_if_demo` →
`suppress_if_synthetic` and extend the
identity-based predicate to cover both
`is_demo` and `is_pilot`.

**M19.1 open counter-analysis:** the
naive rename couples policy to identity.
A pilot that needs controlled outbound
enablement (per-verb code review before
flip) would require tenant-type
reclassification. Live production
dealerships (created via a future non-M19
path) also need a fail-safe default
until an operator explicitly enables
outbound.

**Correction** at §0.a M19.1 decision 2:
add `Dealership.outbound_enabled =
BooleanField(default=False)`. Refactor
guard to `suppress_if_outbound_disabled`.
Retain deprecated `suppress_if_demo` +
`is_demo_dealership` as backward-compat
shims. Add `is_pilot_dealership` +
`is_outbound_enabled` as diagnostic-only
helpers. Auditability, orthogonality, and
per-tenant control all improve.

### 4.3 M19.2 reuses the M6.3 substrate verbatim

**M19.2 session-start opener sketched
three CSV-column-set options** all
pre-supposing authoring a new schema.

**M19.2 open discovery:** the M6.3
`services/inventory_import.py` substrate
(411 lines) already ships a 21-column
vocab with body-style + condition
aliases, `_parse_features`, UTF-8-BOM
tolerance, currency-format parsing, and
multi-tenant scope. The M19.0 planning
memo explicitly directed "extend the M6.3
substrate as needed (additive; no fork)".

**Correction** at §0.a M19.2 decision 1:
reuse `CSV_FIELDS` verbatim. Pilot
wrapper becomes a thin overlay applying
three policy overrides (belt-and-
suspenders guard, `mark_missing_unavailable=False`,
stable `source` label).
`PILOT_INVENTORY_TEMPLATE.md` documents
the shipping M6.3 vocab as the
authoritative pilot schema rather than
authoring a new one.

### 4.4 Inventory-import endpoint deferred from M19.3 to M19.4

**M19.3 session-start opener leaned
"yes, include at M19.3"** arguing
cohesion (all pilot admin endpoints in
one increment).

**M19.3 open counter-analysis:** the
"frontend upload with no backend
receiver" concern dissolves because
M19.4 ships as one unit (frontend + any
backend it needs). Bundling the endpoint
into M19.4 alongside its consumer keeps
M19.3 lifecycle-focused (create / list /
checklist / terminate) and M19.4
end-to-end (upload UI + endpoint + tests
reviewed together).

**Correction** at §0.a M19.3 decision 1:
defer the endpoint. Admin surface deltas:
108 → 112 at M19.3, 112 → 113 at M19.4.

## 5. Compatibility with existing surface

Verified true at every M19 close.

**Backend model / schema.**
- One additive migration (`0048`) bundling
  four `AddField` on Dealership + three
  `CreateModel` + one unique constraint.
  Zero data migration. Zero row rewrites.
- Every existing tenanted-model write
  path continues to succeed under the
  M13.1 default COA seed contract (which
  the new pilot registry also invokes).
- The new `is_pilot` + `outbound_enabled`
  + `terminated_at` + `termination_reason`
  columns default to safe values on
  existing rows; no behavioral change for
  M1-M18 code paths.

**Service surface.**
- The M19.1 outbound-guard refactor
  preserves the M18.1 `suppress_if_demo`
  API surface via a deprecated alias +
  `DeprecationWarning`. All M18-era demo
  dealerships continue to have outbound
  suppressed (both had `outbound_enabled=False`
  by default at the time of the M19.1
  migration; both continue to suppress).
- The M19.2 wrapper delegates to the M6.3
  substrate without forking. Any M6.3
  behavior change automatically applies
  to the pilot import path; the pilot
  wrapper adds policy overlay only.
- The M19.4 `_read_csv_rows` additive fix
  (bytes-mode `UploadedFile` handling)
  preserves the M19.2 text-mode `StringIO`
  path unchanged; every M19.2 test
  continues to pass without modification.

**DRF admin surface.**
- Five new endpoints (four at M19.3,
  one at M19.4) — admin surface
  108 → 113.
- Every existing endpoint continues to
  route, authenticate, and return the
  same response shape.

**Frontend.**
- Zero new operator routes (§0.a M19.4
  decision 2). New `<PilotOnboardingSection>`
  embedded in the existing `/dealer-ai-admin`
  route. No changes to any other page or
  component.
- Frontend Vitest baseline **140 → 153**
  (+13 new tests, zero regressions).

**Tenancy autofill.**
- Two new carriers (`PilotOnboardingChecklist`
  + `PilotOnboardingStep`) follow the
  M13.1 / M17.1 / M18.1 registration
  pattern. Every write path either
  passes `dealership=` explicitly or is
  caught by the pre_save fallback.

**Guard-by-construction posture.**
- The M18.1 outbound-egress scanner
  contract holds unchanged. The M19.1
  refactor swapped the predicate
  (`is_demo` → `outbound_enabled`)
  without changing the scanner's
  requirement that every future
  `services/` egress verb call the
  guard.

## 6. Lessons

Five lessons carry forward to M20+ and
future planning cycles.

### 6.1 Ground planning-time recommendations in the shipped code first

The M19.2 planning brief sketched three
CSV-column-set options as if authoring a
new schema. A ten-minute grep at M19.2
open would have surfaced the M6.3
substrate. Discovery at M19.2 open cost
zero time (the discovery was the correct
answer), but the planning memo could
have surfaced it at M19.0.

**Carry-forward:** at planning-time memo
draft, include a "primitives to extend"
enumeration that is grepped from the
current codebase, not sketched from
memory. The M19.0 memo did this partially
(§2 listed M6.3 as a reusable primitive);
the M19.2 planning brief lost the thread.

### 6.2 Policy fields beat identity-based renames when the domain is orthogonal

The naive `suppress_if_demo` →
`suppress_if_synthetic` rename would
have worked for the M19 scope but scaled
poorly: coupling send policy to tenant
type conflates two orthogonal concerns.
The M19.1 §0.a decision 2 correction
(`Dealership.outbound_enabled` policy
field) is a durable contract that
supports future live-production
dealerships without requiring tenant-
type reclassification.

**Carry-forward:** when the naive fix
involves coupling A to B ("rename this
verb to also cover that case"), consider
whether A and B are really the same
concept. If not, a policy field is often
the right answer.

### 6.3 Bytes vs. text file-like objects deserve explicit boundary handling

Django's `UploadedFile.read()` returns
bytes; `csv.DictReader` requires text.
The M19.4 discovered gap ("415 Unsupported
media type" first, then bytes-mode
`csv.Error`) forced the extension in
`_read_csv_rows` to detect and wrap.
Neither problem surfaced in the M19.2
test suite because those tests used
`StringIO` (text) exclusively.

**Carry-forward:** any file-like
interface should test both text-mode
and bytes-mode paths at the boundary,
not just the primary usage pattern.
Better still: a single
`_normalize_csv_source` helper that
consumers use, so the polymorphism lives
in one place.

### 6.4 Two-step confirm gates are cheap insurance for destructive verbs

The M19.4 `TerminateForm` component's
two-click gate (`pilot-terminate-init`
reveals `pilot-terminate-confirm`)
prevents accidental single-click
termination, particularly important for
`cleanup` mode. Zero UX friction cost
against the operator's judgment surface.

**Carry-forward:** every destructive
verb surfaced to the operator UI gets a
two-step confirm gate. Cleanup /
reset / delete-cascade in particular
should always require a deliberate
second interaction.

### 6.5 Text + selector labels beat screenshots for internal ops docs

The M19.5 playbook uses `data-testid`
selectors instead of screenshots.
Selectors stay in sync with the code
because the M19.4 component test asserts
on them; screenshots would go stale
immediately. The playbook doubles as
accessibility documentation.

**Carry-forward:** internal operational
docs describe controls by intent + role +
stable selector, not by pixel appearance.
Screenshots belong in customer-facing
marketing artifacts.

## 7. Streak update

**85 planning-time as-recommended M5.1 →
M19.0.** Ten consecutive milestones now
(M10 + M11 + M12 + M13 + M14 + M15 +
M16 + M17 + M18 + M19) with every §5
decision confirmed as-recommended at
planning-time open. §0.a implementation-
time micro-decisions across M19.1
through M19.5 (**eleven in total**:
PilotProspect tenancy posture, outbound-
guard policy field, M6.3 vocab reuse,
pilot-import policy overlay, inventory-
import endpoint deferral, `IsAuthenticated`
alone, DRF `FileField` overlay,
extend-existing-admin-route-in-place,
dry-run as TestCase, text-first playbook
posture) do not count against the streak
per M10 §9.

The pattern that held for the tenth
consecutive time:

1. Draft the §5 recommendations at
   planning close of the *previous*
   milestone.
2. Confirm at the next milestone's
   opening session.
3. Amend §0.a as micro-decisions surface
   per implementation session.
4. Never re-vote a §5 decision mid-
   milestone — file the amendment as
   §0.a instead.

**Zero-drift permission-class streak
extends to nineteen consecutive
milestones** (M10 → M19.5): the M19
substrate introduces zero new permission
classes. Any new-operator-role scenario
that surfaces at M20+ can reuse the
existing seven classes or intentionally
break the streak with a documented
`IsPlatformOperator` decision.

## 8. What M19 unblocks for M20+

The M19 shipped surface is **founder-led
pilot conversion infrastructure**. Its
unlocks are **operational** — Chris can
now convert a demo tester into a live
pilot store through a controlled,
codified path without ad hoc database
work.

**What's now unblocked by having pilot
substrate + inventory import + admin
endpoints + frontend surface + playbook +
dry-run:**

- **Founder-led first pilot conversion.**
  Chris can invite a demo tester who
  says "I want to try this" through the
  M19.5 playbook. The M19.4 admin surface
  gives him the controls; the M19.5
  dry-run gives him the CI signal that
  the substrate holds.
- **Codified operational contract.** The
  M19.5 authoritative dry-run test
  proves the M19.1-M19.4 substrate holds
  end-to-end. Any future change that
  breaks the pilot flow will fire this
  test on the next push.
- **Multi-operator readiness (not
  activation).** The M19.3 endpoints
  gate on `IsAuthenticated` alone;
  swapping to `IsPlatformOperator` when a
  second platform operator is introduced
  is a single-file change (add class in
  `permissions.py` + swap the decorator
  list).
- **Pilot-inventory acquisition
  workflow.** The M19.2 wrapper +
  `PILOT_INVENTORY_TEMPLATE.md` +
  M19.4 upload UI let a pilot dealer
  provide inventory in a controlled
  format without an integrations
  dependency.
- **Live-pilot readiness signal.** The
  M19.1 `outbound_enabled=False` default
  keeps pilots fail-safe until Chris
  explicitly flips them at go-live.

**Still-valid unblocked-work items from
earlier milestones** (per M18 §8):

- Tester feedback ingestion (M18-produced
  CSV; still valid if tester sessions
  happen).
- Willingness-to-pay signal aggregation
  from `TesterFeedback`.
- UX-polish backlog driven by
  `TesterFeedback` content.
- F&I chargeback scenario (§0.a M18.2
  decision 1 deferral).
- LLM cost caps for demo stores (§0.a
  M18.1 decision 1 deferral).
- Every still-valid unblocked-work item
  from M17 §8 (period-close comparison,
  financial reports, CSV / PDF export,
  auto-freeze, reopen / unfreeze, M10
  chargeback GL reversal, NSF /
  payment-reversal, category-group-aware
  GL mapping, M14 UX polish, sale-
  reversal, VehicleCost variance,
  deposit / bank reconciliation,
  method-aware fund-flow, BhphFee
  entity, BHPH interest accrual
  detector).

## 9. Standing question — is M20 the "Operational Journey Validation" milestone?

Per M18 §9 the standing question was
"is M19 the process-real-tester-feedback
milestone?" M19's answer was no — Chris
did not run tester sessions between M18
close and M19 open, so pilot-conversion
substrate (Option V) took the M19 slot.
Option T stays deferred.

**Standing question for M20 close:**
review at the end of M20 whether pilots
have actually converted using the M19
substrate. If yes, M20 or M21 should
inform its own target selection with
what the first live pilot(s) surfaced.
If no live pilot has landed, the
question carries forward.

**Recommendation to bring to M20.0
open:** do not preemptively lock M20 as
any specific candidate. M20 target
selection follows the standard business-
priority pattern at M20.0 open. The
candidate list is intentionally expanded
at M19.6 close-out per §0.a M19.6
decision 2:

- **Candidate T (carry-forward)** —
  process real tester feedback (still
  gated on volume + quality of M18.5
  submissions).
- **Candidate U (carry-forward)** —
  hosted-demo substrate (public self-
  serve signup).
- **Candidate A** — return to accounting
  stream (M18 retrospective's
  designated M20 slot per §8).
- **Candidate P** — onboarding UX
  polish (prospect intake UI, checklist
  progress bar, terminate-flow
  refinements).
- **Candidate L** — first-live-pilot
  staging dry-run — codify the M19.5
  dry-run against a real staging DB
  with a real pilot dealer, not just
  SQLite test fixtures.
- **Candidate M** — multi-operator
  support (`IsPlatformOperator`
  permission class — breaks the
  zero-drift streak with intent).
- **Candidate D** — demo-aware LLM
  router / cost caps (M18.1 §0.a
  decision 1 deferral).
- **Candidate C** — F&I chargeback
  substrate (M18.2 §0.a decision 1
  deferral).
- **Candidate J — Operational Journey
  Validation (Playwright acceptance
  testing).** Build durable Playwright
  acceptance suites executing real
  dealership workflows against the M18
  demo stores + M19 pilot substrate.
  Representative journeys: owner
  morning review, sales manager daily
  startup, recon workflow, office /
  accounting workflow, BHPH collections
  workflow, pilot-onboarding journey.
  Each journey executes end-to-end
  through the shipped UI and validates
  that a dealership can perform
  realistic daily operations using
  shipped capabilities. Establishes
  executable operational acceptance
  tests as part of the milestone
  completion contract alongside unit
  tests, integration tests, capability
  matrix updates, and retrospectives.
  **Intentionally distinct from
  Candidate P** — the objective is
  business-workflow validation, not
  generic UI regression testing.

The full M20 planning memo (SESSION_160)
scopes each candidate + presents the
recommended selection at open. Chris
picks with the full brief in hand.
