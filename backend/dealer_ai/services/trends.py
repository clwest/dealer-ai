"""Aggregation/trend calculations for the manager dashboard.

Pure functions that read from the existing models — nothing here depends on the
HTTP layer, so each helper is independently testable.
"""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.db.models import Avg, Count
from django.utils import timezone

from ..models import ChatSession, CustomerLead, Vehicle
from .payment_engine import affordable_max_price


# How much over the affordability ceiling we tolerate before calling it a mismatch.
BUDGET_MISMATCH_HEADROOM = 1.25


def total_chat_sessions() -> int:
    return ChatSession.objects.count()


def total_leads() -> int:
    return CustomerLead.objects.count()


def _profile_value_counts(field: str, *, limit: int = 5) -> List[Dict[str, Any]]:
    """Return [{'value': X, 'count': N}, ...] for a key in extracted_profile."""
    counter: Counter[str] = Counter()
    qs = ChatSession.objects.exclude(extracted_profile={}).values_list(
        "extracted_profile", flat=True
    )
    for profile in qs:
        if not profile:
            continue
        value = profile.get(field)
        if not value:
            continue
        counter[str(value)] += 1
    return [{"value": v, "count": c} for v, c in counter.most_common(limit)]


def top_requested_models(limit: int = 5) -> List[Dict[str, Any]]:
    return _profile_value_counts("model", limit=limit)


def top_requested_vehicle_types(limit: int = 5) -> List[Dict[str, Any]]:
    return _profile_value_counts("vehicle_type", limit=limit)


def average_target_monthly_payment() -> Optional[float]:
    """Average across captured leads (authoritative) — falls back to session
    profiles when no leads have a target yet."""
    avg = (
        CustomerLead.objects.exclude(target_monthly_payment__isnull=True)
        .aggregate(avg=Avg("target_monthly_payment"))
        .get("avg")
    )
    if avg is not None:
        return float(avg)

    values: List[float] = []
    for profile in ChatSession.objects.exclude(extracted_profile={}).values_list(
        "extracted_profile", flat=True
    ):
        v = profile.get("target_monthly_payment") if profile else None
        try:
            values.append(float(v))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    return sum(values) / len(values)


def most_selected_vehicles(limit: int = 5) -> List[Dict[str, Any]]:
    qs = (
        Vehicle.objects.annotate(lead_count=Count("leads"))
        .filter(lead_count__gt=0)
        .order_by("-lead_count", "-year")[:limit]
    )
    return [
        {
            "id": v.id,
            "stock_number": v.stock_number,
            "display_name": v.display_name,
            "price": str(v.price),
            "lead_count": v.lead_count,  # type: ignore[attr-defined]
        }
        for v in qs
    ]


def _lead_is_budget_mismatch(lead: CustomerLead) -> bool:
    target = lead.target_monthly_payment
    if target is None:
        return False
    try:
        target_f = float(target)
    except (TypeError, ValueError):
        return False
    if target_f <= 0:
        return False

    down = float(lead.down_payment or 0)
    flagged = list(lead.interested_vehicles.all())
    if not flagged:
        return False

    max_price = affordable_max_price(target_f, down_payment=down)
    if max_price <= 0:
        return False
    top_price = max(float(v.price) for v in flagged)
    return top_price > max_price * BUDGET_MISMATCH_HEADROOM


def budget_mismatch_count() -> int:
    qs = (
        CustomerLead.objects.exclude(target_monthly_payment__isnull=True)
        .annotate(vehicle_count=Count("interested_vehicles"))
        .filter(vehicle_count__gt=0)
        .prefetch_related("interested_vehicles")
    )
    return sum(1 for lead in qs if _lead_is_budget_mismatch(lead))


def recent_customer_intents(limit: int = 10) -> List[Dict[str, Any]]:
    sessions = (
        ChatSession.objects.exclude(extracted_profile={})
        .order_by("-updated_at")[: limit * 2]
    )
    out: List[Dict[str, Any]] = []
    for session in sessions:
        profile = session.extracted_profile or {}
        intent = profile.get("intent")
        if not intent:
            continue
        out.append(
            {
                "session_id": str(session.id),
                "intent": intent,
                "vehicle_type": profile.get("vehicle_type"),
                "model": profile.get("model"),
                "target_monthly_payment": profile.get("target_monthly_payment"),
                "urgency": profile.get("urgency"),
                "updated_at": session.updated_at.isoformat(),
            }
        )
        if len(out) >= limit:
            break
    return out


def trends_snapshot() -> Dict[str, Any]:
    """One-shot aggregate used by GET /admin/trends/."""
    avg = average_target_monthly_payment()
    return {
        "generated_at": timezone.now().isoformat(),
        "total_chat_sessions": total_chat_sessions(),
        "total_leads": total_leads(),
        "total_leads_last_7d": CustomerLead.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count(),
        "average_target_monthly_payment": (
            round(avg, 2) if avg is not None else None
        ),
        "budget_mismatch_count": budget_mismatch_count(),
        "top_requested_models": top_requested_models(),
        "top_requested_vehicle_types": top_requested_vehicle_types(),
        "most_selected_vehicles": most_selected_vehicles(),
        "recent_customer_intents": recent_customer_intents(),
    }
