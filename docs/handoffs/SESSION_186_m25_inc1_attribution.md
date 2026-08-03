---
title: "SESSION_186 handoff — Milestone 25 · Increment 1 (M25.1 — attribution display + JSONField backend addition)"
status: historical
type: handoff
date: 2026-08-03
session: 186
milestone: 25
milestone_status: in-progress
milestone_name: "Lead-to-Test-Drive Operational Completion"
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_186 — Milestone 25 · Increment 1 (M25.1 — attribution display + JSONField backend addition)

## What shipped

M25.1 closes M24.1-open §3 deferrals **13** (referrer display in
modal) and **14** (platform display for webhook-origin leads).
Both attribution surfaces now render as a "Source" section in
`LeadDetailModal` per the M25 governing contract
(`MILESTONE_25_PLANNING.md` §5.b + §5.c). One additive backend
field + one additive serializer extension + one adapter wiring
change + one modal section + Vitest coverage + Playwright
assertion extensions on the M24.3 referral and M24.4 webhook
journeys. No new endpoints, no new Playwright journeys — the
attribution surface is a display gap, not a workflow gap.

**Backend additions (all additive, no touched behavior):**

- `CustomerLead.source_metadata` — new `JSONField(blank=True,
  default=dict)`. Migration `0049_customerlead_source_metadata`
  (single `AddField`, no backfill required — default handles
  historical rows). Typed accessor
  `CustomerLead.get_source_platform() -> str` on the model
  centralizes the key lookup so read sites stay decoupled from
  the JSON shape.
- `CustomerLeadSerializer` gains `channel`, `referrer`,
  `referrer_name` (SerializerMethodField), and `source_metadata`
  in the exposed fields list. Matches the M11.6
  `AdminLeadListSerializer` additive precedent. Extended
  `read_only_fields` list correspondingly.
- `services.leads.channel_intake._create_lead` gains
  `source_metadata: Optional[dict] = None` kwarg + writes to the
  model at create time.
- `services.leads.channel_intake.record_webhook_lead` now passes
  `source_metadata={"platform": platform}` alongside the
  adapter-normalized kwargs. Before M25.1 the `platform` string
  was used only to dispatch the adapter and discarded; now it is
  persisted so the operator UI can render a platform-specific
  label.

**Frontend additions:**

- `LeadDetailResponse.lead` TS interface extended with `channel`,
  `referrer`, `referrer_name`, `source_metadata` matching the
  M25.1 serializer surface.
- `LeadDetailModal` gains a "Source" section rendered at the top
  of the left column when `channel === "referral"` or
  `channel === "listing_form"`. Chat / walk_in / phone / other
  channels omit the section entirely (no attribution to display).
- Two exported pure helpers on `LeadDetailModal.tsx`:
  `displayPlatform(raw: unknown) -> string` (title-cases
  hyphen/underscore/space-separated platform identifiers) and
  `computeSourceLine(lead) -> string | null` (implements the
  §5.c channel-specific decision table). Exported so the Vitest
  suite can unit-test the pure logic without mounting the modal.
- New `data-testid="lead-source-section"` +
  `data-testid="lead-source-line"` for Playwright targeting.

**Test additions:**

- **Backend +2 tests** in
  `tests/test_handoff_and_reset.py::AdminLeadDetailEndpointTests`
  — `test_exposes_channel_referrer_and_source_metadata` (referral
  lead assertion for all four new fields) +
  `test_exposes_source_metadata_for_webhook_lead` (listing_form
  lead with platform metadata + null-referrer assertion).
- **Backend +1 assertion** in
  `tests/test_m111_channel_intake_service.py::test_webhook_generic_platform_normalizes_and_lands`
  asserting `source_metadata == {"platform": "generic"}` +
  `get_source_platform() == "generic"`.
- **Backend +1 assertion** in
  `tests/test_m111_channel_intake_endpoint.py::test_webhook_happy_path_with_generic_platform`
  fetching the created lead and asserting persisted metadata.
- **Frontend +10 tests** in new file
  `frontend/src/components/LeadDetailModal.test.tsx` — 3 for
  `displayPlatform`, 7 for `computeSourceLine` (chat / walk_in /
  phone / other → null; referral with + without linked
  referrer; listing_form with + without platform; multi-word
  platform title-casing).
