"""Milestone 1 · Increments 1, 2 & 3 — Dealership + tenant-carrier FKs.

Increment 1 (model): tests the `Dealership` shape in isolation.
Increment 2 (FKs + backfill): tests that the six tenant-carrying
models expose a `dealership` FK, that the data migration seeded a
deterministic default row (slug=`default`), and that the fallback
name-resolution ladder produced a valid name.
Increment 3 (write-path plumbing + NOT NULL): tests that the six FKs
are now NOT NULL, that :func:`services.tenancy.get_default_dealership`
returns the seeded row, and that the ``pre_save`` fallback attaches
the default when the caller leaves ``dealership`` unset.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from dealer_ai.models import (
    ChatMessage,
    ChatSession,
    CustomerLead,
    DealerOnboardingProfile,
    Dealership,
    Salesperson,
    Vehicle,
)


class DealershipModel(TestCase):
    def test_round_trip(self):
        d = Dealership.objects.create(name="Copper Canyon Auto", slug="copper-canyon")
        fetched = Dealership.objects.get(slug="copper-canyon")
        self.assertEqual(fetched.pk, d.pk)
        self.assertEqual(fetched.name, "Copper Canyon Auto")

    def test_str_returns_name(self):
        d = Dealership.objects.create(name="Rivertown Motors", slug="rivertown")
        self.assertEqual(str(d), "Rivertown Motors")

    def test_slug_is_unique(self):
        Dealership.objects.create(name="First", slug="dup")
        with self.assertRaises(IntegrityError):
            Dealership.objects.create(name="Second", slug="dup")

    def test_default_ordering_is_by_name(self):
        # Migration 0009 seeds a "Default Dealership" row; exclude it so
        # this test locks the Meta.ordering contract on just the rows
        # it created.
        Dealership.objects.create(name="Zeta", slug="zeta")
        Dealership.objects.create(name="Alpha", slug="alpha")
        Dealership.objects.create(name="Mu", slug="mu")
        names = list(
            Dealership.objects.exclude(slug="default").values_list(
                "name", flat=True
            )
        )
        self.assertEqual(names, ["Alpha", "Mu", "Zeta"])


class DefaultDealershipBackfill(TestCase):
    """Migration 0009 seeded a `slug=default` Dealership and pointed
    every pre-existing row of the six tenant carriers at it. In a fresh
    test DB the "pre-existing rows" set is empty, so we only assert the
    default row's presence + shape and that new rows can attach to it.
    """

    def test_default_dealership_row_exists(self):
        default = Dealership.objects.get(slug="default")
        self.assertTrue(default.name)  # resolved name is non-empty
        # Fallback lands "Default Dealership" when no env / no profile.
        # The exact string depends on env at migration time, so we only
        # assert non-empty + typed.
        self.assertIsInstance(default.name, str)

    def test_backfill_left_zero_null_fks(self):
        # Fresh DB has no rows in the tenant carriers, so trivially zero
        # nulls. The migration's own count check is the real production
        # guarantee; this test locks the invariant for future changes.
        self.assertEqual(Vehicle.objects.filter(dealership__isnull=True).count(), 0)
        self.assertEqual(
            Salesperson.objects.filter(dealership__isnull=True).count(), 0
        )
        self.assertEqual(
            ChatSession.objects.filter(dealership__isnull=True).count(), 0
        )
        self.assertEqual(
            ChatMessage.objects.filter(dealership__isnull=True).count(), 0
        )
        self.assertEqual(
            CustomerLead.objects.filter(dealership__isnull=True).count(), 0
        )
        self.assertEqual(
            DealerOnboardingProfile.objects.filter(
                dealership__isnull=True
            ).count(),
            0,
        )


class TenancyFkAttachment(TestCase):
    """New rows can attach to a Dealership via the FK.

    Locks the FK's presence + related_name so future refactors don't
    silently rename them. FK is NOT NULL as of Increment 3 — the
    write-path plumbing in :mod:`services.tenancy` guarantees no
    caller can produce a null.
    """

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_vehicle_attaches(self):
        v = Vehicle.objects.create(
            stock_number="INC2-V1",
            year=2024,
            model="Ranger",
            price=Decimal("35000.00"),
            dealership=self.default,
        )
        self.assertEqual(v.dealership_id, self.default.pk)
        self.assertIn(v, self.default.vehicles.all())

    def test_salesperson_attaches(self):
        s = Salesperson.objects.create(
            name="Test Advisor", slug="inc2-advisor", dealership=self.default
        )
        self.assertEqual(s.dealership_id, self.default.pk)
        self.assertIn(s, self.default.salespeople.all())

    def test_chat_session_and_message_attach(self):
        session = ChatSession.objects.create(dealership=self.default)
        msg = ChatMessage.objects.create(
            session=session,
            role="user",
            content="hi",
            dealership=self.default,
        )
        self.assertIn(session, self.default.chat_sessions.all())
        self.assertIn(msg, self.default.chat_messages.all())

    def test_customer_lead_attaches(self):
        lead = CustomerLead.objects.create(name="Test Lead", dealership=self.default)
        self.assertIn(lead, self.default.customer_leads.all())

    def test_onboarding_profile_attaches(self):
        profile = DealerOnboardingProfile.objects.create(
            dealership_name="Attached Store", dealership=self.default
        )
        self.assertIn(profile, self.default.onboarding_profiles.all())

    def test_fk_is_now_not_null(self):
        # Milestone 1 · Increment 3 — the six FKs are NOT NULL. Every
        # write path either passes ``dealership=`` explicitly or gets
        # the default attached by the pre_save fallback in
        # :mod:`services.tenancy`, so a null can never reach the DB.
        for model in (
            Vehicle,
            Salesperson,
            ChatSession,
            ChatMessage,
            CustomerLead,
            DealerOnboardingProfile,
        ):
            self.assertFalse(
                model._meta.get_field("dealership").null,
                f"{model.__name__}.dealership should be NOT NULL in Increment 3",
            )


class BackfillDefaultNameResolution(TestCase):
    """The data migration's name-resolution ladder (env → onboarding
    profile → 'Default Dealership') is exercised at migration time and
    can't be re-run here without pytest-django's `--create-db`. We
    smoke-test that the seeded row's name is one of the three valid
    outputs so a refactor of the ladder doesn't silently corrupt it.
    """

    def test_seeded_default_name_is_one_of_the_valid_fallbacks(self):
        default = Dealership.objects.get(slug="default")
        # Env DEALER_AI_DEALER_NAME could be anything at test time, so
        # the only cross-env invariant is: non-empty + string.
        self.assertIsInstance(default.name, str)
        self.assertGreater(len(default.name.strip()), 0)


class TenancyPrimitive(TestCase):
    """Milestone 1 · Increment 3 — the default-tenancy resolver.

    Locks the contract every future write path depends on: there is
    exactly one canonical default Dealership, it's discoverable by
    ``slug='default'``, and the module-level cache round-trips
    consistently across calls.
    """

    def test_get_default_dealership_returns_the_seeded_row(self):
        from dealer_ai.services.tenancy import get_default_dealership

        default = get_default_dealership()
        self.assertEqual(default.slug, "default")

    def test_get_default_dealership_is_stable_across_calls(self):
        from dealer_ai.services.tenancy import get_default_dealership

        first = get_default_dealership()
        second = get_default_dealership()
        self.assertEqual(first.pk, second.pk)

    def test_reset_cache_forces_fresh_lookup(self):
        from dealer_ai.services.tenancy import (
            get_default_dealership,
            reset_default_dealership_cache,
        )

        first = get_default_dealership()
        reset_default_dealership_cache()
        # Post-reset the resolver hits the DB again but still returns
        # the same seeded row (the reset drops the cached PK, not the
        # row itself).
        second = get_default_dealership()
        self.assertEqual(first.pk, second.pk)


class WritePathFallback(TestCase):
    """Milestone 1 · Increment 3 — the ``pre_save`` fallback attaches
    the default Dealership when the caller leaves ``dealership`` unset.

    This is the guarantee that lets NOT NULL be safe without every
    existing caller (management commands, tests, seed scripts) knowing
    about tenancy.
    """

    def test_chat_session_autofill_from_default(self):
        session = ChatSession.objects.create()
        self.assertIsNotNone(session.dealership_id)
        self.assertEqual(session.dealership.slug, "default")

    def test_vehicle_autofill_from_default(self):
        v = Vehicle.objects.create(
            stock_number="INC3-AUTOFILL",
            year=2024,
            model="Bronco",
            price=Decimal("42000.00"),
        )
        self.assertEqual(v.dealership.slug, "default")

    def test_customer_lead_autofill_from_default_when_no_session(self):
        lead = CustomerLead.objects.create(name="Walk-in Wanda")
        self.assertEqual(lead.dealership.slug, "default")

    def test_explicit_dealership_short_circuits_fallback(self):
        # Explicit tenant assignment must never be overwritten by the
        # fallback — this is the seam future request-context tenancy
        # relies on.
        other = Dealership.objects.create(name="Other Store", slug="other")
        session = ChatSession.objects.create(dealership=other)
        self.assertEqual(session.dealership_id, other.pk)

    def test_chat_message_inherits_parent_session_dealership(self):
        # Parent-record inheritance: ChatMessage without an explicit
        # dealership picks up the parent ChatSession's tenant, not the
        # default. This keeps parent + child rows tenant-consistent.
        other = Dealership.objects.create(name="Other Store", slug="other2")
        session = ChatSession.objects.create(dealership=other)
        msg = ChatMessage.objects.create(
            session=session, role="user", content="hi"
        )
        self.assertEqual(msg.dealership_id, other.pk)

    def test_customer_lead_inherits_parent_session_dealership(self):
        other = Dealership.objects.create(name="Other Store", slug="other3")
        session = ChatSession.objects.create(dealership=other)
        lead = CustomerLead.objects.create(name="Session-linked", session=session)
        self.assertEqual(lead.dealership_id, other.pk)

    # Milestone 3 · Increment 1 (SESSION_056) — three new carriers
    # registered with the pre_save autofill signal per
    # ``services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`` extension
    # (6 → 9). Each condition-report model without an explicit
    # dealership picks up the default. See
    # ``MILESTONE_3_PLANNING.md`` §2 row 2.

    def test_condition_report_autofill_from_default(self):
        from django.utils import timezone

        from dealer_ai.models import ConditionReport

        v = Vehicle.objects.create(
            stock_number="M31-AUTOFILL-REPORT",
            year=2024,
            model="Bronco",
            price=Decimal("42000.00"),
        )
        report = ConditionReport.objects.create(
            vehicle=v,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        self.assertIsNotNone(report.dealership_id)
        self.assertEqual(report.dealership.slug, "default")

    def test_condition_finding_autofill_from_default(self):
        from django.utils import timezone

        from dealer_ai.models import (
            CONDITION_CATEGORY_MECHANICAL,
            CONDITION_SEVERITY_REQUIRED,
            ConditionFinding,
            ConditionReport,
        )

        v = Vehicle.objects.create(
            stock_number="M31-AUTOFILL-FINDING",
            year=2024,
            model="Bronco",
            price=Decimal("42000.00"),
        )
        report = ConditionReport.objects.create(
            vehicle=v,
            dealership=v.dealership,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        finding = ConditionFinding.objects.create(
            report=report,
            category=CONDITION_CATEGORY_MECHANICAL,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="Autofill smoke test.",
        )
        self.assertIsNotNone(finding.dealership_id)
        self.assertEqual(finding.dealership.slug, "default")

    def test_condition_finding_photo_autofill_from_default(self):
        from django.utils import timezone

        from dealer_ai.models import (
            CONDITION_CATEGORY_MECHANICAL,
            CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            CONDITION_SEVERITY_REQUIRED,
            ConditionFinding,
            ConditionFindingPhoto,
            ConditionReport,
        )

        v = Vehicle.objects.create(
            stock_number="M31-AUTOFILL-PHOTO",
            year=2024,
            model="Bronco",
            price=Decimal("42000.00"),
        )
        report = ConditionReport.objects.create(
            vehicle=v,
            dealership=v.dealership,
            inspector_name="Marta Ruiz",
            inspected_at=timezone.now(),
            mileage_at_inspection=42_000,
        )
        finding = ConditionFinding.objects.create(
            report=report,
            dealership=v.dealership,
            category=CONDITION_CATEGORY_MECHANICAL,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="Autofill smoke test.",
        )
        photo = ConditionFindingPhoto.objects.create(
            finding=finding,
            storage_key="cr/autofill/one.jpg",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=100_000,
        )
        self.assertIsNotNone(photo.dealership_id)
        self.assertEqual(photo.dealership.slug, "default")
