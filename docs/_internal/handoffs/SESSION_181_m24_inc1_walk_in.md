---
title: "SESSION_181 handoff — Milestone 24 · Increment 1 (M24.1 — shared intake substrate + walk-in UI + LeadDetailModal wire-in + walk-in journey)"
status: historical
type: handoff
date: 2026-08-03
session: 181
milestone: 24
milestone_status: in-progress
milestone_name: "Sales Operational Entry"
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_181 — Milestone 24 · Increment 1 (M24.1 — shared intake substrate + walk-in UI + LeadDetailModal wire-in + walk-in journey)

## What shipped

First anchor UI increment per M24
§5.a + revised §5.h scope.
Validates the walk-in intake workflow
end-to-end via a new shared form
component, a Dialog CTA + modal
wire-in on `DealerAiSalesLeads`, a
new seed command, and a new
Playwright journey. Phone / referral
/ webhook journeys ship at M24.2 /
M24.3 / M24.4 as sibling extensions.

**Also shipped this session:**
implementation-time planning
correction to the M24 memo, handoff,
and next-session file per user
direction at M24.1 open (see the
M24.0 handoff's "Correction at
SESSION_181 open" section for the
reason).

### Planning correction (SESSION_181 open, before implementation)

Under user direction, reopened the
M24 planning contract before writing
any implementation code because
empirical UI substrate verification
surfaced two evidence-based
mismatches:

- **Route path mismatch.** M24.0
  memo referenced
  `/dealer-ai/sales/leads/<id>` as
  the post-create redirect target.
  Real route is
  `/dealer-ai-sales/leads`
  (hyphen; no `:id` sub-route).
- **Downstream-verb UI substrate
  gap.** M24.0 §5.d assumed
  downstream operator UI existed
  for assign + schedule test drive
  + start cadence + attribution
  display + platform display.
  Verification showed only assign
  (via in-scope `LeadDetailModal`
  wire-in) and cadence (already
  shipped) are reachable.

**Revised decisions locked at
M24.1 open** per user direction:

- **§5.b revised.** Post-create
  opens `LeadDetailModal` on same
  page (no redirect; no new
  route). `LeadDetailModal` +
  `AssignmentDropdown` wired into
  `DealerAiSalesLeads` as an
  M24.1 in-scope extension. All
  route references corrected.
- **§5.d revised.** Common core
  across all four channels:
  intake → list visibility with
  correct channel attribution →
  open `LeadDetailModal` → assign
  via `AssignmentDropdown`. Phone
  additionally navigates to
  follow-ups and creates a 24hr
  cadence via existing
  `CadenceConfigPanel`. Walk-in
  / referral / webhook stop at
  assign.
- **§5.h revised.** M24.1
  completion contract expanded
  to include `LeadDetailModal` +
  `AssignmentDropdown` wire-in
  on `DealerAiSalesLeads`.
- **§3 deferrals added:**
  test-drive UI (M25 Candidate
  O2 sub-scope); referrer
  display in modal (M25 small
  UI extension); platform
  display in modal for webhook-
  origin leads (M25 small UI
  extension).

**Streak accounting.** Planning-
time as-recommended streak was
already reset to 0 at M24.0 for
the webhook operator-UI
redirect. Second planning
revision at M24.1 open stays
at 0 (not further reset; not
extended). Both corrections
recorded honestly.

**Durable lesson strengthened.**
M25+ planning-open checklists
must cover both intake and
downstream UI surfaces before
locking §5.b + §5.d.

Committed separately as
`75752f1` prior to any M24.1
implementation code.

### M24.1 implementation

**Verification:**
- Isolated M24.1 journey
  (`sales_manager` project +
  walk-in): **7 passed @
  ~13.0s** (6 setup + 1 M24.1).
- Isolated Vitest run on
  affected files: **12
  passed** (existing 4
  DealerAiSalesLeads + 8 new
  LeadIntakeForm).
- Full Vitest run: **201
  passed** (unchanged 193 +
  8 new).
- Full Django test suite:
  **4,780 pass, 1 skipped, 0
  fail** (167.7s; unchanged).
- Full acceptance suite on
  clean DB: **16 passed @
  25.2s** (6 setup + 10
  journeys; up from 15
  passed / 9 journeys at
  M23.4 close).

