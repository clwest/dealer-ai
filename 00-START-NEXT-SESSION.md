---
state: active
date: 2026-05-02
last_session_shipped: SESSION_019
next_session: SESSION_020
---

# Next session — Dealer AI Kit

> **Platform reframe note:** As of SESSION_019 the codebase is
> the **Dealer AI Kit** — a reusable dealer AI platform.
> Sam Wampler's Freedom Ford McAlester is Dealer #1 and the
> default configuration. See `docs/PLATFORM_REFRAME.md` for the
> identity hierarchy (product → default dealer → active dealer)
> and the path to onboarding a second dealer without forking.

## What just shipped (SESSION_019)

**Platform reframe — Dealer AI Kit.** The mental model
flipped: this is no longer *"Freedom Ford AI"*. It is the
*Dealer AI Kit*, with Sam Wampler's Freedom Ford McAlester as
Dealer #1.

- New `frontend/src/config/defaultDealer.ts` holds
  `DEFAULT_DEALER` (dealer fallback) and `PRODUCT` (kit
  identity).
- `useBrand()` fallbacks, `App.tsx` logo path, sidebar caption
  ("DEALER AI KIT"), embed "Powered by" footer, and HTML
  `<title>` ("Dealer AI Kit — Sam Wampler's Freedom Ford
  McAlester") all sourced from the new config.
- Brand-neutral defaults in `AssistantChat` and softened
  Onboarding placeholders so a future Dealer #2 doesn't see
  Dealer #1's identity bleeding into hint copy.
- New `docs/PLATFORM_REFRAME.md` documents the model
  canonically. `docs/FREEDOM_FORD_SESSION_START.md` got a
  reframe callout at the top; the rest of that file is
  preserved verbatim.

Zero behavior changes. No backend, no chat, no inventory, no
prompts, no migrations.

Read the full handoff at
`docs/handoffs/SESSION_019_platform_reframe_dealer_ai_kit.md`.

---

## Recommended next session — SESSION_020

**Leads pipeline page (turn the stub into real).**

Pre-empted from SESSION_018 by the SESSION_019 reframe; still
the highest-leverage outstanding frontend-only work.

`/dealer-ai-leads` is currently a SESSION_015-era stub: 10 most
recent leads with a *"Preview · full view coming soon"* badge,
basic name / phone / email / urgency. SESSION_020 turns the
stub into the real surface.

**Scope:**

- Per-lead detail (modal or side panel) with full conversation
  transcript, `extracted_profile` fields, `interested_vehicles`
  rendered with `AssistantVehicleCard`, `recommended_next_action`,
  handoff status + assigned salesperson chip.
- Filters: urgency, handoff state, free-text name/email/phone
  search (client-side over loaded page; no new endpoint).
- Reuse `fetchAdminLeads()` and `fetchLeadDetail()` already in
  `frontend/src/lib/api.ts`.
- Brand-aware copy via `useBrand()` where appropriate.

**Strict guardrails:**

- ❌ No new backend endpoints.
- ❌ No chat behavior changes.
- ❌ No edits to `AssistantChat`, `EmbedAssistantPage`, the
  inventory snapshot, or `/dealer-ai-demo`.
- ❌ No write actions on leads (no reassign / handoff toggle /
  notes) — read-only v1.
- ❌ No edits to `DEFAULT_DEALER` / `PRODUCT` config (the
  reframe is settled; SESSION_020 *consumes* it, doesn't edit
  it).
- ❌ No new API contracts beyond a TypeScript field-sync if a
  leads / session payload field is missing from the interface.

**Alternates** (full reasoning in the SESSION_019 handoff):

- `SESSION_020b` — Inventory data quality / image cleanup.
- `SESSION_020c` — Backend X-Frame-Options / CSP allowlist
  for cross-origin embedding (backend-touching).
- `SESSION_020d` — Multi-tenant logo upload (profile field
  + UI consumption).

Default to the Leads pipeline (`SESSION_020`) unless a
specific alternate is dictated by the next demo audience.

---

## Agent launch prompt for SESSION_020

Paste into Claude Code / Cursor / any AI coding agent as the
session opener.

```text
You are picking up SESSION_020 on the Dealer AI Kit (Sam
Wampler's Freedom Ford McAlester is Dealer #1 / default).

Read first (in order):
- docs/PLATFORM_REFRAME.md (the kit's mental model — identity
  hierarchy, product vs dealer)
- docs/handoffs/SESSION_019_platform_reframe_dealer_ai_kit.md
- docs/handoffs/SESSION_018_brand_settings_drive_ui.md
- docs/handoffs/SESSION_015_overview_realism_mobile_shell.md
- frontend/src/pages/LeadsPage.tsx
- frontend/src/lib/api.ts (focus on AdminLead, AdminLeadsQuery,
  fetchAdminLeads, fetchLeadDetail)
- frontend/src/lib/brand.ts (use useBrand — don't recreate)
- frontend/src/config/defaultDealer.ts (read; do not edit)

Goal:
Turn /dealer-ai-leads from a stub into a real pipeline page.

Scope (frontend only):
- Per-lead detail (modal or side panel) showing transcript,
  extracted profile, interested vehicles (use
  AssistantVehicleCard), recommended next action, handoff
  status, salesperson chip.
- Client-side filters: urgency, handoff state, free-text
  search by name/email/phone.
- Reuse existing API helpers — do not add new endpoints.
- Read-only in v1 (no reassign, no handoff toggle, no notes).

Do NOT:
- touch backend
- change chat behavior
- edit AssistantChat, EmbedAssistantPage, the inventory
  snapshot, or /dealer-ai-demo
- edit defaultDealer.ts (the reframe is settled — consume
  it, don't change it)
- add new API contracts beyond a TypeScript field-sync if a
  payload field is missing from the interface
- add write actions on leads

Tasks (suggested order):
1. Inspect AdminLead / fetchLeadDetail return shapes vs the
   current LeadsPage to spot any TypeScript field gaps.
2. Add filter controls (urgency, handoff state, search).
3. Add per-lead detail surface (Dialog or Sheet) wired to
   fetchLeadDetail.
4. Reuse AssistantVehicleCard for interested_vehicles.
5. Apply useBrand() where dealer-name copy makes sense.

Verify:
- npx tsc --noEmit
- npx vite build
- Playwright: open /dealer-ai-leads, exercise filters and
  open detail surface for at least one lead. Console clean.

When complete:
- Write docs/handoffs/SESSION_020_<slug>.md following the
  established pattern.
- Overwrite 00-START-NEXT-SESSION.md to point at SESSION_021.
- Commit code + handoff together; commit the
  00-START-NEXT-SESSION.md update separately.
```

---

## Recent commit history

```
1753525 SESSION_019: platform reframe — Dealer AI Kit
ce60e20 Close SESSION_018, open SESSION_019 (Leads pipeline)
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

## Operational state (verified 2026-05-02 after SESSION_019)

- **Backend**: Django on `:8001`, Ollama llama3.2 on `:11434`.
  Both running locally.
- **Frontend**: Vite on `:5173`. Routes:
  - `/dealer-ai-overview` (real APIs, brand-aware)
  - `/dealer-ai-live-assistant` (chat, brand-aware)
  - `/dealer-ai-inventory` (demo snapshot, 18 vehicles)
  - `/dealer-ai-leads` ← **SESSION_020 target** (stub today)
  - `/dealer-ai-manager-chat` (Coaching Mode)
  - `/dealer-ai-admin/team` (sales team)
  - `/dealer-ai-onboarding` (Setup — feeds the brand hook)
  - `/embed/assistant` (public embed, no shell)
  - `/dealer-ai-demo` (legacy lab, off-nav)
- **Test baseline**: 1210 pass / 1 skip (unchanged since
  SESSION_011; frontend / docs sessions don't move it).
- **Console hygiene**: 0 errors, 0 warnings on every
  brand-aware surface verified in SESSION_019.

---

## Identity quick-reference (post-reframe)

| Layer | Source | Examples |
| --- | --- | --- |
| **Product** | `PRODUCT` in `frontend/src/config/defaultDealer.ts` | Sidebar caption "DEALER AI KIT", embed "Powered by AI Sales Assistant", `<title>` prefix |
| **Default dealer** (fallback) | `DEFAULT_DEALER` in same file | Logo path, fallback name "Sam Wampler's Freedom Ford", fallback location "McAlester", tagline "Sam Wampler Make It Happen" |
| **Active dealer** (runtime) | `OnboardingProfile` via `useBrand()` | Topbar dealer chip, embed brand bar, footer disclaimers, welcome lines |

Resolution: `OnboardingProfile` → `DEFAULT_DEALER` → never
hard-coded inline.

---

## File pattern conventions

- New page → `frontend/src/pages/<Name>Page.tsx`
- New component → `frontend/src/components/<Name>.tsx`
- New helper / hook → `frontend/src/lib/<name>.ts`
- New config → `frontend/src/config/<name>.ts`
- shadcn primitive lives in `frontend/src/components/ui/` —
  patch primitives with `React.forwardRef` reactively when
  they first surface a runtime ref warning. Already done:
  Sheet, Dialog. Still on original pattern: DropdownMenu,
  Tabs.

## Anchors that win on conflict

If anything in this file disagrees with reality:

1. The latest handoff (`docs/handoffs/SESSION_019_*.md`).
2. `git log --oneline -10` (what actually shipped).
3. `git show HEAD:frontend/src/<path>` (current source).

Narrative docs are claims. Code and handoffs are facts.
