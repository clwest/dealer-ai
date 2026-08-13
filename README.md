# Dealer AI

A dealership operating system for independent used-car dealers
that models inventory, reconditioning, leads, deal structure,
F&I, BHPH (buy-here-pay-here), accounting, and collections
workflows. An LLM-powered chat surface sits on top of deterministic
dealership rules and compliance guardrails.

The shipped default persona is a fictional independent lot
(Copper Canyon Auto, Yuma, AZ) with 45 mixed-make used vehicles.
Franchise dealers are supported via env-override configuration
(`DEALER_AI_DEALER_TYPE=franchise`, `DEALER_AI_PRIMARY_MAKE=<make>`).

## Who it is designed for

- **Primary:** independent used-car dealership operators (owner /
  GM / sales manager) at 1–3 rooftop lots, especially those
  serving credit-challenged or BHPH-heavy segments (~$3k–$25k
  price band, mixed-make used inventory).
- **Secondary:** franchise dealers who want a compliant AI sales
  layer their OEM does not provide, via env override.

## Core dealership workflows

Every capability below is implemented end-to-end (backend model
+ REST endpoint + React UI + at least one test):

- **Vehicle chat assistant** — customer-facing chat, embeddable
  as an iframe on the dealer's own website; operator-side live
  chat surface for advisors.
- **Multi-channel lead intake** — chat, walk-in, phone, referral,
  webhook.
- **Inventory** — vehicles, acquisition costs, cost ledger,
  lifecycle stages (incoming → inspection → recon → QC →
  listing → frontline), photos, listing editor.
