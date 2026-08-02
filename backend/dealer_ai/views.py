from pathlib import Path
from typing import Optional
from uuid import uuid4

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    parser_classes,
    permission_classes,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from django.conf import settings
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import (
    ChatMessage,
    ChatSession,
    ConditionFinding,
    ConditionFindingPhoto,
    ConditionReport,
    CustomerLead,
    DealerOnboardingProfile,
    Salesperson,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
)
from .serializers import (
    AcquisitionUpsertRequestSerializer,
    AdminChatSessionListSerializer,
    AdminLeadListSerializer,
    AssignLeadSerializer,
    ChatMessageInputSerializer,
    ChatMessageSerializer,
    ChatSessionSerializer,
    ConditionFindingCreateRequestSerializer,
    ConditionFindingUpdateRequestSerializer,
    ConditionReportCreateRequestSerializer,
    CostCreateRequestSerializer,
    CustomerLeadSerializer,
    DealerOnboardingProfileSerializer,
    ManagerChatInputSerializer,
    ONBOARDING_DEFAULTS,
    PhotoAttachSerializer,
    PhotoRequestUploadSerializer,
    SalespersonAdminSerializer,
    SalespersonPublicSerializer,
    StartChatSerializer,
    VehicleAcquisitionOutputSerializer,
    VehicleAskSerializer,
    VehicleCostOutputSerializer,
    VehicleLedgerHeaderSerializer,
    VehicleSerializer,
)
from datetime import timedelta

from django.utils import timezone

from .services.ad_copy import generate_ad_copy
from .services.audit import audit_events_snapshot
from .services.chat_engine import ChatEngine
from .permissions import (
    IsAdvisorForSlug,
    IsDealerOwnerAtActiveDealership,
    IsDealerOwnerForAdvisorSlug,
    IsSalesManagerOrOwnerAtActiveDealership,
    ReadOnly,
)
from .services.follow_up import (
    SUPPORTED_CHANNELS as FOLLOW_UP_CHANNELS,
    SUPPORTED_TONES as FOLLOW_UP_TONES,
    generate_follow_up_drafts,
)
from .services.handoff_service import build_handoff_packet, packet_to_text
from .services.lead_service import create_lead_from_session
from .services.manager_chat_response import enforce_coaching_shape
from .services.pipeline import pipeline_snapshot
from .services.tenancy import get_current_dealership, get_default_dealership
from .services.trends import trends_snapshot
from .services.vehicle_assistant import analyze_vehicle, answer_vehicle_question
from .services.vehicle_ledger import add_cost, record_acquisition
from . import services  # noqa: F401 — anchor for service submodule imports below

# Milestone 3 · Increment 6A — condition-report admin API.
from .services import condition_report as condition_report_service
from .services import photo_storage as photo_storage_service
from .services.condition_report import (
    ConditionReportImmutableError,
    CrossTenantConditionReportError,
    PhotoAlreadyAttachedError,
    PhotoMetadataMismatchError,
    PhotoNotYetUploadedError,
)
from .services.photo_storage import (
    InvalidContentTypeError as StorageInvalidContentTypeError,
    InvalidStorageKeyError,
    InvalidTTLError,
    LocalUploadNotAvailableError,
    ObjectStorageError,
)
from decimal import ROUND_HALF_UP, Decimal as _Decimal

# Milestone 2 · Increment 6 — money-projection helper. ORM ``Sum``
# aggregations can strip trailing zeros (a sum of ``Decimal("300.00")``
# rows may return ``Decimal("300")``); quantize every money field the
# ledger endpoints emit to two decimal places so the JSON contract is
# byte-for-byte consistent regardless of ORM backend quirks.
_LEDGER_CENTS = _Decimal("0.01")


def _money_str(value) -> str:
    """Return ``value`` as a two-decimal-place :class:`Decimal` string.

    Used by ``admin_vehicle_ledger`` to project every dollar figure
    consistently. ``ROUND_HALF_UP`` matches the rounding mode the
    M2.4a floor-plan engine uses, keeping consumer expectations
    aligned across the API surface.
    """
    return str(_Decimal(value).quantize(_LEDGER_CENTS, rounding=ROUND_HALF_UP))


DEMO_SOURCE = "demo_seed"


DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 200
MAX_LOGO_UPLOAD_BYTES = 2 * 1024 * 1024
ALLOWED_LOGO_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


def _parse_limit(request, default: int = DEFAULT_LIST_LIMIT) -> int:
    raw = request.query_params.get("limit")
    if not raw:
        return default
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, min(n, MAX_LIST_LIMIT))


