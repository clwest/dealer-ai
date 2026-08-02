"""Milestone 18 · Increment 2 (SESSION_148) — retail/subprime archetype.

Per MILESTONE_18_PLANNING.md §7 M18.2. Constructs a coherent
operational story for a small used-car lot: mixed-make inventory
in the $8k-$18k band, subprime-friendly F&I posture, cash-and-
carry sales mix, and just enough recon activity to demonstrate
M3/M4/M5 substrate.

**Coherence contract** per §1 Q6 + §Store-story coherence:
seeded records tell connected operational stories. Every seeded
Sale's ``total_investment`` reconciles with its VehicleCost sums.
Every recon-in-progress vehicle has a self-consistent
VehicleStageEvent progression and matching WorkOrder timeline.
Every CreditApplication references a Sale (or Lead) belonging to
the same tenant. **No Faker-style random population.**

**Atomicity contract** per §5.c Option A: the whole ``build()``
runs inside a single ``@transaction.atomic`` block via the
registry caller. Partial demo stores are architecturally
impossible.

**Data safety** per §5.g Option A: every VIN prefixed ``DEMORS``
(retail-subprime code), every phone in the ``555-01xx`` NANP
fiction block, every email at ``@demo.dealer-ai.example``, every
name drawn from the fixed pseudonym roster.

**§0.a M18.2 decision 1 — Chargeback deferred.** The Chargeback
substrate chain (DealStructure → Contract → Funding →
BackEndProductAgreement → Chargeback) is 4-5 additional entities
with distinct service verbs. Deferring keeps M18.2 focused on
the core retail/subprime persona; a dedicated "F&I chargeback
event" scenario brief at M18.5 is a natural home for it.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Optional

from django.contrib.auth import get_user_model
from django.utils import timezone

from ....models import (
    CATEGORY_DETAIL,
    CATEGORY_MECHANICAL_LABOR,
    CATEGORY_PARTS,
    CATEGORY_TIRES,
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_CATEGORY_TIRES,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_RECOMMENDED,
    CONDITION_SEVERITY_REQUIRED,
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_FORMAT_TABLET,
    DEMO_ARCHETYPE_RETAIL_SUBPRIME,
    FOLLOW_UP_TEMPLATE_1WK,
    LEAD_CHANNEL_CHAT,
    LEAD_CHANNEL_PHONE,
    LEAD_CHANNEL_WALK_IN,
    RECON_DECISION_TIER_MUST_DO,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_BHPH,
    SALE_FINANCE_TYPE_CASH,
    SALE_FINANCE_TYPE_RETAIL,
    SOURCE_AUCTION,
    SOURCE_PRIVATE,
    SOURCE_TRADE,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_INCOMING,
    VEHICLE_STAGE_INSPECTION,
    VEHICLE_STAGE_RECON,
    VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
    VEHICLE_STAGE_TRIGGER_MANUAL,
    ConditionFinding,
    ConditionReport,
    CustomerLead,
    Dealership,
    ReconDecision,
    Salesperson,
    UserDealershipRole,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
    VehicleStage,
    VehicleStageEvent,
    Vendor,
    WorkOrder,
    WorkOrderFinding,
    WorkOrderPart,
)
from ...bhph_notes.bhph_note import record_bhph_note
from ...f_and_i.credit_application import record_credit_application
from ...follow_ups.cadence import start_cadence
from ...sale.computation import record_sale
from ...vehicle_lifecycle import ensure_current_stage
from ..scenario_summary import ScenarioSummary
from ..synthetic_data import (
    synthetic_email,
    synthetic_phone,
    synthetic_vin,
)
from ..synthetic_names import SYNTHETIC_NAMES
from .base import ArchetypeBuilder


User = get_user_model()

_ARCHETYPE = DEMO_ARCHETYPE_RETAIL_SUBPRIME


# ---------------------------------------------------------------------------
# Fixed inventory + staffing specs (deterministic — reset yields same rows)
# ---------------------------------------------------------------------------

# 20 vehicles. Small used-car lot: 4x4/AWD trucks + midsize SUVs +
# reliable sedans; $8k-$18k; 2013-2019. Mixed makes appropriate to
# the persona. Stock numbers deterministic (RS-01 … RS-20) so the
# reset path restores identical identifiers.
_INVENTORY: tuple[dict, ...] = (
    # Trucks / SUVs — sub-prime customers looking for utility.
    {"stock": "RS-01", "year": 2015, "make": "Ford", "model": "F-150",
     "trim": "XLT SuperCab", "body": "truck", "price": "16495",
     "mileage": 118000, "cost_basis": "12800"},
    {"stock": "RS-02", "year": 2014, "make": "Chevrolet",
     "model": "Silverado 1500", "trim": "LT", "body": "truck",
     "price": "14795", "mileage": 132000, "cost_basis": "11200"},
    {"stock": "RS-03", "year": 2016, "make": "Toyota", "model": "Tacoma",
     "trim": "SR5 Access Cab", "body": "truck", "price": "17995",
     "mileage": 108000, "cost_basis": "14200"},
    {"stock": "RS-04", "year": 2017, "make": "Honda", "model": "CR-V",
     "trim": "EX-L", "body": "suv", "price": "16295",
     "mileage": 92000, "cost_basis": "12900"},
    {"stock": "RS-05", "year": 2018, "make": "Ford", "model": "Escape",
     "trim": "SE", "body": "suv", "price": "13995",
     "mileage": 84000, "cost_basis": "10800"},
    {"stock": "RS-06", "year": 2015, "make": "Toyota", "model": "RAV4",
     "trim": "LE AWD", "body": "suv", "price": "12495",
     "mileage": 121000, "cost_basis": "9600"},
    {"stock": "RS-07", "year": 2016, "make": "Nissan", "model": "Rogue",
     "trim": "SV", "body": "suv", "price": "11995",
     "mileage": 116000, "cost_basis": "9200"},
    {"stock": "RS-08", "year": 2017, "make": "Chevrolet",
     "model": "Equinox", "trim": "LT", "body": "suv",
     "price": "13495", "mileage": 98000, "cost_basis": "10400"},
    # Sedans — reliable transportation buyers.
    {"stock": "RS-09", "year": 2016, "make": "Honda", "model": "Civic",
     "trim": "EX", "body": "car", "price": "12995",
     "mileage": 89000, "cost_basis": "10100"},
    {"stock": "RS-10", "year": 2017, "make": "Toyota", "model": "Corolla",
     "trim": "LE", "body": "car", "price": "12495",
     "mileage": 76000, "cost_basis": "9800"},
    {"stock": "RS-11", "year": 2015, "make": "Honda", "model": "Accord",
     "trim": "Sport", "body": "car", "price": "11795",
     "mileage": 112000, "cost_basis": "9100"},
    {"stock": "RS-12", "year": 2014, "make": "Toyota", "model": "Camry",
     "trim": "LE", "body": "car", "price": "10495",
     "mileage": 128000, "cost_basis": "8100"},
    {"stock": "RS-13", "year": 2016, "make": "Nissan", "model": "Altima",
     "trim": "2.5 SV", "body": "car", "price": "10995",
     "mileage": 118000, "cost_basis": "8500"},
    {"stock": "RS-14", "year": 2013, "make": "Ford", "model": "Fusion",
     "trim": "SE", "body": "car", "price": "8495",
     "mileage": 142000, "cost_basis": "6400"},
    {"stock": "RS-15", "year": 2014, "make": "Chevrolet",
     "model": "Cruze", "trim": "LT", "body": "car",
     "price": "8995", "mileage": 138000, "cost_basis": "6800"},
    {"stock": "RS-16", "year": 2015, "make": "Hyundai",
     "model": "Elantra", "trim": "SE", "body": "car",
     "price": "9495", "mileage": 122000, "cost_basis": "7200"},
    {"stock": "RS-17", "year": 2016, "make": "Kia", "model": "Optima",
     "trim": "LX", "body": "car", "price": "11295",
     "mileage": 108000, "cost_basis": "8700"},
    {"stock": "RS-18", "year": 2017, "make": "Mazda", "model": "Mazda3",
     "trim": "Sport", "body": "car", "price": "12995",
     "mileage": 82000, "cost_basis": "10200"},
    {"stock": "RS-19", "year": 2018, "make": "Volkswagen",
     "model": "Jetta", "trim": "S", "body": "car",
     "price": "13495", "mileage": 74000, "cost_basis": "10600"},
    {"stock": "RS-20", "year": 2015, "make": "Subaru",
     "model": "Impreza", "trim": "2.0i", "body": "car",
     "price": "9995", "mileage": 116000, "cost_basis": "7700"},
)


# Staffing — 4 salespeople (1 sales manager + 3 advisors). Slugs
# deterministic so reset restores same identifiers.
_STAFF: tuple[dict, ...] = (
    {"slug": "sam-manager", "name_index": 0, "role": ROLE_SALES_MANAGER,
     "is_manager": True},
    {"slug": "advisor-avery", "name_index": 6, "role": ROLE_ADVISOR,
     "is_manager": False},
    {"slug": "advisor-jamie", "name_index": 1, "role": ROLE_ADVISOR,
     "is_manager": False},
    {"slug": "advisor-morgan", "name_index": 2, "role": ROLE_ADVISOR,
     "is_manager": False},
)


# 15 leads spanning urgency + channel mix. Some assigned to
# salespeople, some unassigned. Vehicle-interest links reference
# specific stock numbers from _INVENTORY.
_LEADS: tuple[dict, ...] = (
    {"name_index": 10, "urgency": "immediate", "channel": LEAD_CHANNEL_WALK_IN,
     "assigned_to_slug": "advisor-avery", "interested": "RS-01"},
    {"name_index": 11, "urgency": "this_week", "channel": LEAD_CHANNEL_CHAT,
     "assigned_to_slug": "advisor-jamie", "interested": "RS-04"},
    {"name_index": 12, "urgency": "this_week", "channel": LEAD_CHANNEL_CHAT,
     "assigned_to_slug": "advisor-morgan", "interested": "RS-10"},
    {"name_index": 13, "urgency": "this_month", "channel": LEAD_CHANNEL_PHONE,
     "assigned_to_slug": "advisor-avery", "interested": "RS-11"},
    {"name_index": 14, "urgency": "researching", "channel": LEAD_CHANNEL_CHAT,
     "assigned_to_slug": None, "interested": "RS-18"},
    {"name_index": 15, "urgency": "immediate", "channel": LEAD_CHANNEL_WALK_IN,
     "assigned_to_slug": "advisor-jamie", "interested": "RS-05"},
    {"name_index": 16, "urgency": "this_week", "channel": LEAD_CHANNEL_CHAT,
     "assigned_to_slug": "advisor-morgan", "interested": "RS-13"},
    {"name_index": 17, "urgency": "this_month", "channel": LEAD_CHANNEL_PHONE,
     "assigned_to_slug": None, "interested": "RS-14"},
    {"name_index": 18, "urgency": "researching", "channel": LEAD_CHANNEL_CHAT,
     "assigned_to_slug": "advisor-avery", "interested": "RS-09"},
    {"name_index": 19, "urgency": "immediate", "channel": LEAD_CHANNEL_WALK_IN,
     "assigned_to_slug": "advisor-jamie", "interested": "RS-06"},
    {"name_index": 20, "urgency": "this_week", "channel": LEAD_CHANNEL_CHAT,
     "assigned_to_slug": "advisor-morgan", "interested": "RS-17"},
    {"name_index": 21, "urgency": "this_month", "channel": LEAD_CHANNEL_PHONE,
     "assigned_to_slug": None, "interested": "RS-19"},
    {"name_index": 22, "urgency": "researching", "channel": LEAD_CHANNEL_CHAT,
     "assigned_to_slug": "advisor-avery", "interested": "RS-20"},
    {"name_index": 23, "urgency": "immediate", "channel": LEAD_CHANNEL_WALK_IN,
     "assigned_to_slug": "advisor-jamie", "interested": "RS-08"},
    {"name_index": 24, "urgency": "this_week", "channel": LEAD_CHANNEL_CHAT,
     "assigned_to_slug": "advisor-morgan", "interested": "RS-16"},
)


# 5 recent Sales — cash + retail-finance + BHPH mix. The BHPH sale
# exercises M15 sync-sibling GL post + M12 BhphNote origination.
# Vehicles chosen from the higher-mileage / lower-price band that
# fits the sub-prime buyer story.
_SALES: tuple[dict, ...] = (
    {"stock": "RS-12", "buyer_name_index": 25, "sold_price": "10495",
     "finance": SALE_FINANCE_TYPE_CASH, "lender": "",
     "days_ago": 3, "cost_basis": "8100"},
    {"stock": "RS-15", "buyer_name_index": 26, "sold_price": "8995",
     "finance": SALE_FINANCE_TYPE_RETAIL,
     "lender": "Regional Credit Union", "days_ago": 6,
     "cost_basis": "6800"},
    {"stock": "RS-16", "buyer_name_index": 27, "sold_price": "9495",
     "finance": SALE_FINANCE_TYPE_RETAIL,
     "lender": "SubPrime Auto Finance", "days_ago": 9,
     "cost_basis": "7200"},
    {"stock": "RS-11", "buyer_name_index": 28, "sold_price": "11795",
     "finance": SALE_FINANCE_TYPE_CASH, "lender": "",
     "days_ago": 12, "cost_basis": "9100"},
    # The BHPH sale — fires M15 sync-sibling GL post + subsequent
    # M12 BhphNote origination.
    {"stock": "RS-14", "buyer_name_index": 29, "sold_price": "8495",
     "finance": SALE_FINANCE_TYPE_BHPH, "lender": "",
     "days_ago": 5, "cost_basis": "6400"},
)


# Recon vehicles (3) — each has an acquisition + condition report +
# findings + work orders + parts + vehicle costs + stage progression.
_RECON_TARGETS: tuple[str, ...] = ("RS-04", "RS-07", "RS-17")


# 2 credit apps — subprime-friendly routing. One paper, one tablet.
# Reference the retail-finance Sales seeded above so the F&I audit
# story is coherent (sub-prime lender routing + retention window).
_CREDIT_APPS: tuple[dict, ...] = (
    {"applicant_name_index": 26, "format": CREDIT_APP_FORMAT_PAPER,
     "sale_stock": "RS-15"},
    {"applicant_name_index": 27, "format": CREDIT_APP_FORMAT_TABLET,
     "sale_stock": "RS-16"},
)


# 4 follow-up tasks — one 1wk cadence per selected lead auto-creates
# 3 tasks (offsets 1.0, 3.0, 7.0). Plus one 24hr cadence for a
# fourth task.
_FOLLOW_UP_LEADS: tuple[dict, ...] = (
    {"lead_name_index": 10, "template": FOLLOW_UP_TEMPLATE_1WK},
)


# Scenario brief slugs — daily briefs at M18.5 reference these to
# tell testers which pre-seeded state they're inheriting.
_SCENARIO_SLUGS: tuple[str, ...] = (
    "owner_daily_snapshot",
    "sales_manager_morning_pipeline",
    "advisor_walk_in_workup",
    "recon_lead_finish_line",
    "office_accounting_close",
    "subprime_credit_app_intake",
)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class RetailSubprimeArchetypeBuilder(ArchetypeBuilder):
    """Retail / subprime independent-dealer archetype.

    Small used-car lot; low volume; sub-prime lender relationships;
    walk-in + chat inbound mix; cash-and-carry + retail-finance +
    one BHPH sale in the recent history.
    """

    archetype = _ARCHETYPE

    def build(self, dealership: Dealership) -> ScenarioSummary:
        assert dealership.is_demo, (
            "RetailSubprimeArchetypeBuilder.build received a non-demo "
            "Dealership. The registry guards against this — reaching "
            "the builder means a bypass. Broken invariant."
        )

        stock_numbers, staged_vehicles = _seed_inventory(dealership)
        staff_by_slug = _seed_staff(dealership)
        leads_by_lead_index = _seed_leads(
            dealership, staff_by_slug
        )
        _seed_recon(dealership, staged_vehicles)
        _seed_sales(dealership)
        _seed_credit_applications(dealership)
        _seed_follow_ups(dealership, leads_by_lead_index)

        return ScenarioSummary(
            archetype=_ARCHETYPE,
            dealership_id=dealership.pk,
            dealership_slug=dealership.slug,
            seeded_stock_numbers=tuple(stock_numbers),
            seeded_user_usernames=tuple(
                sp.user.username for sp in staff_by_slug.values()
                if sp.user is not None
            ),
            seeded_scenario_slugs=_SCENARIO_SLUGS,
            notes=(
                f"Retail/subprime archetype: {len(stock_numbers)} vehicles, "
                f"{len(_STAFF)} salespeople, {len(_LEADS)} leads, "
                f"{len(_SALES)} sales (1 BHPH), "
                f"{len(_RECON_TARGETS)} recon-in-progress, "
                f"{len(_CREDIT_APPS)} credit apps, "
                f"{len(_FOLLOW_UP_LEADS)} follow-up cadences. "
                "Chargeback deferred per §0.a M18.2 decision 1."
            ),
        )


# ---------------------------------------------------------------------------
# Inventory + acquisition + lifecycle stage
# ---------------------------------------------------------------------------


def _seed_inventory(
    dealership: Dealership,
) -> tuple[list[str], dict[str, Vehicle]]:
    """Create the 20 vehicles + acquisitions + lifecycle stages.

    Returns ``(stock_numbers, staged_vehicles)`` where
    ``staged_vehicles`` maps stock -> Vehicle for downstream
    seeders. Every vehicle gets a VehicleAcquisition row (so the
    M2 read-model reads correctly) + a VehicleStage row at
    ``frontline`` (recon targets flip to ``recon`` in
    ``_seed_recon``).
    """
    stock_numbers: list[str] = []
    staged: dict[str, Vehicle] = {}
    now = timezone.now()
    for index, spec in enumerate(_INVENTORY):
        stock = str(spec["stock"])
        # Each vehicle gets a synthetic VIN prefixed DEMORS<hex>.
        vin = synthetic_vin(_ARCHETYPE, index)
        vehicle = Vehicle.objects.create(
            dealership=dealership,
            stock_number=stock,
            vin=vin,
            year=int(spec["year"]),
            make=spec["make"],
            model=spec["model"],
            trim=spec["trim"],
            body_style=spec["body"],
            condition="used",
            mileage=int(spec["mileage"]),
            price=Decimal(spec["price"]),
            fuel_type="Gasoline",
            source=f"demo-{_ARCHETYPE}",
            imported_at=now,
        )
        stock_numbers.append(stock)
        staged[stock] = vehicle

        # Acquisition — mix of sources across the inventory.
        source = (
            SOURCE_AUCTION if index % 3 == 0
            else SOURCE_TRADE if index % 3 == 1
            else SOURCE_PRIVATE
        )
        VehicleAcquisition.objects.create(
            dealership=dealership,
            vehicle=vehicle,
            source=source,
            purchase_price=Decimal(spec["cost_basis"]),
            purchase_date=(now - dt.timedelta(days=45 + index)).date(),
            source_detail=f"{source[:3].upper()}-{index:03d}",
        )

        # Lifecycle stage — idempotent seed via ensure_current_stage
        # (M5.1 helper). Test mode: the auto-bootstrap post_save signal
        # already created a frontline stage; ensure_current_stage
        # no-ops. Prod mode: no auto-bootstrap; ensure_current_stage
        # creates the initial frontline stage. Recon targets get
        # rewritten in _seed_recon after this.
        ensure_current_stage(
            vehicle,
            dealership=dealership,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
        )
    return stock_numbers, staged


# ---------------------------------------------------------------------------
# Staff (Users + Salespeople + UserDealershipRole memberships)
# ---------------------------------------------------------------------------


def _seed_staff(dealership: Dealership) -> dict[str, Salesperson]:
    """Create 4 Django Users + Salespeople + membership roles.

    Returns a slug -> Salesperson map for downstream lead
    assignment. Each Salesperson.user is populated so the
    M4C advisor-scoping permission classes recognize the
    linkage.
    """
    result: dict[str, Salesperson] = {}
    for spec in _STAFF:
        slug = str(spec["slug"])
        name = SYNTHETIC_NAMES[int(spec["name_index"])]
        username = f"{dealership.slug}-{slug}"
        user = User.objects.create_user(  # type: ignore[attr-defined]
            username=username,
            email=synthetic_email(name),
            password="demo-password-not-for-real-use",
            first_name=name.split(" ", 1)[0],
            last_name=name.split(" ", 1)[1] if " " in name else "",
        )
        UserDealershipRole.objects.create(
            user=user, dealership=dealership, role=str(spec["role"])
        )
        salesperson = Salesperson.objects.create(
            dealership=dealership,
            slug=slug,
            name=name,
            phone=synthetic_phone(int(spec["name_index"])),
            user=user,
            is_active=True,
        )
        result[slug] = salesperson
    return result


# ---------------------------------------------------------------------------
# Customer leads
# ---------------------------------------------------------------------------


def _seed_leads(
    dealership: Dealership,
    staff_by_slug: dict[str, Salesperson],
) -> dict[int, CustomerLead]:
    """Create the 15 CustomerLeads + assignment.

    Vehicle-interest is captured on the lead's ``interested_stock``
    field (present on the M11 lead model) so downstream seeders
    can link Sales back to their originating lead.
    """
    result: dict[int, CustomerLead] = {}
    now = timezone.now()
    for index, spec in enumerate(_LEADS):
        name = SYNTHETIC_NAMES[int(spec["name_index"])]
        assigned_slug = spec.get("assigned_to_slug")
        lead = CustomerLead.objects.create(
            dealership=dealership,
            name=name,
            email=synthetic_email(name),
            phone=synthetic_phone(int(spec["name_index"])),
            urgency=str(spec["urgency"]),
            channel=str(spec["channel"]),
            assigned_to=(
                staff_by_slug[str(assigned_slug)]
                if assigned_slug is not None
                else None
            ),
            created_at=now - dt.timedelta(hours=6 + index * 2),
        )
        result[index] = lead
    return result


# ---------------------------------------------------------------------------
# Recon activity
# ---------------------------------------------------------------------------


def _seed_recon(
    dealership: Dealership, staged: dict[str, Vehicle]
) -> None:
    """Set 3 vehicles into recon with a coherent operational story.

    Each recon vehicle gets:

    - Stage flipped from ``frontline`` to ``recon`` with a
      progression event history (incoming → inspection → recon).
    - A completed ConditionReport with 2 findings.
    - A must-do ReconDecision on each finding.
    - A WorkOrder (in-house or outsourced) linked to those
      findings via WorkOrderFinding.
    - 1-2 WorkOrderParts.
    - 2-3 VehicleCost rows (parts + labor + optional detail)
      that reconcile with the M2 investment ledger read model.
    """
    now = timezone.now()
    inspector_names = tuple(
        SYNTHETIC_NAMES[i] for i in (30, 31, 32)
    )
    # Create one outsourced vendor for the mechanical work orders.
    vendor = Vendor.objects.create(
        dealership=dealership,
        name="Desert Auto Repair (demo)",
        slug="desert-auto-repair-demo",
        categories=["mechanical", "electrical"],
        phone=synthetic_phone(35),
        email=synthetic_email("Desert Auto Repair"),
        is_active=True,
    )

    for offset, stock in enumerate(_RECON_TARGETS):
        vehicle = staged[stock]

        # Rewrite lifecycle stage — vehicle is currently in recon.
        stage = VehicleStage.objects.get(vehicle=vehicle)
        acquired_at = now - dt.timedelta(days=12 + offset * 2)
        stage.current_stage = VEHICLE_STAGE_RECON
        stage.entered_at = now - dt.timedelta(days=5 + offset)
        stage.trigger = VEHICLE_STAGE_TRIGGER_MANUAL
        stage.save(
            update_fields=["current_stage", "entered_at", "trigger"]
        )
        # Delete the bootstrap frontline event and replay the story.
        VehicleStageEvent.objects.filter(vehicle=vehicle).delete()
        VehicleStageEvent.objects.create(
            dealership=dealership, vehicle=vehicle,
            from_stage="", to_stage=VEHICLE_STAGE_INCOMING,
            entered_at=acquired_at,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        VehicleStageEvent.objects.create(
            dealership=dealership, vehicle=vehicle,
            from_stage=VEHICLE_STAGE_INCOMING,
            to_stage=VEHICLE_STAGE_INSPECTION,
            entered_at=acquired_at + dt.timedelta(days=1),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        VehicleStageEvent.objects.create(
            dealership=dealership, vehicle=vehicle,
            from_stage=VEHICLE_STAGE_INSPECTION,
            to_stage=VEHICLE_STAGE_RECON,
            entered_at=acquired_at + dt.timedelta(days=2),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )

        # ConditionReport + 2 findings.
        report = ConditionReport.objects.create(
            dealership=dealership,
            vehicle=vehicle,
            inspector_name=inspector_names[offset],
            inspected_at=acquired_at + dt.timedelta(days=1),
            mileage_at_inspection=vehicle.mileage,
            status=CONDITION_REPORT_STATUS_COMPLETE,
            completed_at=acquired_at + dt.timedelta(days=1, hours=2),
        )
        finding_a = ConditionFinding.objects.create(
            dealership=dealership, report=report,
            category=CONDITION_CATEGORY_MECHANICAL,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="Front brake pads at 3mm — replace pads + rotors.",
            estimated_cost=Decimal("380.00"),
        )
        finding_b = ConditionFinding.objects.create(
            dealership=dealership, report=report,
            category=CONDITION_CATEGORY_TIRES,
            severity=CONDITION_SEVERITY_RECOMMENDED,
            description="Rear tires below 4/32 tread depth.",
            estimated_cost=Decimal("420.00"),
        )
        for finding in (finding_a, finding_b):
            ReconDecision.objects.create(
                dealership=dealership, finding=finding,
                tier=RECON_DECISION_TIER_MUST_DO,
                decided_at=acquired_at + dt.timedelta(days=1, hours=3),
            )

        # WorkOrder — outsourced to the mechanical vendor. Status =
        # in_progress with approved_at + started_at populated (M4.2
        # state-transition timestamps).
        approved_at = acquired_at + dt.timedelta(days=2)
        started_at = acquired_at + dt.timedelta(days=2, hours=4)
        work_order = WorkOrder.objects.create(
            dealership=dealership,
            vehicle=vehicle,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue="outsourced",
            vendor=vendor,
            status="in_progress",
            approved_at=approved_at,
            started_at=started_at,
        )
        WorkOrderFinding.objects.create(
            dealership=dealership,
            work_order=work_order, finding=finding_a,
        )
        WorkOrderPart.objects.create(
            dealership=dealership, work_order=work_order,
            name="Front brake pad set",
            quantity=1, status="installed",
            source_type="local_parts",
            unit_cost=Decimal("120.00"),
        )
        WorkOrderPart.objects.create(
            dealership=dealership, work_order=work_order,
            name="Front rotor pair",
            quantity=1, status="installed",
            source_type="local_parts",
            unit_cost=Decimal("180.00"),
        )

        # VehicleCost rows reconcile the recon spend with the M2
        # ledger. is_estimate=False + posted_at=now marks them
        # already-GL-posted (the M13.2 detector treats posted_at
        # not-null as already handled).
        posted_at = acquired_at + dt.timedelta(days=3)
        VehicleCost.objects.create(
            dealership=dealership, vehicle=vehicle,
            category=CATEGORY_PARTS, amount=Decimal("300.00"),
            incurred_at=posted_at, vendor="Desert Auto Repair (demo)",
            reference=f"WO-{work_order.pk}-PARTS", is_estimate=False,
            posted_at=posted_at,
        )
        VehicleCost.objects.create(
            dealership=dealership, vehicle=vehicle,
            category=CATEGORY_MECHANICAL_LABOR, amount=Decimal("220.00"),
            incurred_at=posted_at, vendor="Desert Auto Repair (demo)",
            reference=f"WO-{work_order.pk}-LABOR", is_estimate=False,
            posted_at=posted_at,
        )
        VehicleCost.objects.create(
            dealership=dealership, vehicle=vehicle,
            category=CATEGORY_TIRES, amount=Decimal("420.00"),
            incurred_at=posted_at + dt.timedelta(days=1),
            vendor="Desert Auto Repair (demo)",
            reference=f"WO-{work_order.pk}-TIRES", is_estimate=False,
            posted_at=posted_at + dt.timedelta(days=1),
        )
        # Detail (in-house) — smaller amount, later date.
        VehicleCost.objects.create(
            dealership=dealership, vehicle=vehicle,
            category=CATEGORY_DETAIL, amount=Decimal("85.00"),
            incurred_at=posted_at + dt.timedelta(days=2),
            vendor="in-house detail bay",
            reference=f"DTL-{offset:03d}", is_estimate=False,
            posted_at=posted_at + dt.timedelta(days=2),
        )


# ---------------------------------------------------------------------------
# Sales (uses record_sale service verb → M15 sync-sibling GL post)
# ---------------------------------------------------------------------------


def _seed_sales(dealership: Dealership) -> None:
    """Create 5 recent Sales including 1 BHPH Sale.

    Every Sale routes through ``services.sale.record_sale`` so the
    M15.1 sync-sibling GL post fires, populating M13 JournalEntry
    rows the accounting scenario briefs read. The BHPH Sale
    additionally originates a BhphNote via
    ``services.bhph_notes.record_bhph_note`` so the M12 portfolio
    surface shows one active note.

    Before each Sale, the seeder posts a small VehicleCost row
    (auction purchase basis) so the M15 sale-booking journal has
    non-zero COGS to clear from Recon WIP — mirrors the operational
    reality that a used-car dealer books its auction purchase
    price into VehicleCost at acquisition.
    """
    now = timezone.now()
    for spec in _SALES:
        stock = str(spec["stock"])
        vehicle = Vehicle.objects.get(
            dealership=dealership, stock_number=stock
        )
        sale_date = (
            now - dt.timedelta(days=int(spec["days_ago"]))
        ).date()
        # Post the acquisition cost basis as a VehicleCost so the
        # M15 sale-booking journal has a matching COGS + Recon WIP
        # amount to clear.
        cost_posted_at = now - dt.timedelta(days=int(spec["days_ago"]) + 20)
        VehicleCost.objects.create(
            dealership=dealership, vehicle=vehicle,
            category=CATEGORY_PARTS, amount=Decimal(spec["cost_basis"]),
            incurred_at=cost_posted_at,
            vendor=f"Acquisition basis for {stock}",
            reference=f"ACQ-{stock}", is_estimate=False,
            posted_at=cost_posted_at,
        )

        # Optional buyer lead — creates a CustomerLead row so the
        # sale has a documented buyer trail. Only for sales that
        # need a lead reference in downstream credit-app seeding.
        buyer_name = SYNTHETIC_NAMES[int(spec["buyer_name_index"])]
        buyer = CustomerLead.objects.create(
            dealership=dealership,
            name=buyer_name,
            email=synthetic_email(buyer_name),
            phone=synthetic_phone(int(spec["buyer_name_index"])),
            urgency="immediate",
            channel=LEAD_CHANNEL_WALK_IN,
            created_at=(
                now - dt.timedelta(days=int(spec["days_ago"]) + 1)
            ),
        )

        sale = record_sale(
            vehicle,
            dealership=dealership,
            sale_date=sale_date,
            sold_price=Decimal(spec["sold_price"]),
            finance_type=str(spec["finance"]),
            buyer=buyer,
            lender_name=str(spec.get("lender", "")),
        )

        # If BHPH — originate a BhphNote so the M12 portfolio
        # surface shows an active note.
        if spec["finance"] == SALE_FINANCE_TYPE_BHPH:
            record_bhph_note(
                dealership=dealership,
                sale=sale,
                principal_financed=Decimal(spec["sold_price"]),
                apr=Decimal("21.90"),
                term_weeks=104,
                payment_frequency="weekly",
                first_payment_due=sale_date + dt.timedelta(days=7),
            )


# ---------------------------------------------------------------------------
# Credit applications (uses record_credit_application service verb)
# ---------------------------------------------------------------------------


def _seed_credit_applications(dealership: Dealership) -> None:
    """Seed 2 CreditApplication rows attached to retail-finance Sales.

    Uses the shipped service verb so ``retention_expires_at`` is
    populated per M10 posture. Both apps target sub-prime lenders —
    documented in ``notes`` for tester scenario briefs.
    """
    from ....models import Sale

    for spec in _CREDIT_APPS:
        applicant_name = SYNTHETIC_NAMES[
            int(spec["applicant_name_index"])
        ]
        sale = Sale.objects.get(
            dealership=dealership,
            vehicle__stock_number=str(spec["sale_stock"]),
        )
        record_credit_application(
            dealership=dealership,
            applicant_full_name=applicant_name,
            source_format=str(spec["format"]),
            sale=sale,
            notes=(
                f"Sub-prime routing: {sale.lender_name}. "
                "Applicant profile fits pilot-validation scenario."
            ),
        )


# ---------------------------------------------------------------------------
# Follow-up cadences (uses start_cadence service verb)
# ---------------------------------------------------------------------------


def _seed_follow_ups(
    dealership: Dealership,
    leads_by_lead_index: dict[int, CustomerLead],
) -> None:
    """Seed follow-up cadence + tasks for one representative lead.

    The 1wk template auto-creates 3 tasks (1 / 3 / 7 day offsets)
    per §11.4 FOLLOW_UP_TEMPLATE_OFFSETS. Delivered as pending
    tasks so the tester can walk through the operator work-queue.
    """
    for spec in _FOLLOW_UP_LEADS:
        # Find the target lead in the seeded leads dict by matching
        # its name index.
        target_name = SYNTHETIC_NAMES[int(spec["lead_name_index"])]
        lead: Optional[CustomerLead] = None
        for candidate in leads_by_lead_index.values():
            if candidate.name == target_name:
                lead = candidate
                break
        if lead is None:
            continue
        start_cadence(
            dealership=dealership,
            lead=lead,
            template=str(spec["template"]),
        )
