---
title: "Milestone 3 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-01
sessions: SESSION_055 → SESSION_064
milestone: 3
milestone_name: "Structured condition report"
related:
  - docs/roadmap/MILESTONE_3_PLANNING.md
  - docs/roadmap/MILESTONE_2_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 3
---

# Milestone 3 — Retrospective

Written at Milestone 3 close (SESSION_064). Records what was
planned, what shipped, what deviated and why, and the lessons
that should shape Milestone 4 and beyond. Mirrors the
`MILESTONE_1_RETROSPECTIVE.md` /
`MILESTONE_2_RETROSPECTIVE.md` structure with a small adjustment
to §5 and §8 per the SESSION_064 spec.

## 1. Planned scope

`MILESTONE_3_PLANNING.md` at SESSION_055 defined the milestone
as answering six operational questions from the research corpus
(RECON §2.1 / §2.2 / §2.4 / §2.5 / §2.6 / §3.1 / §12.1 / §12.2
/ §13.1): *what defects were found? how severe? who inspected?
what does each finding look like? what estimated cost? is the
report finished?*

§1 followed with seven design-memo entries — one per subsystem:

- §1.1 `ConditionReport` (many-per-Vehicle, draft/complete
  lifecycle, immutable-once-complete).
- §1.2 `ConditionFinding` (twelve categories, four severities,
  `estimated_cost` documentation-only, no VehicleCost integration).
- §1.3 `Vehicle` read-model extension (two `@property` accessors).
- §1.4 Storage story (S3-compatible + CDN).
- §1.5 `ConditionFindingPhoto` (many-per-Finding, storage-agnostic
  identity later refined to UUID at M3.1).
- §1.6 Operator condition-report UI surface.
- §1.7 What M3 enables for future milestones (M4 recon automation,
  M5 lifecycle gating, M8 operational intelligence, M11+
  warranty-defense provenance).

§2 enumerated 18 existing surfaces the milestone touched with
required work. §3 defined the compatibility checklist. §5.a
resolved the load-bearing storage-story decision (Option A —
storage abstraction ships as its own increment M3.4 BEFORE the
photo model attaches to it in M3.5). §7 sequenced eight
increments, one per session.

**Original §7 sequencing (M3.1 → M3.8) shipped verbatim in
increment identity**, with one in-flight split (M3.6 into
M3.6A + M3.6B — see §3 below).

## 2. What actually shipped

