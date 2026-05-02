---
date: 2026-05-02
title: SESSION_017 — public embed preview + shared AssistantChat
type: implementation-summary
test_baseline: 1210
---

# Session handoff — public embed preview

SESSION_017 turns the Live Assistant into something a dealership
can actually drop into their marketing site. A new public-embed
surface lives at `/embed/assistant`, rendered **outside** the
dealer OS shell so it inherits no sidebar, topbar, or dashboard
chrome. A new "Public Preview" affordance in the OS topbar lets
the dealer see the embed live alongside the copyable HTML
snippet they paste into their CMS.

To stop the embed and the dealer-side Live Assistant from
drifting, the chat innards (state, transcript, composer,
starters, retry, thinking indicator) were extracted into a
shared `<AssistantChat />` component used by both pages.

No backend changes, no chat behavior changes, no API contracts
touched, no inventory logic touched. Honored every guardrail in
the SESSION_017 spec.

Use this snapshot to pick up at SESSION_018.

---

## What shipped

### 1. Public embed surface — `/embed/assistant`

`frontend/src/pages/EmbedAssistantPage.tsx` (new). Mounted at the
new top-level route registered **before** the `/` (App) tree in
`frontend/src/main.tsx`:

```tsx
<Routes>
  <Route path="/embed/assistant" element={<EmbedAssistantPage />} />
  <Route path="/" element={<App />}>
    {/* dealer-OS routes nested here */}
  </Route>
</Routes>
```

Order matters — putting the embed route ahead of `/` makes
`/embed/assistant` resolve as a top-level page that bypasses the
`<App>` layout entirely. No sidebar, no topbar, no dashboard
chrome. Pure widget.

**Layout:**

- **Mini brand bar** at the top: real
  `Sam's Freedom Ford McAlester` shield logo (same asset as the
  OS shell, committed in the branding pass) + the dealer name
  styled as `Sam's Freedom Ford Assistant` + the SESSION_016
  trust row (Real inventory · Payment-aware · No pressure)
  inline beneath. A small `New chat` ghost button appears once
  the user has sent a message; otherwise hidden so the empty
  state stays clean.
- **Centered chat container** (`max-w-3xl`) with the shared
  `<AssistantChat />` rendering the same starters / transcript
  / composer the dealer-side page uses. Welcome line tweaked to
  read like a customer-facing intro:
  *"Hi — I'm Sam's Freedom Ford's sales assistant."*
- **Subtle footer**: *"Estimates only. A Sam's Freedom Ford
  advisor confirms real numbers."* on the left, **"Powered by
  AI Sales Assistant"** on the right (hidden on mobile via
  `sm:inline` so the line stays clean at narrow widths).

**What's intentionally absent:**

- No sidebar / topbar / hamburger / OS chrome.
- No "Dealer OS" wording. The dealer sees that label inside
  their workspace; the customer never should.
- No "Buy Now" stacks, no lead form, no popup, no
  estimate-payment lead-grab. Same forbidden patterns the
  SITE_AUDIT retired.

The `<title>` in the document head still reads *"Sam's Freedom
Ford McAlester — Dealer OS"* because the embed shares the OS's
HTML shell. Future sessions can split the title per-route if
that matters for SEO; at iframe time the parent page's title
is what shows in the address bar anyway.

### 2. Shared `<AssistantChat />` extraction

`frontend/src/components/AssistantChat.tsx` (new). Owns:

- Chat state — `sessionId`, `messages`, `input`, `status`,
  `error`, `lastUserMessage`.
- All handlers — `ensureSession`, `handleSend`, `handleSubmit`,
  `handleContinue`, `handleRetry`.
- Transcript scroll container with messages, thinking
  indicator, error retry block.
- Composer with disabled / loading states.
- Empty-state starter chips.
- The full SESSION_016 visual polish (3-dot pulse thinking,
  amber retry block, customer-voice copy).

**Reset is parent-driven via `key` remount** — no imperative
handle, no `useImperativeHandle`, no `forwardRef` API surface.
Both `LiveAssistantPage` and `EmbedAssistantPage` keep a
`chatKey` state and bump it to remount with fresh state:

```tsx
const [chatKey, setChatKey] = useState(0);
function handleReset() {
  setChatKey((k) => k + 1);
  setHasMessages(false);
}
// …
<AssistantChat key={chatKey} onActivityChange={setHasMessages} />
```

**`onActivityChange` callback** notifies the parent when the
conversation transitions empty → non-empty so the parent can
show its own "New chat" affordance only after the user has
sent at least one message. Both pages use this to gate their
respective reset buttons.

`LiveAssistantPage.tsx` shrank from ~310 lines to ~62. All
chat behavior moved into the shared component, leaving only
the dealer-side header (title + trust row + reset) and the
disclaimer footer.

**Behavior parity is total** — both pages call into the same
`AssistantChat`, so a future change to retry copy, starter
phrasing, vehicle-card rendering, or thinking indicator
applies to both surfaces simultaneously. No drift possible.

