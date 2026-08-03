"""python manage.py seed_journey_sales_manager_daily_startup [--reset]

Milestone 20 · Increment 2 — deterministic seed delta for the
canonical sales manager daily startup journey. Provisions the state
the sales manager journey needs on top of the M18 demo + M19 pilot
base:

- A **sales manager persona** user (``acceptance-sales-manager``)
  with a ``sales_manager`` role at the migration-seeded default
  dealership.
- An **advisor** (``Salesperson`` row with a linked auth user) named
  "Acceptance Advisor" so the assignment dropdown has a stable target.
- Three **unassigned overnight leads** (fresh phone-channel leads
  with varied urgency values) representing the queue the sales
  manager triages first thing.

Per M20 planning §5.d Option B: composes existing service verbs
(``record_phone_lead``) — no parallel write paths. Idempotent via a
stable ``fixture_tag`` in seeded leads' notes + stable
advisor/username slugs.

The ``--reset`` flag deletes the seeded leads + clears the seeded
user's role membership + hides the advisor (is_active=False) then
re-seeds. Users are preserved; the advisor row is preserved so
historical assignments still resolve per :class:`Salesperson` doc.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from dealer_ai.models import (
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    CustomerLead,
    Dealership,
    Salesperson,
    UserDealershipRole,
)
from dealer_ai.services.accounting import seed_default_coa
from dealer_ai.services.leads.channel_intake import record_phone_lead
from dealer_ai.services.tenancy import get_default_dealership

User = get_user_model()


SM_USERNAME = "acceptance-sales-manager"
SM_PASSWORD = "acceptance-sm-password"

ADVISOR_USERNAME = "acceptance-advisor"
ADVISOR_PASSWORD = "acceptance-advisor-password"
ADVISOR_SLUG = "acceptance-advisor"
ADVISOR_NAME = "Acceptance Advisor"
ADVISOR_TITLE = "Test Fixture Advisor"

FIXTURE_TAG = "[M20.2-sales-manager-daily-startup]"

_LEAD_SPECS = (
    {
        "name": "Overnight SM Lead 1",
        "phone": "+15551235001",
        "email": "sm-lead-1@example.com",
        "urgency": "immediate",
    },
    {
        "name": "Overnight SM Lead 2",
        "phone": "+15551235002",
        "email": "sm-lead-2@example.com",
        "urgency": "this_week",
    },
    {
        "name": "Overnight SM Lead 3",
        "phone": "+15551235003",
        "email": "sm-lead-3@example.com",
        "urgency": "this_month",
    },
)


def _existing_leads(dealership: Dealership):
    return CustomerLead.objects.filter(
        dealership=dealership, notes__startswith=FIXTURE_TAG
    )


class Command(BaseCommand):
    help = (
        "Seed the sales-manager persona user + advisor + three unassigned "
        "overnight leads the M20.2 sales manager daily startup journey "
        "triages + assigns."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete the seeded leads, clear the sales-manager's role, "
                "and deactivate the advisor before re-seeding. Users + "
                "advisor row preserved."
            ),
        )

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            dealership = get_default_dealership()
            seed_default_coa(dealership)

            if options["reset"]:
                self._reset(dealership)

            sm_user = self._provision_sales_manager(dealership)
            advisor_user, advisor = self._provision_advisor(dealership)
            leads = self._provision_leads(dealership)

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_journey_sales_manager_daily_startup OK — "
                f"sales_manager={sm_user.username} "
                f"(sales_manager @ {dealership.slug}), "
                f"advisor={advisor.slug} (user={advisor_user.username}), "
                f"leads={[lead.pk for lead in leads]}."
            )
        )

    def _reset(self, dealership: Dealership) -> None:
        deleted_leads, _ = _existing_leads(dealership).delete()
        UserDealershipRole.objects.filter(
            user__username=SM_USERNAME, dealership=dealership
        ).delete()
        # Deactivate the seeded advisor so a subsequent seed re-activates
        # it. Preserves the row (matches :class:`Salesperson` retention
        # semantics).
        Salesperson.objects.filter(slug=ADVISOR_SLUG).update(
            is_active=False
        )
        self.stdout.write(
            f"reset: deleted {deleted_leads} lead row(s) + cleared "
            "sales-manager membership + deactivated advisor."
        )

    def _provision_sales_manager(self, dealership: Dealership):
        user, created = User.objects.get_or_create(
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
        if created:
            self.stdout.write(
                f"provisioned sales-manager user {user.username}."
            )
        else:
            self.stdout.write(
                f"reused existing sales-manager user {user.username}."
            )
        return user

    def _provision_advisor(self, dealership: Dealership):
        advisor_user, user_created = User.objects.get_or_create(
            username=ADVISOR_USERNAME,
            defaults={"email": f"{ADVISOR_USERNAME}@example.com"},
        )
        advisor_user.set_password(ADVISOR_PASSWORD)
        advisor_user.is_active = True
        advisor_user.save()

        # Optional advisor role membership at the same dealership so the
        # advisor could log into their own workspace if the acceptance
        # suite ever exercises that surface. Idempotent.
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
        else:
            self.stdout.write(
                f"reused existing advisor user {advisor_user.username}."
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

    def _provision_leads(self, dealership: Dealership) -> list[CustomerLead]:
        existing = list(_existing_leads(dealership).order_by("pk"))
        if len(existing) >= len(_LEAD_SPECS):
            self.stdout.write(
                f"reused {len(existing)} existing seeded lead(s)."
            )
            return existing[: len(_LEAD_SPECS)]

        for spec in _LEAD_SPECS[len(existing) :]:
            lead = record_phone_lead(
                dealership=dealership,
                name=spec["name"],
                phone=spec["phone"],
                email=spec["email"],
                notes=(
                    f"{FIXTURE_TAG} Fixture lead for M20.2 sales manager "
                    f"daily startup acceptance journey — {spec['name']}."
                ),
                urgency=spec["urgency"],
            )
            existing.append(lead)
            self.stdout.write(f"created lead pk={lead.pk} ({spec['name']}).")

        return existing
