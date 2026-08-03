---
state: active
date: 2026-08-03
last_session_shipped: SESSION_185
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: shipped
milestone_11_status: shipped
milestone_12_status: shipped
milestone_13_status: shipped
milestone_14_status: shipped
milestone_15_status: shipped
milestone_16_status: shipped
milestone_17_status: shipped
milestone_18_status: shipped
milestone_19_status: shipped
milestone_20_status: shipped
milestone_21_status: shipped
milestone_22_status: shipped
milestone_23_status: shipped
milestone_24_status: shipped
milestone_25_status: in-progress
milestone_25_open_increment: 0
milestone_25_open_increment_shipped: true
next_session: SESSION_186
next_milestone: 25
next_milestone_name: "Lead-to-Test-Drive Operational Completion"
next_increment: 1
next_increment_name: "M25.1 — Attribution display + JSONField backend addition"
---

# Next session — SESSION_186 · Milestone 25 · Increment 1 (M25.1 — attribution display + JSONField backend addition)

> **Milestone 25 planning shipped at SESSION_185.** All eight §5
> load-bearing decisions locked; two mid-planning refinements
> captured honestly. Full active memo at
> `docs/roadmap/MILESTONE_25_PLANNING.md`. Handoff at
> `docs/handoffs/SESSION_185_m25_inc0_planning.md`.
>
> **§5.a locked:** A3 (lead-source attribution display) + A4
> (test-drive creation UI) bundled under **"Lead-to-Test-Drive
> Operational Completion."** Anchor business question: *Can a
> salesperson receive a lead, understand exactly where it came
> from, assign it, and schedule the customer's test drive
> entirely through the normal product workflow?*
>
> **§5.b locked as Option A · JSONField variant.** Empirical
> discovery at M25.0 open: `platform` is not persisted on
> `CustomerLead` (webhook adapter dispatches then discards).
> M25.1 adds `CustomerLead.source_metadata = JSONField(blank=
> True, default=dict)` + typed accessor + adapter wiring.
> Chosen over CharField for durability — future attribution
> attributes (ad_source, campaign_id, listing_url, platform_
> lead_id) land as additive JSON keys without further
> migrations. Matches codebase precedent (`ChatSession.
> extracted_profile`, `TestDrive.objections_captured`).
>
> **§5.d locked as modal-only.** New durable design principle
> from M25.0: *one operational workflow beats two partially-
> overlapping ones.* Secondary "+ Record test drive" launch
> point on `DealerAiSalesTestDrives` deferred to M26+ pending
> operator evidence.
>
> **Planning-time streak → 1** at M25.0 close (fresh counter,
> reset at M24.0). Zero-drift permission-class streak enters
> M25 at 24; intended to extend to 25 across M25 (M25.1 uses
> existing M4 permission class; M25.2 adds no new endpoints).
>
> Baselines at SESSION_186 open: **4,780 backend pass, 209
> frontend pass, 13 acceptance journeys.** M25.1 grows all
> three baselines additively.

## First thing SESSION_186 must do

### 1. Verify starting state

- `git status` — clean (or single working commit for the
  M25.0 planning commit if the M25.0 commit lands at
  SESSION_186 open rather than SESSION_185 close).
- `git log --oneline -8` — top should be the M25.0
  planning commit.