**Test-hygiene finding
(Candidate H reinforcement).**
A first pass of the full
acceptance suite on a
state-dirty DB (already
mutated by isolated walk-in
journey runs earlier in the
session) surfaced 3 failing
journeys:
`sales_manager/daily_startup`,
`recon/workflow`,
`office/accounting_workflow`.
All three failed on state
assumptions (e.g.
`expect(seededLead.assigned_to).toBeNull()`
in `daily_startup.spec.ts:76`
— pre-existing lead is
already assigned from prior
runs). Clean-DB re-run
(after deleting
`backend/db.acceptance.sqlite3`)
passed all 16 tests
including my walk-in
journey. Confirms all three
failures are the pre-
existing test-hygiene issue
documented as M22 §9
`feedback_avoid_exact_count_locks_in_tests`
+ M23 §9 Candidate H (test-
hygiene remediation);
strengthens the case for
Candidate H at M25 as an
independently-worthwhile
milestone-family sub-scope.
**M24.1 introduced no
regressions**; the shared-
DB test-hygiene concern is
pre-existing and separately
tracked.

**Backend baseline delta:** 4,780
→ **4,780** (unchanged — new
seed command is not a Django
test; management command
smoke-tested via dev DB +
Playwright test DB).

**Frontend Vitest baseline
delta:** 193 → **201 (+8)** —
eight new LeadIntakeForm tests.

**Acceptance suite baseline
delta:** 9 → **10 journeys**
(sales_manager project grows
from 1 → 2).

**Zero-drift permission-class
streak:** still twenty-three
consecutive milestones (M10 →
M23). M24.1 introduces zero
permission-class changes.
Streak target at M24.5 close:
twenty-four.

**M24 planning-time streak:**
still at 0 post-M24.1 open
correction (per §8 revised
accounting).

### Shipped surface

**Frontend components (new):**
- `frontend/src/components/sales/LeadIntakeForm.tsx`
  — shared intake form
  parameterized by `channel`
  (`"walk_in" | "phone" |
  "referral"`). 9 base fields
  matching backend
  `_BaseIntakeSerializer`.
  Optional `extras` slot for
  referral picker (M24.3).
  `onSubmit` callback lets
  the parent dispatch to the
  channel-specific wrapper.
- `frontend/src/components/sales/LeadIntakeForm.test.tsx`
  — 8 unit tests covering
  submit success, required
  name gate, optional-field
  handling (undefined not
  empty string), name trim,
  400 error, referral 404
  error, reset after
  success, extras slot
  render.

**Frontend pages (extended):**
- `frontend/src/pages/DealerAiSalesLeads.tsx`
  — imported
  `LeadDetailModal`,
  `LeadIntakeForm`, `Dialog`
  primitives, `createWalkInLead`
  wrapper. Added:
  - `useState<number | null>`
    for `selectedLeadId`
    (modal open state).
  - `useState<boolean>` for
    `walkInDialogOpen`
    (intake Dialog state).
  - Page-header `+ Walk-in`
    Button
    (`data-testid="sales-leads-add-walk-in"`).
  - Row `onClick` handler
    setting
    `selectedLeadId` (each
    row also carries
    `data-testid="sales-leads-row-<id>"`).
  - `Dialog` wrapping
    `<LeadIntakeForm
    channel="walk_in"
    onSubmit={createWalkInLead}
    onCreated={(lead) => {
      close dialog;
      open modal for
      new lead;
      reload list;
    }} />`.
  - `LeadDetailModal`
    rendered at page bottom,
    controlled by
    `selectedLeadId`.

**Backend management command
(new):**
- `backend/dealer_ai/management/commands/seed_journey_sales_operational_entry.py`
  — provisions:
  - `acceptance-sales-operator`
    user with `sales_manager`
    role at default
    dealership (session-safe
    per M23.2 durable — only
    sets password on newly-
    created user).
  - `acceptance-sales-operator-advisor`
    (Salesperson + linked
    auth user, `is_active=True`)
    as an alternate
    assignment target.
  - One referring-customer
    lead ("Priya Prior-
    Customer", walk-in
    channel) fixture-tagged
    with
    `[M24.1-sales-operational-entry-referrer]`
    for M24.3 picker.
  - `--reset` deletes the
    fixture lead + clears
    the operator's role +
    deactivates the advisor
    before re-seeding.

