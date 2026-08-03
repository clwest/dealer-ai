"""Milestone 20 · Increment 1 — coverage for the seed_journey_pilot_onboarding management command.

Verifies:

- Fresh invocation provisions the operator user + pilot owner user +
  qualified PilotProspect.
- Second invocation is idempotent (no duplicate users, no duplicate
  prospect rows, no duplicate role memberships).
- Operator user gets a ``sales_manager`` role at the default
  dealership so the persona can reach ``/dealer-ai-admin``.
- Prospect lands in ``qualified`` state so the M19.3 conversion
  endpoint can transition it to ``converted`` when the journey
  creates the pilot.
- ``--reset`` deletes the seeded prospect + clears the seeded users'
  memberships, and the next invocation restores clean state.
- Command output is stable and machine-parseable for CI log
  inspection.

Per M20 planning §5.d Option B — this command composes existing
service verbs (``create_prospect`` + ``advance_prospect_state``); the
test asserts against post-conditions on those verbs, not against
parallel write logic.
"""

from __future__ import annotations

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from dealer_ai.management.commands.seed_journey_pilot_onboarding import (
    OPERATOR_USERNAME,
    PILOT_OWNER_USERNAME,
    PROSPECT_CONTACT_EMAIL,
)
from dealer_ai.models import (
    PILOT_PROSPECT_STATE_DECLINED,
    PILOT_PROSPECT_STATE_QUALIFIED,
    ROLE_SALES_MANAGER,
    PilotProspect,
    UserDealershipRole,
)
from dealer_ai.services.tenancy import get_default_dealership

User = get_user_model()


def _run_seed(*args: str) -> str:
    """Invoke the seed command, return captured stdout."""
    stdout = StringIO()
    call_command("seed_journey_pilot_onboarding", *args, stdout=stdout)
    return stdout.getvalue()


class SeedJourneyPilotOnboardingFreshRunTests(TestCase):
    def test_provisions_operator_user_with_sales_manager_role(self) -> None:
        _run_seed()

        operator = User.objects.get(username=OPERATOR_USERNAME)
        self.assertTrue(operator.is_active)
        self.assertTrue(operator.is_staff)

        default = get_default_dealership()
        membership = UserDealershipRole.objects.get(
            user=operator, dealership=default
        )
        self.assertEqual(membership.role, ROLE_SALES_MANAGER)

    def test_provisions_pilot_owner_user(self) -> None:
        _run_seed()
        owner = User.objects.get(username=PILOT_OWNER_USERNAME)
        self.assertTrue(owner.is_active)

    def test_provisions_qualified_prospect(self) -> None:
        _run_seed()

        prospects = PilotProspect.objects.filter(
            contact_email=PROSPECT_CONTACT_EMAIL
        )
        self.assertEqual(prospects.count(), 1)
        prospect = prospects.get()
        self.assertEqual(
            prospect.eligibility_state, PILOT_PROSPECT_STATE_QUALIFIED
        )
        self.assertEqual(prospect.dealer_business_name, "Acceptance Motors")

    def test_seed_credentials_authenticate_operator(self) -> None:
        _run_seed()
        operator = User.objects.get(username=OPERATOR_USERNAME)
        # The Playwright login step will POST these credentials to
        # /api/dealer-ai/auth/login/. Verify Django accepts them via
        # check_password so a drift between the seed's set_password
        # and the persona registry surfaces here rather than in CI.
        self.assertTrue(operator.check_password("acceptance-op-password"))

    def test_seed_credentials_authenticate_pilot_owner(self) -> None:
        _run_seed()
        owner = User.objects.get(username=PILOT_OWNER_USERNAME)
        self.assertTrue(owner.check_password("acceptance-owner-password"))


