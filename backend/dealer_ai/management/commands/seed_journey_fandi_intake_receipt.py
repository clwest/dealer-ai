"""python manage.py seed_journey_fandi_intake_receipt [--reset]

Milestone 32 · Increment 3 (SESSION_209) — deterministic seed delta
for the F&I intake receipt journey per
``MILESTONE_32_PLANNING.md`` §5.b D11 + §5.e M32.3.

Provisions everything the M32.3 ``fandi-intake-receipt`` Playwright
describe block needs, **fully independent of any M32.2 fixture** (per
§5.c R11 independence guarantee — distinct rows, no shared state,
test order irrelevant, parallelism-safe):

- **F&I manager persona user** (``acceptance-f-and-i-manager``)
  with a ``f_and_i_manager`` role at the migration-seeded default
  dealership.
- **Intake Iris lead** — a dedicated CustomerLead with a
  deterministic name so the Playwright spec can look it up
  unambiguously.
- **FANDI-INTAKE-1 vehicle** — a dedicated Vehicle with a
  deterministic stock number.
- **Approved deal writeup** on ``Intake Iris`` + ``FANDI-INTAKE-1``
  with realistic four-square terms (vehicle_price, trade_allowance,
  down_payment, monthly_payment_target, term_months_target,
  apr_target). Approved via ``approve_deal_writeup`` under the
  seed-provisioned sales-manager user (reuses M20.2 persona).
- **Paired CreditApplication** via ``hand_off_to_fandi`` — the
  real M11.3 code path, extended at M32.1 with the D9-revised²
  ``deal_writeup`` OneToOneField backpointer. The CA appears in
  the F&I intake queue with deterministic pairing.

Per M20 planning §5.d Option B: composes existing service verbs
(``record_deal_writeup``, ``approve_deal_writeup``,
``hand_off_to_fandi``) — no parallel write paths. Idempotent via
stable fixture markers (lead name, vehicle stock number).

The ``--reset`` flag deletes the seeded writeup (which cascades
via CustomerLead.dealership=CASCADE?  no — writeup FK to lead is
CASCADE so deleting the lead cascades the writeup, but the paired
CA survives via SET_NULL on both `lead` and `deal_writeup` FKs
per M10.1 §5.e retention-clock discipline). Users + advisor +
sales_manager persona preserved; fixture rows re-seeded.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from dealer_ai.models import (
    ROLE_F_AND_I_MANAGER,
    ROLE_SALES_MANAGER,
    CreditApplication,
    CustomerLead,
    Dealership,
    DealWriteup,
    UserDealershipRole,
    Vehicle,
)
from dealer_ai.services.accounting import seed_default_coa
from dealer_ai.services.deal_writeups import (
    approve_deal_writeup,
    hand_off_to_fandi,
    record_deal_writeup,
)
from dealer_ai.services.tenancy import get_default_dealership


User = get_user_model()


FANDI_USERNAME = "acceptance-f-and-i-manager"
FANDI_PASSWORD = "acceptance-fandi-password"

# Reuse the M20.2 sales-manager persona for the writeup author +
# approver — matches operator reality (writeups are always sales-
# side; F&I side receives them). Provisioned by
# seed_journey_sales_manager_daily_startup, but we resilient-provision
# in case that seed hasn't run yet (idempotent get_or_create).
SM_USERNAME = "acceptance-sales-manager"
SM_PASSWORD = "acceptance-sm-password"

FIXTURE_LEAD_NAME = "Intake Iris"
FIXTURE_LEAD_PHONE = "+15553201501"
FIXTURE_LEAD_EMAIL = "intake-iris@example.com"

FIXTURE_VEHICLE_STOCK = "FANDI-INTAKE-1"
FIXTURE_VEHICLE_YEAR = 2024
FIXTURE_VEHICLE_MAKE = "Ford"
FIXTURE_VEHICLE_MODEL = "F-150"
FIXTURE_VEHICLE_TRIM = "XLT"
FIXTURE_VEHICLE_PRICE = Decimal("42500.00")

# Realistic four-square terms — mirrors the M32.2 sales journey shape
# but with distinct numbers so any accidental cross-fixture matching
# fails loudly.
FIXTURE_TERMS = {
    "vehicle_price": Decimal("42500.00"),
    "trade_allowance": Decimal("7500.00"),
    "down_payment": Decimal("3000.00"),
    "monthly_payment_target": Decimal("585.00"),
    "term_months_target": 60,
    "apr_target": Decimal("6.99"),
}


class Command(BaseCommand):
    help = (
        "Seed the f_and_i_manager persona user + Intake Iris lead + "
        "FANDI-INTAKE-1 vehicle + approved deal writeup + paired CA "
        "for the M32.3 fandi-intake-receipt Playwright journey. "
        "Fully independent of any M32.2 fixture."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete the Intake Iris lead (cascades the writeup) "
                "and the FANDI-INTAKE-1 vehicle before re-seeding. "
                "Users + persona role membership preserved. Paired CA "
                "survives via SET_NULL on both lead + deal_writeup FKs."
            ),
        )

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            dealership = get_default_dealership()
            seed_default_coa(dealership)

            if options["reset"]:
                self._reset(dealership)

            fandi_user = self._provision_fandi_manager(dealership)
            sm_user = self._provision_sales_manager(dealership)
            lead = self._provision_lead(dealership)
            vehicle = self._provision_vehicle(dealership)
            writeup, credit_app = self._provision_writeup_and_handoff(
                dealership, lead, vehicle, sm_user
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_journey_fandi_intake_receipt OK — "
                f"fandi_manager={fandi_user.username}, "
                f"lead={lead.pk} ({lead.name!r}), "
                f"vehicle={vehicle.pk} (stock={vehicle.stock_number!r}), "
                f"writeup={writeup.pk} (approved+handed_off), "
                f"credit_application={credit_app.pk} "
                f"(deal_writeup_fk={credit_app.deal_writeup_id})."
            )
        )

    def _reset(self, dealership: Dealership) -> None:
        # Deleting the lead cascades the writeup (CASCADE FK on
        # DealWriteup.lead per M11.3 migration 0034). The paired CA
        # survives via SET_NULL on CreditApplication.lead (M10.1 §5.a
        # Option C) + SET_NULL on CreditApplication.deal_writeup
        # (M32.1 D9-revised²) — retention-clock discipline preserved.
        writeup_pks = list(
            DealWriteup.objects.filter(
                dealership=dealership, lead__name=FIXTURE_LEAD_NAME,
            ).values_list("pk", flat=True)
        )
        deleted_leads, _ = CustomerLead.objects.filter(
            dealership=dealership, name=FIXTURE_LEAD_NAME,
        ).delete()
        deleted_vehicles, _ = Vehicle.objects.filter(
            dealership=dealership, stock_number=FIXTURE_VEHICLE_STOCK,
        ).delete()
        # Roles preserved; users preserved (acceptance suite uses
        # deterministic username lookups).
        self.stdout.write(
            f"reset: deleted {deleted_leads} lead row(s) "
            f"(cascade removed writeup pks {writeup_pks}) + "
            f"deleted {deleted_vehicles} vehicle row(s). "
            "Paired CAs preserved via SET_NULL (retention-clock)."
        )

    def _provision_fandi_manager(self, dealership: Dealership):
        user, created = User.objects.get_or_create(
            username=FANDI_USERNAME,
            defaults={"email": f"{FANDI_USERNAME}@example.com"},
        )
        user.set_password(FANDI_PASSWORD)
        user.is_active = True
        user.save()
        UserDealershipRole.objects.get_or_create(
            user=user,
            dealership=dealership,
            defaults={"role": ROLE_F_AND_I_MANAGER},
        )
        if created:
            self.stdout.write(
                f"provisioned f_and_i_manager user {user.username}."
            )
        else:
            self.stdout.write(
                f"reused existing f_and_i_manager user {user.username}."
            )
        return user

    def _provision_sales_manager(self, dealership: Dealership):
        """Idempotent sales-manager provisioning — may already exist
        from ``seed_journey_sales_manager_daily_startup`` running
        earlier in the SEED_COMMANDS array. We re-provision defensively
        so this seed is fully self-contained.
        """
        user, _ = User.objects.get_or_create(
            username=SM_USERNAME,
            defaults={"email": f"{SM_USERNAME}@example.com"},
        )
        user.set_password(SM_PASSWORD)
        user.is_active = True
        user.save()
        UserDealershipRole.objects.get_or_create(
            user=user,
            dealership=dealership,
            defaults={"role": ROLE_SALES_MANAGER},
        )
        return user

    def _provision_lead(self, dealership: Dealership) -> CustomerLead:
        lead, created = CustomerLead.objects.get_or_create(
            dealership=dealership,
            name=FIXTURE_LEAD_NAME,
            defaults={
                "phone": FIXTURE_LEAD_PHONE,
                "email": FIXTURE_LEAD_EMAIL,
            },
        )
        if created:
            self.stdout.write(f"provisioned lead pk={lead.pk}.")
        else:
            self.stdout.write(f"reused existing lead pk={lead.pk}.")
        return lead

    def _provision_vehicle(self, dealership: Dealership) -> Vehicle:
        vehicle, created = Vehicle.objects.get_or_create(
            dealership=dealership,
            stock_number=FIXTURE_VEHICLE_STOCK,
            defaults={
                "year": FIXTURE_VEHICLE_YEAR,
                "make": FIXTURE_VEHICLE_MAKE,
                "model": FIXTURE_VEHICLE_MODEL,
                "trim": FIXTURE_VEHICLE_TRIM,
                "price": FIXTURE_VEHICLE_PRICE,
            },
        )
        if created:
            self.stdout.write(f"provisioned vehicle pk={vehicle.pk}.")
        else:
            self.stdout.write(f"reused existing vehicle pk={vehicle.pk}.")
        return vehicle

    def _provision_writeup_and_handoff(
        self,
        dealership: Dealership,
        lead: CustomerLead,
        vehicle: Vehicle,
        sm_user,
    ) -> tuple[DealWriteup, CreditApplication]:
        """Idempotent writeup + hand-off provisioning.

        If an approved+handed_off writeup already exists on this
        (lead, vehicle) pair with a paired CA, reuse it. Otherwise
        create a fresh writeup, approve it, and hand it off through
        the real M11.3 code path (with M32.1 FK backpointer set).
        """
        existing_writeup = (
            DealWriteup.objects.filter(
                dealership=dealership,
                lead=lead,
                vehicle=vehicle,
                sales_manager_approved_at__isnull=False,
                handed_off_to_fandi_at__isnull=False,
            )
            .order_by("-write_up_at")
            .first()
        )
        if existing_writeup is not None:
            # Look up the paired CA via the M32.1 FK.
            existing_ca = CreditApplication.objects.filter(
                deal_writeup=existing_writeup,
            ).first()
            if existing_ca is not None:
                self.stdout.write(
                    f"reused existing writeup+handoff (writeup pk="
                    f"{existing_writeup.pk}, credit_app pk="
                    f"{existing_ca.pk})."
                )
                return existing_writeup, existing_ca
            # Writeup exists but no paired CA (e.g. reset dropped the
            # CA row). Fall through to re-create.

        writeup = record_deal_writeup(
            dealership=dealership,
            lead=lead,
            vehicle=vehicle,
            written_up_by_user=sm_user,
            vehicle_price=FIXTURE_TERMS["vehicle_price"],
            trade_allowance=FIXTURE_TERMS["trade_allowance"],
            down_payment=FIXTURE_TERMS["down_payment"],
            monthly_payment_target=FIXTURE_TERMS["monthly_payment_target"],
            term_months_target=FIXTURE_TERMS["term_months_target"],
            apr_target=FIXTURE_TERMS["apr_target"],
            notes="[M32.3 fandi-intake-receipt fixture]",
        )
        approve_deal_writeup(writeup=writeup, approved_by_user=sm_user)
        writeup, credit_app = hand_off_to_fandi(writeup=writeup)
        self.stdout.write(
            f"provisioned fresh writeup+handoff (writeup pk="
            f"{writeup.pk}, credit_app pk={credit_app.pk}, "
            f"deal_writeup_fk={credit_app.deal_writeup_id})."
        )
        return writeup, credit_app
