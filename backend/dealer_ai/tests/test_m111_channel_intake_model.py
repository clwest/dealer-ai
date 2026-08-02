"""Milestone 11 · Increment 1 (SESSION_114) — CustomerLead channel + referrer model tests.

Locks the schema surface of the M11.1 additive extension per
``MILESTONE_11_PLANNING.md`` §1.1 + §1.6 + §5.a + §5.b Option A
(user-confirmed at SESSION_114 open, recorded in §0.a).

Coverage:

- Channel default is ``chat`` (M11.1 migration backfill mechanism —
  every pre-M11 row landed here because chat was the only intake
  path).
- Channel vocabulary is exactly the fixed 5+1 set.
- Referrer FK nullable + defaults to None; SET_NULL preserves the
  referred row when the referrer is deleted.
- Reverse accessor ``referred_leads`` traverses the self-FK.
"""

from __future__ import annotations

from django.test import TestCase

from dealer_ai.models import (
    LEAD_CHANNEL_CHAT,
    LEAD_CHANNEL_CHOICES,
    LEAD_CHANNEL_LISTING_FORM,
    LEAD_CHANNEL_OTHER,
    LEAD_CHANNEL_PHONE,
    LEAD_CHANNEL_REFERRAL,
    LEAD_CHANNEL_WALK_IN,
    CustomerLead,
    Dealership,
)


class CustomerLeadChannelDefaultTests(TestCase):
    def test_default_channel_is_chat(self) -> None:
        """M1 chat-funnel invariant — every lead created without an
        explicit channel lands as ``chat``, matching the pre-M11
        historical row shape (which the M11.1 migration also
        backfilled to ``chat``)."""
        dealership = Dealership.objects.create(
            slug="d-default-channel", name="D Default"
        )
        lead = CustomerLead.objects.create(dealership=dealership, name="Alice")
        self.assertEqual(lead.channel, LEAD_CHANNEL_CHAT)

    def test_channel_vocabulary_is_exactly_5_plus_1(self) -> None:
        """The fixed 5+1 set per §5.a Option A. Tests use exact
        equality here (not ``>=``) because this vocab is intentionally
        locked — adding a seventh channel is a planning decision, not
        a code-refactor decision."""
        vocab = {key for key, _ in LEAD_CHANNEL_CHOICES}
        self.assertEqual(
            vocab,
            {
                LEAD_CHANNEL_CHAT,
                LEAD_CHANNEL_WALK_IN,
                LEAD_CHANNEL_PHONE,
                LEAD_CHANNEL_LISTING_FORM,
                LEAD_CHANNEL_REFERRAL,
                LEAD_CHANNEL_OTHER,
            },
        )


class CustomerLeadReferrerFKTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="d-ref-fk", name="D Referrer"
        )
        self.referrer = CustomerLead.objects.create(
            dealership=self.dealership, name="Referrer Ray"
        )

    def test_referrer_defaults_to_null(self) -> None:
        lead = CustomerLead.objects.create(
            dealership=self.dealership, name="No-Referrer Nia"
        )
        self.assertIsNone(lead.referrer)

    def test_referrer_link_persists(self) -> None:
        lead = CustomerLead.objects.create(
            dealership=self.dealership,
            name="Referred Ronny",
            channel=LEAD_CHANNEL_REFERRAL,
            referrer=self.referrer,
        )
        lead.refresh_from_db()
        self.assertEqual(lead.referrer_id, self.referrer.id)

    def test_referrer_delete_sets_null_on_referred(self) -> None:
        referred = CustomerLead.objects.create(
            dealership=self.dealership,
            name="Referred Randall",
            channel=LEAD_CHANNEL_REFERRAL,
            referrer=self.referrer,
        )
        self.referrer.delete()
        referred.refresh_from_db()
        self.assertIsNone(referred.referrer)

    def test_referred_leads_reverse_accessor(self) -> None:
        for name in ["Ref Alice", "Ref Bob", "Ref Carol"]:
            CustomerLead.objects.create(
                dealership=self.dealership,
                name=name,
                channel=LEAD_CHANNEL_REFERRAL,
                referrer=self.referrer,
            )
        self.assertEqual(self.referrer.referred_leads.count(), 3)
