---
title: "Milestone 6 — Implementation-Planning Pass"
status: shipped
type: planning-artifact
generated: 2026-08-01
generated_at_session: SESSION_081 (post-M5-closeout)
shipped_at_session: SESSION_087 (M6.6 closeout)
milestone: 6
milestone_name: "Photography + listing generation"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_5_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_5_PLANNING.md
  - docs/roadmap/MILESTONE_4_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/VEHICLE_CENTRIC_PIVOT.md
  - docs/research/INVENTORY_ACQUISITION_MAPPING.md
  - docs/research/RECON_MAPPING.md
---

# Milestone 6 — Implementation-Planning Pass

**Purpose.** Acceptance contract for Milestone 6
(Photography + listing generation). Every implementation
increment cites back here for scope, invariants, and
refinement provenance. Mirrors the shape M3 / M4 / M5
planning docs proved out.

**Business objective (from
`IMPLEMENTATION_ROADMAP.md` §Milestone 6).** Address the
"photo management + cross-platform listing maintenance"
pain by giving vehicles a structured photo gallery,
generating listing copy with the same drafting-with-scrub
pattern already shipped (M4.5), and enabling the M5.3 /
M5.6 lifecycle transitions that M5 left as **structured
unmet prerequisites** (`photography → listing` via a
photo-count predicate; `listing → frontline` via a
`VehicleListing.published` predicate).

**Zero implementation this session.** Planning artifact
only. SESSION_082 opens M6.1.

---

## 0. Engineering practices to preserve from M2–M5

Synthesized from the four prior retrospectives. Every
practice below is a load-bearing constraint on M6.

1. **Increment discipline** (M2/M3/M4/M5 §6 lesson 1).
   Each M6 sub-increment ships independently verifiable
   in one session. If a proposed increment cannot be
   described in one sentence with one locked invariant,
   split it.

2. **Backend-first architecture; frontend never owns
   business rules** (M4/M5 §6 lesson 2). M6 photo upload
   flows write to a service module; the frontend is a
   thin orchestrator. Every write affordance is gated
   server-side.

3. **Provider-neutral boundaries** (M4/M5 §6 lesson 3).
   Photo storage abstracted behind a service (S3 /
   local / dev-mode substitutes). Listing-copy AI drafts
   route through the shared LLM factory + safety stack.
   No provider-specific coupling in the model or the
   endpoint layer.

4. **Service ownership — one authoritative write path
   per operation** (M4/M5 §6 lesson 4). Every M6.4
   endpoint delegates to a service function; no endpoint
   calls `VehiclePhoto.objects.create()` or
   `VehicleListing.objects.update()` directly.

5. **Local vs production parity** (M4/M5 §6 lesson 5).
   The photo storage layer has a real S3 backend + a
   local-mode substitute. The LLM drafting path uses
   the existing provider factory (already mocked in
   tests).

6. **Honest verification reporting** (M4/M5 §6 lesson
   6). If M6 introduces a listing "publish" that
   doesn't actually push to third-party marketplaces
   yet, the shipped surface must NOT claim it did. M6
   ships **publish-locally + surface-in-showroom**; the
   cross-platform push is deferred.

7. **Storage-first / safer-direction deletion** (M3/M4/M5
   §6 lesson 7). Photo deletes are safer-direction
   first — mark as deleted, then physically remove after
   a grace period (or never, per operator policy).

8. **Load-bearing decisions get user review BEFORE
   code** (M5 §6 lesson 8). Every M6
   `[NEEDS-DECISION-BEFORE-M6.1]` item requires user
   confirmation at the top of SESSION_082 before
   implementation lands.

9. **Distinct domain errors → distinct HTTP status
   codes** (M5 §6 lesson 9). M6 shipping any new domain
   error should follow the M5 discipline: each error
   class → one HTTP status → one remediation path.

10. **Read-model properties are pure reads** (M5 §6
    lesson 10). Any new `Vehicle` @property M6 adds
    (e.g. `Vehicle.primary_photo`,
    `Vehicle.published_listing`) must be side-effect-free.

---

## 1. Design memo

Rule from M4/M5: start with the operational questions,
not the models.

### 1.0 The operational questions Milestone 6 must answer

