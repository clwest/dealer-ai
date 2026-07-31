"""Vehicle-specific AI helper.

Used by the GET /vehicles/<id>/ and POST /vehicles/<id>/ask/ endpoints.
Two public entry points:

- analyze_vehicle(vehicle, *, profile=None) → structured detail payload
  (payment estimates at 60/72/84mo, affordability notes, similar vehicles).

- answer_vehicle_question(vehicle, question, *, profile=None, provider=None,
  session=None) → natural-language reply with low-pressure dealership tone.
  Optionally writes the Q/A pair into a ChatSession transcript.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from ..models import ChatMessage, ChatSession, Vehicle
from .chat_engine import (
    EXTERNAL_VALUE_RESPONSE,
    GUARD_RESPONSE,
    HANDOFF_RESPONSE,
    IDENTITY_RESPONSE,
    NEGOTIATION_RESPONSE,
    RATE_INQUIRY_RESPONSE,
    build_negotiation_response,
    detect_external_value_inquiry,
    detect_handoff_request,
    detect_identity_request,
    detect_negotiation_request,
    detect_rate_inquiry,
    detect_unsafe_request,
)
from .dealer_config import get_dealer_name
from .llm.base import LLMProvider
from .llm.factory import get_llm_provider
from .llm_safety import apply_post_llm_scrubs
from .payment_engine import (
    DEFAULT_TERM_MONTHS,
    affordable_max_price,
    estimate_payment,
)

logger = logging.getLogger(__name__)


def _render(template: str) -> str:
    """Format a dealer-templated string with the current dealer name.

    Mirrors the ``chat_engine._render`` helper — prompt and response
    constants use ``{dealer_name}`` as a placeholder that resolves at
    call time via :func:`dealer_config.get_dealer_name`.
    """
    return template.format(dealer_name=get_dealer_name())


PAYMENT_TERMS = (60, 72, 84)
SIMILAR_LIMIT = 4
PRICE_BAND = 0.20  # ±20% — what counts as a comparable alternative


VEHICLE_ASSISTANT_PROMPT = """You are the AI concierge for {dealer_name} answering a question about ONE specific vehicle.

Your job:
- Answer plainly and helpfully, using only the facts in the VEHICLE block, the SIMILAR INVENTORY block, and PAYMENT MATH.
- Never invent specs, financing offers, rebates, or warranty details that aren't shown.
- If the customer asks about towing, capability, or features the listing doesn't confirm, say so honestly and suggest how a sales advisor can verify.
- When payments come up, label them as ESTIMATES with the W.A.C. (with approved credit) qualifier and the term length. Never state a specific interest rate, APR, or financing percentage. If asked, say "rates vary based on credit and lender approval — final terms are confirmed by the dealership".
- Tone: friendly, low-pressure, dealership professional. 2-4 short sentences unless asked for more detail.
- If the customer compares to another vehicle in SIMILAR INVENTORY, use those facts; if they ask about a vehicle not listed, say it's not in the current set and offer to look it up.
- End with a soft next step (test drive, advisor call) only when it fits the answer.
"""


@dataclass
class VehicleAnalysis:
    vehicle: Vehicle
    payment_estimates: List[Dict[str, Any]]
    affordability_notes: List[str]
    similar_vehicles: List[Vehicle]

    def to_payload(self) -> Dict[str, Any]:
        return {
            "vehicle_id": self.vehicle.id,
            "payment_estimates": self.payment_estimates,
            "affordability_notes": self.affordability_notes,
            "similar_vehicle_ids": [v.id for v in self.similar_vehicles],
        }


# ---- Public API -------------------------------------------------------------


def analyze_vehicle(
    vehicle: Vehicle,
    *,
    profile: Optional[Dict[str, Any]] = None,
) -> VehicleAnalysis:
    profile = profile or {}
    target_monthly = _coerce_float(profile.get("target_monthly_payment"))
    down_payment = _coerce_float(profile.get("down_payment")) or 0.0

    payment_estimates = _payment_estimates(
        vehicle.price, down_payment=down_payment
    )
    notes = _affordability_notes(
        vehicle=vehicle,
        target_monthly=target_monthly,
        down_payment=down_payment,
    )
    similar = list(_similar_vehicles(vehicle))

    return VehicleAnalysis(
        vehicle=vehicle,
        payment_estimates=payment_estimates,
        affordability_notes=notes,
        similar_vehicles=similar,
    )


def _check_pre_llm_guards(
    question: str,
    *,
    session: Optional[ChatSession] = None,
    vehicle: Optional[Vehicle] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Run the same pre-LLM guard chain the chat path uses, in the same
    priority order. Returns (canned_reply, flag) when any guard fires,
    or (None, None) when the question is clean.

    Order: unsafe-request → rate-inquiry → external-value → identity →
    negotiation → handoff. (Image / appointment guards are chat-only —
    the per-vehicle path already has the vehicle in context, so those
    flows route through the regular LLM call.)

    Phase 8p: the negotiation guard uses ``build_negotiation_response``
    so its reply is context-aware. When called from the per-vehicle
    endpoint, the focus vehicle is implicit and we pin it as
    ``current_vehicle_*`` for the helper so the response references
    "the {year} Ford {model}" by name.
    """
    if not question:
        return None, None
    if detect_unsafe_request(question):
        return GUARD_RESPONSE, "prompt_injection"
    if detect_rate_inquiry(question):
        return RATE_INQUIRY_RESPONSE, "rate_inquiry"
    if detect_external_value_inquiry(question):
        return _render(EXTERNAL_VALUE_RESPONSE), "external_value_inquiry"
    if detect_identity_request(question):
        return _render(IDENTITY_RESPONSE), "identity_request"
    if detect_negotiation_request(question):
        # Build a context-aware reply. When the per-vehicle endpoint
        # supplies a vehicle, treat it as the current focus.
        profile: Optional[Dict[str, Any]] = None
        if vehicle is not None:
            profile = (
                dict(session.extracted_profile or {})
                if session is not None
                else {}
            )
            profile["current_vehicle_id"] = vehicle.id
            profile["current_vehicle_stock"] = vehicle.stock_number
        return (
            build_negotiation_response(session, profile=profile),
            "negotiation_request",
        )
    if detect_handoff_request(question):
        return _render(HANDOFF_RESPONSE), "handoff_request"
    return None, None


