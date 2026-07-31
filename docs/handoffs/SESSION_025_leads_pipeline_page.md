---
date: 2026-05-03
title: SESSION_025 — read-only Leads pipeline page
type: implementation-summary
test_baseline: frontend tsc/build clean, Playwright leads route smoke clean
---

# Session handoff — read-only Leads pipeline page

SESSION_025 replaced the SESSION_015 `/dealer-ai-leads` stub with a real
read-only triage surface for assistant-sourced leads.

The page stays inside the existing operator shell and uses only existing
admin read endpoints:

- `GET /api/dealer-ai/admin/leads/`
- `GET /api/dealer-ai/admin/lead/<id>/`

No backend behavior changed. No lead write actions were added. Customer
chat behavior, `/dealer-ai-demo`, public-site routes, and dealer config
constants were left alone.

---

## What changed

### 1. Leads pipeline view

`frontend/src/pages/LeadsPage.tsx` now renders:

- Summary metrics for loaded leads, immediate leads, assigned leads, and
  handed-off leads.
- Client-side search across name, phone, email, trade-in text, summary,
  recommended next action, assignment, and interested vehicles.
- Urgency filters: all, immediate, this week, this month, researching.
- Status filters: all, new, handed off, assigned, unassigned.
- A selectable lead queue sorted by backend urgency ordering.
- A read-only detail panel for the selected lead.

### 2. Read-only lead detail

The detail panel shows existing payload fields:

- Contact info and created time.
- Target monthly payment, down payment, credit range, and assignment.
- Trade-in text when present.
- Recommended next action.
- Conversation summary.
- Extracted session profile.
- Interested vehicles with read-only vehicle tiles.
- Conversation transcript excluding system messages.

The existing `LeadDetailModal` was intentionally not reused because it
contains assignment/handoff mutation flows. SESSION_025 needed a
read-only page.

### 3. Mobile fit

Desktop keeps bounded lead/detail panes. Mobile uses normal page flow so
the long detail content remains visible without nested scroll traps.

---

## Verification

Executed:

- `npx tsc --noEmit` — pass.
- `npx vite build` — pass.
- Vite dev server on `http://127.0.0.1:5173/`.
- Django dev server on `http://127.0.0.1:8001/` from `backend/.venv`.
- Playwright route smoke for `/dealer-ai-leads` on desktop `1440x1000`
  and mobile `390x900`.

Final Playwright result:

| Route | Desktop | Mobile | Console / network |
| --- | --- | --- | --- |
| `/dealer-ai-leads` | fits | fits | clean |

Final screenshot set saved locally at repo root:

```text
session_025_leads_final_desktop.png
session_025_leads_final_mobile.png
```

---

## Known limitations

- The page filters the currently loaded admin lead page (`limit=100`),
  not the entire database.
- There is no source filter because the current lead payload has no
  separate source field; all rows on this route are treated as
  assistant-sourced admin leads.
- No write actions exist here by design. Assignment, handoff, notes,
  CRM sync, email, and SMS remain out of scope.

---

## Recommended next session

Return to the deferred setup polish:

- Multipart logo upload for dealer branding, extending the existing logo
  URL setting without changing the product/dealer identity hierarchy.

