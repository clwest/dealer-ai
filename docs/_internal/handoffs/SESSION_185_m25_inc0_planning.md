---
title: "SESSION_185 handoff — Milestone 25 · Increment 0 (M25.0 — planning refinement + target selection)"
status: historical
type: handoff
date: 2026-08-03
session: 185
milestone: 25
milestone_status: in-progress
milestone_name: "Lead-to-Test-Drive Operational Completion"
increment: 0
increment_status: shipped
commit: 4e0a958
---

# SESSION_185 — Milestone 25 · Increment 0 (M25.0 — planning refinement + target selection)

## What shipped

Planning-only session per the M10.0 / M11.0 / M12.0 / M13.0 /
M14.0 / M15.0 / M16.0 / M17.0 / M18.0 / M19.0 / M20.0 / M21.0
/ M22.0 / M23.0 / M24.0 precedent. Full memo expansion from
the M24.5 skeleton + all **eight** §5 load-bearing decisions
resolved at open, with two mid-planning refinements captured
honestly.

**§5.a → A3 + A4 bundle confirmed at open** per the primary
operational-coverage lens applied against the freshly
regenerated audit artifact (153 endpoints, 113 covered, 40
backend-only post-M24). Recommendation ranking under the
lens: A3 > A4 > H > A2. User confirmed the A3 + A4 bundle
and redirected framing from the initial "Sales UI
completeness" phrasing (which invited feature creep) to
**"Lead-to-Test-Drive Operational Completion"** — a single
operational-workflow narrative binding both anchors under
one business question: *Can a salesperson receive a lead,
understand exactly where it came from, assign it, and
schedule the customer's test drive entirely through the
normal product workflow?*

**§5.b → Option A · JSONField variant confirmed** after
empirical verification surfaced a load-bearing surprise
(see Empirical Discovery section below). Original candidate
framing at M24.1-open close treated §3 deferral 14
(webhook platform display) as "a small UI extension (~10-
line addition)." Verification at M25.0 open confirmed that
`platform` is not persisted on `CustomerLead` — the webhook
receives it, dispatches to an adapter, and discards it
after normalization. Adding a `CustomerLead.source_metadata
= JSONField(blank=True, default=dict)` (over a `CharField`
alternative) was selected for durability: additive-forever
contract for future attribution attributes (ad_source,
campaign_id, platform_lead_id, listing_url) without further
migrations, matches codebase JSON precedent
(`ChatSession.extracted_profile`, `TestDrive.
objections_captured`), query support preserved on Postgres
+ modern SQLite JSON1. Junk-drawer risk mitigated by a
typed accessor `CustomerLead.get_source_platform() -> str`
on the model.

**§5.d → Modal-only confirmed.** Initial recommendation
proposed a modal-attached primary path + a secondary
"+ Record test drive" button on
`DealerAiSalesTestDrives`. User rejected the secondary
launch point per a new durable design principle: **one
operational workflow beats two partially-overlapping ones.**
Deferred to M26+ pending operator evidence.

**§5.c / §5.e / §5.f / §5.g / §5.h** all locked as
recommended.

## Starting-state verification (this session)

- `git status` — clean.
- `git log --oneline -8` — top: `dd21d6c Milestone 24
  shipped — Sales Operational Entry (SESSION_180-184)`.
- `origin/main` matches local `HEAD`.
- `python3 manage.py test dealer_ai` — **4,780 pass, 1
  skipped, 0 fail** in ~161s.
- `cd frontend && npm test` — **209 pass** across 30 test
  files in ~4.3s.
- `python3 manage.py check` — clean (0 issues).
- `python3 manage.py makemigrations --check --dry-run` —
  "No changes detected."
- `cd frontend && npx tsc --noEmit` — clean.
- `cd acceptance && npx tsc --noEmit` — clean.
- `redis-cli ping` — `PONG`.
- `gh run list --workflow=acceptance --branch=main` —
  **First real M24 CI run: SUCCESS in 2m33s.** M24 is
  CI-verified shipped.
- Audit artifact regenerated (`python3 -m dealer_ai.
  scripts.audit_operational_surface`): **153 endpoints,
  113 covered, 40 backend-only.** Diff vs shipped:
  walk-in / phone / referral endpoints flipped from
  `wrapper-only` → `covered` (M24 UI consumers).
  Webhook remains wrapper-only per M24.4 no-operator-
  UI design decision. Uncommitted diff on
  `M21_OPERATIONAL_SURFACE_AUDIT.md` will land with
  the M25.0 planning commit.

## Empirical discovery during M25.0 open (informs §5.b + §5.d)

