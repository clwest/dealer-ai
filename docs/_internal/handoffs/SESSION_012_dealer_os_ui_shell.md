---
date: 2026-05-02
title: SESSION_012 — Dealer OS UI shell + Overview page + coaching polish
type: implementation-summary
test_baseline: 1210
---

# Session handoff — Dealer OS UI shell

SESSION_012 was a frontend-only pass: turn the app from a collection of
routes into a cohesive dealership system. No backend, chat, or API
contract changes. Same shadcn primitives, same Tailwind v3 bridge, same
Ford palette — applied with discipline this time.

Use this snapshot to pick up at SESSION_013.

---

## What shipped

### 1. Persistent app shell (sidebar + topbar)

`frontend/src/App.tsx` was rewritten from a topbar-only layout to a
two-column shell:

- **Sidebar** (`w-60`, `bg-muted/40`, `sm:flex` — hidden under `sm`)
  with five nav items: Overview / Live Assistant / Coaching Mode /
  Team / Setup. Active state = `text-primary` + `border-l-2
  border-primary`. Title: "Dealer OS AI". Footer: "Local · MVP".
- **Topbar** (`h-14`, `border-b border-border`) shows store name
  ("Dealer OS") + scope ("Oklahoma · Dealer OS") on the left and
  an **AI Active** indicator on the right (pulsing emerald dot,
  `text-xs font-medium`).
- All chrome resolves through shadcn tokens (`bg-background`,
  `border-border`, `text-foreground`, etc.) which now point at
  Ford-blue primary + slate neutrals after the index.css remap done
  earlier in the same session.

The five nav routes match the SESSION_012 spec exactly. The pre-existing
"Customer demo" / "Manager dashboard" / "Sales team" labels were
retired in favor of the dealer-friendly "Live Assistant" / "Coaching
Mode" / "Team" / "Setup" wording. Underlying URLs preserved
(`/dealer-ai-demo`, `/dealer-ai-manager-chat`, `/dealer-ai-admin/team`,
`/dealer-ai-onboarding`) — only the labels changed.

### 2. Overview landing page

New file `frontend/src/pages/DealerOverviewPage.tsx`, mounted at
`/dealer-ai-overview`. Root `/` redirects there.

Four shadcn `Card`s in a `lg:grid-cols-2` grid:

- **AI Sales Assistant** — live data. Calls `fetchOnboardingProfile()`
  on mount, surfaces `sales_tone` (humanized) and `updated_at`
  (formatted via `toLocaleString`). Best-effort: render-degrades to
  "Not set" / "—" when the profile is empty or the fetch fails. Has
  an `Active` shadcn `Badge`.
- **Coaching summary** — placeholder per SESSION_012 spec. Shows "3
  scenarios tested" / "1 adjustment made". Wire to a real backend
  query in a later session.
