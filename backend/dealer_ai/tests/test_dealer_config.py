"""SESSION_030 pivot: DealerProfile resolver contract.

Locks the resolution rules that every prompt template + payment engine
caller depends on. The Copper Canyon Auto independent-dealer defaults
(from :mod:`dealer_ai.services.dealer_config`) are the shape-of-business
that the kit ships with post-pivot; overrides come from env, then the
persisted :class:`DealerOnboardingProfile` (name only, until Phase 3
extends the model).
"""

from __future__ import annotations

from django.test import TestCase, override_settings

from dealer_ai.models import DealerOnboardingProfile
from dealer_ai.services.dealer_config import (
    DealerProfile,
    get_dealer_name,
    get_dealer_profile,
)


class GetDealerNameResolution(TestCase):
    def test_defaults_to_sentence_safe_fallback(self):
        DealerOnboardingProfile.objects.all().delete()
        self.assertEqual(get_dealer_name(), "the dealership")

    @override_settings(DEALER_AI_DEALER_NAME="Copper Canyon Auto")
    def test_env_override_wins(self):
        DealerOnboardingProfile.objects.create(dealership_name="Ignored Store")
        self.assertEqual(get_dealer_name(), "Copper Canyon Auto")

    def test_onboarding_profile_used_when_no_env(self):
        DealerOnboardingProfile.objects.create(dealership_name="Rivertown Motors")
        self.assertEqual(get_dealer_name(), "Rivertown Motors")


class GetDealerProfileResolution(TestCase):
    def setUp(self):
        DealerOnboardingProfile.objects.all().delete()

    def test_defaults_ship_copper_canyon_independent_shape(self):
        profile = get_dealer_profile()

        self.assertIsInstance(profile, DealerProfile)
        # Name intentionally stays sentence-safe until operator configures.
        self.assertEqual(profile.name, "the dealership")
        self.assertEqual(profile.dealer_type, "independent")
        self.assertTrue(profile.bhph_enabled)
        self.assertEqual(profile.floor_plan_lender, "NextGear")
        self.assertIn("powertrain", profile.warranty_offering)
        self.assertGreaterEqual(len(profile.subprime_lenders), 3)
        # Mixed-make used lot — no single OEM makes up the whole list.
        self.assertIn("Toyota", profile.makes_carried)
        self.assertIn("Honda", profile.makes_carried)

    def test_profile_is_frozen(self):
        profile = get_dealer_profile()
        with self.assertRaises(Exception):
            profile.name = "Mutated Motors"  # type: ignore[misc]

    @override_settings(DEALER_AI_DEALER_NAME="Copper Canyon Auto")
    def test_env_name_flows_into_profile(self):
        self.assertEqual(get_dealer_profile().name, "Copper Canyon Auto")

    @override_settings(DEALER_AI_DEALER_TYPE="franchise")
    def test_env_dealer_type_override(self):
        self.assertEqual(get_dealer_profile().dealer_type, "franchise")

    @override_settings(DEALER_AI_DEALER_TYPE="  INDEPENDENT  ")
    def test_dealer_type_env_is_lowercased_and_stripped(self):
        self.assertEqual(get_dealer_profile().dealer_type, "independent")

    @override_settings(DEALER_AI_DEALER_TYPE="nonsense")
    def test_invalid_dealer_type_env_falls_back_to_default(self):
        self.assertEqual(get_dealer_profile().dealer_type, "independent")
