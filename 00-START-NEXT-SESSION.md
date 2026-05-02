---
state: active
date: 2026-05-02
last_session_shipped: SESSION_022
next_session: SESSION_023
---

# Next session — Dealer AI Kit

> **Platform reframe note:** This codebase is the **Dealer AI
> Kit** — a reusable dealer AI platform. Sam Wampler's Freedom
> Ford McAlester is Dealer #1 and the default configuration. See
> `docs/PLATFORM_REFRAME.md` for the identity hierarchy and
> `docs/DEALER_DUPLICATION_GUIDE.md` for the operator workflow
> to onboard a second dealer without forking.

## What just shipped (SESSION_022)

**Assistant-first public dealership website.** The app no longer drops
visitors at the operator OS by default. `/` is now a public dealership
homepage built around the AI assistant, `/assistant` is a full-page
customer assistant, and `/showroom` is a public demo inventory surface
with "Ask AI" CTAs. The existing `/dealer-ai-*` operator routes remain
inside the Dealer AI Kit shell, and `/embed/assistant` remains unchanged.

Read the full handoff at
`docs/handoffs/SESSION_022_assistant_first_public_site.md`.

**Verification from SESSION_022:**

- `npx tsc --noEmit` — pass.
- `npx vite build` — pass.
- Playwright smoke:
  - `/` → `Find your next Ford with help, not pressure.`
  - `/assistant` → `Start with what matters to you.`
  - `/showroom` → `Browse the lot, then ask the assistant to narrow it.`
  - `/dealer-ai-overview` → `Overview`
  - console warnings/errors: `[]`

No backend changes. No chat behavior changes. No edits to
`AssistantChat`, `EmbedAssistantPage`, `/dealer-ai-demo`, or
`defaultDealer.ts`.

---

## Recommended next session — SESSION_023

**Monday demo hardening for the assistant-first public site.**

The prior Leads pipeline recommendation is still valid, but it is not
the right next move until the Monday public-site demo is locked. SESSION
023 should harden the exact visitor journey that will be shown live.

**Scope:**

- Walk the Monday demo path across:
  - `/`
  - `/assistant`
  - `/showroom`
  - `/embed/assistant`
  - `/dealer-ai-overview`
- Verify desktop and mobile visual fit with Playwright screenshots.
- Tighten spacing, sizing, and copy where the public site still reads
  like a prototype.
- Decide whether `/assistant?prompt=...` should stay as "starter chip
  first" or become a controlled auto-send flow.
- Consider adding a tiny repeatable Playwright smoke script now that
  `playwright` is installed.
- Keep the public site assistant-first. Do not drift back to a generic
  dealership landing page.

**Strict guardrails:**

- ❌ No backend changes unless a real blocker appears.
- ❌ No chat behavior changes.
- ❌ No edits to `AssistantChat` unless the demo reveals a purely
  presentational issue that affects both public assistant and embed.
- ❌ No edits to `EmbedAssistantPage` unless verifying the Monday path
  reveals a regression.
- ❌ No edits to `/dealer-ai-demo`.
- ❌ No edits to `DEFAULT_DEALER` / `PRODUCT` / `defaultDealer.ts`.
- ❌ No new public inventory contract; showroom stays on the existing
  SESSION_014 sample snapshot until CRM/DMS work is explicitly in scope.

**Defer until after the Monday public-site demo is locked:**

- Leads pipeline page.
- Multipart logo upload.
- CSP / X-Frame allowlist.
- Inventory data quality cleanup.
- Live brand broadcast on Setup save.

---

## Agent launch prompt for SESSION_023

Paste into Claude Code / Cursor / any AI coding agent as the session
opener.

```text
You are picking up SESSION_023 on the Dealer AI Kit. Sam Wampler's
Freedom Ford McAlester is Dealer #1 / default.

Read first:
- context-kit orient
- docs/FREEDOM_FORD_SESSION_START.md
- 00-START-NEXT-SESSION.md
- docs/handoffs/SESSION_022_assistant_first_public_site.md
- docs/PLATFORM_REFRAME.md
- docs/FREEDOM_FORD_BEHAVIOR_LAYER.md
- docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md

Goal:
Harden the Monday demo path for the assistant-first public dealership
site shipped in SESSION_022.

Primary routes:
- /
- /assistant
- /showroom
- /embed/assistant
- /dealer-ai-overview

Tasks:
1. Run frontend typecheck/build.
2. Start Vite and inspect the public routes with Playwright on desktop
   and mobile viewports.
3. Fix only visible demo blockers: spacing, layout, awkward copy,
   responsiveness, route/link issues, or console errors.
4. Decide whether query prompts on /assistant should remain starter-chip
   only or safely auto-send. If changing behavior, keep it frontend-only
   and StrictMode-safe.
5. Optionally add a small Playwright smoke script if it helps repeat the
   Monday-demo checks.

Do NOT:
- touch backend
- change chat behavior
- edit the backend prompt/scrub/payment/inventory logic
- edit /dealer-ai-demo
- edit DEFAULT_DEALER / PRODUCT / defaultDealer.ts
- turn this into the deferred Leads pipeline session

Verify:
- npx tsc --noEmit
- npx vite build
- Playwright route smoke with console clean

When complete:
- Write docs/handoffs/SESSION_023_<slug>.md.
- Overwrite 00-START-NEXT-SESSION.md for SESSION_024.
```

---

## Operational state

- **Backend**: Django expected on `:8001`, Ollama llama3.2 on `:11434`.
- **Frontend**: Vite expected on `:5173`.
- **Public routes**:
  - `/` — assistant-first dealership homepage.
  - `/assistant` — full-page public assistant.
  - `/showroom` — public demo showroom.
  - `/embed/assistant` — standalone embeddable assistant.
- **Operator routes**:
  - `/dealer-ai-overview`
  - `/dealer-ai-live-assistant`
  - `/dealer-ai-inventory`
  - `/dealer-ai-leads`
  - `/dealer-ai-manager-chat`
  - `/dealer-ai-admin/team`
  - `/dealer-ai-onboarding`
  - `/dealer-ai-demo` — legacy lab, off-nav.

## Identity quick-reference

| Layer | Source | Examples |
| --- | --- | --- |
| **Product** | `PRODUCT` in `frontend/src/config/defaultDealer.ts` | Sidebar caption "DEALER AI KIT", embed "Powered by AI Sales Assistant", `<title>` prefix |
| **Default dealer** (fallback) | `DEFAULT_DEALER` in same file | `logoPath` fallback, name "Sam Wampler's Freedom Ford", location "McAlester", tagline "Sam Wampler Make It Happen" |
| **Active dealer** (runtime) | `OnboardingProfile` via `useBrand()` | Public nav/header/footer, assistant welcome lines, embed brand bar |

Resolution: `OnboardingProfile.logo_url || DEFAULT_DEALER.logoPath`
for the logo; `OnboardingProfile.<field> || DEFAULT_DEALER.<field>`
for supported identity fields.

## Anchors that win on conflict

If anything in this file disagrees with reality:

1. The latest handoff (`docs/handoffs/SESSION_022_*.md`).
2. `git log --oneline -10` (what actually shipped).
3. `git show HEAD:frontend/src/<path>` (current source).

Narrative docs are claims. Code and handoffs are facts.