### 3. Public Preview dialog

`frontend/src/components/PublicPreviewDialog.tsx` (new).
Mounted in the global topbar (`frontend/src/App.tsx`) next to
the AI Active indicator — reachable from any OS page, not just
Overview, since "see how this looks externally" is a meta
action that's always relevant.

**The dialog renders:**

- shadcn `<Dialog>` widened to `sm:max-w-3xl` (the default
  `max-w-sm` would have squeezed the iframe).
- Title: *"Public Preview"*.
- Description: *"This is how the assistant appears on your
  website."*
- A **live iframe** (`<iframe src={embedUrl}>`) showing the
  actual `/embed/assistant` page at 480 px tall — so the
  dealer sees their own product, not a static screenshot.
- An **embed-code block** rendered as a read-only `<textarea>`
  (selects on focus) containing the canonical snippet:

  ```html
  <iframe
    src="${origin}/embed/assistant"
    width="100%"
    height="700"
    style="border: none; border-radius: 8px;"
  ></iframe>
  ```

- A **Copy** button using `navigator.clipboard.writeText` with
  a 1.5 s "Copied" confirmation and a `Check` icon.
- An **"Open the embed in a new tab"** link below the snippet
  for full-window preview.

**`embedUrl` is built from `window.location.origin`** memoized
at mount, so the snippet automatically tracks whatever host
the OS is running on — `localhost:5173` in dev, the deployed
hostname in production. No env-var plumbing required.

**`onOpenAutoFocus` is intercepted** to keep focus on the
dialog rather than letting it land inside the iframe. Better
for screen-reader behavior; nothing in the iframe needs
immediate focus.

### 4. Dialog primitive forwardRef patch

`frontend/src/components/ui/dialog.tsx` — `DialogOverlay` and
`DialogContent` were function components without `forwardRef`,
the same pattern that produced a runtime ref warning when the
mobile `Sheet` first opened in SESSION_015. The SESSION_015
handoff predicted this exact fix would be needed when Dialog
was first opened in a future session. Applied the same patch
proactively this session — wrapped both in `React.forwardRef`
with `displayName`. Console stayed clean when the Public
Preview dialog opened.

`DropdownMenu` and `Tabs` carry the same pattern and remain
unfixed — patch reactively when first opened in a later
session.

---

## Files changed

```
frontend/src/components/AssistantChat.tsx            NEW (shared chat surface)
frontend/src/components/PublicPreviewDialog.tsx      NEW (topbar Public Preview)
frontend/src/components/ui/dialog.tsx                forwardRef on DialogOverlay + DialogContent
frontend/src/pages/EmbedAssistantPage.tsx            NEW (/embed/assistant)
frontend/src/pages/LiveAssistantPage.tsx             refactored — uses AssistantChat
frontend/src/main.tsx                                + /embed/assistant route OUTSIDE App tree
frontend/src/App.tsx                                 + <PublicPreviewDialog /> in global topbar
docs/handoffs/SESSION_017_public_embed_preview.md    NEW (this file)
```

---

## Verification

| Step | Result |
| --- | --- |
| `npx tsc --noEmit` | ✓ 0 errors |
| `npx vite build` | ✓ 1.04s · 1715 modules · 48.55 kB CSS · 432.08 kB JS (gzip 120.51 kB) |
| Playwright `/embed/assistant` desktop (1366×900) | ✓ no sidebar / no topbar / no dashboard chrome |
| Embed brand bar — shield logo + "Sam's Freedom Ford Assistant" + trust row | ✓ |
| Embed empty state — bot avatar + welcome + 4 starters in 2-col grid | ✓ |
| Embed footer — "Estimates only…" + "Powered by AI Sales Assistant" | ✓ |
| Embed mobile (390×844) | ✓ brand bar wraps, starters stack, "Powered by…" hidden via sm:inline |
| Console at `/embed/assistant` | ✓ 0 errors, 0 warnings |
| Overview — "Public Preview" button visible in topbar next to AI Active | ✓ |
| Click "Public Preview" opens shadcn Dialog | ✓ |
| Dialog renders live iframe of `/embed/assistant` | ✓ real assistant chrome inside iframe |
| Embed-code textarea shows the canonical snippet | ✓ |
| Copy button + "Open in new tab" link work | ✓ |
| Console with Dialog open | ✓ 0 errors, 0 warnings (forwardRef patch held) |

Backend baseline unchanged — SESSION_017 is frontend-only.
SESSION_011's 1210 pass / 1 skip baseline still holds.

Screenshots saved locally as
`session_017_embed_desktop.png`,
`session_017_embed_mobile.png`,
`session_017_public_preview_modal.png`
(gitignored under `/*.png`).

---

## Known limitations

