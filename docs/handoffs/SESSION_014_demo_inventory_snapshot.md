---
date: 2026-05-02
title: SESSION_014 — demo inventory snapshot + Inventory preview page
type: implementation-summary
test_baseline: 1210
---

# Session handoff — demo inventory snapshot

SESSION_014 is a small, intentionally-bounded UI realism pass. The
goal was to make the OS feel like it knows about the dealer's actual
lot — by capturing a small sample of public inventory data + image
URLs from samsfreedomford.com and rendering it on a new Inventory
preview page. **No production scraper. No backend changes. No chat
behavior tuning.**

This is the bridge surface between SESSION_013 (Live Assistant — real
backend chat) and the future CRM/DMS feed integration. When that
feed lands, the snapshot file is deleted and the consumers
(currently one page) are pointed at the live source.

Use this snapshot to pick up at SESSION_015.

---

## What shipped

### 1. Captured demo inventory snapshot

`frontend/src/data/freedomFordInventorySample.ts` — typed TypeScript
module with 18 curated vehicles plus capture metadata
(`FREEDOM_FORD_SAMPLE_CAPTURED_AT`, `FREEDOM_FORD_SAMPLE_SOURCE_URL`).

**Source pages visited (Playwright MCP, single visit each):**

| URL | Condition mix | Vehicles taken |
| --- | --- | --- |
| `https://www.samsfreedomford.com/inventory/new-vehicles/` | New | 8 |
| `https://www.samsfreedomford.com/inventory/used-vehicles/` | Used + Certified | 10 |

No pagination, no login, no aggressive scrolling beyond the same
lazy-load behavior a regular human visitor would trigger. 27 unique
vehicles were extracted across the two pages; **18** were kept after
curation for visual variety. The remaining 9 were near-duplicates
(another Maverick trim, etc.) and dropped to keep the demo grid
tight.

**Fields captured per vehicle:**

- `vin` — 17-char (extracted from URL slug)
- `stock_number` — from inline "Stock #: …" text
- `year`, `make`, `model`, `trim` — parsed from title link + body
- `condition` — `new` / `used` / `certified`
- `drivetrain` — `AWD` / `FWD` / `4WD` / `RWD` / `4×4`
- `fuel_type` — `Gasoline` / `Hybrid`
- `exterior_color` — from "Ext: …" text (null when absent)
- `mileage` — 0 for new, real mileage for used
- `price` — Freedom Price as displayed
- `msrp` — sticker; new only (null on used)
- `image_url` — Jazel CDN; protocol-relative on source, normalized
  to `https://`
- `vdp_url` — full canonical VDP link
- `display_name` — pre-computed for card rendering convenience

**Sample profile:**

- 8 new (Mavericks across XL / XLT / AWD / FWD / Hybrid + 1 Bronco
  Sport + 1 Escape Active)
- 10 used / certified across 7 brands (Ford, Cadillac, Mercedes,
  Mazda, Jeep, Chevrolet, Lincoln)
- Price range $22,176–$33,879
- Mileage range 0 (new) to 95,753 (used)
- Body styles: truck, SUV, crossover, sedan
- 2 of the 10 used items are Certified, surfaced via the
  `condition: "certified"` enum

### 2. Inventory preview page

`frontend/src/pages/InventoryPreviewPage.tsx` mounted at
`/dealer-ai-inventory`. Read-only, no mutations, no chat side
effects.

**Layout:**

- **Page header** — `Inventory` heading + a live count derived from
  the sample: *"Visual preview of the dealer's lot. 8 new · 10
  used / certified."*
- **Demo banner** — amber surface with `Sparkles` icon. Explicit
  callout: *"Demo data — Sample of 18 vehicles captured on
  2026-05-02 from samsfreedomford.com. Used here for visual realism
  only — the Live Assistant uses real backend inventory. Will be
  replaced by the CRM/DMS feed when that integration lands."* Links
  back to the source page so the provenance is one click away.