**Acceptance setup (extended):**
- `acceptance/support/auth/login.setup.ts`
  — appended
  `seed_journey_sales_operational_entry`
  to `SEED_COMMANDS`. M24.1-
  M24.4 journeys reuse the
  existing `sales_manager`
  persona (`acceptance-sales-
  manager`) for auth via
  storage state; assignment
  target is `Acceptance
  Advisor` from the M20 seed.

**Acceptance journey (new):**
- `acceptance/journeys/sales_manager/walk_in_intake.spec.ts`
  — walk-in intake operational
  contract:
  1. Navigate to
     `/dealer-ai-sales/leads`.
  2. Click `+ Walk-in` CTA.
  3. Fill LeadIntakeForm with
     unique per-run customer
     name.
  4. Submit.
  5. Wait for LeadDetailModal
     header ("Sales handoff
     packet").
  6. Extract new lead id
     from modal header
     ("Lead #<id>" pattern).
  7. Business-outcome
     assertion via admin API:
     lead exists + assigned to
     Acceptance Advisor +
     channel="walk_in".
  8. Reload page + assert
     list row for new lead
     shows channel="walk_in"
     (survives fresh fetch).

**Journey design notes:**
- Reload rather than click-
  close-modal because the
  modal region contains two
  "Close" buttons
  (AssignmentDropdown +
  LeadDetailModal); strict-
  mode collision. Reload
  additionally proves state
  survives a fresh fetch,
  not just optimistic UI.
- Unique per-run customer
  name (timestamped) so
  suite re-runs don't collide
  on the same name.
- API-side assertion is
  authoritative
  (`expectLeadAssignedTo`
  helper from
  `support/assertions/dashboard.ts`).

## Starting-state verification (this session)

Ran the full M24.1-open
checklist per the SESSION_180
handoff:

- `git status` — clean at open;
  M24.0 planning correction
  committed as `75752f1`
  before M24.1 implementation.
- `git log --oneline -6` — top
  is `a52a56e` (M24.0 close)
  at session open;
  `origin/main` at `6dfdb5c`
  (M23 close-out, 1 commit
  behind — no push at M24.0
  per non-goals).
- `python3 manage.py test
  dealer_ai` → **4,780 pass,
  1 skipped, 0 fail** (163s).
- `cd frontend && npm test`
  → **193 pass** at open
  (201 at close).
- `python3 manage.py check`
  clean.
- `python3 manage.py
  makemigrations --check
  --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc
  --noEmit` clean.
- `cd acceptance && npx tsc
  --noEmit` clean (verified
  post-changes).
- `redis-cli ping` → `PONG`.
- M23 acceptance CI run
  `30840071050` verified
  green (2m20s) — inherited
  from M24.0 open.

All green. No §0.a M24.1
amendments needed for pre-
existing regressions.

## §5.d authoring notes (M24.1 in-scope small fixes)

None. The walk-in journey
passed on second attempt —
first attempt hit a Playwright
strict-mode collision on
`Close` button locator (two
"Close" buttons in the modal
region: AssignmentDropdown's
internal Close + LeadDetailModal's
outer Close). Fixed by
reordering steps (business-
outcome API assertion first,
then `page.reload()` to
dismiss the modal + confirm
assignment persists across a
fresh fetch). This was a
journey-authoring adjustment,
not a surfaced operator UI
bug — no in-scope operator
surface gap fixes.

Genuinely-missing UI surfaces
(test-drive UI, referrer
display, platform display)
remain M25 §3 deferrals per
the M24.1-open correction —
not attempted this session.

## Load-bearing decisions honored

**§5.a** — target unchanged
(Sales Operational Entry).

**§5.b** (revised at M24.1
open) — three operator Dialog
CTAs planned; only walk-in
shipped this increment. Post-
create opens `LeadDetailModal`
on same page (no redirect).
`LeadDetailModal` +
`AssignmentDropdown` wired
into `DealerAiSalesLeads`.

**§5.c** — journey in
`acceptance/journeys/sales_manager/`
folder as planned.

**§5.d** (revised at M24.1
open, Option C) — walk-in
row shipped: intake → list
channel visibility → modal →
assign. No test-drive step
(deferred).

**§5.e** — one shared seed
per M24 (Option A). Session-
safe `set_password` guarding
applied from the start per
M23.2 durable memory.

**§5.f** — journey-as-
verifier (Option B). One
authoring adjustment
(strict-mode Close collision)
resolved by test refactor,
not operator surface fix.

**§5.g** — opportunistic
testids (Option B). Added:
`sales-leads-add-walk-in`,
`sales-leads-walk-in-dialog`,
`sales-leads-row-<id>`,
`lead-intake-<channel>-*` (per
LeadIntakeForm field), and
`lead-intake-form-<channel>`.

**§5.h** (revised at M24.1
open, Option B) — M24.1
scope expanded to include
`LeadDetailModal` wire-in.
Shipped: `<LeadIntakeForm>`
+ walk-in Dialog CTA + modal
wire-in + seed + journey.

## Streak

**Planning-time as-recommended
streak: 0** (unchanged since
M24.0 reset; M24.1-open
correction did not further
reset it — the two planning
corrections in this milestone
are recorded honestly rather
than reclassified).

**Zero-drift permission-class
streak: still 23 consecutive
milestones** (M10 → M23) at
M24.1 close. M24.1 introduces
zero permission-class
changes. Streak target at
M24.5 close: 24.

## What's next: SESSION_182 M24.2 phone UI + cadence journey

Per MILESTONE_24_PLANNING.md
§7 M24.2:

- **`+ Phone` Dialog CTA**
  attached to
  `DealerAiSalesLeads.tsx`
  (sibling to walk-in CTA;
  same shape).
- **`<LeadIntakeForm
  channel="phone">`** reuse;
  no new component work
  (shared substrate from
  M24.1).
- **Post-create opens
  `LeadDetailModal`** for the
  new phone lead (wire-in
  from M24.1 reused).
- **Vitest coverage:**
  possibly ~2–3 tests if
  channel-parameterization
  behavior needs additional
  coverage; else no growth.
- **Seed extension:** no new
  fixtures required.
- **New journey**
  `acceptance/journeys/sales_manager/phone_intake.spec.ts`:
  intake → modal → assign →
  navigate to
  `/dealer-ai-sales/follow-ups`
  → use existing
  `CadenceConfigPanel`
  (`CreateCadenceForm`) to
  start 24hr cadence with the
  new lead's ID → assert
  cadence created.
- **Session handoff** at
  `docs/handoffs/SESSION_182_m24_inc2_phone.md`.
- **`00-START-NEXT-SESSION.md`**
  refreshed for M24.3.

**Backend baseline target
at M24.2 close:** 4,780 →
**~4,781** (possibly one
optional seed-fixture test).
Frontend Vitest: 201 →
**~203–204**. Acceptance
suite: 10 → **11**.

## What lands at M24.3 (SESSION_183) — referral UI + journey

Referral adds
`<ReferralLeadFormExtras>` +
attribution API-side assertion.

## What lands at M24.4 (SESSION_184) — webhook integration-to-operator journey

No new UI. Real webhook POST
in setup + operator handles
via existing UI.

## What lands at M24.5 (SESSION_185, or SESSION_184 if M24.4 folds) — close-out

CI validation + capability
matrix + retrospective + M25
skeleton + coordinated push.

## Non-goals for the remaining M24 increments

Per MILESTONE_24_PLANNING.md
§9 (unchanged):

- ❌ No manual webhook UI.
- ❌ No test-drive UI (§3
  deferral 12; M25).
- ❌ No referrer display in
  modal (§3 deferral 13;
  M25).
- ❌ No platform display in
  modal (§3 deferral 14;
  M25).
- ❌ No new routes /
  endpoints / carriers /
  migrations / permission
  classes.
- ❌ No individual per-
  increment pushes.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_24_PLANNING.md`
   (planning locked at
   SESSION_180 with M24.1-
   open corrections
   integrated)
6. `docs/roadmap/MILESTONE_23_PLANNING.md`
7. `docs/roadmap/MILESTONE_23_RETROSPECTIVE.md`
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
9. `docs/CAPABILITY_MATRIX.md`
10. `docs/handoffs/SESSION_180_m24_inc0_planning.md`
    (M24.0 record +
    SESSION_181-open
    correction section)
