---
title: "SESSION_070 handoff — Milestone 4 · Increment 5 (vendor communication drafting)"
status: historical
type: handoff
date: 2026-08-01
session: 070
milestone: 4
milestone_status: in-progress
increment: 5
increment_status: shipped
commit: TBD
---

# SESSION_070 — Milestone 4 · Increment 5 (M4.5 — vendor comm drafting + `_scrub_invented_recon_fact`)

## What shipped

New service module
`backend/dealer_ai/services/vendor_comm.py` with four public
functions (`draft_communication`, `approve_communication`,
`mark_sent`, `log_communication`) + four domain error classes
+ two private cross-tenant guards + source-bundle assembly
helpers + LLM prompt construction.

New post-LLM scrub `_scrub_invented_recon_fact` added to
`services/llm_safety.py`, wired into `apply_post_llm_scrubs`
on `kind in {"vendor_comm", "parts_order"}`. Four regex
families per planning §5.g: invented finding IDs, part
numbers, dollar amounts, ISO dates.

62 focused tests across two new files
(`test_llm_safety_recon_scrub.py`: 29,
`test_vendor_comm_service.py`: 33).

**Zero migrations. Zero API endpoints. Zero permission
classes. Zero frontend changes. Zero real LLM API calls in
tests** (MockLLMProvider throughout). Zero SMTP / SMS wiring
(planning §5.i deferred).

## Session preamble

No planning refinements needed at session open. §1.6 +
§1.6.SHIPPED (SESSION_067) locked the enum vocabularies;
§5.g locked the AI boundary + scrub regex families; §5.i
locked the send-deferred posture; §7 M4.5 locked the four
function signatures.

## Read-first pass performed

1. `docs/roadmap/MILESTONE_4_PLANNING.md` §1.6 +
   §1.6.SHIPPED + §5.g + §5.i + §7 M4.5.
2. `docs/handoffs/SESSION_069_m4_inc4_parts.md` — the
   "Recommended exact scope for SESSION_070" section.
3. `backend/dealer_ai/services/llm_safety.py` — existing
   scrub stack. Learned the `apply_post_llm_scrubs`
   dispatch pattern + how M2.5 `_scrub_acquisition_price`
   was layered in additively. Mirrored the shape for the
   new recon scrub.
4. `backend/dealer_ai/services/llm/base.py` +
   `factory.py` — LLM abstraction; `chat(messages,
   temperature, max_tokens)` is the surface.
5. `backend/dealer_ai/tests/_mocks.py::MockLLMProvider` —
   scripted-reply provider for stubbed tests.
6. `backend/dealer_ai/services/ad_copy.py` — the M2.4
   three-step "AI drafts → safety stack scrubs → operator
   reviews" pattern M4.5 mirrors.
7. `backend/dealer_ai/models.py::VendorCommunication` —
   status invariant matrix for draft / approved / sent /
   logged.
8. `backend/dealer_ai/services/recon.py` — cross-tenant
   guard pattern M4.5 mirrors.

## Concrete deliverables

### Extension to `services/llm_safety.py`

- Module docstring extended: `"vendor_comm"` and
  `"parts_order"` kinds documented. Explanation of the
  `recon_source_bundle=` kwarg contract.
- `_RECON_COMM_KINDS: frozenset[str] = {"vendor_comm",
  "parts_order"}` — module-level; tests import and lock.
- Four private helpers: `_valid_finding_ids`,
  `_valid_part_numbers`, `_valid_dollar_strings`
  (normalizes to two-decimal + integer + comma-grouped
  forms), `_valid_iso_dates`.
- Four regex constants: `_RECON_FINDING_REF_PATTERN`,
  `_RECON_PART_NUMBER_PATTERN`, `_RECON_DOLLAR_PATTERN`,
  `_RECON_ISO_DATE_PATTERN`.
