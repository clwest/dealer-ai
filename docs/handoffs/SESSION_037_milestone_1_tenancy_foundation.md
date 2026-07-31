---
title: "SESSION_037 handoff — Milestone 1 tenancy foundation (Increments 1 & 2)"
status: historical
type: handoff
date: 2026-07-31
session: 037
commits:
  - 36a4d74  # Increment 1 — Dealership tenancy-root model
  - 0e7e710  # Increment 2 — nullable FKs + verified backfill
---

# SESSION_037 — Milestone 1 tenancy foundation (Increments 1 & 2)

## What shipped

The first two increments of Milestone 1. The `Dealership` tenancy
root is now a model, and every one of the six tenant-carrying
models named in `docs/roadmap/MILESTONE_1_PLANNING.md` §1.5 has a
nullable `dealership` FK pointing at a deterministically-seeded
default row. No resolver, view, serializer, endpoint auth, or
frontend behavior was touched — Increment 3 will land those
together with the FK NOT NULL flip.

### Increment 1 — `Dealership` model (commit `36a4d74`)

- New `Dealership(name, slug, timestamps)` in `backend/dealer_ai/models.py`.
- Schema migration `0007_dealership.py`.
- 4 tests locking the model shape (`round_trip`, `__str__`,
  unique-slug, `Meta.ordering`).
- Baseline: 1,300 → 1,304 pass, 1 skipped, 0 fail.

### Increment 2 — nullable FKs + verified backfill (commit `0e7e710`)

Six models gained a nullable `dealership` FK
(`on_delete=CASCADE`, distinct `related_name` per model):

| Model                     | `related_name`         |
|---------------------------|------------------------|
| `Vehicle`                 | `vehicles`             |
| `Salesperson`             | `salespeople`          |
| `ChatSession`             | `chat_sessions`        |
| `ChatMessage`             | `chat_messages`        |
| `CustomerLead`            | `customer_leads`       |
| `DealerOnboardingProfile` | `onboarding_profiles`  |

Two migrations:

- **`0008_add_dealership_fks.py`** — schema; nullable FK add.
- **`0009_backfill_dealership_fks.py`** — data;
  `get_or_create(slug='default')` with `name` resolved via the
  three-tier ladder from `MILESTONE_1_PLANNING.md` §1.5
  (`settings.DEALER_AI_DEALER_NAME` → first non-empty
  `DealerOnboardingProfile.dealership_name` →
  `"Default Dealership"`), then `filter(dealership__isnull=True)
  .update(dealership=default)` for each of the six carriers.
  Post-backfill count check raises if any nulls remain — the
  entire migration then rolls back inside its transaction, so a
  partial backfill can never be committed.

Idempotent: `get_or_create` + `filter(isnull=True)` shape is
safe under repeated invocation. Reverse migration nulls-out
backfilled rows and deletes the default row (only ever called
before the FK is dropped, so no live references exist at that
point).

Backfill verification against the dev DB after applying both
migrations:

| Model                     | Rows | Nulls after backfill |
|---------------------------|-----:|---------------------:|
| `Vehicle`                 |   91 |                   0  |
| `Salesperson`             |    5 |                   0  |
| `ChatSession`             |    3 |                   0  |
| `ChatMessage`             |    6 |                   0  |
| `CustomerLead`            |    0 |                   0  |
| `DealerOnboardingProfile` |    1 |                   0  |

+9 new tests covering: default row exists, per-model
attachment via each `related_name`, the increment-2 nullability
boundary (a guard that fails if NOT NULL lands early), and
non-emptiness of the fallback name.

Final test baseline: **1,313 pass, 1 skipped, 0 fail** (was
1,300 at session start; 1,304 after Increment 1; 1,313 after
Increment 2).

## Deviation from plan — NOT NULL flip deferred to Increment 3

`MILESTONE_1_PLANNING.md` §1.5 listed the migration path as
schema → data → NOT NULL, and SESSION_037's initial instruction
matched. During Increment 2 the NOT NULL flip was generated and
tested; it broke 686 tests because every existing write-path
caller (`views.py`, `services/chat_engine.py`,
`services/inventory_import.py`, `services/lead_service.py`,
`services/follow_up.py`, `services/handoff_service.py`, plus
test setUp blocks) constructs these models without passing
`dealership=`. In production, the same code paths would 500.

The SESSION_037 instruction explicitly said *"Do not modify
resolvers, views, serializers, endpoint auth, or frontend
behavior yet."* Enforcing NOT NULL without those write-path
changes conflicts with that constraint AND with the "leave the
application in a working state" success criterion.

Sequencing chosen instead: NOT NULL lands **inside Increment 3**
together with the write-path plumbing that guarantees it stays
satisfied. Migration `0010_dealership_fks_not_null.py` was
generated, then removed; the model FKs were reverted to
`null=True`; and a `test_fk_is_nullable_in_this_increment`
guard was added so a premature flip fails loudly.

Target end-state (all six FKs `NOT NULL`) is unchanged. Only
the increment boundary shifted. Planning memo not updated
because the memo's contract still holds — the deviation is a
sequencing refinement within the milestone.

## What was NOT touched (compatibility invariants preserved)

Per the SESSION_037 constraint and `MILESTONE_1_PLANNING.md`
§3, none of the following changed. Every §3 checklist item
that was true before this session is still true.

