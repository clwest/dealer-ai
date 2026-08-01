---
state: active
date: 2026-07-31
last_session_shipped: SESSION_058
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: in-progress
next_session: SESSION_059
next_milestone: 3
next_milestone_name: "Structured condition report"
next_increment: 4
next_increment_name: "M3.4 — Storage story (S3-compatible + CDN)"
---

# Next session — SESSION_059 · Milestone 3 · Increment 4 (M3.4 — Storage story)

> **Milestone 3 · Increment 3 (M3.3) shipped at SESSION_058.**
> `Vehicle.latest_condition_report` +
> `Vehicle.latest_completed_condition_report` are live as
> `@property` delegators to the M3.2 service. 20 focused tests
> lock delegation, tenant isolation, query cost
> (`assertNumQueries(1)` when dealership prefetched), and the
> observable absence of caching. Function-local imports handle
> the models ↔ service cycle, mirroring the existing M2.3
> `ledger_totals` pattern. See
> `docs/handoffs/SESSION_058_m3_inc3_read_model.md`.
>
> **SESSION_059 opens M3.4 = the load-bearing storage
> abstraction that M3.5 will bind against.** Planning §5.a is
> the design memo M3.4 implements verbatim: `django-storages`
> dependency, env-driven `DEFAULT_FILE_STORAGE` selection
> (dev/test → `FileSystemStorage`; prod → `S3Storage`), and a
> new `services/photo_storage.py` module with the three
> functions the M3.5 upload flow will consume. No new models.
> No API. No frontend. No photo model behavior (M3.5).

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3 —
   scope boundary.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every presigned
   URL issuance function threads the tenant substrate
   through; M3.4 must NOT re-derive these decisions.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — the acceptance
   contract. §7 M3.1 + §7 M3.2 + §7 M3.3 now annotated
   SHIPPED. **§5.a — the load-bearing storage decision
   (Option A) — is the design memo M3.4 implements
   verbatim.** §7 M3.4 entry locks the sub-scope this
   session ships.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 — the
   eleven lessons inherit unchanged. Lesson 3 (one
   authoritative write path per operation) applies to the
   new `photo_storage.py` service.
7. `docs/research/RECON_MAPPING.md` §2.5 (photos in
   condition reporting — pre-existing damage documentation,
   vendor communication, insurance claims, before/after
   evidence) + §13.1 (warranty exposure — condition
   documentation is the legal record) +
   `VEHICLE_CENTRIC_PIVOT.md` "Technical debt to pay down
   FIRST" item 3 ("File storage story. S3-compatible + CDN.
   Configured via env. Before `VehiclePhoto` ships").

## What M3.4 delivers (per `MILESTONE_3_PLANNING.md` §7 M3.4)

The storage abstraction, landing BEFORE the upload flow so
M3.5 has a real dependency to bind against.

**In scope:**

- `backend/requirements.txt` — add `django-storages[s3]`
  (pulls `boto3` transitively). No version bumps on any
  existing dependency.
- `backend/dealer_kit/settings.py` — env-driven
  `DEFAULT_FILE_STORAGE` selection:
  - `AWS_STORAGE_BUCKET_NAME` present →
    `storages.backends.s3.S3Storage`.
  - Else → Django's default `FileSystemStorage` (writes
    under `MEDIA_ROOT`).
  - This preserves dev / test isolation: unset env means
    zero S3 network access from tests.
- Env-var documentation in the settings-module header
  comment naming every new `AWS_*` variable and the
  local-dev fall-through.
- New module `backend/dealer_ai/services/photo_storage.py`
  exporting three functions:
  - `generate_upload_url(*, storage_key, content_type,
    dealership) -> dict` — returns
    `{upload_url, storage_key, expires_at, method}`.
    Content-type whitelist enforced at the URL boundary
    (four allowed MIME types matching
    `CONDITION_PHOTO_CONTENT_TYPE_CHOICES`; non-image
    types raise `ValueError`). TTL cap ≤ 900 seconds.
  - `object_exists(storage_key: str) -> bool` — HEAD
    verification. Used by M3.5's `attach_photo` to reject
    metadata for objects that don't actually exist.
  - `generate_read_url(*, storage_key, ttl_seconds=900) ->
    str` — short-TTL signed read URL. No permanent public
    URLs (condition photos may show identifying details;
    warranty-defense value depends on the store
    controlling access).
