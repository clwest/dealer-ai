---
state: frozen
date: 2026-08-05
frozen_at_commit: b0597f5
frozen_by_session: 219
last_session_shipped: SESSION_218
last_milestone_shipped: 35
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
milestone_36_status: paused_pending_readiness_decision
next_session: SESSION_220
next_milestone: 36
next_milestone_name: "(pending readiness-lens decision — see docs/DEALER_READINESS_ASSESSMENT.md)"
next_increment: 0
next_increment_name: "M36.0 — readiness decision + planning"
---

# Repository frozen — 2026-08-05 at `b0597f5`

> **Status: FROZEN pending user + ChatGPT review of
> `docs/DEALER_READINESS_ASSESSMENT.md`.** No active work in
> progress. M36 planning paused. The next session cannot
> pick M36 scope until the readiness-lens decision is made.

## What you're looking at

Work stopped at the OPEN of SESSION_219 — Milestone 36 planning.
Before locking M36 scope, the user requested a discovery-only
"dealer readiness" assessment: *what does "dealer ready" look
like for the actual initial customer, and how close are we today?*

The assessment produced a **key finding that changes the M36
optimization**: Dealer OS has more functional depth than launch
readiness. The gap to a first paid pilot is not more F&I links —
it is deployment, notifications, document upload, user-management
UI, data export, and monitoring. None of those are on the M35-
generated M36 candidate list.

The recommendation is to open M36 as a **launch-readiness arc**
(preferred) or a **single dealer-readiness milestone** (fallback)
— NOT to continue the F&I depth-arc with Contract UI.

**No M36 scope was locked.** The prior M35-generated candidate
list (F&I arc, Contract UI recommendation) is on pause pending
review.

## Two documents to read at resume

1. **`docs/DEALER_READINESS_ASSESSMENT.md`** — the full nine-
   section assessment. Read this first; it defines the four
   readiness standards, describes the minimum daily operating
   loop, scores ~45 readiness dimensions, ranks blockers, gives
   the concrete path to first dealer.
2. **`docs/handoffs/SESSION_219_dealer_readiness_assessment.md`**
   — the SESSION_219 handoff summarizing what happened. Short.

Also useful for context if it's been a while:

- `docs/CAPABILITY_MATRIX.md` §7s–7u (M18/M19/M20 — the pilot-
  readiness triple that already shipped, largely forgotten by
  the M35 planning arc)
- `docs/PILOT_ONBOARDING_PLAYBOOK.md` (M19.5 — how a pilot
  actually gets stood up today)
- `docs/handoffs/SESSION_218_m35_inc2_frontend.md` (M35 close)

## Repo state at freeze

Everything green. Nothing dirty. Nothing uncommitted (aside from
this doc + the two other assessment-session docs, which the user
commits at resume).

- git: `main` clean, up-to-date with `origin/main` at `b0597f5`
- Backend: **5,045 pass, 1 skipped, 0 fail** (`python3 manage.py test dealer_ai`)
- Frontend Vitest: **431 pass across 47 files** (`cd frontend && npm test`)
- Frontend `tsc --noEmit`: clean
- Acceptance `tsc --noEmit`: clean
- Django `check` + `makemigrations --check --dry-run`: clean
- Redis: PONG
- Audit artifact: **163 endpoints / 134 covered / 29 backend-only / 321 service verbs**
- Latest M35 CI run: success in 3m4s (M35.2 hash-backfill push, 2026-08-05T16:42:36Z)
- Migrations: `0001` → `0051`
- Operator routes: **30** (see SESSION_219 handoff — supersedes the "21" figure in the M35 close handoff)
- Playwright: **26 spec files, 6 personas, 3 fixtures**
- Permission classes: **7 canonical / 7 actual** — zero-drift streak 39 milestones (M10 → M35)
- Milestones shipped: **M1 → M35**
- M36: **open, no scope, no increments started, no planning memo**

## Unstaged files added or overwritten in SESSION_219

- `docs/DEALER_READINESS_ASSESSMENT.md` (new)
- `docs/handoffs/SESSION_219_dealer_readiness_assessment.md` (new)
- `00-START-NEXT-SESSION.md` (overwritten — this file)

User commits after review.

## First thing SESSION_220 must do

### 1. Verify freeze state is intact

```bash
git status                          # working tree clean or only the 3 SESSION_219 doc changes
git log --oneline -5                # top should still be b0597f5
python3 manage.py test dealer_ai    # 5,045 pass
cd frontend && npm test             # 431 pass
```

If any of the above drifts, investigate before proceeding. The
freeze is only meaningful if the state matches.

### 2. Confirm the SESSION_219 docs still exist

```bash
ls -la docs/DEALER_READINESS_ASSESSMENT.md
ls -la docs/handoffs/SESSION_219_dealer_readiness_assessment.md
```

Both should be present. If the user committed them between
SESSION_219 and SESSION_220 (recommended), `git log` will show
one or two additional commits atop `b0597f5`.

### 3. Read the assessment

Full read of `docs/DEALER_READINESS_ASSESSMENT.md`. Do not skip
to the recommendation — the evidence supporting §7 (strategy
critique) and §8 (recommendation) lives in §2 through §5, and
the recommendation only makes sense with that context.

### 4. Present the readiness decision to the user

The user should have already reviewed the assessment with
ChatGPT before SESSION_220 opens. If not, offer to walk through
the assessment together first.

Present the three M36 options from the assessment §8:

- **Option E (preferred):** Launch-Readiness Arc — 4 focused
  milestones + 2 increments (deploy pipeline → user invitation +
  password reset → notification minimum → document upload →
  data export → monitoring)
- **Option C (fallback):** Single dealer-readiness milestone
  picking user-management UI + notification minimum