- `python3 manage.py test dealer_ai` → **4,780 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **209 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run`
  → "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. Add `CustomerLead.source_metadata` field + migration + accessor

- `backend/dealer_ai/models.py` — append to `CustomerLead`:

  ```python
  source_metadata = models.JSONField(blank=True, default=dict)

  def get_source_platform(self) -> str:
      return (self.source_metadata or {}).get("platform", "")
  ```

- `python3 manage.py makemigrations dealer_ai` — expect a
  single `AddField` migration (`0049_customerlead_source_metadata`
  or next available number).
- `python3 manage.py migrate` — apply.
- No backfill migration required (`default=dict` handles
  historical rows on first read).

### 3. Extend `CustomerLeadSerializer`

Additive extension in `backend/dealer_ai/serializers.py`
(lines 221-254):

- Add `referrer` as `PrimaryKeyRelatedField(read_only=True)`
  (or nested — verify shape that renders cleanly in JSON).
- Add `referrer_name = serializers.SerializerMethodField()`
  with `get_referrer_name(obj) -> str: return obj.referrer.
  name if obj.referrer else ""`.
- Add `source_metadata` to `fields` list (exposed as-is;
  JSONField serializes to dict).

### 4. Wire adapter → `source_metadata` in `record_webhook_lead`

`backend/dealer_ai/services/leads/channel_intake.py:
record_webhook_lead` — pass `source_metadata={"platform":
platform}` through `_create_lead`. Extend `_create_lead`
to accept `source_metadata: dict = None` (defaulting to
`{}`) and write it to `CustomerLead.objects.create(...,
source_metadata=source_metadata or {}, ...)`.

### 5. Extend tests

- **Backend:** M11.1 webhook tests
  (`test_m111_*_webhook*.py`) — assert
  `lead.source_metadata["platform"] == "generic"` (or
  whichever platform the test uses) after creation. Add
  assertion for `lead.get_source_platform()` accessor.
- **Backend:** M6.5 lead-detail tests (or wherever
  `admin_lead_detail` response shape is asserted) — assert
  the new serialized fields (`referrer`, `referrer_name`,
  `source_metadata`) present in the response.
- **Backend:** New unit test for
  `CustomerLeadSerializer` if not already covered.
- Expected new backend baseline: ~4,785-4,790 pass.

### 6. Add "Source" section to `LeadDetailModal`

`frontend/src/components/LeadDetailModal.tsx` — render a
"Source" attribution section near the existing lead-id
header per §5.c rules:

- `chat` / `walk_in` / `phone` / `other` → omit
  Source section.
- `listing_form` → "Source: {display_case(source_
  metadata.platform)}" or "Listing form" fallback.
- `referral` → "Referred by: {referrer_name}" or
  "Referral (referrer not linked)" fallback.

Reads via `detail.lead.referrer_name` +
`detail.lead.source_metadata?.platform`. TypeScript
update needed in `frontend/src/lib/api.ts`
`LeadDetailResponse.lead` interface:

- Add `channel: string`
- Add `referrer: number | null`
- Add `referrer_name: string`
- Add `source_metadata: Record<string, unknown>`

### 7. Vitest coverage

`frontend/src/components/LeadDetailModal.test.tsx` —
new file (or extend existing). Assert Source section
renders correctly for each channel value + fallback
behavior. Expected new frontend baseline: ~215-220
pass.

### 8. Extend acceptance journeys

- **M24.3 referral journey**
  (`acceptance/journeys/sales/referral_lead.spec.ts` or
  equivalent filename — verify at M25.1 open) — after
  creating referral lead + opening modal, assert
  "Referred by: {name}" is visible.
- **M24.4 webhook journey**
  (`acceptance/journeys/sales/webhook_lead.spec.ts` or
  equivalent) — after webhook POST + operator opens
  the resulting lead, assert "Source: {platform_label}"
  is visible. If this requires a fresh operator-flow
  extension beyond M24.4's integration-only assertion,
  add a small companion assertion in the same file.
- Expected acceptance baseline stays at 13 journeys
  (assertions extend within existing journeys).

### 9. Run full baselines clean

- `python3 manage.py test dealer_ai` → all pass.
- `cd frontend && npm test` → all pass.
- `cd acceptance && npm test` (or equivalent Playwright
  invocation) → all 13 journeys pass on clean DB.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run`
  → clean.
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.

### 10. Ship the M25.1 handoff

- `docs/handoffs/SESSION_186_m25_inc1_attribution.md`.
- **Do NOT push** — coordinated push at M25 close per
  §5.h.

## Non-goals for SESSION_186

- ❌ Do NOT ship `<RecordTestDriveForm>` or any
  test-drive UI. That's M25.2.
- ❌ Do NOT add a secondary launch point on
  `DealerAiSalesTestDrives` — modal-only per §5.d.
- ❌ Do NOT make attribution lines clickable /
  navigable. Display-only per §5.c.
- ❌ Do NOT introduce named-platform adapters
  (Autotrader / Cars.com / etc.). Generic adapter
  unchanged.
- ❌ Do NOT modify existing M1–M24 endpoints or
  serializers beyond the additive
  `CustomerLeadSerializer` extension.
- ❌ Do NOT push — coordinated push at close.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT skip the DoD compliance check —
  attribution assertions must extend both M24.3 and
  M24.4 journeys.

## Baseline expected at M25.1 close