Every §3 compatibility item verified true; details in the
annotated checklist at `MILESTONE_3_PLANNING.md` §3.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M3.0 planning | 055 | Full `MILESTONE_3_PLANNING.md` (8 sections; load-bearing storage decision resolved as Option A) | `872f8a0` |
| M3.1 core models | 056 | `ConditionReport` + `ConditionFinding` + `ConditionFindingPhoto` models + migration `0015` + admin + 4 module-level enum constants + tenancy-carrier registration 6→9 + 60 focused tests. Reviewed planning-doc refinement (§1.5 UUID public_id added; storage_key clarified as internal locator; photo rows represent attached objects, never upload intentions) | `2e89913` |
| M3.2 service layer | 057 | `services/condition_report.py` — 7 public functions + `CrossTenantConditionReportError` + `ConditionReportImmutableError` + 61 focused service tests. Reviewed refinement: `dealership=` added to every function (tightens planning contract; uniform security posture) | `0c98f2e` |
| M3.3 Vehicle read-model | 058 | 2 `@property` accessors on `Vehicle` (function-local import mirrors M2.3 `ledger_totals` pattern) + 20 focused tests locking delegation + tenant isolation + `assertNumQueries(1)` + no-caching contract | `c736d03` |
| M3.4 storage abstraction | 059 | `services/photo_storage.py` (~530 lines) with `UploadTarget` + `LOCAL_UPLOAD_URL_MARKER` + `LOCAL_READ_URL_MARKER` + 4 domain errors + 46 focused tests (no `moto` — botocore stubs). Dedicated `STORAGES["condition_photos"]` alias (default alias untouched). Presigned PUT with content-type binding; size verification deferred to M3.5 HEAD. `django-storages[s3]==1.14.6` + `httpx<0.28` transitive pin added. Compat patch: 4 M1/M2 test methods migrated `content_type="application/json"` → `format="json"` (latent DRF bug surfaced by pip install; verified reproducible at pristine M3.3 close) | `3dd56f7` |
| M3.5 photo workflow | 060 | Extended service module with 3 photo functions (`request_photo_upload`, `attach_photo`, `delete_photo`) + 3 domain errors (`PhotoNotYetUploadedError`, `PhotoMetadataMismatchError`, `PhotoAlreadyAttachedError`). Extended storage module with 5 primitives (`ObjectMetadata`, `get_object_metadata`, `parse_canonical_key`, `delete_object`, `store_local_upload`). Five-verification attach path; storage-first delete strategy. 58 focused tests. Zero `boto3` / `storages` imports in condition_report.py | `5ebdc15` |
| M3.6A core admin API | 061 | 6 endpoints (GET latest, POST create, POST complete, POST add-finding, shared PATCH/DELETE finding view) + 3 request serializers + 3 dict-builder projections + 3 lookup helpers + 69 focused tests (permission matrix × 6 endpoints × 5 outcomes + business flow + cross-tenant + no-storage_key-leakage + public-surface security). M3.6 SPLIT into A/B per scope-discipline pushback | `f80a6d1` |
| M3.6B photo API | 062 | 4 endpoints (request-upload, attach, delete, local-mode receiver) + 2 request serializers + 1 photo lookup helper + 1 upload-target projection + 57 focused tests. Local receiver returns 404 in S3 mode. `storage_key` in response ONLY on request-upload (locked by 5 negative tests everywhere else) | `e90af35` |
| M3.7 operator UI | 063 | Route `/dealer-ai-inventory/:stock/condition-report` inside `<RequireAuth>` + `VehicleConditionReportPage.tsx` (~506 lines) + 7 extracted components (`SeverityBadge`, `CompletionBanner`, `PhotoUploadButton`, `PhotoGallery`, `FindingCard`, `AddFindingForm`, `CreateReportForm`) + 10 typed `lib/api.ts` helpers + 2 new `authFetch` helpers (`authPatchJSON`, `authDelete`) + inventory-card button. Findings grouped by CATEGORY then severity. Zero backend changes. Frontend verification only (browser walkthrough deferred to operator first-live-use) | `8e9a5b2` |
| M3.8 closeout | 064 | §3 sweep with inline evidence + this retrospective + `CAPABILITY_MATRIX.md` update + `IMPLEMENTATION_ROADMAP.md` flip. Zero code changes | (this session) |

**Test baseline evolution.** M2 close 1,753 → 1,813 (M3.1)
→ 1,874 (M3.2) → 1,894 (M3.3) → 1,940 (M3.4) → 1,998 (M3.5)
→ 2,067 (M3.6A) → 2,124 (M3.6B) → 2,124 (M3.7 — frontend
only) → **2,124 (M3.8 unchanged)**. Delta: **+371 tests, zero
regressions.** No test suppressed with `@skip` to make the
baseline pass. Frontend `npx tsc --noEmit` clean; `npx vite
build` clean (same pre-existing 552KB chunk warning from M2.7).

## 3. Sequencing refinements

Four material refinements from the SESSION_055 plan. Each was
course-corrected in-flight based on user brief guidance.

Clearly distinguishing planned vs executed:

1. **Planning-doc refinement at M3.1: UUID `public_id` as
   durable external identity (SESSION_056).** *Planned:* §1.5
   originally used `storage_key` (the S3 object key) as both the
   internal storage locator AND the public identity. *Executed:*
   added `public_id` (UUIDField, `default=uuid.uuid4`, unique,
   editable=False) as the durable external identity;
   `storage_key` retained as the internal storage locator only.
   Rationale: conflates two lifecycles — storage keys change on
   provider migration, rekeying, or CDN reconfiguration; the
   durable public identity should survive those changes. Also
   opens the door for a future non-finding photo parent
   (M6 marketing gallery) to reuse the same identity scheme.
   Reviewed by user at SESSION_056 top; §1.5 amended narrowly
   (2 new design notes + 1 field addition + §3 checklist row
   update); no other planning section rewritten.

2. **`dealership=` on every service function at M3.2
   (SESSION_057).** *Planned:* `MILESTONE_3_PLANNING.md` §7 M3.2
   listed `dealership=` on `create_report` and the two
   `latest_*` accessors — omitted from `complete_report`,
   `add_finding`, `update_finding`, `delete_finding`.
   *Executed:* every one of the seven public functions takes
   `dealership=` explicitly. Rationale: uniform security posture
   — every call site must state its tenant intent; the service
   refuses to touch a report or finding whose denormalized
   `dealership` disagrees. Tightening not divergence; no
   user-visible surface existed yet (M3.6 was still ahead).

