---
title: "Dealer Readiness Assessment — Dealer OS"
status: active
type: assessment
date: 2026-08-05
session: 219
baseline_commit: b0597f5
baseline_milestone: 35
authors: assistant + user (Chris)
reviewers_pending: user (Chris) + ChatGPT
supersedes_lens_from: "MILESTONE_34_RETROSPECTIVE.md §9 (F&I depth-arc vs. breadth-reset vs. close-deferral standing question)"
---

# Dealer Readiness Assessment — Dealer OS

**Discovery only.** Written at the open of SESSION_219 in response to
a user request to pause milestone planning and assess whether the
current roadmap is converging on a first real dealer. Not implemented.
Not locked. Pending review by the user and ChatGPT before any M36
scope decision.

Baseline: `main` at `b0597f5` (post-M35 push). Backend 5,045 pass,
frontend 431 pass across 47 files, acceptance 26 spec files, audit
163 endpoints / 134 covered / 29 backend-only / 321 service verbs.

---

## Key finding up front

**Dealer OS has more functional depth than launch readiness.**

M18 (demo-store simulation), M19 (pilot onboarding substrate +
playbook + `/dealer-ai-admin` PilotOnboardingSection UI + 13-phase
dry-run test), and M20 (six executable Playwright journeys) already
shipped a coherent pilot-conversion machinery — fifteen milestones
ago. Since M21 the roadmap has ridden a *coverage-density* lens
(audit endpoints: 134/163 covered) and an F&I depth-arc
(M32→M33→M35) that adds functional depth without touching the
operational surface a real dealer needs to *run the software* end-
to-end.

The gap to a first paid pilot is not more F&I links; it is
**deployment, notifications, document upload, and user-management
UI** — none of which are in the current M36 candidate list.

---

## 1. Defining "dealer ready"

Four distinct standards. Not one.

| Standard | Definition | Current state |
|---|---|---|
| **A. Pilot ready** | Runs at one real dealership with Chris on-call and doing all provisioning / support. Data cannot be lost. Employees can complete every daily workflow that Chris has scoped. | Close, blocked by 4–6 items (§5). |
| **B. First paying dealer ready** | Runs at one dealership *without* daily intervention. Employees invite each other, recover from mistakes, communicate with customers, and extract data at month-end without SSHing into Django. | Farther. Adds notifications, document upload, edit/undo across financial data, data export. |
| **C. Repeatable onboarding ready** | A non-Chris operator can onboard a new dealer following the playbook. New dealer provisioning is codified end-to-end and does not require code changes per tenant. | M19 substrate covers ~70% today. User provisioning is still a Django-admin exercise (`PILOT_ONBOARDING_PLAYBOOK.md` Phase 8); Chris still owns deployment. |
| **D. Scalable SaaS ready** | Self-serve signup, billing, tenant lifecycle, cross-tenant support tooling, SLA-grade observability. Multi-operator platform-operator surface. | Not close. Explicitly out of scope in `docs/research/INDEPENDENT_DEALER_PIVOT.md:141` — "Multi-tenant SaaS shell — separate future project." |

The current milestone strategy has been drifting toward B implicitly
but has not named it as the target since M20.

---

## 2. Minimum viable daily operating loop

For a 2–8 person independent used-car lot:

| Phase | Role | What must happen |
|---|---|---|
| Morning open | Owner | See yesterday's activity, aged inventory, aged leads |
| Lead intake | Sales | Log walk-in / phone / chat lead, assign salesperson |
| Vehicle proposal | Sales | Match customer to inventory, quote payment |
| Writeup | Sales mgr | Approve writeup, capture credit app |
| F&I structure + submit | F&I mgr | Structure deal, submit to lender, record response |
| Contract + delivery | F&I mgr | Print/sign contract, record sale, hand keys |
| Recon (trades) | Recon | Inspect trade, order recon, complete work |
| BHPH servicing | Collections | Take a payment, log a PtP, chase delinquency |
| Accounting close | Office | Post the day's transactions, check trial balance |
| Communication | All | Notify staff/customers of status changes |

