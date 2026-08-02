"""Milestone 10 · Increment 7 (SESSION_112) — ComplianceRecord tests.

Backend tests for the ComplianceRecord entity, additive URL
extensions on Stipulation + BEPA, service verbs, and endpoints
per ``MILESTONE_10_PLANNING.md`` §1.8 + §7 M10.7.
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
    BEPA_TYPE_VSC,
    CHARGEBACK_TYPE_FPD,
    CONTRACT_TYPE_RISC,
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_RETENTION_YEARS,
    ROLE_F_AND_I_MANAGER,
    SALE_FINANCE_TYPE_RETAIL,
    STIP_TYPE_PROOF_OF_INCOME,
    BackEndProductAgreement,
    Chargeback,
    ComplianceRecord,
    Contract,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Dealership,
    LenderProgram,
    LenderSubmission,
    Sale,
    Stipulation,
    Vehicle,
)
from dealer_ai.services.f_and_i import (
    ComplianceAlreadyExistsError,
    CrossTenantComplianceError,
    deal_jacket_summary,
    get_compliance,
    mark_funded,
    record_back_end_product,
    record_chargeback,
    record_compliance,
    record_contract,
    record_funding,
    record_lender_submission,
    record_stipulation,
    sign_contract,
    update_compliance,
    update_stipulation_state,
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


def _make_full_deal(dealership, *, stock: str = "M107-1") -> tuple[
    Contract, LenderSubmission, BackEndProductAgreement
]:
    """Build a full deal (Contract signed + Lender submission +
    BEPA) for a dealership. Returns the three main handles.
    """
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
    deal = DealStructure.objects.create(
        dealership=dealership,
        credit_application=credit_app,
        vehicle=vehicle,
        sale_price=Decimal("30000.00"),
        amount_financed=Decimal("25000.00"),
        apr=Decimal("9.99"),
        term_months=72,
        monthly_payment=Decimal("500.00"),
    )
    program = LenderProgram.objects.create(
        dealership=dealership, name=f"Bank-{stock}"
    )
    submission = record_lender_submission(
        dealership=dealership,
        deal_structure=deal,
        lender_program=program,
    )
    contract = record_contract(
        dealership=dealership,
        deal_structure=deal,
        contract_type=CONTRACT_TYPE_RISC,
    )
    sign_contract(contract, signer_name="Alice")
    contract.refresh_from_db()
    bepa = record_back_end_product(
        dealership=dealership,
        contract=contract,
        product_type=BEPA_TYPE_VSC,
        cost=Decimal("800.00"),
        retail_price=Decimal("1800.00"),
    )
    return contract, submission, bepa


def _fandi_client_at(dealership, *, username: str = "m107-fandi"):
    user = make_user(username=username)
    make_membership(user, dealership, ROLE_F_AND_I_MANAGER)
    return authenticated_client(user), user


# ---- Model tests ------------------------------------------------------------


class ComplianceModelTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(slug="cm7", name="CM7")
        self.other = Dealership.objects.create(slug="cm7-other", name="Other")
        self.contract, _, _ = _make_full_deal(self.dealership)
        self.other_contract, _, _ = _make_full_deal(
            self.other, stock="M107-O"
        )

    def test_create_persists_defaults(self) -> None:
        compliance = ComplianceRecord.objects.create(
            dealership=self.dealership, contract=self.contract
        )
        compliance.refresh_from_db()
        self.assertIsNone(compliance.reg_z_disclosed_at)
        self.assertIsNone(compliance.ofac_checked_at)
        self.assertFalse(compliance.ofac_hit)
        self.assertEqual(compliance.deal_jacket_url, "")

    def test_clean_refuses_cross_tenant_contract(self) -> None:
        compliance = ComplianceRecord(
            dealership=self.dealership, contract=self.other_contract
        )
        with self.assertRaises(ValidationError):
            compliance.clean()

    def test_onetoone_enforces_one_per_contract(self) -> None:
        ComplianceRecord.objects.create(
            dealership=self.dealership, contract=self.contract
        )
        # Second creation on the same contract fails at the DB layer
        # via the OneToOne unique constraint.
        from django.db.utils import IntegrityError

        with self.assertRaises(IntegrityError):
            ComplianceRecord.objects.create(
                dealership=self.dealership, contract=self.contract
            )


class EvidenceUrlExtensionTests(TestCase):
    """M10.7 additive URL fields on Stipulation + BEPA."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="eur", name="Evidence URL"
        )
        self.contract, self.submission, self.bepa = _make_full_deal(
            self.dealership
        )

    def test_stipulation_evidence_url_defaults_blank(self) -> None:
        stip = record_stipulation(
            dealership=self.dealership,
            lender_submission=self.submission,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
        )
        self.assertEqual(stip.evidence_url, "")

    def test_stipulation_evidence_url_accepts_valid_url(self) -> None:
        stip = record_stipulation(
            dealership=self.dealership,
            lender_submission=self.submission,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
        )
        stip.evidence_url = "https://drive.example.com/deal-1/paystub.pdf"
        stip.save(update_fields=["evidence_url"])
        stip.refresh_from_db()
        self.assertIn("drive.example.com", stip.evidence_url)

    def test_bepa_product_agreement_url_defaults_blank(self) -> None:
        self.assertEqual(self.bepa.product_agreement_url, "")