def answer_vehicle_question(
    vehicle: Vehicle,
    question: str,
    *,
    profile: Optional[Dict[str, Any]] = None,
    provider: Optional[LLMProvider] = None,
    session: Optional[ChatSession] = None,
) -> str:
    """Run the vehicle-specific LLM call. Logs Q/A to the session if given.

    Phase 8o+: applies the same pre-LLM guards as the chat path so the
    per-vehicle endpoint can't bypass safety / negotiation / handoff /
    identity / rate / external-value checks. If any guard fires, returns
    the canned response without invoking the LLM and tags the session
    transcript so dashboards see the audit flag.
    """
    question = (question or "").strip()
    if not question:
        return "What would you like to know about this vehicle?"

    # Pre-LLM guard chain — mirror of handle_user_message order.
    guard_reply, guard_flag = _check_pre_llm_guards(
        question, session=session, vehicle=vehicle
    )
    if guard_reply is not None:
        if session is not None:
            ChatMessage.objects.create(
                session=session,
                role="user",
                content=question,
                metadata={
                    "vehicle_id": vehicle.id,
                    "kind": "vehicle_ask",
                    "flag": guard_flag if guard_flag == "prompt_injection" else None,
                },
            )
            msg = ChatMessage.objects.create(
                session=session,
                role="assistant",
                content=guard_reply,
                metadata={
                    "vehicle_id": vehicle.id,
                    "kind": "vehicle_ask",
                    "provider": "guard",
                    "flag": guard_flag,
                },
            )
            # Attach the vehicle the customer was asking about, just like
            # the chat-engine guards would.
            msg.matched_vehicles.add(vehicle)
        return guard_reply

    provider = provider or get_llm_provider()
    analysis = analyze_vehicle(vehicle, profile=profile)

    messages = [
        {"role": "system", "content": _render(VEHICLE_ASSISTANT_PROMPT)},
        {"role": "system", "content": _vehicle_block(vehicle)},
        {
            "role": "system",
            "content": _similar_block(analysis.similar_vehicles, anchor=vehicle),
        },
        {
            "role": "system",
            "content": _payment_math_block(analysis, profile=profile or {}),
        },
        {"role": "user", "content": question},
    ]

    try:
        reply = provider.chat(messages, temperature=0.4, max_tokens=400)
    except Exception as exc:  # noqa: BLE001
        logger.warning("vehicle_assistant LLM call failed: %s", exc)
        reply = ""

    reply = (reply or "").strip()
    if not reply:
        reply = (
            f"I can pull up most details on this {vehicle.display_name}, but I "
            f"want to double-check before I answer that — an advisor from "
            f"{get_dealer_name()} can confirm in a minute. Want me to flag the "
            "question for them?"
        )

    # Phase 4 — close PIPELINE.md §6.1: per-vehicle replies now run through
    # the shared post-LLM safety stack. Wholesale-rewrite classes (dealer
    # cost / negotiation) substitute the canned chat-side guard reply so
    # nothing forbidden ever reaches the customer; partial scrubs strip
    # rate / directive / default-assumption phrasings inline.
    cleaned_reply, scrubs_fired, dropped_reason = apply_post_llm_scrubs(
        reply, kind="vehicle_ask"
    )
    safety_flag: Optional[str] = None
    if dropped_reason == "dealer_cost_safety":
        logger.warning(
            "vehicle_assistant post-LLM safety: rewriting reply (vehicle=%s)",
            vehicle.stock_number,
        )
        reply = GUARD_RESPONSE
        safety_flag = "post_llm_safety_rewrite"
    elif dropped_reason and dropped_reason.startswith("post_llm_override:"):
        kind = dropped_reason.split(":", 1)[1]
        logger.warning(
            "vehicle_assistant post-LLM override: rewriting reply (vehicle=%s, kind=%s)",
            vehicle.stock_number,
            kind,
        )
        reply = _render(
            NEGOTIATION_RESPONSE if kind == "negotiation" else HANDOFF_RESPONSE
        )
        safety_flag = "post_llm_override"
    else:
        reply = cleaned_reply.strip() or reply

    if session is not None:
        ChatMessage.objects.create(
            session=session,
            role="user",
            content=question,
            metadata={"vehicle_id": vehicle.id, "kind": "vehicle_ask"},
        )
        assistant_metadata = {
            "vehicle_id": vehicle.id,
            "kind": "vehicle_ask",
            "provider": provider.name,
        }
        if scrubs_fired:
            assistant_metadata["scrubs"] = scrubs_fired
        if safety_flag is not None:
            assistant_metadata["flag"] = safety_flag
        msg = ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=reply,
            metadata=assistant_metadata,
        )
        msg.matched_vehicles.add(vehicle)

    return reply


