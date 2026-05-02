---
state: active
date: 2026-05-02
last_session_shipped: SESSION_020
next_session: SESSION_021
---

# Next session — Dealer AI Kit

> **Platform reframe note:** This codebase is the **Dealer AI
> Kit** — a reusable dealer AI platform. Sam Wampler's Freedom
> Ford McAlester is Dealer #1 and the default configuration. See
> `docs/PLATFORM_REFRAME.md` for the identity hierarchy and
> `docs/DEALER_DUPLICATION_GUIDE.md` for the operator workflow
> to onboard a second dealer without forking.

## What just shipped (SESSION_020)

**Dealer duplication flow.** The reframe became operationally
demonstrable.

- **`docs/DEALER_DUPLICATION_GUIDE.md`** — operator-facing
  workflow for onboarding Dealer #2 without forking. Mental
  model, what's editable in Setup vs code, "Do not fork the
  repo" rule, Phase 1–4 recommended workflow, printable
  checklist, glossary.
- **Dealer Kit Status card** — read-only summary in
  `/dealer-ai-onboarding`. Shows Product (Dealer AI Kit),
  Active dealer (form state), Location, Brand(s), Logo path,
  "Single-dealer configuration" status. Mirrors form state
  live so the manager previews how their edit will land in
  the OS chrome before saving.
- **`frontend/src/config/defaultDealer.ts`** — comments
  expanded with explicit no-fork rule, identity hierarchy
  callout, retargeting recipe, future-logo-upload note.

Zero behavior changes. No backend touched.

Read the full handoff at
`docs/handoffs/SESSION_020_dealer_duplication_flow.md`.

---

## Recommended next session — SESSION_021

**Multi-tenant logo upload / `logo_url` setting.**

The Dealer Kit Status card and the Duplication Guide both
surface the manual logo file-drop as the **single biggest
remaining developer-only step** in the second-dealer onboarding
flow. SESSION_021 closes that gap.

**Scope:**

- Add `logo_url` (or equivalent — uploaded asset URL or remote
  URL string) to the onboarding / dealership profile. Tiny
  backend touch:
  - new `OnboardingProfile.logo_url` field
    (`CharField(blank=True, default="")`)
  - one-line serializer addition
  - auto-generated migration
- Frontend Setup gains a logo input — start with a simple URL
  text field for v1 (the Dealership profile section is the
  natural home). Real multipart file upload can come later.
- The Dealer Kit Status card's **Logo** row updates to
  display the configured URL when present, falling back to
  `DEFAULT_DEALER.logoPath` when the field is empty.
- `useBrand()` — add `logoUrl` to the `Brand` shape, sourcing
  from `profile.logo_url` first, falling back to
  `DEFAULT_DEALER.logoPath`.
- Brand surfaces (`App.tsx` `BrandHeader`, embed `BrandMark`)
  consume `brand.logoUrl` instead of the hard-coded
  `LOGO_SRC` constant. Keep the existing static asset as the
  fallback path.
- Update `docs/DEALER_DUPLICATION_GUIDE.md`:
  - Remove "logo asset is static" from "What still requires
    code/config".
  - Adjust Phase 1 / Phase 2 wording to reflect that logo is
    now a Setup field.

**Strict guardrails:**

- ❌ No chat behavior changes.
- ❌ No CRM/DMS integration.
- ❌ No full multi-tenant routing — `logo_url` is per-store,
  not per-tenant. Single profile still.
- ❌ No edits to `AssistantChat`, `EmbedAssistantPage`'s chat
  behavior, `/dealer-ai-demo`, the inventory snapshot, or the
  `PRODUCT` constants.
- ❌ No new top-level routes.
- ❌ Don't move the static logo file. The shipped Sam Wampler
  asset stays in `frontend/public/branding/` and remains the
  documented fallback in `DEFAULT_DEALER.logoPath`.

**Alternates** (still on the board from SESSION_019/020):

- `SESSION_021b` — Leads pipeline (deferred three times now;
  pick if the next demo is dealer-ops more than brand setup).
- `SESSION_021c` — Backend X-Frame-Options / CSP allowlist
  for cross-origin embedding (backend-touching; pick when
  third-party-embed deadline is real).

Default to **SESSION_021 (logo upload)** unless a specific
alternate is dictated by the upcoming demo audience.

After SESSION_021, the second-dealer onboarding flow is fully
self-serve: every Phase 1 (developer) step the duplication
guide currently lists collapses into Phase 2 (Setup form).

---

## Agent launch prompt for SESSION_021

Paste into Claude Code / Cursor / any AI coding agent as the
session opener.