3. **Storage-first delete strategy at M3.5 (SESSION_060).**
   *Planned:* the original M3.5 planning entry said "removes
   both S3 object and metadata row (best-effort delete on S3;
   metadata row is the source of truth)." *Executed:* reversed
   the order — storage delete FIRST; already-missing =
   idempotent success; real provider failure = **retain the DB
   row and raise `ObjectStorageError`**. Only after storage
   succeeds does the row get dropped. Rationale: fails in the
   safer direction — never silently orphans a storage object.
   The row is the ONLY cleanup reference for the storage object;
   deleting it first and then getting a storage failure leaves
   no way to retry the cleanup.

4. **M3.6 split into M3.6A + M3.6B (SESSION_061).** *Planned:*
   single-session §7 M3.6 with 10 endpoints (6 core report + 3
   photo + 1 local receiver) + full permission matrix. *Executed:*
   scope-discipline pushback recognized that shipping all 10 in
   one session would produce ~110 tests with meaningful
   verification overhead. Split: M3.6A ships 6 core endpoints
   (SESSION_061, 69 tests); M3.6B ships 4 photo endpoints
   (SESSION_062, 57 tests). Same governance / permission
   composition / error mapping across both halves. `§7 M3.6` in
   the planning doc now carries both A and B annotations.

**In addition, three provider-neutral tightenings landed inside
M3.4 that were not called out in the original planning but which
became load-bearing for M3.5:**

- **`STORAGES` dict replaces legacy `DEFAULT_FILE_STORAGE`.**
  Django 5.0.6 (already installed) supports the modern
  `STORAGES` dict as the preferred configuration. Legacy
  `DEFAULT_FILE_STORAGE` still works but is being phased out.
- **Dedicated `condition_photos` alias.** Default alias
  untouched so unrelated file fields (any future `FileField`)
  never inherit condition-report storage semantics silently.
- **Server-computed canonical keys (no caller-supplied
  `storage_key`).** Closes a path-traversal seam — untrusted
  callers cannot choose keys.
- **No `moto` — botocore stubs + fake adapter via
  dependency injection.** SESSION_059 spec explicitly asked to
  evaluate whether existing tools suffice before adding a
  testing dependency; they did.

## 4. Deviations

**Accepted improvements** (tightenings that landed inside
increments, all reviewed by user first):

1. **UUID public identity for `ConditionFindingPhoto`** (M3.1)
   — see §3 above.
2. **`dealership=` on every service function** (M3.2) —
   see §3 above.
3. **`get_object_metadata` extends storage service beyond
   `object_exists`** (M3.5) — presigned PUT cannot enforce
   upload size; a Boolean HEAD is inadequate for
   post-upload verification. Extended M3.4 with
   `ObjectMetadata` dataclass returning `content_type` +
   `size_bytes` + `exists`. `attach_photo` HEAD-verifies both
   fields against client-declared values before persisting.
4. **Duplicate `storage_key` → predictable domain error**
   (M3.5) — pre-save `.exists()` check raises
   `PhotoAlreadyAttachedError`. Django's `full_clean()` would
   otherwise surface duplicate keys as `ValidationError` from
   `validate_unique`, which is not a stable API contract.
5. **Local upload receiver returns 404 (not 501) in S3 mode**
   (M3.6B) — SESSION_062 spec: "avoid advertising a dev-only
   transport surface." Production callers should not know the
   local-mode endpoint exists.
6. **M3.6 A/B split** (M3.6) — see §3 above.

**True compromises** (deferrals accepted with explicit
rationale, not silent trade-offs):

1. **Upload-intent binding is not persistent.** Presigned
   upload URLs authorize an upload but persist no intent
   record. A malicious client with a valid canonical key
   generated for finding A could attempt to attach it to
   finding B in the same tenant. Mitigations (all shipped):
   attach requires the finding-specific URL path; key
   namespace must match caller's dealership; the attach path
   HEAD-verifies actual object metadata against declared;
   `storage_key` is unique at schema. **This is an accepted
   compromise per SESSION_060 spec** — persistent
   `UploadIntent` model deferred unless implementation
   evidence proves it is required. **No `UploadIntent` model
   in M3.**
2. **Storage-first delete is not fully transactional** — the
   DB row could be deleted after storage delete succeeds but
   before the transaction commits. Fails in the safer
   direction (any partial failure leaves both sides
   consistent or leaves the row present pointing at an
   already-missing object, which the next delete handles
   idempotently). No outbox / queue in v1.
