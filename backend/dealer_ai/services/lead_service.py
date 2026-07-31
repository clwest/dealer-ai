"""Lead creation + conversation summarization for sales handoff.

Used by views.create_lead. Encapsulates:
- conversation summary generation (LLM)
- rule-based "recommended next action" for the salesperson
- lead persistence + handoff system message in the chat thread
- session.lead_created flag flip
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, List, Optional

from django.db import transaction

from ..models import ChatMessage, ChatSession, CustomerLead, Vehicle
from .dealer_config import get_dealer_name
from .intent_parser import merge_profile
from .llm.base import LLMProvider
from .llm.factory import get_llm_provider
from .payment_engine import affordable_max_price
from .tenancy import get_default_dealership

logger = logging.getLogger(__name__)


def _render(template: str) -> str:
    """Format a dealer-templated string with the current dealer name.

    Prompt / signature constants use ``{dealer_name}`` as a placeholder
    resolved at call time via :func:`dealer_config.get_dealer_name`.
    """
    return template.format(dealer_name=get_dealer_name())


SUMMARY_PROMPT = """You are summarizing a chat at {dealer_name} for a salesperson.

Write a tight, factual handoff brief — 3 to 5 sentences — that captures:
- What the customer is looking for (vehicle type, model, condition).
- Their budget signals (target monthly payment, down payment, trade-in).
- Their urgency and any timing/financing notes they mentioned.
- One sentence on the most useful starting point for the salesperson.