- Public function `_scrub_invented_recon_fact(text, *,
  source_bundle) -> (cleaned_text, changed_bool)`. Text-
  only. Deterministic. Empty source bundle treats every
  reference as invented.
- `apply_post_llm_scrubs` signature gained
  `recon_source_bundle: Optional[dict] = None` kwarg.
  Wired into the dispatch: fires on
  `kind in _RECON_COMM_KINDS`, after
  `_scrub_acquisition_price`, before the
  kind-specific `invented_promotion` /
  `invented_appointment` scrubs. Rewrite pattern:
  invented finding → `"the finding"`; invented part
  number → `"the part"`; invented amount →
  `"the quoted amount"`; invented date →
  `"the scheduled date"`.

### New module `services/vendor_comm.py`

**Four public functions:**

- `draft_communication(work_order, *, dealership,
  drafted_by, kind, channel, direction="outbound",
  extra_notes="", provider=None) -> VendorCommunication`
  — three-step drafting pattern per §3.3. Assembles source
  bundle from WO + linked findings + parts. Renders LLM
  prompt with strict boundaries. Runs LLM output through
  `apply_post_llm_scrubs(kind=<kind>, recon_source_bundle=<bundle>)`.
  Rejects (does NOT persist) on `dropped_reason` or empty
  output. Persists `VendorCommunication(status='draft')`
  with `source_provenance={"source_bundle": <bundle>,
  "scrubs_fired": [...], "llm_provider": <name>}`.
- `approve_communication(comm, *, dealership,
  approved_by) -> VendorCommunication` — draft → approved
  transition. `select_for_update` + `refresh_from_db`
  concurrency pattern.
- `mark_sent(comm, *, dealership, sent_by,
  sent_content=None) -> VendorCommunication` — approved
  → sent. `sent_content` defaults to `draft_content` if
  operator sent draft as-is; may be overridden with an
  edited version. Sent-state model-layer invariants
  (nonblank sent_content + all provenance fields) surface
  via `full_clean`.
- `log_communication(work_order, *, dealership,
  logged_by, kind, channel, direction, body) -> VendorCommunication`
  — creates DIRECTLY at `status='logged'`. Accepts any
  kind including `vendor_comm` / `parts_order` (operator
  may log a comm that happened off-system). `work_order`
  is optional (cold calls / new-vendor inbounds).
  `source_provenance = {"logged_off_system": True, ...}`
  distinguishes from AI-drafted rows.

**Four domain errors:**

- `CrossTenantVendorCommError` — cross-tenant guard.
- `VendorCommImmutableError` — illegal state transition or
  invalid kind for the workflow (`draft_communication`
  called with `narrative` kind).
- `ReconFactScrubDroppedError` — LLM output rejected by
  safety stack; draft NOT persisted.
- `EmptyDraftError` — LLM returned empty or scrubbed to
  empty; not persisted.

**Two private cross-tenant guards** — `_assert_work_order_tenant`,
`_assert_comm_tenant`. Same shape as
`services/recon.py::_assert_*_tenant`.

**Module-level constant** — `_AI_DRAFTED_KINDS = {"vendor_comm",
"parts_order"}`. Locks the vocabulary of kinds
`draft_communication` accepts.

**Source-bundle assembly** — `_build_source_bundle(work_order,
*, extra_notes)` builds the dict shape locked at planning §5.g.
Reads `work_order.finding_links.select_related("finding__report")`
and `work_order.parts.all()`. All queries tenant-scoped by
construction.

