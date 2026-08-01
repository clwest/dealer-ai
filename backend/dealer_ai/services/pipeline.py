"""Manager Phase 2: sales pipeline + demand-vs-supply + recommended actions.

Pure-function aggregation over the existing CustomerLead and Vehicle models.
No schema changes, no migrations, no chat-engine touches. The single public
entry is :func:`pipeline_snapshot`, used by ``GET /admin/pipeline/``.

Stages are derived (not stored) — every CustomerLead lands in exactly one of:

    high_intent → new → needs_handoff → researching → contacted

Precedence is evaluated in :func:`_stage_for_lead`. Customer chat is
explicitly out of scope for this module — it neither reads nor writes any
ChatSession / ChatMessage state.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.utils import timezone

from ..models import CustomerLead, Vehicle
from .payment_engine import affordable_max_price
from .trends import (
    most_selected_vehicles,
    top_requested_models,
    top_requested_vehicle_types,
)


# ---- Stage definitions ------------------------------------------------------

STAGE_KEYS: tuple[str, ...] = (
    "high_intent",
    "new",
    "needs_handoff",
    "researching",
    "contacted",
)

STAGE_LABELS: Dict[str, str] = {
    "high_intent": "High intent",
    "new": "New (24h)",
    "needs_handoff": "Needs handoff",
    "researching": "Researching",
    "contacted": "Contacted",
}

NEW_WINDOW_HOURS = 24
NEEDS_HANDOFF_AGING_HOURS = 48
MAX_LEADS_PER_STAGE = 20

# Demand vs supply thresholds — locked from the Phase 2 design.
MISMATCH_LEAD_FLOOR = 3
MISMATCH_RATIO_GATE = 2.0
TIGHT_RATIO_GATE = 1.25

# Recommendation cap.
DEFAULT_MAX_CARDS = 5


def _stage_for_lead(lead: CustomerLead, *, now: datetime) -> str:
    """Return the stage key for `lead`. Precedence: contacted wins on
    handed_off=True; otherwise high_intent → new → researching →
    needs_handoff. Evaluated in order; first match wins."""
    if lead.handed_off:
        return "contacted"
    if lead.urgency == "immediate":
        return "high_intent"
    if (now - lead.created_at) <= timedelta(hours=NEW_WINDOW_HOURS):
        return "new"
    if lead.urgency == "researching":
        return "researching"
    return "needs_handoff"


def _serialize_lead(lead: CustomerLead) -> dict:
    """Return a compact JSON-serializable dict for one lead. Mirrors the
    shape AdminLeadListSerializer produces for the existing handoff queue
    so frontend can reuse the AdminLead type. Phase 4 extends with
    ``assigned_to`` (or null) so SalesPipeline cards can render an
    advisor-avatar badge in one fetch."""
    advisor = lead.assigned_to
    assigned_to_payload = None
    if advisor is not None:
        assigned_to_payload = {
            "id": advisor.pk,
            "name": advisor.name,
            "slug": advisor.slug,
            "title": advisor.title,
            "photo_url": advisor.photo_url,
        }
    return {
        "id": lead.id,
        "name": lead.name,
        "phone": lead.phone,
        "email": lead.email,
        "urgency": lead.urgency,
        "target_monthly_payment": (
            str(lead.target_monthly_payment)
            if lead.target_monthly_payment is not None
            else None
        ),
        "down_payment": (
            str(lead.down_payment) if lead.down_payment is not None else None
        ),
        "handed_off": lead.handed_off,
        "created_at": lead.created_at.isoformat(),
        "assigned_to": assigned_to_payload,
        "assigned_at": (
            lead.assigned_at.isoformat() if lead.assigned_at else None
        ),
        "interested_vehicles": [
            {
                "id": v.id,
                "stock_number": v.stock_number,
                "display_name": v.display_name,
                "price": str(v.price),
            }
            for v in lead.interested_vehicles.all()
        ],
    }


def _compute_stages(
    now: datetime, *, dealership
) -> tuple[List[dict], Dict[str, List[CustomerLead]]]:
    """Bucket every lead into a stage. Returns (serialized stages list,
    raw model instances grouped by stage). The raw map is reused by the
    recommendation engine so we don't double-query."""
    qs = (
        CustomerLead.objects.filter(dealership=dealership)
        .select_related("assigned_to")
        .prefetch_related("interested_vehicles")
        .order_by("-created_at")
    )
    raw: Dict[str, List[CustomerLead]] = {k: [] for k in STAGE_KEYS}
    for lead in qs:
        raw[_stage_for_lead(lead, now=now)].append(lead)

    stages = [
        {
            "key": key,
            "label": STAGE_LABELS[key],
            "count": len(raw[key]),
            "leads": [_serialize_lead(lead) for lead in raw[key][:MAX_LEADS_PER_STAGE]],
        }
        for key in STAGE_KEYS
    ]
    return stages, raw