class ComplianceTenancyCarrierTests(TestCase):
    def test_compliance_is_a_tenant_carrier(self) -> None:
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 34)
        self.assertIn("ComplianceRecord", _TENANT_CARRIER_MODEL_NAMES)


# ---- Service tests ---------------------------------------------------------


class RecordComplianceTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(slug="rc7", name="RC7")
        self.other = Dealership.objects.create(slug="rc7-other", name="Other")
        self.contract, _, _ = _make_full_deal(self.dealership)
        self.other_contract, _, _ = _make_full_deal(
            self.other, stock="RC7-O"
        )

    def test_record_auto_populates_retention_from_ca(self) -> None:
        compliance = record_compliance(
            dealership=self.dealership, contract=self.contract
        )
        # retention_expires_at is denormalized from the parent CA.
        ca = (
            self.contract.deal_structure.credit_application
        )
        self.assertEqual(
            compliance.retention_expires_at, ca.retention_expires_at
        )

    def test_record_persists_deal_jacket_url_and_notes(self) -> None:
        compliance = record_compliance(
            dealership=self.dealership,
            contract=self.contract,
            deal_jacket_url="https://drive.example.com/jacket-42",
            notes="Filed after M10.1 CA intake.",
        )
        self.assertEqual(
            compliance.deal_jacket_url,
            "https://drive.example.com/jacket-42",
        )
        self.assertEqual(compliance.notes, "Filed after M10.1 CA intake.")

    def test_record_cross_tenant_raises(self) -> None:
        with self.assertRaises(CrossTenantComplianceError):
            record_compliance(
                dealership=self.dealership,
                contract=self.other_contract,
            )

    def test_record_duplicate_raises_typed_error(self) -> None:
        record_compliance(
            dealership=self.dealership, contract=self.contract
        )
        with self.assertRaises(ComplianceAlreadyExistsError):
            record_compliance(
                dealership=self.dealership, contract=self.contract
            )


class UpdateComplianceTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(slug="uc7", name="UC7")
        self.contract, _, _ = _make_full_deal(self.dealership)
        self.compliance = record_compliance(
            dealership=self.dealership, contract=self.contract
        )

    def test_partial_update_persists_changed_fields(self) -> None:
        now = timezone.now()
        updated = update_compliance(
            self.compliance,
            reg_z_disclosed_at=now,
            ofac_checked_at=now,
            ofac_hit=False,
        )
        updated.refresh_from_db()
        self.assertIsNotNone(updated.reg_z_disclosed_at)
        self.assertIsNotNone(updated.ofac_checked_at)
        self.assertFalse(updated.ofac_hit)

    def test_partial_update_preserves_unspecified_fields(self) -> None:
        # First: populate two fields.
        now = timezone.now()
        update_compliance(
            self.compliance,
            reg_z_disclosed_at=now,
            red_flags_notes="Verified DL matches address.",
        )
        # Then: update only red_flags_reviewed_at — the two prior
        # fields should stay.
        update_compliance(
            self.compliance, red_flags_reviewed_at=now
        )
        self.compliance.refresh_from_db()
        self.assertIsNotNone(self.compliance.reg_z_disclosed_at)
        self.assertEqual(
            self.compliance.red_flags_notes,
            "Verified DL matches address.",
        )
        self.assertIsNotNone(self.compliance.red_flags_reviewed_at)

    def test_unknown_field_raises(self) -> None:
        with self.assertRaises(ValueError):
            update_compliance(self.compliance, wrong_column="x")

    def test_no_kwargs_is_noop(self) -> None:
        # Empty update should not raise or change updated_at.
        result = update_compliance(self.compliance)
        self.assertEqual(result.pk, self.compliance.pk)


class GetComplianceTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(slug="gc7", name="GC7")
        self.other = Dealership.objects.create(slug="gc7-o", name="Other")
        self.contract, _, _ = _make_full_deal(self.dealership)
        self.compliance = record_compliance(
            dealership=self.dealership, contract=self.contract
        )

    def test_returns_matching_tenant_row(self) -> None:
        self.assertIsNotNone(
            get_compliance(self.compliance.pk, dealership=self.dealership)
        )

    def test_returns_none_for_cross_tenant_pk(self) -> None:
        self.assertIsNone(
            get_compliance(self.compliance.pk, dealership=self.other)
        )