- Backend: ~4,785-4,790 pass (added webhook
  metadata + serializer field tests).
- Frontend: ~215-220 pass (added
  LeadDetailModal Source section coverage).
- Acceptance: 13 journeys (assertions extend
  within M24.3 + M24.4).
- Migrations: 0049 (or next available).

## NEXT TASK

Start SESSION_186 with (a) starting-state
verification, (b) commit the M25.0 planning
artifacts if not already committed at SESSION_185
close, (c) add `CustomerLead.source_metadata`
field + migration + accessor, (d) extend
`CustomerLeadSerializer` additively, (e) wire
`record_webhook_lead` adapter to persist
platform into `source_metadata`, (f) extend
backend tests, (g) add Source section to
`LeadDetailModal` + Vitest coverage, (h) extend
M24.3 referral + M24.4 webhook Playwright
assertions, (i) run full baselines clean, (j)
ship the M25.1 handoff. **No push.**

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_25_PLANNING.md` (M25.0
   active memo, governing contract through M25
   close)
6. `docs/roadmap/MILESTONE_24_RETROSPECTIVE.md` §9
7. `docs/roadmap/MILESTONE_24_PLANNING.md` §3
   (M24.1-open deferrals 12, 13, 14)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
9. `docs/CAPABILITY_MATRIX.md` §7y
10. `docs/research/SALES_DEPARTMENT_MAPPING.md`
    §workflow step 6 + §lead acquisition
11. `docs/handoffs/SESSION_185_m25_inc0_planning.md`
    (M25.0 shipped)

Narrative docs are claims. Rules + research +
code are facts.

---

## Operational state (post-SESSION_185 — M25.0 planning shipped)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0048`. Test baseline:
  **4,780 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 209 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright
  1.49 + TS 5.6 operational; **13 journeys**
  passing end-to-end on clean DB.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. First
  real M24 CI run passed in 2m33s at
  SESSION_185 open verification.
- **Async runtime:** Celery 5.5.3 + Redis
  6.4.0 + `django-celery-beat` 2.8.1
  DatabaseScheduler. 10 scheduled task
  families registered.
- **Milestones shipped:** M1 → M24. M25
  planning locked (M25.0 shipped at
  SESSION_185); M25.1 opens next session.
- **DRF admin surface:** 113 endpoints.
- **Frontend operator routes:** 20.
- **Public endpoints:** +1 M6.5 showroom.
- **Service surface:** all M1–M24 packages
  unchanged. M25.1 will add zero verbs and
  extend the webhook intake verb with one
  kwarg.
- **Frontend surfaces:** unchanged from M24
  close. M25.1 will extend `LeadDetailModal`
  with a Source section; M25.2 will add
  `<RecordTestDriveForm>` in
  `frontend/src/components/sales/`.
- **Tenancy carriers:** 52.
- **Permission classes:** 7 actual —
  zero-drift streak twenty-four consecutive
  milestones (M10 → M24). Intended posture:
  extend to 25 across M25.
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages
  (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 24 status:** SHIPPED (CI-
  verified at SESSION_185 open — first real
  M24 acceptance run green in 2m33s).
- **Milestone 25 status:** in-progress.
  M25.0 planning shipped at SESSION_185;
  M25.1 opens at SESSION_186.
- **Audit tooling:** post-M24 = 113 covered
  / 40 backend-only. Regenerated at
  SESSION_185; uncommitted diff (walk-in /
  phone / referral flipped covered) lands
  with the M25.0 planning commit.
- **Planning-time streak: 1** (at M25.0
  close). Historical run of 89 across M10
  → M23 preserved for the record.
- **DoD amendment (M21.0 §5.f Option B):**
  every future customer-facing milestone
  must add or update at least one
  Playwright operational journey. M25
  compliance path: M25.1 extends M24.3 +
  M24.4 assertions; M25.2 adds
  `sales/lead_to_test_drive.spec.ts`.
- **Durable lessons from M25.0:** (a) one
  operational workflow beats two partially-
  overlapping ones — for customer-facing
  features, default to one canonical entry
  point; defer secondary launch points
  until operator evidence demands them; (b)
  M25.0 empirical verification surfaced
  that `platform` was not persisted despite
  the M24.1-open scope note implying a
  "small UI extension" — verification at
  planning open catches these gaps before
  scope commits. Continues the M24.1-open
  durable lesson.
