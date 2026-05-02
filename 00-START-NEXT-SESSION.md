---
state: active
date: 2026-05-02
last_session_shipped: SESSION_018
next_session: SESSION_019
---

# Next session — Freedom Ford

## What just shipped (SESSION_018)

`SESSION_018 — Brand Settings Drive UI`. Hard-coded
*"Sam's Freedom Ford"* / *"McAlester"* strings across the OS
shell, embed surface, and Public Preview dialog were replaced
with values from the existing onboarding profile via a small
`useBrand()` hook (`frontend/src/lib/brand.ts`). Saving in
Setup → navigating any other route → fresh fetch picks up the
new values.

Logo asset, AssistantChat behavior, inventory logic, chat
behavior, and backend embed-CSP plumbing were all untouched per
the SESSION_018 guardrails.

Read the full handoff at:
`docs/handoffs/SESSION_018_brand_settings_drive_ui.md`.

---

## Recommended next session — SESSION_019

**Leads pipeline page (turn the stub into real).**

`/dealer-ai-leads` shipped in SESSION_015 as a 10-row stub with
a *"Preview · full view coming soon"* badge. SESSION_019 turns
it into the real surface — per-lead detail (modal or side
panel) with full conversation transcript, extracted profile
(budget / body style / urgency), interested vehicles rendered
with the existing `AssistantVehicleCard`, recommended next
action, handoff status, salesperson chip — plus client-side
filtering on urgency / handoff state and free-text search.

Read-only in v1. Reuses `fetchAdminLeads()` and
`fetchLeadDetail()` already in `frontend/src/lib/api.ts`.

**Strict guardrails:**

- ❌ No new backend endpoints.
- ❌ No chat behavior changes.
- ❌ No edits to `AssistantChat`, `EmbedAssistantPage`, the
  demo inventory snapshot, or `/dealer-ai-demo`.
- ❌ No write actions on leads (no reassign, no manual handoff
  toggle, no notes) — read-only is intentional for v1.
- ❌ No new API contracts in `lib/api.ts` beyond a TypeScript
  field-sync if a leads/session payload field is missing from
  the interface.

**Alternates** (covered in the SESSION_018 handoff):

- `SESSION_019b` — Inventory data quality / image cleanup.
- `SESSION_019c` — Backend X-Frame-Options / CSP allowlist
  for cross-origin embedding (backend-touching).
- `SESSION_019d` — Multi-tenant logo upload (onboarding
  field + UI consumption).

Default to the Leads pipeline (`SESSION_019`) unless a
specific alternate is dictated by the upcoming demo audience.

---

## Agent launch prompt for SESSION_019

Paste into Claude Code / Cursor / any AI coding agent as the
session opener.

```text
You are picking up SESSION_019 on the Freedom Ford Dealer OS.

Read first (in order):
- docs/handoffs/SESSION_018_brand_settings_drive_ui.md
- docs/handoffs/SESSION_017_public_embed_preview.md
- docs/handoffs/SESSION_015_overview_realism_mobile_shell.md
- frontend/src/pages/LeadsPage.tsx
- frontend/src/lib/api.ts (focus on AdminLead, AdminLeadsQuery,
  fetchAdminLeads, fetchLeadDetail)
- frontend/src/lib/brand.ts (use this — don't recreate the
  pattern)

Goal:
Turn /dealer-ai-leads from a stub into a real pipeline page.

Scope (frontend only):
- Per-lead detail (modal or side panel) showing transcript +
  extracted profile + interested vehicles + recommended next
  action + handoff status + salesperson chip.
- Client-side filtering: urgency, handoff state, free-text
  search by name/email/phone.
- Reuse existing helpers — do not add new endpoints.
- Read-only in v1.

Do NOT:
- touch backend
- change chat behavior
- edit AssistantChat or EmbedAssistantPage
- add new API contracts beyond TypeScript field-sync
- add write actions (reassign / handoff-toggle / notes)
- modify the demo inventory snapshot or /dealer-ai-demo

Tasks (suggested order):
1. Inspect AdminLead / fetchLeadDetail return shapes.
2. Extend LeadsPage with filters and search.
3. Add per-lead detail surface (Dialog or Sheet) wired to
   fetchLeadDetail.
4. Reuse AssistantVehicleCard for interested_vehicles.
5. Apply useBrand() where dealer-name copy makes sense.

Verify with:
- npx tsc --noEmit
- npx vite build
- Playwright: open /dealer-ai-leads, exercise filters + open
  detail surface for at least one lead, check console clean.

When complete:
- Write docs/handoffs/SESSION_019_<slug>.md following the
  established pattern.
- Update 00-START-NEXT-SESSION.md to point at SESSION_020.
- Commit code + handoff together; commit the
  00-START-NEXT-SESSION.md update separately.
```

---

## Recent commit history

```
1fa172a SESSION_018: brand settings drive UI
2e62e96 SESSION_017: add public embed preview
4e6272e Branding pass: real Sam's Freedom Ford McAlester identity
f39fce3 SESSION_016: polish Live Assistant customer UI
6d21f08 SESSION_015: wire overview to real data and add mobile shell
7bb19ea SESSION_014: add demo inventory snapshot preview
e3cafcc SESSION_013: Live Assistant page + inline vehicle cards
5f98e71 SESSION_012: Dealer OS shell + Overview page + coaching polish
```

---

## Operational state (verified 2026-05-02)

- **Backend**: Django on `:8001`, Ollama llama3.2 on `:11434`.
  Both running locally; backend serves
  `/api/dealer-ai/onboarding/profile/`,
  `/admin/audit-events/`, `/admin/leads/`, plus chat endpoints.
- **Frontend**: Vite on `:5173`. Routes:
  - `/dealer-ai-overview` (real APIs, brand-aware)
  - `/dealer-ai-live-assistant` (chat, brand-aware)
  - `/dealer-ai-inventory` (demo snapshot, 18 vehicles)
  - `/dealer-ai-leads` ← SESSION_019 target (stub today)
  - `/dealer-ai-manager-chat` (Coaching Mode)
  - `/dealer-ai-admin/team` (sales team)
  - `/dealer-ai-onboarding` (Setup — feeds the brand hook)
  - `/embed/assistant` (public embed, no shell)
  - `/dealer-ai-demo` (legacy lab, off-nav)
- **Test baseline**: 1210 pass / 1 skip (unchanged since
  SESSION_011; frontend-only sessions don't move it).
- **Console hygiene**: 0 errors, 0 warnings on every
  brand-aware surface verified in SESSION_018.

---

## File pattern conventions

- New page → `frontend/src/pages/<Name>Page.tsx`
- New component → `frontend/src/components/<Name>.tsx`
- New helper / hook → `frontend/src/lib/<name>.ts`
- shadcn primitive lives in `frontend/src/components/ui/` —
  patch primitives with `React.forwardRef` reactively when
  they first surface a runtime ref warning (Dialog and Sheet
  already done; DropdownMenu and Tabs still on the original
  function-component pattern).

## Anchors that win on conflict

If anything in this file disagrees with reality:

1. The latest handoff (`docs/handoffs/SESSION_018_*.md`).
2. `git log --oneline -10` (what actually shipped).
3. `git show HEAD:frontend/src/<path>` (current source).

Narrative docs are claims. Code and handoffs are facts.
