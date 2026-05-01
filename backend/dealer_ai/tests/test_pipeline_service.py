"""Manager Phase 2: pipeline_snapshot stage assignment + demand-vs-supply.

Covers:

- Stage precedence (high_intent > new > researching > needs_handoff;
  contacted always wins on handed_off=True).
- Stage exclusivity (every lead lands in exactly one stage; counts sum to total).
- pipeline_snapshot top-level shape.
- Demand-vs-supply mismatch / tight / healthy thresholds.
- Bands with zero leads AND zero vehicles are omitted from the response.
- ``GET /admin/pipeline/`` returns 200 with the expected payload shape.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import CustomerLead, Vehicle
from dealer_ai.services import pipeline as pipeline_svc


def _make_vehicle(stock: str, price: str, *, model: str = "F-150") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        model=model,
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


def _set_created_at(lead: CustomerLead, when) -> None:
    """``CustomerLead.created_at`` is auto_now_add — back-date with a raw
    UPDATE so stage tests can simulate aged rows."""
    CustomerLead.objects.filter(pk=lead.pk).update(created_at=when)
    lead.refresh_from_db()


class StageAssignmentTests(TestCase):
    def test_handed_off_lead_goes_to_contacted_regardless_of_urgency(self):
        now = timezone.now()
        lead = CustomerLead.objects.create(
            name="A", urgency="immediate", handed_off=True
        )
        self.assertEqual(pipeline_svc._stage_for_lead(lead, now=now), "contacted")

    def test_high_intent_takes_precedence_over_new_window(self):
        now = timezone.now()
        # Created right now, urgency=immediate — must land in high_intent,
        # not new (precedence locked from §1 of the design).
        lead = CustomerLead.objects.create(
            name="A", urgency="immediate", handed_off=False
        )
        self.assertEqual(
            pipeline_svc._stage_for_lead(lead, now=now), "high_intent"
        )

    def test_new_window_24h(self):
        now = timezone.now()
        lead = CustomerLead.objects.create(
            name="A", urgency="this_week", handed_off=False
        )
        # Default created_at == now → within 24h → new.
        self.assertEqual(pipeline_svc._stage_for_lead(lead, now=now), "new")

    def test_needs_handoff_for_aged_this_week(self):
        now = timezone.now()
        lead = CustomerLead.objects.create(
            name="A", urgency="this_week", handed_off=False
        )
        _set_created_at(lead, now - timedelta(days=2))
        self.assertEqual(
            pipeline_svc._stage_for_lead(lead, now=now), "needs_handoff"
        )

    def test_researching_for_aged_researching_lead(self):
        now = timezone.now()
        lead = CustomerLead.objects.create(
            name="A", urgency="researching", handed_off=False
        )
        _set_created_at(lead, now - timedelta(days=2))
        self.assertEqual(
            pipeline_svc._stage_for_lead(lead, now=now), "researching"
        )

    def test_no_urgency_aged_lead_is_needs_handoff(self):
        now = timezone.now()
        lead = CustomerLead.objects.create(name="A", handed_off=False)
        _set_created_at(lead, now - timedelta(days=3))
        self.assertEqual(
            pipeline_svc._stage_for_lead(lead, now=now), "needs_handoff"
        )

    def test_stage_exclusivity_counts_sum_to_total(self):
        now = timezone.now()
        # One in each bucket.
        l_high = CustomerLead.objects.create(
            name="High", urgency="immediate", handed_off=False
        )
        l_new = CustomerLead.objects.create(
            name="New", urgency="this_week", handed_off=False
        )
        l_handoff = CustomerLead.objects.create(
            name="Handoff", urgency="this_month", handed_off=False
        )
        _set_created_at(l_handoff, now - timedelta(days=2))
        l_research = CustomerLead.objects.create(
            name="Researching", urgency="researching", handed_off=False
        )
        _set_created_at(l_research, now - timedelta(days=2))
        l_contact = CustomerLead.objects.create(
            name="Contacted", urgency="this_week", handed_off=True
        )

        stages, raw = pipeline_svc._compute_stages(now)
        total = CustomerLead.objects.count()
        self.assertEqual(sum(s["count"] for s in stages), total)

        # Each lead appears exactly once across all stages.
        flat_ids = [
            lead.pk for stage_leads in raw.values() for lead in stage_leads
        ]
        self.assertEqual(len(flat_ids), len(set(flat_ids)))
        self.assertEqual(set(flat_ids), {l_high.pk, l_new.pk, l_handoff.pk, l_research.pk, l_contact.pk})


class PipelineSnapshotShapeTests(TestCase):
    def test_snapshot_contains_top_level_keys(self):
        snap = pipeline_svc.pipeline_snapshot()
        for key in (
            "generated_at",
            "stages",
            "demand_vs_supply",
            "recommended_actions",
        ):
            self.assertIn(key, snap, f"missing key: {key}")

    def test_stage_keys_in_canonical_order(self):
        snap = pipeline_svc.pipeline_snapshot()
        keys = [s["key"] for s in snap["stages"]]
        self.assertEqual(
            keys,
            [
                "high_intent",
                "new",
                "needs_handoff",
                "researching",
                "contacted",
            ],
        )

    def test_each_stage_has_count_label_and_leads(self):
        snap = pipeline_svc.pipeline_snapshot()
        for s in snap["stages"]:
            self.assertIn("key", s)
            self.assertIn("label", s)
            self.assertIn("count", s)
            self.assertIn("leads", s)
            self.assertIsInstance(s["leads"], list)

    def test_demand_vs_supply_shape(self):
        snap = pipeline_svc.pipeline_snapshot()
        d = snap["demand_vs_supply"]
        self.assertEqual(d["down_payment_assumption"], 0)
        self.assertIsInstance(d["buckets"], list)


class DemandVsSupplyTests(TestCase):
    # Vehicles priced $30k produce a computed monthly payment ≈ $552/mo at
    # the engine defaults (72mo, $0 down) and so land in the $500–599/mo
    # band's price range. The band's price_low/price_high derive from
    # affordable_max_price(500) and affordable_max_price(599) respectively.

    def setUp(self):
        # Default inventory in the $500–599/mo band's price range.
        for i in range(3):
            _make_vehicle(f"MID-{i}", "30000.00")

    def test_mismatch_when_5_plus_open_leads_target_500_with_few_vehicles(self):
        # Drain available inventory in the $500/mo band — leave only 1.
        Vehicle.objects.all().delete()
        _make_vehicle("LONELY", "30000.00")
        for i in range(8):
            CustomerLead.objects.create(
                name=f"Lead {i}",
                target_monthly_payment=Decimal("500"),
                handed_off=False,
            )

        result = pipeline_svc._compute_demand_vs_supply()
        bucket = next(
            b for b in result["buckets"] if b["band_label"] == "$500–599/mo"
        )
        self.assertEqual(bucket["lead_count"], 8)
        self.assertEqual(bucket["vehicle_count"], 1)
        self.assertEqual(bucket["tier"], "mismatch")
        self.assertGreaterEqual(bucket["ratio"], 2.0)
        self.assertIsNotNone(bucket["suggestion"])

    def test_tight_when_ratio_above_125_below_2_with_floor(self):
        Vehicle.objects.all().delete()
        # 2 vehicles, 3 leads → ratio = 1.5 → tight.
        _make_vehicle("V1", "30000.00")
        _make_vehicle("V2", "30000.00")
        for i in range(3):
            CustomerLead.objects.create(
                name=f"Lead {i}",
                target_monthly_payment=Decimal("500"),
                handed_off=False,
            )
        result = pipeline_svc._compute_demand_vs_supply()
        bucket = next(
            b for b in result["buckets"] if b["band_label"] == "$500–599/mo"
        )
        self.assertEqual(bucket["lead_count"], 3)
        self.assertEqual(bucket["vehicle_count"], 2)
        self.assertEqual(bucket["tier"], "tight")
        self.assertIsNone(bucket["suggestion"])

    def test_healthy_when_supply_meets_demand(self):
        # Lots of vehicles, few leads → healthy.
        for i in range(10):
            _make_vehicle(f"V{i}", "30000.00")
        for i in range(2):
            CustomerLead.objects.create(
                name=f"Lead {i}",
                target_monthly_payment=Decimal("500"),
                handed_off=False,
            )
        result = pipeline_svc._compute_demand_vs_supply()
        bucket = next(
            b for b in result["buckets"] if b["band_label"] == "$500–599/mo"
        )
        self.assertEqual(bucket["tier"], "healthy")

    def test_zero_lead_zero_vehicle_band_is_omitted(self):
        Vehicle.objects.all().delete()
        result = pipeline_svc._compute_demand_vs_supply()
        for b in result["buckets"]:
            self.assertFalse(
                b["lead_count"] == 0 and b["vehicle_count"] == 0,
                f"unexpected empty band: {b}",
            )

    def test_below_floor_lead_count_is_not_mismatch(self):
        # 2 leads vs 0 vehicles — ratio is large, but lead_count < 3 floor.
        Vehicle.objects.all().delete()
        for i in range(2):
            CustomerLead.objects.create(
                name=f"Lead {i}",
                target_monthly_payment=Decimal("500"),
                handed_off=False,
            )
        result = pipeline_svc._compute_demand_vs_supply()
        # The band should appear (lead_count>0) but tier should be "tight"
        # not "mismatch".
        bucket = next(
            (b for b in result["buckets"] if b["band_label"] == "$500–599/mo"),
            None,
        )
        self.assertIsNotNone(bucket)
        self.assertNotEqual(bucket["tier"], "mismatch")

    def test_handed_off_leads_are_excluded_from_demand(self):
        # Handed-off leads should NOT count toward open demand.
        Vehicle.objects.all().delete()
        _make_vehicle("V1", "30000.00")
        for i in range(5):
            CustomerLead.objects.create(
                name=f"Closed {i}",
                target_monthly_payment=Decimal("500"),
                handed_off=True,
            )
        result = pipeline_svc._compute_demand_vs_supply()
        bucket = next(
            (b for b in result["buckets"] if b["band_label"] == "$500–599/mo"),
            None,
        )
        # Either omitted (lead_count=0, vehicle_count=1 still keeps it) or
        # lead_count=0.
        if bucket is not None:
            self.assertEqual(bucket["lead_count"], 0)


class AdminPipelineEndpointTests(TestCase):
    def test_endpoint_returns_200_and_expected_keys(self):
        url = reverse("dealer_ai:admin-pipeline")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        for key in (
            "generated_at",
            "stages",
            "demand_vs_supply",
            "recommended_actions",
        ):
            self.assertIn(key, data)
        self.assertEqual(len(data["stages"]), 5)
        self.assertIsInstance(data["recommended_actions"], list)

    def test_endpoint_serializes_lead_with_interested_vehicles(self):
        v = _make_vehicle("S-1", "25000.00")
        lead = CustomerLead.objects.create(
            name="Chris",
            urgency="immediate",
            target_monthly_payment=Decimal("500"),
            down_payment=Decimal("2000"),
            handed_off=False,
        )
        lead.interested_vehicles.add(v)

        url = reverse("dealer_ai:admin-pipeline")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        high_intent = next(s for s in data["stages"] if s["key"] == "high_intent")
        self.assertEqual(high_intent["count"], 1)
        row = high_intent["leads"][0]
        self.assertEqual(row["name"], "Chris")
        self.assertEqual(row["target_monthly_payment"], "500.00")
        self.assertEqual(row["down_payment"], "2000.00")
        self.assertEqual(len(row["interested_vehicles"]), 1)
        self.assertEqual(row["interested_vehicles"][0]["stock_number"], "S-1")
