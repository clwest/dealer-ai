"""Milestone 1 tenancy resolvers — default row + request-context.

The module is the *single source of truth* for tenancy resolution. Two
distinct entry points serve two distinct call-sites:

- :func:`get_default_dealership` — the single-tenant fallback and the
  target of the write-path ``pre_save`` safety net. Introduced in
  Increment 3.
- :func:`get_current_dealership` — the request-context resolver
  introduced in Increment 4B. Composes three orthogonal signals in
  priority order: authenticated-user membership → request header
  (``X-Dealership-Slug``) → default. Never returns ``None``.

Layer separation (kept intentionally distinct — do not collapse):

- **Identity** — established by DRF's authentication classes; leaves
  ``request.user`` populated (or ``AnonymousUser``). Not this module's
  concern.
- **Authorization** — *which dealership is this user acting within*.
  Answered by :func:`get_current_dealership`. This is the layer 4B
  introduces.
- **Business permissions** — *what may this user do*. Answered by DRF
  permission classes in 4C (advisor workspace) and 4D (admin
  endpoints). Not this module's concern.

Increment 4B write-path plumbing (from Increment 3) is unchanged: the
``pre_save`` autofill signal continues to attach the default when a
tenant is unset. The request-context resolver is *read-side only* —
views call it to scope querysets; write-path callers still pass
``dealership=`` explicitly (or accept the default fallback).

Consumers today:

1. :func:`services.dealer_config.get_dealer_name` /
   :func:`services.dealer_config.get_dealer_profile` — read-path
   resolvers for prompt templating and payment-engine math.
2. The :func:`_auto_attach_default_dealership` ``pre_save`` signal
   handler registered against the six tenant carriers — the write-path
   safety net. Any ``save()`` on ``Vehicle`` / ``Salesperson`` /
   ``ChatSession`` / ``ChatMessage`` / ``CustomerLead`` /
   ``DealerOnboardingProfile`` where ``dealership_id is None`` gets the
   default attached automatically. Callers that already set
   ``dealership=`` (production views, seeders, request-context code
   in later increments) short-circuit the fallback — the handler never
   overwrites an explicit value.
3. :func:`get_current_dealership` (Increment 4B). Called by views that
   need to scope querysets to the requesting user's active dealership.
   No view uses it yet; 4C/4D are the first consumers.

Import-safety: the module never touches the DB at import time. The
first :func:`get_default_dealership` call performs the lookup and
caches the primary key at module scope. :func:`reset_default_dealership_cache`
exists for tests that re-create the test database mid-run.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models.signals import pre_save

if TYPE_CHECKING:  # pragma: no cover — typing-only import
    from ..models import Dealership


_DEFAULT_SLUG = "default"

# Module-level PK cache. The migration-seeded default row has a stable
# PK across the life of a single process (Django test runners recreate
# the DB once per run and reuse it across tests). We cache the PK, not
# the model instance, so a fresh ``.get(pk=...)`` lookup runs per call
# — cheap (single indexed hit) and always returns a live-connection
# instance instead of a stale cached one.
_default_dealership_pk: int | None = None


class DealershipNotConfigured(RuntimeError):
    """Raised when :func:`get_default_dealership` is called before the
    ``0009_backfill_dealership_fks`` migration has seeded the default
    row.

    This should only surface pre-migrate — after migration, the row is
    guaranteed to exist. If a test sees this, either the migration was
    skipped or the row was deleted mid-test; both are bugs.
    """


def get_default_dealership() -> "Dealership":
    """Return the deterministic default :class:`Dealership` row.

    The row is created by data-migration ``0009_backfill_dealership_fks``
    with ``slug="default"``. Every ``save()`` on a tenant-carrying model
    without an explicit ``dealership=`` gets attached here by the
    ``pre_save`` handler below.

    Raises :class:`DealershipNotConfigured` if the row is missing.
    """
    global _default_dealership_pk

    from ..models import Dealership  # lazy: keep this module import-safe

    if _default_dealership_pk is not None:
        try:
            return Dealership.objects.get(pk=_default_dealership_pk)
        except Dealership.DoesNotExist:
            # Test DB was recreated / row was deleted; fall through to
            # the slug lookup below and re-cache.
            _default_dealership_pk = None

    try:
        default = Dealership.objects.get(slug=_DEFAULT_SLUG)
    except Dealership.DoesNotExist as exc:
        raise DealershipNotConfigured(
            "Default Dealership row missing. Ensure migration "
            "0009_backfill_dealership_fks has run."
        ) from exc

    _default_dealership_pk = default.pk
    return default


def reset_default_dealership_cache() -> None:
    """Clear the module-level PK cache.

    Useful for tests that flush and re-seed the tenant carrier rows,
    or that re-create the test database mid-run. Safe to call at any
    time — the next :func:`get_default_dealership` call rehydrates from
    the DB.
    """
    global _default_dealership_pk
    _default_dealership_pk = None


# ---- request-context resolvers (Increment 4B) --------------------------------

_DEALERSHIP_HEADER = "X-Dealership-Slug"


def get_active_membership(user):
    """Return the :class:`UserDealershipRole` a user is currently acting under.

    **This is the extension seam for dealership switching.** Increment
    4B ships a deterministic single-membership implementation; future
    increments (a proper dealership-picker UI, per-session active-role
    persistence, etc.) replace *this function's body* without altering
    :func:`get_current_dealership` or any downstream caller.

    Current implementation (Increment 4B, single-dealership dev
    environment):

    - Anonymous or ``None`` → ``None``.
    - No memberships → ``None``.
    - Exactly one membership → that membership.
    - Multiple memberships → deterministically the first by the model's
      ``Meta.ordering`` (``user, dealership, role``). Deterministic
      choice is safe *today* because no live user holds cross-dealership
      memberships (there are no live users at all). When 4E+ ships the
      login flow the number of multi-dealership users will still be
      zero in single-tenant deployments, and the eventual multi-tenant
      dealership-switching UI is expected to replace this branch before
      real multi-dealership users appear.

    Future extension shape (recorded here so the extension is
    obviously *inside* this helper, not a parallel implementation):

    - Read a session-scoped active-membership PK
      (``request.session["active_membership_id"]``) written by the
      dealership-picker UI. Validate it still belongs to ``user``.
    - If unset or stale, fall through to the deterministic-first
      branch below.
    - A dedicated ``set_active_membership(request, membership)`` helper
      writes the session key.

    Nothing about that extension changes the return type or the
    resolver at :func:`get_current_dealership`.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return None

    from ..models import UserDealershipRole

    # ``select_related("dealership")`` so callers who then read
    # ``membership.dealership`` do not incur a second query.
    return (
        UserDealershipRole.objects.filter(user=user)
        .select_related("dealership")
        .first()
    )


