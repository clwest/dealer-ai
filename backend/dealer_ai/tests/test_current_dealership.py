"""Milestone 1 · Increment 4B — request-context tenancy resolver.

Locks the behavior of :func:`services.tenancy.get_current_dealership`
and its extension-seam helper :func:`services.tenancy.get_active_membership`.

Layer discipline (see the module docstring): Identity is DRF's job;
Authorization ("which dealership") is this resolver; Business
permissions are 4C/4D. These tests are intentionally scoped to the
Authorization layer — no view is exercised.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from dealer_ai.models import (
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    Dealership,
    UserDealershipRole,
)
from dealer_ai.services.tenancy import (
    get_active_membership,
    get_current_dealership,
    get_default_dealership,
)

User = get_user_model()


class ActiveMembershipHelper(TestCase):
    """Lock the ``get_active_membership`` extension seam.

    Future dealership-switching lands *inside* this helper — these
    tests describe the behavior contract the extension must preserve.
    """

    def setUp(self):
        self.dealership_a = Dealership.objects.create(
            name="Copper Canyon Auto", slug="copper-canyon-am"
        )
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-am"
        )
        self.user = User.objects.create_user(
            username="am_user", email="am@example.com", password="x"
        )

    def test_returns_none_for_none_user(self):
        self.assertIsNone(get_active_membership(None))

    def test_returns_none_for_anonymous_user(self):
        self.assertIsNone(get_active_membership(AnonymousUser()))

    def test_returns_none_when_user_has_no_memberships(self):
        self.assertIsNone(get_active_membership(self.user))

    def test_returns_the_single_membership(self):
        m = UserDealershipRole.objects.create(
            user=self.user, dealership=self.dealership_a, role=ROLE_DEALER_OWNER
        )
        result = get_active_membership(self.user)
        self.assertEqual(result, m)
        self.assertEqual(result.dealership, self.dealership_a)

    def test_returns_first_membership_when_user_has_multiple(self):
        # Deterministic-first by Meta.ordering (user, dealership, role).
        # The exact winner depends on PK ordering of dealerships; we
        # only assert that a live membership belonging to this user is
        # returned — this is the seam future extensions will replace
        # with an explicit picker.
        m_a = UserDealershipRole.objects.create(
            user=self.user, dealership=self.dealership_a, role=ROLE_ADVISOR
        )
        m_b = UserDealershipRole.objects.create(
            user=self.user, dealership=self.dealership_b, role=ROLE_ADVISOR
        )
        result = get_active_membership(self.user)
        self.assertIn(result, {m_a, m_b})
        self.assertEqual(result.user, self.user)


class GetCurrentDealershipResolver(TestCase):
    """Lock the composition contract of ``get_current_dealership``.

    Priority order under test: authenticated identity → header →
    default. The resolver never returns ``None`` and never raises on
    an unknown header slug.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.default = get_default_dealership()  # seeded by migration 0009
        self.other = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-gcd"
        )
        self.user = User.objects.create_user(
            username="gcd_user", email="gcd@example.com", password="x"
        )

    def _request(self, headers: dict | None = None, user=None):
        req = self.factory.get("/", **{
            f"HTTP_{k.upper().replace('-', '_')}": v
            for k, v in (headers or {}).items()
        })
        req.user = user if user is not None else AnonymousUser()
        return req

    # --- terminal fallback --------------------------------------------------

    def test_anonymous_request_no_header_returns_default(self):
        req = self._request()
        self.assertEqual(get_current_dealership(req), self.default)

    def test_never_returns_none_even_when_everything_is_missing(self):
        # No user attribute at all — should still fall through to default.
        req = self.factory.get("/")
        # Deliberately do not attach ``user``.
        self.assertEqual(get_current_dealership(req), self.default)

    # --- header layer -------------------------------------------------------

    def test_header_resolves_when_slug_matches_live_dealership(self):
        req = self._request(headers={"X-Dealership-Slug": self.other.slug})
        self.assertEqual(get_current_dealership(req), self.other)

    def test_header_with_unknown_slug_falls_through_to_default(self):
        req = self._request(headers={"X-Dealership-Slug": "no-such-slug"})
        # Silent fall-through — no exception, no 500.
        self.assertEqual(get_current_dealership(req), self.default)

    def test_empty_header_falls_through_to_default(self):
        req = self._request(headers={"X-Dealership-Slug": ""})
        self.assertEqual(get_current_dealership(req), self.default)

    # --- identity layer -----------------------------------------------------

    def test_authenticated_user_with_no_membership_falls_through(self):
        # Auth doesn't create tenancy on its own; only memberships do.
        req = self._request(user=self.user)
        self.assertEqual(get_current_dealership(req), self.default)

    def test_authenticated_user_with_one_membership_wins(self):
        UserDealershipRole.objects.create(
            user=self.user, dealership=self.other, role=ROLE_DEALER_OWNER
        )
        req = self._request(user=self.user)
        self.assertEqual(get_current_dealership(req), self.other)

    def test_membership_beats_header_when_both_present(self):
        # Auth is the strongest signal of intent — the user chose to
        # log in as themselves. A header pointing at a *different*
        # tenant is ignored when the authenticated user has an active
        # membership. This test locks that precedence.
        UserDealershipRole.objects.create(
            user=self.user, dealership=self.other, role=ROLE_DEALER_OWNER
        )
        req = self._request(
            user=self.user,
            headers={"X-Dealership-Slug": self.default.slug},
        )
        self.assertEqual(get_current_dealership(req), self.other)


class DrfAuthenticationDefaultsIntegration(TestCase):
    """Sanity check that the DRF auth defaults from settings actually
    load. Not a permission test — that lands in 4C/4D. This only
    asserts that the framework wiring is present and importable.
    """

    def test_default_authentication_classes_are_configured(self):
        from django.conf import settings

        classes = settings.REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES", [])
        self.assertIn(
            "rest_framework.authentication.SessionAuthentication", classes
        )
        self.assertIn(
            "rest_framework.authentication.TokenAuthentication", classes
        )

    def test_default_permission_classes_remain_unset(self):
        # Enforcement is 4C/4D. If this fails, someone silently tightened
        # the framework default and every currently-public endpoint may
        # have gained a 401.
        from django.conf import settings

        self.assertNotIn(
            "DEFAULT_PERMISSION_CLASSES", settings.REST_FRAMEWORK
        )

    def test_authtoken_app_is_installed(self):
        from django.conf import settings

        self.assertIn("rest_framework.authtoken", settings.INSTALLED_APPS)
