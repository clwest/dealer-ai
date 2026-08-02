"""Milestone 18 · Increment 4 (SESSION_150) — BHPH archetype.

Per MILESTONE_18_PLANNING.md §7 M18.4. Small BHPH dealership; low-
priced reliable-transportation inventory; active portfolio of ~30
notes across aging buckets; ~150 payment history rows; 3 promise-
to-pay entries in various states; 5 collection contacts across
channels; 1 recovered repossession; recent payments intentionally
left with ``posted_at=NULL`` so the M16.1 detector at 11:00 daily
picks them up on next run.

**The M16 detector-eligibility anchor.** ~5 of the ~150 seeded
payments are within 24 hours of ``build()`` time with
``posted_at=NULL``. The M16.1 detector filters
``posted_at__isnull=True`` per §5.d Option A; those recent
payments will post into the GL on the next 11:00 detector cycle.
The remaining ~145 historical payments have ``posted_at``
populated (already-detected). Testers walking the accounting-role
daily brief at M18.5 see this timing dynamic — the trial-balance
surface changes after the 11:00 cycle.

**§0.a M18.2 decision 1 continues to apply.** Chargeback still
deferred.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Optional

from django.contrib.auth import get_user_model
from django.utils import timezone

from ....models import (
    BHPH_CONTACT_CHANNEL_LETTER,
    BHPH_CONTACT_CHANNEL_PHONE,
    BHPH_CONTACT_CHANNEL_SMS,
    BHPH_CONTACT_OUTCOME_CONTACT_MADE,
    BHPH_CONTACT_OUTCOME_LEFT_MESSAGE,
    BHPH_CONTACT_OUTCOME_NO_ANSWER,
    BHPH_PAYMENT_FREQUENCY_BIWEEKLY,
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_PAYMENT_METHOD_ACH,
    BHPH_PAYMENT_METHOD_CASH,
    BHPH_PAYMENT_METHOD_DEBIT,
    BHPH_PROMISE_REASON_FAMILY_HELP,
    BHPH_PROMISE_REASON_PAYCHECK,
    BHPH_PROMISE_REASON_TAX_REFUND,
    BHPH_PROMISE_STATE_BROKEN,
    BHPH_PROMISE_STATE_KEPT,
    BHPH_PROMISE_STATE_PROMISED,
    BHPH_REPO_STATE_RECOVERED,
    DEMO_ARCHETYPE_BHPH,
    FOLLOW_UP_TEMPLATE_24HR,
    FOLLOW_UP_TEMPLATE_1WK,
    LEAD_CHANNEL_CHAT,
    LEAD_CHANNEL_PHONE,
    LEAD_CHANNEL_WALK_IN,
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_BHPH,
    SOURCE_AUCTION,
    SOURCE_PRIVATE,
    SOURCE_WHOLESALE,
    VEHICLE_STAGE_FRONTLINE,
    BhphNote,
    BhphPayment,
    BhphPromiseToPay,
    CollectionContact,
    CustomerLead,
    Dealership,
    Repossession,
    Salesperson,
    UserDealershipRole,
    Vehicle,
    VehicleAcquisition,
)
from ...bhph_notes.bhph_note import record_bhph_note
from ...bhph_payments.bhph_payment import record_payment
from ...bhph_promises.bhph_promise import mark_kept, record_promise
from ...collection_contacts.collection_contact import record_contact
from ...follow_ups.cadence import start_cadence
from ...repossessions.repossession import (
    mark_recovered,
    record_repossession,
)
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

_ARCHETYPE = DEMO_ARCHETYPE_BHPH


# ---------------------------------------------------------------------------
# Fixed specs — deterministic reset
# ---------------------------------------------------------------------------

# 25 vehicles. BHPH mental model: $4k-$12k, older, higher mileage,
# reliable transportation. Stock numbers BH-01..BH-25.
_INVENTORY: tuple[dict, ...] = (
    # Sedans (12) — the transportation core.
    {"stock": "BH-01", "year": 2013, "make": "Toyota", "model": "Camry",
     "trim": "LE", "body": "car", "price": "8995",
     "mileage": 158000, "cost_basis": "6500"},
    {"stock": "BH-02", "year": 2014, "make": "Honda", "model": "Accord",
     "trim": "LX", "body": "car", "price": "9495",
     "mileage": 148000, "cost_basis": "6900"},
    {"stock": "BH-03", "year": 2012, "make": "Toyota", "model": "Corolla",
     "trim": "LE", "body": "car", "price": "7495",
     "mileage": 168000, "cost_basis": "5400"},
    {"stock": "BH-04", "year": 2013, "make": "Honda", "model": "Civic",
     "trim": "LX", "body": "car", "price": "7995",
     "mileage": 152000, "cost_basis": "5800"},
    {"stock": "BH-05", "year": 2011, "make": "Nissan", "model": "Altima",
     "trim": "S", "body": "car", "price": "6495",
     "mileage": 178000, "cost_basis": "4700"},
    {"stock": "BH-06", "year": 2014, "make": "Nissan", "model": "Sentra",
     "trim": "SV", "body": "car", "price": "6995",
     "mileage": 138000, "cost_basis": "5100"},
    {"stock": "BH-07", "year": 2012, "make": "Ford", "model": "Fusion",
     "trim": "SE", "body": "car", "price": "6295",
     "mileage": 172000, "cost_basis": "4500"},
    {"stock": "BH-08", "year": 2013, "make": "Chevrolet",
     "model": "Cruze", "trim": "LT", "body": "car",
     "price": "5495", "mileage": 168000, "cost_basis": "3900"},
    {"stock": "BH-09", "year": 2014, "make": "Hyundai",
     "model": "Elantra", "trim": "SE", "body": "car",
     "price": "5995", "mileage": 148000, "cost_basis": "4300"},
    {"stock": "BH-10", "year": 2015, "make": "Kia", "model": "Forte",
     "trim": "LX", "body": "car", "price": "6295",
     "mileage": 132000, "cost_basis": "4500"},
    {"stock": "BH-11", "year": 2010, "make": "Toyota", "model": "Camry",
     "trim": "LE", "body": "car", "price": "4995",
     "mileage": 198000, "cost_basis": "3500"},
    {"stock": "BH-12", "year": 2015, "make": "Ford", "model": "Focus",
     "trim": "SE", "body": "car", "price": "5495",
     "mileage": 138000, "cost_basis": "3900"},
    # SUVs (8).
    {"stock": "BH-13", "year": 2013, "make": "Ford", "model": "Escape",
     "trim": "SE", "body": "suv", "price": "9995",
     "mileage": 148000, "cost_basis": "7200"},
    {"stock": "BH-14", "year": 2011, "make": "Toyota", "model": "RAV4",
     "trim": "Base", "body": "suv", "price": "8995",
     "mileage": 168000, "cost_basis": "6500"},
    {"stock": "BH-15", "year": 2014, "make": "Chevrolet",
     "model": "Equinox", "trim": "LT", "body": "suv",
     "price": "9995", "mileage": 142000, "cost_basis": "7200"},
    {"stock": "BH-16", "year": 2012, "make": "Honda", "model": "CR-V",
     "trim": "LX", "body": "suv", "price": "8995",
     "mileage": 158000, "cost_basis": "6500"},
    {"stock": "BH-17", "year": 2013, "make": "Nissan", "model": "Rogue",
     "trim": "S", "body": "suv", "price": "7995",
     "mileage": 156000, "cost_basis": "5800"},
    {"stock": "BH-18", "year": 2010, "make": "Ford", "model": "Escape",
     "trim": "XLT", "body": "suv", "price": "6495",
     "mileage": 178000, "cost_basis": "4700"},
    {"stock": "BH-19", "year": 2011, "make": "Chevrolet", "model": "Malibu",
     "trim": "LT", "body": "car", "price": "5495",
     "mileage": 168000, "cost_basis": "3900"},
    {"stock": "BH-20", "year": 2013, "make": "Kia", "model": "Sportage",
     "trim": "LX", "body": "suv", "price": "7495",
     "mileage": 152000, "cost_basis": "5400"},
    # Trucks + minivans (5).
    {"stock": "BH-21", "year": 2010, "make": "Chevrolet",
     "model": "Silverado 1500", "trim": "LT", "body": "truck",
     "price": "10995", "mileage": 168000, "cost_basis": "7900"},
    {"stock": "BH-22", "year": 2012, "make": "Ford", "model": "F-150",
     "trim": "XL", "body": "truck", "price": "11995",
     "mileage": 158000, "cost_basis": "8600"},
    {"stock": "BH-23", "year": 2011, "make": "Toyota", "model": "Tacoma",
     "trim": "Base", "body": "truck", "price": "11995",
     "mileage": 168000, "cost_basis": "8600"},
    {"stock": "BH-24", "year": 2013, "make": "Dodge", "model": "Grand Caravan",
     "trim": "SE", "body": "van", "price": "6995",
     "mileage": 158000, "cost_basis": "5100"},
    {"stock": "BH-25", "year": 2012, "make": "Honda", "model": "Odyssey",
     "trim": "LX", "body": "van", "price": "8495",
     "mileage": 148000, "cost_basis": "6100"},
)


# 4 staff — owner + sales manager + 2 collectors (collectors get
# advisor role for admin access; the collector-vs-advisor
# distinction is a scenario-brief concern, not a role-vocab one).
_STAFF: tuple[dict, ...] = (
    {"slug": "owner-blake", "name_index": 10, "role": ROLE_DEALER_OWNER,
     "is_collector": False},
    {"slug": "sm-cameron", "name_index": 11, "role": ROLE_SALES_MANAGER,
     "is_collector": False},
    {"slug": "coll-drew", "name_index": 12, "role": ROLE_ADVISOR,
     "is_collector": True},
    {"slug": "coll-emerson", "name_index": 13, "role": ROLE_ADVISOR,
     "is_collector": True},
)


# 10 active pipeline leads (BHPH shoppers).
_LEADS: tuple[dict, ...] = tuple(
    {
        "name_index": 30 + i,
        "urgency": ("immediate", "this_week")[i % 2],
        "channel": (
            LEAD_CHANNEL_WALK_IN,
            LEAD_CHANNEL_CHAT,
            LEAD_CHANNEL_PHONE,
        )[i % 3],
        "assigned_to_slug": (
            "coll-drew" if i % 2 == 0 else "coll-emerson"
        ),
        "interested": _INVENTORY[i % len(_INVENTORY)]["stock"],
    }
    for i in range(10)
)


# 5 recent BHPH Sales (the current-week originations). Each fires
# M15 sync-sibling GL post + originates a BhphNote via
# record_bhph_note. These add to the ~30 total notes below.
_RECENT_SALES: tuple[dict, ...] = (
    {"stock": "BH-01", "buyer_name_index": 20, "sold_price": "8995",
     "days_ago": 3, "cost_basis": "6500",
     "apr": "22.90", "term_weeks": 104,
     "frequency": BHPH_PAYMENT_FREQUENCY_WEEKLY},
    {"stock": "BH-05", "buyer_name_index": 21, "sold_price": "6495",
     "days_ago": 5, "cost_basis": "4700",
     "apr": "23.90", "term_weeks": 78,
     "frequency": BHPH_PAYMENT_FREQUENCY_BIWEEKLY},
    {"stock": "BH-11", "buyer_name_index": 22, "sold_price": "4995",
     "days_ago": 8, "cost_basis": "3500",
     "apr": "24.90", "term_weeks": 52,
     "frequency": BHPH_PAYMENT_FREQUENCY_WEEKLY},
    {"stock": "BH-19", "buyer_name_index": 23, "sold_price": "5495",
     "days_ago": 11, "cost_basis": "3900",
     "apr": "22.90", "term_weeks": 78,
     "frequency": BHPH_PAYMENT_FREQUENCY_WEEKLY},
    {"stock": "BH-24", "buyer_name_index": 24, "sold_price": "6995",
     "days_ago": 14, "cost_basis": "5100",
     "apr": "23.90", "term_weeks": 78,
     "frequency": BHPH_PAYMENT_FREQUENCY_BIWEEKLY},
)


# The portfolio is ~30 total notes. Recent sales (5) originate
# above via record_sale + record_bhph_note. The remaining ~25
# historical notes are seeded via direct-create below without
# going through record_sale for scenario-authored reasons
# (see _seed_historical_notes docstring).
_HISTORICAL_NOTE_SPECS: tuple[dict, ...] = tuple(
    {
        "buyer_name_index": 35 + (i % (len(SYNTHETIC_NAMES) - 35)),
        "principal": Decimal(
            ["6500", "7200", "5800", "8600", "5100",
             "6500", "4700", "5400", "3900", "5800",
             "6900", "7200", "8600", "6500", "5100",
             "4700", "3900", "5400", "6500", "5100",
             "4700", "3900", "5800", "6100", "5400"][i]
        ),
        "apr": Decimal(("22.90", "23.90", "24.90")[i % 3]),
        "term_weeks": (78, 104, 52)[i % 3],
        "frequency": (
            BHPH_PAYMENT_FREQUENCY_WEEKLY
            if i % 3 != 1
            else BHPH_PAYMENT_FREQUENCY_BIWEEKLY
        ),
        # Loan age in weeks — spread across the portfolio for aging
        # bucket coverage (fresh 1-4 weeks, current 5-20, past-due
        # 25-40).
        "loan_age_weeks": (2, 6, 12, 18, 26, 32, 8, 4, 14, 20)[i % 10] + i // 10,
        # Aging bucket: current / 30-day past-due / 60-day past-due.
        "aging_bucket": ("current", "past_due_30", "past_due_60")[i % 3],
    }
    for i in range(25)
)


# 3 promise-to-pay records: 1 promised (open), 1 kept
# (reconciled with a real BhphPayment), 1 broken.
_PROMISES: tuple[dict, ...] = (
    {"note_index": 3, "days_ago": 1, "amount": "150.00",
     "reason": BHPH_PROMISE_REASON_PAYCHECK,
     "final_state": BHPH_PROMISE_STATE_PROMISED},
    {"note_index": 7, "days_ago": 12, "amount": "200.00",
     "reason": BHPH_PROMISE_REASON_TAX_REFUND,
     "final_state": BHPH_PROMISE_STATE_KEPT},
    {"note_index": 13, "days_ago": 21, "amount": "120.00",
     "reason": BHPH_PROMISE_REASON_FAMILY_HELP,
     "final_state": BHPH_PROMISE_STATE_BROKEN},
)


# 5 collection-contact records across channels + outcomes.
_COLLECTION_CONTACTS: tuple[dict, ...] = (
    {"note_index": 5, "days_ago": 2,
     "channel": BHPH_CONTACT_CHANNEL_PHONE,
     "outcome": BHPH_CONTACT_OUTCOME_CONTACT_MADE},
    {"note_index": 8, "days_ago": 4,
     "channel": BHPH_CONTACT_CHANNEL_PHONE,
     "outcome": BHPH_CONTACT_OUTCOME_LEFT_MESSAGE},
    {"note_index": 11, "days_ago": 7,
     "channel": BHPH_CONTACT_CHANNEL_SMS,
     "outcome": BHPH_CONTACT_OUTCOME_NO_ANSWER},
    {"note_index": 14, "days_ago": 10,
     "channel": BHPH_CONTACT_CHANNEL_LETTER,
     "outcome": BHPH_CONTACT_OUTCOME_LEFT_MESSAGE},
    {"note_index": 20, "days_ago": 3,
     "channel": BHPH_CONTACT_CHANNEL_PHONE,
     "outcome": BHPH_CONTACT_OUTCOME_CONTACT_MADE},
)


# 1 recovered repossession — targets a note that fell 60+ days past
# due. Ordered 21 days ago; recovered 12 days ago.
_REPOSSESSION_NOTE_INDEX = 17


# 2 follow-up cadences on distinct leads.
_FOLLOW_UP_LEADS: tuple[dict, ...] = (
    {"lead_name_index": 30, "template": FOLLOW_UP_TEMPLATE_1WK},
    {"lead_name_index": 33, "template": FOLLOW_UP_TEMPLATE_24HR},
)


# Scenario brief slugs consumed by M18.5 daily briefs.
_SCENARIO_SLUGS: tuple[str, ...] = (
    "owner_portfolio_health",
    "bhph_collector_daily_book",
    "bhph_promise_followup",
    "office_accounting_close",
    "repo_intake_handoff",
    "nsf_response_workflow",
)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class BhphArchetypeBuilder(ArchetypeBuilder):
    """BHPH archetype — small buy-here-pay-here dealership.

    Active portfolio of ~30 notes across aging buckets, ~150+
    payment history, promise-to-pay + collection-contact rows,
    1 recovered repossession, and recent payments left with
    ``posted_at=NULL`` so the M16.1 daily detector picks them up
    on next run.
    """

    archetype = _ARCHETYPE

    def build(self, dealership: Dealership) -> ScenarioSummary:
        assert dealership.is_demo, (
            "BhphArchetypeBuilder.build received a non-demo "
            "Dealership. The registry guards against this — reaching "
            "the builder means a bypass. Broken invariant."
        )

        stock_numbers, staged_vehicles = _seed_inventory(dealership)
        staff_by_slug = _seed_staff(dealership)
        _seed_leads(dealership, staff_by_slug)
        recent_notes = _seed_recent_sales(
            dealership, staged_vehicles
        )
        historical_notes = _seed_historical_notes(dealership)
        payment_stats = _seed_historical_payments(
            dealership, historical_notes + recent_notes
        )
        _seed_promises(dealership, historical_notes)
        _seed_collection_contacts(
            dealership, historical_notes,
            staff_by_slug.get("coll-drew"),
        )
        _seed_repossession(
            dealership, historical_notes,
            staff_by_slug.get("owner-blake"),
        )
        _seed_follow_ups(dealership)

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
                f"BHPH archetype: {len(stock_numbers)} vehicles, "
                f"{len(_STAFF)} salespeople (2 collectors), "
                f"{len(_LEADS)} leads, "
                f"{len(_RECENT_SALES)} recent BHPH sales, "
                f"{len(historical_notes) + len(recent_notes)} active notes, "
                f"{payment_stats['total']} payment rows "
                f"({payment_stats['unposted']} unposted for M16 detector), "
                f"{len(_PROMISES)} promise-to-pay, "
                f"{len(_COLLECTION_CONTACTS)} collection contacts, "
                "1 recovered repossession. "
                "Chargeback deferred per §0.a M18.2 decision 1."
            ),
        )


# ---------------------------------------------------------------------------
# Seeders
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
        # Sourcing mix per BHPH persona: wholesale + auction.
        source = (
            SOURCE_WHOLESALE if index % 3 == 0
            else (SOURCE_AUCTION if index % 3 == 1 else SOURCE_PRIVATE)
        )
        VehicleAcquisition.objects.create(
            dealership=dealership,
            vehicle=vehicle,
            source=source,
            purchase_price=Decimal(spec["cost_basis"]),
            purchase_date=(now - dt.timedelta(days=45 + index * 2)).date(),
            source_detail=f"{source[:3].upper()}-{index:03d}",
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
            created_at=now - dt.timedelta(hours=6 + index * 4),
        )
        result[name_index] = lead
    return result


def _seed_recent_sales(
    dealership: Dealership,
    staged: dict[str, Vehicle],
) -> list[BhphNote]:
    """Origin ate 5 recent BHPH sales via record_sale (fires M15 GL)
    + record_bhph_note. Returns the resulting BhphNote list."""
    from ....models import CATEGORY_PARTS, VehicleCost

    now = timezone.now()
    notes: list[BhphNote] = []
    for spec in _RECENT_SALES:
        stock = str(spec["stock"])
        vehicle = staged[stock]
        sale_date = (
            now - dt.timedelta(days=int(spec["days_ago"]))
        ).date()
        cost_posted_at = now - dt.timedelta(days=int(spec["days_ago"]) + 20)
        VehicleCost.objects.create(
            dealership=dealership, vehicle=vehicle,
            category=CATEGORY_PARTS, amount=Decimal(spec["cost_basis"]),
            incurred_at=cost_posted_at,
            vendor=f"Acquisition basis for {stock}",
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
            created_at=now - dt.timedelta(days=int(spec["days_ago"]) + 1),
        )
        sale = record_sale(
            vehicle,
            dealership=dealership,
            sale_date=sale_date,
            sold_price=Decimal(spec["sold_price"]),
            finance_type=SALE_FINANCE_TYPE_BHPH,
            buyer=buyer,
            lender_name="",
        )
        note = record_bhph_note(
            dealership=dealership,
            sale=sale,
            principal_financed=Decimal(spec["sold_price"]),
            apr=Decimal(spec["apr"]),
            term_weeks=int(spec["term_weeks"]),
            payment_frequency=str(spec["frequency"]),
            first_payment_due=sale_date + dt.timedelta(days=7),
        )
        notes.append(note)
    return notes


def _seed_historical_notes(
    dealership: Dealership,
) -> list[BhphNote]:
    """Directly create 25 historical BhphNotes without going through
    record_sale (scenario doesn't require the corresponding Sale +
    Vehicle audit trail — the portfolio surface is what matters).

    Each note gets a synthetic buyer CustomerLead so the collector
    daily brief can reference the customer name.
    """
    from ....models import (
        SALE_FINANCE_TYPE_BHPH,
        BhphNote,
        Sale,
    )
    from ...payment_engine import bhph_note_periodic_payment

    now = timezone.now()
    notes: list[BhphNote] = []

    # For historical notes we still need a Sale row (BhphNote FK is
    # to Sale). But to keep the coherence contract honest without
    # exploding the Vehicle count, we cycle the historical notes
    # onto the newer inventory as if those units had been sold a
    # long time ago. That would conflict with the 5 recent-sale
    # vehicles + the M9 OneToOne(Vehicle). So we allocate the
    # remaining 20 vehicles to historical notes and create 5
    # additional "historical" vehicles (BH-H-01..BH-H-05) that
    # exist purely for historical BhphNote origination.

    # Available inventory for historical: skip the 5 recent-sale
    # stocks + any recon (none in this archetype) — 20 available.
    used_stocks = {spec["stock"] for spec in _RECENT_SALES}
    available_vehicles = [
        vehicle for vehicle in Vehicle.objects.filter(
            dealership=dealership
        ).order_by("stock_number")
        if vehicle.stock_number not in used_stocks
        and not Sale.objects.filter(vehicle=vehicle).exists()
    ]

    # Create 5 additional historical Vehicles (BH-H-01..BH-H-05)
    # to cover the shortfall between 20 available and 25 historical
    # notes needed.
    for extra_index in range(5):
        stock = f"BH-H-{extra_index + 1:02d}"
        vin = synthetic_vin(_ARCHETYPE, len(_INVENTORY) + extra_index)
        vehicle = Vehicle.objects.create(
            dealership=dealership,
            stock_number=stock,
            vin=vin,
            year=2011 + extra_index,
            make="Toyota",
            model="Camry",
            trim="LE",
            body_style="car",
            condition="used",
            mileage=170000 + extra_index * 5000,
            price=Decimal("5500.00"),
            fuel_type="Gasoline",
            source=f"demo-{_ARCHETYPE}-historical",
            imported_at=now - dt.timedelta(days=200 + extra_index * 30),
            is_available=False,
        )
        ensure_current_stage(
            vehicle,
            dealership=dealership,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
        )
        available_vehicles.append(vehicle)

    # Create 25 historical Sales + BhphNotes.
    for index, spec in enumerate(_HISTORICAL_NOTE_SPECS):
        vehicle = available_vehicles[index]
        loan_age_weeks = int(spec["loan_age_weeks"])
        sale_date = (now - dt.timedelta(weeks=loan_age_weeks)).date()
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
            created_at=now - dt.timedelta(weeks=loan_age_weeks + 1),
        )
        # Direct Sale.objects.create instead of record_sale — we're
        # backfilling historical closed sales for scenario data, not
        # exercising the M15 sync-sibling GL post for these (they'd
        # create noise in the JournalEntry table without adding
        # scenario value; the 5 recent BHPH sales already exercise
        # M15). Direct-create is legitimate here per §5.d Option A
        # scenarios-are-code posture — the scenario builder chooses
        # which paths to exercise vs bypass, documented explicitly.
        sale = Sale.objects.create(
            dealership=dealership,
            vehicle=vehicle,
            buyer=buyer,
            sale_date=sale_date,
            sold_price=Decimal(spec["principal"]),
            finance_type=SALE_FINANCE_TYPE_BHPH,
            lender_name="",
            gross_realized=Decimal("0.00"),
        )
        # Direct BhphNote.objects.create instead of record_bhph_note
        # because record_bhph_note computes payment_amount and we
        # want to short-circuit that + also skip the "already exists"
        # guard which fires when we retry after test-mode signal
        # re-firing.
        payment_amount = bhph_note_periodic_payment(
            Decimal(spec["principal"]),
            Decimal(spec["apr"]),
            int(spec["term_weeks"]),
            str(spec["frequency"]),
        )
        note = BhphNote.objects.create(
            dealership=dealership,
            sale=sale,
            principal_financed=Decimal(spec["principal"]),
            apr=Decimal(spec["apr"]),
            term_weeks=int(spec["term_weeks"]),
            payment_frequency=str(spec["frequency"]),
            payment_amount=payment_amount,
            first_payment_due=sale_date + dt.timedelta(days=7),
        )
        notes.append(note)
    return notes


def _seed_historical_payments(
    dealership: Dealership,
    notes: list[BhphNote],
) -> dict[str, int]:
    """Seed ~150 BhphPayment rows across the portfolio.

    Payment cadence per note: weekly notes get more payments than
    biweekly. Each note gets 4-8 historical payments (already-
    posted, ``posted_at`` populated) + 0-1 recent unposted payment
    within the last 24 hours (M16 detector-eligible per §5.d Option
    A).

    Returns a stats dict with total + unposted counts for the
    ScenarioSummary notes field.
    """
    now = timezone.now()
    total = 0
    unposted = 0
    for note_index, note in enumerate(notes):
        # Number of historical payments: proportional to age but
        # capped so total stays around ~150.
        historical_count = min(6, max(2, note_index // 4 + 3))
        # Weekly cadence = 7 days, biweekly = 14, semi_monthly ~15.
        cadence_days = (
            7 if note.payment_frequency == BHPH_PAYMENT_FREQUENCY_WEEKLY
            else 14
        )
        # Historical payments — walked backwards from ~2 weeks ago.
        for tick in range(historical_count):
            paid_at = now - dt.timedelta(
                days=14 + tick * cadence_days,
            )
            method = (
                BHPH_PAYMENT_METHOD_CASH,
                BHPH_PAYMENT_METHOD_DEBIT,
                BHPH_PAYMENT_METHOD_ACH,
            )[tick % 3]
            payment = _create_historical_payment(
                dealership, note, paid_at, note.payment_amount, method
            )
            # Mark posted at the following day's 11:00 detector.
            payment.posted_at = paid_at + dt.timedelta(days=1)
            payment.save(update_fields=["posted_at"])
            total += 1

        # Recent unposted payment — some notes only; pick ~1 in 5
        # so we get ~5 detector-eligible rows.
        if note_index % 5 == 0:
            recent_paid_at = now - dt.timedelta(hours=6)
            _create_historical_payment(
                dealership, note, recent_paid_at,
                note.payment_amount, BHPH_PAYMENT_METHOD_CASH,
            )
            # posted_at stays NULL — the M16.1 detector will pick
            # it up on next 11:00 cycle.
            total += 1
            unposted += 1
    return {"total": total, "unposted": unposted}


def _create_historical_payment(
    dealership: Dealership, note: BhphNote,
    paid_at: dt.datetime, amount: Decimal, method: str,
) -> BhphPayment:
    """Direct BhphPayment.objects.create (bypassing record_payment)
    for historical seed rows.

    ``record_payment`` re-computes the allocation using outstanding
    balance + prior payments. For historical seed we don't want
    that live-recompute chain — we want a stable seed that reset
    reproduces deterministically. So we allocate the payment
    entirely to principal (crude but adequate for the scenario
    surface; the collector daily brief cares about the payment
    existing + its amount + method, not the split precision on
    historical rows).
    """
    return BhphPayment.objects.create(
        dealership=dealership,
        note=note,
        paid_at=paid_at,
        amount=amount,
        method=method,
        applied_to_fees=Decimal("0.00"),
        applied_to_interest=Decimal("0.00"),
        applied_to_principal=amount,
    )


def _seed_promises(
    dealership: Dealership,
    historical_notes: list[BhphNote],
) -> None:
    """Seed 3 PromiseToPay rows across historical notes."""
    now = timezone.now()
    for spec in _PROMISES:
        note_index = int(spec["note_index"])
        if note_index >= len(historical_notes):
            continue
        note = historical_notes[note_index]
        promised_at = now - dt.timedelta(days=int(spec["days_ago"]))
        promise = record_promise(
            dealership=dealership,
            note=note,
            promised_at=promised_at,
            promised_amount=Decimal(spec["amount"]),
            promised_reason=str(spec["reason"]),
        )
        final_state = str(spec["final_state"])
        if final_state == BHPH_PROMISE_STATE_KEPT:
            # Create a fulfilling payment + reconcile.
            payment = _create_historical_payment(
                dealership, note,
                promised_at + dt.timedelta(hours=6),
                Decimal(spec["amount"]),
                BHPH_PAYMENT_METHOD_CASH,
            )
            payment.posted_at = promised_at + dt.timedelta(days=1)
            payment.save(update_fields=["posted_at"])
            mark_kept(
                dealership=dealership,
                promise=promise,
                payment=payment,
            )
        elif final_state == BHPH_PROMISE_STATE_BROKEN:
            promise.state = BHPH_PROMISE_STATE_BROKEN
            promise.save(update_fields=["state"])


def _seed_collection_contacts(
    dealership: Dealership,
    historical_notes: list[BhphNote],
    actor: Optional[Salesperson],
) -> None:
    """Seed 5 CollectionContact rows across channels + outcomes."""
    now = timezone.now()
    actor_user = actor.user if actor is not None else None
    for spec in _COLLECTION_CONTACTS:
        note_index = int(spec["note_index"])
        if note_index >= len(historical_notes):
            continue
        note = historical_notes[note_index]
        contacted_at = now - dt.timedelta(days=int(spec["days_ago"]))
        record_contact(
            dealership=dealership,
            note=note,
            contacted_at=contacted_at,
            channel=str(spec["channel"]),
            outcome=str(spec["outcome"]),
            contacted_by_user=actor_user,
            notes=(
                f"Attempted {spec['channel']} contact re: past-due "
                f"payment. Outcome: {spec['outcome']}."
            ),
        )


def _seed_repossession(
    dealership: Dealership,
    historical_notes: list[BhphNote],
    actor: Optional[Salesperson],
) -> None:
    """Seed 1 recovered repossession on the 60+ day past-due note."""
    if _REPOSSESSION_NOTE_INDEX >= len(historical_notes):
        return
    note = historical_notes[_REPOSSESSION_NOTE_INDEX]
    actor_user = actor.user if actor is not None else None
    now = timezone.now()
    repo = record_repossession(
        dealership=dealership,
        note=note,
        ordered_at=now - dt.timedelta(days=21),
        agent_name="Southwest Recovery Services (demo)",
        ordered_by_user=actor_user,
        notes="60+ day past-due, no promise-to-pay follow-through.",
    )
    mark_recovered(
        dealership=dealership,
        repossession=repo,
        recovered_at=now - dt.timedelta(days=12),
        recovery_location="Home residence, agent arrived at 6am.",
    )


def _seed_follow_ups(dealership: Dealership) -> None:
    """Seed follow-up cadences for a couple of leads."""
    for spec in _FOLLOW_UP_LEADS:
        target_index = int(spec["lead_name_index"])
        name = SYNTHETIC_NAMES[target_index % len(SYNTHETIC_NAMES)]
        lead = CustomerLead.objects.filter(
            dealership=dealership, name=name,
        ).order_by("created_at").first()
        if lead is None:
            continue
        start_cadence(
            dealership=dealership,
            lead=lead,
            template=str(spec["template"]),
        )