@api_view(["POST"])
def start_chat(request):
    serializer = StartChatSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    session = ChatSession.objects.create(
        dealership=get_default_dealership(),
        customer_name=data.get("customer_name", ""),
        customer_email=data.get("customer_email", ""),
        customer_phone=data.get("customer_phone", ""),
    )

    initial_message = (data.get("initial_message") or "").strip()
    response_payload = {
        "session": ChatSessionSerializer(session).data,
        "assistant_message": None,
        "matched_vehicles": [],
    }

    if initial_message:
        engine = ChatEngine(session=session)
        result = engine.handle_user_message(initial_message)
        response_payload["assistant_message"] = ChatMessageSerializer(
            result.assistant_message
        ).data
        response_payload["matched_vehicles"] = VehicleSerializer(
            result.matched_vehicles, many=True
        ).data

    return Response(response_payload, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def send_message(request):
    serializer = ChatMessageInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        session = ChatSession.objects.get(id=data["session_id"])
    except ChatSession.DoesNotExist:
        return Response(
            {"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND
        )

    engine = ChatEngine(session=session)
    result = engine.handle_user_message(data["message"])

    return Response(
        {
            "assistant_message": ChatMessageSerializer(result.assistant_message).data,
            "matched_vehicles": VehicleSerializer(
                result.matched_vehicles, many=True
            ).data,
        }
    )


@api_view(["POST"])
def create_lead(request):
    # Validate and normalize the inbound payload (does not persist).
    serializer = CustomerLeadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = dict(serializer.validated_data)

    session_obj = payload.pop("session", None)
    # PrimaryKeyRelatedField returns the model instance for `session`; coerce
    # interested_vehicles back to id list for the service.
    interested = payload.pop("interested_vehicles", []) or []
    payload["interested_vehicles"] = [
        v.id if hasattr(v, "id") else v for v in interested
    ]

    lead = create_lead_from_session(
        session=session_obj,
        payload=payload,
    )

    return Response(
        CustomerLeadSerializer(lead).data, status=status.HTTP_201_CREATED
    )


# ---- Admin / read endpoints ------------------------------------------------


@api_view(["GET"])
def session_detail(request, session_id):
    try:
        session = ChatSession.objects.prefetch_related("messages").get(id=session_id)
    except ChatSession.DoesNotExist:
        return Response(
            {"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND
        )
    return Response(ChatSessionSerializer(session).data)


_LEAD_SINCE_WINDOWS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

_LEAD_VALID_URGENCIES = {"immediate", "this_week", "this_month", "researching"}

# Milestone 11 · Increment 6 (SESSION_119) — channel filter vocab. Imported
# here rather than at module top to avoid a circular-import surface on the
# M11.1 CustomerLead vocab constants (models.py loads views.py transitively
# via app config, so the local import is fine and the set is a snapshot at
# request time).
from .models import LEAD_CHANNEL_CHOICES  # noqa: E402
_LEAD_VALID_CHANNELS = {key for key, _ in LEAD_CHANNEL_CHOICES}

# Severity ranking for ordering=urgency. Higher number = more urgent;
# unset urgency falls to 0. Tie-break on -created_at handled in caller.
_URGENCY_RANK = {
    "immediate": 4,
    "this_week": 3,
    "this_month": 2,
    "researching": 1,
}


def _apply_lead_filters(qs, request):
    """Manager Phase 1: optional filters for the handoff queue.

    Query params (all optional, garbage values silently ignored):

    - ``handed_off``: ``true`` / ``false``
    - ``urgency``: comma-separated subset of immediate / this_week /
      this_month / researching
    - ``since``: ``24h`` / ``7d`` / ``30d``
    - ``ordering``: ``urgency`` / ``created_at`` (default)
    """
    raw_handed = request.query_params.get("handed_off")
    if raw_handed is not None:
        normalized = raw_handed.strip().lower()
        if normalized in ("true", "1", "yes"):
            qs = qs.filter(handed_off=True)
        elif normalized in ("false", "0", "no"):
            qs = qs.filter(handed_off=False)

    raw_urgency = request.query_params.get("urgency")
    if raw_urgency:
        wanted = {
            tok.strip().lower()
            for tok in raw_urgency.split(",")
            if tok.strip()
        }
        wanted = wanted & _LEAD_VALID_URGENCIES
        if wanted:
            qs = qs.filter(urgency__in=list(wanted))

    raw_since = request.query_params.get("since")
    if raw_since in _LEAD_SINCE_WINDOWS:
        cutoff = timezone.now() - _LEAD_SINCE_WINDOWS[raw_since]
        qs = qs.filter(created_at__gte=cutoff)

    # Milestone 11 · Increment 6 (SESSION_119) — channel filter per
    # SESSION_119 §0.a M11.6 addendum. Same "silently ignore garbage
    # values" posture as the M1 handed_off / urgency filters above.
    raw_channel = request.query_params.get("channel")
    if raw_channel:
        wanted = {
            tok.strip().lower()
            for tok in raw_channel.split(",")
            if tok.strip()
        }
        wanted = wanted & _LEAD_VALID_CHANNELS
        if wanted:
            qs = qs.filter(channel__in=list(wanted))

    return qs


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_lead_list(request):
    dealership = get_current_dealership(request)
    limit = _parse_limit(request)
    base_qs = (
        CustomerLead.objects.filter(dealership=dealership)
        .select_related("session")
        .prefetch_related("interested_vehicles")
    )
    filtered_qs = _apply_lead_filters(base_qs, request)

    ordering = request.query_params.get("ordering", "created_at").strip().lower()
    if ordering == "urgency":
        # Pull the filtered set then sort in Python: severity rank
        # desc, then -created_at. Demo scale; portable across DB
        # backends without case expressions.
        rows = list(filtered_qs)
        rows.sort(
            key=lambda lead: (
                -_URGENCY_RANK.get(lead.urgency, 0),
                -lead.created_at.timestamp(),
            )
        )
        results = rows[:limit]
        total_filtered = len(rows)
    else:
        results = list(filtered_qs.order_by("-created_at")[:limit])
        total_filtered = filtered_qs.count()

    return Response(
        {
            "count": total_filtered,
            "limit": limit,
            "results": AdminLeadListSerializer(results, many=True).data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_chat_session_list(request):
    dealership = get_current_dealership(request)
    limit = _parse_limit(request)
    scoped = ChatSession.objects.filter(dealership=dealership)
    qs = scoped.order_by("-updated_at")[:limit]
    return Response(
        {
            "count": scoped.count(),
            "limit": limit,
            "results": AdminChatSessionListSerializer(qs, many=True).data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_trends(request):
    return Response(trends_snapshot(dealership=get_current_dealership(request)))


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_pipeline(request):
    """Manager Phase 2: sales pipeline + demand-vs-supply + recommended actions.

    Pure read aggregate over CustomerLead and Vehicle. No schema changes,
    no chat-engine touches. Milestone 1 · Increment 4D — tenant-scoped
    via ``dealership=`` passed into :func:`pipeline_snapshot`.
    """
    return Response(pipeline_snapshot(dealership=get_current_dealership(request)))


@api_view(["POST"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_ad_copy(request):
    """Manager Phase 3: generate 2–3 ad-copy variants for an inventory or
    marketing recommendation. Read-only with respect to system state — no
    persistence, no auto-publish. Variants pass through the same post-LLM
    safety scrub stack the chat path uses.

    Request body::

        {
          "recommendation": {
            "id": "...",          # required
            "category": "...",    # required, must be inventory|marketing
            "title": "...",
            "explanation": "...",
            "action_text": "...",
            "evidence": {...},
            "cta": {...}          # optional, used to derive band edges
          },
          "vehicle_id": 123        # optional
        }
    """
    body = request.data or {}
    recommendation = body.get("recommendation")
    raw_vehicle_id = body.get("vehicle_id")
    vehicle_id: Optional[int]
    if raw_vehicle_id in (None, ""):
        vehicle_id = None
    else:
        try:
            vehicle_id = int(raw_vehicle_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "vehicle_id must be an integer when provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    try:
        result = generate_ad_copy(
            recommendation=recommendation,
            vehicle_id=vehicle_id,
            dealership=get_current_dealership(request),
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )

    payload = {
        "recommendation_id": result.recommendation_id,
        "variants": result.variants,
        "warnings": result.warnings,
        "vehicles_used": VehicleSerializer(
            result.vehicles_used, many=True
        ).data,
    }
    return Response(payload)


# ---- Manager Phase 4: Salespeople + assignment + advisor workspace --------


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_salespeople(request):
    """List all salespeople (active and inactive). Used by the manager
    dashboard and the assignment dropdown. Phase 4 keeps inactive rows
    visible so historical assignments still resolve, but the frontend
    filters them out of the assignment menu via the ``is_active`` flag.

    Milestone 1 · Increment 4D — tenant-scoped. Admin at Dealership A
    only sees Dealership A's salespeople.
    """
    dealership = get_current_dealership(request)
    qs = Salesperson.objects.filter(dealership=dealership).order_by(
        "-is_active", "name"
    )
    only_active = request.query_params.get("active")
    if only_active in ("true", "1", "yes"):
        qs = qs.filter(is_active=True)
    return Response(
        {
            "count": qs.count(),
            "results": SalespersonAdminSerializer(qs, many=True).data,
        }
    )


@api_view(["GET"])
def public_salespeople(request):
    """Public-facing 'Meet the team' list. Active salespeople only;
    contact details (phone/email/bio) are intentionally omitted."""
    qs = Salesperson.objects.filter(is_active=True).order_by("name")
    return Response(
        {
            "count": qs.count(),
            "results": SalespersonPublicSerializer(qs, many=True).data,
        }
    )


@api_view(["GET"])
def public_salesperson_detail(request, slug):
    """Public-facing single-salesperson detail (active only)."""
    try:
        sp = Salesperson.objects.get(slug=slug, is_active=True)
    except Salesperson.DoesNotExist:
        return Response(
            {"detail": "Salesperson not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(SalespersonPublicSerializer(sp).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_lead_assign(request, lead_id):
    """Assign a lead to a salesperson, or clear assignment when
    ``salesperson_id`` is null.

    Per the locked Phase 4 decisions: cannot assign to an inactive
    salesperson. Already-assigned leads are silently re-assigned.

    Milestone 1 · Increment 4D — both the lead and the target
    salesperson must belong to the caller's active dealership. An admin
    at Dealership A cannot reassign a Dealership B lead, and cannot
    assign any lead to a Dealership B salesperson.
    """
    dealership = get_current_dealership(request)
    try:
        lead = CustomerLead.objects.get(pk=lead_id, dealership=dealership)
    except CustomerLead.DoesNotExist:
        return Response(
            {"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND
        )

    serializer = AssignLeadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    salesperson_id = serializer.validated_data.get("salesperson_id")

    if salesperson_id is None:
        lead.assigned_to = None
        lead.assigned_at = None
    else:
        try:
            sp = Salesperson.objects.get(pk=salesperson_id, dealership=dealership)
        except Salesperson.DoesNotExist:
            return Response(
                {"detail": "Salesperson not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not sp.is_active:
            return Response(
                {"detail": "Cannot assign to an inactive salesperson."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        lead.assigned_to = sp
        lead.assigned_at = timezone.now()
    lead.save(update_fields=["assigned_to", "assigned_at", "updated_at"])

    return Response(AdminLeadListSerializer(lead).data)


_WORKSPACE_RECENT_DAYS = 30


@api_view(["GET"])
@permission_classes(
    [IsAuthenticated & (IsAdvisorForSlug | IsDealerOwnerForAdvisorSlug)]
)
def advisor_workspace(request, slug):
    """Salesperson workspace: profile + open leads + contacted leads.

    Open = assigned + handed_off=false.
    Contacted = assigned + handed_off=true within the last 30 days.

    Milestone 1 · Increment 4C — access is real DRF authorization now.
    Authenticated advisor for this slug OR authenticated dealer_owner
    at the same dealership can view. Everyone else gets 401 (unauth)
    or 403 (auth but not authorized). URL shape and response body
    preserved; the slug-obscurity mechanism (previously documented
    here as v1) is replaced. Post-permission 404 still fires when a
    legitimately-authorized caller hits a slug whose Salesperson is
    inactive — that's the same data-lifecycle check as before.
    """
    try:
        sp = Salesperson.objects.get(slug=slug, is_active=True)
    except Salesperson.DoesNotExist:
        return Response(
            {"detail": "Advisor not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    base = (
        CustomerLead.objects.filter(assigned_to=sp)
        .select_related("session", "assigned_to")
        .prefetch_related("interested_vehicles")
    )
    open_qs = base.filter(handed_off=False).order_by(
        "-assigned_at", "-created_at"
    )
    cutoff = timezone.now() - timedelta(days=_WORKSPACE_RECENT_DAYS)
    contacted_qs = base.filter(
        handed_off=True, updated_at__gte=cutoff
    ).order_by("-updated_at")

    return Response(
        {
            "salesperson": SalespersonPublicSerializer(sp).data,
            "open_leads": AdminLeadListSerializer(
                list(open_qs), many=True
            ).data,
            "contacted_leads": AdminLeadListSerializer(
                list(contacted_qs), many=True
            ).data,
            "counts": {
                "open": open_qs.count(),
                "contacted": contacted_qs.count(),
            },
        }
    )


@api_view(["POST"])
@permission_classes(
    [IsAuthenticated & (IsAdvisorForSlug | IsDealerOwnerForAdvisorSlug)]
)
def advisor_follow_up(request, slug, lead_id):
    """Generate AI follow-up drafts for an assigned lead.

    Body::

        {
          "channel": "sms" | "email",     # default sms
          "tone":    "warm" | "direct"    # default warm
        }

    Milestone 1 · Increment 4C — authorization is DRF-based (see
    :func:`advisor_workspace`). The 403 lead-ownership check below
    (``lead.assigned_to_id != sp.pk``) is preserved verbatim — it is
    the data-scoping layer's manifestation on this endpoint and
    remains distinct from the authorization layer. A dealer_owner
    accessing an advisor's URL still fails the lead-ownership check
    for leads not assigned to that advisor, which is the correct
    behavior: owners can *see* an advisor's queue via the workspace
    endpoint, but drafting on behalf of an advisor is scoped to that
    advisor's own leads.
    """
    try:
        sp = Salesperson.objects.get(slug=slug, is_active=True)
    except Salesperson.DoesNotExist:
        return Response(
            {"detail": "Advisor not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        lead = CustomerLead.objects.prefetch_related(
            "interested_vehicles"
        ).get(pk=lead_id)
    except CustomerLead.DoesNotExist:
        return Response(
            {"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND
        )
    if lead.assigned_to_id != sp.pk:
        return Response(
            {"detail": "Lead is not assigned to this advisor."},
            status=status.HTTP_403_FORBIDDEN,
        )

    body = request.data or {}
    channel = (body.get("channel") or "sms").strip().lower()
    tone = (body.get("tone") or "warm").strip().lower()
    if channel not in FOLLOW_UP_CHANNELS:
        return Response(
            {"detail": f"channel must be one of {sorted(FOLLOW_UP_CHANNELS)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if tone not in FOLLOW_UP_TONES:
        return Response(
            {"detail": f"tone must be one of {sorted(FOLLOW_UP_TONES)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    result = generate_follow_up_drafts(
        lead=lead,
        advisor=sp,
        channel=channel,
        tone=tone,
    )
    return Response(
        {
            "lead_id": result.lead_id,
            "salesperson_slug": result.salesperson_slug,
            "channel": channel,
            "tone": tone,
            "drafts": result.drafts,
            "warnings": result.warnings,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_audit_events(request):
    since = request.query_params.get("since", "24h")
    raw_limit = request.query_params.get("limit")
    try:
        recent_limit = max(1, min(int(raw_limit), 200)) if raw_limit else 50
    except (TypeError, ValueError):
        recent_limit = 50
    return Response(
        audit_events_snapshot(
            since=since,
            recent_limit=recent_limit,
            dealership=get_current_dealership(request),
        )
    )


# ---- Vehicle detail / vehicle ask ------------------------------------------


def _profile_from_request(request) -> dict:
    """Pull customer financial signals from query params or body for the
    vehicle detail/ask endpoints. Falls back to attached session profile."""
    profile: dict = {}
    src = request.query_params if request.method == "GET" else request.data
    target = src.get("target_monthly_payment")
    down = src.get("down_payment")
    if target not in (None, ""):
        profile["target_monthly_payment"] = target
    if down not in (None, ""):
        profile["down_payment"] = down
    return profile


@api_view(["GET"])
def vehicle_detail(request, vehicle_id):
    # Milestone 6 · Increment 5 (SESSION_086) — SESSION_075 §5.i
    # truthful-language refactor. The stock-specific customer
    # lookup path now requires both ``stage='frontline'`` AND a
    # published :class:`VehicleListing`. Non-visible vehicles
    # surface as HTTP 404 with the truthful copy per §5.i rather
    # than exposing internals (recon, stage, ETA, vendor, etc.).
    from .services.chat_engine import (
        CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY,
        customer_lookup_visible_vehicle_by_id,
    )

    vehicle = customer_lookup_visible_vehicle_by_id(vehicle_id)
    if vehicle is None:
        return Response(
            {"detail": CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY},
            status=status.HTTP_404_NOT_FOUND,
        )

    profile = _profile_from_request(request)
    session_id = request.query_params.get("session_id")
    if session_id and not profile:
        try:
            session = ChatSession.objects.get(id=session_id)
            profile = dict(session.extracted_profile or {})
        except ChatSession.DoesNotExist:
            pass

    analysis = analyze_vehicle(vehicle, profile=profile)
    return Response(
        {
            "vehicle": VehicleSerializer(vehicle).data,
            "payment_estimates": analysis.payment_estimates,
            "affordability_notes": analysis.affordability_notes,
            "similar_vehicles": VehicleSerializer(
                analysis.similar_vehicles, many=True
            ).data,
        }
    )


@api_view(["POST"])
def vehicle_ask(request, vehicle_id):
    # Milestone 6 · Increment 5 (SESSION_086) — SESSION_075 §5.i
    # truthful-language refactor. See ``vehicle_detail`` above.
    from .services.chat_engine import (
        CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY,
        customer_lookup_visible_vehicle_by_id,
    )

    vehicle = customer_lookup_visible_vehicle_by_id(vehicle_id)
    if vehicle is None:
        return Response(
            {"detail": CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = VehicleAskSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    session = None
    if data.get("session_id"):
        try:
            session = ChatSession.objects.get(id=data["session_id"])
        except ChatSession.DoesNotExist:
            session = None

    profile = {}
    if session is not None:
        profile = dict(session.extracted_profile or {})
    if data.get("target_monthly_payment") is not None:
        profile["target_monthly_payment"] = data["target_monthly_payment"]
    if data.get("down_payment") is not None:
        profile["down_payment"] = data["down_payment"]

    answer = answer_vehicle_question(
        vehicle=vehicle,
        question=data["question"],
        profile=profile,
        session=session,
    )

    analysis = analyze_vehicle(vehicle, profile=profile)
    return Response(
        {
            "vehicle": VehicleSerializer(vehicle).data,
            "answer": answer,
            "payment_estimates": analysis.payment_estimates,
            "affordability_notes": analysis.affordability_notes,
            "similar_vehicles": VehicleSerializer(
                analysis.similar_vehicles, many=True
            ).data,
        }
    )


# ---- Lead detail / handoff -------------------------------------------------


def _serialize_lead_messages(lead: CustomerLead) -> list:
    if lead.session_id is None:
        return []
    qs = ChatMessage.objects.filter(session_id=lead.session_id).order_by("created_at")
    return ChatMessageSerializer(qs, many=True).data


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_lead_detail(request, lead_id):
    dealership = get_current_dealership(request)
    try:
        lead = (
            CustomerLead.objects.filter(dealership=dealership)
            .select_related("session")
            .prefetch_related("interested_vehicles")
            .get(id=lead_id)
        )
    except CustomerLead.DoesNotExist:
        return Response(
            {"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND
        )

    return Response(
        {
            "lead": CustomerLeadSerializer(lead).data,
            "interested_vehicles": VehicleSerializer(
                lead.interested_vehicles.all(), many=True
            ).data,
            "session_profile": (
                lead.session.extracted_profile if lead.session else {}
            ),
            "messages": _serialize_lead_messages(lead),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_lead_handoff(request, lead_id):
    dealership = get_current_dealership(request)
    try:
        lead = (
            CustomerLead.objects.filter(dealership=dealership)
            .prefetch_related("interested_vehicles")
            .get(id=lead_id)
        )
    except CustomerLead.DoesNotExist:
        return Response(
            {"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND
        )

    packet = build_handoff_packet(lead)

    if request.data.get("mark_handed_off"):
        if not lead.handed_off:
            lead.handed_off = True
            lead.save(update_fields=["handed_off", "updated_at"])

    return Response({**packet, "text": packet_to_text(packet), "handed_off": lead.handed_off})


# ---- Demo reset ------------------------------------------------------------


@api_view(["POST"])
def demo_reset(request):
    """Wipe demo conversational state so a fresh demo can run.

    Default behavior:
        - Delete all chat sessions, chat messages, and customer leads.
        - Reload the bundled demo vehicles.
        - LEAVE imported (non-demo) vehicles alone.

    Explicit opt-ins (request body, JSON):
        - reload_demo_vehicles (bool, default true)
        - delete_imported_vehicles (bool, default false) — drops vehicles whose
          source != 'demo_seed'. Use with care.
    """
    body = request.data or {}
    reload_demo_vehicles = bool(body.get("reload_demo_vehicles", True))
    delete_imported_vehicles = bool(body.get("delete_imported_vehicles", False))

    counts = {
        "chat_messages": ChatMessage.objects.count(),
        "chat_sessions": ChatSession.objects.count(),
        "leads": CustomerLead.objects.count(),
    }
    CustomerLead.objects.all().delete()
    ChatMessage.objects.all().delete()
    ChatSession.objects.all().delete()

    deleted_imported = 0
    if delete_imported_vehicles:
        deleted_imported = (
            Vehicle.objects.exclude(source=DEMO_SOURCE).count()
        )
        Vehicle.objects.exclude(source=DEMO_SOURCE).delete()

    reloaded_count = 0
    if reload_demo_vehicles:
        from io import StringIO

        call_command("seed_demo_vehicles", stdout=StringIO())
        reloaded_count = Vehicle.objects.filter(source=DEMO_SOURCE).count()

    return Response(
        {
            "ok": True,
            "cleared": counts,
            "deleted_imported_vehicles": deleted_imported,
            "demo_vehicles": reloaded_count,
            "imported_vehicles_remaining": (
                Vehicle.objects.exclude(source=DEMO_SOURCE).count()
            ),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def demo_load_scenarios(request):
    """Seed (or re-seed) the bundled demo scenarios. Wraps
    `python manage.py seed_demo_scenarios`."""
    from io import StringIO

    body = request.data or {}
    reset = bool(body.get("reset", False))

    out = StringIO()
    args = ["seed_demo_scenarios"]
    if reset:
        args.append("--reset")
    call_command(*args, stdout=out)

    return Response(
        {
            "ok": True,
            "reset": reset,
            "chat_sessions": ChatSession.objects.count(),
            "leads": CustomerLead.objects.count(),
            "stdout": out.getvalue(),
        },
        status=status.HTTP_200_OK,
    )


# ---- Manager chat tester (SESSION_010) -------------------------------------


@api_view(["POST"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def manager_chat(request):
    """SESSION_010: stateless manager-side chat tester.

    Lets a manager preview how the configured sales assistant responds —
    voice, banned-phrase scrubbing, disclaimer behavior — without
    polluting a real customer session. Each request runs in a fresh
    ephemeral ``ChatSession`` tagged ``channel=manager_test``; the
    existing chat engine handles everything (including SESSION_009
    onboarding overrides), so behavior matches what real customers see.

    Returns ``{"reply": <assistant text>}``. No vehicle cards — the
    tester is voice-and-tone focused, and including matched_vehicles
    here would couple the manager UI to inventory shape changes.
    """
    serializer = ManagerChatInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    message = (data.get("message") or "").strip()
    if not message:
        return Response(
            {"detail": "message is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session = ChatSession.objects.create(
        dealership=get_current_dealership(request),
        metadata={"channel": "manager_test"},
    )
    engine = ChatEngine(session=session)
    result = engine.handle_user_message(message)

    # SESSION_010 hotfix + SESSION_011 structural enforcement.
    # The chat engine already received MANAGER_COACHING_HINT via the
    # manager_test channel and applied SESSION_009 onboarding overrides
    # (banned-phrase scrub + tone overrides + disclaimer). This call
    # adds a final structural pass: it strips known-bad sentences via
    # the existing card-implying scrub AND, if the surviving text
    # impersonates the customer-facing assistant or lacks a coaching
    # frame entirely, replaces it with a context-aware coaching
    # fallback built from the customer's message. Customer-facing chat
    # is unaffected — the enforcer lives in this view only.
    reply_text, _action = enforce_coaching_shape(
        result.assistant_message.content,
        customer_message=message,
    )

    return Response(
        {"reply": reply_text},
        status=status.HTTP_200_OK,
    )


# ---- Onboarding (SESSION_008) ----------------------------------------------


@api_view(["GET", "PUT", "PATCH"])
@permission_classes(
    [ReadOnly | (IsAuthenticated & IsDealerOwnerAtActiveDealership)]
)
def onboarding_profile(request):
    """Singleton dealer onboarding profile.

    GET: returns the current profile, or the default shape if none exists
        yet. Always 200 — the page can render with defaults pre-filled.
        Public (branding must render on unauthenticated pages per
        MILESTONE_1_PLANNING.md §3 compatibility checklist).
    PUT/PATCH: upserts the singleton row. PUT requires the full payload
        (validates every field). PATCH allows partial updates and only
        validates the keys present in the body.

    Milestone 1 · Increment 4D — mutation requires ``dealer_owner`` at
    the caller's active dealership. GET stays public because
    ``useBrand()`` renders on public pages that never authenticate.
    """
    dealership = get_current_dealership(request)
    profile = (
        DealerOnboardingProfile.objects.filter(dealership=dealership).first()
    )

    if request.method == "GET":
        if profile is None:
            return Response(ONBOARDING_DEFAULTS)
        return Response(DealerOnboardingProfileSerializer(profile).data)

    partial = request.method == "PATCH"
    if profile is None:
        # Seed creation with defaults so PATCH (partial) lands cleanly even
        # when only some fields are supplied. PUT will validate every key
        # the serializer requires (none are required by default since all
        # CharField/TextField are blank=True and BooleanField has default).
        serializer = DealerOnboardingProfileSerializer(
            data={**ONBOARDING_DEFAULTS, **request.data}
        )
    else:
        serializer = DealerOnboardingProfileSerializer(
            profile, data=request.data, partial=partial
        )
    serializer.is_valid(raise_exception=True)
    profile = serializer.save(dealership=dealership)
    return Response(
        DealerOnboardingProfileSerializer(profile).data, status=status.HTTP_200_OK
    )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated & IsDealerOwnerAtActiveDealership])
def onboarding_logo_upload(request):
    """Upload a dealer logo and store its served URL in ``logo_url``.

    This keeps ``logo_url`` as the single source of truth for every brand
    surface. Hosted URL paste still uses the JSON profile endpoint.

    Milestone 1 · Increment 4D — requires ``dealer_owner`` at the
    caller's active dealership.
    """
    upload = request.FILES.get("logo")
    if upload is None:
        return Response(
            {"detail": "Upload a file field named 'logo'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    content_type = (upload.content_type or "").lower()
    extension = ALLOWED_LOGO_CONTENT_TYPES.get(content_type)
    if extension is None:
        return Response(
            {
                "detail": (
                    "Unsupported logo type. Use JPG, PNG, WEBP, or SVG."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if upload.size > MAX_LOGO_UPLOAD_BYTES:
        return Response(
            {"detail": "Logo file must be 2 MB or smaller."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    original_suffix = Path(upload.name).suffix.lower()
    if original_suffix in {".jpg", ".jpeg", ".png", ".webp", ".svg"}:
        extension = ".jpg" if original_suffix == ".jpeg" else original_suffix
    path = default_storage.save(
        f"dealer-logos/{uuid4().hex}{extension}",
        upload,
    )
    logo_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{path}")

    dealership = get_current_dealership(request)
    profile = (
        DealerOnboardingProfile.objects.filter(dealership=dealership).first()
    )
    if profile is None:
        serializer = DealerOnboardingProfileSerializer(
            data={**ONBOARDING_DEFAULTS, "logo_url": logo_url}
        )
    else:
        serializer = DealerOnboardingProfileSerializer(
            profile, data={"logo_url": logo_url}, partial=True
        )
    serializer.is_valid(raise_exception=True)
    profile = serializer.save(dealership=dealership)
    return Response(
        DealerOnboardingProfileSerializer(profile).data, status=status.HTTP_200_OK
    )


# ---- Milestone 1 · Increment 4E — browser auth flow -----------------------
#
# Three endpoints implementing the minimal browser-side session flow:
#
#   POST /api/dealer-ai/auth/login/   — authenticate + open Django session
#   POST /api/dealer-ai/auth/logout/  — close the Django session (idempotent)
#   GET  /api/dealer-ai/auth/me/      — current session probe + CSRF primer
#
# Design constraints (see docs/roadmap/AUTHENTICATION_MODEL.md §2):
#
# 1. Session cookies (Django session middleware) drive the browser flow.
#    TokenAuthentication remains configured for non-browser clients but
#    the browser never stores a DRF token in localStorage.
# 2. Login errors return a generic message — never confirm username
#    existence.
# 3. Logout is safe to call when already anonymous — the frontend
#    invokes it on ambiguous state without needing to check first.
# 4. `/me/` uses `@ensure_csrf_cookie` so the very first bootstrap
#    call sets the `csrftoken` cookie the frontend needs for the
#    subsequent login POST.
# 5. `/me/` returns identity + active-dealership + roles minimally.
#    It resolves both via the existing `services.tenancy` primitives —
#    no parallel identity resolver.


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_login(request):
    """Authenticate a user + open a Django session.

    Body: ``{"username": "...", "password": "..."}``. Returns 200 with
    the same shape as :func:`auth_me` when successful, 400 for a
    missing field, 401 with a generic message otherwise.
    """
    body = request.data or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        return Response(
            {"detail": "Username and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=username, password=password)
    if user is None:
        # Generic message — never distinguish "no such user" from
        # "wrong password". This is a login-CSRF and enumeration
        # defense at once.
        return Response(
            {"detail": "Invalid credentials."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    django_login(request, user)
    return Response(_me_payload(request), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_logout(request):
    """End the active Django session.

    Idempotent: returns 200 whether or not a session existed. The
    frontend can call this on ambiguous state (e.g. session expired
    server-side) without a pre-flight check.
    """
    django_logout(request)
    return Response({"detail": "Signed out."}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def auth_me(request):
    """Return the current session state.

    Also primes the ``csrftoken`` cookie via ``@ensure_csrf_cookie`` —
    the frontend calls this once on boot so subsequent unsafe requests
    (login, logout, admin mutations) have the token to include in
    the ``X-CSRFToken`` header.

    Response shape is intentionally minimal (username +
    active dealership + roles) — enough for the frontend to route,
    not enough to become a general user-profile endpoint.
    """
    return Response(_me_payload(request), status=status.HTTP_200_OK)


def _me_payload(request) -> dict:
    """Compose the ``/auth/me/`` response body.

    Delegates to :func:`services.tenancy.get_current_dealership` for
    the active dealership and to the membership model for roles.
    Never invents parallel resolvers; downstream code changes here
    only when those primitives change.
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return {"authenticated": False}

    dealership = get_current_dealership(request)
    # Pull every role the user holds at the active dealership. Multiple
    # concurrent roles at one dealership are supported per the 4A
    # design note.
    from .models import UserDealershipRole  # local import to avoid cycles

    roles = sorted(
        UserDealershipRole.objects.filter(
            user=user, dealership=dealership
        ).values_list("role", flat=True)
    )

    salesperson = getattr(user, "salesperson", None)
    return {
        "authenticated": True,
        "user": {
            "id": user.pk,
            "username": user.get_username(),
            "display_name": (user.get_full_name() or user.get_username()),
            "salesperson_slug": salesperson.slug if salesperson else None,
        },
        "dealership": {
            "id": dealership.pk,
            "slug": dealership.slug,
            "name": dealership.name,
        },
        "roles": roles,
    }


# ---- Milestone 2 · Increment 6 — Vehicle investment ledger admin API -----
#
# Three tenant-scoped admin endpoints under
# ``/api/dealer-ai/admin/vehicles/<stock_number>/``. All three:
#
# - Compose ``[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]``.
#   (Reuses the M1 · Increment 4D permission class unchanged.
#   Recon-manager access is deferred to Milestone 4 per M2 §5.)
# - Resolve ``dealership = get_current_dealership(request)`` once at
#   the top per ``AUTHENTICATION_MODEL.md`` §8b.
# - Look up the vehicle via
#   ``Vehicle.objects.filter(dealership=dealership).get(
#   stock_number=<url_kwarg>)`` — cross-tenant AND nonexistent
#   ``stock_number`` both raise ``DoesNotExist`` and return 404
#   (identical response so existence is not leaked, mirroring
#   ``AdminLeadDetailFailsClosedAcrossTenants``).
# - Write via the ledger service — ``record_acquisition`` and
#   ``add_cost`` — NEVER through ``VehicleAcquisition.objects.create``
#   or ``VehicleCost.objects.create`` directly. Preserves the
#   cross-tenant guard + ``full_clean`` invariants of the M2.2
#   service.
#
# Response shape locked so M2.7 UI can consume without reshaping
# the backend. See ``test_admin_vehicle_ledger.py`` for the
# contract tests.


@api_view(["GET"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_vehicle_ledger(request, stock_number):
    """Return the full ledger view for one vehicle.

    Response shape::

        {
          "vehicle":     {stock_number, vin, year, make, model,
                          trim, price, display_name},
          "acquisition": <VehicleAcquisition projection> | null,
          "costs":       [<VehicleCost projection>, ...],  # chronological
          "totals":      {acquisition_total, flooring_total, recon_total,
                          administrative_total, photography_total,
                          actual_cost_total, estimated_cost_total,
                          total_investment, projected_total_investment},
          "days_in_inventory": int | null,
          "projected_gross":   str(Decimal)   # asking price - total_investment
        }

    All money fields serialize as strings so JavaScript's ``Number``
    cannot silently truncate Decimal precision.

    Cost ordering: ascending ``incurred_at`` with ``pk`` tie-break —
    chronological, so the UI can render a running-total column
    without re-sorting. Locked by
    ``test_admin_vehicle_ledger.ReadLedgerCostOrderingIsDeterministic``.
    """
    dealership = get_current_dealership(request)
    try:
        vehicle = (
            Vehicle.objects.filter(dealership=dealership)
            .select_related("acquisition")
            .get(stock_number=stock_number)
        )
    except Vehicle.DoesNotExist:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Prime the cached ledger_totals once — every totals field
    # below reads from the cache, avoiding double aggregation.
    totals = vehicle.ledger_totals

    # Cost list — chronological ascending. Deterministic tie-break
    # on ``pk`` for rows with the same ``incurred_at`` timestamp
    # (common for accrual runs where every row for a batch shares
    # the same as_of moment).
    costs = list(
        VehicleCost.objects.filter(vehicle=vehicle, dealership=dealership)
        .order_by("incurred_at", "pk")
    )

    # Acquisition — OneToOne, may not exist yet.
    try:
        acquisition = vehicle.acquisition
    except VehicleAcquisition.DoesNotExist:
        acquisition = None

    # projected_gross = asking price - money already committed.
    # Trivial arithmetic in the projection layer (no new business
    # logic on Vehicle) — Vehicle.price + total_investment are
    # both Decimals so subtraction preserves precision.
    projected_gross = vehicle.price - totals.total_investment

    return Response(
        {
            "vehicle": VehicleLedgerHeaderSerializer(vehicle).data,
            "acquisition": (
                VehicleAcquisitionOutputSerializer(acquisition).data
                if acquisition is not None
                else None
            ),
            "costs": VehicleCostOutputSerializer(costs, many=True).data,
            "totals": {
                "acquisition_total": _money_str(totals.acquisition_total),
                "flooring_total": _money_str(totals.flooring_total),
                "recon_total": _money_str(totals.recon_total),
                "administrative_total": _money_str(totals.administrative_total),
                "photography_total": _money_str(totals.photography_total),
                "actual_cost_total": _money_str(totals.actual_cost_total),
                "estimated_cost_total": _money_str(totals.estimated_cost_total),
                "total_investment": _money_str(totals.total_investment),
                "projected_total_investment": _money_str(
                    totals.projected_total_investment
                ),
            },
            "days_in_inventory": vehicle.days_in_inventory,
            "projected_gross": _money_str(projected_gross),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_vehicle_acquisition_upsert(request, stock_number):
    """Create or update the vehicle's acquisition record.

    Wraps :func:`services.vehicle_ledger.record_acquisition` — never
    writes to ``VehicleAcquisition`` directly. Returns
    ``{acquisition: <projection>, created: bool}``. Status code
    reflects the ``created`` flag (201 on create, 200 on update).
    """
    dealership = get_current_dealership(request)
    try:
        vehicle = Vehicle.objects.filter(dealership=dealership).get(
            stock_number=stock_number
        )
    except Vehicle.DoesNotExist:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = AcquisitionUpsertRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    acquisition, created = record_acquisition(
        vehicle,
        dealership=dealership,
        **payload,
    )
    return Response(
        {
            "acquisition": VehicleAcquisitionOutputSerializer(
                acquisition
            ).data,
            "created": created,
        },
        status=(
            status.HTTP_201_CREATED if created else status.HTTP_200_OK
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership])
def admin_vehicle_cost_create(request, stock_number):
    """Post one immutable cost row against the vehicle.

    Wraps :func:`services.vehicle_ledger.add_cost` — never writes
    to ``VehicleCost`` directly. Returns
    ``{cost: <projection>}`` with 201.

    ``created_by`` is attached from ``request.user`` — client-
    supplied attribution is not accepted (would let an
    authenticated operator forge cost authorship).

    Signed amounts pass through: negative values are the reversing-
    entry pattern (see ``ACCOUNTING_DEPARTMENT_MAPPING.md`` §2.11).
    No update or delete endpoint exists in v1; corrections happen
    via reversing entries whose ``reference`` points at the
    original row.
    """
    dealership = get_current_dealership(request)
    try:
        vehicle = Vehicle.objects.filter(dealership=dealership).get(
            stock_number=stock_number
        )
    except Vehicle.DoesNotExist:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = CostCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    try:
        cost = add_cost(
            vehicle,
            dealership=dealership,
            created_by=request.user,
            **payload,
        )
    except ValueError as exc:
        # Defense-in-depth: the ``ChoiceField`` on the serializer
        # already rejects invalid categories with a 400 field-level
        # error, so ValueError from ``add_cost``'s category check
        # should never surface here in practice. If it ever does
        # (e.g. a future serializer refactor loosens validation),
        # return a clean 400 rather than a 500.
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {"cost": VehicleCostOutputSerializer(cost).data},
        status=status.HTTP_201_CREATED,
    )


# =========================================================================
# Milestone 3 · Increment 6A — condition-report admin API (core surface)
# =========================================================================
#
# Six endpoints for reading + writing the condition-report business
# state. Photo endpoints (request-upload, attach, delete, local-mode
# receiver) are queued for Increment 6B — see planning §7 M3.6.
#
# Every endpoint composes:
#     [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]
# — same permission class M2.6 established. No recon-manager role in
# M3 (roadmap deferred to M4).
#
# Every endpoint:
#   - Resolves ``dealership = get_current_dealership(request)`` once
#     at top.
#   - Scopes ``Vehicle`` lookup to that dealership; ``get()``-based
#     lookup that raises ``DoesNotExist`` → 404.
#   - Scopes report / finding lookups explicitly to that dealership;
#     cross-tenant IDs fail closed with 404 (never 403 — never leak
#     whether the resource exists in another tenant).
#   - Passes ``dealership=`` into every service call (never relies on
#     the pre-save autofill signal).
#   - Server-owns ``dealership``, ``authored_by``, ``status``,
#     ``completed_at``; refuses client-supplied values for these
#     fields (serializer whitelist enforces).
#
# Domain-error → HTTP mapping (locked by focused tests):
#
#   CrossTenantConditionReportError → 404
#   ConditionReportImmutableError    → 409 Conflict
#   ValueError (invalid category/severity from service) → 400
#   ValidationError (model full_clean) → 400 with message_dict
#
# Photo-specific errors
# (PhotoNotYetUploadedError, PhotoMetadataMismatchError,
# PhotoAlreadyAttachedError, ObjectStorageError) are wired in M3.6B
# alongside the photo endpoints.
#
# Response projections are inline dict builders (matches the M2.6
# ``admin_vehicle_ledger`` pattern). Photo projections include
# ``public_id`` + minimal metadata + signed read URL; ``storage_key``
# is NEVER exposed.


def _project_photo(photo) -> dict:
    """Response projection for a :class:`ConditionFindingPhoto`.

    ``storage_key`` is deliberately absent — external identity is
    ``public_id`` (M3.1 refinement). Signed read URL comes from
    :func:`photo_storage.generate_read_url`; the URL is short-TTL
    (≤ 900 s per M3.4 cap) and expires_at is included so the UI can
    schedule a refresh if needed.

    In local dev mode the read URL is a
    ``LOCAL_READ_URL_MARKER`` prefix (non-URL scheme) — the UI must
    detect the prefix and resolve through an authenticated Django
    download route (deferred to M3.7 or a later increment).
    """
    signed_url = photo_storage_service.generate_read_url(
        storage_key=photo.storage_key
    )
    expires_at = timezone.now() + timedelta(seconds=900)
    return {
        "public_id": str(photo.public_id),
        "content_type": photo.content_type,
        "size_bytes": photo.size_bytes,
        "caption": photo.caption,
        "uploaded_by": (
            photo.uploaded_by.username
            if photo.uploaded_by_id is not None
            else None
        ),
        "created_at": photo.created_at,
        "signed_read_url": signed_url,
        "read_url_expires_at": expires_at,
    }


def _project_finding(finding) -> dict:
    """Response projection for a :class:`ConditionFinding`.

    ``estimated_cost`` serializes as a two-decimal string (or
    ``null``) so JavaScript's ``Number`` type cannot silently
    truncate. Photos ordered by ``created_at`` (model Meta ordering).
    """
    if finding.estimated_cost is None:
        cost_repr = None
    else:
        cost_repr = str(
            finding.estimated_cost.quantize(
                _LEDGER_CENTS, rounding=ROUND_HALF_UP
            )
        )
    return {
        "id": finding.id,
        "category": finding.category,
        "category_display": finding.get_category_display(),
        "severity": finding.severity,
        "severity_display": finding.get_severity_display(),
        "description": finding.description,
        "estimated_cost": cost_repr,
        "notes": finding.notes,
        "created_at": finding.created_at,
        "updated_at": finding.updated_at,
        "photos": [_project_photo(p) for p in finding.photos.all()],
    }


def _project_report(report) -> dict:
    """Response projection for a :class:`ConditionReport`.

    ``findings`` prefetched via ``select_related`` /
    ``prefetch_related`` at query time; this projection does not
    trigger additional queries as long as callers primed the
    related-object cache correctly.
    """
    return {
        "id": report.id,
        "status": report.status,
        "status_display": report.get_status_display(),
        "inspector_name": report.inspector_name,
        "inspected_at": report.inspected_at,
        "mileage_at_inspection": report.mileage_at_inspection,
        "completed_at": report.completed_at,
        "notes": report.notes,
        "authored_by": (
            report.authored_by.username
            if report.authored_by_id is not None
            else None
        ),
        "created_at": report.created_at,
        "updated_at": report.updated_at,
        "findings": [
            _project_finding(f)
            for f in report.findings.all()
        ],
    }


def _lookup_vehicle_or_404(dealership, stock_number):
    """Tenant-scoped Vehicle lookup — 404 on both nonexistent and
    cross-tenant. Never leak whether a stock_number exists in
    another dealership."""
    try:
        return Vehicle.objects.filter(dealership=dealership).get(
            stock_number=stock_number
        )
    except Vehicle.DoesNotExist:
        return None


def _lookup_report_or_404(dealership, vehicle, report_id):
    """Tenant + vehicle scoped ConditionReport lookup. 404 on any
    miss — cross-tenant, wrong-vehicle, or nonexistent."""
    try:
        return ConditionReport.objects.filter(
            dealership=dealership, vehicle=vehicle
        ).get(pk=report_id)
    except ConditionReport.DoesNotExist:
        return None


def _lookup_finding_or_404(dealership, vehicle, finding_id):
    """Tenant + vehicle scoped ConditionFinding lookup. Traverses
    finding.report.vehicle to enforce the vehicle scope."""
    try:
        return ConditionFinding.objects.filter(
            dealership=dealership, report__vehicle=vehicle
        ).get(pk=finding_id)
    except ConditionFinding.DoesNotExist:
        return None


# ---- 1. Read latest report --------------------------------------------


@api_view(["GET"])
@permission_classes(
    [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]
)
def admin_condition_report_latest(request, stock_number):
    """Return the latest condition report for the vehicle, or
    ``{report: null}`` when the vehicle has never been inspected.

    Response shape::

        {
          "vehicle": {stock_number, vin, year, make, model, trim,
                      price, display_name},
          "report":  <report projection> | null,
        }

    Latest = most recent by ``(-inspected_at, -created_at)`` — the
    service-layer ordering.  Any status (draft or complete);
    ``latest_completed_condition_report`` isn't exposed here in v1
    because the operator UI cares about "what's the current
    inspection state" more than "when did we last sign off."

    Query cost: 4 queries baseline (vehicle + report + findings +
    photos), plus one ``generate_read_url`` per photo (zero DB /
    network — presigned URL is client-side). Prefetch primes the
    ``findings.all() → photos.all()`` chain so no N+1 per finding.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    header = VehicleLedgerHeaderSerializer(vehicle).data

    # Fetch the latest report with findings + photos prefetched.
    # Cannot use the service function directly here because it
    # returns a bare instance without prefetch; requery with the
    # same filter + order.
    latest = (
        ConditionReport.objects.filter(
            vehicle=vehicle, dealership=dealership
        )
        .select_related("authored_by")
        .prefetch_related(
            "findings",
            "findings__photos",
            "findings__photos__uploaded_by",
        )
        .order_by("-inspected_at", "-created_at")
        .first()
    )

    return Response(
        {
            "vehicle": header,
            "report": _project_report(latest) if latest else None,
        }
    )


# ---- 2. Create draft report -----------------------------------------


@api_view(["POST"])
@permission_classes(
    [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]
)
def admin_condition_report_create(request, stock_number):
    """Create a new draft condition report for the vehicle.

    Request body validated by
    :class:`ConditionReportCreateRequestSerializer` — accepts
    ``inspector_name``, ``inspected_at``, ``mileage_at_inspection``,
    ``notes``. Server owns ``dealership`` (resolved from request),
    ``authored_by`` (= ``request.user``), ``status`` (always
    ``draft`` at create), and ``completed_at`` (NULL at create).

    Returns ``{report: <projection>}`` with 201.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ConditionReportCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    report = condition_report_service.create_report(
        vehicle,
        dealership=dealership,
        authored_by=request.user,
        **serializer.validated_data,
    )
    # Re-fetch with prefetch so findings/photos surfaces (empty on
    # create) are hydrated for _project_report's projection.
    report = (
        ConditionReport.objects.filter(pk=report.pk)
        .select_related("authored_by")
        .prefetch_related(
            "findings",
            "findings__photos",
            "findings__photos__uploaded_by",
        )
        .get()
    )
    return Response(
        {"report": _project_report(report)},
        status=status.HTTP_201_CREATED,
    )


# ---- 3. Complete report ---------------------------------------------


@api_view(["POST"])
@permission_classes(
    [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]
)
def admin_condition_report_complete(request, stock_number, report_id):
    """Transition draft → complete.

    Body is empty (or ignored). Server calls
    :func:`condition_report.complete_report` which atomically sets
    ``status = "complete"`` and ``completed_at = now()``.
    Double-complete raises :class:`ConditionReportImmutableError` →
    409.

    Returns ``{report: <projection>}`` with 200.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    report = _lookup_report_or_404(dealership, vehicle, report_id)
    if report is None:
        return Response(
            {"detail": "Condition report not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        condition_report_service.complete_report(
            report, dealership=dealership
        )
    except ConditionReportImmutableError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )

    report = (
        ConditionReport.objects.filter(pk=report.pk)
        .select_related("authored_by")
        .prefetch_related(
            "findings",
            "findings__photos",
            "findings__photos__uploaded_by",
        )
        .get()
    )
    return Response({"report": _project_report(report)})


# ---- 4. Add finding -------------------------------------------------


@api_view(["POST"])
@permission_classes(
    [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]
)
def admin_condition_finding_create(request, stock_number, report_id):
    """Add one finding to a draft report.

    Body validated by
    :class:`ConditionFindingCreateRequestSerializer` — accepts
    ``category``, ``severity``, ``description``, ``estimated_cost``
    (nullable), ``notes``. ``report`` scoped by URL; ``dealership``
    resolved server-side.

    ``estimated_cost`` is documentation-only — never posts to
    ``VehicleCost`` (locked by M3.1 model tests + M3.2 service
    tests + a focused endpoint test).

    Returns ``{finding: <projection>}`` with 201.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    report = _lookup_report_or_404(dealership, vehicle, report_id)
    if report is None:
        return Response(
            {"detail": "Condition report not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ConditionFindingCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        finding = condition_report_service.add_finding(
            report,
            dealership=dealership,
            **serializer.validated_data,
        )
    except ConditionReportImmutableError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    except ValueError as exc:
        # Defensive: the serializer's ChoiceField rejects invalid
        # category/severity, so ValueError from the service's
        # revalidation shouldn't normally surface. If it does, map
        # to 400 rather than 500.
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )

    # Refetch with photos prefetched (empty on create).
    finding = (
        ConditionFinding.objects.filter(pk=finding.pk)
        .prefetch_related("photos", "photos__uploaded_by")
        .get()
    )
    return Response(
        {"finding": _project_finding(finding)},
        status=status.HTTP_201_CREATED,
    )


# ---- 5+6. Update / delete finding (single view, dispatches on method) --


@api_view(["PATCH", "DELETE"])
@permission_classes(
    [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]
)
def admin_condition_finding_detail(request, stock_number, finding_id):
    """PATCH or DELETE one finding on a draft report.

    Combined into a single view because Django URL dispatch is
    method-agnostic — two ``path()`` entries for the same URL would
    collide.

    - **PATCH** — every supplied field goes through
      :func:`condition_report.update_finding` whose whitelist is
      the source of truth. Attempting to include ``report``,
      ``dealership``, ``id``, etc. surfaces as ``ValueError`` from
      the service → 400. Returns ``{finding: <projection>}``
      with 200.
    - **DELETE** — 204 on success. 404 on cross-tenant /
      nonexistent. 409 if the parent report is already complete.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    finding = _lookup_finding_or_404(dealership, vehicle, finding_id)
    if finding is None:
        return Response(
            {"detail": "Condition finding not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "DELETE":
        try:
            condition_report_service.delete_finding(
                finding, dealership=dealership
            )
        except ConditionReportImmutableError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    serializer = ConditionFindingUpdateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        updated = condition_report_service.update_finding(
            finding,
            dealership=dealership,
            **serializer.validated_data,
        )
    except ConditionReportImmutableError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )

    updated = (
        ConditionFinding.objects.filter(pk=updated.pk)
        .prefetch_related("photos", "photos__uploaded_by")
        .get()
    )
    return Response({"finding": _project_finding(updated)})


# =========================================================================
# Milestone 3 · Increment 6B — condition-report photo API (four endpoints)
# =========================================================================
#
# Wires the M3.5 photo service to HTTP. Same governance +
# permission composition + response projection contracts as M3.6A.
#
# Extended domain-error mapping (in addition to M3.6A):
#
#   PhotoNotYetUploadedError       → 409 Conflict
#   PhotoMetadataMismatchError     → 409 Conflict
#   PhotoAlreadyAttachedError      → 409 Conflict
#   InvalidStorageKeyError         → 400
#   InvalidContentTypeError        → 400
#   InvalidTTLError                → 400
#   ObjectStorageError             → 502 Bad Gateway
#   LocalUploadNotAvailableError   → 404 (dev-only surface hidden
#                                          in production S3 mode)
#
# ``storage_key`` invariants:
#
#   - APPEARS in ``request-upload`` responses (client needs it to
#     hand back to ``attach``).
#   - NEVER appears in any other response — attach, delete, latest-
#     report projections all use ``public_id``.
#   - Locked by explicit negative tests in
#     ``test_admin_condition_report.py``.
#
# Local-upload transport:
#
#   - Behaves exactly like S3 upload from the workflow's perspective:
#     request → upload → attach → verify → row. Never bypasses.
#   - Returns 404 in S3 mode (not 501) — do not advertise dev-only
#     surface.
#   - Never creates the ``ConditionFindingPhoto`` row itself; the
#     normal attach endpoint still performs metadata verification.


def _lookup_photo_or_404(
    dealership, vehicle, public_id
):
    """Tenant + finding-report-vehicle-chain scoped photo lookup.

    ``public_id`` is the durable external identity (M3.1 refinement);
    ``storage_key`` is never used for URL routing. Traverses
    ``finding__report__vehicle`` to enforce the vehicle scope in
    addition to the tenant scope.
    """
    try:
        return ConditionFindingPhoto.objects.filter(
            dealership=dealership,
            finding__report__vehicle=vehicle,
        ).get(public_id=public_id)
    except ConditionFindingPhoto.DoesNotExist:
        return None


def _upload_target_response(upload_target) -> dict:
    """Serialize an :class:`UploadTarget` for the request-upload
    response.

    This is the ONLY response projection that includes
    ``storage_key`` — the client needs it to hand back to
    ``attach_photo``. Every other photo response goes through
    :func:`_project_photo` which omits ``storage_key``.
    """
    return {
        "method": upload_target.method,
        "upload_url": upload_target.upload_url,
        "storage_key": upload_target.storage_key,
        "required_headers": dict(upload_target.required_headers),
        "expires_at": upload_target.expires_at,
    }


# ---- 7. Request upload target ---------------------------------------


@api_view(["POST"])
@permission_classes(
    [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]
)
def admin_condition_photo_request_upload(
    request, stock_number, finding_id
):
    """Authorize a photo upload for a draft finding.

    Returns ``{upload_target: {method, upload_url, storage_key,
    required_headers, expires_at}}`` with 200. **Does NOT create a
    ConditionFindingPhoto row** — that lands only after
    :func:`attach_photo` HEAD-verifies the upload.

    ``storage_key`` in the response is the narrow exception to the
    "never expose storage_key" rule; the client needs it to
    subsequently POST to the attach endpoint.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    finding = _lookup_finding_or_404(dealership, vehicle, finding_id)
    if finding is None:
        return Response(
            {"detail": "Condition finding not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = PhotoRequestUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        upload_target = condition_report_service.request_photo_upload(
            finding,
            dealership=dealership,
            content_type=serializer.validated_data["content_type"],
            uploaded_by=request.user,
        )
    except ConditionReportImmutableError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    except StorageInvalidContentTypeError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    except InvalidTTLError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    except ObjectStorageError as exc:
        return Response(
            {"detail": "Upstream storage failure."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response(
        {"upload_target": _upload_target_response(upload_target)}
    )


# ---- 8. Attach photo (verified against actual object metadata) ------


@api_view(["POST"])
@permission_classes(
    [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]
)
def admin_condition_photo_attach(
    request, stock_number, finding_id
):
    """Persist the ConditionFindingPhoto row after HEAD-verifying
    the uploaded object metadata.

    Response uses :func:`_project_photo` — **``storage_key`` is
    NEVER exposed here**. Client identifies the resulting photo by
    ``public_id``.

    Five-verification path (delegated to
    :func:`condition_report.attach_photo`): cross-tenant guard,
    parent report is draft, canonical key shape, key namespace
    matches dealership slug, actual object metadata matches
    declared. Any mismatch → 409 with a specific domain-error
    class.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    finding = _lookup_finding_or_404(dealership, vehicle, finding_id)
    if finding is None:
        return Response(
            {"detail": "Condition finding not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = PhotoAttachSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        photo = condition_report_service.attach_photo(
            finding,
            dealership=dealership,
            storage_key=serializer.validated_data["storage_key"],
            content_type=serializer.validated_data["content_type"],
            size_bytes=serializer.validated_data["size_bytes"],
            caption=serializer.validated_data.get("caption", ""),
            uploaded_by=request.user,
        )
    except CrossTenantConditionReportError as exc:
        # storage_key referenced another dealership's namespace.
        # Fail closed with 404 — do not leak that a key belongs to
        # some other tenant.
        return Response(
            {"detail": "Condition finding not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ConditionReportImmutableError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    except PhotoNotYetUploadedError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    except PhotoMetadataMismatchError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    except PhotoAlreadyAttachedError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    except InvalidStorageKeyError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    except ObjectStorageError as exc:
        return Response(
            {"detail": "Upstream storage failure."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    photo = (
        ConditionFindingPhoto.objects.filter(pk=photo.pk)
        .select_related("uploaded_by")
        .get()
    )
    return Response(
        {"photo": _project_photo(photo)},
        status=status.HTTP_201_CREATED,
    )


# ---- 9. Delete photo (identified by public_id, never storage_key) ---


@api_view(["DELETE"])
@permission_classes(
    [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]
)
def admin_condition_photo_delete(
    request, stock_number, public_id
):
    """Delete a photo by its public UUID.

    Path identity is ``public_id`` — **storage_key is never used
    for routing or lookup**. Tenant + vehicle scoped lookup fails
    closed with 404 for both nonexistent and cross-tenant.

    Delegates to :func:`condition_report.delete_photo` which
    implements the storage-first strategy:
    :func:`photo_storage.delete_object` runs FIRST; if it raises,
    the DB row is retained and the caller sees 502. Only after
    storage success does the row get dropped.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    photo = _lookup_photo_or_404(dealership, vehicle, public_id)
    if photo is None:
        return Response(
            {"detail": "Condition finding photo not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        condition_report_service.delete_photo(
            photo, dealership=dealership
        )
    except ConditionReportImmutableError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    except ObjectStorageError as exc:
        # Storage-first delete failed — the M3.5 service retained
        # the DB row. Surface a sanitized 502.
        return Response(
            {"detail": "Upstream storage failure."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response(status=status.HTTP_204_NO_CONTENT)


# ---- 10. Local-mode multipart upload receiver (dev only) ------------


@api_view(["POST"])
@parser_classes([MultiPartParser])
@permission_classes(
    [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]
)
def admin_condition_photo_local_upload_receiver(
    request, stock_number, finding_id
):
    """Local-mode substitute for a browser-to-S3 PUT.

    **Returns 404 (not 501) when the active adapter is S3** — the
    dev-only surface must not be advertised in production. If a
    caller is running against a real S3-configured environment,
    this endpoint appears not to exist.

    Behaves exactly like S3 upload from the workflow perspective:
    the M3.7 client (or a developer's manual test) POSTs bytes
    here, and MUST STILL POST to the attach endpoint afterward.
    The receiver does NOT create the
    :class:`ConditionFindingPhoto` row — attach still runs the
    five-verification path.

    Request body: multipart with:
      - ``file`` (required) — the raw bytes.
      - ``storage_key`` (required) — the canonical key returned
        by a prior ``request-upload`` response.
      - ``content_type`` (required) — the MIME the upload
        represents; must match what was authorized.

    Returns ``{stored_metadata: {content_type, size_bytes,
    exists}}`` with 201 on success.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    finding = _lookup_finding_or_404(dealership, vehicle, finding_id)
    if finding is None:
        return Response(
            {"detail": "Condition finding not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Multipart fields — validate before touching storage.
    uploaded_file = request.FILES.get("file")
    storage_key = request.data.get("storage_key")
    content_type = request.data.get("content_type")

    if uploaded_file is None:
        return Response(
            {"detail": "Missing multipart field 'file'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not storage_key:
        return Response(
            {"detail": "Missing multipart field 'storage_key'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not content_type:
        return Response(
            {"detail": "Missing multipart field 'content_type'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verify the supplied key namespace matches the caller's
    # dealership. Defense-in-depth alongside
    # :func:`photo_storage.parse_canonical_key`'s regex check.
    try:
        parsed_slug, _parsed_uuid = (
            photo_storage_service.parse_canonical_key(storage_key)
        )
    except InvalidStorageKeyError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    if parsed_slug != dealership.slug:
        return Response(
            {"detail": "Storage key namespace does not match tenant."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Read the bytes once. ``.read()`` on Django's UploadedFile
    # materializes into memory — the 25 MB ceiling in
    # ``store_local_upload`` bounds the cost.
    data = uploaded_file.read()

    try:
        metadata = photo_storage_service.store_local_upload(
            storage_key=storage_key,
            content_type=content_type,
            data=data,
        )
    except LocalUploadNotAvailableError:
        # Production S3 mode — hide the dev surface.
        return Response(
            {"detail": "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except StorageInvalidContentTypeError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    except InvalidStorageKeyError as exc:
        # Also raised for zero-byte / oversized uploads per the
        # ``store_local_upload`` docstring.
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    except ObjectStorageError as exc:
        return Response(
            {"detail": "Upstream storage failure."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response(
        {
            "stored_metadata": {
                "content_type": metadata.content_type,
                "size_bytes": metadata.size_bytes,
                "exists": metadata.exists,
            }
        },
        status=status.HTTP_201_CREATED,
    )