- **Iframe height is fixed.** The dialog renders the iframe at
  480 px tall (fits the modal); the copyable snippet hard-codes
  `height="700"`. If a dealer's site needs a different height
  they edit the snippet manually after copy. A future session
  could expose a height input or use `100dvh` with a
  postMessage resize protocol — overkill for this pass.
- **Snippet uses `window.location.origin`.** Built once at
  mount, memoized. Fine for dev (`localhost:5173`) and for
  production deploys where the OS and the embed live on the
  same host. If the OS is ever served on a different origin
  than the embed (separate subdomain, separate CDN, white-
  label hosting), the snippet would need a configurable
  `EMBED_ORIGIN` env var.
- **No backend CSP / X-Frame-Options allowlist yet.** The
  iframe loads same-origin in this session, which works
  locally without any framing headers. When the embed has to
  load on a different host (the dealer's actual marketing
  site), Django needs an `X-Frame-Options: ALLOWALL` /
  `frame-ancestors` CSP allowlist on the `/embed/assistant`
  response. Explicitly out of scope per the SESSION_017 "no
  backend" guardrail; needs a backend-touching session.
- **Setup dealership name does not yet drive OS / embed
  branding.** The strings `Sam's Freedom Ford`, `McAlester`,
  and the trust-row labels are hard-coded constants in
  `App.tsx` and `EmbedAssistantPage.tsx`. The
  `OnboardingProfile.dealership_name` and `store_location`
  fields exist on the backend and ship in the
  `fetchOnboardingProfile()` payload — they're already used
  by the Overview page's Assistant Status card. Wiring them
  through to the brand chrome is the natural SESSION_018.
- **Iframe `<title>` is the same as the OS document title** —
  cosmetic; only matters if a search engine ever indexes the
  embed URL directly, which it shouldn't (intended for
  iframe-only consumption).
- **`/dealer-ai-demo` legacy route** still mounted from prior
  sessions, untouched. Decision deferred again.

---

## Recommended next session

**SESSION_018 — Brand settings drive UI.**

The Setup page already collects the dealership's identity
(`dealership_name`, `store_location`, `main_brands`,
`sales_phone`, etc.) and persists it to
`OnboardingProfile`. Today those values are read by the
Overview's Assistant Status card and nowhere else — every
brand surface in the app shell and embed still hard-codes
`Sam's Freedom Ford` / `McAlester`. SESSION_018 closes that
loop so a manager who edits Setup sees the OS chrome update.

**Scope:**

- Read `dealership_name` and `store_location` (and
  `main_brands` for the embed welcome line if useful) from
  the existing `fetchOnboardingProfile()` payload.
- Replace the hard-coded constants in:
  - `frontend/src/App.tsx` (sidebar `<BrandHeader />`,
    topbar store name, mobile drawer).
  - `frontend/src/pages/EmbedAssistantPage.tsx` (mini brand
    bar, welcome line, footer disclaimer).
  - `frontend/src/components/PublicPreviewDialog.tsx`
    (iframe title attribute, snippet — though the snippet
    might still want the original store name as the iframe's
    accessible name).
- Cache the profile load at the App-shell level (single
  fetch, shared via context or just prop-drilled) so the
  brand strings don't flicker as each surface fetches its
  own copy.
- **Fallback to current hard-coded values** (`Sam's Freedom
  Ford` / `McAlester`) when the profile is null, empty, or
  the fetch fails — graceful degradation matters for the
  embed surface, which can be loaded by a customer before
  the OS ever boots in a manager's tab.
- **Do NOT change the logo asset.** That's a manually-
  curated brand-team handoff, not derivable from a string
  field. The shield logo at
  `frontend/public/branding/sams-freedom-ford-logo.jpg`
  stays. If a future dealer needs a different logo, that's
  a separate uploaded-asset session.

**Strict out-of-scope guardrails for SESSION_018:**

- ❌ No chat behavior changes (no prompt edits, no scrub
  edits, no manager-chat enforcement edits).
- ❌ No new backend endpoints. The
  `/onboarding/profile/` endpoint already returns
  everything needed.
- ❌ No new pages.
- ❌ No iframe / embed CSP / X-Frame-Options work — those
  belong in a separate backend-touching session whenever
  cross-origin embedding becomes a real requirement.
- ❌ Do not retire `/dealer-ai-demo`, edit the inventory
  snapshot, or touch the AssistantChat component itself.

**Tiny serializer check that's permitted:** if any of the
fields above are missing from the existing
`OnboardingProfilePayload` interface in
`frontend/src/lib/api.ts` despite the backend serializing
them, add them to the TypeScript interface. That's a
read-only contract sync, not a behavior change. Anything
deeper (new field on the model, new endpoint, new
serializer) is out of scope.

After SESSION_018 lands, the OS becomes truly
multi-tenant-ready in chrome: a different dealer with a
different `OnboardingProfile` would see their own name in
every chrome surface without a code change. The logo asset
remains the only manually-curated handoff.
