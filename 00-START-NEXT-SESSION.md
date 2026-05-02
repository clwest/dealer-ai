---
state: active
date: 2026-05-02
last_session_shipped: SESSION_021
next_session: SESSION_022
---

# Next session — Dealer AI Kit

> **Platform reframe note:** This codebase is the **Dealer AI
> Kit** — a reusable dealer AI platform. Sam Wampler's Freedom
> Ford McAlester is Dealer #1 and the default configuration. See
> `docs/PLATFORM_REFRAME.md` for the identity hierarchy and
> `docs/DEALER_DUPLICATION_GUIDE.md` for the operator workflow
> to onboard a second dealer without forking.

## What just shipped (SESSION_021)

**Multi-tenant logo upload via `OnboardingProfile.logo_url`.**
The Setup form gains a Logo URL field, and the brand-resolution
chain (`useBrand`) now resolves
`profile.logo_url || DEFAULT_DEALER.logoPath`. The kit's
static asset stays as the documented fallback. Net effect: a
manager can stand up a second dealer's brand identity end-to-
end from Setup without any developer file-drop.

- Backend: new `logo_url` CharField on
  `DealerOnboardingProfile` + serializer + migration 0005
  + four new tests. **Backend baseline: 1214 / 1** (was
  1210/1).
- Frontend: `Brand.logoUrl` + `Brand.logoFromProfile`,
  consumed by sidebar `BrandHeader`, embed `BrandMark`,
  and the Setup Dealer Kit Status card (which now reads
  `(from profile)` vs `(static default)` source labels).
- Docs: `DEALER_DUPLICATION_GUIDE.md` updated — the Logo
  asset section is retitled *"fallback only — SESSION_021
  collapsed this"*; Phase 1 (developer) is now optional;
  the printable checklist puts the Setup form first.

Read the full handoff at
`docs/handoffs/SESSION_021_logo_url_setting.md`.

---

## Recommended next session — SESSION_022

**Leads pipeline page (turn the stub into real).**

This recommendation has been on the board since SESSION_018,
deferred four times now (in favor of the platform reframe,
the duplication flow, and the logo upload). Each deferral
was correctly higher-priority at the time. SESSION_021
finished the brand-identity loop, so the deepest unfilled
value gap in the OS is once again the Leads pipeline.

`/dealer-ai-leads` is currently a SESSION_015-era stub: 10
most recent leads with a *"Preview · full view coming soon"*
badge and basic name / phone / email / urgency fields.
SESSION_022 turns it into the real surface.

**Scope:**

- Per-lead detail (modal or side panel) showing:
  - Full conversation transcript.
  - `extracted_profile` rendering (budget, body style,
    model intent, urgency).
  - `interested_vehicles` list rendered with the existing
    `AssistantVehicleCard`.
  - `recommended_next_action` text.
  - Handoff status + `assigned_to` salesperson chip.
- Filtering on the list:
  - urgency, handoff state, free-text search by name /
    email / phone (client-side over loaded page).
- Reuse existing `fetchAdminLeads()` and
  `fetchLeadDetail()` helpers in `lib/api.ts`.
- Brand-aware copy via `useBrand()` where appropriate.

**Strict guardrails:**

- ❌ No new backend endpoints.
- ❌ No chat behavior changes.
- ❌ No edits to `AssistantChat`, `EmbedAssistantPage`, the
  inventory snapshot, or `/dealer-ai-demo`.
- ❌ No edits to `DEFAULT_DEALER` / `PRODUCT` /
  `defaultDealer.ts`.
- ❌ No write actions on leads (no reassign / handoff toggle
  / notes) — read-only v1.
- ❌ No new API contracts beyond a TypeScript field-sync if
  a leads / session payload field is missing from the
  interface.

**Alternates** (still on the board):

- `SESSION_022b` — Multipart logo upload (extends
  SESSION_021's URL paste with real file uploads + object
  storage). Pick if a real second-dealer pilot is imminent
  and the URL paste turns out to be friction.
- `SESSION_022c` — Backend X-Frame-Options / CSP allowlist
  for cross-origin embedding. Pick when a third-party-embed
  deadline is real.
- `SESSION_022d` — Inventory data quality / image cleanup
  (deferred since SESSION_016).
- `SESSION_022e` — Live broadcast on Setup save
  (`BrandContext` so topbar updates without navigation).

Default to **SESSION_022 (Leads pipeline)** unless a specific
alternate is dictated by the next demo audience.

---

## Agent launch prompt for SESSION_022

Paste into Claude Code / Cursor / any AI coding agent as the
session opener.