### Loops that terminate inside Dealer OS today ✅

| Loop | Evidence |
|---|---|
| Morning open (owner) | `DealerOverviewPage` + `DealerAdmin` + `DealerAnalyticsPage` (5 tabs) |
| Lead intake | `DealerAiSalesLeads` (chat + walk-in + phone + referral), `LeadDetailModal` + `AssignmentDropdown` |
| Vehicle proposal (chat) | `ChatEngine` with 16-stage scrub + deterministic payment math |
| Writeup + credit app | Writeups panel (M32.2); credit-app intake at `DealerFandIIncoming` (M33) |
| F&I structure | `DealStructureForm` inline in DealerFandIIncoming (M33) |
| Lender submit + response | `LenderSubmissionRecordForm` + `LenderSubmissionResponseForm` (M35.2) |
| Sale + delivery | `VehicleSalePage` (M9) |
| Recon | `VehicleReconPage` full work-order lifecycle (M4) |
| BHPH servicing | `DealerAiBhphNoteDetail` — payment, PtP, contact, repo forms (M12+M23) |
| Accounting close | Trial balance + journal entries + templates (M13–M17, M27–M31) |

### Loops that start but do NOT terminate inside Dealer OS ⚠

| Loop | What breaks | Evidence |
|---|---|---|
| Contract signing | No PDF upload, no e-sign, no printing template | `ComplianceRecord.evidence_url` is a URL string; no upload substrate (M10.7: "No storage plumbing at M10.7 — the URL field captures operator reality") |
| Customer follow-up | Drafts generated, never sent | `services/follow_up.py` returns SMS/email draft text; no Twilio/SendGrid in `requirements.txt` |
| Lender document exchange | External URL only | `Stipulation.evidence_url` |
| Notification of new lead | Nothing pings staff | No `Notification` model, no email/SMS/push in codebase |
| Task assignment | Assignment persists; assignee not notified | `CustomerLead.assigned_to` works; no downstream notify |
| Month-end tax export | No CSV/PDF from any surface | Zero export endpoints in `views_analytics.py` |

### Loops that require external / manual workaround ❌

- Contract PDFs, credit apps, IDs, insurance cards → dealer's Google Drive / paper / DMS.
- Customer texts/emails → dealer's personal phone or SMTP.
- Password resets, invitations, role changes → Django admin (`PILOT_ONBOARDING_PLAYBOOK.md` Phase 8: "Currently a Django-admin exercise").
- Prospect intake UI → Django admin / Python shell.
- Backup / recovery → nothing in-repo.

### Missing loops that would prevent adoption

1. In-app notification of new lead / assigned task — F&I manager cannot know a deal moved into their queue without polling.
2. Signed-contract attachment to a deal — F&I compliance requires it.
3. Employee invitation — owner cannot add a salesperson without shell access.
4. Customer-communication trail on a lead — no log of what was actually said/sent.

### Missing loops acceptable during a supported pilot

- Password reset via Chris (weekly is tolerable)
- Data export via management command (monthly is tolerable)
- Prospect intake via admin (fine while Chris is sole operator)
- Multi-operator support (only Chris runs pilots)
- Cross-browser support (Chromium only)

---

## 3. Readiness scorecard

Classification: **OR** operationally ready · **PP** usable with pilot
assistance · **PB** partial/broken loop · **BS** backend substrate
only · **AB** absent · **UN** intentionally unnecessary for first
dealer.

