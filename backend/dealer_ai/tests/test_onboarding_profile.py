"""SESSION_008: dealer onboarding profile persistence (singleton, one-store).

Endpoint: ``GET|PUT|PATCH /api/dealer-ai/onboarding/profile/``.
Behavior: GET returns the current row or the default shape if none exists.
PUT/PATCH upserts the singleton row.
"""

from __future__ import annotations

import json
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from dealer_ai.models import DealerOnboardingProfile
from dealer_ai.serializers import ONBOARDING_DEFAULTS


URL = reverse("dealer_ai:onboarding-profile")
LOGO_UPLOAD_URL = reverse("dealer_ai:onboarding-logo-upload")


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


class OnboardingLogoUrlTests(TestCase):
    """SESSION_021 — `logo_url` is the per-dealer logo override.

    Empty string default keeps the kit's static fallback in play
    (consumers resolve `profile.logo_url || DEFAULT_DEALER.logoPath`).
    Saving a hosted URL persists it; clearing it back to "" returns
    to fallback behavior.
    """

    LOGO = "https://cdn.example.com/dealer-logo.svg"

    def test_default_logo_url_is_empty_string(self):
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertIn("logo_url", res.json())
        self.assertEqual(res.json()["logo_url"], "")

    def test_put_saves_logo_url(self):
        body = {**ONBOARDING_DEFAULTS, "logo_url": self.LOGO}
        res = self.client.put(URL, data=json.dumps(body), content_type="application/json")
        self.assertEqual(res.status_code, 200, res.content)
        profile = DealerOnboardingProfile.objects.get()
        self.assertEqual(profile.logo_url, self.LOGO)

    def test_get_after_save_returns_logo_url(self):
        body = {**ONBOARDING_DEFAULTS, "logo_url": self.LOGO}
        self.client.put(URL, data=json.dumps(body), content_type="application/json")
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["logo_url"], self.LOGO)

    def test_clearing_logo_url_persists_empty(self):
        # Save a URL, then save back the empty default — confirms the
        # frontend "clear the field to revert to fallback" path works
        # at the API boundary.
        self.client.put(
            URL,
            data=json.dumps({**ONBOARDING_DEFAULTS, "logo_url": self.LOGO}),
            content_type="application/json",
        )
        self.client.put(
            URL,
            data=json.dumps({**ONBOARDING_DEFAULTS, "logo_url": ""}),
            content_type="application/json",
        )
        profile = DealerOnboardingProfile.objects.get()
        self.assertEqual(profile.logo_url, "")


class OnboardingLogoUploadTests(TestCase):
    def test_upload_logo_creates_profile_and_sets_logo_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
                upload = SimpleUploadedFile(
                    "dealer-logo.png",
                    b"\x89PNG\r\n\x1a\n",
                    content_type="image/png",
                )
                res = self.client.post(LOGO_UPLOAD_URL, {"logo": upload})

        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertIn("/media/dealer-logos/", data["logo_url"])
        self.assertTrue(data["logo_url"].endswith(".png"))
        profile = DealerOnboardingProfile.objects.get()
        self.assertEqual(profile.logo_url, data["logo_url"])

    def test_upload_rejects_non_image_file(self):
        upload = SimpleUploadedFile(
            "dealer-logo.txt",
            b"not an image",
            content_type="text/plain",
        )
        res = self.client.post(LOGO_UPLOAD_URL, {"logo": upload})

        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn("Unsupported logo type", res.json()["detail"])


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


class OnboardingIndieFieldsTests(TestCase):
    """SESSION_032 — the eight indie shape-of-business fields
    (dealer_type, bhph_enabled, bhph_configured, subprime_lenders,
    floor_plan_lender, warranty_offering, credit_range_served,
    makes_carried) are accepted by the serializer, round-trip through
    GET, and use safe defaults when omitted."""

    def test_defaults_returned_when_no_profile(self):
        DealerOnboardingProfile.objects.all().delete()
        r = self.client.get(URL)
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertEqual(data["dealer_type"], "")
        self.assertTrue(data["bhph_enabled"])  # matches Copper Canyon default
        self.assertFalse(data["bhph_configured"])
        self.assertEqual(data["subprime_lenders"], "")
        self.assertEqual(data["floor_plan_lender"], "")
        self.assertEqual(data["warranty_offering"], "")
        self.assertEqual(data["credit_range_served"], "")
        self.assertEqual(data["makes_carried"], "")

    def test_put_saves_indie_fields(self):
        body = {
            **ONBOARDING_DEFAULTS,
            "dealer_type": "independent",
            "bhph_enabled": False,
            "bhph_configured": True,
            "subprime_lenders": "Sonoran Credit\nDesert Auto Finance",
            "floor_plan_lender": "NextGear",
            "warranty_offering": "30-day / 1000-mile powertrain",
            "credit_range_served": "580+ with strong down; BHPH below",
            "makes_carried": "Toyota\nHonda\nFord",
        }
        save = self.client.put(URL, data=json.dumps(body), content_type="application/json")
        self.assertEqual(save.status_code, 200, save.content)

        row = DealerOnboardingProfile.objects.get()
        self.assertEqual(row.dealer_type, "independent")
        self.assertFalse(row.bhph_enabled)
        self.assertTrue(row.bhph_configured)
        self.assertIn("Sonoran", row.subprime_lenders)
        self.assertEqual(row.floor_plan_lender, "NextGear")
        self.assertIn("Toyota", row.makes_carried)

    def test_indie_fields_round_trip_through_get(self):
        body = {
            **ONBOARDING_DEFAULTS,
            "dealer_type": "franchise",
            "bhph_enabled": True,
            "bhph_configured": True,
            "makes_carried": "Ford\nLincoln",
        }
        self.client.put(URL, data=json.dumps(body), content_type="application/json")

        r = self.client.get(URL)
        data = r.json()
        self.assertEqual(data["dealer_type"], "franchise")
        self.assertTrue(data["bhph_enabled"])
        self.assertTrue(data["bhph_configured"])
        self.assertEqual(data["makes_carried"], "Ford\nLincoln")

    def test_invalid_dealer_type_rejected(self):
        body = {**ONBOARDING_DEFAULTS, "dealer_type": "nonsense"}
        r = self.client.put(URL, data=json.dumps(body), content_type="application/json")
        # Django REST framework's ChoiceField returns 400 for values
        # outside the choices list.
        self.assertEqual(r.status_code, 400, r.content)