def get_current_dealership(request) -> "Dealership":
    """Return the :class:`Dealership` for the current request context.

    Composes three orthogonal signals in priority order. Each layer is
    a distinct concern; they are ordered by *specificity of intent*,
    not by *strength of authentication*.

    1. **Authenticated identity.**
       :func:`get_active_membership` returns a membership; use its
       dealership. Auth is the strongest signal of intent because the
       user *chose* to log in as themselves and their memberships are
       explicit business data.
    2. **Explicit request signal.** ``X-Dealership-Slug`` header
       matching a live :class:`Dealership`. Enables public / embed /
       cross-domain callers that cannot authenticate (customer chat,
       partner integrations) to declare tenancy explicitly. Silent
       fall-through when the header is missing or the slug does not
       resolve — no exception.
    3. **Default fallback.** :func:`get_default_dealership` — the
       terminal fallback. Guarantees this function never returns
       ``None`` even in a fully anonymous, header-less request.

    Never returns ``None``. Never raises on unknown header slugs (the
    header is a hint, not a contract; treating it as a contract would
    let a caller induce a 500 by sending a bogus slug).

    Not called by any view yet — 4C (advisor workspace) and 4D (admin
    endpoints) are the first consumers. This function is deliberately
    landed one increment ahead of its callers so the resolver's
    behavior can be locked by tests in isolation.
    """
    user = getattr(request, "user", None)
    membership = get_active_membership(user)
    if membership is not None:
        return membership.dealership

    header_value = _read_dealership_header(request)
    if header_value:
        from ..models import Dealership

        header_dealership = Dealership.objects.filter(slug=header_value).first()
        if header_dealership is not None:
            return header_dealership

    return get_default_dealership()


