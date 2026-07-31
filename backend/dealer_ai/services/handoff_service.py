"""Sales handoff packet builder.

Produces a copy-pasteable structured packet for a salesperson, plus a short
suggested message they can send to the customer. No real email/SMS yet —
delivery is the salesperson's responsibility for MVP.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.utils import timezone

from ..models import CustomerLead
from .dealer_config import get_dealer_name
from .llm.base import LLMProvider
from .llm.factory import get_llm_provider

logger = logging.getLogger(__name__)


def _render(template: str) -> str:
    """Format a dealer-templated string with the current dealer name.

    Prompt / signature constants use ``{dealer_name}`` as a placeholder
    resolved at call time via :func:`dealer_config.get_dealer_name`.
    """
    return template.format(dealer_name=get_dealer_name())


SUGGESTED_MESSAGE_PROMPT = """You are drafting a short, friendly first message from a salesperson at {dealer_name} to a customer who just asked the AI concierge for help.

Write 3-5 sentences. Cover:
- A warm, no-pressure hello using the customer's first name.
- Mention the vehicle(s) they showed interest in (if any).
- One concrete next step (test drive, quick call, or quote).
- Acknowledge their budget/timing only if it's clearly stated — never invent numbers.

Style:
- Friendly, professional, dealership-appropriate. Plain English.
- No emojis. No exclamation overload (one max).
- Don't quote financing terms. Don't promise approval or rebates.
- Sign off as "{dealer_name}".
"""


def build_handoff_packet(
    lead: CustomerLead,
    *,
    provider: Optional[LLMProvider] = None,
) -> Dict[str, Any]:
    """Assemble the full handoff packet for one lead."""
    interested = list(lead.interested_vehicles.all())
    suggested_message = _generate_suggested_message(
        lead, interested, provider=provider
    )

    return {
        "lead_id": lead.id,
        "generated_at": timezone.now().isoformat(),
        "customer": {
            "name": lead.name,
            "phone": lead.phone,
            "email": lead.email,
        },
        "interested_vehicles": [
            {
                "id": v.id,
                "stock_number": v.stock_number,
                "display_name": v.display_name,
                "price": str(v.price),
                "url": v.url,
            }
            for v in interested
        ],
        "budget": {
            "target_monthly_payment": _format_decimal(lead.target_monthly_payment),
            "down_payment": _format_decimal(lead.down_payment),
        },
        "trade_in": lead.trade_in or "",
        "credit_range": lead.credit_range or "",
        "urgency": lead.urgency or "",
        "urgency_label": lead.get_urgency_display() if lead.urgency else "",
        "conversation_summary": lead.conversation_summary or "",
        "recommended_next_action": lead.recommended_next_action or "",
        "suggested_message": suggested_message,
        "session_id": str(lead.session_id) if lead.session_id else None,
    }


def packet_to_text(packet: Dict[str, Any]) -> str:
    """Plain-text form of the packet — handy for clipboard / email body."""
    lines: List[str] = []
    customer = packet.get("customer", {}) or {}
    lines.append(f"Lead: {customer.get('name', '—')}")
    contact_bits = [customer.get("phone"), customer.get("email")]
    contact = " · ".join(b for b in contact_bits if b)
    if contact:
        lines.append(f"Contact: {contact}")
    if packet.get("urgency_label"):
        lines.append(f"Urgency: {packet['urgency_label']}")

    budget = packet.get("budget") or {}
    budget_bits: List[str] = []
    if budget.get("target_monthly_payment"):
        budget_bits.append(f"~${budget['target_monthly_payment']}/mo target")
    if budget.get("down_payment"):
        budget_bits.append(f"${budget['down_payment']} down")
    if budget_bits:
        lines.append("Budget: " + ", ".join(budget_bits))

    if packet.get("trade_in"):
        lines.append(f"Trade-in: {packet['trade_in']}")
    if packet.get("credit_range"):
        lines.append(f"Credit: {packet['credit_range']}")

    vehicles = packet.get("interested_vehicles") or []
    if vehicles:
        lines.append("")
        lines.append("Vehicles of interest:")
        for v in vehicles:
            lines.append(
                f"- {v['display_name']} (Stock #{v['stock_number']}, ${v['price']})"
            )

    if packet.get("conversation_summary"):
        lines.append("")
        lines.append("Summary:")
        lines.append(packet["conversation_summary"])

    if packet.get("recommended_next_action"):
        lines.append("")
        lines.append("Recommended next action:")
        lines.append(packet["recommended_next_action"])

    if packet.get("suggested_message"):
        lines.append("")
        lines.append("Suggested first message:")
        lines.append(packet["suggested_message"])

    return "\n".join(lines)


# ---- Internals --------------------------------------------------------------


def _format_decimal(value) -> Optional[str]:
    if value is None:
        return None
    try:
        return f"{Decimal(value):.2f}"
    except (TypeError, ValueError):
        return None


def _first_name(full: str) -> str:
    full = (full or "").strip()
    if not full:
        return "there"
    return full.split()[0]


def _generate_suggested_message(
    lead: CustomerLead,
    interested: List,
    *,
    provider: Optional[LLMProvider] = None,
) -> str:
    provider = provider or get_llm_provider()

    vehicle_lines = [
        f"- {v.display_name} (Stock #{v.stock_number}, ${v.price:,.0f})"
        for v in interested
    ] or ["- (none flagged yet)"]

    profile_lines: List[str] = []
    if lead.target_monthly_payment:
        profile_lines.append(f"target ~${lead.target_monthly_payment}/mo")
    if lead.down_payment:
        profile_lines.append(f"${lead.down_payment} down")
    if lead.trade_in:
        profile_lines.append(f"trade-in: {lead.trade_in}")
    if lead.urgency:
        profile_lines.append(f"timing: {lead.get_urgency_display()}")

    user_payload = (
        f"Customer name: {lead.name}\n"
        f"Vehicles of interest:\n" + "\n".join(vehicle_lines) + "\n"
        f"Profile signals: {', '.join(profile_lines) or '(none)'}\n"
        f"Conversation summary: {lead.conversation_summary or '(no summary)'}\n\n"
        "Write the message now."
    )

    try:
        text = provider.chat(
            [
                {"role": "system", "content": _render(SUGGESTED_MESSAGE_PROMPT)},
                {"role": "user", "content": user_payload},
            ],
            temperature=0.4,
            max_tokens=300,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("handoff suggested_message LLM call failed: %s", exc)
        text = ""

    text = (text or "").strip()
    if text:
        return text

    # Deterministic fallback so handoffs never block on LLM availability.
    pieces: List[str] = [
        f"Hi {_first_name(lead.name)},",
        f"Thanks for reaching out to {get_dealer_name()} — I saw the notes from our AI concierge.",
    ]
    if interested:
        names = ", ".join(v.display_name for v in interested[:2])
        pieces.append(
            f"You showed interest in the {names}; I'd love to help you take a closer look."
        )
    if lead.urgency == "immediate":
        pieces.append("If you're free today, I can line up a same-day test drive.")
    elif lead.urgency == "this_week":
        pieces.append("Is there a day this week that works for a quick test drive?")
    else:
        pieces.append(
            "Whenever you're ready, I can pull together a real quote and "
            "answer any questions."
        )
    pieces.append(f"Talk soon,\n{get_dealer_name()}")
    return " ".join(pieces[:3]) + "\n\n" + " ".join(pieces[3:])