# ---- Demand vs supply -------------------------------------------------------


# Fixed payment bands so the panel renders identically across loads.
_DEMAND_BANDS: List[dict] = [
    {"label": "< $300/mo", "monthly_low": 0, "monthly_high": 299},
    {"label": "$300–399/mo", "monthly_low": 300, "monthly_high": 399},
    {"label": "$400–499/mo", "monthly_low": 400, "monthly_high": 499},
    {"label": "$500–599/mo", "monthly_low": 500, "monthly_high": 599},
    {"label": "$600–699/mo", "monthly_low": 600, "monthly_high": 699},
    {"label": "$700–899/mo", "monthly_low": 700, "monthly_high": 899},
    {"label": "$900+/mo", "monthly_low": 900, "monthly_high": None},
]


def _band_price_range(band: dict) -> tuple[int, Optional[int]]:
    """Map a payment band to a sticker-price range using the same math the
    chat path uses. ``down_payment=0`` so the bands stay stable across
    leads (matches the ``down_payment_assumption`` field on the response).
    """
    low_monthly = max(band["monthly_low"], 1)
    price_low = round(affordable_max_price(float(low_monthly)))
    if band["monthly_high"] is None:
        return price_low, None
    price_high = round(affordable_max_price(float(band["monthly_high"])))
    return price_low, price_high


def _band_model_hint(price_low: int, price_high: Optional[int]) -> str:
    """Suggest body-style families to source for a price band.

    Manager-facing acquisition hint on the pipeline dashboard. Kept
    make-agnostic so the same rule works for a Copper Canyon-style
    mixed-lot indie config, a Dealer OS-style franchise config, or
    any other configuration — the manager knows the specific models
    they buy; the hint just tells them WHAT price/segment shape has
    demand outrunning supply.
    """
    if price_high is None:
        return (
            "loaded full-size trucks, three-row luxury SUVs, or "
            "high-trim performance vehicles"
        )
    avg = (price_low + price_high) / 2
    if avg < 20_000:
        return "compact crossovers, subcompact SUVs, or older-year compact trucks"
    if avg < 28_000:
        return "mid-size sedans, small crossovers, or lower-mile compact trucks"
    if avg < 38_000:
        return (
            "mid-size crossovers, mid-size trucks, or lower-mile "
            "compact SUVs"
        )
    if avg < 50_000:
        return "full-size trucks, three-row SUVs, or higher-trim mid-size trucks"
    if avg < 70_000:
        return "full-size trucks, luxury-brand crossovers, or three-row SUVs"
    return (
        "loaded full-size trucks, three-row luxury SUVs, or "
        "high-trim performance vehicles"
    )


def _classify_tier(*, lead_count: int, vehicle_count: int) -> tuple[str, float]:
    """Return ``(tier, ratio)`` per the Phase 2 thresholds."""
    ratio = lead_count / max(vehicle_count, 1)
    if lead_count >= MISMATCH_LEAD_FLOOR and ratio >= MISMATCH_RATIO_GATE:
        return "mismatch", ratio
    if lead_count >= 1 and ratio >= TIGHT_RATIO_GATE:
        return "tight", ratio
    return "healthy", ratio


