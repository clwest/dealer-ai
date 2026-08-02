"""Milestone 10 · Increment 5 (SESSION_110) — Contract + BEPA + Funding tests.

Combined tests file for the three M10.5 entities. Locks the
model / service / endpoint contract per
``MILESTONE_10_PLANNING.md`` §1.5 + §1.6 (all five decisions
confirmed at SESSION_110 open, recorded in §0.a).

Coverage summary:

- Model: shape/defaults/choices, clean cross-tenant guards,
  CASCADE / OneToOne behaviors, tenancy carrier registry.
- Service: record verbs (happy + cross-tenant + unknown vocab),
  sign_contract / void_contract auto-populate, mark_funded
  auto-populate + amount capture, uniqueness (FundingAlreadyExists),
  sign after void refused.
- Endpoint: create + PATCH for Contract / BEPA / Funding with
  auth positive (f_and_i_manager), cross-tenant 404,
  action-based PATCH (sign/void/mark_funded).
"""

from __future__ import annotations

from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    BEPA_TYPE_GAP,
    BEPA_TYPE_OTHER,
    BEPA_TYPE_T_AND_W,
    BEPA_TYPE_VSC,
    CONTRACT_STATE_SIGNED,
    CONTRACT_STATE_UNSIGNED,
    CONTRACT_STATE_VOIDED,
    CONTRACT_TYPE_CASH,
    CONTRACT_TYPE_LEASE,
    CONTRACT_TYPE_RISC,
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_RETENTION_YEARS,
    FUNDING_STATE_FUNDED,
    FUNDING_STATE_PENDING,
    ROLE_F_AND_I_MANAGER,
    BackEndProductAgreement,
    Contract,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Dealership,
    Funding,
    Vehicle,
)
from dealer_ai.services.f_and_i import (
    ContractAlreadyVoidedError,
    CrossTenantContractError,
    CrossTenantFundingError,
    FundingAlreadyExistsError,
    get_contract,
    get_funding,
    list_products_for_contract,
    mark_funded,
    record_back_end_product,
    record_contract,
    record_funding,
    sign_contract,
    void_contract,
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


def _make_deal_structure(dealership, *, stock: str = "M105-1") -> DealStructure:
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
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28500.00"),
        dealership=dealership,
    )
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


def _fandi_client_at(dealership, *, username: str = "m105-fandi"):
    user = make_user(username=username)
    make_membership(user, dealership, ROLE_F_AND_I_MANAGER)
    return authenticated_client(user)


# ---- Model tests ------------------------------------------------------------


