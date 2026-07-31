"""Milestone 1 · Increment 4A — User↔Dealership membership + role.

Schema-only increment. These tests lock the model contract that
Increments 4B (request-context tenancy resolver), 4C (advisor workspace
auth), and 4D (admin endpoint gating) will consult. Endpoint behavior
is intentionally unchanged by 4A — there are no view tests here.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from dealer_ai.models import (
    ROLE_ADVISOR,
    ROLE_CHOICES,
    ROLE_COLLECTIONS,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_PORTER,
    ROLE_RECON_MANAGER,
    ROLE_SALES_MANAGER,
    Dealership,
    Salesperson,
    UserDealershipRole,
)

User = get_user_model()


class RoleVocabulary(TestCase):
    """Locks the seven canonical roles from
    ``docs/roadmap/IMPLEMENTATION_ROADMAP.md`` §Milestone 1. If a
    downstream milestone wants an eighth role it must update the
    roadmap first — this test forces that conversation.
    """

    def test_role_choices_contain_exactly_seven_canonical_values(self):
        role_values = {value for value, _ in ROLE_CHOICES}
        self.assertEqual(
            role_values,
            {
                ROLE_DEALER_OWNER,
                ROLE_SALES_MANAGER,
                ROLE_RECON_MANAGER,
                ROLE_F_AND_I_MANAGER,
                ROLE_COLLECTIONS,
                ROLE_ADVISOR,
                ROLE_PORTER,
            },
        )
        self.assertEqual(len(ROLE_CHOICES), 7)


class UserDealershipRoleModel(TestCase):
    def setUp(self):
        self.dealership = Dealership.objects.create(
            name="Copper Canyon Auto", slug="copper-canyon-tests"
        )
        self.user = User.objects.create_user(
            username="owner1", email="owner1@example.com", password="x"
        )

    def test_round_trip_create_and_fetch(self):
        membership = UserDealershipRole.objects.create(
            user=self.user, dealership=self.dealership, role=ROLE_DEALER_OWNER
        )
        fetched = UserDealershipRole.objects.get(pk=membership.pk)
        self.assertEqual(fetched.user, self.user)
        self.assertEqual(fetched.dealership, self.dealership)
        self.assertEqual(fetched.role, ROLE_DEALER_OWNER)
        self.assertIsNotNone(fetched.created_at)
        self.assertIsNotNone(fetched.updated_at)

    def test_unique_together_prevents_duplicate_membership(self):
        UserDealershipRole.objects.create(
            user=self.user, dealership=self.dealership, role=ROLE_ADVISOR
        )
        with self.assertRaises(IntegrityError):
            UserDealershipRole.objects.create(
                user=self.user, dealership=self.dealership, role=ROLE_ADVISOR
            )

    def test_same_user_can_hold_multiple_roles_at_same_dealership(self):
        # Realistic in an indie shop: owner also acts as sales_manager.
        UserDealershipRole.objects.create(
            user=self.user, dealership=self.dealership, role=ROLE_DEALER_OWNER
        )
        UserDealershipRole.objects.create(
            user=self.user, dealership=self.dealership, role=ROLE_SALES_MANAGER
        )
        roles = set(
            UserDealershipRole.objects.filter(
                user=self.user, dealership=self.dealership
            ).values_list("role", flat=True)
        )
        self.assertEqual(roles, {ROLE_DEALER_OWNER, ROLE_SALES_MANAGER})

    def test_same_user_can_belong_to_multiple_dealerships(self):
        other = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-tests"
        )
        UserDealershipRole.objects.create(
            user=self.user, dealership=self.dealership, role=ROLE_DEALER_OWNER
        )
        UserDealershipRole.objects.create(
            user=self.user, dealership=other, role=ROLE_ADVISOR
        )
        memberships = self.user.memberships.all()
        self.assertEqual(memberships.count(), 2)
        by_dealership = {m.dealership_id: m.role for m in memberships}
        self.assertEqual(by_dealership[self.dealership.pk], ROLE_DEALER_OWNER)
        self.assertEqual(by_dealership[other.pk], ROLE_ADVISOR)

    def test_reverse_accessor_from_user(self):
        UserDealershipRole.objects.create(
            user=self.user, dealership=self.dealership, role=ROLE_ADVISOR
        )
        self.assertEqual(self.user.memberships.count(), 1)
        self.assertEqual(self.user.memberships.first().role, ROLE_ADVISOR)

    def test_reverse_accessor_from_dealership(self):
        UserDealershipRole.objects.create(
            user=self.user, dealership=self.dealership, role=ROLE_ADVISOR
        )
        self.assertEqual(self.dealership.memberships.count(), 1)
        self.assertEqual(self.dealership.memberships.first().user, self.user)


class SalespersonUserLink(TestCase):
    def setUp(self):
        self.dealership = Dealership.objects.create(
            name="Copper Canyon Auto", slug="copper-canyon-sp-tests"
        )
        self.user = User.objects.create_user(
            username="advisor1", email="advisor1@example.com", password="x"
        )

    def test_user_link_is_optional_for_backfill_window(self):
        # Increment 4A ships the link nullable so existing Salesperson
        # rows continue to load. Increment 4C is the increment that
        # requires the link to be present for authenticated advisor
        # workspace access.
        sp = Salesperson.objects.create(
            dealership=self.dealership,
            name="Jane Advisor",
            slug="jane-advisor",
        )
        self.assertIsNone(sp.user)

    def test_user_link_reverse_accessor(self):
        sp = Salesperson.objects.create(
            dealership=self.dealership,
            name="Jane Advisor",
            slug="jane-advisor-r",
            user=self.user,
        )
        self.assertEqual(self.user.salesperson, sp)

    def test_user_link_is_one_to_one(self):
        Salesperson.objects.create(
            dealership=self.dealership,
            name="Jane Advisor",
            slug="jane-advisor-o1",
            user=self.user,
        )
        with self.assertRaises(IntegrityError):
            Salesperson.objects.create(
                dealership=self.dealership,
                name="Second Row",
                slug="second-row",
                user=self.user,
            )

    def test_user_delete_nulls_link_preserving_salesperson(self):
        # SET_NULL preserves historical lead attribution when a user
        # account is removed — same rationale as `is_active=False`
        # retention on Salesperson.
        sp = Salesperson.objects.create(
            dealership=self.dealership,
            name="Jane Advisor",
            slug="jane-advisor-sn",
            user=self.user,
        )
        self.user.delete()
        sp.refresh_from_db()
        self.assertIsNone(sp.user)
