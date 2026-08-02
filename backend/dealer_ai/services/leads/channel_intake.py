"""Milestone 11 · Increment 1 (SESSION_114) — channel-specific intake verbs.

One verb per non-chat channel. All verbs:

- Accept ``dealership`` explicitly (tenant discipline; the
  :mod:`services.tenancy` pre_save autofill is a safety net only).
- Write ``channel=<constant>`` from ``dealer_ai.models`` so choice
  vocabulary stays authoritative in one place.
- Return the created :class:`CustomerLead`.

Chat-origin intake stays in :mod:`dealer_ai.services.lead_service` and
lands with the default ``channel="chat"``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from django.db import transaction

from ...models import (
    LEAD_CHANNEL_LISTING_FORM,
    LEAD_CHANNEL_PHONE,
    LEAD_CHANNEL_REFERRAL,
    LEAD_CHANNEL_WALK_IN,
    CustomerLead,
    Dealership,
)


class UnknownWebhookPlatformError(Exception):
    """Raised when a webhook payload names a platform with no adapter."""


class CrossTenantReferrerError(Exception):
    """Raised when a referral write names a referrer lead in another tenant.

    Surfaced at the endpoint layer as 404 (never leak cross-tenant
    existence), matching the M2.6 / M3.6 / M4.6 / M9.1 / M10.1 fail-
    closed convention.
    """


def _decimal_or_none(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return None


def _create_lead(
    *,
    dealership: Dealership,
    channel: str,
    name: str,
    phone: str = "",
    email: str = "",
    notes: str = "",
    target_monthly_payment: Any = None,
    down_payment: Any = None,
    trade_in: str = "",
    credit_range: str = "",
    urgency: str = "",
    referrer: Optional[CustomerLead] = None,
) -> CustomerLead:
    return CustomerLead.objects.create(
        dealership=dealership,
        channel=channel,
        name=(name or "").strip(),
        phone=(phone or "").strip(),
        email=(email or "").strip(),
        notes=notes or "",
        target_monthly_payment=_decimal_or_none(target_monthly_payment),
        down_payment=_decimal_or_none(down_payment),
        trade_in=trade_in or "",
        credit_range=credit_range or "",
        urgency=urgency or "",
        referrer=referrer,
    )


# ---- Per-channel verbs ------------------------------------------------------


def record_walk_in_lead(
    *,
    dealership: Dealership,
    name: str,
    phone: str = "",
    email: str = "",
    notes: str = "",
    target_monthly_payment: Any = None,
    down_payment: Any = None,
    trade_in: str = "",
    credit_range: str = "",
    urgency: str = "",
) -> CustomerLead:
    """Persist a walk-in lead (customer arrived without prior contact).

    Corresponds to SALES §lead acquisition (walk-in channel) +
    workflow step 1 (greeting).
    """
    return _create_lead(
        dealership=dealership,
        channel=LEAD_CHANNEL_WALK_IN,
        name=name,
        phone=phone,
        email=email,
        notes=notes,
        target_monthly_payment=target_monthly_payment,
        down_payment=down_payment,
        trade_in=trade_in,
        credit_range=credit_range,
        urgency=urgency,
    )


def record_phone_lead(
    *,
    dealership: Dealership,
    name: str,
    phone: str = "",
    email: str = "",
    notes: str = "",
    target_monthly_payment: Any = None,
    down_payment: Any = None,
    trade_in: str = "",
    credit_range: str = "",
    urgency: str = "",
) -> CustomerLead:
    """Persist a phone-inquiry lead.

    Corresponds to SALES §lead acquisition (phone channel).
    """
    return _create_lead(
        dealership=dealership,
        channel=LEAD_CHANNEL_PHONE,
        name=name,
        phone=phone,
        email=email,
        notes=notes,
        target_monthly_payment=target_monthly_payment,
        down_payment=down_payment,
        trade_in=trade_in,
        credit_range=credit_range,
        urgency=urgency,
    )


def record_referral_lead(
    *,
    dealership: Dealership,
    name: str,
    phone: str = "",
    email: str = "",
    notes: str = "",
    target_monthly_payment: Any = None,
    down_payment: Any = None,
    trade_in: str = "",
    credit_range: str = "",
    urgency: str = "",
    referrer_lead_id: Optional[int] = None,
) -> CustomerLead:
    """Persist a referral lead. Attribution via ``referrer_lead_id``.

    Corresponds to SALES §lead acquisition (referral channel) +
    workflow step 16 (referral capture). Referrer must belong to the
    same tenant; a cross-tenant referrer_lead_id raises
    :class:`CrossTenantReferrerError` (endpoint layer surfaces as 404
    per fail-closed convention).

    ``referrer_lead_id`` may be omitted — a referral lead where the
    referrer identity is captured only in notes still lands with
    ``channel="referral"`` and a NULL referrer FK.
    """
    referrer_obj: Optional[CustomerLead] = None
    if referrer_lead_id is not None:
        try:
            referrer_obj = CustomerLead.objects.get(pk=referrer_lead_id)
        except CustomerLead.DoesNotExist as exc:
            raise CrossTenantReferrerError(
                f"Referrer lead {referrer_lead_id} not found."
            ) from exc
        if referrer_obj.dealership_id != dealership.id:
            raise CrossTenantReferrerError(
                f"Referrer lead {referrer_lead_id} belongs to another tenant."
            )
    return _create_lead(
        dealership=dealership,
        channel=LEAD_CHANNEL_REFERRAL,
        name=name,
        phone=phone,
        email=email,
        notes=notes,
        target_monthly_payment=target_monthly_payment,
        down_payment=down_payment,
        trade_in=trade_in,
        credit_range=credit_range,
        urgency=urgency,
        referrer=referrer_obj,
    )


def record_webhook_lead(
    *,
    dealership: Dealership,
    platform: str,
    payload: dict,
) -> CustomerLead:
    """Persist a listing-platform webhook lead via adapter dispatch.

    ``platform`` selects the adapter module in :mod:`webhook_adapters`.
    Adapters normalize the platform-native envelope into the kwargs
    that :func:`_create_lead` accepts, then this verb persists the
    row with ``channel="listing_form"``. Per MILESTONE_11_PLANNING.md
    §5.b Option A — one generic endpoint + per-platform adapters.

    Unknown platforms raise :class:`UnknownWebhookPlatformError`
    (endpoint layer surfaces as 400).
    """
    from .webhook_adapters import get_adapter

    try:
        adapter = get_adapter(platform)
    except KeyError as exc:
        raise UnknownWebhookPlatformError(
            f"No webhook adapter registered for platform '{platform}'."
        ) from exc

    normalized = adapter.normalize(payload)
    with transaction.atomic():
        return _create_lead(
            dealership=dealership,
            channel=LEAD_CHANNEL_LISTING_FORM,
            **normalized,
        )
