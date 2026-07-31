"""Test fixtures for Milestone 1 authorization work.

Small, focused helpers so tests express *who is calling* in one line
rather than repeating the User + Salesperson + membership setup
pattern. Introduced at SESSION_041 (Increment 4C); intended to serve
every subsequent authorization increment (4D admin gating) without
extension.

Do not put permission-class logic here — this module is fixture-only.
Actual authorization lives in :mod:`dealer_ai.permissions`.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from dealer_ai.models import (
    Dealership,
    Salesperson,
    UserDealershipRole,
)

User = get_user_model()


def make_dealership(slug: str = "test-dealership", name: str | None = None) -> Dealership:
    """Create a Dealership row with a deterministic slug.

    Kept separate from :func:`services.tenancy.get_default_dealership`
    which returns the migration-seeded row. Tests that need a *second*
    dealership (cross-dealership isolation coverage) use this helper.
    """
    return Dealership.objects.create(
        slug=slug, name=name or slug.replace("-", " ").title()
    )


def make_user(username: str = "testuser", password: str = "x") -> "User":
    """Create an auth user with a predictable username/password.

    Tests that need a specific username pass one; otherwise the
    default is fine and different test classes can rely on Django's
    per-test isolation to keep usernames unique within a test run.
    """
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password=password
    )


def make_advisor_user(
    slug: str,
    dealership: Dealership,
    *,
    username: str | None = None,
    salesperson_name: str = "Test Advisor",
    is_active: bool = True,
) -> tuple["User", Salesperson]:
    """Create an authenticated advisor: User + linked Salesperson.

    Returns ``(user, salesperson)`` so tests can assert on either. The
    ``Salesperson.user`` OneToOne link is populated — this is the
    canonical shape :class:`IsAdvisorForSlug` checks for.
    """
    user = make_user(username=username or f"advisor-{slug}")
    salesperson = Salesperson.objects.create(
        dealership=dealership,
        slug=slug,
        name=salesperson_name,
        is_active=is_active,
        user=user,
    )
    return user, salesperson


def make_membership(user, dealership: Dealership, role: str) -> UserDealershipRole:
    """Create a :class:`UserDealershipRole` row with the given role."""
    return UserDealershipRole.objects.create(
        user=user, dealership=dealership, role=role
    )


def authenticated_client(user) -> APIClient:
    """Return a DRF :class:`APIClient` pre-authenticated as ``user``.

    Uses :meth:`APIClient.force_authenticate` so tests do not depend
    on the login endpoint (Increment 4E ships that) or on session
    middleware ordering. This bypasses the auth backends and directly
    attaches ``request.user`` — appropriate for authorization tests
    where authentication is not what is under test.
    """
    client = APIClient()
    client.force_authenticate(user=user)
    return client
