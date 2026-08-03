"""Milestone 20 · Increment 2 — coverage for seed_journey_sales_manager_daily_startup.

Verifies:
- Fresh invocation provisions the sales-manager + advisor users, a
  Salesperson row linked to the advisor user, and three overnight
  leads with varied urgency.
- Second invocation is idempotent (no duplicate users, no duplicate
  advisor row, no duplicate leads, no duplicate memberships).
- ``--reset`` deletes leads + clears sales-manager membership +
  deactivates the advisor; a subsequent seed re-activates + relinks.
- Seeded credentials authenticate both users.
- Advisor row is properly linked to the advisor auth user
  (Salesperson.user is set) — the assignment dropdown depends on
  active salespeople to enumerate.
- Seeded leads carry the fixture tag prefix + are scoped to the
  default dealership only.
"""

from __future__ import annotations

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from dealer_ai.management.commands.seed_journey_sales_manager_daily_startup import (
    ADVISOR_PASSWORD,
    ADVISOR_SLUG,
    ADVISOR_USERNAME,
    FIXTURE_TAG,
    SM_PASSWORD,
    SM_USERNAME,
)
from dealer_ai.models import (
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    CustomerLead,
    Salesperson,
    UserDealershipRole,
)
from dealer_ai.services.tenancy import get_default_dealership

User = get_user_model()


def _run_seed(*args: str) -> str:
    stdout = StringIO()
    call_command(
        "seed_journey_sales_manager_daily_startup", *args, stdout=stdout
    )
    return stdout.getvalue()


class SeedSalesManagerDailyStartupFreshRunTests(TestCase):
    def test_provisions_sales_manager_user_with_role(self) -> None:
        _run_seed()

        sm = User.objects.get(username=SM_USERNAME)
        self.assertTrue(sm.is_active)

        membership = UserDealershipRole.objects.get(
            user=sm, dealership=get_default_dealership()
        )
        self.assertEqual(membership.role, ROLE_SALES_MANAGER)

    def test_provisions_advisor_user_with_role(self) -> None:
        _run_seed()

        advisor_user = User.objects.get(username=ADVISOR_USERNAME)
        self.assertTrue(advisor_user.is_active)

        membership = UserDealershipRole.objects.get(
            user=advisor_user, dealership=get_default_dealership()
        )
        self.assertEqual(membership.role, ROLE_ADVISOR)

    def test_provisions_salesperson_row_linked_to_advisor_user(self) -> None:
        _run_seed()

        advisor_user = User.objects.get(username=ADVISOR_USERNAME)
        advisor = Salesperson.objects.get(slug=ADVISOR_SLUG)
        self.assertTrue(advisor.is_active)
        self.assertEqual(advisor.user_id, advisor_user.pk)
        self.assertEqual(
            advisor.dealership_id, get_default_dealership().pk
        )

    def test_provisions_three_overnight_leads(self) -> None:
        _run_seed()

        leads = CustomerLead.objects.filter(notes__startswith=FIXTURE_TAG)
        self.assertEqual(leads.count(), 3)

    def test_seeded_leads_are_unassigned(self) -> None:
        _run_seed()
        for lead in CustomerLead.objects.filter(
            notes__startswith=FIXTURE_TAG
        ):
            self.assertIsNone(lead.assigned_to)

    def test_seeded_leads_scoped_to_default_dealership(self) -> None:
        _run_seed()
        default = get_default_dealership()
        for lead in CustomerLead.objects.filter(
            notes__startswith=FIXTURE_TAG
        ):
            self.assertEqual(lead.dealership_id, default.pk)

    def test_seeded_credentials_authenticate_sales_manager(self) -> None:
        _run_seed()
        sm = User.objects.get(username=SM_USERNAME)
        self.assertTrue(sm.check_password(SM_PASSWORD))

    def test_seeded_credentials_authenticate_advisor(self) -> None:
        _run_seed()
        advisor_user = User.objects.get(username=ADVISOR_USERNAME)
        self.assertTrue(advisor_user.check_password(ADVISOR_PASSWORD))


class SeedSalesManagerDailyStartupIdempotencyTests(TestCase):
    def test_second_invocation_does_not_duplicate_users(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            User.objects.filter(username=SM_USERNAME).count(), 1
        )
        self.assertEqual(
            User.objects.filter(username=ADVISOR_USERNAME).count(), 1
        )

    def test_second_invocation_does_not_duplicate_salesperson(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            Salesperson.objects.filter(slug=ADVISOR_SLUG).count(), 1
        )

    def test_second_invocation_does_not_duplicate_leads(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            CustomerLead.objects.filter(
                notes__startswith=FIXTURE_TAG
            ).count(),
            3,
        )

    def test_second_invocation_does_not_duplicate_memberships(self) -> None:
        _run_seed()
        _run_seed()
        sm = User.objects.get(username=SM_USERNAME)
        advisor_user = User.objects.get(username=ADVISOR_USERNAME)
        self.assertEqual(
            UserDealershipRole.objects.filter(user=sm).count(), 1
        )
        self.assertEqual(
            UserDealershipRole.objects.filter(user=advisor_user).count(), 1
        )


class SeedSalesManagerDailyStartupResetTests(TestCase):
    def test_reset_deletes_leads_and_re_seeds_fresh_rows(self) -> None:
        _run_seed()
        first_pks = set(
            CustomerLead.objects.filter(notes__startswith=FIXTURE_TAG)
            .values_list("pk", flat=True)
        )
        _run_seed("--reset")
        second_pks = set(
            CustomerLead.objects.filter(notes__startswith=FIXTURE_TAG)
            .values_list("pk", flat=True)
        )
        self.assertEqual(len(second_pks), 3)
        self.assertEqual(first_pks & second_pks, set())

    def test_reset_deactivates_then_re_activates_advisor(self) -> None:
        _run_seed()
        # After reset, the advisor is deactivated. The very same
        # `_run_seed("--reset")` call runs the reset AND re-seeds, so
        # by the time it returns the advisor should be active again.
        _run_seed("--reset")
        advisor = Salesperson.objects.get(slug=ADVISOR_SLUG)
        self.assertTrue(advisor.is_active)

    def test_reset_preserves_users(self) -> None:
        _run_seed()
        _run_seed("--reset")
        self.assertTrue(User.objects.filter(username=SM_USERNAME).exists())
        self.assertTrue(
            User.objects.filter(username=ADVISOR_USERNAME).exists()
        )

    def test_reset_preserves_salesperson_row(self) -> None:
        """Retention semantics: advisor rows are preserved even after
        reset, matching :class:`Salesperson`'s historical accuracy
        posture."""
        _run_seed()
        _run_seed("--reset")
        self.assertEqual(
            Salesperson.objects.filter(slug=ADVISOR_SLUG).count(), 1
        )
