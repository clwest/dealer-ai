"""Milestone 10 · Increment 4 (SESSION_109) — Stipulation endpoint tests.

Locks the HTTP surface of the two new views in
:mod:`views_f_and_i` per ``MILESTONE_10_PLANNING.md`` §7 M10.4.

Coverage:

- Auth positive path (f_and_i_manager, dealer_owner) —
  extended matrix inherited from M10.1's tests.
- Create 201 + response shape.
- Cross-tenant lender_submission → 404 (never leak).
- Invalid stip_type → 400; missing required field → 400.
- PATCH state 200 with cleared_at auto-populated + documented_by
  from request.user.
- Unknown state → 400; unknown / cross-tenant pk → 404.
"""

from __future__ import annotations

from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_RETENTION_YEARS,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    STIP_TYPE_PROOF_OF_INCOME,
    STIP_TYPE_PROOF_OF_INSURANCE,
    STIPULATION_STATE_CLEARED,
    STIPULATION_STATE_OPEN,
    STIPULATION_STATE_WAIVED,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Dealership,
    LenderProgram,
    LenderSubmission,
    Stipulation,
    Vehicle,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import (
    authenticated_client,
    make_membership,
    make_user,
)


CREATE_URL = "dealer_ai:admin-stipulation-create"
UPDATE_URL = "dealer_ai:admin-stipulation-update"


def _make_lender_submission(dealership, *, stock: str = "SE-1") -> LenderSubmission:
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
        dealership=dealership, name=f"P-{stock}"
    )
    return LenderSubmission.objects.create(
        dealership=dealership,
        deal_structure=deal,
        lender_program=program,
        submitted_at=timezone.now(),
    )


def _fandi_client_at(dealership, username: str = "stip-fandi"):
    user = make_user(username=username)
    make_membership(user, dealership, ROLE_F_AND_I_MANAGER)
    return authenticated_client(user), user


class StipulationCreateEndpointTests(TestCase):
    """`POST /admin/stipulations/`."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="stipe-other", name="Other"
        )
        self.submission = _make_lender_submission(self.dealership)
        self.other_submission = _make_lender_submission(
            self.other, stock="SE-OTHER"
        )
        self.client, _ = _fandi_client_at(self.dealership)

    def test_dealer_owner_can_create(self) -> None:
        user = make_user(username="stip-owner")
        make_membership(user, self.dealership, ROLE_DEALER_OWNER)
        response = authenticated_client(user).post(
            reverse(CREATE_URL),
            {
                "lender_submission_id": self.submission.pk,
                "stip_type": STIP_TYPE_PROOF_OF_INCOME,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_create_returns_201_with_projected_row(self) -> None:
        response = self.client.post(
            reverse(CREATE_URL),
            {
                "lender_submission_id": self.submission.pk,
                "stip_type": STIP_TYPE_PROOF_OF_INSURANCE,
                "notes": "Need decl page with lender as loss payee.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["stipulation"]
        self.assertEqual(body["lender_submission_id"], self.submission.pk)
        self.assertEqual(body["stip_type"], STIP_TYPE_PROOF_OF_INSURANCE)
        self.assertEqual(body["state"], STIPULATION_STATE_OPEN)
        self.assertIsNone(body["cleared_at"])
        self.assertIsNone(body["documented_by_id"])

    def test_cross_tenant_submission_returns_404(self) -> None:
        response = self.client.post(
            reverse(CREATE_URL),
            {
                "lender_submission_id": self.other_submission.pk,
                "stip_type": STIP_TYPE_PROOF_OF_INCOME,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_invalid_stip_type_returns_400(self) -> None:
        response = self.client.post(
            reverse(CREATE_URL),
            {
                "lender_submission_id": self.submission.pk,
                "stip_type": "tax_return",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_submission_id_returns_400(self) -> None:
        response = self.client.post(
            reverse(CREATE_URL),
            {"stip_type": STIP_TYPE_PROOF_OF_INCOME},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class StipulationUpdateEndpointTests(TestCase):
    """`PATCH /admin/stipulations/<pk>/`."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="stipu-other", name="Other"
        )
        self.submission = _make_lender_submission(self.dealership)
        self.other_submission = _make_lender_submission(
            self.other, stock="SU-OTHER"
        )
        self.stip = Stipulation.objects.create(
            dealership=self.dealership,
            lender_submission=self.submission,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
        )
        self.other_stip = Stipulation.objects.create(
            dealership=self.other,
            lender_submission=self.other_submission,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
        )
        self.client, self.user = _fandi_client_at(
            self.dealership, username="stip-updater"
        )

    def _patch(self, pk, body):
        return self.client.patch(
            reverse(UPDATE_URL, kwargs={"pk": pk}),
            body,
            format="json",
        )

    def test_state_change_to_cleared_populates_cleared_at_and_documented_by(
        self,
    ) -> None:
        response = self._patch(
            self.stip.pk, {"state": STIPULATION_STATE_CLEARED}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["stipulation"]
        self.assertEqual(body["state"], STIPULATION_STATE_CLEARED)
        self.assertIsNotNone(body["cleared_at"])
        # documented_by sourced from request.user, not request body.
        self.assertEqual(body["documented_by_id"], self.user.pk)

    def test_state_change_to_waived_populates_cleared_at(self) -> None:
        response = self._patch(
            self.stip.pk, {"state": STIPULATION_STATE_WAIVED}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["stipulation"]["cleared_at"])

    def test_partial_update_notes_persists(self) -> None:
        response = self._patch(
            self.stip.pk,
            {
                "state": STIPULATION_STATE_CLEARED,
                "notes": "Received via email.",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["stipulation"]["notes"], "Received via email."
        )

    def test_unknown_state_returns_400(self) -> None:
        response = self._patch(self.stip.pk, {"state": "funded"})
        self.assertEqual(response.status_code, 400)

    def test_unknown_pk_returns_404(self) -> None:
        response = self._patch(
            999999, {"state": STIPULATION_STATE_CLEARED}
        )
        self.assertEqual(response.status_code, 404)

    def test_cross_tenant_pk_returns_404(self) -> None:
        response = self._patch(
            self.other_stip.pk, {"state": STIPULATION_STATE_CLEARED}
        )
        self.assertEqual(response.status_code, 404)
