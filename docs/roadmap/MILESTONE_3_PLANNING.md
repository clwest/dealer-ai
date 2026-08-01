---
title: "Milestone 3 — Implementation-Planning Pass"
status: draft
type: planning-artifact
generated: 2026-07-31
generated_at_session: SESSION_055 (pre-implementation)
milestone: 3
milestone_name: "Structured condition report"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_2_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_2_PLANNING.md
  - docs/roadmap/MILESTONE_1_PLANNING.md
  - docs/BUSINESS_DOMAIN_MAP.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/RECON_MAPPING.md
  - docs/research/VEHICLE_CENTRIC_PIVOT.md
  - docs/research/INDEPENDENT_DEALER_PIVOT.md
supersedes: none
applies_to:
  - SESSION_056+ Milestone 3 implementation sessions
  - Any subsequent session that resumes Milestone 3
---

# Milestone 3 — Implementation-Planning Pass

> **What this is.** The planning artifact produced before Milestone 3
> implementation begins. Mirrors the shape that
> `MILESTONE_2_PLANNING.md` proved out over eight increments:
> engineering practices to preserve (§0), design memo (§1), migration
> impact review (§2), compatibility checklist (§3), reusable-primitive
> review (§4), scope discipline + deferrals (§5), anchors (§6),
> increment sequencing (§7).
>
> **Why this exists.** Milestone 3 introduces the second sensitive
> operational data surface the platform has ever held — the per-vehicle
> structured Condition Report. Unlike the M2 ledger (numbers), M3 holds
> **inspection judgments** authored by a named human that will drive
> every downstream recon decision. The blast radius of getting the
> data shape wrong is high: every future milestone (M4 Recon
> Automation, M5 Lifecycle Stages, M8 Operational Intelligence)
> reads off ConditionReport / ConditionFinding rows, and the
> retrospective §6 lesson 11 named this trap — "*Frontend manual /
> browser verification must not be marked complete when tooling cannot
> perform it*." M3 also introduces the platform's first genuine file
> storage need (photo attachments per finding) — the first surface
> where "where does binary content live" is a decision the kit has
> to make. Confirming the plan and the compatibility invariants
> before touching code is the difference between a clean milestone
> and one that half-lands a storage story and half-lands a data
> model.
>
> **Precedence.** The six rules of `docs/PROJECT_RULES.md` override
> anything in this doc. The scope boundary of
> `IMPLEMENTATION_ROADMAP.md` §Milestone 3 overrides anything in
> this doc. The layer discipline in `AUTHENTICATION_MODEL.md` §1
> overrides anything in this doc. The eleven lessons in
> `MILESTONE_2_RETROSPECTIVE.md` §6 constrain every increment in
> §7.
>
> **How to use it.** Read all sections before writing code. Use the
> compatibility checklist (§3) as the acceptance test — Milestone 3
> is not complete until every checklist item verifies true, with
> evidence recorded inline the way Milestone 2's §3 was annotated
> at close. The multi-photo storage decision in §5 is
> load-bearing: implementation cannot begin until that decision is
> settled and captured here.

---

## 0. Engineering practices to preserve from Milestone 2

Not philosophy — the engineering process Milestone 3 inherits from
the Milestone 2 retrospective (`MILESTONE_2_RETROSPECTIVE.md` §6).
Every increment session should be able to point at these and say
"we did this."

1. **Persistence, service, read model, math, workflow, safety, API,
   and UI are safer as separate increments.** M2's M2.1→M2.7
   sequence made every layer independently reviewable and testable.
   M3 mirrors the shape — models, service, read-model extension,
   storage story, API, UI, and closeout each land in their own
   session. No session ever bundles two increments to "save time."
2. **Deferred work must be redistributed into small increments,
   not accumulated.** If an M3 session narrows scope, the deferred
   work is re-planned into a new small session — never absorbed
   into the following session's scope. The M2 SESSION_047
   course-correction is the model.
3. **Actual vs. estimated semantic contracts inherited.** M2 locked
   `total_investment` (excludes estimates) vs. `estimated_cost_total`
   vs. `projected_total_investment` (sums both). M3
   `ConditionFinding.estimated_cost` will eventually flow into M4-
   authored `VehicleCost` rows with `is_estimate=True` — but not in
   M3 itself. M3 owns the finding-level estimate; it does NOT post
   cost rows. The contract survives untouched.
4. **Immutable rows plus reversing / status transitions preserve
   history.** M2's `VehicleCost` rows are immutable; corrections
   happen by reversing rows. M3's `ConditionReport` uses a
   status-driven equivalent — the report has an explicit `status`
   (`draft` | `complete`); once `complete` it becomes an
   immutable record. Corrections happen by authoring a **new**
   report against the same vehicle (which becomes the new
   `latest`), not by editing the old one. Findings within a `draft`
   report are freely editable; findings within a `complete` report
   are frozen with the report.
5. **Focused positive/negative test matrices over integration
   tests.** M2 shipped 287 focused tests across seven increments.
   Continue. Each M3 increment ships its own focused test file with
   both positive and negative coverage.
6. **Money-as-strings if any cost data ever crosses the API
   boundary.** M2 serialized every money field as a fixed
   two-decimal-place string. `ConditionFinding.estimated_cost` is a
   `Decimal` field; if it ever appears in a JSON response, it MUST
   use the same `_money_str` helper (or a shared successor per M2
   retrospective §7 deferral).
7. **Frontend manual verification must not be marked complete when
   tooling cannot perform it.** M2.7's honest "manual browser smoke
   deferred to operator verification" note is the model. M3's UI
   increment will make the same honest call; the shipping session
   annotates §3 exactly the same way if the environment cannot
   drive an interactive browser.
8. **Migration-check DB alias stays wired.**
   `DATABASES["migration_check"]` (introduced M2.1) protects
   destructive `migrate zero → migrate` verification runs. M3
   introduces three-to-four new migrations; the alias remains the
   safe target for verification.
9. **Extend existing primitives; do not build parallel
   implementations.** M3 extends `Vehicle` (new related tables),
   `services/tenancy.py` (register two new tenant carriers with
   the `pre_save` autofill signal), `dealer_ai/permissions.py`
   (reuse `IsSalesManagerOrOwnerAtActiveDealership` unchanged;
   no new class in M3). Zero parallel implementations.
10. **Clear layer separation.** Identity, tenant scope, business
    permissions, and data scoping remain separate concerns. Every
    ConditionReport write path threads
    `dealership=get_current_dealership(request)` explicitly at the
    view layer. `.filter(dealership=...)` stays visible in views.
    The `pre_save` autofill remains a fallback, never a primary
    write path.
11. **Documentation discipline.** Handoffs are immutable. Session
    ends produce `docs/handoffs/SESSION_NNN_<slug>.md`.
    `00-START-NEXT-SESSION.md` is overwritten. This planning
    document gets annotated in-place at milestone close with the
    shipped evidence — mirroring M2's §3 annotation pattern.

Rule of thumb for every M3 session: if an increment can't be
described in one sentence that names the shipped surface and the
locked invariant, it is too large.

---

## 1. Design Memo

Every entry answers **the same three questions** in this order:
what operational question does this subsystem answer? which existing
primitive does it extend? what does it leave untouched?

**Start with the questions, not the models.** The condition report
exists because the recon manager standing at the vehicle next
Tuesday needs to answer "*what has to happen before I can call this
front-line ready?*" — and the tech who does the work three days
later needs to answer "*what did the inspector actually find?*" —
and the sales manager six weeks after delivery needs to answer
"*what did we know about this vehicle before the customer took it
home?*" (warranty defense). The data model exists to support those
three answers. If a proposed field or endpoint does not sharpen one
of the questions below, it does not belong in Milestone 3.

### 1.0 The operational questions Milestone 3 must answer

Six questions, each traced to the research corpus. These are the
acceptance test for whether the milestone shipped the right thing.

