"""SESSION_030 pivot: Copper Canyon Auto demo-seed shape contract.

Locks the invariants the demo depends on (all-used, mixed-make,
truck/SUV-heavy, indie-friendly price band) so future edits don't
accidentally reshape the seed into something franchise-shaped.
"""

from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from dealer_ai.models import Vehicle


COPPER_CANYON_SOURCE = "copper_canyon_demo"


def _seed():
    call_command("seed_copper_canyon_demo", stdout=StringIO())


class CopperCanyonSeedShape(TestCase):
    def setUp(self):
        _seed()

    def _qs(self):
        return Vehicle.objects.filter(source=COPPER_CANYON_SOURCE)

    def test_seed_creates_between_40_and_60_vehicles(self):
        # Pivot doc target: 40–60 units.
        count = self._qs().count()
        self.assertGreaterEqual(count, 40)
        self.assertLessEqual(count, 60)

    def test_every_unit_is_used(self):
        # Indie mixed-lot has no OEM feed → no new inventory, no CPO.
        non_used = self._qs().exclude(condition="used")
        self.assertEqual(non_used.count(), 0)

    def test_mixed_make_lot(self):
        makes = set(self._qs().values_list("make", flat=True))
        # At least 6 distinct makes represented — the seed spans
        # Toyota / Ford / Honda / Chevy / Nissan / Kia and more.
        self.assertGreaterEqual(len(makes), 6)
        for required in ("Toyota", "Honda", "Chevrolet", "Nissan"):
            self.assertIn(required, makes)

    def test_no_make_dominates_the_lot(self):
        # Sanity: no single make should own >40% of the lot — that
        # would drift back toward a franchise-shaped inventory.
        total = self._qs().count()
        make_counts = self._qs().values_list("make", flat=True)
        counts: dict[str, int] = {}
        for m in make_counts:
            counts[m] = counts.get(m, 0) + 1
        for make, n in counts.items():
            share = n / total
            self.assertLess(
                share, 0.40,
                f"{make} owns {share:.0%} of the lot — should be <40% "
                f"for mixed-make indie shape",
            )

    def test_price_band_stays_indie_friendly(self):
        prices = list(self._qs().values_list("price", flat=True))
        min_price = min(prices)
        max_price = max(prices)
        # Copper Canyon persona: indie used lot serving cash-and-carry
        # through mid-market financed buyers. Under-$8k units for
        # cash / BHPH; ceiling below $27k for the newer-year premium
        # segment.
        self.assertLessEqual(float(min_price), 6000)
        self.assertLessEqual(float(max_price), 27000)

    def test_body_style_mix_is_truck_and_suv_heavy(self):
        qs = self._qs()
        # Border-town + ag economy skews toward trucks & SUVs.
        self.assertGreaterEqual(qs.filter(body_style="truck").count(), 10)
        self.assertGreaterEqual(qs.filter(body_style="suv").count(), 12)
        # Some sedans and vans for family / commuter / small-business
        # buyers.
        self.assertGreaterEqual(qs.filter(body_style="car").count(), 8)
        self.assertGreaterEqual(qs.filter(body_style="van").count(), 2)

    def test_vehicles_span_3_to_10_year_age_window(self):
        # Pivot doc target: 3–10 yrs old at demo time. Seed uses
        # 2012–2020 model years which stays in that window through
        # 2026.
        years = list(self._qs().values_list("year", flat=True))
        self.assertGreaterEqual(min(years), 2012)
        self.assertLessEqual(max(years), 2022)

    def test_idempotent_re_seed_does_not_duplicate(self):
        first = self._qs().count()
        _seed()
        second = self._qs().count()
        self.assertEqual(first, second)

    def test_re_seed_updates_existing_rows(self):
        # Grab a known unit, mutate a field, re-seed, confirm the
        # seed's canonical value is restored.
        unit = self._qs().first()
        self.assertIsNotNone(unit)
        original_price = unit.price
        unit.price = original_price + 1
        unit.save(update_fields=["price"])
        _seed()
        unit.refresh_from_db()
        self.assertEqual(unit.price, original_price)

    def test_all_vehicles_marked_available(self):
        # Seed defaults every unit to on-the-lot / available.
        unavailable = self._qs().filter(is_available=False)
        self.assertEqual(unavailable.count(), 0)

    def test_source_tag_isolates_from_franchise_seed(self):
        # The Copper Canyon and Dealer OS seeds must not collide —
        # they use different source markers so an admin can load one
        # or both without duplicate stock_numbers.
        self.assertEqual(
            self._qs().count(),
            self._qs().filter(source=COPPER_CANYON_SOURCE).count(),
        )
        franchise_stock = set(
            Vehicle.objects.filter(source="demo_seed").values_list(
                "stock_number", flat=True
            )
        )
        copper_stock = set(
            self._qs().values_list("stock_number", flat=True)
        )
        self.assertEqual(franchise_stock & copper_stock, set())
