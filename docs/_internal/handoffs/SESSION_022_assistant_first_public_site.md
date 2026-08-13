---
date: 2026-05-02
title: SESSION_022 — assistant-first public dealership site
type: implementation-summary
test_baseline: frontend tsc/build clean
---

# Session handoff — assistant-first public dealership site

SESSION_022 changed direction from the previously recommended Leads
pipeline work. The new directive was explicit: this is not incremental
operator-OS work; redesign the dealership website experience around the
AI assistant for a real Monday demo.

The result is a public dealership site surface outside the Dealer AI Kit
operator shell:

- `/` — assistant-first homepage.
- `/assistant` — full-page customer assistant.
- `/showroom` — demo showroom with AI-first CTAs.
- `/dealer-ai-*` routes still render inside the existing operator OS
  shell.
- `/embed/assistant` remains the standalone embed route.

No backend changes. No chat behavior changes. No edits to
`AssistantChat`, `EmbedAssistantPage`, the backend inventory pipeline, or
the demo route. The public pages reuse existing components/data and route
traffic into the shared chat component.

---

## What shipped

### 1. Public route split

`frontend/src/main.tsx` now treats public dealership routes and operator
routes as separate experiences.

Public routes:

```text
/                  → DealershipHomePage
/assistant          → PublicAssistantPage
/showroom           → PublicShowroomPage
/embed/assistant    → EmbedAssistantPage, unchanged
```

Operator routes:

```text
/dealer-ai-overview
/dealer-ai-live-assistant
/dealer-ai-inventory
/dealer-ai-leads
/dealer-ai-manager-chat
/dealer-ai-admin/*
/dealer-ai-onboarding
```

The prior `/` redirect into `/dealer-ai-overview` is gone. The public
site is now the default first impression.

### 2. Public dealership components

New directory:

```text
frontend/src/components/dealership/
```

Components:

- `SiteNav.tsx` — public dealership navigation with logo, sales phone,
  showroom/finance/trade links, and a prominent "Talk to AI" CTA.
- `Hero.tsx` — first-viewport assistant-first hero using real sample
  inventory imagery as the background and a compact chat preview.
- `AssistantBand.tsx` — homepage section embedding the shared
  `AssistantChat` component.
- `SiteFooter.tsx` — public footer with dealership contact links, product
  attribution, and an Operator OS link back to `/dealer-ai-overview`.

These files were already present as untracked SESSION_022 WIP when this
session began. This session kept them, refined the hero, and wired them
into real routes instead of replacing them.

### 3. Assistant-first homepage

`frontend/src/pages/DealershipHomePage.tsx` is new.

It includes:

- Full public nav.
- Hero with "AI Assistant · Live now" as the page's conversion signal.
- Embedded assistant section using `AssistantChat` via `AssistantBand`.
- Inventory teaser from the existing
  `FREEDOM_FORD_SAMPLE_INVENTORY` snapshot.
- Trust/finance/trade-in/about bands built around the assistant as the
  first step.

Important behavior: vehicle teaser CTAs go to `/assistant?prompt=...`
instead of inventing a separate vehicle Q&A flow.

### 4. Full-page public assistant

`frontend/src/pages/PublicAssistantPage.tsx` is new.

It renders:

- Public nav/footer.
- Brand-aware assistant headline.
- Proof points for inventory, payment-card source of truth, and human
  handoff.
- Shared `AssistantChat`.
- Query-string prompt support:

```text
/assistant?prompt=I%20need%20a%204WD%20truck
```

The query prompt becomes the first starter chip. It does **not**
auto-send on page load, avoiding duplicate sends under React StrictMode.

### 5. Public showroom

`frontend/src/pages/PublicShowroomPage.tsx` is new.

It uses the existing SESSION_014 sample inventory only; no new API
contract.

Features:

- Search by make/model/trim/color/stock number.
- Client-side filters: all, new, used, certified, hybrid, AWD/4WD.
- Vehicle cards with image, stock number, price, mileage/drivetrain/fuel
  chips.