Style:
- No marketing language. No greetings. No bullet points.
- Use plain past tense. Refer to the customer as "the customer".
- Do NOT invent details that aren't in the transcript or profile.
- Keep it under 120 words.
"""


@dataclass
class LeadInput:
    name: str
    phone: str = ""
    email: str = ""
    target_monthly_payment: Optional[Decimal] = None
    down_payment: Optional[Decimal] = None
    trade_in: str = ""
    credit_range: str = ""
    urgency: str = ""
    notes: str = ""
    interested_vehicle_ids: List[int] = None  # type: ignore[assignment]


# ---- Public API -------------------------------------------------------------


def create_lead_from_session(
    *,
    session: Optional[ChatSession],
    payload: dict,
    provider: Optional[LLMProvider] = None,
) -> CustomerLead:
    """Create a CustomerLead, generate summary + next action, and write a handoff
    message into the chat thread (when a session is supplied)."""
    provider = provider or get_llm_provider()

    interested_ids = payload.get("interested_vehicles") or []
    interested_vehicles: List[Vehicle] = list(
        Vehicle.objects.filter(id__in=interested_ids)
    ) if interested_ids else []

    # Merge any contact info from the lead form back into the session profile so
    # the salesperson can see one consolidated picture.
    if session is not None:
        contact_updates = {}
        if payload.get("target_monthly_payment") is not None:
            try:
                contact_updates["target_monthly_payment"] = int(
                    float(payload["target_monthly_payment"])
                )
            except (TypeError, ValueError):
                pass
        if payload.get("down_payment") is not None:
            try:
                contact_updates["down_payment"] = int(float(payload["down_payment"]))
            except (TypeError, ValueError):
                pass
        if payload.get("urgency"):
            contact_updates["urgency"] = payload["urgency"]
        if payload.get("credit_range"):
            contact_updates["credit_range"] = payload["credit_range"]
        if payload.get("trade_in"):
            contact_updates["trade_in"] = True

        if contact_updates:
            session.extracted_profile = merge_profile(
                session.extracted_profile, contact_updates
            )

    summary = _generate_conversation_summary(
        provider=provider,
        session=session,
        payload=payload,
        interested_vehicles=interested_vehicles,
    )
    next_action = _recommend_next_action(
        payload=payload,
        interested_vehicles=interested_vehicles,
        profile=(session.extracted_profile if session else {}),
    )

    # Tenant inheritance: prefer the parent session's dealership so lead
    # + handoff message stay tenant-consistent with the originating
    # session. When there's no session (direct lead creation, e.g. from
    # a walk-in form), fall through to the default. The pre_save
    # tenancy signal would also cover this case; passing it explicitly
    # here keeps intent visible for future request-context callers.
    lead_dealership = (
        session.dealership if session is not None and session.dealership_id
        else get_default_dealership()
    )

    with transaction.atomic():
        lead = CustomerLead.objects.create(
            dealership=lead_dealership,
            session=session,
            name=payload.get("name", "").strip(),
            phone=payload.get("phone", "").strip(),
            email=payload.get("email", "").strip(),
            target_monthly_payment=_decimal_or_none(payload.get("target_monthly_payment")),
            down_payment=_decimal_or_none(payload.get("down_payment")),
            trade_in=payload.get("trade_in", "") or "",
            urgency=payload.get("urgency", "") or "",
            credit_range=payload.get("credit_range", "") or "",
            notes=payload.get("notes", "") or "",
            conversation_summary=summary,
            recommended_next_action=next_action,
        )
        if interested_vehicles:
            lead.interested_vehicles.set(interested_vehicles)

        if session is not None:
            update_fields = []
            if not session.lead_created:
                session.lead_created = True
                update_fields.append("lead_created")
            update_fields.extend(["extracted_profile", "updated_at"])
            session.save(update_fields=list(set(update_fields)))

            ChatMessage.objects.create(
                dealership=lead_dealership,
                session=session,
                role="system",
                content=_format_handoff_message(lead),
                metadata={"lead_id": lead.id, "kind": "handoff"},
            )

    return lead


# ---- Helpers ----------------------------------------------------------------


def _decimal_or_none(value) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return None


def _generate_conversation_summary(
    *,
    provider: LLMProvider,
    session: Optional[ChatSession],
    payload: dict,
    interested_vehicles: Iterable[Vehicle],
) -> str:
    transcript_lines: List[str] = []
    profile = {}
    if session is not None:
        profile = dict(session.extracted_profile or {})
        for m in session.messages.exclude(role="system").order_by("created_at")[:30]:
            speaker = "Customer" if m.role == "user" else "Assistant"
            transcript_lines.append(f"{speaker}: {m.content}")

    profile_lines = [f"- {k}: {v}" for k, v in profile.items()] or ["- (none)"]

    vehicle_lines = [
        f"- {v.display_name} (Stock #{v.stock_number}, ${v.price:,.0f})"
        for v in interested_vehicles
    ] or ["- (no vehicles flagged)"]

    form_lines = []
    for label, key in [
        ("Name", "name"),
        ("Phone", "phone"),
        ("Email", "email"),
        ("Target monthly payment (USD)", "target_monthly_payment"),
        ("Down payment (USD)", "down_payment"),
        ("Trade-in note", "trade_in"),
        ("Credit range", "credit_range"),
        ("Urgency", "urgency"),
    ]:
        v = payload.get(key)
        if v not in (None, ""):
            form_lines.append(f"- {label}: {v}")

    user_payload = (
        "EXTRACTED PROFILE:\n" + "\n".join(profile_lines) + "\n\n"
        "LEAD FORM:\n" + ("\n".join(form_lines) or "- (none)") + "\n\n"
        "FLAGGED VEHICLES:\n" + "\n".join(vehicle_lines) + "\n\n"
        "TRANSCRIPT:\n" + ("\n".join(transcript_lines) or "(no transcript)")
    )

    try:
        text = provider.chat(
            [
                {"role": "system", "content": _render(SUMMARY_PROMPT)},
                {"role": "user", "content": user_payload},
            ],
            temperature=0.2,
            max_tokens=400,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("lead_service summary LLM call failed: %s", exc)
        text = ""

    text = (text or "").strip()
    if text:
        return text

    # Deterministic fallback if the LLM is unavailable — never block a lead.
    parts = []
    if payload.get("name"):
        parts.append(f"{payload['name']} requested follow-up.")
    if profile.get("vehicle_type") or profile.get("model"):
        parts.append(
            "Looking at "
            + (profile.get("model") or profile.get("vehicle_type", "a Ford"))
            + "."
        )
    if payload.get("target_monthly_payment"):
        parts.append(
            f"Target ~${payload['target_monthly_payment']}/mo"
            + (
                f" with ${payload['down_payment']} down."
                if payload.get("down_payment")
                else "."
            )
        )
    if payload.get("trade_in"):
        parts.append(f"Trade-in: {payload['trade_in']}.")
    if payload.get("urgency"):
        parts.append(f"Timing: {payload['urgency'].replace('_', ' ')}.")
    return " ".join(parts) or f"Customer requested a {get_dealer_name()} follow-up."


def _recommend_next_action(
    *,
    payload: dict,
    interested_vehicles: Iterable[Vehicle],
    profile: dict,
) -> str:
    urgency = (payload.get("urgency") or profile.get("urgency") or "").lower()
    target_monthly = payload.get("target_monthly_payment") or profile.get(
        "target_monthly_payment"
    )
    down_payment = payload.get("down_payment") or profile.get("down_payment") or 0
    flagged = list(interested_vehicles)

    actions: List[str] = []

    if urgency == "immediate":
        actions.append("Call within 1 hour — customer is buying now.")
    elif urgency == "this_week":
        actions.append("Call same-day to book a test drive this week.")
    elif urgency == "this_month":
        actions.append("Reach out within 24 hours; nurture toward a test drive.")
    elif urgency == "researching":
        actions.append(
            "Send a no-pressure intro email with options that match the profile."
        )
    else:
        actions.append("Reach out within 24 hours to qualify timing.")

    # Payment realism check.
    if target_monthly and flagged:
        try:
            tm = float(target_monthly)
            dp = float(down_payment or 0)
            max_price = affordable_max_price(tm, down_payment=dp)
            top_price = float(max(v.price for v in flagged))
            if top_price > max_price * 1.25:
                actions.append(
                    f"Heads up — flagged vehicles top out near ${top_price:,.0f}, "
                    f"but ~${tm}/mo with ${dp:,.0f} down maps closer to "
                    f"${max_price:,.0f}. Lead with realistic alternatives."
                )
        except (TypeError, ValueError):
            pass

    if payload.get("trade_in"):
        actions.append("Pull a trade appraisal before the call.")
    if (payload.get("credit_range") or profile.get("credit_range") or "").lower() in (
        "fair",
        "poor",
        "rebuilding",
    ):
        actions.append("Loop in finance specialist for credit-flex options.")

    if flagged:
        names = ", ".join(v.display_name for v in flagged[:3])
        actions.append(f"Confirm availability of: {names}.")

    return " ".join(actions)


def _format_handoff_message(lead: CustomerLead) -> str:
    lines = [
        "LEAD CAPTURED — handoff to sales:",
        f"Name: {lead.name}",
    ]
    if lead.phone:
        lines.append(f"Phone: {lead.phone}")
    if lead.email:
        lines.append(f"Email: {lead.email}")
    if lead.target_monthly_payment:
        lines.append(f"Target monthly payment: ${lead.target_monthly_payment}")
    if lead.down_payment:
        lines.append(f"Down payment: ${lead.down_payment}")
    if lead.trade_in:
        lines.append(f"Trade-in: {lead.trade_in}")
    if lead.credit_range:
        lines.append(f"Credit range: {lead.credit_range}")
    if lead.urgency:
        lines.append(f"Urgency: {lead.get_urgency_display()}")
    if lead.conversation_summary:
        lines.append("")
        lines.append("Summary: " + lead.conversation_summary)
    if lead.recommended_next_action:
        lines.append("")
        lines.append("Recommended next action: " + lead.recommended_next_action)
    return "\n".join(lines)
