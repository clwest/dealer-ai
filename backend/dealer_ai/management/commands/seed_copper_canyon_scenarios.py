"""python manage.py seed_copper_canyon_scenarios [--reset]

SESSION_030 pivot — Copper Canyon Auto (Yuma, AZ) demo scenarios.

Creates 4 hand-crafted chat sessions + leads pointed at
Copper Canyon inventory stock numbers (CC-*) so the manager
dashboard, lead pipeline, and trends panels have realistic
indie-shaped content for a demo. Runs alongside the existing
:mod:`seed_demo_scenarios` (Dealer OS franchise scenarios).

Vehicles are looked up by stock number from the
:mod:`seed_copper_canyon_demo` set — this command auto-runs
that seeder if the Copper Canyon inventory is missing.

Scenario shapes exercise the indie sales motion:

1. **Cash-and-carry work truck** — ag worker, $7k cash, mixed-make
   Tacoma / Ranger consideration. Handed off.
2. **BHPH weekly-pay SUV** — credit-challenged single parent, $250/wk
   budget, needs the assistant's credit-tier voice + in-house
   financing framing.
3. **Snowbird cash Highlander** — retiree, $18k cash, low-mile
   three-row for AZ→MI drives.
4. **First-time buyer + cosigner** — 620 credit, sedan, immediate
   urgency + advisor handoff request.
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


SCENARIO_TAG = "copper_canyon_scenario"


@dataclass
class ScenarioMessage:
    role: str
    content: str
    minutes_ago_offset: int = 0


@dataclass
class Scenario:
    slug: str
    customer_name: str
    customer_email: str
    customer_phone: str
    minutes_ago: int
    extracted_profile: dict
    messages: List[ScenarioMessage]
    interested_stock_numbers: List[str] = field(default_factory=list)
    lead: Optional[dict] = None


SCENARIOS: List[Scenario] = [
    # ---- 1. Cash-and-carry work truck --------------------------------------
    Scenario(
        slug="cash_work_truck_carlos",
        customer_name="Carlos Mendoza",
        customer_email="carlos.m@example.com",
        customer_phone="(928) 555-0187",
        minutes_ago=22,
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "truck",
            "condition": "used",
            "urgency": "this_week",
            "credit_range": "unknown",
        },
        messages=[
            ScenarioMessage(
                "user",
                "I need a work truck — got about $7,000 cash to spend. "
                "Doesn't matter if it's older, just needs to run.",
                minutes_ago_offset=22,
            ),
            ScenarioMessage(
                "assistant",
                "Straight talk — at $7,000 cash, we've got a couple options "
                "worth walking out to. The older Ford Ranger XLT at $8,995 "
                "stretches you a bit, but has a proven 4.0L V6. There's also "
                "an older Ram 1500 SLT at $10,495 — bigger truck, HEMI V8, "
                "would need financing or trade for the gap. Which direction "
                "do you want to lean?",
                minutes_ago_offset=21,
            ),
            ScenarioMessage(
                "user",
                "The Ranger sounds right. Can I come look at it tomorrow?",
                minutes_ago_offset=19,
            ),
            ScenarioMessage(
                "assistant",
                "Absolutely — I'll flag this for an advisor to confirm the "
                "unit is still on the lot and set up a time. What's the best "
                "phone number to reach you?",
                minutes_ago_offset=18,
            ),
        ],
        interested_stock_numbers=["CC-T-10", "CC-T-12"],
        lead={
            "target_monthly_payment": None,
            "down_payment": 7000,
            "credit_range": "unknown",
            "urgency": "this_week",
            "conversation_summary": (
                "Cash buyer, $7k, work-truck use. Interested in older "
                "Ranger (CC-T-10); noted the older Ram (CC-T-12) as a "
                "stretch option needing financing."
            ),
            "recommended_next_action": (
                "Call to schedule Ranger walk-around. Confirm unit "
                "availability + get real numbers on trade-or-financing "
                "for the Ram if he's open."
            ),
            "handed_off": True,
        },
    ),
    # ---- 2. BHPH weekly-pay SUV --------------------------------------------
    Scenario(
        slug="bhph_weekly_suv_michelle",
        customer_name="Michelle Ortiz",
        customer_email="",
        customer_phone="(928) 555-0244",
        minutes_ago=95,
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "suv",
            "condition": "used",
            "urgency": "immediate",
            "credit_range": "poor",
        },
        messages=[
            ScenarioMessage(
                "user",
                "Looking for a reliable SUV. My credit's rough — I can do "
                "about $250 a week if that helps.",
                minutes_ago_offset=95,
            ),
            ScenarioMessage(
                "assistant",
                "Thanks for being straight with me — credit tier is normal "
                "conversation here, no judgment. Weekly payments are "
                "something an advisor can walk you through in detail, and "
                "we do have in-house financing options for buyers in your "
                "spot. A couple SUVs worth looking at: the 2014 Ford Escape "
                "SE at $8,995, and the 2013 Subaru Forester AWD at $9,495. "
                "Both would fit in-house-financing terms. Want me to "
                "connect you with an advisor to run real numbers?",
                minutes_ago_offset=94,
            ),
            ScenarioMessage(
                "user",
                "Yes please. My kids need something reliable for school runs.",
                minutes_ago_offset=90,
            ),
            ScenarioMessage(
                "assistant",
                "Understood — I'll capture this so an advisor can call you "
                "back today with a real weekly-payment quote on both units. "
                "Best number to reach you at?",
                minutes_ago_offset=89,
            ),
        ],
        interested_stock_numbers=["CC-S-03", "CC-S-07"],
        lead={
            "target_monthly_payment": None,
            "down_payment": None,
            "credit_range": "poor",
            "urgency": "immediate",
            "conversation_summary": (
                "Credit-challenged buyer, single parent, needs reliable "
                "SUV for kids. Weekly-payment ask (~$250/wk); in-house "
                "financing candidate. Interested in Escape (CC-S-03) and "
                "Forester (CC-S-07)."
            ),
            "recommended_next_action": (
                "Advisor call TODAY. Run in-house financing pre-qual, "
                "prepare weekly-payment options on both units, discuss "
                "down-payment sensitivity."
            ),
            "handed_off": False,
        },
    ),
    # ---- 3. Snowbird cash Highlander ---------------------------------------
    Scenario(
        slug="snowbird_cash_highlander_diane",
        customer_name="Diane Reeves",
        customer_email="diane.r@example.com",
        customer_phone="(517) 555-0113",
        minutes_ago=180,
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "suv",
            "condition": "used",
            "urgency": "this_week",
            "credit_range": "excellent",
        },
        messages=[
            ScenarioMessage(
                "user",
                "Hi — I winter in Yuma and drive back to Michigan every "
                "spring. Looking for a comfortable used three-row SUV with "
                "low miles, budget around $18,000 cash.",
                minutes_ago_offset=180,
            ),
            ScenarioMessage(
                "assistant",
                "Perfect budget for what you're describing. The 2016 Honda "
                "Pilot EX at $17,995 with 89k miles is a strong AZ-to-MI "
                "companion — three rows, all-wheel drive, and Honda "
                "reliability makes long-haul mileage a non-issue. If you "
                "want to stretch a bit for the newest year on the lot, the "
                "2020 Toyota Highlander LE at $23,995 is worth a look, but "
                "it's over your cash number. Want to start with the Pilot?",
                minutes_ago_offset=179,
            ),
            ScenarioMessage(
                "user",
                "The Pilot sounds ideal. Can I come drive it Saturday?",
                minutes_ago_offset=175,
            ),
        ],
        interested_stock_numbers=["CC-S-09", "CC-S-08"],
        lead={
            "target_monthly_payment": None,
            "down_payment": 18000,
            "credit_range": "excellent",
            "urgency": "this_week",
            "conversation_summary": (
                "Snowbird cash buyer, $18k, three-row SUV for AZ↔MI drive. "
                "Landed on 2016 Honda Pilot EX (CC-S-09). Highlander "
                "(CC-S-08) noted as a stretch."
            ),
            "recommended_next_action": (
                "Confirm Saturday appointment. Have Pilot detailed and "
                "keys ready. Print CARFAX for the walk-around."
            ),
            "handed_off": False,
        },
    ),
    # ---- 4. First-time buyer + cosigner ------------------------------------
    Scenario(
        slug="first_time_cosigner_marcus",
        customer_name="Marcus Torres",
        customer_email="marcus.t@example.com",
        customer_phone="(928) 555-0301",
        minutes_ago=32,
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "car",
            "condition": "used",
            "urgency": "immediate",
            "credit_range": "fair",
        },
        messages=[
            ScenarioMessage(
                "user",
                "First car — my dad said he'd cosign. My score's around 620. "
                "Something under $14k, reliable, gas-friendly.",
                minutes_ago_offset=32,
            ),
            ScenarioMessage(
                "assistant",
                "Great combo — a cosigner opens up better financing options, "
                "and 620 with cosigner support puts you in reach of most of "
                "our lender panel. Reliable + gas-friendly under $14k, two "
                "worth walking out to: the 2019 Toyota Corolla LE at $13,795 "
                "and the 2017 Honda Civic EX at $13,995. Both are 60k–70k "
                "miles, both hard to beat for long-term ownership. Want "
                "to have an advisor pull real payment options with your "
                "cosigner info?",
                minutes_ago_offset=31,
            ),
            ScenarioMessage(
                "user",
                "Yes — I need something by this weekend, I start a new job "
                "Monday.",
                minutes_ago_offset=28,
            ),
        ],
        interested_stock_numbers=["CC-C-08", "CC-C-11"],
        lead={
            "target_monthly_payment": None,
            "down_payment": None,
            "credit_range": "fair",
            "urgency": "immediate",
            "conversation_summary": (
                "First-time buyer w/ cosigner, 620 credit, <$14k budget. "
                "Interested in Corolla (CC-C-08) and Civic (CC-C-11). "
                "Needs vehicle by weekend for Monday job start."
            ),
            "recommended_next_action": (
                "Advisor call TODAY. Pre-qual with cosigner. Prepare "
                "both units for weekend test drives; note the timeline "
                "pressure."
            ),
            "handed_off": False,
        },
    ),
]


def _apply_scenario(scenario: Scenario) -> tuple[ChatSession, Optional[CustomerLead]]:
    """Create or refresh a scenario's session, messages, and optional lead."""
    now = timezone.now()
    anchor = now - timedelta(minutes=scenario.minutes_ago)

    session, created = ChatSession.objects.get_or_create(
        metadata__slug=scenario.slug,
        defaults={
            "customer_name": scenario.customer_name,
            "customer_email": scenario.customer_email,
            "customer_phone": scenario.customer_phone,
            "metadata": {"slug": scenario.slug, "demo_tag": SCENARIO_TAG},
            "extracted_profile": scenario.extracted_profile,
        },
    )
    if not created:
        # Refresh the fields on the singleton row for this slug so
        # re-runs stay canonical.
        session.customer_name = scenario.customer_name
        session.customer_email = scenario.customer_email
        session.customer_phone = scenario.customer_phone
        session.extracted_profile = scenario.extracted_profile
        session.metadata = {"slug": scenario.slug, "demo_tag": SCENARIO_TAG}
        session.save()
        session.messages.all().delete()

    for msg in scenario.messages:
        cm = ChatMessage.objects.create(
            session=session,
            role=msg.role,
            content=msg.content,
            metadata={"demo_tag": SCENARIO_TAG},
        )
        cm.created_at = anchor + timedelta(
            minutes=(scenario.minutes_ago - msg.minutes_ago_offset)
        )
        cm.save(update_fields=["created_at"])

    interested = list(
        Vehicle.objects.filter(
            stock_number__in=scenario.interested_stock_numbers
        )
    )
    for cm in session.messages.filter(role="assistant"):
        if interested:
            cm.matched_vehicles.set(interested)

    lead_row: Optional[CustomerLead] = None
    if scenario.lead is not None:
        lead_row, _ = CustomerLead.objects.update_or_create(
            session=session,
            defaults={
                "name": scenario.customer_name,
                "phone": scenario.customer_phone,
                "email": scenario.customer_email,
                "target_monthly_payment": _decimal_or_none(
                    scenario.lead.get("target_monthly_payment")
                ),
                "down_payment": _decimal_or_none(
                    scenario.lead.get("down_payment")
                ),
                "credit_range": scenario.lead.get("credit_range", ""),
                "urgency": scenario.lead.get("urgency", ""),
                "conversation_summary": scenario.lead.get(
                    "conversation_summary", ""
                ),
                "recommended_next_action": scenario.lead.get(
                    "recommended_next_action", ""
                ),
                "handed_off": scenario.lead.get("handed_off", False),
            },
        )
        if interested:
            lead_row.interested_vehicles.set(interested)

    return session, lead_row


