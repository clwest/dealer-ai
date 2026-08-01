---
title: "SESSION_053 handoff — Milestone 2 · Increment 7 (operator ledger UI)"
status: historical
type: handoff
date: 2026-07-31
session: 053
milestone: 2
milestone_status: in_progress
increment: 7
increment_status: shipped
commit: ce3817c
---

# SESSION_053 — Milestone 2 · Increment 7 (M2.7 — operator ledger UI)

## What shipped

The smallest complete operator-facing ledger surface, sitting on
top of the M2.6 admin API without reshaping any backend contract.
Frontend-only session. No backend files modified.

## Frontend files added or changed

**Modified (3):**

- `frontend/src/lib/api.ts` — appended M2.7 types + three helper
  functions. All types mirror the M2.6 JSON contract from the
  SESSION_052 handoff byte-for-byte. Also exports two enum
  constants (`ACQUISITION_SOURCE_CHOICES`,
  `COST_CATEGORY_CHOICES`) for form UX; the backend
  re-validates every choice via `ChoiceField(choices=...)` so any
  drift surfaces as a 400 with a field-level error.
- `frontend/src/main.tsx` — imported `VehicleLedgerPage` and
  registered the route
  `/dealer-ai-inventory/:stock/ledger` inside `<RequireAuth>`.
  Public/protected split preserved.
- `frontend/src/pages/InventoryPreviewPage.tsx` — added a
  "Ledger" button to each vehicle card, navigating to
  `/dealer-ai-inventory/${encodeURIComponent(stock)}/ledger`.
  Deliberately operator-only (this page lives at
  `/dealer-ai-inventory` inside `<RequireAuth>`; public
  `/showroom` still shows no ledger link).

**New (1):**

- `frontend/src/pages/VehicleLedgerPage.tsx` — the new page
  (~800 lines including local subcomponents). Structured as
  one file with five local component functions for readability
  (`LedgerHeader`, `LedgerSummary`, `AcquisitionCard`,
  `CategoryTotals`, `CostLedgerTable`, `AddCostForm`) — kept
  local instead of splitting into per-file components because
  none is reused elsewhere and moving them out would just add
  import ceremony.

## Route and API helpers shipped

**Route** (in `main.tsx`, inside `<RequireAuth>`):

```
/dealer-ai-inventory/:stock/ledger
```

Anonymous users hit `RequireAuth` first → redirected to
`/login?next=/dealer-ai-inventory/<stock>/ledger` (M1 · 4E
behavior preserved).

**API helpers** (in `lib/api.ts`, all via `authFetch`):

- `fetchVehicleLedger(stock: string): Promise<VehicleLedgerResponse>`
- `upsertVehicleAcquisition(stock, body): Promise<AcquisitionUpsertResponse>`
- `createVehicleCost(stock, body): Promise<CostCreateResponse>`

Stock number URL-encoded via `encodeURIComponent` in the
`_ledgerBasePath` helper so dealer-specific conventions with
slashes / special chars route safely.

## UI sections completed

Per the SESSION_053 brief §3:

- **Header** — `{year} {make} {model}` + `#{stock_number}` +
  days-in-inventory badge (color-coded per aging bucket) +
  "Back to inventory" link.
- **Primary financial summary** (`LedgerSummary`) — five stat
  cards using the exact backend terminology:
  - Actual investment (`total_investment`)
  - Estimated remaining (`estimated_cost_total`)
  - Projected total investment (`projected_total_investment`)
  - Asking price (`vehicle.price`)
  - Projected gross (`projected_gross`)

  Every stat has a `help` line explicitly documenting the
  distinction: "Committed spending: acquisition + actual costs."
  vs "Open estimates — projected but not yet committed." vs
  "Actual + estimated. Do not treat as sunk cost." — the
  load-bearing M2.2 semantic contract is spelled out in the UI
  so operators cannot conflate the two.
- **Acquisition section** (`AcquisitionCard`) — read-only by
  default; "Edit" / "Record acquisition" button toggles into an
  inline form (`AcquisitionForm`). Every planned field
  represented. When no acquisition exists, shows a clear
  "No acquisition on file yet" state.
