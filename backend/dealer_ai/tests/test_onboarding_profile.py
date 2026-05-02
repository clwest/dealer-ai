"""SESSION_008: dealer onboarding profile persistence (singleton, one-store).

Endpoint: ``GET|PUT|PATCH /api/dealer-ai/onboarding/profile/``.
Behavior: GET returns the current row or the default shape if none exists.
PUT/PATCH upserts the singleton row.
"""

from __future__ import annotations

import json

from django.test import TestCase
from django.urls import reverse

from dealer_ai.models import DealerOnboardingProfile
from dealer_ai.serializers import ONBOARDING_DEFAULTS


URL = reverse("dealer_ai:onboarding-profile")


class OnboardingDefaultsTests(TestCase):
    """GET when no row exists returns the default shape."""

    def test_get_returns_defaults_when_no_profile(self):
        self.assertEqual(DealerOnboardingProfile.objects.count(), 0)
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        # Default row is *not* created by GET.
        self.assertEqual(DealerOnboardingProfile.objects.count(), 0)
        # Every default key is present in the response.
        for key, expected in ONBOARDING_DEFAULTS.items():
            self.assertIn(key, data)
            self.assertEqual(data[key], expected, f"default mismatch for {key}")

    def test_default_payment_disclaimer_text(self):
        """Frontend depends on this seed copy when the page loads cold."""
        res = self.client.get(URL)
        self.assertIn("approved credit", res.json()["payment_disclaimer"].lower())


