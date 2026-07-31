"""Runtime dealer-identity resolver used by every LLM prompt + template.

The kit ships with **no dealer** baked in. Every module that used to
hardcode "Freedom Ford" now formats its prompt/response with
`{dealer_name}` and resolves the value at call time via
`get_dealer_name()`.

Resolution order (first non-empty wins):

1. ``settings.DEALER_AI_DEALER_NAME`` (env-driven —
   `DEALER_AI_DEALER_NAME=...` in `backend/.env` or repo-root `.env`).
2. ``DealerOnboardingProfile.dealership_name`` (the singleton persisted
   via the Setup UI — matches the source-of-truth `useBrand()` uses on
   the frontend).
3. ``"the dealership"`` — a bland but sentence-safe fallback so
   generated copy stays coherent when nothing is configured yet.

Keep this module *dependency-light*: importing it must not require the
Django app registry to be ready, so DB access is lazy and swallowed.
"""

from __future__ import annotations

from django.conf import settings

_FALLBACK_DEALER_NAME = "the dealership"


def get_dealer_name() -> str:
    """Return the display name for the currently-configured dealer."""
    env_name = (getattr(settings, "DEALER_AI_DEALER_NAME", "") or "").strip()
    if env_name:
        return env_name

    try:
        # Lazy import so this module is safe to import at settings-load time.
        from ..models import DealerOnboardingProfile

        profile = DealerOnboardingProfile.objects.first()
        if profile:
            name = (profile.dealership_name or "").strip()
            if name:
                return name
    except Exception:
        # Table doesn't exist yet (fresh install pre-migrate), DB is
        # offline, or the model import fails. Fall through to the
        # bland default rather than crash any caller.
        pass

    return _FALLBACK_DEALER_NAME
