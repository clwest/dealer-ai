"""Milestone 10 · Increment 2 (SESSION_107) — DealStructure service tests.

Locks the service surface of :mod:`services.f_and_i.deal_structure`
per ``MILESTONE_10_PLANNING.md`` §1.2 + §7 M10.2.

Coverage:

- Pure ratio verbs (LTV / PTI / DTI) — happy paths + edge cases
  (NULL income, NULL debt, zero income, zero sale_price, negative
  numerator components, quantization/rounding, real-world
  over-financed LTV > 100%).
- :func:`record_deal_structure` — happy paths (with + without
  income) and rejection paths (cross-tenant CA, cross-tenant
  vehicle, non-positive sale_price / amount_financed /
  monthly_payment / term / APR).
- :func:`get_deal_structure` — tenant-scoped read (hit / unknown
  pk None / cross-tenant pk None).
- :func:`recompute_ratios` — refreshes denormalized columns
  after operator edits.
"""

from __future__ import annotations

from decimal import Decimal

from dateutil.relativedelta import relativedelta
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
from dealer_ai.services.f_and_i import (
    CrossTenantDealStructureError,
    debt_to_income,
    get_deal_structure,
    loan_to_value,
    payment_to_income,
    record_deal_structure,
    recompute_ratios,
)


def _make_vehicle(dealership: Dealership, *, stock: str = "DSS-1") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28500.00"),
        dealership=dealership,
    )


def _make_credit_app(
    dealership: Dealership,
    *,
    name: str = "Alice",
    income=None,
    existing_debt=None,
) -> CreditApplication:
    lead = CustomerLead.objects.create(dealership=dealership, name=name)
    captured = timezone.now()
    return CreditApplication.objects.create(
        dealership=dealership,
        lead=lead,
        applicant_full_name=name,
        source_format=CREDIT_APP_FORMAT_PAPER,
        captured_at=captured,
        retention_expires_at=captured
        + relativedelta(years=CREDIT_APP_RETENTION_YEARS),
        gross_monthly_income=income,
        existing_monthly_debt=existing_debt,
    )


def _build_deal(
    dealership,
    credit_app,
    vehicle,
    *,
    sale_price=Decimal("30000.00"),
    amount_financed=Decimal("25000.00"),
    monthly_payment=Decimal("462.50"),
    apr=Decimal("9.9900"),
    term_months=72,
) -> DealStructure:
    """Build (unsaved) DealStructure for ratio-verb tests."""
    return DealStructure(
        dealership=dealership,
        credit_application=credit_app,
        vehicle=vehicle,
        sale_price=sale_price,
        amount_financed=amount_financed,
        apr=apr,
        term_months=term_months,
        monthly_payment=monthly_payment,
    )