class OnboardingDealershipFieldsTests(TestCase):
    def test_put_saves_dealership_fields(self):
        body = {
            **ONBOARDING_DEFAULTS,
            "dealership_name": "Freedom Ford Tulsa",
            "store_location": "Tulsa, OK",
            "main_brands": "Ford + multi-brand used",
            "sales_phone": "(918) 555-0100",
            "website": "https://freedomford.example.com",
        }
        res = self.client.put(URL, data=json.dumps(body), content_type="application/json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(DealerOnboardingProfile.objects.count(), 1)
        profile = DealerOnboardingProfile.objects.get()
        self.assertEqual(profile.dealership_name, "Freedom Ford Tulsa")
        self.assertEqual(profile.store_location, "Tulsa, OK")
        self.assertEqual(profile.main_brands, "Ford + multi-brand used")
        self.assertEqual(profile.sales_phone, "(918) 555-0100")
        self.assertEqual(profile.website, "https://freedomford.example.com")


class OnboardingManagerFieldsTests(TestCase):
    def test_put_saves_manager_preferences(self):
        body = {
            **ONBOARDING_DEFAULTS,
            "sales_tone": "Warm + consultative",
            "pricing_comfort": "Negotiable — sales has discretion",
            "appointment_preference": "Book online preferred",
            "lead_handoff_style": "Round-robin by team",
        }
        res = self.client.put(URL, data=json.dumps(body), content_type="application/json")
        self.assertEqual(res.status_code, 200, res.content)
        profile = DealerOnboardingProfile.objects.get()
        self.assertEqual(profile.sales_tone, "Warm + consultative")
        self.assertEqual(profile.pricing_comfort, "Negotiable — sales has discretion")
        self.assertEqual(profile.appointment_preference, "Book online preferred")
        self.assertEqual(profile.lead_handoff_style, "Round-robin by team")


class OnboardingSalespersonSeedTests(TestCase):
    def test_put_saves_salesperson_seed(self):
        body = {
            **ONBOARDING_DEFAULTS,
            "salesperson_name": "Sarah Lin",
            "salesperson_role": "Senior Sales Advisor",
            "salesperson_phone": "(918) 555-0123",
            "salesperson_email": "sarah@freedomford.example.com",
            "salesperson_specialties": "Trucks, first-time buyers",
            "salesperson_preferred_tone": "Match store default",
            "salesperson_intro": "Hi, I'm Sarah — 12 years helping families pick the right Ford.",
        }
        res = self.client.put(URL, data=json.dumps(body), content_type="application/json")
        self.assertEqual(res.status_code, 200, res.content)
        profile = DealerOnboardingProfile.objects.get()
        self.assertEqual(profile.salesperson_name, "Sarah Lin")
        self.assertEqual(profile.salesperson_role, "Senior Sales Advisor")
        self.assertEqual(profile.salesperson_phone, "(918) 555-0123")
        self.assertEqual(profile.salesperson_email, "sarah@freedomford.example.com")
        self.assertEqual(profile.salesperson_specialties, "Trucks, first-time buyers")
        self.assertEqual(profile.salesperson_preferred_tone, "Match store default")
        self.assertIn("12 years", profile.salesperson_intro)


class OnboardingAssistantBehaviorTests(TestCase):
    def test_put_saves_assistant_behavior(self):
        body = {
            **ONBOARDING_DEFAULTS,
            "dealership_greeting": "Welcome to Freedom Ford. Tell me what you're shopping for.",
            "approved_phrases": "Want me to set up a closer look?\nWith approved credit",
            "banned_phrases": "guaranteed approval\nbest price ever",
            "escalation_rule": "When a customer asks about specific financing terms, hand off to next available.",
            "payment_disclaimer": "Payments shown are estimates. Final terms with approved credit (W.A.C.).",
        }
        res = self.client.put(URL, data=json.dumps(body), content_type="application/json")
        self.assertEqual(res.status_code, 200, res.content)
        profile = DealerOnboardingProfile.objects.get()
        self.assertIn("Welcome to Freedom Ford", profile.dealership_greeting)
        self.assertIn("closer look", profile.approved_phrases)
        self.assertIn("guaranteed approval", profile.banned_phrases)
        self.assertIn("hand off", profile.escalation_rule)
        self.assertIn("W.A.C.", profile.payment_disclaimer)


class OnboardingChecklistTests(TestCase):
    def test_put_saves_all_checklist_booleans(self):
        body = {
            **ONBOARDING_DEFAULTS,
            "inventory_connected": True,
            "finance_rules_reviewed": True,
            "salespeople_added": True,
            "demo_prompts_tested": True,
            "pilot_approved": True,
        }
        res = self.client.put(URL, data=json.dumps(body), content_type="application/json")
        self.assertEqual(res.status_code, 200, res.content)
        profile = DealerOnboardingProfile.objects.get()
        self.assertTrue(profile.inventory_connected)
        self.assertTrue(profile.finance_rules_reviewed)
        self.assertTrue(profile.salespeople_added)
        self.assertTrue(profile.demo_prompts_tested)
        self.assertTrue(profile.pilot_approved)

    def test_patch_partial_checklist_toggle(self):
        # Seed with all-false defaults via initial PUT.
        self.client.put(URL, data=json.dumps(ONBOARDING_DEFAULTS), content_type="application/json")
        # Toggle only one item via PATCH; the others must remain unchanged.
        res = self.client.patch(
            URL,
            data=json.dumps({"inventory_connected": True}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        profile = DealerOnboardingProfile.objects.get()
        self.assertTrue(profile.inventory_connected)
        # Untouched booleans stay False.
        self.assertFalse(profile.finance_rules_reviewed)
        self.assertFalse(profile.salespeople_added)
        self.assertFalse(profile.demo_prompts_tested)
        self.assertFalse(profile.pilot_approved)


class OnboardingRoundTripTests(TestCase):
    """Save then GET-back returns persisted values; multiple PUTs upsert
    the same singleton row instead of creating new rows."""

    def test_get_after_save_returns_persisted_values(self):
        body = {
            **ONBOARDING_DEFAULTS,
            "dealership_name": "Freedom Ford Tulsa",
            "store_location": "Tulsa, OK",
            "sales_tone": "Direct + fast-paced",
            "salesperson_name": "Sarah Lin",
            "dealership_greeting": "Hi, what brings you in today?",
            "inventory_connected": True,
            "pilot_approved": True,
        }
        save = self.client.put(URL, data=json.dumps(body), content_type="application/json")
        self.assertEqual(save.status_code, 200, save.content)

        load = self.client.get(URL)
        self.assertEqual(load.status_code, 200, load.content)
        data = load.json()
        self.assertEqual(data["dealership_name"], "Freedom Ford Tulsa")
        self.assertEqual(data["store_location"], "Tulsa, OK")
        self.assertEqual(data["sales_tone"], "Direct + fast-paced")
        self.assertEqual(data["salesperson_name"], "Sarah Lin")
        self.assertEqual(data["dealership_greeting"], "Hi, what brings you in today?")
        self.assertTrue(data["inventory_connected"])
        self.assertTrue(data["pilot_approved"])
        # Booleans not set in body keep their default.
        self.assertFalse(data["finance_rules_reviewed"])

    def test_repeat_put_upserts_same_singleton_row(self):
        first = {**ONBOARDING_DEFAULTS, "dealership_name": "First"}
        second = {**ONBOARDING_DEFAULTS, "dealership_name": "Second"}
        self.client.put(URL, data=json.dumps(first), content_type="application/json")
        self.client.put(URL, data=json.dumps(second), content_type="application/json")
        self.assertEqual(DealerOnboardingProfile.objects.count(), 1)
        self.assertEqual(DealerOnboardingProfile.objects.get().dealership_name, "Second")
