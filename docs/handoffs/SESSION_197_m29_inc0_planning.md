---
title: "SESSION_197 handoff — Milestone 29 · Increment 0 (M29.0 — planning refinement + target selection)"
status: historical
type: handoff
date: 2026-08-04
session: 197
milestone: 29
milestone_status: active
milestone_name: "Variable-Amount Journal Templates (on M28.1 template substrate + M27.1 gl-accounts substrate)"
increment: 0
increment_status: shipped
commit: TBD
---

# SESSION_197 — Milestone 29 · Increment 0 (M29.0 — planning refinement + target selection)

## What shipped

M29.0 opened Milestone 29 as a **direct operator-coverage
milestone** under the primary lens that has governed §5.a
selection since M22 close (durable), plus the *substrate-
compound-value continuation* framing that first validated at
M27.1 → M28.1 → M28.2. M29 is the second operator-facing
consumer of the M28.1 template substrate on top of the M27.1
gl-accounts substrate — compound value on compound value,
exactly as the M28.1 model docstring reservation predicted.
All §5 decisions locked in this session; one implementation-
boundary verification performed at open; no code changes; no
push (coordinated push deferred to M29 close).

Full active memo authored at
`docs/roadmap/MILESTONE_29_PLANNING.md`.

**Session artifacts:**

- **Starting-state verification (§1):** git clean, `HEAD ==
  origin/main @ 60af5cf` (M28 push confirmed), Redis PONG,
  Django `check` clean, `makemigrations --check` clean,
  frontend `tsc --noEmit` clean, acceptance `tsc --noEmit`
  clean. Backend suite **4,855 pass, 1 skipped, 0 fail**
  (161.6s). Frontend Vitest **270 pass** (36 files). All
  matches M28.2 close baseline exactly.
- **First M28 CI run verified (§2):** acceptance workflow on
  the M28.2-hash-backfill push completed **green in 2m36s**.
  M28 is CI-verified shipped. Five most recent acceptance
  runs on `main` all green (M24 → M28).
- **Audit regeneration (§3):** `python3 -m
  dealer_ai.scripts.audit_operational_surface` invoked.
  Output: **156 total / 122 covered / 34 backend-only / 315
  service verbs**. Byte-identical to the committed M28.2
  artifact — no drift.
- **Candidate list presented (§4)** across the M28 §9 tiers:
  - **Elevated (highest recommendation strength):** NEW
    variable-amount templates; NEW template edit / delete UI;
    NEW O2 (row-5 public-fetch-helper regex refinement); NEW
    O3 (rows-1–4 plain-string-literal investigation); H
    (test-hygiene remediation — three shared-DB non-
    idempotent journeys unchanged from M27.2 → M28.2).
  - **Gated:** T (real tester feedback); U (hosted-demo
    substrate); L (first-live-pilot staging); M (multi-
    operator support — breaks zero-drift streak).
  - **Deferred pending evidence:** D (LLM router / cost
    caps); C (F&I chargeback substrate).
  - **Deferred stable:** G (dashboard testid hardening).
  - **Deferred at M28 §3 / M27 §3 / M25 §4:** all
    carried forward unchanged.
- **Recommendation (§5):** NEW variable-amount templates,
  under the primary operational-coverage lens (depreciation
  / utilities / payroll accruals are the three most common
  recurring accounting entries that vary period-to-period)
  plus the substrate-compound-value continuation framing
  (second operator-facing consumer of the M28.1 substrate on
  top of M27.1 gl-accounts substrate).
- **User confirmation:** §5.a locked as **NEW variable-amount
  journal templates** with seven binding constraints on the
  workflow (see §6 below). Template edit / delete UI held
  as a separate candidate unless narrow correction evidence
  surfaces during M29 impl. O2 / O3 / H remain deferred
  unless fresh evidence changes their urgency.
- **§5.b D3 implementation-boundary decision (§6):**
  additive-prop pattern on `NewJournalEntryDialog`
  (`lockedLines?: readonly boolean[]`) chosen over the thin-
  wrapper alternative after inspecting the base component.
  User directive: the smallest clean design that keeps
  blank-entry workflow byte-identical to the M27.2 baseline.
- **§5 locks (all):** target (§5.a), eight load-bearing
  design decisions D1–D8 (§5.b), risk register (§5.c),
  verifications (§5.d), two-increment phasing (§5.e), DoD
  compliance (§5.f — exception path at M29.1 as fourth
  precedent, direct satisfaction at M29.2), rollback plan
  (§5.g), non-goals (§5.h).

## 1. Verification results at open

| Check | Expected | Actual |
|---|---|---|
| `git status` | clean | ✅ clean |
| `HEAD == origin/main` | true | ✅ true (60af5cf) |
| `git log --oneline -10` top | M28.2 hash backfill | ✅ 60af5cf |
| Backend suite | 4,855 pass, 1 skip | ✅ 4,855 pass, 1 skip |
| Frontend Vitest | 270 pass, 36 files | ✅ 270 pass, 36 files |
| Django `check` | clean | ✅ clean |
| `makemigrations --check` | No changes | ✅ No changes |
| Frontend `tsc --noEmit` | clean | ✅ clean |
| Acceptance `tsc --noEmit` | clean | ✅ clean |
| `redis-cli ping` | PONG | ✅ PONG |
| Audit artifact | 156 / 122 / 34 / 315 | ✅ 156 / 122 / 34 / 315 |
| First M28 CI run | green | ✅ green (2m36s) |

## 2. First M28 CI run

`Record M28.2 commit hash in SESSION_196 handoff frontmatter`
run: **completed success** in 2m36s on `main`. Five most
recent acceptance runs on `main` all green (M24 → M28). M28
is CI-verified shipped.

