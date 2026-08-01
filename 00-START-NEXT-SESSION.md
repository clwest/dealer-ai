---
state: active
date: 2026-08-01
last_session_shipped: SESSION_064
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
next_session: SESSION_065
next_milestone: 4
next_milestone_name: "Recon automation"
next_increment: 0
next_increment_name: "M4.0 — Milestone 4 planning pass"
---

# Next session — SESSION_065 · Milestone 4 · Increment 0 (M4.0 — planning pass)

> **Milestone 3 shipped in full at SESSION_064.** Test baseline
> **2,124 pass** (+371 from M2 close). Ten shipped increments
> (M3.0 → M3.8). See
> `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` for the full
> retrospective and
> `docs/handoffs/SESSION_064_m3_inc8_closeout.md` for the
> closeout details + milestone audit (4 questions answered
> with evidence).
>
> **SESSION_065 opens Milestone 4 with a planning-only pass.**
> Mirrors M2.0 (SESSION_045) and M3.0 (SESSION_055): write
> `docs/roadmap/MILESTONE_4_PLANNING.md`, resolve any
> load-bearing pre-implementation decisions, sequence 6-8
> increments. **No code. No migration. No implementation.**

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4 —
   scope boundary + business objective.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every M4
   endpoint inherits the four-layer separation; M4 first
   surfaces `recon_manager` role (see M3 retro §8).
5. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §8 —
   engineering context M4 inherits from M3.
6. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6 +
   `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 — durable
   engineering lessons (increment discipline, backend-first,
   provider-neutral, service ownership, honest verification,
   storage-first deletion, document refinements immediately).
7. `docs/roadmap/MILESTONE_3_PLANNING.md` +
   `MILESTONE_2_PLANNING.md` — shape templates for the M4
   planning artifact.
8. `docs/research/RECON_MAPPING.md` §3–§7 + §11 — the
   business-truth source for M4 subsystems (recon planning
   framework; vendor management; parts procurement; workflow;
   vendor communications).
9. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 3 (M4
   phase).

## What M4.0 delivers

**Documentation-only.** Writes
`docs/roadmap/MILESTONE_4_PLANNING.md`. Mirror the shape
`MILESTONE_2_PLANNING.md` + `MILESTONE_3_PLANNING.md` proved
out — eight sections:

1. **Engineering practices to preserve** — synthesized from
   M2 + M3 retros §6 lessons (10 lessons carried forward).
2. **Design memo** — subsystems M4 will ship, each answering
   *what business question does this answer? which existing
   primitive does it extend? what does it leave untouched?*
   Cited to research (`RECON_MAPPING.md` §3 recon planning,
   §4 vendor management, §6 parts procurement, §7 workflow,
   §11 vendor communications).
3. **Migration impact review** — every existing surface M4
   touches with required work. Includes recon-manager
   permission-class addition, `Vendor` model
   (promotes M2 `VehicleCost.vendor` free-text to FK),
   `WorkOrder` model, new post-LLM scrub for vendor-email
   drafting.
4. **Compatibility checklist** — invariants M4 must preserve
   from M1 + M2 + M3.
5. **Reusable primitives review** — what M4 extends vs.
   what it parallels. M3 primitives to reuse:
   `Vehicle.latest_completed_condition_report`,
   `ConditionFinding.estimated_cost`, storage abstraction
   (M3.4), condition-report service (M3.2).
6. **Scope discipline + deferrals** — including any
   load-bearing pre-implementation decisions (analogous to
   M3.5.a storage-story analysis):
   - **Recon-manager role shape** — split further into
     `recon-manager` vs `recon-tech`? Or single role?
   - **Work-order lifecycle** — service layer or FSM
     library?
   - **Vendor entity** — promote `VehicleCost.vendor` to
     FK now or defer?
   - **AI vendor-email drafting** — new post-LLM scrub for
     vendor-facing text (analogous to M2.5
     `_scrub_acquisition_price` for internal cost data).
   - **Findings → work-order → estimate `VehicleCost` seam**
     — how does the M2 ledger's `is_estimate=True` flow tie
     in?
   - **First-live-prod deployment** — M4 is likely the
     first milestone requiring prod (vendor emails go
     outbound; RECON §12.2 sign-off happens at the store).
     Include a "prod-readiness pre-work" increment if
     needed.
7. **Anchors that win on conflict** — same shape M3 used.
8. **Increment sequencing** — 6-8 increments, one per
   session, each with focused tests + full-suite
   verification at boundary. Same shape M3.6 A/B split
   discipline; do not preemptively bundle.

**Explicit non-goals for M4.0:**

- ❌ Any code change (backend or frontend).
- ❌ Any migration.
- ❌ Any test file change.
- ❌ Drafting `services/recon_plan.py`, `models.Vendor`, or
  any implementation module.
- ❌ Modifying M3.1–M3.7 shipped surfaces.
- ❌ Introducing any AI role — that's an M4 increment, not
  M4.0.
- ❌ Overriding the M3 retrospective's §8 bootstrap
  guidance without an explicit reason.

## What SESSION_065 should do

### Recommended step sequence

1. **Read first (in order — one pass, do not skim):**
   - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
     (business objective + operational pain + gap +
     scope boundary).
   - `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` — full
     document. §8 M4 bootstrap is the load-bearing input.
   - `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons
     (carry-forward set for M4).
   - `docs/research/RECON_MAPPING.md` — full document if
     time permits; at minimum §3 (recon planning +
     three-tier framework), §4 (vendor management), §6
     (parts procurement), §7 (workflow), §11 (vendor
     communications).
   - `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 3.
   - `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.8 SHIPPED
     annotation — the shape M4.0 mirrors.
   - `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b — the
     alternate 8-increment shape (M2.0 briefed a 3-increment
     plan that was corrected to 8; M3.0 briefed 8 directly
     and shipped 9 due to M3.6 split; M4 should be planned
     with the 8-increment discipline from the start).

2. **Verify starting state.**
   - `git status` clean (or only pre-existing untracked).
   - `python3 manage.py test dealer_ai` → **2,124 pass, 1
     skipped, 0 fail**.
   - `python3 manage.py check` clean.
   - `python3 manage.py makemigrations --check --dry-run` →
     "No changes detected."
   - `npx tsc --noEmit` clean.
   - `npx vite build` clean.

3. **Draft `MILESTONE_4_PLANNING.md`** — the whole document.
   Aim for 1,000-2,000 lines depending on the number of
   load-bearing decisions that need pre-implementation
   resolution.

4. **Add a bootstrap handoff** at
   `docs/handoffs/SESSION_065_m4_planning.md` (mirrors
   `SESSION_055_milestone_3_planning.md`).

5. **Overwrite `00-START-NEXT-SESSION.md`** with the
   SESSION_066 = M4.1 priority (whatever the M4 §7 §7 M4.1
   entry defines).

## Explicit non-goals for SESSION_065

- ❌ Do NOT modify any backend or frontend code file.
- ❌ Do NOT run any migration.
- ❌ Do NOT add new tests.
- ❌ Do NOT modify M3 planning / retrospective / capability
  matrix rows — M3 is closed.
- ❌ Do NOT reopen the M2 semantic contracts.
- ❌ Do NOT introduce any AI role (deferred to a specific
  M4 increment inside M4.0's sequencing).
- ❌ Do NOT commit any real credentials.

## NEXT TASK

Start SESSION_065 with the read-first list above. Write the
full `MILESTONE_4_PLANNING.md` planning artifact. Resolve
any load-bearing pre-implementation decisions inside §6.
Sequence 6-8 increments. Ship the planning-pass bootstrap
handoff.

Backend baseline at SESSION_065 close: **2,124 unchanged**.
Frontend baseline: unchanged.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §8 (M4
   bootstrap) + §6 (lessons)
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 (lessons)
7. `docs/roadmap/MILESTONE_3_PLANNING.md` +
   `MILESTONE_2_PLANNING.md` (shape templates)
8. `docs/research/RECON_MAPPING.md` §3-§7 + §11
9. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 3
10. `docs/CAPABILITY_MATRIX.md` §7c + §7d (M2 + M3 surface)
11. Most recent handoffs
    (`SESSION_064_m3_inc8_closeout.md`,
    `SESSION_063_m3_inc7_operator_ui.md`,
    `SESSION_062_m3_inc6b_photo_api.md`,
    `SESSION_061_m3_inc6a_admin_api.md`,
    `SESSION_060_m3_inc5_upload_flow.md`,
    `SESSION_059_m3_inc4_storage.md`,
    `SESSION_058_m3_inc3_read_model.md`,
    `SESSION_057_m3_inc2_service_layer.md`,
    `SESSION_056_m3_inc1_core_models.md`,
    `SESSION_055_milestone_3_planning.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_064 — Milestone 3 shipped in full)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015`. Test baseline: **2,124 pass**, 1 skipped,
  0 fail.
- **Backend (prod):** NOT active (M4 is likely the first
  milestone requiring it).
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  clean. `vite build` clean.
- **Frontend (prod):** NONE.
- **DRF defaults + CSRF + permissions:** unchanged.
- **Env-override surface:** unchanged (M3.4 additions
  optional — `AWS_STORAGE_BUCKET_NAME` etc. all documented).
- **Milestone 3 shipped surface:** COMPLETE. All 8
  sub-increments SHIPPED. `MILESTONE_3_PLANNING.md`
  frontmatter `status: shipped`.
  `MILESTONE_3_RETROSPECTIVE.md` written.
  `CAPABILITY_MATRIX.md` §7d added.
  `IMPLEMENTATION_ROADMAP.md` §M3 SHIPPED; §M4 active.
- **Milestone 4 status:** ready for M4.0 planning-pass
  drafting. No planning artifact exists yet;
  `MILESTONE_4_PLANNING.md` is what SESSION_065 creates.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Every deferral has a home in an existing
  planning / retrospective / handoff doc.
- **Dev DB seeded users:** `smoke_owner` + `smoke_advisor`.
  Unchanged.