- `services/dealer_config.py` — resolver signatures unchanged.
- `services/chat_engine.py` — chat session creation unchanged.
- `services/inventory_import.py` — importer signature unchanged.
- `services/llm_safety.py` — 16-stage scrub pipeline untouched.
- `services/payment_engine.py` — deterministic math untouched.
- Any view in `views.py` — no auth added; no queryset scoping.
- Any serializer — DealerOnboardingProfile shape unchanged.
- Frontend — no auth propagation, no login page.
- Django REST Framework config — `REST_FRAMEWORK` in
  `settings.py:100-103` still has no
  `DEFAULT_AUTHENTICATION_CLASSES` /
  `DEFAULT_PERMISSION_CLASSES`.

Env override path (`DEALER_AI_DEALER_NAME`,
`DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`) works
identically to before — the resolver never reads the new
`Dealership` model yet.

## Files touched

Created:

- `backend/dealer_ai/migrations/0007_dealership.py`
- `backend/dealer_ai/migrations/0008_add_dealership_fks.py`
- `backend/dealer_ai/migrations/0009_backfill_dealership_fks.py`
- `backend/dealer_ai/tests/test_dealership.py`

Modified:

- `backend/dealer_ai/models.py` — added `Dealership` model +
  nullable `dealership` FK on 6 existing models.

Documentation touched in this session-close commit:

- `docs/handoffs/SESSION_037_milestone_1_tenancy_foundation.md`
  (this file).
- `00-START-NEXT-SESSION.md` — overwritten to point at
  SESSION_038 = Increment 3.

Not touched (correctly):

- `docs/roadmap/MILESTONE_1_PLANNING.md` — target end-state
  unchanged; deviation is sequencing-only.
- `docs/CAPABILITY_MATRIX.md` §7/§8 — auth model unchanged
  (Milestone 1 not complete).
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §2.7 — flips only
  at Milestone 1 completion.
- `docs/roadmap/DEFERRED_IDEAS.md` — no true out-of-milestone
  idea surfaced; the NOT NULL sequencing note belongs inside
  Milestone 1's Increment 3.

## Recommended scope for SESSION_038 (Milestone 1 · Increment 3)

**Goal:** propagate tenancy through the write path, then flip
FKs to NOT NULL.

**In-scope**:

1. **Resolver primitive** — new `services/tenancy.py::
   get_default_dealership()` (runtime lookup, cache-once,
   raises if missing).
2. **Extend `services/dealer_config.py`** per planning memo
   §3.9: `get_dealer_name()` / `get_dealer_profile()` gain an
   optional `dealership` arg; when omitted, resolve via
   `get_default_dealership()`. Env-override and Copper Canyon
   defaults preserved.
3. **Write-path scoping (defaults-only)**:
   - `services/inventory_import.py` — accept `dealership`
     arg; default to `get_default_dealership()`.
   - `services/chat_engine.py` — set `dealership` on
     `ChatSession` / `ChatMessage` at creation.
   - `services/lead_service.py`, `services/follow_up.py`,
     `services/handoff_service.py` — set `dealership` on
     `CustomerLead` creation.
   - `views.py` `DealerOnboardingProfile` upsert — set
     `dealership` on create.
   - `Salesperson` seeder / admin — set `dealership` on create.
4. **Migration `0010_dealership_fks_not_null.py`** — flip all
   six FKs to `null=False`.
5. **Tests** — add a shared `default_dealership()` helper (a
   base `TestCase` mixin, `setUpTestData`, or per-file
   fixture) so existing tests that construct these models
   pick up the default. Add resolver tests that exercise the
   `dealership=` arg path. The
   `test_fk_is_nullable_in_this_increment` guard in
   `test_dealership.py` will need to be inverted (or
   removed) as part of this increment.

**Explicitly out-of-scope (deferred to Increment 4+)**:

- Request-context tenant resolution (header / domain /
  authenticated-user).
- Tenant-scoped uniqueness (`(dealership, stock_number)`,
  `(dealership, slug)`, `DealerOnboardingProfile` OneToOne).
- Any endpoint auth changes.
- Any frontend changes.

**Blast radius**: medium. Touches ~5 service modules +
`views.py` + several test setUp blocks. The migration itself
is trivial once the write paths pass a default. Estimate:
one focused session.

## Anchors that win on conflict

Unchanged from SESSION_037 start:

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/MILESTONE_1_PLANNING.md`
5. `docs/BUSINESS_DOMAIN_MAP.md`
6. `docs/research/*_MAPPING.md` + `*_PIVOT.md`
7. `docs/CAPABILITY_MATRIX.md`
8. Most recent handoffs (this one +
   `SESSION_036_doc_governance_and_repo_org.md`)
9. `git log --oneline -25`

## Operational state at session close

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0009` applied. Default `Dealership` row exists
  (`slug='default'`, `name='Default Dealership'`).
- **Backend (prod):** `vehicle-match-api.onrender.com` —
  not active. Milestone 1 does not require prod.
- **Frontend (local):** Vite on `:5173`. Unchanged this
  session.
- **Frontend (prod):** none.
- **Test baseline:** 1,313 pass, 1 skipped, 0 fail.
- **Env overrides for franchise config path:** still work.

*End of SESSION_037 handoff.*
