---
state: active
date: 2026-07-31
last_session_shipped: SESSION_053
milestone_1_status: shipped
milestone_2_status: in_progress
next_session: SESSION_054
next_milestone: 2
next_milestone_name: "Vehicle investment ledger"
next_increment: 8
next_increment_name: "Milestone 2 verification + closeout"
---

# Next session — SESSION_054 · Milestone 2 · Increment 8 (M2.8 — verification + closeout)

> **Milestone 2 · Increment 7 shipped at SESSION_053.**
> Operator ledger UI at `/dealer-ai-inventory/:stock/ledger`
> inside `<RequireAuth>`. Three typed API helpers via
> `authFetch`. Money-as-strings end-to-end; frontend never
> recomputes totals. Read-only-until-edit acquisition,
> immutable cost table with reversal badges, distinct
> 401/403/404 UX, days-in-inventory color bucket badge. Role-
> based show/hide via `useAuth()`. "Ledger" link on operator
> inventory cards (URL-encoded). Verification: `npx tsc
> --noEmit` clean, `npx vite build` clean, route smoked via
> curl (200). No component-test framework introduced (per
> brief). Manual browser smoke deferred to operator
> verification. **Backend untouched — no test-baseline
> change, no schema drift, no service-contract change.**
>
> **All eight Milestone 2 increments shipped:** M2.1 (models)
> · M2.2 (service) · M2.3 (read model) · M2.4a (financial
> engine + APR config) · M2.4b (accrual command) · M2.5
> (acquisition-price scrub) · M2.6 (admin API) · M2.7
> (operator UI). SESSION_054 closes the milestone with the
> §3 compatibility sweep + retrospective + doc flips.
>
> **SESSION_054 is documentation-only.** No code changes
> unless a §3 compatibility item fails verification. If a fix
> is needed, mirror the SESSION_044 pattern (small hardening
> in the same closeout commit).

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2 —
   scope boundary.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every M2
   invariant that inherits M1's substrate.
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` — the
   structural template M2's retrospective mirrors, plus its
   §6 lessons that Milestone 2 was expected to inherit.
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §3 (the
   compatibility checklist to walk) + §7.b (the as-shipped
   sequence to close out) + §5 (deferrals to preserve in the
   retrospective's §7).
7. `docs/handoffs/SESSION_053_milestone_2_ledger_ui.md` —
   authoritative M2.8 recommended scope.
8. Earlier M2 handoffs (SESSION_045 – SESSION_052).

## What SESSION_054 should do — M2 · Increment 8

Per `MILESTONE_2_PLANNING.md` §7.b · M2.8 + SESSION_053
handoff's "Exact recommended scope for M2.8". Mirror the
SESSION_044 closeout pattern.

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/handoffs/SESSION_053_milestone_2_ledger_ui.md` §
     "Exact recommended scope for M2.8" — authoritative
     scope + retrospective structure.
   - `docs/handoffs/SESSION_044_milestone_1_closeout.md` —
     precedent for milestone-close doc discipline.
   - `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` — the
     structural template M2's retrospective mirrors
     (frontmatter shape, §1–§8 numbering, lessons format).
   - `docs/roadmap/MILESTONE_2_PLANNING.md` §3 (walk every
     compatibility item) + §7.b (record shipped commits
     per increment).
   - Every SESSION_046 – SESSION_053 handoff (the shipped
     evidence that feeds retrospective §2 and §5).

2. **Walk the §3 compatibility checklist.** For each
   checkbox, record inline the test class / code location /
   runtime probe that locks the invariant. Same shape as the
   SESSION_044 annotation of `MILESTONE_1_PLANNING.md` §3.
   If any item fails verification:
   - Land the smallest possible fix (mirror SESSION_044's
     franchise-env-override two-line fix pattern) in the
     same closeout commit.
   - Document the pre-verification gap explicitly in the
     retrospective §4.
   - Never claim a checklist item is true if verification
     shows otherwise.

3. **Write `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md`** —
   mirror the M1 retrospective structure. Contents per
   SESSION_053 handoff § "Exact recommended scope for
   M2.8":
   - §1 What was planned
   - §2 What shipped (with commit table)
   - §3 Sequencing changes
   - §4 Deviations and why
   - §5 Regressions avoided
   - §6 Lessons learned
   - §7 Remaining deferred work
   - §8 Does the roadmap need adjustment?

4. **Update `docs/CAPABILITY_MATRIX.md`.**
   - Add §7c "Vehicle investment ledger (Milestone 2,
     shipped)".
   - Update §2.1 rows (acquisition record + per-vehicle cost
     basis) from N → F.
   - Update §2.5 row (per-vehicle cost accumulation) from
     N → F (or P if we want to signal vendor entity is M4).
   - Refresh `last_verified` + `verified_against_commit`.

5. **Update `docs/roadmap/IMPLEMENTATION_ROADMAP.md`.**
   - §Milestone 2 recommended-order paragraph — shipped
     date + retrospective link.

6. **Flip `docs/roadmap/MILESTONE_2_PLANNING.md`
   frontmatter.**
   - `status: planning` → `status: shipped`.
   - Add `shipped_at_session`, `shipped_over` (list of
     SESSION_046 – SESSION_054), `retrospective` fields.

7. **Overwrite this file** (`00-START-NEXT-SESSION.md`)
   with SESSION_055 = Milestone 3 planning-pass priority.
   Mirror the SESSION_045 pattern (planning only, no code,
   deliverable is `docs/roadmap/MILESTONE_3_PLANNING.md`).