| # | Question | Research citation |
|---|----------|-------------------|
| 1 | **What defects, needed work, and missing items were found when we inspected this vehicle?** | `RECON_MAPPING.md` §2.1 (multi-point inspection); §2.4 (condition report document); `VEHICLE_CENTRIC_PIVOT.md` §Phase 2. |
| 2 | **How severe is each finding — advisory, recommended, required, or safety?** | `RECON_MAPPING.md` §2.2 (severity levels); §3.1 (three-tier planning framework — must/should/won't drives from severity). |
| 3 | **Who inspected the vehicle, and when?** | `RECON_MAPPING.md` §2.4 ("Inspector name and date"); §2.6 (AI is never allowed to author findings — human-authored discipline is non-negotiable); §12.2 (sign-off authority). |
| 4 | **What does each finding look like?** — photo evidence for warranty defense, vendor communication, and dispute protection. | `RECON_MAPPING.md` §2.5 (photos in condition reporting: pre-existing damage documentation, vendor communication, insurance claims, before/after evidence); §13.1 (warranty exposure — condition documentation is the legal record). |
| 5 | **What is the estimated cost to address each finding we've decided to fix?** | `RECON_MAPPING.md` §3.3 (recon estimate vs. cap); §3.1 (three-tier decision framework requires cost estimates per finding); `VEHICLE_CENTRIC_PIVOT.md` §Phase 2 (optional `cost_estimate` on `ConditionFinding`). |
| 6 | **Is the condition report finished (complete) or still being authored (draft)?** | `RECON_MAPPING.md` §12.1 (front-line-ready checklist — "condition report complete" is item 1); §12.2 (sign-off authority — the report has a formal moment of completion). |

Questions 1–4 are the core of the data shape. Question 5 is the
seam M4 (Recon Automation) reads to auto-mint `VehicleCost` rows
from completed work orders. Question 6 gates whether a
`ConditionReport` is a work-in-progress record or the durable
archival document.

**What Milestone 3 does NOT answer** (deliberate, per
`IMPLEMENTATION_ROADMAP.md` §Milestone 3 scope boundary):

- Q: *Which findings will we fix vs. skip?* — that's the recon
  planning decision (RECON §3.1 three-tier framework). Belongs to
  Milestone 4 when AI drafts work orders from findings.
- Q: *Which vendor should we send this finding to?* — Milestone 4.
- Q: *Is this vehicle ready for front-line retail?* — Milestone 5
  (lifecycle stages + retail gating).
- Q: *What is the actual (invoiced) cost of the work vs. estimate?*
  — Milestone 4 (`WorkOrder.actual_cost`), which auto-mints a
  `VehicleCost` on complete.

### 1.1 Condition report — `ConditionReport` (many-per-Vehicle)

- **Business question answered.** Q3 + Q6. Every finding hangs off
  a report authored by a named human at a point in time; without
  the parent report there is no provenance for the findings.
- **Citation.** `RECON_MAPPING.md` §2.4 (the condition report
  document); §2.6 (AI is never allowed to author); §12.1 + §12.2
  (front-line-ready checklist + sign-off authority);
  `VEHICLE_CENTRIC_PIVOT.md` §Phase 2.
- **Fields (planning shape — final field list decided in M3.1).**
  - `vehicle` (FK, required, on_delete=CASCADE).
  - `dealership` (FK, NOT NULL from day one — greenfield table).
  - `authored_by` (FK to `AUTH_USER_MODEL`, nullable, SET_NULL) —
    provenance for who wrote the report. Nullable + SET_NULL so
    historical rows survive user deletion (mirrors
    `VehicleCost.created_by` SET_NULL rationale from M2.1). The
    inspector's *name* survives even after account removal via
    a separate `inspector_name` CharField (see below) so the
    report remains legally defensible.
  - `inspector_name` (CharField, required) — free text captured
    at author time. Required because RECON §2.4 lists
    "Inspector name" as an explicit field on the document.
    Independent of `authored_by`: the user who *typed* the
    report may be different from the mechanic who *did* the
    inspection (a service writer transcribing a paper inspection,
    for example). Free text keeps the flexibility.
  - `inspected_at` (DateTimeField, required) — when the physical
    inspection happened, not when the row was written.
  - `mileage_at_inspection` (PositiveIntegerField, required) —
    RECON §2.4 explicit field on the document.
  - `status` (CharField with choices: `draft`, `complete`).
    Default `draft`. A `complete` report is immutable (see
    §Design note below).
  - `completed_at` (DateTimeField, nullable) — set when
    `status` transitions to `complete`; never written to a
    `draft` row.
  - `notes` (TextField, blank) — free text for "we inspected
    at Manheim before purchase; this is the arrival-inspection
    against the auction condition report."
  - Timestamps (`created_at`, `updated_at`).
- **Extend.** `Vehicle` (FK relationship target). No changes to
  Vehicle's own fields.
- **Leave untouched.** `Vehicle.is_available` (boolean; computed
  lifecycle refactor stays Milestone 5's concern). No new field
  on `Vehicle` — the "does this vehicle have a completed condition
  report?" question is answerable via a `@property` delegator to
  the M3.2 service, mirroring M2.3's read-model pattern.

**Design note — many-per-Vehicle, not OneToOne.** A vehicle can
be re-inspected. Common examples: arrival inspection reveals
minor issues; post-recon inspection verifies work; pre-front-line
inspection catches missed items; owner walkthrough finds
additional items (RECON §7.5). Each inspection is a fresh
`ConditionReport`. The `latest_condition_report` accessor on
`Vehicle` (M3.3) returns the most recent `complete` report; the
`latest_draft_condition_report` accessor returns the most recent
`draft` if the vehicle has one in progress. **This differs
intentionally from M2's OneToOne `VehicleAcquisition`** — that
was OneToOne because the *buying event* is unique per unit. The
*inspection* is a repeatable event.

**Design note — `draft` vs `complete`.** Draft reports are freely
editable (add findings, edit descriptions, delete findings, change
severity, upload photos). Complete reports are immutable. The
transition `draft → complete` is one-way; there is no `reopen`
transition in M3 v1. If an operator needs to add a missed finding
after completing, they author a **new** report. The rationale:
mirrors the M2 immutable-cost-row + reversing-entry pattern
(retrospective §6 lesson 5); once the report is the "record of
inspection," subsequent edits corrupt the historical truth of
what the inspector knew at inspection time. Explicit re-inspection
preserves the truth.

**Design note — no `reopen` in M3 v1.** Deferred; if operator
evidence surfaces friction that new-report-per-correction cannot
address, revisit. Same discipline as M2's cost-update deferral
(`retrospective §7`).

### 1.2 Condition finding — `ConditionFinding` (many-per-ConditionReport)

- **Business question answered.** Q1 + Q2 + Q5. Each row is one
  observed defect / needed work / missing item.
- **Citation.** `RECON_MAPPING.md` §2.1 (multi-point inspection
  category list); §2.2 (severity levels); §2.6 (AI must never
  invent findings); §2.7 (what AI IS allowed — summarize, group,
  cross-reference; drafting-only). `VEHICLE_CENTRIC_PIVOT.md`
  §Phase 2.
- **Fields.**
  - `report` (FK to `ConditionReport`, required, on_delete=CASCADE).
  - `dealership` (FK, NOT NULL from day one — denormalized for
    tenant-scoped read paths, same rationale as
    `VehicleAcquisition.dealership` / `VehicleCost.dealership`
    from M2.1).
  - `category` (CharField with choices — enumerated below).
  - `severity` (CharField with choices: `advisory`, `recommended`,
    `required`, `safety`).
  - `description` (TextField, required) — the human's words.
    Required; the AI is prohibited from writing findings per
    RECON §2.6.
  - `estimated_cost` (Decimal, nullable, `max_digits=10,
    decimal_places=2`) — the recon manager's estimate of what
    it will cost to address. Nullable because not every finding
    has a known cost at inspection time (some inspections don't
    include estimates per RECON §2.4); the field exists as the
    seam M4 reads when auto-drafting work orders.
  - `notes` (TextField, blank) — free text for context beyond
    the description ("customer complained of noise" or "found
    during post-recon QC").
  - Timestamps (`created_at`, `updated_at`).
- **Category enum (planning shape — final enum lives in the
  models file; add/rename as evidence warrants during M3.1).**
  Twelve categories per `IMPLEMENTATION_ROADMAP.md` §Milestone 3
  scope boundary, cross-referenced against RECON §2.1:
  - `mechanical` — engine performance, transmission, cooling,
    charging, starting, drive-line (RECON §2.1 "Mechanical").
  - `cosmetic` — paint condition, chips, scratches, faded clear
    coat, prior repaint evidence (RECON §2.1 "Cosmetic /
    paint").
  - `body` — panel fit, prior collision evidence, frame
    integrity (RECON §2.1 "Body / structural").
  - `glass` — windshield, side glass, rear glass, sunroof,
    mirrors (RECON §2.1 "Glass").
  - `tires` — tread depth, sidewall condition, age (DOT codes),
    spare (RECON §2.1 "Tires").
  - `interior` — upholstery, dashboard cracks, odors, carpet,
    controls, feature functionality (RECON §2.1 "Interior").
  - `fluids` — oil, coolant, brake fluid, power steering,
    transmission, differential (RECON §2.1 "Fluids").
  - `electrical` — battery, alternator, lighting, warning
    lights, accessories (RECON §2.1 "Electrical").
  - `safety` — brakes, brake fluid, airbag warnings, seatbelts,
    headlight aim, wipers (RECON §2.1 "Safety").
  - `accessories` — floor mats, spare tire and tools, jack,
    wheel locks and key, spare key/fob (RECON §2.1
    "Accessories / features present").
  - `missing` — expected items not present: second key, owner's
    manual, headrest, floor mats, radio anti-theft code (RECON
    §2.1 "Missing items").
  - `other` — the "we saw this but it doesn't fit any of the
    above" bucket. Explicitly enumerated because the RECON §2.1
    categories are a strong partition of *mechanical reality*
    but real inspections surface things that don't fit
    (documentation issues, prior modification, custom
    aftermarket parts).

  Twelve categories. Kept flat (no hierarchy) mirroring M2.1's
  cost-category flatness rationale.

- **Severity enum.** Four values per RECON §2.2, in escalation
  order:
  - `advisory` — noted, no action required.
  - `recommended` — should be addressed, not blocking front-line.
  - `required` — must be addressed before front-line.
  - `safety` — must be addressed before front-line, highest
    priority.

- **Extend.** New relationship on `ConditionReport`. No changes
  to `Vehicle` fields.
- **Leave untouched.** No `VehicleCost` row minted from a
  `ConditionFinding` in M3 — that's M4 (per VCP §Phase 3 and
  roadmap §Milestone 3 out-of-scope). The `estimated_cost` field
  lives on the finding as documentation only; it does NOT post
  anywhere.

**Design note — `estimated_cost` on the finding, not a linked
`VehicleCost(is_estimate=True)`.** Tempting to post an estimate
VehicleCost row (M2's `is_estimate` field is designed for exactly
this). Rejected for M3: the recon planning decision ("must-do vs.
should-do vs. won't-do" — RECON §3.1) has not been made yet at
condition-report time. Posting an `is_estimate=True` VehicleCost
row on inspection would inflate `projected_total_investment`
even for advisory findings the store will never spend on.
Milestone 4 owns the flow: findings → recon plan (must-do
subset) → work orders → estimate VehicleCost rows on order
creation → actual VehicleCost rows on complete. M3 stops at
"we saw this and here's what we think it'd cost."

**Design note — no `photos` field on `ConditionFinding` itself.**
Photos live in a separate `ConditionFindingPhoto` model (§1.4)
so multi-photo attachment does not require a JSON field on the
finding row. This mirrors the M2 pattern of keeping
`VehicleCost` a single-row-per-line and modeling multi-value
relationships as separate tables.

### 1.3 Vehicle read-model extension

- **Business question answered.** "*Does this vehicle have a
  condition report? Which one is the latest complete one?*" — the
  question every operator inventory-list view needs to answer
  cheaply.
- **Citation.** M2.3 established the Vehicle-as-read-model pattern
  (see `MILESTONE_2_PLANNING.md` §1.3). M3 extends the same
  pattern conservatively.
- **Shape.** Two `@property` accessors on `Vehicle`, delegating to
  `services/condition_report.py`:
  - `latest_condition_report` — returns the most recent
    `ConditionReport` (any status) for the vehicle, or `None`.
  - `latest_completed_condition_report` — returns the most recent
    `ConditionReport` with `status="complete"`, or `None`. This
    is the accessor future callers (M4 recon plan drafting, the
    operator UI's "inspected on YYYY-MM-DD" badge) hit most
    often.
- **What Milestone 3 does NOT add.**
  - No `Vehicle.is_ready_for_frontline` computed property.
    Milestone 5 owns the front-line gate; M3 must not preempt
    it. The condition report's `status="complete"` is *one* of
    RECON §12.1's twelve checklist items, not the whole gate.
  - No `Vehicle.frontline_ready` FK, no
    `frontline_readied_at` timestamp — same reason.
  - No `@cached_property` in M3 v1 for the report accessors;
    the access pattern isn't yet proven to be
    read-heavy-with-repeat-access the way `ledger_totals` was.
    M3.3 revisits caching if `assertNumQueries` verification
    shows repeated lookups in the operator UI.

**Design note — narrow read-model surface.** M2.3 added nine
per-total delegators plus one temporal metric. M3.3 deliberately
ships only two accessors. The pattern is proven; the discipline
is "only expose what a real caller needs." If M3.7 (operator UI)
surfaces additional read patterns (finding count by severity,
most-recent-inspection-date, etc.) they land as targeted
properties in that same increment, not preemptively in M3.3.

### 1.4 Storage story — S3-compatible + CDN

> **This subsystem is the load-bearing pre-implementation
> decision.** See §5 for the three-option analysis and the
> chosen path.

- **Business question answered.** Q4. Photo evidence for warranty
  defense (RECON §13.1), vendor communication (RECON §2.5), and
  before/after documentation.
- **Citation.** `VEHICLE_CENTRIC_PIVOT.md` "Technical debt to pay
  down FIRST" item 3 ("File storage story. S3-compatible + CDN.
  Configured via env. Before `VehiclePhoto` ships.") and the
  Phase 2 description ("Multi-photo upload per finding — requires
  file storage from Phase 0"). `MILESTONE_2_RETROSPECTIVE.md` §7
  deferred item ("Multi-photo storage (S3-compatible + CDN) —
  Milestone 3 ConditionReport concern or a pre-M3 half-
  milestone").
- **Shape (per Option A chosen in §5).**
  - `django-storages` added to `requirements.txt` (already the
    canonical Django S3 story).
  - `DEFAULT_FILE_STORAGE` configured per-environment:
    - **Dev / test:** Django's default `FileSystemStorage`
      writing under `MEDIA_ROOT` (already exists in settings).
      Tests never touch S3; the storage abstraction is what
      lets us swap.
    - **Production:** `storages.backends.s3.S3Storage` with
      env-configured bucket, region, and (optionally) endpoint
      URL for S3-compatible providers (DigitalOcean Spaces,
      Backblaze B2, Cloudflare R2, MinIO).
  - Env surface (all optional; if unset, tests + dev use
    FileSystemStorage):
    - `AWS_STORAGE_BUCKET_NAME`
    - `AWS_S3_REGION_NAME`
    - `AWS_S3_ENDPOINT_URL` (for S3-compatible providers)
    - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (or IAM
      role in prod)
    - `AWS_S3_CUSTOM_DOMAIN` (for CDN — CloudFront /
      Cloudflare in front of the bucket)
  - **Presigned upload URLs.** The API returns a presigned
    PUT URL to the browser; the browser uploads the file
    directly to S3, never through the Django app server. This
    is the only pattern that scales past small photo counts
    without saturating the app server's request pipeline.
    Django serves only the metadata write (the
    `ConditionFindingPhoto` row).
  - **Read paths.** Signed CloudFront / bucket URLs with short
    TTL (5–15 minutes typical) — no permanent public URLs. The
    condition report is sensitive: warranty exposure evidence
    is not something a store wants indexed by search engines.
- **Extend.** Django's built-in storage abstraction; no parallel
  file-handling code. All uploads flow through the storage
  backend; nothing reaches disk directly.
- **Leave untouched.** No changes to any existing model. The
  onboarding profile's `logo` field (the platform's only pre-M3
  file field) can migrate to the new storage backend
  opportunistically — but that's out of M3 scope and does not
  need to happen in this milestone.

**Design note — presigned uploads over app-server proxying.** The
Django-through-the-app-server pattern (POST multipart to a Django
view, view writes to storage) is simpler but doesn't scale.
Presigned uploads are the standard pattern for browser-to-S3
uploads and the added complexity is contained in the M3.4 storage
service (one function returning `{upload_url, storage_key,
expires_at}`).

**Design note — signed read URLs, not public.** The
alternative (public bucket with obfuscated paths) is unsafe:
condition photos may show identifying details (VIN plates on
close-ups per RECON §2.5), and warranty-defense value depends on
the store controlling access. Short-TTL signed URLs are the
right shape.

### 1.5 Condition finding photo — `ConditionFindingPhoto` (many-per-ConditionFinding)

- **Business question answered.** Q4 concrete implementation.
- **Citation.** `RECON_MAPPING.md` §2.5 (photos in condition
  reporting — pre-existing damage documentation, vendor
  communication, insurance claims, before/after evidence).
- **Fields.**
  - `public_id` (UUIDField, required, unique, default
    `uuid.uuid4`, editable=False) — the durable public
    identity of the photo. External references (URLs, API
    payloads, log lines) use this value, never `storage_key`.
    Added as an amendment at SESSION_056 (M3.1); see
    §Design note — public identity is a UUID, not the storage
    key.
  - `finding` (FK to `ConditionFinding`, required,
    on_delete=CASCADE).
  - `dealership` (FK, NOT NULL from day one — denormalized;
    same rationale as `VehicleAcquisition.dealership`).
  - `storage_key` (CharField, required, unique) — the object
    key the storage backend understands. Internal storage
    locator only, not a public identifier. Storage-backend-
    agnostic in shape (an S3-style flat key); the storage
    service constructs the actual URL at read time. Populated
    only after the upload has been verified as landed (see
    §Design note — photo rows represent attached objects,
    never upload intentions).
  - `content_type` (CharField, required) — recorded at upload
    time from the browser's chosen MIME type. Whitelist
    enforced at the upload-URL-generation view (`image/jpeg`,
    `image/png`, `image/heic`, `image/webp`). Rejection of
    other types happens *before* the presigned URL is issued
    — the URL scopes the upload's `Content-Type` header so a
    malicious client cannot upload a `.exe` to a PNG endpoint.
  - `size_bytes` (PositiveIntegerField, required) — recorded
    on the S3 side after upload via a completion callback (or
    via HEAD on first-read; M3.5 chooses).
  - `caption` (CharField, blank) — free text ("driver-side
    rocker panel scratch") to accompany the photo.
  - `uploaded_by` (FK to `AUTH_USER_MODEL`, nullable,
    SET_NULL) — provenance.
  - Timestamps (`created_at`).
- **Extend.** New relationship on `ConditionFinding`. No changes
  to any existing model.
- **Leave untouched.** No `Vehicle.photos` or similar cross-
  cutting photo model in M3 — the M6 photography milestone will
  ship its own `VehiclePhoto` gallery for listing photos, and
  the two concerns are intentionally separate (RECON §2.5
  photos are documentation; M6 photos are marketing). Sharing
  a table would collapse two distinct lifecycles.

**Design note — no image processing in M3.** No thumbnail
generation, no EXIF stripping, no image resizing. Raw upload,
raw serve. Every downstream image concern (thumbnails, size
limits beyond the presigned-URL cap, EXIF privacy) is deferred
to whatever milestone first needs it. The M2 discipline of
"ship the minimal thing, revisit with operator evidence"
applies.

**Design note — content-type whitelist enforced at URL
issuance.** The presigned URL includes a `Content-Type`
condition; if the browser tries to upload a different MIME the
S3 API rejects the PUT. This is the standard S3 conditioned-
upload pattern; it's what prevents `.exe` uploads to
`ConditionFindingPhoto` even if a client forges the metadata.

**Design note — public identity is a UUID, not the storage
key.** *Reviewed refinement added at SESSION_056 (M3.1
implementation).* The original §1.5 draft used `storage_key`
as both the storage locator and the public identifier. That
conflates two lifecycles: the storage-backend object key is an
implementation detail (bucket layout, naming scheme, provider
choice — all of which can change) while the durable identity
external callers reference must survive rekeying, provider
migration, and CDN reconfiguration. `public_id` (UUIDField,
`default=uuid.uuid4`, unique, editable=False) is the field
external references bind to; `storage_key` remains an internal
locator the storage service reads. API payloads, URL segments,
audit-log lines, and cross-milestone references (e.g. a future
milestone that attaches photos to a different parent) use
`public_id`. This keeps M3.4 storage decisions from leaking
into observable identity, and it keeps the door open for
future non-finding parents to reuse the same storage
abstraction without a schema rename.

**Design note — photo rows represent attached objects, never
upload intentions.** *Reviewed refinement added at SESSION_056
(M3.1 implementation).* `storage_key` remains required and
unique at the schema level. The presigned-upload workflow (M3.5)
holds the prospective key transiently — outside the model
layer — until the upload lands and is verified (e.g. via HEAD).
Only after verification does the workflow create the
`ConditionFindingPhoto` row. Consequence: any row that exists
represents a successfully attached object; no null-guard
branches for "row exists but object doesn't" leak into read
paths, and no half-attached rows are ever visible to the
operator UI. If verification fails, the transient key is
discarded and no row is created. This mirrors M2's
"immutable-once-written" ledger discipline (retrospective §6
lesson 5) applied to storage identity.

### 1.6 Operator condition-report UI surface

- **Business question answered.** Q1–Q6 in a form. The recon
  manager (or dealer owner acting in that capacity) authors the
  report; the sales manager, tech, and future recon coordinator
  read it.
- **Citation.** `MILESTONE_2_PLANNING.md` §1.6 (operator ledger
  UI — the shape this UI mirrors); `AUTHENTICATION_MODEL.md`
  §2c (`authFetch` / `AuthContext` / `RequireAuth` primitives
  M3 reuses verbatim); VCP "Guardrails" #4 (do NOT build a
  monolithic single-role UI).
- **Shape (planning — final routes and components decided in
  M3.7).**
  - Route: `/dealer-ai-inventory/:stock/condition-report`
    inside `<RequireAuth>`, mirroring
    `/dealer-ai-inventory/:stock/ledger` from M2.7.
  - `frontend/src/pages/VehicleConditionReportPage.tsx` —
    the single page.
  - Three typed `lib/api.ts` helpers via `authFetch`:
    - `fetchLatestConditionReport(stock)` — returns the
      latest report (any status) + all findings + all photos,
      or `null`.
    - `createConditionReport(stock, payload)` — starts a new
      draft.
    - `updateConditionReport(stock, reportId, payload)` —
      edit fields on a draft (locks after complete).
    - `addConditionFinding(stock, reportId, payload)` — add
      a finding to a draft report.
    - `updateConditionFinding(stock, findingId, payload)` —
      edit a finding in a draft report.
    - `deleteConditionFinding(stock, findingId)` — delete a
      finding from a draft report.
    - `completeConditionReport(stock, reportId)` — one-way
      transition draft → complete.
    - `requestFindingPhotoUploadUrl(stock, findingId,
      {content_type, size_bytes})` — returns
      `{upload_url, storage_key, expires_at}`.
    - `attachFindingPhoto(stock, findingId, {storage_key,
      content_type, size_bytes, caption})` — records the
      metadata after browser-to-S3 upload completes.
  - "Condition report" button on operator inventory cards
    (URL-encoded stock; **not** exposed on public
    `/showroom`) — mirroring M2.7's "Ledger" button pattern.
  - Role-based show/hide on write forms via
    `useAuth().hasRole('sales_manager') ||
    hasRole('dealer_owner')` — belt on top of server-side 403.
  - Read-only display of complete reports (photos, findings,
    signatures, timestamps).
  - Editable UI for drafts (add/edit/delete findings, upload
    photos, complete the report).
- **Extend.** All frontend primitives from M1 · 4E
  (`authFetch`, `AuthContext`, `RequireAuth`, `LoginPage`,
  role-gating). All UI patterns from M2.7 (money-as-strings,
  distinct 401/403/404 UX, role-gated write forms).
- **Leave untouched.** No changes to the M2.7 ledger page. No
  changes to the existing `<RequireAuth>` boundary. No new
  route or nav for the customer-facing surface. No shadcn/UI
  component changes.

**Design note — draft vs. complete UI states.** Draft renders
edit affordances (add finding, remove finding, upload photo,
"Complete report" button); complete renders a read-only "signed
document" view with the inspector's name, inspection date, and
completion timestamp prominent. Once complete, the "Author new
report" button is the only way to make additions — enforcing
the immutability discipline from §1.1.

**Design note — manual browser smoke.** Same discipline as M2.7:
if the M3.7 shipping environment cannot drive an interactive
browser, the handoff explicitly says so (rather than falsely
claiming full smoke). Server-side pathway will still be locked by
tests; interactive click-through is a documented deferral.

### 1.7 What Milestone 3 enables for future milestones

Milestone 3 is deliberately "just the data shape" — the point of
the "AI role: NONE yet" invariant from VCP §Phase 2 is to prove
the data shape before automation lands on top. Concrete future
seams:

- **Milestone 4 (Recon Automation)** reads
  `ConditionReport.findings` where `severity in ('required',
  'safety')`, groups by `category`, and drafts a `WorkOrder`
  per group. The `estimated_cost` field is what M4's
  vendor-recommendation engine hits when suggesting bids. The
  M3 `authored_by` + `inspector_name` provenance is what
  M4's AI-drafted vendor emails cite ("per our inspection by
  [inspector_name] on [inspected_at], we found…").
- **Milestone 5 (Lifecycle Stages)** reads
  `Vehicle.latest_completed_condition_report` as one of the
  inputs to the `stage='frontline'` transition. But M5 owns
  the *decision*; M3 owns the *data*.
- **Milestone 8 (Operational Intelligence)** aggregates across
  `ConditionReport` history: inspection-quality variance per
  inspector, finding-frequency per category, correlation
  between skipped `recommended` items and post-sale warranty
  claims (RECON §14.14).
- **Milestone 11+ (Sale + Delivery)** attaches the completed
  `ConditionReport` to the deal jacket as the vehicle's
  provenance record — warranty defense on Day 45 when the
  customer returns with an issue (RECON §13.1).

---

## 2. Migration Impact Review

Every existing surface Milestone 3 touches, with the concrete work
required. Same shape as `MILESTONE_2_PLANNING.md` §2.

| # | Existing surface | Location | M3 impact | Required work |
|---|---|---|---|---|
| 1 | `Vehicle` model | `dealer_ai/models.py::Vehicle` | **Additive relationships only.** New reverse-related `condition_reports` (FK from `ConditionReport`). Two new `@property` accessors on `Vehicle` in M3.3 (`latest_condition_report`, `latest_completed_condition_report`) — delegates to service, no field changes. | None on `Vehicle` itself. Service layer in M3.2. Property additions in M3.3. |
| 2 | `services/tenancy.py` | `services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES` | **Additive.** Three new tenant carriers (`ConditionReport`, `ConditionFinding`, `ConditionFindingPhoto`) register with the `pre_save` autofill signal. Same registration pattern as the six existing carriers. | Extend `_TENANT_CARRIER_MODEL_NAMES` tuple in M3.1 (one line per model). Test coverage extends the existing `WritePathFallback.*` matrix. |
| 3 | `dealer_ai/permissions.py` | `IsSalesManagerOrOwnerAtActiveDealership` | **Directly reused, no extension.** Every new M3 endpoint composes `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]` — the M1 · 4D class unchanged. No `recon_manager` permission class in M3 (Milestone 4 first surfaces recon-manager workflows per M2 §5 deferral). | Import + apply in M3.6 view decorators. Zero code changes to permissions.py itself. |
| 4 | `services/llm_safety.py` | `apply_post_llm_scrubs` | **Zero impact.** No new scrub in M3. Condition reports are internal data authored by humans; they never surface in customer-facing LLM output paths. If a future surface exposes condition-report content to the LLM (M4 vendor-email drafting, for example), that milestone adds its own scrub. | None. |
| 5 | Customer-facing chat surfaces | `services/chat_engine.py`, `views.py::chat_start` / `chat_message` / vehicle_ask | **Zero impact.** Condition-report data never enters customer chat context. The M2.5 `acquisition_price` scrub proves the discipline; M3 inherits it. | None. |
| 6 | Public branding endpoints | `views.py::onboarding_profile` (GET), `views.py::salespeople_list` (public) | **Zero impact.** No change to any public-facing endpoint. | None. |
| 7 | Django admin | `admin.py` | **Additive.** Three new admin registrations (`ConditionReportAdmin`, `ConditionFindingAdmin`, `ConditionFindingPhotoAdmin`). List displays, filters, and search follow the M2 admin pattern (`VehicleAcquisitionAdmin` / `VehicleCostAdmin`). | Ship in M3.1 alongside the models. |
| 8 | `settings.py` | `dealer_kit/settings.py` | **Additive (Option A).** New env-driven `DEFAULT_FILE_STORAGE` selection (test/dev falls through to Django's default `FileSystemStorage`). New `AWS_*` optional env vars. No change to any existing setting. | Ship in M3.4 with the storage story. |
| 9 | `requirements.txt` | `backend/requirements.txt` | **Additive.** One new dependency: `django-storages[s3]` (which pulls `boto3`). No version upgrades to existing packages. | Ship in M3.4 with the storage story. |
| 10 | Media root / test isolation | `tests/*.py` | **Additive.** M3.5 tests use `tempfile.mkdtemp()` for photo upload tests to avoid polluting the dev `MEDIA_ROOT`. Existing test infrastructure otherwise unchanged. | Ship as part of M3.5 test fixtures. |
| 11 | Frontend `main.tsx` (route registration) | `frontend/src/main.tsx` | **Additive.** Register `/dealer-ai-inventory/:stock/condition-report` inside the existing `<RequireAuth>` block. Route sits alongside the M2.7 ledger route; nothing moves. | Ship in M3.7. |
| 12 | Frontend `lib/api.ts` | `frontend/src/lib/api.ts` | **Additive.** New typed helpers for the eight M3 endpoints (see §1.6). All via `authFetch`. Zero change to existing helpers. | Ship in M3.7. |
| 13 | Frontend `pages/` | `frontend/src/pages/` | **Additive.** New `VehicleConditionReportPage.tsx`. No changes to any existing page. | Ship in M3.7. |
| 14 | Operator inventory card | Wherever the M2.7 "Ledger" button lives on the operator inventory list. | **Additive.** New "Condition report" button, URL-encoded stock, next to the "Ledger" button. Not surfaced on public `/showroom`. | Ship in M3.7. |
| 15 | `services/dealer_config.py` | `services/dealer_config.py` | **Zero impact.** No new dealer config field for M3. If future work needs "photo retention days" or similar, that's a separate concern. | None. |
| 16 | M2 ledger service + endpoints + UI | `services/vehicle_ledger.py`, `views.py::admin_vehicle_ledger` etc., `pages/VehicleLedgerPage.tsx` | **Zero impact.** M3 does not touch M2 ledger surface. `ConditionFinding.estimated_cost` lives on the finding, not on `VehicleCost` (per §1.2 design note). | None. |
| 17 | `Vehicle.is_available` | `models.py::Vehicle` | **Zero impact.** No change to `is_available`. Milestone 5 refactors to computed lifecycle. | None. |
| 18 | Prod deployment | Render Blueprint | **NO IMPACT for M3 code.** Recon is an in-store workflow (RECON §12.2 sign-off happens at the store); Milestone 3 does not require prod. Field-based operator sessions land with M4 vendor emails or later. The storage story in M3.4 CAN be tested end-to-end against S3-compatible storage from a dev laptop with local env vars. | None in M3; document that first-live-prod deployment coincides with M4 or later. |

---

## 3. Compatibility Checklist

**Milestone 3 ships with this checklist verified true; evidence
recorded inline at milestone close.** Original invariants preserved
from M1 + M2; each row cites the test class, code location, or
runtime probe that locks it. Mirrors the shape
`MILESTONE_2_PLANNING.md` §3 established at SESSION_054 close.

### Milestone 1 + Milestone 2 invariants Milestone 3 must not regress

Tenancy substrate:
- [ ] `Dealership` model + migration `0007` unchanged.
- [ ] Every existing tenant-carrying model still has `dealership`
  FK NOT NULL.
- [ ] `services/tenancy.py::get_default_dealership` /
  `get_current_dealership` / `get_active_membership` unchanged
  in signature and contract.
- [ ] M3 tenant carriers (`ConditionReport`, `ConditionFinding`,
  `ConditionFindingPhoto`) register with the `pre_save`
  autofill signal. Explicit-`dealership=` writes still
  short-circuit the fallback.
- [ ] Every new M3 tenant-carrying model has `dealership` FK
  NOT NULL from day one.

Identity + authentication:
- [ ] `DEFAULT_PERMISSION_CLASSES` remains **unset**.
- [ ] `SessionAuthentication` + `TokenAuthentication` still
  installed.
- [ ] `/auth/{login,logout,me}` endpoints unchanged.
- [ ] Login endpoint still returns identical 401 for wrong
  password vs unknown user.
- [ ] CSRF still enforced on authenticated mutations.
- [ ] `CSRF_TRUSTED_ORIGINS` still includes dev + prod origins.

Existing endpoint-level permissions:
- [ ] Advisor workspace still authorized by
  `[IsAuthenticated & (IsAdvisorForSlug |
  IsDealerOwnerForAdvisorSlug)]`.
- [ ] Admin endpoints (M1 · 4D + M2.6 ledger) still authorized by
  `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`.
- [ ] Onboarding profile PUT/PATCH still requires
  `IsDealerOwnerAtActiveDealership`.
- [ ] Cross-tenant pk lookups on admin endpoints still fail
  closed (404).

Customer-facing surfaces:
- [ ] Public branding renders unauthenticated.
- [ ] Customer chat (`chat/start`, `chat/message`) unchanged.
- [ ] Per-vehicle Q&A (`vehicles/<id>/ask/`) unchanged.
- [ ] `/`, `/assistant`, `/showroom`, `/embed/assistant`, `/login`
  routes still resolve without a session.
- [ ] Condition-report data never appears in any customer-facing
  surface response body. (Server-side invariant locked by a
  focused test similar to M2's
  `PublicSurfacesNeverExposeLedgerData`.)

Safety stack (the moat):
- [ ] All 8 pre-LLM guards fire in existing order.
- [ ] All post-LLM scrubs including M2.5 `acquisition_price`
  unchanged.
- [ ] Every dollar figure in customer chat still comes from
  `services/payment_engine.py`.
- [ ] Budget-fit classification unchanged.
- [ ] Manager coaching chat still enforces Shape A / Shape B.
- [ ] Ad-copy generator still produces 2–3 variants, still passes
  through `invented_promotion` scrub.
- [ ] Advisor follow-up drafts still pass through
  `invented_appointment` scrub.

M2 ledger substrate:
- [ ] `services/vehicle_ledger.py` (`record_acquisition`,
  `add_cost`, `compute_totals`, `category_group_of`,
  `LedgerTotals`, `CrossTenantLedgerError`, `ZERO`) unchanged
  in signature and contract.
- [ ] `Vehicle.ledger_totals` `@cached_property` + all nine
  per-total delegators + `days_in_inventory` unchanged.
- [ ] `VehicleCost` immutability (no PUT/PATCH/DELETE) unchanged.
- [ ] `total_investment` semantic contract (excludes estimates)
  unchanged.
- [ ] M2.5 `_scrub_acquisition_price` regex + kind-firing
  unchanged.
- [ ] `manage.py accrue_floor_plan_interest` command signature +
  idempotency + dry-run behavior unchanged.
- [ ] M2.6 admin ledger endpoints
  (`/api/dealer-ai/admin/vehicles/<stock_number>/ledger/`
  etc.) unchanged.
- [ ] Money-as-strings API contract on M2.6 endpoints
  unchanged.
- [ ] M2.7 operator ledger UI at
  `/dealer-ai-inventory/:stock/ledger` unchanged.

Dealer identity resolution:
- [ ] `get_dealer_name()` + `get_dealer_profile()` +
  `get_floor_plan_apr()` still resolve DB → env → default in
  the documented order.
- [ ] Franchise env-override still works.
- [ ] Copper Canyon defaults still apply when neither env nor
  DB is set.

Frontend contracts:
- [ ] `useBrand()` + `useDealerProfile()` still resolve
  unauthenticated.
- [ ] `brand.*` Tailwind tokens unchanged.
- [ ] `authFetch` / `AuthContext` / `RequireAuth` / `LoginPage`
  unchanged in contract.
- [ ] Public / protected route split in `main.tsx` unchanged (M3
  adds routes *inside* `<RequireAuth>`).
- [ ] `npx tsc --noEmit` clean.
- [ ] `npx vite build` clean (pre-existing chunk-size warning
  acceptable — same as SESSION_054).

Test baseline:
- [ ] `python3 manage.py test dealer_ai` → **1,753 pass** (or the
  new baseline including M3 focused tests); 1 skipped, 0 fail.
- [ ] No test suppressed with `@skip` to make the baseline pass.

### New invariants Milestone 3 introduces

Model-layer:
- [ ] Every `ConditionReport` row has `dealership` FK NOT NULL
  matching its parent `Vehicle.dealership` (model `clean()`
  cross-tenant guard, same shape as M2).
- [ ] Every `ConditionFinding` row has `dealership` FK NOT NULL
  matching its parent `Vehicle` (via `.report.vehicle`).
- [ ] Every `ConditionFindingPhoto` row has `dealership` FK NOT
  NULL matching its parent `Vehicle` (via
  `.finding.report.vehicle`).
- [ ] `ConditionReport.status` validated at model layer via
  `choices=` (two values: `draft`, `complete`).
- [ ] `ConditionReport.completed_at` is NULL exactly when
  `status="draft"`; set exactly when `status="complete"`
  (locked by model `clean()`).
- [ ] `ConditionFinding.category` is validated at model layer via
  `choices=` (twelve canonical values).
- [ ] `ConditionFinding.severity` is validated at model layer via
  `choices=` (four canonical values).
- [ ] `ConditionFindingPhoto.storage_key` is unique at schema
  level (internal storage locator only — see §1.5 Design note
  "public identity is a UUID, not the storage key").
- [ ] `ConditionFindingPhoto.public_id` (UUIDField,
  `default=uuid.uuid4`, editable=False) is unique at schema
  level and is the durable external identity. External
  references (URLs, API payloads, log lines) MUST use
  `public_id`; `storage_key` MUST NOT be exposed.
- [ ] `ConditionFindingPhoto.content_type` restricted to the
  four-value image whitelist at the model layer.

Business-layer:
- [ ] `services/condition_report.py::create_report(vehicle, *,
  dealership, ...)` refuses cross-tenant writes at entry
  (`CrossTenantConditionReportError` — same shape as
  `CrossTenantLedgerError`).
- [ ] `add_finding(report, *, ...)` refuses cross-tenant.
- [ ] `complete_report(report)` refuses any transition other
  than `draft → complete`; raises on `complete → *`.
- [ ] `add_finding` / `update_finding` / `delete_finding` refuse
  writes when `report.status == "complete"`.
- [ ] `latest_condition_report(vehicle, *, dealership)` +
  `latest_completed_condition_report(vehicle, *, dealership)`
  refuse cross-tenant reads.

Endpoint-layer:
- [ ] Every new endpoint composes
  `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`.
- [ ] Every new endpoint calls
  `dealership = get_current_dealership(request)` once at top.
- [ ] Every new endpoint's queryset carries explicit
  `.filter(dealership=dealership)`.
- [ ] Cross-tenant `stock_number` OR `report_id` OR
  `finding_id` lookups fail closed (404).
- [ ] Full permission matrix locked per endpoint (unauth,
  wrong-role, wrong-tenant, correct owner, correct
  sales_manager — five cases minimum; six if the endpoint has
  a variant like "cost create" needing `created_by`
  attribution).
- [ ] `requestFindingPhotoUploadUrl` endpoint's response
  `expires_at` is never more than 15 minutes in the future
  (protects against long-lived upload URLs).
- [ ] `requestFindingPhotoUploadUrl` rejects non-whitelisted
  content types (400) before issuing the URL.
- [ ] `attachFindingPhoto` refuses to record a photo whose
  `storage_key` does not correspond to an actually-uploaded
  S3 object (verified via HEAD).

Storage-layer:
- [ ] `settings.DEFAULT_FILE_STORAGE` correctly resolves to
  `FileSystemStorage` in dev/test when env vars are unset;
  correctly resolves to `S3Storage` when env vars are set.
- [ ] Test suite runs with zero S3 network access.
- [ ] Photo read URLs are signed with TTL ≤ 15 minutes.
- [ ] No public bucket policy is required.

Frontend:
- [ ] Condition-report page is inside `<RequireAuth>`.
- [ ] Condition-report page fetch calls use `authFetch`.
- [ ] Anonymous navigation to the condition-report URL
  redirects to `/login?next=…`.
- [ ] Advisor-role user navigating to the URL sees the 403
  UI, not the report.
- [ ] No condition-report figure appears in any customer-facing
  surface (`/`, `/assistant`, `/showroom`, `/embed/assistant`).
- [ ] "Condition report" button is on operator inventory cards
  but **not** on public `/showroom` cards.
- [ ] Complete-report UI is fully read-only (no edit
  affordances rendered).
- [ ] Draft-report edit affordances gated on
  `useAuth().hasRole('sales_manager') ||
  hasRole('dealer_owner')`.

---

## 4. Reusable Primitives Review

Primitives from `IMPLEMENTATION_ROADMAP.md` §3 cited by Milestone 3.
All should be **extended or directly reused**, not paralleled.

### §3.1 LLM safety stack — `services/llm_safety.py`

- **Current shape.** `apply_post_llm_scrubs(text, *, kind) ->
  (cleaned_text, scrubs_fired, dropped_reason)`. Extended in
  M2.5 with `_scrub_acquisition_price`.
- **Sufficient for Milestone 3?** *Not consulted.* M3 does not
  emit any LLM output that carries condition-report content —
  the milestone is deliberately AI-free per VCP §Phase 2.
  Cited here only to record that M3 explicitly does not touch
  this primitive. **M4 will extend it** with the invented-recon-
  fact scrub per VCP §Phase 3.
- **What Milestone 3 does NOT change.** Nothing.

### §3.2 Payment engine — `services/payment_engine.py`

- **Not consulted.** M3 does no money math. `ConditionFinding.estimated_cost`
  is a stored Decimal; no computation happens on it in M3.
- **What Milestone 3 does NOT change.** Nothing.

### §3.5 Vehicle model + inventory identity

- **Current shape.** `stock_number` (globally unique), VIN, YMM,
  features, `source`, `imported_at`, `last_seen_at`,
  `dealership` FK NOT NULL, `is_available` (boolean), plus M2.3's
  ledger read-model surface (`ledger_totals` cached property + nine
  delegators + `days_in_inventory`).
- **Sufficient for Milestone 3?** *Yes, with:*
  - New FK related model `ConditionReport`.
  - Two new `@property` methods (`latest_condition_report`,
    `latest_completed_condition_report`) that delegate to
    `services/condition_report.py`.
- **Extension justification.** `Vehicle` is the identity primitive
  the condition report hangs off — same pattern M2.3 established
  for the ledger.
- **What Milestone 3 does NOT change.** No changes to any
  existing Vehicle field. No stock_number uniqueness change
  (still deferred). No `make="Ford"` default rename (still
  deferred). No `is_available` → computed lifecycle (Milestone 5).

### §3.6 Inventory import — `services/inventory_import.py`

- **Not consulted.** M3 does not import condition-report data
  from CSV or any external feed. Every report is authored
  through the UI.
- **What Milestone 3 does NOT change.** Nothing.

### §3.7 Recommended-actions engine — `services/pipeline.py`

- **Not consulted.** M3 does not emit recommended actions from
  condition reports. That is Milestone 8 operational intelligence
  (aging-alert + inspection-quality analytics). Cited here to
  record that M3 explicitly does not fold M8 scope in.
- **What Milestone 3 does NOT change.** Nothing.

### §3.9 Dealer identity resolver — `services/dealer_config.py`

- **Not consulted.** M3 does not add a new dealer config field.
  Storage backend selection uses standard Django settings, not
  the layered resolver.
- **What Milestone 3 does NOT change.** Nothing.

### §3.10 Dealer onboarding profile

- **Not consulted.** No new onboarding profile field for M3.
- **What Milestone 3 does NOT change.** Nothing.

### Directly reused (no extension) — `services/tenancy.py`

- Consumed by every new view (`get_current_dealership(request)`)
  and every new service function (`dealership=` kwarg per M1 §8b).
- Three new tenant carriers register with the existing
  `_TENANT_CARRIER_MODEL_NAMES` tuple in M3.1. The registration
  pattern is unchanged from the six existing carriers.

### Directly reused (no extension) — `dealer_ai/permissions.py`

- `IsSalesManagerOrOwnerAtActiveDealership` composes onto every
  new M3 endpoint. Covers the "operator can look at + manage
  condition data" concern.
- **No new permission class in M3.** `recon_manager` access
  lands in M4 when recon-manager workflows first surface (per
  M2 §5 deferral confirmed by
  `MILESTONE_2_RETROSPECTIVE.md` §7). M3 uses the sales_manager
  + dealer_owner role composition unchanged.

### Directly reused (no extension) — M2 ledger service

- `services/vehicle_ledger.py::add_cost` is the future write
  path M4 will call when auto-minting `VehicleCost` rows from
  completed work orders. M3 does not call `add_cost` — the
  `ConditionFinding.estimated_cost` field lives on the finding
  as documentation only.
- `services/vehicle_ledger.py::compute_totals` continues to
  power the operator ledger UI unchanged.

### Genuinely greenfield in Milestone 3

- `ConditionReport` model.
- `ConditionFinding` model.
- `ConditionFindingPhoto` model.
- `services/condition_report.py` service module.
- Storage backend abstraction (via `django-storages`; the
  package is new, but the pattern is Django-standard).
- Frontend `VehicleConditionReportPage.tsx`.

Everything above is either a new file or a small extension of
an existing primitive (`Vehicle` gets two property delegators;
`services/tenancy.py` gets three carrier registrations). **No
parallel implementations proposed.**

---

## 5. Scope Discipline + Deferrals

Ideas that surfaced during this pass that would expand scope
beyond Milestone 3. Per the Discovery Rule: **deferred, not
discarded.**

### 5.a The load-bearing storage decision

`MILESTONE_2_RETROSPECTIVE.md` §7 identified the storage decision
as the load-bearing pre-M3 concern. Three options:

**Option A — Fold storage into Milestone 3.** Ship the storage
abstraction (`django-storages` config, presigned upload URL
helper, `ConditionFindingPhoto` model) as its own M3 increment
(§7.b M3.4) BEFORE `ConditionFinding` photo attachment lands
(M3.5).

- **Pros:** Storage lands with the milestone that first uses it.
  No pre-M3 coordination overhead. The M3 planning artifact
  captures both concerns as one cohesive plan.
- **Cons:** Increases M3's total surface area (adds one
  increment). If storage takes longer than the plan predicts,
  it delays the whole M3 photo-attachment story.

**Option B — Pre-M3 half-milestone (M2.9 or M3.0).** Ship storage
alone as a small standalone milestone, then M3 planning targets
its use.

- **Pros:** Cleanly separates concerns. Storage story ships and
  gets its own retrospective before condition-report work
  starts.
- **Cons:** Half-milestones defer coordination without avoiding
  the work. The storage plan has to know its consumer
  (`ConditionFindingPhoto`) anyway. Two planning artifacts
  where one would suffice. Adds a session boundary that costs
  handoff overhead.

**Option C — Ship M3 without photos.** Findings text-only for
v1; photo attachments deferred to a later ConditionReport
iteration.

- **Pros:** Smallest M3 surface. Fastest to ship the "human-
  authored inspection discipline" data shape.
- **Cons:** Substantially weaker for warranty defense (RECON
  §13.1 explicitly names photo documentation as the legal
  record). Vendors communicate faster with photos (RECON §2.5).
  Skipping photos would leave one of the four core operational
  questions (Q4) unanswered by M3, forcing a subsequent
  iteration.

**Decision — Option A.**

Reasoning:
1. **Half-milestones defer coordination without avoiding work.**
   Option B splits one dependency chain into two sessions that
   still have to know about each other; that is pure overhead.
2. **The storage story is small if kept minimal.** M3.4's
   scope is: one `requirements.txt` line, one settings block,
   one presigned-URL helper function (~30 lines of service
   code), and its focused tests. No image processing, no
   thumbnail generation, no CDN configuration beyond an env
   variable. This fits an increment cleanly.
3. **Photos are load-bearing for warranty defense.** RECON
   §13.1 names condition documentation as the legal record; a
   text-only report weakens the store's chargeback / small-
   claims position in Day 45 disputes. Option C's simplicity
   is offset by the operational hole it leaves.
4. **Increment-discipline lesson from M2.** Retrospective §6
   lesson 1: "no session should ship two independent
   responsibilities at once unless one truly cannot be tested
   without the other." Option A honors this — M3.4 (storage
   abstraction) and M3.5 (`ConditionFindingPhoto` model +
   upload flow) are two separate increments with independent
   test surfaces even though they land in the same milestone.

The eight-increment sequence in §7 reflects Option A.

### 5.b Other deferred ideas

| Idea | Why it's tempting | Discovery-Rule verdict | Deferred to |
|---|---|---|---|
| `WorkOrder` model + AI-drafted work orders from findings | Natural next step; the whole reason the ConditionReport data shape exists is to feed recon automation. | Explicitly deferred to Milestone 4 by both the roadmap §Milestone 3 out-of-scope list and VCP §Phase 3. Building it in M3 folds M4 scope and prevents the "prove the data shape before automating on top" invariant from VCP §Phase 2. | Milestone 4 (Recon automation) |
| `Vendor` FK model on findings (which vendor should do this?) | Same rationale as M2's deferral. | Deferred to Milestone 4. M3 findings do not reference vendors; the recon-planning decision (RECON §3.6 vendor selection per job) is what M4 owns. | Milestone 4 (Recon automation) |
| Vehicle lifecycle stage advancement based on condition report completion | Feels natural — completing a report is a milestone in the vehicle's journey. | Deferred to Milestone 5 (Lifecycle stages + retail gating). RECON §12.1 lists twelve items in the front-line-ready checklist; condition-report-complete is only item 1. Preempting M5 by adding stage transitions in M3 would corrupt the "M5 owns the retail gate" boundary. | Milestone 5 (Lifecycle stages) |
| Auto-minting `VehicleCost(is_estimate=True)` from `ConditionFinding.estimated_cost` | The M2 `is_estimate` field on VehicleCost was designed for exactly this. | Rejected in §1.2 design note: posting estimate cost rows before the recon plan decision (RECON §3.1 must / should / won't) would inflate `projected_total_investment` for advisory findings the store will never spend on. M4 owns the flow: findings → recon plan → work orders → estimate cost rows on order creation. | Milestone 4 (Recon automation) |
| `recon_manager` role permission class on the condition-report endpoints | RECON §12.2 sign-off authority names the recon manager as the primary owner. | Deferred to Milestone 4 (same reasoning as M2 §5). M3 uses `sales_manager` + `dealer_owner` because those are the roles that own the platform today; adding `recon_manager` here without a live recon-manager user creates a permission class with no consumer. When M4 introduces recon-manager workflows the class lands then. | Milestone 4 (Recon automation) |
| `Warranty callback` tracking (customer returned Day 45 with an issue) | RECON §14.14 names it as a real recurring pain. | Deferred. Post-sale warranty is a Milestone 4 or later concern; M3 provides the *inspection record* that warranty defense depends on but does not itself track callbacks. Explicitly named out-of-scope in the SESSION_055 brief. | Milestone 4 (Recon automation) or later |
| Bulk photo upload (drag-and-drop 20 photos at once) | Common recon workflow; a single vehicle inspection can produce 20–40 photos per RECON §9.1. | Rejected for v1: single-photo-at-a-time UX ships faster and each upload is independent. Add bulk drag-and-drop when operator evidence surfaces friction. | Data-first — revisit with operator evidence |
| Image processing (thumbnails, EXIF stripping, resize) | Storage cost + bandwidth cost + privacy (EXIF may leak GPS). | Rejected for v1 per §1.5 design note. Every image concern is deferred to whatever milestone first needs it. | Data-first — revisit with operator evidence |
| Reopen a completed report | Sometimes an inspector realizes they missed something after clicking Complete. | Rejected for v1 per §1.1 design note. Corrections happen by authoring a **new** report against the same vehicle. Revisit only if operator feedback surfaces friction. | Data-first — revisit with operator evidence |
| Inspection templates ("standard used-car inspection form" the inspector clicks through) | Reduces authoring friction; enforces coverage. | Deferred. Templates are a UX optimization on top of the raw data shape. Ship the raw shape first; add template-driven authoring when operator evidence shows freeform authoring produces incomplete inspections. | Data-first — revisit with operator evidence |
| Inspection scheduling (pre-inspection notification, vendor coordination) | RECON §5 vendor management is real pain. | Explicitly M4 scope. M3 records what an inspection *found*; scheduling the next inspection is a workflow concern. | Milestone 4 (Recon automation) |
| Historical-cost-informed cost estimates ("similar findings cost $X on prior vehicles") | RECON §16.15 recon-cost prediction. | Explicitly Milestone 8 scope. Requires historical corpus that M3 begins accumulating; the AI-driven estimation is M8's own concern. | Milestone 8 (Operational intelligence) |
| Photo aging (retake photos after significant time — RECON §9.6) | Sensible discipline; the recon report needs current photos. | Rejected for v1. Photo aging is a scheduling / notification concern; M3 records photos as timestamped uploads and lets the operator decide when to add more. | Data-first — revisit with operator evidence |
| Inspection-quality analytics (which inspector produces the most / fewest post-sale surprises?) | RECON §7.2 QC checklist patterns; §14.4 inspection quality variance. | Explicitly Milestone 8. M3 records `authored_by` + `inspector_name` per report; M8 aggregates. | Milestone 8 (Operational intelligence) |
| Cross-department findings surface (F&I sees safety findings on VSC-eligible units) | Cross-department context is real; RECON §17.3 lists F&I dependency on recon. | Deferred. M3's operator UI is inspection-focused; cross-department views are Milestone 12+ (aggregate dashboards / cross-role UI). | Milestone 12+ |
| Recall check integration (VIN → NHTSA open recall query) | RECON §16.17 named it. | Deferred. Adds an external-API dependency and belongs to a broader compliance track (RECON §18 "Titles / DMV" and "Compliance" deferred research topics). Not this milestone. | Separate compliance-track milestone |
| Prod deployment as part of M3 | The M2 retrospective §7 flags prod as needing to land alongside the first field-based milestone. | M3 does not require prod (recon sign-off happens at the store — RECON §12.2). Field-based operator sessions land with M4 vendor emails or later. Land prod alongside M4. | Alongside M4 |
| Fresh-DB seed script that includes condition-report data | The Copper Canyon demo currently has zero ledger data (M2 §7 deferral) and would similarly have zero condition-report data. | Deferred to a small developer-productivity increment (same deferral bucket as the M2 seed-with-ledger-data note in retrospective §7). Not M3 scope. | Developer-productivity increment |
| Playwright end-to-end tests for M3 UI | Same tooling already staged in `frontend/package.json` devDependencies from M2.7. | Deferred (same reasoning as M2). Not blocking; complements manual operator smoke. Revisit as a hardening pass across the operator UI surface. | Hardening pass |
| Ledger-write audit logging | The M2 retrospective §7 named it as a Milestone 8 concern. | Same deferral applies to condition-report writes. Structured audit of who-signed-off-what would matter for warranty-defense evidence chains, but that is post-sale (Milestone 4+). | Milestone 4+ or Milestone 8 |

Ideas explicitly *not* deferred here (they belong to earlier
sessions' deferral lists and remain deferred by inheritance):

- SSO / MFA. Deferred per M1 §5.
- User-management UI. Deferred per M1 §5.
- Dealership-switcher UI. Extension seam left inside
  `get_active_membership` per M1 §8.
- Everything in M2 retrospective §7 that is not addressed by M3
  (expected_gross, curtailment automation, cost update/delete,
  DMS-style deal recap, etc.).

**`docs/DEFERRED_IDEAS.md` still does not exist.** Every deferred
idea has a home in an existing planning / retrospective / handoff
doc. If an M3 session surfaces a deferral that does not cleanly
fit any of those, create the file at that moment and lift the
table above into it as the seed. Do not create the file
speculatively.

---

## 6. Anchors that win on conflict

If this planning doc disagrees with:

1. `docs/PROJECT_RULES.md` — the rules win.
2. `docs/DOC_GOVERNANCE.md` — the doc governance wins.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3 — the
   roadmap wins on scope questions.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — the auth model wins
   on identity / tenancy / permission questions.
5. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons — the
   lessons win on engineering-process questions.
6. `docs/research/RECON_MAPPING.md` +
   `docs/research/VEHICLE_CENTRIC_PIVOT.md` — the research wins
   on business-truth questions.
7. `docs/CAPABILITY_MATRIX.md` — the matrix wins on "what does
   the software actually do today?" questions.
8. Current source code — the code wins on "what does the
   software actually do today?" questions.

Planning docs are claims. Rules + research + code are facts.

---

## 7. Increment sequencing

The design memo (§1) describes *what* Milestone 3 delivers. This
section records *how* the work is sliced into per-session
increments so each session ends with the app deployable and the
test baseline healthy.

Mirrors the shape `MILESTONE_2_PLANNING.md` §7.b proved out —
eight increments, one per session, each with focused tests and
full-suite verification at the boundary. The M2 retrospective §8
guidance explicitly recommended this over the original three-
increment sketch, and every §7.b increment landed cleanly across
SESSION_046–SESSION_054.

**Increment discipline for §7.** Every session lands one
increment. No session ever bundles two increments to "save time";
the increment discipline that made Milestones 1 + 2 successful
is preserved verbatim here.

### Increment 1 (M3.1) — Core condition-report models — SHIPPED at SESSION_056

**Scope.** `ConditionReport` + `ConditionFinding` +
`ConditionFindingPhoto` models. Migration `0015` (or whatever the
next sequential number is at SESSION_056 time). Admin
registrations. Category enum (twelve values) + severity enum
(four values) + status enum (two values) + content-type
whitelist (four values) as module-level constants (mirroring
M2.1's `ROLE_CHOICES` / `VEHICLE_COST_CATEGORY_CHOICES` pattern).
Cross-tenant model `clean()` guards on all three models (same
shape as `VehicleAcquisition.clean` / `VehicleCost.clean`).
`_TENANT_CARRIER_MODEL_NAMES` tuple in `services/tenancy.py`
extended to register the three new carriers with the `pre_save`
autofill signal. `DATABASES["migration_check"]` alias verified
against the new migration.

**No service module in M3.1.** Persistence layer only.

**Tests.** ~40 focused model tests: schema (dealership FK NOT
NULL, choices validation, one-to-many relationships,
cascade-delete behavior), cross-tenant guards (clean() rejects
mismatched dealership on all three models), enum coverage (each
category / severity / status / content-type appears exactly
once in choices tuple), `_TENANT_CARRIER_MODEL_NAMES` extension
(three new registrations without breaking the six existing
ones).

**Boundary.** Test baseline: 1,753 → ~1,793 pass (all new;
zero regressions).

**No API. No frontend. No service. No storage.**

**Shipped surface (SESSION_056).**

- Models: `backend/dealer_ai/models.py`
  - `ConditionReport` — 10 fields (vehicle FK, dealership FK,
    authored_by FK nullable SET_NULL, inspector_name CharField,
    inspected_at DateTimeField, mileage_at_inspection
    PositiveIntegerField, status CharField default `draft`,
    completed_at DateTimeField nullable, notes TextField blank,
    created_at + updated_at). `clean()` enforces cross-tenant
    guard + `completed_at` ↔ `status` invariant.
  - `ConditionFinding` — 8 fields (report FK, dealership FK,
    category CharField 12-value choices, severity CharField
    4-value choices, description TextField required,
    estimated_cost Decimal nullable, notes TextField blank,
    created_at + updated_at). `clean()` enforces cross-tenant
    guard via `report.vehicle.dealership`. `estimated_cost`
    is documentation-only and never touches `VehicleCost`
    (invariant locked by
    `test_condition_finding.EstimatedCostDoesNotPostToVehicleCost`).
  - `ConditionFindingPhoto` — 9 fields (public_id UUIDField
    unique editable=False default=uuid.uuid4, finding FK,
    dealership FK, storage_key CharField required unique,
    content_type CharField 4-value whitelist, size_bytes
    PositiveIntegerField, caption CharField blank,
    uploaded_by FK nullable SET_NULL, created_at). `clean()`
    enforces cross-tenant guard via
    `finding.report.vehicle.dealership`.
- Enum constants (module-level in `models.py`):
  - `CONDITION_REPORT_STATUS_CHOICES` (2 values).
  - `CONDITION_SEVERITY_CHOICES` (4 values, escalation order).
  - `CONDITION_CATEGORY_CHOICES` (12 values, flat).
  - `CONDITION_PHOTO_CONTENT_TYPE_CHOICES` (4 values).
- Migration: `backend/dealer_ai/migrations/0015_condition_report.py`.
  Round-tripped clean-slate against `DATABASES["migration_check"]`.
- Admin: `backend/dealer_ai/admin.py` — `ConditionReportAdmin`,
  `ConditionFindingAdmin`, `ConditionFindingPhotoAdmin` mirroring
  `VehicleAcquisitionAdmin` / `VehicleCostAdmin` shape.
- Tenancy carrier extension: `backend/dealer_ai/services/tenancy.py`
  `_TENANT_CARRIER_MODEL_NAMES` extended 6 → 9.
- Tests: three new files totaling 57 focused tests —
  `backend/dealer_ai/tests/test_condition_report.py` (17),
  `test_condition_finding.py` (20),
  `test_condition_finding_photo.py` (20). Extended
  `WritePathFallback` in `test_dealership.py` with three
  autofill tests (6 → 9 carriers verified in-place).
- Planning-doc refinement: §1.5 amended to add UUID public
  identity + storage_key as internal locator + "photo rows
  represent attached objects, never upload intentions"
  design note. §3 checklist updated to lock the new
  `public_id` invariant.

**Baseline delta.** 1,753 → 1,813 pass, 1 skipped, 0 fail
(60 new tests: 57 model tests + 3 tenancy autofill).

### Increment 2 (M3.2) — Condition-report service layer — SHIPPED at SESSION_057

**Scope.** `services/condition_report.py` module with:
- `create_report(vehicle, *, dealership, authored_by,
  inspector_name, inspected_at, mileage_at_inspection,
  notes="") -> ConditionReport` — always creates in
  `status="draft"`.
- `complete_report(report) -> ConditionReport` — one-way
  transition draft → complete; sets `completed_at`; raises on
  `complete → *`.
- `add_finding(report, *, category, severity, description,
  estimated_cost=None, notes="") -> ConditionFinding` —
  refuses when `report.status == "complete"`.
- `update_finding(finding, **kwargs) -> ConditionFinding` —
  refuses when parent report is complete.
- `delete_finding(finding) -> None` — refuses when parent
  report is complete.
- `latest_condition_report(vehicle, *, dealership) ->
  Optional[ConditionReport]` — deterministic ordering.
- `latest_completed_condition_report(vehicle, *, dealership) ->
  Optional[ConditionReport]` — filter to `status="complete"`.
- `CrossTenantConditionReportError(ValueError)` — fail-closed
  guard on every function (same shape as
  `CrossTenantLedgerError`).
- Every function threads `dealership=` explicitly per
  `AUTHENTICATION_MODEL.md` §8b.

**Tests.** ~50 focused service tests: create semantics (always
draft; explicit `dealership=` required); complete transition
(one-way; raises on double-complete); finding CRUD gated by
report status; cross-tenant guards on all seven functions;
deterministic ordering for `latest_*` accessors; `full_clean()`
runs before save on every write.

**Boundary.** Test baseline: ~1,793 → ~1,843 pass. No migrations.
No API. No frontend. No `Vehicle` `@property` methods (that is
M3.3).

**Shipped surface (SESSION_057).**

- Service module: `backend/dealer_ai/services/condition_report.py`
  (567 lines) exporting seven public functions per the scope list
  above.
- **Reviewed refinement — `dealership=` on every function.** The
  planning contract above names `dealership=` on `create_report`
  and the two `latest_*` accessors. As shipped, `complete_report`,
  `add_finding`, `update_finding`, and `delete_finding` also take
  `dealership=` explicitly. Every call site must state its
  tenant intent; the service refuses to touch a report or finding
  whose denormalized `dealership` disagrees. This is a
  *tightening*, not a divergence — no user-visible surface exists
  yet (M3.6 lands the endpoints); the tightening keeps the
  security posture uniform across all seven functions.
- **Domain errors** (both subclass `ValueError`):
  - `CrossTenantConditionReportError` — fail-closed guard at the
    entry of every function.
  - `ConditionReportImmutableError` — refuses edits, additions,
    deletions, or re-completion when `report.status` is
    already `complete`. Distinct class so the M3.6 API layer can
    map it to HTTP 409 Conflict specifically, while cross-tenant
    maps to 404/403.
- **Finding-level cross-tenant check** verifies BOTH
  `finding.dealership == dealership` AND
  `finding.report.vehicle.dealership == dealership`. Per
  SESSION_057 spec: a finding sits two FK hops away from the
  vehicle and either drift is a cross-tenant leak.
- **Immutability guard** (`_refresh_and_assert_draft`) refreshes
  the parent report from DB on every mutation entry — narrow race
  handling for "another process completed while I was holding a
  stale in-memory draft."
- **`update_finding` whitelist:** `category`, `severity`,
  `description`, `estimated_cost`, `notes`. Attempting to set
  any other field (including `report`, `dealership`, `id`,
  `dealership_id`) raises `ValueError`. Re-parenting /
  re-scoping is not an editing operation.
- **`estimated_cost` locked as documentation-only** at the
  service layer with three focused tests
  (`EstimatedCostRemainsInformational` class) — no service
  operation ever creates or modifies a `VehicleCost` row.
- **Deterministic reads** — two focused tests verify repeated
  `latest_*` calls with identical arguments return identical
  results.
- **Tests:** `backend/dealer_ai/tests/test_condition_report_service.py`
  — **61 tests** across thirteen test classes covering: cross-
  tenant on all 7 functions, `create_report` semantics,
  `complete_report` semantics + double-complete refusal +
  `completed_at` never shifts on refusal, `add_finding` +
  invalid category/severity + empty description, `update_finding`
  + whitelist enforcement + re-validation, `delete_finding`,
  composite completed-report immutability, `estimated_cost`
  no-op on `VehicleCost`, `latest_*` accessors, deterministic
  reads, `full_clean` fires before save, transaction behavior
  on refusal (no partial state), full-severity-coverage smoke.

**Baseline delta.** 1,813 → 1,874 pass, 1 skipped, 0 fail
(61 new tests). No migrations. No API. No frontend. No storage.
No AI.

**Files changed (SESSION_057).**

- New: `backend/dealer_ai/services/condition_report.py`.
- New: `backend/dealer_ai/tests/test_condition_report_service.py`.
- No modifications to any existing file. `models.py`,
  `admin.py`, `services/tenancy.py`, `services/vehicle_ledger.py`,
  `services/llm_safety.py`, `permissions.py`, migrations,
  requirements, frontend — all untouched.

### Increment 3 (M3.3) — Vehicle read-model extension

**Scope.** Two `@property` accessors on `Vehicle`, delegating to
`services/condition_report.py`:
- `latest_condition_report` — returns most recent report of
  any status, or `None`.
- `latest_completed_condition_report` — returns most recent
  report with `status="complete"`, or `None`.

**No `@cached_property` in v1.** The M2.3 `ledger_totals`
cached-property pattern is proven for read-heavy repeated-access
data (nine per-total delegators would otherwise fire nine
queries). M3's report accessors are lighter — the operator UI
reads at most both once per page load. If subsequent operator UI
work reveals repeated access, promote to `@cached_property` at
that moment; do not preemptively cache.

**Tests.** ~15 focused tests: correct behavior when the vehicle
has no reports, one draft, one complete, multiple mixed, mixed
across tenants (cross-tenant vehicles never leak through).
`assertNumQueries` verification that each property access costs
exactly one query.

**Boundary.** Test baseline: ~1,843 → ~1,858 pass. No migrations.
No API. No frontend.

### Increment 4 (M3.4) — Storage story (S3-compatible + CDN)

**Scope.** Storage abstraction landing BEFORE the model that uses
it (deliberate sequencing so M3.5 has a real dependency to bind
against):
- `django-storages[s3]` added to `backend/requirements.txt`.
- `settings.py::DEFAULT_FILE_STORAGE` selection: env-driven
  (`AWS_STORAGE_BUCKET_NAME` present → `S3Storage`; else →
  Django's default `FileSystemStorage`).
- `services/photo_storage.py` module with:
  - `generate_upload_url(*, storage_key, content_type,
    max_size_bytes) -> dict` — returns
    `{upload_url, storage_key, expires_at, method}` where the
    presigned URL is scoped to the content type + max size,
    and TTL ≤ 15 minutes.
  - `object_exists(storage_key: str) -> bool` — HEAD verification
    used by the `attachFindingPhoto` endpoint (M3.6) to reject
    metadata for objects that don't actually exist.
  - `generate_read_url(*, storage_key, ttl_seconds=900) -> str`
    — signed read URL for the frontend.
  - Content-type whitelist enforced at
    `generate_upload_url` entry (`image/jpeg`, `image/png`,
    `image/heic`, `image/webp`).
- Env docs updated in `dealer_kit/settings.py` header comment
  block naming every new `AWS_*` variable and the
  local-dev fall-through.

**Tests.** ~25 focused tests: content-type whitelist enforcement
(non-image types raise `ValueError`), TTL cap (never > 900
seconds), URL contains the storage key, dev/test fall-through to
`FileSystemStorage` when env unset. Tests use `moto` or an
S3-compatible mock — zero real network access.

**Boundary.** Test baseline: ~1,858 → ~1,883 pass. One new
dependency. No new models. No API. No frontend.

### Increment 5 (M3.5) — Condition-finding photo model + upload flow

**Scope.**
- `ConditionFindingPhoto` model + migration (probably `0016`).
- Admin registration.
- Service functions in `services/condition_report.py`:
  - `request_photo_upload(finding, *, content_type, size_bytes,
    dealership, uploaded_by) -> dict` — validates finding's
    parent report is draft; validates content type; issues the
    presigned URL via `services/photo_storage.py`; returns
    `{upload_url, storage_key, expires_at}`.
  - `attach_photo(finding, *, storage_key, content_type,
    size_bytes, caption, uploaded_by, dealership) ->
    ConditionFindingPhoto` — verifies the S3 object exists via
    HEAD, verifies size matches (mitigates client size lying),
    creates the metadata row.
  - `delete_photo(photo, *, dealership) -> None` — refuses when
    parent report is complete; removes both S3 object and
    metadata row (best-effort delete on S3; metadata row is the
    source of truth).

**Tests.** ~30 focused tests: photo upload happy path,
non-whitelisted content type rejected at upload-URL issuance,
attaching metadata for non-existent S3 object fails,
size-mismatch rejection, delete-on-draft, delete-refused-on-complete,
cross-tenant guards.

**Boundary.** Test baseline: ~1,883 → ~1,913 pass. One migration.
No API. No frontend.

### Increment 6 (M3.6) — Condition-report admin API + permission matrix

**Scope.** Eight endpoints under
`/api/dealer-ai/admin/vehicles/<stock_number>/…`:
- `GET .../condition-report/latest/` — returns latest report
  (any status) + all findings + all photos with signed read
  URLs, or 404.
- `POST .../condition-reports/` — creates a new draft report.
- `PATCH .../condition-reports/<report_id>/` — edits fields on
  a draft.
- `POST .../condition-reports/<report_id>/complete/` — one-way
  transition to complete.
- `POST .../condition-reports/<report_id>/findings/` — add a
  finding.
- `PATCH .../findings/<finding_id>/` — edit a finding (parent
  report must be draft).
- `DELETE .../findings/<finding_id>/` — delete a finding
  (parent report must be draft).
- `POST .../findings/<finding_id>/photos/upload-url/` — request
  a presigned upload URL.
- `POST .../findings/<finding_id>/photos/` — attach a photo
  after upload completes.
- `DELETE .../photos/<photo_id>/` — remove a photo (parent
  report must be draft).

Permission composition `[IsAuthenticated &
IsSalesManagerOrOwnerAtActiveDealership]` on every endpoint (M1
· 4D class reused unchanged). All endpoints wrap the M3.2 /
M3.5 service — no endpoint bypasses to
`ConditionReport.objects.create` etc. DRF `Serializer` classes
for input validation. Cross-tenant + nonexistent lookups both
return 404 (identical shape, no existence leak — same discipline
as M2.6). `authored_by` / `uploaded_by` derive from
`request.user` — client-supplied attribution ignored.

If any money field (`estimated_cost`) appears in a JSON
response, it uses the M2.6 `_money_str` helper pattern (fixed
two-decimal-place string) to preserve Decimal precision through
JavaScript.

**Tests.** ~70 focused tests: full permission matrix per endpoint
(unauth / wrong-role / wrong-tenant / correct owner / correct
sales_manager — five to six cases each), full read scenarios
(no report / draft / complete / draft-with-findings /
complete-with-findings-and-photos), full write scenarios per
endpoint including negative cases (invalid category, invalid
severity, editing a complete report → 400, cross-tenant lookup
→ 404, PUT/PATCH/DELETE on immutable routes → 405), security
verification (no condition-report keywords on `/vehicles/<id>/`,
`/salespeople/`, `/onboarding/profile/` GET;
`DEFAULT_PERMISSION_CLASSES` remains unset).

**Boundary.** Test baseline: ~1,913 → ~1,983 pass. No new
migrations. No frontend.

### Increment 7 (M3.7) — Operator condition-report UI

**Scope.** Frontend surface per §1.6:
- Route registration in `main.tsx`:
  `/dealer-ai-inventory/:stock/condition-report` inside
  `<RequireAuth>`.
- `frontend/src/pages/VehicleConditionReportPage.tsx`.
- Ten typed `lib/api.ts` helpers via `authFetch`.
- "Condition report" button on operator inventory cards (not on
  public `/showroom`).
- Draft-vs-complete UI states (edit affordances on draft; read-
  only "signed document" view on complete).
- Role-gated write forms via
  `useAuth().hasRole('sales_manager') ||
  hasRole('dealer_owner')` — belt on top of server-side 403.
- Distinct 401/403/404 UX (mirroring M2.7's ErrorPanel
  pattern).
- Direct browser-to-S3 upload flow (request URL → PUT file →
  POST metadata).

**Verification.** `npx tsc --noEmit` clean, `npx vite build`
clean (same pre-existing chunk-size warning as M2.7,
unchanged), route registered + smoked via curl (200 on the SPA
fallback). Component-test framework NOT introduced (no
Vitest / Jest / RTL — same discipline as M2.7). Playwright
staged but not configured. Manual browser smoke deferred to
operator first-live-use if the shipping environment cannot
drive an interactive browser (honesty over false completion).

**Boundary.** Test baseline unchanged (frontend has no test
runner). Backend baseline: ~1,983 (M3.6) still passing.

### Increment 8 (M3.8) — Milestone verification + closeout

**Scope.**
- Full §3 compatibility sweep with evidence recorded inline
  (mirror the SESSION_054 / SESSION_044 pattern — every checklist
  item cited to a test class, code location, or runtime probe).
- `docs/CAPABILITY_MATRIX.md` new §7d "Structured condition
  report" enumerating shipped surface (mirroring §7c's
  vehicle-investment-ledger table).
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3
  paragraph updated with shipped date + retrospective link.
- `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` written (mirror
  M2 retrospective's §1–§8 shape).
- Frontmatter of THIS file updated: `status: shipped`,
  `shipped_at_session: SESSION_XXX`, `shipped_over` list.
- `00-START-NEXT-SESSION.md` overwritten with Milestone 4
  planning-pass priority.

**Runtime smoke against a live backend.** Same discipline as
SESSION_054 M2.8: bring up Django + Vite, authenticate as
`smoke_owner` (dealer_owner), create a draft ConditionReport
via curl, add findings, request an upload URL (may need to
skip real S3 if the local env has no bucket configured — text-
only smoke sufficient for the pathway lock), complete the
report, verify GET returns `status: "complete"` with signed
read URLs where applicable.

**Boundary.** Documentation session; no code changes. Test
baseline unchanged from M3.7.

---

## 8. Related documents

- `docs/PROJECT_RULES.md` — governance layer.
- `docs/DOC_GOVERNANCE.md` — documentation rules.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3 — scope
  contract.
- `docs/roadmap/AUTHENTICATION_MODEL.md` — the auth substrate
  every condition-report endpoint inherits.
- `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` — the lessons M3
  inherits (§6 in particular; §7 for the remaining deferrals M3
  inherits or addresses).
- `docs/roadmap/MILESTONE_2_PLANNING.md` — the planning-artifact
  template this doc mirrors (especially §3 annotated
  compatibility checklist shape, §5 deferrals table shape, and
  §7.b eight-increment shape).
- `docs/BUSINESS_DOMAIN_MAP.md` — business-shape reference,
  especially §4.2 Recon department and §5.1 Vehicle.
- `docs/CAPABILITY_MATRIX.md` — what the software does today
  (baseline against which M3's compatibility invariants hold);
  §7c ledger surface stays untouched by M3.
- `docs/research/RECON_MAPPING.md` — the primary business-truth
  source for M3 (§2 condition assessment, §2.2 severity, §2.4
  the condition report document, §2.5 photos, §2.6 what AI is
  never allowed to do, §2.7 what AI IS allowed, §3 recon
  planning, §12 front-line-ready decision, §13.1 warranty
  exposure, §14 pain points).
- `docs/research/VEHICLE_CENTRIC_PIVOT.md` — architectural plan
  for the whole vehicle-centric pivot (Phase 2 is M3; "AI role:
  NONE yet" is the load-bearing invariant).
- `docs/research/INDEPENDENT_DEALER_PIVOT.md` — the SESSION_030+
  indie-persona pivot the recon workflow sits inside.
- `00-START-NEXT-SESSION.md` — the session priority that
  motivates this planning pass.

---

*End of Milestone 3 planning pass.*