- ~25 focused tests: content-type whitelist enforcement,
  TTL cap (never > 900), URL contains the storage key,
  dev / test fall-through to `FileSystemStorage` when env
  unset. Use `moto` or an S3-compatible mock —
  **zero real network access** in tests.

**Explicitly out of scope (deferred to specific later
increments):**

- ❌ `ConditionFindingPhoto` upload flow
  (`request_photo_upload`, `attach_photo`, `delete_photo`)
  — M3.5. The M3.1 photo model exists; the service
  functions that consume it land in M3.5.
- ❌ Modifications to `ConditionFindingPhoto` model or
  migration — M3.1 shipped the persistence layer; M3.4
  ships only the storage adapter.
- ❌ API endpoints — M3.6.
- ❌ Frontend — M3.7.
- ❌ AI role — never in M3.
- ❌ Any modification to `services/condition_report.py` —
  M3.2's contract is stable; the M3.5 upload flow will
  extend it, not this session.

## What SESSION_059 should do

### Recommended step sequence

1. **Read first (in this order — one pass, do not skim):**
   - `docs/roadmap/MILESTONE_3_PLANNING.md` §5.a (the
     three-option analysis + why Option A won) + §7 M3.4
     (the increment scope) + §1.4 (the storage-story design
     memo) + §1.5 photo model design notes (specifically
     "content-type whitelist enforced at URL issuance" and
     "photo rows represent attached objects, never upload
     intentions").
   - `docs/handoffs/SESSION_058_m3_inc3_read_model.md` —
     what the M3.3 read-model shipped and where M3.4 sits
     in the sequence.
   - `backend/dealer_kit/settings.py` — current
     configuration. Confirm no `DEFAULT_FILE_STORAGE`
     already set; confirm `MEDIA_ROOT` + `MEDIA_URL`
     already configured (they may not be — if not, add them
     as part of this increment).
   - `backend/requirements.txt` — confirm no existing
     `boto3` or `django-storages` pin that would collide.
   - `backend/dealer_ai/models.py::CONDITION_PHOTO_CONTENT_TYPE_CHOICES`
     — the four MIME values `photo_storage.py` must
     enforce.

2. **Verify starting state.**
   - `git status` — clean (or only the pre-existing
     `Dealer OS/` untracked dir).
   - `python3 manage.py test dealer_ai` → **1,894 pass, 1
     skipped, 0 fail**.
   - `python3 manage.py showmigrations dealer_ai` →
     migrations current through `0015_condition_report`.
   - `python3 manage.py makemigrations dealer_ai --check
     --dry-run` → "No changes detected."
   - `python3 -c "import storages"` → **should fail**
     (dependency not yet installed). Installing it is part
     of this increment.

3. **Add dependency.** Append `django-storages[s3]` to
   `backend/requirements.txt`. Install locally via
   `pip install -r backend/requirements.txt`. Verify
   `boto3` and `botocore` land as transitive deps.

4. **Configure settings.** In
   `backend/dealer_kit/settings.py`, add the env-driven
   `DEFAULT_FILE_STORAGE` selection with a comment block
   naming every new `AWS_*` variable and the dev / test
   fall-through invariant. Do NOT set any AWS default
   values.

5. **Author storage service.** Create
   `backend/dealer_ai/services/photo_storage.py` with the
   three functions in the order the M3.5 upload flow will
   call them. Import the content-type whitelist from
   `dealer_ai.models` (already exported as
   `CONDITION_PHOTO_CONTENT_TYPE_CHOICES`); build a
   `frozenset` at module level; validate at the URL
   boundary.

6. **Write focused tests.** New file
   `backend/dealer_ai/tests/test_photo_storage.py`. Use
   `moto` (or an in-process S3 mock) to exercise
   `generate_upload_url` / `object_exists` /
   `generate_read_url` without hitting the network. Verify
   the dev / test fall-through by asserting
   `settings.DEFAULT_FILE_STORAGE` resolves to
   `FileSystemStorage` when `AWS_STORAGE_BUCKET_NAME` is
   unset. Target ~25 tests.

7. **No migration.** M3.4 is pure Python + settings +
   dependency. Confirm at session end.

8. **Full suite + baseline.**
   `python3 manage.py test dealer_ai` should produce
   ~1,919 pass (1,894 + ~25 new), 1 skipped, 0 fail.

9. **Close SESSION_059 with:**
   - Storage service + settings edit + requirements
     addition + focused tests committed.
   - Handoff at
     `docs/handoffs/SESSION_059_m3_inc4_storage.md`.
   - Overwrite this file (`00-START-NEXT-SESSION.md`) with
     the SESSION_060 = M3.5 (upload flow) priority.
   - `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.4 entry
     annotated in-place with `SHIPPED at SESSION_059` +
     shipped-surface manifest.

## Explicit non-goals for SESSION_059

- ❌ Do NOT add `ConditionFindingPhoto` service functions
  (`request_photo_upload`, `attach_photo`, `delete_photo`)
  — those are M3.5.
- ❌ Do NOT modify any model, admin registration, or
  migration.
- ❌ Do NOT extend `services/condition_report.py`.
- ❌ Do NOT add API endpoints, frontend, or photo model
  behavior.
- ❌ Do NOT touch `services/tenancy.py`,
  `services/vehicle_ledger.py`, `services/llm_safety.py`,
  or any pre / post-LLM guard.
- ❌ Do NOT let tests hit real S3 — every S3 call in tests
  must go through `moto` or an equivalent mock.
- ❌ Do NOT pin `boto3` at a specific version;
  `django-storages[s3]` will pull a compatible one.
- ❌ Do NOT introduce any AI role.
- ❌ Do NOT commit any real `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, or `OPENAI_API_KEY`.

## NEXT TASK

Start SESSION_059 with the read-first list above. Ship
`django-storages[s3]` dependency + env-driven
`DEFAULT_FILE_STORAGE` selection +
`services/photo_storage.py` with three functions + ~25
focused tests using `moto`. Do NOT ship the upload flow, API,
or UI — those are M3.5 through M3.7.

Test baseline at SESSION_059 close: 1,894 → ~1,919.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — the acceptance
   contract; §7 M3.1 + §7 M3.2 + §7 M3.3 now annotated
   SHIPPED; §5.a is the load-bearing storage-decision
   memo; §7 M3.4 is the sub-scope this session ships.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 (lessons)
7. `docs/research/RECON_MAPPING.md` §2.5 + §13.1 +
   `docs/research/VEHICLE_CENTRIC_PIVOT.md` "Technical
   debt to pay down FIRST" item 3.
8. `docs/CAPABILITY_MATRIX.md`
9. Most recent handoffs
   (`SESSION_058_m3_inc3_read_model.md`,
   `SESSION_057_m3_inc2_service_layer.md`,
   `SESSION_056_m3_inc1_core_models.md`,
   `SESSION_055_milestone_3_planning.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_058 — M3.3 read-model shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015` applied. Default `Dealership` row exists
  (`slug='default'`). No pending migrations. Test baseline:
  **1,894 pass**, 1 skipped, 0 fail.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active.
- **Frontend (local):** Vite on `:5173`. Unchanged this
  session.
- **Frontend (prod):** NONE.
- **Frontend build:** unchanged this session; `npx tsc
  --noEmit` clean; `npx vite build` clean.
- **DRF defaults + CSRF + endpoint-level permissions:** all
  unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
  No new migration in M3.3; last verified clean-slate
  round-trip was SESSION_056.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR`. Unchanged this session. M3.4
  will add the optional `AWS_*` set.
- **Dev DB seeded users:** `smoke_owner` (dealer_owner) +
  `smoke_advisor` (advisor). Unchanged.
- **Milestone 2 shipped surface (locked, do not touch):**
  see `docs/CAPABILITY_MATRIX.md` §7c.
- **Milestone 3 shipped surface (in-progress):** M3.0
  planning (SESSION_055) + M3.1 core models (SESSION_056) +
  M3.2 service layer (SESSION_057) + M3.3 Vehicle
  read-model (SESSION_058 — this session). M3.4 through
  M3.8 queued for SESSION_059 through SESSION_063.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Every deferred idea from Milestones 1 + 2 + M3
  planning + M3.1 + M3.2 + M3.3 is recorded in the
  respective planning + retrospective + handoff docs.
