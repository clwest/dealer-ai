---
state: active
date: 2026-07-31
last_session_shipped: SESSION_044
milestone_1_status: shipped
next_session: SESSION_045
next_milestone: 2
next_milestone_name: "Vehicle investment ledger"
---

# Next session — SESSION_045 · Milestone 2 (Vehicle investment ledger) — Increment 0 (planning pass, no code)

> **Milestone 1 shipped at SESSION_044.** Every §3 compatibility
> item verified, `CAPABILITY_MATRIX.md` §7b + roadmap §2.7 flipped
> to F, retrospective at
> `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md`. Baseline: 1,466
> pass, 1 skipped, 0 fail.
>
> **SESSION_045 opens Milestone 2 with a planning pass — no
> implementation.** Milestone 2 is "the first day the product is
> worth selling standalone to another dealer" (VCP). Do not
> start typing model code before the plan is written, reviewed,
> and committed.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2 — scope
   boundary (in-scope / out-of-scope enumeration).
4. `docs/BUSINESS_DOMAIN_MAP.md` — business-shape reference.
5. `docs/research/INVENTORY_ACQUISITION_MAPPING.md` +
   `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md` +
   `docs/research/VEHICLE_CENTRIC_PIVOT.md` (Phase 1) — the
   business truth the ledger must serve.
6. `docs/roadmap/AUTHENTICATION_MODEL.md` — every ledger row
   inherits the tenancy + authorization substrate; a new milestone
   must NOT re-derive these decisions.
7. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 — lessons that
   directly shape Milestone 2's approach (migration sequence,
   dedicated migration-check DB alias, pre-save fallback vs.
   primary write path, layer discipline, focused test matrix).
8. `docs/CAPABILITY_MATRIX.md` — what already exists.

## What Milestone 2 delivers (per `IMPLEMENTATION_ROADMAP.md`
§Milestone 2)

For any stock number, answer:

1. **What do we have invested in this vehicle right now?**
2. **What is the projected gross if we sell at the current price?**

**In scope:**

- Acquisition record (source classification: auction / trade /
  wholesale / private / off-lease / rental / repo / fleet;
  purchase price; fees; date).
- Per-vehicle cost ledger with ~25 line-item categories
  spanning acquisition / flooring / recon / admin (per VCP
  §"Investment ledger scope").
- Computed properties: `total_investment`, `expected_gross`,
  `projected_gross`, net profitability.
- Daily floor-plan interest accrual mechanism (manual re-run
  acceptable at first — async infra doesn't ship until
  Milestone 7).
- New post-LLM scrub: **acquisition-price scrub** — belt-and-
  suspenders against any ledger figure leaking to customer chat.
- One operator UI surface to inspect a vehicle's ledger.

**Explicitly out of scope:**

- Floor-plan-lender integration (manual entry ok for v1).
- Auction-feed adapters (VCP §Phase 1 does not scope them).
- Vendor negotiation workflows.
- Trade appraisal workflow (belongs to Milestone 11 sales-side).

## What SESSION_045 should do — Increment 0 (planning pass)

Mirror the shape of `MILESTONE_1_PLANNING.md`. No code this
session. The planning artifact is the deliverable.

### Recommended step sequence

1. **Read first (in this order — one pass, do not skim):**
   - `docs/PROJECT_RULES.md` (all six rules).
   - `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 (lessons) +
     §7 (deferred).
   - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
     (business objective + scope boundary).
   - `docs/research/INVENTORY_ACQUISITION_MAPPING.md` — the full
     document. Note pain #4 (aged unit paralysis), #10 (floor
     plan monitoring), #17 (over-/underbought scenarios),
     §"You make your money when you buy, not when you sell",
     §"Retail-to-Wholesale Spread = Recon + Gross + Overhead".
   - `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md` — the
     sections on cost accumulation + per-vehicle cost basis.
   - `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 1
     (~lines 258–410) — the target `VehicleAcquisition` /
     `VehicleCost` shape and the "~25 line-item categories".
   - `docs/BUSINESS_DOMAIN_MAP.md` — the accounting +
     acquisition sections.
   - `docs/roadmap/AUTHENTICATION_MODEL.md` — every ledger
     model gets a `dealership` FK + tenant-scoped querysets
     from day one. Do not re-derive.
   - `backend/dealer_ai/models.py::Vehicle` — the identity
     primitive the ledger hangs off.
   - `backend/dealer_ai/services/tenancy.py` — the tenancy
     primitives every ledger read/write flows through.

2. **Produce the planning artifact.** New file:
   `docs/roadmap/MILESTONE_2_PLANNING.md`. Mirror the section
   structure of the Milestone 1 planning doc:

   1. **§1 Design memo** — one entry per shipped subsystem
      (acquisition record; cost ledger; computed gross
      properties; floor-plan accrual mechanism;
      acquisition-price scrub; operator ledger UI surface).
      Each entry answers: **why** (with a research citation),
      **existing primitive to extend**, **what to leave
      untouched**.
   2. **§2 Migration impact review** — every existing system
      Milestone 2 touches, with the concrete work required.
      Reuse the Milestone 1 table shape.
   3. **§3 Compatibility checklist** — the acceptance contract.
      Every existing invariant Milestone 2 must uphold. Verified
      inline at Milestone 2 close, not by inference.
   4. **§4 Reusable primitives review** — extend `Vehicle`,
      extend `payment_engine` for daily accrual math, extend
      the scrub stack. No parallel implementations.
   5. **§5 Scope discipline + deferrals** — every idea that
      surfaces during planning that would expand scope, per the
      Discovery Rule.
   6. **§7 Increment sequencing** — decide before starting
      whether Milestone 2 is one increment or split. Given the
      ~25 cost categories + the acquisition-price scrub + the
      operator UI, a 3-increment split is likely (schema +
      write-path + UI/scrub); commit to a shape upfront.

