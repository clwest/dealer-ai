"""Milestone 20 · Increment 3 — coverage for seed_journey_recon_workflow.

Verifies:
- Fresh invocation provisions the recon-manager user with the
  correct role, a fixture Vehicle, a completed ConditionReport, and
  a ConditionFinding with no decision yet.
- Second invocation is idempotent (no duplicate rows).
- ``--reset`` clears the fixture data + role membership, and a
  subsequent seed rebuilds fresh rows.
- Seeded credentials authenticate.
- Fixture stock number + description tag are stable so the
  Playwright suite can rely on them.
"""

from __future__ import annotations

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from dealer_ai.management.commands.seed_journey_recon_workflow import (
    FIXTURE_FINDING_TAG,
    FIXTURE_STOCK,
    RECON_MGR_PASSWORD,
    RECON_MGR_USERNAME,
)
from dealer_ai.models import (
    CONDITION_REPORT_STATUS_COMPLETE,
    ROLE_RECON_MANAGER,
    ConditionFinding,
    ConditionReport,
    UserDealershipRole,
    Vehicle,
)
from dealer_ai.services.tenancy import get_default_dealership

User = get_user_model()


def _run_seed(*args: str) -> str:
    stdout = StringIO()
    call_command("seed_journey_recon_workflow", *args, stdout=stdout)
    return stdout.getvalue()


class SeedReconWorkflowFreshRunTests(TestCase):
    def test_provisions_recon_manager_user_with_role(self) -> None:
        _run_seed()

        user = User.objects.get(username=RECON_MGR_USERNAME)
        self.assertTrue(user.is_active)

        membership = UserDealershipRole.objects.get(
            user=user, dealership=get_default_dealership()
        )
        self.assertEqual(membership.role, ROLE_RECON_MANAGER)

    def test_provisions_fixture_vehicle(self) -> None:
        _run_seed()

        vehicle = Vehicle.objects.get(
            dealership=get_default_dealership(),
            stock_number=FIXTURE_STOCK,
        )
        self.assertEqual(vehicle.year, 2024)
        self.assertEqual(vehicle.model, "F-150")

    def test_provisions_completed_condition_report_for_fixture_vehicle(
        self,
    ) -> None:
        _run_seed()

        report = ConditionReport.objects.get(
            dealership=get_default_dealership(),
            vehicle__stock_number=FIXTURE_STOCK,
        )
        self.assertEqual(report.status, CONDITION_REPORT_STATUS_COMPLETE)
        self.assertIsNotNone(report.completed_at)
        self.assertEqual(report.mileage_at_inspection, 41_500)

    def test_provisions_finding_with_no_decision(self) -> None:
        _run_seed()

        finding = ConditionFinding.objects.get(
            description__startswith=FIXTURE_FINDING_TAG
        )
        self.assertFalse(hasattr(finding, "recon_decision") and finding.recon_decision)

    def test_seeded_credentials_authenticate_recon_manager(self) -> None:
        _run_seed()
        user = User.objects.get(username=RECON_MGR_USERNAME)
        self.assertTrue(user.check_password(RECON_MGR_PASSWORD))


class SeedReconWorkflowIdempotencyTests(TestCase):
    def test_second_invocation_does_not_duplicate_user(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            User.objects.filter(username=RECON_MGR_USERNAME).count(), 1
        )

    def test_second_invocation_does_not_duplicate_vehicle(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            Vehicle.objects.filter(stock_number=FIXTURE_STOCK).count(), 1
        )

    def test_second_invocation_does_not_duplicate_report(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            ConditionReport.objects.filter(
                vehicle__stock_number=FIXTURE_STOCK
            ).count(),
            1,
        )

    def test_second_invocation_does_not_duplicate_finding(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            ConditionFinding.objects.filter(
                description__startswith=FIXTURE_FINDING_TAG
            ).count(),
            1,
        )

    def test_second_invocation_does_not_duplicate_membership(self) -> None:
        _run_seed()
        _run_seed()
        user = User.objects.get(username=RECON_MGR_USERNAME)
        self.assertEqual(
            UserDealershipRole.objects.filter(user=user).count(), 1
        )


class SeedReconWorkflowResetTests(TestCase):
    def test_reset_deletes_fixture_data_and_re_seeds(self) -> None:
        _run_seed()
        first_finding_pk = ConditionFinding.objects.get(
            description__startswith=FIXTURE_FINDING_TAG
        ).pk

        _run_seed("--reset")

        findings = ConditionFinding.objects.filter(
            description__startswith=FIXTURE_FINDING_TAG
        )
        self.assertEqual(findings.count(), 1)
        self.assertNotEqual(findings.get().pk, first_finding_pk)

    def test_reset_preserves_recon_manager_user(self) -> None:
        _run_seed()
        _run_seed("--reset")
        self.assertTrue(
            User.objects.filter(username=RECON_MGR_USERNAME).exists()
        )

    def test_reset_re_provisions_role_membership(self) -> None:
        _run_seed()
        _run_seed("--reset")
        user = User.objects.get(username=RECON_MGR_USERNAME)
        self.assertEqual(
            UserDealershipRole.objects.filter(user=user).count(), 1
        )
