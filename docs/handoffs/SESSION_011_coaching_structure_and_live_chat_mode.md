---
date: 2026-05-02
title: SESSION_011 — structural coaching enforcement + Live Chat Mode + shadcn install
type: implementation-summary
test_baseline: 1210
---

# Session handoff — coaching structure + Live Chat Mode + shadcn

Three threads landed in one session. They share a theme: making the
parts of the system that humans actually look at — the coaching
tester, the operator-facing translation layer, and the React shell —
behave reliably and consistently regardless of what the LLM produces
or what design language the codebase carries forward.

Use this snapshot to pick up at SESSION_012.

---

## What shipped

### 1. Manager-chat structural coaching enforcement

The SESSION_010 hotfix scrubbed banned phrases sentence-by-sentence
but didn't enforce the **shape** of the reply. Novel customer-facing
wording slipped through the gap. SESSION_011 closes that with a
hybrid approach: tightened prompt + post-LLM structural validator +
context-aware fallback.

**Two allowed shapes** for any manager-chat reply, declared in
`MANAGER_COACHING_HINT`:

- **Shape A — pure coaching.** Opens with stems like *"If a customer
  says…"*, *"I'd…"*, *"The assistant should…"*. No customer-facing
  phrasing.
- **Shape B — coaching + quoted preview.** Coaching frame surrounding
  a clearly-quoted sample reply. The quoted block is allowed to
  contain customer-facing language; the surrounding frame is not.

**`enforce_coaching_shape(reply, customer_message)`** in
`services/manager_chat_response.py` is the deterministic gate:

1. Strip any sentences matching the existing card-implying patterns
   (SESSION_010 scrub).
2. Strip double-quoted preview segments before the next check (so
   Shape B's inner sample reply doesn't false-positive trigger
   fallback).
