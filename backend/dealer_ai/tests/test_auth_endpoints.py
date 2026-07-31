"""Milestone 1 · Increment 4E — browser auth flow endpoint tests.

Focused tests for the three new endpoints:

- ``POST /api/dealer-ai/auth/login/``
- ``POST /api/dealer-ai/auth/logout/``
- ``GET  /api/dealer-ai/auth/me/``

The tests use DRF's ``APIClient`` (not ``Client``) throughout because
the endpoints live under DRF and the ``force_authenticate`` /
``credentials`` behavior is DRF-native.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.models import (
    ROLE_DEALER_OWNER,
    ROLE_SALES_MANAGER,
    Salesperson,
)
from dealer_ai.services.tenancy import get_default_dealership
from dealer_ai.tests._auth_helpers import make_membership, make_user

User = get_user_model()


class AuthMeEndpoint(TestCase):
    """`/auth/me/` shape + CSRF-cookie priming behavior."""

    def setUp(self):
        self.dealership = get_default_dealership()
        self.url = reverse("dealer_ai:auth-me")

    def test_anonymous_returns_authenticated_false(self):
        res = APIClient().get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"authenticated": False})

    def test_sets_csrf_cookie_for_bootstrap(self):
        # The frontend bootstraps by calling /me/ so the csrftoken
        # cookie exists before login POST fires.
        res = APIClient().get(self.url)
        self.assertIn("csrftoken", res.cookies)
        # Cookie value must be non-empty — cookies are the whole
        # point of the endpoint's csrf-cookie side effect.
        self.assertTrue(res.cookies["csrftoken"].value)

    def test_authenticated_returns_identity_and_active_dealership(self):
        owner = make_user(username="me-owner")
        make_membership(owner, self.dealership, ROLE_DEALER_OWNER)
        client = APIClient()
        client.force_authenticate(user=owner)
        res = client.get(self.url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["user"]["username"], "me-owner")
        self.assertEqual(data["dealership"]["slug"], self.dealership.slug)
        self.assertEqual(data["roles"], [ROLE_DEALER_OWNER])

    def test_reports_multiple_concurrent_roles_at_active_dealership(self):
        # 4A design note: multi-role per dealership is intentional.
        user = make_user(username="me-multirole")
        make_membership(user, self.dealership, ROLE_DEALER_OWNER)
        make_membership(user, self.dealership, ROLE_SALES_MANAGER)
        client = APIClient()
        client.force_authenticate(user=user)
        data = client.get(self.url).json()
        self.assertEqual(set(data["roles"]), {ROLE_DEALER_OWNER, ROLE_SALES_MANAGER})

    def test_exposes_advisor_slug_when_user_is_linked(self):
        user = make_user(username="me-advisor")
        Salesperson.objects.create(
            dealership=self.dealership,
            slug="my-slug",
            name="Me Advisor",
            user=user,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        data = client.get(self.url).json()
        self.assertEqual(data["user"]["salesperson_slug"], "my-slug")


class AuthLoginEndpoint(TestCase):
    """`/auth/login/` — session establishment + generic error message."""

    def setUp(self):
        self.dealership = get_default_dealership()
        self.password = "correct-horse-battery-staple"
        self.user = User.objects.create_user(
            username="login-user",
            email="login-user@example.com",
            password=self.password,
        )
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.url = reverse("dealer_ai:auth-login")

    def test_valid_credentials_returns_me_payload(self):
        client = APIClient()
        res = client.post(
            self.url,
            data={"username": "login-user", "password": self.password},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["user"]["username"], "login-user")
        self.assertEqual(data["roles"], [ROLE_SALES_MANAGER])

    def test_valid_credentials_establishes_session_cookie(self):
        # After login, subsequent GET /me/ must see the session
        # without re-authenticating via force_authenticate.
        client = APIClient()
        client.post(
            self.url,
            data={"username": "login-user", "password": self.password},
            format="json",
        )
        me = client.get(reverse("dealer_ai:auth-me"))
        self.assertTrue(me.json()["authenticated"])

    def test_wrong_password_returns_generic_401(self):
        res = APIClient().post(
            self.url,
            data={"username": "login-user", "password": "wrong"},
            format="json",
        )
        self.assertEqual(res.status_code, 401)
        # Generic message — no hint about whether username exists.
        self.assertEqual(res.json(), {"detail": "Invalid credentials."})

    def test_unknown_user_returns_same_generic_401(self):
        # User enumeration defense: unknown user must return the
        # same status + body as wrong password. Any divergence would
        # leak which usernames exist.
        res = APIClient().post(
            self.url,
            data={"username": "no-such-user", "password": "whatever"},
            format="json",
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json(), {"detail": "Invalid credentials."})

    def test_missing_password_returns_400(self):
        res = APIClient().post(
            self.url,
            data={"username": "login-user"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_missing_username_returns_400(self):
        res = APIClient().post(
            self.url,
            data={"password": self.password},
            format="json",
        )
        self.assertEqual(res.status_code, 400)


class AuthLogoutEndpoint(TestCase):
    """`/auth/logout/` — session teardown + idempotency."""

    def setUp(self):
        self.dealership = get_default_dealership()
        self.password = "correct-horse-battery-staple"
        self.user = User.objects.create_user(
            username="logout-user", password=self.password
        )
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.login_url = reverse("dealer_ai:auth-login")
        self.logout_url = reverse("dealer_ai:auth-logout")
        self.me_url = reverse("dealer_ai:auth-me")

    def test_logout_clears_session(self):
        client = APIClient()
        client.post(
            self.login_url,
            data={"username": "logout-user", "password": self.password},
            format="json",
        )
        self.assertTrue(client.get(self.me_url).json()["authenticated"])
        res = client.post(self.logout_url)
        self.assertEqual(res.status_code, 200)
        # Session gone.
        self.assertFalse(client.get(self.me_url).json()["authenticated"])

    def test_logout_when_anonymous_is_safe(self):
        # No prior login — logout must not error. The frontend calls
        # this on ambiguous state without pre-flighting.
        res = APIClient().post(self.logout_url)
        self.assertEqual(res.status_code, 200)

    def test_logout_is_idempotent(self):
        client = APIClient()
        client.post(
            self.login_url,
            data={"username": "logout-user", "password": self.password},
            format="json",
        )
        client.post(self.logout_url)
        res = client.post(self.logout_url)  # again
        self.assertEqual(res.status_code, 200)


class SessionAuthenticationDrivesProtectedEndpoints(TestCase):
    """Locks the full round-trip: log in via `/auth/login/`, then hit
    a 4C or 4D protected endpoint using the same session cookie. No
    ``force_authenticate`` — the session is doing the work.
    """

    def setUp(self):
        self.dealership = get_default_dealership()
        self.password = "correct-horse-battery-staple"
        self.owner = User.objects.create_user(
            username="sess-owner", password=self.password
        )
        make_membership(self.owner, self.dealership, ROLE_DEALER_OWNER)

    def _login_client(self, username: str) -> APIClient:
        client = APIClient()
        client.post(
            reverse("dealer_ai:auth-login"),
            data={"username": username, "password": self.password},
            format="json",
        )
        return client

    def test_admin_endpoint_reachable_after_session_login(self):
        client = self._login_client("sess-owner")
        res = client.get(reverse("dealer_ai:admin-lead-list"))
        self.assertEqual(res.status_code, 200, res.content)

    def test_admin_endpoint_401_after_logout(self):
        client = self._login_client("sess-owner")
        client.post(reverse("dealer_ai:auth-logout"))
        res = client.get(reverse("dealer_ai:admin-lead-list"))
        self.assertIn(res.status_code, (401, 403))

    def test_wrong_role_gets_403_not_401(self):
        # Distinct-status invariant: authenticated but under-privileged
        # user must see 403 (authorization failure), never 401
        # (authentication failure). The frontend routes on this.
        advisor = User.objects.create_user(
            username="sess-advisor", password=self.password
        )
        from dealer_ai.models import ROLE_ADVISOR

        make_membership(advisor, self.dealership, ROLE_ADVISOR)
        client = self._login_client("sess-advisor")
        res = client.get(reverse("dealer_ai:admin-lead-list"))
        self.assertEqual(res.status_code, 403)


class CsrfEnforcedOnAuthenticatedMutations(TestCase):
    """Locks the CSRF contract: an authenticated caller using a
    plain ``django.test.Client`` (which honors CSRF middleware) must
    include ``X-CSRFToken`` on unsafe methods against
    ``SessionAuthentication``-backed endpoints, or the request is
    rejected. Prevents cross-site forged writes against a
    logged-in operator's browser.

    We use ``Client(enforce_csrf_checks=True)`` because DRF's
    ``APIClient`` disables CSRF by default (that's what enables
    ``force_authenticate`` for test ergonomics). The plain client
    matches real browser semantics.
    """

    def setUp(self):
        self.password = "correct-horse-battery-staple"
        self.user = User.objects.create_user(
            username="csrf-user", password=self.password
        )
        make_membership(
            self.user, get_default_dealership(), ROLE_DEALER_OWNER
        )
        self.client_csrf = Client(enforce_csrf_checks=True)

    def _login_and_capture_csrf(self) -> str:
        """Log in via the plain client so CsrfViewMiddleware runs;
        return the csrftoken the browser would then send back.
        """
        # Prime the csrftoken cookie via /me/ (has @ensure_csrf_cookie).
        me = self.client_csrf.get(reverse("dealer_ai:auth-me"))
        token = me.cookies["csrftoken"].value
        # Login POST — must include the token in the header.
        login_res = self.client_csrf.post(
            reverse("dealer_ai:auth-login"),
            data={"username": "csrf-user", "password": self.password},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(login_res.status_code, 200, login_res.content)
        # After login, refresh token from cookie jar (Django rotates on
        # login by default).
        return self.client_csrf.cookies["csrftoken"].value

    def test_authenticated_mutation_without_csrf_header_is_rejected(self):
        token = self._login_and_capture_csrf()  # noqa: F841
        # Hit a protected mutation without X-CSRFToken.
        res = self.client_csrf.post(
            reverse("dealer_ai:admin-lead-assign", args=[1]),
            data={"salesperson_id": None},
            content_type="application/json",
        )
        # DRF SessionAuthentication enforces CSRF on authenticated
        # requests -> 403 Forbidden.
        self.assertEqual(res.status_code, 403)

    def test_authenticated_mutation_with_csrf_header_reaches_view(self):
        token = self._login_and_capture_csrf()
        # POST with the token in the header — the request reaches the
        # view. The view returns 404 (no lead pk=1 in this tenant),
        # which is exactly what we want: auth passed, CSRF passed,
        # business logic ran.
        res = self.client_csrf.post(
            reverse("dealer_ai:admin-lead-assign", args=[1]),
            data={"salesperson_id": None},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(res.status_code, 404, res.content)


class PublicBrandingRemainsUnauthenticated(TestCase):
    """§3 compatibility invariant lock: public branding must render
    without a session. If this test ever fails, `useBrand()` on
    unauthenticated public pages will fall through to defaults
    silently — a regression worth failing loudly.
    """

    def test_onboarding_profile_get_is_public(self):
        res = APIClient().get(reverse("dealer_ai:onboarding-profile"))
        self.assertEqual(res.status_code, 200)

    def test_public_salespeople_list_is_public(self):
        res = APIClient().get(reverse("dealer_ai:salespeople-list"))
        self.assertEqual(res.status_code, 200)


# Silence the unused-import lint on `get_token` — it's imported for
# discoverability by future test authors reading this module.
_ = get_token