- **Acceptance +2 assertions** extending existing journeys:
  M24.3 referral journey asserts "Referred by: Priya Prior-
  Customer" in the modal Source line; M24.4 webhook journey
  asserts "Source: Generic" for the ingested lead. No new
  journey files — journey count stays at 13.

## Starting-state verification (this session)

- `git status` — clean; `dd21d6c` + M25.0 planning commits ahead
  of `origin/main` by 2.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` — "No
  changes detected" at open.
- Frontend + acceptance `tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- Backend baseline from SESSION_185: 4,780 pass, 1 skipped, 0
  fail. Frontend: 209 pass. Acceptance: 13 journeys.

## Baselines at M25.1 close

- **Backend: 4,782 pass**, 1 skipped, 0 fail (+2 from M25.1;
  new admin_lead_detail attribution tests).
- **Frontend: 219 pass** across 31 test files (+10 from M25.1;
  new `LeadDetailModal.test.tsx`).
- **Acceptance: 13 journeys**, 19 tests total including setup
  (6 setup + 13 journeys). Full clean-DB run: **19 passed
  (~27.3s)**. Referral journey extends by ~0.2s for the new
  Source-line assertion; webhook journey extends by ~0.2s
  similarly.
- **Migrations:** `0049_customerlead_source_metadata` (single
  `AddField`).
- **`python3 manage.py check`** clean.
- **`python3 manage.py makemigrations --check --dry-run`** —
  "No changes detected."
- **Frontend + acceptance `tsc --noEmit`** clean.

## Design decisions applied at M25.1

- **JSONField default = dict** — no backfill migration required;
  historical rows read as `{}` on first serialization / accessor
  call.
- **Typed accessor centralizes JSON reads.** Read sites use
  `lead.get_source_platform()`; write sites use the adapter
  contract (`source_metadata={"platform": platform}`).
  Junk-drawer risk mitigated per M25.0 §5.b framing.
- **Pure helpers exported for Vitest.** `displayPlatform` and
  `computeSourceLine` are pure functions — the Vitest suite
  exercises the channel × attribution decision table directly
  without mocking the modal's fetch orchestration. The full
  modal integration is covered by the extended M24.3 + M24.4
  Playwright journeys, which are already the operational
  contract per the durable "Playwright as operational contract"
  principle.
- **`data-testid` selectors, not text-content selectors.** The
  Playwright assertions target `lead-source-section` +
  `lead-source-line` for stability — the display strings can
  evolve without breaking the journey.
- **No display-string i18n / localization.** The M25.1 display
  strings are literal English per the shipped UI's monolingual
  posture; no i18n substrate exists yet in the codebase.

## Streak

- **Planning-time as-recommended streak → 2** at M25.1 close.
  M25.1 implementation matched the M25 planning memo §5.b + §5.c
  locks exactly, including the JSONField shape, the typed
  accessor, the additive serializer + adapter posture, and the
  channel-specific display rules.
- **Zero-drift permission-class streak → 25.** M25.1 uses the
  existing M4 `IsSalesManagerOrOwnerAtActiveDealership`
  permission class on the M11.2 endpoint (unchanged; test-drive
  UI comes in M25.2). Twenty-five consecutive milestones (M10 →
  M25) with no new permission classes.

## What's next: SESSION_187 M25.2 test-drive UI

Per `MILESTONE_25_PLANNING.md` §7 sequencing + §5.d modal-only
lock. In order:

1. **Verify at open** — which endpoint returns tenant vehicle
   inventory for the picker. Likely candidate: existing
   `salesApi.ts` wrapper or a sibling in `frontend/src/lib/`.
   If no suitable wrapper exists, add a small additive one
   (still zero backend changes — reads through an existing
   endpoint).
2. **Create `<RecordTestDriveForm>` component** in
   `frontend/src/components/sales/` matching the M24.1
   `<LeadIntakeForm>` substrate pattern. Fields: vehicle
   picker (suggested vehicles from
   `detail.interested_vehicles` + full tenant inventory
   fallback per §5.e), optional `duration_minutes`,
   optional `route_notes`, optional `customer_reaction`,
   optional `objections_captured` (comma-separated
   free-text), optional `next_action`. `driven_at`
   defaults server-side to `timezone.now()` — no form
   input for now.