class LoanToValueTests(TestCase):
    """LTV = amount_financed / sale_price × 100."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="ltv", name="LTV"
        )
        self.credit_app = _make_credit_app(self.dealership)
        self.vehicle = _make_vehicle(self.dealership)

    def test_ltv_at_par(self) -> None:
        deal = _build_deal(
            self.dealership, self.credit_app, self.vehicle,
            sale_price=Decimal("30000.00"),
            amount_financed=Decimal("30000.00"),
        )
        self.assertEqual(loan_to_value(deal), Decimal("100.00"))

    def test_ltv_below_par(self) -> None:
        deal = _build_deal(
            self.dealership, self.credit_app, self.vehicle,
            sale_price=Decimal("30000.00"),
            amount_financed=Decimal("25000.00"),
        )
        # 25000 / 30000 * 100 = 83.333... → quantize to 83.33
        self.assertEqual(loan_to_value(deal), Decimal("83.33"))

    def test_ltv_over_par_with_negative_trade_equity(self) -> None:
        # Real-world subprime: rolls-in negative trade equity.
        deal = _build_deal(
            self.dealership, self.credit_app, self.vehicle,
            sale_price=Decimal("20000.00"),
            amount_financed=Decimal("28000.00"),
        )
        # 28000 / 20000 * 100 = 140.00
        self.assertEqual(loan_to_value(deal), Decimal("140.00"))

    def test_ltv_returns_none_when_sale_price_zero(self) -> None:
        deal = _build_deal(
            self.dealership, self.credit_app, self.vehicle,
            sale_price=Decimal("0.00"),
        )
        self.assertIsNone(loan_to_value(deal))

    def test_ltv_quantization_rounds_half_up(self) -> None:
        # sale=1000, financed=99.95 → 9.995% → half-up → 10.00%
        deal = _build_deal(
            self.dealership, self.credit_app, self.vehicle,
            sale_price=Decimal("1000.00"),
            amount_financed=Decimal("99.95"),
        )
        self.assertEqual(loan_to_value(deal), Decimal("10.00"))


class PaymentToIncomeTests(TestCase):
    """PTI = monthly_payment / gross_monthly_income × 100."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="pti", name="PTI"
        )
        self.vehicle = _make_vehicle(self.dealership)

    def test_pti_standard_case(self) -> None:
        credit_app = _make_credit_app(
            self.dealership, income=Decimal("5000.00")
        )
        deal = _build_deal(
            self.dealership, credit_app, self.vehicle,
            monthly_payment=Decimal("500.00"),
        )
        self.assertEqual(payment_to_income(deal), Decimal("10.00"))

    def test_pti_returns_none_when_income_is_null(self) -> None:
        # M10.1-era credit application without income captured.
        credit_app = _make_credit_app(self.dealership, income=None)
        deal = _build_deal(
            self.dealership, credit_app, self.vehicle,
            monthly_payment=Decimal("500.00"),
        )
        self.assertIsNone(payment_to_income(deal))

    def test_pti_returns_none_when_income_is_zero(self) -> None:
        credit_app = _make_credit_app(
            self.dealership, income=Decimal("0.00")
        )
        deal = _build_deal(
            self.dealership, credit_app, self.vehicle,
            monthly_payment=Decimal("500.00"),
        )
        self.assertIsNone(payment_to_income(deal))

    def test_pti_ignores_existing_debt(self) -> None:
        # PTI is single-payment; DTI is where existing debt matters.
        credit_app = _make_credit_app(
            self.dealership,
            income=Decimal("5000.00"),
            existing_debt=Decimal("2000.00"),  # should not affect PTI
        )
        deal = _build_deal(
            self.dealership, credit_app, self.vehicle,
            monthly_payment=Decimal("500.00"),
        )
        self.assertEqual(payment_to_income(deal), Decimal("10.00"))


