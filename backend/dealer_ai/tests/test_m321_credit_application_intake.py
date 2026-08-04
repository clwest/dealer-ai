"""Milestone 32 · Increment 1 (SESSION_207) — CreditApplication intake
+ provenance-FK tests.

Locks the M32.1 read surface for the F&I intake queue + the D9-
revised² OneToOneField backpointer per
``MILESTONE_32_PLANNING.md`` §5.b D3 + D9-revised².

One new endpoint gated on
``IsFinanceManagerOrOwnerAtActiveDealership`` (reuses M10.7 class —
zero-drift streak preserved) — first F&I-role-gated list endpoint:

- ``GET /admin/credit-applications/`` — tenant-scoped list,
  filterable by ``intake`` (accepts only ``true``), ``lead_id``,
  ``since``. Fail-explicit query validation.

Coverage:

- Service ``list_credit_applications`` — intake filter, lead
  filter, since filter, composition, cross-tenant lead.
- Endpoint list — fail-explicit ``intake`` matrix (including
  ``false`` → 400 per §5.h reserved-and-rejected value), fail-
  explicit ``lead_id``, fail-explicit ``since``, permission matrix,
  projection includes writeup context for hand-off-created CAs,
  NULL backpointer for direct-created CAs.
- Provenance FK behavior — hand-off sets backpointer;
  ``record_credit_application`` accepts ``deal_writeup=``;
  ``DealWriteupAlreadyLinkedError`` raised via service guard;
  ``IntegrityError`` raised via bypass-service direct ORM;
  determinism when a lead has multiple writeups → multiple CAs;
  writeup delete → backpointer becomes NULL (SET_NULL).
- **Mandatory** ``test_writeup_cannot_link_to_multiple_credit_applications``
  exercising all three defense layers per D9-revised².
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    CREDIT_APP_FORMAT_TABLET,
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_SALES_MANAGER,
    CreditApplication,
    CustomerLead,
    Dealership,
    DealWriteup,
    Vehicle,
)
from dealer_ai.services.deal_writeups import (
    approve_deal_writeup,
    hand_off_to_fandi,
    record_deal_writeup,
)
from dealer_ai.services.f_and_i import (
    CrossTenantCreditApplicationError,
    DealWriteupAlreadyLinkedError,
    list_credit_applications,
    record_credit_application,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import (
    authenticated_client,
    make_membership,
    make_user,
)


LIST_ENDPOINT = "dealer_ai:admin-credit-application-list"


def _make_vehicle(dealership: Dealership, stock: str) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("40000.00"),
        dealership=dealership,
    )


def _make_approved_writeup(
    dealership: Dealership, *, stock: str, lead_name: str = "L",
) -> DealWriteup:
    lead = CustomerLead.objects.create(dealership=dealership, name=lead_name)
    vehicle = _make_vehicle(dealership, stock)
    writeup = record_deal_writeup(
        dealership=dealership, lead=lead, vehicle=vehicle,
        vehicle_price=Decimal("28500.00"),
        monthly_payment_target=Decimal("450.00"),
        term_months_target=72,
        apr_target=Decimal("7.49"),
    )
    approver = make_user(username=f"mgr-{stock}")
    make_membership(approver, dealership, ROLE_SALES_MANAGER)
    approve_deal_writeup(writeup=writeup, approved_by_user=approver)
    return writeup


# ---------------------------------------------------------------------------
# Provenance FK behavior — D9-revised² three-layer defense
# ---------------------------------------------------------------------------


class ProvenanceFKBehaviorTests(TestCase):
    def setUp(self) -> None:
        self.d = Dealership.objects.create(slug="p-fk", name="Prov FK")

    def test_hand_off_sets_backpointer(self) -> None:
        writeup = _make_approved_writeup(self.d, stock="P-1")
        writeup, ca = hand_off_to_fandi(writeup=writeup)
        self.assertEqual(ca.deal_writeup_id, writeup.pk)

    def test_record_credit_application_direct_leaves_backpointer_null(
        self,
    ) -> None:
        lead = CustomerLead.objects.create(dealership=self.d, name="Direct")
        ca = record_credit_application(
            dealership=self.d, applicant_full_name="Direct Al",
            source_format=CREDIT_APP_FORMAT_TABLET, lead=lead,
        )
        self.assertIsNone(ca.deal_writeup_id)

    def test_record_credit_application_accepts_deal_writeup_kwarg(
        self,
    ) -> None:
        writeup = _make_approved_writeup(self.d, stock="P-K")
        ca = record_credit_application(
            dealership=self.d, applicant_full_name="Al",
            source_format=CREDIT_APP_FORMAT_TABLET,
            lead=writeup.lead, deal_writeup=writeup,
        )
        self.assertEqual(ca.deal_writeup_id, writeup.pk)

    def test_writeup_delete_nulls_backpointer_not_deletes_ca(self) -> None:
        writeup = _make_approved_writeup(self.d, stock="P-D")
        _, ca = hand_off_to_fandi(writeup=writeup)
        writeup_pk = writeup.pk
        ca_pk = ca.pk
        # Force writeup delete via bypass of any lifecycle constraint —
        # DealWriteup has no delete guard today. SET_NULL should keep
        # the CA row.
        DealWriteup.objects.filter(pk=writeup_pk).delete()
        ca.refresh_from_db()
        self.assertIsNone(ca.deal_writeup_id)
        self.assertTrue(CreditApplication.objects.filter(pk=ca_pk).exists())

    def test_cross_tenant_deal_writeup_raises_cross_tenant_error(
        self,
    ) -> None:
        other = Dealership.objects.create(slug="p-o", name="P Other")
        writeup_other = _make_approved_writeup(other, stock="P-X")
        lead_local = CustomerLead.objects.create(
            dealership=self.d, name="Local"
        )
        with self.assertRaises(CrossTenantCreditApplicationError):
            record_credit_application(
                dealership=self.d, applicant_full_name="A",
                source_format=CREDIT_APP_FORMAT_TABLET,
                lead=lead_local, deal_writeup=writeup_other,
            )

    def test_multiple_writeups_per_lead_pair_deterministically(self) -> None:
        """One lead → two writeups → two hand-offs → two CAs, each paired
        unambiguously via the FK (not via shared lead FK)."""
        lead = CustomerLead.objects.create(
            dealership=self.d, name="Multi"
        )
        v1 = _make_vehicle(self.d, "M-1")
        v2 = _make_vehicle(self.d, "M-2")
        w1 = record_deal_writeup(
            dealership=self.d, lead=lead, vehicle=v1,
            vehicle_price=Decimal("20000.00"),
        )
        w2 = record_deal_writeup(
            dealership=self.d, lead=lead, vehicle=v2,
            vehicle_price=Decimal("35000.00"),
        )
        approver = make_user(username="multi-mgr")
        make_membership(approver, self.d, ROLE_SALES_MANAGER)
        approve_deal_writeup(writeup=w1, approved_by_user=approver)
        approve_deal_writeup(writeup=w2, approved_by_user=approver)

        _, ca1 = hand_off_to_fandi(writeup=w1)
        _, ca2 = hand_off_to_fandi(writeup=w2)

        self.assertNotEqual(ca1.pk, ca2.pk)
        self.assertEqual(ca1.deal_writeup_id, w1.pk)
        self.assertEqual(ca2.deal_writeup_id, w2.pk)
        # And querying by writeup pk returns exactly one CA each.
        self.assertEqual(
            CreditApplication.objects.filter(deal_writeup=w1).count(), 1
        )
        self.assertEqual(
            CreditApplication.objects.filter(deal_writeup=w2).count(), 1
        )

    # -------------------------------------------------------------------
    # MANDATORY per M32.0 §5.b D9-revised² — three-layer defense
    # -------------------------------------------------------------------

    def test_writeup_cannot_link_to_multiple_credit_applications(
        self,
    ) -> None:
        """Belt (OneToOne unique) + suspenders (service guard) + M11.3
        idempotency. Exercises all three defense layers per
        MILESTONE_32_PLANNING.md §5.b D9-revised².
        """
        writeup = _make_approved_writeup(self.d, stock="MND")
        # Layer 3 (M11.3 shipped): hand-off creates first CA.
        _, ca1 = hand_off_to_fandi(writeup=writeup)
        self.assertEqual(ca1.deal_writeup_id, writeup.pk)

        # Layer 2 (service): record_credit_application with the same
        # writeup raises DealWriteupAlreadyLinkedError before DB write.
        with self.assertRaises(DealWriteupAlreadyLinkedError):
            record_credit_application(
                dealership=self.d, applicant_full_name="Bob",
                source_format=CREDIT_APP_FORMAT_TABLET,
                lead=writeup.lead, deal_writeup=writeup,
            )

        # Layer 1 (database): bypass the service via direct ORM. The
        # OneToOne unique constraint raises IntegrityError.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CreditApplication.objects.create(
                    dealership=self.d,
                    applicant_full_name="Carol",
                    source_format=CREDIT_APP_FORMAT_TABLET,
                    lead=writeup.lead,
                    deal_writeup=writeup,
                    captured_at=timezone.now(),
                    retention_expires_at=(
                        timezone.now() + timedelta(days=365 * 7)
                    ),
                )


# ---------------------------------------------------------------------------
# Service layer — list_credit_applications
# ---------------------------------------------------------------------------


class ListCreditApplicationsServiceTests(TestCase):
    def setUp(self) -> None:
        self.d = Dealership.objects.create(slug="l-ca", name="L CA")
        self.other = Dealership.objects.create(slug="l-ca-o", name="L Other")

        # Direct-create CAs (no writeup upstream).
        self.direct_lead = CustomerLead.objects.create(
            dealership=self.d, name="Direct"
        )
        self.direct_ca = record_credit_application(
            dealership=self.d, applicant_full_name="Direct A",
            source_format=CREDIT_APP_FORMAT_TABLET, lead=self.direct_lead,
        )
        # Hand-off-created CA.
        self.writeup = _make_approved_writeup(self.d, stock="L-W", lead_name="Handoff")
        _, self.handoff_ca = hand_off_to_fandi(writeup=self.writeup)
        # Cross-tenant CA.
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross"
        )
        self.cross_ca = record_credit_application(
            dealership=self.other, applicant_full_name="Cross A",
            source_format=CREDIT_APP_FORMAT_TABLET, lead=self.cross_lead,
        )

    def test_no_filter_returns_dealership_scoped(self) -> None:
        rows = list_credit_applications(dealership=self.d)
        pks = {c.pk for c in rows}
        self.assertEqual(pks, {self.direct_ca.pk, self.handoff_ca.pk})
        self.assertNotIn(self.cross_ca.pk, pks)

    def test_intake_true_returns_both_pre_contract_cas(self) -> None:
        # Both direct + handoff CAs are pre-contract at this point.
        rows = list_credit_applications(dealership=self.d, intake=True)
        self.assertEqual(
            {c.pk for c in rows}, {self.direct_ca.pk, self.handoff_ca.pk},
        )

    def test_lead_filter_scopes_to_lead(self) -> None:
        rows = list_credit_applications(
            dealership=self.d, lead=self.writeup.lead,
        )
        self.assertEqual([c.pk for c in rows], [self.handoff_ca.pk])

    def test_cross_tenant_lead_raises(self) -> None:
        with self.assertRaises(CrossTenantCreditApplicationError):
            list_credit_applications(
                dealership=self.d, lead=self.cross_lead,
            )

    def test_since_filter_excludes_older_rows(self) -> None:
        future = timezone.now() + timedelta(days=1)
        rows = list_credit_applications(dealership=self.d, since=future)
        self.assertEqual(rows, [])


# ---------------------------------------------------------------------------
# Endpoint layer — GET /admin/credit-applications/
# ---------------------------------------------------------------------------


class CreditApplicationListEndpointAuthTests(TestCase):
    def setUp(self) -> None:
        self.d = get_default_dealership()

    def test_unauthenticated_returns_401_or_403(self) -> None:
        resp = APIClient().get(reverse(LIST_ENDPOINT))
        self.assertIn(resp.status_code, (401, 403))

    def test_no_membership_returns_403(self) -> None:
        user = make_user(username="cal-nomem")
        resp = authenticated_client(user).get(reverse(LIST_ENDPOINT))
        self.assertEqual(resp.status_code, 403)

    def test_advisor_forbidden(self) -> None:
        user = make_user(username="cal-adv")
        make_membership(user, self.d, ROLE_ADVISOR)
        resp = authenticated_client(user).get(reverse(LIST_ENDPOINT))
        self.assertEqual(resp.status_code, 403)

    def test_sales_manager_forbidden(self) -> None:
        # F&I-gated endpoint; sales manager is NOT allowed even though
        # they manage the upstream writeup flow.
        user = make_user(username="cal-sm")
        make_membership(user, self.d, ROLE_SALES_MANAGER)
        resp = authenticated_client(user).get(reverse(LIST_ENDPOINT))
        self.assertEqual(resp.status_code, 403)

    def test_f_and_i_manager_allowed(self) -> None:
        user = make_user(username="cal-fandi")
        make_membership(user, self.d, ROLE_F_AND_I_MANAGER)
        resp = authenticated_client(user).get(reverse(LIST_ENDPOINT))
        self.assertEqual(resp.status_code, 200)

    def test_dealer_owner_allowed(self) -> None:
        user = make_user(username="cal-do")
        make_membership(user, self.d, ROLE_DEALER_OWNER)
        resp = authenticated_client(user).get(reverse(LIST_ENDPOINT))
        self.assertEqual(resp.status_code, 200)


class CreditApplicationListEndpointFilterValidationTests(TestCase):
    """D3 fail-explicit — invalid values return 400. `intake=false` is
    reserved-and-rejected per §5.h."""

    def setUp(self) -> None:
        self.d = get_default_dealership()
        user = make_user(username="cal-v")
        make_membership(user, self.d, ROLE_F_AND_I_MANAGER)
        self.client = authenticated_client(user)

    def test_missing_intake_returns_unfiltered(self) -> None:
        resp = self.client.get(reverse(LIST_ENDPOINT))
        self.assertEqual(resp.status_code, 200)

    def test_intake_true_applies_filter(self) -> None:
        resp = self.client.get(reverse(LIST_ENDPOINT), {"intake": "true"})
        self.assertEqual(resp.status_code, 200)

    def test_intake_false_returns_400(self) -> None:
        # `intake=false` is reserved-and-rejected per §5.h — do not
        # silently unfilter or accept as "show contracted".
        resp = self.client.get(reverse(LIST_ENDPOINT), {"intake": "false"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("intake", resp.json()["detail"].lower())

    def test_intake_capitalized_returns_400(self) -> None:
        resp = self.client.get(reverse(LIST_ENDPOINT), {"intake": "TRUE"})
        self.assertEqual(resp.status_code, 400)

    def test_intake_numeric_returns_400(self) -> None:
        resp = self.client.get(reverse(LIST_ENDPOINT), {"intake": "1"})
        self.assertEqual(resp.status_code, 400)

    def test_intake_empty_returns_400(self) -> None:
        resp = self.client.get(reverse(LIST_ENDPOINT), {"intake": ""})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_lead_id_returns_400(self) -> None:
        resp = self.client.get(reverse(LIST_ENDPOINT), {"lead_id": "abc"})
        self.assertEqual(resp.status_code, 400)

    def test_nonexistent_lead_id_returns_empty_list(self) -> None:
        resp = self.client.get(reverse(LIST_ENDPOINT), {"lead_id": "999999"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["credit_applications"], [])

    def test_invalid_since_returns_400(self) -> None:
        resp = self.client.get(reverse(LIST_ENDPOINT), {"since": "not-a-date"})
        self.assertEqual(resp.status_code, 400)


class CreditApplicationListEndpointProjectionTests(TestCase):
    def setUp(self) -> None:
        self.d = get_default_dealership()
        user = make_user(username="cal-p")
        make_membership(user, self.d, ROLE_F_AND_I_MANAGER)
        self.client = authenticated_client(user)

    def test_projection_direct_ca_has_null_writeup_context(self) -> None:
        lead = CustomerLead.objects.create(dealership=self.d, name="D")
        record_credit_application(
            dealership=self.d, applicant_full_name="A",
            source_format=CREDIT_APP_FORMAT_TABLET, lead=lead,
        )
        resp = self.client.get(reverse(LIST_ENDPOINT))
        row = resp.json()["credit_applications"][0]
        self.assertIsNone(row["writeup_context"])

    def test_projection_handoff_ca_has_full_writeup_context(self) -> None:
        writeup = _make_approved_writeup(self.d, stock="PJ", lead_name="Proj")
        _, ca = hand_off_to_fandi(writeup=writeup)
        resp = self.client.get(reverse(LIST_ENDPOINT))
        rows = resp.json()["credit_applications"]
        row = next(r for r in rows if r["id"] == ca.pk)
        ctx = row["writeup_context"]
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx["deal_writeup_id"], writeup.pk)
        self.assertEqual(ctx["lead"]["name"], "Proj")
        self.assertEqual(ctx["vehicle"]["stock_number"], "PJ")
        self.assertEqual(ctx["terms"]["vehicle_price"], "28500.00")
        self.assertEqual(ctx["terms"]["monthly_payment_target"], "450.00")
        self.assertEqual(ctx["terms"]["term_months_target"], 72)
        self.assertEqual(ctx["terms"]["apr_target"], "7.49")

    def test_returns_only_dealership_scoped(self) -> None:
        # Own CA
        lead = CustomerLead.objects.create(dealership=self.d, name="Own")
        record_credit_application(
            dealership=self.d, applicant_full_name="Own",
            source_format=CREDIT_APP_FORMAT_TABLET, lead=lead,
        )
        # Cross-tenant CA
        other = Dealership.objects.create(slug="cal-o", name="Cal O")
        cross_lead = CustomerLead.objects.create(dealership=other, name="X")
        record_credit_application(
            dealership=other, applicant_full_name="X",
            source_format=CREDIT_APP_FORMAT_TABLET, lead=cross_lead,
        )
        resp = self.client.get(reverse(LIST_ENDPOINT))
        self.assertEqual(len(resp.json()["credit_applications"]), 1)
