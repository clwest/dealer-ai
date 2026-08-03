"""python manage.py seed_journey_pilot_onboarding [--reset]

Milestone 20 · Increment 1 — deterministic seed delta for the
canonical M20.1 Playwright acceptance journey. Provisions the state
the pilot onboarding journey needs on top of the M18 demo + M19 pilot
base:

- A **platform operator** user (``acceptance-operator``) with a
  ``sales_manager`` role at the migration-seeded default dealership so
  the persona can reach ``/dealer-ai-admin`` and see the
  ``<PilotOnboardingSection>``.
- A **pilot owner** user (``acceptance-pilot-owner``) that the
  journey nominates as the owner_username when creating the pilot
  via the M19.3 create endpoint.
- A **qualified PilotProspect** representing a demo tester who has
  been marked as pilot-ready (``eligibility_state="qualified"``). The
  journey's operator persona sees this prospect in the operator
  surface and converts them into a pilot dealership.

Per M20 planning §5.d Option B: composes existing service verbs
(``create_prospect`` + ``advance_prospect_state``) — no parallel
write paths. Idempotent via ``get_or_create`` on stable slugs / usernames.

The ``--reset`` flag deletes the seeded PilotProspect + resets the
seeded users' roles so a subsequent invocation starts from a known
clean state. Users are preserved (deleting them cascades into rows
the acceptance suite may not know about).
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from dealer_ai.models import (
    PILOT_PROSPECT_STATE_QUALIFIED,
    ROLE_SALES_MANAGER,
    Dealership,
    PilotProspect,
    UserDealershipRole,
)
from dealer_ai.services.accounting import seed_default_coa
from dealer_ai.services.pilot_onboarding import (
    advance_prospect_state,
    create_prospect,
)
from dealer_ai.services.tenancy import get_default_dealership

User = get_user_model()


# Stable identifiers so the seed is idempotent + the Playwright suite
# has predictable targets.
OPERATOR_USERNAME = "acceptance-operator"
OPERATOR_PASSWORD = "acceptance-op-password"
PILOT_OWNER_USERNAME = "acceptance-pilot-owner"
PILOT_OWNER_PASSWORD = "acceptance-owner-password"

PROSPECT_CONTACT_EMAIL = "acceptance-prospect@example.com"
PROSPECT_CONTACT_NAME = "Acceptance Prospect"
PROSPECT_DEALER_BUSINESS_NAME = "Acceptance Motors"
PROSPECT_CONTACT_SOURCE = "m20-acceptance-fixture"
PROSPECT_CHRIS_NOTES = (
    "Fixture prospect created by seed_journey_pilot_onboarding for "
    "the M20.1 Playwright acceptance suite. Marked qualified so the "
    "canonical journey can exercise the demo → pilot conversion path."
)


class Command(BaseCommand):
    help = (
        "Seed the platform-operator + pilot-owner users and the qualified "
        "PilotProspect the M20.1 canonical Playwright journey converts."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete the seeded PilotProspect and reset the seeded "
                "users' role memberships before re-seeding. Users are "
                "preserved."
            ),
        )

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            # Guarantee the default dealership exists + has its default
            # COA. `get_default_dealership()` returns the migration-
            # seeded row; `seed_default_coa` is idempotent per M13.1.
            default_dealership = get_default_dealership()
            seed_default_coa(default_dealership)

            if options["reset"]:
                self._reset(default_dealership)

            operator = self._provision_operator(default_dealership)
            pilot_owner = self._provision_pilot_owner()
            prospect = self._provision_qualified_prospect()

        self.stdout.write(
            self.style.SUCCESS(
                "seed_journey_pilot_onboarding OK "
                f"— operator={operator.username} "
                f"(sales_manager @ {default_dealership.slug}), "
                f"pilot_owner={pilot_owner.username}, "
                f"prospect={prospect.pk} "
                f"(state={prospect.eligibility_state}, "
                f"business={prospect.dealer_business_name!r})."
            )
        )

    def _reset(self, default_dealership: Dealership) -> None:
        deleted_prospects, _ = PilotProspect.objects.filter(
            contact_email=PROSPECT_CONTACT_EMAIL
        ).delete()
        UserDealershipRole.objects.filter(
            user__username__in=(OPERATOR_USERNAME, PILOT_OWNER_USERNAME),
            dealership=default_dealership,
        ).delete()
        self.stdout.write(
            f"reset: deleted {deleted_prospects} prospect row(s) + "
            "cleared operator/pilot-owner memberships."
        )

    def _provision_operator(self, default_dealership: Dealership):
        user, created = User.objects.get_or_create(
            username=OPERATOR_USERNAME,
            defaults={"email": f"{OPERATOR_USERNAME}@example.com"},
        )
        # `set_password` is safe to call whether the user was created
        # this run or not — it re-hashes with the current algorithm.
        user.set_password(OPERATOR_PASSWORD)
        # `is_staff=True` is a belt-and-suspenders in case any admin
        # page checks it; the pilot admin surface only requires
        # IsAuthenticated per M19.3, but `sales_manager` role at the
        # default dealership is what gates the wider /dealer-ai-admin
        # surface via M1.4 authorization.
        user.is_staff = True
        user.is_active = True
        user.save()
        UserDealershipRole.objects.get_or_create(
            user=user,
            dealership=default_dealership,
            defaults={"role": ROLE_SALES_MANAGER},
        )
        if created:
            self.stdout.write(f"provisioned operator user {user.username}.")
        else:
            self.stdout.write(
                f"reused existing operator user {user.username}."
            )
        return user

    def _provision_pilot_owner(self):
        user, created = User.objects.get_or_create(
            username=PILOT_OWNER_USERNAME,
            defaults={"email": f"{PILOT_OWNER_USERNAME}@example.com"},
        )
        user.set_password(PILOT_OWNER_PASSWORD)
        user.is_active = True
        user.save()
        if created:
            self.stdout.write(
                f"provisioned pilot owner user {user.username}."
            )
        else:
            self.stdout.write(
                f"reused existing pilot owner user {user.username}."
            )
        return user

    def _provision_qualified_prospect(self) -> PilotProspect:
        # Idempotency: match on the fixture's stable contact_email.
        existing = PilotProspect.objects.filter(
            contact_email=PROSPECT_CONTACT_EMAIL
        ).order_by("pk").first()
        if existing is not None:
            if existing.eligibility_state == PILOT_PROSPECT_STATE_QUALIFIED:
                self.stdout.write(
                    f"reused existing qualified prospect {existing.pk}."
                )
                return existing
            # Advance to qualified using the service verb (respects the
            # state machine's legal-transition guard).
            if existing.eligibility_state == "prospect":
                advanced = advance_prospect_state(
                    prospect=existing,
                    new_state=PILOT_PROSPECT_STATE_QUALIFIED,
                )
                self.stdout.write(
                    f"advanced existing prospect {advanced.pk} "
                    f"to qualified."
                )
                return advanced
            # Terminal (converted/declined) — do NOT mutate, create a
            # fresh prospect row. The M19 §5.b design says "revisit a
            # declined prospect" = new row.
            self.stdout.write(
                f"existing prospect {existing.pk} is terminal "
                f"({existing.eligibility_state!r}); creating a fresh "
                f"qualified prospect."
            )

        prospect = create_prospect(
            contact_name=PROSPECT_CONTACT_NAME,
            contact_email=PROSPECT_CONTACT_EMAIL,
            dealer_business_name=PROSPECT_DEALER_BUSINESS_NAME,
            contact_source=PROSPECT_CONTACT_SOURCE,
            chris_notes=PROSPECT_CHRIS_NOTES,
        )
        prospect = advance_prospect_state(
            prospect=prospect,
            new_state=PILOT_PROSPECT_STATE_QUALIFIED,
        )
        self.stdout.write(
            f"created new qualified prospect {prospect.pk}."
        )
        return prospect