Nine questions synthesized from
`INVENTORY_ACQUISITION_MAPPING.md` pains #8 + #9 +
`RECON_MAPPING.md` §photography + §listing prep + VCP
Phase 5. These are the acceptance test for whether the
milestone shipped the right thing.

| # | Question | Research citation |
|---|---|---|
| 1 | **What photos exist for this vehicle?** | INVENTORY §pain #9 photo management |
| 2 | **What is the primary / hero photo?** | Same |
| 3 | **How many "listing-ready" photos does this vehicle have right now?** (drives the M5.3 `photography → listing` predicate) | Same + `MILESTONE_5_PLANNING.md` §5.h |
| 4 | **Which photos are marked for deletion (safer-direction) but not yet physically removed?** | M6 §7 storage-first deletion inheritance from M3.5 |
| 5 | **What listing copy has the AI drafted for this vehicle?** | INVENTORY §pain #8 listing maintenance |
| 6 | **Has the operator approved and published the listing?** (drives the M5.3 `listing → frontline` predicate) | Same + `MILESTONE_5_PLANNING.md` §5.h |
| 7 | **When was the listing published?** (aging seam for M8) | INVENTORY §pain #8 |
| 8 | **What is the truthful "not yet listed" language when a customer asks about a vehicle whose listing isn't yet published?** | §5.i M5 deferral — full truthful-language refactor |
| 9 | **How does the operator SEE the photo gallery + listing draft in the UI?** | M5.6 operator-UI precedent |

Questions 1–4 belong to the **`VehiclePhoto`** subsystem
(§1.1). Question 5–7 belong to the **`VehicleListing`**
subsystem (§1.2). Question 8 belongs to the **customer-
chat language refactor** (§1.5 — the M5.5 deferred item).
Question 9 belongs to the **frontend UI** subsystem
(§1.6). And the two M5.3 stubs
(`photography → listing`, `listing → frontline`) become
real rules that consume the M6 predicates (§1.7).

**Questions Milestone 6 does NOT answer** (deliberate,
per `IMPLEMENTATION_ROADMAP.md` §Milestone 6 scope
boundary):

- Q: *Are photos being cross-posted to Facebook
  Marketplace / AutoTrader / Cars.com etc.?* — Milestone
  11+ (sales-side non-chat channels). M6 ships publish-
  locally + surface-in-showroom; cross-platform push is
  the next-generation integration.
- Q: *What does the AI recommend re-shooting?* (photo
  quality analytics) — Milestone 8.
- Q: *Are customers clicking through to the vehicle
  detail page?* (listing performance analytics) —
  Milestone 8.
- Q: *Can the AI edit photos (crop, brighten)?* — never;
  operator uploads what the operator uploads.

### 1.1 Photo gallery — `VehiclePhoto` (many-per-Vehicle)

- **Business questions answered.** Q1 + Q2 + Q3 + Q4.
- **Citation.** INVENTORY §pain #9 + VCP Phase 5.
- **Fields (planning shape — final in M6.1).**
  - `vehicle` (FK CASCADE — vehicle deletion removes
    the gallery).
  - `dealership` (FK NOT NULL from day one; every M6
    tenant carrier follows M1–M5 pattern).
  - `storage_key` (CharField — the S3 / local-storage
    path key; not a URL, so the storage-layer helper
    can compute signed URLs at read time).
  - `content_type` (CharField — MIME type;
    validated to `image/jpeg` | `image/png` | `image/webp`).
  - `width_px` + `height_px` (IntegerField; captured on
    upload; used for the "listing-ready" predicate).
  - `sort_order` (IntegerField default 0 — operator
    can reorder; unique-per-vehicle constraint TBD at
    §5).
  - `is_primary` (BooleanField default False — one
    per vehicle at the service layer; violation is
    a service-layer refusal, not a DB uniqueness
    constraint, so the operator's "swap primary"
    gesture is a single service call not a two-step
    delete-then-insert dance).
  - `caption` (CharField blank — operator-supplied).
  - `uploaded_by` (FK to `AUTH_USER_MODEL`, nullable
    SET_NULL — historical rows survive user deletion).
  - `uploaded_at` (auto_now_add).
  - `marked_deleted_at` (DateTimeField nullable —
    safer-direction deletion per M6 §7 lesson 7).
  - `deleted_by` (FK to `AUTH_USER_MODEL`, nullable
    SET_NULL — records the operator who initiated the
    delete).
  - `updated_at` (auto_now).