**Surprise 1: `platform` is not persisted on
`CustomerLead`.** Verified in
`backend/dealer_ai/services/leads/channel_intake.py:
record_webhook_lead` — the webhook receives `platform`
as a top-level request field, calls
`get_adapter(platform)`, invokes
`adapter.normalize(payload)` to get normalized kwargs,
then calls `_create_lead(dealership=..., channel=
LEAD_CHANNEL_LISTING_FORM, **normalized)`. The
`platform` string is not passed through — it is
discarded after adapter dispatch. `CustomerLead`
persists only `channel="listing_form"` for all
webhook-origin leads regardless of which platform
originated them. §3 deferral 14 as originally framed
at M24.1-open close ("small UI extension") is not
implementable without a backend model addition. This
promoted the platform-persistence decision to a §5.b
load-bearing question resolved at open (see
`MILESTONE_25_PLANNING.md` §5.b).

**Surprise 2:** `CustomerLeadSerializer` (which feeds
`admin_lead_detail`) does NOT expose `channel` or
`referrer`. Only `AdminLeadListSerializer` (which
feeds `admin_lead_list`) exposes them, added at
M11.6. §3 deferral 13 (referrer display in modal)
therefore requires a small additive serializer
extension. Not a surprise in scope — additive
serializer changes are the M11.6 precedent — but a
surprise in that the M24.1-open scope note ("~20-
line addition") accurately captured the frontend
work but omitted the backend serializer additive.

**Non-surprise (confirmed as expected):**

- `record_test_drive` does not mutate parent lead or
  pipeline state. `TestDrive` has no `status` field.
  A newly-persisted drive appears in
  `admin/test-drives/list/` immediately with no
  additional backend work — the M11.6 list endpoint
  filter by `lead_id` already works,
  `DealerAiSalesTestDrives.tsx` already consumes it.
- Walk-in / phone / referral leads land with empty
  `interested_vehicles` (verified in
  `channel_intake._create_lead` — no vehicle
  attach). Chat leads populate via `lead_service`.
  M25.2 vehicle picker must handle both cases —
  suggestions when present, full inventory
  otherwise (locked as §5.e).
- `TestDrive` FKs (`lead`, `vehicle`) are CASCADE
  same-tenant, `driven_by_user` is SET_NULL from
  `request.user`, `driven_at` defaults to
  `timezone.now()`. All aligned with the M25.2
  form contract.

## Load-bearing decisions confirmed at M25.0 open

Full detail in
`docs/roadmap/MILESTONE_25_PLANNING.md` §5. Summary:

- **§5.a** — Target selection: A3 + A4 bundle framed as
  "Lead-to-Test-Drive Operational Completion."
- **§5.b** — Attribution persistence: Option A ·
  JSONField variant. Add
  `CustomerLead.source_metadata` +
  `get_source_platform()` accessor + adapter wiring
  in `record_webhook_lead`. One migration, no
  backfill (default=dict).
- **§5.c** — Attribution display: display-only,
  no navigation links.
- **§5.d** — Test-drive form attachment: modal-only.
  Secondary launch on
  `DealerAiSalesTestDrives` deferred pending
  operator evidence.
- **§5.e** — Vehicle picker: `interested_vehicles`
  as suggestions + full tenant inventory as
  fallback.
- **§5.f** — Increments: 3 (M25.0 planning ·
  M25.1 attribution + JSONField backend · M25.2
  test-drive UI, with M25.3 close-out folding per
  evidence).
- **§5.g** — DoD: extend M24.3 + M24.4 journeys
  in M25.1, add
  `sales/lead_to_test_drive.spec.ts` in M25.2.
- **§5.h** — Close-out: evidence-sized Option B
  fold. Coordinated push once at close.

## Streak

- **Planning-time as-recommended streak → 1** at
  M25.0 close. Two mid-planning refinements
  (framing redirect + JSONField-over-CharField
  selection + modal-only selection) are recorded as
  refinements of the recommendation, not
  corrections — the recommendation process
  presented options and the user selected among
  them. Streak counts increments where the final
  lock matches what was recommended after
  presenting alternatives.
- **Zero-drift permission-class streak** — intended
  to extend from 24 to 25 across M25. M25.1 uses
  existing M4 permission class on the M11.2
  endpoint; M25.2 adds no new endpoints.
- **Historical planning-time streak of 89**
  (M10 → M23) preserved for the record; the
  current counter starts fresh at M25.0.

## What's next: SESSION_186 M25.1 attribution display + JSONField backend

Per `MILESTONE_25_PLANNING.md` §7 sequencing. In order:

1. Add `CustomerLead.source_metadata` field
   (`JSONField(blank=True, default=dict)`) +
   migration + `get_source_platform() -> str`
   accessor.
2. Extend `CustomerLeadSerializer` with
   `referrer` (PrimaryKeyRelatedField),
   `referrer_name` (SerializerMethodField reading
   `self.referrer.name`), and `source_metadata`
   (exposed as-is).
3. Update
   `services.leads.channel_intake.record_webhook_lead`
   to write `source_metadata={"platform": platform}`
   at persistence time.
4. Extend M11.1 webhook tests to assert
   `source_metadata` persistence + M6.5 lead-
   detail tests to assert new serialized fields
   present.
5. Add "Source" section to
   `frontend/src/components/LeadDetailModal.tsx`
   rendering per §5.c channel-specific rules +
   Vitest coverage in `LeadDetailModal.test.tsx`
   (new file, matches existing test patterns).
6. Extend `acceptance/journeys/` M24.3 referral
   journey with modal attribution assertion +
   extend or add small companion for M24.4
   webhook platform display.
7. Run full backend + frontend + acceptance
   baselines clean. Handoff.

## What lands at M25.2 (SESSION_187, possibly _188) — test-drive UI

1. At open: verify which endpoint returns tenant
   vehicle inventory for the picker. Likely
   candidate: existing `salesApi.ts` wrapper or a
   sibling in `frontend/src/lib/`.
2. Create
   `frontend/src/components/sales/RecordTestDriveForm.tsx`
   matching the M24.1
   `<LeadIntakeForm>` substrate pattern.
3. Attach as collapsible "Schedule test drive"
   section inside `LeadDetailModal`.
4. Vitest coverage in
   `RecordTestDriveForm.test.tsx` matching the
   `LeadIntakeForm.test.tsx` shape.
5. New
   `acceptance/journeys/sales/lead_to_test_drive.spec.ts`
   journey: create walk-in lead → post-create
   modal opens → assign salesperson via
   dropdown → expand "Schedule test drive" →
   pick vehicle → submit → assert collapsible
   closes with success indicator → close modal
   → navigate to `DealerAiSalesTestDrives` →
   assert row appears with correct associations
   (lead, vehicle, salesperson, dealership,
   date).
6. Run baselines. Handoff.
7. If evidence-sized close-out posture holds
   (M25.1 + M25.2 clean, no operator-surface
   fixes required): fold M25.3 into this session
   (retrospective + audit rerun + coordinated
   push).

## What lands at M25.3 (SESSION_188 or _189, or folded into M25.2) — close-out

- Draft `MILESTONE_25_RETROSPECTIVE.md` with §8
  corrections captured honestly + §9 evidence for
  M26 candidate ranking.
- Regenerate the audit artifact — expect webhook
  endpoint to flip `wrapper-only → covered` post-
  M25.1 attribution + no change to test-drive
  endpoints (test-drive create was already
  wrapper-only + M25.2 UI consumes it, so
  test-drive create should also flip to
  `covered`).
- Update `IMPLEMENTATION_ROADMAP.md` M25 shipped
  section.
- Update `CAPABILITY_MATRIX.md` §7z (or continue
  §7y depending on convention at close).
- Update `00-START-NEXT-SESSION.md` with M26.0
  priority.
- Coordinated push of all M25 commits to
  `origin/main`.

## Non-goals for the remaining M25 increments

- ❌ Do NOT add a secondary "+ Record test drive"
  entry point anywhere. Modal-only is locked per
  §5.d.
- ❌ Do NOT make attribution lines clickable /
  navigable. Display-only per §5.c.
- ❌ Do NOT introduce named-platform adapters
  (Autotrader / Cars.com / etc.). Generic
  adapter unchanged; `source_metadata` is the
  extension substrate but M25 does not populate
  new adapters.
- ❌ Do NOT add analytics / rollup surfaces.
  JSONField query support enables them later.
- ❌ Do NOT modify M1–M24 shipped surface except
  for the explicit §5.b additive changes.
- ❌ Do NOT expand the vehicle picker beyond
  "Suggested + all inventory."
- ❌ Do NOT push per-increment. Coordinated push
  at close.
- ❌ Do NOT let "one workflow" broaden into
  adjacent sales surfaces.
- ❌ Do NOT skip the M25.1-open verification of
  the vehicle-list endpoint used by the M25.2
  picker (M24.1-open durable lesson: verify
  both intake AND downstream surfaces before
  locking implementation).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_25_PLANNING.md` (this
   session's expanded active memo — governing
   contract for M25.1 through M25 close)
6. `docs/roadmap/MILESTONE_24_RETROSPECTIVE.md`
   §9 (M25 candidate evidence + standing
   question that seeded M25.0)
7. `docs/roadmap/MILESTONE_24_PLANNING.md` §3
   (M24.1-open deferrals 12, 13, 14 — the
   direct M25 re-entry record)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (post-M24 regenerated at this session; 113
   covered / 40 backend-only)
9. `docs/CAPABILITY_MATRIX.md` §7y
10. `docs/research/SALES_DEPARTMENT_MAPPING.md`
    §workflow step 6 + §lead acquisition
