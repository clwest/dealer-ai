"""python manage.py seed_journey_fandi_submission_response [--reset]

Milestone 35 · Increment 2 (SESSION_218) — deterministic seed delta
for the F&I submission-and-response journey per
``MILESTONE_35_PLANNING.md`` §5.b D10 + §5.e M35.2.

Provisions everything the M35.2
``fandi-submission-response-loop`` Playwright describe block needs,
**fully independent of any M32.2 `Sales Sam`, M32.3 `Intake Iris`,
or M33.2 `Structure Sam` fixture** (per M35.0 §5.c R7 independence
guarantee + M34.0 (ff) rerun-hygiene contract — distinct rows,
no shared state, test order irrelevant, parallelism-safe,
independently rerunnable against mutated state):

- **F&I manager persona user** — reuses the shipped M32.3
  ``acceptance-f-and-i-manager`` user + role (idempotent
  get_or_create; no duplicate persona provisioning).
- **Sales-manager provisioning user** — reuses shipped M20.2
  ``acceptance-sales-manager`` (idempotent).
- **Submission Sasha lead** — dedicated CustomerLead with a
  deterministic name distinct from ``Intake Iris`` (M32.3) and
  ``Structure Sam`` (M33.2) so the Playwright spec looks it up
  unambiguously.
- **FANDI-SUB-1 vehicle** — dedicated Vehicle with a deterministic
  stock number distinct from ``FANDI-INTAKE-1`` (M32.3) and
  ``FANDI-STRUCT-1`` (M33.2).
- **Approved deal writeup** on ``Submission Sasha`` + ``FANDI-SUB-1``
  with realistic four-square terms distinct from Iris / Sam so any
  accidental cross-fixture matching fails loudly.
- **Paired CreditApplication** via ``hand_off_to_fandi``.
- **DealStructure on the CA** — pre-created via
  ``record_deal_structure`` service verb so the journey starts
  from the M33.2 In-progress state (not from Incoming). Distinct
  sale price / financing terms so cross-fixture matches fail
  loudly.
- **LenderProgram "Yuma Community Bank"** — active, dealership-
  scoped, deterministic name so the D6 selector populates it.
- **NO existing LenderSubmission** on the DealStructure. The
  journey creates the submission by operator action through the
  M35.2 UI. Re-runs restore the "no submission" invariant per
  M34.0 (ff) rerun-hygiene contract (first re-application at M35.2).

**Rerun invariants** (restored across mutate → re-seed cycles per
M34.0 D8 / candidate durable lesson (ff)):

1. DealStructure exists on the CA (or is re-created if a prior
   run's mutation cascaded it away).
2. LenderProgram "Yuma Community Bank" exists AND
   ``is_active=True``.
3. NO LenderSubmission on the DealStructure — any submission
   created by a prior journey run is deleted at seed re-entry.

Per M20 planning §5.d Option B: composes existing service verbs
(``record_deal_writeup``, ``approve_deal_writeup``,
``hand_off_to_fandi``, ``record_deal_structure``,
``record_lender_program``) — no parallel write paths. Idempotent
via stable fixture markers (lead name, vehicle stock number,
lender program name).

**Why a separate fixture from M33.2 `Structure Sam`.** The M33.2
journey asserts a *transition* from Incoming → In progress. If
the M35.2 journey targeted the same fixture, the two journeys
would race — one asserting the row starts as Incoming, the other
asserting it starts as In progress — and test order would matter.
Distinct fixtures preserve the M32 D11 + M33 D8 + M35 D10
fixture-independence guarantee.

**M20_ACCEPTANCE_DB env-guard** matches M34 D4 pattern — this
command is invoked only from the acceptance workspace's
``login.setup.ts``; not part of any dev/prod seed sequence.
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
    LenderProgram,
    LenderSubmission,
    UserDealershipRole,
    Vehicle,
)
from dealer_ai.services.accounting import seed_default_coa
from dealer_ai.services.deal_writeups import (
    approve_deal_writeup,
    hand_off_to_fandi,
    record_deal_writeup,
)
from dealer_ai.services.f_and_i import record_deal_structure
from dealer_ai.services.tenancy import get_default_dealership


User = get_user_model()


# Reuse the M32.3 F&I manager + M20.2 sales manager persona.
FANDI_USERNAME = "acceptance-f-and-i-manager"
FANDI_PASSWORD = "acceptance-fandi-password"
SM_USERNAME = "acceptance-sales-manager"
SM_PASSWORD = "acceptance-sm-password"

FIXTURE_LEAD_NAME = "Submission Sasha"
FIXTURE_LEAD_PHONE = "+15553501502"
FIXTURE_LEAD_EMAIL = "submission-sasha@example.com"

FIXTURE_VEHICLE_STOCK = "FANDI-SUB-1"
FIXTURE_VEHICLE_YEAR = 2024
FIXTURE_VEHICLE_MAKE = "Ford"
FIXTURE_VEHICLE_MODEL = "Escape"
FIXTURE_VEHICLE_TRIM = "ST-Line"
FIXTURE_VEHICLE_PRICE = Decimal("32450.00")

FIXTURE_LENDER_PROGRAM_NAME = "Yuma Community Bank"

# Distinct four-square terms from M32.3 Intake Iris + M33.2 Structure
# Sam so accidental cross-fixture matches fail loudly.
FIXTURE_TERMS = {
    "vehicle_price": Decimal("32450.00"),
    "trade_allowance": Decimal("6100.00"),
    "down_payment": Decimal("1800.00"),
    "monthly_payment_target": Decimal("445.00"),
    "term_months_target": 72,
    "apr_target": Decimal("8.24"),
}

# Distinct DealStructure inputs so accidental cross-fixture matches
# fail loudly at the F&I structuring layer as well.
FIXTURE_DEAL_STRUCTURE = {
    "sale_price": Decimal("32450.00"),
    "amount_financed": Decimal("27300.00"),
    "apr": Decimal("8.2400"),
    "term_months": 72,
    "monthly_payment": Decimal("445.00"),
    "down_payment": Decimal("1800.00"),
    "trade_allowance": Decimal("6100.00"),
    "trade_payoff": Decimal("2450.00"),
    "taxes": Decimal("2350.00"),
    "fees": Decimal("650.00"),
}


class Command(BaseCommand):
    help = (
        "Seed the Submission Sasha lead + FANDI-SUB-1 vehicle + "
        "approved deal writeup + paired CA + pre-created "
        "DealStructure + Yuma Community Bank LenderProgram (no "
        "LenderSubmission) for the M35.2 fandi-submission-response-"
        "loop Playwright journey. Rerun-safe against mutated state "
        "per M34.0 (ff) contract. Fully independent of any M32.2 / "
        "M32.3 / M33.2 fixture."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete the Submission Sasha lead (cascades the "
                "writeup + DealStructure + LenderSubmissions) + "
                "FANDI-SUB-1 vehicle + Yuma Community Bank "
                "LenderProgram. Users + persona role membership "
                "preserved. Paired CA row survives via SET_NULL "
                "on both `lead` and `deal_writeup` FKs (retention-"
                "clock discipline per M10.1 §5.e + M32.1 D9-revised²)."
            ),
        )

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            dealership = get_default_dealership()
            seed_default_coa(dealership)

            if options["reset"]:
                self._reset(dealership)

            # Rerun-safe invariant #3 restore FIRST: delete any
            # LenderSubmissions created by a prior journey run on
            # the Submission Sasha DealStructure. Runs before the
            # DealStructure lookup so a prior run's cascade
            # (should it occur) is fully cleaned up. Scoped by
            # tenant + lead name → writeup → CA → DS chain.
            self._delete_prior_lender_submissions(dealership)

            fandi_user = self._provision_fandi_manager(dealership)
            sm_user = self._provision_sales_manager(dealership)
            lender_program = self._provision_lender_program(dealership)
            lead = self._provision_lead(dealership)
            vehicle = self._provision_vehicle(dealership)
            writeup, credit_app = self._provision_writeup_and_handoff(
                dealership, lead, vehicle, sm_user
            )
            deal_structure = self._provision_deal_structure(
                dealership, credit_app, vehicle
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_journey_fandi_submission_response OK — "
                f"fandi_manager={fandi_user.username}, "
                f"lead={lead.pk} ({lead.name!r}), "
                f"vehicle={vehicle.pk} (stock={vehicle.stock_number!r}), "
                f"writeup={writeup.pk} (approved+handed_off), "
                f"credit_application={credit_app.pk}, "
                f"deal_structure={deal_structure.pk}, "
                f"lender_program={lender_program.pk} "
                f"({lender_program.name!r}, "
                f"is_active={lender_program.is_active}), "
                f"lender_submissions_on_ds="
                f"{deal_structure.lender_submissions.count()}."
            )
        )

    def _delete_prior_lender_submissions(
        self, dealership: Dealership
    ) -> None:
        """Rerun-safe invariant #3 restore per M34.0 (ff). Scoped by
        tenant + Submission Sasha lead → writeup → CA → DS chain.
        Never touches other fixtures' submissions."""
        deleted, _ = LenderSubmission.objects.filter(
            dealership=dealership,
            deal_structure__credit_application__deal_writeup__lead__name=(
                FIXTURE_LEAD_NAME
            ),
        ).delete()
        if deleted:
            self.stdout.write(
                f"rerun-hygiene: deleted {deleted} prior "
                f"LenderSubmission row(s) on Submission Sasha "
                f"DealStructure(s)."
            )

    def _reset(self, dealership: Dealership) -> None:
        # Delete DealStructures against the paired CA first (targeted
        # by CA lookup via lead name → writeup → CA chain). Then
        # delete the lead (cascades the writeup). Then the vehicle +
        # lender program. CA row survives via SET_NULL.
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
        deleted_programs, _ = LenderProgram.objects.filter(
            dealership=dealership, name=FIXTURE_LENDER_PROGRAM_NAME,
        ).delete()
        self.stdout.write(
            f"reset: deleted {deleted_structures} deal_structure "
            f"row(s) + deleted {deleted_leads} lead row(s) (cascade "
            f"removed writeup pks {writeup_pks}) + deleted "
            f"{deleted_vehicles} vehicle row(s) + deleted "
            f"{deleted_programs} lender_program row(s). "
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

    def _provision_lender_program(
        self, dealership: Dealership
    ) -> LenderProgram:
        """Rerun-safe invariant #2: LenderProgram exists AND
        is_active=True. If a prior run somehow deactivated the row,
        reactivate it in place."""
        program, created = LenderProgram.objects.get_or_create(
            dealership=dealership,
            name=FIXTURE_LENDER_PROGRAM_NAME,
            defaults={
                "contact": "loans@yumacommunitybank.example",
                "terms_summary": (
                    "M35.2 Playwright fixture — used by the "
                    "fandi-submission-response-loop journey. "
                    "Distinct from other fixtures."
                ),
                "is_active": True,
            },
        )
        if not program.is_active:
            program.is_active = True
            program.save(update_fields=["is_active", "updated_at"])
            self.stdout.write(
                f"rerun-hygiene: reactivated lender_program pk="
                f"{program.pk}."
            )
        if created:
            self.stdout.write(f"provisioned lender_program pk={program.pk}.")
        else:
            self.stdout.write(f"reused existing lender_program pk={program.pk}.")
        return program

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
            notes="[M35.2 fandi-submission-response-loop fixture]",
        )
        approve_deal_writeup(writeup=writeup, approved_by_user=sm_user)
        writeup, credit_app = hand_off_to_fandi(writeup=writeup)
        self.stdout.write(
            f"provisioned fresh writeup+handoff (writeup pk="
            f"{writeup.pk}, credit_app pk={credit_app.pk})."
        )
        return writeup, credit_app

    def _provision_deal_structure(
        self,
        dealership: Dealership,
        credit_app: CreditApplication,
        vehicle: Vehicle,
    ) -> DealStructure:
        """Rerun-safe invariant #1: DealStructure exists on the CA.

        If any DealStructure already exists on the CA (from a prior
        run OR from a journey step that mutated state before
        completing), reuse the latest one. Otherwise create a fresh
        one via ``record_deal_structure``.
        """
        existing = (
            DealStructure.objects.filter(
                dealership=dealership,
                credit_application=credit_app,
                vehicle=vehicle,
            )
            .order_by("-created_at", "-pk")
            .first()
        )
        if existing is not None:
            self.stdout.write(
                f"reused existing deal_structure pk={existing.pk}."
            )
            return existing
        deal_structure = record_deal_structure(
            dealership=dealership,
            credit_application=credit_app,
            vehicle=vehicle,
            **FIXTURE_DEAL_STRUCTURE,
        )
        self.stdout.write(
            f"provisioned fresh deal_structure pk={deal_structure.pk}."
        )
        return deal_structure