class ContractModelTests(TestCase):
    """Field-level invariants + clean guards + tenancy carrier."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="cm", name="Contract Model"
        )
        self.other = Dealership.objects.create(slug="cm-other", name="Other")
        self.deal = _make_deal_structure(self.dealership)
        self.other_deal = _make_deal_structure(self.other, stock="M105-O")

    def test_create_persists_all_fields_with_defaults(self) -> None:
        contract = Contract.objects.create(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        contract.refresh_from_db()
        self.assertEqual(contract.state, CONTRACT_STATE_UNSIGNED)
        self.assertEqual(contract.financed_amount, Decimal("0.00"))
        self.assertEqual(contract.total_of_payments, Decimal("0.00"))
        self.assertEqual(contract.finance_charge, Decimal("0.00"))
        self.assertEqual(contract.apr_disclosure, Decimal("0.0000"))
        self.assertIsNone(contract.signed_at)
        self.assertIsNone(contract.voided_at)

    def test_all_three_contract_types_accepted(self) -> None:
        for ctype in (
            CONTRACT_TYPE_RISC,
            CONTRACT_TYPE_LEASE,
            CONTRACT_TYPE_CASH,
        ):
            Contract.objects.create(
                dealership=self.dealership,
                deal_structure=self.deal,
                contract_type=ctype,
            )
        self.assertEqual(Contract.objects.count(), 3)

    def test_clean_refuses_cross_tenant_deal_structure(self) -> None:
        contract = Contract(
            dealership=self.dealership,
            deal_structure=self.other_deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        with self.assertRaises(ValidationError):
            contract.clean()

    def test_deleting_deal_cascades_to_contract(self) -> None:
        contract = Contract.objects.create(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        self.deal.delete()
        self.assertFalse(Contract.objects.filter(pk=contract.pk).exists())


class BackEndProductAgreementModelTests(TestCase):
    """BEPA field invariants + cross-tenant clean + CASCADE."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bem", name="BEPA Model"
        )
        self.other = Dealership.objects.create(slug="bem-other", name="Other")
        self.deal = _make_deal_structure(self.dealership)
        self.other_deal = _make_deal_structure(self.other, stock="BEM-O")
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

    def test_create_persists_all_fields(self) -> None:
        bepa = BackEndProductAgreement.objects.create(
            dealership=self.dealership,
            contract=self.contract,
            product_type=BEPA_TYPE_VSC,
            provider="Zurich",
            cost=Decimal("800.00"),
            retail_price=Decimal("1800.00"),
            term_months=72,
            mileage_limit=100000,
            deductible=Decimal("100.00"),
        )
        bepa.refresh_from_db()
        self.assertEqual(bepa.product_type, BEPA_TYPE_VSC)
        self.assertEqual(bepa.provider, "Zurich")
        self.assertEqual(bepa.cost, Decimal("800.00"))
        self.assertEqual(bepa.retail_price, Decimal("1800.00"))
        self.assertEqual(bepa.term_months, 72)
        self.assertEqual(bepa.deductible, Decimal("100.00"))

    def test_optional_fields_default_to_null(self) -> None:
        # GAP has no term / mileage / deductible.
        bepa = BackEndProductAgreement.objects.create(
            dealership=self.dealership,
            contract=self.contract,
            product_type=BEPA_TYPE_GAP,
            cost=Decimal("400.00"),
            retail_price=Decimal("900.00"),
        )
        self.assertIsNone(bepa.term_months)
        self.assertIsNone(bepa.mileage_limit)
        self.assertIsNone(bepa.deductible)

    def test_clean_refuses_cross_tenant_contract(self) -> None:
        bepa = BackEndProductAgreement(
            dealership=self.dealership,
            contract=self.other_contract,
            product_type=BEPA_TYPE_VSC,
            cost=Decimal("800.00"),
            retail_price=Decimal("1800.00"),
        )
        with self.assertRaises(ValidationError):
            bepa.clean()

    def test_deleting_contract_cascades_to_bepa(self) -> None:
        bepa = BackEndProductAgreement.objects.create(
            dealership=self.dealership,
            contract=self.contract,
            product_type=BEPA_TYPE_VSC,
            cost=Decimal("800.00"),
            retail_price=Decimal("1800.00"),
        )
        self.contract.delete()
        self.assertFalse(
            BackEndProductAgreement.objects.filter(pk=bepa.pk).exists()
        )


