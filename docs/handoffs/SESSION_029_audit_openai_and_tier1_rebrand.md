---
date: 2026-07-30
title: SESSION_029 — cleanup audit, OpenAI swap, Tier 1 rebrand
type: implementation-summary
test_baseline: 1218 pass, 1 skipped (unchanged)
---

# Session handoff — cleanup audit + OpenAI swap + Tier 1 rebrand

Three phases in one session:

1. **Audit + cleanup** — verify what previous handoffs claimed as
   shipped, land the pieces that had drifted uncommitted, refresh
   context-kit hygiene.
2. **LLM provider swap** — Ollama → OpenAI `gpt-5-mini`, including
   provider code changes to handle reasoning-model parameter shape.
3. **Tier 1 rebrand** — templatize dealer identity throughout the
   stack so no user-visible surface hardcodes "Sam Wampler" or
   "Freedom Ford" anymore.

Also: took the Vercel frontend offline pending rebrand, reset the
persisted `OnboardingProfile`, and killed the local Ollama process.

---

## Phase 1 — cleanup audit (5 commits)

Verified each previous session's "shipped" claims against runtime
state. Findings + fixes:

- **`4d9bac3` `feat: land SESSION_024 public assistant polish`** —
  SESSION_024's handoff claimed the `VehicleMatchDeck` (3-card
  stacked carousel), the softer "current inventory / payment-aware"
  copy, and the `min-w-0` guard were shipped. All four sat as
  uncommitted diffs in the working tree. Landed them.
- **`d8f6af9` `docs: backfill session handoffs 024-027`** — the four
  handoff docs were untracked in the working tree; `c2c2067`
  (sessions 024–027 bundle) never picked them up. Committed verbatim
  with a note flagging SESSION_024's "already shipped" claim as
  inaccurate at the time.
- **`d516958` `chore: normalize dev host to 127.0.0.1 + expand CORS
  defaults`** — Vite proxy target + Django CORS defaults now use
  `127.0.0.1` instead of `localhost` (avoids IPv6 `::1` resolution
  breaking the /api proxy on macOS + Node). Reverted a WIP `api.ts`
  change that would have bypassed the Vite proxy AND pinned port
  8000 while Django runs on `:8001`.
- **`d0e80fc` `chore: ignore redesign/ scratch dir and vercel-link
  artifacts`** — `/redesign/` (competitor comparison screenshots)
  and `frontend/.vercel/` gitignored.
- **`9754830` `docs: refresh start-here + regen inventory`** —
  `00-START-NEXT-SESSION.md` corrected from SESSION_027 → 028 as
  last shipped; inventory regenerated (24 handoffs, 255 tracked
  files at that point).

**Test suite baseline confirmed:** `python3 manage.py test` returned
1218 pass, 1 skipped.

---

## Phase 2 — OpenAI swap (`76a5f2e`)

Local dev now uses OpenAI `gpt-5-mini` instead of Ollama.

- `backend/.env`: `DEALER_AI_LLM_PROVIDER=openai`,
  `OPENAI_MODEL=gpt-5-mini`.
- `OPENAI_API_KEY` lives in the repo-root `.env` (gitignored,
  untracked).
- `backend/freedom_ford/settings.py` now loads **two** `.env` files:
  `backend/.env` first, then repo-root `.env` with `override=True`
  so secrets kept at the root win.
- **`backend/dealer_ai/services/llm/openai_provider.py` gained
  reasoning-model support.** gpt-5-mini (and any `gpt-5*`, `o1*`,
  `o3*`, `o4*` variant detected by name prefix) requires:
  - `max_completion_tokens` (not `max_tokens`)
  - default `temperature` only (any other value returns 400)
  - Larger budget (`max(caller*2, 1200)`) because reasoning tokens
    are burned before content tokens.

Live-tested with a real chat request. Deterministic vehicle
matcher still returned 5 matched trucks for "truck under $40k with
towing" — confirming the swap didn't regress the backend math.

**Ollama** is stopped locally; can be re-enabled by flipping
`DEALER_AI_LLM_PROVIDER=ollama` in `backend/.env` and starting
`ollama serve`.

---

## Phase 3 — Tier 1 rebrand (`71f5d48`)

Removed all hardcoded "Sam Wampler" / "Freedom Ford" references
from user-visible surfaces. **Runtime dealer identity is now
templated** — the same code works for any dealership.

### New backend module