- **Extend.** New reverse relation on `Vehicle.photos`
  (via FK).
- **Leave untouched.** Nothing.

### 1.2 Listing draft + publish — `VehicleListing` (OneToOne with Vehicle)

- **Business questions answered.** Q5 + Q6 + Q7.
- **Citation.** INVENTORY §pain #8 + VCP Phase 5.
- **Fields.**
  - `vehicle` (OneToOne CASCADE).
  - `dealership` (FK NOT NULL).
  - `status` (CharField choices — TBD at §5.b:
    likely `draft` / `approved` / `published` /
    `unpublished`).
  - `title` (CharField blank).
  - `body` (TextField blank — the AI-drafted listing
    copy; scrubbed via safety stack).
  - `source_provenance` (JSONField — mirrors M4.5
    pattern; records which M2/M3/M4/M5 data seeded
    the draft).
  - `drafted_by` + `drafted_at` (draft provenance).
  - `approved_by` + `approved_at` (approval
    provenance; nullable until approved).
  - `published_by` + `published_at` (publish
    provenance; nullable until published — the M5.3
    `listing → frontline` predicate reads
    `published_at is not None`).
  - `unpublished_by` + `unpublished_at` +
    `unpublished_reason` (unpublish provenance).
  - `created_at` + `updated_at`.
- **Extend.** New `Vehicle.listing` reverse OneToOne
  accessor.
- **Leave untouched.** `Vehicle.price` still lives on
  `Vehicle` (not `VehicleListing`) — the listing body
  reflects the current price, but the price itself is
  the vehicle's identity.

### 1.3 Photo storage layer — `services/photo_storage.py`

Reuse the existing M3.4 photo storage layer if it
covers the M6 use cases. Otherwise extend with:

- `store_photo(bytes, content_type) → storage_key` —
  writes to S3 (prod) or local disk (dev/test).
- `get_photo_url(storage_key) → str` — signed URL for
  read.
- `remove_photo(storage_key) → None` — hard delete
  (used by the safer-direction reaper, NOT by the
  operator delete gesture).

### 1.4 Photo + listing services — `services/photo_gallery.py` + `services/vehicle_listing.py`

Two new service modules:

- **`services/photo_gallery.py`** — 6ish public
  functions: `upload_photo`, `set_primary`, `reorder`,
  `mark_deleted`, `restore_deleted`, `listing_ready_count`.
  Domain errors: `PhotoDeletionRefusedError` (if
  marked-deleted is the last remaining photo?),
  `PhotoStorageError`.
- **`services/vehicle_listing.py`** — 5ish public
  functions: `draft_listing` (invokes LLM via factory +
  safety stack), `approve_listing`, `publish_listing`,
  `unpublish_listing`, `regenerate_draft`. Domain
  errors: `ListingImmutableError` (analogous to M4.5
  vendor comm), `ListingScrubDroppedError` (safety
  scrub refused the AI output — mirror
  M4.5 `ReconFactScrubDroppedError`).

### 1.5 Customer-chat truthful-language refactor (M5.5 deferred)

- **Business question answered.** Q8 + M5.5 §5.i
  deferred item.
- **Citation.** `MILESTONE_5_PLANNING.md` §5.i
  SESSION_075 refined + `MILESTONE_5_RETROSPECTIVE.md`
  §4 deferrals.
- **Shape.** Locate the exact stock-specific customer-
  chat lookup path in `chat_engine.py`. When a
  customer asks about a vehicle whose lifecycle stage
  is not `frontline` OR whose listing isn't
  `published`, return the truthful copy: *"That
  vehicle is not currently available for retail."* Do
  NOT expose stage / recon details / ETA / vendor /
  expected-ready-date.
- **Alternative deferral.** If locating the exact
  path in `chat_engine.py` requires more investigation
  than fits an increment, defer AGAIN and document
  clearly.

### 1.6 Operator photo + listing UI

- **Business question answered.** Q9.
- **Citation.** M5.6 operator-UI precedent.
- **Shape.** Route
  `/dealer-ai-inventory/:stock/photos` (photo
  gallery) + route
  `/dealer-ai-inventory/:stock/listing` (listing draft
  view + approve/publish gesture). Small extracted
  components in `frontend/src/components/photos/` +
  `components/listing/`.