def _read_dealership_header(request) -> str:
    """Return the ``X-Dealership-Slug`` header value or empty string.

    Django surfaces HTTP headers on ``request.META`` prefixed with
    ``HTTP_``. DRF's ``request.headers`` (Django ≥3) gives a
    case-insensitive dict but is only present when ``request`` is a
    DRF ``Request``; we support both to keep the resolver callable
    from plain Django views without requiring a DRF wrapper.
    """
    headers = getattr(request, "headers", None)
    if headers is not None:
        return (headers.get(_DEALERSHIP_HEADER) or "").strip()
    meta = getattr(request, "META", None) or {}
    return (meta.get("HTTP_X_DEALERSHIP_SLUG") or "").strip()


# ---- pre_save signal — write-path safety net --------------------------------

# Model names covered by the fallback. Kept as strings so the handler
# registration in :func:`register_default_dealership_autofill` doesn't
# trigger app-registry access at import time — the actual model class
# lookup happens inside ``AppConfig.ready()``.
_TENANT_CARRIER_MODEL_NAMES = (
    "Vehicle",
    "Salesperson",
    "ChatSession",
    "ChatMessage",
    "CustomerLead",
    "DealerOnboardingProfile",
    # Milestone 3 · Increment 1 (SESSION_056) — condition-report
    # persistence layer. Extended per MILESTONE_3_PLANNING.md §2 row 2.
    "ConditionReport",
    "ConditionFinding",
    "ConditionFindingPhoto",
    # Milestone 4 · Increment 1 (SESSION_066) — recon persistence
    # layer. Extended per MILESTONE_4_PLANNING.md §2 row 4 (9 → 15).
    # Every new carrier gets the same pre_save autofill safety net as
    # its M1/M2/M3 siblings; the M4.2 service layer will thread
    # ``dealership=`` explicitly on every write path so the fallback
    # is truly a safety net rather than the primary code path.
    "Vendor",
    "ReconDecision",
    "WorkOrder",
    "WorkOrderFinding",
    "WorkOrderPart",
    "VendorCommunication",
    # Milestone 5 · Increment 1 (SESSION_075) — vehicle lifecycle
    # persistence layer. Extended per MILESTONE_5_PLANNING.md §2 row 6
    # and §7 M5.1 (15 → 17). Same safety-net posture as M4: the
    # M5.2 service will thread ``dealership=`` explicitly on every
    # write path so the fallback stays a safety net.
    "VehicleStage",
    "VehicleStageEvent",
    # Milestone 6 · Increment 1 (SESSION_082) — photo gallery + listing
    # persistence layer. Extended per MILESTONE_6_PLANNING.md §2 row 4
    # (17 → 19). Same safety-net posture as M4/M5: the M6.2 photo
    # gallery service and M6.3 listing service will thread
    # ``dealership=`` explicitly on every write path so the fallback
    # stays a safety net.
    "VehiclePhoto",
    "VehicleListing",
    # Milestone 7 · Increment 1 (SESSION_088) — job-run observability
    # substrate. Extended per MILESTONE_7_PLANNING.md §5.e Option A
    # (user-confirmed at SESSION_088 open) (19 → 20). ``JobRunLog`` has
    # no parent-tenant relation (no ``session`` FK to walk), so the
    # ``_parent_session_dealership_id`` branch is unreachable and the
    # fallback path is always "attach the default tenant" — which is
    # the right posture for jobs kicked off with no explicit tenant
    # context. The ``@instrumented_task`` decorator overrides this
    # default when a task receives a ``dealership_id`` kwarg (the
    # explicit path that Django autofill defers to per resolution rule
    # 1 in ``_auto_attach_default_dealership``).
    "JobRunLog",
    # Milestone 7 · Increment 3 (SESSION_090) — aging-per-stage
    # snapshot substrate. Extended per MILESTONE_7_PLANNING.md §5.c
    # Option A (user-confirmed at SESSION_088 open) (20 → 21).
    # ``StageAgingSnapshot`` has no parent-tenant relation (unlike
    # VehiclePhoto ⇐ Vehicle), so the ``_parent_session_dealership_id``
    # branch is unreachable and the fallback path is "attach the
    # default tenant." The M7.3 verb writes ``dealership`` explicitly
    # on every row, so the autofill signal only fires when a caller
    # bypasses the verb.
    "StageAgingSnapshot",
    # Milestone 8 · Increment 1 (SESSION_094) — SLA-breach
    # materialization substrate. Extended per MILESTONE_8_PLANNING.md
    # §5.b Option B (user-confirmed at SESSION_094 open) (21 → 22).
    # ``SlaBreachRecord`` has no parent-tenant relation (the M4
    # ``WorkOrder`` parent has its own ``dealership`` FK but the
    # tenancy resolver does not walk work-order FKs), so the
    # ``_parent_session_dealership_id`` branch is unreachable and
    # the fallback path is "attach the default tenant." The M7.4
    # verb-extension writes ``dealership`` explicitly on every
    # ``get_or_create`` call, so the autofill signal only fires when
    # a caller bypasses the verb.
    "SlaBreachRecord",
    # Milestone 9 · Increment 1 (SESSION_100) — Sale entity per
    # MILESTONE_9_PLANNING.md §1.1 + §5.b Option A (user-confirmed at
    # SESSION_100 open) (22 → 23). ``Sale`` OneToOne with
    # ``Vehicle``; the M9.1 :func:`services.sale.record_sale` writes
    # ``dealership`` explicitly on every row. The autofill signal
    # here is the safety net for callers that bypass the service
    # (Django admin form, ad-hoc management command).
    "Sale",
    # Milestone 9 · Increment 2 (SESSION_101) — Delivery entity per
    # MILESTONE_9_PLANNING.md §1.2 Option A (user-confirmed at
    # SESSION_101 open, recorded in §0.a) (23 → 24). ``Delivery``
    # OneToOne with ``Sale`` (mandatory). The M9.2
    # :func:`services.delivery.record_delivery` writes ``dealership``
    # explicitly on every row; the autofill signal is the safety net.
    "Delivery",
    # Milestone 10 · Increment 1 (SESSION_106) — CreditApplication
    # entity per MILESTONE_10_PLANNING.md §5.a Option C (user-
    # confirmed at SESSION_106 open, recorded in §0.a) (24 → 25).
    # Nullable FKs to CustomerLead and Sale. The M10.1
    # :func:`services.f_and_i.record_credit_application` writes
    # ``dealership`` explicitly on every row; the autofill signal
    # is the safety net for callers that bypass the service
    # (Django admin form, ad-hoc management command). Retention
    # clock is enforced at the model layer per §5.e.
    "CreditApplication",
    # Milestone 10 · Increment 2 (SESSION_107) — DealStructure
    # entity per MILESTONE_10_PLANNING.md §1.2 (attach shape
    # confirmed at planning-time; income/debt capture on the
    # parent CreditApplication per §1.2.a Option A, user-
    # confirmed at SESSION_107 open, recorded in §0.a)
    # (25 → 26). FKs to CreditApplication (parent) and
    # Vehicle (target). The M10.2
    # :func:`services.f_and_i.deal_structure.record_deal_structure`
    # writes ``dealership`` explicitly on every row and computes
    # the LTV / PTI / DTI denormalized columns at write time;
    # the autofill signal is the safety net for callers that
    # bypass the service.
    "DealStructure",
    # Milestone 10 · Increment 3 (SESSION_108) — LenderProgram
    # + LenderSubmission entities per MILESTONE_10_PLANNING.md
    # §1.3 (four §1.3.a-d decisions confirmed at SESSION_108
    # open, all Option A, recorded in §0.a) (26 → 28).
    # LenderProgram is a per-dealership catalog; LenderSubmission
    # FKs to DealStructure (CASCADE) + LenderProgram (PROTECT).
    # The M10.3 :mod:`services.f_and_i.lender` verbs write
    # ``dealership`` explicitly on every row; the autofill
    # signal is the safety net for callers that bypass the
    # service.
    "LenderProgram",
    "LenderSubmission",
    # Milestone 10 · Increment 4 (SESSION_109) — Stipulation
    # entity per MILESTONE_10_PLANNING.md §1.4 (four §1.4.a-d
    # decisions confirmed at SESSION_109 open, all Option A,
    # recorded in §0.a) (28 → 29). Mandatory FK to
    # LenderSubmission (CASCADE). The M10.4
    # :mod:`services.f_and_i.stipulation` verbs write
    # ``dealership`` explicitly on every row and auto-populate
    # ``cleared_at`` on state transitions; the autofill signal
    # is the safety net for callers that bypass the service.
    "Stipulation",
    # Milestone 10 · Increment 5 (SESSION_110) — Contract +
    # BackEndProductAgreement + Funding entities per
    # MILESTONE_10_PLANNING.md §1.5 + §1.6 (five §1.5.a-d +
    # §1.6.a decisions confirmed at SESSION_110 open,
    # recorded in §0.a) (29 → 32). Contract FKs to
    # DealStructure (CASCADE); BackEndProductAgreement FKs to
    # Contract (CASCADE); Funding OneToOne to Contract
    # (CASCADE). The M10.5 :mod:`services.f_and_i.contract`
    # and :mod:`services.f_and_i.funding` verbs write
    # ``dealership`` explicitly on every row and auto-populate
    # ``signed_at`` / ``voided_at`` / ``funded_at`` on state
    # transitions; the autofill signal is the safety net for
    # callers that bypass the service.
    "Contract",
    "BackEndProductAgreement",
    "Funding",
    # Milestone 10 · Increment 6 (SESSION_111) — Chargeback entity
    # per MILESTONE_10_PLANNING.md §1.7 (six §1.7.a-f decisions
    # confirmed at SESSION_111 open, recorded in §0.a) (32 → 33).
    # Nullable FKs to Contract + BackEndProductAgreement (mirrors
    # M10.1 §5.a Option C). The M10.6
    # :func:`services.f_and_i.record_chargeback` writes
    # ``dealership`` explicitly on every row and auto-transitions
    # the associated Funding to ``chargedback`` for deal-level
    # types + auto-populates BEPA ``cancelled_at`` /
    # ``cancellation_amount`` for product-cancellation type. The
    # autofill signal is the safety net for callers that bypass
    # the service.
    "Chargeback",
    # Milestone 10 · Increment 7 (SESSION_112) — ComplianceRecord
    # entity per MILESTONE_10_PLANNING.md §1.8 (six §1.8.a-f
    # decisions confirmed at SESSION_112 open, recorded in §0.a)
    # (33 → 34). OneToOne with Contract per §1.8.a Option A —
    # matches FINANCE §6.9 deal-jacket mental model. Single-
    # entity typed-columns model per §1.8.b Option A covering
    # FINANCE §6.1-§6.9 concerns. The M10.7
    # :mod:`services.f_and_i.compliance` verbs write
    # ``dealership`` explicitly on every row; the autofill
    # signal is the safety net for callers that bypass the
    # service.
    "ComplianceRecord",
    # Milestone 11 · Increment 2 (SESSION_115) — TestDrive entity
    # per MILESTONE_11_PLANNING.md §1.2 + §5.c Option A (user-
    # confirmed at SESSION_114 open, recorded in §0.a) (34 → 35).
    # Mandatory FKs to CustomerLead + Vehicle (both CASCADE). The
    # M11.2 :func:`services.test_drives.record_test_drive` writes
    # ``dealership`` explicitly on every row; the autofill signal
    # is the safety net for callers that bypass the service (Django
    # admin, ad-hoc management command).
    "TestDrive",
    # Milestone 11 · Increment 3 (SESSION_116) — DealWriteup entity
    # per MILESTONE_11_PLANNING.md §1.3 + §5.e Option A (user-
    # confirmed at SESSION_114 open, recorded in §0.a) (35 → 36).
    # Mandatory FKs to CustomerLead + Vehicle (both CASCADE). The
    # M11.3 :mod:`services.deal_writeups` verbs write ``dealership``
    # explicitly on every row and auto-transition the sales-manager
    # approval + F&I handoff timestamps at their respective verb
    # calls. The autofill signal is the safety net for callers that
    # bypass the service. Handoff verb auto-creates a matching
    # M10.1 CreditApplication via the existing
    # :func:`services.f_and_i.record_credit_application` verb.
    "DealWriteup",
)