- "Ask AI" CTA per vehicle:

```text
/assistant?prompt=Would%20the%20<vehicle>%20fit%20my%20budget%3F
```

### 6. Playwright added for verification

`playwright` was added as a dev dependency because the user explicitly
approved installing it for browser verification.

Changed:

```text
frontend/package.json
frontend/package-lock.json
```

`npm install -D playwright` reported two moderate vulnerabilities in the
existing dependency graph. No `npm audit fix --force` was run because
that would be a broad dependency churn unrelated to SESSION_022.

---

## Files changed

```text
frontend/package.json
frontend/package-lock.json
frontend/src/main.tsx
frontend/src/components/dealership/AssistantBand.tsx
frontend/src/components/dealership/Hero.tsx
frontend/src/components/dealership/SiteFooter.tsx
frontend/src/components/dealership/SiteNav.tsx
frontend/src/pages/DealershipHomePage.tsx
frontend/src/pages/PublicAssistantPage.tsx
frontend/src/pages/PublicShowroomPage.tsx
docs/handoffs/SESSION_022_assistant_first_public_site.md
00-START-NEXT-SESSION.md
```

Local verification screenshots saved at repo root:

```text
session_022_home_desktop.png
session_022_assistant_desktop.png
session_022_showroom_mobile.png
```

The `redesign/` folder was already untracked at session start and was
left intact.

---

## Verification

| Step | Result |
| --- | --- |
| `context-kit orient` | Read first |
| `npx tsc --noEmit` | Pass |
| `npx vite build` | Pass — 1724 modules, 55.37 kB CSS, 470.93 kB JS |
| Vite dev server | Running at `http://127.0.0.1:5173/` during verification |
| Playwright `/` | H1: `Find your next Ford with help, not pressure.` |
| Playwright `/assistant` | H1: `Start with what matters to you.` |
| Playwright `/showroom` | H1: `Browse the lot, then ask the assistant to narrow it.` |
| Playwright `/dealer-ai-overview` | H1: `Overview` |
| Playwright console | `[]` — no warnings, no errors |

Backend tests were not run because SESSION_022 was frontend-only and did
not touch backend behavior.

---

## Guardrails honored

- No backend endpoints added.
- No chat behavior changes.
- No edits to `AssistantChat`.
- No edits to `EmbedAssistantPage`.
- No edits to `/dealer-ai-demo`.
- No edits to `DEFAULT_DEALER` / `PRODUCT` / `defaultDealer.ts`.
- No new inventory contract; public showroom uses the existing demo
  sample snapshot.
- Brand-aware copy routes through `useBrand()`.

---

## Known limitations / follow-ups

- Public site contact info is still demo-static in `SiteNav` and
  `SiteFooter` because the onboarding profile does not yet expose
  address/hours fields.
- `/assistant?prompt=...` preloads a starter chip; it does not auto-send.
  This is intentional for StrictMode safety, but a future controlled
  auto-send flow could be added if the demo script needs it.
- The public showroom is still visual/demo inventory, not CRM/DMS-backed.
- Playwright is installed as a dependency, but no formal `test:e2e`
  script was added this session.
- The deferred Leads pipeline remains unbuilt. Keep it deferred until the
  Monday public-site demo is visually and narratively locked.

---

## Recommended next session

**SESSION_023 — Monday demo hardening for the assistant-first public
site.**

Suggested scope:

- Walk the exact Monday demo path across `/`, `/assistant`, `/showroom`,
  `/embed/assistant`, and `/dealer-ai-overview`.
- Tighten any visual spacing or mobile layout issues found in live
  browser review.
- Decide whether `/assistant?prompt=...` should remain "starter first" or
  become a safe controlled auto-send.
- Add a small Playwright smoke script if repeatable browser checks are
  useful now that Playwright is installed.
- Only after the public demo surface is locked, return to the deferred
  Leads pipeline work.
