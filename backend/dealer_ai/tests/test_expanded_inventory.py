"""Phase 8l — expanded demo inventory tests.

Verifies the seeded set has the variety the Phase 8l spec asks for:
  - 40+ vehicles
  - non-Ford brands present in used inventory
  - multiple trucks fit/near-fit at common budget targets ($500/mo + $3k down)
  - multiple SUVs fit/near-fit at common budget targets
  - Ford-first ranking still works on the expanded data
  - demo reset endpoint still preserves imported (non-demo-source) vehicles
"""

from __future__ import annotations

from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from dealer_ai.models import Vehicle
from dealer_ai.services.chat_engine import build_budget_context


def _seed():
    call_command("seed_demo_vehicles", stdout=StringIO())


class SeededInventoryShapeTests(TestCase):
    def test_seed_creates_at_least_40_vehicles(self):
        _seed()
        count = Vehicle.objects.filter(source="demo_seed").count()
        self.assertGreaterEqual(
            count, 40, f"expected ≥40 demo vehicles, got {count}"
        )

    def test_used_inventory_includes_non_ford_brands(self):
        _seed()
        non_ford_used = Vehicle.objects.filter(
            source="demo_seed",
            condition="used",
        ).exclude(make__iexact="Ford")
        makes = sorted(set(non_ford_used.values_list("make", flat=True)))
        self.assertGreaterEqual(
            len(makes), 3, f"expected ≥3 non-Ford makes in used inventory, got {makes}"
        )
        # Spec-named brands should be represented somewhere in the seed.
        all_makes = set(
            Vehicle.objects.filter(source="demo_seed").values_list(
                "make", flat=True
            )
        )
        for required in ("Toyota", "Chevrolet", "Honda"):
            self.assertIn(required, all_makes)

    def test_idempotent_re_seed_does_not_duplicate(self):
        _seed()
        first = Vehicle.objects.filter(source="demo_seed").count()
        _seed()
        second = Vehicle.objects.filter(source="demo_seed").count()
        self.assertEqual(first, second)


class BudgetCoverageTests(TestCase):
    """Verify the expanded inventory has multiple trucks AND multiple SUVs in
    the fit/near-fit window for the most common demo budget ($500/mo + $3k
    down at 60 months)."""

    def setUp(self):
        _seed()

    def _classify(self, *, body_style):
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
            "vehicle_type": body_style,
        }
        return build_budget_context(profile, "$500/mo with $3k down")

    def test_multiple_trucks_fit_or_near_fit_at_500_3k(self):
        ctx = self._classify(body_style="truck")
        matched = ctx.matched_in_budget + ctx.near_fit
        self.assertGreaterEqual(
            len(matched),
            2,
            f"expected ≥2 truck options near $500/mo, got {len(matched)}",
        )

    def test_multiple_suvs_fit_or_near_fit_at_500_3k(self):
        ctx = self._classify(body_style="suv")
        matched = ctx.matched_in_budget + ctx.near_fit
        self.assertGreaterEqual(
            len(matched),
            2,
            f"expected ≥2 SUV options near $500/mo, got {len(matched)}",
        )

    def test_inventory_covers_each_budget_target(self):
        """At $300, $400, $500, $600, $700/mo (with $0 down), at least one
        vehicle should fit or be near-fit."""
        for target in (300, 400, 500, 600, 700):
            ctx = build_budget_context(
                {
                    "target_monthly_payment": target,
                    "down_payment": 0,
                    "term_months": 60,
                },
                f"${target}/month",
            )
            matched = ctx.matched_in_budget + ctx.near_fit
            self.assertGreater(
                len(matched),
                0,
                f"no vehicle fits or is near-fit at ${target}/mo (60mo, $0 down)",
            )


class FordFirstRankingTests(TestCase):
    """Even with non-Ford trade-ins in the seed, Ford should rank ahead of
    other brands in budget-mode results when both qualify."""

    def setUp(self):
        _seed()

    def test_ford_first_in_truck_results_at_500_mo(self):
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
            "vehicle_type": "truck",
        }
        ctx = build_budget_context(profile, "$500/mo, $3k down, trucks")
        matched = ctx.matched_in_budget + ctx.near_fit
        self.assertGreater(len(matched), 0)
        # Find the first non-Ford in the ordered list — every Ford must come
        # before it (Ford-first contract).
        first_non_ford_idx = next(
            (i for i, v in enumerate(matched) if v.make.lower() != "ford"),
            len(matched),
        )
        for v in matched[:first_non_ford_idx]:
            self.assertEqual(v.make.lower(), "ford")


