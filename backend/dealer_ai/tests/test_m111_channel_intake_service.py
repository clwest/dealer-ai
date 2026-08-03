"""Milestone 11 · Increment 1 (SESSION_114) — channel-intake service verbs.

Locks the :mod:`services.leads.channel_intake` verbs + generic webhook
adapter per ``MILESTONE_11_PLANNING.md`` §1.1 + §1.6 + §5.b Option A.

Coverage:

- ``record_walk_in_lead`` — sets channel + name + tenancy, honors
  optional fields.
- ``record_phone_lead`` — sets channel.
- ``record_referral_lead`` — no referrer_lead_id lands with NULL FK,
  valid same-tenant id links FK, cross-tenant id + nonexistent id
  raise :class:`CrossTenantReferrerError`.
- ``record_webhook_lead`` — generic-platform dispatch normalizes
  envelope + lands with ``channel="listing_form"``; unknown platform
  raises :class:`UnknownWebhookPlatformError`.
- Generic adapter — field-mapping unit test (no DB).
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import (
    LEAD_CHANNEL_LISTING_FORM,
    LEAD_CHANNEL_PHONE,
    LEAD_CHANNEL_REFERRAL,
    LEAD_CHANNEL_WALK_IN,
    CustomerLead,
    Dealership,
)
from dealer_ai.services.leads import (
    CrossTenantReferrerError,
    UnknownWebhookPlatformError,
    record_phone_lead,
    record_referral_lead,
    record_walk_in_lead,
    record_webhook_lead,
)
from dealer_ai.services.leads.webhook_adapters import generic as generic_adapter


class WalkInIntakeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="d-walkin", name="D Walkin"
        )

    def test_walk_in_sets_channel_and_tenancy(self) -> None:
        lead = record_walk_in_lead(
            dealership=self.dealership, name="Wanda Walkup"
        )
        self.assertEqual(lead.channel, LEAD_CHANNEL_WALK_IN)
        self.assertEqual(lead.dealership_id, self.dealership.id)
        self.assertEqual(lead.name, "Wanda Walkup")

    def test_walk_in_honors_optional_fields(self) -> None:
        lead = record_walk_in_lead(
            dealership=self.dealership,
            name="Wilma",
            phone="555-0100",
            email="wilma@example.com",
            notes="Interested in a used truck",
            target_monthly_payment="450.00",
            down_payment=Decimal("3000.00"),
            trade_in="2015 Sonata 110k",
            credit_range="good",
            urgency="this_week",
        )
        self.assertEqual(lead.phone, "555-0100")
        self.assertEqual(lead.email, "wilma@example.com")
        self.assertEqual(lead.target_monthly_payment, Decimal("450.00"))
        self.assertEqual(lead.down_payment, Decimal("3000.00"))
        self.assertEqual(lead.trade_in, "2015 Sonata 110k")
        self.assertEqual(lead.credit_range, "good")
        self.assertEqual(lead.urgency, "this_week")


class PhoneIntakeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="d-phone", name="D Phone"
        )

    def test_phone_sets_channel(self) -> None:
        lead = record_phone_lead(
            dealership=self.dealership,
            name="Pat Phoner",
            phone="555-0199",
        )
        self.assertEqual(lead.channel, LEAD_CHANNEL_PHONE)
        self.assertEqual(lead.phone, "555-0199")


class ReferralIntakeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="d-ref", name="D Referral"
        )
        self.other_dealership = Dealership.objects.create(
            slug="d-ref-other", name="D Ref Other"
        )
        self.referrer = record_walk_in_lead(
            dealership=self.dealership, name="Referrer Ray"
        )

    def test_referral_without_referrer_id_lands_with_null_fk(self) -> None:
        lead = record_referral_lead(
            dealership=self.dealership, name="Referred Ronny"
        )
        self.assertEqual(lead.channel, LEAD_CHANNEL_REFERRAL)
        self.assertIsNone(lead.referrer_id)

    def test_referral_with_valid_referrer_id_links_fk(self) -> None:
        lead = record_referral_lead(
            dealership=self.dealership,
            name="Referred Rachel",
            referrer_lead_id=self.referrer.id,
        )
        self.assertEqual(lead.referrer_id, self.referrer.id)
        self.assertEqual(lead.channel, LEAD_CHANNEL_REFERRAL)

    def test_referral_with_nonexistent_referrer_id_raises(self) -> None:
        with self.assertRaises(CrossTenantReferrerError):
            record_referral_lead(
                dealership=self.dealership,
                name="Referred Ryan",
                referrer_lead_id=999_999,
            )

    def test_referral_with_cross_tenant_referrer_id_raises(self) -> None:
        cross = record_walk_in_lead(
            dealership=self.other_dealership, name="Cross Referrer"
        )
        with self.assertRaises(CrossTenantReferrerError):
            record_referral_lead(
                dealership=self.dealership,
                name="Referred Rita",
                referrer_lead_id=cross.id,
            )
        # And no CustomerLead was written on failure.
        self.assertFalse(
            CustomerLead.objects.filter(name="Referred Rita").exists()
        )


class WebhookIntakeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="d-webhook", name="D Webhook"
        )

    def test_webhook_generic_platform_normalizes_and_lands(self) -> None:
        lead = record_webhook_lead(
            dealership=self.dealership,
            platform="generic",
            payload={
                "full_name": "Wendy Web",
                "phone": "555-0111",
                "email": "wendy@example.com",
                "message": "Interested in the F-150",
                "target_monthly_payment": "500",
                "down_payment": "2000",
                "trade_in": "2016 Camry",
                "credit_range": "good",
            },
        )
        self.assertEqual(lead.channel, LEAD_CHANNEL_LISTING_FORM)
        self.assertEqual(lead.name, "Wendy Web")
        self.assertEqual(lead.phone, "555-0111")
        self.assertEqual(lead.email, "wendy@example.com")
        self.assertEqual(lead.notes, "Interested in the F-150")
        self.assertEqual(lead.target_monthly_payment, Decimal("500"))
        self.assertEqual(lead.down_payment, Decimal("2000"))
        self.assertEqual(lead.trade_in, "2016 Camry")
        # M25.1 — webhook must persist the platform identifier so the
        # operator UI can render "Source: {platform_label}" per
        # MILESTONE_25_PLANNING.md §5.b.
        self.assertEqual(lead.source_metadata, {"platform": "generic"})
        self.assertEqual(lead.get_source_platform(), "generic")

    def test_webhook_unknown_platform_raises(self) -> None:
        with self.assertRaises(UnknownWebhookPlatformError):
            record_webhook_lead(
                dealership=self.dealership,
                platform="autotrader",
                payload={"full_name": "Unknown"},
            )


class GenericAdapterUnitTests(TestCase):
    """Pure-function tests for the generic envelope translator."""

    def test_normalize_maps_documented_keys(self) -> None:
        payload = {
            "full_name": "Alice",
            "phone": "555",
            "email": "a@example.com",
            "message": "hi",
            "target_monthly_payment": "300",
            "down_payment": "1000",
            "trade_in": "civic",
            "credit_range": "good",
            "unknown_field": "ignored",
        }
        out = generic_adapter.normalize(payload)
        self.assertEqual(out["name"], "Alice")
        self.assertEqual(out["notes"], "hi")
        self.assertEqual(out["target_monthly_payment"], "300")
        self.assertNotIn("unknown_field", out)

    def test_normalize_defaults_missing_keys_to_blank(self) -> None:
        out = generic_adapter.normalize({"full_name": "Bare"})
        self.assertEqual(out["name"], "Bare")
        self.assertEqual(out["phone"], "")
        self.assertEqual(out["email"], "")
        self.assertEqual(out["notes"], "")
        self.assertIsNone(out["target_monthly_payment"])