3. **Confirm nothing changed in the substrate.** Grep verifies:
   `dealership` FK is present on `Vehicle` (it is, migration
   `0008`); `get_current_dealership` is stable (it is); the
   safety stack has an obvious extension seam for the new scrub
   (it does — `services/llm_safety.py`).

4. **Do NOT write code this session.** No models, no migrations,
   no service functions. The plan alone.

5. **Close SESSION_045 with:**
   - The planning artifact committed.
   - Handoff at `docs/handoffs/SESSION_045_<slug>.md`.
   - Overwrite this file (`00-START-NEXT-SESSION.md`) with the
     SESSION_046 = Milestone 2 Increment 1 priority (the
     specific sequence the planning artifact chose).

## Explicit non-goals for SESSION_045

- ❌ Do NOT write any Milestone 2 code (models, migrations,
  services, views, tests).
- ❌ Do NOT touch the 16-stage safety pipeline (Milestone 2
  ADDs one scrub in later increments; this session does not).
- ❌ Do NOT re-derive Milestone 1 decisions. Every ledger row
  gets a `dealership` FK by default; every admin endpoint that
  serves ledger data goes through
  `IsSalesManagerOrOwnerAtActiveDealership` and
  `.filter(dealership=get_current_dealership(request))`.
- ❌ Do NOT scope in floor-plan-lender integration, auction-feed
  adapters, vendor negotiation, or trade appraisal. All are
  named as out-of-scope in the roadmap.
- ❌ Do NOT scope in tenant-scoped uniqueness on
  `Vehicle.stock_number`. Deferred from Milestone 1 §5.
- ❌ Do NOT touch the `demo/*` gating decision (separate scope
  per Milestone 1 §7 retrospective).
- ❌ Do NOT commit any real `OPENAI_API_KEY` or credentials.

## NEXT TASK

Start SESSION_045 with the read-first list above. Produce
`docs/roadmap/MILESTONE_2_PLANNING.md`. Do not write code.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` (lessons for M2)
6. `docs/roadmap/MILESTONE_1_PLANNING.md` (§3 is the acceptance
   template Milestone 2 mirrors)
7. `docs/BUSINESS_DOMAIN_MAP.md`
8. `docs/research/*_MAPPING.md` + `*_PIVOT.md`
9. `docs/CAPABILITY_MATRIX.md`
10. Most recent handoffs (`SESSION_044_*.md`,
    `SESSION_043_*.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_044 — Milestone 1 closed)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0011` applied; `authtoken` migrations applied. Default
  `Dealership` row exists (`slug='default'`). No pending
  migrations.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 1 did not require prod; Milestone 2 does not
  either.
- **Frontend (local):** Vite on `:5173`. Auth flow wired
  end-to-end.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,466 pass, 1 skipped, 0 fail.
- **DRF defaults:** `SessionAuthentication` +
  `TokenAuthentication` installed; `DEFAULT_PERMISSION_CLASSES`
  intentionally unset (locked by
  `test_default_permission_classes_remain_unset`).
- **CSRF trust origins:** localhost:5173, 127.0.0.1:5173,
  localhost:3000, 127.0.0.1:3000 (env-configurable via
  `CSRF_TRUSTED_ORIGINS`).
- **Endpoint-level permission classes shipped:** advisor (4C) +
  admin (4D) surfaces.
- **Browser auth endpoints:** `/auth/{login,logout,me}`.
- **Frontend auth primitives:** `lib/authFetch.ts`,
  `lib/auth.ts`, `lib/AuthContext.tsx`,
  `components/RequireAuth.tsx`, `pages/LoginPage.tsx`. Sign-out
  button in the topbar.
- **Public / protected route split** in `src/main.tsx`:
  public = `/`, `/assistant`, `/showroom`, `/embed/assistant`,
  `/login`. Everything else is under `RequireAuth`.
- **Franchise env-override + Copper Canyon defaults verified at
  Milestone 1 close.** `DEALER_AI_DEALER_TYPE` and
  `DEALER_AI_PRIMARY_MAKE` now wired through `settings.py` (fix
  landed in SESSION_044).
- **Dev DB seeded users** (safe to keep): `smoke_owner`
  (`dealer_owner`) + `smoke_advisor` (`advisor`, linked to
  `Salesperson.slug=smoke-advisor-slug`). Password
  `smoke-pass-4e`. Not committed to source.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
  Every deferred idea from Milestone 1 is recorded in
  `MILESTONE_1_PLANNING.md` §5 + `MILESTONE_1_RETROSPECTIVE.md`
  §7.
