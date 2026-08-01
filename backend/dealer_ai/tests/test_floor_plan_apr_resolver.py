"""Milestone 2 · Increment 4a — floor-plan APR resolver + field tests.

Locks the layered resolution DB → env → default and the additive
migration-safety of the new ``DealerOnboardingProfile.floor_plan_apr``
column.

Layer contract (see ``services.dealer_config.get_floor_plan_apr``
docstring):

1. ``DealerOnboardingProfile.floor_plan_apr`` (per-tenant, when set)
2. ``settings.DEALER_AI_FLOOR_PLAN_APR`` (env override, when set)
3. ``Decimal("8.5")`` (Copper Canyon baseline)

Test class map:

- ``FloorPlanAprResolutionOrder`` — DB > env > default precedence.
- ``FloorPlanAprEnvHandling`` — silent fall-through on invalid env
  values (matches the M1 · 4F DEALER_AI_DEALER_TYPE env pattern).
- ``FloorPlanAprFieldShape`` — the nullable field is truly nullable;
  existing rows survive migration `0014` without needing a data
  migration; range validation lives in the accrual engine, not the
  field.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase, override_settings

from dealer_ai.models import DealerOnboardingProfile, Dealership
from dealer_ai.services.dealer_config import get_floor_plan_apr


class FloorPlanAprResolutionOrder(TestCase):
    """DB layer wins; env layer wins when DB is null; default falls
    through when both are unset."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        # Every test starts with no onboarding profile — subtests
        # populate as needed.
        DealerOnboardingProfile.objects.all().delete()

    def test_default_falls_through_when_no_db_no_env(self):
        # No profile, no env override → Copper Canyon 8.5%.
        result = get_floor_plan_apr()
        self.assertEqual(result, Decimal("8.5"))
        self.assertIsInstance(result, Decimal)

    @override_settings(DEALER_AI_FLOOR_PLAN_APR="6.25")
    def test_env_wins_when_no_db(self):
        result = get_floor_plan_apr()
        self.assertEqual(result, Decimal("6.25"))
        self.assertIsInstance(result, Decimal)

    def test_db_wins_when_populated(self):
        DealerOnboardingProfile.objects.create(
            dealership=self.default, floor_plan_apr=Decimal("7.75")
        )
        result = get_floor_plan_apr()
        self.assertEqual(result, Decimal("7.75"))

    @override_settings(DEALER_AI_FLOOR_PLAN_APR="6.25")
    def test_db_beats_env_when_both_set(self):
        DealerOnboardingProfile.objects.create(
            dealership=self.default, floor_plan_apr=Decimal("7.75")
        )
        # DB wins even though env is also set — matches the
        # get_dealer_name pattern where env beats DB for the *name*,
        # but for floor_plan_apr the *per-tenant* value beats the
        # env override (env is a fallback for dealerships without a
        # saved profile, not a global master switch). Documented in
        # the resolver docstring.
        result = get_floor_plan_apr()
        self.assertEqual(result, Decimal("7.75"))

    def test_db_null_falls_through_even_when_profile_exists(self):
        # A profile with every field empty except a null
        # ``floor_plan_apr`` still falls through to the env / default
        # layer — the resolver treats "profile exists but this field
        # is None" the same as "no profile."
        DealerOnboardingProfile.objects.create(
            dealership=self.default, floor_plan_apr=None
        )
        result = get_floor_plan_apr()
        self.assertEqual(result, Decimal("8.5"))


class FloorPlanAprEnvHandling(TestCase):
    """Env override coercion + silent fall-through on invalid values."""

    def setUp(self):
        DealerOnboardingProfile.objects.all().delete()

    @override_settings(DEALER_AI_FLOOR_PLAN_APR="8.5")
    def test_env_string_coerces_to_decimal(self):
        result = get_floor_plan_apr()
        self.assertEqual(result, Decimal("8.5"))
        self.assertIsInstance(result, Decimal)

    @override_settings(DEALER_AI_FLOOR_PLAN_APR="")
    def test_empty_env_falls_through_to_default(self):
        result = get_floor_plan_apr()
        self.assertEqual(result, Decimal("8.5"))

    @override_settings(DEALER_AI_FLOOR_PLAN_APR="not-a-number")
    def test_unparseable_env_falls_through_silently(self):
        # A bad env value must NOT crash the resolver — matches the
        # M1 DEALER_AI_DEALER_TYPE pattern. Bad env → default.
        result = get_floor_plan_apr()
        self.assertEqual(result, Decimal("8.5"))

    @override_settings(DEALER_AI_FLOOR_PLAN_APR="   6.75   ")
    def test_env_whitespace_is_stripped_before_coercion(self):
        result = get_floor_plan_apr()
        self.assertEqual(result, Decimal("6.75"))

    @override_settings(DEALER_AI_FLOOR_PLAN_APR="0")
    def test_env_zero_is_returned_verbatim(self):
        # 0% is a valid (if unusual) APR — some intro / promotional
        # floor lines run at 0% for a term. The resolver returns it;
        # the downstream engine treats apr=0 as zero interest.
        result = get_floor_plan_apr()
        self.assertEqual(result, Decimal("0"))


class FloorPlanAprFieldShape(TestCase):
    """The new field is truly nullable and does not require a data
    migration for existing profile rows."""

    def test_field_is_nullable_at_schema_level(self):
        field = DealerOnboardingProfile._meta.get_field("floor_plan_apr")
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_field_is_decimal_field_with_expected_precision(self):
        field = DealerOnboardingProfile._meta.get_field("floor_plan_apr")
        # Percent-unit APR up to 999.99 fits in DecimalField(5, 2) —
        # more than enough for real floor-plan APRs (typical range
        # 4% to 15%).
        self.assertEqual(field.max_digits, 5)
        self.assertEqual(field.decimal_places, 2)

    def test_creating_profile_without_field_succeeds(self):
        # Additive migration invariant — every existing caller that
        # creates a profile without touching floor_plan_apr must
        # still work (the row saves with floor_plan_apr=None).
        default = Dealership.objects.get(slug="default")
        DealerOnboardingProfile.objects.all().delete()
        profile = DealerOnboardingProfile.objects.create(
            dealership=default, dealership_name="Doesn't Set APR"
        )
        self.assertIsNone(profile.floor_plan_apr)

    def test_field_accepts_a_decimal_value(self):
        default = Dealership.objects.get(slug="default")
        DealerOnboardingProfile.objects.all().delete()
        profile = DealerOnboardingProfile.objects.create(
            dealership=default, floor_plan_apr=Decimal("9.25")
        )
        profile.refresh_from_db()
        self.assertEqual(profile.floor_plan_apr, Decimal("9.25"))

    def test_field_has_no_min_max_validators(self):
        """Range validation lives in the accrual engine
        (``daily_floor_plan_interest`` raises on negative APR), NOT
        at the field level. Locking this here prevents a future
        session accidentally adding MinValueValidator here — which
        would introduce validator friction in incrementally-entered
        operator forms without adding real safety."""
        field = DealerOnboardingProfile._meta.get_field("floor_plan_apr")
        # No validators beyond Django's built-ins for DecimalField.
        validator_types = {type(v).__name__ for v in field.validators}
        # DecimalField auto-adds a DecimalValidator for precision;
        # that's expected. Anything else (MinValueValidator,
        # MaxValueValidator, or custom) would indicate scope creep.
        self.assertEqual(validator_types, {"DecimalValidator"})