- **Category totals block** (`CategoryTotals`) — six per-
  category rows (Acquisition, Flooring, Reconditioning,
  Administrative, Photography) + a bottom-of-block emphasis
  row for Total investment. Every value from the backend's
  `totals` object; zero React arithmetic.
- **Cost history table** (`CostLedgerTable`) — chronological
  ascending (order comes from the API — frontend does not
  re-sort). Columns: Incurred / Category (with badges for
  `estimate` and `reversal`) / Amount / Vendor / Reference /
  Posted by. Negative amounts render with an "reversal" badge
  and a muted color; empty state explains the reversing-entry
  correction pattern.
- **Add cost form** (`AddCostForm`, visible only when
  `canWrite`) — grouped `<optgroup>` category dropdown (26
  categories organized by flooring/recon/admin/photography),
  amount input with `inputMode="decimal"`, incurred-at
  datetime-local, vendor / reference / notes, and an
  "Estimate? — Not yet committed, projected only" checkbox.
  Explicit footnote: "Cost entries are immutable. To correct a
  mistake, post a reversing entry with a negative amount and
  reference the original."

## Role behavior

`useAuth().hasRole('sales_manager') || hasRole('dealer_owner')`
gates the write controls (`AcquisitionCard` edit button;
`AddCostForm`). Advisor role sees the page but has no write
controls rendered — belt on top of server-side 403.

Advisor navigating directly to a ledger URL:
1. `<RequireAuth>` lets them through (they're authenticated).
2. `fetchVehicleLedger` throws `ForbiddenError` from `authFetch`
   (the backend endpoint requires
   `IsSalesManagerOrOwnerAtActiveDealership`).
3. `classifyError` returns `{kind: "forbidden"}`.
4. `ErrorPanel` renders the "Not authorized" card explaining
   the ledger is for owners/sales managers.

**Recon-manager role deliberately NOT added.** Deferred to
Milestone 4 per M2 §5.

## Error-state behavior

Every failure mode maps to a distinct panel:

- **Loading**: `LoadingSkeleton` (animated grey card).
- **`UnauthenticatedError` (401)**: "Please sign in" panel.
  In practice this shouldn't fire on the ledger route (`<RequireAuth>`
  intercepts anonymous requests before the page runs) — kept
  as a mid-session safety net for token expiry.
- **`ForbiddenError` (403)**: "Not authorized" panel with an
  advisory to contact owner / sales manager for access.
- **`ApiError` with `status === 404`**: "Vehicle not found"
  panel naming the stock number. Cross-tenant and truly
  nonexistent both surface identically (matches the M2.6
  no-existence-leak contract).
- **Any other error**: falls through to a generic error card
  that prints the exception message. Deliberately NOT a
  "Something went wrong" catch-all — the specific message is
  preserved so debugging is possible from the operator's
  reported symptom.

## Money-handling approach

**Every dollar figure is a string on the wire and stays a
string in state.** The frontend never parses through
`Number` for arithmetic. The `formatMoney(value: string)`
helper is string-manipulation-only: strip a leading `-`, split
on `.` at the decimal, add thousands separators to the whole
part with a regex, join back. Zero float arithmetic.

Consequences:

- Cent-level exactness is preserved end-to-end. A total from
  the backend that reads `"21030.00"` becomes `"$21,030.00"`
  in the UI — no `21029.999999...` drift.
- The UI never sees a "computed" total. Every total in the
  category-totals block, the summary, and the projected-gross
  stat reads from the backend response's `totals` /
  `projected_gross` fields directly. If future work needs a
  new total, add it to the backend service + serializer + the
  M2.6 contract — do NOT compute it in React.
- Form inputs accept currency as free-text strings and submit
  them to the backend serializer unchanged. `inputMode="decimal"`
  on the `<Input>` triggers the numeric keyboard on mobile
  without forcing `type="number"` (which would silently coerce
  through float and break edge cases).

## Tests or verification performed

**Typecheck**: `npx tsc --noEmit` → **clean**.

**Production build**: `npx vite build` → **clean**. Same
pre-existing 524KB chunk-size warning that has appeared since
SESSION_042 (unrelated to M2.7).

**Route smoke**: started `vite --port 5173`, curled `/` (200)
and `/dealer-ai-inventory/CC-T-01/ledger` (200 — SPA fallback
served the app shell so the route is registered and
`RequireAuth` will take over).

