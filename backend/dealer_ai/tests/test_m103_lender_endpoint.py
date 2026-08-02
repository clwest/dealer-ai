"""Milestone 10 · Increment 3 (SESSION_108) — Lender endpoint tests.

Locks the HTTP surface of the three new views in
:mod:`views_f_and_i` per ``MILESTONE_10_PLANNING.md`` §7 M10.3.

Coverage:

- Auth matrix on `POST /admin/lender-programs/` inherited from the
  M10.1/M10.2 permission class — just verify the two positive
  roles here; the extended matrix is locked in M10.1's tests.
- Create program 201 (happy) and 409 on duplicate.
- Create submission 201 (happy) and 404 on cross-tenant deal /
  program.
- PATCH submission 200 (status change + terms) and 400 on
  unknown status; 404 on unknown / cross-tenant pk.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_RETENTION_YEARS,
    LENDER_SUBMISSION_STATUS_APPROVED,
    LENDER_SUBMISSION_STATUS_COUNTER,
    LENDER_SUBMISSION_STATUS_PENDING,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Dealership,
    LenderProgram,
    LenderSubmission,
    Vehicle,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import (
    authenticated_client,
    make_membership,
    make_user,
)


PROGRAM_URL = "dealer_ai:admin-lender-program-create"
SUBMISSION_CREATE_URL = "dealer_ai:admin-lender-submission-create"
SUBMISSION_UPDATE_URL = "dealer_ai:admin-lender-submission-update"


def _make_vehicle(dealership, *, stock: str = "LDE-1") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28500.00"),
        dealership=dealership,
    )


def _make_credit_app(dealership, *, name: str = "Alice") -> CreditApplication:
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
    )


def _make_deal_structure(dealership, credit_app, vehicle) -> DealStructure:
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


def _fandi_client_at(dealership, username: str = "lender-fandi"):
    user = make_user(username=username)
    make_membership(user, dealership, ROLE_F_AND_I_MANAGER)
    return authenticated_client(user)


class LenderProgramEndpointTests(TestCase):
    """`POST /admin/lender-programs/`."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.client = _fandi_client_at(self.dealership)

    def test_dealer_owner_can_create_program(self) -> None:
        user = make_user(username="lp-owner")
        make_membership(user, self.dealership, ROLE_DEALER_OWNER)
        response = authenticated_client(user).post(
            reverse(PROGRAM_URL),
            {"name": "Owner Bank"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_create_persists_all_fields(self) -> None:
        response = self.client.post(
            reverse(PROGRAM_URL),
            {
                "name": "Prime Bank",
                "contact": "rep@primebank.com",
                "terms_summary": "Prime; 84mo max",
                "is_active": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["lender_program"]
        self.assertEqual(body["name"], "Prime Bank")
        self.assertEqual(body["contact"], "rep@primebank.com")
        self.assertEqual(body["terms_summary"], "Prime; 84mo max")
        self.assertFalse(body["is_active"])

    def test_duplicate_name_returns_409(self) -> None:
        self.client.post(
            reverse(PROGRAM_URL), {"name": "Dup Bank"}, format="json"
        )
        response = self.client.post(
            reverse(PROGRAM_URL), {"name": "Dup Bank"}, format="json"
        )
        self.assertEqual(response.status_code, 409)

    def test_missing_name_returns_400(self) -> None:
        response = self.client.post(reverse(PROGRAM_URL), {}, format="json")
        self.assertEqual(response.status_code, 400)


class LenderSubmissionCreateEndpointTests(TestCase):
    """`POST /admin/lender-submissions/`."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="lse-other", name="Other"
        )
        self.credit_app = _make_credit_app(self.dealership)
        self.other_credit_app = _make_credit_app(self.other, name="Other")
        self.vehicle = _make_vehicle(self.dealership, stock="LSE-V-1")
        self.other_vehicle = _make_vehicle(self.other, stock="LSE-OTHER")
        self.deal = _make_deal_structure(
            self.dealership, self.credit_app, self.vehicle
        )
        self.other_deal = _make_deal_structure(
            self.other, self.other_credit_app, self.other_vehicle
        )
        self.program = LenderProgram.objects.create(
            dealership=self.dealership, name="Sub Bank"
        )
        self.other_program = LenderProgram.objects.create(
            dealership=self.other, name="Other Sub Bank"
        )
        self.client = _fandi_client_at(self.dealership, username="lse-fandi")

    def test_create_returns_201_and_projected_row(self) -> None:
        response = self.client.post(
            reverse(SUBMISSION_CREATE_URL),
            {
                "deal_structure_id": self.deal.pk,
                "lender_program_id": self.program.pk,
                "status": LENDER_SUBMISSION_STATUS_APPROVED,
                "approval_terms": {"apr": "9.99"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["lender_submission"]
        self.assertEqual(body["deal_structure_id"], self.deal.pk)
        self.assertEqual(body["lender_program_id"], self.program.pk)
        self.assertEqual(body["lender_program_name"], "Sub Bank")
        self.assertEqual(body["status"], LENDER_SUBMISSION_STATUS_APPROVED)
        self.assertEqual(body["approval_terms"], {"apr": "9.99"})

    def test_create_defaults_status_to_pending(self) -> None:
        response = self.client.post(
            reverse(SUBMISSION_CREATE_URL),
            {
                "deal_structure_id": self.deal.pk,
                "lender_program_id": self.program.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["lender_submission"]["status"],
            LENDER_SUBMISSION_STATUS_PENDING,
        )

    def test_cross_tenant_deal_returns_404(self) -> None:
        response = self.client.post(
            reverse(SUBMISSION_CREATE_URL),
            {
                "deal_structure_id": self.other_deal.pk,
                "lender_program_id": self.program.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_cross_tenant_program_returns_404(self) -> None:
        response = self.client.post(
            reverse(SUBMISSION_CREATE_URL),
            {
                "deal_structure_id": self.deal.pk,
                "lender_program_id": self.other_program.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_missing_deal_returns_400(self) -> None:
        response = self.client.post(
            reverse(SUBMISSION_CREATE_URL),
            {"lender_program_id": self.program.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class LenderSubmissionUpdateEndpointTests(TestCase):
    """`PATCH /admin/lender-submissions/<pk>/`."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="lsu-other", name="Other Update"
        )
        self.credit_app = _make_credit_app(self.dealership)
        self.other_credit_app = _make_credit_app(self.other, name="Other")
        self.vehicle = _make_vehicle(self.dealership, stock="LSU-V-1")
        self.other_vehicle = _make_vehicle(self.other, stock="LSU-OTHER")
        self.deal = _make_deal_structure(
            self.dealership, self.credit_app, self.vehicle
        )
        self.other_deal = _make_deal_structure(
            self.other, self.other_credit_app, self.other_vehicle
        )
        self.program = LenderProgram.objects.create(
            dealership=self.dealership, name="Update Bank"
        )
        self.other_program = LenderProgram.objects.create(
            dealership=self.other, name="Other Update Bank"
        )
        self.submission = LenderSubmission.objects.create(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.program,
            submitted_at=timezone.now(),
        )
        self.other_submission = LenderSubmission.objects.create(
            dealership=self.other,
            deal_structure=self.other_deal,
            lender_program=self.other_program,
            submitted_at=timezone.now(),
        )
        self.client = _fandi_client_at(self.dealership, username="lsu-fandi")

    def _patch(self, pk, body):
        return self.client.patch(
            reverse(SUBMISSION_UPDATE_URL, kwargs={"pk": pk}),
            body,
            format="json",
        )

    def test_status_change_to_counter_returns_200(self) -> None:
        response = self._patch(
            self.submission.pk,
            {
                "status": LENDER_SUBMISSION_STATUS_COUNTER,
                "counter_terms": {"apr": "12.99"},
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["lender_submission"]
        self.assertEqual(body["status"], LENDER_SUBMISSION_STATUS_COUNTER)
        self.assertEqual(body["counter_terms"], {"apr": "12.99"})

    def test_partial_update_preserves_other_fields(self) -> None:
        # First: full update to set some baseline data.
        self._patch(
            self.submission.pk,
            {
                "status": LENDER_SUBMISSION_STATUS_APPROVED,
                "approval_terms": {"apr": "9.99"},
                "notes": "Initial approval",
            },
        )
        # Second: change status only — notes + approval_terms
        # should persist.
        self._patch(
            self.submission.pk,
            {"status": LENDER_SUBMISSION_STATUS_COUNTER},
        )
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, LENDER_SUBMISSION_STATUS_COUNTER)
        self.assertEqual(self.submission.approval_terms, {"apr": "9.99"})
        self.assertEqual(self.submission.notes, "Initial approval")

    def test_unknown_status_returns_400(self) -> None:
        response = self._patch(self.submission.pk, {"status": "funded"})
        self.assertEqual(response.status_code, 400)

    def test_unknown_pk_returns_404(self) -> None:
        response = self._patch(
            999999, {"status": LENDER_SUBMISSION_STATUS_APPROVED}
        )
        self.assertEqual(response.status_code, 404)

    def test_cross_tenant_pk_returns_404(self) -> None:
        # other_submission belongs to self.other, but we call as the
        # default-tenant client.
        response = self._patch(
            self.other_submission.pk,
            {"status": LENDER_SUBMISSION_STATUS_APPROVED},
        )
        self.assertEqual(response.status_code, 404)
