"""Milestone 20 · Increment 2 — coverage for seed_journey_owner_morning_review.

Verifies:
- Fresh invocation provisions the owner user with the correct role
  membership + two overnight leads.
- Second invocation is idempotent (no duplicate user, no duplicate
  leads, no duplicate role membership).
- `--reset` clears the state and re-seeds fresh rows.
- Seeded credentials authenticate the owner user (drift between the
  seed's set_password and the persona registry surfaces here rather
  than in CI).
- Seeded leads carry the fixture tag prefix so subsequent seeds can
  detect them + are scoped to the default dealership only.
"""

from __future__ import annotations

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from dealer_ai.management.commands.seed_journey_owner_morning_review import (
    FIXTURE_TAG,
    OWNER_PASSWORD,
    OWNER_USERNAME,
)
from dealer_ai.models import (
    ROLE_DEALER_OWNER,
    CustomerLead,
    UserDealershipRole,
)
from dealer_ai.services.tenancy import get_default_dealership

User = get_user_model()


def _run_seed(*args: str) -> str:
    stdout = StringIO()
    call_command("seed_journey_owner_morning_review", *args, stdout=stdout)
    return stdout.getvalue()


class SeedOwnerMorningReviewFreshRunTests(TestCase):
    def test_provisions_owner_user_with_dealer_owner_role(self) -> None:
        _run_seed()

        owner = User.objects.get(username=OWNER_USERNAME)
        self.assertTrue(owner.is_active)

        membership = UserDealershipRole.objects.get(
            user=owner, dealership=get_default_dealership()
        )
        self.assertEqual(membership.role, ROLE_DEALER_OWNER)

    def test_provisions_two_overnight_leads(self) -> None:
        _run_seed()

        leads = CustomerLead.objects.filter(notes__startswith=FIXTURE_TAG)
        self.assertEqual(leads.count(), 2)

    def test_seeded_leads_are_unassigned(self) -> None:
        _run_seed()

        leads = CustomerLead.objects.filter(notes__startswith=FIXTURE_TAG)
        for lead in leads:
            self.assertIsNone(
                lead.assigned_to,
                f"lead pk={lead.pk} should be unassigned",
            )

    def test_seeded_leads_scoped_to_default_dealership(self) -> None:
        _run_seed()

        leads = CustomerLead.objects.filter(notes__startswith=FIXTURE_TAG)
        default = get_default_dealership()
        for lead in leads:
            self.assertEqual(lead.dealership_id, default.pk)

    def test_seeded_credentials_authenticate_owner(self) -> None:
        _run_seed()
        owner = User.objects.get(username=OWNER_USERNAME)
        self.assertTrue(owner.check_password(OWNER_PASSWORD))


class SeedOwnerMorningReviewIdempotencyTests(TestCase):
    def test_second_invocation_does_not_duplicate_user(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            User.objects.filter(username=OWNER_USERNAME).count(), 1
        )

    def test_second_invocation_does_not_duplicate_leads(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            CustomerLead.objects.filter(
                notes__startswith=FIXTURE_TAG
            ).count(),
            2,
        )

    def test_second_invocation_does_not_duplicate_membership(self) -> None:
        _run_seed()
        _run_seed()
        owner = User.objects.get(username=OWNER_USERNAME)
        self.assertEqual(
            UserDealershipRole.objects.filter(user=owner).count(), 1
        )

    def test_second_invocation_reports_reuse(self) -> None:
        _run_seed()
        output = _run_seed()
        self.assertIn("reused existing owner user", output)
        self.assertIn("reused", output)


class SeedOwnerMorningReviewResetTests(TestCase):
    def test_reset_deletes_leads_and_re_seeds_fresh_rows(self) -> None:
        _run_seed()
        first_pks = list(
            CustomerLead.objects.filter(notes__startswith=FIXTURE_TAG)
            .order_by("pk")
            .values_list("pk", flat=True)
        )

        _run_seed("--reset")

        second_pks = list(
            CustomerLead.objects.filter(notes__startswith=FIXTURE_TAG)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        self.assertEqual(len(second_pks), 2)
        # Fresh rows have new pks.
        self.assertNotEqual(set(first_pks), set(second_pks))

    def test_reset_preserves_user(self) -> None:
        _run_seed()
        _run_seed("--reset")
        self.assertTrue(
            User.objects.filter(username=OWNER_USERNAME).exists()
        )