```text
You are picking up SESSION_022 on the Dealer AI Kit (Sam
Wampler's Freedom Ford McAlester is Dealer #1 / default).

Read first (in order):
- docs/PLATFORM_REFRAME.md
- docs/DEALER_DUPLICATION_GUIDE.md
- docs/handoffs/SESSION_021_logo_url_setting.md
- docs/handoffs/SESSION_020_dealer_duplication_flow.md
- docs/handoffs/SESSION_019_platform_reframe_dealer_ai_kit.md
- docs/handoffs/SESSION_015_overview_realism_mobile_shell.md
  (the SESSION_015 stub LeadsPage was the seed)
- frontend/src/pages/LeadsPage.tsx (the stub to extend)
- frontend/src/lib/api.ts (focus on AdminLead,
  AdminLeadsQuery, fetchAdminLeads, fetchLeadDetail)
- frontend/src/lib/brand.ts (use useBrand — don't recreate)
- frontend/src/components/AssistantVehicleCard.tsx (reuse
  for interested_vehicles in the detail surface)
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
- Read-only in v1.

Do NOT:
- touch backend
- change chat behavior
- edit AssistantChat, EmbedAssistantPage, the inventory
  snapshot, or /dealer-ai-demo
- edit defaultDealer.ts (PRODUCT or DEFAULT_DEALER)
- add new API contracts beyond a TypeScript field-sync if a
  payload field is missing from the interface
- add write actions on leads (reassign, handoff toggle,
  notes — all explicitly v2)

Tasks (suggested order):
1. Inspect AdminLead / fetchLeadDetail return shapes vs
   the current LeadsPage to spot any TypeScript field gaps.
2. Add filter controls (urgency, handoff state, search).
3. Add per-lead detail surface (Dialog or Sheet) wired to
   fetchLeadDetail.
4. Reuse AssistantVehicleCard for interested_vehicles.
5. Apply useBrand() where dealer-name copy makes sense.

Verify:
- npx tsc --noEmit
- npx vite build
- (Backend tests not required — frontend-only session.)
- Playwright: open /dealer-ai-leads, exercise filters and
  open detail surface for at least one lead. Console clean.

When complete:
- Write docs/handoffs/SESSION_022_<slug>.md following the
  established pattern.
- Overwrite 00-START-NEXT-SESSION.md to point at SESSION_023.
- Commit code + handoff together; commit the
  00-START-NEXT-SESSION.md update separately.
```

---

## Recent commit history

```
e9bb578 SESSION_021: multi-tenant logo upload via OnboardingProfile.logo_url
a824aa3 SESSION_020: dealer duplication flow
5bfde3c Close SESSION_019, open SESSION_020 (Leads pipeline)
1753525 SESSION_019: platform reframe — Dealer AI Kit
ce60e20 Close SESSION_018, open SESSION_019 (Leads pipeline)
1fa172a SESSION_018: brand settings drive UI
2e62e96 SESSION_017: add public embed preview
4e6272e Branding pass: real Sam's Freedom Ford McAlester identity
f39fce3 SESSION_016: polish Live Assistant customer UI
6d21f08 SESSION_015: wire overview to real data and add mobile shell
```

---

## Operational state (verified 2026-05-02 after SESSION_021)

- **Backend**: Django on `:8001`, Ollama llama3.2 on
  `:11434`. Migration `0005_dealeronboardingprofile_logo_url`
  applied to dev DB.
- **Frontend**: Vite on `:5173`. Routes:
  - `/dealer-ai-overview` (real APIs, brand-aware,
    profile-driven logo via SESSION_021)
  - `/dealer-ai-live-assistant` (chat, brand-aware)
  - `/dealer-ai-inventory` (demo snapshot, 18 vehicles)
  - `/dealer-ai-leads` ← **SESSION_022 target** (stub today)
  - `/dealer-ai-manager-chat` (Coaching Mode)
  - `/dealer-ai-admin/team` (sales team)
  - `/dealer-ai-onboarding` (Setup — now has Logo URL +
    Dealer Kit Status card)
  - `/embed/assistant` (public embed, profile-driven logo)
  - `/dealer-ai-demo` (legacy lab, off-nav)
- **Test baseline**: **1214 / 1** (was 1210/1; +4 from
  SESSION_021's logo_url tests).
- **Console hygiene**: 0 errors, 0 warnings on every brand-
  aware surface verified in SESSION_021.

---

## Identity quick-reference

| Layer | Source | Examples |
| --- | --- | --- |
| **Product** | `PRODUCT` in `frontend/src/config/defaultDealer.ts` | Sidebar caption "DEALER AI KIT", embed "Powered by AI Sales Assistant", `<title>` prefix |
| **Default dealer** (fallback) | `DEFAULT_DEALER` in same file | `logoPath` (kit's static asset), fallback name "Sam Wampler's Freedom Ford", fallback location "McAlester", tagline "Sam Wampler Make It Happen" |
| **Active dealer** (runtime) | `OnboardingProfile` via `useBrand()` | Topbar dealer chip, embed brand bar, footer disclaimers, welcome lines, **logo_url (SESSION_021)** |

Resolution: `OnboardingProfile.logo_url || DEFAULT_DEALER.logoPath`
for the logo; `OnboardingProfile.<field> || DEFAULT_DEALER.<field>`
for everything else.

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

1. The latest handoff (`docs/handoffs/SESSION_021_*.md`).
2. `git log --oneline -10` (what actually shipped).
3. `git show HEAD:frontend/src/<path>` (current source).

Narrative docs are claims. Code and handoffs are facts.