# ---- Internals --------------------------------------------------------------


def _coerce_float(value) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _payment_estimates(
    price: Decimal | float, *, down_payment: float = 0.0
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for term in PAYMENT_TERMS:
        est = estimate_payment(price, down_payment=down_payment, term_months=term)
        d = est.to_dict()
        d["term_months"] = term
        out.append(d)
    return out


def _affordability_notes(
    *,
    vehicle: Vehicle,
    target_monthly: Optional[float],
    down_payment: float,
) -> List[str]:
    notes: List[str] = []

    base_no_down = estimate_payment(vehicle.price, down_payment=0)
    notes.append(
        f"Over {DEFAULT_TERM_MONTHS} months with no down payment, the estimated "
        f"payment is around ${base_no_down.monthly_payment:,.0f}/mo "
        "(W.A.C. — with approved credit)."
    )

    if down_payment >= 1000:
        with_down = estimate_payment(vehicle.price, down_payment=down_payment)
        diff = base_no_down.monthly_payment - with_down.monthly_payment
        if diff > 0:
            notes.append(
                f"Putting ${down_payment:,.0f} down drops the {DEFAULT_TERM_MONTHS}-month "
                f"estimate to about ${with_down.monthly_payment:,.0f}/mo — roughly "
                f"${diff:,.0f}/mo less."
            )

    short = estimate_payment(vehicle.price, down_payment=down_payment, term_months=60)
    long_ = estimate_payment(vehicle.price, down_payment=down_payment, term_months=84)
    if short.monthly_payment > long_.monthly_payment:
        savings_per_mo = short.monthly_payment - long_.monthly_payment
        notes.append(
            f"Stretching from 60 to 84 months trims around ${savings_per_mo:,.0f}/mo, "
            "but increases total cost over the life of the loan — sales can sketch "
            "the trade-off."
        )

    if target_monthly:
        max_price = affordable_max_price(target_monthly, down_payment=down_payment)
        price_f = float(vehicle.price)
        if price_f <= max_price:
            notes.append(
                f"Good news — at ${target_monthly:,.0f}/mo with ${down_payment:,.0f} "
                "down, this vehicle fits within a realistic budget for that target."
            )
        elif price_f <= max_price * 1.25:
            notes.append(
                f"This vehicle is a stretch at ${target_monthly:,.0f}/mo with "
                f"${down_payment:,.0f} down — close to the ceiling for that target. "
                "A bit more down or a longer term can bridge the gap."
            )
        else:
            notes.append(
                f"At ${target_monthly:,.0f}/mo with ${down_payment:,.0f} down, this "
                f"price is meaningfully above a realistic target — the closest fit "
                f"is around ${max_price:,.0f}. Sales can show alternatives."
            )

    return notes


def _similar_vehicles(vehicle: Vehicle) -> Iterable[Vehicle]:
    price = float(vehicle.price)
    low = price * (1 - PRICE_BAND)
    high = price * (1 + PRICE_BAND)

    primary = (
        Vehicle.objects.filter(is_available=True)
        .exclude(id=vehicle.id)
        .filter(body_style=vehicle.body_style)
        .filter(price__gte=Decimal(str(low)), price__lte=Decimal(str(high)))
        .order_by("-year", "price")[:SIMILAR_LIMIT]
    )
    primary_list = list(primary)
    if len(primary_list) >= SIMILAR_LIMIT:
        return primary_list

    # Loosen if we don't have enough — include any body style in the price band.
    fill = (
        Vehicle.objects.filter(is_available=True)
        .exclude(id=vehicle.id)
        .exclude(id__in=[v.id for v in primary_list])
        .filter(price__gte=Decimal(str(low * 0.85)), price__lte=Decimal(str(high * 1.15)))
        .order_by("-year", "price")[: SIMILAR_LIMIT - len(primary_list)]
    )
    return primary_list + list(fill)


def _vehicle_block(v: Vehicle) -> str:
    feature_str = ", ".join(map(str, (v.features or [])[:8]))
    lines = [
        "VEHICLE (this is the customer's focus):",
        f"- {v.display_name} | Stock #{v.stock_number}",
        f"- Condition: {v.get_condition_display()} | Body style: {v.get_body_style_display()}",
        f"- Price: ${v.price:,.0f}",
    ]
    if v.msrp and Decimal(v.msrp) > Decimal(v.price):
        lines.append(f"- MSRP: ${v.msrp:,.0f}")
    if v.mileage is not None:
        lines.append(f"- Mileage: {v.mileage:,} mi")
    if v.engine:
        lines.append(f"- Engine: {v.engine}")
    if v.drivetrain:
        lines.append(f"- Drivetrain: {v.drivetrain}")
    if v.transmission:
        lines.append(f"- Transmission: {v.transmission}")
    if v.fuel_type:
        lines.append(f"- Fuel: {v.fuel_type}")
    if v.exterior_color or v.interior_color:
        lines.append(
            f"- Color: {v.exterior_color or '—'} ext / "
            f"{v.interior_color or '—'} int"
        )
    if feature_str:
        lines.append(f"- Notable features: {feature_str}")
    if v.description:
        lines.append(f"- Listing notes: {v.description}")
    return "\n".join(lines)


def _similar_block(similar: List[Vehicle], *, anchor: Vehicle) -> str:
    if not similar:
        return "SIMILAR INVENTORY: (no comparable vehicles in the same price band right now)."
    lines = ["SIMILAR INVENTORY (use only these for cross-comparisons):"]
    for v in similar:
        diff = float(v.price) - float(anchor.price)
        delta = (
            f"+${diff:,.0f}" if diff >= 0 else f"-${abs(diff):,.0f}"
        )
        lines.append(
            f"- {v.display_name} | Stock #{v.stock_number} | "
            f"{v.get_condition_display()} | "
            f"${v.price:,.0f} ({delta} vs anchor) | "
            f"{v.mileage:,} mi"
        )
    return "\n".join(lines)


def _payment_math_block(
    analysis: VehicleAnalysis,
    *,
    profile: Dict[str, Any],
) -> str:
    lines = [
        "PAYMENT MATH (estimates only — quote with the W.A.C. qualifier; "
        "do NOT state any specific interest rate or APR percentage; sales "
        "confirms real terms):"
    ]
    for est in analysis.payment_estimates:
        lines.append(
            f"- {est['term_months']} months: "
            f"~${est['monthly_payment']:,.0f}/mo "
            f"({'$' + format(est['down_payment'], ',.0f')} down) "
            "(W.A.C. — with approved credit)"
        )

    target_monthly = _coerce_float(profile.get("target_monthly_payment"))
    down_payment = _coerce_float(profile.get("down_payment")) or 0.0
    if target_monthly:
        ceiling = affordable_max_price(target_monthly, down_payment=down_payment)
        lines.append(
            f"\nCustomer target: ${target_monthly:,.0f}/mo with ${down_payment:,.0f} "
            f"down → realistic max sticker ≈ ${ceiling:,.0f}."
        )

    if analysis.affordability_notes:
        lines.append("")
        lines.append("Coach notes for the assistant:")
        for note in analysis.affordability_notes:
            lines.append(f"- {note}")
    return "\n".join(lines)
