---
state: active
date: 2026-08-02
last_session_shipped: SESSION_151
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: shipped
milestone_11_status: shipped
milestone_12_status: shipped
milestone_13_status: shipped
milestone_14_status: shipped
milestone_15_status: shipped
milestone_16_status: shipped
milestone_17_status: shipped
milestone_18_status: in-progress
next_session: SESSION_152
next_milestone: 18
next_milestone_name: "Demo Store Simulation + Pilot Validation Readiness"
next_increment: 6
next_increment_name: "M18.6 — Close-out"
---

# Next session — SESSION_152 · Milestone 18 · Increment 6 (M18.6 — Close-out)

> **SESSION_151 shipped M18.5 —** 13
> hand-written daily briefs across the
> three archetypes + brief loader
> service verbs + TesterFeedback POST
> endpoint + CSV export end-to-end.
> Six standard-structure markers in
> every brief; the floor_planned recon
> brief walks the $1,425 F-150 overrun;
> the bhph accounting brief walks the
> M16 detector timing story; the bhph
> collector brief exercises the full
> promise-to-pay + collection-contact
> + repossession chain.
>
> **Backend baseline: 4,514 → 4,538
> pass** (+24 tests, 0 regressions).
> Frontend Vitest 140 (unchanged).
> Migrations 0043-0047 (unchanged).
> Tenancy carriers 50 (unchanged).
> **DRF admin surface 107 → 108**
> (+1 feedback POST). Frontend
> operator routes 20 (unchanged).
> Permission classes 7 — **zero-drift
> streak fourteen consecutive
> milestones** (M10 → M18.5). Celery-
> beat task families 10 (unchanged).
>
> **SESSION_152 opens M18.6 — close-
> out.** Documentation-only per
> M10.8 / M11.7 / M12.8 / M13.4 /
> M14.5 / M15.2 / M16.2 / M17.3
> precedent. Six close-out artifacts
> + one coordinated commit landing
> everything together.

## First thing SESSION_152 must do

### 1. Verify starting state

- `git status` — clean (M18.5 commit
  `957a7ba` landed at SESSION_151
  close).
- `git log --oneline -3` — top
  should be `957a7ba` (M18.5).
- `python3 manage.py test dealer_ai`
  → **4,538 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **140 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Read first (in order)

- `docs/roadmap/MILESTONE_18_PLANNING.md`
  §7 M18.6 (close-out scope).
- All five M18 handoffs
  (SESSION_146 through SESSION_151)
  — the material for the
  retrospective §2 shipped table.
- `docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
  (structure template).
- `docs/CAPABILITY_MATRIX.md` §7r
  (§7s template).
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  §Milestone 17 (M18 SHIPPED entry
  template).

## What M18.6 delivers

Per `MILESTONE_18_PLANNING.md` §7
M18.6:

### Retrospective

Write
`docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
following the M17 retrospective
structure:

- **§1 Planned scope** — six
  planning-time §5 decisions
  confirmed as-recommended at
  SESSION_146 M18.0 open;
  seven-increment sequencing
  (M18.0 → M18.6).
- **§2 What actually shipped** —
  increment table across M18.0
  planning + M18.1 substrate +
  M18.2 retail_subprime + M18.3
  floor_planned + M18.4 bhph +
  M18.5 briefs+feedback + M18.6
  close-out.
- **§3 Deferrals** — 12 M18-
  specific + 11 universal = 23
  (per §3 M18 planning) plus
  the § implementation-time
  additions:
  - Chargeback substrate (§0.a
    M18.2 decision 1) — still
    deferred permanently
    unless operator evidence
    surfaces the need. The
    F&I audit scenario belongs
    to a later milestone.
  - LLM demo cost caps (§0.a
    M18.1 decision 1) — the
    LLM guard belongs to a
    later "demo LLM cost caps"
    decision.
- **§4 Deviations** — three
  §0.a M18.2 decisions
  (Chargeback deferral, registry
  COA seeding correction,
  reverse-order + demo-owned-
  User cleanup on reset); the
  §0.a M18.1 decision 1
  (outbound-send-boundary
  enumeration finding); the
  M18.5 endpoint-count growth
  (107 → 108, first at M18);
  the recon-overrun scenario
  turning out richer than
  planned (VendorCommunication
  history added at M18.3).
- **§5 Compatibility with
  existing surface** — every
  M1-M17 endpoint returns the
  same shape it did at M17
  close; M18 is purely
  additive.
- **§6 Lessons** — expect 6-8
  per pattern:
  - Cross-domain coherence
    contract per §Store-story:
    seeded records must tell
    connected operational
    stories.
  - Scanner tests are the
    right shape for enforcing
    guard-by-construction
    contracts (M18.1 outbound
    scanner).
  - Deterministic seed
    fixtures + `reset_demo_store`
    give testers a predictable
    starting state.
  - Belt-and-suspenders
    guards (NonDemoResetError
    + assert) — proven pattern
    from M15/M16/M17 continues.
  - The 40-name synthetic
    roster is enough for four
    archetypes.
  - Markdown briefs +
    file-system loader is a
    simpler alternative to a
    briefs DB model for
    content that doesn't
    change per-tenant.
