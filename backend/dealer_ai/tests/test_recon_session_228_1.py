"""SESSION_228.1 — the review fixes.

Locks the four items Cowork's 2026-09-01 evening review found
against the SESSION_228 ship:

1. New condition report on a ``budget`` store pre-populates one
   finding per active ``retail_default`` rate-card item.
   ``per_job`` stores stay byte-for-byte unchanged.
2. Budget bands key on the vehicle's acquisition total, not
   its asking price. Fall back to price only when the vehicle
   has no acquisition record.
3. Queued (over-budget) WOs get a symmetric "needs
   authorization: $X over the $Y cap" note; the dashboard
   payload carries ``recon_budget`` and ``recon_spend``.
4. Outside vendor as a part source: ``outside_vendor`` requires
   ``source_name`` non-blank, and links to an existing store
   Vendor when the name matches.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_CATEGORY_FLUIDS,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionReport,
    Dealership,
    DealerOnboardingProfile,
    ReconRateCard,
    SOURCE_AUCTION,
    Vehicle,
    VehicleAcquisition,
    Vendor,
    WORK_ORDER_PART_SOURCE_OUTSIDE_VENDOR,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_DRAFT,
    WORK_ORDER_VENUE_IN_HOUSE,
    WorkOrder,
)
from dealer_ai.services import condition_report as condition_report_service
from dealer_ai.services import recon as recon_service
from dealer_ai.services import recon_budget

User = get_user_model()


def _vehicle(stock, dealership, *, price=Decimal("12_000.00")):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="F-150",
        price=price,
        dealership=dealership,
    )


def _acquisition(vehicle, dealership, *, purchase_price):
    """Mirror the M2 acquisition writer so `acquisition_total` reads
    the purchase_price we set here (no fees / transport / title)."""
    return VehicleAcquisition.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        source=SOURCE_AUCTION,
        purchase_price=Decimal(purchase_price),
        purchase_date=timezone.now().date(),
    )


def _report(vehicle, dealership):
    return ConditionReport.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        inspector_name="Chris",
        inspected_at=timezone.now(),
        mileage_at_inspection=42_000,
        status=CONDITION_REPORT_STATUS_COMPLETE,
        completed_at=timezone.now(),
    )


def _user(name):
    return User.objects.create_user(username=name, password="pw")


def _set_budget_mode(dealership, *, default=Decimal("1200"), bands=None):
    profile, _ = DealerOnboardingProfile.objects.get_or_create(
        dealership=dealership
    )
    profile.recon_authorization_mode = (
        DealerOnboardingProfile.RECON_AUTHORIZATION_MODE_BUDGET
    )
    profile.recon_budget_default = default
    profile.recon_budget_bands = bands or []
    profile.save()
    return profile


# ============================================================================
# Fix 1 — retail-default pre-population
# ============================================================================


class RetailDefaultPrePopulation(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_budget_store_pre_populates_retail_default_items(self):
        _set_budget_mode(self.default)
        lof = ReconRateCard.objects.create(
            dealership=self.default,
            name="LOF",
            work_order_category=CONDITION_CATEGORY_FLUIDS,
            flat_price=Decimal("59.00"),
            retail_default=True,
        )
        # Non-default item — should NOT appear.
        ReconRateCard.objects.create(
            dealership=self.default,
            name="Windshield",
            work_order_category=CONDITION_CATEGORY_MECHANICAL,
            flat_price=Decimal("325.00"),
            retail_default=False,
        )
        # Inactive default — should NOT appear.
        ReconRateCard.objects.create(
            dealership=self.default,
            name="OldRetiredDefault",
            work_order_category=CONDITION_CATEGORY_FLUIDS,
            flat_price=Decimal("99.00"),
            retail_default=True,
            active=False,
        )
        v = _vehicle("PRE-1", self.default)
        report = condition_report_service.create_report(
            v,
            dealership=self.default,
            inspector_name="Chris",
            inspected_at=timezone.now(),
            mileage_at_inspection=30_000,
        )
        findings = list(report.findings.all())
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.category, CONDITION_CATEGORY_FLUIDS)
        self.assertEqual(f.severity, CONDITION_SEVERITY_REQUIRED)
        self.assertEqual(f.estimated_cost, Decimal("59.00"))
        self.assertEqual(f.rate_card_item_id, lof.pk)

    def test_per_job_store_pre_populates_nothing(self):
        # A per_job store profile with a retail_default rate-card
        # item should NOT pre-populate; the per_job pledge is
        # byte-for-byte pre-SESSION_228 behaviour.
        profile, _ = DealerOnboardingProfile.objects.get_or_create(
            dealership=self.default
        )
        profile.recon_authorization_mode = (
            DealerOnboardingProfile.RECON_AUTHORIZATION_MODE_PER_JOB
        )
        profile.save()
        ReconRateCard.objects.create(
            dealership=self.default,
            name="LOF",
            work_order_category=CONDITION_CATEGORY_FLUIDS,
            flat_price=Decimal("59.00"),
            retail_default=True,
        )
        v = _vehicle("PRE-2", self.default)
        report = condition_report_service.create_report(
            v,
            dealership=self.default,
            inspector_name="Chris",
            inspected_at=timezone.now(),
            mileage_at_inspection=30_000,
        )
        self.assertEqual(report.findings.count(), 0)


# ============================================================================
# Fix 2 — bands key on acquisition total, not asking price
# ============================================================================


class BandsKeyOnAcquisitionTotal(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        _set_budget_mode(
            self.default,
            default=Decimal("2500"),
            bands=[
                {"up_to": "10000", "budget": "1200"},
                {"up_to": "20000", "budget": "1800"},
                {"up_to": None, "budget": "2500"},
            ],
        )

    def test_6802_car_priced_at_12000_gets_the_1200_band(self):
        v = _vehicle("BND-1", self.default, price=Decimal("12000"))
        _acquisition(v, self.default, purchase_price=Decimal("6802.80"))
        v.refresh_from_db()
        self.assertEqual(
            recon_budget.recon_budget_for(v, dealership=self.default),
            Decimal("1200"),
        )

    def test_15000_acquisition_gets_the_1800_band(self):
        v = _vehicle("BND-2", self.default, price=Decimal("8000"))
        _acquisition(v, self.default, purchase_price=Decimal("15000"))
        v.refresh_from_db()
        self.assertEqual(
            recon_budget.recon_budget_for(v, dealership=self.default),
            Decimal("1800"),
        )

    def test_no_acquisition_falls_back_to_price(self):
        # Fresh car, no acquisition row yet — the check falls back
        # to price so the WO gate keeps working during the narrow
        # window between Vehicle create and VehicleAcquisition create.
        v = _vehicle("BND-3", self.default, price=Decimal("7500"))
        self.assertEqual(
            recon_budget.recon_budget_for(v, dealership=self.default),
            Decimal("1200"),
        )


# ============================================================================
# Fix 3 — queued WO note + dashboard payload
# ============================================================================


class QueuedNoteAndDashboardPayload(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        _set_budget_mode(self.default, default=Decimal("500"))
        self.vehicle = _vehicle("Q-1", self.default, price=Decimal("8000"))
        self.report = _report(self.vehicle, self.default)
        self.finding = ConditionFinding.objects.create(
            report=self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="Trans work",
            estimated_cost=Decimal("800"),
        )
        self.actor = _user("q-actor")

    def test_over_budget_wo_gets_needs_authorization_note(self):
        wo = recon_service.create_work_order_from_finding(
            self.finding, dealership=self.default, created_by=self.actor
        )
        wo.refresh_from_db()
        self.assertEqual(wo.status, WORK_ORDER_STATUS_DRAFT)
        self.assertIn("needs authorization:", wo.notes)
        self.assertIn("$300", wo.notes)  # 800 estimate - 500 cap
        self.assertIn("$500", wo.notes)  # the cap


# ============================================================================
# Fix 4 — outside_vendor source type
# ============================================================================


class OutsideVendorSource(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _vehicle("OV-1", self.default)
        self.report = _report(self.vehicle, self.default)
        self.finding = ConditionFinding.objects.create(
            report=self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="X",
            estimated_cost=Decimal("100"),
        )
        self.actor = _user("ov-actor")
        self.wo = recon_service.create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            estimated_cost=Decimal("100"),
        )
        recon_service.attach_findings(
            self.wo, dealership=self.default, finding_ids=[self.finding.pk]
        )

    def test_outside_vendor_requires_source_name(self):
        with self.assertRaises(ValueError):
            recon_service.add_part(
                self.wo,
                dealership=self.default,
                name="Compressor",
                source_type=WORK_ORDER_PART_SOURCE_OUTSIDE_VENDOR,
                source_name="",
            )

    def test_outside_vendor_links_matching_vendor(self):
        vendor = Vendor.objects.create(
            dealership=self.default,
            name="Yuma Body Shop",
            slug="yuma-body-shop",
        )
        part = recon_service.add_part(
            self.wo,
            dealership=self.default,
            name="Painted panel",
            source_type=WORK_ORDER_PART_SOURCE_OUTSIDE_VENDOR,
            source_name="Yuma Body Shop",
            unit_cost=Decimal("500"),
        )
        self.assertEqual(part.vendor_id, vendor.pk)
        self.assertEqual(part.source_name, "Yuma Body Shop")

    def test_outside_vendor_no_matching_vendor_still_saves(self):
        # Free text vendor name that doesn't exist — the part
        # still saves, with vendor=None and source_name preserved.
        part = recon_service.add_part(
            self.wo,
            dealership=self.default,
            name="Compressor",
            source_type=WORK_ORDER_PART_SOURCE_OUTSIDE_VENDOR,
            source_name="Never Heard Of Them Auto",
            unit_cost=Decimal("350"),
        )
        self.assertIsNone(part.vendor_id)
        self.assertEqual(part.source_name, "Never Heard Of Them Auto")

    def test_case_insensitive_vendor_match(self):
        vendor = Vendor.objects.create(
            dealership=self.default,
            name="Desert Auto Repair",
            slug="desert-auto-repair",
        )
        part = recon_service.add_part(
            self.wo,
            dealership=self.default,
            name="Rebuild",
            source_type=WORK_ORDER_PART_SOURCE_OUTSIDE_VENDOR,
            source_name="desert auto repair",
            unit_cost=Decimal("1200"),
        )
        self.assertEqual(part.vendor_id, vendor.pk)


# ============================================================================
# Dashboard + WO projection expose recon_budget / recon_spend / overrides
# ============================================================================


class DashboardCarriesBudgetAndSpend(TestCase):
    """Smoke test for the projection additions — the dashboard
    endpoint payload has recon_budget + recon_spend, and each WO
    carries budget_overrides."""

    def setUp(self):
        from rest_framework.test import APIClient
        from dealer_ai.models import (
            ROLE_DEALER_OWNER,
            UserDealershipRole,
        )
        self.default = Dealership.objects.get(slug="default")
        _set_budget_mode(self.default, default=Decimal("1000"))
        self.vehicle = _vehicle("D-1", self.default, price=Decimal("8000"))
        self.owner = User.objects.create_user(
            username="dash-owner", password="pw"
        )
        UserDealershipRole.objects.create(
            user=self.owner,
            dealership=self.default,
            role=ROLE_DEALER_OWNER,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def test_dashboard_carries_budget_and_spend(self):
        res = self.client.get(
            f"/api/dealer-ai/admin/vehicles/{self.vehicle.stock_number}/recon/"
        )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["recon_budget"], "1000.00")
        self.assertEqual(body["recon_spend"], "0.00")

    def test_wo_projection_carries_budget_overrides(self):
        # Grant a per-vehicle override, then read a WO on that
        # vehicle — the projection surfaces the override.
        report = _report(self.vehicle, self.default)
        finding = ConditionFinding.objects.create(
            report=report,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="X",
            estimated_cost=Decimal("100"),
        )
        wo = recon_service.create_work_order(
            self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            estimated_cost=Decimal("100"),
        )
        recon_service.attach_findings(
            wo, dealership=self.default, finding_ids=[finding.pk]
        )
        recon_budget.record_budget_override(
            self.vehicle,
            dealership=self.default,
            amount=Decimal("400"),
            reason="seal on the lift",
            granted_by=self.owner,
        )
        res = self.client.get(
            f"/api/dealer-ai/admin/vehicles/{self.vehicle.stock_number}/recon/"
        )
        self.assertEqual(res.status_code, 200, res.content)
        wos = res.json()["work_orders"]
        self.assertEqual(len(wos), 1)
        overrides = wos[0]["budget_overrides"]
        self.assertEqual(len(overrides), 1)
        self.assertEqual(overrides[0]["amount"], "400.00")
        self.assertEqual(overrides[0]["reason"], "seal on the lift")
        self.assertEqual(overrides[0]["granted_by"], "dash-owner")