| Dimension | Status | Evidence / gap |
|---|---|---|
| Dealership setup / initial config | OR | `/dealer-ai-onboarding` (6 sections including logo, business shape, AI behavior); `DEFAULT_DEALER` fallback |
| User invitation | AB | No UI; `PILOT_ONBOARDING_PLAYBOOK.md` Phase 8 = "Django-admin exercise" |
| Authentication (login/logout) | OR | Session + token, `<RequireAuth>`, tested |
| Password reset | AB | `CAPABILITY_MATRIX.md:4192` — "NOT yet built" |
| MFA | AB · UN | Explicit non-goal (AUTHENTICATION_MODEL §9) |
| Roles / permissions | OR | 7 canonical roles, 7 permission classes, 39-milestone zero-drift streak |
| Inventory add | PB | No add-vehicle UI; **CSV import wired end-to-end via M19.4** |
| Inventory edit / listing / photos | OR | Listing editor, photo gallery with upload/reorder/delete/restore |
| Lead / customer intake | OR | Chat + walk-in + phone + referral + listing-form (M11, M24) |
| Sales workflow | OR | Writeups (M32), follow-ups (M25), be-backs, test-drive log (creation deferred) |
| Desking / writeup | OR | Writeups panel (M32.2) |
| F&I intake | OR | Incoming queue with structure + submit (M33 + M35) |
| F&I downstream (contract/funding/chargeback) | BS | `Contract`/`BackEndProductAgreement`/`Funding` models shipped (M10.5); no UI |
| Recon | OR | Full work-order lifecycle (M4) |
| Accounting | OR | Trial balance + journal entries + templates + reversal (M13–M17, M27–M31) |
| Deal jacket / document upload | AB | Only `evidence_url` (URL string); no `FileField` for deal docs |
| Vehicle photos | OR | Full lifecycle (M6.7) |
| Notifications | AB | No email/SMS/in-app tray; drafts generated only |
| Assignments | PP | `CustomerLead.assigned_to` works; no notification to assignee |
| Daily queue / task inbox | PB | Follow-ups + be-backs queues require manual navigation; no push |
| Reports & owner visibility (in-UI) | OR | `DealerAnalyticsPage` 5 tabs; DealerOverviewPage |
| Reports & owner visibility (export) | AB | Zero export verbs |
| Data import | PP | CSV inventory import works (M19.2 + M19.4); nothing else |
| Data export | AB | Zero CSV/PDF export endpoints |
| Auditability (mistake correction) | PB | PATCH/DELETE on condition findings, journal-entry reversal (M27+M30); no undo on posted sales / F&I / BHPH; no `AuditLog` model |
| Usability for nontechnical staff | UNKNOWN | Playwright asserts persona journeys succeed; real-user usability unverified |
| Reliability | PB | Celery Beat scheduled (9 jobs); no retry/DLQ; no graceful shutdown |
| Backup / recovery | AB | Zero backup scripts. Render free tier SQLite ephemeral. |
| Observability | AB | No Sentry, no `/health` endpoint, no structured logging, no metrics |
| Security (CORS/CSRF/SQL) | OR | Session + CSRF token rotation, ORM parameterization, prompt guards |
| Rate limiting | AB | DRF throttling framework unused |
| Secrets management | PP | Env vars only; no vault |
| Tenant isolation (design) | OR | Documented in `AUTHENTICATION_MODEL.md`; layer discipline enforced |
| Tenant isolation (validation) | PB | No dedicated cross-tenant leak test suite found |
| Deployment | BS | `render.yaml` staged; frontend undeployed; no Postgres/Redis provisioning script |
| Environment mgmt | PP | `.env.example` exists; no runbook; CORS origins hardcoded to stale Vercel URLs in `render.yaml` |
| Onboarding new tenant | OR (partial) | M19 5-endpoint checklist + playbook; user provisioning still Django-admin |
| Training / support / troubleshooting | PB | Django admin exists; no operator log viewer; no per-tenant support tool |
| Integrations required | UN | No DMS/CRM/e-sign; explicit non-goal per pivot doc |

Rough tally across ~45 dimensions: **OR = 15 · PP = 5 · PB = 8 ·
BS = 2 · AB = 12 · UN = 3**.

---

## 4. Capability vs operational usability

Distinguishing "backend substrate exists" from "operator can use it":