class DebtToIncomeTests(TestCase):
    """DTI = (existing_monthly_debt + monthly_payment) / income × 100."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="dti", name="DTI"
        )
        self.vehicle = _make_vehicle(self.dealership)

    def test_dti_standard_case(self) -> None:
        credit_app = _make_credit_app(
            self.dealership,
            income=Decimal("5000.00"),
            existing_debt=Decimal("1000.00"),
        )
        deal = _build_deal(
            self.dealership, credit_app, self.vehicle,
            monthly_payment=Decimal("500.00"),
        )
        # (1000 + 500) / 5000 * 100 = 30.00
        self.assertEqual(debt_to_income(deal), Decimal("30.00"))

    def test_dti_returns_none_when_income_null(self) -> None:
        credit_app = _make_credit_app(
            self.dealership,
            income=None,
            existing_debt=Decimal("1000.00"),
        )
        deal = _build_deal(
            self.dealership, credit_app, self.vehicle,
            monthly_payment=Decimal("500.00"),
        )
        self.assertIsNone(debt_to_income(deal))

    def test_dti_returns_none_when_existing_debt_null(self) -> None:
        credit_app = _make_credit_app(
            self.dealership,
            income=Decimal("5000.00"),
            existing_debt=None,
        )
        deal = _build_deal(
            self.dealership, credit_app, self.vehicle,
            monthly_payment=Decimal("500.00"),
        )
        self.assertIsNone(debt_to_income(deal))

    def test_dti_includes_this_deal_payment_in_numerator(self) -> None:
        # Per FINANCE §3.6 the numerator includes the proposed new
        # loan payment. Verify by isolating monthly_payment as the
        # only source of movement.
        credit_app = _make_credit_app(
            self.dealership,
            income=Decimal("5000.00"),
            existing_debt=Decimal("0.00"),
        )
        deal = _build_deal(
            self.dealership, credit_app, self.vehicle,
            monthly_payment=Decimal("1000.00"),
        )
        # (0 + 1000) / 5000 * 100 = 20.00
        self.assertEqual(debt_to_income(deal), Decimal("20.00"))

    def test_dti_zero_when_both_debt_and_payment_zero(self) -> None:
        credit_app = _make_credit_app(
            self.dealership,
            income=Decimal("5000.00"),
            existing_debt=Decimal("0.00"),
        )
        deal = _build_deal(
            self.dealership, credit_app, self.vehicle,
            monthly_payment=Decimal("0.00"),
        )
        self.assertEqual(debt_to_income(deal), Decimal("0.00"))


class RecordDealStructureTests(TestCase):
    """`record_deal_structure` — happy paths + rejection paths."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="rds", name="Record Deal"
        )
        self.other = Dealership.objects.create(slug="rds-other", name="Other")
        self.vehicle = _make_vehicle(self.dealership)
        self.other_vehicle = _make_vehicle(self.other, stock="RDS-OTHER")
        self.credit_app_with_income = _make_credit_app(
            self.dealership,
            income=Decimal("5000.00"),
            existing_debt=Decimal("1000.00"),
        )
        self.credit_app_no_income = _make_credit_app(
            self.dealership, name="No-Income", income=None, existing_debt=None
        )
        self.other_credit_app = _make_credit_app(
            self.other, name="Other App"
        )

    def _defaults(self) -> dict:
        return dict(
            sale_price=Decimal("30000.00"),
            amount_financed=Decimal("25000.00"),
            apr=Decimal("9.99"),
            term_months=72,
            monthly_payment=Decimal("500.00"),
        )

    def test_record_computes_all_three_ratios_when_income_present(self) -> None:
        deal = record_deal_structure(
            dealership=self.dealership,
            credit_application=self.credit_app_with_income,
            vehicle=self.vehicle,
            **self._defaults(),
        )
        # LTV: 25000/30000 * 100 = 83.33
        self.assertEqual(deal.ltv_pct, Decimal("83.33"))
        # PTI: 500/5000 * 100 = 10.00
        self.assertEqual(deal.pti_pct, Decimal("10.00"))
        # DTI: (1000+500)/5000 * 100 = 30.00
        self.assertEqual(deal.dti_pct, Decimal("30.00"))

    def test_record_ltv_only_when_credit_app_has_no_income(self) -> None:
        deal = record_deal_structure(
            dealership=self.dealership,
            credit_application=self.credit_app_no_income,
            vehicle=self.vehicle,
            **self._defaults(),
        )
        self.assertEqual(deal.ltv_pct, Decimal("83.33"))
        self.assertIsNone(deal.pti_pct)
        self.assertIsNone(deal.dti_pct)

    def test_record_persists_optional_fields(self) -> None:
        deal = record_deal_structure(
            dealership=self.dealership,
            credit_application=self.credit_app_with_income,
            vehicle=self.vehicle,
            **self._defaults(),
            down_payment=Decimal("2500.00"),
            trade_allowance=Decimal("4000.00"),
            trade_payoff=Decimal("500.00"),
            taxes=Decimal("2100.00"),
            fees=Decimal("450.00"),
            back_end_products=[{"name": "VSC", "revenue": "1600.00"}],
        )
        deal.refresh_from_db()
        self.assertEqual(deal.down_payment, Decimal("2500.00"))
        self.assertEqual(deal.trade_allowance, Decimal("4000.00"))
        self.assertEqual(deal.trade_payoff, Decimal("500.00"))
        self.assertEqual(deal.taxes, Decimal("2100.00"))
        self.assertEqual(deal.fees, Decimal("450.00"))
        self.assertEqual(len(deal.back_end_products), 1)

    def test_record_cross_tenant_credit_application_raises(self) -> None:
        with self.assertRaises(CrossTenantDealStructureError):
            record_deal_structure(
                dealership=self.dealership,
                credit_application=self.other_credit_app,
                vehicle=self.vehicle,
                **self._defaults(),
            )

    def test_record_cross_tenant_vehicle_raises(self) -> None:
        with self.assertRaises(CrossTenantDealStructureError):
            record_deal_structure(
                dealership=self.dealership,
                credit_application=self.credit_app_with_income,
                vehicle=self.other_vehicle,
                **self._defaults(),
            )

    def test_record_rejects_non_positive_sale_price(self) -> None:
        with self.assertRaises(ValueError):
            record_deal_structure(
                dealership=self.dealership,
                credit_application=self.credit_app_with_income,
                vehicle=self.vehicle,
                sale_price=Decimal("0.00"),
                amount_financed=Decimal("25000.00"),
                apr=Decimal("9.99"),
                term_months=72,
                monthly_payment=Decimal("500.00"),
            )

    def test_record_rejects_zero_term(self) -> None:
        with self.assertRaises(ValueError):
            record_deal_structure(
                dealership=self.dealership,
                credit_application=self.credit_app_with_income,
                vehicle=self.vehicle,
                sale_price=Decimal("30000.00"),
                amount_financed=Decimal("25000.00"),
                apr=Decimal("9.99"),
                term_months=0,
                monthly_payment=Decimal("500.00"),
            )

    def test_record_rejects_negative_apr(self) -> None:
        with self.assertRaises(ValueError):
            record_deal_structure(
                dealership=self.dealership,
                credit_application=self.credit_app_with_income,
                vehicle=self.vehicle,
                sale_price=Decimal("30000.00"),
                amount_financed=Decimal("25000.00"),
                apr=Decimal("-1.00"),
                term_months=72,
                monthly_payment=Decimal("500.00"),
            )


