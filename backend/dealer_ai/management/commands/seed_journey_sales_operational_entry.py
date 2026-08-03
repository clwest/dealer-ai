"""python manage.py seed_journey_sales_operational_entry [--reset]

Milestone 24 · Increment 1 (SESSION_181) — deterministic seed delta
for the canonical Sales Operational Entry journey family (walk-in
+ phone + referral + webhook integration). Provisions the state the
M24.1-M24.4 journeys share on top of the M18 demo + M19 pilot base:

- A **sales operator persona** user (``acceptance-sales-operator``)
  with a ``sales_manager`` role at the migration-seeded default
  dealership. The role satisfies
  ``IsSalesManagerOrOwnerAtActiveDealership`` — the gate the four
  M11.1 intake endpoints share.
- An **acceptance advisor** (``Salesperson`` row + linked auth user)
  so the ``AssignmentDropdown`` inside ``LeadDetailModal`` has a
  stable target when the M24.1-M24.4 journeys assign the newly
  created lead.
- One **referring-customer lead** — a pre-existing walk-in-channel
  lead used as the picker target for the M24.3 referral journey's
  "Referring customer (existing lead)" slot. Seeded up front so
  the referral increment inherits the fixture without a seed
  extension. Idempotent via a stable ``fixture_tag`` prefix in
  the lead's notes.

Session-safe password handling per M23.2 §5.d durable fix
(``feedback_avoid_exact_count_locks_in_tests`` /
``feedback_playwright_as_operational_contract``): passwords are
only set on newly-created users. Django's session hash includes
the password hash, so an unconditional ``set_password`` on every
seed invocation would invalidate any active sessions the mid-
suite re-invocation pattern relies on.

Per M24 planning §5.e Option A: composes existing service verbs
(``record_walk_in_lead``) — no parallel write paths. Idempotent
via the fixture tag on the seeded referring-customer lead and
stable slugs/usernames.

The ``--reset`` flag deletes the seeded referring-customer lead,
clears the sales-operator's role membership, and deactivates the
seeded advisor before re-seeding. Users are preserved; the
advisor row is preserved so historical assignments still resolve
per :class:`Salesperson` doc.

Webhook payloads are ephemeral per-run and belong in each webhook
journey's ``test.beforeEach`` hook — the seed does not provision
any webhook-related fixture (per M24.1-open §5.e clarification).
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from decimal import Decimal

from dealer_ai.models import (
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    CustomerLead,
    Dealership,
    Salesperson,
    UserDealershipRole,
    Vehicle,
)
from dealer_ai.services.leads.channel_intake import record_walk_in_lead
from dealer_ai.services.tenancy import get_default_dealership

User = get_user_model()


SALES_OPERATOR_USERNAME = "acceptance-sales-operator"
SALES_OPERATOR_PASSWORD = "acceptance-sales-operator-password"

ADVISOR_USERNAME = "acceptance-sales-operator-advisor"
ADVISOR_PASSWORD = "acceptance-sales-operator-advisor-password"
ADVISOR_SLUG = "acceptance-sales-operator-advisor"
ADVISOR_NAME = "Acceptance Sales Operator Advisor"
ADVISOR_TITLE = "Test Fixture Advisor (M24)"

FIXTURE_TAG = "[M24.1-sales-operational-entry-referrer]"

_REFERRING_LEAD_SPEC = {
    "name": "Priya Prior-Customer",
    "phone": "+15551240100",
    "email": "priya-prior@example.com",
    "urgency": "researching",
}

# Milestone 25 · Increment 2 (SESSION_187) — one deterministic Vehicle
# for the M25.2 lead-to-test-drive journey's picker. Stable stock
# number lets the journey pick a known-good target without querying
# the (potentially empty) tenant inventory. Idempotent via the stock
# number's uniqueness — get_or_create is safe across suite re-runs.
M25_TEST_DRIVE_VEHICLE_STOCK = "M25-TEST-DRIVE-01"


def _existing_referring_lead(dealership: Dealership):
    return CustomerLead.objects.filter(
        dealership=dealership, notes__startswith=FIXTURE_TAG
    )


class Command(BaseCommand):
    help = (
        "Seed the sales-operator persona user + acceptance advisor + one "
        "referring-customer lead the M24.1-M24.4 Sales Operational Entry "
        "acceptance journeys share."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete the referring-customer lead, clear the sales-"
                "operator's role, and deactivate the advisor before "
                "re-seeding. Users + advisor row preserved."
            ),
        )

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            dealership = get_default_dealership()

            if options["reset"]:
                self._reset(dealership)

            sales_operator = self._provision_sales_operator(dealership)
            advisor_user, advisor = self._provision_advisor(dealership)
            referring_lead = self._provision_referring_lead(dealership)
            test_drive_vehicle = self._provision_test_drive_vehicle(dealership)

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_journey_sales_operational_entry OK — "
                f"sales_operator={sales_operator.username} "
                f"(sales_manager @ {dealership.slug}), "
                f"advisor={advisor.slug} (user={advisor_user.username}), "
                f"referring_lead_pk={referring_lead.pk}, "
                f"test_drive_vehicle=#{test_drive_vehicle.stock_number}."
            )
        )

    def _reset(self, dealership: Dealership) -> None:
        deleted_leads, _ = _existing_referring_lead(dealership).delete()
        UserDealershipRole.objects.filter(
            user__username=SALES_OPERATOR_USERNAME, dealership=dealership
        ).delete()
        # Deactivate the seeded advisor so a subsequent seed re-
        # activates it. Preserves the row (matches
        # :class:`Salesperson` retention semantics).
        Salesperson.objects.filter(slug=ADVISOR_SLUG).update(is_active=False)
        self.stdout.write(
            f"reset: deleted {deleted_leads} referring-customer lead "
            "row(s) + cleared sales-operator membership + deactivated "
            "advisor."
        )

    def _provision_sales_operator(self, dealership: Dealership):
        user, created = User.objects.get_or_create(
            username=SALES_OPERATOR_USERNAME,
            defaults={"email": f"{SALES_OPERATOR_USERNAME}@example.com"},
        )
        # Session-safe per M23.2 §5.d durable fix — only reset the
        # password on new users. Django's session hash includes the
        # password hash, so an unconditional set_password on every
        # seed invocation would invalidate any active sessions the
        # mid-suite re-invocation pattern relies on.
        if created:
            user.set_password(SALES_OPERATOR_PASSWORD)
            user.is_active = True
            user.save()
        UserDealershipRole.objects.get_or_create(
            user=user,
            dealership=dealership,
            defaults={"role": ROLE_SALES_MANAGER},
        )
        if created:
            self.stdout.write(
                f"provisioned sales-operator user {user.username}."
            )
        else:
            self.stdout.write(
                f"reused existing sales-operator user {user.username}."
            )
        return user

    def _provision_advisor(self, dealership: Dealership):
        advisor_user, user_created = User.objects.get_or_create(
            username=ADVISOR_USERNAME,
            defaults={"email": f"{ADVISOR_USERNAME}@example.com"},
        )
        if user_created:
            advisor_user.set_password(ADVISOR_PASSWORD)
            advisor_user.is_active = True
            advisor_user.save()

        UserDealershipRole.objects.get_or_create(
            user=advisor_user,
            dealership=dealership,
            defaults={"role": ROLE_ADVISOR},
        )

        advisor, advisor_created = Salesperson.objects.get_or_create(
            slug=ADVISOR_SLUG,
            defaults={
                "dealership": dealership,
                "user": advisor_user,
                "name": ADVISOR_NAME,
                "title": ADVISOR_TITLE,
                "email": f"{ADVISOR_USERNAME}@example.com",
                "is_active": True,
            },
        )
        # Reset path may have deactivated; re-activate + relink user.
        if not advisor_created:
            changed_fields: list[str] = []
            if not advisor.is_active:
                advisor.is_active = True
                changed_fields.append("is_active")
            if advisor.user_id != advisor_user.pk:
                advisor.user = advisor_user
                changed_fields.append("user")
            if changed_fields:
                advisor.save(update_fields=changed_fields)

        if user_created:
            self.stdout.write(
                f"provisioned advisor user {advisor_user.username}."
            )
        if advisor_created:
            self.stdout.write(
                f"provisioned advisor slug={advisor.slug}."
            )
        else:
            self.stdout.write(
                f"reused existing advisor slug={advisor.slug} "
                f"(active={advisor.is_active})."
            )
        return advisor_user, advisor

    def _provision_test_drive_vehicle(
        self, dealership: Dealership
    ) -> Vehicle:
        """Milestone 25 · Increment 2 (SESSION_187) — deterministic
        vehicle for the M25.2 lead-to-test-drive journey's picker.

        Idempotent via ``get_or_create`` on the stable
        ``M25_TEST_DRIVE_VEHICLE_STOCK`` stock number. The M25.2
        journey targets this row via the
        ``record-test-drive-vehicle-{id}`` testid + display-name
        substring "Bronco Wildtrak" (both stable across suite
        re-runs).
        """
        vehicle, created = Vehicle.objects.get_or_create(
            stock_number=M25_TEST_DRIVE_VEHICLE_STOCK,
            defaults={
                "dealership": dealership,
                "year": 2025,
                "make": "Ford",
                "model": "Bronco",
                "trim": "Wildtrak",
                "body_style": "suv",
                "condition": "new",
                "mileage": 12,
                "price": Decimal("58500.00"),
                "exterior_color": "Cactus Gray",
                "interior_color": "Black Onyx",
                "drivetrain": "4WD",
                "transmission": "10-Speed Automatic",
                "fuel_type": "Gasoline",
                "engine": "2.7L EcoBoost V6",
                "features": [
                    "Sasquatch Package",
                    "SYNC 4",
                    "12-inch touchscreen",
                ],
                "description": (
                    "Deterministic M25.2 acceptance fixture — "
                    "Bronco Wildtrak for the lead-to-test-drive "
                    "Playwright journey's vehicle picker."
                ),
                "is_available": True,
                "source": "acceptance-fixture",
            },
        )
        if created:
            self.stdout.write(
                f"created M25.2 test-drive fixture vehicle "
                f"#{vehicle.stock_number} ({vehicle.display_name})."
            )
        else:
            self.stdout.write(
                f"reused existing M25.2 test-drive fixture vehicle "
                f"#{vehicle.stock_number}."
            )
        return vehicle

    def _provision_referring_lead(
        self, dealership: Dealership
    ) -> CustomerLead:
        existing = _existing_referring_lead(dealership).order_by("pk").first()
        if existing is not None:
            self.stdout.write(
                f"reused existing referring-customer lead pk={existing.pk} "
                f"({existing.name})."
            )
            return existing
        lead = record_walk_in_lead(
            dealership=dealership,
            name=_REFERRING_LEAD_SPEC["name"],
            phone=_REFERRING_LEAD_SPEC["phone"],
            email=_REFERRING_LEAD_SPEC["email"],
            notes=(
                f"{FIXTURE_TAG} Referring-customer fixture for M24.3 "
                "referral picker — a prior walk-in customer who then "
                "refers a friend."
            ),
            urgency=_REFERRING_LEAD_SPEC["urgency"],
        )
        self.stdout.write(
            f"created referring-customer lead pk={lead.pk} ({lead.name})."
        )
        return lead