### 1.7 Fills the M5.3 rule stubs

- `_rule_photography_to_listing` — reads
  `Vehicle.photos.filter(marked_deleted_at=None,
  is_listing_ready=True).count() ≥ N` predicate. `N`
  is per-dealer TBD at §5.
- `_rule_listing_to_frontline` — NEW rule (M5 kept
  this manual-only). Fires when
  `Vehicle.listing.status='published' AND
  Vehicle.price > 0`.

Both rules land in `services/vehicle_lifecycle.py`
alongside the M5.3 stubs — extending the existing
composition dispatch.

---

## 2. Migration impact review

*(Skeleton — filled in at M6.1.)*

Every existing surface Milestone 6 touches, with the
concrete work required. Same shape as M4 §2 / M5 §2 (22
rows). Preview:

| # | Existing surface | Location | M6 impact |
|---|---|---|---|
| 1 | `Vehicle` model | `models.py` | Additive relationships only. New reverse `photos` + `listing`. |
| 2 | `services/vehicle_lifecycle.py` — M5.3 rule stub | `_rule_photography_to_listing` | Fill in real predicate reading `VehiclePhoto` count. |
| 3 | `services/vehicle_lifecycle.py` — new M5→M6 rule | (new) `_rule_listing_to_frontline` | New deterministic rule reading `VehicleListing.status='published'`. |
| 4 | `services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES` | Existing tuple (17 entries at M5 close) | Additive. Two new tenant carriers (`VehiclePhoto`, `VehicleListing`). 17 → 19. |
| 5 | `services/llm_safety.py` | Existing safety stack | Additive. New scrub or reuse of existing? Decide at §5. Listing copy is customer-facing marketing content — the existing scrub set likely covers most cases. |
| 6 | Public `/showroom` endpoint | `views.py` | Additive. Include primary photo in the response payload for retail-eligible + published vehicles. |
| 7 | `services/chat_engine.py` — customer-facing stock-specific lookup | Where the M5.5 §5.i deferral lives | REFACTORED to surface truthful "not currently available for retail" copy per §1.5. |
| ... | ... | ... | ... |

Row count locks at M6.1 during planning + implementation.

---

## 3. Compatibility checklist

*(Skeleton — filled in at M6.1.)*

Milestone 6 ships with this checklist verified true;
evidence recorded inline at milestone close. Same
shape as M2.8 / M3.8 / M4.9 / M5.7 established.

### Milestone 1–5 invariants Milestone 6 must not regress

- [ ] Every existing tenant-carrying model still has
  `dealership` FK NOT NULL.
- [ ] `Vehicle.is_available` unchanged (M5 §5.e Option D).
- [ ] Every M5 lifecycle transition + rule + endpoint
  unchanged in signature and behavior.
- [ ] `customer_visible_vehicles()` still filters on
  stage=frontline.
- [ ] M4 recon substrate unchanged.
- [ ] Every pre-M6 test passes at 2,754 baseline.

### New invariants Milestone 6 introduces

- [ ] `VehiclePhoto.dealership` NOT NULL from day one.
- [ ] `VehicleListing.dealership` NOT NULL from day one.
- [ ] Cross-tenant `clean()` guards on both models.
- [ ] Photo storage layer honors safer-direction
  deletion (marked_deleted_at before physical remove).
- [ ] Listing publish state is authoritative for
  `_rule_listing_to_frontline`.

---

## 4. Reusable primitives review

- **M3.4 photo storage layer** — direct reuse if
  compatible with the new `VehiclePhoto` model.
- **M4.5 LLM drafting pattern** —
  `services/vendor_comm.py` provides the shape for
  `services/vehicle_listing.py::draft_listing`
  (draft → approve → send equivalent).
- **M4.5 `invented_recon_fact` scrub** —
  `services/llm_safety.py` shows the scrub-extension
  pattern; listing copy might warrant a new scrub
  (`invented_photo_claim`?) — decide at §5.
- **M5.3 rule evaluator pattern** — two new rules
  slot into the existing composition dispatch.
- **M5.6 operator UI pattern** — two new operator
  pages mirror `VehicleLifecyclePage.tsx` shape.

---

## 5. Scope discipline + load-bearing decisions