`backend/dealer_ai/services/dealer_config.py` exposes:

```python
def get_dealer_name() -> str:
    """Resolution order:
       1. settings.DEALER_AI_DEALER_NAME env
       2. DealerOnboardingProfile.dealership_name (DB singleton)
       3. "the dealership" (bland fallback)"""
```

New env var: `DEALER_AI_DEALER_NAME` (empty by default), wired
through `settings.py`.

### Templating pattern

Every LLM system prompt + every canned response constant in these
files now contains `{dealer_name}` as a placeholder:

- `chat_engine.py` (SYSTEM_PROMPT + 6 response constants + guard
  reply builders + the CONVERTIBLE-SPECIFIC NOTE injected into
  prompts + "Prioritize Ford" rule rewritten neutrally)
- `vehicle_assistant.py`
- `handoff_service.py` (including sign-offs like "Talk soon,\n{dealer_name}")
- `follow_up.py` (SMS/email drafts + fallback templates)
- `lead_service.py`
- `ad_copy.py`

Each module has a `_render(template) -> str` helper that formats
against `get_dealer_name()` at call time (not import time), so a
Setup UI change or an env flip takes effect immediately.

### Serializer defaults

`backend/dealer_ai/serializers.py` `ONBOARDING_DEFAULTS`:
- `dealership_name`: `"Freedom Ford"` → `""`
- `main_brands`: `"Ford (new) + multi-brand used"` → `""`

### Frontend

- `DEFAULT_DEALER` in `frontend/src/config/defaultDealer.ts`
  neutralized to `"Your Dealership"` + empty fields.
- `frontend/index.html` `<title>` → `Dealer AI Kit` (no dealer).
- Hero, SiteNav, LeadCaptureModal, GenerateAdModal, DealerAIDemo
  now interpolate `brand.dealershipName` / `brand.tagline` via
  `useBrand()` instead of hardcoding "Freedom Ford" / "Sam Wampler".
- "Find your next Ford" hero copy → "Find your next ride". Trade-in
  placeholder de-Ford-ified.
- Historical Sam Wampler / Freedom Ford examples in `brand.ts`,
  `EmbedAssistantPage`, `AssistantChat`, `AssistantVehicleCard`
  comments rewritten with generic placeholders.

### Tests

46 tests broke because they asserted on "Freedom Ford" strings.
Fixed **without changing intent** via:

- `@override_settings(DEALER_AI_DEALER_NAME="Freedom Ford")` at
  class scope in 4 test files (`test_follow_up.py`,
  `test_handoff_and_reset.py`, `test_post_llm_safety.py`,
  `test_vehicle_assistant.py`) — 16 classes total.
- Where tests did `assertEqual(response, TEMPLATE_CONSTANT)`, the
  assertion now wraps the constant with `_render(...)`.
- Two substring assertions ("freedom ford advisor") flipped to
  match the reworded phrasing "advisor from freedom ford".

### DB reset

Cleared the persisted `DealerOnboardingProfile` fields
(`dealership_name`, `store_location`, `dealership_greeting`,
`main_brands`, `logo_url`). `get_dealer_name()` now returns the
bland fallback `"the dealership"` until a new dealer name is
configured.

---

## Verification

- `python3 manage.py test` → **1218 pass, 1 skipped** (baseline
  preserved).
- `npx tsc --noEmit` → clean.
- `npx vite build` → clean, 488 kB / 133 kB gzip.
- `grep -rnE "Sam Wampler|Freedom Ford" frontend/src frontend/index.html
  backend/dealer_ai/services backend/freedom_ford` → **zero
  matches** except one historical docstring in `dealer_config.py`
  explaining what the module replaces.
- Live smoke: `POST /api/dealer-ai/chat/message/` with an identity
  challenge returned *"I'm the AI assistant for the dealership—I'm
  here to help you with vehicles and get you connected with a real
  advisor when you're ready."* — templating flowed end-to-end
  through the actual request path.
- Live smoke: `GET /api/dealer-ai/onboarding/profile/` returned
  `dealership_name=""`, `main_brands=""`, `logo_url=""` confirming
  the DB reset.

---

## Deployment state (unchanged from earlier this session)

- **Vercel frontend** at `vehicle-match-pi.vercel.app` — **DELETED**
  via the Vercel dashboard partway through this session, to prevent
  Sam Wampler branding from remaining publicly reachable while we
  rebrand. Repo + GitHub remote (`clwest/vehicle-match`) intact.
  `frontend/.vercel/` local link removed.