```text
You are picking up SESSION_021 on the Dealer AI Kit (Sam
Wampler's Freedom Ford McAlester is Dealer #1 / default).

Read first (in order):
- docs/PLATFORM_REFRAME.md (identity hierarchy)
- docs/DEALER_DUPLICATION_GUIDE.md (operator workflow this
  session is closing a gap in)
- docs/handoffs/SESSION_020_dealer_duplication_flow.md
- docs/handoffs/SESSION_019_platform_reframe_dealer_ai_kit.md
- docs/handoffs/SESSION_018_brand_settings_drive_ui.md
  (the useBrand pattern this session extends)
- frontend/src/config/defaultDealer.ts (read; do not edit
  PRODUCT — extend DEFAULT_DEALER fallback if useful)
- frontend/src/lib/brand.ts (the hook to extend)
- frontend/src/pages/DealerOnboardingPage.tsx (Setup form +
  Dealer Kit Status card to update)
- frontend/src/App.tsx (BrandHeader uses LOGO_SRC)
- frontend/src/pages/EmbedAssistantPage.tsx (BrandMark uses
  hard-coded path — replace with brand.logoUrl)
- backend/dealer_ai/models.py (find OnboardingProfile model)
- backend/dealer_ai/serializers.py (find profile serializer)

Goal:
Replace the static logo path with a per-dealer setting on
OnboardingProfile, exposed in Setup, consumed via useBrand.

Scope (frontend + tiny backend):
- Backend: new OnboardingProfile.logo_url CharField
  (blank=True, default=""). Add to serializer. Generate +
  apply migration. Update tests if any reference the
  serializer's field list.
- Frontend api.ts: add logo_url to OnboardingProfilePayload.
- useBrand: add logoUrl to Brand; resolve as
  profile.logo_url || DEFAULT_DEALER.logoPath.
- Setup form: add a Logo URL input in the Dealership profile
  section.
- Dealer Kit Status card: show the resolved logo URL with
  source label ("from profile" vs "static default").
- BrandHeader (App.tsx) + BrandMark (EmbedAssistantPage):
  consume brand.logoUrl instead of LOGO_SRC.
- Update docs/DEALER_DUPLICATION_GUIDE.md to reflect the
  collapsed dev step.

Do NOT:
- change chat behavior
- add CRM/DMS integration
- add multi-tenant routing
- edit AssistantChat, EmbedAssistantPage's chat behavior,
  /dealer-ai-demo, the inventory snapshot, or PRODUCT
- add new routes
- delete or move the static logo asset
- edit DEFAULT_DEALER.logoPath (still the documented
  fallback)

Tasks (suggested order):
1. Inspect backend OnboardingProfile model + serializer.
2. Add logo_url field + serializer + migration.
3. Run backend tests; confirm baseline holds.
4. Frontend api.ts: add logo_url to payload type.
5. Extend useBrand with logoUrl.
6. Add URL input to Setup, wire form state to api round-trip.
7. Update Dealer Kit Status card's Logo row.
8. Switch BrandHeader + BrandMark to brand.logoUrl.
9. Update DEALER_DUPLICATION_GUIDE.md.

Verify:
- backend: python manage.py test dealer_ai (1210/1 baseline)
- npx tsc --noEmit
- npx vite build
- context-kit doctor
- Playwright: open Setup, save a remote logo URL, verify it
  renders in the sidebar + embed; clear the field, verify
  the static fallback still renders. Console clean.

When complete:
- Write docs/handoffs/SESSION_021_<slug>.md.
- Overwrite 00-START-NEXT-SESSION.md to point at SESSION_022.
- Commit code + handoff + docs together; commit the
  00-START-NEXT-SESSION.md update separately if you prefer
  the close-and-open split.
```

---

## Recent commit history

```
5bfde3c Close SESSION_019, open SESSION_020 (Leads pipeline)
1753525 SESSION_019: platform reframe — Dealer AI Kit
ce60e20 Close SESSION_018, open SESSION_019 (Leads pipeline)
1fa172a SESSION_018: brand settings drive UI
2e62e96 SESSION_017: add public embed preview
4e6272e Branding pass: real Sam's Freedom Ford McAlester identity
f39fce3 SESSION_016: polish Live Assistant customer UI
6d21f08 SESSION_015: wire overview to real data and add mobile shell
7bb19ea SESSION_014: add demo inventory snapshot preview
e3cafcc SESSION_013: Live Assistant page + inline vehicle cards
```

(SESSION_020 will be the next commit to land.)

---

## Operational state (verified 2026-05-02 after SESSION_020)

- **Backend**: Django on `:8001`, Ollama llama3.2 on `:11434`.
- **Frontend**: Vite on `:5173`. Routes:
  - `/dealer-ai-overview` (real APIs, brand-aware)
  - `/dealer-ai-live-assistant` (chat, brand-aware)
  - `/dealer-ai-inventory` (demo snapshot, 18 vehicles)
  - `/dealer-ai-leads` (stub — still SESSION_021b candidate)
  - `/dealer-ai-manager-chat` (Coaching Mode)
  - `/dealer-ai-admin/team` (sales team)
  - `/dealer-ai-onboarding` (Setup — now has the Dealer Kit
    Status card; **SESSION_021 target** for the logo input)
  - `/embed/assistant` (public embed, no shell)
  - `/dealer-ai-demo` (legacy lab, off-nav)
- **Test baseline**: 1210 pass / 1 skip (unchanged since
  SESSION_011; frontend / docs sessions don't move it).
- **Console hygiene**: 0 errors, 0 warnings on every brand-
  aware surface verified in SESSION_020.

---

## Identity quick-reference (post-reframe)

| Layer | Source | Examples |
| --- | --- | --- |
| **Product** | `PRODUCT` in `frontend/src/config/defaultDealer.ts` | Sidebar caption "DEALER AI KIT", embed "Powered by AI Sales Assistant", `<title>` prefix |
| **Default dealer** (fallback) | `DEFAULT_DEALER` in same file | Logo path, fallback name "Sam Wampler's Freedom Ford", fallback location "McAlester", tagline "Sam Wampler Make It Happen" |
| **Active dealer** (runtime) | `OnboardingProfile` via `useBrand()` | Topbar dealer chip, embed brand bar, footer disclaimers, welcome lines, **(SESSION_021)** logo URL when set |

Resolution: `OnboardingProfile` → `DEFAULT_DEALER` → never
hard-coded inline. SESSION_021 extends this to the logo asset.

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

1. The latest handoff (`docs/handoffs/SESSION_020_*.md`).
2. `git log --oneline -10` (what actually shipped).
3. `git show HEAD:frontend/src/<path>` (current source).

Narrative docs are claims. Code and handoffs are facts.