### 5.a `[NEEDS-DECISION-BEFORE-M6.1]` — `VehicleListing` status vocabulary

**Question.** What's the state machine for
`VehicleListing.status`?

**Options.**
- **Option A — 4 states:** `draft` / `approved` /
  `published` / `unpublished`. Mirror M4 vendor comm
  shape.
- **Option B — 3 states:** `draft` / `published` /
  `unpublished`. Skip the explicit approve step for
  M6 v1; the operator approves + publishes in one
  gesture.
- **Option C — 5 states:** `draft` / `approved` /
  `published` / `unpublished` / `archived`. Adds a
  terminal archive state for old listings on sold
  vehicles.

**Recommended for user review:** **Option A** —
mirror M4.5 shape; keep the approve gesture explicit
(matches the "AI drafts, human approves, human
publishes" contract).

### 5.b `[NEEDS-DECISION-BEFORE-M6.1]` — Listing-ready photo count threshold

**Question.** How many photos count as "listing-ready"
for the `_rule_photography_to_listing` predicate?

**Options.**
- **Option A — fixed at 8** (industry-common minimum).
- **Option B — per-dealer configurable** via
  `DealerOnboardingProfile.listing_ready_photo_count`.
- **Option C — fixed at 8 for v1; per-dealer in a
  future increment.**

**Recommended for user review:** **Option C** — ship
v1 with a sensible default; add per-dealer
configurability when operator evidence surfaces need.

### 5.c `[NEEDS-DECISION-BEFORE-M6.1]` — Photo storage layer reuse

**Question.** Reuse M3.4's `services/photo_storage.py`
or fork?

**Options.**
- **Option A — extend the existing module** with a new
  `store_vehicle_photo(...)` verb.
- **Option B — new module** `services/vehicle_photo_storage.py`
  that composes the existing S3 primitive but adds
  vehicle-specific path conventions.

**Recommended for user review:** **Option A** —
reuse. The M3 photo storage layer is proven; adding a
vehicle-photo verb is additive without disturbing
condition-report photos.

### 5.d Listing-copy AI scrub

Reuse existing M4.5 `_scrub_invented_recon_fact`
pattern. Add a new scrub `_scrub_invented_photo_claim`
if listing copy fabricates features it can't verify
from `Vehicle.features[]`. Deferred to M6.4 (safety-
stack integration) implementation decision.

### 5.e Publish semantics

M6 v1 publish = "the listing is visible to customers
on the local `/showroom` endpoint." M6 does NOT push
to Facebook Marketplace / AutoTrader / etc. — that's
Milestone 11+.

### 5.f Truthful customer language integration (M5 §5.i deferral)

Full refactor lands in M6.5 (or an earlier
increment). If M6 discovers the M5 investigation was
correct — the exact `chat_engine.py` path is a
significant rewrite — defer again with an explicit
increment reserved.

---

## 6. Anchors that win on conflict

If this planning doc disagrees with:

1. `docs/PROJECT_RULES.md` — the rules win.
2. `docs/DOC_GOVERNANCE.md` — the doc governance wins.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone
   6 — the roadmap wins on scope questions.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — the auth
   model wins on identity / tenancy / permission
   questions.
5. `docs/roadmap/MILESTONE_5_RETROSPECTIVE.md` — the
   lessons win on engineering-process questions
   (especially §6 items 8, 9, 10).
6. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` §6 —
   same.
7. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 5 +
   `INVENTORY_ACQUISITION_MAPPING.md` pain #8 + #9 —
   the research wins on business-truth questions.
8. `docs/CAPABILITY_MATRIX.md` — the matrix wins on
   "what does the software actually do today?"
   questions.
9. Current source code — the code wins on same.

Planning docs are claims. Rules + research + code are
facts.

---

## 7. Increment sequencing

Six increments (mirrors M5 shape). Increment
discipline inherited from M2/M3/M4/M5 retro §6 lesson
1.

### Increment 1 (M6.1) — Core persistence

**Scope.** Two new models (`VehiclePhoto`,
`VehicleListing`) + migration `0018` + admin
registrations + module-level enum constants + cross-
tenant `clean()` guards + `_TENANT_CARRIER_MODEL_NAMES`
tuple extended 17 → 19. No service module, no
endpoints, no rules, no frontend.

**Tests.** ~35 focused model tests.

**Boundary.** Test baseline: 2,754 → ~2,789.

### Increment 2 (M6.2) — Photo storage integration

**Scope.** Extend `services/photo_storage.py` or new
`services/photo_gallery.py` with the ~6 public verbs
listed in §1.4. Reuse M3.4 photo storage primitive.
Wire the storage layer to a local-mode substitute for
tests. No AI, no LLM.

**Tests.** ~30 focused storage + gallery-service
tests.

**Boundary.** Test baseline: ~2,789 → ~2,819. No
migrations.

### Increment 3 (M6.3) — Listing draft + AI safety scrub

**Scope.** `services/vehicle_listing.py` with the ~5
public verbs listed in §1.4. Integrate with the LLM
factory + safety stack. Add
`_scrub_invented_photo_claim` (or reuse existing) if
needed. `draft_listing` invokes the LLM with the
Vehicle + Photos + M3/M4 context.

**Tests.** ~40 focused listing-service tests
(including scrub-refused paths).

**Boundary.** Test baseline: ~2,819 → ~2,859. No
migrations.

### Increment 4 (M6.4) — Deterministic rule integration

**Scope.** Fill in `_rule_photography_to_listing` (M5.3
stub) with the real photo-count predicate. Add new
`_rule_listing_to_frontline` rule reading
`VehicleListing.status='published' AND
Vehicle.price > 0`. Extend `suggest_transitions`
composition to dispatch both rules at their respective
stages.

**Tests.** ~25 focused rule tests.

**Boundary.** Test baseline: ~2,859 → ~2,884. No
migrations.

### Increment 5 (M6.5) — Admin API + operator UI + truthful customer language

**Scope.** Admin endpoints for photo CRUD + listing
draft/approve/publish. Operator UI (`/photos` +
`/listing` routes with extracted components).
**Customer-chat truthful-language refactor for
stock-specific non-frontline / non-published lookups
(§1.5 — M5.5 deferred).**

**Tests.** ~50 focused endpoint + UI + language-scrub
tests.

**Boundary.** Test baseline: ~2,884 → ~2,934. No
migrations.

### Increment 6 (M6.6) — Closeout

**Scope.** Documentation-only. §3 compatibility sweep,
retrospective, capability matrix §7g, roadmap flip,
planning frontmatter, session-start refresh,
`MILESTONE_7_PLANNING.md` per standing user directive,
commit + push.

---

## 8. Related documents

- `docs/PROJECT_RULES.md`
- `docs/DOC_GOVERNANCE.md`
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 6
- `docs/roadmap/AUTHENTICATION_MODEL.md`
- `docs/roadmap/MILESTONE_5_RETROSPECTIVE.md`
- `docs/roadmap/MILESTONE_5_PLANNING.md` (§5.h stubs +
  §5.i deferral)
- `docs/roadmap/MILESTONE_4_PLANNING.md` §1.6 (vendor
  comm draft pattern for listing-copy AI)
- `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 5
- `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
  pain #8 + pain #9
- `docs/research/RECON_MAPPING.md` §photography +
  §listing prep
- `docs/CAPABILITY_MATRIX.md` — §7d M3 condition-
  report photo storage + §7e M4 vendor-comm drafting
  patterns M6 reuses.
- Current source code — authoritative.

---

## 9. Load-bearing decisions summary — items requiring user review before M6.1

Every `[NEEDS-DECISION-BEFORE-M6.1]` in this document,
consolidated:

1. **§5.a — `VehicleListing` status vocabulary.**
   Recommended: Option A (`draft`/`approved`/
   `published`/`unpublished`). User: confirm or
   choose B/C.

2. **§5.b — Listing-ready photo count threshold.**
   Recommended: Option C (fixed at 8 for v1;
   per-dealer configurable later). User: confirm or
   choose A/B.

3. **§5.c — Photo storage layer reuse.**
   Recommended: Option A (extend M3.4 module). User:
   confirm or choose B.

Every other §5.d – §5.f decision is either **chosen**
by the planning doc (with rationale) or deferred to a
future increment (with a home cited). Decisions marked
`[NEEDS-DECISION-BEFORE-M6.1]` are the ones the user
should confirm at the top of SESSION_082 before code
lands — same discipline as M5 §9 SESSION_075 mandate.