3. **`assertNumQueries` not locked on the read-latest
   endpoint.** M3.3 property accessors have `assertNumQueries(1)`
   coverage; M3.6A `admin_condition_report_latest` does not.
   The projection uses `select_related` + nested
   `prefetch_related` for the findings→photos chain, so no
   N+1, but a future edit could regress without a test
   catching it. Deferred to a targeted query-hardening
   session.
4. **No frontend component-test framework.** M2.7 established
   the discipline (no Vitest / Jest / RTL). M3.7 inherited
   verbatim. Component rendering is verified only through
   `tsc --noEmit` + `vite build` structural checks + the
   deferred operator browser walkthrough.
5. **`httpx<0.28` transitive pin + 4 test-method compat
   patches** (M3.4) — latent bugs surfaced by the pip install
   that installed `django-storages`. Fixed test-only (no
   production behavior change); 3 companion 400-expected
   tests in `test_salesperson_and_assignment.py` left as
   deferred test-hardening work (they pass under both the
   buggy and correct body shapes because the endpoint returns
   400 either way).

## 5. Compatibility

Every §3 checklist row verified true at SESSION_064 with
evidence citations in `MILESTONE_3_PLANNING.md` §3. Summary
(details in that document):

- **M1 tenancy substrate unchanged.** `Dealership` model,
  migration `0007`, `get_default_dealership`,
  `get_current_dealership`, `get_active_membership` all
  byte-for-byte unchanged. `_TENANT_CARRIER_MODEL_NAMES`
  extended 6→9 additively (no removals, no re-orderings, no
  signature changes on the pre_save handler).
- **M1 auth unchanged.** `DEFAULT_PERMISSION_CLASSES`
  remains unset (locked by test). `SessionAuthentication` +
  `TokenAuthentication` unchanged. `/auth/*` endpoints
  unchanged. CSRF enforcement unchanged.
- **M1 · 4D + M2.6 permissions unchanged.**
  `IsSalesManagerOrOwnerAtActiveDealership` reused verbatim
  on all 10 new M3.6A/B endpoints.
- **M2 ledger substrate unchanged.**
  `services/vehicle_ledger.py` byte-for-byte unchanged (git
  log confirms zero commits touching the file since
  `872f8a0` M3.0). `Vehicle.ledger_totals`,
  `VehicleCost` immutability, `total_investment` semantic
  contract, M2.5 `acquisition_price` scrub, M2.4 accrual
  command, M2.6 admin ledger endpoints, M2.7 operator ledger
  UI all unchanged. `ConditionFinding.estimated_cost` NEVER
  posts to `VehicleCost` — locked by three separate test
  classes across model / service / endpoint layers.
- **Safety pipeline unchanged.** `services/llm_safety.py`
  untouched. All 8 pre-LLM guards + all post-LLM scrubs
  including M2.5 unchanged. No new scrub in M3 (condition
  reports never enter customer chat context).
- **Public showroom unchanged.** `PublicShowroomPage.tsx`,
  `DealerAIDemo.tsx`, `EmbedAssistantPage.tsx`,
  `PublicAssistantPage.tsx`, `DealershipHomePage.tsx` all
  untouched. Public `salespeople-list` response contains no
  condition-report keywords — locked by
  `test_admin_condition_report.PublicSurfacesNeverExposeConditionReports`.

## 6. Lessons

Durable engineering lessons — written for future contributors
rather than milestone-specific commentary.

1. **Increment discipline pays for itself in verification
   clarity.** The M3.6 A/B split (SESSION_061) is the
   clearest example this milestone: shipping 10 endpoints
   with ~110 tests in one session would have made the
   permission-matrix + business-flow + error-mapping +
   security tests hard to reason about as one unit.
   Splitting into 6 endpoints (69 tests) + 4 endpoints
   (57 tests) meant each half was independently verifiable
   with a focused mental model. The cost of an extra session
   was recovered several times over in review clarity.

2. **Backend-first architecture; frontend never owns business
   rules.** By the time M3.7 shipped, the frontend page was
   a thin orchestrator (~506 lines) around 7 small
   presentation components. Every business decision —
   category vocabulary, severity ordering, edit permission,
   completion transition, upload workflow — lived on the
   backend. The UI could not accidentally invent a new
   severity, skip HEAD verification, or authorize an edit
   the server would refuse. When the M3.7 spec said
   "estimated_cost as 2-decimal string, never summed," the
   UI implementation was trivial because the backend already
   sent the string and never surfaced totals.