3. **Attach as collapsible "Schedule test drive" section**
   inside `LeadDetailModal` — collapsed by default,
   expands on operator click. On successful submit
   collapses with success indicator + optionally
   refreshes cached detail. Modal-only per §5.d; no
   secondary launch point on
   `DealerAiSalesTestDrives`.
4. **Vitest coverage** in
   `RecordTestDriveForm.test.tsx` matching the
   `LeadIntakeForm.test.tsx` shape (submit → onSubmit
   invocation, validation, error surfaces).
5. **New Playwright journey**
   `acceptance/journeys/sales_manager/lead_to_test_drive.spec.ts`:
   create walk-in lead via existing M24.1 substrate →
   post-create modal opens → assign salesperson via
   dropdown → expand "Schedule test drive" → pick
   vehicle from picker → submit → assert collapsible
   closes with success indicator → close modal →
   navigate to `DealerAiSalesTestDrives` → assert row
   appears with correct associations (lead / vehicle /
   salesperson / dealership / date).
6. **Run baselines** — expect 4,782 backend (no new
   backend tests unless the wrapper additions land),
   ~225 frontend, **14 acceptance journeys**.
7. **Ship the M25.2 handoff.**
8. **If evidence-sized close-out posture holds** (clean
   baselines, no operator-surface fixes required):
   fold M25.3 close-out into this session (retrospective
   + audit rerun + coordinated push).

## What lands at M25.3 (SESSION_188 or folded into M25.2) — close-out

- Draft `MILESTONE_25_RETROSPECTIVE.md` with §8 (any
  corrections captured honestly) + §9 evidence for M26
  candidate ranking.
- Regenerate the audit artifact — expect the webhook
  endpoint to remain wrapper-only (M25.1 did not add a
  UI consumer for the webhook endpoint itself — the
  webhook stays integration-driven per M24.4 design)
  and the test-drive create endpoint to flip
  wrapper-only → covered post-M25.2.
- Update `IMPLEMENTATION_ROADMAP.md` M25 shipped
  section.
- Update `CAPABILITY_MATRIX.md` §7z (or continue §7y
  depending on convention at close).
- Update `00-START-NEXT-SESSION.md` with M26.0
  priority.
- Coordinated push of all M25 commits to
  `origin/main`.

## Non-goals for the remaining M25 increments

- ❌ Do NOT add a secondary "+ Record test drive"
  entry point anywhere. Modal-only is locked per §5.d.
- ❌ Do NOT make attribution lines clickable /
  navigable. Display-only per §5.c.
- ❌ Do NOT introduce named-platform adapters
  (Autotrader / Cars.com / etc.). Generic adapter
  unchanged; `source_metadata` is the extension
  substrate but M25 does not populate new adapters.
- ❌ Do NOT add analytics / rollup surfaces. JSONField
  query support enables them later.
- ❌ Do NOT modify M1–M24 shipped surface except for
  the additive M25.1 changes now shipped + the M25.2
  scope.
- ❌ Do NOT expand the vehicle picker beyond
  "Suggested + all inventory."
- ❌ Do NOT push per-increment. Coordinated push at
  M25 close.
- ❌ Do NOT let "one workflow" broaden into adjacent
  sales surfaces.
- ❌ Do NOT skip the M25.2-open verification of the
  vehicle-list endpoint used by the M25.2 picker
  (M24.1-open durable lesson).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_25_PLANNING.md` §5 (M25
   governing contract — §5.b + §5.c locks satisfied
   by this increment; §5.d + §5.e + §5.g land in
   M25.2)
6. `docs/roadmap/MILESTONE_24_PLANNING.md` §3
   (deferrals 12, 13, 14 — 13 + 14 closed by this
   increment; 12 remains for M25.2)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (webhook endpoint remains wrapper-only per M24.4
   no-operator-UI design; test-drive create flips
   post-M25.2)
8. `docs/CAPABILITY_MATRIX.md` §7y
9. `docs/research/SALES_DEPARTMENT_MAPPING.md`
   §lead acquisition (attribution) + §workflow step
   6 (demonstration)
10. `docs/handoffs/SESSION_185_m25_inc0_planning.md`
    (M25.0 governing planning)
