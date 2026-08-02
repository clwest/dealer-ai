"""Milestone 11 · Increment 1 (SESSION_114) — non-chat lead intake package.

Adds channel-specific write verbs on top of the M1 CustomerLead model
per MILESTONE_11_PLANNING.md §1.1 + §1.6 (§5.a Option A additive
CharField + backfill; §5.b Option A generic webhook + adapter dispatch;
§1.6 referrer self-FK for referral attribution). The existing M1
chat-funnel intake path (:mod:`dealer_ai.services.lead_service`)
remains unchanged — chat-origin leads land with the default
``channel="chat"``.

Public verbs:

- :func:`record_walk_in_lead`
- :func:`record_phone_lead`
- :func:`record_referral_lead`
- :func:`record_webhook_lead`

Each verb writes ``dealership`` explicitly (M4+ tenancy discipline);
the ``services.tenancy`` pre_save autofill is the safety net only.
Every verb returns the created :class:`CustomerLead`.

Domain errors:

- :class:`UnknownWebhookPlatformError` — 400 at the endpoint layer.
- :class:`CrossTenantReferrerError` — 404 at the endpoint layer
  (never leak cross-tenant existence).
"""

from __future__ import annotations

from .channel_intake import (
    CrossTenantReferrerError,
    UnknownWebhookPlatformError,
    record_phone_lead,
    record_referral_lead,
    record_walk_in_lead,
    record_webhook_lead,
)

__all__ = [
    "CrossTenantReferrerError",
    "UnknownWebhookPlatformError",
    "record_phone_lead",
    "record_referral_lead",
    "record_walk_in_lead",
    "record_webhook_lead",
]
