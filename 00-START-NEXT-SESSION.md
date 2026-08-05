---
state: active
date: 2026-08-05
last_session_shipped: SESSION_218
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
milestone_18_status: shipped
milestone_19_status: shipped
milestone_20_status: shipped
milestone_21_status: shipped
milestone_22_status: shipped
milestone_23_status: shipped
milestone_24_status: shipped
milestone_25_status: shipped
milestone_26_status: shipped
milestone_27_status: shipped
milestone_28_status: shipped
milestone_29_status: shipped
milestone_30_status: shipped
milestone_31_status: shipped
milestone_32_status: shipped
milestone_33_status: shipped
milestone_34_status: shipped
milestone_35_status: shipped
next_session: SESSION_219
next_milestone: 36
next_milestone_name: "(target selection pending — locked at M36.0 open)"
next_increment: 0
next_increment_name: "M36.0 — Planning refinement + target selection"
---

# Next session — SESSION_219 · Milestone 36 · Increment 0 (M36.0 — planning refinement + target selection)

> **Milestone 35 — Lender Submission Activation — SHIPPED at
> SESSION_218.** M35.0 planning + M35.1 backend + M35.2 frontend
> + Playwright all landed. Backend baseline 5,021 → 5,045.
> Frontend Vitest 402 → 431 across 47 files. Acceptance 25 → 26
> spec files / 32 → 33 tests / 46.3s fresh-DB run. Audit at
> M35 close: **163 / 134 / 29 / 321** (+1 total, +3 covered,
> -3 backend-only, service verbs unchanged).
>
> **Third link in the F&I depth arc** (M32 + M33 + M35). M34
> was an intentional deferral-close pause; M35 resumes.
> Activated the M10.3 substrate operationally 110 sessions after
> it shipped at SESSION_108 — new project record for longest
> substrate-to-UI gap (surpasses M33's 19-session record on
> M10.2 DealStructure).
>
> **First re-application of durable lesson (ff)** at M35.2.
> Submission Sasha seed idempotent from first shipping day;
> `@rerun-hygiene` tag count 3 → 4; back-to-back double-run
> proof passed (11/25.8s + 11/19.5s). **(ff) now load-bearing-
> across-two-milestones** (M34.0 origin + M35.2 re-application).
>
> **Zero-drift permission-class streak 38 → 39** (M10 → M35).
> M35.1 D4 new endpoint reused `_M101_PERMS`; M35.2 added no
> backend endpoints.
>
> **Two §0.a M35.2 amendments applied** — (A) backend
> `latest_lender_submission_id` annotation gap discovered
> during D8 frontend implementation, resolved via small in-
> session backend amendment; (B) test isolation bug in
> `DealerFandIIncoming.test.tsx` (`vi.clearAllMocks` doesn't
> clear queued `mockResolvedValueOnce`) resolved via
> `vi.resetAllMocks` switch. Both preserve the discipline of
> resolving implementation-time gaps in-session.
>
> **Coverage-projection truthfulness (cc) seventh invocation**
> at M35.2 close — audit projection locked from direct artifact
> inspection at M35.0 planning; observed at close matches
> verbatim. (cc) continues to hold as load-bearing-across-
> three-milestones.
>
> **DoD exception path invocation #12** at M35.1; **direct
> satisfaction** at M35.2 via `fandi_submission_response_loop.spec.ts`.
>
> **F&I downstream chain now unblockable.** With LenderSubmission
> operational, Stipulation / Contract / BEPA / Funding /
> Chargeback / Compliance / DealJacket UI candidates are all
> technically unblocked. They remain deferred per M35 §5.h until
> their own scope decisions surface. Each subsequent F&I arc
> continuation gets cheaper (no new substrate needed).
>
> **Standing question at M36.0** (per M34 §9 preserved + M35 §9
> update): three natural next moves — (a) **continue F&I depth
> arc** at 4 links via NEW C chargeback substrate (first M10.6
> UI activation) OR NEW F&I workflow-state extensions
> (Contract/Funding UI + derived state extension to 8-state
> chip); (b) **reset to breadth** via a fresh direct-operator
> gap; (c) **close another §3 deferral** per M34 precedent. F&I
> arc's compound value has grown significantly at M35 —
> unblocking the M10.5–M10.7 substrate makes each continuation
> cheaper.
>
> **Coordinated M35 close push pending.** All M35 work is
> local-only; awaits explicit user confirmation. Expected M35
> commits at push: **6** (M35.0 planning `f17e1eb`; M35.0 hash-
> backfill `50755f3`; M35.1 backend `17fa3b8`; M35.1 hash-
> backfill `22ae5c1`; M35.2 frontend + Playwright (SESSION_218);
> M35.2 hash-backfill follow-up).
>
> **SESSION_219 opens M36.0 — planning refinement + target
> selection.** The assistant recommends one option with rationale
> grounded in the primary operational-coverage lens (durable
> since M22 close); the user confirms or redirects. Verification-
> driven revision cycles at planning-open (z — now load-bearing-
> across-three-milestones after M35.0's 10-correction invocation)
> anticipates user revision rounds strengthening the locked
> design if they surface.

## First thing SESSION_219 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches `origin/main`
  post-M35 push (if pushed) OR local `HEAD` ahead by 6 commits
  (SESSION_216–218 planning + impls + hash-backfills) if push
  not yet executed.
- `git log --oneline -10` — top should be the M35.2 hash-
  backfill commit; check for expected M35 commit sequence.
- `python3 manage.py test dealer_ai` → **5,045 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **431 pass** across 47 files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive reset per
  SESSION_200 §0.a durable lesson (v).

### 2. If M35 pushed — monitor first M35 CI run

If M35 has been pushed, verify the CI acceptance workflow
status via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as §0.a M36.0 amendments before opening
§5.a.

**If green:** M35 is CI-verified shipped; proceed to §3.

### 3. Regenerate the audit artifact

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Expected: **163 / 134 / 29 / 321** unchanged (M35 adds no
endpoints at M36.0). If the artifact drifts, investigate before
scope-locking.

### 4. Present the M36 candidate list

Per the M35 close + M34 §9 evidence:

**Elevated (highest recommendation strength at M36.0 — F&I
arc newly-cheap post-M35):**

- **NEW C — F&I chargeback substrate** (pilot-evidence gated;
  strongest post-M35 context — LenderSubmission unblocks the
  downstream chain including M10.6 Chargeback substrate).
- **Contract UI (M10.5)** — first M10.5 activation candidate;
  unblocked by M35 LenderSubmission activation.
- **Funding UI (M10.5)** — second M10.5 activation candidate;
  requires Contract for a natural workflow order.
- **Stipulation UI (M10.4)** — first M10.4 activation candidate;
  attached to LenderSubmission → unblocked by M35.
- **NEW F&I workflow-state extensions beyond M35's four new
  derived states** (Contracted / Funded via M10.5 substrate
  activation → 8-state chip).
- **Lender Fit Recommendations** (D10 elevation; three of four
  blockers remain — M35 did NOT deliver the fourth; rule /
  attribute retrieval remains gated).
- **NEW F&I-scoped lead-context view** (M32 §3 deferral).
- **Cross-lead sales-manager pending-approval queue** (M32 §3
  deferral).
- **Direct-create CA structuring branch** (M33 §5.h deferral).
- **Iteration UX** (M33 D9 deferral).
- **PATCH on DealStructure** (M33 activation-vocabulary).
- **Alternate-lender resubmission** (M35 §5.h deferral).
- **Submission history view** (M35 §5.h deferral).
- **Structured `counter_terms` / `approval_terms` capture** (M35
  §5.h deferral).
- **LenderProgram create UI** (M35 §5.h deferral).
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (10-milestone deferral).
- **NEW O3 — Rows 1–4 plain-string-literal investigation**
  (10-milestone deferral).

**Shipped since M34 §9:**

- ~~**Lender Submission Activation**~~ SHIPPED at M35.

**Fresh direct-operator gaps to survey (breadth candidates):**
vendor detail (#43); photo reorder (#65); broader F&I subdomain
(#89–101 excl. #94 lender-programs list + #95 lender-submissions
POST + #96 lender-submissions PATCH — 8 uncovered post-M35).

**Gated:** T, U, L, M.
**Deferred pending evidence:** D.
**Deferred stable:** G.
**Deferred at M35 §5.h + M34 §3 / M33 §3 / M32 §3 / M31 §3 /
M30 §3 / M29 §3 / M28 §3 / M27 §3 / M25 §4:** all carried
forward unchanged.

Present each with two-sentence scope + operator pain resolved
+ dependency notes, then present the recommendation.

### 5. Recommend a target for §5.a

Ground the recommendation in the **primary operational-
coverage lens** OR its reframes (F&I depth-arc continuation
per M32 + M33 + M35 precedent; "close a deferral" per M34
precedent) if evidence supports.

**Standing question from M34 retrospective §9 updated at M35
close:** three natural next moves — (a) continue F&I depth arc
at 4 links (NEW C chargeback / Contract UI / Funding UI /
Stipulation UI / NEW workflow-state extensions / Lender Fit if
evidence surfaces); (b) reset to breadth via a fresh direct-
operator gap; (c) close another §3 deferral (per M34 precedent).
Evaluate through the primary operational-coverage lens first;
secondary reframes only if evidence surfaces.

**Alternatively:** if the M35 CI run surfaces regression work
at M36.0, address as §0.a amendments first.

### 6. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the standard load-bearing decisions per
M28/M29/M30/M31/M32/M33/M34/M35 shape.

### 7. Verify BOTH intake AND downstream UI surfaces + FK discoverability before locking §5.b + §5.d

**M24.1-open + M25.0 + M25.2-open + SESSION_189 §3 +
SESSION_190 §2 + M27.0 §7 + M28.0 §7 + M29.0 §7 + M30.0 §7 +
M31.0 §7 + M32.0 §4 + M33.0 §4 + M34.0 §4 + M35.0 §4 durable
lesson.** Every planning-open surface verification must cover
both intake AND downstream paths, including audit-substrate
accuracy checks + FK / identifier discoverability for any
create/edit workflow candidate + role-access verification for
any cross-role UI + field-level prepopulation truthful-entry
check for any form candidate.

**Verification-driven revision cycles discipline (z — load-
bearing-across-three-milestones)** — multiple user-directed
revision rounds at §5.b–§5.h before scope-lock are acceptable
and often strengthen the milestone. M35.0's ten-correction
invocation demonstrated the discipline continues to demonstrate
value even under substantial revision loads.

**Coverage-projection truthfulness (cc — load-bearing-across-
three-milestones)** — at §5.e phase-projection lock AND at
§5.b tool-usage/proof-mechanism claim locks, name the specific
semantic being invoked and validate the projection/claim
against a concrete recent precedent OR an empirical test
before locking scope.

**(ff) rerun-safety-against-shared-state — load-bearing-
across-two-milestones after M35.2** — at planning-open
verification for any journey add or extension, name concrete
invariants the journey depends on and confirm the seed
restores them across mutations the journey applies.

### 8. DoD compliance check

Per the M21.0 §5.f amendment: the M36 active memo §3 must
either name a Playwright journey addition or extension OR
explicitly document why no journey change is required (M26 +
M27.1 + M28.1 + M29.1 + M30.1 + M31.1 + M32.1 + M33.1 + M34.1
+ M34.2 + M35.1 precedents for the exception path — pattern
firmly established at twelve invocations; M35.2 is the eleventh
direct satisfaction).

### 9. Expand M36 planning skeleton

Draft fresh per the standard active-memo shape (no existing
skeleton at close of M35).

### 10. Ship the M36.0 handoff

- `docs/handoffs/SESSION_219_m36_inc0_planning.md`.
- **Do NOT push** — M36.0 is planning only; coordinated push
  at M36 close.

## Non-goals for SESSION_219

- ❌ Do NOT ship any backend or frontend code — planning-only
  session.
- ❌ Do NOT open any M36 implementation increment.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M35 shipped surface.
- ❌ Do NOT modify the acceptance suite unless CI regression
  fixes land as §0.a M36.0 amendments.
- ❌ Do NOT skip the DoD compliance check.
- ❌ Do NOT re-open the M35 first-loop boundary (same-record
  status update; new-submission / alternate-lender / history /
  multi-submission mgmt deferred).
- ❌ Do NOT re-open the (ff) `@rerun-hygiene` tag or back-to-
  back double-run proof mechanism — both load-bearing across
  two milestones.
- ❌ Do NOT modify the M35 four-layer language contract or its
  prohibited-strings list.

## Baseline expected at close

Backend + frontend + acceptance unchanged from M35.2 close.
Only planning docs change.

## NEXT TASK

Start SESSION_219 with (a) starting-state verification;
(b) if M35 pushed, monitor first M35 CI run + fix any
regressions as §0.a M36.0 amendments; (c) regenerate the
audit artifact and confirm 163/134/29/321 holds;
(d) present the candidate list with recommendation +
rationale under the primary operational-coverage lens (with
F&I depth-arc continuation at 4 links vs breadth-reset vs
close-another-deferral framing per M35 §9 standing question);
(e) await user confirmation of §5.a; (f) draft §5.b–§5.h
with verification-driven revision cycles anticipated per
(z); (g) DoD compliance check on §3 draft; (h) expand the
M36 planning memo; (i) ship the M36.0 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_35_PLANNING.md`** §5 + §9 (M36
   candidate list origin + F&I depth-arc standing question
   updated at M35 close)
6. `docs/roadmap/MILESTONE_34_RETROSPECTIVE.md` §9 (preserved
   candidate list + F&I depth-arc framing)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (post-M35
   baseline **163 endpoints / 134 covered / 29 backend-only /
   321 service verbs**)
8. `docs/roadmap/MILESTONE_10_PLANNING.md` §1.4 + §1.5 + §1.6
   + §1.7 (Stipulation / Contract / Funding / Chargeback /
   Compliance substrate contracts — now candidates for
   activation)
9. `docs/CAPABILITY_MATRIX.md` §7ι (M34); §7κ added at M35
   close
10. `docs/handoffs/SESSION_218_m35_inc2_frontend.md` (M35.2
    shipped + M35 close-out)
11. Memory record
    `feedback_playwright_as_operational_contract.md` (M35.2
    re-applied at D9 + D10 + back-to-back proof)
12. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — re-invoked at M35.2 §0.a Amendment A)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_218 — Milestone 35 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0051` (unchanged). Test baseline: **5,045 pass**, 1
  skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest baseline: 431 pass** across 47
  test files.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS 5.6
  operational; **26 journeys** total (M35.2 added
  `fandi_submission_response_loop.spec.ts`).
- **Acceptance (CI):** live; latest run on `origin/main`
  `c76e6db` (M34.2) — success in 3m1s at 2026-08-05T14:25:46Z.
  First M35 CI run pending on M35 push.
- **Async runtime:** unchanged.
- **Milestones shipped:** M1 → **M35**. M36 target selection
  pending (SESSION_219).
- **DRF admin surface:** **123** endpoints (+1 M35.1
  `admin/lender-programs/list/`).
- **Frontend operator routes:** **21** (unchanged — M35.2
  extended `DealerFandIIncoming` in place).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** **321** verbs (unchanged; M35 reused
  shipped verbs).
- **Frontend surfaces:** +2 new M35.2 components in
  `frontend/src/components/f-and-i/`
  (`LenderSubmissionRecordForm` + `LenderSubmissionResponseForm`).
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **thirty-nine consecutive milestones** (M10 → M35). M35.1
  reused `_M101_PERMS`.
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 35 status:** SHIPPED — M35.0 planning + M35.1
  backend + M35.2 frontend + Playwright all local-only;
  awaits coordinated M35 push confirmation.
- **Audit tooling status:** unchanged from M26.1. Coverage
  **134 / 163** (+3 from M34's 131/162 — three lender endpoints
  moved backend-only → covered at M35.2).
- **Playwright personas:** **6 actual** (unchanged).
- **Playwright fixtures:** Intake Iris (M32.3) + Structure Sam
  (M33.2) + **Submission Sasha (M35.2 NEW)** — three fixtures,
  fully independent per M35 §5.c R7.
- **`@rerun-hygiene` tagged specs:** **4** (M34's 3 +
  M35.2's `fandi_submission_response_loop.spec.ts`).
- **§9 evidence for M36** (per M35 close):
  - **Elevated:** NEW C (F&I chargeback, pilot-gated but now
    with M10.6 substrate unblocked); Contract UI (M10.5 first
    activation candidate); Funding UI (M10.5 second); Stipulation
    UI (M10.4 first); NEW F&I workflow-state extensions beyond
    M35's four states; Lender Fit (3 of 4 blockers remain).
  - **M35 §5.h deferrals now candidates:** alternate-lender
    resubmission; submission history view; structured
    counter_terms/approval_terms capture; LenderProgram create
    UI.
  - **M32/M33 §3 deferrals:** F&I-scoped lead-context view;
    cross-lead pending-approval queue; direct-create CA
    structuring branch; iteration UX; PATCH on DealStructure.
  - **NEW O2 + NEW O3:** 10-milestone deferral.
  - **Gated:** T, U, L, M.
  - **Deferred:** D, G.
  - **All prior deferrals unchanged.**
- **Planning-time streak: 14** (at M35 close; assumes no §0.a
  M36.0 amendments; historical run of 89 across M10 → M23
  preserved).
- **DoD amendment (M21.0 §5.f Option B):** exception path
  invocation #12 at M35.1; **direct satisfaction at M35.2**.
  Twelve total exception-path invocations (M26 + M27.1 + M28.1
  + M29.1 + M30.1 + M31.1 + M32.1 + M33.1 + M34.1 + M34.2 +
  M35.1) + eleven direct satisfactions.
- **M35 audit coverage at close:** 163 endpoints, **134
  covered / 29 backend-only** (+3 covered, -3 backend-only,
  +1 total from M34's 162/131/31/321).
- **Durable lessons carried into M36+:** all (a)–(ff) preserved
  from M35.2 close. **(ff) elevated to load-bearing-across-two-
  milestones** after M35.2 first re-application (M34.0 origin +
  M35.2 re-application). **(cc) load-bearing-across-three-
  milestones** with **seventh invocation at M35.2** (M33.1 origin
  + M34.1 + M34.2 + M35.0 planning + M35.1 §0.a + M35.2 close
  + M35.2 §0.a Amendment A). **(z) load-bearing-across-three-
  milestones** with fourth invocation at M35.0 (10 corrections).
  Candidate durable lesson: **R4-class scanner tests must not
  enumerate the prohibited strings inside the scanned file** —
  enumerate in the scanner only (M35.2 D11 fourth defense
  layer). Candidate durable lesson: **per-endpoint URL
  comments must sit above `path(...)`, not inside its argument
  list**, per M35.1 §0.a.
