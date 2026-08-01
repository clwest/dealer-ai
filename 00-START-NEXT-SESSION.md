---
state: active
date: 2026-08-01
last_session_shipped: SESSION_069
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: in-progress
next_session: SESSION_070
next_milestone: 4
next_milestone_name: "Recon automation"
next_increment: 5
next_increment_name: "M4.5 — Vendor communication drafting + invented_recon_fact scrub"
---

# Next session — SESSION_070 · Milestone 4 · Increment 5 (M4.5 — vendor comm drafting + scrub)

> **Milestone 4 · Increment 4 shipped at SESSION_069.**
> Parts-service functions (`add_part`, `update_part`,
> `transition_part_status`, `delete_part`) added to
> `services/recon.py`. 7-transition FSM, whitelist
> updates, per-state timestamp auto-population, cross-
> tenant guard, `select_for_update` concurrency. 49
> focused tests. Backend baseline **2,318 → 2,367 pass**,
> 1 skipped, 0 fail. Zero VehicleCost side effects.
>
> **SESSION_070 opens M4.5 — the AI-drafted vendor comm
> path.** New module `services/vendor_comm.py` (4
> functions), plus `_scrub_invented_recon_fact` extension
> to `services/llm_safety.py` firing on `kind="vendor_comm"`
> and `kind="parts_order"`. LLM path stubbed via mock
> provider — zero real API access in tests.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md` §8b
5. `docs/roadmap/MILESTONE_4_PLANNING.md`:
   - §1.6 + §1.6.SHIPPED — VendorCommunication shape and
     the SESSION_067 enum reconciliation (kind /
     channel / status vocabularies as shipped in M4.1).
   - §5.g — AI boundary (what AI may / may NOT invent) +
     the four regex families for `_scrub_invented_recon_fact`
     + the JSON source-bundle contract.
   - §5.i — send deferred to post-M4 prod-readiness pass.
   - §7 M4.5 — service signatures.
6. `docs/handoffs/SESSION_069_m4_inc4_parts.md` — this
   session's authoritative closeout + "Recommended exact
   scope for SESSION_070".
7. Prior handoffs (066, 067, 068).
8. `backend/dealer_ai/services/llm_safety.py` — the
   existing scrub stack M4.5 extends additively per M2.5
   pattern.
9. `docs/research/RECON_MAPPING.md` §5.6 + §14.7 + §14.8
   + §16.5 (vendor comm research).

## What M4.5 delivers

**Vendor comm service + safety scrub only.** No migrations.
No new endpoints. No frontend. No SMTP / SMS wiring
(planning §5.i deferred).

### New module `services/vendor_comm.py` — 4 functions

- **`draft_communication(work_order, *, dealership,
  drafted_by, kind, channel, extra_notes="") -> VendorCommunication`**
  — assembles a source bundle from the WO + linked findings
  + parts per §5.g:
  ```python
  source = {
      "vehicle": {stock, year, make, model, vin_last_6},
      "vendor": {name},
      "findings": [{id, category, severity, description}, ...],
      "authorized_cost": str_two_decimals or None,
      "estimated_completion_date": iso or None,
      "parts_needed": [{name, part_number, quantity, source_type}, ...],
      "operator_notes": str,
  }
  ```
  Renders the bundle into an LLM prompt via existing
  provider factory. Runs the LLM output through
  `apply_post_llm_scrubs(kind="vendor_comm", ...)`. If the
  scrub rejects (dropped_reason set), the service raises
  a domain error rather than persisting a rejected draft.
  On success, persists `VendorCommunication(status='draft',
  drafted_by=drafted_by, drafted_at=timezone.now(),
  source_provenance=<sentence→source_key map>,
  draft_content=<scrubbed text>)`. Enforces cross-tenant
  guard + `full_clean()` before save.

- **`approve_communication(comm, *, dealership,
  approved_by) -> VendorCommunication`** — draft→approved
  transition. Sets `approved_by` + `approved_at`. Uses
  `select_for_update` + `refresh_from_db` per M4.2
  concurrency pattern.

- **`mark_sent(comm, *, dealership, sent_by,
  sent_content=None) -> VendorCommunication`** —
  approved→sent transition. Captures optional edited
  `sent_content` (falls back to `draft_content` if omitted).
  Sets `sent_by` + `sent_at`. Full model-layer sent-state
  invariant matrix from M4.1 surfaces via `full_clean`.

- **`log_communication(work_order, *, dealership,
  logged_by, kind, channel, direction, body) -> VendorCommunication`**
  — records an off-system comm (operator-recorded phone,
  in-person, inbound email). Creates directly at
  `status='logged'` with `draft_content=body`, `sent_by=logged_by`,
  `sent_at=timezone.now()`. Refuses if `kind` implies
  AI-drafted (i.e. `vendor_comm` or `parts_order` — the
  SESSION_066 refinement "AI-generated content may never
  jump directly to logged" is enforced here at the service
  layer, since the model layer cannot distinguish
  AI-drafted from operator-recorded).

### `_scrub_invented_recon_fact` — new post-LLM scrub

Extends `services/llm_safety.py::apply_post_llm_scrubs`.
Fires on `kind="vendor_comm"` and `kind="parts_order"`
(both new `kind` values recognized by
`apply_post_llm_scrubs`). Runs after
`detect_unsafe_response`. Text-only, zero DB access at
scrub time — source-bundle values are passed as scrub
parameters.

Four detection regex families per §5.g:

- **Invented finding IDs** — draft mentions "Finding #123"
  but 123 is not in `source["findings"][*]["id"]`.
  Rewrite: strip the ID reference; retain the description
  if present in source.
- **Invented part numbers** — draft mentions a part number
  pattern (`[A-Z0-9-]{5,}`) not in
  `source["parts_needed"][*]["part_number"]`. Rewrite:
  strip the part number.
- **Invented dollar amounts** — draft mentions a `$\d+`
  amount not matching `authorized_cost` or the sum of
  `parts_needed[*].unit_cost * quantity`. Rewrite: strip
  the amount; log for operator review.
- **Invented dates** — draft mentions a date not matching
  `estimated_completion_date`. Rewrite: replace with a
  neutral phrase or strip.

## What SESSION_070 should do

### Recommended step sequence

1. **Read first (in order):**
   - `docs/roadmap/MILESTONE_4_PLANNING.md` §1.6 +
     §1.6.SHIPPED + §5.g + §5.i + §7 M4.5.
   - `docs/handoffs/SESSION_069_m4_inc4_parts.md` — the
     scope block above.
   - `backend/dealer_ai/services/llm_safety.py` — the
     existing scrub stack. Understand how M2.5's
     `_scrub_acquisition_price` was layered in — M4.5
     mirrors the same additive shape.
   - `backend/dealer_ai/services/llm/` — the mock provider
     pattern for stubbed LLM calls.
   - `backend/dealer_ai/services/ad_copy.py` +
     `services/follow_up.py` — the "AI drafts N variants;
     safety stack scrubs; operator picks + edits" three-
     step pattern M4.5 mirrors (per planning §3.3).
   - `backend/dealer_ai/models.py::VendorCommunication` —
     the M4.1 model shape, especially the invariant matrix
     for sent / approved / logged states.
   - `backend/dealer_ai/services/recon.py` — the
     cross-tenant guard pattern M4.5 mirrors.

2. **Verify starting state.**
   - `git status` clean (or only pre-existing untracked).
   - `python3 manage.py test dealer_ai` → **2,367 pass, 1
     skipped, 0 fail**.
   - `python3 manage.py check` clean.
   - `python3 manage.py makemigrations --check --dry-run`
     → "No changes detected."

3. **Extend `services/llm_safety.py`** with the new scrub
   function + register it against `kind="vendor_comm"`
   and `kind="parts_order"`.

4. **Draft `services/vendor_comm.py`** with the four
   functions. LLM path stubbed via existing mock provider.
   Every function threads `dealership=` explicitly, calls
   `full_clean()` before save, and re-raises raw scrub /
   validation errors as domain errors where the translation
   carries meaning.

5. **Write ~55 focused tests:**
   - `test_vendor_comm_service.py` — draft happy path,
     source_provenance recording, state transitions,
     human-approval-required-before-send, log skips
     approval, AI-drafted cannot jump to logged.
   - `test_llm_safety_recon_scrub.py` — each regex family
     strips the invented content, correctly-attributed
     content passes untouched.

6. **Full-suite verification.** Target 2,367 → ~2,422 pass.
   Zero regressions.

7. **Ship handoff at
   `docs/handoffs/SESSION_070_m4_inc5_vendor_comm.md`**
   mirroring `SESSION_069_m4_inc4_parts.md` shape.

8. **Overwrite `00-START-NEXT-SESSION.md`** with M4.6
   priority (admin API + permission matrix).

## Explicit non-goals for SESSION_070

- ❌ Do NOT wire outbound SMTP / SMS send. Planning §5.i
  defers to prod-readiness pass.
- ❌ Do NOT add real LLM API calls in tests. Mock provider
  only.
- ❌ Do NOT touch M4.1/M4.2/M4.3/M4.4 substrate.
- ❌ Do NOT add any endpoint — M4.6.
- ❌ Do NOT add new permission class — M4.6.
- ❌ Do NOT touch frontend — M4.7.
- ❌ Do NOT introduce any new migration.

## NEXT TASK

Start SESSION_070 with the read-first list above. Extend
`services/llm_safety.py` with `_scrub_invented_recon_fact`.
Draft `services/vendor_comm.py` (four functions). Write
~55 focused tests split across service + scrub. Target
baseline 2,367 → ~2,422. Ship the M4.5 handoff.

Backend baseline at SESSION_070 close: **~2,422 pass**.
Frontend baseline: unchanged.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_4_PLANNING.md` (SESSION_066
   refinements + SESSION_067 amendments + SESSION_068
   category-mapping table; §5.g anchors M4.5)