8. **Defensive full-suite run** — a sanity that M2.8's
   doc-only changes did not accidentally touch code. Target:
   `python3 manage.py test dealer_ai` → 1,753 pass, 1
   skipped, 0 fail.

9. **Close SESSION_054 with:**
   - Handoff at
     `docs/handoffs/SESSION_054_milestone_2_closeout.md`.
   - Overwrite `00-START-NEXT-SESSION.md` (per step 7).
   - Commit the doc changes.

## Explicit non-goals for SESSION_054 (M2 · Increment 8)

- ❌ Do NOT begin the Milestone 3 planning artifact. That is
  SESSION_055 = M3 · Increment 0 (planning) — mirror the
  SESSION_045 pattern.
- ❌ Do NOT ratchet the deferred ideas into M2. Every one
  stays deferred per the Discovery Rule
  (`PROJECT_RULES.md` §Discovery Rule). Curtailment
  automation, Vendor FK, expected_gross, tenant-scoped
  stock_number uniqueness, is_available → computed,
  multi-photo storage, async infra, bulk-list optimization,
  `floor_plan_apr` Setup UI field — all stay in
  `MILESTONE_2_PLANNING.md` §5 (and now
  `MILESTONE_2_RETROSPECTIVE.md` §7) as recorded deferrals.
- ❌ Do NOT introduce new capabilities. If a §3 item fails,
  land a minimal hardening fix like SESSION_044 did for the
  franchise env-override; do not scope-creep.
- ❌ Do NOT deploy to prod. Milestone 2 does not require
  prod.
- ❌ Do NOT commit any real `OPENAI_API_KEY` or
  credentials.

## NEXT TASK

Start SESSION_054 with the read-first list above. Walk §3.
Write the retrospective. Update `CAPABILITY_MATRIX.md`,
`IMPLEMENTATION_ROADMAP.md`, and
`MILESTONE_2_PLANNING.md` frontmatter. Overwrite this
file for SESSION_055 = M3 planning. Commit. Nothing else.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` (structural
   template for M2's retrospective)
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §3 + §7.b + §5
7. `docs/handoffs/SESSION_053_milestone_2_ledger_ui.md`
   (M2.8 authoritative scope)
8. `docs/handoffs/SESSION_052_milestone_2_ledger_api.md`
9. Earlier M2 handoffs (SESSION_045 – SESSION_051).
10. `docs/handoffs/SESSION_044_milestone_1_closeout.md`
    (closeout-pattern precedent).
11. Current source code — the shipped M2.1–M2.7 surface.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_053 — M2.7 shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0014` applied. No pending migrations.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 2 does not require prod either.
- **Frontend (local):** Vite on `:5173`. Auth flow wired
  end-to-end. **Ledger page shipped this session:**
  `/dealer-ai-inventory/:stock/ledger`.
- **Frontend (prod):** NONE.
- **Test baseline (backend):** **1,753 pass** (unchanged
  from SESSION_052 — M2.7 is frontend-only), 1 skipped,
  0 fail.
- **Frontend build status:** `npx tsc --noEmit` clean;
  `npx vite build` clean (pre-existing 524KB chunk-size
  warning, unchanged from SESSION_044).
- **DRF defaults + CSRF + endpoint-level permissions:** all
  as documented in `AUTHENTICATION_MODEL.md`. Unchanged.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR`.
- **Dev DB seeded users:** `smoke_owner` (dealer_owner) +
  `smoke_advisor` (advisor). Password `smoke-pass-4e`. Not
  committed. Manual browser smoke of M2.7 uses both.
- **Milestone 2 shipped surface (all eight increments):**
  - **M2.1** models — `VehicleAcquisition`, `VehicleCost`,
    `SOURCE_*` × 8, `CATEGORY_*` × 26, admin
    registrations, migrations `0012` + `0013`.
  - **M2.2** service — `record_acquisition`, `add_cost`,
    `compute_totals`, `category_group_of`, `LedgerTotals`,
    `CrossTenantLedgerError`. Category groupings
    (`FLOORING_CATEGORIES`, `RECON_CATEGORIES`,
    `ADMIN_CATEGORIES`, `PHOTOGRAPHY_CATEGORIES`).
  - **M2.3** Vehicle read model — `@cached_property
    ledger_totals` + 9 delegator properties +
    `days_in_inventory`.
  - **M2.4a** financial engine + APR config —
    `daily_floor_plan_interest`, `get_floor_plan_apr`,
    `DealerOnboardingProfile.floor_plan_apr`, migration
    `0014`, `DEALER_AI_FLOOR_PLAN_APR` env.
  - **M2.4b** accrual command —
    `manage.py accrue_floor_plan_interest --dealership=<slug>
    [--as-of=DATE] [--dry-run]`. Workflow-owned
    idempotency via `ACCRUAL:<date>` reference tag.
  - **M2.5** safety scrub — `acquisition_price` joins
    `apply_post_llm_scrubs`, fires on every kind, runs
    AFTER `detect_unsafe_response`.
  - **M2.6** admin API — three endpoints under
    `/api/dealer-ai/admin/vehicles/<stock_number>/`
    (`ledger/` GET, `acquisition/` POST, `costs/` POST).
    Permission composition
    `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`
    (M1 · 4D class reused).
  - **M2.7** operator UI —
    `/dealer-ai-inventory/:stock/ledger` inside
    `<RequireAuth>`. Three typed API helpers via
    `authFetch`. Money-as-strings end-to-end. Role-based
    show/hide on write forms.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Every deferred idea from Milestones 1 + 2 is
  recorded in the respective planning + retrospective +
  handoff docs.