class GetDealStructureTests(TestCase):
    """`get_deal_structure` — tenant-scoped read verb."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="get-ds", name="Get DS"
        )
        self.other = Dealership.objects.create(
            slug="get-ds-other", name="Other"
        )
        self.credit_app = _make_credit_app(
            self.dealership, income=Decimal("5000.00")
        )
        self.vehicle = _make_vehicle(self.dealership)
        self.deal = record_deal_structure(
            dealership=self.dealership,
            credit_application=self.credit_app,
            vehicle=self.vehicle,
            sale_price=Decimal("30000.00"),
            amount_financed=Decimal("25000.00"),
            apr=Decimal("9.99"),
            term_months=72,
            monthly_payment=Decimal("500.00"),
        )

    def test_returns_row_for_matching_tenant(self) -> None:
        found = get_deal_structure(self.deal.pk, dealership=self.dealership)
        self.assertIsNotNone(found)
        self.assertEqual(found.pk, self.deal.pk)

    def test_returns_none_for_unknown_pk(self) -> None:
        self.assertIsNone(
            get_deal_structure(999999, dealership=self.dealership)
        )

    def test_returns_none_for_cross_tenant_pk(self) -> None:
        self.assertIsNone(
            get_deal_structure(self.deal.pk, dealership=self.other)
        )


class RecomputeRatiosTests(TestCase):
    """`recompute_ratios` refreshes denormalized columns."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="recompute", name="Recompute"
        )
        self.credit_app = _make_credit_app(self.dealership, income=None)
        self.vehicle = _make_vehicle(self.dealership)
        # PTI / DTI start NULL because income is NULL.
        self.deal = record_deal_structure(
            dealership=self.dealership,
            credit_application=self.credit_app,
            vehicle=self.vehicle,
            sale_price=Decimal("30000.00"),
            amount_financed=Decimal("25000.00"),
            apr=Decimal("9.99"),
            term_months=72,
            monthly_payment=Decimal("500.00"),
        )

    def test_null_pti_dti_survive_until_income_captured(self) -> None:
        self.assertIsNone(self.deal.pti_pct)
        self.assertIsNone(self.deal.dti_pct)

    def test_recompute_after_income_capture_populates_pti(self) -> None:
        self.credit_app.gross_monthly_income = Decimal("5000.00")
        self.credit_app.save(update_fields=["gross_monthly_income"])
        self.deal.credit_application.refresh_from_db()
        refreshed = recompute_ratios(self.deal)
        refreshed.refresh_from_db()
        self.assertEqual(refreshed.pti_pct, Decimal("10.00"))
        # DTI still NULL — existing_monthly_debt not captured.
        self.assertIsNone(refreshed.dti_pct)

    def test_recompute_after_both_captured_populates_dti(self) -> None:
        self.credit_app.gross_monthly_income = Decimal("5000.00")
        self.credit_app.existing_monthly_debt = Decimal("1000.00")
        self.credit_app.save(
            update_fields=[
                "gross_monthly_income",
                "existing_monthly_debt",
            ]
        )
        self.deal.credit_application.refresh_from_db()
        refreshed = recompute_ratios(self.deal)
        refreshed.refresh_from_db()
        self.assertEqual(refreshed.pti_pct, Decimal("10.00"))
        self.assertEqual(refreshed.dti_pct, Decimal("30.00"))