- **Recent activity** — 4 placeholder events (e.g. "Customer asked:
  Truck under $30k", "Manager tested tone: Firm"). Mock data lives
  in a const at top of file; replace with a real audit-log query
  when ready.
- **Attention items** — placeholder. "No banned phrases configured",
  "Sales team incomplete". Should derive from `OnboardingProfile`
  flags (`salespeople_added`, `banned_phrases`) in a later pass.

The page intentionally avoids any mutation, network write, or chat
side effect. It's a dashboard surface only.

### 3. Coaching Mode page header polish

`frontend/src/pages/ManagerChatPage.tsx`:

- Header rewritten from "Test Assistant Coaching Mode" → "Train Your
  AI Sales Assistant". Subtext: "Try real customer scenarios. The
  assistant will respond using your store's voice." Shorter
  stateless note kept ("Stateless — reload to reset. Not customer-
  facing; use Live Assistant for that.") so the SESSION_010 mode
  contract isn't lost.
- Each assistant bubble is now preceded by an uppercase tracking-wide
  `RECOMMENDED SALES APPROACH` label. User bubbles unchanged.
- Bubble + avatar colors switched from hardcoded `bg-ford-blue` /
  `text-white` to shadcn tokens (`bg-primary` / `text-primary-
  foreground`). Resolves identically (shadcn primary IS Ford blue
  per the SESSION_011 / SESSION_012 token map) but de-couples the
  page from the brand hex.

`submit()`, `sendManagerChat()`, `Turn` shape, scroll behavior, error
handling, Cmd/Ctrl+Enter shortcut — all untouched. End-to-end Ollama
round-trip verified via Playwright with the customer prompt "I want a
truck under $30k.".

### 4. Token bridge consistency

The earlier shadcn token remap (the `bg-background` PostCSS error
fix, see top of session) made all this possible. Verified that:

- `bg-primary` → `#003478` (light) / `#1c69d4` (dark)
- `text-primary` → same
- `border-primary` → same
- `ring-primary` → same
- `bg-muted` → `#f1f5f9` (light) / `#1e293b` (dark)
- `text-muted-foreground` → `#64748b` / `#94a3b8`
- `border-border` → `#e2e8f0` / `#1e293b`
- `bg-accent` → `#1c69d4`

Destructive stayed red. No purples anywhere.

---

## Verification

| Step | Result |
| --- | --- |
| `npm run lint` (`tsc --noEmit`) | ✓ 0 errors |
| `npm run build` (`tsc -b && vite build`) | ✓ 956 ms, 1704 modules, 46.29 kB CSS / 354.49 kB JS |
| Playwright `/dealer-ai-overview` render | ✓ sidebar active, AI Active badge, 4 cards, real onboarding data |
| Playwright `/dealer-ai-manager-chat` render | ✓ new header copy, "Coaching Mode" sidebar active |
| Playwright Ollama round-trip | ✓ "RECOMMENDED SALES APPROACH" label rendered above assistant bubble |
| Console errors (any page) | ✓ 0 |
| Console warnings | 2 React Router v7 future-flag warnings (pre-existing, unrelated) |

Screenshots saved under `docs/handoffs/screenshots/SESSION_012/`.

Backend baseline unchanged — SESSION_012 didn't touch backend, so the
1210 pass / 1 skip baseline from SESSION_011 still holds. Did not re-run
the suite.

---

## Files changed

```
.gitignore                                          + tsconfig.tsbuildinfo, .playwright-mcp/
frontend/src/App.tsx                                rewritten (topbar-only → sidebar+topbar shell)
frontend/src/index.css                              shadcn tokens → Ford palette + slate neutrals
frontend/src/main.tsx                               + /dealer-ai-overview route, / → overview redirect
frontend/src/pages/DealerOverviewPage.tsx           NEW
frontend/src/pages/ManagerChatPage.tsx              header copy + Recommended Sales Approach label
docs/handoffs/SESSION_012_dealer_os_ui_shell.md     NEW (this file)
docs/handoffs/screenshots/SESSION_012/*.png         NEW (3 verification screenshots)
```

---

## Out of scope / known gaps

- **No mobile shell.** Sidebar is `hidden ... sm:flex`. Below `sm`
  there is no hamburger and no nav. Not a regression (the prior
  layout collapsed too) but worth fixing in a future visual pass.
- **Recent activity / Coaching summary / Attention items are
  placeholders.** Real data sources exist — `dealer-ai/admin/audit-
  events`, `OnboardingProfile.salespeople_added` /
  `banned_phrases` — but wiring them was out of scope for the
  SESSION_012 "first product pass" spec.
- **`tsconfig.tsbuildinfo` and `.playwright-mcp/`** added to
  `.gitignore` this session. If older clones have these tracked,
  a separate cleanup commit will be needed.
- **React Router v7 future-flag warnings.** Two console warnings
  about `v7_startTransition` and `v7_relativeSplatPath`. Cosmetic.
  Opt in with `<BrowserRouter future={...}>` when you want them
  silenced.
- **Live Chat Mode contract not exercised.** No persona was named in
  this session, so the `docs/FREEDOM_FORD_TRANSLATION_LAYER.md`
  chat-mode contract did not activate. Mentioned only because it's
  a load-bearing runtime contract — see SESSION_011 handoff.

---

## Next session candidates

- **SESSION_013 — wire Overview to real data.** Replace the three
  placeholder cards with live queries against the existing audit /
  onboarding endpoints. Add a small `/api/dealer-ai/admin/overview/`
  rollup if 4 round-trips feels heavy.
- **Mobile shell.** Add a sheet-based hamburger (shadcn `Sheet` is
  already installed) so the Overview is usable below `sm`.
- **Live Assistant + Setup visual polish.** Same Card + token discipline
  as Overview — the Customer Demo and Onboarding pages still carry
  pre-shadcn styling.
- **Test the v3 → v4 Tailwind migration.** Six v4-only variant
  patterns silently no-op under v3 (per `CLAUDE.md`). If the
  upcoming work needs them (e.g. card group corners, button group
  flattening), it's the right moment.