3. Run two pattern families against the surviving text:
   - `_CUSTOMER_FACING_PATTERNS` (13 regexes — *the card*, *I can show
     you*, *fit your budget*, *would that be something*, etc.).
   - `_COACHING_FRAME_PATTERNS` (7 regexes — *if/when a customer*,
     *I'd open/start/narrow*, *the assistant should*, etc.).
4. If customer-facing patterns hit OR no coaching frame is detected,
   replace the reply with `_coaching_fallback(customer_message)` —
   a context-aware template that pulls vehicle type and budget hints
   from what the customer actually said.

The view (`views.py::manager_chat`) calls
`enforce_coaching_shape(result.assistant_message.content, customer_message=message)`
once, replacing the SESSION_010 direct scrub call. The customer-facing
chat path (`send_message`) is untouched — the enforcer lives in this
view only.

### 2. Jessica's failure case (2026-05-02 morning)

Replayed verbatim as a regression test
(`test_jessica_reported_failure_is_repaired`).

**Customer message:** *"i have $400/mo and want a sedan."*

**LLM output (broken):**
> *"Most sedans in our inventory fall under the payment shown on the
> card, but I can show you some options that might fit your budget.
> Would that be something you'd consider?"*

This sentence trips four customer-facing patterns (*in our inventory*,
*the card*, *I can show you*, *fit your budget*) and lacks any
coaching frame. The enforcer rewrites it to:

> *"If a customer says they want a sedan around $400/mo, I'd narrow
> the conversation before quoting any specific inventory: down
> payment, trade-in, must-have features, or whether they're flexible
> on year and mileage. The assistant should ask one focused
> qualifying question first. What's the priority for this customer?"*

The fallback template extracts the vehicle word (*sedan*) and budget
phrase (*$400/mo*) from the customer's message via
`_VEHICLE_TYPE_HINTS`, `_MONTHLY_PATTERN`, and `_CASH_PATTERN`.

### 3. Live Chat Mode added to the translation layer

The Jessica failure surfaced because she was talking with Claude in
plain English about what she saw — no jargon, no code references.
That conversation was the first real-world exercise of the workflow
we'd been calling "live chat mode" informally. SESSION_011
formalizes it as a first-class section in
`docs/FREEDOM_FORD_TRANSLATION_LAYER.md`:

- **Trigger phrases** — both explicit ("live chat mode", "talk to
  me like Jessica") and implicit (any operator reporting a real
  prompt + response + gut reaction).
- **Operator workflow** — five-lens translation: operator meaning →
  builder/system issue → dealer-owner risk → sales-manager workflow
  impact → Claude Code implementation task.
- **Vocabulary contract** — explicit prohibition list (*backend,
  frontend, code, files, endpoint, API, database, migration, commit,
  deploy, scrub, model, LLM, Ollama, regex, prompt*) with paired
  substitutions (*the system, the page she sees, the saved settings,
  save, guardrail, the assistant*).
- **Refusal rule** — what to do if the operator presses for technical
  detail (deflect first; if pressed, surface a one-sentence summary
  in their language; never paste code).
- **Grounding rule** — held to the same truth-preservation contract
  as every other mode. Specific anti-claim: *say "this improves
  manager-test reliability", not "this will increase sales".*
- **Worked example** — the SESSION_011 catch above, mapped through
  the five lenses.

`Last verified` updated to reflect the SESSION_011 baseline.

### 4. shadcn primitives + Tailwind v3 bridge

The frontend had all four shadcn prerequisites (`class-variance-
authority`, `clsx`, `tailwind-merge`, `lucide-react`) and `lib/
utils.ts` already in place but had never run `shadcn init`.
SESSION_011 installed it.

**Caveat:** the modern shadcn CLI (v4.6.0, `radix-nova` preset) ships
Tailwind **v4**-style CSS (`@import "shadcn/tailwind.css"` virtual,
`oklch()` colors, `has-data-*` / `not-aria-*` variants). The project
runs Tailwind **v3.4**. To avoid a project-wide v3→v4 migration in
this session, we bridged manually:

- `frontend/src/index.css` — stripped v4 virtual imports
  (`@import "shadcn/tailwind.css"`, `@import "tw-animate-css"`,
  `@import "@fontsource-variable/geist"`). CSS variables live under
  `@layer base { :root, .dark }`. Added `--destructive-foreground`
  (the v4 preset omitted it; v3 needs it for the destructive button
  variant). Ford `@layer components` block (`.btn-primary`,
  `.btn-ghost`, `.input`, `.card`) preserved verbatim.
- `frontend/tailwind.config.js` — Ford palette + Inter + soft shadow
  preserved. Added shadcn token mappings under `theme.extend.colors`
  using `var(--token)` directly (vars contain full `oklch(...)`
  expressions, so no `hsl()` wrapper). Added borderRadius mappings
  derived from `--radius`. Added accordion keyframes. Plugin:
  `tailwindcss-animate` (the v3 standard; replaces v4-only
  `tw-animate-css`).
- `frontend/components.json` — shadcn config (style: `radix-nova`,
  base color: neutral, css variables: true, icon library: lucide,
  tsx: true, rsc: false).

**12 primitives installed** in `src/components/ui/`: `button`, `card`,
`input`, `textarea`, `dialog`, `sheet`, `dropdown-menu`, `sonner`,
`badge`, `separator`, `avatar`, `tabs`. (`toast` was deprecated in
favor of `sonner` in modern shadcn.)

**5 deps added:** `radix-ui` (the new monorepo umbrella), `shadcn`
(CLI + helpers), `next-themes` (dark mode hook used by `sonner`),
`sonner` (toast replacement), `tailwindcss-animate` (v3 plugin),
plus minor bumps to `class-variance-authority` and `tailwind-merge`.
**2 deps removed:** `tw-animate-css` (v4-only), `@fontsource-
variable/geist` (preset-installed but unused — Inter is the project
font).

**One bug worth knowing about:** `npx shadcn init` overwrote
`src/lib/utils.ts` and dropped the project's `formatCurrency` helper.
Restored from `git show HEAD:frontend/src/lib/utils.ts` immediately
afterward, before the build attempt.

### 5. Playwright MCP installed

Registered at the Claude Code config level via:

```
claude mcp add playwright -- npx -y @playwright/mcp@latest
```

`claude mcp list` reports it as `Connected`. **Tools are not visible
in the session that installed it** — MCP tool schemas load at
session start. SESSION_012 needs to start in a fresh Claude Code
session for `mcp__playwright__browser_navigate`,
`mcp__playwright__browser_take_screenshot`, etc. to be callable.

---

## File changes

```
backend/
  dealer_ai/
    services/manager_chat_response.py       (rewrite, +365 -30)
    views.py                                 (+15 -8)
    tests/test_manager_chat.py               (+~270 lines, +21 tests, 4 mocks updated)

docs/
  FREEDOM_FORD_TRANSLATION_LAYER.md          (+155, Live Chat Mode section + Last verified)

frontend/
  components.json                            (new — shadcn config)
  package.json                               (deps in/out as above)
  package-lock.json                          (corresponding lockfile updates)
  tailwind.config.js                         (rewrite — color mappings + plugin)
  src/
    index.css                                (rewrite — strip v4 imports, add base/dark vars)
    lib/utils.ts                             (formatCurrency restored)
    components/ui/                           (new — 12 primitives)
      avatar.tsx
      badge.tsx
      button.tsx
      card.tsx
      dialog.tsx
      dropdown-menu.tsx
      input.tsx
      separator.tsx
      sheet.tsx
      sonner.tsx
      tabs.tsx
      textarea.tsx

CLAUDE.md                                    (+44, Frontend stack notes — bridge)
.claude/skills/context-kit/SKILL.md          (upstream Live Chat Mode skill cp'd in)
```

Test baseline: **1189 → 1210 pass / 1 skip / 0 fail** (+21 new tests).

---

## Verification

```
# Backend
cd backend
python manage.py test dealer_ai
# → Ran 1211 tests, 1210 OK, 1 skipped, 0 failed.

# Frontend
cd frontend
npx tsc --noEmit
# → exit 0 (clean)
npx vite build
# → ✓ 1594 modules transformed, 45.79 kB CSS / 343.35 kB JS, 919ms

# Manual coaching-mode replay (Jessica's case)
curl -s -X POST http://localhost:8001/api/dealer-ai/manager-chat/ \
  -H 'Content-Type: application/json' \
  -d '{"message": "i have $400/mo and want a sedan"}' | jq -r .reply
# → coaching-shaped reply, never the "I can show you / the card" leak.
```

---

## Limitations / known gaps

### 1. Six v4-only variant patterns in installed shadcn primitives

The `radix-nova` preset uses Tailwind v4-only modifiers in its
generated `button.tsx` and `card.tsx`. They silently no-op under v3
(no build error, no matching CSS generated):

| Pattern | File | Effect when no-op |
|---|---|---|
| `has-data-[icon=inline-end\|inline-start]:` | button | Icons in buttons get default padding instead of icon-aware reduced padding. |
| `has-data-[slot=card-action]:` | card | Card layout doesn't shift to grid when an action slot is present. |
| `has-data-[slot=card-description]:` | card | Card description spacing stays default. |
| `has-data-[slot=card-footer]:` | card | Card footer doesn't get auto-padding adjustment. |
| `in-data-[slot=button-group]:` | button | Buttons inside button-groups don't auto-flatten corners. |
| `not-aria-[haspopup]:translate-y-px` | button | Tiny click micro-animation skipped. |

Components render correctly — just slightly less polished than full
v4 nova. **Do not author new code that depends on these variants.**
The bridge note in `CLAUDE.md` § *Frontend stack notes* is canonical
for this constraint.

### 2. When the coaching enforcer fires the fallback, onboarding tone is lost

The fallback template is deterministic and doesn't carry the
SESSION_009 onboarding tone overrides (`format_store_voice_block`'s
greeting / sales tone / approved-phrase nudges). On-shape replies
from the LLM still get tone shaping upstream in `chat_engine`; only
fallback-rewritten replies are toneless. Fine because the
fallback-eligible reply was, by definition, the broken one we
discarded — but worth knowing if a manager observes a tone shift
between adjacent test prompts.

### 3. Customer-facing pattern set is denylist-shaped

`_CUSTOMER_FACING_PATTERNS` enumerates the phrasings we've actually
seen leak. Novel customer-facing wording the LLM hasn't produced yet
won't trip detection until added. Coverage today is good for the
demo prompt set; expect to extend the list as Jessica explores more
customer scenarios.

### 4. Salesperson seed still not linked to `Salesperson` model

Carried forward from SESSION_010. `DealerOnboardingProfile.salesperson_seed`
holds JSON the manager enters; the existing `Salesperson` row used by
`/dealer-ai-admin/team` is unrelated. Linking them is in
`ASSISTANT_AGENT_CREATION_ROADMAP.md`.

### 5. Playwright MCP not visible in this session

Installed but only callable from a fresh Claude Code session. The
SESSION_012 flow starts with a restart.

---

## Recommended next session (SESSION_012)

**Theme: UI redesign — make it feel like a real dealership product.**

The backend is stable (1210 / 1 skip / 0 fail). The behavior layer,
translation layer, and onboarding wiring are all in place. The
remaining demo-readiness gap is visual: the React shell is functional
but doesn't yet feel like a product a dealer principal would expect.

### Goals

1. **Refactor the 17 hand-rolled domain components** in
   `frontend/src/components/` to compose shadcn primitives underneath
   while preserving each component's business contract:
   - `LeadDetailModal`, `VehicleDetailModal`, `GenerateAdModal`,
     `FollowUpDraftModal`, `LeadCaptureModal` → built on
     `ui/dialog.tsx`.
   - Dropdowns inside `AssignmentDropdown`, `MyLeadsTable`,
     `RecommendedActions` → `ui/dropdown-menu.tsx`.
   - `StatCard`, `SalespersonCard`, `VehicleCard`, `ChatVehicleCard`
     → `ui/card.tsx` underneath, Ford palette on top.
   - `HandoffQueue`, `MyLeadsTable`, `SalesPipeline` → `ui/tabs.tsx`
     where multi-state, `ui/badge.tsx` for status pills,
     `ui/separator.tsx` between sections.
   - Toast/sonner integration for `LeadCaptureModal` success/error
     states.
2. **Standardize the dealer OS shell** — header, side nav, page
   chrome — so every page (`/dealer-ai-admin`, `/dealer-ai-onboarding`,
   `/dealer-ai-demo`, `/dealer-ai-manager-chat`,
   `/dealer-ai-advisor/<slug>`) shares the same frame, spacing
   tokens, and brand surfaces. Ford palette for brand chrome, shadcn
   neutrals for input/dialog/dropdown surfaces.
3. **Verify each redesigned page with Playwright screenshots**
   before reporting done. Frontend dev server runs at port 5173 with
   the `VITE_API_PROXY_TARGET` env override pointing at the backend.

### Out of scope for SESSION_012

- Tailwind v3 → v4 migration (revisit after the redesign lands).
- New backend endpoints, new agent behavior, new persistence.
- Live Chat Mode workflow with Jessica during the redo (re-engage her
  once SESSION_012 ships and there are real before/after screenshots).
- Authoring code that depends on the six v4-only variants listed
  above.

### Acceptance signals

- All 17 hand-rolled components either compose a shadcn primitive
  under the hood or have an explicit reason recorded in the file
  comment for staying hand-rolled.
- Every page renders without console errors at port 5173.
- Playwright captures a screenshot per page; visual review by the
  human confirms each shell feels coherent.
- Backend baseline holds at 1210 / 1 skip (no backend churn this
  session unless a frontend change exposes a wiring bug).

---

## Pointers for the next session

Read in this order on restart:

1. `docs/FREEDOM_FORD_SESSION_START.md` — entry point, baseline.
2. `00-START-NEXT-SESSION.md` — SESSION_012 priorities (hand-written
   block below the adopt block).
3. This handoff (`SESSION_011_coaching_structure_and_live_chat_mode.md`).
4. `CLAUDE.md` § *Frontend stack notes* — Tailwind v3 + shadcn bridge
   constraints.
5. `docs/FREEDOM_FORD_TRANSLATION_LAYER.md` § *Live Chat Mode* — when
   Jessica re-engages.

After restart, confirm Playwright is callable:

```
claude mcp list
# expect: playwright: ... ✓ Connected
```

Then ToolSearch for `playwright` and the
`mcp__playwright__browser_*` tools should be available.