def _decimal_or_none(value) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(str(value))


def _reset_scenario_rows() -> None:
    """Remove any prior Copper Canyon scenario rows."""
    ChatSession.objects.filter(metadata__demo_tag=SCENARIO_TAG).delete()
    # Leads are cascade-nulled since CustomerLead.session has SET_NULL —
    # explicitly delete any orphans tagged from a prior seed run.
    CustomerLead.objects.filter(
        conversation_summary__icontains="Interested in "
    ).filter(session__isnull=True).delete()


class Command(BaseCommand):
    help = (
        "Seed 4 Copper Canyon Auto demo chat sessions + leads so the "
        "manager dashboard, pipeline, and trends panels have realistic "
        "indie-shaped content."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Wipe prior copper_canyon_scenario rows before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # Ensure the Copper Canyon inventory exists — scenarios reference
        # its stock numbers.
        needed = {
            stock
            for scenario in SCENARIOS
            for stock in scenario.interested_stock_numbers
        }
        missing = needed - set(
            Vehicle.objects.filter(stock_number__in=needed).values_list(
                "stock_number", flat=True
            )
        )
        if missing:
            self.stdout.write(
                self.style.WARNING(
                    f"Missing {len(missing)} Copper Canyon inventory rows — "
                    f"auto-running seed_copper_canyon_demo…"
                )
            )
            call_command("seed_copper_canyon_demo", stdout=StringIO())

        if options.get("reset"):
            _reset_scenario_rows()

        applied = 0
        for scenario in SCENARIOS:
            _apply_scenario(scenario)
            applied += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Copper Canyon scenarios seeded — {applied} sessions "
                f"synced (tag={SCENARIO_TAG})."
            )
        )