class DealJacketSummaryTests(TestCase):
    """`deal_jacket_summary` aggregate — powers the operator UI."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(slug="djs", name="DJS")
        self.contract, self.submission, self.bepa = _make_full_deal(
            self.dealership
        )
        # Populate downstream state: funding + stip + chargeback.
        self.funding = record_funding(
            dealership=self.dealership, contract=self.contract
        )
        mark_funded(self.funding, funding_amount=Decimal("24500.00"))
        self.stip = record_stipulation(
            dealership=self.dealership,
            lender_submission=self.submission,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
        )
        self.chargeback = record_chargeback(
            dealership=self.dealership,
            contract=self.contract,
            bepa=self.bepa,
            chargeback_type=CHARGEBACK_TYPE_FPD,
            chargeback_date=dt.date(2026, 8, 20),
            chargeback_amount=Decimal("500.00"),
            skip_funding_transition=True,
        )

    def test_summary_returns_contract_state(self) -> None:
        summary = deal_jacket_summary(self.contract)
        self.assertEqual(summary["contract"]["id"], self.contract.pk)
        self.assertEqual(summary["contract"]["state"], "signed")

    def test_summary_includes_related_stipulations(self) -> None:
        summary = deal_jacket_summary(self.contract)
        self.assertEqual(len(summary["stipulations"]), 1)
        self.assertEqual(
            summary["stipulations"][0]["stip_type"], STIP_TYPE_PROOF_OF_INCOME
        )

    def test_summary_includes_bepas(self) -> None:
        summary = deal_jacket_summary(self.contract)
        self.assertEqual(len(summary["back_end_products"]), 1)
        self.assertEqual(
            summary["back_end_products"][0]["product_type"], BEPA_TYPE_VSC
        )

    def test_summary_includes_chargebacks(self) -> None:
        summary = deal_jacket_summary(self.contract)
        self.assertEqual(len(summary["chargebacks"]), 1)
        self.assertEqual(
            summary["chargebacks"][0]["chargeback_type"], CHARGEBACK_TYPE_FPD
        )

    def test_summary_includes_funding_state(self) -> None:
        summary = deal_jacket_summary(self.contract)
        self.assertEqual(summary["funding"]["state"], "funded")
        self.assertEqual(summary["funding"]["funding_amount"], "24500.00")

    def test_summary_compliance_is_none_when_no_record(self) -> None:
        summary = deal_jacket_summary(self.contract)
        self.assertIsNone(summary["compliance"])

    def test_summary_compliance_populated_when_record_exists(self) -> None:
        compliance = record_compliance(
            dealership=self.dealership, contract=self.contract
        )
        update_compliance(compliance, ofac_hit=True)
        self.contract.refresh_from_db()
        summary = deal_jacket_summary(self.contract)
        self.assertIsNotNone(summary["compliance"])
        self.assertTrue(summary["compliance"]["ofac_hit"])


# ---- Endpoint tests --------------------------------------------------------


class ComplianceEndpointTests(TestCase):
    """POST + PATCH /admin/compliance-records/."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.contract, _, _ = _make_full_deal(self.dealership)
        self.client, self.user = _fandi_client_at(self.dealership)

    def test_create_returns_201(self) -> None:
        response = self.client.post(
            reverse("dealer_ai:admin-compliance-create"),
            {"contract_id": self.contract.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["compliance"]
        self.assertEqual(body["contract_id"], self.contract.pk)
        self.assertIsNone(body["reg_z_disclosed_at"])

    def test_create_duplicate_returns_409(self) -> None:
        record_compliance(
            dealership=self.dealership, contract=self.contract
        )
        response = self.client.post(
            reverse("dealer_ai:admin-compliance-create"),
            {"contract_id": self.contract.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_patch_partial_update_returns_200(self) -> None:
        compliance = record_compliance(
            dealership=self.dealership, contract=self.contract
        )
        response = self.client.patch(
            reverse(
                "dealer_ai:admin-compliance-update",
                kwargs={"pk": compliance.pk},
            ),
            {"ofac_hit": True, "red_flags_notes": "Address discrepancy"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["compliance"]
        self.assertTrue(body["ofac_hit"])
        self.assertEqual(body["red_flags_notes"], "Address discrepancy")

    def test_deal_jacket_read_returns_summary(self) -> None:
        record_compliance(
            dealership=self.dealership, contract=self.contract
        )
        response = self.client.get(
            reverse(
                "dealer_ai:admin-deal-jacket-read",
                kwargs={"contract_pk": self.contract.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["deal_jacket"]
        self.assertEqual(body["contract"]["id"], self.contract.pk)
        self.assertIsNotNone(body["compliance"])
        self.assertEqual(body["stipulations"], [])

    def test_deal_jacket_read_unknown_contract_returns_404(self) -> None:
        response = self.client.get(
            reverse(
                "dealer_ai:admin-deal-jacket-read",
                kwargs={"contract_pk": 999999},
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_deals_list_returns_contract(self) -> None:
        response = self.client.get(
            reverse("dealer_ai:admin-f-and-i-deals-list")
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["deals"]
        ids = [d["contract_id"] for d in body]
        self.assertIn(self.contract.pk, ids)

    def test_deals_list_state_filter_narrows_result(self) -> None:
        # self.contract state is 'signed'. Filter to 'unsigned' — empty.
        response = self.client.get(
            reverse("dealer_ai:admin-f-and-i-deals-list") + "?state=unsigned"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deals"], [])
