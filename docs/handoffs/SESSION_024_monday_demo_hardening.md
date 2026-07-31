---
date: 2026-05-03
title: SESSION_024 — Monday demo path hardening
type: implementation-summary
test_baseline: frontend tsc/build clean, Playwright route smoke clean
---

# Session handoff — Monday demo path hardening

SESSION_024 hardened the Monday public-site demo path from SESSION_022.
The scope stayed on visible frontend demo blockers for:

- `/`
- `/assistant`
- `/showroom`
- `/embed/assistant`
- `/dealer-ai-overview`

No backend behavior changed. No chat behavior changed. `/dealer-ai-demo`,
`DEFAULT_DEALER`, `PRODUCT`, and the public inventory contract were left
alone.

---

## What changed

### 1. Operator shell mobile fit

`/dealer-ai-overview` had horizontal overflow on a 390px mobile viewport.
The source was the operator topbar: dealer name, location, Public Preview,
and AI Active could exceed the available width.

Changed:

- `frontend/src/App.tsx`
  - Added `min-w-0` to the main shell content column.
  - Let the topbar dealer name truncate.
  - Hid the location label below 460px.
  - Kept the right-side topbar actions from shrinking unpredictably.
- `frontend/src/components/PublicPreviewDialog.tsx`
  - Kept the Public Preview action accessible on mobile while rendering it
    icon-only below `sm`.

Result: `/dealer-ai-overview` now measures `scrollWidth=390` on a 390px
mobile viewport.

### 2. Existing public-site polish retained

The active worktree already contained visual/copy hardening for the
assistant-first public site:

- `frontend/src/components/AssistantChat.tsx`
  - Presentation-only matched-vehicle deck and transcript overflow guard.
- `frontend/src/components/dealership/Hero.tsx`
  - Softer public copy around current inventory and payment-aware behavior.
- `frontend/src/components/dealership/AssistantBand.tsx`
  - Matching assistant-first copy cleanup.
- `frontend/src/pages/PublicAssistantPage.tsx`
  - `min-w-0` guard on the chat panel.

Those changes were verified as part of this session and left intact.

### 3. Query prompt decision

`/assistant?prompt=...` remains a starter-chip flow. It does not auto-send
on page load. That keeps the route React StrictMode-safe and avoids changing
chat behavior before the Monday demo.

---

## Verification

Executed:

- `npx tsc --noEmit` — pass.
- `npx vite build` — pass.
- Vite dev server on `http://127.0.0.1:5173/`.
- Django dev server on `http://127.0.0.1:8001/` from `backend/.venv`.
- Playwright route smoke across desktop `1440x1000` and mobile `390x900`.

Final Playwright result:

| Route | Desktop | Mobile | Console / network |
| --- | --- | --- | --- |
| `/` | fits | fits | clean |
| `/assistant` | fits | fits | clean |
| `/showroom` | fits | fits | clean |
| `/embed/assistant` | fits | fits | clean |
| `/dealer-ai-overview` | fits | fits | clean |

Final screenshot set saved locally at repo root:

```text
session_024_final_home_desktop.png
session_024_final_home_mobile.png
session_024_final_assistant_desktop.png
session_024_final_assistant_mobile.png
session_024_final_showroom_desktop.png
session_024_final_showroom_mobile.png
session_024_final_embed_assistant_desktop.png
session_024_final_embed_assistant_mobile.png
session_024_final_dealer_ai_overview_desktop.png
session_024_final_dealer_ai_overview_mobile.png
```

---

## Runtime notes

The first Playwright pass showed repeated Vite-proxied `500` responses
because Django was not running. After starting the backend on `:8001`,
the same route smoke was clean.

Starting Django with plain `python3` failed because Django was not
installed globally. Use:

```bash
cd backend
./.venv/bin/python manage.py runserver 127.0.0.1:8001
```

---

## Recommended next session

Now that the Monday public-site demo path is locked, return to the
deferred Leads pipeline page.

Target:

- `/dealer-ai-leads`

Use the SESSION_021 recommendation as the starting point: turn the
SESSION_015 stub into a real read-only lead triage page with filters,
lead detail, transcript/context, interested vehicles, assigned
salesperson, and recommended next action.