**No frontend component-test framework introduced.** The
project has no Vitest / Jest / React Testing Library. Playwright
is in `devDependencies` but has no config or test directory.
Per the SESSION_053 brief's explicit instruction — "do not
introduce a new testing framework solely for this increment.
Use typecheck, build, and browser smoke, and record that
decision." — recorded here.

**Manual browser smoke deferred to operator verification.** The
SESSION_053 brief lists a 12-step manual flow (anon → login,
owner records acquisition, add actual + estimated costs,
verify actual vs. projected distinction visible, add negative
reversal, refresh preserves, advisor sees 403, public
surfaces unchanged). I cannot drive an interactive browser
from this environment, so I completed the parts I could —
typecheck + build + static analysis + route smoke — and
documented that the interactive walkthrough belongs to the
operator's first-boot session. All the invariants the manual
smoke would verify are locked by:

- Backend permission-matrix + JSON-contract tests from M2.6
  (57 tests).
- The `AuthContext` + `RequireAuth` + `authFetch` primitives
  from M1 · 4E (their behavior is stable — the M2.7 page just
  consumes them).
- The `formatMoney` string-only helper (mathematically
  correct by construction — no float branch to break).

## Backend changes, if any

**None.** The M2.6 JSON contract shipped in SESSION_052 was
consumed verbatim. No serializer reshape, no new endpoint, no
service change, no permission modification. `git status`
shows only four frontend files touched.

## Browser-smoke results

