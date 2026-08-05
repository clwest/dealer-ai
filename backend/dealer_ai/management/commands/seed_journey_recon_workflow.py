"""python manage.py seed_journey_recon_workflow [--reset]

Milestone 20 · Increment 3 — deterministic seed delta for the
canonical recon workflow journey. Provisions the state the recon
journey needs on top of the M18 demo + M19 pilot base:

- A **recon manager persona** user (``acceptance-recon-manager``)
  with a ``recon_manager`` role at the migration-seeded default
  dealership so the persona can reach
  ``/dealer-ai-inventory/<stock>/recon`` and record decisions.
- A **fixture vehicle** with stable stock number
  ``M20-RECON-ACCEPT`` on the default dealership so the journey has
  a deterministic recon URL to navigate to.
- A **completed ConditionReport** for the fixture vehicle with one
  ConditionFinding that starts with **no decision** — the journey
  clicks a tier button to record the first decision.

Per M20 planning §5.d Option B: creates state directly via ORM in
this seed (matches the pattern in
``tests/test_admin_recon_endpoints.py`` fixtures). ConditionReport +
ConditionFinding do not have public write-verb service functions
outside the demo-store archetypes; direct object creation is the
established test pattern.

Idempotent via stable stock number + fixture tag in the finding
description. The ``--reset`` flag deletes the seeded finding +
report + vehicle + clears the recon-manager's membership then
re-seeds. The user is preserved.

## Rerun invariants (M34.1 · D3)

On every invocation (without ``--reset``), the seed restores the
following pre-flight invariant that the M20.3 recon/workflow
journey depends on:

- **The seeded ConditionFinding has no ``recon_decision``.** The
  journey's step 4 clicks "Must do" which creates a ReconDecision
  via the M4.2 service verb; this reset deletes the child row
  before the next run so the line-58 pre-flight assertion holds.

Scoped by the fixture-tag AND dealership filter for defense-in-
depth against tag collisions across tenants. Direct
``ReconDecision.objects.filter(...).delete()`` does not cascade
upward to ConditionFinding (OneToOne with CASCADE on the child
side, not the parent), verified at M34.0 §4.5.

Rerun-safety per M34.0 §5.b D1 + D3. No product-code changes.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_REQUIRED,
    ROLE_RECON_MANAGER,
    ConditionFinding,
    ConditionReport,
    Dealership,
    ReconDecision,
    UserDealershipRole,
    Vehicle,
)
from dealer_ai.services.accounting import seed_default_coa
from dealer_ai.services.tenancy import get_default_dealership

User = get_user_model()


RECON_MGR_USERNAME = "acceptance-recon-manager"
RECON_MGR_PASSWORD = "acceptance-recon-password"

FIXTURE_STOCK = "M20-RECON-ACCEPT"
FIXTURE_FINDING_TAG = "[M20.3-recon-workflow]"


def _existing_finding(dealership: Dealership):
    return ConditionFinding.objects.filter(
        dealership=dealership,
        description__startswith=FIXTURE_FINDING_TAG,
    ).order_by("pk").first()


def _existing_vehicle(dealership: Dealership):
    return Vehicle.objects.filter(
        dealership=dealership, stock_number=FIXTURE_STOCK
    ).first()


class Command(BaseCommand):
    help = (
        "Seed the recon-manager persona + a fixture vehicle + a completed "
        "ConditionReport with one undecided finding — state the M20.3 "
        "canonical recon workflow journey exercises."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete the seeded finding + report + vehicle and clear "
                "the recon-manager's role membership before re-seeding. "
                "User is preserved."
            ),
        )

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            dealership = get_default_dealership()
            seed_default_coa(dealership)

            if options["reset"]:
                self._reset(dealership)

            recon_mgr = self._provision_recon_manager(dealership)
            vehicle = self._provision_vehicle(dealership)
            self._restore_rerun_invariants(dealership)
            report, finding = self._provision_report_and_finding(
                vehicle, dealership
            )

        existing_decision = getattr(finding, "recon_decision", None)
        decision_label = (
            f"tier={existing_decision.tier}"
            if existing_decision is not None
            else "no decision yet"
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_journey_recon_workflow OK — "
                f"recon_manager={recon_mgr.username} "
                f"(recon_manager @ {dealership.slug}), "
                f"vehicle={vehicle.stock_number}, "
                f"report={report.pk}, finding={finding.pk} "
                f"({decision_label})."
            )
        )

    def _restore_rerun_invariants(self, dealership: Dealership) -> None:
        """[M34.1 · D3] Restore pre-flight invariants the M20.3
        recon/workflow journey depends on, so the seed is rerun-safe
        against mutated state.

        See ``## Rerun invariants`` in the module docstring for the
        contract. Tag-scoped AND dealership-scoped for defense-in-depth
        against tag collisions across tenants. OneToOne relation
        `ReconDecision.finding` cascades child → nothing on parent, so
        this is safe.
        """
        ReconDecision.objects.filter(
            finding__description__startswith=FIXTURE_FINDING_TAG,
            dealership=dealership,
        ).delete()

    def _reset(self, dealership: Dealership) -> None:
        # Delete the finding first (child), then the report, then the
        # vehicle. Cascades handle any ReconDecision rows attached to
        # the finding.
        deleted_findings, _ = ConditionFinding.objects.filter(
            dealership=dealership,
            description__startswith=FIXTURE_FINDING_TAG,
        ).delete()
        deleted_reports, _ = ConditionReport.objects.filter(
            dealership=dealership,
            vehicle__stock_number=FIXTURE_STOCK,
        ).delete()
        deleted_vehicles, _ = Vehicle.objects.filter(
            dealership=dealership, stock_number=FIXTURE_STOCK
        ).delete()
        UserDealershipRole.objects.filter(
            user__username=RECON_MGR_USERNAME, dealership=dealership
        ).delete()
        self.stdout.write(
            f"reset: deleted findings={deleted_findings} "
            f"reports={deleted_reports} vehicles={deleted_vehicles} + "
            "cleared recon-manager membership."
        )

    def _provision_recon_manager(self, dealership: Dealership):
        user, created = User.objects.get_or_create(
            username=RECON_MGR_USERNAME,
            defaults={"email": f"{RECON_MGR_USERNAME}@example.com"},
        )
        user.set_password(RECON_MGR_PASSWORD)
        user.is_active = True
        user.save()
        UserDealershipRole.objects.get_or_create(
            user=user,
            dealership=dealership,
            defaults={"role": ROLE_RECON_MANAGER},
        )
        if created:
            self.stdout.write(
                f"provisioned recon-manager user {user.username}."
            )
        else:
            self.stdout.write(
                f"reused existing recon-manager user {user.username}."
            )
        return user

    def _provision_vehicle(self, dealership: Dealership) -> Vehicle:
        existing = _existing_vehicle(dealership)
        if existing is not None:
            self.stdout.write(
                f"reused existing vehicle {existing.stock_number}."
            )
            return existing
        vehicle = Vehicle.objects.create(
            dealership=dealership,
            stock_number=FIXTURE_STOCK,
            year=2024,
            model="F-150",
            price=Decimal("42500.00"),
        )
        self.stdout.write(f"created vehicle {vehicle.stock_number}.")
        return vehicle

    def _provision_report_and_finding(
        self, vehicle: Vehicle, dealership: Dealership
    ) -> tuple[ConditionReport, ConditionFinding]:
        existing_finding = _existing_finding(dealership)
        if existing_finding is not None:
            self.stdout.write(
                f"reused existing finding pk={existing_finding.pk}."
            )
            return existing_finding.report, existing_finding

        now = timezone.now()
        report = ConditionReport.objects.create(
            vehicle=vehicle,
            dealership=dealership,
            inspector_name="Acceptance Inspector",
            inspected_at=now,
            mileage_at_inspection=41_500,
            status=CONDITION_REPORT_STATUS_COMPLETE,
            completed_at=now,
        )
        finding = ConditionFinding.objects.create(
            report=report,
            dealership=dealership,
            category=CONDITION_CATEGORY_MECHANICAL,
            severity=CONDITION_SEVERITY_REQUIRED,
            description=(
                f"{FIXTURE_FINDING_TAG} Fixture finding for M20.3 "
                "canonical recon workflow acceptance journey — brake "
                "pads worn below 3mm."
            ),
        )
        self.stdout.write(
            f"created report pk={report.pk} + finding pk={finding.pk}."
        )
        return report, finding
