"""python manage.py seed_demo_scenarios [--reset]

Creates 5 hand-crafted chat sessions + leads so the manager dashboard, lead
handoff modal, and trends visualizations have realistic content for a demo.

Vehicles are looked up by stock number from the `seed_demo_vehicles` set —
this command will auto-run that seeder if the demo inventory is missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from typing import Iterable, List, Optional

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from dealer_ai.models import ChatMessage, ChatSession, CustomerLead, Vehicle


SCENARIO_TAG = "demo_scenario"


@dataclass
class ScenarioMessage:
    role: str  # "user" | "assistant" | "system"
    content: str
    minutes_ago_offset: int = 0  # minutes earlier than the session's anchor


@dataclass
class Scenario:
    slug: str
    customer_name: str
    customer_email: str
    customer_phone: str
    minutes_ago: int  # how long ago the session "happened"
    extracted_profile: dict
    messages: List[ScenarioMessage]
    interested_stock_numbers: List[str] = field(default_factory=list)
    lead: Optional[dict] = None  # if None, no lead is captured for this scenario


SCENARIOS: List[Scenario] = [
    # ---- 1. Budget mismatch -------------------------------------------------
    Scenario(
        slug="budget_mismatch_f150",
        customer_name="Jamie Park",
        customer_email="jamie.park@example.com",
        customer_phone="(405) 555-0142",
        minutes_ago=18,
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "truck",
            "model": "F-150",
            "make": "Ford",
            "condition": "new",
            "target_monthly_payment": 500,
            "down_payment": 0,
            "urgency": "this_month",
            "credit_range": "good",
        },
        messages=[
            ScenarioMessage(
                "user",
                "Hey, I'm looking for a new F-150. I want something around $500/month — what would fit?",
                minutes_ago_offset=18,
            ),
            ScenarioMessage(
                "assistant",
                (
                    "Great choice — F-150s are our most popular truck. At $500/mo with no money down, "
                    "your realistic ceiling lands closer to a Ranger XLT or a base F-150 XL than a fully-loaded "
                    "Lariat. Want me to show options around that real budget?"
                ),
                minutes_ago_offset=17,
            ),
            ScenarioMessage(
                "user",
                "Actually I had my eye on the Lariat with the panoramic roof. That's the one for me.",
                minutes_ago_offset=16,
            ),
            ScenarioMessage(
                "assistant",
                (
                    "Totally fair — that 2025 Lariat (Stock #FF-2025-002) lists at $78,495 with the 3.5L EcoBoost, "
                    "BlueCruise, leather, and the pano roof. Just so the numbers are honest: at $500/mo with no down, "
                    "the math points closer to ~$36–40k. To get to that Lariat at $500, you'd typically need around "
                    "$20–25k down or trade equity, or a longer 84-month term. A sales advisor can map both paths for you."
                ),
                minutes_ago_offset=15,
            ),
            ScenarioMessage(
                "user",
                "Hm, I have a 2018 Escape I could trade. It's in good shape, around 70,000 miles.",
                minutes_ago_offset=12,
            ),
            ScenarioMessage(
                "assistant",
                (
                    "That helps a lot — a clean 2018 Escape can move the math meaningfully toward the Lariat. "
                    "I can flag this for a Freedom Ford advisor to pull a real trade appraisal and put live numbers in "
                    "front of you. Want me to capture your contact info?"
                ),
                minutes_ago_offset=10,
            ),
        ],
        interested_stock_numbers=["FF-2025-002"],
        lead={
            "name": "Jamie Park",
            "phone": "(405) 555-0142",
            "email": "jamie.park@example.com",
            "target_monthly_payment": Decimal("500"),
            "down_payment": Decimal("0"),
            "trade_in": "2018 Ford Escape, ~70,000 miles, good condition",
            "credit_range": "good",
            "urgency": "this_month",
            "conversation_summary": (
                "Customer wants a 2025 F-150 Lariat ($78,495) but is targeting $500/mo with no money down. "
                "Has a 2018 Escape (~70,000 miles) available as trade. Open to alternatives once the budget reality "
                "is clear. Strong interest, realistic outcome likely a base F-150 or Ranger unless trade and "
                "down-payment math improves."
            ),
            "recommended_next_action": (
                "Pull a quick trade appraisal on the 2018 Escape, then call today with two options side-by-side: "
                "(1) Lariat with realistic terms incl. trade equity, (2) F-150 XLT closer to the $500 target. "
                "Lead with honesty — Jamie responded well to direct math."
            ),
        },
    ),
    # ---- 2. Used SUV under $30k --------------------------------------------
    Scenario(
        slug="used_suv_under_30k",
        customer_name="Morgan Lee",
        customer_email="morgan.lee@example.com",
        customer_phone="(405) 555-0188",
        minutes_ago=42,
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "suv",
            "condition": "used",
            "target_monthly_payment": 400,
            "down_payment": 2000,
            "urgency": "this_week",
            "credit_range": "good",
        },
        messages=[
            ScenarioMessage(
                "user",
                "Looking for a used SUV under $30k for two kids. Something reliable for the highway commute.",
                minutes_ago_offset=42,
            ),
            ScenarioMessage(
                "assistant",
                (
                    "Two strong fits in that band: a 2021 Escape Titanium Hybrid AWD (#FF-USED-102) at $28,995 with "
                    "leather and a panoramic roof, and a 2020 Explorer Limited 4WD (#FF-USED-103) at $36,995 — slightly "
                    "over budget but bigger. Want me to estimate payments at $400/mo with $2,000 down?"
                ),
                minutes_ago_offset=41,
            ),
            ScenarioMessage(
                "user",
                "Yes please. We probably want the Escape — what does that look like monthly?",
                minutes_ago_offset=39,
            ),
            ScenarioMessage(
                "assistant",
                (
                    "On the Escape Hybrid at $28,995 with $2,000 down: roughly $475/mo over 60 months or about "
                    "$415/mo over 72 months (W.A.C. — with approved credit). These are estimates only; final "
                    "rate and terms depend on credit and lender approval. "
                    "You'd get a hybrid that does about 42 mpg and AWD. Want a Freedom Ford advisor to put real "
                    "numbers together?"
                ),
                minutes_ago_offset=38,
            ),
            ScenarioMessage(
                "user",
                "Yeah let's do it. We'd like to look at it this week.",
                minutes_ago_offset=36,
            ),
        ],
        interested_stock_numbers=["FF-USED-102"],
        lead={
            "name": "Morgan Lee",
            "phone": "(405) 555-0188",
            "email": "morgan.lee@example.com",
            "target_monthly_payment": Decimal("400"),
            "down_payment": Decimal("2000"),
            "trade_in": "",
            "credit_range": "good",
            "urgency": "this_week",
            "conversation_summary": (
                "Family of four needs a used AWD SUV under $30k. Strong interest in the 2021 Escape Titanium "
                "Hybrid AWD ($28,995). Realistic budget at $400/mo with $2k down — 72-month term lands the math "
                "cleanly. Wants to come in this week."
            ),
            "recommended_next_action": (
                "Same-day call to book a test drive this week. Confirm Escape Hybrid availability, prep a "
                "real quote at 72-month term with $2k down. Highlight the fuel-economy story (~42 mpg) "
                "which mattered to them."
            ),
        },
    ),
    # ---- 3. Service question (no purchase intent) ---------------------------
    Scenario(
        slug="service_oil_change",
        customer_name="Avery Chen",
        customer_email="avery.chen@example.com",
        customer_phone="(405) 555-0167",
        minutes_ago=120,
        extracted_profile={
            "intent": "service_question",
            "service_interest": True,
        },
        messages=[
            ScenarioMessage(
                "user",
                "Quick question — what's an oil change run on a 2019 F-150? And do you have a recall on the EcoBoost?",
                minutes_ago_offset=120,
            ),
            ScenarioMessage(
                "assistant",
                (
                    "Honest answer: I don't have live service pricing or recall lookup on my side yet. "
                    "Freedom Ford's service department can quote the oil change in about a minute and check your VIN "
                    "for any open recalls. Want me to flag this for them so they reach out?"
                ),
                minutes_ago_offset=119,
            ),
            ScenarioMessage(
                "user",
                "Sure. I'm here in town, was hoping to book this week.",
                minutes_ago_offset=117,
            ),
        ],
        interested_stock_numbers=[],
        lead={
            "name": "Avery Chen",
            "phone": "(405) 555-0167",
            "email": "avery.chen@example.com",
            "target_monthly_payment": None,
            "down_payment": None,
            "trade_in": "",
            "credit_range": "",
            "urgency": "this_week",
            "conversation_summary": (
                "Existing 2019 F-150 owner asked about oil change pricing and an EcoBoost recall lookup. "
                "Not a sales lead — pure service intent. Wants to book this week."
            ),
            "recommended_next_action": (
                "Route to the service department, not sales. Have a service advisor call within 24 hours with "
                "an oil change quote and run the VIN for recalls. Friendly, no upsell."
            ),
        },
    ),
    # ---- 4. Trade-in + pre-owned financing ---------------------------------
    Scenario(
        slug="trade_in_used_truck",
        customer_name="Riley Singh",
        customer_email="riley.singh@example.com",
        customer_phone="(405) 555-0123",
        minutes_ago=180,
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "truck",
            "condition": "used",
            "trade_in": True,
            "credit_range": "fair",
            "financing_interest": True,
            "urgency": "this_week",
        },
        messages=[
            ScenarioMessage(
                "user",
                "I want to trade in my 2018 Escape on a used truck. My credit's not perfect — fair I'd say.",
                minutes_ago_offset=180,
            ),
            ScenarioMessage(
                "assistant",
                (
                    "Two strong used options today: a 2022 F-150 XLT 4x4 CPO (#FF-USED-101) at $48,995 with a Ford "
                    "certified warranty, and a 2019 Ranger XLT 4x4 (#FF-USED-104) at $26,995 — easier on the budget. "
                    "Both are 4x4, both have the tow package. The CPO comes with extended Ford coverage which often "
                    "matters with fair credit because lenders like the warranty."
                ),
                minutes_ago_offset=178,
            ),
            ScenarioMessage(
                "user",
                "Ranger sounds more realistic. How does the financing work with my situation?",
                minutes_ago_offset=175,
            ),
            ScenarioMessage(
                "assistant",
                (
                    "Honest answer: I can't pull rate quotes — Freedom Ford's finance team works with multiple lenders "
                    "and has flex programs for fair credit, including credit-rebuilding plans. The Ranger at $26,995 "
                    "with a typical trade gives you more room to land a workable monthly. Let me flag this so a finance "
                    "specialist can prep options before your visit."
                ),
                minutes_ago_offset=173,
            ),
            ScenarioMessage(
                "user",
                "Yes please. I can come in Saturday.",
                minutes_ago_offset=170,
            ),
        ],
        interested_stock_numbers=["FF-USED-104", "FF-USED-101"],
        lead={
            "name": "Riley Singh",
            "phone": "(405) 555-0123",
            "email": "riley.singh@example.com",
            "target_monthly_payment": None,
            "down_payment": None,
            "trade_in": "2018 Ford Escape (planning to trade)",
            "credit_range": "fair",
            "urgency": "this_week",
            "conversation_summary": (
                "Wants to trade a 2018 Escape on a used truck. Self-described fair credit. Strongest interest "
                "is the 2019 Ranger XLT 4x4 ($26,995); also looked at the CPO 2022 F-150 ($48,995). Asked "
                "directly about financing fit. Plans to visit Saturday."
            ),
            "recommended_next_action": (
                "Loop in finance specialist with a fair-credit-aware lender shortlist before Saturday. Pull "
                "trade appraisal on the 2018 Escape ahead of the visit. Lead with the Ranger; keep the CPO "
                "F-150 as the upgrade story if the appraisal comes in strong."
            ),
        },
    ),
    # ---- 5. Family camping / towing -----------------------------------------
    Scenario(
        slug="family_camping_tow",
        customer_name="Taylor Romero",
        customer_email="taylor.romero@example.com",
        customer_phone="(405) 555-0119",
        minutes_ago=300,
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "suv",
            "model": "Explorer",
            "make": "Ford",
            "condition": "new",
            "urgency": "this_month",
        },
        messages=[
            ScenarioMessage(
                "user",
                "We have a small camper trailer (~3,500 lb) and three kids. Need an AWD SUV that can tow it for trips.",
                minutes_ago_offset=300,
            ),
            ScenarioMessage(
                "assistant",
                (
                    "For 3,500 lb trailering plus three kids, two strong options: the 2025 Explorer ST-Line AWD "
                    "(#FF-2025-007, $63,995) gives you a real third row and BlueCruise for the highway runs. The "
                    "2025 Bronco Outer Banks 4-Door (#FF-2025-005, $64,995) is more weekend-fun, removable top, "
                    "Sasquatch tires. Both are 4x4/AWD."
                ),
                minutes_ago_offset=298,
            ),
            ScenarioMessage(
                "user",
                "Three kids in car seats — third row matters. The Explorer might win for that alone.",
                minutes_ago_offset=295,
            ),
            ScenarioMessage(
                "assistant",
                (
                    "Yeah, three across in the second row with car seats is rough — the Explorer's third row gives "
                    "you breathing room and a small camper is well within its tow rating. With the 2.3L EcoBoost and "
                    "the BlueCruise package, longer highway road trips get a lot easier. Want me to flag this so a "
                    "Freedom Ford advisor can confirm tow-package availability and set up a test drive?"
                ),
                minutes_ago_offset=293,
            ),
            ScenarioMessage(
                "user",
                "Yes — I'm not in a rush, sometime this month. We're flexible.",
                minutes_ago_offset=290,
            ),
        ],
        interested_stock_numbers=["FF-2025-007"],
        lead={
            "name": "Taylor Romero",
            "phone": "(405) 555-0119",
            "email": "taylor.romero@example.com",
            "target_monthly_payment": None,
            "down_payment": None,
            "trade_in": "",
            "credit_range": "",
            "urgency": "this_month",
            "conversation_summary": (
                "Family of five with a ~3,500 lb camper trailer. Three kids in car seats — third row is a hard "
                "requirement. Strong interest in the 2025 Explorer ST-Line AWD ($63,995). Considered the Bronco "
                "but ruled out for car-seat practicality. No rush — plans to buy this month."
            ),
            "recommended_next_action": (
                "Confirm tow package availability on Stock #FF-2025-007 and book a relaxed test drive that "
                "includes a child-seat fit check. Mention BlueCruise as a road-trip selling point — they "
                "responded to it organically. No urgency-pressure plays needed."
            ),
        },
    ),
]


# ---- Command ---------------------------------------------------------------


class Command(BaseCommand):
    help = "Seed realistic demo chat sessions and leads for presentation use."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Wipe existing demo scenarios + chat state first, then re-seed.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset_demo_state()

        # Make sure demo inventory exists — scenarios reference its stock numbers.
        if not Vehicle.objects.filter(source="demo_seed").exists():
            self.stdout.write(
                self.style.WARNING(
                    "No demo vehicles found — running seed_demo_vehicles first."
                )
            )
            call_command("seed_demo_vehicles", stdout=StringIO())

        created_sessions = 0
        created_leads = 0
        for scenario in SCENARIOS:
            session, lead = self._seed_scenario(scenario)
            if session is not None:
                created_sessions += 1
            if lead is not None:
                created_leads += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_sessions} demo chat sessions, "
                f"{created_leads} demo leads."
            )
        )

    # ---- Helpers ----------------------------------------------------------

    def _reset_demo_state(self) -> None:
        leads = CustomerLead.objects.count()
        sessions = ChatSession.objects.count()
        msgs = ChatMessage.objects.count()
        CustomerLead.objects.all().delete()
        ChatMessage.objects.all().delete()
        ChatSession.objects.all().delete()
        self.stdout.write(
            self.style.WARNING(
                f"Reset: cleared {sessions} sessions, {msgs} messages, {leads} leads."
            )
        )

    @transaction.atomic
    def _seed_scenario(self, scenario: Scenario):
        # If a session for this scenario already exists, skip cleanly so reruns
        # without --reset are idempotent.
        existing = ChatSession.objects.filter(
            metadata__scenario=scenario.slug
        ).first()
        if existing is not None:
            return None, None

        anchor = timezone.now() - timedelta(minutes=scenario.minutes_ago)

        session = ChatSession.objects.create(
            customer_name=scenario.customer_name,
            customer_email=scenario.customer_email,
            customer_phone=scenario.customer_phone,
            extracted_profile=scenario.extracted_profile,
            metadata={"scenario": scenario.slug, "tag": SCENARIO_TAG},
        )
        # `created_at` is auto_now_add so we backdate post-creation.
        ChatSession.objects.filter(id=session.id).update(
            created_at=anchor, updated_at=anchor
        )

        for msg_spec in scenario.messages:
            msg = ChatMessage.objects.create(
                session=session,
                role=msg_spec.role,
                content=msg_spec.content,
                metadata={"scenario": scenario.slug},
            )
            backdate = timezone.now() - timedelta(minutes=msg_spec.minutes_ago_offset)
            ChatMessage.objects.filter(id=msg.id).update(created_at=backdate)

        interested = list(
            Vehicle.objects.filter(stock_number__in=scenario.interested_stock_numbers)
        )

        lead_obj = None
        if scenario.lead:
            lead_data = dict(scenario.lead)
            lead_obj = CustomerLead.objects.create(
                session=session,
                **lead_data,
            )
            if interested:
                lead_obj.interested_vehicles.set(interested)
            CustomerLead.objects.filter(id=lead_obj.id).update(
                created_at=anchor + timedelta(minutes=2),
                updated_at=anchor + timedelta(minutes=2),
            )
            session.lead_created = True
            session.save(update_fields=["lead_created", "updated_at"])

        return session, lead_obj


def installed_scenarios() -> Iterable[Scenario]:
    """Public access for tests/inspection."""
    return SCENARIOS