- **Card grid** — `sm:grid-cols-2 lg:grid-cols-3`. Each card uses
  the existing shadcn `Card` primitive with:
  - 16:9 image at the top, lazy-loaded, `object-cover`
  - Condition pill overlay (`new` emerald / `used` amber /
    `certified` sky)
  - Title (`display_name`) + Stock # · Exterior color
  - Price (Ford blue, right-aligned) + MSRP strikethrough on new
  - Spec chips: mileage / drivetrain / fuel
  - VIN-tail badge for used / certified
  - Single ghost CTA: **View on dealer site** → opens VDP in a new
    tab

### 3. Sidebar + route wiring

- `frontend/src/main.tsx` — registered `<Route path="dealer-ai-
  inventory" element={<InventoryPreviewPage />} />` between Live
  Assistant and the legacy `/dealer-ai-demo` route.
- `frontend/src/App.tsx` — added `Inventory` (with `Car` icon from
  `lucide-react`) to the `NAV_ITEMS` array between Live Assistant
  and Coaching Mode. Active styling matches the rest of the
  sidebar (`text-primary` + `border-l-2 border-primary`).

The SESSION_012 sidebar order is now:

```
Overview · Live Assistant · Inventory · Coaching Mode · Team · Setup
```

### 4. Live Assistant deliberately untouched

The Live Assistant page (`/dealer-ai-live-assistant`) continues to
fetch real inventory through `start_chat` / `send_message`. The
sample data is **not** wired in as a fallback — the backend
`Vehicle` shape and the demo `FreedomFordSampleVehicle` shape are
allowed to drift apart since the demo file is temporary. Crossing
the streams would create a contract drift risk for a feature that
exists only to be deleted.

---

## Verification

| Step | Result |
| --- | --- |
| `npx tsc --noEmit` | ✓ 0 errors |
| `npx vite build` | ✓ 1.00s · 1709 modules · 46.92 kB CSS · 378.57 kB JS (gzip 105.12 kB) |
| Playwright `/dealer-ai-inventory` load | ✓ |
| Sidebar renders Inventory active in Ford blue | ✓ |
| Card count via DOM probe | 18 (matches data file) |
| Image count via DOM probe | 18 |
| Images loaded on first paint | 15 of 18 (3 below-the-fold lazy-load on scroll) |
| Broken images (`naturalWidth === 0`) | 0 |
| Subtitle text via DOM probe | "Visual preview of the dealer's lot. 8 new · 10 used / certified." |
| Console errors | 0 |
| Console warnings | 2 pre-existing React Router v7 future-flag warnings |

Screenshot saved locally as `session_014_inventory_preview.png`
(already gitignored under the `/*.png` pattern from SESSION_013).

Backend baseline unchanged — SESSION_014 is frontend-only.
SESSION_011's 1210 pass / 1 skip baseline still holds.

---

## Files changed

```
frontend/src/App.tsx                                    + Inventory sidebar item with Car icon
frontend/src/main.tsx                                   + /dealer-ai-inventory route + import
frontend/src/data/freedomFordInventorySample.ts         NEW — typed demo data + capture metadata
frontend/src/pages/InventoryPreviewPage.tsx             NEW — read-only preview grid
docs/handoffs/SESSION_014_demo_inventory_snapshot.md    NEW (this file)
```

---

## Limitations / known notes

- **Demo snapshot only.** Static file, no revalidation, no cron.
  Vehicles sell, prices change, photos rotate. Re-capture by hand
  (or wait for the real feed) when the demo starts to feel stale.
- **Image URLs only — no images downloaded.** All `image_url`
  values point at the dealer's Jazel CDN. The repo carries no
  binary blobs from this capture.
- **Image host is a `-qa` subdomain.**
  `media-cdn-a5-jazel-tango.jazel-qa.com` is the host the live
  site serves from, but the `qa` segment suggests the bucket can
  rotate without warning. If images start 404'ing on demos,
  re-capture or hard-code a known-good fallback. Don't try to
  cache the binaries inside the repo as a workaround — that
  recreates the supply-chain footprint we explicitly avoided.
