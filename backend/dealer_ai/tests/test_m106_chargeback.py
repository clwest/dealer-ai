"""Milestone 10 · Increment 6 (SESSION_111) — Chargeback + net_realized tests.

Combined tests for the Chargeback entity, the additive BEPA
cancellation extension, the record verb with two atomic side
effects, the net_realized aggregate verb, and the POST
endpoint. Locks the contract per
``MILESTONE_10_PLANNING.md`` §1.7 + §5.c + §7 M10.6.

Coverage summary:

- Model: shape/defaults/choices, cross-tenant clean guards on
  both nullable FKs, attach-shape (at-least-one) clean,
  tenancy carrier registry.
- Service: record_chargeback (happy + missing parents +
  cross-tenant + unknown type + deal-level auto-transitions
  Funding + product-cancellation auto-populates BEPA + skip
  kwarg suppresses transition + `other` type does not
  auto-transition).
- net_realized: no-chargeback baseline, single deal-level
  chargeback subtracts, product-cancellation subtracts,
  BEPA-only chargeback picked up, cross-vehicle exclusion,
  cross-tenant exclusion, double-count prevention when both
  FKs set.
- Endpoint: POST 201 happy, missing both parents 400, cross-
  tenant contract / bepa 404, unknown chargeback_type 400,
  auto-transition Funding side effect visible.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    BEPA_TYPE_GAP,
    BEPA_TYPE_VSC,
    CHARGEBACK_TYPE_DEAL_UNWIND,
    CHARGEBACK_TYPE_EARLY_PAYOFF,
    CHARGEBACK_TYPE_FPD,
    CHARGEBACK_TYPE_OTHER,
    CHARGEBACK_TYPE_PRODUCT_CANCELLATION,
    CHARGEBACK_TYPE_REPOSSESSION,
    CONTRACT_TYPE_RISC,
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_RETENTION_YEARS,
    DEAL_LEVEL_CHARGEBACK_TYPES,
    FUNDING_STATE_CHARGEDBACK,
    FUNDING_STATE_FUNDED,
    FUNDING_STATE_PENDING,
    ROLE_F_AND_I_MANAGER,
    SALE_FINANCE_TYPE_RETAIL,
    BackEndProductAgreement,
    Chargeback,
    Contract,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Dealership,
    Funding,
    Sale,
    Vehicle,
)
from dealer_ai.services.f_and_i import (
    CrossTenantChargebackError,
    get_chargeback,
    mark_funded,
    net_realized,
    record_back_end_product,
    record_chargeback,
    record_contract,
    record_funding,
    sign_contract,
)
from dealer_ai.services.tenancy import (
    _TENANT_CARRIER_MODEL_NAMES,
    get_default_dealership,
)

from ._auth_helpers import (
    authenticated_client,
    make_membership,
    make_user,
)


# ---- Fixture helpers --------------------------------------------------------


def _make_vehicle(dealership, *, stock: str) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28500.00"),
        dealership=dealership,
    )


def _make_deal_structure(
    dealership, *, stock: str = "M106-1"
) -> DealStructure:
    lead = CustomerLead.objects.create(dealership=dealership, name="Alice")
    captured = timezone.now()
    credit_app = CreditApplication.objects.create(
        dealership=dealership,
        lead=lead,
        applicant_full_name="Alice",
        source_format=CREDIT_APP_FORMAT_PAPER,
        captured_at=captured,
        retention_expires_at=captured
        + relativedelta(years=CREDIT_APP_RETENTION_YEARS),
    )
    vehicle = _make_vehicle(dealership, stock=stock)
    return DealStructure.objects.create(
        dealership=dealership,
        credit_application=credit_app,
        vehicle=vehicle,
        sale_price=Decimal("30000.00"),
        amount_financed=Decimal("25000.00"),
        apr=Decimal("9.99"),
        term_months=72,
        monthly_payment=Decimal("500.00"),
    )


def _make_contract_with_funding(dealership, deal) -> tuple[Contract, Funding]:
    """Return (Contract, Funding) — funding starts in ``funded`` state."""
    contract = record_contract(
        dealership=dealership,
        deal_structure=deal,
        contract_type=CONTRACT_TYPE_RISC,
    )
    sign_contract(contract)
    contract.refresh_from_db()
    funding = record_funding(dealership=dealership, contract=contract)
    mark_funded(funding, funding_amount=Decimal("24500.00"))
    funding.refresh_from_db()
    return contract, funding


def _make_sale_for_deal(
    dealership, deal_structure, *, gross: Decimal = Decimal("3500.00")
) -> Sale:
    return Sale.objects.create(
        dealership=dealership,
        vehicle=deal_structure.vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("30000.00"),
        finance_type=SALE_FINANCE_TYPE_RETAIL,
        gross_realized=gross,
    )


def _fandi_client_at(dealership, *, username: str = "m106-fandi"):
    user = make_user(username=username)
    make_membership(user, dealership, ROLE_F_AND_I_MANAGER)
    return authenticated_client(user), user


# ---- Model tests ------------------------------------------------------------


class ChargebackModelTests(TestCase):
    """Field-level invariants + clean guards + tenancy carrier."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(slug="cm", name="CM")
        self.other = Dealership.objects.create(slug="cm-other", name="Other")
        self.deal = _make_deal_structure(self.dealership)
        self.other_deal = _make_deal_structure(self.other, stock="M106-O")
        self.contract = Contract.objects.create(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        self.other_contract = Contract.objects.create(
            dealership=self.other,
            deal_structure=self.other_deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        self.bepa = BackEndProductAgreement.objects.create(
            dealership=self.dealership,
            contract=self.contract,
            product_type=BEPA_TYPE_VSC,
            cost=Decimal("800.00"),
            retail_price=Decimal("1800.00"),
        )
        self.other_bepa = BackEndProductAgreement.objects.create(
            dealership=self.other,
            contract=self.other_contract,
            product_type=BEPA_TYPE_VSC,
            cost=Decimal("800.00"),
            retail_price=Decimal("1800.00"),
        )

    def test_all_six_chargeback_types_accepted(self) -> None:
        for cb_type in (
            CHARGEBACK_TYPE_FPD,
            CHARGEBACK_TYPE_EARLY_PAYOFF,
            CHARGEBACK_TYPE_PRODUCT_CANCELLATION,
            CHARGEBACK_TYPE_REPOSSESSION,
            CHARGEBACK_TYPE_DEAL_UNWIND,
            CHARGEBACK_TYPE_OTHER,
        ):
            Chargeback.objects.create(
                dealership=self.dealership,
                contract=self.contract,
                chargeback_type=cb_type,
                chargeback_date=dt.date(2026, 8, 15),
                chargeback_amount=Decimal("500.00"),
            )
        self.assertEqual(Chargeback.objects.count(), 6)

    def test_clean_refuses_when_both_parents_null(self) -> None:
        cb = Chargeback(
            dealership=self.dealership,
            chargeback_type=CHARGEBACK_TYPE_FPD,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
        )
        with self.assertRaises(ValidationError):
            cb.clean()

    def test_clean_passes_with_contract_only(self) -> None:
        cb = Chargeback(
            dealership=self.dealership,
            contract=self.contract,
            chargeback_type=CHARGEBACK_TYPE_FPD,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
        )
        cb.clean()

    def test_clean_passes_with_bepa_only(self) -> None:
        cb = Chargeback(
            dealership=self.dealership,
            bepa=self.bepa,
            chargeback_type=CHARGEBACK_TYPE_PRODUCT_CANCELLATION,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
        )
        cb.clean()

    def test_clean_refuses_cross_tenant_contract(self) -> None:
        cb = Chargeback(
            dealership=self.dealership,
            contract=self.other_contract,
            chargeback_type=CHARGEBACK_TYPE_FPD,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
        )
        with self.assertRaises(ValidationError):
            cb.clean()

    def test_clean_refuses_cross_tenant_bepa(self) -> None:
        cb = Chargeback(
            dealership=self.dealership,
            bepa=self.other_bepa,
            chargeback_type=CHARGEBACK_TYPE_PRODUCT_CANCELLATION,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
        )
        with self.assertRaises(ValidationError):
            cb.clean()

    def test_deal_level_types_frozenset_matches_planning(self) -> None:
        # Sanity check on the constant driving auto-transition logic.
        self.assertEqual(
            DEAL_LEVEL_CHARGEBACK_TYPES,
            frozenset(
                (
                    CHARGEBACK_TYPE_FPD,
                    CHARGEBACK_TYPE_EARLY_PAYOFF,
                    CHARGEBACK_TYPE_REPOSSESSION,
                    CHARGEBACK_TYPE_DEAL_UNWIND,
                )
            ),
        )


class BEPACancellationExtensionTests(TestCase):
    """M10.6 additive extension of M10.5 BEPA — nullable columns."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bce", name="BEPA cancellation extension"
        )
        self.deal = _make_deal_structure(self.dealership)
        self.contract = Contract.objects.create(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )

    def test_cancellation_fields_default_to_null(self) -> None:
        bepa = BackEndProductAgreement.objects.create(
            dealership=self.dealership,
            contract=self.contract,
            product_type=BEPA_TYPE_VSC,
            cost=Decimal("800.00"),
            retail_price=Decimal("1800.00"),
        )
        bepa.refresh_from_db()
        self.assertIsNone(bepa.cancelled_at)
        self.assertIsNone(bepa.cancellation_amount)


class ChargebackTenancyCarrierTests(TestCase):
    def test_chargeback_is_a_tenant_carrier(self) -> None:
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 33)
        self.assertIn("Chargeback", _TENANT_CARRIER_MODEL_NAMES)


# ---- Service tests ---------------------------------------------------------


class RecordChargebackTests(TestCase):
    """`record_chargeback` — happy + rejection + side-effect coverage."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(slug="rc", name="RC")
        self.other = Dealership.objects.create(slug="rc-other", name="Other")
        self.deal = _make_deal_structure(self.dealership)
        self.other_deal = _make_deal_structure(self.other, stock="RC-O")
        self.contract, self.funding = _make_contract_with_funding(
            self.dealership, self.deal
        )
        self.bepa = record_back_end_product(
            dealership=self.dealership,
            contract=self.contract,
            product_type=BEPA_TYPE_VSC,
            cost=Decimal("800.00"),
            retail_price=Decimal("1800.00"),
        )
        # Cross-tenant fixtures.
        self.other_contract = Contract.objects.create(
            dealership=self.other,
            deal_structure=self.other_deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        self.other_bepa = BackEndProductAgreement.objects.create(
            dealership=self.other,
            contract=self.other_contract,
            product_type=BEPA_TYPE_VSC,
            cost=Decimal("800.00"),
            retail_price=Decimal("1800.00"),
        )

    def test_neither_parent_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            record_chargeback(
                dealership=self.dealership,
                chargeback_type=CHARGEBACK_TYPE_FPD,
                chargeback_date=dt.date(2026, 8, 15),
                chargeback_amount=Decimal("500.00"),
            )

    def test_cross_tenant_contract_raises(self) -> None:
        with self.assertRaises(CrossTenantChargebackError):
            record_chargeback(
                dealership=self.dealership,
                contract=self.other_contract,
                chargeback_type=CHARGEBACK_TYPE_FPD,
                chargeback_date=dt.date(2026, 8, 15),
                chargeback_amount=Decimal("500.00"),
            )

    def test_cross_tenant_bepa_raises(self) -> None:
        with self.assertRaises(CrossTenantChargebackError):
            record_chargeback(
                dealership=self.dealership,
                bepa=self.other_bepa,
                chargeback_type=CHARGEBACK_TYPE_PRODUCT_CANCELLATION,
                chargeback_date=dt.date(2026, 8, 15),
                chargeback_amount=Decimal("500.00"),
            )

    def test_unknown_type_raises(self) -> None:
        with self.assertRaises(ValueError):
            record_chargeback(
                dealership=self.dealership,
                contract=self.contract,
                chargeback_type="lender_dispute",
                chargeback_date=dt.date(2026, 8, 15),
                chargeback_amount=Decimal("500.00"),
            )

    def test_fpd_auto_transitions_funding_to_chargedback(self) -> None:
        self.assertEqual(self.funding.state, FUNDING_STATE_FUNDED)
        record_chargeback(
            dealership=self.dealership,
            contract=self.contract,
            chargeback_type=CHARGEBACK_TYPE_FPD,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
        )
        self.funding.refresh_from_db()
        self.assertEqual(self.funding.state, FUNDING_STATE_CHARGEDBACK)

    def test_deal_unwind_also_auto_transitions_funding(self) -> None:
        record_chargeback(
            dealership=self.dealership,
            contract=self.contract,
            chargeback_type=CHARGEBACK_TYPE_DEAL_UNWIND,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
        )
        self.funding.refresh_from_db()
        self.assertEqual(self.funding.state, FUNDING_STATE_CHARGEDBACK)

    def test_product_cancellation_does_not_transition_funding(self) -> None:
        record_chargeback(
            dealership=self.dealership,
            contract=self.contract,
            bepa=self.bepa,
            chargeback_type=CHARGEBACK_TYPE_PRODUCT_CANCELLATION,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
        )
        self.funding.refresh_from_db()
        # Funding stays FUNDED — product cancellation reduces
        # commission but leaves the deal funded.
        self.assertEqual(self.funding.state, FUNDING_STATE_FUNDED)

    def test_other_type_does_not_transition_funding(self) -> None:
        record_chargeback(
            dealership=self.dealership,
            contract=self.contract,
            chargeback_type=CHARGEBACK_TYPE_OTHER,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
        )
        self.funding.refresh_from_db()
        # Safer default — ``other`` requires explicit operator PATCH.
        self.assertEqual(self.funding.state, FUNDING_STATE_FUNDED)

    def test_skip_funding_transition_kwarg_suppresses_side_effect(self) -> None:
        record_chargeback(
            dealership=self.dealership,
            contract=self.contract,
            chargeback_type=CHARGEBACK_TYPE_FPD,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
            skip_funding_transition=True,
        )
        self.funding.refresh_from_db()
        self.assertEqual(self.funding.state, FUNDING_STATE_FUNDED)

    def test_product_cancellation_auto_populates_bepa_fields(self) -> None:
        self.assertIsNone(self.bepa.cancelled_at)
        self.assertIsNone(self.bepa.cancellation_amount)
        record_chargeback(
            dealership=self.dealership,
            bepa=self.bepa,
            chargeback_type=CHARGEBACK_TYPE_PRODUCT_CANCELLATION,
            chargeback_date=dt.date(2026, 8, 20),
            chargeback_amount=Decimal("450.00"),
        )
        self.bepa.refresh_from_db()
        self.assertIsNotNone(self.bepa.cancelled_at)
        # cancelled_at is chargeback_date normalized to start-of-day.
        self.assertEqual(self.bepa.cancelled_at.date(), dt.date(2026, 8, 20))
        self.assertEqual(self.bepa.cancellation_amount, Decimal("450.00"))

    def test_bepa_only_chargeback_also_populates_bepa(self) -> None:
        # No Contract FK; just BEPA.
        record_chargeback(
            dealership=self.dealership,
            bepa=self.bepa,
            chargeback_type=CHARGEBACK_TYPE_PRODUCT_CANCELLATION,
            chargeback_date=dt.date(2026, 8, 21),
            chargeback_amount=Decimal("300.00"),
        )
        self.bepa.refresh_from_db()
        self.assertEqual(self.bepa.cancellation_amount, Decimal("300.00"))

    def test_fpd_without_bepa_does_not_populate_bepa(self) -> None:
        # Deal-level chargeback; BEPA fields stay NULL.
        record_chargeback(
            dealership=self.dealership,
            contract=self.contract,
            chargeback_type=CHARGEBACK_TYPE_FPD,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
        )
        self.bepa.refresh_from_db()
        self.assertIsNone(self.bepa.cancelled_at)
        self.assertIsNone(self.bepa.cancellation_amount)


class NetRealizedTests(TestCase):
    """`net_realized(sale)` — pure aggregate correctness."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(slug="nr", name="NR")
        self.other = Dealership.objects.create(slug="nr-other", name="Other")
        self.deal = _make_deal_structure(self.dealership)
        self.contract, self.funding = _make_contract_with_funding(
            self.dealership, self.deal
        )
        self.bepa = record_back_end_product(
            dealership=self.dealership,
            contract=self.contract,
            product_type=BEPA_TYPE_VSC,
            cost=Decimal("800.00"),
            retail_price=Decimal("1800.00"),
        )
        self.sale = _make_sale_for_deal(self.dealership, self.deal)

    def test_baseline_no_chargebacks_equals_gross_realized(self) -> None:
        self.assertEqual(
            net_realized(self.sale), self.sale.gross_realized
        )

    def test_single_deal_chargeback_subtracts(self) -> None:
        record_chargeback(
            dealership=self.dealership,
            contract=self.contract,
            chargeback_type=CHARGEBACK_TYPE_FPD,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
            skip_funding_transition=True,
        )
        expected = self.sale.gross_realized - Decimal("500.00")
        self.assertEqual(net_realized(self.sale), expected)

    def test_product_cancellation_subtracts(self) -> None:
        record_chargeback(
            dealership=self.dealership,
            contract=self.contract,
            bepa=self.bepa,
            chargeback_type=CHARGEBACK_TYPE_PRODUCT_CANCELLATION,
            chargeback_date=dt.date(2026, 8, 20),
            chargeback_amount=Decimal("450.00"),
        )
        # Chargeback counted once even though both FKs point to
        # matching parents (distinct pk set).
        expected = self.sale.gross_realized - Decimal("450.00")
        self.assertEqual(net_realized(self.sale), expected)

    def test_multiple_chargebacks_sum(self) -> None:
        record_chargeback(
            dealership=self.dealership,
            contract=self.contract,
            chargeback_type=CHARGEBACK_TYPE_FPD,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
            skip_funding_transition=True,
        )
        record_chargeback(
            dealership=self.dealership,
            contract=self.contract,
            bepa=self.bepa,
            chargeback_type=CHARGEBACK_TYPE_PRODUCT_CANCELLATION,
            chargeback_date=dt.date(2026, 8, 20),
            chargeback_amount=Decimal("450.00"),
        )
        expected = self.sale.gross_realized - Decimal("950.00")
        self.assertEqual(net_realized(self.sale), expected)

    def test_bepa_only_chargeback_still_attributed(self) -> None:
        # No Contract FK on the chargeback — attribution via BEPA
        # → Contract → DealStructure → Vehicle path.
        record_chargeback(
            dealership=self.dealership,
            bepa=self.bepa,
            chargeback_type=CHARGEBACK_TYPE_PRODUCT_CANCELLATION,
            chargeback_date=dt.date(2026, 8, 25),
            chargeback_amount=Decimal("200.00"),
        )
        expected = self.sale.gross_realized - Decimal("200.00")
        self.assertEqual(net_realized(self.sale), expected)

    def test_cross_tenant_chargeback_excluded(self) -> None:
        # Chargeback in another tenant with the same vehicle in
        # scope shouldn't leak. Create a vehicle collision.
        other_deal = _make_deal_structure(self.other, stock="NR-O")
        other_contract = Contract.objects.create(
            dealership=self.other,
            deal_structure=other_deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        Chargeback.objects.create(
            dealership=self.other,
            contract=other_contract,
            chargeback_type=CHARGEBACK_TYPE_FPD,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("999.00"),
        )
        # Sale in self.dealership — cross-tenant chargeback excluded.
        self.assertEqual(net_realized(self.sale), self.sale.gross_realized)


class GetChargebackTests(TestCase):
    """`get_chargeback` tenant scoping."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(slug="gc", name="GC")
        self.other = Dealership.objects.create(slug="gc-other", name="Other")
        self.deal = _make_deal_structure(self.dealership)
        self.contract = Contract.objects.create(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        self.cb = Chargeback.objects.create(
            dealership=self.dealership,
            contract=self.contract,
            chargeback_type=CHARGEBACK_TYPE_FPD,
            chargeback_date=dt.date(2026, 8, 15),
            chargeback_amount=Decimal("500.00"),
        )

    def test_returns_matching_tenant_row(self) -> None:
        self.assertIsNotNone(
            get_chargeback(self.cb.pk, dealership=self.dealership)
        )

    def test_returns_none_for_cross_tenant_pk(self) -> None:
        self.assertIsNone(
            get_chargeback(self.cb.pk, dealership=self.other)
        )

    def test_returns_none_for_unknown_pk(self) -> None:
        self.assertIsNone(
            get_chargeback(999999, dealership=self.dealership)
        )


# ---- Endpoint tests --------------------------------------------------------


class ChargebackEndpointTests(TestCase):
    """POST /admin/chargebacks/."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(slug="ce-other", name="Other")
        self.deal = _make_deal_structure(self.dealership)
        self.other_deal = _make_deal_structure(self.other, stock="CE-O")
        self.contract, self.funding = _make_contract_with_funding(
            self.dealership, self.deal
        )
        self.bepa = record_back_end_product(
            dealership=self.dealership,
            contract=self.contract,
            product_type=BEPA_TYPE_GAP,
            cost=Decimal("400.00"),
            retail_price=Decimal("900.00"),
        )
        self.other_contract = Contract.objects.create(
            dealership=self.other,
            deal_structure=self.other_deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        self.client, self.user = _fandi_client_at(self.dealership)

    def _post(self, body):
        return self.client.post(
            reverse("dealer_ai:admin-chargeback-create"),
            body,
            format="json",
        )

    def test_create_deal_chargeback_returns_201_and_transitions_funding(
        self,
    ) -> None:
        response = self._post(
            {
                "contract_id": self.contract.pk,
                "chargeback_type": CHARGEBACK_TYPE_FPD,
                "chargeback_date": "2026-08-15",
                "chargeback_amount": "500.00",
            }
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["chargeback"]
        self.assertEqual(body["chargeback_type"], CHARGEBACK_TYPE_FPD)
        # recorded_by sourced from request.user server-side.
        self.assertEqual(body["recorded_by_id"], self.user.pk)
        # Side effect: Funding transitioned to chargedback.
        self.funding.refresh_from_db()
        self.assertEqual(self.funding.state, FUNDING_STATE_CHARGEDBACK)

    def test_create_missing_both_parents_returns_400(self) -> None:
        response = self._post(
            {
                "chargeback_type": CHARGEBACK_TYPE_FPD,
                "chargeback_date": "2026-08-15",
                "chargeback_amount": "500.00",
            }
        )
        self.assertEqual(response.status_code, 400)

    def test_create_cross_tenant_contract_returns_404(self) -> None:
        response = self._post(
            {
                "contract_id": self.other_contract.pk,
                "chargeback_type": CHARGEBACK_TYPE_FPD,
                "chargeback_date": "2026-08-15",
                "chargeback_amount": "500.00",
            }
        )
        self.assertEqual(response.status_code, 404)

    def test_create_unknown_type_returns_400(self) -> None:
        response = self._post(
            {
                "contract_id": self.contract.pk,
                "chargeback_type": "lender_dispute",
                "chargeback_date": "2026-08-15",
                "chargeback_amount": "500.00",
            }
        )
        self.assertEqual(response.status_code, 400)

    def test_create_product_cancellation_populates_bepa(self) -> None:
        response = self._post(
            {
                "contract_id": self.contract.pk,
                "bepa_id": self.bepa.pk,
                "chargeback_type": CHARGEBACK_TYPE_PRODUCT_CANCELLATION,
                "chargeback_date": "2026-08-20",
                "chargeback_amount": "450.00",
            }
        )
        self.assertEqual(response.status_code, 201)
        self.bepa.refresh_from_db()
        self.assertEqual(
            self.bepa.cancellation_amount, Decimal("450.00")
        )
        # Funding stays FUNDED (product cancellation doesn't
        # transition Funding).
        self.funding.refresh_from_db()
        self.assertEqual(self.funding.state, FUNDING_STATE_FUNDED)

    def test_create_with_skip_kwarg_leaves_funding_alone(self) -> None:
        response = self._post(
            {
                "contract_id": self.contract.pk,
                "chargeback_type": CHARGEBACK_TYPE_FPD,
                "chargeback_date": "2026-08-15",
                "chargeback_amount": "500.00",
                "skip_funding_transition": True,
            }
        )
        self.assertEqual(response.status_code, 201)
        self.funding.refresh_from_db()
        self.assertEqual(self.funding.state, FUNDING_STATE_FUNDED)
