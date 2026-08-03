"""python manage.py seed_journey_bhph_collections_workflow [--reset]

Milestone 20 · Increment 4 — deterministic seed delta for the
canonical BHPH collections workflow journey. Provisions the state
the BHPH collections journey needs on top of the M18 demo + M19
pilot base:

- A **BHPH collector persona** user
  (``acceptance-bhph-collector``) with a ``sales_manager`` role at
  the migration-seeded default dealership. (The M12 collections
  endpoints gate on
  ``IsSalesManagerOrOwnerAtActiveDealership``; the model-level
  ``ROLE_COLLECTIONS`` constant is defined but not currently
  wired to any endpoint. §0.a M20.4 decision 2.)
- One **fixture BHPH note** on a stable vehicle
  (stock ``M20-BHPH-ACCEPT``) with a matching Sale + CustomerLead
  (buyer) so the note has an anchor in the M15 sale substrate.
- One **historical BhphPayment** so the note's Payments card has
  content.
- One **BhphPromiseToPay** in the ``broken`` state so the Promises
  card has content with the "operator needs to act" signal.
- One **CollectionContact** so the Contacts card has content.
- One **Repossession** in the ``ordered`` state so the
  Repossessions card has content and completes the "book review"
  narrative.

Milestone 21 · Increment 2 additions — enable the M21.2 write-side
journey extension to walk record-PtP → mark-broken → log-contact →
initiate-repossession → mark-recovered → mark-re-intaked without
needing to fabricate state mid-journey:

- One **second BhphPromiseToPay** in the ``promised`` state — the
  journey marks it broken (the seeded ``broken`` promise remains
  as the historical showcase).
- One **second Repossession** pre-transitioned to ``recovered`` —
  the journey marks it re-intaked via the ConditionReport below
  (the seeded ``ordered`` repossession remains for the mark-
  recovered step).
- One **ConditionReport** for the fixture vehicle in
  ``complete`` state — referenced by ID during the mark-re-intaked
  step.

Per M20 planning §5.d Option B: composes M12 service verbs
(``record_bhph_note`` cannot be used because it requires an
existing Sale + also enforces a uniqueness guard that fights
idempotency; direct object creation is the established pattern in
the demo archetype at
``services/demo_store/archetypes/bhph.py:672-711``). All child
rows go through the M12 service verbs (``record_payment``,
``record_promise`` + ``mark_broken``, ``record_contact``,
``record_repossession``) — no parallel write paths.

Idempotent via the stable vehicle stock number ``M20-BHPH-ACCEPT``.
``--reset`` deletes the fixture chain (repossession, contact,
promise, payment, note, sale, vehicle, buyer) and clears the
collector's role membership before re-seeding. The user is
preserved.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from dealer_ai.models import (
    BHPH_CONTACT_CHANNEL_PHONE,
    BHPH_CONTACT_OUTCOME_LEFT_MESSAGE,
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_PAYMENT_METHOD_CASH,
    BHPH_PROMISE_REASON_PAYCHECK,
    BHPH_PROMISE_REASON_TAX_REFUND,
    CONDITION_REPORT_STATUS_COMPLETE,
    LEAD_CHANNEL_WALK_IN,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    BhphPayment,
    BhphPromiseToPay,
    CollectionContact,
    ConditionReport,
    CustomerLead,
    Dealership,
    Repossession,
    Sale,
    UserDealershipRole,
    Vehicle,
)
from dealer_ai.services.accounting import seed_default_coa
from dealer_ai.services.bhph_notes.bhph_note import (
    bhph_note_periodic_payment,
)
from dealer_ai.services.bhph_payments.bhph_payment import record_payment
from dealer_ai.services.bhph_promises.bhph_promise import (
    mark_broken,
    record_promise,
)
from dealer_ai.services.collection_contacts.collection_contact import (
    record_contact,
)
from dealer_ai.services.repossessions.repossession import (
    mark_recovered,
    record_repossession,
)
from dealer_ai.services.tenancy import get_default_dealership

User = get_user_model()


COLLECTOR_USERNAME = "acceptance-bhph-collector"
COLLECTOR_PASSWORD = "acceptance-bhph-password"

FIXTURE_STOCK = "M20-BHPH-ACCEPT"
FIXTURE_BUYER_NAME = "Acceptance Buyer"
FIXTURE_BUYER_EMAIL = "acceptance-bhph-buyer@example.com"
FIXTURE_PRINCIPAL = Decimal("6500.00")
FIXTURE_APR = Decimal("21.99")
FIXTURE_TERM_WEEKS = 78
FIXTURE_PROMISE_AMOUNT = Decimal("125.00")


def _existing_note(dealership: Dealership) -> BhphNote | None:
    return BhphNote.objects.filter(
        dealership=dealership,
        sale__vehicle__stock_number=FIXTURE_STOCK,
    ).order_by("pk").first()


class Command(BaseCommand):
    help = (
        "Seed the bhph-collector persona + a fixture BHPH note with "
        "payment + broken promise + collection contact + ordered "
        "repossession — state the M20.4 BHPH collections workflow "
        "acceptance journey reviews."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete the fixture chain and clear the "
                "bhph-collector's role membership before re-seeding. "
                "User is preserved."
            ),
        )

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            dealership = get_default_dealership()
            seed_default_coa(dealership)

            if options["reset"]:
                self._reset(dealership)

            collector = self._provision_collector(dealership)
            note = self._provision_note_chain(dealership, collector)

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_journey_bhph_collections_workflow OK — "
                f"collector={collector.username} "
                f"(sales_manager @ {dealership.slug}), "
                f"note_pk={note.pk}, "
                f"vehicle_stock={FIXTURE_STOCK}."
            )
        )

    def _reset(self, dealership: Dealership) -> None:
        # Delete children first, then note, then sale + vehicle +
        # buyer. Cascades cover most of it but explicit deletion
        # keeps counts observable.
        note = _existing_note(dealership)
        n_repos = n_contacts = n_promises = n_payments = n_reports = 0
        if note is not None:
            n_repos, _ = Repossession.objects.filter(
                note=note
            ).delete()
            n_contacts, _ = CollectionContact.objects.filter(
                note=note
            ).delete()
            n_promises, _ = BhphPromiseToPay.objects.filter(
                note=note
            ).delete()
            n_payments, _ = BhphPayment.objects.filter(note=note).delete()
            sale = note.sale
            note.delete()
            # Sale + vehicle + buyer via the sale's FKs. ConditionReport
            # rows on the vehicle cascade with the vehicle delete.
            vehicle = sale.vehicle
            buyer = sale.buyer
            n_reports = ConditionReport.objects.filter(
                vehicle=vehicle
            ).count()
            sale.delete()
            vehicle.delete()
            if buyer is not None:
                buyer.delete()
        UserDealershipRole.objects.filter(
            user__username=COLLECTOR_USERNAME, dealership=dealership
        ).delete()
        self.stdout.write(
            f"reset: deleted repos={n_repos} contacts={n_contacts} "
            f"promises={n_promises} payments={n_payments} "
            f"reports={n_reports} + note chain + "
            "cleared collector membership."
        )

    def _provision_collector(self, dealership: Dealership):
        user, created = User.objects.get_or_create(
            username=COLLECTOR_USERNAME,
            defaults={"email": f"{COLLECTOR_USERNAME}@example.com"},
        )
        user.set_password(COLLECTOR_PASSWORD)
        user.is_active = True
        user.save()
        UserDealershipRole.objects.get_or_create(
            user=user,
            dealership=dealership,
            defaults={"role": ROLE_SALES_MANAGER},
        )
        if created:
            self.stdout.write(
                f"provisioned collector user {user.username}."
            )
        else:
            self.stdout.write(
                f"reused existing collector user {user.username}."
            )
        return user

    def _provision_note_chain(
        self, dealership: Dealership, collector
    ) -> BhphNote:
        existing = _existing_note(dealership)
        if existing is not None:
            self.stdout.write(
                f"reused existing fixture BHPH note pk={existing.pk}."
            )
            return existing

        now = timezone.now()

        # 1. Vehicle
        vehicle = Vehicle.objects.create(
            dealership=dealership,
            stock_number=FIXTURE_STOCK,
            year=2013,
            model="Camry",
            price=Decimal("8995.00"),
        )
        # 2. Buyer (CustomerLead)
        buyer = CustomerLead.objects.create(
            dealership=dealership,
            name=FIXTURE_BUYER_NAME,
            email=FIXTURE_BUYER_EMAIL,
            phone="+15559990001",
            channel=LEAD_CHANNEL_WALK_IN,
            urgency="immediate",
            notes="[M20.4-bhph] Fixture buyer for BHPH acceptance journey.",
        )
        # 3. Sale — direct create per demo archetype pattern (bypasses
        #    M15 GL post noise for fixture-only rows).
        sale_date = (now - dt.timedelta(weeks=12)).date()
        sale = Sale.objects.create(
            dealership=dealership,
            vehicle=vehicle,
            buyer=buyer,
            sale_date=sale_date,
            sold_price=FIXTURE_PRINCIPAL,
            finance_type=SALE_FINANCE_TYPE_BHPH,
            lender_name="",
            gross_realized=Decimal("0.00"),
        )
        # 4. BhphNote — direct create per demo archetype pattern
        #    (short-circuits payment_amount computation + duplicate
        #    guard).
        payment_amount = bhph_note_periodic_payment(
            FIXTURE_PRINCIPAL,
            FIXTURE_APR,
            FIXTURE_TERM_WEEKS,
            BHPH_PAYMENT_FREQUENCY_WEEKLY,
        )
        note = BhphNote.objects.create(
            dealership=dealership,
            sale=sale,
            principal_financed=FIXTURE_PRINCIPAL,
            apr=FIXTURE_APR,
            term_weeks=FIXTURE_TERM_WEEKS,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            payment_amount=payment_amount,
            first_payment_due=sale_date + dt.timedelta(days=7),
        )

        # 5. One historical payment — through the service verb.
        record_payment(
            dealership=dealership,
            note=note,
            paid_at=now - dt.timedelta(weeks=4),
            amount=payment_amount,
            method=BHPH_PAYMENT_METHOD_CASH,
        )
        # 6. One promise, transitioned to broken so the operator has
        #    an actionable signal on the daily book.
        promise = record_promise(
            dealership=dealership,
            note=note,
            promised_at=now - dt.timedelta(days=3),
            promised_amount=FIXTURE_PROMISE_AMOUNT,
            promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
            notes="[M20.4-bhph] Fixture promise (initially promised).",
        )
        mark_broken(
            dealership=dealership,
            promise=promise,
            notes="[M20.4-bhph] Fixture — promise broken (no payment).",
        )
        # 7. One collection contact (immutable audit log).
        record_contact(
            dealership=dealership,
            note=note,
            contacted_at=now - dt.timedelta(days=1),
            channel=BHPH_CONTACT_CHANNEL_PHONE,
            outcome=BHPH_CONTACT_OUTCOME_LEFT_MESSAGE,
            contacted_by_user=collector,
            notes="[M20.4-bhph] Fixture contact — left voicemail.",
        )
        # 8. One repossession in ordered state (not recovered yet).
        record_repossession(
            dealership=dealership,
            note=note,
            ordered_at=now - dt.timedelta(hours=6),
            agent_name="Acceptance Recovery Services",
            ordered_by_user=collector,
            notes="[M20.4-bhph] Fixture repo order.",
        )
        # 9. [M21.2] A second promise in the ``promised`` state so the
        #    M21.2 journey has a clean target for the mark-broken step
        #    without depending on the seeded ``broken`` promise's state.
        record_promise(
            dealership=dealership,
            note=note,
            promised_at=now - dt.timedelta(hours=12),
            promised_amount=FIXTURE_PROMISE_AMOUNT,
            promised_reason=BHPH_PROMISE_REASON_TAX_REFUND,
            notes=(
                "[M21.2-bhph] Fixture promised-state PTP — journey marks broken."
            ),
        )
        # 10. [M21.2] A second repossession pre-transitioned to
        #     ``recovered`` so the journey can exercise mark-re-intaked
        #     directly (mark-recovered runs against the seeded
        #     ``ordered`` repossession created in step 8).
        recovered_repo = record_repossession(
            dealership=dealership,
            note=note,
            ordered_at=now - dt.timedelta(days=5),
            agent_name="Acceptance Recovery Services",
            ordered_by_user=collector,
            notes=(
                "[M21.2-bhph] Fixture recovered repossession — "
                "journey marks re-intaked with ConditionReport."
            ),
        )
        mark_recovered(
            dealership=dealership,
            repossession=recovered_repo,
            recovered_at=now - dt.timedelta(days=2),
            recovery_location="Acceptance recovery yard",
            notes=(
                "[M21.2-bhph] Fixture — marked recovered by seed so the "
                "M21.2 journey can walk straight to re-intake."
            ),
        )
        # 11. [M21.2] One complete ConditionReport for the fixture
        #     vehicle so the mark-re-intaked step has a referenceable
        #     intake report ID. In-tenant + status=complete satisfies
        #     the M12.6 re-intake precondition.
        report_time = now - dt.timedelta(days=1)
        ConditionReport.objects.create(
            dealership=dealership,
            vehicle=vehicle,
            inspector_name="Acceptance QC Inspector",
            inspected_at=report_time,
            mileage_at_inspection=98_500,
            status=CONDITION_REPORT_STATUS_COMPLETE,
            completed_at=report_time,
            notes=(
                "[M21.2-bhph] Fixture intake report for the recovered "
                "repossession — referenced by mark-re-intaked step."
            ),
        )

        self.stdout.write(
            f"created BHPH note chain pk={note.pk} "
            f"(vehicle={vehicle.stock_number}, sale={sale.pk}) "
            "with M21.2 write-side fixtures (promised-state promise, "
            "recovered-state repossession, condition report)."
        )
        return note