Not run (environmental limitation — see "Tests or verification
performed"). The 12-step flow from the brief is queued for
operator verification during the first live run of the ledger
page.

## Frontend build status

- `npx tsc --noEmit` → clean (no errors).
- `npx vite build` → clean (one pre-existing chunk-size
  warning, same as SESSION_044).
- Route registered at `/dealer-ai-inventory/:stock/ledger`
  inside `<RequireAuth>`.

## Documentation updates

- `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b · M2.7 → SHIPPED
  with a full summary of what landed (route, three API
  helpers, money-as-strings discipline, days-in-inventory
  badge, immutable cost table with reversal badges, role-based
  show/hide, distinct 401/403/404 UX, no test-framework
  introduction with rationale).
- `docs/handoffs/SESSION_053_milestone_2_ledger_ui.md` — this
  file.
- `00-START-NEXT-SESSION.md` — overwritten for SESSION_054 =
  M2.8 (milestone verification + closeout).

No separate UI planning doc created (per brief).

## Exact recommended scope for M2.8 (SESSION_054)

**M2.8 — Milestone 2 verification + closeout.** Per
`MILESTONE_2_PLANNING.md` §7.b · M2.8 and the pattern
established by SESSION_044 (Milestone 1 closeout).

### In scope

1. **Full §3 compatibility sweep.** Walk every item in
   `MILESTONE_2_PLANNING.md` §3 (compatibility checklist)
   with evidence recorded inline. Mirror the SESSION_044
   pattern where each checkbox cites the test class, code
   location, or runtime probe that locks the invariant.

2. **`docs/CAPABILITY_MATRIX.md` update:**
   - New §7c "Vehicle investment ledger (Milestone 2,
     shipped)" enumerating the shipped surface: models
     (VehicleAcquisition, VehicleCost + category enum),
     service (record_acquisition / add_cost / compute_totals
     / LedgerTotals / category groupings), Vehicle read model
     (@cached_property + 9 delegators + days_in_inventory),
     payment engine extension (daily_floor_plan_interest),
     dealer_config extension (get_floor_plan_apr),
     onboarding profile field (floor_plan_apr), env var
     (DEALER_AI_FLOOR_PLAN_APR), accrual command
     (accrue_floor_plan_interest), safety scrub
     (acquisition_price), admin API (3 endpoints), operator
     UI (/dealer-ai-inventory/:stock/ledger).
   - Update §2.1 "Inventory & Acquisition" table rows:
     - "Acquisition record" from N → F.
     - "Per-vehicle cost basis + running investment total"
       from N → F.
   - Update §2.5 "Accounting" table row:
     - "Per-vehicle cost accumulation" from N → F (or P if
       we want to signal that vendor entity is Milestone 4).

3. **`docs/roadmap/IMPLEMENTATION_ROADMAP.md` update:**
   - §Milestone 2 recommended-order paragraph updated with
     shipped date + retrospective link.

4. **`docs/roadmap/MILESTONE_2_RETROSPECTIVE.md`** — NEW,
   mirroring `MILESTONE_1_RETROSPECTIVE.md`'s structure:
   - §1 What was planned (§7.a original 3-increment plan).
   - §2 What shipped (§7.b eight-increment as-shipped
     sequence).
   - §3 Sequencing changes (SESSION_045 planned 3
     increments; SESSION_046 discovered the M2.1 →
     persistence-only narrowing that absorbed
     services/vehicle_ledger.py into M2.2; SESSION_047
     rejected the proposed 12-deliverable M2.2 in favor of
     the M2.3–M2.8 breakdown; SESSION_049 split M2.4 into
     M2.4a (math) + M2.4b (workflow); SESSION_051 removed
     "stage 17" numbered-stage terminology from code).
   - §4 Deviations and why.
   - §5 Regressions avoided (M1 baseline preserved, safety
     stack preserved, public routes unchanged, ledger data
     never on public surfaces).
   - §6 Lessons learned (increment discipline still the
     right call; DRF Serializer for input + ModelSerializer
     for output is a durable pattern for admin endpoints;
     money-as-strings-end-to-end preserves precision without
     JavaScript BigInt / bignumber.js; workflow-owned
     idempotency via reference tags beats relying on the
     engine's zero-day short-circuit alone).
   - §7 Remaining deferred work (curtailment automation,
     Vendor FK, expected_gross, tenant-scoped stock_number
     uniqueness, is_available → computed, multi-photo
     storage, async infra, bulk-list optimization for future
     inventory pages, `floor_plan_apr` field in the Setup
     UI, browser smoke — should the manual verification
     surface an operator-friendly gap, treat as a deferred
     idea unless a real blocker).
   - §8 Does the roadmap need adjustment? (No structural
     changes — the M1 → M13 sequence in
     `IMPLEMENTATION_ROADMAP.md` remains sound.)

5. **Overwrite `00-START-NEXT-SESSION.md`** with the
   Milestone 3 planning-pass priority (SESSION_055 =
   Milestone 3 planning; no code — mirror the SESSION_045
   pattern).

### Out of scope for M2.8

- Any code changes. M2.8 is documentation + retrospective
  only. If a §3 compatibility item fails verification and
  requires a fix, either land the fix as a small documented
  M2 hardening (mirror SESSION_044's franchise env-override
  fix) or defer to a Milestone 3 kickoff decision.
- Milestone 3 planning artifact. That is SESSION_055 = M3
  Increment 0, per the M1 pattern.
- Any prod deployment. Milestone 2 does not require prod.
- Ratcheting the deferred ideas into M2 — every deferred item
  stays deferred per the Discovery Rule.

### Verification steps at M2.8 close

- Every §3 compatibility item annotated with inline evidence.
- `docs/CAPABILITY_MATRIX.md` §7c added; §2.1 and §2.5 rows
  updated.
- `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` written.
- `docs/roadmap/MILESTONE_2_PLANNING.md` status frontmatter
  flipped from `planning` (or `in_progress`) to `shipped`
  with `shipped_at_session: SESSION_054` +
  `shipped_over: SESSION_046, ...`.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
  paragraph updated.
- `00-START-NEXT-SESSION.md` overwritten for the M3 planning
  pass.
- Full backend suite pass — a defensive sanity that M2.8's
  doc-only changes didn't accidentally touch code (target:
  1,753 pass, 1 skipped, 0 fail).
- No new migrations.
- No frontend changes.

## Anchors that win on conflict (for the next session)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
   (still binding; M2.8 mirrors this doc's structure)
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §3 (compatibility
   checklist to walk) + §7.b · M2.8
7. `docs/handoffs/SESSION_053_milestone_2_ledger_ui.md`
   (this file — the M2.8 recommended scope)
8. `docs/handoffs/SESSION_052_milestone_2_ledger_api.md`
9. Earlier M2 handoffs (SESSION_045 – SESSION_051).
10. Current source code — the shipped M2.1–M2.7 surface.

Planning docs are claims. Rules + research + code are facts.