def _compute_demand_vs_supply(*, dealership) -> dict:
    """Aggregate open-lead targets vs available inventory across the
    fixed payment bands. Bands with zero leads AND zero vehicles are
    omitted from the response to reduce visual noise."""
    open_targets_qs = (
        CustomerLead.objects.filter(dealership=dealership, handed_off=False)
        .exclude(target_monthly_payment__isnull=True)
        .values_list("target_monthly_payment", flat=True)
    )
    targets: List[float] = []
    for raw in open_targets_qs:
        try:
            targets.append(float(raw))
        except (TypeError, ValueError):
            continue

    vehicle_prices: List[float] = []
    for raw in Vehicle.objects.filter(
        dealership=dealership, is_available=True
    ).values_list("price", flat=True):
        try:
            vehicle_prices.append(float(raw))
        except (TypeError, ValueError):
            continue

    buckets: List[dict] = []
    for band in _DEMAND_BANDS:
        if band["monthly_high"] is None:
            lead_count = sum(1 for t in targets if t >= band["monthly_low"])
        else:
            lead_count = sum(
                1
                for t in targets
                if band["monthly_low"] <= t <= band["monthly_high"]
            )

        price_low, price_high = _band_price_range(band)
        if price_high is None:
            vehicle_count = sum(1 for p in vehicle_prices if p >= price_low)
        else:
            vehicle_count = sum(
                1 for p in vehicle_prices if price_low <= p <= price_high
            )

        if lead_count == 0 and vehicle_count == 0:
            continue

        tier, ratio = _classify_tier(
            lead_count=lead_count, vehicle_count=vehicle_count
        )
        suggestion: Optional[str] = None
        if tier == "mismatch":
            hint = _band_model_hint(price_low, price_high)
            range_phrase = (
                f"${price_low:,}–${price_high:,}"
                if price_high is not None
                else f"${price_low:,}+"
            )
            suggestion = (
                f"Consider sourcing {hint} in the {range_phrase} range."
            )

        buckets.append(
            {
                "band_label": band["label"],
                "monthly_low": band["monthly_low"],
                "monthly_high": band["monthly_high"],
                "price_low": price_low,
                "price_high": price_high,
                "lead_count": lead_count,
                "vehicle_count": vehicle_count,
                "ratio": round(ratio, 2),
                "tier": tier,
                "suggestion": suggestion,
            }
        )

    return {
        "down_payment_assumption": 0,
        "buckets": buckets,
    }


# ---- Recommended actions ----------------------------------------------------


_PRIORITY_RANK: Dict[str, int] = {"high": 0, "medium": 1, "low": 2}
_CATEGORY_ORDER: tuple[str, ...] = ("inventory", "sales", "marketing")


def _avg_target_text(leads: List[CustomerLead]) -> Optional[str]:
    targets: List[float] = []
    for lead in leads:
        if lead.target_monthly_payment is None:
            continue
        try:
            targets.append(float(lead.target_monthly_payment))
        except (TypeError, ValueError):
            continue
    if not targets:
        return None
    avg = sum(targets) / len(targets)
    return f"${avg:,.0f}/mo"


def _band_id_suffix(band_label_low: int, band_label_high: Optional[int]) -> str:
    return f"{band_label_low}_{band_label_high if band_label_high is not None else 'plus'}"