| Capability shipped | Operator usable? | Gap |
|---|---|---|
| `Contract` + `BackEndProductAgreement` + `Funding` (M10.5) | No — no UI | Backend substrate only |
| `Chargeback` model (M10.6) | No — pilot-gated, no UI | Backend substrate only |
| `Stipulation` model + `evidence_url` (M10.4) | Partial — record exists, no file upload | Substrate + partial UI |
| `services/follow_up.py` draft generation | Partial — drafts shown, no send | UI-only, no outbound wire |
| `services/analytics/*` aggregations | Yes for view, no for export | Missing export layer |
| `PilotProspect` state machine | Yes for Chris via shell, no UI | Playbook Phase 1–2 = Django-admin |
| CSV inventory import | Yes — full UI wired (M19.4) | ✓ |
| Photo lifecycle | Yes — full UI wired (M6.7) | ✓ |
| Payment recording (BHPH) | Yes — full UI wired (M12+M23) | ✓ |
| Journal-entry reversal | Yes — full UI wired (M27+M30) | ✓ |

**M35's F&I depth-arc lives in the top rows** — it's valuable but
addresses functional coverage, not operational usability. Meanwhile
the *rows with highest adoption impact* (notifications, document
upload, user invitation) have zero substrate and are not on the
M36 candidate list.

---

## 5. True blockers ranked

### Hard blockers — dealership cannot operate safely without them

1. **No production deployment.** `render.yaml` staged and never activated; frontend undeployed. Every dealer minute requires local dev servers. **Dealbreaker #1.**
2. **No backup / recovery.** Render free tier SQLite is ephemeral; a dealership's ledger can disappear on restart. Postgres migration is trivial but no backup rotation exists.
3. **No document upload for signed contracts / IDs / insurance.** F&I compliance requires attachable evidence; `evidence_url` is not a substitute.
4. **No customer-communication send path.** Drafts generated but no Twilio/SendGrid — dealer cannot text a customer through Dealer OS.
5. **No monitoring / error tracking.** If it fails at 4pm Saturday, no one knows.

### Adoption blockers — works, but employees would reject or abandon it

6. **No employee-invitation UI.** Owner cannot add a salesperson without SSH access. In a 2–8 person shop the owner IS the admin.
7. **No password reset.** Every lost password requires Chris. Not sustainable past week two.
8. **No notification of new lead / assigned task.** F&I manager or salesperson learns of assigned work only by polling.
9. **No undo/edit on posted sales, F&I deals, or BHPH transactions.** Mistakes are inevitable; no recovery path except calling Chris.
10. **No CSV export of deals / sales / trial balance.** Dealer's accountant cannot get monthly data out.

### Support blockers — Chris could pilot but only with unreasonable daily intervention

11. **No `/health` endpoint** — no uptime monitor can be wired.
12. **No operator log viewer / per-tenant data inspector.** Chris must SSH + Django shell for every question.
13. **`PilotProspect` intake UI absent.** Chris uses Django admin, fine for one dealer, painful past three.
14. **Multi-operator (`IsPlatformOperator`) deferred.** Fine while Chris is sole operator.

### Scale blockers — fine for dealer 1, unacceptable for dealers 2–10

15. **Per-tenant Celery Beat scheduling under load — untested.** 9 daily jobs are per-tenant via orchestrator but multi-tenant validation not exercised in M18–M20.
16. No self-serve signup or billing.
17. CORS origins hardcoded in `render.yaml` to stale Vercel URLs.
18. No cross-browser CI (Chromium only).

### Commercial blockers

19. **No pricing model, contract template, SLA, or support scope defined in-repo.** `MARKET_HANDOFF_BUNDLE.md` exists — pending end-to-end read to confirm whether pricing has been decided.
20. **Success criteria for a paid pilot not codified** (though pilot readiness has a checklist).

---

## 6. How close are we?

Refusing to invent a percentage. Naming numerator and denominator.