def _auto_attach_default_dealership(sender, instance, **kwargs) -> None:  # noqa: ARG001
    """``pre_save`` handler: fill ``instance.dealership_id`` when the
    caller left it unset.

    Resolution order:

    1. Explicit ``dealership=`` on ``.create()`` / ``.save()`` — the
       fallback is a no-op when ``dealership_id`` is already populated.
       This preserves the explicit-tenant path that future
       request-context resolution will use.
    2. Parent-record inheritance — if ``instance`` has a ``session_id``
       (``ChatMessage`` and ``CustomerLead`` both do) and the parent
       ``ChatSession`` has a ``dealership_id``, inherit. This keeps
       child rows tenant-consistent with their parent session without
       requiring every caller to plumb the tenant argument through.
    3. Default tenancy — :func:`get_default_dealership`.
    """
    if getattr(instance, "dealership_id", None) is not None:
        return

    session_id = getattr(instance, "session_id", None)
    if session_id is not None:
        parent_dealership_id = _parent_session_dealership_id(sender, session_id)
        if parent_dealership_id is not None:
            instance.dealership_id = parent_dealership_id
            return

    instance.dealership = get_default_dealership()


def _parent_session_dealership_id(sender, session_id) -> int | None:
    """Return the ``dealership_id`` of the parent ``ChatSession``, or
    ``None`` if the session is missing or has no tenancy set yet.

    Uses ``.values_list()`` so exactly one column round-trips per
    inherited save (avoids materializing the full ``ChatSession``
    instance in the hot path)."""
    from django.apps import apps as django_apps

    # Only lookup for models whose `session` FK actually points at
    # ChatSession — guard against false positives if a future model
    # names a field `session` for something else.
    session_field = sender._meta.get_field("session") if _has_field(sender, "session") else None
    if session_field is None:
        return None
    if session_field.related_model is not django_apps.get_model("dealer_ai", "ChatSession"):
        return None

    ChatSession = django_apps.get_model("dealer_ai", "ChatSession")
    return (
        ChatSession.objects.filter(pk=session_id)
        .values_list("dealership_id", flat=True)
        .first()
    )


def _has_field(model, name: str) -> bool:
    try:
        model._meta.get_field(name)
    except Exception:
        return False
    return True


def register_default_dealership_autofill() -> None:
    """Wire :func:`_auto_attach_default_dealership` into ``pre_save`` for
    each tenant carrier.

    Called from :meth:`dealer_ai.apps.DealerAiConfig.ready`. Idempotent
    — Django dispatch deduplicates handler+sender pairs when ``dispatch_uid``
    is set.
    """
    from django.apps import apps as django_apps

    for model_name in _TENANT_CARRIER_MODEL_NAMES:
        Model = django_apps.get_model("dealer_ai", model_name)
        pre_save.connect(
            _auto_attach_default_dealership,
            sender=Model,
            dispatch_uid=f"dealer_ai.tenancy.autofill.{model_name}",
        )
