"""Milestone 18 · Increment 4 (SESSION_150) — BHPH archetype tests.

Covers per MILESTONE_18_PLANNING.md §7 M18.4:

- Row-count contract per specs (~25 vehicles + 4 salespeople + ~10
  leads + 5 recent sales + ~30 notes + ~150 payments + 3 promises
  + 5 contacts + 1 repossession).
- Cross-domain integrity: every BhphNote origins from a BHPH Sale;
  promise-to-pay state consistency; repossession references a
  BhphNote in the same tenant.
- **M16 detector eligibility**: recent unposted payments have
  ``posted_at=None`` (M16.1 filter); historical payments have
  ``posted_at`` populated.
- M15 sync-sibling GL post fires on the 5 recent BHPH sales.
- Reset restores canonical state.
- ScenarioSummary contract populated.
- Synthetic-only data safety (DEMOBH VINs, NANP phones, .example
  emails).
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import (
    BHPH_PROMISE_STATE_BROKEN,
    BHPH_PROMISE_STATE_KEPT,
    BHPH_PROMISE_STATE_PROMISED,
    BHPH_REPO_STATE_RECOVERED,
    DEMO_ARCHETYPE_BHPH,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    BhphPayment,
    BhphPromiseToPay,
    CollectionContact,
    CustomerLead,
    FollowUpCadence,
    JournalEntry,
    Repossession,
    Sale,
    Salesperson,
    Vehicle,
    VehicleAcquisition,
)
from dealer_ai.services.demo_store import (
    ScenarioSummary,
    create_demo_store,
    reset_demo_store,
)
from dealer_ai.services.demo_store.archetypes.bhph import (
    _COLLECTION_CONTACTS,
    _FOLLOW_UP_LEADS,
    _HISTORICAL_NOTE_SPECS,
    _INVENTORY,
    _LEADS,
    _PROMISES,
    _RECENT_SALES,
    _STAFF,
    BhphArchetypeBuilder,
)


class _BuildTestMixin(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.dealership, cls.summary = create_demo_store(
            slug="m184-bhph-fixture",
            archetype=DEMO_ARCHETYPE_BHPH,
            name="M18.4 BHPH Fixture",
        )


# ---------------------------------------------------------------------------
# Row-count contract
# ---------------------------------------------------------------------------


class BhphRowCountsTests(_BuildTestMixin):
    def test_vehicles_include_historical_extras(self) -> None:
        # 25 inventory + 5 additional historical vehicles.
        self.assertEqual(
            Vehicle.objects.filter(dealership=self.dealership).count(),
            len(_INVENTORY) + 5,
        )

    def test_acquisitions_match_inventory_only(self) -> None:
        # The 25 inventory vehicles get VehicleAcquisition; the 5
        # historical extras skip the acquisition record.
        self.assertEqual(
            VehicleAcquisition.objects.filter(
                dealership=self.dealership
            ).count(),
            len(_INVENTORY),
        )

    def test_salespeople_match_staff(self) -> None:
        self.assertEqual(
            Salesperson.objects.filter(
                dealership=self.dealership
            ).count(),
            len(_STAFF),
        )

    def test_notes_at_least_thirty(self) -> None:
        # 5 recent-sale notes + 25 historical notes = 30.
        self.assertEqual(
            BhphNote.objects.filter(
                dealership=self.dealership
            ).count(),
            len(_RECENT_SALES) + len(_HISTORICAL_NOTE_SPECS),
        )

    def test_payment_rows_at_least_one_hundred(self) -> None:
        # ~150 planned; assert generously to allow builder-driven
        # variance without brittle equality.
        count = BhphPayment.objects.filter(
            dealership=self.dealership
        ).count()
        self.assertGreaterEqual(count, 100)

    def test_promises_match_spec(self) -> None:
        self.assertEqual(
            BhphPromiseToPay.objects.filter(
                dealership=self.dealership
            ).count(),
            len(_PROMISES),
        )

    def test_collection_contacts_match_spec(self) -> None:
        self.assertEqual(
            CollectionContact.objects.filter(
                dealership=self.dealership
            ).count(),
            len(_COLLECTION_CONTACTS),
        )

    def test_repossession_present_and_recovered(self) -> None:
        repos = Repossession.objects.filter(
            dealership=self.dealership
        )
        self.assertEqual(repos.count(), 1)
        self.assertEqual(repos.first().state, BHPH_REPO_STATE_RECOVERED)

    def test_follow_up_cadences_present(self) -> None:
        self.assertEqual(
            FollowUpCadence.objects.filter(
                dealership=self.dealership
            ).count(),
            len(_FOLLOW_UP_LEADS),
        )


# ---------------------------------------------------------------------------
# M16 detector eligibility — the key architectural anchor
# ---------------------------------------------------------------------------


class BhphM16DetectorEligibilityTests(_BuildTestMixin):
    def test_at_least_five_payments_have_posted_at_null(self) -> None:
        # The M16.1 detector filters posted_at__isnull=True per §5.d
        # Option A. The archetype seeds ~5 recent unposted payments
        # so the 11:00 detector cycle will post them into the GL
        # after tester login.
        unposted = BhphPayment.objects.filter(
            dealership=self.dealership,
            posted_at__isnull=True,
        )
        self.assertGreaterEqual(unposted.count(), 5)

    def test_unposted_payments_are_recent(self) -> None:
        # Unposted payments should be within the last day so the
        # timing narrative is coherent (posted overnight by the
        # detector after tester login).
        from django.utils import timezone
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(days=2)
        unposted = BhphPayment.objects.filter(
            dealership=self.dealership,
            posted_at__isnull=True,
        )
        for payment in unposted:
            self.assertGreater(payment.paid_at, cutoff)

    def test_historical_payments_have_posted_at_populated(self) -> None:
        # Historical payments (paid_at > 2 days ago) should all
        # have posted_at set — they've already been through the
        # detector.
        from django.utils import timezone
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(days=3)
        historical = BhphPayment.objects.filter(
            dealership=self.dealership,
            paid_at__lt=cutoff,
        )
        self.assertGreaterEqual(historical.count(), 90)
        for payment in historical:
            self.assertIsNotNone(payment.posted_at)


# ---------------------------------------------------------------------------
# Cross-domain integrity
# ---------------------------------------------------------------------------


class BhphCrossDomainTests(_BuildTestMixin):
    def test_every_note_origins_from_a_bhph_sale(self) -> None:
        for note in BhphNote.objects.filter(
            dealership=self.dealership
        ):
            self.assertEqual(
                note.sale.finance_type, SALE_FINANCE_TYPE_BHPH
            )
            self.assertEqual(
                note.sale.dealership_id, self.dealership.pk
            )

    def test_promise_states_include_all_three_terminal_variants(
        self,
    ) -> None:
        # The spec includes 1 promised + 1 kept + 1 broken so the
        # collector scenario brief can walk each state.
        states = set(
            BhphPromiseToPay.objects.filter(
                dealership=self.dealership
            ).values_list("state", flat=True)
        )
        self.assertIn(BHPH_PROMISE_STATE_PROMISED, states)
        self.assertIn(BHPH_PROMISE_STATE_KEPT, states)
        self.assertIn(BHPH_PROMISE_STATE_BROKEN, states)

    def test_kept_promise_links_a_payment(self) -> None:
        kept = BhphPromiseToPay.objects.filter(
            dealership=self.dealership, state=BHPH_PROMISE_STATE_KEPT
        ).first()
        self.assertIsNotNone(kept)
        assert kept is not None
        self.assertIsNotNone(kept.actual_payment_id)

    def test_repossession_note_in_same_tenant(self) -> None:
        repo = Repossession.objects.get(dealership=self.dealership)
        self.assertEqual(repo.note.dealership_id, self.dealership.pk)

    def test_every_salesperson_has_user_linkage(self) -> None:
        for sp in Salesperson.objects.filter(
            dealership=self.dealership
        ):
            self.assertIsNotNone(sp.user_id)


# ---------------------------------------------------------------------------
# M15 sync-sibling GL post — fires on the 5 recent BHPH sales
# ---------------------------------------------------------------------------


class BhphGLPostingTests(_BuildTestMixin):
    def test_recent_sales_produced_journal_entries(self) -> None:
        # Each of the 5 recent BHPH Sales fires the M15.1 sync-
        # sibling GL post via record_sale. The 25 historical Sales
        # bypass record_sale (direct-create for scenario-authored
        # reasons documented in the archetype) so they do NOT fire.
        entries = JournalEntry.objects.filter(
            dealership=self.dealership,
            description__startswith="M9 sale booking",
        )
        self.assertGreaterEqual(entries.count(), len(_RECENT_SALES))

    def test_each_recent_sale_stock_referenced_in_a_journal_entry(
        self,
    ) -> None:
        descriptions = list(
            JournalEntry.objects.filter(
                dealership=self.dealership,
                description__startswith="M9 sale booking",
            ).values_list("description", flat=True)
        )
        for spec in _RECENT_SALES:
            stock = str(spec["stock"])
            self.assertTrue(
                any(stock in d for d in descriptions),
                f"No M9 sale-booking entry mentions {stock}",
            )


# ---------------------------------------------------------------------------
# ScenarioSummary shape
# ---------------------------------------------------------------------------


class BhphScenarioSummaryTests(_BuildTestMixin):
    def test_summary_type_and_archetype(self) -> None:
        self.assertIsInstance(self.summary, ScenarioSummary)
        self.assertEqual(
            self.summary.archetype, DEMO_ARCHETYPE_BHPH
        )

    def test_summary_names_all_inventory_stock_numbers(self) -> None:
        expected = {str(spec["stock"]) for spec in _INVENTORY}
        seeded = set(self.summary.seeded_stock_numbers)
        # Every inventory stock appears (may plus historical
        # extras; the summary only names the primary inventory).
        self.assertTrue(expected.issubset(seeded))

    def test_summary_names_user_usernames(self) -> None:
        self.assertEqual(
            len(self.summary.seeded_user_usernames), len(_STAFF)
        )

    def test_summary_names_collector_scenario_slug(self) -> None:
        self.assertIn(
            "bhph_collector_daily_book",
            self.summary.seeded_scenario_slugs,
        )

    def test_summary_names_repo_scenario_slug(self) -> None:
        self.assertIn(
            "repo_intake_handoff",
            self.summary.seeded_scenario_slugs,
        )


# ---------------------------------------------------------------------------
# Synthetic-only data safety
# ---------------------------------------------------------------------------


class BhphSyntheticDataTests(_BuildTestMixin):
    def test_every_vin_prefixed_demobh(self) -> None:
        for vehicle in Vehicle.objects.filter(
            dealership=self.dealership
        ):
            self.assertTrue(
                vehicle.vin.startswith("DEMOBH"),
                f"Vehicle {vehicle.stock_number} VIN not synthetic",
            )

    def test_every_lead_email_uses_example_tld(self) -> None:
        for lead in CustomerLead.objects.filter(
            dealership=self.dealership
        ):
            self.assertTrue(
                lead.email.endswith("@demo.dealer-ai.example")
            )

    def test_every_lead_phone_uses_nanp_fiction_block(self) -> None:
        for lead in CustomerLead.objects.filter(
            dealership=self.dealership
        ):
            self.assertTrue(lead.phone.startswith("555-01"))

    def test_every_seeded_user_email_uses_example_tld(self) -> None:
        for sp in Salesperson.objects.filter(
            dealership=self.dealership
        ):
            self.assertTrue(
                sp.user.email.endswith("@demo.dealer-ai.example")
            )


# ---------------------------------------------------------------------------
# Reset — canonical state
# ---------------------------------------------------------------------------


class BhphResetTests(TestCase):
    def test_reset_restores_canonical_row_counts(self) -> None:
        dealership, _ = create_demo_store(
            slug="m184-reset-check",
            archetype=DEMO_ARCHETYPE_BHPH,
        )
        note_count = BhphNote.objects.filter(
            dealership=dealership
        ).count()
        payment_count = BhphPayment.objects.filter(
            dealership=dealership
        ).count()
        reset_demo_store(dealership=dealership)
        self.assertEqual(
            BhphNote.objects.filter(
                dealership=dealership
            ).count(),
            note_count,
        )
        self.assertEqual(
            BhphPayment.objects.filter(
                dealership=dealership
            ).count(),
            payment_count,
        )

    def test_reset_preserves_repossession_state(self) -> None:
        dealership, _ = create_demo_store(
            slug="m184-reset-repo",
            archetype=DEMO_ARCHETYPE_BHPH,
        )
        reset_demo_store(dealership=dealership)
        repo = Repossession.objects.get(dealership=dealership)
        self.assertEqual(repo.state, BHPH_REPO_STATE_RECOVERED)


# ---------------------------------------------------------------------------
# Direct-instantiation smoke
# ---------------------------------------------------------------------------


class BhphBuilderDirectTests(TestCase):
    def test_builder_archetype_attr(self) -> None:
        self.assertEqual(
            BhphArchetypeBuilder.archetype, DEMO_ARCHETYPE_BHPH
        )