- **§7 Streak update** — 77
  planning-time as-recommended
  M5.1 → M18.0 (unchanged; six
  §5 decisions per milestone;
  M18 exceeded with seven).
  Implementation-time §0.a
  decisions across M18.1 +
  M18.2 do not count against
  streak per M10 §9.
- **§8 What M18 unblocks for
  M19+** — the M18 shipped
  surface is validation
  infrastructure. When operator
  evidence lands from real
  founder-led tester sessions,
  M19+ scopes shift based on
  what testers actually surface.
  Standing candidates from
  earlier §8 lists remain
  valid (E period-close
  comparison view, A M10
  chargeback GL reversal, etc.).
- **§9 Standing question for
  M19 close** — is M19 (or
  M20) the right slot for
  processing real tester
  feedback + shipping the
  highest-signal changes? The
  M18 substrate exists so this
  question can be answered
  with data, not intuition.

### Capability matrix

Add `docs/CAPABILITY_MATRIX.md`
§7s section describing the M18
shipped surface following §7r
template. Six-row table:

- Substrate (M18.1) — schema
  + service package + guards
  + TesterFeedback model +
  outbound-send-boundary
  scanner.
- Retail/subprime archetype
  (M18.2).
- Floor-planned archetype +
  recon overrun (M18.3).
- BHPH archetype + M16
  detector timing (M18.4).
- Briefs + feedback endpoint +
  CSV exporter (M18.5).
- Close-out surface (M18.6).

### Implementation roadmap

Add
`docs/roadmap/IMPLEMENTATION_ROADMAP.md`
§Milestone 18 SHIPPED entry
following §Milestone 17
template.

### Planning doc flip

Frontmatter update on
`docs/roadmap/MILESTONE_18_PLANNING.md`:
`status: active` → `status:
shipped`. Add
`shipped_at_session:
SESSION_151` and
`retrospective:` pointers.

### M19 skeleton

Draft
`docs/roadmap/MILESTONE_19_PLANNING.md`
skeleton per standing user
directive. Target is TBD — user
names at M19.0 open based on
operational evidence + tester
feedback + still-valid M17/M16
§8 items. Candidates from the
M18 planning §1 remain unblocked.
**Standing question**: is M19
the "process real tester
feedback" milestone, or
something else?

### Session-start refresh

Overwrite `00-START-NEXT-SESSION.md`
with M19.0 priority.

### Coordinated commit

Land all M18.6 docs together
in one coordinated commit per
M10.8 / M11.7 / M12.8 / M13.4 /
M14.5 / M15.2 / M16.2 / M17.3
precedent.

## Explicit non-goals for SESSION_152

- ❌ Do NOT ship M19.0 planning
  expansion (skeleton only).
- ❌ Do NOT modify M17 or M18
  code paths.
- ❌ Do NOT force-push or amend
  any earlier commits.

## NEXT TASK

Start SESSION_152 with (a)
starting-state verification,
(b) reading all five M18
handoffs + M17 retrospective
structure + capability matrix
§7r template, (c) writing the
six close-out artifacts +
coordinated commit landing
all M18.6 docs. Ship the
M18.6 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_PLANNING.md`
   (active memo — about to flip
   shipped)
6. `docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
   (structure template)
7. `docs/handoffs/SESSION_151_m18_inc5_briefs_and_feedback.md`
8. `docs/handoffs/SESSION_150_m18_inc4_bhph_archetype.md`
9. `docs/handoffs/SESSION_149_m18_inc3_floor_planned_archetype.md`
10. `docs/handoffs/SESSION_148_m18_inc2_retail_subprime_archetype.md`
11. `docs/handoffs/SESSION_147_m18_inc1_backend_substrate.md`
12. `docs/handoffs/SESSION_146_m18_inc0_planning.md`
13. `docs/CAPABILITY_MATRIX.md` §7r
    (template for §7s addition)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_151 — M18.5 SHIPPED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0047`. Test baseline:
  **4,538 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 140 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery 5.5.3 + Redis
  6.4.0 + `django-celery-beat` 2.8.1
  DatabaseScheduler. **10 scheduled task
  families**.
- **Milestones shipped:** M1 → M17. M18
  in progress: M18.0 through M18.5
  shipped. **M18.6 close-out next**
  (SESSION_152).
- **DRF admin surface:** **108** endpoints
  (feedback POST landed at M18.5).
- **Frontend operator routes:** **20**
  — unchanged through M18.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** complete
  `services/f_and_i/` (M10) + five
  M11 + seven M12 +
  `services/accounting/` (seven) +
  **`services/demo_store/` (ten
  modules including briefs
  package)**.
- **Tenancy carriers:** **50**.
- **Permission classes:** **7
  actual** — **zero-drift streak
  fourteen consecutive milestones**
  (M10 → M18.5).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M18 has no
  LLM path).
- **Deterministic rules:** unchanged.
- **Milestone 18 status:** M18.0 →
  M18.5 SHIPPED. **M18.6 close-out
  next** (SESSION_152).