class FundingModelTests(TestCase):
    """Funding OneToOne + defaults + cross-tenant clean."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(slug="fm", name="Funding")
        self.other = Dealership.objects.create(slug="fm-other", name="Other")
        self.deal = _make_deal_structure(self.dealership)
        self.other_deal = _make_deal_structure(self.other, stock="FM-O")
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

    def test_create_defaults_state_pending_and_amount_null(self) -> None:
        funding = Funding.objects.create(
            dealership=self.dealership, contract=self.contract
        )
        funding.refresh_from_db()
        self.assertEqual(funding.state, FUNDING_STATE_PENDING)
        self.assertIsNone(funding.funded_at)
        self.assertIsNone(funding.funding_amount)

    def test_onetoone_enforces_one_funding_per_contract(self) -> None:
        Funding.objects.create(
            dealership=self.dealership, contract=self.contract
        )
        with self.assertRaises(IntegrityError):
            Funding.objects.create(
                dealership=self.dealership, contract=self.contract
            )

    def test_clean_refuses_cross_tenant_contract(self) -> None:
        funding = Funding(
            dealership=self.dealership, contract=self.other_contract
        )
        with self.assertRaises(ValidationError):
            funding.clean()


class M105TenancyCarrierTests(TestCase):
    """All three M10.5 entities in the tenant-carrier registry."""

    def test_contract_carrier_registered(self) -> None:
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 30)
        self.assertIn("Contract", _TENANT_CARRIER_MODEL_NAMES)

    def test_bepa_carrier_registered(self) -> None:
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 31)
        self.assertIn("BackEndProductAgreement", _TENANT_CARRIER_MODEL_NAMES)

    def test_funding_carrier_registered(self) -> None:
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 32)
        self.assertIn("Funding", _TENANT_CARRIER_MODEL_NAMES)


# ---- Service tests ---------------------------------------------------------


class ContractServiceTests(TestCase):
    """`record_contract`, `sign_contract`, `void_contract`."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(slug="cs", name="CS")
        self.other = Dealership.objects.create(slug="cs-other", name="Other")
        self.deal = _make_deal_structure(self.dealership)
        self.other_deal = _make_deal_structure(self.other, stock="CS-O")

    def test_record_creates_unsigned_contract(self) -> None:
        contract = record_contract(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
            financed_amount=Decimal("25000.00"),
            total_of_payments=Decimal("32000.00"),
            finance_charge=Decimal("7000.00"),
            apr_disclosure=Decimal("9.9900"),
        )
        self.assertEqual(contract.state, CONTRACT_STATE_UNSIGNED)
        self.assertEqual(contract.financed_amount, Decimal("25000.00"))
        self.assertIsNone(contract.signed_at)

    def test_record_cross_tenant_deal_raises(self) -> None:
        with self.assertRaises(CrossTenantContractError):
            record_contract(
                dealership=self.dealership,
                deal_structure=self.other_deal,
                contract_type=CONTRACT_TYPE_RISC,
            )

    def test_record_unknown_type_raises(self) -> None:
        with self.assertRaises(ValueError):
            record_contract(
                dealership=self.dealership,
                deal_structure=self.deal,
                contract_type="mortgage",
            )

    def test_sign_populates_signed_at_and_signer_name(self) -> None:
        contract = record_contract(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        before = timezone.now()
        signed = sign_contract(contract, signer_name="Alice Smith")
        signed.refresh_from_db()
        self.assertEqual(signed.state, CONTRACT_STATE_SIGNED)
        self.assertIsNotNone(signed.signed_at)
        self.assertGreaterEqual(signed.signed_at, before)
        self.assertEqual(signed.signer_name, "Alice Smith")

    def test_sign_preserves_original_signed_at_on_repeat(self) -> None:
        contract = record_contract(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        sign_contract(contract)
        contract.refresh_from_db()
        original_signed_at = contract.signed_at
        # Second sign should not overwrite the first-signed moment.
        sign_contract(contract)
        contract.refresh_from_db()
        self.assertEqual(contract.signed_at, original_signed_at)

    def test_sign_after_void_raises(self) -> None:
        contract = record_contract(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        void_contract(contract, voided_reason="Test")
        contract.refresh_from_db()
        with self.assertRaises(ContractAlreadyVoidedError):
            sign_contract(contract)

    def test_void_populates_voided_at_and_reason(self) -> None:
        contract = record_contract(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        # Sign first, then void — verify signed_at is preserved.
        sign_contract(contract)
        contract.refresh_from_db()
        original_signed_at = contract.signed_at
        before = timezone.now()
        voided = void_contract(
            contract, voided_reason="Contract errors — re-signing"
        )
        voided.refresh_from_db()
        self.assertEqual(voided.state, CONTRACT_STATE_VOIDED)
        self.assertIsNotNone(voided.voided_at)
        self.assertGreaterEqual(voided.voided_at, before)
        self.assertEqual(
            voided.voided_reason, "Contract errors — re-signing"
        )
        # signed_at preserved (both moments are historical events).
        self.assertEqual(voided.signed_at, original_signed_at)

    def test_get_tenant_scoping(self) -> None:
        contract = record_contract(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        self.assertIsNotNone(
            get_contract(contract.pk, dealership=self.dealership)
        )
        self.assertIsNone(
            get_contract(contract.pk, dealership=self.other)
        )
        self.assertIsNone(get_contract(999999, dealership=self.dealership))


class BackEndProductServiceTests(TestCase):
    """`record_back_end_product` + `list_products_for_contract`."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(slug="bes", name="BES")
        self.other = Dealership.objects.create(slug="bes-other", name="Other")
        self.deal = _make_deal_structure(self.dealership)
        self.other_deal = _make_deal_structure(self.other, stock="BES-O")
        self.contract = record_contract(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        self.other_contract = record_contract(
            dealership=self.other,
            deal_structure=self.other_deal,
            contract_type=CONTRACT_TYPE_RISC,
        )

    def test_record_persists_vsc_with_all_structural_fields(self) -> None:
        bepa = record_back_end_product(
            dealership=self.dealership,
            contract=self.contract,
            product_type=BEPA_TYPE_VSC,
            cost=Decimal("800.00"),
            retail_price=Decimal("1800.00"),
            provider="Zurich",
            term_months=72,
            mileage_limit=100000,
            deductible=Decimal("100.00"),
        )
        self.assertEqual(bepa.product_type, BEPA_TYPE_VSC)
        self.assertEqual(bepa.term_months, 72)

    def test_record_cross_tenant_contract_raises(self) -> None:
        with self.assertRaises(CrossTenantContractError):
            record_back_end_product(
                dealership=self.dealership,
                contract=self.other_contract,
                product_type=BEPA_TYPE_VSC,
                cost=Decimal("800.00"),
                retail_price=Decimal("1800.00"),
            )

    def test_record_unknown_product_type_raises(self) -> None:
        with self.assertRaises(ValueError):
            record_back_end_product(
                dealership=self.dealership,
                contract=self.contract,
                product_type="lojack",
                cost=Decimal("400.00"),
                retail_price=Decimal("800.00"),
            )

    def test_list_returns_all_products_for_contract(self) -> None:
        record_back_end_product(
            dealership=self.dealership,
            contract=self.contract,
            product_type=BEPA_TYPE_VSC,
            cost=Decimal("800.00"),
            retail_price=Decimal("1800.00"),
        )
        record_back_end_product(
            dealership=self.dealership,
            contract=self.contract,
            product_type=BEPA_TYPE_GAP,
            cost=Decimal("400.00"),
            retail_price=Decimal("900.00"),
        )
        self.assertEqual(list_products_for_contract(self.contract).count(), 2)


class FundingServiceTests(TestCase):
    """`record_funding` + `mark_funded` + `get_funding`."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(slug="fs", name="FS")
        self.other = Dealership.objects.create(slug="fs-other", name="Other")
        self.deal = _make_deal_structure(self.dealership)
        self.other_deal = _make_deal_structure(self.other, stock="FS-O")
        self.contract = record_contract(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        self.other_contract = record_contract(
            dealership=self.other,
            deal_structure=self.other_deal,
            contract_type=CONTRACT_TYPE_RISC,
        )

    def test_record_creates_pending_funding(self) -> None:
        funding = record_funding(
            dealership=self.dealership, contract=self.contract
        )
        self.assertEqual(funding.state, FUNDING_STATE_PENDING)
        self.assertIsNone(funding.funded_at)
        self.assertIsNone(funding.funding_amount)

    def test_record_cross_tenant_raises(self) -> None:
        with self.assertRaises(CrossTenantFundingError):
            record_funding(
                dealership=self.dealership, contract=self.other_contract
            )

    def test_record_duplicate_raises_typed_error(self) -> None:
        record_funding(dealership=self.dealership, contract=self.contract)
        with self.assertRaises(FundingAlreadyExistsError):
            record_funding(
                dealership=self.dealership, contract=self.contract
            )

    def test_mark_funded_populates_state_amount_and_funded_at(self) -> None:
        funding = record_funding(
            dealership=self.dealership, contract=self.contract
        )
        before = timezone.now()
        funded = mark_funded(
            funding,
            funding_amount=Decimal("24500.00"),  # lender discount fee
            notes="Discount 2% acquisition fee",
        )
        funded.refresh_from_db()
        self.assertEqual(funded.state, FUNDING_STATE_FUNDED)
        self.assertEqual(funded.funding_amount, Decimal("24500.00"))
        self.assertIsNotNone(funded.funded_at)
        self.assertGreaterEqual(funded.funded_at, before)
        self.assertEqual(funded.notes, "Discount 2% acquisition fee")

    def test_get_tenant_scoping(self) -> None:
        funding = record_funding(
            dealership=self.dealership, contract=self.contract
        )
        self.assertIsNotNone(
            get_funding(funding.pk, dealership=self.dealership)
        )
        self.assertIsNone(
            get_funding(funding.pk, dealership=self.other)
        )


# ---- Endpoint tests --------------------------------------------------------


class ContractEndpointTests(TestCase):
    """Contract create + PATCH sign/void endpoints."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(slug="ce-other", name="Other")
        self.deal = _make_deal_structure(self.dealership)
        self.other_deal = _make_deal_structure(self.other, stock="CE-O")
        self.client = _fandi_client_at(self.dealership, username="ce-fandi")

    def test_create_returns_201(self) -> None:
        response = self.client.post(
            reverse("dealer_ai:admin-contract-create"),
            {
                "deal_structure_id": self.deal.pk,
                "contract_type": CONTRACT_TYPE_RISC,
                "financed_amount": "25000.00",
                "total_of_payments": "32000.00",
                "finance_charge": "7000.00",
                "apr_disclosure": "9.9900",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["contract"]
        self.assertEqual(body["contract_type"], CONTRACT_TYPE_RISC)
        self.assertEqual(body["state"], CONTRACT_STATE_UNSIGNED)

    def test_create_cross_tenant_deal_returns_404(self) -> None:
        response = self.client.post(
            reverse("dealer_ai:admin-contract-create"),
            {
                "deal_structure_id": self.other_deal.pk,
                "contract_type": CONTRACT_TYPE_RISC,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_patch_sign_transitions_to_signed(self) -> None:
        contract = record_contract(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        response = self.client.patch(
            reverse(
                "dealer_ai:admin-contract-update",
                kwargs={"pk": contract.pk},
            ),
            {"action": "sign", "signer_name": "Alice"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["contract"]
        self.assertEqual(body["state"], CONTRACT_STATE_SIGNED)
        self.assertIsNotNone(body["signed_at"])
        self.assertEqual(body["signer_name"], "Alice")

    def test_patch_void_populates_voided_reason(self) -> None:
        contract = record_contract(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        response = self.client.patch(
            reverse(
                "dealer_ai:admin-contract-update",
                kwargs={"pk": contract.pk},
            ),
            {"action": "void", "voided_reason": "Errors on paper"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["contract"]
        self.assertEqual(body["state"], CONTRACT_STATE_VOIDED)
        self.assertEqual(body["voided_reason"], "Errors on paper")

    def test_patch_sign_after_void_returns_409(self) -> None:
        contract = record_contract(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        void_contract(contract, voided_reason="First void")
        response = self.client.patch(
            reverse(
                "dealer_ai:admin-contract-update",
                kwargs={"pk": contract.pk},
            ),
            {"action": "sign"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)


class BackEndProductEndpointTests(TestCase):
    """POST /admin/back-end-products/."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.deal = _make_deal_structure(self.dealership)
        self.contract = record_contract(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        self.client = _fandi_client_at(self.dealership, username="bee-fandi")

    def test_create_vsc_returns_201(self) -> None:
        response = self.client.post(
            reverse("dealer_ai:admin-back-end-product-create"),
            {
                "contract_id": self.contract.pk,
                "product_type": BEPA_TYPE_VSC,
                "cost": "800.00",
                "retail_price": "1800.00",
                "provider": "Zurich",
                "term_months": 72,
                "mileage_limit": 100000,
                "deductible": "100.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["back_end_product"]
        self.assertEqual(body["product_type"], BEPA_TYPE_VSC)
        self.assertEqual(body["cost"], "800.00")
        self.assertEqual(body["retail_price"], "1800.00")

    def test_create_cross_tenant_contract_returns_404(self) -> None:
        other = Dealership.objects.create(slug="bee-other", name="Other")
        other_deal = _make_deal_structure(other, stock="BEE-O")
        other_contract = record_contract(
            dealership=other,
            deal_structure=other_deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        response = self.client.post(
            reverse("dealer_ai:admin-back-end-product-create"),
            {
                "contract_id": other_contract.pk,
                "product_type": BEPA_TYPE_VSC,
                "cost": "800.00",
                "retail_price": "1800.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)


class FundingEndpointTests(TestCase):
    """POST /admin/funding/ + PATCH /admin/funding/<pk>/."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.deal = _make_deal_structure(self.dealership)
        self.contract = record_contract(
            dealership=self.dealership,
            deal_structure=self.deal,
            contract_type=CONTRACT_TYPE_RISC,
        )
        self.client = _fandi_client_at(self.dealership, username="fe-fandi")

    def test_create_returns_201_and_pending_state(self) -> None:
        response = self.client.post(
            reverse("dealer_ai:admin-funding-create"),
            {"contract_id": self.contract.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["funding"]
        self.assertEqual(body["state"], FUNDING_STATE_PENDING)
        self.assertIsNone(body["funding_amount"])

    def test_create_duplicate_funding_returns_409(self) -> None:
        record_funding(dealership=self.dealership, contract=self.contract)
        response = self.client.post(
            reverse("dealer_ai:admin-funding-create"),
            {"contract_id": self.contract.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_patch_mark_funded_populates_amount_and_funded_at(self) -> None:
        funding = record_funding(
            dealership=self.dealership, contract=self.contract
        )
        response = self.client.patch(
            reverse(
                "dealer_ai:admin-funding-update",
                kwargs={"pk": funding.pk},
            ),
            {"action": "mark_funded", "funding_amount": "24500.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["funding"]
        self.assertEqual(body["state"], FUNDING_STATE_FUNDED)
        self.assertEqual(body["funding_amount"], "24500.00")
        self.assertIsNotNone(body["funded_at"])

    def test_patch_unknown_pk_returns_404(self) -> None:
        response = self.client.patch(
            reverse(
                "dealer_ai:admin-funding-update", kwargs={"pk": 999999}
            ),
            {"action": "mark_funded", "funding_amount": "1000.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