- **Render backend** at `vehicle-match-api.onrender.com` — still
  NOT active (Blueprint never activated in SESSION_028).

The CORS mismatch we flagged for the old Vercel URL is no longer
blocking anything because the frontend is gone. `render.yaml`'s
`CORS_ALLOWED_ORIGINS` still points at `vehicle-match.vercel.app`;
that needs a rebrand-time update when a new frontend is deployed.

---

## Not touched (intentional Tier 2 / Tier 3 scope)

**Tier 2 — data still says Ford:**
- Every demo vehicle (Maverick, Ranger, F-150, Bronco, etc.) in
  `backend/dealer_ai/management/commands/seed_demo_vehicles.py`
- Scenario copy in
  `backend/dealer_ai/management/commands/seed_demo_scenarios.py`
- "Repeat Freedom Ford customer" note in
  `backend/dealer_ai/management/commands/seed_phase3_demo.py`
- `frontend/src/data/freedomFordInventorySample.ts` contents
- Backend tests use "Freedom Ford" as fixture data — safe (kept
  intentionally so `@override_settings` decorator works)

**Tier 3 — identifiers not text:**
- Tailwind `ford.blue`, `ford.accent`, `ford.ink`, `ford.ash`,
  `ford.mist` color tokens (used everywhere via `bg-ford-blue`)
- `backend/freedom_ford/` Django project module path (settings
  live at `freedom_ford.settings`)
- `frontend/public/branding/sams-freedom-ford-logo.jpg` asset
- `frontend/src/data/freedomFordInventorySample.ts` filename

---

## Recommended next session (SESSION_030)

You now have three sensible tracks. Pick one, or set a dealer name
first and evaluate visually before deciding scope.

### Option A — Configure a real dealer name and end-to-end demo

Fastest path to seeing the templating work: set
`DEALER_AI_DEALER_NAME=<real name>` in `backend/.env` (or via the
`/dealer-ai-onboarding` UI), reload Django, and walk through the
public assistant + admin surfaces to see how the templated copy
reads with a real brand. No code changes; ~15 min.

### Option B — Tier 2 rebrand (seed data)

Neutralize the Ford-only demo inventory + scenario copy so the demo
stops "looking like a Ford dealer." Requires deciding what the new
sample inventory looks like — mixed makes, or configurable per
dealer? This is where the demo character changes most visibly.

### Option C — Focus on the admin dashboard

Original ask that got derailed by the strip mishap. The
`/dealer-ai-admin` route is unreachable from the sidebar. Two
quick moves: add "Admin" to the sidebar nav, then decide what to
improve on that page (trends, pipeline, handoff queue, audit,
ad-copy generator).

### Deferred (still valid)

- SESSION_004–007 handoff gap — either annotate as "never existed
  and numbering skipped" or fill placeholders.
- Adopt placeholders in `docs/PROJECT_WHAT_IT_IS.md` and
  `docs/BUILD_PLAN.md`.
- `render.yaml` CORS hostname update if/when a new frontend gets
  deployed.

---

## Post-handoff follow-ups (same session, after this doc was first written)

- **`7a91255` `feat: surface /dealer-ai-admin in sidebar`** — The
  `DealerAdmin` page (trends, sales pipeline, handoff queue, audit
  panel, recommended actions with **trending-signal-driven ad-copy
  generator**, demo reset) was previously reachable only via direct
  URL. Added an "Admin" sidebar entry between "Coaching Mode" and
  "Team" with `end: true` so the active-link styling doesn't stick
  when the Team sub-route is open.

- **`2e0977c` `docs: add CAPABILITY_MATRIX.md`** — New durable
  artifact at `docs/CAPABILITY_MATRIX.md`. Records what the platform
  actually does today, backed by runtime evidence rather than
  narrative claims. Covers 12 capability areas + honest gaps. Has
  frontmatter tracking (`last_verified`, `verified_against_commit`)
  so future sessions know when to re-walk the doc.

  **The trending-signal ad-copy flow is documented explicitly in
  Section 6.** Recommendations are computed by `pipeline.py`'s
  `recommended_actions()` from `trends_snapshot()` — top requested
  models, top vehicle types, most-selected units. Cards with
  `category` in `{inventory, marketing}` get a "Generate ad" button
  that opens `GenerateAdModal` (POSTs to `/admin/ad-copy/`).
