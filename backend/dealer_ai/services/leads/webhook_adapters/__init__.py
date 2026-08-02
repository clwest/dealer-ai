"""Milestone 11 · Increment 1 (SESSION_114) — webhook adapter registry.

One generic ``POST /admin/leads/webhook/`` endpoint dispatches to a
per-platform adapter module per MILESTONE_11_PLANNING.md §5.b Option A.
Each adapter exposes a single ``normalize(payload: dict) -> dict``
callable that translates the platform-native envelope into the kwargs
:func:`services.leads.channel_intake._create_lead` accepts (``name``,
``phone``, ``email``, ``notes``, plus the shared budget fields).

The first adapter shipped is :mod:`generic` — a documented envelope
that reflects the minimum any listing platform ships to a dealer
(name / phone / email / message + optional budget hints). Additional
named-platform adapters (Autotrader / Cars.com / CarGurus / Facebook
Marketplace) will land as sibling modules once operator evidence
surfaces the platform-specific envelope shapes. The current
``generic`` adapter is *not* a fabricated proprietary shape — it is
a documented, dealer-owned envelope that platform integrations map
into.
"""

from __future__ import annotations

from typing import Callable, Protocol

from . import generic


class WebhookAdapter(Protocol):
    """Duck-typed adapter contract.

    Each adapter module must expose a top-level ``normalize`` callable
    with this signature. Modules — not classes — are the unit of
    registration so tests can register a fake by import path if ever
    needed (not required at M11.1).
    """

    normalize: Callable[[dict], dict]


_ADAPTERS: dict[str, WebhookAdapter] = {
    "generic": generic,
}


def get_adapter(platform: str) -> WebhookAdapter:
    """Return the adapter for ``platform`` or raise ``KeyError``.

    Callers (currently only
    :func:`services.leads.channel_intake.record_webhook_lead`) map the
    ``KeyError`` to :class:`UnknownWebhookPlatformError` so the
    endpoint layer can surface a 400.
    """
    return _ADAPTERS[platform]


def registered_platforms() -> tuple[str, ...]:
    """Introspection helper for tests + operator UI."""
    return tuple(_ADAPTERS.keys())
