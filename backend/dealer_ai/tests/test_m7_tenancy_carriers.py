"""Milestone 7 · Increment 1 (SESSION_088) — tenancy-carrier extension tests.

Verifies that ``services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`` was
extended from 19 → 20 entries and that the ``pre_save`` autofill signal
wires cleanly for the new carrier (``JobRunLog``).

Mirrors the M6.1 shape in ``test_m6_tenancy_carriers.py`` — same three-
part structure (count locked, new carrier present, prior carriers
preserved) + one wired-autofill smoke test.
"""

from __future__ import annotations

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    Dealership,
    JOB_RUN_STATUS_STARTED,
    JobRunLog,
)
from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES


class TenancyCarriersExtended(TestCase):
    """The M7.1 extension adds ``JobRunLog`` to the 19-entry M6.1 tuple,
    yielding at least 20.

    Count is asserted with ``>=`` (not ``==``) so future milestones can
    add carriers without breaking the M7.1 milestone-shape assertion.
    The exact-count invariant is owned by each milestone's own carrier-
    count test at its shipping time (e.g.
    ``test_carrier_count_is_twenty_one`` in
    ``test_m7_stage_aging_model.py``). Pattern mirrors the
    SESSION_088 relaxation of the M6.1 count assertion.
    """

    def test_carrier_count_at_least_twenty(self):
        self.assertGreaterEqual(
            len(_TENANT_CARRIER_MODEL_NAMES),
            20,
            "Milestone 7 · Increment 1 extended the tenancy-carrier "
            "tuple from 19 → 20 (added JobRunLog). Later milestones "
            "may extend further; this assertion is the floor.",
        )

    def test_job_run_log_present(self):
        self.assertIn("JobRunLog", _TENANT_CARRIER_MODEL_NAMES)

    def test_prior_carriers_preserved(self):
        """Every M1-M6 carrier must remain — additive extension only."""
        expected_prior = {
            # M1
            "Vehicle",
            "Salesperson",
            "ChatSession",
            "ChatMessage",
            "CustomerLead",
            "DealerOnboardingProfile",
            # M3
            "ConditionReport",
            "ConditionFinding",
            "ConditionFindingPhoto",
            # M4
            "Vendor",
            "ReconDecision",
            "WorkOrder",
            "WorkOrderFinding",
            "WorkOrderPart",
            "VendorCommunication",
            # M5
            "VehicleStage",
            "VehicleStageEvent",
            # M6
            "VehiclePhoto",
            "VehicleListing",
        }
        actual = set(_TENANT_CARRIER_MODEL_NAMES)
        missing = expected_prior - actual
        self.assertEqual(
            missing,
            set(),
            f"M1-M6 tenancy carriers must be preserved; missing: {missing}",
        )


class TenancyAutofillWiredForJobRunLog(TestCase):
    """The ``pre_save`` autofill signal registered by
    :func:`register_default_dealership_autofill` covers ``JobRunLog``.

    Smoke test: a row saved without ``dealership=`` gets the default
    attached automatically. This is the fallback path — the
    :func:`@instrumented_task` decorator overrides by passing
    ``dealership_id`` explicitly when the task receives one, per
    ``services.tenancy._auto_attach_default_dealership`` resolution rule
    1 (explicit tenant wins).
    """

    def test_job_run_log_pre_save_autofills_default_dealership(self):
        default = Dealership.objects.get(slug="default")
        # Deliberately omit dealership= — the autofill safety net should
        # attach the default before save() persists the row.
        row = JobRunLog(
            task_name="tests.m7.autofill",
            status=JOB_RUN_STATUS_STARTED,
            started_at=timezone.now(),
        )
        row.save()
        row.refresh_from_db()
        self.assertEqual(row.dealership_id, default.pk)

    def test_job_run_log_explicit_dealership_wins_over_autofill(self):
        default = Dealership.objects.get(slug="default")
        other = Dealership.objects.create(name="Alt", slug="alt-tenant")
        # Explicit dealership= should NOT be overridden by the autofill.
        row = JobRunLog(
            task_name="tests.m7.explicit",
            status=JOB_RUN_STATUS_STARTED,
            started_at=timezone.now(),
            dealership=other,
        )
        row.save()
        row.refresh_from_db()
        self.assertEqual(row.dealership_id, other.pk)
        self.assertNotEqual(row.dealership_id, default.pk)