- **Not the production CRM/DMS feed.** This file is a deliberate
  stub. It will be deleted when the real feed integration lands.
  Treat consumers as throwaway: there is exactly one consumer
  today (`InventoryPreviewPage.tsx`), and the migration path is
  "delete the data file, repoint the import, update the page to
  the live shape."
- **Live Assistant still uses backend `matched_vehicles`.** No
  drift, no fallback wiring. The demo data and the chat-time
  vehicle data are separate code paths on purpose.
- **Overview page intentionally not modified.** SESSION_014's spec
  listed Overview cards as a possible target. Skipped: the
  Overview's recent-activity / coaching-summary / attention-items
  cards are about events, not inventory items. Adding a "Recent
  inventory" card here would have muddied the SESSION_015 plan to
  wire Overview to real audit-event data. Deferred to a focused
  Overview pass.
- **Curated subset.** 27 unique VINs were extracted; 9 were
  dropped (mostly extra Maverick trims that didn't add visual
  variety). The 18-vehicle slice is pure presentation choice — a
  full snapshot would be larger and noisier without telling the
  demo story any better.
- **VDP-only fields not captured.** Things like full feature
  list, engine spec, transmission spec, and interior-color
  details live on each individual VDP. Hitting 18 VDPs would
  exceed the SESSION_014 "small sample" boundary. The fields the
  preview page actually renders (image, title, condition,
  mileage, drivetrain, fuel, price) are all present from the
  listing pages alone.
- **Lazy-loading visible in screenshots.** With `loading="lazy"`
  on the card images, off-screen items appear as gray
  placeholders until scrolled into view. Expected behavior, not
  a bug.

---

## Recommended next session

**SESSION_015 — UI polish pass / Overview realism using existing
APIs only.**

The Live Assistant (SESSION_013) and Inventory preview
(SESSION_014) are the two surfaces a dealer demo will spend the
most time on. The Overview page is the third — and right now it
still serves placeholder data from SESSION_012. SESSION_015
finishes the polish loop.

**Scope:**

- **Overview realism, using only existing backend endpoints.**
  Wire the four Overview cards to the APIs already serving
  traffic (seen in the backend log at session start):
  - **Recent activity** → `/api/dealer-ai/admin/audit-events/?since=24h`
  - **Coaching summary** → derive scenario count from
    `audit-events` `manager_chat` rows, OR use whatever rollup
    is already available; do NOT add a new backend endpoint in
    this session.
  - **Attention items** → derived rules over the existing
    `OnboardingProfile` payload (`banned_phrases` empty,
    `salespeople_added=false`, `payment_disclaimer` empty,
    `pilot_approved=false`).
  - **Today's leads (new card)** → 3-row preview from
    `/api/dealer-ai/admin/leads/?limit=3&ordering=-created_at`,
    with a `View all →` link that stubs to a `Leads` placeholder
    page (full Leads pipeline ships in a later session).
- **Polish-only changes elsewhere.** While we're touching the
  shell, fix two SESSION_012 papercuts:
  - Sidebar collapses below `sm:` with no hamburger. Add a
    `Sheet`-based mobile drawer using the shadcn `Sheet`
    primitive that's already installed.
  - The two React Router v7 future-flag warnings on every page
    load. One-line fix at `BrowserRouter` setup; clears the
    console.

**Strict out-of-scope guardrails for SESSION_015:**

- ❌ No new backend endpoints. Use what's already serving traffic.
- ❌ No chat behavior changes.
- ❌ No new pages beyond a stub `LeadsPage` placeholder if the
  Today's leads card needs a `View all →` target.
- ❌ Do not retire `/dealer-ai-demo`. Leave the legacy lab
  mounted; rename / retire is a separate decision.
- ❌ Do not modify the inventory snapshot or the
  `InventoryPreviewPage`.

After SESSION_015 lands, the OS will look complete enough for an
honest dealer-side demo: real Overview signal, real Live Assistant
chat with inline vehicle cards, demo Inventory preview that's
explicitly framed as demo, working Coaching Mode, and a mobile-
usable shell. The next major decision becomes whether to chase the
public embed (the original SESSION_017 plan) or the Leads pipeline
page first — punt that decision to the SESSION_015 handoff.