- **Option D (not recommended):** Continue F&I depth-arc with
  Contract UI (M10.5). Preserved as an option because the user
  or ChatGPT may have counter-evidence.

Ask the user to pick.

### 5. Once the readiness lens is chosen

Draft the M36 active memo per whichever option was picked:

- **If E:** the memo scopes the FIRST milestone in the arc
  (probably the deploy pipeline, or user invitation + password
  reset if deploy needs external decisions the user hasn't made
  yet). The arc itself gets a top-level scope doc reference; the
  memo scopes only the first milestone.
- **If C:** the memo scopes the single milestone directly.
- **If D:** re-open the M35-generated candidate list, present the
  Contract UI recommendation from SESSION_219's first turn, lock
  §5.a for Contract UI, and draft §5.b–§5.h.

Follow the standard M28–M35 active-memo shape. The verification-
driven revision discipline (z), coverage-projection truthfulness
(cc), and rerun-safety-against-shared-state (ff) durable lessons
all still apply.

### 6. DoD compliance check

Per M21.0 §5.f Option B: whichever M36.0 memo lands must name a
Playwright journey add/extension OR document why no journey
change is required. For a deploy-pipeline milestone the exception
path likely applies (infra change, no user-facing journey delta);
for user-invitation UI or notification UI a new journey is
warranted.

### 7. Ship the M36.0 handoff

`docs/handoffs/SESSION_220_m36_inc0_planning.md` per standard
shape. Do NOT push — planning increments do not push; the
coordinated push comes at milestone close.

## Non-goals for SESSION_220

- ❌ Do NOT default to Contract UI without the user explicitly
  choosing Option D
- ❌ Do NOT skip reading `docs/DEALER_READINESS_ASSESSMENT.md`
  — the user paused specifically to make this decision, and the
  M35-generated candidate list is only meaningful in context of
  the readiness lens
- ❌ Do NOT modify backend / frontend / acceptance code
- ❌ Do NOT open an M36 implementation increment
- ❌ Do NOT force-push or amend earlier commits
- ❌ Do NOT re-open shipped M1–M35 surface

## Path to market (from the assessment §9)

Ordered from most-blocking to least-blocking. Each is estimated
at ~1 milestone unless noted.

1. **Production deployment** — Postgres + Redis + backup rotation
   + frontend host + DNS + HTTPS. Blocks everything downstream.
2. **User invitation + password reset UI** — owner emails
   salesperson; invitee sets password on first login; role change
   UI.
3. **Notification minimum** — email-on-new-lead to assigned
   salesperson; email-on-lender-response to F&I manager; in-app
   notification bell.
4. **Document upload + deal jacket** — `FileField` on new
   `DealDocument` model FK'd to Deal + Stipulation; upload UI;
   S3/B2 blob storage.
5. **Data export minimum** [~1 increment] — CSV of Deals + Sales
   + Trial-balance-as-of; PDF-print of a Deal.
6. **Monitoring minimum** [~1 increment] — `/health` + `/ready`
   endpoints; Sentry; UptimeRobot; resurrect `manage.py
   pilot_dry_run`.

**Rough total:** 4 focused milestones + 2 increments (~12 sessions
at current cadence) to reach standard A (pilot ready with Chris
on-call and doing all provisioning). Standard B (first paying
dealer without daily intervention) needs additionally: undo/edit
on posted financial data, customer-communication send path,
richer data export.

## What can be deferred until after dealer #1

MFA · SSO · self-serve signup · billing · multi-tenant Celery
Beat validation · cross-browser CI · additional F&I depth
(Contract UI, Funding UI, Chargeback, alternate-lender
resubmission) · direct-create structuring branch · LenderProgram
create UI · all existing §3 deferrals.

## What must be manually supported during the pilot

- Chris runs deploy + backup restore
- Chris provisions the tenant via `POST /admin/pilots/create/`
  (M19.4 UI exists)
- Chris uploads inventory CSV or coaches the dealer through it
- Chris investigates via Django admin + logs when the dealer
  reports an issue
- Chris ships hotfixes on request

## Evidence needed to call the pilot successful

- 30 consecutive days of the dealer using Dealer OS as primary
  system for at least one workflow
- Zero critical data loss (backup restore never triggered *in
  anger*)
- Chris intervention rate < once per week by day 30
- Owner reports one workflow "beats what we did before" in an
  open-ended interview
- Signed month-2 commitment (paid or written)
- One workflow measurably faster or more accurate than pre-
  Dealer OS (metric agreed with dealer up front)

## What would stop Chris from putting this in a dealership today?

Ordered by decreasing severity:

1. Nothing is deployed.
2. No backup.
3. No way for staff to know a new lead arrived.
4. No signed-contract attachment.
5. Owner cannot invite their sales manager.
6. No monitoring.
7. No password reset.
8. No accountant-facing export.

Every one of these is a smaller lift than the M35 F&I arc that
just shipped.

---

## Anchors that win on conflict

1. `docs/DEALER_READINESS_ASSESSMENT.md` — **new authoritative
   doc for the readiness lens**
2. `docs/PROJECT_RULES.md`
3. `docs/DOC_GOVERNANCE.md`
4. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
5. `docs/roadmap/AUTHENTICATION_MODEL.md`
6. `docs/PILOT_ONBOARDING_PLAYBOOK.md` (M19.5)
7. `docs/CAPABILITY_MATRIX.md` §7s–7u + §7κ
8. `docs/roadmap/MILESTONE_35_PLANNING.md` §5 + §9 (M36
   candidate list origin — now paused pending readiness
   decision)
9. `docs/handoffs/SESSION_219_dealer_readiness_assessment.md`
10. `docs/handoffs/SESSION_218_m35_inc2_frontend.md` (M35 close)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.
