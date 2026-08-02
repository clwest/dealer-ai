"""Milestone 11 · Increment 1 (SESSION_114) — generic webhook adapter.

Documents the minimum envelope any listing platform (Autotrader,
Cars.com, CarGurus, Facebook Marketplace, Carfax, dealer website
DR system, etc.) ships to a dealer when a customer submits a lead
form on that listing. This adapter is intentionally schema-defensive
— unknown keys are ignored, missing optional keys default to empty
string, and no fields are fabricated on the customer's behalf.

Documented envelope (dealer-owned; platform integrations map into
it, not the other way round)::

    {
        "full_name": "Alice Buyer",              # required
        "phone": "555-0100",                     # optional
        "email": "alice@example.com",            # optional
        "message": "Interested in the F-150",   # optional
        "target_monthly_payment": "450",         # optional (str or num)
        "down_payment": "3000",                  # optional (str or num)
        "trade_in": "2018 Civic 82k",           # optional
        "credit_range": "good",                  # optional
    }

The endpoint layer's serializer enforces that ``full_name`` is
present. This adapter does not re-validate — it only translates
key names into the kwargs :func:`channel_intake._create_lead`
accepts.

Platform-specific adapters (``autotrader.py``, ``cars_com.py``,
``facebook_marketplace.py``, etc.) will land as sibling modules
when operator evidence surfaces the platform-specific field names.
Each one only needs to define a top-level ``normalize`` callable
with the same signature.
"""

from __future__ import annotations

from typing import Any


def normalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Translate the generic-envelope payload into intake kwargs.

    Unknown keys are dropped silently — the envelope is dealer-owned
    and any platform-specific fields belong in a per-platform
    adapter, not this one.
    """
    return {
        "name": payload.get("full_name", ""),
        "phone": payload.get("phone", ""),
        "email": payload.get("email", ""),
        "notes": payload.get("message", ""),
        "target_monthly_payment": payload.get("target_monthly_payment"),
        "down_payment": payload.get("down_payment"),
        "trade_in": payload.get("trade_in", ""),
        "credit_range": payload.get("credit_range", ""),
    }