class SeedJourneyPilotOnboardingIdempotencyTests(TestCase):
    def test_second_invocation_does_not_duplicate_users(self) -> None:
        _run_seed()
        _run_seed()

        self.assertEqual(
            User.objects.filter(username=OPERATOR_USERNAME).count(), 1
        )
        self.assertEqual(
            User.objects.filter(username=PILOT_OWNER_USERNAME).count(), 1
        )

    def test_second_invocation_does_not_duplicate_prospect(self) -> None:
        _run_seed()
        _run_seed()

        self.assertEqual(
            PilotProspect.objects.filter(
                contact_email=PROSPECT_CONTACT_EMAIL
            ).count(),
            1,
        )

    def test_second_invocation_does_not_duplicate_role_membership(self) -> None:
        _run_seed()
        _run_seed()

        default = get_default_dealership()
        operator = User.objects.get(username=OPERATOR_USERNAME)
        memberships = UserDealershipRole.objects.filter(
            user=operator, dealership=default
        )
        self.assertEqual(memberships.count(), 1)

    def test_second_invocation_reports_reuse(self) -> None:
        _run_seed()
        output = _run_seed()
        self.assertIn("reused existing operator user", output)
        self.assertIn("reused existing pilot owner user", output)
        self.assertIn("reused existing qualified prospect", output)


class SeedJourneyPilotOnboardingResetTests(TestCase):
    def test_reset_deletes_prospect_then_re_seeds(self) -> None:
        _run_seed()
        first_prospect_pk = PilotProspect.objects.get(
            contact_email=PROSPECT_CONTACT_EMAIL
        ).pk

        _run_seed("--reset")

        # A fresh row (new pk) is created after reset.
        prospects = PilotProspect.objects.filter(
            contact_email=PROSPECT_CONTACT_EMAIL
        )
        self.assertEqual(prospects.count(), 1)
        self.assertNotEqual(prospects.get().pk, first_prospect_pk)

    def test_reset_clears_and_re_provisions_memberships(self) -> None:
        _run_seed()
        _run_seed("--reset")

        default = get_default_dealership()
        operator = User.objects.get(username=OPERATOR_USERNAME)
        memberships = UserDealershipRole.objects.filter(
            user=operator, dealership=default
        )
        self.assertEqual(memberships.count(), 1)
        self.assertEqual(memberships.get().role, ROLE_SALES_MANAGER)

    def test_reset_preserves_users(self) -> None:
        _run_seed()
        _run_seed("--reset")
        self.assertTrue(
            User.objects.filter(username=OPERATOR_USERNAME).exists()
        )
        self.assertTrue(
            User.objects.filter(username=PILOT_OWNER_USERNAME).exists()
        )


class SeedJourneyPilotOnboardingTenantScopeTests(TestCase):
    def test_prospect_has_no_dealership_fk(self) -> None:
        """PilotProspect is a pre-tenant operator record per M19 §5.b."""
        _run_seed()
        prospect = PilotProspect.objects.get(
            contact_email=PROSPECT_CONTACT_EMAIL
        )
        # PilotProspect.source_demo_dealership is optional; the seed
        # does not populate it, which matches the M20.1 fixture
        # (no source demo required for the acceptance journey).
        self.assertIsNone(prospect.source_demo_dealership)

    def test_operator_role_scoped_to_default_dealership_only(self) -> None:
        _run_seed()
        operator = User.objects.get(username=OPERATOR_USERNAME)
        memberships = UserDealershipRole.objects.filter(user=operator)
        self.assertEqual(memberships.count(), 1)
        self.assertEqual(
            memberships.get().dealership_id, get_default_dealership().pk
        )


class SeedJourneyPilotOnboardingTerminalRecoveryTests(TestCase):
    def test_terminal_prospect_leads_to_fresh_row(self) -> None:
        """A prior prospect with terminal state (declined/converted)
        should not block re-seeding — the seed logs the mismatch and
        creates a fresh qualified row per the M19 §5.b design."""
        _run_seed()
        prospect = PilotProspect.objects.get(
            contact_email=PROSPECT_CONTACT_EMAIL
        )
        # Force to declined (terminal state) so the next seed cannot
        # advance it.
        prospect.eligibility_state = PILOT_PROSPECT_STATE_DECLINED
        prospect.save(update_fields=["eligibility_state"])

        output = _run_seed()

        self.assertIn("terminal", output)
        # The old prospect is preserved, a new one is added.
        prospects = PilotProspect.objects.filter(
            contact_email=PROSPECT_CONTACT_EMAIL
        )
        self.assertEqual(prospects.count(), 2)
        qualified = prospects.filter(
            eligibility_state=PILOT_PROSPECT_STATE_QUALIFIED
        )
        self.assertEqual(qualified.count(), 1)