## 3. Audit regeneration

`python3 -m dealer_ai.scripts.audit_operational_surface`
produced **156 total / 122 covered / 34 backend-only / 315
service verbs**. Byte-identical to the committed M28.2
artifact. No drift.

## 4. Candidate list + recommendation

Full list per §4 of `docs/roadmap/MILESTONE_29_PLANNING.md`.
Recommendation and rationale in §5.a of the same memo.

## 5. §5.b–§5.h decisions locked

All eight §5.b design decisions D1–D8 locked in the memo.
D3 (instantiation UI visual distinction) is the most
detailed decision — see the memo for the full
implementation-boundary specification.

## 6. Seven binding constraints on the M29 workflow (user)

Recorded from the SESSION_197 confirmation message and
enforced across §5.b D1–D8:

1. **NULL amount → variable line semantics:** side + GL
   fixed at template-create; amount supplied at
   instantiate. D1 encodes.
2. **Instantiation fails closed until:** every variable line
   has a positive amount; every fixed line retains its
   stored amount (or an operator-confirmed override); total
   debits equal total credits; all referenced GL accounts
   remain active + tenant-valid. D1 (backend) + D3
   (frontend gate at Post button).
3. **UI distinguishes three cases:** fixed inherited; variable
   requiring input; fixed but overrideable pre-post. D3
   Option A (read-only chip + Override toggle).
4. **No silent debit/credit matching.** Operator sees + confirms
   the complete balanced JE. D4 explicit no-coupling.
5. **Two-line same-amount case must not imply auto-linkage.**
   Named / shared variables remain out of scope. D4 +
   deferral list.
6. **Template is immutable source recipe.** Instantiation or
   pre-post edits do not mutate the saved template. D5
   backend zero-writes-on-instantiate + Playwright deep-
   compare.
7. **Playwright proves the full loop:** create variable-
   amount template → instantiate visibly requests missing
   amounts → unbalanced entry blocked → balanced entry
   posts → template unchanged → JE appears in normal
   list/detail. D8 single combined `test.describe("variable-
   amount", ...)` block; journey count 19 → 20.

## 7. D3 implementation-boundary decision (recorded here for future sessions)

Two options were considered per user directive; the smaller
was chosen:

- **Option chosen: additive prop on
  `NewJournalEntryDialog`** — `lockedLines?: readonly
  boolean[]`. Safe default `undefined` → blank-entry
  behavior byte-identical. Existing regression tests pass
  unchanged. Rationale: `NewJournalEntryDialog` already
  supports optional initial-value behavior cleanly via an
  open-transition `useEffect` (lines 178–191) with a
  `reset()` on close (line 235). The read-only-chip UI
  cannot be composed from outside the base dialog without
  exposing a render slot, which is a larger surface change
  than a single additive prop.
- **Option rejected: `InstantiateJournalEntryDialog`
  wrapper.** Would either duplicate the base dialog's
  line-rendering (unacceptable) or require a render-slot
  prop (larger API change than `lockedLines`).

**Override state (`overridden: Set<number>`) reset paths
guaranteed to clear:**

1. Dialog open false → true transition (existing `useEffect`
   at 178–191 — extend to clear + add `lockedLines` to deps).
2. `initialValues` reference change (already in deps —
   extend body to clear).
3. `lockedLines` reference change (add to deps + extend
   body to clear).
4. `reset()` invocation (line 235 — extend to clear).
5. Dialog close via `onOpenChange(false)` (line 296–299) —
   already invokes `reset()`, so covered by (4).

## 8. Streaks at M29.0 close

- **Planning-time as-recommended streak:** 7 → **8**. Target
  selected as recommended after five-alternative comparison
  + one implementation-boundary verification performed.
  Historical run of 89 across M10 → M23 preserved for the
  record.
- **Zero-drift permission-class streak:** unchanged at 28
  (M10 → M28). M29.0 is planning-only; no code change.
  Projection at M29 close: 29 consecutive.
- **Substrate-compound-value continuation:** M27.1 → M28.1
  → M29 (third link).

## 9. Baselines expected at close

- Backend: 4,855 pass, 1 skip, 0 fail — unchanged from M28
  close.
- Frontend Vitest: 270 pass across 36 files — unchanged.
- Acceptance: 19 journeys — unchanged.
- Audit coverage: 122 / 156 — unchanged.
- DRF admin surface: 116 endpoints — unchanged.
- Frontend operator routes: 20 — unchanged.
- Permission classes: 7 actual — unchanged.
- Only planning docs changed:
  `docs/roadmap/MILESTONE_29_PLANNING.md` (new); this
  handoff; `00-START-NEXT-SESSION.md` (overwritten for
  SESSION_198 M29.1).

## 10. Non-goals for SESSION_197 (all honored)

- ❌ Did not ship any backend or frontend code.
- ❌ Did not open any M29 implementation increment.
- ❌ Did not force-push or amend earlier commits.
- ❌ Did not modify M1–M28 shipped surface.
- ❌ Did not modify the acceptance suite.
- ❌ Did not skip the DoD compliance check (planned:
  exception path at M29.1, direct satisfaction at M29.2).
- ❌ Did not skip the downstream / substrate / FK-
  discoverability verification.
- ❌ Did not re-litigate M28.0 architectural verifications.

## 11. What SESSION_198 (M29.1) opens

- Backend substrate relaxation per D1 + D6.
- No frontend, no acceptance change.
- DoD exception path (fourth precedent).
- Two-source agreement gate at close.
- Local commits only; coordinated push at M29 close.

See `00-START-NEXT-SESSION.md` for the SESSION_198 opening
brief.
