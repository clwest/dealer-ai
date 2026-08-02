"""Milestone 18 · Increment 3 (SESSION_149) — floor-planned archetype.

Per MILESTONE_18_PLANNING.md §7 M18.3. Mid-size independent
dealer: auction floor-plan lender relationship, outside-recon
vendor network across categories, active pipeline with retail-
finance mix, and a **documented recon overrun scenario** that
anchors the recon-lead daily brief at M18.5.

**The recon-overrun anchor.** Per §7 M18.3, one of the five
in-recon vehicles ships with:

- ``WorkOrder.authorized_cost`` set well below
  ``WorkOrder.actual_cost``.
- VehicleCost rows summing to more than the acquisition cost
  basis by $600+.
- A short VendorCommunication history (vendor_comm + narrative)
  documenting the escalation.

Testers walking the recon-lead brief at M18.5 discover this
overrun by comparing authorized vs actual on the work-order
detail page and reconciling against the M2 vehicle-investment
ledger. The scenario surfaces both operational pain (overrun
communication) and platform value (the ledger + work-order
surfaces make the overrun visible).

**§0.a M18.2 decision 1 continues to apply.** Chargeback still
deferred to M18.5.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Optional

from django.contrib.auth import get_user_model
from django.utils import timezone

from ....models import (
    BE_BACK_REASON_BRING_CO_SIGNER,
    BE_BACK_REASON_BRING_TRADE_IN,
    BE_BACK_REASON_TEST_DRIVE,
    BE_BACK_STATE_PROMISED,
    BE_BACK_STATE_RETURNED,
    CATEGORY_BODY_WORK,
    CATEGORY_DETAIL,
    CATEGORY_MECHANICAL_LABOR,
    CATEGORY_PARTS,
    CATEGORY_TIRES,
    CONDITION_CATEGORY_BODY,
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_CATEGORY_TIRES,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_RECOMMENDED,
    CONDITION_SEVERITY_REQUIRED,
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_FORMAT_TABLET,
    DEMO_ARCHETYPE_FLOOR_PLANNED,
    FOLLOW_UP_TEMPLATE_1WK,
    FOLLOW_UP_TEMPLATE_24HR,
    LEAD_CHANNEL_CHAT,
    LEAD_CHANNEL_LISTING_FORM,
    LEAD_CHANNEL_PHONE,
    LEAD_CHANNEL_WALK_IN,
    RECON_DECISION_TIER_MUST_DO,
    RECON_DECISION_TIER_SHOULD_DO,
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_CASH,
    SALE_FINANCE_TYPE_RETAIL,
    SOURCE_AUCTION,
    SOURCE_TRADE,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_INCOMING,
    VEHICLE_STAGE_INSPECTION,
    VEHICLE_STAGE_RECON,
    VEHICLE_STAGE_TRIGGER_MANUAL,
    VENDOR_COMMUNICATION_CHANNEL_EMAIL,
    VENDOR_COMMUNICATION_CHANNEL_PHONE,
    VENDOR_COMMUNICATION_DIRECTION_INBOUND,
    VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
    VENDOR_COMMUNICATION_KIND_NARRATIVE,
    VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
    VENDOR_COMMUNICATION_STATUS_LOGGED,
    VENDOR_COMMUNICATION_STATUS_SENT,
    BeBack,
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
    VendorCommunication,
    WorkOrder,
    WorkOrderFinding,
    WorkOrderPart,
)
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

_ARCHETYPE = DEMO_ARCHETYPE_FLOOR_PLANNED


# ---------------------------------------------------------------------------
# Fixed inventory + staffing specs
# ---------------------------------------------------------------------------

# 40 vehicles. Mid-size independent: newer inventory, higher
# price band, floor-plan-financed. Ford / Chevy / RAM / Toyota
# heavy per the persona. Stock numbers FP-01..FP-40.
_INVENTORY: tuple[dict, ...] = (
    # Trucks (12) — the floor-plan bread-and-butter for a Sun Belt
    # independent.
    {"stock": "FP-01", "year": 2020, "make": "Ford", "model": "F-150",
     "trim": "XLT SuperCrew 4x4", "body": "truck", "price": "32995",
     "mileage": 62000, "cost_basis": "26400"},
    {"stock": "FP-02", "year": 2019, "make": "Ford", "model": "F-150",
     "trim": "Lariat SuperCrew", "body": "truck", "price": "31495",
     "mileage": 74000, "cost_basis": "25200"},
    {"stock": "FP-03", "year": 2018, "make": "RAM", "model": "1500",
     "trim": "Big Horn Crew Cab", "body": "truck", "price": "26995",
     "mileage": 88000, "cost_basis": "21600"},
    {"stock": "FP-04", "year": 2019, "make": "RAM", "model": "1500",
     "trim": "Laramie Crew Cab", "body": "truck", "price": "29495",
     "mileage": 71000, "cost_basis": "23600"},
    {"stock": "FP-05", "year": 2017, "make": "Chevrolet",
     "model": "Silverado 1500", "trim": "LTZ Crew Cab",
     "body": "truck", "price": "24995", "mileage": 96000,
     "cost_basis": "19900"},
    {"stock": "FP-06", "year": 2020, "make": "Chevrolet",
     "model": "Silverado 1500", "trim": "LT Trail Boss",
     "body": "truck", "price": "31995", "mileage": 58000,
     "cost_basis": "25600"},
    {"stock": "FP-07", "year": 2018, "make": "Toyota",
     "model": "Tacoma", "trim": "TRD Off-Road Double Cab",
     "body": "truck", "price": "28495", "mileage": 84000,
     "cost_basis": "22800"},
    {"stock": "FP-08", "year": 2019, "make": "Toyota",
     "model": "Tundra", "trim": "SR5 CrewMax", "body": "truck",
     "price": "33995", "mileage": 68000, "cost_basis": "27200"},
    {"stock": "FP-09", "year": 2017, "make": "Ford", "model": "F-250",
     "trim": "XLT Crew Cab 4x4", "body": "truck", "price": "29995",
     "mileage": 118000, "cost_basis": "23900"},
    {"stock": "FP-10", "year": 2016, "make": "GMC",
     "model": "Sierra 1500", "trim": "SLT Crew Cab", "body": "truck",
     "price": "22995", "mileage": 108000, "cost_basis": "18300"},
    {"stock": "FP-11", "year": 2018, "make": "Ford", "model": "Ranger",
     "trim": "XLT SuperCrew", "body": "truck", "price": "23495",
     "mileage": 76000, "cost_basis": "18700"},
    {"stock": "FP-12", "year": 2020, "make": "RAM", "model": "1500",
     "trim": "Rebel Crew Cab", "body": "truck", "price": "34995",
     "mileage": 52000, "cost_basis": "28000"},
    # SUVs (14) — family-oriented and off-road-capable mix.
    {"stock": "FP-13", "year": 2019, "make": "Ford", "model": "Explorer",
     "trim": "XLT AWD", "body": "suv", "price": "24995",
     "mileage": 72000, "cost_basis": "19900"},
    {"stock": "FP-14", "year": 2020, "make": "Ford", "model": "Explorer",
     "trim": "Limited AWD", "body": "suv", "price": "28995",
     "mileage": 58000, "cost_basis": "23200"},
    {"stock": "FP-15", "year": 2018, "make": "Chevrolet",
     "model": "Tahoe", "trim": "LT", "body": "suv",
     "price": "29995", "mileage": 92000, "cost_basis": "23900"},
    {"stock": "FP-16", "year": 2019, "make": "Chevrolet",
     "model": "Suburban", "trim": "LT", "body": "suv",
     "price": "32995", "mileage": 78000, "cost_basis": "26400"},
    {"stock": "FP-17", "year": 2017, "make": "Toyota",
     "model": "4Runner", "trim": "SR5 Premium 4x4", "body": "suv",
     "price": "27995", "mileage": 89000, "cost_basis": "22400"},
    {"stock": "FP-18", "year": 2018, "make": "Toyota",
     "model": "Highlander", "trim": "XLE AWD", "body": "suv",
     "price": "25995", "mileage": 82000, "cost_basis": "20800"},
    {"stock": "FP-19", "year": 2019, "make": "Toyota", "model": "RAV4",
     "trim": "Adventure AWD", "body": "suv", "price": "22995",
     "mileage": 66000, "cost_basis": "18400"},
    {"stock": "FP-20", "year": 2020, "make": "Ford", "model": "Escape",
     "trim": "SEL AWD", "body": "suv", "price": "19995",
     "mileage": 54000, "cost_basis": "16000"},
    {"stock": "FP-21", "year": 2018, "make": "Ford", "model": "Edge",
     "trim": "SEL AWD", "body": "suv", "price": "18995",
     "mileage": 88000, "cost_basis": "15200"},
    {"stock": "FP-22", "year": 2019, "make": "Chevrolet",
     "model": "Equinox", "trim": "LT AWD", "body": "suv",
     "price": "16995", "mileage": 78000, "cost_basis": "13600"},
    {"stock": "FP-23", "year": 2019, "make": "Chevrolet",
     "model": "Traverse", "trim": "LT Cloth", "body": "suv",
     "price": "22995", "mileage": 82000, "cost_basis": "18400"},
    {"stock": "FP-24", "year": 2020, "make": "Toyota",
     "model": "4Runner", "trim": "TRD Off-Road", "body": "suv",
     "price": "33995", "mileage": 62000, "cost_basis": "27200"},
    {"stock": "FP-25", "year": 2017, "make": "Ford", "model": "Expedition",
     "trim": "XLT 4x4", "body": "suv", "price": "26995",
     "mileage": 108000, "cost_basis": "21600"},
    {"stock": "FP-26", "year": 2018, "make": "GMC", "model": "Yukon",
     "trim": "SLT", "body": "suv", "price": "27995",
     "mileage": 92000, "cost_basis": "22400"},
    # Sedans + hatchbacks (10) — transportation buyers.
    {"stock": "FP-27", "year": 2019, "make": "Toyota", "model": "Camry",
     "trim": "SE", "body": "car", "price": "17995",
     "mileage": 68000, "cost_basis": "14400"},
    {"stock": "FP-28", "year": 2020, "make": "Toyota", "model": "Camry",
     "trim": "XSE V6", "body": "car", "price": "21995",
     "mileage": 54000, "cost_basis": "17600"},
    {"stock": "FP-29", "year": 2018, "make": "Ford", "model": "Fusion",
     "trim": "SE", "body": "car", "price": "13995",
     "mileage": 88000, "cost_basis": "11200"},
    {"stock": "FP-30", "year": 2019, "make": "Ford", "model": "Fusion",
     "trim": "Titanium AWD", "body": "car", "price": "17995",
     "mileage": 62000, "cost_basis": "14400"},
    {"stock": "FP-31", "year": 2020, "make": "Toyota",
     "model": "Corolla", "trim": "XSE", "body": "car",
     "price": "16995", "mileage": 48000, "cost_basis": "13600"},
    {"stock": "FP-32", "year": 2018, "make": "Chevrolet",
     "model": "Malibu", "trim": "LT", "body": "car",
     "price": "13995", "mileage": 78000, "cost_basis": "11200"},
    {"stock": "FP-33", "year": 2019, "make": "Chevrolet",
     "model": "Impala", "trim": "LT", "body": "car",
     "price": "16995", "mileage": 72000, "cost_basis": "13600"},
    {"stock": "FP-34", "year": 2020, "make": "Chevrolet",
     "model": "Malibu", "trim": "Premier", "body": "car",
     "price": "19995", "mileage": 52000, "cost_basis": "16000"},
    {"stock": "FP-35", "year": 2019, "make": "Ford", "model": "Mustang",
     "trim": "EcoBoost Fastback", "body": "car", "price": "22995",
     "mileage": 42000, "cost_basis": "18400"},
    {"stock": "FP-36", "year": 2020, "make": "Toyota",
     "model": "Prius", "trim": "LE", "body": "car",
     "price": "18995", "mileage": 58000, "cost_basis": "15200"},
    # Vans / crossovers (4).
    {"stock": "FP-37", "year": 2019, "make": "Chrysler",
     "model": "Pacifica", "trim": "Touring L", "body": "van",
     "price": "22995", "mileage": 82000, "cost_basis": "18400"},
    {"stock": "FP-38", "year": 2020, "make": "Honda",
     "model": "Odyssey", "trim": "EX-L", "body": "van",
     "price": "27995", "mileage": 62000, "cost_basis": "22400"},
    {"stock": "FP-39", "year": 2018, "make": "Ford", "model": "Transit Connect",
     "trim": "XLT", "body": "van", "price": "17995",
     "mileage": 78000, "cost_basis": "14400"},
    {"stock": "FP-40", "year": 2019, "make": "RAM",
     "model": "ProMaster City", "trim": "SLT", "body": "van",
     "price": "18995", "mileage": 68000, "cost_basis": "15200"},
)


# 6 salespeople: owner + sales manager + 4 advisors.
_STAFF: tuple[dict, ...] = (
    {"slug": "owner-hollis", "name_index": 6, "role": ROLE_DEALER_OWNER,
     "is_manager": True},
    {"slug": "sm-parker", "name_index": 22, "role": ROLE_SALES_MANAGER,
     "is_manager": True},
    {"slug": "adv-blake", "name_index": 10, "role": ROLE_ADVISOR,
     "is_manager": False},
    {"slug": "adv-cameron", "name_index": 11, "role": ROLE_ADVISOR,
     "is_manager": False},
    {"slug": "adv-drew", "name_index": 12, "role": ROLE_ADVISOR,
     "is_manager": False},
    {"slug": "adv-emerson", "name_index": 13, "role": ROLE_ADVISOR,
     "is_manager": False},
)


# ~25 leads — pipeline mix. First column is name_index into the
# synthetic roster; ~half assigned to specific advisors.
_LEADS: tuple[dict, ...] = tuple(
    {
        "name_index": 30 + i,
        "urgency": ("immediate", "this_week", "this_month", "researching")[i % 4],
        "channel": (
            LEAD_CHANNEL_WALK_IN,
            LEAD_CHANNEL_CHAT,
            LEAD_CHANNEL_LISTING_FORM,
            LEAD_CHANNEL_PHONE,
        )[i % 4],
        "assigned_to_slug": (
            None if i % 3 == 0 else (
                "adv-blake",
                "adv-cameron",
                "adv-drew",
                "adv-emerson",
            )[i % 4]
        ),
        "interested": _INVENTORY[i % len(_INVENTORY)]["stock"],
    }
    for i in range(25)
)


# ~10 recent Sales — 8 retail-finance + 2 cash. Stock numbers
# chosen to avoid overlap with recon targets so we don't try to
# sell a vehicle currently in recon.
_SALES: tuple[dict, ...] = (
    {"stock": "FP-25", "buyer_name_index": 20, "sold_price": "26995",
     "finance": SALE_FINANCE_TYPE_RETAIL,
     "lender": "Regional Trust Bank", "days_ago": 2,
     "cost_basis": "21600"},
    {"stock": "FP-26", "buyer_name_index": 21, "sold_price": "27995",
     "finance": SALE_FINANCE_TYPE_RETAIL,
     "lender": "Coast Federal Credit Union", "days_ago": 4,
     "cost_basis": "22400"},
    {"stock": "FP-28", "buyer_name_index": 22, "sold_price": "21995",
     "finance": SALE_FINANCE_TYPE_RETAIL,
     "lender": "Regional Trust Bank", "days_ago": 5,
     "cost_basis": "17600"},
    {"stock": "FP-29", "buyer_name_index": 23, "sold_price": "13995",
     "finance": SALE_FINANCE_TYPE_CASH, "lender": "",
     "days_ago": 6, "cost_basis": "11200"},
    {"stock": "FP-32", "buyer_name_index": 24, "sold_price": "13995",
     "finance": SALE_FINANCE_TYPE_RETAIL,
     "lender": "SubPrime Auto Finance", "days_ago": 7,
     "cost_basis": "11200"},
    {"stock": "FP-33", "buyer_name_index": 15, "sold_price": "16995",
     "finance": SALE_FINANCE_TYPE_RETAIL,
     "lender": "Coast Federal Credit Union", "days_ago": 9,
     "cost_basis": "13600"},
    {"stock": "FP-35", "buyer_name_index": 16, "sold_price": "22995",
     "finance": SALE_FINANCE_TYPE_CASH, "lender": "",
     "days_ago": 10, "cost_basis": "18400"},
    {"stock": "FP-37", "buyer_name_index": 17, "sold_price": "22995",
     "finance": SALE_FINANCE_TYPE_RETAIL,
     "lender": "Regional Trust Bank", "days_ago": 12,
     "cost_basis": "18400"},
    {"stock": "FP-39", "buyer_name_index": 18, "sold_price": "17995",
     "finance": SALE_FINANCE_TYPE_RETAIL,
     "lender": "SubPrime Auto Finance", "days_ago": 14,
     "cost_basis": "14400"},
    {"stock": "FP-40", "buyer_name_index": 19, "sold_price": "18995",
     "finance": SALE_FINANCE_TYPE_RETAIL,
     "lender": "Coast Federal Credit Union", "days_ago": 16,
     "cost_basis": "15200"},
)


# 5 recon targets. The FIRST one is the documented overrun.
_RECON_TARGETS: tuple[str, ...] = (
    "FP-01",   # <-- overrun anchor (F-150 XLT SuperCrew)
    "FP-15",
    "FP-17",
    "FP-24",
    "FP-27",
)


# 4 vendors — one per major recon category.
_VENDORS: tuple[dict, ...] = (
    {"slug": "sunset-mechanical", "name": "Sunset Mechanical (demo)",
     "categories": ["mechanical", "electrical"], "name_index": 33},
    {"slug": "riverside-body-paint", "name": "Riverside Body & Paint (demo)",
     "categories": ["body", "cosmetic", "paint"], "name_index": 34},
    {"slug": "clearview-glass", "name": "Clearview Glass (demo)",
     "categories": ["glass"], "name_index": 35},
    {"slug": "elite-detail-bay", "name": "Elite Detail Bay (demo)",
     "categories": ["detail"], "name_index": 36},
)


# 3 credit apps (retail-finance sales, mix of paper + tablet).
_CREDIT_APPS: tuple[dict, ...] = (
    {"applicant_name_index": 20, "format": CREDIT_APP_FORMAT_PAPER,
     "sale_stock": "FP-25"},
    {"applicant_name_index": 22, "format": CREDIT_APP_FORMAT_TABLET,
     "sale_stock": "FP-28"},
    {"applicant_name_index": 24, "format": CREDIT_APP_FORMAT_TABLET,
     "sale_stock": "FP-32"},
)


# 3 follow-up cadences on distinct leads.
_FOLLOW_UP_LEADS: tuple[dict, ...] = (
    {"lead_name_index": 30, "template": FOLLOW_UP_TEMPLATE_1WK},
    {"lead_name_index": 35, "template": FOLLOW_UP_TEMPLATE_24HR},
    {"lead_name_index": 40, "template": FOLLOW_UP_TEMPLATE_1WK},
)


# 3 be-backs on distinct leads.
_BE_BACKS: tuple[dict, ...] = (
    {"lead_name_index": 32, "reason": BE_BACK_REASON_TEST_DRIVE,
     "days_ago": 2, "state": BE_BACK_STATE_PROMISED},
    {"lead_name_index": 33, "reason": BE_BACK_REASON_BRING_CO_SIGNER,
     "days_ago": 4, "state": BE_BACK_STATE_RETURNED},
    {"lead_name_index": 34, "reason": BE_BACK_REASON_BRING_TRADE_IN,
     "days_ago": 6, "state": BE_BACK_STATE_PROMISED},
)


# Scenario brief slugs (consumed by M18.5 daily briefs).
_SCENARIO_SLUGS: tuple[str, ...] = (
    "owner_capacity_check",
    "sales_manager_pipeline_review",
    "recon_lead_overrun_intervention",
    "office_accounting_close",
    "floor_plan_curtailment_review",
    "advisor_be_back_followup",
)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class FloorPlannedArchetypeBuilder(ArchetypeBuilder):
    """Floor-planned independent-dealer archetype.

    Mid-size independent; auction floor-plan lender; outside-recon
    vendor network; retail-finance-heavy sales mix; **documented
    recon overrun** for the recon-lead scenario brief.
    """

    archetype = _ARCHETYPE

    def build(self, dealership: Dealership) -> ScenarioSummary:
        assert dealership.is_demo, (
            "FloorPlannedArchetypeBuilder.build received a non-demo "
            "Dealership. The registry guards against this — reaching "
            "the builder means a bypass. Broken invariant."
        )

        stock_numbers, staged_vehicles = _seed_inventory(dealership)
        staff_by_slug = _seed_staff(dealership)
        leads_by_lead_index = _seed_leads(
            dealership, staff_by_slug
        )
        vendors_by_slug = _seed_vendors(dealership)
        _seed_recon(dealership, staged_vehicles, vendors_by_slug)
        _seed_sales(dealership)
        _seed_credit_applications(dealership)
        _seed_follow_ups(dealership, leads_by_lead_index)
        _seed_be_backs(dealership, leads_by_lead_index)

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
                f"Floor-planned archetype: {len(stock_numbers)} vehicles, "
                f"{len(_STAFF)} salespeople, {len(_LEADS)} leads, "
                f"{len(_SALES)} sales, "
                f"{len(_RECON_TARGETS)} recon-in-progress (first is "
                "documented overrun anchor), "
                f"{len(_VENDORS)} vendors, "
                f"{len(_CREDIT_APPS)} credit apps, "
                f"{len(_FOLLOW_UP_LEADS)} follow-up cadences, "
                f"{len(_BE_BACKS)} be-backs. "
                "Chargeback deferred per §0.a M18.2 decision 1."
            ),
        )


# ---------------------------------------------------------------------------
# Seeders — mirror retail_subprime shape with M18.3-specific specs
# ---------------------------------------------------------------------------


def _seed_inventory(
    dealership: Dealership,
) -> tuple[list[str], dict[str, Vehicle]]:
    stock_numbers: list[str] = []
    staged: dict[str, Vehicle] = {}
    now = timezone.now()
    for index, spec in enumerate(_INVENTORY):
        stock = str(spec["stock"])
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

        # Auction-heavy for a floor-planned dealer.
        source = SOURCE_AUCTION if index % 4 != 3 else SOURCE_TRADE
        VehicleAcquisition.objects.create(
            dealership=dealership,
            vehicle=vehicle,
            source=source,
            purchase_price=Decimal(spec["cost_basis"]),
            purchase_date=(now - dt.timedelta(days=45 + index)).date(),
            source_detail=(
                "Manheim SoCal, lane 4" if source == SOURCE_AUCTION
                else f"Trade-in from prior deal, ref #{index:03d}"
            ),
        )

        ensure_current_stage(
            vehicle,
            dealership=dealership,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
        )
    return stock_numbers, staged


def _seed_staff(dealership: Dealership) -> dict[str, Salesperson]:
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


def _seed_leads(
    dealership: Dealership,
    staff_by_slug: dict[str, Salesperson],
) -> dict[int, CustomerLead]:
    result: dict[int, CustomerLead] = {}
    now = timezone.now()
    for index, spec in enumerate(_LEADS):
        name_index = int(spec["name_index"])
        name = SYNTHETIC_NAMES[name_index % len(SYNTHETIC_NAMES)]
        assigned_slug = spec.get("assigned_to_slug")
        lead = CustomerLead.objects.create(
            dealership=dealership,
            name=name,
            email=synthetic_email(name),
            phone=synthetic_phone(name_index),
            urgency=str(spec["urgency"]),
            channel=str(spec["channel"]),
            assigned_to=(
                staff_by_slug[str(assigned_slug)]
                if assigned_slug is not None
                else None
            ),
            created_at=now - dt.timedelta(hours=6 + index * 3),
        )
        result[name_index] = lead
    return result


def _seed_vendors(dealership: Dealership) -> dict[str, Vendor]:
    """Create the 4 shared demo vendors — one per major recon
    category."""
    result: dict[str, Vendor] = {}
    for spec in _VENDORS:
        slug = str(spec["slug"])
        vendor = Vendor.objects.create(
            dealership=dealership,
            name=str(spec["name"]),
            slug=slug,
            categories=list(spec["categories"]),
            phone=synthetic_phone(int(spec["name_index"])),
            email=synthetic_email(str(spec["name"])),
            is_active=True,
        )
        result[slug] = vendor
    return result


def _seed_recon(
    dealership: Dealership,
    staged: dict[str, Vehicle],
    vendors_by_slug: dict[str, Vendor],
) -> None:
    """Set 5 vehicles into recon.

    The **first** target is the documented overrun anchor:
    WorkOrder.authorized_cost < WorkOrder.actual_cost by $600+,
    VehicleCost total exceeds baseline recon budget, and a short
    VendorCommunication history documents the escalation.
    """
    now = timezone.now()
    inspector_names = tuple(
        SYNTHETIC_NAMES[i] for i in (37, 38, 39, 25, 26)
    )
    mechanical = vendors_by_slug["sunset-mechanical"]

    for offset, stock in enumerate(_RECON_TARGETS):
        vehicle = staged[stock]
        is_overrun_anchor = offset == 0

        # Rewrite lifecycle stage.
        stage = VehicleStage.objects.get(vehicle=vehicle)
        acquired_at = now - dt.timedelta(days=14 + offset * 2)
        stage.current_stage = VEHICLE_STAGE_RECON
        stage.entered_at = now - dt.timedelta(days=6 + offset)
        stage.trigger = VEHICLE_STAGE_TRIGGER_MANUAL
        stage.save(
            update_fields=["current_stage", "entered_at", "trigger"]
        )
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

        # ConditionReport + findings.
        report = ConditionReport.objects.create(
            dealership=dealership,
            vehicle=vehicle,
            inspector_name=inspector_names[offset],
            inspected_at=acquired_at + dt.timedelta(days=1),
            mileage_at_inspection=vehicle.mileage,
            status=CONDITION_REPORT_STATUS_COMPLETE,
            completed_at=acquired_at + dt.timedelta(days=1, hours=2),
        )
        if is_overrun_anchor:
            # Two mechanical findings that combine to justify the
            # overrun. The estimates are DOCUMENTATION; the actual
            # spend below dwarfs them.
            f_a = ConditionFinding.objects.create(
                dealership=dealership, report=report,
                category=CONDITION_CATEGORY_MECHANICAL,
                severity=CONDITION_SEVERITY_REQUIRED,
                description=(
                    "Transmission slipping under load; suspect "
                    "torque converter — inspect + estimate."
                ),
                estimated_cost=Decimal("450.00"),
            )
            f_b = ConditionFinding.objects.create(
                dealership=dealership, report=report,
                category=CONDITION_CATEGORY_BODY,
                severity=CONDITION_SEVERITY_RECOMMENDED,
                description=(
                    "Rear bumper scuff + minor cosmetic on driver "
                    "door — buff and touch-up."
                ),
                estimated_cost=Decimal("175.00"),
            )
            findings = [f_a, f_b]
        else:
            f_a = ConditionFinding.objects.create(
                dealership=dealership, report=report,
                category=CONDITION_CATEGORY_MECHANICAL,
                severity=CONDITION_SEVERITY_REQUIRED,
                description=(
                    f"Front brakes at 3mm — pads + rotors "
                    f"(recon target {offset})."
                ),
                estimated_cost=Decimal("380.00"),
            )
            f_b = ConditionFinding.objects.create(
                dealership=dealership, report=report,
                category=CONDITION_CATEGORY_TIRES,
                severity=CONDITION_SEVERITY_RECOMMENDED,
                description=(
                    "Two rear tires below 4/32 tread depth."
                ),
                estimated_cost=Decimal("420.00"),
            )
            findings = [f_a, f_b]
        for finding in findings:
            ReconDecision.objects.create(
                dealership=dealership, finding=finding,
                tier=(
                    RECON_DECISION_TIER_MUST_DO
                    if finding.severity == CONDITION_SEVERITY_REQUIRED
                    else RECON_DECISION_TIER_SHOULD_DO
                ),
                decided_at=acquired_at + dt.timedelta(days=1, hours=3),
            )

        # WorkOrder + parts.
        approved_at = acquired_at + dt.timedelta(days=2)
        started_at = acquired_at + dt.timedelta(days=2, hours=4)
        if is_overrun_anchor:
            # Budget: $600 authorized; actual came in >$1,400 →
            # $800+ overrun. The tester walking the M18.5 recon-lead
            # brief discovers this by cross-checking authorized vs
            # actual on the WorkOrder detail view + reconciling
            # against the VehicleCost total.
            authorized_cost = Decimal("600.00")
            actual_cost = Decimal("1425.00")
        else:
            authorized_cost = Decimal("800.00")
            actual_cost = None  # not yet completed
        work_order = WorkOrder.objects.create(
            dealership=dealership,
            vehicle=vehicle,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue="outsourced",
            vendor=mechanical,
            status="in_progress",
            approved_at=approved_at,
            started_at=started_at,
            authorized_cost=authorized_cost,
            actual_cost=actual_cost,
        )
        WorkOrderFinding.objects.create(
            dealership=dealership,
            work_order=work_order, finding=findings[0],
        )
        WorkOrderPart.objects.create(
            dealership=dealership, work_order=work_order,
            name=(
                "Torque converter (rebuilt)"
                if is_overrun_anchor
                else "Front brake pad set"
            ),
            quantity=1, status="installed",
            source_type="online",
            unit_cost=(
                Decimal("485.00") if is_overrun_anchor
                else Decimal("120.00")
            ),
        )
        WorkOrderPart.objects.create(
            dealership=dealership, work_order=work_order,
            name=(
                "Transmission cooler upgrade"
                if is_overrun_anchor
                else "Front rotor pair"
            ),
            quantity=1, status="installed",
            source_type="online",
            unit_cost=(
                Decimal("225.00") if is_overrun_anchor
                else Decimal("180.00")
            ),
        )

        # VehicleCost rows.
        posted_at = acquired_at + dt.timedelta(days=3)
        if is_overrun_anchor:
            # Overrun costs: parts + heavy labor. Total = $1,425.
            costs = (
                (CATEGORY_PARTS, Decimal("710.00"), "Transmission parts"),
                (CATEGORY_MECHANICAL_LABOR, Decimal("560.00"), "Trans R&R labor"),
                (CATEGORY_BODY_WORK, Decimal("155.00"), "Cosmetic touch-up"),
            )
        else:
            costs = (
                (CATEGORY_PARTS, Decimal("300.00"), "Brake parts"),
                (CATEGORY_MECHANICAL_LABOR, Decimal("220.00"), "Brake labor"),
                (CATEGORY_TIRES, Decimal("420.00"), "Rear tires"),
                (CATEGORY_DETAIL, Decimal("85.00"), "Recon-out detail"),
            )
        for cat, amount, ref in costs:
            VehicleCost.objects.create(
                dealership=dealership, vehicle=vehicle,
                category=cat, amount=amount,
                incurred_at=posted_at,
                vendor=mechanical.name if cat != CATEGORY_DETAIL else "in-house detail bay",
                reference=f"WO-{work_order.pk}-{ref}",
                is_estimate=False, posted_at=posted_at,
            )

        # VendorCommunication rows — only on the overrun anchor.
        if is_overrun_anchor:
            VendorCommunication.objects.create(
                dealership=dealership,
                vendor=mechanical,
                work_order=work_order,
                kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
                channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
                direction=VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
                status=VENDOR_COMMUNICATION_STATUS_SENT,
                sent_content=(
                    f"Approving initial estimate ($600) for {vehicle.stock_number} "
                    "transmission inspection. Please advise ASAP if teardown "
                    "reveals additional labor beyond the estimate."
                ),
                approved_at=approved_at + dt.timedelta(hours=2),
                sent_at=approved_at + dt.timedelta(hours=3),
            )
            VendorCommunication.objects.create(
                dealership=dealership,
                vendor=mechanical,
                work_order=work_order,
                kind=VENDOR_COMMUNICATION_KIND_NARRATIVE,
                channel=VENDOR_COMMUNICATION_CHANNEL_PHONE,
                direction=VENDOR_COMMUNICATION_DIRECTION_INBOUND,
                status=VENDOR_COMMUNICATION_STATUS_LOGGED,
                draft_content=(
                    f"Phone call from Sunset Mechanical: torque converter "
                    f"internals damaged, requires full rebuild + cooler "
                    f"upgrade. Revised estimate $1,425 — $800+ over the "
                    f"authorized $600. Recon lead approved verbally; work "
                    f"proceeding. Follow up in writing tomorrow."
                ),
                sent_at=approved_at + dt.timedelta(days=1, hours=4),
            )


def _seed_sales(dealership: Dealership) -> None:
    now = timezone.now()
    for spec in _SALES:
        stock = str(spec["stock"])
        vehicle = Vehicle.objects.get(
            dealership=dealership, stock_number=stock
        )
        sale_date = (
            now - dt.timedelta(days=int(spec["days_ago"]))
        ).date()
        cost_posted_at = now - dt.timedelta(days=int(spec["days_ago"]) + 25)
        VehicleCost.objects.create(
            dealership=dealership, vehicle=vehicle,
            category=CATEGORY_PARTS, amount=Decimal(spec["cost_basis"]),
            incurred_at=cost_posted_at,
            vendor=f"Auction basis for {stock}",
            reference=f"ACQ-{stock}", is_estimate=False,
            posted_at=cost_posted_at,
        )
        buyer_name = SYNTHETIC_NAMES[
            int(spec["buyer_name_index"]) % len(SYNTHETIC_NAMES)
        ]
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
        record_sale(
            vehicle,
            dealership=dealership,
            sale_date=sale_date,
            sold_price=Decimal(spec["sold_price"]),
            finance_type=str(spec["finance"]),
            buyer=buyer,
            lender_name=str(spec.get("lender", "")),
        )


def _seed_credit_applications(dealership: Dealership) -> None:
    from ....models import Sale

    for spec in _CREDIT_APPS:
        applicant_name = SYNTHETIC_NAMES[
            int(spec["applicant_name_index"]) % len(SYNTHETIC_NAMES)
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
                f"Floor-planned dealer routing: {sale.lender_name}. "
                "Standard retail-finance workflow."
            ),
        )


def _seed_follow_ups(
    dealership: Dealership,
    leads_by_lead_index: dict[int, CustomerLead],
) -> None:
    for spec in _FOLLOW_UP_LEADS:
        target_index = int(spec["lead_name_index"])
        lead: Optional[CustomerLead] = leads_by_lead_index.get(target_index)
        if lead is None:
            continue
        start_cadence(
            dealership=dealership,
            lead=lead,
            template=str(spec["template"]),
        )


def _seed_be_backs(
    dealership: Dealership,
    leads_by_lead_index: dict[int, CustomerLead],
) -> None:
    now = timezone.now()
    for spec in _BE_BACKS:
        target_index = int(spec["lead_name_index"])
        lead: Optional[CustomerLead] = leads_by_lead_index.get(target_index)
        if lead is None:
            continue
        promised_at = now - dt.timedelta(days=int(spec["days_ago"]))
        actual_return_at = (
            promised_at + dt.timedelta(days=1, hours=6)
            if spec["state"] == BE_BACK_STATE_RETURNED
            else None
        )
        BeBack.objects.create(
            dealership=dealership,
            lead=lead,
            promised_at=promised_at,
            promised_reason=str(spec["reason"]),
            actual_return_at=actual_return_at,
            state=str(spec["state"]),
        )
