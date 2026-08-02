"""Milestone 10 · Increment 2 (SESSION_107) — DealStructure model tests.

Locks the persistence-layer shape of :class:`DealStructure` per
``MILESTONE_10_PLANNING.md`` §1.2 + the M10.1 CreditApplication
additive extension per §1.2.a Option A (user-confirmed at
SESSION_107 open).

Coverage:

- Field defaults + Decimal precision (sale_price / down_payment /
  amount_financed / apr / monthly_payment / *_pct).
- Ordering (``-created_at``).
- ``clean()`` cross-tenant guards (dealership vs credit_application,
  vs vehicle).
- CASCADE on parent CreditApplication / Vehicle delete.
- Tenant-carrier autofill signal wires ``DealStructure`` in as the
  26th carrier.
- Additive M10.1 columns (``gross_monthly_income`` /
  ``existing_monthly_debt``) default NULL and accept Decimals.
- ``__str__`` renders a human-scannable summary.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_RETENTION_YEARS,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Dealership,
    Vehicle,
)
from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES


def _make_vehicle(dealership: Dealership, *, stock: str = "DS-1") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28500.00"),
        dealership=dealership,
    )


def _make_credit_app(
    dealership: Dealership, *, name: str = "Alice Applicant"
) -> CreditApplication:
    lead = CustomerLead.objects.create(dealership=dealership, name=name)
    captured = timezone.now()
    from dateutil.relativedelta import relativedelta

    return CreditApplication.objects.create(
        dealership=dealership,
        lead=lead,
        applicant_full_name=name,
        source_format=CREDIT_APP_FORMAT_PAPER,
        captured_at=captured,
        retention_expires_at=captured
        + relativedelta(years=CREDIT_APP_RETENTION_YEARS),
    )


class DealStructureShapeTests(TestCase):
    """Field-level invariants."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m102-shape", name="M10.2 Shape"
        )
        self.credit_app = _make_credit_app(self.dealership)
        self.vehicle = _make_vehicle(self.dealership)

    def test_create_persists_all_required_fields(self) -> None:
        deal = DealStructure.objects.create(
            dealership=self.dealership,
            credit_application=self.credit_app,
            vehicle=self.vehicle,
            sale_price=Decimal("30000.00"),
            amount_financed=Decimal("25000.00"),
            apr=Decimal("9.9900"),
            term_months=72,
            monthly_payment=Decimal("462.50"),
        )
        deal.refresh_from_db()
        self.assertEqual(deal.dealership_id, self.dealership.pk)
        self.assertEqual(deal.credit_application_id, self.credit_app.pk)
        self.assertEqual(deal.vehicle_id, self.vehicle.pk)
        self.assertEqual(deal.sale_price, Decimal("30000.00"))
        self.assertEqual(deal.amount_financed, Decimal("25000.00"))
        self.assertEqual(deal.apr, Decimal("9.9900"))
        self.assertEqual(deal.term_months, 72)
        self.assertEqual(deal.monthly_payment, Decimal("462.50"))
        # Optional-input defaults land as 0.00.
        self.assertEqual(deal.down_payment, Decimal("0.00"))
        self.assertEqual(deal.trade_allowance, Decimal("0.00"))
        self.assertEqual(deal.trade_payoff, Decimal("0.00"))
        self.assertEqual(deal.taxes, Decimal("0.00"))
        self.assertEqual(deal.fees, Decimal("0.00"))
        # Ratio outputs default to NULL when written directly (not
        # via the service verb).
        self.assertIsNone(deal.ltv_pct)
        self.assertIsNone(deal.pti_pct)
        self.assertIsNone(deal.dti_pct)
        # back_end_products defaults to empty list.
        self.assertEqual(deal.back_end_products, [])

    def test_back_end_products_stores_json_array(self) -> None:
        products = [
            {"name": "VSC", "cost": "800.00", "revenue": "1600.00"},
            {"name": "GAP", "cost": "300.00", "revenue": "700.00"},
        ]
        deal = DealStructure.objects.create(
            dealership=self.dealership,
            credit_application=self.credit_app,
            vehicle=self.vehicle,
            sale_price=Decimal("30000.00"),
            amount_financed=Decimal("25000.00"),
            apr=Decimal("9.9900"),
            term_months=72,
            monthly_payment=Decimal("462.50"),
            back_end_products=products,
        )
        deal.refresh_from_db()
        self.assertEqual(deal.back_end_products, products)

    def test_ordering_is_created_at_desc(self) -> None:
        older = DealStructure.objects.create(
            dealership=self.dealership,
            credit_application=self.credit_app,
            vehicle=self.vehicle,
            sale_price=Decimal("30000.00"),
            amount_financed=Decimal("25000.00"),
            apr=Decimal("9.99"),
            term_months=72,
            monthly_payment=Decimal("462.50"),
        )
        newer = DealStructure.objects.create(
            dealership=self.dealership,
            credit_application=self.credit_app,
            vehicle=self.vehicle,
            sale_price=Decimal("30000.00"),
            amount_financed=Decimal("24000.00"),
            apr=Decimal("8.99"),
            term_months=72,
            monthly_payment=Decimal("437.15"),
        )
        rows = list(DealStructure.objects.all())
        self.assertEqual(rows[0].pk, newer.pk)
        self.assertEqual(rows[1].pk, older.pk)

    def test_str_summary_includes_ca_vehicle_payment_apr(self) -> None:
        deal = DealStructure.objects.create(
            dealership=self.dealership,
            credit_application=self.credit_app,
            vehicle=self.vehicle,
            sale_price=Decimal("30000.00"),
            amount_financed=Decimal("25000.00"),
            apr=Decimal("9.99"),
            term_months=72,
            monthly_payment=Decimal("462.50"),
        )
        rendered = str(deal)
        self.assertIn(f"CA #{self.credit_app.pk}", rendered)
        self.assertIn(f"Vehicle #{self.vehicle.pk}", rendered)
        self.assertIn("462.50", rendered)
        self.assertIn("9.99", rendered)