- **Recon workflow** — condition report → findings → tiered
  decisions (must_do / should_do / won't_do) → work orders →
  vendor communications → cost tracking.
- **Sales → F&I handoff** — deal writeup, four-square terms
  capture, credit application intake, F&I intake queue.
- **Deal desking** — deal structure (LTV / PTI / DTI ratios),
  standard-APR amortization, tax + fees + trade-in equity.
- **Lender submission + response tracking** — record submission
  to a lender program, record response (approved / countered /
  declined) with terms.
- **BHPH portfolio** — payment intake (weekly / biweekly
  cadence), payment allocation (interest → fees → principal),
  delinquency detection, promise-to-pay, collection contact log,
  repossession.
- **Accounting** — chart of accounts, journal entries with
  double-entry lines, trial balance snapshots, entry reversal.
- **Scheduled background jobs** — floor-plan interest accrual,
  daily stage-age snapshots, vendor SLA breach detection, photo
  tombstone reaping, follow-up surfacing, be-back no-show
  detection, BHPH delinquency + broken-promise detection, GL
  posting for vehicle costs and BHPH payments.

## Architecture

- **Backend:** Django 5 + Django REST Framework, Celery + Redis,
  PostgreSQL (SQLite fallback for dev). Single Django app
  (`dealer_ai/`) under project package (`dealer_kit/`). ~60
  models, ~160 URL routes, 10 scheduled Celery beat jobs, 54
  service modules.
- **Frontend:** React 18 + Vite + TypeScript strict, shadcn/ui
  on Tailwind 3 with dealer-agnostic `brand.*` tokens,
  react-router 6. ~35 routes, ~112 components. No client-side
  query cache; every page is explicit about its data fetches.
- **Acceptance:** Playwright with a persona-per-project setup
  (six operator personas — platform_operator, owner,
  sales_manager, recon_manager, bhph_collector, f_and_i_manager
  — each with its own storage-state auth; the accounting
  Playwright project reuses the owner persona because
  accounting endpoints are dealer-owner-gated). Twenty journey
  specs framed as **operational acceptance contracts**: each
  spec asserts a business outcome (e.g. "F&I can start a deal
  structure"), not just that buttons were clicked.

Deeper architecture reading:
- [`docs/PROJECT_PIPELINE.md`](docs/PROJECT_PIPELINE.md) — the
  pre-LLM guard chain and post-LLM scrub stack, plus known
  entry-point asymmetries.
- [`docs/DEALER_KIT_BEHAVIOR_LAYER.md`](docs/DEALER_KIT_BEHAVIOR_LAYER.md)
  — chat behavior layer.
- [`docs/DEALER_KIT_TRANSLATION_LAYER.md`](docs/DEALER_KIT_TRANSLATION_LAYER.md)
  — persona / translation-mode contract.

## AI's actual role

The LLM is a natural-language interface over a rule-based
engine. It does not make payment decisions, rank inventory,
detect compliance violations, or call external tools. Those all
run in deterministic Python code. The LLM's job is to converse
with the customer or operator and produce responses that get
filtered through the safety pipeline before display.

Implemented today:

- Two-provider factory (Ollama default for local / free, OpenAI
  optional) at `backend/dealer_ai/services/llm/`.
- Pre-LLM prompt-guard chain (~8 guards: injection detection,
  dealer-cost leakage, APR-inquiry, external-valuation ask,
  identity, negotiation, image request, appointment).
- Post-LLM scrub pipeline (~12 scrub functions covering
  W.A.C./rate-language, dealer-cost text, invented promotions,
  invented appointments, invented recon facts, FDCPA collection
  language, indie-prohibited copy).
- Intent parser + keyword-based inventory search (deterministic
  ORM filtering, primary-make-first ordering).

## Deterministic finance / accounting logic

The math is entirely in Python, not the model:

- **Standard-APR amortization** for retail deals through F&I
  (`services/payment_engine.py::estimate_payment`).
- **BHPH amortization** with weekly (52 periods/yr) or biweekly
  (26 periods/yr) cadence (`estimate_bhph_payment`), plus a
  portfolio-typical minimum-down-payment policy floor.
- **Deal-structure ratios** — LTV, PTI, DTI, all Decimal-based
  (`services/f_and_i/deal_structure.py`).
- **Payment allocation** — BHPH payments split interest → fees
  → principal in that order
  (`services/bhph_payments/allocation.py`).
- **GL posting** — immutable journal entries, corrections
  through reversal entries; `posted_at` sentinels prevent
  double-posting; scheduled Celery task posts vehicle costs +
  BHPH payments daily
  (`services/accounting/journal.py`, `vehicle_cost.py`,
  `bhph_payment.py`).

See [`docs/case-studies/`](docs/case-studies/) for the strongest
concrete examples of dealership-domain decisions in code.

## Multi-tenant / role model

- **Tenant model:** `Dealership` — one row per dealership.
  Signal-driven auto-attach on write-side; header-and-membership
  driven read-side scoping.
- **Roles:** owner, sales_manager, recon_manager,
  f_and_i_manager, bhph_collector, advisor, platform_operator
  (via `UserDealershipRole`).
- **Isolation:** each service module raises `CrossTenant*Error`
  when a caller from tenant A attempts to touch a record owned
  by tenant B. Views translate the exception to HTTP 404
  (fail-closed).
- **UI gating:** `hasRole()` hook in the frontend gates
  role-only write surfaces; the backend enforces the same rules
  via custom `IsSalesManagerOrOwnerAtActiveDealership`-style
  permission classes.

## Testing strategy

- **Backend:** 5,045 Django tests (`python manage.py test
  dealer_ai` — 1 skipped, 0 fail, ~178s on a clean install).
  Test files are organized per-milestone. Load-
  bearing suites include the 1,224-line
  `test_admin_vehicle_ledger.py`, the BHPH payment engine
  tests, the W.A.C. compliance scrub tests, and the F&I
  permission-matrix tests.
- **Frontend:** 431 Vitest tests across 47 files
  (`npm run test` under `frontend/` — 0 fail, ~7s). Covers
  component behavior, form validation, API-client typing.
- **Acceptance:** 20 Playwright journey specs in `acceptance/`
  (each spec contains one or more `test(...)` cases against the
  seeded fixture for its persona). Runs on every PR
  (pilot-critical subset, ~90s) and full-suite on push to
  `main`. See
  [`.github/workflows/acceptance.yml`](.github/workflows/acceptance.yml).
- **Unit-test CI:** backend + frontend gated on every PR and
  push. See
  [`.github/workflows/backend-tests.yml`](.github/workflows/backend-tests.yml).
- The acceptance suite uses a `@rerun-hygiene` tag on specs
  whose outcome depends on seed restoration between runs; both
  invocations must pass to prove the invariant. See
  [`docs/case-studies/03-playwright-rerun-hygiene.md`](docs/case-studies/03-playwright-rerun-hygiene.md).

## How to run locally

Requires Python 3.12, Node 20, and (optionally) Ollama.

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                    # edit if you want OpenAI
python manage.py migrate
python manage.py seed_demo_vehicles     # 45 demo vehicles
python manage.py seed_demo_scenarios    # 5 demo chats + leads
python manage.py runserver              # http://localhost:8000

# 2. LLM (local, free) — separate terminal (optional)
ollama pull llama3.1
ollama serve                            # http://localhost:11434

# 3. Frontend — separate terminal
cd frontend
npm install
npm run dev                             # http://localhost:5173

# 4. Acceptance (optional) — separate terminal
cd acceptance
npm install
npx playwright install --with-deps chromium
npx playwright test
```

If Ollama is not running, chat gracefully falls back to a clear
"trouble reaching the AI service" message; the rest of the app
(inventory, payment math, dashboards, accounting) does not depend
on the LLM.

## Screenshots

Product screenshots live in [`docs/screenshots/`](docs/screenshots/).
Populated during the clean-install rehearsal — regenerate with
fresh captures rather than relying on historical dev snapshots.

## Known limitations / not implemented

The following are intentionally *not* built. They are documented
gaps, not stubs pretending to work.

- **No live DMS integration.** Inventory intake is via CSV
  management command or the seed fixtures.
- **No lender API integration.** Lender submissions record the
  status and terms manually; no outbound HTTP to lender
  systems.
- **No payment processor integration** (Stripe / Square / etc.).
  BHPH payments are recorded manually; card capture is not
  wired.
- **No email / SMS outbound.** `method` fields exist on
  vendor / customer communication models; no Twilio / SendGrid /
  SES integration.
- **No embeddings / RAG / pgvector.** Inventory search is
  keyword + ORM.
- **No agent framework** (LangChain / LangGraph / etc.). No
  tool/function calling. The chat is a single-turn orchestrator:
  guard → intent extract → inventory search → LLM(intent) →
  LLM(reply) → scrub → return.
- **No streaming responses** (SSE / WebSocket). Chat replies
  are synchronous request/response.
- **No credit-bureau integration.**
- **Not deployed to real dealerships.** The shipped default
  persona is fictional; the
  [`docs/PILOT_ONBOARDING_PLAYBOOK.md`](docs/PILOT_ONBOARDING_PLAYBOOK.md)
  exists but no live pilot has run against this software.

## AI-assisted development disclosure

The bulk of the implementation was written by Claude Code under
milestone-driven direction. The engineering judgment — scope
decisions, deferrals, empirical verification of risk-registered
assumptions, correction of failed planning assumptions,
documented durable lessons — was human. See
[`AI_ASSISTED_DEVELOPMENT.md`](AI_ASSISTED_DEVELOPMENT.md) for
specifics.

## License

MIT. See [`LICENSE`](LICENSE).
