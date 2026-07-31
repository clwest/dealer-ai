"""Milestone 1 · Increment 4C — advisor-workspace authorization primitives.

DRF permission classes covering **authorization only** — the "may this
authenticated user access this advisor workspace?" question. Identity
lives in DRF's authentication classes (settings.py); tenant scope
lives in :mod:`services.tenancy`; business permissions beyond
"belongs here at all" live in later increments (4D admin gating).

Layer discipline (see ``docs/roadmap/AUTHENTICATION_MODEL.md``):

- **Identity** — DRF authentication classes. Not this module.
- **Authorization** — this module. Each class answers a single yes/no
  question and is composable via DRF's ``|`` and ``&`` operators.
- **Business permissions** — later. E.g. "may the F&I manager
  approve this deal?" belongs to the F&I milestone.
- **Data scoping** — later. The lead-ownership 403 inside
  :func:`views.advisor_follow_up` is the data-scoping layer's
  existing manifestation on this endpoint; it is preserved verbatim
  because it is orthogonal to authorization.

Classes here are intentionally *small* and *focused*. Composing them
at the view layer is preferred to bundling logic into one class. See
``AUTHENTICATION_MODEL.md`` §7 for the specific composition applied
to the advisor workspace.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission

from .models import ROLE_DEALER_OWNER, Salesperson, UserDealershipRole


class IsAdvisorForSlug(BasePermission):
    """The authenticated user *is* the Salesperson whose slug appears
    in the URL kwarg ``slug``.

    Requires the ``Salesperson.user`` link (introduced in Increment
    4A) to be set. Returns ``False`` for any of: anonymous request,
    authenticated user with no linked Salesperson, authenticated user
    whose linked Salesperson has a different slug, or a view whose
    URL routing does not populate ``kwargs["slug"]``.

    Reusable at any endpoint whose URL identifies a Salesperson by
    slug. Not applicable to endpoints identified by a different
    resource (Vehicle stock number, Lead pk, etc.) — those will grow
    their own focused classes.
    """

    message = "Not the advisor for this workspace."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        salesperson = getattr(user, "salesperson", None)
        if salesperson is None:
            return False
        slug = view.kwargs.get("slug") if hasattr(view, "kwargs") else None
        return bool(slug) and salesperson.slug == slug


class IsDealerOwnerForAdvisorSlug(BasePermission):
    """The authenticated user holds ``dealer_owner`` at the dealership
    that owns the Salesperson identified by URL kwarg ``slug``.

    Encodes the §1.4 planning-memo rule: *"dealer_owner (at the same
    dealership) can view any advisor's queue."* Cross-dealership
    ownership does **not** grant access — an owner of Dealership A
    cannot view Dealership B's advisors.

    Reusable at any endpoint whose URL identifies a Salesperson by
    slug. The target-tenant discovery (Salesperson slug → dealership)
    is inherent to the advisor URL shape; other endpoint families
    will use different permission classes with different target-
    tenant discovery. That is intentional — one focused class per
    URL-shape family is cheaper to reason about than a generic
    "IsDealerOwnerSomewhere" abstraction.

    Silent ``False`` on unknown slug — do not raise, and do not leak
    slug existence through differential status codes. The view's own
    404 handling (post-permission) preserves the not-found path for
    legitimate callers.
    """

    message = "Not the dealer owner for this advisor's dealership."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        slug = view.kwargs.get("slug") if hasattr(view, "kwargs") else None
        if not slug:
            return False
        target_dealership_id = (
            Salesperson.objects.filter(slug=slug, is_active=True)
            .values_list("dealership_id", flat=True)
            .first()
        )
        if target_dealership_id is None:
            return False
        return UserDealershipRole.objects.filter(
            user=user,
            dealership_id=target_dealership_id,
            role=ROLE_DEALER_OWNER,
        ).exists()