3. **Provider-neutral boundaries make later migration
   painless.** `services/photo_storage.py` shipped with a
   `_PhotoStorageAdapter` Protocol and two adapters
   (`_LocalAdapter`, `_S3Adapter`). The condition-report
   service imports the public API but never imports `boto3`
   or `django-storages`. If we swap S3 for R2, MinIO, or
   Cloudflare Images, only `_S3Adapter` (or a new adapter)
   changes — no test-file rewrite, no view-layer edits.
   Verified by `grep -n "^import boto3\|^from boto3\|^import
   storages" backend/dealer_ai/services/condition_report.py`
   returning empty.

4. **Service ownership: one authoritative write path per
   operation.** Every M3 endpoint (10 of them) delegates to
   the M3.2/M3.5 service. No endpoint bypasses to
   `ConditionReport.objects.create` or
   `ConditionFinding.objects.create`. This preserves the
   cross-tenant `full_clean()` invariant + the immutability
   guards + the estimated-cost-never-touches-VehicleCost
   invariant across every future caller (M4 API, seed
   scripts, management commands). The M2.6 pattern proved
   this; M3.6 A/B inherited it verbatim.

5. **Local vs production parity for storage.** The local
   adapter uses filesystem via Django's `storages` framework
   under `MEDIA_ROOT/condition-photos`, plus a per-key
   `.content-type` sidecar file to round-trip MIME (which
   FileSystemStorage doesn't record on disk). The local
   upload receiver returns 404 in S3 mode — production
   never advertises the dev surface. The client-side
   `uploadPhotoBytes` branches on `LOCAL_UPLOAD_URL_MARKER`
   prefix, so the same three-step workflow (request-upload
   → upload → attach) shape works in both environments.
   **The M3.4→M3.5→M3.6→M3.7 sequence proved that a
   provider-neutral boundary can preserve parity across dev
   and production without forking the workflow.**

6. **Honest verification reporting over false completion.**
   The M3.7 12-step browser walkthrough was explicitly
   documented as operator-verification-pending in the
   SESSION_063 handoff — not silently ticked as complete.
   The same discipline appears in the §3 checklist entry
   for "advisor-role user navigating to the URL sees the
   403 UI": the shipped behavior is "read-only presentation
   for non-write roles" not "full-page 403," and the
   checklist annotation explains that discrepancy rather
   than pretending the checkbox was met. **When a
   verification cannot honestly be completed, record it as
   pending; do not tick the box.**

7. **Storage-first deletion (fail in the safer direction).**
   The original M3.5 plan said "best-effort delete on S3;
   metadata row is the source of truth" — which would have
   deleted the DB row first and hoped the S3 delete followed.
   The reviewed refinement reversed the order: storage first,
   then row. A real provider failure now retains the row so
   the operator can retry; the storage object is never
   silently orphaned. **When two systems can't be
   transactional, order the operations so that partial
   failure leaves the system recoverable.**

8. **Document implementation refinements immediately, not at
   milestone close.** Every M3 SHIPPED annotation in
   `MILESTONE_3_PLANNING.md` §7 records the refinements
   as they landed (M3.1 UUID public_id, M3.2 `dealership=`,
   M3.4 six refinements, M3.5 six refinements, M3.6 A/B
   split, M3.6B storage_key exception rules). By SESSION_064
   this retrospective is a synthesis, not an archaeology
   exercise. **The retro's cost is proportional to how well
   the per-session handoffs captured the refinements.**

9. **Compat patches surfaced by dependency updates are
   legitimate but must be honest.** M3.4's `pip install`
   surfaced two latent bugs (`openai==1.30.5` × `httpx>=0.28`
   incompatibility; 4 M1/M2 tests using
   `content_type="application/json"` with dict data that DRF's
   `APIRequestFactory._encode_data` refuses to serialize).
   Fixed with `httpx<0.28` pin + 4 test-method migrations to
   `format="json"`. **Both patches documented explicitly in
   the SESSION_059 handoff + planning §7 M3.4 annotation** —
   surfaced to user rather than absorbed silently.

10. **Avoid architectural drift by never generalizing without
    a second proven consumer.** SESSION_060 spec said "M3.5
    should ship only ConditionFindingPhoto behavior. Do not
    generalize into a universal attachment framework without
    a second proven consumer." Shipped exactly that. When M6
    photography needs a similar workflow, the abstraction
    will emerge from real evidence — not a speculative
    "reusable framework" designed against one caller.

## 7. Remaining deferrals

Items intentionally deferred. **These are not feature
requests being reclassified as deferrals** — each has an
explicit rationale.

1. **Operator browser walkthrough for M3.7 (12 steps).** The
   SESSION_063 spec's manual verification steps 1-12 (open
   inventory → create report → add findings → upload →
   attach → refresh → verify persistence → complete → verify
   locked state → verify advisor read-only → verify anonymous
   redirect) remain **operator first-live-use**. This session
   had no interactive browser access; automation of these
   steps via Playwright was deferred by the M3.7 spec itself
   ("Manual browser smoke deferred to operator first-live-use
   if the shipping environment cannot drive an interactive
   browser"). If the walkthrough surfaces UI friction,
   record in `DEFERRED_IDEAS.md` (create at that moment).

2. **Three ambiguous 400-expected tests in
   `test_salesperson_and_assignment.py`** (surfaced at
   SESSION_059 compat patch). Passing under both buggy
   (`content_type="application/json"` with dict data → dict
   repr as body → endpoint returns 400 for JSON parse error)
   and correct (`format="json"` → JSON body → endpoint
   returns 400 for business reason) request shapes.
   Deferred test-hardening work — passes now but tests the
   wrong thing.

3. **Persistent `UploadIntent` binding.** M3 shipped
   attach-side verification (canonical key shape +
   dealership namespace + HEAD metadata match); persistent
   pre-upload intent record deferred. Only revisit if
   implementation evidence surfaces a case that attach-side
   verification cannot address.

4. **`assertNumQueries` locked on
   `admin_condition_report_latest` endpoint.** Read cost is
   4 queries baseline (vehicle + report + findings prefetch +
   photos prefetch) plus zero-DB signed URL generation. No
   N+1 currently, but a future edit could regress without a
   test catching it. Targeted query-hardening pass in a
   later session.

5. **Frontend component-test framework.** M2.7 established
   "no Vitest / Jest / RTL." M3.7 inherited. `tsc --noEmit`
   + `vite build` are the automated frontend verification;
   component behavior verification remains the operator
   browser walkthrough.

## 8. Milestone 4 bootstrap

Milestone 4 is **Recon Automation**. Reads the M3 substrate to
draft work orders, cost projections, and vendor communications
from the `ConditionFinding` records M3 established. Nothing in
this section is a M4 commitment — SESSION_065 (M4.0 planning
pass) is where the actual M4 planning artifact gets drafted.

**Engineering context M4 should inherit:**

- **`ConditionFinding` is the seam.** M3.2 documented +
  M3.7 preserved that `estimated_cost` is documentation only
  and never posts to `VehicleCost`. M4 owns the flow
  finding → recon plan (three-tier RECON §3.1 framework) →
  work order → estimate `VehicleCost(is_estimate=True)` on
  order creation → actual `VehicleCost(is_estimate=False)` on
  complete. That flow requires the finding row's
  `estimated_cost` to be read but never modified.
- **Recon-manager role does NOT exist yet.** M3 deliberately
  did not add a `recon_manager` permission class (M2 §5
  deferral acknowledged in the M3 planning). M4 is the first
  milestone that needs it (vendor-facing users who are not
  sales managers).
- **`services/condition_report.py::latest_completed_condition_report`
  is the accessor M4 recon-plan drafting reads.** M3.3
  shipped this on `Vehicle` as a `@property` delegator.
- **AI role: M4 first surfaces it.** RECON §2.6 prohibits
  AI from authoring findings; M4 needs to draft vendor
  emails ("per our inspection by
  [inspector_name] on [inspected_at], we found…"). New
  post-LLM scrub for vendor-email drafting will need to
  land alongside — the M4 planning pass should include it
  as a first-class subsystem.
- **Photo storage abstraction is production-ready.** M3.4's
  `_S3Adapter` is fully wired; production deployment can
  configure `AWS_*` env vars and the storage swap is
  transparent. M4 (or M5) may be the first milestone that
  actually goes live to prod (M3 was in-store workflow only
  per RECON §12.2 sign-off authority).
- **The 371 M3 tests provide regression coverage for the
  entire condition-report substrate.** M4 additions should
  extend this coverage rather than replace it. Domain-error
  classes (`CrossTenantConditionReportError`,
  `ConditionReportImmutableError`, `PhotoNotYetUploadedError`,
  etc.) are stable public contracts.

**Roadmap position.** After M3.8, `milestone_3_status:
shipped` and `next_milestone: 4` in
`IMPLEMENTATION_ROADMAP.md`. `MILESTONE_4_PLANNING.md` does
not yet exist — SESSION_065 (M4.0) creates it.
