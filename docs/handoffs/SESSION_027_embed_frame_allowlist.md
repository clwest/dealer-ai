---
date: 2026-05-03
title: SESSION_027 — embed frame allowlist
type: implementation-summary
test_baseline: embed policy tests clean, frontend tsc/build clean, Playwright embed preview clean
---

# Session handoff — embed frame allowlist

SESSION_027 added scoped frame-ancestor policy for the public assistant
embed. The goal was to let approved external dealer sites iframe
`/embed/assistant` without making the whole app frameable.

No public-site redesign, chat behavior, CRM, email/SMS, dealer config
constant, or `/dealer-ai-demo` work was done.

---

## What changed

### 1. Django fallback policy

Changed:

- `backend/freedom_ford/settings.py`
- `backend/freedom_ford/middleware.py`

New setting:

```text
DEALER_AI_EMBED_ALLOWED_ORIGINS=https://dealer.example,https://www.dealer.example
```

New middleware:

- Applies only when `request.path` is `/embed/assistant`.
- Removes `X-Frame-Options`.
- Adds:

```text
Content-Security-Policy: frame-ancestors 'self' <allowed origins>
```

Non-embed backend/API responses keep Django's default
`X-Frame-Options: DENY`.

This is a fallback for deployments where Django serves the SPA or handles
the embed route. In local development, Vite serves the frontend route.

### 2. Vite dev / preview policy

Changed:

- `frontend/vite.config.ts`

New environment variable:

```text
VITE_EMBED_ALLOWED_ORIGINS=https://dealer.example,https://www.dealer.example
```

Vite dev and preview now apply the same CSP frame-ancestors header only
for `/embed/assistant`. Other frontend routes are unchanged.

### 3. Tests

Added:

- `backend/dealer_ai/tests/test_embed_frame_policy.py`

Coverage:

- `/embed/assistant` receives a `frame-ancestors` allowlist and no
  `X-Frame-Options`.
- Non-embed API paths keep `X-Frame-Options: DENY` and do not receive
  the scoped CSP header.

---

## Verification

Executed:

- `./.venv/bin/python manage.py test dealer_ai.tests.test_embed_frame_policy dealer_ai.tests.test_onboarding_profile`
  — pass, 18 tests.
- `npx tsc --noEmit` — pass.
- `npx vite build` — pass.
- Vite dev server with:

```text
VITE_API_PROXY_TARGET=http://127.0.0.1:8001
VITE_EMBED_ALLOWED_ORIGINS=https://dealer.example
```

- Django dev server on `http://127.0.0.1:8001/`.
- Header checks:
  - `GET http://127.0.0.1:5173/embed/assistant`
    returned `Content-Security-Policy: frame-ancestors 'self' https://dealer.example`.
  - `GET http://127.0.0.1:5173/dealer-ai-overview`
    did not receive the embed CSP header.
  - `GET http://127.0.0.1:8001/embed/assistant`
    removed `X-Frame-Options` and returned `frame-ancestors 'self'`.
- Playwright:
  - `/embed/assistant` renders.
  - Operator Public Preview iframe renders the embed.
  - Console/network clean.

Screenshots saved locally at repo root:

```text
session_027_embed_assistant.png
session_027_public_preview.png
```

---

## Runtime notes

For a real dealer website, set both environment variables where relevant:

```text
DEALER_AI_EMBED_ALLOWED_ORIGINS=https://dealer-site.example
VITE_EMBED_ALLOWED_ORIGINS=https://dealer-site.example
```

If only Vite/static hosting serves the frontend, the Vite/static host
needs the header. If Django serves the SPA, the Django middleware covers
the embed path.

Do not use a wildcard. The allowlist is intentionally explicit.

---

## Recommended next session

Move to the deferred inventory data quality cleanup.

