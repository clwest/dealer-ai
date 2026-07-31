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

    def test_primary_make_defaults_to_none_for_indie(self):
        # Indie mixed-lot has no primary brand.
        self.assertIsNone(get_dealer_profile().primary_make)

    @override_settings(DEALER_AI_PRIMARY_MAKE="Ford")
    def test_primary_make_env_override(self):
        # Franchise config sets DEALER_AI_PRIMARY_MAKE to the OEM brand.
        self.assertEqual(get_dealer_profile().primary_make, "Ford")

    @override_settings(DEALER_AI_PRIMARY_MAKE="  Toyota  ")
    def test_primary_make_env_is_stripped(self):
        self.assertEqual(get_dealer_profile().primary_make, "Toyota")


class GetDealerProfileIndieFieldsResolution(TestCase):
    """SESSION_032 — the seven indie fields now persist through
    ``DealerOnboardingProfile``. Each field has an independent
    resolution order documented in the module docstring."""

    def setUp(self):
        DealerOnboardingProfile.objects.all().delete()

    def test_profile_dealer_type_beats_env(self):
        DealerOnboardingProfile.objects.create(dealer_type="franchise")
        with override_settings(DEALER_AI_DEALER_TYPE="independent"):
            self.assertEqual(get_dealer_profile().dealer_type, "franchise")

    def test_blank_profile_dealer_type_falls_through_to_env(self):
        DealerOnboardingProfile.objects.create(dealer_type="")
        with override_settings(DEALER_AI_DEALER_TYPE="franchise"):
            self.assertEqual(get_dealer_profile().dealer_type, "franchise")

    def test_bhph_configured_flag_gates_bhph_enabled_reads(self):
        # bhph_configured=False → resolver uses Copper Canyon default (True),
        # ignoring the DB's bhph_enabled value even if it's False.
        DealerOnboardingProfile.objects.create(
            bhph_enabled=False,
            bhph_configured=False,
        )
        self.assertTrue(get_dealer_profile().bhph_enabled)

    def test_bhph_configured_true_lets_user_disable(self):
        DealerOnboardingProfile.objects.create(
            bhph_enabled=False,
            bhph_configured=True,
        )
        self.assertFalse(get_dealer_profile().bhph_enabled)

    def test_bhph_configured_true_lets_user_enable(self):
        DealerOnboardingProfile.objects.create(
            bhph_enabled=True,
            bhph_configured=True,
        )
        self.assertTrue(get_dealer_profile().bhph_enabled)

    def test_subprime_lenders_parses_newlines(self):
        DealerOnboardingProfile.objects.create(
            subprime_lenders="Sonoran Credit\nDesert Auto Finance\n  Vista Lending  \n\n"
        )
        result = get_dealer_profile().subprime_lenders
        self.assertEqual(
            result,
            ("Sonoran Credit", "Desert Auto Finance", "Vista Lending"),
        )

    def test_subprime_lenders_blank_falls_back_to_defaults(self):
        DealerOnboardingProfile.objects.create(subprime_lenders="")
        result = get_dealer_profile().subprime_lenders
        self.assertGreaterEqual(len(result), 3)  # Copper Canyon default

    def test_floor_plan_lender_prefers_db_over_default(self):
        DealerOnboardingProfile.objects.create(floor_plan_lender="Kinetic Advantage")
        self.assertEqual(get_dealer_profile().floor_plan_lender, "Kinetic Advantage")

    def test_floor_plan_lender_blank_falls_back(self):
        DealerOnboardingProfile.objects.create(floor_plan_lender="")
        self.assertEqual(get_dealer_profile().floor_plan_lender, "NextGear")

    def test_warranty_offering_prefers_db(self):
        DealerOnboardingProfile.objects.create(
            warranty_offering="60-day / 2000-mile bumper-to-bumper"
        )
        self.assertEqual(
            get_dealer_profile().warranty_offering,
            "60-day / 2000-mile bumper-to-bumper",
        )

    def test_credit_range_served_prefers_db(self):
        DealerOnboardingProfile.objects.create(
            credit_range_served="500+ with cosigner; open BHPH below"
        )
        self.assertEqual(
            get_dealer_profile().credit_range_served,
            "500+ with cosigner; open BHPH below",
        )

    def test_makes_carried_parses_newlines(self):
        DealerOnboardingProfile.objects.create(
            makes_carried="Toyota\nHonda\nSubaru"
        )
        self.assertEqual(
            get_dealer_profile().makes_carried,
            ("Toyota", "Honda", "Subaru"),
        )

    def test_makes_carried_falls_back_to_main_brands_csv(self):
        # Legacy profile that only populated the CSV `main_brands` field
        # (pre-SESSION_032). Resolver surfaces it through the new API.
        DealerOnboardingProfile.objects.create(
            makes_carried="",
            main_brands="Ford, Lincoln, Mercury",
        )
        self.assertEqual(
            get_dealer_profile().makes_carried,
            ("Ford", "Lincoln", "Mercury"),
        )

    def test_makes_carried_new_field_beats_legacy_csv(self):
        DealerOnboardingProfile.objects.create(
            makes_carried="Toyota\nHonda",
            main_brands="Ford, Lincoln",  # legacy — ignored when new field set
        )
        self.assertEqual(get_dealer_profile().makes_carried, ("Toyota", "Honda"))

    def test_both_makes_fields_blank_falls_back_to_copper_canyon(self):
        DealerOnboardingProfile.objects.create(makes_carried="", main_brands="")
        self.assertIn("Toyota", get_dealer_profile().makes_carried)