class DealStructureCleanTests(TestCase):
    """`clean()` cross-tenant guards."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m102-clean", name="M10.2 Clean"
        )
        self.other = Dealership.objects.create(
            slug="m102-clean-other", name="Other"
        )
        self.credit_app = _make_credit_app(self.dealership)
        self.other_credit_app = _make_credit_app(
            self.other, name="Other Alice"
        )
        self.vehicle = _make_vehicle(self.dealership)
        self.other_vehicle = _make_vehicle(self.other, stock="DS-OTHER")

    def _build(self, **overrides) -> DealStructure:
        defaults = dict(
            dealership=self.dealership,
            credit_application=self.credit_app,
            vehicle=self.vehicle,
            sale_price=Decimal("30000.00"),
            amount_financed=Decimal("25000.00"),
            apr=Decimal("9.99"),
            term_months=72,
            monthly_payment=Decimal("462.50"),
        )
        defaults.update(overrides)
        return DealStructure(**defaults)

    def test_clean_passes_with_same_tenant_ca_and_vehicle(self) -> None:
        self._build().clean()  # should not raise

    def test_clean_refuses_cross_tenant_credit_application(self) -> None:
        with self.assertRaises(ValidationError):
            self._build(credit_application=self.other_credit_app).clean()

    def test_clean_refuses_cross_tenant_vehicle(self) -> None:
        with self.assertRaises(ValidationError):
            self._build(vehicle=self.other_vehicle).clean()


class DealStructureParentDeletionTests(TestCase):
    """CASCADE on parent CreditApplication / Vehicle delete."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m102-cascade", name="M10.2 Cascade"
        )
        self.credit_app = _make_credit_app(self.dealership)
        self.vehicle = _make_vehicle(self.dealership)
        self.deal = DealStructure.objects.create(
            dealership=self.dealership,
            credit_application=self.credit_app,
            vehicle=self.vehicle,
            sale_price=Decimal("30000.00"),
            amount_financed=Decimal("25000.00"),
            apr=Decimal("9.99"),
            term_months=72,
            monthly_payment=Decimal("462.50"),
        )

    def test_credit_application_delete_cascades_to_deal_structure(self) -> None:
        # First expire the CA's retention so the delete guard doesn't
        # fire (model-layer retention refuses unexpired deletes).
        past = timezone.now() - dt.timedelta(days=1)
        CreditApplication.objects.filter(pk=self.credit_app.pk).update(
            retention_expires_at=past
        )
        self.credit_app.refresh_from_db()
        self.credit_app.delete()
        self.assertFalse(
            DealStructure.objects.filter(pk=self.deal.pk).exists()
        )

    def test_vehicle_delete_cascades_to_deal_structure(self) -> None:
        self.vehicle.delete()
        self.assertFalse(
            DealStructure.objects.filter(pk=self.deal.pk).exists()
        )


class DealStructureTenancyCarrierTests(TestCase):
    """The tenant-carrier registry includes ``DealStructure``."""

    def test_deal_structure_is_a_tenant_carrier(self) -> None:
        # M10.2 added ``DealStructure`` as the 26th carrier
        # (M10.1 shipped 25). Later increments keep extending the
        # list — this test locks the M10.2 invariant without an
        # absolute-count assertion, matching the same shape the
        # M10.1 carrier test uses. Carriers only grow, never
        # shrink, so the >= floor is the right shape.
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 26)
        self.assertIn("DealStructure", _TENANT_CARRIER_MODEL_NAMES)


class CreditApplicationAdditiveColumnsTests(TestCase):
    """M10.2 additive columns on M10.1's CreditApplication per §1.2.a."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m102-ca-addcols", name="M10.2 CA additive"
        )

    def test_income_and_debt_default_to_null(self) -> None:
        app = _make_credit_app(self.dealership)
        app.refresh_from_db()
        self.assertIsNone(app.gross_monthly_income)
        self.assertIsNone(app.existing_monthly_debt)

    def test_income_and_debt_accept_decimals(self) -> None:
        lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Income Applicant"
        )
        captured = timezone.now()
        from dateutil.relativedelta import relativedelta

        app = CreditApplication.objects.create(
            dealership=self.dealership,
            lead=lead,
            applicant_full_name="Income Applicant",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=captured,
            retention_expires_at=captured
            + relativedelta(years=CREDIT_APP_RETENTION_YEARS),
            gross_monthly_income=Decimal("5500.00"),
            existing_monthly_debt=Decimal("1250.00"),
        )
        app.refresh_from_db()
        self.assertEqual(app.gross_monthly_income, Decimal("5500.00"))
        self.assertEqual(app.existing_monthly_debt, Decimal("1250.00"))