**LLM prompt construction** — `_build_llm_messages(source_bundle,
*, kind, channel)` renders the bundle into
system + user messages. System message pins the boundaries
(draft ONLY from source; don't invent facts). User
message serializes bundle as human-readable key/value pairs
and requests a body-only draft (no subject line — operator
adds).

**SESSION_066 refinement "AI-generated content may never
jump directly to logged" — structurally enforced.** The
four public functions produce only these status paths:
- `draft_communication` → creates status='draft'
- `approve_communication` → transitions draft → approved
- `mark_sent` → transitions approved → sent
- `log_communication` → creates status='logged' from
  scratch with operator-authored body

None of them transition an existing draft/approved/sent
row into 'logged'. `test_vendor_comm_service.AIDraftedCannotReachLogged`
locks the module public surface + guards against a future
`log_existing_*` function being added.

### Tests (62 new)

**`test_llm_safety_recon_scrub.py` — 29 tests:**

- `ReconCommKindsMembership` (1) — locks the frozenset.
- `ScrubEmptyOrTrivial` (2).
- `ScrubInventedFindingIds` (4).
- `ScrubInventedPartNumbers` (3).
- `ScrubInventedDollarAmounts` (5).
- `ScrubInventedDates` (2).
- `ScrubEmptyBundleTreatsAllAsInvented` (3).
- `ScrubWhitespaceNormalization` (2).
- `ApplyScrubsFiresOnReconKinds` (6) — vendor_comm fires,
  parts_order fires, chat/ad don't, missing bundle,
  ordering with other scrubs.
- `ApplyScrubsHardRewriteReturnsEarly` (1) — unsafe
  response short-circuits before recon scrub runs.

**`test_vendor_comm_service.py` — 33 tests:**

- `AIDraftedKindsVocabulary` (1) — locks `_AI_DRAFTED_KINDS`.
- `DraftCommunicationHappyPath` (5) — creates draft,
  source_provenance shape, parts in bundle, scrub strips
  invented finding, parts_order kind allowed.
- `DraftCommunicationValidation` (4) — narrative
  rejected, invalid channel, invalid direction,
  cross-tenant.
- `DraftCommunicationScrubDropped` (2) — dealer-cost
  unsafe response NOT persisted, empty LLM response NOT
  persisted.
- `ApproveCommunication` (3) — happy path, re-approve
  rejected, cross-tenant rejected.
- `MarkSent` (5) — defaults to draft_content, accepts
  edited, refuses from draft, refuses from sent,
  cross-tenant.
- `LogCommunication` (10) — creates at logged, accepts
  vendor_comm kind, accepts parts_order kind, null WO
  permitted, empty/whitespace body rejected, invalid
  kind/channel/direction rejected, cross-tenant, logged
  source_provenance flag.
- `AIDraftedCannotReachLogged` (2) — public function
  surface locked; no service function transitions an
  existing row into 'logged'.

**Total new tests: 62.**

## Verification evidence

- `python3 manage.py test dealer_ai` → **2,429 pass, 1
  skipped, 0 fail** (up from 2,367; +62 M4.5 tests).
- `python3 manage.py check` → clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- **No new migration files.** No API / permissions / URL /
  frontend files changed.

## Compatibility

Preserved unchanged:

- **M1/M2/M3 substrate.** All APIs unchanged.
- **M4.1 substrate.** Model shapes untouched.
  `VendorCommunication` fields consumed unchanged;
  invariant matrix (`clean()` for draft/approved/sent/
  logged) surfaces via `full_clean`.
- **M4.2 substrate.** State-machine functions untouched.
- **M4.3 substrate.** Ledger helpers untouched. Vendor
  comm never posts to VehicleCost.
- **M4.4 substrate.** Parts service untouched. M4.5 reads
  parts via the `work_order.parts` reverse accessor as
  source-bundle input; never writes.
- **Chat / ad / follow-up scrub behavior.** M4.5 added
  the `_scrub_invented_recon_fact` in a new dispatch
  branch guarded by `kind in _RECON_COMM_KINDS`; other
  kinds unchanged. All ~580 existing chat scrub tests +
  M2.5 acquisition scrub tests + ad / follow-up tests
  continue to pass.
- **Frontend contracts.** No frontend files touched.

## Explicitly out of scope for M4.5

- ❌ Outbound SMTP / SMS send. Planning §5.i defers to
  post-M4 prod-readiness pass.
- ❌ Real LLM API access in tests. MockLLMProvider only.
- ❌ Admin API endpoints — M4.6.
- ❌ New permission class — M4.6.
- ❌ Frontend — M4.7.
- ❌ Bounced-email handling / retry queue — post-M4
  prod-readiness (planning §5.i acceptance criteria).
- ❌ Per-sentence provenance mapping in
  `source_provenance`. M4.5 v1 captures the source bundle
  itself as provenance so the M4.7 UI can render "here's
  what the AI had to work from" alongside the draft.
  Per-sentence attribution requires either structured LLM
  output or NLP heuristics; deferred to future increment
  if operational evidence surfaces the need.

## Files changed

- `backend/dealer_ai/services/llm_safety.py` — imports
  extended (Decimal, InvalidOperation); module docstring
  extended for two new kinds; `_RECON_COMM_KINDS` module
  constant added; four private helpers + four regex
  constants + `_scrub_invented_recon_fact` public function
  added between `_scrub_acquisition_price` and the public
  entry; `apply_post_llm_scrubs` signature extended with
  `recon_source_bundle=None` kwarg + dispatch integration.
- `backend/dealer_ai/services/vendor_comm.py` — new file,
  ~520 lines.
- `backend/dealer_ai/tests/test_llm_safety_recon_scrub.py`
  — new file (29 tests).
- `backend/dealer_ai/tests/test_vendor_comm_service.py` —
  new file (33 tests).
- `docs/handoffs/SESSION_070_m4_inc5_vendor_comm.md` —
  this handoff.
- `00-START-NEXT-SESSION.md` — overwritten with SESSION_071
  = M4.6 priority.

## Recommended exact scope for SESSION_071 (M4.6 — admin API + permission matrix)

Per `MILESTONE_4_PLANNING.md` §7 M4.6 + §5.f (role
permission matrix):

**Scope.**

- Admin API endpoints under
  `/api/dealer-ai/admin/vehicles/<stock_number>/` +
  `/api/dealer-ai/admin/vendors/` per §7 M4.6.
- New permission class
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  composed from existing `recon_manager` / `sales_manager`
  / `dealer_owner` roles per §5.f matrix.
- Domain-error mapping: 409 for `VendorCommImmutableError`
  / `ReconImmutableError` / `InvalidReconTransitionError`;
  404 for cross-tenant + fail-closed lookups.
- Provenance rendering in serializers (source_bundle
  visible in response body for operator review).

**Tests target.** ~90 focused endpoint tests: permission
matrix per endpoint (7 role cases minimum), business
flows, domain-error mapping, cross-tenant fail-closed
404s, no-storage-key-leak, no-recon-data-on-public-
surfaces.

**Boundary.** Backend baseline: ~2,429 → ~2,519 pass.
Extends `views.py` and `permissions.py`. No migrations.
No frontend (that's M4.7).

**Explicit non-goals for M4.6:**

- ❌ Frontend — M4.7.
- ❌ Any new service module — the M4.6 views delegate
  entirely to `services/recon.py` + `services/vendor_comm.py`.
- ❌ Modifying M4.1 – M4.5 substrate.
- ❌ Outbound SMTP / SMS — planning §5.i deferred.

## Anchors that win on conflict for SESSION_071

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_4_PLANNING.md` — §5.f
   (permission matrix), §7 M4.6 (endpoint list).
6. `docs/handoffs/SESSION_070_m4_inc5_vendor_comm.md` —
   this handoff.
7. Prior handoffs (066–069).
8. `backend/dealer_ai/permissions.py` — existing role
   classes; M4.6 composes an additive new class.
9. `backend/dealer_ai/views.py` — existing admin endpoint
   patterns (M2.6 ledger, M3.6 condition-report) that
   M4.6 mirrors.
