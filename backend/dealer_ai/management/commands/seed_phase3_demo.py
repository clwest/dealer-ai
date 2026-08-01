"""python manage.py seed_phase3_demo [--reset]

Manager Phase 3 demo seed — adds enough lead volume in the right shapes
so the dashboard's pipeline + demand-vs-supply + recommended-actions
panels light up with cards a manager can click "Generate Ad" on.

Specifically, after this command:

- 5+ open leads target ~$500/mo → triggers a HIGH-priority inventory
  mismatch card if open-band inventory is thin (the seed_demo_vehicles
  set has limited supply in the $27k–$32k band, which is what $500/mo
  resolves to).
- 3+ leads with urgency=immediate, handed_off=false → triggers a
  HIGH-priority sales card.
- 2+ aged leads (>48h old) in needs_handoff → triggers the aging card.
- 1 lead handed_off=true → ensures the Contacted column isn't empty.

This command is **additive and idempotent**. Each row is tagged with
``metadata.demo_tag = "phase3_seed"`` on the linked session so reruns
without ``--reset`` skip rows that already exist.

The seeded sessions reuse the same demo vehicles seeded by
``seed_demo_vehicles`` — no new inventory, no schema change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from typing import List, Optional

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from dealer_ai.models import ChatSession, CustomerLead, Vehicle


PHASE3_TAG = "phase3_seed"


@dataclass
class Phase3Lead:
    slug: str
    name: str
    phone: str
    email: str
    target_monthly_payment: Optional[Decimal]
    down_payment: Optional[Decimal]
    urgency: str
    handed_off: bool = False
    minutes_ago: int = 30
    interested_stock_numbers: List[str] = field(default_factory=list)
    extracted_profile: dict = field(default_factory=dict)
    conversation_summary: str = ""
    recommended_next_action: str = ""


# Five $500/mo leads → HIGH-priority inventory mismatch card.
_BAND_500_LEADS: List[Phase3Lead] = [
    Phase3Lead(
        slug="band500_a",
        name="Casey Morales",
        phone="(405) 555-0211",
        email="casey.morales@example.com",
        target_monthly_payment=Decimal("500"),
        down_payment=Decimal("1000"),
        urgency="this_week",
        minutes_ago=45,
        interested_stock_numbers=["FF-USED-101"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "truck",
            "target_monthly_payment": 500,
            "down_payment": 1000,
            "urgency": "this_week",
            "credit_range": "good",
        },
        conversation_summary=(
            "Wants a used truck around $500/mo with $1k down. Open to F-150 "
            "or Ranger; first-time truck buyer. Wants to come in this week."
        ),
        recommended_next_action=(
            "Call within the day; pre-quote a Ranger or used F-150 at the "
            "$500/mo target with 72-month term."
        ),
    ),
    Phase3Lead(
        slug="band500_b",
        name="Devon Patel",
        phone="(405) 555-0224",
        email="devon.patel@example.com",
        target_monthly_payment=Decimal("520"),
        down_payment=Decimal("2000"),
        urgency="this_week",
        minutes_ago=120,
        interested_stock_numbers=["FF-USED-102"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "suv",
            "target_monthly_payment": 520,
            "down_payment": 2000,
            "urgency": "this_week",
        },
        conversation_summary=(
            "Family of three, wants used SUV around $520/mo with $2k down. "
            "Strong interest in the Escape Titanium Hybrid."
        ),
        recommended_next_action=(
            "Confirm Escape Hybrid availability and prep numbers at the "
            "real $520/mo target."
        ),
    ),
    Phase3Lead(
        slug="band500_c",
        name="Robin Tate",
        phone="(405) 555-0235",
        email="robin.tate@example.com",
        target_monthly_payment=Decimal("550"),
        down_payment=Decimal("0"),
        urgency="this_month",
        minutes_ago=240,
        interested_stock_numbers=[],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "truck",
            "target_monthly_payment": 550,
            "down_payment": 0,
            "urgency": "this_month",
        },
        conversation_summary=(
            "Wants a truck around $550/mo with no money down. Hasn't picked "
            "a model yet — open to advice."
        ),
        recommended_next_action=(
            "Send 2-3 options at the $550/mo target — Maverick, Ranger, "
            "or used F-150."
        ),
    ),
    Phase3Lead(
        slug="band500_d",
        name="Sage Hernandez",
        phone="(405) 555-0246",
        email="sage.hernandez@example.com",
        target_monthly_payment=Decimal("575"),
        down_payment=Decimal("1500"),
        urgency="this_week",
        minutes_ago=360,
        interested_stock_numbers=["FF-USED-103"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "suv",
            "target_monthly_payment": 575,
            "down_payment": 1500,
            "urgency": "this_week",
        },
        conversation_summary=(
            "Wants used Explorer or similar at $575/mo with $1.5k down. Has "
            "an old trade-in in poor condition."
        ),
        recommended_next_action=(
            "Pull a quick trade appraisal and prep an Explorer or Edge at "
            "the $575/mo target."
        ),
    ),
    Phase3Lead(
        slug="band500_e",
        name="Quinn Walsh",
        phone="(405) 555-0257",
        email="quinn.walsh@example.com",
        target_monthly_payment=Decimal("595"),
        down_payment=Decimal("3000"),
        urgency="this_month",
        minutes_ago=600,
        interested_stock_numbers=[],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "suv",
            "target_monthly_payment": 595,
            "down_payment": 3000,
            "urgency": "this_month",
        },
        conversation_summary=(
            "Researching SUVs at $595/mo with $3k down. Not in a rush — "
            "wants to see options."
        ),
        recommended_next_action=(
            "Email a side-by-side of an Edge vs Explorer at the $595/mo "
            "target."
        ),
    ),
]


# Three urgency=immediate leads → HIGH-priority sales card.
_HIGH_INTENT_LEADS: List[Phase3Lead] = [
    Phase3Lead(
        slug="high_intent_a",
        name="Alex Reed",
        phone="(405) 555-0301",
        email="alex.reed@example.com",
        target_monthly_payment=Decimal("700"),
        down_payment=Decimal("5000"),
        urgency="immediate",
        minutes_ago=10,
        interested_stock_numbers=["FF-2025-001"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "truck",
            "model": "F-150",
            "make": "Ford",
            "target_monthly_payment": 700,
            "down_payment": 5000,
            "urgency": "immediate",
            "credit_range": "good",
        },
        conversation_summary=(
            "Wants a 2025 F-150 XLT. Buying TODAY if numbers work. $5k down "
            "ready, $700/mo target."
        ),
        recommended_next_action=(
            "Call now — has cash in hand and a Saturday delivery window."
        ),
    ),
    Phase3Lead(
        slug="high_intent_b",
        name="Jordan Cruz",
        phone="(405) 555-0312",
        email="jordan.cruz@example.com",
        target_monthly_payment=Decimal("450"),
        down_payment=Decimal("2500"),
        urgency="immediate",
        minutes_ago=25,
        interested_stock_numbers=["FF-USED-104"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "truck",
            "model": "Ranger",
            "make": "Ford",
            "target_monthly_payment": 450,
            "down_payment": 2500,
            "urgency": "immediate",
        },
        conversation_summary=(
            "Wants the 2019 Ranger XLT 4x4 (#FF-USED-104). Ready to write "
            "today, $2.5k down."
        ),
        recommended_next_action=(
            "Call right away — Ranger is in stock; same-day close possible."
        ),
    ),
    Phase3Lead(
        slug="high_intent_c",
        name="Skyler Brooks",
        phone="(405) 555-0323",
        email="skyler.brooks@example.com",
        target_monthly_payment=Decimal("650"),
        down_payment=Decimal("4000"),
        urgency="immediate",
        minutes_ago=55,
        interested_stock_numbers=["FF-2025-007"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "suv",
            "model": "Explorer",
            "make": "Ford",
            "target_monthly_payment": 650,
            "down_payment": 4000,
            "urgency": "immediate",
        },
        conversation_summary=(
            "Family of five — wants the 2025 Explorer ST-Line AWD today. "
            "$4k down ready."
        ),
        recommended_next_action=(
            "Call now — confirm tow package and book test drive in the "
            "next two hours."
        ),
    ),
]


# Two aged needs-handoff leads (>48h) → aging-leads card.
_AGED_LEADS: List[Phase3Lead] = [
    Phase3Lead(
        slug="aged_a",
        name="Pat Ortiz",
        phone="(405) 555-0401",
        email="pat.ortiz@example.com",
        target_monthly_payment=Decimal("400"),
        down_payment=Decimal("0"),
        urgency="this_week",
        minutes_ago=60 * 60,  # 60 hours ago
        interested_stock_numbers=["FF-USED-105"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "car",
            "target_monthly_payment": 400,
            "down_payment": 0,
            "urgency": "this_week",
        },
        conversation_summary=(
            "Asked about a used Mustang at $400/mo no down. Has been sitting "
            "in the queue without contact."
        ),
        recommended_next_action=(
            "Call before end of day — lead is approaching 3 days old."
        ),
    ),
    Phase3Lead(
        slug="aged_b",
        name="Reese Carter",
        phone="(405) 555-0412",
        email="reese.carter@example.com",
        target_monthly_payment=Decimal("475"),
        down_payment=Decimal("1500"),
        urgency="this_week",
        minutes_ago=60 * 65,  # 65 hours ago
        interested_stock_numbers=[],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "truck",
            "target_monthly_payment": 475,
            "down_payment": 1500,
            "urgency": "this_week",
        },
        conversation_summary=(
            "Wants a used truck at $475/mo with $1.5k down. Hasn't been "
            "contacted yet."
        ),
        recommended_next_action=(
            "Sweep this lead today — almost 3 days old."
        ),
    ),
]


# Eight low-band leads ($250–292/mo) → pushes the <$300/mo band into
# `tight` or `mismatch` so the inventory recommendation card appears.
#
# Each entry is hand-crafted with a realistic name, a real interested
# vehicle from the seed_demo_vehicles set under ~$18k, and a unique
# conversation summary + next-action. Together these unblock the LLM
# follow-up generator (which produces noticeably better drafts when
# the lead has a concrete vehicle anchor and a specific summary) and
# keep the demand-band pressure intact for the pipeline panel.
#
# Stock # rationale (verified against seed_demo_vehicles):
#   FF-USED-201..206  → 2013-2017 used sedans, $9,995-$13,495
#   FF-USED-301       → 2018 Ford Escape SE,   $17,995  (slight stretch)
#   FF-USED-305       → 2017 Chevy Equinox LT, $16,995  (slight stretch)
_LOW_BAND_LEADS: List[Phase3Lead] = [
    Phase3Lead(
        slug="low_band_a",
        name="Riley Cooper",
        phone="(405) 555-0612",
        email="riley.cooper@example.com",
        target_monthly_payment=Decimal("250"),
        down_payment=Decimal("500"),
        urgency="this_week",
        minutes_ago=90,
        interested_stock_numbers=["FF-USED-205"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "car",
            "condition": "used",
            "target_monthly_payment": 250,
            "down_payment": 500,
            "urgency": "this_week",
            "credit_range": "fair",
        },
        conversation_summary=(
            "First-time buyer, just out of college. $250/mo with $500 down "
            "is the absolute ceiling. Looking at the 2014 Nissan Altima 2.5 "
            "(#FF-USED-205, $9,995) — wants something reliable for the "
            "OKC commute."
        ),
        recommended_next_action=(
            "Confirm Altima availability and walk through a 72-month term "
            "to land near $250/mo. Frame the higher-mileage tradeoff "
            "honestly — Riley responds well to direct numbers."
        ),
    ),
    Phase3Lead(
        slug="low_band_b",
        name="Sam Hayes",
        phone="(405) 555-0623",
        email="sam.hayes@example.com",
        target_monthly_payment=Decimal("256"),
        down_payment=Decimal("500"),
        urgency="this_month",
        minutes_ago=125,
        interested_stock_numbers=["FF-USED-204"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "car",
            "condition": "used",
            "target_monthly_payment": 256,
            "down_payment": 500,
            "urgency": "this_month",
        },
        conversation_summary=(
            "Long commute from Edmond — wants a reliable used sedan "
            "around $256/mo. Asked about the 2013 Chevy Malibu LT "
            "(#FF-USED-204, $10,995). The older year has them a bit "
            "nervous."
        ),
        recommended_next_action=(
            "Pull a quick service-history summary on the Malibu, then "
            "text Sam the highlights. They'll close fast on concrete "
            "reassurance."
        ),
    ),
    Phase3Lead(
        slug="low_band_c",
        name="Ava Nguyen",
        phone="(405) 555-0634",
        email="ava.nguyen@example.com",
        target_monthly_payment=Decimal("262"),
        down_payment=Decimal("500"),
        urgency="this_week",
        minutes_ago=160,
        interested_stock_numbers=["FF-USED-206"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "car",
            "condition": "used",
            "target_monthly_payment": 262,
            "down_payment": 500,
            "urgency": "this_week",
            "credit_range": "good",
        },
        conversation_summary=(
            "New grad starting a job in Norman next week. Targeting "
            "$262/mo with $500 down. Strong interest in the 2017 "
            "Hyundai Sonata SE (#FF-USED-206, $10,995) — likes the "
            "fuel-economy story."
        ),
        recommended_next_action=(
            "Same-day call. Confirm Sonata availability and prep a "
            "72-month quote. Mention free first service since they're "
            "starting a new job — small wins close this profile."
        ),
    ),
    Phase3Lead(
        slug="low_band_d",
        name="Carter Bell",
        phone="(405) 555-0645",
        email="carter.bell@example.com",
        target_monthly_payment=Decimal("268"),
        down_payment=Decimal("1000"),
        urgency="this_week",
        minutes_ago=195,
        interested_stock_numbers=["FF-USED-201"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "car",
            "condition": "used",
            "make": "Ford",
            "make_lock": True,
            "target_monthly_payment": 268,
            "down_payment": 1000,
            "urgency": "this_week",
        },
        conversation_summary=(
            "Repeat Dealer OS customer — had a 2010 Focus. Wants "
            "to stay Ford and is eyeing the 2014 Ford Fusion SE "
            "(#FF-USED-201, $11,995). $1k down available. Loyalty "
            "buyer — keep the relationship warm."
        ),
        recommended_next_action=(
            "Pull Carter's prior service history if it's on file, "
            "then call. A returning Ford customer at this budget "
            "deserves a personal welcome-back touch."
        ),
    ),
    Phase3Lead(
        slug="low_band_e",
        name="Mikayla Reyes",
        phone="(405) 555-0656",
        email="mikayla.reyes@example.com",
        target_monthly_payment=Decimal("274"),
        down_payment=Decimal("500"),
        urgency="this_month",
        minutes_ago=230,
        interested_stock_numbers=["FF-USED-203"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "car",
            "condition": "used",
            "target_monthly_payment": 274,
            "down_payment": 500,
            "urgency": "this_month",
            "credit_range": "fair",
        },
        conversation_summary=(
            "Old family car finally died. Looking at the 2014 Honda "
            "Accord LX (#FF-USED-203, $12,995). Wants reliability "
            "over anything fancy. $274/mo target with $500 down."
        ),
        recommended_next_action=(
            "Email a clean Accord write-up with the maintenance "
            "highlights and a 72-month estimate at the $274/mo "
            "target. Mikayla is researching — earn the test drive "
            "with detail."
        ),
    ),
    Phase3Lead(
        slug="low_band_f",
        name="Trent Phillips",
        phone="(405) 555-0667",
        email="trent.phillips@example.com",
        target_monthly_payment=Decimal("280"),
        down_payment=Decimal("750"),
        urgency="this_week",
        minutes_ago=265,
        interested_stock_numbers=["FF-USED-202"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "car",
            "condition": "used",
            "target_monthly_payment": 280,
            "down_payment": 750,
            "urgency": "this_week",
        },
        conversation_summary=(
            "Cross-shopping a used Camry vs Accord. Currently on the "
            "2015 Toyota Camry LE (#FF-USED-202, $13,495) at $280/mo "
            "with $750 down. Mentioned a coworker who got a great "
            "deal here — referral lead."
        ),
        recommended_next_action=(
            "Call today. Lead with the Camry, but have the Accord "
            "comparison ready in case Trent pivots. Referral leads "
            "close faster — don't make them wait."
        ),
    ),
    Phase3Lead(
        slug="low_band_g",
        name="Brooke Davis",
        phone="(405) 555-0678",
        email="brooke.davis@example.com",
        target_monthly_payment=Decimal("286"),
        down_payment=Decimal("1500"),
        urgency="this_month",
        minutes_ago=300,
        interested_stock_numbers=["FF-USED-301"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "suv",
            "condition": "used",
            "target_monthly_payment": 286,
            "down_payment": 1500,
            "urgency": "this_month",
        },
        conversation_summary=(
            "New mom — wants a small SUV. Loves the 2018 Ford Escape "
            "SE FWD (#FF-USED-301, $17,995) but the math is tight at "
            "$286/mo. Has $1.5k down. Open to alternatives if the "
            "Escape doesn't pencil out."
        ),
        recommended_next_action=(
            "Pull a real Escape quote at an 84-month term — it lands "
            "closer to her $286/mo target. Have an Equinox or Sonata "
            "ready as a backup if the math is still too tight. Brooke "
            "is not in a rush; earn the right answer."
        ),
    ),
    Phase3Lead(
        slug="low_band_h",
        name="Logan Foster",
        phone="(405) 555-0689",
        email="logan.foster@example.com",
        target_monthly_payment=Decimal("292"),
        down_payment=Decimal("1000"),
        urgency="this_week",
        minutes_ago=335,
        interested_stock_numbers=["FF-USED-305"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "suv",
            "condition": "used",
            "target_monthly_payment": 292,
            "down_payment": 1000,
            "urgency": "this_week",
            "credit_range": "good",
        },
        conversation_summary=(
            "Young professional, just got promoted. Looking at the "
            "2017 Chevy Equinox LT (#FF-USED-305, $16,995). $292/mo "
            "with $1k down. Wants something reliable but isn't loyal "
            "to any brand."
        ),
        recommended_next_action=(
            "Call this week. Confirm Equinox availability and prep "
            "a 72-month estimate. Logan is decisive — match the "
            "energy and they'll close."
        ),
    ),
]


# One handed-off lead so the Contacted column isn't empty.
_CONTACTED_LEADS: List[Phase3Lead] = [
    Phase3Lead(
        slug="contacted_a",
        name="Morgan Ellis",
        phone="(405) 555-0501",
        email="morgan.ellis@example.com",
        target_monthly_payment=Decimal("525"),
        down_payment=Decimal("2000"),
        urgency="this_week",
        handed_off=True,
        minutes_ago=180,
        interested_stock_numbers=["FF-USED-102"],
        extracted_profile={
            "intent": "vehicle_search",
            "vehicle_type": "suv",
            "target_monthly_payment": 525,
            "down_payment": 2000,
            "urgency": "this_week",
        },
        conversation_summary=(
            "Already routed to an advisor. Confirmed test drive for the "
            "Escape Hybrid this weekend."
        ),
        recommended_next_action=(
            "Advisor owns this; follow up after the weekend visit."
        ),
    ),
]


ALL_PHASE3_LEADS: List[Phase3Lead] = (
    _BAND_500_LEADS
    + _HIGH_INTENT_LEADS
    + _AGED_LEADS
    + _CONTACTED_LEADS
    + _LOW_BAND_LEADS
)


class Command(BaseCommand):
    help = "Seed Manager Phase 3 demo leads so the dashboard has visible recommendations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Wipe Phase 3 demo rows first, then re-seed.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset_phase3_state()

        if not Vehicle.objects.filter(source="demo_seed").exists():
            self.stdout.write(
                self.style.WARNING(
                    "No demo vehicles found — running seed_demo_vehicles first."
                )
            )
            call_command("seed_demo_vehicles", stdout=StringIO())

        created = 0
        skipped = 0
        for spec in ALL_PHASE3_LEADS:
            existing = ChatSession.objects.filter(
                metadata__demo_tag=PHASE3_TAG,
                metadata__phase3_slug=spec.slug,
            ).first()
            if existing is not None:
                skipped += 1
                continue
            self._seed_lead(spec)
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Phase 3 seed: created {created} lead(s), skipped {skipped} "
                "already-present row(s)."
            )
        )
        self.stdout.write(
            "Open /dealer-ai-admin to see the pipeline / demand panel / "
            "recommended-actions cards refresh."
        )

    def _reset_phase3_state(self) -> None:
        sessions = ChatSession.objects.filter(metadata__demo_tag=PHASE3_TAG)
        leads_count = CustomerLead.objects.filter(session__in=sessions).count()
        sessions_count = sessions.count()
        # Delete leads first to clear the FK to sessions, then sessions
        # (cascade clears any associated chat messages).
        CustomerLead.objects.filter(session__in=sessions).delete()
        sessions.delete()
        self.stdout.write(
            self.style.WARNING(
                f"Phase 3 reset: removed {sessions_count} session(s), "
                f"{leads_count} lead(s)."
            )
        )

    @transaction.atomic
    def _seed_lead(self, spec: Phase3Lead) -> None:
        anchor = timezone.now() - timedelta(minutes=spec.minutes_ago)

        session = ChatSession.objects.create(
            customer_name=spec.name,
            customer_email=spec.email,
            customer_phone=spec.phone,
            extracted_profile=spec.extracted_profile,
            metadata={"demo_tag": PHASE3_TAG, "phase3_slug": spec.slug},
        )
        ChatSession.objects.filter(id=session.id).update(
            created_at=anchor, updated_at=anchor
        )

        lead = CustomerLead.objects.create(
            session=session,
            name=spec.name,
            phone=spec.phone,
            email=spec.email,
            target_monthly_payment=spec.target_monthly_payment,
            down_payment=spec.down_payment,
            urgency=spec.urgency,
            handed_off=spec.handed_off,
            conversation_summary=spec.conversation_summary,
            recommended_next_action=spec.recommended_next_action,
        )
        if spec.interested_stock_numbers:
            interested = list(
                Vehicle.objects.filter(
                    stock_number__in=spec.interested_stock_numbers
                )
            )
            if interested:
                lead.interested_vehicles.set(interested)
        # Backdate created_at so the aging tests (>48h) can fire.
        CustomerLead.objects.filter(id=lead.id).update(
            created_at=anchor, updated_at=anchor
        )
        session.lead_created = True
        session.save(update_fields=["lead_created", "updated_at"])