def _inventory_cards(buckets: List[dict]) -> List[dict]:
    cards: List[dict] = []
    for b in buckets:
        suffix = _band_id_suffix(b["monthly_low"], b["monthly_high"])
        price_phrase = (
            f"${b['price_low']:,}–${b['price_high']:,}"
            if b["price_high"] is not None
            else f"${b['price_low']:,}+"
        )
        evidence = {
            "band_label": b["band_label"],
            "lead_count": b["lead_count"],
            "vehicle_count": b["vehicle_count"],
            "ratio": b["ratio"],
        }
        cta = {
            "kind": "view_leads_in_band",
            "params": {
                "monthly_low": b["monthly_low"],
                "monthly_high": b["monthly_high"],
            },
        }

        if b["tier"] == "mismatch":
            short = max(b["lead_count"] - b["vehicle_count"], 1)
            short_low = max(short // 2, 1)
            cards.append(
                {
                    "id": f"inventory.mismatch.{suffix}",
                    "category": "inventory",
                    "priority": "high" if b["lead_count"] >= 5 else "medium",
                    "title": f"Source vehicles in the {price_phrase} range",
                    "explanation": (
                        f"{b['lead_count']} open leads target {b['band_label']} "
                        f"but only {b['vehicle_count']} vehicle"
                        f"{'s' if b['vehicle_count'] != 1 else ''} are available "
                        f"in that band — a {b['ratio']}× shortfall."
                    ),
                    "action_text": (
                        f"Acquire {short_low}–{short} unit"
                        f"{'s' if short != 1 else ''} priced {price_phrase}. "
                        + (b["suggestion"] or "")
                    ).strip(),
                    "evidence": evidence,
                    "cta": cta,
                }
            )
        elif b["tier"] == "tight" and b["lead_count"] >= 5:
            cards.append(
                {
                    "id": f"inventory.tight.{suffix}",
                    "category": "inventory",
                    "priority": "medium",
                    "title": f"Tight inventory in the {price_phrase} range",
                    "explanation": (
                        f"{b['lead_count']} open leads vs {b['vehicle_count']} "
                        f"vehicles in {b['band_label']} — keeping up but margin "
                        "is thin."
                    ),
                    "action_text": (
                        f"Add 1–3 units priced {price_phrase} before the gap widens."
                    ),
                    "evidence": evidence,
                    "cta": cta,
                }
            )
        elif b["tier"] == "tight":
            cards.append(
                {
                    "id": f"inventory.watch.{suffix}",
                    "category": "inventory",
                    "priority": "low",
                    "title": f"Watch supply in {b['band_label']}",
                    "explanation": (
                        f"{b['lead_count']} open lead"
                        f"{'s' if b['lead_count'] != 1 else ''} vs "
                        f"{b['vehicle_count']} vehicle"
                        f"{'s' if b['vehicle_count'] != 1 else ''}. Supply is "
                        "keeping up but margin is thin."
                    ),
                    "action_text": (
                        "Watch this band — re-evaluate at the next sourcing review."
                    ),
                    "evidence": evidence,
                    "cta": None,
                }
            )
    return cards


def _sales_cards(
    *,
    stages: List[dict],
    leads_by_stage: Dict[str, List[CustomerLead]],
    now: datetime,
) -> List[dict]:
    cards: List[dict] = []
    high_intent_count = next(
        (s["count"] for s in stages if s["key"] == "high_intent"), 0
    )
    new_count = next((s["count"] for s in stages if s["key"] == "new"), 0)

    high_intent_leads = leads_by_stage.get("high_intent", [])
    needs_handoff_leads = leads_by_stage.get("needs_handoff", [])

    if high_intent_count >= 3:
        avg = _avg_target_text(high_intent_leads)
        explanation = (
            f"{high_intent_count} leads are flagged urgency=immediate and "
            "not yet handed off."
        )
        if avg:
            explanation += f" Average target {avg}."
        cards.append(
            {
                "id": "sales.high_intent_assign",
                "category": "sales",
                "priority": "high",
                "title": (
                    f"{high_intent_count} buying-now leads need an advisor today"
                ),
                "explanation": explanation,
                "action_text": (
                    "Assign each lead in the High Intent column to an advisor "
                    "before end of shift."
                ),
                "evidence": {
                    "high_intent_count": high_intent_count,
                    "avg_target_monthly_payment": avg,
                },
                "cta": {"kind": "view_high_intent_leads"},
            }
        )
    elif high_intent_count >= 1:
        plural = "s" if high_intent_count > 1 else ""
        cards.append(
            {
                "id": "sales.high_intent_clear",
                "category": "sales",
                "priority": "medium",
                "title": f"{high_intent_count} buying-now lead{plural} waiting",
                "explanation": (
                    f"{high_intent_count} lead{plural} flagged urgency=immediate "
                    "awaiting handoff."
                ),
                "action_text": (
                    "Hand off the High Intent column before the day ends."
                ),
                "evidence": {"high_intent_count": high_intent_count},
                "cta": {"kind": "view_high_intent_leads"},
            }
        )

    if new_count >= 5:
        cards.append(
            {
                "id": "sales.new_triage",
                "category": "sales",
                "priority": "medium",
                "title": f"{new_count} new leads in the last 24h",
                "explanation": (
                    "Triage the New column — call or text the unflagged "
                    "ones first."
                ),
                "action_text": (
                    "Open the New column and route each lead to an advisor "
                    "or follow-up queue."
                ),
                "evidence": {"new_count": new_count},
                "cta": {"kind": "view_aging_leads"},
            }
        )

    aging_threshold = now - timedelta(hours=NEEDS_HANDOFF_AGING_HOURS)
    aging_count = sum(
        1 for lead in needs_handoff_leads if lead.created_at <= aging_threshold
    )
    if aging_count > 0:
        plural = "s" if aging_count > 1 else ""
        cards.append(
            {
                "id": "sales.aging_needs_handoff",
                "category": "sales",
                "priority": "medium",
                "title": f"{aging_count} lead{plural} aging in Needs Handoff",
                "explanation": (
                    f"{aging_count} lead{plural} in the Needs Handoff column "
                    f"are >{NEEDS_HANDOFF_AGING_HOURS}h old and still uncontacted."
                ),
                "action_text": "Sweep these before tomorrow's open.",
                "evidence": {
                    "aging_count": aging_count,
                    "threshold_hours": NEEDS_HANDOFF_AGING_HOURS,
                },
                "cta": None,
            }
        )

    # Per-lead "buying-now without flagged vehicles" — only emit when no
    # higher-priority sales card is already on the list.
    has_higher_priority_sales = any(
        c["category"] == "sales" and c["priority"] in ("high", "medium")
        for c in cards
    )
    if not has_higher_priority_sales:
        unflagged = [
            lead
            for lead in high_intent_leads
            if not list(lead.interested_vehicles.all())
        ]
        if unflagged:
            lead = unflagged[0]
            cards.append(
                {
                    "id": f"sales.high_intent_no_vehicles.{lead.id}",
                    "category": "sales",
                    "priority": "low",
                    "title": (
                        f"{lead.name} is buying-now but has no vehicles flagged"
                    ),
                    "explanation": (
                        f"{lead.name} is in High Intent with no "
                        "interested_vehicles. Pull recommendations during "
                        "the call."
                    ),
                    "action_text": (
                        f"Open lead #{lead.id} and surface inventory matching "
                        "their target."
                    ),
                    "evidence": {"lead_id": lead.id, "lead_name": lead.name},
                    "cta": {"kind": "view_high_intent_leads"},
                }
            )

    return cards


def _marketing_cards(
    *,
    inventory_cards: List[dict],
    trends: dict,
    dealership,
) -> List[dict]:
    cards: List[dict] = []
    has_inventory_high = any(
        c["category"] == "inventory" and c["priority"] == "high"
        for c in inventory_cards
    )

    top_models = trends.get("top_requested_models") or []
    if top_models and not has_inventory_high:
        top = top_models[0]
        # Suppress when this model has zero stock or fewer than 2 sessions
        # (signal too weak).
        vehicle_count_for_model = (
            Vehicle.objects.filter(
                dealership=dealership,
                is_available=True,
                model__icontains=top["value"],
            ).count()
        )
        if vehicle_count_for_model >= 2 and top["count"] >= 2:
            slug = top["value"].lower().replace(" ", "_").replace("-", "_")
            cards.append(
                {
                    "id": f"marketing.promote_model.{slug}",
                    "category": "marketing",
                    "priority": "medium",
                    "title": (
                        f"Promote {top['value']} — {top['count']} customer"
                        f"{'s' if top['count'] != 1 else ''} asked, lot has stock"
                    ),
                    "explanation": (
                        f"{top['value']} is the most-requested model "
                        f"({top['count']} session"
                        f"{'s' if top['count'] != 1 else ''}). "
                        f"{vehicle_count_for_model} unit"
                        f"{'s' if vehicle_count_for_model != 1 else ''} in inventory."
                    ),
                    "action_text": (
                        f"Run a {top['value']} promotion this week — feature "
                        "the units in current inventory across pricing bands."
                    ),
                    "evidence": {
                        "model": top["value"],
                        "session_count": top["count"],
                        "available_inventory": vehicle_count_for_model,
                    },
                    "cta": None,
                }
            )

    top_types = trends.get("top_requested_vehicle_types") or []
    if top_types and top_types[0]["count"] >= 3 and not cards:
        top = top_types[0]
        cards.append(
            {
                "id": f"marketing.promote_type.{top['value']}",
                "category": "marketing",
                "priority": "medium",
                "title": (
                    f"{top['value'].title()} demand is steady — push the category"
                ),
                "explanation": (
                    f"{top['count']} sessions interested in {top['value']}. "
                    "Targeted social/email could convert."
                ),
                "action_text": (
                    f"Targeted social/email for {top['value']} shoppers."
                ),
                "evidence": {
                    "vehicle_type": top["value"],
                    "session_count": top["count"],
                },
                "cta": None,
            }
        )

    most_selected = trends.get("most_selected_vehicles") or []
    for v in most_selected:
        if v.get("lead_count", 0) >= 3:
            cards.append(
                {
                    "id": f"marketing.highlight.{v['stock_number']}",
                    "category": "marketing",
                    "priority": "low",
                    "title": f"Highlight {v['display_name']} in collateral",
                    "explanation": (
                        f"This unit is on {v['lead_count']} leads — feature "
                        "it in the next email blast or showroom highlight."
                    ),
                    "action_text": (
                        f"Feature stock #{v['stock_number']} in next promotion."
                    ),
                    "evidence": {
                        "stock_number": v["stock_number"],
                        "display_name": v["display_name"],
                        "lead_count": v["lead_count"],
                    },
                    "cta": None,
                }
            )
            break  # cap at one highlight per refresh
    return cards


def _rank_and_cap(cards: List[dict], *, max_cards: int) -> List[dict]:
    """Sort by priority then category-interleave within each priority tier.
    Stable on identical input — same ids in the same order across calls."""
    if not cards:
        return cards

    cards.sort(
        key=lambda c: (
            _PRIORITY_RANK.get(c["priority"], 99),
            _CATEGORY_ORDER.index(c["category"])
            if c["category"] in _CATEGORY_ORDER
            else 99,
            c["id"],
        )
    )

    by_priority: Dict[str, List[dict]] = defaultdict(list)
    for c in cards:
        by_priority[c["priority"]].append(c)

    output: List[dict] = []
    for prio in ("high", "medium", "low"):
        if not by_priority[prio]:
            continue
        by_cat: Dict[str, List[dict]] = defaultdict(list)
        for c in by_priority[prio]:
            by_cat[c["category"]].append(c)
        # Round-robin across categories within this priority tier.
        while any(by_cat[cat] for cat in _CATEGORY_ORDER):
            for cat in _CATEGORY_ORDER:
                if by_cat[cat]:
                    output.append(by_cat[cat].pop(0))
                    if len(output) >= max_cards:
                        return output
    return output[:max_cards]


def recommended_actions(
    *,
    stages: List[dict],
    demand_buckets: List[dict],
    trends: dict,
    leads_by_stage: Dict[str, List[CustomerLead]],
    now: Optional[datetime] = None,
    max_cards: int = DEFAULT_MAX_CARDS,
    dealership=None,
) -> List[dict]:
    """Pure function. Returns up to ``max_cards`` recommendations ordered by
    priority then category interleave. Inputs are exactly the data the
    pipeline endpoint already collects — no DB queries from this function
    other than the marketing card's per-model inventory lookup, which is a
    single ``Vehicle.objects.filter().count()`` scoped to ``dealership``.
    ``dealership=None`` resolves to the seeded default."""
    from .tenancy import get_default_dealership

    d = dealership or get_default_dealership()
    now = now or timezone.now()

    inventory = _inventory_cards(demand_buckets)
    sales = _sales_cards(stages=stages, leads_by_stage=leads_by_stage, now=now)
    marketing = _marketing_cards(
        inventory_cards=inventory, trends=trends, dealership=d
    )

    return _rank_and_cap(inventory + sales + marketing, max_cards=max_cards)


def _trends_for_recommendations(*, dealership) -> dict:
    """Subset of trends_snapshot the recommendation engine uses. Pulled in
    one place so tests can inject a stub without touching trends.py."""
    return {
        "top_requested_models": top_requested_models(dealership=dealership),
        "top_requested_vehicle_types": top_requested_vehicle_types(
            dealership=dealership
        ),
        "most_selected_vehicles": most_selected_vehicles(dealership=dealership),
    }


# ---- Public entry -----------------------------------------------------------


def pipeline_snapshot(*, dealership=None) -> Dict[str, Any]:
    """One-shot aggregate used by ``GET /admin/pipeline/``.

    Milestone 1 · Increment 4D — tenant-scoped. ``dealership=None``
    resolves to the seeded default (backwards compat for tests
    predating multi-tenancy); the admin view passes
    ``dealership=get_current_dealership(request)`` so isolation is
    explicit at the call site. Recommendations built by
    :func:`recommended_actions` do not query models directly — the
    marketing card's inventory lookup goes through
    :func:`_marketing_cards`, which now takes ``dealership`` too.
    """
    from .tenancy import get_default_dealership

    d = dealership or get_default_dealership()
    now = timezone.now()
    stages, leads_by_stage = _compute_stages(now, dealership=d)
    demand = _compute_demand_vs_supply(dealership=d)
    trends = _trends_for_recommendations(dealership=d)
    actions = recommended_actions(
        stages=stages,
        demand_buckets=demand["buckets"],
        trends=trends,
        leads_by_stage=leads_by_stage,
        now=now,
        dealership=d,
    )
    return {
        "generated_at": now.isoformat(),
        "stages": stages,
        "demand_vs_supply": demand,
        "recommended_actions": actions,
    }
