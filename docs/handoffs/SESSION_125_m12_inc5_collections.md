---
title: "SESSION_125 handoff — Milestone 12 · Increment 5 (M12.5 — Collection contact log + FDCPA scrub)"
status: historical
type: handoff
date: 2026-08-02
session: 125
milestone: 12
milestone_status: in_progress
increment: 5
increment_status: shipped
commit: TBD
---

# SESSION_125 — Milestone 12 · Increment 5 (M12.5 — Collection contact log + FDCPA scrub)

## What shipped

Fourth BHPH-portfolio entity
(`CollectionContact`) — immutable
audit log of collection contact
attempts — plus a new FDCPA-
adjacent scrub layer extending
`services/llm_safety.py`. Per
`MILESTONE_12_PLANNING.md` §1.5 +
§5.e Option A (extend existing
scrub stack — locked at
SESSION_121 open).

**Five §0.a M12.5 open decisions
recorded as-recommended:**

1. **Channel vocab** — fixed 5-
   value set (`phone` /
   `letter` / `sms` / `email` /
   `in_person`).
2. **Outcome vocab** — fixed 4-
   value set (`contact_made` /
   `left_message` /
   `no_answer` /
   `refused_to_speak`).
3. **Scrub scope** — extend the
   existing 16-stage pipeline
   with a new stage under
   `kind="collection_contact"`,
   not a parallel package.
4. **Scrub content targets** —
   pattern-based per category
   (deficiency threats /
   harassment-adjacent /
   false-representation) with a
   fixed phrase list per
   category. Full FDCPA
   classifier deferred beyond
   M12.
5. **Log-and-replace posture** —
   scrub REWRITES the offending
   language rather than blocking
   the whole draft (matches the
   M2 partial-scrub pattern).
   Operator sees neutralized
   copy + a scrub-fired log
   entry.

Streak stands at **41 planning-time
as-recommended M5.1 → M12.1** (§0.a
implementation-time decisions don't
count against streak per M10 §9).

## By the numbers

- **Backend baseline: 4,096 pass, 1
  skipped, 0 fail** (was 4,058 at
  M12.4 close — **+38 tests, 0
  regressions**).
- **Frontend Vitest baseline: 67
  pass** (unchanged — no frontend
  at M12.5).
- **Migrations `0041`**
  (`0041_m125_collection_contact`).
- **Tenancy carriers: 42 → 43**
  (`CollectionContact` registered).
- **DRF admin surface: 90 → 92**
  (two new endpoints —
  create + list).
- **Frontend operator routes:** 15
  (unchanged).
- **Permission classes: 8**
  (unchanged).
- **Celery-beat task families: 8**
  (unchanged — no new detector
  at M12.5).
- **Post-LLM scrub layers: 16 →
  17** (new
  `collection_language` stage
  gated on
  `kind="collection_contact"`).

## Files touched

### New
- `backend/dealer_ai/services/collection_contacts/__init__.py`
- `backend/dealer_ai/services/collection_contacts/collection_contact.py`
  (two verbs)
- `backend/dealer_ai/views_collection_contacts.py`
  (two endpoints)
- `backend/dealer_ai/migrations/0041_m125_collection_contact.py`
- `backend/dealer_ai/tests/test_m125_collection_contact_model.py`
  (7 tests)
- `backend/dealer_ai/tests/test_m125_collection_language_scrub.py`
  (16 tests)
- `backend/dealer_ai/tests/test_m125_collection_contact_service.py`
  (6 tests)
- `backend/dealer_ai/tests/test_m125_collection_contact_endpoint.py`
  (9 tests)
- `docs/handoffs/SESSION_125_m12_inc5_collections.md`
  (this file)

### Modified
- `backend/dealer_ai/models.py` — added
  `CollectionContact` model + 5-
  value channel vocab + 4-value
  outcome vocab.
- `backend/dealer_ai/services/tenancy.py`
  — extended
  `_TENANT_CARRIER_MODEL_NAMES` 42
  → 43.