**Numerator (shipped):** Full daily workflow surface for indie
used-car dealer INCLUDING F&I intake / structure / submit / response,
BHPH portfolio + collections, recon full lifecycle, accounting
reconciliation + trial balance + journal entries, 30 operator routes
with 6 personas tested via 26 Playwright journeys, 5,045 backend
tests, 431 Vitest tests, pilot-onboarding substrate + playbook.

**Denominator (needed for standard A — pilot ready):**
- Numerator above +
- Production deployment (Postgres + Redis + backup) [~1 milestone]
- Employee invitation + password reset UI [~1 milestone]
- Notification minimum (email on new lead + assignment) [~1 milestone]
- Document upload for deal jacket [~1 milestone]
- Data export minimum (deals CSV + trial-balance CSV) [~1 increment]
- Monitoring minimum (Sentry + `/health` + uptime probe) [~1 increment]

**Verdict:** Dealer OS is **`technically pilotable now with
controlled support`** for standard A, and **`a handful of blocking
milestones away`** (4–6 focused milestones) from standard B (first
paying dealer). It is NOT several major product arcs away from a
real dealership.

This is a smaller gap than the current milestone process makes
visible. The audit-coverage lens has focused planning on 8-endpoint-
per-milestone F&I depth; the 15-milestone-old M18–M20 pilot machinery
is a stronger foundation than the metric acknowledges.

---

## 7. Is current strategy converging on dealer readiness?

Candidly: **no, not efficiently.**

### Signs of polishing architecture ahead of customer necessity

- Chargeback substrate (M10.6) shipped without operator use case — still pilot-evidence gated post-M35.
- Zero-drift permission-class streak (39 milestones) celebrated as architectural achievement, while no user-management UI exists for the dealer owner to invite a salesperson.
- Coverage-projection truthfulness (cc) — an ops discipline for coverage math — invoked 7 times as durable lesson; no equivalent tracking for operational-usability coverage.
- Audit artifact tracks 163 endpoints / 134 covered — measures *endpoint-to-Playwright-journey*, not *loop-to-dealer-usability*.

### Signs of completing isolated loops without a coherent daily product

- F&I depth-arc (M32 + M33 + M35) is real progress, not gated by dealer feedback. Contract UI is the natural next link — but a dealer with the current F&I surface cannot record a signed contract, receive a lender-approval notification, or export the deal for their accountant. All three matter more than the fourth F&I link.
- The `standing question` at every §5.a ("continue F&I arc / breadth-reset / close deferral") **has no fourth option: "does this move us toward launch?"**

### Signs of underinvesting in onboarding or usability

- M19 shipped a real pilot playbook — then strategy pivoted back to backend workflow depth. No milestone since M20 has extended the pilot surface (user provisioning UI, notifications, deal-jacket, deploy pipeline).
- Operational-coverage lens is a proxy for functional depth, not for operator readiness. Dealer readiness measures things this lens doesn't see (deploy, notify, export, invite).

### Signs of an obvious "day one" requirement missing

- **You cannot deploy this system to a dealer today.** Prod backend not active; frontend not deployed. Honest gap in `CAPABILITY_MATRIX.md:4203` since the pivot; has never become a milestone target.

### Signs of being closer than the process suggests

- M18 + M19 + M20 is a pilot-readiness triple that already shipped. Most projects at this stage don't have a codified 13-phase pilot dry-run test, an inventory-import CSV template doc, a pilot-onboarding playbook, and 6 executable persona journeys.
- Core operator surface is real — 30 routes, 431 Vitest tests, 26 Playwright journeys. If deployment + notifications + doc upload + invite land, this is a system a dealer could actually run.

**Net:** the roadmap is not measurably converging on dealer
readiness. It is compounding on functional coverage. Two different
denominators.

---

## 8. Recommendation for M36

**Not the F&I lender-submission continuation.**

### Preferred: Option E — preserve M35 as shipped, open M36 as an explicit "Launch-Readiness Arc" spanning several milestones

Rationale:

- F&I depth-arc is a valid *product* investment but primary blockers to a first pilot are *operational* — deploy, notify, invite, attach documents, export data. All have zero substrate and are not on the current candidate list.
- Continuing F&I depth at M36 postpones every launch-readiness item by another milestone. F&I depth remains available and cheap after each launch-readiness increment.
- M18–M20 already framed pilot readiness architecturally; M36 should re-adopt that lens instead of coverage density.

### Fallback: Option C — M36 as a single dealer-readiness milestone

If a full arc is too broad for one planning session, pick
**user-management UI + notification minimum** — highest
adoption-blocker impact per operator effort. This is a strict re-
scope of the primary operational-coverage lens toward *loops that
unblock real employee adoption* rather than *loops that add F&I
depth*.

### Do NOT default to Contract UI

It is the strongest F&I depth candidate but the wrong optimization
at this readiness stage.

---

## 9. Concrete path to first dealer

### Minimum launch boundary (standard A — pilot ready)

Six work packages in dependency order:

1. **Deploy pipeline** (Postgres, Redis, backup rotation, frontend host, DNS, HTTPS) — [~1 milestone; ~3 increments]
   - Wire Postgres via `DATABASE_URL` (schema already Postgres-ready)
   - Deploy Redis (Upstash / Fly Redis) for Celery broker
   - Backup: daily `pg_dump` to S3-compatible store
   - Frontend to Vercel with `VITE_API_PROXY_TARGET` env
   - Reconcile `render.yaml` stale CORS URLs
2. **User invitation + password reset UI** — [~1 milestone]
   - Owner email-invites salesperson; invitee sets password on first login
   - "Forgot password" flow via Django built-in reset framework
   - Role change UI (owner can promote/demote within their tenant)
3. **Notification minimum** — [~1 milestone]
   - Email-on-new-lead to assigned salesperson
   - Email-on-lender-response to F&I manager
   - In-app notification bell with unread count (uses existing `metadata` audit signals)
   - Transactional email via Resend / SendGrid / SES
4. **Document upload + deal jacket** — [~1 milestone]
   - `FileField` on new `DealDocument` model FK'd to Deal + Stipulation
   - Upload UI on F&I deal page + Stipulation row
   - S3/B2 blob storage (env-configurable)
   - Signed URLs for viewing
5. **Data export minimum** — [~1 increment inside a launch milestone]
   - CSV export of Deals + Sales + Trial-balance-as-of
   - PDF-print of a Deal (for the dealer to give the customer)
6. **Monitoring minimum** — [~1 increment]
   - `/health` + `/ready` endpoints
   - Sentry (free tier)
   - UptimeRobot / Better Uptime ping every 5 min
   - Resurrect `manage.py pilot_dry_run` (M19 retrospective deferral)

Rough total: **4 focused milestones + 2 increments** (~12 sessions
at current cadence).

### What can be deferred until after dealer #1

- MFA, SSO, account lockout
- Self-serve signup, billing
- Multi-tenant Celery Beat validation under load
- Cross-browser CI
- Additional F&I depth (Contract UI, Funding UI, Chargeback, alternate-lender resubmission)
- Direct-create structuring branch
- LenderProgram create UI
- All existing §3 deferrals

### What must be manually supported during the pilot

- Chris runs the deploy + backup restore
- Chris provisions the tenant via `POST /admin/pilots/create/` (M19.4 UI exists)
- Chris uploads inventory CSV or coaches the dealer through it
- Chris investigates via Django admin + logs when the dealer reports an issue
- Chris ships hotfixes on request

### Evidence needed before calling the pilot successful

- 30 consecutive days of the dealer's staff using Dealer OS as the primary system for at least one workflow (recommend F&I intake → submit → response since that is the newest and richest surface)
- Zero critical data loss (backup restore never triggered *in anger*)
- Chris intervention rate < once per week by day 30
- Owner reports one specific workflow ("this beats what we did before") in an open-ended interview
- Signed commitment to month 2 (paid or written)
- One workflow measurably faster or more accurate than pre-Dealer OS (surface metric agreed with dealer up front)

### What would stop Chris from putting this in a dealership today?

