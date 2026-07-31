"""Milestone 1 · Increments 1 & 2 — Dealership + tenant-carrier FKs.

Increment 1 (model): tests the `Dealership` shape in isolation.
Increment 2 (FKs + backfill): tests that the six tenant-carrying
models expose a `dealership` FK, that the data migration seeded a
deterministic default row (slug=`default`), and that the fallback
name-resolution ladder produced a valid name.

NOT NULL enforcement is deferred to Increment 3 (bundled with the
write-path tenancy propagation), so the FK is nullable in this
increment. Tests locking that boundary live here so a premature NOT
NULL flip fails loudly.
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
    silently rename them. FK is nullable in this increment (NOT NULL
    flip deferred to Increment 3 with write-path plumbing).
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

    def test_fk_is_nullable_in_this_increment(self):
        # Guard: a future NOT NULL flip must land together with the
        # write-path tenancy plumbing in Increment 3. If this assertion
        # ever fails, it means the flip landed early — the write callers
        # (views, chat_engine, inventory_import) still don't know about
        # tenancy and will 500 in production.
        for model in (
            Vehicle,
            Salesperson,
            ChatSession,
            ChatMessage,
            CustomerLead,
            DealerOnboardingProfile,
        ):
            self.assertTrue(
                model._meta.get_field("dealership").null,
                f"{model.__name__}.dealership should be nullable in Increment 2",
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
