---
state: active
date: 2026-05-03
last_session_shipped: SESSION_023
next_session: SESSION_024
---

# Next session — Dealer AI Kit

> **Platform reframe note:** This codebase is the **Dealer AI
> Kit** — a reusable dealer AI platform. Sam Wampler's Freedom
> Ford McAlester is Dealer #1 and the default configuration. See
> `docs/PLATFORM_REFRAME.md` for the identity hierarchy and
> `docs/DEALER_DUPLICATION_GUIDE.md` for the operator workflow
> to onboard a second dealer without forking.

## What just shipped (SESSION_023)

**Context-kit refresh + fresh-session prep.** The repo's generated
orientation state was refreshed so the next clean terminal can use the
new `start-codex` flows and the current truth/state layer. The root
start file now has an explicit `## NEXT TASK` section, `docs/CONTEXT_KIT_INVENTORY.md`
was regenerated, and `start-codex` now resolves a real next task instead
of falling back to the missing-task message.

Read the full handoff at
`docs/handoffs/SESSION_023_CONTEXT_KIT_REFRESH.md`.

**Verification from SESSION_023:**

- `context-kit inventory --write` — pass.
- `context-kit doctor` — pass with 4 warnings.
- `context-kit orient --short` — pass.
- `context-kit start-codex --short` — pass, next task resolved.
- `context-kit start-codex --mode=execute --model=cheap --short` — pass.
- `npx tsc --noEmit` — pass.
- `npx vite build` — pass.

---

## Recommended next session — SESSION_024

**Monday demo hardening for the assistant-first public site.**

The prior Leads pipeline recommendation is still valid, but it is not
the right next move until the Monday public-site demo is locked. SESSION
024 should harden the exact visitor journey that will be shown live.

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

## NEXT TASK

Harden the Monday demo path for the assistant-first public site.

Focus on:
- `/`
- `/assistant`
- `/showroom`
- `/embed/assistant`
- `/dealer-ai-overview`

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

## Agent launch prompt for SESSION_024

Paste into Claude Code / Cursor / any AI coding agent as the session
opener.

```text
You are picking up SESSION_024 on the Dealer AI Kit. Sam Wampler's
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
- Write docs/handoffs/SESSION_024_<slug>.md.
- Overwrite 00-START-NEXT-SESSION.md for the following session.
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
