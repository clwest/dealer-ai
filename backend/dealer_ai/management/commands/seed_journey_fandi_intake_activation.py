"""python manage.py seed_journey_fandi_intake_activation [--reset]

Milestone 33 · Increment 2 (SESSION_212) — deterministic seed delta
for the F&I intake activation journey per
``MILESTONE_33_PLANNING.md`` §5.b D8 + §5.e M33.2.

Provisions everything the M33.2 ``fandi-intake-activation``
Playwright describe block needs, **fully independent of any M32.2
`Sales Sam` or M32.3 `Intake Iris` fixture** (per M33.0 §5.c R7
independence guarantee — distinct rows, no shared state, test order
irrelevant, parallelism-safe):

- **F&I manager persona user** — reuses the shipped M32.3
  ``acceptance-f-and-i-manager`` user + role (idempotent
  get_or_create; no duplicate persona provisioning).
- **Sales-manager provisioning user** — reuses shipped M20.2
  ``acceptance-sales-manager`` (idempotent).
- **Structure Sam lead** — dedicated CustomerLead with a
  deterministic name distinct from ``Intake Iris`` (M32.3) and
  ``Sales Sam`` (M32.2) so the Playwright spec looks it up
  unambiguously.
- **FANDI-STRUCT-1 vehicle** — dedicated Vehicle with a
  deterministic stock number distinct from
  ``FANDI-INTAKE-1`` (M32.3).
- **Approved deal writeup** on ``Structure Sam`` + ``FANDI-STRUCT-1``
  with realistic four-square terms (distinct values from the M32.3
  fixture so any accidental cross-fixture matching fails loudly).
- **Paired CreditApplication** via ``hand_off_to_fandi`` — the
  real M11.3 code path with M32.1 FK backpointer.
- **NO DealStructure** — the journey creates the DealStructure by
  operator action through the M33.2 UI. Post-run the CA carries
  exactly one DealStructure; re-runs with ``--reset`` restore the
  Incoming state.

Per M20 planning §5.d Option B: composes existing service verbs
(``record_deal_writeup``, ``approve_deal_writeup``,
``hand_off_to_fandi``) — no parallel write paths. Idempotent via
stable fixture markers (lead name, vehicle stock number).

The ``--reset`` flag deletes the seeded lead (cascades the writeup
per M11.3 FK) and any DealStructures the operator created against
the paired CA. Users + roles preserved. Vehicle also reset so a
fresh writeup targets the same stock.

**Why a separate fixture from M32.3 `Intake Iris`.** The M32.3
journey asserts a *terminal* Incoming row (no action). If the M33.2
journey targeted the same fixture, the two journeys would race —
one asserting Incoming, the other transitioning to In progress —
and test order would matter. Distinct fixtures preserve the M32
D11 + M33 D8 fixture-independence guarantee.
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
    DealStructure,
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


# Reuse the M32.3 F&I manager persona + M20.2 sales manager persona.
# Idempotent get_or_create in case those seeds haven't run yet.
FANDI_USERNAME = "acceptance-f-and-i-manager"
FANDI_PASSWORD = "acceptance-fandi-password"
SM_USERNAME = "acceptance-sales-manager"
SM_PASSWORD = "acceptance-sm-password"

FIXTURE_LEAD_NAME = "Structure Sam"
FIXTURE_LEAD_PHONE = "+15553301502"
FIXTURE_LEAD_EMAIL = "structure-sam@example.com"

FIXTURE_VEHICLE_STOCK = "FANDI-STRUCT-1"
FIXTURE_VEHICLE_YEAR = 2024
FIXTURE_VEHICLE_MAKE = "Ford"
FIXTURE_VEHICLE_MODEL = "Bronco"
FIXTURE_VEHICLE_TRIM = "Big Bend"
FIXTURE_VEHICLE_PRICE = Decimal("38750.00")

# Distinct four-square terms from M32.3 `Intake Iris`
# (42500 / 7500 / 3000 / 585 / 60 / 6.99) so accidental cross-
# fixture matches fail loudly.
FIXTURE_TERMS = {
    "vehicle_price": Decimal("38750.00"),
    "trade_allowance": Decimal("5250.00"),
    "down_payment": Decimal("2500.00"),
    "monthly_payment_target": Decimal("520.00"),
    "term_months_target": 66,
    "apr_target": Decimal("7.49"),
}


class Command(BaseCommand):
    help = (
        "Seed the Structure Sam lead + FANDI-STRUCT-1 vehicle + "
        "approved deal writeup + paired CA (no DealStructure) for "
        "the M33.2 fandi-intake-activation Playwright journey. "
        "Fully independent of any M32.2 `Sales Sam` or M32.3 "
        "`Intake Iris` fixture."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete the Structure Sam lead (cascades the writeup) "
                "+ FANDI-STRUCT-1 vehicle + any DealStructures created "
                "against the paired CA. Users + persona role membership "
                "preserved. Paired CA row survives via SET_NULL on "
                "both `lead` and `deal_writeup` FKs (retention-clock "
                "discipline per M10.1 §5.e + M32.1 D9-revised²)."
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
                f"seed_journey_fandi_intake_activation OK — "
                f"fandi_manager={fandi_user.username}, "
                f"lead={lead.pk} ({lead.name!r}), "
                f"vehicle={vehicle.pk} (stock={vehicle.stock_number!r}), "
                f"writeup={writeup.pk} (approved+handed_off), "
                f"credit_application={credit_app.pk} "
                f"(deal_writeup_fk={credit_app.deal_writeup_id}, "
                f"deal_structures={credit_app.deal_structures.count()})."
            )
        )

    def _reset(self, dealership: Dealership) -> None:
        # Order: delete DealStructures against the paired CA first
        # (targeted by CA lookup via lead name → writeup → CA chain),
        # then delete the lead (cascades the writeup per M11.3
        # migration CASCADE FK). CA row survives via SET_NULL.
        paired_ca_pks = list(
            CreditApplication.objects.filter(
                dealership=dealership,
                deal_writeup__lead__name=FIXTURE_LEAD_NAME,
            ).values_list("pk", flat=True)
        )
        deleted_structures, _ = DealStructure.objects.filter(
            dealership=dealership,
            credit_application__pk__in=paired_ca_pks,
        ).delete()

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
        self.stdout.write(
            f"reset: deleted {deleted_structures} deal_structure row(s) "
            f"+ deleted {deleted_leads} lead row(s) (cascade removed "
            f"writeup pks {writeup_pks}) + deleted "
            f"{deleted_vehicles} vehicle row(s). "
            "Paired CAs preserved via SET_NULL (retention-clock)."
        )

    def _provision_fandi_manager(self, dealership: Dealership):
        user, _ = User.objects.get_or_create(
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
        return user

    def _provision_sales_manager(self, dealership: Dealership):
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
        """Idempotent writeup + hand-off provisioning."""
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
            notes="[M33.2 fandi-intake-activation fixture]",
        )
        approve_deal_writeup(writeup=writeup, approved_by_user=sm_user)
        writeup, credit_app = hand_off_to_fandi(writeup=writeup)
        self.stdout.write(
            f"provisioned fresh writeup+handoff (writeup pk="
            f"{writeup.pk}, credit_app pk={credit_app.pk}, "
            f"deal_writeup_fk={credit_app.deal_writeup_id})."
        )
        return writeup, credit_app