Ordered by decreasing severity:

1. Nothing is deployed. Local dev servers do not survive a dealer using the software on a Wednesday afternoon.
2. No backup. Even if deployed, one Postgres crash without backup ends the pilot.
3. No way for staff to know a new lead arrived. Polling isn't a workflow.
4. No signed-contract attachment. F&I compliance failure.
5. The owner cannot invite their sales manager. Chris does it every time; not sustainable.
6. No monitoring. Chris finds out about outages from angry texts.
7. No password reset. Chris resets every password personally.
8. No accountant-facing export. Month-end tax question requires shell access.

**Every one of these is a smaller lift than the M35 F&I arc that
just shipped. None is on the current M36 candidate list.**

---

## Verification / inference / unknowns

### Verified facts (against files or milestone docs cited)

- All ✅ dimension entries above inspected
- Test/route counts confirmed against this session's `manage.py test` + `npm test` + audit-artifact runs
- M18/M19/M20/M35 shipped state verified against `CAPABILITY_MATRIX.md §7s–7t–7u–7κ` and `PILOT_ONBOARDING_PLAYBOOK.md`
- Absence of Twilio/SendGrid/S3/Sentry verified against `requirements.txt` + `settings.py` search

### Architectural inference (defensible but revisable)

- Effort estimates (~4 focused milestones + 2 increments) inferred from M28–M35 velocity + M19 substrate scope; could be off by ±2 milestones
- Claim that "current strategy compounds on functional coverage, not launch readiness" inferred from milestone titles + candidate list + operational-coverage lens documentation; open to counter-evidence
- Ranking of "most acutely blocked workflow during a pilot" depends on the specific dealer; assumes an average 3–5-person indie lot

### Unknowns requiring real dealer validation

- Actual usability of current 30-route surface by non-technical staff
- Whether shipped F&I depth is *sufficient* for a real F&I manager or missing something not surfaced yet
- Real reliability of AI pipeline under a full workday's chat load
- Whether pilot playbook Phase 8 ("add users via Django admin") is *actually* tolerable for one pilot, or whether a dealer will bounce in week 1
- Real cost of running production (OpenAI usage per pilot, Postgres tier, Redis tier)
- Whether `MARKET_HANDOFF_BUNDLE.md` already resolves commercial blockers (not read end-to-end this session)

---

## Suggested next moves at resume

1. **User + ChatGPT review this assessment.** Confirm/reject the finding that launch-readiness is the right M36 lens.
2. **If confirmed:** open M36 as either a single dealer-readiness milestone (user-mgmt + notifications minimum) OR a launch-readiness arc (4 milestones as scoped in §9). Draft §5.b–§5.h against that scope.
3. **If rejected:** name the counter-evidence; the assessment reconciles or is superseded. Most likely counter-argument: "we already have a pilot pipeline and want more F&I depth before we spend a dealer's attention on it" — defensible if paired with a stated deadline for launch-readiness later.
4. **Do NOT lock M36 yet.** The prior M36 candidate list (F&I arc + Contract UI recommendation) is on pause pending this decision.

---

## References

- `docs/CAPABILITY_MATRIX.md` §7s (M18) + §7t (M19) + §7u (M20) + §7κ (M35)
- `docs/PILOT_ONBOARDING_PLAYBOOK.md` (M19.5)
- `docs/PILOT_INVENTORY_TEMPLATE.md` (M19.2)
- `docs/PROJECT_RULES.md` (rule 6 — build around operational problems)
- `docs/DOC_GOVERNANCE.md`
- `docs/research/INDEPENDENT_DEALER_PIVOT.md` (§Non-goals — the SaaS-shell boundary)
- `docs/roadmap/AUTHENTICATION_MODEL.md`
- `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
- `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md` §3 (M19 deferrals — several relevant to launch readiness)
- `docs/roadmap/MILESTONE_20_RETROSPECTIVE.md` §3
- `docs/handoffs/SESSION_219_dealer_readiness_assessment.md` (this session)
