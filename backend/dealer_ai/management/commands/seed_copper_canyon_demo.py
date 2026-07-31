"""SESSION_030 pivot — Copper Canyon Auto (Yuma, AZ) demo inventory.

The invented independent-dealer persona that ships as the kit's
default demo per docs/INDEPENDENT_DEALER_PIVOT.md. 45 mixed-make used
units, $4k–$25k, truck/SUV-heavy, 3–10 yrs old, no OEM feed, no CPO,
no captive finance. Runs alongside :mod:`seed_demo_vehicles` (the
Freedom Ford franchise-config seed); the two are keyed by
``source="copper_canyon_demo"`` and ``source="demo_seed"``
respectively so an admin can load one, the other, or both without
collision.

Idempotent: re-running updates existing units by ``stock_number``
rather than duplicating. Matches the existing seed's contract so the
demo-reset endpoint can wipe / re-seed reliably.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from dealer_ai.models import Vehicle


DEMO_SOURCE = "copper_canyon_demo"


# Shorthand: every unit is used, so we skip repeating condition on each
# dict. The build() helper below fills in condition="used" and any
# other Copper Canyon-wide defaults.
_TRUCKS = [
    {"stock_number": "CC-T-01", "year": 2014, "make": "Toyota", "model": "Tacoma",
     "trim": "SR5 Double Cab 4x4", "price": "16995", "drivetrain": "4x4",
     "mileage": 118000, "engine": "4.0L V6", "fuel_type": "Gasoline",
     "features": ["Tow Package", "Bed Liner"],
     "description": "Well-kept Tacoma with the bulletproof 4.0L V6 and 4x4. "
                    "Solid work-and-play truck for the ag economy."},
    {"stock_number": "CC-T-02", "year": 2016, "make": "Ford", "model": "F-150",
     "trim": "XLT SuperCrew", "price": "18495", "drivetrain": "4x4",
     "mileage": 96000, "engine": "3.5L EcoBoost V6", "fuel_type": "Gasoline",
     "features": ["Tow Package", "Backup Camera", "Bluetooth"],
     "description": "F-150 XLT with the EcoBoost — plenty of tow capacity, "
                    "clean history report available."},
    {"stock_number": "CC-T-03", "year": 2013, "make": "Chevrolet",
     "model": "Silverado 1500", "trim": "LT Crew Cab", "price": "13995",
     "drivetrain": "4x4", "mileage": 142000, "engine": "5.3L V8",
     "fuel_type": "Gasoline",
     "features": ["Tow Package", "Cloth Interior"],
     "description": "Silverado 1500 LT with the 5.3L V8. Ranch- and "
                    "border-town ready."},
    {"stock_number": "CC-T-04", "year": 2018, "make": "Nissan",
     "model": "Frontier", "trim": "SV Crew Cab", "price": "17995",
     "drivetrain": "4x4", "mileage": 84000, "engine": "4.0L V6",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Bluetooth"],
     "description": "Frontier SV — proven V6 midsize truck, well-priced "
                    "against comparable Tacomas."},
    {"stock_number": "CC-T-05", "year": 2015, "make": "GMC",
     "model": "Sierra 1500", "trim": "SLE Double Cab", "price": "15795",
     "drivetrain": "4x4", "mileage": 121000, "engine": "5.3L V8",
     "fuel_type": "Gasoline",
     "features": ["Tow Package", "Alloy Wheels"],
     "description": "Sierra SLE with the 5.3L. Twin to a Silverado at a "
                    "slight discount."},
    {"stock_number": "CC-T-06", "year": 2020, "make": "Ram",
     "model": "1500", "trim": "Big Horn Crew Cab", "price": "24995",
     "drivetrain": "4x4", "mileage": 58000, "engine": "5.7L HEMI V8",
     "fuel_type": "Gasoline",
     "features": ["8.4 Uconnect", "Tow Package", "Sport Appearance"],
     "description": "Newer-gen Ram 1500 Big Horn with the HEMI. Best "
                    "interior in this segment at this price."},
    {"stock_number": "CC-T-07", "year": 2012, "make": "Toyota",
     "model": "Tacoma", "trim": "PreRunner V6 Access Cab", "price": "12495",
     "drivetrain": "RWD", "mileage": 158000, "engine": "4.0L V6",
     "fuel_type": "Gasoline",
     "features": ["Bed Liner"],
     "description": "Older Tacoma PreRunner — 2WD but the same tough "
                    "4.0L V6. Priced to move, great BHPH-friendly unit."},
    {"stock_number": "CC-T-08", "year": 2017, "make": "Ford",
     "model": "F-250 Super Duty", "trim": "XL Regular Cab", "price": "22495",
     "drivetrain": "4x4", "mileage": 89000, "engine": "6.2L V8",
     "fuel_type": "Gasoline",
     "features": ["Work Vinyl", "Tow Package"],
     "description": "Super Duty work truck. Heavy hauling for contractors "
                    "or ag operations."},
    {"stock_number": "CC-T-09", "year": 2019, "make": "Chevrolet",
     "model": "Colorado", "trim": "LT Crew Cab", "price": "19995",
     "drivetrain": "4x4", "mileage": 71000, "engine": "3.6L V6",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Bluetooth", "Bed Liner"],
     "description": "Colorado LT — right-sized truck, easier on fuel than "
                    "a full-size."},
    {"stock_number": "CC-T-10", "year": 2014, "make": "Ford",
     "model": "Ranger", "trim": "XLT SuperCab (Gray-Market)",
     "price": "8995", "drivetrain": "RWD", "mileage": 176000,
     "engine": "4.0L V6", "fuel_type": "Gasoline",
     "features": ["Bed Liner"],
     "description": "Older-gen Ranger — high miles but priced for the "
                    "hard-working buyer. Solid BHPH candidate."},
    {"stock_number": "CC-T-11", "year": 2015, "make": "Nissan",
     "model": "Titan", "trim": "SV Crew Cab", "price": "14995",
     "drivetrain": "4x4", "mileage": 128000, "engine": "5.6L V8",
     "fuel_type": "Gasoline",
     "features": ["Tow Package"],
     "description": "Titan SV — full-size Nissan truck, deals well against "
                    "the Big Three at this price band."},
    {"stock_number": "CC-T-12", "year": 2013, "make": "Ram",
     "model": "1500", "trim": "SLT Quad Cab", "price": "10495",
     "drivetrain": "4x4", "mileage": 149000, "engine": "5.7L HEMI V8",
     "fuel_type": "Gasoline",
     "features": ["Tow Package"],
     "description": "Older Ram 1500 SLT with the HEMI. Great value on the "
                    "cash-and-carry end."},
    {"stock_number": "CC-T-13", "year": 2016, "make": "Toyota",
     "model": "Tundra", "trim": "SR5 CrewMax", "price": "19795",
     "drivetrain": "4x4", "mileage": 108000, "engine": "5.7L V8",
     "fuel_type": "Gasoline",
     "features": ["Tow Package", "Bed Liner"],
     "description": "Tundra CrewMax — the family-hauler full-size Toyota, "
                    "reliability leader in the segment."},
    {"stock_number": "CC-T-14", "year": 2018, "make": "Ford",
     "model": "F-150", "trim": "STX SuperCrew", "price": "18995",
     "drivetrain": "4x4", "mileage": 92000, "engine": "5.0L V8",
     "fuel_type": "Gasoline",
     "features": ["Tow Package", "Alloy Wheels"],
     "description": "F-150 STX with the 5.0L V8. Balanced deal — recent "
                    "year, honest miles."},
]

_SUVS = [
    {"stock_number": "CC-S-01", "year": 2016, "make": "Toyota",
     "model": "RAV4", "trim": "XLE AWD", "price": "14995",
     "drivetrain": "AWD", "mileage": 88000, "engine": "2.5L I-4",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Sunroof"],
     "description": "RAV4 XLE — the segment's reliability benchmark. "
                    "AWD is a nice bonus in the Yuma snowbird crowd."},
    {"stock_number": "CC-S-02", "year": 2018, "make": "Honda",
     "model": "CR-V", "trim": "EX AWD", "price": "16995",
     "drivetrain": "AWD", "mileage": 74000, "engine": "1.5L Turbo I-4",
     "fuel_type": "Gasoline",
     "features": ["Sunroof", "Heated Seats", "Backup Camera"],
     "description": "CR-V EX — arguably the most-requested used SUV on "
                    "any indie lot. Reliable, roomy, easy on fuel."},
    {"stock_number": "CC-S-03", "year": 2014, "make": "Ford",
     "model": "Escape", "trim": "SE FWD", "price": "8995",
     "drivetrain": "FWD", "mileage": 125000, "engine": "1.6L EcoBoost I-4",
     "fuel_type": "Gasoline",
     "features": ["Bluetooth"],
     "description": "Escape SE — affordable compact SUV, good BHPH "
                    "candidate for first-time buyers."},
    {"stock_number": "CC-S-04", "year": 2017, "make": "Chevrolet",
     "model": "Equinox", "trim": "LT FWD", "price": "12795",
     "drivetrain": "FWD", "mileage": 96000, "engine": "2.4L I-4",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Bluetooth", "Cloth Interior"],
     "description": "Equinox LT — practical, spacious compact SUV. "
                    "Priced right for mid-market financing."},
    {"stock_number": "CC-S-05", "year": 2019, "make": "Nissan",
     "model": "Rogue", "trim": "SV AWD", "price": "14495",
     "drivetrain": "AWD", "mileage": 68000, "engine": "2.5L I-4",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Bluetooth", "Heated Seats"],
     "description": "Rogue SV — later-model with lower miles. Popular "
                    "with the border-town commuter set."},
    {"stock_number": "CC-S-06", "year": 2015, "make": "Jeep",
     "model": "Wrangler", "trim": "Sport 4x4 4-Door", "price": "17495",
     "drivetrain": "4x4", "mileage": 102000, "engine": "3.6L V6",
     "fuel_type": "Gasoline",
     "features": ["Removable Top", "Bluetooth"],
     "description": "Wrangler Sport 4-door — desert-town crowd favorite. "
                    "Holds value like nothing else."},
    {"stock_number": "CC-S-07", "year": 2013, "make": "Subaru",
     "model": "Forester", "trim": "2.5i Premium AWD", "price": "9495",
     "drivetrain": "AWD", "mileage": 132000, "engine": "2.5L H-4",
     "fuel_type": "Gasoline",
     "features": ["Sunroof", "Roof Rails"],
     "description": "Forester AWD — practical wagon-SUV, snowbird-ready "
                    "for MI/AZ round trips."},
    {"stock_number": "CC-S-08", "year": 2020, "make": "Toyota",
     "model": "Highlander", "trim": "LE AWD", "price": "23995",
     "drivetrain": "AWD", "mileage": 55000, "engine": "3.5L V6",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Bluetooth", "Third Row Seat"],
     "description": "Highlander LE — three-row family SUV in like-new "
                    "shape. Premium unit on the lot."},
    {"stock_number": "CC-S-09", "year": 2016, "make": "Honda",
     "model": "Pilot", "trim": "EX 8-Passenger", "price": "17995",
     "drivetrain": "AWD", "mileage": 89000, "engine": "3.5L V6",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Third Row Seat", "Heated Seats"],
     "description": "Pilot EX — reliable three-row Honda. Great family "
                    "hauler at this price."},
    {"stock_number": "CC-S-10", "year": 2018, "make": "Ford",
     "model": "Explorer", "trim": "XLT AWD", "price": "19995",
     "drivetrain": "AWD", "mileage": 78000, "engine": "3.5L V6",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Third Row Seat", "Bluetooth"],
     "description": "Explorer XLT — spacious three-row Ford SUV. "
                    "Popular for family-plus-tow duty."},
    {"stock_number": "CC-S-11", "year": 2019, "make": "Chevrolet",
     "model": "Traverse", "trim": "LT AWD", "price": "22495",
     "drivetrain": "AWD", "mileage": 65000, "engine": "3.6L V6",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Third Row Seat", "Bluetooth"],
     "description": "Traverse LT — biggest three-row in this price range. "
                    "Great for large families."},
    {"stock_number": "CC-S-12", "year": 2014, "make": "Jeep",
     "model": "Grand Cherokee", "trim": "Limited 4x4", "price": "11995",
     "drivetrain": "4x4", "mileage": 118000, "engine": "3.6L V6",
     "fuel_type": "Gasoline",
     "features": ["Leather", "Sunroof", "Heated Seats"],
     "description": "Grand Cherokee Limited — leather + sunroof at a "
                    "friendly price point."},
    {"stock_number": "CC-S-13", "year": 2017, "make": "Nissan",
     "model": "Pathfinder", "trim": "S 4x4", "price": "14995",
     "drivetrain": "4x4", "mileage": 94000, "engine": "3.5L V6",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Third Row Seat"],
     "description": "Pathfinder S — three-row Nissan, priced below "
                    "comparable Explorers/Traverses."},
    {"stock_number": "CC-S-14", "year": 2015, "make": "Ford",
     "model": "Edge", "trim": "SEL FWD", "price": "10995",
     "drivetrain": "FWD", "mileage": 111000, "engine": "3.5L V6",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Bluetooth", "Alloy Wheels"],
     "description": "Edge SEL — mid-size SUV with plenty of room. "
                    "Well-optioned for the price."},
    {"stock_number": "CC-S-15", "year": 2018, "make": "Kia",
     "model": "Sorento", "trim": "LX FWD", "price": "13995",
     "drivetrain": "FWD", "mileage": 82000, "engine": "2.4L I-4",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Bluetooth", "Third Row Seat"],
     "description": "Sorento LX — value three-row SUV with Kia's "
                    "reliability track record."},
    {"stock_number": "CC-S-16", "year": 2013, "make": "Hyundai",
     "model": "Santa Fe", "trim": "GLS AWD", "price": "7995",
     "drivetrain": "AWD", "mileage": 134000, "engine": "3.3L V6",
     "fuel_type": "Gasoline",
     "features": ["Bluetooth"],
     "description": "Santa Fe GLS — three-row Hyundai at a cash-buyer "
                    "price point."},
]

_CARS = [
    {"stock_number": "CC-C-01", "year": 2015, "make": "Toyota",
     "model": "Camry", "trim": "LE Sedan", "price": "9995",
     "drivetrain": "FWD", "mileage": 108000, "engine": "2.5L I-4",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Bluetooth"],
     "description": "Camry LE — the used-sedan gold standard. Fair miles, "
                    "clean interior."},
    {"stock_number": "CC-C-02", "year": 2017, "make": "Honda",
     "model": "Civic", "trim": "LX Sedan", "price": "12495",
     "drivetrain": "FWD", "mileage": 85000, "engine": "2.0L I-4",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Bluetooth"],
     "description": "Civic LX — efficient compact, always in demand on the "
                    "used market."},
    {"stock_number": "CC-C-03", "year": 2014, "make": "Honda",
     "model": "Accord", "trim": "Sport Sedan", "price": "10495",
     "drivetrain": "FWD", "mileage": 121000, "engine": "2.4L I-4",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Bluetooth", "Alloy Wheels"],
     "description": "Accord Sport — mid-size Honda with a sportier trim. "
                    "Practical and comfortable."},
    {"stock_number": "CC-C-04", "year": 2016, "make": "Nissan",
     "model": "Altima", "trim": "SV Sedan", "price": "9795",
     "drivetrain": "FWD", "mileage": 98000, "engine": "2.5L I-4",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Bluetooth"],
     "description": "Altima SV — smooth mid-size Nissan sedan at a friendly "
                    "monthly-payment target."},
    {"stock_number": "CC-C-05", "year": 2013, "make": "Chevrolet",
     "model": "Malibu", "trim": "LT Sedan", "price": "6995",
     "drivetrain": "FWD", "mileage": 128000, "engine": "2.5L I-4",
     "fuel_type": "Gasoline",
     "features": ["Bluetooth"],
     "description": "Malibu LT — cash-buyer friendly mid-size. Runs "
                    "clean."},
    {"stock_number": "CC-C-06", "year": 2018, "make": "Hyundai",
     "model": "Elantra", "trim": "SE Sedan", "price": "11495",
     "drivetrain": "FWD", "mileage": 79000, "engine": "2.0L I-4",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Bluetooth"],
     "description": "Elantra SE — later-model compact at a fair price. "
                    "Balance of the factory 10-yr powertrain remaining."},
    {"stock_number": "CC-C-07", "year": 2015, "make": "Ford",
     "model": "Fusion", "trim": "SE Sedan", "price": "7795",
     "drivetrain": "FWD", "mileage": 115000, "engine": "2.5L I-4",
     "fuel_type": "Gasoline",
     "features": ["Bluetooth"],
     "description": "Fusion SE — mid-size Ford sedan at a cash-friendly "
                    "price."},
    {"stock_number": "CC-C-08", "year": 2019, "make": "Toyota",
     "model": "Corolla", "trim": "LE Sedan", "price": "13795",
     "drivetrain": "FWD", "mileage": 66000, "engine": "1.8L I-4",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Bluetooth", "Adaptive Cruise"],
     "description": "Corolla LE — later-model, low miles. Excellent "
                    "long-term keeper."},
    {"stock_number": "CC-C-09", "year": 2014, "make": "Kia",
     "model": "Forte", "trim": "LX Sedan", "price": "5995",
     "drivetrain": "FWD", "mileage": 129000, "engine": "1.8L I-4",
     "fuel_type": "Gasoline",
     "features": ["Bluetooth"],
     "description": "Forte LX — cheap-and-cheerful compact sedan. Under "
                    "$6k, cash-and-carry."},
    {"stock_number": "CC-C-10", "year": 2016, "make": "Nissan",
     "model": "Sentra", "trim": "SV Sedan", "price": "7495",
     "drivetrain": "FWD", "mileage": 102000, "engine": "1.8L I-4",
     "fuel_type": "Gasoline",
     "features": ["Bluetooth"],
     "description": "Sentra SV — reliable compact sedan for the "
                    "credit-rebuilding buyer."},
    {"stock_number": "CC-C-11", "year": 2017, "make": "Honda",
     "model": "Civic", "trim": "EX Sedan", "price": "13995",
     "drivetrain": "FWD", "mileage": 71000, "engine": "1.5L Turbo I-4",
     "fuel_type": "Gasoline",
     "features": ["Sunroof", "Backup Camera", "Alloy Wheels"],
     "description": "Civic EX — sunroof and alloys. One of the best "
                    "sedan values in this range."},
    {"stock_number": "CC-C-12", "year": 2013, "make": "Ford",
     "model": "Focus", "trim": "SE Hatchback", "price": "4495",
     "drivetrain": "FWD", "mileage": 141000, "engine": "2.0L I-4",
     "fuel_type": "Gasoline",
     "features": ["Bluetooth"],
     "description": "Focus SE hatchback — under $5k, transportation-focused "
                    "special. Cash or short BHPH term."},
]

_VANS = [
    {"stock_number": "CC-V-01", "year": 2016, "make": "Ford",
     "model": "Transit Connect", "trim": "XL Cargo",
     "body_style": "van", "price": "11495",
     "drivetrain": "FWD", "mileage": 96000, "engine": "2.5L I-4",
     "fuel_type": "Gasoline",
     "features": ["Bluetooth", "Rubber Flooring"],
     "description": "Transit Connect cargo — small-business work van. "
                    "Ideal for tradespeople and delivery."},
    {"stock_number": "CC-V-02", "year": 2015, "make": "Toyota",
     "model": "Sienna", "trim": "LE Minivan",
     "body_style": "van", "price": "12495",
     "drivetrain": "FWD", "mileage": 118000, "engine": "3.5L V6",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Third Row Seat", "Sliding Doors"],
     "description": "Sienna LE — reliable minivan for large-family or "
                    "shuttle use."},
    {"stock_number": "CC-V-03", "year": 2018, "make": "Chrysler",
     "model": "Pacifica", "trim": "Touring Minivan",
     "body_style": "van", "price": "16995",
     "drivetrain": "FWD", "mileage": 78000, "engine": "3.6L V6",
     "fuel_type": "Gasoline",
     "features": ["Backup Camera", "Third Row Seat", "Sliding Doors",
                  "Bluetooth"],
     "description": "Pacifica Touring — newer-gen minivan, well-equipped "
                    "for family duty."},
]


def _all_units() -> list[dict]:
    """Concatenate every vehicle group and tag body_style defaults.

    Trucks/SUVs/cars use their group's default body_style; vans set it
    explicitly on the dict since :data:`_VANS` overrides. The seed
    ships 45 units total; per :file:`docs/INDEPENDENT_DEALER_PIVOT.md`
    the Phase 2 target is 40–60, so future work can add or trim
    without touching this helper.
    """
    units: list[dict] = []
    for u in _TRUCKS:
        units.append({**u, "body_style": u.get("body_style", "truck")})
    for u in _SUVS:
        units.append({**u, "body_style": u.get("body_style", "suv")})
    for u in _CARS:
        units.append({**u, "body_style": u.get("body_style", "car")})
    units.extend(_VANS)
    return units


class Command(BaseCommand):
    """Seed the Copper Canyon Auto demo inventory."""

    help = (
        "Seed the Copper Canyon Auto (Yuma, AZ) demo inventory — "
        "45 mixed-make used units, $4k–$25k, truck/SUV-heavy. "
        "Idempotent by stock_number."
    )

    def handle(self, *args, **options):
        now = timezone.now()
        created = 0
        updated = 0
        for record in _all_units():
            defaults = {
                "year": record["year"],
                "make": record["make"],
                "model": record["model"],
                "trim": record.get("trim", ""),
                "body_style": record["body_style"],
                # Every unit is used — no CPO / new on an indie lot.
                "condition": "used",
                "mileage": record.get("mileage", 0),
                "price": Decimal(str(record["price"])),
                "msrp": None,  # No MSRP concept on used inventory.
                "exterior_color": record.get("exterior_color", ""),
                "interior_color": record.get("interior_color", ""),
                "drivetrain": record.get("drivetrain", ""),
                "transmission": record.get("transmission", ""),
                "fuel_type": record.get("fuel_type", "Gasoline"),
                "engine": record.get("engine", ""),
                "features": record.get("features", []),
                "description": record.get("description", ""),
                "image_url": record.get("image_url", ""),
                "url": record.get("url", ""),
                "is_available": True,
                "source": DEMO_SOURCE,
                "last_seen_at": now,
                "imported_at": now,
            }
            _, was_created = Vehicle.objects.update_or_create(
                stock_number=record["stock_number"],
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Copper Canyon demo seed complete — "
                f"{created} created, {updated} updated "
                f"({len(_all_units())} total units)."
            )
        )
