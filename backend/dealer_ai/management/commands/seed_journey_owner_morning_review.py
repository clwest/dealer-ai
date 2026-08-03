"""python manage.py seed_journey_owner_morning_review [--reset]

Milestone 20 · Increment 2 — deterministic seed delta for the
canonical owner morning review journey. Provisions the state the
owner journey needs on top of the M18 demo + M19 pilot base:

- An **owner persona** user (``acceptance-owner``) with a
  ``dealer_owner`` role at the migration-seeded default dealership
  so the persona can reach ``/dealer-ai-overview`` +
  ``/dealer-ai-admin`` via the M4 admin gate.
- A pair of **unassigned overnight leads** (fresh phone-channel
  leads with ``urgency="immediate"``) that show up in the "Today's
  leads" card + the leads-list page. These represent the pipeline
  the owner scans first thing in the morning.

Per M20 planning §5.d Option B: composes existing service verbs
(``record_phone_lead``) — no parallel write paths. Idempotent via a
stable ``fixture_tag`` embedded in the seeded leads' notes so
subsequent invocations detect + reuse existing rows rather than
duplicating.

The ``--reset`` flag deletes the seeded leads + clears the seeded
user's role membership then re-seeds. The user is preserved.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from dealer_ai.models import (
    ROLE_DEALER_OWNER,
    CustomerLead,
    Dealership,
    UserDealershipRole,
)
from dealer_ai.services.accounting import seed_default_coa
from dealer_ai.services.leads.channel_intake import record_phone_lead
from dealer_ai.services.tenancy import get_default_dealership

User = get_user_model()


OWNER_USERNAME = "acceptance-owner"
OWNER_PASSWORD = "acceptance-owner-password"

# Embedded fixture tag lets the seed detect its own prior rows on
# subsequent invocations without needing a dedicated column. Every
# seeded lead's ``notes`` field starts with this exact prefix.
FIXTURE_TAG = "[M20.2-owner-morning-review]"

_LEAD_SPECS = (
    {
        "name": "Overnight Buyer A",
        "phone": "+15551234001",
        "email": "buyer-a@example.com",
        "urgency": "immediate",
    },
    {
        "name": "Overnight Buyer B",
        "phone": "+15551234002",
        "email": "buyer-b@example.com",
        "urgency": "this_week",
    },
)


def _existing_leads(dealership: Dealership):
    return CustomerLead.objects.filter(
        dealership=dealership, notes__startswith=FIXTURE_TAG
    )


class Command(BaseCommand):
    help = (
        "Seed the owner persona user + two unassigned overnight leads the "
        "M20.2 canonical owner morning review journey scans."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete the seeded leads and clear the seeded user's "
                "role membership before re-seeding. User is preserved."
            ),
        )

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            dealership = get_default_dealership()
            seed_default_coa(dealership)

            if options["reset"]:
                self._reset(dealership)

            owner = self._provision_owner(dealership)
            leads = self._provision_leads(dealership)

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_journey_owner_morning_review OK — "
                f"owner={owner.username} (dealer_owner @ {dealership.slug}), "
                f"leads={[lead.pk for lead in leads]}."
            )
        )

    def _reset(self, dealership: Dealership) -> None:
        deleted_leads, _ = _existing_leads(dealership).delete()
        UserDealershipRole.objects.filter(
            user__username=OWNER_USERNAME, dealership=dealership
        ).delete()
        self.stdout.write(
            f"reset: deleted {deleted_leads} lead row(s) + "
            "cleared owner membership."
        )

    def _provision_owner(self, dealership: Dealership):
        user, created = User.objects.get_or_create(
            username=OWNER_USERNAME,
            defaults={"email": f"{OWNER_USERNAME}@example.com"},
        )
        user.set_password(OWNER_PASSWORD)
        user.is_active = True
        user.save()
        UserDealershipRole.objects.get_or_create(
            user=user,
            dealership=dealership,
            defaults={"role": ROLE_DEALER_OWNER},
        )
        if created:
            self.stdout.write(f"provisioned owner user {user.username}.")
        else:
            self.stdout.write(f"reused existing owner user {user.username}.")
        return user

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
                    f"{FIXTURE_TAG} Fixture lead for M20.2 owner morning "
                    f"review acceptance journey — {spec['name']}."
                ),
                urgency=spec["urgency"],
            )
            existing.append(lead)
            self.stdout.write(f"created lead pk={lead.pk} ({spec['name']}).")

        return existing