6. `docs/handoffs/SESSION_069_m4_inc4_parts.md`
7. `docs/handoffs/SESSION_068_m4_inc3_ledger.md`
8. `docs/handoffs/SESSION_067_m4_inc2_service_state_machine.md`
9. `docs/handoffs/SESSION_066_m4_inc1_core_models.md`
10. `docs/handoffs/SESSION_065_m4_planning.md`
11. `backend/dealer_ai/services/llm_safety.py` (M2.5
    scrub pattern the M4.5 scrub mirrors)
12. `docs/research/RECON_MAPPING.md` §2.6 (AI must never
    invent findings) + §5.6 + §14.7 + §14.8 + §16.5
    (vendor comm operational context).
13. `docs/CAPABILITY_MATRIX.md` §7c + §7d
14. Most recent handoffs
    (`SESSION_069_m4_inc4_parts.md`,
    `SESSION_068_m4_inc3_ledger.md`,
    `SESSION_067_m4_inc2_service_state_machine.md`,
    `SESSION_066_m4_inc1_core_models.md`,
    `SESSION_065_m4_planning.md`,
    `SESSION_064_m3_inc8_closeout.md`,
    `SESSION_063_m3_inc7_operator_ui.md`,
    `SESSION_062_m3_inc6b_photo_api.md`,
    `SESSION_061_m3_inc6a_admin_api.md`,
    `SESSION_060_m3_inc5_upload_flow.md`,
    `SESSION_059_m3_inc4_storage.md`,
    `SESSION_058_m3_inc3_read_model.md`,
    `SESSION_057_m3_inc2_service_layer.md`,
    `SESSION_056_m3_inc1_core_models.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_069 — M4.4 parts service shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0016` (unchanged since SESSION_066). Test
  baseline: **2,367 pass**, 1 skipped, 0 fail (up from
  2,318; +49 M4.4 parts-service tests).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  clean. `vite build` clean. Unchanged.
- **Frontend (prod):** NONE.
- **DRF defaults + CSRF + permissions:** unchanged.
- **Milestone 4 status:** M4.1 + M4.2 + M4.3 + M4.4
  shipped; vendor comm + scrub (M4.5) is the next
  in-scope increment. Planning artifact `status: draft`
  (flips at M4.9). Amendments landed through SESSION_068
  (category-mapping table at §5.e).
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist.
- **Dev DB seeded users:** `smoke_owner` + `smoke_advisor`.
- **New M4 tables:** unchanged from SESSION_066.
- **Service surface:** `services/recon.py` now exposes:
  - 11 recon-related public functions (10 M4.2 originals
    + `revise_estimate` from M4.3).
  - 4 parts-service public functions (M4.4).
  - 2 Vehicle-property read helpers (M4.2).
  - 4 domain errors.
  - Ledger-integration constants + helpers (M4.3).
  - Parts constants + mutation whitelist + transition
    table (M4.4).
- **Ledger behavior:** every M4.3 auto-minted VehicleCost
  row carries a `WORKORDER:<id>:*` reference matching one
  of five families. Net estimate on any terminal WO =
  `Decimal("0.00")`. Parts do NOT independently post to
  VehicleCost (M4.4 boundary; planning §5.h).