- `backend/dealer_ai/services/llm_safety.py`
  — added
  `_scrub_collection_language` +
  `_COLLECTION_LANGUAGE_PATTERNS`
  (three-category pattern list) +
  wired under
  `kind="collection_contact"` in
  `apply_post_llm_scrubs`.
- `backend/dealer_ai/urls.py` — two
  new admin paths.
- `00-START-NEXT-SESSION.md` —
  flipped to SESSION_126 · M12.6
  priority.

## Collection-language scrub

New `kind="collection_contact"`
gate on `apply_post_llm_scrubs`.
Three pattern categories per §1.5:

### 1. Deficiency threats
- Credit-bureau leverage
  ("we will report you to…")
  → "we may report late
  payments to credit bureaus".
- Lawsuit threats
  ("we will sue you") →
  "legal action is one option
  we may consider".
- Wage garnishment
  ("we will garnish your
  wages") → "wage
  garnishment requires a
  court order".
- Jail-time threats → REMOVED
  (illegal under FDCPA §807(4)).
- Arrest threats → REMOVED.

### 2. Harassment-adjacent
- Employer / workplace contact
  threats → REMOVED (FDCPA
  §805 restrictions).
- Neighbor / family / friend
  contact threats → REMOVED
  (FDCPA §805(b) third-party
  contact).
- Repeated-contact pressure
  ("keep calling until…") →
  "follow up as needed".

### 3. False-representation
- Attorney impersonation →
  REMOVED (FDCPA §807(3)).
- Law-enforcement impersonation
  → REMOVED.
- Court-official impersonation
  → REMOVED.
- Credit-bureau impersonation
  → REMOVED.

Scrub is text-only, no DB access,
no dealer-type gating — FDCPA
rules apply equally at
independent and franchise BHPH
portfolios.

## Non-goals honored

- ❌ No repossession (M12.6).
- ❌ No portfolio analytics or
  UI (M12.7).
- ❌ No full FDCPA classifier
  (deferred beyond M12 —
  pattern-based catches the
  common cases without an
  external safety-model
  dependency).
- ❌ No auto-generation of
  collection copy — scrub
  runs on drafted output only.
- ❌ No SMS / email / phone
  transport integration — the
  entity records that a
  contact happened, not the
  content transport.
- ❌ No contact-attempt
  workflow orchestration.

## Design notes worth remembering

### Extended existing scrub stack, not parallel
Per §5.e Option A. The new
`collection_language` scrub is a
new stage in the 16 → 17 stage
pipeline, not a separate package.
Preserves the single-authority
posture for post-LLM safety —
one entry point
(`apply_post_llm_scrubs`), one
kind dispatch.

### Log-and-replace, not block
Matches the M2
`default_assumption` /
`internal_directive` /
`rate_language` scrub pattern.
The operator sees the
neutralized copy + a
`scrubs_fired` log entry. This
is a text safety net, not a
final compliance gate — a full
FDCPA classifier is deferred
beyond M12.

### Pattern list intentionally narrow
Each of the three categories
uses a fixed phrase list rather
than an ML classifier. Coverage
is deliberately not exhaustive:
the scrub catches the most
common problematic phrasings
that LLMs produce, without
introducing a false-positive
risk (neutral collection copy
must pass through unchanged —
locked by
`test_neutral_reminder_passes_through_unchanged`).

### `contacted_by_user` FK SET_NULL
The audit record survives
operator-account deletion
(mirrors `PhotoAsset.uploaded_by`
rationale). The endpoint auto-
populates the FK with
`request.user`, so operators
don't have to identify
themselves manually.

### No new dealer-type gating
FDCPA rules apply equally at
independent and franchise BHPH
portfolios — no
`get_dealer_profile()` check
inside the scrub. Distinct from
the M2 `_scrub_indie_prohibited`
which IS dealer-type-gated
because that copy is only wrong
in an independent context.

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_12_PLANNING.md`
   §1.5 + §5.e + §7 M12.5
4. `docs/handoffs/SESSION_124_m12_inc4_ptp.md`
   (previous session)
5. `backend/dealer_ai/services/llm_safety.py`
   (extended stack)
6. `backend/dealer_ai/services/collection_contacts/`
7. `backend/dealer_ai/models.py::CollectionContact`