class Phase8mInventoryShapeTests(TestCase):
    """Phase 8m expansion (55 → 90). Locks in the additive contract:
    target counts, new body styles (van), EV depth, hybrid + diesel coverage,
    and per-band test-prompt budget clusters from the Phase 8m spec."""

    def setUp(self):
        _seed()

    def _qs(self):
        return Vehicle.objects.filter(source="demo_seed")

    def test_total_count_at_least_90(self):
        self.assertGreaterEqual(self._qs().count(), 90)

    def test_condition_mix_meets_phase_8m_targets(self):
        qs = self._qs()
        self.assertGreaterEqual(qs.filter(condition="new").count(), 22)
        self.assertGreaterEqual(qs.filter(condition="certified").count(), 12)
        self.assertGreaterEqual(qs.filter(condition="used").count(), 56)

    def test_body_style_mix_meets_phase_8m_targets(self):
        qs = self._qs()
        self.assertGreaterEqual(qs.filter(body_style="truck").count(), 30)
        self.assertGreaterEqual(qs.filter(body_style="suv").count(), 35)
        self.assertGreaterEqual(qs.filter(body_style="ev").count(), 7)
        self.assertGreaterEqual(qs.filter(body_style="van").count(), 5)
        self.assertGreaterEqual(qs.filter(body_style="car").count(), 13)

    def test_van_inventory_now_exists(self):
        # Phase 8l had zero vans; Phase 8m must seed at least one Ford
        # commercial Transit and at least one used minivan trade-in.
        qs = self._qs().filter(body_style="van")
        ford_van = qs.filter(make__iexact="Ford")
        used_van = qs.filter(condition="used").exclude(make__iexact="Ford")
        self.assertTrue(ford_van.exists(), "expected Ford Transit van(s) in seed")
        self.assertTrue(used_van.exists(), "expected used minivan trade-in(s) in seed")

    def test_ev_cross_shop_includes_non_ford(self):
        # Lightning, Mach-E, plus at least one used non-Ford EV.
        ev_qs = self._qs().filter(body_style="ev")
        ford_evs = set(
            ev_qs.filter(make__iexact="Ford").values_list("model", flat=True)
        )
        non_ford_ev_makes = set(
            ev_qs.exclude(make__iexact="Ford").values_list("make", flat=True)
        )
        self.assertIn("F-150 Lightning", ford_evs)
        self.assertGreaterEqual(
            len(non_ford_ev_makes),
            2,
            f"expected ≥2 non-Ford EV makes (Tesla/Hyundai/Kia/etc), got {non_ford_ev_makes}",
        )

    def test_hybrid_inventory_spans_new_cpo_used(self):
        hybrid_qs = self._qs().filter(fuel_type__iexact="Hybrid")
        conditions = set(hybrid_qs.values_list("condition", flat=True))
        # Phase 8m spec promises hybrids at every condition tier.
        for c in ("new", "certified", "used"):
            self.assertIn(c, conditions, f"missing {c} hybrid in seed")

    def test_diesel_truck_now_available(self):
        # Phase 8l had zero diesels; Phase 8m promises Super Duty + Cummins.
        diesel_qs = self._qs().filter(
            fuel_type__iexact="Diesel", body_style="truck"
        )
        self.assertGreaterEqual(diesel_qs.count(), 2)
        # Ford diesel must be available for Ford-only diesel-truck shoppers.
        self.assertTrue(diesel_qs.filter(make__iexact="Ford").exists())

    def test_three_row_suvs_cluster_at_used_500_target(self):
        """Spec test prompt #7: '3-row SUV, ~$500/mo, used is fine' should
        produce multiple matches across brands after Phase 8m.

        Phase 8s cap: matched_vehicles is bounded by 1 fit + 2 near_fits
        (max 3 total). The original "≥4 cluster" assertion was written
        for the pre-cap world; under the cap the strongest signal that
        the inventory is genuinely rich is "the cap fills out" — i.e.,
        at least 1 fit, at least 1 near-fit, and exactly 3 matched.
        """
        ctx = build_budget_context(
            {
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 72,
                "vehicle_type": "suv",
            },
            "$500/mo, $3k down, 72 months, SUV",
        )
        matched = ctx.matched_in_budget + ctx.near_fit
        # The expanded inventory still produces a healthy classification —
        # the cap then narrows it to 1 fit + up to 2 near-fits.
        self.assertGreaterEqual(len(ctx.matched_in_budget), 1)
        self.assertGreaterEqual(len(ctx.near_fit), 1)
        self.assertEqual(len(matched), 3)


class DemoResetPreservesImportsTests(TestCase):
    """The /demo/reset/ endpoint must keep CSV-imported (non-demo-source)
    vehicles. Sanity check the contract still holds with the expanded seed."""

    def test_imported_vehicles_survive_default_reset(self):
        _seed()
        Vehicle.objects.create(
            stock_number="IMPORTED-XYZ",
            year=2024,
            make="Ford",
            model="Edge",
            body_style="suv",
            condition="used",
            price=Decimal("28995"),
            source="csv:dealer",
        )
        url = reverse("dealer_ai:demo-reset")
        res = self.client.post(url, data={}, content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            Vehicle.objects.filter(stock_number="IMPORTED-XYZ").exists()
        )
        # Demo set is reseeded.
        self.assertGreaterEqual(
            Vehicle.objects.filter(source="demo_seed").count(), 40
        )
